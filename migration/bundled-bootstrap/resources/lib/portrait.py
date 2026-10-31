"""r11 portrait layout for Arctic Fuse 3 on iPhone ("layout A": hero card, poster rows, bottom tab bar).

Kodi picks the skin folder whose aspect is closest to the screen, so Fuse gets a `portrait` folder next to
`1080i`. Home, the TV/Movies/Downloads hubs, the show page (MyVideoNav), the info page, the select dialog
(the watch chooser) and the More menu are drawn for portrait. Every other window is the landscape Fuse
window shrunk into the middle of the portrait screen, so nothing becomes unreachable.

The same module builds the folder into the IPA (scripts/build_customized_ipa.py) and, on the phone,
refreshes the poster rows from the owner's widget lists and reloads the skin when the phone rotates.
"""
import json,os,re,struct,zlib,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

REVISION='ios-portrait-r1'
FOLDER='portrait'
# iPhone 16 Pro portrait: 402x874 pt with 62/34 pt safe-area insets. Kodi stretches the skin canvas into
# the safe area, so 1080 x 2090 keeps pixels square there. 9:16 covers phones with a home button.
WIDTH,HEIGHT=1080,2090
RES=[('9:19.5',WIDTH,HEIGHT),('9:16',WIDTH,1920)]
MARKER='Kodi-iOS portrait '+REVISION
NODES='addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-{}.json'
ICONS='special://skin/extras/icons/'
MEDIA='special://skin/extras/portrait/'
DRIVE='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
MENU='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)'
UPDATES='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/check_updates.py)'
BG='FF0B0B0F';GREY='FFB9B9BF';DIM='FF8C8C92';GREEN='FF46D369';CARD='FF1C1C22'
# window file -> (title, widget lists, tab)
HUBS={'Home.xml':('Home',['homewidgets'],'home'),
      'Custom_1101_Hub.xml':('TV Shows',['1101widgets'],'tv'),
      'Custom_1102_Hub.xml':('Movies',['1102widgets'],'movies'),
      'Custom_1103_Hub.xml':('Downloads',['1103widgets','1104widgets'],'downloads'),
      'Custom_1104_Hub.xml':('Downloads',['1104widgets','1103widgets'],'downloads')}
SPOTLIGHT={'Home.xml':'home','Custom_1101_Hub.xml':'1101','Custom_1102_Hub.xml':'1102','Custom_1103_Hub.xml':'1103','Custom_1104_Hub.xml':'1104'}
TABS=[('home','Home','house.png','ReplaceWindow(Home)'),('tv','TV','tv.png','ReplaceWindow(1101)'),
      ('movies','Movies','film.png','ReplaceWindow(1102)'),('downloads','Downloads','download.png','ReplaceWindow(1103)'),
      ('drive','Drive','cloud.png',DRIVE),('more','More','ellipsis.png','ActivateWindow(1170)')]
MORE=[('Settings','gear.png','ActivateWindow(settings)'),('Google Drive','cloud.png',DRIVE),
      ('Check for updates','cloud-arrow-down.png',UPDATES),('iPhone navigation / recovery','life-ring.png',MENU),
      ('Favourites','favourites2.png','ActivateWindow(1160)'),('File manager','filebox.png','ActivateWindow(filemanager)')]
HANDMADE=set(HUBS)|{'Custom_1182_Dialog_Topmenu_Overlay.xml','MyVideoNav.xml','DialogVideoInfo.xml','DialogSelect.xml','Custom_1170_Dialog_Options.xml','Font.xml','Includes.xml'}
# Never shrunk: playback stays landscape, and these are not windows.
SKIP_WRAP={'VideoFullScreen.xml','VideoOSD.xml','MusicVisualisation.xml','SlideShow.xml','Pointer.xml'}
FONTS=[('p_title','Inter-Bold.ttf',84),('p_head','Inter-Bold.ttf',60),('p_row','Inter-Bold.ttf',44),
       ('p_btn','Inter-Bold.ttf',42),('p_body','Inter-Regular.ttf',36),('p_meta','Inter-Regular.ttf',34),
       ('p_meta_bold','Inter-Bold.ttf',34),('p_label','Inter-Bold.ttf',30),('p_tab','Inter-Regular.ttf',26)]
POSTER=(290,435);GAP=22;SIDE=40

