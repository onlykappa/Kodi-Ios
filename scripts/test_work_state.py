"""Build 193, Phase 2: one status model (work_state.py) that every page and the bell read, every 2 s. Each rule from
docs/plans/build-193-roadmap.md and each cause in docs/LOG-REVIEW-192.md that the model owns has a test here."""
import importlib.util,io,json,sys,tempfile,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(BOOT)]
import work_state as ws
import transfer_history as th
NOW=1_000_000.0;MB=1048576.0;GB=1024*MB

def conv(stage='Converting',progress=42,rate=4.8*MB,eta_s=360,updated=NOW-1,running=True,**extra):
 return {'jobs':{},'current':dict(title='Scary.Movie.2026.2160p.mkv',stage='Step 3 of 3 · '+stage,progress=progress,rate=rate,eta_s=eta_s,
                                   running=running,updated=updated,**extra)}

def job(name,status='waiting',repack=False,size=4.3*GB,**extra):
 return dict(source={'id':name,'name':name,'size':int(size)},status=status,repack=repack,**extra)

class Words(unittest.TestCase):
 def test_copy_stages_are_clear_and_percent_remains_confirmed(self):
  current={'name':'Movie','stage':'copying','sent':2,'total':10,'rate':0,'updated':NOW-1}
  source={'jobs':[{'title':'Movie','status':'copying'}],'current':current}
  for phase,text in [('reading','Reading download'),('uploading','Uploading to Google Drive'),('paused_playback','Paused for playback')]:
   current['phase']=phase
   state=ws.build({'debrid':source,'slow':'airplay'},NOW)
   self.assertIn(text,state['jobs'][0]['line']);self.assertEqual(state['jobs'][0]['pct'],20)
  current['updated']=NOW-130;current['phase']='reading'
  self.assertIn('Waiting for download',ws.build({'debrid':source},NOW)['jobs'][0]['line'])
  current['phase']='paused_playback'
  self.assertEqual(ws.build({'debrid':source,'slow':'video'},NOW)['jobs'][0]['line'],'Paused for playback')
 def test_network_retry_survives_playback_status(self):
  source={'jobs':[{'title':'Movie','status':'copying','tries':1,'retry_at':NOW+120}],
          'current':{'name':'Movie','sent':2,'total':10,'updated':NOW-1,'phase':'uploading'}}
  for slow in ('video','buffering'):
   row=ws.build({'debrid':source,'slow':slow},NOW)['jobs'][0]
   self.assertEqual(row['state'],ws.NETWORK)
   self.assertIn('trying again in 2 min',row['line'])
 def test_resuming_after_playback_does_not_count_the_hold_as_network_silence(self):
  source={'jobs':[{'title':'Movie','status':'copying'}],
          'current':{'name':'Movie','stage':'copying','sent':2,'total':10,'updated':NOW-600,
                     'phase':'reading','phase_at':NOW-1,'rate':0}}
  row=ws.build({'debrid':source},NOW)['jobs'][0]
  self.assertEqual(row['state'],ws.RUNNING);self.assertEqual(row['pct'],20)
  self.assertIn('Reading download',row['line'])
  row=ws.build({'debrid':source},NOW+130)['jobs'][0]
  self.assertEqual(row['state'],ws.NETWORK);self.assertIn('Waiting for download',row['line'])
 def test_running(self):
  s=ws.build({'prep':conv()},NOW);j=s['jobs'][0]
  self.assertEqual((s['mode'],j['state'],j['kind']),('running','running','conv'))
  self.assertEqual(j['line'],'Converting · 4.8 MB/s · 6 min left');self.assertEqual(j['title'],'Scary Movie (2026)')
  self.assertEqual(s['bell'],{'state':'running','pct':42,'tint':ws.PURPLE,'count':1,'needs':0})
 def test_repack_says_faster_start(self):
  s=ws.build({'prep':conv('Making it start faster',kind='repack')},NOW)
  self.assertEqual(s['jobs'][0]['line'],'Making it start faster · 4.8 MB/s · 6 min left')
 def test_slowed_only_with_the_services_reason(self):
  s=ws.build({'prep':conv(rate=1.1*MB,eta_s=1500),'slow':'airplay'},NOW);j=s['jobs'][0]
  self.assertEqual((s['mode'],j['state']),('slowed','slowed'))
  self.assertEqual(j['line'],'Slower while AirPlay plays · 1.1 MB/s · 25 min left')
  self.assertEqual(s['bell']['tint'],ws.GREY)                     # grey ring while slowed
  self.assertEqual(ws.build({'prep':conv(),'slow':'video'},NOW)['jobs'][0]['line'],'Slower while a video plays · 4.8 MB/s · 6 min left')
  # No reason from the service: never "slower" or "paused by a video", whatever the stage text says.
  s=ws.build({'prep':conv('Paused while a video plays')},NOW)
  self.assertEqual(s['jobs'][0]['line'],'Converting · 4.8 MB/s · 6 min left')
  self.assertNotIn('video plays',json.dumps(s))
 def test_paused_by_you(self):
  s=ws.build({'prep':conv('Paused by you',paused=True,rate=0),'paused':{'conv':True}},NOW)
  self.assertEqual((s['mode'],s['jobs'][0]['line']),('paused_by_you','Paused by you'))
  self.assertEqual(s['bell']['state'],'paused_by_you');self.assertEqual(ws.bell_properties(s)['Notices.Active'],'')
  # Paused while nothing converts: the next one waits for the owner.
  s=ws.build({'prep':{'jobs':{'a':job('Fall.2.mkv')}},'paused':{'conv':True}},NOW)
  self.assertEqual(s['mode'],'paused_by_you');self.assertTrue(s['next'][0]['paused'])
 def test_needs_you_beats_everything_and_is_the_only_red(self):
  ws.need('drive_signin');flags=ws.flags();ws.need('drive_signin',False)
  s=ws.build({'prep':conv(),**flags},NOW)
  self.assertEqual(s['mode'],'needs_you');self.assertEqual(s['needs'][0]['title'],'Sign in to Google Drive again')
  self.assertEqual(s['needs'][0]['button'],'Sign in');self.assertEqual(s['bell']['needs'],1)
  self.assertEqual(ws.bell_properties(s)['Notices.Needs'],'1')
  self.assertEqual(ws.bell_properties(ws.build({'prep':conv()},NOW))['Notices.Needs'],'')   # never red otherwise
  self.assertEqual(ws.flags()['needs'],[])
 def test_waiting_for_the_network(self):
  debrid={'jobs':[{'hash':'h','title':'Inception (2010)','status':'copying','tries':2,'retry_at':NOW+120}],'current':{}}
  s=ws.build({'debrid':debrid},NOW)
  self.assertEqual((s['mode'],s['jobs'][0]['line']),('waiting_network','Waiting for the network · trying again in 2 min'))
  ws.network('drive',NOW+60,'Google Drive is busy');flags=ws.flags();ws.network('drive')
  s=ws.build(flags,NOW);self.assertEqual(s['mode'],'waiting_network');self.assertIn('Google Drive is busy · trying again in 1 min',s['headline'])
 def test_copy_with_no_progress_is_not_moving(self):
  """Build-192 log 13:23:56-13:28:57: one 32 MB piece hung; every page kept the last speed."""
  live={'jobs':[{'hash':'h','title':'Inception (2010)','status':'copying'}],
        'current':{'name':'Inception.mkv','stage':'copying','sent':2.7*GB,'total':7.1*GB,'rate':2.4*MB,'eta_s':540,'updated':NOW-5}}
  s=ws.build({'debrid':live},NOW);self.assertEqual(s['jobs'][0]['line'],'AllDebrid → Drive · 2.4 MB/s · 9 min left')
  self.assertEqual(s['bell']['tint'],ws.BLUE)
  live['current']['updated']=NOW-130
  s=ws.build({'debrid':live},NOW);j=s['jobs'][0]
  self.assertEqual((j['state'],j['line']),('waiting_network','Waiting for Google Drive · no answer for 2 min'))
  self.assertEqual(s['running'],0)

