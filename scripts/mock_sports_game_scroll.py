#!/usr/bin/env python3
"""Mockup generator: ONE game page, scrolled. The hero and Play and Sources as in the sources mockup, then the Info section (tabs pinned under a compact score strip, as the owner's example
screenshots do) with Stats from LIVE ESPN data; the same page is shown at several scroll positions in a phone-sized window (402 x 778 pt). Evidence class: MOCKUP (browser, not Kodi).
usage: python3 -B scripts/mock_sports_game_scroll.py [OUT.html]   (written outside the repository by default; it holds live data and is never committed)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_sports_game_info as m

OUT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.html') else '/tmp/claude-0/mock-scroll.html'
POSITIONS = (0, 560, 1180, 1900, 2700)


def build():
    board = m.get('basketball/nba/scoreboard')
    chosen = next((e for e in board['events'] if e['status']['type']['state'] == 'in'), None) or next(e for e in board['events'] if e['status']['type']['state'] == 'post')
    summary = m.get('basketball/nba/summary?event=%s' % chosen['id'])
    comp = summary['header']['competitions'][0]
    ev = {'competitions': [comp]}
    away = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
    home = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
    live = comp['status']['type']['state'] == 'in'

    def glow(c):
        return m.lighten(c['team'].get('color'), .3)

    def side(c):
        t = c['team']
        record = (c.get('record') or [{}])[0].get('displayValue', '') if isinstance(c.get('record'), list) else ''
        return '<div class="hteam"><img src="%s"><b>%s</b><span>%s</span></div>' % (m.esc(m.team_logo(t)), m.esc(t.get('name') or t.get('displayName')), m.esc(record))
    hero = ('<div class="hero" style="background:radial-gradient(circle at 12%% 40%%,%s88,transparent 55%%),radial-gradient(circle at 88%% 40%%,%s88,transparent 55%%)">'
            '<div class="lg">%s</div>%s<div class="hmid">%s<div class="hsc">%s – %s</div><small>%s</small></div>%s</div>') % (
        glow(away), glow(home), m.esc('NBA'), side(away), '<span class="live">● LIVE</span>' if live else 'Final', m.esc(away.get('score')), m.esc(home.get('score')),
        m.esc(comp['status']['type'].get('shortDetail', '')), side(home))
    play = '<div class="play">▶ Play</div><div class="auto">Plays <b>720pStream</b> first<br>Best on this phone: 1080p · 4.8 Mbps · worked 5 of 5</div>'
    sources = ('<div class="head"><h2>Sources</h2><span class="gl">Checked 2 min ago</span></div><div class="group">'
               '<div class="src"><div class="tile">72</div><div class="md"><div class="name">720pStream <span class="tag">Best</span></div><div class="chips"><span class="chip qq">1080p</span><span class="chip">30 fps</span><span class="chip">4.8 Mbps</span></div><div class="meta"><span class="dot g"></span>Worked 5 of 5 · 2 h ago</div></div><div class="go"></div></div>'
               '<div class="src"><div class="tile">CM</div><div class="md"><div class="name">Crew MUT</div><div class="chips"><span class="chip">720p</span><span class="chip">30 fps</span><span class="chip">2.4 Mbps</span></div><div class="meta"><span class="dot g"></span>Worked 3 of 4 · yesterday</div></div><div class="go"></div></div>'
               '<div class="src"><div class="tile">LF</div><div class="md"><div class="name">LiveFeeds</div><div class="chips"><span class="chip">480p</span><span class="chip">25 fps</span><span class="chip">0.9 Mbps</span></div><div class="meta"><span class="dot o"></span>Worked 1 of 3 · stalled twice</div></div><div class="go"></div></div>'
               '<div class="more"><span>Other sources (3)</span><span>›</span></div></div>')
    tabs = ('Stats', 'Play-By-Play', 'Standings')
    sticky = m.header_strip(ev, 'Stats', tabs).replace('class="strip"', 'class="strip compact"')
    rows = [('fieldGoalPct', 'Field Goal %'), ('threePointFieldGoalPct', 'Three Point %'), ('freeThrowPct', 'Free Throw %'), ('totalRebounds', 'Rebounds'), ('assists', 'Assists'), ('turnovers', 'Turnovers'), ('steals', 'Steals'), ('blocks', 'Blocks')]
    body = m.odds_card(summary) + m.team_stats_card(summary, rows)
    for block in summary['boxscore']['players']:
        group = block['statistics'][0]
        people = sorted([p for p in group['athletes'] if len(p.get('stats') or []) >= len(group['labels'])], key=lambda p: -(m.number(p['stats'][group['labels'].index('PTS')]) or 0))[:6]
        cols = [group['labels'].index(l) for l in ('MIN', 'PTS', 'REB', 'AST') if l in group['labels']]
        t = '<tr><th>Player</th>%s</tr>' % ''.join('<th>%s</th>' % m.esc(group['labels'][i]) for i in cols)
        for p in people:
            a = p['athlete']
            t += '<tr><td>%s <i>%s</i></td>%s</tr>' % (m.esc(a.get('shortName')), m.esc((a.get('position') or {}).get('abbreviation', '')), ''.join('<td>%s</td>' % m.esc(p['stats'][i]) for i in cols))
        body += '<div class="card"><div class="ct"><img src="%s">%s</div><table>%s</table></div>' % (m.esc(m.team_logo(block['team'])), m.esc(block['team'].get('shortDisplayName')), t)
    page_inner = hero + play + sources + '<div class="head"><h2>Game info</h2></div><div class="pin">' + sticky + '</div>' + body + '<div class="end">Standings and Play-By-Play are the other two tabs</div>'
    return page_inner, comp


CSS = m.CSS + '''
.vps{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}.vpw{width:402px}.vp{width:402px;height:778px;overflow:hidden;background:#000;border-radius:30px;border:1px solid #333;position:relative}
.vp .scroll{height:100%;overflow-y:auto;padding:0 14px 40px;scrollbar-width:none}.vp .scroll::-webkit-scrollbar{display:none}
.hero{margin:0 -14px 0;padding:54px 14px 22px;display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;position:relative}.hero .lg{width:100%;text-align:center;color:var(--grey);font-weight:700;font-size:14px;margin-bottom:6px}
.hteam{width:118px;text-align:center}.hteam img{width:84px;height:84px;object-fit:contain}.hteam b{display:block;font-size:19px;margin-top:6px}.hteam span{color:var(--grey);font-size:14px}
.hmid{flex:1;text-align:center;padding-top:6px}.hmid .live{color:var(--red);font-weight:700;font-size:14px}.hsc{font-size:34px;font-weight:700;margin:4px 0}.hmid small{color:var(--grey);font-size:14px}
.play{height:60px;border-radius:30px;background:#fff;color:#000;font-weight:700;font-size:17px;display:flex;align-items:center;justify-content:center;margin:4px 0 8px}.auto{text-align:center;color:var(--grey);font-size:13px;line-height:1.35;margin-bottom:22px}.auto b{color:#fff}
.head{display:flex;justify-content:space-between;align-items:baseline;margin:6px 0 4px}.head h2{font-size:22px;margin:0}.gl{color:var(--grey);font-size:15px}
.group{background:var(--s1);border-radius:13px;overflow:hidden;margin-bottom:16px}.src{display:flex;gap:12px;align-items:center;padding:12px;border-bottom:1px solid var(--sep)}.tile{width:44px;height:44px;border-radius:10px;background:var(--s2);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex:none}.md{flex:1;min-width:0}
.name{font-size:17px;font-weight:600;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.tag{font-size:12px;font-weight:700;color:var(--bluet);background:rgba(10,132,255,.2);border-radius:9px;padding:2px 8px}.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:5px}.chip{font-size:12px;font-weight:600;background:var(--s2);border-radius:7px;padding:2px 7px}.chip.qq{background:rgba(48,209,88,.18);color:var(--green)}
.meta{font-size:13px;color:var(--grey);margin-top:4px;display:flex;align-items:center;gap:6px}.dot{width:8px;height:8px;border-radius:50%;display:inline-block}.g{background:var(--green)}.o{background:#FF9F0A}.go{width:44px;height:44px;border-radius:50%;background:#fff;flex:none;display:flex;align-items:center;justify-content:center}.go:after{content:"";border-left:14px solid #000;border-top:9px solid transparent;border-bottom:9px solid transparent;margin-left:4px}
.more{display:flex;justify-content:space-between;padding:14px 12px;color:var(--bluet);font-size:15px;font-weight:500}
.pin{position:sticky;top:0;z-index:5;background:linear-gradient(#000 92%,transparent);margin:0 -14px;padding:2px 14px 2px}.strip.compact{padding:2px 4px 4px}.pin .tabs{margin-bottom:10px}
.pin .strip{display:none}.pin.stuck .strip{display:flex}.end{text-align:center;color:var(--grey);font-size:13px;padding:14px 0}.sc2{display:none}
.cap2{font-size:12.5px;color:var(--grey);text-align:center;margin-top:8px}
'''


def main():
    inner, comp = build()
    cells = ''.join('<div class="vpw"><div class="vp"><div class="scroll" data-y="%d">%s</div></div><p class="cap2">scrolled %d pt</p></div>' % (y, inner, y) for y in POSITIONS)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Game page scrolled (mockup, live ESPN data)</title><style>%s</style></head><body>'
            '<h1>One game page, scrolled <span class="badge">MOCKUP</span></h1>'
            '<p class="note">Mockup in a browser (not the app, not Kodi). The same page in a phone-sized window (402 x 778 pt) at five scroll positions, live ESPN data. Top: hero, Play, Sources (checked by themselves). '
            'Scrolling on: Game info with the tabs only (the score is already above). Once the tabs reach the top of the screen the compact score appears above them and both stay pinned while the stats scroll under.</p>'
            '<div class="vps">%s</div>'
            '<script>document.querySelectorAll(".scroll").forEach(function(e){var pin=e.querySelector(".pin");function f(){pin.classList.toggle("stuck",pin.getBoundingClientRect().top<=e.getBoundingClientRect().top+3)}e.addEventListener("scroll",f);e.scrollTop=parseInt(e.dataset.y);f()})</script></body></html>') % (CSS, cells)
    with open(OUT, 'w', encoding='utf-8') as handle:
        handle.write(page)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
