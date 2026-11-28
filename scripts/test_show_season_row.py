"""A downloaded (library) show's season page keeps the season row (owner, build 615: "when I scroll up I can't select a different
season without backing out"). The row was only drawn for TMDb Helper shows (their folder path); a library show's episodes now carry
KodiIOS.SeasonsPath and the page draws a second season list (id 47) from it. Checked in the desktop Kodi rig with a fake show."""
import re,sys,unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import portrait as p

class SeasonRow(unittest.TestCase):
 def test_library_season_list_is_on_the_show_page_and_reads_the_episodes_season_path(self):
  xml=p.video_nav(False) if p.video_nav.__code__.co_argcount else p.video_nav()
  self.assertIn('<control type="list" id="47">',xml)
  self.assertIn('<content>$INFO[Container(52).ListItem.Property(KodiIOS.SeasonsPath)]</content>',xml)
  self.assertIn('!String.IsEmpty(Container(52).ListItem.Property(KodiIOS.SeasonsPath))',xml)
  ids=re.findall(r'<control type="[a-z]+" id="(\d+)"',xml)
  self.assertEqual(len(ids),len(set(ids)))   # no id used twice
  self.assertIn('id="48"',xml)                # the TMDb Helper show's row is untouched
 def test_the_library_plugin_puts_the_season_list_on_every_episode(self):
  src=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
  self.assertIn("'KodiIOS.SeasonsPath':seasons",src)
  self.assertIn("seasons=page_url({k:v for k,v in params.items() if k in ('type','folder','show','year','local','loose','merge')})",src)   # the show's route, without the season

 def test_the_pinned_season_row_waits_until_the_pages_own_row_has_scrolled_away(self):
  # ISSUE-493: HasPrevious alone is true from the first pixel of scroll, so two season rows showed at once
  src=(ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
  self.assertIn("pinned_visible='Container.Content(seasons) + Container(9900).HasPrevious + !Container(9900).HasNext'",src)

if __name__=='__main__':unittest.main()
