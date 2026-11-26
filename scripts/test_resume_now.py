"""Library status says "Paused for playback" with nothing playing: Resume now (owner, 2026-11-25, build 698 log 8e545f74, screenshot IMG_0686)."""
import sys, unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import slowdown as sd


class Window(dict):
    def getProperty(self, k): return self.get(k, '')
    def setProperty(self, k, v): self[k] = v
    def clearProperty(self, k): self.pop(k, None)


OPEN = '{"t": 1000.0, "via": "elementum"}'


class Force(unittest.TestCase):
    def setUp(self): sd._play.update(video_since=None, asked=0.0)
    def test_an_opening_mark_that_never_became_a_video_holds_work_until_released(self):
        self.assertEqual(sd.play_reason(False, False, False, OPEN, now=1010.0), 'buffering')                  # the 120 s hold of build 698
        window = Window({'KodiIOS.Open': OPEN, 'KodiIOS.OpenResolved': '1', 'KodiIOS.OpenWanted': '1'})
        until = sd.force_run(window, now=1010.0)
        self.assertEqual(until, 1010.0 + sd.FORCE_SECONDS)
        self.assertEqual({k for k in sd.MARKS if k in window}, set())                                         # the marks are gone
        self.assertEqual(sd.play_reason(False, False, False, OPEN, now=1011.0, forced=sd.forced_until(window[sd.FORCE_PROPERTY])), '')
    def test_the_release_never_overrides_a_video_a_cast_or_a_stalled_buffer(self):
        forced = 2000.0
        self.assertEqual(sd.play_reason(True, False, False, OPEN, now=1500.0, forced=forced), 'airplay')
        self.assertEqual(sd.play_reason(False, True, False, OPEN, now=1500.0, forced=forced), 'buffering')
        self.assertEqual(sd.play_reason(False, False, True, '', now=1500.0, forced=forced), 'video')
    def test_it_ends_by_itself(self):
        self.assertEqual(sd.play_reason(False, False, False, OPEN, now=1010.0, forced=1009.0), 'buffering')   # an old force does nothing
        self.assertEqual(sd.forced_until(''), 0.0); self.assertEqual(sd.forced_until('x'), 0.0); self.assertEqual(sd.forced_until('12.5'), 12.5)


class Wiring(unittest.TestCase):
    def test_download_only_leaves_no_opening_mark_and_the_service_passes_the_force(self):
        cloud = (ROOT / 'migration/bundled-bootstrap/resources/lib/elementum_cloud.py').read_text()
        self.assertLess(cloud.index("if mode != 1 and home is not None:"), cloud.index("if mode < 0:return True"))
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertEqual(service.count('forced=slowdown.forced_until(xbmcgui.Window(10000).getProperty(slowdown.FORCE_PROPERTY))'), 2)
    def test_the_working_now_card_has_the_link_only_while_work_waits_and_nothing_plays(self):
        import library_page as lp
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/library_page.py').read_text()
        self.assertEqual(lp.RESUME, 9007); self.assertIn("u.has('run.resume')", text); self.assertIn('!Player.HasVideo', text)
        status = (ROOT / 'migration/bundled-bootstrap/library_status.py').read_text()
        self.assertIn("out['run.resume']='true' if any('for playback' in", status)
        self.assertIn('slowdown.force_run(xbmcgui.Window(10000))', status)


if __name__ == '__main__':
    unittest.main()
