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
ADDON_UPDATES='RunScript(service.kodi.ios.bootstrap,addon_updates)'
WINDOW='10004'
PAGE='Window(%s).Property(Settings.Page)'%WINDOW
ON_ROOT='String.IsEmpty(%s)'%PAGE
ON_CUSTOM='String.IsEqual(%s,custom)'%PAGE
ON_LIBRARY='String.IsEqual(%s,library)'%PAGE
ON_BADGES='String.IsEqual(%s,badges)'%PAGE
ON_OSD='String.IsEqual(%s,osd)'%PAGE
ON_TABS='String.IsEqual(%s,tabs)'%PAGE
ON_INFO='String.IsEqual(%s,info)'%PAGE
ON_VIEWS='String.IsEqual(%s,views)'%PAGE
# Customisation's own pages: (page, condition, first row, the Customisation row it came from, title).
SUBPAGES=(('badges',ON_BADGES,9501,9414,'Poster Badges'),('osd',ON_OSD,9531,9411,'Video Controls'),('tabs',ON_TABS,9551,9401,'Tabs & Rows'),
          ('info',ON_INFO,9561,9412,'Info Page'),('views',ON_VIEWS,9581,9413,'View Types'))
ON_SUBPAGE=' | '.join('[%s]'%c for _,c,_,_,_ in SUBPAGES)
COUNTS='RunScript(service.kodi.ios.bootstrap,customise_counts)'
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
CUSTOM_PAGE='SetProperty(Settings.Page,custom,%s)\x00SetFocus(9401)\x00RunScript(service.kodi.ios.bootstrap,customise_counts)'%WINDOW
LIBRARY_PAGE='SetProperty(Settings.Page,library,%s)\x00SetFocus(9451)'%WINDOW
LIBRARY_SCAN='RunScript(service.kodi.ios.bootstrap,library_scan)'
LIBRARY_STATUS='RunScript(service.kodi.ios.bootstrap,library_status)'
LIBRARY_REFRESH='RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=library_refresh&all=1)'
ROOT=[
 [R(9111,'Skin','RunScript(service.kodi.ios.bootstrap,skin_settings_page)','paintbrush.png',PURPLE),
  R(9112,'Interface','RunScript(service.kodi.ios.bootstrap,section_page,interface)','palette.png',BLUE),
  R(9113,'Customisation',CUSTOM_PAGE,'sliders.png','FFD1D1D6'),
  R(9114,'Player','RunScript(service.kodi.ios.bootstrap,section_page,player)','circle-play.png',GREEN),
  R(9115,'Media','RunScript(service.kodi.ios.bootstrap,section_page,media)','film.png',ORANGE),
  R(9116,'Library',LIBRARY_PAGE,'folder.png',BLUE),
  # Settings › AI Upscale (ai-upscale-settings-mockups.html board A, DEC-042): right under Library, a purple wand.
  R(9117,'AI Upscale','RunScript(service.kodi.ios.bootstrap,upscale_settings)','wand-magic-sparkles.png',PURPLE,
    '$INFO[Window(Home).Property(KodiIOS.UpscaleSummary)]')],
 # What the profile button's More menu held (round 5: the gear in the header opens Settings instead).
 [R(9171,'Google Drive','ActivateWindow(Videos,plugin://plugin.googledrive/,return)','cloud.png',BLUE),
  R(9172,'Favourites','RunScript(service.kodi.ios.bootstrap,favourites_page)','star.png',ORANGE),
  R(9173,'Check for updates','RunScript(service.kodi.ios.bootstrap,check_updates)','cloud-arrow-down.png',GREEN),
  R(9174,'iPhone navigation / recovery','RunScript(service.kodi.ios.bootstrap,navigation_menu)','life-ring.png',RED)],
 # PVR & Live TV and Games are gone (owner, 2026-11-12): the app ships without the PVR clients and game cores
 # (build_customized_ipa.prune_unused_addons), so those pages had nothing to set.
 [R(9131,'System','RunScript(service.kodi.ios.bootstrap,section_page,system)','gear.png',SILVER),
  R(9132,'Services','RunScript(service.kodi.ios.bootstrap,section_page,services)','sitemap.png',TEAL),
  R(9133,'Profiles','RunScript(service.kodi.ios.bootstrap,profiles_page)','user.png',BLUE)],
 [R(9141,'Add-ons','ActivateWindow(addonbrowser)','puzzle-piece.png',ORANGE,badge=UPDATES),
  R(9142,'File Manager','ActivateWindow(filemanager)','folder.png',TEAL),
  R(9143,'Event Log','ActivateWindow(eventlog)','list.png',SILVER),
  R(9145,'Export diagnostic log','RunScript(service.kodi.ios.bootstrap,export_logs)','list.png',BLUE),
  R(9144,'Activity','Addon.OpenSettings(service.kodi.ios.bootstrap)','bars-progress.png',BLUE)],
 [R(9151,'Information','ActivateWindow(systeminfo)','circle-info.png',SILVER)],
]
# Fuse's Customisation list (1080i/Settings.xml), same actions.
def fuse_dialog(items,title):
 return 'SetProperty(CustomDialogSettingsItems,%s,Home)\x00SetProperty(CustomDialogSettingsTitle,%s,Home)\x00ActivateWindow(1118)'%(items,title)
def subpage(name):
 first=[f for n,_,f,_,_ in SUBPAGES if n==name][0]
 return 'SetProperty(Settings.Page,%s,%s)\x00SetFocus(%d)'%(name,WINDOW,first)
BADGES_PAGE,OSD_PAGE,TABS_PAGE,INFO_PAGE,VIEWS_PAGE=(subpage(n) for n in ('badges','osd','tabs','info','views'))
COUNT=lambda key:'$INFO[Window(%s).Property(custom.%s)]'%(WINDOW,key)
CUSTOM=[
 ('Home Screen',[R(9401,'Tabs & Rows',TABS_PAGE,'table-cells-large.png',BLUE,COUNT('rows'))],
  'Choose which tabs show, their order and the rows on each.'),
 ('Pages',[R(9411,'Video Controls',OSD_PAGE,'circle-play.png',GREEN,COUNT('osd')),
  R(9412,'Info Page',INFO_PAGE,'circle-info.png',SILVER,COUNT('info')),
  R(9413,'View Types',VIEWS_PAGE,'grip.png',PURPLE,COUNT('views')),
  R(9414,'Poster Badges',BADGES_PAGE,'circle-check.png',ORANGE,COUNT('badges'))],''),
 ('',[R(9421,'Skin Settings','RunScript(service.kodi.ios.bootstrap,skin_settings_page)','paintbrush.png',PURPLE),
  R(9422,'TMDb Helper','Addon.OpenSettings(plugin.video.themoviedb.helper)','film.png','FF01B4E4')],
  'TMDb Helper fills the Home rows. Sign in to Trakt from Accounts.'),
]
LIBRARY=[
 ('iPhone Files',[R(9451,'Scan iPhone files',LIBRARY_SCAN,'magnifying-glass.png',BLUE)],
  'Find movies and shows in Kodi Downloads or a folder you choose. Upload missing files to Google Drive. Remove phone copies only after their size and checksum match Drive.'),
 ('Library',[R(9452,'Refresh Library',LIBRARY_REFRESH,'arrows-rotate.png',BLUE),
  R(9453,'Movies','RunScript(service.kodi.ios.bootstrap,library_manager,movie)','film.png',ORANGE),
  R(9454,'TV Shows','RunScript(service.kodi.ios.bootstrap,library_manager,tv)','tv.png',PURPLE),
  R(9458,'Check Drive for problems','RunScript(service.kodi.ios.bootstrap,library_manager,check)','magnifying-glass.png',ORANGE),
  # ISSUE-198: copies that ended, with their reason; Retry All / Clear.
  R(9459,'Download problems','RunScript(service.kodi.ios.bootstrap,copy_problems)','triangle-exclamation.png',RED)],
  'Includes completed downloads on this iPhone and in Google Drive.'),
 ('Kodi and AirPlay',[R(9457,'Library status',LIBRARY_STATUS,'file-waveform.png',PURPLE)],
  'Every movie and show in Google Drive › Kodi Downloads is prepared once, so seeking on Kodi and AirPlay never waits. Check now to see what is ready, waiting or paused.'),
 ('Google Drive',[R(9455,'Google Drive settings','Addon.OpenSettings(plugin.googledrive)','cloud.png',BLUE),
  R(9456,'Transfer settings','Addon.OpenSettings(service.kodi.ios.bootstrap)','sliders.png',SILVER)],
  'Kodi can scan its own files and folders made available to the app.'),
]

