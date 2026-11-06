"""Skin files for the activity pill (activity.py publishes what they show):

- portrait/Custom_1187_Activity.xml: the pill, a modeless dialog that opens by itself while something runs (like
  Fuse's header overlay 1182). Above the tab bar on Home/Movies/TV/Library/Search, at the bottom of every other
  page, compact at the top over full-screen pages (Umbrella's getting-ready, Choose a version). Tap: Activity sheet.
- 1080i/Custom_1187_Activity.xml: over video, compact and only while the video controls are up.
- portrait/ and 1080i/DialogExtendedProgressBar.xml: Kodi's own background progress box, drawn invisible. Kodi still
  fills its heading (30), text (31) and progress (32), which activity.py reads; nothing of it is ever drawn.
- portrait/IOSActivity.xml: the Activity sheet (activity_page.py): jobs grouped by kind, each with its ring.

Look: round-4 mockup approved by the owner (DEC-027; docs/design/activity-mockups-r4.html): progress is a ring
around the app tile in both pill and sheet, every control has a 118-unit (44 pt) touch area, Close instead of Done.
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
MAX_HEADS=5   # kinds of job in the sheet (activity.KINDS)
# navigation.patch_skin and the portrait refresh both leave files with this marker alone (see pages.play_on_tv).
LANDSCAPE_MARKER='Kodi-iOS player controls: activity'
P=lambda k:'$INFO[Window(Home).Property(Activity.%s)]'%k
HAS=lambda k:'!String.IsEmpty(Window(Home).Property(Activity.%s))'%k
IS=lambda k,v:'String.IsEqual(Window(Home).Property(Activity.%s),%s)'%(k,v)
TABS='Window.IsActive(home) | Window.IsActive(1103) | Window.IsActive(1104) | Window.IsActive(1105)'
FULL='Window.IsVisible(source_progress.xml) | Window.IsVisible(DeckSourceSelect.xml)'
# Never over: the bell's page and the Activity sheet (they list the same), the keyboard, start-up, a slideshow, and
# alerts (modal dialogs), except the full-screen pages above, which are modal too.
HIDE=('Window.IsVisible(IOSNotifications.xml) | Window.IsVisible(IOSLibraryStatus.xml) | Window.IsVisible(%s) | Window.IsActive(virtualkeyboard) | Window.IsActive(numericinput)'
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

RING=140;TILE=108;HIT=118;DISC=92   # ring tile 52 pt around a 40 pt tile; touch areas 44 pt, drawn discs 34 pt

def corner_texture(p,size,radius,top,bottom):
 """White rounded square with only the chosen ends rounded (nine-sliced with border=radius). One rounded end is the
 matching half of a rectangle twice as tall, so the other end's corners fall outside the texture."""
 if top and bottom:cover=lambda x,y:p.coverage(x,y,size,size,radius)
 elif top:cover=lambda x,y:p.coverage(x,y,size,2*size,radius)
 else:cover=lambda x,y:p.coverage(x,y+size,size,2*size,radius)
 return p.png(size,size,lambda x,y:(255,255,255,int(255*cover(x,y))))

def textures(p):
 out={'ring_%02d.png'%k:arc(p,RING,10,k/20.0) for k in range(21)}
 # Nearly opaque glass: the standard glass let list rows show through the pill (found in the rig on Settings).
 for h in (170,124,72):out['pill_glass_%d.png'%h]=p.glass(h,h/2,(36,36,40,250),(255,255,255,46))
 out['tile108.png']=p.rounded(TILE,TILE,27);out['tile86.png']=p.rounded(86,86,24);out['tile92.png']=p.rounded(92,92,26)
 # Sheet: top corners 38 pt (102 units); grouped rows: 16 pt (43 units) on the group's outer corners only.
 out['sheet_bg.png']=corner_texture(p,240,102,True,False)
 for name,top,bottom in (('row_only',True,True),('row_first',True,False),('row_last',False,True)):out[name+'.png']=corner_texture(p,160,43,top,bottom)
 return out

def tile(p,x,y,size,icon,tint,texture):
 g=int(size*0.54)
 return p.image(x,y,size,size,p.MEDIA+texture,tint)+p.icon(x+(size-g)//2,y+(size-g)//2,g,p.ICONS+icon,p.WHITE)

def ring_tile(p,x,y,ring,ring_tint,icon,tint,ring_on,spin_on,art='',art_on='false'):
 """The app tile inside its progress ring: filled clockwise to the job's percentage (ring_00..ring_20), or, with no
 percentage, a short arc spinning in the same place (HIG: keep the indicator's place and style)."""
 M=p.MEDIA;o=(RING-TILE)//2
 return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,y,RING,RING)+
  p.image(0,0,RING,RING,M+'ring_20.png','29FFFFFF','<visible>%s | %s</visible>'%(ring_on,spin_on))+
  p.image(0,0,RING,RING,M+ring,ring_tint,'<visible>%s</visible>'%ring_on)+
  p.image(0,0,RING,RING,M+'ring_06.png',ring_tint,'<visible>%s</visible>'%spin_on+
   '<animation effect="rotate" end="-360" center="auto" time="1100" loop="true" reversible="false" condition="true">Conditional</animation>')+
  tile(p,o,o,TILE,icon,tint,'tile108.png')+
  # The poster of what is downloading, over the app tile (which stays as the fallback while it loads).
  (p.image(o,o,TILE,TILE,art,p.WHITE,'<visible>%s</visible>'%art_on,aspect='>scale',diffuse=M+'tile108.png',background=True) if art else '')+
  '</control>')

