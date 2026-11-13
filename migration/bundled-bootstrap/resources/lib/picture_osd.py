"""1080i/IOSPictureMenu.xml: video controls › Picture (DEC-039/042, video-picture-mockups.html round 4, boards A, B, E).

The same popover as the approved Subtitles / Audio menu (pages.track_menu): a glass card under the button that opened
it, 118-unit rows, the close disc, a blue back link for the sub-page. Window properties come from picture_menu.props;
picture_page.py fills them and handles the taps.

Main page: header "Picture" and the blue scope link ("This show ›", board B); AI Upscale (only for videos under 4K):
the title, the video's own size as a grey tag, the chosen size on the right, then a slider of stops (Off, then only the
sizes above the video: 2 to 5 stops); on AirPlay the copy's state (board E: ready, preparing with its bar, or "Prepare a
4K UHD copy"); Saturation with − / + and a thin bar. Sub-page (page=apply): This video only / This show / All videos and
"Reset this show to the default".
"""
MENU = 'IOSPictureMenu.xml'
CLOSE, SCOPE, BACK_LINK, PREPARE, RESET, LIST = 9500, 9520, 9502, 9530, 9550, 9310
SAT_MINUS, SAT_PLUS = 9541, 9542
STOP_BASE = 9600          # stop k of an n-stop slider: 9600 + 10 * n + k
MEDIA = 'special://skin/extras/portrait/'
ICONS = 'special://skin/extras/icons/'
W, ROW, HEAD, PAD = 840, 118, 108, 27
UP_H = 2 * ROW + 40       # AI Upscale: its title row and the slider
TV_H = 240                # AirPlay: headline, a line that may take two rows, bar or button
NOTE_H = 80
SAT_H = ROW + 40


def stop_id(n, k):
    return STOP_BASE + 10 * n + k


def _img(x, y, w, h, tex, color='FFFFFFFF', extra='', border=''):
    return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s colordiffuse="%s">%s</texture>%s</control>'
            % (x, y, w, h, ' border="%s"' % border if border else '', color, tex, extra))


def _lab(x, y, w, h, text, font, color='FFFFFFFF', align='left', extra=''):
    return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
            '<align>%s</align><aligny>center</aligny><label>%s</label><scroll>false</scroll>%s</control>' % (x, y, w, h, font, color, align, text, extra))


def _btn(ident, x, y, w, h, extra=''):
    return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<texturefocus /><texturenofocus />%s</control>' % (ident, x, y, w, h, extra))


P = lambda k: '$INFO[Window().Property(%s)]' % k
IS = lambda k, v: 'String.IsEqual(Window().Property(%s),%s)' % (k, v)
HAS = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
EMPTY = lambda k: 'String.IsEmpty(Window().Property(%s))' % k   # never '!' + HAS(k): Kodi reads '!!X' as '!X'
MAIN = 'String.IsEmpty(Window().Property(page))'


def _group(height, body, cond):
    return '<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>' % (W, height, cond, body)


