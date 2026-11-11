"""Build 193, Phase 3 (owner: "stuff should ALWAYS be moving even if an AirPlay movie is playing, just slower … AirPlay
must not stutter … Pause stays a real pause"): slowdown.py, its use by every worker, and the build-192 log's cause 1
(the converter's own log lines counted as AirPlay playing and held everything)."""
import sys,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import slowdown,airplay,app_state

class Window:
 def __init__(self):self.p={}
 def setProperty(self,k,v):self.p[k]=v
 def getProperty(self,k):return self.p.get(k,'')

class Reset(unittest.TestCase):
 def setUp(self):slowdown._state.update(strain_until=0.0);slowdown.configure(lambda:'')
 def tearDown(self):slowdown._state.update(strain_until=0.0);slowdown.configure(lambda:'')

class Rule(Reset):
 def test_reason_only_from_the_service(self):
  self.assertEqual(slowdown.reason(),'')
  slowdown.configure(lambda:'video');self.assertEqual(slowdown.reason(),'video')
  slowdown.configure(lambda:'airplay');self.assertEqual(slowdown.reason(),'airplay')
  slowdown.configure(lambda:'nonsense');self.assertEqual(slowdown.reason(),'')   # only the two reasons exist
  def broken():raise RuntimeError('player gone')
  slowdown.configure(broken);self.assertEqual(slowdown.reason(),'')               # never stops work on an error
 def test_share_per_reason(self):
  self.assertEqual(slowdown.share(''),1.0)
  self.assertEqual(slowdown.share('video'),0.35);self.assertEqual(slowdown.share('airplay'),0.25)
  self.assertGreater(slowdown.share('airplay'),0)    # slowed, never stopped
 def test_rest_keeps_the_share(self):
  self.assertEqual(slowdown.rest_for(2.0,1.0),0.0)
  self.assertAlmostEqual(slowdown.rest_for(1.0,0.25),3.0)        # busy 1 s of every 4
  self.assertAlmostEqual(slowdown.rest_for(1.0,0.35),1/0.35-1)
  self.assertEqual(slowdown.rest_for(30.0,0.25),slowdown.MAX_REST)   # a Stop or Pause is noticed within MAX_REST
 def test_gate_rests_only_while_slowed_and_ends_early(self):
  slept=[];g=slowdown.Gate(why=lambda:'',sleep=slept.append)
  self.assertEqual(g.after(1.0),0.0);self.assertEqual(slept,[])
  g=slowdown.Gate(why=lambda:'airplay',sleep=slept.append);self.assertAlmostEqual(g.after(1.0),3.0)
  self.assertAlmostEqual(sum(slept),3.0);self.assertTrue(all(s<=1.0 for s in slept))
  slept.clear();going=[True,False]
  g=slowdown.Gate(why=lambda:'airplay',sleep=slept.append,keep_going=lambda:going.pop(0) if going else False)
  g.after(2.0);self.assertEqual(len(slept),1)    # Pause / Stop pressed during the rest: it ends at once

class AirPlayNotStutter(Reset):
 def test_slow_tv_read_cuts_the_share(self):
  now=1000.0
  self.assertFalse(slowdown.note_served(['GET /video/prepared.mp4 bytes=0-4194303 206 4194304 B 310 ms'],now))
  self.assertFalse(slowdown.note_served(['GET /video/prepared.mp4 bytes=0-1 206 2 B 4000 ms'],now))   # a tiny probe
  self.assertEqual(slowdown.share('airplay',now),0.25)
  self.assertTrue(slowdown.note_served(['GET /video/prepared.mp4 bytes=0-4194303 206 4194304 B 2600 ms'],now))
  self.assertEqual(slowdown.share('airplay',now+10),slowdown.STRAINED)
  self.assertEqual(slowdown.share('airplay',now+slowdown.STRAIN_HOLD+1),0.25)   # back once the TV keeps up again
  self.assertEqual(slowdown.share('video',now+10),0.35)                          # strain is about AirPlay only

