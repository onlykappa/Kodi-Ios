"""The library tools' pages (owner-approved mockup docs/design/library-tools-mockups.html): Queue, History and AirPlay
check (owner, build 173: no Phone space page, videos live on Google Drive). tool_pages.py fills them through window
properties; library_tools.py says what goes in them.

- portrait/IOSQueue.xml        Library status › Waiting › Edit order: ▲ ▼ per video (no drag on iPhone).
- portrait/IOSHistory.xml      Transfers › History: Today / Yesterday / 7 days.
- portrait/IOSAirPlayCheck.xml and 1080i/IOSAirPlayCheck.xml   Play on TV › Last time (landscape, over the video) and an
  AirPlay notification (portrait).
Built from the same pieces as Library status and Transfers (backdrop, nav button, SURFACE cards). Every portrait control
is at least 118 units (44 pt); the landscape sheet's at least 100 (44 pt on its 1920 canvas).
"""
QUEUE, HISTORY, AIRPLAY = 'IOSQueue.xml', 'IOSHistory.xml', 'IOSAirPlayCheck.xml'
BACK, LIST = 9001, 9300
UP, DOWN = 9810, 9830          # line row n: ▲ 9810+n, ▼ 9830+n
DAY = 9870                     # History day switch 9871..9873
CLOSE = 9500                   # landscape AirPlay check: × (9099 is the dimmed screen around the sheet)
HIT = 118
ROW = 150
QUEUE_SLOTS, HELD_SLOTS, DRIVE_SLOTS, HISTORY_SLOTS, STEPS = 10, 3, 3, 12, 4
DAYS = (('today', 'Today'), ('yesterday', 'Yesterday'), ('week', '7 days'))   # library_tools.DAYS
PURPLE, ORANGE, RED = 'FFBF5AF2', 'FFFF9F0A', 'FFFF453A'
NOLABEL = '<scroll>false</scroll>'


def _P(k):
    return '$INFO[Window().Property(%s)]' % k


def _has(k):
    return '!String.IsEmpty(Window().Property(%s))' % k


def _is(k, v):
    return 'String.IsEqual(Window().Property(%s),%s)' % (k, v)


def _window(p, comment, default, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s %s -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation><controls>%s</controls></window>\n'
            ) % (p.MARKER, comment, default, body)


