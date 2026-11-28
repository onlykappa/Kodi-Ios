"""ESPN's summary of one game, read once and turned into plain rows for the Info page's Stats and Play-By-Play tabs (owner, 2026-11-28: "i love it do it").

One request per game (https://site.api.espn.com/apis/site/v2/sports/<league>/summary?event=<id>), asked to be compressed (a football game is 53 KB that way, 576 KB otherwise), kept
for 25 s while the game is live and 10 minutes once it is over. Every part is optional: what ESPN does not give for a sport is simply not in the answer. Pure parsing here (no Kodi);
sports_game_facts_page.py draws it and sports_game_facts.py fills the page."""
import gzip
import json
import re
import threading
import time
import urllib.request

URL = 'https://site.api.espn.com/apis/site/v2/sports/%s/summary?event=%s'
TTL_LIVE, TTL_DONE = 25, 600
TIMEOUT = 10
UA = 'KodiIOS/1.0'
MAX_BYTES = 3 * 1024 * 1024
STAT_ROWS, BLOCKS, BLOCK_ROWS, PLAYS = 10, 8, 5, 12
FOOTBALL = ('totalOffensivePlays', 'totalYards', 'yardsPerPlay', 'netPassingYards', 'rushingYards', 'firstDowns', 'thirdDownEff', 'turnovers', 'totalPenaltiesYards', 'possessionTime')
BASKETBALL = ('fieldGoalPct', 'threePointFieldGoalPct', 'freeThrowPct', 'totalRebounds', 'assists', 'turnovers', 'steals', 'blocks', 'fastBreakPoints', 'pointsInPaint')
PREFERRED_COLUMNS = ('MIN', 'PTS', 'REB', 'AST')
SKIP_GROUPS = ('fumbles', 'defensive', 'interceptions', 'kickReturns', 'puntReturns')
_cache = {}
_lock = threading.Lock()


def _number(text):
    found = re.search(r'-?\d+(?:\.\d+)?', str(text).replace(':', '.'))
    return float(found.group(0)) if found else None


def _text(value):
    return str(value if value is not None else '').strip()


def event_id(game):
    """The ESPN event number inside a game id ('espn:NFL:401873083'), or ''."""
    tail = str((game or {}).get('id') or '').split(':')[-1]
    return tail if tail.isdigit() else ''


def url_for(game):
    import sports_espn
    path = sports_espn.path_of((game or {}).get('league', ''))
    number = event_id(game)
    return URL % (path, number) if path and number else ''


def download(url, timeout=TIMEOUT):
    request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_BYTES + 1)
        if response.headers.get('Content-Encoding') == 'gzip':
            data = gzip.decompress(data)
    if len(data) > MAX_BYTES:
        raise ValueError('summary too large')
    return json.loads(data)


def fetch(game, get=download, clock=time.time):
    """The parsed detail of a game, or None (no such summary, ESPN down). Reused while fresh."""
    url = url_for(game)
    if not url:
        return None
    live = (game or {}).get('state') == 'live'
    with _lock:
        held = _cache.get(url)
    if held and clock() - held[0] < (TTL_LIVE if live else TTL_DONE):
        return held[1]
    try:
        detail = parse(get(url), game)
    except Exception:
        return held[1] if held else None
    with _lock:
        _cache[url] = (clock(), detail)
    return detail


