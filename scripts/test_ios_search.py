"""Board 12: the Search page's All results in MOVIES / TV SHOWS sections (ios_search.py in the watch add-on)."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parents[1] / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
spec = importlib.util.spec_from_file_location('ios_search', LIB / 'ios_search.py')
ios_search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ios_search)


class Sections(unittest.TestCase):
    def test_headings_lead_each_section_and_empty_ones_go(self):
        out = ios_search.grouped([('movie', 'MOVIES', [{'label': 'The Maze Runner'}]), ('tv', 'TV SHOWS', [])])
        self.assertEqual(out, [('header', 'MOVIES'), ('item', 'movie', {'label': 'The Maze Runner'})])

    def test_each_section_keeps_its_best_few(self):
        out = ios_search.grouped([('movie', 'MOVIES', [{'label': str(n)} for n in range(20)]), ('tv', 'TV SHOWS', [{'label': 'a'}])])
        self.assertEqual([e[0] for e in out].count('item'), ios_search.PER_SECTION + 1)
        self.assertEqual(out[ios_search.PER_SECTION + 1], ('header', 'TV SHOWS'))

    def test_both_searches_asked_in_order(self):
        asked = []

        def rpc(text):
            path = json.loads(text)['params']['directory']
            asked.append(path)
            kind = 'movie' if 'tmdb_type=movie' in path else 'tv'
            return json.dumps({'result': {'files': [{'label': kind + ' hit'}]}})
        result = ios_search.fetch(rpc, 'maze runner')
        self.assertEqual([(k, t, [f['label'] for f in files]) for k, t, files in result],
                         [('movie', 'MOVIES', ['movie hit']), ('tv', 'TV SHOWS', ['tv hit'])])
        self.assertTrue(all('query=maze%20runner' in p for p in asked))

    def test_a_failed_search_is_an_empty_section(self):
        result = ios_search.fetch(lambda text: 'not json', 'x')
        self.assertEqual([files for _, _, files in result], [[], []])


if __name__ == '__main__':
    unittest.main()
