"""Sports games and streams from JetExtractors (DEC-061; the owner chose The Loop family's source add-on over ESPN on 2026-11-16).

script.module.jetextractors holds ~45 scrapers; each one's get_items() lists games (JetItem: title "Team A vs Team B", start time, league, status) with
streams (JetLink). This module asks them all at once, turns every JetItem into merge *records* (sports_merge.py), merges them into the games of the
contract in sports_model.py, and plays a chosen stream through JetProxy (plugin.video.jetproxy) or Kodi's own player. The add-ons' code is used as
shipped; nothing in them is read, copied or changed here, only their public classes (JetExtractor, JetItem, JetLink) are called.

Slow scrapers never hold the page: a load waits LOAD_SECONDS for the add-on answers, shows what has come in, and the rest finish in the background.
Nothing here logs a stream address or a header (logs are shared); only counts, add-on names and a few game titles.
"""
import base64
import copy
import json
import re
import sys
import threading
import time
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

import sports_merge
import sports_model as sm

TTL = 120               # seconds a finished answer is reused
SHOW_AFTER = 6          # allow an initial scan to collect a useful first batch
LOAD_SECONDS = 18       # how long a page waits for the scrapers before showing what it has
EXTRACTOR_SECONDS = 40  # heartbeat grace period; page waits are bounded separately
LIVE_FOR = 4 * 3600     # a game with a start time is live from its start for this long
SOON_BEFORE = 600       # a game that should have started minutes ago still lists as upcoming/live
HORIZON = 8 * 86400
MODULE_ID = 'script.module.jetextractors'
JETPROXY = 'plugin://plugin.video.jetproxy/play/'
RUN = 'KodiIOS.SportsJetRun'      # Home window: when the collecting script started (epoch seconds)
DATA = 'KodiIOS.SportsJetData'    # Home window: JSON {at, done, records, reason} the script keeps up to date
_play_session = threading.local()  # each Kodi script owns its local scraper proxy
PLAY = 'KodiIOS.SportsJetPlay'    # Home window: JSON of the source a page asked to play

# Scrapers of replays, full-match videos, IPTV lists and plain hosts: they give no games.
SKIP = {'basketballreplays', 'fullfightreplays', 'fullraces', 'fullreplays', 'nflvideo', 'nhlvideo', 'rugbyvideo', 'soccerfullmatch', 'sportsvideo',
        'topravideo', 'watchprowrestling', 'homeiptv', 'myiptv', 'telegram_xtream', 'tvgarden', 'uktvnow', 'cloudstream', 'streamtape', 'tinyurl',
        'template', 'ondemand', 'voodc', 'sofascore', 'embedhd_api', 'backdoor', 'backdoor2', 'xyz_mappings'}

# (words in the add-on's league text, code, name, sport, joiner). First match wins; checked in order.
LEAGUES = (
    ('premier league', 'EPL', 'Premier League', 'Soccer', 'vs'), ('champions league', 'UCL', 'UEFA Champions League', 'Soccer', 'vs'),
    ('la liga', 'LIGA', 'La Liga', 'Soccer', 'vs'), ('bundesliga', 'BUN', 'Bundesliga', 'Soccer', 'vs'), ('serie a', 'SERA', 'Serie A', 'Soccer', 'vs'),
    ('ligue 1', 'LIG1', 'Ligue 1', 'Soccer', 'vs'), ('mls', 'MLS', 'MLS', 'Soccer', 'vs'),
    ('ncaaf', 'NCAAF', 'College Football', 'American football', 'at'), ('college football', 'NCAAF', 'College Football', 'American football', 'at'),
    ('nfl', 'NFL', 'NFL', 'American football', 'at'), ('american football', 'NFL', 'NFL', 'American football', 'at'),
    ('ncaab', 'NCAAB', 'College Basketball', 'Basketball', 'at'), ('college basketball', 'NCAAB', 'College Basketball', 'Basketball', 'at'),
    ('wnba', 'WNBA', 'WNBA', 'Basketball', 'at'), ('nba', 'NBA', 'NBA', 'Basketball', 'at'), ('basketball', 'NBA', 'Basketball', 'Basketball', 'at'),
    ('nhl', 'NHL', 'NHL', 'Hockey', 'at'), ('hockey', 'NHL', 'Hockey', 'Hockey', 'at'),
    ('mlb', 'MLB', 'MLB', 'Baseball', 'at'), ('baseball', 'MLB', 'Baseball', 'Baseball', 'at'),
    ('ufc', 'UFC', 'UFC', 'Combat sports', 'vs'), ('mma', 'MMA', 'MMA', 'Combat sports', 'vs'), ('boxing', 'BOX', 'Boxing', 'Combat sports', 'vs'),
    ('wwe', 'WWE', 'WWE', 'Combat sports', 'vs'),
    ('formula', 'F1', 'Formula 1', 'Motorsport', 'vs'), ('f1', 'F1', 'Formula 1', 'Motorsport', 'vs'), ('motogp', 'MGP', 'MotoGP', 'Motorsport', 'vs'),
    ('nascar', 'NASC', 'NASCAR', 'Motorsport', 'vs'),
    ('soccer', 'SOC', 'Soccer', 'Soccer', 'vs'), ('football', 'SOC', 'Soccer', 'Soccer', 'vs'),
)
_SPLIT = re.compile(r'\s+(?:vs\.?|v|@|at|-|–|—)\s+', re.I)


