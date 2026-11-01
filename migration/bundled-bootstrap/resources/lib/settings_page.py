"""Portrait Settings (owner-approved mockups, design/settings-mockups): an iOS 27 Settings-style grouped list in place
of Fuse's landscape Settings window shrunk into the middle of the screen, plus the Accounts page.

- portrait/Settings.xml: the Settings home (profile card -> Accounts, add-on updates banner, every Kodi category as a
  row with a black icon tile and coloured glyph) and, in the same window, the Customisation page (Fuse's own
  customisation entries). Window(10004).Property(Settings.Page) picks the page.
- portrait/IOSAccounts.xml: provider sign-ins, filled by accounts_page.py (accounts.py).

Leaf pages (Kodi's own categories, add-on settings) still open their windows. portrait.py passes its helpers in `p`.
"""
import os,importlib.util as _iu
_spec=_iu.spec_from_file_location('accounts',os.path.join(os.path.dirname(os.path.abspath(__file__)),'accounts.py'))
accounts=_iu.module_from_spec(_spec);_spec.loader.exec_module(accounts)

BOOT='special://xbmc/addons/service.kodi.ios.bootstrap/'
ACCOUNTS='RunScript(%saccounts_page.py)'%BOOT
WINDOW='10004'
PAGE='Window(%s).Property(Settings.Page)'%WINDOW
ON_ROOT='String.IsEmpty(%s)'%PAGE
ON_CUSTOM='String.IsEqual(%s,custom)'%PAGE
UPDATES='!String.IsEmpty(System.AddonUpdateCount) + !String.IsEqual(System.AddonUpdateCount,0)'
FUSE='skin.arctic.fuse.3'

# iOS metrics at 2.687 units/pt: 52pt rows, 26pt group corners, 31pt icon tiles, 34pt between groups.
ROW=140;ROW2=170;RADIUS=70;TILE=84;GLYPH=58;GAP=90;PAD=43;TEXT_X=PAD+TILE+38
TILE_BG='FF161618';RED='FFFF453A';BLUE='FF0A84FF';GREEN='FF30D158'
PURPLE='FFBF5AF2';ORANGE='FFFF9F0A';TEAL='FF64D2FF';PINK='FFFF6AB0';SILVER='FFAEAEB2'

def textures(p):
 return {'group.png':p.rounded(160,160,RADIUS),'tile84.png':p.rounded(TILE,TILE,24),'tile100.png':p.rounded(100,100,28),
         'avatar.png':p.rounded(300,300,150),'avatar_s.png':p.rounded(160,160,80)}

# Rows: (id, label, actions joined by \x00, glyph, tint, value, badge condition)
def R(id,text,actions,glyph='',tint=SILVER,value='',badge=''):return (id,text,actions,glyph,tint,value,badge)
CUSTOM_PAGE='SetProperty(Settings.Page,custom,%s)\x00SetFocus(9401)'%WINDOW
ROOT=[
 [R(9111,'Skin','ActivateWindow(skinsettings)','paintbrush.png',PURPLE),
  R(9112,'Interface','ActivateWindow(interfacesettings)','palette.png',BLUE),
  R(9113,'Customisation',CUSTOM_PAGE,'sliders.png','FFD1D1D6'),
  R(9114,'Player','ActivateWindow(playersettings)','circle-play.png',GREEN),
  R(9115,'Media','ActivateWindow(mediasettings)','film.png',ORANGE)],
 [R(9121,'PVR & Live TV','ActivateWindow(pvrsettings)','tv.png',RED),
  R(9122,'Games','ActivateWindow(gamesettings)','gamepad.png',PINK)],
 [R(9131,'System','ActivateWindow(systemsettings)','gear.png',SILVER),
  R(9132,'Services','ActivateWindow(servicesettings)','sitemap.png',TEAL),
  R(9133,'Profiles','ActivateWindow(profiles)','user.png',BLUE)],
 [R(9141,'Add-ons','ActivateWindow(addonbrowser)','puzzle-piece.png',ORANGE,badge=UPDATES),
  R(9142,'File Manager','ActivateWindow(filemanager)','folder.png',TEAL),
  R(9143,'Event Log','ActivateWindow(eventlog)','list.png',SILVER)],
 [R(9151,'Information','ActivateWindow(systeminfo)','circle-info.png',SILVER)],
]
# Fuse's Customisation list (1080i/Settings.xml), same actions.
def fuse_dialog(items,title):
 return 'SetProperty(CustomDialogSettingsItems,%s,Home)\x00SetProperty(CustomDialogSettingsTitle,%s,Home)\x00ActivateWindow(1118)'%(items,title)
