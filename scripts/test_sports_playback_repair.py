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
 def test_late_workers_keep_scan_lock_and_do_not_publish_premature_done(self):
  import fcntl,tempfile,contextlib
  with tempfile.TemporaryDirectory() as folder:
   home=Home();waits=[];published=[]
   def wait(seconds):
    waits.append(seconds)
    with open(Path(folder)/'sports-jet-scan.lock','a') as other:
     with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
    self.assertFalse(published)
    return len(waits)==3
   provider=NS(_start=lambda:NS(wait=wait),_publish=lambda done:published.append(done))
   with patch.dict(sys.modules,{'xbmc':NS(),'xbmcgui':NS(),'xbmcvfs':NS(translatePath=lambda p:folder)}),patch.object(sj,'named_addon',side_effect=contextlib.nullcontext),patch.object(sj,'JetProvider',return_value=provider):
    sj.run_script([],home)
   self.assertEqual(len(waits),3);self.assertEqual(published,[True]);self.assertFalse(home.getProperty(sj.RUN))
   with open(Path(folder)/'sports-jet-scan.lock','a') as guard:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def test_fallback_log_does_not_include_exception_urls(self):
  logs=[]
  with patch.object(sj,'play_one',side_effect=RuntimeError('https://secret.invalid/path?token=private')):
   with self.assertRaises(RuntimeError):sj.play({'play':'fixture'},logger=logs.append)
  self.assertTrue(logs)
  self.assertNotIn('secret.invalid',' '.join(logs))
  self.assertNotIn('token=private',' '.join(logs))
 def test_nested_streams_retry_and_play_the_resolved_address(self):
  import json
  class Link:
   def __init__(self,address,links=False,resolveurl=False):
    self.address=address;self.links=links;self.resolveurl=resolveurl;self.direct=False
    self.extractor='fixture';self.unquote=True;self.jetproxy=False;self.headers={'Referer':'https://fixture.invalid/'};self.inputstream=None
   @staticmethod
   def from_dict(value):return Link(value['address'],links=True)
   def xbmc_format(self):
    from urllib.parse import urlencode
    return self.address+'|'+urlencode(self.headers)
  nested=[Link('https://bad.invalid/embed',resolveurl=True),Link('https://good.invalid/embed',resolveurl=True)]
  fallback_calls=[]
  def no_fallback(link):fallback_calls.append(link.address);return None
  extractor=NS(name='fixture',get_links=lambda link:nested,get_link=no_fallback)
  module=NS(get_extractor=lambda name:extractor)
  seen=[];logs=[]
  class ListItem:
   def __init__(self,path):self.path=path
   def getPath(self):return self.path
  xbmc=NS(Player=lambda:NS(play=lambda path,item=None:seen.append(path)))
  resolver=NS(resolve=lambda address: '' if 'bad.invalid' in address else 'https://cdn.invalid/stream.mp4|User-Agent=Fixture')
  with patch.object(sj,'import_jet',return_value=(module,None)),patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':NS(ListItem=ListItem),'jetextractors.models':NS(JetLink=Link),'resolveurl':resolver}):
   self.assertTrue(sj.play_one(json.dumps({'e':'fixture','l':{'address':'https://fixture.invalid/list'}}),logs.append))
  from urllib.parse import parse_qs
  self.assertEqual(len(seen),1)
  path,headers=seen[0].split('|',1)
  self.assertEqual(path,'https://cdn.invalid/stream.mp4')
  self.assertEqual(parse_qs(headers),{'User-Agent':['Fixture'],'Referer':['https://fixture.invalid/']})
  self.assertEqual(fallback_calls,['https://bad.invalid/embed'])
  self.assertTrue(any('bad.invalid' in line for line in logs))
  self.assertFalse(any('/embed' in line for line in logs))
  # HLS goes through JetProxy; resolver and extractor headers must both survive.
  import base64
  from urllib.parse import urlsplit
  seen.clear();fallback_calls.clear();resolver.resolve=lambda address:'https://cdn.invalid/live.m3u8|User-Agent=Fixture'
  with patch.object(sj,'import_jet',return_value=(module,None)),patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':NS(ListItem=ListItem),'jetextractors.models':NS(JetLink=Link),'resolveurl':resolver}):
   self.assertTrue(sj.play_one(json.dumps({'e':'fixture','l':{'address':'https://fixture.invalid/list'}}),logs.append))
  self.assertTrue(seen[0].startswith('plugin://plugin.video.jetproxy/play/https://cdn.invalid/live.m3u8?'))
  self.assertEqual(fallback_calls,[])
  encoded=parse_qs(urlsplit(seen[0]).query)['h'][0]
  self.assertEqual(json.loads(base64.urlsafe_b64decode(encoded)),{'User-Agent':'Fixture','Referer':'https://fixture.invalid/'})
 def test_scraper_resolver_is_used_when_resolveurl_fails(self):
  import json
  class Link:
   def __init__(self,address,resolveurl=False,direct=False):
    self.address=address;self.resolveurl=resolveurl;self.direct=direct;self.links=False
    self.unquote=True;self.jetproxy=False;self.headers={};self.inputstream=None
   @staticmethod
   def from_dict(value):return Link(value['address'],resolveurl=True)
   def xbmc_format(self):return self.address
  fallback_calls=[]
  def own_resolver(link):
   fallback_calls.append(link.address);return Link('https://cdn.invalid/live.mp4')
  extractor=NS(get_link=own_resolver)
  module=NS(get_extractor=lambda name:extractor)
  paths=[]
  class ListItem:
   def __init__(self,path):self.path=path
   def getPath(self):return self.path
  xbmc=NS(Player=lambda:NS(play=lambda path,item=None:paths.append(path)))
  with patch.object(sj,'import_jet',return_value=(module,None)),patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':NS(ListItem=ListItem),'jetextractors.models':NS(JetLink=Link),'resolveurl':NS(resolve=lambda address:'')}):
   self.assertTrue(sj.play_one(json.dumps({'e':'LiveFeeds','l':{'address':'https://embed.invalid/watch'}}),lambda text:None))
  self.assertEqual(paths,['https://cdn.invalid/live.mp4'])
  self.assertEqual(fallback_calls,['https://embed.invalid/watch'])
 def test_existing_loopback_proxy_is_played_directly_with_inputstream(self):
  import json
  calls=[];applied=[]
  class Link:
   address='http://127.0.0.1:48123/token/video.m3u8';unquote=True;links=False;direct=True;resolveurl=False;jetproxy=False;headers={'Referer':'https://fixture.invalid/'}
   inputstream=NS(set_properties=lambda item:applied.append(item))
   @staticmethod
   def from_dict(value):return Link()
   def xbmc_format(self):return self.address+'|Referer=fixture'
  class ListItem:
   def __init__(self,path):self.path=path
   def getPath(self):return self.path
  xbmc=NS(Player=lambda:NS(play=lambda path,item=None:calls.append(path)))
  module=NS(get_extractor=lambda name:NS())
  with patch.object(sj,'import_jet',return_value=(module,None)),patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':NS(ListItem=ListItem),'jetextractors.models':NS(JetLink=Link)}):
   self.assertTrue(sj.play_one(json.dumps({'e':'fixture','l':{'address':'fixture'}}),lambda text:None))
  self.assertEqual(calls,['http://127.0.0.1:48123/token/video.m3u8|Referer=fixture'])
  self.assertEqual(len(applied),1)
  self.assertEqual(sj._play_session.proxy_url,'http://127.0.0.1:48123/token/video.m3u8')
 def test_local_proxy_lifetime_waits_for_start_and_stop(self):
  address='http://127.0.0.1:48123/video.m3u8';states=iter([False,True,True,False]);waits=[]
  player=NS(isPlaying=lambda:next(states),getPlayingFile=lambda:address+'|Referer=fixture')
  monitor=NS(abortRequested=lambda:False,waitForAbort=lambda seconds:(waits.append(seconds) or False))
  sj.hold_local_proxy(NS(Player=lambda:player,Monitor=lambda:monitor),address)
  self.assertEqual(len(waits),3)
 def test_proxy_waits_through_previous_video_and_exits_when_replaced(self):
  address='http://127.0.0.1:48123/video.m3u8'
  current=iter(['https://old.invalid/a',address,'https://new.invalid/b']);waits=[]
  player=NS(isPlaying=lambda:True,getPlayingFile=lambda:next(current))
  monitor=NS(abortRequested=lambda:False,waitForAbort=lambda seconds:(waits.append(seconds) or False))
  sj.hold_local_proxy(NS(Player=lambda:player,Monitor=lambda:monitor),address)
  self.assertEqual(len(waits),2)
 def test_live_page_does_not_play_handled_boolean(self):
  # Execute the actual onClick method with only its native dependencies substituted.
  import importlib.util
  spec=importlib.util.spec_from_file_location('sports_live_repair',ROOT/'migration/bundled-bootstrap/sports_live.py')
  live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/sports_live.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='onClick')
  plays=[];env={'lp':NS(BACK=1,REFRESH=2,RETRY=3,SEE_UPCOMING=4),'control_target':lambda c:('source',1,1),'sports_provider':NS(play=lambda *a,**k:True),'play_source':live.play_source,'log':lambda *a:None,'xbmc':NS(Player=lambda:NS(play=lambda p:plays.append(p))),'xbmcgui':NS()}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-onclick','exec'),env)
  page=NS(slots={(1,1):{'id':'fixture'}},finish=lambda:None);env['onClick'](page,10);self.assertFalse(plays)
  env['sports_provider'].play=lambda *a,**k:'https://fixture.invalid/live.m3u8';env['onClick'](page,10);self.assertEqual(len(plays),1)
if __name__=='__main__':unittest.main()
