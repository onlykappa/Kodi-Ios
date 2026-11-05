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
ACCOUNTS='RunScript(service.kodi.ios.bootstrap,accounts_page)'
SEARCH='RunScript(service.kodi.ios.bootstrap,settings_search)'
WINDOW='10004'
PAGE='Window(%s).Property(Settings.Page)'%WINDOW
ON_ROOT='String.IsEmpty(%s)'%PAGE
ON_CUSTOM='String.IsEqual(%s,custom)'%PAGE
ON_LIBRARY='String.IsEqual(%s,library)'%PAGE
UPDATES='!String.IsEmpty(System.AddonUpdateCount) + !String.IsEqual(System.AddonUpdateCount,0)'
FUSE='skin.arctic.fuse.3'

# iOS metrics at 2.687 units/pt: 52pt rows, 26pt group corners, 31pt icon tiles, 34pt between groups.
ROW=140;ROW2=170;RADIUS=70;TILE=84;GLYPH=66;GAP=90;PAD=43;TEXT_X=PAD+TILE+38
TILE_BG='FF161618';RED='FFFF453A';BLUE='FF0A84FF';GREEN='FF30D158'
PURPLE='FFBF5AF2';ORANGE='FFFF9F0A';TEAL='FF64D2FF';PINK='FFFF6AB0';SILVER='FFAEAEB2'

def toggle(p,on):
 """iOS 26 switch (63x28 pt): green or grey capsule with the elongated white knob."""
 w,h=170,76;kw,kh=104,64;kx=w-kw-6 if on else 6;ky=6;track=(48,209,88) if on else (57,57,61)
 def pixel(x,y):
  a=p.coverage(x,y,w,h,h/2);k=p.coverage(x-kx,y-ky,kw,kh,kh/2) if kx<=x<kx+kw and ky<=y<ky+kh else 0
  r,g,b=(int(t+(255-t)*k) for t in track);return (r,g,b,int(255*max(a,k)))
 return p.png(w,h,pixel)

def hl(p):
 """Focus highlight: rounded rectangle inset 10 units from every edge of the row (9-slice border 44)."""
 n=120;return p.png(n,n,lambda x,y:(255,255,255,int(255*p.coverage(x-10,y-10,n-20,n-20,34)) if 10<=x<n-10 and 10<=y<n-10 else 0))

def textures(p):
 return {'group.png':p.rounded(160,160,RADIUS),'tile84.png':p.rounded(TILE,TILE,24),'tile100.png':p.rounded(100,100,28),
         'avatar.png':p.rounded(300,300,150),'avatar_s.png':p.rounded(160,160,80),
         'hl.png':hl(p),'toggle_on.png':toggle(p,True),'toggle_off.png':toggle(p,False)}