def league_of(text, title=''):
    """(code, name, sport, joiner) for an add-on's league text; the title is looked at when the league says nothing known."""
    low = ' %s ' % re.sub(r'[^a-z0-9 ]+', ' ', str(text or '').lower())
    for word, code, name, sport, joiner in LEAGUES:
        if ' %s ' % word in low:
            return code, name, sport, joiner
    text = str(text or '').strip()
    if text and text.lower() != 'unknown':
        code = re.sub(r'[^A-Z0-9]', '', text.upper())[:5] or 'OTH'
        return code, text[:28], 'Other', 'vs'
    return 'OTH', 'Other', 'Other', 'vs'


def teams(title):
    """(away, home, joiner-word) from 'A vs B', 'A @ B', 'A at B'; None when the title is a single name (an event, a channel)."""
    parts = _SPLIT.split(re.sub(r'\s+', ' ', str(title or '')).strip(), maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    match = _SPLIT.search(str(title))
    word = (match.group(0).strip().lower() if match else 'vs').rstrip('.')
    return parts[0].strip(' -:'), parts[1].strip(' -:'), 'at' if word in ('@', 'at') else 'vs'


def code_of(name):
    words = [w for w in re.findall(r'[A-Za-z0-9]+', str(name or '')) if w.lower() not in sports_merge.NOISE]
    return (''.join(words[0][:4]) if len(words) == 1 else ''.join(w[0] for w in words[:4]) or '???').upper()[:4]


def quality_of(name):
    text = str(name or '').lower()
    m = re.search(r'(2160|1440|1080|720|576|480|360)\s*p?', text)
    if m:
        return m.group(1) + 'p'
    if '4k' in text:
        return '2160p'
    return '1080p' if re.search(r'\bfhd\b', text) else ('720p' if re.search(r'\bhd\b', text) else '')


def language_of(name):
    text = str(name or '').lower()
    for word, label in (('english', 'English'), ('spanish', 'Spanish'), ('french', 'French'), ('german', 'German'), ('portuguese', 'Portuguese'),
                        ('italian', 'Italian'), ('arabic', 'Arabic'), ('russian', 'Russian')):
        if word in text:
            return label
    return 'English' if re.search(r'\b(en|eng)\b', text) else ''


def epoch_of(value):
    try:
        return int(value.timestamp())
    except (AttributeError, OverflowError, OSError, ValueError):
        return None


def state_of(item, start, now):
    """'live', 'upcoming' or None (finished, or nothing to tell) for one JetItem."""
    status = str(getattr(item, 'status', '') or '').lower()
    if any(w in status for w in ('ended', 'final', 'finished', 'replay', 'full time')):
        return None
    if 'live' in status:
        return 'live'
    if start is None:
        return None
    if start > now + HORIZON:
        return None
    if start > now + SOON_BEFORE:
        return 'upcoming'
    return 'live' if now - start <= LIVE_FOR else None


def descriptor(extractor, link):
    """The opaque play value of one stream: which scraper, and the JetLink as the add-on's own to_dict() wrote it."""
    import sports_loop_routes
    if sports_loop_routes.valid_route(getattr(link, 'address', '')):
        extractor = sports_loop_routes.NAME
    return json.dumps({'e': extractor, 'l': link.to_dict()}, separators=(',', ':'))


def records(item, extractor, now):
    """The merge records of one JetItem (one per stream); [] for what is not a game of two sides or has no stream."""
    pair = teams(getattr(item, 'title', ''))
    links = [l for l in (getattr(item, 'links', None) or []) if getattr(l, 'address', None)]
    start = epoch_of(getattr(item, 'starttime', None))
    state = state_of(item, start, now)
    if not pair or not links or state is None:
        return []
    away, home, word = pair
    code, name, sport, joiner = league_of(getattr(item, 'league', None), item.title)
    if word == 'at':
        joiner = 'at'
    out = []
    for link in links:
        address = getattr(link, 'address', '')
        label = '%s %s' % (getattr(link, 'name', '') or '', address if not getattr(link, 'links', False) and not str(address).startswith('plugin://') else '')
        out.append({'addon': extractor, 'league': code, 'league_name': name, 'sport': sport, 'state': state, 'start': start if start is not None else now,
                    'away': {'code': code_of(away), 'name': away, 'score': None},
                    'home': {'code': code_of(home), 'name': home, 'score': None},
                    'joiner': joiner, 'clock': '', 'left': None, 'quality': quality_of(label), 'language': language_of(label),
                    'play': descriptor(extractor, link), 'separate_source': str(address).startswith('plugin://plugin.video.the-loop/')})
    return out


def log(text):
    try:
        import xbmc
        xbmc.log('Kodi iOS Sports: ' + text, xbmc.LOGINFO)
    except ImportError:
        pass


def add_module_paths(addon_id, find, seen=None):
    """Put an add-on's python module folder, and those of the modules it requires, on sys.path. Kodi only does this for the add-on that is running; this
    script is not JetExtractors, so without it `import requests` fails (owner log 916e0a6a). `find(id)` -> the add-on's folder or None."""
    import os
    import xml.etree.ElementTree as ET
    seen = set() if seen is None else seen
    if addon_id in seen or addon_id.startswith('xbmc.'):
        return seen
    seen.add(addon_id)
    folder = find(addon_id)
    if not folder:
        return seen
    try:
        root = ET.parse(os.path.join(folder, 'addon.xml')).getroot()
    except Exception:
        return seen
    for ext in root.iter('extension'):
        if ext.get('point') == 'xbmc.python.module' and ext.get('library'):
            path = os.path.join(folder, ext.get('library'))
            if path not in sys.path:
                sys.path.insert(0, path)
    for need in root.iter('import'):
        if need.get('addon'):
            add_module_paths(need.get('addon'), find, seen)
    return seen


def _folder(addon_id):
    try:
        import xbmcaddon
        return xbmcaddon.Addon(addon_id).getAddonInfo('path').rstrip('/')
    except Exception:
        return None


def import_jet(find=_folder):
    """The jetextractors package, found through its add-on's folder; (module, None) or (None, reason)."""
    try:
        add_module_paths(MODULE_ID, find)
        add_module_paths("script.module.resolveurl", find)
        import jetextractors.extractor as module
        return module, None
    except Exception as error:
        return None, type(error).__name__


def load_extractors(module):
    """(extractor objects that list games, 'configured'). Only the add-on's own get_extractors() is used: it applies the add-on's settings and
    domains and its own checks on who may ask. When it refuses, nothing is worked around; the reason is logged and the pages say "Can't load"."""
    found = list(module.get_extractors())
    out = []
    for ext in found:
        short = type(ext).__module__.rsplit('.', 1)[-1]
        if short in SKIP or getattr(ext, 'resolve_only', False) or getattr(ext, 'disabled', False):
            continue
        if type(ext).get_items is module.JetExtractor.get_items:   # no games of its own
            continue
        out.append(ext)
    return out, 'configured'


class JetProvider:
    """The contract's provider over JetExtractors. `loader()` -> (extractors, how) and `clock` are injectable (tests)."""

    def __init__(self, loader=None, clock=time.time, wait=LOAD_SECONDS, remote=False, publish=None, window=None, launch=None, score_loader=None):
        self.loader, self.clock, self.wait = loader, clock, wait
        self.remote, self.publish, self.launch = remote, publish, launch   # remote: a page asks the script (run_script) and reads its answer
        self.window = window
        self.lock = threading.Lock()
        self.records = {}     # extractor name -> [records]
        self.stats = {}       # extractor name -> 'n items' | error text
        self.at = 0
        self.running = None   # (thread list, done event)
        self.reason = ''
        self._remote_cache = None  # snapshot bytes and recent merged result
        self.score_loader, self._scores = score_loader, []
        self._score_started = self._score_at = 0
        self._score_busy = False
        self._score_requested = set()

    # -- loading
    def _extractors(self):
        if self.loader:
            return self.loader()
        import sports_independent
        independent = [sports_independent.StreamsCenter()]
        module, reason = import_jet()
        if module is None:
            self.reason = 'JetExtractors is not installed (%s)' % reason
            return independent, 'independent'
        try:
            extractors, how = load_extractors(module)
            return extractors + independent, how + '+independent'
        except Exception as error:
            self.reason = 'JetExtractors refused or failed (%s)' % type(error).__name__
            log('jet: unavailable (%s); trying independent sources' % type(error).__name__)
            return independent, 'independent'

    def _start(self):
        if self.loader:
            extractors, how = self._extractors()
            discover_jet = False
        else:
            import sports_independent
            import sports_fawa
            extractors = [sports_fawa.FawaNews()] if _folder('plugin.video.the-loop') else [sports_independent.StreamsCenter(), sports_fawa.FawaNews()]
            how = 'Loop routes' if _folder('plugin.video.the-loop') else 'independent'
            discover_jet = True
        done = threading.Event()
        pending = [len(extractors) + int(discover_jet)]
        started = self.clock()
        if not extractors:
            log('jet: no scrapers (%s)' % (self.reason or how))
            done.set()
            self.running = done
            return done
        log('jet: %d scrapers (%s)' % (len(extractors), how))

        def work(ext):
            name = getattr(ext, 'name', None) or type(ext).__name__
            try:
                items = ext.get_items() or []
                found = []
                for item in items:
                    try:
                        found += records(item, name, int(self.clock()))
                    except Exception:
                        continue
                text = '%d games, %d streams' % (len({(r['away']['name'], r['home']['name']) for r in found}), len(found))
                with self.lock:
                    self.records[name] = found
                    self.stats[name] = text
                if found:
                    log('jet: %s %s, e.g. %s' % (name, text, '; '.join(sorted({sm.versus(r) for r in found})[:2])))
            except Exception as error:
                with self.lock:
                    self.stats[name] = type(error).__name__
                    self.records.setdefault(name, [])
                log('jet: %s failed (%s)' % (name, type(error).__name__))
            finally:
                with self.lock:
                    pending[0] -= 1
                self._publish(pending[0] <= 0)
                with self.lock:
                    if pending[0] <= 0:
                        done.set()
                        log('jet: all scrapers answered after %ds (%d with games)' % (self.clock() - started, sum(1 for v in self.records.values() if v)))

        gate = threading.Semaphore(2 if how == 'Loop routes' else 8)

        def guarded(ext):
            with gate:
                work(ext)
        for ext in extractors:
            threading.Thread(target=guarded, args=(ext,), daemon=True).start()
        if discover_jet:
            def discover():
                try:
                    home = None
                    if _folder('plugin.video.the-loop'):
                        import sports_loop_routes
                        others = sports_loop_routes.discover()
                        log('jet: %d Loop source routes discovered' % len(others))
                    else:
                        try:
                            home = self._home()
                            import sports_pause
                            if sports_pause.Pause(window=home).active():
                                return
                        except Exception:
                            home = None
                        module, reason = import_jet()
                        if module is None:
                            self.reason = 'JetExtractors is not installed (%s)' % reason
                            return
                        others, _ = load_extractors(module)
                    with self.lock:
                        pending[0] += len(others)
                    for ext in others:
                        threading.Thread(target=guarded, args=(ext,), daemon=True).start()
                except Exception as error:
                    self.reason = 'JetExtractors refused or failed (%s)' % type(error).__name__
                    import sports_pause
                    if sports_pause.is_refusal(error):
                        sports_pause.Pause(window=home).pause()
                        log('jet: paused (access refused)')
                    log('jet: unavailable (%s); independent sources remain available' % type(error).__name__)
                finally:
                    with self.lock:
                        pending[0] -= 1
                        finished = pending[0] <= 0
                    self._publish(finished)
                    if finished:
                        done.set()
            threading.Thread(target=discover, daemon=True).start()
        self.running = done
        return done

    def _publish(self, done):
        """Hand what has come in so far to whoever asked (the script's Home window property); never raises."""
        if not self.publish:
            return
        try:
            with self.lock:
                every = [r for rs in self.records.values() for r in rs]
            self.publish({'at': int(self.clock()), 'done': bool(done), 'records': every, 'reason': self.reason})
        except Exception as error:
            log('jet: publish failed (%s)' % type(error).__name__)

    def _home(self):
        if self.window is None:
            import xbmcgui
            self.window = xbmcgui.Window(10000)
        return self.window

    def _remote_load(self, force):
        """A page's load: read the script's answer; start the script when there is none fresh and none running. Waits `wait` seconds for partial or full data."""
        try:
            home = self._home()
        except ImportError:   # not inside Kodi (tests, tools): nothing to ask
            raise sm.SportsUnavailable('not running inside Kodi')
        now = self.clock()

        raw_seen = ''
        def read():
            nonlocal raw_seen
            try:
                raw = home.getProperty(DATA) or ''
                decoded = json.loads(raw or 'null')
                if decoded is not None:
                    raw_seen = raw
                return decoded
            except ValueError:
                return None
        data = read()
        if force or not data or now - data.get('at', 0) >= TTL:
            try:
                started = float(home.getProperty(RUN) or 0)
            except ValueError:
                started = 0
            if now - started > EXTRACTOR_SECONDS + 10:   # nothing running (or a stuck one): start it
                home.setProperty(RUN, str(now))
                (self.launch or _launch)('sports_jet_run')
                # Keep the existing snapshot visible while the replacement scan runs.
        had_records = bool(data and data.get('records'))
        began = time.monotonic()   # real time: the injected clock is only for the data's own timestamps
        while time.monotonic() - began < self.wait:
            data = read() or data
            if data and (data.get('done') or (data.get('records') and (had_records or time.monotonic() - began >= SHOW_AFTER))):
                break
            time.sleep(0.4)
        data = read() or data
        if not data or not data.get('records'):
            if data and data.get('done'):
                raise sm.SportsUnavailable(data.get('reason') or 'no scraper listed a game')
            raise sm.SportsUnavailable('the scrapers are still loading')
        self.at = data.get('at', 0)
        now_mono = time.monotonic()
        with self.lock:
            cached = self._remote_cache
        if raw_seen and cached and cached[0] == raw_seen and now_mono - cached[1] < 2:
            return self._with_scores(copy.deepcopy(cached[2]))
        result = self._games(data['records'])
        with self.lock:
            self._remote_cache = (raw_seen, time.monotonic(), result)
        return self._with_scores(copy.deepcopy(result))

    def _load(self, force=False):
        if self.remote:
            return self._remote_load(force)
        with self.lock:
            fresh = self.at and self.clock() - self.at < TTL
            busy = self.running is not None and not self.running.is_set()
        if force or not (fresh or busy):
            with self.lock:
                self.records, self.stats, self.reason = ({}, {}, '') if not busy else (self.records, self.stats, self.reason)
            done = self._start()
            self.at = self.clock()
        else:
            done = self.running
        if done is not None and not (fresh and not busy):
            done.wait(self.wait)
        with self.lock:
            every = [r for rs in self.records.values() for r in rs]
            stats = dict(self.stats)
        if not every:
            if self.running is not None and not self.running.is_set():
                raise sm.SportsUnavailable('the scrapers are still loading')
            raise sm.SportsUnavailable(self.reason or 'no scraper listed a game (%s)' % ', '.join('%s: %s' % kv for kv in sorted(stats.items())[:4]))
        return self._games(every)

    def score_revision(self):
        with self.lock:
            return self._score_at

    def _with_scores(self, data):
        """Enrich only unambiguously matched live games; never hold up playback/list loading."""
        if not self.score_loader or not data['live']:
            return data
        now = time.monotonic()
        codes = sorted({g['league'] for g in data['live'] if g.get('league')})
        with self.lock:
            start = not self._score_busy and (not self._score_started or now - self._score_started >= 45 or not set(codes).issubset(self._score_requested))
            if start:
                self._score_busy = True
                self._score_started = now
                self._score_requested = set(codes)
            scores = list(self._scores) if self._score_at and now - self._score_at < 90 else []
        if start:
            def fetch():
                try:
                    values = self.score_loader(codes)
                    with self.lock:
                        self._scores, self._score_at = list(values or []), time.monotonic()
                except Exception as error:
                    log('scores: lookup failed (%s)' % type(error).__name__)
                finally:
                    with self.lock:
                        self._score_busy = False
            threading.Thread(target=fetch, daemon=True).start()
        for game in data['live']:
            matches = []
            for score in scores:
                if score.get('state') != 'live':
                    continue
                if sports_merge.same_game(game, score):
                    matches.append((score, False))
                else:
                    swapped = dict(score, away=score['home'], home=score['away'])
                    if sports_merge.same_game(game, swapped):
                        matches.append((score, True))
            if len(matches) == 1:
                score, reverse = matches[0]
                for side, other in (('away', 'home'), ('home', 'away')):
                    game[side]['score'] = score[other if reverse else side].get('score')
                game['clock'], game['left'] = score.get('clock') or '', score.get('left')
        return data

    def _games(self, every):
        now = int(self.clock())
        import sports_loop_routes
        order = sorted({r['addon'] for r in every}, key=lambda name: (not name.startswith('Loop '), sports_loop_routes.source_rank(name) if name.startswith('Loop ') else 0, name))
        games = sports_merge.merge(every, order)
        live = [g for g in games if g['state'] == 'live']
        upcoming = [g for g in games if g['state'] == 'upcoming' and g['start'] >= now - SOON_BEFORE]
        leagues = {}
        for g in live + upcoming:
            lg = leagues.setdefault(g['league'], {'code': g['league'], 'name': g['league_name'], 'sport': g['sport'], 'live': 0, 'next': None})
            if g['state'] == 'live':
                lg['live'] += 1
            elif lg['next'] is None or g['start'] < lg['next']:
                lg['next'] = g['start']
        return {'at': self.at, 'live': live, 'upcoming': upcoming, 'leagues': sorted(leagues.values(), key=lambda l: l['name'])}

    # -- the contract
    def refresh(self):
        self._load(force=True)

    def live_games(self, league=None):
        return sm.filter_league(sm.order_live(self._load()['live']), league)

    def upcoming_games(self, league=None):
        return sm.filter_league(sorted(self._load()['upcoming'], key=lambda g: g['start']), league)

    def leagues(self):
        return list(self._load()['leagues'])

    def game(self, gid):
        data = self._load()
        return next((g for g in data['live'] + data['upcoming'] if g['id'] == gid), None)

    def overview(self):
        data = self._load()
        now = int(self.clock())
        offset = sm.device_offset(now)
        coming = [g['start'] for g in data['upcoming'] if g['start'] >= now]
        today = [s for s in coming if sm.day_label(s, now, offset) == 'Today']
        return {'updated': data['at'] or now, 'live': len(data['live']), 'live_sports': sorted({g['sport'] for g in data['live']}),
                'next': min(coming) if coming else None, 'more_today': max(0, len(today) - 1), 'leagues': len(data['leagues']), 'finished_today': 0}


def _launch(route, *args):
    import xbmc
    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,%s)' % ','.join((route,) + args))


