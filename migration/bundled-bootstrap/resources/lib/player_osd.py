"""Video controls (VideoOSD) in the Apple TV player's layout, for Arctic Fuse's landscape (1080i) folder.

Fullscreen video is landscape on the phone, so the controls live in 1080i (2340 x 1080 on an iPhone 16 Pro).
Top left: close and Play on TV (AirPlay icon). Centre: back 10 s, play/pause, forward 10 s. Bottom: the title,
speed / audio / subtitles, the progress bar with time left, then Info and Continue Watching (the in-progress
row). No volume control. Fuse's seek bar is replaced by seekbar_window(), shown only while the owner seeks.
"""
import re
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

MARKER='Kodi-iOS player controls r5'
EDGE=150   # from the screen edges: rounded corners and the Dynamic Island (about 56 pt on an iPhone 16 Pro)
# Build 191 (owner, landscape video: "the words get cut off by the camera island ... need to move over to the right"):
# nothing that is read or tapped starts closer than SAFE to either side (the island is on the left or the right,
# whichever way the phone turns): 140 units of 2340 = 59 pt of 874, the iPhone's landscape safe-area inset.
SAFE=140
ICONS='special://skin/extras/icons/'
MEDIA='special://skin/extras/portrait/'
BOOT='special://xbmc/addons/service.kodi.ios.bootstrap/'
CAST='RunScript(service.kodi.ios.bootstrap,cast)'
SPEED='RunScript(service.kodi.ios.bootstrap,speed)'
PICTURE='RunScript(service.kodi.ios.bootstrap,picture_page)'   # V1: the Picture menu (picture_page.py)
# Owner-approved Subtitles / Audio menus (tracks.py) instead of Kodi's settings dialogs.
TRACKS='RunScript(service.kodi.ios.bootstrap,tracks,%s)'
NEXT_EPISODE='RunScript(service.kodi.ios.bootstrap,next_episode)'
EPISODE='!String.IsEmpty(VideoPlayer.TVShowTitle) + !String.IsEmpty(VideoPlayer.Episode)'
CONTINUE='plugin://plugin.video.kodi.ios.watch/?action=continue&type=all'
# Board 08 (U.6): Info opens the episode card (pages.info_card) over the controls; Fuse's action closed the controls
# and waited for TMDb Helper's details page.
INFO='ActivateWindow(1193)'
# The row's list is only fetched once Continue Watching is tapped (its path is empty until then), so opening the
# controls during playback does not start the watch add-on every time.
PANEL='Skin.HasSetting(ios_osd_continue)'
SIDE=168            # 63 pt in from each edge, as the reference
SIZES=(112,170,246) # glass circles drawn by portrait.textures()

def e(text):return escape(str(text),{'"':'&quot;'})

def image(x,y,w,h,texture,color='FFFFFFFF',extra='',border=''):
 return ('<control type="image"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>'
         '<texture%s colordiffuse="%s">%s</texture>%s</control>')%(x,y,w,h,' border="%s"'%border if border else '',color,texture,extra)

def label(x,y,w,h,text,font,color='FFFFFFFF',align='left',extra=''):
 return ('<control type="label"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font>'
         '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><label>%s</label>%s</control>')%(x,y,w,h,font,color,align,e(text),extra)

