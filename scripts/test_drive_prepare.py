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
  import threading
  d=Drive();orig=d.call;puts=[];entered=threading.Event();release=threading.Event();done=threading.Event();errors=[]
  def slow(method,url,body=None,headers=None):
   if method=='PUT' and body:
    entered.set()
    if not release.wait(10):raise TimeoutError('Test upload was not released')
    puts.append(len(body))
   return orig(method,url,body,headers)
  d.call=slow;sink=dp.Sink(d,'staging','prepared',lambda:True)
  piece=b'z'*(dp.MAIN_CHUNK)
  def produce():
   try:sink.write(0,'.mp4',piece);sink.write(0,'.mp4',piece);sink.write(0,'.mp4',b'end')
   except BaseException as error:errors.append(error)
   finally:done.set()
  producer=threading.Thread(target=produce,daemon=True);producer.start()
  try:
   self.assertTrue(entered.wait(5),'background uploader started')
   self.assertTrue(done.wait(5),'converter returned while the network upload is still blocked')
   self.assertFalse(errors)
   self.assertFalse(release.is_set())
  finally:release.set();producer.join(5)
  self.assertFalse(producer.is_alive())
  result=sink.finish()['0']
  self.assertEqual(d.files[result['id']]['data'],piece*2+b'end')
  self.assertTrue(all(0<n<=dp.MAIN_CHUNK for n in puts))   # ISSUE-202: movie pieces up to 32 MB
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
 def test_once_every_unit_is_made_the_rest_reads_as_the_upload(self):
  # ISSUE-202 (build-350 log): 47 of 47 units made, then "Converting 79%" for 20 minutes while the movie went up.
  sink=dp.Sink(Drive(),'staging','p',lambda:True)
  sink.made,sink.sent=400*1024*1024,100*1024*1024
  self.assertNotIn('upload_left',sink.stats());self.assertEqual(sink.stats()['transfer_phase'],'')
  sink.made_all=True;stats=sink.stats()
  self.assertEqual((stats['transfer_phase'],stats['upload_left'],stats['upload_total']),('uploading',300*1024*1024,400*1024*1024))
 def test_movie_pieces_may_grow_to_32_mb_and_start_at_1_mb(self):
  dp.learn_piece(0)   # nothing learned from an earlier file
  sink=dp.Sink(Drive(),'staging','p',lambda:True)
  t={'offset':0,'buffer':bytearray(),'track':0,'url':'u','md5':None}
  sink.closed=True
  try:sink._send_parts(t,0,False)
  except Exception:pass
  self.assertEqual((t['chunks'].limit,t['chunks'].current),(dp.MAIN_CHUNK,1024*1024))
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
 def test_a_track_mp4_cannot_keep_is_kept_as_it_is_with_plain_words(self):
  # Owner screenshot (2026-11-13, Naruto Shippuuden S1 E16): "Video preparation paused: This file has tracks MP4 cannot
  # preserve; original retained". Nothing was paused: it is kept as it is, once, in plain words.
  notes=[];self.q.notify=lambda kind,title,text:notes.append((kind,title,text))
  def refused(*args,**kwargs):raise RuntimeError('This file has tracks MP4 cannot preserve; original retained')
  self.n.convert_to=refused
  self.assertFalse(self.q.process_one());self.assertFalse(self.q.process_one())
  job=self.q.state['jobs']['slot'];self.assertTrue(job['blocked'])
  self.assertEqual(notes,[('info','Kept as it is',"Film still plays in Kodi as it is; it has DVD picture subtitles or a second video track an MP4 can't keep, so it isn't made ready for AirPlay.")])
  self.assertEqual(self.d.files['source']['data'],b'original')
 def test_repair_puts_a_kept_video_back_in_the_queue(self):
  # ISSUE-226 / P1 (owner log a1729c16): Repair and Repair All sent a retry that left blocked=True, so nothing started.
  notes=[];self.q.notify=lambda kind,title,text:notes.append((kind,title,text))
  def refused(*args,**kwargs):raise RuntimeError('This file has tracks MP4 cannot preserve; original retained')
  self.n.convert_to=refused
  self.assertFalse(self.q.process_one())
  job=self.q.state['jobs']['slot'];self.assertTrue(job['blocked']);self.assertTrue(job['kept_told'])
  job.update(image_subs_retried=True,hdr_retried=True,repack_failed=True)
  queued=lambda:[s for s,j in self.q.state['jobs'].items() if j.get('status') not in ('done','superseded') and not j.get('blocked') and not j.get('kept')]
  self.assertEqual(queued(),[])
  prep.request(self.tmp.name,'retry','source');self.assertTrue(self.q.apply_requests())
  self.assertEqual(queued(),['slot'])                                                    # the queue picks it again
  for name in prep.FORGIVEN:self.assertNotIn(name,self.q.state['jobs']['slot'])
  ran=[];self.n.convert_to=lambda *a,**k:ran.append(1) or (_ for _ in ()).throw(RuntimeError('This file has tracks MP4 cannot preserve; original retained'))
  self.assertFalse(self.q.process_one());self.assertEqual(ran,[1])                      # it really ran again
  self.assertEqual(len(notes),2)                                                         # and said so again
  prep.request(self.tmp.name,'now','source');self.q.apply_requests()
  self.assertEqual([j.get('blocked') for j in self.q.state['jobs'].values()],[None])     # Start now clears it too
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
 def test_network_trouble_waits_and_carries_on_without_counting(self):
  # ISSUE-198 (owner log b3c5d6eb, build 350): Drive reads stopped for 5 minutes, then "Source read: Input/output error"
  # failed the conversion; network trouble now waits 15 s and carries on, then the conversion finishes.
  calls={'n':0};real=self.n.convert_to
  def flaky(*args,**kwargs):
   calls['n']+=1
   if calls['n']==1:raise RuntimeError('Source read: Input/output error')
   return real(*args,**kwargs)
  self.n.convert_to=flaky
  self.assertFalse(self.q.process_one());job=self.q.state['jobs']['slot']
  self.assertEqual((job['status'],job.get('attempts',0),job['net_attempts']),('waiting',0,1))
  self.assertLessEqual(job['retry_after']-self.q.clock(),15)
  job['retry_after']=0
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(self.q.state['jobs']['slot']['status'],'done')
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
  # ISSUE-238: a failed final check stops the video after one conversion; Repair (retry) makes it again.
  self.n.bad=True;self.assertFalse(self.q.process_one());self.n.bad=False
  self.assertTrue(self.q.state['jobs']['slot']['blocked']);self.assertFalse(self.q.process_one());self.assertEqual(self.n.calls,1)
  prep.request(self.tmp.name,'retry','source');self.assertTrue(self.q.apply_requests())
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


