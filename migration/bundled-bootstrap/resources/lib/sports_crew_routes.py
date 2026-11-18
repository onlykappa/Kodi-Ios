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


def listing(path, session=None, playback=False):
    if not valid_route(path):
        raise ValueError('invalid Crew route')
    import json, threading, xbmc
    home = _home()
    if not playback and playback_requested():
        return []
    if home:
        home.setProperty(SCAN_BUSY, 'true')
    stop = threading.Event()
    if home and session is not None:
        import sports_crew_context
        def hide_background_busy():
            # Crew displays this modal for dynamic lists. It blocks the Sports
            # dialog even though the request runs in the background. Only hide
            # it during our own listing, never during native playback handoff.
            while not stop.wait(.1):
                if not sports_crew_context.valid(home, session) or home.getProperty(OWNER):
                    return
                if (xbmc.getCondVisibility('Window.IsVisible(busydialognocancel)')
                        and sports_crew_context.valid(home, session) and not home.getProperty(OWNER)):
                    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        threading.Thread(target=hide_background_busy, daemon=True).start()
    try:
        if not playback and playback_requested():
            return []
        reply = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0', 'id':1, 'method':'Files.GetDirectory',
                           'params':{'directory':path, 'media':'files', 'properties':['title']}})))
    finally:
        stop.set()
        if home:
            home.clearProperty(SCAN_BUSY)
    if reply.get('error'):
        raise RuntimeError('Crew listing unavailable')
    return reply.get('result', {}).get('files', [])


def match_game(text, games):
    """Match both sides only against ESPN's own names/aliases, rejecting ambiguity."""
    import re, sports_merge
    # Crew providers add their own live status, clock, and broadcast time
    # around the matchup. Strip only observed decorations, not team words.
    text = common.label(text)
    text = re.sub(r'^NCAA\s+Men\s+LIVE\s+', '', text, flags=re.I)
    text = re.sub(r'^\d{1,2}:\d{2}\s*-\s*(?:1st|2nd)\s+Half\s+', '', text, flags=re.I)
    text = re.sub(r'\s+\d{1,2}:\d{2}\s*[AP]M\s+ET\s*$', '', text, flags=re.I)
    pair = common.title_pair(text)
    if not pair:
        return None
    def team_matches(name, team):
        return any(sports_merge.same_team(name, alias) for alias in [team['name']] + team.get('aliases', []))
    matches = [game for game in games if
               (team_matches(pair[0], game['away']) and team_matches(pair[1], game['home'])) or
               (team_matches(pair[1], game['away']) and team_matches(pair[0], game['home']))]
    return matches[0] if len(matches) == 1 else None


class CrewLink:
    """Keep native menu provenance: opening another league clears Crew's regex cache."""
    def __init__(self, address, menu_path, game):
        self.address, self.name, self.links = address, '', False
        self.menu_path = menu_path
        import re
        provider = menu_path[1]['label'] if len(menu_path) > 1 else ''
        alias = re.search(r'\(([A-Za-z0-9 _-]{1,16})\)', provider)
        self.source_name = 'Crew ' + alias.group(1).strip() if alias else ''
        self.game = {'league':game.get('league') or game.get('league_name'), 'start':game['start'],
                     'away':{key:game['away'][key] for key in ('name','aliases') if key in game['away']},
                     'home':{key:game['home'][key] for key in ('name','aliases') if key in game['home']}}

    def to_dict(self):
        return {'address':self.address, 'menu_path':self.menu_path, 'game':self.game}


def refresh_link(link, read=None):
    """Ask Crew to rebuild the selected menu chain; never write or patch its cache."""
    route = link.get('address', '')
    if not valid_route(route):
        raise ValueError('invalid Crew playback route')
    path = link.get('menu_path') or []
    if not path:
        if '$doregex[' in parse_qs(urlsplit(route).query).get('url', [''])[0]:
            raise RuntimeError('Crew source needs a fresh menu scan')
        return route
    if len(path) > MAX_DEPTH + 1 or not all(isinstance(step, dict) and valid_route(step.get('address')) for step in path):
        raise ValueError('invalid Crew source ancestry')
    root = path[0]['address']
    if parse_qs(urlsplit(root).query).get('action', [''])[0] not in ACTIONS:
        raise ValueError('invalid Crew sports root')
    game = link.get('game') or {}
    if not all(game.get(side, {}).get('name') for side in ('away', 'home')):
        raise ValueError('Crew source lacks its matched game')
    home = _home()
    owner = home.getProperty(OWNER) if home else ''
    def check_owner():
        if home and owner and home.getProperty(OWNER) != owner:
            raise InterruptedError('Crew playback request replaced')
    def load(address):
        check_owner()
        entries = (read or (lambda value: listing(value, playback=True)))(address)
        check_owner()
        return entries
    entries = load(root)
    for step in path[1:]:
        folders = [entry for entry in entries if entry.get('filetype') == 'directory' and valid_route(entry.get('file'))]
        exact = [entry for entry in folders if entry['file'] == step['address']]
        matches = exact or [entry for entry in folders if common.label(entry.get('title') or entry.get('label')) == step.get('label')]
        if len(matches) != 1:
            raise RuntimeError('Crew source folder is no longer uniquely available')
        entries = load(matches[0]['file'])
    matches = [entry for entry in entries if entry.get('filetype') != 'directory' and valid_route(entry.get('file'))
               and match_game(entry.get('title') or entry.get('label') or '', [game])]
    exact = [entry for entry in matches if entry['file'] == route]
    matches = exact or matches
    if len(matches) != 1:
        raise RuntimeError('Crew game source is no longer uniquely available')
    return matches[0]['file']


