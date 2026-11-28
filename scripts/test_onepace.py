"""One Pace as a show (owner, 2026-11-28): arcs are seasons, English dub where it exists, else Japanese with burned-in English subtitles, new episodes tracked.
Samples in scripts/fixtures are trimmed copies of the public watch page and release feed (Romance Dawn, Whisky Peak, two Thriller Bark episodes; three feed items)."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import onepace as op

import json
PAGE = json.loads((ROOT / 'scripts/fixtures/onepace_watch.json').read_text(encoding='utf-8'))['html']
FEED = (ROOT / 'scripts/fixtures/onepace_feed.xml').read_text(encoding='utf-8')


class Parse(unittest.TestCase):
    def test_arcs_episodes_and_variants_come_out_of_the_page(self):
        arcs = op.parse_watch(PAGE)
        self.assertEqual([(a['slug'], len(a['episodes'])) for a in arcs], [('romance-dawn', 4), ('whisky-peak', 2), ('thriller-bark', 2)])
        first = arcs[0]
        self.assertEqual((first['title'], first['chapters']), ('Romance Dawn', '1–7'))
        episode = first['episodes'][0]
        self.assertEqual((episode['number'], episode['minutes']), (1, 17))
        self.assertTrue(episode['title'].startswith('ROMANCE DAWN'))
        self.assertIn('Luffy', episode['plot'])
        self.assertEqual(set(episode['variants']), {'English Subtitles', 'English Dub', 'English Dub with Closed Captions'})
        self.assertEqual(episode['variants']['English Dub']['1080p'], 'https://pixeldrain.net/u/gpR8Tf9E')
        self.assertEqual(set(episode['variants']['English Dub']), {'480p', '720p', '1080p'})
    def test_the_all_in_one_batch_is_not_an_episode_variant(self):
        for arc in op.parse_watch(PAGE):
            for episode in arc['episodes']:
                self.assertNotIn('All-in-One', episode['variants'])
    def test_other_markup_gives_nothing_not_an_error(self):
        for text in ('', None, '<html></html>', '<main><li data-timeline-segment="x"></li></main>'):
            self.assertIsInstance(op.parse_watch(text), list)


class Choice(unittest.TestCase):
    def episodes(self):
        arcs = op.parse_watch(PAGE)
        return {a['slug']: a['episodes'] for a in arcs}
    def test_the_dub_plays_when_there_is_one_at_the_best_resolution(self):
        got = op.choose(self.episodes()['romance-dawn'][0])
        self.assertEqual((got['audio'], got['japanese_only'], got['resolution']), ('English dub', False, '1080p'))
        self.assertEqual(got['file'], 'https://pixeldrain.net/api/file/gpR8Tf9E')
    def test_without_a_dub_it_is_japanese_with_english_subtitles_and_marked_so(self):
        got = op.choose(self.episodes()['whisky-peak'][0])
        self.assertEqual((got['audio'], got['japanese_only']), ('Japanese', True))
        self.assertTrue(got['file'].startswith('https://pixeldrain.net/api/file/'))
    def test_the_viewer_can_ask_for_the_japanese_file_of_a_dubbed_episode(self):
        episode = self.episodes()['romance-dawn'][0]
        got = op.choose(episode, prefer='japanese')
        self.assertEqual((got['audio'], got['japanese_only']), ('Japanese', False))   # a dub exists: not "Japanese only"
        self.assertEqual(got['page'], episode['variants']['English Subtitles']['1080p'])
    def test_resolution_falls_back_and_an_episode_with_nothing_has_no_choice(self):
        episode = {'variants': {'English Dub': {'480p': 'https://pixeldrain.net/u/AAA', '720p': 'https://pixeldrain.net/u/BBB'}}}
        self.assertEqual(op.choose(episode)['resolution'], '720p')
        self.assertIsNone(op.choose({'variants': {}}))
        self.assertIsNone(op.choose({}))
    def test_only_pixeldrain_pages_become_file_addresses(self):
        self.assertEqual(op.file_url('https://pixeldrain.net/u/abc123'), 'https://pixeldrain.net/api/file/abc123')
        for bad in ('', None, 'https://evil.example/u/abc', 'https://pixeldrain.net/l/abc', 'javascript:alert(1)'):
            self.assertEqual(op.file_url(bad), '')


class Show(unittest.TestCase):
    def test_every_arc_is_a_season_and_every_released_episode_plays(self):
        seasons = op.seasons(op.parse_watch(PAGE))
        self.assertEqual([(s['season'], s['title'], len(s['episodes']), s['dubbed']) for s in seasons],
                         [(1, 'Romance Dawn', 4, 4), (2, 'Whisky Peak', 2, 0), (3, 'Thriller Bark', 2, 0)])
        self.assertFalse(any(s['upcoming'] for s in seasons))
        self.assertTrue(all(e['file'] for s in seasons for e in s['episodes']))
    def test_an_arc_with_no_episode_yet_is_an_empty_upcoming_season(self):
        seasons = op.seasons([{'slug': 'new', 'title': 'New Arc', 'chapters': '', 'anime': '', 'episodes': []}])
        self.assertEqual((seasons[0]['upcoming'], seasons[0]['episodes']), (True, []))


class Feed(unittest.TestCase):
    def test_releases(self):
        items = op.parse_feed(FEED)
        self.assertEqual(len(items), 3)
        self.assertEqual((items[0]['chapters'], items[0]['name'], items[0]['resolution'], items[0]['category']), ('1014-1015', 'Wano 63', '1080p', 'cut/regular'))
        self.assertEqual(len(items[0]['hash']), 40)
    def test_a_broken_or_empty_feed_is_nothing(self):
        for text in ('', None, '<rss>', 'not xml at all', '<item><title></title></item>'):
            self.assertEqual(op.parse_feed(text), [])


class NewThings(unittest.TestCase):
    def state(self):
        return op.signature(op.seasons(op.parse_watch(PAGE)))
    def test_the_first_look_reports_nothing(self):
        self.assertEqual(op.changes({}, op.seasons(op.parse_watch(PAGE))), [])
    def test_unchanged_reports_nothing(self):
        self.assertEqual(op.changes(self.state(), op.seasons(op.parse_watch(PAGE))), [])
    def test_a_new_episode_a_new_dub_and_a_new_arc_are_each_reported(self):
        seasons = op.seasons(op.parse_watch(PAGE))
        before = self.state()
        before['romance-dawn'] = [3, 3]                        # one episode (dubbed) fewer than now
        before['whisky-peak'] = [2, -1]                        # a dub appeared
        del before['thriller-bark']                            # a whole arc is new
        kinds = sorted((c['kind'], c['arc']) for c in op.changes(before, seasons))
        self.assertIn(('arc', 'Thriller Bark'), kinds); self.assertIn(('episode', 'Romance Dawn'), kinds)
        self.assertIn(('dub', 'Romance Dawn'), kinds); self.assertIn(('dub', 'Whisky Peak'), kinds)


class ChipName(unittest.TestCase):
    def test_long_arc_names_are_cut_at_a_word_for_the_chip(self):
        self.assertEqual(op.chip_name('Romance Dawn'), 'Romance Dawn'); self.assertEqual(op.chip_name('Special: One Piece Fan Letter'), 'One Piece Fan\u2026')
        self.assertEqual(op.chip_name('Sabaody Archipelago'), 'Sabaody\u2026'); self.assertEqual(op.chip_name(''), ''); self.assertTrue(len(op.chip_name('x' * 40)) <= 16)


if __name__ == '__main__':
    unittest.main()