def _head(p, title, sub, right='', scroll=False):
    """Back, the page's large title (a short fixed name, so it always fits) and the line under it; `scroll` lets a
    line with a video's name of any length scroll instead of being cut off."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    return (p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close') + right +
            p.label(S, 160, w, 110, title, 'p_large', p.WHITE, 'left', NOLABEL) +
            p.label(S, 268, w, 56, sub, 'p_sub', p.GREY, 'left', '<scroll>true</scroll>' if scroll else NOLABEL))


def _section(p, text, cond, right=''):
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    return ('<control type="group"><width>%d</width><height>96</height><visible>%s</visible>' % (W, cond) +
            p.label(S + 12, 30, w - 24, 60, text, 'p_foot_b', p.GREY) +
            (p.label(S + 12, 30, w - 24, 60, right, 'p_foot', p.GREY, 'right', NOLABEL) if right else '') + '</control>')


def _foot(p, text, cond='', height=160):
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    return ('<control type="group"><width>%d</width><height>%d</height>%s' % (W, height, '<visible>%s</visible>' % cond if cond else '') +
            p.label(S + 12, 20, w - 24, height - 40, text, 'p_cap', p.GREY, 'left', '<wrapmultiline>true</wrapmultiline>') + '</control>')


def _card_row(p, key, tint=None, right=0, extra=''):
    """A grouped row: title and the line under it (in `tint`, or by `<key>tone`). `right` keeps room for buttons."""
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    text_w = w - 48 - right
    if tint:
        sub = p.label(S + 24, 84, text_w, 50, _P(key + 'sub'), 'p_pill_s', tint, 'left', NOLABEL)
    else:
        sub = ''.join(p.label(S + 24, 84, text_w, 50, _P(key + 'sub'), 'p_pill_s', colour, 'left',
                              NOLABEL + '<visible>%s</visible>' % cond)
                      for colour, cond in ((p.GREEN, _is(key + 'tone', 'ok')), (p.GREY, u.neg(_is(key + 'tone', 'ok')))))
    return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, ROW + 12, _has(key + 'title')) +
            p.surface(S - 6, 0, w + 12, ROW, 'round.png', p.SURFACE, 32) +
            p.label(S + 24, 22, text_w, 58, _P(key + 'title'), 'p_pill', p.WHITE, 'left', NOLABEL) + sub + extra + '</control>')


def _arrow(p, id, x, glyph, key):
    """A 118-unit ▲ or ▼ button; greyed and disabled at the end of the line."""
    return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>' % (x, (ROW - HIT) // 2, HIT, HIT) +
            p.image(7, 7, 104, 104, p.MEDIA + 'close_disc.png', '2EFFFFFF', '<visible>%s</visible>' % _has(key)) +
            p.image(7, 7, 104, 104, p.MEDIA + 'close_disc.png', '24FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % id) +
            # Owner (build 173): "arrows ... can be larger" and centred: the chevron is drawn centred in its own texture.
            p.image(25, 25, 68, 68, p.MEDIA + glyph, p.WHITE, '<visible>%s</visible>' % _has(key)) +
            p.image(25, 25, 68, 68, p.MEDIA + glyph, p.DIM, '<visible>%s</visible>' % u.neg(_has(key))) +
            '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
            '<enable>%s</enable></control></control>' % (id, HIT, HIT, _has(key)))


RETRY = 9890
QPREV, QNEXT, HPREV, HNEXT = 9841, 9842, 9905, 9906
QCANCEL = 9843   # Cancel All beside DOWNLOADING TO GOOGLE DRIVE (owner, 2026-11-12)


QBAR = 9850     # the Queue's running-job bar (tool_windows sets it)


def _round_arrow(p, u, ident, x, y, glyph, key):
    """Board 7: a 44 pt round button, filled #2C2C2E when it can move the row, empty and dim at the end of the line."""
    on = _has(key)
    return ('<control type="group"><left>%d</left><top>%d</top>' % (x, y) +
            p.image(0, 0, 118, 118, p.MEDIA + 'avatar_s.png', u.SURF2, '<visible>%s</visible>' % on) +
            p.image(0, 0, 118, 118, p.MEDIA + 'avatar_s.png', '1FFFFFFF', '<visible>Control.HasFocus(%d)</visible>' % ident) +
            p.image(36, 36, 46, 46, p.MEDIA + glyph, p.WHITE, '<visible>%s</visible>' % on) +
            p.image(36, 36, 46, 46, p.MEDIA + glyph, '4DEBEBF5', '<visible>%s</visible>' % u.neg(on)) +
            '<control type="button" id="%d"><width>118</width><height>118</height><label></label><texturefocus /><texturenofocus />'
            '<enable>%s</enable></control></control>' % (ident, on))


