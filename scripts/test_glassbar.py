import importlib.util,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('glassbar',ROOT/'migration/bundled-bootstrap/resources/lib/glassbar.py')
glassbar=importlib.util.module_from_spec(spec);spec.loader.exec_module(glassbar)
sys.path.insert(0,str(ROOT/'scripts'))
import ios_portrait

class Lib:
 def __init__(self):self.calls=[];self.tap=-1
 def kodi_glassbar_show(self,v):self.calls.append(('show',v))
 def kodi_glassbar_select(self,i):self.calls.append(('select',i))
 def kodi_glassbar_take_tap(self):t,self.tap=self.tap,-1;return t

class ControllerTests(unittest.TestCase):
 def setUp(self):
  self.lib=Lib();self.active='home';self.dialog=False;self.portrait=True;self.props={};self.ran=[]
  def visible(cond):
   if cond=='System.HasActiveModalDialog':return self.dialog
   tab=self.active.split(':')[1] if ':' in self.active else ''
   window=self.active.split(':')[0]
   for part in cond.split(' | '):
    terms=part.split(' + ');ok=True
    for t in terms:
     if t.startswith('Window.IsActive('):ok&=t=='Window.IsActive(%s)'%window
     elif t.startswith('String.IsEmpty('):ok&=tab==''
     elif t.startswith('String.IsEqual('):ok&=t.endswith(','+tab+')') and tab!=''
     elif t.startswith('!Window.IsActive('):ok&=t!='!Window.IsActive(%s)'%window
    if ok:return True
   return False
  spec=importlib.util.spec_from_file_location('portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
  portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
  self.actions=[portrait.tab_actions(t[0]) for t in portrait.TABS]
  self.tick,self.poll,self.close=glassbar.controller(self.lib,visible,lambda:self.portrait,self.ran.append,self.actions)
 def test_shows_on_tab_pages_in_portrait_and_marks_the_page(self):
  self.active='home:tv';self.tick()
  self.assertEqual(self.lib.calls,[('select',2),('show',1)])
  # No window property: the skin's own bar depends on the framework being there, not on the native bar's state.
  self.assertEqual(self.props,{})
 def test_hidden_for_dialogs_landscape_and_other_windows(self):
  self.tick();self.dialog=True;self.tick()
  self.assertEqual(self.lib.calls[-1],('show',0));self.assertEqual(self.props,{})
  self.dialog=False;self.portrait=False;self.lib.calls.clear();self.tick();self.assertEqual(self.lib.calls,[])
  self.portrait=True;self.active='videos';self.tick();self.assertEqual(self.lib.calls,[])
 def test_library_covers_both_download_hubs(self):
  self.active='1104';self.tick();self.assertIn(('select',3),self.lib.calls)
 def test_tap_runs_that_tab_once_and_not_the_current_page(self):
  self.tick();self.lib.tap=4;self.poll();self.poll()
  self.assertEqual(self.ran,['ReplaceWindow(1105)'])
  self.lib.tap=0;self.poll();self.assertEqual(self.ran,['ReplaceWindow(1105)'])
spec_s=importlib.util.spec_from_file_location('searchbar',ROOT/'migration/bundled-bootstrap/resources/lib/searchbar.py')
searchbar=importlib.util.module_from_spec(spec_s);spec_s.loader.exec_module(searchbar)

class SearchLib:
 def __init__(self):self.calls=[]
 def kodi_search_show(self,v):self.calls.append(('show',v))

class SearchFieldTests(unittest.TestCase):
 def setUp(self):
  self.lib=SearchLib();self.page=True;self.dialog=False;self.portrait=True;self.props={};self.now=0.0;self.queue=[]
  visible=lambda c:self.dialog if c=='System.HasActiveModalDialog' else (self.page if c==searchbar.PAGE else False)
  take=lambda:self.queue.pop(0) if self.queue else (0,'')
  self.tick,self.poll,self.close=searchbar.controller(self.lib,take,visible,lambda:self.portrait,self.props.__setitem__,lambda:self.now)
 def test_field_shows_only_on_the_search_page_in_portrait_without_dialogs(self):
  self.tick();self.tick();self.assertEqual(self.lib.calls,[('show',1)])
  self.dialog=True;self.tick();self.dialog=False;self.tick();self.page=False;self.tick()
  self.assertEqual(self.lib.calls,[('show',1),('show',0),('show',1),('show',0)])
  self.close();self.assertEqual(self.lib.calls[-1],('show',0))
 def test_results_follow_typing_once_it_pauses(self):
  self.queue=[(1,'scary')];self.poll();self.assertEqual(self.props,{})
  self.now=0.2;self.queue=[(1,'scary movie')];self.poll();self.now=0.5;self.poll();self.assertEqual(self.props,{})
  self.now=0.7;self.poll()
  self.assertEqual(self.props,{'Portrait.Search.Query':'scary movie','Portrait.Search.Path':'plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=multi&query=scary%20movie'})
  self.now=2;self.poll();self.assertEqual(len(self.props),2)
 def test_search_key_lists_at_once_and_x_clears(self):
  self.queue=[(1|2,'alien & aliens')];self.poll()
  self.assertEqual(self.props['Portrait.Search.Path'],searchbar.SEARCH%'multi'+'alien%20%26%20aliens')
  self.queue=[(1|4,'')];self.poll();self.assertEqual(self.props,{'Portrait.Search.Query':'','Portrait.Search.Path':''})
 def test_filter_pills_switch_between_movies_and_shows(self):
  kind={'v':''}
  visible=lambda c:c==searchbar.PAGE
  tick,poll,_=searchbar.controller(self.lib,lambda:(1|2,'alien'),visible,lambda:True,self.props.__setitem__,lambda:0,info=lambda l:kind['v'])
  tick();poll();self.assertIn('tmdb_type=multi',self.props['Portrait.Search.Path'])
  kind['v']='movie';tick();self.assertIn('tmdb_type=movie&query=alien',self.props['Portrait.Search.Path'])
  kind['v']='tv';tick();self.assertIn('tmdb_type=tv',self.props['Portrait.Search.Path'])
 def test_search_page_layout(self):
  import xml.etree.ElementTree as ET
  spec=importlib.util.spec_from_file_location('portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
  portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
  root=ET.fromstring(portrait.search_window('<window id="1105"/>'))
  panels={c.get('id'):c for c in root.iter('control') if c.get('type')=='panel'}
  # Results grid: three posters a row, filled from the typed search, under the native band.
  results=panels['5200'];self.assertIn('Portrait.Search.Path',results.findtext('content'))
  self.assertGreater(int(results.findtext('top')),portrait.SEARCH_BAND)
  self.assertEqual(int(results.find('itemlayout').get('width'))*3,1080-2*int(results.findtext('left'))+24)
  # Categories while the field is empty; the old Kodi field only on a phone without the native one.
  self.assertIn('String.IsEmpty(Window(Home).Property(Portrait.Search.Path))',panels['5100'].findtext('visible'))
  button=[c for c in root.iter('control') if c.get('id')=='5101'][0]
  self.assertTrue(any(g.findtext('visible')=='!'+portrait.SEARCH_NATIVE for g in root.iter('control') if button in list(g.iter('control'))))
 def test_framework_source_has_the_search_field(self):
  src=(ROOT/'migration/glassbar-ios/build-glassbar.sh').read_text()
  for name in ('void kodi_search_show(int','void kodi_search_focus(int','void kodi_search_set(const char','int kodi_search_take(char *buffer, int size)'):
   self.assertIn('__attribute__((visibility("default"))) '+name,src)
  for text in ('UIReturnKeySearch','UITextFieldViewModeWhileEditing','systemImageNamed:@"xmark"','constraintEqualToAnchor:window.safeAreaLayoutGuide.topAnchor constant:60'):self.assertIn(text,src)

class IpaTests(unittest.TestCase):
 def locks(self,tmp,bar_sha,exe_sha=''):
  bar=Path(tmp)/'bar.json';exe=Path(tmp)/'exe.json'
  bar.write_text(json.dumps({'framework_release':{'tag':'t','asset':'KodiGlassBar.framework.zip','sha256':bar_sha}}))
  exe.write_text(json.dumps({'executable_release':{'tag':'e','asset':'x.zip','sha256':exe_sha}}))
  old=(ios_portrait.GLASSBAR,ios_portrait.EXECUTABLE);ios_portrait.GLASSBAR,ios_portrait.EXECUTABLE=bar,exe
  self.addCleanup(lambda:setattr(ios_portrait,'GLASSBAR',old[0]) or setattr(ios_portrait,'EXECUTABLE',old[1]))
 def test_unpinned_pieces_are_skipped(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.locks(tmp,'')
   self.assertEqual(ios_portrait.fetch(Path(tmp)/'out',get=lambda url:self.fail('no download expected')),[])
 def test_pinned_framework_is_verified(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=b'framework';self.locks(tmp,ios_portrait.sha(data))
   self.assertEqual(ios_portrait.fetch(Path(tmp)/'out',get=lambda url:data),['KodiGlassBar'])
   self.locks(tmp,'0'*64)
   with self.assertRaises(AssertionError):ios_portrait.fetch(Path(tmp)/'out2',get=lambda url:data)
 def test_repository_pins_the_published_framework(self):
  lock=json.loads((ROOT/'migration/glassbar-ios/source-lock.json').read_text())['framework_release']
  self.assertEqual(len(lock['sha256']),64)
 def test_framework_unpacked_into_frameworks(self):
  with tempfile.TemporaryDirectory() as tmp:
   buf=io.BytesIO()
   with zipfile.ZipFile(buf,'w') as z:z.writestr('KodiGlassBar.framework/KodiGlassBar',b'bin');z.writestr('KodiGlassBar.framework/Info.plist',b'x')
   archive=Path(tmp)/'bar.zip';archive.write_bytes(buf.getvalue());app=Path(tmp)/'Kodi.app';app.mkdir()
   info=ios_portrait.add_glassbar(app,archive)
   self.assertEqual(info['framework'],'Frameworks/KodiGlassBar.framework');self.assertTrue((app/info['framework']/'KodiGlassBar').is_file())
   with self.assertRaises(AssertionError):ios_portrait.add_glassbar(app,archive)
 def test_glass_bar_source_exports_the_functions_python_loads(self):
  src=(ROOT/'migration/glassbar-ios/build-glassbar.sh').read_text()
  for name in ('kodi_glassbar_show','kodi_glassbar_select','kodi_glassbar_take_tap'):self.assertIn('void '+name if name!='kodi_glassbar_take_tap' else 'int '+name,src)
  self.assertIn('NSClassFromString(@"UIGlassEffect")',src)
 def test_skin_tab_bar_only_without_the_native_one(self):
  # Owner: two tab bars overlapped and swapped when switching quickly (the skin's showed whenever the native one hid).
  spec=importlib.util.spec_from_file_location('portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
  portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
  self.assertIn('<visible>!Skin.HasSetting(Portrait.NativeTabBar)</visible>',portrait.tabbar('home'))
  self.assertNotIn('Portrait.GlassBar',portrait.tabbar('home'))
 def test_glass_bar_owns_the_strip_around_and_below_it(self):
  # r2: a tap that missed the capsule by a little (sides, home-indicator area, just above) opened the row behind.
  src=(ROOT/'migration/glassbar-ios/build-glassbar.sh').read_text()
  self.assertIn('- (BOOL)pointInside:(CGPoint)point withEvent:(UIEvent *)event {',src)
  self.assertIn('CGRectGetMinY([self convertRect:self.bounds toView:window]) - 12',src)
  self.assertIn('inWindow.y <= CGRectGetMaxY(window.bounds)',src)
 def test_airplay_source_exports_the_functions_python_loads(self):
  src=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for name in ('void kodi_airplay_show(int','void kodi_airplay_open(void','void kodi_airplay_play(const char','int kodi_airplay_state(void',
               'void kodi_airplay_close(void','void kodi_background_keep(int'):self.assertIn('__attribute__((visibility("default"))) '+name,src)
  # Silence mixed with other apps, only in the background, restarted after a call.
  for text in ('AVAudioSessionCategoryOptionMixWithOthers','UIApplicationDidEnterBackgroundNotification','AVAudioSessionInterruptionTypeEnded'):self.assertIn(text,src)
  # r4: Apple's player keeps Kodi's orientation, sits over Kodi, and asks Kodi to rebuild its screen when it closes.
  for text in ('UIModalPresentationOverFullScreen','- (BOOL)shouldAutorotate { return NO; }','NSSelectorFromString(@"applyRotatedScreen")'):self.assertIn(text,src)
if __name__=='__main__':unittest.main()
