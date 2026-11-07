"""Approved board 4: selectable job chips and a single live graph."""
import status_ui as u
WINDOW='IOSTransfers.xml'
BACK,LIST,HISTORY,BAR,OTHER=9001,9300,9002,9711,9720
OTHERS,DONE,NEXT,HIT=6,3,3,118


def page(p):
    S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
    P=u.P
    head=p.backdrop()+p.nav_button(BACK,S,36,'chevron-left.png','Close')+u.tap(p,HISTORY,W-S-260,31,260,118,'History')
    head+=u.text(p,S,160,w,110,'Transfers','p_large')+u.text(p,S,268,w,56,P('headline'),'p_sub',p.GREY)
    # A horizontal grouplist scrolls if more jobs run than fit on the line.
    chips='<control type="grouplist"><left>%d</left><top>350</top><width>%d</width><height>124</height><orientation>horizontal</orientation><itemgap>16</itemgap><usecontrolcoords>true</usecontrolcoords>'%(S,w)+''.join(
        '<control type="group"><width>440</width><height>124</height><visible>%s</visible>%s</control>'%(u.has('other.%d.label'%n),
        p.pill_button(OTHER+n,0,0,440,124,P('other.%d.label'%n),[('','noop')],'glass',extra=u.NOS)) for n in range(1,OTHERS+1))+'</control>'
    card=p.surface(S,500,w,1050,'round.png',p.SURFACE,p.RADIUS)
    card+=u.text(p,S+30,520,w-60,58,P('title'),'p_pill')
    card+=u.text(p,S+30,584,w-60,54,P('step'),'p_foot',p.GREY)
    card+=u.text(p,S+30,650,310,124,P('number'),'p_large')
    card+=u.text(p,S+350,698,w-380,60,P('units'),'p_foot',p.GREY)
    card+=u.graph(p,'',S+30,800,w-60,420)+u.bar(p,S+30,1240,w-60,'',BAR)
    card+=u.text(p,S+30,1270,w-60,54,P('line'),'p_cap',p.GREY)
    for i,(title,key) in enumerate((('Peak','peak'),('Average','avg'),('Started','started'))):
        x=S+30+i*(w-60)//3;cw=(w-60)//3-10
        card+=u.text(p,x,1360,cw,44,title,'p_cap',p.GREY)+u.text(p,x,1410,cw,60,P(key),'p_foot_b')
    card='<control type="group"><visible>%s</visible>%s</control>'%(u.has('title'),card)
    empty='<control type="group"><visible>!%s</visible>'%u.has('title')+u.text(p,S,550,w,80,P('empty.title'),'p_h3')+u.text(p,S,640,w,60,P('empty.text'),'p_cap',p.GREY)+'</control>'
    rows=u.section(p,'UP NEXT',u.has('next.1.title'))
    for n in range(1,NEXT+1):
        k='next.%d.'%n
        rows+=u.group(p,150,u.text(p,S+30,8,w-60,60,P(k+'title'),'p_pill')+u.text(p,S+30,72,w-60,50,P(k+'line'),'p_cap',p.GREY),u.has(k+'title'))
    listing='<control type="grouplist" id="9300"><top>1570</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><usecontrolcoords>true</usecontrolcoords>%s</control>'%(W,rows)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 193 approved status boards -->\n<window><defaultcontrol always="true">9001</defaultcontrol><controls>'+head+chips+card+empty+listing+'</controls></window>'


def files(p):return {p.FOLDER+'/'+WINDOW:page(p).encode()}
