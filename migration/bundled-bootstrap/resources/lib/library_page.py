"""Settings › Library › Library status (owner-approved mockup: docs/design/library-status-mockup.html).

Every movie and episode in Google Drive › Kodi Downloads, grouped by where it is: preparing now, downloading, waiting
(in line, waiting for phone space, or retrying after a problem), ready for Kodi and AirPlay, kept as it is. A summary
ring and the phone space on top, a filter, and a details sheet per video with what can be done about it.

- portrait/IOSLibraryStatus.xml: the page; library_status.py fills it (window properties, list 9300 items).
- portrait/IOSLibraryItem.xml: the details sheet for one video.
Sizes follow docs/design/APPLE-UI-POLICY.md: 2.687 units per pt, every control at least 118 units (44 pt).
"""
WINDOW = 'IOSLibraryStatus.xml'
ITEM = 'IOSLibraryItem.xml'
FILTERS = (('all', 'All'), ('ready', 'Ready'), ('todo', 'To do'), ('downloading', 'Downloading'))   # buttons 9101-9104
LIST, BACK, CHECK, SPACE = 9300, 9001, 9002, 9440
ROW = 200
HIT = 118
PURPLE = 'FFBF5AF2'
BLUE = 'FF0A84FF'


def _kind(name):
    return 'String.IsEqual(ListItem.Property(kind),%s)' % name


def _prop(name):
    return 'String.IsEqual(ListItem.Property(state),%s)' % name


