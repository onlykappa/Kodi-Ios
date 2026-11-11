"""Round 5 header (owner picked option A; build 173: Back stays the bold chevron with no circle): a gear in place of the
profile picture (opens Settings), a thin busy arc on the bell, and refresh on Home, Movies and TV: their TMDb Helper rows
and hero move to the next page of their lists, the copies of the old page are turned off, and the service copies the
new page under the same keys."""
import importlib.util,json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
portrait=load('portrait_header',LIB/'portrait.py')
cache=load('ios_cache_header',WATCH/'resources/lib/ios_cache.py')
refresh_rows=load('refresh_rows_t',BOOT/'refresh_rows.py')
TRENDING='plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie'
POPULAR='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv'

def nodes(tmp):
 n=Path(tmp)/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3';n.mkdir(parents=True)
 for name,paths in (('homewidgets',[TRENDING,'videodb://movies/titles/',POPULAR]),('1102widgets',[POPULAR]),('1101widgets',['videodb://tvshows/'])):
  (n/('skinvariables-shortcut-%s.json'%name)).write_text(json.dumps([{'label':'x%d'%i,'path':p} for i,p in enumerate(paths)]))

def hubs_xml():
 widgets=[{'label':'Trending','path':TRENDING},{'label':'Mine','path':'videodb://movies/titles/'}]
 hubs=[(tab,(tab.title(),widgets,tab,spot,'all')) for tab,spot in (('home','home'),('movies','1102'),('tv','1101'))]
 return portrait.hubs_window('<window id="0"/>',hubs,{})

class Pages(unittest.TestCase):
 def test_page_numbers(self):
  self.assertEqual([portrait.next_page(x) for x in ('','1','2',str(portrait.PAGES),'junk')],[2,2,3,1,2])
  self.assertEqual(portrait.paged(TRENDING,3),TRENDING+'&page=3');self.assertEqual(portrait.paged(TRENDING,1),TRENDING)
  self.assertEqual(portrait.paged(TRENDING+'&page=4',''),TRENDING);self.assertEqual(portrait.paged('videodb://movies/',3),'videodb://movies/')
 def test_copies_keep_one_key_per_list(self):
  self.assertEqual(cache.row_key(TRENDING+'&page=3'),cache.row_key(TRENDING));self.assertEqual(cache.row_key(TRENDING),portrait.cache_key(TRENDING))
  self.assertEqual(cache.unpaged(TRENDING+'&page=12'),TRENDING);self.assertEqual(cache.PAGED.pattern,portrait.PAGED.pattern)
 def test_hero_flag_holds_the_path_the_skin_compares(self):
  ran=[];info={}
  flags=cache.Flags(lambda c:False,lambda c:info.get(c,''),ran.append)
  self.assertTrue(flags.set('hero.home',TRENDING+'&page=2'));self.assertEqual(ran,['Skin.SetString(PortraitCache.hero.home,"%s")'%TRENDING])
  info['Skin.String(PortraitCache.hero.home)']=TRENDING
  self.assertTrue(flags.on('hero.home',TRENDING+'&page=2'))
 def test_a_new_page_is_copied_again(self):
  class Store:
   def __init__(s):s.entries={}
   def stuck(s,now):return {}
   def load(s,key,now=None):return s.entries.get(key)
   def write(s,key,url,items,now):s.entries[key]={'url':url,'time':now,'items':items};return True
  store=Store();flags=cache.Flags(lambda c:True,lambda c:'',lambda a:None)
  answer={'files':[{'file':'x','label':'A','type':'movie'}]}
  key=cache.row_key(TRENDING)
  cache.refresh([(key,TRENDING)],store,flags,lambda url:answer,lambda s:False,lambda:100)
  done,_=cache.refresh([(key,TRENDING+'&page=2')],store,flags,lambda url:answer,lambda s:False,lambda:101)
  self.assertEqual(done,[key]);self.assertEqual(store.entries[key]['url'],TRENDING+'&page=2')
 def test_service_lists_each_tab_at_its_page(self):
  with tempfile.TemporaryDirectory() as tmp:
   nodes(tmp)
   spots,rows=portrait.cache_lists(tmp,lambda s:TRENDING if s=='home' else 'videodb://x',lambda tab:{'home':'3'}.get(tab,''))
   self.assertEqual(spots['home'],TRENDING+'&page=3');self.assertEqual(spots['1102'],'videodb://x')
   self.assertEqual(rows,[TRENDING+'&page=3','videodb://movies/titles/',POPULAR+'&page=3',POPULAR,'videodb://tvshows/'])
   self.assertIn("lambda tab:xbmc.getInfoLabel(page_of(tab))",(LIB/'portrait.py').read_text())
 def test_tab_lists(self):
  with tempfile.TemporaryDirectory() as tmp:
   nodes(tmp)
   keys,ids=portrait.tab_lists(tmp,'home')
   self.assertEqual(keys,['hero.home',cache.row_key(TRENDING),cache.row_key(POPULAR)]);self.assertEqual(ids,[4000,5002,5004])
   keys,ids=portrait.tab_lists(tmp,'movies');self.assertEqual(ids,[14000,15002])

