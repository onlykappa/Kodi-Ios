import hashlib,http.server,importlib.util,json,os,tempfile,threading,time,unittest,urllib.parse
from unittest import mock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('driveupload',ROOT/'migration/bundled-bootstrap/resources/lib/driveupload.py')
up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)

class FakeDrive(http.server.BaseHTTPRequestHandler):
 """Enough of Drive v3: folder search and create, resumable uploads with 308 / Range, and status queries."""
 files={};uploads={};fail_after=None;requests=0;digest_override=None;verifications=0
 def log_message(self,*a):pass
 def reply(self,status,body=b'',headers=None):
  self.send_response(status)
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def body(self):return self.rfile.read(int(self.headers.get('Content-Length') or 0))
 def do_GET(self):
  assert self.headers['Authorization']=='Bearer token-1'
  parsed=urllib.parse.urlsplit(self.path)
  if parsed.path.startswith('/files/') or parsed.path.startswith('/session/'):
   FakeDrive.verifications+=1;fid=urllib.parse.unquote(parsed.path.rsplit('/',1)[1]);item=self.files.get(fid)
   if not item:return self.reply(404,b'{}')
   data=item.get('data',b'')
   return self.reply(200,json.dumps({'id':fid,'size':str(len(data)),
     'md5Checksum':FakeDrive.digest_override or hashlib.md5(data).hexdigest(),'trashed':item.get('trashed',False)}).encode())
  q=urllib.parse.parse_qs(parsed.query)['q'][0]
  name=q.split("name='")[1].split("' and mimeType")[0].replace("\\'","'");parent=q.split("and '")[1].split("' in parents")[0]
  hits=[{'id':i} for i,f in self.files.items() if f['name']==name and f['parents']==[parent]]
  self.reply(200,json.dumps({'files':hits}).encode())
 def do_POST(self):
  meta=json.loads(self.body());fid='f%d'%(len(self.files)+1)
  if 'uploadType=resumable' in self.path:
   self.uploads['/session/'+fid]={'meta':meta,'size':int(self.headers['X-Upload-Content-Length']),'data':b''}
   return self.reply(200,headers={'Location':'http://127.0.0.1:%d/session/%s'%(self.server.server_port,fid)})
  self.files[fid]=meta;self.reply(200,json.dumps({'id':fid}).encode())
 def do_PUT(self):
  FakeDrive.requests+=1;up_=self.uploads[self.path];data=self.body();rng=self.headers['Content-Range']
  if FakeDrive.fail_after is not None and FakeDrive.requests>FakeDrive.fail_after:return self.reply(503)
  if not rng.startswith('bytes */'):
   start=int(rng.split()[1].split('-')[0]);assert start==len(up_['data']);up_['data']+=data
  if len(up_['data'])==up_['size']:
   fid=self.path.rsplit('/',1)[1];self.files[fid]=dict(up_['meta'],data=up_['data'])
   return self.reply(200,json.dumps({'id':fid,'size':str(up_['size'])}).encode())
  self.reply(308,headers={'Range':'bytes=0-%d'%(len(up_['data'])-1)} if up_['data'] else {})

