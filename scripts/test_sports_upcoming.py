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
        self.assertEqual((rows[0]['clock'],rows[0]['soon'],rows[0]['sources']),('7:30 PM','in 45 min','2 sources'))
        self.assertEqual(rows[1]['sources'],'No sources yet')
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

    def test_long_names_wrap_and_keep_every_character(self):
        game=dict(self.games[0],away={'name':'Borussia Mönchengladbach'},home={'name':'Brighton & Hove Albion'})
        props,rows,_,_=upcoming.model([game],self.provider.now,self.provider.now,0)
        self.assertEqual(rows[0]['title'],sm.versus(game))
        self.assertGreater(int(rows[0]['lines']),1)
        self.assertNotIn('…',props['row.0.title'])
        self.assertGreater(page.row_height(int(rows[0]['lines'])),page.row_height(1))
        self.assertEqual(rows[0]['soon'],'in 45 min')

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
        self.assertTrue(any(c.get('type')=='textbox' and c.findtext('width')=='570' for c in tree.iter('control')))
        self.assertIn('sports_upcoming', (BOOT/'default.py').read_text())
        self.assertIn('sports_upcoming_page.files(ns)',p.__file__ and Path(p.__file__).read_text())


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