def button(id,x,y,w,h,actions,text='',font='font_midi_bold',extra=''):
 """A frosted capsule (circle when w == h); the light focus ring is how a tap shows."""
 tex=MEDIA+'glass_%d.png'%h
 clicks=''.join('<onclick>%s</onclick>'%e(a) for a in actions)
 return ('<control type="button" id="%d"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>'
         '<label>%s</label><font>%s</font><textcolor>FFFFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor>'
         '<align>center</align><aligny>center</aligny>'
         '<texturefocus border="%d" colordiffuse="FFFFFFFF">%s</texturefocus><texturenofocus border="%d" colordiffuse="E6FFFFFF">%s</texturenofocus>'
         '%s%s</control>')%(id,x,y,w,h,e(text),font,h//2,tex,h//2,tex,clicks,extra)

def glyph(cx,cy,size,name,extra=''):
 return image(cx-size//2,cy-size//2,size,size,name if '://' in name else ICONS+name,'FFFFFFFF','<aspectratio>keep</aspectratio>'+extra)

def circle(id,x,y,size,name,action,glyph_size=None,extra='',over=''):
 g=glyph_size or size*44//100
 return button(id,x,y,size,size,[action],extra=extra)+glyph(x+size//2,y+size//2,g,name)+over

def tap(id,cx,cy,size,name,action,nav='',glyph_size=None,extra=''):
 """A plain white glyph with an invisible touch area around it (the Apple TV player has no button shapes);
 the glyph dims slightly when the control has focus, so a tap still shows."""
 g=glyph_size or size*6//10
 return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
         '<texturefocus /><texturenofocus /><onclick>%s</onclick>%s%s</control>')%(id,cx-size//2,cy-size//2,size,size,e(action),nav,extra)+\
        glyph(cx,cy,g,name,'<animation effect="fade" start="100" end="70" time="0" condition="Control.HasFocus(%d)">Conditional</animation>'%id)

def text_button(id,x,y,w,h,label_text,actions,nav=''):
 clicks=''.join('<onclick>%s</onclick>'%e(a) for a in actions)
 return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><label>%s</label>'
         '<font>font_midi_bold</font><textcolor>D9FFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>left</align><aligny>center</aligny>'
         '<textoffsetx>0</textoffsetx><texturefocus /><texturenofocus />%s%s</control>')%(id,x,y,w,h,e(label_text),clicks,nav)

def group(anchor,width,body,extra=''):
 """A group pinned to the screen's centre or right edge, so the layout holds whichever landscape width Kodi gives
 the window (1080i has 16:9 = 1920 and 19.5:9 = 2340 layouts, and a window loaded upright gets the 16:9 one)."""
 where={'centre':'<centerleft>50%%</centerleft><width>%d</width>'%width,'right':'<right>0</right><width>%d</width>'%width,
        'left':'<left>0</left><width>%d</width>'%width}[anchor]
 return '<control type="group">%s%s%s</control>'%(where,extra,body)

# Settings › Customisation › Video Controls › Hide Controls After (Fuse's OSD_Timeout, in seconds): the controls close
# that long after they open or after the last tap, unless paused or Continue Watching is open. Empty or 0 = never.
# ISSUE-279 (owner, build 430: "it sits there forever"): Fuse ships it empty, so the controls never hid. The first time
# the controls open it becomes DEFAULT_TIMEOUT seconds, once (ios_osd_timeout_default), so emptying it later still
# means never.
TIMEOUT='Skin.String(OSD_Timeout)'
DEFAULT_TIMEOUT=5
DEFAULTED='Skin.HasSetting(ios_osd_timeout_default)'
DEFAULT_ONLOAD=(('String.IsEmpty(%s) + !%s'%(TIMEOUT,DEFAULTED),'Skin.SetString(OSD_Timeout,%d)'%DEFAULT_TIMEOUT),
                ('!%s'%DEFAULTED,'Skin.SetBool(ios_osd_timeout_default)'))
ARM_WHEN='!String.IsEmpty(%s) + !String.IsEqual(%s,0) + !Player.Paused + !Skin.HasSetting(ios_osd_continue)'%(TIMEOUT,TIMEOUT)
# ISSUE-279 (owner: "if i tap outside of the pause or play or skip it should hide the menu anywhere i tap"; log 72b62563:
# ten taps on no control, "control 0 (not handled)"): a clear button under everything closes the controls, as a tap
# does in Apple's player. Drawn first, so every real control is above it and keeps its own taps.
BACKDROP=('<control type="button" id="7100"><left>0</left><top>0</top><right>0</right><bottom>0</bottom>'
          '<texturefocus /><texturenofocus /><label></label><onclick>Dialog.Close(videoosd)</onclick></control>')
ARM=('CancelAlarm(osd_timeout,true)','AlarmClock(osd_timeout,Dialog.Close(videoosd),$INFO[%s,00:,],silent)'%TIMEOUT)
def rearm(xml):
 tags=''.join('<onclick condition="%s">%s</onclick>'%(e(ARM_WHEN),e(a)) for a in ARM)
 return re.sub(r'(<control type="button" id="\d+">)',lambda m:m.group(1)+tags,xml)

def window():
 """Layout from the owner's reference (Apple TV player, landscape): back top left; AirPlay / audio / subtitles /
 speed top right; back 10, play-pause, forward 10 in the centre; the title, a thin bar with a white knob and the
 time left at the bottom; Info and Continue Watching as text below. No button shapes, no volume. Everything is
 pinned to the left edge, the centre or the right edge (r3): coordinates below are inside those groups. r4: the GUI
 covers the whole screen during video (Kodi app r18, no safe-area box), so the margins keep the controls clear of the
 rounded corners and the Dynamic Island."""
 left=EDGE;top=110
 back=tap(7101,left+75,top,150,'chevron-left.png','PlayerControl(Stop)','<onright>7124</onright><ondown>7112</ondown>',104)
 # Build 206 (owner, build 205: "i want a button at the top to watch next episode"): next to back, only for episodes
 # (the top right holds the four icons; a centred button would meet them on the 16:9 layout).
 back+=('<control type="group"><visible>%s</visible>'%EPISODE+
        text_button(7103,left+170,top-75,420,150,'Next Episode  ›',[NEXT_EPISODE],'<onleft>7101</onleft><onright>7124</onright><ondown>7112</ondown>')+
        '</control>')
 # Right group, 900 wide: speed, audio, subtitles, AirPlay from left to right, the last 90 in from the edge.
 # DEC-039/042 (video-picture-mockups round 4): Picture (wand) is the fifth icon, left of speed.
 rw=1080;rx=rw-EDGE
 icons=''.join(tap(id,rx-75-i*180,top,150,icon,action,nav,74 if icon.endswith('airplay.png') else 96) for i,(id,icon,action,nav) in enumerate([
   (7102,MEDIA+'airplay.png',CAST,'<onleft>7123</onleft><ondown>7112</ondown>'),
   (7123,'closed-captioning.png',TRACKS%'subtitles','<onleft>7122</onleft><onright>7102</onright><ondown>7112</ondown>'),
   (7122,'file-waveform.png',TRACKS%'audio','<onleft>7121</onleft><onright>7123</onright><ondown>7112</ondown>'),
   (7121,'gauge-high.png',SPEED,'<onleft>7124</onleft><onright>7122</onright><ondown>7112</ondown>'),
   (7124,'wand-magic-sparkles.png',PICTURE,'<onleft>7101</onleft><onright>7121</onright><ondown>7112</ondown>')]))
 head=back+group('right',rw,icons)
 # Centre row in a group 1200 wide centred on the screen; the "10" sits inside the arrows ($NUMBER: a bare 10
 # would be read as a Kodi string id).
 cw=1200;cx=cw//2;cy=520;gap=420
 ten=lambda x:label(x-70,cy-36,140,72,'$NUMBER[10]','font_main_bold','FFFFFFFF','center')
 centre=group('centre',cw,
  tap(7111,cx-gap,cy,240,'rotate-left.png','Seek(-10)','<onright>7112</onright><onup>7101</onup><ondown>7131</ondown>',160)+ten(cx-gap)+
  '<control type="button" id="7112"><left>%d</left><top>%d</top><width>260</width><height>260</height><texturefocus /><texturenofocus />'
  '<onclick>PlayerControl(Play)</onclick><onleft>7111</onleft><onright>7113</onright><onup>7101</onup><ondown>7131</ondown></control>'%(cx-130,cy-130)+
  glyph(cx+10,cy,150,'play.png','<visible>Player.Paused | Player.Forwarding | Player.Rewinding</visible>')+
  glyph(cx,cy,140,'pause.png','<visible>!Player.Paused + !Player.Forwarding + !Player.Rewinding</visible>')+
  tap(7113,cx+gap,cy,240,'rotate-right.png','Seek(10)','<onleft>7112</onleft><onup>7102</onup><ondown>7131</ondown>',160)+ten(cx+gap)+
  # Build 210: the buffer percentage lives here, in the controls already on screen while seeking. Its own dialog
  # (Custom_1156) froze Kodi's main thread each time it opened (logs 34cd7aac 15:07:09, 3efdc5ca 15:53:08).
  label(cx-300,cy+150,600,64,'Buffering $INFO[Player.CacheLevel]%','font_main_bold','FFFFFFFF','center','<visible>Player.Caching</visible>')+
  # Board 05 (DEC-036): the buffer fill as a thin bar under the words (the cache level is the only number Kodi has).
  '<control type="progress"><left>%d</left><top>%d</top><width>360</width><height>11</height><info>Player.CacheLevel</info><visible>Player.Caching</visible>'
  '<texturebg border="6" colordiffuse="33FFFFFF">%sdot.png</texturebg><lefttexture /><midtexture border="6" colordiffuse="FF0A84FF">%sdot.png</midtexture><righttexture /></control>'%(cx-180,cy+222,MEDIA,MEDIA),
  '<visible>!%s</visible>'%PANEL)
 # Title: the film, or the show and the episode.
 title=('<control type="label"><left>%d</left><right>%d</right><top>770</top><height>90</height><font>font_title_midi</font>'
  '<textcolor>FFFFFFFF</textcolor><align>left</align><aligny>center</aligny><label>%s</label><visible>!%s</visible></control>')%(
  left,left,e('$INFO[VideoPlayer.TVShowTitle,,  ·  ]$INFO[VideoPlayer.Title]'),PANEL)
 # Thin bar with a white knob (drag to seek), time left under its right end.
 bar=('<control type="group"><left>%d</left><right>%d</right><top>862</top><height>60</height>'%(left,left)+
  # Track and fill in one control (same height and place), the knob from a slider whose bar is an invisible
  # picture of the slider's height (Kodi sizes the knob from the bar picture).
  '<control type="progress"><left>0</left><right>0</right><top>25</top><height>10</height><info>Player.Progress</info>'
  '<texturebg border="4" colordiffuse="59FFFFFF">%sdot.png</texturebg><lefttexture />'
  '<midtexture border="4" colordiffuse="FFFFFFFF">%sdot.png</midtexture><righttexture /></control>'%(MEDIA,MEDIA)+
  '<control type="slider" id="7131"><left>0</left><right>0</right><top>6</top><height>48</height><action>seek</action><texturesliderbar>%sclear48.png</texturesliderbar>'%MEDIA+
  '<textureslidernib colordiffuse="FFFFFFFF">%sknob.png</textureslidernib><textureslidernibfocus colordiffuse="FFFFFFFF">%sknob.png</textureslidernibfocus>'
  '<onup>7112</onup><ondown>7141</ondown></control>'%(MEDIA,MEDIA)+
  '</control>'+
  '<control type="label"><right>%d</right><width>400</width><top>936</top><height>60</height><font>font_midi</font><textcolor>D9FFFFFF</textcolor>'
  '<align>right</align><aligny>center</aligny><label>-$INFO[Player.TimeRemaining]</label></control>'%left)
 row=(text_button(7141,left,936,140,60,'Info',[INFO],'<onright>7142</onright><onup>7131</onup>')+
      text_button(7142,left+200,936,460,60,'Continue Watching',['Skin.ToggleSetting(ios_osd_continue)','Skin.SetString(ios_osd_continue_path,%s)'%CONTINUE],'<onleft>7141</onleft><onup>7201</onup>'))
 panel=('<control type="group"><visible>%s</visible>'%PANEL+
  '<animation effect="fade" start="0" end="100" time="200">Visible</animation>'+
  label(left,520,1200,60,'Continue Watching','font_head_bold')+
  label(left,590,1400,60,'Nothing in progress yet','font_main','99FFFFFF','left','<visible>Integer.IsEqual(Container(7201).NumItems,0) + !Container(7201).IsUpdating</visible>')+
  '<control type="list" id="7201"><left>%d</left><right>%d</right><top>590</top><height>270</height><orientation>horizontal</orientation>'%(left,left)+
  '<ondown>7131</ondown><onup>7101</onup><scrolltime tween="cubic" easing="out">300</scrolltime>'
  '<itemlayout width="420" height="270">%s</itemlayout><focusedlayout width="420" height="270">%s</focusedlayout>'
  '<content target="videos">$INFO[Skin.String(ios_osd_continue_path)]</content></control></control>')%(card(False),card(True))
 shade=('<control type="image"><left>0</left><top>0</top><right>0</right><bottom>0</bottom><texture colordiffuse="59000000">%swhite.png</texture></control>'
  '<control type="image"><left>0</left><top>0</top><right>0</right><height>360</height><texture colordiffuse="B3FFFFFF">%sfade_down.png</texture></control>'
  '<control type="image"><left>0</left><bottom>0</bottom><right>0</right><height>520</height><texture colordiffuse="E6FFFFFF">%sfade_up.png</texture></control>')%(MEDIA,MEDIA,MEDIA)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window>\n<defaultcontrol always="true">7112</defaultcontrol>'
  '<animation effect="fade" start="0" end="100" time="150">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation>'
  '<onunload>Skin.Reset(ios_osd_continue)</onunload><onunload>Skin.Reset(ios_osd_continue_path)</onunload><onunload>CancelAlarm(osd_timeout,true)</onunload>'
  +''.join('<onload condition="%s">%s</onload>'%(e(c),e(a)) for c,a in DEFAULT_ONLOAD)
  +''.join('<onload condition="%s">%s</onload>'%(e(ARM_WHEN),e(a)) for a in ARM)+
  '<controls>%s%s</controls>\n</window>\n')%(MARKER,BACKDROP,rearm(shade+head+centre+title+bar+row+panel))

# r4: never shown. The owner does not want a bar besides the controls' own ("the old one still appears"): the
# window stays because Kodi opens it while seeking and moves its progress control (401).
SEEKING='false'

def seekbar_window():
 """Kodi's seek bar window (DialogSeekBar.xml), replacing Fuse's: kept for Kodi, never visible."""
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s seek bar -->\n<window>\n<zorder>0</zorder><visible>false</visible>'
  '<controls><control type="progress" id="401"><left>0</left><top>0</top><width>1</width><height>1</height><visible>false</visible></control></controls>\n</window>\n')%MARKER