class Build192Causes(unittest.TestCase):
 def test_a_stopped_job_is_not_running(self):
  """Cause 4: Inception stopped at 13:11:00 and kept "Paused while a video plays" with running=False."""
  prep=conv('Paused while a video plays',running=False,updated=NOW-36);prep['jobs']={'b':job('Lanterns.S01E01.mkv',repack=True)}
  s=ws.build({'prep':prep},NOW)
  self.assertEqual(s['jobs'],[]);self.assertEqual(s['mode'],'queued');self.assertEqual(s['headline'],'1 up next')
  self.assertEqual(s['next'][0]['what'],'faster start')
 def test_old_running_record_from_a_previous_launch(self):
  """Cause 6: at 12:57:36 the queue's current said running, 228 s old, from the previous launch."""
  self.assertEqual(ws.build({'prep':conv(updated=NOW-228)},NOW)['jobs'],[])
  # A heartbeat (preparation_runtime) keeps a quiet conversion alive (a 32 MB piece going up).
  s=ws.build({'prep':conv(updated=NOW-40),'runtime':{'phase':'Converting','known':True,'updated':NOW-1}},NOW)
  self.assertEqual(s['jobs'][0]['state'],'running')
 def test_library_check_is_its_own_job(self):
  prep={'jobs':{},'current':{'title':'Movies and shows','stage':'Checking downloaded videos','running':True,'updated':NOW-1,'progress':0}}
  j=ws.build({'prep':prep},NOW)['jobs'][0];self.assertEqual((j['kind'],j['line']),('check','Checking Google Drive'))
 def test_nothing_is_moving_only_when_nothing_runs_or_waits(self):
  self.assertEqual(ws.build({},NOW)['headline'],'Nothing is moving right now')
  for inp in ({'prep':conv()},{'prep':{'jobs':{'a':job('a.mkv')}}},{'paused':{'conv':True},'prep':{'jobs':{'a':job('a.mkv')}}}):
   self.assertNotIn('Nothing is moving',ws.build(inp,NOW)['headline'])
 def test_one_up_next_list(self):
  """Cause 12: Notifications counted kept and blocked jobs; Library status did not."""
  prep={'jobs':{'a':job('Fall.2.mkv',repack=True,size=16.9*GB),'b':job('Scary.Movie.2026.mkv'),'c':job('Kept.mkv',kept=True),
                'd':job('Blocked.mkv',blocked=True),'e':job('Done.mkv',status='done')}}
  s=ws.build({'prep':prep},NOW)
  self.assertEqual([(n['title'],n['what']) for n in s['next']],[('Scary Movie (2026)','convert'),('Fall 2','faster start')])

