"""Run inside the desktop Kodi rig (RunScript with this file's path, argument f1 | long | team | upcoming): opens the real game page (IOSSportsGame.xml) with sample data so the
hero can be looked at. Sample data only; no provider, no network.  usage (inside Kodi): RunScript(/path/to/rig_sports_hero.py, f1)   or live ESPN data: RunScript(..., espn:F1) / espn:NBA / espn"""
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
def _rows():
    """Sample source rows in every state of the mockup (checking, measured, slow, failed, remembered): the probe results are put in by hand, no network."""
    import json
    import sports_probe
    import sports_livefeeds
    import sports_p720
    import sports_fawa
    def own(name, n):
        return json.dumps({'e': name, 'l': {'address': 'https://x/%d' % n}})
    live, p72, fawa = own(sports_livefeeds.NAME, 1), own(sports_p720.NAME, 2), own(sports_fawa.NAME, 3)
    sports_probe._results[live] = (time.time() - 12, {'ok': True, 'height': 1080, 'fps': 30, 'kbps': 4200})
    sports_probe._results[p72] = (time.time() - 12, {'ok': True, 'kbps': 1400, 'speed': 1.1})
    crew = json.dumps({'e': 'TheCrewRoute', 'l': {}})
    now = time.time()
    return [{'id': 'a', 'addon': 'LiveFeeds', 'quality': '', 'language': '', 'tag': 'best', 'play': live, 'seen': {'ok': 5, 'ok_at': now - 7200, 'height': 1080, 'fps': 30, 'kbps': 4800}},
            {'id': 'b', 'addon': '720pStream', 'quality': '', 'language': '', 'tag': 'good', 'play': p72},
            {'id': 'c', 'addon': 'FawaNews', 'quality': '', 'language': '', 'play': fawa},
            {'id': 'd', 'addon': 'Crew MUT', 'quality': '720p', 'language': 'English', 'play': crew, 'seen': {'ok': 3, 'ok_at': now - 90000, 'height': 720, 'fps': 30, 'kbps': 2400}},
            {'id': 'e', 'addon': 'Loop ReedStreams', 'quality': '', 'language': '', 'play': crew + ' ', 'seen': {'fail': 2, 'fail_at': now, 'dead': True}},
            {'id': 'f', 'addon': 'Loop Guide', 'quality': '', 'language': '', 'play': crew + '  ', 'also': ['Sports Hub']}]


GAMES['rows'] = dict(GAMES['team'], sources=[])
GAMES['upcoming'] = dict(GAMES['f1'], state='upcoming', start=now + 5400, sources=[])
mode = sys.argv[1] if len(sys.argv) > 1 else 'f1'
if mode.startswith('espn'):
    # LIVE data, exactly as the app gets it: the app's own provider reads ESPN (espn / espn:F1 / espn:NBA ...): the first live game of that league, else the first upcoming one.
    import sports_provider
    provider = sports_provider.get()
    wanted = mode.split(':', 1)[1].upper() if ':' in mode else ''
    pool = list(provider.live_games()) + list(provider.upcoming_games())
    game = next((g for g in pool if not wanted or g['league'] == wanted), None) or pool[0]
    xbmc.log('RIGHERO live game %s %s %s' % (game['id'], game['league'], game['state']), xbmc.LOGINFO)
else:
    game = GAMES[mode]
import sports_logos
import xbmcvfs
crests = sports_logos.crests(xbmcvfs.translatePath('special://profile/'), [game['away'].get('crest', ''), game['home'].get('crest', '')])
if not crests:   # the rig's Kodi python cannot reach ESPN: use a copy fetched outside Kodi (rig only, never committed)
    for url in [game['away'].get('crest', '')]:
        local = '/tmp/claude-0/rig/crest-%s.png' % ('f1' if 'f1' in url else 'pga')
        if url and os.path.isfile(local):
            crests[url] = local
if mode == 'rows':
    game = dict(game, sources=_rows())
props, _sources = sports_game.model(game, now, 0, crests=crests)


class Page(xbmcgui.WindowXMLDialog):
    def onInit(self):
        for key, value in props.items():
            self.setProperty(key, value if isinstance(value, str) else str(value))


path = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
Page('IOSSportsGame.xml', path, 'Default', '1080i').doModal()