def _odds(summary):
    picks = summary.get('pickcenter') or []
    if not picks:
        return None
    pick = picks[0]
    spread, total = pick.get('spread'), pick.get('overUnder')
    teams = {t.get('homeAway'): (t.get('team') or {}).get('abbreviation', '') for t in (summary.get('boxscore') or {}).get('teams', [])}
    if spread is None or total is None or len(teams) != 2:
        return None

    def whole(value):
        return '%d' % value if isinstance(value, (int, float)) else _text(value)

    def line(entry):
        return ('-%s' % abs(spread)) if entry.get('favorite') else ('+%s' % abs(spread))
    away, home = pick.get('awayTeamOdds') or {}, pick.get('homeTeamOdds') or {}
    return {'provider': _text((pick.get('provider') or {}).get('name')),
            'rows': [{'team': teams.get('away', ''), 'spread': line(away), 'spread_odds': whole(away.get('spreadOdds')), 'total': 'O %s' % total, 'total_odds': whole(pick.get('overOdds')), 'money': whole(away.get('moneyLine'))},
                     {'team': teams.get('home', ''), 'spread': line(home), 'spread_odds': whole(home.get('spreadOdds')), 'total': 'U %s' % total, 'total_odds': whole(pick.get('underOdds')), 'money': whole(home.get('moneyLine'))}]}


def _teams(summary):
    out = {}
    for entry in (summary.get('boxscore') or {}).get('teams', []):
        team = entry.get('team') or {}
        out[entry.get('homeAway')] = {'abbr': _text(team.get('abbreviation')), 'name': _text(team.get('shortDisplayName') or team.get('displayName')), 'color': _text(team.get('color'))[:6],
                                      'logo': _text(team.get('logo') or ((team.get('logos') or [{}])[0].get('href'))), 'stats': entry.get('statistics') or []}
    return out


def _stat_rows(teams):
    away, home = teams.get('away'), teams.get('home')
    if not away or not home:
        return []

    def find(entry, key):
        return next((s for s in entry['stats'] if s.get('name') == key), None)
    pairs = []
    for wanted in (FOOTBALL, BASKETBALL):
        keyed = [(key, find(away, key), find(home, key)) for key in wanted]
        pairs = [(a.get('label') or key, a.get('displayValue'), h.get('displayValue')) for key, a, h in keyed if a and h]
        if len(pairs) >= 4:
            break
    if len(pairs) < 4:   # another sport: the first rows ESPN gives
        pairs, seen = [], set()
        for a in away['stats']:
            label = _text(a.get('label') or a.get('name'))
            h = next((s for s in home['stats'] if s.get('name') == a.get('name')), None)
            if not label or label in seen or not h or a.get('displayValue') in (None, '') or h.get('displayValue') in (None, ''):
                continue
            seen.add(label)
            pairs.append((label, a['displayValue'], h['displayValue']))
    rows = []
    for label, a, h in pairs[:STAT_ROWS]:
        x, y = _number(a), _number(h)
        share = 0
        if x is not None and y is not None and x + y > 0:
            share = min(95, max(5, int(round(100 * x / (x + y) / 5.0)) * 5))
        rows.append({'label': _text(label), 'away': _text(a), 'home': _text(h), 'share': share})
    return rows


def _blocks(summary):
    out = []
    for block in (summary.get('boxscore') or {}).get('players', []):
        team = block.get('team') or {}
        for group in block.get('statistics') or []:
            labels = list(group.get('labels') or [])
            athletes = [a for a in group.get('athletes') or [] if len(a.get('stats') or []) >= len(labels) > 0]
            name = _text(group.get('name'))
            if not athletes or name in SKIP_GROUPS:
                continue
            columns = [labels.index(c) for c in PREFERRED_COLUMNS if c in labels] if all(c in labels for c in PREFERRED_COLUMNS) else list(range(min(5, len(labels))))
            order = athletes
            if 'PTS' in labels:
                order = sorted(athletes, key=lambda a: -(_number(a['stats'][labels.index('PTS')]) or 0))
            rows = []
            for a in order[:BLOCK_ROWS if 'PTS' in labels else 3]:
                person = a.get('athlete') or {}
                rows.append({'name': _text(person.get('shortName') or person.get('displayName')), 'pos': _text((person.get('position') or {}).get('abbreviation')),
                             'cells': [_text(a['stats'][i]) for i in columns]})
            out.append({'team': _text(team.get('shortDisplayName') or team.get('displayName')), 'logo': _text(team.get('logo')), 'title': name.title() if name else 'Players',
                        'labels': [_text(labels[i]) for i in columns], 'rows': rows})
    return out[:BLOCKS]


