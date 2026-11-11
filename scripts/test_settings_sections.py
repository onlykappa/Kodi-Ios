"""Settings redesign step 1 (owner-approved mockups, docs/design/settings-pages-mockups.html board 1-2): section pages
with category rows, the category page without its chip row, Back to the section page."""
import sys,unittest,xml.etree.ElementTree as ET,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import section_rows as sr,settings_page as sp

class Rows(unittest.TestCase):
 def test_summary_uses_only_meaningful_values(self):
  settings=[{'type':'boolean','value':True},{'type':'integer','value':750},
            {'type':'string','value':'skin.arctic.fuse.3'},                       # an add-on id says nothing
            {'type':'string','value':'Arctic Fuse 3'},
            {'type':'integer','value':1,'options':[{'value':1,'label':'Skin default'},{'value':2,'label':'Dark'}]}]
  self.assertEqual(sr.summary(settings),'Arctic Fuse 3 · Skin default')
  self.assertEqual(sr.summary([{'type':'boolean','value':True},{'type':'integer','value':5}]),'2 settings')
  self.assertEqual(sr.summary([]),'')
 def test_rows_icons_and_properties(self):
  cats=[{'id':'skin','label':'Skin'},{'id':'weird','label':'Something'}]
  rows=sr.rows(cats,lambda c:[{'type':'string','value':'Value'}] if c=='skin' else (_ for _ in ()).throw(RuntimeError('x')))
  self.assertEqual((rows[0]['name'],rows[0]['sub'],rows[0]['icon']),('Skin','Value','brush.png'))
  self.assertEqual((rows[1]['sub'],rows[1]['icon']),('',sr.DEFAULT_ICON[0]))        # a failing category still gets a row
  props=sr.properties('interface',rows)
  self.assertEqual(props['title'],'Interface');self.assertEqual(props['rows'],'2')
  self.assertEqual(props['sec.1.name'],'Skin');self.assertEqual(props['sec.3.name'],'')
 def test_every_section_has_a_window_and_the_home_rows_route_to_it(self):
  src=(LIB/'settings_page.py').read_text()
  for sec,(title,window,foot) in sr.SECTIONS.items():
   self.assertIn('RunScript(service.kodi.ios.bootstrap,section_page,%s)'%sec,src)
   self.assertNotIn("'ActivateWindow(%s)'"%window,src)                         # no row opens the chip page directly
   self.assertTrue(title and foot)

class Xml(unittest.TestCase):
 class P:
  pass
 def build(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('portrait_sec',LIB/'portrait.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  return m
 def test_section_window(self):
  p=self.build();xml=sp.section_page(p);root=ET.fromstring(xml.split('\n',2)[2])
  ids=[c.get('id') for c in root.iter('control') if c.get('id')]
  self.assertEqual(len(ids),len(set(ids)))
  for n in range(1,sr.MAX_ROWS+1):self.assertIn(str(9600+n),ids)
  self.assertIn('9001',ids)
 def test_category_window_hides_chips_only_when_opened_from_a_row(self):
  p=self.build();xml=sp.category_window(p,'<window id="5"/>')
  self.assertIn('KodiIOS.CategoryPage',xml);self.assertIn('<onunload>ClearProperty(KodiIOS.CategoryPage,Home)</onunload>',xml)
  # Back opens the section page first, then goes back (the window's own cleanup would otherwise run first)
  self.assertLess(xml.index('section_page,$INFO[Window(Home).Property(KodiIOS.CategorySection)]'),xml.index('<onclick>Action(Back)</onclick>'))
  self.assertEqual(xml.count('id="3"'),1)                                          # the chip row stays (Kodi focuses its buttons)
 def test_script_is_registered_and_sets_the_properties(self):
  self.assertIn("'section_page'",(BOOT/'default.py').read_text())
  page=(BOOT/'section_page.py').read_text()
  self.assertIn("KodiIOS.CategoryPage",page);self.assertIn("KodiIOS.CategorySection",page);self.assertIn("ActivateWindow(%s,%s)",page)

if __name__=='__main__':unittest.main()
