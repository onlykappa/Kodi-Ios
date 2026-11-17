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
 def test_reject_other_addon_or_network_url(self):
  for value in ['https://example.invalid','plugin://other.addon/play','plugin://user:pass@plugin.video.the-loop/play']:
   self.assertFalse(lr.valid_route(value))
if __name__=='__main__':unittest.main()