class CrewSource:
    def __init__(self, title, route, games, read=listing, session=None, cache_state=None):
        self.name = 'Crew ' + common.label(title)
        self.route, self.games, self.read = route, games, read
        self.session = session
        self.cache_state = cache_state

    def get_items(self):
        latest = []
        for latest in self.batches():
            pass
        return latest

    def batches(self):
        import time
        began = time.monotonic()
        pending, visited, emitted, items = [(self.route, 0, None, [{'address':self.route, 'label':self.name}])], set(), set(), []
        failures = 0
        import sports_crew_context
        home = _home()
        def active():
            return not playback_requested() and (home is None or sports_crew_context.valid(home, self.session))
        def read_fresh(path):
            # Opening a different Crew league clears its global regex table.
            # Reopen the native ancestors and follow only unique Crew folders.
            if not active():
                raise InterruptedError('Crew discovery cancelled')
            fresh_path = [path[0]]
            entries = self.read(path[0]['address'])
            for step in path[1:]:
                if not active():
                    raise InterruptedError('Crew discovery cancelled')
                folders = [e for e in entries if e.get('filetype') == 'directory' and valid_route(e.get('file'))]
                exact = [e for e in folders if e['file'] == step['address']]
                matches = exact or [e for e in folders if common.label(e.get('title') or e.get('label')) == step.get('label')]
                if len(matches) != 1:
                    raise RuntimeError('Crew folder is no longer uniquely available')
                address = matches[0]['file']
                fresh_path.append({'address':address, 'label':step['label']})
                entries = self.read(address)
            return entries, fresh_path
        while pending and len(visited) < MAX_FOLDERS and not playback_requested() and (home is None or sports_crew_context.valid(home, self.session)):
            route, depth, parent_game, menu_path = pending.pop(0)
            if route in visited or not valid_route(route):
                continue
            visited.add(route)
            try:
                if self.cache_state is not None and self.cache_state.get('owner') != self.route and depth:
                    entries, menu_path = read_fresh(menu_path)
                else:
                    entries = self.read(route)
                if self.cache_state is not None:
                    self.cache_state['owner'] = self.route
            except Exception:
                # A dead subfolder must not discard games from other sites.
                if self.cache_state is not None:
                    self.cache_state['owner'] = None
                failures += 1
                yield list(items)
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
                            pending.insert(0, (address, depth + 1, game, menu_path + [{'address':address, 'label':title}]))
                        else:
                            pending.append((address, depth + 1, game, menu_path + [{'address':address, 'label':title}]))
                    continue
                if not game or address in emitted:
                    continue
                emitted.add(address)
                items.append(SimpleNamespace(title=game['away']['name']+' vs '+game['home']['name'],
                             league=game['league_name'], status='LIVE' if game['state']=='live' else '',
                             starttime=datetime.fromtimestamp(game['start']), links=[CrewLink(address, menu_path, game)]))
            yield list(items)
        import sports_jet
        sports_jet.log('jet: %s: %d folders, %d unavailable, %d matched streams in %.2fs' % (self.name, len(visited), failures, len(items), time.monotonic() - began))
        yield list(items)


def discover(read=listing, schedule=None, session=None):
    if schedule is None:
        schedule = globals()['schedule']()
    # ESPN is authoritative for live status. Keep upcoming games in the
    # schedule, but do not walk Crew menus for events that have not started.
    live = [game for game in schedule if game.get('state') == 'live']
    if not live:
        return []
    if session is not None:
        import sports_crew_context, xbmc
        home = _home()
        if home is None or not sports_crew_context.wait_ready(home, session, xbmc):
            return []
        if read is listing:
            read = lambda route: listing(route, session=session)
    entries = read('plugin://' + ADDON + '/?action=bluehat')
    sources, seen, cache_state = [], set(), {'owner':None}
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
        sources.append(CrewSource(entry.get('label') or 'Sports', route, games, read, session, cache_state))
    return sorted(sources, key=lambda source: parse_qs(urlsplit(source.route).query).get('action') == ['fullsites'])

AMERICAN_LEAGUES = frozenset(('NFL', 'NBA', 'WNBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB', 'MLS'))


def schedule():
    import sports_espn
    provider = sports_espn.EspnProvider(fetch=lambda url: sports_espn.fetch_json(url, timeout=3), leagues=AMERICAN_LEAGUES)
    snapshot = provider._load()
    return snapshot['live'] + snapshot['upcoming']