OWN_ID = 'service.kodi.ios.bootstrap'


class named_addon:
    """While active, a no-id call to the add-on constructor in the Kodi add-on module names this add-on instead of raising (scripts run through default.py's
    runpy, where Kodi cannot tell which add-on is meant: ISSUE-365; the same as the Library status failure of build 159). JetExtractors asks for "the current add-on" this way
    and is otherwise not touched; this only says who we are. Restored on exit."""

    def __init__(self, module=None, own=OWN_ID):
        self.module, self.own, self.original = module, own, None

    def __enter__(self):
        if self.module is None:
            import xbmcaddon
            self.module = xbmcaddon
        self.original = self.module.Addon
        original, own = self.original, self.own

        def Addon(*args, **kwargs):
            if not args and not kwargs.get('id'):
                return original(own)
            return original(*args, **kwargs)
        self.module.Addon = Addon
        return self

    def __exit__(self, *exc):
        self.module.Addon = self.original


def run_script(args, window=None):
    """The main thread of `sports_jet_run`: collect games (no args) or play the source in PLAY ('play'). JetExtractors needs a normal script thread."""
    import xbmcgui
    home = window or xbmcgui.Window(10000)
    if args[:1] == ['play']:
        key = args[1] if len(args) > 1 else ''
        source = {}
        try:
            source = json.loads(home.getProperty(PLAY + key) or '{}')
            home.clearProperty(PLAY + key)
            import sports_loop_router
            if source.get('native_owner') and home.getProperty(sports_loop_router.OWNER) != source['native_owner']:
                return
            import contextlib, sports_loop_routes
            try:
                native = bool(source.get('native_queue')) or json.loads(source.get('play') or '{}').get('e') == sports_loop_routes.NAME
            except (ValueError, TypeError):
                native = False
            # Native Loop owns its plugin interpreter and identity. Only direct
            # Jet imports need the bootstrap's bare-Addon context.
            with (contextlib.nullcontext() if native else named_addon()):
                _play_session.proxy_url = None
                play(source)
                if getattr(_play_session, 'proxy_url', None):
                    import xbmc
                    hold_local_proxy(xbmc, _play_session.proxy_url)
        except Exception as error:
            log('jet: play failed (%s)' % type(error).__name__)
            try:
                xbmcgui.Dialog().notification('Sports', "Can't play this source right now. Try another source.", xbmcgui.NOTIFICATION_WARNING, 4000)
            except Exception:
                pass
        finally:
            import sports_loop_router
            if source.get('native_owner') and home.getProperty(sports_loop_router.OWNER) == source['native_owner']:
                home.clearProperty(sports_loop_router.OWNER)
        return
    import fcntl, os, xbmcvfs
    folder = xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap')
    os.makedirs(folder, exist_ok=True)
    guard = open(os.path.join(folder, 'sports-jet-scan.lock'), 'a')
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        guard.close()
        log('jet: collection already running; reused')
        return
    try:
        provider = JetProvider(window=home, publish=lambda data: home.setProperty(DATA, json.dumps(data, separators=(',', ':'))))
        import contextlib
        with (contextlib.nullcontext() if _folder('plugin.video.the-loop') else named_addon()):
            done = provider._start()
            try:
                import xbmc
                monitor = xbmc.Monitor()
            except (ImportError, AttributeError):
                monitor = None
            # Native plugin listing can outlive the page's bounded wait. Keep
            # ownership until workers finish instead of launching duplicate scans.
            while not done.wait(1):
                home.setProperty(RUN, str(time.time()))
                if monitor is not None and monitor.abortRequested():
                    return
        provider._publish(True)   # also when no scraper could start: the page then gets `reason`
    finally:
        home.clearProperty(RUN)
        guard.close()


