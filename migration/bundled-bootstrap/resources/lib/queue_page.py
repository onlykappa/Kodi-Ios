"""Library status › Queue (DEC-045, docs/design/queue-favourites-mockups.html board E).

Draws IOSQueueList.xml, one scrolling list (no Previous / More pages): "Downloading to Google Drive · N" then
"Preparing for Kodi and AirPlay · N"; each row a poster tile, the title, one grey line, and, while it moves, its
percentage and bar. Edit (top right) turns on edit mode in the same window (board E2): a red – on each row that can be
removed (it asks first), the lines icon on rows that can move (Move to Top / Up / Down: Kodi cannot drag rows), Done,
and the red "Cancel All Downloads to Drive" at the bottom. tool_windows.open_queue fills it from
library_tools.queue_page_view. Kodi skin XML, portrait units; existing helpers and tokens only.
"""
WINDOW = 'IOSQueueList.xml'
BACK, EDIT, CANCEL_ALL = 9001, 9002, 9010
DRIVE_ROW, DRIVE_MINUS, DRIVE_SLOTS = 9200, 9230, 20
PREP_ROW, PREP_MINUS, PREP_MOVE, PREP_SLOTS = 9300, 9400, 9500, 50
DRIVE_BARS, PREP_BARS = 9600, 9650
LIST = 9900
ROW_H = 160


def _row(p, u, k, ident, minus, bar, move=None):
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    editing = u.has('editing')
    b = u.row_back(p, k, w, ROW_H) + u.tap(p, ident, S + 120, 0, w - 250, ROW_H)
    # Poster (normal) or the red – (edit mode, on rows that can be removed).
    poster = (p.image(S + 30, (ROW_H - 99) // 2, 66, 99, M + 'poster16.png', u.SURF2) +
              p.image(S + 30, (ROW_H - 99) // 2, 66, 99, P(k + 'poster'), p.WHITE, '', '>scale', M + 'poster16.png', background=True))
    b += '<control type="group"><visible>%s</visible>%s</control>' % (u.neg(editing) + ' | ' + u.neg(u.has(k + 'removable')), poster)
    b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
        editing + ' + ' + u.has(k + 'removable'), u.glyph(p, S + 34, (ROW_H - 52) // 2, 52, 'circle-minus.png', 'FFFF453A'),
        u.tap(p, minus, S, (ROW_H - 118) // 2, 120, 118))
    tw = w - 130 - 38 - 170
    b += u.text(p, S + 130, 30, tw, 56, P(k + 'title'), 'p_body')
    b += u.text(p, S + 130, 88, tw, 46, P(k + 'sub'), 'p_foot', p.GREY)
    # Moving: percentage and bar (hidden in edit mode where the lines icon takes the right edge).
    moving = u.has(k + 'pct') + ' + ' + u.neg(editing)
    b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
        moving, u.text(p, S + w - 38 - 150, 30, 150, 56, P(k + 'pct'), 'p_foot_b', P(k + 'tint'), 'right'),
        u.id_bar(p, bar, S + 130, 140, w - 130 - 38, 8, P(k + 'tint'), texture='pill16.png', border=4))
    if move is not None:
        b += '<control type="group"><visible>%s</visible>%s%s</control>' % (
            editing + ' + ' + u.has(k + 'movable'), p.icon(S + w - 38 - 56, (ROW_H - 56) // 2, 56, 'grip-lines.png', p.GREY),
            u.tap(p, move, S + w - 130, (ROW_H - 118) // 2, 130, 118))
    return u.group(p, ROW_H, b, u.has(k + 'title'))


def page(p):
    import status_ui as u
    W, S, w, P = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'noop')])
    body += u.link(p, EDIT, W - S - 250, 36, 250, 118, P('edit.label'), font='p_btn')
    body += u.text(p, S, 150, w, 110, 'Queue', 'p_large')
    rows = u.section(p, P('drive.head'), u.has('drive.head'))
    for n in range(DRIVE_SLOTS):
        rows += _row(p, u, 'drive.%d.' % n, DRIVE_ROW + n, DRIVE_MINUS + n, DRIVE_BARS + n)
    rows += u.group(p, 21, '', u.has('drive.head'))
    rows += u.section(p, P('prep.head'), u.has('prep.head'))
    for n in range(PREP_SLOTS):
        rows += _row(p, u, 'prep.%d.' % n, PREP_ROW + n, PREP_MINUS + n, PREP_BARS + n, PREP_MOVE + n)
    rows += u.group(p, 90, u.text(p, S + 26, 20, w - 52, 50, P('more'), 'p_foot', p.GREY), u.has('more'))
    rows += u.group(p, 200, u.paragraph(p, S + 26, 20, w - 52, 170, P('foot'), 'p_foot', p.GREY), u.has('foot'))
    rows += u.group(p, 130, ('<control type="button" id="%d"><left>%d</left><top>6</top><width>%d</width><height>118</height>'
                             '<label>Cancel All Downloads to Drive</label><font>p_sub</font><textcolor>FFFF453A</textcolor>'
                             '<focusedcolor>FFFF453A</focusedcolor><align>center</align><aligny>center</aligny><scroll>false</scroll>'
                             '<texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>') % (
                                 CANCEL_ALL, S, w, p.MEDIA), u.has('editing') + ' + ' + u.has('cancelall'))
    rows += u.group(p, 200, u.text(p, S, 40, w, 60, P('empty'), 'p_foot', p.GREY, 'center'), u.has('empty'))
    rows += u.group(p, 200, '')
    body += ('<control type="grouplist" id="%d"><top>290</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Queue (DEC-045 board E), drawn by queue_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
