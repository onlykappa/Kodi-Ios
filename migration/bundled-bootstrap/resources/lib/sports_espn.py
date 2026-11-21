"""Sports data from ESPN's public scoreboard feed (DEC-059; the owner chose a public schedule source on 2026-11-16 because none of the Loop add-ons
gives games on the phone).

One request per league for today and the next week (https://site.api.espn.com/apis/site/v2/sports/<sport>/<league>/scoreboard). It is a feed the
ESPN website itself uses; it has no key and no contract, so every field is read defensively and one league failing never fails the others. The
provider fills the contract of sports_model.py: live games (score, clock, how much is left), upcoming games, leagues, an overview. Sources (the
streams under a game) come from add-ons and are added by sports_provider; here every game starts with none ("No sources yet").
"""
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import sports_model as sm

BASE = 'https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard'
# The feed answers a date range with HTTP 400, a single date and the plain scoreboard with 200. The plain scoreboard is the feed's own idea of "today" and
# it lags: on 2026-11-20 at 10:25 ET it still answered the finished 2026-11-19 slate, so the owner's Sports page said "Nothing live, next game tomorrow"
# while that day's games (4:00 PM onwards) were on Apple Sports (ISSUE-399). So each league is asked three times: the plain scoreboard, today's date and
# tomorrow's (the answers are merged by event id). The feed's days are US Eastern days: a game that starts at 01:00 UTC belongs to the previous day.
EXTRA_DAYS = (0, 1)
FEED_DAY_SHIFT = 5 * 3600   # seconds from UTC to the feed's day (US Eastern, standard time)
TTL = 45           # seconds a fetched answer is reused (a page asks three or four things in a row)
TIMEOUT = 8        # seconds for one league
UA = 'KodiIOS/1.0'

# code, name, sport (sports_model.SPORT_ORDER), ESPN path, joiner, (periods, minutes each) or ('innings', n)
LEAGUES = (
    ('NFL', 'NFL', 'American football', 'football/nfl', 'at', (4, 15)),
    ('NCAAF', 'College Football', 'American football', 'football/college-football', 'at', (4, 15)),
    ('NBA', 'NBA', 'Basketball', 'basketball/nba', 'at', (4, 12)),
    ('WNBA', 'WNBA', 'Basketball', 'basketball/wnba', 'at', (4, 10)),
    ('NCAAB', 'College Basketball', 'Basketball', 'basketball/mens-college-basketball', 'at', (2, 20)),
    ('NHL', 'NHL', 'Hockey', 'hockey/nhl', 'at', (3, 20)),
    ('MLB', 'MLB', 'Baseball', 'baseball/mlb', 'at', ('innings', 9)),
    ('EPL', 'Premier League', 'Soccer', 'soccer/eng.1', 'vs', (2, 45)),
    ('LIGA', 'La Liga', 'Soccer', 'soccer/esp.1', 'vs', (2, 45)),
    ('BUN', 'Bundesliga', 'Soccer', 'soccer/ger.1', 'vs', (2, 45)),
    ('SERA', 'Serie A', 'Soccer', 'soccer/ita.1', 'vs', (2, 45)),
    ('LIG1', 'Ligue 1', 'Soccer', 'soccer/fra.1', 'vs', (2, 45)),
    ('UCL', 'UEFA Champions League', 'Soccer', 'soccer/uefa.champions', 'vs', (2, 45)),
    ('MLS', 'MLS', 'Soccer', 'soccer/usa.1', 'vs', (2, 45)),
    # One event rather than a two-team game: a tournament or a race weekend (a title, no opponent), and a fight card (its main event's two fighters).
    ('PGA', 'PGA Tour', 'Golf', 'golf/pga', '', 'event'),
    ('LPGA', 'LPGA Tour', 'Golf', 'golf/lpga', '', 'event'),
    ('UFC', 'UFC', 'Combat sports', 'mma/ufc', 'vs', 'fight'),
    ('F1', 'Formula 1', 'Motorsport', 'racing/f1', '', 'event'),
)


