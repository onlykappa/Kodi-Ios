"""Shared Kodi controls for the build-193 boards. All coordinates are portrait units."""
PURPLE, BLUE, TRACK = 'FFBF5AF2', 'FF0A84FF', 'FF3A3A3C'
HIT = 118
NOS = '<scroll>false</scroll>'
P = lambda k: '$INFO[Window().Property(%s)]' % k
has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k


def text(p, x, y, w, h, value, font='p_foot', tint=None, align='left'):
    return p.label(x, y, w, h, value, font, tint or p.WHITE, align, NOS)


def tap(p, ident, x, y, w, h, title='', tint=None):
    return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<label>%s</label><font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
            '<align>center</align><aligny>center</aligny><scroll>false</scroll><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus>'
            '<texturenofocus /></control>') % (ident,x,y,w,h,p.e(title),tint or p.ACCENT,p.WHITE,p.MEDIA)


def group(p, height, body, cond='true'):
    return '<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>' % (p.WIDTH,height,cond,body)


def section(p, title, cond='true', action=''):
    return group(p,118,text(p,p.SIDE+10,30,p.WIDTH-2*p.SIDE-(300 if action else 20),60,title,'p_foot_b',p.GREY)+action,cond)


def bar(p, x, y, w, key, ident=None):
    return ('<control type="progress"%s><left>%d</left><top>%d</top><width>%d</width><height>11</height>'
            '<info>Window().Property(%spct)</info><texturebg colordiffuse="%s">%swhite.png</texturebg><lefttexture />'
            '<midtexture colordiffuse="%s">%swhite.png</midtexture><righttexture /></control>') % (
                ' id="%d"'%ident if ident else '',x,y,w,key,TRACK,p.MEDIA,P(key+'tint'),p.MEDIA)


def working(p, key, ident, compact=False, menu=None):
    """Poster + one canonical status line, shared by Library and Notifications."""
    S,w,M=p.SIDE,p.WIDTH-2*p.SIDE,p.MEDIA
    h=220 if compact else 360
    body=p.surface(S,0,w,h,'round.png',p.SURFACE,p.RADIUS)
    body+=tap(p,ident,S,0,w,h)
    body+=p.image(S+30,30,140,180 if compact else 210,M+'white.png',p.SURFACE2,diffuse=M+'poster_mask.png')
    body+=p.image(S+30,30,140,180 if compact else 210,P(key+'poster'),p.WHITE,'','>scale',M+'poster_mask.png',background=True)
    x=S+200
    if compact:
        body+=text(p,x,24,w-350,58,P(key+'title'),'p_pill')
        body+=text(p,x,88,w-350,50,P(key+'line'),'p_cap',p.GREY)
        body+=bar(p,x,164,w-280,key)
        if menu:body+=tap(p,menu,S+w-124,0,124,118,'•••',p.GREY)
    else:
        body+=text(p,x,20,w-420,44,'WORKING ON NOW','p_cap',PURPLE)
        body+=text(p,x,68,w-420,62,P(key+'title'),'p_pill')
        body+=text(p,x,136,w-420,50,P(key+'step'),'p_foot',p.GREY)
        body+=p.image(S+w-182,48,150,150,M+'ring_20.png',TRACK)
        body+=p.image(S+w-182,48,150,150,M+P(key+'ring'),P(key+'tint'))
        body+=text(p,S+w-182,48,150,150,P(key+'percent'),'p_foot_b',p.WHITE,'center')
        moving='String.IsEqual(Window().Property(%sstate),running)'%key
        body+=p.image(S+30,250,360,80,P(key+'graph'),p.WHITE,'<visible>'+moving+'</visible>','>stretch')
        body+='<control type="group"><visible>'+moving+'</visible>'+text(p,S+420,262,w-510,54,P(key+'metrics'),'p_foot',p.GREY)+'</control>'
        body+='<control type="group"><visible>!'+moving+'</visible>'+text(p,S+30,262,w-110,54,P(key+'line'),'p_foot',p.GREY)+'</control>'
    body+=p.icon(S+w-60,h-78,32,'chevron-right.png',p.GREY)
    return group(p,h+20,body,has(key+'title'))


def needs(p, key='need.', ident=9004, elevated=False):
    S,w=p.SIDE,p.WIDTH-2*p.SIDE
    body=p.surface(S,0,w,290,'round.png',p.SURFACE2 if elevated else p.SURFACE,p.RADIUS)
    body+=p.surface(S+30,30,80,80,'round_s.png','33FF9F0A',p.RADIUS)
    body+=p.icon(S+46,46,48,'triangle-exclamation.png','FFFF9F0A')
    body+=text(p,S+140,22,w-170,56,P(key+'title'),'p_foot_b')
    body+=text(p,S+140,84,w-170,50,P(key+'text'),'p_cap',p.GREY)
    body+=p.pill_button(ident,S+140,154,300,124,P(key+'button'),[('','noop')],'primary',extra=NOS)
    return group(p,310,body,has(key+'title'))


def graph(p, key, x, y, w, h):
    """Raster is only the plot. Axis, units, time and peak stay sharp Kodi labels."""
    return (p.image(x+70,y+44,w-80,h-100,P(key+'graph'),p.WHITE,'','>stretch')+
            text(p,x,y,160,40,'MB/s','p_cap',p.GREY)+
            text(p,x+w-300,y,300,40,'peak '+P(key+'peak'),'p_cap',p.GREY,'right')+
            ''.join(text(p,x,y+44+i*(h-140)//2,65,40,P(key+'axis%d'%i),'p_cap',p.GREY) for i in range(3))+
            text(p,x+70,y+h-48,(w-80)//2,40,P(key+'from'),'p_cap',p.GREY)+
            text(p,x+70+(w-80)//2,y+h-48,(w-80)//2,40,'now','p_cap',p.GREY,'right'))
