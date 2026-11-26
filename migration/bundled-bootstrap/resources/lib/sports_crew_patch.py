"""Let Crew's sports menus work without any Crew window or dialog (owner, 2026-11-20: no Crew UI at all).

Two things in Crew get in the way, and both come from code the sports menu files carry (downloaded at run time from github.com/posadka/xmls2,
sports/<league>/<league>.xml), not from the add-on itself:
 1. Event lists start with `if not Container.PluginName == 'plugin.video.thecrew': return`. With Crew's window no longer opened under Sports the
    lists came back empty (ISSUE-396).
 2. Opening an event's link (a play) shows Crew's own progress dialog, "THE CREW SPORTS / The Crew Is Finding Your Event..." (ISSUE-397).
While the Home property SCAN holds a time in the future (a game's source search sets it, and so does a Sports play), one change to the pinned Crew
module makes the label read as Crew and replaces Crew's progress dialog with a silent stand-in. At any other time Crew behaves as it always did.
The change is made only to the exact pinned file (version and line both checked); any other version or file is left alone.
"""
import os

SCAN = 'KodiIOS.SportsCrewScan'
MODULE = 'script.module.thecrew'
VERSION = '3.2.29'
RELATIVE = os.path.join('lib', 'resources', 'lib', 'modules', 'control.py')
ORIGINAL = 'infoLabel = xbmc.getInfoLabel\n'
MARK = '# Kodi iOS Sports scan'
PATCHED = '''def _kodi_ios_sports_scan():  # Kodi iOS Sports scan: true while a Sports source search or play is running (SCAN holds a time in the future)
    try:
        import time
        import xbmcgui
        return float(xbmcgui.Window(10000).getProperty('%s') or 0) > time.time()
    except Exception:
        return False


class _KodiIosSilentProgress:  # stands in for xbmcgui.DialogProgress: Crew's "Finding Your Event" box is never drawn
    def create(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def iscanceled(self):
        return False

    def isFinished(self):
        return False


if _kodi_ios_sports_scan():
    try:
        import xbmcgui as _kodi_ios_gui
        _kodi_ios_gui.DialogProgress = _KodiIosSilentProgress
        _kodi_ios_gui.DialogProgressBG = _KodiIosSilentProgress   # Crew's own control.py makes both boxes next, so those are silent too
    except Exception:
        pass


def infoLabel(label):
    if label == 'Container.PluginName' and _kodi_ios_sports_scan():
        return 'plugin.video.thecrew'
    return xbmc.getInfoLabel(label)
''' % SCAN


def _version(folder):
    try:
        text = open(os.path.join(folder, 'addon.xml'), encoding='utf-8').read()
    except OSError:
        return ''
    marker = 'version="'
    start = text.find(marker, text.find('<addon '))
    return text[start + len(marker):text.find('"', start + len(marker))] if start >= 0 else ''


def apply(folders):
    """Patch the first listed Crew module folder that is the pinned version. Returns 'patched', 'already', or a short reason it was left alone."""
    reason = 'no Crew module folder'
    for folder in folders:
        path = os.path.join(folder, RELATIVE)
        if not os.path.isfile(path):
            continue
        if _version(folder) != VERSION:
            reason = 'Crew module is not the pinned version'
            continue
        try:
            source = open(path, encoding='utf-8').read()
        except OSError:
            reason = 'Crew module cannot be read'
            continue
        if MARK in source:
            return 'already'
        if source.count(ORIGINAL) != 1:
            reason = 'Crew module does not match the pinned file'
            continue
        try:
            open(path, 'w', encoding='utf-8').write(source.replace(ORIGINAL, PATCHED, 1))
        except OSError:
            reason = 'Crew module cannot be written'
            continue
        return 'patched'
    return reason


CLIENT_RELATIVE = os.path.join('lib', 'resources', 'lib', 'modules', 'client.py')
CLIENT_ANCHOR = "def parseHTML(html, name='', attrs=None, ret=False):\n"
CLIENT_MARK = '# Kodi iOS parseDOM'
CLIENT_ADDED = ("parseDOM = parseDom  # Kodi iOS parseDOM: Crew's runtime stream code (generic streamer, rapidmoviez and others) calls client.parseDOM, "
                "which client.py never defined: \"Streamer [generic] failed ... has no attribute 'parseDOM'\" (owner log 551591c4)\n\n\n")


