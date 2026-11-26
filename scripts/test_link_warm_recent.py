"""Continue warm-up of the first Continue Watching links, and the guard's refused-link early cut (owner, 2026-11-23)."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import link_warm as lw
import continue_guard as cg

NOW = 1_000_000.0
def row(n, player='umbrella', age=3600, pos=600, total=3000):
    return {'player': player, 'position': pos, 'total': total, 'stream': {'url': 'https://x.test/%d.mkv' % n, 'at': NOW - age}}

class Recent(unittest.TestCase):
    def test_only_first_three_rows(self):
        rows = [row(i) for i in range(10)]
        self.assertEqual([u for u, f, sec in lw.recent_links(rows, NOW)], ['https://x.test/%d.mkv' % i for i in range(3)])
    def test_skips_other_players_old_links_and_no_resume(self):
        rows = [row(0, player='elementum'), row(1, age=73 * 3600), row(2, pos=1), row(3, pos=2900), row(4)]
        self.assertEqual([u for u, f, sec in lw.recent_links(rows, NOW, limit=5)], ['https://x.test/4.mkv'])
    def test_72_hours_kept(self):
        self.assertEqual(len(lw.recent_links([row(0, age=71 * 3600)], NOW)), 1)
    def test_fraction_and_seconds(self):
        got = lw.recent_links([row(0, pos=600, total=3000)], NOW)[0]
        self.assertAlmostEqual(got[1], 0.2); self.assertEqual(got[2], 600)

class Warm(unittest.TestCase):
    def test_reads_start_end_and_resume_point(self):
        seen = []
        class R:
            headers = {'Content-Range': 'bytes 0-1/100000000'}
            def __init__(self): self.n = 0
            def read(self, k): 
                self.n += 1
                return b'x' * k if self.n < 3 else b''
            def __enter__(self): return self
            def __exit__(self, *a): return False
        def opener(request, timeout=0):
            seen.append(request.get_header('Range')); return R()
        made = lw.warm('https://x.test/a.mkv', 0, opener, fraction=0.5)
        self.assertEqual(made, 3)
        self.assertEqual(seen[0], 'bytes=0-%d' % (lw.HEAD - 1))
        self.assertTrue(seen[1].startswith('bytes=%d-' % (100000000 - lw.TAIL)))
        self.assertTrue(seen[2].startswith('bytes=50000000-'))
    def test_failure_is_swallowed(self):
        def boom(request, timeout=0): raise OSError('no')
        self.assertEqual(lw.warm('https://x.test/a.mkv', 0, boom, fraction=0.5), 0)
    def test_loop_skips_while_playing_and_repeats_not_within_25_min(self):
        calls, clock, waits = [], [NOW], []
        def wait(sec):
            waits.append(sec); clock[0] += sec; return len(waits) >= 4
        busy = [True]
        def warm_it(url, size, fraction=None, seconds=None): calls.append(url); return 3
        lw.watch(lambda: [row(0)], lambda: busy[0], wait, lambda t: None, now=lambda: clock[0], warm_it=warm_it)
        self.assertEqual(calls, [])                     # busy: nothing warmed
        busy[0] = False; waits.clear(); clock[0] = NOW
        lw.watch(lambda: [row(0)], lambda: busy[0], wait, lambda t: None, now=lambda: clock[0], warm_it=warm_it)
        self.assertEqual(len(calls), 1)                 # 10 min apart < 25 min: warmed once in the run
    def test_nothing_is_warmed_on_mobile_data(self):
        calls, waits = [], []
        def wait(sec): waits.append(sec); return len(waits) >= 2
        lw.watch(lambda: [row(0)], lambda: False, wait, lambda t: None, now=lambda: NOW, warm_it=lambda *a, **k: calls.append(1) or 3, allowed=lambda: False)
        self.assertEqual(calls, [])
    def test_log_has_no_address(self):
        logs = []
        waits = []
        def wait(sec): waits.append(sec); return len(waits) >= 2
        lw.watch(lambda: [row(0)], lambda: False, wait, logs.append, now=lambda: NOW, warm_it=lambda *a, **k: 3)
        self.assertTrue(logs and all('x.test' not in l for l in logs))

def el(ident, payload):
    n = len(payload)
    return bytes.fromhex(ident) + bytes([0x80 | n]) + payload if n < 127 else bytes.fromhex(ident) + bytes([0x40 | (n >> 8), n & 255]) + payload
def uint(v):
    return v.to_bytes(max(1, (v.bit_length() + 7) // 8), 'big')
def cue(t, pos):
    return el('BB', el('B3', uint(t)) + el('B7', el('F7', uint(1)) + el('F1', uint(pos))))

class ResumeOffset(unittest.TestCase):
    """The Matroska seek Kodi makes, found from the file's start and its Cues (rig: 30.0 s went to the 28 s cue, byte 39427588 of 84556212)."""
    SEG = 400                                   # where the Segment's data starts
    head = b'\x1a\x45\xdf\xa3\x80' + b'\x18\x53\x80\x67\x88' + el('2AD7B1', uint(1000000))
    def tail(self):
        return b'\x00' * 20 + bytes.fromhex('1C53BB6B') + (lambda c: bytes([0x40 | (len(c) >> 8), len(c) & 255]) + c)(cue(0, 100) + cue(28000, 5000) + cue(30000, 7000) + cue(32000, 9000))
    def test_the_cue_before_the_place_is_used(self):
        head = self.head + b'\x00' * 10
        seg = head.find(b'\x18\x53\x80\x67') + 5
        self.assertEqual(lw.resume_offset(head, self.tail(), 10 ** 6, 30.0), seg + 5000)   # 30.0 s -> the 28 s cue, as Kodi does
        self.assertEqual(lw.resume_offset(head, self.tail(), 10 ** 6, 30.6), seg + 7000)
    def test_not_matroska_or_no_cues_gives_none(self):
        self.assertIsNone(lw.resume_offset(b'\x00' * 100, self.tail(), 10 ** 6, 30.0))
        self.assertIsNone(lw.resume_offset(self.head, b'\x00' * 100, 10 ** 6, 30.0))
        self.assertIsNone(lw.resume_offset(b'', b'', 10 ** 6, 30.0))

