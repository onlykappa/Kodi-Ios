"""F2 (PR #24 roadmap): several re-packages at once. Build-356 log 7249de4d: 27 jobs waited behind one re-package that
read Drive at 3-7 MB/s. Known re-packages (the picture is copied) now run in extra lanes beside the main one; the native
side is proven by test_remux.c's test_preparation_parallel (three at once keep their packets and validate)."""
import sys, tempfile, threading, time, types, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
LIB = BOOT / 'resources/lib'
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB))
import drive_stream, prepare_cloud, prepare_downloads, work_state  # noqa: E402


def job(name, **kw):
    return dict({'source': {'id': name, 'name': name + '.mkv', 'size': 10}, 'status': 'waiting', 'attempts': 0}, **kw)


class Queue:
    def __init__(self, jobs):
        self.state = {'jobs': jobs}
        self.lock = threading.RLock()
        self.clock = time.time
        self.runtime = None
        self.stream = drive_stream.DriveStream.__new__(drive_stream.DriveStream)
        self.stream.wide_items = set()
        self.work = Path(tempfile.mkdtemp())   # the main lane tidies old local checkpoints here

    def commit(self):
        pass


class Lanes(unittest.TestCase):
    def test_known_repack(self):
        self.assertTrue(prepare_cloud.known_repack({'repack': True}))
        self.assertTrue(prepare_cloud.known_repack({'probe': {'copy_video': True}}))
        self.assertFalse(prepare_cloud.known_repack({'probe': {'copy_video': False}}))
        self.assertFalse(prepare_cloud.known_repack({}))                                   # not read yet: main lane only
        self.assertFalse(prepare_cloud.known_repack({'repack': True, 'audit': True}))      # being checked

    def run_lanes(self, jobs, lanes):
        q = Queue(jobs)
        taken, gate = {}, threading.Barrier(len(lanes))

        def fake_run(q_, keep_going, lane, runtime, set_card, drop_card, card, candidates, slot, job_, item, last):
            taken[lane] = slot
            set_card({'title': item['name'], 'running': True, 'updated': time.time(), 'progress': 40})
            self.assertIn(slot, q_.running_slots)       # claimed while it runs
            gate.wait(5)                                # every lane is inside at once
            return True
        original = prepare_cloud._run
        prepare_cloud._run = fake_run
        try:
            threads = [threading.Thread(target=prepare_cloud.process_one, args=(q, lambda: True, lane)) for lane in lanes]
            for t in threads:
                t.start()
            for t in threads:
                t.join(10)
        finally:
            prepare_cloud._run = original
        return q, taken

    def test_each_lane_takes_its_own_job_and_extra_lanes_only_re_packages(self):
        jobs = {'conv': job('Film', probe={'copy_video': False}), 'a': job('A', repack=True), 'b': job('B', repack=True),
                'c': job('C', repack=True)}
        q, taken = self.run_lanes(jobs, [None, '2', '3'])
        self.assertEqual(len(set(taken.values())), 3, taken)                 # no job twice
        self.assertIn(taken['2'], ('a', 'b', 'c'))
        self.assertIn(taken['3'], ('a', 'b', 'c'))
        self.assertEqual(q.running_slots, set())                             # released afterwards
        self.assertEqual(sorted(q.state['lanes']), ['2', '3'])               # each lane's own card

    def test_an_extra_lane_never_takes_a_real_conversion_or_an_unread_job(self):
        q = Queue({'conv': job('Film', probe={'copy_video': False}), 'new': job('New')})
        self.assertFalse(prepare_cloud.process_one(q, lambda: True, '2'))

    def test_the_lane_cards_reach_library_status_and_leave_up_next(self):
        now = time.time()
        prep = {'jobs': {'a': job('Naruto.S01E06', repack=True), 'b': job('Naruto.S01E07', repack=True)},
                'current': {'title': 'Inception.2010.mkv', 'running': True, 'updated': now, 'progress': 17, 'kind': 'repack',
                            'stage': 'Step 3 of 3 · Making it start faster'},
                'lanes': {'2': {'title': 'Naruto.S01E06.mkv', 'running': True, 'updated': now, 'progress': 55},
                          '3': {'title': 'Old.mkv', 'running': True, 'updated': now - 3600, 'progress': 5}}}   # stale: hidden
        model = work_state.build({'prep': prep}, now)
        moving = [(j['kind'], j['pct']) for j in model['jobs']]
        self.assertIn(('repack', 55), moving)
        self.assertEqual(len([j for j in model['jobs'] if j['kind'] in ('conv', 'repack')]), 2)
        self.assertNotIn('Naruto S01E06', [n['title'] for n in model['next']])
        self.assertTrue(any('S01E07' in n['title'] or 'E07' in n['title'] or '7' in n['title'] for n in model['next']), model['next'])

    def test_read_ahead_shares_the_block_cache(self):
        counts = [drive_stream.ahead_count(False, '', True, n) for n in (1, 2, 3)]
        self.assertEqual(counts, [8, 8, 6])
        self.assertLessEqual(3 * (counts[2] + 1), drive_stream.KEEP)       # three lanes never push out each other's blocks
        s = drive_stream.DriveStream.__new__(drive_stream.DriveStream)
        s.wide_items = set()
        s.widen('a'); s.widen('b'); s.unwide('a')
        self.assertEqual(s.wide_items, {'b'})

    def test_the_service_runs_the_lanes_with_the_owners_rules(self):
        src = (BOOT / 'service.py').read_text()
        self.assertIn("for lane in range(2,2+prepare_downloads.REPACK_LANES):", src)
        self.assertIn("and not prepare_downloads.interrupts(profile) and not slowdown.reason() and not getattr(q,'upscaling',False)", src)
        self.assertIn("not getattr(preparation,'running_slots',None)", src)      # AI Upscale waits for the lanes
        self.assertEqual(prepare_downloads.REPACK_LANES, 2)


if __name__ == '__main__':
    unittest.main()
