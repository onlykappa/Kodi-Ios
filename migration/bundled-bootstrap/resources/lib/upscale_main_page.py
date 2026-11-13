"""Settings › AI Upscale (DEC-044, docs/design/ai-upscale-library-mockups.html boards A and B).

Draws three windows, filled by upscale_settings.py from upscale_page.main_view / copy_sheet / next_rows:
- IOSUpscale.xml (board A): back, large title; the Making now card (poster, title, one line, the bar, a round
  pause/resume control) that opens the copy's sheet; Up next with Edit and up to three rows plus "Show all N"; one row
  per show; Settings (toggles, Upscale to), the iPhone's AI status, the space the copies use; red Cancel All Upscaling.
- IOSUpscaleCopy.xml (board B1): the status sheet (grabber, ✕) with the copy's poster, title, line, bar, stages, and
  Pause / Cancel Copy.
- IOSUpscaleNext.xml (board B2): Up next › Edit: – removes a copy, ≡ moves it (Move to Top / Up / Down: Kodi cannot
  drag rows), red Remove All From Up Next, Done.
Kodi skin XML in portrait units (2.687 per pt), existing helpers and tokens only (status_ui, library_page.capsule,
settings_page toggles, the Library's poster mask). No new colours, radii or button styles.
"""
WINDOW, SHEET, EDIT_WINDOW = 'IOSUpscale.xml', 'IOSUpscaleCopy.xml', 'IOSUpscaleNext.xml'
BACK = 9001
MAKING, MAKING_PAUSE = 9020, 9022
EDIT, NEXT, NEXT_SLOTS, SHOW_ALL = 9030, 9040, 3, 9050
SHOW, SHOW_SLOTS = 9200, 30
NEW, SIZE, CHARGE, ENGINE, SPACE, CANCEL_ALL = 9101, 9102, 9103, 9110, 9111, 9120
LIST = 9300
# The sheet
SHEET_CLOSE, SHEET_PAUSE, SHEET_CANCEL, SHEET_DIM = 9200, 9201, 9202, 9099
# Up next › Edit
DONE, REMOVE_ALL, ROW, REMOVE, MOVE, EDIT_SLOTS = 9002, 9010, 9200, 9300, 9400, 60
ROW_H, CARD_H = 150, 250


