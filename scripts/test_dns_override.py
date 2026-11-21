"""A host the phone's DNS answers wrongly is connected by DNS over HTTPS's address (owner, build 634 log 89646295: Crew's embedsports host failed TLS on the phone's
addresses and worked on DoH's)."""
import json,os,socket,sys,tempfile,types,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import dns_override as d,sports_crew_patch as cp,host_check as hc

OK='ok TLSv1.3';BAD='tls refused ([SSL] unknown error)'
class Decide(unittest.TestCase):
    def test_the_logged_case_is_an_override(self):   # phone DNS: 4 addresses that refuse TLS; DoH: one that works
        own=['1.1.1.1','1.1.1.2','1.1.1.3','1.1.1.4']
        self.assertEqual(d.decide('taifood-blog.asia',lambda h:own,lambda h:['104.21.9.9'],lambda h,a:OK if a=='104.21.9.9' else BAD),('override','104.21.9.9'))
    def test_working_dns_needs_no_override_and_nothing_resolved_is_none(self):
        self.assertEqual(d.decide('h',lambda h:['1.1.1.1'],lambda h:['2.2.2.2'],lambda h,a:OK),('fine',''))
        self.assertEqual(d.decide('h',lambda h:['1.1.1.1'],lambda h:['1.1.1.1'],lambda h,a:BAD),('none',''))   # DoH says the same address: nothing better to use
        self.assertEqual(d.decide('h',lambda h:['1.1.1.1'],lambda h:['2.2.2.2'],lambda h,a:BAD),('none',''))   # DoH's does not work either
        def boom(h):raise OSError('x')
        self.assertEqual(d.decide('h',boom,boom,lambda h,a:BAD),('none',''))
class Refresh(unittest.TestCase):
    def test_the_table_follows_the_checks(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            f=os.path.join(t,'x','dns-overrides.json');logs=[]
            sysd={'a.example':['1.1.1.1'],'b.example':['3.3.3.3']};dohd={'a.example':['9.9.9.9'],'b.example':['3.3.3.3']}
            tls=lambda h,a:OK if a in ('9.9.9.9','3.3.3.3') else BAD
            now=[1000.0]
            out=d.refresh(f,('a.example','b.example'),lambda h:sysd[h],lambda h:dohd[h],tls,lambda:now[0],logs.append)
            self.assertEqual(out,{'a.example':'9.9.9.9'});self.assertEqual(json.load(open(f)),{'a.example':{'ip':'9.9.9.9','at':1000}})
            self.assertIn('dns override: a.example connects by public address',logs[0]);self.assertNotIn('9.9.9.9',' '.join(logs))   # no address in the log
            sysd['a.example']=['9.9.9.9']                              # the phone's DNS is right again
            out=d.refresh(f,('a.example','b.example'),lambda h:sysd[h],lambda h:dohd[h],tls,lambda:now[0],logs.append)
            self.assertEqual(out,{});self.assertEqual(json.load(open(f)),{});self.assertIn('override removed',logs[-1])
    def test_only_listed_hosts_are_kept(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            f=os.path.join(t,'o.json');d.save(f,{'evil.example':{'ip':'6.6.6.6','at':1}})
            d.refresh(f,('a.example',),lambda h:[],lambda h:[],lambda h,a:BAD);self.assertEqual(d.load(f),{})
class Wrapper(unittest.TestCase):
    """The code appended to Crew's control module, run for real with a throwaway table."""
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.addCleanup(__import__('shutil').rmtree,self.dir,True)
        self.real=socket.getaddrinfo;self.addCleanup(setattr,socket,'getaddrinfo',self.real)
        self.fake=types.ModuleType('xbmcvfs');self.fake.translatePath=lambda p:self.dir
        old=sys.modules.get('xbmcvfs');sys.modules['xbmcvfs']=self.fake
        self.addCleanup(lambda:sys.modules.__setitem__('xbmcvfs',old) if old else sys.modules.pop('xbmcvfs',None))
    def wrap(self,table):
        Path(self.dir,'dns-overrides.json').write_text(json.dumps(table))
        exec(compile(cp.DNS_ADDED,'control_dns','exec'),{});return socket.getaddrinfo
    def test_an_override_answers_for_its_host_only(self):
        import time
        wrapped=self.wrap({'taifood-blog.asia':{'ip':'104.21.9.9','at':int(time.time())},'old.example':{'ip':'8.8.8.8','at':1}})
        self.assertIsNot(wrapped,self.real)
        self.assertEqual(wrapped('Taifood-Blog.asia',443,0,socket.SOCK_STREAM)[0][4],('104.21.9.9',443))        # the host's own name, the working address
        self.assertEqual(wrapped('taifood-blog.asia','443',socket.AF_INET,socket.SOCK_STREAM)[0][4],('104.21.9.9',443))
        self.assertTrue(any(i[4][0]=='127.0.0.1' for i in wrapped('localhost',80,socket.AF_INET)))               # another name: the normal lookup
        with self.assertRaises(socket.gaierror):wrapped('no-such-host.invalid',80)                              # real failures still fail
        with self.assertRaises(socket.gaierror):wrapped('old.example',443)                                      # an entry over 12 h old is ignored (the real lookup fails here)
    def test_an_ipv6_answer_is_a_v6_address_and_only_for_v6_or_any_family(self):
        import time
        wrapped=self.wrap({'v6.example':{'ip':'2606:4700::1','at':int(time.time())}})
        r=wrapped('v6.example',443,0,socket.SOCK_STREAM)[0];self.assertEqual((r[0],r[4][0],r[4][1]),(socket.AF_INET6,'2606:4700::1',443))
        with self.assertRaises(socket.gaierror):wrapped('v6.example',443,socket.AF_INET,socket.SOCK_STREAM)      # asked for v4 only: not answered with a v6 address
    def test_a_missing_or_broken_table_changes_nothing_and_a_second_run_does_not_stack(self):
        wrapped=self.wrap({});Path(self.dir,'dns-overrides.json').write_text('{not json')
        self.assertTrue(any(i[4][0]=='127.0.0.1' for i in wrapped('localhost',80,socket.AF_INET)))
        again=self.wrap({});self.assertIs(again,wrapped)                                                         # already wrapped: left as it is
class Patch(unittest.TestCase):
    def test_the_patch_is_added_once_to_the_pinned_version_only(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            mod=Path(t)/'script.module.thecrew';rel=mod/cp.RELATIVE;rel.parent.mkdir(parents=True);rel.write_text('import xbmc\n'+cp.ORIGINAL)
            (mod/'addon.xml').write_text('<addon id="x" version="9.9.9"/>')
            self.assertEqual(cp.apply_dns([str(mod)]),'Crew module is not the pinned version')
            (mod/'addon.xml').write_text('<addon id="x" version="%s"/>'%cp.VERSION)
            self.assertEqual(cp.apply_dns([str(mod)]),'patched');self.assertEqual(cp.apply_dns([str(mod)]),'already')
            text=rel.read_text();self.assertEqual(text.count(cp.DNS_MARK),1);compile(text,'control','exec')
    def test_the_service_patches_crew_early_and_runs_the_checker(self):
        svc=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('dns_override.watch(file,monitor.waitForAbort,log)',svc);self.assertIn('sports_crew_patch.ensure(',svc)
        self.assertEqual(hc.HOSTS,d.HOSTS)
if __name__=='__main__':unittest.main()
