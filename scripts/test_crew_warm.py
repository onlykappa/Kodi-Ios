"""A game page lists Crew's folder when it opens, so the tap does not (owner, build 639 log fd1d028c: Crew's folders were listed twice, 0.95 s and 1.76 s, after every tap)."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'))
import sports_crew_routes as crew

ROOT='plugin://plugin.video.thecrew/'
GAME={'away':{'name':'Alpha'},'home':{'name':'Beta'},'league_name':'NBA','state':'live','start':1000}
FRESH=ROOT+'?action=play&url=%24doregex%5Bmakelist2%5D%7Cregex%3Dfresh&content=0'
ROOT_ROUTE=ROOT+'?action=nba';PARENT=ROOT+'?action=xdirectory&url=parent'

def entry(label,route,folder=True):
    return {'label':label,'file':ROOT+route,'filetype':'directory' if folder else 'file'}

class Warm(unittest.TestCase):
    def setUp(self):
        crew._WARM.clear();self.calls=[]
        def fake(path,session=None,playback=False):
            self.calls.append(path)
            return [entry('Alpha vs Beta',FRESH.removeprefix(ROOT),False)] if path==PARENT else [entry('NBA LIVE (CS)','?action=xdirectory&url=parent')]
        self.patch=patch.object(crew,'_listing',fake);self.patch.start();self.addCleanup(self.patch.stop)
    def link(self):
        return crew.CrewLink(ROOT+'?action=play&url=old',[{'address':ROOT_ROUTE,'label':'Crew NBA'},{'address':PARENT,'label':'NBA LIVE (CS)'}],GAME).to_dict()
    def test_a_tap_after_the_page_warmed_it_lists_nothing(self):
        link=self.link()
        self.assertTrue(crew.warm(link));self.assertEqual(self.calls,[PARENT])
        self.assertEqual(crew.refresh_link(link),FRESH);self.assertEqual(self.calls,[PARENT])   # no folder listed at the tap
    def test_another_crew_listing_in_between_means_the_tap_lists_again(self):
        link=self.link();crew.warm(link)
        crew.listing(ROOT+'?action=other')   # a prefetch or another game's page: Crew's link rules may be gone
        self.assertEqual(crew.refresh_link(link),FRESH);self.assertEqual(self.calls,[PARENT,ROOT+'?action=other',PARENT])
    def test_an_old_warm_answer_is_not_trusted(self):
        link=self.link();crew.warm(link)
        route=link['address'];found,gen,at=crew._WARM[route];crew._WARM[route]=(found,gen,at-crew.WARM_FOR-1)
        crew.refresh_link(link);self.assertEqual(self.calls,[PARENT,PARENT])
    def test_warming_never_raises(self):
        def boom(*a,**k):raise RuntimeError('Crew gone')
        with patch.object(crew,'_listing',boom):self.assertFalse(crew.warm(self.link()))
        self.assertFalse(crew.warm({'address':'https://not-a-crew-route'}))
    def test_the_game_page_warms_the_best_crew_source_once(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/sports_game.py').read_text()
        self.assertIn('warm_best(',text);self.assertIn('self._warmed',text)
    def test_warm_best_only_warms_a_crew_source_and_never_raises(self):
        import json,sports_game
        crewsrc={'addon':'Crew','quality':'','play':json.dumps({'e':'TheCrewRoute','l':{'address':ROOT+'?action=play&url=x'}})}
        loopsrc={'addon':'Loop','quality':'','play':json.dumps({'e':'TheLoopRoute','l':{'address':'plugin://plugin.video.theloop/?x'}})}
        seen=[]
        self.assertTrue(sports_game.warm_best([crewsrc],warm=lambda link:seen.append(link) or True));self.assertEqual(seen,[{'address':ROOT+'?action=play&url=x'}])
        seen.clear();self.assertFalse(sports_game.warm_best([loopsrc],warm=lambda link:seen.append(link)));self.assertEqual(seen,[])
        self.assertFalse(sports_game.warm_best([],warm=lambda link:True));self.assertFalse(sports_game.warm_best([{'play':'{no'}],warm=lambda link:True))
class Joining(unittest.TestCase):   # build 645 log aec66fce: the tap came 2 s into the warm listing and started a second one
    def setUp(self):
        crew._WARM.clear();crew._INFLIGHT.clear()
    def test_a_tap_during_the_warm_listing_waits_for_it_and_lists_nothing_itself(self):
        import threading,time
        calls=[];started=threading.Event();release=threading.Event()
        def slow(path,session=None,playback=False):
            calls.append(path);started.set();release.wait(5)
            return [entry('Alpha vs Beta',FRESH.removeprefix(ROOT),False)] if path==PARENT else [entry('NBA LIVE (CS)','?action=xdirectory&url=parent')]
        link=crew.CrewLink(ROOT+'?action=play&url=old',[{'address':ROOT_ROUTE,'label':'Crew NBA'},{'address':PARENT,'label':'NBA LIVE (CS)'}],GAME).to_dict()
        answers=[]
        with patch.object(crew,'_listing',slow):
            warm=threading.Thread(target=lambda:crew.warm(link));warm.start();started.wait(2)
            tap=threading.Thread(target=lambda:answers.append(crew.refresh_link(link)));tap.start()
            time.sleep(.2);self.assertTrue(tap.is_alive())   # waiting, not listing
            release.set();warm.join(3);tap.join(3)
        self.assertEqual(answers,[FRESH]);self.assertEqual(calls,[PARENT])
    def test_a_background_listing_waits_for_a_moving_screen_but_never_long(self):
        waited=[];readings=iter(['60.0','60.0','3.1'])
        t=crew.yield_to_screen(fps=lambda:next(readings),sleep=waited.append)
        self.assertEqual(len(waited),2);self.assertEqual(t,.5)
        self.assertEqual(crew.yield_to_screen(fps=lambda:'60',sleep=lambda n:None),crew.YIELD_MAX)   # a screen that never settles: three seconds at most
        self.assertEqual(crew.yield_to_screen(fps=lambda:'3.0',sleep=lambda n:self.fail('idle screen')),0.0)
        self.assertEqual(crew.yield_to_screen(fps=lambda:'abc',sleep=lambda n:self.fail('unreadable')),0.0)
    def test_only_background_listings_yield(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/sports_crew_routes.py').read_text()
        self.assertIn('    if not playback:\n        yield_to_screen()',text)

class AutoSearch(unittest.TestCase):   # build 646 log 317cd411: "None yet" on a live game until Check now was tapped
    def setUp(self):
        import sports_game;self.g=sports_game
    def test_a_live_game_without_sources_keeps_looking_for_three_minutes(self):
        g=self.g
        self.assertTrue(g.auto_wanted(True,False,100,100+g.AUTO_SEARCH-1))
        self.assertFalse(g.auto_wanted(True,False,100+g.AUTO_SEARCH,100+g.AUTO_SEARCH))   # it gives up: "None yet" and Check now
        self.assertFalse(g.auto_wanted(False,False,100,1000))        # a game that has not started: Remind me, as before
        self.assertFalse(g.auto_wanted(True,True,100,1000))          # sources found
        self.assertFalse(g.auto_wanted(True,False,100,1000,failed=True))
    def test_a_new_look_is_due_five_seconds_after_the_last_and_never_beside_a_running_one(self):
        g=self.g
        self.assertTrue(g.auto_due(10,4,False));self.assertFalse(g.auto_due(8,4,False));self.assertFalse(g.auto_due(100,4,True))
        self.assertFalse(g.auto_due(60,0,False,g.AUTO_ASK));self.assertTrue(g.auto_due(g.AUTO_ASK,0,False,g.AUTO_ASK))   # a real search (Crew walks its menus) is not started every few seconds
    def test_the_page_uses_it(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/sports_game.py').read_text()
        self.assertIn('auto_wanted(',text);self.assertIn('auto_due(',text);self.assertIn('searching = searching or auto_wanted(',text)
        self.assertIn('AUTO_ASK',text);self.assertIn('self.refresh(reload=False)   # only reads',text)

class Resolved(unittest.TestCase):   # build 639 log fd1d028c: about 6 s between the play call and Kodi's first stream, silent in the log
    def test_the_time_to_the_first_stream_is_logged_without_an_address(self):
        import sports_jet
        t=[0.0];logs=[];states=iter(['','',ROOT+'?action=play&url=x','http://127.0.0.1:55608/manifest/a.m3u8'])
        route=ROOT+'?action=play&url=x'
        def clock():return t[0]
        def sleep(n):t[0]+=n
        self.assertTrue(sports_jet.watch_resolved(route,lambda:next(states),logs.append,clock=clock,sleep=sleep))
        self.assertEqual(len(logs),1);self.assertIn('handed Kodi its stream 0.8s',logs[0]);self.assertNotIn('127.0.0.1',logs[0])
    def test_no_stream_in_time_is_logged_and_nothing_raises(self):
        import sports_jet
        t=[0.0];logs=[]
        def boom():raise RuntimeError('player gone')
        self.assertFalse(sports_jet.watch_resolved('r',boom,logs.append,clock=lambda:t[0],sleep=lambda n:t.__setitem__(0,t[0]+n),limit=2))
        self.assertIn('no stream in 2s',logs[0])

if __name__=='__main__':unittest.main()
