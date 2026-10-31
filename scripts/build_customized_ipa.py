"""Bundle the validated configuration in an isolated official app; no native patching."""
import argparse,contextlib,hashlib,io,json,os,shutil,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from build_unsigned_ipa import build as unsigned,validate_staging
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
 ('clouddrive/common/remote/signin.py',b'from clouddrive.common.remote.request import Request\n',b'from clouddrive.common.remote.request import Request, tls_context\n'),
 ('clouddrive/common/remote/signin.py',b'self.sock = self._context.wrap_socket(',b'self.sock = tls_context().wrap_socket('),
 ('clouddrive/common/service/upstream.py',b'import urllib.parse\n',b'import urllib.parse\n\nfrom clouddrive.common.remote.request import tls_context\n'),
 ('clouddrive/common/service/upstream.py',b'self._context = ssl.create_default_context()',b'self._context = tls_context()'),
 ('clouddrive/common/ui/addon.py',b"    def _search(self, driveid, item_driveid=None, item_id=None):\n        self.get_provider().configure(self._account_manager, driveid)\n        query = self._dialog.input(",SEARCH),
 ('addon.xml',b'<import addon="script.module.pyqrcode"/>',b'<import addon="script.module.pyqrcode"/>\n\t\t<import addon="script.module.certifi"/>')]

def patch_drive(addonroot):
 files={}
 for name,old,new in DRIVE_PATCHES:
  path=addonroot/DRIVE_COMMON/name;before=files.setdefault(name,(path,path.read_bytes()))[1]
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
    if not os.path.isfile(os.path.join(framework, "elementum")):
        log.error("Elementum engine not found at %s" % framework)
        return False, False
    return framework, os.path.join(framework, "elementum")