def _upscale():
    """Board A: title, grey tag, chosen size; the stops slider (one drawing per stop count, 2..5)."""
    x0, x1 = PAD + 70, W - PAD - 70
    body = _img(PAD, 0, W - 2 * PAD, UP_H - 20, MEDIA + 'round_s.png', '47000000', border='26')
    body += _lab(PAD + 36, 0, 300, ROW, 'AI Upscale', 'font_main')
    # The video's own size as a grey tag, clear of the title (rig: at +270 it sat on "AI Upscale").
    body += _img(PAD + 360, (ROW - 56) // 2, 130, 56, MEDIA + 'pill_72.png', '1FFFFFFF', border='28')
    body += _lab(PAD + 360, 0, 130, ROW, P('src'), 'font_mini', '99EBEBF5', 'center')
    body += _lab(W - PAD - 236, 0, 200, ROW, P('chosen'), 'font_main_bold', 'FF4FA8FF', 'right')
    ty = ROW + 26
    body += _img(x0, ty - 4, x1 - x0, 8, MEDIA + 'dot.png', '33FFFFFF', border='4')
    for n in range(2, 6):
        cond_n = IS('stops', n)
        for k in range(n):
            x = x0 + (x1 - x0) * k // (n - 1)
            on = '%s + %s' % (cond_n, IS('sel', k))
            # The blue fill up to the chosen stop, the knob on it, a tick and the stop's name under every stop.
            if k:
                body += _img(x0, ty - 4, x - x0, 8, MEDIA + 'dot.png', 'FF0A84FF', '<visible>%s</visible>' % on, '4')
            body += _img(x - 9, ty - 9, 18, 18, MEDIA + 'dot.png', '80FFFFFF', '<visible>%s</visible>' % cond_n, '9')
            body += _img(x - 26, ty - 26, 52, 52, MEDIA + 'knob.png', 'FFFFFFFF', '<visible>%s</visible>' % on)
            body += _lab(x - 90, ty + 30, 180, 50, P('stop.%d' % k), 'font_mini', 'FFFFFFFF', 'center',
                         '<visible>%s + %s</visible>' % (cond_n, IS('sel', k)))
            body += _lab(x - 90, ty + 30, 180, 50, P('stop.%d' % k), 'font_mini', '99EBEBF5', 'center',
                         '<visible>%s + !%s</visible>' % (cond_n, IS('sel', k)))
            body += _btn(stop_id(n, k), x - 90, ty - 60, 180, 150, '<visible>%s</visible>' % cond_n)
    return _group(UP_H, body, '%s + %s' % (MAIN, HAS('upscale')))


def _tv():
    """Board E: on AirPlay, the copy's state under the slider."""
    body = _lab(PAD + 36, 0, W - 2 * PAD - 72, 60, P('tv.head'), 'font_main_bold', 'FFFFFFFF', 'left', '<visible>%s</visible>' % HAS('tv.head'))
    body += _lab(PAD + 36, 54, W - 2 * PAD - 72, 100, P('tv.line'), 'font_mini', '99EBEBF5', 'left',
                 '<wrapmultiline>true</wrapmultiline>').replace('<aligny>center</aligny>', '<aligny>top</aligny>')
    # Preparing: the thin bar (DEC-036), filled by the script (Kodi cannot read a percentage from a property).
    body += ('<control type="progress" id="9531"><left>%d</left><top>%d</top><width>%d</width><height>11</height><visible>%s</visible>'
             '<texturebg border="5" colordiffuse="33FFFFFF">%sdot.png</texturebg><lefttexture />'
             '<midtexture border="5" colordiffuse="FF0A84FF">%sdot.png</midtexture><righttexture /></control>') % (
        PAD + 36, 176, W - 2 * PAD - 72, IS('tv.state', 'preparing'), MEDIA, MEDIA)
    # Not prepared yet: one white capsule.
    body += _img(PAD + 36, 158, W - 2 * PAD - 72, 72, MEDIA + 'pill_72.png', 'FFFFFFFF', '<visible>%s</visible>' % HAS('tv.button'), '36')
    body += _lab(PAD + 36, 158, W - 2 * PAD - 72, 72, P('tv.button'), 'font_main_bold', 'FF000000', 'center', '<visible>%s</visible>' % HAS('tv.button'))
    body += _btn(PREPARE, PAD + 36, 140, W - 2 * PAD - 72, 108, '<visible>%s</visible>' % HAS('tv.button'))
    return _group(TV_H, body, '%s + %s + %s' % (MAIN, HAS('upscale'), HAS('tv')))


def _note():
    return _group(NOTE_H, _lab(PAD + 36, 0, W - 2 * PAD - 72, NOTE_H, P('note'), 'font_mini', '99EBEBF5'),
                  '%s + %s' % (MAIN, HAS('note')))


def _saturation():
    disc = lambda bx, ident, plus: (
        _img(bx + 10, (ROW - 76) // 2, 86, 76, MEDIA + 'pill_72.png', '1FFFFFFF', border='36') +
        _img(bx + 10, (ROW - 76) // 2, 86, 76, MEDIA + 'pill_72.png', '24FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % ident, '36') +
        _img(bx + 35, (ROW - 6) // 2, 36, 6, MEDIA + 'white.png') + (_img(bx + 50, (ROW - 36) // 2, 6, 36, MEDIA + 'white.png') if plus else '') +
        _btn(ident, bx, 0, 106, ROW))
    x = W - PAD - 372
    body = _img(PAD, 0, W - 2 * PAD, SAT_H - 20, MEDIA + 'round_s.png', '47000000', border='26')
    body += _lab(PAD + 36, 0, 300, ROW, 'Saturation', 'font_main')
    body += disc(x, SAT_MINUS, False) + _lab(x + 106, 0, 150, ROW, P('sat'), 'font_main', 'FFFFFFFF', 'center') + disc(x + 256, SAT_PLUS, True)
    body += ('<control type="progress" id="9543"><left>%d</left><top>%d</top><width>%d</width><height>8</height>'
             '<texturebg border="4" colordiffuse="33FFFFFF">%sdot.png</texturebg><lefttexture />'
             '<midtexture border="4" colordiffuse="FFFFFFFF">%sdot.png</midtexture><righttexture /></control>') % (
        PAD + 36, ROW + 2, W - 2 * PAD - 72, MEDIA, MEDIA)
    return _group(SAT_H, body, MAIN)


def _apply_page():
    """Board B: three rows with a tick on the one that keeps this picture, then Reset and a footnote."""
    row = lambda focused: ((_img(0, 0, W - 2 * PAD, ROW, MEDIA + 'round_s.png', '1AFFFFFF', border='26') if focused else '') +
                           _img(28, (ROW - 52) // 2, 52, 52, ICONS + 'check.png', 'FF4FA8FF', '<visible>!String.IsEmpty(ListItem.Property(on))</visible>') +
                           _lab(100, 0, W - 2 * PAD - 130, ROW, '$INFO[ListItem.Label]', 'font_main'))
    body = _img(PAD, 0, W - 2 * PAD, 3 * ROW, MEDIA + 'round_s.png', '47000000', border='26')
    body += ('<control type="list" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
             '<onup>%d</onup><ondown>%d</ondown><itemlayout height="%d" width="%d">%s</itemlayout>'
             '<focusedlayout height="%d" width="%d">%s</focusedlayout></control>') % (
        LIST, PAD, W - 2 * PAD, 3 * ROW, BACK_LINK, RESET, ROW, W - 2 * PAD, row(False), ROW, W - 2 * PAD, row(True))
    body += _lab(PAD + 36, 3 * ROW + 10, W - 2 * PAD - 72, ROW, 'Reset this show to the default', 'font_main', 'FF4FA8FF')
    body += _btn(RESET, PAD, 3 * ROW + 10, W - 2 * PAD, ROW, '<onup>%d</onup>' % LIST)
    body += _lab(PAD + 36, 4 * ROW + 20, W - 2 * PAD - 72, 100, "A show's own picture wins over the default.", 'font_mini', '99EBEBF5', 'left',
                 '<wrapmultiline>true</wrapmultiline>')
    return '<control type="group"><top>%d</top><visible>!%s</visible>%s</control>' % (HEAD, MAIN, body)


def _backgrounds():
    """The card's height for each combination of what shows (no clipping in Kodi: one drawing per combination)."""
    out = ''
    for up in (0, 1):
        for tv in (0, 1):
            for note in (0, 1):
                if tv and not up:
                    continue
                h = HEAD + up * UP_H + tv * TV_H + note * NOTE_H + SAT_H + PAD
                cond = ' + '.join([MAIN, (HAS if up else EMPTY)('upscale'),
                                   (HAS if tv else EMPTY)('tv') if up else 'true',
                                   (HAS if note else EMPTY)('note')])
                out += _img(0, 0, W, h, MEDIA + 'round_s.png', 'F52C2C2E', '<visible>%s</visible>' % cond, '26')
    out += _img(0, 0, W, HEAD + 4 * ROW + 140, MEDIA + 'round_s.png', 'F52C2C2E', '<visible>!%s</visible>' % MAIN, '26')
    return out


def menu():
    head = (_lab(36, 0, 300, HEAD, P('title'), 'font_head_bold', 'FFFFFFFF', 'left', '<visible>%s</visible>' % MAIN) +
            # Board B's way in: the scope link ("This show ›"), blue, in the header.
            ('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label>%s  ›</label>'
             '<font>font_main</font><textcolor>FF4FA8FF</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>right</align><aligny>center</aligny>'
             '<texturefocus /><texturenofocus /><onright>%d</onright><visible>%s</visible></control>') % (SCOPE, W - 560, 420, HEAD, P('scope'), CLOSE, MAIN) +
            ('<control type="button" id="%d"><left>12</left><top>0</top><width>%d</width><height>%d</height><label>‹ Picture</label>'
             '<font>font_head_bold</font><textcolor>FF4FA8FF</textcolor><focusedcolor>FF64D2FF</focusedcolor><textoffsetx>24</textoffsetx>'
             '<align>left</align><aligny>center</aligny><texturefocus /><texturenofocus /><ondown>%d</ondown><visible>!%s</visible></control>') % (
                BACK_LINK, W - 170, HEAD, LIST, MAIN) +
            _img(W - 97, 16, 75, 75, MEDIA + 'close_disc.png', '2EFFFFFF') +
            _img(W - 97, 16, 75, 75, MEDIA + 'close_disc.png', '24FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % CLOSE) +
            _img(W - 74, 39, 29, 29, MEDIA + 'close_cross.png', 'B3EBEBF5') +
            _btn(CLOSE, W - 118, -5, 118, 118))
    sections = ('<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>1200</height><orientation>vertical</orientation>'
                '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>%s%s%s%s</control>') % (
        HEAD, W, _upscale(), _tv(), _note(), _saturation())
    inner = ('<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'
             '<animation effect="slide" start="0,-24" end="0,0" time="220" tween="cubic" easing="out">WindowOpen</animation>' +
             _backgrounds() + head + sections + _apply_page())
    body = ('<control type="button" id="9099"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texturefocus /><texturenofocus />'
            '<onclick>Close</onclick><onfocus>SetFocus(%d)</onfocus></control>' % CLOSE +
            # Under the Picture button: the fifth icon from the right (player_osd), 140 in from the edge (SAFE).
            '<control type="group"><right>%d</right><top>172</top><width>%d</width>%s</control>' % (140 + 4 * 180 - 300, W, inner))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: picture menu r1 (navigation.patch_skin leaves this marker alone) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>\n') % (CLOSE, body)
