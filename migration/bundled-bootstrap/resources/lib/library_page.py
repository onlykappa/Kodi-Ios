"""Settings › Library › Library status (owner-approved mockup: docs/design/library-status-mockup.html).

Every movie and episode in Google Drive › Kodi Downloads, grouped by where it is: preparing now, downloading, waiting
(in line, waiting for phone space, or retrying after a problem), ready for Kodi and AirPlay, kept as it is. A summary
ring on top (owner, build 173: no phone space card: videos live on Google Drive), a filter, and a details sheet per video with what can be done about it.

- portrait/IOSLibraryStatus.xml: the page; library_status.py fills it (window properties, list 9300 items).
- portrait/IOSLibraryItem.xml: the details sheet for one video.
Sizes follow docs/design/APPLE-UI-POLICY.md: 2.687 units per pt, every control at least 118 units (44 pt).
"""
WINDOW = 'IOSLibraryStatus.xml'
ITEM = 'IOSLibraryItem.xml'
FILTERS = (('all', 'All'), ('ready', 'Ready'), ('todo', 'To do'), ('downloading', 'Downloading'))   # buttons 9101-9104
LIST, BACK, CHECK = 9300, 9001, 9002
EDIT = 9003   # Waiting › Edit order (the Queue)
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
            # Owner (build 170): the square poster stuck out of the ring. A round poster inside it (knob.png is a circle).
            p.image(S + 35, 50, 100, 100, M + 'white.png', p.SURFACE2, diffuse=M + 'knob.png') +
            p.image(S + 35, 50, 100, 100, art, p.WHITE, '', '>scale', M + 'knob.png', background=True) + '</control>')
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
            p.icon(S + 56, 70, 60, p.ICONS + '$INFO[ListItem.Property(icon)]', p.WHITE))
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
    waiting = 'String.IsEqual(Window().Property(filter),waiting)'
    edit = ('<control type="group"><left>%d</left><top>31</top><width>300</width><height>%d</height><visible>%s</visible>' % (W - S - 300 + 20, HIT, waiting) +
            '<control type="button" id="%d"><width>300</width><height>%d</height><label>Edit order</label><font>p_foot_b</font>'
            '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny><textoffsetx>20</textoffsetx>'
            '<texturefocus /><texturenofocus /><ondown>9101</ondown></control></control>' % (EDIT, HIT, p.ACCENT, p.WHITE))
    check = ('<control type="group"><left>%d</left><top>31</top><width>%d</width><height>%d</height><visible>!%s</visible>' % (W - S - HIT + 20, HIT, HIT, waiting) +
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
    n = len(FILTERS)
    filters = ''.join('<control type="group"><left>%d</left><top>0</top>' % (i * w // n) +
                      p.image(4, 4, w // n - 8, 80, M + 'pill_96.png', 'FF636366',
                              '<visible>String.IsEqual(Window().Property(filter),%s)</visible>' % key, border=40) +
                      '<control type="button" id="%d"><top>-15</top><width>%d</width><height>%d</height><label>%s</label><font>p_foot_b</font><textoffsetx>0</textoffsetx>'
                      '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
                      '<texturefocus /><texturenofocus /><ondown>%d</ondown><onup>%d</onup></control></control>'
                      % (9101 + i, w // n, HIT, text, p.GREY, p.WHITE, LIST, CHECK) for i, (key, text) in enumerate(FILTERS))
    listing = ('<control type="list" id="%d"><left>0</left><top>690</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><onup>9101</onup><scrolltime tween="cubic" easing="out">250</scrolltime>' % (LIST, W) +
               _layouts(p, False) + _layouts(p, True) + '</control>')
    body = ('<controls>' + p.backdrop() +
            p.nav_button(BACK, S, 36, 'chevron-left.png', [('String.IsEqual(Window().Property(filter),all)', 'Close')], '<ondown>9101</ondown>') + check + edit +
            p.label(S, 160, w, 110, P('title'), 'p_large', p.WHITE, 'left', '<scroll>false</scroll>') +
            p.label(S, 268, w, 56, P('sub'), 'p_sub', p.GREY, 'left', '<scroll>false</scroll>') +
            summary +
            '<control type="group"><left>%d</left><top>570</top>' % S + p.surface(0, 0, w, 88, 'pill_96.png', p.SURFACE, 44) + filters + '</control>' +
            listing + '</controls>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s library status -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n') % (p.MARKER, LIST, body)


CARD_FACTS = 5      # rows under the speed card (library_rows.FACTS)
TONES = (('ok', 'FF30D158'), ('warn', 'FFFF9F0A'), ('plain', None), ('conv', 'FFBF5AF2'), ('down', 'FF0A84FF'))


def item_sheet(p):
    """portrait/IOSLibraryItem.xml: one video's details, over the dimmed page. Buttons 9201/9202 (actions), 9200 close.
    Build 177 (owner-approved mockup): a live speed card (graph, right now, peak, average, time left, bar 9210) for a
    movie that converts or downloads, then rows sized to how many there are; a ready movie has Play / Play on TV."""
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    nos = '<scroll>false</scroll>'
    height = 1720
    top = p.HEIGHT - height
    card_on = has('card')

    def facts(y, cond):
        rows = ''.join('<control type="group"><top>%d</top><visible>%s</visible>' % (n * 104, has('fact%d.label' % n)) +
                       (p.image(24, 0, w - 48, 2, M + 'white.png', p.SEP) if n else '') +
                       p.label(30, 0, 300, 104, P('fact%d.label' % n), 'p_pill_s', p.GREY, 'left', '<aligny>center</aligny>' + nos) +
                       p.label(330, 0, w - 360, 104, P('fact%d.value' % n), 'p_pill_s', p.WHITE, 'right', '<aligny>center</aligny>' + nos) +
                       '</control>' for n in range(CARD_FACTS))
        # The rounded panel is exactly as tall as its rows (owner, build 169: no empty grey space under them).
        panels = ''.join(p.image(0, 0, w, n * 104, M + 'round.png', p.SURFACE2,
                                 '<visible>String.IsEqual(Window().Property(facts.n),%d)</visible>' % n, border=32)
                         for n in range(1, CARD_FACTS + 1))
        return '<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>' % (S, y, cond) + panels + rows + '</control>'
    col = (w - 60) // 3

    def stat(i, title, key):
        x = 30 + i * col
        return (p.label(x, 170, col - 10, 44, title, 'p_cap', p.GREY, 'left', nos) +
                p.label(x, 212, col - 10, 58, P(key), 'p_pill', p.WHITE, 'left', nos))
    card = ('<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>' % (S, top + 380, card_on) +
            p.image(0, 0, w, 620, M + 'round.png', p.SURFACE2, border=32) +
            p.label(30, 20, w - 60, 44, 'Right now', 'p_cap', p.GREY, 'left', nos) +
            p.label(30, 60, w - 60, 100, P('card.now'), 'p_h2', p.WHITE, 'left', '<aligny>center</aligny>' + nos) +
            stat(0, 'Peak', 'card.peak') + stat(1, 'Average', 'card.avg') + stat(2, 'Time left', 'card.left') +
            p.image(30, 290, w - 60, 220, P('card.graph'), p.WHITE, '<visible>%s</visible>' % has('card.graph'), '') +
            p.label(30, 290, w - 60, 220, 'Measuring…', 'p_body', p.GREY, 'center',
                    '<aligny>center</aligny><visible>!%s</visible>' % has('card.graph')) +
            p.label(30, 515, (w - 60) // 2, 40, P('card.from'), 'p_cap', p.DIM, 'left', nos) +
            p.label(30 + (w - 60) // 2, 515, (w - 60) // 2, 40, 'now', 'p_cap', p.DIM, 'right', nos) +
            '<control type="progress" id="9210"><left>30</left><top>572</top><width>%d</width><height>14</height><visible>%s</visible>'
            '<texturebg border="7" colordiffuse="FF3A3A3C">%sdot.png</texturebg><lefttexture />'
            '<midtexture border="7" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'
            % (w - 60, has('bar'), M, P('bar.tint'), M) +
            '</control>')
    status = ''.join(p.label(S + 230, top + 160, w - 230, 56, P('status'), 'p_pill_s', colour or p.GREY, 'left',
                             nos + '<visible>String.IsEqual(Window().Property(tone),%s)</visible>' % tone) for tone, colour in TONES)
    close = p.close_button(9200, W - S - HIT + 13, top + 40, navigation='<ondown>9201</ondown>')
    # Build 179 (owner): a waiting movie has three: Start converting now, Prepare next, Keep as it is (red).
    buttons = (p.pill_button(9201, S, top + 1010, w, 124, P('action1.label'), [('', 'noop')], 'primary', '',
                             '<visible>%s</visible><onup>9200</onup><ondown>9202</ondown>' % has('action1.label')) +
               p.pill_button(9202, S, top + 1150, w, 124, '[COLOR %s]%s[/COLOR]' % (P('action2.colour'), P('action2.label')), [('', 'noop')], 'glass', '',
                             '<visible>%s</visible><onup>9201</onup><ondown>9203</ondown>' % has('action2.label')) +
               p.pill_button(9203, S, top + 1290, w, 124, '[COLOR %s]%s[/COLOR]' % (P('action3.colour'), P('action3.label')), [('', 'noop')], 'glass', '',
                             '<visible>%s</visible><onup>9202</onup>' % has('action3.label')))
    body = ('<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="80000000">%swhite.png</texturefocus>'
            '<texturenofocus colordiffuse="80000000">%swhite.png</texturenofocus><onclick>Close</onclick></control>' % (W, p.HEIGHT, M, M) +
            '<control type="group">'
            '<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>' % (height, height) +
            p.image(0, top, W, height + 140, M + 'sheet_bg.png', p.SURFACE, border=102) +
            p.image((W - 100) // 2, top + 22, 100, 14, M + 'dot.png', '4DFFFFFF', border=7) +
            p.image(S, top + 60, 190, 274, M + 'white.png', p.SURFACE2, diffuse=M + 'poster_mask.png') +
            p.image(S, top + 60, 190, 274, P('poster'), p.WHITE, '', '>scale', M + 'poster_mask.png', background=True) +
            p.label(S + 230, top + 70, w - 230 - HIT, 90, P('title'), 'p_h2', p.WHITE, 'left', nos) +
            status +
            p.label(S + 230, top + 222, w - 230, 56, P('quality'), 'p_pill_s', p.GREY, 'left', nos) +
            close + card +
            facts(top + 1030, card_on) + facts(top + 380, '!' + card_on) +
            buttons + '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s library item -->\n<window><defaultcontrol always="true">9201</defaultcontrol>'
            '<controls>%s</controls></window>\n') % (p.MARKER, body)


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode(), p.FOLDER + '/' + ITEM: item_sheet(p).encode()}
