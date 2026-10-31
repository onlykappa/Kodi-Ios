import importlib.util,json,plistlib,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
sys.path.insert(0,str(ROOT/'scripts'))
import ios_portrait

ADDON='''<addon id="skin.arctic.fuse.3" version="3.4.8"><extension point="xbmc.gui.skin">
        <res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" />
</extension></addon>'''
FONT='<fonts><fontset id="Default"><include>Font_Default</include></fontset></fonts>'
HOME='<window><onload>RunScript(script.skinvariables)</onload><controls><control type="group" id="98400"><description>frame</description></control></controls></window>'
HUB='<window type="window" id="1101"><controls /></window>'
DIALOG='<window><controls><control type="label" id="1" /><control type="group" id="98400" /></controls></window>'
SETTINGS='<window><controls><control type="list" id="3" /><control type="image" id="98400" /></controls></window>'

class PortraitTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();base=Path(self.tmp.name)
  self.skin=base/'skin.arctic.fuse.3';(self.skin/'1080i').mkdir(parents=True)
  (self.skin/'addon.xml').write_text(ADDON)
  for name,data in {'Font.xml':FONT,'Home.xml':HOME,'Custom_1101_Hub.xml':HUB,'DialogConfirm.xml':DIALOG,'Settings.xml':SETTINGS,'Includes.xml':'<includes />'}.items():
   (self.skin/'1080i'/name).write_text(data)
  self.profile=base/'profile';nodes=self.profile/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3'
  nodes.mkdir(parents=True)
  (nodes/'skinvariables-shortcut-homewidgets.json').write_text(json.dumps([
   {'label':'Popular','path':'plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie','target':'videos'},
   {'label':'Sports','path':'RunScript(script.loop.sportshub)','target':''},
   {'label':'Umbrella','path':'plugin://plugin.video.umbrella','target':'videos'},
   {'label':'Library','path':'videodb://movies/titles/','target':'videos'}]))
  self.files=portrait.build(self.skin,self.profile)
 def tearDown(self):self.tmp.cleanup()
 def read(self,rel):return ET.parse(self.skin/rel).getroot()

 def test_every_xml_parses(self):
  for rel in self.files:
   if rel.endswith('.xml'):ET.parse(self.skin/rel)
 def test_resolutions_added_once_and_landscape_default_kept(self):
  data=(self.skin/'addon.xml').read_text()
  self.assertEqual(data.count('folder="portrait"'),2);self.assertIn('default="true" folder="1080i"',data)
  self.assertFalse(portrait.add_resolutions(self.skin/'addon.xml'))
 def test_square_pixels_in_iphone_safe_area(self):
  # 402 x (874-62-34) pt
  self.assertAlmostEqual(portrait.WIDTH/portrait.HEIGHT,402/778,places=3)
 def test_rows_only_for_lists_of_titles(self):
  home=(self.skin/'portrait/Home.xml').read_text()
  self.assertIn('info=popular',home);self.assertIn('videodb://movies/titles/',home)
  self.assertNotIn('sportshub',home);self.assertNotIn('plugin://plugin.video.umbrella<',home)
 def test_hub_keeps_fuse_onloads_window_id_and_has_tab_bar(self):
  home=self.read('portrait/Home.xml');self.assertEqual(home.findtext('onload'),'RunScript(script.skinvariables)')
  hub=self.read('portrait/Custom_1101_Hub.xml');self.assertEqual(hub.get('id'),'1101')
  ids={c.get('id') for c in hub.iter('control')}
  self.assertTrue({'4000','4001','4002','5000','9200','9201','9206'}<=ids)
 def test_select_dialog_has_kodi_control_ids(self):
  ids={c.get('id') for c in self.read('portrait/DialogSelect.xml').iter('control')}
  self.assertTrue({'1','2','3','5','6','7','8'}<=ids)
 def test_video_info_has_play_button(self):
  ids={c.get('id') for c in self.read('portrait/DialogVideoInfo.xml').iter('control')}
  self.assertIn('8',ids);self.assertIn('4',ids)
 def test_landscape_windows_are_shrunk_without_the_safe_area_frame(self):
  root=self.read('portrait/Settings.xml');ids=[c.get('id') for c in root.iter('control')]
  self.assertNotIn('98400',ids);self.assertIn('3',ids)
  zoom=root.find('controls/control/animation')
  self.assertEqual(zoom.get('effect'),'zoom');self.assertEqual(zoom.get('start'),'0,0,1920,1080')
  # Full windows get a background; dialogs stay transparent over the window below.
  self.assertEqual(root.find('controls/control').get('type'),'image')
  self.assertEqual(self.read('portrait/DialogConfirm.xml').find('controls/control').get('type'),'group')
 def test_landscape_header_overlay_is_empty_in_portrait(self):
  self.assertEqual(len(list(self.read('portrait/Custom_1182_Dialog_Topmenu_Overlay.xml').iter('control'))),0)
 def test_includes_chain_to_fuse_and_define_variables(self):
  root=self.read('portrait/Includes.xml')
  self.assertEqual(root.find('include').get('file'),'../1080i/Includes.xml')
  self.assertTrue({'Portrait_Hero_Art','Portrait_Show_Art','Portrait_Select_Art'}<={v.get('name') for v in root.iter('variable')})
 def test_fonts_added_to_every_fontset(self):
  names={f.findtext('name') for f in self.read('portrait/Font.xml').iter('font')}
  self.assertIn('p_title',names)
 def test_refresh_is_idempotent_and_follows_widget_changes(self):
  self.assertEqual(portrait.refresh(self.skin,self.profile),[])
  nodes=self.profile/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-homewidgets.json'
  nodes.write_text(json.dumps([{'label':'New row','path':'plugin://x/?a=1','target':'videos'}]))
  self.assertEqual(portrait.refresh(self.skin,self.profile),['portrait/Home.xml'])
 def test_textures_are_png(self):
  for name,data in portrait.textures().items():self.assertTrue(data.startswith(b'\x89PNG'),name)

