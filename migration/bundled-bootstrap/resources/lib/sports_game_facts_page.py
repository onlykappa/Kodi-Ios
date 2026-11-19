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
TAB_INFO, TAB_STANDINGS = 9012, 9013
ST_ROWS = 8
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
    # Kickoff (and Venue, when ESPN has one) in one grouped card.
    for with_venue in (False, True):
        h = 290 if with_venue else 130
        body = u.card(p, card_x, 0, card_w, h)
        body += u.text(p, 92, 0, 300, 130, 'Kickoff', 'p_foot_b')
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
    header = p.nav_button(BACK, 32, 5, 'chevron-left.png', 'noop')
    content = u.group(p, 134, header) + hero.hero(p) + _actions(p)
    tabs = u.group(p, 40, '', u.has('has.tabs')) + u.group(p, 160, _segment(p, [(TAB_INFO, 'Info', 'info'), (TAB_STANDINGS, 'Standings', 'standings')], 'tab'), u.has('has.tabs'))
    content += tabs
    info_on, standings_on = '!String.IsEqual(Window().Property(tab),standings)', 'String.IsEqual(Window().Property(tab),standings)'
    content += _gate(u.group(p, 40, '') + _info_tab(p), info_on)
    content += _gate(_standings_tab(p), standings_on)
    content += u.group(p, 260, '')
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s</control>') % (LIST, content)
    body += p.tabbar('library')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>' % body


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
