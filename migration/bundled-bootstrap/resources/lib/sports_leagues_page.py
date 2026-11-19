"""Leagues grouped by sport: approved boards 16–17 and the board 20 provider failure."""
import status_ui as u
import sports_edit_button as edit_button

WINDOW = 'IOSSportsLeagues.xml'
BACK, REFRESH, RETRY, LIST = 9001, 9002, 9003, 9300
ROW, SLOTS = 50000, 80
TITLE_LINE, DETAIL_LINE, PAD, MIN_ROW = 57, 52, 27, 183
FORMS = tuple((title, detail) for title in range(1, 5) for detail in range(1, 5))
SCROLL_CLEAR = 720
LOGO_TILE, LOGO_PAD, LOGO_BG = 118, 14, 'FFF2F2F7'   # a 44 pt light tile; the logo sits 5 pt inside it


def row_height(title, detail):
    return max(MIN_ROW, PAD * 2 + title * TITLE_LINE + 3 + detail * DETAIL_LINE)


def _rows(p):
    out = ''
    for n in range(SLOTS):
        key = 'row.%d.' % n
        heading = (u.text(p,p.SIDE,43,690,70,u.P(key+'sport'),'p_h2') +
                   u.text(p,774,43,252,70,u.P(key+'sport.count'),'p_sub',p.GREY,'right'))
        out += u.group(p,110,heading.replace('<top>43</top>','<top>19</top>'),u.has(key+'sport')+
                       ' + String.IsEqual(Window().Property(%sfirstsport),true)' % key)
        out += u.group(p,134,heading,u.has(key+'sport')+
                       ' + !String.IsEqual(Window().Property(%sfirstsport),true)' % key)
        for form,(title,detail) in enumerate(FORMS):
            h = row_height(title,detail)
            text_h = title*TITLE_LINE + 3 + detail*DETAIL_LINE
            top = (h-text_h)//2
            body = u.row_back(p,key,972,h)
            body += u.tap(p,ROW+n*len(FORMS)+form,p.SIDE,0,972,h)
            # The league's real logo on a light rounded tile (owner: "I want the real logos, not just letters"); a league with
            # no logo gets a neutral ring on the same tile, never letters (sports_logos.py).
            top_t = (h-LOGO_TILE)//2
            body += p.image(92,top_t,LOGO_TILE,LOGO_TILE,p.MEDIA+'round.png',LOGO_BG,border=32)
            body += p.image(92+LOGO_PAD,top_t+LOGO_PAD,LOGO_TILE-2*LOGO_PAD,LOGO_TILE-2*LOGO_PAD,u.P(key+'logo'),p.WHITE,
                            '<aspectratio>keep</aspectratio><visible>%s</visible>'%u.has(key+'logo'))
            body += p.image(92+38,top_t+38,LOGO_TILE-76,LOGO_TILE-76,p.MEDIA+'ring_20.png','FF8E8E93',
                            '<visible>!%s</visible>'%u.has(key+'logo'))
            body += p.textbox(242,top,680,title*TITLE_LINE,u.P(key+'title'),'p_h3')
            body += p.textbox(242,top+title*TITLE_LINE+3,680,detail*DETAIL_LINE,u.P(key+'detail'),'p_sub',p.GREY)
            body += u.glyph(p,960,(h-32)//2,32,'chevron-right.png',p.GREY)
            out += u.group(p,h,body,'String.IsEqual(Window().Property(%sform),%d)' % (key,form))
    return out


def _error(p):
    body = p.image(459,163,161,161,p.MEDIA+'pill_170.png','2EFF9F0A')
    body += p.image(499,203,81,81,p.MEDIA+'sports_warning.png',u.ORANGE)
    body += u.text(p,p.SIDE,345,972,65,u.P('error.title'),'p_state_title',align='center')
    for n in range(2):
        body += p.textbox(150,431+n*56,780,56,u.P('error.text.%d'%n),'p_sub',p.GREY).replace(
            '<autoscroll>','<align>center</align><autoscroll>')
    body += p.pill_button(RETRY,356,591,367,134,'Try again',[('','noop')],'primary',
                         extra='<animation effect="fade" start="100" end="75" time="0" condition="Control.HasFocus(%d)">Conditional</animation>'%RETRY)
    return u.group(p,760,body,'String.IsEqual(Window().Property(state),error)')


def page(p):
    header = p.nav_button(BACK,32,5,'chevron-left.png','noop')
    header += p.nav_button(REFRESH,940,5,p.MEDIA+'hdr_refresh.png','noop',glyph_size=60).replace(p.WHITE,p.ACCENT)
    header += edit_button.xml(p,940-20-edit_button.W,22)
    header += u.text(p,p.SIDE,124,972,110,'Leagues','p_large')
    header += u.text(p,p.SIDE,239,972,51,u.P('subtitle'),'p_sub',p.GREY)
    empty = u.group(p,118,u.text(p,p.SIDE,30,972,60,u.P('empty.text'),'p_sub',p.GREY,'center'),u.has('empty.text'))
    content = u.group(p,315,header) + _rows(p) + _error(p) + empty
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s%s</control>') % (
                 LIST,content,u.group(p,SCROLL_CLEAR,p.image(0,0,1,SCROLL_CLEAR,p.MEDIA+'white.png','00000000')))
    body += p.tabbar('library')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Sports Leagues, approved boards 16, 17 and 20 -->\n'
            '<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>') % body


def files(p):
    # The existing Upcoming generator owns the shared warning mask; portrait builds it before this page.
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
