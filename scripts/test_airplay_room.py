"""Owner (build 185 log: "airplay stops out of nowhere"): the TV's first read took 12 s and the next ones 19 s while an
AllDebrid copy went up to Drive, and Apple's player timed out. While AirPlay plays, the copies, the uploads and the
conversion wait; a timeout at the start is tried once more."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB)]
import airplay,cast

class Window:
 def __init__(self):self.p={}
 def setProperty(self,k,v):self.p[k]=v
 def getProperty(self,k):return self.p.get(k,'')

class Busy(unittest.TestCase):
 def test_marked_while_apple_player_logs(self):
  w=Window();self.assertFalse(airplay.busy(w,100))
  airplay.mark_busy(w,100);self.assertTrue(airplay.busy(w,150));self.assertFalse(airplay.busy(w,100+airplay.BUSY_FOR+1))
  airplay.activity(['GET /prepared.mp4 bytes=0-1 206 2 B 12 ms'],w,500);self.assertTrue(airplay.busy(w,520))
  airplay.activity(['player: closed at 812.0 s'],w,530);self.assertFalse(airplay.busy(w,531))
  airplay.activity([],w,540);self.assertFalse(airplay.busy(w,541))
  w.setProperty(airplay.BUSY,'junk');self.assertFalse(airplay.busy(w,1))
 def test_retry_only_a_timeout(self):
  self.assertTrue(cast.retry_airplay('failed','The request timed out.'))
  self.assertFalse(cast.retry_airplay('failed','This codec is not supported'))
  self.assertFalse(cast.retry_airplay('playing','The request timed out.'))
  self.assertFalse(cast.retry_airplay('failed',None))

class Wiring(unittest.TestCase):
 def test_service_holds_and_cast_marks(self):
  svc=(BOOT/'service.py').read_text();send=(BOOT/'cast.py').read_text()
  self.assertIn('airplay_busy=lambda:airplay.playback_active(playback_lib,xbmcgui.Window(10000),time.time())',svc)
  # Build 193: AirPlay no longer holds anything; it slows the work (slowdown.py). Only the owner's Pause holds.
  self.assertIn("keep_going=lambda:not monitor.abortRequested() and not transfer_control.paused(profile,'up'),on_done=done",svc)
  self.assertIn("uploading=lambda:idle() and not transfer_control.paused(profile,'up')   #",svc)
  self.assertIn("slowdown.configure(lambda:'airplay' if airplay_busy() else ('video' if xbmc.getCondVisibility('Player.HasVideo') else ''))",svc)
  self.assertNotIn("or airplay_busy())",svc)
  self.assertIn('airplay.activity(lines,xbmcgui.Window(10000),time.time())',svc)
  self.assertIn('airplay.mark_busy(home,time.time())',send);self.assertIn('lib.kodi_airplay_close();airplay.clear_busy(home)',send)
  self.assertNotIn('cast.retry_airplay(outcome,why)',send)  # an old attempt must not silently start another session
  # Build 188: Kodi stays awake while AirPlay plays (the TV reads from Kodi's server), before the music exception ends
  self.assertIn("if airplay.playback_active(lib,xbmcgui.Window(10000),time.time()):return 'AirPlay'",svc)
  self.assertLess(send.index('airplay.mark_busy(home,time.time())'),send.index('lib.kodi_airplay_play(source'))
  self.assertLess(send.index('lib.kodi_airplay_play(source'),send.index('cast.airplay_outcome('))

if __name__=='__main__':unittest.main()
