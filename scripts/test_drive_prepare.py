"""Storage-free output, interrupted conversion, validation and original-ID replacement."""
import hashlib,io,json,sys,tempfile,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import drive_prepare as dp
import prepare_downloads as prep
import driveupload

class Drive:
 def __init__(self):
  self.files={'source':dict(id='source',name='Film.2160p.mkv',data=b'original',version='1',parents=['movies'],appProperties={})}
  self.sessions={};self.calls=[];self.number=0;self.corrupt=False;self.fail=False
 def folder(self,parts):return 'staging'
 def meta(self,key):
  f=self.files[key]
  return dict({k:v for k,v in f.items() if k!='data'},size=str(len(f['data'])),md5Checksum=hashlib.md5(f['data']).hexdigest())
 def call(self,method,url,body=None,headers=None):
  self.calls.append((method,url,body,headers or {}));headers=headers or {}
  if method=='GET':
   key=url.split('/files/')[1].split('?')[0]
   return 200,{'ETag':self.files[key]['version']},json.dumps(self.meta(key)).encode()
  if method=='POST' or (method=='PATCH' and 'uploadType=resumable' in url):
   self.number+=1;session='https://upload.example/%d'%self.number
   target=None if method=='POST' else url.split('/files/')[1].split('?')[0]
   self.sessions[session]=dict(target=target,meta=json.loads(body),data=b'')
   return 200,{'Location':session},b''
  if method=='PUT':
   s=self.sessions[url];cr=headers['Content-Range']
   if cr.startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(len(s['data'])-1)} if s['data'] else {}),b''
   start,end=map(int,cr.split()[1].split('/')[0].split('-'));total=cr.split('/')[-1]
   assert start==len(s['data']);assert end==start+len(body)-1
   if self.fail:raise OSError('network interruption')
   s['data']+=body
   if total=='*' or len(s['data'])<int(total):return 308,{'Range':'bytes=0-%d'%end},b''
   assert int(total)==len(s['data'])
   key=s['target'] or 'temp-%d'%self.number
   old=self.files.get(key,{})
   self.files[key]=dict(old,**s['meta'],id=key,data=s['data'],version=str(int(old.get('version',0))+1))
   result=self.meta(key)
   if self.corrupt:result['md5Checksum']='wrong'
   return 200,{},json.dumps(result).encode()
  if method=='PATCH':
   key=url.split('/files/')[1].split('?')[0];self.files[key].update(json.loads(body));return 200,{},b'{}'
  raise AssertionError((method,url))
 def open_at(self,key,offset):
  data=self.files[key]['data'];r=io.BytesIO(data[offset:]);r.status=206;r.headers={'Content-Range':'bytes %d-%d/%d'%(offset,len(data)-1,len(data))};return r

