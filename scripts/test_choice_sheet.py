"""Choice sheet (mockup round 3, boards 13-15): one bottom sheet for the source, quality and season pickers."""
import importlib.util,sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import choice_sheet as c,season_sources as ss

def portrait():
 spec=importlib.util.spec_from_file_location('portrait_skin',LIB/'portrait.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Sheet(unittest.TestCase):
 def test_window_is_well_formed_bottom_aligned_and_registered(self):
  x=c.window(portrait());root=ET.fromstring(x.split('\n',2)[2])
  ids=[e.get('id') for e in root.iter('control') if e.get('id')];self.assertEqual(len(ids),len(set(ids)))
  for n in range(c.MAX_ROWS):self.assertIn(str(c.ROW0+n),ids)
  for i in (c.LINK,c.CANCEL,c.DIM,9800):self.assertIn(str(i),ids)
  stack=[e for e in root.iter('control') if e.get('id')=='9800'][0];self.assertEqual(stack.find('align').text,'right')   # grows upward
  src=(LIB/'settings_page.py').read_text();self.assertIn("choice_sheet.WINDOW:choice_sheet.window(p)",src)
 def test_properties_and_answers(self):
  props=c.properties({'heading':'H','rows':[{'label':'A','cover':75},{'label':'B','tag':'BEST','tag_kind':'best'}],'link':'Show All'})
  self.assertEqual((props['rows'],props['row.1.cover'],props['row.2.cover'],props['row.2.tag_kind'],props['row.3.label']),('2','8','','best',''))
  self.assertEqual([c.result(c.ROW0,2,True),c.result(c.ROW0+1,2,True),c.result(c.LINK,2,True),c.result(c.LINK,2,False),c.result(c.CANCEL,2,True)],[0,1,2,-1,-1])
 def test_season_spec_tags_and_bars(self):
  sources={n:['1080p']+(['4k'] if n<=6 else []) for n in range(1,9)}
  spec=ss.sheet_spec('Lanterns',1,[('4k',6),('1080p',8)],sources,list(range(1,9)))
  self.assertEqual(spec['heading'],'Lanterns · Season 1');self.assertEqual(spec['foot'],ss.FOOT)
  self.assertEqual([(r['label'],r['tag'],r['tag_kind'],round(r['cover'])) for r in spec['rows']],[('4K Ultra HD','6 OF 8','warn',75),('1080p Full HD','ALL 8','best',100)])
  self.assertEqual(spec['rows'][0]['detail'],'Episodes 1–6 now · 7–8 wait')
 def test_pickers_use_it(self):
  self.assertIn('sheet.choose(quality_sheet(labels, title, total)',(ROOT/'migration/deck-picker/deck_picker.py').read_text())
  self.assertIn('selected=sheet_choice(rows,kind_of,art,info,name)',(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py').read_text())
  self.assertIn('choice_sheet.choose({',(ROOT/'migration/bundled-bootstrap/download.py').read_text())
  sys.path.insert(0,str(ROOT/'migration/deck-picker'))
  import deck_picker as dp
  q=dp.quality_sheet(['[B]4K Ultra HD[/B]\x1f5 versions · from 18 GB','[B]720p HD[/B]\x1f3 versions · from 1.1 GB','Show all 25 links'],'The Maze Runner',25)
  self.assertEqual((q['heading'],q['sub'],q['link'],q['rows'][0]['tag'],q['rows'][1]['tag']),('The Maze Runner','Pick a quality · 25 versions found','Show All 25 Links','BEST',''))

if __name__=='__main__':unittest.main()
