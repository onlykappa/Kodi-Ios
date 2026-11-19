"""What the game page's Info section shows: venue, each team's recent form and record, and the standings table (board D, docs/design/sports-game-mockups.html).

All of it comes from ESPN's public feeds (the same host as the scoreboard, no key): the team schedule for the last five results, and the standings
for the table. Every field is read defensively and a section is simply left out when ESPN has nothing for it. Nothing here is a source or a stream.
"""
import os
import threading
import time

import sports_espn

SCHEDULE = 'https://site.api.espn.com/apis/site/v2/sports/%s/teams/%s/schedule'
STANDINGS = 'https://site.api.espn.com/apis/v2/sports/%s/standings?level=3'
TTL = 600          # seconds a fetched answer is reused
ROWS = 8           # the most standings rows the page draws
FORM = 5           # results shown per team

_cache = {}
_lock = threading.Lock()


def _get(url, fetch, now):
    with _lock:
        hit = _cache.get(url)
        if hit and now - hit[0] < TTL:
            return hit[1]
    body = fetch(url)
    with _lock:
        _cache[url] = (now, body)
    return body


def forget():
    with _lock:
        _cache.clear()


def form(body, team_id, last=FORM):
    """The last results of one team, oldest first, as 'W' / 'L' / 'D'."""
    out = []
    events = (body or {}).get('events') or []
    for event in sorted(events, key=lambda e: str(e.get('date') or '')):
        try:
            comp = (event.get('competitions') or [{}])[0]
            if ((comp.get('status') or {}).get('type') or {}).get('state') != 'post':
                continue
            mine = next(c for c in comp.get('competitors') or [] if str((c.get('team') or {}).get('id')) == str(team_id))
            other = next(c for c in comp.get('competitors') or [] if c is not mine)
            if mine.get('winner') is True:
                out.append('W')
            elif other.get('winner') is True:
                out.append('L')
            else:
                out.append('D')
        except (StopIteration, AttributeError, TypeError):
            continue
    return out[-last:]


def _stat(entry, *names):
    stats = {s.get('name'): s for s in entry.get('stats') or []}
    for name in names:
        if name in stats:
            shown = stats[name].get('displayValue')
            return shown if shown not in (None, '') else str(stats[name].get('value', ''))
    return ''


def _row(entry, rank, me):
    team = entry.get('team') or {}
    soccer = bool(_stat(entry, 'points') and _stat(entry, 'gamesPlayed'))
    ties = _stat(entry, 'ties')
    if soccer:
        cols = (_stat(entry, 'wins'), ties, _stat(entry, 'losses'), _stat(entry, 'points'))
    else:
        cols = (_stat(entry, 'wins'), _stat(entry, 'losses'), ties if ties not in ('', '0') else '', _stat(entry, 'winPercent'))
    logos = team.get('logos') or [{}]
    names = [team.get(k) for k in ('shortDisplayName', 'name', 'displayName', 'abbreviation') if team.get(k)]
    short = next((n for n in names if len(n) <= 16), names[-1][:16] if names else '')   # one line of the column, never cut mid-word
    return {'rank': str(rank), 'team': short,
            'crest': logos[0].get('href', '') if isinstance(logos[0], dict) else '', 'cols': cols,
            'me': str(team.get('id')) in me, 'soccer': soccer}


def _groups(node, path=()):
    """Every leaf table of the standings answer: (names from the top, entries)."""
    out = []
    path = path + (node.get('name') or '',)
    entries = (node.get('standings') or {}).get('entries')
    if entries:
        out.append((path, entries))
    for child in node.get('children') or []:
        out += _groups(child, path)
    return out


def _cut(rows):
    """At most ROWS rows; a game team below the cut replaces the last row so it never vanishes."""
    keep = rows[:ROWS]
    for extra in rows[ROWS:]:
        if extra['me'] and not any(r['me'] and r['team'] == extra['team'] for r in keep):
            keep = keep[:ROWS - 1] + [extra]
    return keep


def _view(name, title, rows):
    rows = _cut(rows)
    soccer = any(r['soccer'] for r in rows)
    if soccer:
        cols = ('W', 'D', 'L', 'PTS')
    else:
        cols = ('W', 'L', 'T' if any(r['cols'][2] for r in rows) else '', 'PCT')
    return {'name': name, 'title': title, 'cols': cols, 'rows': rows}


