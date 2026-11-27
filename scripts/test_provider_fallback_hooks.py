"""Actual picker/download/season and conservatively patched Umbrella fallback boundaries.

Umbrella method anchors inspected at public upstream commit f53e04a100e97e8bdcafec06c47af2539df5e7a0,
omega/plugin.video.umbrella/resources/lib/modules/sources.py. Small fixture methods retain those call signatures
and real no-results/cancel branches; unsupported source versions are left unchanged.
"""
import importlib.util,json,sys,tempfile,types,unittest,urllib.parse
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path[:0]=[str(LIB),str(ROOT/'migration/bundled-bootstrap')]
import provider_fallback as pf,provider_fallback_hooks as hooks,source_match,season_sources,episode_watch,elementum_download,umbrella_picker
spec=importlib.util.spec_from_file_location('hooks_actual_deck',ROOT/'migration/deck-picker/deck_picker.py');deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
class Home:
 def __init__(self):self.p={}
 def getProperty(self,k):return self.p.get(k,'')
 def setProperty(self,k,v):self.p[k]=v
 def clearProperty(self,k):self.p.pop(k,None)
def candidate(provider='jacktook',quality='1080p',name='Film.2020.1080p.WEB-DL.H264'):
 return {'provider':provider,'name':name,'quality':quality,'size':2,'seeders':30,'url':'https://video.example.test/source.mp4','resolver':{'id':provider},'_id':provider}
