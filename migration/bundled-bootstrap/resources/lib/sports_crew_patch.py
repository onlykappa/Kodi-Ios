"""Let Crew's sports menus list their events without Crew's own window open (owner, 2026-11-20: no Crew UI at all).

Crew's sports menus build their event lists with code the menu file carries, and that code starts with a check: `Container.PluginName` must be
`plugin.video.thecrew`, else it returns nothing. With Crew's window no longer opened under Sports the check failed and every event list came back
empty (ISSUE-396). While a game's source search runs, the Home property SCAN is set, and this one-line change to the pinned Crew module makes
that label read as Crew. Nothing else of Crew changes, and the change is made only to the exact pinned file (version and line both checked);
any other version or file is left alone.
"""
import os

SCAN = 'KodiIOS.SportsCrewScan'
MODULE = 'script.module.thecrew'
VERSION = '3.2.29'
RELATIVE = os.path.join('lib', 'resources', 'lib', 'modules', 'control.py')
ORIGINAL = 'infoLabel = xbmc.getInfoLabel\n'
MARK = '# Kodi iOS Sports scan'
PATCHED = '''def infoLabel(label):  # Kodi iOS Sports scan: while a game's source search runs, Crew's menus see their own add-on as the container
    if label == 'Container.PluginName':
        try:
            import xbmcgui
            if xbmcgui.Window(10000).getProperty('%s'):
                return 'plugin.video.thecrew'
        except Exception:
            pass
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
    result = apply(folders())
    if result not in ('patched', 'already'):
        log('crew: scan patch left alone (%s)' % result)
    elif result == 'patched':
        log('crew: scan patch applied')
    return result
