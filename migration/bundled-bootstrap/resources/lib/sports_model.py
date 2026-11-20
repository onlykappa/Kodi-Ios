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
import copy
import time

SPORT_ORDER = ('Soccer', 'Basketball', 'American football', 'Hockey', 'Baseball', 'Golf', 'Combat sports', 'Motorsport')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


class SportsUnavailable(Exception):
    """No add-on answered: the page shows "Can't load ... right now" with one Try again button."""


def parse_clock(text):
    """Seconds since midnight from Kodi's clock text: '16:05:09', '16:05', '4:05 PM', '04:05:09 AM' (12-hour phones). None when it is not a clock."""
    import re
    match = re.match(r'^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\s*$', str(text or ''))
    if not match:
        return None
    hours, minutes, seconds, half = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0), (match.group(4) or '').upper()
    if half:
        if not 1 <= hours <= 12:
            return None
        hours = hours % 12 + (12 if half == 'PM' else 0)
    if hours > 23 or minutes > 59 or seconds > 59:
        return None
    return hours * 3600 + minutes * 60 + seconds


def kodi_offset(utc_now=None):
    """Seconds east of UTC by Kodi's own clock (System.Time is the phone's local time, 12- or 24-hour), or None outside Kodi. Python's idea of
    the time zone can be UTC inside an iOS app, which would show every game at the wrong hour; Kodi's clock is what the phone shows."""
    try:
        import re
        import xbmc
        text = str(xbmc.getInfoLabel('System.Time(hh:mm:ss)') or '')
        if not re.search(r'[AaPp][Mm]', text):
            # A 12-hour phone writes '06:15:30' with no marker (on the phone this read as morning and every game showed 12 hours off): ask for the marker.
            marker = str(xbmc.getInfoLabel('System.Time(xx)') or '').strip()
            if re.match(r'^[AaPp][Mm]$', marker):
                text += ' ' + marker
        local = parse_clock(text)
    except Exception:
        return None
    if local is None:
        return None
    utc_now = time.time() if utc_now is None else utc_now
    delta = local - int(utc_now) % 86400
    delta = (delta + 12 * 3600) % 86400 - 12 * 3600      # into -12 h .. +12 h
    return int(round(delta / 900.0)) * 900                  # time zones are whole quarter hours


def device_offset(now=None):
    """Seconds east of UTC on this phone (daylight saving included). Kodi's own clock decides while the question is about the present, so a phone
    whose Python thinks it is UTC still shows its real local times; Python's table answers for another moment or outside Kodi."""
    local = time.localtime(now)
    python_offset = -(time.altzone if local.tm_isdst > 0 and time.daylight else time.timezone)
    if now is None or abs(now - time.time()) < 3600:
        kodi = kodi_offset()
        if kodi is not None:
            return kodi
    return python_offset


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


def start_text(start, now, offset):
    """The upcoming game's status, using the same countdown/day rules as the list."""
    if start < now:
        return 'Started'
    soon = soon_text(start, now)
    if soon:
        return 'Starts %s' % soon
    day = day_label(start, now, offset)
    return 'Starts %s' % (day.lower() if day in ('Today', 'Tomorrow') else day)


def order_sources(sources):
    """Best, then Also good, then other sources; preserve the provider's order within each rank."""
    return sorted(sources, key=lambda s: {'best': 0, 'good': 1}.get(s.get('tag'), 2))


def count_text(n, one, many=None):
    """'1 game', '3 games'."""
    return '%d %s' % (n, one if n == 1 else (many or one + 's'))