def play_request(source, logger=log, window=None, launch=None):
    """What a tap on a source does: leave the source for the script and start it (the page's thread cannot call JetExtractors)."""
    if window is None:
        import xbmcgui
        window = xbmcgui.Window(10000)
    home = window
    import uuid, sports_loop_router
    key = uuid.uuid4().hex   # separate payload/ownership even for taps in the same millisecond
    home.setProperty(sports_loop_router.OWNER, key)
    payload = {'play': source.get('play'), 'alts': source.get('alts') or [], 'id': source.get('id'),
               'native_queue': source.get('native_queue') or [], 'native_owner': key}
    home.setProperty(PLAY + key, json.dumps(payload, separators=(',', ':')))
    logger('sports: play %s from %s (%s, %s)' % (source.get('id'), source.get('addon'), source.get('quality'), source.get('language')))
    (launch or _launch)('sports_jet_run', 'play', key)
    return True


# -- playing ----------------------------------------------------------------------------------------------------------
def proxy_path(address, headers):
    """plugin://plugin.video.jetproxy/play/<address>?h=<base64 headers>, the route JetProxy's main.py serves."""
    path = JETPROXY + quote(address, safe=':/')   # a '?' or '&' inside the address must not end the path
    if headers:
        path += '?h=' + quote(base64.urlsafe_b64encode(json.dumps(headers, separators=(',', ':')).encode()).decode(), safe='=')
    return path


