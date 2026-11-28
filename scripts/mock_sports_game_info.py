#!/usr/bin/env python3
"""Mockup generator: the game's Info page (Stats / Play-By-Play / Standings) drawn from LIVE ESPN data, the same public feed the app reads
(site.api.espn.com), so a mock shows what the phone would show for a real game today. Evidence class: MOCKUP (browser render, not Kodi, not the phone).

usage: python3 -B scripts/mock_sports_game_info.py [OUT.html] [NFL_EVENT_ID]
The output holds live data and ESPN image addresses (not files); it is written outside the repository by default and is never committed."""
import html
import json
import re
import sys
import urllib.request

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/mock-info.html'


def get(path):
    request = urllib.request.Request(ESPN + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def esc(value):
    return html.escape(str(value if value is not None else ''))


def number(text):
    found = re.search(r'-?\d+(?:\.\d+)?', str(text).replace(':', '.'))
    return float(found.group(0)) if found else None


def lighten(color, amount=.35):
    color = (color or '808080')[:6]
    try:
        parts = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        parts = [128, 128, 128]
    return '#%02X%02X%02X' % tuple(round(p + (255 - p) * amount) for p in parts)


CSS = '''
:root{--bg:#000;--s1:#1C1C1E;--s2:#2C2C2E;--grey:rgba(235,235,245,.6);--sep:rgba(235,235,245,.2);--blue:#0A84FF;--bluet:#4FA8FF;--green:#30D158;--red:#FF453A}
*{box-sizing:border-box}body{margin:0;background:#111;color:#fff;font-family:Inter,-apple-system,system-ui,sans-serif;padding:24px 16px}
h1{font-size:20px;margin:0 0 4px}.note{color:var(--grey);font-size:13px;margin:0 0 20px;max-width:980px;line-height:1.45}.badge{display:inline-block;font-size:11px;font-weight:700;border-radius:6px;padding:1px 6px;background:#3a3a3c}
.row{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start}.col{width:402px}.cap{font-size:13px;font-weight:600;margin:0 0 8px}.cap span{color:var(--grey);font-weight:400}
.phone{width:402px;background:var(--bg);border-radius:34px;border:1px solid #333;padding:14px 14px 22px;overflow:hidden}
.strip{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:6px 4px 10px}.side{display:flex;align-items:center;gap:8px}.side img{width:44px;height:44px;object-fit:contain}.sc{font-size:34px;font-weight:700;letter-spacing:-.5px}.sc.dim{color:var(--grey)}
.mid{text-align:center;font-size:15px;font-weight:700}.mid small{display:block;color:var(--grey);font-weight:600;font-size:13px}.live{color:var(--red)}
.tabs{display:flex;justify-content:space-between;margin:2px 0 14px}.tab{flex:1;text-align:center;font-size:16px;font-weight:700;padding:9px 0;border-radius:20px;color:var(--grey)}.tab.on{background:#fff;color:#000}
.card{background:var(--s1);border-radius:16px;padding:14px;margin-bottom:12px}.ct{text-align:center;font-weight:700;font-size:16px;margin-bottom:10px;display:flex;justify-content:center;align-items:center;gap:8px}.ct img{width:22px;height:22px;object-fit:contain}
table{width:100%;border-collapse:collapse;font-size:15px}th{font-weight:500;color:var(--grey);text-align:right;padding:6px 3px;font-size:14px}td{text-align:right;padding:8px 3px;font-weight:600}th:first-child,td:first-child{text-align:left}td:first-child{font-weight:600}td:first-child i{font-style:normal;color:var(--grey);font-weight:500}
tr.sep td{border-top:1px solid var(--sep)}.odds td,.odds th{text-align:center}.odds small{display:block;color:var(--grey);font-weight:500;font-size:12px}.prov{color:var(--grey);font-size:12px;margin-top:8px}
.ts{display:grid;grid-template-columns:70px 1fr 70px;align-items:end;margin-bottom:12px}.ts b{font-size:21px}.ts b:last-child{text-align:right}.ts span{text-align:center;color:var(--grey);font-size:14px;padding-bottom:2px}
.bar{grid-column:1/4;display:flex;height:5px;gap:4px;margin-top:5px}.bar i{display:block;height:100%;border-radius:3px}
.seg{display:flex;background:var(--s2);border-radius:12px;padding:3px;margin-bottom:12px}.seg span{flex:1;text-align:center;padding:8px 0;font-size:15px;font-weight:600;border-radius:10px;color:var(--grey)}.seg span.on{background:#636366;color:#fff}
.q{display:flex;align-items:center;gap:10px;color:var(--grey);font-size:12px;font-weight:600;letter-spacing:.4px;margin:14px 0}.q:before,.q:after{content:"";flex:1;height:1px;background:var(--sep)}
.drive{background:var(--s1);border-radius:16px;padding:12px 14px;margin-bottom:10px;border-left:4px solid var(--c,#555)}.dh{display:flex;justify-content:space-between;gap:8px}.dt{font-weight:700;font-size:16px}.dd{color:var(--grey);font-size:14px;margin-top:2px}.tag{font-size:11px;font-weight:700;color:var(--green);background:rgba(48,209,88,.18);border-radius:8px;padding:2px 7px;height:fit-content}
.plays{margin-top:8px;border-top:1px solid var(--sep);padding-top:6px}.plays p{margin:6px 0;font-size:13.5px;line-height:1.35;color:#e5e5ea}.plays p small{color:var(--grey)}
.chev{text-align:center;color:var(--grey);font-size:14px;margin-top:2px}
.st td:nth-child(2){text-align:left}.st img{width:22px;height:22px;object-fit:contain;vertical-align:middle;margin-right:8px}.st tr.me td{background:rgba(255,255,255,.08)}.st td:first-child{color:var(--grey);width:22px}
.sess{display:flex;justify-content:space-between;gap:10px;padding:11px 0;border-bottom:1px solid var(--sep);font-size:15px}.sess:last-child{border:0}.sess small{display:block;color:var(--grey);font-size:12.5px;margin-top:2px}.pill{font-size:12px;font-weight:700;border-radius:8px;padding:2px 8px;height:fit-content;background:var(--s2)}.pill.l{background:rgba(255,69,58,.2);color:var(--red)}.pill.d{color:var(--grey)}
.legend{font-size:12.5px;color:var(--grey);line-height:1.5;max-width:900px;margin-top:22px}.legend b{color:#fff}
'''


def team_logo(team):
    return team.get('logo') or ((team.get('logos') or [{}])[0].get('href', ''))


def header_strip(event, tab, tabs):
    comp = event['competitions'][0]
    status = comp['status']['type']
    away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
    home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
    live = status['state'] == 'in'
    state = ('<span class="live">%s</span>' % esc(comp['status'].get('displayClock', '') and 'LIVE')) if live else esc(status.get('shortDetail') if status['state'] == 'pre' else 'Final')
    sub = esc(comp['status'].get('type', {}).get('shortDetail', '')) if live else ''
    out = ('<div class="strip"><div class="side"><img src="%s"><span class="sc dim">%s</span></div><div class="mid">%s<small>%s</small></div>'
           '<div class="side"><span class="sc">%s</span><img src="%s"></div></div>') % (
        esc(team_logo(away['team'])), esc(away.get('score', '')), state, sub, esc(home.get('score', '')), esc(team_logo(home['team'])))
    out += '<div class="tabs">%s</div>' % ''.join('<span class="tab%s">%s</span>' % (' on' if t == tab else '', esc(t)) for t in tabs)
    return out


def odds_card(summary):
    picks = summary.get('pickcenter') or []
    if not picks:
        return ''
    odds = picks[0]
    away, home = odds.get('awayTeamOdds') or {}, odds.get('homeTeamOdds') or {}
    spread = odds.get('spread')
    if spread is None or not odds.get('overUnder'):
        return ''

    def side(entry, fav):
        line = ('-%s' % abs(spread)) if entry.get('favorite') else ('+%s' % abs(spread))
        return line, ('%d' % entry['spreadOdds']) if isinstance(entry.get('spreadOdds'), (int, float)) else entry.get('spreadOdds', ''), entry.get('moneyLine', '')
    teams = summary['boxscore']['teams']
    names = {t['homeAway']: t['team']['abbreviation'] for t in teams}
    a, h = side(away, 0), side(home, 0)
    rows = ''.join('<tr><td>%s</td><td>%s<small>%s</small></td><td>%s<small>%s</small></td><td>%s</td></tr>' % (
        esc(names.get(k, '')), esc(v[0]), esc(v[1]), esc(w), esc(o), esc(v[2])) for k, v, w, o in (
        ('away', a, 'O %s' % odds['overUnder'], '%d' % odds['overOdds'] if isinstance(odds.get('overOdds'), (int, float)) else odds.get('overOdds', '')), ('home', h, 'U %s' % odds['overUnder'], '%d' % odds['underOdds'] if isinstance(odds.get('underOdds'), (int, float)) else odds.get('underOdds', ''))))
    return ('<div class="card"><div class="ct">Betting Odds</div><table class="odds"><tr><th>Team</th><th>Spread</th><th>Total</th><th>Moneyline</th></tr>%s</table>'
            '<div class="prov">Odds provided by %s</div></div>') % (rows, esc((odds.get('provider') or {}).get('name', '')))


FOOT_ROWS = [('totalOffensivePlays', 'Plays'), ('totalYards', 'Yards'), ('yardsPerPlay', 'Yards per Play'), ('netPassingYards', 'Passing Yards'), ('rushingYards', 'Rushing Yards'),
             ('firstDowns', '1st Downs'), ('thirdDownEff', '3rd Down Efficiency'), ('turnovers', 'Turnovers'), ('totalPenaltiesYards', 'Penalties (yards)'), ('possessionTime', 'Time of Possession')]


def team_stats_card(summary, wanted, title='Team Stats'):
    teams = {t['homeAway']: t for t in summary['boxscore']['teams']}
    if len(teams) != 2:
        return ''
    rows = ''
    for key, label in wanted:
        values = {}
        for side, t in teams.items():
            found = next((s for s in t['statistics'] if s.get('name') == key or s.get('label') == key), None)
            values[side] = found.get('displayValue') if found else None
        if None in values.values():
            continue
        a, h = number(values['away']), number(values['home'])
        bar = ''
        if a is not None and h is not None and a + h > 0:
            share = round(100 * a / (a + h))
            bar = '<div class="bar"><i style="width:%d%%;background:%s"></i><i style="width:%d%%;background:%s"></i></div>' % (
                max(share, 4), lighten(teams['away']['team'].get('color')), max(100 - share, 4), lighten(teams['home']['team'].get('color')))
        rows += '<div class="ts"><b>%s</b><span>%s</span><b>%s</b>%s</div>' % (esc(values['away']), esc(label), esc(values['home']), bar)
    return '<div class="card"><div class="ct">%s</div>%s</div>' % (esc(title), rows)


def player_cards(summary, groups, per_group=3, cols=5):
    out = ''
    for block in summary['boxscore']['players']:
        team = block['team']
        body = ''
        for group in block['statistics']:
            if group.get('name') not in groups:
                continue
            labels = group['labels'][:cols]
            people = group['athletes'][:per_group]
            if not people:
                continue
            body += '<tr class="sep"><th>%s</th>%s</tr>' % (esc(group['name'].title()), ''.join('<th>%s</th>' % esc(l) for l in labels))
            for person in people:
                a = person['athlete']
                pos = (a.get('position') or {}).get('abbreviation', '')
                body += '<tr><td>%s <i>%s</i></td>%s</tr>' % (esc(a.get('shortName') or a.get('displayName')), esc(pos), ''.join('<td>%s</td>' % esc(v) for v in person['stats'][:cols]))
        out += '<div class="card"><div class="ct"><img src="%s">%s</div><table>%s</table></div>' % (esc(team_logo(team)), esc(team.get('shortDisplayName') or team.get('displayName')), body)
    return out


def drives_frame(summary, event):
    drives = (summary.get('drives') or {}).get('previous') or []
    out = '<div class="seg"><span class="on">All Drives</span><span>Scoring Drives</span></div>'
    last_q = None
    first = True
    for drive in reversed(drives[-6:]):
        q = ((drive.get('start') or {}).get('period') or {}).get('number')
        if q != last_q and q:
            out += '<div class="q">START OF %s QUARTER</div>' % esc({1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH'}.get(q, '%dTH' % q))
            last_q = q
        team = drive.get('team') or {}
        color = lighten(((team.get('color')) or '808080'), .1)
        plays = ''
        if first:
            for play in (drive.get('plays') or [])[:4]:
                plays += '<p>%s</p>' % esc(play.get('text') or play.get('shortText'))
            first = False
        out += ('<div class="drive" style="--c:%s"><div class="dh"><div><div class="dt">%s</div><div class="dd">%s</div></div>%s</div>%s<div class="chev">⌄</div></div>') % (
            color, esc(drive.get('displayResult') or drive.get('result')), esc(drive.get('description')),
            '<span class="tag">SCORE</span>' if drive.get('isScore') else '', ('<div class="plays">%s</div>' % plays) if plays else '')
    return out


def standings_frame(summary):
    out = ''
    for group in (summary.get('standings') or {}).get('groups', [])[:2]:
        entries = group['standings']['entries']
        playing = {t['team']['id'] for t in summary['boxscore']['teams']}
        rows = ''
        for rank, entry in enumerate(entries, 1):
            stats = {s['name']: s['displayValue'] for s in entry['stats']}
            me = ' class="me"' if str(entry['id']) in playing else ''
            rows += '<tr%s><td>%d</td><td><img src="%s">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                me, rank, esc(entry['logo'][0]['href'] if isinstance(entry.get('logo'), list) and entry['logo'] else entry.get('logo')), esc(entry['team'] if isinstance(entry['team'], str) else entry['team'].get('displayName')), esc(stats.get('wins')), esc(stats.get('losses')), esc(stats.get('ties', '0')), esc(stats.get('winPercent')))
        out += '<div class="card st"><div class="ct">%s</div><table><tr><th></th><th></th><th>W</th><th>L</th><th>T</th><th>PCT</th></tr>%s</table></div>' % (esc(group.get('divisionHeader') or group.get('header')), rows)
    return out


def frame(caption, inner):
    return '<div class="col"><p class="cap">%s</p><div class="phone">%s</div></div>' % (caption, inner)


def nfl_frames(event_id):
    summary = get('football/nfl/summary?event=%s' % event_id)
    board = get('football/nfl/scoreboard')
    event = next((e for e in board['events'] if e['id'] == str(event_id)), None) or {'competitions': [summary['header']['competitions'][0]]}
    comp = summary['header']['competitions'][0]
    # the header block of a summary carries the same fields as a scoreboard event for the strip
    ev = {'competitions': [comp]}
    for c in comp['competitors']:
        c.setdefault('team', {})
    tabs = ('Stats', 'Play-By-Play', 'Standings')
    stats = header_strip(ev, 'Stats', tabs) + odds_card(summary) + team_stats_card(summary, FOOT_ROWS) + player_cards(summary, ('passing', 'rushing', 'receiving', 'kicking'))
    plays = header_strip(ev, 'Play-By-Play', tabs) + drives_frame(summary, ev)
    table = header_strip(ev, 'Standings', tabs) + standings_frame(summary)
    name = summary['header'].get('competitions', [{}])[0].get('competitors', [{}])[0].get('team', {}).get('displayName', '')
    return [frame('NFL · Stats <span>(live ESPN: boxscore, pickcenter)</span>', stats), frame('NFL · Play-By-Play <span>(live ESPN: drives)</span>', plays), frame('NFL · Standings <span>(live ESPN: standings)</span>', table)]


def nba_frame():
    board = get('basketball/nba/scoreboard')
    chosen = next((e for e in board['events'] if e['status']['type']['state'] == 'in'), None) or next((e for e in board['events'] if e['status']['type']['state'] == 'post'), None)
    if not chosen:
        return ''
    summary = get('basketball/nba/summary?event=%s' % chosen['id'])
    comp = summary['header']['competitions'][0]
    ev = {'competitions': [comp]}
    tabs = ('Stats', 'Play-By-Play', 'Standings')
    rows = [('fieldGoalPct', 'Field Goal %'), ('threePointFieldGoalPct', 'Three Point %'), ('freeThrowPct', 'Free Throw %'), ('totalRebounds', 'Rebounds'), ('assists', 'Assists'), ('turnovers', 'Turnovers'), ('steals', 'Steals'), ('blocks', 'Blocks')]
    inner = header_strip(ev, 'Stats', tabs) + odds_card(summary) + team_stats_card(summary, rows)
    for block in summary['boxscore']['players']:
        group = block['statistics'][0]
        people = sorted([p for p in group['athletes'] if len(p.get('stats') or []) >= len(group['labels'])], key=lambda p: -(number(p['stats'][group['labels'].index('PTS')]) or 0))[:5]
        cols = [group['labels'].index(l) for l in ('MIN', 'PTS', 'REB', 'AST') if l in group['labels']]
        body = '<tr><th>Player</th>%s</tr>' % ''.join('<th>%s</th>' % esc(group['labels'][i]) for i in cols)
        for p in people:
            a = p['athlete']
            body += '<tr><td>%s <i>%s</i></td>%s</tr>' % (esc(a.get('shortName')), esc((a.get('position') or {}).get('abbreviation', '')), ''.join('<td>%s</td>' % esc(p['stats'][i]) for i in cols))
        inner += '<div class="card"><div class="ct"><img src="%s">%s</div><table>%s</table></div>' % (esc(team_logo(block['team'])), esc(block['team'].get('shortDisplayName')), body)
    return frame('NBA · Stats <span>(live ESPN, %s)</span>' % esc(comp['status']['type'].get('shortDetail', '')), inner)


def f1_frame():
    board = get('racing/f1/scoreboard')
    event = board['events'][0]
    rows = ''
    for comp in event['competitions']:
        state = comp['status']['type']['state']
        label = (comp.get('type') or {}).get('abbreviation', '')
        names = {'FP1': 'Practice 1', 'FP2': 'Practice 2', 'FP3': 'Practice 3', 'Qual': 'Qualifying', 'Race': 'Race', 'SQ': 'Sprint Qualifying', 'SR': 'Sprint'}
        pill = '<span class="pill l">LIVE</span>' if state == 'in' else ('<span class="pill d">Final</span>' if state == 'post' else '<span class="pill">%s</span>' % esc(comp['date'][11:16] + ' UTC'))
        top = ''
        if state == 'post':
            ranked = sorted([c for c in comp.get('competitors', []) if c.get('order')], key=lambda c: c['order'])[:3]
            top = '<small>%s</small>' % esc('  ·  '.join('%d %s' % (c['order'], (c.get('athlete') or {}).get('shortName', '')) for c in ranked)) if ranked else ''
        rows += '<div class="sess"><div>%s<small>%s</small>%s</div>%s</div>' % (esc(names.get(label, label)), esc(comp['date'][:10]), top, pill)
    inner = ('<div class="strip"><div class="mid" style="text-align:left;font-size:20px">%s<small>%s</small></div></div>' % (esc(event['name']), esc((event.get('circuit') or {}).get('fullName', '')))) + '<div class="card"><div class="ct">Race weekend</div>%s</div>' % rows
    return frame('F1 · Weekend <span>(live ESPN: scoreboard sessions)</span>', inner)


def main():
    event_id = sys.argv[2] if len(sys.argv) > 2 else None
    if not event_id:
        board = get('football/nfl/scoreboard')
        done = [e for e in board['events'] if e['status']['type']['state'] in ('post', 'in')]
        event_id = (done or board['events'])[0]['id']
    frames = nfl_frames(event_id)
    for extra in (nba_frame, f1_frame):
        try:
            frames.append(extra())
        except Exception as error:   # one sport's feed being down never blocks the rest of the mock
            print('skipped', extra.__name__, type(error).__name__)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Game info page (mockup, live ESPN data)</title><style>%s</style></head><body>'
            '<h1>Game info page: Stats, Play-By-Play, Standings <span class="badge">MOCKUP</span></h1>'
            '<p class="note">Mockup in a browser (not the app, not Kodi). Every number is live from ESPN, the same public feed the app reads, so these are the facts the phone could show for these games today. '
            'Style follows the Kodi iOS tokens (black page, grouped cards, Inter, white capsule for the selected tab). Layout idea after the owner\'s example screenshots; no ESPN branding or artwork is copied, logos are ESPN\'s own runtime image addresses.</p>'
            '<div class="row">%s</div>'
            '<div class="legend"><b>Where each part comes from (ESPN summary feed).</b> Betting Odds: <b>pickcenter</b>. Team Stats: <b>boxscore.teams[].statistics</b>, bars in the teams\' own colours (lightened to read on black). Player tables: <b>boxscore.players</b>. '
            'Play-By-Play: <b>drives.previous</b> with each drive\'s plays. Standings: <b>standings.groups</b> (the playing teams highlighted). Basketball has the same boxscore, odds and plays; F1 has sessions and results from the scoreboard. '
            'A game that has not started shows only what exists (odds, venue, standings) and the other tabs say "Starts at ...". Nothing is added that ESPN does not give.</div></body></html>') % (CSS, ''.join(frames))
    with open(OUT, 'w', encoding='utf-8') as handle:
        handle.write(page)
    print('wrote', OUT, len(page))


if __name__ == '__main__':
    main()
