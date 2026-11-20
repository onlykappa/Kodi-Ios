"""Sports landing page (DEC-054, DEC-057; approved board 2 of docs/design/sports-approved-pages.html, option A).

Draws IOSSports.xml: back, Edit and refresh (top right), the large title "Sports" with "Updated just now", then (owner's mockup A1, 2026-11-19)
a compact Live Now card, "Up next" (the next four games, the Upcoming page's own rows, with See all; owner 2026-11-20: four keep the two tiles on screen) and the Upcoming and Leagues gradient tiles.
sports.py fills it from sports_model / sports_provider and sets every property below. Kodi skin XML, portrait units
(2.687 per pt); existing tokens and helpers only. The tile colours are the board's: red live, blue later, purple leagues, grey idle.
"""
import status_ui as u
import sports_edit_button as edit_button
import sports_upcoming_page as upcoming_page

WINDOW = 'IOSSports.xml'
BACK, REFRESH, LIVE, UPCOMING, LEAGUES, FINISHED, RETRY = 9001, 9002, 9101, 9102, 9103, 9104, 9105
SEE_ALL, LIST, NEXT, NEXT_ROWS = 9106, 9300, 9120, 12     # See all, the scrolling list, the twelve Up next rows' ids (today's games only) (NEXT + 4 * row + form - 1)
TOP = 370                       # the list starts 14 pt under the subtitle
TILE_H = 150                    # 56 pt: a slim tile, title and one line (owner-approved mockup docs/design/sports-home-tiles.html, 2026-11-20: the 115 pt tiles were bulky)
LIVE_H = 269                    # 100 pt: the Live Now card, still the biggest block on the page (was 117 pt)
GAP = 32                        # 12 pt
PAD = 43                        # 16 pt inside a tile
LINE = 52                       # one line of 15 pt detail text
FINISHED_H = 150                # 56 pt
# Characters per detail line, kept under what the tile's width holds in Inter at 15 pt (DEC-050: text wraps, it is never cut off).
FIT_BIG, FIT_HALF = 36, 18

# (name, top colour, bottom colour) of each tile's gradient, from the board's CSS (150 deg: mostly top to bottom)
TILES = {'live': ((196, 48, 43), (74, 14, 18)), 'idle': ((58, 58, 60), (28, 28, 30)),
         'up': ((47, 111, 224), (14, 37, 99)), 'lg': ((142, 91, 232), (42, 23, 102))}
BIG, HALF = (972, LIVE_H), (470, TILE_H)   # drawn at their own size, so the 54-unit corners stay round (a stretched texture made them oval)


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
        out['sports_%s.png' % name] = _tile(p, size[0], size[1], top, bottom, 54)
    out['sports_big_mask.png'] = p.rounded(BIG[0], BIG[1], 54)
    out['sports_half_mask.png'] = p.rounded(HALF[0], HALF[1], 54)
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
    """The tile's title (17 pt bold) over one detail line (13 pt), left-aligned, with a chevron at the right."""
    P = u.P
    out = u.text(p, PAD, 26, w - 2 * PAD - 50, 58, P(key + '.title'), 'p_h3')
    out += u.text(p, PAD, 86, w - 2 * PAD - 50, 44, P(key + '.d1'), 'p_foot', 'EBFFFFFF')
    out += u.glyph(p, w - PAD - 8, h // 2, 36, 'chevron-right.png', 'EBFFFFFF')
    return out


def _tile_xml(p, ident, key, x, w, texture, mask):
    """One short gradient tile (title and one or two lines, bottom-anchored) with a button over all of it."""
    out = p.image(0, 0, w, TILE_H, p.MEDIA + 'sports_%s.png' % texture, p.WHITE, aspect='>stretch')
    out += _text_block(p, w, TILE_H, key, False)
    out += ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
            '<texturefocus colordiffuse="30FFFFFF" border="%d">%s%s</texturefocus><texturenofocus /></control>' % (ident, w, TILE_H, 54 if texture in ('up', 'lg') else 27, p.MEDIA, mask))
    return '<control type="group"><left>%d</left><top>0</top><width>%d</width><height>%d</height>%s</control>' % (x, w, TILE_H, out)


