"""RunScript(service.kodi.ios.bootstrap,library_repair_page,tmdb=..,title=..,season=..,episode=..,quality=..):
L5 automatic Repair (library_repair.py) in its own script, with a notification when it is queued or not found."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))


def run(argv):
    import xbmc
    import xbmcgui
    import library_repair
    import season_sources
    a = library_repair.args(argv[1:])
    tries = library_repair.tries_for(a.get('quality'))
    if a.get('cancel'):
        # Pick Better Versions: the old picks leave the queue first (the copy loop drops cancelled hashes), so the new
        # pick is never taken for the episode already waiting.
        import time
        import xbmcvfs
        import debrid_drive
        import transfer_control
        profile = xbmcvfs.translatePath('special://profile/')
        hashes = [h for h in a['cancel'].split(';') if h]
        for h in hashes:
            transfer_control.cancel_copy(profile, h)
        monitor = xbmc.Monitor()
        for _ in range(90):
            waiting = [j for j in debrid_drive.load(profile).get('jobs', [])
                       if str(j.get('hash', '')).lower() in hashes and j.get('status') not in ('done', 'failed')]
            if not waiting or monitor.waitForAbort(1):
                break
        xbmc.log('Kodi iOS repair: %d old picks cancelled before picking again' % len(hashes), xbmc.LOGINFO)
    dialog = xbmcgui.Dialog()
    home = xbmcgui.Window(10000)
    found = missed = held = 0
    pending = library_repair.episodes_arg(a.get('episodes'))
    tmdb = a.get('tmdb', '')
    keys = lambda pairs: ['%s:%d:%d' % (tmdb, s_, e_) for s_, e_ in pairs]
    # DEC-047 board B2: the show page shows "Looking for 1080p…" on every episode this run will look up, at once, and its
    # ✕ (KodiIOS.RepairCancel) stops one of them.
    library_repair.mark_searching(home, keys(pending), add=True)
    quality_name = season_sources.QUALITY_NAMES.get(a.get('quality'), a.get('quality') or '')
    import xbmcvfs
    import quality_choice
    profile = xbmcvfs.translatePath('special://profile/')
    many = len(pending) > 1
    import time as _time
    # ISSUE-268: several episodes are one request; their downloads' messages join one entry. One episode keeps its own.
    batch = 'repair:%s:%d' % (tmdb, int(_time.time())) if many else ''
    # DEC-049 board A (owner screenshot, build 415: Notifications filled with "Repair" lines): one line for a run of several
    # episodes, not two per episode.
    if many:
        dialog.notification('Repair', 'Looking up %d episodes%s' % (len(pending), ' at %s' % quality_name if quality_name else ''),
                            xbmcgui.NOTIFICATION_INFO, 3000)
    try:
      for season, episode in pending:
        key = keys([(season, episode)])[0]
        label = '%s S%02dE%02d' % (a.get('title', ''), season, episode)
        if library_repair.cancelled(home, key):
            library_repair.mark_searching(home, [key], add=False)
            dialog.notification('Repair', '%s: stopped' % label, xbmcgui.NOTIFICATION_INFO, 3000)
            continue
        if quality_choice.state(profile, tmdb, season) in ('asking', 'looking'):
            # The season waits for the owner's answer (its notice is up); nothing is searched for it meanwhile.
            library_repair.mark_searching(home, [key], add=False)
            quality_choice.add_episode(profile, tmdb, season, episode)
            held += 1
            continue
        if not many:
            dialog.notification('Repair', 'Looking up %s again%s' % (label, ' at %s' % quality_name if quality_name else ''), xbmcgui.NOTIFICATION_INFO, 3000)
        request = lambda *args, **kw: season_sources.request(*args, cancel=lambda: library_repair.cancelled(home, key), batch=batch, **kw)
        state, detail = library_repair.repair(request, home, tmdb, a.get('title', ''),
                                              season, episode, tries, log=lambda text: xbmc.log(text, xbmc.LOGINFO))
        library_repair.mark_searching(home, [key], add=False)
        if state == 'queued':
            found += 1
            if not many:
                dialog.notification('Repair', '%s is downloading%s' % (label, '' if detail == 'any' else ' · %s' % season_sources.QUALITY_NAMES.get(detail, detail)),
                                    xbmcgui.NOTIFICATION_INFO, 5000)
        elif state == 'held':
            held += 1   # one notice for the season (DEC-049 board A), not one per episode
        elif library_repair.cancelled(home, key):
            dialog.notification('Repair', '%s: stopped' % label, xbmcgui.NOTIFICATION_INFO, 3000)
        else:
            missed += 1
            if not many:
                dialog.notification('Repair', '%s: %s' % (label, detail), xbmcgui.NOTIFICATION_WARNING, 6000)
    finally:
        library_repair.mark_searching(home, keys(pending), add=False)
        library_repair.clear_cancel(home, keys(pending))
    if found + missed + held > 1:
        xbmc.log('Kodi iOS repair: %d queued, %d not found, %d wait for the quality choice' % (found, missed, held), xbmc.LOGINFO)
    if many:
        words = [w for w in ('%d downloading' % found if found else '', '%d not found' % missed if missed else '',
                             '%d wait for your choice' % held if held else '') if w]
        dialog.notification('Repair', '%s · %s' % (a.get('title', ''), ' · '.join(words) or 'nothing to do'),
                            xbmcgui.NOTIFICATION_WARNING if missed else xbmcgui.NOTIFICATION_INFO, 6000)

if __name__ == '__main__':
    run(sys.argv)
