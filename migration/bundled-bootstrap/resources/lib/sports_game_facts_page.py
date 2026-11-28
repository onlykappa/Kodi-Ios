"""The game's Info / Standings page (owner mockups pages 8 and D1/D2): the two teams on their colours, the action capsule (Remind me, Reminder on or
Play, as on the game page), an Info | Standings switch, then the facts: kickoff and venue and each team's recent form, or the standings table
with a Divisional / Wild Card switch. There is no broadcaster row (the owner: the player is the place you watch). Draws IOSSportsGameFacts.xml;
sports_game_facts.py fills it (the game's properties plus sports_game_info's ESPN facts). A part ESPN has nothing for is not drawn; a game with
no table has no tabs."""
import status_ui as u
import sports_hero as hero

WINDOW = 'IOSSportsGameFacts.xml'
BACK, LIST = 9001, 9300
AUTO, REMIND, REMIND_ON = 9005, 9006, 9008
STANDINGS_SWITCH, STANDINGS_SWITCH_BACK = 9009, 9010      # Divisional / Wild Card
TAB_INFO, TAB_STANDINGS, TAB_PLAYS = 9012, 9013, 9014      # Stats (TAB_INFO's id), Standings, Play-By-Play
TAB_ALT = 20                                              # the two-tab row (a game with no standings) has its own ids: id + 20
BAR_BASE = 9100                                           # the team-stat bars (filled by the window's script: a progress control cannot read a property)
ST_ROWS = 8
STAT_ROWS, BLOCKS, BLOCK_ROWS, PLAYS = 10, 8, 5, 12      # sports_game_detail's slots
HEAD_H = 300                                              # the fixed header: score strip and tabs; the list scrolls under it
COLS = 5
DOTS = 5
PILL_W = 640
PILL_X = (1080 - PILL_W) // 2


def _gate(xml, cond):
    """Add `cond` to every top-level block of a tab (a list's blocks must each carry their own height, so a tab is not wrapped in a group)."""
    import re
    return re.sub(r'(<control type="group"><width>1080</width><height>\d+</height><visible>)(.*?)(</visible>)',
                  lambda m: '%s%s + %s%s' % (m.group(1), cond, m.group(2), m.group(3)), xml)


def _segment(p, halves, shown_prop):
    """Two halves in one rounded card, the shown one lifted (board D). halves: [(id, label, value of shown_prop while this half is shown)]."""
    seg = u.card(p, p.SIDE, 0, 972, 138)
    for (ident, label, value), x in zip(halves, (p.SIDE + 10, p.SIDE + 486)):
        seg += p.image(x, 10, 476, 118, p.MEDIA + 'r27.png', '33EBEBF5', '<visible>String.IsEqual(Window().Property(%s),%s)</visible>' % (shown_prop, value), border=27)
        seg += u.tap(p, ident, x, 10, 476, 118, label, p.WHITE)
    return u.group(p, 138, seg)


