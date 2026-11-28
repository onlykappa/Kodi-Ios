"""ISSUE-498: how heavy a stream the connection carries, learned from the blocks streams really fetch; the version list uses it."""
import sys, tempfile, unittest, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import connection_speed as cs

MB = 1024 * 1024


class Meter(unittest.TestCase):
    def test_parallel_blocks_are_not_counted_twice(self):
        m = cs.Meter()
        for i in range(8):                       # a 4 MB block every 2 s, each taking 2.4 s: two in flight at a time
            m.add(4 * MB, i * 2.0, i * 2.0 + 2.4)
        rate, busy, total = m.rate(16.0)
        self.assertAlmostEqual(rate * 8 / 1e6, 16.4, 0); self.assertEqual(total, 32 * MB)
    def test_too_little_says_nothing(self):
        m = cs.Meter(); m.add(1 * MB, 0, 1.0); self.assertIsNone(m.rate(5.0))                # under 2 MB
        m = cs.Meter(); m.add(3 * MB, 0, 1.0); self.assertIsNone(m.rate(5.0))                # under 3 s of fetching
    def test_old_blocks_leave_the_window(self):
        m = cs.Meter(); m.add(8 * MB, 0, 4.0); self.assertIsNotNone(m.rate(10.0)); self.assertIsNone(m.rate(100.0))
    def test_recording_is_at_most_every_ten_seconds(self):
        m = cs.Meter()
        self.assertTrue(m.due(100.0)); self.assertFalse(m.due(105.0)); self.assertTrue(m.due(110.5))


