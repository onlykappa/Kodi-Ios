"""r30 (owner: "lets fix restarting when its closed and have it keep progress"): the Drive side of carrying a
conversion on. Pieces end at KodiAirPlay's marks (rounded down to 256 KiB), a checkpoint is saved once Drive confirmed
such a piece, and a new run sends the kept bytes and then the converter's output from the mark into the same upload."""
import importlib.util,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(Path(__file__).resolve().parent)]
import drive_prepare as dp,resume_store,driveupload
from test_drive_prepare import Drive

STEP=dp.STEP
def mark(offset,tfra=(),sides=None):
 lines=['kr-resume 1','offset %d'%offset,'seq 7','layout 2/1/27/86018']+['side %d %d'%(k-1,v) for k,v in (sides or {}).items()]+list(tfra)
 return '\n'.join(lines)+'\n'

class Pieces(unittest.TestCase):
 def setUp(self):
  self.old=(dp.MAIN_CHUNK,dp.CHUNK,dp.MARK_CAP);dp.CHUNK=dp.MAIN_CHUNK=4*STEP;dp.MARK_CAP=12*STEP
  self.tmp=tempfile.TemporaryDirectory()
 def tearDown(self):dp.MAIN_CHUNK,dp.CHUNK,dp.MARK_CAP=self.old;self.tmp.cleanup()
 def run_until(self,drive,data,marks,stop_at,saved,background=False):
  """A first run: the movie in 100 KB writes, marks as the converter gives them; it stops after stop_at bytes."""
  sink=dp.Sink(drive,'staging','slot',lambda:True,background=background,spool=self.tmp.name,on_checkpoint=saved.append)
  for at in range(0,stop_at,100*1024):
   for m in [m for m in marks if at<=m<at+100*1024]:sink.mark_from(mark(m,['tfra 1 %d %d'%(m,m)]))
   sink.write(0,'.mp4',data[at:min(at+100*1024,stop_at)])
  return sink
 def test_pieces_end_at_marks_and_a_new_run_carries_on(self):
  drive=Drive();data=os.urandom(40*STEP+12345);marks=[5*STEP+777,11*STEP+3,23*STEP+999]
  saved=[];sink=self.run_until(drive,data,marks,30*STEP,saved)
  self.assertTrue(saved);cp=saved[-1]
  sent=len(drive.sessions[cp['url']]['data'])
  self.assertEqual(sent%STEP,0);self.assertEqual(cp['offset'],sent)
  m=cp['offset']+len(cp['tail']);self.assertIn(m,marks);self.assertLess(len(cp['tail']),STEP)
  self.assertEqual(cp['tail'],data[cp['offset']:m])
  self.assertEqual(cp['mark'].count('tfra '),marks.index(m)+1)   # every index line up to that mark
  for c in saved:self.assertEqual(c['offset']%STEP,0)
  # Kodi closed: everything in RAM is gone. The next run gets the converter's output from the mark on.
  resume_store.save(self.tmp.name,'slot',('src','md5',1,'1'),cp)
  back=resume_store.load(self.tmp.name,'slot',('src','md5',1,'1'))
  self.assertEqual(back,cp);self.assertTrue(resume_store.alive(drive,back))
  self.assertIsNone(resume_store.load(self.tmp.name,'slot',('src','other',1,'1')))
  again=dp.Sink(drive,'staging','slot',lambda:True,background=False,spool=self.tmp.name,checkpoint=back)
  for at in range(m,len(data),100*1024):again.write(0,'.mp4',data[at:at+100*1024])
  result=again.finish()['0']
  self.assertEqual(drive.files[result['id']]['data'],data)   # the same movie, uploaded once
  self.assertEqual(sum(1 for c in drive.calls if c[0]=='POST'),1)
 def test_the_upload_thread_saves_checkpoints_too(self):
  import time
  drive=Drive();data=os.urandom(30*STEP);saved=[]
  sink=self.run_until(drive,data,[5*STEP+10,9*STEP+20],20*STEP,saved,background=True)
  for _ in range(100):
   if saved:break
   time.sleep(0.05)
  sink.close()
  self.assertTrue(saved);self.assertEqual(saved[-1]['offset']%STEP,0);self.assertLess(len(saved[-1]['tail']),STEP)
 def test_far_from_a_mark_it_goes_up_anyway(self):
  drive=Drive();data=os.urandom(20*STEP);saved=[]
  sink=self.run_until(drive,data,[],len(data),saved)
  self.assertFalse(saved);self.assertGreater(sink.tracks[0]['offset'],0)
  self.assertLessEqual(len(sink.tracks[0]['buffer']),dp.MARK_CAP)
 def test_a_lost_session_is_not_alive(self):
  drive=Drive();cp={'url':'https://upload.example/none','offset':0,'tail':b'','mark':mark(1)}
  self.assertFalse(resume_store.alive(drive,cp))
 def test_picture_subtitles_wait_and_carry_on(self):
  drive=Drive()
  sink=dp.Sink(drive,'staging','slot',lambda:True,background=False,spool=self.tmp.name)
  sink.write(2,'.eng.1.sup',b'A'*1000);sink.write(2,'.eng.1.sup',b'B'*500)
  self.assertEqual(sum(1 for c in drive.calls if c[0]=='POST'),0)   # nothing goes up before the movie ends
  cp={'url':None,'offset':0,'tail':b'','mark':mark(5,sides={2:1200})}
  sink.write(0,'.mp4',b'm'*5)
  # Carry on from a mark that kept 1200 bytes of the subtitle file
  drive2=Drive();_,headers,_=drive2.call('POST','x?uploadType=resumable','{"name":"slot.mp4"}'.encode());cp['url']=headers['Location']
  drive2.call('PUT',cp['url'],b'm'*0 or b'',{'Content-Range':'bytes */*'})
  again=dp.Sink(drive2,'staging','slot',lambda:True,background=False,spool=self.tmp.name,checkpoint=dict(cp,tail=b'mmmmm'))
  again.write(2,'.eng.1.sup',b'C'*10);again.write(0,'.mp4',b'rest')
  out=again.finish()
  self.assertEqual(drive2.files[out['0']['id']]['data'],b'mmmmmrest')
  side=[f for f in drive2.files.values() if f.get('name','').endswith('.sup')]
  self.assertEqual(side[0]['data'],b'A'*1000+b'B'*200+b'C'*10)
  self.assertEqual(side[0]['name'],'slot.eng.1.sup')
 def test_store_clears(self):
  resume_store.save(self.tmp.name,'s',('a',),{'url':'u','offset':0,'tail':b'x','mark':'m'})
  (resume_store.folder(self.tmp.name)/'s.side2').write_bytes(b'x')
  resume_store.clear(self.tmp.name,'s');self.assertEqual(list(resume_store.folder(self.tmp.name).glob('s.*')),[])

