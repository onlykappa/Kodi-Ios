"""ISSUE-298 (owner, build 442: "all the screens have really poor scrolling ... the flick just sucks and not smooth for
nearly any screen other than the home movies and tv shows"): every page's group lists take the hubs' scroll settings."""
import re,sys,types,unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import portrait


class SmoothScroll(unittest.TestCase):
 def test_adds_the_hub_scroll_once_and_keeps_an_own_one(self):
  xml=('<window><controls><control type="grouplist" id="1"><itemgap>0</itemgap><control type="button" id="2" /></control>'
       '<control type="grouplist" id="3"><scrolltime>100</scrolltime><control type="button" id="4" /></control></controls></window>')
  out=portrait.smooth_scroll(xml)
  root=ET.fromstring(out)
  g={c.get('id'):c for c in root.iter('control') if c.get('type')=='grouplist'}
  self.assertEqual(g['1'].find('scrolltime').text,'380');self.assertEqual(g['1'].find('scrolltime').get('tween'),'cubic')
  self.assertEqual(g['3'].find('scrolltime').text,'100')            # a page's own setting stays
  self.assertEqual(portrait.smooth_scroll(out),out)                   # applied twice: unchanged
  self.assertEqual(portrait.smooth_scroll(xml.encode()),out.encode())

 def test_the_hubs_setting_is_the_one_used(self):
  self.assertIn(portrait.HUB_SCROLL.replace('380','380'),(LIB/'portrait.py').read_text())
  self.assertIn('<scrolltime tween="cubic" easing="out">380</scrolltime><usecontrolcoords>true</usecontrolcoords>',(LIB/'portrait.py').read_text())

 def test_every_page_grouplist_scrolls_like_the_hubs(self):
  ns=types.SimpleNamespace(**vars(portrait))
  import library_page,copy_problems_page,library_show_page,library_select_page,library_tools_page,transfers_page,library_files_page
  pages={}
  for mod in (library_page,copy_problems_page,library_show_page,library_tools_page,transfers_page,library_files_page):
   pages.update(mod.files(ns))
  checked=0
  for name,data in pages.items():
   if not name.endswith('.xml'):continue
   text=portrait.smooth_scroll(data).decode()
   for m in re.finditer(r'<control type="grouplist"[^>]*>',text):
    nxt=text.find('<control ',m.end());self.assertIn('<scrolltime',text[m.end():nxt],name);checked+=1
  self.assertGreater(checked,8)

 def test_portrait_applies_it_to_every_portrait_page(self):
  src=(LIB/'portrait.py').read_text()
  self.assertIn("if rel.startswith(FOLDER+'/') and rel.endswith('.xml'):files[rel]=smooth_scroll(files[rel])",src)


if __name__=='__main__':unittest.main()
