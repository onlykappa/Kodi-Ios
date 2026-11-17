"""Boards 16/17/20: shared league ordering/wording, complete rows and asynchronous navigation/recovery."""
import copy
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
import sports_leagues as leagues
import sports_leagues_page as page
import sports_upcoming
import sports_upcoming_page
import default as dispatcher

NOW=1794768300


def until(predicate):
    deadline=time.monotonic()+2
    while not predicate() and time.monotonic()<deadline:time.sleep(.005)
    assert predicate(),'background refresh did not finish'


class Provider:
    def __init__(self,fail=False):
        self.fail=fail;self.calls=0
        self.snapshot=sm.Sample(now=NOW,offset=0).leagues()
    def refresh(self):
        self.calls+=1
        if self.fail:raise sm.SportsUnavailable('private-test-error')
    def leagues(self):
        if self.fail:raise sm.SportsUnavailable('private-test-error')
        return copy.deepcopy(self.snapshot)
    def overview(self):return {'updated':NOW}


class Projection(unittest.TestCase):
    def test_board16_uses_shared_ordering_counts_and_red_live_fragment(self):
        source=Provider().snapshot
        before=copy.deepcopy(source)
        props,rows=leagues.model(source,NOW,NOW,0)
        expected=sm.order_leagues(source)
        self.assertEqual([r['league'] for r in rows],[lg for _,items in expected for lg in items])
        self.assertEqual([r['sport'] for r in rows if r['sport']],[sport for sport,_ in expected])
        self.assertEqual(props['subtitle'],'12 leagues · updated just now')
        self.assertEqual(props['row.0.sport.count'],'4 leagues')
        self.assertEqual(rows[0]['code'],'UCL')
        nba=next(r for r in rows if r['code']=='NBA')
        self.assertEqual((nba['live'],nba['next']),sm.league_detail(nba['league'],NOW,0))
        self.assertEqual(nba['detail'],'[COLOR FFFF453A]1 live[/COLOR] · next today 9:15 PM')
        self.assertEqual(source,before)

    def test_board17_retains_all_sports_and_nothing_coming_up(self):
        props,rows=leagues.model(Provider().snapshot,NOW,NOW,0)
        self.assertEqual([r['sport'] for r in rows if r['sport']],list(sm.SPORT_ORDER))
        for code in ('WNBA','BUN','MLB','UFC','F1'):
            row=next(r for r in rows if r['code']==code)
            self.assertEqual(row['detail'],'Nothing coming up')
        self.assertEqual(rows[-1]['title'],'Formula 1')
        self.assertEqual(rows[-1]['pos'],'only')

    def test_full_names_and_long_detail_get_wrapped_forms(self):
        lg={'code':'UCL','name':'UEFA Champions League International Competition','sport':'Soccer','live':1,
            'next':NOW+9*86400}
        props,rows=leagues.model([lg],NOW,NOW,0)
        title,detail=page.FORMS[int(rows[0]['form'])]
        self.assertGreater(title,1)
        self.assertEqual(rows[0]['title'],lg['name'])
        self.assertIn(sm.league_detail(lg,NOW,0)[1],rows[0]['detail'])
        self.assertGreater(page.row_height(title,detail),page.row_height(1,1))
        self.assertNotIn('…',str(props))

    def test_board20_loading_and_successful_zero_remain_distinct(self):
        for state in ('loading','error','ready'):
            props,rows=leagues.model([],NOW if state=='ready' else 0,NOW,0,state)
            self.assertEqual(props['state'],state)
            self.assertFalse(rows)
        props,_=leagues.model([],0,NOW,0,'error')
        self.assertEqual(props['subtitle'],'Not updated')
        self.assertEqual(props['error.title'],'Can’t load leagues right now')
        self.assertEqual(props['error.text.0']+' '+props['error.text.1'],
                         'The sports add-ons didn’t answer. Check the connection, then try again.')
        self.assertFalse(props['row.0.form'])
        props,_=leagues.model([],NOW,NOW,0)
        self.assertEqual(props['subtitle'],'0 leagues · updated just now')
        self.assertEqual(props['empty.text'],'No leagues listed')

    def test_removed_leagues_and_old_error_text_are_cleared(self):
        props,rows=leagues.model([Provider().snapshot[0]],NOW,NOW,0)
        self.assertEqual(len(rows),1)
        for key in ('title','code','form','sport','detail'):
            self.assertEqual(props['row.1.'+key],'')
        self.assertEqual(props['error.title'],'')


