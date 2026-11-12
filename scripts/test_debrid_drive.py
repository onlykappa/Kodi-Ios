"""Owner (build 160): "a movie im downloading goes onto my phone still … if i do a large movie it wont ever download";
chose AllDebrid straight to Drive. alldebrid (client, pick), driveupload.upload_stream, debrid_drive (queue, step),
and the wiring in download.py, service.py and notices.py."""
import io,json,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import alldebrid,debrid_drive,driveupload,notices
H='a'*40

class Client(unittest.TestCase):
 def api(self,answers):
  self.calls=[]
  def request(method,url,data,headers):
   self.calls.append((method,url,data,headers));return json.dumps(answers.pop(0)).encode()
  return alldebrid.AllDebrid('tok',request)
 def test_add_status_files_unlock(self):
  api=self.api([{'status':'success','data':{'magnets':[{'id':7,'ready':False}]}},
                {'status':'success','data':{'magnets':{'statusCode':1,'size':100,'downloaded':40,'status':'Downloading'}}},
                {'status':'success','data':{'magnets':[{'files':[{'n':'Fall.2022','e':[{'n':'Fall.2022.2160p.mkv','s':9,'l':'L1'},{'n':'sample.mkv','s':1,'l':'L2'}]}]}]}},
                {'status':'success','data':{'link':'https://x.debrid.it/dl/f.mkv','filename':'Fall.2022.2160p.mkv','filesize':9}}])
  self.assertEqual(api.add(H),('7',False))
  self.assertEqual(self.calls[0][3]['Authorization'],'Bearer tok');self.assertIn('agent=KodiIOS',self.calls[0][1])
  self.assertEqual(self.calls[0][2],{'magnets[]':[H]})
  self.assertEqual(api.status('7'),(1,0.4,'Downloading'))
  self.assertEqual(api.files('7'),[('Fall.2022/Fall.2022.2160p.mkv',9,'L1'),('Fall.2022/sample.mkv',1,'L2')])
  self.assertEqual(api.unlock('L1'),('https://x.debrid.it/dl/f.mkv','Fall.2022.2160p.mkv',9))
 def test_errors_in_plain_words(self):
  api=self.api([{'status':'error','error':{'code':'AUTH_BAD_APIKEY','message':'bad'}}])
  with self.assertRaises(alldebrid.Problem) as c:api.add(H)
  self.assertIn('Umbrella › Accounts',str(c.exception))
  with self.assertRaises(alldebrid.Problem):alldebrid.AllDebrid('')
 def test_token_from_umbrella_settings(self):
  self.assertEqual(alldebrid.token_from_settings('<settings><setting id="alldebridtoken">abc123</setting></settings>'),'abc123')
  self.assertEqual(alldebrid.token_from_settings('<setting id="alldebridtoken" value="xyz" />'),'xyz')
  self.assertEqual(alldebrid.token_from_settings(''),'')
 def test_pick(self):
  files=[('F/Movie.2160p.mkv',9,'a'),('F/Sample/sample.mkv',1,'b'),('F/extras.mkv',5,'c'),('F/info.nfo',1,'d')]
  self.assertEqual([f[2] for f in alldebrid.pick(files,'movie')],['a'])
  pack=[('S/Show.S01E02.mkv',2,'e2'),('S/Show.S01E01.mkv',2,'e1'),('S/Show.S01E03.mkv',2,'e3')]
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'episode','1','2')],['e2'])
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'season','1')],['e1','e2','e3'])
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'season','1',episodes=[1,3])],['e1','e3'])

