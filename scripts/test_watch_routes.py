import importlib.util,unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
path=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_routes.py'
spec=importlib.util.spec_from_file_location('watch',path);watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
class WatchTests(unittest.TestCase):
 def item(self,kind='movie',**args):return SimpleNamespace(mediatype=kind,params={'info':'play','tmdb_id':'42',**args},unique_ids={},label='Fixture',art={'poster':'https://example.invalid/poster.png'},infoproperties={'isPlayable':'true'},is_folder=False,context_menu=[('Original context action','fixture')])
 def test_movie_route_keeps_native_context_for_resolver_dialog(self):
  item=self.item();original='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_id=42';self.assertEqual(watch.wrap_item(item,original),original);self.assertFalse(item.is_folder);self.assertEqual(item.infoproperties['isPlayable'],'true')
 def test_context_metadata_and_art_preserved(self):
  item=self.item();before=(item.context_menu[:],item.label,item.art.copy());watch.wrap_item(item,'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_id=42');self.assertEqual((item.context_menu,item.label,item.art),before)
 def test_show_opens_its_seasons_directly(self):
  browse='plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_id=42';self.assertEqual(watch.wrap_item(self.item('tvshow',info='seasons'),browse),browse)
 def test_old_show_links_keep_episode_navigation(self):
  browse='plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_id=42';item=self.item('tvshow',info='seasons');url=watch.wrap_item_r1(item,browse);params={k:v[0] for k,v in parse_qs(urlsplit(url).query).items()};self.assertEqual(watch.choices(params)[0]['url'],browse)
 def test_episode_uses_exact_season_and_episode(self):
  result=watch.choices({'kind':'episode','tmdb_id':'42','season':'0','episode':'3'},True);self.assertEqual(result[0]['url'],'plugin://plugin.video.elementum/show/42/season/0/episode/3/forcelinks')
 def test_unready_elementum_never_autoplays_or_substitutes(self):
  rows=watch.choices({'kind':'movie','tmdb_id':'42'});self.assertEqual(rows[0]['action'],'engine_status');self.assertTrue(all(not r['url'].startswith('plugin://plugin.video.elementum/') for r in rows));self.assertEqual(rows[1]['url'],'plugin://plugin.googledrive/')
 def test_ready_test_route_prioritizes_elementum(self):self.assertEqual(watch.choices({'kind':'movie','tmdb_id':'42'},True)[0]['action'],'elementum')
 def test_arbitrary_folder_route_rejected(self):
  with self.assertRaises(ValueError):watch.choices({'kind':'tvshow','tmdb_id':'42','browse':'plugin://untrusted/?info=seasons'})
 def test_non_media_navigation_untouched(self):
  item=self.item('season');original='plugin://plugin.video.themoviedb.helper/?info=episodes';self.assertEqual(watch.wrap_item(item,original),original)
 def test_missing_episode_data_never_routes_to_random_episode(self):
  with self.assertRaises(ValueError):watch.choices({'kind':'episode','tmdb_id':'42'})
if __name__=='__main__':unittest.main()