def _live_card(p, w):
    """Nothing live: a grey card with the next game. Live: the red gradient with the "4 live" capsule."""
    S = p.SIDE
    out = p.image(S, 0, w, LIVE_H, p.MEDIA + 'row_only.png', p.SURFACE, '<visible>String.IsEqual(Window().Property(live.mode),idle)</visible>', border=43)
    out += p.image(S, 0, w, LIVE_H, p.MEDIA + 'sports_live.png', p.WHITE, '<visible>String.IsEqual(Window().Property(live.mode),live)</visible>', '>stretch')
    out += u.text(p, S + PAD, 30, 500, 48, 'LIVE NOW', 'p_foot_b', p.GREY)
    out += u.text(p, S + PAD, 86, w - 2 * PAD, 62, u.P('live.title'), 'p_h3')
    out += p.textbox(S + PAD, 156, w - 2 * PAD, 76, u.P('live.detail'), 'p_foot', 'EBFFFFFF')
    out += ('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
            '<texturefocus colordiffuse="30FFFFFF" border="43">%srow_only.png</texturefocus><texturenofocus /></control>' % (LIVE, S, w, LIVE_H, p.MEDIA))
    return out


def _badge(p):
    """The white "● 4 live" capsule at the top right of Live Now."""
    w = p.WIDTH - 2 * p.SIDE
    x = p.SIDE + w - PAD - 250
    body = p.image(0, 0, 250, 72, p.MEDIA + 'pill_72.png', p.WHITE, border=36)
    body += p.image(26, 25, 22, 22, p.MEDIA + 'dot.png', 'FFFF453A')
    body += u.text(p, 62, 0, 170, 72, u.P('live.badge'), 'p_foot_b', 'FF8E1B16')
    return '<control type="group"><left>%d</left><top>%d</top><width>250</width><height>72</height><visible>%s</visible>%s</control>' % (
        x, 22, u.has('live.badge'), body)


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
    # Everything under the title scrolls as one list: the live card, the two tiles, Up next.
    items = u.group(p, LIVE_H + GAP, _live_card(p, w) + _badge(p))
    # The Upcoming and Leagues tiles sit right under Live now so they are never cut off by the floating tab bar (owner, 2026-11-20); the four games scroll below them.
    tiles = _tile_xml(p, UPCOMING, 'up', S, half, 'up', 'sports_half_mask.png') + _tile_xml(p, LEAGUES, 'lg', S + half + GAP, half, 'lg', 'sports_half_mask.png')
    items += u.group(p, TILE_H + 8, tiles)
    see_all = ('<control type="button" id="%d"><left>%d</left><top>0</top><width>260</width><height>118</height><label>See all</label><font>p_sub</font>'
               '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny><textoffsetx>0</textoffsetx><scroll>false</scroll>'
               '<texturefocus /><texturenofocus /></control>' % (SEE_ALL, W - S - 260, p.GREY, p.GREY))
    items += u.group(p, 118, u.text(p, S + 10, 24, 600, 70, 'Up next', 'p_h2') + see_all, u.has('next.0.lines') + ' | ' + u.has('next.empty'))
    for n in range(NEXT_ROWS):
        key = 'next.%d.' % n
        for lines in upcoming_page.FORMS:
            items += u.group(p, upcoming_page.row_height(lines), upcoming_page.game_row(p, key, NEXT + 4 * n + lines - 1, lines, w),
                             'String.IsEqual(Window().Property(%slines),%d)' % (key, lines))
    empty = p.image(S, 0, w, 150, p.MEDIA + 'row_only.png', p.SURFACE, border=43) + u.text(p, S + PAD, 0, w - 2 * PAD, 150, u.P('next.empty'), 'p_sub', p.GREY, 'center')
    items += u.group(p, 150 + GAP, empty, u.has('next.empty'))   # nothing left today: one grey line, See all still opens the full list
    items += u.group(p, 320, '')   # the last row scrolls fully above the floating tab bar (portrait.TAB_CLEAR)
    tiles = ('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible><scrolltime tween="cubic" easing="out">220</scrolltime>%s</control>'
             % (LIST, TOP, W, ok, items))
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
