"""The library tools' pages (owner-approved mockup docs/design/library-tools-mockups.html): Queue, Phone space, History and
AirPlay check. tool_pages.py fills them through window properties; library_tools.py says what goes in them.

- portrait/IOSQueue.xml        Library status › Waiting › Edit order: ▲ ▼ per video (no drag on iPhone).
- portrait/IOSPhoneSpace.xml   Library status › the Phone space card: one bar, a row per kind, Clear where it is safe.
- portrait/IOSHistory.xml      Transfers › History: Today / Yesterday / 7 days.
- portrait/IOSAirPlayCheck.xml and 1080i/IOSAirPlayCheck.xml   Play on TV › Last time (landscape, over the video) and an
  AirPlay notification (portrait).
Built from the same pieces as Library status and Transfers (backdrop, nav button, SURFACE cards). Every portrait control
is at least 118 units (44 pt); the landscape sheet's at least 100 (44 pt on its 1920 canvas).
"""
QUEUE, SPACE, HISTORY, AIRPLAY = 'IOSQueue.xml', 'IOSPhoneSpace.xml', 'IOSHistory.xml', 'IOSAirPlayCheck.xml'
BACK, LIST = 9001, 9300
UP, DOWN = 9810, 9830          # line row n: ▲ 9810+n, ▼ 9830+n
BAR = 9850                     # Phone space bar segments 9851..9855 (cumulative percentages)
CLEAR = 9860                   # Phone space row n: Clear 9860+n
DAY = 9870                     # History day switch 9871..9873
CLOSE = 9500                   # landscape AirPlay check: × (9099 is the dimmed screen around the sheet)
HIT = 118
ROW = 150
QUEUE_SLOTS, HELD_SLOTS, DRIVE_SLOTS, SPACE_ROWS, HISTORY_SLOTS, STEPS = 10, 3, 3, 5, 12, 4
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


def _head(p, title, sub, right=''):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    return (p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close') + right +
            p.label(S, 160, w, 110, title, 'p_large', p.WHITE, 'left', NOLABEL) +
            p.label(S, 268, w, 56, sub, 'p_sub', p.GREY, 'left', NOLABEL))


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
        sub = p.label(S + 24, 78, text_w, 50, _P(key + 'sub'), 'p_pill_s', tint, 'left', NOLABEL)
    else:
        sub = ''.join(p.label(S + 24, 78, text_w, 50, _P(key + 'sub'), 'p_pill_s', colour, 'left',
                              NOLABEL + '<visible>%s</visible>' % cond)
                      for colour, cond in ((p.GREEN, _is(key + 'tone', 'ok')), (p.GREY, '!' + _is(key + 'tone', 'ok'))))
    return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, ROW + 12, _has(key + 'title')) +
            p.surface(S - 6, 0, w + 12, ROW, 'round.png', p.SURFACE, 32) +
            p.label(S + 24, 22, text_w, 58, _P(key + 'title'), 'p_pill', p.WHITE, 'left', NOLABEL) + sub + extra + '</control>')


def _arrow(p, id, x, glyph, key):
    """A 118-unit ▲ or ▼ button; greyed and disabled at the end of the line."""
    return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>' % (x, (ROW - HIT) // 2, HIT, HIT) +
            p.image(9, 9, HIT - 18, HIT - 18, p.MEDIA + 'dot.png', '26FFFFFF', '<visible>%s</visible>' % _has(key)) +
            p.image(9, 9, HIT - 18, HIT - 18, p.MEDIA + 'dot.png', '33FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % id) +
            # Button glyphs are 46 units (APPLE-UI-POLICY §5.5).
            p.image(36, 36, 46, 46, p.MEDIA + glyph, p.WHITE, '<visible>%s</visible>' % _has(key)) +
            p.image(36, 36, 46, 46, p.MEDIA + glyph, p.DIM, '<visible>!%s</visible>' % _has(key)) +
            '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
            '<enable>%s</enable></control></control>' % (id, HIT, HIT, _has(key)))


def queue_page(p):
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE

    def line(n):
        key = 'line.%d.' % n
        arrows = _arrow(p, UP + n, S + w - 2 * HIT - 20, 'arrow_up.png', key + 'up') + _arrow(p, DOWN + n, S + w - HIT - 6, 'arrow_down.png', key + 'down')
        return _card_row(p, key, p.GREY, 2 * HIT + 30, '<control type="group"><left>0</left><top>0</top>%s</control>' % arrows)
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>340</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               _section(p, 'Converting now', _has('now.title')) + _card_row(p, 'now.', PURPLE) +
               _section(p, 'Up next', _has('line.1.title'), _P('line.count')) + ''.join(line(n) for n in range(1, QUEUE_SLOTS + 1)) +
               _foot(p, _P('line.more'), _has('line.more'), 100) +
               _section(p, 'Waiting for something', _has('held.1.title')) +
               ''.join(_card_row(p, 'held.%d.' % n, ORANGE) for n in range(1, HELD_SLOTS + 1)) +
               _section(p, 'Downloading to Google Drive', _has('drive.1.title')) +
               ''.join(_card_row(p, 'drive.%d.' % n) for n in range(1, DRIVE_SLOTS + 1)) +
               _foot(p, _P('empty'), _has('empty'), 200) +
               _foot(p, 'Moving a video to the top makes it next; the one converting now finishes first. '
                        '"Keep as it is" is in each video\'s sheet on Library status.', '', 220) + '</control>')
    return _window(p, 'library queue', BACK, _head(p, 'Queue', 'Converts one video at a time, top first') + listing)


