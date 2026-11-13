"""Library file manager L6 (DEC-043, docs/design/library-files-mockups.html board D1).

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


def _rows(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = ''
    for n in range(SLOTS):
        k = 'it.%d.' % n
        b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S, 0, w, ROW_H)
        # Board D1: a round checkbox, blue with a tick when picked.
        b += u.glyph(p, S + 38, ROW_H // 2 - 27, 54, 'circle.png', '66EBEBF5', '<visible>%s</visible>' % u.neg(u.has(k + 'on')))
        b += u.glyph(p, S + 38, ROW_H // 2 - 27, 54, 'circle-check.png', 'FF0A84FF', '<visible>%s</visible>' % u.has(k + 'on'))
        b += u.text(p, S + 128, 24, w - 166, 58, u.P(k + 'title'), 'p_body')
        b += u.text(p, S + 128, 84, w - 166, 50, u.P(k + 'line'), 'p_foot', p.GREY)
        out += u.group(p, ROW_H, b, u.has(k + 'title'))
    return out


def page(p):
    import status_ui as u
    W, H, S, w = p.WIDTH, p.HEIGHT, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    body = p.backdrop()
    body += u.link(p, ALL, S, 36, 330, 118, P('all.label'), 'left') + u.link(p, DONE, W - S - 230, 36, 230, 118, 'Done')
    body += u.text(p, S, 160, w, 100, P('title'), 'p_h2')
    body += ('<control type="group"><visible>%s</visible>%s</control>' % (u.has('watched.label'),
             u.link(p, WATCHED, S, 262, 420, 96, P('watched.label'), 'left', 'p_foot')))
    listing = ('<control type="grouplist" id="%d"><top>370</top><width>%d</width><bottom>%d</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W, BAR_H + 90) +
               _rows(p, u) + u.group(p, 120, '') + '</control>')
    body += listing
    # Board D1: the red capsule says how much space comes back before anything happens.
    bar = (u.tap(p, DELETE, S, 0, w, BAR_H) + p.image(S, 0, w, BAR_H, p.MEDIA + 'pill_134.png', 'FFFF453A', border=67) +
           u.text(p, S, 0, w, BAR_H, P('delete.label'), 'p_btn', p.WHITE, 'center'))
    body += '<control type="group"><top>%d</top><visible>%s</visible>%s</control>' % (H - BAR_H - 60, u.has('delete.label'), bar)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board D (DEC-043), drawn by library_select_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (ROW, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