class Store(unittest.TestCase):
    def speeds(self, tmp, clock):
        return cs.Speeds(os.path.join(tmp, 'x', cs.FILE), clock)
    def test_a_figure_is_kept_per_network_and_goes_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = [1000.0]; s = self.speeds(tmp, lambda: now[0])
            self.assertIsNone(s.estimate('wifi:aaaa')); s.note('wifi:aaaa', 20.0)
            self.assertEqual(s.estimate('wifi:aaaa'), 20.0); self.assertIsNone(s.estimate('wifi:bbbb')); self.assertIsNone(s.estimate('cellular:aaaa'))   # another network: unknown
            now[0] += cs.STALE + 1; self.assertIsNone(s.estimate('wifi:aaaa'))
    def test_a_slower_sample_pulls_harder_than_a_faster_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.speeds(tmp, lambda: 1000.0)
            s.note('k', 20.0); self.assertEqual(s.note('k', 10.0), 13.0)        # 0.3 * 20 + 0.7 * 10
            s.note('j', 10.0); self.assertEqual(s.note('j', 20.0), 15.0)        # 0.5 * 10 + 0.5 * 20
    def test_nonsense_is_ignored_and_no_path_is_harmless(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.speeds(tmp, lambda: 1.0)
            for bad in (0, -5, 5000): self.assertIsNone(s.note('k', bad))
            self.assertIsNone(s.note('', 10.0)); self.assertIsNone(cs.Speeds(None).note('k', 10.0)); self.assertIsNone(cs.Speeds(None).estimate('k'))
    def test_network_key_has_no_address(self):
        a, b = cs.network_key('wifi', '192.168.1.3'), cs.network_key('wifi', '192.168.1.77')
        self.assertEqual(a, b); self.assertNotIn('192', a); self.assertNotEqual(a, cs.network_key('wifi', '10.0.0.5')); self.assertTrue(cs.network_key('wifi', '').endswith(':none'))


class Advice(unittest.TestCase):
    def test_the_limit_follows_the_measured_rate_within_bounds(self):
        self.assertEqual(cs.allowed(None), cs.DEFAULT); self.assertEqual(cs.allowed(0), cs.DEFAULT)
        self.assertEqual(cs.allowed(13.7), 9.6)                # the owner's AllDebrid link: an 11.4 Mbit/s HDR stream is over it
        self.assertEqual(cs.allowed(3.0), cs.FLOOR); self.assertEqual(cs.allowed(100.0), cs.CAP); self.assertEqual(cs.allowed(30.0), 20.0)
    def test_the_log_line_says_what_was_used(self):
        self.assertIn('no stream speed measured', cs.advice(None, 10.0)); self.assertIn('13.7 Mbit/s', cs.advice(13.7, 9.6)); self.assertIn('line 82 Mbit/s', cs.advice(13.7, 9.6, 82.0))
    def test_a_slow_line_lowers_the_limit_but_a_fast_one_never_raises_it(self):
        # ISSUE-503 (owner log f821266d): the line did 82 Mbit/s while streams got 6.6 to 17.7: the line's speed says nothing about a stream
        self.assertEqual(cs.allowed(13.7, 82.0), 9.6); self.assertEqual(cs.allowed(None, 82.0), cs.DEFAULT); self.assertEqual(cs.allowed(30.0, 82.0), 20.0)
        self.assertEqual(cs.allowed(30.0, 8.0), 5.6); self.assertEqual(cs.allowed(13.7, 3.0), cs.FLOOR)
        self.assertEqual(cs.delivery(None), cs.STREAM_TYPICAL); self.assertEqual(cs.delivery(0), cs.STREAM_TYPICAL); self.assertEqual(cs.delivery(8.5), 8.5)
        self.assertEqual(cs.stream_key('wifi:aaaa'), 'wifi:aaaa#stream'); self.assertEqual(cs.stream_key(''), '')
    def test_record_stores_a_figure_once_enough_was_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = cs.Speeds(os.path.join(tmp, cs.FILE), lambda: 5.0); m = cs.Meter()
            self.assertIsNone(cs.record(m, 12.0, s, 'wifi:aaaa'))             # nothing read yet
            m = cs.Meter()
            for i in range(6): m.add(4 * MB, i * 2.0, i * 2.0 + 2.0)
            got = cs.record(m, 12.0, s, 'wifi:aaaa')
            self.assertAlmostEqual(got, 16.8, 0); self.assertAlmostEqual(s.estimate(cs.stream_key('wifi:aaaa')), 16.8, 0); self.assertIsNone(s.estimate('wifi:aaaa'))   # kept apart from the line's own figure
            self.assertIsNone(cs.record(m, 13.0, s, 'wifi:aaaa'))             # not again within ten seconds
    def test_recording_never_raises(self):
        self.assertIsNone(cs.record(None, 1.0, None, 'k'))


class Wiring(unittest.TestCase):
    def test_streams_feed_it_and_the_list_uses_it(self):
        lib = ROOT / 'migration/bundled-bootstrap/resources/lib'
        self.assertIn("connection_speed.record(meter,now)", (lib / 'remote_media.py').read_text())
        picker = (lib / 'umbrella_picker.py').read_text()
        self.assertIn("deck.STREAM[0]=connection_speed.delivery(stream);deck.WIFI[0]=float(line or 0);deck.LIMIT[0]=connection_speed.allowed(stream,line)", picker); self.assertIn("connection_speed.advice(stream,deck.LIMIT[0],line)", picker)
        self.assertIn("limit = LIMIT[0] or STREAM_MBPS", (ROOT / 'migration/deck-picker/deck_picker.py').read_text())

    def test_the_block_trace_records_a_sample(self):
        import remote_media
        class Fake: pass
        f = Fake(); f.born = 0.0; f.logged = 0; f._log = lambda line: None
        # call the real method on a bare object: only successful blocks with a size count
        remote_media.Foreground._trace(f, 'block', 1, 0.0, size=4 * MB)
        self.assertEqual(len(f.speed_meter.items), 1)
        remote_media.Foreground._trace(f, 'block', 2, 0.0, error='x'); remote_media.Foreground._trace(f, 'read', 3, 0.0, size=4 * MB)
        self.assertEqual(len(f.speed_meter.items), 1)


class Probe(unittest.TestCase):
    # ISSUE-503: a live reading of the line
    def opener(self, chunks, tick):
        class R:
            def __init__(me): me.n = 0
            def __enter__(me): return me
            def __exit__(me, *a): return False
            def read(me, size):
                tick[0] += 0.2
                me.n += 1
                return b'x' * 65536 if me.n <= chunks else b''
        return lambda url: R()
    def test_the_rate_comes_from_bytes_over_time_and_a_short_read_says_nothing(self):
        t = [0.0]
        got = cs.probe(self.opener(40, t), lambda: t[0])                  # 40 chunks of 64 KiB in 8 s would be capped at 3 s: 15 chunks
        self.assertTrue(got and 2 < got < 4); t = [0.0]
        self.assertIsNone(cs.probe(self.opener(2, t), lambda: t[0]))      # 128 KiB: too little to judge
        def broken(url): raise OSError('x')
        self.assertIsNone(cs.probe(broken))


if __name__ == '__main__':
    unittest.main()
