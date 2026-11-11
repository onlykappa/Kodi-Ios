import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.path.insert(0,str(BOOT/'resources/lib'))   # settings_search imports settings_find
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
search=load('settings_search',BOOT/'resources/lib/settings_search.py')
find=load('settings_find',BOOT/'resources/lib/settings_find.py')
sp=load('settings_page_q',BOOT/'resources/lib/settings_page.py')
default=load('default_q',BOOT/'default.py')
KODI=('<settings version="1"><section id="player" label="14200"><category id="videoplayer" label="14215">'
 '<group id="1"><setting id="videoplayer.autoplaynextitem" type="list[integer]" label="13433"><level>0</level></setting>'
 '<setting id="videoplayer.secret" type="boolean" label="999"><level>4</level></setting></group></category></section>'
 '<section id="unknown" label="1"><category id="x" label="2"><group id="1"><setting id="a" label="3" /></group></category></section></settings>')
NAMES={14200:'Player',14215:'Videos',13433:'Play next video automatically',999:'Internal'}

class SettingsSearch(unittest.TestCase):
 def test_page_rows_are_indexed_with_their_actions(self):
  entries=search.page_entries(sp)
  self.assertIn(('Player','Settings','RunScript(service.kodi.ios.bootstrap,section_page,player)'),entries)
  self.assertTrue(any(l=='Tabs & Rows' and w.startswith('Customisation') for l,w,_ in entries))
 def test_kodi_settings_open_their_section_at_the_category(self):
  entries=search.kodi_entries(KODI,NAMES.get)
  self.assertIn(('Play next video automatically','Player › Videos','ActivateWindow(playersettings,videoplayer)'),entries)
  self.assertFalse(any(l=='Internal' for l,_,_ in entries))   # level 4 is hidden in Kodi too
  self.assertFalse(any(a.endswith(',x)') for _,_,a in entries))
  self.assertEqual(search.kodi_entries('<broken',NAMES.get),[])
 def test_matching_is_by_words_label_first_and_unique(self):
  entries=search.page_entries(sp)+search.kodi_entries(KODI,NAMES.get)
  found=find.search(entries,'  PLAYER ')
  self.assertEqual(found[0][0],'Player');self.assertIn('Play next video automatically',[f[0] for f in found])   # section match
  self.assertEqual([f[0] for f in find.search(entries,'next video')],['Play next video automatically'])
  self.assertEqual(find.search(entries,''),[]);self.assertEqual(find.search(entries,'zzzz'),[])
  self.assertEqual(len(find.search(entries+entries,'player')),len(find.search(entries,'player')))
 def test_script_is_a_bootstrap_page(self):
  self.assertIn('settings_search',default.PAGES);self.assertTrue((BOOT/'settings_search.py').is_file())
  self.assertEqual(sp.SEARCH,'RunScript(service.kodi.ios.bootstrap,settings_search)')
 def test_library_scan_is_discoverable_and_runs_the_scan_dispatcher(self):
  found=find.search(search.page_entries(sp),'scan iPhone')
  self.assertEqual(found,[('Scan iPhone files','Library › iPhone Files','RunScript(service.kodi.ios.bootstrap,library_scan)')])
  path,argv=default.target(['service.kodi.ios.bootstrap','library_scan'])
  self.assertEqual(Path(path),BOOT/'library_scan.py');self.assertEqual(argv,[path])
  self.assertIn(('Refresh Library','Library › Library',sp.LIBRARY_REFRESH),find.search(search.page_entries(sp),'refresh library'))


class NeverAnInvisibleDialog(unittest.TestCase):
 """Owner (build 168 log): "Control 9160 in window 13000 has been asked to focus, but it can't" - the search page was
 hidden until something was typed, yet sat over Settings: taps went nowhere and Back was hidden. The page is always
 shown, lists Settings' own rows before typing, and opens with the field focused."""
 def test_page_always_shown_and_lists_settings_before_typing(self):
  xml=sp.search_window(types_portrait())
  self.assertNotIn('<visible>',xml.split('<controls>',1)[1].split('<control type="group">',1)[0])
  ctl=(BOOT/'settings_search.py').read_text()
  self.assertIn("refresh('')",ctl);self.assertIn("[e for e in entries if e[1]=='Settings']",ctl)
  self.assertIn('self.setFocusId(FIELD)',ctl);self.assertIn('settings_page.SEARCH_LIST',ctl)

def types_portrait():
 import types
 return types.SimpleNamespace(**load('portrait_for_search',BOOT/'resources/lib/portrait.py').__dict__)

if __name__=='__main__':unittest.main()
