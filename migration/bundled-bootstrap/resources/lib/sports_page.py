"""Sports landing page (DEC-054, DEC-057; approved board 2 of docs/design/sports-approved-pages.html, option A).

Draws IOSSports.xml: back, refresh (top right), the large title "Sports" with "Updated just now", then three gradient tiles
(Live Now the big one, Upcoming and Leagues side by side, the Search category tiles' style) and one slim "Finished today" row.
sports.py fills it from sports_model / sports_provider and sets every property below. Kodi skin XML, portrait units
(2.687 per pt); existing tokens and helpers only. The tile colours are the board's: red live, blue later, purple leagues, grey idle.
"""
import status_ui as u
import sports_edit_button as edit_button

WINDOW = 'IOSSports.xml'
BACK, REFRESH, LIVE, UPCOMING, LEAGUES, FINISHED, RETRY = 9001, 9002, 9101, 9102, 9103, 9104, 9105
TOP = 370                       # the tiles start 14 pt under the subtitle
TILE_H = 527                    # 196 pt
GAP = 32                        # 12 pt
PAD = 43                        # 16 pt inside a tile
LINE = 52                       # one line of 15 pt detail text
FINISHED_H = 150                # 56 pt
# Characters per detail line, kept under what the tile's width holds in Inter at 15 pt (DEC-050: text wraps, it is never cut off).
FIT_BIG, FIT_HALF = 36, 16

# (name, top colour, bottom colour) of each tile's gradient, from the board's CSS (150 deg: mostly top to bottom)
TILES = {'live': ((196, 48, 43), (74, 14, 18)), 'idle': ((58, 58, 60), (28, 28, 30)),
         'up': ((47, 111, 224), (14, 37, 99)), 'lg': ((142, 91, 232), (42, 23, 102))}
BIG, HALF = (486, 264), (235, 264)   # texture sizes: half the tile's units, so the 27-unit corners stretch to the board's 54


def _tile(p, w, h, top, bottom, radius):
    def pixel(x, y):
        t = min(1, max(0, (y / h) * 0.75 + (x / w) * 0.25))
        rgb = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        return rgb + (int(255 * p.coverage(x, y, w, h, radius)),)
    return p.png(w, h, pixel)


def textures(p):
    out = {}
    for name, (top, bottom) in TILES.items():
        size = BIG if name in ('live', 'idle') else HALF
        out['sports_%s.png' % name] = _tile(p, size[0], size[1], top, bottom, 27)
    out['sports_big_mask.png'] = p.rounded(BIG[0], BIG[1], 27)
    out['sports_half_mask.png'] = p.rounded(HALF[0], HALF[1], 27)
    return out


def split_lines(text, limit):
    """The text as at most two lines of up to `limit` characters, broken at spaces (the page cannot measure text, so it wraps it)."""
    if '\n' in str(text or ''):   # a break the caller chose
        return [line.strip() for line in str(text).split('\n')][:2]
    words, lines = str(text or '').split(), []
    for word in words:
        if lines and len(lines[-1]) + 1 + len(word) <= limit:
            lines[-1] += ' ' + word
        else:
            lines.append(word)
    if len(lines) > 2:
        lines = [lines[0], ' '.join(lines[1:])]
    return lines


def _text_block(p, w, h, key, big):
    """The tile's title and detail lines, bottom-anchored: one variant for a one-line detail, one for two lines."""
    P = u.P
    out = ''
    for n in (1, 2):
        cond = 'String.IsEqual(Window().Property(%s.lines),%d)' % (key, n)
        y2 = h - PAD - LINE
        y1 = y2 - LINE if n == 2 else y2
        body = u.text(p, PAD, y1 - 78, w - 2 * PAD, 80, P(key + '.title'), 'p_h2')
        if n == 2:
            body += u.text(p, PAD, y1, w - 2 * PAD, LINE, P(key + '.d1'), 'p_sub', 'EBFFFFFF')
            body += u.text(p, PAD, y2, w - 2 * PAD, LINE, P(key + '.d2'), 'p_sub', 'EBFFFFFF')
        else:
            body += u.text(p, PAD, y2, w - 2 * PAD, LINE, P(key + '.d1'), 'p_sub', 'EBFFFFFF')
        out += '<control type="group"><visible>%s</visible>%s</control>' % (cond, body)
    return out


def _tile_xml(p, ident, key, x, y, w, texture_for, glyph, big, mask):
    """One tile: gradient, a translucent circle with its glyph, the text, and a button over all of it."""
    P = u.P
    out = ''
    for name, cond in texture_for:
        out += p.image(0, 0, w, TILE_H, p.MEDIA + 'sports_%s.png' % name, p.WHITE, '<visible>%s</visible>' % cond, '>stretch')
    out += p.image(PAD, PAD, 124, 124, p.MEDIA + 'pill_124.png', '33FFFFFF')
    out += p.icon(PAD + 27, PAD + 27, 70, glyph, p.WHITE)
    out += _text_block(p, w, TILE_H, key, big)
    out += ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
            '<texturefocus colordiffuse="30FFFFFF" border="27">%s%s</texturefocus><texturenofocus /></control>' % (ident, w, TILE_H, p.MEDIA, mask))
    return '<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s</control>' % (x, y, w, TILE_H, out)


