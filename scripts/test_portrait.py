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
  for name,data in {'Font.xml':FONT,'Home.xml':HOME,'Custom_1101_Hub.xml':HUB,'DialogConfirm.xml':DIALOG,'Settings.xml':SETTINGS,'SettingsSystemInfo.xml':SETTINGS,'Includes.xml':'<includes />'}.items():
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
  # Movies and TV forward to their group in Home, so they keep their rows loaded between tab switches.
  self.assertEqual([o.text for o in hub.findall('onload')][-2:],['SetProperty(Portrait.Tab,tv,home)','ReplaceWindow(Home)'])
  ids=[c.get('id') for c in home.iter('control') if c.get('id')]
  self.assertEqual(len(ids),len(set(ids)),'control ids repeat across hubs')
  for offset in (0,10000,20000):
   self.assertTrue({str(n+offset) for n in (4000,4001,4002,5000,9200,9201,9206,9207)}<=set(ids))
 def test_hub_groups_switch_by_tab_property(self):
  home=self.read('portrait/Home.xml')
  for gid,tab in (('3900',''),('13900','movies'),('23900','tv')):
   group=home.find(".//control[@id='%s']"%gid);cond=group.findtext('visible')
   self.assertIn('Portrait.Tab',cond);self.assertTrue(cond.endswith(tab+')') if tab else cond.startswith('String.IsEmpty'))
   # each hub's rows and tab bar live inside its own group
   self.assertIsNotNone(group.find(".//control[@id='%d']"%(int(gid)+1101)))
  movies_tab=home.find(".//control[@id='19202']")
  self.assertEqual([o.text for o in movies_tab.findall('onclick')],['SetProperty(Portrait.Tab,movies,home)','ReplaceWindow(Home)','SetFocus(14000)'])
 def test_last_row_clears_the_tab_bar(self):
  home=self.read('portrait/Home.xml');page=home.find(".//control[@id='5000']")
  self.assertEqual(page.findtext('height'),str(portrait.HEIGHT))
  self.assertGreaterEqual(int(list(page)[-1].findtext('height')),300)
 def test_select_dialog_has_kodi_control_ids(self):
  ids={c.get('id') for c in self.read('portrait/DialogSelect.xml').iter('control')}
  self.assertTrue({'1','2','3','5','6','7','8'}<=ids)
 def test_video_info_has_play_button(self):
  ids={c.get('id') for c in self.read('portrait/DialogVideoInfo.xml').iter('control')}
  self.assertIn('8',ids);self.assertIn('4',ids)
 def test_landscape_windows_are_shrunk_without_the_safe_area_frame(self):
  root=self.read('portrait/SettingsSystemInfo.xml');ids=[c.get('id') for c in root.iter('control')]
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
 def test_a_start_changes_nothing_after_the_build(self):
  # Build 88: navigation framed the new video controls, the portrait refresh rewrote them, and each start
  # reloaded the skin four times. Navigation then portrait, as the bootstrap runs them, must settle at once.
  nav=importlib.util.spec_from_file_location('nav2',ROOT/'migration/bundled-bootstrap/resources/lib/navigation.py');n=importlib.util.module_from_spec(nav);nav.loader.exec_module(n)
  skin=Path(self.tmp.name)/'fresh'/'skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True);(skin/'addon.xml').write_text(ADDON)
  plain='<?xml version="1.0" encoding="UTF-8"?>\n<window>\n<controls>\n<control type="label" id="1"><label>x</label></control>\n</controls>\n</window>\n'
  for name in ('Home.xml','VideoOSD.xml','DialogSeekBar.xml','Settings.xml','Includes.xml','Font.xml'):
   (skin/'1080i'/name).write_text(FONT if name=='Font.xml' else '<includes />' if name=='Includes.xml' else plain)
  n.patch_skin(skin);portrait.build(skin,self.profile)
  for _ in range(2):self.assertEqual(n.patch_skin(skin),[]);self.assertEqual(portrait.refresh(skin,self.profile),[])
 def test_deck_page_for_portrait(self):
  page=self.read('portrait/DeckSourceSelect.xml');ids={c.get('id') for c in page.iter('control')}
  self.assertTrue({'32500','32501','32503'}<=ids)  # what deck_picker.py drives
  xml=(self.skin/'portrait/DeckSourceSelect.xml').read_text()
  for prop in ('deck.poster','deck.fanart','deck.title','deck.meta','deck.plot','deck.quality_label','deck.count_label','ListItem.Property(badge)'):self.assertIn(prop,xml)
 def test_player_controls_replace_fuse_osd(self):
  (self.skin/'1080i/DialogSeekBar.xml').write_text('<?xml version="1.0"?>\n<window>\n<controls/></window>')
  files=portrait.portrait_files(self.skin,self.profile)
  osd=ET.fromstring(files['1080i/VideoOSD.xml']);ids={c.get('id') for c in osd.iter('control')}
  # close, Play on TV, back 10 / play-pause / forward 10, speed / audio / subtitles, seek, Info, Continue Watching
  self.assertTrue({'7101','7102','7111','7112','7113','7121','7122','7123','7131','7141','7142','7201'}<=ids)
  clicks=[o.text for o in osd.iter('onclick')]
  for action in ['PlayerControl(Stop)','RunScript(service.kodi.ios.bootstrap,cast)','Seek(-10)','PlayerControl(Play)','Seek(10)',
                 'RunScript(service.kodi.ios.bootstrap,speed)','ActivateWindow(osdaudiosettings)','ActivateWindow(osdsubtitlesettings)','$VAR[Action_OSD_WikiInfo]']:self.assertIn(action,clicks)
  self.assertNotIn('volume',files['1080i/VideoOSD.xml'].decode().lower())
  self.assertIn('$NUMBER[10]',files['1080i/VideoOSD.xml'].decode())  # a bare 10 is a Kodi string id
  # r4: Fuse's seek bar is replaced by a window that never shows (the owner wants only the controls' bar); Kodi's
  # progress control 401 stays.
  seek=ET.fromstring(files['1080i/DialogSeekBar.xml']);self.assertEqual(seek.find('visible').text,'false')
  self.assertEqual([c.get('id') for c in seek.iter('control') if c.get('id')],['401'])
  # Pinned to the left/centre/right, never a fixed x beyond Fuse's 16:9 width (Kodi loads the seek bar upright).
  for root in (seek,osd):
   for c in root.iter('control'):
    x=c.find('left')
    if x is not None and x.text.isdigit():self.assertLess(int(x.text)+int((c.find('width').text if c.find('width') is not None and c.find('width').text.isdigit() else 0)),1920,ET.tostring(c)[:200])
  self.assertTrue(files['extras/portrait/airplay.png'].startswith(b'\x89PNG'))
  nav=importlib.util.spec_from_file_location('nav',ROOT/'migration/bundled-bootstrap/resources/lib/navigation.py');n=importlib.util.module_from_spec(nav);nav.loader.exec_module(n)
  self.assertEqual(n.patch_osd(files['1080i/VideoOSD.xml'],'VideoOSD.xml'),files['1080i/VideoOSD.xml'])
 def test_buttons_run_pages_by_addon_id(self):
  # "Script invoked without an addon" (ISSUE-071): every RunScript of the setup add-on in the generated files names
  # the add-on and a page default.py knows, and that page exists.
  import re
  spec=importlib.util.spec_from_file_location('boot_default',ROOT/'migration/bundled-bootstrap/default.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
  text=''.join(v.decode('utf-8','replace') for k,v in portrait.portrait_files(self.skin,self.profile).items() if k.endswith('.xml'))
  pages=set(re.findall(r'RunScript\(service\.kodi\.ios\.bootstrap,([a-z_]+)',text));self.assertTrue({'notifications','cast','speed'}<=pages,pages)
  for page in pages:
   self.assertIn(page,d.PAGES);self.assertTrue((ROOT/'migration/bundled-bootstrap'/(page+'.py')).is_file(),page)
  self.assertNotIn('RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/',text)
  path,argv=d.target(['default.py','download','kind=season','season=2']);self.assertTrue(path.endswith('download.py'));self.assertEqual(argv[1:],['kind=season','season=2'])
  path,argv=d.target(['default.py']);self.assertTrue(path.endswith('recover.py'))
 def test_fuse_splash_never_shows(self):
  files=portrait.portrait_files(self.skin,self.profile);splash=ET.fromstring(files['portrait/Custom_1198_Dialog_Startup.xml'])
  self.assertEqual((splash.get('id'),splash.get('type'),splash.find('visible').text),('1198','dialog','false'))
 def test_start_skips_an_unchanged_refresh(self):
  first=portrait.refresh_if_needed(self.skin,self.profile)
  self.assertEqual(portrait.refresh_if_needed(self.skin,self.profile),[])
  calls=[];real=portrait.refresh
  try:
   portrait.refresh=lambda skin,profile:calls.append(1) or []
   self.assertEqual(portrait.refresh_if_needed(self.skin,self.profile),[]);self.assertEqual(calls,[])
   # Writing our own 1080i files is not a change; a Fuse file or the widget list is.
   (self.skin/'1080i/VideoOSD.xml').write_text('<window />');portrait.refresh_if_needed(self.skin,self.profile);self.assertEqual(calls,[])
   home=self.skin/'1080i/Home.xml';home.write_text(home.read_text()+' ');portrait.refresh_if_needed(self.skin,self.profile);self.assertEqual(calls,[1])
  finally:portrait.refresh=real
 def test_textures_are_png(self):
  for name,data in portrait.textures().items():self.assertTrue(data.startswith(b'\x89PNG'),name)

 def test_tab_bar_order_and_no_drive(self):
  self.assertEqual([t[1] for t in portrait.TABS],['Home','Movies','TV','Library','Search'])
  home=(self.skin/'portrait/Home.xml').read_text();self.assertNotIn('googledrive',home.split('tab bar')[1])
 def test_continue_watching_leads_each_hub(self):
  root=self.read('portrait/Home.xml')
  for offset,kind in ((0,'all'),(20000,'episode'),(10000,'movie')):
   first=root.find(".//control[@id='%d']"%(5001+offset))
   self.assertEqual(first.findtext('content'),portrait.CONTINUE+kind)
 def test_old_in_progress_rows_are_replaced(self):
  self.assertTrue(portrait.in_progress({'label':'In Progress Movies','path':'special://profile/playlists/video/In Progress Movies.xsp'}))
  self.assertFalse(portrait.in_progress({'label':'Popular','path':'plugin://x/?info=popular'}))
 def test_library_and_search_pages(self):
  lib=(self.skin/'portrait/Custom_1103_Hub.xml').read_text()
  self.assertIn('plugin://plugin.video.kodi.ios.watch/?action=library&amp;type=movie',lib);self.assertIn('plugin://plugin.video.kodi.ios.watch/?action=library&amp;type=tv',lib)  # Kodi's library + Google Drive downloads
  search=self.read('portrait/Custom_1105_Search.xml')
  self.assertIsNone(search.find('onload[.="RunScript(script.skinvariables)"]'))
  self.assertEqual(len(search.findall(".//control[@id='5100']/content/item")),len(portrait.CATEGORIES))
  self.assertIn('ActivateWindow(Videos,plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&with_id=True&with_genres=18&sort_by=popularity.desc,return)',[o.text for o in search.iter('onclick')])
 def test_context_menu_has_kodi_ids_and_fixed_layout(self):
  root=self.read('portrait/DialogContextMenu.xml');ids={c.get('id') for c in root.iter('control')}
  self.assertTrue({'996','1000'}<=ids)
  # No 999: Kodi would shrink it to the menu and move the dialog to the pressed item (off screen near the bottom).
  self.assertNotIn('999',ids);self.assertEqual(root.find('controls/control').findtext('height'),str(portrait.HEIGHT))
  # A long menu hides the card; icons hide once the menu would scroll (they are a fixed layer beside it).
  xml=(self.skin/'portrait/DialogContextMenu.xml').read_text();self.assertIn('Control.IsVisible(1010)',xml);self.assertIn('!Control.IsVisible(1016)',xml)
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
 def test_turning_the_phone_never_reloads_the_skin(self):
  # Every turn used to reload the skin, rebuilding Home and all its rows at each video start and stop.
  L,P=(2622,1206),(1206,2622);seq=iter([P,L,L,L,P,P,P,L,L]);calls=[];ticks=[]
  sizes={'wh':P}
  def info(label):return str(sizes['wh'][0] if label=='System.ScreenWidth' else sizes['wh'][1])
  def wait(t):
   nxt=next(seq,None)
   if nxt is None:return True
   sizes['wh']=nxt;return False
  portrait.watch(info,calls.append,wait,lambda:'skin.arctic.fuse.3',tick=lambda:ticks.append(1))
  self.assertEqual(calls,[]);self.assertEqual(len(ticks),9)
 def test_playback_windows_have_no_portrait_copy(self):
  with tempfile.TemporaryDirectory() as tmp:
   skin=Path(tmp);(skin/'portrait').mkdir();(skin/'portrait/DialogSeekBar.xml').write_text('<window />')
   changed=portrait.write(skin,{})
   self.assertEqual(changed,['portrait/DialogSeekBar.xml']);self.assertFalse((skin/'portrait/DialogSeekBar.xml').exists())

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
  for name in ['XBMCController.mm','WinSystemIOS.h','IOSEAGLView.mm','GUIControlGroupList.cpp','Info.plist.in','GUIWindow.cpp']:self.assertIn(name,patch)
  # Touch scrolling: flick speed in pixels like the positions (momentum), pan distance in skin units like the point.
  self.assertIn('velocity.x *= screenScale;',patch);self.assertIn('if (action.GetID() == ACTION_GESTURE_PAN)',patch)
  # A page (group list) takes momentum and the vertical drags that start on a row; the screen size heals itself.
  for text in ['GUIBaseContainer.cpp','ACTION_GESTURE_NOTIFY)\n+  { // Kodi-iOS','parent->GetControlType() == GUICONTROL_GROUPLIST','- (void)healScreenSize','auto frame = self.bounds;']:self.assertIn(text,patch)
  # Menus portrait only; landscape only while video plays (and turned to on play, back on stop).
  self.assertIn('return UIInterfaceOrientationMaskPortrait;',patch);self.assertIn('s_videoLandscape)\n+    return UIInterfaceOrientationMaskLandscape;',patch)
  # Video turns landscape once its stream is open (OnAVStart), back on stop, retried by a timer until it takes.
  for text in ['msg == "OnAVStart"','setVideoLandscape:NO','scheduledTimerWithTimeInterval:0.5','requestGeometryUpdateWithPreferences']:self.assertIn(text,patch)
  self.assertIn('+\t<string>UIInterfaceOrientationPortrait</string>',patch)
  self.assertIn('return UIInterfaceOrientationMaskPortrait;',patch);self.assertIn('ResetInternalScreenSize',patch)
  # Upstream drew a taller-than-wide framebuffer as a sideways landscape viewport.
  self.assertIn('-    if(framebufferHeight > framebufferWidth) {',patch)
  # r19: taps right of the portrait width reached no view in landscape (play/pause, CC, AirPlay): the window sends
  # unclaimed points to the GL view, and a tap that still reached no view is handed to Kodi from sendEvent:.
  for text in ['- (UIView*)hitTest:(CGPoint)point withEvent:(UIEvent*)event','return gl;','@implementation UIApplication (KodiTouchRescue)',
               'method_exchangeImplementations(original, rescue);','- (void)rescueTouches:(UIEvent*)event','"handed to Kodi"']:self.assertIn(text,patch)
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