# --- tiny PNG writer (no PIL on the build host) -------------------------------------------------------
def png(width,height,pixel):
 rows=b''.join(b'\0'+b''.join(struct.pack('4B',*pixel(x,y)) for x in range(width)) for y in range(height))
 chunk=lambda tag,data:struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')

def rounded(width,height,radius):
 def alpha(x,y):
  cx=min(max(x+0.5,radius),width-radius);cy=min(max(y+0.5,radius),height-radius)
  d=((x+0.5-cx)**2+(y+0.5-cy)**2)**0.5
  return (255,255,255,int(255*min(1,max(0,radius-d+0.5))))
 return png(width,height,alpha)

def textures():
 shade=lambda x,y:(0,0,0,int(255*min(1,max(0,(y/255-0.35)/0.55))**1.4))
 return {'round.png':rounded(96,96,32),'round_s.png':rounded(48,48,16),'pill.png':rounded(120,120,60),
         'shade.png':png(4,256,shade),'top.png':png(4,256,lambda x,y:(11,11,15,int(255*(y/255)))),
         'poster_mask.png':rounded(POSTER[0],POSTER[1],22),'hero_mask.png':rounded(500,575,22),
         'thumb_mask.png':rounded(360,203,16),'white.png':png(4,4,lambda x,y:(255,255,255,255)),'play.png':triangle(64)}

def triangle(size):
 def alpha(x,y):
  # right-pointing triangle, anti-aliased by 4x4 supersampling
  inside=sum(1 for i in range(4) for j in range(4) if (lambda px,py:px>=8 and abs(py-size/2)<=(size-8-px)*0.58)(x+(i+.5)/4,y+(j+.5)/4))
  return (255,255,255,int(255*inside/16))
 return png(size,size,alpha)

# --- XML helpers ---------------------------------------------------------------------------------------
def e(text):return escape(str(text),{'"':'&quot;'})
def tag(name,value,**attrs):
 a=''.join(' %s="%s"'%(k.rstrip('_'),e(v)) for k,v in attrs.items())
 return '<%s%s>%s</%s>'%(name,a,e(value),name)
def box(x,y,w,h,color,texture='round.png',border=32,extra=''):
 return ('<control type="image"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>'
         '<texture border="%d" colordiffuse="%s">%s%s</texture>%s</control>')%(x,y,w,h,border,color,MEDIA,texture,extra)
def label(x,y,w,h,text,font,color='FFFFFFFF',align='left',extra=''):
 return ('<control type="label"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font>'
         '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><label>%s</label>%s</control>')%(x,y,w,h,font,color,align,e(text),extra)