class Build192Cause1(Reset):
 def test_converter_lines_are_not_airplay(self):
  """Build-192 log 13:10:00-13:10:36: 'prepare: unit started …' marked AirPlay busy; 16 s later the conversion said
  'Paused while a video plays' with nothing playing."""
  w=Window()
  airplay.activity(['prepare: unit started via hardware HDR (av1 decoder to hevc_videotoolbox)',
                    'prepare: video 1/297 made in 16.4 s for 30 s of film (1.82x real time)'],w,500)
  self.assertFalse(airplay.busy(w,501))
  airplay.activity(['  prepare: fragments of about 60 s (source 7.0 Mbit/s), samples interleaved'],w,510)
  self.assertFalse(airplay.busy(w,511))
  airplay.activity(['prepare: unit started','GET /video/prepared.mp4 bytes=0-1 206 2 B 12 ms'],w,520)
  self.assertTrue(airplay.busy(w,521))          # the AirPlay server's own lines still count
  airplay.activity(['player: closed at 812.0 s'],w,530);self.assertFalse(airplay.busy(w,531))

class Workers(Reset):
 def test_pace_slows_the_converter_on_screen(self):
  clock=[0.0];slept=[]
  def sleep(s):slept.append(s);clock[0]+=s
  pace=app_state.Pace(on_screen=lambda:True,cpu_clock=lambda:0.0,clock=lambda:clock[0],sleep=sleep)
  clock[0]+=1.0;self.assertEqual(pace.tick(),0.0)       # nothing plays: flat out on screen (build 168)
  slowdown.configure(lambda:'video');slowdown._state['at']=-10
  clock[0]+=1.0;self.assertAlmostEqual(pace.tick(),1/0.35-1)   # a video plays: a share, never a hold
 def test_every_worker_uses_the_gate(self):
  self.assertIn('self.gate.after(time.monotonic() - began)',(LIB/'drive_prepare.py').read_text())
  stream=(LIB/'drive_stream.py').read_text()
  self.assertIn('self.gate.after(time.monotonic() - began, sum(len(x) for x in parts), download=True)',stream)
  self.assertIn('(2 if stream.playback else 1 if slowdown.reason() else READ_AHEAD)',stream)
  up=(LIB/'driveupload.py').read_text()
  self.assertEqual(up.count('slowdown.Gate(keep_going=keep_going)'),2)   # phone uploads and AllDebrid copies
  self.assertIn('gate.after(put_s,len(chunk),download=True)',up)
  self.assertIn('pause = max(pause, self.slow(wall))',(LIB/'app_state.py').read_text())
 def test_sink_hold_is_only_the_owners_pause(self):
  import drive_prepare
  sink=drive_prepare.Sink(None,'p','n',lambda:True,hold=lambda:False,background=False)
  self.assertIsInstance(sink.gate,slowdown.Gate)
 def test_service_never_waits_for_playback(self):
  svc=(BOOT/'service.py').read_text()
  self.assertIn("idle=lambda:not monitor.abortRequested()\n",svc)
  self.assertNotIn('and not airplay_busy()',svc)
  self.assertNotIn('isPlayingVideo() or transfer_control',svc)
  self.assertIn("preparation.paused=lambda:(not monitor.abortRequested() and transfer_control.paused(profile,'conv') and",svc)
  self.assertEqual(svc.count("slowdown.configure(lambda:'airplay' if"),2)
  # The owner's Pause reaches the converter's hold loop (its words: "Paused by you").
  self.assertIn("not transfer_control.paused(profile,'conv')",svc.split('converting=lambda:')[1].split('\n')[0])
  cloud=(LIB/'prepare_cloud.py').read_text()
  self.assertIn("q.runtime.phase('Paused by you',False,item['name'])",cloud)
  self.assertNotIn("phase('Paused while a video plays'",cloud)

