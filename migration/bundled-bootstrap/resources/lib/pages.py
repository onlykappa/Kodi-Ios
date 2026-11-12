"""Round 2 portrait pages (owner-approved mockups, docs/design/fuse-pages-mockups.html) in place of Fuse's landscape
boxes shrunk into the middle of the screen:

- Shared dialogs: DialogConfirm (yes/no, OK and progress share it in Kodi 21) as an iOS alert, DialogTextViewer,
  DialogSettings (same rows as the add-on settings sheet).
- Kodi windows: AddonBrowser, EventLog, SettingsSystemInfo, FileManager.
- Umbrella's "getting ready to play" window (source_progress.xml, filled from umbrella_ready.py).
- Play on TV over video: 1080i/IOSPlayOnTV.xml, driven by cast.py (landscape, Fuse's 1920x1080 canvas and fonts).
- Kodi's busy dialog (DialogBusy) as a centred pill in both folders (busy_dialog).

Every page keeps the control ids Kodi (or Umbrella) drives. portrait.py passes its helpers in `p`;
settings_page.py supplies the shared row/header pieces.
"""
UPDATES='!String.IsEmpty(System.AddonUpdateCount) + !String.IsEqual(System.AddonUpdateCount,0)'
BLUE='FF0A84FF';RED='FFFF453A';GREEN='FF30D158';ORANGE='FFFF9F0A'
ROW=140;TOP=200

def sp(p):return p.settings_page

def tag_line(p,size=64,radius=16,stroke=3):
 """A rounded outline (nine-sliced with border=radius): the info card's tags (board 08)."""
 return p.png(size,size,lambda x,y:(255,255,255,int(255*max(0,p.coverage(x,y,size,size,radius)-p.coverage(x,y,size,size,radius,stroke)))))