# Native switch pages (round-4 mockups 08 and 10). Each switch writes the same skin setting as Fuse's box did:
# S(id, label, setting, on when the setting is absent, needs this condition to be changeable).
def S(id,text,setting,inverted=False,enable=''):return {'id':id,'text':text,'setting':setting,'inverted':inverted,'enable':enable}
def on_condition(sw):return ('!' if sw['inverted'] else '')+'Skin.HasSetting(%s)'%sw['setting']
BADGES=[
 ('On Posters',[S(9501,'Watched','Indicator.DisableWatched',True),S(9502,'In Your Library','Indicator.DisableLibrary',True),
  S(9503,'Part of a Collection','Indicator.DisableCollection',True),S(9504,'Progress Bar','Indicator.DisableProgress',True),
  S(9505,'Video Versions','Indicator.MovieVersionBanner')],'Shown on the posters in Home, Movies, TV and the Library.'),
 ('Episodes & TV',[S(9511,'Episodes Left','Indicator.DisableEpisodes',True),
  S(9512,'Also on Shows Not Started','Indicator.EnableUnwatchedCount',False,'!Skin.HasSetting(Indicator.DisableEpisodes)'),
  S(9513,'Premiere / Finale','Indicator.EpisodeTypeBanner')],   # no Live TV: its Catch-up indicator is gone
  'Episodes Left counts the episodes you have not watched yet, on shows you have started.'),
 ('Trakt (TMDb Helper)',[S(9521,'On Your Watchlist','Indicator.TraktWatchlist'),S(9522,'In Your Favourites','Indicator.TraktFavourites')],
  'Shown when you are signed in to Trakt in TMDb Helper.'),
]
OSD_TIMEOUT='Skin.String(OSD_Timeout)'
OSD=[
 ('Controls',[('value',R(9531,'Hide Controls After','Skin.SetNumeric(OSD_Timeout)',value='$INFO[%s,, s]'%OSD_TIMEOUT))],
  'Leave it empty to keep the controls until you tap the video.'),
 ('Info Over the Video',[S(9541,'Landscape Artwork','OSD.InfoOverlay.DisableLandscapeOnInfo',True),
  S(9542,'Plot & Ratings','OSD.InfoOverlay.DisablePlotRatingsOnInfo',True)],'Shown when a video starts and when you pause it.'),
]
ROWS_SCRIPT='RunScript(service.kodi.ios.bootstrap,customise_rows,tab=%s)'
TABS_PAGE_ROWS=[
 ('Tab Bar',[('value',R(9551,'Home',ROWS_SCRIPT%'home','house.png',BLUE,COUNT('rows.home'))),
  ('value',R(9552,'Movies',ROWS_SCRIPT%'movies','film.png',ORANGE,COUNT('rows.movies'))),
  ('value',R(9553,'TV Shows',ROWS_SCRIPT%'tv','tv.png',PURPLE,COUNT('rows.tv')))],
  'Tap a tab to choose its rows. Library and Search are fixed pages.'),
]
# Our info page (portrait.video_info) draws these rows under the plot, from TMDb Helper.
INFO=[
 ('Sections',[S(9561,'Starring','VideoInfo.Widgets.DisableStarring',True),S(9562,'Crew','VideoInfo.Widgets.DisableCrew',True),
  S(9563,'Seasons','VideoInfo.Widgets.DisableSeasons',True),S(9564,'Collection','VideoInfo.Widgets.DisableCollection',True),
  S(9565,'Recommendations','VideoInfo.Widgets.DisableRecommendations',True),S(9566,'Videos & Trailers','VideoInfo.Widgets.DisableVideos',True)],
  'The rows under the plot on a movie or show page, from TMDb Helper. Seasons shows on shows, Collection on movies.'),
]
GRID='Skin.String(Portrait.Grid)'
VIEWS=[
 ('Movies & TV Shows',[('radio',R(9581,'Poster Grid · 3 across','Skin.Reset(Portrait.Grid)'),'String.IsEmpty(%s)'%GRID),
  ('radio',R(9582,'Large Posters · 2 across','Skin.SetString(Portrait.Grid,large)'),'String.IsEqual(%s,large)'%GRID)],
  'How the Library, categories and search results show movies and shows.'),
]
def view_name(visible):return 'Large Posters' if visible('String.IsEqual(%s,large)'%GRID) else 'Poster Grid'

def switches(page):return [r for _,rows,_ in page for r in rows if isinstance(r,dict)]
def count_rules():
 """{property: [conditions]} for customise_counts.py: how many of a page's switches are on."""
 return {'badges':[on_condition(sw) for sw in switches(BADGES)],'osd':[on_condition(sw) for sw in switches(OSD)],
         'info':[on_condition(sw) for sw in switches(INFO)]}

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

