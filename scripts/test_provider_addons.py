"""Packaging contracts for pinned movie/TV source fallback add-ons; no network or IPA construction."""
import copy,io,json,os,sqlite3,stat,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import provider_addons as providers

def archive(id,version='1.0.0',requires='',extensions='',files=None):
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w') as z:
  z.writestr(id+'/addon.xml','<addon id="%s" version="%s"><requires>%s</requires>%s<extension point="xbmc.addon.metadata"><license>GPL-3.0</license></extension></addon>'%(id,version,requires,extensions))
  for name,body in (files or {'LICENSE':'retained license','lib/source.py':'# upstream copyright\n'}).items():z.writestr(id+'/'+name,body)
 return data.getvalue()

class Packaging(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.inputs=self.root/'inputs';self.addons=self.root/'addons';self.boot=self.addons/'service.kodi.ios.bootstrap'
 def tearDown(self):self.tmp.cleanup()
 def spec(self,id,data,**extra):return dict(id=id,version='1.0.0',url='https://example.invalid/'+id+'.zip',sha256=providers.digest(data),**extra)
 def inputs_for(self,specs,archives,**extra):
  lock=dict(schema=1,packages=specs,provider_packages=[],core_dependencies=['xbmc.python'],**extra)
  providers.run(self.inputs,lock,get=lambda url:archives[url.rsplit('/',1)[1][:-4]])
  return lock
 def test_verified_fetch_and_install_preserve_sources_and_license(self):
  data=archive('plugin.fixture');spec=self.spec('plugin.fixture',data)
  lock=self.inputs_for([spec],{'plugin.fixture':data});receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual(receipt['addons'],['plugin.fixture']);self.assertEqual((self.addons/'plugin.fixture/LICENSE').read_text(),'retained license')
  self.assertEqual((self.addons/'plugin.fixture/lib/source.py').read_text(),'# upstream copyright\n')
  self.assertEqual(json.loads((self.boot/'provider-fallback-notices.json').read_text())['source_lock'],lock)
 def test_download_digest_failure_is_rejected(self):
  data=archive('plugin.fixture');spec=self.spec('plugin.fixture',data)
  with self.assertRaisesRegex(ValueError,'download digest'):providers.run(self.inputs,dict(packages=[spec]),get=lambda url:b'changed')
 def test_archive_changed_after_verified_fetch_is_rejected(self):
  data=archive('plugin.fixture');lock=self.inputs_for([self.spec('plugin.fixture',data)],{'plugin.fixture':data});(self.inputs/'plugin.fixture.zip').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'archive digest'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_input_lock_change_is_rejected(self):
  data=archive('plugin.fixture');lock=self.inputs_for([self.spec('plugin.fixture',data)],{'plugin.fixture':data});(self.inputs/'source-lock.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'reviewed source lock'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_manifest_identity_and_version_must_match_lock(self):
  data=archive('plugin.fixture','2.0.0');spec=self.spec('plugin.fixture',data)
  with self.assertRaisesRegex(ValueError,'identity mismatch'):self.inputs_for([spec],{'plugin.fixture':data})
 def test_native_traversal_account_and_link_entries_are_rejected(self):
  for name in ('plugin.fixture/native.so','plugin.fixture/native.DLL','plugin.fixture/../outside','/outside','plugin.fixture/profile/accounts.json','plugin.fixture/settings.xml'):
   with self.subTest(name=name):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:z.writestr(name,'x')
    with self.assertRaises(ValueError):providers.members(data.getvalue(),'plugin.fixture/')
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:
   entry=zipfile.ZipInfo('plugin.fixture/link');entry.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(entry,'/outside')
  with self.assertRaises(ValueError):providers.members(data.getvalue(),'plugin.fixture/')
 def test_foreign_bytecode_is_excluded(self):
  data=archive('plugin.fixture',files={'__pycache__/source.cpython-39.pyc':b'bytecode','source.py':'pass'})
  self.assertEqual(set(providers.members(data,'plugin.fixture/')),{'addon.xml','source.py'})
 def test_new_services_are_disabled_without_losing_other_extensions(self):
  data=archive('plugin.fixture',extensions='<extension point="xbmc.service" library="service.py"/><extension point="xbmc.python.pluginsource" library="main.py"/>')
  spec=self.spec('plugin.fixture',data,remove_services=True);lock=self.inputs_for([spec],{'plugin.fixture':data});receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  xml=ET.parse(self.addons/'plugin.fixture/addon.xml').getroot();self.assertIsNone(xml.find("extension[@point='xbmc.service']"));self.assertIsNotNone(xml.find("extension[@point='xbmc.python.pluginsource']"))
  self.assertEqual(receipt['patches'][0]['before_sha256'],providers.digest(providers.members(data,'plugin.fixture/')['addon.xml']))
 def test_required_service_restored_on_reused_verified_provider(self):
  service='<extension point="xbmc.service" library="service.py"/>'
  data=archive('plugin.fixture',extensions=service,files={'service.py':'# upstream service\n'})
  spec=self.spec('plugin.fixture',data,required_services=['service.py']);lock=self.inputs_for([spec],{'plugin.fixture':data})
  dest=self.addons/'plugin.fixture';dest.mkdir(parents=True)
  (dest/'addon.xml').write_text('<addon id="plugin.fixture" version="1.0.0"><requires/></addon>')
  (dest/'service.py').write_text('# upstream service\n')
  receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual(ET.parse(dest/'addon.xml').getroot().find("extension[@point='xbmc.service']").get('library'),'service.py')
  self.assertEqual(receipt['patches'][0]['changes'],['restored required upstream service'])
  receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual(receipt['patches'],[])
 def test_required_service_rejects_unknown_reused_launcher(self):
  data=archive('plugin.fixture',extensions='<extension point="xbmc.service" library="service.py"/>',files={'service.py':'# upstream service\n'})
  spec=self.spec('plugin.fixture',data,required_services=['service.py']);lock=self.inputs_for([spec],{'plugin.fixture':data})
  dest=self.addons/'plugin.fixture';dest.mkdir(parents=True)
  (dest/'addon.xml').write_text('<addon id="plugin.fixture" version="1.0.0"><requires/></addon>')
  (dest/'service.py').write_text('# unknown service\n')
  with self.assertRaisesRegex(ValueError,'differs from pinned source'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_unused_crew_dependencies_removed_and_source_exclusions_recorded(self):
  data=archive('plugin.fixture',requires='<import addon="script.module.resolveurl.xxx"/><import addon="script.thecrew.artwork"/>',files={'LICENSE':'license','lib/adult/unused.py':'pass','lib/source.py':'pass'})
  spec=self.spec('plugin.fixture',data,remove_requires=['script.module.resolveurl.xxx','script.thecrew.artwork'],exclude_prefixes=['lib/adult/'])
  lock=self.inputs_for([spec],{'plugin.fixture':data});receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual(ET.parse(self.addons/'plugin.fixture/addon.xml').getroot().findall('requires/import'),[])
  self.assertFalse((self.addons/'plugin.fixture/lib/adult/unused.py').exists());self.assertEqual(receipt['excluded'][0]['path'],'lib/adult/unused.py');self.assertTrue((self.addons/'plugin.fixture/LICENSE').is_file())
 def test_context_dependencies_do_not_add_visible_context_actions(self):
  extension='<extension point="kodi.context.item"><menu><item library="default.py"><visible>true</visible></item></menu></extension>'
  data=archive('context.fixture',extensions=extension);spec=self.spec('context.fixture',data,hide_context_menus=True);lock=self.inputs_for([spec],{'context.fixture':data})
  providers.install(self.inputs,self.addons,self.boot,lock);self.assertEqual(ET.parse(self.addons/'context.fixture/addon.xml').findtext('extension/menu/item/visible'),'false')
 def test_dependency_missing_or_too_old_fails_closed(self):
  data=archive('plugin.fixture',requires='<import addon="module.required" version="2.0.0"/>');lock=self.inputs_for([self.spec('plugin.fixture',data)],{'plugin.fixture':data})
  with self.assertRaisesRegex(ValueError,'Missing provider dependency'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_existing_compatible_module_is_reused_without_overwrite(self):
  module=archive('module.required');data=archive('plugin.fixture',requires='<import addon="module.required" version="1.0.0"/>')
  lock=self.inputs_for([self.spec('module.required',module),self.spec('plugin.fixture',data)],{'module.required':module,'plugin.fixture':data})
  existing=self.addons/'module.required';existing.mkdir(parents=True);before='<addon id="module.required" version="2.0.0"/>';(existing/'addon.xml').write_text(before)
  receipt=providers.install(self.inputs,self.addons,self.boot,lock);self.assertEqual(receipt['reused'],[{'id':'module.required','version':'2.0.0'}]);self.assertEqual((existing/'addon.xml').read_text(),before)
 def test_existing_incompatible_module_is_rejected(self):
  module=archive('module.required');data=archive('plugin.fixture',requires='<import addon="module.required" version="1.0.0"/>')
  lock=self.inputs_for([self.spec('module.required',module),self.spec('plugin.fixture',data)],{'module.required':module,'plugin.fixture':data})
  existing=self.addons/'module.required';existing.mkdir(parents=True);(existing/'addon.xml').write_text('<addon id="module.required" version="0.1.0"/>')
  with self.assertRaisesRegex(ValueError,'too old'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_required_writable_copy_is_the_sanitized_source(self):
  data=archive('plugin.fixture',extensions='<extension point="xbmc.service" library="service.py"/>')
  spec=self.spec('plugin.fixture',data,profile_copy=True,remove_services=True);lock=self.inputs_for([spec],{'plugin.fixture':data});receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual(receipt['profile_copies'],['plugin.fixture']);self.assertEqual((self.boot/'payload/plugin.fixture/addon.xml').read_bytes(),(self.addons/'plugin.fixture/addon.xml').read_bytes())
 def test_provider_payload_only_ships_runtime_files_and_licenses(self):
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:
   for name in ('LICENSE','meta.json','providers/pkg/source.py','providerModules/pkg/code.py','README.md','.github/workflows/test.yml'):z.writestr('source-root/'+name,'x')
  body=data.getvalue();spec=dict(name='prism-a4k',root='source-root/',url='https://example.invalid/prism-a4k.zip',sha256=providers.digest(body),destination='provider-fallback/prism-a4k',version='1.0')
  lock=dict(packages=[],provider_packages=[spec],core_dependencies=[]);providers.run(self.inputs,lock,get=lambda url:body);providers.install(self.inputs,self.addons,self.boot,lock)
  dest=self.boot/'provider-fallback/prism-a4k';self.assertTrue((dest/'LICENSE').is_file());self.assertTrue((dest/'providers/pkg/source.py').is_file());self.assertFalse((dest/'.github').exists());self.assertFalse((dest/'README.md').exists())
 def test_complete_license_text_is_verified_and_shipped_with_public_notices(self):
  text=b'Complete licence text';source=self.root/'reviewed/licenses/GPL-3.0.md';source.parent.mkdir(parents=True);source.write_bytes(text)
  lock=dict(packages=[],provider_packages=[],core_dependencies=[],license_texts=[{'path':'licenses/GPL-3.0.md','sha256':providers.digest(text)}]);providers.run(self.inputs,lock,get=lambda url:b'')
  with patch.object(providers,'LOCK',source.parent.parent/'source-lock.json'):providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual((self.boot/'provider-fallback/licenses/GPL-3.0.md').read_bytes(),text)
  source.write_bytes(b'changed')
  with patch.object(providers,'LOCK',source.parent.parent/'source-lock.json'):
   with self.assertRaisesRegex(ValueError,'licence text digest'):providers.install(self.inputs,self.addons,self.boot,lock)
 def test_public_mapping_database_is_verified_and_packaged_outside_user_state(self):
  with sqlite3.connect(':memory:') as database:
   database.execute('CREATE TABLE anime (mal_id INTEGER PRIMARY KEY, themoviedb_id INTEGER)');database.execute('INSERT INTO anime VALUES (1, 2)');data=database.serialize()
  spec=dict(name='otaku-mappings',url='https://example.invalid/mappings.db',sha256=providers.digest(data),bytes=len(data),file='mappings.db',format='sqlite',tables={'anime':['mal_id','themoviedb_id']},destination='provider-fallback/otaku/mappings.db')
  lock=dict(packages=[],provider_packages=[],core_dependencies=[],data_assets=[spec]);providers.run(self.inputs,lock,get=lambda url:data);receipt=providers.install(self.inputs,self.addons,self.boot,lock)
  self.assertEqual((self.boot/'provider-fallback/otaku/mappings.db').read_bytes(),data);self.assertEqual(receipt['data_assets'][0]['bytes'],len(data));self.assertFalse((self.boot/'seed/addon_data').exists())
 def test_mapping_database_with_unexpected_profile_table_or_missing_columns_is_rejected(self):
  with sqlite3.connect(':memory:') as database:
   database.execute('CREATE TABLE anime (mal_id INTEGER)');data=database.serialize()
   with self.assertRaisesRegex(ValueError,'schema mismatch'):providers.validate_asset(data,{'format':'sqlite','tables':{'anime':['themoviedb_id']}})
   database.execute('CREATE TABLE account_tokens (token TEXT)');data=database.serialize()
   with self.assertRaisesRegex(ValueError,'Unexpected.*tables'):providers.validate_asset(data,{'format':'sqlite','tables':{'anime':['mal_id']}})

class ReviewedLock(unittest.TestCase):
 def test_six_fallback_roots_and_dependencies_have_immutable_digest_pins(self):
  lock=json.loads(providers.LOCK.read_text());ids={s['id'] for s in lock['packages']}
  self.assertEqual(set(lock['roots']),{'plugin.video.jacktook','plugin.video.pov','script.module.magneto','plugin.video.otaku','plugin.video.thecrew','plugin.video.prism'})
  self.assertTrue(set(lock['roots'])<=ids)
  for spec in lock['packages']+lock['provider_packages']+lock.get('data_assets',[]):
   self.assertRegex(spec['sha256'],r'^[0-9a-f]{64}$');self.assertTrue(spec['url'].startswith('https://'))
   if 'raw.githubusercontent.com' in spec['url'] or 'codeload.github.com' in spec['url']:self.assertRegex(spec['commit'],r'^[0-9a-f]{40}$');self.assertIn(spec['commit'],spec['url'])
   if spec.get('id') not in lock.get('sports_roots',[]):self.assertFalse(spec.get('id','').startswith('repository.'))   # sports_roots: a real repository add-on, by design
 def test_crew_preserves_required_artwork_and_omits_unused_extensions(self):
  lock=json.loads(providers.LOCK.read_text());specs={s['id']:s for s in lock['packages']}
  self.assertNotIn('script.module.resolveurl.xxx',specs);self.assertIn('script.thecrew.artwork',specs)
  self.assertIn('script.module.resolveurl.xxx',specs['script.module.thecrew']['remove_requires'])
  self.assertNotIn('script.thecrew.artwork',specs['plugin.video.thecrew']['remove_requires'])
  crew=specs['plugin.video.thecrew'];self.assertFalse(crew['remove_services']);self.assertEqual(crew['required_services'],['service.py'])
  self.assertTrue(all(s.get('remove_services') for s in lock['packages'] if s['id'] in lock['roots'] and s['id'].startswith('plugin.video.') and s['id']!='plugin.video.thecrew'))

class SportsLock(unittest.TestCase):
    def test_the_loop_family_is_fetched_live_by_kodi_not_unzipped_in_place(self):
        # ISSUE-357 follow-up (owner, 2026-11-16): unzipping The Loop's files gave it no repository origin and it failed on the phone
        # ("Invalid params"). Only a tiny pointer add-on (its real repository) is bundled; Kodi's own installer fetches The Loop,
        # LoopTV, Loop Guide and JetExtractors from it live, the same way a real install would, which the desktop rig showed working.
        lock = json.loads(providers.LOCK.read_text())
        ids = {s['id'] for s in lock['packages']}
        self.assertEqual(lock['sports_roots'], ['repository.loop'])
        self.assertIn('repository.loop', ids)
        for id in ('plugin.video.the-loop', 'plugin.video.loopguide', 'plugin.video.looptv', 'script.module.jetextractors'):
            self.assertNotIn(id, ids)
        spec = next(s for s in lock['packages'] if s['id'] == 'repository.loop')
        self.assertTrue(spec['url'].startswith('https://loopaddon.uk/'))
        self.assertRegex(spec['sha256'], r'^[0-9a-f]{64}$')

    def test_the_host_that_answers_only_kodi_is_still_fetched_as_kodi(self):
        seen = []

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'x'
        import urllib.request
        real = urllib.request.urlopen
        urllib.request.urlopen = lambda request, timeout=0: seen.append(request.get_header('User-agent')) or Reply()
        try:
            providers.fetch('https://loopaddon.uk/zips19/x.zip')
            providers.fetch('https://mirrors.kodi.tv/x.zip')
        finally:
            urllib.request.urlopen = real
        self.assertEqual(seen[0], providers.KODI_CLIENT)
        self.assertEqual(seen[1], 'Kodi-iOS-provider-build')

    def test_a_failing_download_is_tried_again_and_then_reported(self):
        import urllib.request
        real, sleep = urllib.request.urlopen, providers.time.sleep
        calls = []

        def fail(request, timeout=0):
            calls.append(1)
            raise OSError('network')
        urllib.request.urlopen = fail
        providers.time.sleep = lambda s: None
        try:
            with self.assertRaises(OSError):
                providers.fetch('https://mirrors.kodi.tv/x.zip')
        finally:
            urllib.request.urlopen = real
            providers.time.sleep = sleep
        self.assertEqual(len(calls), 4)


class BuildIntegration(unittest.TestCase):
 def test_preparer_bundles_provider_and_lists_it_as_optional_in_dependency_order(self):
  from build_customized_ipa import prepare,BOOT
  from test_import_profile import make_bundle
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);app=root/'source/Kodi.app';base=app/'AppData/AppHome';(base/'system').mkdir(parents=True);(base/'addons').mkdir();(base/'system/addon-manifest.xml').write_text('<addons><addon>xbmc.python</addon></addons>')
   bundle=root/'bundle.zip';sha=make_bundle(bundle);inputs=root/'providers';inputs.mkdir()
   body=archive('plugin.fallback',requires='<import addon="xbmc.python" version="3.0.1"/>');spec=dict(id='plugin.fallback',version='1.0.0',url='https://example.invalid/f.zip',sha256=providers.digest(body))
   lock=dict(packages=[spec],provider_packages=[],core_dependencies=['xbmc.python']);(inputs/'plugin.fallback.zip').write_bytes(body);(inputs/'source-lock.json').write_text(json.dumps(lock));lock_path=root/'reviewed-lock.json';lock_path.write_text(json.dumps(lock))
   with patch.object(providers,'LOCK',lock_path):staged,report=prepare(app,bundle,sha,root/'work',providers=inputs)
   self.assertIn('plugin.fallback',report['addon_ids']);self.assertEqual(report['provider_fallback']['addons'],['plugin.fallback'])
   system=ET.parse(staged/report['system_manifest']).getroot();self.assertEqual(system.find("addon[.='plugin.fallback']").get('optional'),'true')
   seed=json.loads((staged/'AppData/AppHome/addons'/BOOT/'seed/seed-manifest.json').read_text());self.assertIn('plugin.fallback',seed['addons'])
   self.assertFalse((base/'addons/plugin.fallback').exists())

@unittest.skipUnless(os.environ.get('KODI_PROVIDER_INPUTS'),'actual verified provider inputs not supplied')
class ActualPinnedInputs(unittest.TestCase):
 def test_all_reviewed_archives_stage_through_real_preparer_without_an_ipa(self):
  from build_customized_ipa import prepare,BOOT
  from test_import_profile import make_bundle
  lock=json.loads(providers.LOCK.read_text());inputs=Path(os.environ['KODI_PROVIDER_INPUTS'])
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);app=root/'foundation/Kodi.app';base=app/'AppData/AppHome';(base/'system').mkdir(parents=True);(base/'addons').mkdir();(base/'system/addon-manifest.xml').write_text('<addons><addon>xbmc.python</addon><addon>xbmc.addon</addon></addons>')
   bundle=root/'bundle.zip';sha=make_bundle(bundle);staged,report=prepare(app,bundle,sha,root/'work',providers=inputs);addonroot=staged/'AppData/AppHome/addons';order=report['addon_ids']
   self.assertTrue(set(lock['roots'])<=set(order));self.assertEqual(len(report['provider_fallback']['addons']),len(lock['packages']))
   for spec in lock['packages']:
    xml=ET.parse(addonroot/spec['id']/'addon.xml').getroot();self.assertEqual(xml.get('version'),spec['version'])
    if spec.get('remove_services'):self.assertIsNone(xml.find("extension[@point='xbmc.service']"))
    for dependency in xml.findall('requires/import'):
     id=dependency.get('addon')
     if dependency.get('optional')=='true' or id in lock['core_dependencies']:continue
     self.assertIn(id,order);self.assertLess(order.index(id),order.index(spec['id']))
   for asset in lock.get('data_assets',[]):self.assertEqual(providers.digest((addonroot/BOOT/asset['destination']).read_bytes()),asset['sha256'])
   for license in lock.get('license_texts',[]):self.assertEqual(providers.digest((addonroot/BOOT/'provider-fallback'/license['path']).read_bytes()),license['sha256'])

if __name__=='__main__':unittest.main()
