"""r11 portrait layout for Arctic Fuse 3 on iPhone: Netflix rows with an Apple TV app look.

Kodi picks the skin folder whose aspect is closest to the screen, so Fuse gets a `portrait` folder next to
`1080i`. Home, the TV/Movies/Downloads hubs, the show page (MyVideoNav), the info page, the select dialog
(the watch chooser) and the More menu are drawn for portrait. Every other window is the landscape Fuse
window shrunk into the middle of the portrait screen, so nothing becomes unreachable.

The same module builds the folder into the IPA (scripts/build_customized_ipa.py) and, on the phone,
refreshes the rows from the owner's widget lists and reloads the skin when the phone rotates.
"""
import hashlib,json,os,re,struct,zlib,xml.etree.ElementTree as ET
import importlib.util as _iu
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
      ('Favourites','star.png','FFFF9F0A','ActivateWindow(1160)'),
      ('File manager','clapperboard.png','FF5E5CE6','ActivateWindow(filemanager)'),
      ('iPhone navigation / recovery','life-ring.png','FFFF453A',MENU)]
HANDMADE=set(HUBS)|set(LIBRARY_FILES)|{'Includes_Portrait.xml',SEARCH_FILE,'Startup.xml','Custom_1198_Dialog_Startup.xml','DialogContextMenu.xml','Custom_1182_Dialog_Topmenu_Overlay.xml','MyVideoNav.xml','DialogVideoInfo.xml','DialogSelect.xml','Custom_1170_Dialog_Options.xml','Font.xml','Includes.xml','Settings.xml','SettingsCategory.xml','DialogAddonSettings.xml',activity_skin.NAME,activity_skin.BOX}|pages.HANDMADE
# Never shrunk: playback stays landscape, and these are not windows.
SKIP_WRAP={'VideoFullScreen.xml','VideoOSD.xml','MusicVisualisation.xml','SlideShow.xml','Pointer.xml'}
# Shown only over landscape playback: no portrait copy, so Kodi always loads them from 1080i with landscape
# coordinates (it picks a window's folder when it loads it, and these load while the phone is still upright).
VIDEO_ONLY={'DialogSeekBar.xml','DialogFullScreenInfo.xml','DialogSubtitles.xml','VideoOSDBookmarks.xml','DialogPVRChannelsOSD.xml',
            'GameOSD.xml','MusicOSD.xml','Custom_1140_OSD_Playlist.xml','Custom_1141_OSD_Cast.xml','Custom_1142_OSD_MusicTracks.xml',
            'Custom_1143_OSD_NextOverlay.xml','Custom_1145_OSD_InfoPanel.xml','Custom_1146_OSD_AudioStreams.xml',
            'Custom_1147_OSD_SubtitleStreams.xml','Custom_1148_OSD_VideoStreams.xml','Custom_1151_OSD_MusicInfoOverlay.xml',
            'Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml','Custom_1193_VideoOSDInfo.xml',
            'IOSPlayOnTV.xml'}   # pages.play_on_tv: Play on TV over video
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
 if math.hypot(u-12,v-12)<GEAR_HOLE:return False
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