def row_xml(p,r,y,first,moves,w,height=ROW,check=''):
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
 if check:xml+=p.icon(right-10,y+(height-50)//2,50,'check.png',BLUE,'<visible>%s</visible>'%check)
 else:xml+=p.icon(right,y+(height-34)//2,34,'chevron-right.png',p.GREY)
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
 # Grows with its text (build 224 rig audit: Accounts' and Library's last footer lines were cut off): p_foot fits
 # about 46 characters per line across the page, 44 units a line.
 import math
 h=max(h,30+44*math.ceil(len(str(text))/46.0))
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
 return card(p,[R(9102,'Add-on Updates Available',ADDON_UPDATES,badge=UPDATES)],moves,UPDATES)

def search_field(p,moves):
 """iOS Settings search field at the top of the list: opens Kodi's keyboard and lists the matching settings."""
 w=p.WIDTH-2*p.SIDE;h=124
 return ('<control type="group"><width>%d</width><height>%d</height><control type="group"><left>%d</left>'%(p.WIDTH,h,p.SIDE)+
  '<control type="button" id="9100"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
  '<texturefocus border="54" colordiffuse="FF3A3A3C">%spill_108.png</texturefocus><texturenofocus border="54" colordiffuse="%s">%spill_108.png</texturenofocus>'
  '%s%s</control>'%(w,h,p.MEDIA,p.SURFACE,p.MEDIA,clicks(p,SEARCH),nav_xml(p,moves))+
  p.icon(36,(h-44)//2,44,'magnifying-glass.png',p.GREY)+p.label(100,0,w-140,h,'Search','p_body',p.GREY)+'</control></control>')

def switch_row(p,sw,y,first,moves,w):
 on=on_condition(sw);tx,ty=w-PAD-130,y+(ROW-58)//2
 xml=('<control type="button" id="%d"><left>0</left><top>%d</top><width>%d</width><height>%d</height><label></label>%s%s%s%s</control>'
      %(sw['id'],y,w,ROW,highlight(p,w,ROW),'<enable>%s</enable>'%sw['enable'] if sw['enable'] else '',
        '<onclick>Skin.ToggleSetting(%s)</onclick>'%sw['setting'],nav_xml(p,moves)))
 if not first:xml+=p.image(PAD,y,w-PAD,2,p.MEDIA+'white.png',p.SEP)
 dim='<animation effect="fade" start="100" end="40" time="0" condition="![%s]">Conditional</animation>'%sw['enable'] if sw['enable'] else ''
 return xml+('<control type="group">%s'%dim+p.label(PAD,y,w-PAD-200,ROW,sw['text'],'p_body')+
  p.image(tx,ty,130,58,p.MEDIA+'toggle_on.png',p.WHITE,'<visible>%s</visible>'%on)+
  p.image(tx,ty,130,58,p.MEDIA+'toggle_off.png',p.WHITE,'<visible>![%s]</visible>'%on)+'</control>')

def unwrap(item):
 """A page's item: a switch (dict), ('value', R) or ('radio', R, condition that it is the chosen one)."""
 if isinstance(item,dict):return 'switch',item,''
 if item[0]=='radio':return 'radio',item[1],item[2]
 return 'value',item[1],''
def page_rows(page):return [unwrap(r)[1] for _,rows,_ in page for r in rows]
def row_id(r):return r['id'] if isinstance(r,dict) else r[0]

def switch_list(p,page,first_up=9001,top=''):
 """A page of grouped switches, value rows (Hide Controls After) and choices (View Types)."""
 ids=[(row_id(r),'') for r in page_rows(page)];moves=nav(ids)
 moves[ids[0][0]]=([('',first_up)],moves[ids[0][0]][1])
 w=p.WIDTH-2*p.SIDE;body=top
 for title,rows,note in page:
  inner=''
  for i,item in enumerate(rows):
   kind,r,cond=unwrap(item)
   if kind=='switch':inner+=switch_row(p,r,i*ROW,i==0,moves[r['id']],w)
   else:
    inner+=row_xml(p,r,i*ROW,i==0,moves[r[0]],w,check=cond)
    if r[0]==9531:inner+=p.label(w-PAD-34-420,i*ROW,400,ROW,'Never','p_body',p.GREY,'right','<visible>String.IsEmpty(%s)</visible>'%OSD_TIMEOUT)
  h=ROW*len(rows)
  body+=((section(p,title) if title else spacer(20))+'<control type="group"><width>%d</width><height>%d</height>'%(p.WIDTH,h)+
         p.surface(p.SIDE,0,w,h,'group.png',p.SURFACE,RADIUS)+'<control type="group"><left>%d</left>%s</control></control>'%(p.SIDE,inner)+
         (footer(p,note,130) if note else spacer(20))+spacer(GAP-30))
 return body+spacer(160)

def badges_preview(p):
 """Mockup 08: three posters showing the badges that are on (a watched film, a show part-way through, one in progress)."""
 w,h=220,330;gap=40;left=(p.WIDTH-3*w-2*gap)//2;xml=''
 for n,(badge,glyph,color) in enumerate((('Indicator.DisableWatched','circle-check.png',p.GREEN if hasattr(p,'GREEN') else GREEN),
                                        ('Indicator.DisableEpisodes','',''),('Indicator.DisableProgress','',''))):
  x=left+n*(w+gap);xml+=p.surface(x,0,w,h,'tile100.png','FF2C2C2E',28)
  on='!Skin.HasSetting(%s)'%badge
  if glyph:xml+=('<control type="group"><left>%d</left><top>12</top><visible>%s</visible>'%(x+w-62,on)+
                 p.image(0,0,50,50,p.MEDIA+'avatar_s.png','B3000000')+p.icon(9,9,32,glyph,color)+'</control>')
  elif n==1:xml+=('<control type="group"><left>%d</left><top>12</top><visible>%s</visible>'%(x+12,on)+
                  p.image(0,0,66,50,p.MEDIA+'pill_56.png','E60A84FF','',border=25)+p.label(0,0,66,50,'4','p_foot_b',p.WHITE,'center')+'</control>')
  else:xml+=(p.image(x+18,h-34,w-36,10,p.MEDIA+'pill_96.png','59FFFFFF','<visible>%s</visible>'%on,border=5)+
             p.image(x+18,h-34,(w-36)*3//5,10,p.MEDIA+'pill_96.png',p.WHITE,'<visible>%s</visible>'%on,border=5))
 return ('<control type="group"><width>%d</width><height>%d</height>%s</control>'%(p.WIDTH,h+30,xml)+
         footer(p,'A preview of the badges you have on.',90)+spacer(30))

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
SETTINGS_Y=76;SETTINGS_TOP=340
def header(p,back_actions,titles,y=36,down='<ondown>9300</ondown>'):
 """Glass back button and centred title over a black bar (the page scrolls under it)."""
 bar=p.image(0,0,p.WIDTH,y+154,p.MEDIA+'white.png',p.BG)+p.image(0,y+154,p.WIDTH,60,p.MEDIA+'fade_down.png')
 back=p.nav_button(9001,p.SIDE,y,'chevron-left.png',back_actions,down)
 names=''.join(p.label(260,y,p.WIDTH-520,108,t,'p_h3',p.WHITE,'center','<visible>%s</visible>'%c if c else '') for t,c in titles)
 root=next((cond for text,cond in titles if text=='Settings'),None)
 if root is not None:
  regular=' + '.join('![%s]'%root for _ in [0])
  large=p.image(0,0,p.WIDTH,320,p.MEDIA+'white.png',p.BG)+p.label(p.SIDE,200,p.WIDTH-2*p.SIDE,140,'Settings','p_title')
  return '<control type="group"><visible>%s</visible>%s</control><control type="group"><visible>%s</visible>%s</control>'%(root,large,regular,bar+names)+back
 return bar+names+back

def settings_window(p,original):
 """portrait/Settings.xml. Keeps Fuse's window attributes and onload helpers; opens on the home page when entered
 from Home (coming back from a category keeps the page you left)."""
 lst=lambda id,cond,body,top:('<control type="grouplist" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom>'
  '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>%s</control>')%(id,top,p.WIDTH,cond,body)
 back=[(ON_CUSTOM,'ClearProperty(Settings.Page,%s)'%WINDOW),(ON_CUSTOM,'SetFocus(9113)'),
       (ON_LIBRARY,'ClearProperty(Settings.Page,%s)'%WINDOW),(ON_LIBRARY,'SetFocus(9116)'),
       # A Customisation page goes back to Customisation (its rows' values counted again).
       # Kodi checks every condition first and then runs the actions in order, so the page changes before the focus.
       (ON_SUBPAGE,'SetProperty(Settings.Page,custom,%s)'%WINDOW)]+[(c,'SetFocus(%d)'%row) for _,c,_,row,_ in SUBPAGES]+[
       (ON_SUBPAGE,COUNTS),(ON_ROOT,'Action(Back)')]
 body=('<controls>'+p.backdrop()+lst(9300,ON_ROOT,root_list(p),SETTINGS_TOP)+lst(9310,ON_CUSTOM,custom_list(p),SETTINGS_TOP)+
       lst(9320,ON_LIBRARY,library_list(p),SETTINGS_TOP)+
       lst(9330,ON_BADGES,switch_list(p,BADGES,top=badges_preview(p)),SETTINGS_TOP)+lst(9340,ON_OSD,switch_list(p,OSD),SETTINGS_TOP)+
       lst(9350,ON_TABS,switch_list(p,TABS_PAGE_ROWS),SETTINGS_TOP)+lst(9360,ON_INFO,switch_list(p,INFO),SETTINGS_TOP)+
       lst(9370,ON_VIEWS,switch_list(p,VIEWS),SETTINGS_TOP)+
       header(p,back,[('Settings',ON_ROOT),('Customisation',ON_CUSTOM),('Library',ON_LIBRARY)]+[(t,c) for _,c,_,_,t in SUBPAGES],SETTINGS_Y,
              '<ondown condition="%s">9300</ondown><ondown condition="%s">9401</ondown><ondown condition="%s">9451</ondown>'%(ON_ROOT,ON_CUSTOM,ON_LIBRARY)+
              ''.join('<ondown condition="%s">%d</ondown>'%(c,f) for _,c,f,_,_ in SUBPAGES))+'</controls>')
 extra=('<onload condition="Window.Previous(home)">ClearProperty(Settings.Page,%s)</onload>'%WINDOW+
        '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>')
 # Back from a category opened on the Customisation page: the home rows are hidden, so focus that page instead.
 extra+='<onload condition="%s">SetFocus(9401)</onload>'%ON_CUSTOM
 extra+='<onload condition="%s">SetFocus(9451)</onload>'%ON_LIBRARY
 extra+='<onload condition="%s">%s</onload>'%(ON_CUSTOM,COUNTS)
 extra+=''.join('<onload condition="%s">SetFocus(%d)</onload>'%(c,f) for _,c,f,_,_ in SUBPAGES)
 extra+='<onload condition="%s">%s</onload>'%(ON_TABS,COUNTS)   # back from a tab's rows: its count again
 return p.window(original,body,'9101',extra)

# --- Search Settings (owner-approved mockup, docs/design/settings-pages-mockups.html, board 11) ---
SEARCH_FIELD=9161;SEARCH_LIST=9160;SEARCH_CARD=8   # property rows: 1..7 draw a card that size; 8 means eight or more
def search_window(p):
 """portrait/IOSSettingsSearch.xml for settings_search.py: Back (9001) and the title, the field (9161, a Kodi edit control
 so iOS opens its keyboard), the matches as a grouped list (9160) on a card that grows with them, and "No settings match"
 (property empty). The page's properties: rows (how many matches the card shows) and empty ('1' when nothing matches)."""
 # field_y: the iPhone's own search field (glassbar kodi_search_context, 116.5-182.5 pt under the safe area) sits here;
 # the Kodi edit control below is only drawn without it (property native empty).
 w=p.WIDTH-2*p.SIDE;field_y=340;field_h=124;list_y=field_y+field_h+40;room=p.HEIGHT-list_y
 kodi_field='<visible>String.IsEmpty(Window().Property(native))</visible>'
 field=('<control type="edit" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
        '<font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><hinttext>Search</hinttext><label></label>'
        '<align>left</align><aligny>center</aligny><textoffsetx>100</textoffsetx>'
        '<texturefocus border="62" colordiffuse="FF3A3A3C">%spill_124.png</texturefocus>'
        '<texturenofocus border="62" colordiffuse="%s">%spill_124.png</texturenofocus>'
        '<onup>9001</onup><ondown>%d</ondown>'+kodi_field+'</control>')%(SEARCH_FIELD,p.SIDE,field_y,w,field_h,p.WHITE,p.WHITE,p.MEDIA,p.SURFACE,p.MEDIA,SEARCH_LIST)
 card=''.join('<control type="group"><visible>String.IsEqual(Window().Property(rows),%d)</visible>%s</control>'
              %(k,p.surface(p.SIDE,0,w,k*ROW2,'group.png',p.SURFACE,RADIUS)) for k in range(1,SEARCH_CARD))
 card+=('<control type="group"><visible>String.IsEqual(Window().Property(rows),%d)</visible>%s</control>'
        %(SEARCH_CARD,p.surface(p.SIDE,0,w,room,'group.png',p.SURFACE,RADIUS)))
 def item(focus):
  # Label and breadcrumb come from ListItem: the label carries [B] around the typed part.
  tag='focusedlayout' if focus else 'itemlayout'
  return ('<%s width="%d" height="%d">'%(tag,w,ROW2)+(p.image(0,0,w,ROW2,p.MEDIA+'white.png','18FFFFFF') if focus else '')+
          p.image(PAD,0,w-PAD,2,p.MEDIA+'white.png',p.SEP,'<visible>!String.IsEqual(ListItem.Property(first),1)</visible>')+
          p.label(PAD,22,w-2*PAD-110,90,'$INFO[ListItem.Label]','p_body',p.WHITE,'left','<scroll>false</scroll>')+
          p.label(PAD,94,w-2*PAD-110,60,'$INFO[ListItem.Label2]','p_foot',p.GREY,'left','<scroll>false</scroll>')+
          p.icon(w-PAD-34,(ROW2-34)//2,34,'chevron-right.png',p.GREY)+'</%s>'%tag)
 results=('<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
          '<orientation>vertical</orientation><itemgap>0</itemgap><onup condition="!String.IsEmpty(Window().Property(native))">9001</onup>'
          '<onup>%d</onup>'
          '<scrolltime tween="cubic" easing="out">160</scrolltime>%s%s</control>')%(SEARCH_LIST,p.SIDE,list_y,w,room,SEARCH_FIELD,item(False),item(True))
 empty=('<control type="group"><visible>!String.IsEmpty(Window().Property(empty))</visible>'+
        p.label(p.SIDE,list_y+60,w,110,'No settings match','p_h3',p.WHITE,'center')+
        p.label(p.SIDE+PAD,list_y+180,w-2*PAD,120,'Try a shorter word or check the spelling.','p_foot',p.GREY,'center',
                '<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+'</control>')
 body=('<controls>'+p.backdrop()+
       '<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height>%s</control>'%(list_y,p.WIDTH,room,card)+
       results+empty+field+
       p.icon(p.SIDE+36,field_y+(field_h-44)//2,44,'magnifying-glass.png',p.GREY,kodi_field)+
       header(p,[('','Close')],[('Search Settings','')],36,'<ondown condition="!String.IsEmpty(Window().Property(native))">%d</ondown><ondown>%d</ondown>'%(SEARCH_LIST,SEARCH_FIELD))+'</controls>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>%s</window>\n')%(p.MARKER,SEARCH_FIELD,body)

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

# --- Section page: a section's categories as rows (owner-approved mockup docs/design/settings-pages-mockups.html, board 1) ---
SECTION_ROWS=9
def section_page(p):
 """portrait/IOSSection.xml for section_page.py: Interface, Player, Media, Services, System, PVR and Games open to their
 categories as rows (tile, name, what is set now) instead of Kodi's chip row. Properties title, subtitle, foot and
 for each row n: sec.n.name / .sub / .icon / .tint; button 9600+n opens category n (9001 closes)."""
 w=p.WIDTH-2*p.SIDE;P=lambda k:'$INFO[Window().Property(%s)]'%k;h=ROW2;tile=100
 order=[(9600+n,'') for n in range(1,SECTION_ROWS+1)]
 moves=nav(order)
 def row(n,y,first):
  q=lambda k:'$INFO[Window().Property(sec.%d.%s)]'%(n,k)
  x=PAD+tile+38
  xml=('<control type="group"><visible>!String.IsEmpty(Window().Property(sec.%d.name))</visible><width>%d</width><height>%d</height>'%(n,w,h)+
       '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s%s</control>'
       %(9600+n,w,h,highlight(p,w,h),nav_xml(p,moves[9600+n])))
  if not first:xml+=p.image(x,0,w-x,2,p.MEDIA+'white.png',p.SEP)
  xml+=(p.surface(PAD,(h-tile)//2,tile,tile,'tile100.png',q('tint'),28)+p.icon(PAD+15,(h-70)//2,70,icon_path(p,q('icon')),p.WHITE)+
        p.label(x,22,w-x-90,64,q('name'),'p_body')+p.label(x,86,w-x-90,56,q('sub'),'p_foot',p.GREY)+
        p.icon(w-PAD-34,(h-34)//2,34,'chevron-right.png',p.DIM)+'</control>')
  return xml
 body=''.join(row(n,0,n==1) for n in range(1,SECTION_ROWS+1))
 card_xml=('<control type="grouplist" id="9310"><left>%d</left><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation><itemgap>0</itemgap>'
           '<usecontrolcoords>false</usecontrolcoords><onup>9001</onup>%s</control>')%(p.SIDE,w,SECTION_ROWS*h,body)
 # The card and the footer under it fit the rows shown (property rows): one background and footer per count.
 fit=''
 for k in range(1,SECTION_ROWS+1):
  fit+=('<control type="group"><visible>String.IsEqual(Window().Property(rows),%d)</visible>'%k+
        p.surface(p.SIDE,0,w,k*h,'group.png',p.SURFACE,RADIUS)+
        p.label(p.SIDE+PAD,k*h+14,w-2*PAD,140,P('foot'),'p_foot',p.GREY,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+'</control>')
 shell='<control type="group"><width>%d</width><height>%d</height>%s%s</control>'%(p.WIDTH,SECTION_ROWS*h+160,fit,card_xml)
 lst=('<control type="grouplist" id="9300"><left>0</left><top>200</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
      '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%p.WIDTH+
      p.label(p.SIDE+PAD,0,w-2*PAD,130,P('title'),'p_large',p.WHITE,'left','<scroll>false</scroll>')+
      '<control type="image"><height>14</height><texture /></control>'+shell+spacer(60)+'</control>')
 page='<controls>'+p.backdrop()+lst+header(p,[('','Close')],[('','')])+'</controls>'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9601</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(p.MARKER,page)

# --- Skin Settings list page (mockup board 6): Fuse's entries of one section as rows -----------------------------
def skin_list_page(p):
 """portrait/IOSSkinList.xml for skin_settings_page.py: a title and one list (9310) whose items carry the properties
 kind (title|switch|button), on (switches) and the label / label2 (a button's value). 9001 closes."""
 w=p.WIDTH-2*p.SIDE;M=p.MEDIA;P=lambda k:'$INFO[Window().Property(%s)]'%k
 L=lambda k:'$INFO[ListItem.Property(%s)]'%k
 kind=lambda k:'String.IsEqual(ListItem.Property(kind),%s)'%k
 def layout(focused):
  bg=(p.image(0,0,w,ROW,M+'white.png','1AFFFFFF','<visible>%s</visible>'%'!%s'%kind('title')) if focused else '')
  return (p.image(0,0,w,ROW,M+'white.png',p.SURFACE,'<visible>!%s</visible>'%kind('title'))+bg+
          p.image(PAD,ROW-2,w-PAD,2,M+'white.png',p.SEP,'<visible>!%s</visible>'%kind('title'))+
          # group title: small grey words sitting on the page, as the Settings pages have
          p.label(PAD,0,w-2*PAD,ROW,L('label'),'p_h3',p.GREY,'left','<aligny>bottom</aligny><scroll>false</scroll><visible>%s + String.IsEmpty(ListItem.Property(note))</visible>'%kind('title'))+
          # Settings › AI Upscale: a grey note under a group (wrapped), and a grey second line under a row; a row with no
          # value on the right gets the width a value would take (rig: "Upscale new downl..." was cut).
          p.textbox(PAD,14,w-2*PAD,ROW-14,L('label'),'p_cap',p.GREY).replace('<control type="textbox">','<control type="textbox"><visible>!String.IsEmpty(ListItem.Property(note))</visible>',1)+
          p.label(PAD,0,w-2*PAD-420,ROW,L('label'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!%s + String.IsEmpty(ListItem.Property(sub)) + !String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(PAD,ROW//2-54,w-2*PAD-420,56,L('label'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!%s + !String.IsEmpty(ListItem.Property(sub)) + !String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(PAD,ROW//2+4,w-2*PAD-420,48,L('sub'),'p_cap',p.GREY,'left','<scroll>false</scroll><visible>!%s + !String.IsEmpty(ListItem.Property(sub)) + !String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(PAD,0,w-2*PAD-200,ROW,L('label'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!%s + String.IsEmpty(ListItem.Property(sub)) + String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(PAD,ROW//2-54,w-2*PAD-200,56,L('label'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!%s + !String.IsEmpty(ListItem.Property(sub)) + String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(PAD,ROW//2+4,w-2*PAD-200,48,L('sub'),'p_cap',p.GREY,'left','<scroll>false</scroll><visible>!%s + !String.IsEmpty(ListItem.Property(sub)) + String.IsEmpty(ListItem.Property(value))</visible>'%kind('title'))+
          p.label(w-PAD-400,0,330,ROW,L('value'),'p_body',p.GREY,'right','<scroll>false</scroll><visible>%s</visible>'%kind('button'))+
          p.icon(w-PAD-34,(ROW-34)//2,34,'chevron-right.png',p.DIM,'<visible>%s</visible>'%kind('button'))+
          p.image(w-PAD-130,(ROW-58)//2,130,58,M+'toggle_on.png',p.WHITE,'<visible>%s + !String.IsEmpty(ListItem.Property(on))</visible>'%kind('switch'))+
          p.image(w-PAD-130,(ROW-58)//2,130,58,M+'toggle_off.png',p.WHITE,'<visible>%s + String.IsEmpty(ListItem.Property(on))</visible>'%kind('switch')))
 lst=('<control type="list" id="9310"><left>%d</left><top>330</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
      '<scrolltime tween="cubic" easing="out">200</scrolltime><onup>9001</onup>'
      '<itemlayout height="%d" width="%d">%s</itemlayout><focusedlayout height="%d" width="%d">%s</focusedlayout></control>')%(
      p.SIDE,w,ROW,w,layout(False),ROW,w,layout(True))
 title=p.label(p.SIDE+PAD,190,w-2*PAD,140,P('title'),'p_large',p.WHITE,'left','<scroll>false</scroll>')
 page='<controls>'+p.backdrop()+lst+title+header(p,[('','Close')],[('','')])+'</controls>'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9310</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(p.MARKER,page)

# --- Add-on Updates (owner-approved mockup, docs/design/settings-pages-mockups.html, board 12) ---
UPDATE_ROWS=8;UPDATE_ROW=9600          # row n is button 9600+n: it opens Kodi's add-on list
UPDATE_CHECK=(9650,9651)               # Check Now: in the empty state, and under the list
def addon_updates_page(p):
 """portrait/IOSAddonUpdates.xml for addon_updates.py. Properties: rows (0 shows the empty state; otherwise the rows to
 show, 8 meaning eight or more), upd.n.name and upd.n.icon for row n, checked (the line under the title) and button
 (Check Now's label). Kodi's own add-on list (addons://outdated/) is what a row opens."""
 w=p.WIDTH-2*p.SIDE;h=ROW2;tile=100;top=360;P=lambda k:'$INFO[Window().Property(%s)]'%k
 is_empty='String.IsEqual(Window().Property(rows),0)';has_rows='!String.IsEqual(Window().Property(rows),0)'
 def button(id,x,y,width):
  return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>124</height>'
          '<label>%s</label><font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
          '<align>center</align><aligny>center</aligny>'
          '<texturefocus border="62" colordiffuse="FF3A3A3C">%spill_124.png</texturefocus>'
          '<texturenofocus border="62" colordiffuse="%s">%spill_124.png</texturenofocus></control>')%(
          id,x,y,width,P('button'),p.ACCENT,p.ACCENT,p.MEDIA,p.SURFACE2,p.MEDIA)
 def row(n):
  q=lambda k:P('upd.%d.%s'%(n,k));x=PAD+tile+38
  xml=('<control type="group"><visible>!String.IsEmpty(Window().Property(upd.%d.name))</visible><width>%d</width><height>%d</height>'%(n,w,h)+
       '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s</control>'
       %(UPDATE_ROW+n,w,h,highlight(p,w,h)))
  if n>1:xml+=p.image(x,0,w-x,2,p.MEDIA+'white.png',p.SEP)
  return xml+(p.surface(PAD,(h-tile)//2,tile,tile,'tile100.png',ORANGE,28)+p.icon(PAD+15,(h-70)//2,70,'puzzle-piece.png',p.WHITE)+
       p.image(PAD,(h-tile)//2,tile,tile,q('icon'),p.WHITE,'<visible>!String.IsEmpty(Window().Property(upd.%d.icon))</visible>'%n,'',p.MEDIA+'tile100.png')+
       p.label(x,22,w-x-90,64,q('name'),'p_body',p.WHITE,'left','<scroll>false</scroll>')+
       p.label(x,86,w-x-90,56,'Update available','p_foot',p.GREY)+
       p.icon(w-PAD-34,(h-34)//2,34,'chevron-right.png',p.GREY)+'</control>')
 # Empty state: a green tick in a tile, the title, when the check last ran, and Check Now.
 tile_x=(p.WIDTH-176)//2
 empty=('<control type="group"><visible>%s</visible>'%is_empty+
        p.surface(tile_x,560,176,176,'group.png',p.SURFACE,RADIUS)+p.icon(tile_x+33,593,110,'check.png',GREEN)+
        p.label(p.SIDE,800,w,110,P('heading'),'p_h3',p.WHITE,'center')+
        p.label(p.SIDE+PAD,930,w-2*PAD,200,P('checked'),'p_sub',p.GREY,'center','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+
        button(UPDATE_CHECK[0],(p.WIDTH-420)//2,1190,420)+'</control>')
 # The list: a card that fits the rows (property rows), then the line under it and Check Now, in one grouplist so they follow the rows.
 card=''.join('<control type="group"><visible>String.IsEqual(Window().Property(rows),%d)</visible>%s</control>'
              %(k,p.surface(p.SIDE,0,w,k*h,'group.png',p.SURFACE,RADIUS)) for k in range(1,UPDATE_ROWS+1))
 foot=('<control type="group"><visible>%s</visible><width>%d</width><height>150</height>'%(has_rows,w)+
       p.label(PAD,14,w-2*PAD,130,P('checked'),'p_foot',p.GREY,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+'</control>')
 check=('<control type="group"><visible>%s</visible><width>%d</width><height>160</height>'%(has_rows,w)+button(UPDATE_CHECK[1],(w-420)//2,26,420)+'</control>')
 lst=('<control type="grouplist" id="9310"><left>%d</left><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
      '<itemgap>0</itemgap><usecontrolcoords>false</usecontrolcoords>%s%s%s</control>')%(p.SIDE,w,UPDATE_ROWS*h+400,
      ''.join(row(n) for n in range(1,UPDATE_ROWS+1)),foot,check)
 rows_block=('<control type="group"><visible>%s</visible><left>0</left><top>%d</top><width>%d</width><height>%d</height>%s%s</control>'
             %(has_rows,top,p.WIDTH,UPDATE_ROWS*h+400,card,lst))
 body=('<controls>'+p.backdrop()+empty+rows_block+
       header(p,[('','Close')],[('Add-on Updates','')],36,
              '<ondown condition="%s">%d</ondown><ondown>%d</ondown>'%(is_empty,UPDATE_CHECK[0],UPDATE_ROW+1))+'</controls>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>%s</window>\n')%(p.MARKER,9001,body)

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
SEGMENTS=4   # board 08: up to four add-on setting sections side by side; more scroll sideways
def setting_templates(p,category_type,segmented=False):
 """The row templates Kodi copies for every setting: full-width iOS cells, 52 pt high, hairline gaps between them."""
 w=p.WIDTH-2*p.SIDE;M=p.MEDIA;base='<width>%d</width><height>%d</height>'%(w,ROW)
 if segmented:
  # Roadmap 2.3 (board 08): a segmented control: equal segments on one track, the chosen one lighter.
  seg=(w-12)//SEGMENTS
  pill=('<control type="%s" id="10"><width>%d</width><height>84</height><label></label><font>p_foot_b</font><textcolor>%s</textcolor>'
        '<focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
        '<texturefocus border="40" colordiffuse="FF636366">%spill_96.png</texturefocus><texturenofocus />'
        %(category_type,seg,p.GREY,p.WHITE,M))
 else:
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
  # The label stops before the switch (build 224 rig audit: "Announce services to other systems", "Ignore different
  # video versions on scan" and add-on settings ran under the switch).
  ('<control type="radiobutton" id="8">%s%s%s<textwidth>%d</textwidth><radiowidth>130</radiowidth><radioheight>58</radioheight><radioposx>%d</radioposx>'
   '<textureradioonfocus>%stoggle_on.png</textureradioonfocus><textureradioonnofocus>%stoggle_on.png</textureradioonnofocus>'
   '<textureradioofffocus>%stoggle_off.png</textureradioofffocus><textureradiooffnofocus>%stoggle_off.png</textureradiooffnofocus>'
   '<textureradioondisabled colordiffuse="66FFFFFF">%stoggle_on.png</textureradioondisabled><textureradiooffdisabled colordiffuse="66FFFFFF">%stoggle_off.png</textureradiooffdisabled>'
   '</control>')%(base,row_textures(p),text_style(p),w-2*PAD-130-24,w-PAD-130,M,M,M,M,M,M)+
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

def setting_body(p,title,header_buttons,extra='',categories=True,paged=False,segmented=False):
 """Header (title = label 2), category pills (grouplist 3), settings (grouplist 5), help text (label 6)."""
 w=p.WIDTH-2*p.SIDE
 bar=p.image(0,0,p.WIDTH,(LIST_TOP if categories else 200)-10,p.MEDIA+'white.png',p.BG)
 heading=('<control type="label" id="2"><left>300</left><top>36</top><width>%d</width><height>108</height><font>p_h3</font>'
          '<textcolor>%s</textcolor><align>center</align><aligny>center</aligny><scroll>false</scroll><label>%s</label>%s</control>')%(p.WIDTH-600,p.WHITE,p.e(title),'<visible>String.IsEmpty(Window(Home).Property(KodiIOS.CategoryPage))</visible>' if paged else '')
 # Opened from a section page row (section_page.py sets KodiIOS.CategoryPage): the chip row slides out of sight (it must
 # stay "visible" so Kodi can focus its buttons and load that category) and the category's name is a large title.
 paged_on='!String.IsEmpty(Window(Home).Property(KodiIOS.CategoryPage))'
 hide=('<animation effect="slide" end="0,-700" time="0" condition="%s">Conditional</animation>'%paged_on) if paged else ''
 if segmented:
  # One rounded track behind the segments (board 08); the grouplist sits 6 px inside it.
  track=('<control type="image"><left>%d</left><top>200</top><width>%d</width><height>96</height><texture border="48" colordiffuse="%s">%spill_96.png</texture>%s</control>'
         %(p.SIDE,w,p.SURFACE,p.MEDIA,'' if categories else '<visible>false</visible>'))
  cats=track+('<control type="grouplist" id="3"><left>%d</left><top>206</top><width>%d</width><height>84</height><orientation>horizontal</orientation>'
       '<itemgap>0</itemgap><scrolltime tween="cubic" easing="out">250</scrolltime><ondown>5</ondown><onup>9001</onup>%s%s</control>')%(
       p.SIDE+6,w-12,'' if categories else '<visible>false</visible>',hide)
 else:
  cats=('<control type="grouplist" id="3"><left>%d</left><top>200</top><width>%d</width><height>96</height><orientation>horizontal</orientation>'
       '<itemgap>16</itemgap><scrolltime tween="cubic" easing="out">250</scrolltime><ondown>5</ondown><onup>9001</onup>%s%s</control>')%(
       p.SIDE,w,'' if categories else '<visible>false</visible>',hide)
 big=(p.label(p.SIDE+PAD,190,w-2*PAD,140,'$INFO[Window(Home).Property(KodiIOS.CategoryPage)]','p_large',p.WHITE,'left','<scroll>false</scroll><visible>%s</visible>'%paged_on)
      if paged else '')
 lst=('<control type="grouplist" id="5"><left>%d</left><top>%d</top><width>%d</width><bottom>%d</bottom><orientation>vertical</orientation>'
      '<itemgap>2</itemgap><usecontrolcoords>false</usecontrolcoords><onup>3</onup><scrolltime tween="cubic" easing="out">250</scrolltime></control>')%(
      p.SIDE,LIST_TOP if categories else 200,w,HELP_H)
 # Anchored to the bottom: the 9:16 resolution (home-button phones) has a shorter canvas than 9:19.5.
 help_=('<control type="image"><left>0</left><bottom>0</bottom><width>%d</width><height>%d</height><texture colordiffuse="%s">%swhite.png</texture></control>'
        %(p.WIDTH,HELP_H,p.BG,p.MEDIA)+
        '<control type="label" id="6"><width>1</width><height>1</height><visible>false</visible></control>'+
        '<control type="textbox"><left>%d</left><bottom>16</bottom><width>%d</width><height>%d</height><font>p_foot</font><textcolor>%s</textcolor>'
        '<label>$INFO[Control.GetLabel(6)]</label><autoscroll>false</autoscroll></control>')%(p.SIDE+PAD,w-2*PAD,HELP_H-40,p.GREY)
 return '<controls>'+p.backdrop()+lst+bar+heading+big+cats+help_+header_buttons+extra+'</controls>'

def category_window(p,original):
 """portrait/SettingsCategory.xml: System, Player, Media, Interface, Services, PVR and Games pages."""
 back=p.nav_button(9001,p.SIDE,36,'chevron-left.png','Action(Back)','<ondown>3</ondown>')
 # From a section page row, Back returns to that section page (it was closed to open this one).
 back=back.replace('<onclick>Action(Back)</onclick>','<onclick condition="!String.IsEmpty(Window(Home).Property(KodiIOS.CategorySection))">'
                   'RunScript(service.kodi.ios.bootstrap,section_page,$INFO[Window(Home).Property(KodiIOS.CategorySection)])</onclick><onclick>Action(Back)</onclick>',1)
 level=('<control type="button" id="20"><left>%d</left><top>36</top><width>290</width><height>108</height><font>p_foot_b</font>'
        '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
        '<texturefocus border="54" colordiffuse="FF48484A">%spill_108.png</texturefocus><texturenofocus border="54" colordiffuse="%s">%spill_108.png</texturenofocus>'
        '<onclick>settingslevelchange</onclick><ondown>3</ondown><onleft>9001</onleft></control>')%(p.WIDTH-p.SIDE-290,BLUE,BLUE,p.MEDIA,p.SURFACE,p.MEDIA)
 body=setting_body(p,'',back+level,setting_templates(p,'togglebutton'),paged=True)
 return p.window(original,body,'5','<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>'
                 '<onunload>ClearProperty(KodiIOS.CategoryPage,Home)</onunload><onunload>ClearProperty(KodiIOS.CategorySection,Home)</onunload>')

def addon_settings_window(p,original,categories=True):
 """portrait/DialogAddonSettings.xml: every add-on's settings (Elementum, Umbrella, Trakt...) as an iOS sheet with
 Cancel and Done. 28/29 are Kodi's OK and Cancel; 20 and 30 stay hidden as in Fuse."""
 text_button=lambda id,x,text,color,bold,align:(('<control type="button" id="%d"><left>%d</left><top>36</top><width>240</width><height>108</height><textoffsetx>0</textoffsetx>'
   '<label>%s</label><font>%s</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>%s</align><aligny>center</aligny>'
   '<texturefocus /><texturenofocus /><ondown>3</ondown></control>')%(id,x,text,'p_btn' if bold else 'p_body',color,'FF64D2FF',align))
 hidden=''.join('<control type="button" id="%d"><width>1</width><height>1</height><visible>false</visible><texturefocus /><texturenofocus /></control>'%i for i in (20,30))
 # Board 08: Kodi writes "OK" on 28 and "Settings - <add-on>" as the title; both are drawn transparent and the board's
 # "Done" and the add-on's own name (System.AddonTitle of the Addon.ID property Kodi sets) are drawn over them.
 buttons=(text_button(29,p.SIDE,'Cancel',BLUE,False,'left')+text_button(28,p.WIDTH-p.SIDE-240,'Done','00FFFFFF',True,'right').replace('<focusedcolor>FF64D2FF</focusedcolor>','<focusedcolor>00FFFFFF</focusedcolor>')+
          p.label(p.WIDTH-p.SIDE-240,36,240,108,'[B]Done[/B]','p_btn',BLUE,'right','<visible>!Control.HasFocus(28)</visible>')+
          p.label(p.WIDTH-p.SIDE-240,36,240,108,'[B]Done[/B]','p_btn','FF64D2FF','right','<visible>Control.HasFocus(28)</visible>')+
          p.label(300,36,p.WIDTH-600,108,'[B]$INFO[System.AddonTitle($INFO[Window.Property(Addon.ID)])][/B]','p_h3',p.WHITE,'center','<scroll>false</scroll>')+hidden)
 body=setting_body(p,'',buttons,setting_templates(p,'button',segmented=True),categories,segmented=True)
 body=body.replace('<font>p_h3</font><textcolor>%s</textcolor><align>center</align><aligny>center</aligny><scroll>false</scroll><label></label>'%p.WHITE,
                   '<font>p_h3</font><textcolor>00FFFFFF</textcolor><align>center</align><aligny>center</aligny><scroll>false</scroll><label></label>',1)
 return p.window(original,body,'5','<animation effect="slide" start="0,300" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
                 '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>')

# --- Profiles and Favourites pages (owner-approved mockup boards 09 and 10: profiles_page.py, favourites_page.py) ---
def _module(name):
 spec=_iu.spec_from_file_location(name,os.path.join(os.path.dirname(os.path.abspath(__file__)),name+'.py'))
 module=_iu.module_from_spec(spec);spec.loader.exec_module(module);return module
profiles_rows=_module('profiles_rows');favourites_rows=_module('favourites_rows');choice_sheet=_module('choice_sheet')

def profile_row(p,n,w):
 """Profile n (shown while its name is set): picture or initials, its name and, for the current profile, "Signed in now"
 with a blue tick. Button 9600+n switches to it. The rows sit in a grouplist, so their positions follow the count."""
 flag=lambda k:'Window().Property(profile.%d.%s)'%(n,k)
 P=lambda k:'$INFO[%s]'%flag(k)
 shown='!String.IsEmpty(%s)'%flag('name');current='String.IsEqual(%s,true)'%flag('current');thumb='!String.IsEmpty(%s)'%flag('thumb')
 h=ROW2;a=130;x=PAD+a+40;ay=(h-a)//2;tw=w-x-PAD-110
 return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,h,shown)+
  '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s%s</control>'
  %(9600+n,w,h,highlight(p,w,h),'<onup>9001</onup>' if n==1 else '')+
  (p.image(x,0,w-x,2,p.MEDIA+'white.png',p.SEP) if n>1 else '')+
  p.surface(PAD,ay,a,a,'avatar_s.png','FF7B88C4')+p.label(PAD,ay,a,a,P('initials'),'p_h3',p.WHITE,'center','<visible>!%s</visible>'%thumb)+
  p.image(PAD,ay,a,a,P('thumb'),p.WHITE,'<visible>%s</visible>'%thumb,'',p.MEDIA+'avatar_s.png')+
  p.label(x,0,tw,h,P('name'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!%s</visible>'%current)+
  p.label(x,26,tw,70,P('name'),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>%s</visible>'%current)+
  p.label(x,96,tw,56,profiles_rows.SIGNED_IN,'p_foot',p.GREY,'left','<visible>%s</visible>'%current)+
  p.icon(w-PAD-40,(h-50)//2,50,'check.png',p.ACCENT,'<visible>%s</visible>'%current)+'</control>')

def profiles_page(p):
 """portrait/IOSProfiles.xml for profiles_page.py (Settings > Profiles, mockup board 09): one row per profile, then Add
 Profile in blue, and the footer under the card. Window properties: rows (profiles + 1), profile.n.name / initials /
 thumb / current. Buttons 9600+n switch to profile n, 9609 opens Kodi's Profiles window, 9001 closes."""
 w=p.WIDTH-2*p.SIDE;h=ROW2;n_rows=profiles_rows.MAX+1;x=PAD+130+40
 add=('<control type="group"><width>%d</width><height>%d</height>'%(w,h)+
  '<control type="button" id="9609"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>%s</control>'%(w,h,highlight(p,w,h))+
  p.image(x,0,w-x,2,p.MEDIA+'white.png',p.SEP)+
  p.surface(PAD,(h-130)//2,130,130,'avatar_s.png',p.SURFACE2)+p.label(PAD,(h-130)//2,130,130,'+','p_h2',p.ACCENT,'center')+
  p.label(x,0,w-x-PAD,h,profiles_rows.ADD,'p_body',p.ACCENT,'left','<scroll>false</scroll>')+'</control>')
 rows=''.join(profile_row(p,n,w) for n in range(1,profiles_rows.MAX+1))+add
 # The card's background and the footer under it are drawn for each row count (property rows), as section_page does.
 fit=''.join('<control type="group"><visible>String.IsEqual(Window().Property(rows),%d)</visible>'%k+
  p.surface(p.SIDE,0,w,k*h,'group.png',p.SURFACE,RADIUS)+
  p.label(p.SIDE+PAD,k*h+14,w-2*PAD,140,profiles_rows.FOOT,'p_foot',p.GREY,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+'</control>'
  for k in range(1,n_rows+1))
 shell=('<control type="group"><width>%d</width><height>%d</height>%s'%(p.WIDTH,n_rows*h+160,fit)+
  '<control type="grouplist" id="9310"><left>%d</left><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><usecontrolcoords>false</usecontrolcoords>%s</control></control>')%(p.SIDE,w,n_rows*h,rows)
 lst=('<control type="grouplist" id="9300"><left>0</left><top>200</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
      '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%p.WIDTH+
      p.label(p.SIDE,0,w,130,'Profiles','p_large',p.WHITE,'left','<scroll>false</scroll>')+
      spacer(14)+shell+spacer(60)+'</control>')
 page='<controls>'+p.backdrop()+lst+header(p,[('','Close')],[('Profiles','')])+'</controls>'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9601</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(p.MARKER,page)

def rank_badge(p,prop,x,y,tag):
 """A small dark pill on a poster: the imported list's rank ("#3") or watch count ("3x"). Drawn only while the property is set.
 A flat translucent chip (a Kodi-drawn surface, not glass): at least 70 % black so it reads over any artwork."""
 return ('<control type="group"><left>%d</left><top>%d</top><visible>!String.IsEmpty(Window().Property(%s))</visible>'%(x,y,prop[len('Window().Property('):-1])+
  p.surface(0,0,104,48,'pill_96.png','B3000000',24)+p.label(0,0,104,48,'$INFO[%s]'%prop,'p_foot_b',p.WHITE,'center')+'</control>')

def favourite_cell(p,n,x,y,cw,ch):
 """Poster n (shown while its title is set): the Movies grid's poster card and art, its title under it, and in Edit mode a
 red remove badge on the favourites Favourites.AddFavourite can remove. Button 9700+n opens it (or removes it in Edit)."""
 flag=lambda k:'Window().Property(fav.%d.%s)'%(n,k)
 shown='!String.IsEmpty(%s)'%flag('title')
 badge='String.IsEqual(%s,true) + !String.IsEmpty(Window().Property(editing))'%flag('removable')
 cap=96
 return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><visible>%s</visible>'%(x,y,cw,ch+cap,shown)+
  '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus /></control>'%(9700+n,cw,ch+cap)+
  '<control type="group"><animation effect="zoom" start="100" end="104" time="160" center="auto" tween="cubic" easing="out" condition="Control.HasFocus(%d)">Conditional</animation>'%(9700+n)+
  p.image(0,0,cw,ch,p.MEDIA+'white.png',p.SURFACE,'','',p.MEDIA+'poster_mask.png')+
  p.image(0,0,cw,ch,'$INFO[%s]'%flag('thumb'),p.WHITE,'','>scale',p.MEDIA+'poster_mask.png',background=True)+
  p.label(0,ch+14,cw,cap-14,'$INFO[%s]'%flag('title'),'p_foot_b',p.WHITE,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+
  rank_badge(p,flag('rank'),12,12,'top')+rank_badge(p,flag('watched'),12,ch-60,'bottom')+
  '<control type="group"><left>%d</left><top>14</top><visible>%s</visible>'%(cw-70,badge)+
  p.image(0,0,56,56,p.MEDIA+'avatar_s.png',RED)+p.image(2,2,52,52,p.MEDIA+'close_cross.png',p.WHITE)+'</control></control></control>')

def favourites_page(p):
 """portrait/IOSFavourites.xml for favourites_page.py (Settings > Favourites, mockup board 10): the favourites as a poster
 grid, three across, the empty state, the footer, and Edit (top right) that shows remove badges. Window properties:
 count, fav.n.title / thumb / removable. Buttons 9700+n open favourite n (or remove it in Edit); 9010 Edit, 9011 Done."""
 w=p.WIDTH-2*p.SIDE;cols=3;cw=(w-(cols-1)*p.GAP)//cols;ch=cw*3//2;cap=96;row_h=ch+cap+p.GAP
 rows=''.join('<control type="group"><width>%d</width><height>%d</height><visible>!String.IsEmpty(Window().Property(fav.%d.title))</visible>%s</control>'%(
   p.WIDTH,row_h,3*r+1,''.join(favourite_cell(p,3*r+c+1,p.SIDE+c*(cw+p.GAP),0,cw,ch) for c in range(cols)))
   for r in range(favourites_rows.MAX//cols))
 # DEC-045 board F1: the star in a yellow-tinted disc, what is empty, and how to add one (policy §6).
 empty=('<control type="group"><width>%d</width><height>760</height><visible>String.IsEmpty(Window().Property(count)) | String.IsEqual(Window().Property(count),0)</visible>'%p.WIDTH+
  p.image(p.WIDTH//2-86,180,172,172,p.MEDIA+'avatar_s.png','29FFD60A')+p.icon(p.WIDTH//2-66,200,132,'star.png','FFFFD60A')+
  p.label(p.SIDE,390,w,70,favourites_rows.EMPTY,'p_h3',p.WHITE,'center')+
  p.label(p.SIDE+60,470,w-120,100,favourites_rows.EMPTY_LINE,'p_foot',p.GREY,'center','<wrapmultiline>true</wrapmultiline>')+
  p.pill_button(9032,p.SIDE+90,600,w-180,124,'Import a List',[],'primary','')+'</control>')
 none=('<control type="group"><width>%d</width><height>160</height><visible>!String.IsEmpty(Window().Property(none))</visible>'%p.WIDTH+
  p.label(p.SIDE,40,w,60,'$INFO[Window().Property(none)]','p_foot',p.GREY,'center')+'</control>')
 import importlib.util as _u,os as _os
 _sp=_u.spec_from_file_location('notifications_skin',_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'notifications_skin.py'))
 ns=_u.module_from_spec(_sp);_sp.loader.exec_module(ns)
 chips=('<control type="group"><width>%d</width><height>130</height><visible>!String.IsEmpty(Window().Property(chips))</visible>'%p.WIDTH+
  ns.segmented(p,favourites_rows.FILTERS,y=0,base=9020)+'</control>')
 tool=('<control type="group"><width>%d</width><height>130</height><visible>!String.IsEmpty(Window().Property(chips))</visible>'%p.WIDTH+
  '<control type="button" id="9030"><left>%d</left><top>6</top><width>420</width><height>118</height><label>Import a List</label>'
  '<font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>left</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /></control>'%(p.SIDE,p.ACCENT,p.ACCENT)+
  '<control type="button" id="9031"><left>%d</left><top>6</top><width>520</width><height>118</height><label>$INFO[Window().Property(sortlabel)]</label>'
  '<font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /></control>'%(p.WIDTH-p.SIDE-520,p.ACCENT,p.ACCENT)+'</control>')
 lst=('<control type="grouplist" id="9300"><left>0</left><top>200</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
      '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%p.WIDTH+
      p.label(p.SIDE,0,w,130,favourites_rows.TITLE,'p_large',p.WHITE,'left','<scroll>false</scroll>')+
      spacer(14)+chips+tool+rows+none+empty+spacer(160)+'</control>')
 has='!String.IsEmpty(Window().Property(fav.1.title))';editing='!String.IsEmpty(Window().Property(editing))'
 # Edit and Done are text buttons in the header's right corner, in the accent blue like Cancel and Done in the sheets.
 edit=('<control type="button" id="9010"><left>%d</left><top>36</top><width>240</width><height>108</height><label>Edit</label>'
  '<font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /><visible>String.IsEmpty(Window().Property(editing)) + %s</visible><ondown>9300</ondown></control>')%(
  p.WIDTH-p.SIDE-240,p.ACCENT,p.ACCENT,has)
 done=('<control type="button" id="9011"><left>%d</left><top>36</top><width>240</width><height>108</height><label>Done</label>'
  '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>right</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /><visible>%s</visible><ondown>9300</ondown></control>')%(p.WIDTH-p.SIDE-240,p.ACCENT,p.ACCENT,editing)
 page='<controls>'+p.backdrop()+lst+header(p,[('','Close')],[])+edit+done+'</controls>'   # DEC-045 F: one title (the large one)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9001</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(p.MARKER,page)

def files(p,read):
 """{relative path: bytes} for the portrait folder and its textures."""
 out={p.FOLDER+'/Settings.xml':settings_window(p,read('Settings.xml')).encode(),
      p.FOLDER+'/IOSAccounts.xml':accounts_page(p).encode(),
      p.FOLDER+'/IOSSection.xml':section_page(p).encode(),
      p.FOLDER+'/IOSSkinList.xml':skin_list_page(p).encode(),
      p.FOLDER+'/IOSProfiles.xml':profiles_page(p).encode(),
      p.FOLDER+'/IOSFavourites.xml':favourites_page(p).encode(),
      p.FOLDER+'/IOSSettingsSearch.xml':search_window(p).encode(),
      p.FOLDER+'/IOSAddonUpdates.xml':addon_updates_page(p).encode(),
      p.FOLDER+'/'+choice_sheet.WINDOW:choice_sheet.window(p).encode(),
      p.FOLDER+'/SettingsCategory.xml':category_window(p,read('SettingsCategory.xml')).encode(),
      p.FOLDER+'/DialogAddonSettings.xml':addon_settings_window(p,read('DialogAddonSettings.xml')).encode()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