def _quarter(number):
    return {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}.get(number, 'OT' if number else '')


def _plays(summary, teams):
    out = []
    drives = ((summary.get('drives') or {}).get('previous')) or []
    if drives:   # football: one card per drive, the latest first
        for drive in reversed(drives[-PLAYS:]):
            team = drive.get('team') or {}
            color = _text(team.get('color') or next((t['color'] for t in teams.values() if t['name'] == _text(team.get('shortDisplayName'))), ''))[:6]
            out.append({'title': _text(drive.get('displayResult') or drive.get('result')), 'detail': _text(drive.get('description')),
                        'when': _quarter(((drive.get('start') or {}).get('period') or {}).get('number')), 'score': bool(drive.get('isScore')), 'color': color,
                        'team': _text(team.get('shortDisplayName') or team.get('displayName'))})
        return out
    plays = summary.get('plays') or []
    for play in reversed(plays[-PLAYS * 3:]):   # basketball, hockey, baseball: the latest plays
        text = _text(play.get('text') or play.get('shortText'))
        if not text:
            continue
        period = ((play.get('period') or {}).get('displayValue')) or _quarter((play.get('period') or {}).get('number'))
        clock = _text((play.get('clock') or {}).get('displayValue'))
        scoring = bool(play.get('scoringPlay'))
        tag = '%s %s – %s %s' % (teams.get('away', {}).get('abbr', ''), play.get('awayScore', ''), teams.get('home', {}).get('abbr', ''), play.get('homeScore', '')) if scoring and 'awayScore' in play else ''
        out.append({'title': ' · '.join(v for v in (period, clock) if v), 'detail': text, 'when': '', 'score': scoring, 'tag': tag, 'color': '', 'team': ''})
        if len(out) >= PLAYS:
            break
    if out:
        return out
    for event in reversed(summary.get('keyEvents') or []):   # soccer: the key events
        text = _text(event.get('text') or event.get('shortText'))
        if text:
            out.append({'title': _text((event.get('clock') or {}).get('displayValue')), 'detail': text, 'when': '', 'score': bool(event.get('scoringPlay')), 'tag': '', 'color': '',
                        'team': _text((event.get('team') or {}).get('displayName'))})
        if len(out) >= PLAYS:
            break
    return out


def parse(summary, game=None):
    """{'odds', 'stats', 'blocks', 'plays', 'teams'} from one ESPN summary; every part may be empty."""
    summary = summary or {}
    teams = _teams(summary)
    result = {'odds': None, 'stats': [], 'blocks': [], 'plays': [], 'teams': {k: {f: v[f] for f in ('abbr', 'name', 'color', 'logo')} for k, v in teams.items()}}
    for key, make in (('odds', lambda: _odds(summary)), ('stats', lambda: _stat_rows(teams)), ('blocks', lambda: _blocks(summary)), ('plays', lambda: _plays(summary, teams))):
        try:
            result[key] = make()
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            pass
    return result


# --- the Info window's properties ------------------------------------------------------------------------------------------------------------
def _argb(color, amount=.3):
    """'0a2343' -> 'FF....' lightened so a dark team colour still reads on black; 'FF8E8E93' (grey) when ESPN gives none."""
    color = (color or '')[:6]
    try:
        parts = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return 'FF8E8E93'
    return 'FF%02X%02X%02X' % tuple(round(v + (255 - v) * amount) for v in parts)


def _lines(text, width=48):
    """How many lines a play's text needs in the 860 px card (about 48 characters a line)."""
    return 1 if len(_text(text)) <= width else 2 if len(_text(text)) <= 2 * width - 8 else 3


def logos(detail):
    """The image addresses the window should download (team logos in the player tables)."""
    return [b['logo'] for b in (detail or {}).get('blocks', []) if b.get('logo')]