def line(name,q='1080p',seeds=30):return '%s (%d/0) [2.0 GB] WEB-DL H264 - Primary\n%s'%(q,seeds,name)
class Hooks(unittest.TestCase):
 def setUp(self):
  self.home=Home();self.exp=source_match.expected('movie',['Film'],year=2020,tmdb='1')
  self.xbmc=types.SimpleNamespace(Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:False),Player=Mock(),log=Mock(),LOGINFO=1)
  modules={'xbmc':self.xbmc,'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:str(LIB)),
           'kodi_six':types.SimpleNamespace(xbmc=self.xbmc,xbmcgui=types.SimpleNamespace(Window=lambda i:self.home)),
           'xbmcgui':types.SimpleNamespace(Window=lambda i:self.home)}
  self.mods=patch.dict(sys.modules,modules);self.mods.start();self.addCleanup(self.mods.stop)
  self.h=patch.object(deck,'_home',return_value=self.home);self.h.start();self.addCleanup(self.h.stop)
  self.loader=patch.object(umbrella_picker,'load',return_value=deck);self.loader.start();self.addCleanup(self.loader.stop)
  self.sm=patch.object(deck,'_matcher',return_value=source_match);self.sm.start();self.addCleanup(self.sm.stop)
  self.pick=patch.object(deck,'choose_source',return_value=0);self.pick.start();self.addCleanup(self.pick.stop)
  self.profile=types.SimpleNamespace(_home=lambda:self.home,parse_all=deck.parse_all,is_bad=deck.is_bad,below_quality=deck.below_quality,run=Mock(return_value=0))
 def test_primary_success_and_primary_picker_cancel_never_search_backups(self):
  with patch.object(pf,'search') as search:
   self.assertEqual(deck.run('Film',[line('Film.2020.1080p.WEB-DL.H264')],expect=self.exp),0);search.assert_not_called()
   with patch.object(deck,'choose_source',return_value=-1):self.assertEqual(deck.run('Film',[line('Film.2020.1080p.WEB-DL.H264')],expect=self.exp),-1)
   search.assert_not_called()
 def test_empty_primary_uses_existing_picker_and_resolves_selected_origin(self):
  found=candidate()
  with patch.object(pf,'search',return_value=[found]) as search,patch.object(pf,'resolve',return_value=found['url']) as resolve:
   self.assertEqual(deck.run('Film',[],expect=self.exp,mode='stream'),-1)
  self.assertEqual(search.call_count,1);self.assertEqual(resolve.call_args.args[0],found)
  self.xbmc.Player.return_value.play.assert_called_once_with(found['url'])
 def test_wrong_title_primary_is_not_exposed_as_a_foreign_source(self):
  found=candidate()
  with patch.object(pf,'search',return_value=[found]),patch.object(pf,'resolve',return_value=found['url']):
   self.assertEqual(deck.run('Film',[line('Another.Film.2020.1080p')],expect=self.exp,mode='stream'),-1)
  self.xbmc.Player.return_value.play.assert_called_once_with(found['url'])
 def test_cam_or_too_small_strict_backup_advances_to_next_provider_without_picker_cancel(self):
  bad=candidate(name='Film.2020.1080p.CAM');good=candidate('pov')
  with patch.object(pf,'search',side_effect=[[bad],[good]]) as search,patch.object(pf,'resolve',return_value=good['url']):
   result=hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:False)
  self.assertEqual(result['candidate'],good);self.assertEqual(search.call_args_list[1].kwargs['exclude'],('jacktook',));self.profile.run.assert_called_once()
  tiny=candidate();tiny['size']=.01;self.profile.run.reset_mock()
  with patch.object(pf,'search',side_effect=[[tiny],[good]]) as search,patch.object(pf,'resolve',return_value=good['url']):
   result=hooks._resolved(self.profile,self.exp,'Film','download',auto={'profile':{'strict_quality':True,'quality':'1080p','runtime':120}},cancel=lambda:False)
  self.assertEqual(result['candidate'],good);self.assertEqual(search.call_count,2)
 def test_policy_uncertain_playback_stale_generation_and_dedupe(self):
  found=candidate()
  with patch.object(hooks,'playback_uncertain',return_value=True),patch.object(pf,'search') as search:
   self.assertIsNone(hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:False));search.assert_not_called()
  self.home.p[hooks.MANUAL]='first'
  def replaced(*a,**k):self.home.p[hooks.MANUAL]='second';return [found]
  with patch.object(pf,'search',side_effect=replaced),patch.object(pf,'resolve') as resolve:
   with self.assertRaises(pf.Canceled):hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:False)
  resolve.assert_not_called();self.profile.run.assert_not_called()
  a=dict(candidate('jacktook'),torrent_hash='a'*40,seeders=3);b=dict(candidate('jacktook'),name='Film.2020.720p.WEB',torrent_hash='A'*40,seeders=9)
  self.assertEqual(hooks.dedupe([a,b,candidate('pov')]),[b,candidate('pov')])
 def test_episode_failure_goes_to_backup_once_and_healthy_primary_does_no_work(self):
  exp=source_match.expected('episode',['Show'],season=1,episode=2,tmdb='9');ep=candidate(name='Show.S01E02.1080p.WEB-DL.H264')
  with patch.object(pf,'search',return_value=[ep]) as search,patch.object(pf,'resolve',return_value=ep['url']) as resolve:
   result=hooks._resolved(self.profile,exp,'Show','stream',cancel=lambda:False)
  self.assertEqual((search.call_count,resolve.call_count,result['url']),(1,1,ep['url']))
  with patch.object(pf,'search') as search:
   self.assertEqual(deck.run('Show',[line('Show.S01E02.1080p.WEB-DL.H264')],expect=exp),0);search.assert_not_called()
 def test_no_source_and_cancel_are_safe(self):
  with patch.object(pf,'search',return_value=[]):self.assertIsNone(hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:False))
  with patch.object(pf,'search') as search:
   with self.assertRaises(pf.Canceled):hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:True)
   search.assert_not_called()
 def test_primary_strict_quality_miss_searches_backups_before_original_lower_quality_fallback(self):
  exp=source_match.expected('episode',['Show'],tmdb='2',season=1,episode=1)
  auto={'request_id':'Q','until':10**12,'purpose':'queue','target':{'tmdb':'2','season':1,'episode':1},'profile':{'quality':'1080p','strict_quality':True}}
  self.home.setProperty(deck.AUTO_PICK,json.dumps(auto));found=candidate(name='Show.S01E01.1080p.WEB-DL.H264')
  with patch.object(pf,'search',return_value=[found]) as search,patch.object(pf,'resolve',return_value=found['url']),patch.object(pf,'queue_download',return_value=True) as queue:
   self.assertEqual(deck.run('Show',[line('Show.S01E01.720p','720p')],expect=exp),-1)
  self.assertEqual(search.call_count,1);self.assertTrue(queue.called)
  result=json.loads(self.home.getProperty(deck.AUTO_RESULT));self.assertEqual(result['quality'],'1080p');self.assertEqual(result['request_id'],'Q')
 def test_verified_anime_mapping_keeps_original_auto_request_coordinates(self):
  exp=source_match.expected('episode',['Example Show'],tmdb='100',season=2,episode=2)
  auto={'request_id':'anime','until':10**12,'purpose':'queue','target':{'tmdb':'100','season':2,'episode':2},
        'profile':{'quality':'1080p','strict_quality':True}}
  self.home.setProperty(deck.AUTO_PICK,json.dumps(auto))
  request=pf.request_from_expected(exp,'queue',auto['profile'])
  mapping={'source':'otaku-db+tmdb-episode+ani.zip','verified':True,'tmdb':'100','season':2,'episode':2,
           'mal_id':123,'title':'Canonical Anime','absolute_episode':14,'anime_season':1}
  source=candidate('otaku',name='Canonical.Anime.-.014.1080p.WEB-DL.H264.mkv')
  source.update(cached=True,resolver={'request':dict(request,anime=True,anime_mapping=mapping)})
  self.assertTrue(pf.verified([source],request,'otaku'))
  with patch.object(pf,'search',return_value=[source]),patch.object(pf,'resolve',return_value=source['url']) as resolve:
   selected=hooks._resolved(deck,exp,'Example Show','download',auto=auto,cancel=lambda:False)
  self.assertEqual(selected['candidate'],source)
  self.assertEqual(selected['request']['season'],2);self.assertEqual(selected['request']['episode'],2)
  self.assertEqual(resolve.call_args.args[1]['episode'],2)
  result=json.loads(self.home.getProperty(deck.AUTO_RESULT))
  self.assertTrue(result['found']);self.assertEqual(result['request_id'],'anime');self.assertEqual(result['episode'],2)
  self.assertEqual(deck._CONTEXT['exp']['season'],2);self.assertEqual(deck._CONTEXT['exp']['episode'],2)
 def test_scan_uses_automatic_picker_quality_result_without_resolve_or_queue(self):
  exp=source_match.expected('episode',['Show'],tmdb='2',season=1,episode=1)
  auto={'request_id':'scan','until':10**12,'purpose':'scan','target':{'tmdb':'2','season':1,'episode':1},'profile':{}}
  self.home.setProperty(deck.AUTO_PICK,json.dumps(auto));found=candidate(name='Show.S01E01.1080p.WEB-DL.H264')
  with patch.object(pf,'search',return_value=[found]),patch.object(pf,'resolve') as resolve,patch.object(pf,'queue_download') as queue:
   self.assertEqual(deck.run('Show',[],expect=exp),-1)
  result=json.loads(self.home.getProperty(deck.AUTO_RESULT));self.assertEqual(result['qualities'],['1080p']);resolve.assert_not_called();queue.assert_not_called()
 def test_backup_picker_or_transport_cancel_stops_chain_without_resolve(self):
  self.profile.run.return_value=-1
  with patch.object(pf,'search',return_value=[candidate()]) as search,patch.object(pf,'resolve') as resolve:
   self.assertTrue(hooks.deck_fallback(self.profile,self.exp,'Film',cancel=lambda:False))
  self.assertEqual(search.call_count,1);resolve.assert_not_called()
  with patch.object(pf,'search') as search:
   self.assertTrue(hooks.deck_fallback(self.profile,self.exp,'Film',cancel=lambda:True));search.assert_not_called()
 def test_failed_resolver_advances_origin_and_never_passes_payload_to_primary_resolver(self):
  first=candidate();second=candidate('pov')
  with patch.object(pf,'search',side_effect=[[first],[second]]) as search,patch.object(pf,'resolve',side_effect=[RuntimeError('expired'),second['url']]):
   result=hooks._resolved(self.profile,self.exp,'Film','stream',cancel=lambda:False)
  self.assertEqual(result['candidate'],second);self.assertEqual(search.call_args.kwargs['exclude'],('jacktook',))
 def test_stream_magnet_never_reaches_download_interception_or_player(self):
  magnet='magnet:?xt=urn:btih:'+'a'*40
  import debrid_token,debrid_account   # a working AllDebrid key (with no key, or a failing service, a Stream goes to peers instead: test_direct_stream)
  with patch.object(debrid_token,'has',return_value=True),patch.object(debrid_account,'is_unavailable',return_value=False),patch.object(pf,'queue_download') as queue,self.assertRaises(ValueError):
   hooks.dispatch({'url':magnet,'request':{'purpose':'stream','tmdb':'2','season':1,'episode':3}})
  self.xbmc.Player.return_value.play.assert_not_called();queue.assert_not_called()
 def test_http_download_calls_durable_queue_and_never_starts_live_player(self):
  selected={'candidate':candidate(),'url':candidate()['url'],'request':{'purpose':'queue'}}
  with patch.object(pf,'queue_download',return_value=True) as queue:self.assertTrue(hooks.dispatch(selected,{'request_id':'queue'}))
  self.assertEqual(queue.call_args.args[:2],(selected['candidate'],selected['url']));self.xbmc.Player.assert_not_called()
 def test_primary_download_redirect_success_does_not_search_again(self):
  with patch.object(hooks,'deck_fallback') as fallback:
   reached=hooks.download_follow('plugin://plugin.video.elementum/movie/1/links',self.exp,lambda url:'http://127.0.0.1:9220/play?uri=chosen')
  self.assertIn('/play?',reached);fallback.assert_not_called();self.assertFalse(self.home.p)
 def test_dismissed_primary_picker_cannot_start_backup_after_follow_returns(self):
  def primary(url):
   self.assertEqual(deck._selection_result(-1),-1)
   return 'http://127.0.0.1:9220/movie/1/links'
  with patch.object(hooks,'deck_fallback') as fallback,self.assertRaises(elementum_download.Canceled):
   hooks.download_follow('plugin://plugin.video.elementum/movie/1/links',self.exp,primary)
  fallback.assert_not_called();self.assertFalse(self.home.p)
 def test_offline_download_searches_backups_but_primary_cancel_does_not(self):
  def offline(url):raise OSError('primary offline')
  with patch.object(hooks,'deck_fallback',return_value=True) as fallback:hooks.download_follow('plugin://plugin.video.elementum/movie/1/links',self.exp,offline)
  fallback.assert_called_once();self.assertFalse(self.home.p)
  def canceled(url):raise elementum_download.Canceled('cancel')
  with patch.object(hooks,'deck_fallback') as fallback,self.assertRaises(elementum_download.Canceled):hooks.download_follow('x',self.exp,canceled)
  fallback.assert_not_called()
 def test_umbrella_empty_returns_origin_resolved_direct_action_without_native_source_dict(self):
  found=candidate();self.profile.run.return_value=0
  with patch.object(pf,'search',return_value=[found]),patch.object(pf,'resolve',return_value=found['url']):
   handled,url=hooks.umbrella_selection({'title':'Film'},self.profile,self.exp)
  self.assertTrue(handled);self.assertEqual(url,found['url'])

