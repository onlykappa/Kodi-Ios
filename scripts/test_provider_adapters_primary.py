"""Headless Jacktook/POV contracts plus actual entrypoints loaded from immutable official ZIP fixtures.

Set KODI_PROVIDER_INPUTS to the flat verified provider ZIP directory and KODI_REQUIRE_PROVIDER_FIXTURES=1
to make absence an error. Fixture source stays outside Git; no scraping implementation is vendored here.
"""
import ast,concurrent.futures,contextlib,dataclasses,enum,hashlib,html,importlib.util,json,os,re,sys,threading,time,types,typing,unicodedata,unittest,zipfile
from pathlib import Path
from string import printable
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
from provider_adapters import jacktook,pov
FIXTURES=Path(os.environ.get('KODI_PROVIDER_INPUTS') or os.environ.get('KODI_PROVIDER_FIXTURES') or str(ROOT.parent/'scratch/provider-fallback/addons'))
REQUEST={'media_type':'episode','title':'Pilot','show_title':'Lanterns','year':'2026','imdb':'tt1234567','tmdb':'99','tvdb':'88','season':0,'episode':1,'aliases':['The Lanterns'],'purpose':'stream'}

class Cache:
 def __init__(self,values=None):self.values=dict(values or {});self.writes=[]
 def get(self,key,*args,**kwargs):return self.values.get(key)
 def set(self,key,value,*args,**kwargs):self.writes.append(key);self.values[key]=value

class Context:
 def __init__(self,modules=None,settings=None,session=None):
  self.modules=modules or {};self.settings=types.SimpleNamespace(getSetting=lambda key:(settings or {}).get(key,''))
  self.session=session;self.stopped=False;self.checks=0
 def import_module(self,name):return self.modules[name]
 def remaining(self):return 20
 def cancelled(self):return self.stopped
 def check(self):
  self.checks+=1
  if self.stopped:raise TimeoutError('Fixture cancelled')

def fixture_source(addon,relative):
 archive=next((folder/(addon+'.zip') for folder in (FIXTURES,FIXTURES.parent) if (folder/(addon+'.zip')).exists()),None)
 if archive is None:
  if os.environ.get('KODI_REQUIRE_PROVIDER_FIXTURES')=='1':raise AssertionError('Pinned provider fixture missing: '+addon)
  raise unittest.SkipTest('Pinned official provider ZIP fixtures not supplied')
 lock=json.loads((ROOT/'migration/provider-fallback/source-lock.json').read_text())
 metadata=next(spec for spec in lock['packages'] if spec['id']==addon)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['sha256']
 with zipfile.ZipFile(archive) as zipped:return zipped.read(addon+'/'+relative).decode('utf-8-sig')

def upstream(addon,relative,environment=None,names=None):
 source=fixture_source(addon,relative);tree=ast.parse(source)
 if names is None:tree.body=[node for node in tree.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
 else:tree.body=[node for node in tree.body if (isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names)
                 or (isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in names for target in node.targets))]
 name='fixture_'+addon.replace('.','_')+'_'+relative.replace('/','_').replace('.','_')
 module=types.ModuleType(name);sys.modules[name]=module
 module.__dict__.update(vars(typing));module.__dict__.update(environment or {})
 exec(compile(ast.fix_missing_locations(tree),relative,'exec'),module.__dict__)
 return module