class FakeDrive(driveupload.Drive):
 """Drive's resumable upload: keeps what it got; can lose the last chunk once."""
 def __init__(self,lose_after=None):
  super().__init__(lambda:'t',None);self.data=b'';self.lose_after=lose_after;self.puts=0;self.folders_made=[]
 def call(self,method,url,body=None,headers=None):
  if method=='POST':return 200,{'Location':'https://upload/session'},b''
  cr=headers['Content-Range']
  if cr.startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(len(self.data)-1)} if self.data else {}),b''
  a,b=cr[6:].split('/')[0].split('-');a=int(a);total=int(cr.split('/')[1])
  self.puts+=1
  if self.lose_after and self.puts==self.lose_after:return 308,{'Range':'bytes=0-%d'%(a-1)} if a else {},b''   # dropped
  self.data=self.data[:a]+body
  if len(self.data)==total:return 200,{},json.dumps({'id':'drive-1','size':str(total)}).encode()
  return 308,{'Range':'bytes=0-%d'%(len(self.data)-1)},b''
 def folder(self,parts):self.folders_made.append(parts);return 'folder-id'

class Stream(unittest.TestCase):
 def test_chunk_policy_shrinks_aligns_and_recovers_cautiously(self):
  policy=driveupload.StreamChunks(8*1024*1024)
  policy.observe(8*1024*1024,1,12);self.assertEqual(policy.current,8*1024*1024)   # 12 s: kept (ISSUE-164)
  policy.observe(8*1024*1024,1,27)          # the owner's 0.3 MB/s: about ten seconds' worth, 256 KiB aligned
  self.assertEqual(policy.current,2816*1024)
  for _ in range(2):policy.observe(policy.current,.5,1)
  self.assertEqual(policy.current,2816*1024)
  policy.observe(policy.current,.5,1);self.assertEqual(policy.current,5632*1024)
  policy.observe(policy.current,120,1);self.assertEqual(policy.current,1024*1024)
 def test_activity_does_not_claim_unconfirmed_download_bytes(self):
  import threading
  thread=threading.get_ident();events=[];drive=FakeDrive()
  def activity(phase,done,total):
   self.assertEqual(threading.get_ident(),thread)
   self.assertLessEqual(done,len(drive.data));events.append(phase)
  drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,activity=activity)
  self.assertIn('reading',events);self.assertIn('uploading',events)
 def setUp(self):
  self.old=driveupload.CHUNK;driveupload.CHUNK=256*1024
  self.blob=bytes(range(256))*4000   # ~1 MB
  self.opened=[]
 def tearDown(self):driveupload.CHUNK=self.old
 def open_at(self,offset):self.opened.append(offset);return io.BytesIO(self.blob[offset:])
 def test_copies_without_a_local_file_and_resumes_from_drive(self):
  drive=FakeDrive(lose_after=2);session={}
  result=drive.upload_stream(self.open_at,len(self.blob),'Fall.mkv','p',session,lambda:None)
  self.assertEqual(drive.data,self.blob);self.assertEqual(result['id'],'drive-1')
  self.assertEqual(self.opened,[0,256*1024])     # Drive dropped the 2nd chunk: read again from where it got to
 def test_a_restart_carries_on(self):
  drive=FakeDrive();drive.data=self.blob[:512*1024];session={'url':'https://upload/session','size':len(self.blob)}
  drive.upload_stream(self.open_at,len(self.blob),'Fall.mkv','p',session,lambda:None)
  self.assertEqual(self.opened,[512*1024]);self.assertEqual(drive.data,self.blob)
 def test_stop_when_asked(self):
  with self.assertRaises(driveupload.Stop):FakeDrive().upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,keep_going=lambda:False)
 def test_confirmed_progress_precedes_throttle_and_completion_does_not_wait(self):
  import slowdown
  drive=FakeDrive();seen=[];calls=[]
  class Gate:
   def after(inner,seconds,nbytes=0,download=False):
    calls.append(len(drive.data))
    self.assertEqual(seen[-1],len(drive.data))
    self.assertLess(len(drive.data),len(self.blob))
  with patch.object(slowdown,'Gate',side_effect=[type('Reader',(),{'after':lambda *a,**k:None})(),Gate()]):
   drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,progress=lambda sent,total:seen.append(sent))
  self.assertEqual(seen[-1],len(self.blob));self.assertEqual(len(calls),drive.puts-1)
 def test_large_stream_reports_eight_megabyte_checkpoints(self):
  driveupload.CHUNK=32*1024*1024;self.blob=b'z'*(17*1024*1024);seen=[];drive=FakeDrive()
  drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,progress=lambda sent,total:seen.append(sent))
  self.assertEqual(seen,[8*1024*1024,16*1024*1024,17*1024*1024]);self.assertEqual(drive.data,self.blob)

