"""The Sports hub's first frame holds the games (owner, build 623: "needs to be instant like every other page")."""
import os,sys,tempfile,threading,types,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
sys.path[:0]=[str(ROOT),str(ROOT/'resources/lib')]
for name in ('xbmc','xbmcgui','xbmcvfs','xbmcaddon'):sys.modules.setdefault(name,types.ModuleType(name))
sys.modules['xbmc'].log=lambda *a,**k:None;sys.modules['xbmc'].LOGINFO=1
import sports,sports_espn as se,sports_hybrid as hy
from test_sports_fresh import board

class Page:
    def __init__(self):self.props={}
    def setProperty(self,k,v):self.props[k]=v

class Provider:
    def __init__(self,path,now,answers,hold=None):
        self.calls=[]
        def fetch(url):
            self.calls.append(url)
            if hold:hold.wait(5)
            if not answers:raise OSError('offline')
            return answers[0]
        self.espn=se.EspnProvider(fetch=fetch,clock=lambda:now,leagues={'NHL'},snapshot_path=path)
        self.provider=hy.HybridProvider(self.espn,lambda *a,**k:[])
class Module:
    def __init__(self,provider):self.p=provider
    def get(self):return self.p

class FirstFrame(unittest.TestCase):
    def test_a_saved_answer_fills_the_page_before_it_opens_without_asking_espn(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');Provider(path,1_795_000_000,[board()]).espn.refresh()
            hold=threading.Event();later=Provider(path,1_795_000_100,[board()],hold);page=Page()   # ESPN's answer is held back: the draw must not wait for it
            self.assertTrue(later.provider.has_answer())
            self.assertTrue(sports.draw_first(page,Module(later.provider)));hold.set()
            self.assertEqual(page.props['state'],'ok');self.assertIn('up.title',page.props);self.assertNotEqual(page.props.get('up.d1'),'Checking games')
            self.assertTrue(page.last and page.last['state']=='ok');# the real answer follows in the background
    def test_with_nothing_saved_the_page_waits_instead_of_blocking_on_espn(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            later=Provider(os.path.join(d,'none.json'),1_795_000_100,[board()]);page=Page()
            self.assertFalse(later.provider.has_answer());self.assertFalse(sports.draw_first(page,Module(later.provider)))
            self.assertEqual(page.props,{});self.assertEqual(later.calls,[])
    def test_a_provider_that_breaks_never_stops_the_page_opening(self):
        class Bad:
            def get(self):raise RuntimeError('x')
        self.assertFalse(sports.draw_first(Page(),Bad()))

class Wiring(unittest.TestCase):
    def test_a_refresh_does_not_cover_drawn_games_with_updating(self):
        text=(ROOT/'sports.py').read_text()
        self.assertIn('if refresh and not self.last:',text);self.assertIn('first = draw_first(page, sports_provider)',text)
        self.assertIn("if not getattr(self, 'last', None):",text)
    def test_the_service_asks_espn_first_thing_and_loads_the_hubs_modules(self):
        text=(ROOT/'service.py').read_text()
        start=text.index(' def sports_data_loop():');end=text.index(' threading.Thread(target=sports_data_loop,daemon=True).start()')
        self.assertIn('import sports,sports_upcoming,sports_live,sports_leagues,sports_rows,sports_filter,sports_hybrid,sports_espn',text[start:end])
        self.assertNotIn('waitForAbort(0.5)',text[start:end])
        self.assertLess(end,text.index("window.setProperty('KodiIOS.Build'"))   # started before the set-up work
class Upcoming(unittest.TestCase):
    def test_a_cold_start_reads_the_saved_answer_so_the_right_window_opens_once(self):   # build 623 log f5848994: short window, then the long one
        text=(ROOT/'sports_upcoming.py').read_text()
        seed=text.index("if _CACHE is None:");choose=text.index('slots = page.SLOTS_SHORT\n    if _CACHE is not None:')
        self.assertLess(seed,choose);self.assertIn("provider, 'has_answer'",text[seed:choose]);self.assertIn('_CACHE = (provider.upcoming_games(), provider.overview()',text[seed:choose])
class Startup(unittest.TestCase):
    def test_the_log_says_which_import_line_is_slow(self):
        text=(ROOT/'service.py').read_text()
        self.assertIn("_PARTS.append(('bootstrap',time.monotonic()))",text);self.assertIn("bootstrap entered (imports %.3fs: %s)",text)
if __name__=='__main__':unittest.main()