def button(id,x,y,w,h,text,action,fill,textcolor,icon='',font='p_btn',extra=''):
 iconxml=('<control type="image"><left>%d</left><top>%d</top><width>44</width><height>44</height>'
          '<texture colordiffuse="%s">%s</texture></control>')%(w//2-100,(h-44)//2,textcolor,icon if '://' in icon else ICONS+icon) if icon else ''
 return ('<control type="group"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>%s'
         '<control type="button" id="%d"><width>%s</width><height>%s</height><font>%s</font><label>%s</label>'
         '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
         '<textoffsetx>%d</textoffsetx><texturefocus border="32" colordiffuse="%s">%sround.png</texturefocus>'
         '<texturenofocus border="32" colordiffuse="%s">%sround.png</texturenofocus>%s<onclick>%s</onclick></control>%s</control>'
         )%(x,y,w,h,'',id,w,h,font,e(text),textcolor,textcolor,30 if icon else 0,fill,MEDIA,fill,MEDIA,extra,e(action),iconxml)

def tabbar(active):
 w=WIDTH//len(TABS);items=[]
 for i,(key,text,icon,action) in enumerate(TABS):
  color='FFFFFFFF' if key==active else DIM
  items.append(('<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>150</height>'
   '<texturefocus colordiffuse="1AFFFFFF">%swhite.png</texturefocus><texturenofocus /><label></label>'
   '<onclick>%s</onclick><onup>5000</onup><onleft>%d</onleft><onright>%d</onright></control>'
   '<control type="image"><left>%d</left><top>22</top><width>56</width><height>56</height><texture colordiffuse="%s">%s</texture></control>'
   )%(9201+i,i*w,w,MEDIA,e(action),9201+(i-1)%len(TABS),9201+(i+1)%len(TABS),i*w+(w-56)//2,color,ICONS+icon)+label(i*w,86,w,40,text,'p_tab',color,'center'))
 return ('<control type="group" id="9200"><description>%s tab bar</description><left>0</left><bottom>0</bottom><width>%d</width><height>150</height>'
  '<control type="image"><width>%d</width><height>150</height><texture colordiffuse="F5121216">%swhite.png</texture></control>'
  '<control type="image"><width>%d</width><height>2</height><texture colordiffuse="14FFFFFF">%swhite.png</texture></control>%s</control>'
  )%(MARKER,WIDTH,WIDTH,MEDIA,WIDTH,MEDIA,''.join(items))

# --- rows from the owner's widget lists ----------------------------------------------------------------
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

def row(index,widget,last):
 id=5001+index;title=str(widget.get('label') or '')
 # Hidden while empty; allowhiddenfocus keeps Kodi loading the row's content while it is hidden.
 visible='Integer.IsGreater(Container(%d).NumItems,0) | Container(%d).IsUpdating'%(id,id)
 item=('<control type="image"><width>%d</width><height>%d</height><texture background="true" diffuse="%sposter_mask.png" fallback="DefaultVideo.png">$INFO[ListItem.Art(poster)]</texture><aspectratio>scale</aspectratio></control>'
       '<control type="image"><width>%d</width><height>%d</height><texture colordiffuse="FF26262C" diffuse="%sposter_mask.png">%swhite.png</texture><visible>String.IsEmpty(ListItem.Art(poster))</visible></control>'
       '<control type="label"><left>14</left><top>%d</top><width>%d</width><height>120</height><font>p_label</font><textcolor>FFFFFFFF</textcolor><aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><label>$INFO[ListItem.Label]</label><visible>String.IsEmpty(ListItem.Art(poster))</visible></control>'
       )%(POSTER[0],POSTER[1],MEDIA,POSTER[0],POSTER[1],MEDIA,MEDIA,POSTER[1]-134,POSTER[0]-28)
 focus=item+('<control type="image"><width>%d</width><height>%d</height><texture border="16" colordiffuse="FFFFFFFF">%sround_s.png</texture><visible>Control.HasFocus(%d)</visible></control>'
             '<control type="image"><left>6</left><top>6</top><width>%d</width><height>%d</height><texture background="true" diffuse="%sposter_mask.png" fallback="DefaultVideo.png">$INFO[ListItem.Art(poster)]</texture><aspectratio>scale</aspectratio><visible>Control.HasFocus(%d)</visible></control>'
             )%(POSTER[0],POSTER[1],MEDIA,id,POSTER[0]-12,POSTER[1]-12,MEDIA,id)
 return ('<control type="label" id="%d"><width>%d</width><height>96</height><left>%d</left><font>p_row</font><textcolor>FFFFFFFF</textcolor>'
  '<aligny>bottom</aligny><textoffsetx>%d</textoffsetx><label>%s</label><visible>%s</visible></control>'
  '<control type="list" id="%d"><left>0</left><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
  '%s<scrolltime tween="quadratic">300</scrolltime><preloaditems>2</preloaditems>'
  '<visible allowhiddenfocus="true">%s</visible>'
  '<itemlayout width="%d" height="%d"><control type="group"><left>%d</left><top>18</top>%s</control></itemlayout>'
  '<focusedlayout width="%d" height="%d"><control type="group"><left>%d</left><top>18</top>%s</control></focusedlayout>'
  '<content target="%s">%s</content></control>'
  )%(id+500,WIDTH,0,SIDE,e(title),visible,id,WIDTH,POSTER[1]+36,'<ondown>9201</ondown>' if last else '',visible,
     POSTER[0]+GAP,POSTER[1]+36,SIDE,item,POSTER[0]+GAP,POSTER[1]+36,SIDE,focus,e(widget.get('target') or 'videos'),e(widget['path']))

def hero(spotlight):
 # The hub's spotlight list (TMDb on the phone): swipe sideways for the next title.
 w,h=WIDTH-2*SIDE,1150
 layout=lambda focused:('<control type="group"><left>%d</left>'
  '<control type="image"><width>%d</width><height>%d</height><texture background="true" diffuse="%shero_mask.png" fallback="DefaultVideo.png">$VAR[Portrait_Hero_Art]</texture><aspectratio>scale</aspectratio></control>'
  '<control type="image"><width>%d</width><height>%d</height><texture diffuse="%shero_mask.png">%sshade.png</texture></control>'
  '</control>')%(SIDE,w,h,MEDIA,w,h,MEDIA,MEDIA)
 info='Container(4000).ListItem'
 meta=('[COLOR %s]$INFO[%s.Rating,,  TMDb][/COLOR]$INFO[%s.Year,   •   ]$INFO[%s.Genre,   •   ]')%(GREEN,info,info,info)
 # A show opens its page (seasons and episodes); a movie goes straight to "How would you like to watch?".
 play=('PlayMedia($ESCINFO[%s.FileNameAndPath])'%info)
 show=('ActivateWindow(Videos,$ESCINFO[%s.FolderPath],return)'%info)
 is_show='String.IsEqual(%s.DBType,tvshow)'%info
 return ('<control type="group" id="4100"><height>%d</height>'
  '<control type="fixedlist" id="4000"><width>%d</width><height>%d</height><orientation>horizontal</orientation>'
  '<movement>0</movement><focusposition>0</focusposition><scrolltime tween="cubic">400</scrolltime><ondown>4001</ondown>'
  '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
  '<content target="videos" limit="12">$INFO[Skin.String(HomeSwitcher.%s.Spotlight.Path)]</content></control>'
  '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>240</height><aspectratio aligny="bottom">keep</aspectratio><texture>$INFO[%s.Art(clearlogo)]</texture></control>'
  '%s%s'
  '<control type="group"><top>%d</top>%s%s</control>'
  '</control>'
  )%(h+30,WIDTH,h,WIDTH,h,layout(False),WIDTH,h,layout(True),spotlight,
     SIDE+120,h-530,w-240,info,
     label(SIDE+40,h-470,w-80,210,'$INFO[%s.Label]'%info,'p_title','FFFFFFFF','center','<wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(%s.Art(clearlogo))</visible>'%info),
     label(SIDE+20,h-240,w-40,60,meta,'p_meta',GREY,'center'),
     h-160,
     button(4001,SIDE+60,0,420,110,'Play','','FFFFFFFF','FF000000',MEDIA+'play.png','p_btn','<onup>4000</onup><onright>4002</onright><ondown>5001</ondown>'
            '<onclick condition="%s">%s</onclick><onclick condition="!%s">%s</onclick>'%(is_show,e(show),is_show,e(play))).replace('<onclick></onclick>',''),
     button(4002,SIDE+w-480,0,420,110,'Info','SetFocus(4000)'+'\x00'+'Action(Info)','B36D6D6E','FFFFFFFF','circle-info.png','p_btn','<onup>4000</onup><onleft>4001</onleft><ondown>5001</ondown>'))

def hub_window(original,title,widgets,tab,spotlight):
 rows=''.join(row(i,w,i==len(widgets)-1) for i,w in enumerate(widgets)) or label(SIDE,0,WIDTH-80,200,'Nothing here yet','p_body',GREY)
 header=(label(SIDE,0,700,120,title,'p_head')+
  button(9101,WIDTH-SIDE-96,12,96,96,'','ReplaceWindow(1105)','1FFFFFFF','FFFFFFFF','',extra='')+
  '<control type="image"><left>%d</left><top>38</top><width>44</width><height>44</height><texture>%smagnifying-glass.png</texture></control>'%(WIDTH-SIDE-70,ICONS))
 body=('<controls>'
  '<control type="image"><width>%d</width><height>%d</height><texture colordiffuse="%s">%swhite.png</texture></control>'
  '<control type="grouplist" id="5000"><top>130</top><width>%d</width><bottom>150</bottom><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><scrolltime tween="quadratic">350</scrolltime><usecontrolcoords>true</usecontrolcoords>%s%s'
  '<control type="image"><height>60</height><texture /></control></control>'
  '<control type="image"><width>%d</width><height>150</height><texture>%stop.png</texture><animation effect="rotate" end="180" center="auto" time="0" condition="true">Conditional</animation></control>'
  '<control type="group"><top>6</top>%s</control>%s</controls>'
  )%(WIDTH,HEIGHT,BG,MEDIA,WIDTH,hero(spotlight),rows,WIDTH,MEDIA,header,tabbar(tab))
 return window(original,body,'4000')

def window(original,body,default,extra_root=''):
 """Keep the landscape window's type/id and its onload helpers (Fuse init, the bootstrap's setup lock)."""
 root=ET.fromstring(original) if original else ET.Element('window')
 attrs=''.join(' %s="%s"'%(k,e(v)) for k,v in root.attrib.items())
 keep=''.join(ET.tostring(node,encoding='unicode') for node in root if node.tag in ('onload','onunload','include','param','zorder','depth','menucontrol','views','animation') and not (node.tag=='include' and 'View_' in (node.text or '')))
 out='<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window%s><defaultcontrol always="true">%s</defaultcontrol>%s%s%s</window>\n'%(MARKER,attrs,default,keep,extra_root,body)
 return re.sub('\x00','</onclick><onclick>',out)

VARIABLES=('<variable name="Portrait_Hero_Art"><value condition="!String.IsEmpty(ListItem.Art(poster))">$INFO[ListItem.Art(poster)]</value>'
           '<value>$INFO[ListItem.Art(fanart)]</value></variable>')

# --- show page (seasons as chips, episodes below) and generic lists -------------------------------------
def video_nav(original):
 chips=('<control type="list" id="50"><left>%d</left><top>860</top><width>%d</width><height>110</height><orientation>horizontal</orientation>'
  '<ondown>60</ondown><onup>9001</onup><scrolltime>250</scrolltime><visible>Container.Content(seasons)</visible>'
  '<itemlayout width="250" height="110">%s</itemlayout><focusedlayout width="250" height="110">%s</focusedlayout></control>')
 chip=lambda on:(box(0,10,230,90,'FFFFFFFF' if on else '1AFFFFFF','pill.png',45)+
  label(0,10,230,90,'$INFO[ListItem.Label]','p_meta_bold','FF000000' if on else 'FFFFFFFF','center'))
 ep_item=lambda focused:('<control type="image"><left>%d</left><top>20</top><width>360</width><height>203</height>'
  '<texture background="true" diffuse="%sthumb_mask.png" fallback="DefaultVideo.png">$VAR[Portrait_Thumb]</texture><aspectratio>scale</aspectratio></control>'
  '<control type="image"><left>%d</left><top>91</top><width>60</width><height>60</height><texture colordiffuse="DDFFFFFF">%splay.png</texture></control>'
  '%s%s%s')%(SIDE,MEDIA,SIDE+150,ICONS,
  label(SIDE+390,30,WIDTH-SIDE*2-390,60,'$INFO[ListItem.Episode,,. ]$INFO[ListItem.Title]','p_meta_bold'),
  label(SIDE+390,90,WIDTH-SIDE*2-390,50,'$INFO[ListItem.Duration(mins),, min]$INFO[ListItem.Premiered,   •   ]','p_meta',DIM),
  box(SIDE-14,6,WIDTH-2*SIDE+28,231,'1FFFFFFF','round_s.png',16) if focused else '')
 episodes=('<control type="list" id="%d"><left>0</left><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
  '<onup>%s</onup><scrolltime tween="quadratic">300</scrolltime><visible>%s</visible>'
  '<itemlayout height="243">%s</itemlayout><focusedlayout height="243">%s</focusedlayout>%s</control>')
 generic=('<control type="list" id="51"><left>0</left><top>170</top><width>%d</width><bottom>0</bottom><onup>9001</onup>'
  '<scrolltime tween="quadratic">300</scrolltime><visible>!Container.Content(seasons) + !Container.Content(episodes)</visible>'
  '<itemlayout height="190">%s</itemlayout><focusedlayout height="190">%s</focusedlayout></control>')
 gen_item=lambda focused:((box(SIDE-14,8,WIDTH-2*SIDE+28,174,'1FFFFFFF','round_s.png',16) if focused else '')+
  '<control type="image"><left>%d</left><top>20</top><width>100</width><height>150</height><texture background="true" diffuse="%sposter_mask.png">$INFO[ListItem.Art(poster)]</texture><aspectratio>scale</aspectratio><visible>!String.IsEmpty(ListItem.Art(poster))</visible></control>'
  '<control type="image"><left>%d</left><top>45</top><width>100</width><height>100</height><texture>$INFO[ListItem.Icon]</texture><aspectratio>keep</aspectratio><visible>String.IsEmpty(ListItem.Art(poster))</visible></control>'
  %(SIDE,MEDIA,SIDE)+label(SIDE+130,25,WIDTH-2*SIDE-130,80,'$INFO[ListItem.Label]','p_meta_bold')+
  label(SIDE+130,95,WIDTH-2*SIDE-130,60,'$INFO[ListItem.Label2]','p_meta',DIM))
 art='$INFO[ListItem.Art(tvshow.fanart)]'
 head=('<control type="group"><visible>Container.Content(seasons) | Container.Content(episodes)</visible>'
  '<control type="image"><width>%d</width><height>720</height><texture background="true">$VAR[Portrait_Show_Art]</texture><aspectratio>scale</aspectratio></control>'
  '<control type="image"><width>%d</width><height>720</height><texture>%stop.png</texture></control>'
  '%s%s%s</control>'
  )%(WIDTH,WIDTH,MEDIA,
     label(SIDE,520,WIDTH-2*SIDE,110,'$VAR[Portrait_Show_Title]','p_title','FFFFFFFF','left','<scroll>false</scroll>'),
     label(SIDE,630,WIDTH-2*SIDE,56,'[COLOR %s]$INFO[ListItem.Rating,,  TMDb][/COLOR]$INFO[ListItem.Year,   •   ]$INFO[Container.NumItems,   •   , seasons]'%GREEN,'p_meta',GREY),
     '<control type="textbox"><left>%d</left><top>692</top><width>%d</width><height>150</height><font>p_meta</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label></control>'%(SIDE,WIDTH-2*SIDE,GREY))
 back=button(9001,SIDE,20,96,96,'','Back','66000000','FFFFFFFF','',extra='<ondown>50</ondown>')+(
  '<control type="image"><left>%d</left><top>46</top><width>44</width><height>44</height><texture>%schevron-left.png</texture></control>'%(SIDE+26,ICONS))
 plain_title=label(SIDE+120,20,WIDTH-2*SIDE-120,96,'$INFO[Container.FolderName]','p_head','FFFFFFFF','left','<visible>!Container.Content(seasons) + !Container.Content(episodes)</visible>')
 body=('<controls><control type="image"><width>%d</width><height>%d</height><texture colordiffuse="%s">%swhite.png</texture></control>%s'
  %(WIDTH,HEIGHT,BG,MEDIA,head)+
  chips%(SIDE,WIDTH-SIDE,chip(False),chip(True))+
  # Seasons page: episodes of the season chip in focus. Episodes page: the folder's own list.
  episodes%(60,990,WIDTH,'50','Container.Content(seasons)',ep_item(False),ep_item(True),'<content target="videos">$INFO[Container(50).ListItem.FolderPath]</content>')+
  episodes%(52,880,WIDTH,'9001','Container.Content(episodes)',ep_item(False),ep_item(True),'')+
  generic%(WIDTH,gen_item(False),gen_item(True))+back+plain_title+'</controls>')
 extra=('<views>50,51,52</views>')
 return window(original,body,'50',extra)

SHOW_VARS=('<variable name="Portrait_Show_Art"><value condition="!String.IsEmpty(ListItem.Art(tvshow.fanart))">$INFO[ListItem.Art(tvshow.fanart)]</value>'
           '<value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value><value>$INFO[Container.Art(fanart)]</value></variable>'
           '<variable name="Portrait_Show_Title"><value condition="!String.IsEmpty(ListItem.TVShowTitle)">$INFO[ListItem.TVShowTitle]</value><value>$INFO[Container.FolderName]</value></variable>'
           '<variable name="Portrait_Select_Art">'+''.join('<value condition="!String.IsEmpty(Container(%d).ListItem.Art(%s))">$INFO[Container(%d).ListItem.Art(%s)]</value>'%(c,k,c,k) for k in ('thumb','fanart','poster') for c in (3,6))+'</variable>'
           '<variable name="Portrait_Thumb"><value condition="!String.IsEmpty(ListItem.Art(thumb))">$INFO[ListItem.Art(thumb)]</value><value>$INFO[ListItem.Art(fanart)]</value></variable>')

def video_info(original):
 w=WIDTH-2*SIDE
 body=('<controls><control type="image"><width>%d</width><height>%d</height><texture colordiffuse="%s">%swhite.png</texture></control>'
  '<control type="image"><width>%d</width><height>1100</height><texture background="true">$INFO[ListItem.Art(fanart)]</texture><aspectratio>scale</aspectratio></control>'
  '<control type="image"><width>%d</width><height>1100</height><texture>%stop.png</texture></control>'
  '<control type="image"><left>%d</left><top>560</top><width>%d</width><height>200</height><aspectratio align="left" aligny="bottom">keep</aspectratio><texture>$INFO[ListItem.Art(clearlogo)]</texture></control>'
  '%s%s'
  '<control type="grouplist"><left>%d</left><top>950</top><width>%d</width><height>110</height><orientation>horizontal</orientation><itemgap>30</itemgap>%s%s</control>'
  '<control type="textbox" id="4"><left>%d</left><top>1100</top><width>%d</width><height>700</height><font>p_body</font><textcolor>%s</textcolor><label>$INFO[ListItem.Plot]</label></control>'
  '%s</controls>'
  )%(WIDTH,HEIGHT,BG,MEDIA,WIDTH,WIDTH,MEDIA,SIDE,w,
     label(SIDE,600,w,200,'$INFO[ListItem.Title]','p_title','FFFFFFFF','left','<wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(ListItem.Art(clearlogo))</visible>'),
     label(SIDE,820,w,60,'[COLOR %s]$INFO[ListItem.Rating,,  TMDb][/COLOR]$INFO[ListItem.Year,   •   ]$INFO[ListItem.Genre,   •   ]$INFO[ListItem.Duration(mins),   •   , min]'%GREEN,'p_meta',GREY),
     SIDE,w,
     button(8,0,0,480,110,'Play','','FFFFFFFF','FF000000',MEDIA+'play.png',extra='<visible>!String.IsEqual(ListItem.DBType,tvshow)</visible>').replace('<onclick></onclick>',''),
     button(9010,0,0,480,110,'Episodes','Close'+'\x00'+'ActivateWindow(Videos,$ESCINFO[ListItem.FolderPath],return)','B36D6D6E','FFFFFFFF','tv.png',extra='<visible>String.IsEqual(ListItem.DBType,tvshow)</visible>'),
     SIDE,w,GREY,
     button(9001,SIDE,20,96,96,'','Close','66000000','FFFFFFFF')+'<control type="image"><left>%d</left><top>46</top><width>44</width><height>44</height><texture>%sxmark.png</texture></control>'%(SIDE+26,ICONS))
 return window(original,body,'8')

def centered_dialog(original,heading,items_xml,list_id,height,default,extra='',card='',group_extra=''):
 """A rounded card in the middle of the screen; tapping outside closes it."""
 w=WIDTH-2*70;top=(HEIGHT-height)//2
 body=('<controls>'
  '<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="B3000000">%swhite.png</texturefocus>'
  '<texturenofocus colordiffuse="B3000000">%swhite.png</texturenofocus><onclick>Close</onclick><onfocus>SetFocus(%s)</onfocus></control>'
  '<control type="group"><left>70</left><top>%d</top><width>%d</width><height>%d</height>%s'
  '<animation effect="zoom" start="94" end="100" center="auto" time="180" tween="cubic" easing="out">WindowOpen</animation>'
  '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>'
  '<animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'
  '%s%s%s%s</control></controls>'
  )%(WIDTH,HEIGHT,MEDIA,MEDIA,list_id,top,w,height,group_extra,card or box(0,0,w,height,CARD),heading,items_xml,extra)
 return window(original,body,default)

SELECT_ROWS=8
def select_dialog(original):
 """Kodi's select dialog (also "How would you like to watch?"): a card sized to its rows, centred."""
 w=WIDTH-2*70;full=200+SELECT_ROWS*140+170
 count=lambda n,op='IsEqual':'[Integer.%s(Container(3).NumItems,%d) | Integer.%s(Container(6).NumItems,%d)]'%(op,n,op,n)
 # The watch chooser gives every row the title's art: show it once, beside the question, instead of per row.
 titled='!String.IsEmpty(Container(3).ListItem.Art(poster)) | !String.IsEmpty(Container(6).ListItem.Art(poster))'
 art='$VAR[Portrait_Select_Art]'
 heading=(label(50,30,w-100,130,'$INFO[Control.GetLabel(1)]','p_row','FFFFFFFF','left','<wrapmultiline>true</wrapmultiline><visible>![%s]</visible>'%titled)+
          '<control type="image"><left>50</left><top>30</top><width>220</width><height>124</height><texture diffuse="%sthumb_mask.png">%s</texture><aspectratio>scale</aspectratio><visible>%s</visible></control>'%(MEDIA,art,titled)+
          label(300,30,w-350,130,'$INFO[Control.GetLabel(1)]','p_meta_bold','FFFFFFFF','left','<wrapmultiline>true</wrapmultiline><visible>%s</visible>'%titled)+
          '<control type="label" id="1"><visible>false</visible></control>')
 icon_row='!String.IsEmpty(ListItem.Icon) + !String.StartsWith(ListItem.Icon,Default) + String.IsEmpty(ListItem.Art(poster))'
 row=lambda focused:((box(20,4,w-40,128,'1FFFFFFF','round_s.png',16) if focused else '')+
  '<control type="image"><left>40</left><top>26</top><width>84</width><height>84</height><texture diffuse="%sthumb_mask.png">$INFO[ListItem.Icon]</texture><aspectratio>scale</aspectratio><visible>%s</visible></control>'%(MEDIA,icon_row)+
  label(40,4,w-120,128,'$INFO[ListItem.Label]','p_body','FFFFFFFF','left','<visible>![%s]</visible>'%icon_row)+
  label(150,4,w-200,128,'$INFO[ListItem.Label]','p_body','FFFFFFFF','left','<visible>%s</visible>'%icon_row)+
  '<control type="image"><left>%d</left><top>48</top><width>40</width><height>40</height><texture colordiffuse="FF46D369">%scheck.png</texture><visible>ListItem.IsSelected</visible></control>'%(w-90,ICONS)+
  '<control type="image"><left>40</left><top>134</top><width>%d</width><height>2</height><texture colordiffuse="0FFFFFFF">%swhite.png</texture></control>'%(w-80,MEDIA))
 lists=''.join(('<control type="list" id="%d"><left>0</left><top>170</top><width>%d</width><height>%d</height><onup>%d</onup><ondown>%d</ondown>'
  '<scrolltime tween="quadratic">250</scrolltime><itemlayout height="140">%s</itemlayout><focusedlayout height="140">%s</focusedlayout></control>'
  )%(id,w,SELECT_ROWS*140,id,9050,row(False),row(True)) for id in (3,6))
 # Fewer rows: a shorter card (one background per row count), moved down to stay centred, Cancel moved up.
 cards=''.join(box(0,0,w,200+n*140+170,CARD,extra='<visible>%s</visible>'%count(n)) for n in range(1,SELECT_ROWS))
 cards+=box(0,0,w,full,CARD,extra='<visible>%s</visible>'%count(SELECT_ROWS-1,'IsGreater'))
 slide=lambda dy,n:'<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(dy,count(n))
 cancel=('<control type="group"><top>%d</top>%s%s</control>'%(full-150,''.join(slide(-(SELECT_ROWS-n)*140,n) for n in range(1,SELECT_ROWS)),
         button(9050,50,0,w-100,100,'Cancel','Close','1AFFFFFF','FFFFFFFF',font='p_meta_bold',extra='<onup>3</onup>')))
 hidden=''.join('<control type="button" id="%d"><visible>false</visible></control>'%i for i in (5,7,8))+'<control type="label" id="2"><visible>false</visible></control>'
 return centered_dialog(original,heading,lists+cancel+hidden,3,full,'3',card=cards,group_extra=''.join(slide((SELECT_ROWS-n)*70,n) for n in range(1,SELECT_ROWS)))

def more_menu(original):
 w=WIDTH-2*70;height=200+len(MORE)*140+40
 items=''.join('<item><label>%s</label><icon>%s</icon><onclick>Dialog.Close(1170)</onclick><onclick>%s</onclick></item>'%(e(t),ICONS+i,e(a)) for t,i,a in MORE)
 row=lambda focused:((box(20,4,w-40,128,'1FFFFFFF','round_s.png',16) if focused else '')+
  '<control type="image"><left>50</left><top>42</top><width>52</width><height>52</height><texture>$INFO[ListItem.Icon]</texture></control>'+
  label(140,4,w-180,128,'$INFO[ListItem.Label]','p_body'))
 lst=('<control type="list" id="3"><left>0</left><top>150</top><width>%d</width><height>%d</height><itemlayout height="140">%s</itemlayout>'
      '<focusedlayout height="140">%s</focusedlayout><content>%s</content></control>')%(w,len(MORE)*140,row(False),row(True),items)
 return centered_dialog(original,label(50,40,w-100,80,'More','p_row'),lst,3,height,'3')

# --- fallback: any other window is the landscape window, shrunk into the middle ------------------------
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
