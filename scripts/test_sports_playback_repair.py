"""Owner build557: true-as-path, hidden ResolveURL and repeated full scraper collections."""
import sys,unittest,ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import sports_jet as sj
class Home:
 def __init__(self):self.p={}
 def getProperty(self,k):return self.p.get(k,'')
 def setProperty(self,k,v):self.p[k]=v
 def clearProperty(self,k):self.p.pop(k,None)
class Repair(unittest.TestCase):
 def test_resolver_log_host_omits_secrets_and_headers(self):
  self.assertEqual(sj.resolver_host('https://' + 'user' + ':' + 'pw' + '@media.example/path?token=private|Authorization=private'),'media.example')
  self.assertEqual(sj.resolver_host('not a URL with secret'),'unknown')
 def test_import_also_loads_resolveurl_module_graph(self):
  paths=[]
  with patch.object(sj,'add_module_paths',side_effect=lambda name,find:paths.append(name)),patch.dict(sys.modules,{'jetextractors':NS(),'jetextractors.extractor':NS()}):sj.import_jet()
  self.assertIn('script.module.resolveurl',paths)
 def test_forced_refresh_joins_running_scan_and_keeps_old_data(self):
  import json
  home=Home();home.setProperty(sj.RUN,'1000');home.setProperty(sj.DATA,json.dumps({'at':900,'done':True,'records':[]}));calls=[]
  p=sj.JetProvider(remote=True,window=home,clock=lambda:1001,wait=0,launch=lambda *a:calls.append(a))
  with self.assertRaises(Exception):p._remote_load(True)
  self.assertFalse(calls);self.assertTrue(home.getProperty(sj.DATA))
 def test_unresolved_page_never_falls_back_to_original_address(self):
  link=NS(address='https://fixture.invalid/page',links=False,direct=False,resolveurl=False)
  for answer in [None,link,NS(address=link.address,direct=False,resolveurl=False)]:
   self.assertIsNone(sj.expand(NS(),NS(get_link=lambda l:answer),link))
 def test_real_resolved_link_still_accepted(self):
  link=NS(address='https://fixture.invalid/page',links=False,direct=False,resolveurl=False)
  final=NS(address='https://fixture.invalid/video.m3u8',direct=True)
  self.assertIs(sj.expand(NS(),NS(get_link=lambda l:final),link),final)
 def test_second_interpreter_scan_joins_the_process_lock(self):
  import fcntl,tempfile
  with tempfile.TemporaryDirectory() as folder:
   home=Home()
   with open(Path(folder)/'sports-jet-scan.lock','a') as guard:
    fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with patch.dict(sys.modules,{'xbmcgui':NS(),'xbmcvfs':NS(translatePath=lambda p:folder)}),patch.object(sj,'JetProvider') as factory:
     sj.run_script([],home)
     factory.assert_not_called()
 def test_failed_collection_releases_lock_and_running_marker(self):
  import fcntl,tempfile,contextlib
  with tempfile.TemporaryDirectory() as folder:
   home=Home();home.setProperty(sj.RUN,'1000')
   with patch.dict(sys.modules,{'xbmcgui':NS(),'xbmcvfs':NS(translatePath=lambda p:folder)}),patch.object(sj,'named_addon',side_effect=contextlib.nullcontext),patch.object(sj,'JetProvider') as factory:
    factory.return_value._start.side_effect=RuntimeError('fixture collection failure')
    with self.assertRaisesRegex(RuntimeError,'fixture collection failure'):sj.run_script([],home)
   self.assertFalse(home.getProperty(sj.RUN))
   with open(Path(folder)/'sports-jet-scan.lock','a') as guard:
    fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def test_live_page_does_not_play_handled_boolean(self):
  # Execute the actual onClick method with only its native dependencies substituted.
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/sports_live.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='onClick')
  plays=[];env={'lp':NS(BACK=1,REFRESH=2,RETRY=3,SEE_UPCOMING=4),'control_target':lambda c:('source',1,1),'sports_provider':NS(play=lambda *a:True),'log':lambda *a:None,'xbmc':NS(Player=lambda:NS(play=lambda p:plays.append(p)))}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-onclick','exec'),env)
  page=NS(slots={(1,1):{'id':'fixture'}});env['onClick'](page,10);self.assertFalse(plays)
  env['sports_provider'].play=lambda *a:'https://fixture.invalid/live.m3u8';env['onClick'](page,10);self.assertEqual(len(plays),1)
if __name__=='__main__':unittest.main()