class Contracts(unittest.TestCase):
 def test_jacktook_normalizes_bytes_quality_and_preserves_upstream_payload(self):
  native=types.SimpleNamespace(title='Lanterns.S00E01.2160p.mkv',size=2*1024**3,quality='2160',seeders=7,infoHash='a'*40,url='',indexer='Fixture')
  module=types.SimpleNamespace(cache=Cache({'stremio_addons':[]}),search_client=Mock(return_value=[native]),pre_process_results=Mock(side_effect=lambda rows,*a,**k:rows))
  ctx=Context({'lib.search':module});found=jacktook.search(REQUEST,ctx)
  self.assertEqual((found[0]['quality'],found[0]['size'],found[0]['seeders']),('4k',2,7))
  self.assertEqual(found[0]['resolver']['native']['infoHash'],'a'*40)
  self.assertEqual(module.search_client.call_args.args[0:4],('Lanterns',{'imdb_id':'tt1234567','tmdb_id':'99','tvdb_id':'88'},'tv','tv'))
  self.assertFalse(module.search_client.call_args.kwargs['show_dialog']);json.dumps(found)
 def test_jacktook_existing_empty_selection_does_not_get_default_sources(self):
  for saved in ({'stremio_addons':'[]'},{'source_manager_selection':[]},{'source_manager_selection':'[]'},{'source_manager_selection':''}):
   with self.subTest(saved=saved):
    module=types.SimpleNamespace(cache=Cache(saved))
    self.assertIsNone(jacktook._defaults(module,Context()))
 def test_jacktook_preserves_existing_server_configuration(self):
  module=types.SimpleNamespace(cache=Cache())
  self.assertIsNone(jacktook._defaults(module,Context(settings={'jackett_host':'https://fixture.invalid'})))
 def test_jacktook_cancellation_is_not_an_empty_success(self):
  ctx=Context();ctx.stopped=True
  with self.assertRaises(TimeoutError):jacktook.search(REQUEST,ctx)
 def test_pov_passes_original_title_ids_aliases_and_special_coordinates(self):
  seen=[]
  class Provider:
   hasEpisodes=True
   def sources(self,data,hosts):
    seen.append((data,hosts));return [dict(name='Lanterns.S00E01.1080p.mkv',quality='1080p',size=1.5,seeders=8,hash='a'*40,url='magnet:?xt=urn:btih:'+'a'*40)]
  ctx=Context({'pov':types.SimpleNamespace(sources=lambda:[('fixture',Provider)])})
  found=pov.search(REQUEST,ctx)
  self.assertEqual((seen[0][0]['tvshowtitle'],seen[0][0]['season'],seen[0][0]['episode']),('Lanterns','0','1'))
  self.assertEqual(seen[0][0]['aliases'],[{'title':'The Lanterns','country':''}]);self.assertEqual(seen[0][1],{})
  self.assertEqual(found[0]['size'],1.5);self.assertEqual(found[0]['resolver']['native']['provider'],'fixture');json.dumps(found)
 def test_pov_pack_parser_receives_its_native_shared_request_first(self):
  calls=[]
  class Provider:
   hasEpisodes=True;pack_capable=True
   def sources(self,*args):calls.append('sources');return []
   def sources_packs(self,*args):calls.append('packs');return []
  pov.search(dict(REQUEST,purpose='packs'),Context({'pov':types.SimpleNamespace(sources=lambda:[('fixture',Provider)])}))
  self.assertEqual(calls,['sources','packs'])
 def test_pov_discovery_never_imports_the_player_or_debrid_resolver(self):
  ctx=Context({'pov':types.SimpleNamespace(sources=lambda:[])})
  self.assertEqual(pov.search(REQUEST,ctx),[]);self.assertEqual(set(ctx.modules),{'pov'})
 def test_pov_resolve_only_selected_candidate_and_preserve_native_meta(self):
  chosen=[]
  class Source:
   def __init__(self,native,meta):chosen.append((native,meta))
   def resolve_sources(self):return 'https://fixture.invalid/selected.mkv'
  ctx=Context({'modules.debrid':types.SimpleNamespace(debrid_enabled=lambda:['alldebrid'],Source=Source)})
  candidate={'resolver':{'native':dict(url='magnet:?xt=urn:btih:'+'a'*40,hash='a'*40,scrape_provider='external'), 'request':REQUEST}}
  self.assertEqual(pov.resolve(candidate,ctx),'https://fixture.invalid/selected.mkv')
  self.assertEqual(chosen[0][0]['debrid'],'alldebrid');self.assertEqual(chosen[0][1]['season'],'0')
 def test_pov_no_native_account_returns_the_existing_torrent_pipeline_locator(self):
  magnet='magnet:?xt=urn:btih:'+'a'*40
  ctx=Context({'modules.debrid':types.SimpleNamespace(debrid_enabled=lambda:[])})
  self.assertEqual(pov.resolve({'resolver':{'native':{'url':magnet}}},ctx),magnet)
 def test_pov_deadline_interrupts_before_provider_discovery(self):
  ctx=Context();ctx.stopped=True
  with self.assertRaises(TimeoutError):pov.search(REQUEST,ctx)