def _date(ts):
    t = time.gmtime(ts)
    return '%04d%02d%02d' % (t.tm_year, t.tm_mon, t.tm_mday)


def _epoch(text):
    """'2026-11-15T18:00Z' -> epoch seconds, or None."""
    try:
        t = time.strptime(str(text).replace('Z', '').split('.')[0][:16], '%Y-%m-%dT%H:%M')
        import calendar
        return calendar.timegm(t)
    except (ValueError, TypeError):
        return None


def _seconds(clock):
    """'8:41' -> 521; "67'" -> 4020; '45'+2'' -> 2820; '' -> None."""
    text = str(clock or '').replace("'", '').replace('′', '').strip()
    try:
        if ':' in text:
            minutes, seconds = text.split(':')[:2]
            return int(float(minutes)) * 60 + int(float(seconds))
        return int(float(text.split('+')[0])) * 60 + (int(float(text.split('+')[1])) * 60 if '+' in text else 0)
    except (ValueError, IndexError):
        return None


def _left(cfg, period, clock):
    """Share of the game left, 0..1, or None when it cannot be told."""
    try:
        period = int(period)
        if cfg[0] == 'innings':
            return max(0.02, min(1.0, (cfg[1] - period + 0.5) / cfg[1])) if period > 0 else None
        periods, minutes = cfg
        total = periods * minutes * 60.0
        secs = _seconds(clock)
        if secs is None or period < 1:
            return None
        if minutes == 45:   # soccer: the clock counts up through the whole match
            return max(0.02, min(1.0, 1 - secs / total))
        if period > periods:   # overtime
            return 0.02
        remaining = (periods - period) * minutes * 60 + secs   # the clock counts down inside a period
        return max(0.02, min(1.0, remaining / total))
    except (TypeError, ValueError):
        return None


def _mark(league, cfg, period):
    """'Q3', 'P2', 'H1' (halves), 'OT'."""
    if period > cfg[0]:
        return 'OT'
    return ('P' if league == 'NHL' else 'Q' if cfg[0] == 4 else 'H') + str(period)


def _clock(league, status, cfg):
    """'Q3 · 8:41', 'P2 · 12:10', 'Top 7th', "67'", 'Half'."""
    kind = ((status.get('type') or {}).get('name') or '')
    detail = (status.get('type') or {}).get('shortDetail') or ''
    period, shown = status.get('period') or 0, status.get('displayClock') or ''
    if kind == 'STATUS_HALFTIME':
        return 'Half'
    if cfg[0] == 'innings':
        return detail or 'Live'
    if cfg[1] == 45:
        return shown or detail or 'Live'
    if kind == 'STATUS_END_PERIOD' or (shown in ('0:00', '0.0') and period):
        return 'End of ' + _mark(league, cfg, period)
    mark = _mark(league, cfg, period)
    return '%s · %s' % (mark, shown) if shown else mark


def path_of(code):
    return next((row[3] for row in LEAGUES if row[0] == code), '')


def _venue(v):
    """('NRG Stadium', 'Houston, TX') from a scoreboard venue, or ('', '')."""
    try:
        a = v.get('address') or {}
        place = ', '.join(x for x in (a.get('city'), a.get('state') or a.get('country')) if x)
        return (v.get('fullName') or '', place)
    except AttributeError:
        return ('', '')


def _person(name):
    return {'id': '', 'record': '', 'split': '', 'code': (name or '???')[:4].upper(), 'name': name or '', 'score': None, 'crest': '',
            'aliases': [name] if name else []}


