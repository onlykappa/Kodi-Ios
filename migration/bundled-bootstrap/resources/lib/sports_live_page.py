"""Sports › Live Now (DEC-055, DEC-057; approved boards 6-9 of docs/design/sports-approved-pages.html, option B).

Draws IOSSportsLive.xml: back, refresh, the title with "4 games on now · updated just now", league chips, then one card per live game:
the league label and the clock, both teams with their scores, and the game's sources under them (best first, each with a play button).
A card is a run of pooled rows in one vertical list (a head row, then one row per source), because Kodi list items cannot differ in height;
sports_live.py fills the properties. Kodi skin XML, portrait units (2.687 per pt); existing tokens and helpers only.

Properties (sports_live.py sets them; every one is read here):
  state ('ok' | 'none' | 'error'), sub, chips.rows (1-3), chip.N (label) and chip.N.on ('true'), more (the "N more games" note)
  g.G.league, g.G.clock, g.G.pos ('first' | 'only'), g.G.a|h.code / .name / .score / .lead ('true') / .crest, g.G.n (sources)
  g.G.s.S.addon, .mono, .detail, .also, .tag ('best' | 'good' | ''), .pos ('mid' | 'last')
  none.title / none.text / none.button, err.title / err.text / err.button
"""
import status_ui as u
import sports_page as sp

WINDOW = 'IOSSportsLive.xml'
BACK, REFRESH, RETRY, SEE_UPCOMING = sp.BACK, sp.REFRESH, sp.RETRY, 9106
GAMES, SOURCES = 12, 4                 # cards on a page and sources shown under each; the rest is behind the league chips and the note
CHIPS, CHIPS_PER_ROW = 15, 5
CHIP0, PLAY0, LIST = 9200, 9300, 9099
SEARCH0 = 9700
ALSO_IDS, CHIP_IDS = 200, 20          # the row variants with an "Also on" line, and the ids one chip-row variant spans
TOP = 370
CHIP_W, CHIP_H, CHIP_GAP, CHIP_ROW = 160, 91, 21, 118
PAD = 43                               # 16 pt
HEAD_H = 341
SRC_H, SRC_ALSO_H = 161, 215           # 60 pt, 80 pt
GAP = 27                               # 10 pt between cards
TAG_W = {'best': 128, 'good': 214}


def _wrap(p, x, y, w, h, value, font, color, align='left'):
    """One or two lines, never cut off (DEC-050): a label that wraps and is centred in its box."""
    return p.label(x, y, w, h, value, font, color, align, '<wrapmultiline>true</wrapmultiline><scroll>false</scroll>')


def _bg(p, key, w, h, x, poses):
    """The card's background for this row: rounded ends only at the first/last row of a card (the row_* textures)."""
    out = ''
    for pos, tex in poses:
        out += p.image(x, 0, w, h, p.MEDIA + tex, p.SURFACE, '<visible>String.IsEqual(Window().Property(%spos),%s)</visible>' % (key, pos),
                       border=43 if tex != 'white.png' else '')
    return out


def _team(p, key, w, y):
    """One team row: the crest circle (a picture when the add-on has one), the name, the score (white for the leader)."""
    P = u.P
    out = p.image(PAD, y + 3, 86, 86, p.MEDIA + 'pill_96.png', u.TRACK)   # a plain circle: no 9-slice border
    out += p.image(PAD, y + 3, 86, 86, P(key + 'crest'), p.WHITE, '<visible>%s</visible>' % u.has(key + 'crest'), '>scale')
    out += u.text(p, PAD, y + 3, 86, 86, P(key + 'code'), 'p_cap', p.WHITE, 'center').replace(
        '<scroll>false</scroll>', '<scroll>false</scroll><visible>%s</visible>' % u.neg(u.has(key + 'crest')), 1)
    out += _wrap(p, PAD + 118, y, w - 2 * PAD - 118 - 150, 92, P(key + 'name'), 'p_body', p.WHITE)
    lead = 'String.IsEqual(Window().Property(%slead),true)' % key
    out += u.text(p, w - PAD - 140, y, 140, 92, P(key + 'score'), 'p_h2', p.WHITE, 'right').replace(
        '<scroll>false</scroll>', '<scroll>false</scroll><visible>%s</visible>' % lead, 1)
    out += u.text(p, w - PAD - 140, y, 140, 92, P(key + 'score'), 'p_h2', p.GREY, 'right').replace(
        '<scroll>false</scroll>', '<scroll>false</scroll><visible>%s</visible>' % u.neg(lead), 1)
    return out