def _info_tab(p):
    """Board D1: when and where, then each team's recent form."""
    out = ''
    card_x, card_w = p.SIDE, 972
    # Starts / Started (and Venue, when ESPN has one) in one grouped card.
    for with_venue in (False, True):
        h = 290 if with_venue else 130
        body = u.card(p, card_x, 0, card_w, h)
        body += u.text(p, 92, 0, 300, 130, u.P('info.when'), 'p_foot_b')
        body += u.text(p, 400, 0, 588, 130, u.P('info.kickoff'), 'p_foot', p.GREY, 'right')
        if with_venue:
            body += p.image(92, 130, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
            body += u.text(p, 92, 133, 250, 157, 'Venue', 'p_foot_b')
            body += p.textbox(330, 148, 658, 51 * 2, u.P('info.venue'), 'p_foot', p.GREY).replace('<autoscroll>', '<align>right</align><autoscroll>')
            body += u.text(p, 330, 232, 658, 51, u.P('info.place'), 'p_foot', p.GREY, 'right')
        cond = u.has('info.kickoff') + (' + ' + u.has('info.venue') if with_venue else ' + String.IsEmpty(Window().Property(info.venue))')
        out += u.group(p, h + 40, body, cond)
    # Recent form: a grouped card, one row per team, five W / L / D dots.
    out += u.group(p, 118, u.text(p, p.SIDE + 10, 30, 700, 70, 'Recent form', 'p_h3'), u.has('form.0.name'))
    rows = ''
    for n in range(2):
        key = 'form.%d.' % n
        y = n * 190
        rows += p.textbox(92, y + 14, 500, 102, u.P(key + 'name'), 'p_foot_b')
        rows += u.text(p, 92, y + 116, 560, 54, u.P(key + 'line'), 'p_foot', p.GREY)
        for d in range(DOTS):
            x = 988 - (DOTS - d) * 68 + 12
            for letter, tint in (('W', p.GREEN), ('L', 'FFFF453A'), ('D', '66EBEBF5')):
                cond = 'String.IsEqual(Window().Property(%sd%d),%s)' % (key, d, letter)
                dot = p.image(x, y + 62, 56, 56, p.MEDIA + 'r27.png', tint, border=27)
                dot += u.text(p, x, y + 62, 56, 56, letter, 'p_foot_b', 'FF000000', 'center')
                rows += '<control type="group"><visible>%s</visible>%s</control>' % (cond, dot)
        if n == 0:
            rows += p.image(92, 190, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
    out += u.group(p, 420, u.card(p, card_x, 0, card_w, 380) + rows, u.has('form.0.name'))
    return out


def _standings_tab(p):
    """Board D2: the table (the game's two teams tinted, real crests) and the Divisional / Wild Card switch."""
    card_x, card_w = p.SIDE, 972
    out = ''
    out += u.group(p, 118, u.text(p, p.SIDE + 10, 30, 960, 70, u.P('st.title'), 'p_h3'), u.has('st.title'))
    head = p.image(card_x, 0, card_w, 100, p.MEDIA + 'row_first.png', p.SURFACE, border=43)
    cols = ((560, 90), (655, 90), (750, 90), (858, 130))
    for i, (x, w) in enumerate(cols):
        head += u.text(p, x, 0, w, 100, u.P('st.h%d' % i), 'p_foot', p.GREY, 'right')
    head += u.text(p, 92, 0, 120, 100, '#', 'p_foot', p.GREY) + u.text(p, 250, 0, 300, 100, 'Team', 'p_foot', p.GREY)
    out += u.group(p, 100, head, u.has('st.title'))
    for n in range(ST_ROWS):
        key = 'st.%d.' % n
        h = 134
        b = u.row_back(p, key, card_w, h)
        b += p.image(card_x + 14, 8, card_w - 28, h - 16, p.MEDIA + 'r21.png', '330A84FF', '<visible>' + u.has(key + 'me') + '</visible>', border=21)
        b += u.text(p, 92, 0, 80, h, u.P(key + 'rank'), 'p_foot', p.GREY)
        b += p.image(172, (h - 72) // 2, 72, 72, u.P(key + 'crest'), extra='<visible>' + u.has(key + 'crest') + '</visible>', aspect='>keep', background=True)
        b += u.text(p, 262, 0, 290, h, u.P(key + 'team'), 'p_foot')
        for i, (x, w) in enumerate(cols):
            b += u.text(p, x, 0, w, h, u.P(key + 'c%d' % i), 'p_foot', align='right')
        out += u.group(p, h, b, u.has(key + 'team'))
    out += u.group(p, 40, '', u.has('st.switch'))
    out += u.group(p, 180, _segment(p, [(STANDINGS_SWITCH_BACK, 'Divisional', 'wild'), (STANDINGS_SWITCH, 'Wild Card', 'div')], 'st.switch'), u.has('st.switch'))
    return out



def _header(p):
    """Fixed at the top while the list scrolls (the owner's example: the score and the tabs stay): back, the compact score, the three tabs."""
    out = p.image(0, 0, 1080, HEAD_H, p.MEDIA + 'white.png', 'FF000000')
    out += p.nav_button(BACK, 32, 5, 'chevron-left.png', 'noop')
    team = 'String.IsEqual(Window().Property(strip.kind),teams)'
    event = 'String.IsEqual(Window().Property(strip.kind),event)'
    strip = ''
    for side, x, sx, align in (('away', 170, 280, 'left'), ('home', 814, 640, 'right')):
        strip += p.image(x, 22, 96, 96, u.P(side + '.crest'), extra='<visible>' + u.has(side + '.crest') + '</visible>', aspect='>keep', background=True)
        strip += u.text(p, x, 22, 96, 96, u.P(side + '.code'), 'p_foot_b', align='center').replace('</control>', '<visible>' + u.neg(u.has(side + '.crest')) + '</visible></control>')
        strip += u.text(p, sx, 12, 160, 116, u.P('strip.' + side), 'p_title', 'FFFFFFFF' if side == 'home' else p.GREY, align)
    strip += u.text(p, 440, 24, 200, 54, u.P('strip.status'), 'p_foot_b', p.WHITE, 'center').replace('<textcolor>' + p.WHITE + '</textcolor>', '<textcolor>' + u.P('strip.tint') + '</textcolor>')
    strip += u.text(p, 440, 76, 200, 46, u.P('strip.sub'), 'p_cap', p.GREY, 'center')
    out += '<control type="group"><visible>%s</visible>%s</control>' % (team, strip)
    ev = p.image(170, 22, 96, 96, u.P('away.crest'), extra='<visible>' + u.has('away.crest') + '</visible>', aspect='>keep', background=True)
    ev += p.textbox(290, 14, 760, 112, u.P('away.name'), 'p_foot_b').replace('<autoscroll>', '<aligny>center</aligny><autoscroll>')
    out += '<control type="group"><visible>%s</visible>%s</control>' % (event, ev)
    def row(items, bump=0):
        width = 972 // len(items)
        seg = u.card(p, p.SIDE, 0, 972, 104)
        for k, (ident, label, value) in enumerate(items):
            x = p.SIDE + 6 + k * width
            w = width - 12
            seg += p.image(x, 6, w, 92, p.MEDIA + 'r27.png', p.WHITE, '<visible>String.IsEqual(Window().Property(tab),%s)</visible>' % value, border=27)
            seg += u.tap(p, ident + bump, x, 6, w, 92, '', p.GREY)
            seg += '<control type="group"><visible>String.IsEqual(Window().Property(tab),%s)</visible>%s</control>' % (value, u.text(p, x, 6, w, 92, label, 'p_foot_b', 'FF000000', 'center'))
            seg += '<control type="group"><visible>!String.IsEqual(Window().Property(tab),%s)</visible>%s</control>' % (value, u.text(p, x, 6, w, 92, label, 'p_foot_b', p.GREY, 'center'))
        return seg
    three = ((TAB_INFO, 'Stats', 'stats'), (TAB_PLAYS, 'Play-By-Play', 'plays'), (TAB_STANDINGS, 'Standings', 'standings'))
    out += '<control type="group"><top>164</top><visible>%s</visible>%s</control>' % (u.has('has.tabs'), row(three))
    out += '<control type="group"><top>164</top><visible>%s</visible>%s</control>' % (u.neg(u.has('has.tabs')), row(three[:2], TAB_ALT))
    return out


def _message(p):
    """While ESPN's answer is on its way, or has nothing: one plain line (the cards below draw only what exists)."""
    out = u.group(p, 150, u.text(p, p.SIDE, 40, 972, 70, 'Loading the stats…', 'p_foot', p.GREY, 'center'), 'String.IsEqual(Window().Property(detail),loading)')
    out += u.group(p, 150, u.text(p, p.SIDE, 40, 972, 70, 'ESPN has no stats for this game yet.', 'p_foot', p.GREY, 'center'), 'String.IsEqual(Window().Property(detail),none)')
    return out


def _odds(p):
    h = 520
    body = u.card(p, p.SIDE, 0, 972, h - 20)
    body += u.text(p, p.SIDE, 18, 972, 70, 'Betting Odds', 'p_h3', p.WHITE, 'center')
    for x, w, label in ((92, 150, 'Team'), (250, 250, 'Spread'), (500, 250, 'Total'), (750, 240, 'Moneyline')):
        body += u.text(p, x, 96, w, 56, label, 'p_cap', p.GREY, 'left' if label == 'Team' else 'center')
    for n in range(2):
        key, y = 'odds.r%d.' % n, 160 + n * 130
        if n:
            body += p.image(92, y - 4, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
        body += u.text(p, 92, y, 150, 120, u.P(key + 'team'), 'p_foot_b')
        body += u.text(p, 250, y + 6, 250, 60, u.P(key + 'spread'), 'p_foot_b', p.WHITE, 'center') + u.text(p, 250, y + 62, 250, 44, u.P(key + 'so'), 'p_cap', p.GREY, 'center')
        body += u.text(p, 500, y + 6, 250, 60, u.P(key + 'total'), 'p_foot_b', p.WHITE, 'center') + u.text(p, 500, y + 62, 250, 44, u.P(key + 'to'), 'p_cap', p.GREY, 'center')
        body += u.text(p, 750, y, 240, 120, u.P(key + 'money'), 'p_foot_b', p.WHITE, 'center')
    body += u.text(p, 92, 420, 896, 50, 'Odds provided by ' + u.P('odds.provider'), 'p_cap', p.GREY)
    return u.group(p, h, body, u.has('odds.r0.team'))


def _team_stats(p):
    out = u.group(p, 118, u.text(p, p.SIDE + 10, 30, 960, 70, 'Team Stats', 'p_foot_b', p.GREY), u.has('ts.0.label'))
    for n in range(STAT_ROWS):
        key, h = 'ts.%d.' % n, 150
        b = u.row_back(p, key, 972, h)
        b += u.text(p, 92, 10, 260, 70, u.P(key + 'away'), 'p_h3') + u.text(p, 728, 10, 260, 70, u.P(key + 'home'), 'p_h3', p.WHITE, 'right')
        b += u.text(p, 330, 14, 420, 60, u.P(key + 'label'), 'p_cap', p.GREY, 'center')
        b += u.id_bar(p, BAR_BASE + n, 92, 96, 896, 11, u.P(key + 'ac'), u.P(key + 'hc'))
        out += u.group(p, h, b, u.has(key + 'label'))
    return out


def _blocks(p):
    out = ''
    cols = [(423 + 113 * i, 113) for i in range(COLS)]
    for n in range(BLOCKS):
        key = 'blk.%d.' % n
        head = p.image(p.SIDE + 10, 40, 60, 60, u.P(key + 'logo'), extra='<visible>' + u.has(key + 'logo') + '</visible>', aspect='>keep', background=True)
        head += u.text(p, p.SIDE + 84, 30, 800, 80, u.P(key + 'team'), 'p_foot_b')
        out += u.group(p, 118, head, u.has(key + 'team'))
        for rows in (3, 5):   # the window pads a block to 3 or 5 rows
            h = 100 + 90 * rows + 30
            b = u.card(p, p.SIDE, 0, 972, h - 20)
            b += u.text(p, 92, 6, 330, 90, u.P(key + 'title'), 'p_cap', p.GREY)
            for i, (x, w) in enumerate(cols):
                b += u.text(p, x, 6, w, 90, u.P(key + 'h%d' % i), 'p_cap', p.GREY, 'right')
            for r in range(rows):
                y = 100 + 90 * r
                if r:
                    b += p.image(92, y, 896, 2, p.MEDIA + 'white.png', '14EBEBF5')
                b += p.textbox(92, y + 4, 330, 84, u.P(key + 'r%d.name' % r), 'p_foot_b').replace('<autoscroll>', '<aligny>center</aligny><autoscroll>')
                for i, (x, w) in enumerate(cols):
                    b += u.text(p, x, y, w, 90, u.P(key + 'r%d.c%d' % (r, i)), 'p_foot', p.WHITE, 'right')
            out += u.group(p, h, b, 'String.IsEqual(Window().Property(%srows),%d)' % (key, rows))
    return out


def _stats_tab(p):
    return _message(p) + u.group(p, 40, '') + _info_tab(p) + _odds(p) + _team_stats(p) + u.group(p, 30, '') + _blocks(p)


def _plays_tab(p):
    """One card per drive (football) or play: a colour stripe, what happened, the plain description (wraps up to three lines), a SCORE mark."""
    out = _message(p).replace('Loading the stats…', 'Loading the plays…').replace('no stats for this game yet', 'no plays for this game yet')
    for n in range(PLAYS):
        key = 'play.%d.' % n
        for lines in (1, 2, 3):   # the window gives a play 1, 2 or 3 lines
            h = 40 + 62 + 51 * lines + 36
            b = u.card(p, p.SIDE, 0, 972, h - 16)
            b += p.image(p.SIDE + 14, 22, 8, h - 60, p.MEDIA + 'white.png', u.P(key + 'color'), '<visible>' + u.has(key + 'color') + '</visible>')
            b += u.text(p, 92 + 14, 18, 600, 62, u.P(key + 'title'), 'p_foot_b')
            b += p.image(838, 24, 150, 52, p.MEDIA + 'r27.png', '3330D158', '<visible>String.IsEqual(Window().Property(%sscore),true)</visible>' % key, border=26)
            b += u.text(p, 838, 24, 150, 52, 'SCORE', 'p_cap', p.GREEN, 'center').replace('</control>', '<visible>String.IsEqual(Window().Property(%sscore),true)</visible></control>' % key)
            for x, w, vis in ((520, 300, 'String.IsEqual(Window().Property(%sscore),true)'), (620, 360, '!String.IsEqual(Window().Property(%sscore),true)')):   # beside the SCORE mark, not under it
                b += u.text(p, x, 18, w, 62, u.P(key + 'tag'), 'p_cap', p.GREY, 'right').replace('</control>', '<visible>' + vis % key + '</visible></control>')
            b += p.textbox(92 + 14, 80, 860, 51 * lines + 6, u.P(key + 'detail'), 'p_foot', p.GREY)
            out += u.group(p, h, b, 'String.IsEqual(Window().Property(%sform),%d)' % (key, lines))
    return out



def _actions(p):
    """The same capsule as the game page: Play when there is a source, else Remind me / Reminder on (before the game starts)."""
    no_source = 'String.IsEqual(Window().Property(state),empty) + String.IsEmpty(Window().Property(game.live))'
    out = u.group(p, 182, p.pill_button(AUTO, PILL_X, 27, PILL_W, 128, 'Play', [('', 'noop')], 'primary', 'play.png', inline=True), u.has('sources.count'))
    out += u.group(p, 182, p.pill_button(REMIND, PILL_X, 27, PILL_W, 128, 'Remind me', [('', 'noop')], 'primary', 'bell.png', inline=True),
                   no_source + ' + String.IsEmpty(Window().Property(remind.on))')
    out += u.group(p, 182, p.pill_button(REMIND_ON, PILL_X, 27, PILL_W, 128, 'Reminder on', [('', 'noop')], 'glass', 'check.png', inline=True),
                   no_source + ' + !String.IsEmpty(Window().Property(remind.on))')
    return out


def page(p):
    """The Info window: a fixed header (score and the Stats / Play-By-Play / Standings tabs) over a list that scrolls."""
    stats, plays, table = 'String.IsEqual(Window().Property(tab),stats)', 'String.IsEqual(Window().Property(tab),plays)', 'String.IsEqual(Window().Property(tab),standings)'
    content = _gate(_stats_tab(p), stats)
    content += _gate(_plays_tab(p), plays)
    content += _gate(u.group(p, 30, '') + _standings_tab(p), table)
    content += u.group(p, 260, '')
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>%d</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s</control>') % (LIST, HEAD_H, content)
    body += _header(p)
    body += p.tabbar('library')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>' % body


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
