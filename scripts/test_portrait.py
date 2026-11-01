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
 def test_old_writable_copy_gets_the_portrait_layout(self):
  # A phone that ran an earlier build keeps a Fuse copy without the portrait folder or resolution.
  import shutil;shutil.rmtree(self.skin/'portrait');(self.skin/'addon.xml').write_text(ADDON)
  self.assertTrue(portrait.missing(self.skin))
  portrait.build(self.skin,self.profile)
  self.assertFalse(portrait.missing(self.skin));self.assertTrue((self.skin/'portrait/Home.xml').is_file())
 def test_textures_are_png(self):
  for name,data in portrait.textures().items():self.assertTrue(data.startswith(b'\x89PNG'),name)

 def test_tab_bar_order_and_no_drive(self):
  self.assertEqual([t[1] for t in portrait.TABS],['Home','Movies','TV','Library','Search'])
  home=(self.skin/'portrait/Home.xml').read_text();self.assertNotIn('googledrive',home.split('tab bar')[1])
 def test_continue_watching_leads_each_hub(self):
  for name,kind in (('Home.xml','all'),('Custom_1101_Hub.xml','episode'),('Custom_1102_Hub.xml','movie')):
   root=self.read('portrait/'+name);first=root.find(".//control[@id='5001']")
   self.assertEqual(first.findtext('content'),portrait.CONTINUE+kind)
 def test_old_in_progress_rows_are_replaced(self):
  self.assertTrue(portrait.in_progress({'label':'In Progress Movies','path':'special://profile/playlists/video/In Progress Movies.xsp'}))
  self.assertFalse(portrait.in_progress({'label':'Popular','path':'plugin://x/?info=popular'}))
 def test_library_and_search_pages(self):
  lib=(self.skin/'portrait/Custom_1103_Hub.xml').read_text()
  self.assertIn('videodb://movies/titles/',lib);self.assertIn('videodb://tvshows/titles/',lib)
  search=self.read('portrait/Custom_1105_Search.xml')
  self.assertIsNone(search.find('onload[.="RunScript(script.skinvariables)"]'))
  self.assertEqual(len(search.findall(".//control[@id='5100']/content/item")),len(portrait.CATEGORIES))
  self.assertIn('ActivateWindow(Videos,plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&with_id=True&with_genres=18&sort_by=popularity.desc,return)',[o.text for o in search.iter('onclick')])
 def test_context_menu_has_kodi_ids_and_fixed_layout(self):
  root=self.read('portrait/DialogContextMenu.xml');ids={c.get('id') for c in root.iter('control')}
  self.assertTrue({'996','999','1000'}<=ids)
  bg=root.find(".//control[@id='999']");self.assertEqual(bg.findtext('height'),str(portrait.HEIGHT))
  self.assertIn('Portrait_Ctx_Icon_0',(self.skin/'portrait/Includes.xml').read_text())
 def test_movie_and_show_folders_use_the_grid(self):
  self.assertIn('<views>50,51,52,53</views>',(self.skin/'portrait/MyVideoNav.xml').read_text())

class ServiceTests(unittest.TestCase):
 def test_focused_item_published_only_on_home_and_hubs(self):
  labels={'Container.ListItem.Label':'Show','Container.ListItem.Art(landscape)':'art.jpg','Container.ListItem.Property(subtitle)':'S1, E2'}
  state={'hub':True};seen={}
  tick=portrait.focused_item_publisher(lambda k:labels.get(k,''),lambda c:state['hub'] if 'Window' in c else False,seen.__setitem__)
  tick();self.assertEqual(seen,{'Title':'Show','Art':'art.jpg','Sub':'S1, E2'})
  seen.clear();state['hub']=False;labels['Container.ListItem.Label']='Other';tick();self.assertEqual(seen,{})
 def test_progress_saved_and_stop_reported(self):
  calls=[];clock=iter(range(0,1000,11))
  class Player:
   playing=True
   def isPlayingVideo(self):return self.playing
   def getTime(self):return 600
   def getTotalTime(self):return 1200
  class Store:
   def update(self,read,write,position,total):calls.append(('update',position,total))
   def stopped(self,read,write):calls.append(('stopped',))
  player=Player();tick=portrait.progress_tracker(player,Store(),None,None,lambda:next(clock))
  tick();player.playing=False;tick()
  self.assertEqual(calls,[('update',600,1200),('update',600,1200),('stopped',)])

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
 def test_no_reload_while_video_plays(self):
  # Playback turns the picture to landscape; the skin must not reload under the video.
  L,P=(2622,1206),(1206,2622);sizes={'wh':P};calls=[];ticks=iter(range(8))
  def info(label):return str(sizes['wh'][0] if label=='System.ScreenWidth' else sizes['wh'][1])
  def wait(t):
   sizes['wh']=L;return next(ticks,None) is None
  portrait.watch(info,calls.append,wait,lambda:'skin.arctic.fuse.3',busy=lambda:True)
  self.assertEqual(calls,[])

