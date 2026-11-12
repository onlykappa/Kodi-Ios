"""Library file manager L1 (DEC-043): one model of downloads for boards A-F of library-files-mockups.html."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import library_files as lf

MB = 1024 ** 2
NARUTO = {'id': 'f-naruto', 'title': 'Naruto Shippuden', 'year': 2007}
RICK = {'id': 'f-rick', 'title': 'Rick and Morty', 'year': 2013}


def ep(i, season=1, size=260, quality='1080p', name=None):
    return {'id': 'e%d' % i, 'season': season, 'episode': i, 'size': size * MB, 'quality': quality,
            'name': name or 'Naruto S01E%02d.mp4' % i, 'title': 'Naruto Shippuden'}


PREP = {'jobs': {
    'a': {'status': 'done', 'source': {'id': 'e1'}, 'prepared_id': 'e1'},
    'b': {'status': 'done', 'source': {'id': 'old2'}, 'prepared_id': 'e2'},
    'c': {'status': 'running', 'source': {'id': 'e3'}},
    'd': {'status': 'failed', 'error': 'Drive upload: HTTP 503', 'source': {'id': 'e4'}},
    'm': {'status': 'done', 'source': {'id': 'm1'}, 'prepared_id': 'm1'},
    'h': {'status': 'waiting', 'source': {'id': 'm2'}},
}}
DEBRID = {'jobs': [
    {'title': 'Naruto Shippuden', 'kind': 'episode', 'season': '1', 'episode': '5', 'status': 'copying', 'copied': 61, 'size': 100},
    {'title': 'Naruto Shippuden', 'kind': 'episode', 'season': '1', 'episode': '9', 'status': 'failed', 'error': 'not added'},
    {'title': 'Naruto Shippuden', 'kind': 'episode', 'season': '1', 'episode': '10', 'status': 'failed', 'error': 'Cancelled'},
    {'title': 'Naruto Shippuden', 'kind': 'episode', 'season': '1', 'episode': '1', 'status': 'done'},
]}
UPSCALE = {'copies': {'e2': {'status': 'ready', 'label': '4K UHD', 'copy_id': 'c2', 'size': 2400 * MB},
                      'e3': {'status': 'running', 'label': '4K UHD'}}}


class States(unittest.TestCase):
    def test_each_file_has_one_state(self):
        prep, copies = lf._index_prep(PREP), lf._index_copies(UPSCALE)
        self.assertEqual(lf.file_state(ep(1), prep, copies)['state'], lf.READY)
        two = lf.file_state(ep(2), prep, copies)
        self.assertEqual((two['state'], two['ai'], two['ai_label']), (lf.READY, True, '4K UHD'))
        self.assertEqual(lf.file_state(ep(3), prep, copies)['state'], lf.CONVERTING)
        four = lf.file_state(ep(4), prep, copies)
        self.assertEqual((four['state'], four['problem']), (lf.PROBLEM, 'Drive upload: HTTP 503'))
        self.assertEqual(lf.file_state(ep(7), prep, copies)['state'], lf.UNKNOWN)
        self.assertEqual(lf.file_state(dict(ep(7), prepared=True), prep, copies)['state'], lf.READY)

    def test_a_kept_repack_is_ready_not_a_problem(self):
        prep = lf._index_prep({'jobs': {'x': {'status': 'failed', 'blocked': True, 'repack_failed': True, 'source': {'id': 'e1'}}}})
        self.assertEqual(lf.file_state(ep(1), prep, {})['state'], lf.READY)


class Shows(unittest.TestCase):
    def setUp(self):
        self.files = {'f-naruto': [ep(1), ep(2), ep(3), ep(4)], 'f-rick': [dict(ep(i), id='r%d' % i) for i in (1, 2)]}

    def test_board_a_rows_and_chips(self):
        rows = lf.show_rows([NARUTO, RICK], self.files, PREP, DEBRID, UPSCALE)
        naruto = rows[0]
        # 4 on Drive + episode 5 copying + episode 9 failed to copy (a cancelled one is not a problem)
        self.assertEqual(naruto['episodes'], 6)
        self.assertEqual(naruto['counts'], {'ready': 2, 'converting': 1, 'copying': 1, 'problem': 2, 'unknown': 0})
        self.assertEqual(naruto['chips'], [('2 ready', 'green'), ('2 problems', 'red'), ('1 converting', 'orange')])
        self.assertEqual(naruto['size'], 4 * 260 * MB)
        self.assertEqual(rows[1]['chips'], [('All ready', 'green')])   # unknown counts as ready (prepared elsewhere)

    def test_chips_keep_problems_and_ai_in_three(self):
        self.assertEqual(lf.chips({'ready': 7, 'problem': 1}, 0, 8), [('7 ready', 'green'), ('1 problem', 'red')])
        self.assertEqual(lf.chips({'ready': 11}, 11, 11), [('All ready', 'green'), ('AI · 11', 'purple')])

    def test_board_b_episode_lines_and_repair(self):
        rows = lf.episode_rows(NARUTO, self.files['f-naruto'], PREP, DEBRID, UPSCALE, names={(1, 1): 'Homecoming'})
        self.assertEqual([r['episode'] for r in rows], [1, 2, 3, 4, 5, 9])
        self.assertEqual(rows[0]['name'], 'Homecoming')
        self.assertEqual(rows[0]['line'], 'Ready · 1080p · 260 MB')
        self.assertEqual(rows[1]['line'], 'Ready · 1080p · 260 MB · AI 4K UHD')
        self.assertEqual(rows[2]['line'], 'Converting')
        self.assertTrue(rows[3]['repair'] and rows[3]['line'].startswith('Problem · Drive upload'))
        self.assertEqual(rows[4]['line'], 'Copying to Drive · 61 %')
        self.assertEqual((rows[5]['line'], rows[5]['repair']), ('Not added', True))

    def test_search_and_sort(self):
        rows = lf.show_rows([NARUTO, RICK], self.files, PREP)
        self.assertEqual([r['title'] for r in lf.search(rows, '  rick ')], ['Rick and Morty'])
        self.assertEqual([r['title'] for r in lf.sort_shows(rows, 'size')], ['Naruto Shippuden', 'Rick and Morty'])
        self.assertEqual([r['title'] for r in lf.sort_shows(list(reversed(rows)), 'name')], ['Naruto Shippuden', 'Rick and Morty'])


class Movies(unittest.TestCase):
    def test_board_e_badges_and_size_sort(self):
        movies = [{'id': 'm1', 'title': 'Fall', 'size': 3400 * MB}, {'id': 'm2', 'title': 'Hell House LLC Origins', 'size': 1900 * MB},
                  {'id': 'm3', 'title': 'Interstellar', 'size': 58 * 1024 * MB}]
        rows = lf.movie_rows(movies, PREP, {'copies': {'m1': {'status': 'ready', 'label': '4K UHD'}}}, sort='size')
        self.assertEqual([(r['title'], r['badge']) for r in rows],
                         [('Interstellar', 'Ready'), ('Fall', 'AI 4K UHD'), ('Hell House LLC Origins', 'Converting')])


class Space(unittest.TestCase):
    def test_storage_and_free_up(self):
        files = {'f-naruto': [ep(1), ep(2)]}
        shows = lf.show_rows([NARUTO], files, PREP)
        movies = lf.movie_rows([{'id': 'm1', 'title': 'Fall', 'size': 3 * 1024 * MB}], PREP)
        store = lf.storage(shows, movies, UPSCALE, {'usage': 10, 'limit': 20})
        self.assertEqual((store['shows'], store['movies'], store['ai']), (520 * MB, 3 * 1024 * MB, 2400 * MB))
        self.assertEqual((store['used'], store['limit']), (10, 20))
        groups = {g['key']: g for g in lf.free_up(shows, files, movies, UPSCALE, watched={'e1'})}
        self.assertEqual((groups['watched']['count'], groups['watched']['bytes']), (1, 260 * MB))
        self.assertEqual(groups['ai']['items'], ['c2'])
        self.assertEqual(groups['largest']['items'], ['m1'])

    def test_sizes_read_as_on_the_board(self):
        self.assertEqual(lf.size_text(262 * MB), '262 MB')
        self.assertEqual(lf.size_text(int(8.3 * 1024 ** 3)), '8.3 GB')
        self.assertEqual(lf.size_text(0), '')



class Page(unittest.TestCase):
    """library_manager.fill: every property board A reads."""
    def setUp(self):
        import importlib.util
        root = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap'
        spec = importlib.util.spec_from_file_location('library_manager', root / 'library_manager.py')
        self.lm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.lm)
        files = {'f-naruto': [ep(1), ep(2), ep(3), ep(4)], 'f-rick': [dict(ep(i), id='r%d' % i, size=1400) for i in (1, 2)]}
        shows = lf.show_rows([NARUTO, RICK], files, PREP, DEBRID, UPSCALE)
        movies = lf.movie_rows([{'id': 'm1', 'title': 'Fall', 'year': 2022, 'size': 3400 * MB, 'quality': '1080p'}], PREP)
        self.data = {'shows': shows, 'movies': movies, 'storage': lf.storage(shows, movies, UPSCALE)}

    def test_tv_rows(self):
        props, rows = self.lm.fill(self.data, 'tv', 'name', '', slots=5)
        self.assertEqual((props['title'], props['sort.label']), ('TV Shows', 'Name'))   # no arrow character: Inter has none (the rig drew a box))
        self.assertEqual(props['row.0.title'], 'Naruto Shippuden')
        self.assertEqual(props['row.0.sub'], 'Season 1 · 6 episodes · 1.0 GB')
        self.assertEqual((props['row.0.chip0'], props['row.0.chip0c'], props['row.0.chip1c']), ('2 ready', 'green', 'red'))
        self.assertEqual((props['row.0.pos'], props['row.1.pos']), ('first', 'last'))
        self.assertEqual(props['row.2.title'], '')      # unused slots are cleared
        self.assertEqual(props['empty'], '')
        self.assertTrue(props['store.line'].endswith('on Google Drive'))
        self.assertIn('AI copies 2.3 GB', props['store.legend'])

    def test_movies_and_search(self):
        props, rows = self.lm.fill(self.data, 'movie', 'size', '', slots=5)
        self.assertEqual((props['title'], props['row.0.title'], props['row.0.chip0'], props['row.0.chip0c']), ('Movies', 'Fall', 'Ready', 'green'))
        self.assertEqual(props['row.0.sub'], '2022 · 3.3 GB · 1080p')
        props, rows = self.lm.fill(self.data, 'tv', 'recent', 'zzz', slots=5)
        self.assertEqual((rows, props['empty']), ([], 'Nothing matches “zzz”.'))
        props, rows = self.lm.fill({'shows': [], 'movies': [], 'storage': lf.storage([], [])}, 'tv', slots=5)
        self.assertIn('No downloaded shows yet', props['empty'])


if __name__ == '__main__':
    unittest.main()
