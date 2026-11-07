"""The library tools' pages (owner-approved mockup docs/design/library-tools-mockups.html): Queue, History and AirPlay
check (owner, build 173: no Phone space page, videos live on Google Drive). tool_pages.py fills them through window
properties; library_tools.py says what goes in them.

- portrait/IOSQueue.xml        Library status › Waiting › Edit order: ▲ ▼ per video (no drag on iPhone).
- portrait/IOSHistory.xml      Transfers › History: Today / Yesterday / 7 days.
- portrait/IOSAirPlayCheck.xml and 1080i/IOSAirPlayCheck.xml   Play on TV › Last time (landscape, over the video) and an
  AirPlay notification (portrait).
Built from the same pieces as Library status and Transfers (backdrop, nav button, SURFACE cards). Every portrait control
is at least 118 units (44 pt); the landscape sheet's at least 100 (44 pt on its 1920 canvas).
"""
QUEUE, HISTORY, AIRPLAY = 'IOSQueue.xml', 'IOSHistory.xml', 'IOSAirPlayCheck.xml'
BACK, LIST = 9001, 9300
UP, DOWN = 9810, 9830          # line row n: ▲ 9810+n, ▼ 9830+n
DAY = 9870                     # History day switch 9871..9873
CLOSE = 9500                   # landscape AirPlay check: × (9099 is the dimmed screen around the sheet)
HIT = 118
ROW = 150
QUEUE_SLOTS, HELD_SLOTS, DRIVE_SLOTS, HISTORY_SLOTS, STEPS = 10, 3, 3, 12, 4
DAYS = (('today', 'Today'), ('yesterday', 'Yesterday'), ('week', '7 days'))   # library_tools.DAYS
PURPLE, ORANGE, RED = 'FFBF5AF2', 'FFFF9F0A', 'FFFF453A'
NOLABEL = '<scroll>false</scroll>'


def _P(k):
    return '$INFO[Window().Property(%s)]' % k


def _has(k):
    return '!String.IsEmpty(Window().Property(%s))' % k


def _is(k, v):
    return 'String.IsEqual(Window().Property(%s),%s)' % (k, v)


def _window(p, comment, default, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s %s -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation><controls>%s</controls></window>\n'
            ) % (p.MARKER, comment, default, body)


