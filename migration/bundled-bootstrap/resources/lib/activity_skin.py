"""Skin files for the activity pill (activity.py publishes what they show):

- portrait/Custom_1187_Activity.xml: the pill, a modeless dialog that opens by itself while something runs (like
  Fuse's header overlay 1182). Above the tab bar on Home/Movies/TV/Library/Search, at the bottom of every other
  page, compact at the top over full-screen pages (Umbrella's getting-ready, Choose a version). Tap: Activity sheet.
- 1080i/Custom_1187_Activity.xml: over video, compact and only while the video controls are up.
- portrait/ and 1080i/DialogExtendedProgressBar.xml: Kodi's own background progress box, drawn invisible. Kodi still
  fills its heading (30), text (31) and progress (32), which activity.py reads; nothing of it is ever drawn.
- portrait/IOSActivity.xml: the Activity sheet (activity_page.py), every job with its own bar.
"""
import math
ID=1187
NAME='Custom_1187_Activity.xml'
SHEET='IOSActivity.xml'
BOX='DialogExtendedProgressBar.xml'
# By add-on id, as every page of the setup add-on (ISSUE-071; default.py runs the page).
OPEN='RunScript(service.kodi.ios.bootstrap,activity_page)'
PAUSE='RunScript(service.kodi.ios.bootstrap,activity_page,pause)'
ROWS=6
# navigation.patch_skin and the portrait refresh both leave files with this marker alone (see pages.play_on_tv).
LANDSCAPE_MARKER='Kodi-iOS player controls: activity'
P=lambda k:'$INFO[Window(Home).Property(Activity.%s)]'%k
HAS=lambda k:'!String.IsEmpty(Window(Home).Property(Activity.%s))'%k
IS=lambda k,v:'String.IsEqual(Window(Home).Property(Activity.%s),%s)'%(k,v)
TABS='Window.IsActive(home) | Window.IsActive(1103) | Window.IsActive(1104) | Window.IsActive(1105)'
FULL='Window.IsVisible(source_progress.xml) | Window.IsVisible(DeckSourceSelect.xml)'
# Never over: the bell's page and the Activity sheet (they list the same), the keyboard, start-up, a slideshow, and
# alerts (modal dialogs), except the full-screen pages above, which are modal too.
HIDE=('Window.IsVisible(IOSNotifications.xml) | Window.IsVisible(%s) | Window.IsActive(virtualkeyboard) | Window.IsActive(numericinput)'
      ' | Window.IsVisible(startup) | Window.IsVisible(1198) | Window.IsActive(slideshow) | Window.IsActive(fullscreenvideo)'
      ' | [System.HasActiveModalDialog + ![%s]]')%(SHEET,FULL)
VISIBLE='%s + ![%s]'%(HAS('Show'),HIDE)

def arc(p,size,stroke,frac):
 """A ring filled clockwise from 12 o'clock to `frac` (white, tinted by colordiffuse)."""
 c=size/2.0;r=c-stroke/2.0-1
 def pixel(x,y):
  dx,dy=x+0.5-c,y+0.5-c;d=math.hypot(dx,dy)
  a=max(0.0,min(1.0,stroke/2.0-abs(d-r)+0.5))
  if a<=0:return (255,255,255,0)
  ang=(math.degrees(math.atan2(dx,-dy))+360)%360
  return (255,255,255,int(255*a)) if frac>=1 or ang<=frac*360 else (255,255,255,0)
 return p.png(size,size,pixel)

def textures(p):
 out={'ring_%02d.png'%k:arc(p,72,9,k/20.0) for k in range(21)}
 # Nearly opaque glass: the standard glass let list rows show through the pill (found in the rig on Settings).
 for h in (170,124,72):out['pill_glass_%d.png'%h]=p.glass(h,h/2,(36,36,40,250),(255,255,255,46))
 out['tile118.png']=p.rounded(118,118,32);out['tile86.png']=p.rounded(86,86,24);out['tile92.png']=p.rounded(92,92,26)
 out['sheet_top.png']=p.png(160,160,lambda x,y:(255,255,255,int(255*p.coverage(x,y,160,320,64))) if y<160 else (0,0,0,0))
 return out

def spinner(p,x,y,size,extra=''):
 return p.image(x,y,size,size,p.MEDIA+'ring.png',p.WHITE,
  '<animation effect="rotate" end="-360" center="auto" time="1100" loop="true" reversible="false" condition="true">Conditional</animation>'+extra)

