"""Sports › Live Now (DEC-055, DEC-057; the owner's approved rows of 2026-11-21, ISSUE-426).

Draws IOSSportsLive.xml: back, the title with "4 games on now · updated just now", then every live game as a compact row, grouped by league under a
small header (the league's logo, its name and a chevron, "College Football" under NCAAF). Only live games: no upcoming. A row (89 pt, measured from the
owner's ESPN-app reference): each team's logo at its edge with its short name (or code, "UNC") under it, its score beside the logo in a condensed
bold (Barlow Condensed ExtraBold, p_score) and, in the middle, the white game clock, the football on the side that has the ball and the grey
down-and-distance line with the yard line (red inside the 20). A tap opens the game's page. Kodi skin XML, portrait units (2.687 per pt).

Properties (sports_live.py sets them; every one is read here):
  state ('ok' | 'none' | 'error'), sub, more (the "N more games" note)
  g.G.gn / .gs / .hp / .gl (the league header: name, subtitle, 'true' when there is no subtitle, logo file; set on the first game of each league only)
  g.G.clock, g.G.dn (down and distance), g.G.yd (yard line), g.G.rz ('true' inside the 20), g.G.ball ('a' | 'h')
  g.G.a|h.name (the row shows when set) / .short / .score / .crest
  none.title / none.text / none.button, err.title / err.text / err.button
"""
import status_ui as u
import sports_page as sp

WINDOW = 'IOSSportsLive.xml'
BACK, REFRESH, RETRY, SEE_UPCOMING = sp.BACK, sp.REFRESH, sp.RETRY, 9106
GAMES = 30                             # rows on a page; the rest is behind the note
CHIPS, CHIPS_PER_ROW = 15, 5
CHIP0, LIST = 9200, 9099
SEARCH0 = 9700
CARD0 = 9740                              # the tap area of each row: a tap opens that game's page (owner, 2026-11-20)
CHIP_IDS = 20                             # the ids one chip-row variant spans
TOP = 370
CHIP_W, CHIP_H, CHIP_GAP, CHIP_ROW = 160, 91, 21, 118
PAD = 43                               # 16 pt: the rows run a little wider than the page's 20 pt margin, as the reference does
GAP = 27


def _wrap(p, x, y, w, h, value, font, color, align='left'):
    """One or two lines, never cut off (DEC-050): a label that wraps and is centred in its box."""
    return p.label(x, y, w, h, value, font, color, align, '<wrapmultiline>true</wrapmultiline><scroll>false</scroll>')


# Geometry measured from the owner's ESPN-app crops (3 px per pt, row pitch 89 pt) and approved in the mockup of 2026-11-21 (ISSUE-426).
ROW_H = 239                               # 89 pt
LOGO, LOGO_Y = 97, 40                     # 36 pt
NAME_Y, NAME_W, NAME_H = 153, 204, 50     # the short name, centred under the logo
SCORE_W, SCORE_Y, SCORE_H = 150, 70, 97   # the score, 56 pt wide, centred in the row
COL = 339                                 # 126 pt: a team's side (logo, name and score); the middle is what is left
BALL = 51                                 # 19 pt
HEAD_H, HEAD_SUB_H = 88, 128              # a league header, without and with a subtitle
CARD_H = ROW_H
LINE = '24EBEBF5'


def _team(p, key, x, logo_x):
    """A team's logo (bare, as the reference draws it) at logo_x with its short name centred under it, x being the left of the name's box; an empty
    ring when the team has no logo (never letters)."""
    out = p.image(logo_x, LOGO_Y, LOGO, LOGO, u.P(key + 'crest'), p.WHITE, '<visible>%s</visible>' % u.has(key + 'crest'), '>keep')
    out += p.image(logo_x + 22, LOGO_Y + 22, LOGO - 44, LOGO - 44, p.MEDIA + 'ring_20.png', 'FF8E8E93', '<visible>%s</visible>' % u.neg(u.has(key + 'crest')))
    out += u.text(p, x, NAME_Y, NAME_W, NAME_H, u.P(key + 'short'), 'p_foot_b', p.GREY, 'center')
    return out


def _clock_row(p, key, top, cond):
    """The clock with the football on the side that has the ball: a centred row, the invisible ball takes no room."""
    ball = lambda side: p.image(0, (59 - BALL) // 2, BALL, BALL, p.MEDIA + 'football.png', p.WHITE,
                                '<visible>String.IsEqual(Window().Property(%sball),%s)</visible>' % (key, side), '>keep')
    return ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>59</height><orientation>horizontal</orientation><align>center</align>'
            '<itemgap>14</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s'
            '<control type="label"><width>auto</width><height>59</height><font>p_pill</font><textcolor>FFFFFFFF</textcolor><aligny>center</aligny>'
            '<scroll>false</scroll><label>%s</label></control>%s</control>') % (COL, top, p.WIDTH - 2 * PAD - 2 * COL, cond, ball('a'), u.P(key + 'clock'), ball('h'))


