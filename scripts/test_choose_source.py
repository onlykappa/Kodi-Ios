"""Long press > Choose source on an episode or a movie of a TMDb Helper page (owner 2026-11-25: it worked on Home, not in the TV show menu)."""
import importlib.util, sys, unittest, urllib.parse
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
spec = importlib.util.spec_from_file_location('choose_source', ROOT / 'migration/bundled-bootstrap/choose_source.py')
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)

EP = 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=124364&season=4&episode=7'
MOVIE = 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=603'


class Choose(unittest.TestCase):
    def test_an_episode_and_a_movie_give_their_ids_from_the_play_path(self):
        self.assertEqual(cs.target('episode', EP, {}), {'tmdb_type': 'tv', 'tmdb_id': '124364', 'season': '4', 'episode': '7'})
        self.assertEqual(cs.target('movie', MOVIE, {}), {'tmdb_type': 'movie', 'tmdb_id': '603'})
        self.assertEqual(cs.target('episode', '', {'tvshow.tmdb_id': '124364', 'season': '4', 'episode': '7'}), {'tmdb_type': 'tv', 'tmdb_id': '124364', 'season': '4', 'episode': '7'})
    def test_what_has_no_ids_or_is_not_an_episode_or_movie_is_refused(self):
        self.assertIsNone(cs.target('episode', 'plugin://x/', {})); self.assertIsNone(cs.target('episode', EP.replace('&episode=7', ''), {}))
        self.assertIsNone(cs.target('season', EP, {})); self.assertIsNone(cs.target('tvshow', EP, {}))
    def test_the_action_runs_the_plugins_choose_source_with_the_ids_only(self):
        text = cs.action(cs.target('episode', EP, {}))
        self.assertTrue(text.startswith('RunPlugin(plugin://plugin.video.kodi.ios.watch/?') and text.endswith(')'))
        query = dict(urllib.parse.parse_qsl(text[text.index('?') + 1:-1]))
        self.assertEqual(query, {'tmdb_type': 'tv', 'tmdb_id': '124364', 'season': '4', 'episode': '7', 'action': 'choose_source'})
    def test_the_menu_entry_and_the_plugin_handle_it(self):
        addon = (ROOT / 'migration/bundled-bootstrap/addon.xml').read_text()
        self.assertIn('<item library="choose_source.py">', addon); self.assertIn('<label>Choose source</label>', addon)
        entry = addon[addon.index('choose_source.py'):]
        entry = entry[:entry.index('</item>')]
        self.assertIn('plugin://plugin.video.themoviedb.helper', entry)             # TMDb Helper pages only: Home's cards and the library pages have their own menus
        self.assertIn('!String.Contains(ListItem.FolderPath,plugin.video.kodi.ios.watch/?action=library)', entry)
        plugin = (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/default.py').read_text()
        self.assertIn("params.get('tmdb_id','').isdigit() and params.get('tmdb_type') in ('movie','tv')", plugin)
        self.assertIn('choose_url(entry)', plugin)
    def test_the_synthetic_entry_plays_with_the_ask_flag(self):
        sys.path.insert(0, str(ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
        import ios_continue as c
        ids = {'kind': 'episode', 'tmdb_id': '124364', 'season': '4', 'episode': '7'}
        url = c.choose_url(dict(ids, title='', art={}, position=0))
        self.assertIn('ios_choose=1', url); self.assertNotIn('ios_continue=1', url); self.assertIn('season=4&episode=7', url)
        self.assertEqual(c.key(ids), 'episode:124364:4:7')


if __name__ == '__main__':
    unittest.main()
