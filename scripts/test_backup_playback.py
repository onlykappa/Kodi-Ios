"""Backup playback (roadmap step 7): controlled HLS server, fake player, torrent hash checks. Host tests; no iOS engine or receiver."""
import hashlib,sys,threading,types,unittest,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import backup_playback as b, source_contract as c
from test_fresh_resolve import Site,Transport,CAND,MOVIE

class Player:
 def __init__(s,advance=True):s.calls=[];s.stops=0;s.t=0.0;s.advance=advance;s.running=False
 def play(s,url,headers,resume=0):s.calls.append((url,dict(headers),resume));s.running=True
 def time(s):
  if s.running and s.advance:s.t+=0.6
  return s.t if s.running else 0.0
 def stop(s):s.stops+=1;s.running=False
class Clock:
 def __init__(s):s.t=0.0
 def __call__(s):return s.t
 def sleep(s,d):s.t+=d

def pb(player,route=None):
 clk=Clock();return b.Playback(player,route,clock=clk,sleep=clk.sleep)

class Direct(unittest.TestCase):
 def setUp(self):self.site=Site();self.tr=Transport(self.site)
 def tearDown(self):self.site.srv.shutdown();self.site.srv.server_close()
 def test_hls_starts_and_time_advances(self):
  p=Player();play=pb(p);self.assertEqual(play.start(CAND,MOVIE,self.tr,resume=42),'playing')
  self.assertEqual(len(p.calls),1);url,headers,resume=p.calls[0]
  self.assertTrue(url.startswith('http://127.0.0.1:') and url.endswith('.m3u8') and url!=self.site.url(),'guarded HLS goes through the local proxy (ISSUE-489)');self.assertEqual((headers,resume),({},42));self.assertGreaterEqual(p.t,b.ADVANCE)
  self.assertTrue(all(h[1]=='t1' for h in self.site.hits));play.stop()
 def test_no_time_advance_times_out_and_stops_player(self):
  p=Player(advance=False);play=pb(p)
  with self.assertRaises(c.Outcome) as cm:play.start(CAND,MOVIE,self.tr)
  self.assertEqual(cm.exception.kind,c.TIMEOUT);self.assertEqual(p.stops,1);self.assertIsNone(play.current)
 def test_cancel_while_resolving_never_starts_the_player(self):
  p=Player();state={'n':0}
  def cancel():state['n']+=1;return len(self.site.hits)>=1      # becomes true once the chain check has begun
  with self.assertRaises(c.Outcome) as cm:pb(p).start(CAND,MOVIE,self.tr,cancel=cancel)
  self.assertEqual(cm.exception.kind,c.CANCELED);self.assertEqual(p.calls,[]);self.assertEqual(p.stops,0)
 def test_stop_from_another_thread_during_the_wait_closes_the_player(self):
  p=Player(advance=False);play=pb(p);play.sleep=lambda d:(play.stop() if p.running else None)
  with self.assertRaises(c.Outcome) as cm:play.start(CAND,MOVIE,self.tr)
  self.assertEqual(cm.exception.kind,c.CANCELED);self.assertEqual(p.stops,1);self.assertEqual(len(p.calls),1)
 def test_stop_while_resolving_prevents_a_late_start(self):
  p=Player();play=pb(p);orig=self.tr.resolve
  def slow(*a):play.stop();return orig(*a)
  self.tr.resolve=slow
  with self.assertRaises(c.Outcome) as cm:play.start(CAND,MOVIE,self.tr)
  self.assertEqual(cm.exception.kind,c.CANCELED);self.assertEqual(p.calls,[])
 def test_same_request_twice_is_one_player_and_other_request_replaces_it(self):
  p=Player(advance=False);play=pb(p);started=threading.Event();go=threading.Event()
  play.sleep=lambda d:(started.set(),go.wait(2))
  out={};t=threading.Thread(target=lambda:out.setdefault('r',self._try(play)));t.start();started.wait(2)
  self.assertEqual(play.start(CAND,MOVIE,self.tr),'duplicate');self.assertEqual(len(p.calls),1)
  other=dict(MOVIE,title='Another Film')
  with self.assertRaises(c.Outcome):play.start(dict(CAND,name='Another.Film.2024.1080p.WEB'),dict(other,title='Another Film'),self.tr,cancel=lambda:True)
  self.assertGreaterEqual(p.stops,1);go.set();t.join(5)
 def _try(self,play):
  try:return play.start(CAND,MOVIE,self.tr)
  except c.Outcome as e:return e.kind
 def test_wrong_title_never_plays(self):
  p=Player()
  with self.assertRaises(c.Outcome):pb(p).start(dict(CAND,name='Other.Film.2024.1080p'),MOVIE,self.tr)
  self.assertEqual(p.calls,[]);self.assertEqual(self.tr.calls,0)
 def test_unroutable_candidate_is_unsupported(self):
  with self.assertRaises(c.Outcome) as cm:pb(Player()).start({'provider':'jacktook','name':'Example.Film.2024.1080p'},MOVIE,self.tr)
  self.assertEqual(cm.exception.kind,c.UNSUPPORTED)

