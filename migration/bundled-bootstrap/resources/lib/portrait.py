"""r11 portrait layout for Arctic Fuse 3 on iPhone: Netflix rows with an Apple TV app look.

Kodi picks the skin folder whose aspect is closest to the screen, so Fuse gets a `portrait` folder next to
`1080i`. Home, the TV/Movies/Downloads hubs, the show page (MyVideoNav), the info page, the select dialog
(the watch chooser) and the More menu are drawn for portrait. Every other window is the landscape Fuse
window shrunk into the middle of the portrait screen, so nothing becomes unreachable.

The same module builds the folder into the IPA (scripts/build_customized_ipa.py) and, on the phone,
refreshes the rows from the owner's widget lists and reloads the skin when the phone rotates.
"""
import json,os,re,struct,zlib,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

REVISION='ios-portrait-r2'
FOLDER='portrait'
# iPhone 16 Pro portrait: 402x874 pt with 62/34 pt safe-area insets. Kodi stretches the skin canvas into
# the safe area, so 1080 x 2090 keeps pixels square there (1 pt = 2.687 units). 9:16 covers home-button phones.
WIDTH,HEIGHT=1080,2090
RES=[('9:19.5',WIDTH,HEIGHT),('9:16',WIDTH,1920)]
MARKER='Kodi-iOS portrait '+REVISION
NODES='addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-{}.json'
ICONS='special://skin/extras/icons/'
MEDIA='special://skin/extras/portrait/'
DRIVE='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
MENU='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)'
UPDATES='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/check_updates.py)'
# iOS dark palette: system background, grouped surfaces, secondary/tertiary labels.
BG='FF000000';SURFACE='FF1C1C1E';SURFACE2='FF2C2C2E';WHITE='FFFFFFFF'
GREY='99EBEBF5';DIM='4DEBEBF5';SEP='33EBEBF5';GREEN='FF30D158'
# window file -> (title, widget lists, tab)
HUBS={'Home.xml':('Home',['homewidgets'],'home'),
      'Custom_1101_Hub.xml':('TV Shows',['1101widgets'],'tv'),
      'Custom_1102_Hub.xml':('Movies',['1102widgets'],'movies'),
      'Custom_1103_Hub.xml':('Downloads',['1103widgets','1104widgets'],'downloads'),
      'Custom_1104_Hub.xml':('Downloads',['1104widgets','1103widgets'],'downloads')}
SPOTLIGHT={'Home.xml':'home','Custom_1101_Hub.xml':'1101','Custom_1102_Hub.xml':'1102','Custom_1103_Hub.xml':'1103','Custom_1104_Hub.xml':'1104'}
TABS=[('home','Home','house.png','ReplaceWindow(Home)'),('tv','TV Shows','tv.png','ReplaceWindow(1101)'),
      ('movies','Movies','film.png','ReplaceWindow(1102)'),('downloads','Downloads','download.png','ReplaceWindow(1103)')]
SEARCH='ReplaceWindow(1105)'
# More (the profile button): iOS Settings-style rows with coloured icon tiles.
MORE=[('Settings','gear.png','FF8E8E93','ActivateWindow(settings)'),
      ('Google Drive','cloud.png','FF0A84FF',DRIVE),
      ('Check for updates','cloud-arrow-down.png','FF30D158',UPDATES),
      ('Favourites','star.png','FFFF9F0A','ActivateWindow(1160)'),
      ('File manager','clapperboard.png','FF5E5CE6','ActivateWindow(filemanager)'),
      ('iPhone navigation / recovery','life-ring.png','FFFF453A',MENU)]
