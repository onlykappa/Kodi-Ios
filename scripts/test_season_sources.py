"""Exercise actual source filtering, strict quality queue receipts, durable retries and pre-transfer visibility."""
import datetime,http.server,importlib.util,io,json,sys,tempfile,threading,time,types,unittest,urllib.error,urllib.parse
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'migration/bundled-bootstrap')]
import season_sources as season,episode_watch as watch,source_match,debrid_drive,work_state,library_rows,prepare_downloads,tool_windows
spec=importlib.util.spec_from_file_location('season_deck',ROOT/'migration/deck-picker/deck_picker.py')
deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)

class Home:
 def __init__(self):self.p={}
 def getProperty(self,k):return self.p.get(k,'')
 def setProperty(self,k,v):self.p[k]=v
 def clearProperty(self,k):self.p.pop(k,None)

def line(name,q='1080p',seeds=20):return '%s (%d / 0) [2.0 GB] WEB-DL H.265 - Test\n%s\nicon.png'%(q,seeds,name)

class Picker(unittest.TestCase):
 def setUp(self):
  self.home=Home();self.exp=source_match.expected('episode',['Sample Show'],tmdb='123',season=1,episode=1)
  self.patch=patch.object(deck,'_home',return_value=self.home);self.patch.start();self.addCleanup(self.patch.stop)
 def request(self,purpose,episode=1,quality=None):
  self.home.setProperty(watch.AUTO,json.dumps({'request_id':'test','until':10**12,'purpose':purpose,
    'target':{'tmdb':'123','season':1,'episode':episode},'profile':{'quality':quality,'strict_quality':True}}))
 def test_scan_hides_dead_wrong_title_and_bad_sources_and_never_opens_ui(self):
  self.request('scan')
  rows=[line('Sample.Show.S01E01.1080p.HEVC'),line('Sample.Show.S01E01.2160p.HEVC','4k',0),
        line('Other.Show.S01E01.2160p.HEVC','4k'),line('Sample.Show.S01E02.2160p.HEVC','4k')]
  with patch.object(deck,'choose_source',side_effect=AssertionError('scan opened picker')):
   self.assertEqual(deck.run('Sample Show',rows,expect=self.exp),-1)
  self.assertEqual(json.loads(self.home.getProperty(watch.RESULT))['qualities'],['1080p'])
 def test_strict_queue_never_uses_lower_quality(self):
  self.request('queue',quality='4k')
  self.assertEqual(deck.run('Sample Show',[line('Sample.Show.S01E01.1080p.HEVC')],expect=self.exp),-1)
  self.assertFalse(json.loads(self.home.getProperty(watch.RESULT))['found'])
 def test_scan_identity_mismatch_never_falls_back_to_a_manual_picker(self):
  self.request('scan')
  wrong=dict(self.exp,tmdb='999')
  with patch.object(deck,'choose_source',side_effect=AssertionError('mismatched scan opened picker')):
   self.assertEqual(deck.run('Sample Show',[line('Sample.Show.S01E01.1080p.HEVC')],expect=wrong),-1)
  self.assertIn('error',json.loads(self.home.getProperty(watch.RESULT)))
 def test_packs_never_offer_single_episodes_even_with_show_all(self):
  self.request('packs',episode=None)
  exp=source_match.expected('season',['Sample Show'],tmdb='123',season=1)
  rows=[line('Sample.Show.S01E01.2160p.HEVC','4k')]+[line('Sample.Show.S01.Complete.1080p.HEVC.%d'%i) for i in range(8)]
  shown=[]
  with patch.object(deck,'choose_source',side_effect=lambda title,rows,*args:shown.extend(rows) or -1):
   self.assertEqual(deck.run('Sample Show',rows,expect=exp),-1)
  self.assertEqual(len(shown),8)
  self.assertNotIn('Episode 1 only',json.dumps(shown))
  self.assertTrue(json.loads(self.home.getProperty(watch.RESULT))['packs'])
 def test_partial_season_only_triggers_episode_fallback(self):
  self.request('packs',episode=None)
  exp=source_match.expected('season',['Sample Show'],tmdb='123',season=1)
  with patch.object(deck,'choose_source',side_effect=AssertionError('partial pack offered')):
   self.assertEqual(deck.run('Sample Show',[line('Sample.Show.S01E01.1080p.HEVC')],expect=exp),-1)
  self.assertFalse(json.loads(self.home.getProperty(watch.RESULT))['packs'])

