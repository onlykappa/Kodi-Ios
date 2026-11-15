"""Build 193 Library status and movie sheets, approved boards 1–3 and 9."""
WINDOW = 'IOSLibraryStatus.xml'
ITEM = 'IOSLibraryItem.xml'
FILTERS = (('ready', 'Ready'), ('working', 'Working'), ('waiting', 'Up next'), ('kept', 'Kept'))   # buttons 9101-9104
LIST, BACK, CHECK = 9300, 9001, 9002
EDIT = 9003   # Waiting › Edit order (the Queue)
VIEW_QUEUE = 9006   # One current download, before there are any Up next rows
HIT = 118
PURPLE = 'FFBF5AF2'
BLUE = 'FF0A84FF'


SLOTS, SLOT, WORK, NEED, MORE, PREVIOUS = 40, 9400, 9005, 9004, 9050, 9051
# Build 194: one pool of rows per section, each drawn as in the approved mockups (boards 1 and 2):
# (key, first control id, rows, row height). The page's script fills them; no Previous/More paging.
POOLS = (('down', 9310, 6, 231), ('next', 9400, 40, 161), ('kept', 9450, 15, 161))   # DEC-047: no Ready list
SEGMENTS = 9811        # summary bar: ready, working, up next, kept (widths set by the script)
DOWN_BARS = 9330       # the AllDebrid copy bars, one per 'down' row
WORK_BAR = 9350        # the 'Working on now' bar (running card, then the still card), DEC-036
LANE, LANE_BARS, LANES = 9360, 9370, 2   # DEC-044 board D: one row per extra preparation lane (F2), under the card
BAR_X, BAR_W, BAR_Y, BAR_H, BAR_GAP = 38, 896, 118, 21, 8     # inside the summary card (units)
LIST_TOP = 362


def pool_slot(key, n):
    return dict((k, base) for k, base, _, _ in POOLS)[key] + n


def _header(p, u, title, cond, action=''):
    """A section title (15 pt semibold, GREY) with an optional link on the same line (Edit order)."""
    S = p.SIDE
    return u.group(p, 105, u.text(p, S + 10, 16, p.WIDTH - 2 * S - (340 if action else 20), 51, title, 'p_pill', p.GREY) + action, cond)


def _work(p, u):
    """Board 1/2 'Working on now' card: poster, eyebrow, title, step, percentage and bar; then the sparkline and speed (running), or the
    model's line (slowed, paused, waiting)."""
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    running = 'String.IsEqual(Window().Property(work.state),running)'

    def body(h, moving):
        b = u.card(p, S, 0, w, h) + u.tap(p, WORK if moving else WORK + 100, S, 0, w, h)
        b += p.image(S + 38, 38, 140, 210, M + 'white.png', u.SURF2, diffuse=M + 'poster21.png')
        b += p.image(S + 38, 38, 140, 210, P('work.poster'), p.WHITE, '', '>scale', M + 'poster21.png', background=True)
        b += u.text(p, S + 210, 62, w - 440, 43, P('work.eyebrow'), 'p_foot_b', u.PURPLE)   # 'WORKING ON NOW · 3' with lanes
        b += u.text(p, S + 210, 113, w - 248, 54, P('work.title'), 'p_h3')
        b += u.text(p, S + 210, 175, w - 248, 51, P('work.step'), 'p_sub', p.GREY)
        # DEC-036: a thin bar under the step, the percentage at the top right (the only ring is the Home bell's).
        b += u.text(p, S + w - 228, 62, 190, 43, P('work.percent'), 'p_foot_b', p.WHITE, 'right')
        b += ('<control type="group"><visible>%s</visible>' % u.has('work.percent') +
              u.id_bar(p, WORK_BAR + (0 if moving else 1), S + 210, 238, w - 248, 12, P('work.tint'), texture='pill16.png', border=6) +
              '</control>')
        if moving:
            # Owner screenshot (build 327): a flat purple line under a conversion at 0 % with no speed yet; the graph shows
            # only beside a speed.
            b += p.image(S + 38, 279, 438, 81, P('work.graph'), p.WHITE, '<visible>%s</visible>' % u.has('work.speed'), '>stretch')
            b += ('<control type="grouplist"><left>%d</left><top>287</top><width>%d</width><height>51</height><orientation>horizontal</orientation>'
                  '<itemgap>12</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>' % (S + 502, w - 560, u.has('work.speed')) +
                  '<control type="label"><width>auto</width><scroll>false</scroll><height>51</height><font>p_pill</font><textcolor>%s</textcolor><label>%s</label></control>' % (p.WHITE, P('work.speed')) +
                  '<control type="label"><width>auto</width><scroll>false</scroll><height>51</height><font>p_sub</font><textcolor>%s</textcolor><label>%s</label></control>' % (p.GREY, P('work.left')) +
                  '</control>')
            b += u.glyph(p, S + w - 62, 294, 38, 'chevron-right.png', p.GREY)
        else:
            b += u.text(p, S + 38, 279, w - 120, 43, P('work.line'), 'p_foot', p.GREY)
            b += u.glyph(p, S + w - 62, 282, 38, 'chevron-right.png', p.GREY)
        return b
    return (u.group(p, 398 + u.GAP, body(398, True), u.has('work.title') + ' + ' + running) +
            u.group(p, 360 + u.GAP, body(360, False), u.has('work.title') + ' + ' + u.neg(running)))


