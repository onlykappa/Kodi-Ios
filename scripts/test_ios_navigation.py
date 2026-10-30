import importlib.util,json,shutil,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ios_navigation_test',ROOT/'migration/bundled-bootstrap/resources/lib/navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
HOME=b'<window><onload>OriginalAction()</onload><controls><include>missing-generated-menu</include><control type="list" id="501"><content>videodb://movies/titles/</content></control></controls></window>'
class NavigationTests(unittest.TestCase):
 def header(self,data=HOME,name='Home.xml'):return ET.fromstring(nav.patch_window(data,name)).find("controls/control[@id='98200']")
 def test_every_hub_tab_has_a_touch_target(self):
  group=self.header();self.assertTrue(group.findtext('visible').startswith('System.Platform.IOS'))
  actions=[b.findtext('onclick') for b in group.iter('control') if b.get('type')=='button' and b.get('id')]
  for action in ['ReplaceWindow(1105)','ReplaceWindow(Home)','ReplaceWindow(1101)','ReplaceWindow(1102)','ReplaceWindow(1103)','ReplaceWindow(1104)','ActivateWindow(1170)']:self.assertIn(action,actions)
 def test_spacers_cannot_steal_tab_touches(self):
  spacers=[b for b in self.header().iter('control') if b.get('type')=='button' and not b.get('id')]
  self.assertEqual(len(spacers),5)
  for b in spacers:self.assertEqual(b.findtext('enable'),'false');self.assertIsNone(b.find('onclick'))
 def test_focus_is_not_forced_onto_injected_controls(self):
  root=ET.fromstring(nav.patch_window(HOME,'Home.xml'));self.assertIsNone(root.find('defaultcontrol'));actions=[x.text for x in root.findall('onload')]
  self.assertIn('OriginalAction()',actions);self.assertNotIn('SetFocus(98104)',actions);self.assertIn('SetProperty(HomeSwitcher.IsVisible,True,Home)',actions)
 def test_r2_bar_is_removed_from_every_window(self):
  bar=b'<control type="group" id="98100"><description>Kodi-iOS permanent navigation ios-touch-navigation-r2</description></control>'
  r2=b'<window><defaultcontrol always="true">98104</defaultcontrol><onload condition="System.Platform.IOS">SetFocus(98104)</onload><controls>'+bar+b'</controls></window>'
  root=ET.fromstring(nav.patch_window(r2,'Home.xml'));self.assertIsNone(root.find('defaultcontrol'));self.assertNotIn('SetFocus(98104)',[x.text for x in root.findall('onload')])
  for name in ['Home.xml','Settings.xml','MyVideoNav.xml']:self.assertIsNone(ET.fromstring(nav.patch_window(b'<window><controls>'+bar+b'</controls></window>',name)).find("controls/control[@id='98100']"))
  self.assertEqual(nav.patch_window(b'<window><controls/></window>','Settings.xml'),b'<window><controls/></window>')
 def test_header_stays_visible_on_ios_only(self):
  data=b'<a><onfocus>ClearProperty(HomeSwitcher.IsVisible,Home)</onfocus><onfocus condition="![$PARAM[x]]">ClearProperty(HomeSwitcher.IsVisible,Home)</onfocus></a>'
  once=nav.patch_includes(data);self.assertEqual(nav.patch_includes(once),once)
  self.assertEqual([x.get('condition') for x in ET.fromstring(once)],['!System.Platform.IOS','[![$PARAM[x]]] + !System.Platform.IOS'])
 def test_gear_menu_gets_drive_and_recovery_and_widgets_put_phone_rows_first(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);nodes=p/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3';nodes.mkdir(parents=True)
   (nodes/'skinvariables-shortcut-powermenu.json').write_text(json.dumps([{'label':'$LOCALIZE[1036]','path':'ActivateWindow(1160)'},{'label':'$LOCALIZE[13009]','path':'ActivateWindow(Settings)'}]))
   (nodes/'skinvariables-shortcut-homewidgets.json').write_text(json.dumps([{'label':'In Progress','path':'special://profile/playlists/video/x.xsp'},{'label':'Popular','path':'plugin://plugin.video.themoviedb.helper/?info=discover'},{'label':'Local','path':'videodb://movies/titles/'}]))
   self.assertEqual(len(nav.update_nodes(p)),2);self.assertEqual(nav.update_nodes(p),[])
   power=json.loads((nodes/'skinvariables-shortcut-powermenu.json').read_text())
   self.assertEqual([x['path'] for x in power],['ActivateWindow(1160)',nav.DRIVE,nav.MENU,'ActivateWindow(Settings)']);self.assertEqual(power[-1]['label'],'$LOCALIZE[5]')
   self.assertEqual([x['label'] for x in json.loads((nodes/'skinvariables-shortcut-homewidgets.json').read_text())],['Popular','In Progress','Local'])
   self.assertTrue((p/'addon_data/service.kodi.ios.bootstrap/navigation-backup'/nav.REVISION/'nodes/skinvariables-shortcut-powermenu.json').exists())
 def test_spotlight_only_replaces_untouched_library_defaults(self):
  values={'HomeSwitcher.Home.Spotlight.Path':'special://skin/extras/playlists/RandomMovies.xsp','HomeSwitcher.1101.Spotlight.Path':'plugin://owner.choice/'};calls=[]
  self.assertEqual(nav.phone_defaults(lambda k:values.get(k,''),calls.append),['Home']);self.assertTrue(all('HomeSwitcher.Home.' in c for c in calls))
 def test_longpress_pan_settings_and_navigation_gestures(self):
  r=ET.fromstring(nav.TOUCH);self.assertEqual(r.findtext('global/touch/longpress'),'RightClick');self.assertEqual(r.findtext('global/touch/pan'),'PanGesture');self.assertEqual(r.findtext("global/touch/tap[@pointers='3']"),'ActivateWindow(settings)');self.assertEqual(r.findtext("global/touch/swipe[@direction='right']"),nav.MENU)
 def test_preserves_dialogs_and_playback(self):
  for data,name in [(b'<window type="dialog"><controls/></window>','DialogSelect.xml'),(b'<window><controls/></window>','VideoFullScreen.xml'),(b'<window><controls/></window>','DialogKeyboard.xml'),(b'<window><controls/></window>','Pointer.xml'),(b'<window><controls/></window>','VideoOSD.xml')]:self.assertEqual(nav.patch_window(data,name),data)
 def test_patch_is_byte_idempotent(self):
  once=nav.patch_window(HOME,'Home.xml');self.assertEqual(nav.patch_window(once,'Home.xml'),once)
 def test_id_conflict_fails_instead_of_overwriting_owner_control(self):
  for id in ['98100','98200']:
   with self.assertRaises(ValueError):nav.patch_window(b'<window><controls><control id="'+id.encode()+b'" type="button"/></controls></window>','Home.xml')
 def test_upgrade_applies_to_already_completed_profile_and_preserves_backup(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);skin=base/'addons/skin.arctic.fuse.3/1080i';skin.mkdir(parents=True);(skin/'Home.xml').write_bytes(HOME)
   p=base/'userdata';state=p/'addon_data/service.kodi.ios.bootstrap';state.mkdir(parents=True);(state/'status.json').write_text('{"status":"COMPLETE"}')
   first=nav.upgrade(base,p);self.assertEqual(first['changed_files'],1);self.assertEqual(json.loads((state/'status.json').read_text())['status'],'COMPLETE');self.assertEqual((state/'navigation-backup'/nav.REVISION/'Home.xml').read_bytes(),HOME)
   second=nav.upgrade(base,p);self.assertEqual(second['changed_files'],0);self.assertFalse(second['keymap_changed']);self.assertEqual((state/'navigation-backup'/nav.REVISION/'Home.xml').read_bytes(),HOME)
 def test_safe_without_writable_skin(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual(nav.upgrade(Path(t),Path(t)/'userdata')['status'],'WAITING FOR WRITABLE SKIN')
 def test_bad_xml_fails_without_damaging_existing_file(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'1080i';p.mkdir();(p/'Home.xml').write_bytes(b'<window>broken')
   with self.assertRaises(ET.ParseError):nav.patch_skin(Path(t))
   self.assertEqual((p/'Home.xml').read_bytes(),b'<window>broken')
 def test_live_skin_false_and_string_return_values_are_verified_by_readback(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'addon_data/skin.arctic.fuse.3/settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="flag" type="bool">false</setting><setting id="label" type="string">a,b (test)</setting></settings>')
   values={};calls=[]
   def api(method,params):
    if method.endswith('SetSkinSettingValue'):values[params['setting']]=params['value'];return {'result':params['value']}
    return {'result':{'value':values[params['setting']]}}
   self.assertEqual(nav.sync_skin_preferences(Path(t),api,calls.append),2);self.assertFalse(values['flag']);self.assertEqual(values['label'],'a,b (test)');self.assertEqual(calls[-1],'Skin.SetBool(homeswitcher.disablefirstwidgetfocus,true)')
 def test_live_skin_readback_failure_is_not_ignored(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'addon_data/skin.arctic.fuse.3/settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="flag" type="bool">true</setting></settings>')
   with self.assertRaises(RuntimeError):nav.sync_skin_preferences(Path(t),lambda method,params:{'result':{'value':False}},lambda command:None)
 def test_new_skin_settings_use_builtin_and_dynamic_readback_not_stale_json_index(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'addon_data/skin.arctic.fuse.3/settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="label" type="string">a,b (test)</setting><setting id="flag" type="bool">false</setting></settings>')
   values={'label':'a,b (test)','flag':False,'script-skinviewtypes-hash':'','Shortcuts.RebuildDateTime':nav.REVISION};commands=[]
   result=nav.sync_skin_preferences(Path(t),lambda *a:{'error':{}},commands.append,lambda id,is_bool:values[id])
   self.assertEqual(result,2);self.assertIn('Skin.SetString("label","a,b (test)")',commands);self.assertIn('Skin.SetBool("flag",false)',commands);self.assertIn('Skin.Reset("script-skinviewtypes-hash")',commands)
if __name__=='__main__':unittest.main()
