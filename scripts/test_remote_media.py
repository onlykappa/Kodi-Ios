"""Foreground HTTP cache reuses Drive ranges without its credentials, throttling or disk storage."""
import ast,io,json,sys,threading,time,types,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import remote_media as remote,drive_stream,slowdown
DATA=bytes(range(256))*(5*1024*1024//256+1)
class Reply(io.BytesIO):
 def __init__(self,data,start,end):
  super().__init__(data[start:end+1]);self.status=206
  self.headers={'Content-Range':'bytes %d-%d/%d'%(start,min(end,len(data)-1),len(data))}
 def getcode(self):return self.status
class Cache(unittest.TestCase):
 def setUp(self):self.requests=[];self.lock=threading.Lock()
 def open(self,request,timeout):
  with self.lock:self.requests.append(request)
  a,b=map(int,request.get_header('Range')[6:].split('-'))
  return Reply(DATA,a,min(b,len(DATA)-1))
 def source(self,url='https://media.example/episode.mkv'):
  source=remote.Foreground(url,open_url=self.open);self.addCleanup(source.close);return source
 def read(self,source,a,b):
  with urllib.request.urlopen(urllib.request.Request(source.media_url,headers={'Range':'bytes=%d-%d'%(a,b)}),timeout=5) as r:return r.read()
 def test_ranges_are_exact_and_repeated_probe_reads_reuse_blocks(self):
  s=self.source()
  for _ in range(5):self.assertEqual(self.read(s,0,65535),DATA[:65536])
  self.assertEqual(self.read(s,len(DATA)-123,len(DATA)-1),DATA[-123:])
  self.assertLessEqual(len(self.requests),3)
  self.assertTrue(all(r.full_url=='https://media.example/episode.mkv' for r in self.requests))
 def test_source_metrics_explain_cache_and_upstream_reads_without_url_or_headers(self):
  source=self.source('https://media.example/episode.mkv?secret=PRIVATE|Authorization=Bearer%20PRIVATE')
  self.read(source,0,99);self.read(source,0,99)
  stats=source.stats()
  self.assertGreater(stats['cache_hits'],0);self.assertGreater(stats['cache_misses'],0)
  self.assertGreater(stats['http_requests'],0);self.assertEqual(stats['last_status'],206)
  self.assertGreater(stats['read_bytes'],0);self.assertIn('source_read_ms',stats)
  self.assertNotIn('PRIVATE',json.dumps(stats));self.assertNotIn('https://',json.dumps(stats))
 def test_cross_block_and_suffix_ranges(self):
  s=self.source();a=2*1024*1024-10;b=a+99
  self.assertEqual(self.read(s,a,b),DATA[a:b+1])
  with urllib.request.urlopen(urllib.request.Request(s.media_url,headers={'Range':'bytes=-20'})) as r:self.assertEqual(r.read(),DATA[-20:])
 def test_only_the_original_provider_headers_are_forwarded(self):
  s=self.source('https://media.example/episode.mkv|user-agent=TestPlayer&Authorization=Bearer%20test&Cookie=a%3Db&Range=bad')
  self.read(s,0,99);request=self.requests[0]
  self.assertEqual(request.get_header('User-agent'),'TestPlayer')
  self.assertEqual(request.get_header('Authorization'),'Bearer test');self.assertEqual(request.get_header('Cookie'),'a=b')
  self.assertTrue(request.get_header('Range').startswith('bytes=0-'))
 def test_no_drive_authorization_is_sent_to_the_provider(self):
  s=self.source();self.read(s,0,99);self.assertIsNone(self.requests[0].get_header('Authorization'))
 def test_foreground_reads_do_not_use_the_background_download_gate(self):
  s=self.source()
  with patch.object(slowdown.Gate,'after',side_effect=AssertionError('foreground throttled')):
   self.assertEqual(self.read(s,0,99),DATA[:100])
 def test_wrong_upstream_range_is_rejected(self):
  response=Reply(DATA,0,100)
  s=remote.Foreground('https://media.example/file.mkv',open_url=lambda *a:response);self.addCleanup(s.close)
  with self.assertRaisesRegex(ConnectionError,'wrong byte range'):s._fetch('media',2097152,2097251)
 def test_cache_size_and_default_drive_profile_are_unchanged(self):
  # ISSUE-163: 4 MiB blocks, 24 kept, four fetched at once for the TV's source; Drive's own profile unchanged.
  s=self.source();self.assertEqual((s.block_size,s.blocks.keep,s.ahead_blocks),(4*1024*1024,24,4))
  blocks=drive_stream._Blocks(lambda *a:None)
  self.assertEqual((blocks.block_size,blocks.keep),(8*1024*1024,24))
 def test_known_working_local_sources_and_playlists_bypass_the_adapter(self):
  for url in ('http://127.0.0.1:1234/file.mkv','http://localhost:1/x.mkv','http://[::1]:2/x.mkv','https://x.example/a.m3u8','https://x.example/a.mp4'):
   self.assertFalse(remote.eligible(url))
  self.assertTrue(remote.eligible('https://x.example/a.MKV?expires=1'))
class SlowLink(unittest.TestCase):
 """ISSUE-163: a debrid link answers each request slowly; reading the start of an episode in order must keep four
 requests in flight, not one or two (build 224: 2 MiB per 2.6-3 s, 20-50 s before the first picture)."""
 def test_sequential_read_keeps_four_requests_in_flight(self):
  data=bytes(range(256))*(24*1024*1024//256);state={'now':0,'most':0};lock=threading.Lock()
  def slow(request,timeout):
   with lock:state['now']+=1;state['most']=max(state['most'],state['now'])
   try:
    time.sleep(.5);a,b=map(int,request.get_header('Range')[6:].split('-'));return Reply(data,a,min(b,len(data)-1))
   finally:
    with lock:state['now']-=1
  s=remote.Foreground('https://media.example/slow.mkv',open_url=slow);self.addCleanup(s.close)
  began=time.monotonic();got=0
  with urllib.request.urlopen(urllib.request.Request(s.media_url,headers={'Range':'bytes=0-%d'%(len(data)-1)}),timeout=30) as r:
   while True:
    chunk=r.read(1<<20)
    if not chunk:break
    got+=len(chunk)
  took=time.monotonic()-began
  self.assertEqual(got,len(data));self.assertGreaterEqual(state['most'],4)
  self.assertLess(took,3.0)   # 6 blocks at 0.5 s each: about 1 s in parallel, 3 s one after another
class Broker(unittest.TestCase):
 def setUp(self):
  self.sources=[]
  def factory(url):
   def open(request,timeout):
    a,b=map(int,request.get_header('Range')[6:].split('-'));return Reply(DATA,a,min(b,len(DATA)-1))
   source=remote.Foreground(url,open_url=open);self.sources.append(source);return source
  self.broker=remote.Broker(source_factory=factory);self.addCleanup(self.broker.close)
  self.home=type('Home',(),{'getProperty':lambda _,key:self.broker.url})()
 def test_real_service_registers_cache_with_a_path_home_and_closes_on_abort(self):
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/service.py').read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='drive_uploads')
  setup=next(n for n in fn.body if isinstance(n,ast.Try) and any(isinstance(c,ast.Name) and c.id=='remote_media' for c in ast.walk(n)))
  properties={};stopped=threading.Event();closed=threading.Event();errors=[]
  window=types.SimpleNamespace(setProperty=lambda k,v:properties.update({k:v}),getProperty=lambda k:properties.get(k,''),clearProperty=lambda k:properties.pop(k,None))
  def close():
   try:original_close()
   finally:closed.set()
  original_close=self.broker.close
  self.broker.close=close
  env=dict(home=Path('/synthetic/kodi/home'),remote_media=remote,tls_context=lambda:None,native_reader=None,
           xbmcgui=types.SimpleNamespace(Window=lambda ident:window if ident==10000 else None),
           monitor=types.SimpleNamespace(waitForAbort=lambda delay:stopped.wait(.01)),threading=threading,xbmc=object(),
           diagnostics=types.SimpleNamespace(log_exception=lambda *args:errors.append(args)))
  try:
   with patch.object(remote,'Broker',return_value=self.broker):
    exec(compile(ast.Module(body=[setup],type_ignores=[]),'service-cache-setup','exec'),env)
   self.assertFalse(errors);self.assertEqual(properties[remote.PROPERTY],self.broker.url)
   url,lease=remote.acquire('https://media.example/episode.mkv',window)
   self.assertIsNotNone(lease);self.assertTrue(url.startswith('http://127.0.0.1:'))
   with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-9'})) as response:
    self.assertEqual(response.read(),DATA[:10])
  finally:
   stopped.set();self.assertTrue(closed.wait(3))
  self.assertNotIn(remote.PROPERTY,properties);self.assertIsNone(self.broker.current)
 def test_registration_failure_closes_the_started_server(self):
  window=types.SimpleNamespace(setProperty=lambda *args:(_ for _ in ()).throw(RuntimeError('window unavailable')))
  with patch.object(remote,'Broker',return_value=self.broker),patch.object(self.broker,'close') as close:
   with self.assertRaisesRegex(RuntimeError,'window unavailable'):remote.start(object(),window)
   close.assert_called_once()
 def test_support_sampler_reads_safe_stats_from_the_service_owned_source(self):
  _,lease=remote.acquire('https://media.example/episode.mkv',self.home)
  with urllib.request.urlopen(urllib.request.Request(self.broker.current.media_url,headers={'Range':'bytes=0-99'})) as response:response.read()
  counters=remote.stats(self.home)
  self.assertGreater(counters['http_requests'],0);self.assertGreater(counters['cache_misses'],0)
  self.assertNotIn('media.example',json.dumps(counters));self.assertNotIn(self.broker.ident,json.dumps(counters))
  lease.close();self.assertEqual(remote.stats(self.home),{})
 def test_service_owned_source_and_explicit_close(self):
  url,lease=remote.acquire('https://media.example/episode.mkv',self.home)
  self.assertTrue(url.startswith('http://127.0.0.1:'));self.assertIsNotNone(lease)
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-9'})) as r:self.assertEqual(r.read(),DATA[:10])
  lease.close();self.assertIsNone(self.broker.current)
 def test_stale_lease_cannot_close_a_new_source(self):
  _,old=remote.acquire('https://media.example/one.mkv',self.home)
  _,new=remote.acquire('https://media.example/two.mkv',self.home)
  current=self.broker.current;old.close();self.assertIs(self.broker.current,current)
  new.close();self.assertIsNone(self.broker.current)
 def test_missing_or_wrong_control_endpoint_preserves_the_original_route(self):
  for endpoint in ('','http://outside.example/api',self.broker.url+'wrong'):
   home=type('Home',(),{'getProperty':lambda _,key:endpoint})()
   self.assertEqual(remote.acquire('https://media.example/episode.mkv',home),('https://media.example/episode.mkv',None))
 def test_control_endpoint_rejects_an_unknown_token(self):
  with self.assertRaises(urllib.error.HTTPError):remote._call(self.broker.url+'bad',{'action':'open','source':'https://media.example/a.mkv'})
class Warm(Broker):
 """ISSUE-259: the video Kodi plays is read ahead (start and end) so Play on TV takes a warm source."""
 def test_warm_source_is_taken_by_play_on_tv_with_its_blocks(self):
  endpoint=self.broker.url;src='https://media.example/episode.mkv'
  ident=remote._call(endpoint,{'action':'warm','source':src})['id']
  warm=self.broker.current
  for _ in range(100):
   if warm.blocks.misses>=2 and not warm.blocks.pending:break
   time.sleep(.02)
  self.assertIn(('media',0),warm.blocks.data);self.assertIn(('media',(len(DATA)-1)//remote.BLOCK),warm.blocks.data)
  url,lease=remote.acquire(src,self.home)
  self.assertTrue(lease.warmed);self.assertIs(self.broker.current,warm);self.assertNotEqual(lease.ident,ident)
  remote._call(endpoint,{'action':'cool','id':ident});self.assertIs(self.broker.current,warm)   # the TV keeps it
  self.assertEqual(remote._call(endpoint,{'action':'warm','source':'https://media.example/other.mkv'}),{'busy':True})
  lease.close();self.assertIsNone(self.broker.current)
 def test_cool_releases_an_untaken_source_and_another_video_replaces_it(self):
  endpoint=self.broker.url
  one=remote._call(endpoint,{'action':'warm','source':'https://media.example/one.mkv'})['id']
  first=self.broker.current
  remote._call(endpoint,{'action':'warm','source':'https://media.example/two.mkv'})
  self.assertIsNot(self.broker.current,first)
  remote._call(endpoint,{'action':'cool','id':one});self.assertIsNotNone(self.broker.current)   # stale id
  two=self.broker.ident;remote._call(endpoint,{'action':'cool','id':two});self.assertIsNone(self.broker.current)
  _,lease=remote.acquire('https://media.example/three.mkv',self.home);self.assertFalse(lease.warmed);lease.close()
 def run_watch(self,files,steady=True,wifi=True):
  calls=[];ticks=iter(range(10**6));seq=iter(files)
  def call(endpoint,payload):calls.append(payload['action']);return {'id':'w1'} if payload['action']=='warm' else {}
  def wait(_):
   try:self.now=next(seq);return False
   except StopIteration:return True
  clock=lambda:next(ticks)*3
  with patch.object(remote,'_call',call):
   remote.watch(self.home,lambda:self.now,lambda:steady,lambda:wifi,wait,clock=clock)
  return calls
 def test_watch_warms_once_after_steady_play_and_releases_on_stop(self):
  src='https://media.example/episode.mkv|User-Agent=x'
  self.assertEqual(self.run_watch([src]*8+['']),['warm','cool'])
  self.assertEqual(self.run_watch([src]*8+[src]*5),['warm'])   # a pause or more playing keeps it, warmed once
 def test_watch_reads_nothing_on_cellular_buffering_or_local_links(self):
  src='https://media.example/episode.mkv'
  self.assertEqual(self.run_watch([src]*8+[''],wifi=False),[])
  self.assertEqual(self.run_watch([src]*8+[''],steady=False),[])
  self.assertEqual(self.run_watch(['http://127.0.0.1:5000/a.mkv']*8+['']),[])
  self.assertEqual(self.run_watch(['https://media.example/a.m3u8']*8),[])
 def test_service_warms_only_with_a_converting_framework_on_wifi(self):
  text=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn("if airplay.converts(playback_lib):",text);self.assertIn("cache_tune.link_kind()=='wifi'",text)
  self.assertIn('target=remote_media.watch',text)
class KodiPlays(Broker):
 """ISSUE-280 (owner, build 430 log 72b62563: an Umbrella episode sat at "Getting ready to play… 0%" for 32 s, 19 s of
 it in Kodi's own open of the MKV over one AllDebrid connection): Kodi's player reads it through the cache."""
 SRC='https://media.example/Black.Clover.S02E07.1080p.CR.WEB.mkv'
 def settle(self,source):
  for _ in range(150):
   if source.blocks.misses>=2 and not source.blocks.pending:break
   time.sleep(.02)
 def test_umbrella_link_goes_through_the_cache_with_start_and_end_asked_for(self):
  url=remote.for_kodi(self.SRC,self.home)
  self.assertTrue(url.startswith('http://127.0.0.1:'));self.assertTrue(self.broker.kodi)
  current=self.broker.current;self.settle(current)
  self.assertIn(('media',0),current.blocks.data);self.assertIn(('media',(len(DATA)-1)//remote.BLOCK),current.blocks.data)
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-9'})) as r:self.assertEqual(r.read(),DATA[:10])
 def test_other_links_and_a_missing_service_keep_the_link(self):
  for src in ('https://media.example/a.mp4','https://media.example/a.m3u8','http://127.0.0.1:9/a.mkv'):
   self.assertEqual(remote.for_kodi(src,self.home),src)
  nobody=type('Home',(),{'getProperty':lambda _,key:''})()
  self.assertEqual(remote.for_kodi(self.SRC,nobody),self.SRC)
  with patch.object(remote,'KODI_PLAYBACK',False):self.assertEqual(remote.for_kodi(self.SRC,self.home),self.SRC)
 def test_play_on_tv_gets_the_real_link_and_shares_the_cache(self):
  url=remote.for_kodi(self.SRC,self.home);current=self.broker.current
  self.assertEqual(remote.original(url+'|User-Agent=Kodi',self.home),self.SRC)    # never 127.0.0.1 for a TV
  self.assertEqual(remote.original('https://other.example/x.mkv',self.home),'https://other.example/x.mkv')
  tv,lease=remote.acquire(self.SRC,self.home)
  self.assertTrue(lease.warmed);self.assertIs(self.broker.current,current);self.assertEqual(tv,url)
  lease.close();self.assertIs(self.broker.current,current)          # Kodi may still read it: released when idle
 def test_idle_source_is_released(self):
  remote.for_kodi(self.SRC,self.home);current=self.broker.current;self.settle(current)
  self.assertFalse(self.broker.reap(now=self.broker.opened+5))
  with patch.object(time,'time',return_value=time.time()+remote.KODI_IDLE+1):
   self.assertTrue(self.broker.reap(now=self.broker.opened+remote.KODI_IDLE+1))
  self.assertIsNone(self.broker.current);self.assertFalse(self.broker.kodi)
 def test_umbrella_unlock_hands_kodi_the_cache(self):
  import umbrella_recovery
  class Home:
   def __init__(self):self.p={}
   def setProperty(self,k,v):self.p[k]=v
   def getProperty(self,k):return self.p.get(k,'')
  home=Home();warmed=[];answer={'link':self.SRC,'filename':'e.mkv','filesize':len(DATA)}
  umbrella_recovery.remember('https://host.example/f/abc',answer,home=home,warm=lambda *a:warmed.append(a),route=lambda src,h:'http://127.0.0.1:1/x/media/source')
  self.assertEqual(answer['link'],'http://127.0.0.1:1/x/media/source');self.assertEqual(warmed,[])
  self.assertEqual(umbrella_recovery.selected(self.SRC,home)['source'],self.SRC)   # renewal keeps the real link
  answer={'link':self.SRC,'filename':'e.mkv','filesize':len(DATA)}
  umbrella_recovery.remember('https://host.example/f/abc',answer,home=home,warm=lambda *a:warmed.append(a),route=lambda src,h:1/0)
  self.assertEqual(answer['link'],self.SRC);self.assertEqual(len(warmed),1)          # any failure: as before
 def test_play_on_tv_translates_what_kodi_plays(self):
  text=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  self.assertIn('playing=remote_media.original(player.getPlayingFile(),home)',text)
  self.assertIn('url,needs_phone=cast.stream_url(playing,phone)',text)
  self.assertNotIn('playing=player.getPlayingFile()',text)
class Controller(Broker):
 def test_airplay_controller_passes_the_cached_source_and_releases_it(self):
  import importlib.util,types
  spec=importlib.util.spec_from_file_location('cache_cast_controller',ROOT/'migration/bundled-bootstrap/cast.py')
  controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
  raw='https://media.example/episode.mkv';lib=object()
  gui=types.SimpleNamespace(Window=lambda n:self.home)
  xbmc=types.SimpleNamespace(log=lambda *a:None,LOGINFO=1)
  for fails in (False,True):
   def play(*args):
    self.assertTrue(args[-2].startswith('http://127.0.0.1:'));self.assertIsNotNone(args[-1]);self.assertIsNotNone(self.broker.current)
    if fails:raise RuntimeError('cancelled startup')
   with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(controller.airplay,'load',return_value=lib),\
        patch.object(controller.airplay,'converts',return_value=True),patch.object(controller.cast,'airplay_source',return_value=raw),\
        patch.object(controller,'_send_airplay',side_effect=play):
    if fails:
     with self.assertRaises(RuntimeError):controller.send_airplay(xbmc,None,None,'lib',raw,'Movie',raw)
    else:controller.send_airplay(xbmc,None,None,'lib',raw,'Movie',raw)
   self.assertIsNone(self.broker.current)
 def test_airplay_playing_handoff_keeps_the_service_cache_alive(self):
  import importlib.util,types
  spec=importlib.util.spec_from_file_location('cache_cast_handoff',ROOT/'migration/bundled-bootstrap/cast.py')
  controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
  raw='https://media.example/episode.mkv';gui=types.SimpleNamespace(Window=lambda n:self.home)
  xbmc=types.SimpleNamespace(log=lambda *a:None,LOGINFO=1)
  with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(controller.airplay,'load',return_value=object()),\
       patch.object(controller.airplay,'converts',return_value=True),patch.object(controller.cast,'airplay_source',return_value=raw),\
       patch.object(controller,'_send_airplay',return_value=True):
   self.assertTrue(controller.send_airplay(xbmc,None,None,'lib',raw,'Movie',raw))
  self.assertIsNotNone(self.broker.current)
  with urllib.request.urlopen(urllib.request.Request(self.broker.current.media_url,headers={'Range':'bytes=0-9'})) as r:
   self.assertEqual(r.read(),DATA[:10])
 def test_tv_handoff_keeps_cache_but_native_failure_closes_it(self):
  import importlib.util,types
  spec=importlib.util.spec_from_file_location('cache_tv_handoff',ROOT/'migration/bundled-bootstrap/cast.py')
  controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
  raw='https://media.example/episode.mkv';gui=types.SimpleNamespace(Window=lambda n:self.home)
  xbmc=types.SimpleNamespace(log=lambda *a:None,executebuiltin=lambda *a:None,LOGINFO=1,LOGWARNING=2)
  for result in (2,3,'error'):
   def serve(source,compat,out,size):
    self.assertTrue(source.startswith(b'http://127.0.0.1:'))
    if result=='error':raise RuntimeError('native startup failed')
    out.value=b'http://192.0.2.1:1234/master.m3u8';return result
   lib=types.SimpleNamespace(kodi_airplay_serve=serve,kodi_airplay_close=lambda:None)
   with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(controller.airplay,'load',return_value=lib),\
        patch.object(controller.airplay,'send_subtitles',return_value=None),patch.object(controller.airplay,'log_lines',return_value=[]):
    link,served=controller.tv_link(xbmc,'lib',raw,raw,'dlna')
   if result==2:self.assertTrue(served);self.assertIsNotNone(self.broker.current)
   else:self.assertIsNone(self.broker.current)

if __name__=='__main__':unittest.main()