def parse_events(code, name, sport, joiner, kind, body, now):
    """(live, upcoming, finished) for a league whose events are not two-team games: golf and F1 (the event's title alone) and UFC (the card's main
    event: the last fight listed, its two fighters). A tournament that began and is not over is live (its round is the clock)."""
    live, upcoming, finished = [], [], 0
    for event in (body or {}).get('events') or []:
        try:
            status = event.get('status') or {}
            state = (status.get('type') or {}).get('state')
            start = _epoch(event.get('date'))
            comps = event.get('competitions') or [{}]
            if state not in ('pre', 'in', 'post') or start is None:
                continue
            if state == 'post':
                finished += 1
                continue
            title = event.get('name') or event.get('shortName') or name
            if kind == 'fight':
                fighters = [((c.get('athlete') or {}).get('displayName') or '') for c in (comps[-1].get('competitors') or [])]
                if len(fighters) != 2:
                    continue
                away, home = _person(fighters[0]), _person(fighters[1])
            else:
                away, home = _person(title), _person('')
                away['code'] = code
            game = {'id': 'espn:%s:%s' % (code, event.get('id')), 'league': code, 'league_name': name, 'sport': sport,
                    'state': 'live' if state == 'in' else 'upcoming', 'away': away, 'home': home, 'joiner': joiner, 'start': start,
                    'sources': [], 'path': path_of(code), 'venue': _venue((comps[0] or {}).get('venue')), 'title': title}
            if state == 'in':
                period = (comps[0].get('status') or {}).get('period') or status.get('period')
                game['clock'] = ('Round %s' % period) if kind == 'event' and period and sport == 'Golf' else 'Live'
                game['left'] = None
                live.append(game)
            elif start >= now - 600:
                upcoming.append(game)
        except (AttributeError, TypeError, KeyError, IndexError):
            continue
    return live, upcoming, finished


def parse(code, name, sport, joiner, cfg, body, now):
    """(live games, upcoming games, finished count) from one league's scoreboard answer."""
    if cfg in ('event', 'fight'):
        return parse_events(code, name, sport, joiner, cfg, body, now)
    live, upcoming, finished = [], [], 0
    for event in (body or {}).get('events') or []:
        try:
            comp = (event.get('competitions') or [{}])[0]
            status = comp.get('status') or event.get('status') or {}
            state = (status.get('type') or {}).get('state')
            start = _epoch(event.get('date'))
            teams = {c.get('homeAway'): c for c in comp.get('competitors') or []}
            if state not in ('pre', 'in', 'post') or start is None or 'home' not in teams or 'away' not in teams:
                continue
            if state == 'post':
                finished += 1
                continue

            def team(c):
                t = c.get('team') or {}
                rec = next((r.get('summary') for r in c.get('records') or [] if r.get('type') == 'total' or r.get('name') == 'overall'), '')
                split = next((r.get('summary') for r in c.get('records') or [] if r.get('type') == ('home' if c.get('homeAway') == 'home' else 'road')), '')
                out = {'id': str(t.get('id') or ''), 'record': rec or '', 'split': split or '',
                       'short': t.get('shortDisplayName') or t.get('name') or '', 'color': str(t.get('color') or '')[:6],
                       'code': (t.get('abbreviation') or t.get('shortDisplayName') or '???')[:4].upper(),
                       'name': t.get('displayName') or t.get('name') or 'Team', 'score': None, 'crest': t.get('logo') or '',
                       'aliases': list(dict.fromkeys(value for key in ('displayName', 'shortDisplayName', 'name', 'abbreviation') if (value := t.get(key))))}
                if state == 'in':
                    try:
                        out['score'] = int(float(c.get('score')))
                    except (TypeError, ValueError):
                        out['score'] = None
                return out
            game = {'id': 'espn:%s:%s' % (code, event.get('id')), 'league': code, 'league_name': name, 'sport': sport,
                    'state': 'live' if state == 'in' else 'upcoming', 'away': team(teams['away']), 'home': team(teams['home']),
                    'joiner': joiner, 'start': start, 'sources': [], 'path': path_of(code),
                    'venue': _venue(comp.get('venue')), 'week': ((event.get('week') or {}).get('number') or 0)}
            if state == 'in':
                game['clock'] = _clock(code, status, cfg)
                game['left'] = _left(cfg, status.get('period'), status.get('displayClock'))
                seconds = status.get('clock')
                if cfg[0] != 'innings' and cfg[1] != 45 and isinstance(seconds, (int, float)) and (status.get('period') or 0) > 0:
                    # a countdown clock (basketball, football, hockey): the seconds left, so the page can tick them between fetches (sm.live_clock)
                    game.update({'clock_secs': float(seconds), 'clock_mark': _mark(code, cfg, status.get('period') or 0),
                                 'clock_state': (status.get('type') or {}).get('name') or ''})
                live.append(game)
            elif start >= now - 600:   # a game that should have started a few minutes ago still shows as upcoming
                upcoming.append(game)
        except (AttributeError, TypeError, KeyError):
            continue   # one odd event never costs the league
    return live, upcoming, finished


