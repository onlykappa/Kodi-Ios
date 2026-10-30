"""Widget-independent native Kodi controls and idempotent, backed-up iOS upgrade."""
import hashlib,json,os,re,xml.etree.ElementTree as ET
from pathlib import Path
REVISION='ios-touch-navigation-r1'
GROUP=98100
MARKER='Kodi-iOS permanent navigation '+REVISION
MENU='RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)'
TOUCH='''<keymap><global><touch><tap>LeftClick</tap><longpress>RightClick</longpress><pan>PanGesture</pan><tap pointers="3">ActivateWindow(settings)</tap><swipe direction="left" pointers="2">Back</swipe><swipe direction="right" pointers="2">RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/navigation_menu.py)</swipe><swipe direction="up" pointers="2">PageUp</swipe><swipe direction="down" pointers="2">PageDown</swipe></touch></global></keymap>'''
ACTIONS=[('Back','Action(Back)'),('Home','ActivateWindow(home)'),('Browse',MENU),('Settings','ActivateWindow(settings)'),('Drive','ActivateWindow(Videos,plugin://plugin.googledrive/,return)'),('Recovery',MENU)]
def sha(data):return hashlib.sha256(data).hexdigest()
def element(parent,name,value,**attributes):
 node=ET.SubElement(parent,name,attributes);node.text=str(value);return node

def bar():
 group=ET.Element('control',{'type':'group','id':str(GROUP)});element(group,'description',MARKER);element(group,'visible','System.Platform.IOS')
 # 1920x1080 skin coordinates: inset from edges/home indicator, large independent targets.
 element(group,'left','5%');element(group,'top',884);element(group,'width','90%');element(group,'height',136)
 for index,(label,action) in enumerate(ACTIONS):
  c=ET.SubElement(group,'control',{'type':'button','id':str(GROUP+index+1)})
  for name,value in [('left',str(round(index*100/6,3))+'%'),('top',0),('width','16%'),('height',136),('label',label),('font','font_main'),('textcolor','FFFFFFFF'),('focusedcolor','FFFFFFFF'),('align','center'),('aligny','center'),('onclick',action),('onleft',GROUP+(index-1)%6+1),('onright',GROUP+(index+1)%6+1),('onup','SetFocus(501)')]:element(c,name,value)
  element(c,'texturefocus','common/white.png',colordiffuse='FF315C88');element(c,'texturenofocus','common/white.png',colordiffuse='ED181B26')
 return group

def patch_window(data,filename):
 root=ET.fromstring(data)
 # Kodi identifies many dialogs by filename without a type=dialog attribute.
 major=filename.startswith('My') or filename in {'Home.xml','Settings.xml','SettingsCategory.xml','SettingsProfile.xml','SettingsSystemInfo.xml','SkinSettings.xml','AddonBrowser.xml','FileManager.xml','EventLog.xml'} or re.fullmatch(r'Custom_110[1-9]_(Hub|Search)\.xml',filename)
 if not major:return data
 if root.tag!='window' or root.get('type')=='dialog' or filename in {'VideoFullScreen.xml','FullscreenVideo.xml','Startup.xml'}:return data
 controls=root.find('controls')
 if controls is None:return data
 previous=controls.find("control[@id='98100']")
 if previous is not None:
  if previous.findtext('description')==MARKER:return data
  raise ValueError('Navigation control ID collision')
 controls.append(bar())
 if filename=='Home.xml' or 'Hub' in filename:
  for old in list(root.findall('defaultcontrol')):root.remove(old)
  default=ET.Element('defaultcontrol',{'always':'true'});default.text='98104';root.insert(0,default)
  for action in ['Skin.Reset(Hub.Home.DisableSubmenu)','Skin.SetBool(homeswitcher.disablefirstwidgetfocus)','SetFocus(98104)']:
   node=ET.Element('onload',{'condition':'System.Platform.IOS'});node.text=action;root.insert(list(root).index(controls),node)
 ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'

def patch_skin(skin,backup=None):
 skin=Path(skin);changed=[]
 for path in sorted((skin/'1080i').glob('*.xml')):
  if path.is_symlink():raise ValueError('Skin XML symlink refused')
  before=path.read_bytes();after=patch_window(before,path.name)
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


def sync_skin_preferences(seed,api,builtin):
 """Synchronize loaded state; verify values rather than the setter's assigned-value result."""
 path=Path(seed)/'addon_data/skin.arctic.fuse.3/settings.xml'
 if not path.exists():return 0
 def set_value(id,value):
  response=api('Settings.SetSkinSettingValue',{'setting':id,'value':value})
  if 'error' in response:
   # Kodi's API cannot create an unknown skin setting; the standard builtin can.
   quote=lambda text:'"'+str(text).replace('\\','\\\\').replace('"','\\"')+'"'
   command='Skin.SetBool('+quote(id)+','+('true' if value else 'false')+')' if isinstance(value,bool) else 'Skin.SetString('+quote(id)+',__kodi_ios_seed__)'
   builtin(command)
   if not isinstance(value,bool):
    if 'error' in api('Settings.SetSkinSettingValue',{'setting':id,'value':value}):raise RuntimeError('Skin string registration failed')
  result=api('Settings.GetSkinSettingValue',{'setting':id})
  if 'error' in result or result.get('result',{}).get('value')!=value:raise RuntimeError('Skin preference readback failed')
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
