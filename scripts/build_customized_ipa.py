"""Bundle the validated configuration in an isolated official app; no native patching."""
import argparse,contextlib,hashlib,io,json,os,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from build_unsigned_ipa import build as unsigned,validate_staging
import ios_portrait
from import_runtime.safe_import import validate_bundle,digest
import importlib.util
_spec=importlib.util.spec_from_file_location('ipa_bootstrap_helpers',Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/bootstrap.py')
_helpers=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_helpers)
tree_digest=_helpers.tree_digest
_navspec=importlib.util.spec_from_file_location('ipa_navigation',Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/navigation.py')
_nav=importlib.util.module_from_spec(_navspec);_navspec.loader.exec_module(_nav)
ROOT=Path(__file__).resolve().parents[1]
BOOT='service.kodi.ios.bootstrap'
# Drive sign-in on the phone: upstream urlopen has no timeout (stuck on "Connecting with server"), and the TLS
# handshake to the sign-in server fails with "[SSL] unknown error" on the device even with certifi's CA bundle
# (TMDb Helper's requests work). Requests now step through certifi, TLS 1.2 only, then Kodi's own curl stack,
# keeping the first that works; the iPhone menu's network diagnostics records which one that is.
TLS=b'''

_tls_contexts = {}
_tls_mode = 0


def tls_context(mode=None):
    """Kodi iOS: certifi's CA bundle when available; mode 1 also caps the handshake at TLS 1.2."""
    import ssl
    mode = min(_tls_mode, 1) if mode is None else mode
    if mode not in _tls_contexts:
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = ssl.create_default_context()
        if mode == 1:
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        _tls_contexts[mode] = context
    return _tls_contexts[mode]


def _is_tls_error(e):
    import ssl
    return isinstance(e, ssl.SSLError) or isinstance(getattr(e, 'reason', None), ssl.SSLError)


class _KodiResponse(object):
    """The small part of an urllib response that Request uses, for a body fetched by Kodi."""
    def __init__(self, url, body):
        import email.message
        import io
        self._url = url
        self._body = io.BytesIO(body)
        self._info = email.message.Message()

    def getcode(self):
        return 200

    def info(self):
        return self._info

    def geturl(self):
        return self._url

    def read(self, size=-1):
        return self._body.read(size)

    def close(self):
        self._body.close()


def _kodi_open(req):
    # Kodi's curl handles TLS itself. Copy to a temp file: xbmcvfs.File.readBytes() returns nothing when a
    # response has no Content-Length (the sign-in server and GitHub's API send such responses).
    import base64
    import os
    import urllib.parse
    import uuid
    import xbmcvfs
    options = dict((name.lower(), value) for name, value in req.header_items())
    if req.data is not None:
        data = req.data if isinstance(req.data, bytes) else Utils.encode(req.data)
        options['postdata'] = base64.b64encode(data).decode('ascii')
        options.setdefault('content-type', 'application/x-www-form-urlencoded')
    url = req.full_url + ('|' + urllib.parse.urlencode(options) if options else '')
    temp = xbmcvfs.translatePath('special://temp/clouddrive-%s.http' % uuid.uuid4().hex)
    try:
        if not xbmcvfs.copy(url, temp):
            raise RuntimeError('Kodi network request failed: ' + urllib.parse.urlsplit(req.full_url).netloc)
        with open(temp, 'rb') as f:
            body = f.read()
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return _KodiResponse(req.full_url, body)


def _open_url(req):
    global _tls_mode
    first = None
    for mode in range(_tls_mode, 3):
        try:
            response = _kodi_open(req) if mode == 2 else urllib.request.urlopen(req, timeout=30, context=tls_context(mode))
        except Exception as e:
            if not _is_tls_error(e):
                raise
            first = first or e
            Logger.notice('TLS transport %d failed: %s' % (mode, e))
            continue
        if mode != _tls_mode:
            Logger.notice('Using TLS transport %d after: %s' % (mode, first))
            _tls_mode = mode
        return response
    raise first
'''
# The iOS watch menu searches Drive for a title: no drive id needed (first signed-in drive) and no typing.
SEARCH=b'''    def _search(self, driveid=None, item_driveid=None, item_id=None, query=None):
        if not driveid:
            drives = [drive['id'] for account in self.get_accounts().values() for drive in account['drives']]
            if not drives:
                self._dialog.ok(self._addon_name, 'Sign in to Google Drive first: open Google Drive and choose "Add an account".')
                return
            driveid = drives[0]
        self.get_provider().configure(self._account_manager, driveid)
        query = query or self._dialog.input('''
DRIVE_COMMON='script.module.clouddrive.common/'
DRIVE_PATCHES=[('clouddrive/common/remote/request.py',b'response = urllib.request.urlopen(req)\n',b'response = _open_url(req)\n'),
 ('clouddrive/common/remote/request.py',b'import urllib\n',b'import urllib\n'+TLS),
 # The sign-in screen first calls /ip with no headers, so Python sent its default "Python-urllib" user agent,
 # which Cloudflare answers with error 1010 on a *.workers.dev sign-in server. Give every request a user agent.
 ('clouddrive/common/remote/request.py',b'        if not self.headers:\n            self.headers = {}\n',b'        if not self.headers:\n            self.headers = {}\n        if not any(name.lower() == \'user-agent\' for name in self.headers):\n            self.headers[\'User-Agent\'] = \'Kodi clouddrive.common\'\n'),
 ('clouddrive/common/remote/signin.py',b'from clouddrive.common.remote.request import Request\n',b'from clouddrive.common.remote.request import Request, tls_context\n'),
 ('clouddrive/common/remote/signin.py',b'self.sock = self._context.wrap_socket(',b'self.sock = tls_context().wrap_socket('),
 # A self-hosted sign-in server on a free *.workers.dev address can't turn off Cloudflare's Browser Integrity Check,
 # which answers error 1010 to the add-on's non-browser user agent (and to the /ip probe, which sent none).
 ('clouddrive/common/remote/signin.py',b"        return '%s/%s clouddrive.common/%s Kodi/%s Python/%s' % (",b"        return 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) %s/%s clouddrive.common/%s Kodi/%s Python/%s' % ("),
 ('clouddrive/common/remote/signin.py',b"status, ip = self._request_over(family, '/ip')",b"status, ip = self._request_over(family, '/ip', self._headers())"),
 ('clouddrive/common/service/upstream.py',b'import urllib.parse\n',b'import urllib.parse\n\nfrom clouddrive.common.remote.request import tls_context\n'),
 ('clouddrive/common/service/upstream.py',b'self._context = ssl.create_default_context()',b'self._context = tls_context()'),
 ('clouddrive/common/ui/addon.py',b"    def _search(self, driveid, item_driveid=None, item_id=None):\n        self.get_provider().configure(self._account_manager, driveid)\n        query = self._dialog.input(",SEARCH),
 ('addon.xml',b'<import addon="script.module.pyqrcode"/>',b'<import addon="script.module.pyqrcode"/>\n\t\t<import addon="script.module.certifi"/>')]

def patch_drive(addonroot):
 files={}
 for name,old,new in DRIVE_PATCHES:
  path=addonroot/DRIVE_COMMON/name;files.setdefault(name,(path,path.read_bytes()))[1]
  data=path.read_bytes();assert data.count(old)==1,'Unexpected Drive source: '+name
  path.write_bytes(data.replace(old,new))
 return [{'path':'addons/'+DRIVE_COMMON+name,'before_sha256':digest(before),'after_sha256':digest(path.read_bytes())} for name,(path,before) in files.items()]

ELEMENTUM='plugin.video.elementum';BURST='script.elementum.burst'
# The engine cannot run as a separate program on iOS, so the add-on's own library mode loads it in-process
# from the app's Frameworks/elementum.framework (built by migration/elementum-ios/build-ios-engine.sh).
ELEMENTUM_IOS=b'''def ios_engine():
    # Kodi-iOS: the engine ships inside the app as Frameworks/elementum.framework and runs in Kodi's process.
    global log_path
    global custom_path
    binary_platform.update(os="ios", arch="arm64", fork=False)
    app = translatePath("special://xbmc/").rstrip("/")
    while app and not app.endswith(".app") and os.path.dirname(app) != app:
        app = os.path.dirname(app)
    framework = os.path.join(app, "Frameworks", "elementum.framework")
    custom_path = get_addon_profile_dir().rstrip("/")
    if not os.path.isdir(custom_path):
        os.makedirs(custom_path)
    log_path = os.path.join(custom_path, "elementum.log")
    ios_follow_container()
    if ios_failed_starts() >= 2:
        # Two starts in a row took Kodi down with them: skip the engine so Kodi stays usable, and put what the
        # engine wrote into kodi.log, where the log uploader finds it. "Retry Elementum engine" clears the marker.
        for name in ("elementum.log", "elementum-stderr.log"):
            try:
                with open(os.path.join(custom_path, name), errors="replace") as f:
                    log.error("Elementum engine stopped Kodi on its last start. %s (end):\\n%s" % (name, f.read()[-8000:]))
            except Exception:
                pass
        xbmc.executebuiltin("Notification(Elementum,Engine stopped Kodi last time - not started,10000)")
        # Performance pass: skip this one start only. The marker used to stay, so the engine stayed off at every
        # later start until "Retry Elementum engine" (the owner's log: iOS ending the app twice while the engine was
        # starting left Elementum off; playing and downloading with it then did nothing).
        try:
            os.remove(os.path.join(custom_path, "engine-starting"))
        except OSError:
            pass
        return False, False
    if not os.path.isfile(os.path.join(framework, "elementum")):
        log.error("Elementum engine not found at %s" % framework)
        return False, False
    return framework, os.path.join(framework, "elementum")

def ios_follow_container():
    # iOS gives the app a new data folder (.../Data/Application/<UUID>/) when it is reinstalled, so folders saved
    # as full paths point at the old one ("Cannot write to download location"). Before the engine reads its
    # settings, move every Elementum folder setting to the current data folder and make sure the folder exists.
    import re
    pattern = r"/Data/Application/[0-9A-Fa-f-]{36}/"
    here = re.search(pattern, translatePath("special://home/"))
    if not here:
        return
    for key in ("download_path", "completed_movies_path", "completed_shows_path", "library_path", "torrents_path"):
        value = ADDON.getSetting(key)
        fixed = re.sub(pattern, here.group(0), value)
        if fixed != value:
            ADDON.setSetting(key, fixed)
            log.info("Kodi-iOS: %s followed the app's data folder to %s" % (key, fixed))
        if fixed and here.group(0) in fixed:
            try:
                os.makedirs(fixed, exist_ok=True)
            except OSError as e:
                log.error("Kodi-iOS: cannot create %s: %s" % (fixed, e))

def ios_failed_starts():
    # How many starts in a row never got the engine answering (a Go panic aborts the whole app).
    try:
        with open(os.path.join(custom_path, "engine-starting")) as f:
            return int(f.read().strip() or 1)
    except (IOError, OSError, ValueError):
        return 0

def ios_crash_guard():
    # Marks the start until the engine answers (or Kodi closes normally); a panic in Go aborts the whole app
    # before Python can react, so the next start sees the marker. One such start is retried; the engine is only
    # skipped after two in a row. The engine's own crash output goes to stderr: keep it in a file.
    marker = os.path.join(custom_path, "engine-starting")
    with open(marker, "w") as f:
        f.write(str(ios_failed_starts() + 1))
    try:
        err = os.path.join(custom_path, "elementum-stderr.log")
        mode = "ab" if os.path.exists(err) and os.path.getsize(err) < 1000000 else "wb"
        stream = open(err, mode)
        stream.write(("\\n--- engine start %s ---\\n" % time.strftime("%Y-%m-%d %H:%M:%S")).encode())
        stream.flush()
        os.dup2(stream.fileno(), 2)
    except Exception as e:
        log.error("Could not keep Elementum's crash output: %s" % e)

    def clear():
        # Closing Kodi (or iOS ending it) soon after opening is not a failed start: only a start that never
        # reached a running engine counts.
        monitor = xbmc.Monitor()
        for _ in range(60):
            if monitor.waitForAbort(2):
                break
            try:
                urllib_request.urlopen(ELEMENTUMD_HOST + "/", timeout=2).close()
                break
            except Exception as e:
                if getattr(e, "code", None):
                    break  # an HTTP answer: the engine is up
        try:
            os.remove(marker)
        except OSError:
            pass
    threading.Thread(target=clear).start()

'''
ELEMENTUM_PATCHES=[('resources/site-packages/elementum/daemon.py',b'def get_elementum_binary():\n',ELEMENTUM_IOS+b'def get_elementum_binary():\n'),
 ('resources/site-packages/elementum/daemon.py',b'    binary_platform = get_platform()\n\n    binary = "elementum"',b'    binary_platform = get_platform()\n    if xbmc.getCondVisibility("System.Platform.IOS"):\n        return ios_engine()\n\n    binary = "elementum"'),
 ('resources/site-packages/elementum/daemon.py',b'    proc = None\n    if force_library != u"true":',b'    if binary_platform.get("os") == "ios":\n        force_library = u"true"\n        elementum_library = "elementum"\n        ios_crash_guard()\n\n    proc = None\n    if force_library != u"true":'),
 ('resources/site-packages/elementum/daemon.py',b'proc = start_elementumd(monitor, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)',b'proc = start_elementumd(monitor, **({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT} if hasSubprocess else {}))'),
 # The Deck's "Choose a version" page (migration/deck-picker) sits in front of Elementum's link dialog, as on the Deck.
 ('resources/site-packages/elementum/rpc.py',b'        title_encoded = "%s %s" % (getLocalizedLabel(title), toUtf8(subject))\n\n        # For Kodi <= 16\n',
  b'        title_encoded = "%s %s" % (getLocalizedLabel(title), toUtf8(subject))\n        try:  # DECK-ELEMENTUM\n            from elementum import deck_picker\n            _deck_choice = deck_picker.run(title_encoded, items)\n            if _deck_choice is not None:\n                return _deck_choice\n        except Exception:\n            pass\n\n        # For Kodi <= 16\n'),
 # iOS closes the app's listening sockets while it is in the background: Elementum's RPC server thread then died on
 # "[Errno 9] Bad file descriptor" (owner's log, ISSUE-068) and Elementum could no longer show its dialogs until Kodi
 # restarted. Serve again with a new server until Kodi exits (Kodi's own JSON-RPC server already does this).
 ('resources/site-packages/elementum/rpc.py',b"""def server_thread():
    try:
        bjsonrpc.bjsonrpc_options['threaded'] = True
        s = bjsonrpc.createserver(host="0.0.0.0", port=JSONRPC_EXT_PORT, handler_factory=ElementumRPCServer)
        log.info("elementum: starting jsonrpc service")
        s.serve()
        log.info("elementum: exiting jsonrpc service")
    except Exception:
        import traceback
        map(log.error, traceback.format_exc().split("\\n"))
        raise
""",b"""def server_thread():
    # KODI-IOS: serve again after iOS closed the socket in the background (Errno 9), until Kodi exits.
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        try:
            bjsonrpc.bjsonrpc_options['threaded'] = True
            s = bjsonrpc.createserver(host="0.0.0.0", port=JSONRPC_EXT_PORT, handler_factory=ElementumRPCServer)
            log.info("elementum: starting jsonrpc service")
            s.serve()
            log.info("elementum: exiting jsonrpc service")
        except Exception as e:
            log.info("elementum: jsonrpc service stopped (%s), starting it again" % e)
        if monitor.waitForAbort(1):
            break
"""),
 # The engine thread only starts where Elementum can fork; on iOS it runs in-process (library mode) instead.
 ('resources/site-packages/elementum/service.py',b'    if not ONLY_CLIENT and PLATFORM["fork"]:',b'    if not ONLY_CLIENT and (PLATFORM["fork"] or PLATFORM.get("os") == "ios"):'),
 ('resources/site-packages/elementum/osarch.py',b'    if global_platform:\n',b'    if xbmc.getCondVisibility("System.Platform.IOS"):\n        ret.update(os="ios", arch="arm64", fork=False)\n        return ret\n\n    if global_platform:\n')]

# Inspect initial /play requests AND source-picker redirects before either reaches the local downloader.
ELEMENTUM_CLOUD=b"""def _kodi_cloud(url):
    import sys
    from xbmcvfs import translatePath
    lib=translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')
    if lib not in sys.path:sys.path.insert(0,lib)
    import elementum_cloud
    return elementum_cloud.route(url)

"""
ELEMENTUM_PATCHES += [
 ('resources/site-packages/elementum/navigation.py',b'def _json(url):\n',ELEMENTUM_CLOUD+b'def _json(url):\n    if _kodi_cloud(url):return None\n'),
 ('resources/site-packages/elementum/navigation.py',b'        if response.code == 300:\n',b'        if location and _kodi_cloud(location):return None\n        if response.code == 300:\n')]

# Kodi-iOS source check (service.kodi.ios.bootstrap/resources/lib/source_match.py) inside Burst, where every provider's
# results arrive: a torrent of another title ("Fall" 2026 for "Fall" 2022) never reaches Elementum, so its dialog, its
# auto-pick ("silent") plays and downloads only get the title asked for. Burst 0.0.99 (migration/elementum-ios/source-lock.json).
BURST_HELPERS=b"""# KODI-IOS-SOURCE-MATCH r1: only torrents of the title Elementum asked for (service.kodi.ios.bootstrap source_match.py)
_kios = {}


def _kios_start(payload, method):
    _kios.clear()
    _kios.update(payload=payload, method=method, hidden=[], exp=None, ready=False)
    Thread(target=_kios_expect).start()    # TMDb while the providers search, not after them


def _kios_expect():
    # The identity (titles in every language, year(s), IMDb/TMDb, season/episode), completed from TMDb once per search.
    from threading import Lock
    lock = _kios.setdefault('lock', Lock())
    with lock:
        if not _kios.get('ready'):
            _kios['ready'] = True
            try:
                import sys
                try:
                    from xbmcvfs import translatePath
                except ImportError:
                    translatePath = xbmc.translatePath
                lib = translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')
                if lib not in sys.path:
                    sys.path.insert(0, lib)
                import source_match
                exp = source_match.from_burst(_kios.get('payload'), _kios.get('method'))
                _kios['sm'] = source_match
                _kios['exp'] = source_match.enrich(exp) if exp else None
            except Exception as e:
                log.warning("Kodi-iOS source check unavailable: %s" % repr(e))
    return _kios.get('sm'), _kios.get('exp')


def _kios_prefilter(provider, results):
    try:
        sm, exp = _kios_expect()
        if not sm or not exp:
            return results
        kept, hidden = sm.split(results, exp, name=lambda r: r.get('name'))
        _kios['hidden'].extend(hidden)
        if hidden:
            log.info("[%s] Kodi-iOS source check: kept %d, hidden %d (%s)" % (provider, len(kept), len(hidden), sm.reasons_text(hidden)))
        return kept
    except Exception as e:
        log.warning("[%s] Kodi-iOS source check failed: %s" % (provider, repr(e)))
        return results


def _kios_finish(results, payload):
    sm, exp = _kios.get('sm'), _kios.get('exp')
    if not sm or not exp:
        return results
    hidden = _kios.get('hidden') or []
    sm.report('Burst', exp, results, hidden, name=lambda r: r.get('name'))
    revealed = False
    if hidden and not results:
        message = "No source is %s: %d hidden (%s)" % (exp.get('label'), len(hidden), sm.reasons_text(hidden))
        if not payload.get('silent'):
            try:
                revealed = xbmcgui.Dialog().yesno('Not this title?', message + "\\n\\nShow them anyway?")
            except Exception:
                revealed = False
        if revealed:
            results = cleanup_results([r for r, _ in hidden])
        else:
            notify(message, ADDON_ICON)
    sm.publish(exp, hidden=len(hidden), revealed=revealed)
    return results


"""
BURST_PATCHES=[('burst/burst.py',b'def search(payload, method="general"):\n',BURST_HELPERS+b'def search(payload, method="general"):\n'),
 ('burst/burst.py',b"    request_time = time.time()\n\n    cookie_sync(payload['silent'])\n",b"    request_time = time.time()\n    _kios_start(payload, method)  # KODI-IOS-SOURCE-MATCH\n\n    cookie_sync(payload['silent'])\n"),
 # Before each provider's results are sorted and cut to the best ones, so the other title cannot crowd this one out.
 ('burst/burst.py',b'    definition = get_alias(definition, get_setting("%s_alias" % provider))\n\n    # 0 "Resolution"\n',
  b'    definition = get_alias(definition, get_setting("%s_alias" % provider))\n    results = _kios_prefilter(provider, results)  # KODI-IOS-SOURCE-MATCH\n\n    # 0 "Resolution"\n'),
 ('burst/burst.py',b'    filtered_results = apply_filters(provider_results)\n',b'    filtered_results = apply_filters(provider_results)\n    filtered_results = _kios_finish(filtered_results, payload)  # KODI-IOS-SOURCE-MATCH\n')]

def patch_burst(addonroot):
 """BURST_PATCHES into the unpacked Burst; [{'path','before_sha256','after_sha256'}]."""
 files={}
 for name,old,new in BURST_PATCHES:
  path=addonroot/BURST/name;before=files.setdefault(name,(path,path.read_bytes()))[1]
  data=path.read_bytes();assert data.count(old)==1,'Unexpected Burst source: '+name
  path.write_bytes(data.replace(old,new))
 return [{'path':'addons/'+BURST+'/'+name,'before_sha256':digest(before),'after_sha256':digest(path.read_bytes())} for name,(path,before) in files.items()]

def unpack_addon(archive,id,dest):
 """Extract one add-on zip (plain Python and data only) into dest/<id>."""
 with zipfile.ZipFile(archive) as z:
  names=[n for n in z.namelist() if not n.endswith('/')]
  assert all(n.startswith(id+'/') and '..' not in n and not n.endswith(('.so','.dll','.dylib','.exe','.pyd')) for n in names),'Unexpected add-on layout: '+id
  for n in names:
   path=dest/n;assert not path.exists(),'Unexpected add-on collision: '+n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(n))