'''
ELEMENTUM_PATCHES=[('resources/site-packages/elementum/daemon.py',b'def get_elementum_binary():\n',ELEMENTUM_IOS+b'def get_elementum_binary():\n'),
 ('resources/site-packages/elementum/daemon.py',b'    binary_platform = get_platform()\n\n    binary = "elementum"',b'    binary_platform = get_platform()\n    if xbmc.getCondVisibility("System.Platform.IOS"):\n        return ios_engine()\n\n    binary = "elementum"'),
 ('resources/site-packages/elementum/daemon.py',b'    proc = None\n    if force_library != u"true":',b'    if binary_platform.get("os") == "ios":\n        force_library = u"true"\n        elementum_library = "elementum"\n\n    proc = None\n    if force_library != u"true":'),
 ('resources/site-packages/elementum/daemon.py',b'proc = start_elementumd(monitor, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)',b'proc = start_elementumd(monitor, **({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT} if hasSubprocess else {}))'),
 ('resources/site-packages/elementum/osarch.py',b'    if global_platform:\n',b'    if xbmc.getCondVisibility("System.Platform.IOS"):\n        ret.update(os="ios", arch="arm64", fork=False)\n        return ret\n\n    if global_platform:\n')]

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
  path=addonroot/ELEMENTUM/name;before=files.setdefault(name,(path,path.read_bytes()))[1]
  data=path.read_bytes();assert data.count(old)==1,'Unexpected Elementum source: '+name
  path.write_bytes(data.replace(old,new))
 modules=sorted((inputs/'modules').iterdir())
 for d in modules:assert not (addonroot/d.name).exists(),'Unexpected module collision';shutil.copytree(d,addonroot/d.name)
 frameworks=target/'Frameworks';frameworks.mkdir(exist_ok=True);assert not (frameworks/'elementum.framework').exists()
 with zipfile.ZipFile(inputs/'framework.zip') as z:
  for n in z.namelist():assert n.startswith('elementum.framework/') and '..' not in n
  z.extractall(frameworks)
 binary=frameworks/'elementum.framework/elementum';assert binary.read_bytes()[:4]==b'\xcf\xfa\xed\xfe','Engine is not a 64-bit Mach-O'
 return {'addons':[ELEMENTUM,BURST]+[d.name for d in modules],'framework':'Frameworks/elementum.framework','framework_sha256':digest(binary.read_bytes()),
         'patches':[{'path':'addons/'+ELEMENTUM+'/'+name,'before_sha256':digest(before),'after_sha256':digest(path.read_bytes())} for name,(path,before) in files.items()]}

def prepare(app,bundle,expected,work,elementum=None):
 validate_staging(app,work)
 manifest,addons,config=validate_bundle(bundle,expected)
 target=work/'Kodi.app';shutil.copytree(app,target,symlinks=True)
 manifests=list(target.rglob('system/addon-manifest.xml'));assert len(manifests)==1,'Unique Kodi system manifest required'
 system=manifests[0];base=system.parent.parent;addonroot=base/'addons';assert addonroot.is_dir()
 for name,data in addons.items():
  dest=base/name
  assert not dest.exists(),'Unexpected bundled addon collision: '+name
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 navigation_files=_nav.patch_skin(addonroot/'skin.arctic.fuse.3') if (addonroot/'skin.arctic.fuse.3').is_dir() else []
 drive_files=patch_drive(addonroot) if (addonroot/DRIVE_COMMON).is_dir() else []
 engine=add_elementum(elementum,target,addonroot) if elementum else None
 bootstrap=addonroot/BOOT;shutil.copytree(ROOT/'migration/bundled-bootstrap',bootstrap)
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
 return target,{'addon_ids':order,'seed_files':entries,'system_manifest':str(system.relative_to(target)),'bootstrap_id':BOOT,'import_sha256':expected,'mutable_skins':mutable,'navigation_patch':{'revision':_nav.REVISION,'files':navigation_files},'drive_patch':{'files':drive_files},'elementum':engine}

def build(app,bundle,expected,deb,output,work,elementum=None):
 staged,details=prepare(app,bundle,expected,work,elementum)
 # The shared native packer emits a diagnostic-only intermediate label; publish only the final verified customized report.
 with contextlib.redirect_stdout(io.StringIO()):report=unsigned(staged,output,deb)
 old=output/report['filename'];ipa=output/'Kodi-iOS-Customized-Touch-r10.ipa';old.rename(ipa)
 with zipfile.ZipFile(ipa) as z:
  assert z.testzip() is None
  base='Payload/Kodi.app/'+details['system_manifest'].rsplit('/system/',1)[0]
  for id in details['addon_ids']+[BOOT]:assert base+'/addons/'+id+'/addon.xml' in z.namelist()
  patches={'addons/skin.arctic.fuse.3/'+e['path']:e for e in details['navigation_patch']['files']}
  patches.update({e['path']:e for e in details['drive_patch']['files']})
  for name,body in validate_bundle(bundle,expected)[1].items():
   if name in patches:assert digest(body)==patches[name]['before_sha256'],'Navigation patch source mismatch'
   expected_hash=patches[name]['after_sha256'] if name in patches else digest(body)
   assert digest(z.read(base+'/'+name))==expected_hash,'Bundled addon bytes changed unexpectedly'
  for e in details['seed_files']:assert digest(z.read(base+'/addons/'+BOOT+'/seed/'+e['path']))==e['sha256']
  if details['elementum']:
   assert digest(z.read('Payload/Kodi.app/Frameworks/elementum.framework/elementum'))==details['elementum']['framework_sha256'],'Engine framework missing from IPA'
   for e in details['elementum']['patches']:assert digest(z.read(base+'/'+e['path']))==e['after_sha256']
 report.update(filename=ipa.name,sha256=digest(ipa.read_bytes()),configuration_bundled=True,addons_added=True,status='CUSTOMIZED_UNSIGNED_HOST_VALIDATED_DEVICE_TEST_PENDING',bootstrap=details,device_tested=False,manual_import_required=False,elementum_engine_included=bool(details['elementum']),navigation_revision=_nav.REVISION,patched_navigation_windows=len(details['navigation_patch']['files']),configuration_files=len(details['seed_files']),limitations=['iPhone bootstrap execution, skin rendering, signing, Google Drive and rollback still require actual device evidence','Use foreground Kodi; no unverified native engine or remote service'])
 (output/'ipa-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in {'native_inventory','bootstrap'}}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--deb',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--elementum',type=Path,help='inputs from fetch_elementum_inputs.py');a=p.parse_args();build(a.app,a.bundle,a.expected_sha256,a.deb,a.output,a.work,a.elementum if a.elementum and (a.elementum/'framework.zip').is_file() else None)
