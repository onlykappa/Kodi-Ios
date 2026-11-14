"""Favourites list import: reading a Notes list, matching names, saving and sorting (mockup boards H-J)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'scripts'))
import favourites_import as fi
import favourites_match as fm

NOTES = """✅=Complete upto available episodes
‼️=Has More coming
 need to get clips

1. Naruto\U0001f3a5//shippuden✅
2. bleach\U0001f3a5 ✅ ‼️
3. dragon ball//Z//super ✅
4. aot (3)✅  RYANNE
5. MHA \U0001f3a5 ✅ ‼️
6. Beserk (STARTED)
9. Jujutsu kaisen ✅ ‼️ (3) RYANNE
38. life of immortal king
40. heavenly delusion (STARTED)✅
46. darling in the franxx ✅
50. darling in the franxx ✅
60. heavenly delusion (STARTED) ng
64. one peice
"""


def titles(raw):
    return [e['title'] for e in fi.parse(raw)['entries']]


class Reading(unittest.TestCase):
    def test_only_names_are_taken_and_the_key_is_skipped(self):
        got = fi.parse(NOTES)
        names = [e['title'] for e in got['entries']]
        self.assertEqual(names[:9], ['Naruto', 'Naruto shippuden', 'bleach', 'dragon ball', 'dragon ball Z', 'dragon ball super',
                                      'aot', 'MHA', 'Beserk'])
        self.assertNotIn('RYANNE', ' '.join(names))
        self.assertFalse([n for n in names if 'complete' in n.lower() or 'clips' in n.lower()])
        for n in names:
            self.assertTrue(all(c.isalnum() or c in " :/-'&." for c in n), n)

    def test_rank_is_list_order_and_a_bracketed_number_is_the_watch_count(self):
        got = {e['title']: e for e in fi.parse(NOTES)['entries']}
        self.assertEqual(got['Naruto']['rank'], 1)
        self.assertEqual(got['aot']['watched'], 3)
        self.assertEqual(got['Jujutsu kaisen']['watched'], 3)
        self.assertEqual(got['Beserk']['watched'], 0)         # (STARTED) is a note, not a count
        self.assertEqual([e['rank'] for e in fi.parse(NOTES)['entries']], list(range(1, len(fi.parse(NOTES)['entries']) + 1)))

    def test_slashes_split_and_a_title_with_a_slash_alone_stays_whole(self):
        self.assertEqual(titles('1. dragon ball//Z//super'), ['dragon ball', 'dragon ball Z', 'dragon ball super'])
        self.assertEqual(titles('1. Fate/zero\n2. Re:Zero'), ['Fate/zero', 'Re:Zero'])

    def test_duplicates_are_reported_with_their_lines_and_added_once(self):
        got = fi.parse(NOTES)
        self.assertEqual(got['duplicates'], [{'title': 'darling in the franxx', 'lines': [46, 50]}])
        self.assertEqual(titles(NOTES).count('darling in the franxx'), 1)

    def test_a_paste_without_line_breaks_still_splits_on_numbers(self):
        self.assertEqual(titles('1. Naruto 2. bleach (2) 3. aot RYANNE'), ['Naruto', 'bleach', 'aot'])

    def test_a_plain_list_and_year_hints(self):
        got = fi.parse('Inception (2010)\n\nThe Batman (2022)\nSpirited Away')
        self.assertEqual([(e['title'], e['year']) for e in got['entries']],
                         [('Inception', '2010'), ('The Batman', '2022'), ('Spirited Away', '')])

    def test_all_capitals_titles_are_kept(self):
        self.assertEqual(titles('1. MHA\n2. Fire Force RYAN'), ['MHA', 'Fire Force'])

    def test_empty_and_marker_only_lines_give_nothing(self):
        self.assertEqual(fi.parse('')['entries'], [])
        self.assertEqual(titles('1. ✅‼️\n2. (STARTED)'), [])


def fake_search(table):
    return lambda query: table.get(fm.norm(query), [])


def tv(i, name, pop=10, year='2011-01-01'):
    return {'media_type': 'tv', 'id': i, 'name': name, 'first_air_date': year, 'popularity': pop, 'poster_path': '/p%d.jpg' % i}


def movie(i, name, pop=10, year='2011-01-01'):
    return {'media_type': 'movie', 'id': i, 'title': name, 'release_date': year, 'popularity': pop}


class Matching(unittest.TestCase):
    def test_an_exact_title_matches_and_a_clear_winner_beats_a_remake(self):
        search = fake_search({'one piece': [tv(1, 'One Piece', 200), tv(2, 'One Piece', 20, '2023-01-01')]})
        status, found = fm.resolve('One Piece', search)
        self.assertEqual((status, found['tmdb']), ('match', '1'))

    def test_equal_exact_titles_are_asked_not_guessed(self):
        search = fake_search({'the batman': [movie(1, 'The Batman', 50), tv(2, 'The Batman', 45)]})
        status, found = fm.resolve('The Batman', search)
        self.assertEqual(status, 'question')
        self.assertEqual([c['tmdb'] for c in found], ['1', '2'])

    def test_a_misspelling_is_a_question_with_the_close_title(self):
        search = fake_search({'one peice': [tv(1, 'One Piece', 200), movie(3, 'One Piece Film: Red', 40)]})
        status, found = fm.resolve('one peice', search)
        self.assertEqual(status, 'question')
        self.assertEqual(found[0]['title'], 'One Piece')

    def test_a_stray_trailing_word_is_dropped_on_the_second_try(self):
        search = fake_search({'heavenly delusion': [tv(7, 'Heavenly Delusion', 30)]})
        status, found = fm.resolve('heavenly delusion ng', search)
        self.assertEqual((status, found['tmdb']), ('match', '7'))

    def test_nothing_found_is_missing(self):
        self.assertEqual(fm.resolve('zzzz', fake_search({})), ('missing', None))

    def test_results_that_do_not_look_like_the_name_are_asked_not_guessed(self):
        status, found = fm.resolve('zzzz', fake_search({'zzzz': [tv(1, 'Something Else Entirely')]}))
        self.assertEqual((status, found[0]['title']), ('question', 'Something Else Entirely'))

    def test_an_abbreviation_matches_the_titles_initials(self):
        search = fake_search({'aot': [tv(4, 'Attack on Titan', 200), tv(9, 'Another Old Tale', 5)],
                              'mha': [tv(5, 'My Hero Academia', 150)]})
        self.assertEqual(fm.resolve('aot', search)[1]['tmdb'], '4')
        self.assertEqual(fm.resolve('MHA', search)[1]['tmdb'], '5')

    def test_run_groups_results_and_catches_same_title_under_two_names(self):
        entries = fi.parse('1. heavenly delusion\n2. heavenly delusion ng\n3. one peice\n4. zzzz')['entries']
        search = fake_search({'heavenly delusion': [tv(7, 'Heavenly Delusion', 30)], 'one peice': [tv(1, 'One Piece', 200)]})
        out = fm.run(entries, search)
        self.assertEqual([m['tmdb'] for m in out['matched']], ['7'])
        self.assertEqual(out['duplicates'], [{'title': 'Heavenly Delusion', 'lines': [1, 2]}])
        self.assertEqual([q['entry']['title'] for q in out['questions']], ['one peice'])
        self.assertEqual([m['title'] for m in out['missing']], ['zzzz'])

    def test_a_search_that_fails_never_stops_the_import(self):
        def broken(query):
            raise OSError('offline')
        out = fm.run(fi.parse('1. Naruto')['entries'], broken)
        self.assertEqual(len(out['missing']), 1)

    def test_cancel_stops_between_names(self):
        calls = []
        out = fm.run(fi.parse('1. a1\n2. b2\n3. c3')['entries'], lambda q: calls.append(q) or [], cancelled=lambda: len(calls) >= 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(out['missing']), 1)


class Saving(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name

    def rows(self):
        return [{'kind': 'tv', 'tmdb': '1', 'title': 'Naruto', 'year': '2002', 'rank': 1, 'watched': 0},
                {'kind': 'tv', 'tmdb': '2', 'title': 'Bleach', 'year': '2004', 'rank': 2, 'watched': 3},
                {'kind': 'movie', 'tmdb': '3', 'title': 'The Batman', 'year': '2022', 'rank': 3}]

    def test_added_in_order_and_a_second_import_continues_and_skips_known(self):
        added, already = fi.add(self.profile, self.rows(), 'List A', now=100)
        self.assertEqual([i['rank'] for i in added], [1, 2, 3])
        self.assertEqual(already, [])
        again = fi.add(self.profile, [dict(self.rows()[0], rank=1), {'kind': 'tv', 'tmdb': '9', 'title': 'Z', 'rank': 2}], 'List B', now=200)
        self.assertEqual([i['title'] for i in again[0]], ['Z'])
        self.assertEqual(len(again[1]), 1)
        saved = fi.load(self.profile)['items']
        self.assertEqual([i['rank'] for i in saved], [1, 2, 3, 4])
        self.assertEqual(saved[3]['list'], 'List B')

    def test_sorting(self):
        fi.add(self.profile, self.rows(), 'List A', now=100)
        fi.add(self.profile, [{'kind': 'tv', 'tmdb': '9', 'title': 'Angels', 'year': '2015', 'rank': 1}], 'List B', now=200)
        items = fi.load(self.profile)['items']
        names = lambda key: [i['title'] for i in fi.ordered(items, key)]
        self.assertEqual(names('list'), ['Naruto', 'Bleach', 'The Batman', 'Angels'])
        self.assertEqual(names('year'), ['The Batman', 'Angels', 'Bleach', 'Naruto'])
        self.assertEqual(names('name')[0], 'Angels')
        self.assertEqual(names('name')[1], 'The Batman')       # "The" is ignored: B for Batman before Bleach
        self.assertEqual(names('imported')[-1], 'Angels')
        self.assertEqual(names('added')[0], 'Angels')

    def test_remove_and_a_broken_file(self):
        fi.add(self.profile, self.rows(), 'A', now=1)
        fi.remove(self.profile, {'kind': 'tv', 'tmdb': '1'})
        self.assertEqual([i['tmdb'] for i in fi.load(self.profile)['items']], ['2', '3'])
        Path(fi.path(self.profile)).write_text('{broken')
        self.assertEqual(fi.load(self.profile)['items'], [])

    def test_sort_choice_is_remembered_and_unknown_ignored(self):
        fi.set_sort(self.profile, 'year')
        fi.set_sort(self.profile, 'nonsense')
        self.assertEqual(fi.load(self.profile)['sort'], 'year')


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import settings_page
        import portrait
        cls.xml = settings_page.favourites_page(portrait)

    def test_import_sort_and_empty_button_exist(self):
        for control in ('9030', '9031', '9032'):
            self.assertIn('id="%s"' % control, self.xml)
        self.assertIn('Window().Property(sortlabel)', self.xml)

    def test_posters_carry_rank_and_watch_badges_from_properties(self):
        self.assertIn('Window().Property(fav.1.rank)', self.xml)
        self.assertIn('Window().Property(fav.1.watched)', self.xml)

    def test_rank_shows_only_in_list_order_and_the_grid_opens_imported_titles(self):
        import favourites_rows as fr
        rows = [fr.imported_entry({'kind': 'tv', 'tmdb': '5', 'title': 'Naruto', 'rank': 1, 'watched': 3, 'poster': '/a.jpg'}),
                fr.imported_entry({'kind': 'movie', 'tmdb': '6', 'title': 'Inception', 'rank': 2})]
        self.assertEqual(fr.properties(rows, True)['fav.1.rank'], '#1')
        self.assertEqual(fr.properties(rows, False)['fav.1.rank'], '')
        self.assertEqual(fr.properties(rows, True)['fav.1.watched'], '3\u00d7')
        self.assertEqual(fr.properties(rows, True)['fav.2.watched'], '')
        self.assertIn('info=seasons&tmdb_type=tv&tmdb_id=5', rows[0]['action'])
        self.assertIn('info=play&tmdb_type=movie&tmdb_id=6', rows[1]['action'])
        self.assertEqual(rows[0]['thumb'], 'https://image.tmdb.org/t/p/w342/a.jpg')
        self.assertTrue(rows[0]['removable'])
        self.assertEqual([r['title'] for r in fr.shown(rows, 'movie')], ['Inception'])
        self.assertEqual([r['title'] for r in fr.shown(rows, 'tv')], ['Naruto'])


if __name__ == '__main__':
    unittest.main()