def add_profile_addons(inputs,bootstrap):
 """Add-ons other add-ons load from special://home/addons (Umbrella imports its scraper module from there):
 the setup add-on copies them into the writable add-ons folder at first start."""
 found=sorted((inputs/'extras-profile').glob('*.zip')) if (inputs/'extras-profile').is_dir() else []
 for archive in found:unpack_addon(archive,archive.stem,bootstrap/'payload')
 return [a.stem for a in found]

DECK_PICKER=ROOT/'migration/deck-picker'
SOURCE_MATCH=ROOT/'migration/bundled-bootstrap/resources/lib/source_match.py'

def deck_page_files():
 """The Deck's page and its pictures, {path under resources/skins/Default: bytes}."""
 import base64
 page=(DECK_PICKER/'DeckSourceSelect.xml').read_bytes()
 # The phone's canvas is wider than 1280 at 720 high: let the full-screen background layers reach the right edge.
 full=b'\t\t\t<left>0</left>\n\t\t\t<top>0</top>\n\t\t\t<width>1280</width>\n'
 assert page.count(full)==2,'Unexpected DeckSourceSelect.xml'
 page=page.replace(full,b'\t\t\t<left>0</left>\n\t\t\t<top>0</top>\n\t\t\t<right>0</right>\n')
 files={'720p/DeckSourceSelect.xml':page}
 for name,data in json.loads((DECK_PICKER/'media.json').read_text())['files'].items():files['media/deck/'+name]=base64.b64decode(data)
 return files