def card(focused):
 art='$INFO[ListItem.Art(landscape)]'
 return (image(0,0,396,223,MEDIA+'white.png','FF1C1C1E',border='')+
  image(0,0,396,223,'$INFO[ListItem.Art(fanart)]','FFFFFFFF','<aspectratio>scale</aspectratio>')+
  image(0,0,396,223,art,'FFFFFFFF','<aspectratio>scale</aspectratio><visible>!String.IsEmpty(ListItem.Art(landscape))</visible>')+
  (image(-6,-6,408,235,MEDIA+'glass_112.png','FFFFFFFF','',border='40') if focused else '')+
  label(0,228,396,40,'$INFO[ListItem.Label]','font_mini_bold','FFFFFFFF' if focused else 'B3FFFFFF'))

def hide_seekbar(original):
 """Fuse's seek bar window stays away while these controls (with their own bar) are up."""
 cond='<visible>!Window.IsActive(videoosd)</visible>'
 if cond in original:return original
 head,sep,rest=original.partition('<window>')
 if not sep:return original
 return head+sep+'\n    '+cond+rest

# Build 191 (owner screenshot): Fuse's own info over the video (Custom_1152, at the start and on pause: title,
# "4K • 1 hr 37 mins", plot, "Ends at"; Custom_1153, the same over the controls; VideoFullScreen's info lines)
# starts 80 units from the edge, under the Dynamic Island. Their controls go into one group inset SAFE from both
# sides; the safe-area frame (navigation.FRAME) stays outside it, or its black bars would cover the video's edges.
INSET=('VideoFullScreen.xml','Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml')
INSET_MARKER='Kodi-iOS player controls: safe-area inset'   # navigation.patch_skin leaves files with this alone

