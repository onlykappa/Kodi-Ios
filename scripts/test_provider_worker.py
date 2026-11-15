"""Isolated worker deadlines, cancellation, private replies and account read-through contracts."""
import http.server,json,os,shutil,sys,tempfile,threading,time,unittest,urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import provider_fallback as fallback
import provider_fallback_worker as worker
# CI executes the same pinned requests engine shipped in the app, even on a bare Python runner.
_provider_temp = None
if os.environ.get('KODI_PROVIDER_INPUTS'):
    import hashlib,zipfile
    lock=json.loads((ROOT/'migration/provider-fallback/source-lock.json').read_text())
    _provider_temp=tempfile.TemporaryDirectory()
    for spec in lock['packages']:
        if spec['id'] not in ('script.module.requests','script.module.urllib3','script.module.certifi','script.module.idna','script.module.chardet','script.module.charset_normalizer'):continue
        data=(Path(os.environ['KODI_PROVIDER_INPUTS'])/(spec['id']+'.zip')).read_bytes()
        if hashlib.sha256(data).hexdigest()!=spec['sha256']:raise AssertionError('HTTP worker fixture checksum differs')
        with zipfile.ZipFile(__import__('io').BytesIO(data)) as archive:
            for name in archive.namelist():
                if '..' in Path(name).parts or Path(name).is_absolute():raise AssertionError('Unsafe HTTP worker fixture')
            archive.extractall(_provider_temp.name)
        sys.path.insert(0,str(Path(_provider_temp.name)/spec['id']/'lib'))
try:import requests;HAS_REQUESTS=True
except ImportError:HAS_REQUESTS=False
if os.environ.get('KODI_REQUIRE_PROVIDER_FIXTURES')=='1' and not HAS_REQUESTS:
    raise RuntimeError('Pinned requests worker fixtures are required')


