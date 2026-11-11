"""Pickers (owner-approved mockup boards 13-14): Download / Stream tiles and the quality rows with a second line."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))

class Pickers(unittest.TestCase):
 def test_select_dialog_has_a_second_line_and_tiles(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('portrait_pick',LIB/'portrait.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  xml=m.select_dialog('<window id="2000"/>')
  self.assertIn('$INFO[ListItem.Label2]',xml);self.assertIn('ListItem.Property(tint)',xml);self.assertIn('ListItem.Property(glyph)',xml)
  self.assertIn('<visible>![',xml)                                            # plain centred rows stay for choices without either
 def test_watch_dialog_rows_are_download_and_stream(self):
  src=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py').read_text()
  self.assertIn("rows.append(('Download','play',engine))",src);self.assertIn("rows.append(('Stream','play',umbrella))",src)
  self.assertNotIn("rows.append(('Elementum'",src);self.assertNotIn("rows.append(('Umbrella'",src)
  self.assertIn("ROW_TILE",src)
 def test_quality_rows_name_the_count_and_size(self):
  sys.path.insert(0,str(ROOT/'migration/deck-picker'))
  import deck_picker as dp
  items=[{'quality':'1080p','size':2.4,'seeds':5,'providers':[]}]
  src=(ROOT/'migration/deck-picker/deck_picker.py').read_text()
  self.assertIn("\\x1f%d version%s \\u00b7 from %s",src);self.assertIn("name, _, detail = text.partition(u'\\x1f')",src)

if __name__=='__main__':unittest.main()
