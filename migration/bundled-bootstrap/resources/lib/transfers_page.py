"""portrait/IOSTransfers.xml: the Transfers page (owner-approved mockup; opened only by tapping a transfer card in
Notifications). A speed graph with Down / Up / Peak / Today, a 5 min · 1 hour · 24 hours switch, then every transfer
with its bar, speed and time left, what is next and what finished today. transfers.py fills it; transfer_history.py
paints the graph. Built from the same pieces as Library status (backdrop, nav button, SURFACE cards, pill switch);
every control at least 118 units (44 pt).
"""
WINDOW = 'IOSTransfers.xml'
BACK, LIST = 9001, 9300
RANGES = (('5min', '5 min'), ('hour', '1 hour'), ('day', '24 hours'))   # buttons 9701-9703
JOBS, NEXT, DONE = 3, 3, 3
JOB_BAR = 9710   # job n's bar is 9710+n
HIT = 118
BLUE, GREEN, PURPLE, ORANGE = 'FF0A84FF', 'FF30D158', 'FFBF5AF2', 'FFFF9F0A'


def page(p):
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k

    def stat(i, key, title, tint):
        x = 24 + i * (w - 48) // 4
        return ((p.image(x, 30, 22, 22, M + 'dot.png', tint) if tint else '') +
                p.label(x + (32 if tint else 0), 18, 230, 46, title, 'p_cap', p.GREY, 'left', '<scroll>false</scroll>') +
                p.label(x, 66, 240, 62, P(key + '.value'), 'p_h3', p.WHITE, 'left', '<scroll>false</scroll>') +
                p.label(x, 128, 240, 44, P(key + '.mbps'), 'p_cap', p.GREY, 'left', '<scroll>false</scroll>'))
    n = len(RANGES)
    switch = ''.join('<control type="group"><left>%d</left><top>0</top>' % (i * (w - 48) // n) +
                     p.image(4, 4, (w - 48) // n - 8, 80, M + 'pill_96.png', 'FF636366',
                             '<visible>String.IsEqual(Window().Property(range),%s)</visible>' % key, border=40) +
                     '<control type="button" id="%d"><top>-15</top><width>%d</width><height>%d</height><label>%s</label><font>p_foot_b</font>'
                     '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
                     '<texturefocus /><texturenofocus /><onup>%d</onup><ondown>%d</ondown></control></control>'
                     % (9701 + i, (w - 48) // n, HIT, text, p.GREY, p.WHITE, BACK, LIST) for i, (key, text) in enumerate(RANGES))
    legend = ''.join(p.image(24 + x, 902, 30, 8, M + 'white.png', tint) + p.label(64 + x, 880, 300, 50, text, 'p_cap', p.GREY)
                     for x, tint, text in ((0, BLUE, 'Downloading'), (320, GREEN, 'Uploading to Drive'), (680, PURPLE, 'Converting')))
    chart = ('<control type="group"><left>%d</left><top>290</top>' % S +
             p.surface(-6, 0, w + 12, 1080, 'round.png', p.SURFACE, 32) +
             stat(0, 'down', 'Down', BLUE) + stat(1, 'up', 'Up', GREEN) + stat(2, 'peak', 'Peak', '') + stat(3, 'today', 'Today', '') +
             p.image(24, 200, w - 48, 660, P('graph'), p.WHITE, '<visible>%s</visible>' % has('graph'), '') +
             p.label(24, 200, w - 48, 660, 'Nothing has moved yet.', 'p_body', p.GREY, 'center',
                     '<aligny>center</aligny><visible>!%s</visible>' % has('graph')) +
             p.label(24, 820, w - 48, 44, P('limit'), 'p_cap', ORANGE, 'left', '<scroll>false</scroll>') + legend +
             '<control type="group"><left>24</left><top>960</top>' + p.surface(0, 0, w - 48, 88, 'pill_96.png', p.SURFACE2, 44) +
             switch + '</control></control>')

    def job(n):
        pre = 'job.%d.' % n
        return ('<control type="group"><width>%d</width><height>240</height><visible>%s</visible>' % (W, has(pre + 'title')) +
                p.surface(S - 6, 0, w + 12, 220, 'round.png', p.SURFACE, 32) +
                p.image(S + 24, 26, 112, 168, M + 'white.png', p.SURFACE2) +
                p.image(S + 24, 26, 112, 168, P(pre + 'poster'), p.WHITE, '', '>scale') +
                p.label(S + 160, 18, w - 190, 44, P(pre + 'kind'), 'p_cap', P(pre + 'tint'), 'left', '<scroll>false</scroll>') +
                p.label(S + 160, 58, w - 190, 58, P(pre + 'title'), 'p_pill', p.WHITE, 'left', '<scroll>false</scroll>') +
                '<control type="progress" id="%d"><left>%d</left><top>128</top><width>%d</width><height>12</height>'
                '<texturebg border="6" colordiffuse="52787880">%sdot.png</texturebg><lefttexture />'
                '<midtexture border="6" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'
                % (JOB_BAR + n, S + 160, w - 190, M, P(pre + 'tint'), M) +
                p.label(S + 160, 152, w - 190, 50, P(pre + 'line'), 'p_pill_s', p.GREY, 'left', '<scroll>false</scroll>') +
                '</control>')

    def section(text, cond):
        return ('<control type="group"><width>%d</width><height>96</height><visible>%s</visible>' % (W, cond) +
                p.label(S + 12, 30, w - 24, 60, text, 'p_foot_b', p.GREY) + '</control>')

    def entry(pre, n):
        k = '%s.%d.' % (pre, n)
        return ('<control type="group"><width>%d</width><height>100</height><visible>%s</visible>' % (W, has(k + 'title')) +
                p.label(S + 12, 0, w - 460, 100, P(k + 'title'), 'p_pill_s', p.WHITE, 'left', '<aligny>center</aligny><scroll>false</scroll>') +
                p.label(S + w - 440, 0, 428, 100, P(k + 'line'), 'p_cap', p.GREY, 'right', '<aligny>center</aligny><scroll>false</scroll>') +
                p.image(S + 12, 98, w - 24, 2, M + 'white.png', p.SEP) + '</control>')
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>1400</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><onup>9701</onup>' % (LIST, W) +
               section('Now', has('has.jobs')) + ''.join(job(n) for n in range(1, JOBS + 1)) +
               section('Up next', has('next.1.title')) + ''.join(entry('next', n) for n in range(1, NEXT + 1)) +
               section('Done today', has('done.1.title')) + ''.join(entry('done', n) for n in range(1, DONE + 1)) +
               '<control type="group"><width>%d</width><height>200</height>' % W +
               p.label(S + 12, 30, w - 24, 140, "Speeds are measured on the phone. Uploads can't go faster than your internet's upload.",
                       'p_cap', p.GREY, 'left', '<wrapmultiline>true</wrapmultiline>') + '</control></control>')
    body = ('<controls>' + p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close', '<ondown>9701</ondown>') +
            p.label(S, 160, w, 110, 'Transfers', 'p_large') + chart + listing + '</controls>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s transfers -->\n<window><defaultcontrol always="true">9701</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n') % (p.MARKER, body)


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
