"""The watch plugin's listing cache (ios_cache.py): hub rows answer from the last TMDb Helper result at once."""
import importlib.util,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ios_cache',ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
TRENDING='plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie&widget=true'
RPC={'files':[
 {'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=1','filetype':'file','label':'Dune','type':'movie',
  'year':2021,'genre':['Sci-Fi'],'rating':8.1,'plot':'Sand.','art':{'poster':'p.jpg','fanart':'f.jpg','clearart':'x'},'uniqueid':{'tmdb':1}},
 {'file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=tv&tmdb_id=2','filetype':'directory','label':'Show','type':'tvshow','uniqueid':{'tmdb':'2'}},
 {'file':'','label':'broken'}]}

class FakeItem:
 def __init__(self,label='',offscreen=False):self.label=label;self.props={};self.info=None;self.art=None;self.ids=None
 def setArt(self,a):self.art=a
 def setInfo(self,kind,i):self.info=i
 def setUniqueIDs(self,i):self.ids=i
 def setProperty(self,k,v):self.props[k]=v

class CacheTests(unittest.TestCase):
 def setUp(self):
  self.files={};self.read=lambda p:self.files.get(p,'');self.write=self.files.__setitem__;self.calls=[]
 def rpc(self,method,params):self.calls.append(params['directory']);return RPC
 def run_route(self,query):
  added=[]
  plugin=SimpleNamespace(addDirectoryItem=lambda h,u,li,isFolder:added.append((u,li,isFolder)),
                         setContent=lambda h,c:None,endOfDirectory=lambda h,cacheToDisc=True:None)
  def jsonrpc(request):
   self.calls.append(json.loads(request)['params']['directory']);return json.dumps({'result':RPC})
  cache.directory(1,query,SimpleNamespace(executeJSONRPC=jsonrpc),SimpleNamespace(ListItem=FakeItem),plugin,self.read,self.write)
  return added
 def test_route_round_trips_encoded_and_raw(self):
  wrapped=cache.route(TRENDING)
  self.assertTrue(wrapped.startswith(cache.ROUTE));self.assertNotIn('&tmdb',wrapped)
  self.assertEqual(cache.url_from_query('?'+wrapped.split('?',1)[1]),TRENDING)
  self.assertEqual(cache.url_from_query('action=cached&url='+TRENDING),TRENDING)  # hero: raw skin string
  self.assertEqual(cache.route('videodb://movies/'),'videodb://movies/')
 def test_items_keep_path_kind_and_skin_fields(self):
  items=cache.from_rpc(RPC)
  self.assertEqual([i['path'] for i in items],[f['file'] for f in RPC['files'][:2]])
  self.assertEqual([i['folder'] for i in items],[False,True])
  self.assertEqual(items[0]['art'],{'poster':'p.jpg','fanart':'f.jpg'})
  self.assertEqual(cache.properties(items[0]),{'tmdb_id':'1','tmdb_type':'movie','IsPlayable':'true'})
  self.assertEqual(cache.properties(items[1]),{'tmdb_id':'2','tmdb_type':'tv'})
  self.assertEqual(cache.info(items[0])['mediatype'],'movie')
 def test_first_visit_runs_the_list_once_then_serves_the_copy(self):
  query='?'+cache.route(TRENDING).split('?',1)[1]
  first=self.run_route(query);self.assertEqual(self.calls,[TRENDING])
  second=self.run_route(query);self.assertEqual(self.calls,[TRENDING])  # no second TMDb Helper run
  self.assertEqual([(u,f) for u,_,f in first],[(u,f) for u,_,f in second])
  self.assertEqual(second[0][1].props['IsPlayable'],'true');self.assertFalse(second[0][2]);self.assertTrue(second[1][2])
 def test_other_spotlights_pass_through_live(self):
  self.run_route('action=cached&url=videodb://movies/titles/');self.run_route('action=cached&url=videodb://movies/titles/')
  self.assertEqual(len(self.calls),2);self.assertEqual(self.files,{})
 def test_empty_url_lists_nothing(self):
  self.assertEqual(self.run_route('action=cached&url='),[]);self.assertEqual(self.calls,[])
 def test_refresh_only_stale_one_at_a_time(self):
  cache.store(self.write,TRENDING,cache.from_rpc(RPC),now=lambda:1000)
  other=TRENDING.replace('trending_week','popular')
  done=cache.refresh(self.rpc,self.read,self.write,[TRENDING,other,other,'videodb://x'],now=lambda:1060)
  self.assertEqual(done,[other]);self.assertEqual(self.calls,[other])
  self.assertEqual(cache.refresh(self.rpc,self.read,self.write,[TRENDING],now=lambda:1001+cache.MAX_AGE),[TRENDING])
 def test_failed_refresh_keeps_old_copy(self):
  cache.store(self.write,TRENDING,cache.from_rpc(RPC),now=lambda:0)
  cache.refresh(lambda m,p:None,self.read,self.write,[TRENDING],now=lambda:10**9)
  self.assertEqual(len(cache.load(self.read,TRENDING)['items']),2)
 def test_portrait_wraps_rows_like_the_plugin(self):
  import portrait
  self.assertEqual(portrait.CACHED,cache.ROUTE);self.assertEqual(portrait.CACHEABLE,cache.CACHEABLE)
  self.assertEqual(portrait.cached(TRENDING),cache.route(TRENDING))
  self.assertEqual(portrait.cached(portrait.CONTINUE+'all'),portrait.CONTINUE+'all')
 def test_refresher_waits_for_the_start_then_runs(self):
  import portrait
  waits=[];fake=SimpleNamespace(refresh=lambda rpc,r,w,paths,wait,pause:list(paths))
  out=portrait.listing_refresher(fake,None,None,None,lambda:[TRENDING],lambda s:waits.append(s) or False)
  self.assertEqual(out,[TRENDING]);self.assertEqual(waits[0],portrait.REFRESH_AFTER);self.assertGreaterEqual(portrait.REFRESH_AFTER,20)
  self.assertEqual(portrait.listing_refresher(fake,None,None,None,lambda:[TRENDING],lambda s:True),[])
 def test_route_is_checked_before_the_heavy_imports(self):
  src=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/default.py').read_text()
  self.assertLess(src.index("action=cached&"),src.index("parse_qs(argv[2]"))
  self.assertNotIn('import tmdb',(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_cache.py').read_text())
if __name__=='__main__':unittest.main()