def round_button(p,id,x,y,glyphs,extra='',navigation=''):
 """A 118-unit (44 pt) touch area with a 92-unit drawn disc and a centred glyph; glyphs: [(icon, condition)]."""
 M=p.MEDIA;d=(HIT-DISC)//2;g=46
 button=('<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />%s</control>'%(id,HIT,HIT,navigation)
         if id else '')
 return ('<control type="group"><left>%d</left><top>%d</top>%s'%(x,y,extra)+
  p.image(d,d,DISC,DISC,M+'dot.png','26FFFFFF')+
  (p.image(d,d,DISC,DISC,M+'dot.png','33FFFFFF','<visible>Control.HasFocus(%d)</visible>'%id) if id else '')+
  ''.join(p.icon((HIT-g)//2,(HIT-g)//2,g,icon,p.WHITE,'<visible>%s</visible>'%cond if cond else '') for icon,cond in glyphs)+
  button+'</control>')

def full_pill(p,w):
 """The 62 pt pill: ring tile (or stacked tiles), title, status line (it starts with the percentage), pause/resume."""
 h=170;M=p.MEDIA;single='!%s'%HAS('Stack')
 ring_on='%s + [%s | %s | %s]'%(single,IS('State','progress'),IS('State','paused'),IS('State','done'))
 spin_on='%s + %s'%(single,IS('State','spin'))
 one=ring_tile(p,14,(h-RING)//2,P('Ring'),P('RingTint'),P('Icon'),P('Tint'),ring_on,spin_on,P('Art'),HAS('Art'))
 stack=''.join(('<control type="group"><left>%d</left><top>%d</top><visible>%s + %s</visible>'%(22+i*58,39,HAS('Stack'),HAS('S%d.Icon'%(i+1)))+
  p.image(-7,-7,106,106,M+'tile92.png','FF2A2A2E')+tile(p,0,0,92,P('S%d.Icon'%(i+1)),P('S%d.Tint'%(i+1)),'tile92.png')+'</control>') for i in range(4))
 right=16+HIT+16   # the pause control's lane, kept clear even when it is hidden
 def texts(x,cond):
  return ('<control type="group"><visible>%s</visible>'%cond+
   p.label(x,28,w-x-right,58,P('Title'),'p_pill',p.WHITE,'left','<scroll>false</scroll>')+
   p.label(x,90,w-x-right,50,P('Sub'),'p_pill_s',p.GREY,'left','<scroll>false</scroll>')+'</control>')
 text=(texts(14+RING+26,single)+
       texts(22+58+92+26,'%s + %s'%(HAS('Stack'),IS('Count','2')))+
       texts(22+2*58+92+26,'%s + %s'%(HAS('Stack'),IS('Count','3')))+
       texts(22+3*58+92+26,'%s + !%s + !%s'%(HAS('Stack'),IS('Count','2'),IS('Count','3'))))
 pause=round_button(p,0,w-16-HIT,(h-HIT)//2,[('pause.png',IS('Pause','pause')),('play.png',IS('Pause','resume'))],'<visible>%s</visible>'%HAS('Pause'))
 return p.image(0,0,w,h,M+'pill_glass_170.png',p.WHITE,border=85)+one+stack+text+pause

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
 """portrait/IOSActivity.xml: a bottom sheet over the dimmed page. Jobs grouped by kind (a header above the first job
 of each kind, Activity.<n>.Head), rows 1..ROWS with pause/resume 9611+, Close 9600, dimmed page 9099.
 As tall as its content: one background per layout (rows_heads, Activity.Layout); the content slides up to match."""
 W=p.WIDTH;M=p.MEDIA;side=43;w=W-2*side;row=196;ghead=84;head=200;foot=90
 R=lambda n,k:'$INFO[Window(Home).Property(Activity.%d.%s)]'%(n,k)
 H=lambda n,k:'!String.IsEmpty(Window(Home).Property(Activity.%d.%s))'%(n,k)
 Q=lambda n,k,v:'String.IsEqual(Window(Home).Property(Activity.%d.%s),%s)'%(n,k,v)
 layouts=[(k,g) for k in range(1,ROWS+1) for g in range(1,min(k,MAX_HEADS)+1)]
 height=lambda k,g:head+k*row+g*ghead+foot
 lay=lambda k,g:IS('Layout','%d_%d'%(k,g))
 small=height(1,0)
 def header(n):
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,ghead,H(n,'Head'))+
   p.label(12,28,w-276,50,R(n,'Head'),'p_foot_b',p.GREY,'left','<scroll>false</scroll>')+
   p.label(w-252,28,240,50,R(n,'HeadCount'),'p_foot',p.GREY,'right')+'</control>')
 def line(n):
  backs=''.join(p.image(0,0,w,row,M+tex,'FF2C2C2E','<visible>%s</visible>'%Q(n,'Pos',pos),border=43) for pos,tex in
                (('only','row_only.png'),('first','row_first.png'),('last','row_last.png'),('mid','white.png')))
  sep=p.image(176,0,w-176,2,M+'white.png',p.SEP,'<visible>%s | %s</visible>'%(Q(n,'Pos','mid'),Q(n,'Pos','last')))
  ring_on='[%s | %s | %s]'%(Q(n,'State','progress'),Q(n,'State','paused'),Q(n,'State','done'))
  nav='<onup>%d</onup><ondown>%d</ondown>'%(9610+n-1 if n>1 else 9600,9610+n+1)
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,row,H(n,'Title'))+backs+sep+
   ring_tile(p,18,(row-RING)//2,R(n,'Ring'),R(n,'Bar'),R(n,'Icon'),R(n,'Tint'),ring_on,Q(n,'State','spin'),R(n,'Art'),H(n,'Art'))+
   p.label(176,30,w-176-240,58,R(n,'Title'),'p_pill',p.WHITE,'left','<scroll>false</scroll>')+
   p.label(176,94,w-176-240,50,R(n,'Sub'),'p_pill_s',p.GREY,'left','<scroll>false</scroll>')+
   p.label(w-236,0,90,row,R(n,'Pct')+'%','p_pill_s',p.GREY,'right','<visible>%s + !%s</visible>'%(H(n,'Pct'),Q(n,'State','done')))+
   round_button(p,9610+n,w-16-HIT,(row-HIT)//2,[('pause.png',Q(n,'Pause','pause')),('play.png',Q(n,'Pause','resume'))],
                '<visible>%s</visible>'%H(n,'Pause'),nav)+'</control>')
 empty=('<control type="group"><width>%d</width><height>%d</height><visible>String.IsEmpty(Window(Home).Property(Activity.1.Title))</visible>'%(w,row)+
        p.label(0,40,w,90,'Nothing running right now','p_h3',p.GREY,'center')+'</control>')
 others=' | '.join(lay(k,g) for k,g in layouts if (k,g)!=(1,1))
 backs=''.join(p.image(0,p.HEIGHT-height(k,g),W,height(k,g)+140,M+'sheet_bg.png','FF1C1C1E',
                       '<visible>%s</visible>'%(lay(k,g) if (k,g)!=(1,1) else '![%s]'%others),border=102)
               for k,g in layouts)
 rise=''.join('<animation effect="slide" start="0,0" end="0,-%d" time="0" condition="%s">Conditional</animation>'%(height(k,g)-height(1,1),lay(k,g))
              for k,g in layouts if (k,g)!=(1,1))
 top=p.HEIGHT-height(1,1)
 content=('<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height>%s'%(top,W,height(ROWS,MAX_HEADS),rise)+
  p.image((W-100)//2,22,100,14,M+'dot.png','4DFFFFFF',border=7)+
  p.label(side+12,60,w-200,100,'Activity','p_title')+
  round_button(p,9600,W-side-HIT,52,[('xmark.png','')],'','<ondown>9611</ondown>')+
  '<control type="grouplist" id="9300"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%(side,head,w,ROWS*row+MAX_HEADS*ghead)+
  ''.join(header(n)+line(n) for n in range(1,ROWS+1))+empty+'</control></control>')
 drop=height(ROWS,MAX_HEADS)
 anim=('<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
       '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>')%(drop,drop)
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
SKIP={NAME,SHEET,BOX,'IOSNotifications.xml','IOSLibraryStatus.xml','IOSLibraryItem.xml','IOSNoticeDetail.xml','IOSTransfers.xml','Font.xml','Includes.xml','Custom_1182_Dialog_Topmenu_Overlay.xml','Startup.xml',
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
         btn(9792,'<left>%d</left><top>%d</top><width>%d</width><height>%d</height><visible>%s</visible>'%(w-16-HIT,(170-HIT)//2,HIT,HIT,p.e(HAS('Pause'))),PAUSE)+'</control>')

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
