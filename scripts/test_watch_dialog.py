import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
path=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py'
spec=importlib.util.spec_from_file_location('watch_dialog',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DialogTests(unittest.TestCase):
 def setUp(self):
  self.dialog=mock.Mock();self.dialog.select.return_value=-1
  self.xbmc=SimpleNamespace(getCondVisibility=mock.Mock(return_value=False),executebuiltin=mock.Mock())
  self.settings=mock.Mock();self.settings.getSettingBool.return_value=False
  self.mods={'xbmc':self.xbmc,'xbmcgui':SimpleNamespace(Dialog=lambda:self.dialog,ListItem=mock.Mock()),'xbmcaddon':SimpleNamespace(Addon=lambda id:self.settings),'xbmcvfs':SimpleNamespace(exists=lambda path:True)}
  self.patch=mock.patch.dict(sys.modules,self.mods);self.patch.start()
  self.engine=SimpleNamespace(file='ios.elementum.json',is_local=False,kodi_file=None)
  self.player=SimpleNamespace(allow_playlist=True,details=SimpleNamespace(art={'poster':'fixture'},infolabels={'title':'Fixture'}),player_items=SimpleNamespace(items_play=[self.engine]))
 def tearDown(self):self.patch.stop()
 def test_cancel_never_selects_a_backend(self):self.assertIsNone(module.choose_player(self.player));self.xbmc.executebuiltin.assert_not_called();self.assertFalse(self.player.allow_playlist)
 def test_unready_selection_shows_status_without_playback(self):
  self.dialog.select.return_value=0;self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once();self.xbmc.executebuiltin.assert_not_called()
 def test_ready_elementum_is_first_and_explicit(self):
  self.xbmc.getCondVisibility.return_value=True;self.settings.getSettingBool.return_value=True;self.dialog.select.return_value=0
  self.assertIs(module.choose_player(self.player),self.engine)
 def test_deck_style_question_with_umbrella_slot(self):
  module.choose_player(self.player);title=self.dialog.select.call_args[0][0];self.assertTrue(title.startswith('How would you like to watch'))
  labels=[c.kwargs.get('label') for c in self.mods['xbmcgui'].ListItem.call_args_list];self.assertEqual(labels[:2],['Elementum — not available on iPhone yet','Umbrella — coming soon'])
 def test_umbrella_offered_once_installed(self):
  umbrella=SimpleNamespace(file='ios.umbrella.json',is_local=False,kodi_file=None);self.player.player_items.items_play=[self.engine,umbrella]
  self.xbmc.getCondVisibility.side_effect=lambda cond:'umbrella' in cond;self.dialog.select.return_value=1
  self.assertIs(module.choose_player(self.player),umbrella)
 def test_umbrella_placeholder_shows_status_only(self):
  self.dialog.select.return_value=1;self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once();self.xbmc.executebuiltin.assert_not_called()
 def test_drive_search_uses_the_title(self):
  self.dialog.select.return_value=2;self.assertIsNone(module.choose_player(self.player))
  self.xbmc.executebuiltin.assert_called_once_with('ActivateWindow(Videos,plugin://plugin.googledrive/?action=_search&content_type=video&query=Fixture,return)')
 def test_private_drive_is_separate_browse_not_title_match(self):
  self.dialog.select.return_value=3;self.assertIsNone(module.choose_player(self.player));self.xbmc.executebuiltin.assert_called_once_with('ActivateWindow(Videos,plugin://plugin.googledrive/,return)')
 def test_other_backend_not_substituted(self):
  other=SimpleNamespace(file='some-other-player.json',is_local=False,kodi_file=None);self.player.player_items.items_play=[other];self.dialog.select.return_value=0
  self.assertIsNone(module.choose_player(self.player));self.dialog.ok.assert_called_once()
 def test_artwork_is_passed_to_native_kodi_listitems(self):
  module.choose_player(self.player);self.mods['xbmcgui'].ListItem.return_value.setArt.assert_called_with({'poster':'fixture'})
if __name__=='__main__':unittest.main()