class Upload(unittest.TestCase):
 def setUp(self):self.d=Drive();self.source=prep.metadata(self.d,'source')
 def test_unknown_length_stream_is_bounded_and_not_committed_until_success(self):
  sink=dp.Sink(self.d,'staging','prepared',lambda:True)
  block=b'x'*65536
  for _ in range(50):
   sink.write(0,'.mp4',block)
   self.assertLessEqual(len(sink.tracks[0]['buffer']),dp.CHUNK)
  self.assertEqual(list(self.d.files),['source'])
  result=sink.finish()['0'];self.assertEqual(self.d.files[result['id']]['data'],block*50)
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_upload_error_or_bad_checksum_does_not_replace_original(self):
  sink=dp.Sink(self.d,'staging','prepared',lambda:True);sink.write(0,'.mp4',b'prepared')
  self.d.corrupt=True
  with self.assertRaisesRegex(RuntimeError,'checksum'):sink.finish()
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_original_id_is_replaced_only_after_complete_upload(self):
  sink=dp.Sink(self.d,'staging','prepared',lambda:True)
  data=b'prepared'*400000;sink.write(0,'.mp4',data);main=sink.finish()['0'];session={}
  result=dp.replace(self.d,self.source,main,session,lambda:None,lambda:True,
                    lambda offset:self.d.open_at(main['id'],offset),lambda n,t:None)
  self.assertEqual(result['id'],'source');self.assertEqual(self.d.files['source']['data'],data)
  self.assertEqual(self.d.files['source']['name'],'Film.2160p.mp4');self.assertEqual(session,{})
 def test_interrupted_update_retains_original_and_resumes_from_acknowledged_range(self):
  sink=dp.Sink(self.d,'staging','prepared',lambda:True);sink.write(0,'.mp4',b'y'*(dp.CHUNK*2+10));main=sink.finish()['0']
  session={};sent=[0]
  def progress(n,t):sent[0]=n
  with self.assertRaises(driveupload.Stop):
   dp.replace(self.d,self.source,main,session,lambda:None,lambda:sent[0]==0,lambda n:self.d.open_at(main['id'],n),progress)
  self.assertEqual(self.d.files['source']['data'],b'original');self.assertEqual(sent[0],dp.CHUNK)
  offsets=[]
  dp.replace(self.d,self.source,main,session,lambda:None,lambda:True,lambda n:(offsets.append(n) or self.d.open_at(main['id'],n)),lambda n,t:None)
  self.assertEqual(offsets,[dp.CHUNK]);self.assertEqual(len(self.d.files['source']['data']),dp.CHUNK*2+10)
 def test_changed_source_is_never_replaced(self):
  self.d.files['source']['data']=b'externally changed'
  with self.assertRaisesRegex(RuntimeError,'source changed'):
   dp.replace(self.d,self.source,dict(size=8,md5Checksum='f'*32),{},lambda:None,lambda:True,lambda n:None,lambda n,t:None)
 def test_short_read_and_wrong_range_are_not_uploaded(self):
  sink=dp.Sink(self.d,'staging','prepared',lambda:True);sink.write(0,'.mp4',b'prepared');main=sink.finish()['0']
  def wrong(n):r=self.d.open_at(main['id'],n);r.headers={};return r
  with self.assertRaisesRegex(RuntimeError,'wrong prepared byte range'):
   dp.replace(self.d,self.source,main,{},lambda:None,lambda:True,wrong,lambda n,t:None)
  self.assertEqual(self.d.files['source']['data'],b'original')

class Native:
 outputs=True;streams=True;keeps_image_subs=True
 def __init__(self):self.calls=0;self.fail=False;self.bad=False
 def probe(self,path):return dict(ready='temp-' in path,width=3840,height=2160,hdr=True,duration=1300)
 def convert_to(self,source,sink,keep,progress):
  self.calls+=1;sink.write(0,'.mp4',b'prepared video')
  if self.fail:raise driveupload.Stop('stopped')
  progress(2,1300,1300)
 def verify(self,source,target):
  if self.bad:raise RuntimeError('Output validation failed; original retained')
class Stream:
 def url(self,key):return 'http://127.0.0.1:1234/'+key+'/file'
 def forget(self,key):pass

class Queue(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.d=Drive();self.n=Native();self.q=prep.Queue(self.tmp.name,self.d,self.n,stream=Stream())
  self.q.state['jobs']={'slot':{'source':prep.metadata(self.d,'source'),'status':'waiting'}}
  self.open=patch('prepare_cloud.urllib.request.urlopen',side_effect=lambda req,timeout:self.d.open_at(req.full_url.split('/')[-2],int(req.headers['Range'][6:-1])))
  self.open.start();self.addCleanup(self.open.stop)
 def test_end_to_end_queue_writes_no_local_media_and_marks_ready(self):
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'prepared video');self.assertTrue(prep.ready(self.d.meta('source')))
  self.assertEqual(list(self.q.work.iterdir()),[]);self.assertTrue(self.d.files['temp-1']['trashed'])
 def test_cancel_keeps_original_and_retry_restarts_generation(self):
  self.n.fail=True;self.assertFalse(self.q.process_one());self.assertEqual(self.d.files['source']['data'],b'original')
  self.n.fail=False;self.assertTrue(self.q.process_one());self.assertEqual(self.n.calls,2)
 def test_bad_output_keeps_original_untagged(self):
  self.n.bad=True;self.assertFalse(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'original');self.assertFalse(prep.ready(self.d.meta('source')))
 def test_completed_temp_is_reused_after_interruption(self):
  self.n.bad=True;self.assertFalse(self.q.process_one());self.n.bad=False
  self.q.state['jobs']['slot']['retry_after']=0
  self.assertTrue(self.q.process_one());self.assertEqual(self.n.calls,1)

if __name__=='__main__':unittest.main()
