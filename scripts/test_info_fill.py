"""The Info card's description for a title Continue played from its remembered link (owner, 2026-11-24, build 688: an episode's card said "No description for this video yet.")."""
import json, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
import info_fill as fill


class Library:
    """The drivelibrary.season lookup: {episode number: {...}} for a season, cached."""
    calls = []
    @staticmethod
    def season(tmdb, number, key, cache, get, cached_only=False):
        Library.calls.append((tmdb, number))
        return {'1': {'title': 'The God Who Destroys', 'plot': 'Beerus wakes.'}, '8': {'title': 'Episode 8', 'plot': ''}}


EP = {'kind': 'episode', 'tmdb_id': '312359', 'season': '1', 'episode': '1'}


class Lookup(unittest.TestCase):
    def test_an_episode_takes_its_plot_from_its_season(self):
        self.assertEqual(fill.lookup(EP, 'k', {}, None, Library), {'plot': 'Beerus wakes.', 'title': 'The God Who Destroys'})
        self.assertEqual(fill.lookup(dict(EP, episode='8'), 'k', {}, None, Library)['plot'], '')            # TMDb has none for it: nothing is invented
        self.assertEqual(fill.lookup(dict(EP, episode='99'), 'k', {}, None, Library), {'plot': '', 'title': ''})
    def test_a_movie_takes_its_plot_from_its_page(self):
        asked = []
        def get(url): asked.append(url); return json.dumps({'overview': 'A thief.', 'title': 'Inception'})
        self.assertEqual(fill.lookup({'kind': 'movie', 'tmdb_id': '27205'}, 'KEY', {}, get, Library), {'plot': 'A thief.', 'title': 'Inception'})
        self.assertEqual(asked, ['https://api.themoviedb.org/3/movie/27205?api_key=KEY'])
        self.assertEqual(fill.lookup({'kind': 'movie', 'tmdb_id': '27205'}, 'KEY', {}, lambda url: (_ for _ in ()).throw(OSError('offline')), Library), {})
    def test_nothing_without_a_key_an_id_or_a_season(self):
        self.assertEqual(fill.lookup(EP, '', {}, None, Library), {}); self.assertEqual(fill.lookup(dict(EP, tmdb_id=''), 'k', {}, None, Library), {})
        self.assertEqual(fill.lookup(dict(EP, season='x'), 'k', {}, None, Library), {}); self.assertEqual(fill.lookup({'kind': 'other', 'tmdb_id': '1'}, 'k', {}, None, Library), {})


class Run(unittest.TestCase):
    def go(self, entry, has_plot=False):
        out = {'put': [], 'kept': []}
        plot = fill.run(entry, lambda: has_plot, 'k', {}, None, Library, out['put'].append, out['kept'].append)
        return plot, out
    def test_it_looks_the_plot_up_shows_it_and_keeps_it_with_the_record(self):
        plot, out = self.go(EP); self.assertEqual((plot, out), ('Beerus wakes.', {'put': ['Beerus wakes.'], 'kept': ['Beerus wakes.']}))
    def test_a_record_that_has_the_plot_shows_it_without_a_lookup(self):
        Library.calls.clear(); plot, out = self.go(dict(EP, plot='Kept earlier.'))
        self.assertEqual((plot, out['put'], out['kept'], Library.calls), ('Kept earlier.', ['Kept earlier.'], [], []))
    def test_a_playing_item_with_its_own_plot_is_left_alone(self):
        Library.calls.clear(); plot, out = self.go(EP, has_plot=True); self.assertEqual((plot, out['put'], Library.calls), ('', [], []))
    def test_no_plot_anywhere_shows_nothing_and_keeps_nothing(self):
        plot, out = self.go(dict(EP, episode='8')); self.assertEqual((plot, out['put'], out['kept']), ('', [], []))


class Wiring(unittest.TestCase):
    def test_the_record_keeps_the_plot_and_the_stream_player_gives_it_to_the_playing_item(self):
        import ios_continue
        class Details: infolabels = {'title': 'The God Who Destroys', 'tvshowtitle': 'Dragon Ball Super: Beerus', 'plot': 'Beerus wakes.'}; art = {}
        class Player: details = Details(); tmdb_type = 'tv'; tmdb_id = '312359'; season = '1'; episode = '1'
        store = {}
        read = lambda location: store.get(location, ''); write = lambda location, text: store.__setitem__(location, text)
        key = ios_continue.record(Player(), read, write, choice='umbrella')
        self.assertEqual(ios_continue.load(read)['items'][key]['plot'], 'Beerus wakes.')
        ios_continue.update(read, write, 100, 1400, plot='ignored: one is kept already')
        self.assertEqual(ios_continue.load(read)['items'][key]['plot'], 'Beerus wakes.')
        library = (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
        self.assertIn("tag.setPlot(entry['plot'])", library)
    def test_the_service_runs_it_and_the_card_shows_the_property(self):
        portrait = (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn('info_fill.run(', portrait); self.assertIn('   info_started()\n', portrait)
        import pages
        card = pages.info_card()
        self.assertIn('Window(Home).Property(KodiIOS.Plot)', card); self.assertIn('No description for this video yet.', card)
        self.assertEqual(fill.PROPERTY, 'KodiIOS.Plot')


if __name__ == '__main__':
    unittest.main()
