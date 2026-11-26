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
    def test_all_sources_crew_wins_and_the_loop_is_not_asked_when_crew_answers_quickly(self):
        called=[]
        self.assertEqual(sports_provider.all_sources(GAME,after=2,crew=lambda:[{'id':'crew'}],loop=lambda:called.append(1) or [{'id':'loop'}]),[{'id':'crew'}])
        self.assertEqual(called,[])
    def test_the_loop_starts_when_crew_answers_empty_without_waiting_out_the_delay(self):
        began=time.monotonic()
        self.assertEqual(sports_provider.all_sources(GAME,after=30,crew=lambda:[],loop=lambda:[{'id':'loop'}]),[{'id':'loop'}])
        self.assertLess(time.monotonic()-began,5)
    def test_a_silent_crew_does_not_hold_the_page_for_minutes(self):
        import threading;release=threading.Event()
        began=time.monotonic()
        got=sports_provider.all_sources(GAME,after=1,crew=lambda:release.wait(30) and [],loop=lambda:[{'id':'loop'}])
        release.set()
        self.assertEqual(got,[{'id':'loop'}]);self.assertLess(time.monotonic()-began,8)
    def test_when_both_are_empty_or_fail_the_answer_is_empty(self):
        def boom():raise RuntimeError('x')
        self.assertEqual(sports_provider.all_sources(GAME,after=1,crew=boom,loop=lambda:[]),[])
        self.assertEqual(sports_provider.all_sources(GAME,after=1,crew=lambda:[],loop=boom),[])
    def test_the_hybrid_provider_uses_crew_then_loop(self):
        import inspect;self.assertIn('all_sources',inspect.getsource(sports_provider))
if __name__=='__main__':unittest.main()
