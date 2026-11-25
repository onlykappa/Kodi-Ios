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
import http.client  # noqa: F401  loaded before any test patches sys.modules (Python 3.14: a patched-away http leaves portrait's xml import without http.client)
import urllib.request  # noqa: F401
import portrait  # noqa: F401

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

    def test_a_white_or_light_team_colour_never_washes_the_hero_out(self):
        # Owner, 2026-11-20: "the colors seem to flash white ... then goes to all white". Cologne's ESPN colour is ffffff.
        self.assertEqual(game_page.glow('ffffff'),game_page.NEUTRAL)          # white: the soft grey of a team with no colour
        self.assertEqual(game_page.glow('f8f8f8'),game_page.NEUTRAL)
        for color in ('ffd100','a0d8f0','e6e6e6','00ff00'):
            tint=game_page.glow(color);rgb=[int(tint[2+i:4+i],16) for i in (0,2,4)]
            self.assertLessEqual(game_page._luminance(rgb),game_page.MAX_GLOW+.01,color)
        self.assertEqual(game_page.glow('0c2340'),TINT_B8+game_page.lighten('0c2340'))   # a dark colour is only lightened, as before
        self.assertEqual(game_page.glow('dc052d')[:2],'B8')
    def test_board13_is_empty_not_a_provider_failure(self):
        self.game['sources']=[]
        props,sources=game_page.model(self.game,NOW,0)
        self.assertEqual(props['state'],'empty')
        self.assertEqual(props['sources.count'],'')
        self.assertEqual(props['error.title'],'')
        self.assertEqual(props['source.0.form'],'')
        self.assertEqual(props['clock'],'7:30 PM')
        self.assertFalse(sources)

    def test_live_search_states_are_distinct_from_empty_and_upcoming(self):
        self.game.update(state='live',sources=[])
        props,_=game_page.model(self.game,NOW,0,searching=True)
        self.assertEqual(props['state'],'searching')
        props,_=game_page.model(self.game,NOW,0)
        self.assertEqual((props['state'],props['game.live']),('empty','true'))
        self.assertIn('Try again',props['empty.text'])

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


TINT_B8='B8'