class FakeAPI:
 def __init__(self,ready=True,status=(4,1.0,'Ready')):self.ready=ready;self.st=status;self.added=[]
 def add(self,h):self.added.append(h);return '9',self.ready
 def status(self,m):return self.st
 def files(self,m):return [('Fall/Fall.2022.2160p.mkv',3,'L')]
 def unlock(self,l):return 'https://x/f','Fall.2022.2160p.mkv',3

class NativeCopies(unittest.TestCase):
 def test_copy_bytes_bypass_python_reader_and_query_uncertain_ack_before_resuming(self):
  blob=b'x'*(3*1024*1024);offsets=[]
  class API(FakeAPI):
   def unlock(self,link):return 'https://source/f','Fall.2022.2160p.mkv',len(blob)
  class Drive(FakeDrive):
   def copy_piece(self,source,source_headers,target,headers,offset,count,total,timeout):
    offsets.append(offset)
    result=self.call('PUT',target,blob[offset:offset+count],{'Content-Range':'bytes %d-%d/%d'%(offset,offset+count-1,total)})
    if len(offsets)==1:raise ConnectionError('response lost after Drive accepted the bytes')
    return result
  with tempfile.TemporaryDirectory() as profile:
   debrid_drive.queue(profile,{'id':H,'name':'Fall'},'movie','Fall');drive=Drive();api=API()
   debrid_drive.step(profile,api,drive)
   def forbidden(*args):raise AssertionError('Video bytes passed through Python source reader')
   debrid_drive.step(profile,api,drive,open_url=forbidden)
   self.assertEqual(debrid_drive.load(profile)['jobs'][0]['status'],'done');self.assertEqual(drive.data,blob)
   self.assertEqual(offsets,[0,1024*1024,2*1024*1024])

class HashNamedJobs(unittest.TestCase):
 """Owner screenshot (build 314): Build Season's episodes went into Drive folders named after the torrent hash
 ("3c90db2e052…"), so the Library had no title or poster for them."""
 def test_jobs_take_the_show_title_and_copied_files_move_into_its_folder(self):
  h='3c90db2e05'+'a'*30
  state={'jobs':[{'hash':h,'name':h,'title':h,'kind':'episode','season':'1','episode':'2','show_tmdb':'31910','status':'done',
                  'files':[{'path':'Naruto Shippuuden - 002 [1080p].mkv','drive_name':'Naruto Shippuuden - 002 [1080p].mkv','drive_id':'f1','done':True}]},
                 {'hash':'b'*40,'name':'b'*40,'title':'b'*40,'kind':'episode','season':'1','episode':'3','show_tmdb':'31910','status':'new','files':[]},
                 {'hash':'c'*40,'name':'Fall','title':'Fall','kind':'movie','status':'new','files':[]}]}
  changed=debrid_drive.retitle('/p',state,plans={'31910':{'title':'Naruto Shippūden'}})
  self.assertEqual([j['title'] for j,_ in changed],['Naruto Shippūden','Naruto Shippūden'])
  self.assertEqual((state['jobs'][1]['name'],state['jobs'][2]['title']),('Naruto Shippūden S01E03','Fall'))
  calls=[]
  class Drive:
   def folder(self,parts):return 'id:'+'/'.join(parts[1:])
   def call(self,method,url,body=None,headers=None):
    calls.append((method,url));return (200,{},b'{"files":[]}') if method=='GET' else (200,{},b'{}')
  self.assertEqual(debrid_drive.rehome(Drive(),state['jobs'][0]),1)
  move=calls[0][1]
  self.assertIn('addParents=id%3ATV%20Shows/Naruto%20Shipp%C5%ABden',move.replace('%2F','/'))
  self.assertIn('removeParents=id%3ATV%20Shows/'+h,move.replace('%2F','/'))
  self.assertTrue(any(m=='PATCH' and h in u for m,u in calls[2:]))      # the empty hash folder goes to the Trash
  self.assertNotIn('moved_from',state['jobs'][0])
  self.assertTrue(debrid_drive.is_hash('A'*32) and not debrid_drive.is_hash('Naruto'))
  self.assertEqual(state['jobs'][0]['files'][0]['drive_name'],'Naruto Shippūden S01E02 - Naruto Shippuuden - 002 [1080p].mkv')
  import drivelibrary
  info=drivelibrary.parse(state['jobs'][0]['files'][0]['drive_name'])
  self.assertEqual((info['title'],info['season'],info['episode']),('Naruto Shippūden','1','2'))
  self.assertEqual(debrid_drive.episode_name(state['jobs'][0],'Naruto.S01E02.mkv'),'Naruto.S01E02.mkv')   # already says it