class InstantCancel(unittest.TestCase):
 """ISSUE-208 (owner: "deleting the download queue is also slow as hell, it needs to be instant")."""
 def test_a_cancel_shows_at_once_before_the_copier_applies_it(self):
  import debrid_drive,transfer_control
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.save(p,{'jobs':[{'hash':'a'*40,'name':'A','title':'Heat','kind':'movie','status':'copying','files':[],'added':1},
                                {'hash':'b'*40,'name':'B','title':'Fall','kind':'movie','status':'new','files':[],'added':2}],
                        'current':{'stage':'copying','sent':1,'total':10,'updated':time.time(),'name':'A'}})
   self.assertEqual(ws.current(p)['copies_waiting'],2)
   transfer_control.cancel_copy(p,'A'*40)
   titles=[j['title'] for j in ws.current(p)['jobs']+ws.current(p)['drive_next']]
   self.assertNotIn('Heat',titles)
   transfer_control.cancel_copy(p,'b'*40)
   now=ws.current(p)
   self.assertFalse([j for j in now['jobs'] if j.get('kind')=='copy']);self.assertFalse(now['drive_next'])
   self.assertEqual(now['copies_waiting'],0)
   self.assertEqual([j['status'] for j in debrid_drive.load(p)['jobs']],['copying','new'])   # the copier still applies it
 def test_the_copier_wakes_on_a_cancel_and_forgets_requests_with_nothing_left(self):
  src=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('while not nap(delay):',src);self.assertIn('if transfer_control.cancelled_copies(profile):return False',src)
  import debrid_drive
  forgot=[]
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.save(p,{'jobs':[{'hash':'a'*40,'name':'A','title':'Heat','kind':'movie','status':'done','files':[],'added':1}]})
   debrid_drive.step(p,None,None,cancelled=lambda:{'a'*40,'c'*40},forget=forgot.append)
  self.assertEqual(sorted(forgot),['a'*40,'c'*40])

