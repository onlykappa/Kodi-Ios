"""Owner (build 168): Inception (AV1 10-bit HDR 4K) stayed at 0% on an iPhone 16 Pro. "add how fast its moving too, and
increase cpu limit to how all other apps operate". app_state.Pace, the live progress line and the r18 HDR hardware path."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import app_state,prepare_downloads as prep

class Clock:
 def __init__(self):self.t=0.0;self.cpu=0.0;self.slept=[]
 def wall(self):return self.t
 def thread(self):return self.cpu
 def sleep(self,s):self.slept.append(s);self.t+=s

class Pacing(unittest.TestCase):
 def run_pace(self,on_screen):
  c=Clock();p=app_state.Pace(on_screen=lambda:on_screen,cpu_clock=c.thread,clock=c.wall,sleep=c.sleep)
  for _ in range(100):c.t+=0.1;c.cpu+=0.1;p.tick()   # a thread that would use a whole core
  return c
 def test_no_limit_while_kodi_is_on_screen(self):
  self.assertEqual(self.run_pace(True).slept,[])
 def test_background_stays_under_ios_limit(self):
  c=self.run_pace(False)
  self.assertLessEqual(c.cpu/c.t,app_state.BACKGROUND_SHARE+0.01);self.assertGreater(c.cpu/c.t,0.5)
 def test_unknown_state_counts_as_background(self):
  app_state._cache.update(at=-10.0,value=None)
  self.assertFalse(app_state.foreground(clock=lambda:100.0,read=lambda:None))
  app_state._cache.update(at=-10.0)
  self.assertTrue(app_state.foreground(clock=lambda:200.0,read=lambda:app_state.ACTIVE))
  self.assertFalse(app_state.foreground(clock=lambda:300.0,read=lambda:app_state.BACKGROUND))
 def test_both_converters_use_it(self):
  src=(LIB/'prepare_downloads.py').read_text()
  self.assertEqual(src.count('pace=app_state.Pace()'),2);self.assertNotIn('2*cpu-wall',src)

class LiveLine(unittest.TestCase):
 def test_never_a_bare_zero(self):
  self.assertEqual(prep.speed_text(0,0),'')
  self.assertEqual(prep.speed_text(79477322,0),'75 MB read')
  self.assertEqual(prep.speed_text(int(1.2*1024**3),8.4*1024**2),'1.2 GB read · 8.4 MB/s')
  self.assertEqual(prep.live_line({'progress':0,'detail':'75 MB read · 0.4 MB/s'}),' · 75 MB read · 0.4 MB/s')
  self.assertEqual(prep.live_line({'progress':12,'detail':'1.2 GB read · 8.4 MB/s'}),' · 12% · 1.2 GB read · 8.4 MB/s')
  self.assertEqual(prep.live_line({'progress':0}),'')
 def test_speed_over_the_last_seconds(self):
  q=prep.Queue.__new__(prep.Queue)
  reads=iter([0,10*1024**2,30*1024**2])
  q.stream=type('S',(),{'stats':lambda s:{'read_bytes':next(reads)}})()
  self.assertEqual(q.read_speed(0.0),(0,0.0))
  self.assertEqual(q.read_speed(5.0)[1],2*1024**2)
  self.assertEqual(q.read_speed(10.0),(30*1024**2,3*1024**2))

class HardwareHDR(unittest.TestCase):
 def test_r18_passes_decoder_frames_to_the_hevc_encoder(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  self.assertIn('frames->sw_format == AV_PIX_FMT_P010',c)
  self.assertIn('c->pix_fmt=AV_PIX_FMT_VIDEOTOOLBOX;c->sw_pix_fmt=AV_PIX_FMT_P010LE;',c)
  self.assertIn('j->conv = av_frame_clone(fr);',c)
  self.assertIn('hdr_pass_broken = 1',c)
  self.assertLess(c.index('if (!j->enc) j->hdr_pass ='),c.index('if (!j->enc) j->gpu ='))
  self.assertIn('--enable-decoder=av1 --enable-hwaccel=av1_videotoolbox',(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text())

if __name__=='__main__':unittest.main()