def head_row(p, g):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    P, key = u.P, 'g.%d.' % g
    body = _bg(p, key, w, HEAD_H, S, (('first', 'row_first.png'), ('only', 'row_only.png')))
    body += p.image(S + PAD, PAD, 190, 64, p.MEDIA + 'pill_56.png', u.SURF2, border=28)
    body += u.text(p, S + PAD, PAD, 190, 64, P(key + 'league'), 'p_foot_b', p.WHITE, 'center')
    body += ('<control type="grouplist"><left>%d</left><top>%d</top><width>420</width><height>64</height><orientation>horizontal</orientation>'
             '<align>right</align><itemgap>14</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<control type="image"><width>22</width><height>22</height><top>21</top><texture colordiffuse="FFFF453A">%sdot.png</texture></control>'
             '<control type="label"><width>auto</width><height>64</height><font>p_sub</font><textcolor>FFFF453A</textcolor><aligny>center</aligny>'
             '<scroll>false</scroll><label>%s</label></control></control>' % (S + w - PAD - 420, PAD, p.MEDIA, P(key + 'clock')))
    shifted = '<control type="group"><left>%d</left><top>0</top><width>%d</width><height>%d</height>%s</control>'
    body += shifted % (S, w, HEAD_H, _team(p, key + 'a.', w, 128) + _team(p, key + 'h.', w, 228))
    return u.group(p, HEAD_H, body, u.has(key + 'a.name'))