def queue_page(p):
    """Board 7 (build 194: laid out from docs/design/build-193-measurements.md)."""
    import status_ui as u
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    header = lambda title, cond, h: u.group(p, h, u.text(p, S + 10, 0, w - 20, 62, title, 'p_pill', p.GREY), cond)
    now = u.card(p, S, 0, w, 215)
    now += u.text(p, S + 38, 32, w - 230, 54, _P('now.title'), 'p_h3') + u.text(p, S + w - 188, 32, 150, 54, _P('now.percent'), 'p_pill', PURPLE, 'right')
    now += u.id_bar(p, QBAR, S + 38, 107, w - 76, 11, _P('now.tint'), texture='pill11.png', border=5)
    now += u.text(p, S + 38, 140, w - 76, 43, _P('now.sub'), 'p_foot', p.GREY)
    rows = header('WORKING ON NOW', _has('now.title'), 99) + u.group(p, 215 + 38, now, _has('now.title'))
    rows += header('UP NEXT', _has('line.1.title'), 105)
    for n in range(1, QUEUE_SLOTS + 1):
        key = 'line.%d.' % n
        later = _is(key + 'later', 'true')
        b = u.row_back(p, key, w, 174)
        b += p.image(S + 38, 48, 75, 75, p.MEDIA + 'avatar_s.png', '2E0A84FF', '<visible>%s</visible>' % u.neg(later))
        b += p.image(S + 38, 48, 75, 75, p.MEDIA + 'avatar_s.png', u.SURF2, '<visible>%s</visible>' % later)
        b += '<control type="group"><visible>%s</visible>%s</control>' % (u.neg(later), u.text(p, S + 38, 48, 75, 75, '$NUMBER[%d]' % n, 'p_foot_b', p.ACCENT, 'center'))
        b += '<control type="group"><visible>%s</visible>%s</control>' % (later, u.text(p, S + 38, 48, 75, 75, '$NUMBER[%d]' % n, 'p_foot_b', p.GREY, 'center'))
        b += u.text(p, S + 140, 38, w - 140 - 300, 54, _P(key + 'title'), 'p_body') + u.text(p, S + 140, 94, w - 140 - 300, 43, _P(key + 'sub'), 'p_foot', p.GREY)
        b += _round_arrow(p, u, UP + n, S + w - 290, 28, 'arrow_up.png', key + 'up') + _round_arrow(p, u, DOWN + n, S + w - 145, 28, 'arrow_down.png', key + 'down')
        rows += u.group(p, 174, b, _has(key + 'title'))
    rows += u.group(p, 38, '', _has('line.1.title'))
    rows += u.group(p, 100, u.text(p, S, 0, w, 60, _P('line.more'), 'p_foot', p.GREY), _has('line.more'))
    rows += header('WAITING', _has('held.1.title'), 105)
    rows += ''.join(_card_row(p, 'held.%d.' % n, p.GREY) for n in range(1, HELD_SLOTS + 1))
    # Red Cancel All on the right of the Drive heading (it asks first; tool_windows Queue). The heading leaves it room.
    cancel = u.link(p, QCANCEL, W - S - 300, -28, 290, 118, 'Cancel All').replace(
        '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>' % (p.ACCENT, p.ACCENT), '<textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor>')
    rows += u.group(p, 105, u.text(p, S + 10, 0, w - 330, 62, 'DOWNLOADING TO DRIVE', 'p_pill', p.GREY) +
                    '<control type="group"><visible>%s</visible>%s</control>' % (_has('cancel_all'), cancel), _has('drive.1.title'))
    rows += ''.join(_card_row(p, 'drive.%d.' % n, p.GREY) for n in range(1, DRIVE_SLOTS + 1))
    rows += u.group(p, 124, u.tap(p, QPREV, S, 0, w // 2, 118, 'Previous',enabled=_has('page.previous')) + u.tap(p, QNEXT, S + w // 2, 0, w // 2, 118, 'More',enabled=_has('page.more')), _has('pages'))
    rows += u.group(p, 160, u.paragraph(p, S + 10, 0, w - 20, 150, 'Moving a video to the top makes it next. Faster-start jobs are already Ready, so they wait behind new movies on their own.', 'p_foot'))
    rows += u.group(p, 100, u.text(p, S, 0, w, 60, _P('empty'), 'p_foot', p.GREY), _has('empty'))
    rows += u.group(p, 200, '')
    listing = ('<control type="grouplist" id="9300"><top>365</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<usecontrolcoords>true</usecontrolcoords>%s</control>') % (W, rows)
    return _window(p, 'library queue', BACK, _head(p, 'Queue', _P('subtitle')) + listing)


def history_page(p):
    """Board 8 (build 194): the day switch is the same segmented control as Notifications; unfinished attempts first."""
    import status_ui as u
    import notifications_skin
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    switch = notifications_skin.segmented(p, DAYS, prop='day', base=DAY + 1)
    header = lambda title, cond, h: u.group(p, h, u.text(p, S + 10, 0, w - 20, 62, title, 'p_pill', p.GREY), cond)
    rows = header("DIDN'T FINISH", _has('unfinished'), 99)
    for n in range(1, HISTORY_SLOTS + 1):
        key = 'h.%d.' % n
        b = u.glyph(p, S + 38, 32, 59, 'circle-exclamation.png', RED)
        b += u.text(p, S + 129, 32, w - 129 - 230, 54, _P(key + 'title'), 'p_body') + u.text(p, S + w - 230, 32, 192, 54, _P(key + 'when'), 'p_foot', p.GREY, 'right')
        b += u.text(p, S + 129, 91, w - 167, 43, _P(key + 'result'), 'p_foot', p.GREY)
        shown = _has(key + 'title') + ' + ' + _is(key + 'section', 'unfinished')
        # Board 8: the card holds "Try again" only when it can be retried; otherwise it ends under the reason.
        retry = (p.image(S + 129, 161, 269, 97, p.MEDIA + 'pill_96.png', u.SURF2, border=48) +
                 u.link(p, RETRY + n, S + 129, 151, 269, 118, 'Try again', 'center', 'p_pill'))
        rows += u.group(p, 290 + 21, u.card(p, S, 0, w, 290) + b + retry, shown + ' + ' + _has(key + 'retry'))
        rows += u.group(p, 172 + 21, u.card(p, S, 0, w, 172) + b, shown + ' + String.IsEmpty(Window().Property(%sretry))' % key)
    rows += u.group(p, 17, '', _has('unfinished'))
    rows += header('FINISHED', _has('finished'), 105)
    for n in range(1, HISTORY_SLOTS + 1):
        key = 'h.%d.' % n
        b = u.row_back(p, key, w, 163)
        b += u.glyph(p, S + 38, 48, 59, 'circle-check.png', p.GREEN)
        b += u.text(p, S + 129, 32, w - 129 - 230, 54, _P(key + 'title'), 'p_body') + u.text(p, S + w - 230, 32, 192, 54, _P(key + 'when'), 'p_foot', p.GREY, 'right')
        b += u.text(p, S + 129, 89, w - 167, 43, _P(key + 'result'), 'p_foot', p.GREY)
        rows += u.group(p, 163, b, _has(key + 'title') + ' + ' + _is(key + 'section', 'finished'))
    rows += u.group(p, 124, u.tap(p, HPREV, S, 0, w // 2, 118, 'Previous') + u.tap(p, HNEXT, S + w // 2, 0, w // 2, 118, 'More'), _has('pages'))
    rows += u.group(p, 160, u.text(p, S, 40, w, 70, _P('empty'), 'p_foot', p.GREY), _has('empty'))
    rows += u.group(p, 200, '')
    listing = ('<control type="grouplist" id="9300"><top>443</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<usecontrolcoords>true</usecontrolcoords>%s</control>') % (W, rows)
    return _window(p, 'transfer history', BACK, _head(p, 'History', '') + switch + listing)


def airplay_page(p):
    """Portrait: opened from an AirPlay notification."""
    S, W, M, w = p.SIDE, p.WIDTH, p.MEDIA, p.WIDTH - 2 * p.SIDE

    def step(n):
        key = 'step.%d.' % n
        icons = ''.join(p.icon(S + 24, 34, 64, glyph, colour, '<visible>%s</visible>' % _is(key + 'tone', tone))
                        for tone, glyph, colour in (('ok', 'circle-check.png', p.GREEN), ('bad', 'circle-xmark.png', RED),
                                                    ('warn', 'circle-info.png', ORANGE)))
        return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, 212, _has(key + 'name')) +
                p.surface(S - 6, 0, w + 12, 200, 'round.png', p.SURFACE, 32) + icons +
                p.label(S + 116, 20, w - 140, 44, _P(key + 'name'), 'p_cap', p.GREY, 'left', NOLABEL) +
                p.label(S + 116, 62, w - 140, 112, _P(key + 'detail'), 'p_pill_s', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>') +
                '</control>')
    tip = ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, 340, _has('try')) +
           _section(p, 'What to try', 'true').replace('<control type="group">', '<control type="group"><top>0</top>', 1) +
           '<control type="group"><top>96</top>' + p.surface(S - 6, 0, w + 12, 230, 'round.png', p.SURFACE, 32) +
           p.label(S + 24, 20, w - 48, 190, _P('try'), 'p_pill_s', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>') +
           '</control></control>')
    headline = ''.join(p.label(S, 340, w, 70, _P('headline'), 'p_h3', colour, 'left', NOLABEL + '<visible>%s</visible>' % _is('tone', tone))
                       for tone, colour in (('ok', p.GREEN), ('bad', RED)))
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>430</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               ''.join(step(n) for n in range(1, STEPS + 1)) + tip + _foot(p, _P('empty'), _has('empty'), 200) + '</control>')
    # Owner (build 173): titles must fit. The page's own name is the large title; the video's (any length) goes under it.
    sub = '[COLOR %s]%s[/COLOR] · %s' % (p.WHITE, _P('title'), _P('when'))
    return _window(p, 'airplay check', BACK, _head(p, 'AirPlay check', sub, scroll=True) + headline + listing)


def airplay_sheet(close_button_1080=None):
    """1080i/IOSAirPlayCheck.xml: the same check as a sheet over the video (Play on TV › Last time), on Fuse's 1920x1080
    canvas with Fuse's fonts, like the Play on TV sheet."""
    if close_button_1080 is None:
        import importlib.util as iu
        import os
        spec = iu.spec_from_file_location('pages_close', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages.py'))
        module = iu.module_from_spec(spec)
        spec.loader.exec_module(module)
        close_button_1080 = module.close_button_1080
    MEDIA, ICONS = 'special://skin/extras/portrait/', 'special://skin/extras/icons/'
    w, row, top = 1400, 120, 40

    def img(x, y, w, h, tex, color='FFFFFFFF', extra='', border=''):
        return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s colordiffuse="%s">%s</texture>%s</control>'
                % (x, y, w, h, ' border="%s"' % border if border else '', color, tex, extra))

    def lab(x, y, w, h, text, font, color='FFFFFFFF', align='left', extra=''):
        return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
                '<align>%s</align><aligny>center</aligny><label>%s</label>%s</control>' % (x, y, w, h, font, color, align, text, extra))

    def step(n):
        key = 'step.%d.' % n
        icons = ''.join(img(40, (row - 52) // 2, 52, 52, ICONS + glyph, colour, '<visible>%s</visible>' % _is(key + 'tone', tone))
                        for tone, glyph, colour in (('ok', 'circle-check.png', 'FF30D158'), ('bad', 'circle-xmark.png', RED),
                                                    ('warn', 'circle-info.png', ORANGE)))
        return ('<control type="group"><top>%d</top><visible>%s</visible>' % (150 + (n - 1) * row, _has(key + 'name')) +
                (img(120, 0, w - 160, 2, MEDIA + 'white.png', '1AFFFFFF') if n > 1 else '') + icons +
                lab(120, 10, 300, 40, _P(key + 'name'), 'font_mini', '99EBEBF5') +
                lab(120, 48, w - 160, 60, _P(key + 'detail'), 'font_main_bold') + '</control>')
    height = 150 + STEPS * row + 160
    body = ('<control type="image"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texture colordiffuse="73000000">%swhite.png</texture></control>' % MEDIA +
            '<control type="button" id="9099"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texturefocus /><texturenofocus />'
            '<onclick>Close</onclick><onfocus>SetFocus(%d)</onfocus></control>' % CLOSE +
            '<control type="group"><centerleft>50%%</centerleft><top>%d</top><width>%d</width>' % (top, w) +
            '<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
            '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>' +
            # As tall as it needs: the "What to try" part only when something went wrong.
            img(0, 0, w, height, MEDIA + 'sheet_l.png', border='40', extra='<visible>%s</visible>' % _has('try')) +
            img(0, 0, w, height - 120, MEDIA + 'sheet_l.png', border='40', extra='<visible>!%s</visible>' % _has('try')) +
            img(36, 40, 76, 76, MEDIA + 'dot.png', '1FFFFFFF') + img(55, 59, 38, 38, MEDIA + 'airplay.png') +
            lab(134, 30, w - 300, 56, _P('title'), 'font_head_bold', 'FFFFFFFF', 'left', '<scroll>true</scroll>') +
            lab(134, 84, w - 300, 40, '%s · %s' % (_P('headline'), _P('when')), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('headline')) +
            lab(134, 84, w - 300, 40, _P('empty'), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('empty')) +
            close_button_1080(CLOSE, w - 130, 28, '<onclick>Close</onclick>') +
            ''.join(step(n) for n in range(1, STEPS + 1)) +
            '<control type="group"><top>%d</top><visible>%s</visible>' % (150 + STEPS * row + 10, _has('try')) +
            lab(40, 0, 300, 40, 'What to try', 'font_mini', '99EBEBF5') +
            '<control type="textbox"><left>40</left><top>40</top><width>%d</width><height>90</height><font>font_mini</font>'
            '<textcolor>FFFFFFFF</textcolor><label>%s</label></control></control>' % (w - 80, _P('try')) +
            '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: AirPlay check r1 (navigation.patch_skin leaves this marker alone) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>\n') % (CLOSE, body)


def arrow(p, up):
    """A bold chevron pointing up or down (128 px, white; tinted by colordiffuse), centred both ways: its outline
    including the stroke spans the same distance above and below the middle."""
    import math

    def distance(x, y, ax, ay, bx, by):
        t = max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        return math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay))
    half, stroke = 24, 8.5         # the chevron's centre line spans 64 ± half; the stroke adds the same both ways
    a, b, c = ((20, 64 + half), (64, 64 - half), (108, 64 + half)) if up else ((20, 64 - half), (64, 64 + half), (108, 64 - half))

    def pixel(x, y):
        d = min(distance(x + .5, y + .5, *a, *b), distance(x + .5, y + .5, *b, *c))
        return (255, 255, 255, int(255 * max(0, min(1, stroke - d))))
    return p.png(128, 128, pixel)


def files(p):
    return {p.FOLDER + '/' + QUEUE: queue_page(p).encode(), p.FOLDER + '/' + HISTORY: history_page(p).encode(), p.FOLDER + '/' + AIRPLAY: airplay_page(p).encode(),
            '1080i/' + AIRPLAY: airplay_sheet(p.pages.close_button_1080).encode(),
            'extras/portrait/arrow_up.png': arrow(p, True), 'extras/portrait/arrow_down.png': arrow(p, False)}