def add_deck_picker(addonroot):
 """The Deck's Elementum link page: quality first, then the five best links with the title's poster and details.
 Umbrella gets the same page through the bootstrap add-on (umbrella_picker.py), which carries its own copy."""
 files={'site-packages/elementum/deck_picker.py':(DECK_PICKER/'deck_picker.py').read_bytes(),
        # The page's source check (the bootstrap add-on's lib has its own copy, from migration/bundled-bootstrap).
        'site-packages/elementum/source_match.py':SOURCE_MATCH.read_bytes()}
 files.update({'skins/Default/'+rel:data for rel,data in deck_page_files().items()})
 # The page's dark backdrop and close button are Elementum's own pictures: Umbrella's copy needs them too.
 media=addonroot/ELEMENTUM/'resources/skins/Default/media'
 shared={'skins/Default/media/'+rel:(media/rel).read_bytes() for rel in ('AddonWindow/white.png','Button/close.png') if (media/rel).is_file()}
 written=[]
 for root,extra in ((addonroot/ELEMENTUM/'resources',files),(addonroot/BOOT/'resources',
   {'lib/deck_picker.py':files['site-packages/elementum/deck_picker.py'],**{'skins/Default/'+rel:data for rel,data in deck_page_files().items()},**shared})):
  for rel,data in extra.items():
   dest=root/rel;assert not dest.exists(),'Unexpected deck picker collision: '+str(dest)
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);written.append(str(dest.relative_to(addonroot.parent)))
 return sorted(written)