class FinalCheck(unittest.TestCase):
 """Owner log (build 368): 30 failed preparations for Naruto Shippuuden, each one a full read and write on Drive."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.d=Drive();self.n=Native();self.q=prep.Queue(self.tmp.name,self.d,self.n,stream=Stream())
  self.q.state['jobs']={'slot':{'source':prep.metadata(self.d,'source'),'status':'waiting'}}
  self.notes=[];self.q.notify=lambda kind,title,text:self.notes.append((kind,title,text))
  self.open=patch('prepare_cloud.urllib.request.urlopen',side_effect=lambda req,timeout:self.d.open_at(req.full_url.split('/')[-2],int(req.headers['Range'][6:-1])))
  self.open.start();self.addCleanup(self.open.stop)
 def job(self):return self.q.state['jobs']['slot']
 def test_a_wrong_picture_stops_after_one_conversion_and_says_which_check(self):
  self.n.probe=lambda path:dict(ready='temp-' in path,width=1920 if 'temp-' in path else 3840,height=1080 if 'temp-' in path else 2160,hdr=True,duration=1300)
  self.assertFalse(self.q.process_one())
  job=self.job();self.assertTrue(job['blocked']);self.assertTrue(job['verify_failed']);self.assertNotIn('repack_failed',job)
  self.assertIn('The prepared picture is 1920x1080, the original is 3840x2160',job['error']);self.assertIn('original retained',job['error'])
  self.assertNotIn('did not preserve',job['error'])
  self.assertFalse(self.q.process_one());self.assertFalse(self.q.process_one());self.assertEqual(self.n.calls,1)   # not made again
  self.assertEqual(len(self.notes),1);self.assertEqual(self.notes[0][:2],('info','Kept as it is'))
  self.assertEqual(self.d.files['source']['data'],b'original');self.assertNotIn('temp-1',self.d.files)
  self.assertEqual([p['name'] for p in prep.preparation_problems(self.q.state)],['Film.2160p.mkv'])   # Download problems lists it
 def test_not_ready_and_hdr_changes_have_their_own_words(self):
  import prepare_cloud
  before=dict(width=3840,height=2160,hdr=True)
  self.assertIn('not marked ready',prepare_cloud.verify_problem(before,dict(before,ready=False)))
  self.assertIn('HDR changed',prepare_cloud.verify_problem(before,dict(before,ready=True,hdr=False)))
  self.assertEqual(prepare_cloud.verify_problem(before,dict(before,ready=True)),'')
 def test_a_repack_that_plays_reads_as_ready_and_repair_clears_it(self):
  import library_files
  self.n.probe=lambda path:dict(ready=False,width=3840,height=2160,hdr=True,duration=1300)
  self.job()['repack']=True
  self.assertFalse(self.q.process_one());job=self.job()
  self.assertTrue(job['blocked'] and job['repack_failed'] and job['verify_failed'])
  self.assertEqual(library_files.file_state({'id':'source'},{'source':job},{})['state'],library_files.READY)
  self.assertEqual(prep.preparation_problems(self.q.state),[])
  prep.request(self.tmp.name,'retry','source');self.assertTrue(self.q.apply_requests())
  for name in ('blocked','verify_failed','verify_told','repack_failed'):self.assertNotIn(name,self.job())
  self.n.probe=lambda path:dict(ready='temp-' in path,width=3840,height=2160,hdr=True,duration=1300)
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
 def test_a_checksum_mismatch_stops_too(self):
  real=prep.metadata
  def lying(drive,key):
   got=real(drive,key)
   if key.startswith('temp-'):got['md5Checksum']='0'*32
   return got
  with patch.object(prep,'metadata',lying):self.assertFalse(self.q.process_one())
  self.assertTrue(self.job()['blocked']);self.assertIn('checksum differs; original retained',self.job()['error'])
 def test_network_trouble_in_the_final_check_still_waits_and_retries(self):
  self.n.probe=lambda path:(_ for _ in ()).throw(RuntimeError('Source read: Input/output error'))
  self.assertFalse(self.q.process_one());job=self.job()
  self.assertFalse(job.get('blocked'));self.assertEqual((job['status'],job.get('attempts',0)),('waiting',0))

 def test_the_converters_own_check_failing_stops_after_one_too(self):
  # ISSUE-238: native.verify (duration, tracks, seeks) failing repeated whole conversions; it stops after one now.
  self.n.verify=lambda source,target:(_ for _ in ()).throw(RuntimeError('Prepared video duration differs from the source'))
  self.assertFalse(self.q.process_one());job=self.job()
  self.assertTrue(job['blocked'] and job['verify_failed']);self.assertIn('duration differs',job['error'])
  self.assertFalse(self.q.process_one());self.assertEqual(self.n.calls,1)
  self.assertNotIn('temp-1',self.d.files)
 def test_the_converters_check_during_network_trouble_waits(self):
  self.n.verify=lambda source,target:(_ for _ in ()).throw(RuntimeError('Prepared Drive file validation failed'))
  self.q.stream.stats=lambda:{'read_error':'Connection reset by peer'}
  self.assertFalse(self.q.process_one());job=self.job()
  self.assertFalse(job.get('blocked'));self.assertEqual((job['status'],job.get('attempts',0)),('waiting',0))

class MobileData(unittest.TestCase):
 """Owner log (build 368): the phone was on mobile data 13:31-13:40 while preparation read and wrote a whole movie."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.d=Drive();self.n=Native();self.q=prep.Queue(self.tmp.name,self.d,self.n,stream=Stream())
  self.q.state['jobs']={'slot':{'source':prep.metadata(self.d,'source'),'status':'waiting'}}
  self.link='cellular';self.q.link=lambda:self.link
  self.open=patch('prepare_cloud.urllib.request.urlopen',side_effect=lambda req,timeout:self.d.open_at(req.full_url.split('/')[-2],int(req.headers['Range'][6:-1])))
  self.open.start();self.addCleanup(self.open.stop)
 def test_nothing_starts_on_mobile_data_and_it_starts_on_wifi(self):
  self.assertFalse(self.q.process_one());self.assertEqual(self.n.calls,0);self.assertTrue(self.q.state['wifi_hold'])
  self.link='wifi'
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(self.n.calls,1);self.assertNotIn('wifi_hold',self.q.state)
 def test_start_now_overrides_mobile_data(self):
  prep.request(self.tmp.name,'now','source');self.q.apply_requests()
  with patch.object(prep.phone_space,'free',return_value=0):self.assertTrue(self.q.process_one())
  self.assertEqual(self.n.calls,1)
 def test_a_running_job_stops_cleanly_when_the_phone_goes_to_mobile_data(self):
  self.link='wifi';seen=[]
  def convert(source,sink,keep,progress,*a,**k):
   self.n.calls+=1;self.link='cellular'
   if not keep():raise driveupload.Stop('stopped')
   seen.append('kept going')
  self.n.convert_to=convert
  self.assertFalse(self.q.process_one());job=self.q.state['jobs']['slot']
  self.assertEqual((seen,job['status'],job['retry_after'],job.get('attempts',0)),([],'paused',0,0))
  self.assertFalse(self.q.process_one());self.assertEqual(self.n.calls,1);self.assertTrue(self.q.state['wifi_hold'])
 def test_the_status_says_waiting_for_wifi(self):
  import work_state as ws
  snap=ws.build({'prep':dict(self.q.state,wifi_hold=True)},1000.0)
  self.assertIn('Waiting for Wi-Fi',snap['wait']);self.assertEqual(snap['mode'],ws.NETWORK);self.assertIn('Waiting for Wi-Fi',snap['headline'])
  self.assertNotIn('Waiting for Wi-Fi',ws.build({'prep':self.q.state},1000.0)['wait'])

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