def apply_client(folders):
    """Give Crew's client module the `parseDOM` name its own downloaded streamers call (it defines only `parseDom`). Pinned version and the exact anchor line
    are checked, as for the scan patch. Returns 'patched', 'already', or a short reason it was left alone."""
    reason = 'no Crew module folder'
    for folder in folders:
        path = os.path.join(folder, CLIENT_RELATIVE)
        if not os.path.isfile(path):
            continue
        if _version(folder) != VERSION:
            reason = 'Crew module is not the pinned version'
            continue
        try:
            source = open(path, encoding='utf-8').read()
        except OSError:
            reason = 'Crew client cannot be read'
            continue
        if CLIENT_MARK in source or 'parseDOM =' in source:
            return 'already'
        if source.count(CLIENT_ANCHOR) != 1 or 'def parseDom(' not in source:
            reason = 'Crew client does not match the pinned file'
            continue
        try:
            open(path, 'w', encoding='utf-8').write(source.replace(CLIENT_ANCHOR, CLIENT_ADDED + CLIENT_ANCHOR, 1))
        except OSError:
            reason = 'Crew client cannot be written'
            continue
        return 'patched'
    return reason


DNS_MARK = '# Kodi iOS dns override'
DNS_ADDED = '''

# Kodi iOS dns override: a host this phone's DNS answers wrongly (dns_override.py in the service lists it in dns-overrides.json) is connected by the working address
# DNS over HTTPS gave; the name, and so TLS's certificate check, stays the host's own. Any other name, and any failure here, goes to the normal lookup.
def _kodi_ios_dns():
    try:
        import json
        import os
        import socket
        import time
        import xbmcvfs
        real = socket.getaddrinfo
        if getattr(real, '_kodi_ios', False):
            return
        where = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap'), 'dns-overrides.json')
        cache = [None, {}]

        def table():
            try:
                stamp = os.path.getmtime(where)
            except OSError:
                cache[:] = [None, {}]
                return cache[1]
            if stamp != cache[0]:
                try:
                    with open(where, encoding='utf-8') as handle:
                        data = json.load(handle)
                except Exception:
                    data = {}
                cache[:] = [stamp, data if isinstance(data, dict) else {}]
            return cache[1]

        def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            try:
                entry = table().get(str(host).lower())
                if entry and time.time() - float(entry.get('at', 0)) < 43200:
                    ip = str(entry['ip'])
                    v6 = ':' in ip
                    if family in (0, socket.AF_INET6 if v6 else socket.AF_INET):
                        number = int(port or 0)
                        return [(socket.AF_INET6 if v6 else socket.AF_INET, type or socket.SOCK_STREAM, proto or 6, '',
                                 (ip, number, 0, 0) if v6 else (ip, number))]
            except Exception:
                pass
            return real(host, port, family, type, proto, flags)
        getaddrinfo._kodi_ios = True
        socket.getaddrinfo = getaddrinfo
    except Exception:
        pass


_kodi_ios_dns()
'''


def apply_dns(folders):
    """Append the name-lookup wrapper to Crew's control module (pinned version and file checked; added once). Returns 'patched', 'already', or a short reason."""
    reason = 'no Crew module folder'
    for folder in folders:
        path = os.path.join(folder, RELATIVE)
        if not os.path.isfile(path):
            continue
        if _version(folder) != VERSION:
            reason = 'Crew module is not the pinned version'
            continue
        try:
            source = open(path, encoding='utf-8').read()
        except OSError:
            reason = 'Crew module cannot be read'
            continue
        if DNS_MARK in source:
            return 'already'
        try:
            open(path, 'w', encoding='utf-8').write(source.rstrip('\n') + '\n' + DNS_ADDED)
        except OSError:
            reason = 'Crew module cannot be written'
            continue
        return 'patched'
    return reason


def folders():
    """Where Kodi keeps this add-on on the phone and on the desktop rig."""
    out = []
    try:
        import xbmcvfs
        for base in ('special://home/addons/', 'special://xbmc/addons/'):
            out.append(xbmcvfs.translatePath(base + MODULE))
    except Exception:
        pass
    return out


def ensure(log=lambda text: None):
    client = apply_client(folders())
    if client == 'patched':
        log('crew: parseDOM alias added')
    elif client != 'already':
        log('crew: parseDOM alias left alone (%s)' % client)
    dns = apply_dns(folders())
    if dns == 'patched':
        log('crew: name-lookup wrapper added (dns_override)')
    elif dns != 'already':
        log('crew: name-lookup wrapper left alone (%s)' % dns)
    result = apply(folders())
    if result not in ('patched', 'already'):
        log('crew: scan patch left alone (%s)' % result)
    elif result == 'patched':
        log('crew: scan patch applied')
    return result


def mark(home, seconds):
    """Say that a Sports search or play is running for the next `seconds` seconds (a time, so a crash can never leave it on)."""
    import time
    try:
        home.setProperty(SCAN, str(time.time() + seconds))
    except Exception:
        pass
