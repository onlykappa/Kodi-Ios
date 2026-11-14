"""Library file manager L6 (DEC-043, docs/design/library-files-mockups.html board D1).

DEC-047 board D: for a show's episodes, each row has its still and number, season chips and a toolbar (Better Version,
Prepare Again, Delete); other lists (Free Up Space, Check Drive) keep the red capsule below.
Draws IOSLibrarySelect.xml: "Select All" (left) and "Done" (right), "N selected" as the title, an optional
"Watched (n)" link, then one pooled row per video with a round checkbox, its title and a grey size line; a red
"Delete N · size" capsule at the bottom once something is ticked. Board D2's alert is a Kodi yes/no dialog.
library_manager.py (open_select) fills it from library_delete; Free Up Space (L8) opens it already ticked.
Kodi skin XML, portrait units; existing helpers and tokens only.
"""
WINDOW = 'IOSLibrarySelect.xml'
DONE, ALL, WATCHED, DELETE = 9002, 9004, 9005, 9800
ROW, SLOTS, ROW_H = 9200, 80, 160
LIST = 9300
BAR_H = 134
# DEC-047 board D: for a show's episodes, the rows carry their still and number, season chips pick the season shown, and a
# toolbar acts on the chosen episodes (Better Version, Prepare Again, Delete); other lists keep the red Delete capsule.
SEASON, SEASONS = 9110, 8
BETTER, PREPARE, TOOL_DELETE = 9810, 9811, 9812
TOOL_H = 190
THUMB_W, THUMB_H = 172, 97


def _rows(p, u):
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    out = ''
    for n in range(SLOTS):
        k = 'it.%d.' % n
        pic = u.has(k + 'num')
        b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S, 0, w, ROW_H)
        b += p.image(S, 0, w, ROW_H, M + 'white.png', '140A84FF', '<visible>%s + %s</visible>' % (u.has(k + 'on'), pic))
        # Board D1: a round checkbox, blue with a tick when picked.
        b += u.glyph(p, S + 38, ROW_H // 2 - 27, 54, 'circle.png', '66EBEBF5', '<visible>%s</visible>' % u.neg(u.has(k + 'on')))
        b += u.glyph(p, S + 38, ROW_H // 2 - 27, 54, 'circle-check.png', 'FF0A84FF', '<visible>%s</visible>' % u.has(k + 'on'))
        ty = (ROW_H - THUMB_H) // 2
        still = (p.image(S + 120, ty, THUMB_W, THUMB_H, M + 'thumb16.png', p.SURFACE2, border=21) +
                 p.image(S + 120, ty, THUMB_W, THUMB_H, P(k + 'thumb'), p.WHITE, '', '>scale', M + 'thumb16.png', background=True) +
                 u.text(p, S + 132, ty + THUMB_H - 42, 120, 38, P(k + 'num'), 'p_cap', p.WHITE))
        tx = S + 120 + THUMB_W + 30
        b += '<control type="group"><visible>%s</visible>%s%s%s</control>' % (
            pic, still, u.paragraph(p, tx, 14, w - (tx - S) - 30, 106, P(k + 'title'), 'p_sub', p.WHITE),
            u.text(p, tx, 104, w - (tx - S) - 30, 44, P(k + 'line'), 'p_foot', p.GREY))
        b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
            u.neg(pic), u.text(p, S + 128, 24, w - 166, 58, P(k + 'title'), 'p_body'),
            u.text(p, S + 128, 84, w - 166, 50, P(k + 'line'), 'p_foot', p.GREY))
        out += u.group(p, ROW_H, b, u.has(k + 'title'))
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
            SEASON + n, u.P(k), k, k, k, p.MEDIA, k, p.MEDIA, k)
    return out + '</control>'


def _toolbar(p, u):
    """Board D1/D3: three actions with a glyph over a short label; grey until something is picked, Delete red."""
    W, H, M = p.WIDTH, p.HEIGHT, p.MEDIA
    b = p.image(0, 0, W, TOOL_H + 60, M + 'white.png', 'F81C1C1E') + p.image(0, 0, W, 3, M + 'white.png', '29EBEBF5')
    cw = W // 3
    any_ = u.has('any')
    for i, (ident, glyph, label, tint) in enumerate(((BETTER, 'arrows-rotate.png', 'Better Version', p.ACCENT),
                                                     (PREPARE, 'arrow-rotate-right.png', 'Prepare Again', p.ACCENT),
                                                     (TOOL_DELETE, 'trash.png', 'Delete', 'FFFF453A'))):
        x = i * cw
        for cond, colour in ((any_, tint), (u.neg(any_), '4DEBEBF5')):
            b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
                cond, u.glyph(p, x + cw // 2 - 24, 34, 48, glyph, colour), u.text(p, x, 92, cw, 50, label, 'p_cap', colour, 'center'))
        b += u.tap(p, ident, x, 0, cw, TOOL_H)
    return '<control type="group"><top>%d</top><visible>%s</visible>%s</control>' % (H - TOOL_H - 60, u.has('tools'), b)


def page(p):
    import status_ui as u
    W, H, S, w = p.WIDTH, p.HEIGHT, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    body = p.backdrop()
    body += u.link(p, ALL, S, 36, 330, 118, P('all.label'), 'left') + u.link(p, DONE, W - S - 230, 36, 230, 118, 'Done', font='p_btn')
    body += u.text(p, S, 160, w, 100, P('title'), 'p_h2')
    body += u.text(p, S, 258, w, 50, P('count'), 'p_foot', p.GREY)
    body += ('<control type="group"><visible>%s</visible>%s</control>' % (u.has('watched.label'),
             u.link(p, WATCHED, W - S - 420, 236, 420, 96, P('watched.label'), 'right', 'p_foot')))
    chips = '<control type="group"><top>330</top><visible>%s</visible>%s</control>' % (u.has('season.1'), _seasons(p, u))
    listing = ('<control type="grouplist" id="%d"><top>340</top><width>%d</width><bottom>%d</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
               '<animation effect="slide" start="0,0" end="0,120" time="0" condition="%s">Conditional</animation>' % (
                   LIST, W, TOOL_H + 60 + 140, u.has('season.1')) +
               _rows(p, u) + u.group(p, 220, '') + '</control>')
    body += chips + listing
    # Board D1 (other lists): the red capsule says how much space comes back before anything happens.
    bar = (u.tap(p, DELETE, S, 0, w, BAR_H) + p.image(S, 0, w, BAR_H, p.MEDIA + 'pill_134.png', 'FFFF453A', border=67) +
           u.text(p, S, 0, w, BAR_H, P('delete.label'), 'p_btn', p.WHITE, 'center'))
    body += '<control type="group"><top>%d</top><visible>%s + %s</visible>%s</control>' % (
        H - BAR_H - 60, u.has('delete.label'), u.neg(u.has('tools')), bar)
    body += _toolbar(p, u)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board D (DEC-043, DEC-047), drawn by library_select_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (ROW, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
