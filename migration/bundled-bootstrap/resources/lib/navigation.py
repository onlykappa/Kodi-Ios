"""Widget-independent native Kodi controls and idempotent, backed-up iOS upgrade."""
import hashlib,json,os,re,xml.etree.ElementTree as ET
from pathlib import Path
REVISION='ios-touch-navigation-r9'
GROUP=98100
HEADER=98200
BACK=98300
FRAME=98400
LEGACY='Kodi-iOS permanent navigation '
MARKER='Kodi-iOS touch header '+REVISION
BACK_MARKER='Kodi-iOS back/home '+REVISION
# Kodi keeps pixels square, so on a wide iPhone the 1080-high canvas is wider than 1920: anchor right-side items
# with <right>, never a fixed <left>.
FRAME_MARKER='Kodi-iOS safe-area frame '+REVISION
MENU='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)'
# Swipes move between rows only where Fuse stacks horizontal rows (hubs, search, info page). In ordinary lists
# a flick already scrolls natively; an extra Up there pushed focus out of the list.
TOUCH='''<keymap><global><touch><tap>LeftClick</tap><longpress>RightClick</longpress><pan>PanGesture</pan><tap pointers="3">ActivateWindow(settings)</tap><swipe direction="left" pointers="2">Back</swipe><swipe direction="right" pointers="2">RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)</swipe><swipe direction="up" pointers="2">PageUp</swipe><swipe direction="down" pointers="2">PageDown</swipe></touch></global><home><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></home><window11101><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11101><window11102><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11102><window11103><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11103><window11104><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11104><window11105><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11105><window11106><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11106><window11107><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11107><window11108><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11108><window11109><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></window11109><movieinformation><touch><swipe direction="up">Down</swipe><swipe direction="down">Up</swipe></touch></movieinformation></keymap>'''
DRIVE='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
UPDATES='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/check_updates.py)'
HUBS=['home','1101','1102','1103','1104']
RIGHT=['1106','1107','1108','1109']
ICONS='Skin.HasSetting(HomeSwitcher.EnableIcons)'
# Onloads written by earlier revisions; r3 rewrites them so focus is never forced onto injected controls.
OWN_ONLOADS={'SetFocus(98104)','Skin.Reset(Hub.Home.DisableSubmenu)','Skin.SetBool(homeswitcher.disablefirstwidgetfocus)','SetProperty(HomeSwitcher.IsVisible,True,Home)'}
ONLOADS=['Skin.Reset(Hub.Home.DisableSubmenu)','Skin.SetBool(homeswitcher.disablefirstwidgetfocus)','SetProperty(HomeSwitcher.IsVisible,True,Home)']
POWER=[{'icon':'special://skin/extras/icons/cloud.png','label':'Google Drive','path':DRIVE,'target':''},
       {'icon':'special://skin/extras/icons/cloud-arrow-down.png','label':'Check for updates','path':UPDATES,'target':''},
       {'icon':'special://skin/extras/icons/life-ring.png','label':'iPhone navigation / recovery','path':MENU,'target':''}]
# Rows that stay empty until a Trakt sign-in; an empty first row puts "No Results" in the hero title.
ACCOUNT=('info=trakt_',)
# Widgets that read the Deck's library or local files; empty on the phone until media is added.
LOCAL=('videodb://','special://profile/playlists/','special://skin/extras/playlists/','special://profile/media/')
SPOTLIGHT=[('Home','special://skin/extras/playlists/RandomMovies.xsp','plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&sort_by=popularity.desc','Popular Movies'),
           ('1102','special://skin/extras/playlists/RandomMovies.xsp','plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&sort_by=popularity.desc','Popular Movies'),
           ('1101','videodb://tvshows/titles/','plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&sort_by=popularity.desc','Popular TV Shows')]
def sha(data):return hashlib.sha256(data).hexdigest()
def element(parent,name,value,**attributes):
 node=ET.SubElement(parent,name,attributes);node.text=str(value);return node

def hub_visible(window):
 return 'true' if window=='home' else '!String.IsEmpty(Skin.String(HomeSwitcher.'+window+'.Toggle)) + $EXP[Exp_Hub_'+window+'_Available]'

def touch_button(parent,id,action,fields):
 c=ET.SubElement(parent,'control',{'type':'button','id':str(id)})
 for name,value in fields:element(c,name,value)
 element(c,'texturefocus','');element(c,'texturenofocus','');element(c,'onclick',action)
 # A tapped tab keeps focus; Down (a one-finger swipe up) must lead into the rows like Fuse's own hub menu.
 element(c,'ondown','$VAR[Hub_Action_Down]')
 return c

