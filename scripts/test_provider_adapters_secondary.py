"""Secondary adapter contracts plus hash-checked upstream API fixtures (no real accounts/network/playback).

Set PROVIDER_FIXTURES to the pinned extraction parent used by scripts/provider_addons.py for upstream checks.
The class bodies are compiled directly from verified upstream ZIPs; scraper/resolver methods are not copied here.
"""
import ast,hashlib,importlib.util,json,os,sys,tempfile,types,unittest,zipfile
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
from provider_adapters import thecrew,prism,otaku

FIXTURES=Path(os.environ.get('PROVIDER_FIXTURES','/workspace/scratch/provider-fallback'))
MOVIE={'media_type':'movie','title':'Heat','year':1995,'imdb':'tt0113277','tmdb':'949','quality':'1080p'}
EPISODE={'media_type':'episode','title':'Episode two','show_title':'Example Show','year':2020,'imdb':'tt123','tmdb':'100','season':2,'episode':2,'quality':'1080p'}
NATIVE={'release_title':'Heat.1995.1080p.mkv','url':'https://media.example/heat.mkv','quality':'1080p','size':4,'direct':True,'debrid':''}

class Context:
 def __init__(self,modules=None):
  self.modules=modules or {};self.stopped=False;self.addon_id='fixture';self.addon_path='/fixture';self.profile='/private'
  self.import_module=mock.Mock(side_effect=lambda name:self.modules[name]);self.settings=mock.Mock()
 def check(self):
  if self.stopped:raise RuntimeError('cancelled')
 def cancelled(self):return self.stopped
 def remaining(self):return 7.25

def upstream_class(package,relative,name,namespace=None):
 """Read real code only after checking its official package digest against the repository's immutable lock."""
 lock=json.loads((ROOT/'migration/provider-fallback/source-lock.json').read_text())
 expected=next(p for p in lock['packages'] if p['id']==package)
 archive=FIXTURES/(package+'.zip')
 if not archive.is_file():raise unittest.SkipTest('Pinned upstream fixture ZIP is not staged: '+package)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected['sha256']:raise AssertionError('Upstream fixture checksum differs')
 with zipfile.ZipFile(archive) as source:
  matches=[p for p in source.namelist() if p.endswith('/'+relative)]
  if len(matches)!=1:raise AssertionError('Upstream fixture path is ambiguous')
  tree=ast.parse(source.read(matches[0]).decode('utf-8-sig'))
 node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
 globals_={'__name__':'upstream_fixture','BrowserBase':object,**(namespace or {})}
 exec(compile(ast.Module(body=[node],type_ignores=[]),matches[0],'exec'),globals_)
 return globals_[name]

class CrewContract(unittest.TestCase):
 def test_calls_real_scraper_contract_without_ui_flags_or_plugin_play(self):
  scraper=mock.Mock();scraper.getSources.return_value=[dict(NATIVE),dict(NATIVE,local=True)]
  module=types.SimpleNamespace(Sources=lambda:scraper,cleanup_playback_ui=mock.Mock())
  context=Context({'resources.lib.modules.sources':module});result=thecrew.search(EPISODE,context)
  self.assertEqual(len(result),1);self.assertEqual(result[0]['quality'],'1080p');self.assertEqual(result[0]['size'],4)
  args=scraper.getSources.call_args
  self.assertEqual(args.kwargs['season'],'2');self.assertEqual(args.kwargs['episode'],'2')
  self.assertEqual(args.kwargs['tvshowtitle'],'Example Show');self.assertFalse(args.kwargs['show_dialog']);self.assertFalse(args.kwargs['use_overlay'])
  self.assertEqual(args.kwargs['timeout'],7.25);module.cleanup_playback_ui.assert_not_called()
 def test_native_resolver_keeps_encoded_http_headers(self):
  scraper=mock.Mock();scraper.sourcesResolve.return_value='https://media.example/movie.mkv|User-Agent=Kodi+iOS&Cookie=opaque'
  result=thecrew.resolve({'resolver':{'source':dict(NATIVE)}},Context({'resources.lib.modules.sources':types.SimpleNamespace(Sources=lambda:scraper)}))
  self.assertEqual(result,{'url':'https://media.example/movie.mkv','headers':{'User-Agent':'Kodi iOS','Cookie':'opaque'}})
  scraper.sourcesResolve.assert_called_once_with(dict(NATIVE),info=False)
 def test_cancel_before_or_after_upstream_cannot_become_a_normal_provider_miss(self):
  context=Context();context.stopped=True
  with self.assertRaisesRegex(RuntimeError,'cancelled'):thecrew.search(MOVIE,context)
  context.import_module.assert_not_called()
  context=Context();scraper=mock.Mock()
  def stopped(*args,**kwargs):context.stopped=True;return []
  scraper.getSources.side_effect=stopped;context.modules['resources.lib.modules.sources']=types.SimpleNamespace(Sources=lambda:scraper)
  with self.assertRaisesRegex(RuntimeError,'cancelled'):thecrew.search(MOVIE,context)