def space_page(p):
    S, W, M, w = p.SIDE, p.WIDTH, p.MEDIA, p.WIDTH - 2 * p.SIDE
    # Kodi draws no split bar: one progress per kind, each to the running total up to it, the longest drawn first.
    segments = ''.join('<control type="progress" id="%d"><left>24</left><top>150</top><width>%d</width><height>28</height>'
                       '<texturebg border="14" colordiffuse="%s">%sdot.png</texturebg><lefttexture />'
                       '<midtexture border="14" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'
                       % (BAR + n, w - 48, '52787880' if n == SPACE_ROWS else '00000000', M, _P('space.%d.tint' % n), M)
                       for n in range(SPACE_ROWS, 0, -1))
    card = ('<control type="group"><left>%d</left><top>350</top>' % S + p.surface(-6, 0, w + 12, 230, 'round.png', p.SURFACE, 32) +
            p.label(24, 30, w - 320, 110, _P('total'), 'p_large', p.WHITE, 'left', NOLABEL) +
            p.label(w - 324, 60, 300, 60, 'used by Kodi', 'p_foot', p.GREY, 'right', NOLABEL) + segments + '</control>')

    def row(n):
        key = 'space.%d.' % n
        # 124: a capsule height portrait.CAPSULES makes a texture for (118 has none).
        clear = p.pill_button(CLEAR + n, S + w - 200, (ROW - 124) // 2, 180, 124, 'Clear', [('', 'noop')], 'glass', '',
                              '<visible>%s</visible>' % _has(key + 'clear'))
        return ('<control type="group"><width>%d</width><height>%d</height>' % (W, ROW + 12) +
                p.surface(S - 6, 0, w + 12, ROW, 'round.png', p.SURFACE, 32) +
                p.surface(S + 24, 31, 88, 88, 'round_s.png', _P(key + 'tint'), 26) +
                p.icon(S + 44, 51, 48, p.ICONS + _P(key + 'icon'), p.WHITE) +
                p.label(S + 136, 22, w - 136 - 420, 58, _P(key + 'name'), 'p_pill', p.WHITE, 'left', NOLABEL) +
                p.label(S + 136, 78, w - 136 - 230, 50, _P(key + 'line'), 'p_cap', p.GREY, 'left', NOLABEL) +
                p.label(S + w - 420, 22, 190, 58, _P(key + 'size'), 'p_pill_s', p.WHITE, 'right', NOLABEL) +
                clear + '</control>')
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>600</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               _section(p, 'What uses it', 'true') + ''.join(row(n) for n in range(1, SPACE_ROWS + 1)) +
               _foot(p, 'Movies never stay on the phone: they live on Google Drive. Kodi always leaves at least 5 GB free for you.', '', 200) +
               '</control>')
    return _window(p, 'phone space', BACK, _head(p, 'Phone space', _P('free')) + card + listing)


