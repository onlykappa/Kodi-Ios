"""Approved board 4 (build 194: laid out from docs/design/build-193-measurements.md): one chip per running job, the
chosen job's card (title, step, speed, graph, bar, Peak / Average / Started) and Up next in one grouped card."""
import status_ui as u
WINDOW='IOSTransfers.xml'
BACK,LIST,HISTORY,BAR,OTHER=9001,9300,9002,9711,9720
OTHERS,DONE,NEXT,HIT=6,3,3,118
CARD_TOP=500                       # board 4: the card starts at 246 pt
PLOT=(38,333,817,403)              # inside the card: x, y, plot width, plot height (the axis numbers sit to its right)


def chip(p,n):
    """A 36 pt capsule: white with black text when chosen, #2C2C2E with white text otherwise; the job's colour as a dot."""
    P,k=u.P,'other.%d.'%n
    on='String.IsEqual(Window().Property(%son),true)'%k
    b=p.image(0,0,360,97,p.MEDIA+'pill_96.png',p.WHITE,'<visible>%s</visible>'%on,border=48)
    b+=p.image(0,0,360,97,p.MEDIA+'pill_96.png',u.SURF2,'<visible>%s</visible>'%u.neg(on),border=48)
    b+=p.image(38,38,21,21,p.MEDIA+'avatar_s.png',P(k+'tint'))
    b+='<control type="group"><visible>%s</visible>%s</control>'%(on,u.text(p,75,0,270,97,P(k+'label'),'p_pill','FF000000'))
    b+='<control type="group"><visible>%s</visible>%s</control>'%(u.neg(on),u.text(p,75,0,270,97,P(k+'label'),'p_pill',p.WHITE))
    b+=('<control type="button" id="%d"><left>0</left><top>-10</top><width>360</width><height>118</height><label></label>'
        '<texturefocus /><texturenofocus /></control>')%(OTHER+n)
    return '<control type="group"><width>360</width><height>97</height><visible>%s</visible>%s</control>'%(u.has(k+'label'),b)


def page(p):
    S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
    P=u.P
    head=p.backdrop()+p.nav_button(BACK,S,36,'chevron-left.png','Close')+u.link(p,HISTORY,W-S-300,41,300,118,'History',font='p_body')
    head+=u.text(p,S,160,w,110,'Transfers','p_large')+u.text(p,S,268,w,56,P('headline'),'p_sub',p.GREY)
    chips=('<control type="grouplist"><left>%d</left><top>365</top><width>%d</width><height>97</height><orientation>horizontal</orientation>'
           '<itemgap>21</itemgap><usecontrolcoords>true</usecontrolcoords>'%(S,w)+''.join(chip(p,n) for n in range(1,OTHERS+1))+'</control>')
    px,py,pw,ph=PLOT
    c=u.card(p,S,0,w,994)
    c+=u.text(p,S+38,38,w-76,54,P('title'),'p_h3')
    c+=u.text(p,S+38,97,w-76,51,P('step'),'p_sub',p.GREY)
    c+=('<control type="grouplist"><left>%d</left><top>164</top><width>%d</width><height>110</height><orientation>horizontal</orientation>'
        '<itemgap>16</itemgap><usecontrolcoords>true</usecontrolcoords>'%(S+38,w-76)+
        '<control type="label"><width>auto</width><scroll>false</scroll><height>110</height><font>p_large</font><textcolor>%s</textcolor><label>%s</label></control>'%(p.WHITE,P('number'))+
        '<control type="label"><width>auto</width><scroll>false</scroll><height>90</height><top>20</top><font>p_h3</font><textcolor>%s</textcolor><aligny>bottom</aligny><label>%s</label></control>'%(p.GREY,P('units'))+
        '</control>')
    has_graph=u.has('graph')
    c+=p.image(S+px,py,pw,ph,P('graph'),p.WHITE,'<visible>%s</visible>'%has_graph,'>stretch')
    axis=''.join(u.text(p,S+px+pw+12,py+round(ph*g)-20,w-px-pw-50,40,P('axis%d'%i),'p_cap',p.GREY) for i,g in enumerate((.25,.5,.75)))
    axis+=u.text(p,S+px,py+ph+8,400,40,P('from'),'p_cap',p.GREY)+u.text(p,S+px+pw-300,py+ph+8,300,40,'now','p_cap',p.GREY,'right')
    c+='<control type="group"><visible>%s</visible>%s</control>'%(has_graph,axis)
    c+=u.text(p,S+px,py,pw,ph,P('wait'),'p_sub',p.GREY,'center').replace('<scroll>false</scroll>','<aligny>center</aligny><scroll>false</scroll><visible>%s</visible>'%u.neg(has_graph),1)
    c+=u.id_bar(p,BAR,S+38,817,w-76,16,P('tint'),texture='pill16.png',border=8)
    for i,(title,key) in enumerate((('Peak','peak'),('Average','avg'),('Started','started'))):
        x=S+38+i*(w-76)//3;cw=(w-76)//3-12
        c+=u.text(p,x,860,cw,43,title,'p_foot',p.GREY)+u.text(p,x,903,cw,54,P(key),'p_h3')
    card='<control type="group"><top>%d</top><visible>%s</visible>%s</control>'%(CARD_TOP,u.has('title'),c)
    empty=('<control type="group"><top>%d</top><visible>%s</visible>'%(CARD_TOP,u.neg(u.has('title')))+u.card(p,S,0,w,300)+
           u.text(p,S+38,60,w-76,70,P('empty.title'),'p_h3',p.WHITE,'center')+
           u.paragraph(p,S+38,140,w-76,120,P('empty.text'),'p_foot',align='center')+'</control>')
    rows=u.group(p,99,u.text(p,S+10,0,w-20,62,'UP NEXT','p_pill',p.GREY),u.has('next.1.title'))
    for n in range(1,NEXT+1):
        k='next.%d.'%n
        b=u.row_back(p,k,w,141)+u.text(p,S+38,0,w-458,141,P(k+'title'),'p_body')+u.text(p,S+w-420,0,382,141,P(k+'line'),'p_foot',p.GREY,'right')
        rows+=u.group(p,141,b,u.has(k+'title'))
    listing=('<control type="grouplist" id="9300"><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<usecontrolcoords>true</usecontrolcoords>%s</control>')%(CARD_TOP+994+38,W,rows)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 194: approved board 4 -->\n<window><defaultcontrol always="true">9001</defaultcontrol><controls>'+head+chips+card+empty+listing+'</controls></window>'


def files(p):return {p.FOLDER+'/'+WINDOW:page(p).encode()}
