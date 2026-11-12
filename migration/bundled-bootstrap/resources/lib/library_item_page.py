"""Library file manager, step L4 (DEC-043, docs/design/library-files-mockups.html board C, round 3).

Draws IOSLibraryItem2.xml: a sheet over the show for one episode (or movie): title and line; its steps as a short
checklist (on Google Drive, ready for Kodi and AirPlay, AI Upscale, subtitles) with a tick, a running bar or a red '!';
the file facts; then the main action (Play, or Repair on a problem), a second one (Play on TV / Choose a Version) and
a red Delete. library_manager.py fills it (fill_item).
"""
WINDOW = 'IOSLibraryItem2.xml'
CLOSE, PRIMARY, SECONDARY, DELETE = 9001, 9010, 9011, 9012
STEPS, STEP_BAR = 4, 9500
FACTS = 4
TOP = 150
MARKS = (('ok', 'circle-check.png', 'FF30D158'), ('bad', 'circle-exclamation.png', 'FFFF453A'),
         ('off', 'circle.png', '4DEBEBF5'), ('run', 'circle-half-stroke.png', 'FFFF9F0A'))


def page(p):
    import status_ui as u
    W, S, w = p.WIDTH, p.SIDE, p.WIDTH - 2 * p.SIDE
    P = u.P
    out = p.image(0, 0, W, p.HEIGHT, p.MEDIA + 'white.png', '99000000')   # the dimmed page behind the sheet
    out += p.image(0, TOP, W, p.HEIGHT - TOP + 60, p.MEDIA + 'r27.png', 'FF1C1C1E', border=27)
    out += p.image((W - 96) // 2, TOP + 24, 96, 13, p.MEDIA + 'pill16.png', '4DEBEBF5', border=6)   # grabber
    out += u.text(p, S, TOP + 70, w - 140, 80, P('title'), 'p_h2') + u.text(p, S, TOP + 152, w, 50, P('sub'), 'p_foot', p.GREY)
    out += p.nav_button(CLOSE, W - S - 118, TOP + 50, 'xmark.png', [('true', 'Close')])
    y = TOP + 240
    steps = u.card(p, S, y, w, STEPS * 150)
    for n in range(STEPS):
        k, top = 'step.%d.' % n, y + n * 150
        row = ''
        for state, glyph, tint in MARKS:
            row += u.glyph(p, S + 38, top + 46, 50, glyph, tint, '<visible>String.IsEqual(Window().Property(%sstate),%s)</visible>' % (k, state))
        row += u.text(p, S + 120, top + 24, w - 160, 54, P(k + 'title'), 'p_body')
        row += u.text(p, S + 120, top + 80, w - 160, 46, P(k + 'detail'), 'p_foot', p.GREY)
        row += '<control type="group"><visible>%s</visible>%s</control>' % (
            'String.IsEqual(Window().Property(%sstate),run) + %s' % (k, u.has(k + 'pct')),
            u.id_bar(p, STEP_BAR + n, S + 120, top + 132, w - 160, 11, u.BLUE, texture='pill11.png', border=5))
        if n:
            row += p.image(S + 120, top, w - 120, 3, p.MEDIA + 'white.png', '1FEBEBF5')
        steps += '<control type="group"><visible>%s</visible>%s</control>' % (u.has(k + 'title'), row)
    out += steps
    y += STEPS * 150 + 38
    facts = u.card(p, S, y, w, FACTS * 96)
    for n in range(FACTS):
        k, top = 'fact.%d.' % n, y + n * 96
        facts += u.text(p, S + 38, top, 260, 96, P(k + 'k'), 'p_foot', p.GREY)
        facts += u.text(p, S + 300, top, w - 338, 96, P(k + 'v'), 'p_foot')
    out += facts
    y += FACTS * 96 + 54
    # Main action: a white capsule (Play, or Repair on a problem); second: a dark capsule; Delete: red text.
    half = (w - 32) // 2
    out += p.image(S, y, half, 134, p.MEDIA + 'pill_134.png', 'FFFFFFFF', border=67)
    out += u.tap(p, PRIMARY, S, y, half, 134) + u.text(p, S, y, half, 134, P('primary'), 'p_btn', 'FF000000', 'center')
    out += '<control type="group"><visible>%s</visible>%s</control>' % (u.has('secondary'), (
        p.image(S + half + 32, y, half, 134, p.MEDIA + 'pill_134.png', 'FF3A3A3C', border=67) +
        u.tap(p, SECONDARY, S + half + 32, y, half, 134) + u.text(p, S + half + 32, y, half, 134, P('secondary'), 'p_btn', p.WHITE, 'center')))
    out += ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>118</height><label>%s</label>'
            '<font>p_btn</font><textcolor>FFFF453A</textcolor><focusedcolor>FFFF453A</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturefocus /><texturenofocus /></control>') % (DELETE, S, y + 170, w, P('delete'))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Library file manager board C (DEC-043), drawn by library_item_page.py -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>' % (PRIMARY, out))


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