def add_elementum(inputs,target,addonroot):
 """Install the pinned Elementum client (patched for iOS), Burst, their Python modules and the engine framework."""
 with zipfile.ZipFile(inputs/'burst.zip') as z:
  names=[n for n in z.namelist() if not n.endswith('/')]
  # Search providers only: plain Python and data, nothing native that iOS would have to load.
  assert all(n.startswith(BURST+'/') and '..' not in n and not n.endswith(('.so','.dll','.dylib','.exe')) for n in names)
  for n in names:
   dest=addonroot/n;assert not dest.exists(),'Unexpected Burst collision';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
 with zipfile.ZipFile(inputs/'client.zip') as z:
  names=[n for n in z.namelist() if not n.endswith('/')];assert all(n.startswith(ELEMENTUM+'/') and '..' not in n for n in names)
  # platform_detect probes ELF/PE test libraries; iOS cannot load them and the patched osarch never asks.
  for n in names:
   if n.startswith(ELEMENTUM+'/resources/site-packages/platform_detect/libraries/'):continue
   dest=addonroot/n;assert not dest.exists(),'Unexpected Elementum collision';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
 files={}
 for name,old,new in ELEMENTUM_PATCHES:
  path=addonroot/ELEMENTUM/name;files.setdefault(name,(path,path.read_bytes()))[1]
  data=path.read_bytes();assert data.count(old)==1,'Unexpected Elementum source: '+name
  path.write_bytes(data.replace(old,new))
 burst_patches=patch_burst(addonroot)
 deck_picker=add_deck_picker(addonroot)
 modules=sorted((inputs/'modules').iterdir())
 apps=sorted((inputs/'extras-app').glob('*.zip')) if (inputs/'extras-app').is_dir() else []
 for archive in apps:unpack_addon(archive,archive.stem,addonroot)
 for d in modules:assert not (addonroot/d.name).exists(),'Unexpected module collision';shutil.copytree(d,addonroot/d.name)
 frameworks=target/'Frameworks';frameworks.mkdir(exist_ok=True);assert not (frameworks/'elementum.framework').exists()
 with zipfile.ZipFile(inputs/'framework.zip') as z:
  for n in z.namelist():assert n.startswith('elementum.framework/') and '..' not in n
  z.extractall(frameworks)
 binary=frameworks/'elementum.framework/elementum';assert binary.read_bytes()[:4]==b'\xcf\xfa\xed\xfe','Engine is not a 64-bit Mach-O'
 extra=[]
 for archive in sorted((inputs/'frameworks').glob('*.framework.zip')) if (inputs/'frameworks').is_dir() else []:
  name=archive.name[:-len('.zip')];assert not (frameworks/name).exists()
  with zipfile.ZipFile(archive) as z:
   for n in z.namelist():assert n.startswith(name+'/') and '..' not in n
   z.extractall(frameworks)
  executable=frameworks/name/name[:-len('.framework')];assert executable.read_bytes()[:4]==b'\xcf\xfa\xed\xfe',name+' is not a 64-bit Mach-O'
  extra.append('Frameworks/'+name)
 return {'addons':[ELEMENTUM,BURST]+[d.name for d in modules]+[a.stem for a in apps],'framework':'Frameworks/elementum.framework','frameworks':extra,'deck_picker':deck_picker,'burst_patches':burst_patches,'framework_sha256':digest(binary.read_bytes()),
         'patches':[{'path':'addons/'+ELEMENTUM+'/'+name,'before_sha256':digest(before),'after_sha256':digest(path.read_bytes())} for name,(path,before) in files.items()]}

