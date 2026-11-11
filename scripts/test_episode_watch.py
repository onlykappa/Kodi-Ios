"""Advance a fake calendar through an anticipated release and exercise persistent opening-only checks."""
import copy,datetime,importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import episode_watch as watch,episode_watch_runtime as runtime,debrid_drive,elementum_cloud,elementum_download
from test_elementum_cloud import url,magnet

def timestamp(date):return datetime.datetime.fromisoformat(date).replace(tzinfo=datetime.timezone.utc).timestamp()
def ep(n,aired,season=1):return {'season_number':season,'episode_number':n,'name':'Episode '+str(n),'air_date':aired}

class Calendar(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.profile=self.tmp.name
  self.now=timestamp('2026-11-10T12:00:00');self.downloaded=[];self.logs=[]
  watch.register(self.profile,'123','Show',1,1,{'quality':'4k','hdr':'HDR10','codec':'HEVC'},self.now)
  self.details={'id':123,'seasons':[{'season_number':1,'air_date':'2026-10-01'}]}
  self.rows=[ep(1,'2026-11-10'),ep(2,'2026-11-11'),ep(3,None)]
  self.owned=lambda show,row:row['season_number']==1 and row['episode_number']==1
  self.fetch=lambda show,row:self.downloaded.append((show['tmdb'],row['season_number'],row['episode_number'],show['preference'])) or True
 def sweep(self,**kwargs):
  args=dict(get_show=lambda ident:copy.deepcopy(self.details),get_season=lambda *a:{'episodes':copy.deepcopy(self.rows)},
            existing=self.owned,download=self.fetch,clock=lambda:self.now,log=lambda *a,**k:self.logs.append((a,k)))
  args.update(kwargs);return watch.sweep(self.profile,**args)
 def test_future_and_unknown_dates_wait_then_release_is_queued_once_across_restarts(self):
  self.assertEqual(self.sweep(),0);self.assertEqual(self.downloaded,[])
  self.now=timestamp('2026-11-11T12:00:00');self.assertEqual(self.sweep(),1)
  self.assertEqual(self.downloaded[0][:3],('123',1,2));self.assertEqual(self.downloaded[0][3]['quality'],'4k')
  self.now+=3600;self.assertEqual(self.sweep(),0);self.assertEqual(len(self.downloaded),1)
  self.assertEqual(watch.load(self.profile)['shows']['123']['episodes']['1:2']['status'],'queued')
 def test_missing_source_is_retried_on_a_later_opening(self):
  self.now=timestamp('2026-11-11T12:00:00')
  self.assertEqual(self.sweep(download=lambda *a:False),0)
  self.now+=watch.COOLDOWN+1;self.assertEqual(self.sweep(),1)
 def test_a_failed_queued_download_retries_but_a_canceled_or_active_one_does_not(self):
  self.now=timestamp('2026-11-11T12:00:00');self.assertEqual(self.sweep(),1)
  self.now+=watch.COOLDOWN+1
  self.assertEqual(self.sweep(existing=lambda show,row:True),0)
  self.now+=watch.COOLDOWN+1
  self.assertEqual(self.sweep(existing=lambda show,row:'failed' if row['episode_number']==2 else True),1)
  self.assertEqual(len(self.downloaded),2)
 def test_imdb_metadata_resolution_retains_the_canonical_show_id_for_following(self):
  import source_match
  def metadata(path,*args):
   return {'tv_results':[{'id':123}]} if path.startswith('/find/') else {'id':123,'name':'Show','first_air_date':'2026-01-01'}
  with patch.object(source_match,'tmdb_get',side_effect=metadata):
   result=source_match.enrich(source_match.expected('episode',['Show'],imdb='tt123',season=1,episode=2),key='synthetic')
  self.assertEqual(result['tmdb'],'123')
 def test_ownership_failure_defers_instead_of_assuming_missing(self):
  self.now=timestamp('2026-11-11T12:00:00')
  self.sweep(existing=lambda *a:(_ for _ in ()).throw(OSError('offline')))
  self.assertFalse(self.downloaded);self.assertEqual(self.logs[-1][0],('check_deferred',))
 def test_metadata_failure_is_not_cached_as_an_empty_finished_season(self):
  self.now=timestamp('2026-11-11T12:00:00');self.sweep(get_season=lambda *a:None)
  self.now+=watch.COOLDOWN+1;self.assertEqual(self.sweep(),1)
 def test_registration_does_not_backfill_old_seasons_or_specials(self):
  self.rows=[ep(1,'2026-10-10'),ep(1,'2026-11-10',0),ep(2,'not-a-date')]
  self.assertEqual(self.sweep(),0);self.assertFalse(self.downloaded)
 def test_later_announced_season_is_discovered_from_fresh_metadata(self):
  self.now=timestamp('2027-01-01T12:00:00')
  self.details['seasons'].append({'season_number':2,'air_date':'2027-01-01'})
  self.rows=[ep(1,'2027-01-01',2)]
  self.assertEqual(self.sweep(),1);self.assertEqual(self.downloaded[0][1:3],(2,1))
 def test_opening_cooldown_and_attempt_cap_bound_work(self):
  self.rows=[ep(i,'2026-11-10') for i in range(1,30)]
  self.assertEqual(self.sweep(),watch.MAX_EPISODES)
  self.assertEqual(self.sweep(),0);self.assertEqual(len(self.downloaded),watch.MAX_EPISODES)
 def test_new_registration_during_sweep_is_not_overwritten(self):
  def fetch(*args):watch.register(self.profile,'456','Other show',1,1,{'quality':'1080p'},self.now);return True
  self.now=timestamp('2026-11-11T12:00:00');self.sweep(download=fetch)
  self.assertEqual(set(watch.load(self.profile)['shows']),{'123','456'})
 def test_registration_preserves_start_date_and_prior_episode_ledger(self):
  self.now=timestamp('2026-11-11T12:00:00');self.sweep()
  watch.register(self.profile,'123','Show',1,2,{'quality':'1080p'},self.now)
  show=watch.load(self.profile)['shows']['123']
  self.assertEqual(show['since'],timestamp('2026-11-10T12:00:00'));self.assertEqual(show['episodes']['1:2']['status'],'queued')
 def test_cancellation_never_launches_a_search(self):
  self.sweep(keep_going=lambda:False);self.assertFalse(self.downloaded)
 def test_actual_dates_and_season_numbers_beat_episode_names(self):
  self.rows=[dict(ep(2,'2026-11-12'),name='Available now!')]
  self.assertEqual(self.sweep(),0)
 def test_picker_selection_requires_fresh_matching_name_and_show_id(self):
  pick={'show_tmdb':'456','season':1,'episode':2,'selection_name':'Other.S01E02.mkv','time':self.now,'quality':'4k'}
  window=types.SimpleNamespace(getProperty=lambda key:json.dumps(pick))
  self.assertFalse(watch.remember_selection(self.profile,window,{'name':'wrong'},'Other',self.now))
  self.assertTrue(watch.remember_selection(self.profile,window,{'name':pick['selection_name'],'season':'1','episode':'2'},'Other',self.now))
  self.assertIn('456',watch.load(self.profile)['shows'])
  pick['time']=self.now-301;self.assertFalse(watch.remember_selection(self.profile,window,{'name':pick['selection_name']},'Other',self.now))
 def test_existing_library_preference_uses_the_downloaded_shows_resolution(self):
  import prepare_downloads
  prepare_downloads.save(self.profile,{'library':{'items':[{'name':'Show.S01E01.2160p.HEVC.mkv','folder':'Show'},
                                                           {'name':'Other.S01E01.720p.mkv','folder':'Other'}]}})
  self.assertEqual(watch.library_preference(self.profile,'Show')['quality'],'4k')
 def test_same_episode_number_from_two_seasons_of_one_pack_stays_separate(self):
  torrent={'id':'a1'*20,'name':'Show.Complete.S01-S02'}
  debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,now=1,show_tmdb='123')
  debrid_drive.queue(self.profile,torrent,'episode','Show',2,2,now=1,show_tmdb='123')
  self.assertEqual([(j['season'],j['episode']) for j in debrid_drive.load(self.profile)['jobs']],[('1','2'),('2','2')])
 def test_old_inflight_job_can_gain_show_identity_without_being_queued_again(self):
  torrent={'id':'a1'*20,'name':'Show.S01E02'}
  debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,now=1)
  debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,now=2,show_tmdb='123')
  jobs=debrid_drive.load(self.profile)['jobs'];self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['show_tmdb'],'123')
 def test_foreground_and_watcher_cannot_enqueue_the_same_source_twice(self):
  import concurrent.futures
  torrent={'id':'a1'*20,'name':'Show.S01E02'}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   list(pool.map(lambda n:debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,show_tmdb='123'),range(8)))
  self.assertEqual(len(debrid_drive.load(self.profile)['jobs']),1)
 def test_worker_saving_old_state_preserves_new_show_identity(self):
  torrent={'id':'a1'*20,'name':'Show.S01E02'}
  debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,now=1)
  held=debrid_drive.load(self.profile)
  debrid_drive.queue(self.profile,torrent,'episode','Show',1,2,show_tmdb='123')
  held['jobs'][0]['status']='fetching';debrid_drive.save(self.profile,held)
  self.assertEqual(debrid_drive.load(self.profile)['jobs'][0]['show_tmdb'],'123')