class PrismContract(unittest.TestCase):
 def setup_search(self,result):
  globals_=types.SimpleNamespace(ADDON_ID='plugin.video.prism',abort_requested=lambda:False,cancel_playback=mock.Mock(),notification=mock.Mock())
  scraper=mock.Mock();scraper.get_sources.return_value=result;scraper.window=types.SimpleNamespace(silent=False)
  module=types.SimpleNamespace(Sources=mock.Mock(return_value=scraper))
  context=Context({'resources.lib.modules.globals':types.SimpleNamespace(g=globals_),'resources.lib.modules.getSources':module})
  return context,globals_,scraper,module
 def test_silent_search_cannot_start_cache_assist_and_serializes_native_sets(self):
  source={'type':'torrent','hash':'abc','release_title':'Heat.1995.1080p','quality':'1080p','size':2048,'info':{'HEVC'},'seeds':7}
  context,g,scraper,module=self.setup_search(([],[source],{}));original=g.cancel_playback
  def run():
   self.assertTrue(scraper.silent);self.assertTrue(scraper.window.silent);self.assertEqual(scraper.timeout,7.25)
   scraper._build_cache_assist();g.cancel_playback();g.notification('ignored');return [],[source],{}
  scraper.get_sources.side_effect=run
  with mock.patch.object(prism,'_providers') as providers:result=prism.search(MOVIE,context)
  providers.assert_called_once();self.assertIs(g.cancel_playback,original);original.assert_not_called()
  self.assertEqual(result[0]['size'],2);self.assertEqual(result[0]['seeders'],7);self.assertEqual(result[0]['resolver']['source']['info'],['HEVC'])
  scraper._send_provider_stop_event.assert_called_once();json.dumps(result)
 def test_resolver_explicitly_forbids_manual_selection_and_unwraps_tuple(self):
  resolver=mock.Mock();resolver.resolve_single_source.return_value=('https://media.example/movie.mkv','Heat')
  g=types.SimpleNamespace(ADDON_ID='plugin.video.prism',abort_requested=lambda:False)
  context=Context({'resources.lib.modules.globals':types.SimpleNamespace(g=g),'resources.lib.modules.resolver':types.SimpleNamespace(Resolver=lambda:resolver)})
  source={'type':'torrent'};meta=prism._metadata(EPISODE)
  self.assertEqual(prism.resolve({'resolver':{'source':source,'metadata':meta}},context),'https://media.example/movie.mkv')
  resolver.resolve_single_source.assert_called_once_with(source,meta,pack_select=False,silent=True,allow_manual_prompt=False)
 def test_bundle_copy_preserves_existing_provider_files(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source';target=Path(tmp)/'target';source.mkdir();target.mkdir()
   (source/'existing.py').write_text('new');(source/'new.py').write_text('new');(target/'existing.py').write_text('owner')
   prism._copy_missing(source,target,Context())
   self.assertEqual((target/'existing.py').read_text(),'owner');self.assertEqual((target/'new.py').read_text(),'new')
 def test_uncached_results_are_not_offered_and_cancel_is_not_an_empty_result(self):
  context,g,scraper,module=self.setup_search(([],[{'type':'torrent (uncached)'}],{}))
  with mock.patch.object(prism,'_providers'):self.assertEqual(prism.search(MOVIE,context),[])
  context.stopped=True
  with self.assertRaisesRegex(RuntimeError,'cancelled'):prism.search(MOVIE,context)

class OtakuContract(unittest.TestCase):
 def request(self):
  return dict(EPISODE,anime=True,anime_mapping={'verified':True,'mal_id':123,'absolute_episode':14,'tmdb':'100','season':2,'episode':2,'kitsu_id':12})
 def context(self,source=None):
  database=types.SimpleNamespace(get_mappings=mock.Mock(return_value={'mal_id':123,'themoviedb_id':'100','kitsu_id':12}))
  control=types.SimpleNamespace(getBool=lambda key:key=='provider.torrentio')
  scraper=mock.Mock();scraper.get_sources.return_value={'cached':[source] if source else [],'uncached':[dict(source or {},type='torrent (uncached)')]}
  module=types.SimpleNamespace(Sources=lambda:scraper)
  return Context({'resources.lib.ui.database':database,'resources.lib.ui.control':control,'resources.lib.pages.torrentio':module}),scraper,database
 def test_movies_and_unverified_or_mismatched_tmdb_coordinates_never_import_otaku(self):
  for request in (MOVIE,dict(self.request(),anime=False),dict(self.request(),season=3),dict(self.request(),tmdb='999')):
   with self.subTest(request=request):
    context=Context();self.assertEqual(otaku.search(request,context),[]);context.import_module.assert_not_called()
 def test_unmapped_ordinary_tv_never_performs_a_metadata_or_scraper_request(self):
  with mock.patch.object(otaku,'_mapping_rows',return_value=[]),mock.patch.object(otaku,'_tmdb_episode') as metadata:
   context=Context();self.assertEqual(otaku.search(EPISODE,context),[]);context.import_module.assert_not_called();metadata.assert_not_called()
 def test_matching_installed_mapping_passes_mal_absolute_episode_to_real_provider(self):
  source={'type':'torrent','cached':True,'quality':3,'release_title':'Example Show - 14.mkv','hash':'abc','debrid_provider':'Alldebrid','byte_size':1024**3,'seeders':4}
  context,scraper,database=self.context(source);result=otaku.search(self.request(),context)
  self.assertEqual(len(result),1);self.assertEqual(result[0]['quality'],'1080p');self.assertEqual(result[0]['size'],1)
  self.assertEqual(scraper.get_sources.call_args.args[1:3],(123,'14'));database.get_mappings.assert_called_once_with(123,'mal_id')
 def test_conflicting_installed_mapping_fails_closed(self):
  context,scraper,database=self.context();database.get_mappings.return_value={'mal_id':123,'themoviedb_id':'999','kitsu_id':12}
  self.assertEqual(otaku.search(self.request(),context),[]);scraper.get_sources.assert_not_called()
 def test_resolver_uses_validated_absolute_episode_without_manual_pack_selection(self):
  context,scraper,database=self.context();api=mock.Mock();api.resolve_single_magnet.return_value='https://media.example/episode.mkv'
  context.modules['resources.lib.debrid.all_debrid']=types.SimpleNamespace(AllDebrid=lambda:api)
  source={'type':'torrent','cached':True,'hash':'abc','debrid_provider':'Alldebrid','filename':'episode14.mkv'}
  self.assertEqual(otaku.resolve({'resolver':{'request':self.request(),'source':source}},context),'https://media.example/episode.mkv')
  api.resolve_single_magnet.assert_called_once_with('abc','magnet:?xt=urn:btih:abc','14',False,'episode14.mkv')

class Admission(unittest.TestCase):
 def test_verified_cached_crew_torrent_with_no_peers_survives_real_admission(self):
  import provider_fallback
  source=dict(NATIVE,url='magnet:?xt=urn:btih:'+'a'*40,source='cached torrent',seeders=0)
  scraper=mock.Mock();scraper.getSources.return_value=[source]
  context=Context({'resources.lib.modules.sources':types.SimpleNamespace(Sources=lambda:scraper)})
  candidate=thecrew.search(MOVIE,context)
  self.assertTrue(candidate[0]['cached']);self.assertEqual(len(provider_fallback.verified(candidate,MOVIE,'thecrew')),1)
  source['source']='uncached torrent';candidate=thecrew.search(MOVIE,context)
  self.assertFalse(candidate[0]['cached']);self.assertEqual(provider_fallback.verified(candidate,MOVIE,'thecrew'),[])
 def test_prism_confirmed_cached_torrent_with_no_peers_survives_real_admission(self):
  import provider_fallback
  source={'type':'torrent','hash':'b'*40,'release_title':'Heat.1995.1080p.mkv','quality':'1080p','size':2048,'seeds':0,'debrid_provider':'all_debrid'}
  context,g,scraper,module=PrismContract().setup_search(([],[source],{}))
  with mock.patch.object(prism,'_providers'):candidate=prism.search(MOVIE,context)
  self.assertTrue(candidate[0]['cached']);self.assertEqual(len(provider_fallback.verified(candidate,MOVIE,'prism')),1)
 def test_otaku_cached_torrent_with_no_peers_survives_real_admission(self):
  import provider_fallback
  request=dict(OtakuContract().request(),season=1,episode=14)
  request['anime_mapping']=dict(request['anime_mapping'],season=1,episode=14)
  source={'type':'torrent','hash':'c'*40,'release_title':'Example.Show.S01E14.1080p.mkv','quality':3,'seeders':0,'cached':True,'debrid_provider':'Alldebrid'}
  context,scraper,database=OtakuContract().context(source)
  candidate=otaku.search(request,context)
  self.assertTrue(candidate[0]['cached']);self.assertEqual(len(provider_fallback.verified(candidate,request,'otaku')),1)

class AuthoritativeAdmission(unittest.TestCase):
 def candidate(self):
  request=OtakuContract().request()
  request['anime_mapping'].update(source='otaku-db+tmdb-episode+ani.zip',title='Canonical Anime',anime_season=1)
  source={'type':'torrent','hash':'c'*40,'release_title':'Canonical.Anime.-.014.1080p.mkv','quality':3,'seeders':0,'cached':True,'debrid_provider':'Alldebrid'}
  context,scraper,database=OtakuContract().context(source)
  return request,context,otaku.search(request,context)
 def test_canonical_mal_absolute_episode_survives_search_and_selected_native_resolver(self):
  import provider_fallback
  request,context,candidates=self.candidate()
  api=mock.Mock();api.resolve_single_magnet.return_value='https://media.example/verified.mkv'
  context.modules['resources.lib.debrid.all_debrid']=types.SimpleNamespace(AllDebrid=lambda:api)
  class Transport:
   def available(self,provider):return provider=='otaku'
   def search(self,provider,query,deadline,cancel):return candidates
   def resolve(self,provider,candidate,query,deadline,cancel):return otaku.resolve(candidate,context)
  transport=Transport()
  found=provider_fallback.search(EPISODE,transport=transport)
  self.assertEqual(len(found),1);self.assertEqual(found[0]['provider'],'otaku')
  self.assertEqual(provider_fallback.resolve(found[0],EPISODE,transport=transport),'https://media.example/verified.mkv')
  self.assertEqual(api.resolve_single_magnet.call_args.args[2],'14')
 def test_authoritative_mapping_cannot_change_original_tmdb_season_or_episode(self):
  import provider_fallback
  request,context,candidates=self.candidate()
  for key,value in [('tmdb','999'),('season',3),('episode',15)]:
   altered=json.loads(json.dumps(candidates))
   altered[0]['resolver']['request']['anime_mapping'][key]=value
   self.assertEqual(provider_fallback.verified(altered,EPISODE,'otaku'),[])
 def test_absolute_episode_mismatch_is_rejected(self):
  import provider_fallback
  request,context,candidates=self.candidate()
  candidates[0]['name']='Canonical.Anime.-.015.1080p.mkv'
  self.assertEqual(provider_fallback.verified(candidates,EPISODE,'otaku'),[])

class MappingDiscovery(unittest.TestCase):
 def row(self,**kwargs):return dict({'mal_id':123,'kitsu_id':12,'mal_title':'Example Show Season 2','themoviedb_id':100,'thetvdb_season':2,'thetvdb_part':1},**kwargs)
 def response(self,**kwargs):return {'mappings':{'mal_id':123},'episodes':{'14':dict({'episode':'14','tvdbId':555,'tmdbId':444,'seasonNumber':1,'episodeNumber':99},**kwargs)}}
 def discover(self,data,rows=None,episode=None):
  api=mock.Mock();api.get_anime_info.return_value=data
  context=Context({'resources.lib.indexers.anizip':types.SimpleNamespace(ANIZIPAPI=lambda:api)})
  with mock.patch.object(otaku,'_mapping_rows',return_value=rows if rows is not None else [self.row()]),mock.patch.object(otaku,'_tmdb_episode',return_value=episode or {'id':444,'external_ids':{'tvdb_id':555}}):
   result=otaku._discover(EPISODE,context)
  return result,api
 def test_exact_episode_ids_bridge_ordering_without_assuming_same_season_or_number(self):
  mapping,api=self.discover(self.response())
  self.assertEqual(mapping['absolute_episode'],14);self.assertEqual((mapping['season'],mapping['episode']),(2,2))
  self.assertEqual(mapping['source'],'otaku-db+tmdb-episode+ani.zip');api.get_anime_info.assert_called_once_with(123)
 def test_mismatched_episode_ids_or_mal_ids_and_ambiguous_episode_ids_fail_closed(self):
  for data in (self.response(tvdbId=999,tmdbId=444),self.response(tvdbId=555,tmdbId=888),self.response(tvdbId=999,tmdbId=888),dict(self.response(),mappings={'mal_id':999}),
               dict(self.response(),episodes={'14':{'episode':'14','tvdbId':555},'15':{'episode':'15','tvdbId':555}})):
   with self.subTest(data=data):self.assertIsNone(self.discover(data)[0])
 def test_request_without_supplied_anime_flag_or_mapping_discovers_then_calls_otaku(self):
  source={'type':'torrent','hash':'c'*40,'release_title':'Example.Show.S02E02.1080p.mkv','quality':3,'cached':True,'debrid_provider':'Alldebrid'}
  context,scraper,database=OtakuContract().context(source)
  mapping,_=self.discover(self.response())
  with mock.patch.object(otaku,'_discover',return_value=mapping):candidates=otaku.search(EPISODE,context)
  self.assertEqual(len(candidates),1);self.assertTrue(candidates[0]['resolver']['request']['anime'])
  self.assertEqual(scraper.get_sources.call_args.args[1:3],(123,'14'))

class RealUpstreamFixtures(unittest.TestCase):
 def test_crew_real_getSources_cache_api_uses_exact_media_coordinates_silently(self):
  c=types.SimpleNamespace(log=lambda *a,**k:None,devmode=False)
  control=types.SimpleNamespace(setting=lambda key:'true')
  Sources=upstream_class('script.module.thecrew','lib/resources/lib/modules/sources.py','Sources',{'c':c,'control':control})
  scraper=Sources.__new__(Sources);scraper.get_cached_sources=mock.Mock(return_value=[dict(NATIVE)])
  module=types.SimpleNamespace(Sources=lambda:scraper)
  result=thecrew.search(EPISODE,Context({'resources.lib.modules.sources':module}))
  self.assertEqual(len(result),1);self.assertTrue(scraper.silent_mode)
  scraper.get_cached_sources.assert_called_once_with('tt123','100','2','2')
 def test_prism_real_finalizer_miss_does_not_start_cache_assist_or_stop_playback(self):
  g=types.SimpleNamespace(ADDON_ID='plugin.video.prism',abort_requested=lambda:False,cancel_playback=mock.Mock(),notification=mock.Mock(),ADDON_NAME='Prism',get_language_string=lambda key:str(key))
  Sources=upstream_class('plugin.video.prism','resources/lib/modules/getSources.py','Sources',{'g':g,'monkey_requests':types.SimpleNamespace(allow_provider_requests=True)})
  scraper=Sources.__new__(Sources);scraper.window=types.SimpleNamespace(silent=False)
  scraper._is_playable_source=lambda:False;scraper.sources_information={'allTorrents':{},'cached_hashes':set()};scraper.item_information=prism._metadata(MOVIE)
  scraper._send_provider_stop_event=mock.Mock();scraper.get_sources=scraper._finalise_results
  context=Context({'resources.lib.modules.globals':types.SimpleNamespace(g=g),'resources.lib.modules.getSources':types.SimpleNamespace(Sources=lambda meta:scraper)})
  with mock.patch.object(prism,'_providers'):self.assertEqual(prism.search(MOVIE,context),[])
  g.cancel_playback.assert_not_called();g.notification.assert_not_called()
 def test_prism_real_selected_source_resolver_direct_api_without_dialogs(self):
  Resolver=upstream_class('plugin.video.prism','resources/lib/modules/resolver/__init__.py','Resolver')
  resolver=Resolver.__new__(Resolver)
  g=types.SimpleNamespace(ADDON_ID='plugin.video.prism')
  context=Context({'resources.lib.modules.globals':types.SimpleNamespace(g=g),'resources.lib.modules.resolver':types.SimpleNamespace(Resolver=lambda:resolver)})
  payload={'source':{'type':'direct','url':'https://media.example/movie.mp4','release_title':'Heat'},'metadata':prism._metadata(MOVIE)}
  self.assertEqual(prism.resolve({'resolver':payload},context),'https://media.example/movie.mp4')
 def test_otaku_real_get_sources_requires_installed_kitsu_mapping_and_returns_cached(self):
  request=OtakuContract().request();context,scraper,database=OtakuContract().context()
  source={'type':'torrent','cached':True,'quality':3,'hash':'hash','debrid_provider':'Alldebrid','release_title':'Example - 14'}
  Sources=upstream_class('plugin.video.otaku','resources/lib/pages/torrentio.py','Sources',{'database':database,'control':types.SimpleNamespace(log=lambda *a:None)})
  real=Sources();real.process_torrentio_episodes=mock.Mock(return_value=[source]);real.append_cache_uncached_noduplicates=lambda:setattr(real,'cached',list(real.sources))
  context.modules['resources.lib.pages.torrentio']=types.SimpleNamespace(Sources=lambda:real)
  result=otaku.search(request,context)
  self.assertEqual(len(result),1);self.assertEqual(real.kitsu_id,12)
  real.process_torrentio_episodes.assert_called_once_with(123,'14',None,None)
 def test_crew_selected_movie_tv_entrypoint_does_not_import_adult_only_modules(self):
  archive=FIXTURES/'script.module.thecrew.zip'
  if not archive.is_file():self.skipTest('Pinned Crew ZIP is not staged')
  with zipfile.ZipFile(archive) as source:
   path=next(n for n in source.namelist() if n.endswith('/lib/resources/lib/modules/sources.py'))
   tree=ast.parse(source.read(path).decode('utf-8-sig'))
  imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
  imports+=[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
  self.assertFalse(any('adult_sites' in name or 'resolveurl.xxx' in name for name in imports))

if __name__=='__main__':unittest.main()