def prepare(app,bundle,expected,work,elementum=None,portrait_inputs=None):
 validate_staging(app,work)
 manifest,addons,config=validate_bundle(bundle,expected)
 target=work/'Kodi.app';shutil.copytree(app,target,symlinks=True)
 manifests=list(target.rglob('system/addon-manifest.xml'));assert len(manifests)==1,'Unique Kodi system manifest required'
 system=manifests[0];base=system.parent.parent;addonroot=base/'addons';assert addonroot.is_dir()
 # special://xbmc/system/advancedsettings.xml: Kodi's splash off on every install (ios_portrait.disable_splash).
 splash=ios_portrait.disable_splash(system.parent)
 for name,data in addons.items():
  dest=base/name
  assert not dest.exists(),'Unexpected bundled addon collision: '+name
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 navigation_files=_nav.patch_skin(addonroot/'skin.arctic.fuse.3') if (addonroot/'skin.arctic.fuse.3').is_dir() else []
 drive_files=patch_drive(addonroot) if (addonroot/DRIVE_COMMON).is_dir() else []
 engine=add_elementum(elementum,target,addonroot) if elementum else None
 bootstrap=addonroot/BOOT;shutil.copytree(ROOT/'migration/bundled-bootstrap',bootstrap,dirs_exist_ok=True)  # the Deck page (add_deck_picker) may already be in it
 profile_addons=add_profile_addons(elementum,bootstrap) if elementum else []
 # The in-app updater compares this with the build-N release tags.
 (bootstrap/'build.json').write_text(json.dumps({'build':int(os.environ.get('GITHUB_RUN_NUMBER') or 0),'commit':os.environ.get('GITHUB_SHA','')[:12]})+'\n')
 seed=bootstrap/'seed';seed.mkdir();entries=[]
 for name,data in sorted(config.items()):
  relative=name[len('userdata/'):]
  if relative=='guisettings.xml':
   gui=ET.fromstring(data)
   for setting in list(gui.findall('setting')):
    if setting.get('id')=='input.enablemouse':gui.remove(setting)
   data=ET.tostring(gui,encoding='utf-8')+b'\n'
  dest=seed/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);entries.append({'path':relative,'sha256':digest(data)})
 # r11 portrait: skin folder (rows from the seeded widget lists), Info.plist, optional rotation-aware executable.
 portrait=ios_portrait.apply(target,addonroot/'skin.arctic.fuse.3',seed,portrait_inputs) if (addonroot/'skin.arctic.fuse.3').is_dir() else None
 keymap=seed/'keymaps/zz-kodi-ios-navigation.xml';keymap.parent.mkdir(parents=True,exist_ok=True);keymap.write_bytes(_nav.TOUCH.encode()+b'\n');entries.append({'path':'keymaps/zz-kodi-ios-navigation.xml','sha256':digest(keymap.read_bytes())})
 # Topological dependency order, excluding native/core providers already in the foundation.
 requires={}
 for id in manifest['addon_ids']+(engine['addons'] if engine else []):
  xml=ET.parse(addonroot/id/'addon.xml').getroot();requires[id]=[d.get('addon') for d in xml.findall('requires/import') if d.get('optional')!='true']
 order=[];visiting=set()
 def visit(id):
  if id in order:return
  assert id not in visiting,'Dependency cycle';visiting.add(id)
  for dep in requires[id]:
   if dep in requires:visit(dep)
  visiting.remove(id);order.append(id)
 for id in sorted(requires):visit(id)
 mutable=[{'id':id,'version':ET.parse(addonroot/id/'addon.xml').getroot().get('version'),'tree_sha256':tree_digest(addonroot/id)} for id in order if id.startswith('skin.')]
 (seed/'seed-manifest.json').write_text(json.dumps({'version':'3-touch-r10','files':entries,'addons':order,'mutable_skins':mutable,'navigation_revision':_nav.REVISION},indent=2)+'\n')
 tree=ET.parse(system);root=tree.getroot();existing={a.text for a in root.findall('addon')}
 for id in order+[BOOT]:
  assert id not in existing,'System manifest collision';ET.SubElement(root,'addon',{} if id==BOOT else {'optional':'true'}).text=id
 ET.indent(root);tree.write(system,encoding='utf-8',xml_declaration=True)
 return target,{'addon_ids':order,'seed_files':entries,'system_manifest':str(system.relative_to(target)),'bootstrap_id':BOOT,'import_sha256':expected,'mutable_skins':mutable,'navigation_patch':{'revision':_nav.REVISION,'files':navigation_files},'drive_patch':{'files':drive_files},'elementum':engine,'profile_addons':profile_addons,'portrait':portrait,'splash':splash}

