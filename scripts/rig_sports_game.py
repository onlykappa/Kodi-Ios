"""Run inside the desktop Kodi rig: opens the real game page (sports_game.run, with the Game info below the sources) for a LIVE ESPN game: RunScript(this, NBA).
The sources are sample rows (see rig_sports_hero._rows) so every state of the rows shows; the facts come from ESPN as in the app. Evidence class: desktop Kodi rig."""
import os
import sys
import time

import xbmcaddon

here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, 'resources', 'lib'))
import sports_game
import sports_provider

league = (sys.argv[1] if len(sys.argv) > 1 else 'NBA').upper()
provider = sports_provider.get()
pool = list(provider.live_games()) + list(provider.upcoming_games())
game = next(g for g in pool if g['league'] == league)
sys.argv = ['rig_sports_hero.py', 'rows']
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rig_sports_hero.py')).read().split("def _rows():")[1].split("GAMES['rows']")[0]
ns = {'time': time}
exec("def _rows():" + src, ns)
game = dict(game, sources=ns['_rows']())
sports_game.run(game, provider=provider)