# Build 192 (quick win): Fuse's info over the video repeated the title our controls already show, so it hides while
# the controls are up.
HIDE_UNDER_OSD=('Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml')
def safe_inset(original,hide_under_osd=False):
 """Fuse's landscape window with everything in <controls> moved into a group SAFE in from the left and right."""
 if not original or INSET_MARKER in original:return original
 root=ET.fromstring(original);controls=root.find('controls')
 if root.tag!='window' or controls is None:return original
 group=ET.Element('control',{'type':'group'})
 for key,value in (('description',INSET_MARKER),('left',SAFE),('right',SAFE),('top',0),('bottom',0)):ET.SubElement(group,key).text=str(value)
 if hide_under_osd:ET.SubElement(group,'visible').text='!Window.IsVisible(videoosd)'
 for child in list(controls):
  if child.tag=='control' and child.get('id')=='98400':continue
  controls.remove(child);group.append(child)
 controls.insert(0,group)
 return '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n'

BUFFER_MARKER='Kodi-iOS player controls: buffering pill'   # navigation.patch_skin leaves these alone
BUFFER_WINDOW='Custom_1156_Buffering.xml'
def buffering_window():
 """Build 206 (owner, build 205: "i completely understand if it needs to buffer but have it show like a buffer
 percentage so i know its working"): while Kodi fills its buffer (after a seek, a stall) a pill between the centre
 controls and the title: the spinning ring and "Buffering 45%" (Player.CacheLevel). Its own dialog (as Fuse's info
 over the video), which Kodi opens and closes on its visible condition. Nearly opaque: Kodi cannot blur."""
 w,h=460,84
 spin='<animation effect="rotate" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation>'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window type="dialog" id="1156"><zorder>2</zorder>'
  '<visible>false</visible>'   # build 210: never opens (it froze Kodi); the OSD shows the percentage
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation>'
  '<controls><control type="group"><centerleft>50%%</centerleft><top>668</top><width>%d</width><height>%d</height>'
  '<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><texture border="42" colordiffuse="EB2C2C2E">%sround.png</texture></control>'
  '<control type="image"><left>26</left><top>18</top><width>48</width><height>48</height><texture colordiffuse="FFFFFFFF">%sring.png</texture>%s</control>'
  '<control type="label"><left>92</left><top>0</top><width>%d</width><height>%d</height><font>font_midi</font><textcolor>FFFFFFFF</textcolor>'
  '<align>left</align><aligny>center</aligny><scroll>false</scroll><label>Buffering $INFO[Player.CacheLevel]%%</label></control>'
  '</control></controls></window>\n')%(BUFFER_MARKER,w,h,w,h,MEDIA,MEDIA,spin,w-92-26,h)

