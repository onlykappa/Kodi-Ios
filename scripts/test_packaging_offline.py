"""Packaging without upstream hosts (roadmap step 12): preserved inputs are used by digest, tampering is refused, a staged bundle searches on its own."""
import json,os,shutil,socket,subprocess,sys,tempfile,textwrap,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import provider_addons as providers
from test_provider_addons import archive
ROOT=Path(__file__).resolve().parents[1]

def blocked(url):raise OSError('network blocked')

class Offline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.keep=self.root/'preserved';self.keep.mkdir();self.out=self.root/'out'
  self.a=archive('plugin.one');self.b=archive('plugin.two')
  self.lock=dict(schema=1,packages=[dict(id=i,version='1.0.0',url='https://example.invalid/%s.zip'%i,sha256=providers.digest(d)) for i,d in (('plugin.one',self.a),('plugin.two',self.b))],provider_packages=[],core_dependencies=['xbmc.python'])
  (self.keep/'any-name-one.bin').write_bytes(self.a);(self.keep/'sub').mkdir();(self.keep/'sub/other.zip').write_bytes(self.b)
 def tearDown(self):self.tmp.cleanup()
 def test_build_staging_needs_no_network_when_preserved_inputs_exist(self):
  def no_socket(*a,**k):raise AssertionError('network used')
  with patch.object(socket.socket,'connect',no_socket):
   receipt=providers.run(self.out,self.lock,get=blocked,preserved=self.keep)
  self.assertEqual([r['id'] for r in receipt['packages']],['plugin.one','plugin.two']);self.assertEqual((self.out/'plugin.one.zip').read_bytes(),self.a)
 def test_files_are_matched_by_digest_not_by_name(self):
  (self.keep/'any-name-one.bin').unlink();(self.keep/'plugin.one-1.0.0.zip').write_bytes(self.a+b'tampered')   # right name, wrong bytes
  with self.assertRaises(OSError):providers.run(self.out,self.lock,get=blocked,preserved=self.keep)
 def test_a_tampered_preserved_copy_never_replaces_a_good_download(self):
  (self.keep/'any-name-one.bin').write_bytes(b'x'*10)
  receipt=providers.run(self.out,self.lock,get=lambda url:{'plugin.one':self.a,'plugin.two':self.b}[url.rsplit('/',1)[1][:-4]],preserved=self.keep)
  self.assertEqual((self.out/'plugin.one.zip').read_bytes(),self.a);self.assertEqual(len(receipt['packages']),2)
 def test_partial_preserved_set_falls_back_to_the_network_only_for_the_rest(self):
  (self.keep/'sub/other.zip').unlink();asked=[]
  def get(url):asked.append(url);return self.b
  providers.run(self.out,self.lock,get=get,preserved=self.keep);self.assertEqual(asked,['https://example.invalid/plugin.two.zip'])
 def test_a_wrong_download_is_still_rejected_without_a_preserved_copy(self):
  with self.assertRaisesRegex(ValueError,'digest'):providers.run(self.out,self.lock,get=lambda url:b'changed')
 def test_symlinks_and_empty_folders_are_ignored(self):
  (self.keep/'link').symlink_to(self.keep/'any-name-one.bin');self.assertEqual(len(providers.preserved_store(self.keep)),2);self.assertEqual(providers.preserved_store(None),{})

class ElementumInputs(unittest.TestCase):
 def setUp(self):
  import fetch_elementum_inputs as fe;self.fe=fe
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.keep=self.root/'keep';self.keep.mkdir();self.out=self.root/'out'
  self.blobs={'client':b'client-bytes','framework':b'framework-bytes','burst':b'burst-bytes','extra':b'extra-bytes'}
  d=providers.digest
  self.lock={'plugin_release':{'client_zip_url':'https://x.invalid/client.zip','client_zip_sha256':d(self.blobs['client'])},
   'framework_release':{'tag':'t','asset':'a.zip','sha256':d(self.blobs['framework'])},'burst':{'url':'https://x.invalid/burst.zip','sha256':d(self.blobs['burst'])},
   'extras':{'script.extra':{'url':'https://x.invalid/e.zip','sha256':d(self.blobs['extra']),'install':'app'}},'modules':[]}
  for i,(k,v) in enumerate(self.blobs.items()):(self.keep/('f%d.bin'%i)).write_bytes(v)
 def tearDown(self):self.tmp.cleanup()
 def run_it(self,get,preserved):return self.fe.run(self.out,self.lock,get=get,modules=lambda specs,dest:dest.mkdir(parents=True,exist_ok=True),airplay={'tag':'t','asset':'a'},mirror=None,preserved=preserved)
 def test_client_framework_burst_and_extras_come_from_the_preserved_folder_with_no_network(self):
  receipt=self.run_it(blocked,self.keep);self.assertTrue(receipt['elementum']);self.assertEqual((self.out/'framework.zip').read_bytes(),self.blobs['framework']);self.assertEqual((self.out/'extras-app/script.extra.zip').read_bytes(),self.blobs['extra'])
 def test_a_tampered_preserved_file_is_not_used(self):
  for f in self.keep.iterdir():f.write_bytes(f.read_bytes()+b'x')
  with self.assertRaises(OSError):self.run_it(blocked,self.keep)
 def test_without_a_preserved_folder_behaviour_is_unchanged(self):
  with self.assertRaises(OSError):self.run_it(blocked,None)

class Staged(unittest.TestCase):
 def test_a_staged_bundle_restarts_and_searches_with_no_network_and_no_repo(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);boot=Path(tmp.name)/'service.kodi.ios.bootstrap'
  shutil.copytree(ROOT/'migration/bundled-bootstrap',boot,ignore=shutil.ignore_patterns('__pycache__'))     # what build_customized_ipa does
  code=textwrap.dedent('''
   import json,sys
   sys.path[:0]=[sys.argv[1]+'/resources/lib']
   import independent_sites as s, provider_fallback as f, source_contract as c
   H='%040x'
   page=json.dumps([{'id':'1','name':'Example.Film.2024.1080p.WEB-DL.x264','info_hash':H%1,'seeders':'40','size':'2000000000'}])
   def fetch(url,timeout):
       if url.startswith('https://apibay.org'):return page
       raise ConnectionError('blocked')
   out,found,report=s.search_all({'media_type':'movie','title':'Example Film','year':2024,'profile':{}},fetch=fetch)
   print(json.dumps([out,[i['torrent_hash'] for i in found],report.get('apibay')]))
  ''')
  cmd=[sys.executable,'-I','-c',code,str(boot)]
  if shutil.which('unshare') and subprocess.run(['unshare','-rn','true']).returncode==0:cmd=['unshare','-rn']+cmd
  run=subprocess.run(cmd,capture_output=True,text=True,cwd=tmp.name,timeout=60);self.assertEqual(run.returncode,0,run.stderr[-400:])
  self.assertEqual(json.loads(run.stdout.strip().splitlines()[-1]),['ok',['%040x'%1],'ok'])

class NoCodeDownloads(unittest.TestCase):
 def test_the_update_flow_saves_a_file_and_never_runs_downloaded_code(self):
  text=(ROOT/'migration/bundled-bootstrap/resources/lib/updates.py').read_text()
  for forbidden in ('exec(','eval(','importlib','__import__','subprocess','os.system','compile(','runpy'):self.assertNotIn(forbidden,text,forbidden)
  self.assertIn('Kodi Updates',text)          # the IPA lands where the Files app and the sideloader find it; the signed install path stays outside the app

if __name__=='__main__':unittest.main()
