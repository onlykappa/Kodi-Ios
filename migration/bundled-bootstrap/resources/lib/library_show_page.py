"""Library file manager, step L3 (DEC-043, docs/design/library-files-mockups.html board B, round 3).

Draws IOSLibraryShow.xml: the show's art behind a round back button, ••• and Select; the title and one grey line; three
numbers (episodes, size on Drive, ready for TV); season chips; then one pooled row per episode: number and name, one
state line with a coloured dot, a thin bar while it converts or copies, and a red Repair only on a problem.
library_manager.py fills it from library_files.episode_rows.
"""
WINDOW = 'IOSLibraryShow.xml'
BACK, MORE, SELECT = 9001, 9002, 9003
SEASON, SEASONS = 9110, 8
EP, SLOTS, EP_H = 9400, 60, 200
REPAIR = 9600
BAR = 9700
LIST = 9300
# DEC-047 board C: the ••• menu, drawn by this page (Kodi's context menu let the next tap fall through to the page behind).
MENU_DIM, MENU = 9799, 9800       # the catcher behind the menu, then up to MENU_ITEMS rows (9800-9804)
MENU_ITEMS, MENU_W, MENU_ROW = 5, 680, 150
DOTS = (('ready', 'FF30D158'), ('converting', 'FFFF9F0A'), ('copying', 'FF0A84FF'), ('problem', 'FFFF453A'), ('unknown', 'FF30D158'))
THUMB_W, THUMB_H = 215, 121       # 80 x 45 pt, a TMDb still at 16:9
TWO_LINES = 22                    # titles longer than this wrap to a second line (DEC-046/047: never "…")


def _round(p, u, ident, x, glyph):
    """Board B round 3: a 44 pt dark disc over the art, the glyph in white."""
    return (p.image(x, 40, 118, 118, p.MEDIA + 'pill_134.png', 'E01C1C1E') + u.glyph(p, x + 59 - 22, 77, 44, glyph, p.WHITE) +
            u.tap(p, ident, x, 40, 118, 118))