def _lanes(p, u):
    """DEC-044 board D: each extra preparation lane as its own row (the copy rows' card), with its bar and percentage."""
    S, w, P = p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    out = ''
    for n in range(LANES):
        k = 'lane.%d.' % n
        b = u.card(p, S, 0, w, 231) + u.tap(p, LANE + n, S, 0, w, 231)
        b += u.text(p, S + 38, 38, w - 230, 54, P(k + 'title'), 'p_body')
        b += u.text(p, S + w - 188, 41, 150, 51, P(k + 'pct'), 'p_pill', u.PURPLE, 'right')
        b += u.id_bar(p, LANE_BARS + n, S + 38, 113, w - 76, 16, P(k + 'tint'), texture='pill16.png', border=8)
        b += u.text(p, S + 38, 150, w - 76, 43, P(k + 'sub'), 'p_foot', p.GREY)
        out += u.group(p, 231 + 21, b, u.has(k + 'title'))
    return out


def _needs(p, u):
    """Board 2: the needs-you card (orange tile, sentence, white Sign in capsule)."""
    S, w, P = p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    b = u.card(p, S, 0, w, 451)
    b += p.image(S + 38, 38, 97, 97, p.MEDIA + 'r27.png', '2EFF9F0A', border=27)
    b += u.glyph(p, S + 57, 57, 59, 'triangle-exclamation.png', u.ORANGE)
    b += u.text(p, S + 167, 38, w - 205, 54, P('need.title'), 'p_h3')
    b += u.paragraph(p, S + 167, 99, w - 205, 164, P('need.text'))
    b += p.pill_button(NEED, S + 38, 296, w - 76, 124, P('need.button'), [('', 'noop')], 'primary', extra=u.NOS)
    return u.group(p, 451 + u.GAP, b, u.has('need.title'))


