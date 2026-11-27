"""Run inside the desktop Kodi rig (RunScript with this file's path, argument f1 | long | team | upcoming): opens the real game page (IOSSportsGame.xml) with sample data so the
hero can be looked at. Sample data only; no provider, no network.  usage (inside Kodi): RunScript(/path/to/rig_sports_hero.py, f1)"""
import os
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, 'resources', 'lib'))
import sports_game

now = time.time()
SRC = [{'id': 's1', 'addon': 'IndependentLiveFeeds', 'quality': '1080p', 'language': 'English', 'tag': 'best', 'play': '{}', 'label': 'LiveFeeds'}]
GAMES = {
    'f1': {'id': 'espn:F1:1', 'league': 'F1', 'league_name': 'Formula 1', 'sport': 'Motorsport', 'state': 'live', 'start': now - 1800, 'joiner': 'vs',
           'away': {'name': 'Qatar Airways Qatar Grand Prix', 'code': 'F1', 'score': None, 'crest': 'https://a.espncdn.com/i/teamlogos/leagues/500-dark/f1.png'}, 'home': {'name': '', 'code': '', 'score': None}, 'clock': 'Practice 2', 'sources': SRC},
    'long': {'id': 'espn:PGA:1', 'league': 'PGA', 'league_name': 'PGA Tour', 'sport': 'Golf', 'state': 'upcoming', 'start': now + 7200, 'joiner': 'vs',
             'away': {'name': 'The RSM Classic presented by Sea Island Resort and Hotels', 'code': 'PGA', 'score': None, 'crest': 'https://a.espncdn.com/i/teamlogos/leagues/500-dark/pgatour.png'}, 'home': {'name': '', 'code': '', 'score': None}, 'sources': []},
    'team': {'id': 'espn:NFL:1', 'league': 'NFL', 'league_name': 'NFL', 'sport': 'American football', 'state': 'live', 'start': now - 3600, 'joiner': 'at',
             'away': {'name': 'Kansas City Chiefs', 'short': 'Chiefs', 'code': 'KC', 'score': 14, 'color': 'E31837'}, 'home': {'name': 'Buffalo Bills', 'short': 'Bills', 'code': 'BUF', 'score': 17, 'color': '00338D'}, 'clock': '', 'sources': SRC},
}
GAMES['upcoming'] = dict(GAMES['f1'], state='upcoming', start=now + 5400, sources=[])
game = GAMES[(sys.argv[1] if len(sys.argv) > 1 else 'f1')]
import sports_logos
import xbmcvfs
crests = sports_logos.crests(xbmcvfs.translatePath('special://profile/'), [game['away'].get('crest', ''), game['home'].get('crest', '')])
if not crests:   # the rig's Kodi python cannot reach ESPN: use a copy fetched outside Kodi (rig only, never committed)
    for url in [game['away'].get('crest', '')]:
        local = '/tmp/claude-0/rig/crest-%s.png' % ('f1' if 'f1' in url else 'pga')
        if url and os.path.isfile(local):
            crests[url] = local
props, _sources = sports_game.model(game, now, 0, crests=crests)


class Page(xbmcgui.WindowXMLDialog):
    def onInit(self):
        for key, value in props.items():
            self.setProperty(key, value if isinstance(value, str) else str(value))


path = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
Page('IOSSportsGame.xml', path, 'Default', '1080i').doModal()
