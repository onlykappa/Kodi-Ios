"""Owner bug: long press › Choose source / Choose player on a started title went back to Kodi's resume question and
the saved pick; choosing never offered a choice."""
import importlib.util,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
sys.path.insert(0,str(LIB))
def load(name):
 spec=importlib.util.spec_from_file_location(name,LIB/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
dialog=load('ios_watch_dialog');cont=load('ios_continue')

class Choosing(unittest.TestCase):
 def test_flag_and_tmdb_helper_choose_player(self):
  self.assertTrue(dialog.choosing(None,['plugin','1','?info=play&tmdb_id=1&ios_choose=1']))
  self.assertTrue(dialog.choosing(types.SimpleNamespace(ignore_default=True),['p','1','?info=play']))
  self.assertFalse(dialog.choosing(types.SimpleNamespace(ignore_default=False),['p','1','?info=play&ios_continue=1']))
 def test_choose_url_asks_instead_of_continuing(self):
  url=cont.choose_url({'kind':'movie','tmdb_id':'27205'})
  self.assertIn('ios_choose=1',url);self.assertNotIn('ios_continue=1',url);self.assertIn('tmdb_id=27205',url)
  ep=cont.choose_url({'kind':'episode','tmdb_id':'1','season':'2','episode':'3'})
  self.assertIn('season=2&episode=3&ios_choose=1',ep)
 def test_menu_skips_shortcuts_when_choosing(self):
  source=(LIB/'ios_watch_dialog.py').read_text()
  self.assertIn("downloaded=None if choosing(player) else downloaded_item",source)
  self.assertIn("rows.insert(0,('Downloaded copy','play',copy))",source)
 def test_choose_source_plays_this_title_not_a_simulated_tap(self):
  source=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/default.py').read_text()
  handler=source[source.index("if params.get('action')=='choose_source':"):source.index("if params.get('action')=='engine_status':")]
  self.assertNotIn("Action(Select)",handler);self.assertIn("PlayMedia(%s)'%choose_url(entry)",handler)
  self.assertIn("seekTime(start)",handler)

if __name__=='__main__':unittest.main()