# Owner crash report (build 142, cpu_resource_fatal): iOS killed Kodi for CPU use, and part of it was Python compiling
# source (builtin_compile / Py_CompileStringObject under import). The app bundle is read-only, so Python can never save
# a .pyc there: the official package ships none for its standard library (1089 .py, 0 in python3.11/__pycache__) and
# none for most add-ons, and every plugin run (a row, a show page, a source search) parsed os, json and TMDb Helper
# again. They are now compiled here by the same Python version (3.11, cache tag cpython-311), as unchecked-hash .pyc
# files, which Python uses without comparing them with the source (the bundle never changes after signing).
PYC_TAG='cpython-311'
def python311():
 exe=os.environ.get('KODI_IOS_PYTHON311') or shutil.which('python3.11')
 assert exe,'Python 3.11 is required to precompile the bundle (set KODI_IOS_PYTHON311)'
 version=subprocess.run([exe,'-I','-c','import sys;print(sys.implementation.cache_tag)'],capture_output=True,text=True,check=True).stdout.strip()
 assert version==PYC_TAG,'Bundle bytecode must come from CPython 3.11, got '+version
 return exe
def precompile(app):
 app=Path(app);roots=sorted(str(p) for p in list(app.glob('Frameworks/lib/python3.11'))+list(app.rglob('AppHome/addons')) if p.is_dir())
 assert len(roots)==2,'Expected the Python standard library and AppHome/addons, got %r'%roots
 before=sum(1 for _ in app.rglob('*.%s.pyc'%PYC_TAG))
 # Files that are not Python 3 (old test data, Python 2 back-ports) fail to compile and stay source-only.
 subprocess.run([python311(),'-I','-m','compileall','-q','-j','0','--invalidation-mode','unchecked-hash',
                 '-s',str(app),'-p','Kodi.app']+roots,check=False,stdout=subprocess.DEVNULL)
 after=sum(1 for _ in app.rglob('*.%s.pyc'%PYC_TAG))
 sources=sum(1 for root in roots for _ in Path(root).rglob('*.py'))
 assert after-before>sources//2,'Too few modules precompiled (%d of %d)'%(after-before,sources)
 return {'tag':PYC_TAG,'added':after-before,'sources':sources}

