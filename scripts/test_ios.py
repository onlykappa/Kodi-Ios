import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
import check_ios
import build_ios_config
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class IOSTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for name in ['migration','reports','inventory','snapshot']:shutil.copytree(ROOT/name,self.root/name)
 def tearDown(self):self.tmp.cleanup()
 def refresh(self):
  p=self.root/'migration/ios/manifest.json';v=json.loads(p.read_text())
  for entry in v['files']:entry['sha256']=hashlib.sha256((p.parent/entry['path']).read_bytes()).hexdigest()
  p.write_text(json.dumps(v))
 def test_static(self):self.assertTrue(check_ios.check(self.root)['passed'])
 def test_reproducible(self):
  before={str(p.relative_to(self.root/"migration/ios")):p.read_bytes() for p in (self.root/"migration/ios").rglob("*") if p.is_file()}
  with patch.multiple(build_ios_config,ROOT=self.root,DEST=self.root/"migration/ios"):build_ios_config.build()
  after={str(p.relative_to(self.root/"migration/ios")):p.read_bytes() for p in (self.root/"migration/ios").rglob("*") if p.is_file()}
  self.assertEqual(before,after)
 def test_youtube_removed_from_target_only(self):
  target=self.root/'migration/ios';plan=json.loads((target/'addon-plan.json').read_text())
  self.assertFalse(any('youtube' in x['id'] for x in plan['addons']))
  for path in (target/'userdata').rglob('*'):
   if path.is_file():self.assertNotIn('plugin.video.youtube',path.read_text().lower())
  self.assertTrue((self.root/'snapshot/userdata/addon_data/plugin.video.themoviedb.helper/players/deck.elementum.json').exists())
 def test_longpress_normal_context_menu(self):
  import xml.etree.ElementTree as ET
  touch=ET.parse(self.root/'migration/ios/userdata/keymaps/ios-touch.xml').getroot()
  self.assertEqual(touch.find('global/touch/longpress').text,'ContextMenu')
 def test_modified_file(self):
  (self.root/'migration/ios/userdata/guisettings.xml').write_text('<settings/>')
  with self.assertRaises(AssertionError):check_ios.check(self.root)
 def test_excluded_backend(self):
  p=self.root/'migration/ios/userdata/guisettings.xml';p.write_text('<settings><setting>plugin.video.'+'umbrella</setting></settings>');self.refresh()
  with self.assertRaises(AssertionError):check_ios.check(self.root)
 def test_missing_dependency(self):
  p=self.root/'migration/ios/addon-plan.json';v=json.loads(p.read_text());v['addons']=[a for a in v['addons'] if a['id']!='xbmc.python'];p.write_text(json.dumps(v));self.refresh()
  with self.assertRaises(AssertionError):check_ios.check(self.root)
 def test_lower_dependency_version(self):
  p=self.root/'migration/ios/addon-plan.json';v=json.loads(p.read_text())
  for a in v['addons']:
   if a['id']=='script.skinvariables':a['source_version_candidate']='0.0.0'
  p.write_text(json.dumps(v));self.refresh()
  with self.assertRaises(AssertionError):check_ios.check(self.root)
if __name__=='__main__':unittest.main()
