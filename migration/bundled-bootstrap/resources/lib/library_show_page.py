"""Library file manager, step L3 (DEC-043, docs/design/library-files-mockups.html board B, round 3).

Draws IOSLibraryShow.xml: the show's art behind a round back button, ••• and Select; the title and one grey line; three
numbers (episodes, size on Drive, ready for TV); season chips; then one pooled row per episode: number and name, one
state line with a coloured dot, a thin bar while it converts or copies, and a red Repair only on a problem.
library_manager.py fills it from library_files.episode_rows.
"""
WINDOW = 'IOSLibraryShow.xml'
BACK, MORE, SELECT = 9001, 9002, 9003
SEASON, SEASONS = 9110, 8
EP, SLOTS, EP_H = 9400, 60, 190
REPAIR = 9600
BAR = 9700
LIST = 9300
DOTS = (('ready', 'FF30D158'), ('converting', 'FFFF9F0A'), ('copying', 'FF0A84FF'), ('problem', 'FFFF453A'), ('unknown', 'FF30D158'))


def _round(p, u, ident, x, glyph):
    """Board B round 3: a 44 pt dark disc over the art, the glyph in white."""
    return (p.image(x, 40, 118, 118, p.MEDIA + 'pill_134.png', 'B3000000') + u.glyph(p, x + 59 - 22, 77, 44, glyph, p.WHITE) +
            u.tap(p, ident, x, 40, 118, 118))


def _numbers(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    cw = (w - 2 * 32) // 3
    out = ''
    for i, key in enumerate(('n.episodes', 'n.size', 'n.ready')):
        x = S + i * (cw + 32)
        out += (u.card(p, x, 0, cw, 190) + u.text(p, x + 34, 30, cw - 50, 76, u.P(key), 'p_h2') +
                u.text(p, x + 34, 112, cw - 50, 50, u.P(key + '.label'), 'p_foot', p.GREY))
    return out


def _seasons(p, u):
    out = ('<control type="grouplist"><left>%d</left><top>0</top><width>%d</width><height>96</height>'
           '<orientation>horizontal</orientation><itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>' % (p.SIDE, p.WIDTH - 2 * p.SIDE))
    for n in range(SEASONS):
        k = 'season.%d' % n
        on = 'String.IsEqual(Window().Property(season.on),%d)' % n
        out += ('<control type="button" id="%d"><width min="160" max="400">auto</width><height>96</height><label>%s</label>'
                '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><textoffsetx>40</textoffsetx><aligny>center</aligny>'
                '<texturenofocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturenofocus>'
                '<texturefocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturefocus>'
                '<visible>!String.IsEmpty(Window().Property(%s))</visible></control>') % (
            SEASON + n, u.P(k), p.WHITE, p.WHITE, k, p.MEDIA, k, p.MEDIA, k)   # the script tints the chosen season blue
        out += ''   # the chosen season is marked by the script (label in the selected state below)
    return out + '</control>'


def _rows(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = ''
    for n in range(SLOTS):
        k = 'ep.%d.' % n
        b = u.row_back(p, k, w, EP_H) + u.tap(p, EP + n, S, 0, w, EP_H)   # Repair is drawn above it
        b += u.text(p, S + 38, 30, w - 76 - 250, 56, u.P(k + 'title'), 'p_body')
        for state, tint in DOTS:
            b += p.image(S + 38, 108, 24, 24, p.MEDIA + 'dot.png', tint,
                         '<visible>String.IsEqual(Window().Property(%sstate),%s)</visible>' % (k, state))
        b += u.text(p, S + 80, 92, w - 80 - 300, 56, u.P(k + 'line'), 'p_foot', p.GREY)
        b += ('<control type="group"><visible>%s</visible>%s</control>' % (
            u.has(k + 'bar'), u.id_bar(p, BAR + n, S + 38, 158, w - 76 - 260, 13, u.BLUE, texture='pill16.png', border=6)))
        # A red Repair capsule only on an episode with a problem (round 2); 44 pt tall.
        b += ('<control type="group"><visible>%s</visible>%s%s</control>' % (
            u.has(k + 'repair'), p.image(S + w - 250, 36, 212, 118, p.MEDIA + 'pill_134.png', '2EFF453A'),
            '<control type="button" id="%d"><left>%d</left><top>36</top><width>212</width><height>118</height><label>Repair</label>'
            '<font>p_btn</font><textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturefocus /><texturenofocus /></control>' % (REPAIR + n, S + w - 250)))
        out += u.group(p, EP_H, b, u.has(k + 'title'))
    return out


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
    controls = (p.backdrop() + hero + head + listing + _round(p, u, BACK, S, 'chevron-left.png') +
                _round(p, u, MORE, W - S - 118 - 236, 'ellipsis.png') +
                u.link(p, SELECT, W - S - 210, 40, 210, 118, 'Select'))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board B (DEC-043), drawn by library_show_page.py -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (EP, controls))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
