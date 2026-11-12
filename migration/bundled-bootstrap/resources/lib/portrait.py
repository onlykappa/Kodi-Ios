"""r11 portrait layout for Arctic Fuse 3 on iPhone: Netflix rows with an Apple TV app look.

Kodi picks the skin folder whose aspect is closest to the screen, so Fuse gets a `portrait` folder next to
`1080i`. Home, the TV/Movies/Downloads hubs, the show page (MyVideoNav), the info page, the select dialog
(the watch chooser) and the More menu are drawn for portrait. Every other window is the landscape Fuse
window shrunk into the middle of the portrait screen, so nothing becomes unreachable.

The same module builds the folder into the IPA (scripts/build_customized_ipa.py) and, on the phone,
refreshes the rows from the owner's widget lists and reloads the skin when the phone rotates.
"""
import sys
import hashlib,json,os,re,struct,zlib,xml.etree.ElementTree as ET
import importlib.util as _iu
for _name in ('status_ui','notifications_skin'):
 _shared=_iu.spec_from_file_location(_name,os.path.join(os.path.dirname(os.path.abspath(__file__)),_name+'.py'))
 _module=_iu.module_from_spec(_shared);sys.modules[_name]=_module;_shared.loader.exec_module(_module)
_spec=_iu.spec_from_file_location('player_osd',os.path.join(os.path.dirname(os.path.abspath(__file__)),'player_osd.py'))
player_osd=_iu.module_from_spec(_spec);_spec.loader.exec_module(player_osd)
_spec=_iu.spec_from_file_location('settings_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'settings_page.py'))
settings_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(settings_page)
_spec=_iu.spec_from_file_location('pages',os.path.join(os.path.dirname(os.path.abspath(__file__)),'pages.py'))
pages=_iu.module_from_spec(_spec);_spec.loader.exec_module(pages)
_spec=_iu.spec_from_file_location('activity_skin',os.path.join(os.path.dirname(os.path.abspath(__file__)),'activity_skin.py'))
activity_skin=_iu.module_from_spec(_spec);_spec.loader.exec_module(activity_skin)
_spec=_iu.spec_from_file_location('library_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'library_page.py'))
library_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(library_page)
_spec=_iu.spec_from_file_location('notice_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'notice_page.py'))
notice_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(notice_page)
_spec=_iu.spec_from_file_location('transfers_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'transfers_page.py'))
transfers_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(transfers_page)
_spec=_iu.spec_from_file_location('library_tools_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'library_tools_page.py'))
library_tools_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(library_tools_page)
_spec=_iu.spec_from_file_location('rows_page',os.path.join(os.path.dirname(os.path.abspath(__file__)),'rows_page.py'))
rows_page=_iu.module_from_spec(_spec);_spec.loader.exec_module(rows_page)
from pathlib import Path
from xml.sax.saxutils import escape

REVISION='ios-portrait-r3'
FOLDER='portrait'
# iPhone 16 Pro portrait: 402x874 pt with 62/34 pt safe-area insets. Kodi stretches the skin canvas into
# the safe area, so 1080 x 2090 keeps pixels square there (1 pt = 2.687 units). 9:16 covers home-button phones.
# The aspect label is the canvas's true ratio: Kodi chooses a resolution by the ratio its *label* states
# (CSkinInfo closestRes / RESOLUTION_INFO::DisplayRatio), not by width/height. The old '9:19.5' (0.462) lost to
# '9:16' (0.563) on the 16 Pro's 0.517 safe area, so the phone drew every portrait page on 1080 x 1920 stretched
# 9 % taller: circles became ovals and anything placed near the bottom ran off screen (owner, build 154).
WIDTH,HEIGHT=1080,2090
RES=[('1080:2090',WIDTH,HEIGHT),('9:16',WIDTH,1920)]
MARKER='Kodi-iOS portrait '+REVISION
NODES='addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-{}.json'
ICONS='special://skin/extras/icons/'
MEDIA='special://skin/extras/portrait/'
DRIVE='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
MENU='RunScript(service.kodi.ios.bootstrap,navigation_menu)'
UPDATES='RunScript(service.kodi.ios.bootstrap,check_updates)'
# iOS dark palette: system background, grouped surfaces, secondary/tertiary labels.
BG='FF000000';SURFACE='FF1C1C1E';SURFACE2='FF2C2C2E';WHITE='FFFFFFFF'
GREY='99EBEBF5';DIM='4DEBEBF5';SEP='33EBEBF5';GREEN='FF30D158'
# window file -> (title, widget lists, tab)
# window file -> (title, widget lists, tab, Continue Watching type)
HUBS={'Home.xml':('Home',['homewidgets'],'home','all'),
      'Custom_1101_Hub.xml':('TV Shows',['1101widgets'],'tv','episode'),
      'Custom_1102_Hub.xml':('Movies',['1102widgets'],'movies','movie')}
SPOTLIGHT={'Home.xml':'home','Custom_1101_Hub.xml':'1101','Custom_1102_Hub.xml':'1102'}
LIBRARY_FILES=('Custom_1103_Hub.xml','Custom_1104_Hub.xml')
SEARCH_FILE='Custom_1105_Search.xml'
CONTINUE='plugin://plugin.video.kodi.ios.watch/?action=continue&type='
# Floating tab bar (Apple TV app): Home, Movies, TV, Library (downloaded media), Search.
# Home, Movies and TV are one window (Home.xml) with a group per hub, so all three load their rows at start and
# switching between them only changes Window(Home).Property(Portrait.Tab); Custom_1101/1102 forward to it.
_spec=_iu.spec_from_file_location('ios_tabs',os.path.join(os.path.dirname(os.path.abspath(__file__)),'ios_tabs.py'))
ios_tabs=_iu.module_from_spec(_spec);_spec.loader.exec_module(ios_tabs)
TAB_PROPERTY,HUB_TABS,HUB_OFFSET=ios_tabs.TAB_PROPERTY,ios_tabs.HUB_TABS,ios_tabs.HUB_OFFSET
tab_actions=ios_tabs.tab_actions
def tab_visible(key):
 return 'String.IsEmpty(Window(Home).Property(%s))'%TAB_PROPERTY if key=='home' else 'String.IsEqual(Window(Home).Property(%s),%s)'%(TAB_PROPERTY,key)
TABS=ios_tabs.TABS
TAB_CLEAR=320                # the last row scrolls fully above the floating tab bar (and the home indicator)
ACCENT='FF4FA8FF'
def titled_page(title,path):
 # A TMDb Helper folder is named after the add-on; the page shows the tile's name instead (cleared on the hubs).
 return 'SetProperty(Portrait.Title,%s,home)\x00ActivateWindow(Videos,%s,return)'%(title,path)
# Library: Kodi's own library together with the downloads kept in Google Drive › Kodi Downloads (owner, 2026-11-02:
# "this needs to be linked to library, not gear to Drive"); the watch add-on lists both (ios_library.py).
LIBRARY_PAGE='plugin://plugin.video.kodi.ios.watch/?action=library&type='
LIBRARY=[('Movies','film.png',titled_page('Movies',LIBRARY_PAGE+'movie')),
         ('TV Shows','tv.png',titled_page('TV Shows',LIBRARY_PAGE+'tv'))]
TMDB='plugin://plugin.video.themoviedb.helper/'
SEARCH_ACTION='ActivateWindow(Videos,%s?info=search&tmdb_type=multi,return)'%TMDB
# Search page categories (TMDb TV genres) with their tile gradients.
CATEGORIES=[('Drama',18,(52,92,190),(12,18,52)),('Comedy',35,(44,196,182),(22,86,150)),('Crime',80,(196,48,48),(58,10,22)),
            ('Sci-Fi & Fantasy',10765,(122,72,232),(30,18,96)),('Action & Adventure',10759,(244,132,44),(150,32,24)),
            ('Animation',16,(252,176,64),(222,72,128)),('Mystery',9648,(70,84,110),(14,18,30)),('Documentary',99,(46,150,90),(10,58,40)),
            ('Reality',10764,(234,84,164),(112,28,122)),('Kids',10762,(84,176,252),(56,86,222)),('Family',10751,(250,204,84),(238,118,58)),
            ('War & Politics',10768,(130,118,86),(40,34,24))]
# More (the profile button): iOS Settings-style rows with coloured icon tiles.
MORE=[('Settings','gear.png','FF8E8E93','ActivateWindow(settings)'),
      ('Google Drive','cloud.png','FF0A84FF',DRIVE),
      ('Check for updates','cloud-arrow-down.png','FF30D158',UPDATES),
      ('Favourites','star.png','FFFF9F0A','RunScript(service.kodi.ios.bootstrap,favourites_page)'),
      # Roadmap 2.6: Kodi's desktop file manager replaced by the app's own Transfers page.
      ('Transfers','clapperboard.png','FF5E5CE6','RunScript(service.kodi.ios.bootstrap,activity_page)'),
      ('iPhone navigation / recovery','life-ring.png','FFFF453A',MENU)]
HANDMADE=set(HUBS)|set(LIBRARY_FILES)|{'Includes_Portrait.xml',SEARCH_FILE,'Startup.xml','Custom_1198_Dialog_Startup.xml','DialogContextMenu.xml','Custom_1182_Dialog_Topmenu_Overlay.xml','MyVideoNav.xml','DialogVideoInfo.xml','DialogSelect.xml','Custom_1170_Dialog_Options.xml','Font.xml','Includes.xml','Settings.xml','SettingsCategory.xml','DialogAddonSettings.xml',activity_skin.NAME,activity_skin.BOX}|pages.HANDMADE
# Never shrunk: playback stays landscape, and these are not windows.
SKIP_WRAP={'VideoFullScreen.xml','VideoOSD.xml','MusicVisualisation.xml','SlideShow.xml','Pointer.xml'}
# Shown only over landscape playback: no portrait copy, so Kodi always loads them from 1080i with landscape
# coordinates (it picks a window's folder when it loads it, and these load while the phone is still upright).
VIDEO_ONLY={'DialogSeekBar.xml','Custom_1156_Buffering.xml','DialogFullScreenInfo.xml','DialogSubtitles.xml','VideoOSDBookmarks.xml','DialogPVRChannelsOSD.xml',
            'GameOSD.xml','MusicOSD.xml','Custom_1140_OSD_Playlist.xml','Custom_1141_OSD_Cast.xml','Custom_1142_OSD_MusicTracks.xml',
            'Custom_1143_OSD_NextOverlay.xml','Custom_1145_OSD_InfoPanel.xml','Custom_1146_OSD_AudioStreams.xml',
            'Custom_1147_OSD_SubtitleStreams.xml','Custom_1148_OSD_VideoStreams.xml','Custom_1151_OSD_MusicInfoOverlay.xml',
            'Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml','Custom_1193_VideoOSDInfo.xml',
            'IOSPlayOnTV.xml','IOSAirPlayFlow.xml','IOSTrackMenu.xml'}   # pages.play_on_tv, pages.track_menu, airplay_flow: Play on TV over video
# iOS text styles at 2.687 units/pt (large title 34pt, title2 22pt, headline/body 17pt, subhead 15pt, footnote 13pt...).
FONTS=[('p_large','Inter-Bold.ttf',92),('p_title','Inter-Bold.ttf',78),('p_h2','Inter-Bold.ttf',58),
       ('p_h3','Inter-Bold.ttf',46),('p_body','Inter-Regular.ttf',44),('p_sub','Inter-Regular.ttf',40),
       ('p_foot','Inter-Regular.ttf',35),('p_foot_b','Inter-Bold.ttf',35),('p_cap','Inter-Regular.ttf',30),
       ('p_tab','Inter-Bold.ttf',27),('p_tile','Inter-Bold.ttf',38),('p_btn','Inter-Bold.ttf',46),
       ('p_pill','Inter-Bold.ttf',40),('p_pill_s','Inter-Regular.ttf',35)]   # the activity pill (activity_skin.py)
SIDE=54                      # 20 pt margins
POSTER=(300,450);CARD=(640,360);GAP=26;RADIUS=26
HERO=1420
# Pages scroll above the floating tab bar, so the row in focus is never hidden under it.
PAGE_H=HEIGHT
CAPSULES=(56,72,96,108,112,124,126,128,150,170,246)

# --- tiny PNG writer (no PIL on the build host) -------------------------------------------------------
def types_ns():
 import types;return types.SimpleNamespace(png=png,coverage=coverage)

def png(width,height,pixel):
 rows=b''.join(b'\0'+b''.join(struct.pack('4B',*pixel(x,y)) for x in range(width)) for y in range(height))
 chunk=lambda tag,data:struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')

def coverage(x,y,width,height,radius,inset=0):
 """Anti-aliased coverage of a rounded rectangle (inset shrinks it, for strokes)."""
 r=max(radius-inset,0.01);cx=min(max(x+0.5,inset+r),width-inset-r);cy=min(max(y+0.5,inset+r),height-inset-r)
 return min(1,max(0,r-((x+0.5-cx)**2+(y+0.5-cy)**2)**0.5+0.5))

def rounded(width,height,radius):
 return png(width,height,lambda x,y:(255,255,255,int(255*coverage(x,y,width,height,radius))))

def glass(size,radius,fill,stroke):
 """Frosted surface: translucent fill with a hairline light edge (iOS materials)."""
 def pixel(x,y):
  outer=coverage(x,y,size,size,radius);inner=coverage(x,y,size,size,radius,2.5)
  edge=max(outer-inner,0);a=fill[3]*inner/255+stroke[3]*edge/255
  if a<=0:return (0,0,0,0)
  mix=lambda i:int((fill[i]*fill[3]*inner/255+stroke[i]*stroke[3]*edge/255)/a)
  return (mix(0),mix(1),mix(2),int(255*min(a,1)))
 return png(size,size,pixel)

def fade(alpha):return png(64,256,lambda x,y:(0,0,0,int(255*alpha(y/255))))

def triangle(size):
 def alpha(x,y):
  inside=sum(1 for i in range(4) for j in range(4) if (lambda px,py:px>=8 and abs(py-size/2)<=(size-8-px)*0.58)(x+(i+.5)/4,y+(j+.5)/4))
  return (255,255,255,int(255*inside/16))
 return png(size,size,alpha)

def ring(size,stroke):
 """Open ring (a quarter missing, like the activity spinner) around the bell while a download runs."""
 import math
 def pixel(x,y):
  outer=coverage(x,y,size,size,size/2);inner=coverage(x,y,size,size,size/2,stroke)
  angle=math.degrees(math.atan2(y+0.5-size/2,x+0.5-size/2))%360
  return (255,255,255,int(255*max(outer-inner,0)*(0 if 230<angle<320 else 1)))
 return png(size,size,pixel)

def shape(size,inside,samples=4):
 """Anti-aliased white glyph: inside(u,v) on a 24x24 design grid (the mockups' SVG viewBox), supersampled."""
 k=24/size;n=samples*samples
 def pixel(x,y):
  hits=sum(1 for i in range(samples) for j in range(samples) if inside((x+(i+.5)/samples)*k,(y+(j+.5)/samples)*k))
  return (255,255,255,int(255*hits/n))
 return png(size,size,pixel)

ROUND=0.9   # corner radius of the gear's teeth on the 24 grid
def gear_outline(teeth=8,tip=10.4,root=8.1,tip_half=10,base_half=17,steps=6):
 """Header gear (owner-approved, round 5, then "cleaned up"): tapered teeth with rounded tips and curved gaps
 around a centred hole, like SF Symbols' gearshape.fill. The polygon is drawn ROUND inside the final edge; the
 rounding (a ROUND-wide margin, round joins) brings it back out. Shared with header-buttons-mockups.html."""
 import math
 pts=[];t_r=tip-ROUND;b_r=root-ROUND
 at=lambda r,deg:(12+r*math.sin(math.radians(deg)),12-r*math.cos(math.radians(deg)))
 step=360/teeth
 for i in range(teeth):
  c=i*step
  pts+=[at(b_r,c-base_half),at(t_r,c-tip_half),at(t_r,c+tip_half),at(b_r,c+base_half)]
  pts+=[at(b_r,c+base_half+(step-2*base_half)*k/steps) for k in range(1,steps)]
 return pts
GEAR=gear_outline();GEAR_HOLE=3.7
def gear_inside(u,v,pts=GEAR):
 import math
 r=math.hypot(u-12,v-12)
 if r<GEAR_HOLE:return False
 # Only the band of the teeth needs the polygon test (tests drew the texture slowly: 268 s for test_portrait).
 if pts is GEAR and r<8.1-ROUND-0.05:return True
 if pts is GEAR and r>10.4+0.05:return False
 inside=False;near=False;n=len(pts)
 for i in range(n):
  (x1,y1),(x2,y2)=pts[i],pts[(i+1)%n]
  if (y1>v)!=(y2>v) and u<x1+(v-y1)*(x2-x1)/(y2-y1):inside=not inside
  dx,dy=x2-x1,y2-y1;t=max(0,min(1,((u-x1)*dx+(v-y1)*dy)/(dx*dx+dy*dy)))
  if math.hypot(u-x1-t*dx,v-y1-t*dy)<=ROUND:near=True
 return inside or near
def gear_svg():
 """The same gear as an SVG symbol body for the mockups (fill plus a round-joined stroke of 2 x ROUND)."""
 d='M'+' L'.join('%.2f %.2f'%pt for pt in GEAR)+'Z'
 h=GEAR_HOLE+ROUND
 return ('<path d="%s M12 %.2f a%.2f %.2f 0 1 0 0.01 0Z" fill="currentColor" fill-rule="evenodd" stroke="currentColor" '
         'stroke-width="%.1f" stroke-linejoin="round"/>')%(d,12-h,h,h,2*ROUND)

def refresh_inside(u,v):
 """arrow.clockwise: an open circle (r 7.7, stroke 2.4) with its arrowhead at the top right."""
 import math
 dx,dy=u-11.9,v-12.4;r=math.hypot(dx,dy);a=math.degrees(math.atan2(dy,dx))%360
 if abs(r-7.7)<=1.2 and not (a>318 or a<6):return True
 def seg(ax,ay,bx,by):
  px,py=bx-ax,by-ay;t=max(0,min(1,((u-ax)*px+(v-ay)*py)/(px*px+py*py)))
  return math.hypot(u-ax-t*px,v-ay-t*py)<=1.2
 return seg(18.6,2.8,18.6,7.4) or seg(18.6,7.4,14.0,7.4)

def arc(size,stroke,degrees):
 """Thin open ring for the busy bell (round 5): degrees of arc, round ends, spun by the skin."""
 import math
 c=size/2;rr=c-stroke/2-1
 def inside(u,v):
  x,y=u*size/24,v*size/24;dx,dy=x-c,y-c;r=math.hypot(dx,dy);a=math.degrees(math.atan2(dy,dx))%360
  if abs(r-rr)<=stroke/2 and a<=degrees:return True
  for e in (0,degrees):
   ex,ey=c+rr*math.cos(math.radians(e)),c+rr*math.sin(math.radians(e))
   if math.hypot(x-ex,y-ey)<=stroke/2:return True
  return False
 return shape(size,inside,3)

_GLYPHS={}
def header_glyphs():
 """The round-5 header textures, drawn once per process (supersampled, so not cheap)."""
 if not _GLYPHS:_GLYPHS.update({'ring_arc.png':arc(132,5,150),'hdr_gear.png':shape(96,gear_inside),'hdr_refresh.png':shape(96,refresh_inside)})
 return _GLYPHS

def textures():
 return {**header_glyphs(),'round.png':rounded(96,96,32),'round_s.png':rounded(64,64,26),'menu_round.png':rounded(160,160,64),**{'menu_%s.png'%k:activity_skin.corner_texture(types_ns(),160,64,t,b) for k,t,b in (('first',True,False),('last',False,True))},'glass_card.png':glass(160,44,(44,44,46,245),(255,255,255,26)),
         'fade_down.png':fade(lambda t:(1-t)**1.6*0.85),'fade_up.png':fade(lambda t:t**1.5),
         'hero_fade.png':fade(lambda t:0 if t<0.3 else ((t-0.3)/0.7)**1.25),
         'poster_mask.png':rounded(POSTER[0],POSTER[1],RADIUS),'card_mask.png':rounded(CARD[0],CARD[1],RADIUS),
         'thumb_mask.png':rounded(400,225,20),'tile_mask.png':rounded(80,80,18),'dot.png':rounded(24,24,12),'knob.png':rounded(48,48,24),'clear48.png':png(4,48,lambda x,y:(0,0,0,0)),
         'white.png':png(4,4,lambda x,y:(255,255,255,255)),'play.png':triangle(64),'airplay.png':player_osd.airplay_png(png),'ring.png':ring(132,7),
         # Capsules per height: 9-slice borders of h/2 keep the ends perfectly round at any width.
         **{'pill_%d.png'%h:rounded(h,h,h/2) for h in CAPSULES},
         **{'glass_%d.png'%h:glass(h,h/2,(30,30,34,232),(255,255,255,50)) for h in CAPSULES},
         'cap_top.png':png(96,48,lambda x,y:(255,255,255,int(255*coverage(x,y,96,96,44)))),
         'cap_bottom.png':png(96,48,lambda x,y:(255,255,255,int(255*coverage(x,y+48,96,96,44)))),
         **{'tile_%d.png'%gid:gradient(120,180,top,bottom) for _,gid,top,bottom in CATEGORIES}}

def gradient(width,height,top,bottom):
 """Diagonal two-colour tile background (Apple TV category tiles)."""
 def pixel(x,y):
  t=min(1,max(0,(y/height)*0.8+(x/width)*0.2))
  return tuple(int(a+(b-a)*t) for a,b in zip(top,bottom))+(255,)
 return png(width,height,pixel)

# --- XML helpers ---------------------------------------------------------------------------------------
def e(text):return escape(str(text),{'"':'&quot;'})
def image(x,y,w,h,texture,color=WHITE,extra='',aspect='',diffuse='',border='',background=False):
 return ('<control type="image"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s'
         '<texture%s%s%s colordiffuse="%s">%s</texture>%s</control>')%(
  x,y,w,h,('<aspectratio%s</aspectratio>'%aspect) if aspect else '',
  ' background="true"' if background else '',' diffuse="%s"'%diffuse if diffuse else '',' border="%s"'%border if border else '',color,texture,extra)
def close_cross():
 # SF-style rounded X, without the large transparent margins of the icon-pack glyph.
 import math
 def distance(x,y,ax,ay,bx,by):
  t=max(0,min(1,((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
  return math.hypot(x-ax-t*(bx-ax),y-ay-t*(by-ay))
 # 128 px with ends at 18..110 (owner: "cleaner larger x"), so it stays sharp at any button size.
 return png(128,128,lambda x,y:(255,255,255,int(255*max(0,min(1,7.5-min(distance(x+.5,y+.5,18,18,110,110),distance(x+.5,y+.5,18,110,110,18)))))))

def close_disc():
 """A smooth 128 px circle for close buttons (dot.png is 24 px and its edge went soft when scaled up)."""
 return png(128,128,lambda x,y:(255,255,255,int(255*coverage(x,y,128,128,64))))

CLOSE_DISC=104;CLOSE_GLYPH=52
def close_button(id,x,y,extra='',navigation='',size=118):
 """The one close (×) button of every sheet (owner, build 173: "cleaner larger x and cleaner circle"): a `size`
 touch area, a smooth CLOSE_DISC circle and a CLOSE_GLYPH cross centred in it; the circle brightens while focused."""
 d=(size-CLOSE_DISC)//2;g=(size-CLOSE_GLYPH)//2
 return ('<control type="group"><left>%s</left><top>%s</top><width>%d</width><height>%d</height>%s'%(x,y,size,size,extra)+
  image(d,d,CLOSE_DISC,CLOSE_DISC,MEDIA+'close_disc.png','2EFFFFFF')+
  image(d,d,CLOSE_DISC,CLOSE_DISC,MEDIA+'close_disc.png','24FFFFFF','<visible>Control.HasFocus(%d)</visible>'%id)+
  image(g,g,CLOSE_GLYPH,CLOSE_GLYPH,MEDIA+'close_cross.png',WHITE)+
  '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />%s</control>'%(id,size,size,navigation)+
  '</control>')


def icon(x,y,size,name,color=WHITE,extra=''):return image(x,y,size,size,name if ('://' in name or name.startswith('$')) else ICONS+name,color,extra,'>keep')
def textbox(x,y,w,h,text,font,color=WHITE):
 """Wrapped text inside a list's item layout (owner, build 229: episode titles and plots ended in "..." after one
 line). A list draws a label on one line whatever wrapmultiline says; a textbox wraps and shows whole lines only."""
 return ('<control type="textbox"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font>'
         '<textcolor>%s</textcolor><label>%s</label><autoscroll>false</autoscroll></control>')%(x,y,w,h,font,color,e(text))
def label(x,y,w,h,text,font,color=WHITE,align='left',extra=''):
 return ('<control type="label"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font>'
         '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><label>%s</label>%s</control>')%(x,y,w,h,font,color,align,e(text),extra)
def surface(x,y,w,h,texture,color=WHITE,border=0,extra=''):return image(x,y,w,h,MEDIA+texture,color,extra,border=border)

def pill_button(id,x,y,w,h,text,actions,style,glyph='',extra='',glyph_x=None,inline=False):
 """Apple-style capsule: 'primary' white with black text, 'glass' frosted. actions: [(condition, action)].
 inline: the glyph and the label are centred together whatever the label's length (owner, build 229: on a show page
 "Play S4 · Immortal Devastators..." ran under the play glyph), the label ending in "..." when it is too long."""
 fill,tex,textcolor=(('FFFFFFFF','pill_%d.png'%h,'FF000000') if style=='primary' else ('FFFFFFFF','glass_%d.png'%h,'FFFFFFFF'))
 clicks=''.join('<onclick%s>%s</onclick>'%(' condition="%s"'%e(c) if c else '',e(a)) for c,a in actions)
 if inline and glyph and text:
  inner=('<control type="button" id="%d"><width>%d</width><height>%d</height><label></label>'
         '<texturefocus border="%d" colordiffuse="%s">%s%s</texturefocus><texturenofocus border="%d" colordiffuse="%s">%s%s</texturenofocus>'
         '%s%s</control>')%(id,w,h,h//2,fill,MEDIA,tex,h//2,fill,MEDIA,tex,clicks,extra)
  row=('<control type="grouplist"><left>40</left><top>0</top><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
       '<align>center</align><itemgap>18</itemgap><usecontrolcoords>true</usecontrolcoords>'%(w-80,h)+
       icon(0,(h-46)//2,46,glyph,textcolor)+
       '<control type="label"><width max="%d">auto</width><height>%d</height><font>p_btn</font><textcolor>%s</textcolor>'
       '<aligny>center</aligny><label>%s</label><scroll>false</scroll></control></control>')%(w-80-64,h,textcolor,e(text))
  visible=''.join(re.findall(r'<visible(?: [^>]*)?>.*?</visible>',extra))
  return '<control type="group"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s%s%s</control>'%(x,y,w,h,visible,inner,row)
 inner=('<control type="button" id="%d"><width>%d</width><height>%d</height><label>%s</label><font>p_btn</font>'
        '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><textoffsetx>%d</textoffsetx>'
        '<texturefocus border="%d" colordiffuse="%s">%s%s</texturefocus><texturenofocus border="%d" colordiffuse="%s">%s%s</texturenofocus>'
        '%s%s</control>')%(id,w,h,e(text),textcolor,textcolor,36 if glyph and text else 0,h//2,fill,MEDIA,tex,h//2,fill,MEDIA,tex,clicks,extra)
 gx=glyph_x if glyph_x is not None else ((w//2-100) if text else (w-46)//2)
 glyphxml=icon(gx,(h-46)//2,46,glyph,textcolor) if glyph else ''
 # Visibility belongs to the complete capsule, including its decorative glyph.
 visible=''.join(re.findall(r'<visible(?: [^>]*)?>.*?</visible>',extra))
 return '<control type="group"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s%s%s</control>'%(x,y,w,h,visible,inner,glyphxml)

def circle_button(id,x,y,size,glyph,action,extra=''):return pill_button(id,x,y,size,size,'',[('',action)],'glass',glyph,extra)

NAV_TOUCH=150;NAV_GLYPH=104
def nav_button(id,x,y,glyph,actions,extra='',visible=''):
 """Back and refresh as the video player has them (owner, build 146: "I love this back button, apply it everywhere"):
 a bold white glyph with no circle, the player's 104 in a 150 touch area (both layouts show 1 unit as the same size
 on the phone). x, y place it where the 108 glass circle was; the glyph dims while focused so a tap shows.
 actions: an action, or [(condition, action)]."""
 actions=[('',actions)] if isinstance(actions,str) else actions
 clicks=''.join('<onclick%s>%s</onclick>'%(' condition="%s"'%e(c) if c else '',e(a)) for c,a in actions)
 c=54  # centre of the old 108 circle, inside the group placed where it was
 dim='<animation effect="fade" start="100" end="65" time="0" condition="Control.HasFocus(%d)">Conditional</animation>'%id
 return ('<control type="group"><left>%s</left><top>%s</top><width>108</width><height>108</height>%s'%(x,y,'<visible>%s</visible>'%visible if visible else '')+
  '<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
  '<texturefocus /><texturenofocus />%s%s</control>'%(id,c-NAV_TOUCH//2,c-NAV_TOUCH//2,NAV_TOUCH,NAV_TOUCH,clicks,extra)+
  icon(c-NAV_GLYPH//2,c-NAV_GLYPH//2,NAV_GLYPH,glyph,WHITE,dim)+'</control>')

NOTICES='RunScript(service.kodi.ios.bootstrap,notifications)'
SETTINGS='ActivateWindow(settings)'
HDR=108;HDR_GAP=24;HDR_GLYPH=46   # header buttons (owner-approved round 5, option A): 40 pt glass circles; button glyphs 46 (APPLE-UI-POLICY §5.5)
def header_button(id,x,y,glyph,action,extra=''):
 """Glass header circle with a centred glyph (bell, gear, refresh); glyph is an icons/ name or a full path."""
 off=(HDR-HDR_GLYPH)//2
 return pill_button(id,x,y,HDR,HDR,'',[('',action)],'glass','',extra)[:-len('</control>')]+icon(off,off,HDR_GLYPH,glyph)+'</control>'
def bell(x,y,extra=''):
 """Real model percentage; needs-you is the only red badge. No looping arc."""
 active='!String.IsEmpty(Window(Home).Property(Notices.Active))'
 pct='Window(Home).Property(Notices.Pct)'
 # Board 6: the ring sits on a grey track (#3A3A3C) while something moves.
 rings=image(-10,-10,128,128,MEDIA+'ring_20.png','FF3A3A3C','<visible>'+active+'</visible>')
 for n in range(21):
  cond=active+' + !Integer.IsGreater(%s,%d)'%(pct,n*5+2)
  if n:cond+=' + Integer.IsGreater(%s,%d)'%(pct,n*5-3)
  rings+=image(-10,-10,128,128,MEDIA+'ring_%02d.png'%n,'$INFO[Window(Home).Property(Notices.Tint)]','<visible>'+cond+'</visible>')
 needs='!String.IsEmpty(Window(Home).Property(Notices.Needs))'
 badge=''
 # Build 194: the blue count only when something runs, there is a count and nothing needs the owner (the old
 # condition read "!!String.IsEmpty(...)" and drew an empty blue badge while slowed).
 count='!String.IsEmpty(Window(Home).Property(Notices.Count))'
 for key,tint,cond in (('Count','FF0A84FF',active+' + '+count+' + String.IsEmpty(Window(Home).Property(Notices.Needs))'),('Needs','FFFF453A',needs)):
  badge+='<control type="group"><left>70</left><top>-6</top><visible>'+cond+'</visible>'+image(0,0,50,50,MEDIA+'dot.png',tint)+label(0,0,50,50,'$INFO[Window(Home).Property(Notices.%s)]'%key,'p_cap',WHITE,'center','<scroll>false</scroll>')+'</control>'
 # The invisible hit target is 118, while the visible bell remains 24 pt.
 return '<control type="group"><left>%d</left><top>%d</top>'%(x,y)+rings+icon(23,23,62,'bell.png')+'<control type="button" id="9207"><left>-5</left><top>-5</top><width>118</width><height>118</height><texturefocus /><texturenofocus /><onclick>'+NOTICES+'</onclick>'+extra+'</control>'+badge+'</control>'


def gear(x,y,extra=''):
 """Gear in place of the profile picture: opens Settings (Accounts is its first row). A dot while add-on updates wait."""
 updates='!String.IsEmpty(System.AddonUpdateCount) + !String.IsEqual(System.AddonUpdateCount,0)'
 return ('<control type="group"><left>%d</left><top>%d</top><width>108</width><height>108</height>'%(x,y)+
  header_button(9206,0,0,MEDIA+'hdr_gear.png',SETTINGS,extra)+
  '<control type="group"><left>78</left><top>-4</top><visible>%s</visible>'%updates+
  image(0,0,36,36,MEDIA+'dot.png','FF000000')+image(4,4,28,28,MEDIA+'dot.png','FFFF453A')+'</control></control>')

REFRESHING='Window(Home).Property(Portrait.Refreshing)'
def refresh_rows_action(tab):return 'RunScript(service.kodi.ios.bootstrap,refresh_rows,tab=%s)'%tab
def refresh_button(x,y,tab,extra=''):
 """Refresh on Home, Movies and TV: every TMDb Helper row and the hero show the next page of their list
 (refresh_rows.py). The arrow spins while the rows load, then a tick for a moment."""
 busy='String.IsEqual(%s,%s)'%(REFRESHING,tab);done='String.IsEqual(%s,done.%s)'%(REFRESHING,tab)
 off=(HDR-HDR_GLYPH)//2
 return ('<control type="group"><left>%d</left><top>%d</top><width>108</width><height>108</height>'%(x,y)+
  pill_button(9208,0,0,HDR,HDR,'',[('!'+busy,refresh_rows_action(tab))],'glass','',extra)+
  '<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><visible>!%s</visible>'%(off,off,HDR_GLYPH,HDR_GLYPH,done)+
  '<animation effect="rotate" end="-360" center="auto" time="900" loop="true" reversible="false" condition="%s">Conditional</animation>'%busy+
  icon(0,0,HDR_GLYPH,MEDIA+'hdr_refresh.png')+'</control>'+
  icon(off,off,HDR_GLYPH,'circle-check.png',GREEN,'<visible>%s</visible>'%done)+'</control>')

def refreshed_toast(tab,title):
 """'New picks on Home': under the header for a moment after a refresh."""
 done='String.IsEqual(%s,done.%s)'%(REFRESHING,tab);w=560;h=96
 return ('<control type="group"><left>%d</left><top>184</top><width>%d</width><height>%d</height><visible>%s</visible>'%((WIDTH-w)//2,w,h,done)+
  '<animation effect="fade" time="180">VisibleChange</animation><animation effect="slide" start="0,-30" end="0,0" time="220" tween="cubic" easing="out">Visible</animation>'+
  surface(0,0,w,h,'glass_96.png',WHITE,48)+icon(40,(h-44)//2,44,'circle-check.png',GREEN)+
  label(100,0,w-130,h,'New picks on %s'%title,'p_foot_b',WHITE,'left')+'</control>')

def header_buttons(y,tab=None,down=''):
 """Right side of a large-title header: [refresh] bell gear, with left/right moves between them."""
 gx=WIDTH-SIDE-HDR;bx=gx-HDR_GAP-HDR;rx=bx-HDR_GAP-HDR
 xml=bell(bx,y,down+'<onright>9206</onright>'+('<onleft>9208</onleft>' if tab else ''))+gear(gx,y,down+'<onleft>9207</onleft>')
 if tab:xml=refresh_button(rx,y,tab,down+'<onright>9207</onright>')+xml
 return xml
def header_width(tab=None):return WIDTH-2*SIDE-(3 if tab else 2)*(HDR+HDR_GAP)

def window(original,body,default,extra_root=''):
 # Pages with the tab bar forget the title of the last category or library page.
 extra_root+='<onload>ClearProperty(Portrait.Title,home)</onload>' if 'id="9200"' in body else ''
 """Keep the landscape window's type/id and its onload helpers (Fuse init, the bootstrap's setup lock)."""
 root=ET.fromstring(original) if original else ET.Element('window')
 attrs=''.join(' %s="%s"'%(k,e(v)) for k,v in root.attrib.items())
 keep=''.join(ET.tostring(node,encoding='unicode') for node in root if node.tag in ('onload','onunload','include','param','zorder','depth','menucontrol','views','animation') and not (node.tag=='include' and 'View_' in (node.text or '')))
 return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window%s><defaultcontrol always="true">%s</defaultcontrol>%s%s%s</window>\n'%(MARKER,attrs,default,keep,extra_root,body)

# Onload actions of Fuse's Home that only served Fuse's own layout, run at every Home open (each switch back from
# Library or Search too): its splash script (a Python run; Fuse's splash is never shown here, ISSUE-065), the
# first-start focus helper and the ratings monitor.
FUSE_HOME_DROP=('skinvariables-splash.json','Action_FirstStart_HomeFocus','Action_RatingsMonitor')

def strip_fuse_onloads(original):
 """Fuse's Home.xml without FUSE_HOME_DROP, and with its Skin.SetString/SetBool onloads skipped when the value is
 already set (each one saved guisettings.xml to disk at every Home open)."""
 if not original:return original
 root=ET.fromstring(original)
 for node in list(root):
  if node.tag!='onload':continue
  text=node.text or ''
  if any(key in text for key in FUSE_HOME_DROP):root.remove(node);continue
  m=re.fullmatch(r'Skin\.SetString\(([^,()]+),([^()]*)\)',text.strip()) or re.fullmatch(r'Skin\.SetBool\(([^,()]+)\)',text.strip())
  # Only plain values: one like "10000|11101" would be read as a condition ("|" is OR).
  if m and not node.get('condition') and re.fullmatch(r'[\w.\-]*',m.groups()[-1]):
   node.set('condition','!String.IsEqual(Skin.String(%s),%s)'%(m.group(1),m.group(2)) if m.re.pattern.startswith('Skin\\.SetString') else '!Skin.HasSetting(%s)'%m.group(1))
 return ET.tostring(root,encoding='unicode')

def backdrop():return image(0,0,WIDTH,HEIGHT,MEDIA+'white.png',BG)

# --- hubs: hero, rows, tab bar --------------------------------------------------------------------------
# Overlap fix (performance pass): the skin's tab bar showed whenever the native glass bar was hidden (a dialog, a page
# change), so the two swapped when switching quickly. The skin bar now exists only on a phone without the native bar
# (a saved skin setting, set or reset at each start from the framework's presence).
NATIVE_TAB_BAR='Portrait.NativeTabBar'
def tabbar(active):
 """One floating frosted capsule, centred: Home, Movies, TV, Library, Search. The current tab sits in a
 darker inner capsule with a blue icon and label (iOS 26 tab bar)."""
 tab_w=188;pad=12;h=150;bar_w=pad*2+tab_w*len(TABS);left=(WIDTH-bar_w)//2;items=[]
 for i,(key,text,glyph) in enumerate(TABS):
  on=key==active;color=ACCENT if on else WHITE;x=pad+i*tab_w
  clicks=''.join('<onclick%s>%s</onclick>'%(' condition="%s"'%e(c) if c else '',e(a)) for c,a in tab_actions(key))
  items.append(('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
   '<texturefocus border="63" colordiffuse="%s">%spill_126.png</texturefocus><texturenofocus border="63" colordiffuse="%s">%spill_126.png</texturenofocus>'
   '<label></label>%s<onup>5000</onup><onleft>%d</onleft><onright>%d</onright></control>'
   )%(9201+i,x,pad,tab_w,h-2*pad,'26FFFFFF' if not on else 'CC000000',MEDIA,'B3000000' if on else '01000000',MEDIA,clicks,
      9201+(i-1)%len(TABS),9201+(i+1)%len(TABS))
   +icon(x+(tab_w-58)//2,24,58,glyph,color)+label(x,84,tab_w,40,text,'p_tab',color,'center'))
 return ('<control type="image"><left>0</left><bottom>0</bottom><width>%d</width><height>330</height><texture>%sfade_up.png</texture></control>'
  '<control type="group" id="9200"><description>%s tab bar</description><left>%d</left><bottom>24</bottom><width>%d</width><height>%d</height>'
  '<visible>!Skin.HasSetting(%s)</visible>'
  '<control type="image"><width>%d</width><height>%d</height><texture border="75">%sglass_150.png</texture></control>%s</control>'
  )%(WIDTH,MEDIA,MARKER,left,bar_w,h,NATIVE_TAB_BAR,bar_w,h,MEDIA,''.join(items))

def usable(widget):
 path=str(widget.get('path') or '')
 if not path or path.startswith(('RunScript(','ActivateWindow(','library://','$','${')):return False
 # Turned off in Settings › Customisation › Tabs & Rows (rows_editor.set_on): keeps its place, not shown.
 if str(widget.get('disabled') or '').lower() in ('true','1'):return False
 # An add-on's root folder is a menu, not a row of titles.
 if path.startswith('plugin://') and '?' not in path:return False
 return True

def load_widgets(profile,lists):
 rows=[]
 for name in lists:
  path=Path(profile)/NODES.format(name)
  try:data=json.loads(path.read_text(encoding='utf-8'))
  except (OSError,ValueError):continue
  rows+=[w for w in data if isinstance(w,dict) and usable(w)]
 return rows

# Poster Badges (Settings › Customisation › Poster Badges): Fuse's own indicator settings, drawn on our posters and
# episode rows. One badge at the top right (the first that applies: watched, Trakt watchlist, Trakt favourite,
# collection, in the library), episodes left at the top left, the progress bar and the movie's version along the bottom.
BADGE={'watched':'!Skin.HasSetting(Indicator.DisableWatched) + [ListItem.IsPlayed | String.IsEqual(ListItem.Overlay,OverlayWatched.png)]',
 'watchlist':'Skin.HasSetting(Indicator.TraktWatchlist) + !String.IsEmpty(ListItem.Property(watchlist_rank))',
 'favourite':'Skin.HasSetting(Indicator.TraktFavourites) + !String.IsEmpty(ListItem.Property(favorites_rank))',
 'collection':'!Skin.HasSetting(Indicator.DisableCollection) + ListItem.IsCollection',
 'library':'!Skin.HasSetting(Indicator.DisableLibrary) + !String.IsEmpty(ListItem.DBID) + !String.IsEmpty(ListItem.Property(Item.Info))',
 'episodes':'!Skin.HasSetting(Indicator.DisableEpisodes) + String.IsEqual(ListItem.DBType,tvshow) + !String.IsEmpty(ListItem.Property(UnWatchedEpisodes))'
            ' + !Integer.IsEqual(ListItem.Property(UnWatchedEpisodes),0) + [!Integer.IsEqual(ListItem.Property(WatchedEpisodes),0) | Skin.HasSetting(Indicator.EnableUnwatchedCount)]',
 'progress':'!Skin.HasSetting(Indicator.DisableProgress) + !ListItem.IsCollection + ListItem.IsResumable',
 'version':'Skin.HasSetting(Indicator.MovieVersionBanner) + String.IsEqual(ListItem.DBType,movie) + ListItem.HasVideoVersions + !String.IsEmpty(ListItem.VideoVersionName)',
 'episode_type':'Skin.HasSetting(Indicator.EpisodeTypeBanner) + !String.IsEmpty(ListItem.Property(episode_type))'}
CORNER=(('watched','circle-check.png',GREEN),('watchlist','bookmark.png','FFED1C24'),('favourite','heart.png','FFED1C24'),
        ('collection','layer-group.png',WHITE),('library','hard-drive.png',WHITE))
EPISODE_TYPES=(('series_premiere','Series Premiere'),('season_premiere','Season Premiere'),('mid_season_premiere','Mid-season Premiere'),
               ('series_finale','Series Finale'),('season_finale','Season Finale'),('mid_season_finale','Mid-season Finale'))
def progress_bar(x,y,w,info='ListItem.PercentPlayed',visible=''):
 return ('<control type="progress"><left>%d</left><top>%d</top><width>%d</width><height>10</height><info>%s</info>%s'
  '<texturebg border="5" colordiffuse="59FFFFFF">%spill_96.png</texturebg><midtexture border="5" colordiffuse="FFFFFFFF">%spill_96.png</midtexture>'
  '<lefttexture /><righttexture /><overlaytexture /></control>')%(x,y,w,info,'<visible>%s</visible>'%visible if visible else '',MEDIA,MEDIA)
def poster_badges(w,h):
 xml='';shown=[]
 for key,glyph,color in CORNER:
  cond=' + '.join(['[%s]'%BADGE[key]]+['![%s]'%BADGE[k] for k in shown]);shown.append(key)
  xml+=('<control type="group"><left>%d</left><top>14</top><visible>%s</visible>'%(w-70,cond)+
        image(0,0,56,56,MEDIA+'avatar_s.png','B3000000')+icon(10,10,36,glyph,color)+'</control>')
 xml+=('<control type="group"><left>14</left><top>14</top><visible>%s</visible>'%BADGE['episodes']+
       image(0,0,72,56,MEDIA+'pill_56.png','E60A84FF',border=28)+label(0,0,72,56,'$INFO[ListItem.Property(UnWatchedEpisodes)]','p_foot_b',WHITE,'center')+'</control>')
 xml+=image(0,h-110,w,110,MEDIA+'fade_up.png','B3FFFFFF',diffuse=MEDIA+'poster_mask.png',extra='<visible>[%s] | [%s]</visible>'%(BADGE['progress'],BADGE['version']))
 xml+=label(20,h-84,w-40,44,'$INFO[ListItem.VideoVersionName]','p_cap',WHITE,'left','<visible>%s</visible>'%BADGE['version'])
 xml+=progress_bar(20,h-30,w-40,visible=BADGE['progress'])
 return xml
def episode_badges(x,y,w,h):
 types=''.join(label(20,14,w-40,44,'[B]%s[/B]'%text,'p_cap',WHITE,'left','<visible>String.IsEqual(ListItem.Property(episode_type),%s)</visible>'%key) for key,text in EPISODE_TYPES)
 return ('<control type="group"><left>%d</left><top>%d</top>'%(x,y)+
  '<control type="group"><visible>%s</visible>%s</control>'%(BADGE['episode_type'],types)+
  '<control type="group"><left>%d</left><top>14</top><visible>%s</visible>'%(w-70,BADGE['watched'])+image(0,0,56,56,MEDIA+'avatar_s.png','B3000000')+icon(10,10,36,'circle-check.png',GREEN)+'</control>'+
  progress_bar(20,h-30,w-40,visible='!Skin.HasSetting(Indicator.DisableProgress) + ListItem.IsResumable')+'</control>')

def poster_item(focused):
 w,h=POSTER
 zoom='<animation effect="zoom" start="100" end="104" time="160" center="auto" tween="cubic" easing="out">Focus</animation>' if focused else ''
 return ('<control type="group"><left>%d</left><top>14</top>%s'%(SIDE,zoom)+
  image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  label(20,h-170,w-40,150,'$INFO[ListItem.Label]','p_foot_b',WHITE,'left','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(poster))</visible>')+
  image(0,0,w,h,'$INFO[ListItem.Art(poster)]',WHITE,'','>scale',MEDIA+'poster_mask.png',background=True)+poster_badges(w,h)+'</control>')

CARD_NO_ART='String.IsEmpty(ListItem.Art(landscape)) + String.IsEmpty(ListItem.Art(fanart)) + String.IsEmpty(ListItem.Art(thumb))'

def card_item(focused,progress=False):
 """Apple TV app 'Up Next' card: 16:9 art in a rounded tile, then a small grey line and the title.
 Continue Watching cards add the playback progress over the art."""
 w,h=CARD;text_h=150
 zoom='<animation effect="zoom" start="100" end="103" time="160" center="auto" tween="cubic" easing="out">Focus</animation>' if focused else ''
 bar=('<control type="progress"><left>26</left><top>%d</top><width>%d</width><height>10</height><info>ListItem.PercentPlayed</info>'
      '<texturebg border="5" colordiffuse="59FFFFFF">%spill_96.png</texturebg><midtexture border="5" colordiffuse="FFFFFFFF">%spill_96.png</midtexture>'
      '<lefttexture /><righttexture /><overlaytexture /></control>')%(h-34,w-52,MEDIA,MEDIA) if progress else ''
 sub=('$INFO[ListItem.Property(subtitle)]' if progress else '$INFO[ListItem.Genre]$INFO[ListItem.Year,  ·  ]')
 return ('<control type="group"><left>%d</left><top>14</top>%s'%(SIDE,zoom)+
  surface(0,0,w,h+text_h,'round_s.png',SURFACE,26)+
  # No landscape, fanart or thumb (new titles, people): the title on the dark tile instead of a blank card.
  label(40,30,w-80,h-60,'$INFO[ListItem.Label]','p_h2',WHITE,'center','<aligny>center</aligny><wrapmultiline>true</wrapmultiline><visible>%s</visible>'%CARD_NO_ART)+
  image(0,0,w,h,'$VAR[Portrait_Card_Art]',WHITE,'','>scale',MEDIA+'card_mask.png',background=True)+
  (image(0,h-120,w,120,MEDIA+'fade_up.png','B3FFFFFF',diffuse=MEDIA+'card_mask.png') if progress else '')+bar+
  label(26,h+18,w-52,44,sub,'p_cap',GREY,'left','<font>p_foot_b</font>')+
  label(26,h+62,w-52,60,'$INFO[ListItem.Label]','p_h3')+'</control>')

# Listing cache (build-137): a TMDb Helper row or hero shows its last result, kept by the bootstrap service, through
# the watch plugin's cached route (resources/lib/ios_cache.py there), which only reads a file. Which one a row uses
# is a skin variable decided by saved skin settings the moment Home opens: the cached route while the row's flag is
# on (set by the service only after the copy was written and read back), otherwise the real TMDb Helper path. The
# names, keys and route must match ios_cache.py (scripts/test_listing_cache.py checks them).
CACHE_ROUTE='plugin://plugin.video.kodi.ios.watch/?action=cached&key='
CACHE_FLAG='PortraitCache.'
CACHEABLE=(TMDB,)
WATCH_ON='System.AddonIsEnabled(plugin.video.kodi.ios.watch)'
def cache_key(path):return 'r'+hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:15]
def spotlight_path(spotlight):return 'Skin.String(HomeSwitcher.%s.Spotlight.Path)'%spotlight

# Refresh on Home, Movies and TV (round 5): each tab has a page number, Skin.String(Portrait.Page.<tab>), empty for
# the first page. Its TMDb Helper rows and hero load that page (TMDb Helper's own `page` parameter); Continue Watching,
# Up Next and library rows never change. refresh_rows.py moves it on; copies keep their key without the page.
PAGE_STRING='Portrait.Page.%s'
PAGES=5   # then back to the first page
PAGED=re.compile(r'[&?]page=\d+$')
def page_of(tab):return 'Skin.String(%s)'%(PAGE_STRING%tab)
def unpaged(path):return PAGED.sub('',str(path or ''))
def paged(path,page):
 """path showing that page of its list (TMDb Helper only; page 1 or none: the plain path)."""
 path=unpaged(path)
 if not str(page or '').isdigit() or int(page)<=1 or not path.startswith(CACHEABLE):return path
 return '%s%spage=%d'%(path,'&' if '?' in path else '?',int(page))
def next_page(current):
 """The page the refresh button shows next: 2, 3 ... PAGES, then the first again."""
 n=int(current) if str(current or '').isdigit() else 1
 return 1 if n>=PAGES else n+1

def cached_content(name,path,variables,spotlight=None,tab=None):
 """Container content for a hub row (path) or hero (spotlight id): a variable in Includes.xml choosing the cached
 route when its flag is on, else the live path (at the tab's page, when the refresh button moved it on). Other rows
 (Continue Watching, library) keep their path as is."""
 if variables is None or (spotlight is None and not str(path).startswith(CACHEABLE)):return e(path)
 if spotlight is None:
  key=cache_key(path);on='Skin.HasSetting(%s%s)'%(CACHE_FLAG,key)
  tmdb=''
 else:
  # The flag holds the path the copy was made from: a spotlight changed in the skin settings goes live at once.
  key='hero.'+str(spotlight).lower();flag='Skin.String(%s%s)'%(CACHE_FLAG,key)
  on='!String.IsEmpty(%s) + String.IsEqual(%s,%s)'%(flag,flag,spotlight_path(spotlight))
  tmdb=' + String.StartsWith(%s,%s)'%(spotlight_path(spotlight),CACHEABLE[0])
 page=''
 if tab:
  # Another page while its copy is being made: the live list at that page.
  page='<value condition="%s">%s</value>'%(e('!String.IsEmpty(%s)%s'%(page_of(tab),tmdb)),e('%s&page=$INFO[%s]'%(path,page_of(tab))))
 variables[name]='<variable name="%s"><value condition="%s + %s">%s</value>%s<value>%s</value></variable>'%(
  name,e(on),WATCH_ON,e(CACHE_ROUTE+key),page,e(path))
 return '$VAR[%s]'%name

def row(index,widget,last,tab='home',variables=None):
 id=5001+index;title=str(widget.get('label') or '')
 style=widget.get('style') or ('poster' if str(widget.get('widget_style') or '').lower()=='poster' else 'card')
 w,h=(POSTER[0],POSTER[1]+40) if style=='poster' else (CARD[0],CARD[1]+180)
 # Hidden while empty; allowhiddenfocus keeps Kodi loading the row's content while it is hidden.
 visible='Integer.IsGreater(Container(%d).NumItems,0) | Container(%d).IsUpdating'%(id,id)
 item=poster_item if style=='poster' else (lambda f:card_item(f,style=='continue'))
 return (label(SIDE,0,WIDTH-2*SIDE,128,'%s  [COLOR %s]›[/COLOR]'%(title,GREY),'p_h2',WHITE,'left','<aligny>bottom</aligny><visible>%s</visible>'%visible).replace('<control type="label">','<control type="label" id="%d">'%(id+500),1)+
  # Board 13: while the row is still loading and has nothing yet, its tiles are drawn as placeholders (SURFACE, the
  # item's own size and corners), so the first frame already shows the page's structure. A 1-unit group: the grouplist
  # moves the list down by 1 while it shows.
  ('<control type="group"><height>1</height><visible>Container(%d).IsUpdating + Integer.IsEqual(Container(%d).NumItems,0)</visible>'%(id,id)+
   ''.join(image(SIDE+k*(w+GAP),14,w,POSTER[1] if style=='poster' else CARD[1],MEDIA+'white.png',SURFACE,
                 diffuse=MEDIA+('poster_mask.png' if style=='poster' else 'card_mask.png')) for k in range(4 if style=='poster' else 2))+'</control>')+
  ('<control type="list" id="%d"><left>0</left><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
   '%s<scrolltime tween="cubic" easing="out">320</scrolltime><preloaditems>2</preloaditems><visible allowhiddenfocus="true">%s</visible>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
   '<content target="%s">%s</content></control>'
   )%(id,WIDTH,h,'<ondown>9201</ondown>' if last else '',visible,w+GAP,h,item(False),w+GAP,h,item(True),
      e(widget.get('target') or 'videos'),cached_content('Portrait_Cache_Row_%s_%d'%(tab,index),widget['path'],variables,tab=tab)))

def hero(spotlight,title,tab='home',variables=None):
 """Full-bleed hero: the hub's spotlight titles (swipe sideways), logo, genre line, Play and Info, page dots."""
 info='Container(4000).ListItem'
 art=image(0,0,WIDTH,HERO,'$VAR[Portrait_Hero_Art]',WHITE,'','>scale',background=True)
 meta='$INFO[%s.Genre]$INFO[%s.Year,  ·  ]$INFO[%s.MPAA,  ·  ]'%(info,info,info)
 is_show='String.IsEqual(%s.DBType,tvshow)'%info
 # A show opens its page (seasons and episodes); a movie goes straight to "How would you like to watch?".
 # Roadmap 2.10 (owner screenshot: the watch question named another title than the one shown): a tap that lands while
 # the spotlight is still sliding to the next title is ignored, so Play and Info act on the title on screen.
 still='!Container(4000).Scrolling'
 play=[(still+' + '+is_show,'ActivateWindow(Videos,$ESCINFO[%s.FolderPath],return)'%info),(still+' + !'+is_show,'PlayMedia($ESCINFO[%s.FileNameAndPath])'%info)]
 dots=''.join('<control type="group"><width>34</width><height>20</height><visible>Integer.IsGreaterOrEqual(Container(4000).NumItems,%d)</visible>%s%s</control>'
  %(i,image(7,0,20,20,MEDIA+'dot.png','59FFFFFF'),image(7,0,20,20,MEDIA+'dot.png',WHITE,'<visible>Integer.IsEqual(Container(4000).CurrentItem,%d)</visible>'%i)) for i in range(1,9))
 btn_w=440
 return ('<control type="group" id="4100"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
  '<control type="list" id="4000"><left>0</left><top>0</top><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
  '<scrolltime tween="cubic" easing="out">450</scrolltime><ondown>4001</ondown><visible allowhiddenfocus="true">true</visible>'
  '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
  '<content target="videos" limit="8">%s</content></control>'
  '%s%s'                                        # fades
  '%s%s'                                        # large title + profile
  '<control type="image"><left>120</left><top>%d</top><width>%d</width><height>250</height><aspectratio aligny="bottom">keep</aspectratio><texture>$INFO[%s.Art(clearlogo)]</texture></control>'
  '%s%s%s'
  '<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>20</height><orientation>horizontal</orientation><align>center</align><itemgap>0</itemgap>%s</control>'
  '</control>'
  )%(WIDTH,HERO,WIDTH,HERO,WIDTH,HERO,art,WIDTH,HERO,art,
     cached_content('Portrait_Cache_Hero_%s'%tab,'$INFO[%s]'%spotlight_path(spotlight),variables,spotlight,tab),
     image(0,0,WIDTH,HERO,MEDIA+'hero_fade.png'),image(0,0,WIDTH,420,MEDIA+'fade_down.png'),
     label(SIDE,40,header_width(tab),120,title,'p_large'),
     header_buttons(46,tab,'<ondown>4000</ondown>')+refreshed_toast(tab,title),
     HERO-560,WIDTH-240,info,
     label(SIDE,HERO-560,WIDTH-2*SIDE,250,'$INFO[%s.Label]'%info,'p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(%s.Art(clearlogo))</visible>'%info),
     label(SIDE,HERO-296,WIDTH-2*SIDE,56,meta,'p_foot',GREY,'center'),
     # Play and Info only once there is a title to play; until then a soft placeholder where the art will be.
     '<control type="group"><visible>Integer.IsGreater(Container(4000).NumItems,0)</visible>'+
     pill_button(4001,WIDTH//2-btn_w-12,HERO-214,btn_w,124,'Play',play,'primary',MEDIA+'play.png','<onup>4000</onup><onright>4002</onright><ondown>5001</ondown>')+
     pill_button(4002,WIDTH//2+12,HERO-214,btn_w,124,'Info',[(still,'SetFocus(4000)'),(still,'Action(Info)')],'glass','circle-info.png','<onup>4000</onup><onleft>4001</onleft><ondown>5001</ondown>')+'</control>'+
     # Board 13 (first frame): until the spotlight has a title, a soft dark hero with placeholders where the title
     # and its genre line will be; no spinner, no words.
     '<control type="group"><visible>Integer.IsEqual(Container(4000).NumItems,0)</visible>'
     '<animation effect="fade" start="100" end="55" time="900" pulse="true" condition="Container(4000).IsUpdating">Conditional</animation>'+
     image(0,0,WIDTH,HERO,MEDIA+'white.png','FF15161A')+image(0,0,WIDTH,HERO,MEDIA+'hero_fade.png')+
     surface((WIDTH-618)//2,HERO-420,618,81,'round.png',SURFACE,22)+
     surface((WIDTH-403)//2,HERO-300,403,43,'round.png',SURFACE,16)+'</control>',
     HERO-62,WIDTH,dots)

def in_progress(widget):
 text=(str(widget.get('path') or '')+' '+str(widget.get('label') or '')).lower()
 return 'inprogress' in text or 'in progress' in text or 'continue watching' in text

SHIFTED=re.compile(r'(?<=id=")(\d+)(?=")|(?<=>)(\d+)(?=<)|(?<=\()(\d+)(?=[,)])')
def shift(xml,offset):
 """Move one hub's control ids (4000s hero, 5000s rows, 9200s tab bar, 9206-9208 header) out of the others' way."""
 def move(m):
  n=int(m.group(0))
  return str(n+offset) if offset and (4000<=n<4200 or 5000<=n<6000 or 9200<=n<9210) else m.group(0)
 return SHIFTED.sub(move,xml)

def hub_body(title,widgets,tab,spotlight,resume='all',variables=None):
 # Continue Watching leads (movies and episodes the owner started); the old in-progress rows would repeat it.
 widgets=[{'label':'Continue Watching','path':CONTINUE+resume,'target':'videos','style':'continue'}]+[w for w in widgets if not in_progress(w)]
 rows=''.join(row(i,w,i==len(widgets)-1,tab,variables) for i,w in enumerate(widgets))
 body=('<control type="grouplist" id="5000"><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><scrolltime tween="cubic" easing="out">380</scrolltime><usecontrolcoords>true</usecontrolcoords>%s%s'
  '<control type="image"><height>%d</height><texture /></control></control>'
  '%s%s'
  )%(WIDTH,PAGE_H,hero(spotlight,title,tab,variables),rows,TAB_CLEAR,image(0,0,WIDTH,90,MEDIA+'fade_down.png'),tabbar(tab))
 return shift(body,HUB_OFFSET[tab])

def hub_window(original,title,widgets,tab,spotlight,resume='all'):
 """One hub alone in its window (kept for tests and tools; the phone uses hubs_window)."""
 return window(original,'<controls>%s%s</controls>'%(backdrop(),hub_body(title,widgets,tab,spotlight,resume)),'4000')

def hubs_window(original,hubs,variables=None):
 """Home, Movies and TV in one window: a group per hub, shown by Portrait.Tab. Every row of all three hubs
 loads when Home opens (the preloader) and keeps its titles while another hub shows, so switching needs no reload."""
 groups=''.join('<control type="group" id="%d"><visible>%s</visible>%s</control>'%(3900+HUB_OFFSET[tab],tab_visible(tab),hub_body(*args,variables=variables))
                for tab,args in hubs)
 focus=''.join('<onload condition="%s">SetFocus(%d)</onload>'%(e(tab_visible(tab)),4000+HUB_OFFSET[tab]) for tab,_ in hubs if HUB_OFFSET[tab])
 return window(strip_fuse_onloads(original),'<controls>%s%s</controls>'%(backdrop(),groups),'4000',focus)

def forward_window(original,tab):
 """Movies/TV windows (opened by Fuse menus or older shortcuts) show that hub in Home instead."""
 return window(original,'<controls>%s</controls>'%backdrop(),'9999',
               '<onload>SetProperty(%s,%s,home)</onload><onload>ReplaceWindow(Home)</onload>'%(TAB_PROPERTY,tab))

def page_header(title):
 """Large title on black with the bell and gear (Settings), as on the Apple TV app's Library and Search."""
 return label(SIDE,40,header_width(),120,title,'p_large')+header_buttons(46)

def clicks(actions):return ''.join('<onclick>%s</onclick>'%e(a) for a in actions.split('\x00'))

def library_window(original):
 """Library: Movies and TV Shows (downloaded media in Kodi's library), then a poster grid."""
 row_h=150
 items=''.join('<item><label>%s</label><icon>%s</icon>%s</item>'%(e(t),ICONS+i,clicks(a)) for t,i,a in LIBRARY)
 item=lambda focused:((image(0,0,WIDTH,row_h,MEDIA+'white.png','14FFFFFF') if focused else '')+
  icon(SIDE-14,(row_h-112)//2,112,'$INFO[ListItem.Icon]',ACCENT)+label(SIDE+120,0,WIDTH-2*SIDE-200,row_h,'$INFO[ListItem.Label]','p_h3','FFFFFFFF','left','<font>p_body</font>')+
  label(WIDTH-SIDE-60,0,50,row_h,'›','p_h2',DIM,'right')+image(SIDE+120,row_h-2,WIDTH-SIDE-120,2,MEDIA+'white.png',SEP))
 lst=('<control type="list" id="5000"><left>0</left><top>200</top><width>%d</width><height>%d</height><ondown>9204</ondown>'
      '<itemlayout height="%d">%s</itemlayout><focusedlayout height="%d">%s</focusedlayout><content>%s</content></control>'
      )%(WIDTH,row_h*len(LIBRARY),row_h,item(False),row_h,item(True),items)
 body='<controls>%s%s%s%s</controls>'%(backdrop(),page_header('Library'),lst,tabbar('library'))
 return window(original,body,'5000')

# r3 glass bar framework: the field is a native iOS search field in a dark band at the top (searchbar.py), and the results
# of what is typed show in a poster grid under it; Portrait.SearchBar marks a phone that has it.
SEARCH_NATIVE='String.IsEqual(Window(Home).Property(Portrait.SearchBar),1)'
SEARCH_PATH='Window(Home).Property(Portrait.Search.Path)'
SEARCH_BAND=161  # the native band ends 60 pt below the top of the safe area: 60 x 2.687 px per pt

GENRE_PHOTO='Portrait.GenrePhoto.'
GENRE_PHOTOS='portrait-genre-photos.json'
WEEK=7*86400
# TMDb's movie and TV genre taxonomies differ. Reality and Kids have no movie genre counterpart.
MOVIE_GENRES={18:'18',35:'35',80:'80',10765:'878|14',10759:'28|12',16:'16',9648:'9648',99:'99',10751:'10751',10768:'10752'}
MOVIE_FILTER='String.IsEqual(Window(Home).Property(Portrait.Search.Type),movie)'

def category_path(gid,kind):
 from urllib.parse import quote
 genre=MOVIE_GENRES.get(gid) if kind=='movie' else str(gid)
 if genre is None:return None
 return '%s?info=discover&tmdb_type=%s&with_id=True&with_genres=%s&sort_by=popularity.desc'%(TMDB,kind,quote(genre,safe=''))

def category_clicks(name,gid):
 actions=''
 for kind,condition in (('movie',MOVIE_FILTER),('tv','!'+MOVIE_FILTER)):
  path=category_path(gid,kind)
  if path:
   title='War' if kind=='movie' and gid==10768 else name
   actions+=''.join('<onclick condition="%s">%s</onclick>'%(e(condition),e(action)) for action in titled_page(title,path).split('\x00'))
 return actions

def genre_photo_path(gid):
 return '%s?info=discover&tmdb_type=tv&with_id=True&with_genres=%d&sort_by=popularity.desc'%(TMDB,gid)

def pick_photo(files,used=()):
 """The backdrop (fanart, else landscape) of the first listed title not already used by another tile."""
 for f in files or []:
  art=f.get('art') or {}
  url=art.get('fanart') or art.get('landscape') or art.get('tvshow.fanart') or ''
  if url and url not in used:return url
 return ''

def genre_photos(rpc,set_property,read,write,now,busy=lambda:False,wait=lambda seconds:False):
 """One backdrop per Search category (TMDb Helper's most popular show of the genre), kept for a week so Search
 does not run TMDb Helper twelve times on every visit. Sets Window(Home).Property(Portrait.GenrePhoto.<genre id>)."""
 try:cache=json.loads(read() or '{}')
 except ValueError:cache={}
 fresh=now()-cache.get('time',0)<WEEK and all(str(gid) in cache.get('photos',{}) for _,gid,_,_ in CATEGORIES)
 photos=dict(cache.get('photos',{}))
 # Existing artwork is usable immediately, even when stale. Cosmetic refresh must yield to actual use.
 for gid,url in photos.items():
  if url:set_property(GENRE_PHOTO+gid,url)
 if not fresh:
  used=set()
  for _,gid,_,_ in CATEGORIES:
   while busy():
    if wait(2):return photos
   try:files=(rpc('Files.GetDirectory',{'directory':genre_photo_path(gid),'media':'video','properties':['art'],'limits':{'start':0,'end':6}}) or {}).get('files')
   except Exception:files=None
   photos[str(gid)]=pick_photo(files,used);used.add(photos[str(gid)])
   if wait(0.2):return photos
  if any(photos.values()):write(json.dumps({'time':now(),'photos':photos}))
 for gid,url in photos.items():
  if url:set_property(GENRE_PHOTO+gid,url)
 return photos

def genre_photos_tick(visible,start):
 """Loads the genre photos (in the background) the first time Search opens."""
 state={'done':False}
 def tick():
  if not state['done'] and visible('Window.IsActive(1105)'):state['done']=True;start()
 return tick

def search_window(original):
 """Search: a search field at the top, the results of what is typed in a poster grid under it while typing, the
 category tiles while the field is empty (Apple TV app)."""
 tile_w,tile_h,gap=308,462,24;cols=3;left=(WIDTH-cols*tile_w-(cols-1)*gap)//2
 old=('<control type="group"><visible>!%s</visible>'%SEARCH_NATIVE+page_header('Search')+
  ('<control type="group"><left>%d</left><top>186</top><width>%d</width><height>124</height>'
  '<control type="button" id="5101"><width>%d</width><height>124</height><label></label>'
  '<texturefocus border="62" colordiffuse="FF3A3A3C">%spill_124.png</texturefocus><texturenofocus border="62" colordiffuse="%s">%spill_124.png</texturenofocus>'
  '<onclick>%s</onclick><ondown>5100</ondown></control>%s%s</control>'
  )%(SIDE,WIDTH-2*SIDE,WIDTH-2*SIDE,MEDIA,SURFACE,MEDIA,e(SEARCH_ACTION),icon(40,38,48,'magnifying-glass.png',GREY),label(110,0,WIDTH-2*SIDE-150,124,'Shows, Movies, and More','p_body',GREY))+
  '</control>')
 items=''.join('<item><label>%s</label><property name="tile">%stile_%d.png</property><property name="photo">$INFO[Window(Home).Property(%s%d)]</property><property name="tint">F2%02X%02X%02X</property>%s</item>'
  %(e(name),MEDIA,gid,GENRE_PHOTO,gid,*bottom,
    ('<visible>!%s</visible>'%e(MOVIE_FILTER) if gid not in MOVIE_GENRES else '')+category_clicks(name,gid)) for name,gid,_,bottom in CATEGORIES)
 zoom=lambda focused:'<animation effect="zoom" start="100" end="104" time="160" center="auto">Focus</animation>' if focused else ''
 tile=lambda focused:('<control type="group"><left>0</left><top>0</top>%s'%zoom(focused)+
  image(0,0,tile_w,tile_h,'$INFO[ListItem.Property(tile)]',WHITE,diffuse=MEDIA+'poster_mask.png')+
  # Owner (build-133): a photo per genre like the Apple TV app (genre_photos), the genre colour as a tint over it.
  image(0,0,tile_w,tile_h,'$INFO[ListItem.Property(photo)]',WHITE,aspect='>scale',diffuse=MEDIA+'poster_mask.png',background=True)+
  # Style C (owner): the photo as it is, fading into the genre colour behind the label.
  image(0,tile_h-300,tile_w,300,MEDIA+'fade_up.png','$INFO[ListItem.Property(tint)]',diffuse=MEDIA+'poster_mask.png',extra='<visible>!String.IsEmpty(ListItem.Property(photo))</visible>')+
  image(0,tile_h-200,tile_w,200,MEDIA+'fade_up.png','80FFFFFF',diffuse=MEDIA+'poster_mask.png',extra='<visible>String.IsEmpty(ListItem.Property(photo))</visible>')+
  '<control type="textbox"><left>26</left><top>%d</top><width>%d</width><height>120</height><font>p_tile</font><textcolor>FFFFFFFF</textcolor><label>$INFO[ListItem.Label]</label></control>'%(tile_h-150,tile_w-40)+'</control>')
 # With the native field the page has no header: the categories move up under the band.
 up='<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(SEARCH_BAND+160-350,SEARCH_NATIVE)
 panel=('<control type="panel" id="5100"><left>%d</left><top>350</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
  '<onup>5101</onup><scrolltime tween="cubic" easing="out">300</scrolltime><visible>String.IsEmpty(%s)</visible>%s'
  '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout><content>%s</content></control>'
  )%(left,WIDTH-left,SEARCH_PATH,up,tile_w+gap,tile_h+gap,tile(False),tile_w+gap,tile_h+gap,tile(True),items)
 # Results as a list (owner-approved board 12): a 140 x 210 poster, the title, and year and kind on a grey line. The poster
 # card shows the title when a result has no poster (people, some new titles). Rows are 78 pt (210 units); no chevron,
 # a row plays or opens like Home's. (The bold matching letters wait for ISSUE-160's device check.)
 row_h=210;row_w=WIDTH-2*SIDE;tx=SIDE+0
 kindmap=(('movie','Movie'),('tv','TV Show'),('season','Season'),('episode','Episode'))
 sub=lambda focused:(label(180,112,row_w-200,50,'$INFO[ListItem.Year]','p_foot',GREY,'left','<scroll>false</scroll><visible>!%s</visible>'%'|'.join('String.IsEqual(ListItem.Property(tmdb_type),%s)'%k for k,_ in kindmap))+
  ''.join(label(180,112,row_w-200,50,'$INFO[ListItem.Year,,  ·  ]%s'%t,'p_foot',GREY,'left','<scroll>false</scroll><visible>String.IsEqual(ListItem.Property(tmdb_type),%s)</visible>'%k) for k,t in kindmap))
 # Board 12: on All the list comes in sections (ios_search.py); a heading is an item of its own (property header),
 # drawn as a small grey caption at the bottom of its row.
 head='!String.IsEmpty(ListItem.Property(header))'
 result=lambda focused:('<control type="group"><visible>!%s</visible>'%head+
  (image(0,0,row_w,row_h-6,MEDIA+'white.png','1FFFFFFF') if focused else '')+
  image(0,10,140,190,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  image(0,10,140,190,'$INFO[ListItem.Art(poster)]',WHITE,aspect='>scale',diffuse=MEDIA+'poster_mask.png',background=True)+
  label(180,50,row_w-200,60,'$INFO[ListItem.Label]','p_h3',WHITE,'left','<scroll>false</scroll>')+sub(focused)+
  image(180,row_h-2,row_w-180,2,MEDIA+'white.png',SEP)+'</control>'+
  label(0,row_h-80,row_w,60,'$INFO[ListItem.Label]','p_foot_b',GREY,'left','<scroll>false</scroll><visible>%s</visible>'%head))
 # Filter (owner): All / Movies / Shows, as Window(Home).Property(Portrait.Search.Type) ('' / movie / tv) for searchbar.py.
 kind='Window(Home).Property(Portrait.Search.Type)'
 pills=''
 x=SIDE
 for n,(text,value,pw) in enumerate((('All','',170),('Movies','movie',230),('TV Shows','tv',290))):   # each pill fits its word
  on=('String.IsEmpty(%s)'%kind) if not value else 'String.IsEqual(%s,%s)'%(kind,value)
  act=('ClearProperty(Portrait.Search.Type,home)' if not value else 'SetProperty(Portrait.Search.Type,%s,home)'%value)
  pills+=('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>96</height><label>%s</label>'
   '<font>p_sub</font><align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor>'
   '<texturefocus border="48" colordiffuse="FF3A3A3C">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="FF1C1C1E">%spill_96.png</texturenofocus>'
   '<onclick>%s</onclick></control>'
   '<control type="image"><left>%d</left><top>0</top><width>%d</width><height>96</height><texture border="48" colordiffuse="33FFFFFF">%spill_96.png</texture><visible>%s</visible></control>'
   )%(5210+n,x,pw,text,MEDIA,MEDIA,e(act),x,pw,MEDIA,e(on))
  x+=pw+20
 top=SEARCH_BAND+30
 filters='<control type="group"><top>%d</top><visible>%s</visible>%s</control>'%(top,SEARCH_NATIVE,pills)
 top+=120
 results=(filters+'<control type="group"><visible>!String.IsEmpty(%s)</visible>'%SEARCH_PATH+
  label(SIDE,top,WIDTH-2*SIDE,70,'Results','p_h3',GREY,'left','<visible>!String.IsEmpty(%s)</visible>'%kind)+   # All: the sections' headings instead
  ('<control type="list" id="5200"><left>%d</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
   '<scrolltime tween="cubic" easing="out">300</scrolltime><preloaditems>2</preloaditems>'
   # All: no "Results" line, and the first heading's row starts high, so the list moves up (board 12).
   '<animation effect="slide" end="0,-200" time="0" condition="String.IsEmpty(Window(Home).Property(Portrait.Search.Type))">Conditional</animation>'
   '<itemlayout height="%d">%s</itemlayout><focusedlayout height="%d">%s</focusedlayout>'
   '<content target="videos">$INFO[%s]</content></control>'
   )%(SIDE,top+90,WIDTH-2*SIDE,row_h,result(False),row_h,result(True),SEARCH_PATH)+
  # Board 12: the search glyph above "No results".
  icon((WIDTH-104)//2,top+110,104,'magnifying-glass.png',GREY,'<visible>Integer.IsEqual(Container(5200).NumItems,0) + !Container(5200).IsUpdating</visible>')+
  label(SIDE,top+250,WIDTH-2*SIDE,80,'$INFO[Window(Home).Property(Portrait.Search.Query),No results for “,”]','p_h3',WHITE,'center','<scroll>false</scroll>'
        '<visible>Integer.IsEqual(Container(5200).NumItems,0) + !Container(5200).IsUpdating</visible>')+
  label(SIDE,top+330,WIDTH-2*SIDE,60,'Check the spelling or try fewer words.','p_sub',GREY,'center',
        '<visible>Integer.IsEqual(Container(5200).NumItems,0) + !Container(5200).IsUpdating</visible>')+
  label(SIDE,top+90,WIDTH-2*SIDE,120,'Searching…','p_body',GREY,'center','<visible>Container(5200).IsUpdating</visible>')+
  '</control>')
 # Fuse's own search window starts its keyboard and widgets on load; this page does not.
 root=ET.fromstring(original) if original else ET.Element('window')
 bare='<window%s />'%''.join(' %s="%s"'%(k,e(v)) for k,v in root.attrib.items())
 body='<controls>%s%s%s%s<control type="image"><height>2</height><texture /></control>%s</controls>'%(backdrop(),panel,results,old,tabbar('search'))
 return window(bare,body,'5100')

VARIABLES=('<variable name="Portrait_Hero_Art"><value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value>'
           '<value>$INFO[ListItem.Art(poster)]</value></variable>'
           '<variable name="Portrait_Card_Art"><value condition="!String.IsEmpty(ListItem.Art(landscape))">$INFO[ListItem.Art(landscape)]</value>'
           '<value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value><value>$INFO[ListItem.Art(thumb)]</value></variable>')

# --- show page (seasons as chips, episodes below), episode lists and plain folders ------------------------
DL_GAP=20;DL_H=108;DL_SHIFT=DL_GAP+DL_H   # the Download button under Play pushes the seasons page down by this
DOWNLOAD_SEASON=('RunScript(service.kodi.ios.bootstrap,download,kind=season,'
 'path=$ESCINFO[Container(50).ListItem.FolderPath],season=$INFO[Container(50).ListItem.Season],'
 'title=$ESCINFO[ListItem.TVShowTitle],year=$INFO[ListItem.Year],'
 'tvshow.tmdb_id=$INFO[Container(50).ListItem.Property(tvshow.tmdb_id)])')
DOWNLOADED_SHOW='String.IsEqual(Container.Property(KodiIOS.DownloadedShow),true)'
def show_header(ids_down):
 """A show's header is ordinary page content, so the same vertical page moves art, controls and episodes."""
 art_h=840;logo='$INFO[ListItem.Art(tvshow.clearlogo)]'
 # A selected season has its own next playable episode; the child episode page uses the container fallback.
 play=[(DOWNLOADED_SHOW+' + Container.Content(seasons) + !String.IsEmpty(Container(50).ListItem.Property(KodiIOS.PlayPath))','PlayMedia($ESCINFO[Container(50).ListItem.Property(KodiIOS.PlayPath)])'),
       (DOWNLOADED_SHOW+' + Container.Content(seasons) + String.IsEmpty(Container(50).ListItem.Property(KodiIOS.PlayPath))','PlayMedia($ESCINFO[Container.Property(KodiIOS.PlayPath)])'),
       (DOWNLOADED_SHOW+' + Container.Content(episodes)','PlayMedia($ESCINFO[Container.Property(KodiIOS.PlayPath)])'),
       ('!'+DOWNLOADED_SHOW,'PlayMedia($ESCINFO[Container(60).ListItemAbsolute(0).FileNameAndPath])')]
 header=('<control type="group"><width>%d</width><height>744</height>'%WIDTH+
  image(0,0,WIDTH,art_h,'$VAR[Portrait_Show_Art]',WHITE,'','>scale',background=True)+
  image(0,0,WIDTH,art_h,MEDIA+'hero_fade.png')+image(0,0,WIDTH,300,MEDIA+'fade_down.png')+
  '<control type="image"><left>140</left><top>430</top><width>800</width><height>230</height><aspectratio aligny="bottom">keep</aspectratio><texture>%s</texture></control>'%logo+
  label(SIDE,430,WIDTH-2*SIDE,230,'$VAR[Portrait_Show_Title]','p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(tvshow.clearlogo))</visible>')+
  label(SIDE,672,WIDTH-2*SIDE,52,'[COLOR %s]$VAR[Portrait_Show_Rating,★ ]  [/COLOR]$VAR[Portrait_Show_Year]$VAR[Portrait_Show_Genres,  ·  ]'%GREEN,'p_foot',GREY,'center')+'</control>')
 play_visible='Container.Content(seasons) | [Container.Content(episodes) + '+DOWNLOADED_SHOW+']'
 play_button=pill_button(9002,SIDE,0,WIDTH-2*SIDE,124,'$VAR[Portrait_Show_Play_Label]',play,'primary',MEDIA+'play.png',
  '<visible>%s</visible><onup>9001</onup><ondown condition="%s">52</ondown><ondown condition="%s">50</ondown><ondown condition="%s">9003</ondown>'%(
   play_visible,'Container.Content(episodes)','['+DOWNLOADED_SHOW+' | !System.HasAddon(plugin.video.elementum)] + Container.Content(seasons)','!'+DOWNLOADED_SHOW+' + Container.Content(seasons) + System.HasAddon(plugin.video.elementum)'),inline=True)
 header+='<control type="group"><width>%d</width><height>144</height><visible>%s</visible>%s</control>'%(WIDTH,play_visible,play_button)
 download_visible='Container.Content(seasons) + !'+DOWNLOADED_SHOW+' + System.HasAddon(plugin.video.elementum)'
 header+='<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>'%(WIDTH,DL_SHIFT,download_visible,
  pill_button(9003,SIDE,0,WIDTH-2*SIDE,DL_H,'Download $VAR[Portrait_Season_Short]',[('',DOWNLOAD_SEASON)],'glass',ICONS+'download.png',
              '<visible>%s</visible><onup>9002</onup><ondown>50</ondown>'%download_visible,inline=True))
 header+='<control type="group"><width>%d</width><height>160</height><control type="textbox"><left>%d</left><top>0</top><width>%d</width><height>132</height><font>p_foot</font><textcolor>%s</textcolor><label>$VAR[Portrait_Show_Plot]</label><autoscroll>false</autoscroll></control></control>'%(WIDTH,SIDE,WIDTH-2*SIDE,GREY)
 return header

def episode_item(focused):
 thumb_w,thumb_h=400,225
 bg=surface(SIDE-18,4,WIDTH-2*SIDE+36,thumb_h+176,'round_s.png','14FFFFFF',26) if focused else ''
 return ('<control type="group"><visible>String.IsEqual(ListItem.DBType,episode)</visible>'+bg+image(SIDE,18,thumb_w,thumb_h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'thumb_mask.png')+
  image(SIDE,18,thumb_w,thumb_h,'$VAR[Portrait_Thumb]',WHITE,'','>scale',MEDIA+'thumb_mask.png',background=True)+
  image(SIDE+thumb_w//2-48,18+thumb_h//2-48,96,96,MEDIA+'glass_96.png')+icon(SIDE+thumb_w//2-18,18+thumb_h//2-20,40,MEDIA+'play.png')+
  episode_badges(SIDE,18,thumb_w,thumb_h)+
  textbox(SIDE+thumb_w+30,30,WIDTH-2*SIDE-thumb_w-30,116,'$INFO[ListItem.Episode,,. ]$INFO[ListItem.Title]','p_h3',WHITE)+
  label(SIDE+thumb_w+30,160,WIDTH-2*SIDE-thumb_w-30,48,'$INFO[ListItem.Duration(mins),,m]$INFO[ListItem.Premiered,  ·  ]','p_cap',GREY)+
  textbox(SIDE,thumb_h+36,WIDTH-2*SIDE,84,'$INFO[ListItem.Plot]','p_cap',GREY)+'</control>')

def video_nav(original):
 chip=lambda on:('<control type="group"><visible>String.IsEqual(ListItem.DBType,season)</visible>'+surface(0,8,250,96,'pill_96.png' if on else 'glass_96.png',WHITE,48)+
  label(0,8,250,96,'$VAR[Portrait_Chip_Label]','p_foot_b','FF000000' if on else WHITE,'center')+'</control>')
 chips=('<control type="list" id="50"><left>%d</left><top>%d</top><width>%d</width><height>112</height><orientation>horizontal</orientation>'
  '<ondown>60</ondown><onup condition="%s">9002</onup><onup condition="%s">9003</onup><scrolltime tween="cubic">250</scrolltime><visible>Container.Content(seasons)</visible>'
  '<itemlayout width="268" height="112">%s</itemlayout><focusedlayout width="268" height="112">%s</focusedlayout></control>')%(SIDE,0,WIDTH-SIDE,'['+DOWNLOADED_SHOW+' | !System.HasAddon(plugin.video.elementum)]','!'+DOWNLOADED_SHOW+' + System.HasAddon(plugin.video.elementum)',chip(False),chip(True))
 episodes=('<control type="list" id="%d"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<onup>%s</onup><scrolltime tween="cubic" easing="out">300</scrolltime><visible>%s</visible>'
  '<itemlayout height="420">%s</itemlayout><focusedlayout height="420">%s</focusedlayout>%s</control>')
 gen_item=lambda focused:((surface(SIDE-18,6,WIDTH-2*SIDE+36,198,'round_s.png','14FFFFFF',26) if focused else '')+
  image(SIDE,18,116,174,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'tile_mask.png')+
  image(SIDE,18,116,174,'$INFO[ListItem.Art(poster)]',WHITE,'<visible>!String.IsEmpty(ListItem.Art(poster))</visible>','>scale',MEDIA+'tile_mask.png',background=True)+
  icon(SIDE+18,65,80,'$INFO[ListItem.Icon]',WHITE,'<visible>String.IsEmpty(ListItem.Art(poster))</visible>')+
  label(SIDE+146,34,WIDTH-2*SIDE-210,80,'$INFO[ListItem.Label]','p_h3')+
  label(SIDE+146,108,WIDTH-2*SIDE-210,60,'$INFO[ListItem.Label2]','p_foot',GREY)+
  label(WIDTH-SIDE-40,18,40,174,'›','p_h2',DIM,'right'))
 generic=('<control type="list" id="51"><left>0</left><top>190</top><width>%d</width><bottom>0</bottom><onup>9001</onup>'
  '<scrolltime tween="cubic" easing="out">300</scrolltime><visible>!Container.IsUpdating + !Container.Content(seasons) + !Container.Content(episodes) + !Container.Content(movies) + !Container.Content(tvshows)</visible>'
  '<itemlayout height="210">%s</itemlayout><focusedlayout height="210">%s</focusedlayout></control>')%(WIDTH,gen_item(False),gen_item(True))
 back=nav_button(9001,SIDE,36,'chevron-left.png','Back','<ondown>9002</ondown>')
 plain_title=label(SIDE+136,36,WIDTH-2*SIDE-136,108,'$VAR[Portrait_Page_Title]','p_h2',WHITE,'left','<visible>!Container.IsUpdating + !Container.Content(seasons) + !Container.Content(episodes) + !Container.Content(movies) + !Container.Content(tvshows)</visible>')
 refresh=nav_button(9010,WIDTH-SIDE-108,36,'arrows-rotate.png',
  'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=library_refresh)','<ondown>53</ondown>',
  'String.StartsWith(Container.FolderPath,plugin://plugin.video.kodi.ios.watch/) + String.Contains(Container.FolderPath,action=library)')
 # One scroll owner for the complete show page. The native portrait handoff keeps this viewport lazy and
 # shares each vertical pan between the header and the episode list, including drags that begin on a card.
 show_page=('<control type="grouplist" id="9900"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
  '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
  '<scrolltime tween="cubic" easing="out">300</scrolltime><visible>Container.Content(seasons) | Container.Content(episodes)</visible>'
  '%s%s%s%s</control>')%(WIDTH,HEIGHT,show_header('50'),chips,
  episodes%(60,0,WIDTH,HEIGHT,'50','Container.Content(seasons)',episode_item(False),episode_item(True),'<content target="videos">$INFO[Container(50).ListItem.FolderPath]</content>'),
  episodes%(52,0,WIDTH,HEIGHT,'9002','Container.Content(episodes)',episode_item(False),episode_item(True),''))
 # Owner (build 229): "If i scroll down after i select a season the season selecter disappears". Once the page has
 # scrolled, the same seasons (the folder's own listing, cached by the add-on) stay pinned under the Back button. A tap
 # selects that season in the page's own row (SetFocus absolute takes a 0-based index; CurrentItem is 1-based).
 pinned_visible='Container.Content(seasons) + Container(9900).HasPrevious'
 pinned=('<control type="group"><visible>%s</visible>'%pinned_visible+
  '<animation effect="fade" start="0" end="100" time="180">Visible</animation><animation effect="fade" start="100" end="0" time="120">Hidden</animation>'+
  image(0,0,WIDTH,300,MEDIA+'white.png','FF000000')+image(0,300,WIDTH,60,MEDIA+'fade_down.png')+
  ('<control type="list" id="49"><left>%d</left><top>170</top><width>%d</width><height>112</height><orientation>horizontal</orientation>'
   '<onup>9001</onup><ondown>60</ondown><scrolltime tween="cubic">250</scrolltime>'
   '<onclick>SetFocus(50,$INFO[Container(49).CurrentItem],absolute)</onclick><onclick>Control.Move(50,-1)</onclick>'
   '<itemlayout width="268" height="112">%s</itemlayout><focusedlayout width="268" height="112">%s</focusedlayout>'
   '<content>$INFO[Container.FolderPath]</content></control>')%(SIDE,WIDTH-SIDE,pinned_chip(False),pinned_chip(True))+'</control>')
 body=('<controls>'+backdrop()+show_page+generic+grid()+image(0,0,WIDTH,90,MEDIA+'fade_down.png')+pinned+back+plain_title+refresh+'</controls>')
 return window(original,body,'50','<views>50,51,52,53</views>')

def pinned_chip(focused):
 """A season in the pinned row: white when it is the season the page shows (the row on the page decides)."""
 on='String.IsEqual(ListItem.Label,Container(50).ListItem.Label)'
 return ('<control type="group"><visible>String.IsEqual(ListItem.DBType,season)</visible>'+
  surface(0,8,250,96,'pill_96.png',WHITE,48,'<visible>%s</visible>'%on)+surface(0,8,250,96,'glass_96.png',WHITE,48,'<visible>!%s</visible>'%on)+
  label(0,8,250,96,'$VAR[Portrait_Chip_Label]','p_foot_b','FF000000','center','<visible>%s</visible>'%on)+
  label(0,8,250,96,'$VAR[Portrait_Chip_Label]','p_foot_b',WHITE,'center','<visible>!%s</visible>'%on)+'</control>')

GRID='Container.Content(movies) | Container.Content(tvshows)'
GRID_LARGE='String.IsEqual(Skin.String(Portrait.Grid),large)'   # Settings › Customisation › View Types
def grid():
 """Movies and shows (Library, categories, search results): a poster grid, three across (or two, View Types)."""
 gap=24
 def size(cols):
  w=(WIDTH-2*SIDE-(cols-1)*gap)//cols;return w,w*3//2
 def item(focused,w,h):
  return ('<control type="group"><left>0</left><top>0</top>%s'%('<animation effect="zoom" start="100" end="104" time="160" center="auto">Focus</animation>' if focused else '')+
   image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
   label(20,h-170,w-40,150,'$INFO[ListItem.Label]','p_foot_b',WHITE,'left','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(poster))</visible>')+
   image(0,0,w,h,'$INFO[ListItem.Art(poster)]',WHITE,'','>scale',MEDIA+'poster_mask.png',background=True)+
   poster_badges(w,h)+'</control>')
 (w3,h3),(w2,h2)=size(3),size(2);left=SIDE
 layouts=''
 for cond,(w,h) in (('',(w3,h3)),(GRID_LARGE,(w2,h2))):
  c=' condition="%s"'%cond if cond else ''
  layouts+=('<itemlayout width="%d" height="%d"%s>%s</itemlayout><focusedlayout width="%d" height="%d"%s>%s</focusedlayout>'
            %(w+gap,h+gap,c,item(False,w,h),w+gap,h+gap,c,item(True,w,h)))
 return (label(SIDE,180,WIDTH-2*SIDE,110,'$VAR[Portrait_Page_Title]','p_title',WHITE,'left','<visible>%s</visible>'%GRID)+
  ('<control type="panel" id="53"><left>%d</left><top>320</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><onup>9001</onup>'
   '<scrolltime tween="cubic" easing="out">300</scrolltime><visible>%s</visible>%s</control>')%(left,WIDTH-left,GRID,layouts))

SHOW_VARS=('<variable name="Portrait_Show_Art"><value condition="!String.IsEmpty(ListItem.Art(tvshow.fanart))">$INFO[ListItem.Art(tvshow.fanart)]</value>'
           '<value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value><value>$INFO[Container.Art(fanart)]</value></variable>'
           '<variable name="Portrait_Show_Title"><value condition="!String.IsEmpty(ListItem.TVShowTitle)">$INFO[ListItem.TVShowTitle]</value><value condition="!String.IsEmpty(Container.PluginCategory)">$INFO[Container.PluginCategory]</value><value>$INFO[Container.FolderName]</value></variable>'
           '<variable name="Portrait_Select_Art">'+''.join('<value condition="!String.IsEmpty(Container(%d).ListItem.Art(%s))">$INFO[Container(%d).ListItem.Art(%s)]</value>'%(c,k,c,k) for k in ('thumb','fanart','poster') for c in (3,6))+'</variable>'
           '<variable name="Portrait_Page_Title"><value condition="!String.IsEmpty(Window(Home).Property(Portrait.Title)) + String.IsEqual(Container.FolderName,TMDb Helper)">$INFO[Window(Home).Property(Portrait.Title)]</value>'
           '<value condition="!String.IsEmpty(Container.PluginCategory)">$INFO[Container.PluginCategory]</value>'
           '<value>$INFO[Container.FolderName]</value></variable>'
           '<variable name="Portrait_Thumb"><value condition="!String.IsEmpty(ListItem.Art(thumb))">$INFO[ListItem.Art(thumb)]</value><value>$INFO[ListItem.Art(fanart)]</value></variable>')

# Downloaded pages keep show metadata stable while an episode card is focused.
SHOW_VARS+=''.join('<variable name="Portrait_Show_%s"><value condition="%s + !String.IsEmpty(Container.Property(KodiIOS.Show%s))">$INFO[Container.Property(KodiIOS.Show%s)]</value><value>$INFO[ListItem.%s]</value></variable>'%
 (name,DOWNLOADED_SHOW,name,name,label) for name,label in (('Plot','Plot'),('Year','Year'),('Rating','Rating'),('Genres','Genre')))
SHOW_VARS+='<variable name="Portrait_Show_Play_Label"><value condition="%s + Container.Content(seasons) + !String.IsEmpty(Container(50).ListItem.Property(KodiIOS.PlayLabel))">$INFO[Container(50).ListItem.Property(KodiIOS.PlayLabel)]</value><value condition="%s">$INFO[Container.Property(KodiIOS.PlayLabel)]</value><value>Play $VAR[Portrait_Season_Short]</value></variable>'%(DOWNLOADED_SHOW,DOWNLOADED_SHOW)
SHOW_VARS+='<variable name="Portrait_Chip_Label"><value condition="String.IsEqual(ListItem.Season,0)">Specials</value><value condition="!String.IsEmpty(ListItem.Season)">Season $INFO[ListItem.Season]</value><value>$INFO[ListItem.Label]</value></variable>'
# "Season 4" (or Specials), not the season's long name, on the Play and Download buttons (owner, build 229).
SHOW_VARS+='<variable name="Portrait_Season_Short"><value condition="String.IsEqual(Container(50).ListItem.Season,0)">Specials</value><value condition="!String.IsEmpty(Container(50).ListItem.Season)">Season $INFO[Container(50).ListItem.Season]</value><value>$INFO[Container(50).ListItem.Label]</value></variable>'

# Settings › Customisation › Info Page: rows under the plot, from TMDb Helper, each behind Fuse's own switch
# (settings_page.INFO). (key, title, TMDb Helper info, setting, only for, landscape thumbnails)
INFO_ROWS=(('cast','Starring','cast','VideoInfo.Widgets.DisableStarring','',False),
           ('crew','Crew','crew','VideoInfo.Widgets.DisableCrew','',False),
           ('seasons','Seasons','seasons','VideoInfo.Widgets.DisableSeasons','tvshow',False),
           ('collection','Collection','collection','VideoInfo.Widgets.DisableCollection','movie',False),
           ('similar','More Like This','recommendations','VideoInfo.Widgets.DisableRecommendations','',False),
           ('videos','Videos & Trailers','videos','VideoInfo.Widgets.DisableVideos','',True))
INFO_ID=5101
INFO_KIND='[String.IsEqual(ListItem.DBType,movie) | String.IsEqual(ListItem.DBType,tvshow)]'
def info_variables():
 tmdb='plugin://plugin.video.themoviedb.helper/?info=%s&'
 query=('<variable name="Portrait_Info_Query">'
  '<value condition="String.IsEqual(ListItem.DBType,tvshow) + !String.IsEmpty(ListItem.UniqueID(tmdb))">tmdb_type=tv&amp;tmdb_id=$INFO[ListItem.UniqueID(tmdb)]</value>'
  '<value condition="String.IsEqual(ListItem.DBType,tvshow)">tmdb_type=tv&amp;query=$INFO[ListItem.Title]&amp;year=$INFO[ListItem.Year]</value>'
  '<value condition="!String.IsEmpty(ListItem.UniqueID(tmdb))">tmdb_type=movie&amp;tmdb_id=$INFO[ListItem.UniqueID(tmdb)]</value>'
  '<value>tmdb_type=movie&amp;query=$INFO[ListItem.Title]&amp;year=$INFO[ListItem.Year]</value></variable>')
 rows=''
 for key,_,info,setting,only,_ in INFO_ROWS:
  cond='!Skin.HasSetting(%s) + %s + System.HasAddon(plugin.video.themoviedb.helper)'%(setting,'String.IsEqual(ListItem.DBType,%s)'%only if only else INFO_KIND)
  # Empty while the switch is off, so a section that is off never asks TMDb Helper for anything.
  rows+='<variable name="Portrait_Info_%s"><value condition="%s">%s$VAR[Portrait_Info_Query]</value><value></value></variable>'%(key,e(cond),e(tmdb%info))
 return query+rows
def info_row(n,key,title,landscape):
 id=INFO_ID+n;w,h=(400,225) if landscape else (220,330)
 def item(focused):
  zoom='<animation effect="zoom" start="100" end="104" time="160" center="auto">Focus</animation>' if focused else ''
  return ('<control type="group"><left>%d</left><top>10</top>%s'%(SIDE,zoom)+
   image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+('thumb_mask.png' if landscape else 'poster_mask.png'))+
   image(0,0,w,h,'$INFO[ListItem.Art(%s)]'%('thumb' if landscape else 'poster'),WHITE,'','>scale',MEDIA+('thumb_mask.png' if landscape else 'poster_mask.png'),background=True)+
   ('' if landscape else image(0,0,w,h,'$INFO[ListItem.Art(thumb)]',WHITE,'<visible>String.IsEmpty(ListItem.Art(poster))</visible>','>scale',MEDIA+'poster_mask.png',background=True))+
   label(0,h+10,w,44,'$INFO[ListItem.Label]','p_cap',WHITE)+label(0,h+52,w,40,'$INFO[ListItem.Label2]','p_cap',GREY)+'</control>')
 shown='Integer.IsGreater(Container(%d).NumItems,0) | Container(%d).IsUpdating'%(id,id)
 return (label(SIDE,0,WIDTH-2*SIDE,110,title,'p_h3',WHITE,'left','<aligny>bottom</aligny><visible>%s</visible>'%shown)+
  ('<control type="list" id="%d"><left>0</left><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
   '<scrolltime tween="cubic" easing="out">300</scrolltime><visible allowhiddenfocus="true">%s</visible>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
   '<content target="videos">$VAR[Portrait_Info_%s]</content></control>')%(id,WIDTH,h+110,shown,w+GAP,h+110,item(False),w+GAP,h+110,item(True),key))

def video_info(original):
 art_h=1150;w=WIDTH-2*SIDE
 body=('<controls>'+backdrop()+
  image(0,0,WIDTH,art_h,'$INFO[ListItem.Art(fanart)]',WHITE,'','>scale',background=True)+
  image(0,0,WIDTH,art_h,MEDIA+'hero_fade.png')+image(0,0,WIDTH,300,MEDIA+'fade_down.png')+
  '<control type="image"><left>140</left><top>640</top><width>800</width><height>250</height><aspectratio aligny="bottom">keep</aspectratio><texture>$INFO[ListItem.Art(clearlogo)]</texture></control>'+
  label(SIDE,640,w,250,'$INFO[ListItem.Title]','p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(clearlogo))</visible>')+
  label(SIDE,906,w,52,'[COLOR %s]$INFO[ListItem.Rating,★ ]  [/COLOR]$INFO[ListItem.Year]$INFO[ListItem.Genre,  ·  ]$INFO[ListItem.Duration(mins),  ·  ,m]$INFO[ListItem.MPAA,  ·  ]'%GREEN,'p_foot',GREY,'center')+
  pill_button(8,SIDE,990,w,124,'Play',[],'primary',MEDIA+'play.png','<visible>!String.IsEqual(ListItem.DBType,tvshow)</visible>')+
  pill_button(9010,SIDE,990,w,124,'Episodes',[('','Close'),('','ActivateWindow(Videos,$ESCINFO[ListItem.FolderPath],return)')],'primary','tv.png','<visible>String.IsEqual(ListItem.DBType,tvshow)</visible>')+
  # The plot, then the Info Page rows (Settings › Customisation › Info Page), scrolling under the buttons.
  '<control type="grouplist" id="5100"><left>0</left><top>1150</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
  '<itemgap>10</itemgap><usecontrolcoords>true</usecontrolcoords><onup>8</onup>'%WIDTH+
  '<control type="textbox" id="4"><left>%d</left><width>%d</width><height>420</height><font>p_sub</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label></control>'%(SIDE,w,GREY)+
  label(SIDE,0,w,60,'$INFO[ListItem.Director,Director: ]','p_cap',DIM)+
  ''.join(info_row(n,key,title,land) for n,(key,title,_,_,_,land) in enumerate(INFO_ROWS))+
  '<control type="image"><height>200</height><texture /></control></control>'+
  circle_button(9001,SIDE,36,108,'xmark.png','Close')+'</controls>')
 return window(original,body,'8')

def centered_dialog(original,body,default):
 """Dimmed screen (tap outside to close) with a card in the middle."""
 dim=('<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="99000000">%swhite.png</texturefocus>'
      '<texturenofocus colordiffuse="99000000">%swhite.png</texturenofocus><onclick>Close</onclick><onfocus>SetFocus(%s)</onfocus></control>')%(WIDTH,HEIGHT,MEDIA,MEDIA,default)
 anims=('<animation effect="zoom" start="92" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
        '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>'
        '<animation effect="fade" start="100" end="0" time="120">WindowClose</animation>')
 return window(original,'<controls>%s<control type="group">%s%s</control></controls>'%(dim,anims,body),default)

SELECT_ROWS=7
def select_dialog(original):
 """Kodi's select dialog, and so "How would you like to watch?": an iOS action sheet at the bottom of the screen
 (owner-approved board 01, docs/design/fuse-windows-mockups.html; roadmap U.1), sized to its rows: the question in a
 small bold heading, rows with the name on the left (a tile and a grey second line when the caller gives them),
 then a separate solid Cancel in blue. With the title's art (the watch chooser) the art leads the card."""
 x=27;w=WIDTH-2*x;row_h=132;cancel_h=156;gap=27;bottom=40
 titled='[!String.IsEmpty(Container(3).ListItem.Art(poster)) | !String.IsEmpty(Container(6).ListItem.Art(poster))]'
 count=lambda n,op='IsEqual':'[Integer.%s(Container(3).NumItems,%d) | Integer.%s(Container(6).NumItems,%d)]'%(op,n,op,n)
 head_plain,head_art=170,170+300
 # Card height for n rows (n<SELECT_ROWS; more rows scroll inside the full card).
 def card_h(n,head):return head+n*row_h
 full=card_h(SELECT_ROWS,head_art)+gap+cancel_h;top=HEIGHT-full-bottom
 heading=('<control type="image"><left>%d</left><top>36</top><width>420</width><height>236</height><texture diffuse="%sthumb_mask.png">$VAR[Portrait_Select_Art]</texture><aspectratio>scale</aspectratio><visible>%s</visible></control>'%((w-420)//2,MEDIA,titled)+
  '<control type="group"><visible>%s</visible>%s</control>'%(titled,label(40,290,w-80,150,'$INFO[Control.GetLabel(1)]','p_pill',WHITE,'center','<wrapmultiline>true</wrapmultiline>'))+
  '<control type="group"><visible>!%s</visible>%s</control>'%(titled,label(40,24,w-80,130,'$INFO[Control.GetLabel(1)]','p_pill',WHITE,'center','<wrapmultiline>true</wrapmultiline>'))+
  '<control type="label" id="1"><visible>false</visible></control>')
 icon_row='!String.IsEmpty(ListItem.Icon) + !String.StartsWith(ListItem.Icon,Default) + String.IsEmpty(ListItem.Art(poster))'
 # Owner-approved pickers (docs/design/settings-pages-mockups.html boards 13-14): a choice may carry a second line
 # (ListItem.Label2: "5 versions · from 18 GB") and a coloured tile (properties tint and glyph, as in the More menu).
 tile='!String.IsEmpty(ListItem.Property(tint))';two='!String.IsEmpty(ListItem.Label2)'
 item=lambda focused:(image(0,0,w,2,MEDIA+'white.png',SEP)+(image(0,2,w,row_h-2,MEDIA+'white.png','14FFFFFF') if focused else '')+
  icon(40,(row_h-72)//2,72,'$INFO[ListItem.Icon]',WHITE,'<visible>%s + !%s</visible>'%(icon_row,tile))+
  label(48,0,w-150,row_h,'$INFO[ListItem.Label]','p_body',WHITE,'left','<scroll>false</scroll><visible>![%s] + !%s + !%s</visible>'%(icon_row,tile,two))+
  label(140,0,w-200,row_h,'$INFO[ListItem.Label]','p_body',WHITE,'left','<visible>%s + !%s + !%s</visible>'%(icon_row,tile,two))+
  # a tile: 80 square in the choice's colour with its glyph, text beside it
  image(40,(row_h-80)//2,80,80,MEDIA+'tile_mask.png','$INFO[ListItem.Property(tint)]','<visible>%s</visible>'%tile)+
  icon(40+18,(row_h-44)//2,44,'$INFO[ListItem.Property(glyph)]',WHITE,'<visible>%s</visible>'%tile)+
  label(150,10,w-260,70,'$INFO[ListItem.Label]','p_body',WHITE,'left','<scroll>false</scroll><visible>%s + %s</visible>'%(tile,two))+
  label(150,0,w-260,row_h,'$INFO[ListItem.Label]','p_body',WHITE,'left','<scroll>false</scroll><visible>%s + !%s</visible>'%(tile,two))+
  label(150,72,w-260,48,'$INFO[ListItem.Label2]','p_foot',GREY,'left','<scroll>false</scroll><visible>%s + %s</visible>'%(tile,two))+
  # two lines, no tile: left-aligned name over its detail
  label(40,10,w-130,70,'$INFO[ListItem.Label]','p_body',WHITE,'left','<scroll>false</scroll><visible>!%s + %s</visible>'%(tile,two))+
  label(40,72,w-130,48,'$INFO[ListItem.Label2]','p_foot',GREY,'left','<scroll>false</scroll><visible>!%s + %s</visible>'%(tile,two))+
  icon(w-90,(row_h-44)//2,44,'check.png',ACCENT,'<visible>ListItem.IsSelected</visible>'))
 lists=''.join(('<control type="list" id="%d"><left>0</left><top>%d</top><width>%d</width><height>%d</height><onup>%d</onup><ondown>9050</ondown>'
  '<scrolltime tween="cubic">250</scrolltime><itemlayout height="%d">%s</itemlayout><focusedlayout height="%d">%s</focusedlayout>%s</control>'
  )%(id,head_plain,w,SELECT_ROWS*row_h,id,row_h,item(False),row_h,item(True),
     '<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(head_art-head_plain,titled)) for id in (3,6))
 # One card background per (row count, with/without art); the whole sheet slides to stay centred.
 cards=''
 for n in range(1,SELECT_ROWS+1):
  cond=count(n) if n<SELECT_ROWS else count(SELECT_ROWS-1,'IsGreater')
  for head,art_cond in ((head_art,titled),(head_plain,'!'+titled)):
   h=card_h(n,head)
   cards+=(image(0,0,w,h,MEDIA+'glass_card.png',WHITE,'<visible>%s + %s</visible>'%(cond,art_cond),border=44)+
     '<control type="group"><top>%d</top><visible>%s + %s</visible>%s</control>'%(h+gap,cond,art_cond,
      # A solid surface (no see-through glass: the page's buttons showed through it) with the blue Cancel.
      ('<control type="button"%s><left>0</left><top>0</top><width>%d</width><height>%d</height><label>Cancel</label><font>p_btn</font>'
       '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
       '<texturefocus border="44" colordiffuse="FF3A3A3C">%sglass_card.png</texturefocus><texturenofocus border="44" colordiffuse="FFFFFFFF">%sglass_card.png</texturenofocus>'
       '<onclick>Close</onclick><onup>3</onup></control>')%(' id="9050"' if (n,head)==(1,head_art) else '',w,cancel_h,ACCENT,ACCENT,MEDIA,MEDIA)))
 slides=''.join('<animation effect="slide" end="0,%d" time="0" condition="%s + %s">Conditional</animation>'%(full-(card_h(n,head)+gap+cancel_h),count(n),c)
               for n in range(1,SELECT_ROWS) for head,c in ((head_art,titled),(head_plain,'!'+titled)))
 # A long list without art: the full card is shorter by the art's height, so it moves down to the bottom too.
 slides+='<animation effect="slide" end="0,%d" time="0" condition="%s + !%s">Conditional</animation>'%(head_art-head_plain,count(SELECT_ROWS-1,'IsGreater'),titled)
 hidden=''.join('<control type="button" id="%d"><visible>false</visible></control>'%i for i in (5,7,8))+'<control type="label" id="2"><visible>false</visible></control>'
 body='<left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s%s%s%s%s'%(x,top,w,full,slides,cards,heading,lists,hidden)
 return centered_dialog(original,body,'3')

# Board 11 (owner-approved, docs/design/fuse-windows-mockups.html; roadmap U.10): Fuse's options window (1170) is the
# More menu here, drawn as the activity sheet: grabber, large title, close, grouped rows with chevrons, a footnote.
# Places to go first, then app upkeep.
MORE_GROUPS=(('Settings','Google Drive','Favourites','Transfers'),('Check for updates','iPhone navigation / recovery'))
def more_menu(original):
 """The More menu (the profile button, Fuse's window 1170) as a bottom sheet in the activity sheet's style: SURFACE
 sheet with 38 pt top corners, SURFACE2 groups with 16 pt corners, 54 pt rows with a tile, the name and a chevron.
 Every row goes somewhere, so it closes with the close button (and a tap on the dimmed page), not Done."""
 W=WIDTH;side=43;w=W-2*side;row=145;head=200;gap=43;foot=120;tile=80
 by_name={t:(t,i,c,a) for t,i,c,a in MORE}
 groups=[[by_name[t] for t in names if t in by_name] for names in MORE_GROUPS]
 groups=[g for g in groups if g]
 h=head+sum(len(g)*row for g in groups)+gap*(len(groups)-1)+foot
 top=HEIGHT-h
 def item(focused,list_id):
  backs=''.join(image(0,0,w,row,MEDIA+tex,SURFACE2,'<visible>String.IsEqual(ListItem.Property(pos),%s)</visible>'%pos,border=43) for pos,tex in
                (('only','row_only.png'),('first','row_first.png'),('last','row_last.png'),('mid','white.png')))
  return (backs+(''.join(image(0,0,w,row,MEDIA+tex,'14FFFFFF','<visible>Control.HasFocus(%d) + String.IsEqual(ListItem.Property(pos),%s)</visible>'%(list_id,pos),border=43) for pos,tex in
                (('only','row_only.png'),('first','row_first.png'),('last','row_last.png'),('mid','white.png'))) if focused else '')+
   image(40,(row-tile)//2,tile,tile,MEDIA+'tile_mask.png','$INFO[ListItem.Property(tint)]')+
   icon(40+10,(row-60)//2,60,'$INFO[ListItem.Icon]')+
   label(150,0,w-250,row,'$INFO[ListItem.Label]','p_body',WHITE,'left','<scroll>false</scroll>')+
   icon(w-84,(row-48)//2,48,'chevron-right.png',GREY)+
   image(150,0,w-150,2,MEDIA+'white.png',SEP,'<visible>!String.IsEqual(ListItem.Property(pos),first) + !String.IsEqual(ListItem.Property(pos),only)</visible>'))
 lists='';y=head
 for n,group in enumerate(groups):
  pos=lambda k:'only' if len(group)==1 else 'first' if k==0 else 'last' if k==len(group)-1 else 'mid'
  items=''.join('<item><label>%s</label><icon>%s</icon><property name="tint">%s</property><property name="pos">%s</property>'
                '<onclick>Dialog.Close(1170)</onclick><onclick>%s</onclick></item>'%(e(t),ICONS+i,c,pos(k),e(a)) for k,(t,i,c,a) in enumerate(group))
  up='9600' if n==0 else str(3+n-1);down=str(3+n+1) if n<len(groups)-1 else str(3+n)
  lists+=('<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><onup>%s</onup><ondown>%s</ondown>'
          '<itemlayout height="%d">%s</itemlayout><focusedlayout height="%d">%s</focusedlayout><content>%s</content></control>')%(
          3+n,side,y,w,len(group)*row,up,down,row,item(False,3+n),row,item(True,3+n),items)
  y+=len(group)*row+gap
 y-=gap
 content=('<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height>'%(top,W,h)+
  image(0,0,W,h+140,MEDIA+'sheet_bg.png',SURFACE,border=102)+
  image((W-100)//2,22,100,14,MEDIA+'dot.png','4DFFFFFF',border=7)+
  label(side+12,60,w-200,120,'More','p_title')+
  close_button(9600,W-side-118,62,navigation='<onclick>Close</onclick><ondown>3</ondown>')+lists+
  label(side+12,y+16,w-24,60,'Kodi $INFO[System.BuildVersionShort]$INFO[Window(Home).Property(KodiIOS.Build), · build ]','p_foot',GREY,'left','<scroll>false</scroll>')+
  '</control>')
 anim=('<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
       '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>')%(h,h)
 body=('<controls><control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="73000000">%swhite.png</texturefocus>'
       '<texturenofocus colordiffuse="73000000">%swhite.png</texturenofocus><onclick>Close</onclick><onfocus>SetFocus(3)</onfocus></control>'%(W,HEIGHT,MEDIA,MEDIA)+
       '<control type="group"><animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>%s%s</control></controls>'%(anim,content))
 return window(original,body,'3')

CTX_ROWS=15
# Context menu entries -> icon (first match wins; Kodi's String.Contains ignores case).
CTX_ICONS=[('Resume','clock-rotate-left.png'),('Trailer','film.png'),('next','forward.png'),('unwatched','eye-slash.png'),
           ('watched','eye.png'),('Play','play.png'),('Download','circle-down.png'),('Details','circle-info.png'),('Information','circle-info.png'),
           ('Info','circle-info.png'),('Show','tv.png'),('Season','tv.png'),('Queue','list.png'),('favourite','star.png'),
           ('Delete','trash.png'),('Remove','circle-xmark-regular.png'),('Search','magnifying-glass.png'),('Share','share.png'),
           ('Manage','gear.png'),('Settings','gear.png'),('Browse','folder.png'),('Add','square-plus.png')]
ITEM='Window(Home).Property(Portrait.Item.%s)'
def ctx_variables():
 # Media windows give the dialog their ListItem; Home and the hubs do not, so the bootstrap service keeps a
 # copy of the focused row item in Portrait.Item.* (focused_item_publisher).
 own='!String.IsEmpty(ListItem.Label)'
 pick=lambda name,mine,theirs:'<variable name="%s"><value condition="%s">%s</value><value>%s</value></variable>'%(name,own,mine,theirs)
 return (pick('Portrait_Ctx_Title','$INFO[ListItem.Label]','$INFO[%s]'%(ITEM%'Title'))+
  pick('Portrait_Ctx_Art','$VAR[Portrait_Card_Art]','$INFO[%s]'%(ITEM%'Art'))+
  # Board 07 (owner): Kodi's "Information" reads "Details" (string 19033); every other row as Kodi names it.
  ''.join('<variable name="Portrait_Ctx_Label_%d"><value condition="String.IsEqual(Control.GetLabel(%d),$LOCALIZE[19033])">Details</value>'
          '<value>$INFO[Control.GetLabel(%d)]</value></variable>'%(i,1001+i,1001+i) for i in range(CTX_ROWS))+
  pick('Portrait_Ctx_Sub','$INFO[ListItem.Property(subtitle)]$INFO[ListItem.Year]$INFO[ListItem.Genre,  ·  ]','$INFO[%s]'%(ITEM%'Sub'))+''.join('<variable name="Portrait_Ctx_Icon_%d">%s<value>%sellipsis.png</value></variable>'%(i,''.join(
  '<value condition="String.Contains(Control.GetLabel(%d),%s)">%s%s</value>'%(1001+i,word,ICONS,name) for word,name in CTX_ICONS),ICONS) for i in range(CTX_ROWS)))

# Rows whose action cannot be undone or takes the item away: red, as iOS draws destructive menu items (board 07).
CTX_RED=('Remove','Delete')
def context_menu(original):
 """Long press (owner-approved board 07, docs/design/fuse-windows-mockups.html; roadmap U.5): the page dims, the
 item is lifted as a copy (its 16:9 art, the small line and the title) and an iOS context menu opens under it:
 340 pt wide (the board's Continue Watching menu: long names fit), 48 pt rows with the name on the left and its glyph on the right, hairlines between rows, 24 pt
 corners, destructive rows (Remove, Delete) in red. A tap on a row plays/opens straight away (2.19); only a long
 press gets here. Kodi cannot morph the item into the preview or know where it sits on the page, so the copy
 is drawn at the top of the screen with the menu under it. Kodi fills the rows (list 996 from button 1000);
 the skin cannot choose which entries Kodi and the add-ons put there."""
 x=SIDE;card_w,art_h=CARD;top=230;cap_h=150;card_h=art_h+cap_h;menu_w=914;row_h=129;pad=48
 menu_top=top+card_h+32
 no_art='String.IsEmpty(ListItem.Art(fanart)) + String.IsEmpty(ListItem.Art(landscape)) + String.IsEmpty(ListItem.Art(thumb)) + String.IsEmpty(Window(Home).Property(Portrait.Item.Art))'
 # Owner (build 229): tapping Dragon Ball in Continue Watching asked "Resume from 00:11:53" under The Awakening's card:
 # Kodi's resume prompt is this window too, and the focused item (the spotlight) is not what is being played. The
 # resume prompt (second row "Play from beginning", Kodi string 12021) never shows the card.
 no_art='[%s] | String.IsEqual(Control.GetLabel(1002),$LOCALIZE[12021])'%no_art
 fit_card=(HEIGHT-menu_top-60)//row_h;fit_screen=(HEIGHT-top-60)//row_h
 long_menu='Control.IsVisible(%d)'%(1001+fit_card);scrolls='Control.IsVisible(%d)'%(1001+fit_screen)
 card=('<control type="group"><left>%d</left><top>%d</top><visible>![%s] + !%s</visible>'%(x,top,no_art,long_menu)+
  '<animation effect="zoom" start="96" end="104" center="%d,%d" time="260" tween="cubic" easing="out">WindowOpen</animation>'%(card_w//2,card_h)+
  '<animation effect="zoom" start="104" end="104" center="%d,%d" time="0" condition="true">Conditional</animation>'%(card_w//2,card_h)+
  image(0,0,card_w,art_h,MEDIA+'white.png',SURFACE2,diffuse=MEDIA+'card_mask.png')+
  image(0,0,card_w,art_h,'$VAR[Portrait_Ctx_Art]',WHITE,'','>scale',MEDIA+'card_mask.png',background=True)+
  label(4,art_h+18,card_w-8,46,'$VAR[Portrait_Ctx_Sub]','p_foot',GREY,'left','<scroll>false</scroll>')+
  label(4,art_h+62,card_w-8,62,'$VAR[Portrait_Ctx_Title]','p_h3',WHITE,'left','<scroll>false</scroll>')+'</control>')
 # The buttons' own text is not drawn: each row's name is a label over it (Details for Information, red when
 # destructive), so the buttons only take the taps.
 template=('<control type="button" id="1000"><width>%d</width><height>%d</height><font>p_body</font><textcolor>00000000</textcolor>'
  '<focusedcolor>00000000</focusedcolor><textoffsetx>%d</textoffsetx><textwidth>%d</textwidth><align>left</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /></control>')%(menu_w,row_h,pad,menu_w-2*pad-100)
 red='[%s]'%' | '.join('String.Contains(Control.GetLabel(%%d),%s)'%w for w in CTX_RED)
 # The menu's background, one per row count (Kodi cannot size an image to the list), and per row its glyph on the
 # right, the hairline above it and, for a destructive row, the name again in red over the white one.
 backs=''.join(image(0,0,menu_w,n*row_h,MEDIA+'menu_round.png','F52C2C2E','<visible>Control.IsVisible(%d) + !Control.IsVisible(%d)</visible>'%(1000+n,1001+n),border=64)
               for n in range(1,CTX_ROWS+1))
 rows=''
 for i in range(CTX_ROWS):
  id=1001+i;y=i*row_h;bad=red.replace('%d',str(id));shown='Control.IsVisible(%d) + !%s'%(id,scrolls)
  last='!Control.IsVisible(%d)'%(id+1)
  # The focused row's highlight follows the menu's corners: the first row's top, the last row's bottom.
  hl=lambda tex,cond:image(0,y,menu_w,row_h,MEDIA+tex,'1FFFFFFF','<visible>Control.HasFocus(%d) + %s</visible>'%(id,cond),border=64)
  rows+=((hl('menu_round.png',last)+hl('menu_first.png','!'+last)) if i==0 else (hl('menu_last.png',last)+hl('white.png','!'+last)))
  rows+=((image(pad,y,menu_w-2*pad,2,MEDIA+'white.png',SEP,'<visible>%s</visible>'%shown) if i else '')+
   label(pad,y,menu_w-2*pad-100,row_h,'$VAR[Portrait_Ctx_Label_%d]'%i,'p_body',WHITE,'left','<scroll>false</scroll><visible>Control.IsVisible(%d) + !%s</visible>'%(id,bad))+
   label(pad,y,menu_w-2*pad-100,row_h,'$VAR[Portrait_Ctx_Label_%d]'%i,'p_body','FFFF453A','left','<scroll>false</scroll><visible>Control.IsVisible(%d) + %s</visible>'%(id,bad))+
   icon(menu_w-pad-72,y+(row_h-72)//2,72,'$VAR[Portrait_Ctx_Icon_%d]'%i,WHITE,'<visible>%s + !%s</visible>'%(shown,bad))+
   icon(menu_w-pad-72,y+(row_h-72)//2,72,'$VAR[Portrait_Ctx_Icon_%d]'%i,'FFFF453A','<visible>%s + %s</visible>'%(shown,bad)))
 # No art (e.g. a menu button) or a long menu: the menu moves up to where the card would be.
 menu=('<control type="group"><left>%d</left><top>%d</top>'%(x,menu_top)+
  '<animation effect="slide" end="%d,%d" time="0" condition="[%s] | %s">Conditional</animation>'%((WIDTH-menu_w)//2-x,top-menu_top,no_art,long_menu)+
  # Without the card (e.g. Resume / Play from beginning) the menu sits in the middle of the screen, as an iOS
  # alert does: one step per possible row count, since Kodi cannot measure the list.
  ''.join('<animation effect="slide" end="0,%d" time="0" condition="[[%s] | %s] + Control.IsVisible(%d) + !Control.IsVisible(%d)">Conditional</animation>'
          %((HEIGHT-n*row_h)//2-top,no_art,long_menu,1000+n,1001+n) for n in range(1,fit_screen+1) if (HEIGHT-n*row_h)//2>top)+
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>'
  '<animation effect="zoom" start="90" end="100" center="%d,0" time="240" tween="cubic" easing="out">WindowOpen</animation>'%(menu_w//2)+
  backs+
  '<control type="grouplist" id="996"><width>%d</width><height>%d</height><orientation>vertical</orientation><itemgap>0</itemgap>%s</control>'
  %(menu_w,HEIGHT-top-60,template)+rows+'</control>')
 # No background control (999): Kodi would resize it to the menu and centre the dialog on the pressed item.
 # Without one the dialog is the full screen, so the card and menu stay where this layout puts them.
 body=('<controls><control type="image"><width>%d</width><height>%d</height><texture colordiffuse="80000000">%swhite.png</texture>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation></control>'
  '<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus /><texturenofocus /><onclick>Close</onclick><onfocus>SetFocus(996)</onfocus></control>'
  '%s%s</controls>')%(WIDTH,HEIGHT,MEDIA,WIDTH,HEIGHT,card,menu)
 return window(original,body,'996')

def deck_row(focused):
 """One version on the Deck page: headline, features, size and source; the best match carries a badge."""
 w=WIDTH-2*SIDE;h=236;dark='FF000000';text=dark if focused else WHITE;sub='B3000000' if focused else GREY;dim='80000000' if focused else DIM
 card=surface(0,0,w,h-24,'round.png','FFF5F5F7' if focused else 'F22C2C2E',32)
 badge=('<control type="group"><right>28</right><top>26</top><width>250</width><height>56</height>'
  '<visible>!String.IsEmpty(ListItem.Property(badge))</visible>'+
  image(0,0,250,56,MEDIA+'pill_56.png',dark if focused else '40FFFFFF',border=28)+
  label(0,0,250,56,'$INFO[ListItem.Property(badge)]','p_cap',WHITE,'center')+'</control>')
 # Room for the badge; long headlines end in "..." instead of scrolling.
 return (card+label(40,22,w-320,70,'$INFO[ListItem.Property(headline)]','p_h3',text,'left','<scroll>false</scroll>')+
  label(40,92,w-80,56,'$INFO[ListItem.Property(tags)]','p_foot',sub)+
  label(40,146,w-80,50,'$INFO[ListItem.Property(meta)]','p_foot',dim)+badge)

def links_row(focused):
 """One link on the All Links page (board 16): the release as the title, up to four tag pills (AV1 in orange: it
 can need converting), size and seeds on one line."""
 w=WIDTH-2*SIDE;h=228;text='FF000000' if focused else WHITE;sub='B3000000' if focused else GREY
 card=surface(0,0,w,h-20,'round.png','FFF5F5F7' if focused else 'F22C2C2E',32)
 pills=''
 for n in range(1,5):
  x=40+(n-1)*186;kind='String.IsEqual(ListItem.Property(tag%d.kind),av1)'%n;has='!String.IsEmpty(ListItem.Property(tag%d))'%n
  pills+=('<control type="group"><left>%d</left><top>98</top><width>174</width><height>56</height><visible>%s</visible>'%(x,has)+
   image(0,0,174,56,MEDIA+'pill_56.png','40000000' if focused else '33FFFFFF','<visible>!%s</visible>'%kind,border=28)+
   image(0,0,174,56,MEDIA+'pill_56.png','FFFF9F0A','<visible>%s</visible>'%kind,border=28)+
   label(0,0,174,56,'[B]$INFO[ListItem.Property(tag%d)][/B]'%n,'p_cap',text,'center','<scroll>false</scroll>')+'</control>')
 return (card+label(40,20,w-80,72,'$INFO[ListItem.Property(headline)]','p_h3',text,'left','<scroll>false</scroll>')+pills+
  label(40,158,w-80,46,'$INFO[ListItem.Property(meta)]','p_foot',sub))

def deck_page(original=''):
 """The Deck's "Choose a version" page (Elementum and Umbrella, deck_picker.py) drawn for portrait. Kodi looks
 for an add-on's window in the current skin folder first, so this one is used while the phone is upright; the
 Deck's own landscape page stays in the add-ons. Same control ids and properties as the Deck page."""
 prop=lambda name:'$INFO[Window().Property(deck.%s)]'%name
 has=lambda name:'!String.IsEmpty(Window().Property(deck.%s))'%name
 art_h=760;top=300;poster_w,poster_h=240,360
 head=(image(0,0,WIDTH,art_h,prop('fanart'),'99FFFFFF','<visible>%s</visible>'%has('fanart'),'>scale',background=True)+
  image(0,0,WIDTH,art_h,MEDIA+'hero_fade.png')+image(0,0,WIDTH,300,MEDIA+'fade_down.png')+
  '<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(SIDE,top,has('poster'))+
  image(0,0,poster_w,poster_h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  image(0,0,poster_w,poster_h,prop('poster'),WHITE,'','>scale',MEDIA+'poster_mask.png',background=True)+'</control>'+
  '<control type="group"><left>%d</left><top>%d</top><width>%d</width>'%(SIDE+poster_w+36,top,WIDTH-2*SIDE-poster_w-36)+
  '<visible>%s</visible>'%has('poster')+
  label(0,0,WIDTH-2*SIDE-poster_w-36,130,prop('title'),'p_h2',WHITE,'left','<aligny>top</aligny><wrapmultiline>true</wrapmultiline>')+
  label(0,140,WIDTH-2*SIDE-poster_w-36,50,prop('meta'),'p_foot',GREY)+
  '<control type="textbox"><top>200</top><width>%d</width><height>160</height><font>p_foot</font><textcolor>%s</textcolor><label>%s</label></control>'%(WIDTH-2*SIDE-poster_w-36,DIM,prop('plot'))+
  '</control>'+
  label(SIDE,top,WIDTH-2*SIDE,130,prop('subject'),'p_h2',WHITE,'left','<visible>!%s</visible><wrapmultiline>true</wrapmultiline>'%has('poster')))
 heading=('<control type="label" id="32501"><left>%d</left><top>%d</top><width>%d</width><height>100</height><font>p_title</font>'
  '<textcolor>FFFFFFFF</textcolor><label>Choose a version</label></control>')%(SIDE,top+poster_h+50,WIDTH-2*SIDE)
 sub=label(SIDE,top+poster_h+150,WIDTH-2*SIDE,56,'%s  ·  %s'%(prop('quality_label'),prop('count_label')),'p_sub',GREY)
 lst=('<control type="list" id="32503"><left>%d</left><top>%d</top><width>%d</width><bottom>40</bottom><orientation>vertical</orientation>'
  '<onup>32500</onup><scrolltime tween="cubic" easing="out">300</scrolltime>'
  '<itemlayout height="236">%s</itemlayout><focusedlayout height="236">%s</focusedlayout></control>')%(SIDE,top+poster_h+230,WIDTH-2*SIDE,deck_row(False),deck_row(True))
 back=nav_button(32500,SIDE,36,'chevron-left.png','Close','<ondown>32503</ondown><ondown>32504</ondown>')
 # Roadmap 2.1 (board 16): "Show All Links" opens this page in mode "all": a compact bar (back, All Links, the sort
 # menu), a large title, then every link with tag pills. The quality page keeps the poster header and list 32503.
 all_on="String.IsEqual(Window().Property(deck.mode),all)"
 normal='<control type="group"><visible>!%s</visible>%s%s%s%s</control>'%(all_on,head,heading,sub,lst)
 sort=('<control type="group"><visible>%s + !%s</visible>'%(all_on,has('empty'))+   # nothing to sort when empty (board 09)
  '<control type="button" id="32510"><left>%d</left><top>40</top><width>420</width><height>100</height>'%(WIDTH-SIDE-420)+
  '<label>$INFO[Window().Property(deck.sort)]</label><font>p_btn</font><textcolor>FF4FA8FF</textcolor><focusedcolor>FF64D2FF</focusedcolor>'
  '<align>right</align><aligny>center</aligny><textoffsetx>56</textoffsetx><texturefocus /><texturenofocus /><ondown>32504</ondown><onleft>32500</onleft></control>'+
  image(WIDTH-SIDE-40,70,40,40,ICONS+'chevron-down.png','FF4FA8FF')+'</control>')
 links=('<control type="list" id="32504"><left>%d</left><top>380</top><width>%d</width><bottom>40</bottom><orientation>vertical</orientation>'
  '<onup>32510</onup><scrolltime tween="cubic" easing="out">300</scrolltime><visible>%s</visible>'
  '<itemlayout height="228">%s</itemlayout><focusedlayout height="228">%s</focusedlayout></control>')%(SIDE,WIDTH-2*SIDE,all_on,links_row(False),links_row(True))
 all_page=('<control type="group"><visible>%s</visible>'%all_on+
  label(SIDE,150,WIDTH-2*SIDE,120,'All Links','p_large',WHITE)+
  label(SIDE,270,WIDTH-2*SIDE,70,'%s  ·  %s'%(prop('subject'),prop('count_label')),'p_sub',GREY,'left','<scroll>false</scroll>')+'</control>')
 # Board 09 states (docs/design/fuse-windows-mockups.html): results arriving while providers still answer (the picker
 # sets deck.status, e.g. "3 of 5 providers answered"; Stop sets deck.stop) and nothing found (deck.empty with its
 # one next step; Try Again sets deck.retry). Plain words, no provider names or errors on screen.
 searching=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>230</height><visible>%s + %s</visible>'%(SIDE,HEIGHT-300,WIDTH-2*SIDE,all_on,has('status'))+
  surface(0,0,WIDTH-2*SIDE,230,'round.png','F22C2C2E',32)+
  label(40,24,WIDTH-2*SIDE-260,60,'Still searching','p_h3',WHITE,'left','<scroll>false</scroll>')+
  label(40,82,WIDTH-2*SIDE-260,48,prop('status'),'p_foot',GREY,'left','<scroll>false</scroll>')+
  pages.slide_bar(MEDIA,40,150,WIDTH-2*SIDE-80)+
  '<control type="button" id="32511"><left>%d</left><top>16</top><width>200</width><height>118</height><label>Stop</label><font>p_btn</font>'
  '<textcolor>%s</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>center</align><aligny>center</aligny><texturefocus /><texturenofocus />'
  '<onclick>SetProperty(deck.stop,true)</onclick><onup>32504</onup><onleft>32504</onleft></control>'%(WIDTH-2*SIDE-220,ACCENT)+'</control>')
 empty=('<control type="group"><visible>%s + %s</visible>'%(all_on,has('empty'))+
  icon((WIDTH-104)//2,570,104,'magnifying-glass.png',GREY)+   # board 09: the search glyph above the words
  label(SIDE,700,WIDTH-2*SIDE,90,'No versions found','p_h2',WHITE,'center')+
  '<control type="textbox"><left>%d</left><top>800</top><width>%d</width><height>200</height><font>p_sub</font><textcolor>%s</textcolor><align>center</align><label>%s</label></control>'%(SIDE+40,WIDTH-2*SIDE-80,GREY,prop('empty'))+
  pill_button(32512,(WIDTH-360)//2,1010,360,112,'Try Again',[('','SetProperty(deck.retry,true)')],'primary','','<onup>32500</onup>')+'</control>')
 body='<controls>%s%s%s%s%s%s%s%s</controls>'%(backdrop(),normal,all_page,links,sort,searching,empty,back)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">32503</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>%s</window>\n')%(MARKER,body)

NOTICE_SLOTS=4;NOTICE_ROWS=15
NOTICE_FILTERS=(('all','All'),('general','General'),('downloads','Downloads'),('problems','Problems'))   # buttons 9101-9104, notifications.FILTER_KEYS
def notices_page():
 import notifications_skin
 return notifications_skin.page(type('PortraitTokens',(),globals()))


def shrink(data,name=''):
 root=ET.fromstring(data)
 if root.tag!='window':return None
 controls=root.find('controls')
 if controls is None:return None
 scale=WIDTH/1920;h=round(1080*scale,1);top=round((HEIGHT-h)/2,1)
 group=ET.Element('control',{'type':'group'})
 for key,value in (('description',MARKER+' landscape window'),('left','0'),('top','0'),('width','1920'),('height','1080')):ET.SubElement(group,key).text=value
 anim=ET.SubElement(group,'animation',{'effect':'zoom','start':'0,0,1920,1080','end':'0,%s,%d,%s'%(top,WIDTH,h),'time':'0','condition':'true'});anim.text='Conditional'
 # The landscape safe-area frame (navigation.FRAME) would black out the portrait screen around the window.
 for parent in root.iter():
  for child in list(parent):
   if child.tag=='control' and child.get('id')=='98400':parent.remove(child)
 for child in list(controls):controls.remove(child);group.append(child)
 if root.get('type')!='dialog' and not name.startswith('Dialog'):
  bg=ET.SubElement(controls,'control',{'type':'image'})
  for tag_,value in (('width',str(WIDTH)),('height',str(HEIGHT)),('texture','colors/black.png')):ET.SubElement(bg,tag_).text=value
  ET.SubElement(bg,'colordiffuse').text='FF000000';bg.find('texture').text=MEDIA+'white.png'
 controls.append(group)
 if root.get('type')!='dialog' and not name.startswith('Dialog'):
  # Fuse's backgrounds overflow 1920x1080; black bars keep them out of the empty top and bottom.
  for y,height in ((0,top),(top+h,HEIGHT-top-h)):
   bar=ET.SubElement(controls,'control',{'type':'image'})
   for key,value in (('top',str(y)),('width',str(WIDTH)),('height',str(height)),('texture',MEDIA+'white.png'),('colordiffuse','FF000000')):ET.SubElement(bar,key).text=value
 return b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='utf-8')+b'\n'

# Owner: the text should be San Francisco, Apple's typeface. Apple's licence does not allow shipping it in the app, but
# every iPhone has it: the portrait build copies the phone's own system font file into the writable skin's fonts
# folder (it never leaves the phone) and uses it for every style, bold styles with Kodi's bold rendering. Without it
# (another device, a new iOS path) Inter stays.
SF_CANDIDATES=('/System/Library/Fonts/CoreUI/SFUI.ttf','/System/Library/Fonts/Core/SFUI.ttf','/System/Library/Fonts/CoreUI/SFUIText.ttf',
               '/System/Library/Fonts/Core/SFUIText.ttf','/System/Library/Fonts/CoreUI/SFUI-Regular.otf')
SF_FILE='SF-UI.ttf'
def system_font(skin,candidates=SF_CANDIDATES):
 """The phone's San Francisco copied to <skin>/fonts/SF-UI.ttf (once; again when iOS updates it), or None."""
 import shutil
 for path in candidates:
  try:
   if not os.path.isfile(path):continue
   dest=Path(skin)/'fonts'/SF_FILE
   if not dest.exists() or dest.stat().st_size!=os.path.getsize(path):
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
   return SF_FILE
  except OSError:continue
 return None

# Owner (build-132): San Francisco "looks good but skinny". Kodi's FreeType draws the variable SFUI.ttf at its default
# instance and has no weight setting, only <style>bold</style> (FreeType's emboldening). Every style whose Inter file
# is heavier than Regular (Medium, SemiBold, Bold, ExtraBold, Black, Heavy) is drawn bold, and so are the primary
# white labels (row titles, settings rows, the search field: p_body); secondary grey text stays regular so headings
# and titles still stand out from it.
HEAVY_FILE=re.compile(r'(Medium|SemiBold|Bold|Black|Heavy)',re.I)
SF_BOLD_NAMES={'p_body'}
def sf_bold(name,filename):return bool(HEAVY_FILE.search(filename)) or name in SF_BOLD_NAMES

def fonts(original,sf=None):
 root=ET.fromstring(original)
 for fontset in root.findall('fontset'):
  for name,filename,size in FONTS:
   f=ET.SubElement(fontset,'font');ET.SubElement(f,'name').text=name;ET.SubElement(f,'filename').text=sf or filename;ET.SubElement(f,'size').text=str(size)
   if sf and sf_bold(name,filename):ET.SubElement(f,'style').text='bold'
 return b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='utf-8')+b'\n'

def with_variables(xml):return xml

def variable_block(row_variables=None):
 rows=''.join(v for _,v in sorted((row_variables or {}).items()))
 return VARIABLES+SHOW_VARS+ctx_variables()+info_variables()+rows

def includes(row_variables=None):
 # Kodi reads variables only from includes; Fuse's own includes still come from 1080i.
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<includes><include file="../1080i/Includes.xml" />%s</includes>\n'
         %(MARKER,variable_block(row_variables))).encode()

# Owner log (build 142): Kodi read the skin's includes once, from 1080i, because the screen turned portrait only
# after the skin loaded; Home then came from the portrait folder with every $VAR (rows, heroes, card art) undefined,
# so no row showed. The same variables now also come from 1080i (one include line in Fuse's Includes.xml), whichever
# folder Kodi reads first. A second identical definition is ignored by Kodi.
LANDSCAPE_VARS='Includes_Portrait.xml'
LANDSCAPE_HOOK='<include file="%s" />'%LANDSCAPE_VARS
def landscape_variables(row_variables=None):
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: portrait variables, also defined when Kodi reads 1080i -->\n'
         '<includes>%s</includes>\n'%(MARKER,variable_block(row_variables))).encode()
def landscape_includes(original):
 """Fuse's 1080i/Includes.xml with the include line for LANDSCAPE_VARS (once)."""
 if not original or LANDSCAPE_HOOK in original:return original
 if re.search(r'<includes\s*/>',original):return re.sub(r'<includes\s*/>','<includes>'+LANDSCAPE_HOOK+'</includes>',original,count=1)
 return re.sub(r'(<includes(?:\s[^>]*)?>)',lambda m:m.group(1)+'\n    '+LANDSCAPE_HOOK,original,count=1)

def hub_files(skin,profile,variables=None):
 source=Path(skin)/'1080i';out={}
 read=lambda name:(source/name).read_text(encoding='utf-8') if (source/name).exists() else ''
 hubs=[(tab,(title,load_widgets(profile,lists),tab,SPOTLIGHT[name],resume)) for name,(title,lists,tab,resume) in HUBS.items()]
 hubs.sort(key=lambda h:HUB_TABS.index(h[0]))
 out['Home.xml']=hubs_window(read('Home.xml'),hubs,variables).encode()
 for name,(title,lists,tab,resume) in HUBS.items():
  if name!='Home.xml':out[name]=forward_window(read(name),tab).encode()
 for name in LIBRARY_FILES:out[name]=library_window(read(name)).encode()
 out[SEARCH_FILE]=search_window(read(SEARCH_FILE)).encode()
 return out

def portrait_files(skin,profile):
 """Every file of the portrait folder, derived from the current 1080i folder and widget lists."""
 skin=Path(skin);source=skin/'1080i';files={}
 for path in sorted(source.glob('*.xml')):
  if path.name in HANDMADE or path.name in SKIP_WRAP or path.name in VIDEO_ONLY:continue
  raw=path.read_bytes()
  # Shrunk from the landscape seek bar as this refresh leaves it, so the next start finds nothing to change.
  if path.name=='DialogSeekBar.xml':raw=player_osd.hide_seekbar(raw.decode('utf-8')).encode()
  try:data=shrink(raw,path.name)
  except ET.ParseError:continue
  if data:files[FOLDER+'/'+path.name]=data
 read=lambda name:(source/name).read_text(encoding='utf-8') if (source/name).exists() else ''
 files[FOLDER+'/Font.xml']=fonts(read('Font.xml'),system_font(skin))
 files[FOLDER+'/MyVideoNav.xml']=with_variables(video_nav(read('MyVideoNav.xml'))).encode()
 files[FOLDER+'/DialogVideoInfo.xml']=with_variables(video_info(read('DialogVideoInfo.xml'))).encode()
 files[FOLDER+'/DialogSelect.xml']=select_dialog(read('DialogSelect.xml')).encode()
 files[FOLDER+'/Custom_1170_Dialog_Options.xml']=more_menu(read('Custom_1170_Dialog_Options.xml')).encode()
 files[FOLDER+'/DialogContextMenu.xml']=context_menu(read('DialogContextMenu.xml')).encode()
 # Fuse's landscape header (tabs/search/gear) is replaced by the portrait header and tab bar.
 files[FOLDER+'/Custom_1182_Dialog_Topmenu_Overlay.xml']=window(read('Custom_1182_Dialog_Topmenu_Overlay.xml'),'<controls />','9999').encode()
 row_variables={}
 for name,data in hub_files(skin,profile,row_variables).items():files[FOLDER+'/'+name]=data
 files[FOLDER+'/Includes.xml']=includes(row_variables)
 files['1080i/'+LANDSCAPE_VARS]=landscape_variables(row_variables)
 if read('Includes.xml'):files['1080i/Includes.xml']=landscape_includes(read('Includes.xml')).encode()
 for name,data in textures().items():files['extras/portrait/'+name]=data
 files[FOLDER+'/DeckSourceSelect.xml']=deck_page().encode()
 files[FOLDER+'/IOSNotifications.xml']=notices_page().encode()
 # Fuse's startup splash ("Arctic Fuse - Reticulating Splines") showed over Home, shrunk into portrait, for up to a
 # minute at every start. The window stays (Fuse keeps its startup status in its properties) but never shows.
 files[FOLDER+'/Custom_1198_Dialog_Startup.xml']=SPLASH
 files[FOLDER+'/Startup.xml']=STARTUP
 # Settings home, Customisation and Accounts in the iOS Settings style (settings_page.py).
 import types
 files.update(settings_page.files(types.SimpleNamespace(**globals()),read))
 files['extras/portrait/close_cross.png']=close_cross();files['extras/portrait/close_disc.png']=close_disc()
 # Round 2: shared dialogs, Add-ons, Event Log, System Info, File Manager, Umbrella's getting-ready, Play on TV.
 files.update(pages.files(types.SimpleNamespace(**globals()),read))
 # The activity pill in place of Kodi's background progress box, which is never drawn (activity_skin.py).
 ns=types.SimpleNamespace(**globals());files.update(activity_skin.files(ns))
 # Settings › Library › Library status and its details sheet (library_page.py).
 files.update(library_page.files(ns))
 # Notifications › a message's details with its part of kodi.log (notice_page.py).
 files.update(notice_page.files(ns))
 # The Transfers page (speed graph), opened from a transfer card in Notifications (transfers_page.py).
 files.update(transfers_page.files(ns))
 # Library tools: Queue, Phone space, History and AirPlay check (library_tools_page.py).
 files.update(library_tools_page.files(ns))
 # Settings › Customisation › Tabs & Rows › a tab (rows_page.py, filled by customise_rows.py).
 files.update(rows_page.files(ns))
 for rel in list(files):
  if rel.startswith(FOLDER+'/'):files[rel]=activity_skin.inject(ns,rel[len(FOLDER)+1:],files[rel])
 # Fullscreen video is landscape: the Apple TV-style controls go into the landscape folder.
 files['1080i/VideoOSD.xml']=player_osd.window().encode()
 # Fuse's seek bar flashed up at every video start (buffering, the resume jump): ours shows only while seeking.
 if (source/'DialogSeekBar.xml').exists():files['1080i/DialogSeekBar.xml']=player_osd.seekbar_window().encode()
 # Fuse's info over the video, clear of the Dynamic Island on either side (player_osd.safe_inset).
 for name in player_osd.INSET:
  if read(name):files['1080i/'+name]=player_osd.safe_inset(read(name),name in player_osd.HIDE_UNDER_OSD).encode()
 # Build 206: "Buffering 45%" over the video while Kodi fills its buffer.
 files['1080i/'+player_osd.BUFFER_WINDOW]=player_osd.buffering_window().encode()
 return files

def row_files(skin,profile):
 """Only the files the widget lists feed: the hubs (Home, Movies, TV) and their row variables, exactly as
 portrait_files makes them (scripts/test_customisation.py compares the two)."""
 import types
 row_variables={};files={}
 for name,data in hub_files(skin,profile,row_variables).items():files[FOLDER+'/'+name]=data
 files[FOLDER+'/Includes.xml']=includes(row_variables)
 files['1080i/'+LANDSCAPE_VARS]=landscape_variables(row_variables)
 ns=types.SimpleNamespace(**globals())
 for rel in list(files):
  if rel.startswith(FOLDER+'/'):files[rel]=activity_skin.inject(ns,rel[len(FOLDER)+1:],files[rel])
 return files

def refresh_rows(xbmc,invoke,skin,profile):
 """After Settings › Customisation › Tabs & Rows (owner, build 204: "ensure its quick"): the full refresh redrew every
 texture in Python (about 4.7 s in the desktop rig before Home showed the change); a row change only rewrites the
 hub files. The start-up marker is brought up to date so the next start does not rebuild everything."""
 import time
 started=time.monotonic()
 changed=write(skin,row_files(skin,profile))
 for folder in sorted({c.split('/')[0] for c in changed if '/' in c}):refresh_listing(skin,folder)
 try:
  marker=Path(profile)/INPUTS;marker.parent.mkdir(parents=True,exist_ok=True)
  marker.write_text(json.dumps({'inputs':fingerprint(skin,profile)})+'\n')
 except OSError:pass
 reload=bool(changed) and needs_reload(changed,xbmc.getCondVisibility)
 if reload and is_portrait(xbmc.getInfoLabel):invoke('ReloadSkin()')
 xbmc.log('Kodi iOS rows: %d hub files updated%s (%.3fs)'%(len(changed),'; skin reloaded' if reload else '',time.monotonic()-started),xbmc.LOGINFO)
 return changed

SPLASH=('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: Fuse startup splash, never shown -->\n'
        '<window type="dialog" id="1198"><visible>false</visible><controls /></window>\n'%MARKER).encode()

# Fuse's startup window ran its startup script at every launch: ~60 skin settings written again, a blurred copy of
# its background made with TMDb Helper (never shown in portrait) and a fixed one-second wait before Home. The script
# still runs once (Fuse's defaults); after that the app goes straight to Home.
STARTUP=('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: straight to Home after the first launch -->\n<window>'
 '<onload condition="Skin.HasSetting(Portrait.FuseStartupDone)">SetProperty(ReloadDone,1,Home)</onload>'
 '<onload condition="Skin.HasSetting(Portrait.FuseStartupDone)">ReplaceWindow(Home)</onload>'
 '<onload condition="!Skin.HasSetting(Portrait.FuseStartupDone)">RunScript(script.skinvariables,run_executebuiltin=special://skin/shortcuts/skinvariables-startup.json,use_rules=True,var_image_simplebackground=$VAR[Image_SimpleBackground])</onload>'
 '<onload condition="!Skin.HasSetting(Portrait.FuseStartupDone)">Skin.SetBool(Portrait.FuseStartupDone)</onload>'
 '<controls /></window>\n'%MARKER).encode()

def write(skin,files):
 changed=[]
 # Portrait copies of playback windows from earlier builds would be picked over the landscape ones.
 for name in sorted(VIDEO_ONLY|SKIP_WRAP):
  stale=Path(skin)/FOLDER/name
  if stale.is_file():stale.unlink();changed.append(FOLDER+'/'+name)
 for rel,data in files.items():
  dest=Path(skin)/rel
  if dest.exists() and dest.read_bytes()==data:continue
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);changed.append(rel)
 return changed

def build(skin,profile):
 """Write the portrait folder into a Fuse copy (IPA build). Returns {relative path: bytes}."""
 files=portrait_files(skin,profile);write(skin,files);add_resolutions(Path(skin)/'addon.xml')
 return files

def add_resolutions(addon):
 """Fuse's addon.xml lists the portrait resolutions exactly as RES says. Also upgrades a phone's writable copy that
 has older entries (the '9:19.5' label). Returns True when the file changed."""
 data=addon.read_text(encoding='utf-8')
 res=''.join('<res aspect="%s" default="false" folder="%s" width="%d" height="%d" />\n        '%(a,FOLDER,w,h) for a,w,h in RES)
 old=re.compile(r'<res [^>]*folder="%s"[^>]*/>\s*'%FOLDER)
 if ''.join(m.group(0) for m in old.finditer(data))==res:return False
 data=old.sub('',data)
 anchor=re.search(r'<res [^>]*default="true"[^>]*/>',data);assert anchor,'Fuse resolution list not found'
 addon.write_text(data[:anchor.start()]+res+data[anchor.start():],encoding='utf-8');return True

# --- on the phone ----------------------------------------------------------------------------------
def refresh(skin,profile):
 """On the phone: follow the owner's widget lists and any later landscape (1080i) repair.
 Returns the changed paths; the caller reloads the skin if any changed."""
 return write(skin,portrait_files(skin,profile))

# Written into 1080i by this module (portrait_files' '1080i/' entries, incl. pages.py's Play on TV), so they are not
# inputs: as an input, any later rewrite of one (navigation's start-up patching) would rebuild and reload at each start.
OWN_1080I={'VideoOSD.xml','DialogSeekBar.xml','Custom_1156_Buffering.xml','IOSPlayOnTV.xml','IOSTrackMenu.xml','IOSAirPlayFlow.xml','IOSAirPlayCheck.xml','Includes.xml','Includes_Portrait.xml','Custom_1187_Activity.xml','DialogExtendedProgressBar.xml','DialogBusy.xml',pages.NOTIFY,pages.VOLUME,pages.INFO_WAIT}|set(player_osd.INSET)   # + activity_skin.py, pages.BUSY, player_osd.INSET
INPUTS='addon_data/service.kodi.ios.bootstrap/portrait-inputs.json'

def fingerprint(skin,profile):
 """What the portrait folder is made from: this code (with player_osd and settings_page), Fuse's landscape files (except the two written here), its
 addon.xml and the owner's widget lists. Sizes and change times, so a start reads no file contents."""
 skin=Path(skin);h=hashlib.sha256(REVISION.encode())
 for code in (Path(__file__),Path(player_osd.__file__),Path(settings_page.__file__),*(Path(__file__).with_name(n) for n in ('profiles_rows.py','favourites_rows.py','choice_sheet.py')),Path(pages.__file__),Path(ios_tabs.__file__),Path(notice_page.__file__),Path(library_page.__file__),Path(transfers_page.__file__),Path(library_tools_page.__file__),Path(activity_skin.__file__),Path(rows_page.__file__),Path(__file__).with_name('status_ui.py'),Path(__file__).with_name('notifications_skin.py'),Path(__file__).with_name('airplay_flow.py')):h.update(code.read_bytes())
 def stamp(path):
  try:st=path.stat();h.update(('%s:%d:%d;'%(path.name,st.st_size,st.st_mtime_ns)).encode())
  except OSError:h.update(('%s:-;'%path.name).encode())
 for path in sorted((skin/'1080i').glob('*.xml')):
  if path.name not in OWN_1080I:stamp(path)
 stamp(skin/'addon.xml')
 for lists in sorted({name for _,lists,_,_ in HUBS.values() for name in lists}):stamp(Path(profile)/NODES.format(lists))
 h.update(str(len(list((skin/FOLDER).glob('*.xml'))) if (skin/FOLDER).is_dir() else '-').encode())
 return h.hexdigest()

def refresh_if_needed(skin,profile):
 """refresh() only when an input changed since the last start: rebuilding every portrait window (300 files parsed,
 textures drawn in Python) took the phone's CPU while Home was loading at every start."""
 marker=Path(profile)/INPUTS;now=fingerprint(skin,profile)
 try:
  if json.loads(marker.read_text())['inputs']==now:return []
 except (OSError,ValueError,KeyError,TypeError):pass
 changed=refresh(skin,profile)
 marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'inputs':fingerprint(skin,profile)})+'\n')
 return changed

def missing(skin):
 """True when the writable Fuse copy predates r11: setup never overwrites a copy that is already there,
 so a phone that ran an earlier build keeps a Fuse without the portrait folder or its resolution."""
 skin=Path(skin);addon=skin/'addon.xml'
 return not (skin/FOLDER).is_dir() or not addon.is_file() or 'folder="%s"'%FOLDER not in addon.read_text(encoding='utf-8')

def is_portrait(info):
 try:return int(info('System.ScreenHeight'))>int(info('System.ScreenWidth'))
 except ValueError:return None

def watch(info,invoke,wait,current_skin,fuse='skin.arctic.fuse.3',interval=0.5,settle=2,tick=None,busy=None):
 """Run the per-session ticks. Turning the phone no longer reloads the skin (that rebuilt Home and every row at
 each video start and stop): playback windows only exist in 1080i, menus are portrait, and Kodi r8 reloads a
 dialog opened in the other orientation from the matching folder."""
 while not wait(interval):
  if tick:tick()

def focused_item_publisher(info,visible,set_property):
 """Home and the hubs are not media windows, so Kodi's long-press menu cannot see their focused item:
 publish it (title, art, one detail line) as Window(Home).Property(Portrait.Item.*)."""
 last={}
 def tick():
  if visible('System.HasActiveModalDialog') or not visible('Window.IsActive(home) | Window.IsActive(1101) | Window.IsActive(1102)'):return
  item='Container.ListItem'
  # Performance pass: two cheap labels first; the six others only when the focused item changed (they were asked
  # every half second while Home was on screen, each one waiting for Kodi's GUI lock).
  key=(info('System.CurrentControlId'),info(item+'.Label'))
  if key==last.get('_key'):return
  last['_key']=key
  art=next((v for v in (info(item+'.Art(landscape)'),info(item+'.Art(fanart)'),info(item+'.Art(thumb)')) if v),'')
  sub=info(item+'.Property(subtitle)') or '  ·  '.join(v for v in (info(item+'.Year'),info(item+'.Genre')) if v)
  for key,value in (('Title',info(item+'.Label')),('Art',art),('Sub',sub)):
   if last.get(key)!=value:last[key]=value;set_property(key,value)
 return tick

def first_feed_publisher(info,log,clock,timeout=60,started=None):
 """Two startup-only milestones, measured from portrait-service entry. Counts mean list data is available, not
 that poster textures have been decoded/drawn. Stop polling once both arrive or after a minute; no titles/URLs."""
 started=clock() if started is None else started
 pending={'hero':4000,'first-row':5002};finished=False
 def tick():
  nonlocal finished
  if finished:return
  elapsed=clock()-started
  if elapsed>=timeout:
   log('Kodi iOS startup feed: pending %s after %.3fs (service clock)'%(','.join(pending),elapsed));finished=True;return
  for name,container in list(pending.items()):
   try:count=int(info('Container(%d).NumItems'%container) or 0)
   except (TypeError,ValueError,RuntimeError):continue
   if count>0:
    log('Kodi iOS startup feed: %s has %d items +%.3fs (service clock)'%(name,count,elapsed));del pending[name]
  finished=not pending
 return tick

def progress_tracker(player,continue_module,read,write,clock,every=10,external=lambda:{}):
 """Continue Watching: save the position of what the chooser started, and drop it once finished."""
 state={'playing':False,'saved':float('-inf'),'position':0,'total':0,'started':0,'seed':0,'remote':False,'handoff':False}
 def tick():
  try:
   try:remote=external() or {}
   except Exception:remote={}
   on_tv=bool(remote.get('active') and remote.get('state')==1 and remote.get('sample_age_s',0)<=15)
   if on_tv or player.isPlayingVideo():
    now=clock()
    if not state['playing']:
     state.update(playing=True,started=now,seed=0)
     try:
      data=continue_module.load(read);entry=data.get('items',{}).get(data.get('current')) or {}
      state.update(seed=float(entry.get('position') or 0),position=float(entry.get('position') or 0),total=float(entry.get('total') or 0))
     except (AttributeError,ValueError,TypeError):pass
    position,total=(remote.get('position',0),remote.get('duration',0)) if on_tv else (player.getTime(),player.getTotalTime())
    if state['remote'] and not on_tv:state.update(seed=state['position'],started=now,handoff=True)
    state['remote']=on_tv
    if state['handoff'] and not on_tv:
     if abs(position-state['seed'])>10 and now-state['started']<20:return
     state['handoff']=False
    # Opening/initial seek can briefly report zero. Do not erase a real resume point during that interval.
    if state['seed']>=10 and position<10 and now-state['started']<20:return
    state.update(position=position,total=total)
    if now-state['saved']>=every:continue_module.update(read,write,state['position'],state['total']);state['saved']=now
   elif state['playing']:
    state['playing']=False;continue_module.update(read,write,state['position'],state['total']);continue_module.stopped(read,write)
  except Exception as error:_quiet('portrait:1179',error)
 return tick

# Read by Kodi when the skin loads (fonts, includes, Home and the windows marked LOAD_ON_GUI_INIT in the owner's log):
# a change to one shows only after ReloadSkin. Every other window is read the first time it opens.
LOADED_AT_START={'Font.xml','Includes.xml','Includes_Portrait.xml','Home.xml','Custom_1187_Activity.xml','Startup.xml','Pointer.xml','DialogBusy.xml','DialogNotification.xml',
                 'DialogVolumeBar.xml','DialogExtendedProgressBar.xml','DialogSeekBar.xml','Custom_1151_OSD_MusicInfoOverlay.xml',
                 'Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml','Custom_1192_SeasonalTheme.xml',
                 'Custom_1194_Debug_Grid.xml','Custom_1198_Dialog_Startup.xml','Custom_1199_Debug_Overlay.xml'}
def needs_reload(changed,visible=lambda condition:False):
 """ReloadSkin (Home, its rows and the tab pages built again) only for a change Kodi already read: a file loaded with
 the skin, a texture, addon.xml, or the window on screen. A window not opened yet is read from the new file when it
 opens (one opened and closed again in the first seconds keeps its old layout until the next start)."""
 for path in changed:
  folder,_,name=path.rpartition('/')
  if folder not in (FOLDER,'1080i') or not name.endswith('.xml') or name in LOADED_AT_START:return True
  if visible('Window.IsVisible(%s)'%name):return True
 return False

REFRESH_AFTER=20    # seconds after the service starts before the first TMDb Helper run of the cache (past the start)
REFRESH_EVERY=600   # then a look for copies past ios_cache.MAX_AGE every ten minutes
FETCH_TIMEOUT=90    # seconds one Files.GetDirectory may take
def bounded(fetch,timeout=FETCH_TIMEOUT):
 """fetch(url) on its own thread, TimeoutError after timeout. Kodi's Files.GetDirectory never returns when the plugin
 exits without endOfDirectory (desktop rig: a TMDb Helper Trakt list answered 401 and the call hung for good)."""
 import threading
 def call(url):
  box={}
  def run():
   try:box['result']=fetch(url)
   except Exception as error:box['error']=error
  worker=threading.Thread(target=run,daemon=True);worker.start();worker.join(timeout)
  if worker.is_alive():raise TimeoutError('no answer in %d s'%timeout)
  if 'error' in box:raise box['error']
  return box.get('result')
 return call
def cache_lists(profile,spotlight,page=lambda tab:''):
 """({spotlight id: path}, [row paths]) the three hubs show, Home first (as hub_files and hub_body build them), each at
 the page its tab shows (page(tab): Skin.String(Portrait.Page.<tab>)); the copies' keys leave the page out."""
 spots={};rows=[]
 for name,(title,lists,tab,resume) in sorted(HUBS.items(),key=lambda h:HUB_TABS.index(h[1][2])):
  n=page(tab)
  spots[SPOTLIGHT[name]]=paged(spotlight(SPOTLIGHT[name]),n)
  rows+=[paged(w['path'],n) for w in load_widgets(profile,lists) if not in_progress(w)]
 return spots,rows

def tab_lists(profile,tab):
 """(cache keys, container ids) of one hub's TMDb Helper rows and hero: what refresh_rows turns live and waits for."""
 for name,(title,lists,hub_tab,resume) in HUBS.items():
  if hub_tab!=tab:continue
  widgets=[w for w in load_widgets(profile,lists) if not in_progress(w)]
  keys=['hero.'+str(SPOTLIGHT[name]).lower()]+[cache_key(w['path']) for w in widgets if str(w['path']).startswith(CACHEABLE)]
  # Row ids as hub_body numbers them: Continue Watching is 5001, the widgets follow; all shifted by the hub's offset.
  ids=[4000+HUB_OFFSET[tab]]+[5002+i+HUB_OFFSET[tab] for i,w in enumerate(widgets) if str(w['path']).startswith(CACHEABLE)]
  return keys,ids
 return [],[]

def listing_cache(cache,store,flags,lists,fetch,wait,busy,log,clock=None,after=None):
 """Background thread (run_service). At once: flags whose copy is gone go off, so those rows load TMDb Helper again.
 After REFRESH_AFTER: missing and stale copies are made one at a time (Files.GetDirectory from this service, never
 from the plugin), each row's flag going on once its copy reads back; never during video or outside Fuse."""
 import time
 clock=clock or time.time
 def pace(seconds):
  if seconds>0 and wait(seconds):return True   # Kodi's waitForAbort(0) waits for ever
  while busy():
   if wait(30):return True
  return False
 try:
  on,cleared=cache.check(lists(),store,flags,clock)
  log('%d rows and heroes served from copies, %d flags turned off (copy missing or unusable)'%(on,cleared))
  if pace(REFRESH_AFTER):return
  while True:
   current=lists()
   done,failed=cache.refresh(current,store,flags,fetch,pace,clock)
   cache.prune(store,current,clock)
   if done or failed:log('%d copies made or refreshed, %d failed%s'%(len(done),len(failed),(' ('+'; '.join(failed[:3])+')') if failed else ''))
   if after:   # roadmap 1C.4: the titles now on screen get their details fetched before anyone taps Play
    try:after(current)
    except Exception as error:log('details warm-up skipped: %r'%error)
   if pace(REFRESH_EVERY):return
 except Exception as error:
  # Rows keep whatever their flags say: good copies stay served, the others stay live.
  log('stopped: %r'%error)

def refresh_listing(skin,folder=None):
 """Read the portrait folder through Kodi once after writing it. Kodi answers "does this window file exist" from its
 directory cache when the folder was listed before (CFile::Exists -> g_directoryCache), so a page added while Kodi
 runs was "missing" until the next start (build 173: IOSTransfers.xml, "XML File for Window is missing"). A plain
 listing replaces the cached copy."""
 try:
  import xbmcvfs
  xbmcvfs.listdir(os.path.join(str(skin),folder or FOLDER)+'/')
 except Exception:pass

def refresh_skin(xbmc,invoke,skin,profile):
 """Bring the portrait folder up to date and reload the skin when a change needs it; returns the changed paths."""
 import time
 started=time.monotonic()
 if missing(skin):
  # Add the portrait folder and resolution, then have Kodi re-read addon.xml so the folder can be chosen.
  changed=list(build(skin,profile));invoke('UpdateLocalAddons')
  xbmc.log('Kodi iOS portrait layout added to the writable skin copy (%d files)'%len(changed),xbmc.LOGINFO)
 else:
  changed=refresh_if_needed(skin,profile)
  if add_resolutions(Path(skin)/'addon.xml'):
   # Kodi reads a skin's resolutions when it loads the skin add-on: the new label applies from the next start.
   invoke('UpdateLocalAddons');changed=list(changed)+['addon.xml']
   xbmc.log('Kodi iOS portrait resolution label updated (true 1080:2090 ratio); applies when Kodi next starts',xbmc.LOGINFO)
 # Fuse's start: no hub preloading (it opened each hub window in turn, the portrait hubs are one window) and no
 # wait-for-widgets loop (its script ran again every half second for up to a minute while rows loaded).
 for setting,on in (('Startup.EnableHubPreloading',False),('Startup.DisableWaitForLoad',True)):
  if bool(xbmc.getCondVisibility('Skin.HasSetting(%s)'%setting))!=on:invoke(('Skin.SetBool(%s)' if on else 'Skin.Reset(%s)')%setting)
 # Build 200: IOSAirPlayFlow.xml (1080i) was written after Kodi listed 1080i, so the Play on TV card was "missing" and
 # Kodi's plain dialogs showed instead. Re-list every folder a file was written to, not only portrait.
 for folder in sorted({c.split('/')[0] for c in changed if '/' in c} or ({FOLDER} if changed else set())):refresh_listing(skin,folder)
 reload=bool(changed) and needs_reload(changed,xbmc.getCondVisibility)
 listed=(' ('+', '.join(c for c in changed if not c.startswith('extras/'))[:300]+')') if changed else ''
 xbmc.log('Kodi iOS portrait files checked in %s: %d updated%s%s (%.3fs)'%(skin,len(changed),listed,
          '; skin reloaded' if reload else ('; no reload needed' if changed else ''),time.monotonic()-started),xbmc.LOGINFO)
 marker=Path(profile)/'addon_data/service.kodi.ios.bootstrap/portrait.json'
 if not marker.exists():
  # Once: no ".." rows, so a show page opens on its first season (the owner can turn it back on in Settings).
  xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.SetSettingValue','params':{'setting':'filelists.showparentdiritems','value':False}}))
  marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'revision':REVISION})+'\n')
 tune_cache(xbmc,profile)
 if reload and is_portrait(xbmc.getInfoLabel):invoke('ReloadSkin()')
 return changed

# Build 206 (owner, build 205: seeking an Umbrella episode "nearly broke the app ... I need fluid seeking"): Kodi read
# ahead 20 MB of a stream at up to 4x its bitrate; after a seek that refill is the wait. 96 MB (Kodi keeps about three
# times this in RAM) at up to 10x refills a seek far sooner. Set once, so the owner can still change them in Kodi.
CACHE={'filecache.memorysize':96,'filecache.readfactor':1000}
CACHE_MARKER='addon_data/service.kodi.ios.bootstrap/cache-206.json'
def tune_cache(xbmc,profile):
 marker=Path(profile)/CACHE_MARKER
 if marker.exists():return False
 for setting,value in CACHE.items():
  xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.SetSettingValue','params':{'setting':setting,'value':value}}))
 marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps(CACHE)+'\n')
 return True

def run_service(xbmc,xbmcvfs,monitor,profile,invoke,fuse='skin.arctic.fuse.3',ready=None,native_ui_started=False):
 """Started by the bootstrap service as soon as it starts. The tab bar, Continue Watching and the focused-item details
 start at once; the portrait refresh runs in its own thread once `ready` is set (after setup, which can rewrite Fuse's
 landscape files the portrait folder is made from). Build-132 started all of it only after setup and the refresh:
 the owner's tab bar appeared ~10 s after launch."""
 import threading,time
 entered=time.monotonic()
 xbmc.log('Kodi iOS startup: portrait service entered',xbmc.LOGINFO)
 if not native_ui_started:
  import native_ui
  threading.Thread(target=native_ui.run,args=(xbmc,xbmcvfs,monitor),daemon=True).start()
 def keep_current():
  if ready is not None:
   while not ready.wait(0.25):
    if monitor.abortRequested():return
  skin=Path(xbmcvfs.translatePath('special://skin/')).resolve()
  if skin.name!=fuse:
   xbmc.log('Kodi iOS portrait: the current skin is %s, not Arctic Fuse; layouts left alone'%skin,xbmc.LOGWARNING);return
  try:refresh_skin(xbmc,invoke,skin,profile)
  except Exception as error:
   import traceback
   xbmc.log('Kodi iOS portrait refresh failed: %s\n%s'%(error,traceback.format_exc()),xbmc.LOGERROR)
   xbmc.executebuiltin('Notification(Kodi iOS,Phone layouts did not update - send the log from the gear menu,8000)')
 threading.Thread(target=keep_current,daemon=True).start()
 tick=None
 try:
  import importlib.util,time,xbmcaddon
  lib=Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path')))/'resources/lib/ios_continue.py'
  spec=importlib.util.spec_from_file_location('ios_continue',lib);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  def read(path):
   f=xbmcvfs.File(path)
   try:return f.read()
   finally:f.close()
  def write(path,text):
   xbmcvfs.mkdirs(path.rsplit('/',1)[0]);f=xbmcvfs.File(path,'w')
   try:f.write(text)
   finally:f.close()
  import airplay
  try:native_player=airplay.cached_load(airplay.library_path(xbmcvfs.translatePath('special://xbmc/')))
  except Exception:native_player=None
  tick=progress_tracker(xbmc.Player(),module,read,write,time.monotonic,external=lambda:airplay.health(native_player))
 except Exception as error:xbmc.log('Kodi iOS continue watching unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 # Listing cache: check the row flags against the copies now, then fill and refresh copies in the background.
 try:
  import importlib.util,threading,xbmcaddon
  lib=Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path')))/'resources/lib/ios_cache.py'
  spec=importlib.util.spec_from_file_location('ios_cache',lib);cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
  def fetch(url):
   answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Files.GetDirectory',
                     'params':{'directory':url,'media':'video','properties':cache.PROPERTIES}})))
   if 'error' in answer:raise RuntimeError(str(answer['error'].get('message') or answer['error'])[:120])
   return answer.get('result')
  copies=cache.Store(xbmcvfs.translatePath(cache.FOLDER))
  def warm_details_after(current):
   # Roadmap 1C.4: TMDb Helper fetches the details of the hero titles and the Continue Watching history in the background.
   import details_warm
   hero=[(copies.load(key) or {}).get('items') for key,_ in current if key.startswith('hero.')]
   entries=[]
   try:entries=list(module.load(read)['items'].values())
   except Exception:pass
   details_warm.run(details_warm.collect(hero,entries),str(profile),lambda url:xbmc.executebuiltin('RunPlugin(%s)'%url),monitor.waitForAbort,
                    lambda:xbmc.getSkinDir()!=fuse or xbmc.getCondVisibility('Player.HasVideo'),log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
  threading.Thread(target=listing_cache,daemon=True,kwargs=dict(
   after=warm_details_after,cache=cache,store=copies,
   flags=cache.Flags(xbmc.getCondVisibility,xbmc.getInfoLabel,xbmc.executebuiltin),
   lists=lambda:cache.targets(*cache_lists(profile,lambda s:xbmc.getInfoLabel(spotlight_path(s)),lambda tab:xbmc.getInfoLabel(page_of(tab)))),fetch=bounded(fetch),
   wait=monitor.waitForAbort,busy=lambda:xbmc.getSkinDir()!=fuse or xbmc.getCondVisibility('Player.HasVideo'),
   log=lambda text:xbmc.log('Kodi iOS listing cache: '+text,xbmc.LOGINFO))).start()
 except Exception as error:import diagnostics;xbmc.log('Kodi iOS listing cache unavailable: %s'%diagnostics.error_text(error),xbmc.LOGWARNING)
 import xbmcgui
 home=xbmcgui.Window(10000)
 publish=focused_item_publisher(xbmc.getInfoLabel,xbmc.getCondVisibility,lambda k,v:home.setProperty('Portrait.Item.'+k,v))
 # During fullscreen video the menu-only work stops: each getInfoLabel / getCondVisibility waits for Kodi's GUI
 # lock, and the focused-item publisher asked up to ten of them every half second while the owner used the video
 # controls. The tab bar's tick stays (two size checks in landscape) so it hides as the video starts.
 video=lambda:xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)')
 always=[t for t in (tick,) if t]
 menu_ticks=[first_feed_publisher(xbmc.getInfoLabel,lambda text:xbmc.log(text,xbmc.LOGINFO),time.monotonic,started=entered),publish]
 def load_genre_photos():
  import threading
  store=os.path.join(str(profile),GENRE_PHOTOS)
  def read():
   try:
    with open(store,encoding='utf-8') as f:return f.read()
   except OSError:return ''
  def write(text):
   try:
    with open(store,'w',encoding='utf-8') as f:f.write(text)
   except OSError:pass
  def rpc(method,params):
   return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))).get('result')
  import time as clock
  busy=lambda:xbmc.getCondVisibility('!Window.IsActive(1105) | Player.HasVideo | System.HasActiveModalDialog | '
                                    '!String.IsEmpty(Window(Home).Property(Portrait.Search.Query)) | '
                                    '!String.IsEmpty(Window(Home).Property(Notices.Active))')
  threading.Thread(target=lambda:genre_photos(rpc,home.setProperty,read,write,clock.time,busy,monitor.waitForAbort),daemon=True).start()
 menu_ticks.append(genre_photos_tick(xbmc.getCondVisibility,load_genre_photos))
 def ticks():
  for t in always:t()
  if not video():
   for t in menu_ticks:t()
 watch(xbmc.getInfoLabel,invoke,monitor.waitForAbort,xbmc.getSkinDir,fuse,tick=ticks)

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc,diagnostics;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,diagnostics.error_text(error)),xbmc.LOGWARNING)
 except Exception:pass
