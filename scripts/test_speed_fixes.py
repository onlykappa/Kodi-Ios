"""Performance pass (docs/ROADMAP-PERFORMANCE.md 1E): on-demand Elementum engine and the other start-up trims."""
import ast,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
LIB=ROOT/'migration/bundled-bootstrap/resources/lib';sys.path.insert(0,str(LIB))
import elementum_engine,elementum_download
from build_customized_ipa import ELEMENTUM_PATCHES

SERVICE=b'import threading\nfrom elementum.daemon import elementumd_thread\n\ndef run():\n    threads = []\n    if not ONLY_CLIENT and PLATFORM["fork"]:\n        threads.append(threading.Thread(target=elementumd_thread, args=[monitor]))  # Elementumd thread\n'

class LazyEngine(unittest.TestCase):
 def test_ensure_starts_only_when_not_running(self):
  asked=[]
  self.assertTrue(elementum_engine.ensure(lambda:asked.append(1),lambda:False,is_running=lambda:True));self.assertEqual(asked,[])
  states=iter([False,False,False,True])
  self.assertTrue(elementum_engine.ensure(lambda:asked.append(1),lambda:False,is_running=lambda:next(states)));self.assertEqual(asked,[1])
 def test_ensure_gives_up_when_cancelled_or_late(self):
  self.assertFalse(elementum_engine.ensure(lambda:None,lambda:True,is_running=lambda:False))
  self.assertFalse(elementum_engine.ensure(lambda:None,lambda:False,is_running=lambda:False,attempts=3))
 def test_follow_asks_for_the_engine_once_before_its_first_request(self):
  calls=[]
  class R:
   def read(self):return b''
  class Opener:
   def open(self,url,timeout=0):calls.append(('open',url));return R()
  elementum_download.follow('plugin://plugin.video.elementum/x',opener=Opener(),route=lambda u:False,engine=lambda:calls.append('engine'))
  self.assertEqual(calls[0],'engine');self.assertEqual(calls.count('engine'),1)
 def test_follow_skips_the_engine_when_the_cloud_route_handles_the_link(self):
  calls=[]
  elementum_download.follow('plugin://plugin.video.elementum/x',opener=object(),route=lambda u:True,engine=lambda:calls.append('engine'))
  self.assertEqual(calls,[])
 def test_service_patch_waits_for_demand_and_compiles(self):
  text=SERVICE
  for name,old,new in ELEMENTUM_PATCHES:
   if name.endswith('/service.py') and old in text:text=text.replace(old,new)
  self.assertIn(b'target=kios_engine_thread',text);self.assertIn(b'KodiIOS.ElementumEngine',text)
  compile(text.decode(),'service.py','exec')
  self.assertIn(elementum_engine.WANTED.encode(),text)
 def test_plugin_asks_for_the_engine_after_the_cloud_check(self):
  (after,)=[n for f,o,n in ELEMENTUM_PATCHES if o==b'def _json(url):\n']
  self.assertLess(after.index(b'_kodi_cloud(url)'),after.index(b'    _kodi_engine()\n'))

SERVICE_PY=ROOT/'migration/bundled-bootstrap/service.py'

class StartupImports(unittest.TestCase):
 def tree(self):return ast.parse(SERVICE_PY.read_text())
 def test_heavy_modules_are_not_imported_at_module_level(self):
  eager={a.name for n in self.tree().body if isinstance(n,ast.Import) for a in n.names}
  eager|={n.module for n in self.tree().body if isinstance(n,ast.ImportFrom)}
  for name in ('portrait','driveupload','activity','signin_server','umbrella_ready','background','calibration'):self.assertNotIn(name,eager)
 def test_late_module_imports_on_first_attribute_only(self):
  cls=[n for n in self.tree().body if isinstance(n,ast.ClassDef) and n.name=='_Late'][0]
  space={};exec(compile(ast.Module([cls],[]),'service.py','exec'),space)
  late=space['_Late']('json');self.assertIsNone(late._module)
  self.assertEqual(late.dumps([1]),'[1]');self.assertIsNotNone(late._module)
 def test_service_names_still_bound(self):
  src=SERVICE_PY.read_text()
  for name in ('activity','signin_server','background','calibration','driveupload','portrait','umbrella_ready'):self.assertIn(name+'.',src)
  self.assertIn("[_Late(n) for n in",src)

