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
        conv = {'title': 'Lanterns · S1 E1', 'pct': 42, 'state': 'running', 'step': 'Making it start faster', 'tint_now': 'FFBF5AF2'}
        downs = [{'label': 'S2 E48 · Naruto Shippuden', 'label2': 'Downloading · 7.2 MB/s · 1 min', 'row': {'pct': 92}}]
        out = library_status.slim_rows(conv, '4.8 MB/s', '· 6 min left', [], downs)
        self.assertEqual(out['work.status'], 'Making it start faster · 4.8 MB/s · 6 min left')
        self.assertEqual((out['work.num'], out['work.ring'], out['work.pos']), ('42', 'ring_08.png', 'first'))
        self.assertEqual((out['down.0.num'], out['down.0.pos'], out['down.0.tint']), ('92', 'last', 'FF0A84FF'))
        self.assertEqual(out['run.heading'], 'WORKING NOW · 2')
        self.assertEqual(out['lane.0.pos'], '')


if __name__ == '__main__':
    unittest.main()
