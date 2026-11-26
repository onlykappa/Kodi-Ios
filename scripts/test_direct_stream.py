"""Peer-to-peer stream route (roadmap step 18): host tests with a fake player and prompt. The iOS engine, real swarms and a VPN are not involved."""
import json,sys,unittest,urllib.parse
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import direct_stream as ds, backup_playback as bp, source_contract as c, source_health as sh, alldebrid as ad, debrid_account as da

HASH='a'*40
REQ={'media_type':'movie','title':'Example Film','year':2024,'profile':{}}
CAND={'provider':'local','name':'Example.Film.2024.1080p.WEB','torrent_hash':HASH,'magnet':'magnet:?xt=urn:btih:'+HASH,'size':1,'seeders':9}
class Home:
 def __init__(s):s.p={}
 def getProperty(s,k):return s.p.get(k,'')
 def setProperty(s,k,v):s.p[k]=v
 def clearProperty(s,k):s.p.pop(k,None)
class Player:
 def __init__(s,advance=True):s.calls=[];s.stops=0;s.t=0.0;s.advance=advance;s.running=False;s.home=None;s.seen_grant=None
 def play(s,url,headers,resume=0):
  s.calls.append((url,dict(headers)));s.running=True
  if s.home is not None:s.seen_grant=s.home.getProperty(ds.PROPERTY)
 def time(s):
  if s.running and s.advance:s.t+=.6
  return s.t if s.running else 0.0
 def stop(s):s.stops+=1;s.running=False
class Canceled(Exception):pass
def down(clock):
 h=sh.Health('',clock)
 for i in range(3):h.record('debrid',c.OFFLINE);clock.t+=1
 return h
class Clock:
 def __init__(s,t=1000.0):s.t=t
 def __call__(s):return s.t
def pb(player,clk=None):
 t=[0.0]
 return bp.Playback(player,clock=lambda:t[0],sleep=lambda d:t.__setitem__(0,t[0]+d))

class Grant(unittest.TestCase):
 def test_one_use_short_life_exact_hash(self):
  h=Home();ds.grant(h,HASH,100);self.assertFalse(ds.consume(h,'b'*40,101));self.assertEqual(h.p,{},'a wrong hash also spends it')
  ds.grant(h,HASH,100);self.assertTrue(ds.consume(h,HASH.upper(),101));self.assertFalse(ds.consume(h,HASH,101))
  ds.grant(h,HASH,100);self.assertFalse(ds.consume(h,HASH,100+ds.GRANT_TTL+1))
  self.assertFalse(ds.consume(None,HASH));h.p[ds.PROPERTY]='not json';self.assertFalse(ds.consume(h,HASH))

class Plan(unittest.TestCase):
 def test_only_verified_torrents_and_only_when_debrid_is_not_the_better_route(self):
  clk=Clock();health=sh.Health('',clk)
  with patch('debrid_token.has',return_value=True):
   with self.assertRaises(c.Outcome) as cm:ds.plan(CAND,REQ,health);self.assertEqual(cm.exception.kind,c.UNSUPPORTED)
   self.assertEqual(ds.plan(CAND,REQ,health,force=True),HASH)
   self.assertEqual(ds.plan(CAND,REQ,down(clk)),HASH)
  with patch('debrid_token.has',return_value=False):self.assertEqual(ds.plan(CAND,REQ,health),HASH,'no debrid key at all')
 def test_wrong_things_never_stream(self):
  with patch('debrid_token.has',return_value=False):
   for cand in (dict(CAND,name='Other.Film.2024.1080p'),dict(CAND,magnet='magnet:?xt=urn:btih:'+'b'*40),{'name':'Example.Film.2024','url':'https://x.invalid/a.mp4','provider':'local'},dict(CAND,seeders=0)):
    with self.assertRaises(c.Outcome):ds.plan(cand,REQ,None)

