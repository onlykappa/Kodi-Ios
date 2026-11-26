"""Sports matching and start policy (roadmap step 10): unique current matches only; live handles expire; no link is persisted."""
import sys,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import sports_match as m, source_contract as c

NOW=1_800_000_000
def team(n,score=None):return {'name':n,'score':score}
def game(start=NOW-1800,state='live',league='EPL',away='Chelsea',home='Arsenal',gid='espn:EPL:1'):
 return {'id':gid,'league':league,'state':state,'start':start,'away':team(away,1),'home':team(home,2)}
def src(i,play='{"request":1}',q='1080p'):return {'id':i,'addon':'thecrew','quality':q,'language':'English','play':play}
def listing(start=NOW-1700,**k):
 g=game(start=start,**{x:y for x,y in k.items() if x in('league','away','home')});g['sources']=k.get('sources',[src('a'),src('b','{"request":2}','720p')]);return g
def kind(f,*a,**k):
 try:f(*a,**k)
 except c.Outcome as e:return e.kind
 return None

class Status(unittest.TestCase):
 def test_live_upcoming_and_stale(self):
  self.assertEqual(m.status(game(),NOW),'live');self.assertEqual(m.status(game(NOW+3600,'upcoming'),NOW),'upcoming')
  self.assertEqual(m.status(game(NOW-9*3600),NOW),'stale','live for over 8 h: ESPN state is stale')
  self.assertEqual(m.status(game(NOW-4*3600,'upcoming'),NOW),'stale','upcoming but started hours ago')
  self.assertEqual(m.status(game(NOW+3*86400,'upcoming'),NOW),'stale','too far ahead to attach a source')
  self.assertEqual(m.status(game(state='post'),NOW),'stale');self.assertEqual(m.status({},NOW),'stale')

class Match(unittest.TestCase):
 def test_one_unique_current_match(self):
  self.assertEqual([s['id'] for s in m.unique_match(game(),[listing()],NOW)['sources']],['a','b'])
 def test_wrong_league_teams_or_time_never_match(self):
  for l in (listing(league='UCL'),listing(away='Chelsea Women'),listing(home='Spurs'),listing(start=NOW-1800-3*3600)):
   self.assertEqual(kind(m.unique_match,game(),[l],NOW),c.EMPTY)
 def test_listing_without_sources_is_empty(self):
  self.assertEqual(kind(m.unique_match,game(),[dict(listing(),sources=[])],NOW),c.EMPTY)
 def test_ambiguous_listings_are_rejected_not_guessed(self):
  second=listing(start=NOW-1800+40*60)                      # same teams 40 minutes apart: still "the same game" by name, but another game
  self.assertEqual(kind(m.unique_match,game(),[listing(),second],NOW),c.UNSUPPORTED)
 def test_the_same_listing_seen_twice_is_merged(self):
  a=listing();b=listing(start=NOW-1700+30,sources=[src('b','{"request":2}','720p'),src('c','{"request":3}','480p')])
  self.assertEqual([s['id'] for s in m.unique_match(game(),[a,b],NOW)['sources']],['a','b','c'])
 def test_stale_game_rejects_before_matching(self):
  self.assertEqual(kind(m.unique_match,game(NOW-9*3600),[listing(NOW-9*3600)],NOW),c.UNSUPPORTED)

class Start(unittest.TestCase):
 def test_start_launches_the_first_source_and_persists_no_play_request(self):
  seen=[];rec=m.Launcher().start(game(),[listing()],NOW-10,seen.append,NOW)
  self.assertEqual(seen[0]['id'],'a');self.assertEqual(rec,{'game':'espn:EPL:1','id':'a','addon':'thecrew','quality':'1080p','language':'English'})
  self.assertNotIn('play',rec);self.assertNotIn('request',repr(rec))
 def test_chosen_source_by_id_and_unknown_id(self):
  seen=[];m.Launcher().start(game(),[listing()],NOW-10,seen.append,NOW,source_id='b');self.assertEqual(seen[0]['id'],'b')
  self.assertEqual(kind(m.Launcher().start,game(),[listing()],NOW-10,seen.append,NOW,source_id='zzz'),c.UNSUPPORTED)
 def test_expired_listing_is_not_played(self):
  seen=[];self.assertEqual(kind(m.Launcher().start,game(),[listing()],NOW-m.LIVE_TTL-1,seen.append,NOW),c.EXPIRED);self.assertEqual(seen,[])
  self.assertEqual(kind(m.Launcher().start,game(),[listing()],None,seen.append,NOW),c.EXPIRED)
 def test_cancel_and_ended_game_never_launch(self):
  seen=[];L=m.Launcher()
  self.assertEqual(kind(L.start,game(),[listing()],NOW-10,seen.append,NOW,cancel=lambda:True),c.CANCELED)
  self.assertEqual(kind(L.start,game(),[listing()],NOW-10,seen.append,NOW,current=lambda i:dict(game(),state='post')),c.UNSUPPORTED)
  self.assertEqual(kind(L.start,game(),[listing()],NOW-10,seen.append,NOW,current=lambda i:None),c.UNSUPPORTED)
  self.assertEqual(seen,[]);L.start(game(),[listing()],NOW-10,seen.append,NOW,current=lambda i:game());self.assertEqual(len(seen),1)
 def test_second_tap_while_opening_does_nothing(self):
  L=m.Launcher();seen=[];inside=threading.Event();go=threading.Event();out={}
  def slow(s):seen.append(s);inside.set();go.wait(3)
  t=threading.Thread(target=lambda:out.setdefault('r',L.start(game(),[listing()],NOW-10,slow,NOW)));t.start();inside.wait(3)
  self.assertEqual(kind(L.start,game(),[listing()],NOW-10,seen.append,NOW),c.UNSUPPORTED);go.set();t.join(3);self.assertEqual(len(seen),1)
  L.start(game(),[listing()],NOW-10,seen.append,NOW);self.assertEqual(len(seen),2,'a later tap works once the first finished')
 def test_failed_launch_releases_the_guard(self):
  L=m.Launcher()
  def boom(s):raise RuntimeError('x')
  with self.assertRaises(RuntimeError):L.start(game(),[listing()],NOW-10,boom,NOW)
  seen=[];L.start(game(),[listing()],NOW-10,seen.append,NOW);self.assertEqual(len(seen),1)

