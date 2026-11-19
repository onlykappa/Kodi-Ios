"""Sports from JetExtractors (DEC-061, ISSUE-363): JetItems become merged games with sources; slow or failing scrapers never fail the rest; play
descriptors round-trip; the JetProxy path keeps '?' inside the address out of the query."""
import json
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_jet as sj  # noqa: E402
import sports_model as sm  # noqa: E402

NOW = 1763316000


class Link:   # the attributes of jetextractors.models.JetLink that the adapter reads
    def __init__(self, address, name='', links=False):
        self.address, self.name, self.links = address, name, links

    def to_dict(self):
        return {'address': self.address, 'name': self.name}


def item(title, start=None, league=None, status=None, links=None):
    return NS(title=title, links=links if links is not None else [Link('https://x/1', 'Stream 1 [English, HD]')],
              starttime=datetime.fromtimestamp(start) if start else None, league=league, status=status)


class Ext:
    def __init__(self, name, items=None, error=None, delay=0):
        self.name, self.items, self.error, self.delay = name, items or [], error, delay

    def get_items(self):
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.items


def provider(*exts, wait=2):
    return sj.JetProvider(loader=lambda: (list(exts), 'test'), clock=lambda: NOW, wait=wait)


class Parsing(unittest.TestCase):
    def test_titles(self):
        self.assertEqual(sj.teams('Arsenal vs Chelsea'), ('Arsenal', 'Chelsea', 'vs'))
        self.assertEqual(sj.teams('Bills @ Chiefs'), ('Bills', 'Chiefs', 'at'))
        self.assertEqual(sj.teams('Lakers at Celtics'), ('Lakers', 'Celtics', 'at'))
        self.assertIsNone(sj.teams('ESPN HD'))

    def test_leagues_and_quality(self):
        self.assertEqual(sj.league_of('NBA')[:2], ('NBA', 'NBA'))
        self.assertEqual(sj.league_of('English Premier League')[0], 'EPL')
        self.assertEqual(sj.league_of('Padel')[0], 'PADEL')
        self.assertEqual((sj.quality_of('Stream 2 [English, HD, 40 viewers]'), sj.language_of('Stream 2 [English, HD]')), ('720p', 'English'))
        self.assertEqual(sj.quality_of('1080p feed'), '1080p')

    def test_state(self):
        mk = lambda **kw: item('A vs B', **kw)
        self.assertEqual(sj.state_of(mk(), NOW + 3600, NOW), 'upcoming')
        self.assertEqual(sj.state_of(mk(), NOW - 600 - 3600, NOW), 'live')
        self.assertIsNone(sj.state_of(mk(), NOW - 9 * 3600, NOW))
        self.assertEqual(sj.state_of(mk(status='LIVE'), None, NOW), 'live')
        self.assertIsNone(sj.state_of(mk(status='Ended (Nov 1)'), NOW - 100, NOW))
        self.assertIsNone(sj.state_of(mk(), None, NOW))

    def test_live_unknown_scores_are_not_fabricated(self):
        rec = sj.records(item('Arsenal vs Chelsea', NOW - 60, 'Premier League', status='LIVE'), 'fixture', NOW)[0]
        self.assertIsNone(rec['away']['score'])
        self.assertIsNone(rec['home']['score'])

    def test_records_one_per_stream_and_descriptor_roundtrip(self):
        it = item('Arsenal vs Chelsea', NOW + 7200, 'Premier League', links=[Link('https://a/1', 'HD'), Link('https://a/2', 'Stream 2', links=True)])
        recs = sj.records(it, 'Streamed', NOW)
        self.assertEqual(len(recs), 2)
        self.assertEqual((recs[0]['league'], recs[0]['sport'], recs[0]['state']), ('EPL', 'Soccer', 'upcoming'))
        self.assertEqual(json.loads(recs[1]['play'])['l']['address'], 'https://a/2')
        self.assertEqual(sj.records(item('ESPN HD', NOW + 60), 'X', NOW), [])
        self.assertEqual(sj.records(item('A vs B', NOW + 60, links=[]), 'X', NOW), [])


