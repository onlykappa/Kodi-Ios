import hashlib,importlib.util,json,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bundled_bootstrap',ROOT/'migration/bundled-bootstrap/resources/lib/bootstrap.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BootstrapTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.seed=self.base/'seed';self.profile=self.base/'phone/userdata';self.seed.mkdir();self.profile.mkdir(parents=True);self.calls=[];self.values={'locale.language':'original','input.enablemouse':False,'lookandfeel.skin':'skin.estuary'}
  files={'guisettings.xml':b'<settings><setting id="locale.language">resource.language.en_gb</setting><setting id="input.enablemouse">true</setting></settings>','addon_data/skin/settings.xml':b'<settings><setting id="layout">custom</setting></settings>','playlists/video/test.xsp':b'<smartplaylist/>'}
  entries=[]
  for name,body in files.items():
   p=self.seed/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);entries.append({'path':name,'sha256':hashlib.sha256(body).hexdigest()})
  (self.seed/'seed-manifest.json').write_text(json.dumps({'version':'1','files':entries,'addons':['dep','skin']}))
 def tearDown(self):self.temp.cleanup()
 def api(self,method,params):
  self.calls.append((method,params))
  if method=='Addons.GetAddonDetails':return {'result':{'addon':{'enabled':False,'version':'1'}}}
  if method=='Addons.SetAddonEnabled':return {'result':'OK'}
  if method=='Settings.GetSettingValue':return {'result':{'value':self.values[params['setting']]}}
  self.values[params['setting']]=params['value'];return {'result':True}
 def test_first_setup_and_second_launch_preserves_owner_changes(self):
  self.assertEqual(m.initialize(self.seed,self.profile,self.api),'COMPLETE');p=self.profile/'playlists/video/test.xsp';p.write_bytes(b'owner edit');self.calls=[]
  self.assertEqual(m.initialize(self.seed,self.profile,self.api),'COMPLETE');self.assertEqual(p.read_bytes(),b'owner edit');self.assertEqual(self.calls,[])
 def test_hash_failure_writes_nothing(self):
  (self.seed/'guisettings.xml').write_text('corrupt')
  with self.assertRaises(ValueError):m.initialize(self.seed,self.profile,self.api)
  self.assertEqual(list(self.profile.iterdir()),[])
 def test_missing_addon_writes_nothing(self):
  with self.assertRaises(ValueError):m.initialize(self.seed,self.profile,lambda *a:{'error':{}})
  self.assertEqual(list(self.profile.iterdir()),[])
 def test_partial_failure_restores_old_files(self):
  p=self.profile/'playlists/video/test.xsp';p.parent.mkdir(parents=True);p.write_bytes(b'original')
  with self.assertRaises(RuntimeError):m.initialize(self.seed,self.profile,self.api,fail_after='files')
  self.assertEqual(p.read_bytes(),b'original');self.assertFalse((self.profile/'addon_data/skin/settings.xml').exists())
 def test_explicit_recovery_restores_private_settings_and_gui(self):
  p=self.profile/'addon_data/skin/settings.xml';p.parent.mkdir(parents=True);old=b'<settings><setting id="private.account">synthetic private state</setting></settings>';p.write_bytes(old)
  m.initialize(self.seed,self.profile,self.api);self.assertIn(b'synthetic private state',p.read_bytes());m.restore(self.profile,self.api);self.assertEqual(p.read_bytes(),old);self.assertEqual(self.values['locale.language'],'original');self.assertFalse(self.values['input.enablemouse'])
 def test_never_overwrites_live_core_settings_file(self):
  p=self.profile/'guisettings.xml';p.write_bytes(b'live core settings');m.initialize(self.seed,self.profile,self.api);self.assertEqual(p.read_bytes(),b'live core settings');self.assertEqual(self.values['lookandfeel.skin'],'skin.arctic.fuse.3')
 def test_api_failure_is_not_marked_complete(self):
  def fail(method,params):return {'error':{}} if method=='Settings.SetSettingValue' else self.api(method,params)
  with self.assertRaises(RuntimeError):m.initialize(self.seed,self.profile,fail)
  s=json.loads((self.profile/'addon_data'/m.ID/'status.json').read_text());self.assertNotEqual(s['status'],'COMPLETE')
 def test_symlink_target_refused(self):
  (self.profile/'playlists').symlink_to(self.base,target_is_directory=True)
  with self.assertRaises(ValueError):m.initialize(self.seed,self.profile,self.api)
 def test_skin_rejection_does_not_leave_false_complete_marker(self):
  with self.assertRaises(RuntimeError):m.initialize(self.seed,self.profile,self.api,verify_skin=lambda:False)
  s=json.loads((self.profile/'addon_data'/m.ID/'status.json').read_text());self.assertNotEqual(s['status'],'COMPLETE');self.assertEqual(self.values['lookandfeel.skin'],'skin.estuary')
 def mutable_fixture(self):
  import shutil
  addonroot=self.base/'bundled/addons';seed=addonroot/m.ID/'seed';shutil.copytree(self.seed,seed)
  skin=addonroot/'skin.fixture';(skin/'1080i').mkdir(parents=True);(skin/'addon.xml').write_text('<addon id="skin.fixture" version="1.0.0"/>');(skin/'1080i/generated.xml').write_bytes(b'original source')
  manifest=json.loads((seed/'seed-manifest.json').read_text());manifest['mutable_skins']=[{'id':'skin.fixture','version':'1.0.0','tree_sha256':m.tree_digest(skin)}];(seed/'seed-manifest.json').write_text(json.dumps(manifest));return seed,skin
 def test_writable_skin_copy_preserves_bundle_and_refreshes_before_activation(self):
  seed,skin=self.mutable_fixture();paths=[];home=self.base/'phone'
  self.assertEqual(m.initialize(seed,self.profile,self.api,home=home,refresh=lambda p:paths.extend(p)),'COMPLETE')
  dest=home/'addons/skin.fixture';self.assertEqual(paths,[dest]);(dest/'1080i/generated.xml').write_bytes(b'phone generated')
  self.assertEqual((skin/'1080i/generated.xml').read_bytes(),b'original source')
  self.assertEqual(m.initialize(seed,self.profile,self.api,home=home,refresh=lambda p:None),'COMPLETE');self.assertEqual((dest/'1080i/generated.xml').read_bytes(),b'phone generated')
 def test_existing_skin_version_conflict_preserved(self):
  seed,skin=self.mutable_fixture();home=self.base/'phone';dest=home/'addons/skin.fixture';dest.mkdir(parents=True);xml=b'<addon id="skin.fixture" version="2.0.0"/>';(dest/'addon.xml').write_bytes(xml)
  with self.assertRaises(ValueError):m.initialize(seed,self.profile,self.api,home=home,refresh=lambda p:None)
  self.assertEqual((dest/'addon.xml').read_bytes(),xml)
 def test_corrupt_skin_source_not_copied(self):
  seed,skin=self.mutable_fixture();(skin/'1080i/generated.xml').write_bytes(b'changed')
  with self.assertRaises(ValueError):m.initialize(seed,self.profile,self.api,home=self.base/'phone',refresh=lambda p:None)
  self.assertFalse((self.base/'phone/addons/skin.fixture').exists())
 def test_failed_rescan_does_not_activate_skin_or_mark_complete(self):
  seed,skin=self.mutable_fixture()
  def fail(paths):raise RuntimeError('Kodi path mismatch')
  with self.assertRaises(RuntimeError):m.initialize(seed,self.profile,self.api,home=self.base/'phone',refresh=fail)
  self.assertNotEqual(self.values['lookandfeel.skin'],'skin.arctic.fuse.3');s=json.loads((self.profile/'addon_data'/m.ID/'status.json').read_text());self.assertNotEqual(s['status'],'COMPLETE')
if __name__=='__main__':unittest.main()