class Guard(unittest.TestCase):
    def mark(self, at=1000.0):
        return cg.note({'tmdb_type': 'movie', 'tmdb_id': '1'}, lambda: at, 'https://x.test/a.mkv')
    def test_refused_link_cut_after_8_seconds_not_before(self):
        m = self.mark()
        self.assertEqual(cg.decide(m, 1007.0, False, False, refused=True), 'wait')
        self.assertEqual(cg.decide(m, 1008.5, False, False, refused=True), 'fallback')
    def test_slow_link_keeps_waiting(self):
        m = self.mark()
        self.assertEqual(cg.decide(m, 1000.0 + cg.LIMIT - 1, False, False, refused=False), 'wait')   # LIMIT 20 s since 2026-11-25 (was 30)
        self.assertEqual(cg.decide(m, 1000.0 + cg.LIMIT, False, False), 'fallback')
    def test_opened_streams_are_never_cut_early(self):
        self.assertEqual(cg.decide(self.mark(), 1012.0, False, False, opened=True, refused=True), 'wait')
    def test_probe_needs_two_refusals_and_one_request_at_a_time(self):
        t = [0.0]; started = []
        p = cg.Probe(lambda url: False, now=lambda: t[0], start=lambda work: started.append(work))
        self.assertFalse(p('u')); self.assertEqual(len(started), 1)
        self.assertFalse(p('u')); self.assertEqual(len(started), 1)   # first still running
        started.pop()(); t[0] += 3
        self.assertFalse(p('u')); started.pop()(); t[0] += 3
        self.assertTrue(p('u'))
    def test_probe_answer_resets(self):
        t = [0.0]; started = []; answers = iter([False, True, False])
        p = cg.Probe(lambda url: next(answers), now=lambda: t[0], start=lambda w: started.append(w))
        for _ in range(3):
            p('u'); started.pop()(); t[0] += 3
        self.assertFalse(p('u'))
    def test_note_carries_address(self):
        self.assertEqual(json.loads(self.mark())['url'], 'https://x.test/a.mkv')

if __name__ == '__main__':
    unittest.main()
