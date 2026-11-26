"""The scroll test (ISSUE-429): the Sports hub scrolls itself part by part so a log says what costs a frame."""
import re,sys,types,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.path[:0]=[str(BOOT/'resources/lib'),str(BOOT)]
import scroll_test as st

class Home:
    def __init__(self):self.props={};self.history=[]
    def setProperty(self,k,v):self.props[k]=v;self.history.append(v)
    def clearProperty(self,k):self.props.pop(k,None)

class Runner(unittest.TestCase):
    def test_the_property_names_the_parts_left_out(self):
        self.assertEqual(st.value(()),'');self.assertEqual(st.value(('live',)),'_live_');self.assertEqual(st.value(('live','tiles','rows')),'_live_tiles_rows_')
    def test_every_run_scrolls_down_and_up_and_is_summed_up(self):
        home=Home();moves=[];logs=[];rates=iter([30,12,28,26,40,3]*5000)
        found=st.run(home,moves.append,lambda:next(rates),lambda s:False,logs.append,steps=2,pause=0.3,settle=0)
        self.assertEqual(home.history,['','_live_','_tiles_','_rows_','_live_tiles_rows_']);self.assertNotIn(st.PROPERTY,home.props)   # always cleared at the end
        self.assertEqual(moves,(['Down']*2+['Up']*2)*5);self.assertEqual(len(logs),5);self.assertEqual(list(found),[n for n,_ in st.RUNS])
        self.assertRegex(logs[0],r'^Kodi iOS scroll test: everything drawn: \d+ fps typical, \d+ fps slowest tenth, \d+ samples$')
        self.assertTrue(all(r>=st.ANIMATING for v in found.values() for r in v))   # idle readings are not counted
    def test_closing_kodi_stops_it_and_still_clears_the_property(self):
        home=Home();calls=[]
        def wait(s):calls.append(s);return len(calls)>3
        st.run(home,lambda d:None,lambda:30,wait,lambda t:None,steps=2,pause=.3,settle=0)
        self.assertNotIn(st.PROPERTY,home.props);self.assertLess(len(home.history),5)
    def test_a_failure_still_clears_the_property(self):
        home=Home()
        def move(d):raise RuntimeError('x')
        with self.assertRaises(RuntimeError):st.run(home,move,lambda:30,lambda s:False,lambda t:None,steps=1,pause=.2,settle=0)
        self.assertNotIn(st.PROPERTY,home.props)
    def test_too_few_readings_say_so(self):
        self.assertIn('too few readings (3)',st.summary('x',[30,30,30]))

class Skin(unittest.TestCase):
    """The parts are hidden only while the property names them; with it empty nothing changes. The taps and focus stay."""
    def pages(self):
        import portrait,sports_page,sports_upcoming_page
        p=portrait
        return sports_page.page(p),sports_upcoming_page.page(p)
    def test_the_hub_and_the_game_rows_carry_the_hooks_and_keep_their_buttons(self):
        hub,upcoming=self.pages()
        for part in ('live','tiles','rows'):self.assertIn('!String.Contains(Window(Home).Property(KodiIOS.ScrollTest),_%s_)'%part,hub)
        self.assertIn('_rows_',upcoming)
        for ident in (9101,9102,9103,9106):self.assertIn('id="%d"'%ident,hub)   # the card, both tiles and See all are still buttons
        self.assertNotRegex(hub,r'!\(')   # the project's rule for Kodi conditions
    def test_a_hidden_part_never_takes_a_button_with_it(self):
        import xml.etree.ElementTree as ET
        for page in self.pages():
            root=ET.fromstring(page.encode());hidden=0
            for group in root.iter('control'):
                if group.get('type')=='group' and 'KodiIOS.ScrollTest' in (group.findtext('visible') or ''):
                    hidden+=1;self.assertEqual([c.get('id') for c in group.iter('control') if c.get('type')=='button'],[])   # taps and focus stay whatever is left out
            self.assertGreater(hidden,0)
    def test_the_trigger_is_a_hidden_search_and_the_hub_starts_the_test(self):
        search=(BOOT/'settings_search.py').read_text();sports=(BOOT/'sports.py').read_text()
        self.assertIn("if query.lower()=='scroll test':found=[('Run the scroll test','Developer','RunScript(service.kodi.ios.bootstrap,sports,scrolltest)')]",search)
        self.assertIn("if args and args[0] == 'scrolltest':",sports);self.assertIn('test.start(self, xbmc, xbmcgui, log)',sports)
if __name__=='__main__':unittest.main()