class TwoLanes(unittest.TestCase):
 """ISSUE-164 / 1F.4: a season's episodes go up to Drive up to three at a time; a movie is still one upload."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def season(self,names):
  class Pack(FakeAPI):
   def files(self,m):return [('S/%s'%n,3,n) for n in names]
   def unlock(self,l):return 'https://x/'+l,l,3
  return Pack()
 def drive(self,fail=None,pause=.3):
  import threading,time
  test=self;lock=threading.Lock();test.now=test.most=0;test.uploaded=[];test.shown=[];p=self.p
  class Lanes(FakeDrive):
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None,activity=lambda *a:None):
    with lock:test.now+=1;test.most=max(test.most,test.now)
    try:
     session.update(url='https://upload/'+name,size=size);save()
     time.sleep(pause);progress(1,size);time.sleep(pause)
     test.shown.append(dict(debrid_drive.load(p).get('current') or {}))
     if name==fail:raise ConnectionError('dropped')
     progress(size,size);test.uploaded.append(name);return {'id':'d-'+name,'size':str(size)}
    finally:
     with lock:test.now-=1
  return Lanes()
 def run_job(self,api,drive):
  for _ in range(6):
   if debrid_drive.step(self.p,api,drive) is None:break
 def test_a_season_uploads_three_episodes_at_once(self):
  # Roadmap 1F.4: three lanes when three or more files remain (build-252 log: ~3.3 MB/s per lane on a 115 Mbps line).
  names=['Show.S01E0%d.mkv'%n for n in (1,2,3)]
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  drive=self.drive();self.run_job(self.season(names),drive)
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(sorted(self.uploaded),names);self.assertEqual(self.most,3)
  self.assertTrue(all(f['done'] and f['drive_id'] for f in job['files']))
  self.assertEqual(len(drive.folders_made),3)
  self.assertTrue(any(c.get('parallel')==3 for c in self.shown))      # the pages show all three lanes' speed
  state=debrid_drive.load(self.p);self.assertNotIn('current',state);self.assertNotIn('current_also',state)
 def test_build_season_episodes_one_job_each_copy_three_at_a_time(self):
  # Owner log 31996cd8 (build 309, 182/101 Mbps line): one job per episode went up one at a time (~2.8 MB/s).
  class Episodes(FakeAPI):
   def files(self,m):return [('S/Show.S01E0%s.mkv'%m[-1],3,'Show.S01E0%s.mkv'%m[-1])]
   def unlock(self,l):return 'https://x/'+l,l,3
   def add(self,h):self.added.append(h);return 'magnet'+h[-1],True
  for n in (1,2,3,4):
   debrid_drive.queue(self.p,{'id':('%d'%n)*40,'name':'Show S01E0%d'%n},'episode','Show',season='1',episode=str(n))
  drive=self.drive();api=Episodes()
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)          # episode 1: added at AllDebrid
  debrid_drive.step(self.p,api,drive)                              # 1, 2 and 3 copy side by side
  self.assertEqual(self.most,3);self.assertEqual(sorted(self.uploaded),['Show.S01E01.mkv','Show.S01E02.mkv','Show.S01E03.mkv'])
  jobs=debrid_drive.load(self.p)['jobs']
  self.assertEqual([j['status'] for j in jobs],['done','done','done','new'])
  self.run_job(api,drive)
  self.assertEqual([j['status'] for j in debrid_drive.load(self.p)['jobs']],['done']*4)
 def test_a_companion_episode_failing_does_not_fail_the_first(self):
  class Episodes(FakeAPI):
   def files(self,m):return [('S/Show.S01E0%s.mkv'%m[-1],3,'Show.S01E0%s.mkv'%m[-1])]
   def unlock(self,l):return 'https://x/'+l,l,3
   def add(self,h):self.added.append(h);return 'magnet'+h[-1],True
  for n in (1,2):
   debrid_drive.queue(self.p,{'id':('%d'%n)*40,'name':'Show S01E0%d'%n},'episode','Show',season='1',episode=str(n))
  drive=self.drive(fail='Show.S01E02.mkv',pause=.05);api=Episodes()
  debrid_drive.step(self.p,api,drive);debrid_drive.step(self.p,api,drive)
  jobs=debrid_drive.load(self.p)['jobs']
  self.assertEqual(jobs[0]['status'],'done')
  self.assertEqual((jobs[1]['status'],jobs[1]['tries']),('copying',1));self.assertIn('ConnectionError',jobs[1]['error'])
 def test_two_episodes_use_two_lanes_and_five_use_three_at_a_time(self):
  self.assertEqual([debrid_drive.lanes_for(n) for n in (0,1,2,3,4,10)],[1,1,2,3,3,3])
  for count,most in ((2,2),(5,3)):
   self.tearDown();self.setUp()
   names=['Show.S01E%02d.mkv'%n for n in range(1,count+1)]
   debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
   self.run_job(self.season(names),self.drive(pause=.1))
   self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'done');self.assertEqual(sorted(self.uploaded),names);self.assertEqual(self.most,most)
 def test_a_movie_is_still_one_upload(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  self.run_job(FakeAPI(),self.drive());self.assertEqual(self.most,1)
 def test_one_lane_failing_keeps_the_others_work_and_the_session(self):
  names=['Show.S01E01.mkv','Show.S01E02.mkv']
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  api,drive=self.season(names),self.drive(fail='Show.S01E02.mkv')
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)                 # AllDebrid has it
  self.assertEqual(debrid_drive.step(self.p,api,drive),30)                # copy: one lane failed, tried again in 30 s
  job=debrid_drive.load(self.p)['jobs'][0];files={f['path']:f for f in job['files']}
  self.assertTrue(files['S/Show.S01E01.mkv']['done']);self.assertFalse(files['S/Show.S01E02.mkv']['done'])
  self.assertEqual(files['S/Show.S01E02.mkv']['session']['url'],'https://upload/Show.S01E02.mkv')   # resumes there
  self.assertEqual(job['tries'],1)

class Queue(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name;self.notes=[];self.done=[]
 def tearDown(self):self.tmp.cleanup()
 def test_expired_source_renews_at_the_same_offset_without_waiting_for_a_job_retry(self):
  api=FakeAPI();unlocks=[];opens=[]
  def unlock(link):
   unlocks.append(link);return 'https://source/'+str(len(unlocks)),'Fall.2022.2160p.mkv',3
  api.unlock=unlock
  def open(url,offset):
   opens.append((url,offset))
   if url.endswith('/1'):raise urllib.error.HTTPError(url,403,'expired',{},io.BytesIO())
   return io.BytesIO(b'abc'[offset:])
  debrid_drive.queue(self.p,{'id':H,'name':'Fall'},'movie','Fall')
  debrid_drive.step(self.p,api,FakeDrive())
  drive=FakeDrive();debrid_drive.step(self.p,api,drive,open_url=open)
  self.assertEqual(drive.data,b'abc');self.assertEqual(opens,[('https://source/1',0),('https://source/2',0)])
  self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'done')
 def run_all(self,api,drive):
  for _ in range(10):
   if debrid_drive.step(self.p,api,drive,lambda k,t,x:self.notes.append((k,t)),open_url=lambda u,o:io.BytesIO(b'abc'[o:]),on_done=self.done.append) is None:break
 def test_movie_end_to_end(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  self.assertEqual(len(debrid_drive.queue(self.p,{'id':H},'movie')['hash']),40);self.assertEqual(len(debrid_drive.load(self.p)['jobs']),1)
  drive=FakeDrive();self.run_all(FakeAPI(),drive)
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(drive.data,b'abc');self.assertEqual(drive.folders_made,[['Kodi Downloads','Movies']])
  self.assertIn(('drive','Saved to Google Drive'),self.notes);self.assertEqual(len(self.done),1)
  self.assertFalse(debrid_drive.active(self.p));self.assertEqual(debrid_drive.uploads(self.p),[])
 def test_a_season_download_with_one_episode_says_so(self):
  # Owner (build 205): "i pressed full season" and the Lanterns version picked held S01E01 alone (8.4 GB).
  class One(FakeAPI):
   def files(self,m):return [('Lanterns/Lanterns.S01E01.2160p.mkv',3,'L')]
   def unlock(self,l):return 'https://x/f','Lanterns.S01E01.2160p.mkv',3
  debrid_drive.queue(self.p,{'id':H,'name':'Lanterns.S01E01.2160p'},'season','Lanterns',season='1')
  self.run_all(One(),FakeDrive())
  self.assertIn(('problem','Only one episode was in that download'),self.notes)
  self.assertNotIn(('drive','Saved to Google Drive'),self.notes)
 def test_speed_between_slow_pieces(self):
  # Build 207 (build-206 log): 32 MB pieces 20-30 s apart; the 20 s window held one mark and every page read 0 MB/s.
  t={'now':1000.0};seen=[];p=self.p
  class Slow(FakeDrive):
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None,activity=lambda *a:None):
    for n in range(1,4):
     t['now']+=25;progress(n*32*1048576,size);seen.append(debrid_drive.load(p)['current']['rate'])
    return {'id':'d','size':str(size)}
  class Big(FakeAPI):
   def files(self,m):return [('Fall/Fall.2022.2160p.mkv',10**10,'L')]
   def unlock(self,l):return 'https://x/f','Fall.2022.2160p.mkv',10**10
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  for _ in range(5):
   if debrid_drive.step(self.p,Big(),Slow(),clock=lambda:t['now']) is None or len(seen)>=3:break
  self.assertEqual(seen[0],0.0)
  self.assertAlmostEqual(seen[1],32*1048576/25.0);self.assertAlmostEqual(seen[2],32*1048576/25.0)
 def test_waits_while_alldebrid_fetches(self):
  debrid_drive.queue(self.p,{'id':H},'movie','Fall (2022)')
  api=FakeAPI(ready=False,status=(1,0.25,'Downloading'))
  self.assertEqual(debrid_drive.step(self.p,api,FakeDrive()),1)
  self.assertEqual(debrid_drive.step(self.p,api,FakeDrive()),15)
  up=notices.uploads(self.p);self.assertEqual(up[0]['line'],'AllDebrid is fetching it · 25%')
 def test_alldebrid_refusal_fails_with_its_words(self):
  debrid_drive.queue(self.p,{'id':H},'movie','Fall (2022)')
  class Bad(FakeAPI):
   def add(self,h):raise alldebrid.Problem('AllDebrid needs a premium subscription for this.')
  debrid_drive.step(self.p,Bad(),FakeDrive(),lambda k,t,x:self.notes.append((k,t,x)))
  self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'failed');self.assertIn('premium',self.notes[0][2])
 def test_episode_goes_to_its_show(self):
  self.assertEqual(debrid_drive.folders('episode','Lanterns.S01E01.2160p.mkv','Lanterns'),['Kodi Downloads','TV Shows','Lanterns'])
  self.assertEqual(debrid_drive.folders('season','01 - Pilot.mkv','Lanterns'),['Kodi Downloads','TV Shows','Lanterns'])
  self.assertEqual(debrid_drive.info_hash({'id':H.upper()}),H);self.assertEqual(debrid_drive.info_hash({'id':'nothex'}),'')

class SeriesPack(unittest.TestCase):
    """Owner (build 252): seasons 1-3 of Naruto Shippuden from a complete-series pack queued all 500 episodes and the
    films three times."""
    PACK = 'Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio)/'
    def files(self):
        out = []
        for season, first, last in ((1, 1, 32), (2, 33, 53), (3, 54, 71), (4, 72, 88)):
            for n in range(first, last + 1):
                out.append((self.PACK + 'Season %02d (%03d-%03d)/Naruto Shippuden Episode %03d.mkv' % (season, first, last, n), 400, 'L%d' % n))
        out.append((self.PACK + 'Movies/Naruto Shippuden The Movie 02 - Bonds (2008).mkv', 2000, 'M2'))
        return out
    def test_a_season_takes_only_its_folder(self):
        picked = alldebrid.pick(self.files(), 'season', '2')
        self.assertEqual(len(picked), 21)
        self.assertTrue(all('/Season 02 (' in p for p, _, _ in picked))
    def test_sxxeyy_names_win_and_another_season_is_empty(self):
        files = [('Show.S01/Show.S01E%02d.mkv' % n, 300, str(n)) for n in range(1, 11)]
        self.assertEqual(len(alldebrid.pick(files, 'season', '1')), 10)
        self.assertEqual(alldebrid.pick(files, 'season', '3'), [])
    def test_an_unknowable_series_pack_is_refused_not_queued(self):
        files = [('Pack/Episode %03d.mkv' % n, 300, str(n)) for n in range(1, 501)]
        with self.assertRaises(alldebrid.TooMany):
            alldebrid.pick(files, 'season', '1')

class CancelAll(unittest.TestCase):
    def test_every_unfinished_copy_is_cancelled_once(self):
        import transfer_control
        with tempfile.TemporaryDirectory() as tmp:
            debrid_drive.save(tmp, {'jobs': [{'hash': 'AA', 'status': 'copying'}, {'hash': 'bb', 'status': 'new'},
                                             {'hash': 'cc', 'status': 'done'}, {'hash': 'dd', 'status': 'failed'}]})
            self.assertEqual(transfer_control.unfinished_copies(tmp), ['aa', 'bb'])
            self.assertEqual(transfer_control.cancel_all_copies(tmp), 2)
            self.assertEqual(transfer_control.cancelled_copies(tmp), {'aa', 'bb'})
            self.assertEqual(transfer_control.menu('up', {'source': 'debrid', 'hash': 'aa'}, queued=2)[-2],
                             ('Cancel all downloads to Drive (2)', 'cancel_all'))


class RememberShows(unittest.TestCase):
    def test_finished_episode_copies_name_their_show(self):
        seen = []
        jobs = [{'status': 'done', 'kind': 'episode', 'title': 'Phony', 'show_tmdb': '275139',
                 'files': [{'drive_name': 'phony.s01e01.1080p.web.h264-x.mkv'}]},
                {'status': 'copying', 'kind': 'episode', 'title': 'Busy', 'show_tmdb': '1', 'files': []},
                {'status': 'done', 'kind': 'movie', 'title': 'Film', 'show_tmdb': '2', 'files': []},
                {'status': 'done', 'kind': 'season', 'title': 'Old', 'files': []}]
        self.assertTrue(debrid_drive.remember_shows(None, jobs, lambda names, tmdb: seen.append((names, tmdb)) or True))
        self.assertEqual(len(seen), 1)
        names, tmdb = seen[0]
        self.assertEqual(tmdb, '275139')
        self.assertIn('Phony', names)
        self.assertEqual(len(names), 2)


class Wiring(unittest.TestCase):
 def test_download_uses_the_shared_pre_selection_interceptor(self):
  src=(BOOT/'download.py').read_text()
  self.assertIn('dl.follow(url)',src)
  self.assertNotIn('dl.added(',src)
  self.assertNotIn('to_drive(',src)
  hook=(BOOT/'resources/lib/elementum_cloud.py').read_text()
  self.assertIn('watch=mode == 1',hook)
 def test_service_runs_the_queue(self):
  src=(BOOT/'service.py').read_text()
  self.assertIn('debrid_drive.step(profile,alldebrid.AllDebrid(token),drive',src);self.assertIn('threading.Thread(target=debrid_loop,daemon=True).start()',src)
  self.assertIn('prepare_downloads.request_check(profile)',src[src.index('def debrid_loop'):])

class PlayedVersions(unittest.TestCase):
 """Owner (build 160): "Download only or download and watch doesnt appear when i select the source it just starts
 downloading" — a played version kept downloading onto the phone (19.8 GB Fall)."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_taken_after_grace_only_while_nothing_plays(self):
  t=[{'id':H,'name':'Fall.2022.2160p.WEB-DL.DV.mkv','progress':12},{'id':'b'*40,'name':'Done.2020.mkv','progress':100}]
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1000),[])        # just appeared (buffering, choosing)
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=True,now=1100),[])         # playing: never, and the clock restarts
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1200),[])
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1200+debrid_drive.GRACE),[H])
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual((job['kind'],job['title'],job['hash']),('movie','Fall',H))
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=5000),[])        # once
 def test_kinds(self):
  self.assertEqual([debrid_drive.kind_of(n) for n in ('Fall.2022.mkv','Lanterns.S01E02.mkv','Lanterns.S01.2160p','Show Season 2 Complete')],
                   ['movie','episode','season','season'])
 def test_service_takes_them_back_from_elementum(self):
  src=(BOOT/'service.py').read_text()
  self.assertIn("debrid_drive.adopt(profile,notices.torrent_list(),xbmc.Player().isPlayingVideo())",src)
  self.assertIn("driveupload.remove_torrent(tid)",src[src.index('def debrid_loop'):])


class OneAtATimeOnTheConnection(unittest.TestCase):
 """Owner (build 168 log): Fall's copy from AllDebrid ran at ~0.2 MB/s while Inception's conversion read and wrote Drive."""
 def test_copying_flag_and_preparation_waits(self):
  import tempfile
  with tempfile.TemporaryDirectory() as p:
   self.assertFalse(debrid_drive.copying(p))
   debrid_drive.save(p,{'jobs':[],'current':{'stage':'copying','sent':1,'total':2}});self.assertTrue(debrid_drive.copying(p))
   debrid_drive.save(p,{'jobs':[],'current':{'stage':'fetching','sent':1,'total':2}});self.assertFalse(debrid_drive.copying(p))
  # build 170: preparation no longer waits for copies (they run at 6-8 MB/s now)
 def test_each_chunk_reports_both_sides(self):
  src=(LIB/'driveupload.py').read_text()
  self.assertIn("MB/s from the source), sent in %.1f s (%.2f MB/s to Google Drive)",src)

if __name__=='__main__':unittest.main()