class Rows(unittest.TestCase):
 def test_full_and_partial_coverage_lines(self):
  sources={n:['1080p']+(['4k'] if n<=6 else []) for n in range(1,9)}
  rows=season.quality_rows([('4k',6),('1080p',8)],sources,list(range(1,9)))
  self.assertEqual(rows[1],('[B]1080p Full HD[/B]','[COLOR FF30D158]All 8 episodes[/COLOR]'))
  self.assertEqual(rows[0][1],'[COLOR FFFF9F0A]6 of 8[/COLOR] \u00b7 1\u20136 now, 7\u20138 wait')
  self.assertEqual(season.spans([1,2,3,5,7,8]),'1\u20133, 5, 7\u20138')

class Batch(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.notes=[];self.labels=[];self.pick=0;self.calls=[];self.cancel=False
  owner=self
  class Progress:
   def create(self,*a):pass
   def update(self,*a):pass
   def iscanceled(self):return owner.cancel
   def close(self):pass
  self.gui=types.SimpleNamespace(DialogProgress=Progress,NOTIFICATION_INFO=0)
  self.xbmc=types.SimpleNamespace(Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:False))
  self.dialog=types.SimpleNamespace(select=lambda title,rows:self.labels.extend(rows) or self.pick,
   ok=lambda *a:self.notes.append(a),notification=lambda *a:self.notes.append(a))
 def run_batch(self,sources,receipts=None):
  def search(n,purpose,q=None):
   self.calls.append((n,purpose,q))
   return {'qualities':sources.get(n,[])} if purpose=='scan' else {'found':True,'queued':(receipts or {}).get(n,True)}
  return season.run(self.xbmc,self.gui,self.dialog,Home(),self.tmp.name,'123','Sample Show',1,[1,2,3],{1},search)
 def test_only_actual_quality_options_and_missing_episodes_wait_without_downgrade(self):
  self.assertEqual(self.run_batch({2:['1080p'],3:[]}),[2])
  # Board 3 rows: quality in bold, then coverage (episode 2 now, episode 3 waits).
  self.assertEqual(self.labels,['[B]1080p Full HD[/B]\x1f[COLOR FFFF9F0A]1 of 2[/COLOR] \u00b7 2 now, 3 waits'])
  self.assertEqual(self.calls,[(2,'scan',None),(3,'scan',None),(2,'queue','1080p')])
  planned=watch.load(self.tmp.name)['shows']['123']['planned']
  self.assertEqual(planned['1:3'],{'quality':'1080p','status':'not_found'})
 def test_selected_source_without_queue_receipt_never_counts_as_queued(self):
  self.assertEqual(self.run_batch({2:['4k'],3:['1080p']},{2:False}),[])
  self.assertEqual([l.split('\x1f')[0] for l in self.labels],['[B]4K Ultra HD[/B]','[B]1080p Full HD[/B]'])
 def test_cancel_quality_creates_no_plan(self):
  self.pick=-1;self.assertEqual(self.run_batch({2:['1080p']}),[])
  self.assertFalse(watch.load(self.tmp.name)['shows'])
 def test_cancel_scan_creates_no_plan_or_quality_dialog(self):
  self.cancel=True;self.assertEqual(self.run_batch({2:['1080p']}),[]);self.assertFalse(self.labels)
 def test_no_sources_has_no_unavailable_menu_options(self):
  self.assertEqual(self.run_batch({}),[]);self.assertFalse(self.labels)
 def test_scan_budget_offers_only_seen_qualities_and_retains_unscanned_episodes(self):
  clock=[0]
  def search(n,purpose,q=None):
   self.calls.append((n,purpose,q))
   if purpose=='scan':clock[0]+=31;return {'qualities':['1080p']}
   return {'queued':True}
  with patch.object(season.time,'monotonic',side_effect=lambda:clock[0]):
   got=season.run(self.xbmc,self.gui,self.dialog,Home(),self.tmp.name,'123','Sample Show',1,[1,2,3,4],set(),search)
  self.assertEqual(got,[1,2])
  self.assertEqual([n for n,p,q in self.calls if p=='scan'],[1,2])
  planned=watch.load(self.tmp.name)['shows']['123']['planned']
  self.assertEqual(planned['1:3'],{'quality':'1080p','status':'not_found'})
  self.assertEqual(planned['1:4'],{'quality':'1080p','status':'not_found'})
 def test_cancel_during_last_scan_never_opens_quality_or_creates_plan(self):
  def search(*args):self.cancel=True;return {'qualities':['4k']}
  self.assertEqual(season.run(self.xbmc,self.gui,self.dialog,Home(),self.tmp.name,'123','Sample Show',1,[1],set(),search),[])
  self.assertFalse(self.labels);self.assertFalse(watch.load(self.tmp.name)['shows'])
 def test_cancel_active_queue_cancels_the_remaining_retry_plan(self):
  def search(n,purpose,q=None):
   if purpose=='scan':return {'qualities':['1080p']}
   self.cancel=True;raise season.dl.Canceled('canceled')
  self.assertEqual(season.run(self.xbmc,self.gui,self.dialog,Home(),self.tmp.name,'123','Sample Show',1,[1,2],set(),search),[])
  show=watch.load(self.tmp.name)['shows']['123']
  self.assertFalse(show['planned']);self.assertEqual(show['episodes']['1:1']['status'],'canceled')
 def test_future_undated_and_specials_are_not_scraped(self):
  rows=[{'episode':n,'firstaired':date} for n,date in [(1,'2026-11-09'),(2,'2026-11-10'),(3,'2026-11-11'),(4,''),(0,'2026-11-09')]]
  self.assertEqual(season.aired(rows,datetime.date(2026,11,10)),[1,2])
 def test_explicit_old_episode_retries_on_opening_at_exact_quality_without_backfilling_others(self):
  watch.plan_season(self.tmp.name,'123','Sample Show',1,[2],'4k',now=1800000000)
  queued=[]
  rows=[{'season_number':1,'episode_number':n,'air_date':'2020-01-01'} for n in (1,2,3)]
  watch.sweep(self.tmp.name,lambda n:{'id':123,'seasons':[{'season_number':1,'air_date':'2020-01-01'}]},
   lambda *a:{'episodes':rows},lambda *a:False,lambda show,row:queued.append((row['episode_number'],show['preference'])) or True,
   clock=lambda:1800002000)
  self.assertEqual(queued,[(2,{'quality':'4k','strict_quality':True})])
 def test_cancel_planned_removes_unprocessed_retries(self):
  watch.plan_season(self.tmp.name,'123','Sample Show',1,[2,3],'1080p')
  watch.cancel_planned(self.tmp.name,'123',1,[3])
  self.assertEqual(set(watch.load(self.tmp.name)['shows']['123']['planned']),{'1:2'})
  self.assertEqual(watch.load(self.tmp.name)['shows']['123']['episodes']['1:3']['status'],'canceled')
 def test_existing_accepted_episode_is_not_searched_or_queued_twice(self):
  debrid_drive.queue(self.tmp.name,{'id':'a1'*20,'name':'Sample.Show.S01E02.1080p'},'episode','Sample Show',1,2,show_tmdb='123')
  self.assertEqual(self.run_batch({2:['1080p'],3:['1080p']}),[3])
  self.assertFalse(any(n==2 for n,p,q in self.calls))
 def test_batch_lane_is_released_after_cancel_and_defers_the_opening_watcher(self):
  home=Home();self.cancel=True
  self.assertEqual(season.run(self.xbmc,self.gui,self.dialog,home,self.tmp.name,'123','Sample Show',1,[1],set()),[])
  self.assertFalse(watch.batch_active(home))
  home.setProperty(watch.BATCH,str(10**12))
  self.assertTrue(watch.batch_active(home))
  self.assertEqual(season.run(self.xbmc,self.gui,self.dialog,home,self.tmp.name,'123','Sample Show',1,[1],set()),[])
  self.assertFalse(self.labels)

