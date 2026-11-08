"""Owner (build 160): a Ready movie said "Apple's AirPlay player can't play this video (MP4)", and "i like have to
press it twice". The log: nothing showed for ~12 s, so Play on TV was pressed again; the second AirPlay session shut the
first one's stream (-1004 "Could not connect to the server"), and the first, failing, shut the second's."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True
sys.path.insert(0,str(BOOT/'resources/lib'))
import cast

LOG=['start: http://127.0.0.1:58940/download/x/The%20Nightmare%20Before%20Christmas.mp4',
     'player: could not open the stream: Error Domain=NSURLErrorDomain Code=-1004 "Could not connect to the server." UserInfo={NSLocalizedDescription=Could not connect to the server.',
     'prepared: source-resolution MP4 byte ranges; no live conversion, subtitle burn or prefetch queue']

class Words(unittest.TestCase):
 def test_the_owners_failure_in_everyday_words(self):
  self.assertEqual(cast.player_problem(LOG),'the TV could not connect to the phone')
  self.assertEqual(cast.player_problem(['player: stopped: The operation could not be completed']),'the TV stopped the video')
  self.assertEqual(cast.player_problem(['player: ready']),'')
  self.assertIn("AirPlay didn't start on the TV: the TV could not connect to the phone.",cast.NOT_STARTED%cast.player_problem(LOG))
  self.assertNotIn("can't play this video",cast.NOT_STARTED)

class OneAtATime(unittest.TestCase):
 def test_busy_for_90_seconds(self):
  self.assertTrue(cast.busy('1000',1050));self.assertFalse(cast.busy('1000',1091));self.assertFalse(cast.busy('',5));self.assertFalse(cast.busy(None,5))
 def test_the_page_guards_and_always_releases(self):
  src=(BOOT/'cast.py').read_text()
  run=src[src.index('def run():'):src.index('def pick_sheet(')]
  self.assertLess(run.index('with cast.session_lock('),run.index('run_owned()'))
  self.assertIn("home.setProperty(cast.BUSY,str(time.time()))\n  try:run_owned()",run)
  self.assertIn("finally:home.clearProperty(cast.BUSY)",run)

class Feedback(unittest.TestCase):
 def test_connecting_shows_at_once_with_cancel_and_kodi_carries_on(self):
  src=(BOOT/'cast.py').read_text()
  body=src[src.index('def send_airplay('):src.index('def send(xbmc')]
  # Owner-approved Play on TV card (airplay_flow, 2026-11-08): shown before the play starts, with Cancel.
  self.assertLess(body.index("ui.show('opening' if converting else 'connecting'"),body.index('lib.kodi_airplay_play(source'))
  self.assertIn('return ui.canceled() or monitor.waitForAbort(seconds)',body)
  self.assertIn("if outcome=='aborted':ui.close();return",body)
  self.assertLess(body.index("if xbmc.getCondVisibility('Player.Paused'):player.pause()   # Kodi carries on"),body.index("if outcome=='aborted':ui.close();return"))
 def test_a_converting_framework_never_blames_the_format(self):
  src=(BOOT/'cast.py').read_text()
  body=src[src.index('def send_airplay('):src.index('def send(xbmc')]
  tail=body[body.index("if outcome=='aborted':ui.close();return"):]
  self.assertLess(tail.index('elif converting:'),tail.index('cast.MIRRORING'))
  self.assertIn('cast.NOT_STARTED%problem',tail)

if __name__=='__main__':unittest.main()
