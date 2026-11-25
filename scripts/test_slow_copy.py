"""ISSUE-484 (owner log 9ba9b5b5): a slow upload line says so, and a copy crawling on cellular waits for Wi-Fi."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration' / 'bundled-bootstrap' / 'resources' / 'lib'))
import debrid_drive, work_state

MB = 1048576


class SlowCellular(unittest.TestCase):
    def test_waits_only_after_a_slow_stretch(self):
        s = {}
        self.assertFalse(debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 1000))
        self.assertFalse(debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 1100))   # under 3 min
        self.assertTrue(debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 1190))

    def test_fast_cellular_keeps_going(self):
        s = {}
        debrid_drive.slow_cellular(s, 'cellular', 3 * MB, 0)
        self.assertFalse(debrid_drive.slow_cellular(s, 'cellular', 3 * MB, 600))

    def test_stays_held_until_the_link_changes(self):
        s = {}
        debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 0)
        self.assertTrue(debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 200))
        self.assertTrue(debrid_drive.slow_cellular(s, 'cellular', 0, 300))
        self.assertFalse(debrid_drive.slow_cellular(s, 'wifi', 0.4 * MB, 400))
        self.assertFalse(debrid_drive.slow_cellular(s, 'cellular', 0.1 * MB, 410))    # a new stay starts its own clock

    def test_no_rate_yet_is_not_slow(self):
        s = {}
        debrid_drive.slow_cellular(s, 'cellular', 0, 0)
        self.assertFalse(debrid_drive.slow_cellular(s, 'cellular', 0, 999))


class SlowLine(unittest.TestCase):
    def job(self, rate, eta):
        return {'kind': 'copy', 'state': work_state.COPYING if hasattr(work_state, 'COPYING') else 'copying',
                'step': 'Copying', 'rate': rate, 'eta_s': eta}

    def test_long_slow_copy_is_explained(self):
        self.assertTrue(work_state.slow_line(self.job(0.4 * MB, 2400)))
        self.assertIn('slow upload line', work_state.line(dict(self.job(0.4 * MB, 2400))))

    def test_short_or_fast_copy_is_not(self):
        self.assertFalse(work_state.slow_line(self.job(0.4 * MB, 300)))
        self.assertFalse(work_state.slow_line(self.job(5 * MB, 4000)))
        self.assertFalse(work_state.slow_line(self.job(0, 4000)))
        self.assertFalse(work_state.slow_line({'kind': 'convert', 'rate': 0.4 * MB, 'eta_s': 4000}))

    def test_hold_words(self):
        self.assertIn('too slow', work_state.SLOW_CELL_WAIT)


if __name__ == '__main__':
    unittest.main()
