"""Upcoming, approved board 10: portrait Kodi XML using the shared page controls."""
import status_ui as u

WINDOW = 'IOSSportsUpcoming.xml'
BACK, REFRESH, LIST, RETRY, LEAGUES = 9001, 9002, 9300, 9003, 9004
CHIP, CHIPS, ROW, SLOTS = 40000, 16, 45000, 120
CHIP_LINES = 4
SCROLL_CLEAR = 720  # Board 11 leaves room below the final day as the header scrolls away.
TITLE_LINE, DETAIL_H, PAD, MIN_ROW = 57, 56, 32, 194
FORMS = range(1, 5)


def row_height(lines):
    return max(MIN_ROW, PAD * 2 + TITLE_LINE * lines + 13 + DETAIL_H + 4)


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
                 '<visible>String.IsEqual(Window().Property(chipline.%d),true)</visible>%s</control>') % (p.SIDE,p.WIDTH-2*p.SIDE,line,out)
    return rows


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
            title_h = lines*TITLE_LINE
            main_h = title_h+13+DETAIL_H
            top = (h-main_h)//2
            b = u.row_back(p,key,width,h)
            b += u.tap(p,ROW+n*len(FORMS)+lines-1,p.SIDE,0,width,h)
            for with_soon in (True,False):
                visible=u.has(key+'soon') if with_soon else u.neg(u.has(key+'soon'))
                b += p.label(p.SIDE+38,(h-(96 if with_soon else 56))//2,232,56,u.P(key+'clock'),'p_h3',p.ACCENT,extra=u.NOS+'<visible>'+visible+'</visible>')
            b += u.text(p,p.SIDE+38,(h-96)//2+56,232,40,u.P(key+'soon'),'p_foot',p.GREY)
            b += p.textbox(355,top,570,title_h,u.P(key+'title'),'p_h3')
            # A label-only horizontal group gives the league badge its natural width without clipping.
            badge = ('<control type="button"><width min="102">auto</width><height>56</height><label>%s</label>'
                     '<font>p_foot_b</font><textoffsetx>24</textoffsetx><textcolor>%s</textcolor>'
                     '<disabledcolor>%s</disabledcolor><enable>false</enable>'
                     '<texturefocus /><texturenofocus border="21" colordiffuse="%s">%sr21.png</texturenofocus></control>') % (
                         u.P(key+'league'),p.WHITE,p.WHITE,p.SURFACE2,p.MEDIA)
            badge += ('<control type="label"><width>430</width><height>56</height><label>%s</label><font>p_foot</font>'
                      '<textcolor>%s</textcolor><aligny>center</aligny></control>') % (u.P(key+'sources'),p.GREY)
            b += ('<control type="grouplist"><left>355</left><top>%d</top><width>570</width><height>56</height>'
                  '<orientation>horizontal</orientation><itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>%s</control>') % (top+title_h+13,badge)
            b += u.glyph(p,960,(h-32)//2,32,'chevron-right.png',p.GREY)
            out += u.group(p,h,b,'String.IsEqual(Window().Property(%slines),%d)' % (key,lines))
    return out


def page(p):
    header = p.nav_button(BACK,32,5,'chevron-left.png','noop')
    header += p.nav_button(REFRESH,940,5,p.MEDIA+'hdr_refresh.png','noop',glyph_size=60).replace(p.WHITE,p.ACCENT)
    header += u.text(p,p.SIDE,124,972,110,'Upcoming','p_large')
    header += u.text(p,p.SIDE,239,972,51,u.P('subtitle'),'p_sub',p.GREY)
    content = u.group(p,315,header) + _chips(p) + _rows(p)
    content += ('<control type="group"><height>600</height><visible>%s</visible>%s%s%s</control>') % (
        u.has('empty.title'),u.text(p,108,170,864,90,u.P('empty.title'),'p_h2',align='center'),
        p.textbox(150,280,780,150,u.P('empty.text'),'p_sub',p.GREY),
        p.pill_button(RETRY,270,470,540,134,'Try again',[('','noop')],'primary',extra='<visible>String.IsEqual(Window().Property(state),error)</visible>')+
        p.pill_button(LEAGUES,270,470,540,134,'See Leagues',[('','noop')],'primary',extra='<visible>String.IsEqual(Window().Property(state),empty)</visible>'))
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s%s</control>') % (
                 LIST,content,u.group(p,SCROLL_CLEAR,p.image(0,0,1,SCROLL_CLEAR,p.MEDIA+'white.png','00000000')))
    body += p.tabbar('library')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports Upcoming, approved board 10 -->\n'
            '<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>') % body


def files(p):
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
