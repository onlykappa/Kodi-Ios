"""Intercept Elementum's selected URI before /play starts its local torrent engine.

Called for both initial plugin requests and source-picker redirects. Fail closed:
missing accounts or an unreadable torrent must never start a phone download.
"""
import base64
import hashlib
import os
import urllib.parse
import urllib.request

def ask(dialog, heading, rows):
    """Roadmap B.9 (owner log eabc204b 09:58:04): after the version, Kodi's select box asked the next question. The
    approved choice sheet asks it instead; Kodi's box only if the sheet cannot open. rows: [(label, detail)]."""
    try:
        import xbmcgui
        import choice_sheet
        return choice_sheet.choose({'heading': heading, 'rows': [{'label': l, 'detail': d} for l, d in rows]}, xbmcgui=xbmcgui)
    except Exception:
        return dialog.select(heading, ['%s · %s' % (l, d) for l, d in rows])


LIMIT = 8 * 1024 * 1024  # torrent metadata only, never media


def torrent_hash(data, with_name=False):
    """Hash the original bencoded info span (re-encoding can change the torrent hash)."""
    def end(pos, depth=0):
        if depth > 64 or pos >= len(data):
            raise ValueError('Invalid torrent metadata')
        ch = data[pos:pos + 1]
        if ch == b'i':
            return data.index(b'e', pos) + 1
        if ch in (b'l', b'd'):
            pos += 1
            while data[pos:pos + 1] != b'e':
                pos = end(pos, depth + 1)
            return pos + 1
        colon = data.index(b':', pos)
        count = int(data[pos:colon])
        if count < 0 or colon + 1 + count > len(data):
            raise ValueError('Invalid torrent metadata')
        return colon + 1 + count
    if not data.startswith(b'd') or len(data) > LIMIT:
        raise ValueError('Invalid torrent metadata')
    pos = 1
    while data[pos:pos + 1] != b'e':
        colon = data.index(b':', pos)
        key = data[colon + 1:end(pos)]
        pos = end(pos)
        stop = end(pos)
        if key == b'info':
            h=hashlib.sha1(data[pos:stop]).hexdigest()
            name=''
            if with_name and data[pos:pos+1]==b'd':
                at=pos+1
                while data[at:at+1]!=b'e':
                    colon=data.index(b':',at);field=data[colon+1:end(at)];at=end(at)
                    finish=end(at)
                    if field in (b'name',b'name.utf-8'):
                        colon=data.index(b':',at);name=data[colon+1:finish].decode('utf-8','replace')
                        if field==b'name.utf-8':break
                    at=finish
            return (h,name) if with_name else h
        pos = stop
    raise ValueError('Torrent has no info dictionary')


