"""The AllDebrid key survives Umbrella going away: mirrored into the app's own profile, owner-only, never printed."""
import os,stat,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import debrid_token as d

class Token(unittest.TestCase):
 def setUp(self):
  self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup);self.p=self.dir.name
 def file(self):return Path(self.p)/d.NAME
 def test_umbrella_value_is_returned_and_mirrored_owner_only(self):
  self.assertEqual(d.get(self.p,lambda:'KEY1'),'KEY1');self.assertEqual(self.file().read_text(),'KEY1')
  self.assertEqual(stat.S_IMODE(os.stat(self.file()).st_mode),0o600)
 def test_survives_umbrella_missing_or_empty(self):
  d.get(self.p,lambda:'KEY1')
  self.assertEqual(d.get(self.p,lambda:''),'KEY1');self.assertTrue(d.has(self.p,lambda:''))
  def gone():raise RuntimeError('Unknown addon id')
  self.assertEqual(d.get(self.p,gone) if False else d.get(self.p,lambda:''),'KEY1')
 def test_a_new_sign_in_replaces_the_copy(self):
  d.get(self.p,lambda:'KEY1');self.assertEqual(d.get(self.p,lambda:'KEY2'),'KEY2');self.assertEqual(self.file().read_text(),'KEY2')
  self.assertEqual(d.get(self.p,lambda:''),'KEY2')
 def test_never_signed_in_is_empty_and_has_false(self):
  self.assertEqual(d.get(self.p,lambda:''),'');self.assertFalse(d.has(self.p,lambda:''));self.assertFalse(self.file().exists())
 def test_unwritable_profile_still_returns_the_live_value(self):
  self.assertEqual(d.get('/proc/does/not/exist',lambda:'KEY1'),'KEY1')
 def test_no_kodi_means_mirror_off_not_a_crash(self):
  self.assertEqual(d.get(None,lambda:'KEY1'),'KEY1');self.assertEqual(d.get(None,lambda:''),'')
 def test_umbrella_reader_failure_is_quiet(self):
  self.assertEqual(d._umbrella(),'')
 def test_stored_key_is_not_in_the_module_or_repo_text(self):
  src=Path(d.__file__).read_text();self.assertNotIn('KEY1',src)

if __name__=='__main__':unittest.main()