HANDMADE=set(HUBS)|{'Custom_1182_Dialog_Topmenu_Overlay.xml','MyVideoNav.xml','DialogVideoInfo.xml','DialogSelect.xml','Custom_1170_Dialog_Options.xml','Font.xml','Includes.xml'}
# Never shrunk: playback stays landscape, and these are not windows.
SKIP_WRAP={'VideoFullScreen.xml','VideoOSD.xml','MusicVisualisation.xml','SlideShow.xml','Pointer.xml'}
# iOS text styles at 2.687 units/pt (large title 34pt, title2 22pt, headline/body 17pt, subhead 15pt, footnote 13pt...).
FONTS=[('p_large','Inter-Bold.ttf',92),('p_title','Inter-Bold.ttf',78),('p_h2','Inter-Bold.ttf',58),
       ('p_h3','Inter-Bold.ttf',46),('p_body','Inter-Regular.ttf',44),('p_sub','Inter-Regular.ttf',40),
       ('p_foot','Inter-Regular.ttf',35),('p_foot_b','Inter-Bold.ttf',35),('p_cap','Inter-Regular.ttf',30),
       ('p_tab','Inter-Bold.ttf',27),('p_btn','Inter-Bold.ttf',46)]
SIDE=54                      # 20 pt margins
POSTER=(300,450);CARD=(640,360);GAP=26;RADIUS=26
HERO=1420
CAPSULES=(96,108,124,128,130,150)

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

def textures():
 return {'round.png':rounded(96,96,32),'round_s.png':rounded(64,64,26),'glass_card.png':glass(160,44,(44,44,46,245),(255,255,255,26)),
         'fade_down.png':fade(lambda t:(1-t)**1.6*0.85),'fade_up.png':fade(lambda t:t**1.5),
         'hero_fade.png':fade(lambda t:0 if t<0.3 else ((t-0.3)/0.7)**1.25),
         'poster_mask.png':rounded(POSTER[0],POSTER[1],RADIUS),'card_mask.png':rounded(CARD[0],CARD[1],RADIUS),
         'thumb_mask.png':rounded(400,225,20),'tile_mask.png':rounded(80,80,18),'dot.png':rounded(24,24,12),
         'white.png':png(4,4,lambda x,y:(255,255,255,255)),'play.png':triangle(64),
         # Capsules per height: 9-slice borders of h/2 keep the ends perfectly round at any width.
         **{'pill_%d.png'%h:rounded(h,h,h/2) for h in CAPSULES},
         **{'glass_%d.png'%h:glass(h,h/2,(30,30,34,232),(255,255,255,50)) for h in CAPSULES}}

# --- XML helpers ---------------------------------------------------------------------------------------
def e(text):return escape(str(text),{'"':'&quot;'})
def image(x,y,w,h,texture,color=WHITE,extra='',aspect='',diffuse='',border='',background=False):
 return ('<control type="image"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s'
         '<texture%s%s%s colordiffuse="%s">%s</texture>%s</control>')%(
  x,y,w,h,('<aspectratio%s</aspectratio>'%aspect) if aspect else '',
  ' background="true"' if background else '',' diffuse="%s"'%diffuse if diffuse else '',' border="%s"'%border if border else '',color,texture,extra)
def icon(x,y,size,name,color=WHITE,extra=''):return image(x,y,size,size,name if '://' in name else ICONS+name,color,extra,'>keep')
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
 return '<control type="group"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s%s</control>'%(x,y,w,h,inner,glyphxml)

def circle_button(id,x,y,size,glyph,action,extra=''):return pill_button(id,x,y,size,size,'',[('',action)],'glass',glyph,extra)

def window(original,body,default,extra_root=''):
 """Keep the landscape window's type/id and its onload helpers (Fuse init, the bootstrap's setup lock)."""
 root=ET.fromstring(original) if original else ET.Element('window')
 attrs=''.join(' %s="%s"'%(k,e(v)) for k,v in root.attrib.items())
 keep=''.join(ET.tostring(node,encoding='unicode') for node in root if node.tag in ('onload','onunload','include','param','zorder','depth','menucontrol','views','animation') and not (node.tag=='include' and 'View_' in (node.text or '')))
 return '<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window%s><defaultcontrol always="true">%s</defaultcontrol>%s%s%s</window>\n'%(MARKER,attrs,default,keep,extra_root,body)

