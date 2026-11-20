"""The Loop's background work stays off while the setting is on, and only an add-on this app switched off is switched back on."""
import os,sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import loop_quiet as lq

class Quiet(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.state=os.path.join(self.tmp.name,'s.json')
        self.enabled=True;self.installed=True;self.calls=[];self.logs=[]
    def rpc(self,method,params):
        self.calls.append((method,params.get('enabled')))
        if method=='Addons.GetAddonDetails':return {'addon':{'enabled':self.enabled}} if self.installed else {}
        if method=='Addons.SetAddonEnabled':self.enabled=params['enabled'];return {}
    def run_(self,wanted):return lq.apply(wanted,self.rpc,self.state,self.logs.append)
    def test_on_switches_the_loop_off_once(self):
        self.assertEqual(self.run_(True),'disabled');self.assertFalse(self.enabled)
        self.assertEqual(self.run_(True),'');self.assertEqual([c for c in self.calls if c[0]=='Addons.SetAddonEnabled'],[('Addons.SetAddonEnabled',False)])
    def test_off_switches_it_back_only_if_this_app_switched_it_off(self):
        self.run_(True);self.assertEqual(self.run_(False),'enabled');self.assertTrue(self.enabled)
    def test_an_add_on_the_owner_disabled_is_left_alone(self):
        self.enabled=False;self.assertEqual(self.run_(False),'');self.assertFalse(self.enabled)
        self.assertEqual(self.run_(True),'');self.assertFalse(self.enabled)   # already off: nothing to do and nothing recorded
        self.assertEqual(self.run_(False),'');self.assertFalse(self.enabled)
    def test_not_installed_or_rpc_failing_is_quiet(self):
        self.installed=False;self.assertEqual(self.run_(True),'')
        def boom(method,params):raise RuntimeError('x')
        self.assertEqual(lq.apply(True,boom,self.state),'')
if __name__=='__main__':unittest.main()
