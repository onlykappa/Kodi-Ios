"""Roadmap 3.1: when iOS takes the silent audio away, the keep-alive asks again every tick, tells the owner once if it
stays away, and logs how long recovery took."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import background


class Run(object):
    """Drives background.watch with a script of (work reason, audio status) per tick, one second per tick."""

    def __init__(self, script, patience=180):
        self.script, self.i, self.t = script, 0, 0.0
        self.keeps, self.logs, self.told = [], [], []
        background.watch(self.keeps.append, lambda: self.script[min(self.i, len(self.script) - 1)][0], self.wait, self.logs.append,
                         status=lambda: self.script[min(self.i, len(self.script) - 1)][1], notify=lambda a, b: self.told.append((a, b)),
                         clock=lambda: self.t, patience=patience)

    def wait(self, seconds):
        self.i += 1
        self.t += 1.0
        return self.i >= len(self.script)


class Recovery(unittest.TestCase):
    def test_every_tick_with_work_asks_the_framework_to_restart_the_silence(self):
        run = Run([('upload', 2), ('upload', -2), ('upload', -2), ('upload', 2), ('', 0)])
        self.assertEqual(run.keeps, [1, 1, 1, 1, 0])         # asked on each tick, released when the work ends

    def test_a_short_interruption_is_only_logged_and_its_recovery_timed(self):
        run = Run([('upload', 2)] + [('upload', -2)] * 30 + [('upload', 2)] * 2)
        self.assertEqual(run.told, [])
        self.assertTrue(any('audio interrupted by iOS' in line for line in run.logs))
        self.assertTrue(any('silent audio running again after 30 s' in line for line in run.logs))

    def test_a_long_interruption_tells_the_owner_once(self):
        run = Run([('download', -2)] * 400, patience=180)
        self.assertEqual(len(run.told), 1)
        title, text = run.told[0]
        self.assertEqual(title, 'Background work paused')
        self.assertIn('carry on when you open Kodi', text)

    def test_a_failed_start_counts_the_same_way(self):
        self.assertEqual(len(Run([('download', -1)] * 200, patience=100).told), 1)

    def test_a_second_interruption_after_recovery_is_told_again(self):
        script = [('upload', -2)] * 200 + [('upload', 2)] * 3 + [('upload', -2)] * 200
        self.assertEqual(len(Run(script, patience=100).told), 2)

    def test_nothing_is_told_when_no_work_waits(self):
        self.assertEqual(Run([('', -2)] * 400).told, [])

    def test_a_failing_notice_never_stops_the_keep_alive(self):
        def boom(a, b):
            raise RuntimeError('synthetic')
        ticks = [0]

        def wait(seconds):
            ticks[0] += 1
            return ticks[0] >= 300
        keeps = []
        background.watch(keeps.append, lambda: 'upload', wait, status=lambda: -2, notify=boom, clock=lambda: float(ticks[0]), patience=10)
        self.assertGreaterEqual(len(keeps), 299)

    def test_the_service_passes_the_notice_to_the_keep_alive(self):
        source = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('"notify":lambda title,text:notices.note("info",title,text)', source)


if __name__ == '__main__':
    unittest.main()
