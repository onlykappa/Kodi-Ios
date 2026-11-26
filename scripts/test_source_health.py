"""Source health (roadmap step 11): cooldowns, expiry, deliberate retry, no penalty for cancel, no starvation, nothing sensitive stored."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import source_health as h, source_contract as c, provider_fallback as f, independent_sites as sites
from test_independent_sites import Fetch,pages,MOVIE
from test_provider_fallback import Transport

class Clock:
 def __init__(s,t=1_000_000.0):s.t=t
 def __call__(s):return s.t

class Unit(unittest.TestCase):
 def setUp(self):self.clk=Clock();self.h=h.Health('',self.clk)
 def test_unknown_is_not_healthy_and_stays_eligible(self):
  self.assertEqual(self.h.state('pov'),'unknown');self.assertEqual(self.h.order(['pov','prism']),['pov','prism'])
 def test_failure_cools_down_grows_and_expires(self):
  self.h.record('pov',c.OFFLINE);self.assertEqual(self.h.state('pov'),'cooldown');self.clk.t+=121;self.assertEqual(self.h.state('pov'),'unknown')
  self.h.record('pov',c.OFFLINE);self.clk.t+=121;self.assertEqual(self.h.state('pov'),'cooldown','the second failure cools for 10 minutes')
  self.clk.t+=600;self.assertEqual(self.h.state('pov'),'unknown')
 def test_refusal_cools_longest_and_layout_change_longer(self):
  self.h.record('a',c.REFUSED);self.h.record('b',c.OFFLINE);self.h.record('c',c.UNSUPPORTED);self.clk.t+=130
  self.assertEqual((self.h.state('a'),self.h.state('b'),self.h.state('c')),('cooldown','unknown','cooldown'))
 def test_cancel_empty_expired_never_penalise(self):
  for o in (c.CANCELED,c.EMPTY,c.EXPIRED,'nonsense'):self.h.record('pov',o)
  self.assertEqual(self.h.state('pov'),'unknown');self.assertEqual(self.h.data.get('pov',{}).get('fails',0),0)
 def test_success_clears_cooldown_and_orders_first_by_recency(self):
  self.h.record('a',c.OFFLINE);self.h.record('b',c.OK);self.clk.t+=10;self.h.record('c',c.OK);self.h.record('a',c.OK)
  self.assertEqual(self.h.state('a'),'recent');self.assertEqual(self.h.order(['x','a','b','c','y']),['a','c','b','x','y'])
  self.clk.t+=h.RECENT+1;self.assertEqual(self.h.state('b'),'unknown');self.assertEqual(self.h.order(['x','b']),['x','b'])
 def test_cooling_sources_are_skipped_unless_asked_again(self):
  self.h.record('a',c.REFUSED);self.assertEqual(self.h.order(['a','b']),['b']);self.assertEqual(self.h.order(['a','b'],retry=('a',)),['a','b'])
  self.h.retry('a');self.assertEqual(self.h.state('a'),'unknown');self.h.record('a',c.REFUSED);self.assertEqual(self.h.data['a']['fails'],2)

class Store(unittest.TestCase):
 def test_persists_bounded_and_holds_no_links(self):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);path=str(Path(d.name)/'x'/h.NAME);clk=Clock();a=h.Health(path,clk)
  a.record('pov',c.REFUSED);b=h.Health(path,clk);self.assertEqual(b.state('pov'),'cooldown')
  text=Path(path).read_text();self.assertNotIn('http',text);self.assertEqual(set(json.loads(text)['pov']),{'failed','fails','kind','until'})
  for i in range(h.MAX_ENTRIES+10):clk.t+=1;a.record('s%d'%i,c.OK)
  self.assertLessEqual(len(json.loads(Path(path).read_text())),h.MAX_ENTRIES)
  clk.t+=h.KEEP+10;a.record('fresh',c.OK);self.assertEqual(list(json.loads(Path(path).read_text())),['fresh'],'old entries expire')
 def test_damaged_file_or_no_profile_is_harmless(self):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);p=Path(d.name)/h.NAME;p.write_text('{not json');self.assertEqual(h.Health(str(p)).data,{})
  p.write_text('[1,2]');self.assertEqual(h.Health(str(p)).data,{});x=h.Health('');x.record('a',c.OK);self.assertEqual(x.state('a'),'recent')

REQ={'media_type':'movie','title':'Example Film','year':2024,'quality':'1080p','profile':{}}
SRC={'name':'Example.Film.2024.1080p.WEB-DL.mkv','quality':'1080p','url':'https://fixture.invalid/m.mkv','size':1,'seeders':0}
class Chain(unittest.TestCase):
 def setUp(self):self.clk=Clock();self.h=h.Health('',self.clk)
 def test_dead_provider_cannot_starve_the_next_and_is_skipped_until_cooldown_ends(self):
  t=Transport({'jacktook':TimeoutError(),'pov':[SRC]});found=f.search(REQ,transport=t,health=self.h)
  self.assertEqual((found[0]['provider'],t.calls),('pov',['jacktook','pov']));self.assertEqual(self.h.state('jacktook'),'cooldown')
  t2=Transport({'jacktook':TimeoutError(),'pov':[SRC]});f.search(REQ,transport=t2,health=self.h);self.assertEqual(t2.calls,['pov'],'no repeated scan of a cooling source')
  self.clk.t+=200;t3=Transport({'jacktook':TimeoutError(),'pov':[SRC]});f.search(REQ,transport=t3,health=self.h);self.assertEqual(t3.calls,['pov'],'the recent winner goes first and wins');self.assertEqual(self.h.state('jacktook'),'unknown','its cooldown has ended: eligible again, not called healthy')
 def test_recent_success_goes_first_but_untested_are_not_called_healthy(self):
  self.h.record('prism',c.OK);t=Transport({'jacktook':[SRC],'prism':[SRC]});f.search(REQ,transport=t,health=self.h);self.assertEqual(t.calls,['prism'])
  self.assertEqual(self.h.state('jacktook'),'unknown')
 def test_cancel_is_not_recorded_and_does_not_advance(self):
  t=Transport({'jacktook':f.Canceled('stop'),'pov':[SRC]})
  with self.assertRaises(f.Canceled):f.search(REQ,transport=t,health=self.h)
  self.assertEqual(t.calls,['jacktook']);self.assertEqual(self.h.state('jacktook'),'unknown');self.assertEqual(self.h.data,{})
 def test_empty_answer_costs_nothing(self):
  t=Transport({'jacktook':[],'pov':[SRC]});f.search(REQ,transport=t,health=self.h);self.assertEqual(self.h.state('jacktook'),'unknown')
 def test_site_search_skips_a_refused_site_and_others_still_answer(self):
  p=pages();import test_independent_sites as ti
  fx=Fetch(p);sites.search_all(MOVIE,fetch=fx,health=self.h)
  p2=pages();p2['https://apibay.org']=Exception('x');p2['https://apibay.org']=type('E',(Exception,),{'code':429})()
  self.h=h.Health('',self.clk);fx2=Fetch(p2);out,found,rep=sites.search_all(MOVIE,fetch=fx2,health=self.h)
  self.assertEqual(rep['apibay'],c.REFUSED);self.assertEqual(self.h.state('apibay'),'cooldown');self.assertTrue(found)
  fx3=Fetch(pages());out,found,rep=sites.search_all(MOVIE,fetch=fx3,health=self.h)
  self.assertFalse(any(u.startswith('https://apibay.org') for u in fx3.calls),'a refused site is not asked again during its cooldown');self.assertNotIn('apibay',rep);self.assertTrue(found)

if __name__=='__main__':unittest.main()