class QueueVisibility(unittest.TestCase):
 def test_acceptance_to_transfer_keeps_the_same_detail_identity(self):
  state={'jobs':[{'hash':'a1'*20,'title':'Sample Movie','status':'copying','season':'','episode':''}],'current':{}}
  before=work_state.build({'debrid':state},100)
  state['current']={'stage':'copying','sent':25,'total':100,'folder':'resolved-folder','updated':100}
  after=work_state.build({'debrid':state},100)
  self.assertEqual(work_state.job_key(before['jobs'][0]),work_state.job_key(after['jobs'][0]))
  self.assertEqual(after['jobs'][0]['pct'],25)
 def test_refresh_reads_saved_jobs_despite_idle_published_model(self):
  import transfer_control
  with tempfile.TemporaryDirectory() as profile:
   debrid_drive.queue(profile,{'id':'a1'*20,'name':'Sample.Movie.1080p'},'movie','Sample Movie')
   debrid_drive.queue(profile,{'id':'b2'*20,'name':'Other.Movie.1080p'},'movie','Other Movie')
   transfer_control.set_paused(profile,'up',True)
   model=work_state.current(profile)
   self.assertEqual(model['mode'],work_state.PAUSED)
   self.assertEqual(len(model['jobs']),1);self.assertEqual(len(model['drive_next']),1)
   self.assertTrue(model['jobs'][0]['indeterminate'])
   view=library_rows.with_model(prepare_downloads.library_view({'jobs':{}}),model)
   self.assertEqual(view['total'],2);self.assertEqual(len(view['rows']['waiting']),1)
   row=view['rows']['waiting'][0]
   self.assertIn('Uploads paused',row['sub'])
   detail=library_rows.details(row,view)
   self.assertIn(('Resume','toggle'),detail['actions'])
   q=tool_windows.queue_snapshot(profile)
   self.assertEqual(len(q['drive']),2);self.assertFalse(q['line']);self.assertFalse(q['held'])
   transfer_control.set_paused(profile,'up',False)
   self.assertEqual(work_state.current(profile)['jobs'][0]['state'],work_state.QUEUED)
   saved=debrid_drive.load(profile)
   for job in saved['jobs']:job['status']='done'
   debrid_drive.save(profile,saved)
   emptied=library_rows.with_model(view,work_state.current(profile))
   self.assertFalse(emptied['rows']['waiting']);self.assertEqual(emptied['total'],0)

