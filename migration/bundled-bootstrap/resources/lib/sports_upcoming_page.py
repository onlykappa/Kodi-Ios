"""Upcoming, approved board 10: portrait Kodi XML using the shared page controls."""
import sports_edit_button as edit_button
import status_ui as u
import math

WINDOW = 'IOSSportsUpcoming.xml'
BACK, REFRESH, LIST, RETRY, LEAGUES = 9001, 9002, 9300, 9003, 9004
CHIP, CHIPS, ROW, SLOTS = 40000, 16, 45000, 120
CHIP_LINES = 1   # one row that scrolls sideways (owner: no stranded second line)
SCROLL_CLEAR = 720  # Board 11 leaves room below the final day as the header scrolls away.
TITLE_LINE, DETAIL_H, PAD, MIN_ROW = 57, 56, 32, 194
FORMS = range(1, 3)   # 1 two teams, 2 an event with a title only (sports_rows.FORMS)
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


ROW_H, TIME_W = 228, 216   # 85 pt (approved mockup); the middle column holds "10:00 PM" at 15 pt
LOGO = 86                    # 32 pt


def row_height(form=1):
    return ROW_H


def _chips(p):
    rows = ''
    for line in range(CHIP_LINES):
        out = ''
        for n in range(CHIPS):
            key = 'chip.%d.' % n
            for size in range(2, 9):
                width = 126 + (size-2)*24
                ident = CHIP+line*CHIPS*7+n*7+size-2
                inside = p.image(0,13,width,92,p.MEDIA+'pill_96.png',u.P(key+'fill'),border=46)
                inside += u.tap(p,ident,0,0,width,118)
                inside += u.text(p,0,13,width,92,u.P(key+'label'),'p_pill',u.P(key+'textcolor'),'center')
                out += ('<control type="group"><width>%d</width><height>118</height>'
                        '<visible>String.IsEqual(Window().Property(%ssize),%d) + String.IsEqual(Window().Property(%sline),%d)</visible>'
                        '<animation effect="fade" start="100" end="70" time="0" condition="Control.HasFocus(%d)">Conditional</animation>%s</control>') % (width,key,size,key,line,ident,inside)
        rows += ('<control type="grouplist"><left>%d</left><width>%d</width><height>118</height>'
                 '<orientation>horizontal</orientation><itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>'
                 '<visible>String.IsEqual(Window().Property(chipline.%d),true)</visible>%s</control>') % (p.SIDE,p.WIDTH-p.SIDE,line,out)   # runs to the screen edge: the chips that do not fit are cut by the edge and scroll in
    return rows


def game_row(p, key, ident, form, width):
    """One game row, the approved Apple Sports layout (docs/design/sports-list-rows.html): form 1 is two teams (logo, short name, record under it)
    with the league tag over the start time between them; form 2 (a tournament or race: no second side) is its wrapped title and the same tag and time.
    Type sizes are the policy's three: time 15 pt (p_pill), name 13 pt (p_foot_b), record and tag 11 pt (p_cap). The hub's Up next reuses it."""
    h = ROW_H
    colw = (width - TIME_W) // 2
    mid = p.SIDE + colw
    b = u.row_back(p, key, width, h)
    b += u.tap(p, ident, p.SIDE, 0, width, h)
    if form == 1:
        for side, x in (('away', p.SIDE), ('home', mid + TIME_W)):
            k = key + side + '.'
            lx = x + (colw - LOGO) // 2
            b += p.image(lx, 28, LOGO, LOGO, u.P(k + 'logo'), p.WHITE, '<aspectratio>keep</aspectratio><visible>%s</visible>' % u.has(k + 'logo'))
            b += p.image(lx + 23, 51, 40, 40, p.MEDIA + 'ring_20.png', 'FF8E8E93', '<visible>%s</visible>' % u.neg(u.has(k + 'logo')))
            b += u.text(p, x, 120, colw, 46, u.P(k + 'name'), 'p_foot_b', p.WHITE, 'center')
            b += u.text(p, x, 166, colw, 40, u.P(k + 'rec'), 'p_cap', p.GREY, 'center')
        tx = mid
    else:
        b += p.textbox(p.SIDE + 43, 36, width - TIME_W - 130, 156, u.P(key + 'title'), 'p_foot_b', p.WHITE)
        tx = p.SIDE + width - TIME_W - 30
    b += u.text(p, tx, 38, TIME_W, 40, u.P(key + 'tag'), 'p_cap', p.GREY, 'center')
    b += u.text(p, tx, 80, TIME_W, 56, u.P(key + 'clock'), 'p_pill', p.WHITE, 'center')
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
    content = u.group(p,315,header) + _chips(p) + _rows(p)
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
