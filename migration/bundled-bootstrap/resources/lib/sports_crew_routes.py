"""Sports catalog from The Crew's normal Kodi menus; playback stays in The Crew."""
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import sports_loop_routes as common

ADDON = 'plugin.video.thecrew'
NAME = 'TheCrewRoute'
# Only sports menus, never movie/TV/replay/account routes during discovery.
ACTIONS = {'nfl', 'nhl', 'nba', 'mlb', 'ncaa', 'ncaab', 'fifa', 'fullsites'}
MAX_FOLDERS = 24
MAX_DEPTH = 3
SCAN_BUSY = 'KodiIOS.SportsCrewListing'
OWNER = 'KodiIOS.SportsNativeOwner'


def _home():
    try:
        import xbmcgui
        return xbmcgui.Window(10000)
    except (ImportError, AttributeError):
        return None


def playback_requested():
    home = _home()
    if home and home.getProperty(OWNER):
        return True
    try:
        import xbmc
        return bool(xbmc.Player().isPlayingVideo())
    except (ImportError, AttributeError):
        return False


def wait_for_listing(timeout=10):
    import time
    home = _home()
    if home is None:
        return
    import xbmc
    began = time.monotonic()
    while home and home.getProperty(SCAN_BUSY):
        if time.monotonic() - began >= timeout:
            raise RuntimeError('Crew catalog is still finishing a request')
        xbmc.sleep(100)



def valid_route(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'plugin' and parsed.netloc == ADDON and not parsed.username and not parsed.password
    except (ValueError, TypeError):
        return False


def listing(path):
    if not valid_route(path):
        raise ValueError('invalid Crew route')
    import json, xbmc
    home = _home()
    if playback_requested():
        return []
    if home:
        home.setProperty(SCAN_BUSY, 'true')
    try:
        if playback_requested():
            return []
        reply = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0', 'id':1, 'method':'Files.GetDirectory',
                           'params':{'directory':path, 'media':'files', 'properties':['title']}})))
    finally:
        if home:
            home.clearProperty(SCAN_BUSY)
    if reply.get('error'):
        raise RuntimeError('Crew listing unavailable')
    return reply.get('result', {}).get('files', [])


def match_game(text, games):
    """Match both sides only against ESPN's own names/aliases, rejecting ambiguity."""
    import sports_merge
    pair = common.title_pair(text)
    if not pair:
        return None
    def team_matches(name, team):
        return any(sports_merge.same_team(name, alias) for alias in [team['name']] + team.get('aliases', []))
    matches = [game for game in games if
               (team_matches(pair[0], game['away']) and team_matches(pair[1], game['home'])) or
               (team_matches(pair[1], game['away']) and team_matches(pair[0], game['home']))]
    return matches[0] if len(matches) == 1 else None


class CrewSource:
    def __init__(self, title, route, games, read=listing):
        self.name = 'Crew ' + common.label(title)
        self.route, self.games, self.read = route, games, read

    def get_items(self):
        from sports_independent import Link
        pending, visited, emitted, items = [(self.route, 0, None)], set(), set(), []
        failures = 0
        while pending and len(visited) < MAX_FOLDERS and not playback_requested():
            route, depth, parent_game = pending.pop(0)
            if route in visited or not valid_route(route):
                continue
            visited.add(route)
            try:
                entries = self.read(route)
            except Exception:
                # A dead subfolder must not discard games from other sites.
                failures += 1
                continue
            for entry in entries[:512]:
                address = entry.get('file', '')
                title = common.label(entry.get('title') or entry.get('label') or '')
                if not valid_route(address) or any(word in title.lower().replace(' ', '') for word in common.SKIP_LABELS + ('search', 'foxy')):
                    continue
                pair = common.title_pair(title)
                game = match_game(title, self.games) if pair else parent_game
                if entry.get('filetype') == 'directory':
                    # Do not walk a different/ambiguous game under an inherited match.
                    if depth < MAX_DEPTH and (not pair or game):
                        if game is not None:
                            pending.insert(0, (address, depth + 1, game))
                        else:
                            pending.append((address, depth + 1, game))
                    continue
                if not game or address in emitted:
                    continue
                emitted.add(address)
                items.append(SimpleNamespace(title=game['away']['name']+' vs '+game['home']['name'],
                             league=game['league_name'], status='LIVE' if game['state']=='live' else '',
                             starttime=datetime.fromtimestamp(game['start']), links=[Link(address)]))
        import sports_jet
        sports_jet.log('jet: %s: %d folders, %d unavailable, %d matched streams' % (self.name, len(visited), failures, len(items)))
        return items


def discover(read=listing, schedule=None):
    if schedule is None:
        schedule = globals()['schedule']()
    # ESPN is authoritative for live status. Keep upcoming games in the
    # schedule, but do not walk Crew menus for events that have not started.
    live = [game for game in schedule if game.get('state') == 'live']
    if not live:
        return []
    entries = read('plugin://' + ADDON + '/?action=bluehat')
    sources, seen = [], set()
    league_codes = {game.get('league') or game.get('league_name') for game in live}
    league_actions = {'nfl':'NFL', 'nba':'NBA', 'nhl':'NHL', 'mlb':'MLB', 'ncaa':'NCAAF', 'ncaab':'NCAAB', 'fifa':'MLS'}
    for entry in entries[:64]:
        route = entry.get('file', '')
        if entry.get('filetype') != 'directory' or not valid_route(route) or route in seen:
            continue
        if parse_qs(urlsplit(route).query).get('action', [''])[0] not in ACTIONS:
            continue
        action = parse_qs(urlsplit(route).query).get('action', [''])[0]
        if action != 'fullsites' and league_actions.get(action) not in league_codes:
            continue
        seen.add(route)
        games = live if action == 'fullsites' else [game for game in live if (game.get('league') or game.get('league_name')) == league_actions[action]]
        sources.append(CrewSource(entry.get('label') or 'Sports', route, games, read))
    return sorted(sources, key=lambda source: parse_qs(urlsplit(source.route).query).get('action') == ['fullsites'])

AMERICAN_LEAGUES = frozenset(('NFL', 'NBA', 'WNBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB', 'MLS'))


def schedule():
    import sports_espn
    provider = sports_espn.EspnProvider(fetch=lambda url: sports_espn.fetch_json(url, timeout=3), leagues=AMERICAN_LEAGUES)
    snapshot = provider._load()
    return snapshot['live'] + snapshot['upcoming']