# These branches and method signatures are the actual inspected upstream entry points, not substitute hook APIs.
UMBRELLA='''class Sources:
 def play(self,title,year,imdb,tmdb,tvdb,season,episode,tvshowtitle,premiered,meta,select,rescrape=None):
  self.meta=meta
  if not self.prem_providers:
   return 'no-provider'
  return self.errorForSources()
 def errorForSources(self,title=None,year=None,imdb=None,tmdb=None,tvdb=None,season=None,episode=None,tvshowtitle=None,premiered=None):
  return 'empty'
 def sourceSelect(self,title,items,uncached_items,meta):
  return items
 def sourcesAutoPlay(self,items):
  if progressDialog.iscanceled(): return 'cancel'
  return 'resolved'
 def getSources_dialog(self,*args):
  if progressDialog.iscanceled():
   return 'cancel'
  return []
'''
class UmbrellaPatch(unittest.TestCase):
 def test_actual_method_hooks_compile_once_and_cancellation_mark_is_conditional(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'sources.py';path.write_text(UMBRELLA)
   self.assertTrue(hooks.install(path));saved=path.read_text();self.assertFalse(hooks.install(path));self.assertEqual(saved,path.read_text())
   namespace={'progressDialog':types.SimpleNamespace(iscanceled=lambda:False)};exec(compile(saved,str(path),'exec'),namespace)
   calls=[];namespace['_kodi_provider_fallback']=lambda owner:calls.append(owner) or True
   obj=namespace['Sources']();obj.prem_providers=[]
   self.assertIsNone(obj.play('Film',2020,'tt1','1',None,None,None,None,None,{},'0'));self.assertEqual(len(calls),1)
   self.assertFalse(obj._kodi_provider_cancelled);self.assertEqual(obj.sourcesAutoPlay([]),'resolved');self.assertFalse(obj._kodi_provider_cancelled)
   namespace['progressDialog'].iscanceled=lambda:True;self.assertEqual(obj.sourcesAutoPlay([]),'cancel');self.assertTrue(obj._kodi_provider_cancelled)
   self.assertEqual(obj._kodi_provider_request['title'],'Film')
 def test_unsupported_umbrella_structure_is_not_rewritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'sources.py';path.write_text('class Different:\n def play(self):pass\n')
   before=path.read_bytes();self.assertFalse(hooks.install(path));self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
