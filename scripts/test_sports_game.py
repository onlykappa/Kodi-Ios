"""Boards 12–13: full game text, ranked source identities and the asynchronous provider/play door."""
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
import sports_game as game_page
import sports_game_page as page
import sports_model as sm
import sports_upcoming

NOW=1794768300


def until(predicate):
    deadline=time.monotonic()+2
    while not predicate() and time.monotonic()<deadline:time.sleep(.005)
    assert predicate(),'background refresh did not finish'


class Projection(unittest.TestCase):
    def setUp(self):
        self.provider=sm.Sample(now=NOW)
        self.game=copy.deepcopy(self.provider.game('epl-1'))

    def test_board12_uses_the_contract_and_keeps_play_values(self):
        props,sources=game_page.model(self.game,NOW,0)
        self.assertEqual((props['league'],props['starts'],props['clock'],props['day']),
                         ('EPL','Starts in 45 min','7:30 PM','Today'))
        self.assertEqual((props['away.code'],props['away.name'],props['home.code']),('ARS','Arsenal','CHE'))
        self.assertEqual(props['source.0.detail'],'1080p · English\nAlso on Loop TV')
        self.assertEqual((props['source.0.code'],props['source.1.code']),('TL','LG'))
        self.assertEqual((props['source.0.tag'],props['source.1.tag']),('best','good'))
        self.assertEqual(props['sources.count'],'2')
        self.assertIs(sources[0],self.game['sources'][0])
        self.assertEqual(sources[0]['play'],self.game['sources'][0]['play'])

    def test_unknown_quality_has_readable_copy_without_empty_separator(self):
        self.game['sources']=self.game['sources'][:1]
        self.game['sources'][0].update(quality='',language='',also=[],tag='')
        props,_=game_page.model(self.game,NOW,0)
        self.assertEqual(props['source.0.detail'],'Quality not reported')

    def test_board13_is_empty_not_a_provider_failure(self):
        self.game['sources']=[]
        props,sources=game_page.model(self.game,NOW,0)
        self.assertEqual(props['state'],'empty')
        self.assertEqual(props['sources.count'],'')
        self.assertEqual(props['error.title'],'')
        self.assertEqual(props['source.0.form'],'')
        self.assertEqual(props['clock'],'7:30 PM')
        self.assertFalse(sources)

    def test_long_teams_and_source_metadata_keep_all_text(self):
        self.game['away'].update(name='Borussia Mönchengladbach',code='BMG',crest='https://example.invalid/crest.png')
        self.game['home'].update(name='Brighton & Hove Albion',code='BHA')
        self.game.update(league='UCL',league_name='UEFA Champions League')
        source=self.game['sources'][1]
        source.update(addon='International Sports Network',language='French Canadian commentary',also=['The Loop','Loop Guide','Sports Hub'])
        props,_=game_page.model(self.game,NOW,0)
        self.assertGreaterEqual(int(props['hero.lines']),3)
        self.assertEqual(props['away.name'],'Borussia Mönchengladbach')
        self.assertEqual(props['home.name'],'Brighton & Hove Albion')
        self.assertEqual(props['away.crest'],self.game['away']['crest'])
        title,detail=page.FORMS[int(props['source.1.form'])]
        self.assertGreater(title,1);self.assertGreater(detail,1)
        self.assertGreaterEqual(detail,6)  # This fixture needs six lines in the desktop Kodi text column.
        self.assertEqual(props['source.1.title'],source['addon'])
        self.assertIn('French Canadian commentary',props['source.1.detail'])
        self.assertIn('Sports Hub',props['source.1.detail'])

    def test_refresh_clears_removed_sources_and_reorders_new_sources(self):
        self.game['sources'].reverse()
        props,sources=game_page.model(self.game,NOW,0)
        self.assertEqual(sources[0]['tag'],'best')
        self.game['sources']=[]
        props,_=game_page.model(self.game,NOW,0)
        for n in (0,1,page.SLOTS-1):
            for field in ('title','detail','form','tag'):self.assertEqual(props['source.%d.%s'%(n,field)],'')

    def test_missing_game_failure_and_loading_stay_distinct(self):
        for state,expected in [('ready','gone'),('loading','loading'),('error','error')]:
            props,_=game_page.model(None,NOW,0,state)
            self.assertEqual(props['state'],expected)
        props,_=game_page.model(None,NOW,0,'error')
        self.assertEqual(props['error.title'],"Can't load this game right now")

    def test_later_day_keeps_the_full_two_digit_hour(self):
        props,_=game_page.model(self.provider.game('epl-2'),NOW,0)
        self.assertEqual(props['clock'],'12:30 PM')
        self.assertEqual(props['day'],'Sat, Nov 21')