def backdrop():return image(0,0,WIDTH,HEIGHT,MEDIA+'white.png',BG)

# --- hubs: hero, rows, tab bar --------------------------------------------------------------------------
def tabbar(active):
 """Floating frosted capsule with the four sections, and a separate search circle (iOS 26 tab bar)."""
 tab_w=196;pad=10;bar_w=pad*2+tab_w*len(TABS);h=150;items=[]
 for i,(key,text,glyph,action) in enumerate(TABS):
  on=key==active;color=WHITE if on else 'B3FFFFFF';x=pad+i*tab_w
  items.append(('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
   '<texturefocus border="65" colordiffuse="%s">%spill_130.png</texturefocus><texturenofocus border="65" colordiffuse="%s">%spill_130.png</texturenofocus>'
   '<label></label><onclick>%s</onclick><onup>5000</onup><onleft>%d</onleft><onright>%d</onright></control>'
   )%(9201+i,x,pad,tab_w,h-2*pad,'40FFFFFF' if on else '1AFFFFFF','%s',('2EFFFFFF' if on else '00FFFFFF'),'%s',e(action),9201+(i-1)%len(TABS),9201+(i+1)%(len(TABS)+1))%(MEDIA,MEDIA)
   +icon(x+(tab_w-54)//2,26,54,glyph,color)+label(x,84,tab_w,40,text,'p_tab',color,'center'))
 return ('<control type="image"><left>0</left><bottom>0</bottom><width>%d</width><height>330</height><texture>%sfade_up.png</texture></control>'
  '<control type="group" id="9200"><description>%s tab bar</description><left>%d</left><bottom>24</bottom><width>%d</width><height>%d</height>'
  '<control type="image"><width>%d</width><height>%d</height><texture border="75">%sglass_150.png</texture></control>%s</control>'
  '<control type="group"><right>%d</right><bottom>24</bottom><width>%d</width><height>%d</height>%s</control>'
  )%(WIDTH,MEDIA,MARKER,SIDE-14,bar_w,h,bar_w,h,MEDIA,''.join(items),SIDE-14,h,h,
     circle_button(9205,0,0,h,'magnifying-glass.png',SEARCH,'<onleft>%d</onleft><onup>5000</onup>'%(9200+len(TABS))))

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
  try:data=json.loads(path.read_text())
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

def card_item(focused):
 """16:9 'Up Next' card with title and genre underneath (Apple TV app)."""
 w,h=CARD
 zoom='<animation effect="zoom" start="100" end="103" time="160" center="auto" tween="cubic" easing="out">Focus</animation>' if focused else ''
 return ('<control type="group"><left>%d</left><top>14</top>%s'%(SIDE,zoom)+
  image(0,0,w,h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'card_mask.png')+
  image(0,0,w,h,'$VAR[Portrait_Card_Art]',WHITE,'','>scale',MEDIA+'card_mask.png',background=True)+
  label(0,h+14,w,50,'$INFO[ListItem.Label]','p_foot_b')+
  label(0,h+62,w,44,'$INFO[ListItem.Genre]$INFO[ListItem.Year,  ·  ]','p_cap',GREY)+'</control>')

def row(index,widget,last):
 id=5001+index;title=str(widget.get('label') or '')
 poster=str(widget.get('widget_style') or '').lower()=='poster'
 w,h=(POSTER[0],POSTER[1]+40) if poster else (CARD[0],CARD[1]+150)
 # Hidden while empty; allowhiddenfocus keeps Kodi loading the row's content while it is hidden.
 visible='Integer.IsGreater(Container(%d).NumItems,0) | Container(%d).IsUpdating'%(id,id)
 item=poster_item if poster else card_item
 return (label(SIDE,0,WIDTH-2*SIDE,128,'%s  [COLOR %s]›[/COLOR]'%(title,GREY),'p_h2',WHITE,'left','<aligny>bottom</aligny><visible>%s</visible>'%visible).replace('<control type="label">','<control type="label" id="%d">'%(id+500),1)+
  ('<control type="list" id="%d"><left>0</left><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
   '%s<scrolltime tween="cubic" easing="out">320</scrolltime><preloaditems>2</preloaditems><visible allowhiddenfocus="true">%s</visible>'
   '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
   '<content target="%s">%s</content></control>'
   )%(id,WIDTH,h,'<ondown>9201</ondown>' if last else '',visible,w+GAP,h,item(False),w+GAP,h,item(True),
      e(widget.get('target') or 'videos'),e(widget['path'])))

def hero(spotlight,title):
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
  '<scrolltime tween="cubic" easing="out">450</scrolltime><ondown>4001</ondown>'
  '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
  '<content target="videos" limit="8">$INFO[Skin.String(HomeSwitcher.%s.Spotlight.Path)]</content></control>'
  '%s%s'                                        # fades
  '%s%s'                                        # large title + profile
  '<control type="image"><left>120</left><top>%d</top><width>%d</width><height>250</height><aspectratio aligny="bottom">keep</aspectratio><texture>$INFO[%s.Art(clearlogo)]</texture></control>'
  '%s%s%s%s'
  '<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>20</height><orientation>horizontal</orientation><align>center</align><itemgap>0</itemgap>%s</control>'
  '</control>'
  )%(WIDTH,HERO,WIDTH,HERO,WIDTH,HERO,art,WIDTH,HERO,art,spotlight,
     image(0,0,WIDTH,HERO,MEDIA+'hero_fade.png'),image(0,0,WIDTH,420,MEDIA+'fade_down.png'),
     label(SIDE,40,WIDTH-2*SIDE-140,120,title,'p_large'),
     circle_button(9206,WIDTH-SIDE-108,46,108,'circle-user.png','ActivateWindow(1170)','<ondown>4000</ondown>'),
     HERO-560,WIDTH-240,info,
     label(SIDE,HERO-560,WIDTH-2*SIDE,250,'$INFO[%s.Label]'%info,'p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(%s.Art(clearlogo))</visible>'%info),
     label(SIDE,HERO-296,WIDTH-2*SIDE,56,meta,'p_foot',GREY,'center'),
     pill_button(4001,WIDTH//2-btn_w-12,HERO-214,btn_w,124,'Play',play,'primary',MEDIA+'play.png','<onup>4000</onup><onright>4002</onright><ondown>5001</ondown>'),
     pill_button(4002,WIDTH//2+12,HERO-214,btn_w,124,'Info',[('','SetFocus(4000)'),('','Action(Info)')],'glass','circle-info.png','<onup>4000</onup><onleft>4001</onleft><ondown>5001</ondown>'),
     HERO-62,WIDTH,dots)

def hub_window(original,title,widgets,tab,spotlight):
 rows=''.join(row(i,w,i==len(widgets)-1) for i,w in enumerate(widgets)) or label(SIDE,0,WIDTH-2*SIDE,200,'Nothing here yet','p_body',GREY)
 body=('<controls>%s'
  '<control type="grouplist" id="5000"><top>0</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><scrolltime tween="cubic" easing="out">380</scrolltime><usecontrolcoords>true</usecontrolcoords>%s%s'
  '<control type="image"><height>360</height><texture /></control></control>'
  '%s%s</controls>'
  )%(backdrop(),WIDTH,HEIGHT,hero(spotlight,title),rows,image(0,0,WIDTH,90,MEDIA+'fade_down.png'),tabbar(tab))
 return window(original,body,'4000')

VARIABLES=('<variable name="Portrait_Hero_Art"><value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value>'
           '<value>$INFO[ListItem.Art(poster)]</value></variable>'
           '<variable name="Portrait_Card_Art"><value condition="!String.IsEmpty(ListItem.Art(landscape))">$INFO[ListItem.Art(landscape)]</value>'
           '<value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value><value>$INFO[ListItem.Art(thumb)]</value></variable>')

# --- show page (seasons as chips, episodes below), episode lists and plain folders ------------------------
def show_header(ids_down):
 """Art, logo/title, meta, 'Play' and plot for a show's seasons or episodes page."""
 art_h=840
 logo='$INFO[ListItem.Art(tvshow.clearlogo)]'
 play=('PlayMedia($ESCINFO[Container(60).ListItemAbsolute(0).FileNameAndPath])')
 return ('<control type="group"><visible>Container.Content(seasons) | Container.Content(episodes)</visible>'+
  image(0,0,WIDTH,art_h,'$VAR[Portrait_Show_Art]',WHITE,'','>scale',background=True)+
  image(0,0,WIDTH,art_h,MEDIA+'hero_fade.png')+image(0,0,WIDTH,300,MEDIA+'fade_down.png')+
  '<control type="image"><left>140</left><top>430</top><width>800</width><height>230</height><aspectratio aligny="bottom">keep</aspectratio><texture>%s</texture></control>'%logo+
  label(SIDE,430,WIDTH-2*SIDE,230,'$VAR[Portrait_Show_Title]','p_title',WHITE,'center','<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(tvshow.clearlogo))</visible>')+
  label(SIDE,672,WIDTH-2*SIDE,52,'[COLOR %s]$INFO[ListItem.Rating,★ ]  [/COLOR]$INFO[ListItem.Year]$INFO[ListItem.Genre,  ·  ]'%GREEN,'p_foot',GREY,'center')+
  pill_button(9002,SIDE,744,WIDTH-2*SIDE,124,'Play  $INFO[Container(50).ListItem.Label]',[('','%s'%play)],'primary',MEDIA+'play.png',
              '<visible>Container.Content(seasons)</visible><onup>9001</onup><ondown>50</ondown>',glyph_x=(WIDTH-2*SIDE)//2-200)+
  '<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>150</height><font>p_foot</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label><autoscroll>false</autoscroll></control>'%(SIDE,886,WIDTH-2*SIDE,GREY)+
  '</control>')

def episode_item(focused):
 thumb_w,thumb_h=400,225
 bg=surface(SIDE-18,4,WIDTH-2*SIDE+36,thumb_h+176,'round_s.png','14FFFFFF',26) if focused else ''
 return (bg+image(SIDE,18,thumb_w,thumb_h,MEDIA+'white.png',SURFACE,diffuse=MEDIA+'thumb_mask.png')+
  image(SIDE,18,thumb_w,thumb_h,'$VAR[Portrait_Thumb]',WHITE,'','>scale',MEDIA+'thumb_mask.png',background=True)+
  image(SIDE+thumb_w//2-48,18+thumb_h//2-48,96,96,MEDIA+'glass_96.png')+icon(SIDE+thumb_w//2-18,18+thumb_h//2-20,40,MEDIA+'play.png')+
  label(SIDE+thumb_w+30,40,WIDTH-2*SIDE-thumb_w-30,110,'$INFO[ListItem.Episode,,. ]$INFO[ListItem.Title]','p_h3',WHITE,'left','<wrapmultiline>true</wrapmultiline>')+
  label(SIDE+thumb_w+30,154,WIDTH-2*SIDE-thumb_w-30,48,'$INFO[ListItem.Duration(mins),,m]$INFO[ListItem.Premiered,  ·  ]','p_cap',GREY)+
  '<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>96</height><font>p_cap</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label></control>'%(SIDE,thumb_h+40,WIDTH-2*SIDE,GREY))

def video_nav(original):
 chip=lambda on:(surface(0,8,250,96,'pill_96.png' if on else 'glass_96.png',WHITE,48)+
  label(0,8,250,96,'$INFO[ListItem.Label]','p_foot_b','FF000000' if on else WHITE,'center'))
 chips=('<control type="list" id="50"><left>%d</left><top>1036</top><width>%d</width><height>112</height><orientation>horizontal</orientation>'
  '<ondown>60</ondown><onup>9002</onup><scrolltime tween="cubic">250</scrolltime><visible>Container.Content(seasons)</visible>'
  '<itemlayout width="268" height="112">%s</itemlayout><focusedlayout width="268" height="112">%s</focusedlayout></control>')%(SIDE,WIDTH-SIDE,chip(False),chip(True))
 episodes=('<control type="list" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
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
  '<scrolltime tween="cubic" easing="out">300</scrolltime><visible>!Container.Content(seasons) + !Container.Content(episodes)</visible>'
  '<itemlayout height="210">%s</itemlayout><focusedlayout height="210">%s</focusedlayout></control>')%(WIDTH,gen_item(False),gen_item(True))
 back=circle_button(9001,SIDE,36,108,'chevron-left.png','Back','<ondown>9002</ondown>')
 plain_title=label(SIDE+136,36,WIDTH-2*SIDE-136,108,'$INFO[Container.FolderName]','p_h2',WHITE,'left','<visible>!Container.Content(seasons) + !Container.Content(episodes)</visible>')
 body=('<controls>'+backdrop()+show_header('50')+chips+
  # Seasons page: episodes of the season chip in focus. Episodes page: the folder's own list.
  episodes%(60,1176,WIDTH,'50','Container.Content(seasons)',episode_item(False),episode_item(True),'<content target="videos">$INFO[Container(50).ListItem.FolderPath]</content>')+
  episodes%(52,1036,WIDTH,'9001','Container.Content(episodes)',episode_item(False),episode_item(True),'')+
  generic+image(0,0,WIDTH,90,MEDIA+'fade_down.png')+back+plain_title+'</controls>')
 return window(original,body,'50','<views>50,51,52</views>')

SHOW_VARS=('<variable name="Portrait_Show_Art"><value condition="!String.IsEmpty(ListItem.Art(tvshow.fanart))">$INFO[ListItem.Art(tvshow.fanart)]</value>'
           '<value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value><value>$INFO[Container.Art(fanart)]</value></variable>'
           '<variable name="Portrait_Show_Title"><value condition="!String.IsEmpty(ListItem.TVShowTitle)">$INFO[ListItem.TVShowTitle]</value><value>$INFO[Container.FolderName]</value></variable>'
           '<variable name="Portrait_Select_Art">'+''.join('<value condition="!String.IsEmpty(Container(%d).ListItem.Art(%s))">$INFO[Container(%d).ListItem.Art(%s)]</value>'%(c,k,c,k) for k in ('thumb','fanart','poster') for c in (3,6))+'</variable>'
           '<variable name="Portrait_Thumb"><value condition="!String.IsEmpty(ListItem.Art(thumb))">$INFO[ListItem.Art(thumb)]</value><value>$INFO[ListItem.Art(fanart)]</value></variable>')

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
  label(40,0,w-80,row_h,'$INFO[ListItem.Label]','p_body',WHITE,'center','<visible>![%s]</visible>'%icon_row)+
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

def fonts(original):
 root=ET.fromstring(original)
 for fontset in root.findall('fontset'):
  for name,filename,size in FONTS:
   f=ET.SubElement(fontset,'font');ET.SubElement(f,'name').text=name;ET.SubElement(f,'filename').text=filename;ET.SubElement(f,'size').text=str(size)
 return b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='utf-8')+b'\n'

def with_variables(xml):return xml

def includes():
 # Kodi reads variables only from includes; Fuse's own includes still come from 1080i.
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<includes><include file="../1080i/Includes.xml" />%s%s</includes>\n'
         %(MARKER,VARIABLES,SHOW_VARS)).encode()

def hub_files(skin,profile):
 source=Path(skin)/'1080i';out={}
 for name,(title,lists,tab) in HUBS.items():
  path=source/name;original=path.read_text() if path.exists() else ''
  out[name]=with_variables(hub_window(original,title,load_widgets(profile,lists),tab,SPOTLIGHT[name])).encode()
 return out

def portrait_files(skin,profile):
 """Every file of the portrait folder, derived from the current 1080i folder and widget lists."""
 skin=Path(skin);source=skin/'1080i';files={}
 for path in sorted(source.glob('*.xml')):
  if path.name in HANDMADE or path.name in SKIP_WRAP:continue
  try:data=shrink(path.read_bytes(),path.name)
  except ET.ParseError:continue
  if data:files[FOLDER+'/'+path.name]=data
 read=lambda name:(source/name).read_text() if (source/name).exists() else ''
 files[FOLDER+'/Font.xml']=fonts(read('Font.xml'))
 files[FOLDER+'/MyVideoNav.xml']=with_variables(video_nav(read('MyVideoNav.xml'))).encode()
 files[FOLDER+'/DialogVideoInfo.xml']=with_variables(video_info(read('DialogVideoInfo.xml'))).encode()
 files[FOLDER+'/DialogSelect.xml']=select_dialog(read('DialogSelect.xml')).encode()
 files[FOLDER+'/Custom_1170_Dialog_Options.xml']=more_menu(read('Custom_1170_Dialog_Options.xml')).encode()
 # Fuse's landscape header (tabs/search/gear) is replaced by the portrait header and tab bar.
 files[FOLDER+'/Custom_1182_Dialog_Topmenu_Overlay.xml']=window(read('Custom_1182_Dialog_Topmenu_Overlay.xml'),'<controls />','9999').encode()
 files[FOLDER+'/Includes.xml']=includes()
 for name,data in hub_files(skin,profile).items():files[FOLDER+'/'+name]=data
 for name,data in textures().items():files['extras/portrait/'+name]=data
 return files

def write(skin,files):
 changed=[]
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
 data=addon.read_text()
 if 'folder="%s"'%FOLDER in data:return False
 res=''.join('<res aspect="%s" default="false" folder="%s" width="%d" height="%d" />\n        '%(a,FOLDER,w,h) for a,w,h in RES)
 anchor=re.search(r'<res [^>]*default="true"[^>]*/>',data);assert anchor,'Fuse resolution list not found'
 addon.write_text(data[:anchor.start()]+res+data[anchor.start():]);return True

# --- on the phone ----------------------------------------------------------------------------------
def refresh(skin,profile):
 """On the phone: follow the owner's widget lists and any later landscape (1080i) repair.
 Returns the changed paths; the caller reloads the skin if any changed."""
 if not (Path(skin)/FOLDER).is_dir():return []
 return write(skin,portrait_files(skin,profile))

def is_portrait(info):
 try:return int(info('System.ScreenHeight'))>int(info('System.ScreenWidth'))
 except ValueError:return None

def watch(info,invoke,wait,current_skin,fuse='skin.arctic.fuse.3',interval=0.5,settle=2):
 """Reload the skin after the phone settles in a new orientation, so Kodi loads the matching folder."""
 last=is_portrait(info);pending=0
 while not wait(interval):
  now=is_portrait(info)
  if now is None or now==last:pending=0;continue
  pending+=1
  if pending<settle:continue
  last=now;pending=0
  if current_skin()==fuse:invoke('ReloadSkin()')

def run_service(xbmc,xbmcvfs,monitor,profile,invoke,fuse='skin.arctic.fuse.3'):
 """Started by the bootstrap service after setup: keep the portrait folder current, then follow rotations."""
 skin=Path(xbmcvfs.translatePath('special://skin/')).resolve()
 if skin.name==fuse:
  try:
   changed=refresh(skin,profile)
   marker=Path(profile)/'addon_data/service.kodi.ios.bootstrap/portrait.json'
   if not marker.exists():
    # Once: no ".." rows, so a show page opens on its first season (the owner can turn it back on in Settings).
    xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.SetSettingValue','params':{'setting':'filelists.showparentdiritems','value':False}}))
    marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'revision':REVISION})+'\n')
   if changed and is_portrait(xbmc.getInfoLabel):invoke('ReloadSkin()')
  except Exception as error:xbmc.log('Kodi iOS portrait refresh skipped: '+type(error).__name__,xbmc.LOGWARNING)
 watch(xbmc.getInfoLabel,invoke,monitor.waitForAbort,xbmc.getSkinDir,fuse)