# Rows: (id, label, actions joined by \x00, glyph, tint, value, badge condition)
def R(id,text,actions,glyph='',tint=SILVER,value='',badge=''):return (id,text,actions,glyph,tint,value,badge)
CUSTOM_PAGE='SetProperty(Settings.Page,custom,%s)\x00SetFocus(9401)'%WINDOW
LIBRARY_PAGE='SetProperty(Settings.Page,library,%s)\x00SetFocus(9451)'%WINDOW
LIBRARY_SCAN='RunScript(service.kodi.ios.bootstrap,library_scan)'
LIBRARY_REFRESH='RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=library_refresh&all=1)'
ROOT=[
 [R(9111,'Skin','ActivateWindow(skinsettings)','paintbrush.png',PURPLE),
  R(9112,'Interface','ActivateWindow(interfacesettings)','palette.png',BLUE),
  R(9113,'Customisation',CUSTOM_PAGE,'sliders.png','FFD1D1D6'),
  R(9114,'Player','ActivateWindow(playersettings)','circle-play.png',GREEN),
  R(9115,'Media','ActivateWindow(mediasettings)','film.png',ORANGE),
  R(9116,'Library',LIBRARY_PAGE,'folder.png',BLUE)],
 [R(9121,'PVR & Live TV','ActivateWindow(pvrsettings)','tv.png',RED),
  R(9122,'Games','ActivateWindow(gamesettings)','gamepad.png',PINK)],
 [R(9131,'System','ActivateWindow(systemsettings)','gear.png',SILVER),
  R(9132,'Services','ActivateWindow(servicesettings)','sitemap.png',TEAL),
  R(9133,'Profiles','ActivateWindow(profiles)','user.png',BLUE)],
 [R(9141,'Add-ons','ActivateWindow(addonbrowser)','puzzle-piece.png',ORANGE,badge=UPDATES),
  R(9142,'File Manager','ActivateWindow(filemanager)','folder.png',TEAL),
  R(9143,'Event Log','ActivateWindow(eventlog)','list.png',SILVER),
  R(9144,'Activity','Addon.OpenSettings(service.kodi.ios.bootstrap)','bars-progress.png',BLUE)],
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
LIBRARY=[
 ('iPhone Files',[R(9451,'Scan iPhone files',LIBRARY_SCAN,'magnifying-glass.png',BLUE)],
  'Find movies and shows in Kodi Downloads or a folder you choose. Upload missing files to Google Drive. Remove phone copies only after their size and checksum match Drive.'),
 ('Library',[R(9452,'Refresh Library',LIBRARY_REFRESH,'arrows-rotate.png',BLUE),
  R(9453,'Movies','ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=movie&fresh=1,return)','film.png',ORANGE),
  R(9454,'TV Shows','ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&fresh=1,return)','tv.png',PURPLE)],
  'Includes completed downloads on this iPhone and in Google Drive.'),
 ('Google Drive',[R(9455,'Google Drive settings','Addon.OpenSettings(plugin.googledrive)','cloud.png',BLUE),
  R(9456,'Transfer settings','Addon.OpenSettings(service.kodi.ios.bootstrap)','sliders.png',SILVER)],
  'Kodi can scan its own files and folders made available to the app.'),
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
    tags.append((' + '.join(hide+[cond]),target));hide.append('![%s]'%cond)   # Kodi groups with [ ], not ( )
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
 # iOS 26 press state: a rounded inset highlight, so it never pokes out of the group's rounded corners.
 return ('<texturefocus border="44" colordiffuse="1FFFFFFF">%shl.png</texturefocus><texturenofocus />'%p.MEDIA)

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
 xml+=p.icon(right,y+(height-34)//2,34,'chevron-right.png',p.GREY)
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
 thumb='!String.IsEmpty(System.ProfileThumb) + !String.Contains(System.ProfileThumb,DefaultUser)'
 return ('<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,h)+p.surface(p.SIDE,0,w,h,'group.png',p.SURFACE,RADIUS)+
  '<control type="group"><left>%d</left>'%p.SIDE+
  '<control type="button" id="9101"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s%s%s</control>'
   %(w,h,highlight(p,w,h),clicks(p,ACCOUNTS),nav_xml(p,moves))+
  p.surface(PAD,ay,a,a,'avatar_s.png','FF7B88C4')+p.icon(PAD+(a-80)//2,ay+(a-80)//2,80,'user.png',p.WHITE,'<visible>![%s]</visible>'%thumb)+
  p.image(PAD,ay,a,a,'$INFO[System.ProfileThumb]',p.WHITE,'<visible>%s</visible>'%thumb,'',p.MEDIA+'avatar_s.png')+
  p.label(PAD+a+40,40,w-PAD-a-140,70,'$INFO[System.ProfileName]','p_h3')+
  p.label(PAD+a+40,108,w-PAD-a-140,60,'Trakt, Drive, Elementum & more','p_foot',p.GREY)+
  p.icon(w-PAD-34,(h-34)//2,34,'chevron-right.png',p.GREY)+'</control></control>')

def updates_banner(p,moves):
 return card(p,[R(9102,'Add-on Updates Available','ActivateWindow(addonbrowser,addons://outdated/,return)',badge=UPDATES)],moves,UPDATES)

def search_field(p,moves):
 """iOS Settings search field at the top of the list: opens Kodi's keyboard and lists the matching settings."""
 w=p.WIDTH-2*p.SIDE;h=108
 return ('<control type="group"><width>%d</width><height>%d</height><control type="group"><left>%d</left>'%(p.WIDTH,h,p.SIDE)+
  '<control type="button" id="9100"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
  '<texturefocus border="54" colordiffuse="FF3A3A3C">%spill_108.png</texturefocus><texturenofocus border="54" colordiffuse="%s">%spill_108.png</texturenofocus>'
  '%s%s</control>'%(w,h,p.MEDIA,p.SURFACE,p.MEDIA,clicks(p,SEARCH),nav_xml(p,moves))+
  p.icon(36,(h-44)//2,44,'magnifying-glass.png',p.GREY)+p.label(100,0,w-140,h,'Search','p_body',p.GREY)+'</control></control>')

def root_ids():
 ids=[(9100,''),(9101,''),(9102,UPDATES)]
 for group in ROOT:ids+=[(r[0],'') for r in group]
 return ids

def custom_ids():
 return [(r[0],'') for _,rows,_ in CUSTOM for r in rows]

def root_list(p):
 moves=nav(root_ids())
 body=search_field(p,moves[9100])+spacer(40)+profile_card(p,moves[9101])+spacer(40,UPDATES)+updates_banner(p,moves)+spacer(GAP)
 for group in ROOT:body+=card(p,group,moves)+spacer(GAP)
 body+=('<control type="group"><width>%d</width><height>120</height>'%p.WIDTH+
        p.label(p.SIDE,0,p.WIDTH-2*p.SIDE,60,'Kodi $INFO[System.BuildVersionShort]$INFO[Window(Home).Property(KodiIOS.Build), (build ,)]'
                '  ·  $INFO[System.AddonTitle(%s)] $INFO[System.AddonVersion(%s)]'%(FUSE,FUSE),
                'p_foot',p.GREY,'center')+'</control>')
 return body+spacer(160)

def custom_list(p):
 moves=nav(custom_ids());body=''
 for title,rows,note in CUSTOM:
  body+=(section(p,title) if title else '')+card(p,rows,moves)+(footer(p,note) if note else spacer(20))+spacer(GAP-30)
 return body+spacer(160)

def library_list(p):
 moves=nav([(r[0],'') for _,rows,_ in LIBRARY for r in rows]);body=''
 moves[9451]=([('',9001)],moves[9451][1])
 for title,rows,note in LIBRARY:
  body+=section(p,title)+card(p,rows,moves)+footer(p,note,210 if title=='iPhone Files' else 130)+spacer(GAP-30)
 return body+spacer(160)

# Settings home: the header sits lower so the back circle and title clear the status bar like Search's band
# (SEARCH_BAND, 60 pt) and the large titles of Library and Search (top 40-46); the list starts under it.
SETTINGS_Y=76;SETTINGS_TOP=SETTINGS_Y+164
def header(p,back_actions,titles,y=36,down='<ondown>9300</ondown>'):
 """Glass back button and centred title over a black bar (the page scrolls under it)."""
 bar=p.image(0,0,p.WIDTH,y+154,p.MEDIA+'white.png',p.BG)+p.image(0,y+154,p.WIDTH,60,p.MEDIA+'fade_down.png')
 back=p.nav_button(9001,p.SIDE,y,'chevron-left.png',back_actions,down)
 names=''.join(p.label(260,y,p.WIDTH-520,108,t,'p_h3',p.WHITE,'center','<visible>%s</visible>'%c if c else '') for t,c in titles)
 return bar+names+back

def settings_window(p,original):
 """portrait/Settings.xml. Keeps Fuse's window attributes and onload helpers; opens on the home page when entered
 from Home (coming back from a category keeps the page you left)."""
 lst=lambda id,cond,body,top:('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom>'
  '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s</control>')%(id,top,p.WIDTH,cond,body)
 back=[(ON_CUSTOM,'ClearProperty(Settings.Page,%s)'%WINDOW),(ON_CUSTOM,'SetFocus(9113)'),
       (ON_LIBRARY,'ClearProperty(Settings.Page,%s)'%WINDOW),(ON_LIBRARY,'SetFocus(9116)'),(ON_ROOT,'Action(Back)')]
 body=('<controls>'+p.backdrop()+lst(9300,ON_ROOT,root_list(p),SETTINGS_TOP)+lst(9310,ON_CUSTOM,custom_list(p),SETTINGS_TOP)+
       lst(9320,ON_LIBRARY,library_list(p),SETTINGS_TOP)+
       header(p,back,[('Settings',ON_ROOT),('Customisation',ON_CUSTOM),('Library',ON_LIBRARY)],SETTINGS_Y,
              '<ondown condition="%s">9300</ondown><ondown condition="%s">9401</ondown><ondown condition="%s">9451</ondown>'%(ON_ROOT,ON_CUSTOM,ON_LIBRARY))+'</controls>')
 extra=('<onload condition="Window.Previous(home)">ClearProperty(Settings.Page,%s)</onload>'%WINDOW+
        '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>')
 # Back from a category opened on the Customisation page: the home rows are hidden, so focus that page instead.
 extra+='<onload condition="%s">SetFocus(9401)</onload>'%ON_CUSTOM
 extra+='<onload condition="%s">SetFocus(9451)</onload>'%ON_LIBRARY
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
 ay=70   # clear of the header's fade
 head=('<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,ay+550)+
  p.surface(ax,ay,a,a,'avatar.png','FF7B88C4')+p.label(ax,ay,a,a,P('initials'),'p_large',p.WHITE,'center','<visible>!%s</visible>'%thumb)+
  p.image(ax,ay,a,a,P('thumb'),p.WHITE,'<visible>%s</visible>'%thumb,'',p.MEDIA+'avatar.png')+
  p.label(p.SIDE,ay+330,w,100,P('name'),'p_title',p.WHITE,'center')+
  p.label(p.SIDE,ay+430,w,60,P('summary'),'p_sub',p.GREY,'center')+'</control>')
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

# --- Kodi's own setting pages (categories and add-on settings) -------------------------------------------------
# Kodi builds these pages itself from templates the skin provides (GUIDialogSettingsBase): category buttons from
# id 10 into grouplist 3, settings from ids 7 (button), 8 (switch), 9 (spinner), 12 (edit), 13 (slider), 14 (group
# title), 15 (colour) and 11 (separator) into grouplist 5; label 2 is the page title and 6 the focused setting's help.
LIST_TOP=356;HELP_H=210
def row_textures(p,focus=True):
 return ('<texturefocus colordiffuse="%s">%swhite.png</texturefocus><texturenofocus colordiffuse="%s">%swhite.png</texturenofocus>'
         %(p.SURFACE2 if focus else p.SURFACE,p.MEDIA,p.SURFACE,p.MEDIA))
def text_style(p):
 return ('<font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><disabledcolor>%s</disabledcolor>'
         '<align>left</align><aligny>center</aligny><textoffsetx>%d</textoffsetx>')%(p.WHITE,p.WHITE,p.DIM,PAD)
def setting_templates(p,category_type):
 """The row templates Kodi copies for every setting: full-width iOS cells, 52 pt high, hairline gaps between them."""
 w=p.WIDTH-2*p.SIDE;M=p.MEDIA;base='<width>%d</width><height>%d</height>'%(w,ROW)
 pill=('<control type="%s" id="10"><width>300</width><height>96</height><label></label><font>p_foot_b</font><textcolor>%s</textcolor>'
       '<focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
       '<texturefocus border="48" colordiffuse="FF48484A">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="%s">%spill_96.png</texturenofocus>'
       %(category_type,p.GREY,p.WHITE,M,p.SURFACE,M))
 if category_type=='togglebutton':
  pill+=('<alttexturefocus border="48" colordiffuse="%s">%spill_96.png</alttexturefocus><alttexturenofocus border="48" colordiffuse="%s">%spill_96.png</alttexturenofocus>'
         '<altlabel></altlabel>'%(BLUE,M,BLUE,M))
 pill+='</control>'
 chev=(p.ICONS+'chevron-left.png',p.ICONS+'chevron-right.png')
 return (pill+
  '<control type="button" id="7">%s%s%s<label2></label2></control>'%(base,row_textures(p),text_style(p))+
  ('<control type="radiobutton" id="8">%s%s%s<radiowidth>130</radiowidth><radioheight>58</radioheight><radioposx>%d</radioposx>'
   '<textureradioonfocus>%stoggle_on.png</textureradioonfocus><textureradioonnofocus>%stoggle_on.png</textureradioonnofocus>'
   '<textureradioofffocus>%stoggle_off.png</textureradioofffocus><textureradiooffnofocus>%stoggle_off.png</textureradiooffnofocus>'
   '<textureradioondisabled colordiffuse="66FFFFFF">%stoggle_on.png</textureradioondisabled><textureradiooffdisabled colordiffuse="66FFFFFF">%stoggle_off.png</textureradiooffdisabled>'
   '</control>')%(base,row_textures(p),text_style(p),w-PAD-130,M,M,M,M,M,M)+
  ('<control type="spincontrolex" id="9">%s%s%s<spinwidth>36</spinwidth><spinheight>36</spinheight><spinposx>%d</spinposx>'
   '<textureup colordiffuse="%s">%s</textureup><textureupfocus colordiffuse="%s">%s</textureupfocus>'
   '<texturedown colordiffuse="%s">%s</texturedown><texturedownfocus colordiffuse="%s">%s</texturedownfocus>'
   '<textureupdisabled colordiffuse="%s">%s</textureupdisabled><texturedowndisabled colordiffuse="%s">%s</texturedowndisabled>'
   '</control>')%(base,row_textures(p),text_style(p),PAD,p.DIM,chev[1],p.WHITE,chev[1],p.DIM,chev[0],p.WHITE,chev[0],p.SEP,chev[1],p.SEP,chev[0])+
  '<control type="edit" id="12">%s%s%s<hinttext></hinttext></control>'%(base,row_textures(p),text_style(p))+
  ('<control type="sliderex" id="13">%s%s%s<sliderwidth>260</sliderwidth><sliderheight>14</sliderheight><textwidth>%d</textwidth>'
   '<texturesliderbar border="7" colordiffuse="FF48484A">%sdot.png</texturesliderbar>'
   '<textureslidernib colordiffuse="%s">%sknob.png</textureslidernib><textureslidernibfocus colordiffuse="%s">%sknob.png</textureslidernibfocus>'
   '</control>')%(base,row_textures(p),text_style(p),w-PAD-260-300,M,p.WHITE,M,BLUE,M)+
  ('<control type="label" id="14"><width>%d</width><height>116</height><font>p_h3</font><textcolor>%s</textcolor>'
   '<align>left</align><aligny>bottom</aligny><textoffsetx>%d</textoffsetx></control>')%(w,p.GREY,PAD)+
  ('<control type="colorbutton" id="15">%s%s%s<colorwidth>60</colorwidth><colorheight>60</colorheight><colorposx>%d</colorposx>'
   '<texturecolormask>%sdot.png</texturecolormask><texturecolordisabledmask>%sdot.png</texturecolordisabledmask></control>')%(
   base,row_textures(p),text_style(p),w-PAD-60,M,M)+
  '<control type="image" id="11"><width>%d</width><height>34</height><texture /></control>'%w)

def setting_body(p,title,header_buttons,extra='',categories=True):
 """Header (title = label 2), category pills (grouplist 3), settings (grouplist 5), help text (label 6)."""
 w=p.WIDTH-2*p.SIDE
 bar=p.image(0,0,p.WIDTH,(LIST_TOP if categories else 200)-10,p.MEDIA+'white.png',p.BG)
 heading=('<control type="label" id="2"><left>300</left><top>36</top><width>%d</width><height>108</height><font>p_h3</font>'
          '<textcolor>%s</textcolor><align>center</align><aligny>center</aligny><scroll>true</scroll><label>%s</label></control>')%(p.WIDTH-600,p.WHITE,p.e(title))
 cats=('<control type="grouplist" id="3"><left>%d</left><top>200</top><width>%d</width><height>96</height><orientation>horizontal</orientation>'
       '<itemgap>16</itemgap><scrolltime tween="cubic" easing="out">250</scrolltime><ondown>5</ondown><onup>9001</onup>%s</control>')%(
       p.SIDE,w,'' if categories else '<visible>false</visible>')
 lst=('<control type="grouplist" id="5"><left>%d</left><top>%d</top><width>%d</width><bottom>%d</bottom><orientation>vertical</orientation>'
      '<itemgap>2</itemgap><usecontrolcoords>false</usecontrolcoords><onup>3</onup><scrolltime tween="cubic" easing="out">250</scrolltime></control>')%(
      p.SIDE,LIST_TOP if categories else 200,w,HELP_H)
 # Anchored to the bottom: the 9:16 resolution (home-button phones) has a shorter canvas than 9:19.5.
 help_=('<control type="image"><left>0</left><bottom>0</bottom><width>%d</width><height>%d</height><texture colordiffuse="%s">%swhite.png</texture></control>'
        %(p.WIDTH,HELP_H,p.BG,p.MEDIA)+
        '<control type="label" id="6"><width>1</width><height>1</height><visible>false</visible></control>'+
        '<control type="textbox"><left>%d</left><bottom>16</bottom><width>%d</width><height>%d</height><font>p_foot</font><textcolor>%s</textcolor>'
        '<label>$INFO[Control.GetLabel(6)]</label><autoscroll>false</autoscroll></control>')%(p.SIDE+PAD,w-2*PAD,HELP_H-40,p.GREY)
 return '<controls>'+p.backdrop()+lst+bar+heading+cats+help_+header_buttons+extra+'</controls>'

def category_window(p,original):
 """portrait/SettingsCategory.xml: System, Player, Media, Interface, Services, PVR and Games pages."""
 back=p.nav_button(9001,p.SIDE,36,'chevron-left.png','Action(Back)','<ondown>3</ondown>')
 level=('<control type="button" id="20"><left>%d</left><top>36</top><width>290</width><height>108</height><font>p_foot_b</font>'
        '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
        '<texturefocus border="54" colordiffuse="FF48484A">%spill_108.png</texturefocus><texturenofocus border="54" colordiffuse="%s">%spill_108.png</texturenofocus>'
        '<onclick>settingslevelchange</onclick><ondown>3</ondown><onleft>9001</onleft></control>')%(p.WIDTH-p.SIDE-290,BLUE,BLUE,p.MEDIA,p.SURFACE,p.MEDIA)
 body=setting_body(p,'',back+level,setting_templates(p,'togglebutton'))
 return p.window(original,body,'5','<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>')

def addon_settings_window(p,original,categories=True):
 """portrait/DialogAddonSettings.xml: every add-on's settings (Elementum, Umbrella, Trakt...) as an iOS sheet with
 Cancel and Done. 28/29 are Kodi's OK and Cancel; 20 and 30 stay hidden as in Fuse."""
 text_button=lambda id,x,text,color,bold,align:(('<control type="button" id="%d"><left>%d</left><top>36</top><width>240</width><height>108</height><textoffsetx>0</textoffsetx>'
   '<label>%s</label><font>%s</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>%s</align><aligny>center</aligny>'
   '<texturefocus /><texturenofocus /><ondown>3</ondown></control>')%(id,x,text,'p_btn' if bold else 'p_body',color,'FF64D2FF',align))
 hidden=''.join('<control type="button" id="%d"><width>1</width><height>1</height><visible>false</visible><texturefocus /><texturenofocus /></control>'%i for i in (20,30))
 buttons=text_button(29,p.SIDE,'Cancel',BLUE,False,'left')+text_button(28,p.WIDTH-p.SIDE-240,'Done',BLUE,True,'right')+hidden
 body=setting_body(p,'',buttons,setting_templates(p,'button'),categories)
 return p.window(original,body,'5','<animation effect="slide" start="0,300" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
                 '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>')

def files(p,read):
 """{relative path: bytes} for the portrait folder and its textures."""
 out={p.FOLDER+'/Settings.xml':settings_window(p,read('Settings.xml')).encode(),
      p.FOLDER+'/IOSAccounts.xml':accounts_page(p).encode(),
      p.FOLDER+'/SettingsCategory.xml':category_window(p,read('SettingsCategory.xml')).encode(),
      p.FOLDER+'/DialogAddonSettings.xml':addon_settings_window(p,read('DialogAddonSettings.xml')).encode()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
