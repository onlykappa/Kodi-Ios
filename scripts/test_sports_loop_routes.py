import sys,json,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_loop_routes as lr
import sports_jet as sj
class Tests(unittest.TestCase):
 def test_exact_loop_route_handoff_never_imports_jet(self):
  route='plugin://plugin.video.the-loop/play/fixture';calls=[]
  with patch.object(sj,'import_jet',side_effect=AssertionError('direct Jet import')),patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda value:calls.append(value))),'xbmcgui':NS()}):
   self.assertTrue(sj.play_one(json.dumps({'e':lr.NAME,'l':{'address':route}}),lambda s:None))
  self.assertEqual(calls,[route])
 def test_cards_keep_loop_routes_and_reject_ambiguous_matches(self):
  game={'away':{'name':'Alpha'},'home':{'name':'Beta'},'league_name':'NBA','state':'live','start':1000}
  route='plugin://plugin.video.the-loop/play/game-a'
  entries=[{'label':'[COLORblue]NBA[/COLOR] |[B] Beta vs Alpha --- CH 1[/B]','file':route,'filetype':'file'}, {'label':'Alpha vs Different','file':'plugin://plugin.video.the-loop/play/wrong','filetype':'file'}]
  source=lr.LoopSource('FawaNews','plugin://plugin.video.the-loop/list/fawa',[game],lambda path:entries)
  items=source.get_items();self.assertEqual(len(items),1)
  record=sj.records(items[0],source.name,1001)[0]
  self.assertEqual(json.loads(record['play'])['e'],lr.NAME);self.assertEqual(json.loads(record['play'])['l']['address'],route)
  self.assertIsNone(lr.match_game('Alpha vs Beta',[game,dict(game)]))
 def test_discovery_retains_sources_but_skips_replay_and_account_menus(self):
  root='plugin://plugin.video.the-loop/';zone=root+'zone';route=root+'fawa'
  entries={root:[{'label':'Scraper Zone','file':zone,'filetype':'directory'}],zone:[{'label':'FawaNews','file':route,'filetype':'directory'}, {'label':'HomeIPTV','file':root+'iptv','filetype':'directory'}, {'label':'Full Replays','file':root+'replay','filetype':'directory'}, {'label':'CollegeVideo','file':root+'old-games','filetype':'directory'}, {'label':'Foxxy','file':root+'channels','filetype':'directory'}]}
  found=lr.discover(read=lambda path:entries[path],schedule=[])
  self.assertEqual([x.name for x in found],['Loop FawaNews'])
 def test_the_route_list_is_kept_for_hours_and_only_the_best_sites_are_read(self):
  import tempfile,os
  root='plugin://plugin.video.the-loop/';zone=root+'zone'
  names=['FawaNews','LiveFeeds','ReedStreams']+['Other%d'%n for n in range(30)]
  entries={root:[{'label':'Scraper Zone','file':zone,'filetype':'directory'}],zone:[{'label':n,'file':root+'r%d'%i,'filetype':'directory'} for i,n in enumerate(names)]}
  calls=[]
  def read(path):calls.append(path);return entries[path]
  with tempfile.TemporaryDirectory() as d:
   cache=os.path.join(d,'loop-routes.json')
   first=lr.discover(read=read,schedule=[],cache=cache,now=1000.0)
   self.assertEqual([x.name for x in first][:3],['Loop FawaNews','Loop LiveFeeds','Loop ReedStreams']);self.assertEqual(len(first),lr.MAX_ROUTES)
   self.assertEqual(len(calls),2)
   again=lr.discover(read=read,schedule=[],cache=cache,now=1000.0+3600)
   self.assertEqual(len(calls),2,'the second search reads nothing from The Loop to find its routes');self.assertEqual([x.name for x in again],[x.name for x in first])
   lr.discover(read=read,schedule=[],cache=cache,now=1000.0+lr.ROUTES_TTL+1)
   self.assertEqual(len(calls),4,'after the keeping time the list is read again')
   self.assertNotIn('token',open(cache).read())
 def test_loop_links_carry_the_game_so_the_opening_card_has_teams(self):
  import sports_opening
  game={'league':'NFL','start':1000,'state':'live','away':{'name':'Kansas City Chiefs','code':'KC','crest':'c1'},'home':{'name':'Buffalo Bills','code':'BUF','crest':'c2'}}
  link=lr.LoopLink('plugin://plugin.video.the-loop/play_video/x',game)
  src={'play':json.dumps({'e':lr.NAME,'l':link.to_dict()})}
  self.assertEqual(sports_opening.matchup(src),'Kansas City Chiefs\nBuffalo Bills');self.assertEqual(sports_opening.game_of(src)['state'],'live')
 def test_real_loop_discovery_feeds_provider_without_direct_jet(self):
  import sports_fawa
  game={'away':{'name':'Alpha'},'home':{'name':'Beta'},'league_name':'NBA','state':'live','start':1000}
  route='plugin://plugin.video.the-loop/play/fixture'
  source=lr.LoopSource('FawaNews','plugin://plugin.video.the-loop/list',[game],lambda path:[{'label':'Alpha vs Beta','file':route,'filetype':'file'}])
  with patch.object(sj,'_folder',side_effect=lambda name:'/fixture/loop' if name==lr.ADDON else None),patch.object(lr,'discover',return_value=[source]),patch.object(sj,'import_jet',side_effect=AssertionError('direct Jet called')),patch.object(sports_fawa.FawaNews,'get_items',return_value=[]):
   provider=sj.JetProvider(clock=lambda:1001);self.assertTrue(provider._start().wait(2))
   self.assertEqual(provider.records[source.name][0]['addon'],'Loop FawaNews')
   self.assertEqual(json.loads(provider.records[source.name][0]['play'])['e'],lr.NAME)
 def test_native_plugin_starts_are_bounded_to_two(self):
  import threading,time,sports_fawa
  state={'active':0,'peak':0};lock=threading.Lock()
  def items():
   with lock:state['active']+=1;state['peak']=max(state['peak'],state['active'])
   time.sleep(.03)
   with lock:state['active']-=1
   return []
  sources=[NS(name='Loop fixture %d'%n,get_items=items) for n in range(8)]
  with patch.object(sj,'_folder',side_effect=lambda name:'/fixture/loop' if name==lr.ADDON else None),patch.object(lr,'discover',return_value=sources),patch.object(sports_fawa.FawaNews,'get_items',return_value=[]):
   provider=sj.JetProvider();self.assertTrue(provider._start().wait(2))
  self.assertEqual(state['peak'],2)
 def test_startup_prepares_proxy_without_listing_menus(self):
  logs=[]
  with patch.object(lr,'prepare_proxy',return_value=True) as prepare,patch.object(lr,'listing',side_effect=AssertionError('startup opened menu')):
   self.assertTrue(lr.warmup_proxy(lambda seconds:False,logs.append))
  prepare.assert_called_once_with();self.assertIn('shared proxy ready',logs[0])
 def test_startup_shutdown_does_not_patch_files(self):
  with patch.object(lr,'prepare_proxy') as prepare:
   self.assertFalse(lr.warmup_proxy(lambda seconds:True,lambda line:None))
  prepare.assert_not_called()
 def test_startup_failure_is_quiet_and_does_not_log_urls(self):
  logs=[]
  with patch.object(lr,'prepare_proxy',side_effect=OSError('https://private.invalid/?token=fixture')):
   self.assertFalse(lr.warmup_proxy(lambda seconds:False,logs.append))
  self.assertIn('OSError',logs[0]);self.assertNotIn('private.invalid',' '.join(logs))
 def test_reject_other_addon_or_network_url(self):
  for value in ['https://example.invalid','plugin://other.addon/play','plugin://user:pass@plugin.video.the-loop/play']:
   self.assertFalse(lr.valid_route(value))
if __name__=='__main__':unittest.main()
