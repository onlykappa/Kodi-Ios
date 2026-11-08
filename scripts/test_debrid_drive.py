"""Owner (build 160): "a movie im downloading goes onto my phone still … if i do a large movie it wont ever download";
chose AllDebrid straight to Drive. alldebrid (client, pick), driveupload.upload_stream, debrid_drive (queue, step),
and the wiring in download.py, service.py and notices.py."""
import io,json,sys,tempfile,unittest
from pathlib import Path
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

class FakeAPI:
 def __init__(self,ready=True,status=(4,1.0,'Ready')):self.ready=ready;self.st=status;self.added=[]
 def add(self,h):self.added.append(h);return '9',self.ready
 def status(self,m):return self.st
 def files(self,m):return [('Fall/Fall.2022.2160p.mkv',3,'L')]
 def unlock(self,l):return 'https://x/f','Fall.2022.2160p.mkv',3

class Queue(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name;self.notes=[];self.done=[]
 def tearDown(self):self.tmp.cleanup()
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
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None):
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