def _detail_row(p, key):
    """"2nd & 10 · WVU 45": grey, the yard line red inside the 20 (ESPN's red zone)."""
    grey = lambda cond, value, extra='': ('<control type="label"><width>auto</width><height>45</height><font>p_cap</font><textcolor>%s</textcolor><aligny>center</aligny>'
                                          '<scroll>false</scroll>%s<label>%s</label></control>') % (extra or p.GREY, cond, value)
    rz = 'String.IsEqual(Window().Property(%srz),true)' % key
    return ('<control type="grouplist"><left>%d</left><top>140</top><width>%d</width><height>45</height><orientation>horizontal</orientation><align>center</align>'
            '<itemgap>8</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s%s%s%s</control>') % (
        COL, p.WIDTH - 2 * PAD - 2 * COL, u.has(key + 'dn'), grey('', u.P(key + 'dn')),
        grey('<visible>%s</visible>' % u.has(key + 'yd'), '·'),
        grey('<visible>%s</visible>' % u.neg(rz), u.P(key + 'yd')),
        grey('<visible>%s</visible>' % rz, u.P(key + 'yd'), 'FFFF453A'))


def header(p, g, with_sub):
    """A league's header: its logo, name and a chevron (not a button), "College Football" under NCAAF. A hairline above it, but not on the first."""
    key, h = 'g.%d.' % g, HEAD_SUB_H if with_sub else HEAD_H
    cond = u.has(key + ('gs' if with_sub else 'hp'))   # hp: a header with no subtitle (set by sports_live.py), gs: one with
    body = '' if g == 1 else p.image(PAD, 0, p.WIDTH - 2 * PAD, 2, p.MEDIA + 'white.png', LINE)
    body += p.image(PAD + 22, (h - 64) // 2 + 6, 64, 64, u.P(key + 'gl'), p.WHITE, '<visible>%s</visible>' % u.has(key + 'gl'), '>keep')
    ty = 16 if with_sub else 24
    body += ('<control type="grouplist"><left>%d</left><top>%d</top><width>600</width><height>52</height><orientation>horizontal</orientation>'
             '<itemgap>10</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<control type="label"><width>auto</width><height>52</height><font>p_foot_b</font><textcolor>FFFFFFFF</textcolor><aligny>center</aligny>'
             '<scroll>false</scroll><label>%s</label></control>%s</control>') % (
        PAD + 22 + 64 + 24, ty, u.P(key + 'gn'), p.icon(0, 10, 32, 'chevron-right.png', p.GREY))
    if with_sub:
        body += u.text(p, PAD + 22 + 64 + 24, 68, 700, 40, u.P(key + 'gs'), 'p_cap', p.GREY)
    return u.group(p, h, body, cond)


def head_row(p, g):
    """One live game as a compact row (see the module docstring)."""
    w = p.WIDTH - 2 * PAD
    P, key = u.P, 'g.%d.' % g
    body = p.image(PAD, 0, w, 2, p.MEDIA + 'white.png', LINE, '<visible>%s</visible>' % u.neg(u.has(key + 'gn')))   # a hairline between rows, none under a header
    body += '<control type="group"><left>%d</left><top>0</top><width>%d</width><height>%d</height>' % (PAD, w, ROW_H)
    body += _team(p, key + 'a.', 0, 54)
    body += _team(p, key + 'h.', w - NAME_W, w - COL + 188)
    body += u.text(p, 188, SCORE_Y, SCORE_W, SCORE_H, P(key + 'a.score'), 'p_score', p.WHITE, 'center')
    body += u.text(p, w - COL, SCORE_Y, SCORE_W, SCORE_H, P(key + 'h.score'), 'p_score', p.WHITE, 'center')
    body += _clock_row(p, key, 64, u.has(key + 'dn')) + _clock_row(p, key, 89, u.neg(u.has(key + 'dn'))) + _detail_row(p, key)
    body += '</control>'
    body += ('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
             '<texturefocus colordiffuse="18FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>') % (CARD0 + g - 1, PAD, w, ROW_H, p.MEDIA)
    return u.group(p, ROW_H, body, u.has(key + 'a.name'))


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
    # No refresh button: ESPN's answer is kept fresh by the service (sports_data loop), so nothing needs refreshing by hand (owner, build 619)
    head += u.text(p, S, 160, w, 110, 'Live Now', 'p_large') + u.text(p, S, 268, w, 56, P('sub'), 'p_sub', p.GREY)
    items = ''   # no league chips on Live Now (owner, 2026-11-20): the cards start under the subtitle
    for g in range(1, GAMES + 1):
        items += header(p, g, False) + header(p, g, True) + head_row(p, g)
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