class Controller(unittest.TestCase):
    def exercise(self,provider,scenario,seed=None):
        logs,late,windows=[],[],[]
        class Window:
            def __init__(self,*args):self.props={};self.closed=False;windows.append(self)
            def setProperty(self,key,value):
                if self.closed:late.append(key)
                self.props[key]=value
            def close(self):self.closed=True
            def doModal(self):
                self.onInit()
                try:scenario(self)
                finally:
                    if not self.closed:self.onClick(page.BACK)
        xbmc=types.SimpleNamespace(log=lambda text,*args:logs.append(text),LOGINFO=1,executebuiltin=lambda text:logs.append('run '+text),
            Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:True))
        gui=types.SimpleNamespace(WindowXMLDialog=Window)
        vfs=types.SimpleNamespace(translatePath=lambda path:path,listdir=lambda path:None)
        with patch.dict(sys.modules,xbmc=xbmc,xbmcgui=gui,xbmcvfs=vfs),patch.object(leagues,'_CACHE',None),patch.object(leagues.sports_provider,'get',return_value=provider) as get:
            leagues.run(clock=lambda:NOW,seed=seed)
            get.assert_called_once_with()
        self.assertFalse(late)
        return logs

    def test_opens_before_fetch_completes_and_reentry_keeps_focus_state(self):
        provider=Provider();entered=threading.Event();release=threading.Event()
        get_leagues=provider.leagues
        def held():entered.set();release.wait(2);return get_leagues()
        provider.leagues=held
        def scenario(w):
            self.assertTrue(entered.wait(1));self.assertEqual(w.props['state'],'loading')
            release.set();until(lambda:not w.fetching)
            self.assertEqual(w.props['row.0.code'],'UCL')
            stop=w.stop;data=w.data
            w.onInit()
            self.assertIs(w.stop,stop);self.assertIs(w.data,data)
        self.exercise(provider,scenario)
        self.assertEqual(provider.calls,0)

    def test_error_survives_timer_redraw_and_failed_retry_then_recovers(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching);w.draw()
            self.assertEqual(w.props['state'],'error')
            self.assertNotIn('private-test-error',str(w.props))
            w.onClick(page.RETRY);until(lambda:not w.fetching);w.draw()
            self.assertEqual(w.props['state'],'error')
            provider.fail=False
            w.onClick(page.RETRY);until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(w.props['subtitle'],'12 leagues · updated just now')
            self.assertFalse(w.props['error.title'])
        self.exercise(provider,scenario)
        self.assertEqual(provider.calls,2)

    def test_cached_data_stays_visible_when_refresh_fails(self):
        seed=(Provider().snapshot,NOW)
        def scenario(w):
            until(lambda:not w.fetching);w.draw()
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(w.props['row.0.code'],'UCL')
        self.exercise(Provider(fail=True),scenario,seed)

    def test_closing_during_fetch_never_writes_to_closed_window(self):
        provider=Provider();entered=threading.Event();release=threading.Event()
        get_leagues=provider.leagues
        def held():entered.set();release.wait(2);return get_leagues()
        provider.leagues=held
        def scenario(w):
            self.assertTrue(entered.wait(1))
            w.onClick(page.BACK);release.set();until(lambda:not w.fetching)
            self.assertTrue(w.stop.is_set())
        self.exercise(provider,scenario)

    def test_row_tap_logs_until_the_league_route_is_registered_and_available(self):
        def scenario(w):
            until(lambda:not w.fetching)
            w.onClick(page.ROW+int(w.props['row.0.form']))
        logs=self.exercise(Provider(),scenario)
        self.assertIn('sports: league UCL',logs)
        sent=[]
        xbmc=types.SimpleNamespace(executebuiltin=sent.append)
        with patch.dict(sys.modules,xbmc=xbmc),patch.object(dispatcher,'PAGES',('sports_league',)),patch.object(leagues.os.path,'isfile',return_value=True):
            leagues.open_league('NBA',lambda text:None)
            leagues.open_league('NBA),recover',lambda text:None)
        self.assertEqual(sent,['RunScript(service.kodi.ios.bootstrap,sports_league,NBA)'])
        with patch.dict(sys.modules,xbmc=xbmc),patch.object(dispatcher,'PAGES',()),patch.object(leagues.os.path,'isfile',return_value=True):
            leagues.open_league('NBA',lambda text:None)
        self.assertEqual(len(sent),1)


class Structure(unittest.TestCase):
    def test_generated_window_registration_taps_focus_and_wrapping(self):
        import portrait
        root=ET.fromstring(page.files(portrait)['portrait/'+page.WINDOW])
        ids=[c.get('id') for c in root.iter('control') if c.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(root.find('defaultcontrol').get('always'),'false')
        xml=ET.tostring(root,encoding='unicode')
        self.assertNotIn('!(',xml);self.assertNotIn('…',xml)
        self.assertIn('sports_warning.png',xml)
        self.assertIn('p_state_title',xml)
        self.assertIn('scrolltime',xml)
        for c in root.iter('control'):
            if c.get('type')=='button' and c.findtext('enable')!='false':
                self.assertGreaterEqual(int(c.findtext('height')),118)
                self.assertGreaterEqual(int(c.findtext('width')),118)
        self.assertIn('sports_leagues',dispatcher.PAGES)
        source=(BOOT/'resources/lib/portrait.py').read_text()
        self.assertIn('sports_leagues_page.files(ns)',source)
        self.assertIn('Path(sports_leagues_page.__file__)',source)
        self.assertGreaterEqual(page.SCROLL_CLEAR,720)

    def test_upcoming_see_leagues_opens_the_same_provider_and_clock(self):
        source=(BOOT/'sports_upcoming.py').read_text()
        self.assertIn('sports_leagues.run(provider=provider,clock=clock)',source)
        self.assertIn('page.LEAGUES',source)


if __name__=='__main__':unittest.main()
