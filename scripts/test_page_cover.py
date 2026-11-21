"""Opaque full-screen pages stop the window under them drawing while they are open (owner, 2026-11-21: keep the current UI, scroll smoothly; build 621
log 5b1f4222: Sports pages 21-34 fps against Home's 60). Desktop Kodi rig, wheel-scrolling with the window under hidden: Upcoming (120 games) 65 -> 118-133
fps, Favourites 78 -> 159, Notifications 84 -> 169, each with less CPU; screenshots of the pages unchanged; Home back at once on close."""
import re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True;sys.path.insert(0,str(BOOT/'resources/lib'))
import page_cover as pc

class Home:
    def __init__(self):self.p={}
    def getProperty(self,k):return self.p.get(k,'')
    def setProperty(self,k,v):self.p[k]=v
    def clearProperty(self,k):self.p.pop(k,None)

class Cover(unittest.TestCase):
    def test_a_page_covers_while_open_and_stacked_pages_keep_it(self):
        home=Home()
        with pc.covering(home):
            self.assertTrue(home.getProperty(pc.COVERED))
            with pc.covering(home):self.assertEqual(len(home.getProperty(pc.COVERED).split()),2)
            self.assertEqual(len(home.getProperty(pc.COVERED).split()),1)   # the hub page under Upcoming still covers
        self.assertEqual(home.getProperty(pc.COVERED),'')
    def test_an_error_in_the_page_still_uncovers(self):
        home=Home()
        with self.assertRaises(RuntimeError):
            with pc.covering(home):raise RuntimeError('page failed')
        self.assertEqual(home.getProperty(pc.COVERED),'')
    def test_the_service_clears_a_dead_pages_cover_only_when_no_dialog_is_open(self):
        home=Home();home.setProperty(pc.COVERED,'dead')
        self.assertFalse(pc.tidy(home,True));self.assertEqual(home.getProperty(pc.COVERED),'dead')
        self.assertTrue(pc.tidy(home,False));self.assertEqual(home.getProperty(pc.COVERED),'')
        self.assertIn('page_cover.tidy(home,xbmc.getCondVisibility(\'System.HasActiveModalDialog\'))',(BOOT/'service.py').read_text())

class Skin(unittest.TestCase):
    def test_the_windows_under_these_pages_hide_while_covered_nothing_else(self):
        # Opt-in: the test_portrait context-menu check found that a dialog whose skin file says no type="dialog" was wrapped too (its menu would hide
        # over a Sports page); only Home, the hubs, the Library hub and Search are wrapped.
        import portrait as p
        self.assertEqual(p.COVERED_CONDITION,'![!String.IsEmpty(Window(Home).Property(KodiIOS.Covered)) + System.HasActiveModalDialog]')
        self.assertEqual(p.covered('<controls><control type="image"/></controls>'),
                         '<controls><control type="group"><visible>%s</visible><control type="image"/></control></controls>'%p.COVERED_CONDITION)
        self.assertEqual(p.covered('<controls />'),'<controls />')
        self.assertNotIn('KodiIOS.Covered',p.window('<window id="106"/>','<controls><control type="image"/></controls>','1'))   # window() itself never wraps
        src=(BOOT/'resources/lib/portrait.py').read_text()
        for call in ("covered('<controls>%s%s</controls>'%(backdrop(),hub_body(","covered('<controls>%s%s</controls>'%(backdrop(),groups))",
                     "return window(original,covered(body),'5000')","return window(bare,covered(body),'5100')"):
            self.assertIn(call,src)
        self.assertEqual(src.count('covered('),5)   # the definition and these four

class Pages(unittest.TestCase):
    def test_the_opaque_pages_cover(self):
        for name in ('sports','sports_live','sports_upcoming','sports_leagues','sports_game','favourites_page','notifications'):
            text=(BOOT/(name+'.py')).read_text()
            self.assertRegex(text,r'with page_cover\.covering\(\):[^\n]*\n\s+\w+\.doModal\(\)',name)
    def test_they_draw_an_opaque_backdrop(self):
        import portrait as p
        self.assertEqual(p.backdrop(),p.image(0,0,p.WIDTH,p.HEIGHT,p.MEDIA+'white.png',p.BG));self.assertEqual(p.BG,'FF000000')

if __name__=='__main__':unittest.main()