class Upload(unittest.TestCase):
 def setUp(self):
  FakeDrive.files={};FakeDrive.uploads={};FakeDrive.fail_after=None;FakeDrive.requests=0;FakeDrive.digest_override=None;FakeDrive.verifications=0
  self.server=http.server.HTTPServer(('127.0.0.1',0),FakeDrive);threading.Thread(target=self.server.serve_forever,daemon=True).start()
  base='http://127.0.0.1:%d'%self.server.server_port
  self.patch=(up.API,up.UPLOAD,up.CHUNK);up.API=base+'/files';up.UPLOAD=base+'/upload';up.CHUNK=1024*1024
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'Kodi Downloads'
 def tearDown(self):self.server.shutdown();self.server.server_close();up.API,up.UPLOAD,up.CHUNK=self.patch;self.tmp.cleanup()
 def video(self,rel,size):
  p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(os.urandom(size));old=time.time()-600;os.utime(p,(old,old));return p
 def test_uploads_into_drive_folders_resumes_and_removes_phone_copies(self):
  ep=self.video("TV Shows/Grey's Anatomy/Season 1/Grey's Anatomy S01E01.mkv",5*1024*1024+123);movie=self.video('Movies/Heat (1995).mp4',300000)
  self.video('Movies/notes.txt',10);fresh=self.root/'Movies/Fresh.mkv';fresh.write_bytes(b'x'*10)
  digest=hashlib.sha256(ep.read_bytes()).hexdigest()
  drive=up.Drive(lambda:'token-1',up.sender(None));state=str(Path(self.tmp.name)/'state.json');logs=[]
  FakeDrive.fail_after=3
  invalidations=[]
  with self.assertRaises(RuntimeError):up.run_once(str(self.root),drive,state,logs.append,on_uploaded=lambda:invalidations.append('uploaded'))
  # The movie went up before the failure; the episode's session was kept for resuming.
  self.assertFalse(movie.exists());self.assertTrue(ep.exists());self.assertIn(str(ep),json.loads(Path(state).read_text())['sessions'])
  self.assertEqual(invalidations,['uploaded'])  # a later failure must not hide an already uploaded movie
  self.assertEqual(FakeDrive.verifications,1)  # size alone did not authorize deleting the phone copy
  partial=len(FakeDrive.uploads['/session/'+json.loads(Path(state).read_text())['sessions'][str(ep)]['url'].rsplit('/',1)[1]]['data']);self.assertGreater(partial,0)
  FakeDrive.fail_after=None
  self.assertEqual(up.run_once(str(self.root),drive,state,logs.append),1)
  names={f['name']:f for f in FakeDrive.files.values()}
  self.assertEqual(hashlib.sha256(names["Grey's Anatomy S01E01.mkv"]['data']).hexdigest(),digest)
  chain=[];node=names["Grey's Anatomy S01E01.mkv"]['parents'][0]
  while node!='root':chain.insert(0,FakeDrive.files[node]['name']);node=FakeDrive.files[node]['parents'][0]
  self.assertEqual(chain,['Kodi Downloads','TV Shows',"Grey's Anatomy",'Season 1'])
  self.assertFalse(ep.exists());self.assertFalse(movie.exists());self.assertFalse((self.root/"TV Shows/Grey's Anatomy").exists())
  self.assertTrue((self.root/'Movies/notes.txt').exists());self.assertTrue(fresh.exists());self.assertEqual(json.loads(Path(state).read_text())['sessions'],{})
  self.assertEqual(sum(1 for f in FakeDrive.files.values() if f.get('name')=='Kodi Downloads'),1)
 def test_stops_when_asked_and_keeps_the_file(self):
  ep=self.video('Movies/Long.mkv',3*1024*1024);calls=iter([True,True,False])
  drive=up.Drive(lambda:'token-1',up.sender(None))
  with self.assertRaises(up.Stop):up.run_once(str(self.root),drive,str(Path(self.tmp.name)/'s.json'),print,lambda:next(calls,False))
  self.assertTrue(ep.exists())
 def test_checksum_mismatch_keeps_original_even_when_drive_size_matches(self):
  movie=self.video('Movies/Heat (1995).mkv',1234);FakeDrive.digest_override='0'*32
  drive=up.Drive(lambda:'token-1',up.sender(None));logs=[]
  self.assertEqual(up.run_once(str(self.root),drive,str(Path(self.tmp.name)/'s.json'),logs.append),1)
  self.assertTrue(movie.exists());self.assertEqual(FakeDrive.verifications,1)
  self.assertTrue(any('checksum' in message.lower() for message in logs))
 def test_source_change_during_transfer_keeps_phone_copy(self):
  movie=self.video('Movies/Heat (1995).mkv',1234)
  drive=up.Drive(lambda:'token-1',up.sender(None))
  up.run_once(str(self.root),drive,str(Path(self.tmp.name)/'s.json'),lambda text:None,
              on_uploaded=lambda:movie.write_bytes(b'x'*1234))
  self.assertTrue(movie.exists());self.assertEqual(movie.read_bytes(),b'x'*1234)
 def test_cancellation_after_remote_verification_keeps_original(self):
  movie=self.video('Movies/Heat (1995).mkv',1234);active=[True]
  drive=up.Drive(lambda:'token-1',up.sender(None))
  def confirm(*args):active[0]=False;return True
  with mock.patch.object(up,'confirmed',side_effect=confirm):
   with self.assertRaises(up.Stop):
    up.run_once(str(self.root),drive,str(Path(self.tmp.name)/'s.json'),lambda text:None,keep_going=lambda:active[0])
  self.assertTrue(movie.exists())
 def test_transfer_lock_rejects_an_overlapping_scan_and_releases_after_failure(self):
  with up.transfer_lock(self.tmp.name):
   with self.assertRaises(up.Stop):
    with up.transfer_lock(self.tmp.name):self.fail('must not acquire a second writer lock')
  with up.transfer_lock(self.tmp.name):pass
 def test_failed_folder_lookup_never_creates_a_duplicate_folder(self):
  sent=[]
  def send(method,url,body,headers):sent.append(method);return 503,{},b'{}'
  drive=up.Drive(lambda:'token-1',send)
  with self.assertRaises(RuntimeError):drive.folder(['Kodi Downloads','Movies'])
  self.assertEqual(sent,['GET'])
 def test_remote_verification_requires_checksum_size_and_not_trashed(self):
  class Reply:
   def __init__(self,meta,status=200):self.meta=meta;self.status=status
   def call(self,*args):return self.status,{},json.dumps(self.meta).encode()
  good={'id':'remote','size':'4','md5Checksum':'ab'*16,'trashed':False}
  self.assertTrue(up.confirmed(Reply(good),'remote',4,'ab'*16))
  for change in ({'size':'3'},{'md5Checksum':'cd'*16},{'md5Checksum':''},{'trashed':True}):
   with self.subTest(change=change):self.assertFalse(up.confirmed(Reply(dict(good,**change)),'remote',4,'ab'*16))
  with self.assertRaises(RuntimeError):up.confirmed(Reply({},403),'remote',4,'ab'*16)
 def test_pending_excludes_samples_symlinks_hidden_and_partial_files(self):
  movie=self.video('Movies/Heat (1995).mkv',1234)
  self.video('Movies/sample.mkv',100);self.video('Movies/Heat.mkv.part',100);self.video('Movies/.staging/Other.mkv',100)
  self.video('Movies/Still.partial.mkv',100);self.video('Movies/Still.tmp.mkv',100)
  linked=self.root/'Movies/Linked.mkv';linked.symlink_to(movie)
  self.assertEqual([Path(path).name for path,parts in up.pending(str(self.root))],['Heat (1995).mkv'])
 def test_tokens_refresh_through_the_sign_in_server_and_are_saved(self):
  account={'id':'a','access_tokens':{'access_token':'old','refresh_token':'r','expires_in':3600,'date':0}};saved=[]
  token=up.token_source(lambda:{'a':account},saved.append,lambda rt:{'access_token':'new','expires_in':3600},now=lambda:10000)
  self.assertEqual(token(),'new');self.assertEqual(saved[0]['access_tokens']['date'],10000)
  self.assertEqual(up.token_source(lambda:{'a':account},saved.append,None,now=lambda:10001)(),'new')
  with self.assertRaises(RuntimeError):up.token_source(lambda:{},None,None)()