def until_text(start, now):
    """'in 2 h 10 min' / 'in 45 min' for a game that starts within a day, else ''."""
    seconds = start - now
    if not 0 <= seconds < 24 * 3600:
        return ''
    minutes = max(1, seconds // 60)
    hours, minutes = divmod(minutes, 60)
    return 'in %d h %d min' % (hours, minutes) if hours and minutes else 'in %d h' % hours if hours else 'in %d min' % minutes


def live_clock(game, now):
    """The game clock as it is now: 'Q3 · 4:12' counted down second by second from the last ESPN answer (clock_secs at clock_at) while the clock is
    running; otherwise the text ESPN gave. A stopped clock (timeout, end of a period), soccer and baseball keep ESPN's own text."""
    secs, at = game.get('clock_secs'), game.get('clock_at')
    if secs is None or at is None or not game.get('clock_running') or game.get('state') != 'live':
        return game.get('clock') or ''
    left = secs - min(max(0, now - at), 90)   # never run on more than 90 s without a fresh answer
    if left <= 0:
        return game.get('clock') or ''
    text = '%d:%02d' % divmod(int(left), 60)
    return '%s · %s' % (game['clock_mark'], text) if game.get('clock_mark') else text


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
    if not game['home']['name']:   # a tournament or a race weekend: the event's own title
        return game['away']['name']
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
_ESPN = 'https://a.espncdn.com/i/teamlogos/%s.png'
SAMPLE_CRESTS = {   # real ESPN crest addresses for the sample teams, so the desktop rig shows logos (the app takes the address from the feed)
    'ARS': _ESPN % 'soccer/500/359', 'CHE': _ESPN % 'soccer/500/363', 'RS': _ESPN % 'soccer/500/89', 'AC': _ESPN % 'soccer/500/93',
    'BOS': _ESPN % 'nba/500/bos', 'DEN': _ESPN % 'nba/500/den', 'LAL': _ESPN % 'nba/500/lal', 'GSW': _ESPN % 'nba/500/gs',
    'TOR': _ESPN % 'nhl/500/tor', 'MTL': _ESPN % 'nhl/500/mtl', 'KC': _ESPN % 'nfl/500/kc', 'BUF': _ESPN % 'nfl/500/buf'}


def _team(code, name, score=None, color=''):
    team = {'code': code, 'name': name, 'score': score, 'crest': SAMPLE_CRESTS.get(code, '')}
    if color:   # a few sample teams carry the colour ESPN gives, so the game page's glow can be looked at in the rig
        team['color'] = color
    return team


def _src(addon, quality, language, tag='', also=()):
    return {'id': '%s|%s|%s' % (addon, quality, language), 'addon': addon, 'quality': quality, 'language': language,
            'tag': tag, 'also': list(also), 'play': 'sample://%s/%s/%s' % (addon, quality, language)}


class Sample:
    """A provider with the approved boards' sample data, times relative to `now` (default: 6:45 PM today, so the first game is in
    45 minutes). Used by the tests and the rig; `fail=True` makes every call raise SportsUnavailable."""

    def __init__(self, now=None, offset=0, fail=False, quiet=False):
        self.offset = offset
        self.fail = fail
        ticking = now is None   # the rig (no fixed `now`): the basketball and football clocks count down for real; tests keep fixed data
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
        if ticking:
            for game in self.live:
                if game['id'] in ('nba-1', 'nfl-1'):
                    secs = {'nba-1': 252.0, 'nfl-1': 521.0}[game['id']]
                    game.update({'clock_secs': secs, 'clock_at': time.time(), 'clock_mark': 'Q3', 'clock_running': True})
        self.upcoming = [
            g('epl-1', 'EPL', 'Soccer', 'upcoming', _team('ARS', 'Arsenal'), _team('CHE', 'Chelsea'), now + 45 * 60, lname='Premier League',
              sources=[_src('The Loop', '1080p', 'English', 'best', ['Loop TV']), _src('Loop Guide', '720p', 'English', 'good')]),
            g('liga-1', 'LIGA', 'Soccer', 'upcoming', _team('RS', 'Real Sociedad', color='0A4EA0'), _team('AC', 'Athletic Club', color='D4001A'), now + 75 * 60, lname='La Liga'),
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
                         ('MLB', 'MLB', 'Baseball'), ('PGA', 'PGA Tour', 'Golf'), ('UFC', 'UFC', 'Combat sports'), ('F1', 'Formula 1', 'Motorsport')]

    def _check(self):
        if self.fail:
            raise SportsUnavailable('sample provider set to fail')

    def refresh(self):
        self._check()

    def live_games(self, league=None):
        self._check()
        return copy.deepcopy(filter_league(order_live(self.live), league))   # copies: a caller's edits never reach the provider

    def upcoming_games(self, league=None):
        self._check()
        return copy.deepcopy(filter_league(sorted(self.upcoming, key=lambda g: g['start']), league))

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
        return copy.deepcopy(next((g for g in self.live + self.upcoming if g['id'] == gid), None))

    def overview(self):
        self._check()
        today = day_label(self.now, self.now, self.offset)
        later = [g for g in self.upcoming if day_label(g['start'], self.now, self.offset) == today]
        return {'updated': self.now, 'live': len(self.live), 'live_sports': sorted({g['sport'] for g in self.live}),
                'next': min(g['start'] for g in self.upcoming), 'more_today': max(0, len(later) - 1),
                'leagues': len(self._leagues), 'finished_today': 6}
