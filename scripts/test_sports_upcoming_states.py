"""Upcoming boards 14–15: successful emptiness, persistent failure, retry and cached-data behaviour."""
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

NOW=1794768300


def until(predicate):
    deadline=time.monotonic()+2
    while not predicate() and time.monotonic()<deadline:time.sleep(.005)
    assert predicate(),'background refresh did not finish'


class Provider:
    def __init__(self,games=(),fail=False):self.games=list(games);self.fail=fail;self.calls=0
    def refresh(self):
        self.calls+=1
        if self.fail:raise sm.SportsUnavailable('raw-fixture-details')
    def upcoming_games(self):
        if self.fail:raise sm.SportsUnavailable('raw-fixture-details')
        return list(self.games)
    def overview(self):return {'updated':NOW}


class Projection(unittest.TestCase):
    def test_empty_has_the_board14_copy_and_no_chips_or_rows(self):
        props,rows,_,_=upcoming.model([],NOW,NOW,0)
        self.assertEqual(props['state'],'empty')
        self.assertEqual(props['subtitle'],'Updated just now')
        self.assertEqual(props['empty.title'],'No games coming up')
        self.assertEqual(props['empty.text'],'Nothing is scheduled yet.')
        self.assertEqual(props['empty.text.0'],props['empty.text'])
        self.assertEqual(props['empty.text.1'],'')
        self.assertFalse(rows)
        self.assertFalse(any(props['chip.%d.label'%n] for n in range(page.CHIPS)))
        self.assertFalse(any(props['row.%d.title'%n] for n in range(page.SLOTS)))

    def test_failure_has_the_board15_copy_and_is_not_successful_emptiness(self):
        props,_,_,_=upcoming.model([],0,NOW,0,state='error')
        self.assertEqual(props['state'],'error')
        self.assertEqual(props['subtitle'],'Not updated')
        self.assertEqual(props['empty.title'],'Can’t load games right now')
        self.assertEqual(props['empty.text'],'The sports add-ons didn’t answer. Check the connection, then try again.')
        self.assertEqual(props['empty.text'],' '.join(props['empty.text.%d'%n] for n in range(2)))

    def test_expired_cache_hides_all_chips_and_clears_the_old_rows(self):
        games=sm.Sample(now=NOW).upcoming_games()
        props,rows,_,_=upcoming.model(games,NOW,NOW+8*86400,0)
        self.assertEqual(props['state'],'empty')
        self.assertFalse(rows)
        self.assertFalse(any(props['chipline.%d'%n] for n in range(page.CHIP_LINES)))
        self.assertFalse(any(props['chip.%d.size'%n] for n in range(page.CHIPS)))
        self.assertEqual(props['row.0.title'],'')

    def test_no_timestamp_does_not_claim_a_fresh_update(self):
        props,_,_,_=upcoming.model([],0,NOW,0)
        self.assertEqual(props['state'],'empty')
        self.assertEqual(props['subtitle'],'Not updated')


