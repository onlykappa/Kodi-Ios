import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from package_drive_addons import package
class PackageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cache=self.root/'cache';self.addon=self.cache/'plugin.example';self.addon.mkdir(parents=True)
  self.data={'addon.xml':b'<addon id="plugin.example" version="1.0.0"/>','entry.py':b'print("example")\n','LICENSE.txt':b'Fixture license\n'}
  self.lock={'repositories':[{'addon_id':'plugin.example','version':'1.0.0','commit':'a'*40,'files':[]}]};self.write()
 def tearDown(self):self.tmp.cleanup()
 def write(self):
  files=[]
  for name,data in self.data.items():
   (self.addon/name).write_bytes(data);files.append({'path':name,'bytes':len(data),'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
  self.lock['repositories'][0]['files']=files
 def test_reproducible(self):
  a=package(self.lock,self.cache,self.root/'a');b=package(self.lock,self.cache,self.root/'b');self.assertEqual(a,b)
 def test_tamper_rejected(self):
  (self.addon/'entry.py').write_text('tampered')
  with self.assertRaises(AssertionError):package(self.lock,self.cache,self.root/'out')
 def test_untracked_account_state_not_packaged(self):
  (self.addon/'accounts.db').write_text('private fixture')
  package(self.lock,self.cache,self.root/'out')
  with zipfile.ZipFile(self.root/'out/plugin.example-1.0.0.zip') as archive:self.assertFalse(any('accounts' in name for name in archive.namelist()))
 def test_secret_pattern_rejected(self):
  self.data['entry.py']=('value="'+'AIza'+'A'*35+'"\n').encode();self.write()
  with self.assertRaises(AssertionError):package(self.lock,self.cache,self.root/'out')
if __name__=='__main__':unittest.main()
