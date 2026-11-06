"""Notifications › a message's details (owner, build 159: "when i tap a notification it brings me to that log").

portrait/IOSNoticeDetail.xml: a sheet over the dimmed Notifications page with the message, what happened in one
sentence, and the part of kodi.log Kodi wrote around it (notices.attach_logs copies it when the message arrives).
notifications.py fills it. Built from the same pieces as the Library status details sheet (library_page.item_sheet):
sheet_bg, the grabber, the ✕ close, a SURFACE2 rounded box and portrait.pill_button; sizes per
docs/design/APPLE-UI-POLICY.md (2.687 units per pt, every control at least 118 units).
"""
SHEET = 'IOSNoticeDetail.xml'
CLOSE, ACTION, LOG, DIM = 9700, 9701, 9710, 9099
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
    """portrait/IOSNoticeDetail.xml."""
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    height = 1780
    top = p.HEIGHT - height
    close = ('<control type="group"><left>%d</left><top>%d</top>' % (W - S - HIT + 13, top + 40) +
             p.image(13, 13, 92, 92, M + 'dot.png', '26FFFFFF') +
             p.image(13, 13, 92, 92, M + 'dot.png', '33FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % CLOSE) +
             p.image(29, 29, 60, 60, M + 'close_cross.png', p.WHITE) +
             '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
             '<ondown>%d</ondown></control></control>' % (CLOSE, HIT, HIT, LOG))
    head = (p.surface(S, top + 64, 110, 110, 'round_s.png', P('tint'), 24) +
            p.icon(S + 27, top + 91, 56, p.ICONS + P('icon'), p.WHITE) +
            p.label(S + 140, top + 56, w - 140 - HIT, 80, P('title'), 'p_h3', p.WHITE, 'left', '<scroll>false</scroll>') +
            p.label(S + 140, top + 128, w - 140 - HIT, 50, P('ago'), 'p_cap', p.GREY, 'left', '<scroll>false</scroll>') +
            p.label(S, top + 210, w, 150, P('text'), 'p_body', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>'))
    happened = ('<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>' % (S, top + 380, has('summary')) +
                p.image(0, 0, w, 230, M + 'round.png', p.SURFACE2, border=32) +
                p.label(30, 22, w - 60, 50, 'What happened', 'p_foot_b', p.GREY) +
                p.label(30, 76, w - 60, 140, P('summary'), 'p_pill_s', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>') +
                '</control>')
    listing = ('<control type="group"><top>%d</top>' % (top + 640) +
               p.label(S + 12, 0, w - 24, 56, 'From kodi.log · tap a line to read', 'p_foot_b', p.GREY) +
               p.label(S + 12, 70, w - 24, 120, P('nolog'), 'p_pill_s', p.GREY, 'left',
                       '<wrapmultiline>true</wrapmultiline><visible>%s</visible>' % has('nolog')) +
               '<control type="list" id="%d"><left>0</left><top>64</top><width>%d</width><height>%d</height>'
               '<orientation>vertical</orientation><onup>%d</onup><ondown>%d</ondown>'
               '<scrolltime tween="cubic" easing="out">200</scrolltime>' % (LOG, W, height - 640 - 64 - 200, CLOSE, ACTION) +
               _log_item(p, False) + _log_item(p, True) + '</control></control>')
    action = p.pill_button(ACTION, S, p.HEIGHT - 170, w, 124, P('action.label'), [('', 'noop')], 'primary', '',
                           '<visible>%s</visible><onup>%d</onup>' % (has('action.label'), LOG))
    body = ('<control type="button" id="%d"><width>%d</width><height>%d</height><texturefocus colordiffuse="80000000">%swhite.png</texturefocus>'
            '<texturenofocus colordiffuse="80000000">%swhite.png</texturenofocus><onclick>Close</onclick></control>' % (DIM, W, p.HEIGHT, M, M) +
            '<control type="group">'
            '<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>' % (height, height) +
            p.image(0, top, W, height + 140, M + 'sheet_bg.png', p.SURFACE, border=102) +
            p.image((W - 100) // 2, top + 22, 100, 14, M + 'dot.png', '4DFFFFFF', border=7) +
            head + close + happened + listing + action + '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s notice detail -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<controls>%s</controls></window>\n') % (p.MARKER, CLOSE, body)


def files(p):
    return {p.FOLDER + '/' + SHEET: sheet(p).encode()}
