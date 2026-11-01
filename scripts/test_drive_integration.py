import json,hashlib,shutil,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from check_drive_integration import check
ROOT=Path(__file__).resolve().parents[1]
class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for name in ['migration','reports','inventory']:shutil.copytree(ROOT/name,self.root/name)
  self.settings=self.root/'migration/ios/userdata/addon_data/plugin.googledrive/settings.xml'
 def tearDown(self):self.tmp.cleanup()
 def change(self,key,value):
  tree=ET.parse(self.settings);found=tree.getroot().find("setting[@id='"+key+"']")
  if found is None:found=ET.SubElement(tree.getroot(),'setting',id=key)
  found.text=value;tree.write(self.settings,encoding='unicode')
 def test_current_integration(self):self.assertTrue(check(self.root)['passed'])
 def test_unapproved_relay(self):
  self.change('sign-in-server','https://unapproved.example')
  with self.assertRaises(AssertionError):check(self.root)
 def test_account_state_rejected(self):
  self.change('access_token','fixture')
  with self.assertRaises(AssertionError):check(self.root)
 def test_optional_directory_listing_rejected(self):
  self.change('allow_directory_listing','true')
  with self.assertRaises(AssertionError):check(self.root)
 def test_missing_drive_root(self):
  p=self.root/'migration/ios/addon-plan.json';v=json.loads(p.read_text());v['roots'].remove('plugin.googledrive');p.write_text(json.dumps(v))
  with self.assertRaises(AssertionError):check(self.root)
if __name__=='__main__':unittest.main()
