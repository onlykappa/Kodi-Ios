"""Approved Upcoming board 10: contract projection, full text, navigation, asynchronous refresh and generated XML."""
import importlib.util
import sys
import threading
import time
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'migration/bundled-bootstrap'
sys.path[:0]=[str(BOOT),str(BOOT/'resources/lib')]
import sports_model as sm
import sports_upcoming as upcoming
import sports_upcoming_page as page


class Projection(unittest.TestCase):
    def setUp(self):
        self.provider=sm.Sample(now=1794768300,offset=0)
        self.games=self.provider.upcoming_games()

    def view(self,**kw):
        return upcoming.model(self.games,self.provider.now,self.provider.now,0,**kw)

    def test_board10_counts_days_times_and_source_words(self):
        props,rows,codes,selected=self.view()
        self.assertEqual(props['subtitle'],'6 games coming up · updated just now')
        self.assertEqual([r['day'] for r in rows if r['day']],['Today','Tomorrow','Sat, Nov 21'])
        self.assertEqual([r['day.count'] for r in rows if r['day']],['3 games','2 games','1 game'])
        self.assertEqual((rows[0]['clock'],rows[0]['tag'],rows[0]['lines']),('7:30 PM',rows[0]['game']['league'],'1'))   # the league tag sits over the time (approved mockup)
        self.assertEqual(codes,sm.league_codes(self.games))
        self.assertEqual(selected,'All')
        self.assertEqual(props['chipline.0'],'')   # no chip row: the Edit filter chooses leagues

    def test_filter_keeps_available_chips_and_uses_same_game_identity(self):
        props,rows,codes,selected=self.view(league='NBA')
        self.assertEqual([r['game']['id'] for r in rows],['nba-2'])
        self.assertEqual(props['subtitle'],'NBA · 1 game coming up · updated just now')
        self.assertEqual(codes,sm.league_codes(self.games))
        self.assertEqual(selected,'NBA')

    def test_started_games_leave_upcoming_and_stale_slots_are_cleared(self):
        props,rows,_,_=upcoming.model(self.games,self.provider.now,self.games[0]['start']+1,0)
        self.assertNotIn('epl-1',[r['game']['id'] for r in rows])
        self.assertEqual(props['row.119.title'],'')

    def test_long_names_fall_back_to_the_code_and_nothing_is_cut(self):
        game=dict(self.games[0],away={'name':'Borussia Mönchengladbach','short':'Borussia Mönchengladbach','code':'BMG','record':'3-4-5'},home={'name':'Brighton & Hove Albion','short':'Brighton','code':'BHA','record':''})
        props,rows,_,_=upcoming.model([game],self.provider.now,self.provider.now,0)
        self.assertEqual(rows[0]['title'],sm.versus(game))
        self.assertEqual((props['row.0.away.name'],props['row.0.home.name'],props['row.0.away.rec']),('BMG','Brighton','3-4-5'))   # over 16 characters: the code, not a cut name
        self.assertNotIn('…',props['row.0.away.name'])

    def test_an_event_without_a_second_side_is_form_two_with_its_title(self):
        game=dict(self.games[0],away={'name':'Las Vegas Grand Prix','code':'F1'},home={'name':''},title='Las Vegas Grand Prix',league='F1')
        props,rows,_,_=upcoming.model([game],self.provider.now,self.provider.now,0)
        self.assertEqual((props['row.0.lines'],props['row.0.title'],props['row.0.tag'],props['row.0.home.name']),('2','Las Vegas Grand Prix','F1',''))

    def test_loading_empty_failure_are_distinct(self):
        for state,expected in [('loading','loading'),('ready','empty'),('error','error')]:
            props,_,_,_=upcoming.model([],0,self.provider.now,0,state=state)
            self.assertEqual(props['state'],expected)
        props,_,_,_=upcoming.model([],0,self.provider.now,0,state='error')
        self.assertEqual(props['empty.title'],'Can’t load games right now')