if __name__=='__main__':unittest.main()

class SeedingTorrents(unittest.TestCase):
 """Owner (PR 8): finished torrents still seeding in Elementum's folder must go to Drive, not stay on the phone."""
 def setUp(self):
  self.dir=tempfile.TemporaryDirectory();self.root=self.dir.name;old=time.time()-600
  def make(rel,data=b'x'*10):
   p=os.path.join(self.root,rel);os.makedirs(os.path.dirname(p),exist_ok=True)
   with open(p,'wb') as f:f.write(data)
   os.utime(p,(old,old));return p
  self.movie=make('Scary.Movie.2026.2160p/Scary.Movie.2026.2160p.mkv')
  self.ep1=make('Lanterns.S01.1080p/Lanterns.S01E01.1080p.mkv');self.ep2=make('Lanterns.S01.1080p/Lanterns.S01E02.1080p.mkv')
  make('Lanterns.S01.1080p/sample.mkv');make('Half.Done.2025/Half.Done.2025.mkv')
  self.torrents=[{'id':'a','name':'Scary.Movie.2026.2160p','progress':100},{'id':'b','name':'Lanterns.S01.1080p','progress':100.0},
                 {'id':'c','name':'Half.Done.2025','progress':42.0}]
 def tearDown(self):self.dir.cleanup()
 def test_only_finished_torrents_with_movie_and_show_folders(self):
  found={os.path.basename(p):(parts,tid) for p,parts,tid in up.seeding_pending(self.root,self.torrents)}
  self.assertEqual(found['Scary.Movie.2026.2160p.mkv'],(['Kodi Downloads','Movies'],'a'))
  self.assertEqual(found['Lanterns.S01E01.1080p.mkv'],(['Kodi Downloads','TV Shows','Lanterns'],'b'))
  self.assertIn('Lanterns.S01E02.1080p.mkv',found)
  self.assertNotIn('sample.mkv',found);self.assertNotIn('Half.Done.2025.mkv',found)
  self.assertEqual(up.seeding_pending(self.root,[{'id':'x','name':'../etc','progress':100}]),[])
 def test_season_pack_files_without_episode_numbers_go_to_the_show(self):
  p=os.path.join(self.root,'The.Bear.Season.2.1080p','01 - Beef.mkv');os.makedirs(os.path.dirname(p))
  open(p,'wb').write(b'x'*10)
  found=up.seeding_pending(self.root,[{'id':'d','name':'The.Bear.Season.2.1080p','progress':100}])
  self.assertEqual(found[0][1],['Kodi Downloads','TV Shows','The Bear'])
 def test_torrent_dropped_only_after_every_video_is_verified(self):
  seeding=up.seeding_pending(self.root,self.torrents);dropped=[]
  class D:
   def folder(self,parts):return '/'.join(parts)
   def upload(self,path,folder,sessions,save,keep,progress):return {'id':path,'size':os.path.getsize(path)}
  verified={self.movie,self.ep1}  # episode 2's Drive copy cannot be verified
  with mock.patch.object(up,'confirmed',lambda drive,fid,size,digest:fid in verified), \
       mock.patch.object(up,'pending',lambda root:[]):
   state=os.path.join(self.root,'state.json')
   count=up.run_once(self.root,D(),state,lambda m:None,seeding=seeding,drop=dropped.append)
  self.assertEqual(count,3);self.assertEqual(dropped,['a'])  # the show keeps seeding until episode 2 verifies
  self.assertTrue(os.path.exists(self.ep1))  # Elementum removes torrent files itself, never a half torrent
  # Next cycle: the two verified files are not uploaded again; once episode 2 verifies, the show is dropped.
  uploads=[]
  class D2(D):
   def upload(self,path,folder,sessions,save,keep,progress):uploads.append(path);return {'id':path,'size':os.path.getsize(path)}
  verified.add(self.ep2)
  with mock.patch.object(up,'confirmed',lambda drive,fid,size,digest:fid in verified), \
       mock.patch.object(up,'pending',lambda root:[]):
   up.run_once(self.root,D2(),state,lambda m:None,seeding=up.seeding_pending(self.root,self.torrents),drop=dropped.append)
  self.assertEqual(uploads,[self.ep2]);self.assertIn('b',dropped)
 def test_service_feeds_seeding_torrents(self):
  source=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('driveupload.seeding_pending(download,torrents)',source)
  self.assertIn('seeding,driveupload.remove_torrent',source)