class RedirectBoundary(unittest.TestCase):
 def setUp(self):
  sys.path.insert(0,str(ROOT/'scripts'))
  import test_elementum_cloud
  self.fixture=test_elementum_cloud.Route('test_cancel_never_enqueues_or_starts_a_player')
  self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.home=Home();self.fixture.mods['xbmcgui'].Window=lambda ident:self.home
  self.exp=source_match.expected('episode',['Sample Show'],tmdb='123',season=1,episode=2)
  self.rows=[line('Sample.Show.S01E02.1080p.HEVC')]
  self.shown=patch.object(deck,'_home',return_value=self.home);self.shown.start();self.addCleanup(self.shown.stop)
 def follow(self,url,timeout,route):
  owner=self
  class Opener:
   def open(self,url,timeout):
    index=deck.run('Sample Show',owner.rows,expect=owner.exp)
    if index<0:return io.BytesIO(b'')
    name=deck.parse_all(owner.rows)[index]['name']
    magnet='magnet:?'+urllib.parse.urlencode({'xt':'urn:btih:'+'a1'*20,'dn':name})
    location=season.dl.ENGINE+'/download?'+urllib.parse.urlencode({'uri':magnet,'season':1,'episode':2})
    raise urllib.error.HTTPError(url,302,'selected',{'Location':location},None)
  return season.dl.follow(url,opener=Opener(),timeout=timeout,route=route)
 def test_actual_scan_then_strict_redirect_saves_a_real_durable_job_once(self):
  scanned=season.request(self.home,'123',1,2,follow=self.follow)
  self.assertEqual(scanned['qualities'],['1080p']);self.assertFalse(self.fixture.jobs())
  result=season.request(self.home,'123',1,2,'queue','1080p',follow=self.follow)
  self.assertTrue(result['queued']);self.assertEqual(len(self.fixture.jobs()),1)
  self.assertEqual(self.fixture.jobs()[0]['show_tmdb'],'123')
  self.fixture.dialog.select.assert_not_called()
  self.assertFalse(watch.active_request(self.home))
 def test_source_disappearing_in_selected_quality_has_no_queue_receipt(self):
  result=season.request(self.home,'123',1,2,'queue','4k',follow=self.follow)
  self.assertFalse(result['queued']);self.assertFalse(self.fixture.jobs())
  self.assertTrue(watch.canceled(self.home,{'tmdb':'123','season':1,'episode':2}))
 def test_empty_search_can_fall_back_without_an_interactive_picker(self):
  self.rows=[]
  result=season.request(self.home,'123',1,2,follow=self.follow)
  self.assertEqual(result['qualities'],[]);self.assertFalse(self.fixture.jobs())
 def test_malformed_sources_are_not_reported_as_usable(self):
  self.rows=['not a supported source list']
  self.assertEqual(season.request(self.home,'123',1,2,follow=self.follow),{})
 def test_no_picker_no_results_response_is_distinct_from_failed_http(self):
  empty=lambda url,**kwargs:url.replace(season.dl.PLUGIN_PREFIX,season.dl.ENGINE,1)
  self.assertEqual(season.request(self.home,'123',1,purpose='packs',follow=empty)['packs'],False)
  def failed(*a,**k):raise OSError('offline')
  with self.assertRaises(OSError):season.request(self.home,'123',1,2,follow=failed)
  self.assertFalse(watch.active_request(self.home))