class OfficialJacktook(unittest.TestCase):
 def setUp(self):
  self.playback=upstream('plugin.video.jacktook','lib/clients/stremio/playback.py',
    dict(json=json,re=re,dataclass=dataclasses.dataclass,field=dataclasses.field,is_youtube_addon_enabled=lambda:False,
         parse_qs=__import__('urllib.parse',fromlist=['parse_qs']).parse_qs,quote=__import__('urllib.parse',fromlist=['quote']).quote,
         unquote=__import__('urllib.parse',fromlist=['unquote']).unquote,urlparse=__import__('urllib.parse',fromlist=['urlparse']).urlparse))
 def test_real_native_playback_entrypoint_resolves_hash_and_preserves_direct_headers(self):
  ctx=Context({'lib.clients.stremio.playback':self.playback})
  magnet=jacktook.resolve({'resolver':{'native':dict(title='Lanterns.S00E01.1080p',infoHash='a'*40)}},ctx)
  self.assertTrue(magnet.startswith('magnet:?xt=urn:btih:'+'a'*40))
  direct=dict(title='Lanterns.S00E01.1080p',url='https://fixture.invalid/video.mkv',stremioMetadata={'behaviorHints':{'proxyHeaders':{'request':{'User-Agent':'Fixture Player'}}}})
  result=jacktook.resolve({'resolver':{'native':direct}},ctx)
  self.assertIn('User-Agent=Fixture',result)
 def test_real_native_playback_rejects_unsafe_header_metadata(self):
  ctx=Context({'lib.clients.stremio.playback':self.playback})
  native=dict(title='Lanterns',url='https://fixture.invalid/video.mkv',stremioMetadata={'headers':{'Bad\nHeader':'x'}})
  with self.assertRaises(Exception):jacktook.resolve({'resolver':{'native':native}},ctx)
 def test_real_search_client_and_stremio_client_run_headless_with_ephemeral_public_defaults(self):
  parsed=__import__('urllib.parse',fromlist=['urlsplit'])
  addon_manager=upstream('plugin.video.jacktook','lib/api/stremio/addon_manager.py',dict(hashlib=hashlib,json=json,urlsplit=parsed.urlsplit,urlunsplit=parsed.urlunsplit,kodilog=lambda *a,**k:None))
  enums=upstream('plugin.video.jacktook','lib/utils/general/utils.py',{'Enum':enum.Enum},names={'IndexerType','Indexer','SearchVariant'})
  torrent=upstream('plugin.video.jacktook','lib/domain/torrent.py',dict(dataclass=dataclasses.dataclass,field=dataclasses.field))
  protocol=upstream('plugin.video.jacktook','lib/clients/stremio/protocol.py',dict(hashlib=hashlib,json=json,re=re,ipaddress=__import__('ipaddress'),socket=__import__('socket'),quote=parsed.quote,urljoin=parsed.urljoin,urlsplit=parsed.urlsplit))
  seen=[]
  class Response:
   status_code=200
   def __init__(self,data):self.data=data;self.content=json.dumps(data).encode();self.headers={}
   def json(self):return self.data
   def raise_for_status(self):pass
   def close(self):pass
  class Session:
   def get(self,url,**kwargs):
    seen.append(url)
    if url.endswith('/manifest.json'):
     return Response({'id':url.split('/')[2],'name':'Fixture','version':'1.0','resources':['stream'],'types':['movie','series'],'idPrefixes':['tt'],'catalogs':[]})
    return Response({'streams':[{'name':'Fixture 1080p','title':'Lanterns.S00E01.1080p.mkv','infoHash':'a'*40,'behaviorHints':{'videoSize':2*1024**3}}]})
  session=Session();cache=Cache()
  class BaseClient:
   def __init__(self,*args):self.session=session
   def handle_exception(self,*args):raise AssertionError('Native client failed')
  env=dict(contextlib=contextlib,re=re,timedelta=__import__('datetime').timedelta,BaseClient=BaseClient,TorrentStream=torrent.TorrentStream,Addon=addon_manager.Addon,
           cache=cache,IndexerType=enums.IndexerType,normalize_stream=self.playback.normalize_stream,classify=self.playback.classify,
           get_addon_display_name=lambda addon:addon.manifest.name,build_addon_instance_label=addon_manager.build_addon_instance_label,
           build_resource_url=protocol.build_resource_url,safe_cache_key=protocol.safe_cache_key,cache_ttl_seconds=protocol.cache_ttl_seconds,
           response_json=protocol.response_json,USER_AGENT_HEADER={},get_int_setting=lambda key:10,get_cache_expiration=lambda:0,
           is_cache_enabled=lambda:False,kodilog=lambda *a,**k:None,find_languages_in_string=lambda text:[],
           convert_size_to_bytes=lambda value:0,info_hash_to_magnet=lambda value:'magnet:?xt=urn:btih:'+value,
           xbmc=types.SimpleNamespace(LOGERROR=4,LOGINFO=1))
  client=upstream('plugin.video.jacktook','lib/clients/stremio/addon_client.py',env,names={'_response_data','_candidate_metadata','StremioAddonClient'})
  search_env=dict(ThreadPoolExecutor=concurrent.futures.ThreadPoolExecutor,Future=concurrent.futures.Future,as_completed=concurrent.futures.as_completed,
   cache=cache,SearchVariant=enums.SearchVariant,Indexer=enums.Indexer,TorrentStream=torrent.TorrentStream,
   TITLE_LANGUAGE_LOCALIZED_FIRST='localized_first',MAX_STREMIO_ADDONS_PER_SEARCH=8,StremioAddonClient=client.StremioAddonClient,
   get_setting=lambda key,*a,**k:False,get_selected_stream_addons=lambda:[],get_addon_by_base_url=lambda url:None,
   get_selected_stream_addon_records=lambda:[],reconcile_source_selection=lambda **kwargs:kwargs['cache_backend'].set('source_manager_selection','["ephemeral"]'),
   _build_title_fallback_queries=lambda title,*a,**k:[title],_build_search_cache_scope=lambda *a:'fixture',
   _check_search_caches=lambda *a,**k:None,_search_worker_count=lambda:2,_is_source_enabled=lambda *a,**k:True,
   _is_enabled=lambda key:False,_perform_search_with_title_fallback=lambda *a,**k:[],cache_results=lambda *a,**k:None,
   close_busy_dialog=Mock(side_effect=AssertionError('Provider UI opened')),notification=Mock(side_effect=AssertionError('Provider UI opened')),
   DialogListener=Mock(side_effect=AssertionError('Provider dialog constructed')),kodilog=lambda *a,**k:None,
   xbmc=types.SimpleNamespace(LOGDEBUG=0,LOGINFO=1))
  native_search=upstream('plugin.video.jacktook','lib/search.py',search_env,names={'search_client','_run_simple_search','_submit_search_tasks','_collect_search_results','_perform_search','add_task_if_enabled'})
  native_search.pre_process_results=lambda rows,*a,**k:rows
  ctx=Context({'lib.search':native_search,'lib.clients.stremio.helpers':addon_manager},session=session)
  candidates=jacktook.search(REQUEST,ctx)
  self.assertEqual(len(candidates),2);self.assertEqual(candidates[0]['name'],'Lanterns.S00E01.1080p.mkv')
  self.assertEqual(candidates[0]['size'],2);self.assertTrue(all('/stream/series/tt1234567:0:1.json' in parsed.unquote(url) for url in seen if not url.endswith('manifest.json')))
  self.assertFalse(cache.writes);self.assertEqual(cache.values,{})
  self.assertEqual(len(jacktook.search(REQUEST,ctx)),2)  # a second search must not see invalid persisted defaults

