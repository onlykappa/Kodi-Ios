"""Settings › Favourites as its own manager (owner-approved boards K1-K8, docs/design/favourites-manager-mockups.html).

Two windows, both filled by favourites_manager.py:
  IOSFavManage.xml  one list page for K1-K5. Every part of a page is a row of one list (LIST, or LIST_SEG when the page has
                    a segmented control): section captions, grouped rows with an icon or a count, rows with a poster, a rank
                    and a chip, notes, a white button and a centred link. ListItem.Property(kind) picks the row's layout.
  IOSFavPick.xml    the poster picker for K7 (Needs your answer) and K8 (Not found): posters three to a row, each with its
                    name and what it is (kind · year · seasons), the most likely one marked; a search field (K8) and
                    Search Another Name / Skip This One under the grid.
Sizes follow APPLE-UI-POLICY (2.687 units per pt, every control at least 118 units); nothing is cut off (DEC-050): titles
and lines wrap in textboxes sized for two lines."""
MANAGE = 'IOSFavManage.xml'
PICK = 'IOSFavPick.xml'
BACK = 9001
LIST, LIST_SEG = 9500, 9501
SEG = 9021                 # segments 9021-9023
GRID = 9600
SEARCH, OTHER, SKIP = 9030, 9031, 9032
TOP, TOP_SEG = 330, 446    # where the list starts without and with the segmented control
ROW, ROW2, POSTER_ROW = 150, 196, 236
HEADER, NOTE, BUTTON, LINK, GAP, STATS = 84, 140, 170, 130, 30, 220
CELL_W, CELL_H = 324, 660


def _kind(name):
    return 'String.IsEqual(ListItem.Property(kind),%s)' % name


def _has(prop):
    return '!String.IsEmpty(ListItem.Property(%s))' % prop


def _not(prop):
    return 'String.IsEmpty(ListItem.Property(%s))' % prop


def _row_back(p, w, h):
    """A row inside one grouped card: rounded ends only for the first/last row (ListItem.Property(pos)), a hairline above
    every row but the first (status_ui.row_back, for list items)."""
    S, M = p.SIDE, p.MEDIA
    out = ''.join(p.image(S, 0, w, h, M + tex, p.SURFACE, '<visible>String.IsEqual(ListItem.Property(pos),%s)</visible>' % pos,
                          border=43 if pos != 'mid' else '')
                  for pos, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('mid', 'white.png'), ('last', 'row_last.png')))
    return out + p.image(S + 30, 0, w - 30, 3, M + 'white.png', '1FEBEBF5',
                         '<visible>String.IsEqual(ListItem.Property(pos),mid) | String.IsEqual(ListItem.Property(pos),last)</visible>')


def _press(p, w, h, focused):
    return p.image(p.SIDE, 0, w, h, p.MEDIA + 'white.png', '14FFFFFF') if focused else ''


