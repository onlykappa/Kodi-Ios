"""Run inside the desktop Kodi rig: opens the real game Info window (IOSSportsGameFacts) for a LIVE ESPN game, the data the app reads.
usage (inside Kodi): RunScript(/path/to/rig_sports_info.py, NFL|NBA|...[, tab]). If the rig's Python cannot reach ESPN, a summary saved outside Git
(KODI_RIG_HOME/summary-<LEAGUE>.json, rig only) is used instead. Evidence class: desktop Kodi rig."""
import json
import os
import sys
import time

import xbmc
import xbmcaddon

here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, 'resources', 'lib'))
import sports_game_detail
import sports_game_facts
import sports_provider

league = (sys.argv[1] if len(sys.argv) > 1 else 'NFL').upper()
home = os.environ.get('KODI_RIG_HOME', '/tmp/claude-0/rig')
saved = os.path.join(home, 'game-%s.json' % league)
if os.path.isfile(saved):
    game = json.load(open(saved))
else:
    provider = sports_provider.get()
    pool = list(provider.live_games()) + list(provider.upcoming_games())
    game = next(g for g in pool if g['league'] == league)
xbmc.log('RIGINFO game %s %s %s' % (game['id'], game['league'], game['state']), xbmc.LOGINFO)
offline = os.path.join(home, 'summary-%s.json' % league)
if os.path.isfile(offline):
    real = sports_game_detail.download
    def download(url, timeout=10):
        try:
            return real(url, timeout)
        except Exception:
            return json.load(open(offline))
    sports_game_detail.download = download
    sports_game_detail.fetch.__defaults__ = (download, time.time)


def drive():
    """Optional extra args after the tab: click=ID (tap a control) and scroll=N (move the list N rows), done from inside Kodi because the rig has no touch."""
    import threading
    steps = [a for a in sys.argv[2:] if '=' in a]
    def work():
        time.sleep(7)
        for step in steps:
            key, value = step.split('=')
            xbmc.executebuiltin('SendClick(%s)' % value if key == 'click' else 'SetFocus(9300)')
            if key == 'scroll':
                time.sleep(.3)
                xbmc.executebuiltin('Control.Move(9300,%s)' % value)
            time.sleep(2)
    threading.Thread(target=work, daemon=True).start()


drive()
sports_game_facts.run(game)
