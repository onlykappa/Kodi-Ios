"""Sports catalog from The Crew's normal Kodi menus; playback stays in The Crew."""
import time
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit
import sports_loop_routes as common

ADDON = 'plugin.video.thecrew'
NAME = 'TheCrewRoute'
# Only sports menus, never movie/TV/replay/account routes during discovery.
ACTIONS = {'nfl', 'nhl', 'nba', 'mlb', 'ncaa', 'ncaab', 'fifa', 'fullsites',
           'ufc', 'f1', 'pga'}   # Crew's own UFC, Formula 1 and PGA menus (3.2.2 has them): scanned for sources too (owner, 2026-11-20)
MAX_FOLDERS = 24
MAX_DEPTH = 3
SCAN_BUSY = 'KodiIOS.SportsCrewListing'
OWNER = 'KodiIOS.SportsNativeOwner'
ONLY_LEAGUE = 'KodiIOS.SportsCrewOnlyLeague'   # set while one game's page searches: only that league's Crew menu is read (owner, 2026-11-20)


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


_LISTED = [0]    # how many Crew listings have been made: opening another folder clears Crew's link rules, so a link found earlier is only still good while this has not moved
_WARM = {}       # route -> (the link refresh_link found, _LISTED then, when): a game page opened it ahead of the tap
WARM_FOR = 120   # seconds a warmed link is trusted


def listing(path, session=None, playback=False):
    if not valid_route(path):
        raise ValueError('invalid Crew route')
    _LISTED[0] += 1
    try:
        return _listing(path, session, playback)
    finally:
        _LISTED[0] += 1


def _listing(path, session=None, playback=False):
    import json, threading, xbmc
    home = _home()
    if not playback and playback_requested():
        return []
    if home:
        home.setProperty(SCAN_BUSY, 'true')
    stop = threading.Event()
    if home:
        # Crew shows a modal busy dialog for its dynamic lists. It blocks everything on screen (taps land on the dialog) even though the request
        # runs in the background; a background source search (build 616) left it up on the Home screen and over the game page (owner, 2026-11-20:
        # "the loading circle keeps loading and I cant scroll or do anything"). So it is closed within 50 ms, for every listing this module makes,
        # whether or not a game page is open. Never during a native playback handoff, which has its own dialogs.
        def hide_background_busy():
            while not stop.wait(.05):
                if home.getProperty(OWNER):
                    return
                for name in ('busydialognocancel', 'busydialog'):
                    if xbmc.getCondVisibility('Window.IsVisible(%s)' % name):
                        xbmc.executebuiltin('Dialog.Close(%s)' % name)
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
        import time
        self.at = time.time()   # when Crew listed it: a recent link's folder address is still current (bug 1, refresh_link)
        # The opening card (build 634 screenshot IMG_0543: no LIVE line, the teams' letters instead of crests, "Milwau" and "Philadelphia 76e") draws from this: it
        # needs each team's short name, code and crest and whether the game is on, which the descriptor did not carry.
        self.game = {'league':game.get('league') or game.get('league_name'), 'start':game['start'], 'state':game.get('state') or '',
                     'away':{key:game['away'][key] for key in ('name','aliases','short','code','crest') if key in game['away']},
                     'home':{key:game['home'][key] for key in ('name','aliases','short','code','crest') if key in game['home']}}

    def to_dict(self):
        return {'address':self.address, 'menu_path':self.menu_path, 'game':self.game, 'at':self.at}


DIRECT_FOR = 600   # seconds a found link's own folder is opened directly by refresh_link


def refresh_link(link, read=None):
    """Ask Crew to rebuild the selected menu chain; never write or patch its cache."""
    route = link.get('address', '')
    if not valid_route(route):
        raise ValueError('invalid Crew playback route')
    if read is None:
        # Owner, build 639 log fd1d028c: a tap spent 2.7 s re-listing Crew's folders twice (0.95 s, 1.76 s) before handing Kodi the link. The game page does
        # that listing when it opens (warm); a tap soon after, with no other Crew listing in between, uses its answer.
        kept = _WARM.get(route)
        if kept and kept[1] == _LISTED[0] and 0 <= time.time() - kept[2] < WARM_FOR:
            import sports_jet
            sports_jet.log('sports: Crew link was refreshed when the game page opened (%.0f s ago); no folder is listed now' % (time.time() - kept[2]))
            return kept[0]
        _WARM.pop(route, None)
        found = _refresh_link(link, read)
        _WARM[route] = (found, _LISTED[0], time.time())
        return found
    return _refresh_link(link, read)


def warm(link):
    """From a game page that has a Crew source: do refresh_link's listing now, off the tap. Never raises; True when the link is ready."""
    try:
        home = _home()
        if home and home.getProperty(OWNER):
            return False   # a playback is being handed over: it does its own
        refresh_link(link)
        return True
    except Exception:
        return False