def header():
 """Tap targets over Fuse's header. The header is drawn by modeless dialog 1182, which Kodi never sends
 touches to, and its own hub switcher is an off-screen button driven by left/right only."""
 group=ET.Element('control',{'type':'group','id':str(HEADER)});element(group,'description',MARKER)
 element(group,'visible','System.Platform.IOS + !Skin.HasSetting(HomeSwitcher.Vertical) + !String.IsEmpty(Window(Home).Property(HomeSwitcher.IsVisible))')
 # Mirrors Home_Switcher_Horz geometry so each target lies exactly over its drawn tab or icon.
 inner=ET.SubElement(group,'control',{'type':'group'});element(inner,'include','Home_Group_Definition');element(inner,'include','Home_Reposition')
 touch_button(inner,HEADER+1,'ReplaceWindow(1105)',[('left',-20),('width',80),('height',80),('visible','!Skin.HasSetting(HomeSwitcher.DisableSearch)')])
 tabs=ET.SubElement(inner,'control',{'type':'grouplist'});element(tabs,'top',-100)
 icons=ET.SubElement(tabs,'include',{'content':'Object_Left','condition':ICONS});ET.SubElement(icons,'param',{'name':'left'}).text='-10'
 for name,value in [('left',-20),('orientation','horizontal'),('height',1080)]:element(tabs,name,value)
 for index,window in enumerate(HUBS):
  visible=hub_visible(window);label='$INFO[Skin.String(HomeSwitcher.'+window+'.Name)]';action='ReplaceWindow(Home)' if window=='home' else 'ReplaceWindow('+window+')'
  slot=ET.SubElement(tabs,'control',{'type':'group'})
  for name,value in [('top',100),('width',560),('height',80),('visible',visible)]:element(slot,name,value)
  hit=ET.SubElement(tabs,'control',{'type':'group'})
  for name,value in [('left',-480),('width',480),('top',100),('height',80),('visible',visible)]:element(hit,name,value)
  touch_button(hit,HEADER+10+index,action,[('font','font_main_bold'),('label',label),('width','auto'),('height',80),('textcolor','00ffffff'),('focusedcolor','00ffffff'),('visible','!'+ICONS)])
  touch_button(hit,HEADER+20+index,action,[('left',10),('width',80),('height',80),('visible',ICONS)])
  # Same advance as Home_Spacer, but disabled so it never takes a touch meant for the tab beside it.
  spacer=ET.SubElement(tabs,'control',{'type':'button'})
  for name,value in [('left',-560),('font','font_main_bold'),('textcolor','00ffffff'),('focusedcolor','00ffffff'),('disabledcolor','00ffffff'),('label',label),('height',80)]:element(spacer,name,value)
  width=ET.SubElement(spacer,'include',{'content':'Object_Width','condition':ICONS});ET.SubElement(width,'param',{'name':'width'}).text='100'
  for name,value in [('width','auto'),('centertop','50%'),('texturenofocus',''),('texturefocus',''),('enable','false'),('visible',visible)]:element(spacer,name,value)
 right=ET.SubElement(inner,'control',{'type':'grouplist'});element(right,'include','Home_Right_Group_Definition');element(right,'height',80);element(right,'centertop','50%')
 for index,(window,visible,action) in enumerate([(w,hub_visible(w),'ReplaceWindow('+w+')') for w in RIGHT]+[('1170','!$EXP[Exp_Hubs_Menu_Loopback]','ActivateWindow(1170)')]):
  slot=ET.SubElement(right,'control',{'type':'group'})
  for name,value in [('width',80),('height',80),('visible',visible)]:element(slot,name,value)
  touch_button(slot,HEADER+30+index,action,[('width',80),('height',80)])
 end=ET.SubElement(right,'control',{'type':'group'});element(end,'width',0)
 # While the spotlight's Play/More Information row has focus, Fuse fills the screen with the hero info and pushes
 # the rows to the bottom edge. A slow drag over that text reaches no list, so nothing scrolls; any touch there
 # moves focus to the rows instead, where a drag scrolls natively.
 hero=touch_button(group,HEADER+50,'$VAR[Hub_Action_Widgets]',[('left',0),('right',0),('top',230),('height',470),('visible','ControlGroup(310).HasFocus()'),('onfocus','$VAR[Hub_Action_Widgets]')])
 hero.remove(hero.find('ondown'))
 return group

