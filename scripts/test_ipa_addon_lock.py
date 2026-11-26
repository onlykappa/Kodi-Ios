"""Per-add-on IPA lock: digests are stable, ignore bytecode, and comparing reports added, removed and changed add-ons."""
import json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ipa_addon_lock as L
ROOT=Path(__file__).resolve().parents[1]
P=L.PREFIX
def ipa(files,path):
 with zipfile.ZipFile(path,'w') as z:
  for n,b in files.items():z.writestr(P+n,b)
class Lock(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.a=self.d/'a.ipa';self.b=self.d/'b.ipa'
  self.base={'plugin.x/addon.xml':'<addon id="plugin.x" version="1.2">','plugin.x/a.py':'print(1)','plugin.y/addon.xml':'<addon id="plugin.y" version="3">'}
  ipa(self.base,self.a)
 def tearDown(self):self.tmp.cleanup()
 def test_digest_version_and_bytecode_is_ignored(self):
  d=L.digest_ipa(self.a);self.assertEqual((d['plugin.x']['version'],d['plugin.x']['files']),('1.2',2));self.assertEqual(L.digest_ipa(self.a),d)
  ipa(dict(self.base,**{'plugin.x/__pycache__/a.cpython-311.pyc':b'x','plugin.x/b.pyc':b'y'}),self.b);self.assertEqual(L.digest_ipa(self.b),d)
 def test_compare_reports_added_removed_and_changed(self):
  lock={'addons':L.digest_ipa(self.a)};files=dict(self.base);files['plugin.x/a.py']='print(2)';del files['plugin.y/addon.xml'];files['plugin.z/addon.xml']='<addon version="9">'
  ipa(files,self.b);self.assertEqual(L.compare(self.b,lock),{'added':['plugin.z'],'removed':['plugin.y'],'changed':['plugin.x']});self.assertEqual(L.compare(self.a,lock),{'added':[],'removed':[],'changed':[]})
 def test_committed_lock_covers_the_ipa_add_ons_and_the_pinned_provider_set(self):
  lock=json.loads((ROOT/'migration/ipa-addons/build-679.json').read_text());a=lock['addons'];self.assertGreater(len(a),100)
  for must in ('plugin.video.elementum','script.elementum.burst','plugin.video.thecrew','plugin.video.jacktook','plugin.video.pov','skin.arctic.fuse.3','plugin.video.themoviedb.helper','service.kodi.ios.bootstrap'):self.assertIn(must,a)
  self.assertRegex(lock['ipa']['sha256'],r'^[0-9a-f]{64}$')
if __name__=='__main__':unittest.main()