class Hero(unittest.TestCase):
    """The hero of the owner's page 6 mockup: short names with records on each team's colour, the time and how long until it, Game info."""
    def game(self,**extra):
        game={'id':'g','league':'NFL','league_name':'NFL','start':NOW+2*3600+600,'sources':[],'state':'upcoming','joiner':'at',
              'away':{'code':'IND','name':'Indianapolis Colts','short':'Colts','record':'3-7','color':'0c2340'},
              'home':{'code':'HOU','name':'Houston Texans','short':'Texans','record':'3-6'}}
        game.update(extra)
        return game

    def test_short_names_records_colours_and_when(self):
        props,_=game_page.model(self.game(week=11),NOW,0)
        self.assertEqual((props['away.name'],props['home.name'],props['away.record'],props['home.record']),('Colts','Texans','3-7','3-6'))
        self.assertEqual((props['away.tint'],props['home.tint']),(TINT_B8+game_page.lighten('0c2340'),game_page.NEUTRAL))   # a team without a colour gets the soft grey
        self.assertEqual(props['when'],'Today · in 2 h 10 min')
        self.assertEqual((props['info.title'],props['info.sub']),('NFL · Week 11','Today at 8:55 PM'))
        self.assertEqual(game_page.model(self.game(),NOW,0)[0]['info.title'],'NFL')   # no week, no "· Week"

    def test_crests_come_from_the_phones_own_copies(self):
        game=self.game();game['away']['crest']='https://a.espncdn.com/i/teamlogos/nfl/500/ind.png'
        self.assertEqual(game_page.model(game,NOW,0)[0]['away.crest'],game['away']['crest'])   # no mapping given: the address as it is
        self.assertEqual(game_page.model(game,NOW,0,crests={})[0]['away.crest'],'')             # not downloaded yet: the ring with the code shows
        self.assertEqual(game_page.model(game,NOW,0,crests={game['away']['crest']:'/p/c.png'})[0]['away.crest'],'/p/c.png')

    def test_a_colour_that_is_not_hex_is_ignored(self):
        game=self.game();game['away']['color']='not-hex'
        self.assertEqual(game_page.model(game,NOW,0)[0]['away.tint'],game_page.NEUTRAL)

    def test_the_sources_card_says_when_it_last_looked(self):
        self.assertEqual(game_page.checked_text(None,NOW),'')
        self.assertEqual(game_page.checked_text(NOW-20,NOW),'Checked just now')
        self.assertEqual(game_page.checked_text(NOW-120,NOW),'Checked 2 minutes ago')
        self.assertEqual(game_page.checked_text(NOW-60,NOW),'Checked 1 minute ago')
        self.assertEqual(game_page.checked_text(NOW-7300,NOW),'Checked 2 hours ago')
        self.assertEqual(game_page.model(self.game(),NOW,0,checked=NOW-120)[0]['checked'],'Checked 2 minutes ago')

    def test_lighten_mixes_dark_team_colours_toward_white(self):
        self.assertEqual(game_page.lighten('000000'),'4C4C4C')
        self.assertEqual(game_page.lighten('FFFFFF'),'FFFFFF')

    def test_a_live_game_shows_live_the_score_and_the_clock(self):
        game=self.game(state='live',clock='Q3 · 4:12');game['away']['score']=88;game['home']['score']=91
        props,_=game_page.model(game,NOW,0)
        self.assertEqual((props['game.live'],props['clock'],props['when']),('true','88 – 91','Q3 · 4:12'))
        game['away']['score']=None
        self.assertEqual(game_page.model(game,NOW,0)[0]['clock'],'Q3 · 4:12')   # no score (golf, F1): just the clock

    def test_the_live_clock_counts_down_between_espn_answers(self):
        game={'state':'live','clock':'Q3 · 8:41','clock_secs':521.0,'clock_at':NOW,'clock_mark':'Q3','clock_running':True}
        self.assertEqual(sm.live_clock(game,NOW),'Q3 · 8:41')
        self.assertEqual(sm.live_clock(game,NOW+1),'Q3 · 8:40')
        self.assertEqual(sm.live_clock(game,NOW+61),'Q3 · 7:40')
        self.assertEqual(sm.live_clock(game,NOW+500),'Q3 · 7:11')            # never more than 90 s without a fresh answer
        stopped=dict(game,clock_running=False)
        self.assertEqual(sm.live_clock(stopped,NOW+30),'Q3 · 8:41')            # a stopped clock (timeout) is not counted
        self.assertEqual(sm.live_clock(dict(game,clock_secs=None),NOW+30),'Q3 · 8:41')   # soccer, baseball: ESPN's own text
        self.assertEqual(sm.live_clock(dict(game,clock_secs=3.0),NOW+10),'Q3 · 8:41')    # ran out: wait for ESPN's answer (end of period)
        self.assertEqual(sm.live_clock(dict(game,state='upcoming'),NOW+5),'Q3 · 8:41')

    def test_the_game_page_shows_the_ticking_clock(self):
        game=self.game(state='live',clock='Q3 · 4:12',clock_secs=252.0,clock_at=NOW,clock_mark='Q3',clock_running=True);game['away']['score']=88;game['home']['score']=91
        self.assertEqual(game_page.model(game,NOW,0)[0]['when'],'Q3 · 4:12')
        self.assertEqual(game_page.model(game,NOW+12,0)[0]['when'],'Q3 · 4:00')

    def test_until_text(self):
        self.assertEqual([sm.until_text(NOW+s,NOW) for s in (45*60,3600,7800,-5,24*3600)],['in 45 min','in 1 h','in 2 h 10 min','',''])

    def test_a_title_only_event_names_just_its_title(self):
        game=self.game(away={'code':'PGA','name':'The RSM Classic','short':'','record':''},home={'code':'','name':'','record':''})
        props,_=game_page.model(game,NOW,0)
        self.assertEqual((props['away.name'],props['home.name']),('The RSM Classic',''))


