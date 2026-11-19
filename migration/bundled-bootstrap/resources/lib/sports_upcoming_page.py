"""Upcoming, approved board 10: portrait Kodi XML using the shared page controls."""
import sports_edit_button as edit_button
import status_ui as u
import math

WINDOW = 'IOSSportsUpcoming.xml'
BACK, REFRESH, LIST, RETRY, LEAGUES, LEAGUE_PICK = 9001, 9002, 9300, 9003, 9004, 9006
ROW, SLOTS = 45000, 120
PICK_SIZES = range(3, 8)
PICK_IDS = [LEAGUE_PICK + 10 * (size - 3) for size in PICK_SIZES]   # one control id per width form   # the capsule's width follows the league's label length (All, NFL, NCAAB ...)
SCROLL_CLEAR = 720  # Board 11 leaves room below the final day as the header scrolls away.
TITLE_LINE, DETAIL_H, PAD, MIN_ROW = 57, 56, 32, 194
FORMS = range(1, 5)
_STATE_ART = {}


def _line(x,y,ax,ay,bx,by):
    dx,dy=bx-ax,by-ay
    t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-ax-t*dx,y-ay-t*dy)<=1


def _calendar(x,y):
    edges=((4,6,20,6),(20,6,20,20),(20,20,4,20),(4,20,4,6),
           (4,10,20,10),(8,3,8,7),(16,3,16,7))
    return (any(_line(x,y,*edge) for edge in edges) or
            math.hypot(max(8-x,0,x-10),max(14-y,0,y-16))<=1)


def _warning(x,y):
    return any(_line(x,y,*edge) for edge in ((12,3,2,20),(2,20,22,20),(22,20,12,3),(12,10,12,15),(12,17.5,12,18)))


