"""Exercise real adaptive preparation uploads, ACK recovery and independent heartbeat/UI transport evidence."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import drive_prepare as dp,prepare_downloads as prep,preparation_runtime as runtime,work_state
from test_drive_prepare import Drive
MB=1024*1024

class Transfers(unittest.TestCase):
 def sink(self,drive=None,**kw):
  sink=dp.Sink(drive or Drive(),'staging','p',lambda:True,**kw);self.addCleanup(sink.close);return sink
 def test_slow_conversion_upload_shrinks_without_changing_media_or_resume_window(self):
  now=[0.];drive=Drive();original=drive.call;sizes=[]
  def slow(method,url,body=None,headers=None):
   if method=='PUT' and body:
    # ISSUE-164: pieces aim at ~10 s and shrink past 15 s, so the slow line here is 0.1 MB/s (2 MB took 20 s).
    sizes.append(len(body));now[0]+=.1 if len(sizes)<=3 else len(body)/(.1*MB)
   return original(method,url,body,headers)
  drive.call=slow;sink=self.sink(drive,clock=lambda:now[0],background=False)
  data=b'x'*(dp.MAIN_CHUNK+1);sink.write(0,'.mp4',data);item=sink.finish()['0']
  self.assertEqual(sizes[0],MB);self.assertIn(2*MB,sizes);self.assertEqual(sizes[4],MB)
  self.assertTrue(all(n%dp.STEP==0 for n in sizes[:-1]));self.assertEqual(sum(sizes),len(data))
  self.assertEqual(drive.files[item['id']]['data'],data);self.assertEqual(drive.files['source']['data'],b'original')
  self.assertEqual(dp.MARK_CAP,256*MB);self.assertEqual(dp.MAIN_CHUNK,32*MB)
 def test_more_than_eight_successful_small_pieces_do_not_exhaust_retry_budget(self):
  sink=self.sink(background=False);sink._new_track(0,None,0)
  t=sink.tracks[0];import driveupload
  t['chunks']=driveupload.StreamChunks(limit=MB)
  data=b'x'*(12*MB+123);t['buffer'].extend(data);t['md5'].update(data)
  sink._send(t,len(data),final=True)
  self.assertEqual(t['offset'],len(data));self.assertEqual(sink.drive.files[t['result']['id']]['data'],data)
 def test_lost_ack_does_not_repeat_confirmed_bytes_with_adaptive_chunks(self):
  drive=Drive();original=drive.call;lost=[False];now=[0.]
  def lost_ack(method,url,body=None,headers=None):
   if method=='PUT' and body:now[0]+=20
   out=original(method,url,body,headers)
   if method=='PUT' and body and not lost[0]:lost[0]=True;raise TimeoutError('ACK lost')
   return out
  drive.call=lost_ack;sink=self.sink(drive,clock=lambda:now[0],sleep=lambda n:None,background=False)
  data=b'x'*(16*MB+123);sink.write(0,'.mp4',data);result=sink.finish()['0']
  self.assertTrue(lost[0]);self.assertEqual(drive.files[result['id']]['data'],data)
 def test_partial_ack_retries_only_unconfirmed_bytes(self):
  drive=Drive();original=drive.call;partial=[False]
  def half(method,url,body=None,headers=None):
   if method=='PUT' and body and not partial[0] and len(body)>=2*MB:
    partial[0]=True;start=int(headers['Content-Range'].split()[1].split('-')[0]);body=body[:MB]
    headers=dict(headers,**{'Content-Range':'bytes %d-%d/*'%(start,start+len(body)-1)})
   return original(method,url,body,headers)
  drive.call=half;sink=self.sink(drive,background=False)
  data=b'x'*(10*MB+123);sink.write(0,'.mp4',data);result=sink.finish()['0']
  self.assertTrue(partial[0]);self.assertEqual(drive.files[result['id']]['data'],data)
 def test_first_slow_ack_reports_a_real_speed_and_resume_offset_is_not_counted_as_new_bytes(self):
  now=[10.];sink=self.sink(clock=lambda:now[0]);sink._new_track(0,'https://upload.example/resume',50*MB)
  now[0]=42;sink._confirmed({'offset':58*MB},0)
  self.assertAlmostEqual(sink.rate(),.25*MB)
 def test_full_queue_with_failed_uploader_does_not_hang_finalization(self):
  sink=self.sink();t=sink._new_track(0,'https://upload.example/x',0)
  t['error']=RuntimeError('upload failed')
  with self.assertRaisesRegex(RuntimeError,'upload failed'):sink.finish()

class TransportStatus(unittest.TestCase):
 def test_heartbeat_updates_wait_and_ack_without_another_native_callback(self):
  now=[100.];sink=dp.Sink(Drive(),'staging','p',lambda:True,clock=lambda:now[0]);self.addCleanup(sink.close)
  with tempfile.TemporaryDirectory() as profile:
   state={'jobs':{},'current':{'title':'Lanterns.S01E06.mkv','running':True,'stage':'Converting','progress':8,'updated':100}}
   prep.save(profile,state)
   with runtime.Lease(profile,stats=sink.stats,clock=lambda:now[0],every=60) as lease:
    lease.phase('Converting',True,state['current']['title']);sink.finishing=True;sink.uploads[1]=100
    now[0]=113;lease.pulse()
    current=prep.snapshot(profile,now=lambda:now[0])['current']
    self.assertEqual(current['stage'],'Waiting for Drive');self.assertEqual(current['progress'],8)
    model=work_state._conversion(state,runtime.read(profile,clock=lambda:now[0]),now[0])
    self.assertEqual(model['step'],'Waiting for Drive');self.assertEqual(model['rate'],0)
    sink.marks=[(100,0)];now[0]=132;sink._confirmed({'offset':8*MB},0);sink.uploads[1]=132;lease.pulse()
    current=prep.snapshot(profile,now=lambda:now[0])['current']
    self.assertEqual(current['stage'],'Uploading to Google Drive');self.assertEqual(current['out_bytes'],8*MB)
    self.assertAlmostEqual(current['rate'],.25*MB);self.assertEqual(current['eta_s'],0)
 def test_upload_state_does_not_replace_an_explicit_pause(self):
  c=runtime.current({'running':True,'paused':True,'stage':'Paused by you'},
                    {'phase':'Paused by you','known':False,'updated':100,'transfer_phase':'waiting_drive','up_rate':123})
  self.assertEqual(c['stage'],'Paused by you')
 def test_an_old_upload_rate_does_not_override_verification(self):
  c=runtime.current({'running':True,'stage':'Verifying the Drive file','rate':0},
                    {'phase':'Verifying the Drive file','known':False,'updated':100,'transfer_phase':'','up_rate':123})
  self.assertEqual(c['stage'],'Verifying the Drive file');self.assertEqual(c['rate'],0)

if __name__=='__main__':unittest.main()