def textures(p):
 return {'tag_line.png':tag_line(p),'alert.png':p.glass(120,40,(44,44,48,252),(255,255,255,40)),'sheet_l.png':p.glass(120,40,(36,36,40,230),(255,255,255,44))}

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
 """portrait/DialogConfirm.xml (owner-approved board 03, docs/design/fuse-windows-mockups.html): a short bold title,
 one line of context and hairline-divided buttons. Kodi fills heading 1 and text 9 and shows buttons 10 (No/Cancel),
 11 (Yes/OK) and 12 (custom); progress dialogs show 10 and the bar 20. One button is full width, two share the row
 (the likely choice on the trailing side, bold) and a custom third stacks all three, Cancel last. The buttons keep
 their ids and a 118-unit height but draw nothing themselves: the rows are separate images and labels that follow
 which buttons Kodi shows (their text is read back with Control.GetLabel). A destructive verb is red."""
 w=800;rh=118;top=400;h_two=top+rh;h_three=top+3*rh;M=p.MEDIA
 v=lambda i:'Control.IsVisible(%d)'%i
 three=v(12);two='%s + %s + !%s'%(v(10),v(11),v(12));only10='%s + !%s + !%s'%(v(10),v(11),v(12));only11='%s + !%s + !%s'%(v(11),v(10),v(12))
 x=(p.WIDTH-w)//2;y=(p.HEIGHT-h_two)//2
 destructive='[%s]'%' | '.join('String.Contains(Control.GetLabel(11),%s)'%k for k in ('Delete','delete','Remove','remove','Clear','clear','Reset','reset','Erase'))
 def ghost(id,l,t,width,visible='',extra=''):
  return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><label></label>'
          '<textcolor>00000000</textcolor><focusedcolor>00000000</focusedcolor><texturefocus /><texturenofocus />%s%s</control>')%(id,l,t,width,rh,('<visible>%s</visible>'%visible) if visible else '',extra)
 def lit(l,t,width,focus,visible):
  # Pressed/focused row: a rounded inset highlight, so it does not poke out of the card's corners.
  return p.image(l+10,t+10,width-20,rh-20,M+'round_s.png','24FFFFFF','<visible>%s + Control.HasFocus(%d)</visible>'%(visible,focus),border=26)
 def words(l,t,width,button,font,color,visible):
  return p.label(l,t,width,rh,'$INFO[Control.GetLabel(%d)]'%button,font,color,'center','<visible>%s</visible><scroll>false</scroll>'%visible)
 hair=lambda l,t,width,height,visible='':p.image(l,t,width,height,M+'white.png',p.SEP,('<visible>%s</visible>'%visible) if visible else '')
 B=p.ACCENT
 # Which row each button sits on in each layout: (left, top, width, layout condition)
 rows={11:[(0,top,w,only11),(w//2,top,w//2,two),(0,top,w,three)],
       10:[(0,top,w,only10),(0,top,w//2,two),(0,top+2*rh,w,three)],
       12:[(0,top+rh,w,three)]}
 drawn=''
 for button,places in rows.items():
  for l,t,width,cond in places:
   drawn+=lit(l,t,width,button,cond)
   if button==11:
    drawn+=words(l,t,width,11,'p_btn',B,cond+' + ![%s]'%destructive)+words(l,t,width,11,'p_btn',RED,cond+' + '+destructive)
   else:drawn+=words(l,t,width,button,'p_body',B,cond)
 chrome=(hair(0,top,w,2)+hair(w//2-1,top,2,rh,two)+hair(0,top+rh,w,2,three)+hair(0,top+2*rh,w,2,three))
 anim=('<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
       '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'
       # The stacked layout is 236 units taller: the group is lifted by half of that so the card stays centred.
       '<animation effect="slide" end="0,-%d" time="0" condition="%s">Conditional</animation>')%(rh,three)
 card=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,y,w,h_three)+anim+
  p.image(0,0,w,h_two,M+'alert.png',p.WHITE,'<visible>!%s</visible>'%three,border=40)+
  p.image(0,0,w,h_three,M+'alert.png',p.WHITE,'<visible>%s</visible>'%three,border=40)+
  '<control type="label" id="1"><left>50</left><top>52</top><width>%d</width><height>64</height><font>p_h3</font><textcolor>%s</textcolor>'
  '<align>center</align><aligny>center</aligny><scroll>false</scroll></control>'%(w-100,p.WHITE)+
  '<control type="textbox" id="9"><left>60</left><top>126</top><width>%d</width><height>%d</height><font>p_foot</font><textcolor>%s</textcolor>'
  '<align>center</align><autoscroll delay="4000" time="2000" repeat="6000">true</autoscroll><pagecontrol>-</pagecontrol></control>'%(w-120,top-126-30,p.GREY)+
  '<control type="progress" id="20"><left>60</left><top>%d</top><width>%d</width><height>13</height>'
  '<texturebg border="6" colordiffuse="33FFFFFF">%sdot.png</texturebg><lefttexture /><midtexture border="6" colordiffuse="%s">%sdot.png</midtexture><righttexture /></control>'%(top-70,w-120,M,BLUE,M)+
  chrome+drawn+
  ghost(11,0,top,w,'',('<onup>12</onup><ondown>12</ondown><onleft>10</onleft><onright>10</onright>'))+
  ghost(12,0,top+rh,w,'','<onup>11</onup><ondown>10</ondown>')+
  ghost(10,0,top,w//2,'','<onleft>11</onleft><onright>11</onright><onup>12</onup><ondown>11</ondown>'
        '<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(2*rh,three))+
  # Right-hand halves that only a stacked or Cancel-only row needs, so the whole row answers a tap.
  ghost(9102,w//2,top,w//2,only10,'<onclick>SendClick(10)</onclick>')+
  ghost(9103,w//2,top+2*rh,w//2,three,'<onclick>SendClick(10)</onclick>')+
  '</control>')
 dim=p.image(0,0,p.WIDTH,p.HEIGHT,M+'white.png','8C000000')
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
 # Board 10: a long title wraps to two lines (bottom-aligned above the show line and the plot), never "...".
 title=p.label(p.SIDE,card_y-680,w,200,'$INFO[Window.Property(umbrella.title)]','p_title',p.WHITE,'left',
               '<aligny>bottom</aligny><wrapmultiline>true</wrapmultiline><visible>String.IsEmpty(Window.Property(umbrella.clearlogo))</visible>')
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
  # Board 10, before a source is known: the Umbrella tile, "Looking for a source" and where it looks, then
  # Umbrella's own words (IOSReady.Text) under them.
  '<control type="group"><visible>!%s</visible>'%ready+
  p.surface(40,40,100,100,'tile100.png','FF7D3CFF',28)+p.icon(55,55,70,'umbrella.png',p.WHITE)+
  p.label(170,40,w-210,56,'Looking for a source','p_body',p.WHITE)+
  p.label(170,96,w-210,46,'Umbrella · your accounts','p_foot',p.GREY)+
  '<control type="textbox"><left>40</left><top>178</top><width>%d</width><height>170</height><font>p_foot</font><textcolor>%s</textcolor>'
  '<label>%s</label></control></control>'%(w-80,'FFD1D1D6',R('Text'))+
  # Kodi's progress control cannot read a window property, so the bar is 20 segments shown by Umbrella's percent.
  # DEC-036 / board 10: one thin bar (11 units). It follows Umbrella's percent once a source is known, and slides
  # while Umbrella is still looking.
  p.image(40,368,w-80,11,M+'dot.png','33FFFFFF',border=6,extra='<visible>%s</visible>'%ready)+
  ''.join(p.image(40,368,max(11,(w-80)*k//20),11,M+'dot.png',BLUE,
                  '<visible>%s + Integer.IsGreaterOrEqual(Window.Property(percent),%d)</visible>'%(ready,k*5),border=6) for k in range(1,21))+
  slide_bar(M,40,368,w-80,extra='<visible>!%s</visible>'%ready)+
  p.label(40,390,w-300,60,'Getting ready to play…','p_foot','FFD1D1D6')+
  p.label(w-260,390,220,60,'$INFO[Window.Property(percent)]%','p_foot','FFD1D1D6','right','<visible>%s</visible>'%ready)+'</control>')
 cancel=('<control type="button" id="9001"><left>%d</left><top>%d</top><width>%d</width><height>140</height><label>Cancel</label>'
         '<font>p_btn</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
         '<texturefocus border="70" colordiffuse="FFFFFFFF">%sglass_150.png</texturefocus><texturenofocus border="70" colordiffuse="FFFFFFFF">%sglass_150.png</texturenofocus>'
         '<onclick>Action(Back)</onclick></control>')%(p.SIDE,p.HEIGHT-200,w,p.WHITE,p.WHITE,M,M)
 # Umbrella's "icon only" setting: just a small spinner in the corner, as Umbrella draws it.
 small=('<control type="group"><visible>String.IsEqual(Window.Property(umbrella.icononly),true) + !String.IsEqual(Window.Property(umbrella.isHidden),true)</visible>'+
        slide_bar(M,W-p.SIDE-240,90,240)+'</control>')
 hidden_text='<control type="textbox" id="2001"><left>-4000</left><top>0</top><width>800</width><height>800</height><font>p_cap</font></control>'
 full='<control type="group"><visible>![%s]</visible>%s%s%s%s%s%s%s</control>'%(hidden,art,logo,title,tv,plot,card,cancel)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window><defaultcontrol always="true">9001</defaultcontrol>'
         '<animation effect="fade" start="0" end="100" time="250">WindowOpen</animation><controls>%s%s%s</controls></window>\n')%(
         p.MARKER,full,small,hidden_text)

def image_bg(p,texture):
 return ('<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><aspectratio>scale</aspectratio>'
         '<texture background="true" colordiffuse="B3FFFFFF">%s</texture></control>')%(p.WIDTH,p.HEIGHT,texture)

# --- Play on TV (landscape, over video) -------------------------------------------------------------------
def _airplay_flow():
 """airplay_flow.py beside this file (pages.py is also loaded by path, without resources/lib on sys.path)."""
 import importlib.util,os
 spec=importlib.util.spec_from_file_location('airplay_flow',os.path.join(os.path.dirname(os.path.abspath(__file__)),'airplay_flow.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def close_button_1080(id,x,y,extra='',size=100,disc=None):
 """close_button (portrait.py) for the landscape sheets (Play on TV, AirPlay check), on Fuse's 1920x1080 canvas."""
 disc=disc or int(size*104/118);g=int(disc/2);d=(size-disc)//2;o=(size-g)//2
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

TRACK_MENU='IOSTrackMenu.xml'
TRACK_ROWS=3   # rows shown before the list scrolls
# Board 02: Playback speed shows every speed Kodi plays (0.8x-1.5x) in its own list, so none scrolls away.
SPEED_LIST=9311;SPEED_ROWS=6
def track_menu():
 """1080i/IOSTrackMenu.xml for tracks.py: the Subtitles / Audio menu over the video (owner-approved mockup
 docs/design/player-subtitles-audio-mockups.html, round 2). A popover under the button that opened it, on the
 landscape canvas (2340 x 1080 on the phone, 2.68 units/pt). Window properties: mode (subtitles|audio), title,
 cta / cta_state (idle|busy|done|none|error), hint, timing, boost. Controls: 9500 close, 9501 More, 9510 Download
 and apply, 9310 the tracks (filled by the script), 9401/9402 timing -/+, 9403/9404 volume boost -/+."""
 MEDIA='special://skin/extras/portrait/';ICONS='special://skin/extras/icons/'
 P=lambda k:'$INFO[Window().Property(%s)]'%k
 isp=lambda k,v:'String.IsEqual(Window().Property(%s),%s)'%(k,v)
 subs=isp('mode','subtitles')
 # Roadmap B.7/2.12: Playback speed is a third mode: the list of speeds, no Download/Timing/Boost.
 speed=isp('mode','speed')
 # Board 02 (Subtitles › More and its found subtitles): a sub-page under a blue back link in the header, without
 # Download and apply or Timing (Window property page: '' for the tracks, else the page; back: the link's text).
 sub='!String.IsEmpty(Window().Property(page))'
 w=840;row=118;head=108;pad=27;cpad=38;list_h=TRACK_ROWS*row;cta_h=112
 def img(x,y,w,h,tex,color='FFFFFFFF',extra='',border=''):
  return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s colordiffuse="%s">%s</texture>%s</control>'
          %(x,y,w,h,' border="%s"'%border if border else '',color,tex,extra))
 def lab(x,y,w,h,text,font,color='FFFFFFFF',align='left',extra=''):
  return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
          '<align>%s</align><aligny>center</aligny><label>%s</label><scroll>false</scroll>%s</control>'%(x,y,w,h,font,color,align,text,extra))
 def stepper(x,y,minus,plus,value,nav=''):
  disc=lambda bx,id,g:(img(bx+10,y+(row-76)//2,86,76,MEDIA+'pill_72.png','1FFFFFFF',border='36')+
                       img(bx+10,y+(row-76)//2,86,76,MEDIA+'pill_72.png','24FFFFFF','<visible>Control.HasFocus(%d)</visible>'%id,'36')+
                       img(bx+35,y+(row-6)//2,36,6,MEDIA+'white.png')+
                       (img(bx+50,y+(row-36)//2,6,36,MEDIA+'white.png') if g=='plus' else '')+
                       '<control type="button" id="%d"><left>%d</left><top>%d</top><width>106</width><height>%d</height><texturefocus /><texturenofocus />%s</control>'%(id,bx,y,row,nav))
  return (disc(x,minus,'minus')+lab(x+106,y,150,row,P(value),'font_main','FFFFFFFF','center')+disc(x+256,plus,'plus'))
 def card(y,rows,body):
  return img(pad,y,w-2*pad,rows*row,MEDIA+'round_s.png','47000000',border='26')+body
 item=lambda focused:(
  (img(0,0,w-2*pad,row,MEDIA+'round_s.png','1AFFFFFF',border='26') if focused else '')+
  img(100,row-2,w-2*pad-100,2,MEDIA+'white.png','1FEBEBF5','<visible>!String.IsEmpty(ListItem.Property(sep))</visible>')+
  img(28,(row-52)//2,52,52,ICONS+'check.png','FF4FA8FF','<visible>!String.IsEmpty(ListItem.Property(on))</visible>')+
  lab(100,0,w-2*pad-330,row,'$INFO[ListItem.Label]','font_main_bold','FFFFFFFF','left','<visible>!String.IsEmpty(ListItem.Property(on))</visible>')+
  lab(100,0,w-2*pad-330,row,'$INFO[ListItem.Label]','font_main','FFFFFFFF','left','<visible>String.IsEmpty(ListItem.Property(on))</visible>')+
  lab(w-2*pad-226,0,200,row,'$INFO[ListItem.Property(tag)]','font_mini','99EBEBF5','right','<visible>String.IsEmpty(ListItem.Property(new))</visible>')+
  lab(w-2*pad-226,0,200,row,'$INFO[ListItem.Property(tag)]','font_mini','FF30D158','right','<visible>!String.IsEmpty(ListItem.Property(new))</visible>'))
 def tracks(y,up,down,id=9310,rows=TRACK_ROWS,cond=''):
  nrows='Window().Property(rows)'
  cards=''.join(img(pad,y,w-2*pad,k*row,MEDIA+'round_s.png','47000000','<visible>String.IsEqual(%s,%d)</visible>'%(nrows,k),'26') for k in range(1,rows+1))
  return ('<control type="group"><visible>%s</visible>'%cond if cond else '')+(cards+
   '<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
   '<onup>%s</onup><ondown>%s</ondown><scrolltime>200</scrolltime>'%(id,pad,y,w-2*pad,rows*row,up,down)+
   '<itemlayout height="%d" width="%d">%s</itemlayout><focusedlayout height="%d" width="%d">%s</focusedlayout></control>'%(row,w-2*pad,item(False),row,w-2*pad,item(True)))+('</control>' if cond else '')
 # Subtitles: header, Download and apply, its hint, tracks, Timing.
 y_cta=head;y_hint=y_cta+cta_h;y_list=y_hint+42;y_time=y_list+list_h+16;h_subs=y_time+2*row+pad
 cta=('<control type="group"><visible>%s + !%s</visible>'%(subs,sub)+
  img(cpad,y_cta,w-2*cpad,cta_h,MEDIA+'pill_112.png','FFFFFFFF','<visible>%s | %s | %s</visible>'%(isp('cta_state','idle'),isp('cta_state','none'),isp('cta_state','error')),'56')+
  img(cpad,y_cta,w-2*cpad,cta_h,MEDIA+'pill_112.png','1FFFFFFF','<visible>%s</visible>'%isp('cta_state','busy'),'56')+
  img(cpad,y_cta,w-2*cpad,cta_h,MEDIA+'pill_112.png','2930D158','<visible>%s</visible>'%isp('cta_state','done'),'56')+
  img(cpad,y_cta,w-2*cpad,cta_h,MEDIA+'pill_112.png','1A000000','<visible>Control.HasFocus(9510)</visible>','56')+
  img(w//2-200,y_cta+(cta_h-44)//2,44,44,MEDIA+'ring.png','FFFFFFFF','<visible>%s</visible>'
      '<animation effect="rotate" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation>'%isp('cta_state','busy'))+
  lab(cpad,y_cta,w-2*cpad,cta_h,P('cta'),'font_main_bold','FF000000','center','<visible>!%s + !%s</visible>'%(isp('cta_state','busy'),isp('cta_state','done')))+
  lab(cpad+40,y_cta,w-2*cpad-40,cta_h,P('cta'),'font_main_bold','FFFFFFFF','center','<visible>%s</visible>'%isp('cta_state','busy'))+
  lab(cpad,y_cta,w-2*cpad,cta_h,P('cta'),'font_main_bold','FF30D158','center','<visible>%s</visible>'%isp('cta_state','done'))+
  '<control type="button" id="9510"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texturefocus /><texturenofocus />'
  '<onup>9500</onup><ondown>9310</ondown></control>'%(cpad,y_cta,w-2*cpad,cta_h)+
  lab(pad,y_hint,w-2*pad,42,P('hint'),'font_mini','99EBEBF5','center')+
  '</control>')
 # Shared by both modes, drawn once (one set of ids): the tracks and Timing. Audio has no Download and apply, so
 # they slide up by its height; Volume boost is Audio's own row under Timing.
 lift=y_list-head;h_audio=y_time-lift+2*row+pad
 audio=('<control type="group"><left>0</left><top>0</top><width>%d</width>'%w+
  '<animation effect="slide" start="0,0" end="0,-%d" time="0" condition="!%s | %s">Conditional</animation>'%(lift,subs,sub)+
  tracks(y_list,9510,9401,cond='!'+speed)+tracks(y_list,9500,9500,SPEED_LIST,SPEED_ROWS,speed)+
  '<control type="group"><left>0</left><top>0</top><width>%d</width>'%w+
  ''.join('<animation effect="slide" start="0,0" end="0,-%d" time="0" condition="String.IsEqual(Window().Property(rows),%d)">Conditional</animation>'%((TRACK_ROWS-k)*row,k) for k in range(1,TRACK_ROWS))+
  '<control type="group"><visible>!%s + !%s</visible>'%(speed,sub)+
  img(pad,y_time,w-2*pad,2*row,MEDIA+'round_s.png','47000000','','26')+
  lab(pad+36,y_time,300,row,'Timing','font_main')+stepper(w-pad-372,y_time,9401,9402,'timing','<onup>9310</onup><ondown>9501</ondown>')+
  '<control type="group"><visible>%s</visible>'%subs+
  img(pad+36,y_time+row-1,w-2*pad-36,2,MEDIA+'white.png','1FEBEBF5')+
  img(pad,y_time+row,w-2*pad,row,MEDIA+'round_s.png','1AFFFFFF','<visible>Control.HasFocus(9501)</visible>','26')+
  lab(pad+36,y_time+row,300,row,'More','font_main')+
  img(w-pad-70,y_time+row+(row-56)//2,40,56,ICONS+'chevron-right.png','80EBEBF5')+
  '<control type="button" id="9501"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texturefocus /><texturenofocus />'
  '<onup>9401</onup></control>'%(pad,y_time+row,w-2*pad,row)+
  '</control>'+
  '<control type="group"><visible>!%s</visible>'%subs+
  img(pad+36,y_time+row-1,w-2*pad-36,2,MEDIA+'white.png','1FEBEBF5')+
  lab(pad+36,y_time+row,300,row,'Volume boost','font_main')+stepper(w-pad-372,y_time+row,9403,9404,'boost','<onup>9401</onup>')+
  '</control></control></control></control>')
 h_speed=y_list-lift+list_h+pad
 back=''.join(img(0,0,w,hh-(TRACK_ROWS-k)*row,MEDIA+'round_s.png','F52C2C2E','<visible>%s + String.IsEqual(Window().Property(rows),%d)</visible>'%(cond,k),'26')
              for cond,hh in (('%s + !%s'%(subs,sub),h_subs),('!%s + !%s'%(subs,speed),h_audio),('%s + %s'%(subs,sub),h_speed)) for k in range(1,TRACK_ROWS+1))
 back+=''.join(img(0,0,w,h_speed+(k-TRACK_ROWS)*row,MEDIA+'round_s.png','F52C2C2E','<visible>%s + String.IsEqual(Window().Property(rows),%d)</visible>'%(speed,k),'26')
               for k in range(1,SPEED_ROWS+1))
 more=''   # More is a row under Timing (mockup board 1)
 inner=('<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation><animation effect="fade" start="100" end="0" time="120">WindowClose</animation>'
  '<animation effect="slide" start="0,-24" end="0,0" time="220" tween="cubic" easing="out">WindowOpen</animation>'+
  back+lab(36,0,w-170,head,P('title'),'font_head_bold','FFFFFFFF','left','<visible>!%s</visible>'%sub)+
  # The sub-page's back link (9502): blue, where the title was; tracks.py goes one page up.
  '<control type="button" id="9502"><left>12</left><top>0</top><width>%d</width><height>%d</height><label>$INFO[Window().Property(back)]</label>'
  '<font>font_head_bold</font><textcolor>FF4FA8FF</textcolor><focusedcolor>FF64D2FF</focusedcolor><textoffsetx>24</textoffsetx><align>left</align><aligny>center</aligny>'
  '<texturefocus /><texturenofocus /><onright>9500</onright><ondown>9310</ondown><visible>%s</visible></control>'%(w-170,head,sub)+more+(img(w-97,16,75,75,MEDIA+'close_disc.png','2EFFFFFF')+img(w-97,16,75,75,MEDIA+'close_disc.png','24FFFFFF','<visible>Control.HasFocus(9500)</visible>')+img(w-74,39,29,29,MEDIA+'close_cross.png','B3EBEBF5')+'<control type="button" id="9500"><left>%d</left><top>-5</top><width>118</width><height>118</height><texturefocus /><texturenofocus /><ondown>9510</ondown></control>'%(w-118))+cta+audio)
 body=('<control type="button" id="9099"><left>0</left><top>0</top><width>100%</width><height>100%</height><texturefocus /><texturenofocus />'
  '<onclick>Close</onclick><onfocus>SetFocus(9310)</onfocus></control>'
  # Under the button that opened it: CC (subtitles), 140 in from the right (SAFE); Audio slides 190 left, under the
  # waveform. One copy of the controls (two copies would share their ids).
  '<control type="group"><right>140</right><top>172</top><width>'+str(w)+'</width>'
  '<animation effect="slide" start="0,0" end="-190,0" time="0" condition="!'+subs+'">Conditional</animation>'
  '<animation effect="slide" start="0,0" end="-180,0" time="0" condition="'+speed+'">Conditional</animation>'+inner+'</control>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: track menu r1 (navigation.patch_skin leaves this marker alone) -->\n'
         '<window type="dialog"><defaultcontrol always="true">9500</defaultcontrol><controls>%s</controls></window>\n')%body

# --- Kodi's busy dialog (DialogBusy: opening a video, buffering, loading a list) ---------------------------
# Build 191 (owner: a white badge with the Kodi logo over the Library posters, and a small spinner over the video
# "instead of the pill loader"): Fuse's DialogBusy, its Kodi logo in a white circle with a spinning arc made for
# the bottom-right corner of a 1920x1080 screen, was shrunk into the portrait screen as it is (so it floated over
# the poster grid) and left untouched in landscape (1080i, over the video). Both folders now get one pill in the
# middle of the screen: the glass of the activity pill, the open ring spinning, "Loading…". The 1080i copy carries
# the landscape marker (navigation.patch_skin leaves it alone) and is centred with centerleft/centertop, so it
# holds on the 2340-wide layout too. Progress 10 stays (Kodi drives it), never drawn.
BUSY='DialogBusy.xml'
def slide_bar(media,x,y,w,h=11,segment=0.36,time=1100,extra='',fill='FF0A84FF',track=True):
 """Indeterminate progress (DEC-036): the 20 % white track with a short blue segment sliding along it. Kodi cannot clip,
 so the segment moves between the two ends of the track. `extra` (a <visible> or animation) goes on both pieces."""
 seg=int(w*segment)
 return (('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture border="%d" colordiffuse="33FFFFFF">%sdot.png</texture>%s</control>'%(x,y,w,h,h//2,media,extra) if track else '')+
         '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture border="%d" colordiffuse="%s">%sdot.png</texture>'
         '<animation effect="slide" start="0,0" end="%d,0" time="%d" tween="sine" easing="inout" loop="true" condition="true">Conditional</animation>%s</control>')%(
         x,y,seg,h,h//2,fill,media,w-seg,time,extra)
def busy_dialog(marker,font,media='special://skin/extras/portrait/'):
 """DialogBusy: the opening card of owner-approved boards 04/05 (docs/design/fuse-windows-mockups.html). When the opener
 has set Window(home).Property(IOSOpen.Title) the card names the open ("Opening X", IOSOpen.Source, then stages 1-3
 from IOSOpen.Stage ticked as they finish, a sliding bar, and after about ten seconds IOSOpen.Slow in plain words).
 Cancel (9850) is Kodi's Back, which the busy dialog honours (roadmap 2.18). Any other wait is the white spinning
 circle in the middle of the screen, no card and no Cancel (owner, 2026-11-12, DEC-037: "I miss my white loading circle")."""
 w=720;pad=48;inner=w-2*pad;icons='special://skin/extras/icons/'
 title='Window(home).Property(IOSOpen.Title)';has='!String.IsEmpty(%s)'%title;no='String.IsEmpty(%s)'%title
 stage=lambda n:'Window(home).Property(IOSOpen.Stage)'
 def only(cond,body):return '<control type="group"><visible>%s</visible>%s</control>'%(cond,body)
 L=lambda x,y,wd,h,text,f,color,align='left',extra='':('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font>'
   '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><scroll>false</scroll><label>%s</label>%s</control>')%(x,y,wd,h,f,color,align,text,extra)
 stages=''
 for n,(doing,done) in enumerate((('Finding your copy…','Found your copy'),('Connecting…','Connected'),('Reading the file…','Read the file')),1):
  y=190+(n-1)*66
  at='Integer.IsEqual(Window(home).Property(IOSOpen.Stage),%d)'%n
  passed=' | '.join('Integer.IsEqual(Window(home).Property(IOSOpen.Stage),%d)'%k for k in range(n+1,5))
  stages+=(
   '<control type="image"><left>%d</left><top>%d</top><width>44</width><height>44</height><aspectratio>keep</aspectratio><texture colordiffuse="FF30D158">%scircle-check.png</texture><visible>%s</visible></control>'%(pad,y+11,icons,passed)+
   '<control type="image"><left>%d</left><top>%d</top><width>44</width><height>44</height><aspectratio>keep</aspectratio><texture colordiffuse="FF0A84FF">%scircle.png</texture><visible>%s</visible></control>'%(pad,y+11,icons,at)+
   '<control type="image"><left>%d</left><top>%d</top><width>44</width><height>44</height><aspectratio>keep</aspectratio><texture colordiffuse="33EBEBF5">%scircle.png</texture><visible>![%s | %s]</visible></control>'%(pad,y+11,icons,at,passed)+
   L(pad+66,y,inner-66,66,doing,'p_sub','FFFFFFFF','left','<visible>%s</visible>'%at)+
   L(pad+66,y,inner-66,66,done,'p_sub','99EBEBF5','left','<visible>%s</visible>'%passed)+
   L(pad+66,y,inner-66,66,doing.rstrip('…'),'p_sub','4DEBEBF5','left','<visible>![%s | %s]</visible>'%(at,passed)))
 long_h=720;short_h=340
 card=(
  '<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><texture border="40" colordiffuse="FFFFFFFF">%salert.png</texture><visible>%s</visible></control>'%(w,long_h,media,has)+

  only(has,L(pad,40,inner,64,'$INFO[%s,Opening ,]'%title,'p_h3','FFFFFFFF','center')+
       L(pad,104,inner,52,'$INFO[Window(home).Property(IOSOpen.Source)]','p_foot','99EBEBF5','center')+
       only('!String.IsEmpty(Window(home).Property(IOSOpen.Stage))',stages)+
       slide_bar(media,pad,420,inner)+
       # About ten seconds in, why it is slow, in the host's own words.
       '<control type="group"><visible>!String.IsEmpty(Window(home).Property(IOSOpen.Slow))</visible>'
       '<animation effect="fade" start="0" end="100" delay="10000" time="250">WindowOpen</animation>'+
       L(pad,452,inner,52,'Taking longer than usual.','p_foot_b','FFFFFFFF','center')+
       L(pad,500,inner,52,'$INFO[Window(home).Property(IOSOpen.Slow)]','p_foot','99EBEBF5','center')+'</control>')+
  # Owner (2026-11-12, Watch Options): any other wait is the white spinning circle again, no card and no Cancel
  # (Back still leaves); the card stays for opening a video, where its stages and Cancel help.
  only(no,'<control type="image"><left>%d</left><top>%d</top><width>96</width><height>96</height><texture colordiffuse="FFFFFFFF">%sring.png</texture>'
          '<animation effect="fade" start="0" end="100" time="200" delay="400">WindowOpen</animation>'
          '<animation effect="rotate" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation></control>'%((w-96)//2,(long_h-96)//2,media)))
 # One Cancel for both cards: secondary (a glass-styled capsule, 124 units), at the foot of whichever card shows.
 cancel=('<control type="button" id="9850"><left>%d</left><top>%d</top><width>%d</width><height>124</height><font>%s</font>'
  '<label>Cancel</label><textcolor>FFFFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>center</align><aligny>center</aligny>'
  '<texturefocus border="62" colordiffuse="FF5A5A5E">%spill_124.png</texturefocus><texturenofocus border="62" colordiffuse="FF3A3A3C">%spill_124.png</texturenofocus>'
  '<onclick>Action(Back)</onclick><visible>%s</visible></control>')%(
  pad,long_h-124-40,inner,font,media,media,has)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: Kodi busy dialog as the opening card -->\n<window><zorder>1000</zorder><controls>'
  '<control type="group"><centerleft>50%%</centerleft><centertop>50%%</centertop><width>%d</width><height>%d</height>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation>'
  '%s%s</control>'
  '<control type="group"><left>-4000</left><top>-4000</top><width>10</width><height>10</height><visible>false</visible>'
  '<control type="progress" id="10"><width>10</width><height>10</height><texturebg /><lefttexture /><midtexture /><righttexture /></control></control>'
  '</controls></window>\n')%(marker,w,long_h,card,cancel)

# Board 09, option A (owner, 2026-11-12): while Elementum's Burst asks the torrent sites, a card in the style of the
# opening card (board 04) says what is happening, instead of only the pill. Burst opens it (build_customized_ipa
# BURST_PATCHES: _kios_card) and keeps Window(home).Property(IOSSearch.*) up to date: Title, Answered, Total, Found, Pct.
# Stop (9801) ends the search and goes on with what was found; Cancel (9802) drops the search.
SEARCHING='IOSSearching.xml'
SEASON_QUALITY='IOSSeasonQuality.xml';SEASON_READY='IOSSeasonReady.xml'
def searching_card(p):
 """IOSSearching.xml (season-pack-mockups boards A and C, owner 2026-11-12): one card for every wait on sources. Burst's
 site search (build_customized_ipa BURST_CARD) and Build Season (season_sheet.Card) fill Window(home).Property(IOSSearch.*):
 Kicker (small grey line), Title, Lines (1-5) with Line.N.Text / .Count / .State (ok: green tick, wait: spinning ring,
 none: grey dash) and Pct for the bar. One full-width Cancel (9802); no Stop (owner: "I'd never press Stop")."""
 M=p.MEDIA;w=760;pad=44;inner=w-2*pad;top=196;lh=66;foot=40+11+40+124+40
 P=lambda k:'$INFO[Window(home).Property(IOSSearch.%s)]'%k
 lines_is=lambda n:'String.IsEqual(Window(home).Property(IOSSearch.Lines),%d)'%n
 height=lambda n:top+n*lh+foot
 backs=''.join(p.image(0,0,w,height(n),M+'alert.png',p.WHITE,'<visible>%s</visible>'%lines_is(n),border=40) for n in range(1,6))
 rows=''
 for n in range(1,6):
  y=top+(n-1)*lh;st=lambda v:'String.IsEqual(Window(home).Property(IOSSearch.Line.%d.State),%s)'%(n,v)
  has='!String.IsEmpty(Window(home).Property(IOSSearch.Line.%d.Text))'%n
  rows+=('<control type="group"><visible>%s</visible>'%has+
   p.image(pad,y+15,36,36,M+'dot.png','2E30D158','<visible>%s</visible>'%st('ok'))+
   p.icon(pad+7,y+22,22,'check.png','FF30D158','<visible>%s</visible>'%st('ok'))+
   p.image(pad,y+15,36,36,M+'ring.png','FF0A84FF','<visible>%s</visible><animation effect="rotate" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation>'%st('wait'))+
   p.image(pad,y+15,36,36,M+'dot.png','1FEBEBF5','<visible>%s</visible>'%st('none'))+
   p.image(pad+11,y+31,14,4,M+'white.png',p.GREY,'<visible>%s</visible>'%st('none'))+
   # A line without a count ("Looking for episode 13") gets the whole width (rig: it was cut short).
   p.label(pad+56,y,inner-56-220,lh,P('Line.%d.Text'%n),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>!String.IsEmpty(Window(home).Property(IOSSearch.Line.%d.Count))</visible>'%n)+
   p.label(pad+56,y,inner-56,lh,P('Line.%d.Text'%n),'p_body',p.WHITE,'left','<scroll>false</scroll><visible>String.IsEmpty(Window(home).Property(IOSSearch.Line.%d.Count))</visible>'%n)+
   p.label(pad+inner-220,y,220,lh,P('Line.%d.Count'%n),'p_foot',p.GREY,'right','<scroll>false</scroll>')+'</control>')
 pct='Window(home).Property(IOSSearch.Pct)'
 bar=(p.image(pad,0,inner,11,M+'dot.png','33FFFFFF',border=6)+
  ''.join(p.image(pad,0,max(11,inner*k//20),11,M+'dot.png','FF0A84FF','<visible>Integer.IsGreaterOrEqual(%s,%d)</visible>'%(pct,k*5),border=6) for k in range(1,21)))
 cancel=('<control type="button" id="9802"><left>%d</left><top>51</top><width>%d</width><height>124</height><font>p_btn</font><label>Cancel</label>'
  '<textcolor>FFFFFFFF</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>center</align><aligny>center</aligny>'
  '<texturefocus border="62" colordiffuse="FF5A5A5E">%spill_124.png</texturefocus><texturenofocus border="62" colordiffuse="FF3A3A3C">%spill_124.png</texturenofocus></control>')%(pad,inner,M,M)
 # The bar and Cancel sit under the last line: one step per line count (Kodi cannot measure).
 low=('<control type="group"><top>%d</top>'%(top+40)+
  ''.join('<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(n*lh,lines_is(n)) for n in range(1,6))+bar+cancel+'</control>')
 body=(backs+p.label(pad,36,inner,52,P('Kicker'),'p_foot',p.GREY,'center','<scroll>false</scroll>')+
  p.label(pad,92,inner,70,P('Title'),'p_h3',p.WHITE,'center','<scroll>false</scroll>')+rows+low)
 # Centred on the screen for every line count: the card's group moves up half of what it grows.
 centre=''.join('<animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'%(-(height(n)-height(1))//2,lines_is(n)) for n in range(2,6))
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS: searching / building card (season-pack boards A, C) -->\n<window type="dialog"><defaultcontrol always="true">9802</defaultcontrol><controls>'
  '<control type="image"><width>100%%</width><height>100%%</height><texture colordiffuse="8C000000">%swhite.png</texture></control>'
  '<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>%s'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation>'
  '%s</control></controls></window>\n')%(M,(p.WIDTH-w)//2,(p.HEIGHT-height(1))//2,w,height(5),centre,body)

def _sheet(p,name,comment,default,h,body):
 """A bottom sheet in the activity sheet's style (season-pack boards B and D): grabber, SURFACE, 38 pt top corners."""
 M=p.MEDIA;W=p.WIDTH
 anim=('<animation effect="slide" start="0,%d" end="0,0" time="300" tween="cubic" easing="out">WindowOpen</animation>'
       '<animation effect="slide" start="0,0" end="0,%d" time="220" tween="cubic" easing="in">WindowClose</animation>')%(h,h)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS: %s -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>'
  '<control type="image"><width>%d</width><height>%d</height><texture colordiffuse="8C000000">%swhite.png</texture>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation></control>'
  '<control type="group"><left>0</left><top>%d</top><width>%d</width><height>%d</height>%s'%(comment,default,W,p.HEIGHT,M,p.HEIGHT-h,W,h,anim)+
  p.image(0,0,W,h+140,M+'sheet_bg.png',p.SURFACE,border=102)+p.image((W-100)//2,22,100,14,M+'dot.png','4DFFFFFF',border=7)+
  body+'</control></controls></window>\n')

def _header(p,title,sub,y=70):
 """Poster (the show's) beside the large title and the grey line under it."""
 M=p.MEDIA;S=p.SIDE
 return (p.image(S,y,118,172,M+'white.png',p.SURFACE2,diffuse=M+'poster_mask.png')+
  p.image(S,y,118,172,'$INFO[Window(home).Property(IOSSeason.Poster)]',p.WHITE,'','>scale',M+'poster_mask.png',background=True)+
  p.label(S+150,y+30,p.WIDTH-2*S-150,74,title,'p_h2',p.WHITE,'left','<scroll>false</scroll>')+
  p.label(S+150,y+104,p.WIDTH-2*S-150,52,sub,'p_foot',p.GREY,'left','<scroll>false</scroll>'))

def _white_button(p,id,x,y,w,label,nav=''):
 M=p.MEDIA
 return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>140</height><font>p_btn</font><label>%s</label>'
  '<textcolor>FF000000</textcolor><focusedcolor>FF000000</focusedcolor><align>center</align><aligny>center</aligny>'
  '<texturefocus border="70" colordiffuse="FFFFFFFF">%spill_150.png</texturefocus><texturenofocus border="70" colordiffuse="FFFFFFFF">%spill_150.png</texturenofocus>'
  # White as in the mockups: it has the focus from the start, so a grey focus colour made it look pressed (rig).
  '%s</control>')%(id,x,y,w,label,M,M,nav)

def _text_button(p,id,x,y,w,label,nav=''):
 return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>118</height><font>p_btn</font><label>%s</label>'
  '<textcolor>%s</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>center</align><aligny>center</aligny><texturefocus /><texturenofocus />%s</control>')%(id,x,y,w,label,p.ACCENT,nav)

def season_quality_sheet(p):
 """IOSSeasonQuality.xml (season-pack board B round 2, Build Season only): the season and show, four quality cards
 (9701-9704; the chosen one outlined in blue with a tick), one sentence on what happens, Build (9720) and Cancel (9721).
 season_sheet.pick_quality fills Window().Property(...)."""
 M=p.MEDIA;S=p.SIDE;W=p.WIDTH;w=W-2*S;gap=27;cw=(w-gap)//2;ch=200
 P=lambda k:'$INFO[Window().Property(%s)]'%k
 grid_y=290;how_y=grid_y+2*ch+gap+40;btn_y=how_y+170;h=btn_y+140+20+118+60
 cards=''
 for n in range(1,5):
  x=S+((n-1)%2)*(cw+gap);y=grid_y+((n-1)//2)*(ch+gap);on='!String.IsEmpty(Window().Property(q.%d.on))'%n
  up,down,left,right={1:(9701,9703,9701,9702),2:(9702,9704,9701,9702),3:(9701,9720,9703,9704),4:(9702,9720,9703,9704)}[n]   # 2 x 2 grid, then Build
  nav='<onup>%d</onup><ondown>%d</ondown><onleft>%d</onleft><onright>%d</onright>'%(up,down,left,right)
  cards+=(p.image(x,y,cw,ch,M+'round.png','FF0A84FF','<visible>%s</visible>'%on,border=32)+
   p.image(x+6,y+6,cw-12,ch-12,M+'round.png','FF16273D','<visible>%s</visible>'%on,border=28)+
   p.image(x,y,cw,ch,M+'round.png',p.SURFACE2,'<visible>!%s</visible>'%on,border=32)+
   p.label(x+36,y+34,cw-130,80,P('q.%d.label'%n),'p_h2',p.WHITE,'left','<scroll>false</scroll>')+
   p.label(x+36,y+118,cw-60,50,P('q.%d.note'%n),'p_foot',p.GREY,'left','<scroll>false</scroll>')+
   p.image(x+cw-82,y+28,54,54,M+'dot.png','FF0A84FF','<visible>%s</visible>'%on)+p.icon(x+cw-70,y+40,30,'check.png',p.WHITE,'<visible>%s</visible>'%on)+
   '<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texturefocus colordiffuse="14FFFFFF" border="32">%sround.png</texturefocus><texturenofocus />%s</control>'%(9700+n,x,y,cw,ch,M,nav))
 body=(_header(p,P('season.title'),P('season.sub'))+cards+
  '<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>150</height><font>p_foot</font><textcolor>%s</textcolor><label>%s</label></control>'%(S+6,how_y,w-12,p.GREY,P('how'))+
  _white_button(p,9720,S,btn_y,w,P('button'),'<onup>9703</onup><ondown>9721</ondown>')+_text_button(p,9721,S,btn_y+150,w,'Cancel','<onup>9720</onup>'))
 return _sheet(p,SEASON_QUALITY,'Build Season quality sheet (board B)',9720,h,body)

def season_ready_sheet(p):
 """IOSSeasonReady.xml (season-pack board D round 2): the season, three numbers (episodes, quality, size), up to four
 episodes (number, name, an orange tag for a lower quality, size), "N more", one line on what was not in the quality,
 Download All (9730) and Cancel (9731). season_sheet.confirm_ready fills Window().Property(...)."""
 M=p.MEDIA;S=p.SIDE;W=p.WIDTH;w=W-2*S;gap=22;sw=(w-2*gap)//3;sh=150;rh=104
 P=lambda k:'$INFO[Window().Property(%s)]'%k;has=lambda k:'!String.IsEmpty(Window().Property(%s))'%k
 st_y=280;list_y=st_y+sh+34;rows_h=4*rh+rh;warn_y=list_y+rows_h+24;btn_y=warn_y+170;h=btn_y+140+20+118+60
 stats=''.join(p.image(S+i*(sw+gap),st_y,sw,sh,M+'round.png',p.SURFACE2,border=32)+
  p.label(S+i*(sw+gap)+30,st_y+22,sw-40,70,P(k),'p_h2',p.WHITE,'left','<scroll>false</scroll>')+
  p.label(S+i*(sw+gap)+30,st_y+90,sw-40,44,t,'p_foot',p.GREY,'left') for i,(k,t) in enumerate((('count','episodes'),('quality','quality'),('total','total'))))
 rows=p.image(S,list_y,w,rows_h,M+'round.png',p.SURFACE2,border=32)
 for n in range(1,5):
  y=list_y+(n-1)*rh;low=has('row.%d.low'%n)
  rows+=('<control type="group"><visible>%s</visible>'%has('row.%d.name'%n)+
   (p.image(S+110,y,w-110,2,M+'white.png',p.SEP) if n>1 else '')+
   p.label(S+20,y,70,rh,P('row.%d.no'%n),'p_foot_b',p.GREY,'right')+
   p.label(S+110,y,w-110-340,rh,P('row.%d.name'%n),'p_body',p.WHITE,'left','<scroll>false</scroll>')+
   '<control type="group"><visible>%s</visible>'%low+p.image(S+w-330,y+(rh-50)//2,120,50,M+'tag_line.png','FFFF9F0A',border=16)+
   p.label(S+w-330,y,120,rh,P('row.%d.low'%n),'p_cap','FFFF9F0A','center')+'</control>'+
   p.label(S+w-200,y,170,rh,P('row.%d.size'%n),'p_foot',p.GREY,'right')+'</control>')
 rows+=('<control type="group"><visible>%s</visible>'%has('more')+p.image(S+110,list_y+4*rh,w-110,2,M+'white.png',p.SEP)+
  p.label(S+110,list_y+4*rh,w-200,rh,P('more'),'p_body',p.ACCENT,'left')+'</control>')
 warn=(p.label(S+6,warn_y,40,56,'!','p_foot_b','FFFF9F0A','left','<visible>!%s</visible>'%has('ok'))+
  p.icon(S+6,warn_y+12,30,'check.png','FF30D158','<visible>%s</visible>'%has('ok'))+
  '<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>156</height><font>p_foot</font><textcolor>%s</textcolor><label>%s</label></control>'%(S+52,warn_y,w-58,p.GREY,P('warn')))
 body=(_header(p,P('title'),P('sub'))+stats+rows+warn+
  _white_button(p,9730,S,btn_y,w,P('button'),'<ondown>9731</ondown>')+_text_button(p,9731,S,btn_y+150,w,'Cancel','<onup>9730</onup>'))
 return _sheet(p,SEASON_READY,'Build Season ready sheet (board D)',9730,h,body)

# Build 192 (quick wins): Kodi's toasts and volume bar as iOS banners instead of Fuse's corner pill. The controls'
# Info (Custom_1193) is the episode card of board 08 (info_card). Kodi fills 400/401/402 (icon, heading, text) and
# moves 933 (volume); they stay, hidden, and the banner reads their labels.
NOTIFY='DialogNotification.xml';VOLUME='DialogVolumeBar.xml';INFO_WAIT='Custom_1193_VideoOSDInfo.xml'
def banner(marker,x,y,w,h,inner,extra=''):
 media='special://skin/extras/portrait/'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: iOS banner -->\n<window type="dialog"><zorder>1000</zorder>%s<controls>'
  '<control type="group"><left>%s</left><top>%d</top><width>%d</width><height>%d</height>'
  '<animation effect="slide" start="0,-%d" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>'
  '<animation effect="slide" start="0,0" end="0,-%d" time="220" tween="cubic" easing="in">WindowClose</animation>'
  '<animation effect="fade" start="100" end="0" time="200">WindowClose</animation>'
  '<control type="image"><left>0</left><top>0</top><width>%d</width><height>%d</height><texture border="%d" colordiffuse="F21C1C1E">%sgroup.png</texture></control>'
  '%s</control>%s</controls></window>\n')%(marker,'',x,y,w,h,y+h,y+h,w,h,min(70,h//2),media,inner,extra)
def notification_dialog(marker,x,y,w,big,small):
 h=170;icons='special://skin/extras/icons/';tile=110;tx=30+tile+30
 own='!String.StartsWith(Control.GetLabel(400),Default) + !String.IsEmpty(Control.GetLabel(400))'
 inner=('<control type="image"><left>30</left><top>30</top><width>%d</width><height>%d</height><texture colordiffuse="FF2C2C2E" border="28">special://skin/extras/portrait/tile100.png</texture></control>'%(tile,tile)+
  '<control type="image"><left>55</left><top>55</top><width>60</width><height>60</height><aspectratio>keep</aspectratio><texture colordiffuse="FFFFFFFF">%sbell.png</texture><visible>![%s]</visible></control>'%(icons,own)+
  '<control type="image"><left>30</left><top>30</top><width>%d</width><height>%d</height><aspectratio>keep</aspectratio><texture>$INFO[Control.GetLabel(400)]</texture><visible>%s</visible></control>'%(tile,tile,own)+
  '<control type="label"><left>%d</left><top>26</top><width>%d</width><height>60</height><font>%s</font><textcolor>FFFFFFFF</textcolor><aligny>center</aligny><label>$INFO[Control.GetLabel(401)]</label></control>'%(tx,w-tx-30,big)+
  '<control type="label"><left>%d</left><top>86</top><width>%d</width><height>60</height><font>%s</font><textcolor>FFAEAEB2</textcolor><aligny>center</aligny><scroll>true</scroll><label>$INFO[Control.GetLabel(402)]</label></control>'%(tx,w-tx-30,small))
 hidden=('<control type="image" id="400"><width>1</width><height>1</height><visible>false</visible></control>'
         '<control type="label" id="401"><width>1</width><height>1</height><visible>false</visible></control>'
         '<control type="label" id="402"><width>1</width><height>1</height><visible>false</visible></control>')
 return banner(marker,x,y,w,h,inner,hidden)
def volume_dialog(marker,x,y,w,font):
 h=120;icons='special://skin/extras/icons/';media='special://skin/extras/portrait/';bar=w-60-70-40-130
 inner=('<control type="image"><left>40</left><top>30</top><width>60</width><height>60</height><aspectratio>keep</aspectratio><texture colordiffuse="FFFFFFFF">%svolume-high.png</texture><visible>!Player.Muted</visible></control>'%icons+
  '<control type="image"><left>40</left><top>30</top><width>60</width><height>60</height><aspectratio>keep</aspectratio><texture colordiffuse="FFFF453A">%svolume-xmark.png</texture><visible>Player.Muted</visible></control>'%icons+
  '<control type="progress"><left>130</left><top>52</top><width>%d</width><height>16</height><info>Player.Volume</info>'
  '<texturebg border="8" colordiffuse="59FFFFFF">%spill_96.png</texturebg><midtexture border="8" colordiffuse="FFFFFFFF">%spill_96.png</midtexture>'
  '<lefttexture /><righttexture /><overlaytexture /></control>'%(bar,media,media)+
  '<control type="label"><left>%d</left><top>0</top><width>110</width><height>%d</height><font>%s</font><textcolor>FFFFFFFF</textcolor><align>right</align><aligny>center</aligny><label>$INFO[Control.GetLabel(933)]</label></control>'%(130+bar+10,h,font))
 hidden=('<control type="label" id="31"><width>1</width><height>1</height><visible>false</visible></control>'
         '<control type="progress" id="933"><width>1</width><height>1</height><visible>false</visible><info>Player.Volume</info></control>')
 return banner(marker,x,y,w,h,inner,hidden).replace('<zorder>1000</zorder>','<zorder>1001</zorder>',1)
def info_card():
 """1080i/Custom_1193_VideoOSDInfo.xml: Info in the video controls as an episode card (owner-approved board 08,
 docs/design/fuse-windows-mockups.html, roadmap U.6). It replaces Fuse's 1193, which only waited for TMDb Helper's
 details page and closed the controls. The card sits above the progress bar on the left, over the playing video:
 still, show, S·E, the episode title, the plot (four lines) and two tags (runtime, ends at). Everything comes from
 the playing item (library_play sets show, season, episode, plot and art: B.4); without metadata it shows what it
 has and a placeholder line, never an empty card. Kodi cannot blur, so the card is a flat 98 % opaque surface.
 Tap outside, the close button or Back closes it; the video keeps playing. Landscape canvas: 2.687 units/pt."""
 M='special://skin/extras/portrait/';I='special://skin/extras/icons/'
 left,bottom=150,795                      # the controls' left edge (player_osd.EDGE); 106 pt above the bottom
 pad=38;still_w,still_h=623,349;tx=pad+still_w+43;w=1505;close=118
 tw=w-tx-pad;meta_y=442;h=meta_y+56+pad;top=bottom-h
 episode='!String.IsEmpty(VideoPlayer.TVShowTitle)'
 has=lambda info:'!String.IsEmpty(%s)'%info
 def img(x,y,ww,hh,tex,color='FFFFFFFF',extra='',border='',diffuse=''):
  return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><texture%s%s colordiffuse="%s">%s</texture>%s</control>'
          %(x,y,ww,hh,' border="%s"'%border if border else '',' diffuse="%s"'%diffuse if diffuse else '',color,tex,extra))
 def lab(x,y,ww,hh,text,font,color='FFFFFFFF',extra=''):
  return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font><textcolor>%s</textcolor>'
          '<aligny>center</aligny><scroll>false</scroll><label>%s</label>%s</control>'%(x,y,ww,hh,font,color,text,extra))
 thumb,fanart='Player.Art(thumb)','Player.Art(fanart)'
 # A frame Kodi grabs from the file itself (image://video@...) is not a still: the placeholder shows instead.
 has=lambda info:'[!String.IsEmpty(%s)%s]'%(info,' + !String.StartsWith(%s,image://video@)'%info if info==thumb else '')
 still=(img(pad,pad,still_w,still_h,M+'white.png','FF1C1C1E',diffuse=M+'thumb_mask.png')+
  img(pad+(still_w-92)//2,pad+(still_h-92)//2,92,92,I+'film.png','4DEBEBF5','<aspectratio>keep</aspectratio><visible>!%s + !%s</visible>'%(has(thumb),has(fanart)))+
  '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><aspectratio>scale</aspectratio><fadetime>150</fadetime>'
  '<texture diffuse="%sthumb_mask.png" background="true">$INFO[%s]</texture><visible>%s</visible></control>'%(pad,pad,still_w,still_h,M,thumb,has(thumb))+
  '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><aspectratio>scale</aspectratio><fadetime>150</fadetime>'
  '<texture diffuse="%sthumb_mask.png" background="true">$INFO[%s]</texture><visible>!%s + %s</visible></control>'%(pad,pad,still_w,still_h,M,fanart,has(thumb),has(fanart)))
 grey='99EBEBF5'
 text=(lab(tx,44,tw-close,36,'[UPPERCASE]$INFO[VideoPlayer.TVShowTitle][/UPPERCASE]','font_midi_bold',grey,'<visible>%s</visible>'%episode)+
  lab(tx,44,tw-close,36,'[UPPERCASE]$INFO[VideoPlayer.Genre][/UPPERCASE]','font_midi_bold',grey,'<visible>!%s</visible>'%episode)+
  lab(tx,82,tw-close,44,'S$INFO[VideoPlayer.Season] · E$INFO[VideoPlayer.Episode]','font_head',grey,'<visible>%s</visible>'%episode)+
  lab(tx,82,tw-close,44,'$INFO[VideoPlayer.Year]','font_head',grey,'<visible>!%s</visible>'%episode)+
  lab(tx,128,tw,66,'$INFO[VideoPlayer.Title]','font_title_main')+
  '<control type="textbox"><left>%d</left><top>200</top><width>%d</width><height>186</height><font>font_head</font><textcolor>%s</textcolor>'
  '<autoscroll>false</autoscroll><label>$INFO[VideoPlayer.Plot]</label><visible>%s</visible></control>'%(tx,tw,grey,has('VideoPlayer.Plot'))+
  lab(tx,200,tw,52,'No description for this video yet.','font_head',grey,'<visible>!%s</visible>'%has('VideoPlayer.Plot')))
 tag=lambda id,text,cond='':('<control type="button" id="%d"><width min="120">auto</width><height>56</height><textoffsetx>22</textoffsetx>'
  '<font>font_main_bold</font><textcolor>%s</textcolor><disabledcolor>%s</disabledcolor><align>center</align><aligny>center</aligny><label>%s</label>'
  '<texturefocus border="16" colordiffuse="40EBEBF5">%stag_line.png</texturefocus><texturenofocus border="16" colordiffuse="40EBEBF5">%stag_line.png</texturenofocus>'
  '<enable>false</enable>%s</control>'%(id,grey,grey,text,M,M,'<visible>%s</visible>'%cond if cond else ''))
 meta=('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>56</height><orientation>horizontal</orientation><itemgap>21</itemgap>'%(pad,meta_y,w-2*pad)+
  tag(9601,'$INFO[Player.Duration(mins)] min',has('Player.Duration'))+tag(9602,'Ends at $INFO[Player.FinishTime]',has('Player.FinishTime'))+'</control>')
 card=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(left,top,w,h)+
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation>'
  '<animation effect="slide" start="0,24" end="0,0" time="240" tween="cubic" easing="out">WindowOpen</animation>'+
  img(0,0,w,h,M+'round_s.png','FA2C2C2E',border='26')+
  '<control type="button" id="9098"><width>%d</width><height>%d</height><texturefocus /><texturenofocus /><onfocus>SetFocus(9500)</onfocus></control>'%(w,h)+
  still+text+meta+close_button_1080(9500,w-close,0,'<onclick>Close</onclick>',close,92)+'</control>')
 body=('<control type="button" id="9099"><left>0</left><top>0</top><width>100%</width><height>100%</height><texturefocus /><texturenofocus />'
  '<onclick>Close</onclick><onfocus>SetFocus(9500)</onfocus></control>'+
  # The controls fade back behind the card (board 08); the video keeps playing.
  '<control type="image"><left>0</left><top>0</top><width>100%%</width><height>100%%</height><texture colordiffuse="8C000000">%swhite.png</texture>'
  '<animation effect="fade" start="0" end="100" time="200">WindowOpen</animation><animation effect="fade" start="100" end="0" time="150">WindowClose</animation></control>'%M+card)
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: info card (board 08) -->\n'
         '<window type="dialog" id="1193"><zorder>3</zorder><defaultcontrol always="true">9500</defaultcontrol><controls>%s</controls></window>\n')%body

HANDMADE={SEARCHING,SEASON_QUALITY,SEASON_READY,NOTIFY,VOLUME,'DialogConfirm.xml','DialogTextViewer.xml','DialogSettings.xml','AddonBrowser.xml','EventLog.xml','SettingsSystemInfo.xml','FileManager.xml',BUSY}

def files(p,read):
 out={p.FOLDER+'/DialogConfirm.xml':confirm_dialog(p,read('DialogConfirm.xml')),
      p.FOLDER+'/DialogTextViewer.xml':text_viewer(p,read('DialogTextViewer.xml')),
      p.FOLDER+'/DialogSettings.xml':settings_dialog(p,read('DialogSettings.xml')),
      p.FOLDER+'/AddonBrowser.xml':addon_browser(p,read('AddonBrowser.xml')),
      p.FOLDER+'/EventLog.xml':event_log(p,read('EventLog.xml')),
      p.FOLDER+'/SettingsSystemInfo.xml':system_info(p,read('SettingsSystemInfo.xml')),
      p.FOLDER+'/FileManager.xml':file_manager(p,read('FileManager.xml')),
      p.FOLDER+'/source_progress.xml':umbrella_ready(p),
      '1080i/IOSPlayOnTV.xml':play_on_tv(),
      '1080i/'+TRACK_MENU:track_menu(),   # owner-approved Subtitles / Audio menus (tracks.py)
      '1080i/IOSAirPlayFlow.xml':_airplay_flow().page(close_button_1080),   # owner-approved Play on TV boards (2026-11-08)
      p.FOLDER+'/'+BUSY:busy_dialog(p.MARKER,'p_pill'),
      p.FOLDER+'/'+SEARCHING:searching_card(p),   # boards 09 / season A, C
      p.FOLDER+'/'+SEASON_QUALITY:season_quality_sheet(p),p.FOLDER+'/'+SEASON_READY:season_ready_sheet(p),   # Build Season B, D
      '1080i/'+BUSY:busy_dialog('Kodi-iOS player controls: busy pill','font_main_bold'),
      p.FOLDER+'/'+NOTIFY:notification_dialog(p.MARKER,p.SIDE,150,p.WIDTH-2*p.SIDE,'p_foot_b','p_foot'),
      p.FOLDER+'/'+VOLUME:volume_dialog(p.MARKER,(p.WIDTH-640)//2,150,640,'p_foot_b'),
      # Landscape (video): centred at the top, clear of the island on either side.
      '1080i/'+NOTIFY:notification_dialog('Kodi-iOS player controls: notification','(1920-1100)/2',40,1100,'font_main_bold','font_midi').replace('<left>(1920-1100)/2</left>','<centerleft>50%</centerleft>'),
      '1080i/'+VOLUME:volume_dialog('Kodi-iOS player controls: volume','x',40,700,'font_main_bold').replace('<left>x</left>','<centerleft>50%</centerleft>')}
 out['1080i/'+INFO_WAIT]=info_card()
 out={k:v.encode() for k,v in out.items()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
