"""Roadmap 1G.2: the conversion log reader, and that the native log line it reads still has the same shape."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import conversion_log as cl

LINE = 'compat: segment %d converted in %d ms (%d%% of realtime) via %s, source I/O %d ms, 0 subtitle events, 0 frames drawn, subtitle preroll through 0.000 s'


def log(*rows):
    return [LINE % row for row in rows]


class Reader(unittest.TestCase):
    def test_a_session_that_stays_within_the_target_has_only_three_lines(self):
        events = cl.parse(log((0, 5200, 87, 'GPU scale + VideoToolbox H.264', 900), (1, 3400, 57, 'GPU scale + VideoToolbox H.264', 300),
                              (2, 3300, 55, 'GPU scale + VideoToolbox H.264', 280)))
        summary = cl.summarize(events)
        self.assertEqual((summary['converted'], summary['first_three_pct'], summary['slow_after_first_three']), (3, [87, 57, 55], []))
        self.assertIn('no segment after the first three was slower than 70 %', summary['verdict'])

    def test_later_lines_are_misses_with_their_route(self):
        rows = [(0, 5200, 87, 'CPU av1', 900), (1, 3400, 57, 'CPU av1', 300), (2, 3300, 55, 'CPU av1', 280),
                (7, 9100, 152, 'CPU av1', 400), (8, 7000, 117, 'CPU av1', 350)]
        summary = cl.summarize(cl.parse(log(*rows)))
        self.assertEqual(summary['slow_after_first_three'], [(7, 152, 'CPU av1'), (8, 117, 'CPU av1')])
        self.assertIn('2 segments after the first three were slower than 70 % of real time; worst 152 %', summary['verdict'])
        self.assertEqual(summary['routes']['CPU av1']['segments'], 5)
        self.assertEqual(summary['routes']['CPU av1']['median_io_ms'], 350)

    def test_target_can_be_moved_and_failures_are_counted(self):
        rows = [(i, 6000, 100 + i, 'CPU h264 10-bit', 100) for i in range(5)]
        events = cl.parse(log(*rows) + ['compat: segment 9 failed after 1200 ms, source I/O 40 ms', 'unrelated line'])
        self.assertEqual(cl.summarize(events, target=103)['slow_after_first_three'], [(4, 104, 'CPU h264 10-bit')])
        self.assertEqual(cl.summarize(events)['failed'], 1)
        self.assertEqual(cl.summarize([])['verdict'], 'no conversion lines')

    def test_command_line_exit_code_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'kodi.log'
            path.write_text('\n'.join(log((0, 3000, 50, 'GPU', 100), (1, 3000, 50, 'GPU', 100), (2, 3000, 50, 'GPU', 100))) + '\n')
            self.assertEqual(cl.main([str(path)]), 0)
            path.write_text('\n'.join(log((0, 3000, 50, 'GPU', 100), (4, 9000, 150, 'GPU', 100))) + '\n')
            self.assertEqual(cl.main([str(path)]), 0)      # fewer than four lines: nothing past the first three
            path.write_text('\n'.join(log(*[(i, 3000, 50 if i < 3 else 90, 'GPU', 100) for i in range(5)])) + '\n')
            self.assertEqual(cl.main([str(path)]), 1)

    def test_the_native_line_still_has_the_shape_the_reader_expects(self):
        source = (ROOT / 'migration/airplay-ios/remux/src/kr_remux.c').read_text()
        self.assertIn('compat: segment %d converted in %.0f ms (%.0f%% of realtime) via %s, source I/O %.0f ms', source)
        self.assertIn('compat: segment %d %s after %.0f ms, source I/O %.0f ms', source)
        self.assertIn('atomic_fetch_add(&S.vlogged, 1) < 3 || pct > 70', source)


if __name__ == '__main__':
    unittest.main()
