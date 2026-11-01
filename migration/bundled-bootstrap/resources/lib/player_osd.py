"""Video controls (VideoOSD) in the Apple TV player's layout, for Arctic Fuse's landscape (1080i) folder.

Fullscreen video is landscape on the phone, so the controls live in 1080i (2340 x 1080 on an iPhone 16 Pro).
Top left: close and Play on TV (AirPlay icon). Centre: back 10 s, play/pause, forward 10 s. Bottom: the title,
speed / audio / subtitles, the progress bar with time left, then Info and Continue Watching (the in-progress
row). No volume control. Fuse's own seek bar hides while these controls are up, since they carry their own.
"""
from xml.sax.saxutils import escape

MARKER='Kodi-iOS player controls r1'
ICONS='special://skin/extras/icons/'
MEDIA='special://skin/extras/portrait/'
BOOT='special://xbmc/addons/service.kodi.ios.bootstrap/'
CAST='RunScript(%scast.py)'%BOOT
SPEED='RunScript(%sspeed.py)'%BOOT
CONTINUE='plugin://plugin.video.kodi.ios.watch/?action=continue&type=all'
INFO='$VAR[Action_OSD_WikiInfo]'
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

def window():
 top=64
 # Top left: close (stop) and Play on TV.
 head=(circle(7101,SIDE,top,112,'xmark.png','PlayerControl(Stop)',60,'<onright>7102</onright><ondown>7111</ondown>')+
       circle(7102,SIDE+136,top,112,MEDIA+'airplay.png',CAST,54,'<onleft>7101</onleft><ondown>7111</ondown>'))
 # Centre: back 10 s, play / pause, forward 10 s.
 ten=lambda x,y:label(x,y+4,170,170,'$NUMBER[10]','font_tiny_bold','FFFFFFFF','center')
 centre=('<control type="group"><centerleft>50%%</centerleft><centertop>50%%</centertop><width>760</width><height>246</height>'
  '<visible>!%s</visible>'%PANEL+
  circle(7111,0,38,170,'rotate-left.png','Seek(-10)',104,'<onright>7112</onright><onup>7101</onup><ondown>7121</ondown>')+
  ten(0,38)+
  button(7112,257,0,246,246,['PlayerControl(Play)'],extra='<onleft>7111</onleft><onright>7113</onright><onup>7101</onup><ondown>7121</ondown>')+
  glyph(257+123+8,123,104,'play.png','<visible>Player.Paused | Player.Forwarding | Player.Rewinding</visible>')+
  glyph(257+123,123,96,'pause.png','<visible>!Player.Paused + !Player.Forwarding + !Player.Rewinding</visible>')+
  circle(7113,590,38,170,'rotate-right.png','Seek(10)',104,'<onleft>7112</onleft><onup>7102</onup><ondown>7121</ondown>')+
  ten(590,38)+
  '</control>')
 # Bottom left: show and episode (or the film and its year), Apple TV style.
 episode='!String.IsEmpty(VideoPlayer.TVShowTitle)'
 title=('<control type="group"><visible>!%s</visible>'%PANEL+
  label(SIDE,660,1300,56,'$INFO[VideoPlayer.Title]','font_midi_bold','FFFFFFFF','left','<visible>%s</visible>'%episode)+
  label(SIDE,660,1300,56,'$INFO[VideoPlayer.Year]','font_midi_bold','B3FFFFFF','left','<visible>!%s</visible>'%episode)+
  label(SIDE,712,1400,84,'$INFO[VideoPlayer.TVShowTitle]','font_title_main','FFFFFFFF','left','<visible>%s</visible>'%episode)+
  label(SIDE,712,1400,84,'$INFO[VideoPlayer.Title]','font_title_main','FFFFFFFF','left','<visible>!%s</visible>'%episode)+
  '</control>')
 # Bottom right: speed, audio, subtitles in one capsule.
 tools=('<control type="group"><right>%d</right><top>680</top><width>417</width><height>112</height><visible>!%s</visible>'%(SIDE,PANEL)+
  image(0,0,417,112,MEDIA+'glass_112.png','E6FFFFFF',border=56)+
  ''.join('<control type="button" id="%d"><left>%d</left><top>0</top><width>139</width><height>112</height><texturefocus colordiffuse="33FFFFFF" border="40">%sglass_112.png</texturefocus><texturenofocus /><onclick>%s</onclick>%s</control>'
          %(7121+i,i*139,MEDIA,e(action),nav)+glyph(i*139+70,56,52,icon)
          for i,(icon,action,nav) in enumerate([
           ('gauge-high.png',SPEED,'<onright>7122</onright><onup>7113</onup><ondown>7141</ondown>'),
           ('file-waveform.png','ActivateWindow(osdaudiosettings)','<onleft>7121</onleft><onright>7123</onright><onup>7113</onup><ondown>7141</ondown>'),
           ('closed-captioning.png','ActivateWindow(osdsubtitlesettings)','<onleft>7122</onleft><onup>7113</onup><ondown>7141</ondown>')]))+
  '</control>')
 # Progress: elapsed, the bar (drag to seek), time left.
 bar=('<control type="group"><left>%d</left><right>%d</right><top>820</top><height>60</height>'%(SIDE,SIDE)+
  label(0,0,150,60,'$INFO[Player.Time]','font_main_bold','B3FFFFFF','left')+
  '<control type="group"><left>170</left><right>170</right>'
  '<control type="image"><left>0</left><right>0</right><top>22</top><height>16</height><texture border="8" colordiffuse="59FFFFFF">%sdot.png</texture></control>'%MEDIA+
  '<control type="progress"><left>0</left><right>0</right><top>22</top><height>16</height><info>Player.Progress</info><texturebg /><lefttexture />'
  '<midtexture border="8" colordiffuse="FFEBEBEB">%sdot.png</midtexture><righttexture /></control>'%MEDIA+
  '<control type="slider" id="7131"><left>0</left><right>0</right><top>0</top><height>60</height><action>seek</action><texturesliderbar /><textureslidernib /><textureslidernibfocus />'
  '<onup>7121</onup><ondown>7141</ondown></control>'
  '</control>'+
  '<control type="label"><right>0</right><width>150</width><top>0</top><height>60</height><font>font_main_bold</font><textcolor>B3FFFFFF</textcolor>'
  '<align>right</align><aligny>center</aligny><label>-$INFO[Player.TimeRemaining]</label></control>'
  '</control>')
 # Bottom row: Info (Fuse's details page), Continue Watching (the in-progress row, shown above).
 row=(button(7141,SIDE,916,190,112,[INFO],'Info','font_midi_bold','<onright>7142</onright><onup>7131</onup>')+
      button(7142,SIDE+214,916,470,112,['Skin.ToggleSetting(ios_osd_continue)'],'Continue Watching','font_midi_bold','<onleft>7141</onleft><onup>7201</onup>'))
 panel=('<control type="group"><visible>%s</visible>'%PANEL+
  '<animation effect="fade" start="0" end="100" time="200">Visible</animation>'+
  label(SIDE,470,1200,60,'Continue Watching','font_head_bold')+
  label(SIDE,540,1400,60,'Nothing in progress yet','font_main','99FFFFFF','left','<visible>Integer.IsEqual(Container(7201).NumItems,0) + !Container(7201).IsUpdating</visible>')+
  '<control type="list" id="7201"><left>%d</left><right>0</right><top>540</top><height>270</height><orientation>horizontal</orientation>'%SIDE+
  '<ondown>7142</ondown><onup>7101</onup><scrolltime tween="cubic" easing="out">300</scrolltime>'
  '<itemlayout width="420" height="270">%s</itemlayout><focusedlayout width="420" height="270">%s</focusedlayout>'
  '<content target="videos">%s</content></control></control>')%(card(False),card(True),e(CONTINUE))
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window>\n<defaultcontrol always="true">7112</defaultcontrol>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="200">WindowClose</animation>'
  '<onunload>Skin.Reset(ios_osd_continue)</onunload><onunload>CancelAlarm(osd_timeout,true)</onunload>'
  '<controls>%s%s%s%s%s%s%s%s</controls>\n</window>\n')%(
   MARKER,'<control type="image"><left>0</left><top>0</top><right>0</right><bottom>0</bottom><texture colordiffuse="73000000">%swhite.png</texture></control>'%MEDIA,head,centre,title,tools,bar,row,panel)

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

def airplay_png(png,size=96):
 """AirPlay glyph: a screen outline open at the bottom, with a triangle rising into it. png: portrait.png."""
 s=size/96.0
 def inside_triangle(x,y):
  # apex (48,54), base y=88 from x=22..74
  ax,ay,by,bl,br=48*s,54*s,88*s,22*s,74*s
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
