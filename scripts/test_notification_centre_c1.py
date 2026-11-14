"""C1 (owner, 2026-11-14, approved build442-mockups.html): the notification centre's rows are as tall as their content,
repeats fold into one row, Today and Earlier are separate cards, nothing is cut off."""
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
sys.path.insert(0, str(BOOT))
import notifications_skin as ns  # noqa: E402


class Lines(unittest.TestCase):
    def test_word_wrap_count(self):
        self.assertEqual(ns.lines('', 10, 3), 0)
        self.assertEqual(ns.lines('short', 10, 3), 1)
        self.assertEqual(ns.lines('aaaa bbbb cccc', 10, 3), 2)
        self.assertEqual(ns.lines('x ' * 200, 10, 4), 4)

    def test_every_height_has_a_part(self):
        import portrait
        xml = portrait.notifications_page() if hasattr(portrait, 'notifications_page') else ns.page(type('T', (), vars(portrait)))
        for n in (1, 15):
            for tl in (1, 2, 3):
                self.assertIn('String.IsEqual(Window().Property(msg.%d.tl),%d)' % (n, tl), xml)
            for ll in (1, 2, 3, 4):
                self.assertIn('String.IsEqual(Window().Property(msg.%d.ll),%d)' % (n, ll), xml)
        self.assertNotIn('!(', xml)          # Kodi groups conditions with [ ], not ( )
        self.assertNotIn('…', xml)


class Model(unittest.TestCase):
    def setUp(self):
        try:
            import notifications  # noqa: F401
        except Exception as error:   # needs Kodi stubs
            self.skipTest('notifications needs Kodi: %s' % error)
        self.n = notifications

    def test_fold_sections_and_positions(self):
        now = time.time()
        items = [{'id': '1', 'time': now - 60, 'kind': 'drive', 'title': 'Saved to Google Drive', 'text': 'A'},
                 {'id': '2', 'time': now - 70, 'kind': 'general', 'title': 'Add-ons put back', 'text': 'x', 'was_read': True},
                 {'id': '3', 'time': now - 80, 'kind': 'general', 'title': 'Add-ons put back', 'text': 'x', 'was_read': True},
                 {'id': '4', 'time': now - 3 * 86400, 'kind': 'download', 'title': 'Old', 'text': 'y'}]
        props, shown = self.n.message_properties(items, 'all', now=now)
        self.assertEqual(len(shown), 3)
        self.assertEqual(props['msg.2.count'], '×2')
        self.assertEqual((props['msg.1.section'], props['msg.2.section'], props['msg.3.section']), ('TODAY', '', 'EARLIER'))
        self.assertEqual((props['msg.1.pos'], props['msg.2.pos'], props['msg.3.pos']), ('first', 'last', 'only'))
        self.assertEqual(props['msg.1.tl'], '1')
        self.assertEqual(props['msg.1.ll'], '1')


if __name__ == '__main__':
    unittest.main()