class Openings(unittest.TestCase):
 def test_only_launch_and_foreground_transitions_check_once_and_busy_defers(self):
  frames=[(True,True),(True,False),(True,False),(False,False),(False,False),(True,False),(True,False)]
  state={'i':-1};calls=[]
  def wait(seconds):state['i']+=1;return state['i']>=len(frames)
  watch.run_open_checks(types.SimpleNamespace(waitForAbort=wait),lambda:True,lambda:frames[state['i']][0],
   lambda:frames[state['i']][1],lambda:True,lambda:calls.append(state['i']))
  self.assertEqual(calls,[1,5])
 def test_disabled_setting_does_not_check(self):
  turns=iter([False,False,True]);check=Mock()
  watch.run_open_checks(types.SimpleNamespace(waitForAbort=lambda delay:next(turns)),lambda:True,lambda:True,lambda:False,lambda:False,check)
  check.assert_not_called()

class Runtime(unittest.TestCase):
 def test_follow_only_enrolls_an_existing_show_without_downloading_again_or_requiring_engine(self):
  fixture,home,props=self.setup_runtime();fixture.dialog.select.return_value=2
  spec=importlib.util.spec_from_file_location('follow_download_entry',ROOT/'migration/bundled-bootstrap/download.py')
  entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
  with patch.dict(sys.modules,{'elementum_engine':types.SimpleNamespace(running=lambda:False)}),\
       patch.object(sys,'argv',['download.py','kind=season','title=Show','season=1','path=plugin://plugin.video.themoviedb.helper/?tmdb_id=123&tmdb_type=tv&season=1']),\
       patch.object(elementum_download,'follow') as follow:
   entry.run()
  self.assertIn('123',watch.load(fixture.tmp.name)['shows']);follow.assert_not_called();fixture.dialog.ok.assert_not_called()
 def setup_runtime(self):
  from test_elementum_cloud import Route
  fixture=Route();fixture.setUp();self.addCleanup(fixture.doCleanups)
  props={}
  home=types.SimpleNamespace(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.update({k:v}),clearProperty=lambda k:props.pop(k,None))
  fixture.mods['xbmcgui'].Window=lambda ident:home;fixture.mods['xbmcgui'].ListItem=lambda label='',label2='':label+'\x1f'+label2
  return fixture,home,props
 def test_startup_wiring_never_runs_an_episode_check_on_the_main_thread(self):
  source=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('target=episode_watch_runtime.run',source);self.assertIn('setup_done.is_set',source)
 def test_queue_requires_request_result_not_just_a_source_pick(self):
  from test_elementum_cloud import Route
  fixture=Route();fixture.setUp();self.addCleanup(fixture.doCleanups)
  properties={'KodiIOS.AutoPick':json.dumps({'target':{'tmdb':'123','season':1,'episode':2},'request_id':'request','mode':0,'until':time.time()+600})}
  home=types.SimpleNamespace(getProperty=lambda k:properties.get(k,''),setProperty=lambda k,v:properties.update({k:v}),clearProperty=lambda k:properties.pop(k,None))
  fixture.mods['xbmcgui'].Window=lambda ident:home
  self.assertTrue(elementum_cloud.route(url(uri=magnet(),season='1',episode='2'),quiet=True,request_id='request'))
  self.assertEqual(fixture.jobs(),[]);fixture.dialog.select.assert_not_called()
  properties['KodiIOS.AutoPick.Result']=json.dumps({'request_id':'request','found':True,'name':'Show.S01E02.2160p.HDR'})
  self.assertTrue(elementum_cloud.route(url(uri=magnet(),season='1',episode='2'),quiet=True,request_id='request'))
  self.assertEqual(len(fixture.jobs()),1);self.assertEqual(fixture.jobs()[0]['show_tmdb'],'123')
  self.assertTrue(json.loads(properties['KodiIOS.AutoPick.Queued'])['queued']);fixture.dialog.select.assert_not_called()
 def test_actual_download_selection_enrolls_the_show_and_tags_the_inflight_job(self):
  fixture,home,props=self.setup_runtime()
  props['KodiIOS.SeasonPick']=json.dumps({'show_tmdb':'123','season':1,'episode':2,'selection_name':'Show.S01E02.2160p.HDR',
                                       'time':time.time(),'quality':'4k'})
  elementum_cloud.route(url(uri=magnet(),season='1',episode='2'))
  self.assertIn('123',watch.load(fixture.tmp.name)['shows']);self.assertEqual(fixture.jobs()[0]['show_tmdb'],'123')
 def test_runtime_catalog_picker_and_queue_work_together_without_dialogs(self):
  import drivelibrary,library_scan,source_match
  spec=importlib.util.spec_from_file_location('episode_picker',ROOT/'migration/deck-picker/deck_picker.py')
  picker=importlib.util.module_from_spec(spec);spec.loader.exec_module(picker)
  fixture,home,props=self.setup_runtime();now=time.time();today=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).date().isoformat()
  watch.register(fixture.tmp.name,'123','Show',1,1,{'quality':'4k','codec':'HEVC'},now-86400)
  details={'id':123,'name':'Show','first_air_date':'2026-10-01','seasons':[{'season_number':1,'air_date':'2026-10-01'}]}
  def api(request,timeout):
   import io
   return io.BytesIO(json.dumps({'episodes':[ep(2,today)]} if '/season/' in request else details).encode())
  def follow(request,**kwargs):
   self.assertIn('/show/123/season/1/episode/2/download',request)
   result=picker.run('Show S01E02',['4K (15 / 1) [2.00 GB] WEB H.265 - Source\nShow.S01E02.2160p.HDR\nicon.png'],
                    expect=source_match.expected('episode',['Show'],tmdb='123',season=1,episode=2))
   self.assertEqual(result,0)
   kwargs['route'](url(uri=magnet(),season='1',episode='2'))
  with patch.object(runtime.urllib.request,'urlopen',side_effect=api),patch.object(source_match,'tmdb_key',return_value='synthetic'),\
       patch.object(drivelibrary,'client',return_value=(object(),'drive')),patch.object(library_scan,'remote_files',return_value=[]),\
       patch.dict(sys.modules,{'elementum_engine':types.SimpleNamespace(running=lambda:True),'ios_downloaded':types.SimpleNamespace(completed_copy=lambda *a,**k:None)}),\
       patch.object(elementum_download,'follow',side_effect=follow),patch.object(picker,'_home',return_value=home):
   count=runtime.pass_once(fixture.tmp.name,home,lambda:True,lambda *a,**k:None)
   self.assertEqual(count,1);self.assertEqual(len(fixture.jobs()),1)
   self.assertEqual(runtime.pass_once(fixture.tmp.name,home,lambda:True,lambda *a,**k:None),0)
  self.assertFalse(home.getProperty(watch.AUTO));fixture.dialog.select.assert_not_called();fixture.dialog.ok.assert_not_called()
 def test_quiet_account_failure_does_not_interrupt_the_user(self):
  fixture,home,props=self.setup_runtime();fixture.addon.getSetting.return_value=''
  elementum_cloud.route(url(uri=magnet(),season='1',episode='2'),quiet=True,request_id='missing')
  self.assertEqual(fixture.jobs(),[]);fixture.dialog.ok.assert_not_called();fixture.dialog.select.assert_not_called()
 def test_expired_automatic_request_does_not_block_future_opening_checks(self):
  fixture,home,props=self.setup_runtime()
  props[watch.AUTO]=json.dumps({'until':100,'target':{'tmdb':'123','season':1,'episode':2}})
  self.assertIsNone(watch.active_request(home,now=101));self.assertNotIn(watch.AUTO,props)
 def test_late_results_are_suppressed_and_an_explicit_retry_can_clear_the_marker(self):
  fixture,home,props=self.setup_runtime();target={'tmdb':'123','season':1,'episode':2}
  watch.cancel_request(home,{'target':target},now=100)
  self.assertTrue(watch.canceled(home,target,now=101))
  self.assertFalse(watch.canceled(home,dict(target,episode=3),now=101))
  watch.canceled(home,target,now=102,clear=True)
  self.assertFalse(watch.canceled(home,target,now=103))
 def test_no_source_rows_in_an_automatic_search_never_open_the_manual_picker(self):
  spec=importlib.util.spec_from_file_location('empty_episode_picker',ROOT/'migration/deck-picker/deck_picker.py')
  picker=importlib.util.module_from_spec(spec);spec.loader.exec_module(picker)
  fixture,home,props=self.setup_runtime();target={'tmdb':'123','season':1,'episode':2}
  props[watch.AUTO]=json.dumps({'target':target,'request_id':'request','until':time.time()+600})
  with patch.object(picker,'_home',return_value=home):
   self.assertEqual(picker.run('Show S01E02',[],expect=dict(target,kind='episode')),-1)

import time
if __name__=='__main__':unittest.main()