def back_home():
 """Visible Back/Home for touch: these windows otherwise need a remote's Back button to leave."""
 group=ET.Element('control',{'type':'group','id':str(BACK)});element(group,'description',BACK_MARKER)
 for name,value in [('visible','System.Platform.IOS'),('right',60),('bottom',24),('width',420),('height',90)]:element(group,name,value)
 for index,(label,action) in enumerate([('Back','Action(Back)'),('Home','ActivateWindow(Home)')]):
  c=ET.SubElement(group,'control',{'type':'button','id':str(BACK+1+index)})
  # Bottom-right corner: free on Fuse's media and settings screens, clear of the header clock.
  for name,value in [('left',index*220),('width',200),('height',90),('label',label),('font','font_main_bold'),('align','center'),('aligny','center'),('textcolor','FFFFFFFF'),('focusedcolor','FF000000'),('onclick',action),('onleft',BACK+1),('onright',BACK+2)]:element(c,name,value)
  element(c,'texturefocus','common/menu.png',border='40',colordiffuse='FFFFFFFF');element(c,'texturenofocus','common/menu.png',border='40',colordiffuse='40FFFFFF')
 return group

def frame():
 """Black bars over the iPhone safe areas: Fuse's 200% blurred background and poster rows draw past the canvas."""
 group=ET.Element('control',{'type':'group','id':str(FRAME)});element(group,'description',FRAME_MARKER);element(group,'visible','System.Platform.IOS')
 for edges in [[('left',-1000),('top',-1000),('width',1000),('bottom',-1000)],[('right',-1000),('top',-1000),('width',1000),('bottom',-1000)],
               [('left',-1000),('right',-1000),('top',-1000),('height',1000)],[('left',-1000),('right',-1000),('bottom',-1000),('height',1000)]]:
  image=ET.SubElement(group,'control',{'type':'image'})
  for name,value in edges:element(image,name,value)
  element(image,'texture','common/white.png',colordiffuse='FF000000')
 return group

def patch_frame(data,filename):
 if filename in {'Pointer.xml'}:return data
 root=ET.fromstring(data)
 controls=root.find('controls')
 if root.tag!='window' or controls is None:return data
 old=controls.find("control[@id='"+str(FRAME)+"']")
 if not owned(old,'Kodi-iOS safe-area frame '):raise ValueError('Navigation control ID collision')
 # Last child, so it is drawn over anything that spills into the bars.
 if old is not None and old.findtext('description')==FRAME_MARKER and list(controls)[-1] is old:return data
 if old is not None:controls.remove(old)
 controls.append(frame());ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'

def owned(control,prefix):
 return control is None or (control.findtext('description') or '').startswith(prefix)

def patch_window(data,filename):
 root=ET.fromstring(data)
 # Kodi identifies many dialogs by filename without a type=dialog attribute.
 hub=filename=='Home.xml' or re.fullmatch(r'Custom_110[1-9]_(Hub|Search)\.xml',filename)
 major=hub or filename.startswith('My') or filename in {'Settings.xml','SettingsCategory.xml','SettingsProfile.xml','SettingsSystemInfo.xml','SkinSettings.xml','AddonBrowser.xml','FileManager.xml','EventLog.xml'}
 if not major:return data
 if root.tag!='window' or root.get('type')=='dialog' or filename in {'VideoFullScreen.xml','FullscreenVideo.xml','Startup.xml'}:return data
 controls=root.find('controls')
 if controls is None:return data
 legacy=controls.find("control[@id='"+str(GROUP)+"']");previous=controls.find("control[@id='"+str(HEADER)+"']")
 if not owned(legacy,LEGACY) or not owned(previous,'Kodi-iOS touch header '):raise ValueError('Navigation control ID collision')
 if not hub:
  # r2 placed a fixed bar over every major window; it covered content. A small Back/Home pair replaces it.
  back=controls.find("control[@id='"+str(BACK)+"']")
  if not owned(back,'Kodi-iOS back/home '):raise ValueError('Navigation control ID collision')
  if legacy is None and back is not None and back.findtext('description')==BACK_MARKER:return data
  for old in (legacy,back):
   if old is not None:controls.remove(old)
  controls.append(back_home());ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'
 if legacy is None and previous is not None and previous.findtext('description')==MARKER:return data
 for old in (legacy,previous):
  if old is not None:controls.remove(old)
 for old in list(root.findall('defaultcontrol')):
  if (old.text or '').strip()=='98104':root.remove(old)
 for node in list(root):
  if node.tag=='onload' and (node.text or '') in OWN_ONLOADS and node.get('condition')=='System.Platform.IOS':root.remove(node)
 if filename=='Home.xml' or 'Hub' in filename:
  # Prevent onload helpers/reload alarms from racing Kodi's Keep Skin dialog.
  lock='String.IsEmpty(Window(Home).Property(KodiIOS.Activating))'
  for node in list(root):
   action=node.text or ''
   if (node.tag=='onload' and ('runscript(' in action.lower() or 'reloadskin' in action.lower())) or (node.tag=='include' and action in {'Action_BuildViews','Action_BuildShortcuts_OnLoad'}):
    if lock not in node.get('condition',''):node.set('condition','['+node.get('condition','true')+'] + '+lock)
 for action in ONLOADS:
  node=ET.Element('onload',{'condition':'System.Platform.IOS'});node.text=action;root.insert(list(root).index(controls),node)
 controls.append(header())
 ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'