def jet_paused():
    import sports_pause
    try:
        import xbmcgui
        home = xbmcgui.Window(10000)
    except Exception:
        home = None
    return sports_pause.Pause(window=home).active()


def candidates(module, extractor, link, depth=0):
    """Yield each candidate; a failed nested stream must not hide its siblings."""
    if depth > 4 or jet_paused():
        return
    if getattr(link, 'links', False):
        try:
            children = extractor.get_links(link) or []
        except Exception:
            return
        for sub in children:
            try:
                sub.extractor = sub.extractor or link.extractor
                owner = extractor
                if getattr(sub, 'extractor', None) and sub.extractor != getattr(extractor, 'name', None):
                    owner = module.get_extractor(sub.extractor) or extractor
                yield from candidates(module, owner, sub, depth + 1)
            except Exception:
                continue
        return
    if getattr(link, 'direct', False):
        yield link
        return
    if getattr(link, 'resolveurl', False):
        # Some scrapers (including LiveFeeds) also implement their own resolver.
        # Only ask it if the caller advances after ResolveURL fails.
        yield link
    if jet_paused():
        return
    try:
        resolved = extractor.get_link(link)
    except Exception:
        return
    if resolved is None or not getattr(resolved, 'address', None):
        return
    if getattr(resolved, 'address', None) == getattr(link, 'address', None) and not getattr(resolved, 'direct', False):
        return
    yield resolved


