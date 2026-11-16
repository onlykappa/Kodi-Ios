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
# The feed answers a date range with HTTP 400, a single date and the plain scoreboard (today, or the whole week for the NFL) with 200. So each league is
# asked twice: the plain scoreboard and tomorrow's date (the answers are merged by event id).
EXTRA_DAYS = (1,)
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


def parse(code, name, sport, joiner, cfg, body, now):
    """(live games, upcoming games, finished count) from one league's scoreboard answer."""
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
                out = {'code': (t.get('abbreviation') or t.get('shortDisplayName') or '???')[:4].upper(),
                       'name': t.get('displayName') or t.get('name') or 'Team', 'score': None, 'crest': t.get('logo') or ''}
                if state == 'in':
                    try:
                        out['score'] = int(float(c.get('score')))
                    except (TypeError, ValueError):
                        out['score'] = 0
                return out
            game = {'id': 'espn:%s:%s' % (code, event.get('id')), 'league': code, 'league_name': name, 'sport': sport,
                    'state': 'live' if state == 'in' else 'upcoming', 'away': team(teams['away']), 'home': team(teams['home']),
                    'joiner': joiner, 'start': start, 'sources': []}
            if state == 'in':
                game['clock'] = _clock(code, status, cfg)
                game['left'] = _left(cfg, status.get('period'), status.get('displayClock'))
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


class EspnProvider:
    """The contract's provider over the ESPN feed. `fetch(url)` is injectable (tests)."""

    def __init__(self, fetch=None, clock=time.time):
        self.fetch, self.clock = fetch or fetch_json, clock
        self.lock = threading.Lock()
        self.snapshot = None   # {'at', 'live', 'upcoming', 'leagues', 'finished'}

    def _log(self, text):
        """One line in kodi.log; the pages only say "can't load", so the reason goes here."""
        try:
            import xbmc
            xbmc.log('Kodi iOS Sports: ' + text, xbmc.LOGINFO)
        except ImportError:
            pass

    # -- loading
    def _load(self, force=False):
        with self.lock:
            now = int(self.clock())
            if not force and self.snapshot and now - self.snapshot['at'] < TTL:
                return self.snapshot
            days = [_date(now + d * 86400) for d in EXTRA_DAYS]
            jobs = [(entry, [BASE % entry[3]] + ['%s?dates=%s' % (BASE % entry[3], day) for day in days]) for entry in LEAGUES]

            def one(job):
                entry, urls = job
                try:
                    merged, seen, first_error = {'events': []}, set(), None
                    for n, url in enumerate(urls):
                        try:
                            part = self.fetch(url)
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
            return self.snapshot

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
        return {'updated': data['at'], 'live': len(data['live']), 'live_sports': sorted({g['sport'] for g in data['live']}),
                'next': min(coming) if coming else None, 'more_today': max(0, len(today) - 1),
                'leagues': len(data['leagues']), 'finished_today': data['finished']}