def _library_page():
    """library_page's capsule and sizes (loaded by path: the skin generator does not put this folder on sys.path)."""
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location('library_page', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library_page.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _poster(p, u, k, x, y, w, h):
    M = p.MEDIA
    return (p.image(x, y, w, h, M + 'poster16.png', u.SURF2) +
            p.image(x, y, w, h, u.P(k + 'poster'), p.WHITE, '', '>scale', M + 'poster16.png', background=True))


def _row(p, u, k, ident, h=ROW_H, poster=True, value=False, chevron=True):
    """A grouped row: poster tile, title, grey line, optional value and chevron, one tap area."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    b = u.row_back(p, k, w, h) + u.tap(p, ident, S, 0, w, h)
    x = S + 38
    if poster:
        b += _poster(p, u, k, S + 30, (h - 99) // 2, 66, 99)
        x = S + 130
    right = (200 if value else 0) + (70 if chevron else 0)
    b += u.text(p, x, h // 2 - 56, w - (x - S) - 38 - right, 58, u.P(k + 'title'), 'p_body')
    b += u.text(p, x, h // 2 + 4, w - (x - S) - 38 - right, 46, u.P(k + 'sub'), 'p_foot', p.GREY)
    if value:
        b += u.text(p, S + w - 38 - 70 - 200, 0, 200, h, u.P(k + 'value'), 'p_sub', p.GREY, 'right')
    if chevron:
        b += p.icon(S + w - 38 - 40, h // 2 - 20, 40, 'chevron-right.png', p.GREY)
    return b


def _toggle(p, u, k, ident, title, sub=''):
    S, w, M = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA
    h = ROW_H if sub else 130
    b = u.row_back(p, k, w, h) + u.tap(p, ident, S, 0, w, h)
    if sub:
        b += u.text(p, S + 38, h // 2 - 56, w - 240, 58, title, 'p_body')
        b += u.text(p, S + 38, h // 2 + 4, w - 240, 46, sub, 'p_foot', p.GREY)
    else:
        b += u.text(p, S + 38, 0, w - 240, h, title, 'p_body')
    b += p.image(S + w - 38 - 130, (h - 58) // 2, 130, 58, M + 'toggle_on.png', p.WHITE, '<visible>%s</visible>' % u.has(k + 'on'))
    b += p.image(S + w - 38 - 130, (h - 58) // 2, 130, 58, M + 'toggle_off.png', p.WHITE, '<visible>%s</visible>' % u.neg(u.has(k + 'on')))
    return u.group(p, h, b)


def _red(p, u, ident, label, cond):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    return u.group(p, 130, ('<control type="button" id="%d"><left>%d</left><top>6</top><width>%d</width><height>118</height>'
                            '<label>%s</label><font>p_sub</font><textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor>'
                            '<align>center</align><aligny>center</aligny><scroll>false</scroll><texturefocus colordiffuse="14FFFFFF">'
                            '%swhite.png</texturefocus><texturenofocus /></control>') % (ident, S, w, p.e(label), p.MEDIA), cond)


def _making(p, u):
    """Board A1/A3: the card. Grey bar and line when it waits (charger, heat, paused by you)."""
    S, w, M = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA
    h = CARD_H
    b = u.card(p, S, 0, w, h) + u.tap(p, MAKING, S, 0, w - 170, h)
    b += _poster(p, u, 'making.', S + 30, 30, 126, 190)
    x, tw = S + 190, w - 190 - 190
    b += u.text(p, x, 44, tw, 60, u.P('making.title'), 'p_body')
    b += u.text(p, x, 108, tw, 46, u.P('making.line'), 'p_foot', p.GREY)
    b += u.bar(p, x, 178, tw, 'making.')
    # The round pause / resume control: a ~92-unit disc in a 118-unit touch area (policy §4.7).
    cx, cy = S + w - 38 - 118, (h - 118) // 2
    b += p.image(cx + 13, cy + 13, 92, 92, M + 'avatar_s.png', u.SURF2)
    b += '<control type="group"><visible>%s</visible>%s</control>' % (u.neg(u.has('making.paused')), p.icon(cx + 29, cy + 29, 60, 'pause.png', p.WHITE))
    b += '<control type="group"><visible>%s</visible>%s</control>' % (u.has('making.paused'), p.icon(cx + 32, cy + 29, 60, 'play.png', p.WHITE))
    b += u.tap(p, MAKING_PAUSE, cx, cy, 118, 118)
    return u.group(p, h + 21, b, u.has('making.title'))


def page(p):
    import status_ui as u
    W, S, w, P = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'noop')])
    body += u.text(p, S, 150, w, 110, 'AI Upscale', 'p_large')
    rows = u.section(p, 'MAKING NOW', u.has('making.title')) + _making(p, u)
    rows += u.section(p, P('next.head'), u.has('next.head'), u.link(p, EDIT, S + w - 260, 0, 250, 118, 'Edit'))
    for n in range(NEXT_SLOTS):
        k = 'next.%d.' % n
        rows += u.group(p, ROW_H, _row(p, u, k, NEXT + n, chevron=False), u.has(k + 'title'))
    all_row = (u.row_back(p, 'all.', w, 130) + u.tap(p, SHOW_ALL, S, 0, w, 130) +
               u.text(p, S + 38, 0, w - 160, 130, P('all.label'), 'p_body', p.ACCENT) + p.icon(S + w - 78, 45, 40, 'chevron-right.png', p.GREY))
    rows += u.group(p, 130, all_row, u.has('all.label'))
    rows += u.group(p, 21, '')
    rows += u.section(p, 'SHOWS AND MOVIES', u.has('show.0.title'))
    for n in range(SHOW_SLOTS):
        k = 'show.%d.' % n
        rows += u.group(p, ROW_H, _row(p, u, k, SHOW + n, value=True), u.has(k + 'title'))
    rows += u.group(p, 120, u.paragraph(p, S + 26, 20, w - 52, 90, P('shows.note'), 'p_foot', p.GREY), u.has('shows.note'))
    rows += u.section(p, 'SETTINGS')
    rows += _toggle(p, u, 'set.new.', NEW, 'Upscale new downloads', '720p and 1080p only')
    size_row = (u.row_back(p, 'set.size.', w, 130) + u.tap(p, SIZE, S, 0, w, 130) + u.text(p, S + 38, 0, 400, 130, 'Upscale to', 'p_body') +
                u.text(p, S + w - 38 - 70 - 300, 0, 300, 130, P('set.size.value'), 'p_sub', p.GREY, 'right') +
                p.icon(S + w - 78, 45, 40, 'chevron-right.png', p.GREY))
    rows += u.group(p, 130, size_row)
    rows += _toggle(p, u, 'set.charge.', CHARGE, 'Only while charging')
    rows += u.group(p, 200, u.paragraph(p, S + 26, 20, w - 52, 170, 'Copies are made in the background and play on the TV with AirPlay. '
                                        'The original stays for the phone and older TVs. About 2.5× the size on Google Drive.', 'p_foot', p.GREY))
    rows += u.section(p, 'THIS IPHONE')
    eng = u.row_back(p, 'engine.', w, ROW_H) + u.tap(p, ENGINE, S, 0, w, ROW_H)
    eng += p.image(S + 30, (ROW_H - 81) // 2, 81, 81, p.MEDIA + 'r21.png', '33BF5AF2', border=21)
    eng += p.icon(S + 30 + 20, (ROW_H - 41) // 2, 41, 'wand-magic-sparkles.png', 'FFBF5AF2')
    eng += u.text(p, S + 140, ROW_H // 2 - 56, w - 260, 58, P('engine.title'), 'p_body')
    eng += u.text(p, S + 140, ROW_H // 2 + 4, w - 260, 46, P('engine.sub'), 'p_foot', p.GREY)
    eng += p.icon(S + w - 78, ROW_H // 2 - 20, 40, 'chevron-right.png', p.GREY)
    rows += u.group(p, ROW_H, eng)
    rows += u.section(p, 'SPACE')
    rows += u.group(p, ROW_H, _row(p, u, 'space.', SPACE, poster=False))
    rows += _red(p, u, CANCEL_ALL, 'Cancel All Upscaling', u.has('cancelall'))
    rows += u.group(p, 120, u.paragraph(p, S + 60, 0, w - 120, 110, 'Stops the copy being made and empties Up next. Copies already made stay.',
                                        'p_foot', p.GREY, 'center'), u.has('cancelall'))
    rows += u.group(p, 200, '')
    body += ('<control type="grouplist" id="%d"><top>290</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- AI Upscale (DEC-044 board A), drawn by upscale_main_page.py -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, body))


def sheet(p):
    """Board B1: the copy's status sheet."""
    import status_ui as u
    lp = _library_page()
    W, S, w, M, H, P = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, p.HEIGHT, u.P
    top = 300
    body = u.tap(p, SHEET_DIM, 0, 0, W, H).replace('<texturefocus colordiffuse="14FFFFFF">', '<texturefocus colordiffuse="00FFFFFF">', 1)
    body += p.image(0, 0, W, H, M + 'white.png', 'B3000000')
    body += p.image(0, top, W, H, M + 'sheet_bg.png', p.SURFACE, border=102)
    body += p.image(W // 2 - 54, top + 21, 107, 13, M + 'pill11.png', 'FF48484A', border=5)
    body += u.text(p, S, top + 70, w - 160, 90, 'Making now', 'p_h3')
    body += p.close_button(SHEET_CLOSE, W - S - 118, top + 50)
    y = top + 200
    ch = 920
    body += u.card(p, S, y, w, ch, u.SURF2)
    body += _poster(p, u, '', S + 38, y + 38, 172, 258)
    tx, tw = S + 240, w - 240 - 38
    body += u.paragraph(p, tx, y + 38, tw, 130, P('title'), 'p_h3', p.WHITE)
    body += u.text(p, tx, y + 176, tw, 46, P('sub'), 'p_foot', p.GREY)
    body += u.text(p, tx, y + 226, tw, 46, P('device'), 'p_foot', p.GREY)
    body += u.bar(p, S + 38, y + 340, w - 76, '')
    body += u.text(p, S + 38, y + 370, (w - 76) // 2, 46, P('stats'), 'p_foot', p.GREY)
    body += u.text(p, S + 38 + (w - 76) // 2, y + 370, (w - 76) // 2, 46, P('left'), 'p_foot', p.GREY, 'right')
    for n in range(3):
        k = 'stage%d.' % n
        sy = y + 440 + n * 70
        for state, glyph, tint in (('done', 'circle-check.png', 'FF30D158'), ('now', 'circle-play.png', 'FF0A84FF'), ('next', 'circle-minus.png', '4DEBEBF5')):
            body += '<control type="group"><visible>String.IsEqual(Window().Property(%sstate),%s)</visible>%s</control>' % (
                k, state, u.glyph(p, S + 38, sy + 8, 43, glyph, tint))
        body += u.text(p, S + 100, sy, w - 140, 60, P(k + 'label'), 'p_sub', P(k + 'tint'))
    bw = (w - 76 - 27) // 2
    body += lp.capsule(p, SHEET_PAUSE, S + 38, y + ch - 38 - lp.BUTTON_H, bw, lp.BUTTON_H, P('pause'), False, 'true')
    body += lp.capsule(p, SHEET_CANCEL, S + 38 + bw + 27, y + ch - 38 - lp.BUTTON_H, bw, lp.BUTTON_H, '[COLOR FFFF453A]Cancel Copy[/COLOR]', False, 'true')
    body += u.paragraph(p, S + 26, y + ch + 30, w - 52, 120, 'Cancel stops this copy and removes it from Up next. The original stays and plays as before.',
                        'p_foot', p.GREY)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- AI Upscale › the copy (DEC-044 board B1) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (SHEET_CLOSE, body))


def edit(p):
    """Board B2: Up next › Edit."""
    import status_ui as u
    W, S, w, P = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE, u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'noop')])
    body += u.link(p, DONE, W - S - 250, 36, 250, 118, 'Done', font='p_btn')
    body += u.text(p, S, 150, w, 110, P('heading'), 'p_large')
    rows = ''
    for n in range(EDIT_SLOTS):
        k = 'row.%d.' % n
        b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S + 130, 0, w - 260, ROW_H)
        b += u.glyph(p, S + 34, (ROW_H - 52) // 2, 52, 'circle-minus.png', 'FFFF453A') + u.tap(p, REMOVE + n, S, (ROW_H - 118) // 2, 120, 118)
        b += _poster(p, u, k, S + 130, (ROW_H - 99) // 2, 66, 99)
        b += u.text(p, S + 226, ROW_H // 2 - 56, w - 226 - 150, 58, P(k + 'title'), 'p_body')
        b += u.text(p, S + 226, ROW_H // 2 + 4, w - 226 - 150, 46, P(k + 'sub'), 'p_foot', p.GREY)
        b += p.icon(S + w - 38 - 56, ROW_H // 2 - 28, 56, 'grip-lines.png', p.GREY) + u.tap(p, MOVE + n, S + w - 130, (ROW_H - 118) // 2, 130, 118)
        rows += u.group(p, ROW_H, b, u.has(k + 'title'))
    rows += u.group(p, 200, u.paragraph(p, S + 26, 20, w - 52, 170, P('foot'), 'p_foot', p.GREY), u.has('foot'))
    rows += _red(p, u, REMOVE_ALL, P('removeall'), u.has('removeall'))
    rows += u.group(p, 200, u.text(p, S, 40, w, 60, P('empty'), 'p_foot', p.GREY, 'center'), u.has('empty'))
    body += ('<control type="grouplist" id="%d"><top>290</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- AI Upscale › Up next › Edit (DEC-044 board B2) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (DONE, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode(), p.FOLDER + '/' + SHEET: sheet(p).encode(),
            p.FOLDER + '/' + EDIT_WINDOW: edit(p).encode()}
