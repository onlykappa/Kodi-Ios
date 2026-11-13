"""F4 (PR #24 roadmap): what the owner watches next is prepared first, and copies leave it the line."""
import json, os, sys, tempfile, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BOOT / 'resources/lib'))
import debrid_drive, prepare_downloads as prep, watch_next  # noqa: E402

CONTINUE = {'items': {'episode:31910:1:5': {'kind': 'episode', 'tmdb_id': '31910', 'tvshowtitle': 'Naruto Shippūden',
                                             'season': '1', 'episode': '5', 'position': 300, 'total': 1400},
                      'movie:27205::': {'kind': 'movie', 'tmdb_id': '27205', 'title': 'Inception', 'position': 60, 'total': 8000}}}


def job(name, **kw):
    return dict({'source': {'id': name, 'name': name, 'size': 1}, 'status': 'waiting'}, **kw)


class WatchNext(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: prep.WATCH_NEXT.__setitem__(0, lambda name: False))

    def test_the_started_episode_and_the_next_three(self):
        wanted = watch_next.keys(CONTINUE)
        hits = [n for n in range(1, 12) if watch_next.matches(wanted, 'Naruto Shippuden - %03d [1080p].mkv' % n)]
        self.assertEqual(hits, [5, 6, 7, 8])
        self.assertTrue(watch_next.matches(wanted, 'Naruto.Shippuden.S01E06.1080p.WEB.mkv'))     # any spelling of the name
        self.assertFalse(watch_next.matches(wanted, 'Naruto.Shippuden.S02E06.1080p.WEB.mkv'))
        self.assertFalse(watch_next.matches(wanted, 'Inception.2010.2160p.mkv'))
        self.assertFalse(watch_next.matches(wanted, 'Bleach.S01E06.mkv'))

    def test_they_are_prepared_first_but_after_the_owners_own_choices(self):
        prep.WATCH_NEXT[0] = lambda name: watch_next.matches(watch_next.keys(CONTINUE), name)
        jobs = {'a': job('Bleach.S01E01.mkv', repack=True), 'b': job('Naruto.Shippuden.S01E07.mkv'),
                'c': job('Naruto.Shippuden.S01E06.mkv', repack=True), 'd': job('Film.2020.mkv', priority=9000),
                'e': job('Naruto.Shippuden.S01E20.mkv', repack=True)}
        order = [slot for slot, _ in sorted(jobs.items(), key=lambda pair: prep.order_key(*pair))]
        self.assertEqual(order[0], 'd')                       # Prepare next / Start now stays first
        self.assertEqual(set(order[1:3]), {'b', 'c'})         # then episodes 6 and 7, before the other re-packages
        self.assertEqual(set(order[3:]), {'a', 'e'})

    def test_the_cached_reader_follows_the_file(self):
        with tempfile.TemporaryDirectory() as profile:
            wanted = watch_next.cached(profile)
            self.assertFalse(wanted('Naruto.Shippuden.S01E06.mkv'))          # no Continue Watching yet
            os.makedirs(os.path.dirname(watch_next.path(profile)))
            with open(watch_next.path(profile), 'w') as f:
                json.dump(CONTINUE, f)
            self.assertTrue(wanted('Naruto.Shippuden.S01E06.mkv'))
            self.assertFalse(wanted('Naruto.Shippuden.S01E12.mkv'))

    def test_copies_leave_the_line_to_a_next_to_watch_preparation(self):
        with tempfile.TemporaryDirectory() as profile:
            now = time.time()
            state = {'jobs': {}, 'current': {'title': 'Naruto.Shippuden.S01E06.mkv', 'running': True, 'updated': now, 'watch_next': True}}
            prep.save(profile, state)
            self.assertTrue(debrid_drive.priority_running(profile, now))
            state['current']['watch_next'] = False
            prep.save(profile, state)
            self.assertFalse(debrid_drive.priority_running(profile, now))
            state['current'].update(watch_next=True, updated=now - 900)      # a stale card says nothing
            prep.save(profile, state)
            self.assertFalse(debrid_drive.priority_running(profile, now))
        self.assertEqual(debrid_drive.PRIORITY_LANES, 2)
        src = (BOOT / 'resources/lib/debrid_drive.py').read_text()
        self.assertIn("if busy and priority_running(profile, clock()):\n                cap = min(cap, PRIORITY_LANES)", src)
        self.assertIn("watch_next=prep.watch_next(job)", (BOOT / 'resources/lib/prepare_cloud.py').read_text())
        self.assertIn("prepare_downloads.WATCH_NEXT[0]=watch_next.cached(profile)", (BOOT / 'service.py').read_text())


if __name__ == '__main__':
    unittest.main()
