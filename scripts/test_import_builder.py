import ast,unittest,xml.etree.ElementTree as ET
from build_import_review import patch_helper,clean_addon,deterministic_zip
class BuilderTests(unittest.TestCase):
 def fixture(self):
  p='plugin.video.themoviedb.helper/'
  return p,{p+'addon.xml':b'<addon id="plugin.video.themoviedb.helper" version="6.18.1"><requires><import addon="xbmc.python" version="3.0.1"/></requires></addon>',p+'resources/tmdbhelper/lib/player/dialog/player.py':b'class Player:\n    def get_player(self):\n        return self.autoplay()\n\n    def untouched(self):\n        return 42\n',p+'resources/tmdbhelper/lib/items/listitem.py':b'class Item:\n    def url(self):\n        return BuildURL(self.path, **self.params).url\n'}
 def test_patch_requires_explicit_choice_and_retains_other_methods(self):
  p,files=self.fixture();out,_=patch_helper(files,'plugin.video.themoviedb.helper');source=out[p+'resources/tmdbhelper/lib/player/dialog/player.py'].decode();ast.parse(source)
  self.assertNotIn('self.autoplay()',source);self.assertIn('if selected else None',source);self.assertIn('return 42',source)
  root=ET.fromstring(out[p+'addon.xml']);self.assertEqual(root.get('version'),'6.18.1+ios.1');self.assertIsNotNone(root.find("requires/import[@addon='plugin.video.kodi.ios.watch']"))
 def test_changed_patch_hook_stops_instead_of_shipping_autoplay(self):
  p,files=self.fixture();files[p+'resources/tmdbhelper/lib/items/listitem.py']=b'# upstream hook changed\n'
  with self.assertRaises(AssertionError):patch_helper(files,'plugin.video.themoviedb.helper')
 def test_duplicate_resolver_hook_is_rejected(self):
  p,files=self.fixture();files[p+'resources/tmdbhelper/lib/player/dialog/player.py']+=b'\ndef get_player():\n    pass\n'
  with self.assertRaises(AssertionError):patch_helper(files,'plugin.video.themoviedb.helper')
 def test_public_archive_id_version_mismatch_rejected(self):
  p,files=self.fixture()
  with self.assertRaises(AssertionError):clean_addon(deterministic_zip(files),{'id':'plugin.video.themoviedb.helper','version':'0.0.0'})
 def test_versioned_root_and_macos_metadata_normalized(self):
  p,files=self.fixture();versioned={k.replace(p,'plugin.video.themoviedb.helper-6.18.1/',1):v for k,v in files.items()};versioned['__MACOSX/._artifact']=b'packaging metadata'
  data,ver,_=clean_addon(deterministic_zip(versioned),{'id':'plugin.video.themoviedb.helper','version':'6.18.1','url':'https://example.invalid/public-addon.zip'});self.assertEqual(ver,'6.18.1+ios.1')
  from import_runtime.safe_import import archive_files
  self.assertTrue(all(n.startswith(p) for n in archive_files(data)))
 def test_unknown_sibling_archive_payload_rejected(self):
  p,files=self.fixture();files['unexpected/extra.py']=b'# extra'
  with self.assertRaises(AssertionError):clean_addon(deterministic_zip(files),{'id':'plugin.video.themoviedb.helper','version':'6.18.1','url':'https://example.invalid/public-addon.zip'})
if __name__=='__main__':unittest.main()
