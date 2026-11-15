"""Sports: the data contract and the plain rules every Sports page shares (DEC-055, DEC-056, DEC-057).

Pages never talk to an add-on. They ask a *provider* (`Sample` below for tests and the rig, only when KODI_IOS_SPORTS=sample; The Loop's
provider next, later others) through sports_provider.get() and get plain dicts back:

    game    {'id', 'league' (short code: 'NFL'), 'league_name', 'sport', 'state' ('live' | 'upcoming'),
             'away': team, 'home': team, 'joiner' ('vs' | 'at'), 'start' (epoch seconds),
             'clock' ('Q3 · 8:41', live only), 'left' (share of the game left 0..1, live only, None if unknown),
             'sources': [source]}
    team    {'code' (3 letters), 'name', 'score' (int, live only), 'crest' (a picture path or '')}
    source  {'id', 'addon' ('The Loop'), 'quality' ('1080p'), 'language' ('English'), 'tag' ('best' | 'good' | ''),
             'also': ['Loop TV'] (the other add-ons that have this stream), 'play' (what the play path is given, opaque)}
    league  {'code', 'name', 'sport', 'live' (number of live games), 'next' (epoch seconds of the next game or None)}
    overview {'updated' (epoch), 'live' (number of live games), 'live_sports' [names], 'next' (epoch or None), 'more_today' (int),
              'leagues' (int), 'finished_today' (int)}

A provider has: overview(), live_games(league=None), upcoming_games(league=None), leagues(), game(id), refresh(). Each raises
SportsUnavailable when no add-on answered at all (the pages then show the "can't load" state; one failing add-on never raises).
Times are epoch seconds; the helpers below turn them into the phone's own wording, with the time-zone offset passed in so they test.
"""
import time

SPORT_ORDER = ('Soccer', 'Basketball', 'American football', 'Hockey', 'Baseball', 'Combat sports', 'Motorsport')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


class SportsUnavailable(Exception):
    """No add-on answered: the page shows "Can't load ... right now" with one Try again button."""


def device_offset(now=None):
    """Seconds east of UTC on this phone right now (daylight saving included)."""
    local = time.localtime(now)
    return -(time.altzone if local.tm_isdst > 0 and time.daylight else time.timezone)


# --- time wording ------------------------------------------------------------------------------------------------------
def _local(ts, offset):
    return time.gmtime(ts + offset)


def clock_text(start, offset):
    """'7:30 PM'."""
    t = _local(start, offset)
    return '%d:%02d %s' % (t.tm_hour % 12 or 12, t.tm_min, 'AM' if t.tm_hour < 12 else 'PM')


def day_label(start, now, offset):
    """'Today', 'Tomorrow', else 'Sat, Nov 21'."""
    day = lambda ts: (ts + offset) // 86400
    gap = day(start) - day(now)
    if gap == 0:
        return 'Today'
    if gap == 1:
        return 'Tomorrow'
    t = _local(start, offset)
    return '%s, %s %d' % (WEEKDAYS[t.tm_wday], MONTHS[t.tm_mon - 1], t.tm_mday)


def soon_text(start, now):
    """'in 45 min' when the game starts within the hour (and has not started), else ''."""
    minutes = (start - now) // 60
    return 'in %d min' % max(1, minutes) if 0 <= start - now < 3600 else ''


def count_text(n, one, many=None):
    """'1 game', '3 games'."""
    return '%d %s' % (n, one if n == 1 else (many or one + 's'))


def sources_text(n):
    """'No sources yet', '1 source', '2 sources'."""
    return 'No sources yet' if not n else count_text(n, 'source')