CUSTOM=[
 ('Home Screen',[R(9401,'Widgets','ActivateWindow(1115)','table-cells-large.png',BLUE),
  R(9402,'Search Page','SetProperty(Shortcuts.EditMenu,menu=searchwidgets,Home)\x00ClearProperty(Shortcuts.EditMode,Home)'
                       '\x00ClearProperty(Shortcuts.EditGUID,Home)\x00ActivateWindow(1116)','magnifying-glass.png',SILVER)],
  'Choose and reorder the rows on Home and on the Search page.'),
 ('Pages',[R(9411,'Video Controls',fuse_dialog('DialogCustom_VideoOSD_Items','$LOCALIZE[31434]'),'circle-play.png',GREEN),
  R(9412,'Info Page',fuse_dialog('DialogCustom_VideoInfo_Items','$LOCALIZE[12003]'),'circle-info.png',SILVER),
  R(9413,'View Types','RunScript(script.skinvariables,action=buildviews,configure)','grip.png',PURPLE),
  R(9414,'Indicators',fuse_dialog('DialogCustom_Settings_Items_Indicators','$LOCALIZE[31234]'),'circle-check.png',ORANGE)],''),
 ('',[R(9421,'Skin Settings','ActivateWindow(skinsettings)','paintbrush.png',PURPLE),
  R(9422,'TMDb Helper','Addon.OpenSettings(plugin.video.themoviedb.helper)','film.png','FF01B4E4')],
  'TMDb Helper fills the Home rows. Sign in to Trakt from Accounts.'),
]

def clicks(p,actions):return ''.join('<onclick>%s</onclick>'%p.e(a) for a in actions.split('\x00'))

def nav(ids):
 """onup/ondown between consecutive focusable rows. ids: [(id, visible condition or '')] in screen order; a row with
 a condition is skipped when hidden (exclusive conditions, so only one navigation runs)."""
 out={}
 def step(seq):
  tags=[];hide=[]
  for target,cond in seq:
   if cond:
    tags.append((' + '.join(hide+[cond]),target));hide.append('!(%s)'%cond)
   else:
    tags.append((' + '.join(hide),target));break
  return tags
 for i,(rid,_) in enumerate(ids):
  out[rid]=(step(list(reversed(ids[:i]))),step(ids[i+1:]))
 return out

def nav_xml(p,moves):
 up,down=moves;xml=''
 for tag,items in (('onup',up),('ondown',down)):
  for cond,target in items:xml+='<%s%s>%s</%s>'%(tag,' condition="%s"'%p.e(cond) if cond else '',target,tag)
 return xml

def highlight(p,w,h):
 return ('<texturefocus border="20" colordiffuse="1AFFFFFF">%sround_s.png</texturefocus><texturenofocus />'%p.MEDIA)

