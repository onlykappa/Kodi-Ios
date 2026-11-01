import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'migration/import-overlays/script.kodi.ios.first_run/resources/lib/activation.py'
spec=importlib.util.spec_from_file_location('activation',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ActivationTests(unittest.TestCase):
 def api(self,fail=None,missing=None,already=False):
  self.calls=[]
  def call(method,params):
   id=params['addonid'];self.calls.append((method,id,params.get('enabled')))
   if method.endswith('GetAddonDetails'):return {'error':'missing'} if id==missing else {'result':{'addon':{'enabled':already,'version':'1.0'}}}
   return {'error':'fixture'} if id==fail and params['enabled'] else {'result':'OK'}
  return call
 def test_dependency_enabled_first(self):
  r=m.activate(self.api(),{'root':{'requires':['dep']},'dep':{'requires':[]}});self.assertEqual(r['newly_enabled'],['dep','root'])
 def test_missing_addon_has_zero_enable_side_effects(self):
  r=m.activate(self.api(missing='root'),{'root':{'requires':[]}});self.assertEqual(r['status'],'BLOCKED');self.assertFalse(any(x[0].endswith('SetAddonEnabled') for x in self.calls))
 def test_partial_enable_failure_requests_rollback(self):
  r=m.activate(self.api(fail='root'),{'root':{'requires':['dep']},'dep':{'requires':[]}});self.assertEqual(r['status'],'FAILED');self.assertEqual(self.calls[-1],('Addons.SetAddonEnabled','dep',False))
 def test_existing_enable_state_not_overwritten(self):
  r=m.activate(self.api(already=True),{'root':{'requires':[]}});self.assertEqual(r['newly_enabled'],[])
 def test_cycle_rejected(self):
  with self.assertRaises(ValueError):m.order_addons({'a':{'requires':['b']},'b':{'requires':['a']}})
 def test_non_ios_entrypoint_has_no_activation_side_effects(self):
  import sys,types
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('first_run_entry',ROOT/'migration/import-overlays/script.kodi.ios.first_run/default.py');entry=importlib.util.module_from_spec(spec)
  fake=types.SimpleNamespace(getCondVisibility=lambda key:False)
  class Dialog:
   def ok(self,*args):pass
  with patch.dict(sys.modules,{'xbmc':fake,'xbmcgui':types.SimpleNamespace(Dialog=Dialog),'xbmcvfs':types.SimpleNamespace()}):
   spec.loader.exec_module(entry)
   with patch.object(entry,'activate',side_effect=AssertionError('non-iOS write')):entry.run()
if __name__=='__main__':unittest.main()
