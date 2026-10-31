import hashlib,http.server,importlib.util,json,os,tempfile,threading,time,unittest,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('driveupload',ROOT/'migration/bundled-bootstrap/resources/lib/driveupload.py')
up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)

class FakeDrive(http.server.BaseHTTPRequestHandler):
 """Enough of Drive v3: folder search and create, resumable uploads with 308 / Range, and status queries."""
 files={};uploads={};fail_after=None;requests=0
 def log_message(self,*a):pass
 def reply(self,status,body=b'',headers=None):
  self.send_response(status)
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def body(self):return self.rfile.read(int(self.headers.get('Content-Length') or 0))
 def do_GET(self):
  assert self.headers['Authorization']=='Bearer token-1'
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)['q'][0]
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
  FakeDrive.files={};FakeDrive.uploads={};FakeDrive.fail_after=None;FakeDrive.requests=0
  self.server=http.server.HTTPServer(('127.0.0.1',0),FakeDrive);threading.Thread(target=self.server.serve_forever,daemon=True).start()
  base='http://127.0.0.1:%d'%self.server.server_port
  self.patch=(up.API,up.UPLOAD,up.CHUNK);up.API=base+'/files';up.UPLOAD=base+'/upload';up.CHUNK=1024*1024
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'Kodi Downloads'
 def tearDown(self):self.server.shutdown();up.API,up.UPLOAD,up.CHUNK=self.patch;self.tmp.cleanup()
 def video(self,rel,size):
  p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(os.urandom(size));old=time.time()-600;os.utime(p,(old,old));return p
 def test_uploads_into_drive_folders_resumes_and_removes_phone_copies(self):
  ep=self.video("TV Shows/Grey's Anatomy/Season 1/Grey's Anatomy S01E01.mkv",5*1024*1024+123);movie=self.video('Movies/Heat (1995).mp4',300000)
  self.video('Movies/notes.txt',10);fresh=self.root/'Movies/Fresh.mkv';fresh.write_bytes(b'x'*10)
  digest=hashlib.sha256(ep.read_bytes()).hexdigest()
  drive=up.Drive(lambda:'token-1',up.sender(None));state=str(Path(self.tmp.name)/'state.json');logs=[]
  FakeDrive.fail_after=3
  with self.assertRaises(RuntimeError):up.run_once(str(self.root),drive,state,logs.append)
  # The movie went up before the failure; the episode's session was kept for resuming.
  self.assertFalse(movie.exists());self.assertTrue(ep.exists());self.assertIn(str(ep),json.load(open(state))['sessions'])
  partial=len(FakeDrive.uploads['/session/'+json.load(open(state))['sessions'][str(ep)]['url'].rsplit('/',1)[1]]['data']);self.assertGreater(partial,0)
  FakeDrive.fail_after=None
  self.assertEqual(up.run_once(str(self.root),drive,state,logs.append),1)
  names={f['name']:f for f in FakeDrive.files.values()}
  self.assertEqual(hashlib.sha256(names["Grey's Anatomy S01E01.mkv"]['data']).hexdigest(),digest)
  chain=[];node=names["Grey's Anatomy S01E01.mkv"]['parents'][0]
  while node!='root':chain.insert(0,FakeDrive.files[node]['name']);node=FakeDrive.files[node]['parents'][0]
  self.assertEqual(chain,['Kodi Downloads','TV Shows',"Grey's Anatomy",'Season 1'])
  self.assertFalse(ep.exists());self.assertFalse(movie.exists());self.assertFalse((self.root/"TV Shows/Grey's Anatomy").exists())
  self.assertTrue((self.root/'Movies/notes.txt').exists());self.assertTrue(fresh.exists());self.assertEqual(json.load(open(state))['sessions'],{})
  self.assertEqual(sum(1 for f in FakeDrive.files.values() if f.get('name')=='Kodi Downloads'),1)
 def test_stops_when_asked_and_keeps_the_file(self):
  ep=self.video('Movies/Long.mkv',3*1024*1024);calls=iter([True,True,False])
  drive=up.Drive(lambda:'token-1',up.sender(None))
  with self.assertRaises(up.Stop):up.run_once(str(self.root),drive,str(Path(self.tmp.name)/'s.json'),print,lambda:next(calls,False))
  self.assertTrue(ep.exists())
 def test_tokens_refresh_through_the_sign_in_server_and_are_saved(self):
  account={'id':'a','access_tokens':{'access_token':'old','refresh_token':'r','expires_in':3600,'date':0}};saved=[]
  token=up.token_source(lambda:{'a':account},saved.append,lambda rt:{'access_token':'new','expires_in':3600},now=lambda:10000)
  self.assertEqual(token(),'new');self.assertEqual(saved[0]['access_tokens']['date'],10000)
  self.assertEqual(up.token_source(lambda:{'a':account},saved.append,None,now=lambda:10001)(),'new')
  with self.assertRaises(RuntimeError):up.token_source(lambda:{},None,None)()
if __name__=='__main__':unittest.main()