def expand(module, extractor, link, depth=0):
    """Return the first candidate for callers that only need to inspect a link."""
    return next(candidates(module, extractor, link, depth), None)


TRIES = 5   # the source's own add-on and up to four others that list the same stream


def play(source, logger=log):
    """Start a source (what a tap on a line does): its own add-on first, then the others that list the same stream, until one opens. Raises when none can."""
    values = [v for v in [source.get('play')] + list(source.get('alts') or []) if v][:TRIES]
    if source.get('native_queue'):
        import sports_loop_router
        try:
            return sports_loop_router.play(source['native_queue'], logger, owner=source.get('native_owner'), keep_owner_on_failure=bool(source.get('alts')))
        except InterruptedError:
            return False  # user stop/shutdown must not start a different provider
        except Exception as error:
            logger('jet: native queue ended (%s)' % type(error).__name__)
            values = [v for v in source.get('alts', []) if v][:TRIES]
            if not values:
                raise RuntimeError('no sports source opened') from None
    last = None
    for value in values:
        if source.get('native_owner'):
            import xbmcgui, sports_loop_router
            if xbmcgui.Window(10000).getProperty(sports_loop_router.OWNER) != source['native_owner']:
                return False
        try:
            return play_one(value, logger)
        except Exception as error:
            last = error
            import sports_pause
            if sports_pause.is_refusal(error):
                try:
                    import xbmcgui
                    home = xbmcgui.Window(10000)
                except Exception:
                    home = None
                sports_pause.Pause(window=home).pause()
                logger('jet: paused (access refused)')
            logger('jet: a source failed (%s); %s' % (type(error).__name__, 'trying the next' if value != values[-1] else 'no more'))
    raise last or RuntimeError('this source has nothing to play')


