"""Library file manager, step L2 (DEC-043, docs/design/library-files-mockups.html board A, round 3).

Draws IOSLibraryFiles.xml: back, large title, a TV Shows / Movies switch, the storage card, search and sort, then one
pooled row per show (or movie): poster, title, one grey line, up to three state chips and a chevron. library_manager.py
fills it from library_files.py. Kodi skin XML, portrait units (2.687 per pt); existing tokens and helpers only.
"""
WINDOW = 'IOSLibraryFiles.xml'
BACK, TAB_SHOWS, TAB_MOVIES, SEARCH, SORT, VIEW = 9001, 9101, 9102, 9103, 9104, 9105
STORE_BAR = 9120
ROW, SLOTS, ROW_H = 9200, 30, 236
LIST = 9300
CHIP_COLORS = (('green', 'FF30D158'), ('orange', 'FFFF9F0A'), ('blue', 'FF0A84FF'), ('red', 'FFFF453A'), ('purple', 'FFBF5AF2'))
CHIPS = 3
TOP = 300
# L7 (board E): the Movies side is a three-column poster grid; each poster has its size line and one state badge.
MOVIE, COLS, CELL_GAP = 9400, 3, 32
POSTER_H_OF_W = 1.5           # 2:3 posters


def _tab(p, u, ident, x, w, label, key):
    on = 'String.IsEqual(Window().Property(tab),%s)' % key
    return (p.image(x, 0, w, 96, p.MEDIA + 'r27.png', u.SEG_GREY, '<visible>%s</visible>' % on, border=27) +
            '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>118</height><label>%s</label>'
            '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturefocus /><texturenofocus /><textoffsety>-11</textoffsety></control>' % (ident, x, w, p.e(label), p.WHITE, p.WHITE))


def _chips(p, u, k, x, y):
    """Up to three pills, each sized to its words: a horizontal grouplist of auto-width buttons, one per colour, of which
    only the one named by the row's chipNc property shows."""
    out = ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>62</height>'
           '<orientation>horizontal</orientation><itemgap>16</itemgap><usecontrolcoords>true</usecontrolcoords>' % (x, y, p.WIDTH - x - 150))
    for c in range(CHIPS):
        for name, tint in CHIP_COLORS:
            cond = 'String.IsEqual(Window().Property(%schip%dc),%s)' % (k, c, name)
            out += ('<control type="button"><width min="80" max="420">auto</width><height>62</height><label>%s</label>'
                    '<font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><textoffsetx>22</textoffsetx>'
                    '<aligny>center</aligny><texturenofocus border="21" colordiffuse="2E%s">%sr21.png</texturenofocus>'
                    '<texturefocus border="21" colordiffuse="2E%s">%sr21.png</texturefocus><enable>false</enable>'
                    '<disabledcolor>%s</disabledcolor><visible>%s</visible></control>') % (
                u.P('%schip%d' % (k, c)), tint, tint, tint[2:], p.MEDIA, tint[2:], p.MEDIA, tint, cond)
    return out + '</control>'


def _rows(p, u):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = ''
    for n in range(SLOTS):
        k = 'row.%d.' % n
        b = u.row_back(p, k, w, ROW_H) + u.tap(p, ROW + n, S, 0, w, ROW_H)
        b += p.image(S + 32, 28, 120, 180, u.P(k + 'art'), 'FFFFFFFF', aspect='>scale', diffuse=p.MEDIA + 'poster16.png')
        b += p.image(S + 32, 28, 120, 180, p.MEDIA + 'poster16.png', '1FEBEBF5', '<visible>String.IsEmpty(Window().Property(%sart))</visible>' % k)
        b += u.text(p, S + 184, 26, w - 184 - 100, 56, u.P(k + 'title'), 'p_body')
        b += u.text(p, S + 184, 84, w - 184 - 100, 46, u.P(k + 'sub'), 'p_foot', p.GREY)
        b += _chips(p, u, k, S + 184, 146)
        b += u.glyph(p, S + w - 70, ROW_H // 2 - 18, 36, 'chevron-right.png', p.DIM)
        out += u.group(p, ROW_H, b, u.has(k + 'title'))
    return out


def _badge(p, u, k, x, y, w):
    """Board E: one small state pill on the poster (Ready, AI 4K, 42 %, Problem), coloured by its state."""
    out = ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>62</height>'
           '<orientation>horizontal</orientation><usecontrolcoords>true</usecontrolcoords>' % (x, y, w))
    for name, tint in CHIP_COLORS:
        out += ('<control type="button"><width min="80" max="%d">auto</width><height>62</height><label>%s</label>'
                '<font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><textoffsetx>20</textoffsetx>'
                '<aligny>center</aligny><texturenofocus border="21" colordiffuse="E61C1C1E">%sr21.png</texturenofocus>'
                '<texturefocus border="21" colordiffuse="E61C1C1E">%sr21.png</texturefocus><enable>false</enable>'
                '<disabledcolor>%s</disabledcolor><visible>String.IsEqual(Window().Property(%sbadgec),%s)</visible></control>') % (
            w, u.P(k + 'badge'), tint, tint, p.MEDIA, p.MEDIA, tint, k, name)
    return out + '</control>'


