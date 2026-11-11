"""Performance pass (docs/ROADMAP-PERFORMANCE.md 1E): on-demand Elementum engine and the other start-up trims."""
import sys,unittest
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

if __name__=='__main__':unittest.main()
