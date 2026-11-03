"""Listing cache (build-137): hub rows and heroes from their last TMDb Helper result, without ever blanking Home.

The watch plugin's cached route only reads a copy (no JSON-RPC, no TMDb Helper); the skin picks cached or live per row
from saved skin flags; the bootstrap service makes copies one at a time and sets a flag only after the copy reads back.
"""
import importlib.util,json,os,sys,tempfile,time,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch'
spec=importlib.util.spec_from_file_location('ios_cache',WATCH/'resources/lib/ios_cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import portrait

TRENDING='plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie'
POPULAR='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv'
MOVIE='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=1423191'
SHOW='plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=1424'
# Shape of Kodi 21's Files.GetDirectory answer for a TMDb Helper list (desktop rig, 2026-11-03), trimmed.
ANSWER={'files':[
 {'file':MOVIE,'filetype':'file','label':'Resident Evil','title':'Resident Evil','type':'movie','year':2026,'genre':['Horror'],
  'rating':7.34,'votes':0,'plot':'Night.','mpaa':'R','runtime':5700,'premiered':'2026-09-16','playcount':0,'season':-1,'episode':-1,
  'showtitle':'','director':[],'resume':{'position':0.0,'total':0.0},
  'art':{'poster':'p.jpg','fanart':'f.jpg','fanart3':'f3.jpg','clearlogo':'l.png','landscape':'w.jpg'},
  'uniqueid':{'tmdb':'1423191','imdb':'tt1','unknown':'tt1'},
  'customproperties':{'isplayable':'true','tmdb_id':'1423191','item.info':'play','dbtype':'movie',
   'contextmenulabel(0)':'$ADDON[plugin.video.themoviedb.helper 32322]','contextmenuaction(0)':'RunPlugin(%s&ignore_default=true)'%MOVIE,
   'contextmenulabel(1)':'$ADDON[plugin.video.themoviedb.helper 32235]','contextmenuaction(1)':'RunScript(plugin.video.themoviedb.helper,related_lists,tmdb_type=movie,tmdb_id=1423191)'}},
 {'file':SHOW,'filetype':'directory','label':'Columbo','type':'tvshow','uniqueid':{'tmdb':1424},'customproperties':{'tmdb_type':'tv','item.info':'seasons'}},
 {'file':'','label':'broken'}]}

class FakeTag:
 def __init__(self):self.values={}
 def __getattr__(self,name):
  if not name.startswith('set'):raise AttributeError(name)
  return lambda *a:self.values.__setitem__(name,a)
class FakeItem:
 def __init__(self,label='',path='',offscreen=False):self.label,self.path,self.tag=label,path,FakeTag();self.props={};self.menu=[];self.art={}
 def setArt(self,a):self.art=a
 def getVideoInfoTag(self):return self.tag
 def setProperties(self,p):self.props.update(p)
 def addContextMenuItems(self,m):self.menu+=m
class FakeKodi:
 """xbmc with no executeJSONRPC: the cached route must never call it."""
 def __init__(self,labels=None):self.builtins=[];self.labels=labels or {};self.logs=[];self.LOGWARNING=2
 def executebuiltin(self,b):self.builtins.append(b)
 def getInfoLabel(self,l):return self.labels.get(l,'')
 def log(self,text,level=0):self.logs.append(text)

class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=cache.Store(os.path.join(self.tmp.name,'listings'))
  self.skin={};self.runs=[]
  self.flags=cache.Flags(lambda c:self.skin.get(c[len('Skin.HasSetting('):-1])=='true',
                         lambda l:self.skin.get(l[len('Skin.String('):-1],''),self.builtin)
 def tearDown(self):self.tmp.cleanup()
 def builtin(self,b):
  self.runs.append(b);name=b[b.index('(')+1:-1]
  if b.startswith('Skin.SetBool('):self.skin[name]='true'
  elif b.startswith('Skin.SetString('):k,v=name.split(',',1);self.skin[k]=v.strip('"')
  elif b.startswith('Skin.Reset('):self.skin.pop(name,None)
 def serve(self,key,labels=None,now=10**6):
  added=[];ends=[];kodi=FakeKodi(labels)
  plugin=SimpleNamespace(addDirectoryItems=lambda h,items,n:added.extend(items),setContent=lambda h,c:None,
                         endOfDirectory=lambda h,succeeded=True,cacheToDisc=True:ends.append(succeeded))
  cache.serve(1,key,kodi,SimpleNamespace(ListItem=FakeItem),plugin,self.store.read,lambda:now)
  self.assertEqual(ends,[True])  # the directory always ends at once, also with no copy
  return added,kodi

class CopyTests(Base):
 def test_items_keep_path_kind_properties_and_long_press_entries(self):
  items=cache.from_rpc(ANSWER)
  self.assertEqual([(i['path'],i['folder']) for i in items],[(MOVIE,False),(SHOW,True)])
  movie=items[0]
  self.assertEqual(movie['props']['isplayable'],'true');self.assertEqual(movie['props']['tmdb_id'],'1423191')
  self.assertFalse([k for k in movie['props'] if k.startswith('contextmenu')])
  self.assertEqual([m[1] for m in movie['menu']],[ANSWER['files'][0]['customproperties']['contextmenuaction(%d)'%n] for n in (0,1)])
  self.assertEqual(movie['art'],{'poster':'p.jpg','fanart':'f.jpg','clearlogo':'l.png','landscape':'w.jpg'})
  self.assertEqual(movie['ids'],{'tmdb':'1423191','imdb':'tt1'})
  self.assertEqual(movie['info']['mediatype'],'movie');self.assertEqual(movie['info']['duration'],5700)
  self.assertNotIn('season',movie['info']);self.assertNotIn('tvshowtitle',movie['info'])
  self.assertEqual(items[1]['info'],{'mediatype':'tvshow'})
 def test_fields_asked_exist_in_kodi_21(self):
  # Build-134 asked for "tvshowtitle": Kodi refused the whole Files.GetDirectory call. List.Fields.Files, JSON-RPC 13.5:
  known={'title','year','genre','rating','votes','plot','mpaa','art','uniqueid','showtitle','season','episode','runtime','premiered',
         'playcount','resume','director','tagline','originaltitle','studio','country','trailer','customproperties','cast','file'}
  self.assertLessEqual(set(cache.PROPERTIES),known);self.assertNotIn('tvshowtitle',cache.PROPERTIES)
 def test_write_reads_back_and_damaged_copies_are_refused(self):
  key=cache.row_key(TRENDING)
  self.assertTrue(self.store.write(key,TRENDING,cache.from_rpc(ANSWER),1000))
  self.assertEqual(len(self.store.load(key)['items']),2);self.assertFalse(os.path.exists(self.store.path(key)+'.tmp'))
  good=self.store.read(key)
  for text in ('',good[:len(good)//2],'[]',good.replace('"format":1','"format":0'),good.replace(TRENDING,POPULAR),
               json.dumps({'format':1,'key':key,'url':TRENDING,'time':1,'items':[]})):
   self.assertIsNone(cache.parse(text,key),text[:60])
  self.assertIsNone(cache.parse(good,cache.row_key(POPULAR)))
  self.assertIsNotNone(cache.parse(good,key,now=1000+cache.KEEP-1));self.assertIsNone(cache.parse(good,key,now=1001+cache.KEEP))

class RouteTests(Base):
 def test_lists_the_copy_with_real_paths(self):
  key=cache.row_key(TRENDING);self.store.write(key,TRENDING,cache.from_rpc(ANSWER),10**6)
  added,kodi=self.serve(key)
  self.assertEqual([(u,f) for u,_,f in added],[(MOVIE,False),(SHOW,True)]);self.assertEqual(kodi.builtins,[])
  li=added[0][1]
  self.assertEqual(li.path,MOVIE);self.assertEqual(li.props['isplayable'],'true');self.assertEqual(len(li.menu),2)
  self.assertEqual(li.tag.values['setMediaType'],('movie',));self.assertEqual(li.tag.values['setYear'],(2026,))
  self.assertEqual(li.tag.values['setGenres'],(['Horror'],));self.assertEqual(li.tag.values['setUniqueIDs'][0]['tmdb'],'1423191')
 def test_missing_or_damaged_copy_lists_nothing_and_turns_the_flag_off(self):
  key=cache.row_key(TRENDING)
  for damage in (None,'{not json','{"format":1}'):
   if damage is not None:
    os.makedirs(self.store.folder,exist_ok=True);Path(self.store.path(key)).write_text(damage)
   added,kodi=self.serve(key)
   self.assertEqual(added,[]);self.assertEqual(kodi.builtins,['Skin.Reset(PortraitCache.%s)'%key]);self.assertTrue(kodi.logs)
 def test_copy_too_old_goes_live(self):
  key=cache.row_key(TRENDING);self.store.write(key,TRENDING,cache.from_rpc(ANSWER),0)
  added,kodi=self.serve(key,now=cache.KEEP+1);self.assertEqual(added,[]);self.assertEqual(len(kodi.builtins),1)
 def test_hero_copy_only_for_the_current_spotlight(self):
  self.store.write('hero.home',TRENDING,cache.from_rpc(ANSWER),10**6)
  spot='Skin.String(HomeSwitcher.home.Spotlight.Path)'
  self.assertEqual(len(self.serve('hero.home',{spot:TRENDING})[0]),2)
  added,kodi=self.serve('hero.home',{spot:POPULAR});self.assertEqual(added,[]);self.assertEqual(kodi.builtins,['Skin.Reset(PortraitCache.hero.home)'])
 def test_bad_keys_touch_nothing(self):
  for key in ('../../guisettings','hero.home)','r1234'):
   added,kodi=self.serve(key);self.assertEqual((added,kodi.builtins),([],[]))
 def test_route_reads_a_file_and_nothing_else(self):
  src=(WATCH/'resources/lib/ios_cache.py').read_text()
  self.assertNotIn('executeJSONRPC',src);self.assertNotIn('import tmdb',src)
  default=(WATCH/'default.py').read_text();body=default[default.index('def run('):]
  block=body[:body.index('import xbmc,xbmcaddon')]
  self.assertIn("action=cached&key=",block);self.assertIn('ios_cache.serve(',block);self.assertNotIn('JSONRPC',block)
 def run_plugin(self,key,broken=False):
  """The plugin's real entry point (default.py) with stand-in Kodi modules."""
  kodi=FakeKodi();ends=[];added=[]
  fakes={'xbmc':kodi,'xbmcgui':SimpleNamespace(ListItem=FakeItem),'xbmcvfs':SimpleNamespace(translatePath=lambda p:self.store.folder),
         'xbmcplugin':SimpleNamespace(addDirectoryItems=lambda h,i,n:added.extend(i),setContent=lambda h,c:None,
                                      endOfDirectory=lambda h,succeeded=True,cacheToDisc=True:ends.append(succeeded))}
  saved={k:sys.modules.get(k) for k in list(fakes)+['ios_cache']}
  sys.modules.update(fakes)
  sys.modules['ios_cache']=SimpleNamespace(FOLDER='x',Store=cache.Store,serve=None) if broken else cache
  try:
   spec=importlib.util.spec_from_file_location('watch_default',WATCH/'default.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   mod.run(['plugin://plugin.video.kodi.ios.watch/','7','?action=cached&key='+key,'resume:false'])
  finally:
   for k,v in saved.items():
    if v is None:sys.modules.pop(k,None)
    else:sys.modules[k]=v
  return added,ends,kodi.builtins
 def test_plugin_entry_point_serves_and_never_leaves_a_row_stuck(self):
  key=cache.row_key(TRENDING);self.store.write(key,TRENDING,cache.from_rpc(ANSWER),time.time())
  added,ends,builtins=self.run_plugin(key);self.assertEqual((len(added),ends,builtins),(2,[True],[]))
  added,ends,builtins=self.run_plugin(key,broken=True)   # any failure in the route: flag off, directory ended
  self.assertEqual((added,ends,builtins),([],[False],['Skin.Reset(PortraitCache.%s)'%key]))

class FlagTests(Base):
 def test_row_and_hero_flags(self):
  key=cache.row_key(TRENDING)
  self.assertTrue(self.flags.set(key,TRENDING));self.assertEqual(self.runs[-1],'Skin.SetBool(PortraitCache.%s)'%key)
  self.assertTrue(self.flags.on(key,TRENDING))
  self.flags.set('hero.home',TRENDING);self.assertEqual(self.runs[-1],'Skin.SetString(PortraitCache.hero.home,"%s")'%TRENDING)
  self.assertTrue(self.flags.on('hero.home',TRENDING));self.assertFalse(self.flags.on('hero.home',POPULAR))
  self.assertFalse(self.flags.set('hero.1101','plugin://plugin.video.themoviedb.helper/?q="x"'))
  self.flags.clear(key);self.assertFalse(self.flags.on(key,TRENDING))
 def test_start_check_turns_off_flags_without_a_copy_and_restores_lost_ones(self):
  gone,kept,lost=cache.row_key(TRENDING),cache.row_key(POPULAR),'hero.home'
  self.flags.set(gone,TRENDING);self.flags.set(kept,POPULAR)
  self.store.write(kept,POPULAR,cache.from_rpc(ANSWER),10**6);self.store.write(lost,TRENDING,cache.from_rpc(ANSWER),10**6)
  on,cleared=cache.check([(gone,TRENDING),(kept,POPULAR),(lost,TRENDING)],self.store,self.flags,lambda:10**6)
  self.assertEqual((on,cleared),(2,1))
  self.assertFalse(self.flags.on(gone,TRENDING));self.assertTrue(self.flags.on(kept,POPULAR));self.assertTrue(self.flags.on(lost,TRENDING))
 def test_hero_copy_of_an_old_spotlight_is_not_flagged(self):
  self.store.write('hero.home',TRENDING,cache.from_rpc(ANSWER),10**6);self.flags.set('hero.home',TRENDING)
  self.assertEqual(cache.check([('hero.home',POPULAR)],self.store,self.flags,lambda:10**6),(0,1))
  self.assertEqual(self.skin.get('PortraitCache.hero.home'),None)

class RefreshTests(Base):
 def fetch(self,url):self.fetched.append(url);return ANSWER
 def test_fills_one_at_a_time_and_flags_only_after_the_copy_reads_back(self):
  self.fetched=[];lists=cache.targets({'home':TRENDING,'1101':'videodb://tvshows/'},[TRENDING,POPULAR,'videodb://movies/'])
  self.assertEqual([k for k,_ in lists],['hero.home',cache.row_key(TRENDING),cache.row_key(POPULAR)])
  order=[]
  def fetch(url):order.append(('fetch',url,dict(self.skin)));return ANSWER
  done,failed=cache.refresh(lists,self.store,self.flags,fetch,lambda s:order.append(('wait',s)) and False,lambda:10**6)
  self.assertEqual((len(done),failed),(3,[]))
  self.assertEqual([o[0] for o in order],['fetch','wait']*3)              # never two TMDb Helper runs together
  self.assertEqual(order[1][2] if order[1][0]=='fetch' else order[2][2],{'PortraitCache.hero.home':TRENDING})  # flag after the copy
  self.assertTrue(all(self.flags.on(k,u) for k,u in lists))
 def test_only_stale_copies_run_again(self):
  self.fetched=[];key=cache.row_key(TRENDING)
  self.store.write(key,TRENDING,cache.from_rpc(ANSWER),1000)
  cache.refresh([(key,TRENDING)],self.store,self.flags,self.fetch,lambda s:False,lambda:1000+60)
  self.assertEqual(self.fetched,[]);self.assertTrue(self.flags.on(key,TRENDING))
  cache.refresh([(key,TRENDING)],self.store,self.flags,self.fetch,lambda s:False,lambda:1001+cache.MAX_AGE)
  self.assertEqual(self.fetched,[TRENDING])
 def test_failed_or_empty_run_keeps_the_old_copy_and_sets_no_flag(self):
  key,new=cache.row_key(TRENDING),cache.row_key(POPULAR)
  self.store.write(key,TRENDING,cache.from_rpc(ANSWER),0)
  def broken(url):
   if url==TRENDING:raise RuntimeError('Invalid params.')
   return {'files':[]}
  done,failed=cache.refresh([(key,TRENDING),(new,POPULAR)],self.store,self.flags,broken,lambda s:False,lambda:10**5)
  self.assertEqual(done,[]);self.assertEqual(len(failed),2);self.assertIn('Invalid params',failed[0])
  self.assertEqual(len(self.store.load(key)['items']),2);self.assertIsNone(self.store.load(new))
  self.assertFalse(self.flags.on(new,POPULAR))
 def test_stops_when_kodi_exits(self):
  self.fetched=[]
  cache.refresh([(cache.row_key(TRENDING),TRENDING),(cache.row_key(POPULAR),POPULAR)],self.store,self.flags,self.fetch,lambda s:True,lambda:0)
  self.assertEqual(self.fetched,[TRENDING])
 def test_prune_only_old_copies_no_hub_shows(self):
  key,old=cache.row_key(TRENDING),cache.row_key(POPULAR)
  for k,u in ((key,TRENDING),(old,POPULAR)):self.store.write(k,u,cache.from_rpc(ANSWER),0)
  self.assertEqual(cache.prune(self.store,[(key,TRENDING)],lambda:os.path.getmtime(self.store.path(old))+8*86400),[old])
  self.assertIsNotNone(self.store.load(key))

class SkinTests(unittest.TestCase):
 def hubs(self):
  widgets=[{'label':'Continue','path':portrait.CONTINUE+'all'},{'label':'Trending','path':TRENDING},{'label':'Mine','path':'videodb://movies/titles/'}]
  hubs=[(tab,(tab.title(),widgets,tab,spot,'all')) for tab,spot in (('home','home'),('movies','1102'),('tv','1101'))]
  variables={};root=ET.fromstring(portrait.hubs_window('<window id="0"/>',hubs,variables));return root,variables
 def test_names_keys_and_route_match_the_plugin(self):
  self.assertEqual((portrait.CACHE_ROUTE,portrait.CACHE_FLAG,portrait.CACHEABLE),(cache.ROUTE,cache.FLAG,cache.CACHEABLE))
  self.assertEqual(portrait.cache_key(TRENDING),cache.row_key(TRENDING));self.assertTrue(cache.valid_key(portrait.cache_key(TRENDING)))
  self.assertEqual(portrait.spotlight_path('1101'),cache.hero_skin_path(cache.hero_key('1101')))
 def test_rows_choose_cached_or_live_from_saved_flags(self):
  root,variables=self.hubs();key=cache.row_key(TRENDING)
  row=ET.fromstring(variables['Portrait_Cache_Row_home_2']).findall('value')
  self.assertEqual(row[0].get('condition'),'Skin.HasSetting(PortraitCache.%s) + System.AddonIsEnabled(plugin.video.kodi.ios.watch)'%key)
  self.assertEqual((row[0].text,row[1].text,row[1].get('condition')),(cache.ROUTE+key,TRENDING,None))
  contents=[c.findtext('content') for c in root.iter('control') if c.get('type')=='list' and c.findtext('content')]
  self.assertIn(portrait.CONTINUE+'all',contents);self.assertIn('videodb://movies/titles/',contents)  # not TMDb Helper: as before
  self.assertIn('$VAR[Portrait_Cache_Row_tv_2]',contents)
 def test_hero_compares_its_flag_with_the_current_spotlight(self):
  _,variables=self.hubs()
  hero=ET.fromstring(variables['Portrait_Cache_Hero_movies']).findall('value')
  self.assertIn('String.IsEqual(Skin.String(PortraitCache.hero.1102),Skin.String(HomeSwitcher.1102.Spotlight.Path))',hero[0].get('condition'))
  self.assertIn('!String.IsEmpty(Skin.String(PortraitCache.hero.1102))',hero[0].get('condition'))
  self.assertEqual((hero[0].text,hero[1].text),(cache.ROUTE+'hero.1102','$INFO[Skin.String(HomeSwitcher.1102.Spotlight.Path)]'))
 def test_service_lists_every_hub_home_first(self):
  with tempfile.TemporaryDirectory() as tmp:
   nodes=Path(tmp)/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3';nodes.mkdir(parents=True)
   for name,path in (('homewidgets',TRENDING),('1102widgets',POPULAR),('1101widgets','videodb://tvshows/')):
    (nodes/('skinvariables-shortcut-%s.json'%name)).write_text(json.dumps([{'label':'x','path':path},{'label':'In Progress','path':TRENDING+'&inprogress'}]))
   spots,rows=portrait.cache_lists(tmp,lambda s:'spot-'+s)
   self.assertEqual(list(spots),['home','1102','1101']);self.assertEqual(rows,[TRENDING,POPULAR,'videodb://tvshows/'])
 def test_service_thread_checks_at_once_and_runs_tmdb_helper_only_later(self):
  calls=[]
  fake=SimpleNamespace(check=lambda lists,store,flags,clock:calls.append('check') or (0,0),
                       refresh=lambda lists,store,flags,fetch,wait,clock:calls.append('refresh') or ([],[]),
                       prune=lambda store,lists,clock:None)
  waits=iter([False,True])
  def wait(s):calls.append(('wait',s));return next(waits)
  portrait.listing_cache(fake,None,None,lambda:[],None,wait,lambda:False,lambda t:None)
  self.assertEqual(calls,['check',('wait',portrait.REFRESH_AFTER),'refresh',('wait',portrait.REFRESH_EVERY)])
  self.assertGreaterEqual(portrait.REFRESH_AFTER,15)
 def test_service_waits_while_video_plays(self):
  calls=[];busy=iter([True,True,False])
  fake=SimpleNamespace(check=lambda *a:(0,0),refresh=lambda *a:calls.append('refresh') or ([],[]),prune=lambda *a:None)
  waits=iter([False,False,False,True])
  portrait.listing_cache(fake,None,None,lambda:[],None,lambda s:calls.append(s) or next(waits),lambda:next(busy,False),lambda t:None)
  self.assertEqual(calls,[portrait.REFRESH_AFTER,30,30,'refresh',portrait.REFRESH_EVERY])

if __name__=='__main__':unittest.main()