def _numbers(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    cw = (w - 2 * 32) // 3
    out = ''
    for i, key in enumerate(('n.episodes', 'n.size', 'n.ready')):
        x = S + i * (cw + 32)
        out += (u.card(p, x, 0, cw, 190) + u.text(p, x + 34, 30, cw - 50, 76, u.P(key), 'p_h2', u.P(key + '.tint')) +
                u.text(p, x + 34, 112, cw - 50, 50, u.P(key + '.label'), 'p_foot', p.GREY))
    return out


def _seasons(p, u):
    out = ('<control type="grouplist"><left>%d</left><top>0</top><width>%d</width><height>96</height>'
           '<orientation>horizontal</orientation><itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>' % (p.SIDE, p.WIDTH - 2 * p.SIDE))
    for n in range(SEASONS):
        k = 'season.%d' % n
        out += ('<control type="button" id="%d"><width min="160" max="400">auto</width><height>96</height><label>%s</label>'
                '<font>p_btn</font><textcolor>$INFO[Window().Property(%s.text)]</textcolor><focusedcolor>$INFO[Window().Property(%s.text)]</focusedcolor>'
                '<textoffsetx>40</textoffsetx><aligny>center</aligny>'
                '<texturenofocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturenofocus>'
                '<texturefocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturefocus>'
                '<visible>!String.IsEmpty(Window().Property(%s))</visible></control>') % (
            SEASON + n, u.P(k), k, k, k, p.MEDIA, k, p.MEDIA, k)   # board B: the chosen season white with black text
    return out + '</control>'


def _rows(p, u):
    """DEC-047 board B: the episode's still (or a placeholder with its number), its title on one or two lines, one state line
    with a coloured dot, a thin bar while it moves, and a round Repair (or ✕ while it searches) on a missing episode."""
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    tx = S + 27 + THUMB_W + 32
    out = ''
    for n in range(SLOTS):
        k = 'ep.%d.' % n
        two, side = u.has(k + 'two'), u.has(k + 'repair') + ' | ' + u.has(k + 'searching')
        tw = w - (tx - S) - 38
        b = u.row_back(p, k, w, EP_H) + u.tap(p, EP + n, S, 0, w, EP_H)   # Repair is drawn above it
        ty = (EP_H - THUMB_H) // 2
        b += p.image(S + 27, ty, THUMB_W, THUMB_H, M + 'thumb16.png', p.SURFACE2, border=21)
        b += p.image(S + 27, ty, THUMB_W, THUMB_H, P(k + 'thumb'), p.WHITE, '', '>scale', M + 'thumb16.png', background=True)
        b += u.text(p, S + 27 + 14, ty + THUMB_H - 46, 120, 40, P(k + 'num'), 'p_cap', p.WHITE)
        for wide, cond in ((tw, u.neg(side)), (tw - 150, side)):
            b += '<control type="group"><visible>%s</visible>' % cond
            b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
                u.neg(two), u.text(p, tx, 38, wide, 56, P(k + 'title'), 'p_body'), _state(p, u, k, tx, 104, wide))
            b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
                two, u.paragraph(p, tx, 14, wide, 112, P(k + 'title'), 'p_body', p.WHITE), _state(p, u, k, tx, 128, wide))
            b += '</control>'
        b += ('<control type="group"><visible>%s</visible>%s</control>' % (
            u.has(k + 'bar'), u.id_bar(p, BAR + n, tx, EP_H - 26, w - (tx - S) - 38 - 150, 11, u.BLUE, texture='pill16.png', border=5)))
        # The round Repair: a red ring (a red disc under a smaller dark one), the arrow; ✕ while it searches. 44 pt touch area.
        cx = S + w - 38 - 92
        disc = (p.image(cx, (EP_H - 92) // 2, 92, 92, M + 'pill_134.png', '8CFF453A') +
                p.image(cx + 4, (EP_H - 92) // 2 + 4, 84, 84, M + 'pill_134.png', p.SURFACE2))
        b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
            u.has(k + 'repair') + ' + ' + u.neg(u.has(k + 'searching')), disc, u.glyph(p, cx + 46 - 20, (EP_H - 40) // 2, 40, 'arrow-rotate-right.png', p.WHITE))
        b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
            u.has(k + 'searching'), disc.replace('8CFF453A', '990A84FF'), u.glyph(p, cx + 46 - 18, (EP_H - 36) // 2, 36, 'xmark.png', p.ACCENT))
        b += '<control type="group"><visible>%s</visible>%s</control>' % (side, u.tap(p, REPAIR + n, S + w - 160, (EP_H - 118) // 2, 160, 118))
        out += u.group(p, EP_H, b, u.has(k + 'title'))
    return out


def _state(p, u, k, x, y, w):
    out = ''
    for state, tint in DOTS:
        out += p.image(x, y + 16, 24, 24, p.MEDIA + 'dot.png', tint, '<visible>String.IsEqual(Window().Property(%sstate),%s)</visible>' % (k, state))
    return out + u.text(p, x + 40, y, w - 40, 56, u.P(k + 'line'), 'p_foot', p.GREY)


def _menu(p, u):
    """DEC-047 board C: under the ••• button, rows of 150 units (an icon, the action, one grey line); Delete last and red. A
    full-screen catcher behind it closes only the menu. Shown while Window().Property(menu) is set."""
    W, S, M, P = p.WIDTH, p.SIDE, p.MEDIA, u.P
    x, y = W - S - MENU_W, 176
    b = ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
         '<texturefocus colordiffuse="59000000">%swhite.png</texturefocus><texturenofocus colordiffuse="59000000">%swhite.png</texturenofocus></control>'
         % (MENU_DIM, W, p.HEIGHT, M, M))
    b += p.image(x, y, MENU_W, P('menu.h'), M + 'r27.png', 'FA2C2C2E', border=27)
    rows = ''
    for n in range(MENU_ITEMS):
        k = 'menu.%d.' % n
        red = 'String.IsEqual(Window().Property(%sred),true)' % k
        r = '<control type="group"><top>%d</top>' % (n * MENU_ROW)
        r += p.image(x + 40, MENU_ROW - 3, MENU_W - 40, 3, M + 'white.png', '29EBEBF5', '<visible>!String.IsEmpty(Window().Property(menu.%d.label))</visible>' % (n + 1))
        r += u.glyph(p, x + 38 + 22, (MENU_ROW - 44) // 2, 44, P(k + 'icon'), p.WHITE, '<visible>!%s</visible>' % red)
        r += u.glyph(p, x + 38 + 22, (MENU_ROW - 44) // 2, 44, P(k + 'icon'), 'FFFF453A', '<visible>%s</visible>' % red)
        r += '<control type="group"><visible>!String.IsEmpty(Window().Property(%ssub))</visible>%s%s</control>' % (
            k, u.text(p, x + 130, 24, MENU_W - 160, 56, P(k + 'label'), 'p_body', P(k + 'tint')),
            u.text(p, x + 130, 80, MENU_W - 160, 44, P(k + 'sub'), 'p_cap', p.GREY))
        r += '<control type="group"><visible>String.IsEmpty(Window().Property(%ssub))</visible>%s</control>' % (
            k, u.text(p, x + 130, 0, MENU_W - 160, MENU_ROW, P(k + 'label'), 'p_body', P(k + 'tint')))
        r += u.tap(p, MENU + n, x, 0, MENU_W, MENU_ROW)
        rows += '<control type="group"><visible>!String.IsEmpty(Window().Property(%slabel))</visible>%s</control></control>' % (k, r)
    b += '<control type="group"><top>%d</top>%s</control>' % (y, rows)
    return ('<control type="group"><visible>!String.IsEmpty(Window().Property(menu))</visible>'
            '<animation effect="fade" start="0" end="100" time="180" tween="cubic" easing="out">Visible</animation>'
            '<animation effect="fade" start="100" end="0" time="120">Hidden</animation>%s</control>' % b)


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    hero = (p.image(0, 0, W, 760, P('fanart'), 'FFFFFFFF', aspect='>scale') +
            p.image(0, 0, W, 760, p.MEDIA + 'fade_up.png', 'FF000000'))
    head = (u.text(p, S, 520, w, 110, P('title'), 'p_large') + u.text(p, S, 632, w, 56, P('sub'), 'p_sub', p.GREY))
    listing = ('<control type="grouplist" id="%d"><top>720</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               u.group(p, 190 + 38, _numbers(p, u)) + u.group(p, 96 + 38, _seasons(p, u), u.has('season.1')) +
               _rows(p, u) + u.group(p, 160, u.text(p, S, 30, w, 100, P('empty'), 'p_foot', p.GREY), u.has('empty')) +
               u.group(p, 260, '') + '</control>')
    # DEC-047: one capsule holding Select and ••• (drawn about 90 % opaque so it reads over any artwork).
    pair = (p.image(W - S - 400, 40, 400, 118, p.MEDIA + 'pill_134.png', 'E01C1C1E', border=59) +
            p.image(W - S - 160, 64, 3, 70, p.MEDIA + 'white.png', '24FFFFFF') +
            u.link(p, SELECT, W - S - 400, 40, 240, 118, 'Select', 'center', 'p_btn', p.WHITE) +
            u.glyph(p, W - S - 80 - 22, 77, 44, 'ellipsis.png', p.WHITE) + u.tap(p, MORE, W - S - 160, 40, 160, 118))
    controls = (p.backdrop() + hero + head + listing + _round(p, u, BACK, S, 'chevron-left.png') + pair + _menu(p, u))
    # DEC-047 board C: a dialog, like the other Library pages, so nothing is drawn or tapped behind it.
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library show page (DEC-043 board B, DEC-047 boards B and C), drawn by library_show_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (EP, controls))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