class Refresh(unittest.TestCase):
 def press(self,page='',prop=''):
  with tempfile.TemporaryDirectory() as tmp:
   nodes(tmp)
   props={'Portrait.Refreshing':prop};ran=[];seen=[];clock=iter(range(1000))
   loading=iter([True,True,False])
   def wait(s):seen.append(props['Portrait.Refreshing']);return False
   result=refresh_rows.refresh('home',tmp,lambda label:page if label=='Skin.String(Portrait.Page.home)' else '',lambda c:next(loading),
                               ran.append,props.get,props.__setitem__,wait,portrait,lambda:next(clock))
   return result,ran,seen,props
 def test_next_page_live_at_once_then_done(self):
  page,ran,seen,props=self.press('2')
  self.assertEqual(page,3);self.assertIn('Skin.SetString(Portrait.Page.home,3)',ran)
  self.assertIn('Skin.Reset(PortraitCache.hero.home)',ran);self.assertIn('Skin.Reset(PortraitCache.%s)'%cache.row_key(TRENDING),ran)
  self.assertLess(ran.index('Skin.Reset(PortraitCache.hero.home)'),ran.index('Skin.SetString(Portrait.Page.home,3)'))
  self.assertEqual(seen[0],'home');self.assertEqual(seen[-1],'done.home');self.assertEqual(props['Portrait.Refreshing'],'')
 def test_back_to_the_first_page(self):
  page,ran,_,_=self.press(str(portrait.PAGES));self.assertEqual(page,1);self.assertIn('Skin.Reset(Portrait.Page.home)',ran)
 def test_a_second_press_while_loading_does_nothing(self):
  page,ran,_,props=self.press('2',prop='home');self.assertIsNone(page);self.assertEqual(ran,[]);self.assertEqual(props['Portrait.Refreshing'],'home')
 def test_tab_argument_and_entry(self):
  self.assertEqual([refresh_rows.tab_from(a) for a in (['tab=movies'],['tv'],[],['tab=x'])],['movies','tv','home','home'])
  self.assertIn("'refresh_rows'",(BOOT/'default.py').read_text())
  self.assertEqual(portrait.refresh_rows_action('tv'),'RunScript(service.kodi.ios.bootstrap,refresh_rows,tab=tv)')

class Header(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.xml=hubs_xml()
 def test_gear_bell_and_refresh_on_every_hub(self):
  ids={c.get('id') for c in ET.fromstring(self.xml.split('\n',2)[2]).iter('control')}
  for off in (0,10000,20000):
   for n in (9206,9207,9208):self.assertIn(str(n+off),ids)
  for tab in ('home','movies','tv'):self.assertIn('refresh_rows,tab=%s'%tab,self.xml)
  self.assertIn('hdr_gear.png',self.xml);self.assertIn('ActivateWindow(settings)',self.xml);self.assertNotIn('circle-user.png',self.xml)
  self.assertNotIn('ring_arc.png',self.xml);self.assertIn('Notices.Pct',self.xml);self.assertIn('New picks on Movies',self.xml)
 def test_glyph_sizes_follow_the_policy(self):
  self.assertEqual(portrait.HDR_GLYPH,46);self.assertEqual(portrait.NAV_GLYPH,104)
  self.assertNotIn('ActivateWindow(1170)',portrait.page_header('Library'))
 def test_back_has_no_circle(self):
  back=portrait.nav_button(9001,54,36,'chevron-left.png','Back')
  self.assertNotIn('glass_',back);self.assertNotIn('dot.png',back)
 def test_textures_once_and_identical(self):
  first=portrait.header_glyphs();self.assertIs(first,portrait.header_glyphs())
  full=portrait.shape(96,lambda u,v:portrait.gear_inside(u,v,list(portrait.GEAR)))
  self.assertEqual(full,first['hdr_gear.png'])   # the quick in / out test changes no pixel

class SettingsKeepsTheMoreMenu(unittest.TestCase):
 def test_rows(self):
  sp=load('settings_page_header',LIB/'settings_page.py')
  rows={r[1]:r[2] for g in sp.ROOT for r in g}
  self.assertEqual(rows['Favourites'],'RunScript(service.kodi.ios.bootstrap,favourites_page)');self.assertIn('check_updates',rows['Check for updates'])
  self.assertIn('navigation_menu',rows['iPhone navigation / recovery']);self.assertIn('plugin.googledrive',rows['Google Drive'])

if __name__=='__main__':unittest.main()
