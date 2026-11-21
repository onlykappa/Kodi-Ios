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
