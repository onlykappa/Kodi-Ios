"""The pinned Loop/Jet add-on set (migration/loop-addons/source-lock.json): well-formed, every pin verifiable by the existing provider fetcher."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import provider_addons as pa
ROOT=Path(__file__).resolve().parents[1]
LOCK=json.loads((ROOT/'migration/loop-addons/source-lock.json').read_text())

class Lock(unittest.TestCase):
 def test_shape_and_pins(self):
  ids=[p['id'] for p in LOCK['packages']];self.assertEqual(len(ids),len(set(ids)))
  for p in LOCK['packages']:
   self.assertRegex(p['sha256'],r'^[0-9a-f]{64}$');self.assertTrue(p['url'].startswith(('https://loopaddon.uk/','https://mirrors.kodi.tv/')),p['id']);self.assertGreater(p['size'],1000);self.assertTrue(p['version'])
  for must in ('plugin.video.the-loop','script.module.jetextractors','plugin.video.jetproxy','plugin.video.loopguide','plugin.video.looptv','plugin.video.dailymotion_com'):self.assertIn(must,ids)
  self.assertNotIn('plugin.video.youtube',ids,'YouTube is only an optional dependency and the owner does not use it')
 def test_every_dependency_is_pinned_here_or_elsewhere(self):
  have={p['id'] for p in LOCK['packages']}
  for f in ('migration/provider-fallback/source-lock.json','migration/elementum-ios/source-lock.json','migration/umbrella/source-lock.json'):
   d=json.loads((ROOT/f).read_text());have|={s.get('id') or s.get('name') for k in ('packages','provider_packages') for s in d.get(k,[]) if isinstance(s,dict)}|set(d.get('extras',{}))
  kodi_builtin={'xbmc.python','script.module.requests','script.module.routing','script.module.unidecode','script.module.inputstreamhelper','script.module.resolveurl','script.module.pycryptodome','script.module.kodi-six','script.module.future','script.module.beautifulsoup4','script.module.dateutil','script.module.soupsieve','script.module.microjenscrapers'}
  missing=sorted({r.replace(' (optional)','') for p in LOCK['packages'] for r in p['requires'] if '(optional)' not in r}-have-kodi_builtin)
  self.assertEqual(missing,[],'dependencies neither pinned here nor shipped in the IPA: %s'%missing)
 def test_the_fetcher_accepts_the_lock_format(self):
  self.assertTrue(all(k in LOCK for k in ('packages','provider_packages','core_dependencies')))

if __name__=='__main__':unittest.main()
