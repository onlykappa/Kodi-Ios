"""ISSUE-345 (owner logs 53a92f39, a83e06c7: Play on TV pressed again and again while nothing showed): the owner-approved
mockup C, a slim banner at the top of the video from the moment a TV is picked: the step, a thin bar and Stop; then
"Playing on your TV" for two seconds. A second press only leaves it there."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
sys.dont_write_bytecode = True
import airplay_flow as af  # noqa: E402


class Words(unittest.TestCase):
    def test_each_step_has_its_line_and_bar(self):
        for stage, bar in (('opening', '0'), ('waiting_tv', '35'), ('connecting', '70')):   # a step starts no lower than its floor; the bar then moves
            v = af.banner_view(stage)
            self.assertEqual((v['bar'], v['stop']), (bar, 'Stop'))
            self.assertTrue(v['sub'].startswith('Step '))
        self.assertIn('Converting', af.banner_view('opening', converting=True)['title'])

    def test_the_bar_follows_the_whole_wait_on_one_curve_and_never_goes_back(self):
        # Owner, build 549: it "gets to about 50 % then immediately plays". One curve for the whole start, tuned to the recent starts.
        last = 0
        for t in range(0, 90):
            pct = af.progress_pct(t, '', 'opening', last)
            self.assertGreaterEqual(pct, last)
            self.assertLessEqual(pct, 97)
            last = pct
        self.assertEqual(af.progress_pct(0), 0)
        self.assertGreater(af.progress_pct(10), af.progress_pct(3))
        # a start expected to take 6 s is at about 80 % at 6 s; one expected to take 25 s is not
        self.assertGreaterEqual(af.progress_pct(6, expected=6), 75)
        self.assertLessEqual(af.progress_pct(6, expected=25), 45)
        self.assertLessEqual(af.progress_pct(3600), 97)   # never full before the TV plays

    def test_the_native_phase_lifts_the_bar_and_names_what_is_happening(self):
        self.assertGreaterEqual(af.progress_pct(1, 'inspecting'), 15)
        self.assertGreaterEqual(af.progress_pct(1, 'ready'), 40)
        self.assertGreaterEqual(af.progress_pct(1, 'connecting'), 70)
        self.assertGreaterEqual(af.progress_pct(1, '', 'waiting_tv'), 35)
        self.assertEqual(af.progress_pct(1, 'inspecting', last=60), 60)   # never below what was shown
        self.assertIn('Reading the video', af.banner_view('opening', phase='inspecting')['sub'])
        self.assertTrue(af.banner_view('opening', phase='inspecting')['sub'].startswith('Step 1 of 3'))
        self.assertIn('Reading the video', af.banner_view('opening', tv='Living Room Roku', phase='inspecting')['sub'])
        self.assertNotIn('usually a few seconds', af.banner_view('opening', phase='ready')['sub'])
        self.assertIn('usually a few seconds', af.banner_view('opening')['sub'])   # before any phase is known

    def test_the_next_start_is_expected_to_take_about_as_long_as_this_one_did(self):
        self.assertEqual(af.next_expected(25, 14), round(0.6 * 25 + 0.4 * 14, 1))
        self.assertEqual(af.next_expected(0.5, 14), round(max(3.0, 0.6 * 0.5 + 0.4 * 14), 1))   # never below 3 s
        self.assertEqual(af.next_expected(999, 14), 60.0)
        self.assertEqual(af.next_expected('x', 14), 14)

    def test_the_controller_ticks_the_bar_twice_a_second_and_a_failing_tick_never_stops_the_start(self):
        import cast
        seen = []
        phases = iter(['opening', 'inspecting', 'inspecting', 'ready', 'connecting'])
        waits = []

        def network():
            return {'phase': next(phases, 'connecting'), 'expected': True, 'start_age_s': 1, 'connect_age_s': 0}

        def wait(seconds):
            waits.append(seconds)
            return len(waits) >= 5   # the user stops after five polls

        def tick(group, seconds, phase):
            seen.append((group, round(seconds, 1), phase))
            if len(seen) == 2:
                raise RuntimeError('display problem')
        outcome = cast.airplay_outcome(lambda: 0, wait, network=network, stage=lambda *a: None, tick=tick)
        self.assertEqual(outcome, 'aborted')
        self.assertEqual(waits, [0.5] * 5)
        self.assertEqual([t[2] for t in seen], ['opening', 'inspecting', 'inspecting', 'ready', 'connecting'])
        self.assertEqual(seen[0][0], 'opening')

    def test_done_says_where_the_tv_starts_and_has_no_stop(self):
        d = af.banner_done(1623.8)
        self.assertEqual((d['title'], d['sub'], d['stop'], d['bar']), ('Playing on your TV', 'From 27:03', '', ''))
        self.assertEqual(af.banner_done(3725)['sub'], 'From 1:02:05')


class Window(unittest.TestCase):
    def test_the_page(self):
        xml = af.banner_page()
        root = ET.fromstring(xml.split('\n', 2)[2])
        ids = {c.get('id') for c in root.iter('control') if c.get('id')}
        self.assertEqual(ids, {str(af.BANNER_BAR), str(af.BANNER_STOP)})
        self.assertNotIn('!!', xml)
        self.assertNotIn('!(', xml)
        pages = (BOOT / 'resources/lib/pages.py').read_text()
        self.assertIn("'1080i/IOSTVBanner.xml':_airplay_flow().banner_page()", pages)


class Wiring(unittest.TestCase):
    src = (BOOT / 'cast.py').read_text()

    def test_shown_before_the_source_is_opened(self):
        start = self.src.index('def send_airplay(')
        self.assertLess(self.src.index('_BANNER[0]=Banner(xbmc,_g)', start), self.src.index('remote_media.acquire(', start))

    def test_a_second_press_never_stops_and_shows_no_notice(self):
        self.assertNotIn("dialog.notification('Play on TV','Stopped'", self.src)
        self.assertNotIn('Still connecting to the TV', self.src)
        self.assertNotIn('tap Play on TV again to stop', self.src)

    def test_playing_then_two_seconds_then_gone(self):
        self.assertIn('_BANNER[0].done(at);_BANNER[0]=None', self.src)
        self.assertIn('self.apply(self.flow.banner_done(at,tv=self.tv));self.xbmc.sleep(2000);self.close()', self.src)


class NoVideoOnScreen(unittest.TestCase):
    """ISSUE-348 (owner screenshot IMG_0156): the landscape card drawn stretched over the upright app."""
    src = (BOOT / 'cast.py').read_text()

    def test_the_problem_is_asked_in_the_portrait_sheet(self):
        spec, actions = af.sheet_spec(af.problem_view('slow_source', 'Ep', busy='Interstellar is uploading'))
        self.assertEqual(spec['heading'], 'The movie took too long to load')
        self.assertTrue(spec['sub'].endswith('took too long for playback to start.'))
        self.assertIn('Try again to reconnect', spec['foot'])
        self.assertEqual(actions, ['retry'])
        self.assertEqual(spec['button'], 'Not now')   # no video on screen to keep watching
        spec, actions = af.sheet_spec(af.problem_view('unreachable', 'Ep', settings=True))
        self.assertEqual(actions, ['settings', 'retry'])
        self.assertEqual(spec['button'], 'Cancel')
        self.assertIn('Local Network is on for Kodi (Settings › Kodi)', spec['foot'])
        spec, actions = af.sheet_spec(af.problem_view('mirroring', 'Ep', reason='Not this one.'))
        self.assertEqual((actions, spec['button']), ([], 'OK'))

    def test_the_card_and_the_banner_only_over_the_video(self):
        self.assertIn("xbmc.getCondVisibility('Window.IsVisible(fullscreenvideo)')", self.src)
        ask = self.src[self.src.index(' def ask(self,props,monitor):'):self.src.index(' def shown(self):')]
        self.assertLess(ask.index('if not video_on_screen(self.xbmc):'), ask.index('if self.win is not None:'))
        self.assertIn('choice_sheet.choose(spec,xbmcgui=self.xbmcgui,xbmc=self.xbmc)', ask)
        banner = self.src[self.src.index('class Banner:'):self.src.index('class FlowUI:')]
        self.assertIn('if not video_on_screen(xbmc):return', banner)
        self.assertIn('if self.win is not None and not video_on_screen(self.xbmc):', banner)

    def test_long_titles_wrap_in_the_sheet(self):
        import choice_sheet
        self.assertTrue(choice_sheet.tall({'label': 'Pause uploads and try again', 'tint': 'FFFF9F0A'}))


class RokuToo(unittest.TestCase):
    """Owner (2026-11-15): "make airplay work seemless on any device mainly roku": a TV's own player (Roku, DLNA,
    Chromecast) gets the banner too, in two steps and with the TV's name."""
    src = (BOOT / 'cast.py').read_text()

    def test_two_steps_with_the_tvs_name(self):
        self.assertEqual(af.banner_view('opening', tv='Living Room Roku')['sub'], 'Step 1 of 2 · usually a few seconds')
        v = af.banner_view('connecting', tv='Living Room Roku')
        self.assertEqual((v['title'], v['sub']), ('Waiting for your TV to start playing', 'Step 2 of 2 · Living Room Roku'))
        self.assertEqual(af.banner_done(65, tv='Living Room Roku')['sub'], 'Living Room Roku · From 1:05')
        self.assertEqual(af.banner_view('connecting')['sub'], 'Step 3 of 3 · up to 15 s')   # AirPlay unchanged

    def test_the_tv_route_shows_it_and_guards_a_second_tap(self):
        send = self.src[self.src.index('def send('):self.src.index('def _send_tv(')]
        self.assertIn("_BANNER[0]=Banner(xbmc,_g,tv.get('name') or 'your TV')", send)
        self.assertIn('setProperty(TV_STARTING', send)
        self.assertIn('clearProperty(TV_STARTING)', send)
        tv = self.src[self.src.index('def _send_tv('):]
        self.assertLess(tv.index('_BANNER[0].done('), tv.index("player.stop();notices.note('info'"))

    def test_a_roku_handing_over_to_airplay_keeps_one_banner(self):
        start = self.src.index('def send_airplay(')
        self.assertLess(self.src.index('if _BANNER[0]:_BANNER[0].close()', start), self.src.index('_BANNER[0]=Banner(xbmc,_g)', start))


if __name__ == '__main__':
    unittest.main()