def cell_size(p):
    w = p.WIDTH - 2 * p.SIDE
    cw = (w - (COLS - 1) * CELL_GAP) // COLS
    return cw, int(cw * POSTER_H_OF_W)


def _grid(p, u):
    """Board E: SLOTS posters in rows of three (pooled cells, filled as mov.N.*); each tap opens board C."""
    S = p.SIDE
    cw, ph = cell_size(p)
    cell_h = ph + 150
    out = ''
    for r in range((SLOTS + COLS - 1) // COLS):
        b = ''
        for c in range(COLS):
            n = r * COLS + c
            if n >= SLOTS:
                break
            k, x = 'mov.%d.' % n, S + c * (cw + CELL_GAP)
            one = (p.image(x, 0, cw, ph, p.MEDIA + 'poster16.png', 'FF2C2C2E') +
                   p.image(x, 0, cw, ph, u.P(k + 'art'), 'FFFFFFFF', aspect='>scale', diffuse=p.MEDIA + 'poster16.png') +
                   u.tap(p, MOVIE + n, x, 0, cw, cell_h) +
                   _badge(p, u, k, x + 16, 16, cw - 32) +
                   u.text(p, x, ph + 18, cw, 54, u.P(k + 'title'), 'p_foot_b') +
                   u.text(p, x, ph + 72, cw, 46, u.P(k + 'sub'), 'p_foot', p.GREY))
            b += '<control type="group"><visible>%s</visible>%s</control>' % (u.has(k + 'title'), one)
        out += u.group(p, cell_h + 38, b, u.has('mov.%d.title' % (r * COLS)))
    return out


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', [('true', 'Close')])
    body += u.text(p, S, 150, w - 160, 110, P('title'), 'p_large')
    # Owner (L7 review): "i like the list version … make it so i can change the view at anytime". On the Movies side a
    # button beside the title switches list / grid (the glyph shows the view it switches to); the choice is kept.
    movies = 'String.IsEqual(Window().Property(tab),movie)'
    body += p.nav_button(VIEW, W - S - 108, 152, 'grid.png', [('true', 'noop')],
                         visible=movies + ' + !String.IsEqual(Window().Property(view),grid)')
    body += p.nav_button(VIEW + 1, W - S - 108, 152, 'list.png', [('true', 'noop')],
                         visible=movies + ' + String.IsEqual(Window().Property(view),grid)')
    # Board A: the switch.
    switch = (u.card(p, 0, 0, w, 96, u.SURF2) + _tab(p, u, TAB_SHOWS, 6, w // 2 - 12, 'TV Shows', 'tv') +
              _tab(p, u, TAB_MOVIES, w // 2 + 6, w // 2 - 12, 'Movies', 'movie'))
    body += '<control type="group"><left>%d</left><top>%d</top>%s</control>' % (S, 300, switch)
    # The storage card: the line, one bar (library of quota, or shows/movies/AI split by the script), the legend.
    store = (u.card(p, S, 0, w, 236) + u.text(p, S + 38, 34, w - 76, 56, P('store.line'), 'p_body') +
             u.id_bar(p, STORE_BAR, S + 38, 112, w - 76, 21, u.BLUE, texture='pill21.png', border=10) +
             u.text(p, S + 38, 158, w - 76, 46, P('store.legend'), 'p_foot', p.GREY))
    # Search (a tap opens the keyboard) and sort (Recent / Name / Size).
    search = (u.card(p, S, 0, w - 330, 118, u.SURF2) + u.glyph(p, S + 40, 41, 36, 'magnifying-glass.png', p.GREY) +
              u.group(p, 118, u.text(p, S + 100, 0, w - 460, 118, P('search'), 'p_sub'), u.has('search')) +
              u.group(p, 118, u.text(p, S + 100, 0, w - 460, 118, 'Search downloads', 'p_sub', p.GREY), u.neg(u.has('search'))) +
              u.tap(p, SEARCH, S, 0, w - 330, 118) +
              u.link(p, SORT, S + w - 300, 0, 250, 118, P('sort.label')) +
              p.image(S + w - 40, 41, 36, 36, p.ICONS + 'chevron-down.png', p.ACCENT))   # the font has no \u25be
    listing = ('<control type="grouplist" id="%d"><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, 450, W) +
               u.group(p, 236 + 38, store, u.has('store.line')) + u.group(p, 118 + 38, search) +
               _rows(p, u) + _grid(p, u) +
               u.group(p, 160, u.text(p, S, 30, w, 100, P('empty'), 'p_foot', p.GREY), u.has('empty')) +
               u.group(p, 260, '') + '</control>')
    body += listing
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board A (DEC-043), drawn by library_files_page.py -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (TAB_SHOWS, body))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
