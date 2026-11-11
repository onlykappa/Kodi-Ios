import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
path=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py'
spec=importlib.util.spec_from_file_location('watch_dialog',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DialogTests(unittest.TestCase):
 def setUp(self):
  self.copy_patch=mock.patch.object(module,'downloaded_item',return_value=None);self.copy_check=self.copy_patch.start();self.addCleanup(self.copy_patch.stop)
  self.dialog=mock.Mock();self.dialog.select.return_value=-1
  self.logged=[]
  self.xbmc=SimpleNamespace(getCondVisibility=mock.Mock(return_value=False),executebuiltin=mock.Mock(),log=lambda text,level=0:self.logged.append(text),LOGINFO=1)
  self.settings=mock.Mock();self.settings.getSettingBool.return_value=False
  self.home=mock.Mock()
  self.mods={'xbmc':self.xbmc,'xbmcgui':SimpleNamespace(Dialog=lambda:self.dialog,ListItem=mock.Mock(),Window=lambda id:self.home),'xbmcaddon':SimpleNamespace(Addon=lambda id:self.settings),'xbmcvfs':SimpleNamespace(exists=lambda path:True)}
  self.patch=mock.patch.dict(sys.modules,self.mods);self.patch.start()
  self.engine=SimpleNamespace(file='ios.elementum.json',is_local=False,kodi_file=None)
  self.player=SimpleNamespace(allow_playlist=True,details=SimpleNamespace(art={'poster':'fixture'},infolabels={'title':'Fixture'}),player_items=SimpleNamespace(items_play=[self.engine]))
 def tearDown(self):self.patch.stop()
 def test_cancel_never_selects_a_backend(self):self.assertIsNone(module.choose_player(self.player));self.xbmc.executebuiltin.assert_not_called();self.assertFalse(self.player.allow_playlist)
 def test_the_log_says_what_was_offered_and_picked(self):
  # Owner logs: "lib.player - Failure!" after a tap, and nothing said why.
  module.choose_player(self.player)
  self.assertTrue(any('offered' in t and 'picked -1' in t for t in self.logged));self.assertTrue(any('nothing picked' in t for t in self.logged))
 def test_unready_selection_shows_status_without_playback(self):
  self.dialog.select.return_value=0;self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once();self.xbmc.executebuiltin.assert_not_called()
 def test_ready_elementum_is_first_and_explicit(self):
  self.xbmc.getCondVisibility.return_value=True;self.settings.getSettingBool.return_value=True;self.dialog.select.return_value=0
  self.assertIs(module.choose_player(self.player),self.engine)
 def test_deck_style_question_with_umbrella_slot(self):
  module.choose_player(self.player);title=self.dialog.select.call_args[0][0];self.assertTrue(title.startswith('How would you like to watch'))
  labels=[c.kwargs.get('label') for c in self.mods['xbmcgui'].ListItem.call_args_list];self.assertEqual(labels[:2],['Download — not available on iPhone yet','Stream — coming soon'])
 def test_umbrella_offered_once_installed(self):
  umbrella=SimpleNamespace(file='ios.umbrella.json',is_local=False,kodi_file=None);self.player.player_items.items_play=[self.engine,umbrella]
  self.xbmc.getCondVisibility.side_effect=lambda cond:'umbrella' in cond;self.dialog.select.return_value=1
  self.assertIs(module.choose_player(self.player),umbrella)
 def test_umbrella_placeholder_shows_status_only(self):
  self.dialog.select.return_value=1;self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once();self.xbmc.executebuiltin.assert_not_called()
 def test_no_google_drive_rows(self):
  module.choose_player(self.player);labels=[c.kwargs.get('label') for c in self.mods['xbmcgui'].ListItem.call_args_list]
  self.assertEqual(labels,['Download — not available on iPhone yet','Stream — coming soon'])
 def test_other_backend_not_substituted(self):
  other=SimpleNamespace(file='some-other-player.json',is_local=False,kodi_file=None);self.player.player_items.items_play=[other];self.dialog.select.return_value=0
  self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once()
 def test_artwork_is_passed_to_native_kodi_listitems(self):
  module.choose_player(self.player);self.mods['xbmcgui'].ListItem.return_value.setArt.assert_called_with({'poster':'fixture'})
 def continue_setup(self,saved,argv):
  umbrella=SimpleNamespace(file='ios.umbrella.json',is_local=False,kodi_file=None);self.player.player_items.items_play=[self.engine,umbrella]
  self.player.tmdb_type='movie';self.player.tmdb_id='1'
  self.xbmc.getCondVisibility.return_value=True;self.settings.getSettingBool.return_value=True
  recorded=[]
  fake=SimpleNamespace(player_key=lambda player:'movie:1::',saved_choice=lambda read,key:saved,record=lambda *a,**k:recorded.append(k.get('choice')))
  self.patch_extra=mock.patch.dict(sys.modules,{'ios_continue':fake});self.patch_extra.start();self.addCleanup(self.patch_extra.stop)
  self.argv=mock.patch.object(sys,'argv',argv);self.argv.start();self.addCleanup(self.argv.stop)
  return umbrella,recorded
 def test_continue_watching_reuses_player_and_version(self):
  umbrella,recorded=self.continue_setup({'player':'umbrella','version':{'name':'Film.1080p','quality':'1080p'}},
                                        ['plugin://x','1','?info=play&tmdb_type=movie&tmdb_id=1&ios_continue=1'])
  self.assertIs(module.choose_player(self.player),umbrella);self.dialog.select.assert_not_called();self.assertEqual(recorded,['umbrella'])
  name,value=self.home.setProperty.call_args[0];self.assertEqual(name,'KodiIOS.Resume.Source')
  import json;self.assertEqual(json.loads(value)['name'],'Film.1080p')
 def test_normal_play_still_asks(self):
  umbrella,recorded=self.continue_setup({'player':'umbrella','version':{'name':'Film.1080p'}},['plugin://x','1','?info=play&tmdb_type=movie&tmdb_id=1'])
  self.dialog.select.return_value=0
  self.assertIs(module.choose_player(self.player),self.engine);self.dialog.select.assert_called_once();self.assertEqual(recorded,['elementum'])
  self.assertNotIn('KodiIOS.Resume.Source',[c[0][0] for c in self.home.setProperty.call_args_list]);self.home.clearProperty.assert_called_with('KodiIOS.Resume.Source')
 def test_continue_without_a_saved_pick_asks(self):
  umbrella,recorded=self.continue_setup({},['plugin://x','1','?info=play&tmdb_type=movie&tmdb_id=1&ios_continue=1'])
  self.dialog.select.return_value=1
  self.assertIs(module.choose_player(self.player),umbrella);self.dialog.select.assert_called_once();self.home.setProperty.assert_not_called()
if __name__=='__main__':unittest.main()