class LearnedPieceSize(unittest.TestCase):
 """Owner log (2026-11-13): every file started again at 1 MB; the last good piece size now carries to the next file."""
 def run_file(self,drive,pieces,sink=None,clock=None):
  sink=sink or dp.Sink(drive,'p','x',lambda:True)
  t=dict(url='u',offset=0,buffer=bytearray(),md5=None,name='x',chunk=1,track=0)
  for n in range(pieces):
   t['buffer'].extend(b'a'*(40*1024*1024));sink._send(t,len(t['buffer']),final=False,sleep=lambda s:None)
  return t
 def test_next_file_starts_where_the_last_one_ended_and_a_failure_forgets_it(self):
  class D:
   def __init__(s,fail=False):s.got=0;s.sizes=[];s.fail=fail
   def call(s,method,url,body=b'',headers=None):
    if headers['Content-Range'].startswith('bytes */'):return 308,{'Range':'bytes=0-%d'%(s.got-1)} if s.got else {},b''
    if s.fail:s.fail=False;return 503,{},b''
    s.sizes.append(len(body));s.got+=len(body);return 308,{'Range':'bytes=0-%d'%(s.got-1)},b''
  with patch.object(dp,'_link_kind',lambda:'wifi'):
   dp.learn_piece(0)
   first=D();self.run_file(first,1)
   self.assertEqual(first.sizes[0],1024*1024)               # nothing learned yet: starts at 1 MB
   dp.learn_piece(16*1024*1024)
   second=D();self.run_file(second,1)
   self.assertEqual(second.sizes[0],16*1024*1024)           # learned size carries over
   dp.learn_piece(64*1024*1024*1024)
   third=D();self.run_file(third,1)
   self.assertEqual(third.sizes[0],dp.MAIN_CHUNK)           # never above the cap
   dp.learn_piece(512*1024)
   fourth=D();self.run_file(fourth,1)
   self.assertEqual(fourth.sizes[0],1024*1024)              # never below 1 MB
   dp.learn_piece(16*1024*1024)
   failing=D(fail=True)
   with self.assertRaises(RuntimeError):
    sink=dp.Sink(failing,'p','x',lambda:True);t=dict(url='u',offset=0,buffer=bytearray(b'a'*(40*1024*1024)),md5=None,name='x',chunk=1,track=0)
    sink._send_parts(t,len(t['buffer']),False,attempts=1,sleep=lambda s:None)
   self.assertEqual(dp.learned_piece(dp.MAIN_CHUNK),8*1024*1024)   # ISSUE-240: a dropped piece halves it, not 1 MB
  dp.learn_piece(0)
 def test_a_dropped_connection_halves_the_piece_and_it_grows_back(self):
  # ISSUE-240: drops used to send every piece back to 1 MB.
  class D:
   def __init__(s,drops):s.got=0;s.sizes=[];s.drops=list(drops);s.n=0
   def call(s,method,url,body=b'',headers=None):
    if headers['Content-Range'].startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(s.got-1)} if s.got else {}),b''
    s.n+=1
    if s.n in s.drops:raise ConnectionError('The network connection was lost (-1005)')
    s.sizes.append(len(body));s.got+=len(body);return 308,{'Range':'bytes=0-%d'%(s.got-1)},b''
  MB=1024*1024
  with patch.object(dp,'_link_kind',lambda:'wifi'):
   dp.learn_piece(16*MB)
   drive=D(drops=[2]);self.run_file(drive,2)
   self.assertEqual(drive.sizes[:2],[16*MB,8*MB])             # one drop: half, not 1 MB
   self.assertEqual(max(drive.sizes),16*MB)                   # grows back after fast pieces
   self.assertGreaterEqual(dp.learned_piece(dp.MAIN_CHUNK),8*MB)
  dp.learn_piece(0)
 def test_steady_pieces_grow_toward_ten_seconds(self):
  # ISSUE-246: on a shared line every 4 MB piece took ~8 s, so pieces never grew (three under 6 s were needed).
  MB=1024*1024
  now=[0.0]
  class D:
   def __init__(s):s.got=0;s.sizes=[]
   def call(s,method,url,body=b'',headers=None):
    if headers['Content-Range'].startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(s.got-1)} if s.got else {}),b''
    now[0]+=len(body)/(0.5*MB)          # 0.5 MB/s: 4 MB takes 8 s
    s.sizes.append(len(body));s.got+=len(body);return 308,{'Range':'bytes=0-%d'%(s.got-1)},b''
  with patch.object(dp,'_link_kind',lambda:'wifi'):
   dp.learn_piece(4*MB)
   drive=D();sink=dp.Sink(drive,'p','x',lambda:True,clock=lambda:now[0])
   self.run_file(drive,1,sink=sink)
   self.assertEqual(sum(drive.sizes),40*MB);self.assertEqual(drive.sizes[0],4*MB)
   self.assertEqual(drive.sizes[1],5*MB)       # 4 MB in 8 s -> 5 MB (about ten seconds at that speed)
   self.assertTrue(all(b>=a for a,b in zip(drive.sizes,drive.sizes[1:-1])))
  dp.learn_piece(0)
 def test_a_change_of_link_forgets_it_and_sidecars_do_not_use_it(self):
  kind={'now':'wifi'}
  with patch.object(dp,'_link_kind',lambda:kind['now']):
   dp.learn_piece(16*1024*1024)
   self.assertEqual(dp.learned_piece(dp.MAIN_CHUNK),16*1024*1024)
   kind['now']='cellular'
   self.assertEqual(dp.learned_piece(dp.MAIN_CHUNK),0)
  dp.learn_piece(0)

if __name__=='__main__':unittest.main()