class Provider(unittest.TestCase):
    def test_two_scrapers_one_game_two_sources_and_leagues(self):
        a = Ext('A', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League'), item('Lakers vs Celtics', NOW - 1800, 'NBA', 'LIVE')])
        b = Ext('B', [item('Arsenal FC vs Chelsea FC', NOW + 7200, 'EPL', links=[Link('https://b/1', '1080p')])])
        p = provider(a, b)
        up = p.upcoming_games()
        self.assertEqual(len(up), 1)
        self.assertEqual(len(up[0]['sources']), 2)
        self.assertEqual(up[0]['sources'][0]['tag'], 'best')
        self.assertEqual([g['league'] for g in p.live_games()], ['NBA'])
        self.assertEqual(sorted(l['code'] for l in p.leagues()), ['EPL', 'NBA'])
        self.assertEqual(p.game(up[0]['id'])['id'], up[0]['id'])
        ov = p.overview()
        self.assertEqual((ov['live'], ov['leagues']), (1, 2))

    def test_failing_scraper_does_not_fail_the_rest(self):
        p = provider(Ext('Bad', error=RuntimeError('boom')), Ext('Good', [item('A vs B', NOW + 900, 'NBA')]))
        self.assertEqual(len(p.upcoming_games()), 1)

    def test_nothing_anywhere_says_unavailable(self):
        with self.assertRaises(sm.SportsUnavailable):
            provider(Ext('Bad', error=RuntimeError('boom'))).live_games()
        with self.assertRaises(sm.SportsUnavailable):
            sj.JetProvider(loader=lambda: ([], 'missing'), clock=lambda: NOW, wait=1).live_games()

    def test_slow_scraper_is_left_to_finish_in_the_background(self):
        p = provider(Ext('Fast', [item('A vs B', NOW + 900, 'NBA')]), Ext('Slow', [item('C vs D', NOW + 900, 'NBA')], delay=1.5), wait=0.3)
        self.assertEqual(len(p.upcoming_games()), 1)
        time.sleep(1.6)
        self.assertEqual(len(p.upcoming_games()), 2)


class Playing(unittest.TestCase):
    def test_proxy_path(self):
        path = sj.proxy_path('https://h/live.m3u8?token=a&b=1', {'Referer': 'https://r/'})
        self.assertTrue(path.startswith('plugin://plugin.video.jetproxy/play/https://h/live.m3u8%3Ftoken%3Da%26b%3D1?h='))
        self.assertEqual(sj.proxy_path('https://h/x.m3u8', {}), 'plugin://plugin.video.jetproxy/play/https://h/x.m3u8')

    def test_provider_door_plays_jet_descriptors_only(self):
        import sports_provider
        self.assertEqual(sports_provider.play({'id': 's', 'play': 'sample-play'}), 'sample-play')


class ModulePaths(unittest.TestCase):
    def test_required_modules_are_put_on_the_path(self):   # owner log 916e0a6a: "No module named 'requests'"
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmp:
            def make(id, needs, lib='lib'):
                d = os.path.join(tmp, id)
                os.makedirs(os.path.join(d, lib))
                imports = ''.join('<import addon="%s"/>' % n for n in needs)
                open(os.path.join(d, 'addon.xml'), 'w').write('<addon id="%s"><requires><import addon="xbmc.python"/>%s</requires>'
                                                                '<extension point="xbmc.python.module" library="%s"/></addon>' % (id, imports, lib))
            make('script.module.jetextractors', ['script.module.requests', 'script.module.gone'])
            make('script.module.requests', ['script.module.urllib3'])
            make('script.module.urllib3', [], 'lib')
            before = list(sys.path)
            try:
                seen = sj.add_module_paths('script.module.jetextractors', lambda i: os.path.join(tmp, i) if os.path.isdir(os.path.join(tmp, i)) else None)
                for id in ('script.module.jetextractors', 'script.module.requests', 'script.module.urllib3'):
                    self.assertIn(os.path.join(tmp, id, 'lib'), sys.path)
                self.assertIn('script.module.gone', seen)   # a missing module is skipped, not fatal
            finally:
                sys.path[:] = before



class Window:
    def __init__(self):
        self.p = {}

    def getProperty(self, k):
        return self.p.get(k, '')

    def setProperty(self, k, v):
        self.p[k] = v

    def clearProperty(self, k):
        self.p.pop(k, None)


class Remote(unittest.TestCase):
    """ISSUE-365: JetExtractors runs in a script's main thread; a page only asks and reads."""

    def test_script_publishes_after_each_scraper_and_page_reads_it(self):
        win = Window()
        a = Ext('A', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League')])
        runner = sj.JetProvider(loader=lambda: ([a], 'test'), clock=lambda: NOW,
                                publish=lambda d: win.setProperty(sj.DATA, json.dumps(d)))
        runner._start().wait(3)
        time.sleep(0.2)
        data = json.loads(win.getProperty(sj.DATA))
        self.assertTrue(data['done'])
        self.assertEqual(len(data['records']), 1)
        launched = []
        page = sj.JetProvider(remote=True, window=win, clock=lambda: NOW, wait=1, launch=lambda *a: launched.append(a))
        self.assertEqual(len(page.upcoming_games()), 1)
        self.assertEqual(launched, [])   # fresh data: the script is not started again

    def test_incomplete_snapshot_is_returned_without_waiting_for_other_scrapers(self):
        win = Window()
        a = Ext('A', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League')])
        runner = sj.JetProvider(loader=lambda: ([a], 'test'), clock=lambda: NOW,
                                publish=lambda d: win.setProperty(sj.DATA, json.dumps(d)))
        runner._start().wait(3)
        snapshot = json.loads(win.getProperty(sj.DATA)); snapshot['done'] = False
        win.setProperty(sj.DATA, json.dumps(snapshot))
        page = sj.JetProvider(remote=True, window=win, clock=lambda: NOW, wait=2, launch=lambda *a: None)
        from unittest.mock import patch
        with patch.object(sj.time, 'sleep') as sleep:
            page.refresh()
            self.assertEqual(len(page.upcoming_games()), 1)
            self.assertGreater(page.overview()['updated'], 0)
            sleep.assert_not_called()

    def test_remote_snapshot_reuses_merge_and_invalidates_when_records_change(self):
        from unittest.mock import patch
        win = Window()
        a = Ext('A', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League')])
        runner = sj.JetProvider(loader=lambda: ([a], 'test'), clock=lambda: NOW,
                                publish=lambda d: win.setProperty(sj.DATA, json.dumps(d)))
        runner._start().wait(3)
        page = sj.JetProvider(remote=True, window=win, clock=lambda: NOW, wait=1, launch=lambda *a: None)
        with patch.object(page, '_games', wraps=page._games) as merge:
            games = page.upcoming_games(); games[0]['away']['name'] = 'changed by caller'
            self.assertNotEqual(page.upcoming_games()[0]['away']['name'], 'changed by caller')
            page.overview(); page.leagues()
            self.assertEqual(merge.call_count, 1)
            data = json.loads(win.getProperty(sj.DATA)); data['at'] += 1
            win.setProperty(sj.DATA, json.dumps(data))
            page.upcoming_games()
            self.assertEqual(merge.call_count, 2)

    def test_page_starts_the_script_once_and_reports_loading(self):
        win, launched = Window(), []
        page = sj.JetProvider(remote=True, window=win, clock=lambda: NOW, wait=0.1, launch=lambda *a: launched.append(a))
        with self.assertRaises(sm.SportsUnavailable):
            page.live_games()
        with self.assertRaises(sm.SportsUnavailable):
            page.live_games()
        self.assertEqual(launched, [('sports_jet_run',)])   # the second page load finds it running

    def test_script_keeps_schedule_available_when_crew_is_missing(self):
        win = Window()
        from unittest.mock import patch
        with patch('sports_crew_routes.schedule', return_value=[]), patch('sports_independent.StreamsCenter.get_items', side_effect=AssertionError('independent called')), patch.object(sj, 'import_jet', side_effect=AssertionError('Jet called')), patch.dict(sys.modules, {'xbmcgui': NS(Window=lambda i: win), 'xbmcaddon': NS(Addon=lambda *a, **k: None), 'xbmcvfs': NS(translatePath=lambda p: __import__('tempfile').gettempdir()+'/kodi-sports-host-test')}):
            sj.run_script([], window=win)
        data = json.loads(win.getProperty(sj.DATA))
        self.assertTrue(data['done'])
        self.assertIn('not installed', data['reason'])
        page = sj.JetProvider(remote=True, window=win, clock=lambda: data['at'], wait=0.1, launch=lambda *a: None)
        self.assertEqual(data['schedule'], [])
        self.assertEqual(page.live_games(), [])

    def test_a_tap_leaves_the_source_and_starts_the_play_script(self):
        win, launched = Window(), []
        sj.play_request({'id': 's1', 'addon': 'A', 'quality': '720p', 'language': 'English', 'play': '{"e":"A"}'}, window=win,
                        launch=lambda *a: launched.append(a))
        self.assertEqual(launched[0][:2], ('sports_jet_run', 'play'))
        key = launched[0][2]
        self.assertEqual(json.loads(win.getProperty(sj.PLAY + key))['play'], '{"e":"A"}')


class NamedAddon(unittest.TestCase):
    def test_bare_addon_names_us_while_active_and_is_restored(self):   # ISSUE-365
        class Strict:
            def __init__(self, id=None):
                if not id:
                    raise RuntimeError('No valid addon id could be obtained')
                self.id = id
        module = NS(Addon=Strict)
        with self.assertRaises(RuntimeError):
            module.Addon()
        with sj.named_addon(module):
            self.assertEqual(module.Addon().id, 'service.kodi.ios.bootstrap')
            self.assertEqual(module.Addon('script.module.x').id, 'script.module.x')
            self.assertEqual(module.Addon(id='y').id, 'y')
        self.assertIs(module.Addon, Strict)


class LivePageDoesNotPlayTrue(unittest.TestCase):
    def test_live_page_skips_playing_when_the_script_already_started_it(self):   # ISSUE-366
        text = (ROOT / 'migration/bundled-bootstrap/sports_live.py').read_text()
        self.assertIn("isinstance(path, str)", text)


class Fallback(unittest.TestCase):
    """Build 557 log: Embedsport2's server failed for every game while other add-ons list the same match; quick taps raced on one property."""

    def test_merge_keeps_the_other_addons_streams_as_alternatives(self):
        a = Ext('Embedsport2', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League', links=[Link('https://a/1')])])
        b = Ext('ReedStreams', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League', links=[Link('https://b/1')])])
        src = provider(a, b).upcoming_games()[0]['sources']
        self.assertEqual(len(src), 1)
        self.assertEqual(src[0]['addon'], 'Embedsport2')
        self.assertEqual([json.loads(v)['e'] for v in src[0]['alts']], ['ReedStreams'])

    def test_play_tries_the_next_add_when_the_first_cannot_open(self):
        tried = []
        original = sj.play_one
        def fake(value, logger=None):
            tried.append(json.loads(value)['e'])
            if json.loads(value)['e'] != 'Reed':
                raise RuntimeError('no playable stream behind this source')
            return True
        sj.play_one = fake
        try:
            self.assertTrue(sj.play({'play': '{"e":"Embed"}', 'alts': ['{"e":"Bad"}', '{"e":"Reed"}']}, logger=lambda t: None))
            self.assertEqual(tried, ['Embed', 'Bad', 'Reed'])
            with self.assertRaises(RuntimeError):
                sj.play({'play': '{"e":"Embed"}', 'alts': []}, logger=lambda t: None)
        finally:
            sj.play_one = original

    def test_two_quick_taps_do_not_share_a_property(self):
        win, launched = Window(), []
        for n in (1, 2):
            sj.play_request({'id': 's%d' % n, 'play': '{"e":"A%d"}' % n}, window=win, launch=lambda *a: launched.append(a))
            time.sleep(0.005)
        self.assertNotEqual(launched[0][2], launched[1][2])
        self.assertEqual(json.loads(win.getProperty(sj.PLAY + launched[0][2]))['id'], 's1')


class LiveClockStamps(unittest.TestCase):
    def test_a_clock_that_moved_is_running_and_one_that_did_not_is_stopped(self):
        import sports_jet
        first = sports_jet.annotate_clocks([{'id': 'g', 'clock_secs': 500.0, 'clock_state': 'STATUS_IN_PROGRESS'}], [], now=1000)
        self.assertEqual((first[0]['clock_at'], first[0]['clock_running']), (1000, True))   # a first look: running while ESPN says in progress
        moved = sports_jet.annotate_clocks([{'id': 'g', 'clock_secs': 488.0}], first, now=1012)
        self.assertTrue(moved[0]['clock_running'])
        stopped = sports_jet.annotate_clocks([{'id': 'g', 'clock_secs': 488.0}], moved, now=1030)
        self.assertFalse(stopped[0]['clock_running'])   # same seconds 18 s later: a timeout or a stoppage
        resumed = sports_jet.annotate_clocks([{'id': 'g', 'clock_secs': 470.0}], stopped, now=1048)
        self.assertTrue(resumed[0]['clock_running'])
        quick = sports_jet.annotate_clocks([{'id': 'g', 'clock_secs': 488.0}], moved, now=1013)
        self.assertTrue(quick[0]['clock_running'])      # under 3 s apart tells nothing: keep what was known
        stoppage = sports_jet.annotate_clocks([{'id': 'h', 'clock_secs': 60.0, 'clock_state': 'STATUS_END_PERIOD'}], [], now=1000)
        self.assertFalse(stoppage[0]['clock_running'])
        self.assertNotIn('clock_at', sports_jet.annotate_clocks([{'id': 'x'}], [], now=1)[0])   # soccer and baseball carry no seconds

    def test_scores_are_asked_for_often_and_trusted_briefly(self):
        import sports_jet
        self.assertLessEqual(sports_jet.SCORE_EVERY, 10)
        self.assertLessEqual(sports_jet.SCORE_STALE, 60)


if __name__ == '__main__':
    unittest.main()