def row_xml(p,r,y,first,moves,w,height=ROW):
 rid,text,actions,glyph,tint,value,badge=r;x=TEXT_X if glyph else PAD
 xml=('<control type="button" id="%d"><left>0</left><top>%d</top><width>%d</width><height>%d</height><label></label>%s%s%s</control>'
      %(rid,y,w,height,highlight(p,w,height),clicks(p,actions),nav_xml(p,moves)))
 if not first:xml+=p.image(x,y,w-x,2,p.MEDIA+'white.png',p.SEP)
 if glyph:
  xml+=p.surface(PAD,y+(height-TILE)//2,TILE,TILE,'tile84.png',TILE_BG,24)+p.icon(PAD+(TILE-GLYPH)//2,y+(height-GLYPH)//2,GLYPH,glyph,tint)
 xml+=p.label(x,y,w-x-300,height,text,'p_body')
 right=w-PAD-34
 if value:xml+=p.label(right-420,y,400,height,value,'p_body',p.GREY,'right')
 if badge:
  xml+=('<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(right-100,y+(height-60)//2,badge)+
        p.surface(0,0,80,60,'pill_56.png',RED,28)+p.label(0,0,80,60,'$INFO[System.AddonUpdateCount]','p_foot_b',p.WHITE,'center')+'</control>')
 xml+=p.icon(right,y+(height-34)//2,34,'chevron-right.png',p.DIM)
 return xml

def card(p,rows,moves,visible='',height=ROW):
 """One rounded group of rows (inset 20 pt, like iOS)."""
 w=p.WIDTH-2*p.SIDE;h=height*len(rows)
 inner=''.join(row_xml(p,r,i*height,i==0,moves[r[0]],w,height) for i,r in enumerate(rows))
 return ('<control type="group"><width>%d</width><height>%d</height>%s'%(p.WIDTH,h,'<visible>%s</visible>'%visible if visible else '')+
         p.surface(p.SIDE,0,w,h,'group.png',p.SURFACE,RADIUS)+'<control type="group"><left>%d</left>%s</control></control>'%(p.SIDE,inner))

def spacer(h,visible=''):
 return '<control type="image"><height>%d</height>%s<texture /></control>'%(h,'<visible>%s</visible>'%visible if visible else '')

def footer(p,text,h=110):
 return ('<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,h)+
         p.label(p.SIDE+PAD,10,p.WIDTH-2*(p.SIDE+PAD),h-20,text,'p_foot',p.GREY,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+'</control>')

def section(p,text):
 return ('<control type="group"><width>%d</width><height>80</height>'%p.WIDTH+
         p.label(p.SIDE+PAD,0,p.WIDTH-2*(p.SIDE+PAD),70,text,'p_h3',p.GREY)+'</control>')

def profile_card(p,moves):
 """Apple Account-style card: profile picture (or a person glyph), profile name, the services on the Accounts page."""
 w=p.WIDTH-2*p.SIDE;h=220;a=160;ay=(h-a)//2
 thumb='!String.IsEmpty(System.ProfileThumb)'
 return ('<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,h)+p.surface(p.SIDE,0,w,h,'group.png',p.SURFACE,RADIUS)+
  '<control type="group"><left>%d</left>'%p.SIDE+
  '<control type="button" id="9101"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s%s%s</control>'
   %(w,h,highlight(p,w,h),clicks(p,ACCOUNTS),nav_xml(p,moves))+
  p.surface(PAD,ay,a,a,'avatar_s.png','FF7B88C4')+p.icon(PAD+(a-80)//2,ay+(a-80)//2,80,'user.png',p.WHITE,'<visible>!%s</visible>'%thumb)+
  p.image(PAD,ay,a,a,'$INFO[System.ProfileThumb]',p.WHITE,'<visible>%s</visible>'%thumb,'>scale',p.MEDIA+'avatar_s.png')+
  p.label(PAD+a+40,40,w-PAD-a-140,70,'$INFO[System.ProfileName]','p_h3')+
  p.label(PAD+a+40,108,w-PAD-a-140,60,'Trakt, Drive, Elementum & more','p_foot',p.GREY)+
  p.icon(w-PAD-34,(h-34)//2,34,'chevron-right.png',p.DIM)+'</control></control>')

def updates_banner(p,moves):
 return card(p,[R(9102,'Add-on Updates Available','ActivateWindow(addonbrowser,addons://outdated/,return)',badge=UPDATES)],moves,UPDATES)

def root_ids():
 ids=[(9101,''),(9102,UPDATES)]
 for group in ROOT:ids+=[(r[0],'') for r in group]
 return ids

def custom_ids():
 return [(r[0],'') for _,rows,_ in CUSTOM for r in rows]

def root_list(p):
 moves=nav(root_ids())
 body=profile_card(p,moves[9101])+spacer(40,UPDATES)+updates_banner(p,moves)+spacer(GAP)
 for group in ROOT:body+=card(p,group,moves)+spacer(GAP)
 body+=('<control type="group"><width>%d</width><height>120</height>'%p.WIDTH+
        p.label(p.SIDE,0,p.WIDTH-2*p.SIDE,60,'Kodi $INFO[System.BuildVersionShort]  ·  $INFO[System.AddonTitle(%s)] $INFO[System.AddonVersion(%s)]'%(FUSE,FUSE),
                'p_foot',p.DIM,'center')+'</control>')
 return body+spacer(160)

def custom_list(p):
 moves=nav(custom_ids());body=''
 for title,rows,note in CUSTOM:
  body+=(section(p,title) if title else '')+card(p,rows,moves)+(footer(p,note) if note else spacer(20))+spacer(GAP-30)
 return body+spacer(160)

def header(p,back_actions,titles):
 """Glass back button and centred title over a black bar (the page scrolls under it)."""
 bar=p.image(0,0,p.WIDTH,190,p.MEDIA+'white.png',p.BG)+p.image(0,190,p.WIDTH,60,p.MEDIA+'fade_down.png')
 back=p.pill_button(9001,p.SIDE,36,108,108,'',back_actions,'glass','chevron-left.png','<ondown>9300</ondown>')
 names=''.join(p.label(260,36,p.WIDTH-520,108,t,'p_h3',p.WHITE,'center','<visible>%s</visible>'%c if c else '') for t,c in titles)
 return bar+names+back

def settings_window(p,original):
 """portrait/Settings.xml. Keeps Fuse's window attributes and onload helpers; opens on the home page when entered
 from Home (coming back from a category keeps the page you left)."""
 lst=lambda id,cond,body,top:('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom>'
  '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s</control>')%(id,top,p.WIDTH,cond,body)
 back=[(ON_CUSTOM,'ClearProperty(Settings.Page,%s)'%WINDOW),(ON_CUSTOM,'SetFocus(9113)'),(ON_ROOT,'Action(Back)')]
 body=('<controls>'+p.backdrop()+lst(9300,ON_ROOT,root_list(p),200)+lst(9310,ON_CUSTOM,custom_list(p),200)+
       header(p,back,[('Settings',ON_ROOT),('Customisation',ON_CUSTOM)])+'</controls>')
 extra=('<onload condition="Window.Previous(home)">ClearProperty(Settings.Page,%s)</onload>'%WINDOW+
        '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>')
 # Back from a category opened on the Customisation page: the home rows are hidden, so focus that page instead.
 extra+='<onload condition="%s">SetFocus(9401)</onload>'%ON_CUSTOM
 return p.window(original,body,'9101',extra)

def account_row(p,n,y,first,moves,w):
 P=lambda k:'$INFO[Window().Property(acct.%d.%s)]'%(n,k)
 signed='!String.IsEmpty(Window().Property(acct.%d.signed))'%n
 button='!String.IsEmpty(Window().Property(acct.%d.button))'%n
 h=ROW2;tile=100;right=w-PAD
 xml=('<control type="button" id="%d"><left>0</left><top>%d</top><width>%d</width><height>%d</height><label></label>%s%s</control>'
      %(9600+n,y,w,h,highlight(p,w,h),nav_xml(p,moves)))
 if not first:xml+=p.image(PAD+tile+38,y,w-PAD-tile-38,2,p.MEDIA+'white.png',p.SEP)
 x=PAD+tile+38
 xml+=(p.surface(PAD,y+(h-tile)//2,tile,tile,'tile100.png',P('tint'),28)+p.icon(PAD+15,y+(h-70)//2,70,icon_path(p,P('icon')),p.WHITE)+
       p.label(x,y+24,w-x-300,64,P('name'),'p_body')+
       p.image(x,y+106,22,22,p.MEDIA+'dot.png',GREEN,'<visible>%s</visible>'%signed)+
       p.label(x+34,y+88,w-x-334,56,P('text'),'p_foot',GREEN,'left','<visible>%s</visible>'%signed)+
       p.label(x,y+88,w-x-300,56,P('text'),'p_foot',p.GREY,'left','<visible>!%s</visible>'%signed)+
       p.icon(right-34,y+(h-34)//2,34,'chevron-right.png',p.DIM,'<visible>%s</visible>'%signed)+
       '<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(right-230,y+(h-72)//2,button)+
       p.surface(0,0,230,72,'pill_72.png',BLUE,36)+p.label(0,0,230,72,P('button'),'p_foot_b',p.WHITE,'center')+'</control>')
 return xml

def icon_path(p,prop):return p.ICONS+prop

def accounts_page(p):
 """portrait/IOSAccounts.xml (Apple Account style): avatar, name and summary, then the services by section."""
 w=p.WIDTH-2*p.SIDE;P=lambda k:'$INFO[Window().Property(%s)]'%k
 services=accounts.SERVICES;links=accounts.LINKS
 order=[(9600+n,'') for n in range(1,len(services)+1)]+[(9611+i,'') for i in range(len(links))]
 moves=nav(order)
 thumb='!String.IsEmpty(Window().Property(thumb))';a=300;ax=(p.WIDTH-a)//2
 head=('<control type="group"><width>%d</width><height>560</height>'%p.WIDTH+
  p.surface(ax,10,a,a,'avatar.png','FF7B88C4')+p.label(ax,10,a,a,P('initials'),'p_large',p.WHITE,'center','<visible>!%s</visible>'%thumb)+
  p.image(ax,10,a,a,P('thumb'),p.WHITE,'<visible>%s</visible>'%thumb,'>scale',p.MEDIA+'avatar.png')+
  p.label(p.SIDE,340,w,100,P('name'),'p_title',p.WHITE,'center')+
  p.label(p.SIDE,440,w,60,P('summary'),'p_sub',p.GREY,'center')+'</control>')
 body=head
 notes=('Tap a service to manage it or sign out. Debrid and scraper logins are inside each add-on.',
        'Signing in to Trakt in TMDb Helper fills "Because You Watched" and the recommendation rows on Home.')
 for s,title in enumerate(accounts.SECTIONS):
  rows=[n for n,svc in enumerate(services,1) if svc['section']==s]
  h=ROW2*len(rows)
  inner=''.join(account_row(p,n,i*ROW2,i==0,moves[9600+n],w) for i,n in enumerate(rows))
  body+=(section(p,title)+'<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,h)+
         p.surface(p.SIDE,0,w,h,'group.png',p.SURFACE,RADIUS)+'<control type="group"><left>%d</left>%s</control></control>'%(p.SIDE,inner)+
         footer(p,notes[s])+spacer(GAP-30))
 link_rows=[R(9611+i,t,a_,g,c) for i,(t,g,c,a_) in enumerate(links)]
 # Link rows are handled by accounts_page.py (onClick), so they carry no onclick of their own.
 link_rows=[(r[0],r[1],'',r[3],r[4],'','') for r in link_rows]
 body+=card(p,link_rows,moves).replace('<onclick></onclick>','')+footer(p,'Sign-ins stay on this iPhone. They are never uploaded to GitHub or included in builds.',140)+spacer(160)
 lst=('<control type="grouplist" id="9300"><left>0</left><top>200</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
      '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>%s</control>')%(p.WIDTH,body)
 page='<controls>'+p.backdrop()+lst+header(p,[('','Close')],[('Accounts','')])+'</controls>'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9601</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(p.MARKER,page)

def files(p,read):
 """{relative path: bytes} for the portrait folder and its textures."""
 out={p.FOLDER+'/Settings.xml':settings_window(p,read('Settings.xml')).encode(),
      p.FOLDER+'/IOSAccounts.xml':accounts_page(p).encode()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
