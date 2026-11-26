"""The walk of Crew's menus remembers where games were found and visits those folders first; a recent walk answers a new search (owner, 2026-11-21, build 646 logs:
a cold walk of one league's 14 folders took 28.5 s and the first source came only at its end; every search started another walk)."""
import json,sys,tempfile,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import sports_crew_routes as crew
import sports_provider as provider

R='plugin://plugin.video.thecrew/'
GAME={'id':'espn:NBA:1','away':{'name':'Alpha'},'home':{'name':'Beta'},'league_name':'NBA','league':'NBA','state':'live','start':1000}
def folder(label,key):return {'label':label,'file':R+'?action=xdirectory&url='+key,'filetype':'directory'}
def stream(label,key):return {'label':label,'file':R+'?action=play&url='+key,'filetype':'file'}

class Walk(unittest.TestCase):
    def source(self,path):
        order=[]
        def read(route):
            order.append(route)
            if route==R+'league':return [folder('Site A','a'),folder('Site B','b'),folder('Site C','c')]
            if route.endswith('url=c'):return [stream('Alpha vs Beta','game')]
            return []
        src=crew.CrewSource('NBA',R+'league',[GAME],read);src.memory_path=path
        return src,order
    def test_the_folder_a_game_was_found_in_is_visited_first_next_time(self):
        path=str(Path(tempfile.mkdtemp())/'crew-yield.json')
        src,order=self.source(path);src.get_items()
        self.assertEqual([o.rsplit('url=',1)[-1] for o in order[1:]],['a','b','c'])   # the first walk: Crew's own order
        data=json.loads(Path(path).read_text());self.assertIn(GAME['id'],data['games']);self.assertEqual(data['games'][GAME['id']]['path'][0],'Site C')
        src,order=self.source(path);src.get_items()
        self.assertEqual(order[1].rsplit('url=',1)[-1],'c')   # remembered: Site C first
    def test_a_folder_that_held_games_before_comes_before_one_that_did_not(self):
        memory={'yield':{crew.folder_key('NBA',['Site B']):3},'games':{}}
        key=lambda label:crew.order_key(memory,'NBA',[label],[])
        self.assertLess(key('Site B'),key('Site A'));self.assertEqual(key('Site A'),key('Site C'))   # the rest keep Crew's order
    def test_without_memory_the_order_is_crews_own(self):
        src,order=self.source(None);src.get_items()
        self.assertEqual([o.rsplit('url=',1)[-1] for o in order[1:]],['a','b','c'])
    def test_old_games_and_damaged_files_are_not_trusted(self):
        path=Path(tempfile.mkdtemp())/'crew-yield.json'
        path.write_text(json.dumps({'yield':{'x':1},'games':{'old':{'path':['A'],'at':time.time()-crew.GAME_KEEP_FOR-5},'new':{'path':['B'],'at':time.time()}}}))
        mem=crew.load_memory(str(path));self.assertEqual(list(mem['games']),['new'])
        path.write_text('{no');self.assertEqual(crew.load_memory(str(path)),{'yield':{},'games':{}});self.assertEqual(crew.load_memory(None),{'yield':{},'games':{}})
    def test_older_counts_fade_and_the_file_stays_small(self):
        mem={'yield':{'x':0.04,'y':1},'games':{}}
        crew.remember_walk(mem,'NBA',[('g',['A','B'])])
        self.assertNotIn('x',mem['yield']);self.assertAlmostEqual(mem['yield']['y'],0.8);self.assertEqual(mem['yield']['NBA|A'],1);self.assertEqual(mem['yield']['NBA|A/B'],1)

class Reuse(unittest.TestCase):
    class Jet:
        def __init__(self,data):self.data=data
        def _home(self):
            d=self.data
            return type('H',(),{'getProperty':lambda s,k:json.dumps(d) if d is not None else ''})()
    def test_a_recent_finished_walk_of_the_same_league_is_reused(self):
        now=1000.0
        jet=self.Jet({'done':True,'at':now-60,'league':'NBA'})
        self.assertTrue(provider.walk_reusable(jet,'NBA',now=lambda:now))
        self.assertTrue(provider.walk_reusable(self.Jet({'done':True,'at':now-60,'league':''}),'NBA',now=lambda:now))   # every league was walked
    def test_another_league_an_old_walk_or_one_still_running_is_not(self):
        now=1000.0
        self.assertFalse(provider.walk_reusable(self.Jet({'done':True,'at':now-60,'league':'NHL'}),'NBA',now=lambda:now))
        self.assertFalse(provider.walk_reusable(self.Jet({'done':True,'at':now-provider.REUSE_WALK-1,'league':'NBA'}),'NBA',now=lambda:now))
        self.assertFalse(provider.walk_reusable(self.Jet({'done':False,'at':now-5,'league':'NBA'}),'NBA',now=lambda:now))
        self.assertFalse(provider.walk_reusable(self.Jet(None),'NBA',now=lambda:now))
    def test_check_now_asks_fresh_and_the_walk_ttl_is_longer(self):
        game=(ROOT/'migration/bundled-bootstrap/sports_game.py').read_text()
        self.assertIn('self.find_sources(fresh=True)   # "Check now"',game)
        jet=(ROOT/'migration/bundled-bootstrap/resources/lib/sports_jet.py').read_text()
        self.assertIn('WALK_TTL = 180',jet);self.assertIn("'league': self.walked",jet)
        import sports_jet;self.assertGreater(sports_jet.WALK_TTL,sports_jet.TTL)
if __name__=='__main__':unittest.main()