class SlowBody(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Length','50');self.end_headers()
        try:
            for _ in range(50):self.wfile.write(b'x');self.wfile.flush();time.sleep(.03)
        except OSError:pass


class Worker(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.folder=self.root/'job';self.folder.mkdir(mode=0o700)
        (self.root/'addon.xml').write_text('<addon id="fixture"><requires><import addon="xbmc.python" version="3.0.0"/></requires></addon>')
        self.native=SimpleNamespace(getAddonInfo=lambda key:str(self.root),getSetting=lambda key:'')
        self.xbmc=SimpleNamespace(log=mock.Mock(),executebuiltin=mock.Mock())
        self.gui=SimpleNamespace(Dialog=object,DialogProgress=object,DialogProgressBG=object)
        self.addon=SimpleNamespace(Addon=lambda *args,**kwargs:self.native)
    def tearDown(self):self.tmp.cleanup()
    def context(self,seconds=.18):return worker.Context('jacktook',self.folder,time.monotonic()+seconds,self.native,self.root)
    def server(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),SlowBody);server.daemon_threads=True
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:%d/body'%server.server_port
    @unittest.skipUnless(HAS_REQUESTS,'requests networking is also exercised in the real Kodi rig')
    def test_requests_drip_fed_body_cannot_outlive_the_absolute_worker_deadline(self):
        url=self.server();context=self.context();began=time.monotonic()
        with self.assertRaises(Exception):
            with worker.guarded(context,self.xbmc,self.gui,self.addon):context.session.get(url,timeout=1).content
        self.assertLess(time.monotonic()-began,.7)
    def test_urllib_drip_fed_body_cannot_outlive_the_absolute_worker_deadline(self):
        url=self.server();context=self.context();began=time.monotonic()
        with self.assertRaises(Exception):
            with worker.guarded(context,self.xbmc,self.gui,self.addon):
                with urllib.request.urlopen(url,timeout=1) as response:response.read()
        self.assertLess(time.monotonic()-began,.7)
    @unittest.skipUnless(HAS_REQUESTS,'requests networking is also exercised in the real Kodi rig')
    def test_removing_parent_mailbox_interrupts_an_active_requests_body(self):
        url=self.server();context=self.context(5);timer=threading.Timer(.15,lambda:shutil.rmtree(self.folder));timer.start();self.addCleanup(timer.cancel)
        began=time.monotonic()
        with self.assertRaises(Exception):
            with worker.guarded(context,self.xbmc,self.gui,self.addon):context.session.get(url,timeout=4).content
        self.assertLess(time.monotonic()-began,.7);self.assertFalse(self.folder.exists())
    def request(self):
        fallback.write_private(self.folder/'request.json',{'provider':'jacktook','operation':'search',
            'request':{'title':'Fixture Movie','media_type':'movie','year':2020},'deadline':time.monotonic()+3})
    def test_worker_reply_is_private_and_provider_logs_are_suppressed(self):
        self.request();adapter=SimpleNamespace(search=lambda request,context:self.xbmc.log('provider-private-payload') or [{'name':'Fixture.Movie.2020.1080p.mkv'}])
        original=worker.importlib.import_module
        with mock.patch.object(worker.importlib,'import_module',side_effect=lambda name,*a,**k:adapter if name.startswith('provider_adapters.') else original(name,*a,**k)):
            worker.run(self.folder,self.root,self.xbmc,self.gui,self.addon)
        result=self.folder/'result.json';self.assertEqual(json.loads(result.read_text())['status'],'ok')
        self.assertEqual(result.stat().st_mode&0o777,0o600);self.assertEqual((self.folder/'request.json').stat().st_mode&0o777,0o600)
        self.xbmc.log.assert_not_called()
    def test_provider_imports_receive_numeric_plugin_handle_and_restore_parent_argv(self):
        self.request();before=list(sys.argv);seen=[]
        def search(request,context):seen.append(list(sys.argv));return []
        original=worker.importlib.import_module
        with mock.patch.object(worker.importlib,'import_module',side_effect=lambda name,*a,**k:SimpleNamespace(search=search) if name.startswith('provider_adapters.') else original(name,*a,**k)):
            worker.run(self.folder,self.root,self.xbmc,self.gui,self.addon)
        self.assertEqual(seen,[['plugin://plugin.video.jacktook','1','']]);self.assertEqual(sys.argv,before)
    def test_a_late_worker_cannot_recreate_a_removed_job(self):
        self.request()
        def search(request,context):shutil.rmtree(self.folder);return [{'name':'Fixture.Movie.2020.1080p.mkv'}]
        original=worker.importlib.import_module
        with mock.patch.object(worker.importlib,'import_module',side_effect=lambda name,*a,**k:SimpleNamespace(search=search) if name.startswith('provider_adapters.') else original(name,*a,**k)):
            worker.run(self.folder,self.root,self.xbmc,self.gui,self.addon)
        self.assertFalse(self.folder.exists())
    def test_unsafe_worker_identifiers_are_ignored_before_importing_kodi(self):
        for args in ([],['../other'],['a'*32,'extra'],['a'*31],['G'*32]):worker.main(args)
        self.assertEqual(list(self.folder.iterdir()),[])
    def test_default_provider_account_is_read_through_but_explicit_disabled_choice_is_preserved(self):
        addon=SimpleNamespace(getSetting=lambda key:'false',getAddonInfo=lambda key:str(self.root))
        proxy=worker.AddonSettings(addon,'synthetic',{'enabled':'enabled'})
        with mock.patch.dict(sys.modules,{'xbmcvfs':SimpleNamespace(translatePath=lambda path:path)}):
            self.assertEqual(proxy.getSetting('enabled'),'true')
            (self.root/'settings.xml').write_text('<settings><setting id="enabled">false</setting></settings>')
            self.assertEqual(proxy.getSetting('enabled'),'false')
    def test_recursive_module_dependencies_are_available_to_the_isolated_invoker(self):
        for name,xml in {'plugin':'<addon><requires><import addon="module.one"/></requires></addon>',
          'one':'<addon><requires><import addon="module.two"/><import addon="plugin" optional="true"/></requires><extension point="xbmc.python.module" library="lib"/></addon>',
          'two':'<addon><extension point="xbmc.python.module" library="python"/></addon>'}.items():
            root=self.root/name;root.mkdir();(root/'addon.xml').write_text(xml)
            (root/('python' if name=='two' else 'lib')).mkdir()
        native=lambda name:SimpleNamespace(getAddonInfo=lambda key:str(self.root/name))
        addons=SimpleNamespace(Addon=lambda ident:native({'module.one':'one','module.two':'two','plugin':'plugin'}[ident]))
        self.assertEqual(worker.module_paths(native('plugin'),addons),[str(self.root/'one/lib'),str(self.root/'two/python')])
    def test_module_library_cannot_escape_the_installed_addon(self):
        (self.root/'addon.xml').write_text('<addon><extension point="xbmc.python.module" library="../outside"/></addon>')
        with self.assertRaises(ValueError):worker.module_paths(self.native,self.addon)


if __name__=='__main__':unittest.main()
