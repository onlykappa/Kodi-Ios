"""The show page's bell (mockup board G): one sheet with two switches for this show, tap a row's switch to flip it; Done closes.
RunScript(service.kodi.ios.bootstrap,anticipated_bell,tmdb=...,title=...). Logic is resources/lib/anticipated.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import anticipated as bell


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    import choice_sheet
    import episode_watch
    import source_match
    args = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    tmdb, title = args.get('tmdb', '').strip(), args.get('title', '').strip()
    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()
    info = None
    try:
        key = source_match.tmdb_key()
        info = bell.Lookup(key).upcoming(tmdb) if key and tmdb.isdigit() else None
    except Exception as error:
        xbmc.log('Kodi iOS bell: lookup failed (%s)' % type(error).__name__, xbmc.LOGWARNING)
    if not info:
        dialog.ok('New episodes', 'There is no upcoming episode for this show right now.')
        return
    home = xbmcgui.Window(10000)
    # G3 (owner-approved): one sheet with two real switches that flip in place, and Done. Each flip is saved at once.

    def toggle(index):
        state = bell.switches(profile, tmdb)
        which = 'alert' if index == 0 else 'auto'
        preference = None
        if which == 'auto' and not state['auto']:
            try:
                preference = episode_watch.library_preference(profile, title)
            except Exception:
                preference = {'quality': '1080p'}
        state = bell.flip(profile, tmdb, title, which, info, preference)
        if home.getProperty(bell.PROP_TMDB) == tmdb:
            home.setProperty(bell.PROP_ON, 'true' if state['on'] else '')
        return state[which]

    choice_sheet.choose({'heading': 'New episodes \u00b7 %s' % (title or 'this show'), 'sub': bell.label(info),
                         'rows': bell.rows(bell.switches(profile, tmdb)), 'button': 'Done',
                         'foot': 'Alert on and downloads off: you are told, nothing is downloaded.'}, xbmcgui=xbmcgui, toggle=toggle)


if __name__ == '__main__':
    run()