def _row(p, focused):
    S, w, M = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA
    pos = lambda v: 'String.IsEqual(ListItem.Property(pos),%s)' % v
    backs = ''.join(p.image(S, 0, w, ROW, M + tex, p.SURFACE, '<visible>%s</visible>' % pos(v), border=43)
                    for v, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('last', 'row_last.png'), ('mid', 'white.png')))
    sep = p.image(S + 160, 0, w - 160, 2, M + 'white.png', p.SEP, '<visible>%s | %s</visible>' % (pos('mid'), pos('last')))
    focus = p.image(S, 0, w, ROW, M + 'white.png', '14FFFFFF', '<visible>%s</visible>' % pos('mid')) + ''.join(
        p.image(S, 0, w, ROW, M + tex, '14FFFFFF', '<visible>%s</visible>' % pos(v), border=43)
        for v, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('last', 'row_last.png'))) if focused else ''
    preparing = _prop('preparing')
    art = '$INFO[ListItem.Art(poster)]'
    poster = ('<control type="group"><visible>!%s</visible>' % preparing +
              p.image(S + 24, 18, 112, 164, M + 'white.png', p.SURFACE2, diffuse=M + 'poster_mask.png') +
              p.image(S + 24, 18, 112, 164, art, p.WHITE, '', '>scale', M + 'poster_mask.png', background=True) + '</control>')
    ring = ('<control type="group"><visible>%s</visible>' % preparing +
            p.image(S + 10, 25, 150, 150, M + 'ring_20.png', '29FFFFFF') +
            p.image(S + 10, 25, 150, 150, M + '$INFO[ListItem.Property(ring)]', PURPLE) +
            p.image(S + 31, 46, 108, 108, M + 'white.png', p.SURFACE2, diffuse=M + 'tile108.png') +
            p.image(S + 31, 46, 108, 108, art, p.WHITE, '', '>scale', M + 'tile108.png', background=True) + '</control>')
    text_w = w - 160 - 130
    warn = '!String.IsEmpty(ListItem.Property(warn))'
    texts = (p.label(S + 160, 40, text_w, 58, '$INFO[ListItem.Label]', 'p_pill', p.WHITE, 'left', '<scroll>false</scroll>') +
             p.label(S + 160, 100, text_w, 50, '$INFO[ListItem.Label2]', 'p_pill_s', p.GREY, 'left', '<scroll>false</scroll><visible>!%s</visible>' % warn) +
             p.label(S + 160, 100, text_w, 50, '$INFO[ListItem.Label2]', 'p_pill_s', 'FFFF9F0A', 'left', '<scroll>false</scroll><visible>%s</visible>' % warn))
    bar = lambda state, tint: ('<control type="progress"><left>%d</left><top>160</top><width>%d</width><height>12</height>'
                               '<info>ListItem.Property(pct)</info><visible>%s</visible>'
                               '<texturebg border="6" colordiffuse="52787880">%sdot.png</texturebg><lefttexture />'
                               '<midtexture border="6" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'
                               % (S + 160, text_w, _prop(state), M, tint, M))
    right = (p.icon(S + w - 96, (ROW - 60) // 2, 60, 'circle-check.png', p.GREEN, '<visible>%s</visible>' % _prop('ready')) +
             p.icon(S + w - 76, (ROW - 40) // 2, 40, 'chevron-right.png', p.GREY,
                    '<visible>!%s + !%s</visible>' % (_prop('ready'), preparing)))
    return backs + focus + sep + poster + ring + texts + bar('downloading', BLUE) + bar('uploading', p.GREEN) + right


def _folder(p, focused):
    """A folder row (Waiting, Ready for Kodi and AirPlay, Kept as it is): coloured tile, name, what is in it, count."""
    S, w, M = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA
    pos = lambda v: 'String.IsEqual(ListItem.Property(pos),%s)' % v
    backs = ''.join(p.image(S, 0, w, ROW, M + tex, p.SURFACE, '<visible>%s</visible>' % pos(v), border=43)
                    for v, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('last', 'row_last.png'), ('mid', 'white.png')))
    focus = (p.image(S, 0, w, ROW, M + 'white.png', '14FFFFFF', '<visible>%s</visible>' % pos('mid')) + ''.join(
        p.image(S, 0, w, ROW, M + tex, '14FFFFFF', '<visible>%s</visible>' % pos(v), border=43)
        for v, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('last', 'row_last.png')))) if focused else ''
    sep = p.image(S + 160, 0, w - 160, 2, M + 'white.png', p.SEP, '<visible>%s | %s</visible>' % (pos('mid'), pos('last')))
    tile = (p.surface(S + 30, 44, 112, 112, 'round_s.png', '$INFO[ListItem.Property(tint)]', 26) +
            p.icon(S + 56, 70, 60, '$INFO[ListItem.Property(icon)]', p.WHITE))
    text_w = w - 160 - 230
    texts = (p.label(S + 160, 40, text_w, 58, '$INFO[ListItem.Label]', 'p_pill', p.WHITE, 'left', '<scroll>false</scroll>') +
             p.label(S + 160, 100, text_w, 50, '$INFO[ListItem.Label2]', 'p_pill_s', p.GREY, 'left', '<scroll>false</scroll>'))
    right = (p.label(S + w - 220, 0, 130, ROW, '$INFO[ListItem.Property(count)]', 'p_pill', p.GREY, 'right', '<aligny>center</aligny>') +
             p.icon(S + w - 76, (ROW - 40) // 2, 40, 'chevron-right.png', p.GREY))
    return backs + focus + sep + tile + texts + right


def _layouts(p, focused):
    """One layout for every item: Kodi chooses among conditional item layouts by global conditions, not per item (build
    160 drew the section headers as empty poster rows), so each part shows by the item's kind instead."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    tag = 'focusedlayout' if focused else 'itemlayout'
    group = lambda kind, body: '<control type="group"><visible>%s</visible>%s</control>' % (_kind(kind), body)
    foot = p.label(S + 12, 24, w - 24, ROW - 40, '$INFO[ListItem.Label]', 'p_cap', p.GREY, 'left', '<wrapmultiline>true</wrapmultiline>')
    return ('<%s height="%d">' % (tag, ROW) + group('row', _row(p, focused)) + group('folder', _folder(p, focused)) +
            group('foot', foot) + '</%s>' % tag)


def page(p):
    """portrait/IOSLibraryStatus.xml."""
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    check = ('<control type="group"><left>%d</left><top>31</top><width>%d</width><height>%d</height>' % (W - S - HIT + 20, HIT, HIT) +
             '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
             '<ondown>9101</ondown></control>' % (CHECK, HIT, HIT) +
             p.icon((HIT - 56) // 2, (HIT - 56) // 2, 56, 'arrows-rotate.png', p.ACCENT,
                    '<animation effect="fade" start="100" end="60" time="0" condition="Control.HasFocus(%d)">Conditional</animation>' % CHECK) +
             '</control>')
    summary = (p.surface(S - 6, 340, w + 12, 210, 'round.png', p.SURFACE, 32) +
               p.image(S + 24, 365, 160, 160, M + 'ring_20.png', '29FFFFFF') +
               p.image(S + 24, 365, 160, 160, M + P('ring'), p.GREEN) +
               p.label(S + 24, 365, 160, 160, P('pct') + '%', 'p_h3', p.WHITE, 'center', '<aligny>center</aligny>') +
               p.label(S + 214, 382, w - 238, 64, P('headline'), 'p_h3', p.WHITE, 'left', '<scroll>false</scroll>') +
               p.label(S + 214, 450, w - 238, 56, P('legend'), 'p_cap', p.GREY, 'left', '<scroll>false</scroll>'))
    space = (p.surface(S - 6, 570, w + 12, 176, 'round.png', p.SURFACE, 32) +
             p.label(S + 24, 590, w - 330, 50, 'Phone space', 'p_foot', p.GREY) +
             p.label(S + w - 300, 590, 276, 50, P('free'), 'p_foot_b', p.WHITE, 'right') +
             '<control type="progress" id="%d">' % SPACE + '<left>%d</left><top>652</top><width>%d</width><height>16</height>'
             '<texturebg border="8" colordiffuse="52787880">%sdot.png</texturebg><lefttexture />'
             '<midtexture border="8" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>' % (S + 24, w - 48, M, PURPLE, M) +
             p.label(S + 24, 682, w - 48, 50, P('space'), 'p_cap', p.GREY, 'left', '<scroll>false</scroll>'))
    n = len(FILTERS)
    filters = ''.join('<control type="group"><left>%d</left><top>0</top>' % (i * w // n) +
                      p.image(4, 4, w // n - 8, 80, M + 'pill_96.png', 'FF636366',
                              '<visible>String.IsEqual(Window().Property(filter),%s)</visible>' % key, border=40) +
                      '<control type="button" id="%d"><top>-15</top><width>%d</width><height>%d</height><label>%s</label><font>p_foot_b</font><textoffsetx>0</textoffsetx>'
                      '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
                      '<texturefocus /><texturenofocus /><ondown>%d</ondown><onup>%d</onup></control></control>'
                      % (9101 + i, w // n, HIT, text, p.GREY, p.WHITE, LIST, CHECK) for i, (key, text) in enumerate(FILTERS))
    listing = ('<control type="list" id="%d"><left>0</left><top>890</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><onup>9101</onup><scrolltime tween="cubic" easing="out">250</scrolltime>' % (LIST, W) +
               _layouts(p, False) + _layouts(p, True) + '</control>')
    body = ('<controls>' + p.backdrop() +
            p.nav_button(BACK, S, 36, 'chevron-left.png', [('String.IsEqual(Window().Property(filter),all)', 'Close')], '<ondown>9101</ondown>') + check +
            p.label(S, 160, w, 110, P('title'), 'p_large', p.WHITE, 'left', '<scroll>false</scroll>') +
            p.label(S, 268, w, 56, P('sub'), 'p_sub', p.GREY, 'left', '<scroll>false</scroll>') +
            summary + space +
            '<control type="group"><left>%d</left><top>770</top>' % S + p.surface(0, 0, w, 88, 'pill_96.png', p.SURFACE, 44) + filters + '</control>' +
            listing + '</controls>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s library status -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n') % (p.MARKER, LIST, body)


def item_sheet(p):
    """portrait/IOSLibraryItem.xml: one video's details, over the dimmed page. Buttons 9201/9202 (actions), 9200 close."""
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    height = 1330
    top = p.HEIGHT - height
    facts = ''.join('<control type="group"><top>%d</top><visible>%s</visible>' % (n * 104, has('fact%d.label' % n)) +
                    (p.image(24, 0, w - 48, 2, M + 'white.png', p.SEP) if n else '') +
                    p.label(30, 0, 330, 104, P('fact%d.label' % n), 'p_pill_s', p.GREY, 'left', '<aligny>center</aligny><scroll>false</scroll>') +
                    p.label(370, 0, w - 400, 104, P('fact%d.value' % n), 'p_pill_s', p.WHITE, 'right', '<aligny>center</aligny><scroll>false</scroll>') +
                    '</control>' for n in range(4))
    status = (p.label(S + 230, top + 160, w - 230, 56, P('status'), 'p_pill_s', p.GREEN, 'left', '<scroll>false</scroll><visible>String.IsEqual(Window().Property(tone),ok)</visible>') +
              p.label(S + 230, top + 160, w - 230, 56, P('status'), 'p_pill_s', 'FFFF9F0A', 'left', '<scroll>false</scroll><visible>String.IsEqual(Window().Property(tone),warn)</visible>') +
              p.label(S + 230, top + 160, w - 230, 56, P('status'), 'p_pill_s', p.GREY, 'left', '<scroll>false</scroll><visible>String.IsEqual(Window().Property(tone),plain)</visible>'))
    close = ('<control type="group"><left>%d</left><top>%d</top>' % (W - S - HIT + 13, top + 40) +
             p.image(13, 13, 92, 92, M + 'dot.png', '26FFFFFF') +
             p.image(13, 13, 92, 92, M + 'dot.png', '33FFFFFF', '<visible>Control.HasFocus(9200)</visible>') +
             p.image(29, 29, 60, 60, M + 'close_cross.png', p.WHITE) +
             '<control type="button" id="9200"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
             '<ondown>9201</ondown></control></control>' % (HIT, HIT))
    buttons = (p.pill_button(9201, S, top + 1010, w, 124, P('action1.label'), [('', 'noop')], 'primary', '',
                             '<visible>%s</visible><onup>9200</onup><ondown>9202</ondown>' % has('action1.label')) +
               p.pill_button(9202, S, top + 1150, w, 124, '[COLOR FFFF453A]%s[/COLOR]' % P('action2.label'), [('', 'noop')], 'glass', '',
                             '<visible>%s</visible><onup>9201</onup>' % has('action2.label')))
    body = ('<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="80000000">%swhite.png</texturefocus>'
            '<texturenofocus colordiffuse="80000000">%swhite.png</texturenofocus><onclick>Close</onclick></control>' % (W, p.HEIGHT, M, M) +
            '<control type="group">'
            '<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>' % (height, height) +
            p.image(0, top, W, height + 140, M + 'sheet_bg.png', p.SURFACE, border=102) +
            p.image((W - 100) // 2, top + 22, 100, 14, M + 'dot.png', '4DFFFFFF', border=7) +
            p.image(S, top + 60, 190, 274, M + 'white.png', p.SURFACE2, diffuse=M + 'poster_mask.png') +
            p.image(S, top + 60, 190, 274, P('poster'), p.WHITE, '', '>scale', M + 'poster_mask.png', background=True) +
            p.label(S + 230, top + 70, w - 230 - HIT, 90, P('title'), 'p_h2', p.WHITE, 'left', '<scroll>false</scroll>') +
            status +
            p.label(S + 230, top + 222, w - 230, 56, P('quality'), 'p_pill_s', p.GREY, 'left', '<scroll>false</scroll>') +
            close +
            '<control type="group"><left>%d</left><top>%d</top>' % (S, top + 380) +
            p.image(0, 0, w, 4 * 104, M + 'round.png', p.SURFACE2, border=32) + facts + '</control>' +
            buttons + '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s library item -->\n<window><defaultcontrol always="true">9201</defaultcontrol>'
            '<controls>%s</controls></window>\n') % (p.MARKER, body)


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode(), p.FOLDER + '/' + ITEM: item_sheet(p).encode()}
