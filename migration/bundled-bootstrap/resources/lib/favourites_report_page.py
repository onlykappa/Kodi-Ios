"""The last import's report (owner, 2026-11-15: the full page of mockup board I3, "have it be an option in the import page,
don't make it pull up when it's done, make a place for me to check it"). Opened from Import a List › Last import.

Properties (set by favourites_import_page.Report from favourites_import.report_properties): title, sub, added, lines,
dup.title / dup.text / dup.pos, ask.*, miss.*, foot, empty. Buttons: BACK, DONE, DUP / ASK / MISS (the three groups),
VIEW (View Favourites)."""
WINDOW = 'IOSImportReport.xml'
BACK, DONE, VIEW = 9001, 9002, 9010
DUP, ASK, MISS = 9101, 9102, 9103
TEXT_LINES = 3          # each group lists its titles on up to three lines; the text itself says "and N more"
GROUPS = (('dup', DUP, 'FFFFFFFF'), ('ask', ASK, 'FF4FA8FF'), ('miss', MISS, 'FFFF9F0A'))


def page(p):
    import status_ui as u
    S, W, w, P = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE, u.P
    head = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close')
    head += u.link(p, DONE, W - S - 260, 41, 260, 118, 'Done', font='p_body')
    head += u.text(p, S, 150, w, 110, P('title'), 'p_large')
    head += p.textbox(S, 262, w, 46, P('sub'), 'p_cap', p.GREY)
    summary = u.card(p, S, 0, w, 190)
    summary += u.text(p, S + 38, 30, w - 76, 62, P('added'), 'p_h3')
    summary += p.textbox(S + 38, 102, w - 76, 50, P('lines'), 'p_foot', p.GREY)
    rows = u.group(p, 190 + 30, summary, u.has('added'))
    for key, ident, tint in GROUPS:
        k = key + '.'
        for n in range(1, TEXT_LINES + 1):      # as tall as its text: k.lines is 1-3 (favourites_import.report_properties)
            row_h = 30 + 54 + 4 + n * 44 + 28
            b = u.row_back(p, k, w, row_h) + u.tap(p, ident, S, 0, w, row_h)
            b += u.text(p, S + 38, 30, w - 76 - 60, 54, P(k + 'title'), 'p_pill', tint)
            b += p.textbox(S + 38, 30 + 54 + 4, w - 76 - 60, n * 44, P(k + 'text'), 'p_foot', p.GREY)
            b += u.glyph(p, S + w - 66, (row_h - 34) // 2, 34, 'chevron-right.png', p.GREY)
            rows += u.group(p, row_h, b, '%s + String.IsEqual(Window().Property(%slines),%d)' % (u.has(k + 'title'), k, n))
    rows += u.group(p, 150, p.textbox(S + 20, 26, w - 40, 100, P('foot'), 'p_cap', p.GREY), u.has('foot'))
    rows += u.group(p, 160, p.pill_button(VIEW, S, 10, w, 128, 'View Favourites', [('', 'noop')], 'primary', extra=u.NOS), u.has('added'))
    rows += u.group(p, 300, u.text(p, S, 80, w, 80, P('empty'), 'p_h3', p.GREY, 'center'), u.has('empty'))
    rows += u.group(p, 200, '')
    body = head + ('<control type="grouplist" id="9300"><top>330</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
                   '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % W) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Favourites import report (board I3) -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<controls>%s</controls></window>' % (BACK, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