def fetch_json(url, timeout=TIMEOUT):
    """The JSON at url, asked for gzipped (a league's answer is 100-200 KB plain)."""
    request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(request, timeout=timeout) as answer:
        raw = answer.read(8 * 1024 * 1024)
        if answer.headers.get('Content-Encoding') == 'gzip':
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode('utf-8', 'replace'))


SNAPSHOT_KEEP = 6 * 3600   # seconds a remembered answer may still be drawn first
FRESH_DISK = 45            # seconds: an answer on disk this young was written by the service's loop (sports_data) and needs no refresh at all
REFRESH_SKIP = 10          # a page's own refresh is skipped when the answer on disk is younger than this


class EspnProvider:
    """The contract's provider over the ESPN feed. `fetch(url)` is injectable (tests)."""

    def __init__(self, fetch=None, clock=time.time, leagues=None, snapshot_path=None):
        self.fetch, self.clock = fetch, clock   # None: fetch_json, looked up at each call
        self.snapshot_path = snapshot_path      # the last answer is kept here, so a page opened after a restart draws it at once (owner: "a black screen for a second")
        self.saved_at = 0.0
        self.disk_seen = 0.0   # modification time of the file the in-memory answer came from or was last compared with
        self.ttl = TTL   # the phone's provider lowers it (sports_hybrid.TTL) so scores stay live
        self.league_defs = tuple(entry for entry in LEAGUES if leagues is None or entry[0] in leagues)
        self.lock = threading.Lock()
        self.snapshot = None   # {'at', 'live', 'upcoming', 'leagues', 'finished'}

    def _log(self, text):
        """One line in kodi.log; the pages only say "can't load", so the reason goes here."""
        try:
            import xbmc
            xbmc.log('Kodi iOS Sports: ' + text, xbmc.LOGINFO)
        except ImportError:
            pass

    # -- the last answer on disk
    def _read_disk(self):
        try:
            import json
            with open(self.snapshot_path, encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, dict) and all(key in data for key in ('at', 'live', 'upcoming', 'leagues')) and self.clock() - data['at'] < SNAPSHOT_KEEP:
                return data
        except (OSError, ValueError, TypeError):
            pass
        return None

    def _adopt_newer_disk(self):
        """Another process (the service's loop, another page) wrote a newer answer: take it instead of asking ESPN again. Lock held by the caller."""
        if not self.snapshot_path:
            return False
        try:
            import os
            stamp = os.path.getmtime(self.snapshot_path)
        except OSError:
            return False
        if stamp <= self.disk_seen:
            return False
        self.disk_seen = stamp
        data = self._read_disk()
        if data and (self.snapshot is None or data['at'] > self.snapshot['at']):
            self.snapshot = data
            return True
        return False

    def _write_disk(self, snapshot):
        if not self.snapshot_path or self.clock() - self.saved_at < 4:
            return
        try:
            import json
            import os
            import tempfile
            folder = os.path.dirname(self.snapshot_path) or '.'
            os.makedirs(folder, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=folder)
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                json.dump(snapshot, out, separators=(',', ':'), default=str)
            os.replace(temp, self.snapshot_path)
            self.saved_at = self.clock()
        except (OSError, TypeError, ValueError):
            pass

    def remembered(self):
        """True while the answer on offer is the one kept from last time (or one is waiting on disk to be offered): the real one is on its way."""
        if self.snapshot is not None:
            return bool(self.snapshot.get('remembered'))
        if not self.snapshot_path:
            return False
        data = self._read_disk()
        return data is not None and self.clock() - data['at'] > FRESH_DISK   # younger than that, the service kept it current: nothing is on its way

    def _refresh_later(self):
        def run():
            try:
                self._load(force=True)
            except Exception as error:
                self._log('background refresh: %s' % type(error).__name__)
        threading.Thread(target=run, daemon=True).start()

    # -- loading
    def _load(self, force=False):
        with self.lock:
            now = int(self.clock())
            if not force and self.snapshot is None and self.snapshot_path:
                remembered = self._read_disk()
                if remembered:   # the first read after a start: what was true last time, now; the real answer follows in the background
                    try:
                        import os
                        self.disk_seen = os.path.getmtime(self.snapshot_path)
                    except OSError:
                        pass
                    if now - remembered['at'] <= FRESH_DISK:   # the service kept it current: nothing to wait for or refresh
                        self.snapshot = dict(remembered)
                        return self.snapshot
                    self.snapshot = dict(remembered, remembered=True)
                    self._refresh_later()
                    return self.snapshot
            if not force and self.snapshot and not self.snapshot.get('remembered') and self.snapshot['at'] != now:
                self._adopt_newer_disk()
            if not force and self.snapshot and self.snapshot.get('remembered'):
                return self.snapshot
            if not force and self.snapshot and now - self.snapshot['at'] < self.ttl:
                return self.snapshot
            days = [_date(now - FEED_DAY_SHIFT + d * 86400) for d in EXTRA_DAYS]
            jobs = [(entry, [BASE % entry[3]] + ['%s?dates=%s' % (BASE % entry[3], day) for day in days]) for entry in self.league_defs]

            def one(job):
                entry, urls = job
                try:
                    merged, seen, first_error = {'events': []}, set(), None
                    for n, url in enumerate(urls):
                        try:
                            part = (self.fetch or fetch_json)(url)
                        except Exception as error:   # a later day failing keeps what the first answer gave
                            if n == 0:
                                raise
                            first_error = first_error or error
                            continue
                        for event in (part or {}).get('events') or []:
                            if event.get('id') not in seen:
                                seen.add(event.get('id'))
                                merged['events'].append(event)
                    return entry, merged, None
                except Exception as error:   # no network, a changed feed, a timeout: this league only
                    return entry, None, '%s: %s' % (type(error).__name__, str(error)[:90])
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(one, jobs))
            live, upcoming, leagues, finished, answered = [], [], [], 0, 0
            for (code, name, sport, _path, joiner, cfg), body, error in results:
                if error:
                    continue
                answered += 1
                lg, up, done = parse(code, name, sport, joiner, cfg, body, now)
                live += lg
                upcoming += up
                finished += done
                later = [g['start'] for g in up if g['start'] >= now]
                leagues.append({'code': code, 'name': name, 'sport': sport, 'live': len(lg), 'next': min(later) if later else None})
            if not answered:
                self._log('no league answered (%s)' % next((error for _, _, error in results if error), 'nothing asked'))
                if self.snapshot:
                    return self.snapshot   # the last good answer is better than none
                raise sm.SportsUnavailable('no league answered')
            self.snapshot = {'at': now, 'live': live, 'upcoming': upcoming, 'leagues': leagues, 'finished': finished}
            self._write_disk(self.snapshot)
            return self.snapshot

    # -- the contract
    def refresh(self):
        with self.lock:   # an answer another process wrote a moment ago is as good as asking again
            if self._adopt_newer_disk() and not self.snapshot.get('remembered') and self.clock() - self.snapshot['at'] < REFRESH_SKIP:
                return
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
        return {'updated': data['at'], 'live': len(data['live']), 'live_sports': sorted({g['sport'] for g in data['live']}),
                'next': min(coming) if coming else None, 'more_today': max(0, len(today) - 1),
                'leagues': len(data['leagues']), 'finished_today': data['finished']}