def _summary(p, u):
    """Board 1: 'N of M ready' + time to go, ONE segmented bar (script sizes it), four count buttons."""
    S, w, P = p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    b = u.card(p, S, 0, w, 355)
    b += u.text(p, S + 38, 38, 420, 54, P('headline'), 'p_h3')   # board 1: '8 of 12 ready' left, the time to go right
    b += u.text(p, S + 478, 41, w - 516, 51, P('remaining'), 'p_sub', p.GREY, 'right')
    b += p.image(S + BAR_X, BAR_Y, BAR_W, BAR_H, p.MEDIA + 'pill21.png', u.TRACK, border=10)
    for i, tint in enumerate((p.GREEN, u.PURPLE, u.BLUE, u.SEG_GREY)):
        b += ('<control type="image" id="%d"><left>%d</left><top>%d</top><width>0</width><height>%d</height>'
              '<texture border="10" colordiffuse="%s">%spill21.png</texture></control>') % (SEGMENTS + i, S + BAR_X, BAR_Y, BAR_H, tint, p.MEDIA)
    cw = (BAR_W - 3 * 16) // 4
    for i, (key, title, tint) in enumerate((('ready', 'Ready', p.GREEN), ('working', 'Working', u.PURPLE),
                                             ('next', 'Up next', p.ACCENT), ('kept', 'Kept', p.GREY))):
        x = S + 38 + i * (cw + 16)
        b += p.image(x, 167, cw, 150, p.MEDIA + 'r27.png', u.SURF2, border=27)
        if key != 'ready':   # DEC-047: the ready count is a number only; its list lives in Library › Movies / TV Shows
            b += u.tap(p, 9101 + i, x, 167, cw, 150)
        b += u.text(p, x, 183, cw, 64, P('count.' + key), 'p_h2', tint, 'center')
        b += u.text(p, x, 252, cw, 44, title, 'p_cap', p.GREY, 'center')
    return u.group(p, 355 + u.GAP, b, u.has('headline'))


def _pool(p, u, key, base, slots, h):
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    out = ''
    for n in range(slots):
        k = '%s.%d.' % (key, n)
        if key == 'down':      # its own card per copy (board 2)
            b = u.card(p, S, 0, w, 231) + u.tap(p, base + n, S, 0, w, 231)
            b += u.text(p, S + 38, 38, w - 230, 54, P(k + 'title'), 'p_body')
            b += u.text(p, S + w - 188, 41, 150, 51, P(k + 'pct'), 'p_pill', p.ACCENT, 'right')
            b += u.id_bar(p, DOWN_BARS + n, S + 38, 113, w - 76, 16, u.BLUE, texture='pill16.png', border=8)
            b += u.text(p, S + 38, 150, w - 76, 43, P(k + 'sub'), 'p_foot', p.GREY)
            out += u.group(p, 231 + 21, b, u.has(k + 'title'))
            continue
        b = u.row_back(p, k, w, h) + u.tap(p, base + n, S, 0, w, h)
        fade = '<animation effect="fade" start="100" end="45" time="0" condition="%s">Conditional</animation>' % u.has(k + 'off')
        if key == 'next':
            b += p.image(S + 38, 40, 81, 81, M + 'avatar_s.png', '2E0A84FF')
            b += u.text(p, S + 38, 40, 81, 81, P(k + 'number'), 'p_foot_b', p.ACCENT, 'center')
            b += u.text(p, S + 150, 32, w - 188, 54, P(k + 'title'), 'p_body')
            b += u.text(p, S + 150, 89, w - 188, 43, P(k + 'sub'), 'p_foot', p.GREY)
        elif key == 'kept':
            b += u.text(p, S + 38, 32, w - 76, 54, P(k + 'title'), 'p_body')
            b += u.text(p, S + 38, 89, w - 76, 43, P(k + 'sub'), 'p_foot', p.GREY)
        else:   # ready
            b += u.glyph(p, S + 38, 40, 59, 'circle-check.png', p.GREEN)
            b += u.text(p, S + 129, 0, w - 129 - 300, h, P(k + 'title'), 'p_body')
            b += u.text(p, S + w - 300, 0, 262, h, P(k + 'sub'), 'p_foot', p.GREY, 'right')
        out += u.group(p, h, '<control type="group">%s%s</control>' % (fade, b), u.has(k + 'title'))
    return out


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    titles = {'down': 'DOWNLOADING TO GOOGLE DRIVE', 'next': 'UP NEXT', 'kept': 'KEPT AS IT IS', 'ready': 'READY FOR KODI AND AIRPLAY'}
    pools = {}
    for key, base, slots, h in POOLS:
        action = u.link(p, EDIT, W - S - 300, -18, 290, 118, P('queue.label')) if key == 'next' else ''
        if key == 'down':
            action=('<control type="group"><visible>%s</visible>%s</control>' % (
                u.neg(u.has('next.0.title')),u.link(p,VIEW_QUEUE,W-S-300,-18,290,118,'View queue')))
        heading=_header(p,u,titles[key],u.has('%s.0.title'%key),action)
        if key=='down':
            heading=(_header(p,u,'DOWNLOADS',u.has('down.0.title')+' + '+u.neg(u.has('next.0.title')),action)+
                     _header(p,u,titles[key],u.has('down.0.title')+' + '+u.has('next.0.title')))
        pools[key] = (heading + _pool(p, u, key, base, slots, h) +
                      u.group(p, u.GAP, '', u.has('%s.0.title' % key)))
    listing = ('<control type="grouplist" id="9300"><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST_TOP, W) +
               _needs(p, u) + _work(p, u) + _lanes(p, u) + pools['down'] + _summary(p, u) + pools['next'] + pools['kept'] +
               u.group(p, 150, u.text(p, S, 30, w, 60, P('empty'), 'p_foot', p.GREY), u.has('empty')) +
               u.group(p, 200, '') + '</control>')
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('String.IsEqual(Window().Property(filter),all)', 'Close')])
    # Refresh: the 22 pt blue glyph of the mockup (ACCENT), in a 118-unit touch area.
    body += ('<control type="button" id="%d"><left>%d</left><top>41</top><width>118</width><height>118</height><label></label>'
             '<texturefocus /><texturenofocus /><onclick>noop</onclick></control>' % (CHECK, W - S - 118))
    body += u.glyph(p, W - S - 85, 74, 52, 'arrow-rotate-right.png', p.ACCENT,
                   '<animation effect="fade" start="100" end="65" time="0" condition="Control.HasFocus(%d)">Conditional</animation>' % CHECK)
    body += u.text(p, S, 160, w, 110, P('title'), 'p_large') + u.text(p, S, 268, w, 56, P('sub'), 'p_sub', p.GREY) + listing
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 194: approved boards 1 and 2 -->\n<window><defaultcontrol always="true">9001</defaultcontrol><controls>' + body + '</controls></window>'