class Structure(unittest.TestCase):
    def test_xml_has_real_buttons_complete_text_and_runtime_crests(self):
        import portrait
        xml=page.page(portrait);root=ET.fromstring(xml)
        ids=[c.get('id') for c in root.iter('control') if c.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertNotIn('!(',xml);self.assertNotIn('…',xml)
        self.assertIn('None yet',xml)
        self.assertIn('Check now',xml)
        self.assertIn('Window().Property(away.tint)',xml)
        self.assertIn('Window().Property(info.title)',xml)
        self.assertIn('Searching for sources',xml)
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
        # A reminder's notification opens a game by id (RunScript ... sports_game,<id>), so it is a page now (board C of the game page).
        self.assertIn("'sports_game'",(BOOT/'default.py').read_text())


class Controller(unittest.TestCase):
    def exercise(self,provider,scenario,play=None,search=False):
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
            game_page.run(seed,provider=provider,clock=lambda:NOW,search=search)
        self.assertFalse(writes_after_close)
        return windows[0],played

    def test_focused_search_opens_loading_and_cancels_with_page(self):
        provider=sm.Sample(now=NOW);calls=[]
        provider.request_game=lambda ident:calls.append(('request',ident)) or 'token'
        provider.searching_game=lambda ident,token:True
        provider.cancel_game_search=lambda token:calls.append(('cancel',token))
        seed=provider.game('epl-1');seed['sources']=[]
        def scenario(w):
            self.assertEqual(w.props['state'],'searching')
            w.onClick(page.BACK)
        original=sm.Sample.game
        with patch.object(sm.Sample,'game',lambda self,ident:seed if ident=='epl-1' else original(self,ident)):
            self.exercise(provider,scenario,search=True)
        self.assertEqual(calls,[('request','epl-1'),('cancel','token')])

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
        run.assert_called_once_with(game,provider=provider,clock=clock,search=True)   # opening a game looks for its sources

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

class RemindThenPlay(unittest.TestCase):
    """Owner-approved board C: Remind me before a source exists, Reminder on once asked, Play with the best source when one is found."""
    def game(self,sources=True):
        g=copy.deepcopy(sm.Sample(now=NOW,offset=0).upcoming[0])
        if not sources:g['sources']=[]
        return g

    def test_no_source_offers_a_reminder_then_says_it_is_on(self):
        import sports_reminders as sr
        props,_=game_page.model(self.game(False),NOW,0)
        self.assertEqual((props['state'],props['remind.on'],props['remind.note'],props['play.best']),('empty','',"No source yet. Tap Remind me for a notification when one is ready.",''))
        record={'on_source':True,'before':True}
        props,_=game_page.model(self.game(False),NOW,0,reminder=record)
        self.assertEqual(props['remind.on'],'true')
        self.assertEqual(props['remind.note'],'Reminders are set for this game.')   # plain words, no bold (owner)

    def test_a_source_names_the_best_one_under_play(self):
        props,found=game_page.model(self.game(True),NOW,0)
        self.assertTrue(props['play.best'].startswith('[COLOR FFFFFFFF][B]Best source:[/B][/COLOR] '))   # the label is bold white, the rest grey
        self.assertEqual(props['other.text'],'Other sources (%d)' % (len(found)-1))
        self.assertIn('1080p',props['play.best'])

    def test_the_page_has_both_buttons_and_the_script_runs_the_sheet(self):
        import portrait
        xml=page.files(portrait)['portrait/'+page.WINDOW].decode()
        ET.fromstring(xml)
        for ident in (page.REMIND,page.REMIND_ON):self.assertIn('id="%d"'%ident,xml)
        self.assertIn('Window().Property(remind.note)',xml);self.assertIn('Window().Property(play.best)',xml)
        src=(BOOT/'sports_game.py').read_text()
        self.assertIn('ident in (page.REMIND,page.REMIND_ON)',src);self.assertIn('sports_remind.ask(',src)


if __name__=='__main__':unittest.main()
