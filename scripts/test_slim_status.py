"""ISSUE-292 (DEC-051 board A round 2): Library status lists every running job as one slim row of one grouped list."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
import library_page  # noqa: E402
import portrait  # noqa: E402


class Slim(unittest.TestCase):
    def test_page_has_slim_rows_for_every_slot(self):
        xml = library_page.page(portrait)
        for k, ident in library_page.RUN_SLOTS:
            self.assertIn('Window().Property(%sring)' % k, xml)
            self.assertIn('id="%d"' % ident, xml)
            for tl in (1, 2):
                for sl in (1, 2):
                    self.assertIn('String.IsEqual(Window().Property(%stl),%d) + String.IsEqual(Window().Property(%ssl),%d)' % (k, tl, k, sl), xml)
        self.assertNotIn('Window().Property(work.eyebrow)', xml)   # the big card is gone
        self.assertNotIn('!(', xml)
        self.assertLess(library_page.slim_height(1, 1), 140)        # about 47 pt

    def test_model(self):
        sys.path.insert(0, str(BOOT))
        try:
            import library_status
        except Exception as error:
            self.skipTest('needs Kodi: %s' % error)
        conv = {'title': 'Lanterns · S1 E1', 'pct': 42, 'state': 'running', 'step': 'Making it start faster', 'tint_now': 'FFBF5AF2',
                'rate': 4.8 * 1024 * 1024, 'eta_s': 360}
        lane = {'title': 'Naruto Shippuden · S1 E6', 'pct': 63, 'state': 'running', 'step': 'Making it start faster',
                'rate': 4.8 * 1024 * 1024, 'eta_s': 120}
        downs = [{'label': 'S2 E48 · Naruto Shippuden', 'label2': 'Downloading', 'row': {'pct': 92}}]
        jobs = [{'title': 'S2 E48 · Naruto Shippuden', 'state': 'running', 'step': 'Downloading', 'rate': 7.2 * 1024 * 1024, 'eta_s': 60}]
        out = library_status.slim_rows(library_status.slim_slots(conv, [lane], downs, jobs))
        # Owner (build 442): every row reads like the first, with its speed and time left.
        for k in ('work.', 'lane.0.', 'down.0.'):
            self.assertRegex(out[k + 'status'], r' · [\d.]+ MB/s · .*left$', k)
            self.assertEqual(out[k + 'sl'], '1', out[k + 'status'])       # one line: the rows are even
        self.assertEqual((out['work.num'], out['work.ring'], out['work.pos']), ('42', 'ring_08.png', 'first'))
        self.assertEqual((out['down.0.num'], out['down.0.pos'], out['down.0.tint']), ('92', 'last', 'FF0A84FF'))
        self.assertEqual(out['run.heading'], 'WORKING NOW · 3')
        self.assertEqual(out['lane.1.pos'], '')

    def test_time_left_from_progress(self):
        sys.path.insert(0, str(BOOT))
        try:
            import library_status
        except Exception as error:
            self.skipTest('needs Kodi: %s' % error)
        j = {'title': 'Lane only', 'pct': 20}
        library_status.with_eta(j, now=100)
        out = library_status.with_eta(dict(j, pct=30), now=120)        # 10 % in 20 s: 70 % takes 140 s
        self.assertAlmostEqual(out['eta_s'], 140)

    def test_width_estimate(self):
        import notifications_skin as ns
        self.assertEqual(ns.lines_in('Making it start faster · 4.8 MB/s · 6 min left', 30, library_page.SLIM_TEXT_W, 2), 1)
        self.assertEqual(ns.lines_in('WWWW ' * 12, 30, library_page.SLIM_TEXT_W, 2), 2)
        self.assertEqual(ns.lines_in('', 30, 100, 2), 0)

if __name__ == '__main__':
    unittest.main()
