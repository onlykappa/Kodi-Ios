"""DEC-052 / ISSUE-276: the Library index, one record every screen reads. Built from the owner's state in log 8d661d6e
(build 424): Naruto Shippuuden season 1 on Drive, season 2 landing and copying, an old failed copy of S1 E6 whose episode
is on Drive ("S1 E6 · Unnamed download"), a real problem, a cancelled copy, and two movies/episodes kept as they are."""
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.modules.setdefault('xbmc', types.SimpleNamespace(log=lambda *a, **k: None, LOGINFO=1))
import library_index as li  # noqa: E402
import problem_ignore  # noqa: E402

MB = 1024 ** 2


def drive(i, name, folder='Naruto Shippuuden'):
    return {'id': 'd%s' % i, 'name': name, 'folder': folder, 'size': 200 * MB}


def owner_state():
    listing = [drive('1-%d' % n, 'Naruto Shippuuden S01E%02d - Naruto Shippuden Episode %03d.mkv' % (n, n)) for n in range(1, 29)]
    listing += [drive('2-%d' % n, 'Naruto Shippuuden S02E%02d - [Anime Time] Naruto Shippuden - %03d.mkv' % (n, n)) for n in range(33, 49)]
    listing += [drive('rm5', 'Rick and Morty S01E05 1080p.mkv', 'Rick and Morty'), drive('fall', 'Fall 2 Deadpoint (2026).mkv', 'Movies'),
                drive('dup', 'Naruto Shippuuden S01E05 - another copy.mkv')]
    prep = {'jobs': {}}
    for item in listing:
        prep['jobs']['j' + item['id']] = {'status': 'done', 'source': {'id': item['id']}}
    prep['jobs']['jd2-48'] = {'status': 'running', 'source': {'id': 'd2-48'}}
    prep['jobs']['jdrm5'] = {'status': 'failed', 'blocked': True, 'verify_failed': True, 'source': {'id': 'drm5'},
                             'error': 'The prepared copy did not pass its checks'}
    prep['jobs']['jdfall'] = {'status': 'failed', 'blocked': True, 'repack_failed': True, 'source': {'id': 'dfall'},
                              'error': 'MP4 packet: Invalid argument'}
    debrid = {'jobs': [
        {'title': 'Naruto Shippuuden', 'kind': 'episode', 'season': '2', 'episode': str(n), 'status': 'copying', 'hash': 'c%d' % n,
         'copied': 30, 'size': 100, 'show_tmdb': '31910', 'added': n} for n in range(49, 54)] + [
        {'title': '', 'kind': 'episode', 'season': '1', 'episode': '6', 'status': 'failed', 'hash': 'old6', 'name': '',
         'error': 'AllDebrid: File not available due to no peer', 'added': 1, 'finished': 5, 'show_tmdb': '31910'},
        {'title': 'Naruto Shippuuden', 'kind': 'episode', 'season': '2', 'episode': '54', 'status': 'failed', 'hash': 'f54',
         'error': 'AllDebrid: File not available due to no peer', 'added': 2, 'finished': 6, 'show_tmdb': '31910'},
        {'title': 'Phony', 'kind': 'episode', 'season': '1', 'episode': '9', 'status': 'failed', 'hash': 'x9', 'error': 'Cancelled',
         'added': 3, 'finished': 7},
        {'title': 'Naruto Shippuuden', 'kind': 'episode', 'season': '2', 'episode': '40', 'status': 'failed', 'hash': 'old40',
         'error': 'Not the quality you picked: 704x480, you chose 1080p', 'low_quality': True, 'added': 4, 'finished': 8}]}
    return listing, prep, debrid