class Stream(unittest.TestCase):
 def setUp(self):self.home=Home();self.p=Player();self.p.home=self.home;self.patch=patch('debrid_token.has',return_value=False);self.patch.start();self.addCleanup(self.patch.stop)
 def test_approved_stream_hands_elementums_play_url_to_the_player_with_a_one_time_grant(self):
  asked=[];r=ds.stream(CAND,REQ,pb(self.p),self.home,lambda:asked.append(1))
  self.assertEqual((r,asked),('playing',[1]));url=self.p.calls[0][0]
  self.assertTrue(url.startswith('plugin://plugin.video.elementum/play?uri='));self.assertEqual(urllib.parse.unquote(url.split('uri=')[1]),'magnet:?xt=urn:btih:'+HASH)
  self.assertEqual(json.loads(self.p.seen_grant)['hash'],HASH,'the grant exists when the player starts');self.assertTrue(ds.consume(self.home,HASH),'and is still unspent')
  self.assertFalse(ds.consume(self.home,HASH))
 def test_declined_prompt_starts_nothing(self):
  def no():raise Canceled('declined')
  with self.assertRaises(c.Outcome) as cm:ds.stream(CAND,REQ,pb(self.p),self.home,no)
  self.assertEqual(cm.exception.kind,c.REFUSED);self.assertEqual((self.p.calls,self.home.p),([],{}))
 def test_cancel_after_the_prompt_starts_nothing(self):
  with self.assertRaises(c.Outcome) as cm:ds.stream(CAND,REQ,pb(self.p),self.home,lambda:None,cancel=lambda:True)
  self.assertEqual((cm.exception.kind,self.p.calls,self.home.p),(c.CANCELED,[],{}))
 def test_no_peers_times_out_revokes_the_grant_and_stops_the_player(self):
  p=Player(advance=False);p.home=self.home
  with self.assertRaises(c.Outcome) as cm:ds.stream(CAND,REQ,pb(p),self.home,lambda:None,wait=30)
  self.assertEqual(cm.exception.kind,c.TIMEOUT);self.assertEqual((p.stops,self.home.p),(1,{}))
 def test_the_wait_is_longer_than_a_direct_link_gets(self):
  self.assertGreater(ds.WAIT,bp.START_SECONDS)
 def test_stream_is_not_a_download_and_debrid_ok_means_no_direct_route(self):
  with patch('debrid_token.has',return_value=True):
   with self.assertRaises(c.Outcome):ds.stream(CAND,REQ,pb(self.p),self.home,lambda:None)
  self.assertEqual(self.p.calls,[]);self.assertEqual(ds.stream(CAND,REQ,pb(self.p),self.home,lambda:None,force=True),'playing')
 def test_same_torrent_twice_is_one_session(self):
  p=Player(advance=False);p.home=self.home;play=pb(p);started=[]
  import threading
  clk=[0.0]
  def slow(d):
   started.append(1)
   if len(started)==1:
    self.assertEqual(ds.stream(CAND,REQ,play,self.home,lambda:None,force=True),'duplicate')
   clk[0]+=d
  play.sleep=slow;play.clock=lambda:clk[0]
  with self.assertRaises(c.Outcome):ds.stream(CAND,REQ,play,self.home,lambda:None,force=True,wait=3)
  self.assertEqual(len(p.calls),1)

class Route(unittest.TestCase):
 def test_elementum_cloud_lets_exactly_the_approved_torrent_through(self):
  mods={m:MagicMock() for m in ('xbmcaddon','xbmcvfs','debrid_drive','drivelibrary','notices')}
  home=Home();gui=MagicMock();gui.Window.return_value=home;mods['xbmcgui']=gui
  import elementum_cloud as cloud
  url='plugin://plugin.video.elementum/play?uri='+urllib.parse.quote('magnet:?xt=urn:btih:'+HASH,safe='')
  with patch.dict(sys.modules,mods),patch('debrid_token.has',return_value=False):
   ds.grant(home,HASH);self.assertFalse(cloud.route(url),'approved: Elementum plays it itself')
   self.assertEqual(home.p,{});self.assertTrue(cloud.route(url),'second time: back to the debrid route (which refuses without a key)')
   ds.grant(home,'b'*40);self.assertTrue(cloud.route(url),'a grant for another torrent changes nothing')

class Hook(unittest.TestCase):
 def test_dispatch_streams_a_magnet_from_peers_only_when_debrid_is_marked_unavailable(self):
  import provider_fallback_hooks as hooks,types
  sel={'candidate':CAND,'url':'magnet:?xt=urn:btih:'+HASH,'request':dict(REQ,purpose='stream')}
  import debrid_token,debrid_account
  with patch.object(debrid_token,'has',return_value=True),patch.object(debrid_account,'is_unavailable',return_value=False):
   self.assertFalse(hooks.direct_wanted(),'a working key keeps the old refusal')
   with patch.dict(sys.modules,{'xbmc':MagicMock()}):
    with self.assertRaises(ValueError):hooks.dispatch(sel,cancel=lambda:False)
  with patch.object(debrid_token,'has',return_value=False):
   self.assertTrue(hooks.direct_wanted(),'no debrid key at all: peers are the way')
  with patch.object(debrid_token,'has',return_value=True),patch.object(debrid_account,'is_unavailable',return_value=True):
   self.assertTrue(hooks.direct_wanted())
  calls=[]
  fake_direct=types.SimpleNamespace(stream=lambda *a,**k:calls.append(k.get('health')) or 'playing')
  mods={'xbmc':MagicMock(),'xbmcgui':MagicMock(),'elementum_download':types.SimpleNamespace(_torrent_gate=lambda:None,Canceled=Canceled),'p2p_rules':types.SimpleNamespace(stream_best=lambda *a,**k:calls.append(k.get('health')) or (CAND,'playing'),STATUS='s'),'backup_playback':MagicMock()}
  with patch.object(hooks,'direct_wanted',return_value=True),patch.dict(sys.modules,mods):
   self.assertTrue(hooks.dispatch(sel,cancel=lambda:False))
  self.assertEqual(len(calls),1)
  def refuse(*a,**k):raise c.Outcome(c.REFUSED)
  mods['p2p_rules']=types.SimpleNamespace(stream_best=refuse,STATUS='s')
  with patch.object(hooks,'direct_wanted',return_value=True),patch.dict(sys.modules,mods):
   self.assertFalse(hooks.dispatch(sel,cancel=lambda:False))

if __name__=='__main__':unittest.main()