def airplay_png(png,size=96):
 """AirPlay glyph: a screen outline open at the bottom, with a triangle rising into it. png: portrait.png."""
 s=size/96.0
 def inside_triangle(x,y):
  # apex (48,54), base y=88 from x=22..74
  ax,ay,by,_,br=48*s,54*s,88*s,22*s,74*s
  if y<ay or y>by:return False
  half=(y-ay)/(by-ay)*(br-ax)
  return ax-half<=x<=ax+half
 def pixel(x,y):
  px,py=x+0.5,y+0.5
  # screen: rounded rectangle 6..90 x 10..70, stroke 7, gap 30..66 on the bottom edge
  l,t,r,b,w,rad=6*s,10*s,90*s,70*s,7*s,10*s
  def in_round(px,py,l,t,r,b,rad):
   if px<l or px>r or py<t or py>b:return False
   cx=min(max(px,l+rad),r-rad);cy=min(max(py,t+rad),b-rad)
   return (px-cx)**2+(py-cy)**2<=rad*rad
  ring=in_round(px,py,l,t,r,b,rad) and not in_round(px,py,l+w,t+w,r-w,b-w,max(rad-w,1))
  if ring and py>b-w-1 and 30*s<px<66*s:ring=False
  on=ring or inside_triangle(px,py)
  return (255,255,255,255 if on else 0)
 return png(size,size,pixel)
