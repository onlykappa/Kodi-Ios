import json,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
from build_customized_ipa import prepare,patch_drive,DRIVE_PATCHES,DRIVE_COMMON,BOOT,ELEMENTUM,BURST,ELEMENTUM_PATCHES,ELEMENTUM_IOS,BURST_PATCHES
from test_import_profile import make_bundle
class EngineGuardTests(unittest.TestCase):
 """The patched Elementum start (ELEMENTUM_IOS) run with stand-ins for Kodi."""
 def env(self,tmp):
  import os,types
  notes=[]
  ns={'os':os,'time':__import__('time'),'threading':__import__('threading'),'binary_platform':{},
      'translatePath':lambda p:str(tmp/'Kodi.app/AppData/AppHome')+'/','get_addon_profile_dir':lambda:str(tmp/'profile'),
      'ADDON':types.SimpleNamespace(getSetting=lambda k:'',setSetting=lambda k,v:None),
      'log':types.SimpleNamespace(error=notes.append,info=notes.append),
      'xbmc':types.SimpleNamespace(executebuiltin=notes.append)}
  exec(ELEMENTUM_IOS.decode(),ns)
  (tmp/'Kodi.app/Frameworks/elementum.framework').mkdir(parents=True);(tmp/'Kodi.app/Frameworks/elementum.framework/elementum').write_bytes(b'x')
  (tmp/'profile').mkdir()
  return ns,notes
 def test_a_skipped_engine_starts_again_next_time(self):
  # Owner log: after two starts that never reached the engine, Elementum stayed off at every later start.
  with tempfile.TemporaryDirectory() as t:
   tmp=Path(t);ns,notes=self.env(tmp);marker=tmp/'profile/engine-starting'
   marker.write_text('2')
   self.assertEqual(ns['ios_engine'](),(False,False))
   self.assertFalse(marker.exists())
   self.assertTrue(any('not started' in str(n) for n in notes))
   framework,binary=ns['ios_engine']()
   self.assertTrue(str(binary).endswith('elementum.framework/elementum'))
 def test_elementum_folders_follow_a_reinstalled_app(self):
  # (Moved from the bootstrap service, which did this a second time at every start.)
  with tempfile.TemporaryDirectory() as t:
   tmp=Path(t);ns,_=self.env(tmp)
   old='/private/var/mobile/Containers/Data/Application/3C035651-951A-4CE8-826D-3F157EF3E5AC/Documents/'
   new='/private/var/mobile/Containers/Data/Application/59AA78BE-C5DC-4512-9C33-1D2B3C4D5E6F/Documents/'
   settings={'download_path':old+'Elementum Downloads/','completed_movies_path':old+'Kodi Downloads/Movies/','torrents_path':'/somewhere/else/'}
   made=[]
   ns['ADDON'].getSetting=lambda k:settings.get(k,'');ns['ADDON'].setSetting=settings.__setitem__
   ns['translatePath']=lambda p:new+'Kodi/'
   ns['os'].makedirs,real=(lambda path,exist_ok=False:made.append(path)),ns['os'].makedirs
   try:ns['ios_follow_container']()
   finally:ns['os'].makedirs=real
   self.assertEqual(settings['download_path'],new+'Elementum Downloads/')
   self.assertEqual(settings['completed_movies_path'],new+'Kodi Downloads/Movies/')
   self.assertEqual(settings['torrents_path'],'/somewhere/else/')
 def test_one_failed_start_is_retried(self):
  with tempfile.TemporaryDirectory() as t:
   tmp=Path(t);ns,_=self.env(tmp);(tmp/'profile/engine-starting').write_text('1')
   self.assertTrue(str(ns['ios_engine']()[1]).endswith('elementum'))

class BundleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.app=self.root/'original/Kodi.app';base=self.app/'AppData/AppHome';(base/'system').mkdir(parents=True);(base/'addons').mkdir();(base/'system/addon-manifest.xml').write_text('<addons><addon>xbmc.python</addon></addons>');self.bundle=self.root/'bundle.zip';self.sha=make_bundle(self.bundle)
 def tearDown(self):self.tmp.cleanup()
 def test_airplay_local_network_purpose_is_in_the_staged_app_only(self):
  import plistlib
  original={'CFBundleIdentifier':'org.fixture.kodi','NSBonjourServices':['_fixture._tcp'],'UIBackgroundModes':['fetch']}
  (self.app/'Info.plist').write_bytes(plistlib.dumps(original))
  app,_=prepare(self.app,self.bundle,self.sha,self.root/'work')
  info=plistlib.loads((app/'Info.plist').read_bytes())
  self.assertEqual(info['NSLocalNetworkUsageDescription'],'Kodi streams the video from this iPhone to your TV over Wi-Fi.')
  self.assertEqual(info['CFBundleIdentifier'],original['CFBundleIdentifier'])
  self.assertEqual(info['NSBonjourServices'],original['NSBonjourServices'])
  self.assertEqual(info['UIBackgroundModes'],['fetch','audio'])
  self.assertEqual(plistlib.loads((self.app/'Info.plist').read_bytes()),original)
 def test_drive_requests_get_timeout_and_certifi_context(self):
  base=self.root/'addons'/DRIVE_COMMON
  for name,before,_ in DRIVE_PATCHES:
   path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((path.read_bytes() if path.exists() else b'x\n')+before)
  receipt=patch_drive(self.root/'addons');self.assertEqual(len(receipt),len({n for n,_,_ in DRIVE_PATCHES}))
  for name,_,after in DRIVE_PATCHES:self.assertIn(after,(base/name).read_bytes())
  with self.assertRaises(AssertionError):patch_drive(self.root/'addons')
 def test_drive_extra_services_off_unless_setting_true(self):
  old,new=next((o,n) for name,o,n in DRIVE_PATCHES if name.endswith('service/utils.py'))
  source=(b"class KodiUtils:\n    setting=''\n    @staticmethod\n    def get_addon_setting(key):\n        return KodiUtils.setting\n"
          b"class ServiceUtil(object):\n    @staticmethod\n    def run(services):\n"+old+b"        return [s.name for s in services]\n")
  patched=source.replace(old,new)
  self.assertNotEqual(patched,source)
  def names(setting,wanted):
   ns=self.exec_ns(patched);ns['KodiUtils'].setting=setting
   return ns['ServiceUtil'].run([type('S',(),{'name':n})() for n in wanted])
  all4=['download','source','export','player']
  self.assertEqual(names('',all4),['download'])
  self.assertEqual(names('false',all4),['download'])
  self.assertEqual(names('true',all4),all4)
  self.assertIsNone(names('',['source']))   # nothing left to run: the service returns instead of waking every second
 @staticmethod
 def exec_ns(code):
  ns={};exec(code.decode(),ns);return ns
 def test_packaged_sources_manifest_seed_and_original_preserved(self):
  app,receipt=prepare(self.app,self.bundle,self.sha,self.root/'work');base=app/'AppData/AppHome';xml=ET.parse(base/'system/addon-manifest.xml').getroot()
  self.assertEqual(xml.find("addon[.='fixture.addon']").get('optional'),'true');self.assertIsNone(xml.find("addon[.='"+BOOT+"']").get('optional'))
  self.assertTrue((base/'addons'/BOOT/'service.py').is_file());self.assertTrue((base/'addons'/BOOT/'recover.py').is_file());self.assertTrue((base/'addons/fixture.addon/resources/settings.xml').is_file())
  seed=json.loads((base/'addons'/BOOT/'seed/seed-manifest.json').read_text());self.assertEqual(seed['addons'],['fixture.addon']);self.assertEqual(len(seed['files']),3)
  self.assertFalse((self.app/'AppData/AppHome/addons/fixture.addon').exists());self.assertEqual(len(ET.parse(self.app/'AppData/AppHome/system/addon-manifest.xml').getroot()),1)
  # Kodi's splash off for every install: special://xbmc/system/advancedsettings.xml, read before the profile's file.
  self.assertEqual(ET.parse(base/'system/advancedsettings.xml').getroot().findtext('splash'),'false')
  self.assertEqual(receipt['splash']['path'],'advancedsettings.xml');self.assertFalse((self.app/'AppData/AppHome/system/advancedsettings.xml').exists())
 def elementum_inputs(self):
  inputs=self.root/'elementum';inputs.mkdir();files={}
  for name,old,_ in ELEMENTUM_PATCHES:files[name]=files.get(name,b'')+b'# x\n'+old+b'\n'
  with zipfile.ZipFile(inputs/'client.zip','w') as z:
   z.writestr(ELEMENTUM+'/addon.xml','<addon id="plugin.video.elementum" version="0.1.114"><requires><import addon="script.module.kodi-six"/><import addon="repository.elementumorg" optional="true"/></requires></addon>')
   z.writestr(ELEMENTUM+'/resources/site-packages/platform_detect/libraries/linux_x64/test.so','elf')
   for name,data in files.items():z.writestr(ELEMENTUM+'/'+name,data)
  with zipfile.ZipFile(inputs/'framework.zip','w') as z:z.writestr('elementum.framework/elementum',b'\xcf\xfa\xed\xfe'+b'\0'*60);z.writestr('elementum.framework/Info.plist','<plist/>')
  (inputs/'frameworks').mkdir()
  with zipfile.ZipFile(inputs/'frameworks/KodiAirPlay.framework.zip','w') as z:z.writestr('KodiAirPlay.framework/KodiAirPlay',b'\xcf\xfa\xed\xfe'+b'\0'*60);z.writestr('KodiAirPlay.framework/Info.plist','<plist/>')
  for id in ['script.module.kodi-six','script.module.future']:
   d=inputs/'modules'/id;d.mkdir(parents=True);(d/'addon.xml').write_text('<addon id="'+id+'" version="1"><requires><import addon="xbmc.python"/></requires></addon>')
  with zipfile.ZipFile(inputs/'burst.zip','w') as z:
   z.writestr(BURST+'/addon.xml','<addon id="'+BURST+'" version="0.0.99"><requires><import addon="plugin.video.elementum" optional="true"/><import addon="script.module.kodi-six"/><import addon="script.module.future"/></requires></addon>')
   z.writestr(BURST+'/burst/providers/providers.json','{}')
   z.writestr(BURST+'/burst/burst.py',b''.join(b'# x\n'+old for _,old,_ in BURST_PATCHES))
  for mode,id in [('app','script.module.resolveurl'),('profile','script.module.cocoscrapers')]:
   (inputs/('extras-'+mode)).mkdir()
   with zipfile.ZipFile(inputs/('extras-'+mode)/(id+'.zip'),'w') as z:z.writestr(id+'/addon.xml','<addon id="'+id+'" version="1"><requires><import addon="xbmc.python"/></requires></addon>');z.writestr(id+'/lib/m.py','x=1')
  return inputs
 def test_elementum_engine_bundled_in_frameworks_and_patched_for_ios(self):
  app,receipt=prepare(self.app,self.bundle,self.sha,self.root/'work',self.elementum_inputs());base=app/'AppData/AppHome'
  self.assertTrue((app/'Frameworks/elementum.framework/elementum').is_file());self.assertTrue((app/'Frameworks/KodiAirPlay.framework/KodiAirPlay').is_file());self.assertEqual(receipt['elementum']['frameworks'],['Frameworks/KodiAirPlay.framework']);self.assertEqual(len(receipt['elementum']['patches']),5)
  daemon=(base/'addons'/ELEMENTUM/'resources/site-packages/elementum/daemon.py').read_bytes()
  site=base/'addons'/ELEMENTUM/'resources/site-packages/elementum'
  for _,_,after in ELEMENTUM_PATCHES:self.assertIn(after,daemon+(site/'osarch.py').read_bytes()+(site/'service.py').read_bytes()+(site/'rpc.py').read_bytes()+(site/'navigation.py').read_bytes())
  self.assertFalse((base/'addons'/ELEMENTUM/'resources/site-packages/platform_detect/libraries').exists())
  self.assertIn(b'ios_crash_guard()\n',daemon);self.assertIn(b'engine-starting',daemon)
  self.assertIn(b'deck_picker.run(title_encoded, items)',(site/'rpc.py').read_bytes())
  page=(base/'addons'/ELEMENTUM/'resources/skins/Default/720p/DeckSourceSelect.xml').read_text();self.assertEqual(page.count('<right>0</right>'),2)
  self.assertTrue((site/'deck_picker.py').is_file());self.assertTrue((base/'addons'/ELEMENTUM/'resources/skins/Default/media/deck/rounded_s.png').read_bytes().startswith(b'\x89PNG'))
  seed=json.loads((base/'addons'/BOOT/'seed/seed-manifest.json').read_text());order=seed['addons']
  self.assertLess(order.index('script.module.kodi-six'),order.index(ELEMENTUM));self.assertLess(order.index('script.module.future'),order.index(BURST))
  self.assertTrue((base/'addons'/BURST/'burst/providers/providers.json').is_file())
  # Burst checks every provider's results against the title asked for, with the bootstrap add-on's source_match.py.
  burst=(base/'addons'/BURST/'burst/burst.py').read_bytes()
  for _,_,after in BURST_PATCHES:self.assertIn(after,burst)
  self.assertEqual([p['path'] for p in receipt['elementum']['burst_patches']],['addons/'+BURST+'/burst/burst.py'])
  self.assertTrue((base/'addons'/BOOT/'resources/lib/source_match.py').is_file());self.assertTrue((site/'source_match.py').is_file())
  self.assertTrue((base/'addons/script.module.resolveurl/lib/m.py').is_file());self.assertIn('script.module.resolveurl',order)
  self.assertTrue((base/'addons'/BOOT/'payload/script.module.cocoscrapers/lib/m.py').is_file());self.assertNotIn('script.module.cocoscrapers',order)
  self.assertEqual(receipt['profile_addons'],['script.module.cocoscrapers'])
  xml=ET.parse(base/'system/addon-manifest.xml').getroot();self.assertEqual(xml.find("addon[.='"+ELEMENTUM+"']").get('optional'),'true')
 def test_corrupt_input_rejected_before_any_copy(self):
  with self.assertRaises(Exception):prepare(self.app,self.bundle,'bad',self.root/'work')
  self.assertFalse((self.root/'work').exists())
 def test_overlapping_source_and_work_rejected(self):
  with self.assertRaises(AssertionError):prepare(self.app,self.bundle,self.sha,self.app/'nested')
