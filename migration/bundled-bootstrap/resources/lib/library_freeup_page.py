"""Library file manager L8 (DEC-043, docs/design/library-files-mockups.html board F): Free Up Space.

Draws IOSLibraryFreeUp.xml, opened by tapping the storage card on board A: back, the large title, a card with what
Google Drive holds, "SUGGESTIONS" and one row per group (biggest first) with its size line and a blue "Review ›"; each
opens board D's select list already ticked (nothing is removed without its alert). A grey footnote says deleted files
stay in Drive's Trash for 30 days. library_manager.py fills it from library_delete.free_up_groups.
"""
WINDOW = 'IOSLibraryFreeUp.xml'
BACK = 9001
ROW, SLOTS, ROW_H = 9200, 6, 190
LIST = 9300


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'Close')])
    body += u.text(p, S, 150, w, 110, 'Free Up Space', 'p_large')
    card = (u.card(p, S, 0, w, 190) + u.text(p, S + 38, 30, w - 76, 70, P('store.line'), 'p_h2') +
            u.text(p, S + 38, 108, w - 76, 50, P('store.sub'), 'p_foot', p.GREY))
    rows = ''
    for n in range(SLOTS):
        k = 'g.%d.' % n
        b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S, 0, w, ROW_H)
        b += u.text(p, S + 38, 30, w - 76 - 230, 60, u.P(k + 'title'), 'p_body')
        b += u.text(p, S + 38, 98, w - 76 - 230, 54, u.P(k + 'sub'), 'p_foot', p.GREY)
        b += u.text(p, S + w - 268, 0, 230, ROW_H, 'Review', 'p_sub', p.ACCENT, 'right')
        b += u.glyph(p, S + w - 32, ROW_H // 2 - 14, 28, 'chevron-right.png', p.ACCENT)
        rows += u.group(p, ROW_H, b, u.has(k + 'title'))
    listing = ('<control type="grouplist" id="%d"><top>290</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               u.group(p, 190 + 38, card) + u.section(p, 'SUGGESTIONS', u.has('g.0.title')) + rows +
               u.group(p, 140, u.text(p, S, 20, w, 100, P('empty'), 'p_foot', p.GREY), u.has('empty')) +
               u.group(p, 150, u.text(p, S, 30, w, 100, 'Deleted files stay in Drive\'s Trash for 30 days.',
                                      'p_foot', p.GREY)) +
               u.group(p, 200, '') + '</control>')
    body += listing
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board F (DEC-043), drawn by library_freeup_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (ROW, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