def resolver_host(address):
    """Only the hostname is logged; never the path, user info, query or headers."""
    try:
        host = urlsplit(str(address).split('|', 1)[0]).hostname or ''
        return host if re.fullmatch(r'[a-zA-Z0-9.-]{1,253}', host) else 'unknown'
    except ValueError:
        return 'unknown'


def is_loopback(address):
    try:
        return (urlsplit(address).hostname or '').lower() in ('127.0.0.1', 'localhost', '::1')
    except ValueError:
        return False


def hold_local_proxy(xbmc, address, startup_seconds=20):
    """The scraper's local HTTP server lives on this script's daemon thread."""
    player, monitor = xbmc.Player(), xbmc.Monitor()
    deadline, started = time.monotonic() + startup_seconds, False
    while not monitor.abortRequested():
        if player.isPlaying():
            try:
                current = player.getPlayingFile().split('|', 1)[0]
            except Exception:
                current = ''
            if current == address:
                started = True
            elif current and started:
                return
        elif started:
            return
        if not started and time.monotonic() >= deadline:
            return
        if monitor.waitForAbort(0.5):
            return


def play_one(play_value, logger=log):
    """One add-on's stream of a game. Raises when it cannot be opened."""
    import xbmc
    import xbmcgui
    value = json.loads(play_value)
    import sports_independent
    import sports_fawa
    import sports_loop_routes
    if value.get('e') == sports_loop_routes.NAME:
        route = value['l']['address']
        if not sports_loop_routes.valid_route(route):
            raise ValueError('invalid Loop playback route')
        sports_loop_routes.prepare_proxy()
        logger('sports: playing via The Loop')
        xbmc.Player().play(route)
        return True
    if value.get('e') == sports_fawa.NAME:
        address = sports_fawa.resolve(value['l']['address'])
        item = xbmcgui.ListItem(path=address)
        item.setMimeType('application/x-mpegURL')
        item.setProperty('inputstream', 'inputstream.ffmpegdirect')
        item.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
        item.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
        xbmc.Player().play(address, item)
        _play_session.proxy_url = address
        logger('sports: playing FawaNews via local proxy')
        return True
    if value.get('e') == sports_independent.NAME:
        address, headers = sports_independent.resolve(value['l']['address'], note=logger)
        logger('sports: playing independent source via JetProxy')
        xbmc.Player().play(proxy_path(address, headers))
        return True
    import sports_pause
    try:
        home = xbmcgui.Window(10000)
    except Exception:
        home = None
    if sports_pause.Pause(window=home).active():
        logger('jet: paused (access refused)')
        raise RuntimeError('JetExtractors paused')
    module, reason = import_jet()
    if module is None:
        raise RuntimeError('JetExtractors missing: %s' % reason)
    from jetextractors.models import JetLink
    link = JetLink.from_dict(value['l'])
    extractor = module.get_extractor(value['e'])
    if extractor is None:
        raise RuntimeError('scraper %s not found' % value['e'])
    last = None
    for final in candidates(module, extractor, link):
        try:
            address = unquote(final.address) if final.unquote and re.search(r'%3[Aa]%2[Ff]', final.address) else final.address
            if getattr(final, 'resolveurl', False):
                import resolveurl
                host = resolver_host(address)
                logger('jet: ResolveURL trying host %s' % host)
                address = resolveurl.resolve(address) or ''
                if not address:
                    logger('jet: ResolveURL could not resolve host %s' % host)
                    raise RuntimeError('ResolveURL could not open this stream')
            address, sep, encoded_headers = address.partition('|')
            headers = dict(parse_qsl(encoded_headers, keep_blank_values=True)) if sep else {}
            headers.update(final.headers or {})
            local_proxy = is_loopback(address)
            use_proxy = bool(final.jetproxy or (not local_proxy and headers and '.m3u8' in address.lower()))
            logger('sports: playing %s via %s' % (value['e'], 'JetProxy' if use_proxy else 'Kodi'))
            if use_proxy:
                xbmc.Player().play(proxy_path(address, headers))
                return True
            playable = copy.copy(final)
            playable.address = address  # ResolveURL may have replaced the original embed URL.
            playable.headers = headers or None
            path = playable.xbmc_format() if hasattr(playable, 'xbmc_format') else address + ('|' + urlencode(headers) if headers else '')
            item = xbmcgui.ListItem(path=path)
            if getattr(final, 'inputstream', None) is not None:
                final.inputstream.set_properties(item)
            xbmc.Player().play(item.getPath(), item)
            if local_proxy:
                _play_session.proxy_url = address
            return True
        except Exception as error:
            last = error
            logger('jet: stream candidate failed (%s); trying next' % type(error).__name__)
    raise last or RuntimeError('no playable stream behind this source')