def props(detail, state='ready', crests=None, bar_base=9100):
    """(window properties, {control id: percent}) for the Stats and Play-By-Play tabs. `state` is 'loading', 'ready' or 'none'. Every slot not used is an empty string."""
    crests = crests or {}
    out = {'detail': state, 'odds.provider': ''}
    for r in range(2):
        for key in ('team', 'spread', 'so', 'total', 'to', 'money'):
            out['odds.r%d.%s' % (r, key)] = ''
    for n in range(STAT_ROWS):
        for key in ('label', 'away', 'home', 'pos', 'ac', 'hc'):
            out['ts.%d.%s' % (n, key)] = ''
    for n in range(BLOCKS):
        for key in ('team', 'logo', 'title', 'rows'):
            out['blk.%d.%s' % (n, key)] = ''
        for i in range(5):
            out['blk.%d.h%d' % (n, i)] = ''
        for r in range(BLOCK_ROWS):
            out['blk.%d.r%d.name' % (n, r)] = ''
            for i in range(5):
                out['blk.%d.r%d.c%d' % (n, r, i)] = ''
    for n in range(PLAYS):
        for key in ('title', 'detail', 'tag', 'score', 'color', 'form'):
            out['play.%d.%s' % (n, key)] = ''
    bars = {}
    if not detail or state != 'ready':
        return out, bars
    odds = detail.get('odds')
    if odds:
        out['odds.provider'] = odds['provider']
        for r, row in enumerate(odds['rows'][:2]):
            out.update({'odds.r%d.team' % r: row['team'], 'odds.r%d.spread' % r: row['spread'], 'odds.r%d.so' % r: row['spread_odds'], 'odds.r%d.total' % r: row['total'],
                        'odds.r%d.to' % r: row['total_odds'], 'odds.r%d.money' % r: row['money']})
    teams = detail.get('teams') or {}
    rows = (detail.get('stats') or [])[:STAT_ROWS]
    for n, row in enumerate(rows):
        key = 'ts.%d.' % n
        out.update({key + 'label': row['label'], key + 'away': row['away'], key + 'home': row['home'], key + 'pos': 'only' if len(rows) == 1 else 'first' if n == 0 else 'last' if n == len(rows) - 1 else 'mid',
                    key + 'ac': _argb((teams.get('away') or {}).get('color'), .35), key + 'hc': _argb((teams.get('home') or {}).get('color'), .35)})
        bars[bar_base + n] = row['share'] or 50
    last_team = None
    for n, block in enumerate((detail.get('blocks') or [])[:BLOCKS]):
        key = 'blk.%d.' % n
        if block['team'] != last_team:
            out[key + 'team'] = block['team']
            out[key + 'logo'] = crests.get(block.get('logo'), '')
            last_team = block['team']
        out[key + 'title'] = block['title']
        out[key + 'rows'] = '3' if len(block['rows']) <= 3 else '5'
        for i, label in enumerate(block['labels'][:5]):
            out['%sh%d' % (key, i)] = label
        for r, person in enumerate(block['rows'][:BLOCK_ROWS]):
            out['%sr%d.name' % (key, r)] = person['name'] + ((' ' + person['pos']) if person.get('pos') else '')
            for i, value in enumerate(person['cells'][:5]):
                out['%sr%d.c%d' % (key, r, i)] = value
    for n, play in enumerate((detail.get('plays') or [])[:PLAYS]):
        key = 'play.%d.' % n
        out.update({key + 'title': ' · '.join(v for v in (play.get('when'), play['title']) if v), key + 'detail': play['detail'], key + 'tag': play.get('tag') or play.get('team') or '',
                    key + 'score': 'true' if play.get('score') else '', key + 'color': _argb(play.get('color'), .35) if play.get('color') else '', key + 'form': str(_lines(play['detail']))})
    return out, bars
