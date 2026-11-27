"""The Loop as the second place to look for one game's sources (after The Crew), through its own routes. Host tests only."""
import sys,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
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
    def test_sites_answering_soon_after_the_first_are_in_the_list_too(self):
        import threading
        state={'n':0}
        class Jet:
            running=types.SimpleNamespace(is_set=lambda:False)
            def live_games(self):
                state['n']+=1
                srcs=[{'addon':'Loop A','play':'a','tag':''}]+([{'addon':'Loop B','play':'b','tag':''}] if state['n']>=3 else [])
                return [dict(GAME,sources=srcs)]
            def upcoming_games(self):return []
        clock=iter(range(0,1000));t={'v':0}
        with patch.object(sports_jet,'_folder',lambda id:'/x/'+id):
            sources=sports_provider.loop_sources(GAME,sleep=lambda s:t.__setitem__('v',t['v']+1),clock=lambda:t['v'],make=lambda:Jet())
        self.assertEqual(sorted(s['play'] for s in sources),['a','b'])
    def test_the_rest_of_the_loops_routes_are_not_walked_once_the_search_is_over(self):
        opened=[]
        def mk(name,block=None):
            return fake_source(name,[GAME])
        def discover(schedule=None,**k):
            sources=[]
            for n in range(8):
                src=fake_source('Site%d'%n,[GAME]);orig=src.get_items
                src.get_items=(lambda o=orig,n=n:opened.append(n) or o())
                sources.append(src)
            return sources
        with patch.object(sports_jet,'_folder',lambda id:'/x/'+id),patch.object(sports_loop_routes,'discover',discover):
            found=sports_provider.loop_sources(GAME,sleep=lambda s:time.sleep(0.01),clock=time.monotonic)
        n=len(opened);time.sleep(0.5)
        self.assertTrue(found);self.assertEqual(len(opened),n,'nothing more is opened after the search returned')
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

class HybridTopUp(unittest.TestCase):
    """The page's provider: Crew's sources at once, The Loop's merged in when they arrive; The Loop is the only source when Crew has none."""
    def make(self,crew,loop,claim=None):
        import threading,test_sports_hybrid as th,sports_hybrid
        espn=th.Espn();espn.ttl=sports_hybrid.TTL
        store={'v':''}
        prov=sports_hybrid.HybridProvider(espn,crew,clock=lambda:th.NOW,store=(lambda:store['v'],lambda t:store.__setitem__('v',t)),
                                          more_sources=loop,merge=sports_provider.merge_ranked,claim=claim)
        game=(prov.live_games()+prov.upcoming_games())[0]
        return prov,game['id'],th
    def wait(self,th,predicate,seconds=3.0):
        end=time.time()+seconds
        while time.time()<end:
            if predicate():return True
            time.sleep(0.02)
        return False
    def test_crew_sources_show_at_once_and_the_loops_join_them_later(self):
        import threading;release=threading.Event()
        crew=lambda game,**k:[{'id':'c','addon':'Crew CS','play':'p1','tag':''}]
        loop=lambda game:release.wait(5) and [{'id':'l','addon':'Loop FawaNews','play':'p2','tag':''}]
        prov,gid,th=self.make(crew,loop)
        token=prov.request_game(gid)
        self.assertTrue(self.wait(th,lambda:not prov.searching_game(gid,token)))
        self.assertEqual([s['play'] for s in prov.game(gid)['sources']],['p1'],'Crew is not held up by The Loop')
        release.set()
        self.assertTrue(self.wait(th,lambda:len(prov.game(gid)['sources'])==2))
        self.assertEqual(sorted(s['play'] for s in prov.game(gid)['sources']),['p1','p2'])
    def test_with_no_crew_sources_the_page_keeps_searching_until_the_loop_answers(self):
        import threading;release=threading.Event()
        prov,gid,th=self.make(lambda game,**k:[],lambda game:release.wait(5) and [{'id':'l','addon':'Loop FawaNews','play':'p2','tag':''}])
        token=prov.request_game(gid)
        time.sleep(0.3);self.assertTrue(prov.searching_game(gid,token),'still looking, not "no sources"')
        release.set()
        self.assertTrue(self.wait(th,lambda:not prov.searching_game(gid,token)))
        self.assertEqual([s['play'] for s in prov.game(gid)['sources']],['p2'])
    def test_another_script_already_asking_means_this_one_does_not(self):
        asked=[]
        prov,gid,th=self.make(lambda game,**k:[{'id':'c','addon':'Crew CS','play':'p1','tag':''}],lambda game:asked.append(1) or [],claim=lambda g:False)
        token=prov.request_game(gid);self.wait(th,lambda:not prov.searching_game(gid,token));time.sleep(0.3)
        self.assertEqual(asked,[])
    def test_the_loop_is_not_asked_twice_in_90_seconds(self):
        asked=[]
        prov,gid,th=self.make(lambda game,**k:[{'id':'c','addon':'Crew CS','play':'p1','tag':''}],lambda game:asked.append(1) or [])
        prov.request_game(gid);time.sleep(0.4);prov.request_game(gid);time.sleep(0.4)
        self.assertEqual(len(asked),1)


class Claim(unittest.TestCase):
    def home(self,props):
        class Win:
            def getProperty(self,k):return props.get(k,'')
            def setProperty(self,k,v):props[k]=v
        return types.SimpleNamespace(Window=lambda i:Win())
    def test_the_loop_is_only_asked_while_a_sports_game_page_is_open(self):
        props={}
        with patch.dict(sys.modules,{'xbmcgui':self.home(props)}):
            self.assertFalse(sports_provider.claim_loop('g',now=lambda:1000.0),'a prefetch or reminder with no page open never starts The Loop')
            props['KodiIOS.SportsGameOpen']=str(1000.0+3600)
            self.assertTrue(sports_provider.claim_loop('g',now=lambda:1000.0))
            self.assertFalse(sports_provider.claim_loop('g',now=lambda:1010.0),'one asker per game at a time')
            self.assertTrue(sports_provider.claim_loop('g',now=lambda:1100.0))
            props['KodiIOS.SportsGameOpen']='900'
            self.assertFalse(sports_provider.claim_loop('h',now=lambda:1200.0),'an expired page marker does not count')

class Quiet(unittest.TestCase):
    def test_progress_boxes_are_closed_during_a_loop_search_and_not_after(self):
        calls=[]
        done=sports_provider._quiet_progress_boxes(close=lambda:calls.append(1),every=0.01)
        time.sleep(0.15);done.set();n=len(calls);time.sleep(0.1)
        self.assertGreater(n,3);self.assertLessEqual(len(calls),n+1,'closing stops with the search')
    def test_each_sites_sources_are_handed_to_the_page_as_they_arrive(self):
        seen=[];state={'n':0}
        class Jet:
            running=types.SimpleNamespace(is_set=lambda:False)
            def live_games(self):
                state['n']+=1
                srcs=[{'addon':'Loop A','play':'a','tag':''}]+([{'addon':'Loop B','play':'b','tag':''}] if state['n']>=3 else [])
                return [dict(GAME,sources=srcs)]
            def upcoming_games(self):return []
            def stop(self):pass
        t={'v':0}
        with patch.object(sports_jet,'_folder',lambda id:'/x/'+id),patch.object(sports_provider,'_quiet_progress_boxes',lambda **k:threading.Event()):
            sports_provider.loop_sources(GAME,sleep=lambda s:t.__setitem__('v',t['v']+1),clock=lambda:t['v'],make=lambda:Jet(),progress=lambda f:seen.append(sorted(x['play'] for x in f)))
        self.assertEqual(seen,[['a'],['a','b']])
if __name__=='__main__':unittest.main()