import source_health as sh
class HealthWiring(unittest.TestCase):
 def test_failed_launch_cools_its_family_and_a_cooling_family_goes_last(self):
  hl=sh.Health('',lambda:float(NOW))
  def boom(s):raise ConnectionError('https://x.invalid?token=SECRET')
  with self.assertRaises(ConnectionError):m.Launcher().start(game(),[listing()],NOW-10,boom,NOW,health=hl)
  self.assertEqual(hl.state('sports:thecrew'),'cooldown');self.assertNotIn('SECRET',repr(hl.data))
  seen=[];l=listing(sources=[src('a'),dict(src('b'),addon='Loop')]);m.Launcher().start(game(),[l],NOW-10,seen.append,NOW,health=hl);self.assertEqual(seen[0]['id'],'b')
  seen=[];m.Launcher().start(game(),[l],NOW-10,seen.append,NOW,health=hl,source_id='a');self.assertEqual(seen[0]['id'],'a','a source the person picked is not reordered')
 def test_cancel_is_not_recorded(self):
  hl=sh.Health('',lambda:float(NOW));self.assertEqual(kind(m.Launcher().start,game(),[listing()],NOW-10,lambda s:None,NOW,cancel=lambda:True,health=hl),c.CANCELED);self.assertEqual(hl.data,{})

from test_fresh_resolve import Site
import backup_playback as bp
class Player:
 def __init__(s,advance=True):s.calls=[];s.stops=0;s.t=0.0;s.advance=advance;s.running=False
 def play(s,url,headers,resume=0):s.calls.append((url,dict(headers)));s.running=True
 def time(s):
  if s.running and s.advance:s.t+=0.6
  return s.t if s.running else 0.0
 def stop(s):s.stops+=1;s.running=False
class Independent(unittest.TestCase):
 def test_independent_outcomes_feed_health(self):
  self.setUp();hl=sh.Health('',lambda:float(NOW))
  self.assertEqual(m.start_independent(game(),'a',self.pb,self.resolve,NOW,health=hl),'playing');self.assertEqual(hl.state('sports:independent'),'recent')
  self.site.mode='429';self.pb.stop();hl.record('sports:independent',c.OK)
  with self.assertRaises(c.Outcome):m.start_independent(game(),'a',bp.Playback(Player()),self.resolve,NOW,health=hl)
  self.assertEqual(hl.state('sports:independent'),'cooldown');self.tearDown()
 def setUp(self):
  self.site=Site();self.p=Player();self.pb=bp.Playback(self.p,sleep=lambda d:None)
  self.resolve=lambda address:(self.site.url(),{'X-Token':'t1'})
 def tearDown(self):self.site.srv.shutdown();self.site.srv.server_close()
 def test_controlled_game_to_advancing_playback_with_header_continuity(self):
  self.assertEqual(m.start_independent(game(),'https://embed.invalid/watch/x',self.pb,self.resolve,NOW),'playing')
  self.assertEqual(len(self.p.calls),1);self.assertEqual(self.p.calls[0][1],{'X-Token':'t1'});self.assertTrue(all(h[1]=='t1' for h in self.site.hits))
  self.assertEqual(m.start_independent(game(),'https://embed.invalid/watch/x',self.pb,self.resolve,NOW),'duplicate');self.assertEqual(len(self.p.calls),1)
 def test_stale_ended_and_cancelled_games_never_reach_the_player(self):
  for kw in (dict(g=game(NOW-9*3600)),dict(current=lambda i:dict(game(),state='post')),dict(current=lambda i:None),dict(cancel=lambda:True)):
   g=kw.pop('g',game());self.assertIn(kind(m.start_independent,g,'https://embed.invalid/x',self.pb,self.resolve,NOW,**kw),(c.UNSUPPORTED,c.CANCELED))
  self.assertEqual(self.p.calls,[]);self.assertEqual(self.site.hits,[])
 def test_resolver_failures_are_typed(self):
  def nothing(a):raise RuntimeError('no verified HLS stream available')
  def down(a):raise ConnectionError('https://x.invalid?token=SECRET')
  self.assertEqual(kind(m.start_independent,game(),'a',self.pb,nothing,NOW),c.EMPTY)
  self.assertEqual(kind(m.start_independent,game(),'a',bp.Playback(Player()),down,NOW),c.OFFLINE)
 def test_dead_playlist_is_refused_before_playing(self):
  self.site.mode='429';self.assertEqual(kind(m.start_independent,game(),'a',self.pb,self.resolve,NOW),c.REFUSED);self.assertEqual(self.p.calls,[])
 def test_no_advance_times_out_and_closes_the_player(self):
  p=Player(advance=False);clk=[0.0]
  pb=bp.Playback(p,clock=lambda:clk[0],sleep=lambda d:clk.__setitem__(0,clk[0]+d+5))
  self.assertEqual(kind(m.start_independent,game(),'a',pb,self.resolve,NOW),c.TIMEOUT);self.assertEqual(p.stops,1)

if __name__=='__main__':unittest.main()