class InterruptibleHTTP(unittest.TestCase):
 def setUp(self):
  self.started=threading.Event();self.release=threading.Event();self.cancel=threading.Event();owner=self
  class Slow(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    if self.path=='/body':
     self.send_response(200);self.send_header('Content-Length','100');self.send_header('Connection','close');self.end_headers()
    owner.started.set();owner.release.wait(4)
    if self.path!='/body':
     self.send_response(302);self.send_header('Location','/download?late=1');self.end_headers()
  self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Slow);self.server.daemon_threads=True
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def tearDown(self):
  self.release.set();self.server.shutdown();self.server.server_close()
 def check_canceled(self,path):
  timer=threading.Thread(target=lambda:(self.started.wait(2),self.cancel.set()),daemon=True);timer.start()
  routed=[];started=time.monotonic()
  with self.assertRaises(season.dl.Canceled):
   season.dl.follow('http://127.0.0.1:%d%s'%(self.server.server_address[1],path),timeout=3,
    cancel=self.cancel.is_set,engine=lambda:True,route=lambda url:routed.append(url) and False)
  self.assertLess(time.monotonic()-started,1.5)
  self.assertEqual(len(routed),1)  # a late /download redirect never reaches the queue
 def test_cancel_interrupts_headers_and_never_routes_a_late_download(self):self.check_canceled('/headers')
 def test_cancel_interrupts_response_body_even_with_connection_close(self):self.check_canceled('/body')
 def test_deadline_interrupts_a_stalled_request(self):
  started=time.monotonic()
  with self.assertRaises(TimeoutError):season.dl._interruptible_get('http://127.0.0.1:%d/headers'%self.server.server_address[1],.2,lambda:False)
  self.assertLess(time.monotonic()-started,1.5)