def _badge(p):
    """The white "● 4 live" capsule at the top right of Live Now."""
    w = p.WIDTH - 2 * p.SIDE
    x = w - PAD - 250
    body = p.image(0, 0, 250, 72, p.MEDIA + 'pill_72.png', p.WHITE, border=36)
    body += p.image(26, 25, 22, 22, p.MEDIA + 'dot.png', 'FFFF453A')
    body += u.text(p, 62, 0, 170, 72, u.P('live.badge'), 'p_foot_b', 'FF8E1B16')
    return '<control type="group"><left>%d</left><top>%d</top><width>250</width><height>72</height><visible>%s</visible>%s</control>' % (
        x, PAD + 6, u.has('live.badge'), body)


def page(p):
    S, W = p.SIDE, p.WIDTH
    w, half = W - 2 * S, (W - 2 * S - GAP) // 2
    P = u.P
    ok, bad = 'String.IsEqual(Window().Property(state),ok)', 'String.IsEqual(Window().Property(state),error)'
    head = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close')
    head += ('<control type="button" id="%d"><left>%d</left><top>40</top><width>%d</width><height>118</height><label></label>'
             '<texturefocus /><texturenofocus /><animation effect="fade" start="100" end="65" time="0" condition="Control.HasFocus(%d)">Conditional</animation></control>'
             % (REFRESH, W - S - 150, 150, REFRESH))
    head += p.icon(W - S - 84, 57, 84, 'arrows-rotate.png', p.ACCENT)
    head += edit_button.xml(p, W - S - 150 - 20 - edit_button.W, 52)
    head += u.text(p, S, 160, w, 110, 'Sports', 'p_large') + u.text(p, S, 268, w, 56, P('sub'), 'p_sub', p.GREY)
    live = _tile_xml(p, LIVE, 'live', 0, 0, w, (('live', 'String.IsEqual(Window().Property(live.mode),live)'),
                                              ('idle', 'String.IsEqual(Window().Property(live.mode),idle)')), 'tower-broadcast.png', True, 'sports_big_mask.png')
    live += _badge(p)
    up = _tile_xml(p, UPCOMING, 'up', 0, TILE_H + GAP, half, (('up', 'true'),), 'calendar-day.png', False, 'sports_half_mask.png')
    lg = _tile_xml(p, LEAGUES, 'lg', half + GAP, TILE_H + GAP, half, (('lg', 'true'),), 'medal.png', False, 'sports_half_mask.png')
    fin_y = 2 * TILE_H + 2 * GAP
    fin = u.card(p, 0, 0, w, FINISHED_H)
    fin += u.text(p, PAD + 6, 0, w - 420, FINISHED_H, 'Finished today', 'p_h3')
    fin += u.text(p, w - 420 - 90, 0, 420, FINISHED_H, P('fin'), 'p_sub', p.GREY, 'right')
    fin += p.icon(w - PAD - 30, (FINISHED_H - 32) // 2, 32, 'chevron-right.png', p.GREY)
    fin += ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
            '<texturefocus colordiffuse="22FFFFFF" border="43">%srow_only.png</texturefocus><texturenofocus /></control>' % (FINISHED, w, FINISHED_H, p.MEDIA))
    tiles = ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><visible>%s</visible>%s%s%s'
             '<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height><visible>%s</visible>%s</control></control>'
             % (S, TOP, w, ok, live, up, lg, fin_y, w, FINISHED_H, u.has('fin'), fin))
    # Can't load: plain words, one button; the details go to the log, never the screen (APPLE-UI-POLICY section 6).
    err = p.image((W - 161) // 2, 700, 161, 161, p.MEDIA + 'pill_150.png', '2EFF9F0A')
    err += p.icon((W - 80) // 2, 740, 80, 'triangle-exclamation.png', 'FFFF9F0A')
    err += u.text(p, S, 900, w, 80, P('err.title'), 'p_h3', p.WHITE, 'center')
    err += p.label(S + 60, 990, w - 120, 130, P('err.text'), 'p_sub', p.GREY, 'center', '<wrapmultiline>true</wrapmultiline><aligny>top</aligny><scroll>false</scroll>')
    err += p.pill_button(RETRY, (W - 340) // 2, 1150, 340, 134, P('err.button'), [('', 'noop')], 'primary')
    err = '<control type="group"><visible>%s</visible>%s</control>' % (bad, err)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports landing: approved board 2 (DEC-057) -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, head + tiles + err))


def files(p):
    out = {p.FOLDER + '/' + WINDOW: page(p).encode()}
    out.update({'extras/portrait/' + name: data for name, data in textures(p).items()})
    return out
