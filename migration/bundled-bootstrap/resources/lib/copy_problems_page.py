"""Settings › Library › Download problems (owner-approved mockup, docs/design/download-problems-mockups.html).

Draws IOSDownloadProblems.xml: back, large title, the summary card (can try again · need a new source · cancelled),
the segmented filter, then pooled slots that are either a section header or a problem row (poster, title, one grey
line, a short reason in its colour, one action capsule), the white Retry button, the red Clear Cancelled link and
the empty state. copy_problems.py fills it. Kodi skin XML, portrait units (2.687 per pt); existing helpers only:
status_ui cards, rows and text, notifications_skin's segmented control, portrait's pill_button.
"""
WINDOW = 'IOSDownloadProblems.xml'
BACK, RETRY, CLEAR = 9001, 9010, 9011
FILTERS = (('all', 'All'), ('retry', 'Retry'), ('source', 'Source'), ('cancelled', 'Cancelled'))
FILTER0 = 9101
ROW, ACT, SLOTS, ROW_H, HEAD_H = 9200, 9400, 40, 204, 118
HEAD_CLEAR = 9500   # DEC-044 board C: Clear on the "Cancelled by you" heading, one id per slot
LIST = 9300
WHY = (('orange', 'FFFF9F0A'), ('red', 'FFFF453A'), ('grey', '99EBEBF5'))


def _summary(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    tw = (w - 2 * u.PAD - 2 * 21) // 3
    b = u.card(p, S, 0, w, 300)
    for n, (key, label, tint) in enumerate((('sum.retry', 'Can try again', p.ACCENT), ('sum.source', 'New source', u.ORANGE),
                                           ('sum.cancelled', 'Cancelled', p.WHITE))):
        x = S + u.PAD + n * (tw + 21)
        b += u.card(p, x, u.PAD, tw, 160, u.SURF2)
        b += u.text(p, x + 26, u.PAD + 14, tw - 40, 64, u.P(key), 'p_h2', tint)
        b += u.text(p, x + 26, u.PAD + 92, tw - 40, 46, label, 'p_cap', p.GREY)
    b += u.text(p, S + u.PAD, 222, w - 2 * u.PAD, 50, 'Network drops wait and carry on by themselves.', 'p_foot', p.GREY)
    return u.group(p, 300 + 32, b, u.has('sum.any'))


def _slot(p, u, n):
    S, w, M = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA
    k = 'row.%d.' % n
    head = u.text(p, S + 26, 40, w - 52 - 260, 60, u.P(k + 'head'), 'p_foot_b', p.GREY)
    # Board C (DEC-044): the Cancelled section's heading carries Clear (blue text, 118-unit hit area).
    head += '<control type="group"><visible>%s</visible>%s</control>' % (
        u.has(k + 'headclear'), u.link(p, HEAD_CLEAR + n, S + w - 260, 10, 234, 118, u.P(k + 'headclear')))
    b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S, 0, w - 230, ROW_H)
    b += p.image(S + 32, 26, 102, 152, M + 'poster16.png', u.SURF2)
    b += p.image(S + 32, 26, 102, 152, u.P(k + 'poster'), p.WHITE, '', '>scale', M + 'poster16.png', background=True)
    tx, tw = S + 164, w - 164 - 250
    b += u.text(p, tx, 24, tw, 56, u.P(k + 'title'), 'p_h3')
    b += u.text(p, tx, 82, tw, 46, u.P(k + 'sub'), 'p_foot', p.GREY)
    for name, tint in WHY:
        b += '<control type="group"><visible>String.IsEqual(Window().Property(%swhyc),%s)</visible>%s</control>' % (
            k, name, u.text(p, tx, 130, tw, 46, u.P(k + 'why'), 'p_foot', tint))
    # The row's one action: a small SURFACE2 capsule with blue words, inside a 118-unit hit area (policy §4.5).
    b += p.image(S + w - 230, ROW_H // 2 - 42, 196, 84, M + 'r21.png', u.SURF2, border=21)
    b += ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>196</width><height>118</height><label>%s</label>'
          '<font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
          '<scroll>false</scroll><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>') % (
              ACT + n, S + w - 230, ROW_H // 2 - 59, u.P(k + 'act'), p.ACCENT, p.ACCENT, M)
    return u.group(p, HEAD_H, head, u.has(k + 'head')) + u.group(p, ROW_H, b, u.has(k + 'title'))


def page(p):
    import status_ui as u
    import notifications_skin as ns
    W, S, w, P = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'Close')])
    body += u.text(p, S, 150, w, 110, 'Download problems', 'p_large')
    rows = _summary(p, u)
    rows += u.group(p, 118 + 10, ns.segmented(p, FILTERS, y=10, base=FILTER0), u.has('sum.any'))
    for n in range(SLOTS):
        rows += _slot(p, u, n)
    rows += u.group(p, 90, u.text(p, S + 26, 24, w - 52, 50, P('more'), 'p_foot', p.GREY), u.has('more'))
    rows += u.group(p, 160, p.pill_button(RETRY, S, 36, w, 124, P('retry.label'), [('', 'noop')], 'primary', extra=u.NOS),
                    u.has('retry.label'))
    rows += u.group(p, 190, u.paragraph(p, S + 26, 20, w - 52, 160, P('foot'), 'p_foot'), u.has('foot'))
    rows += u.group(p, 130, ('<control type="button" id="%d"><left>%d</left><top>6</top><width>%d</width><height>118</height>'
                             '<label>%s</label><font>p_sub</font><textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor>'
                             '<align>center</align><aligny>center</aligny><scroll>false</scroll><texturefocus colordiffuse="14FFFFFF">'
                             '%swhite.png</texturefocus><texturenofocus /></control>') % (CLEAR, S, w, P('clear.label'), p.MEDIA),
                    u.has('clear.label'))
    # Board D: the empty state says what is empty and what would appear (policy §6).
    empty = (u.glyph(p, W // 2 - 60, 120, 120, 'circle-check.png', 'FF30D158') +
             u.text(p, S, 260, w, 70, 'No download problems', 'p_h3', p.WHITE, 'center') +
             u.paragraph(p, S + 60, 340, w - 120, 140, 'Every copy is on Google Drive or on its way. Anything that stops shows up here.',
                         'p_foot', p.GREY, 'center'))
    rows += u.group(p, 520, empty, u.has('empty'))
    rows += u.group(p, 100, u.text(p, S, 20, w, 60, P('none'), 'p_foot', p.GREY, 'center'), u.has('none'))
    rows += u.group(p, 200, '')
    body += ('<control type="grouplist" id="%d"><top>290</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Download problems (approved mockup), drawn by copy_problems_page.py -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
