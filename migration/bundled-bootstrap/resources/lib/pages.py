"""Round 2 portrait pages (owner-approved mockups, docs/design/fuse-pages-mockups.html) in place of Fuse's landscape
boxes shrunk into the middle of the screen:

- Shared dialogs: DialogConfirm (yes/no, OK and progress share it in Kodi 21) as an iOS alert, DialogTextViewer,
  DialogSettings (same rows as the add-on settings sheet).
- Kodi windows: AddonBrowser, EventLog, SettingsSystemInfo, FileManager.
- Umbrella's "getting ready to play" window (source_progress.xml, filled from umbrella_ready.py).
- Play on TV over video: 1080i/IOSPlayOnTV.xml, driven by cast.py (landscape, Fuse's 1920x1080 canvas and fonts).

Every page keeps the control ids Kodi (or Umbrella) drives. portrait.py passes its helpers in `p`;
settings_page.py supplies the shared row/header pieces.
"""
UPDATES='!String.IsEmpty(System.AddonUpdateCount) + !String.IsEqual(System.AddonUpdateCount,0)'
BLUE='FF0A84FF';RED='FFFF453A';GREEN='FF30D158';ORANGE='FFFF9F0A'
ROW=140;TOP=200

def sp(p):return p.settings_page

def textures(p):
 return {'alert.png':p.glass(120,40,(44,44,48,252),(255,255,255,40)),'sheet_l.png':p.glass(120,40,(36,36,40,230),(255,255,255,44))}

# --- shared pieces --------------------------------------------------------------------------------------
def page(p,original,body,default,extra=''):
 return p.window(original,'<controls>'+p.backdrop()+body+'</controls>',default,
                 '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>'+extra)

def back_header(p,title,back='Action(Back)',down='50'):
 s=sp(p)
 return s.header(p,[('',back)],[(title,'')]).replace('<ondown>9300</ondown>','<ondown>%s</ondown>'%down)