class OfficialPOV(unittest.TestCase):
 def test_real_torrentio_provider_parses_fixture_and_filters_other_titles(self):
  log=types.SimpleNamespace(error=lambda *a,**k:None,log=lambda *a,**k:None,LOGERROR=4)
  clean=upstream('plugin.video.pov','lib/pov/modules/cleantitle.py',dict(re=re,html=html,log_utils=log))
  utils=upstream('plugin.video.pov','lib/pov/modules/source_utils.py',dict(re=re,unicodedata=unicodedata,Future=concurrent.futures.Future,
    printable=printable,thread=threading.Thread,cleantitle=clean,log_utils=log,homeWindow=lambda:types.SimpleNamespace(getProperty=lambda key:''),
    jsloads=json.loads,setSetting=lambda *a:None,getSetting=lambda *a,**k:'false',Undesirables=object))
  seen=[]
  class Session:
   def request(self,method,url,**kwargs):
    seen.append(url)
    return types.SimpleNamespace(text=json.dumps({'streams':[{'infoHash':'a'*40,'title':'Lanterns.S00E01.1080p.WEB.mkv\n👤 12 💾 1.50 GB'},
                                                           {'infoHash':'b'*40,'title':'Other.Show.S00E01.1080p.mkv\n👤 4 💾 2 GB'}]}))
  client=types.SimpleNamespace(randomagent=lambda:'Fixture',session=Session())
  native=upstream('plugin.video.pov','lib/pov/torrentio.py',dict(re=re,Lock=threading.Lock,jsloads=json.loads,client=client,source_utils=utils))
  native.source.clear_all()
  ctx=Context({'pov':types.SimpleNamespace(sources=lambda:[('torrentio',native.source)])})
  found=pov.search(REQUEST,ctx)
  self.assertEqual(len(found),1);self.assertEqual(found[0]['torrent_hash'],'a'*40)
  self.assertEqual((found[0]['quality'],found[0]['size'],found[0]['seeders']),('1080p',1.5,12))
  self.assertEqual(seen,['https://torrentio.strem.fun/stream/series/tt1234567:0:1.json'])
 def test_real_selected_source_resolver_receives_exact_special_episode(self):
  calls=[]
  class API:
   defaults_to_cloud=False
   def parse_magnet_pack(self,*args):return [{'torrent_id':'fixture','filename':'Lanterns.S00E01.1080p.mkv','size':10,'link':'chosen'},
                                           {'torrent_id':'fixture','filename':'Lanterns.S00E02.1080p.mkv','size':20,'link':'wrong'}]
   def unrestrict_link(self,key):calls.append(key);return 'https://fixture.invalid/'+key+'.mkv'
  parsed=__import__('urllib.parse',fromlist=['unquote'])
  functions=upstream('plugin.video.pov','resources/lib/modules/source_utils.py',
    dict(re=re,unicodedata=unicodedata,printable=printable,unescape=html.unescape,unquote=parsed.unquote,
         kodi_utils=types.SimpleNamespace(supported_media=lambda:'.mkv|.mp4')),
    names={'SEAS_EP_REGEX','seas_ep_filter','clean_title','strip_non_ascii_and_unprintable','extras_filter','supported_video_extensions'})
  log=types.SimpleNamespace(local_string=lambda *a:'',get_setting=lambda *a:'',show_busy_dialog=lambda:None,hide_busy_dialog=lambda:None,confirm_dialog=lambda *a:False,select_dialog=lambda *a:None,logger=lambda *a:None)
  settings=types.SimpleNamespace(store_resolved_torrent_to_cloud=lambda *a:False,store_resolved_usenet_to_cloud=lambda *a:False)
  native=upstream('plugin.video.pov','resources/lib/modules/debrid.py',dict(kodi_utils=log,settings=settings,metadata=types.SimpleNamespace(get_title=lambda meta:meta['title']),
    default_external_scrapers=('external',),default_internal_scrapers=(),import_debrid=lambda name:API(),Thread=threading.Thread,json=json),names={'Source'})
  candidate={'resolver':{'native':{'url':'magnet:?xt=urn:btih:'+'a'*40,'hash':'a'*40,'scrape_provider':'external'},'request':REQUEST}}
  with patch.dict(sys.modules,{'modules.source_utils':functions}):
   result=pov.resolve(candidate,Context({'modules.debrid':types.SimpleNamespace(Source=native.Source,debrid_enabled=lambda:['alldebrid'])}))
  self.assertEqual(result,'https://fixture.invalid/chosen.mkv');self.assertEqual(calls,['chosen'])

if __name__=='__main__':unittest.main()