def _refresh_link(link, read=None):
    route = link.get('address', '')
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
        import time
        began = time.monotonic()
        entries = (read or (lambda value: listing(value, playback=True)))(address)
        import sports_jet
        sports_jet.log('sports: Crew refresh folder completed in %.3fs (%d entries)' % (time.monotonic() - began, len(entries)))
        check_owner()
        return entries
    def pick(entries):
        matches = [entry for entry in entries if entry.get('filetype') != 'directory' and valid_route(entry.get('file'))
                   and match_game(entry.get('title') or entry.get('label') or '', [game])]
        exact = [entry for entry in matches if entry['file'] == route]
        matches = exact or matches
        return matches[0]['file'] if len(matches) == 1 else None
    # Bug 1 (owner, build 619 log: about 3 s of a Sports tap were spent reopening Crew's sports root and then the game's folder, one after the other):
    # the game's own folder is opened directly when its address is a plain Crew route (no $doregex rule from its parent). Opening it rebuilds Crew's link
    # rules for the items in it. If the game's link is not uniquely there, the whole chain is reopened as before.
    # Crew's folder addresses can expire (test_reopens_native_menu_chain...), so only a link found in the last DIRECT_FOR seconds (the service's prefetch)
    # tries its folder directly.
    last = path[-1].get('address') or ''
    import time
    try:
        recent = time.time() - float(link.get('at') or 0) < DIRECT_FOR
    except (TypeError, ValueError):
        recent = False
    if recent and len(path) > 1 and '$doregex[' not in unquote(last):
        try:
            found = pick(load(last))
        except InterruptedError:
            raise
        except Exception:
            found = None
        if found:
            return found
        import sports_jet
        sports_jet.log('sports: Crew game folder alone did not give the link; reopening the whole chain')
    else:   # build 639 log fd1d028c: two listings (root, then folder) on every tap and nothing said why the direct way was not taken
        try:
            import sports_jet
            sports_jet.log('sports: Crew game folder not opened directly (%s)' % ('link found %.0f s ago' % (time.time() - float(link.get('at') or 0)) if not recent
                                                                                  else 'only %d menu step(s)' % len(path) if len(path) <= 1 else 'its address holds a $doregex rule'))
        except Exception:
            pass
    entries = load(root)
    for step in path[1:]:
        folders = [entry for entry in entries if entry.get('filetype') == 'directory' and valid_route(entry.get('file'))]
        exact = [entry for entry in folders if entry['file'] == step['address']]
        matches = exact or [entry for entry in folders if common.label(entry.get('title') or entry.get('label')) == step.get('label')]
        if len(matches) != 1:
            raise RuntimeError('Crew source folder is no longer uniquely available')
        entries = load(matches[0]['file'])
    found = pick(entries)
    if not found:
        raise RuntimeError('Crew game source is no longer uniquely available')
    return found


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
        unmatched = [0]   # event-looking titles (two teams) Crew showed that matched no game: counted, never named
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
                if pair and not game and not entry.get('filetype') == 'directory':unmatched[0] += 1
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
        sports_jet.log('jet: %s: %d event-looking titles matched no live game' % (self.name, unmatched[0]))
        sports_jet.log('jet: %s: %d folders, %d unavailable, %d matched streams in %.2fs' % (self.name, len(visited), failures, len(items), time.monotonic() - began))
        yield list(items)


def discover(read=listing, schedule=None, session=None):
    if schedule is None:
        schedule = globals()['schedule']()
    # ESPN is authoritative for live status. Keep upcoming games in the
    # schedule, but do not walk Crew menus for events that have not started.
    live = [game for game in schedule if game.get('state') == 'live']
    home_only = _home()
    only = home_only.getProperty(ONLY_LEAGUE) if home_only else ''
    if only:   # a game page asked: read only its own league's Crew menu, not every menu
        live = [game for game in live if (game.get('league') or game.get('league_name')) == only]
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
    for entry in entries[:64]:
        route = entry.get('file', '')
        if entry.get('filetype') != 'directory' or not valid_route(route) or route in seen:
            continue
        if parse_qs(urlsplit(route).query).get('action', [''])[0] not in ACTIONS:
            continue
        action = parse_qs(urlsplit(route).query).get('action', [''])[0]
        if action != 'fullsites' and not (CREW_LEAGUES.get(action, frozenset()) & league_codes):
            continue
        if action == 'fullsites' and only and any(only in codes for codes in CREW_LEAGUES.values()):
            continue   # one game's search reads only its own league's menu, never the all-sites menu (owner, 2026-11-20) ... unless Crew has no menu for that league (see below)
        seen.add(route)
        games = live if action == 'fullsites' else [game for game in live if (game.get('league') or game.get('league_name')) in CREW_LEAGUES[action]]
        sources.append(CrewSource(entry.get('label') or 'Sports', route, games, read, session, cache_state))
    return sorted(sources, key=lambda source: parse_qs(urlsplit(source.route).query).get('action') == ['fullsites'])

AMERICAN_LEAGUES = frozenset(('NFL', 'NBA', 'WNBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB', 'MLS'))
SOCCER = frozenset(('MLS', 'EPL', 'LIGA', 'BUN', 'SERA', 'LIG1', 'UCL'))
# The leagues each Crew menu (its `action`) lists. Crew's soccer menu (fifa) is soccer of every league; build 615's log: a Bundesliga game that had
# been on for 25 minutes found no source because the schedule Crew was asked about held only American leagues, so nothing was "live" for it.
CREW_LEAGUES = {'nfl': frozenset(('NFL',)), 'nba': frozenset(('NBA', 'WNBA')), 'nhl': frozenset(('NHL',)), 'mlb': frozenset(('MLB',)),
                'ncaa': frozenset(('NCAAF',)), 'ncaab': frozenset(('NCAAB',)), 'fifa': SOCCER, 'ufc': frozenset(('UFC',)),
                'f1': frozenset(('F1',)), 'pga': frozenset(('PGA',))}


def schedule(only=None):
    """ESPN's games for Crew's search: every league (or just the one game's league, which is faster). It was American leagues only, so a live soccer
    match, UFC fight or race was never "live" here and its sources were never looked for."""
    import sports_espn
    provider = sports_espn.EspnProvider(fetch=lambda url: sports_espn.fetch_json(url, timeout=3), leagues={only} if only else None)
    snapshot = provider._load()
    return snapshot['live'] + snapshot['upcoming']