def textures():
 return {'round.png':rounded(96,96,32),'round_s.png':rounded(64,64,26),'glass_card.png':glass(160,44,(44,44,46,245),(255,255,255,26)),
         'fade_down.png':fade(lambda t:(1-t)**1.6*0.85),'fade_up.png':fade(lambda t:t**1.5),
         'hero_fade.png':fade(lambda t:0 if t<0.3 else ((t-0.3)/0.7)**1.25),
         'poster_mask.png':rounded(POSTER[0],POSTER[1],RADIUS),'card_mask.png':rounded(CARD[0],CARD[1],RADIUS),
         'thumb_mask.png':rounded(400,225,20),'tile_mask.png':rounded(80,80,18),'dot.png':rounded(24,24,12),'knob.png':rounded(48,48,24),'clear48.png':png(4,48,lambda x,y:(0,0,0,0)),
         'white.png':png(4,4,lambda x,y:(255,255,255,255)),'play.png':triangle(64),'airplay.png':player_osd.airplay_png(png),'ring.png':ring(132,7),'ring_arc.png':arc(132,5,150),'hdr_gear.png':shape(96,gear_inside),'hdr_refresh.png':shape(96,refresh_inside),
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
def label(x,y,w,h,text,font,color=WHITE,align='left',extra=''):
 return ('<control type="label"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font>'
         '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><label>%s</label>%s</control>')%(x,y,w,h,font,color,align,e(text),extra)
def surface(x,y,w,h,texture,color=WHITE,border=0,extra=''):return image(x,y,w,h,MEDIA+texture,color,extra,border=border)

def pill_button(id,x,y,w,h,text,actions,style,glyph='',extra='',glyph_x=None):
 """Apple-style capsule: 'primary' white with black text, 'glass' frosted. actions: [(condition, action)]."""
 fill,tex,textcolor=(('FFFFFFFF','pill_%d.png'%h,'FF000000') if style=='primary' else ('FFFFFFFF','glass_%d.png'%h,'FFFFFFFF'))
 clicks=''.join('<onclick%s>%s</onclick>'%(' condition="%s"'%e(c) if c else '',e(a)) for c,a in actions)
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
HDR=108;HDR_GAP=24;HDR_GLYPH=52   # header buttons (owner-approved round 5, option A): 40 pt glass circles, 19 pt glyphs
def header_button(id,x,y,glyph,action,extra=''):
 """Glass header circle with a centred glyph (bell, gear, refresh); glyph is an icons/ name or a full path."""
 off=(HDR-HDR_GLYPH)//2
 return pill_button(id,x,y,HDR,HDR,'',[('',action)],'glass','',extra)[:-len('</control>')]+icon(off,off,HDR_GLYPH,glyph)+'</control>'
def bell(x,y,extra=''):
 """Bell: red count of unread messages, a thin blue arc turning around it while something runs
 (the bootstrap service keeps Notices.Unread and Notices.Active on the Home window)."""
 unread='Window(Home).Property(Notices.Unread)'
 return ('<control type="group"><left>%d</left><top>%d</top><width>108</width><height>108</height>'%(x,y)+
  image(-12,-12,132,132,MEDIA+'ring_arc.png',ACCENT,'<visible>!String.IsEmpty(Window(Home).Property(Notices.Active))</visible>'
   '<animation effect="rotate" end="-360" center="auto" time="1200" loop="true" reversible="false" condition="true">Conditional</animation>')+
  header_button(9207,0,0,'bell.png',NOTICES,extra)+
  '<control type="group"><left>66</left><top>-8</top><visible>!String.IsEmpty(%s) + !String.IsEqual(%s,0)</visible>'%(unread,unread)+
  image(0,0,56,56,MEDIA+'dot.png','FF000000')+image(4,4,48,48,MEDIA+'dot.png','FFFF453A')+
  label(4,4,48,48,'$INFO[%s]'%unread,'p_foot_b',WHITE,'center','<aligny>center</aligny>')+'</control></control>')

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

def poster_item(focused):
 w,h=POSTER
 zoom='<animation effect="zoom" start="100" end="104" time="160" center="auto" tween="cubic" easing="out">Focus</animation>' if focused else ''
 return ('<control type="group"><left>%d</left><top>14</top>%s'%(SIDE,zoom)+
  image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  label(20,h-170,w-40,150,'$INFO[ListItem.Label]','p_foot_b',WHITE,'left','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(poster))</visible>')+
  image(0,0,w,h,'$INFO[ListItem.Art(poster)]',WHITE,'','>scale',MEDIA+'poster_mask.png',background=True)+'</control>')

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

def cached_content(name,path,variables,spotlight=None):
 """Container content for a hub row (path) or hero (spotlight id): a variable in Includes.xml choosing the cached
 route when its flag is on, else the live path. Other rows (Continue Watching, library) keep their path as is."""
 if variables is None or (spotlight is None and not str(path).startswith(CACHEABLE)):return e(path)
 if spotlight is None:
  key=cache_key(path);on='Skin.HasSetting(%s%s)'%(CACHE_FLAG,key)
 else:
  # The flag holds the path the copy was made from: a spotlight changed in the skin settings goes live at once.
  key='hero.'+str(spotlight).lower();flag='Skin.String(%s%s)'%(CACHE_FLAG,key)
  on='!String.IsEmpty(%s) + String.IsEqual(%s,%s)'%(flag,flag,spotlight_path(spotlight))
 variables[name]='<variable name="%s"><value condition="%s + %s">%s</value><value>%s</value></variable>'%(
  name,e(on),WATCH_ON,e(CACHE_ROUTE+key),e(path))
 return '$VAR[%s]'%name

def row(index,widget,last,tab='home',variables=None):
 id=5001+index;title=str(widget.get('label') or '')
 style=widget.get('style') or ('poster' if str(widget.get('widget_style') or '').lower()=='poster' else 'card')
 w,h=(POSTER[0],POSTER[1]+40) if style=='poster' else (CARD[0],CARD[1]+180)
 # Hidden while empty; allowhiddenfocus keeps Kodi loading the row's content while it is hidden.
 visible='Integer.IsGreater(Container(%d).NumItems,0) | Container(%d).IsUpdating'%(id,id)
 item=poster_item if style=='poster' else (lambda f:card_item(f,style=='continue'))
 return (label(SIDE,0,WIDTH-2*SIDE,128,'%s  [COLOR %s]›[/COLOR]'%(title,GREY),'p_h2',WHITE,'left','<aligny>bottom</aligny><visible>%s</visible>'%visible).replace('<control type="label">','<control type="label" id="%d">'%(id+500),1)+
  ('<control type="list" id="%d"><left>0</left><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
   '%s<scrolltime tween="cubic" easing="out">320</scrolltime><preloaditems>2</preloaditems><visible allowhiddenfocus="true">%s</visible>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
   '<content target="%s">%s</content></control>'
   )%(id,WIDTH,h,'<ondown>9201</ondown>' if last else '',visible,w+GAP,h,item(False),w+GAP,h,item(True),
      e(widget.get('target') or 'videos'),cached_content('Portrait_Cache_Row_%s_%d'%(tab,index),widget['path'],variables)))

def hero(spotlight,title,tab='home',variables=None):
 """Full-bleed hero: the hub's spotlight titles (swipe sideways), logo, genre line, Play and Info, page dots."""
 info='Container(4000).ListItem'
 art=image(0,0,WIDTH,HERO,'$VAR[Portrait_Hero_Art]',WHITE,'','>scale',background=True)
 meta='$INFO[%s.Genre]$INFO[%s.Year,  ·  ]$INFO[%s.MPAA,  ·  ]'%(info,info,info)
 is_show='String.IsEqual(%s.DBType,tvshow)'%info
 # A show opens its page (seasons and episodes); a movie goes straight to "How would you like to watch?".
 play=[(is_show,'ActivateWindow(Videos,$ESCINFO[%s.FolderPath],return)'%info),('!'+is_show,'PlayMedia($ESCINFO[%s.FileNameAndPath])'%info)]
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
     cached_content('Portrait_Cache_Hero_%s'%tab,'$INFO[%s]'%spotlight_path(spotlight),variables,spotlight),
     image(0,0,WIDTH,HERO,MEDIA+'hero_fade.png'),image(0,0,WIDTH,420,MEDIA+'fade_down.png'),
     label(SIDE,40,header_width(tab),120,title,'p_large'),
     header_buttons(46,tab,'<ondown>4000</ondown>')+refreshed_toast(tab,title),
     HERO-560,WIDTH-240,info,
     label(SIDE,HERO-560,WIDTH-2*SIDE,250,'$INFO[%s.Label]'%info,'p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(%s.Art(clearlogo))</visible>'%info),
     label(SIDE,HERO-296,WIDTH-2*SIDE,56,meta,'p_foot',GREY,'center'),
     # Play and Info only once there is a title to play; until then a soft placeholder where the art will be.
     '<control type="group"><visible>Integer.IsGreater(Container(4000).NumItems,0)</visible>'+
     pill_button(4001,WIDTH//2-btn_w-12,HERO-214,btn_w,124,'Play',play,'primary',MEDIA+'play.png','<onup>4000</onup><onright>4002</onright><ondown>5001</ondown>')+
     pill_button(4002,WIDTH//2+12,HERO-214,btn_w,124,'Info',[('','SetFocus(4000)'),('','Action(Info)')],'glass','circle-info.png','<onup>4000</onup><onleft>4001</onleft><ondown>5001</ondown>')+'</control>'+
     '<control type="group"><visible>Integer.IsEqual(Container(4000).NumItems,0)</visible>'+
     surface(SIDE,220,WIDTH-2*SIDE,HERO-420,'round.png',SURFACE,32,'<animation effect="fade" start="100" end="45" time="900" pulse="true" condition="Container(4000).IsUpdating">Conditional</animation>')+
     label(SIDE,220,WIDTH-2*SIDE,HERO-420,'Loading…','p_sub',DIM,'center','<visible>Container(4000).IsUpdating</visible>')+'</control>',
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
 # Results: posters only (the title shows on a dark card when a result has no poster: people, some new titles).
 result=lambda focused:('<control type="group"><left>0</left><top>0</top>%s'%zoom(focused)+
  image(0,0,tile_w,tile_h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  '<control type="textbox"><left>24</left><top>24</top><width>%d</width><height>%d</height><font>p_body</font><textcolor>%s</textcolor><align>center</align><label>$INFO[ListItem.Label]</label></control>'%(tile_w-48,tile_h-48,GREY)+
  image(0,0,tile_w,tile_h,'$INFO[ListItem.Art(poster)]',WHITE,aspect='>scale',diffuse=MEDIA+'poster_mask.png',background=True)+'</control>')
 # Filter (owner): All / Movies / Shows, as Window(Home).Property(Portrait.Search.Type) ('' / movie / tv) for searchbar.py.
 kind='Window(Home).Property(Portrait.Search.Type)'
 pills=''
 for n,(text,value) in enumerate((('All',''),('Movies','movie'),('Shows','tv'))):
  on=('String.IsEmpty(%s)'%kind) if not value else 'String.IsEqual(%s,%s)'%(kind,value)
  act=('ClearProperty(Portrait.Search.Type,home)' if not value else 'SetProperty(Portrait.Search.Type,%s,home)'%value)
  x=SIDE+n*230
  pills+=('<control type="button" id="%d"><left>%d</left><top>0</top><width>210</width><height>96</height><label>%s</label>'
   '<font>p_sub</font><align>center</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor>'
   '<texturefocus border="48" colordiffuse="FF3A3A3C">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="FF1C1C1E">%spill_96.png</texturenofocus>'
   '<onclick>%s</onclick></control>'
   '<control type="image"><left>%d</left><top>0</top><width>210</width><height>96</height><texture border="48" colordiffuse="33FFFFFF">%spill_96.png</texture><visible>%s</visible></control>'
   )%(5210+n,x,text,MEDIA,MEDIA,e(act),x,MEDIA,e(on))
 top=SEARCH_BAND+30
 filters='<control type="group"><top>%d</top><visible>%s</visible>%s</control>'%(top,SEARCH_NATIVE,pills)
 top+=120
 results=(filters+'<control type="group"><visible>!String.IsEmpty(%s)</visible>'%SEARCH_PATH+
  label(SIDE,top,WIDTH-2*SIDE,70,'Results','p_h3',GREY)+
  ('<control type="panel" id="5200"><left>%d</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
   '<scrolltime tween="cubic" easing="out">300</scrolltime><preloaditems>2</preloaditems>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
   '<content target="videos">$INFO[%s]</content></control>'
   )%(left,top+90,WIDTH-left,tile_w+gap,tile_h+gap,result(False),tile_w+gap,tile_h+gap,result(True),SEARCH_PATH)+
  label(SIDE,top+90,WIDTH-2*SIDE,120,'No results','p_body',GREY,'center',
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
   play_visible,'Container.Content(episodes)','['+DOWNLOADED_SHOW+' | !System.HasAddon(plugin.video.elementum)] + Container.Content(seasons)','!'+DOWNLOADED_SHOW+' + Container.Content(seasons) + System.HasAddon(plugin.video.elementum)'),glyph_x=(WIDTH-2*SIDE)//2-230)
 header+='<control type="group"><width>%d</width><height>144</height><visible>%s</visible>%s</control>'%(WIDTH,play_visible,play_button)
 download_visible='Container.Content(seasons) + !'+DOWNLOADED_SHOW+' + System.HasAddon(plugin.video.elementum)'
 header+='<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>'%(WIDTH,DL_SHIFT,download_visible,
  pill_button(9003,SIDE,0,WIDTH-2*SIDE,DL_H,'Download  $INFO[Container(50).ListItem.Label]',[('',DOWNLOAD_SEASON)],'glass',ICONS+'download.png',
              '<visible>%s</visible><onup>9002</onup><ondown>50</ondown>'%download_visible,glyph_x=(WIDTH-2*SIDE)//2-300))
 header+='<control type="group"><width>%d</width><height>170</height><control type="textbox"><left>%d</left><top>0</top><width>%d</width><height>150</height><font>p_foot</font><textcolor>%s</textcolor><label>$VAR[Portrait_Show_Plot]</label><autoscroll>false</autoscroll></control></control>'%(WIDTH,SIDE,WIDTH-2*SIDE,GREY)
 return header

def episode_item(focused):
 thumb_w,thumb_h=400,225
 bg=surface(SIDE-18,4,WIDTH-2*SIDE+36,thumb_h+176,'round_s.png','14FFFFFF',26) if focused else ''
 return ('<control type="group"><visible>String.IsEqual(ListItem.DBType,episode)</visible>'+bg+image(SIDE,18,thumb_w,thumb_h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'thumb_mask.png')+
  image(SIDE,18,thumb_w,thumb_h,'$VAR[Portrait_Thumb]',WHITE,'','>scale',MEDIA+'thumb_mask.png',background=True)+
  image(SIDE+thumb_w//2-48,18+thumb_h//2-48,96,96,MEDIA+'glass_96.png')+icon(SIDE+thumb_w//2-18,18+thumb_h//2-20,40,MEDIA+'play.png')+
  label(SIDE+thumb_w+30,40,WIDTH-2*SIDE-thumb_w-30,110,'$INFO[ListItem.Episode,,. ]$INFO[ListItem.Title]','p_h3',WHITE,'left','<wrapmultiline>true</wrapmultiline>')+
  label(SIDE+thumb_w+30,154,WIDTH-2*SIDE-thumb_w-30,48,'$INFO[ListItem.Duration(mins),,m]$INFO[ListItem.Premiered,  ·  ]','p_cap',GREY)+
  label(SIDE,thumb_h+40,WIDTH-2*SIDE,56,'$INFO[ListItem.Plot]','p_cap',GREY,'left','<scroll>false</scroll>')+'</control>')

def video_nav(original):
 chip=lambda on:('<control type="group"><visible>String.IsEqual(ListItem.DBType,season)</visible>'+surface(0,8,250,96,'pill_96.png' if on else 'glass_96.png',WHITE,48)+
  label(0,8,250,96,'$INFO[ListItem.Label]','p_foot_b','FF000000' if on else WHITE,'center')+'</control>')
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
 body=('<controls>'+backdrop()+show_page+generic+grid()+image(0,0,WIDTH,90,MEDIA+'fade_down.png')+back+plain_title+refresh+'</controls>')
 return window(original,body,'50','<views>50,51,52,53</views>')

GRID='Container.Content(movies) | Container.Content(tvshows)'
def grid():
 """Movies and shows (Library, categories, search results): a three-column poster grid."""
 cols=3;gap=24;w=(WIDTH-2*SIDE-(cols-1)*gap)//cols;h=w*3//2;left=(WIDTH-cols*w-(cols-1)*gap)//2
 item=lambda focused:('<control type="group"><left>0</left><top>0</top>%s'%('<animation effect="zoom" start="100" end="104" time="160" center="auto">Focus</animation>' if focused else '')+
  image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'poster_mask.png')+
  label(20,h-170,w-40,150,'$INFO[ListItem.Label]','p_foot_b',WHITE,'left','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(poster))</visible>')+
  image(0,0,w,h,'$INFO[ListItem.Art(poster)]',WHITE,'','>scale',MEDIA+'poster_mask.png',background=True)+
  image(w-58,14,44,44,ICONS+'circle-check.png',GREEN,'<visible>ListItem.IsPlayed</visible>')+'</control>')
 return (label(SIDE,180,WIDTH-2*SIDE,110,'$VAR[Portrait_Page_Title]','p_title',WHITE,'left','<visible>%s</visible>'%GRID)+
  ('<control type="panel" id="53"><left>%d</left><top>320</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><onup>9001</onup>'
   '<scrolltime tween="cubic" easing="out">300</scrolltime><visible>%s</visible>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout></control>'
   )%(left,WIDTH-left,GRID,w+gap,h+gap,item(False),w+gap,h+gap,item(True)))

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
SHOW_VARS+='<variable name="Portrait_Show_Play_Label"><value condition="%s + Container.Content(seasons) + !String.IsEmpty(Container(50).ListItem.Property(KodiIOS.PlayLabel))">$INFO[Container(50).ListItem.Property(KodiIOS.PlayLabel)]</value><value condition="%s">$INFO[Container.Property(KodiIOS.PlayLabel)]</value><value>Play $INFO[Container(50).ListItem.Label]</value></variable>'%(DOWNLOADED_SHOW,DOWNLOADED_SHOW)

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
  '<control type="textbox" id="4"><left>%d</left><top>1150</top><width>%d</width><height>620</height><font>p_sub</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label></control>'%(SIDE,w,GREY)+
  label(SIDE,1790,w,48,'$INFO[ListItem.Director,Director: ]','p_cap',DIM)+
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
 """Kodi's select dialog, and so "How would you like to watch?": an iOS action sheet in the middle,
 sized to its rows. With the title's art (the watch chooser) the art leads the card."""
 x=96;w=WIDTH-2*x;row_h=132;cancel_h=128;gap=22
 titled='[!String.IsEmpty(Container(3).ListItem.Art(poster)) | !String.IsEmpty(Container(6).ListItem.Art(poster))]'
 count=lambda n,op='IsEqual':'[Integer.%s(Container(3).NumItems,%d) | Integer.%s(Container(6).NumItems,%d)]'%(op,n,op,n)
 head_plain,head_art=170,170+300
 # Card height for n rows (n<SELECT_ROWS; more rows scroll inside the full card).
 def card_h(n,head):return head+n*row_h
 full=card_h(SELECT_ROWS,head_art)+gap+cancel_h;top=(HEIGHT-full)//2
 heading=('<control type="image"><left>%d</left><top>36</top><width>420</width><height>236</height><texture diffuse="%sthumb_mask.png">$VAR[Portrait_Select_Art]</texture><aspectratio>scale</aspectratio><visible>%s</visible></control>'%((w-420)//2,MEDIA,titled)+
  '<control type="group"><visible>%s</visible>%s</control>'%(titled,label(40,290,w-80,150,'$INFO[Control.GetLabel(1)]','p_h3',WHITE,'center','<wrapmultiline>true</wrapmultiline>'))+
  '<control type="group"><visible>!%s</visible>%s</control>'%(titled,label(40,24,w-80,130,'$INFO[Control.GetLabel(1)]','p_h3',WHITE,'center','<wrapmultiline>true</wrapmultiline>'))+
  '<control type="label" id="1"><visible>false</visible></control>')
 icon_row='!String.IsEmpty(ListItem.Icon) + !String.StartsWith(ListItem.Icon,Default) + String.IsEmpty(ListItem.Art(poster))'
 item=lambda focused:(image(0,0,w,2,MEDIA+'white.png',SEP)+(image(0,2,w,row_h-2,MEDIA+'white.png','14FFFFFF') if focused else '')+
  icon(40,(row_h-72)//2,72,'$INFO[ListItem.Icon]',WHITE,'<visible>%s</visible>'%icon_row)+
  label(40,0,w-80,row_h,'$INFO[ListItem.Label]','p_sub',WHITE,'center','<wrapmultiline>true</wrapmultiline><scroll>false</scroll><visible>![%s]</visible>'%icon_row)+
  label(140,0,w-200,row_h,'$INFO[ListItem.Label]','p_body',WHITE,'left','<visible>%s</visible>'%icon_row)+
  icon(w-86,(row_h-40)//2,40,'check.png',GREEN,'<visible>ListItem.IsSelected</visible>'))
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
      pill_button(9050 if (n,head)==(1,head_art) else 0,0,0,w,cancel_h,'Cancel',[('','Close')],'glass','','<onup>3</onup>').replace('<control type="button" id="0">','<control type="button">')))
 slides=''.join('<animation effect="slide" end="0,%d" time="0" condition="%s + %s">Conditional</animation>'%((full-(card_h(n,head)+gap+cancel_h))//2,count(n),c)
               for n in range(1,SELECT_ROWS) for head,c in ((head_art,titled),(head_plain,'!'+titled)))
 hidden=''.join('<control type="button" id="%d"><visible>false</visible></control>'%i for i in (5,7,8))+'<control type="label" id="2"><visible>false</visible></control>'
 body='<left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s%s%s%s%s'%(x,top,w,full,slides,cards,heading,lists,hidden)
 return centered_dialog(original,body,'3')

def more_menu(original):
 """iOS Settings-style grouped list: coloured icon tiles, labels, chevrons."""
 x=70;w=WIDTH-2*x;row_h=140;h=170+len(MORE)*row_h+30;top=(HEIGHT-h)//2
 items=''.join('<item><label>%s</label><icon>%s</icon><property name="tint">%s</property><onclick>Dialog.Close(1170)</onclick><onclick>%s</onclick></item>'%(e(t),ICONS+i,c,e(a)) for t,i,c,a in MORE)
 item=lambda focused:((image(0,0,w,row_h,MEDIA+'white.png','14FFFFFF') if focused else '')+
  image(44,(row_h-80)//2,80,80,MEDIA+'tile_mask.png','$INFO[ListItem.Property(tint)]')+
  icon(44+18,(row_h-44)//2,44,'$INFO[ListItem.Icon]')+
  label(160,0,w-260,row_h,'$INFO[ListItem.Label]','p_body')+label(w-90,0,50,row_h,'›','p_h2',DIM,'right')+
  image(160,row_h-2,w-160,2,MEDIA+'white.png',SEP))
 lst=('<control type="list" id="3"><left>0</left><top>170</top><width>%d</width><height>%d</height><itemlayout height="%d">%s</itemlayout>'
      '<focusedlayout height="%d">%s</focusedlayout><content>%s</content></control>')%(w,len(MORE)*row_h,row_h,item(False),row_h,item(True),items)
 body=('<left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,top,w,h)+
  image(0,0,w,h,MEDIA+'glass_card.png',border=44)+label(44,40,w-88,100,'More','p_h2')+lst)
 return centered_dialog(original,body,'3')

CTX_ROWS=15
# Context menu entries -> icon (first match wins; Kodi's String.Contains ignores case).
CTX_ICONS=[('Resume','clock-rotate-left.png'),('Trailer','film.png'),('next','forward.png'),('unwatched','eye-slash.png'),
           ('watched','circle-check.png'),('Play','circle-play.png'),('Download','circle-down.png'),('Information','circle-info.png'),
           ('Info','circle-info.png'),('Show','tv.png'),('Season','tv.png'),('Queue','list.png'),('favourite','star.png'),
           ('Remove','circle-xmark.png'),('Delete','trash.png'),('Search','magnifying-glass.png'),('Share','share.png'),
           ('Manage','gear.png'),('Settings','gear.png'),('Browse','folder.png'),('Add','square-plus.png')]
ITEM='Window(Home).Property(Portrait.Item.%s)'
def ctx_variables():
 # Media windows give the dialog their ListItem; Home and the hubs do not, so the bootstrap service keeps a
 # copy of the focused row item in Portrait.Item.* (focused_item_publisher).
 own='!String.IsEmpty(ListItem.Label)'
 pick=lambda name,mine,theirs:'<variable name="%s"><value condition="%s">%s</value><value>%s</value></variable>'%(name,own,mine,theirs)
 return (pick('Portrait_Ctx_Title','$INFO[ListItem.Label]','$INFO[%s]'%(ITEM%'Title'))+
  pick('Portrait_Ctx_Art','$VAR[Portrait_Card_Art]','$INFO[%s]'%(ITEM%'Art'))+
  pick('Portrait_Ctx_Sub','$INFO[ListItem.Property(subtitle)]$INFO[ListItem.Year]$INFO[ListItem.Genre,  ·  ]','$INFO[%s]'%(ITEM%'Sub'))+''.join('<variable name="Portrait_Ctx_Icon_%d">%s<value>%sellipsis.png</value></variable>'%(i,''.join(
  '<value condition="String.Contains(Control.GetLabel(%d),%s)">%s%s</value>'%(1001+i,word,ICONS,name) for word,name in CTX_ICONS),ICONS) for i in range(CTX_ROWS)))

def context_menu(original):
 """Long press: the title as a card on top, then a frosted menu with an icon per entry (iOS context menu)."""
 x=60;card_w=WIDTH-2*x;pad=20;art_h=(card_w-2*pad)*9//16;card_h=pad+art_h+136;top=110;menu_w=780;row_h=120;cap=30
 menu_top=top+card_h+30
 no_art='String.IsEmpty(ListItem.Art(fanart)) + String.IsEmpty(ListItem.Art(landscape)) + String.IsEmpty(ListItem.Art(thumb)) + String.IsEmpty(Window(Home).Property(Portrait.Item.Art))'
 card=('<control type="group"><left>%d</left><top>%d</top><visible>![%s] + !Control.IsVisible(%d)</visible>'%(x,top,no_art,1001+(HEIGHT-(top+card_h+30)-60-2*cap)//row_h)+
  '<animation effect="zoom" start="94" end="100" center="auto" time="240" tween="back" easing="out">WindowOpen</animation>'+
  surface(0,0,card_w,card_h,'glass_card.png',WHITE,44)+
  image(pad,pad,card_w-2*pad,art_h,'$VAR[Portrait_Ctx_Art]',WHITE,'','>scale',MEDIA+'card_mask.png',background=True)+
  label(40,pad+art_h+16,card_w-80,46,'$VAR[Portrait_Ctx_Sub]','p_foot_b',GREY)+
  label(40,pad+art_h+60,card_w-80,66,'$VAR[Portrait_Ctx_Title]','p_h3')+'</control>')
 template=('<control type="button" id="1000"><width>%d</width><height>%d</height><font>p_body</font><textcolor>FFFFFFFF</textcolor>'
  '<focusedcolor>FFFFFFFF</focusedcolor><textoffsetx>128</textoffsetx><align>left</align><aligny>center</aligny>'
  '<texturefocus colordiffuse="FF3A3A3C">%swhite.png</texturefocus><texturenofocus colordiffuse="F22C2C2E">%swhite.png</texturenofocus></control>')%(menu_w,row_h,MEDIA,MEDIA)
 caps=lambda name:'<control type="image"><width>%d</width><height>%d</height><texture border="44,0,44,0" colordiffuse="F22C2C2E">%s%s</texture></control>'%(menu_w,cap,MEDIA,name)
 # Rows that fit under the card, and on the whole screen. A longer menu hides the card; one longer than the
 # screen scrolls, and its icons (a fixed layer beside the list) would no longer line up, so they hide.
 fit_card=(HEIGHT-menu_top-60-2*cap)//row_h;fit_screen=(HEIGHT-top-60-2*cap)//row_h
 long_menu='Control.IsVisible(%d)'%(1001+fit_card);scrolls='Control.IsVisible(%d)'%(1001+fit_screen)
 icons=''.join(icon(42,cap+i*row_h+(row_h-58)//2,58,'$VAR[Portrait_Ctx_Icon_%d]'%i,WHITE,'<visible>Control.IsVisible(%d) + !%s</visible>'%(1001+i,scrolls)) for i in range(CTX_ROWS))
 # No art (e.g. a menu button) or a long menu: the menu moves up to where the card would be.
 menu=('<control type="group"><left>%d</left><top>%d</top>'%(x,menu_top)+
  '<animation effect="slide" end="%d,%d" time="0" condition="[%s] | %s">Conditional</animation>'%((WIDTH-menu_w)//2-x,-(card_h+30),no_art,long_menu)+
  # Without the card (e.g. Resume / Play from beginning) the menu sits in the middle of the screen, as an iOS
  # alert does: one step per possible row count, since Kodi cannot measure the list.
  ''.join('<animation effect="slide" end="0,%d" time="0" condition="[[%s] | %s] + Control.IsVisible(%d) + !Control.IsVisible(%d)">Conditional</animation>'
          %((HEIGHT-(n*row_h+2*cap))//2-top,no_art,long_menu,1000+n,1001+n) for n in range(1,fit_screen+1) if (HEIGHT-(n*row_h+2*cap))//2>top)+
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>'+
  '<control type="grouplist" id="996"><width>%d</width><height>%d</height><orientation>vertical</orientation><itemgap>0</itemgap>%s%s%s</control>'
  %(menu_w,HEIGHT-top-60,caps('cap_top.png'),template,caps('cap_bottom.png'))+icons+'</control>')
 # No background control (999): Kodi would resize it to the menu and centre the dialog on the pressed item.
 # Without one the dialog is the full screen, so the card and menu stay where this layout puts them.
 body=('<controls><control type="image"><width>%d</width><height>%d</height><texture colordiffuse="99000000">%swhite.png</texture></control>'
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
 back=nav_button(32500,SIDE,36,'chevron-left.png','Close','<ondown>32503</ondown>')
 body='<controls>%s%s%s%s%s%s</controls>'%(backdrop(),head,heading,sub,lst,back)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">32503</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>%s</window>\n')%(MARKER,body)

NOTICE_SLOTS=4;NOTICE_ROWS=15
NOTICE_FILTERS=(('all','All'),('general','General'),('downloads','Downloads'),('problems','Problems'))   # buttons 9101-9104, notifications.FILTER_KEYS
def notices_page():
 """Notification center (owner-approved mockup): live downloads with progress bars, the Google Drive upload,
 then earlier messages. notifications.py fills it through window properties and the progress controls."""
 P=lambda name:'$INFO[Window().Property(%s)]'%name
 has=lambda name:'!String.IsEmpty(Window().Property(%s))'%name
 w=WIDTH-2*SIDE
 def section(text,cond,extra=''):
  return ('<control type="group"><width>%d</width><height>96</height><visible>%s</visible>'%(WIDTH,cond)+
   label(SIDE,30,w-260,60,text,'p_foot_b',GREY)+(label(SIDE+w-240,30,240,60,extra,'p_foot',GREY,'right') if extra else '')+'</control>')
 def card(n):
  h=350;pre='dl.%d.'%n   # Pause/Cancel are 124 high (46 pt): touch areas of at least 44 pt (APPLE-UI-POLICY 4.5)
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(WIDTH,h+24,has(pre+'title'))+
   surface(SIDE-6,0,w+12,h,'round.png',SURFACE,32)+
   # Owner: tapping a transfer card opens the Transfers page (speed graph); Pause/Cancel are drawn on top of this.
   '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus /></control>'%(9435+n,SIDE-6,w+12,h)+
   surface(SIDE+24,26,130,196,'round_s.png','FF3A3A3C',20)+icon(SIDE+59,94,60,'download.png',GREY,'<visible>!%s</visible>'%has(pre+'poster'))+
   image(SIDE+24,26,130,196,P(pre+'poster'),extra='<aspectratio>scale</aspectratio><visible>%s</visible>'%has(pre+'poster'))+
   label(SIDE+184,22,w-210,64,P(pre+'title'),'p_h3',WHITE,'left','<scroll>false</scroll>')+
   '<control type="progress" id="%d"><left>%d</left><top>110</top><width>%d</width><height>14</height>'
   '<texturebg border="7" colordiffuse="52787880">%sdot.png</texturebg><lefttexture /><midtexture border="7" colordiffuse="FF0A84FF">%sdot.png</midtexture><righttexture /></control>'%(9400+n,SIDE+184,w-210,MEDIA,MEDIA)+
   label(SIDE+184,136,w-210,48,P(pre+'line')+'$INFO[Window().Property(%sspeed),  ·  ,]'%pre,'p_cap',GREY)+
   pill_button(9410+n,SIDE+184,202,240,124,P(pre+'pausetext'),[('','noop')],'glass')+
   pill_button(9420+n,SIDE+184+260,202,240,124,'[COLOR FFFF453A]Cancel[/COLOR]',[('','noop')],'glass')+'</control>')
 def transfer(pre,progress_id,glyph,tint,tile):
  """Upload/preparation card: title, summary, bar, status. One label per line, each truncating (ISSUE-101)."""
  return ('<control type="group"><width>%d</width><height>244</height><visible>%s</visible>'%(WIDTH,has(pre+'title'))+
   surface(SIDE-6,0,w+12,220,'round.png',SURFACE,32)+
   '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>220</height><label></label><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>'%(progress_id+2,SIDE-6,w+12,MEDIA)+
   surface(SIDE+24,26,130,168,'round_s.png',tile,20)+icon(SIDE+59,80,60,glyph,tint,'<visible>![%s] + ![%s]</visible>'%(has(pre+'indeterminate'),has(pre+'poster')))+
   image(SIDE+59,80,60,60,MEDIA+'ring_06.png',tint,'<visible>%s</visible><animation effect="rotate" end="-360" center="auto" time="1100" loop="true" condition="true">Conditional</animation>'%has(pre+'indeterminate'))+
   image(SIDE+24,26,130,168,P(pre+'poster'),extra='<aspectratio>scale</aspectratio><visible>%s</visible>'%has(pre+'poster'))+
   label(SIDE+184,20,w-210,60,P(pre+'title'),'p_h3',WHITE,'left','<scroll>false</scroll>')+
   label(SIDE+184,80,w-210,46,P(pre+'summary'),'p_cap',GREY)+
   '<control type="progress" id="%d"><left>%d</left><top>134</top><width>%d</width><height>14</height>'
   '<texturebg border="7" colordiffuse="52787880">%sdot.png</texturebg><lefttexture /><midtexture border="7" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'%(progress_id,SIDE+184,w-210,MEDIA,tint,MEDIA)+
   label(SIDE+184,158,w-210,46,P(pre+'line'),'p_cap',GREY)+'</control>')
 def row(n):
  pre='msg.%d.'%n;h=170
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(WIDTH,h+14,has(pre+'title'))+
   surface(SIDE-6,0,w+12,h,'round_s.png',SURFACE,20)+
   '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus><texturenofocus /></control>'%(9500+n,SIDE-6,w+12,h,MEDIA)+
   image(SIDE+8,h//2-8,16,16,MEDIA+'dot.png','FF0A84FF','<visible>%s</visible>'%has(pre+'unread'))+
   surface(SIDE+36,30,86,86,'round_s.png',P(pre+'tint'),20)+icon(SIDE+56,50,46,ICONS+P(pre+'icon'),WHITE)+
   label(SIDE+150,22,w-300,58,P(pre+'title'),'p_foot_b',WHITE,'left','<scroll>false</scroll>')+
   label(SIDE+150,80,w-190,70,P(pre+'text'),'p_cap',GREY,'left','<wrapmultiline>true</wrapmultiline>')+
   label(SIDE+w-140,22,120,58,P(pre+'ago'),'p_cap',GREY,'right')+'</control>')
 filters=''.join('<control type="group"><left>%d</left><top>0</top>'%(i*w//len(NOTICE_FILTERS))+
   image(4,4,w//len(NOTICE_FILTERS)-8,80,MEDIA+'pill_96.png','FF636366','<visible>String.IsEqual(Window().Property(filter),%s)</visible>'%key,border=40)+
   '<control type="button" id="%d"><top>-15</top><width>%d</width><height>118</height><label>%s</label><font>p_foot_b</font><textoffsetx>0</textoffsetx><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
   '<align>center</align><aligny>center</aligny><texturefocus /><texturenofocus /></control></control>'%(9101+i,w//len(NOTICE_FILTERS),text,GREY,WHITE)
   for i,(key,text) in enumerate(NOTICE_FILTERS))
 body=('<controls>'+backdrop()+
  nav_button(9001,SIDE,36,'chevron-left.png','Close','<ondown>9101</ondown>')+
  '<control type="button" id="9002"><left>%d</left><top>31</top><width>260</width><height>118</height><label>Clear All</label><font>p_body</font>'
  '<textcolor>%s</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>right</align><aligny>center</aligny><texturefocus /><texturenofocus /></control>'%(WIDTH-SIDE-260,ACCENT)+
  label(SIDE,160,w,110,'Notifications','p_large')+
  '<control type="group"><left>%d</left><top>290</top>'%SIDE+surface(0,0,w,88,'pill_96.png',SURFACE,44)+filters+'</control>'+
  '<control type="grouplist" id="9300"><left>0</left><top>400</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%WIDTH+
  section('Downloading',has('has.dl'),P('dl.summary'))+''.join(card(n) for n in range(1,NOTICE_SLOTS+1))+
  section('Uploading to Google Drive',has('has.up'))+transfer('up.',9430,'cloud-arrow-up.png',GREEN,'FF1F3D2B')+
  section('Preparing for Kodi and AirPlay',has('has.prepare'))+
  transfer('prepare.',9431,'cloud-arrow-up.png',GREEN,'FF1F3D2B')+
  section('Earlier',has('has.msg'))+''.join(row(n) for n in range(1,NOTICE_ROWS+1))+
  '<control type="group"><width>%d</width><height>300</height><visible>%s</visible>'%(WIDTH,has('empty'))+
  label(SIDE,80,w,80,"You're all caught up",'p_h3',GREY,'center')+'</control>'+
  '<control type="image"><height>200</height><texture /></control></control></controls>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9101</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>%s</window>\n')%(MARKER,body)

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
 return VARIABLES+SHOW_VARS+ctx_variables()+rows

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
 for rel in list(files):
  if rel.startswith(FOLDER+'/'):files[rel]=activity_skin.inject(ns,rel[len(FOLDER)+1:],files[rel])
 # Fullscreen video is landscape: the Apple TV-style controls go into the landscape folder.
 files['1080i/VideoOSD.xml']=player_osd.window().encode()
 # Fuse's seek bar flashed up at every video start (buffering, the resume jump): ours shows only while seeking.
 if (source/'DialogSeekBar.xml').exists():files['1080i/DialogSeekBar.xml']=player_osd.seekbar_window().encode()
 return files

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
OWN_1080I={'VideoOSD.xml','DialogSeekBar.xml','IOSPlayOnTV.xml','IOSAirPlayCheck.xml','Includes.xml','Includes_Portrait.xml','Custom_1187_Activity.xml','DialogExtendedProgressBar.xml'}   # + activity_skin.py
INPUTS='addon_data/service.kodi.ios.bootstrap/portrait-inputs.json'

def fingerprint(skin,profile):
 """What the portrait folder is made from: this code (with player_osd and settings_page), Fuse's landscape files (except the two written here), its
 addon.xml and the owner's widget lists. Sizes and change times, so a start reads no file contents."""
 skin=Path(skin);h=hashlib.sha256(REVISION.encode())
 for code in (Path(__file__),Path(player_osd.__file__),Path(settings_page.__file__),Path(pages.__file__),Path(ios_tabs.__file__),Path(notice_page.__file__),Path(library_page.__file__),Path(transfers_page.__file__),Path(library_tools_page.__file__)):h.update(code.read_bytes())
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

def progress_tracker(player,continue_module,read,write,clock,every=10):
 """Continue Watching: save the position of what the chooser started, and drop it once finished."""
 state={'playing':False,'saved':float('-inf'),'position':0,'total':0}
 def tick():
  try:
   if player.isPlayingVideo():
    state.update(playing=True,position=player.getTime(),total=player.getTotalTime())
    if clock()-state['saved']>=every:continue_module.update(read,write,state['position'],state['total']);state['saved']=clock()
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
def cache_lists(profile,spotlight):
 """({spotlight id: path}, [row paths]) the three hubs show, Home first (as hub_files and hub_body build them)."""
 spots={};rows=[]
 for name,(title,lists,tab,resume) in sorted(HUBS.items(),key=lambda h:HUB_TABS.index(h[1][2])):
  spots[SPOTLIGHT[name]]=spotlight(SPOTLIGHT[name])
  rows+=[w['path'] for w in load_widgets(profile,lists) if not in_progress(w)]
 return spots,rows

def listing_cache(cache,store,flags,lists,fetch,wait,busy,log,clock=None):
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
 if changed:refresh_listing(skin)
 reload=bool(changed) and needs_reload(changed,xbmc.getCondVisibility)
 listed=(' ('+', '.join(c for c in changed if not c.startswith('extras/'))[:300]+')') if changed else ''
 xbmc.log('Kodi iOS portrait files checked in %s: %d updated%s%s (%.3fs)'%(skin,len(changed),listed,
          '; skin reloaded' if reload else ('; no reload needed' if changed else ''),time.monotonic()-started),xbmc.LOGINFO)
 marker=Path(profile)/'addon_data/service.kodi.ios.bootstrap/portrait.json'
 if not marker.exists():
  # Once: no ".." rows, so a show page opens on its first season (the owner can turn it back on in Settings).
  xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.SetSettingValue','params':{'setting':'filelists.showparentdiritems','value':False}}))
  marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'revision':REVISION})+'\n')
 if reload and is_portrait(xbmc.getInfoLabel):invoke('ReloadSkin()')
 return changed

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
  tick=progress_tracker(xbmc.Player(),module,read,write,time.monotonic)
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
  threading.Thread(target=listing_cache,daemon=True,kwargs=dict(
   cache=cache,store=cache.Store(xbmcvfs.translatePath(cache.FOLDER)),
   flags=cache.Flags(xbmc.getCondVisibility,xbmc.getInfoLabel,xbmc.executebuiltin),
   lists=lambda:cache.targets(*cache_lists(profile,lambda s:xbmc.getInfoLabel(spotlight_path(s)))),fetch=bounded(fetch),
   wait=monitor.waitForAbort,busy=lambda:xbmc.getSkinDir()!=fuse or xbmc.getCondVisibility('Player.HasVideo'),
   log=lambda text:xbmc.log('Kodi iOS listing cache: '+text,xbmc.LOGINFO))).start()
 except Exception as error:xbmc.log('Kodi iOS listing cache unavailable: %s'%error,xbmc.LOGWARNING)
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
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass
