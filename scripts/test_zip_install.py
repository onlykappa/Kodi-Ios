"""Install from a zip file (zip_install.py, ISSUE-497)."""
import os,sys,tempfile,time,unittest,zipfile
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','migration','bundled-bootstrap','resources','lib'))
import zip_install as z

MANIFEST='<?xml version="1.0"?><addon id="plugin.video.example" name="Example Streams" version="2.4.1">'\
 '<requires><import addon="xbmc.python" version="3.0.0"/><import addon="script.module.requests"/><import addon="script.module.opt" optional="true"/></requires>'\
 '<extension point="xbmc.python.pluginsource" library="default.py"><provides>video</provides></extension></addon>'

def make(path,files):
 with zipfile.ZipFile(path,'w') as f:
  for name,data in files.items():f.writestr(name,data)

class ZipInstall(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def good(self,name='plugin.video.example-2.4.1.zip'):
  p=os.path.join(self.d,name);make(p,{'plugin.video.example/addon.xml':MANIFEST,'plugin.video.example/default.py':'print(1)','plugin.video.example/res/a.txt':'x'});return p
 def test_inspect_reads_the_manifest(self):
  info=z.inspect(self.good())
  self.assertTrue(info['ok']);self.assertEqual((info['id'],info['name'],info['version'],info['kind']),('plugin.video.example','Example Streams','2.4.1','Video add-on'))
  self.assertEqual(info['requires'],['xbmc.python','script.module.requests']);self.assertEqual(info['optional'],['script.module.opt'])
  self.assertEqual(z.describe(info),'Version 2.4.1 · Video add-on')
 def test_missing_ignores_kodis_own_and_installed(self):
  self.assertEqual(z.missing(['xbmc.python','kodi.binary.global.main','script.module.requests','script.module.x'],['script.module.requests']),['script.module.x'])
 def test_bad_zips_are_refused_in_plain_words(self):
  p=os.path.join(self.d,'a.zip');make(p,{'a.txt':'x','b/c.txt':'y'});self.assertFalse(z.inspect(p)['ok'])
  open(os.path.join(self.d,'b.zip'),'wb').write(b'not a zip');self.assertFalse(z.inspect(os.path.join(self.d,'b.zip'))['ok'])
  p=os.path.join(self.d,'c.zip');make(p,{'plugin.video.other/addon.xml':MANIFEST});self.assertIn('id does not match',z.inspect(p)['reason'])
  p=os.path.join(self.d,'d.zip');make(p,{'plugin.video.example/addon.xml':MANIFEST,'plugin.video.example/../../evil.txt':'x'});self.assertFalse(z.inspect(p)['ok'])
 def test_unpack_stays_inside_the_addons_folder(self):
  dest=os.path.join(self.d,'addons');os.makedirs(dest)
  out=z.unpack(self.good(),'plugin.video.example',dest)
  self.assertTrue(os.path.isfile(os.path.join(out,'addon.xml')));self.assertTrue(os.path.isfile(os.path.join(out,'res','a.txt')))
  evil=os.path.join(self.d,'e.zip');make(evil,{'plugin.video.example/addon.xml':MANIFEST,'plugin.video.example/../x.txt':'x'})
  with self.assertRaises(ValueError):z.unpack(evil,'plugin.video.example',dest)
  self.assertFalse(os.path.exists(os.path.join(dest,'x.txt')))
 def test_find_zips_is_newest_first_and_top_level_only(self):
  a=os.path.join(self.d,'in');b=os.path.join(self.d,'home');os.makedirs(a);os.makedirs(os.path.join(b,'deep'))
  for folder,name,age in ((a,'old.zip',500),(b,'new.zip',10),(b,'notes.txt',5),(os.path.join(b,'deep'),'hidden.zip',1)):
   path=os.path.join(folder,name);open(path,'wb').write(b'x'*2048);t=time.time()-age;os.utime(path,(t,t))
  got=z.find_zips([(a,'Shared with Kodi'),(b,'Kodi folder'),(os.path.join(self.d,'nope'),'x')])
  self.assertEqual([(g['name'],g['where']) for g in got],[('new.zip','Kodi folder'),('old.zip','Shared with Kodi')])
 def test_texts(self):
  self.assertEqual(z.size_text(4400000),'4.2 MB');self.assertEqual(z.size_text(310000),'303 KB');self.assertEqual(z.when_text(time.time()-60),'Today')

if __name__=='__main__':unittest.main()