def row_layout(p,w,focused,icon='$INFO[ListItem.Icon]',label='$INFO[ListItem.Label]',sub='$INFO[ListItem.Label2]',right='',
               tint='FF0F0F10',extra='',height=ROW,selected='',sub_cond=''):
 """iOS row for list items: icon tile, title, grey subtitle, right value, chevron, hairline."""
 x=40+84+34
 xml=(p.image(0,0,w,height,p.MEDIA+'white.png',p.SURFACE2 if focused else p.SURFACE)+
      p.image(x,height-2,w-x,2,p.MEDIA+'white.png',p.SEP)+
      p.surface(40,(height-84)//2,84,84,'tile84.png',tint,24)+
      p.image(48,(height-68)//2,68,68,icon,p.WHITE,'','>keep'))
 if sub:
  # Two lines when there is a subtitle, the title centred alone when it is empty (Kodi leaves Label2 blank often).
  has=sub_cond or '!String.IsEmpty(ListItem.Label2)'
  scroll='<scroll>%s</scroll>'%('true' if focused else 'false')
  xml+=(p.label(x,height//2-58,w-x-260,60,label,'p_body',p.WHITE,'left',scroll+'<visible>%s</visible>'%has)+
        p.label(x,height//2+2,w-x-200,52,sub,'p_foot',p.GREY,'left','<visible>%s</visible>'%has)+
        p.label(x,0,w-x-260,height,label,'p_body',p.WHITE,'left',scroll+'<visible>![%s]</visible>'%has))
 else:
  xml+=p.label(x,0,w-x-260,height,label,'p_body',p.WHITE,'left','<scroll>%s</scroll>'%('true' if focused else 'false'))
 if right:xml+=p.label(w-460,0,380,height,right,'p_foot',p.GREY,'right')
 if selected:xml+=p.image(w-96,(height-52)//2,52,52,p.ICONS+'circle-check.png',BLUE,'<visible>%s</visible>'%selected)
 xml+=p.icon(w-74,(height-34)//2,34,'chevron-right.png',p.DIM,extra)
 return xml

def media_list(p,id,top,bottom=0,layout=None,height=ROW,extra='',left=None,width=None):
 w=width or (p.WIDTH-2*p.SIDE);x=p.SIDE if left is None else left
 layout=layout or (lambda f:row_layout(p,w,f))
 return ('<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><bottom>%d</bottom><orientation>vertical</orientation>'
         '<scrolltime tween="cubic" easing="out">260</scrolltime><onup>9001</onup>%s'
         '<itemlayout height="%d">%s</itemlayout><focusedlayout height="%d">%s</focusedlayout></control>')%(
         id,x,top,w,bottom,extra,height,layout(False),height,layout(True))

def pill_button(p,id,x,y,w,text,actions='',extra='',selected=''):
 """Capsule like the category pills; blue when `selected` (a condition) holds."""
 M=p.MEDIA
 sel=('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>96</height><texture border="48" colordiffuse="%s">%spill_96.png</texture>'
      '<visible>%s</visible></control>'%(x,y,w,BLUE,M,selected)) if selected else ''
 return (sel+'<control type="button" id="%d"><left>%d</left><top>%d</top><width min="%d" max="600">auto</width><height>96</height><label>%s</label><font>p_foot_b</font>'
         '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><textoffsetx>36</textoffsetx>'
         '<texturefocus border="48" colordiffuse="66636366">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="%s">%spill_96.png</texturenofocus>'
         '%s%s</control>')%(id,x,y,w,p.e(text),p.WHITE,p.WHITE,M,'00000000' if selected else p.SURFACE,M,
                             ''.join('<onclick>%s</onclick>'%p.e(a) for a in actions.split('\x00') if a),extra)

# --- iOS alert: yes/no, OK, progress ---------------------------------------------------------------------
def confirm_dialog(p,original):
 """portrait/DialogConfirm.xml. Kodi fills heading 1 and text 9, shows buttons 10 (No/Cancel), 11 (Yes/OK) and
 12 (custom) as needed, and the progress bar 20 only for progress dialogs."""
 w=900;h=680;x=(p.WIDTH-w)//2;y=(p.HEIGHT-h)//2;M=p.MEDIA
 def button(id,text_color,fill):
  return ('<control type="button" id="%d"><width min="250" max="520">auto</width><height>112</height><font>p_btn</font><textcolor>%s</textcolor>'
          '<focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><textoffsetx>44</textoffsetx>'
          '<texturefocus border="56" colordiffuse="%s">%spill_112.png</texturefocus><texturenofocus border="56" colordiffuse="%s">%spill_112.png</texturenofocus>'
          '<onup>9</onup></control>')%(id,text_color,text_color,'FF5A5A5E' if fill!=BLUE else 'FF3D9BFF',M,fill,M)
 dim=('<control type="image"><width>%d</width><height>%d</height><texture colordiffuse="8C000000">%swhite.png</texture></control>'%(p.WIDTH,p.HEIGHT,M))
 card=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,y,w,h)+
  '<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
  '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'+
  p.image(0,0,w,h,M+'alert.png',p.WHITE,border=40)+
  '<control type="label" id="1"><left>50</left><top>44</top><width>%d</width><height>70</height><font>p_h3</font><textcolor>%s</textcolor>'
  '<align>center</align><aligny>center</aligny><scroll>true</scroll></control>'%(w-100,p.WHITE)+
  '<control type="textbox" id="9"><left>60</left><top>130</top><width>%d</width><height>%d</height><font>p_sub</font><textcolor>FFD1D1D6</textcolor>'
  '<align>center</align><autoscroll delay="4000" time="2000" repeat="6000">true</autoscroll><pagecontrol>-</pagecontrol></control>'%(w-120,h-130-250)+
  '<control type="progress" id="20"><left>60</left><top>%d</top><width>%d</width><height>14</height>'
  '<texturebg border="7" colordiffuse="40FFFFFF">%sdot.png</texturebg><lefttexture /><midtexture border="7" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'%(h-230,w-120,M,BLUE,M)+
  '<control type="grouplist" id="9100"><left>40</left><top>%d</top><width>%d</width><height>112</height><orientation>horizontal</orientation>'
  '<align>center</align><itemgap>24</itemgap>'%(h-160,w-80)+button(10,p.WHITE,'FF48484A')+button(12,p.WHITE,'FF48484A')+button(11,p.WHITE,BLUE)+
  '</control></control>')
 # Kodi hides 11 in progress dialogs; this 1x1 button takes the first focus and hands it to Yes/OK, else Cancel
 # (focus stayed nowhere before, so a remote could not cancel).
 relay=('<control type="button" id="9101"><left>0</left><top>0</top><width>1</width><height>1</height><texturefocus /><texturenofocus />'
        '<onfocus condition="Control.IsVisible(11)">SetFocus(11)</onfocus><onfocus condition="!Control.IsVisible(11) + Control.IsVisible(10)">SetFocus(10)</onfocus>'
        '<onfocus condition="!Control.IsVisible(11) + !Control.IsVisible(10)">SetFocus(12)</onfocus></control>')
 return p.window(original,'<controls>'+dim+relay+card+'</controls>','9101')

def text_viewer(p,original):
 """portrait/DialogTextViewer.xml: heading 1, text 5 (changelogs, add-on descriptions, logs)."""
 w=p.WIDTH-2*p.SIDE
 body=(back_header(p,'','Close','5').replace('<label></label></control>','<label></label></control>',1)+
  '<control type="label" id="1"><left>230</left><top>36</top><width>%d</width><height>108</height><font>p_h3</font><textcolor>%s</textcolor>'
  '<align>center</align><aligny>center</aligny><scroll>true</scroll></control>'%(p.WIDTH-460,p.WHITE)+
  p.surface(p.SIDE,TOP,w,p.HEIGHT-TOP-60,'group.png',p.SURFACE,70)+
  '<control type="textbox" id="5"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>p_sub</font><textcolor>FFD1D1D6</textcolor>'
  '<pagecontrol>61</pagecontrol><onup>9001</onup></control>'%(p.SIDE+48,TOP+44,w-96,p.HEIGHT-TOP-150)+
  '<control type="scrollbar" id="61"><left>%d</left><top>%d</top><width>10</width><height>%d</height><texturesliderbackground />'
  '<texturesliderbar border="5" colordiffuse="66FFFFFF">%sdot.png</texturesliderbar><orientation>vertical</orientation><showonepage>false</showonepage></control>'%(
   p.WIDTH-p.SIDE-26,TOP+50,p.HEIGHT-TOP-170,p.MEDIA))
 return p.window(original,'<controls>'+p.backdrop()+body+'</controls>','5')

def settings_dialog(p,original):
 """portrait/DialogSettings.xml (Kodi's generic settings dialogs: set content, library, profile...): the same sheet
 as the add-on settings, Cancel 29 and Done 28, custom button 30 hidden like Fuse."""
 # These dialogs mostly have one unnamed section, so no category pills (an empty pill showed otherwise).
 return sp(p).addon_settings_window(p,original,categories=False)

# --- Add-ons ---------------------------------------------------------------------------------------------
def addon_browser(p,original):
 """portrait/AddonBrowser.xml: Kodi's addons:// folders in list 50 as App Store-style rows (icon, name, version),
 with the folder name as the title and shortcuts for updates and zip installs on the root page."""
 root='String.IsEqual(Container.FolderPath,addons://) | String.IsEmpty(Container.FolderPath)'
 w=p.WIDTH-2*p.SIDE
 def item(f):
  return row_layout(p,w,f,sub='$INFO[ListItem.AddonVersion]$INFO[ListItem.Label2, · ,]',tint='FF0F0F10',
                    sub_cond='!String.IsEmpty(ListItem.AddonVersion) | !String.IsEmpty(ListItem.Label2)')
 title='$INFO[Container.FolderName]'
 body=(media_list(p,50,TOP+130,40,item)+
       p.image(0,0,p.WIDTH,TOP+120,p.MEDIA+'white.png',p.BG)+
       back_header(p,'')+
       p.label(260,36,p.WIDTH-520,108,'[B]Add-ons[/B]','p_h3',p.WHITE,'center','<visible>%s</visible>'%root)+
       p.label(260,36,p.WIDTH-520,108,title,'p_h3',p.WHITE,'center','<visible>![%s]</visible>'%root)+
       '<control type="grouplist" id="9010"><left>%d</left><top>%d</top><width>%d</width><height>96</height><orientation>horizontal</orientation>'
       '<itemgap>16</itemgap><ondown>50</ondown><onup>9001</onup>'%(p.SIDE,TOP,w)+
       pill_button(p,9011,0,0,250,'My Add-ons','Container.Update(addons://user/,replace)')+
       pill_button(p,9012,0,0,300,'$LOCALIZE[24043]$INFO[System.AddonUpdateCount, (,)]','Container.Update(addons://outdated/,replace)',
                   '<visible>%s</visible>'%UPDATES)+
       pill_button(p,9013,0,0,260,'From Zip','InstallFromZip')+
       pill_button(p,9014,0,0,200,'Search','Container.Update(addons://search/,replace)')+
       '</control>')
 return page(p,original,body,'50')

# --- Event log -------------------------------------------------------------------------------------------
def event_log(p,original):
 """portrait/EventLog.xml: Kodi's buttons 21 (level), 22 (that level only), 4 (order) and 20 (clear) become pills
 over list 50; each event is a row with its level badge, description and time."""
 w=p.WIDTH-2*p.SIDE
 def item(f):
  h=170;x=40+84+34
  return (p.image(0,0,w,h,p.MEDIA+'white.png',p.SURFACE2 if f else p.SURFACE)+p.image(x,h-2,w-x,2,p.MEDIA+'white.png',p.SEP)+
          p.surface(40,(h-84)//2,84,84,'tile84.png','FF0F0F10',24)+p.image(52,(h-60)//2,60,60,'$INFO[ListItem.Icon]',p.WHITE,'','>keep')+
          p.label(x,22,w-x-230,60,'$INFO[ListItem.Label]','p_body',p.WHITE,'left','<scroll>%s</scroll>'%('true' if f else 'false'))+
          p.label(x,86,w-x-40,56,'$INFO[ListItem.Label2]','p_foot',p.GREY))
 def btn(id,x,width,label,kind='button',extra=''):
  t='<control type="%s" id="%d"><width min="%d" max="700">auto</width><height>96</height><font>p_foot_b</font><textcolor>%s</textcolor>'%(kind,id,width,p.WHITE)
  return (t+'<focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><textoffsetx>36</textoffsetx>'
          '<texturefocus border="48" colordiffuse="66636366">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="%s">%spill_96.png</texturenofocus>'
          '%s<ondown>50</ondown><onup>9001</onup></control>')%(p.WHITE,p.MEDIA,p.SURFACE,p.MEDIA,extra)
 x=0
 bar=('<control type="grouplist" id="9010"><left>%d</left><top>%d</top><width>%d</width><height>96</height><orientation>horizontal</orientation>'
      '<itemgap>16</itemgap><scrolltime tween="cubic" easing="out">250</scrolltime>'%(p.SIDE,TOP,w)+
      btn(21,x,180,'',extra='<label>$LOCALIZE[14119]</label><onright>22</onright>')+
      btn(22,x,180,'','togglebutton','<label>$LOCALIZE[14121]</label><altlabel>$LOCALIZE[14121]</altlabel>'
          '<alttexturefocus border="48" colordiffuse="%s">%spill_96.png</alttexturefocus><alttexturenofocus border="48" colordiffuse="%s">%spill_96.png</alttexturenofocus>'
          '<onleft>21</onleft><onright>4</onright>'%(BLUE,p.MEDIA,BLUE,p.MEDIA))+
      btn(4,x,180,'','togglebutton','<label>$LOCALIZE[584]</label><altlabel>$LOCALIZE[585]</altlabel><onleft>22</onleft><onright>20</onright>')+
      btn(20,x,150,'','button','<label>[COLOR FFFF453A]$LOCALIZE[192][/COLOR]</label><onleft>4</onleft>')+'</control>')
 body=(media_list(p,50,TOP+130,40,item,170)+p.image(0,0,p.WIDTH,TOP+120,p.MEDIA+'white.png',p.BG)+back_header(p,'Event Log')+bar+
       '<control type="group"><top>%d</top><visible>Integer.IsEqual(Container(50).NumItems,0)</visible>'%(TOP+400)+
       p.label(p.SIDE,0,w,80,'No events','p_h3',p.GREY,'center')+'</control>')
 return page(p,original,body,'50')

# --- System information ----------------------------------------------------------------------------------
INFO_TABS=[(95,'$LOCALIZE[20037]'),(94,'$LOCALIZE[154]'),(96,'$LOCALIZE[705]'),(97,'$LOCALIZE[157]'),(98,'$LOCALIZE[13281]'),
           (99,'$LOCALIZE[31000]'),(100,'$LOCALIZE[12389]')]
def system_info(p,original):
 """portrait/SettingsSystemInfo.xml. Kodi switches the section when a button 94-100 gets focus and fills labels
 2-11 (and the privacy policy textbox 30); 52/53 carry the build. Live meters on top, like the mockup."""
 w=p.WIDTH-2*p.SIDE;M=p.MEDIA
 # 9003, not Fuse's 3: Kodi writes its third info line into control 3, which Fuse also gave its tab list.
 tabs=('<control type="grouplist" id="9003"><left>%d</left><top>%d</top><width>%d</width><height>96</height><orientation>horizontal</orientation>'
       '<itemgap>16</itemgap><ondown>9001</ondown>'%(p.SIDE,TOP,w))
 for i,(id,label) in enumerate(INFO_TABS):
  tabs+=('<control type="button" id="%d"><width min="%d" max="600">auto</width><height>96</height><label>%s</label><font>p_foot_b</font><textcolor>%s</textcolor>'
         '<focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><textoffsetx>30</textoffsetx>'
         '<texturefocus border="48" colordiffuse="%s">%spill_96.png</texturefocus><texturenofocus border="48" colordiffuse="%s">%spill_96.png</texturenofocus>'
         '<onup>9001</onup></control>')%(id,200,label,p.GREY,p.WHITE,BLUE,M,p.SURFACE,M)
 tabs+='</control>'
 tile=lambda x,y,title,value,info,color:(p.label(x+34,y+22,400,44,title,'p_foot',p.GREY)+p.label(x+34,y+66,400,70,value,'p_h2')+
  '<control type="progress"><left>%d</left><top>%d</top><width>%d</width><height>18</height><info>%s</info>'
  '<texturebg border="9" colordiffuse="FF3A3A3C">%sdot.png</texturebg><lefttexture /><midtexture border="9" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'%(
   x+34,y+150,w//2-80,info,M,color,M))
 th=210
 meters=('<control type="group"><left>%d</left><top>%d</top><visible>!Control.IsVisible(30)</visible>'%(p.SIDE,TOP+130)+
  p.surface(0,0,w,th*2,'group.png',p.SURFACE,70)+p.image(w//2,20,2,th*2-40,M+'white.png',p.SEP)+p.image(30,th,w-60,2,M+'white.png',p.SEP)+
  tile(0,0,'Memory','$INFO[System.Memory(used.percent)]','System.Memory(used)','FFBF5AF2')+
  tile(w//2,0,'CPU','','System.CPUUsage',ORANGE)+
  p.label(34,th+22,400,44,'Free space','p_foot',p.GREY)+p.label(34,th+66,w//2-60,70,'$INFO[System.FreeSpace]','p_h3')+
  p.label(w//2+34,th+22,400,44,'Screen','p_foot',p.GREY)+p.label(w//2+34,th+66,w//2-60,70,'$INFO[System.ScreenWidth]×$INFO[System.ScreenHeight]','p_h3')+
  '</control>')
 rows_top=TOP+130+th*2+60
 rows=''.join(('<control type="label" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>p_sub</font>'
               '<textcolor>%s</textcolor><aligny>center</aligny></control>')%(i,p.SIDE+44,rows_top+(i-2)*104,w-88,104,p.WHITE)
              +p.image(p.SIDE+44,rows_top+(i-1)*104-1,w-44,2,M+'white.png',p.SEP,'<visible>!String.IsEmpty(Control.GetLabel(%d))</visible>'%(i+1))
              for i in range(2,12))
 card=('<control type="group"><visible>!Control.IsVisible(30)</visible>'+
  p.surface(p.SIDE,rows_top-20,w,10*104+40,'group.png',p.SURFACE,70)+rows+'</control>')
 policy=('<control type="textbox" id="30"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>p_foot</font>'
         '<textcolor>FFD1D1D6</textcolor><pagecontrol>61</pagecontrol></control>')%(p.SIDE+20,TOP+140,w-40,p.HEIGHT-TOP-260)
 build=(p.label(p.SIDE,p.HEIGHT-110,w,50,'Kodi $INFO[System.BuildVersionShort]  ·  $INFO[System.BuildDate]','p_cap',p.DIM,'center')+
        '<control type="label" id="52"><width>1</width><height>1</height><visible>false</visible></control>'
        '<control type="label" id="53"><width>1</width><height>1</height><visible>false</visible></control>'
        '<control type="label" id="40"><width>1</width><height>1</height><visible>false</visible></control>')
 body=meters+card+policy+build+back_header(p,'Information','Action(Back)','9003')+tabs
 # Fuse's kept onload focuses its old tab list (3); focus Summary after it, or Kodi shows no section at all.
 return page(p,original,body,'95','<onload>SetFocus(95)</onload>')

# --- File manager ----------------------------------------------------------------------------------------
def file_manager(p,original):
 """portrait/FileManager.xml. Kodi's file manager copies and moves between its two lists (20 and 21), so both stay:
 stacked, each with its folder (101/102) and item count (12/13). Long-press or the context menu acts on items."""
 w=p.WIDTH-2*p.SIDE;half=(p.HEIGHT-TOP-60)//2
 def pane(id,label_id,count_id,top,title):
  def item(f):
   return row_layout(p,w,f,'$INFO[ListItem.Icon]','$INFO[ListItem.Label]','$INFO[ListItem.Label2]',
                     selected='ListItem.IsSelected',height=130)
  other=21 if id==20 else 20
  return (p.label(p.SIDE+44,top,w-300,70,title,'p_h3',p.GREY)+
          '<control type="label" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>50</height><font>p_cap</font><textcolor>%s</textcolor>'
          '<scroll>true</scroll></control>'%(label_id,p.SIDE+44,top+66,w-88,p.DIM)+
          '<control type="label" id="%d"><left>%d</left><top>%d</top><width>260</width><height>70</height><font>p_foot</font><textcolor>%s</textcolor>'
          '<align>right</align><aligny>center</aligny></control>'%(count_id,p.WIDTH-p.SIDE-300,top,p.GREY)+
          media_list(p,id,top+130,p.HEIGHT-(top+half-20),item,130,
                     '<ondown>%d</ondown>'%other if id==20 else '<onup>20</onup>').replace('<onup>9001</onup><onup>20</onup>','<onup>20</onup>'))
 body=(pane(20,101,12,TOP,'Files')+pane(21,102,13,TOP+half,'Copy & Move To')+
       p.image(0,0,p.WIDTH,TOP-10,p.MEDIA+'white.png',p.BG)+back_header(p,'File Manager','Action(Back)','20'))
 return page(p,original,body,'20')

# --- Umbrella: getting ready to play ---------------------------------------------------------------------
def umbrella_ready(p):
 """portrait/source_progress.xml (Umbrella looks in the current skin folder first). Same ids and properties as
 Umbrella's own window: textbox 2001 (its text, hidden here), Window.Property(umbrella.*), percent."""
 R=lambda k:'$INFO[Window(home).Property(IOSReady.%s)]'%k
 ready='String.IsEqual(Window(home).Property(IOSReady.Ready),true)'
 hidden='String.IsEqual(Window.Property(umbrella.isHidden),true) | String.IsEqual(Window.Property(umbrella.icononly),true)'
 W=p.WIDTH;w=W-2*p.SIDE;M=p.MEDIA
 card_h=520;card_y=p.HEIGHT-card_h-250
 # Opaque black page (it is a dialog over whatever was open), fanart on the top part fading into it.
 art_h=card_y-60
 art=(p.backdrop()+
      ('<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><aspectratio>scale</aspectratio>'
       '<texture background="true" colordiffuse="CCFFFFFF">$INFO[Window.Property(umbrella.fanart)]</texture></control>')%(W,art_h)+
      p.image(0,0,W,art_h,M+'hero_fade.png')+p.image(0,0,W,260,M+'fade_down.png'))
 logo=('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>260</height><aspectratio align="left" aligny="bottom">keep</aspectratio>'
       '<texture background="true">$INFO[Window.Property(umbrella.clearlogo)]</texture></control>')%(p.SIDE,card_y-700,w-200)
 title=p.label(p.SIDE,card_y-560,w,140,'$INFO[Window.Property(umbrella.title)]','p_title',p.WHITE,'left',
               '<visible>String.IsEmpty(Window.Property(umbrella.clearlogo))</visible>')
 plot=('<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>200</height><font>p_foot</font><textcolor>%s</textcolor>'
       '<label>$INFO[Window.Property(umbrella.plot)]</label></control>')%(p.SIDE,card_y-400,w,p.GREY)
 tv=p.label(p.SIDE,card_y-460,w,56,'$INFO[Window.Property(umbrella.tvtitle)]','p_foot_b','FFFF6B6B')
 # Source card
 card=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(p.SIDE,card_y,w,card_h)+
  p.image(0,0,w,card_h,M+'glass_card.png',p.WHITE,border=44)+
  '<control type="group"><visible>%s</visible>'%ready+
  p.surface(40,40,100,100,'tile100.png','FF7D3CFF',28)+p.icon(55,55,70,'umbrella.png',p.WHITE)+
  p.label(170,40,w-460,56,R('Provider'),'p_body',p.WHITE)+
  p.label(170,96,w-460,46,'$INFO[Window(home).Property(IOSReady.Via),via ,]','p_foot',p.GREY)+
  p.label(w-330,40,290,100,R('Size'),'p_h3',p.WHITE,'right')+
  '<control type="group"><visible>!String.IsEmpty(Window(home).Property(IOSReady.Quality))</visible>'+
  p.surface(40,178,120,64,'pill_56.png','FFFFFFFF',28)+p.label(40,178,120,64,R('Quality'),'p_foot_b','FF000000','center')+'</control>'+
  '<control type="textbox"><left>180</left><top>184</top><width>%d</width><height>110</height><font>p_foot_b</font><textcolor>%s</textcolor>'
  '<label>%s</label></control>'%(w-220,p.WHITE,R('Badges'))+
  p.label(40,290,w-80,50,R('File'),'p_cap',p.GREY,'left','<scroll>true</scroll>')+'</control>'+
  '<control type="textbox"><left>40</left><top>40</top><width>%d</width><height>270</height><font>p_foot</font><textcolor>%s</textcolor>'
  '<label>%s</label><visible>!%s</visible></control>'%(w-80,'FFD1D1D6',R('Text'),ready)+
  # Kodi's progress control cannot read a window property, so the bar is 20 segments shown by Umbrella's percent.
  p.image(40,360,w-80,16,M+'dot.png','33FFFFFF',border=8)+
  ''.join(p.image(40,360,max(16,(w-80)*k//20),16,M+'dot.png',p.WHITE,
                  '<visible>Integer.IsGreaterOrEqual(Window.Property(percent),%d)</visible>'%(k*5),border=8) for k in range(1,21))+
  p.label(40,390,w-300,60,'Getting ready to play…','p_foot','FFD1D1D6')+
  p.label(w-260,390,220,60,'$INFO[Window.Property(percent)]%','p_foot','FFD1D1D6','right')+'</control>')
 cancel=('<control type="button" id="9001"><left>%d</left><top>%d</top><width>%d</width><height>140</height><label>Cancel</label>'
         '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
         '<texturefocus border="70" colordiffuse="FFFFFFFF">%sglass_150.png</texturefocus><texturenofocus border="70" colordiffuse="FFFFFFFF">%sglass_150.png</texturenofocus>'
         '<onclick>Action(Back)</onclick></control>')%(p.SIDE,p.HEIGHT-200,w,p.WHITE,p.WHITE,M,M)
 # Umbrella's "icon only" setting: just a small spinner in the corner, as Umbrella draws it.
 small=('<control type="group"><visible>String.IsEqual(Window.Property(umbrella.icononly),true) + !String.IsEqual(Window.Property(umbrella.isHidden),true)</visible>'+
        p.image(W-p.SIDE-120,40,120,120,M+'ring.png',p.WHITE,'<animation effect="rotate" end="-360" center="auto" time="1200" loop="true" reversible="false" condition="true">Conditional</animation>')+'</control>')
 hidden_text='<control type="textbox" id="2001"><left>-4000</left><top>0</top><width>800</width><height>800</height><font>p_cap</font></control>'
 full='<control type="group"><visible>![%s]</visible>%s%s%s%s%s%s%s</control>'%(hidden,art,logo,title,tv,plot,card,cancel)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9001</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="250">WindowOpen</animation><controls>%s%s%s</controls></window>\n')%(
         p.MARKER,full,small,hidden_text)

def image_bg(p,texture):
 return ('<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><aspectratio>scale</aspectratio>'
         '<texture background="true" colordiffuse="B3FFFFFF">%s</texture></control>')%(p.WIDTH,p.HEIGHT,texture)

# --- Play on TV (landscape, over video) -------------------------------------------------------------------
def close_button_1080(id,x,y,extra='',size=100):
 """close_button (portrait.py) for the landscape sheets (Play on TV, AirPlay check), on Fuse's 1920x1080 canvas."""
 disc=int(size*104/118);g=int(size*52/118);d=(size-disc)//2;o=(size-g)//2
 img=lambda x,y,s,tex,col,more='':('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
                                   '<texture colordiffuse="%s">%s%s</texture>%s</control>'%(x,y,s,s,col,'special://skin/extras/portrait/',tex,more))
 return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,y,size,size)+
  img(d,d,disc,'close_disc.png','2EFFFFFF')+img(d,d,disc,'close_disc.png','24FFFFFF','<visible>Control.HasFocus(%d)</visible>'%id)+
  img(o,o,g,'close_cross.png','FFFFFFFF')+
  '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus />%s</control>'%(id,size,size,extra)+
  '</control>')

TV_ROWS=6
def play_on_tv():
 """1080i/IOSPlayOnTV.xml for cast.py, on Fuse's landscape 1920x1080 canvas with Fuse's fonts: an AirPlay-style
 glass sheet. Rows 9601+ are filled through properties tv.<n>.name / .kind / .icon / .on; 9500 closes. The sheet is
 as tall as its rows and centred with <centerleft> (the phone's landscape layout is wider than 1920): cast.py sets `count` (rows shown, plus one while searching) and one of the backgrounds matches."""
 MEDIA='special://skin/extras/portrait/';ICONS='special://skin/extras/icons/'
 P=lambda k:'$INFO[Window().Property(%s)]'%k
 has=lambda k:'!String.IsEmpty(Window().Property(%s))'%k
 w=760;row=104;head=150;foot=120;y=60
 def img(x,y,w,h,tex,color='FFFFFFFF',extra='',border=''):
  return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s colordiffuse="%s">%s</texture>%s</control>'
          %(x,y,w,h,' border="%s"'%border if border else '',color,tex,extra))
 def lab(x,y,w,h,text,font,color='FFFFFFFF',align='left',extra=''):
  return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
          '<align>%s</align><aligny>center</aligny><label>%s</label>%s</control>'%(x,y,w,h,font,color,align,text,extra))
 count='Window().Property(count)'
 backs=''.join(img(0,0,w,head+k*row+foot,MEDIA+'sheet_l.png',border='40',extra='<visible>String.IsEqual(%s,%d)</visible>'%(count,k))
               for k in range(1,TV_ROWS+2))
 def tv_row(n):
  pre='tv.%d.'%n
  return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,row,has(pre+'name'))+
   '<control type="button" id="%d"><left>12</left><top>0</top><width>%d</width><height>%d</height><label></label>'
   '<texturefocus border="30" colordiffuse="26FFFFFF">%sround_s.png</texturefocus><texturenofocus />'
   '<onup>%d</onup><ondown>%d</ondown></control>'%(9600+n,w-24,row,MEDIA,9600+n-1 if n>1 else 9500,9600+n+1 if n<TV_ROWS else 9600+n)+
   (img(126,0,w-162,2,MEDIA+'white.png','1AFFFFFF') if n>1 else '')+
   img(36,(row-68)//2,68,68,MEDIA+'tile_mask.png','24FFFFFF')+img(46,(row-48)//2,48,48,ICONS+P(pre+'icon'))+
   lab(126,10,w-260,48,P(pre+'name'),'font_main_bold')+lab(126,54,w-260,40,P(pre+'kind'),'font_mini','99EBEBF5')+
   img(w-90,(row-40)//2,40,40,ICONS+'check.png','FF0A84FF','<visible>%s</visible>'%has(pre+'on'))+'</control>')
 searching=('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(w,row,has('searching'))+
  img(44,(row-52)//2,52,52,MEDIA+'ring.png','FFFFFFFF','<visible>String.IsEqual(Window().Property(spin),true)</visible>'
      '<animation effect="rotate" end="-360" center="auto" time="1200" loop="true" reversible="false" condition="true">Conditional</animation>')+
  '<control type="textbox"><left>126</left><top>8</top><width>%d</width><height>%d</height><font>font_mini</font><textcolor>FFD1D1D6</textcolor>'
  '<label>%s</label></control>'%(w-160,row-16,P('searching'))+'</control>')
 note=('<control type="textbox"><left>36</left><top>14</top><width>%d</width><height>%d</height><font>font_mini</font><textcolor>99EBEBF5</textcolor>'
       '<label>%s</label></control>')%(w-72,foot-24,P('note'))
 stack=('<control type="grouplist" id="9300"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
        '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'%(head,w,(TV_ROWS+1)*row+foot)+
        ''.join(tv_row(n) for n in range(1,TV_ROWS+1))+searching+
        '<control type="group"><width>%d</width><height>%d</height>%s</control></control>'%(w,foot,note))
 body=('<control type="image"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texture colordiffuse="73000000">%swhite.png</texture></control>'%MEDIA+
  '<control type="button" id="9099"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texturefocus /><texturenofocus /><onclick>Close</onclick><onfocus>SetFocus(9601)</onfocus></control>'
  '<control type="group"><centerleft>50%%</centerleft><top>%d</top><width>%d</width>'%(y,w)+
  '<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'+
  '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'+
  backs+img(36,40,76,76,MEDIA+'dot.png','1FFFFFFF')+img(55,59,38,38,MEDIA+'airplay.png')+
  lab(134,34,w-280,52,'Play on TV','font_head_bold')+lab(134,84,w-280,40,P('subtitle'),'font_mini','99EBEBF5','left','<visible>!%s</visible>'%has('last'))+
  lab(134,84,w-400,40,P('subtitle'),'font_mini','99EBEBF5','left','<visible>%s</visible>'%has('last'))+
  # How the last Play on TV over AirPlay went (the AirPlay check, library_tools_page.airplay_sheet), once there is one.
  '<control type="button" id="9501"><left>%d</left><top>28</top><width>190</width><height>100</height><label>Last time</label><font>font_mini</font>'
  '<textcolor>FF4FA8FF</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>center</align><aligny>center</aligny>'
  '<texturefocus border="30" colordiffuse="26FFFFFF">%sround_s.png</texturefocus><texturenofocus />'
  '<visible>%s</visible><onright>9500</onright><ondown>9601</ondown></control>'%(w-336,MEDIA,has('last'))+
  close_button_1080(9500,w-126,28,'<ondown>9601</ondown><onleft>9501</onleft>')+stack+'</control>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: Play on TV sheet r1 (navigation.patch_skin leaves this marker alone) -->\n'
         '<window type="dialog"><defaultcontrol always="true">9601</defaultcontrol><controls>%s</controls></window>\n')%body

HANDMADE={'DialogConfirm.xml','DialogTextViewer.xml','DialogSettings.xml','AddonBrowser.xml','EventLog.xml','SettingsSystemInfo.xml','FileManager.xml'}

def files(p,read):
 out={p.FOLDER+'/DialogConfirm.xml':confirm_dialog(p,read('DialogConfirm.xml')),
      p.FOLDER+'/DialogTextViewer.xml':text_viewer(p,read('DialogTextViewer.xml')),
      p.FOLDER+'/DialogSettings.xml':settings_dialog(p,read('DialogSettings.xml')),
      p.FOLDER+'/AddonBrowser.xml':addon_browser(p,read('AddonBrowser.xml')),
      p.FOLDER+'/EventLog.xml':event_log(p,read('EventLog.xml')),
      p.FOLDER+'/SettingsSystemInfo.xml':system_info(p,read('SettingsSystemInfo.xml')),
      p.FOLDER+'/FileManager.xml':file_manager(p,read('FileManager.xml')),
      p.FOLDER+'/source_progress.xml':umbrella_ready(p),
      '1080i/IOSPlayOnTV.xml':play_on_tv()}
 out={k:v.encode() for k,v in out.items()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