def tile(p,x,y,size,icon,tint,texture):
 g=int(size*0.54)
 return p.image(x,y,size,size,p.MEDIA+texture,tint)+p.icon(x+(size-g)//2,y+(size-g)//2,g,p.ICONS+icon,p.WHITE)

def full_pill(p,w):
 """The 62 pt pill: app tile with a ring badge (or stacked tiles), title, detail, then %, spinner or pause."""
 h=170;M=p.MEDIA;single='!%s'%HAS('Stack')
 ring_on='[%s | %s | %s]'%(IS('State','progress'),IS('State','paused'),IS('State','done'))
 one=('<control type="group"><visible>%s</visible>'%single+tile(p,26,26,118,P('Icon'),P('Tint'),'tile118.png')+
  '<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(26+118-50,26+118-50,ring_on)+
  p.image(-6,-6,84,84,M+'dot.png','FF2A2A2E')+p.image(0,0,72,72,M+'ring_20.png','40FFFFFF')+
  p.image(0,0,72,72,M+P('Ring'),P('RingTint'))+'</control></control>')
 stack=''.join(('<control type="group"><left>%d</left><top>%d</top><visible>%s + %s</visible>'%(22+i*58,39,HAS('Stack'),HAS('S%d.Icon'%(i+1)))+
  p.image(-7,-7,106,106,M+'tile92.png','FF2A2A2E')+tile(p,0,0,92,P('S%d.Icon'%(i+1)),P('S%d.Tint'%(i+1)),'tile92.png')+'</control>') for i in range(4))
 def texts(x,cond):
  return ('<control type="group"><visible>%s</visible>'%cond+
   p.label(x,30,w-x-210,58,P('Title'),'p_pill',p.WHITE,'left','<scroll>false</scroll>')+
   p.label(x,88,w-x-210,50,P('Sub'),'p_pill_s',p.GREY,'left','<scroll>false</scroll>')+'</control>')
 text=(texts(186,single)+   # clear of the ring badge on the tile
       texts(22+58+92+26,'%s + %s'%(HAS('Stack'),IS('Count','2')))+
       texts(22+2*58+92+26,'%s + %s'%(HAS('Stack'),IS('Count','3')))+
       texts(22+3*58+92+26,'%s + !%s + !%s'%(HAS('Stack'),IS('Count','2'),IS('Count','3'))))
 right=(spinner(p,w-122,(h-72)//2,72,'<visible>%s</visible>'%IS('State','spin'))+
  p.label(w-200,0,170,h,P('Pct')+'%','p_pill','$INFO[Window(Home).Property(Activity.RingTint)]','right',
          '<visible>%s + !%s</visible>'%(IS('State','progress'),HAS('Pause')))+
  p.icon(w-74,(h-40)//2,40,'chevron-right.png',p.GREY,'<visible>%s</visible>'%IS('State','done')))
 pause=('<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(w-134,(h-104)//2,HAS('Pause'))+
  p.image(0,0,104,104,M+'dot.png','26FFFFFF')+
  p.icon(26,26,52,'pause.png',p.WHITE,'<visible>%s</visible>'%IS('Pause','pause'))+
  p.icon(28,26,52,'play.png',p.WHITE,'<visible>%s</visible>'%IS('Pause','resume'))+'</control>')
 return p.image(0,0,w,h,M+'pill_glass_170.png',p.WHITE,border=85)+one+stack+text+right+pause

def compact_pill(p,w):
 h=124;M=p.MEDIA
 return (p.image(0,0,w,h,M+'pill_glass_124.png',p.WHITE,border=62)+
  tile(p,19,19,86,P('Icon'),P('Tint'),'tile86.png')+
  p.label(124,0,w-160,h,'$INFO[Window(Home).Property(Activity.Title)]$INFO[Window(Home).Property(Activity.Pct), · ,%]','p_pill',p.WHITE,'left','<scroll>false</scroll>'))

def pill_window(p):
 """portrait/Custom_1187_Activity.xml."""
 W=p.WIDTH;inset=38;w=W-2*inset;cw=700
 slide=('<animation effect="slide" start="0,60" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
        '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>'
        '<animation effect="fade" start="100" end="0" time="200">WindowClose</animation>')
 body=('<control type="group"><left>%d</left><bottom>196</bottom><width>%d</width><height>170</height><visible>[%s] + ![%s]</visible>%s%s</control>'
       %(inset,w,TABS,FULL,slide,full_pill(p,w))+
       '<control type="group"><left>%d</left><bottom>50</bottom><width>%d</width><height>170</height><visible>![%s] + ![%s]</visible>%s%s</control>'
       %(inset,w,TABS,FULL,slide,full_pill(p,w))+
       '<control type="group"><left>%d</left><top>40</top><width>%d</width><height>124</height><visible>%s</visible>%s%s</control>'
       %((W-cw)//2,cw,FULL,slide.replace('0,60','0,-60'),compact_pill(p,cw)))
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s activity pill -->\n<window type="dialog" id="%d"><visible>%s</visible><zorder>2</zorder>'
         '<controls>%s</controls></window>\n')%(p.MARKER,ID,p.e(VISIBLE),body)

def landscape_pill():
 """1080i/Custom_1187_Activity.xml: Fuse's 1920x1080 canvas and fonts, top centre, only with the video controls."""
 MEDIA='special://skin/extras/portrait/';ICONS='special://skin/extras/icons/'
 visible='%s + Window.IsActive(fullscreenvideo) + Window.IsVisible(videoosd)'%HAS('Show')
 w=520;h=72;x=(1920-w)//2   # centred on the row of round buttons in the video controls (about 107 units down)
 img=lambda x,y,w,h,t,c='FFFFFFFF',extra='',b='':('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
   '<texture%s colordiffuse="%s">%s</texture>%s</control>')%(x,y,w,h,' border="%s"'%b if b else '',c,t,extra)
 body=('<control type="group"><left>%d</left><top>71</top><width>%d</width><height>%d</height>'%(x,w,h)+
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="160">WindowClose</animation>'+
  img(0,0,w,h,MEDIA+'pill_glass_72.png',b='36')+
  img(10,10,52,52,MEDIA+'tile86.png',P('Tint'))+img(22,22,28,28,ICONS+P('Icon'))+
  '<control type="label"><left>76</left><top>0</top><width>%d</width><height>%d</height><font>font_main_bold</font><textcolor>FFFFFFFF</textcolor>'
  '<aligny>center</aligny><label>$INFO[Window(Home).Property(Activity.Title)]$INFO[Window(Home).Property(Activity.Pct), · ,%%]</label></control>'%(w-100,h)+
  '</control>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s (navigation.patch_skin leaves this marker alone) -->\n'
         '<window type="dialog" id="%d"><visible>%s</visible><zorder>2</zorder><controls>%s</controls></window>\n')%(LANDSCAPE_MARKER,ID,visible.replace('&','&amp;'),body)

def hidden_box(marker):
 """Kodi's background progress box, never drawn: its three controls stay so Kodi can fill them (activity.py reads
 them), inside a group that is never visible (so never focusable). No animation, no background, nothing on screen.
 30 and 31 are buttons: Python reads a button's label from Kodi (ControlButton.getLabel); a label or textbox only
 returns what Python itself set (found in the Kodi rig: both always read empty)."""
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: Kodi background progress, drawn by the activity pill instead -->\n'
         '<window><controls><control type="group"><left>-4000</left><top>-4000</top><width>10</width><height>10</height><visible>false</visible>'
         '<control type="button" id="30"><width>900</width><height>10</height><font>%s</font><texturefocus /><texturenofocus /></control>'
         '<control type="button" id="31"><width>900</width><height>10</height><font>%s</font><texturefocus /><texturenofocus /></control>'
         '<control type="progress" id="32"><width>10</width><height>10</height><texturebg /><lefttexture /><midtexture /><righttexture /></control>'
         '</control></controls></window>\n')%(marker,'p_cap' if 'portrait' in marker else 'font_mini','p_cap' if 'portrait' in marker else 'font_mini')

def sheet(p):
 """portrait/IOSActivity.xml: bottom sheet over a dimmed page; rows 9601+ (pause 9611+), progress bars 9621+.
 As tall as its rows: one background per row count, and the content slides up to match (Activity.Count)."""
 W=p.WIDTH;M=p.MEDIA;row=190;head=170;foot=60;x=24;w=W-2*x
 R=lambda n,k:'$INFO[Window(Home).Property(Activity.%d.%s)]'%(n,k)
 H=lambda n,k:'!String.IsEmpty(Window(Home).Property(Activity.%d.%s))'%(n,k)
 Q=lambda n,k,v:'String.IsEqual(Window(Home).Property(Activity.%d.%s),%s)'%(n,k,v)
 rows_of=lambda k:max(1,min(ROWS,k))
 height=lambda k:head+rows_of(k)*row+foot
 count=lambda k:'String.IsEqual(Window(Home).Property(Activity.Count),%d)'%k
 def line(n):
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,row,H(n,'Title'))+
   (p.image(170,0,w-210,2,M+'white.png','1AFFFFFF') if n>1 else '')+
   tile(p,40,(row-112)//2,112,R(n,'Icon'),R(n,'Tint'),'tile118.png')+
   p.label(178,26,w-178-170,56,R(n,'Title'),'p_pill',p.WHITE,'left','<scroll>false</scroll>')+
   p.label(178,84,w-178-170,46,R(n,'Sub'),'p_pill_s',p.GREY,'left','<scroll>false</scroll>')+
   '<control type="progress" id="%d"><left>178</left><top>144</top><width>%d</width><height>12</height><visible>!%s + !%s</visible>'
   '<texturebg border="6" colordiffuse="26FFFFFF">%sdot.png</texturebg><lefttexture /><midtexture border="6" colordiffuse="%s">%sdot.png</midtexture>'
   '<righttexture /></control>'%(9620+n,w-178-170,Q(n,'State','spin'),Q(n,'State','done'),M,R(n,'Bar'),M)+
   '<control type="group"><left>178</left><top>144</top><visible>%s</visible>'%Q(n,'State','spin')+
   p.image(0,0,w-178-170,12,M+'dot.png','26FFFFFF',border=6)+
   p.image(0,0,180,12,M+'dot.png','B3FFFFFF','<animation effect="slide" start="0,0" end="%d,0" time="1400" loop="true" reversible="false" condition="true">Conditional</animation>'%(w-178-170-180),border=6)+
   '</control>'+
   p.icon(w-120,(row-56)//2,56,'circle-check.png','FF30D158','<visible>%s</visible>'%Q(n,'State','done'))+
   '<control type="group"><left>%d</left><top>%d</top><visible>%s</visible>'%(w-150,(row-96)//2,H(n,'Pause'))+
   '<control type="button" id="%d"><width>96</width><height>96</height><label></label><texturefocus colordiffuse="40FFFFFF">%sdot.png</texturefocus>'
   '<texturenofocus colordiffuse="26FFFFFF">%sdot.png</texturenofocus><onup>%d</onup><ondown>%d</ondown></control>'%(9610+n,M,M,9610+n-1 if n>1 else 9600,9610+n+1)+
   p.icon(22,22,52,'pause.png',p.WHITE,'<visible>%s</visible>'%Q(n,'Pause','pause'))+
   p.icon(24,22,52,'play.png',p.WHITE,'<visible>%s</visible>'%Q(n,'Pause','resume'))+'</control></control>')
 empty=('<control type="group"><width>%d</width><height>%d</height><visible>String.IsEmpty(Window(Home).Property(Activity.1.Title))</visible>'%(w,row)+
        p.label(0,40,w,90,'Nothing running right now','p_h3',p.GREY,'center')+'</control>')
 base=p.HEIGHT-24-height(1)
 # Backgrounds: one per row count (bottom edge fixed); 0 rows uses the one-row size with the empty message.
 backs=''.join(p.image(x,p.HEIGHT-24-height(k),w,height(k),M+'alert.png',p.WHITE,
                       '<visible>%s</visible>'%(count(k) if k>1 else '![%s]'%' | '.join(count(j) for j in range(2,ROWS+1))),border=40)
               for k in range(1,ROWS+1))
 rise=''.join('<animation effect="slide" start="0,0" end="0,-%d" time="0" condition="%s">Conditional</animation>'%((k-1)*row,count(k)) for k in range(2,ROWS+1))
 content=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s'%(x,base,w,height(ROWS),rise)+
  p.image((w-100)//2,22,100,14,M+'dot.png','4DFFFFFF',border=7)+
  p.label(48,56,w-400,90,'Activity','p_h2')+
  '<control type="button" id="9600"><left>%d</left><top>56</top><width>240</width><height>90</height><label>Done</label><font>p_btn</font>'
  '<textcolor>FF0A84FF</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>right</align><aligny>center</aligny><textoffsetx>0</textoffsetx>'
  '<texturefocus /><texturenofocus /><ondown>9611</ondown></control>'%(w-288)+
  '<control type="grouplist" id="9300"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%(head,w,ROWS*row)+''.join(line(n) for n in range(1,ROWS+1))+empty+'</control></control>')
 anim=('<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
       '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>')%(height(ROWS),height(ROWS))
 body=('<control type="button" id="9099"><width>%d</width><height>%d</height><texturefocus colordiffuse="73000000">%swhite.png</texturefocus>'
       '<texturenofocus colordiffuse="73000000">%swhite.png</texturenofocus><onclick>Close</onclick></control>'%(W,p.HEIGHT,M,M)+
       '<control type="group">%s%s%s</control>'%(anim,backs,content))
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s activity sheet -->\n<window><defaultcontrol always="true">9600</defaultcontrol>'
         '<controls>%s</controls></window>\n')%(p.MARKER,body)

# Kodi gives taps and keys only to the active window or a modal dialog, never to a modeless one like the pill
# (CGUIWindowManager::HandleAction; found in the rig: taps on the pill reached Home). So every portrait page gets
# two invisible buttons exactly where the pill is drawn, shown only while it is: tap = Activity sheet, the
# round button on the right = pause or resume. The modeless pill itself can never take focus from the page.
TAB_PAGES={'Home.xml','Custom_1101_Hub.xml','Custom_1102_Hub.xml','Custom_1103_Hub.xml','Custom_1104_Hub.xml','Custom_1105_Search.xml'}
FULL_PAGES={'source_progress.xml','DeckSourceSelect.xml'}
SKIP={NAME,SHEET,BOX,'IOSNotifications.xml','Font.xml','Includes.xml','Custom_1182_Dialog_Topmenu_Overlay.xml','Startup.xml',
      'Custom_1198_Dialog_Startup.xml'}
MARK='<!-- activity pill tap -->'

def tap_controls(p,name):
 W=p.WIDTH;inset=38;w=W-2*inset
 btn=lambda id,extra,action:('<control type="button" id="%d">%s<label></label><texturefocus /><texturenofocus /><onclick>%s</onclick></control>'
                             %(id,extra,p.e(action)))
 if name in FULL_PAGES:
  cw=700
  return ('<control type="group"><left>%d</left><top>40</top><width>%d</width><height>124</height><visible>%s</visible>'%((W-cw)//2,cw,p.e(VISIBLE))+
          btn(9791,'<width>%d</width><height>124</height>'%cw,OPEN)+'</control>')
 place='<bottom>196</bottom>' if name in TAB_PAGES else '<bottom>50</bottom>'
 return ('<control type="group"><left>%d</left>%s<width>%d</width><height>170</height><visible>%s</visible>'%(inset,place,w,p.e(VISIBLE))+
         btn(9791,'<width>%d</width><height>170</height>'%w,OPEN)+
         btn(9792,'<left>%d</left><top>33</top><width>104</width><height>104</height><visible>%s</visible>'%(w-134,p.e(HAS('Pause'))),PAUSE)+'</control>')

def inject(p,name,data):
 """The page's XML with the pill's tap area as its last (topmost) control. Dialogs other than the full-screen pages
 are left alone (the pill hides over them)."""
 if name in SKIP or not name.endswith('.xml'):return data
 text=data.decode('utf-8') if isinstance(data,bytes) else data
 head=text[:400]
 dialog='type="dialog"' in head or (name.startswith('Dialog') and name not in FULL_PAGES)
 if (dialog and name not in FULL_PAGES) or MARK in text:return data
 end=text.rfind('</controls>')
 if end<0:return data
 out=text[:end]+MARK+tap_controls(p,name)+text[end:]
 return out.encode('utf-8') if isinstance(data,bytes) else out

def files(p):
 out={p.FOLDER+'/'+NAME:pill_window(p),'1080i/'+NAME:landscape_pill(),
      p.FOLDER+'/'+BOX:hidden_box('Kodi-iOS portrait '+p.REVISION),'1080i/'+BOX:hidden_box(LANDSCAPE_MARKER),
      p.FOLDER+'/'+SHEET:sheet(p)}
 out={k:v.encode() for k,v in out.items()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