CARD_FACTS = 5      # rows under the speed card (library_rows.FACTS)
TONES = (('ok', 'FF30D158'), ('warn', 'FFFF9F0A'), ('plain', None), ('conv', 'FFBF5AF2'), ('down', 'FF0A84FF'))
STEP_BARS = 9301       # the three step bars (Downloaded, On Drive, now), filled by the sheet's script
PEAK = 9310            # the "peak N" label, moved by the script to the peak's place on the graph
SHEET_TOP = 30         # the sheet starts just under the status bar (board 3: 70 pt from the top of the screen)
GRAPH = (38, 204, 897, 403)   # inside the speed card: x, y, width, height (board 3)
BUTTON_H = 134                # board 3/9: Play and Pause are 50 pt capsules, 10 pt apart
PLOT_W = 807                  # the plot's share of that width (300 of 334 pt); the axis numbers sit to its right


def capsule(p, ident, x, y, w, h, label, primary, cond):
    """Board 3's two buttons: a white capsule with black text, or a filled #3A3A3C capsule with white text."""
    fill, colour = (p.WHITE, 'FF000000') if primary else ('FF3A3A3C', p.WHITE)
    return ('<control type="group"><visible>%s</visible>' % cond + p.image(x, y, w, h, p.MEDIA + 'pill_%d.png' % h, fill, border=h // 2) +
            '<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><label>%s</label>'
            '<font>p_h3</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
            '<scroll>false</scroll><texturefocus colordiffuse="1F000000">%spill_%d.png</texturefocus><texturenofocus /></control></control>') % (
                ident, x, y, w, h, label, colour, colour, p.MEDIA, h)


def speed_card(p, u, prefix, x0, y0, w, h, wait_key):
    """Board 3/4 speed card body (inside a card at x0,y0): 'Right now', the number + unit, time left, the graph with its
    right-hand axis, times, peak marker label, and Average / Done / Started under a hairline."""
    P = u.P
    gx, gy, gw, gh = GRAPH
    has_graph = u.has(prefix + 'graph')
    b = u.text(p, x0 + 38, y0 + 38, 400, 43, 'Right now', 'p_foot', p.GREY)
    b += ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>91</height><orientation>horizontal</orientation>'
          '<itemgap>12</itemgap><usecontrolcoords>true</usecontrolcoords>' % (x0 + 38, y0 + 84, w - 400) +
          '<control type="label"><width>auto</width><scroll>false</scroll><height>91</height><font>p_title</font><textcolor>%s</textcolor><label>%s</label></control>' % (p.WHITE, P(prefix + 'num')) +
          '<control type="label"><width>auto</width><scroll>false</scroll><height>80</height><top>11</top><font>p_body</font><textcolor>%s</textcolor><aligny>bottom</aligny><label>%s</label></control>' % (p.GREY, P(prefix + 'unit')) +
          '</control>')
    b += u.text(p, x0 + w - 438, y0 + 38, 400, 51, P(prefix + 'left'), 'p_sub', p.GREY, 'right')
    plot_x, plot_y = x0 + gx, y0 + gy
    b += p.image(plot_x, plot_y, PLOT_W, gh - 54, P(prefix + 'graph'), p.WHITE, '<visible>%s</visible>' % has_graph, '>stretch')
    axis = ''.join(u.text(p, plot_x + PLOT_W + 12, plot_y + round((gh - 54) * g) - 20, gw - PLOT_W - 12, 40, P(prefix + 'axis%d' % i), 'p_cap', p.GREY)
                   for i, g in enumerate((.25, .5, .75)))
    axis += u.text(p, plot_x, plot_y + gh - 46, 400, 40, P(prefix + 'from'), 'p_cap', p.GREY)
    axis += u.text(p, plot_x + PLOT_W - 300, plot_y + gh - 46, 300, 40, 'now', 'p_cap', p.GREY, 'right')
    axis += ('<control type="label" id="%d"><left>%d</left><top>%d</top><width>300</width><height>40</height><font>p_cap</font>'
             '<textcolor>%s</textcolor><scroll>false</scroll><label>peak %s</label></control>') % (PEAK, plot_x, plot_y + round((gh - 54) * .2) - 52, p.GREY, P(prefix + 'peak'))
    b += '<control type="group"><visible>%s</visible>%s</control>' % (has_graph, axis)
    b += u.text(p, plot_x, plot_y, PLOT_W, gh - 54, P(wait_key), 'p_sub', p.GREY, 'center').replace('<scroll>false</scroll>', '<aligny>center</aligny><scroll>false</scroll><visible>%s</visible>' % u.neg(has_graph), 1)
    b += p.image(x0 + 38, y0 + h - 166, w - 76, 3, p.MEDIA + 'white.png', '1FEBEBF5')
    for i, (title, key) in enumerate((('Average', 'avg'), ('Done', 'done'), ('Started', 'started'))):
        cx = x0 + 38 + i * (w - 76) // 3
        cw = (w - 76) // 3 - 12
        b += u.text(p, cx, y0 + h - 140, cw, 43, title, 'p_foot', p.GREY) + u.text(p, cx, y0 + h - 94, cw, 54, P(prefix + key), 'p_h3')
    return b


