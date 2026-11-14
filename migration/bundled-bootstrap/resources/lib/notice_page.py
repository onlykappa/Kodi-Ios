"""Notifications › a message's details (owner, build 159: "when i tap a notification it brings me to that log").

portrait/IOSNoticeDetail.xml: a sheet over the dimmed Notifications page with the message, what happened in one
sentence, and the part of kodi.log Kodi wrote around it (notices.attach_logs copies it when the message arrives).
notifications.py fills it. Built from the same pieces as the Library status details sheet (library_page.item_sheet):
sheet_bg, the grabber, the ✕ close, a SURFACE2 rounded box and portrait.pill_button; sizes per
docs/design/APPLE-UI-POLICY.md (2.687 units per pt, every control at least 118 units).
"""
SHEET = 'IOSNoticeDetail.xml'
CLOSE, ACTION, LOG, DIM = 9700, 9701, 9710, 9099
FIX1, FIX2, TECH, SHARE = 9702, 9703, 9704, 9705   # DEC-046: the other fixes, Technical details, Share Log
FACTS = 5
HIT = 118
LINE = 196      # one log record: time and level, then up to three lines of text
LEVELS = (('error', 'FFFF453A'), ('warning', 'FFFF9F0A'), ('info', 'FF8E8E93'))


def _log_item(p, focused):
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    tag = 'focusedlayout' if focused else 'itemlayout'
    level = lambda name: 'String.IsEqual(ListItem.Property(level),%s)' % name
    return ('<%s height="%d">' % (tag, LINE) +
            (p.image(S, 0, w, LINE, p.MEDIA + 'white.png', '14FFFFFF') if focused else '') +
            ''.join(p.label(S + 24, 18, w - 48, 44, '$INFO[ListItem.Label2]', 'p_cap', tint, 'left',
                            '<scroll>false</scroll><visible>%s</visible>' % level(name)) for name, tint in LEVELS) +
            '<control type="textbox"><left>%d</left><top>62</top><width>%d</width><height>120</height><font>p_cap</font><textcolor>%s</textcolor><label>$INFO[ListItem.Label]</label><autoscroll>false</autoscroll></control>' % (S + 24,w - 48,p.WHITE) +
            p.image(S + 24, LINE - 2, w - 48, 2, p.MEDIA + 'white.png', p.SEP) +
            '</%s>' % tag)


