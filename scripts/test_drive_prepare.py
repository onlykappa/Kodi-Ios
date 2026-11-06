"""Storage-free output, interrupted conversion, validation and original-ID replacement."""
import hashlib,io,json,sys,tempfile,unittest,urllib.parse,urllib.error
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
   if cr.startswith('bytes */') and s.get('result'):return 200,{},json.dumps(s['result']).encode()
   if cr.startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(len(s['data'])-1)} if s['data'] else {}),b''
   start,end=map(int,cr.split()[1].split('/')[0].split('-'));total=cr.split('/')[-1]
   assert start==len(s['data']);assert end==start+len(body)-1
   if self.fail:raise OSError('network interruption')
   s['data']+=body
   if total=='*' or len(s['data'])<int(total):return 308,{'Range':'bytes=0-%d'%end},b''
   assert int(total)==len(s['data'])
   key=s['target'] or 'temp-'+url.rsplit('/',1)[1]
   old=self.files.get(key,{})
   self.files[key]=dict(old,**s['meta'],id=key,data=s['data'],version=str(int(old.get('version',0))+1))
   result=self.meta(key)
   if self.corrupt:result['md5Checksum']='wrong'
   s['result']=result
   return 200,{},json.dumps(result).encode()
  if method=='DELETE':
   key=url.split('/files/')[1].split('?')[0]
   if key not in self.files:return 404,{},b''
   del self.files[key];return 204,{},b''
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
  for _ in range(300):
   sink.write(0,'.mp4',block)
   self.assertLessEqual(len(sink.tracks[0]['buffer']),dp.CHUNK)
  self.assertEqual(list(self.d.files),['source'])
  result=sink.finish()['0'];self.assertEqual(self.d.files[result['id']]['data'],block*300)
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_lost_acknowledgement_does_not_duplicate_intermediate_or_final_bytes(self):
  for final in (False,True):
   with self.subTest(final=final):
    drive=Drive();original_call=drive.call;lost=[False]
    def unreliable(method,url,body=None,headers=None):
     result=original_call(method,url,body,headers)
     cr=(headers or {}).get('Content-Range','')
     is_final=not cr.endswith('/*')
     if method=='PUT' and not cr.startswith('bytes */') and is_final==final and not lost[0]:
      lost[0]=True;raise urllib.error.URLError(TimeoutError('ack lost'))
     return result
    drive.call=unreliable
    sink=dp.Sink(drive,'staging','prepared',lambda:True)
    data=b'prepared'*(dp.CHUNK//8+20);sink.write(0,'.mp4',data)
    result=sink.finish()['0']
    self.assertTrue(lost[0]);self.assertEqual(drive.files[result['id']]['data'],data)
    self.assertEqual(drive.files['source']['data'],b'original')
 def test_unacknowledged_chunk_is_replayed_once(self):
  original=self.d.call;failed=[False]
  def unreliable(method,url,body=None,headers=None):
   if method=='PUT' and not (headers or {}).get('Content-Range','').startswith('bytes */') and not failed[0]:
    failed[0]=True;raise urllib.error.URLError(TimeoutError())
   return original(method,url,body,headers)
  self.d.call=unreliable;sink=dp.Sink(self.d,'staging','prepared',lambda:True)
  sink.write(0,'.mp4',b'prepared');result=sink.finish()['0']
  self.assertEqual(self.d.files[result['id']]['data'],b'prepared')
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
 def test_unsupported_dolby_vision_is_kept_without_endless_background_retries(self):
  def unsupported(*args):raise RuntimeError('This Dolby Vision codec needs RPU remapping; original retained')
  self.n.convert_to=unsupported
  self.assertFalse(self.q.process_one())
  self.assertTrue(self.q.state['jobs']['slot']['blocked'])
  self.assertFalse(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_end_to_end_queue_writes_no_local_media_and_marks_ready(self):
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'prepared video');self.assertTrue(prep.ready(self.d.meta('source')))
  self.assertEqual(list(self.q.work.iterdir()),[]);self.assertNotIn('temp-1',self.d.files)
  self.assertEqual([c[1].split('/files/')[1] for c in self.d.calls if c[0]=='DELETE'],['temp-1'])
 def test_cancel_keeps_original_and_retry_restarts_generation(self):
  self.n.fail=True;self.assertFalse(self.q.process_one());self.assertEqual(self.d.files['source']['data'],b'original')
  self.n.fail=False;self.assertTrue(self.q.process_one());self.assertEqual(self.n.calls,2)
 def test_bad_output_keeps_original_untagged(self):
  self.n.bad=True;self.assertFalse(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'original');self.assertFalse(prep.ready(self.d.meta('source')))
 def test_invalid_completed_temp_is_regenerated_on_retry(self):
  self.n.bad=True;self.assertFalse(self.q.process_one());self.n.bad=False
  self.q.state['jobs']['slot']['retry_after']=0
  self.assertTrue(self.q.process_one());self.assertEqual(self.n.calls,2)

 def test_transient_verification_failure_reuses_valid_completed_temp(self):
  verify=self.n.verify
  self.n.verify=lambda *args:(_ for _ in ()).throw(OSError('network'))
  self.assertFalse(self.q.process_one());self.n.verify=verify
  self.q.state['jobs']['slot']['retry_after']=0
  self.assertTrue(self.q.process_one());self.assertEqual(self.n.calls,1)

 def test_cleanup_failure_retries_without_reencoding_or_deleting_original(self):
  call=self.d.call;fail=[True]
  def failing(method,*args,**kwargs):
   if method=='DELETE' and fail[0]:fail[0]=False;return 500,{},b''
   return call(method,*args,**kwargs)
  with patch.object(self.d,'call',side_effect=failing):self.assertTrue(self.q.process_one())
  self.assertTrue(prep.ready(self.d.meta('source')));self.assertIn('temp-1',self.d.files)
  self.assertFalse(self.q.process_one());self.assertNotIn('temp-1',self.d.files);self.assertEqual(self.n.calls,1)
  self.assertIn('source',self.d.files)

 def test_cleanup_journal_survives_restart_and_library_rescan(self):
  with patch.object(dp,'discard',side_effect=SystemExit('simulated process exit')):
   with self.assertRaises(SystemExit):self.q.process_one()
  self.assertTrue(prep.ready(self.d.meta('source')));self.assertIn('temp-1',self.d.files)
  q=prep.Queue(self.tmp.name,self.d,self.n,stream=Stream())
  with patch.object(prep.library_scan,'remote_files',return_value=[self.d.meta('source')]):q.scan(force=True)
  self.assertNotIn('slot',q.state['jobs'])
  self.assertFalse(q.process_one());self.assertNotIn('temp-1',self.d.files)
  self.assertEqual(q.state['staging_cleanup'],[]);self.assertEqual(self.n.calls,1)

 def test_changed_source_rescan_journals_unused_output_before_removing_its_job(self):
  self.n.verify=lambda *args:(_ for _ in ()).throw(OSError('network'))
  self.assertFalse(self.q.process_one());self.assertIn('temp-1',self.d.files)
  self.d.files['source'].update(data=b'changed original',version='2')
  with patch.object(prep.library_scan,'remote_files',return_value=[self.d.meta('source')]):self.q.scan(force=True)
  self.assertNotIn('slot',self.q.state['jobs']);self.assertIn('temp-1',self.q.state['staging_cleanup'])
  for job in self.q.state['jobs'].values():job['kept']=True
  self.assertFalse(self.q.process_one());self.assertNotIn('temp-1',self.d.files)
  self.assertEqual(self.d.files['source']['data'],b'changed original')
 def test_keep_original_cleans_unused_output_without_starting_another_conversion(self):
  self.n.verify=lambda *args:(_ for _ in ()).throw(OSError('network'))
  self.assertFalse(self.q.process_one());self.assertIn('temp-1',self.d.files)
  prep.request(self.tmp.name,'keep','source')
  self.assertFalse(self.q.process_one());self.assertNotIn('temp-1',self.d.files)
  self.assertEqual(self.d.files['source']['data'],b'original');self.assertEqual(self.n.calls,1)

if __name__=='__main__':unittest.main()
