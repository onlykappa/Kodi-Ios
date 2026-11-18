"""Crew catalog matching, native ownership, isolation and priority regressions."""
import json, sys, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_crew_routes as crew
import sports_native_routes as native
import sports_loop_routes as loop
import sports_loop_router as router
import sports_jet as jet
import sports_crew_context as context

ROOT = 'plugin://plugin.video.thecrew/'
GAME = {'away':{'name':'Alpha'}, 'home':{'name':'Beta'}, 'league_name':'NBA', 'state':'live', 'start':1000}
def entry(label, route, folder=True):
 return {'label':label, 'file':ROOT+route, 'filetype':'directory' if folder else 'file'}
def source(name='Crew NBA', quality='', route='?action=play&url=fixture'):
 return {'addon':name, 'quality':quality, 'play':json.dumps({'e':crew.NAME, 'l':{'address':ROOT+route}})}

class Tests(unittest.TestCase):
 def test_failed_folder_yields_before_another_folder_is_read(self):
  calls=[]
  def read(route):
   calls.append(route)
   if route.endswith('broken'): raise OSError('unavailable')
   return [entry('site','broken'),entry('site','next')]
  batches=crew.CrewSource('NBA',ROOT+'league',[GAME],read).batches()
  next(batches)
  next(batches)
  self.assertEqual(calls,[ROOT+'league',ROOT+'broken'])
  next(batches)
  self.assertEqual(calls[-1],ROOT+'next')

 def test_round_robin_refreshes_stale_provider_folders_after_another_league(self):
  from urllib.parse import parse_qs,urlsplit
  serial={'generation':0,'active':None};calls=[]
  def read(route):
   q=parse_qs(urlsplit(route).query);action=q.get('action',[''])[0];calls.append(action)
   if action in ('nba','nhl'):
    serial['generation']+=1;serial['active']=action
    return [entry(action.upper()+' LIVE (CS)','?action=xdirectory&url='+action+str(serial['generation']))]
   token=q.get('url',[''])[0]
   if token!=serial['active']+str(serial['generation']):raise RuntimeError('stale regex cache')
   return [entry('Alpha vs Beta','?action=play&url='+token,False)]
  live_nba=dict(GAME,league='NBA');live_nhl=dict(GAME,league='NHL',league_name='NHL')
  def roots(path):return [entry('NBA','?action=nba'),entry('NHL','?action=nhl')]
  categories=crew.discover(roots,schedule=[live_nba,live_nhl])
  for ext in categories:ext.read=read
  iters=[iter(ext.batches()) for ext in categories]
  self.assertTrue(all(next(it)==[] for it in iters))
  self.assertEqual([len(next(it)) for it in iters],[1,1])
 def test_refreshing_discovery_ancestors_rejects_ambiguous_folder(self):
  root=ROOT+'?action=nba';old=ROOT+'?action=xdirectory&url=old';calls=[]
  state={'owner':'another'}
  def read(route):
   calls.append(route)
   if len(calls)==1:return [entry('NBA LIVE (CS)','?action=xdirectory&url=old')]
   return [entry('NBA LIVE (CS)','?action=xdirectory&url=one'),entry('NBA LIVE (CS)','?action=xdirectory&url=two')]
  ext=crew.CrewSource('NBA',root,[GAME],read,cache_state=state);b=ext.batches();next(b)
  state['owner']='another';self.assertEqual(next(b),[])
  self.assertEqual(calls,[root,root]);self.assertNotIn(old,calls)
 def test_cancel_during_discovery_ancestor_refresh_stops_before_child(self):
  props={context.SESSION:'open:fixture'};home=NS(getProperty=lambda k:props.get(k,''));calls=[]
  root=ROOT+'?action=nba';state={'owner':'another'}
  def read(route):
   calls.append(route)
   if len(calls)==2:props[context.SESSION]='closed:fixture'
   return [entry('NBA LIVE (CS)','?action=xdirectory&url=provider')]
  with patch.object(crew,'_home',return_value=home):
   b=crew.CrewSource('NBA',root,[GAME],read,session='open:fixture',cache_state=state).batches();next(b);state['owner']='another';next(b)
  self.assertEqual(calls,[root,root])

 def test_crew_categories_rotate_and_publish_before_first_finishes(self):
  order=[]; snapshots=[]
  class Batched:
   def __init__(self,name): self.name=name
   def batches(self):
    order.append(self.name+' first');yield []
    order.append(self.name+' second');yield []
  with patch.object(jet,'_folder',return_value='/installed'),patch.object(crew,'schedule',return_value=[]),patch.object(crew,'discover',return_value=[Batched('NHL'),Batched('NBA')]):
   provider=jet.JetProvider(clock=lambda:1001,publish=lambda value:snapshots.append(value))
   self.assertTrue(provider._start().wait(2))
  self.assertEqual(order,['NHL first','NBA first','NHL second','NBA second'])
  self.assertTrue(any(not value['done'] for value in snapshots))
  self.assertTrue(snapshots[-1]['done'])

 def test_discover_only_actual_sports_menu_routes(self):
  entries=[entry('NBA','?action=nba'),entry('Replay','?action=sreplays'),entry('Movies','?action=movies'),entry('Live sites','?action=fullsites'),entry('NBA duplicate','?action=nba')]
  found=crew.discover(lambda route:entries,schedule=[GAME])
  self.assertEqual([x.name for x in found],['Crew NBA','Crew Live sites'])
 def test_upcoming_only_does_not_open_crew(self):
  upcoming=dict(GAME,state='upcoming')
  self.assertEqual(crew.discover(lambda route:self.fail('Crew should not be scanned'),schedule=[upcoming]),[])
  self.assertEqual(crew.discover(lambda route:self.fail('Crew should not be scanned'),schedule=[]),[])
 def test_discovery_uses_only_live_leagues_and_live_games(self):
  nba=dict(GAME,league='NBA',state='live')
  later=dict(GAME,league='NHL',league_name='NHL',state='upcoming')
  entries=[entry('NBA','?action=nba'),entry('NHL','?action=nhl'),entry('Live sites','?action=fullsites')]
  found=crew.discover(lambda route:entries,schedule=[nba,later])
  self.assertEqual([x.name for x in found],['Crew NBA','Crew Live sites'])
  self.assertTrue(all(x.games==[nba] for x in found))
 def test_cached_upcoming_rechecks_espn_when_stale(self):
  scheduled=dict(GAME,id='fixture',league='NBA',sport='Basketball',state='upcoming',start=2000,sources=[])
  data=json.dumps({'at':1000,'done':True,'records':[],'schedule':[scheduled]})
  launched=[];properties={jet.DATA:data}
  home=NS(getProperty=lambda key:properties.get(key,''),setProperty=lambda key,value:properties.__setitem__(key,value))
  provider=jet.JetProvider(remote=True,clock=lambda:1046,window=home,wait=.01,launch=lambda *args:launched.append(args))
  self.assertEqual(len(provider.upcoming_games()),1)
  self.assertEqual(launched,[('sports_jet_run',)])
 def test_nested_game_keeps_exact_route_and_never_uses_unmatched_channels(self):
  routes={ROOT+'league':[entry('Alpha vs Beta','game'),entry('Sports TV','channel',False)],ROOT+'game':[entry('Source 1','?action=play&url=fixture%2Fexact',False)]}
  ext=crew.CrewSource('NBA',ROOT+'league',[GAME],lambda route:routes[route])
  records=jet.records(ext.get_items()[0],ext.name,1001)
  self.assertEqual(json.loads(records[0]['play'])['e'],crew.NAME)
  self.assertEqual(json.loads(records[0]['play'])['l']['address'],ROOT+'?action=play&url=fixture%2Fexact')
 def test_ambiguous_and_wrong_child_matches_do_not_inherit_parent(self):
  routes={ROOT+'league':[entry('Alpha vs Beta','game')],ROOT+'game':[entry('Alpha vs Other','wrong',False),entry('Beta vs Alpha','valid',False)]}
  ext=crew.CrewSource('NBA',ROOT+'league',[GAME],lambda route:routes[route])
  self.assertEqual(len(ext.get_items()),1)
  ext.games=[GAME,dict(GAME)];self.assertEqual(ext.get_items(),[])
 def test_cycles_failures_and_replay_folders_are_bounded(self):
  calls=[]
  def read(route):
   calls.append(route)
   if route.endswith('broken'):raise OSError('private URL omitted')
   return [entry('site','loop'),entry('replay','replays'),entry('site','broken'),entry('Alpha vs Beta','video',False)]
  items=crew.CrewSource('NBA',ROOT+'league',[GAME],read).get_items()
  self.assertEqual(len(items),1);self.assertLessEqual(len(calls),crew.MAX_FOLDERS)
  self.assertFalse(any(x.endswith('replays') for x in calls))
 def test_crew_scan_timing_omits_routes_and_game_names(self):
  with patch.object(jet,'log') as log:
   self.assertEqual(crew.CrewSource('NBA',ROOT+'private-route',[GAME],lambda path:[]).get_items(),[])
  message=log.call_args.args[0]
  self.assertRegex(message,r'1 folders, 0 unavailable, 0 matched streams in [0-9.]+s')
  self.assertNotIn('private-route',message)
  self.assertNotIn('Alpha',message)
 def test_crew_primary_and_native_queue_retains_loop_and_independent_fallbacks(self):
  other={'addon':'Independent','quality':'','play':'fallback'}
  backup={'addon':'Loop FawaNews','quality':'4K','play':json.dumps({'e':loop.NAME,'l':{'address':'plugin://plugin.video.the-loop/play/fixture'}})}
  selected=router.automatic_source([backup,other,source()])
  self.assertEqual(selected['native_queue'][0]['addon'],'Crew NBA')
  self.assertEqual(len(selected['native_queue']),2);self.assertEqual(selected['alts'],['fallback'])
 def test_route_type_cannot_impersonate_another_addon(self):
  wrong=source();value=json.loads(wrong['play']);value['e']=loop.NAME;wrong['play']=json.dumps(value)
  self.assertIsNone(router.native_route(wrong))
  for route in ['https://invalid.test/','plugin://user:pass@plugin.video.thecrew/play','plugin://other/play']:
   self.assertFalse(crew.valid_route(route))
 def test_crew_play_uses_exact_route_without_proxy_or_protected_imports(self):
  calls=[];logs=[];address=ROOT+'?action=play&url=fixture%2Fexact'
  with patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda route:calls.append(route))),'xbmcgui':NS()}),patch.object(loop,'prepare_proxy',side_effect=AssertionError('Loop touched')),patch.object(jet,'import_jet',side_effect=AssertionError('Jet touched')):
   self.assertTrue(jet.play_one(source(route='?action=play&url=fixture%2Fexact')['play'],logs.append))
  self.assertEqual(calls,[address]);self.assertIn('The Crew',logs[0])
 def test_crew_queue_preparation_does_not_touch_loop(self):
  with patch.object(loop,'prepare_proxy',side_effect=AssertionError('Loop touched')):
   self.assertFalse(native.prepare_proxy([ROOT+'play']))
 def test_installed_crew_discovery_never_opens_loop_or_direct_jet(self):
  import sports_fawa
  ext=crew.CrewSource('NBA',ROOT+'league',[GAME],lambda path:[entry('Alpha vs Beta','play',False)])
  with patch.object(jet,'log') as log,patch.object(jet,'_folder',return_value='/fixture/installed'),patch.object(crew,'discover',return_value=[ext]),patch.object(crew,'schedule',return_value=[dict(GAME,id='fixture',league='NBA',sport='Basketball',sources=[])]),patch.object(loop,'discover',side_effect=AssertionError('Loop touched')),patch.object(jet,'import_jet',side_effect=AssertionError('Jet touched')),patch.object(sports_fawa.FawaNews,'get_items',return_value=[]):
   provider=jet.JetProvider(clock=lambda:1001)
   self.assertTrue(provider._start().wait(2));self.assertEqual(len(provider.records['Crew NBA']),1)
   messages=[call.args[0] for call in log.call_args_list]
   self.assertTrue(any('ESPN schedule ready in ' in s and '(1 live, 0 upcoming)' in s for s in messages))
 def test_espn_keeps_games_without_sources_and_owns_status_scores_and_ids(self):
  schedule=dict(GAME,id='espn:NBA:fixture',league='NBA',sport='Basketball',sources=[],clock='Q2 03:00',left=180,
                away=dict(GAME['away'],score=41),home=dict(GAME['home'],score=40))
  provider=jet.JetProvider(clock=lambda:1001);provider.schedule=[schedule]
  empty=provider._games([])['live'][0]
  self.assertEqual(empty['id'],'espn:NBA:fixture');self.assertEqual(empty['sources'],[])
  ext=crew.CrewSource('NBA',ROOT+'league',[schedule],lambda path:[entry('Alpha vs Beta','play',False)])
  records=jet.records(ext.get_items()[0],ext.name,1001)
  game=provider._games(records)['live'][0]
  self.assertEqual(game['away']['score'],41);self.assertEqual(game['clock'],'Q2 03:00')
  self.assertEqual(game['id'],schedule['id']);self.assertEqual(len(game['sources']),1)
  provider.schedule=[dict(schedule,state='upcoming',start=2000)]
  result=provider._games(records)
  self.assertEqual(result['live'],[]);self.assertEqual(result['upcoming'][0]['state'],'upcoming')
 def test_unmatched_provider_game_never_enters_schedule(self):
  provider=jet.JetProvider(clock=lambda:1001);provider.schedule=[]
  ext=crew.CrewSource('NBA',ROOT+'league',[GAME],lambda path:[entry('Alpha vs Beta','play',False)])
  self.assertEqual(provider._games(jet.records(ext.get_items()[0],ext.name,1001))['live'],[])
 def test_remote_schedule_is_ready_while_sources_are_loading_and_can_be_empty(self):
  for schedule in [[],[dict(GAME,id='espn:NBA:fixture',league='NBA',sport='Basketball',sources=[])]]:
   data=json.dumps({'at':1001,'done':False,'records':[],'schedule':schedule})
   home=NS(getProperty=lambda key:data if key==jet.DATA else '1001',setProperty=lambda *args:None)
   provider=jet.JetProvider(remote=True,clock=lambda:1001,window=home,wait=.01)
   result=provider._remote_load(False)
   self.assertEqual(len(result['live']),len(schedule))
 def test_american_schedule_only_fetches_selected_leagues(self):
  import sports_espn
  seen=[]
  provider=sports_espn.EspnProvider(fetch=lambda url:seen.append(url) or {'events':[]},leagues=crew.AMERICAN_LEAGUES)
  provider._load()
  self.assertEqual({entry[0] for entry in provider.league_defs},crew.AMERICAN_LEAGUES)
  self.assertFalse(any('/soccer/eng.' in url or '/soccer/esp.' in url for url in seen))
 def test_aliases_are_espn_supplied_and_ambiguous_pairs_are_rejected(self):
  game=dict(GAME,away={'name':'Alpha City','aliases':['Alpha']},home={'name':'Beta Town','aliases':['Beta']})
  self.assertIs(crew.match_game('Alpha vs Beta',[game]),game)
  self.assertIsNone(crew.match_game('Alpha vs Beta',[game,dict(game)]))
  self.assertIsNone(crew.match_game('Alpha vs Other',[game]))
 def test_observed_crew_live_basketball_titles_match_espn(self):
  game=dict(GAME,away={'name':'Notre Dame Fighting Irish','aliases':['Notre Dame']},home={'name':'Florida Gators','aliases':['Florida']})
  for title in ['NCAA Men LIVE Florida vs Notre Dame','Florida vs Notre Dame 4:51 PM ET','19:48 - 2nd Half Florida Gators vs Notre Dame Fighting Irish']:
   with self.subTest(title=title):
    self.assertIs(crew.match_game(title,[game]),game)
    self.assertIsNone(crew.match_game(title,[game,dict(game)]))
  self.assertIsNone(crew.match_game('South Florida vs Notre Dame 4:51 PM ET',[game]))
 def test_observed_titles_produce_sources_only_for_the_unique_espn_game(self):
  game=dict(GAME,away={'name':'Notre Dame Fighting Irish','aliases':['Notre Dame']},home={'name':'Florida Gators','aliases':['Florida']})
  routes={ROOT+'league':[entry('NCAA Men LIVE Florida vs Notre Dame','game'),entry('Florida vs Notre Dame 4:51 PM ET','direct',False),entry('South Florida vs Notre Dame 4:51 PM ET','wrong',False)],ROOT+'game':[entry('Source 1','nested',False)]}
  ext=crew.CrewSource('NCAAB',ROOT+'league',[game],lambda route:routes[route])
  items=ext.get_items()
  self.assertEqual({item.links[0].address for item in items},{ROOT+'direct',ROOT+'nested'})
  ext.games=[game,dict(game)]
  self.assertEqual(ext.get_items(),[])
 def test_different_league_or_start_cannot_attach_a_stream(self):
  schedule=dict(GAME,id='fixture',league='NBA',sport='Basketball',sources=[])
  ext=crew.CrewSource('NBA',ROOT+'league',[GAME],lambda path:[entry('Alpha vs Beta','play',False)])
  records=jet.records(ext.get_items()[0],ext.name,1001)
  provider=jet.JetProvider(clock=lambda:1001);provider.schedule=[schedule]
  for wrong in [dict(records[0],league='NHL'),dict(records[0],start=10000)]:
   self.assertEqual(provider._games([wrong])['live'][0]['sources'],[])
 def test_native_crew_scans_are_serial_and_use_no_independent_sources(self):
  import threading,time,sports_fawa
  state={'active':0,'peak':0};lock=threading.Lock()
  def items():
   with lock:state['active']+=1;state['peak']=max(state['peak'],state['active'])
   time.sleep(.01)
   with lock:state['active']-=1
   return []
  sources=[NS(name='Crew fixture %d'%n,get_items=items) for n in range(4)]
  with patch.object(jet,'_folder',return_value='/installed'),patch.object(crew,'schedule',return_value=[]),patch.object(crew,'discover',return_value=sources),patch.object(sports_fawa.FawaNews,'get_items',side_effect=AssertionError('independent called')):
   provider=jet.JetProvider();self.assertTrue(provider._start().wait(2))
  self.assertEqual(state['peak'],1)
 def test_play_request_preempts_native_catalog_without_opening_a_directory(self):
  props={crew.OWNER:'request'}
  home=NS(getProperty=lambda key:props.get(key,''),setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  with patch.object(crew,'_home',return_value=home),patch.dict(sys.modules,{'xbmc':NS(executeJSONRPC=lambda payload: self.fail('directory opened during playback'))}):
   self.assertEqual(crew.listing(ROOT+'?action=nba'),[])
 def test_listing_marker_clears_on_failure(self):
  props={}
  home=NS(getProperty=lambda key:props.get(key,''),setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  def fail(payload):
   self.assertEqual(props[crew.SCAN_BUSY],'true');raise RuntimeError('private fixture')
  with patch.object(crew,'_home',return_value=home),patch.dict(sys.modules,{'xbmc':NS(executeJSONRPC=fail)}):
   with self.assertRaises(RuntimeError):crew.listing(ROOT+'?action=nba')
  self.assertNotIn(crew.SCAN_BUSY,props)
 def test_playback_waits_for_active_listing_to_finish(self):
  props={crew.SCAN_BUSY:'true'};waits=[]
  home=NS(getProperty=lambda key:props.get(key,''))
  def sleep(ms):waits.append(ms);props.clear()
  with patch.object(crew,'_home',return_value=home),patch.dict(sys.modules,{'xbmc':NS(sleep=sleep)}):
   crew.wait_for_listing()
  self.assertEqual(waits,[100])
 def test_catalog_yields_while_a_video_is_already_playing(self):
  with patch.object(crew,'_home',return_value=None),patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(isPlayingVideo=lambda:True))}):
   self.assertTrue(crew.playback_requested())
   self.assertEqual(crew.listing(ROOT+'?action=nba'),[])
 def test_source_failure_keeps_espn_games_and_never_pauses_jet(self):
  import sports_pause
  schedule=[dict(GAME,id='fixture',league='NBA',sport='Basketball',sources=[])]
  with patch.object(jet,'_folder',return_value='/installed'),patch.object(crew,'schedule',return_value=schedule),patch.object(crew,'discover',side_effect=RuntimeError('private fixture')),patch.object(sports_pause.Pause,'pause',side_effect=AssertionError('Jet touched')):
   provider=jet.JetProvider(clock=lambda:1001,crew_only=True)
   self.assertTrue(provider._start().wait(2))
   self.assertEqual(len(provider._games([])['live']),1)
   self.assertIn('Crew discovery',provider.reason)
 def test_complete_native_query_is_retained(self):
  calls=[];route='?action=play&url=fixture%2Fexact&content=addons'
  with patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda address:calls.append(address))),'xbmcgui':NS()}):
   self.assertTrue(jet.play_one(source(route=route)['play'],lambda message:None))
  self.assertEqual(calls,[ROOT+route])
 def test_matched_game_is_expanded_before_unrelated_folders_consume_budget(self):
  def read(route):
   if route.endswith('root'):return [entry('Site %d'%n,'site%d'%n) for n in range(40)]
   if route.endswith('site0'):return [entry('Alpha vs Beta','matched')]
   if route.endswith('matched'):return [entry('Source','play',False)]
   return []
  items=crew.CrewSource('NBA',ROOT+'root',[GAME],read).get_items()
  self.assertEqual(len(items),1)
 def test_closed_session_stops_the_next_crew_folder(self):
  props={context.SESSION:'open:fixture'};calls=[]
  home=NS(getProperty=lambda k:props.get(k,''))
  def read(route):
   calls.append(route);props[context.SESSION]='closed:fixture'
   return [entry('another site','next')]
  with patch.object(crew,'_home',return_value=home):
   items=crew.CrewSource('NBA',ROOT+'root',[GAME],read,session='open:fixture').get_items()
  self.assertEqual(items,[]);self.assertEqual(calls,[ROOT+'root'])
 def test_new_session_cannot_revive_old_collector(self):
  home=NS(getProperty=lambda k:'open:new' if k==context.SESSION else '')
  with patch.object(crew,'_home',return_value=home):
   self.assertEqual(crew.CrewSource('NBA',ROOT+'root',[GAME],lambda route:self.fail('stale scan opened a folder'),session='open:old').get_items(),[])
 def test_context_restores_only_its_own_navigation_and_never_during_playback(self):
  props={};actions=[];state={'crew':False,'playing':False}
  home=NS(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v))
  def execute(command,*args):
   actions.append(command)
   if command.startswith('ActivateWindow'):state['crew']=True
  xbmc=NS(getInfoLabel=lambda k:context.ADDON if state['crew'] else '',getCondVisibility=lambda k:True,
          Player=lambda:NS(isPlayingVideo=lambda:state['playing']),executebuiltin=execute)
  gui=NS(getCurrentWindowId=lambda:10025)
  ctx=context.Context(home,xbmc,gui);ctx.open();self.assertTrue(ctx.ready.wait(1))
  ctx.cancel();self.assertEqual(len(actions),1)
  ctx.close();self.assertEqual(actions[-1],'Action(Back)')
  ctx.close();self.assertEqual(actions.count('Action(Back)'),1)
  state['crew']=False;ctx=context.Context(home,xbmc,gui);ctx.open();self.assertTrue(ctx.ready.wait(1))
  props[context.OWNER]='playback';ctx.close();self.assertEqual(actions.count('Action(Back)'),1)
 def test_existing_crew_and_missing_addon_are_not_navigated(self):
  for already_open,installed in [(True,True),(False,False)]:
   props={};actions=[]
   home=NS(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v))
   xbmc=NS(getInfoLabel=lambda k:context.ADDON if already_open else '',getCondVisibility=lambda k:installed,
           Player=lambda:NS(isPlayingVideo=lambda:False),executebuiltin=lambda *a:actions.append(a))
   ctx=context.Context(home,xbmc,NS(getCurrentWindowId=lambda:10025));ctx.open();ctx.close()
   self.assertEqual(actions,[])
 def test_play_request_ends_scan_session_before_dispatch(self):
  props={context.SESSION:'open:fixture'};calls=[]
  home=NS(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v))
  def launch(*args):
   calls.append(args)
   self.assertEqual(props[context.SESSION],'closed:fixture')
   self.assertTrue(props[context.OWNER])
  jet.play_request(source(),lambda message:None,window=home,launch=launch)
  self.assertEqual(len(calls),1)
 def test_unready_or_cancelled_context_never_opens_a_crew_directory(self):
  for current in ['closed:fixture','open:different']:
   home=NS(getProperty=lambda k:current if k==context.SESSION else '')
   xbmc=NS(getInfoLabel=lambda k:'',sleep=lambda ms:None)
   with patch.object(crew,'_home',return_value=home),patch.dict(sys.modules,{'xbmc':xbmc}):
    self.assertEqual(crew.discover(read=lambda path:self.fail('unexpected Crew listing'),schedule=[GAME],session='open:fixture'),[])
 def test_only_sports_owned_background_listing_hides_crew_busy_dialog(self):
  import time
  for owner in ['', 'playing']:
   props={context.SESSION:'open:fixture',context.OWNER:owner};calls=[]
   home=NS(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
   def rpc(payload):
    time.sleep(.25)
    return json.dumps({'result':{'files':[]}})
   xbmc=NS(executeJSONRPC=rpc,getCondVisibility=lambda x:True,executebuiltin=lambda x:calls.append(x),Player=lambda:NS(isPlayingVideo=lambda:False))
   with patch.object(crew,'_home',return_value=home),patch.dict(sys.modules,{'xbmc':xbmc}):
    self.assertEqual(crew.listing(ROOT+'?action=nba',session='open:fixture'),[])
   self.assertEqual(bool(calls),not bool(owner))
   self.assertTrue(all(x=='Dialog.Close(busydialognocancel)' for x in calls))
 def test_reopens_native_menu_chain_after_another_league_clears_regex_cache(self):
  old=ROOT+'?action=play&url=%24doregex%5Bmakelist2%5D%7Cregex%3Dold'
  fresh=ROOT+'?action=play&url=%24doregex%5Bmakelist2%5D%7Cregex%3Dfresh&content=0'
  root=ROOT+'?action=nba';parent=ROOT+'?action=xdirectory&url=fresh-parent'
  calls=[]
  def read(route):
   calls.append(route)
   if route==root:return [entry('NBA LIVE (CS)','?action=xdirectory&url=fresh-parent')]
   if route==parent:return [entry('Alpha vs Beta',fresh.removeprefix(ROOT),False)]
   self.fail('old cached folder used')
  link=crew.CrewLink(old,[{'address':root,'label':'Crew NBA'},{'address':ROOT+'?action=xdirectory&url=expired-parent','label':'NBA LIVE (CS)'}],GAME).to_dict()
  self.assertEqual(crew.refresh_link(link,read),fresh)
  self.assertEqual(calls,[root,parent]);self.assertEqual(link['address'],old)
 def test_unresolved_legacy_expression_is_rejected_without_menu_provenance(self):
  with self.assertRaises(RuntimeError):crew.refresh_link({'address':ROOT+'?action=play&url=%24doregex%5Bmakelist2%5D%7Cregex%3Dmissing'})
 def test_refresh_refuses_missing_ambiguous_or_wrong_game(self):
  link=crew.CrewLink(ROOT+'play',[{'address':ROOT+'?action=nba','label':'Crew NBA'}],GAME).to_dict()
  for rows in [[],[entry('Alpha vs Other','wrong',False)],[entry('Alpha vs Beta','one',False),entry('Beta vs Alpha','two',False)]]:
   with self.assertRaises(RuntimeError):crew.refresh_link(link,lambda route:rows)
 def test_refresh_never_calls_another_addon_or_non_sports_root(self):
  link=crew.CrewLink(ROOT+'play',[{'address':ROOT+'?action=movies','label':'Movies'}],GAME).to_dict()
  with self.assertRaises(ValueError):crew.refresh_link(link,lambda route:self.fail('unexpected lookup'))
  link['menu_path'][0]['address']='plugin://another.addon/'
  with self.assertRaises(ValueError):crew.refresh_link(link,lambda route:self.fail('unexpected lookup'))
 def test_refresh_stops_when_a_new_play_request_replaces_ownership(self):
  props={crew.OWNER:'old'};home=NS(getProperty=lambda key:props.get(key,''))
  link=crew.CrewLink(ROOT+'play',[{'address':ROOT+'?action=nba','label':'NBA'}],GAME).to_dict()
  def read(route):props[crew.OWNER]='new';return [entry('Alpha vs Beta','play',False)]
  with patch.object(crew,'_home',return_value=home):
   with self.assertRaises(InterruptedError):crew.refresh_link(link,read)
 def test_native_provider_abbreviation_is_preserved_for_distinct_source_labels(self):
  ext=crew.CrewSource('NHL',ROOT+'?action=nhl',[GAME],lambda route:[entry('NHL LIVE (CS)','provider')] if route.endswith('nhl') else [entry('Alpha vs Beta','play',False)])
  item=ext.get_items()[0];record=jet.records(item,ext.name,1001)[0]
  self.assertEqual(record['addon'],'Crew CS')
  self.assertEqual(json.loads(record['play'])['e'],crew.NAME)
  self.assertEqual(json.loads(record['play'])['l']['menu_path'][-1]['label'],'NHL LIVE (CS)')
if __name__=='__main__':unittest.main()
