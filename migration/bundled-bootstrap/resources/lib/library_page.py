"""Build 193 Library status and movie sheets, approved boards 1–3 and 9."""
WINDOW = 'IOSLibraryStatus.xml'
ITEM = 'IOSLibraryItem.xml'
FILTERS = (('ready', 'Ready'), ('working', 'Working'), ('waiting', 'Up next'), ('kept', 'Kept'))   # buttons 9101-9104
LIST, BACK, CHECK = 9300, 9001, 9002
EDIT = 9003   # Waiting › Edit order (the Queue)
HIT = 118
PURPLE = 'FFBF5AF2'
BLUE = 'FF0A84FF'


SLOTS, SLOT, WORK, NEED, MORE, PREVIOUS = 40, 9400, 9005, 9004, 9050, 9051


def page(p):
    import status_ui as u
    W,S,w=p.WIDTH,p.SIDE,p.WIDTH-2*p.SIDE
    P=u.P
    summary=p.surface(S,0,w,270,'round.png',p.SURFACE,p.RADIUS)
    summary+=u.text(p,S+30,16,340,60,P('headline'),'p_h3')
    summary+=u.text(p,S+390,16,w-420,60,P('remaining'),'p_foot',p.GREY,'right')
    # Overlaid cumulative fills form one segmented bar, using Kodi progress sizing.
    summary+=p.image(S+30,98,w-60,16,p.MEDIA+'white.png','FF8E8E93')
    for key,tint in (('next',BLUE),('working',PURPLE),('ready',p.GREEN)):
        summary+=('<control type="progress"><left>%d</left><top>98</top><width>%d</width><height>16</height>'
                  '<info>Window().Property(summary.%s)</info><texturebg /><lefttexture />'
                  '<midtexture colordiffuse="%s">%swhite.png</midtexture><righttexture /></control>')%(S+30,w-60,key,tint,p.MEDIA)
    for i,(key,title) in enumerate((('ready','Ready'),('working','Working'),('next','Up next'),('kept','Kept'))):
        x=S+i*w//4
        summary+=p.surface(x+5,132,w//4-10,124,'round_s.png',p.SURFACE2,p.RADIUS)
        summary+=u.tap(p,9101+i,x,132,w//4,124)
        summary+=u.text(p,x,132,w//4,54,P('count.'+key),'p_h3',{'ready':p.GREEN,'working':PURPLE,'next':p.ACCENT,'kept':p.GREY}[key],'center')
        summary+=u.text(p,x,190,w//4,48,title,'p_cap',p.GREY,'center')
    rows=''
    for n in range(SLOTS):
        key='row.%d.'%n
        rows+=u.section(p,P(key+'section'),u.has(key+'section'))
        body=''.join(p.surface(S,0,w,180,texture,p.SURFACE,43 if pos!='mid' else 0,'<visible>String.IsEqual(Window().Property(%spos),%s)</visible>'%(key,pos)) for pos,texture in (('only','row_only.png'),('first','row_first.png'),('mid','white.png'),('last','row_last.png')))
        body+=u.tap(p,SLOT+n,S,0,w,180)
        body+=p.image(S+24,18,96,144,P(key+'poster'),p.WHITE,'','>scale',p.MEDIA+'poster_mask.png',background=True)
        body+=p.surface(S+28,48,76,76,'dot.png',BLUE,0,'<visible>'+u.has(key+'number')+'</visible>')
        body+=u.text(p,S+28,48,76,76,P(key+'number'),'p_cap',p.WHITE,'center')
        body+=u.text(p,S+150,22,w-240,58,P(key+'title'),'p_pill')
        body+=u.text(p,S+150,86,w-240,50,P(key+'sub'),'p_cap',p.GREY)
        body+=p.icon(S+w-70,62,54,'circle-check.png',p.GREEN,'<visible>String.IsEqual(Window().Property(%sstate),ready)</visible>'%key)
        body+='<control type="group"><visible>String.IsEqual(Window().Property(%sstate),downloading) | String.IsEqual(Window().Property(%sstate),uploading)</visible>'%(key,key)+u.bar(p,S+150,152,w-260,key)+'</control>'
        rows+=u.group(p,180,body,u.has(key+'title'))
    listing=('<control type="grouplist" id="9300"><top>330</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
             '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%W+
             u.needs(p)+u.working(p,'work.',WORK)+u.group(p,290,summary)+
             u.group(p,118,u.tap(p,EDIT,W-S-270,0,270,118,'Edit order'),u.has('queue'))+
             rows+u.group(p,124,u.tap(p,PREVIOUS,S,0,w//2,118,'Previous')+u.tap(p,MORE,S+w//2,0,w//2,118,'More'),u.has('pages'))+
             u.group(p,150,u.text(p,S,30,w,60,P('empty'),'p_foot',p.GREY),u.has('empty'))+'</control>')
    body=p.backdrop()+p.nav_button(BACK,S,36,'chevron-left.png',[('String.IsEqual(Window().Property(filter),all)','Close')])
    body+=p.nav_button(CHECK,W-S-108,36,'arrows-rotate.png','noop')
    body+=u.text(p,S,160,w,110,'Library status','p_large')+u.text(p,S,268,w,56,P('sub'),'p_sub',p.GREY)+listing
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 193 approved status boards -->\n<window><defaultcontrol always="true">9001</defaultcontrol><controls>'+body+'</controls></window>'


CARD_FACTS = 5      # rows under the speed card (library_rows.FACTS)
TONES = (('ok', 'FF30D158'), ('warn', 'FFFF9F0A'), ('plain', None), ('conv', 'FFBF5AF2'), ('down', 'FF0A84FF'))


def item_sheet(p):
    import status_ui as u
    W,S,w,M=p.WIDTH,p.SIDE,p.WIDTH-2*p.SIDE,p.MEDIA
    P=u.P;top=140
    body=u.tap(p,9099,0,0,W,p.HEIGHT)
    body+=p.image(0,top,W,p.HEIGHT,M+'sheet_bg.png',p.SURFACE,border=102)
    body+=p.image(W//2-54,top+22,108,14,M+'dot.png','FF8E8E93')
    body+=p.image(S,top+70,172,258,M+'white.png',p.SURFACE2,diffuse=M+'poster_mask.png')
    body+=p.image(S,top+70,172,258,P('poster'),p.WHITE,'','>scale',M+'poster_mask.png',background=True)
    body+=u.text(p,S+210,top+90,w-350,80,P('title'),'p_h2')
    body+=u.text(p,S+210,top+180,w-230,58,P('quality'),'p_sub',p.GREY)
    body+=p.close_button(9200,W-S-118,top+60,navigation='<onclick>Close</onclick>')
    for i in range(3):
        key='step%d.'%i;x=S+i*(w+16)//3;cw=(w-32)//3
        body+=u.bar(p,x,top+380,cw,key)
        body+=u.text(p,x,top+410,cw,54,P(key+'label'),'p_cap',p.GREY)
    card=p.surface(S,0,w,680,'round.png',p.SURFACE2,p.RADIUS)
    card+=u.text(p,S+30,20,w-60,64,'Right now '+P('card.now'),'p_h3')
    card+=u.text(p,S+30,90,w-60,50,P('card.left'),'p_foot',p.GREY)
    card+=u.graph(p,'card.',S+30,164,w-60,340)
    for i,(title,key) in enumerate((('Average','avg'),('Done','done'),('Started','started'))):
        x=S+30+i*(w-60)//3;cw=(w-60)//3-10
        card+=u.text(p,x,530,cw,44,title,'p_cap',p.GREY)+u.text(p,x,580,cw,58,P('card.'+key),'p_foot_b')
    body+='<control type="group"><top>%d</top><visible>%s</visible>%s</control>'%(top+500,u.has('card'),card)
    body+=u.text(p,S,top+1220,w,56,P('sentence'),'p_cap',p.GREY)
    facts=''
    for n in range(CARD_FACTS):
        key='fact%d.'%n;y=n*130
        facts+=u.text(p,S+30,y,330,130,P(key+'label'),'p_sub',p.GREY)
        facts+=u.text(p,S+370,y,w-400,130,P(key+'value'),'p_sub',P(key+'tint'),'right')
    body+='<control type="group"><top>%d</top><visible>!%s</visible>'%(top+500,u.has('card'))+p.surface(S,0,w,650,'round.png',p.SURFACE2,p.RADIUS)+facts+'</control>'
    body+='<control type="group"><top>%d</top>'%(top+1300)+u.needs(p,elevated=True)+'</control>'
    for n in range(3):
        # Two equal capsules as approved; exceptional queue actions retain the third row.
        x=S+n*(w+24)//2;y=p.HEIGHT-180
        if n==2:x=S;y-=150
        body+=p.pill_button(9201+n,x,y,(w-24)//2 if n<2 else w,124,('[COLOR '+P('action%d.colour'%(n+1))+']'+P('action%d.label'%(n+1))+'[/COLOR]' if n else P('action1.label')),[('','noop')],
                            'primary' if n==0 else 'glass',extra=u.NOS+'<visible>%s</visible>'%u.has('action%d.label'%(n+1)))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 193 approved status boards -->\n<window><defaultcontrol always="true">9200</defaultcontrol><controls>'+body+'</controls></window>'


def files(p):
    return {p.FOLDER + '/' + WINDOW: page(p).encode(), p.FOLDER + '/' + ITEM: item_sheet(p).encode()}
