"""Board 5; shared live cards, queue link, and the existing earlier messages."""
import status_ui as u


def page(p):
    S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
    head=p.backdrop()+p.nav_button(9001,S,36,'chevron-left.png','Close')+u.tap(p,9002,W-S-260,31,260,118,'Clear All')
    head+=u.text(p,S,160,w,110,'Notifications','p_large')
    # Existing filter semantics, with ≥44 pt hit targets.
    for i,(key,title) in enumerate(p.NOTICE_FILTERS):head+=u.tap(p,9101+i,S+i*w//4,290,w//4,118,title)
    rows=u.section(p,'RUNNING NOW',u.has('live'))
    for key,ident,menu in [('prepare.',9433,9460),('up.',9432,9461)]+[('dl.%d.'%n,9435+n,9461+n) for n in range(1,5)]:
        rows+=u.working(p,key,ident,compact=True,menu=menu)
    rows+=u.group(p,118,u.tap(p,9440,S,0,w,118,u.P('next.link')),u.has('next.link'))
    rows+=u.section(p,'EARLIER',u.has('has.msg'))
    for n in range(1,p.NOTICE_ROWS+1):
        key='msg.%d.'%n
        body=p.surface(S,0,w,180,'round.png',p.SURFACE,p.RADIUS)+u.tap(p,9500+n,S,0,w,180)
        body+=p.image(S+8,78,16,16,p.MEDIA+'dot.png',u.BLUE,'<visible>'+u.has(key+'unread')+'</visible>')
        body+=p.surface(S+36,36,86,86,'round_s.png',u.P(key+'tint'),p.RADIUS)+p.icon(S+56,56,46,p.ICONS+u.P(key+'icon'))
        body+=u.text(p,S+150,22,w-330,58,u.P(key+'title'),'p_foot_b')
        body+=u.text(p,S+150,86,w-180,56,u.P(key+'text'),'p_cap',p.GREY)
        body+=u.text(p,S+w-150,22,130,58,u.P(key+'ago'),'p_cap',p.GREY,'right')
        rows+=u.group(p,190,body,u.has(key+'title'))
    rows+=u.group(p,180,u.text(p,S,50,w,80,"You're all caught up",'p_h3',p.GREY),u.has('empty'))
    body=head+'<control type="grouplist" id="9300"><top>420</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%W+rows+'</control>'
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 193 approved status boards -->\n<window><defaultcontrol always="true">9001</defaultcontrol><controls>'+body+'</controls></window>'
