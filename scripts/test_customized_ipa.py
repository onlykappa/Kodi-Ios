import json,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from build_customized_ipa import prepare,patch_drive,DRIVE_PATCHES,DRIVE_COMMON,BOOT
from test_import_profile import make_bundle
class BundleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.app=self.root/'original/Kodi.app';base=self.app/'AppData/AppHome';(base/'system').mkdir(parents=True);(base/'addons').mkdir();(base/'system/addon-manifest.xml').write_text('<addons><addon>xbmc.python</addon></addons>');self.bundle=self.root/'bundle.zip';self.sha=make_bundle(self.bundle)
 def tearDown(self):self.tmp.cleanup()
 def test_drive_requests_get_timeout_and_certifi_context(self):
  base=self.root/'addons'/DRIVE_COMMON
  for name,before,_ in DRIVE_PATCHES:
   path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((path.read_bytes() if path.exists() else b'x\n')+before)
  receipt=patch_drive(self.root/'addons');self.assertEqual(len(receipt),4)
  for name,_,after in DRIVE_PATCHES:self.assertIn(after,(base/name).read_bytes())
  with self.assertRaises(AssertionError):patch_drive(self.root/'addons')
 def test_packaged_sources_manifest_seed_and_original_preserved(self):
  app,receipt=prepare(self.app,self.bundle,self.sha,self.root/'work');base=app/'AppData/AppHome';xml=ET.parse(base/'system/addon-manifest.xml').getroot()
  self.assertEqual(xml.find("addon[.='fixture.addon']").get('optional'),'true');self.assertIsNone(xml.find("addon[.='"+BOOT+"']").get('optional'))
  self.assertTrue((base/'addons'/BOOT/'service.py').is_file());self.assertTrue((base/'addons'/BOOT/'recover.py').is_file());self.assertTrue((base/'addons/fixture.addon/resources/settings.xml').is_file())
  seed=json.loads((base/'addons'/BOOT/'seed/seed-manifest.json').read_text());self.assertEqual(seed['addons'],['fixture.addon']);self.assertEqual(len(seed['files']),3)
  self.assertFalse((self.app/'AppData/AppHome/addons/fixture.addon').exists());self.assertEqual(len(ET.parse(self.app/'AppData/AppHome/system/addon-manifest.xml').getroot()),1)
 def test_corrupt_input_rejected_before_any_copy(self):
  with self.assertRaises(Exception):prepare(self.app,self.bundle,'bad',self.root/'work')
  self.assertFalse((self.root/'work').exists())
 def test_overlapping_source_and_work_rejected(self):
  with self.assertRaises(AssertionError):prepare(self.app,self.bundle,self.sha,self.app/'nested')
if __name__=='__main__':unittest.main()
