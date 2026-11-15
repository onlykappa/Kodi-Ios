"""Sports: The Loop's provider, step 1 (DEC-057): discovery of its menu tree, bounded and read-only; no adapter yet, so no source."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_loop as sl  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_provider as sp  # noqa: E402


def folder(label, path):
    return {'label': label, 'file': path, 'filetype': 'directory'}


def item(label, path, plot=''):
    return {'label': label, 'file': path, 'filetype': 'file', 'plot': plot}


TREE = {
    'plugin://a/': [folder('Live', 'plugin://a/live'), folder('Leagues', 'plugin://a/leagues'), item('Settings', 'plugin://a/settings')],
    'plugin://a/live': [item('NFL | PIT vs CLE', 'plugin://a/play?id=1', 'Steelers at Browns'), folder('Today', 'plugin://a/today')],
    'plugin://a/leagues': [folder('NFL', 'plugin://a/nfl'), folder('NBA', 'plugin://a/nba')],
    'plugin://a/today': [folder('Deep', 'plugin://a/deep')],
    'plugin://a/nfl': [item('Game', 'plugin://a/play?id=2')],
    'plugin://a/nba': [],
    'plugin://a/deep': [item('Too deep', 'plugin://a/play?id=3')],
}


class Rpc:
    def __init__(self, tree=None, fail=()):
        self.tree, self.fail, self.calls = TREE if tree is None else tree, set(fail), []

    def __call__(self, method, params=None):
        self.calls.append((method, (params or {}).get('directory')))
        path = params['directory']
        if path in self.fail or path not in self.tree:
            raise ValueError('Failed to get directory')
        return {'files': self.tree[path]}


class Walk(unittest.TestCase):
    def test_folders_are_listed_and_items_are_only_recorded(self):
        rpc = Rpc()
        nodes = sl.walk(rpc, 'plugin://a/')
        self.assertEqual({m for m, _ in rpc.calls}, {'Files.GetDirectory'})   # read-only: nothing is played or resolved
        listed = [p for _, p in rpc.calls]
        self.assertNotIn('plugin://a/play?id=1', listed)
        self.assertNotIn('plugin://a/settings', listed)
        labels = [(n['depth'], n['label'], n['folder']) for n in nodes]
        self.assertIn((2, 'NFL | PIT vs CLE', False), labels)   # an item sits one level below the folder that lists it
        self.assertIn((0, '', True), labels)
        self.assertIn((1, 'Live', True), labels)

    def test_depth_is_bounded(self):
        nodes = sl.walk(Rpc(), 'plugin://a/', depth=3)
        self.assertNotIn('Too deep', [n['label'] for n in nodes])   # three levels: the folder 'Deep' is seen, its contents are not listed
        self.assertIn('Deep', [n['label'] for n in nodes])
        self.assertLessEqual(max(n['depth'] for n in nodes), 3)
        shallow = sl.walk(Rpc(), 'plugin://a/', depth=1)
        self.assertEqual([n['depth'] for n in shallow], [0, 1, 1, 1])

    def test_a_flood_of_items_does_not_starve_the_folders(self):
        tree = {'plugin://f/': [item('E%d' % i, 'plugin://f/e%d' % i) for i in range(300)] + [folder('Leagues', 'plugin://f/leagues')],
                'plugin://f/leagues': [item('NFL', 'plugin://f/nfl')]}
        nodes = sl.walk(Rpc(tree), 'plugin://f/')
        self.assertEqual(sum(1 for n in nodes if n['depth'] == 1 and not n['folder']), sl.SAMPLES)
        self.assertEqual(next(n for n in nodes if n['depth'] == 0)['items'], 301)   # the count is kept
        self.assertIn('NFL', [n['label'] for n in nodes])

    def test_the_number_of_nodes_is_bounded(self):
        big = {'plugin://b/': [folder('F%d' % i, 'plugin://b/%d' % i) for i in range(50)]}
        big.update({'plugin://b/%d' % i: [item('I%d' % j, 'plugin://b/p%d%d' % (i, j)) for j in range(50)] for i in range(50)})
        self.assertLessEqual(len(sl.walk(Rpc(big), 'plugin://b/', nodes=60)), 60)

    def test_the_time_is_bounded(self):
        ticks = iter(range(0, 1000, 10))
        nodes = sl.walk(Rpc(), 'plugin://a/', clock=lambda: next(ticks), seconds=25)
        self.assertLessEqual(len(nodes), 4)   # the clock moves 10 s a look: it stops after about three folders

    def test_a_failing_folder_is_recorded_and_the_rest_goes_on(self):
        nodes = sl.walk(Rpc(fail=['plugin://a/live']), 'plugin://a/')
        live = next(n for n in nodes if n['label'] == 'Live')
        self.assertTrue(live['folder'])
        broken = next(n for n in nodes if n['path'] == 'plugin://a/live' and n['depth'] == 1 and n['error'])
        self.assertIn('ValueError', broken['error'])
        self.assertIn('NFL', [n['label'] for n in nodes])

    def test_long_text_is_cut_and_marked(self):
        nodes = sl.walk(Rpc({'plugin://c/': [item('x' * 300, 'plugin://c/' + 'y' * 400, 'z' * 300)]}), 'plugin://c/')
        n = nodes[1]
        self.assertTrue(n['label'].endswith('[cut]') and len(n['label']) < 100)
        self.assertTrue(n['path'].endswith('[cut]') and n['plot'].endswith('[cut]'))


class Discover(unittest.TestCase):
    def test_every_loop_add_on_is_tried_and_a_missing_one_says_so(self):
        tree = {'plugin://%s/' % sl.PLUGINS[0]: [item('Hello', 'plugin://x/1')]}
        result = sl.discover(Rpc(tree), now=lambda: 123)
        self.assertEqual((result['time'], sorted(result['plugins'])), (123, sorted(sl.PLUGINS)))
        self.assertEqual(result['plugins'][sl.PLUGINS[0]]['nodes'][1]['label'], 'Hello')
        self.assertIn('ValueError', result['plugins'][sl.PLUGINS[1]]['nodes'][0]['error'])

    def test_the_log_is_short_and_says_what_is_there(self):
        tree = {'plugin://%s/' % sl.PLUGINS[0]: [folder('Live', 'plugin://x/live')] + [item('G%d' % i, 'plugin://x/%d' % i) for i in range(300)],
                'plugin://x/live': [item('One', 'plugin://x/1')]}   # (the folder is listed; its entry says "Live")
        lines = sl.log_lines(sl.discover(Rpc(tree)))
        self.assertLessEqual(len(lines), sl.LOG_LINES)
        self.assertTrue(lines[0].startswith('the-loop folder |'))
        self.assertTrue(any('folder | Live |' in line for line in lines))

    def test_kodis_rpc_answers_and_errors(self):
        xbmc = types.SimpleNamespace(executeJSONRPC=lambda body: json.dumps({'result': {'files': [1]}}))
        self.assertEqual(sl.kodi_rpc(xbmc)('Files.GetDirectory', {}), {'files': [1]})
        bad = types.SimpleNamespace(executeJSONRPC=lambda body: json.dumps({'error': {'message': 'nope'}}))
        with self.assertRaises(ValueError):
            sl.kodi_rpc(bad)('Files.GetDirectory', {})


class Once(unittest.TestCase):
    def test_it_runs_once_a_day_and_writes_the_tree_and_the_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            xbmc = types.SimpleNamespace(executeJSONRPC=lambda body: json.dumps({'result': {'files': [item('Hi', 'plugin://x/1')]}}))
            xbmcvfs = types.SimpleNamespace(translatePath=lambda p: tmp + '/')
            lines = []
            first = sl.discover_once(xbmc, xbmcvfs, lines.append, now=lambda: 5000)
            self.assertIsNotNone(first)
            with open(os.path.join(tmp, sl.OUT), encoding='utf-8') as fh:
                saved = json.load(fh)
            self.assertEqual(sorted(saved['plugins']), sorted(sl.PLUGINS))
            self.assertTrue(any('discovery:' in l and 'Hi' in l for l in lines))
            self.assertIn('written to', lines[-1])
            before = len(lines)
            self.assertIsNone(sl.discover_once(xbmc, xbmcvfs, lines.append, now=lambda: os.path.getmtime(os.path.join(tmp, sl.OUT)) + 60))
            self.assertEqual(len(lines), before)   # lately done: nothing again
            self.assertIsNotNone(sl.discover_once(xbmc, xbmcvfs, lines.append, now=lambda: os.path.getmtime(os.path.join(tmp, sl.OUT)) + sl.EVERY + 1))

    def test_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x')
            self.assertTrue(sl.due(path, 100))
            open(path, 'w').close()
            m = os.path.getmtime(path)
            self.assertFalse(sl.due(path, m + 10))
            self.assertTrue(sl.due(path, m + sl.EVERY))


class Provider(unittest.TestCase):
    def test_no_adapter_yet_so_no_source_and_the_discovery_starts_once(self):
        started = []
        p = sl.LoopProvider(starter=lambda: started.append(1))
        for call in (p.overview, p.live_games, p.upcoming_games, p.leagues, p.refresh, lambda: p.game('x')):
            with self.assertRaises(sm.SportsUnavailable):
                call()
        self.assertEqual(started, [1])

    def test_pages_get_it_when_nothing_is_forced(self):
        os.environ.pop('KODI_IOS_SPORTS', None)
        sp.reset()
        try:
            self.assertIsInstance(sp.get(), sl.LoopProvider)
            with self.assertRaises(sm.SportsUnavailable):   # outside Kodi the discovery does not start (no xbmc to ask)
                sp.get().overview()
        finally:
            sp.reset()


if __name__ == '__main__':
    unittest.main()
