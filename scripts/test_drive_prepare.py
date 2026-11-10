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
  self.second_upload=False
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
   if method=='PATCH':self.second_upload=True
   self.number+=1;session='https://upload.example/%d'%self.number
   target=None if method=='POST' else url.split('/files/')[1].split('?')[0]
   self.sessions[session]=dict(target=target,meta=dict(json.loads(body),parents=json.loads(body).get('parents',['staging'])),data=b'')
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
   key=url.split('/files/')[1].split('?')[0]
   if key not in self.files:return 404,{},b''
   query=dict(urllib.parse.parse_qsl(url.split('?',1)[1])) if '?' in url else {}
   f=self.files[key];change=json.loads(body)
   if 'appProperties' in change:f['appProperties']=dict(f.get('appProperties') or {},**change.pop('appProperties'))
   f.update(change)
   if query.get('addParents'):f['parents']=[x for x in f.get('parents',[]) if x!=query.get('removeParents')]+[query['addParents']]
   return 200,{},json.dumps(self.meta(key)).encode()
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
   self.assertLessEqual(len(sink.tracks[0]['buffer']),dp.MAIN_CHUNK)
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
    data=b'prepared'*(dp.MAIN_CHUNK//8+20);sink.write(0,'.mp4',data)
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

class BackgroundUpload(unittest.TestCase):
 """Build 177 (build-176 log: upload busy 270 of 294 s at ~3 MB/s, the converter waiting on each 8 MB piece)."""
 def test_converter_does_not_wait_for_a_slow_upload(self):
  import time as _t
  d=Drive();orig=d.call;puts=[]
  def slow(method,url,body=None,headers=None):
   if method=='PUT' and body:_t.sleep(1.5);puts.append(len(body))   # one piece takes 1.5 s to go up
   return orig(method,url,body,headers)
  d.call=slow;sink=dp.Sink(d,'staging','prepared',lambda:True)
  piece=b'z'*(dp.MAIN_CHUNK)
  t0=_t.monotonic();sink.write(0,'.mp4',piece);sink.write(0,'.mp4',piece);sink.write(0,'.mp4',b'end')
  self.assertLess(_t.monotonic()-t0,1.0)   # handed over, not uploaded in this thread (that alone would take 1.5 s)
  result=sink.finish()['0']
  self.assertEqual(d.files[result['id']]['data'],piece*2+b'end')
  self.assertTrue(all(0<n<=8*1024*1024 for n in puts))
  self.assertEqual(sum(puts),dp.MAIN_CHUNK*2+3);self.assertEqual(sink.sent,dp.MAIN_CHUNK*2+3)
 def test_upload_error_reaches_the_converter_and_original_stays(self):
  d=Drive();orig=d.call
  def broken(method,url,body=None,headers=None):
   if method=='PUT':return 400,{},b''
   return orig(method,url,body,headers)
  d.call=broken;sink=dp.Sink(d,'staging','prepared',lambda:True,sleep=lambda s:None)
  import time as _t
  with self.assertRaises(RuntimeError):
   for _ in range(8):sink.write(0,'.mp4',b'q'*dp.MAIN_CHUNK);_t.sleep(0.05)
   sink.finish()
  self.assertEqual(d.files['source']['data'],b'original')
 def test_close_ends_the_thread(self):
  sink=dp.Sink(Drive(),'staging','prepared',lambda:True);sink.write(0,'.mp4',b'a'*(dp.MAIN_CHUNK+1))
  sink.close();self.assertFalse(sink.tracks[0]['thread'].is_alive())
 def test_rate_over_recent_seconds(self):
  now=[0.0];sink=dp.Sink(Drive(),'staging','p',lambda:True,clock=lambda:now[0])
  t={'offset':0}
  for i in range(5):now[0]=i*2.0;t['offset']=i*16*1024*1024;sink._confirmed(t,0)
  self.assertAlmostEqual(sink.rate(),8*1024*1024)

class Native:
 outputs=True;streams=True;keeps_image_subs=True
 def __init__(self):self.calls=0;self.fail=False;self.bad=False
 def probe(self,path):return dict(ready='temp-' in path,width=3840,height=2160,hdr=True,duration=1300)
 def convert_to(self,source,sink,keep,progress,paused=None,waiting=None,resume=None):
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
  def unsupported(*args,**kwargs):raise RuntimeError('This Dolby Vision codec needs RPU remapping; original retained')
  self.n.convert_to=unsupported
  self.assertFalse(self.q.process_one())
  self.assertTrue(self.q.state['jobs']['slot']['blocked'])
  self.assertFalse(self.q.process_one())
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_failed_faster_start_is_not_retried_for_ever(self):
  # Build-192 log 13:55:08: Fall 2's re-pack failed at 22 % on "MP4 packet: Invalid argument"; each retry restarts at 0 %.
  notes=[];self.q.notify=lambda kind,title,text:notes.append((kind,title,text))
  def refused(*args,**kwargs):raise RuntimeError('MP4 packet: Invalid argument')
  self.n.convert_to=refused
  self.q.state['jobs']['slot']['repack']=True
  self.assertFalse(self.q.process_one())
  job=self.q.state['jobs']['slot'];self.assertTrue(job['blocked']);self.assertTrue(job['repack_failed'])
  self.assertEqual(notes,[('info','Kept as it is',"Film still plays in Kodi and on AirPlay; it couldn't be made to start faster.")])
  self.assertFalse(self.q.process_one());self.assertEqual(len(notes),1)          # not tried again
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_same_error_on_a_first_conversion_is_retried(self):
  def refused(*args,**kwargs):raise RuntimeError('MP4 packet: Invalid argument')
  self.n.convert_to=refused
  self.assertFalse(self.q.process_one());job=self.q.state['jobs']['slot']
  self.assertFalse(job.get('blocked'));self.assertGreater(job['retry_after'],0)   # a movie that is not ready yet keeps trying
 def test_end_to_end_queue_writes_no_local_media_and_marks_ready(self):
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  # Build 181: uploaded once. The prepared file takes the original's place; the original goes to the bin.
  new=self.d.meta('temp-1')
  self.assertEqual(self.d.files['temp-1']['data'],b'prepared video');self.assertTrue(prep.ready(new))
  self.assertEqual((new['name'],new['parents']),('Film.2160p.mp4',['movies']))
  self.assertTrue(self.d.files['source'].get('trashed'));self.assertEqual(self.d.files['source']['data'],b'original')
  self.assertFalse(self.d.second_upload);self.assertEqual([c for c in self.d.calls if c[0]=='DELETE'],[])
  self.assertEqual(self.q.state['jobs']['slot']['prepared_id'],'temp-1');self.assertEqual(list(self.q.work.iterdir()),[])
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

 def test_bin_failure_finishes_on_the_next_pass_without_reencoding(self):
  call=self.d.call;fail=[True]
  def failing(method,url,body=None,headers=None):
   if method=='PATCH' and body and b'trashed' in body and fail[0]:fail[0]=False;return 500,{},b''
   return call(method,url,body,headers)
  with patch.object(self.d,'call',side_effect=failing):self.assertFalse(self.q.process_one())
  job=self.q.state['jobs']['slot'];self.assertEqual(job['promoted'],'temp-1');self.assertTrue(prep.ready(self.d.meta('temp-1')))
  job['retry_after']=0
  self.assertTrue(self.q.process_one());self.assertTrue(self.d.files['source'].get('trashed'));self.assertEqual(self.n.calls,1)
  self.assertIn('temp-1',self.d.files)

 def test_exit_after_the_move_survives_restart(self):
  with patch.object(dp,'bin',side_effect=SystemExit('simulated process exit')):
   with self.assertRaises(SystemExit):self.q.process_one()
  self.assertTrue(prep.ready(self.d.meta('temp-1')));self.assertFalse(self.d.files['source'].get('trashed'))
  q=prep.Queue(self.tmp.name,self.d,self.n,stream=Stream())
  self.assertTrue(q.process_one());self.assertTrue(self.d.files['source'].get('trashed'))
  self.assertEqual(q.state['jobs']['slot']['status'],'done');self.assertEqual(self.n.calls,1);self.assertFalse(self.d.second_upload)

 def test_watch_request_follows_the_new_file(self):
  import debrid_drive
  debrid_drive.save(self.tmp.name,{'jobs':[{'hash':'h','files':[{'drive_id':'source','done':True}]}]})
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(debrid_drive.load(self.tmp.name)['jobs'][0]['files'][0]['drive_id'],'temp-1')

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


class PartialAcknowledgements(unittest.TestCase):
 """Owner (build 169 log): Interstellar failed after two hours: "Preparation upload did not acknowledge its byte range"."""
 def test_partial_keep_and_hiccup_carry_on(self):
  import drive_prepare
  class D:
   def __init__(s):s.got=b'';s.calls=0
   def call(s,method,url,body=b'',headers=None):
    s.calls+=1;cr=headers['Content-Range']
    if cr.startswith('bytes */'):return 308,{'Range':'bytes=0-%d'%(len(s.got)-1)} if s.got else {},b''
    a=int(cr[6:].split('-')[0])
    if s.calls==1:s.got+=body[:len(body)//2];return 308,{'Range':'bytes=0-%d'%(len(s.got)-1)},b''   # half kept
    if s.calls==2:return 503,{},b''                                                                     # hiccup
    s.got=s.got[:a]+body;return 308,{'Range':'bytes=0-%d'%(len(s.got)-1)},b''
  d=D();sink=drive_prepare.Sink(d,'p','x',lambda:True)
  t=dict(url='u',offset=0,buffer=bytearray(b'a'*1000),md5=None,name='x',chunk=1000)
  sink._send(t,1000,final=False,sleep=lambda s:None)
  self.assertEqual((t['offset'],len(t['buffer']),d.got),(1000,0,b'a'*1000))

if __name__=='__main__':unittest.main()