class BytecodeTests(unittest.TestCase):
 def test_bundle_python_precompiled_for_311(self):
  # Owner crash report (build 142): iOS killed Kodi for CPU; Python recompiled read-only bundle sources on every run.
  import build_customized_ipa as b,importlib.util as iu,marshal,sys
  with tempfile.TemporaryDirectory() as tmp:
   app=Path(tmp)/'Kodi.app';std=app/'Frameworks/lib/python3.11';add=app/'AppData/AppHome/addons/plugin.x'
   for d,names in ((std,('os.py','json/decoder.py')),(add,('default.py','resources/lib/a.py'))):
    for n in names:(d/n).parent.mkdir(parents=True,exist_ok=True);(d/n).write_text('VALUE=%r\n'%n)
   (add/'py2.py').write_text('print "python 2"\n')
   info=b.precompile(app)
   self.assertEqual((info['tag'],info['added'],info['sources']),('cpython-311',4,5))
   pyc=std/'__pycache__/os.cpython-311.pyc';data=pyc.read_bytes()
   # PEP 552 flags: bit 0 hash-based, bit 1 check source. 0b01 = never compared with the source.
   self.assertEqual(int.from_bytes(data[4:8],'little'),0b01)
   self.assertFalse((add/'__pycache__/py2.cpython-311.pyc').exists())
   if sys.implementation.cache_tag=='cpython-311':
    self.assertEqual(marshal.loads(data[16:]).co_filename,'Kodi.app/Frameworks/lib/python3.11/os.py')
 def test_build_requires_python311(self):
  import build_customized_ipa as b,os
  from unittest import mock
  with mock.patch.dict(os.environ,{'KODI_IOS_PYTHON311':'/nonexistent/python'}):
   with self.assertRaises(Exception):b.python311()
if __name__=='__main__':unittest.main()
