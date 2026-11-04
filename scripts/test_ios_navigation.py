import importlib.util,json,shutil,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ios_navigation_test',ROOT/'migration/bundled-bootstrap/resources/lib/navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
HOME=b'<window><onload>OriginalAction()</onload><controls><include>missing-generated-menu</include><control type="list" id="501"><content>videodb://movies/titles/</content></control></controls></window>'
class NavigationTests(unittest.TestCase):
 def test_warm_upgrade_skips_parsing_and_rechecks_modified_or_new_inputs(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);skin=base/'addons/skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True)
   home=skin/'1080i/Home.xml';home.write_bytes(HOME);profile=base/'userdata'
   nav.upgrade(base,profile)
   with patch.object(nav,'patch_skin',side_effect=AssertionError('warm startup reparsed every window')):
    self.assertEqual(nav.upgrade(base,profile)['changed_files'],0)
   home.write_bytes(HOME)
   self.assertEqual(nav.upgrade(base,profile)['changed_files'],1)
   parts=skin/nav.TEMPLATES;parts.mkdir(parents=True)
   (parts/'widgets_standard_include.xmltemplate').write_bytes(b'<include name="{includes_name}-onunload">\n    {combined_widget_unload}\n</include>')
   self.assertEqual(nav.upgrade(base,profile)['changed_files'],1)
   keymap=profile/'keymaps/zz-kodi-ios-navigation.xml';keymap.write_text('<keymap/>')
   self.assertTrue(nav.upgrade(base,profile)['keymap_changed'])
   (profile/'addon_data/service.kodi.ios.bootstrap/navigation-upgrade.json').write_text('{invalid')
   with patch.object(nav,'patch_skin',wraps=nav.patch_skin) as scan:
    nav.upgrade(base,profile);self.assertEqual(scan.call_count,1)
 def test_warm_upgrade_does_not_bypass_symlink_protection(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);skin=base/'addons/skin.arctic.fuse.3/1080i';skin.mkdir(parents=True)
   (skin/'Home.xml').write_bytes(HOME);profile=base/'userdata';nav.upgrade(base,profile)
   target=base/'private.xml';target.write_text('<includes/>');(skin/'external.xml').symlink_to(target)
   with self.assertRaises(ValueError):nav.upgrade(base,profile)
 def test_empty_generated_unload_is_registered_but_real_actions_are_preserved(self):
  for empty in (b'<include name="skinvariables-homewidgets-standard-onunload" />',
                b'<include name="skinvariables-1101widgets-standard-onunload">\n </include>'):
   fixed=nav.empty_widget_unloads(empty);root=ET.fromstring(fixed)
   # Kodi 21's LoadIncludes requires FirstChild(): a definition child registers even an empty include.
   self.assertIsNotNone(root.find('definition'));self.assertEqual(nav.empty_widget_unloads(fixed),fixed)
  real=b'<include name="skinvariables-homewidgets-standard-onunload"><onunload>ClearProperty(WidgetCombined.1.Path,Home)</onunload></include>'
  self.assertEqual(nav.empty_widget_unloads(real),real)
  unrelated=b'<include name="owner-empty" />';self.assertEqual(nav.empty_widget_unloads(unrelated),unrelated)
 def test_widget_generator_emits_valid_empty_and_nonempty_unloads(self):
  template=b'<include name="{includes_name}-onunload">\n    {combined_widget_unload}\n</include>'
  fixed=nav.empty_widget_unloads(template);self.assertEqual(nav.empty_widget_unloads(fixed),fixed)
  for actions in (b'',b'<onunload>ClearProperty(WidgetCombined.1.Path,Home)</onunload>'):
   root=ET.fromstring(fixed.replace(b'{includes_name}',b'skinvariables-homewidgets-standard').replace(b'{combined_widget_unload}',actions))
   definition=root.find('definition');self.assertIsNotNone(definition)
   self.assertEqual(len(definition),int(bool(actions)))
 def test_existing_generated_files_and_future_templates_are_repaired_together(self):
  with tempfile.TemporaryDirectory() as t:
   skin=Path(t);(skin/'1080i').mkdir();parts=skin/nav.TEMPLATES;parts.mkdir(parents=True)
   generated=skin/'1080i/script-skinvariables-generator-includes-.xml'
   generated.write_bytes(b'<includes><include name="skinvariables-homewidgets-standard-onunload" /></includes>')
   template=parts/'widgets_standard_include.xmltemplate'
   template.write_bytes(b'<include name="{includes_name}-onunload">\n    {combined_widget_unload}\n</include>')
   self.assertEqual(len(nav.patch_skin(skin)),2);self.assertEqual(nav.patch_skin(skin),[])
   self.assertIsNotNone(ET.parse(generated).find('include/definition'));self.assertIn(b'<definition>',template.read_bytes())
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
 def test_non_hub_windows_get_visible_back_and_home(self):
  once=nav.patch_window(b'<window><controls/></window>','MyVideoNav.xml');self.assertEqual(nav.patch_window(once,'MyVideoNav.xml'),once)
  group=ET.fromstring(once).find("controls/control[@id='98300']");self.assertEqual(group.findtext('visible'),'System.Platform.IOS')
  self.assertEqual([b.findtext('onclick') for b in group.findall('control')],['Action(Back)','ActivateWindow(Home)'])
  for b in group.findall('control'):self.assertGreaterEqual(int(b.findtext('height')),88)
  self.assertIsNone(group.find('left'));self.assertEqual(group.findtext('right'),'60')
  for name in ['DialogSelect.xml','VideoOSD.xml']:self.assertEqual(nav.patch_window(b'<window><controls/></window>',name),b'<window><controls/></window>')
 def test_submenu_and_bumper_dialogs_never_open_on_ios(self):
  data=b'<a><onup condition="String.IsEmpty(Skin.String(X))">ActivateWindow(1181)</onup><oninfo>ActivateWindow(1181)</oninfo><ondown>ActivateWindow(1180)</ondown><onup>ActivateWindow(1170)</onup></a>'
  once=nav.patch_includes(data);self.assertEqual(nav.patch_includes(once),once)
  self.assertEqual([x.get('condition') for x in ET.fromstring(once)],['[String.IsEmpty(Skin.String(X))] + !System.Platform.IOS','!System.Platform.IOS','!System.Platform.IOS',None])
 def test_vertical_swipes_move_between_rows(self):
  r=ET.fromstring(nav.TOUCH)
  for window in ['window11106','window11109','movieinformation']:self.assertEqual(r.findtext(window+"/touch/swipe[@direction='up']"),'Down');self.assertEqual(r.findtext(window+"/touch/swipe[@direction='down']"),'Up')
 def test_portrait_pages_scroll_with_the_finger_not_row_by_row(self):
  # Home (Home/Movies/TV hubs), Library and Search: a row swipe on top of the drag made the page jump mid-flick.
  r=ET.fromstring(nav.TOUCH)
  for window in ['home','window11101','window11102','window11103','window11104','window11105']:self.assertIsNone(r.find(window))
 def test_ordinary_lists_keep_native_drag_scrolling(self):
  r=ET.fromstring(nav.TOUCH);self.assertFalse([x for x in r.findall('global/touch/swipe') if x.get('direction') in ('up','down') and not x.get('pointers')]);self.assertEqual(r.findtext('global/touch/pan'),'PanGesture')
 def test_black_frame_covers_safe_areas_and_stays_on_top(self):
  once=nav.patch_frame(b'<window type="dialog"><controls><control type="image"/></controls></window>','DialogSelect.xml');self.assertEqual(nav.patch_frame(once,'DialogSelect.xml'),once)
  last=list(ET.fromstring(once).find('controls'))[-1];self.assertEqual(last.get('id'),'98400');self.assertEqual(last.findtext('visible'),'System.Platform.IOS')
  # Kodi widens the canvas on wide phones, so each piece is anchored outside an edge, never at a fixed 1920.
  for image in last.findall('control'):
   edges={k:int(image.findtext(k)) for k in ['left','right','top','bottom','width','height'] if image.find(k) is not None}
   self.assertTrue(edges.get('left')==-edges.get('width',0)==-1000 or edges.get('right')==-edges.get('width',0)==-1000 or edges.get('top')==-edges.get('height',0)==-1000 or edges.get('bottom')==-edges.get('height',0)==-1000,edges)
   self.assertNotIn(1920,edges.values())
  moved=ET.fromstring(once);moved.find('controls').append(ET.Element('control'));again=nav.patch_frame(ET.tostring(moved),'DialogSelect.xml')
  self.assertEqual(list(ET.fromstring(again).find('controls'))[-1].get('id'),'98400')
  self.assertEqual(nav.patch_frame(b'<window><controls/></window>','Pointer.xml'),b'<window><controls/></window>')
 def test_generated_rows_and_zoom_are_patched(self):
  with tempfile.TemporaryDirectory() as t:
   skin=Path(t);(skin/'1080i').mkdir();parts=skin/nav.TEMPLATES;parts.mkdir(parents=True)
   (parts/'widgets_row.xmltemplate').write_bytes(b'<control>{x}<onfocus>ClearProperty(HomeSwitcher.IsVisible,Home)</onfocus></control>')
   (skin/'1080i/Includes_Background.xml').write_bytes(b'<includes>'+nav.ZOOM[0]+b' /></animation></includes>')
   self.assertEqual(len(nav.patch_skin(skin)),2);self.assertEqual(nav.patch_skin(skin),[])
   self.assertIn(b'condition="!System.Platform.IOS">ClearProperty',(parts/'widgets_row.xmltemplate').read_bytes());self.assertIn(nav.ZOOM[1],(skin/'1080i/Includes_Background.xml').read_bytes())
 def test_header_stays_visible_on_ios_only(self):
  data=b'<a><onfocus>ClearProperty(HomeSwitcher.IsVisible,Home)</onfocus><onfocus condition="![$PARAM[x]]">ClearProperty(HomeSwitcher.IsVisible,Home)</onfocus></a>'
  once=nav.patch_includes(data);self.assertEqual(nav.patch_includes(once),once)
  self.assertEqual([x.get('condition') for x in ET.fromstring(once)],['!System.Platform.IOS','[![$PARAM[x]]] + !System.Platform.IOS'])
 def test_gear_menu_gets_drive_and_recovery_and_widgets_put_phone_rows_first(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);nodes=p/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3';nodes.mkdir(parents=True)
   (nodes/'skinvariables-shortcut-powermenu.json').write_text(json.dumps([{'label':'$LOCALIZE[1036]','path':'ActivateWindow(1160)'},{'label':'$LOCALIZE[13009]','path':'ActivateWindow(Settings)'}]))
   (nodes/'skinvariables-shortcut-homewidgets.json').write_text(json.dumps([{'label':'In Progress','path':'special://profile/playlists/video/x.xsp'},{'label':'Trakt','path':'plugin://plugin.video.themoviedb.helper/?info=trakt_becauseyouwatched'},{'label':'Popular','path':'plugin://plugin.video.themoviedb.helper/?info=discover'},{'label':'Local','path':'videodb://movies/titles/'}]))
   self.assertEqual(len(nav.update_nodes(p)),2);self.assertEqual(nav.update_nodes(p),[])
   power=json.loads((nodes/'skinvariables-shortcut-powermenu.json').read_text())
   self.assertEqual([x['path'] for x in power],['ActivateWindow(1160)',nav.DRIVE,nav.UPDATES,nav.MENU,'ActivateWindow(Settings)']);self.assertEqual(power[-1]['label'],'$LOCALIZE[5]')
   self.assertEqual([x['label'] for x in json.loads((nodes/'skinvariables-shortcut-homewidgets.json').read_text())],['Popular','Trakt','In Progress','Local'])
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
class PlayOnTVButton(unittest.TestCase):
 def test_video_controls_get_a_top_right_play_on_tv_button_once(self):
  osd=b'<window><controls><control type="group" id="1"/></controls></window>'
  once=nav.patch_osd(osd,'VideoOSD.xml');group=ET.fromstring(once).find("controls/control[@id='98500']")
  self.assertEqual(group.findtext('right'),'48');self.assertEqual(group.findtext('description'),nav.CAST_MARKER)
  self.assertEqual(group.find("control[@type='button']").findtext('onclick'),nav.CAST_SCRIPT)
  self.assertEqual(nav.patch_osd(once,'VideoOSD.xml'),once);self.assertEqual(nav.patch_osd(osd,'Home.xml'),osd)
  with self.assertRaises(ValueError):nav.patch_osd(b'<window><controls><control type="group" id="98500"/></controls></window>','VideoOSD.xml')
if __name__=='__main__':unittest.main()