def sheet(p):
    """portrait/IOSNoticeDetail.xml (DEC-046 boards G and H): what happened in plain words, what you can do (the fixes as
    a white capsule and rows), Technical details behind a link (facts, the kodi.log lines, Share Log). Titles and lines
    wrap to a second line instead of ending in "…" (owner)."""
    import status_ui as u
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    height = 1780
    top = p.HEIGHT - height
    plain, tech = u.neg(has('tech')), has('tech')
    wrap = '<wrapmultiline>true</wrapmultiline>'
    close = p.close_button(CLOSE, W - S - HIT + 13, top + 40, navigation='<ondown>%d</ondown>' % ACTION)
    head = (p.surface(S, top + 64, 110, 110, 'round_s.png', P('tint'), 24) +
            p.icon(S + 27, top + 91, 56, p.ICONS + P('icon'), p.WHITE) +
            p.label(S + 140, top + 52, w - 140 - HIT, 140, P('title'), 'p_h3', p.WHITE, 'left', wrap + '<aligny>top</aligny>') +
            p.label(S + 140, top + 196, w - 140, 50, P('ago'), 'p_cap', p.GREY, 'left', '<scroll>false</scroll>'))
    # The plain view, stacked (N2, owner-approved; ISSUE-299): what happened, the timeline when there is one, what you
    # can do and Technical details. A grouplist closes up the parts that are not there, so a notice without a timeline
    # or without fixes leaves no gap.
    card = ('<control type="group"><height>380</height><visible>%s</visible>' % plain +
            p.image(S, 0, w, 360, M + 'round.png', p.SURFACE2, border=32) +
            '<control type="group"><left>%d</left>' % S +
            '<control type="group"><visible>%s</visible>%s</control>' % (u.neg(has('good')), p.label(30, 22, w - 60, 46, 'WHAT HAPPENED', 'p_foot_b', p.GREY)) +
            p.label(30, 74, w - 60, 200, P('happened'), 'p_pill_s', p.WHITE, 'left', wrap + '<aligny>top</aligny>') +
            '<control type="group"><visible>%s</visible>%s%s</control>' % (
                has('safe'), u.glyph(p, 30, 284, 40, 'circle-check.png', p.GREEN), p.label(84, 270, w - 114, 80, P('safe'), 'p_foot', p.WHITE, 'left', wrap)) +
            '</control></control>')
    steps = ''
    for n in range(1, 4):
        k = 'tl.%d.' % n
        steps += ('<control type="group"><top>%d</top><visible>%s</visible>' % ((n - 1) * 70, has(k + 'text')) +
                  p.label(S + 12, 0, 150, 64, P(k + 'time'), 'p_foot', p.GREY, 'left', '<scroll>false</scroll>') +
                  p.image(S + 176, 22, 20, 20, M + 'dot.png', P(k + 'tint')) +
                  p.label(S + 220, 0, w - 232, 64, P(k + 'text'), 'p_foot', p.WHITE, 'left', '<scroll>false</scroll>') + '</control>')
    timeline = '<control type="group"><height>230</height><visible>%s + %s</visible>%s</control>' % (plain, has('tl.1.text'), steps)
    todo = ('<control type="group"><height>210</height><visible>%s + %s</visible>' % (plain, has('fix0.label')) +
            p.label(S + 12, 0, w - 24, 50, 'WHAT YOU CAN DO', 'p_foot_b', p.GREY) +
            p.pill_button(ACTION, S, 64, w, 124, P('fix0.label'), [('', 'noop')], 'primary', '', '<onup>%d</onup><ondown>%d</ondown>' % (CLOSE, FIX1)) +
            '</control>')
    rows = ''
    for n, ident in ((1, FIX1), (2, FIX2)):
        k = 'fix%d.' % n
        rows += ('<control type="group"><height>166</height><visible>%s + %s</visible>' % (plain, has(k + 'label')) +
                 u.card(p, S, 0, w, 150, p.SURFACE2) +
                 u.tap(p, ident, S, 0, w, 150) +
                 p.label(S + 30, 22, w - 140, 56, P(k + 'label'), 'p_body', p.WHITE, 'left', '<scroll>false</scroll>') +
                 p.label(S + 30, 80, w - 140, 46, P(k + 'sub'), 'p_foot', p.GREY, 'left', '<scroll>false</scroll>') +
                 p.icon(S + w - 70, 55, 40, 'chevron-right.png', p.GREY) + '</control>')
    link = ('<control type="group"><height>130</height><visible>%s + %s</visible>%s</control>' % (
        plain, has('tech.available'), u.link(p, TECH, S, 0, w, 118, 'Technical details ›', align='center')))
    stack = ('<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>%s</control>') % (top + 270, W, height - 270, card + timeline + todo + rows + link)
    # Technical details: the facts as a table, the kodi.log lines, Share Log.
    facts = '<control type="group"><top>%d</top><visible>%s</visible>' % (top + 270, tech)
    facts += u.link(p, TECH + 100, S - 10, -10, 420, 118, '‹ What happened', align='left')
    for n in range(FACTS):
        k = 'fact%d.' % n
        facts += ('<control type="group"><top>%d</top><visible>%s</visible>' % (110 + n * 104, has(k + 'label')) +
                  u.card(p, S, 0, w, 96, p.SURFACE2) +
                  p.label(S + 30, 0, 300, 96, P(k + 'label'), 'p_foot', p.GREY, 'left', '<scroll>false</scroll>') +
                  p.label(S + 330, 0, w - 360, 96, P(k + 'value'), 'p_foot_b', p.WHITE, 'right', '<scroll>false</scroll>') + '</control>')
    facts += '</control>'
    listing = ('<control type="group"><top>%d</top><visible>%s</visible>' % (top + 870, tech) +
               p.label(S + 12, 0, w - 24, 56, 'FROM KODI.LOG · TAP A LINE TO READ IT ALL', 'p_foot_b', p.GREY) +
               p.label(S + 12, 70, w - 24, 120, P('nolog'), 'p_pill_s', p.GREY, 'left', wrap + '<visible>%s</visible>' % has('nolog')) +
               '<control type="list" id="%d"><left>0</left><top>64</top><width>%d</width><height>%d</height>'
               '<orientation>vertical</orientation><onup>%d</onup><ondown>%d</ondown>'
               '<scrolltime tween="cubic" easing="out">200</scrolltime>' % (LOG, W, height - 870 - 64 - 220, TECH + 100, SHARE) +
               _log_item(p, False) + _log_item(p, True) + '</control></control>')
    share = '<control type="group"><visible>%s</visible>%s</control>' % (
        tech, p.pill_button(SHARE, S, p.HEIGHT - 170, w, 124, 'Share Log', [('', 'noop')], 'glass', '', '<onup>%d</onup>' % LOG))
    body = ('<control type="button" id="%d"><width>%d</width><height>%d</height><texturefocus colordiffuse="80000000">%swhite.png</texturefocus>'
            '<texturenofocus colordiffuse="80000000">%swhite.png</texturenofocus><onclick>Close</onclick></control>' % (DIM, W, p.HEIGHT, M, M) +
            '<control type="group">'
            '<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>' % (height, height) +
            p.image(0, top, W, height + 140, M + 'sheet_bg.png', p.SURFACE, border=102) +
            p.image((W - 100) // 2, top + 22, 100, 14, M + 'dot.png', '4DFFFFFF', border=7) +
            head + close + stack + facts + listing + share + '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s notice detail (DEC-046) -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<controls>%s</controls></window>\n') % (p.MARKER, CLOSE, body)


def files(p):
    return {p.FOLDER + '/' + SHEET: sheet(p).encode()}