def torrent_bytes(name=b'file.mkv'):
 info=b'd6:lengthi5e4:name%d:%s12:piece lengthi16384e6:pieces20:%se'%(len(name),name,b'x'*20)
 return b'd8:announce3:udp4:info'+info+b'e',hashlib.sha1(info).hexdigest()
HASH='a'*40
MAG={'provider':'jacktook','name':'Example.Film.2024.1080p.WEB','torrent_hash':HASH,'magnet':'magnet:?xt=urn:btih:'+HASH,'size':1,'seeders':5}
class Torrent(unittest.TestCase):
 def route(self,answer=True):
  calls=[];return calls,(lambda m,r:(calls.append((m,r.get('purpose'))),answer)[1])
 def test_hash_matches_magnet_file_and_base32(self):
  data,h=torrent_bytes();self.assertEqual(b.torrent_file_hash(data),h)
  self.assertEqual(b.verify_torrent(dict(MAG,torrent_hash=h,magnet='magnet:?xt=urn:btih:'+h),data),h)
  b32=base64.b32encode(bytes.fromhex(h)).decode();self.assertEqual(b.magnet_hash('magnet:?xt=urn:btih:'+b32),h)
 def test_mismatches_are_unsupported(self):
  data,h=torrent_bytes()
  for cand,file in ((dict(MAG,magnet='magnet:?xt=urn:btih:'+'b'*40),None),(MAG,data),({'name':'x'},None)):
   with self.assertRaises(c.Outcome) as cm:b.verify_torrent(cand,file)
   self.assertEqual(cm.exception.kind,c.UNSUPPORTED)
  with self.assertRaises(c.Outcome):b.verify_torrent(MAG,b'not a torrent')
 def test_download_goes_to_the_existing_route_once(self):
  calls,route=self.route();r=pb(Player(),route).start(MAG,dict(MOVIE,purpose='download'),None)
  self.assertEqual(r,'sent');self.assertEqual(calls,[('magnet:?xt=urn:btih:'+HASH,'download')])
 def test_stream_never_becomes_a_download(self):
  calls,route=self.route()
  with self.assertRaises(c.Outcome) as cm:pb(Player(),route).start(MAG,dict(MOVIE,purpose='stream'),None)
  self.assertEqual((cm.exception.kind,calls),(c.UNSUPPORTED,[]))
 def test_declined_route_is_refused_and_cancel_sends_nothing(self):
  calls,route=self.route(False)
  with self.assertRaises(c.Outcome) as cm:pb(Player(),route).start(MAG,dict(MOVIE,purpose='download'),None)
  self.assertEqual(cm.exception.kind,c.REFUSED)
  calls,route=self.route()
  with self.assertRaises(c.Outcome) as cm:pb(Player(),route).start(MAG,dict(MOVIE,purpose='download'),None,cancel=lambda:True)
  self.assertEqual((cm.exception.kind,calls),(c.CANCELED,[]))
 def test_wrong_title_torrent_is_not_sent(self):
  calls,route=self.route()
  with self.assertRaises(c.Outcome):pb(Player(),route).start(dict(MAG,name='Other.Film.2024.1080p'),dict(MOVIE,purpose='download'),None)
  self.assertEqual(calls,[])
 def test_no_route_configured_sends_nothing(self):
  with self.assertRaises(c.Outcome):pb(Player(),None).start(MAG,dict(MOVIE,purpose='download'),None)

class Kodi(unittest.TestCase):
 def test_kodi_player_headers_and_resume(self):
  seen={}
  class P:
   def play(s,target,item):seen['t']=target;seen['i']=item
   def isPlaying(s):return True
   def getTime(s):return 3.5
   def stop(s):seen['stop']=True
  class Item:
   def __init__(s,path=''):s.p={};s.path=path
   def setProperty(s,k,v):s.p[k]=v
  sys.modules['xbmc']=types.SimpleNamespace(Player=P);sys.modules['xbmcgui']=types.SimpleNamespace(ListItem=Item)
  try:
   k=b.KodiPlayer();k.play('https://a.invalid/m.m3u8',{'X-Token':'1'},30);k.stop()
   self.assertEqual(seen['t'],'https://a.invalid/m.m3u8|X-Token=1');self.assertEqual(seen['i'].p,{'StartOffset':'30.0'});self.assertEqual(k.time(),3.5);self.assertTrue(seen['stop'])
  finally:sys.modules.pop('xbmc',None);sys.modules.pop('xbmcgui',None)

if __name__=='__main__':unittest.main()
