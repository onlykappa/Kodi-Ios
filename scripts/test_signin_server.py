"""Owner review (PR 8): Drive refresh tokens go only to the owner's own sign-in worker, never the public relay."""
import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('signin_server',ROOT/'migration/bundled-bootstrap/resources/lib/signin_server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Addon:
 def __init__(self,v):self.v={'sign-in-server':v}
 def getSetting(self,k):return self.v.get(k,'')
 def setSetting(self,k,v):self.v[k]=v
class SigninServer(unittest.TestCase):
 def test_server_never_public(self):
  self.assertEqual(s.server(''),s.SERVER);self.assertEqual(s.server('https://drive.signinserver.com/'),s.SERVER)
  self.assertEqual(s.server('https://other.example/'),'https://other.example')
  self.assertTrue(s.SERVER.startswith('https://kodi-signin.') and s.SERVER.endswith('.workers.dev'))
 def test_migrate_existing_installs(self):
  a=Addon('https://drive.signinserver.com');self.assertTrue(s.migrate(a));self.assertEqual(a.v['sign-in-server'],s.SERVER)
  b=Addon('https://my.custom/');self.assertFalse(s.migrate(b));self.assertEqual(b.v['sign-in-server'],'https://my.custom/')
 def test_no_public_relay_left_in_app_code(self):
  for p in ('migration/bundled-bootstrap/service.py','migration/bundled-bootstrap/resources/lib/drivelibrary.py',
            'migration/bundled-bootstrap/resources/lib/netcheck.py','migration/ios/userdata/addon_data/plugin.googledrive/settings.xml',
            'scripts/build_ios_config.py','migration/google-drive/source-lock.json'):
   self.assertNotIn('drive.signinserver.com',(ROOT/p).read_text(),p)
if __name__=='__main__':unittest.main()
