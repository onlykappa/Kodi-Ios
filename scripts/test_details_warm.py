"""Roadmap 1C.4: TMDb Helper's details for the titles on screen are fetched in the background before Play is tapped."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'scripts'))
import details_warm as dw

WATCH = ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py'


def movie(tmdb):
    return {'label': 'M' + tmdb, 'path': 'plugin://x', 'info': {'mediatype': 'movie'}, 'ids': {'tmdb': tmdb}}


def show(tmdb):
    return {'label': 'S' + tmdb, 'path': 'plugin://x', 'info': {'mediatype': 'tvshow'}, 'props': {'tmdb_id': tmdb}}


class Targets(unittest.TestCase):
    def test_hero_items_and_continue_records_become_targets(self):
        self.assertEqual(dw.from_item(movie('11')), {'tmdb_type': 'movie', 'tmdb_id': '11'})
        self.assertEqual(dw.from_item(show('22')), {'tmdb_type': 'tv', 'tmdb_id': '22'})
        for bad in (None, {}, {'info': {'mediatype': 'season'}, 'ids': {'tmdb': '1'}}, {'info': {'mediatype': 'movie'}, 'ids': {'tmdb': 'x'}}):
            self.assertIsNone(dw.from_item(bad))
        self.assertEqual(dw.from_continue({'kind': 'episode', 'tmdb_id': '33', 'season': '2', 'episode': '5'}),
                         {'tmdb_type': 'tv', 'tmdb_id': '33', 'season': '2', 'episode': '5'})
        self.assertEqual(dw.from_continue({'kind': 'movie', 'tmdb_id': '44'}), {'tmdb_type': 'movie', 'tmdb_id': '44'})
        self.assertIsNone(dw.from_continue({'kind': 'movie', 'tmdb_id': ''}))

    def test_continue_watching_comes_first_newest_first_then_the_first_three_of_each_hero(self):
        found = dw.collect([[movie('1'), movie('2'), movie('3'), movie('4')], [show('5')]],
                           [{'kind': 'movie', 'tmdb_id': '90', 'played': 1}, {'kind': 'movie', 'tmdb_id': '91', 'played': 9}])
        self.assertEqual([t['tmdb_id'] for t in found], ['91', '90', '1', '2', '3', '5'])

    def test_no_duplicates_and_a_limit(self):
        self.assertEqual(len(dw.collect([[movie('1'), movie('1')]], [{'kind': 'movie', 'tmdb_id': '1'}])), 1)
        many = [[movie(str(n)) for n in range(3)] for _ in range(1)]
        self.assertEqual(len(dw.collect(many * 6, [], limit=4)), 3)    # duplicates collapse
        self.assertEqual(len(dw.collect([[movie(str(n))] for n in range(30)], [], limit=5)), 5)

    def test_the_route_url_uses_the_helper_and_its_own_info_name(self):
        url = dw.url({'tmdb_type': 'tv', 'tmdb_id': '7', 'season': '1', 'episode': '2'})
        self.assertTrue(url.startswith('plugin://plugin.video.themoviedb.helper/?'))
        for part in ('info=ios_warm', 'tmdb_type=tv', 'tmdb_id=7', 'season=1', 'episode=2'):
            self.assertIn(part, url)


class Run(unittest.TestCase):
    def test_each_title_is_asked_once_per_ttl_and_never_during_a_video(self):
        with tempfile.TemporaryDirectory() as profile:
            asked, clock = [], [1000.0]
            targets = [{'tmdb_type': 'movie', 'tmdb_id': '1'}, {'tmdb_type': 'movie', 'tmdb_id': '2'}]
            kw = dict(run_plugin=asked.append, wait=lambda s: False, now=lambda: clock[0], pause=0)
            self.assertEqual(dw.run(targets, profile, busy=lambda: False, **kw), 2)
            self.assertEqual(dw.run(targets, profile, busy=lambda: False, **kw), 0)            # asked already
            clock[0] += dw.TTL + 1
            self.assertEqual(dw.run(targets[:1], profile, busy=lambda: False, **kw), 1)       # the TTL ran out
            self.assertEqual(dw.run([{'tmdb_type': 'movie', 'tmdb_id': '3'}], profile, busy=lambda: True, **kw), 0)
            self.assertEqual(len(asked), 3)
            self.assertTrue(all('info=ios_warm' in u for u in asked))

    def test_it_stops_when_kodi_exits_and_survives_a_damaged_marker(self):
        with tempfile.TemporaryDirectory() as profile:
            marker = Path(profile) / dw.MARKER
            marker.parent.mkdir(parents=True)
            marker.write_text('not json')
            asked = []
            n = dw.run([{'tmdb_type': 'movie', 'tmdb_id': str(i)} for i in range(5)], profile, asked.append, lambda s: True, lambda: False)
            self.assertEqual((n, len(asked)), (1, 1))


class Route(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('watch_warm', WATCH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_warm_details_builds_the_same_details_play_uses(self):
        m, built = self.load(), []

        class Details(object):
            def __init__(self, *args):
                built.append(args)

            @property
            def details(self):
                built.append('fetched')
                return object()
        self.assertTrue(m.warm_details({'tmdb_type': 'tv', 'tmdb_id': '7', 'season': '1', 'episode': '2'}, Details))
        self.assertEqual(built, [('tv', '7', '1', '2'), 'fetched'])
        built.clear()
        self.assertTrue(m.warm_details({'tmdb_type': 'movie', 'tmdb_id': '9'}, Details))
        self.assertEqual(built[0], ('movie', '9', None, None))

    def test_bad_requests_and_failures_are_quiet(self):
        m = self.load()

        class Broken(object):
            def __init__(self, *args):
                raise RuntimeError('synthetic')
        self.assertFalse(m.warm_details({'tmdb_type': 'movie', 'tmdb_id': '9'}, Broken))
        self.assertFalse(m.warm_details({'tmdb_type': 'person', 'tmdb_id': '9'}, Broken))
        self.assertFalse(m.warm_details({'tmdb_type': 'movie', 'tmdb_id': 'x'}, Broken))

    def test_the_build_adds_the_route_to_tmdb_helper_and_skips_quietly_when_the_anchor_moves(self):
        from build_import_review import patch_helper
        prefix = 'plugin.video.themoviedb.helper/'
        tmdb = ROOT / 'scripts'
        source = (Path(__file__).resolve().parent / 'test_import_builder.py').read_text()
        self.assertIn('patch_helper', source)           # the existing fixture builder lives there
        import test_import_builder as builder
        case = builder.BuilderTests()
        p, files = case.fixture()
        router = p + 'resources/tmdbhelper/lib/items/router.py'
        files[router] = (b"class Router:\n    def run(self):\n        if self.params.get('info') == 'play':\n            return self.play_player()\n"
                         b"        self.get_directory()\n    def play_player(self):\n"
                         b"        play_player(handle=self.handle if self.handle != -1 else None, **self.params)\n")
        out, changes = patch_helper(files, 'plugin.video.themoviedb.helper')
        text = out[router].decode()
        self.assertLess(text.index("'ios_warm'"), text.index("== 'play'"))
        compile(text, 'router.py', 'exec')
        self.assertTrue(any('titles on screen' in c for c in changes))
        p, files = case.fixture()
        files[router] = b"class Router:\n    def run(self):\n        self.get_directory()\n    def play_player(self):\n" \
                        b"        play_player(handle=self.handle if self.handle != -1 else None, **self.params)\n"
        out, changes = patch_helper(files, 'plugin.video.themoviedb.helper')
        self.assertNotIn('ios_warm', out[router].decode())      # no failure, just no warm-up


if __name__ == '__main__':
    unittest.main()