def history_page(p):
    S, W, M, w = p.SIDE, p.WIDTH, p.MEDIA, p.WIDTH - 2 * p.SIDE
    n = len(DAYS)
    switch = ('<control type="group"><left>%d</left><top>340</top>' % S + p.surface(0, 0, w, 88, 'pill_96.png', p.SURFACE, 44) +
              ''.join('<control type="group"><left>%d</left><top>0</top>' % (i * w // n) +
                      p.image(4, 4, w // n - 8, 80, M + 'pill_96.png', 'FF636366', '<visible>%s</visible>' % _is('day', key), border=40) +
                      '<control type="button" id="%d"><top>-15</top><width>%d</width><height>%d</height><label>%s</label><font>p_foot_b</font>'
                      '<textoffsetx>0</textoffsetx><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align>'
                      '<aligny>center</aligny><texturefocus /><texturenofocus /></control></control>'
                      % (DAY + 1 + i, w // n, HIT, text, p.GREY, p.WHITE) for i, (key, text) in enumerate(DAYS)) +
              '</control>')
    week = ('<control type="group"><left>%d</left><top>460</top>' % S + p.surface(-6, 0, w + 12, 200, 'round.png', p.SURFACE, 32) +
            p.label(24, 20, w - 48, 44, 'Last 7 days', 'p_cap', p.GREY, 'left', NOLABEL) +
            p.label(24, 62, w - 48, 80, _P('week.total'), 'p_h2', p.WHITE, 'left', NOLABEL) +
            p.label(24, 140, w - 48, 44, _P('week.line'), 'p_cap', p.GREY, 'left', NOLABEL) + '</control>')

    def entry(k):
        key = 'h.%d.' % k
        return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, ROW, _has(key + 'title')) +
                p.label(S + 12, 18, w - 24, 58, _P(key + 'title'), 'p_pill', p.WHITE, 'left', NOLABEL) +
                p.label(S + 12, 78, w - 24, 50, _P(key + 'result'), 'p_pill_s', p.GREEN, 'left', NOLABEL + '<visible>%s</visible>' % _is(key + 'tone', 'ok')) +
                p.label(S + 12, 78, w - 24, 50, _P(key + 'result'), 'p_pill_s', RED, 'left', NOLABEL + '<visible>%s</visible>' % _is(key + 'tone', 'bad')) +
                p.label(S + 12, 78, w - 24, 50, _P(key + 'line'), 'p_cap', p.GREY, 'right', NOLABEL) +
                p.image(S + 12, ROW - 2, w - 24, 2, M + 'white.png', p.SEP) + '</control>')
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>690</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               ''.join(entry(k) for k in range(1, HISTORY_SLOTS + 1)) + _foot(p, _P('more'), _has('more'), 100) +
               _foot(p, _P('empty'), _has('empty'), 160) +
               _foot(p, 'Kept for 30 days. Speeds are measured on the phone.', '', 140) + '</control>')
    return _window(p, 'transfer history', DAY + 1, _head(p, 'History', 'What finished, how long it took and how fast') + switch + week + listing)


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
    return _window(p, 'airplay check', BACK, _head(p, _P('title'), _P('when')) + headline + listing)


def airplay_sheet():
    """1080i/IOSAirPlayCheck.xml: the same check as a sheet over the video (Play on TV › Last time), on Fuse's 1920x1080
    canvas with Fuse's fonts, like the Play on TV sheet."""
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
            lab(134, 30, w - 300, 56, _P('title'), 'font_head_bold') +
            lab(134, 84, w - 300, 40, '%s · %s' % (_P('headline'), _P('when')), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('headline')) +
            lab(134, 84, w - 300, 40, _P('empty'), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('empty')) +
            '<control type="button" id="%d"><left>%d</left><top>28</top><width>100</width><height>100</height><label>×</label><font>font_main_bold</font>'
            '<textcolor>FFD1D1D6</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturefocus colordiffuse="40FFFFFF">%sdot.png</texturefocus><texturenofocus colordiffuse="1FFFFFFF">%sdot.png</texturenofocus>'
            '<onclick>Close</onclick></control>' % (CLOSE, w - 130, MEDIA, MEDIA) +
            ''.join(step(n) for n in range(1, STEPS + 1)) +
            '<control type="group"><top>%d</top><visible>%s</visible>' % (150 + STEPS * row + 10, _has('try')) +
            lab(40, 0, 300, 40, 'What to try', 'font_mini', '99EBEBF5') +
            '<control type="textbox"><left>40</left><top>40</top><width>%d</width><height>90</height><font>font_mini</font>'
            '<textcolor>FFFFFFFF</textcolor><label>%s</label></control></control>' % (w - 80, _P('try')) +
            '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: AirPlay check r1 (navigation.patch_skin leaves this marker alone) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>\n') % (CLOSE, body)


def arrow(p, up):
    """A bold chevron pointing up or down (64 px, white; tinted by colordiffuse)."""
    import math

    def distance(x, y, ax, ay, bx, by):
        t = max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        return math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay))
    a, b, c = ((12, 42), (32, 22), (52, 42)) if up else ((12, 22), (32, 42), (52, 22))

    def pixel(x, y):
        d = min(distance(x + .5, y + .5, *a, *b), distance(x + .5, y + .5, *b, *c))
        return (255, 255, 255, int(255 * max(0, min(1, 4.0 - d))))
    return p.png(64, 64, pixel)


def files(p):
    return {p.FOLDER + '/' + QUEUE: queue_page(p).encode(), p.FOLDER + '/' + SPACE: space_page(p).encode(),
            p.FOLDER + '/' + HISTORY: history_page(p).encode(), p.FOLDER + '/' + AIRPLAY: airplay_page(p).encode(),
            '1080i/' + AIRPLAY: airplay_sheet().encode(),
            'extras/portrait/arrow_up.png': arrow(p, True), 'extras/portrait/arrow_down.png': arrow(p, False)}
