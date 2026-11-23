"""A Sports page's first read never waits for a refresh that is already running (owner, 2026-11-23, log e38980c3: hub load 2265 ms, Upcoming 2718 ms, Leagues 2979 ms, each
the length of the page's own background ESPN fetch, which held the provider's lock while the page's read waited for it)."""
import json, os, sys, tempfile, threading, time, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_espn as se


def old_snapshot(path, age):
    now = int(time.time())
    game = lambda i: {'id': 'g%d' % i, 'league': 'NFL', 'sport': 'Football', 'state': 'upcoming', 'start': now + 3600 * (i % 40), 'home': {}, 'away': {}}
    with open(path, 'w') as f:
        json.dump({'at': now - age, 'live': [], 'upcoming': [game(i) for i in range(50)], 'leagues': [{'code': 'NFL', 'name': 'NFL', 'sport': 'Football', 'live': 0, 'next': now + 60}], 'finished': 0}, f)


class Nonblocking(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(); self.path = os.path.join(self.dir, 'snap.json'); old_snapshot(self.path, 3 * 3600)
        self.gate = threading.Event(); self.asked = []
        def slow(url):
            self.asked.append(url); self.gate.wait(8); return {'events': []}
        self.addCleanup(self.gate.set)
        self.provider = se.EspnProvider(fetch=slow, snapshot_path=self.path)
    def timed(self, fn):
        t = time.monotonic(); out = fn(); return out, time.monotonic() - t

    def test_reads_do_not_wait_for_the_refresh_they_started(self):
        # the page's sequence: has_answer, overview, upcoming_games, leagues (all the first reads of a fresh process)
        self.assertTrue(self.provider.has_answer())
        _, a = self.timed(self.provider.overview)
        _, b = self.timed(self.provider.upcoming_games)
        _, c = self.timed(self.provider.leagues)
        time.sleep(.3); self.assertTrue(self.asked, 'the background refresh did start')   # it is running (blocked in its fetch) while the reads were made
        for took in (a, b, c):
            self.assertLess(took, .5, 'a read waited for the running refresh (%.2f s)' % took)
        _, d = self.timed(self.provider.overview); self.assertLess(d, .5)
    def test_the_refresh_still_lands_and_replaces_the_remembered_answer(self):
        self.provider.overview(); time.sleep(.2); self.gate.set()
        for _ in range(100):
            if self.provider.snapshot and not self.provider.snapshot.get('remembered'): break
            time.sleep(.05)
        self.assertFalse(self.provider.snapshot.get('remembered'))
    def test_with_nothing_saved_the_first_read_does_wait_for_the_answer(self):
        os.unlink(self.path); self.gate.set()
        asked = []
        provider = se.EspnProvider(fetch=lambda url: asked.append(url) or {'events': []}, snapshot_path=self.path)
        self.assertEqual(provider.overview()['live'], 0); self.assertTrue(asked)   # nothing to draw instead: it asked, and waited for the answer
    def test_two_forced_refreshes_do_not_fetch_at_once(self):
        order = []; lock = threading.Lock(); live = [0]; worst = [0]
        def fetch(url):
            with lock: live[0] += 1; worst[0] = max(worst[0], live[0])
            time.sleep(.01)
            with lock: live[0] -= 1
            return {'events': []}
        provider = se.EspnProvider(fetch=fetch, snapshot_path=None); provider.snapshot = {'at': 0, 'live': [], 'upcoming': [], 'leagues': [], 'finished': 0}
        threads = [threading.Thread(target=lambda: provider._load(force=True)) for _ in range(2)]
        [t.start() for t in threads]; [t.join(20) for t in threads]
        self.assertLessEqual(worst[0], 6)   # the pool's own six at most: one fetch round at a time, not two rounds interleaved
        self.assertFalse(provider.fetch_lock.locked())


if __name__ == '__main__':
    unittest.main()