def _head(p, title, sub, right='', scroll=False):
    """Back, the page's large title (a short fixed name, so it always fits) and the line under it; `scroll` lets a
    line with a video's name of any length scroll instead of being cut off."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    return (p.backdrop() + p.nav_button(BACK, S, 36, 'chevron-left.png', 'Close') + right +
            p.label(S, 160, w, 110, title, 'p_large', p.WHITE, 'left', NOLABEL) +
            p.label(S, 268, w, 56, sub, 'p_sub', p.GREY, 'left', '<scroll>true</scroll>' if scroll else NOLABEL))


def _section(p, text, cond, right=''):
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    return ('<control type="group"><width>%d</width><height>96</height><visible>%s</visible>' % (W, cond) +
            p.label(S + 12, 30, w - 24, 60, text, 'p_foot_b', p.GREY) +
            (p.label(S + 12, 30, w - 24, 60, right, 'p_foot', p.GREY, 'right', NOLABEL) if right else '') + '</control>')


def _foot(p, text, cond='', height=160):
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    return ('<control type="group"><width>%d</width><height>%d</height>%s' % (W, height, '<visible>%s</visible>' % cond if cond else '') +
            p.label(S + 12, 20, w - 24, height - 40, text, 'p_cap', p.GREY, 'left', '<wrapmultiline>true</wrapmultiline>') + '</control>')


def _card_row(p, key, tint=None, right=0, extra=''):
    """A grouped row: title and the line under it (in `tint`, or by `<key>tone`). `right` keeps room for buttons."""
    S, W, w = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE
    text_w = w - 48 - right
    if tint:
        sub = p.label(S + 24, 84, text_w, 50, _P(key + 'sub'), 'p_pill_s', tint, 'left', NOLABEL)
    else:
        sub = ''.join(p.label(S + 24, 84, text_w, 50, _P(key + 'sub'), 'p_pill_s', colour, 'left',
                              NOLABEL + '<visible>%s</visible>' % cond)
                      for colour, cond in ((p.GREEN, _is(key + 'tone', 'ok')), (p.GREY, '!' + _is(key + 'tone', 'ok'))))
    return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, ROW + 12, _has(key + 'title')) +
            p.surface(S - 6, 0, w + 12, ROW, 'round.png', p.SURFACE, 32) +
            p.label(S + 24, 22, text_w, 58, _P(key + 'title'), 'p_pill', p.WHITE, 'left', NOLABEL) + sub + extra + '</control>')


def _arrow(p, id, x, glyph, key):
    """A 118-unit ▲ or ▼ button; greyed and disabled at the end of the line."""
    return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>' % (x, (ROW - HIT) // 2, HIT, HIT) +
            p.image(7, 7, 104, 104, p.MEDIA + 'close_disc.png', '2EFFFFFF', '<visible>%s</visible>' % _has(key)) +
            p.image(7, 7, 104, 104, p.MEDIA + 'close_disc.png', '24FFFFFF', '<visible>Control.HasFocus(%d)</visible>' % id) +
            # Owner (build 173): "arrows ... can be larger" and centred: the chevron is drawn centred in its own texture.
            p.image(25, 25, 68, 68, p.MEDIA + glyph, p.WHITE, '<visible>%s</visible>' % _has(key)) +
            p.image(25, 25, 68, 68, p.MEDIA + glyph, p.DIM, '<visible>!%s</visible>' % _has(key)) +
            '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />'
            '<enable>%s</enable></control></control>' % (id, HIT, HIT, _has(key)))


RETRY = 9890
QPREV, QNEXT, HPREV, HNEXT = 9841, 9842, 9905, 9906


def queue_page(p):
    import status_ui as u
    S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
    now=p.surface(S,0,w,230,'round.png',p.SURFACE,p.RADIUS)
    now+=u.text(p,S+30,20,w-190,60,_P('now.title'),'p_pill')+u.text(p,S+w-150,20,120,60,_P('now.percent'),'p_foot_b',PURPLE,'right')
    now+=u.bar(p,S+30,100,w-60,'now.')+u.text(p,S+30,138,w-60,56,_P('now.sub'),'p_cap',p.GREY)
    rows=u.section(p,'WORKING ON NOW',_has('now.title'))+u.group(p,250,now,_has('now.title'))
    rows+=u.section(p,'UP NEXT',_has('line.1.title'))
    for n in range(1,QUEUE_SLOTS+1):
        key='line.%d.'%n
        body=p.surface(S,0,w,180,'round.png',p.SURFACE,p.RADIUS)
        body+=p.surface(S+30,50,76,76,'dot.png',u.BLUE)+u.text(p,S+30,50,76,76,str(n),'p_cap',p.WHITE,'center')
        body+=u.text(p,S+136,20,w-420,60,_P(key+'title'),'p_pill')+u.text(p,S+136,86,w-420,50,_P(key+'sub'),'p_cap',p.GREY)
        body+=_arrow(p,UP+n,S+w-2*HIT-20,'arrow_up.png',key+'up')+_arrow(p,DOWN+n,S+w-HIT-6,'arrow_down.png',key+'down')
        rows+=u.group(p,190,body,_has(key+'title'))
    rows+=u.group(p,100,u.text(p,S,20,w,60,_P('line.more'),'p_cap',p.GREY),_has('line.more'))
    rows+=u.section(p,'WAITING',_has('held.1.title'))
    rows+=''.join(_card_row(p,'held.%d.'%n,p.GREY) for n in range(1,HELD_SLOTS+1))
    rows+=u.section(p,'DOWNLOADING TO GOOGLE DRIVE',_has('drive.1.title'))
    rows+=''.join(_card_row(p,'drive.%d.'%n,p.GREY) for n in range(1,DRIVE_SLOTS+1))
    rows+=u.group(p,124,u.tap(p,QPREV,S,0,w//2,118,'Previous')+u.tap(p,QNEXT,S+w//2,0,w//2,118,'More'),_has('pages'))
    rows+=u.group(p,160,u.text(p,S+10,20,w-20,50,'Moving a video to the top makes it next.','p_cap',p.GREY)+
                  u.text(p,S+10,78,w-20,50,'Faster-start jobs are Ready; they wait behind new movies.','p_cap',p.GREY))
    rows+=u.group(p,100,u.text(p,S,0,w,60,_P('empty'),'p_cap',p.GREY),_has('empty'))
    listing='<control type="grouplist" id="9300"><top>340</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><usecontrolcoords>true</usecontrolcoords>%s</control>'%(W,rows)
    return _window(p,'library queue',BACK,_head(p,'Queue',_P('subtitle'))+listing)


def history_page(p):
    import status_ui as u
    S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
    switch=''
    for i,(key,title) in enumerate(DAYS):
        switch+=p.surface(S+i*w//3,304,w//3-4,110,'round.png',p.SURFACE2,p.RADIUS,'<visible>%s</visible>'%_is('day',key))
        switch+=u.tap(p,DAY+1+i,S+i*w//3,300,w//3,118,title)
    rows=''
    # Separate sections keep unfinished attempts first, regardless of their time.
    for tone,title in (('unfinished',"DIDN'T FINISH"),('finished','FINISHED')):
        rows+=u.section(p,title,_has(tone))
        for n in range(1,HISTORY_SLOTS+1):
            key='h.%d.'%n;bad=tone=='unfinished'
            body=p.surface(S,0,w,290 if bad else 170,'round.png',p.SURFACE,p.RADIUS)
            body+=p.icon(S+30,34,60,'circle-xmark.png' if bad else 'circle-check.png',RED if bad else p.GREEN)
            body+=u.text(p,S+120,22,w-350,60,_P(key+'title'),'p_pill')
            body+=u.text(p,S+w-200,22,170,60,_P(key+'when'),'p_cap',p.GREY,'right')
            body+=u.text(p,S+120,90,w-150,54,_P(key+'result'),'p_cap',p.GREY)
            if bad:
                body+=p.pill_button(RETRY+n,S+120,160,300,124,'Try again',[('','noop')],'glass',extra=u.NOS+'<visible>%s</visible>'%_has(key+'retry'))
            rows+=u.group(p,310 if bad else 180,body,_has(key+'title')+' + '+_is(key+'section',tone))
    rows+=u.group(p,124,u.tap(p,HPREV,S,0,w//2,118,'Previous')+u.tap(p,HNEXT,S+w//2,0,w//2,118,'More'),_has('pages'))
    rows+=u.group(p,160,u.text(p,S,40,w,70,_P('empty'),'p_foot',p.GREY),_has('empty'))
    listing='<control type="grouplist" id="9300"><top>440</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><usecontrolcoords>true</usecontrolcoords>%s</control>'%(W,rows)
    return _window(p,'transfer history',BACK,_head(p,'History','')+switch+listing)


def airplay_page(p):
    """Portrait: opened from an AirPlay notification."""
    S, W, M, w = p.SIDE, p.WIDTH, p.MEDIA, p.WIDTH - 2 * p.SIDE

    def step(n):
        key = 'step.%d.' % n
        icons = ''.join(p.icon(S + 24, 34, 64, glyph, colour, '<visible>%s</visible>' % _is(key + 'tone', tone))
                        for tone, glyph, colour in (('ok', 'circle-check.png', p.GREEN), ('bad', 'circle-xmark.png', RED),
                                                    ('warn', 'circle-info.png', ORANGE)))
        return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, 212, _has(key + 'name')) +
                p.surface(S - 6, 0, w + 12, 200, 'round.png', p.SURFACE, 32) + icons +
                p.label(S + 116, 20, w - 140, 44, _P(key + 'name'), 'p_cap', p.GREY, 'left', NOLABEL) +
                p.label(S + 116, 62, w - 140, 112, _P(key + 'detail'), 'p_pill_s', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>') +
                '</control>')
    tip = ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (W, 340, _has('try')) +
           _section(p, 'What to try', 'true').replace('<control type="group">', '<control type="group"><top>0</top>', 1) +
           '<control type="group"><top>96</top>' + p.surface(S - 6, 0, w + 12, 230, 'round.png', p.SURFACE, 32) +
           p.label(S + 24, 20, w - 48, 190, _P('try'), 'p_pill_s', p.WHITE, 'left', '<wrapmultiline>true</wrapmultiline>') +
           '</control></control>')
    headline = ''.join(p.label(S, 340, w, 70, _P('headline'), 'p_h3', colour, 'left', NOLABEL + '<visible>%s</visible>' % _is('tone', tone))
                       for tone, colour in (('ok', p.GREEN), ('bad', RED)))
    listing = ('<control type="grouplist" id="%d"><left>0</left><top>430</top><width>%d</width><bottom>0</bottom>'
               '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (LIST, W) +
               ''.join(step(n) for n in range(1, STEPS + 1)) + tip + _foot(p, _P('empty'), _has('empty'), 200) + '</control>')
    # Owner (build 173): titles must fit. The page's own name is the large title; the video's (any length) goes under it.
    sub = '[COLOR %s]%s[/COLOR] · %s' % (p.WHITE, _P('title'), _P('when'))
    return _window(p, 'airplay check', BACK, _head(p, 'AirPlay check', sub, scroll=True) + headline + listing)


def airplay_sheet(close_button_1080=None):
    """1080i/IOSAirPlayCheck.xml: the same check as a sheet over the video (Play on TV › Last time), on Fuse's 1920x1080
    canvas with Fuse's fonts, like the Play on TV sheet."""
    if close_button_1080 is None:
        import importlib.util as iu
        import os
        spec = iu.spec_from_file_location('pages_close', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages.py'))
        module = iu.module_from_spec(spec)
        spec.loader.exec_module(module)
        close_button_1080 = module.close_button_1080
    MEDIA, ICONS = 'special://skin/extras/portrait/', 'special://skin/extras/icons/'
    w, row, top = 1400, 120, 40

    def img(x, y, w, h, tex, color='FFFFFFFF', extra='', border=''):
        return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s colordiffuse="%s">%s</texture>%s</control>'
                % (x, y, w, h, ' border="%s"' % border if border else '', color, tex, extra))

    def lab(x, y, w, h, text, font, color='FFFFFFFF', align='left', extra=''):
        return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
                '<align>%s</align><aligny>center</aligny><label>%s</label>%s</control>' % (x, y, w, h, font, color, align, text, extra))

    def step(n):
        key = 'step.%d.' % n
        icons = ''.join(img(40, (row - 52) // 2, 52, 52, ICONS + glyph, colour, '<visible>%s</visible>' % _is(key + 'tone', tone))
                        for tone, glyph, colour in (('ok', 'circle-check.png', 'FF30D158'), ('bad', 'circle-xmark.png', RED),
                                                    ('warn', 'circle-info.png', ORANGE)))
        return ('<control type="group"><top>%d</top><visible>%s</visible>' % (150 + (n - 1) * row, _has(key + 'name')) +
                (img(120, 0, w - 160, 2, MEDIA + 'white.png', '1AFFFFFF') if n > 1 else '') + icons +
                lab(120, 10, 300, 40, _P(key + 'name'), 'font_mini', '99EBEBF5') +
                lab(120, 48, w - 160, 60, _P(key + 'detail'), 'font_main_bold') + '</control>')
    height = 150 + STEPS * row + 160
    body = ('<control type="image"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texture colordiffuse="73000000">%swhite.png</texture></control>' % MEDIA +
            '<control type="button" id="9099"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texturefocus /><texturenofocus />'
            '<onclick>Close</onclick><onfocus>SetFocus(%d)</onfocus></control>' % CLOSE +
            '<control type="group"><centerleft>50%%</centerleft><top>%d</top><width>%d</width>' % (top, w) +
            '<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
            '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>' +
            # As tall as it needs: the "What to try" part only when something went wrong.
            img(0, 0, w, height, MEDIA + 'sheet_l.png', border='40', extra='<visible>%s</visible>' % _has('try')) +
            img(0, 0, w, height - 120, MEDIA + 'sheet_l.png', border='40', extra='<visible>!%s</visible>' % _has('try')) +
            img(36, 40, 76, 76, MEDIA + 'dot.png', '1FFFFFFF') + img(55, 59, 38, 38, MEDIA + 'airplay.png') +
            lab(134, 30, w - 300, 56, _P('title'), 'font_head_bold', 'FFFFFFFF', 'left', '<scroll>true</scroll>') +
            lab(134, 84, w - 300, 40, '%s · %s' % (_P('headline'), _P('when')), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('headline')) +
            lab(134, 84, w - 300, 40, _P('empty'), 'font_mini', '99EBEBF5', 'left', '<visible>%s</visible>' % _has('empty')) +
            close_button_1080(CLOSE, w - 130, 28, '<onclick>Close</onclick>') +
            ''.join(step(n) for n in range(1, STEPS + 1)) +
            '<control type="group"><top>%d</top><visible>%s</visible>' % (150 + STEPS * row + 10, _has('try')) +
            lab(40, 0, 300, 40, 'What to try', 'font_mini', '99EBEBF5') +
            '<control type="textbox"><left>40</left><top>40</top><width>%d</width><height>90</height><font>font_mini</font>'
            '<textcolor>FFFFFFFF</textcolor><label>%s</label></control></control>' % (w - 80, _P('try')) +
            '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: AirPlay check r1 (navigation.patch_skin leaves this marker alone) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>\n') % (CLOSE, body)


def arrow(p, up):
    """A bold chevron pointing up or down (128 px, white; tinted by colordiffuse), centred both ways: its outline
    including the stroke spans the same distance above and below the middle."""
    import math

    def distance(x, y, ax, ay, bx, by):
        t = max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        return math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay))
    half, stroke = 24, 8.5         # the chevron's centre line spans 64 ± half; the stroke adds the same both ways
    a, b, c = ((20, 64 + half), (64, 64 - half), (108, 64 + half)) if up else ((20, 64 - half), (64, 64 + half), (108, 64 - half))

    def pixel(x, y):
        d = min(distance(x + .5, y + .5, *a, *b), distance(x + .5, y + .5, *b, *c))
        return (255, 255, 255, int(255 * max(0, min(1, stroke - d))))
    return p.png(128, 128, pixel)


def files(p):
    return {p.FOLDER + '/' + QUEUE: queue_page(p).encode(), p.FOLDER + '/' + HISTORY: history_page(p).encode(), p.FOLDER + '/' + AIRPLAY: airplay_page(p).encode(),
            '1080i/' + AIRPLAY: airplay_sheet(p.pages.close_button_1080).encode(),
            'extras/portrait/arrow_up.png': arrow(p, True), 'extras/portrait/arrow_down.png': arrow(p, False)}