class Structure(unittest.TestCase):
    def test_registered_xml_has_unique_controls_wrapping_and_real_hit_areas(self):
        spec=importlib.util.spec_from_file_location('portrait_sports',BOOT/'resources/lib/portrait.py')
        p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
        xml=page.page(p)
        tree=ET.fromstring(xml)
        ids=[c.get('id') for c in tree.iter('control') if c.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertNotIn('!(',xml)
        self.assertNotIn('…',xml)
        self.assertTrue(list(tree.iter('control')))
        for c in tree.iter('control'):
            if c.get('type')=='button' and c.findtext('enable')!='false':
                self.assertGreaterEqual(int(c.findtext('height')),118)
        self.assertTrue(any(c.get('type')=='textbox' for c in tree.iter('control')))   # form 2 wraps an event's title
        self.assertEqual(page.row_height(1),page.ROW_H)   # every row is one height (85 pt)
        self.assertIn('sports_upcoming', (BOOT/'default.py').read_text())
        self.assertIn('sports_upcoming_page.files(ns)',p.__file__ and Path(p.__file__).read_text())


class WindowSizes(unittest.TestCase):
    """Owner, build 617 log: the Upcoming flick was choppy. The usual list now gets a short window (30 rows); only a longer list opens the long one."""
    def test_the_window_has_room_for_the_games_it_is_given(self):
        self.assertEqual(page.window_for(0),page.WINDOW);self.assertEqual(page.window_for(page.SLOTS_SHORT),page.WINDOW)
        self.assertEqual(page.window_for(page.SLOTS_SHORT+1),page.WINDOW_LONG)
        self.assertGreaterEqual(page.SLOTS,page.SLOTS_SHORT*2)

    def test_both_windows_are_written_and_the_short_one_is_much_smaller_with_the_same_ids(self):
        spec=importlib.util.spec_from_file_location('portrait_sports',BOOT/'resources/lib/portrait.py')
        ns=importlib.util.module_from_spec(spec);spec.loader.exec_module(ns)
        short,long_=page.page(ns,page.SLOTS_SHORT),page.page(ns,page.SLOTS)
        self.assertLess(len(short),len(long_)//2)
        self.assertIn('id="%d"'%page.ROW,short);self.assertIn('id="%d"'%page.ROW,long_)       # the first game's tap is the same control in both
        self.assertNotIn('id="%d"'%(page.ROW+page.SLOTS_SHORT*len(page.FORMS)),short)         # and the short one stops where it says
        self.assertIn('id="%d"'%(page.ROW+page.SLOTS_SHORT*len(page.FORMS)),long_)
        names=page.files(ns)
        self.assertTrue(any(k.endswith('/'+page.WINDOW) for k in names));self.assertTrue(any(k.endswith('/'+page.WINDOW_LONG) for k in names))

    def test_the_projection_fills_only_the_slots_the_window_has(self):
        provider=sm.Sample(now=1794768300,offset=0)
        props,rows,*_=upcoming.model(provider.upcoming_games(),provider.now,provider.now,0,slots=page.SLOTS_SHORT)
        self.assertIn('row.%d.lines'%(page.SLOTS_SHORT-1),props);self.assertNotIn('row.%d.lines'%page.SLOTS_SHORT,props)
        props,*_=upcoming.model(provider.upcoming_games(),provider.now,provider.now,0)
        self.assertIn('row.%d.lines'%(page.SLOTS-1),props)

    def test_leagues_has_a_slot_for_every_league_and_not_four_times_as_many(self):
        import sports_espn,sports_leagues_page as lp
        self.assertGreaterEqual(lp.SLOTS,len(sports_espn.LEAGUES)+8);self.assertLessEqual(lp.SLOTS,48)


class Controller(unittest.TestCase):
    def test_opens_before_fetch_completes_filters_and_logs_game_tap(self):
        provider=sm.Sample(now=1794768300)
        entered,release=threading.Event(),threading.Event()
        original=provider.upcoming_games
        def get_games():
            entered.set();release.wait(2);return original()
        provider.upcoming_games=get_games
        provider.refresh=lambda: self.fail('opening Upcoming forced a scan')
        selected=[];opened=[]
        class Window:
            def __init__(self,*args):self.props={}
            def setProperty(self,k,v):self.props[k]=v
            def close(self):pass
            def doModal(self):
                self.onInit();opened.append(self.props['state'])
                assert entered.wait(1)
                assert self.props['state']=='loading'
                release.set()
                until=time.monotonic()+2
                while self.props.get('state')!='ready' and time.monotonic()<until:time.sleep(.01)
                assert self.props['state']=='ready'
                index=self.codes.index('NBA')
                self.onClick(page.CHIP+index*7+1)
                assert self.props['subtitle'].startswith('NBA · 1 game coming up')
                stop=self.stop
                self.onInit()  # Returning from a child window must keep the filter and timer.
                assert self.stop is stop
                assert self.league=='NBA'
                self.onClick(page.ROW+int(self.props['row.0.lines'])-1)
                self.onClick(page.BACK)
        xbmc=types.SimpleNamespace(log=lambda *a:None,LOGINFO=1,
            Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:True))
        gui=types.SimpleNamespace(WindowXMLDialog=Window)
        vfs=types.SimpleNamespace(translatePath=lambda x:x,listdir=lambda x:None)
        with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui,'xbmcvfs':vfs}),patch.object(upcoming,'_CACHE',None):
            upcoming.run(provider=provider,clock=lambda:provider.now,on_game=lambda game,log:selected.append(game['id']))
        self.assertEqual(opened,['loading'])
        self.assertEqual(selected,['nba-2'])


if __name__=='__main__':unittest.main()