def _right(p, w, h):
    """What a row shows at its right edge: a count (orange when it needs you), a value, an action pill, a chip, a chevron."""
    S, M = p.SIDE, p.MEDIA
    x = S + w - 70
    out = p.icon(x, (h - 40) // 2, 40, 'chevron-right.png', p.GREY, '<visible>%s</visible>' % _has('go'))
    cnt = (h - 62) // 2
    out += p.image(x - 130, cnt, 112, 62, M + 'pill_150.png', '33FF9F0A', '<visible>%s + String.IsEqual(ListItem.Property(count_kind),o)</visible>' % _has('count'), border=31)
    out += p.image(x - 130, cnt, 112, 62, M + 'pill_150.png', '1FEBEBF5', '<visible>%s + !String.IsEqual(ListItem.Property(count_kind),o)</visible>' % _has('count'), border=31)
    out += p.label(x - 130, cnt, 112, 62, '[B]$INFO[ListItem.Property(count)][/B]', 'p_foot', 'FFFF9F0A', 'center',
                   '<scroll>false</scroll><visible>String.IsEqual(ListItem.Property(count_kind),o)</visible>')
    out += p.label(x - 130, cnt, 112, 62, '[B]$INFO[ListItem.Property(count)][/B]', 'p_foot', p.GREY, 'center',
                   '<scroll>false</scroll><visible>%s + !String.IsEqual(ListItem.Property(count_kind),o)</visible>' % _has('count'))
    out += p.label(x - 330, 0, 310, h, '$INFO[ListItem.Property(value)]', 'p_sub', p.GREY, 'right', '<scroll>false</scroll>')
    act = (h - 76) // 2
    out += p.image(S + w - 250, act, 220, 76, M + 'pill_150.png', p.SURFACE2, '<visible>%s</visible>' % _has('act'), border=38)
    out += p.label(S + w - 250, act, 220, 76, '[B]$INFO[ListItem.Property(act)][/B]', 'p_foot', p.ACCENT, 'center', '<scroll>false</scroll>')
    out += p.image(S + w - 250, act + 8, 220, 60, M + 'pill_150.png', '$INFO[ListItem.Property(chip_back)]', '<visible>%s</visible>' % _has('chip'), border=30)
    out += p.label(S + w - 250, act + 8, 220, 60, '[B]$INFO[ListItem.Property(chip)][/B]', 'p_cap', '$INFO[ListItem.Property(chip_tint)]', 'center', '<scroll>false</scroll>')
    return out


def _row(p, w, h, focused):
    """A grouped row: an icon tile (Property(glyph) on Property(tint)) or none, the title (Property(ltint) colours it) and
    its line under it (two lines in the taller ROW2), and the right edge."""
    S, M = p.SIDE, p.MEDIA
    lines = 2 if h == ROW2 else 1
    out = _row_back(p, w, h) + _press(p, w, h, focused)
    tile = (h - 84) // 2
    out += p.image(S + 30, tile, 84, 84, M + 'round_s.png', '$INFO[ListItem.Property(tint)]', '<visible>%s</visible>' % _has('glyph'), border=24)
    out += p.image(S + 50, tile + 20, 44, 44, '$INFO[ListItem.Property(glyph)]', p.WHITE, '<visible>%s</visible>' % _has('glyph'), '>keep')
    text_w = w - 30 - 330
    for with_tile, x in (('glyph', S + 140), ('', S + 30)):
        cond = _has('glyph') if with_tile else _not('glyph')
        out += ('<control type="group"><visible>%s</visible>' % cond +
                p.label(x, 18, text_w - (110 if with_tile else 0), 60, '[B]$INFO[ListItem.Label][/B]', 'p_pill',
                        '$INFO[ListItem.Property(ltint)]', 'left', '<scroll>false</scroll>') +
                p.textbox(x, 80, text_w - (110 if with_tile else 0), 46 * lines, '$INFO[ListItem.Label2]', 'p_foot', p.GREY) +
                '</control>')
    return out + _right(p, w, h)


def _poster_row(p, w, focused):
    """A title with its rank, poster, name, line and an orange/grey third line, and a chip or an action at the right."""
    S, h = p.SIDE, POSTER_ROW
    out = _row_back(p, w, h) + _press(p, w, h, focused)
    out += p.label(S + 10, 0, 70, h, '[B]$INFO[ListItem.Property(rank)][/B]', 'p_cap', p.GREY, 'right', '<scroll>false</scroll>')
    out += p.image(S + 96, 34, 112, 168, p.MEDIA + 'white.png', p.SURFACE2, '<visible>%s</visible>' % _has('poster_box'))
    out += p.image(S + 96, 34, 112, 168, '$INFO[ListItem.Art(thumb)]', p.WHITE, '<visible>%s</visible>' % _has('poster_box'), '>scale',
                   p.MEDIA + 'poster_mask.png', background=True)
    tw = w - 230 - 280
    out += p.textbox(S + 230, 30, tw, 96, '[B]$INFO[ListItem.Label][/B]', 'p_foot_b', p.WHITE)
    out += p.textbox(S + 230, 126, tw, 42, '$INFO[ListItem.Label2]', 'p_cap', p.GREY)
    out += p.textbox(S + 230, 168, tw, 42, '$INFO[ListItem.Property(em)]', 'p_cap', 'FFFF9F0A')
    return out + _right(p, w, h)


def _stats(p, w):
    """Up to four numbers with their names (K1: Favourites, Movies, Shows, Need a look; K5: Names, Added, Need a look)."""
    S, M = p.SIDE, p.MEDIA
    out = p.image(S, 0, w, STATS - 30, M + 'row_only.png', p.SURFACE, border=43)
    for count in (3, 4):
        tile = (w - 40 - (count - 1) * 20) // count
        group = ''
        for n in range(1, count + 1):
            x = S + 20 + (n - 1) * (tile + 20)
            group += p.image(x, 20, tile, STATS - 70, M + 'round_s.png', p.SURFACE2, border=24)
            group += p.label(x + 24, 34, tile - 40, 64, '[B]$INFO[ListItem.Property(s%dn)][/B]' % n, 'p_h3', '$INFO[ListItem.Property(s%dt)]', 'left', '<scroll>false</scroll>')
            group += p.textbox(x + 24, 100, tile - 36, 80, '$INFO[ListItem.Property(s%dl)]' % n, 'p_cap', p.GREY)
        out += '<control type="group"><visible>String.IsEqual(ListItem.Property(tiles),%d)</visible>%s</control>' % (count, group)
    return out


def _layouts(p, focused):
    S, W, M = p.SIDE, p.WIDTH, p.MEDIA
    w = W - 2 * S
    tag = 'focusedlayout' if focused else 'itemlayout'
    parts = [
        ('header', HEADER, p.label(S + 30, 22, w - 60, 56, '$INFO[ListItem.Label]', 'p_foot_b', p.GREY, 'left', '<scroll>false</scroll>')),
        ('row', ROW, _row(p, w, ROW, focused)),
        ('row2', ROW2, _row(p, w, ROW2, focused)),
        ('poster', POSTER_ROW, _poster_row(p, w, focused)),
        ('stats', STATS, _stats(p, w)),
        ('note', NOTE, p.textbox(S + 20, 10, w - 40, NOTE - 20, '$INFO[ListItem.Label]', 'p_cap', p.GREY)),
        ('button', BUTTON, p.image(S, 20, w, 128, M + 'pill_150.png', p.WHITE, border=64) +
         (p.image(S, 20, w, 128, M + 'pill_150.png', '33000000', border=64) if focused else '') +
         p.label(S, 20, w, 128, '[B]$INFO[ListItem.Label][/B]', 'p_btn', 'FF000000', 'center', '<scroll>false</scroll>')),
        ('link', LINK, p.label(S, 0, w, LINK, '[B]$INFO[ListItem.Label][/B]', 'p_body', '$INFO[ListItem.Property(ltint)]', 'center', '<scroll>false</scroll>') +
         (p.image(S, 6, w, LINK - 12, M + 'pill_150.png', '14FFFFFF', border=59) if focused else '')),
        ('gap', GAP, ''),
    ]
    return ''.join('<%s height="%d" condition="%s">%s</%s>' % (tag, h, _kind(k), body, tag) for k, h, body in parts)


def _list(p, ident, top, visible):
    return ('<control type="list" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom>'
            '<visible>%s</visible><orientation>vertical</orientation><onup>%d</onup>'
            '<scrolltime tween="cubic" easing="out">200</scrolltime>%s%s</control>') % (
        ident, top, p.WIDTH, visible, BACK, _layouts(p, False), _layouts(p, True))


def manage(p):
    """IOSFavManage.xml: the header, an optional segmented control (Window().Property(seg.count) 2 or 3), and the list."""
    import status_ui as u
    S, W, M, P = p.SIDE, p.WIDTH, p.MEDIA, u.P
    w = W - 2 * S
    seg_on = '!String.IsEmpty(Window().Property(seg.count))'
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close')
    body += p.label(S + 120, 36, w - 120, 108, P('back'), 'p_sub', p.ACCENT, 'left', '<scroll>false</scroll>')
    body += p.label(S, 150, w, 110, P('title'), 'p_large', p.WHITE, 'left', '<scroll>false</scroll>')
    body += p.textbox(S, 262, w, 46, P('sub'), 'p_cap', p.GREY)
    seg = '<control type="group"><top>320</top><visible>%s</visible>' % seg_on
    seg += p.image(S, 0, w, 104, M + 'round_s.png', p.SURFACE, border=24)
    for count in (2, 3):
        cw = (w - 12) // count
        group = ''
        for n in range(1, count + 1):
            x = S + 6 + (n - 1) * cw
            on = 'String.IsEqual(Window().Property(seg.on),%d)' % n
            group += p.image(x, 6, cw, 92, M + 'round_s.png', 'FF636366', '<visible>%s</visible>' % on, border=20)
            group += ('<control type="button" id="%d"><left>%d</left><top>6</top><width>%d</width><height>92</height>'
                      '<label>[B]%s[/B]</label><font>p_foot</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
                      '<align>center</align><aligny>center</aligny><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus>'
                      '<texturenofocus /><ondown>%d</ondown><onup>%d</onup></control>') % (
                SEG + n - 1, x, cw, P('seg.%d' % n), p.GREY, p.WHITE, M, LIST_SEG, BACK)
        seg += '<control type="group"><visible>String.IsEqual(Window().Property(seg.count),%d)</visible>%s</control>' % (count, group)
    seg += '</control>'
    body += seg + _list(p, LIST, TOP, '!' + seg_on) + _list(p, LIST_SEG, TOP_SEG, seg_on)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Favourites manager (boards K1-K5) -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<controls>%s</controls></window>' % (LIST, body.replace('!!String.IsEmpty', 'String.IsEmpty')))


def _cell(p, focused):
    M = p.MEDIA
    tag = 'focusedlayout' if focused else 'itemlayout'
    pw, ph = CELL_W - 24, (CELL_W - 24) * 3 // 2
    out = p.image(0, 0, CELL_W - 12, CELL_H - 16, M + 'round_s.png', p.SURFACE, border=24)
    out += p.image(0, 0, CELL_W - 12, CELL_H - 16, M + 'round_s.png', 'FF0A84FF', '<visible>%s</visible>' % _has('best'), border=24)
    out += p.image(5, 5, CELL_W - 22, CELL_H - 26, M + 'round_s.png', p.SURFACE, '<visible>%s</visible>' % _has('best'), border=20)
    out += p.image(6, 6, pw, ph, M + 'white.png', p.SURFACE2, diffuse=M + 'poster_mask.png')
    out += p.image(6, 6, pw, ph, '$INFO[ListItem.Art(poster)]', p.WHITE, '', '>scale', M + 'poster_mask.png', background=True)
    out += p.image(18, 18, 190, 50, M + 'pill_150.png', 'FF0A84FF', '<visible>%s</visible>' % _has('best'), border=25)
    out += p.label(18, 18, 190, 50, '[B]$INFO[ListItem.Property(best)][/B]', 'p_tab', p.WHITE, 'center', '<scroll>false</scroll>')
    out += p.textbox(14, ph + 16, CELL_W - 40, 84, '[B]$INFO[ListItem.Label][/B]', 'p_cap', p.WHITE)
    out += p.textbox(14, ph + 100, CELL_W - 40, 80, '$INFO[ListItem.Label2]', 'p_tab', p.GREY)
    if focused:
        out += p.image(0, 0, CELL_W - 12, CELL_H - 16, M + 'round_s.png', '1FFFFFFF', border=24)
    return '<%s width="%d" height="%d">%s</%s>' % (tag, CELL_W, CELL_H, out, tag)


def pick(p):
    """IOSFavPick.xml: the name asked about, a line, the search field (K8), the posters, and the two choices under them."""
    import status_ui as u
    S, W, H, M, P = p.SIDE, p.WIDTH, p.HEIGHT, p.MEDIA, u.P
    w = W - 2 * S
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    body = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close')
    body += p.label(S + 120, 36, w - 120, 108, P('back'), 'p_sub', p.ACCENT, 'left', '<scroll>false</scroll>')
    body += p.textbox(S, 150, w, 140, '[B]%s[/B]' % P('title'), 'p_h2', p.WHITE)
    body += p.textbox(S + 10, 292, w - 20, 92, P('sub'), 'p_cap', p.GREY)
    search = ('<control type="group"><top>392</top><visible>%s</visible>' % has('search') +
              p.image(S, 0, w, 118, M + 'round_s.png', p.SURFACE2, border=24) +
              p.icon(S + 30, 37, 44, 'magnifying-glass.png', p.GREY) +
              p.label(S + 96, 0, w - 130, 118, P('query'), 'p_sub', p.WHITE, 'left', '<scroll>false</scroll>') +
              '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>118</height>'
              '<texturefocus colordiffuse="14FFFFFF" border="24">%sround_s.png</texturefocus><texturenofocus />'
              '<ondown>%d</ondown><onup>%d</onup></control></control>') % (SEARCH, S, w, M, GRID + 1, BACK)
    body += search
    for top, cond in ((392, '!' + has('search')), (530, has('search'))):
        body += ('<control type="panel" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
                 '<visible>%s</visible><orientation>vertical</orientation><onup>%d</onup><ondown>%d</ondown>'
                 '<scrolltime tween="cubic" easing="out">200</scrolltime>%s%s</control>') % (
            GRID + (top == 530), S, top, CELL_W * 3, H - 340 - top, cond, SEARCH if top == 530 else BACK, OTHER, _cell(p, False), _cell(p, True))
    body += ('<control type="group"><visible>%s</visible>' % has('other') +
             p.pill_button(OTHER, S, H - 320, w, 128, P('other'), [('', 'noop')], 'glass', extra='<onup>%d</onup><ondown>%d</ondown>' % (GRID, SKIP)) +
             '</control>')
    body += u.link(p, SKIP, S, H - 180, w, 118, 'Skip This One', align='center', tint=p.GREY)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Favourites manager poster picker (boards K7, K8) -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<controls>%s</controls></window>' % (GRID, body.replace('!!String.IsEmpty', 'String.IsEmpty')))


def files(p):
    return {p.FOLDER + '/' + MANAGE: manage(p).encode(), p.FOLDER + '/' + PICK: pick(p).encode()}