class DownloadCap(unittest.TestCase):
 """Build 206 (owner, build 205: seeking an Umbrella episode "nearly broke the app ... it should use download speeds"):
 an AllDebrid copy read 32 MB in 2.4 s while the episode played. Downloads keep under CAP while something plays and
 wait while Kodi buffers; uploads keep the time share."""
 def gate(self,whys):
  slept=[];seq=list(whys)
  why=lambda:seq.pop(0) if len(seq)>1 else seq[0]
  return slowdown.Gate(why=why,sleep=slept.append),slept
 def test_a_download_keeps_under_the_cap_while_airplay_plays(self):
  g,slept=self.gate(['airplay'])
  rested=g.after(0.08,1024*1024,download=True)   # 1 MB read in 0.08 s = 12.5 MB/s
  self.assertAlmostEqual(rested,1.0-0.08,places=2)    # held to 1 MB/s
  self.assertAlmostEqual(sum(slept),rested,places=2)
 def test_uploads_keep_the_time_share_under_airplay(self):
  g,_=self.gate(['airplay']);self.assertAlmostEqual(g.after(1.0),1.0/0.25-1.0,places=2)
 def test_uploads_are_capped_under_airplay(self):
  text=(LIB/'driveupload.py').read_text()
  self.assertIn('gate.after(time.monotonic()-began,len(chunk),download=True)',text)
  self.assertIn('gate.after(put_s,len(chunk),download=True)',text)
  g,_=self.gate(['airplay']);self.assertAlmostEqual(g.after(1.0,32*1024*1024,download=True),31.0,places=2)
 def test_every_worker_waits_while_kodi_plays_or_buffers(self):
  # Build 208 (owner, build 207: seeking froze for 100 s while an upload, a copy and the converter ran): while Kodi
  # plays a video (Umbrella stream, Drive download, anything) all background work waits until it stops.
  for whys in (['buffering']*5+[''],['video']*3+['buffering']*2+['']):
   g,slept=self.gate(whys)
   g.after(1.0);self.assertEqual(slept,[1.0]*4)
   g,slept=self.gate(whys)
   g.after(0.08,1024*1024,download=True);self.assertEqual(slept,[1.0]*4)
 def test_a_stop_ends_the_wait(self):
  going=[True,False];slept=[]
  g=slowdown.Gate(why=lambda:'video',sleep=slept.append,keep_going=lambda:going.pop(0) if going else False)
  g.after(2.0);self.assertEqual(slept,[1.0])
 def test_the_converter_and_its_reads_hold_while_kodi_plays(self):
  self.assertIn("hold=lambda:paused() or __import__('slowdown').holding()",(LIB/'prepare_cloud.py').read_text())
  self.assertIn('preparation.stream.hold=lambda:preparation.paused() or slowdown.holding()',(BOOT/'service.py').read_text())
  slowdown.configure(lambda:'video');slowdown._state['at']=-10;self.assertTrue(slowdown.holding())
  slowdown.configure(lambda:'airplay');slowdown._state['at']=-10;self.assertFalse(slowdown.holding())
  slowdown.configure(lambda:'');slowdown._state['at']=-10
 def test_full_speed_when_nothing_plays(self):
  g,slept=self.gate(['']);self.assertEqual(g.after(0.08,1024*1024,download=True),0.0);self.assertEqual(slept,[])
 def test_the_service_reports_buffering(self):
  text=(BOOT/'service.py').read_text()
  self.assertEqual(text.count("'buffering' if xbmc.getCondVisibility('Player.Caching') else 'video'"),2)
  self.assertIn("reader_gate.after(time.monotonic()-piece,len(data),download=True)",(LIB/'driveupload.py').read_text())

class Watched(Reset):
 """Build 207 (build-206 log d85fe349): 1.3 MB/s from AllDebrid with nothing playing, 13-16 MB/s in build 205. The
 download asked Kodi's GUI (Player.HasVideo) after every 1 MB; in the background that waits for the GUI lock."""
 def tearDown(self):
  if hasattr(self,'t'):self.stop.set();self.t.join(2)
  super().tearDown()
 def start(self,fn):
  self.stop=threading.Event();self.lines=[]
  slowdown.configure(fn)
  self.t=threading.Thread(target=slowdown.watch,args=(lambda s:self.stop.wait(0.02),),kwargs={'log':self.lines.append},daemon=True)
  self.t.start()
  deadline=time.monotonic()+2
  while not slowdown._state['watched'] and time.monotonic()<deadline:time.sleep(0.01)
 def test_workers_never_ask_kodi(self):
  calls=[];me=threading.current_thread()
  def slow():
   calls.append(threading.current_thread());time.sleep(0.05);return ''
  self.start(slow)
  gate=slowdown.Gate(sleep=lambda s:None)
  began=time.monotonic()
  for _ in range(200):gate.after(0.01,1024*1024,download=True)   # 200 MB read with nothing playing
  self.assertLess(time.monotonic()-began,0.5)
  self.assertEqual(gate.rested,0.0)
  self.assertNotIn(me,calls)                                       # only the watcher asked
 def test_watcher_follows_playback_and_logs_it(self):
  now={'v':''}
  self.start(lambda:now['v'])
  now['v']='video';time.sleep(0.15)
  self.assertEqual(slowdown.reason(),'video')
  now['v']='';time.sleep(0.15)
  self.assertEqual(slowdown.reason(),'')
  self.assertEqual(self.lines,['Kodi iOS slowdown: Slower while a video plays','Kodi iOS slowdown: full speed'])
 def test_service_starts_the_watcher(self):
  svc=(BOOT/'service.py').read_text()
  self.assertIn('target=slowdown.watch',svc)

if __name__=='__main__':unittest.main()
