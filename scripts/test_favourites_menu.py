"""ISSUE-322 (owner, build 486): holding a favourite closed Favourites and Kodi's own menu opened over Home with "Add to
favourites". A long press on a poster opens the page's menu: Download, View Details, and Remove from Favourites last.
ISSUE-323: a failed TMDb lookup is tried again and is never reported as "not found"."""
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path[:0] = [str(BOOT), str(BOOT / 'resources/lib')]
sys.dont_write_bytecode = True
import favourites_page as fp      # noqa: E402
import favourites_rows as fr      # noqa: E402
import favourites_match as fm     # noqa: E402


class Menu(unittest.TestCase):
    def test_a_show_offers_download_details_and_remove_last(self):
        e = fr.imported_entry({'kind': 'tv', 'tmdb': '73223', 'title': 'Black Clover, (2017)', 'year': '2017'})
        options = fp.menu_options(e)
        self.assertEqual([o[0]['label'] for o in options], ['Download', 'View Details', 'Remove from Favourites'])
        self.assertEqual(options[0][1], 'RunScript(service.kodi.ios.bootstrap,download,kind=tvshow,tmdb=73223,title=Black Clover 2017,year=2017)')
        self.assertEqual(options[1][1], 'RunScript(plugin.video.themoviedb.helper,add_tmdb=73223,tmdb_type=tv,call_auto=1190)')
        self.assertEqual(options[-1][1], 'remove')
        self.assertFalse(any('favourite' in o[0]['label'].lower() and 'remove' not in o[0]['label'].lower() for o in options))

    def test_a_movie_downloads_as_a_movie(self):
        e = fr.imported_entry({'kind': 'movie', 'tmdb': '27205', 'title': 'Inception', 'year': '2010'})
        self.assertIn('kind=movie,tmdb=27205', fp.menu_options(e)[0][1])

    def test_a_favourite_without_an_id_can_still_be_removed(self):
        e = {'title': 'Some folder', 'kind': '', 'removable': True, 'tmdb': ''}
        self.assertEqual([o[1] for o in fp.menu_options(e)], ['remove'])

    def test_the_page_reads_a_long_press_as_the_menu_not_back(self):
        source = (BOOT / 'favourites_page.py').read_text()
        self.assertIn('LONG = (101, 117)', source)
        self.assertIn('if code in LONG or code == 10:', source)
        self.assertLess(source.index('if code in LONG or code == 10:'), source.index('if code in BACK:'))


class Lookups(unittest.TestCase):
    def test_a_failed_lookup_is_tried_again(self):
        calls = []

        def search(query):
            calls.append(query)
            if len(calls) < 3:
                raise TimeoutError('slow')
            return [{'id': 1, 'media_type': 'tv', 'name': 'Black Clover', 'first_air_date': '2017-10-03', 'popularity': 50}]
        with mock.patch.object(fm, 'pause', lambda s: None):
            result = fm.run([{'title': 'Black Clover', 'rank': 1, 'line': 1}], search)
        self.assertEqual(len(result['matched']), 1)
        self.assertEqual(result['missing'], [])

    def test_a_lookup_that_keeps_failing_is_not_called_not_found(self):
        def search(query):
            raise TimeoutError('slow')
        with mock.patch.object(fm, 'pause', lambda s: None):
            result = fm.run([{'title': 'Black Clover', 'rank': 1, 'line': 1}], search)
        self.assertEqual([m.get('failed') for m in result['missing']], [True])


if __name__ == '__main__':
    unittest.main()