def selected(url, read=None):
    """Selected hash, display name and episode context, or None for a browsing/search URL."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme == 'plugin':
        if parsed.netloc != 'plugin.video.elementum':return None
    elif parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != 65220:return None
    if parsed.path.rstrip('/') not in ('/play', '/download'):return None
    q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
    uri = q.get('uri') or q.get('resume') or ''
    if not uri:raise ValueError('Elementum did not provide the selected torrent')
    name = q.get('query', '')
    magnet = urllib.parse.urlsplit(uri)
    if magnet.scheme == 'magnet':
        mq = urllib.parse.parse_qs(magnet.query)
        hashes = [v[9:] for v in mq.get('xt', []) if v.lower().startswith('urn:btih:')]
        h = hashes[0] if hashes else ''
        if len(h) == 32:h = base64.b32decode(h.upper()).hex()
        name = (mq.get('dn') or [name])[0]
    elif len(uri) == 40 and all(c in '0123456789abcdefABCDEF' for c in uri):h = uri
    else:
        if read is None:
            if uri.startswith(('http://', 'https://')):
                with urllib.request.urlopen(uri, timeout=30) as response:data = response.read(LIMIT + 1)
            else:
                import xbmcvfs
                path = xbmcvfs.translatePath(uri)
                with open(path, 'rb') as f:data = f.read(LIMIT + 1)
        else:data = read(uri)
        h, torrent_name = torrent_hash(data, with_name=True)
        name = name or torrent_name
    if len(h) != 40 or any(c not in '0123456789abcdefABCDEF' for c in h):
        raise ValueError('The selected torrent has no supported info-hash')
    return dict(q, hash=h.lower(), name=name)


def route(url,quiet=False,request_id=None):
    """True means consumed (queued, cancelled or error). False means ordinary browsing."""
    # Test the route before importing Kodi APIs; don't affect Elementum browsing.
    p = urllib.parse.urlsplit(url)
    if p.path.rstrip('/') not in ('/play', '/download'):return False
    import xbmcaddon, xbmcgui, xbmcvfs
    import debrid_drive, drivelibrary, notices
    dialog = xbmcgui.Dialog()
    try:
        choice = selected(url)
        if choice is None:return False
        if not xbmcaddon.Addon('plugin.video.umbrella').getSetting('alldebridtoken'):
            raise RuntimeError('Sign in to AllDebrid in Umbrella › Accounts first.')
        # The Drive add-on owns its account registry; use the same registry as the service.
        common = xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
        import sys
        if common not in sys.path:sys.path.append(common)
        from clouddrive.common.account import AccountManager
        accounts = AccountManager(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.googledrive').getAddonInfo('profile')))
        if not accounts.get_accounts():raise RuntimeError('Sign in to Google Drive first.')
        profile = xbmcvfs.translatePath('special://profile/')
        try:home = xbmcgui.Window(10000)
        except Exception:home = None
        auto = auto_season(home,choice=choice) if home is not None else None
        if request_id and (not auto or auto.get('request_id')!=request_id):
            _refused('no matching automatic request' if not auto else 'another request id')
            return True
        # Build Season already leaves out the episodes on the phone or Drive (season_sources), and a pack's torrent
        # name carries no episode: matching it against the Library took any Naruto copy for this episode (owner log
        # 5169a460, build 290). Only a hand-picked version is checked here.
        existing = None if auto is not None else existing_url(profile,choice)
        if existing:
            import xbmc
            xbmc.executebuiltin('PlayMedia(%s)'%existing)
            return True
        import transfer_control
        held=transfer_control.paused(profile,'up')
        if auto is None and held:
            mode=ask(dialog,'Uploads are paused',[('Download now','Uploads resume'),('Download and watch','Uploads resume; plays when ready'),
                                                   ('Keep it queued','Uploads stay paused')])
            if mode in (0,1):transfer_control.set_paused(profile,'up',False)
            elif mode==2:mode=0
        else:
            mode = auto.get('mode', 0) if auto is not None else ask(dialog, 'Save to Google Drive', [('Download only', 'Saved to Google Drive · watch any time'), ('Download and watch', 'Plays as soon as it is ready on Drive')])
        if mode < 0:return True
        if auto is None and home is not None:
            try:home.setProperty('KodiIOS.LastSaveMode', str(mode))   # the rest of a season reuses it
            except Exception:pass
        name = choice['name'] or choice['hash']
        info = drivelibrary.parse(name)
        kind = 'episode' if choice.get('episode') else ('season' if choice.get('season') else debrid_drive.kind_of(name))
        tracked=(auto or {}).get('target') or {}
        if not tracked and home is not None:
            import episode_watch
            pick=episode_watch.selection(home,choice)
            tracked={'tmdb':pick.get('show_tmdb'),'season':pick.get('season'),'episode':pick.get('episode')}
        job = debrid_drive.queue(profile, {'id':choice['hash'], 'name':name}, kind,
                                 info.get('title') or drivelibrary.display_title(name),
                                 choice.get('season') or info.get('season') or tracked.get('season') or '',
                                 choice.get('episode') or info.get('episode') or '', watch=mode == 1,show_tmdb=tracked.get('tmdb'))
        try:
            import xbmc,diagnostics,transfer_control
            # Roadmap B.11: this runs in Elementum's interpreter; join the app's session so the line names the build.
            try:diagnostics.attach(xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path'),profile)
            except Exception:pass
            diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'download_queue','saved',kind=kind,
                              status=job.get('status'),uploads_paused=transfer_control.paused(profile,'up'),
                              pending_jobs=sum(j.get('status') not in ('done','failed') for j in debrid_drive.load(profile).get('jobs',[])))
        except Exception:pass  # logging must never undo a saved download
        if auto is not None and home is not None:
            import json
            home.setProperty('KodiIOS.AutoPick.Queued',json.dumps({'request_id':auto.get('request_id'),'queued':True}))
        if auto is None and home is not None and kind in ('episode','season'):
            try:
                import episode_watch
                episode_watch.remember_selection(profile,home,choice,job['title'])
            except Exception:pass  # following a show must not undo its confirmed download
        replaced = None if request_id else replacing(xbmcgui.Window(10000))
        if replaced:
            # Library status › "Find a version without converting": the AV1 copy stops converting now and goes to Drive's
            # bin once this copy is on Drive (owner, build 185: "it needs to end the conversion and begin the download").
            import prepare_downloads
            prepare_downloads.request(profile, 'replace', replaced)
        if auto is None:
            import transfer_control
            held=transfer_control.paused(profile,'up')
            status='Queued · uploads paused' if held else 'Queued for Google Drive'
            detail='Resume uploads in Library status to start' if held else ('will play after preparation' if mode == 1 else 'AllDebrid → Drive → Prepare')
            notices.note('download', status, '%s · %s' % (job['title'],detail))
            dialog.notification('Download', status, xbmcgui.NOTIFICATION_INFO, 4000)
    except Exception as error:
        # Transport errors can contain signed URLs. Only our own plain errors are displayed.
        message = str(error) if isinstance(error, (ValueError, RuntimeError)) else 'Could not queue this torrent (%s).' % type(error).__name__
        if 'http://' in message or 'https://' in message:message = 'Could not read the selected torrent metadata.'
        if quiet:
            import xbmc,diagnostics
            diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'episode_watch','queue_deferred',error=type(error).__name__)
        else:dialog.ok('Download to Google Drive', message)
    return True


def same_pick(picked, chosen):
    """The picker's version and Elementum's selection are the same torrent. Owner log 15e6cbc4 (build 288, Naruto
    Shippuden): the picker names a file inside a pack by its full path ('Naruto Shippuden (001-500) [...]/... Episode
    001 Homecoming.mkv'), Elementum's selection only by the torrent ('Naruto Shippuden (001-500) [...]'); every episode
    was refused and the season said '0 episodes added'."""
    import re
    norm = lambda s: re.sub(r'\s+', ' ', str(s or '')).strip().lower()
    a, b = norm(picked), norm(chosen)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return len(short) >= 8 and long_.startswith(short) and long_[len(short)] in '/ ._-[('


def refusal(wanted, selected, choice):
    """Why Elementum's selection is not the automatic season request's pick ('' when it is). Owner log 5169a460 (build
    290): every Build Season episode was refused without a word in the log. Season and episode are compared only when
    Elementum's link carries them."""
    if selected.get('request_id') != wanted.get('request_id'):
        return 'another request'
    if not selected.get('found'):
        return 'picker found nothing'
    if not same_pick(selected.get('name'), choice.get('name')):
        return 'different version'
    for k in ('season', 'episode'):
        have = str(choice.get(k) or '')
        if have and have.lstrip('0') != str(wanted['target'].get(k) or '').lstrip('0'):
            return 'different ' + k
    return ''


def _refused(why):
    try:
        import xbmc
        xbmc.log('Kodi iOS cloud: automatic pick refused (%s)' % why, xbmc.LOGINFO)
    except Exception:
        pass


def auto_season(window, now=None,choice=None):
    """download.py's automatic season request (deck_picker.AUTO_PICK) while it lasts, else None."""
    import json, time
    try:
        raw = window.getProperty('KodiIOS.AutoPick')
        wanted = json.loads(raw) if raw else None
        if wanted and float(wanted.get('until', 0)) >= (time.time() if now is None else now):
            if wanted.get('target') and choice is not None:
                selected=json.loads(window.getProperty('KodiIOS.AutoPick.Result') or '{}')
                why=refusal(wanted,selected,choice)
                if why:
                    _refused(why)
                    return None
            return wanted
    except Exception:
        pass
    return None


REPLACING = 'KodiIOS.Replacing'


def replacing(window, now=None):
    """The Drive id of the video a "without converting" search replaces (set by Library status, 15 minutes), once."""
    import time
    raw = window.getProperty(REPLACING) or ''
    ident, _, at = raw.partition('|')
    window.clearProperty(REPLACING)
    try:
        fresh = (time.time() if now is None else now) - float(at) < 15 * 60
    except ValueError:
        fresh = False
    return ident if ident and fresh else ''


def existing_url(profile,choice):
    """Skip the download question only for a verified, prepared copy at the selected quality."""
    import prepare_downloads as prep
    import drivelibrary
    name=choice['name']
    if not name:return None
    key=drivelibrary.media_key(name)
    if key is None:return None
    items=(prep.load(profile).get('library') or {}).get('items') or []
    matches=[e for e in items if e.get('state')=='ready' and drivelibrary.media_key(e.get('name',''))==key
             and drivelibrary.media_year(e.get('name',''))==drivelibrary.media_year(name)
             and drivelibrary.quality(e.get('name',''))>=drivelibrary.quality(name)]
    if not matches:return None
    try:
        drive,driveid=drivelibrary.client()
        if drive and driveid:
            for item in matches:
                if prep.playback_ready(profile,prep.metadata(drive,item['id'])):return drivelibrary.play_url(driveid,item['id'])
    except Exception:pass
    return None