class Fit(unittest.TestCase):
 """Build 190 (end-to-end test): Drive is nearly always between two marks when Kodi closes."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory()
 def tearDown(self):self.tmp.cleanup()
 def cp(self,**kw):return dict(dict(url='u',offset=10*STEP,tail=b't'*100,mark=mark(10*STEP+100)),**kw)
 def test_up_to_the_mark_the_tail_fills_the_gap(self):
  r=resume_store.fit(self.cp(),10*STEP+40,copied=False)
  self.assertEqual((r['offset'],r['tail'],r['skip']),(10*STEP+40,b't'*60,0))
 def test_past_the_mark_a_copy_skips_what_drive_has(self):
  r=resume_store.fit(self.cp(),12*STEP,copied=True)
  self.assertEqual((r['offset'],r['tail'],r['skip']),(12*STEP,b'',12*STEP-(10*STEP+100)))
  self.assertIsNone(resume_store.fit(self.cp(),12*STEP,copied=False))   # a re-encode does not repeat exactly
  self.assertIsNone(resume_store.fit(self.cp(),None,copied=True));self.assertIsNone(resume_store.fit(None,0,True))
 def test_kept_pieces_cover_what_drive_lacks(self):
  a=os.path.join(self.tmp.name,'p0');b=os.path.join(self.tmp.name,'p1')
  Path(a).write_bytes(b'A'*STEP);Path(b).write_bytes(b'B'*STEP)
  c=dict(url='u',offset=2*STEP,tail=b'',mark=mark(2*STEP),pieces=[[0,STEP,a],[STEP,2*STEP,b]])
  r=resume_store.fit(c,STEP//2,copied=False)
  self.assertEqual((r['offset'],r['tail']),(STEP//2,b'A'*(STEP//2)+b'B'*STEP))
  os.remove(b);self.assertIsNone(resume_store.fit(c,STEP//2,copied=False))   # a missing piece: start again
 def test_sink_skips_and_keeps(self):
  drive=Drive();_,headers,_=drive.call('POST','x?uploadType=resumable','{"name":"slot.mp4"}'.encode())
  url=headers['Location'];drive.call('PUT',url,b'm'*STEP,{'Content-Range':'bytes 0-%d/*'%(STEP-1)})
  # Drive has STEP bytes, the mark is at 100: the converter's next STEP-100 bytes are already there.
  s=dp.Sink(drive,'staging','slot',lambda:True,background=False,spool=self.tmp.name,checkpoint=dict(url=url,offset=STEP,tail=b'',mark=mark(100),skip=STEP-100))
  s.write(0,'.mp4',b'm'*(STEP-100)+b'rest')
  out=s.finish()['0'];self.assertEqual(drive.files[out['id']]['data'],b'm'*STEP+b'rest')
 def test_kept_files_follow_the_movie_and_go_once_drive_has_them(self):
  saved=[];s=dp.Sink(Drive(),'staging','slot',lambda:True,spool=self.tmp.name,keep_pieces=True,on_checkpoint=saved.append)
  old=dp.MAIN_CHUNK;dp.MAIN_CHUNK=STEP
  try:
   s._new_track(0,'u',0)
   s.tracks[0]['buffer']=bytearray()   # write path only for _keep
   s._keep(0,b'x'*(STEP+10));self.assertEqual(sorted(p[:2] for p in s.pieces.values()),[[0,STEP],[STEP,STEP+10]])
   self.assertEqual(Path(s.pieces[STEP][2]).read_bytes(),b'x'*10)
   s.mark_from(mark(STEP+5));self.assertEqual(saved[-1]['offset'],STEP+5);self.assertEqual(len(saved[-1]['pieces']),2)
   s._drop_confirmed(STEP);self.assertEqual(list(s.pieces),[STEP])
  finally:dp.MAIN_CHUNK=old;s.close()

class Wiring(unittest.TestCase):
 def test_native_and_queue(self):
  prep=(LIB/'prepare_downloads.py').read_text();cloud=(LIB/'prepare_cloud.py').read_text()
  self.assertIn("lib.kodi_airplay_prepare_marks(1)",prep);self.assertIn('if track==-1:',prep)
  self.assertIn("r=self.lib.kodi_airplay_prepare_resume(",prep);self.assertIn('raise ResumeFailed(',prep)
  self.assertIn("checkpoint=resume_store.load(q.profile,slot,prep.identity(item)) if resumes else None",cloud)
  self.assertIn("held=resume_store.confirmed(q.drive,checkpoint) if job.get('probe') else None",cloud)
  self.assertIn("checkpoint=resume_store.fit(checkpoint,held,bool((job.get('probe') or {}).get('copy_video')))",cloud)
  self.assertIn("keep_pieces=resumes and not (job.get('probe') or {}).get('copy_video'),",cloud)
  self.assertIn("except prep.ResumeFailed as error:",cloud);self.assertIn("raise driveupload.Stop('Starting the conversion again')",cloud)
  self.assertIn("sink.finish()\n                    resume_store.clear(q.profile,slot)",cloud)
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('int kodi_airplay_prepare_resume(',c);self.assertIn('+skip_trailer',c);self.assertIn('static int write_mfra(',c)
  self.assertIn('test_preparation_resume(work,argv[2]);',(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text())

if __name__=='__main__':unittest.main()