INCLUDES={'Includes_Home.xml','Includes_Hubs.xml','Includes_Actions.xml','Includes_Search.xml','Includes_Background.xml'}
# Fuse also builds widget rows on the device from these templates; they clear the header flag on focus too.
TEMPLATES='shortcuts/generator/data/parts'
# The 150% fanart zoom on focus reads as a broken, zoomed-in screen inside the iPhone's safe area.
ZOOM=(b'<animation type="Conditional" condition="$PARAM[condition]">\n            <effect type="zoom" start="100" end="flixart_zoom_p"',b'<animation type="Conditional" condition="[$PARAM[condition]] + !System.Platform.IOS">\n            <effect type="zoom" start="100" end="flixart_zoom_p"')
# D-pad behaviour disabled on iOS only: Fuse hides the header whenever a widget gains focus, and an Up/Left/Info
# opens submenu 1181 or bumper 1180, modal dialogs that dim the screen and swallow every tap.
IOS_OFF=[rb'ClearProperty\(HomeSwitcher\.IsVisible,Home\)',rb'ActivateWindow\(118[01]\)']

def patch_includes(data):
 def guard(match):
  condition=b'!System.Platform.IOS' if match.group(2) is None else b'['+match.group(2)+b'] + !System.Platform.IOS'
  return b'<'+match.group(1)+b' condition="'+condition+b'">'+match.group(3)+b'</'+match.group(1)+b'>'
 for action in IOS_OFF:data=re.sub(rb'<(on\w+)(?: condition="((?:(?!System\.Platform\.IOS)[^"])*)")?>('+action+rb')</\1>',guard,data)
 return data.replace(*ZOOM)

def patch_skin(skin,backup=None):
 skin=Path(skin);changed=[]
 for path in sorted((skin/'1080i').glob('*.xml'))+sorted((skin/TEMPLATES).glob('*.xmltemplate')):
  if path.is_symlink():raise ValueError('Skin XML symlink refused')
  before=path.read_bytes()
  if path.suffix=='.xmltemplate' or path.name in INCLUDES:after=patch_includes(before)
  else:after=patch_frame(patch_window(before,path.name),path.name)
  if before==after:continue
  if backup is not None:
   dest=Path(backup)/path.name
   if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(before)
  temp=path.with_name(path.name+'.ios-nav-tmp');temp.write_bytes(after);os.replace(temp,path)
  changed.append({'path':path.relative_to(skin).as_posix(),'before_sha256':sha(before),'after_sha256':sha(after)})
 return changed

