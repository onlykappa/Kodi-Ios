"""Bug 4: completed media appears before cosmetic artwork requests; background work yields to actual use."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
import ios_library as page

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

drive=load('art_drive_fixture',BOOT/'drivelibrary.py')
worker=load('art_worker_fixture',BOOT/'library_watch.py')
RESPONSE=json.dumps({'results':[{'id':42,'poster_path':'/poster.jpg','backdrop_path':'/background.jpg'}]}).encode()

def movie(title='Heat',year='1995',**extra):
 return dict(title=title,year=year,season='',episode='',path='/phone/'+title+'.mkv',id=title,name=title+'.mkv',**extra)

class CachedForeground(unittest.TestCase):
 def test_actual_directory_uses_cached_only_rows_and_never_overwrites_hydrated_cache(self):
  fixture=load('art_actual_directory_fixture',ROOT/'scripts/test_library_refresh.py').ActualDirectory()
  with mock.patch.object(page,'local_rows',wraps=page.local_rows) as local,mock.patch.object(page,'drive_rows',wraps=page.drive_rows) as remote:
   fixture.render(['/phone/Kodi Downloads/Movies/Heat.1995.mkv'],drive_enabled=True)
  self.assertTrue(local.call_args.kwargs['cached_only']);self.assertTrue(remote.call_args.kwargs['cached_only'])
  remote.call_args.args[3].save_json.assert_not_called()
 def test_local_and_drive_rows_use_existing_art_without_any_missing_art_http(self):
  network=mock.Mock(side_effect=AssertionError('foreground artwork network call'))
  cache={'movie:heat:1995':{'poster':'cached-poster'}}
  local=page.local_rows('movie','','',[movie(),movie('Missing')],drive,cache,'KEY',network,cached_only=True)
  self.assertEqual(local[0][2]['poster'],'cached-poster');self.assertEqual(local[1][2],{})
  with mock.patch.object(drive,'listing',return_value=([movie(),movie('Missing')],'drive')):
   rows=page.drive_rows('movie',None,'',drive,'state',cache,'KEY',network,cached_only=True)
  self.assertEqual(rows[0][2]['poster'],'cached-poster');self.assertFalse(rows[1][2]['poster'])
  network.assert_not_called();self.assertEqual(len(cache),1)
 def test_tv_root_and_episode_rows_also_do_not_fetch_art(self):
  network=mock.Mock(side_effect=AssertionError('foreground artwork network call'))
  entry=dict(movie('Lanterns'),season='1',episode='2')
  for folder in (None,'show-folder'):
   with self.subTest(folder=folder),mock.patch.object(drive,'listing',return_value=([entry],'drive')):
    page.drive_rows('tv',folder,'Lanterns' if folder else '',drive,'state',{},'KEY',network,cached_only=True)
  page.local_rows('tv','','',[entry],drive,{},'KEY',network,cached_only=True)
  page.local_rows('tv','Lanterns','1995',[entry],drive,{},'KEY',network,cached_only=True)
  network.assert_not_called()
 def test_missing_key_does_not_cache_an_empty_result_forever(self):
  cache={};network=mock.Mock(return_value=RESPONSE)
  self.assertEqual(drive.artwork('movie','Heat','1995','',cache,network),{})
  self.assertEqual(cache,{});network.assert_not_called()
  self.assertIn('poster',drive.artwork('movie','Heat','1995','KEY',cache,network));network.assert_called_once()
 def test_spaced_episode_only_filename_uses_parent_show(self):
  import ios_downloaded
  with mock.patch.object(ios_downloaded,'completed_files',return_value=['/phone/TV Shows/Lanterns/Season 1/S01 E02.mkv']):
   entries=page.local_entries('tv',drive)
  self.assertEqual([(e['title'],e['season'],e['episode']) for e in entries],[('Lanterns','1','2')])

class BackgroundHydration(unittest.TestCase):
 def hydrate(self,tmp,entries,get,**kwargs):
  return worker.hydrate_artwork({'type':'movie'},entries,[],drive,tmp,'KEY',get,lambda:True,**kwargs)
 def test_missing_posters_are_saved_once_then_reused(self):
  network=mock.Mock(return_value=RESPONSE)
  with tempfile.TemporaryDirectory() as tmp:
   self.assertTrue(self.hydrate(tmp,[movie()],network));self.assertFalse(self.hydrate(tmp,[movie()],network))
   cache=drive.load_json(str(Path(tmp)/'drive-library-art.json'),{})
   self.assertEqual(cache['movie:heat:1995']['poster'],drive.IMAGE+'w500/poster.jpg')
  network.assert_called_once();self.assertGreater(network.call_args.args[1],0);self.assertLessEqual(network.call_args.args[1],2)
 def test_time_budget_stops_requests_and_caps_each_timeout(self):
  now=[0];timeouts=[]
  def get(url,timeout):timeouts.append(timeout);now[0]+=3;return RESPONSE
  with tempfile.TemporaryDirectory() as tmp:
   self.assertTrue(self.hydrate(tmp,[movie('Movie '+str(i)) for i in range(20)],get,clock=lambda:now[0]))
  self.assertEqual(timeouts,[2,1])
 def test_healthy_fast_requests_are_still_limited_to_six_titles(self):
  network=mock.Mock(return_value=RESPONSE)
  with tempfile.TemporaryDirectory() as tmp:self.hydrate(tmp,[movie('Movie '+str(i)) for i in range(20)],network,clock=lambda:0)
  self.assertEqual(network.call_count,6)
 def test_leaving_page_during_a_request_stops_the_batch(self):
  active=[True]
  def get(url,timeout):active[0]=False;return RESPONSE
  network=mock.Mock(side_effect=get)
  with tempfile.TemporaryDirectory() as tmp:
   worker.hydrate_artwork({'type':'movie'},[movie('One'),movie('Two')],[],drive,tmp,'KEY',network,lambda:active[0])
  network.assert_called_once()
 def test_off_page_busy_or_no_key_does_no_artwork_or_cache_write(self):
  for key,active in (('KEY',False),('',True)):
   with self.subTest(key=key,active=active),tempfile.TemporaryDirectory() as tmp:
    network=mock.Mock(return_value=RESPONSE)
    self.assertFalse(worker.hydrate_artwork({'type':'movie'},[movie()],[],drive,tmp,key,network,lambda:active))
    network.assert_not_called();self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_loose_show_filters_other_shows_and_episode_art_matches_displayed_cache_key(self):
  entries=[movie('Lanterns'),movie('Other')]
  params={'type':'tv','folder':'root','show':'Lanterns','year':'1995','loose':'1'}
  self.assertEqual(list(worker.art_titles(params,[],entries)),[('tv','Lanterns','')])

class ArtworkRefresh(unittest.TestCase):
 def simulate(self,hydration,busy_art=None):
  state={'tick':-1};calls=[];path=[page.page_url({'type':'movie'})];busy_art=busy_art or [False]*4
  def wait(seconds):state['tick']+=1;return state['tick']>=len(busy_art)
  with tempfile.TemporaryDirectory() as tmp:
   worker.watch(lambda:path[0],lambda:False,lambda action:calls.append(state['tick']),wait,
    SimpleNamespace(current_params=page.current_params,local_entries=lambda *a:[]),
    SimpleNamespace(listing=lambda *a,**kw:([],None)),tmp,clock=lambda:state['tick']*5,
    hydrate=lambda *a:hydration(state,path),art_every=5,art_busy=lambda:busy_art[state['tick']])
  return calls
 def test_only_actual_art_change_refreshes_an_unchanged_visible_page(self):
  self.assertEqual(self.simulate(lambda state,path:state['tick']==2),[0,2])
 def test_download_activity_defers_cosmetic_work(self):
  called=[]
  def hydrate(state,path):called.append(state['tick']);return True
  self.assertEqual(self.simulate(hydrate,[True,True,False,False]),[0,2,3]);self.assertEqual(called,[2,3])
 def test_leaving_during_art_lookup_never_refreshes_the_new_page(self):
  def hydrate(state,path):path[0]='plugin://another/';return True
  self.assertEqual(self.simulate(hydrate),[])

if __name__=='__main__':unittest.main()
