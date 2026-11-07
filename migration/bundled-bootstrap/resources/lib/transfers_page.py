"""portrait/IOSTransfers.xml: the Transfers page, one job at a time (owner-approved mockup, build 172; opened only by
tapping a transfer card in Notifications). The job's kind in its colour, its title, how fast it goes right now, its
peak, average and start, one graph of that job only, its bar and time left; then any other job running (tap to switch
the graph), what finished and what is next. transfers.py fills it; transfer_history.py paints the graph. Built from
the same pieces as Library status (backdrop, nav button, SURFACE cards); every control at least 118 units (44 pt).
"""
WINDOW = 'IOSTransfers.xml'
BACK, LIST = 9001, 9300
HISTORY = 9002   # top right: what finished each day (library_tools_page.HISTORY)
BAR = 9711
OTHER = 9720      # "Also running" rows are 9721, 9722
OTHERS, DONE, NEXT = 2, 3, 3
HIT = 118


def page(p):
    W, S, M = p.WIDTH, p.SIDE, p.MEDIA
    w = W - 2 * S
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    nolabel = '<scroll>false</scroll>'
    col = (w - 48) // 3

    def stat(i, title, key):
        x = 24 + i * col
        return (p.label(x, 330, col - 10, 44, title, 'p_cap', p.GREY, 'left', nolabel) +
                p.label(x, 372, col - 10, 60, P(key), 'p_pill', p.WHITE, 'left', nolabel))
    card = ('<control type="group"><left>%d</left><top>290</top><visible>%s</visible>' % (S, has('title')) +
            p.surface(-6, 0, w + 12, 1090, 'round.png', p.SURFACE, 32) +
            p.label(24, 22, w - 48, 44, P('kind'), 'p_cap', P('tint'), 'left', nolabel) +
            p.label(24, 66, w - 48, 62, P('title'), 'p_pill', p.WHITE, 'left', nolabel) +
            p.label(24, 140, w - 48, 44, 'Right now', 'p_cap', p.GREY, 'left', nolabel) +
            p.label(24, 180, w - 48, 130, P('now'), 'p_large', p.WHITE, 'left', nolabel) +
            stat(0, 'Peak', 'peak') + stat(1, 'Average', 'avg') + stat(2, 'Started', 'started') +
            p.image(24, 460, w - 48, 430, P('graph'), p.WHITE, '<visible>%s</visible>' % has('graph'), '') +
            p.label(24, 460, w - 48, 430, 'Measuring…', 'p_body', p.GREY, 'center',
                    '<aligny>center</aligny><visible>!%s</visible>' % has('graph')) +
            p.label(24, 896, (w - 48) // 2, 40, P('from'), 'p_cap', p.DIM, 'left', nolabel) +
            p.label(24 + (w - 48) // 2, 896, (w - 48) // 2, 40, 'now', 'p_cap', p.DIM, 'right', nolabel) +
            '<control type="progress" id="%d"><left>24</left><top>960</top><width>%d</width><height>14</height>'
            '<texturebg border="7" colordiffuse="FF3A3A3C">%sdot.png</texturebg><lefttexture />'
            '<midtexture border="7" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'
            % (BAR, w - 48, M, P('tint'), M) +
            p.label(24, 990, w - 48, 60, P('line'), 'p_pill_s', p.GREY, 'left', nolabel) +
            '</control>')
    empty = ('<control type="group"><left>%d</left><top>290</top><visible>!%s</visible>' % (S, has('title')) +
             p.surface(-6, 0, w + 12, 300, 'round.png', p.SURFACE, 32) +
             p.label(24, 60, w - 48, 70, 'Nothing is moving right now', 'p_pill', p.WHITE, 'center', nolabel) +
             p.label(24, 140, w - 48, 110, 'Downloads, Drive copies and conversions show here while they run.',
                     'p_cap', p.GREY, 'center', '<wrapmultiline>true</wrapmultiline>') + '</control>')

    def section(text, cond):
        return ('<control type="group"><width>%d</width><height>96</height><visible>%s</visible>' % (W, cond) +
                p.label(S + 12, 30, w - 24, 60, text, 'p_foot_b', p.GREY) + '</control>')

    def other(n):
        k = 'other.%d.' % n
        return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, HIT + 16, has(k + 'label')) +
                p.surface(S - 6, 0, w + 12, HIT, 'round.png', p.SURFACE, 32) +
                p.image(S + 24, HIT // 2 - 11, 22, 22, M + 'dot.png', P(k + 'tint')) +
                p.label(S + 66, 0, w - 440, HIT, P(k + 'label'), 'p_pill_s', p.WHITE, 'left', '<aligny>center</aligny>' + nolabel) +
                p.label(S + w - 380, 0, 356, HIT, P(k + 'rate') + '  ›', 'p_pill_s', p.GREY, 'right', '<aligny>center</aligny>' + nolabel) +
                '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
                '<texturefocus /><texturenofocus /></control>' % (OTHER + n, S - 6, w + 12, HIT) +
                '</control>')

    def entry(pre, n):
        k = '%s.%d.' % (pre, n)
        return ('<control type="group"><width>%d</width><height>100</height><visible>%s</visible>' % (W, has(k + 'title')) +
                p.label(S + 12, 0, w - 520, 100, P(k + 'title'), 'p_pill_s', p.WHITE, 'left', '<aligny>center</aligny>' + nolabel) +
                p.label(S + w - 500, 0, 488, 100, P(k + 'line'), 'p_cap', p.GREY, 'right', '<aligny>center</aligny>' + nolabel) +
                p.image(S + 12, 98, w - 24, 2, M + 'white.png', p.SEP) + '</control>')
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>1400</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
               '<visible>%s</visible>' % (LIST, W, has('title')) +
               section('Also running · tap to see its graph', has('other.1.label')) + ''.join(other(n) for n in range(1, OTHERS + 1)) +
               section('Finished', has('done.1.title')) + ''.join(entry('done', n) for n in range(1, DONE + 1)) +
               section('Up next', has('next.1.title')) + ''.join(entry('next', n) for n in range(1, NEXT + 1)) +
               '<control type="group"><width>%d</width><height>200</height>' % W +
               p.label(S + 12, 30, w - 24, 140, "Speeds are measured on the phone. Uploads can't go faster than your internet's upload.",
                       'p_cap', p.GREY, 'left', '<wrapmultiline>true</wrapmultiline>') + '</control></control>')
    quiet = ('<control type="grouplist" id="%d"><left>0</left><top>620</top><width>%d</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<visible>!%s</visible>' % (LIST + 1, W, has('title')) +
             section('Finished', has('done.1.title')) + ''.join(entry('done', n) for n in range(1, DONE + 1)) +
             section('Up next', has('next.1.title')) + ''.join(entry('next', n) for n in range(1, NEXT + 1)) + '</control>')
    history = ('<control type="group"><left>%d</left><top>31</top><width>260</width><height>%d</height>' % (W - S - 260 + 20, HIT) +
               '<control type="button" id="%d"><width>260</width><height>%d</height><label>History</label><font>p_foot_b</font>'
               '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny><textoffsetx>20</textoffsetx>'
               '<texturefocus /><texturenofocus /></control></control>' % (HISTORY, HIT, p.ACCENT, p.WHITE))
    body = ('<controls>' + p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close', '<ondown>%d</ondown>' % (OTHER + 1)) + history +
            p.label(S, 160, w, 110, 'Transfers', 'p_large') + card + empty + listing + quiet + '</controls>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s transfers -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n') % (p.MARKER, BACK, body)


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode()}