class WatchTests(unittest.TestCase):
 def run_watch(self,sizes,skin='skin.arctic.fuse.3'):
  sizes=iter(sizes);current={};calls=[]
  def info(label):
   if label=='System.ScreenHeight':current['wh']=next(sizes,None)
   wh=current['wh']
   if wh is None:raise StopIteration
   return str(wh[0] if label=='System.ScreenWidth' else wh[1])
  try:portrait.watch(info,calls.append,lambda t:False,lambda:skin,settle=2)
  except StopIteration:pass
  return calls
 def test_reload_once_after_rotation_settles(self):
  L,P=(2622,1206),(1206,2622)
  self.assertEqual(self.run_watch([L,L,P,P,P,P]),['ReloadSkin()'])
 def test_brief_flip_is_ignored(self):
  L,P=(2622,1206),(1206,2622)
  self.assertEqual(self.run_watch([L,P,L,L]),[])
 def test_other_skin_never_reloaded(self):
  L,P=(2622,1206),(1206,2622)
  self.assertEqual(self.run_watch([L,P,P,P],skin='skin.estuary'),[])

class IpaTests(unittest.TestCase):
 def test_info_plist_allows_portrait_once(self):
  with tempfile.TemporaryDirectory() as tmp:
   app=Path(tmp);(app/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'Kodi','UISupportedInterfaceOrientations':['UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}))
   ios_portrait.allow_portrait(app);ios_portrait.allow_portrait(app)
   self.assertEqual(plistlib.loads((app/'Info.plist').read_bytes())['UISupportedInterfaceOrientations'],
    ['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight'])
 def test_native_patch_targets_pinned_files(self):
  patch=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()
  for name in ['XBMCController.mm','WinSystemIOS.h','AnnounceReceiver.mm','GUIControlGroupList.cpp','Info.plist.in']:self.assertIn(name,patch)
  self.assertIn('UIInterfaceOrientationMaskAllButUpsideDown',patch);self.assertIn('ResetInternalScreenSize',patch)
  lock=json.loads((ROOT/'migration/ios-portrait/source-lock.json').read_text())
  self.assertEqual(lock['commit'],'a3a448d26b8d560a65655dab2cd122994dc4e146')
if __name__=='__main__':unittest.main()
