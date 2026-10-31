import json,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
from build_customized_ipa import prepare,patch_drive,DRIVE_PATCHES,DRIVE_COMMON,BOOT,ELEMENTUM,BURST,ELEMENTUM_PATCHES
from test_import_profile import make_bundle
class BundleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.app=self.root/'original/Kodi.app';base=self.app/'AppData/AppHome';(base/'system').mkdir(parents=True);(base/'addons').mkdir();(base/'system/addon-manifest.xml').write_text('<addons><addon>xbmc.python</addon></addons>');self.bundle=self.root/'bundle.zip';self.sha=make_bundle(self.bundle)
 def tearDown(self):self.tmp.cleanup()
 def test_drive_requests_get_timeout_and_certifi_context(self):
  base=self.root/'addons'/DRIVE_COMMON
  for name,before,_ in DRIVE_PATCHES:
   path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((path.read_bytes() if path.exists() else b'x\n')+before)
  receipt=patch_drive(self.root/'addons');self.assertEqual(len(receipt),len({n for n,_,_ in DRIVE_PATCHES}))
  for name,_,after in DRIVE_PATCHES:self.assertIn(after,(base/name).read_bytes())
  with self.assertRaises(AssertionError):patch_drive(self.root/'addons')
 def test_packaged_sources_manifest_seed_and_original_preserved(self):
  app,receipt=prepare(self.app,self.bundle,self.sha,self.root/'work');base=app/'AppData/AppHome';xml=ET.parse(base/'system/addon-manifest.xml').getroot()
  self.assertEqual(xml.find("addon[.='fixture.addon']").get('optional'),'true');self.assertIsNone(xml.find("addon[.='"+BOOT+"']").get('optional'))
  self.assertTrue((base/'addons'/BOOT/'service.py').is_file());self.assertTrue((base/'addons'/BOOT/'recover.py').is_file());self.assertTrue((base/'addons/fixture.addon/resources/settings.xml').is_file())
  seed=json.loads((base/'addons'/BOOT/'seed/seed-manifest.json').read_text());self.assertEqual(seed['addons'],['fixture.addon']);self.assertEqual(len(seed['files']),3)
  self.assertFalse((self.app/'AppData/AppHome/addons/fixture.addon').exists());self.assertEqual(len(ET.parse(self.app/'AppData/AppHome/system/addon-manifest.xml').getroot()),1)
 def elementum_inputs(self):
  inputs=self.root/'elementum';inputs.mkdir();files={}
  for name,old,_ in ELEMENTUM_PATCHES:files[name]=files.get(name,b'')+b'# x\n'+old+b'\n'
  with zipfile.ZipFile(inputs/'client.zip','w') as z:
   z.writestr(ELEMENTUM+'/addon.xml','<addon id="plugin.video.elementum" version="0.1.114"><requires><import addon="script.module.kodi-six"/><import addon="repository.elementumorg" optional="true"/></requires></addon>')
   z.writestr(ELEMENTUM+'/resources/site-packages/platform_detect/libraries/linux_x64/test.so','elf')
   for name,data in files.items():z.writestr(ELEMENTUM+'/'+name,data)
  with zipfile.ZipFile(inputs/'framework.zip','w') as z:z.writestr('elementum.framework/elementum',b'\xcf\xfa\xed\xfe'+b'\0'*60);z.writestr('elementum.framework/Info.plist','<plist/>')
  for id in ['script.module.kodi-six','script.module.future']:
   d=inputs/'modules'/id;d.mkdir(parents=True);(d/'addon.xml').write_text('<addon id="'+id+'" version="1"><requires><import addon="xbmc.python"/></requires></addon>')
  with zipfile.ZipFile(inputs/'burst.zip','w') as z:
   z.writestr(BURST+'/addon.xml','<addon id="'+BURST+'" version="0.0.99"><requires><import addon="plugin.video.elementum" optional="true"/><import addon="script.module.kodi-six"/><import addon="script.module.future"/></requires></addon>')
   z.writestr(BURST+'/burst/providers/providers.json','{}')
  return inputs
 def test_elementum_engine_bundled_in_frameworks_and_patched_for_ios(self):
  app,receipt=prepare(self.app,self.bundle,self.sha,self.root/'work',self.elementum_inputs());base=app/'AppData/AppHome'
  self.assertTrue((app/'Frameworks/elementum.framework/elementum').is_file());self.assertEqual(len(receipt['elementum']['patches']),2)
  daemon=(base/'addons'/ELEMENTUM/'resources/site-packages/elementum/daemon.py').read_bytes()
  for _,_,after in ELEMENTUM_PATCHES:self.assertIn(after,daemon+(base/'addons'/ELEMENTUM/'resources/site-packages/elementum/osarch.py').read_bytes())
  self.assertFalse((base/'addons'/ELEMENTUM/'resources/site-packages/platform_detect/libraries').exists())
  seed=json.loads((base/'addons'/BOOT/'seed/seed-manifest.json').read_text());order=seed['addons']
  self.assertLess(order.index('script.module.kodi-six'),order.index(ELEMENTUM));self.assertLess(order.index('script.module.future'),order.index(BURST))
  self.assertTrue((base/'addons'/BURST/'burst/providers/providers.json').is_file())
  xml=ET.parse(base/'system/addon-manifest.xml').getroot();self.assertEqual(xml.find("addon[.='"+ELEMENTUM+"']").get('optional'),'true')
 def test_corrupt_input_rejected_before_any_copy(self):
  with self.assertRaises(Exception):prepare(self.app,self.bundle,'bad',self.root/'work')
  self.assertFalse((self.root/'work').exists())
 def test_overlapping_source_and_work_rejected(self):
  with self.assertRaises(AssertionError):prepare(self.app,self.bundle,self.sha,self.app/'nested')
if __name__=='__main__':unittest.main()
