"""Build 224 (owner: downloading "completely broken"; build-223 log 27f59dcd: uploads paused in all 122 snapshots,
four AllDebrid downloads waiting): AirPlay's Pause and retry ends with AirPlay; old pauses are lifted once."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import transfer_control as tc

class Pauses(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.p=self.t.name
 def tearDown(self):self.t.cleanup()
 def test_airplay_pause_lifts_after_airplay(self):
  for k in tc.KINDS:tc.set_paused(self.p,k,True,now=100,why='airplay')
  q=[None]
  self.assertEqual(tc.release_airplay(self.p,True,now=200,quiet_since=q),[])          # still playing
  self.assertEqual(tc.release_airplay(self.p,False,now=300,quiet_since=q),[])         # just stopped: grace starts
  self.assertEqual(tc.release_airplay(self.p,False,now=300+tc.AIRPLAY_GRACE-1,quiet_since=q),[])
  self.assertEqual(tc.release_airplay(self.p,False,now=300+tc.AIRPLAY_GRACE,quiet_since=q),['conv','up'])
  self.assertFalse(tc.paused(self.p,'up'))
 def test_owner_pause_stays(self):
  tc.set_paused(self.p,'up',True,now=100)
  q=[None];tc.release_airplay(self.p,False,now=0,quiet_since=q)
  self.assertEqual(tc.release_airplay(self.p,False,now=10**6,quiet_since=q),[])
  self.assertTrue(tc.paused(self.p,'up'));self.assertEqual(tc.reason(self.p,'up'),'you')
 def test_old_files_read_as_owner_pause(self):
  f=tc.folder(self.p)/'paused-up';f.parent.mkdir(parents=True);f.write_text('1731200000.0')
  self.assertEqual(tc.reason(self.p,'up'),'you')
 def test_reset_once(self):
  f=tc.folder(self.p)/'paused-up';f.parent.mkdir(parents=True);f.write_text('1731200000.0')
  self.assertEqual(tc.reset_once(self.p),['up']);self.assertFalse(tc.paused(self.p,'up'))
  tc.set_paused(self.p,'up',True)
  self.assertEqual(tc.reset_once(self.p),[]);self.assertTrue(tc.paused(self.p,'up'))   # only the first start
 def test_wiring(self):
  self.assertIn("set_paused(profile,kind,True,why='airplay')",(BOOT/'cast.py').read_text())
  svc=(BOOT/'service.py').read_text()
  self.assertIn('transfer_control.reset_once(profile)',svc);self.assertIn('transfer_control.release_airplay(profile,airplay_busy(),quiet_since=quiet)',svc)

class PausedCard(unittest.TestCase):
 def test_card_and_resume_page(self):
  import work_state
  card=work_state.NEEDS_TEXT['uploads_paused']
  self.assertEqual((card['title'],card['button']),('Downloads are paused','Resume'))
  self.assertEqual(card['action'],'RunScript(service.kodi.ios.bootstrap,resume_uploads)')
  self.assertIn("'resume_uploads'",(BOOT/'default.py').read_text())
  page=(BOOT/'resume_uploads.py').read_text()
  self.assertIn("transfer_control.set_paused(profile,'up',False)",page);self.assertIn("work_state.need('uploads_paused',False,profile)",page)
  self.assertIn("work_state.need('uploads_paused',transfer_control.paused(profile,'up') and debrid_drive.active(profile),profile)",(BOOT/'service.py').read_text())

if __name__=='__main__':unittest.main()