def updated_text(updated, now, offset):
    """The landing and page subtitles: 'Updated just now', 'Updated 5 min ago', 'Updated at 7:30 PM' (a day or more: 'Updated Sat, Nov 21')."""
    gap = now - updated
    if gap < 60:
        return 'Updated just now'
    if gap < 3600:
        return 'Updated %d min ago' % (gap // 60)
    if day_label(updated, now, offset) == 'Today':
        return 'Updated at %s' % clock_text(updated, offset)
    return 'Updated %s' % day_label(updated, now, offset)


def versus(game):
    """'Arsenal vs Chelsea' or 'Kansas City Chiefs at Buffalo Bills' (away first)."""
    return '%s %s %s' % (game['away']['name'], game.get('joiner') or 'vs', game['home']['name'])


# --- ordering and grouping --------------------------------------------------------------------------------------------
def order_live(games):
    """Closest to its end first (DEC-055); a game whose end cannot be told goes last, by start time."""
    return sorted(games, key=lambda g: (g.get('left') is None, g.get('left') if g.get('left') is not None else 0, g.get('start', 0)))


def group_by_day(games, now, offset):
    """[(label, [games])], soonest first, a day at a time (DEC-056)."""
    out = []
    for g in sorted(games, key=lambda g: g['start']):
        label = day_label(g['start'], now, offset)
        if out and out[-1][0] == label:
            out[-1][1].append(g)
        else:
            out.append((label, [g]))
    return out


def order_leagues(leagues):
    """[(sport, [leagues])]: sports with something live first, then the rest in SPORT_ORDER; inside a sport the leagues with
    something live first, then the soonest next game, then the name (DEC-057)."""
    by = {}
    for lg in leagues:
        by.setdefault(lg['sport'], []).append(lg)

    def sport_key(sport):
        live = sum(l.get('live', 0) for l in by[sport])
        rank = SPORT_ORDER.index(sport) if sport in SPORT_ORDER else len(SPORT_ORDER)
        return (live == 0, rank, sport)
    return [(s, sorted(by[s], key=lambda l: (not l.get('live'), l.get('next') is None, l.get('next') or 0, l['name'])))
            for s in sorted(by, key=sport_key)]


def league_detail(league, now, offset):
    """(live text, next text) of a league row: ('1 live', 'next today 9:15 PM'), ('', 'Next today 7:30 PM') or ('', '')."""
    live = '%d live' % league['live'] if league.get('live') else ''
    nxt = ''
    if league.get('next') is not None and league['next'] >= now:
        word = 'next' if live else 'Next'
        label = day_label(league['next'], now, offset)
        label = label.lower() if label in ('Today', 'Tomorrow') else label
        nxt = '%s %s %s' % (word, label, clock_text(league['next'], offset))
    return live, nxt


def filter_league(games, code):
    """The games of one league (a league page is Live Now and Upcoming filtered, DEC-057)."""
    return [g for g in games if g['league'] == code] if code else list(games)


def league_codes(games):
    """The league chips of a list: 'All' and each league that has a game, most games first, then by code."""
    counts = {}
    for g in games:
        counts[g['league']] = counts.get(g['league'], 0) + 1
    return ['All'] + sorted(counts, key=lambda c: (-counts[c], c))


# --- sample data (the approved boards) ---------------------------------------------------------------------------------
def _team(code, name, score=None):
    return {'code': code, 'name': name, 'score': score, 'crest': ''}


def _src(addon, quality, language, tag='', also=()):
    return {'id': '%s|%s|%s' % (addon, quality, language), 'addon': addon, 'quality': quality, 'language': language,
            'tag': tag, 'also': list(also), 'play': 'sample://%s/%s/%s' % (addon, quality, language)}


class Sample:
    """A provider with the approved boards' sample data, times relative to `now` (default: 6:45 PM today, so the first game is in
    45 minutes). Used by the tests and the rig; `fail=True` makes every call raise SportsUnavailable."""

    def __init__(self, now=None, offset=0, fail=False, quiet=False):
        self.offset = offset
        self.fail = fail
        if now is None:
            now = int(time.time())
        self.now = now
        at = lambda days, h, m: (now + offset) // 86400 * 86400 - offset + days * 86400 + h * 3600 + m * 60
        g = lambda gid, lg, sport, state, away, home, start, joiner='vs', clock='', left=None, sources=(), lname=None: {
            'id': gid, 'league': lg, 'league_name': lname or lg, 'sport': sport, 'state': state, 'away': away, 'home': home,
            'joiner': joiner, 'start': start, 'clock': clock, 'left': left, 'sources': list(sources)}
        self.live = [
            g('ucl-1', 'UCL', 'Soccer', 'live', _team('BMG', 'Borussia Mönchengladbach', 2), _team('BHA', 'Brighton & Hove Albion', 1),
              now - 67 * 60, clock='67′', left=0.26, lname='UEFA Champions League',
              sources=[_src('Loop TV', '1080p', 'English', 'best'), _src('The Loop', '720p', 'German'),
                       _src('Sports Hub', '720p', 'English', 'good', ['Loop Guide'])]),
            g('nba-1', 'NBA', 'Basketball', 'live', _team('BOS', 'Boston Celtics', 88), _team('DEN', 'Denver Nuggets', 91),
              now - 85 * 60, clock='Q3 · 4:12', left=0.34,
              sources=[_src('The Loop', '1080p', 'English', 'best', ['Loop Guide']), _src('Loop TV', '720p', 'English', 'good')]),
            g('nfl-1', 'NFL', 'American football', 'live', _team('PIT', 'Pittsburgh Steelers', 17), _team('CLE', 'Cleveland Browns', 14),
              now - 100 * 60, joiner='at', clock='Q3 · 8:41', left=0.40,
              sources=[_src('The Loop', '1080p', 'English', 'best', ['Loop TV', 'Sports Hub']), _src('Loop Guide', '720p', 'English', 'good'),
                       _src('Sports Hub', '720p', 'Spanish')]),
            g('nhl-1', 'NHL', 'Hockey', 'live', _team('TOR', 'Toronto Maple Leafs', 1), _team('MTL', 'Montréal Canadiens', 1),
              now - 50 * 60, clock='P2 · 8:40', left=0.48, sources=[_src('The Loop', '720p', 'English', 'best', ['Loop TV'])]),
        ]
        self.upcoming = [
            g('epl-1', 'EPL', 'Soccer', 'upcoming', _team('ARS', 'Arsenal'), _team('CHE', 'Chelsea'), now + 45 * 60, lname='Premier League',
              sources=[_src('The Loop', '1080p', 'English', 'best', ['Loop TV']), _src('Loop Guide', '720p', 'English', 'good')]),
            g('liga-1', 'LIGA', 'Soccer', 'upcoming', _team('RS', 'Real Sociedad'), _team('AC', 'Athletic Club'), now + 75 * 60, lname='La Liga'),
            g('nba-2', 'NBA', 'Basketball', 'upcoming', _team('LAL', 'Los Angeles Lakers'), _team('GSW', 'Golden State Warriors'), now + 150 * 60,
              sources=[_src('The Loop', '1080p', 'English', 'best'), _src('Loop TV', '720p', 'English', 'good'), _src('Sports Hub', '720p', 'Spanish')]),
            g('nhl-2', 'NHL', 'Hockey', 'upcoming', _team('TOR', 'Toronto Maple Leafs'), _team('MTL', 'Montréal Canadiens'), at(1, 19, 0),
              sources=[_src('The Loop', '720p', 'English', 'best')]),
            g('nfl-2', 'NFL', 'American football', 'upcoming', _team('KC', 'Kansas City Chiefs'), _team('BUF', 'Buffalo Bills'), at(1, 20, 15), joiner='at'),
            g('epl-2', 'EPL', 'Soccer', 'upcoming', _team('MCI', 'Manchester City'), _team('BHA', 'Brighton & Hove Albion'), at(6, 12, 30), lname='Premier League'),
        ]
        if quiet:
            self.live = []   # nothing live: the grey Live Now tile
        self._leagues = [('EPL', 'Premier League', 'Soccer'), ('LIGA', 'La Liga', 'Soccer'), ('UCL', 'UEFA Champions League', 'Soccer'),
                         ('BUN', 'Bundesliga', 'Soccer'), ('NBA', 'NBA', 'Basketball'), ('WNBA', 'WNBA', 'Basketball'),
                         ('NFL', 'NFL', 'American football'), ('NCAAF', 'College Football', 'American football'), ('NHL', 'NHL', 'Hockey'),
                         ('MLB', 'MLB', 'Baseball'), ('UFC', 'UFC', 'Combat sports'), ('F1', 'Formula 1', 'Motorsport')]

    def _check(self):
        if self.fail:
            raise SportsUnavailable('sample provider set to fail')

    def refresh(self):
        self._check()

    def live_games(self, league=None):
        self._check()
        return filter_league(order_live(self.live), league)

    def upcoming_games(self, league=None):
        self._check()
        return filter_league(sorted(self.upcoming, key=lambda g: g['start']), league)

    def leagues(self):
        self._check()
        out = []
        for code, name, sport in self._leagues:
            lives = [g for g in self.live if g['league'] == code]
            later = [g['start'] for g in self.upcoming if g['league'] == code]
            out.append({'code': code, 'name': name, 'sport': sport, 'live': len(lives), 'next': min(later) if later else None})
        return out

    def game(self, gid):
        self._check()
        return next((g for g in self.live + self.upcoming if g['id'] == gid), None)

    def overview(self):
        self._check()
        today = day_label(self.now, self.now, self.offset)
        later = [g for g in self.upcoming if day_label(g['start'], self.now, self.offset) == today]
        return {'updated': self.now, 'live': len(self.live), 'live_sports': sorted({g['sport'] for g in self.live}),
                'next': min(g['start'] for g in self.upcoming), 'more_today': max(0, len(later) - 1),
                'leagues': len(self._leagues), 'finished_today': 6}