def build(app,bundle,expected,deb,output,work,elementum=None,portrait_inputs=None):
 staged,details=prepare(app,bundle,expected,work,elementum,portrait_inputs)
 details['bytecode']=precompile(staged)
 # The shared native packer emits a diagnostic-only intermediate label; publish only the final verified customized report.
 with contextlib.redirect_stdout(io.StringIO()):report=unsigned(staged,output,deb)
 old=output/report['filename'];ipa=output/'Kodi-iOS-Customized-Touch-r10.ipa';old.rename(ipa)
 with zipfile.ZipFile(ipa) as z:
  assert z.testzip() is None
  base='Payload/Kodi.app/'+details['system_manifest'].rsplit('/system/',1)[0]
  for id in details['addon_ids']+[BOOT]:assert base+'/addons/'+id+'/addon.xml' in z.namelist()
  patches={'addons/skin.arctic.fuse.3/'+e['path']:e for e in details['navigation_patch']['files']}
  patches.update({e['path']:e for e in details['drive_patch']['files']})
  for e in (details['portrait'] or {}).get('changed',[]):
   # A file the navigation patch already edited (VideoOSD.xml): its source is the bundle's, its result the portrait one.
   patches[e['path']]=dict(e,before_sha256=patches[e['path']]['before_sha256']) if e['path'] in patches else e
  for name,body in validate_bundle(bundle,expected)[1].items():
   if name in patches:assert digest(body)==patches[name]['before_sha256'],'Navigation patch source mismatch'
   expected_hash=patches[name]['after_sha256'] if name in patches else digest(body)
   assert digest(z.read(base+'/'+name))==expected_hash,'Bundled addon bytes changed unexpectedly'
  for e in details['seed_files']:assert digest(z.read(base+'/addons/'+BOOT+'/seed/'+e['path']))==e['sha256']
  assert digest(z.read(base+'/system/advancedsettings.xml'))==details['splash']['sha256'],'Splash setting missing from IPA'
  names=set(z.namelist())
  for module in ('Payload/Kodi.app/Frameworks/lib/python3.11/__pycache__/os.%s.pyc','Payload/Kodi.app/Frameworks/lib/python3.11/json/__pycache__/decoder.%s.pyc'):
   assert module%PYC_TAG in names,'Precompiled standard library missing from IPA: '+module%PYC_TAG
  if details['elementum']:
   assert digest(z.read('Payload/Kodi.app/Frameworks/elementum.framework/elementum'))==details['elementum']['framework_sha256'],'Engine framework missing from IPA'
   for e in details['elementum']['patches']:assert digest(z.read(base+'/'+e['path']))==e['after_sha256']
 report.update(filename=ipa.name,sha256=digest(ipa.read_bytes()),configuration_bundled=True,addons_added=True,status='CUSTOMIZED_UNSIGNED_HOST_VALIDATED_DEVICE_TEST_PENDING',bootstrap=details,device_tested=False,manual_import_required=False,elementum_engine_included=bool(details['elementum']),navigation_revision=_nav.REVISION,patched_navigation_windows=len(details['navigation_patch']['files']),configuration_files=len(details['seed_files']),limitations=['iPhone bootstrap execution, skin rendering, signing, Google Drive and rollback still require actual device evidence','Use foreground Kodi; no unverified native engine or remote service'])
 (output/'ipa-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in {'native_inventory','bootstrap'}}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--deb',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--elementum',type=Path,help='inputs from fetch_elementum_inputs.py');p.add_argument('--portrait-inputs',type=Path,help='from ios_portrait.py --fetch');a=p.parse_args();build(a.app,a.bundle,a.expected_sha256,a.deb,a.output,a.work,a.elementum if a.elementum and (a.elementum/'framework.zip').is_file() else None,a.portrait_inputs)
