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


class ShowPage(Page):
    """library_manager.fill_show: board B for one show."""
    def test_board_b(self):
        data = dict(self.data, episodes={'f-naruto': [ep(1), ep(2), ep(3), ep(4), ep(1, season=2)]},
                    prep=PREP, debrid=DEBRID, upscale=UPSCALE, fanart={'f-naruto': 'fan.jpg'})
        show = data['shows'][0]
        props, shown, seasons = self.lm.fill_show(data, show, slots=10)
        self.assertEqual(seasons, [1, 2])
        self.assertEqual((props['season.0'], props['season.1'], props['season.2'], props['season.on']), ('Season 1', 'Season 2', '', '0'))
        self.assertEqual((props['n.episodes'], props['n.ready'], props['fanart']), ('7', '3', 'fan.jpg'))
        self.assertEqual([r['episode'] for r in shown], [1, 2, 3, 4, 5, 9])
        self.assertEqual(props['ep.0.title'], '1 \u00b7 Naruto Shippuden')
        self.assertEqual((props['ep.3.state'], props['ep.3.repair']), ('problem', 'true'))
        self.assertEqual((props['ep.4.state'], props['ep.4.bar']), ('copying', 'true'))   # 61 % known
        self.assertEqual(props['ep.2.bar'], '')                                          # converting, no percentage yet
        self.assertEqual((props['ep.0.pos'], props['ep.5.pos'], props['ep.6.title']), ('first', 'last', ''))
        props, shown, _ = self.lm.fill_show(data, show, season=2, slots=10)
        self.assertEqual(([r['season'] for r in shown], props['season.on']), ([2], '1'))


class ItemSheet(Page):
    """library_manager.fill_item: board C for an episode or a movie, in each state."""
    def rows(self):
        data = dict(self.data, episodes={'f-naruto': [ep(1), ep(2), ep(3), ep(4)]}, prep=PREP, debrid=DEBRID, upscale=UPSCALE)
        _, shown, _ = self.lm.fill_show(data, data['shows'][0], slots=10)
        return {r['episode']: r for r in shown}

    def test_ready_with_ai_copy(self):
        props, actions = self.lm.fill_item(self.rows()[2], {'title': 'Naruto Shippuden'})
        self.assertEqual((props['title'], props['sub']), ('2 \u00b7 Naruto Shippuden', 'Naruto Shippuden \u00b7 Season 1'))
        self.assertEqual([props['step.%d.state' % n] for n in range(4)], ['ok', 'ok', 'ok', 'off'])
        self.assertEqual(props['step.2.title'], 'AI Upscale \u00b7 4K UHD')
        self.assertEqual((props['primary'], props['secondary'], props['delete']), ('Play', 'Play on TV', 'Delete Episode\u2026'))
        self.assertEqual(actions, ('play', 'tv', 'delete'))

    def test_problem_and_not_added_lead_with_repair(self):
        props, actions = self.lm.fill_item(self.rows()[4], {'title': 'Naruto'})
        self.assertEqual((props['step.1.state'], props['primary'], actions[0]), ('bad', 'Repair', 'retry'))
        self.assertIn('HTTP 503', props['step.1.detail'])
        props, actions = self.lm.fill_item(self.rows()[9], {'title': 'Naruto'})
        self.assertEqual((props['step.0.title'], props['secondary'], actions), ('Not added', 'Choose a Version', ('repair', 'choose', '')))

    def test_copying_and_movie(self):
        props, actions = self.lm.fill_item(self.rows()[5], {'title': 'Naruto'})
        self.assertEqual((props['step.0.state'], props['step.0.pct'], actions), ('run', '61', ('close', '', '')))
        movie = self.data['movies'][0]
        props, actions = self.lm.fill_item(movie, None, 'movie')
        self.assertEqual((props['title'], props['sub'], props['delete']), ('Fall', 'Movie \u00b7 2022', 'Delete Movie\u2026'))


class Repair(unittest.TestCase):
    """L5 (board C3): Repair looks the episode up again with Build Season's automatic pick, no version question."""
    def test_quality_of_the_show_first_then_any(self):
        import library_repair as lr
        rows = [{'id': 'a', 'quality': '1080p'}, {'id': 'b', 'quality': '1080p HDR'}, {'id': 'c', 'quality': '720p'}, {'id': None, 'quality': ''}]
        self.assertEqual(lr.qualities(rows), ['1080p', None])
        self.assertEqual(lr.qualities([{'id': None}]), [None])
        self.assertEqual(lr.quality_key('2160p · 14 GB'), '4k')

    def test_repair_queues_and_falls_back(self):
        import library_repair as lr
        calls = []
        def request(home, tmdb, season, episode, purpose, quality, title=''):
            calls.append((purpose, quality))
            return {'queued': quality is None}
        self.assertEqual(lr.repair(request, None, '46260', 'Naruto', 1, 9, ['1080p', None]), ('queued', 'any'))
        self.assertEqual(calls, [('queue', '1080p'), ('queue', None)])   # automatic pick, never the version menu
        busy = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('Another episode search is running. Try again when it finishes.'))
        self.assertEqual(lr.repair(busy, None, '1', 'X', 1, 1, [None])[0], 'none')
        self.assertEqual(lr.repair(lambda *a, **k: {}, None, '1', 'X', 1, 1, [None]), ('none', 'No version with seeds was found for it.'))

    def test_one_script_for_several_episodes(self):
        import library_repair as lr
        args = lr.script_args('46260', 'Naruto, Shippuden', [{'season': 1, 'episode': 9}, {'season': 1, 'episode': 3}], '1080p')
        self.assertEqual(args, ['tmdb=46260', 'title=Naruto  Shippuden', 'quality=1080p', 'episodes=1:3;1:9'])
        self.assertEqual(lr.episodes_arg(lr.args(args)['episodes']), [(1, 3), (1, 9)])

    def test_the_pages_use_it(self):
        root = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap'
        manager = (root / 'library_manager.py').read_text()
        self.assertIn("RunScript(service.kodi.ios.bootstrap,library_repair_page,%s)", manager)
        self.assertIn("repair_rows([r for r in problems if not r.get('id')], self.data, self.show, self.episodes)", manager)
        self.assertIn("'library_repair_page'", (root / 'default.py').read_text())


if __name__ == '__main__':
    unittest.main()