def _states(p):
    out=''
    for state,glyph,fill,tint,ident,title,width,detail_h in (
        ('empty','sports_calendar.png','1FEBEBF5',p.GREY,LEAGUES,'See Leagues',445,56),
        ('error','sports_warning.png','2EFF9F0A',u.ORANGE,RETRY,'Try again',367,112)):
        body=p.image(459,163,161,161,p.MEDIA+'pill_170.png',fill)
        body+=p.image(499,203,81,81,p.MEDIA+glyph,tint)
        body+=u.text(p,p.SIDE,345,972,65,u.P('empty.title'),'p_state_title',align='center')
        for line in range(detail_h//56):
            body+=p.textbox(150,431+line*56,780,56,u.P('empty.text.%d'%line),'p_sub',p.GREY).replace(
                '<autoscroll>','<align>center</align><autoscroll>')
        body+=p.pill_button(ident,(1080-width)//2,431+detail_h+48,width,134,title,[('','noop')],'primary',
                           extra='<animation effect="fade" start="100" end="75" time="0" condition="Control.HasFocus(%d)">Conditional</animation>' % ident)
        out+=u.group(p,760,body,'String.IsEqual(Window().Property(state),%s)' % state)
    return out


def row_height(lines):
    return max(MIN_ROW, PAD * 2 + TITLE_LINE * lines + 13 + DETAIL_H + 4)


def _picker(p):
    """Mockup A: one capsule "League  All ⌄" under the subtitle; it opens the app's choice sheet of the leagues that have games."""
    out = ''
    for size in PICK_SIZES:
        ident = LEAGUE_PICK + 10 * (size - 3)
        width = 196 + 27 * size + 24 + 52
        inside = p.image(0, 13, width, 92, p.MEDIA + 'pill_96.png', p.SURFACE2, border=46)
        inside += u.tap(p, ident, 0, 0, width, 118)
        inside += u.text(p, 34, 13, 170, 92, 'League', 'p_pill')
        inside += u.text(p, 190, 13, 27 * size + 30, 92, u.P('league.label'), 'p_pill', p.ACCENT)
        inside += p.icon(width - 24 - 36, 13 + 28, 36, 'chevron-down.png', p.ACCENT)
        out += ('<control type="group"><left>%d</left><width>%d</width><height>118</height>'
                '<visible>String.IsEqual(Window().Property(league.size),%d)</visible>'
                '<animation effect="fade" start="100" end="70" time="0" condition="Control.HasFocus(%d)">Conditional</animation>%s</control>') % (p.SIDE, width, size, ident, inside)
    return u.group(p, 140, out, u.has('league.label'))


def game_row(p, key, ident, lines, width):
    """One game row (time, title, league logo and the small line, chevron) at the height its title lines need; the hub's Up next reuses it."""
    h = row_height(lines)
    title_h = lines*TITLE_LINE
    main_h = title_h+13+DETAIL_H
    top = (h-main_h)//2
    b = u.row_back(p,key,width,h)
    b += u.tap(p,ident,p.SIDE,0,width,h)
    # The time as the mockups show it: "4:30" large and blue, "PM" under it in grey, and "in 44 min" under that when the game is close.
    for with_soon in (True,False):
        visible=u.has(key+'soon') if with_soon else u.neg(u.has(key+'soon'))
        y0 = (h-(136 if with_soon else 96))//2
        t = p.label(p.SIDE+38,y0,232,56,u.P(key+'clock.main'),'p_h3',p.ACCENT,extra=u.NOS)
        t += u.text(p,p.SIDE+38,y0+56,232,40,u.P(key+'clock.ampm'),'p_foot',p.GREY)
        if with_soon:
            t += u.text(p,p.SIDE+38,y0+96,232,40,u.P(key+'soon'),'p_foot',p.GREY)
        b += '<control type="group"><visible>%s</visible>%s</control>' % (visible,t)
    b += p.textbox(355,top,570,title_h,u.P(key+'title'),'p_h3')
    # A label-only horizontal group gives the league badge its natural width without clipping.
    # The league's real logo on a small light tile (owner: logos, not letters); a neutral ring when it has none.
    badge = ('<control type="group"><width>56</width><height>56</height>%s%s%s</control>') % (
        p.image(0,0,56,56,p.MEDIA+'r21.png','FFF2F2F7',border=21),
        p.image(7,7,42,42,u.P(key+'logo'),p.WHITE,'<aspectratio>keep</aspectratio><visible>%s</visible>'%u.has(key+'logo')),
        p.image(16,16,24,24,p.MEDIA+'ring_20.png','FF8E8E93','<visible>!%s</visible>'%u.has(key+'logo')))
    badge += ('<control type="label"><width>430</width><height>56</height><label>%s</label><font>p_foot</font>'
              '<textcolor>%s</textcolor><aligny>center</aligny></control>') % (u.P(key+'sources'),p.GREY)
    b += ('<control type="grouplist"><left>355</left><top>%d</top><width>570</width><height>56</height>'
          '<orientation>horizontal</orientation><itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>%s</control>') % (top+title_h+13,badge)
    b += u.glyph(p,960,(h-32)//2,32,'chevron-right.png',p.GREY)
    return b


def _rows(p):
    out = ''
    width = p.WIDTH - 2*p.SIDE
    for n in range(SLOTS):
        key = 'row.%d.' % n
        heading = (u.text(p,p.SIDE,43,width-250,70,u.P(key+'day'),'p_h2') +
                   u.text(p,p.WIDTH-p.SIDE-240,43,240,70,u.P(key+'day.count'),'p_sub',p.GREY,'right'))
        out += u.group(p,121,heading.replace('<top>43</top>','<top>29</top>'),'String.IsEqual(Window().Property(%sfirstday),true)' % key)
        out += u.group(p,134,heading,u.has(key+'day')+' + !String.IsEqual(Window().Property(%sfirstday),true)' % key)
        for lines in FORMS:
            h = row_height(lines)
            out += u.group(p,h,game_row(p,key,ROW+n*len(FORMS)+lines-1,lines,width),'String.IsEqual(Window().Property(%slines),%d)' % (key,lines))
    return out


def page(p):
    header = p.nav_button(BACK,32,5,'chevron-left.png','noop')
    header += p.nav_button(REFRESH,940,5,p.MEDIA+'hdr_refresh.png','noop',glyph_size=60).replace(p.WHITE,p.ACCENT)
    header += edit_button.xml(p,940-20-edit_button.W,22)
    header += u.text(p,p.SIDE,124,972,110,'Upcoming','p_large')
    header += u.text(p,p.SIDE,239,972,51,u.P('subtitle'),'p_sub',p.GREY)
    content = u.group(p,315,header) + _picker(p) + _rows(p)
    content += _states(p)
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s%s</control>') % (
                 LIST,content,u.group(p,SCROLL_CLEAR,p.image(0,0,1,SCROLL_CLEAR,p.MEDIA+'white.png','00000000')))
    body += p.tabbar('library')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports Upcoming, approved board 10 -->\n'
            '<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>') % body


def files(p):
    if not _STATE_ART:
        _STATE_ART.update({'sports_calendar.png':p.shape(96,_calendar),'sports_warning.png':p.shape(96,_warning)})
    files={p.FOLDER+'/'+WINDOW:page(p).encode()}
    files.update({'extras/portrait/'+name:data for name,data in _STATE_ART.items()})
    return files
