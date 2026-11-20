"""Sources for live games are looked for before anyone presses check (owner, 2026-11-20)."""
import sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_sources_prefetch as pf

class Provider:
    def __init__(self,games):
        self.games={g['id']:g for g in games};self.asked=[];self.searching={};self.cancelled=[]
    def live_games(self,league=None):return [dict(g) for g in self.games.values() if g['state']=='live']
    def request_game(self,gid):
        self.asked.append(gid);token='t%d'%len(self.asked);self.searching[token]=2   # two polls, then done
        return token
    def searching_game(self,gid,token):
        left=self.searching.get(token,0)
        if left>0:self.searching[token]=left-1
        return left>0
    def cancel_game_search(self,token):self.cancelled.append(token)
    def game(self,gid):return self.games[gid]

def game(gid,start,sources=()):return {'id':gid,'state':'live','start':start,'league':'BUN','sources':list(sources)}

class Prefetch(unittest.TestCase):
    def make(self,games,busy=lambda:False):
        self.provider=Provider(games);self.now=[1000.0];self.logs=[]
        return pf.Prefetch(lambda:self.provider,busy,self.logs.append,clock=lambda:self.now[0],sleep=lambda s:self.now.__setitem__(0,self.now[0]+s))
    def test_the_soonest_live_game_without_a_source_is_searched_first_one_at_a_time(self):
        p=self.make([game('b',200),game('a',100),game('c',50,sources=['x'])])
        self.assertEqual(p.tick(),'a');self.assertEqual(self.provider.asked,['a'])   # one search per look, c already has a source
        self.assertEqual(p.tick(),'b')
        self.assertIsNone(p.tick())                                                   # a and b tried: nothing more to do now
    def test_a_game_with_no_source_is_tried_again_after_the_retry_time_not_before(self):
        p=self.make([game('a',100)])
        p.tick();self.now[0]+=pf.RETRY-5;self.assertIsNone(p.tick())
        self.now[0]+=10;self.assertEqual(p.tick(),'a');self.assertEqual(self.provider.asked,['a','a'])
    def test_it_stays_out_of_the_way_while_a_video_plays_or_a_game_page_searches(self):
        p=self.make([game('a',100)],busy=lambda:True)
        self.assertIsNone(p.tick());self.assertEqual(self.provider.asked,[])
    def test_a_finished_game_is_forgotten_and_a_search_that_never_ends_is_cancelled(self):
        p=self.make([game('a',100)]);p.tick();self.assertIn('a',p.attempts)
        self.provider.games['a']['state']='post';p.tick();self.assertNotIn('a',p.attempts)
        q=self.make([game('z',1)])
        self.provider.searching_game=lambda gid,token:True   # never done
        q.tick();self.assertEqual(self.provider.cancelled,['t1'])
    def test_sources_found_are_logged(self):
        p=self.make([game('a',100,sources=[])])
        orig=self.provider.game;self.provider.game=lambda gid:dict(orig(gid),sources=['s1','s2'])
        p.tick();self.assertTrue(any('2 source(s) ready' in line for line in self.logs))
    def test_an_unreachable_provider_is_not_fatal(self):
        p=self.make([])
        p.get_provider=lambda:type('P',(),{'live_games':lambda s,league=None:(_ for _ in ()).throw(RuntimeError('x'))})()
        self.assertIsNone(p.tick())

class Watch(unittest.TestCase):
    """A Sports page opened pokes the loop: the look happens at once, not at the next minute (owner, build 618)."""
    def run_watch(self,pokes,seconds):
        ticks=[];clock={'n':0}
        class Provider:
            def live_games(self,league=None):ticks.append(clock['n']);return []
        def wait(step):
            clock['n']+=step;return clock['n']>seconds
        poked=iter(pokes)
        pf.watch(lambda:Provider(),lambda:False,wait,every=60,first=20,poke=lambda:next(poked,False))
        return ticks
    def test_without_a_poke_it_looks_after_the_first_wait_and_then_every_minute(self):
        self.assertEqual(self.run_watch([],140)[:3],[20,80,140])
    def test_a_poke_looks_at_once(self):
        self.assertEqual(self.run_watch([False,False,True],10)[0],3)

if __name__=='__main__':unittest.main()