def item_sheet(p):
    """Boards 3 and 9: a movie's sheet over the dimmed page."""
    import status_ui as u
    W, S, w, M, H = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, p.HEIGHT
    P = u.P
    top = SHEET_TOP
    body = u.tap(p, 9099, 0, 0, W, H).replace('<texturefocus colordiffuse="14FFFFFF">', '<texturefocus colordiffuse="00FFFFFF">', 1)
    body += p.image(0, 0, W, H, M + 'white.png', 'F20B0B0C')
    body += p.image(0, top, W, H, M + 'sheet_bg.png', p.SURFACE, border=102)
    body += p.image(W // 2 - 54, top + 21, 107, 13, M + 'pill11.png', 'FF48484A', border=5)
    body += p.image(S, top + 78, 172, 258, M + 'white.png', u.SURF2, diffuse=M + 'poster27.png')
    body += p.image(S, top + 78, 172, 258, P('poster'), p.WHITE, '', '>scale', M + 'poster27.png', background=True)
    body += u.text(p, S + 209, top + 140, w - 209 - 150, 70, P('title'), 'p_h2')
    body += u.text(p, S + 209, top + 223, w - 209 - 20, 51, P('quality'), 'p_sub', p.GREY)
    body += p.close_button(9200, W - S - 118, top + 78)   # the one close button of every sheet (build 173)
    cw = (w - 32) // 3
    for i in range(3):
        key = 'step%d.' % i
        x = S + i * (cw + 16)
        body += u.id_bar(p, STEP_BARS + i, x, top + 379, cw, 11, P(key + 'tint'), texture='pill11.png', border=5)
        body += u.text(p, x, top + 406, cw, 43, P(key + 'label'), 'p_foot_b' if i == 2 else 'p_foot', p.WHITE if i == 2 else p.GREY)
    ch = 803
    card = u.card(p, S, 0, w, ch, u.SURF2) + speed_card(p, u, 'card.', S, 0, w, ch, 'card.wait')
    facts = ''
    for n in range(CARD_FACTS):
        key = 'fact%d.' % n
        y = n * 129
        if n:
            facts += p.image(S + 38, y, w - 76, 3, M + 'white.png', '1FEBEBF5', '<visible>%s</visible>' % u.has(key + 'label'))
        facts += u.text(p, S + 38, y, 400, 129, P(key + 'label'), 'p_sub')
        facts += u.text(p, S + 440, y, w - 478, 129, P(key + 'value'), 'p_sub', P(key + 'tint'), 'right')
    # Board 3 / 9: one column under the steps, each part right under the one before (hidden parts take no room):
    # the speed card while it works, or the facts when it is ready; the sentence; the needs-you card when relevant.
    item = lambda h, inner, cond: '<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>' % (W, h, cond, inner)
    column = item(ch + u.GAP, card, u.has('card'))
    column += item(129 * 4 + u.GAP, u.card(p, S, 0, w, 129 * 4, u.SURF2) + facts, u.neg(u.has('card')) + ' + ' + u.neg(u.has('fact4.label')))
    column += item(129 * 5 + u.GAP, u.card(p, S, 0, w, 129 * 5, u.SURF2) + facts, u.neg(u.has('card')) + ' + ' + u.has('fact4.label'))
    column += item(170 + u.GAP, u.paragraph(p, S, 0, w, 170, P('sentence')), u.has('sentence'))
    column += item(290, u.needs(p, elevated=True), u.has('need.title'))
    body += ('<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>%s</control>') % (top + 492, W, H - 24 - BUTTON_H - 20 - top - 492, column)
    bw = (w - 27) // 2
    y = H - 24 - BUTTON_H
    body += capsule(p, 9201, S, y, bw, BUTTON_H, P('action1.label'), True, u.has('action1.label'))
    body += capsule(p, 9202, S + bw + 27, y, bw, BUTTON_H, '[COLOR %s]%s[/COLOR]' % (P('action2.colour'), P('action2.label')), False, u.has('action2.label'))
    body += capsule(p, 9203, S, y - BUTTON_H - 27, w, BUTTON_H, '[COLOR %s]%s[/COLOR]' % (P('action3.colour'), P('action3.label')), False, u.has('action3.label'))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 194: approved boards 3 and 9 -->\n<window><defaultcontrol always="true">9200</defaultcontrol><controls>' + body + '</controls></window>'


def files(p):
    import status_ui as u
    out = {p.FOLDER + '/' + WINDOW: page(p).encode(), p.FOLDER + '/' + ITEM: item_sheet(p).encode()}
    out.update({'extras/portrait/' + name: data for name, data in u.textures(p).items()})
    return out