class OneRecord(unittest.TestCase):
    def setUp(self):
        self.listing, self.prep, self.debrid = owner_state()
        self.index = li.build(self.listing, self.prep, self.debrid, clock=lambda: 1000.0)

    def test_every_screen_gets_the_same_numbers(self):
        whole, tv, movies = li.counts(self.index), li.counts(self.index, 'tv'), li.counts(self.index, 'movies')
        naruto = li.counts(self.index, ('show', 'Naruto Shippūden'))
        # Library status (whole library) = TV + movies; one show's numbers are part of TV's.
        for k in ('total', 'ready', 'working', 'problems', 'kept'):
            self.assertEqual(whole[k], tv[k] + movies[k], k)
        self.assertEqual(naruto['total'], 28 + 16 + 5 + 1)          # S1 28, S2 33-48 on Drive, 49-53 copying, 54 a problem
        self.assertEqual((naruto['ready'], naruto['converting'], naruto['copying'], naruto['problems']), (28 + 15, 1, 5, 1))
        # The show page's seasons grow as season 2 lands (owner item 3).
        seasons = {s['title']: s['seasons'] for s in li.shows(self.index)}['Naruto Shippuuden']
        self.assertEqual((seasons[1]['total'], seasons[2]['total'], seasons[2]['copying']), (28, 22, 5))
        # Download problems lists exactly the problems the counts count (plus the cancelled copy, never counted).
        rows = li.problems(self.index)
        self.assertEqual(len([r for r in rows if r['state'] == li.PROBLEM]), whole['problems'])
        self.assertEqual([r['state'] for r in rows if r['title'] == 'Phony'], [li.CANCELLED])
        self.assertEqual(whole['cancelled'], 1)

    def test_a_failed_copy_of_a_video_on_drive_is_not_a_problem(self):
        # "S1 E6 · Unnamed download" while E6 played; and the low copy of S2 E40 that was replaced.
        problems = [(r['season'], r['episode']) for r in li.problems(self.index) if r['kind'] == 'episode']
        self.assertNotIn((1, 6), problems)
        self.assertNotIn((2, 40), problems)
        self.assertIn((2, 54), problems)

    def test_kept_problem_and_ready_are_decided_once(self):
        by_id = {e['id']: e for e in self.index['videos'] if e['id']}
        self.assertEqual(by_id['drm5']['state'], li.PROBLEM)        # failed its checks: needs the owner (Repair / Keep)
        self.assertEqual(by_id['dfall']['state'], li.READY)         # plays; only its faster start failed
        self.prep['jobs']['jdrm5']['kept'] = True                   # Keep as It Is
        index = li.build(self.listing, self.prep, self.debrid)
        self.assertEqual({e['id']: e for e in index['videos'] if e['id']}['drm5']['state'], li.KEPT)
        self.assertEqual(li.counts(index)['kept'], 1)

    def test_one_entry_per_video(self):
        keys = [e['key'] for e in self.index['videos']]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(self.index['duplicates'], ['ddup'])        # S1 E5 twice on Drive: one entry, the extra listed

    def test_dont_show_again_hides_it_everywhere(self):
        with tempfile.TemporaryDirectory() as profile:
            row = next(r for r in li.problems(self.index) if r['episode'] == 54)
            import debrid_drive
            p = next(p for p in debrid_drive.problems(self.debrid) if p['key'] == row['problem_key'])
            problem_ignore.ignore(profile, p)
            index = li.build(self.listing, self.prep, self.debrid, ignored=problem_ignore.load(profile))
        self.assertEqual((li.counts(index)['problems'], li.counts(index)['hidden']), (li.counts(self.index)['problems'] - 1, 1))
        self.assertNotIn(54, [r['episode'] for r in li.problems(index)])


class SharedRecord(unittest.TestCase):
    """Step 2: the service writes the index, pages read it, every action shows on every page at once."""
    def setUp(self):
        import prepare_downloads, debrid_drive
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.profile = self.tmp.name
        listing, prep, debrid = owner_state()
        prep['library'] = {'items': listing, 'checked': 900.0}
        prepare_downloads.save(self.profile, prep);debrid_drive.save(self.profile, debrid)

    def test_the_counter_moves_only_when_something_shown_changes(self):
        first = li.refresh(self.profile, {'ok': True}, clock=lambda: 1000.0)
        self.assertEqual((first['counter'], li.load(self.profile)['counter']), (1, 1))
        self.assertEqual(li.refresh(self.profile, {'ok': True}, clock=lambda: 1001.0)['counter'], 1)   # nothing changed
        li.refresh(self.profile, {'ok': False, 'error': "can't reach Google Drive"}, clock=lambda: 1002.0)
        self.assertEqual(li.load(self.profile)['counter'], 2)                                            # the health line did
        self.assertEqual(li.load(self.profile)['checked'], 900.0)

    def test_an_action_shows_on_every_page_at_once(self):
        index = li.refresh(self.profile, clock=lambda: 1000.0)
        key = next(e['key'] for e in index['videos'] if e['episode'] == 50 and e['season'] == 2)
        li.intend(self.profile, [key], 'stop', now=1000.0)
        entry = next(e for e in li.refresh(self.profile, clock=lambda: 1001.0)['videos'] if e['key'] == key)
        self.assertEqual((entry['pending'], li.entry_line(entry)), ('stop', 'Stopping…'))
        later = next(e for e in li.refresh(self.profile, clock=lambda: 1000.0 + li.INTENT_TTL + 1)['videos'] if e['key'] == key)
        self.assertNotIn('pending', later)                                                               # the real state took over
        with self.assertRaises(ValueError):
            li.intend(self.profile, [key], 'explode')

    def test_the_service_loop_sets_the_counter_property(self):
        props, ticks = {}, iter([False, False, True])
        li.publish(self.profile, lambda every: next(ticks), set_property=props.__setitem__, clock=lambda: 1000.0)
        self.assertEqual(props[li.PROPERTY], '1')
        self.assertIn('target=library_index.publish,args=(profile,', (ROOT / 'migration/bundled-bootstrap/service.py').read_text())


if __name__ == '__main__':
    unittest.main()
