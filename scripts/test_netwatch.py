"""ISSUE-271 (owner logs 4e5fb2dd / 18a4f9c7, build 424): quicker, smoother recovery when switching Wi-Fi <-> cellular."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import netwatch  # noqa: E402
import driveupload  # noqa: E402


class Watcher(unittest.TestCase):
    def setUp(self):
        netwatch.reset()
        netwatch._state['started'] = True     # no thread in tests: readings are fed by hand

    def test_a_switch_counts_once_it_is_seen_twice_and_never_for_no_address(self):
        self.assertFalse(netwatch.observe('wifi'))
        g = netwatch.generation()
        self.assertFalse(netwatch.observe('other'))          # the moment between networks
        self.assertFalse(netwatch.observe('cellular'))       # seen once
        self.assertTrue(netwatch.observe('cellular'))        # seen twice: changed
        self.assertEqual((netwatch.link(), netwatch.generation()), ('cellular', g + 1))
        self.assertFalse(netwatch.observe('wifi'));self.assertFalse(netwatch.observe('cellular'))   # a flicker
        self.assertEqual(netwatch.generation(), g + 1)


class Memory(unittest.TestCase):
    def setUp(self):
        driveupload.LinkMemory.clear()

    def test_each_link_starts_at_what_worked_on_it(self):
        big = 32 * 1024 * 1024
        self.assertEqual(driveupload.LinkMemory.start('cellular', big, big), (4 * 1024 * 1024, 0.0))   # never seen: small
        self.assertEqual(driveupload.LinkMemory.start('wifi', big, big), (big, 0.0))
        driveupload.LinkMemory.remember('cellular', 2 * 1024 * 1024, 900000.0)
        driveupload.LinkMemory.remember('wifi', 16 * 1024 * 1024, 9000000.0)
        self.assertEqual(driveupload.LinkMemory.start('cellular', big, big), (2 * 1024 * 1024, 900000.0))
        self.assertEqual(driveupload.LinkMemory.start('wifi', big, big)[0], 16 * 1024 * 1024)

    def test_the_copy_run_ends_at_the_next_piece_and_starts_again_at_once(self):
        src = (LIB / 'debrid_drive.py').read_text()
        self.assertIn('and not link_moved(netgen)', src)
        i = src.index('except driveupload.Stop:\n        if link_moved(netgen):')
        self.assertIn('return 1', src[i:i + 600])
        self.assertIn('LinkMemory.start(link', (LIB / 'driveupload.py').read_text())
        self.assertIn('netwatch.start()', (LIB.parents[1] / 'service.py').read_text())


if __name__ == '__main__':
    unittest.main()
