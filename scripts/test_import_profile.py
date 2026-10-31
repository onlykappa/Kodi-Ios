import io,json,hashlib,stat,tempfile,unittest,zipfile
from pathlib import Path
from import_runtime.safe_import import prepare_export,apply_bundle,restore_clean,validate_bundle,snapshot_hashes,ImportFailure,MARKER,export_private_profile

def zipbytes(files):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w') as z:
  for name,data in files.items():z.writestr(name,data)
 return stream.getvalue()

def make_bundle(path,missing=False,dependency='3.0.0',bad_member=None):
 addon={'fixture.addon/addon.xml':f'<addon id="fixture.addon" version="1.0.0"><requires><import addon="xbmc.python" version="{dependency}"/></requires></addon>'.encode(),'fixture.addon/main.py':b'# fixture source\n','fixture.addon/resources/settings.xml':b'<settings version="1"><category label="Fixture"><setting id="safe.flag" type="bool" default="true"/></category></settings>'}
 if bad_member:addon[bad_member]=b'fixture'
 files={'addons/fixture.addon.zip':zipbytes(addon),'configuration/userdata/guisettings.xml':b'<settings version="2"><setting id="lookandfeel.skin">skin.arctic.fuse.3</setting><setting id="safe.preference">true</setting></settings>','configuration/userdata/addon_data/fixture.addon/settings.xml':b'<settings><setting id="safe.option">true</setting></settings>'}
 entries=[]
 for name,data in files.items():
  entry={'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'kind':'addon' if name.startswith('addons/') else 'configuration'}
  if entry['kind']=='addon':entry.update(addon_id='fixture.addon',version='1.0.0')
  entries.append(entry)
 manifest={'schema':1,'files':entries,'addon_ids':['fixture.addon','missing.addon'] if missing else ['fixture.addon'],'provided_addons':{'xbmc.python':{'version':'3.0.1'}}}
 files['manifest.json']=json.dumps(manifest).encode();path.write_bytes(zipbytes(files));return hashlib.sha256(path.read_bytes()).hexdigest()
class ImportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.source=self.base/'export/Kodi';(self.source/'userdata').mkdir(parents=True)
  (self.source/'userdata/guisettings.xml').write_text('<settings version="2"><setting id="lookandfeel.skin">skin.estuary</setting><setting id="audio.device">target-device</setting></settings>')
  private_dir=self.source/'userdata/addon_data/fixture.addon';private_dir.mkdir(parents=True);self.private_value='fixture-'+'existing-account-value'
  (private_dir/'accounts.db').write_text(self.private_value)
  (private_dir/'settings.xml').write_text('<settings><setting id="account.reference">'+self.private_value+'</setting></settings>')
  self.target=prepare_export(self.source,self.base/'work/Kodi');self.bundle=self.base/'bundle.zip';self.sha=make_bundle(self.bundle);self.backups=self.base/'backups';self.before=snapshot_hashes(self.target);self.source_before=snapshot_hashes(self.source)
 def tearDown(self):self.temp.cleanup()
 def apply(self,**kw):return apply_bundle(self.bundle,self.target,self.backups,self.sha,**kw)
 def unchanged(self):self.assertEqual(snapshot_hashes(self.target),self.before);self.assertEqual(snapshot_hashes(self.source),self.source_before)
 def test_success_preserves_target_settings_and_account_state(self):
  result=self.apply();self.assertEqual(result['status'],'APPLIED TO PRIVATE STAGING')
  self.assertIn('skin.estuary',(self.target/'userdata/guisettings.xml').read_text());self.assertIn('target-device',(self.target/'userdata/guisettings.xml').read_text())
  self.assertIn(self.private_value,(self.target/'userdata/addon_data/fixture.addon/settings.xml').read_text());self.assertEqual((self.target/'userdata/addon_data/fixture.addon/accounts.db').read_text(),self.private_value)
  self.assertEqual(snapshot_hashes(self.source),self.source_before)
 def test_addon_settings_definitions_copied_byte_for_byte(self):
  self.apply()
  expected=b'<settings version="1"><category label="Fixture"><setting id="safe.flag" type="bool" default="true"/></category></settings>'
  self.assertEqual((self.target/'addons/fixture.addon/resources/settings.xml').read_bytes(),expected)
 def test_missing_addon_rejected_before_changes(self):
  self.sha=make_bundle(self.bundle,missing=True)
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
 def test_corrupt_archive_checksum_rejected(self):
  self.bundle.write_bytes(self.bundle.read_bytes()+b'corrupted')
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
 def test_corrupt_content_manifest_rejected(self):
  files={'manifest.json':b'{bad'};self.bundle.write_bytes(zipbytes(files));self.sha=hashlib.sha256(self.bundle.read_bytes()).hexdigest()
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
 def test_repeat_import_is_noop(self):
  self.apply();before=snapshot_hashes(self.target);r=self.apply();self.assertEqual(r['writes'],0);self.assertEqual(snapshot_hashes(self.target),before)
 def test_local_managed_changes_are_not_overwritten(self):
  self.apply();p=self.target/'addons/fixture.addon/main.py';p.write_text('# owner changed source\n')
  with self.assertRaises(ImportFailure):self.apply()
  self.assertEqual(p.read_text(),'# owner changed source\n')
 def test_partial_staging_failure_preserves_clean_target(self):
  with self.assertRaises(ImportFailure):self.apply(fail_at='staging')
  self.unchanged()
 def test_mid_commit_failure_restores_original(self):
  with self.assertRaises(ImportFailure):self.apply(fail_at='commit')
  self.unchanged()
 def test_restore_clean_profile_matches_all_hashes(self):
  r=self.apply();restore_clean(Path(r['backup']),self.target);self.unchanged()
 def test_missing_dependency_version_rejected(self):
  self.sha=make_bundle(self.bundle,dependency='99.0.0')
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
 def test_nested_path_traversal_rejected(self):
  self.sha=make_bundle(self.bundle,bad_member='../escape')
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged();self.assertFalse((self.base/'escape').exists())
 def test_native_addon_payload_rejected(self):
  self.sha=make_bundle(self.bundle,bad_member='fixture.addon/engine.so')
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
 def test_private_export_roundtrip_and_no_nested_output(self):
  self.apply();out=self.base/'private-profile.zip';r=export_private_profile(self.target,out)
  self.assertFalse(r['publish_to_github'])
  with zipfile.ZipFile(out) as z:self.assertEqual(z.read('Kodi/userdata/addon_data/fixture.addon/accounts.db').decode(),self.private_value)
  with self.assertRaises(ImportFailure):export_private_profile(self.target,self.target/'recursive.zip')
 def test_unmarked_target_rejected(self):
  (self.target/MARKER).unlink()
  with self.assertRaises(ImportFailure):self.apply()
 def test_working_deck_path_rejected_even_with_marker(self):
  fake=self.base/'.var/app/tv.kodi.Kodi';fake.mkdir(parents=True);(fake/MARKER).write_text('{}')
  with self.assertRaises(ImportFailure):prepare_export(self.source,fake/'new-staging')
 def test_nested_project_repository_rejected(self):
  repo=self.base/'other-project';(repo/'.git').mkdir(parents=True)
  with self.assertRaises(ImportFailure):prepare_export(self.source,repo/'private-profile')
 def test_symlink_profile_rejected(self):
  (self.target/'outside').symlink_to(self.source,target_is_directory=True)
  with self.assertRaises(ImportFailure):self.apply()
 def test_case_colliding_addon_files_rejected(self):
  self.sha=make_bundle(self.bundle,bad_member='fixture.addon/MAIN.py')
  with self.assertRaises(ImportFailure):self.apply()
  self.unchanged()
if __name__=='__main__':unittest.main()
