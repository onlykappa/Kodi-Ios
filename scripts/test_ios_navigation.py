import importlib.util,json,shutil,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ios_navigation_test',ROOT/'migration/bundled-bootstrap/resources/lib/navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
HOME=b'<window><onload>OriginalAction()</onload><controls><include>missing-generated-menu</include><control type="list" id="501"><content>videodb://movies/titles/</content></control></controls></window>'
class NavigationTests(unittest.TestCase):
 def test_empty_widget_does_not_gate_settings_or_recovery(self):
  root=ET.fromstring(nav.patch_window(HOME,'Home.xml'));group=root.find("controls/control[@id='98100']")
  self.assertEqual(group.findtext('visible'),'System.Platform.IOS');self.assertEqual(len(group.findall('control')),6)
  for id,action in [('98104','ActivateWindow(settings)'),('98106',nav.MENU)]:
   button=group.find("control[@id='"+id+"']");self.assertEqual(button.findtext('onclick'),action);self.assertIsNone(button.find('visible'));self.assertIsNone(button.find('enable'))
 def test_no_helper_or_generated_include_required_for_bar(self):
  root=ET.fromstring(nav.patch_window(HOME,'Home.xml'));group=root.find("controls/control[@id='98100']");self.assertEqual(group.findall('.//include'),[]);self.assertNotIn('Container(',ET.tostring(group).decode())
 def test_default_focus_and_submenu_independent_of_widget_results(self):
  root=ET.fromstring(nav.patch_window(HOME,'Home.xml'));self.assertEqual(root.findtext('defaultcontrol'),'98104');actions=[x.text for x in root.findall('onload')];self.assertIn('OriginalAction()',actions);self.assertIn('Skin.Reset(Hub.Home.DisableSubmenu)',actions);self.assertEqual(actions[-1],'SetFocus(98104)')
 def test_bar_rectangles_and_focus_links(self):
  g=nav.bar();self.assertEqual(g.findtext('width'),'90%');self.assertGreaterEqual(int(g.findtext('height')),128);ids={x.get('id') for x in g.findall('control')}
  for b in g.findall('control'):
   self.assertIn(b.findtext('onleft'),ids);self.assertIn(b.findtext('onright'),ids);self.assertGreaterEqual(int(b.findtext('height')),128);self.assertEqual(b.findtext('font'),'font_main')
 def test_longpress_pan_settings_and_navigation_gestures(self):
  r=ET.fromstring(nav.TOUCH);self.assertEqual(r.findtext('global/touch/longpress'),'RightClick');self.assertEqual(r.findtext('global/touch/pan'),'PanGesture');self.assertEqual(r.findtext("global/touch/tap[@pointers='3']"),'ActivateWindow(settings)');self.assertEqual(r.findtext("global/touch/swipe[@direction='right']"),nav.MENU)
 def test_preserves_dialogs_and_playback(self):
  for data,name in [(b'<window type="dialog"><controls/></window>','DialogSelect.xml'),(b'<window><controls/></window>','VideoFullScreen.xml'),(b'<window><controls/></window>','DialogKeyboard.xml'),(b'<window><controls/></window>','Pointer.xml'),(b'<window><controls/></window>','VideoOSD.xml')]:self.assertEqual(nav.patch_window(data,name),data)
 def test_patch_is_byte_idempotent(self):
  once=nav.patch_window(HOME,'Home.xml');self.assertEqual(nav.patch_window(once,'Home.xml'),once)
 def test_id_conflict_fails_instead_of_overwriting_owner_control(self):
  with self.assertRaises(ValueError):nav.patch_window(b'<window><controls><control id="98100" type="button"/></controls></window>','Home.xml')
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
if __name__=='__main__':unittest.main()