import threading,time,re
import page_wait

class PageLoops(unittest.TestCase):
 class Quiet:
  def abortRequested(self):return False
 def test_idle_wakes_when_the_page_closes(self):
  stop=threading.Event();threading.Timer(0.05,stop.set).start()
  begun=time.monotonic();self.assertTrue(page_wait.idle(stop,self.Quiet(),5))
  self.assertLess(time.monotonic()-begun,1)
 def test_idle_times_out_and_follows_abort(self):
  self.assertFalse(page_wait.idle(threading.Event(),self.Quiet(),0.05))
  class Abort:
   def abortRequested(self):return True
  self.assertTrue(page_wait.idle(threading.Event(),Abort(),5))
 def test_no_page_loop_sleeps_in_waitForAbort_ignoring_its_stop_event(self):
  base=ROOT/'migration/bundled-bootstrap'
  for path in list(base.glob('*.py'))+[base/'resources/lib/tool_windows.py']:
   self.assertNotRegex(path.read_text(),r'self\.stop\.is_set\(\) and not monitor\.waitForAbort',path.name)

from build_import_review import patch_helper
import test_import_builder

TOKEN_SOURCE=b'''class T:
    @cached_property
    def winprop_traktisauth(self):
        winprop_traktisauth = get_property('TraktIsAuth', is_type=float)
        winprop_traktisauth = winprop_traktisauth or self.authorization_check()  # first start
        return winprop_traktisauth or 0
'''
TOKEN_PATH='resources/tmdbhelper/lib/api/trakt/token.py'

class TraktDeferral(unittest.TestCase):
 def fixture(self):return test_import_builder.BuilderTests().fixture()
 def test_saved_valid_token_is_confirmed_in_the_background(self):
  import threading,time,types
  p,files=self.fixture();files[p+TOKEN_PATH]=TOKEN_SOURCE
  out,changes=patch_helper(files,'plugin.video.themoviedb.helper');source=out[p+TOKEN_PATH].decode();tree=ast.parse(source)
  self.assertIn('self.ios_deferred_check()',source);self.assertNotIn('or self.authorization_check()',source)
  self.assertTrue(any('Trakt token check' in c for c in changes))
  method=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='ios_deferred_check'][0]
  props={};done=threading.Event();calls=[]
  def get_property(key,set_property=None,clear_property=False):
   if clear_property:props.pop(key,None)
   else:props[key]=set_property
  space={'get_property':get_property};exec(ast.unparse(ast.Module([method],[])),space)
  def check(valid,confirmed):
   me=types.SimpleNamespace(access_token='a',refresh_token='r',has_valid_token=valid,expires_in_timestamp=99.0,
    update_traktisauth_property=lambda:props.__setitem__('TraktIsAuth','99.0'))
   def authorization_check():calls.append('net');done.set();return confirmed
   me.authorization_check=authorization_check;done.clear();calls.clear();props.clear()
   result=space['ios_deferred_check'](me);done.wait(2);time.sleep(0.05);return result
  self.assertEqual(check(True,False),99.0);self.assertNotIn('TraktIsAuth',props)   # rejected: next use checks again
  self.assertEqual(check(True,True),99.0);self.assertEqual(props['TraktIsAuth'],'99.0')
  self.assertIsNone(check(False,None));self.assertEqual(calls,['net'])   # expired: the old blocking check
 def test_changed_upstream_token_code_stops_the_build(self):
  p,files=self.fixture();files[p+TOKEN_PATH]=b'# upstream changed\n'
  with self.assertRaises(AssertionError):patch_helper(files,'plugin.video.themoviedb.helper')

if __name__=='__main__':unittest.main()