class IpaTests(unittest.TestCase):
 def test_info_plist_launches_portrait_and_keeps_landscape_for_video(self):
  with tempfile.TemporaryDirectory() as tmp:
   app=Path(tmp);(app/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'Kodi','UISupportedInterfaceOrientations':['UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}))
   ios_portrait.allow_portrait(app);ios_portrait.allow_portrait(app)
   info=plistlib.loads((app/'Info.plist').read_bytes())
   self.assertEqual(info['UISupportedInterfaceOrientations'],
    ['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight'])
   self.assertEqual(info['UIInterfaceOrientation'],'UIInterfaceOrientationPortrait')
 def test_native_patch_targets_pinned_files(self):
  patch=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()
  for name in ['XBMCController.mm','WinSystemIOS.h','IOSEAGLView.mm','GUIControlGroupList.cpp','Info.plist.in']:self.assertIn(name,patch)
  # Menus portrait only; landscape only while video plays (and turned to on play, back on stop).
  self.assertIn('return UIInterfaceOrientationMaskPortrait;',patch);self.assertIn('PlayingVideo())\n+    return UIInterfaceOrientationMaskLandscape;',patch)
  self.assertEqual(patch.count('[g_xbmcController updateVideoOrientationLock];'),2)
  self.assertIn('+\t<string>UIInterfaceOrientationPortrait</string>',patch)
  self.assertIn('return UIInterfaceOrientationMaskPortrait;',patch);self.assertIn('ResetInternalScreenSize',patch)
  # Upstream drew a taller-than-wide framebuffer as a sideways landscape viewport.
  self.assertIn('-    if(framebufferHeight > framebufferWidth) {',patch)
  lock=json.loads((ROOT/'migration/ios-portrait/source-lock.json').read_text())
  self.assertEqual(lock['commit'],'a3a448d26b8d560a65655dab2cd122994dc4e146')
 def test_swap_executable_checks_libraries(self):
  loads={b'official':['/usr/lib/libz.1.dylib','@rpath/KodiAirPlay.framework/KodiAirPlay'],
         b'system':['/usr/lib/libz.1.dylib','/System/Library/Frameworks/Metal.framework/Metal'],
         b'shipped':['@rpath/KodiGlassBar.framework/KodiGlassBar','@executable_path/Frameworks/libshairplay.0.dylib'],b'missing':['@rpath/Nope.framework/Nope']}
  real=ios_portrait.macho
  ios_portrait.macho=lambda data:{'dylib_loads':[{'name':n,'weak':False} for n in loads[data]]}
  try:
   for build,ok in [(b'system',True),(b'shipped',True),(b'missing',False)]:
    with tempfile.TemporaryDirectory() as tmp:
     app=Path(tmp)/'Kodi.app';(app/'Frameworks/KodiGlassBar.framework').mkdir(parents=True)
     (app/'Frameworks/KodiGlassBar.framework/KodiGlassBar').write_bytes(b'x');(app/'Frameworks/libshairplay.0.dylib').write_bytes(b'x')
     (app/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'Kodi'}));(app/'Kodi').write_bytes(b'official')
     exe=Path(tmp)/'new';exe.write_bytes(build)
     if ok:
      info=ios_portrait.swap_executable(app,exe);self.assertEqual((app/'Kodi').read_bytes(),build)
      self.assertIn('/usr/lib/libz.1.dylib' if build==b'shipped' else '@rpath/KodiAirPlay.framework/KodiAirPlay',info['dylibs_dropped'])
     else:
      with self.assertRaises(AssertionError):ios_portrait.swap_executable(app,exe)
      self.assertEqual((app/'Kodi').read_bytes(),b'official')
  finally:ios_portrait.macho=real
if __name__=='__main__':unittest.main()
