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
    tries = [a['quality'], None] if a.get('quality') else [None]
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
    found = missed = 0
    for season, episode in library_repair.episodes_arg(a.get('episodes')):
        label = '%s S%02dE%02d' % (a.get('title', ''), season, episode)
        dialog.notification('Repair', 'Looking up %s again' % label, xbmcgui.NOTIFICATION_INFO, 3000)
        state, detail = library_repair.repair(season_sources.request, home, a.get('tmdb', ''), a.get('title', ''),
                                              season, episode, tries, log=lambda text: xbmc.log(text, xbmc.LOGINFO))
        if state == 'queued':
            found += 1
            dialog.notification('Repair', '%s is downloading%s' % (label, '' if detail == 'any' else ' · %s' % season_sources.QUALITY_NAMES.get(detail, detail)),
                                xbmcgui.NOTIFICATION_INFO, 5000)
        else:
            missed += 1
            dialog.notification('Repair', '%s: %s' % (label, detail), xbmcgui.NOTIFICATION_WARNING, 6000)
    if found + missed > 1:
        xbmc.log('Kodi iOS repair: %d queued, %d not found' % (found, missed), xbmc.LOGINFO)

if __name__ == '__main__':
    run(sys.argv)