def src_row(p, g, s, also):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    P, key = u.P, 'g.%d.s.%d.' % (g, s)
    h = SRC_ALSO_H if also else SRC_H
    present = u.has(key + 'addon')
    cond = present + (' + ' + u.has(key + 'also') if also else ' + ' + u.neg(u.has(key + 'also')))
    body = _bg(p, key, w, h, S, (('mid', 'white.png'), ('last', 'row_last.png')))
    body += p.image(S + PAD, 0, w - 2 * PAD, 3, p.MEDIA + 'white.png', '1FEBEBF5')
    body += p.image(S + PAD, (h - 108) // 2, 108, 108, p.MEDIA + 'r27.png', u.SURF2)
    body += u.text(p, S + PAD, (h - 108) // 2, 108, 108, P(key + 'mono'), 'p_foot_b', p.WHITE, 'center')
    x, tw = S + PAD + 140, w - 2 * PAD - 140 - 96 - 32 - 214 - 24
    top = 22 if also else 24
    body += u.text(p, x, top, tw + 214, 56, P(key + 'addon'), 'p_h3', p.WHITE)
    body += u.text(p, x, top + 55, tw + 214, 50, P(key + 'detail'), 'p_sub', p.GREY)
    if also:
        body += u.text(p, x, top + 105, w - 2 * PAD - 140 - 96 - 32, 50, P(key + 'also'), 'p_sub', p.GREY)
    for tag, label, fill, color in (('best', 'Best', '330A84FF', p.ACCENT), ('good', 'Also good', '24EBEBF5', p.GREY)):
        cx = S + w - PAD - 96 - 24 - TAG_W[tag]
        on = 'String.IsEqual(Window().Property(%stag),%s)' % (key, tag)
        body += '<control type="group"><visible>%s</visible>%s%s</control>' % (
            on, p.image(cx, (h - 62) // 2, TAG_W[tag], 62, p.MEDIA + 'pill_56.png', fill, border=28),
            u.text(p, cx, (h - 62) // 2, TAG_W[tag], 62, label, 'p_foot_b', color, 'center'))
    play = S + w - PAD - 96
    body += p.image(play, (h - 96) // 2, 96, 96, p.MEDIA + 'pill_96.png', p.WHITE, border=48)
    body += p.image(play + 33, (h - 96) // 2 + 28, 40, 40, p.MEDIA + 'play.png', 'FF000000', '', '>keep')   # the solid triangle
    ident = PLAY0 + (g - 1) * 10 + (s - 1) + (ALSO_IDS if also else 0)   # unique per variant; sports_live.py maps both ranges back
    body += ('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
             '<texturefocus colordiffuse="22FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>' % (ident, S, w, h, p.MEDIA))
    return u.group(p, h, body, cond)


def search_row(p, g):
    """A source-free live game can request a focused search."""
    S, w, key = p.SIDE, p.WIDTH - 2 * p.SIDE, 'g.%d.' % g
    body = p.image(S, 0, w, SRC_H, p.MEDIA + 'row_last.png', p.SURFACE, border=43)
    body += p.pill_button(SEARCH0 + g - 1, S + (w - 440) // 2, 16, 440, 128,
                          'Find sources', [('', 'noop')], 'primary')
    cond = u.has(key + 'id') + ' + String.IsEqual(Window().Property(%sn),0)' % key
    return u.group(p, SRC_H, body, cond)


def chip_id(rows, n):
    return CHIP0 + (rows - 1) * CHIP_IDS + n


def chips_block(p, rows):
    S = p.SIDE
    out = ''
    for n in range(CHIPS):
        r, c = divmod(n, CHIPS_PER_ROW)
        if r >= rows:
            break
        key = 'chip.%d' % n
        on = 'String.IsEqual(Window().Property(%s.on),true)' % key
        x, y = S + c * (CHIP_W + CHIP_GAP), r * CHIP_ROW + (CHIP_ROW - CHIP_H) // 2
        chip = (p.image(x, y, CHIP_W, CHIP_H, p.MEDIA + 'pill_96.png', p.WHITE, '<visible>%s</visible>' % on, border=45) +
                p.image(x, y, CHIP_W, CHIP_H, p.MEDIA + 'pill_96.png', p.SURFACE, '<visible>%s</visible>' % u.neg(on), border=45) +
                u.text(p, x, y, CHIP_W, CHIP_H, u.P(key), 'p_pill', 'FF000000', 'center').replace(
                    '<scroll>false</scroll>', '<scroll>false</scroll><visible>%s</visible>' % on, 1) +
                u.text(p, x, y, CHIP_W, CHIP_H, u.P(key), 'p_pill', p.WHITE, 'center').replace(
                    '<scroll>false</scroll>', '<scroll>false</scroll><visible>%s</visible>' % u.neg(on), 1) +
                '<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><label></label>'
                '<texturefocus /><texturenofocus /></control>' % (chip_id(rows, n), x, r * CHIP_ROW, CHIP_W, CHIP_ROW))
        out += '<control type="group"><visible>%s</visible>%s</control>' % (u.has(key), chip)
    return out


def page(p):
    S, W = p.SIDE, p.WIDTH
    w = W - 2 * S
    P = u.P
    ok, none, bad = ('String.IsEqual(Window().Property(state),%s)' % s for s in ('ok', 'none', 'error'))
    head = p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close')
    head += ('<control type="button" id="%d"><left>%d</left><top>40</top><width>150</width><height>118</height><label></label>'
             '<texturefocus /><texturenofocus /><animation effect="fade" start="100" end="65" time="0" condition="Control.HasFocus(%d)">Conditional</animation></control>'
             % (REFRESH, W - S - 150, REFRESH))
    head += p.icon(W - S - 84, 57, 84, 'arrows-rotate.png', p.ACCENT)
    head += u.text(p, S, 160, w, 110, 'Live Now', 'p_large') + u.text(p, S, 268, w, 56, P('sub'), 'p_sub', p.GREY)
    rows = ''.join(u.group(p, r * CHIP_ROW + 21, chips_block(p, r), 'String.IsEqual(Window().Property(chips.rows),%d)' % r) for r in (1, 2, 3))
    items = rows
    for g in range(1, GAMES + 1):
        items += head_row(p, g)
        items += search_row(p, g)
        for s in range(1, SOURCES + 1):
            items += src_row(p, g, s, False) + src_row(p, g, s, True)
        items += u.group(p, GAP, '', u.has('g.%d.a.name' % g))
    items += u.group(p, 150, u.text(p, S, 0, w, 150, P('more'), 'p_sub', p.GREY, 'center'), u.has('more'))
    items += u.group(p, 360, '', 'true')
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
               '<usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s</control>') % (LIST, TOP, W, ok, items)

    def message(cond, key, glyph, tint, bg, button_id, button_w=340):
        out = p.image((W - 161) // 2, 640, 161, 161, p.MEDIA + 'pill_150.png', bg)
        out += p.icon((W - 80) // 2, 680, 80, glyph, tint)
        out += u.text(p, S, 840, w, 80, P(key + '.title'), 'p_h3', p.WHITE, 'center')
        out += p.label(S + 60, 930, w - 120, 130, P(key + '.text'), 'p_sub', p.GREY, 'center', '<wrapmultiline>true</wrapmultiline><aligny>top</aligny><scroll>false</scroll>')
        out += p.pill_button(button_id, (W - button_w) // 2, 1090, button_w, 134, P(key + '.button'), [('', 'noop')], 'primary')
        return '<control type="group"><visible>%s</visible>%s</control>' % (cond, out)
    nothing = message(none, 'none', 'tower-broadcast.png', p.GREY, '24EBEBF5', SEE_UPCOMING, 440)   # "See Upcoming" needs the room
    failed = message(bad, 'err', 'triangle-exclamation.png', 'FFFF9F0A', '2EFF9F0A', RETRY)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports Live Now: approved boards 6-9, option B (DEC-055) -->\n'
            '<window><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (BACK, head + listing + nothing + failed))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