def upgrade(home,profile):
 home=Path(home);profile=Path(profile);skin=home/'addons/skin.arctic.fuse.3'
 if not skin.is_dir():return {'revision':REVISION,'status':'WAITING FOR WRITABLE SKIN','changed_files':0}
 if skin.is_symlink() or any(p.is_symlink() for p in [home,profile,*skin.parents]):raise ValueError('Navigation upgrade symlink refused')
 state=profile/'addon_data/service.kodi.ios.bootstrap';backup=state/'navigation-backup'/REVISION
 changed=patch_skin(skin,backup)
 keymap=profile/'keymaps/zz-kodi-ios-navigation.xml';body=TOUCH.encode()+b'\n'
 key_changed=not keymap.exists() or keymap.read_bytes()!=body
 if key_changed:
  if keymap.is_symlink():raise ValueError('Keymap symlink refused')
  if keymap.exists():
   dest=backup/'previous-touch-keymap.xml';dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():dest.write_bytes(keymap.read_bytes())
  keymap.parent.mkdir(parents=True,exist_ok=True);keymap.write_bytes(body)
 state.mkdir(parents=True,exist_ok=True);receipt={'revision':REVISION,'status':'PATCHED','changed_files':len(changed),'keymap_changed':key_changed,'files':changed,'device_navigation_verified':False}
 if changed or key_changed or not (state/'navigation-upgrade.json').exists():(state/'navigation-upgrade.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return receipt

def update_nodes(profile):
 """Phone menu contents: Drive and recovery in the gear menu, and widgets that can load on a phone first."""
 profile=Path(profile);nodes=profile/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3'
 backup=profile/'addon_data/service.kodi.ios.bootstrap/navigation-backup'/REVISION/'nodes';changed=[]
 def edit(name,change):
  path=nodes/name
  if not path.is_file():return
  if path.is_symlink():raise ValueError('Menu node symlink refused')
  before=path.read_bytes();items=json.loads(before)
  if not isinstance(items,list):raise ValueError('Unexpected menu node format')
  items=change(items);after=json.dumps(items,indent=2,ensure_ascii=False).encode()+b'\n'
  if items==json.loads(before):return
  dest=backup/name
  if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(before)
  temp=path.with_name(name+'.ios-nav-tmp');temp.write_bytes(after);os.replace(temp,path);changed.append(name)
 def power(items):
  items=[dict(item) for item in items]
  for item in items:
   # The Deck's Quit entry was retargeted to Settings, but still showed the Quit label.
   if (item.get('path') or '').lower()=='activatewindow(settings)' and item.get('label')=='$LOCALIZE[13009]':item['label']='$LOCALIZE[5]'
  paths=[(item.get('path') or '').lower() for item in items]
  at=paths.index('activatewindow(settings)') if 'activatewindow(settings)' in paths else len(items)
  for extra in POWER:
   if extra['path'].lower() not in paths:items.insert(at,dict(extra));at+=1
  return items
 def phone_first(items):
  def rank(item):
   path=(item.get('path') or '').lower()
   return 2 if path.startswith(LOCAL) else 1 if any(a in path for a in ACCOUNT) else 0
  return sorted(items,key=rank)
 edit('skinvariables-shortcut-powermenu.json',power)
 for name in ['skinvariables-shortcut-homewidgets.json','skinvariables-shortcut-1101widgets.json','skinvariables-shortcut-1102widgets.json']:edit(name,phone_first)
 return changed

def phone_defaults(read_skin,builtin):
 """Point untouched library spotlights at TMDb so the hero banner is not an empty library query."""
 quote=lambda text:'"'+str(text).replace('\\','\\\\').replace('"','\\"')+'"'
 changed=[]
 for window,old,new,label in SPOTLIGHT:
  key='HomeSwitcher.'+window+'.Spotlight.'
  if read_skin(key+'Path')!=old:continue
  builtin('Skin.SetString('+quote(key+'Path')+','+quote(new)+')');builtin('Skin.SetString('+quote(key+'Label')+','+quote(label)+')');changed.append(window)
 return changed


def sync_skin_preferences(seed,api,builtin,read_skin=None):
 """Synchronize loaded state; verify values rather than the setter's assigned-value result."""
 path=Path(seed)/'addon_data/skin.arctic.fuse.3/settings.xml'
 if not path.exists():return 0
 def set_value(id,value):
  response=api('Settings.SetSkinSettingValue',{'setting':id,'value':value})
  if 'error' in response:
   # Kodi's API cannot create an unknown skin setting; the standard builtin can.
   quote=lambda text:'"'+str(text).replace('\\','\\\\').replace('"','\\"')+'"'
   command='Skin.SetBool('+quote(id)+','+('true' if value else 'false')+')' if isinstance(value,bool) else 'Skin.SetString('+quote(id)+','+quote(value or '__kodi_ios_seed__')+')'
   builtin(command)
   if value=='':builtin('Skin.Reset('+quote(id)+')')
  result=api('Settings.GetSkinSettingValue',{'setting':id})
  if 'error' not in result:actual=result.get('result',{}).get('value')
  elif read_skin is not None:actual=read_skin(id,isinstance(value,bool))
  else:raise RuntimeError('Skin preference readback unavailable')
  if actual!=value:raise RuntimeError('Skin preference readback failed')
 count=0
 for setting in ET.parse(path).getroot().findall('setting'):
  id=setting.get('id')
  if not id or id.lower() in {'script-skinviewtypes-hash','script-skinviewtypes-checksum','shortcuts.rebuilddatetime'}:continue
  value=(setting.text or '').lower()=='true' if setting.get('type')=='bool' else setting.text or ''
  if id.lower()=='hub.home.disablesubmenu':value=False
  if id.lower()=='homeswitcher.disablefirstwidgetfocus':value=True
  set_value(id,value);count+=1
 for id,value in [('script-skinviewtypes-hash',''),('Shortcuts.RebuildDateTime',REVISION)]:set_value(id,value)
 # This normal builtin also requests Kodi's core Settings.Save, unlike the raw JSON setter.
 builtin('Skin.SetBool(homeswitcher.disablefirstwidgetfocus,true)')
 return count