class Controller(unittest.TestCase):
    def exercise(self,provider,scenario,cache=None):
        logs=[];late=[]
        class Window:
            def __init__(self,*args):self.props={};self.closed=False
            def setProperty(self,k,v):
                if self.closed:late.append(k)
                self.props[k]=v
            def close(self):self.closed=True
            def doModal(self):
                self.onInit()
                try:scenario(self)
                finally:
                    if not self.closed:self.onClick(page.BACK)
        xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda message,*_:logs.append(message),
            Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:True))
        vfs=types.SimpleNamespace(translatePath=lambda s:s,listdir=lambda s:None)
        with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':types.SimpleNamespace(WindowXMLDialog=Window),'xbmcvfs':vfs}),\
             patch.object(upcoming,'_CACHE',cache),patch.object(upcoming.sports_provider,'get',return_value=provider) as get:
            upcoming.run(clock=lambda:NOW)
            get.assert_called_once_with()
        self.assertFalse(late)
        return logs

    def test_cold_failure_survives_a_timer_redraw(self):
        def scenario(w):
            until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'error')
            w.draw()
            self.assertEqual(w.props['state'],'error')
            self.assertNotIn('raw-fixture-details',str(w.props))
        self.exercise(Provider(fail=True),scenario)

    def test_retry_recovers_to_the_list_and_clears_error_text(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching)
            provider.fail=False;provider.games=sm.Sample(now=NOW).upcoming_games()
            w.onClick(page.RETRY);until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(w.props['row.0.title'],'Arsenal vs Chelsea')
            self.assertEqual(w.props['empty.title'],'')
            self.assertFalse(w.failed)
        self.exercise(provider,scenario)
        self.assertEqual(provider.calls,1)

    def test_timer_poll_recovers_after_slow_first_scan(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'error')
            provider.fail=False;provider.games=sm.Sample(now=NOW).upcoming_games()
            w.poll();until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(w.props['row.0.title'],'Arsenal vs Chelsea')
            w.poll();self.assertEqual(provider.calls,1)
        self.exercise(provider,scenario)

    def test_timer_picks_up_new_partial_results_without_forcing_a_scan(self):
        provider=Provider()
        def scenario(w):
            until(lambda:not w.fetching)
            provider.games=sm.Sample(now=NOW).upcoming_games()
            w.poll();until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(provider.calls,0)
        self.exercise(provider,scenario)

    def test_timer_poll_does_not_retry_closed_page(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching)
            w.onClick(page.BACK);w.poll()
            self.assertEqual(provider.calls,0)
        self.exercise(provider,scenario)

    def test_retry_can_finish_successfully_with_no_games(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching)
            provider.fail=False
            w.onClick(page.RETRY);until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'empty')
            self.assertEqual(w.props['subtitle'],'Updated just now')
            w.draw();self.assertEqual(w.props['state'],'empty')
        self.exercise(provider,scenario)

    def test_repeated_failure_keeps_the_recovery_state(self):
        provider=Provider(fail=True)
        def scenario(w):
            until(lambda:not w.fetching)
            w.onClick(page.RETRY);until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'error')
            w.draw();self.assertEqual(w.props['state'],'error')
        self.exercise(provider,scenario)
        self.assertEqual(provider.calls,1)

    def test_empty_refresh_can_reveal_new_games(self):
        provider=Provider()
        def scenario(w):
            until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'empty')
            provider.games=sm.Sample(now=NOW).upcoming_games()
            w.onClick(page.REFRESH);until(lambda:not w.fetching)
            self.assertEqual(w.props['state'],'ready')
            self.assertEqual(w.props['empty.text'],'')
        self.exercise(provider,scenario)

    def test_cached_games_stay_visible_when_refresh_fails(self):
        games=sm.Sample(now=NOW).upcoming_games()
        def scenario(w):
            until(lambda:not w.fetching)
            w.draw()
            self.assertEqual(w.props['state'],'ready')
            self.assertTrue(w.props['subtitle'].startswith('6 games coming up'))
            self.assertFalse(w.props['empty.title'])
        self.exercise(Provider(fail=True),scenario,cache=(games,NOW))

    def test_close_during_retry_does_not_write_to_the_closed_window(self):
        provider=Provider();entered=threading.Event();release=threading.Event()
        games=provider.upcoming_games
        def held():entered.set();release.wait(2);return games()
        provider.upcoming_games=held
        def scenario(w):
            self.assertTrue(entered.wait(1));self.assertEqual(w.props['state'],'loading')
            w.onClick(page.BACK);release.set();until(lambda:not w.fetching)
            self.assertTrue(w.stop.is_set())
        self.exercise(provider,scenario)

    def test_see_leagues_opens_the_leagues_page(self):
        def scenario(w):
            until(lambda:not w.fetching)
            w.onClick(page.LEAGUES)
        import sports_leagues
        with patch.object(sports_leagues,'run') as opened:
            logs=self.exercise(Provider(),scenario)
            opened.assert_called_once()
        self.assertIn('sports: leagues',logs)


class Structure(unittest.TestCase):
    def test_states_have_distinct_actions_registered_fonts_and_generated_icons(self):
        import portrait
        files=page.files(portrait);root=ET.fromstring(files['portrait/'+page.WINDOW])
        for ident in (page.RETRY,page.LEAGUES):
            button=root.find('.//control[@id="%d"]'%ident)
            self.assertGreaterEqual(int(button.findtext('height')),118)
            self.assertGreaterEqual(int(button.findtext('width')),118)
        self.assertEqual(len(root.findall('.//control[@id="%d"]'%page.RETRY)),1)
        self.assertEqual(len(root.findall('.//control[@id="%d"]'%page.LEAGUES)),1)
        names={name for name,_,_ in portrait.FONTS}
        self.assertIn('p_state_title',names)
        for name in ('sports_calendar.png','sports_warning.png'):
            self.assertTrue(files['extras/portrait/'+name].startswith(b'\x89PNG\r\n\x1a\n'))


if __name__=='__main__':unittest.main()