class Structure(unittest.TestCase):
    def test_xml_has_real_buttons_complete_text_and_runtime_crests(self):
        import portrait
        xml=page.page(portrait);root=ET.fromstring(xml)
        ids=[c.get('id') for c in root.iter('control') if c.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertNotIn('!(',xml);self.assertNotIn('…',xml)
        self.assertIn('No sources yet',xml)
        self.assertIn('Check back closer to the start. Refresh looks again.',xml)
        self.assertIn('Window().Property(away.crest)',xml)
        self.assertIn('Window().Property(home.crest)',xml)
        clock=next(c for c in root.iter('control') if c.findtext('label')=='$INFO[Window().Property(clock)]')
        # Inter's two-digit-hour clock needs 378 units; leave room while staying between the crests.
        self.assertGreaterEqual(int(clock.findtext('width')),400)
        self.assertGreaterEqual(int(clock.findtext('left')),314)
        self.assertLessEqual(int(clock.findtext('left'))+int(clock.findtext('width')),767)
        for c in root.iter('control'):
            if c.get('type')=='button' and c.findtext('enable')!='false':
                self.assertGreaterEqual(int(c.findtext('height')),118)
        text=(BOOT/'resources/lib/portrait.py').read_text()
        self.assertIn('sports_game_page.files(ns)',text)
        self.assertIn('Path(sports_game_page.__file__)',text)
        self.assertNotIn("'sports_game'",(BOOT/'default.py').read_text())


class Controller(unittest.TestCase):
    def exercise(self,provider,scenario,play=None):
        seed=copy.deepcopy(sm.Sample(now=NOW).game('epl-1'))
        windows=[];writes_after_close=[]
        class Window:
            def __init__(self,*args):self.props={};self.closed=False;windows.append(self)
            def setProperty(self,key,value):
                if self.closed:writes_after_close.append(key)
                self.props[key]=value
            def close(self):self.closed=True
            def doModal(self):
                self.onInit()
                try:scenario(self)
                finally:
                    if not self.closed:self.onClick(page.BACK)
        xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda *a:None,
            Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:True),
            executebuiltin=lambda text:None,sleep=lambda ms:None)
        vfs=types.SimpleNamespace(translatePath=lambda x:x,listdir=lambda x:None)
        with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':types.SimpleNamespace(WindowXMLDialog=Window),'xbmcvfs':vfs}),\
             patch.object(game_page.sports_provider,'play',side_effect=play) as played:
            game_page.run(seed,provider=provider,clock=lambda:NOW)
        self.assertFalse(writes_after_close)
        return windows[0],played

    def test_seed_opens_immediately_and_whole_source_row_uses_play_door(self):
        provider=sm.Sample(now=NOW)
        entered,release=threading.Event(),threading.Event()
        get_game=provider.game
        def held(ident):entered.set();release.wait(2);return get_game(ident)
        provider.game=held
        provider.refresh=lambda:self.fail('opening a game forced a scan')
        def scenario(window):
            self.assertEqual(window.props['away.name'],'Arsenal')
            self.assertTrue(entered.wait(1))
            self.assertTrue(window.fetching)
            ident=page.SOURCE+int(window.props['source.0.form'])
            window.onClick(ident)
            window.onClick(page.SOURCE+len(page.FORMS)+int(window.props['source.1.form']))
            release.set();until(lambda:not window.fetching)
        _,played=self.exercise(provider,scenario)
        self.assertEqual(played.call_count,2)
        self.assertEqual([call.args[0]['id'] for call in played.call_args_list],
                         [source['id'] for source in provider.game('epl-1')['sources']])

    def test_background_read_picks_up_sources_without_forcing_another_scan(self):
        provider=sm.Sample(now=NOW)
        def scenario(w):
            until(lambda:not w.fetching)
            current=copy.deepcopy(provider.game('epl-1'))
            current['sources']=current['sources'][:1]
            provider.game=lambda ident:current
            provider.refresh=lambda:(_ for _ in ()).throw(AssertionError('forced duplicate scan'))
            w.refresh(reload=False);until(lambda:not w.fetching)
            self.assertEqual(w.props['sources.count'],'1')
        self.exercise(provider,scenario)

    def test_auto_button_keeps_ranked_fallback_choices(self):
        provider=sm.Sample(now=NOW)
        def scenario(w):
            until(lambda:not w.fetching)
            w.onClick(page.AUTO)
        _,played=self.exercise(provider,scenario)
        self.assertEqual(played.call_count,1)
        self.assertTrue(played.call_args.args[0]['alts'])

    def test_native_handoff_closes_modal_before_dispatch(self):
        import sports_jet
        provider=sm.Sample(now=NOW);launched=threading.Event()
        def play(source,log,launch=None):launch('sports_jet_run','play','fixture-key')
        def scenario(w):
            until(lambda:not w.fetching)
            def dispatch(*args):
                self.assertTrue(w.closed)
                self.assertTrue(w.stop.is_set())
                self.assertEqual(args,('sports_jet_run','play','fixture-key'))
                launched.set()
            with patch.object(sports_jet,'_launch',side_effect=dispatch):
                w.onClick(page.AUTO)
                self.assertTrue(launched.wait(1))
        self.exercise(provider,scenario,play)

    def test_failed_refresh_keeps_seed_and_success_can_remove_sources(self):
        provider=sm.Sample(now=NOW)
        get_game=provider.game
        def fail(ident):raise sm.SportsUnavailable('test provider offline')
        provider.game=fail
        def scenario(window):
            until(lambda:not window.fetching)
            self.assertEqual(window.props['sources.count'],'2')
            self.assertFalse(window.props['error.title'])
            self.assertNotIn('test provider offline',str(window.props))
            provider.refresh=lambda:None
            refreshed=get_game('epl-1')
            refreshed['sources']=[]
            provider.game=lambda ident:refreshed if ident==refreshed['id'] else None
            window.onClick(page.REFRESH);until(lambda:not window.fetching)
            self.assertEqual(window.props['state'],'empty')
            self.assertEqual(window.props['source.0.form'],'')
        self.exercise(provider,scenario)

    def test_close_during_fetch_prevents_late_window_writes(self):
        provider=sm.Sample(now=NOW)
        entered,release=threading.Event(),threading.Event()
        get_game=provider.game
        def held(ident):entered.set();release.wait(2);return get_game(ident)
        provider.game=held
        def scenario(window):
            self.assertTrue(entered.wait(1))
            window.onClick(page.BACK)
            release.set();until(lambda:not window.fetching)
            self.assertTrue(window.stop.is_set())
        self.exercise(provider,scenario)

    def test_upcoming_passes_the_same_game_provider_and_clock(self):
        provider=sm.Sample(now=NOW);game=provider.game('epl-1');clock=lambda:NOW
        with patch.object(game_page,'run') as run:
            sports_upcoming.open_game(game,lambda s:None,provider,clock)
        run.assert_called_once_with(game,provider=provider,clock=clock)

    def test_reentering_keeps_the_existing_worker_and_game(self):
        provider=sm.Sample(now=NOW);calls=[]
        provider.refresh=lambda:calls.append('refresh')
        def scenario(window):
            until(lambda:not window.fetching)
            stop=window.stop
            window.onInit()
            self.assertIs(window.stop,stop)
            self.assertEqual(calls,[])
            self.assertEqual(window.props['away.name'],'Arsenal')
        self.exercise(provider,scenario)

    def test_play_failure_is_plain_and_a_later_tap_clears_it(self):
        provider=sm.Sample(now=NOW)
        def scenario(window):
            until(lambda:not window.fetching)
            ident=page.SOURCE+int(window.props['source.0.form'])
            window.onClick(ident)
            self.assertEqual(window.props['play.error'],"Can't play this source right now. Try another source.")
            self.assertNotIn('raw-play-error',str(window.props))
            window.onClick(ident)
            self.assertEqual(window.props['play.error'],'')
        _,played=self.exercise(provider,scenario,play=[RuntimeError('raw-play-error'),None])
        self.assertEqual(played.call_count,2)


    def test_refresh_clears_a_previous_play_failure(self):
        def scenario(window):
            until(lambda:not window.fetching)
            window.onClick(page.SOURCE+int(window.props['source.0.form']))
            self.assertTrue(window.props['play.error'])
            window.refresh()
            until(lambda:not window.fetching)
            self.assertEqual(window.props['play.error'],'')
        self.exercise(sm.Sample(now=NOW),scenario,play=[RuntimeError('fixture play failure')])


if __name__=='__main__':unittest.main()
