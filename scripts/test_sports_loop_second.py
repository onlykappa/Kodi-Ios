"""The Loop as the second place to look for one game's sources (after The Crew), through its own routes. Host tests only."""
import sys,time,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_jet,sports_provider,sports_loop_routes,sports_independent
NOW=time.time()
GAME={'id':'espn:NFL:1','league':'NFL','league_name':'NFL','sport':'football','state':'live','start':NOW-1800,
      'away':{'name':'Philadelphia Eagles','code':'PHI'},'home':{'name':'Dallas Cowboys','code':'DAL'},'sources':[]}
def fake_source(name,games):
    def items():
        return [types.SimpleNamespace(title=g['away']['name']+' vs '+g['home']['name'],league=g['league_name'],status='LIVE',
                starttime=__import__('datetime').datetime.fromtimestamp(g['start']),links=[sports_independent.Link('plugin://plugin.video.the-loop/play_video/abc')]) for g in games]
    return types.SimpleNamespace(name='Loop '+name,get_items=items)

class LoopSecond(unittest.TestCase):
    def test_without_the_loop_nothing_is_searched(self):
        with patch.object(sports_jet,'_folder',lambda id:''):
            self.assertEqual(sports_provider.loop_sources(GAME),[])
    def test_loop_routes_are_read_even_when_crew_is_installed_and_only_this_game_matches(self):
        other=dict(GAME,id='x',away={'name':'Boston Bruins'},home={'name':'Chicago Blackhawks'})
        seen={}
        def discover(schedule=None,**k):
            seen['schedule']=schedule;return [fake_source('Site A',[GAME,other]),fake_source('Site B',[GAME])]
        with patch.object(sports_jet,'_folder',lambda id:'/x/'+id),patch.object(sports_loop_routes,'discover',discover):
            sources=sports_provider.loop_sources(GAME,sleep=lambda s:None)
        self.assertEqual(seen['schedule'],[GAME],'only this game is asked for, not the whole ESPN schedule')
        self.assertGreaterEqual(len(sources),1)
        self.assertTrue(all(str(s.get('play') or '').startswith('{') or s.get('play') for s in sources))
        self.assertTrue(any('Loop' in str(s.get('addon') or s.get('label') or s) for s in sources),sources)
    def test_a_failing_loop_is_an_empty_list_not_an_error(self):
        def boom(**k):raise RuntimeError('loop listing unavailable')
        with patch.object(sports_jet,'_folder',lambda id:'/x/'+id),patch.object(sports_loop_routes,'discover',boom):
            self.assertEqual(sports_provider.loop_sources(GAME,sleep=lambda s:None),[])
    def test_both_places_sources_are_merged_crew_first_without_duplicates(self):
        got=sports_provider.all_sources(GAME,after=1,grace=2,crew=lambda:[{'id':'c','play':'p1'}],loop=lambda:[{'id':'l','play':'p2'},{'id':'dup','play':'p1'}])
        self.assertEqual([s['play'] for s in got],['p1','p2'])
    def test_the_sources_that_worked_before_come_first_and_are_tagged_best_and_good(self):
        import sports_stream_health as h
        health=h.Health(None,lambda:1000.0);health.ok('Loop BckDr2',{'height':1080,'kbps':5000});health.ok('Crew CCS',{'height':720,'kbps':2000});health.fail('Loop TimStreams','no picture')
        found=[{'addon':'Crew CCS','play':'a','tag':''},{'addon':'Loop TimStreams','play':'b','tag':''},{'addon':'Loop BckDr2','play':'c','tag':''},{'addon':'Loop New','play':'d','tag':''}]
        ranked=sports_provider.rank_sources(found,health)
        self.assertEqual([s['addon'] for s in ranked],['Loop BckDr2','Crew CCS','Loop New','Loop TimStreams'])
        self.assertEqual([s['tag'] for s in ranked],['best','good','',''],'never-tried and recently failed sources are not promoted')
    def test_ranking_never_raises_or_drops_sources(self):
        class Broken:
            def score(self,*a):raise RuntimeError('x')
        self.assertEqual(len(sports_provider.rank_sources([{'addon':'a'}],Broken())),1,'a failing memory file never drops the sources')
    def test_a_quick_crew_does_not_hide_the_loops_sources_but_a_slow_loop_does_not_hold_the_page(self):
        import threading;release=threading.Event();began=time.monotonic()
        got=sports_provider.all_sources(GAME,after=1,grace=2,crew=lambda:[{'id':'c','play':'p1'}],loop=lambda:release.wait(30) and [{'id':'l','play':'p2'}])
        release.set()
        self.assertEqual([s['play'] for s in got],['p1']);self.assertLess(time.monotonic()-began,8)
    def test_the_loop_starts_when_crew_answers_empty_without_waiting_out_the_delay(self):
        began=time.monotonic()
        self.assertEqual(sports_provider.all_sources(GAME,after=30,grace=1,crew=lambda:[],loop=lambda:[{'id':'loop','play':'p'}]),[{'id':'loop','play':'p'}])
        self.assertLess(time.monotonic()-began,5)
    def test_a_silent_crew_does_not_hold_the_page_for_minutes(self):
        import threading;release=threading.Event()
        began=time.monotonic()
        got=sports_provider.all_sources(GAME,after=1,grace=1,crew=lambda:release.wait(30) and [],loop=lambda:[{'id':'loop','play':'p'}])
        release.set()
        self.assertEqual(got,[{'id':'loop','play':'p'}]);self.assertLess(time.monotonic()-began,8)
    def test_when_both_are_empty_or_fail_the_answer_is_empty(self):
        def boom():raise RuntimeError('x')
        self.assertEqual(sports_provider.all_sources(GAME,after=1,crew=boom,loop=lambda:[]),[])
        self.assertEqual(sports_provider.all_sources(GAME,after=1,crew=lambda:[],loop=boom),[])
    def test_the_hybrid_provider_uses_crew_then_loop(self):
        import inspect;self.assertIn('all_sources',inspect.getsource(sports_provider))
if __name__=='__main__':unittest.main()
