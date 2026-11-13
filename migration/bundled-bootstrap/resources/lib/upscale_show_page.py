"""Settings › AI Upscale › one show (V3, DEC-042, docs/design/ai-upscale-settings-mockups.html board C).

Draws IOSUpscaleShow.xml: back, the show's title and one grey line; "Upscale this show" with a segmented choice (Off,
then only the sizes above its videos, the Picture menu's slider); its episodes with a chip each (Ready, Making,
Waiting, Off); a white capsule to make the rest; a red "Remove the copies…" that asks first. upscale_settings.py fills
it from upscale_page.show_view. Kodi skin XML, portrait units; existing helpers and tokens only.
"""
WINDOW = 'IOSUpscaleShow.xml'
BACK, PRIMARY, REMOVE = 9001, 9010, 9012
SEG, SEGS = 9110, 6
ROW, SLOTS, ROW_H = 9200, 60, 170
LIST = 9300
TONES = (('green', 'FF30D158'), ('blue', 'FF0A84FF'), ('grey', 'FF8E8E93'))


def _segments(p, u):
    """The size choice: one capsule per size; the chosen one is tinted blue by the script (seg.N.tint)."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = ('<control type="grouplist"><left>%d</left><top>140</top><width>%d</width><height>118</height>'
           '<orientation>horizontal</orientation><itemgap>16</itemgap><usecontrolcoords>true</usecontrolcoords>' % (S + 32, w - 64))
    for n in range(SEGS):
        k = 'seg.%d' % n
        out += ('<control type="button" id="%d"><width min="150" max="320">auto</width><height>118</height><label>%s</label>'
                '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><textoffsetx>38</textoffsetx>'
                '<align>center</align><aligny>center</aligny>'
                '<texturenofocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturenofocus>'
                '<texturefocus border="27" colordiffuse="$INFO[Window().Property(%s.tint)]">%sr27.png</texturefocus>'
                '<visible>!String.IsEmpty(Window().Property(%s))</visible></control>') % (
            SEG + n, u.P(k), p.WHITE, p.WHITE, k, p.MEDIA, k, p.MEDIA, k)
    return out + '</control>'


def _chip(p, u, k, right):
    """One state pill at the row's right end, sized to its word."""
    out = ''
    for name, tint in TONES:
        out += ('<control type="grouplist"><left>%d</left><top>54</top><width>260</width><height>62</height>'
                '<orientation>horizontal</orientation><align>right</align><usecontrolcoords>true</usecontrolcoords>'
                '<visible>String.IsEqual(Window().Property(%stone),%s)</visible>'
                '<control type="button"><width min="80" max="260">auto</width><height>62</height><label>%s</label>'
                '<font>p_foot_b</font><textcolor>%s</textcolor><disabledcolor>%s</disabledcolor><textoffsetx>22</textoffsetx>'
                '<aligny>center</aligny><enable>false</enable>'
                '<texturenofocus border="21" colordiffuse="2E%s">%sr21.png</texturenofocus>'
                '<texturefocus border="21" colordiffuse="2E%s">%sr21.png</texturefocus></control></control>') % (
            right - 260, k, name, u.P(k + 'chip'), tint, tint, tint[2:], p.MEDIA, tint[2:], p.MEDIA)
    return out


def _rows(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = ''
    for n in range(SLOTS):
        k = 'ep.%d.' % n
        b = u.row_back(p, k, w, ROW_H)
        b += u.text(p, S + 38, 26, w - 76 - 290, 60, u.P(k + 'title'), 'p_body')
        b += u.text(p, S + 38, 88, w - 76 - 290, 50, u.P(k + 'line'), 'p_foot', p.GREY)
        b += _chip(p, u, k, S + w - 38)
        out += u.group(p, ROW_H, b, u.has(k + 'title'))
    return out


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'Close')])
    body += u.text(p, S, 150, w, 110, P('title'), 'p_large') + u.text(p, S, 262, w, 56, P('sub'), 'p_sub', p.GREY)
    size_card = (u.card(p, S, 0, w, 298) + u.text(p, S + 38, 30, w - 300, 70, 'Upscale this %s' % '$INFO[Window().Property(what)]', 'p_body') +
                 u.text(p, S + w - 338, 30, 300, 70, P('chosen'), 'p_body', p.GREY, 'right') + _segments(p, u))
    primary = (u.tap(p, PRIMARY, S, 0, w, 134) + p.image(S, 0, w, 134, p.MEDIA + 'pill_134.png', 'FFFFFFFF', border=67) +
               u.text(p, S, 0, w, 134, P('primary'), 'p_btn', 'FF000000', 'center'))
    remove = ('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>118</height><label>%s</label>'
              '<font>p_btn</font><textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor><align>center</align>'
              '<aligny>center</aligny><texturefocus /><texturenofocus /></control>') % (REMOVE, S, w, P('remove'))
    listing = ('<control type="grouplist" id="%d"><top>350</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               u.group(p, 298 + 38, size_card) +
               u.group(p, 120, u.text(p, S, 0, w, 120, P('note'), 'p_foot', p.GREY), u.has('note')) +
               u.group(p, 134 + 38, primary, u.has('primary')) +
               u.section(p, P('episodes.title'), u.has('ep.0.title')) +
               _rows(p, u) +
               u.group(p, 160, remove, u.has('remove')) +
               u.group(p, 260, '') + '</control>')
    body += listing
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Settings > AI Upscale > one show (V3, DEC-042 board C), drawn by upscale_show_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, body))   # ISSUE-230: the segments show only once the page has filled them, so Kodi could not focus 9110 ("asked to focus, but it can't")


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