def standings(body, team_ids):
    """{'views': [...]} or None. Each view is {'name', 'title', 'cols', 'rows'}.

    The first view is the smallest table that holds a game team (the division, or the league's table); a second, 'Wild Card', is the whole conference
    ordered by playoff seed, for sports that have divisions."""
    me = {str(t) for t in team_ids if t}
    groups = _groups(body or {})
    own = [g for g in groups if any(str((e.get('team') or {}).get('id')) in me for e in g[1])]
    if not own:
        return None
    path, entries = min(own, key=lambda g: len(g[1]))
    name = path[-1]
    if name[:4].isdigit() and len(path) > 1:   # '2026-27 English Premier League' -> the league's own name
        name = path[-2]
    rows = [_row(e, n, me) for n, e in enumerate(entries, 1)]
    divisions = len(path) > 2
    views = [_view('Divisional' if divisions else 'Table', name, rows)]
    if divisions:
        conf = [e for g in groups if g[0][:-1] == path[:-1] for e in g[1]]
        ordered = sorted(conf, key=lambda e: int(_stat(e, 'playoffSeed') or 999))
        wild = [_row(e, n, me) for n, e in enumerate(ordered, 1)]
        for row, entry in zip(wild, ordered):
            row['rank'] = _stat(entry, 'playoffSeed') or row['rank']
        views.append(_view('Wild Card', path[-2], wild))
    return {'views': views}


def sample():
    """The approved board D (Colts at Texans) for the desktop Kodi rig, with KODI_IOS_SPORTS=sample; never used in the app."""
    crest = lambda abbr: 'https://a.espncdn.com/i/teamlogos/nfl/500/%s.png' % abbr
    def row(n, team, w, l, pct, me=False):
        return {'rank': str(n), 'team': team, 'crest': crest({'Texans': 'hou', 'Jaguars': 'jax', 'Titans': 'ten', 'Colts': 'ind', 'Bills': 'buf', 'Chiefs': 'kc'}.get(team, '')), 'cols': (w, l, '', pct), 'me': me, 'soccer': False}
    div = [row(1, 'Texans', '6', '3', '.667', True), row(2, 'Jaguars', '5', '4', '.556'), row(3, 'Titans', '3', '6', '.333'), row(4, 'Colts', '3', '7', '.300', True)]
    wild = [row(1, 'Bills', '8', '1', '.889'), row(2, 'Chiefs', '7', '2', '.778'), row(3, 'Texans', '6', '3', '.667', True), row(4, 'Jaguars', '5', '4', '.556')]
    return {'venue': 'NRG Stadium', 'place': 'Houston, TX',
            'form': [{'name': 'Indianapolis Colts', 'record': '3-7', 'split': '1-4', 'side': 'Away', 'results': ['L', 'L', 'W', 'L', 'L']},
                     {'name': 'Houston Texans', 'record': '3-6', 'split': '2-2', 'side': 'Home', 'results': ['W', 'L', 'W', 'W', 'L']}],
            'standings': {'views': [_view('Divisional', 'AFC South', div), _view('Wild Card', 'American Football Conference', wild)]}}


def build(game, fetch=None, now=None):
    """The Info facts for a game: {'venue', 'place', 'form': [away, home], 'standings'}; a part is empty when ESPN has none."""
    if fetch is None and os.environ.get('KODI_IOS_SPORTS') == 'sample':
        return sample()
    fetch = fetch or sports_espn.fetch_json
    now = time.time() if now is None else now
    out = {'venue': '', 'place': '', 'form': [], 'standings': None}
    venue = game.get('venue') or ('', '')
    out['venue'], out['place'] = venue[0], venue[1]
    path = game.get('path') or sports_espn.path_of(game.get('league'))
    if not path:
        return out
    for side in ('away', 'home'):
        team = game.get(side) or {}
        results = []
        if team.get('id'):
            try:
                results = form(_get(SCHEDULE % (path, team['id']), fetch, now), team['id'])
            except Exception:
                results = []
        out['form'].append({'name': team.get('name', ''), 'record': team.get('record', ''), 'split': team.get('split', ''),
                            'side': 'Away' if side == 'away' else 'Home', 'results': results})
    try:
        out['standings'] = standings(_get(STANDINGS % path, fetch, now), [(game.get(s) or {}).get('id') for s in ('away', 'home')])
    except Exception:
        out['standings'] = None
    if not any(f['results'] or f['record'] for f in out['form']):
        out['form'] = []
    return out
