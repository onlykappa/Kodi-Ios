"""Umbrella pin fetch (host test against a local git repository standing in for upstream; the real upstream is not contacted)."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fetch_umbrella as fu, provider_addons as pa
ROOT=Path(__file__).resolve().parents[1]

def g(args,cwd):return subprocess.run(['git']+args,cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()

class Fetch(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.up=self.root/'up';self.up.mkdir()
  g(['init','-q'],self.up);g(['config','user.email','t@t'],self.up);g(['config','user.name','t'],self.up);g(['config','uploadpack.allowAnySHA1InWant','true'],self.up);g(['config','uploadpack.allowFilter','true'],self.up)
  self.data=b'PK-fake-zip-bytes'*50;path=self.up/'omega/zips/p/p-1.0.zip';path.parent.mkdir(parents=True);path.write_bytes(self.data)
  g(['add','.'],self.up);g(['commit','-q','-m','1.0'],self.up);self.commit=g(['rev-parse','HEAD'],self.up);self.blob=g(['rev-parse','HEAD:omega/zips/p/p-1.0.zip'],self.up)
  self.lock={'package':{'id':'p','version':'1.0','upstream_repository':'x','commit':self.commit,'zip_path':'omega/zips/p/p-1.0.zip','git_blob':self.blob,'sha256':hashlib.sha256(self.data).hexdigest(),'size':len(self.data)}}
 def tearDown(self):self.tmp.cleanup()
 def test_exact_commit_is_fetched_and_verified(self):
  self.assertEqual(fu.fetch(self.lock,remote=str(self.up)),self.data)
 def test_wrong_pins_are_refused(self):
  for key,value in (('sha256','0'*64),('size',5),('git_blob','1'*40)):
   bad=json.loads(json.dumps(self.lock));bad['package'][key]=value
   with self.assertRaises((ValueError,subprocess.CalledProcessError)):fu.fetch(bad,remote=str(self.up))
 def test_a_preserved_copy_is_used_by_digest_with_no_network(self):
  keep=self.root/'keep';keep.mkdir();(keep/'whatever.bin').write_bytes(self.data)
  self.assertEqual(fu.fetch(self.lock,remote='/nonexistent/never-contacted',preserved=keep),self.data)
  (keep/'whatever.bin').write_bytes(self.data+b'x')
  with self.assertRaises(subprocess.CalledProcessError):fu.fetch(self.lock,remote='/nonexistent/never-contacted',preserved=keep)
 def test_the_real_lock_is_well_formed(self):
  p=json.loads((ROOT/'migration/umbrella/source-lock.json').read_text())['package']
  self.assertEqual((p['id'],p['version'],len(p['sha256']),len(p['commit']),len(p['git_blob'])),('plugin.video.umbrella','6.8.02',64,40,40));self.assertFalse(p['native_code'])

if __name__=='__main__':unittest.main()