class AiredEpisodes(unittest.TestCase):
    """Owner (2026-11-12): Naruto Shippuden S1 (2007) said no aired episodes could be verified."""
    def test_undated_episodes_count_unless_the_season_is_only_future(self):
        import datetime
        from season_sources import aired
        today=datetime.date(2026,11,12)
        rows=lambda *dates:[{'episode':n,'firstaired':d,'filetype':'file'} for n,d in enumerate(dates,1)]
        self.assertEqual(aired(rows('','',''),today),[1,2,3])                       # no dates at all
        self.assertEqual(aired(rows('2007-02-15','',''),today),[1,2,3])             # some dated, aired
        self.assertEqual(aired(rows('2026-12-01','',''),today),[])                  # brand-new season
        self.assertEqual(aired(rows('','2026-12-01',''),today),[1])                 # undated before the next one
        self.assertEqual(aired(rows('2007-02-15','2027-01-01'),today),[1])          # future one left out
        self.assertEqual(aired([{'episode':1,'premiered':'2007-02-15'}],today),[1])

class PlanSeason(unittest.TestCase):
    def test_download_all_plans_even_when_the_show_could_not_be_registered(self):
        # Owner log 4e7b2fb2 (build 284): KeyError '31910' after Download All, nothing queued.
        with tempfile.TemporaryDirectory() as profile:
            watch.plan_season(profile,'31910','',1,[1,2,3],'1080p',now=5)
            show=watch.load(profile)['shows']['31910']
            self.assertEqual(sorted(show['planned']),['1:1','1:2','1:3'])
            watch.record_planned(profile,'31910',1,2,True)
            self.assertEqual(watch.load(profile)['shows']['31910']['planned']['1:2']['status'],'queued')
            watch.plan_season(profile,'31910','Naruto Shippuden',1,[4],'1080p',now=6)
            self.assertEqual(watch.load(profile)['shows']['31910']['title'],'Naruto Shippuden')

class ThreeLanes(unittest.TestCase):
    def test_lookups_run_three_at_a_time_each_in_its_lane(self):
        # Owner (2026-11-12): "fix the speed for shows" (one episode at a time, about 5.5 s each).
        import threading
        busy=[];peak=[0];seen={};lock=threading.Lock()
        def work(n,lane):
            with lock:busy.append(n);peak[0]=max(peak[0],len(busy));seen[n]=lane
            time.sleep(0.05)
            with lock:busy.remove(n)
        shown=[]
        season.lanes(list(range(1,10)),work,lambda d,c:shown.append(d),lambda:False,{'stop':False},3)
        self.assertEqual(sorted(seen),list(range(1,10)));self.assertEqual(peak[0],3)
        self.assertEqual(set(seen.values()),set(watch.LANES))
    def test_stop_takes_no_new_episode(self):
        done=[];halt={'stop':False}
        season.lanes(list(range(1,20)),lambda n,l:(done.append(n),time.sleep(0.05)),lambda d,c:None,lambda:len(done)>=3,halt,3)
        self.assertTrue(halt['stop']);self.assertLess(len(done),19)
    def test_season_jobs_back_in_episode_order(self):
        with tempfile.TemporaryDirectory() as profile:
            for n,h in ((3,'c'),(1,'a'),(2,'b')):
                debrid_drive.queue(profile,{'id':h*40,'name':'Naruto S01E0%d'%n},'episode','Naruto','1',str(n),show_tmdb='31910')
            debrid_drive.queue(profile,{'id':'d'*40,'name':'Other S01E01'},'episode','Other','1','1',show_tmdb='9')
            self.assertTrue(debrid_drive.order_season(profile,'31910','1'))
            self.assertEqual([(j['show_tmdb'],j['episode']) for j in debrid_drive.load(profile)['jobs']],
                             [('31910','1'),('31910','2'),('31910','3'),('9','1')])
            self.assertFalse(debrid_drive.order_season(profile,'31910','1'))

if __name__=='__main__':unittest.main()
