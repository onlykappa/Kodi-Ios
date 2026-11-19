"""Sports › Edit: the league sheet (owner's mockups B1 and B2, 2026-11-19), drawn as its own window, IOSSportsEdit.xml.

A bottom sheet over the page that opened it: grabber, "Leagues" with a white Done capsule, one line of help, the All on / All off capsules, then
every league grouped by sport: a small caps heading and one row per league (its real logo, name, the next game, a green switch; plain switches
only, the owner dropped the per-sport "Only" links). It scrolls; sports_edit.py fills the properties item.N.* and saves each flip at once. Existing tokens and helpers only.
"""
import status_ui as u

WINDOW = 'IOSSportsEdit.xml'
DONE, ALL_ON, ALL_OFF, LIST = 9203, 9201, 9202, 9300
ROW0, SLOTS = 41000, 40
ROW_H, HEAD_H = 150, 118
TILE, TILE_PAD = 100, 12


def _switch(p, y, key):
    on, off = 'String.IsEqual(Window().Property(%son),on)' % key, 'String.IsEqual(Window().Property(%son),off)' % key
    x, w, h, knob = 876, 112, 56, 46
    track = lambda cond, color: p.image(x, y, w, h, p.MEDIA + 'pill_56.png', color, '<visible>%s</visible>' % cond, border=28)
    dot = lambda cond, kx: p.image(kx, y + (h - knob) // 2, knob, knob, p.MEDIA + 'avatar_s.png', p.WHITE, '<visible>%s</visible>' % cond)
    return track(on, p.GREEN) + track(off, 'FF39393D') + dot(on, x + w - 5 - knob) + dot(off, x + 5)


def _items(p):
    out = ''
    for n in range(SLOTS):
        key = 'item.%d.' % n
        head = u.text(p, 92, 29, 640, 60, '[UPPERCASE]%s[/UPPERCASE]' % u.P(key + 'title'), 'p_foot_b', p.GREY)
        out += u.group(p, HEAD_H, head, 'String.IsEqual(Window().Property(%skind),head)' % key)
        body = u.row_back(p, key, 972, ROW_H, color='FF000000')
        body += u.tap(p, ROW0 + n, p.SIDE, 0, 972, ROW_H)
        top = (ROW_H - TILE) // 2
        body += p.image(92, top, TILE, TILE, p.MEDIA + 'round.png', 'FFF2F2F7', border=32)
        body += p.image(92 + TILE_PAD, top + TILE_PAD, TILE - 2 * TILE_PAD, TILE - 2 * TILE_PAD, u.P(key + 'logo'), p.WHITE,
                        '<aspectratio>keep</aspectratio><visible>%s</visible>' % u.has(key + 'logo'))
        body += p.image(92 + 32, top + 32, TILE - 64, TILE - 64, p.MEDIA + 'ring_20.png', 'FF8E8E93', '<visible>!%s</visible>' % u.has(key + 'logo'))
        body += u.text(p, 222, 22, 560, 60, u.P(key + 'title'), 'p_foot_b')
        body += u.text(p, 222, 80, 560, 52, u.P(key + 'detail'), 'p_foot', p.GREY)
        body += _switch(p, (ROW_H - 56) // 2, key)
        out += u.group(p, ROW_H, body, 'String.IsEqual(Window().Property(%skind),row)' % key)
    return out


def _chip(p, ident, x, label, width):
    return (p.image(x, 13, width, 92, p.MEDIA + 'pill_96.png', p.SURFACE2, border=46) + u.tap(p, ident, x, 0, width, 118) +
            u.text(p, x, 13, width, 92, label, 'p_pill', align='center'))


def page(p):
    W, H = p.WIDTH, p.HEIGHT
    top = 150
    sheet = p.image(22, top, W - 44, H - top - 30, p.MEDIA + 'row_only.png', p.SURFACE, border=43)
    sheet += p.image((W - 120) // 2, top + 22, 120, 11, p.MEDIA + 'pill11.png', 'FF636366', border=5)
    sheet += u.text(p, 76, top + 56, 600, 110, 'Leagues', 'p_h2')
    sheet += p.pill_button(DONE, W - 76 - 250, top + 47, 250, 128, 'Done', [('', 'noop')], 'primary')
    sheet += p.textbox(76, top + 190, 928, 110, u.P('edit.help'), 'p_sub', p.GREY)
    sheet += '<control type="group"><left>76</left><top>%d</top><width>928</width><height>118</height>%s%s</control>' % (
        top + 310, _chip(p, ALL_ON, 0, 'All on', 250), _chip(p, ALL_OFF, 274, 'All off', 262))
    lst = ('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>46</bottom><orientation>vertical</orientation>'
           '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><scrolltime tween="cubic" easing="out">220</scrolltime>%s%s</control>'
           % (LIST, top + 450, W, _items(p), u.group(p, 120, '')))
    dim = ('<control type="button" id="9199"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
           '<texturefocus colordiffuse="99000000">%swhite.png</texturefocus><texturenofocus colordiffuse="99000000">%swhite.png</texturenofocus>'
           '<onclick>Close</onclick></control>' % (W, H, p.MEDIA, p.MEDIA))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports Edit sheet (owner mockups B1-B2) -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="slide" start="0,300" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>'
            '<animation effect="fade" start="100" end="0" time="140">WindowClose</animation>'
            '<controls>%s%s%s</controls></window>' % (DONE, dim, sheet, lst))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
