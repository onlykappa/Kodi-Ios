"""Sports › Remind me: the reminder sheet (owner mockup page 7), IOSSportsRemind.xml.

A bottom sheet over the dimmed game page: grabber, "Remind me about Colts at Texans", one line of help, a card with the two switches ("When a
source is ready", "15 minutes before it starts"), a wide white capsule ("Turn on reminder", or "Done" when a reminder already exists) and a text
button under it ("Cancel", or a red "Turn reminder off"). sports_remind.py fills the properties; existing tokens and helpers only."""
import status_ui as u

WINDOW = 'IOSSportsRemind.xml'
ROW1, ROW2, PRIMARY, SECONDARY, DONE, SECONDARY_OFF, DIM = 9401, 9402, 9403, 9404, 9405, 9406, 9499
ROW_H = 150
SHEET_H = 1000


def _switch(p, y, key):
    on, off = 'String.IsEqual(Window().Property(%son),on)' % key, 'String.IsEqual(Window().Property(%son),off)' % key
    x, w, h, knob = 876, 112, 56, 46
    track = lambda cond, color: p.image(x, y, w, h, p.MEDIA + 'pill_56.png', color, '<visible>%s</visible>' % cond, border=28)
    dot = lambda cond, kx: p.image(kx, y + (h - knob) // 2, knob, knob, p.MEDIA + 'avatar_s.png', p.WHITE, '<visible>%s</visible>' % cond)
    return track(on, p.GREEN) + track(off, 'FF39393D') + dot(on, x + w - 5 - knob) + dot(off, x + 5)


def _row(p, ident, key, y, first):
    out = p.image(p.SIDE, y, 972, ROW_H, p.MEDIA + ('row_first.png' if first else 'row_last.png'), p.SURFACE2, border=43)
    out += u.tap(p, ident, p.SIDE, y, 972, ROW_H)
    out += u.text(p, 92, y + 22, 760, 60, u.P(key + 'label'), 'p_foot_b')
    out += u.text(p, 92, y + 80, 760, 52, u.P(key + 'detail'), 'p_foot', p.GREY)
    out += _switch(p, y + (ROW_H - 56) // 2, key)
    if not first:
        out += p.image(92, y, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
    return out


def page(p):
    W, H = p.WIDTH, p.HEIGHT
    top = H - SHEET_H - 30
    sheet = p.image(22, top, W - 44, SHEET_H, p.MEDIA + 'row_only.png', p.SURFACE, border=43)
    sheet += p.image((W - 120) // 2, top + 22, 120, 11, p.MEDIA + 'pill11.png', 'FF636366', border=5)
    sheet += p.textbox(100, top + 70, W - 200, 120, u.P('heading'), 'p_h3').replace('<autoscroll>', '<align>center</align><autoscroll>')
    sheet += p.textbox(100, top + 200, W - 200, 110, u.P('sub'), 'p_sub', p.GREY).replace('<autoscroll>', '<align>center</align><autoscroll>')
    rows = _row(p, ROW1, 'row.1.', top + 335, True) + _row(p, ROW2, 'row.2.', top + 335 + ROW_H, False)
    new, old = 'String.IsEqual(Window().Property(mode),new)', 'String.IsEqual(Window().Property(mode),existing)'
    pill_y = top + 335 + 2 * ROW_H + 50
    sheet += rows
    at = lambda y, h, cond, body: '<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height><visible>%s</visible>%s</control>' % (y, W, h, cond, body)
    sheet += at(pill_y, 140, new, p.pill_button(PRIMARY, p.SIDE, 0, 972, 128, 'Turn on reminder', [('', 'noop')], 'primary', 'bell.png', inline=True))
    sheet += at(pill_y, 140, old, p.pill_button(DONE, p.SIDE, 0, 972, 128, 'Done', [('', 'noop')], 'primary'))
    link_y = pill_y + 140
    sheet += at(link_y, 118, new, u.link(p, SECONDARY, p.SIDE, 0, 972, 118, 'Cancel', 'center', 'p_body'))
    sheet += at(link_y, 118, old, u.link(p, SECONDARY_OFF, p.SIDE, 0, 972, 118, 'Turn reminder off', 'center', 'p_body', 'FFFF453A'))
    dim = ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
           '<texturefocus colordiffuse="99000000">%swhite.png</texturefocus><texturenofocus colordiffuse="99000000">%swhite.png</texturenofocus>'
           '<onclick>Close</onclick></control>' % (DIM, W, H, p.MEDIA, p.MEDIA))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports reminder sheet (owner mockup page 7) -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="slide" start="0,300" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>'
            '<animation effect="fade" start="100" end="0" time="140">WindowClose</animation>'
            '<controls>%s%s</controls></window>' % (PRIMARY, dim, sheet))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