class Freshness(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_older_than_six_seconds_is_never_running(self):
  ws.save(self.p,ws.build({'prep':conv()},NOW))
  self.assertEqual(ws.load(self.p,NOW+2)['jobs'][0]['state'],'running')
  old=ws.load(self.p,NOW+ws.STALE+1)
  self.assertEqual((old['mode'],old['jobs'][0]['state'],old['jobs'][0]['line'],old['running']),('stale','stale','Updating…',0))
  self.assertEqual(ws.bell_properties(old)['Notices.Active'],'')
  self.assertIsNone(ws.load(self.p+'/nowhere',NOW))
 def test_publish_every_two_seconds_and_sets_the_bell(self):
  props={};ticks=[0]
  def wait(s):
   self.assertEqual(s,2);ticks[0]+=1;return ticks[0]>3
  ws.publish(self.p,lambda:{'prep':conv(updated=time.time())},wait,set_property=props.__setitem__)
  self.assertEqual(ws.load(self.p)['mode'],'running')
  self.assertEqual({k:props[k] for k in ('Notices.Active','Notices.Pct','Notices.Count')},{'Notices.Active':'true','Notices.Pct':'42','Notices.Count':'1'})

class Pages(unittest.TestCase):
 """Every page reads the model: Library status and the Queue (align), Notifications (model_cards), Transfers
 (page_state), the bell (bell_properties / notices.badge)."""
 def test_library_status_agrees(self):
  prep=conv('Paused while a video plays');s=ws.build({'prep':prep,'slow':'airplay'},NOW)
  aligned=ws.align(prep,s)['current']
  self.assertTrue(aligned['running']);self.assertTrue(aligned['stage'].startswith('Step 3 of 3 · Slower while AirPlay plays'))
  self.assertFalse(ws.align(prep,ws.build({},NOW))['current']['running'])      # the model has nothing moving
  import prepare_downloads
  state=dict(ws.align(prep,s),library={'items':[{'id':'x','name':'Scary.Movie.2026.2160p.mkv','folder':'Movies','size':1,'state':'todo'}]},
             jobs={'k':job('Scary.Movie.2026.2160p.mkv',status='paused')})
  state['jobs']['k']['source']['id']='x'
  row=prepare_downloads.library_view(state,now=lambda:NOW)['rows']['preparing'][0]
  self.assertIn('Slower while AirPlay plays',row['sub'])
  for name in ('library_status.py',):self.assertIn('work_state.align(prepare_downloads.snapshot(profile),model)',(BOOT/name).read_text())
  self.assertIn('work_state.align(prepare_downloads.snapshot(profile), model)',(LIB/'tool_windows.py').read_text())
 def test_notifications_cards(self):
  spec=importlib.util.spec_from_file_location('notifications_ws',BOOT/'notifications.py');n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
  card,up=n.model_cards(ws.build({'prep':conv(),'slow':'video'},NOW),'id1')
  self.assertEqual((card['line'],card['progress'],card['running'],card['id']),('Slower while a video plays · 4.8 MB/s · 6 min left',42,True,'id1'))
  card,_=n.model_cards(ws.build({'prep':{'jobs':{'a':job('Fall.2.mkv')}}},NOW))
  self.assertEqual((card['title'],card['line'],card['running']),('Fall 2','Up next · #1',False))
  self.assertEqual(n.model_cards(ws.build({},NOW)),({},''))
 def test_transfers_never_says_nothing_while_something_waits(self):
  spec=importlib.util.spec_from_file_location('transfers_ws',BOOT/'transfers.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
  history={}
  for i in range(0,20,2):th.track(history,NOW-20+i,{'conv':{'title':'Scary Movie (2026)','rate':4*MB,'pct':40}})
  # The model has it moving: shown.
  props,_,kind,_=t.page_state(history,NOW,'conv',[],ws.build({'prep':conv()},NOW));self.assertEqual(kind,'conv')
  # Stopped (the model has nothing): not shown as running, even though the history record is 2 s old.
  props,_,kind,_=t.page_state(history,NOW,'conv',[],ws.build({'prep':{'jobs':{'a':job('Fall.2.mkv')}}},NOW))
  self.assertIsNone(kind);self.assertEqual(props['empty.title'],'1 up next')
  props,_,kind,_=t.page_state({},NOW,'conv',[],ws.build({},NOW));self.assertEqual(props['empty.title'],'Nothing is moving right now')
  # Paused by you, not yet in the history: shown with the model's words, no "Starting…".
  props,_,kind,_=t.page_state({},NOW,'conv',[],ws.build({'prep':conv('Paused by you',paused=True,rate=0)},NOW))
  self.assertEqual((kind,props['now']),('conv','Paused by you'));self.assertIn('Paused by you',props['line'])
  self.assertIn("P('empty.title')",(LIB/'transfers_page.py').read_text())
 def test_bell_reads_the_model(self):
  src=(LIB/'notices.py').read_text();self.assertIn('work_state.load(profile,now)',src)
  self.assertNotIn("window.setProperty('Notices.Active',now[1])",src)
  svc=(BOOT/'service.py').read_text()
  self.assertIn("threading.Thread(target=work_state.publish,args=(profile,work_inputs,monitor.waitForAbort)",svc)
  self.assertIn("work_state.need('drive_signin')",svc);self.assertIn("work_state.need('alldebrid_key',not token and debrid_drive.active(profile))",svc)

class Workers(unittest.TestCase):
 def test_failed_check_clears_its_card(self):
  """Cause 6/12-minute "Checking downloaded videos" while the sign-in was refused (12:57-13:09)."""
  import prepare_downloads
  class Q:
   scanning=threading.Lock();lock=threading.Lock();state={'current':{'title':'Movies and shows','running':True}};saved=0
   def _scan(self,*a):raise RuntimeError('Sign-in refused')
   def commit(self):Q.saved+=1
  q=Q()
  with self.assertRaises(RuntimeError):prepare_downloads.Queue.scan(q)
  self.assertNotIn('current',q.state);self.assertGreater(Q.saved,0)
  q.state={'current':{'title':'Inception','running':True}}
  with self.assertRaises(RuntimeError):prepare_downloads.Queue.scan(q)
  self.assertIn('current',q.state)          # a conversion's card is not the check's to clear
 def test_alldebrid_copy_progress_has_time_and_resets_tries(self):
  import debrid_drive,driveupload
  sys.path.insert(0,str(Path(__file__).resolve().parent))
  from test_debrid_drive import FakeAPI,FakeDrive,H
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.queue(p,{'id':H},'movie','Fall (2022)')
   class Flaky(FakeDrive):
    # ISSUE-188: a failed copy is tried again RETRIES_IN_RUN times in the same turn; fail once more than that.
    def __init__(self):super().__init__();self.fail=debrid_drive.RETRIES_IN_RUN+1
    def call(self,method,url,body=None,headers=None):
     if self.fail and method=='PUT':self.fail-=1;raise ConnectionError('reset')
     return super().call(method,url,body,headers)
   drive=Flaky();clock=[NOW]
   step=lambda:debrid_drive.step(p,FakeAPI(),drive,open_url=lambda u,o:io.BytesIO(b'abc'[o:]),clock=lambda:clock[0])
   step()                                     # add: copying
   self.assertEqual(step(),15)                # the piece fails every try this turn: network trouble, again in 15 s (ISSUE-198)
   j=debrid_drive.load(p)['jobs'][0];self.assertEqual((j.get('tries',0),j['net_tries'],j['retry_at']),(0,1,NOW+15))
   self.assertEqual(ws.build({'debrid':debrid_drive.load(p)},NOW)['jobs'][0]['line'],'Waiting for the network · trying again in a moment')
   seen=[]
   orig=debrid_drive.save
   debrid_drive.save=lambda profile,state,enqueue=False:(seen.append(json.loads(json.dumps(state.get('current') or {}))),orig(profile,state,enqueue))
   try:step()
   finally:debrid_drive.save=orig
   self.assertTrue(any(c.get('updated')==NOW for c in seen))
   j=debrid_drive.load(p)['jobs'][0];self.assertEqual(j['status'],'done');self.assertEqual(j.get('tries',0),0)

class FreshLane(unittest.TestCase):
 def test_the_card_shows_the_lane_that_moved_last(self):
  # Owner screenshot (build 325): "Waiting for Google Drive · no answer for 23 min" while other lanes copied.
  job={'hash':'a'*40,'title':'Naruto','kind':'season','season':'1','status':'copying','files':[{'path':'S/Naruto.S01E06.mkv'},{'path':'S/Naruto.S01E07.mkv'}]}
  stale={'stage':'copying','sent':0,'total':100,'updated':NOW-23*60,'file':'Naruto.S01E06.mkv','count':2,'index':1}
  live={'stage':'copying','sent':50,'total':100,'updated':NOW-5,'file':'Naruto.S01E07.mkv','count':2,'index':2}
  card=ws._copy({'jobs':[job],'current':stale,'current_also':live},NOW)
  self.assertEqual(card['pct'],50);self.assertNotIn('wait',card)

class FourLanes(unittest.TestCase):
 def test_every_copy_has_its_card_and_up_next_starts_at_one(self):
  # Owner screenshot (build 329): four copies ran, Library status showed one ("1 working"); Up next read E3, E1, E4.
  import debrid_drive,notices,tempfile,json,os,time
  now=time.time()
  jobs=[{'hash':'h%d'%n,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':str(n),'status':'copying' if n<=4 else 'new','files':[]}
        for n in (3,1,4,2,5,7,6)]
  lanes={str(i):{'name':'Naruto Shippuden','file':'Naruto Shippuden S01E%02d - x.mkv'%n,'count':1,'sent':10,'total':100,'stage':'copying',
                 'updated':now-3,'job':'h%d:1:%d'%(n,n),'rate':1000} for i,n in enumerate((1,2,3,4))}
  self.assertEqual([j['episode'] for j in debrid_drive.in_line(jobs)],['1','2','3','4','5','6','7'])
  with tempfile.TemporaryDirectory() as p:
   d=os.path.join(p,'addon_data','service.kodi.ios.bootstrap');os.makedirs(d)
   json.dump({'jobs':jobs,'lanes':lanes},open(os.path.join(d,'debrid-drive.json'),'w'))
   self.assertEqual(len(debrid_drive.uploads(p,now=now)),4)
   cards=[u['title'] for u in notices.uploads(p) if u['source']=='debrid']
   self.assertEqual(cards,['Naruto Shippuden · S1 E1','Naruto Shippuden · S1 E2','Naruto Shippuden · S1 E3','Naruto Shippuden · S1 E4'])
   self.assertEqual(debrid_drive.uploads(p,now=now+3600),[])                      # quiet lanes leave
  waiting=[c['title'] for c in ws._copy_next({'jobs':jobs,'lanes':lanes})]
  self.assertEqual(waiting,['Naruto Shippuden · S1 E5','Naruto Shippuden · S1 E6','Naruto Shippuden · S1 E7'])
 def test_the_status_model_has_a_card_per_lane(self):
  jobs=[{'hash':'h%d'%n,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':str(n),'status':'copying','files':[]} for n in (1,2,3,4,5)]
  lanes={str(i):{'name':'Naruto Shippuden','file':'Naruto Shippuden S01E%02d.mkv'%n,'count':1,'sent':10,'total':100,'stage':'copying',
                 'updated':NOW-2,'job':'h%d:1:%d'%(n,n),'rate':1000,'rate_own':1000} for i,n in enumerate((1,2,3,4))}
  snap=ws.build({'debrid':{'jobs':jobs,'lanes':lanes}},NOW)
  copies=[j for j in snap['jobs'] if j['kind']=='copy']
  self.assertEqual([j['title'] for j in copies],['Naruto Shippuden · S1 E%d'%n for n in (1,2,3,4)])
  self.assertEqual(len({j['id'] for j in copies}),4)
  one=ws.build({'debrid':{'jobs':jobs,'lanes':{'0':lanes['0']},'current':lanes['0']}},NOW)   # one lane: one card, as before
  self.assertEqual(len([j for j in one['jobs'] if j['kind']=='copy']),1)
 def test_library_status_writes_only_what_changed(self):
  src=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/library_status.py').read_text()
  self.assertIn("if seen.get(key)==value:return",src);self.assertIn("self.bar(library_page.DOWN_BARS+n,r.get('pct') or 0)",src)

class WifiOnly(unittest.TestCase):
 def test_copies_wait_for_wifi_and_the_card_says_so(self):
  # E15: Copy downloads to Google Drive only on Wi-Fi; on cellular the copies wait.
  import debrid_drive,tempfile
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.queue(p,{'id':'a'*40,'name':'Fall'},'movie','Fall (2022)')
   debrid_drive.hold(p,'wifi')
   snap=ws.build({'debrid':debrid_drive.load(p)},NOW)
   copy=[j for j in snap['jobs'] if j['kind']=='copy'][0]
   self.assertIn('Waiting for Wi-Fi',copy['line']+copy.get('why',''))
   debrid_drive.hold(p,'')
   self.assertNotIn('hold',debrid_drive.load(p))
   self.assertEqual(len(debrid_drive.load(p)['jobs']),1)               # the queue is untouched
  root=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
  self.assertIn('id="copy_wifi_only"',(root/'resources/settings.xml').read_text())
  self.assertIn("and not wifi_only_hold(),on_done=done,",(root/'service.py').read_text())

class TimeLeft(unittest.TestCase):
 def test_every_copy_left_counts_over_all_lanes(self):
  # E17: "about 16 min to go" with 31 episodes waiting; "84 h" from a starved conversion rate.
  M=1024**2
  jobs=[{'hash':'h%d'%n,'title':'Naruto','kind':'episode','season':'1','episode':str(n),'status':'copying' if n<=4 else 'new',
         'files':[{'path':'Naruto S01E%02d.mkv'%n,'drive_name':'Naruto S01E%02d.mkv'%n,'size':280*M,'done':False}] if n<=8 else []}
        for n in range(1,32)]
  lanes={str(i):{'name':'Naruto','file':'Naruto S01E%02d.mkv'%n,'count':1,'sent':140*M,'total':280*M,'stage':'copying',
                 'updated':NOW-2,'job':'h%d:1:%d'%(n,n),'rate':90*1024,'rate_own':90*1024} for i,n in enumerate((1,2,3,4))}
  debrid={'jobs':jobs,'lanes':lanes}
  left=ws.copy_bytes_left(debrid)
  self.assertAlmostEqual(left/M,4*140+4*280+23*280,delta=1)                  # unlisted jobs count as the average file
  snap=ws.build({'debrid':debrid},NOW);snap['copy_left']=left
  text=ws.remaining_text(snap)
  self.assertTrue(text.startswith('about 6 h'),text)                    # ~8.1 GB at 0.35 MB/s: about 6 h 25 min, not 16 min
  self.assertIsNone(ws.copy_bytes_left({'jobs':[{'status':'new','files':[]}]}))

class SeasonQueue(unittest.TestCase):
 """Owner (build 205): "i went to download a entire season and it seems only 1 thing is downloading? it should show a
 que of the episodes". The log: one AllDebrid job for the whole Lanterns season pack (8.4 GB)."""
 def debrid(self):
  files=[{'path':'Lanterns.S01E%02d.1080p.mkv'%n,'size':1,'done':n<3} for n in range(1,11)]
  return {'jobs':[{'status':'copying','title':'Lanterns','name':'Lanterns.S01','files':files,'hash':'h'},
                  {'status':'new','title':'Dune (2021)','name':'Dune','files':[],'hash':'k'}],
          'current':{'name':'Lanterns','stage':'copying','sent':5,'total':10,'updated':100.0,'file':'Lanterns.S01E03.1080p.mkv','index':3,'count':10}}
 def test_the_copy_names_its_episode_and_counts_the_season(self):
  model=ws.build({'debrid':self.debrid()},100.0)
  copy=[j for j in model['jobs'] if j['kind']=='copy'][0]
  self.assertEqual(copy['title'],'Lanterns · S01E03');self.assertTrue(copy['line'].startswith('AllDebrid → Drive · 3 of 10'))
 def test_the_rest_of_the_season_waits_in_order_then_the_other_jobs(self):
  model=ws.build({'debrid':self.debrid()},100.0)
  titles=[j['title'] for j in model['drive_next']]
  self.assertEqual(titles[:2],['Lanterns · S01E04','Lanterns · S01E05']);self.assertEqual(titles[6],'Lanterns · S01E10')
  self.assertEqual(titles[-1],'Dune (2021)');self.assertEqual(len(titles),8)
  self.assertEqual(model['running'],1);self.assertIn('8 up next',model['headline'])
  import library_tools
  q=library_tools.queue_view({'rows':{},'model':model})
  self.assertEqual([r['title'] for r in q['drive']][:3],['Lanterns · S01E03','Lanterns · S01E04','Lanterns · S01E05'])
 def test_episode_labels(self):
  self.assertEqual(ws.episode_label('Show.S1E7.mkv'),'S01E07');self.assertEqual(ws.episode_label('folder/show 2x05.mp4'),'S02E05')
 def test_debrid_drive_records_which_file(self):
  text=(LIB/'debrid_drive.py').read_text()
  self.assertIn("'file': name, 'index': owner['files'].index(entry) + 1, 'count': len(owner['files'])",text)


class NoTorrentIds(unittest.TestCase):
 # Owner screenshot (2026-11-12): queued copies read '45e2c1e044af006c...'.
 H='45e2c1e044af006c8fbf625483a18e1c2b3d4e5f'
 def title(self,job,names=None):
  ws._NAMES.clear();ws._NAMES.update(names or {});return ws._download_title(job)
 def test_a_real_name_stays(self):
  self.assertEqual(self.title({'title':'Phony','season':1,'episode':2}),'Phony · S1 E2')
 def test_an_id_becomes_the_file_the_show_or_download(self):
  self.assertNotIn(self.H[:12],self.title({'name':self.H,'files':[{'path':'Phony/Phony.S01E01.1080p.mkv'}]}))
  self.assertEqual(self.title({'name':self.H,'title':self.H,'show_tmdb':'77','season':1,'episode':3},{'77':'Phony'}),'Phony · S1 E3')
  self.assertEqual(self.title({'name':self.H,'title':self.H,'season':2,'episode':1}),'Download · S2 E1')
 def test_names_come_from_the_cached_show_details(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)/'addon_data/service.kodi.ios.bootstrap';d.mkdir(parents=True)
   (d/'drive-library-art.json').write_text(json.dumps({'show:77':{'name':'Phony'},'tv:phony:':{'tmdb_id':'77'}}))
   self.assertEqual(ws.show_names(t),{'77':'Phony'})
  self.assertEqual(ws.show_names('/nonexistent'),{})

if __name__=='__main__':unittest.main()
