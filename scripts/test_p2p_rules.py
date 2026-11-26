"""Peer-to-peer ranking, waiting and fallback rules (roadmap step 19): host tests with a fake player and clock."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import p2p_rules as p2p, backup_playback as bp, source_contract as c, source_health as sh
from test_direct_stream import Home,Player,Canceled,REQ

def cand(i,seeders=10,quality='1080p',size=2e9,name='Example.Film.2024.1080p.WEB'):
 h='%040x'%i;return {'provider':'local','name':name,'torrent_hash':h,'magnet':'magnet:?xt=urn:btih:'+h,'seeders':seeders,'quality':quality,'size':size}
class Clock:
 def __init__(s):s.t=0.0
 def __call__(s):return s.t
 def sleep(s,d):s.t+=d
class Multi:
 """Player stand-in: the swarm whose hash is in `alive` starts; others never move the clock."""
 def __init__(s,alive,clk):s.alive=alive;s.clk=clk;s.calls=[];s.running=False;s.t=0.0;s.stops=0;s.current=''
 def play(s,url,headers,resume=0):s.calls.append(url);s.running=True;s.t=0.0;s.current=url
 def time(s):
  if s.running and any(h in s.current for h in s.alive):s.t+=.6
  return s.t if s.running else 0.0
 def stop(s):s.stops+=1;s.running=False
def setup(alive):
 clk=Clock();player=Multi(alive,clk);pb=bp.Playback(player,clock=clk,sleep=clk.sleep);return clk,player,pb

class Rank(unittest.TestCase):
 def test_viable_and_ordering(self):
  a,b,c_,d,e=cand(1,3),cand(2,50),cand(3,1),cand(4,200,'720p'),cand(5,40,size=40e9)
  self.assertEqual([x['torrent_hash'][-1] for x in p2p.rank([a,b,c_,d,e])],['2','1','4'],'1 seeder and a 40 GB file are out; the better quality leads over more seeders')
  self.assertEqual([x['torrent_hash'][-1] for x in p2p.rank([a,d],wanted_quality='720p')],['4','1'])
 def test_a_cooling_swarm_is_left_out_and_unknown_is_kept(self):
  clk=Clock();h=sh.Health('',clk);a,b=cand(1),cand(2);h.record(p2p.key(a),c.TIMEOUT)
  self.assertEqual(p2p.rank([a,b],health=h),[b]);clk.t+=3600;self.assertEqual(len(p2p.rank([a,b],health=h)),2)
 def test_status_text_is_plain(self):
  self.assertEqual(p2p.status_text(10,90),'Waiting for peers · 80 s');self.assertNotIn('…',p2p.status_text(0,90))

class Chain(unittest.TestCase):
 def setUp(self):self.home=Home();self.patch=patch('debrid_token.has',return_value=False);self.patch.start();self.addCleanup(self.patch.stop)
 def test_the_first_swarm_that_starts_wins_and_the_prompt_is_asked_once(self):
  a,b=cand(1,60),cand(2,40);clk,pl,pb=setup([b['torrent_hash']]);asked=[];shown=[];hl=sh.Health('',clk)
  got,res=p2p.stream_best([a,b],REQ,pb,self.home,lambda:asked.append(1),health=hl,clock=clk,show=lambda text,pct=0:shown.append(text))
  self.assertEqual((got['torrent_hash'][-1],res,len(asked)),('2','playing',1));self.assertEqual(len(pl.calls),2);self.assertEqual(pl.stops,1,'the dead swarm was stopped')
  self.assertEqual((hl.state(p2p.key(a)),hl.state(p2p.key(b))),('cooldown','recent'));self.assertEqual(shown[0],'Waiting for peers · 90 s');self.assertEqual(shown[-1],'')
 def test_nothing_viable_is_empty_and_all_dead_is_a_timeout_within_the_total_bound(self):
  clk,pl,pb=setup([])
  with self.assertRaises(c.Outcome) as cm:p2p.stream_best([cand(1,1)],REQ,pb,self.home,lambda:None,clock=clk)
  self.assertEqual(cm.exception.kind,c.EMPTY)
  with self.assertRaises(c.Outcome) as cm:p2p.stream_best([cand(i,30-i) for i in range(1,6)],REQ,pb,self.home,lambda:None,clock=clk)
  self.assertEqual(cm.exception.kind,c.TIMEOUT);self.assertLessEqual(len(pl.calls),p2p.MAX_TRIES);self.assertLessEqual(clk.t,p2p.TOTAL_WAIT+p2p.FIRST_WAIT)
 def test_a_swarm_that_failed_is_not_retried_until_its_cooldown_ends(self):
  clk,pl,pb=setup([]);hl=sh.Health('',clk);cs=[cand(1,30),cand(2,20)]
  with self.assertRaises(c.Outcome):p2p.stream_best(cs,REQ,pb,self.home,lambda:None,health=hl,clock=clk)
  first=len(pl.calls)
  with self.assertRaises(c.Outcome) as cm:p2p.stream_best(cs,REQ,pb,self.home,lambda:None,health=hl,clock=clk)
  self.assertEqual((cm.exception.kind,len(pl.calls)),(c.EMPTY,first),'everything is cooling: nothing is tried again')
 def test_declined_prompt_and_cancel_never_advance(self):
  clk,pl,pb=setup([]);def_=lambda:(_ for _ in ()).throw(Canceled('no'))
  with self.assertRaises(c.Outcome) as cm:p2p.stream_best([cand(1),cand(2)],REQ,pb,self.home,def_,clock=clk)
  self.assertEqual((cm.exception.kind,pl.calls),(c.REFUSED,[]))
  clk,pl,pb=setup([])
  with self.assertRaises(c.Outcome) as cm:p2p.stream_best([cand(1),cand(2)],REQ,pb,self.home,lambda:None,cancel=lambda:True,clock=clk)
  self.assertEqual((cm.exception.kind,pl.calls),(c.CANCELED,[]))
 def test_wrong_title_candidates_are_skipped_without_penalty(self):
  clk,pl,pb=setup(['%040x'%2]);hl=sh.Health('',clk);bad=cand(1,99,name='Other.Film.2024.1080p');good=cand(2,10)
  got,_=p2p.stream_best([bad,good],REQ,pb,self.home,lambda:None,health=hl,clock=clk);self.assertEqual(got['torrent_hash'][-1],'2');self.assertEqual(hl.state(p2p.key(bad)),'unknown')

if __name__=='__main__':unittest.main()
