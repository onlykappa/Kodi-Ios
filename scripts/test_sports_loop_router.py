"""Native queue selection, privacy, cancellation and successful playback cleanup."""
import json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_loop_router as router

def source(name='Loop LiveFeeds',quality='',path='one'):
 return {'addon':name,'quality':quality,'play':json.dumps({'e':'TheLoopRoute','l':{'address':'plugin://plugin.video.the-loop/play/'+path}})}

class Tests(unittest.TestCase):
 def test_rank_uses_reported_quality_then_provider_priority_and_keeps_other_adapters(self):
  other={'addon':'Independent','quality':'','play':'independent-value'}
  selected=router.automatic_source([source('Loop XYZAlt',path='x'),source('Loop LiveFeeds',path='live'),source('Loop Other','1080p','hd'),other])
  self.assertEqual(selected['native_queue'][0]['addon'],'Loop Other')
  self.assertEqual(selected['native_queue'][1]['addon'],'Loop LiveFeeds')
  self.assertEqual(selected['alts'],['independent-value'])
 def test_non_native_uses_existing_fallback_door(self):
  selected=router.automatic_source([{'addon':'A','play':'a'},{'addon':'B','play':'b'}])
  self.assertNotIn('native_queue',selected);self.assertEqual(selected['alts'],['b'])
 def test_invalid_route_never_enters_native_queue(self):
  for address in ['https://example.invalid/private','plugin://other/play','plugin://u:p@plugin.video.the-loop/play']:
   self.assertIsNone(router.native_route({'play':json.dumps({'e':'TheLoopRoute','l':{'address':address}})}))
 def test_async_handoff_preserves_queue_and_replaces_ownership(self):
  import sports_jet
  props={};launched=[]
  home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''))
  selected=router.automatic_source([source(path='first'),source(path='second')])
  for _ in range(2):sports_jet.play_request(selected,lambda s:None,home,lambda *a:launched.append(a))
  keys=[args[-1] for args in launched]
  self.assertNotEqual(keys[0],keys[1])
  payload=json.loads(props[sports_jet.PLAY+keys[-1]])
  self.assertEqual(payload['native_queue'],selected['native_queue'])
  self.assertEqual(payload['native_owner'],props[router.OWNER])
 def test_provider_can_stage_request_without_launching_over_a_modal(self):
  import sports_provider,sports_jet
  props={};pending=[]
  home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''))
  selected=router.automatic_source([source(path='first'),source(path='second')])
  with patch.dict('os.environ',{'KODI_IOS_SPORTS':'jet'}),patch.dict(sys.modules,{'xbmcgui':NS(Window=lambda ident:home)}),patch.object(sports_jet,'_launch',side_effect=AssertionError('premature native launch')):
   self.assertTrue(sports_provider.play(selected,lambda line:None,launch=lambda *args:pending.append(args)))
  self.assertEqual(pending[0][:2],('sports_jet_run','play'))
  self.assertEqual(json.loads(props[sports_jet.PLAY+pending[0][-1]])['native_queue'],selected['native_queue'])
 def test_native_script_does_not_replace_the_addon_constructor(self):
  import sports_jet
  props={};home=NS(getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
  selected=router.automatic_source([source()]);props[sports_jet.PLAY+'fixture']=json.dumps(selected)
  fake_opening=NS(open=lambda:None,cancelled=False,wait=lambda timeout=45:None,close=lambda:None)
  with patch.dict(sys.modules,{'xbmcgui':NS(),'sports_opening':NS(Opening=lambda source,home:fake_opening)}),patch.object(sports_jet,'named_addon',side_effect=AssertionError('native context patched')),patch.object(sports_jet,'play',return_value=True) as played:
   sports_jet.run_script(['play','fixture'],home)
   played.assert_called_once()
 def test_stale_script_cannot_start_after_a_new_request(self):
  import sports_jet
  props={router.OWNER:'new',sports_jet.PLAY+'old':json.dumps({'native_owner':'old','play':source()['play']})}
  home=NS(getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
  with patch.dict(sys.modules,{'xbmcgui':NS()}),patch.object(sports_jet,'play',side_effect=AssertionError('stale request played')) as played:
   sports_jet.run_script(['play','old'],home)
   played.assert_not_called()
  self.assertEqual(props[router.OWNER],'new')
 def test_native_queue_failure_tries_independent_alternative(self):
  import sports_jet
  selected=router.automatic_source([source(),{'addon':'Independent','play':'independent-value'}])
  with patch.object(router,'play',side_effect=RuntimeError('private fixture details')),patch.object(sports_jet,'play_one',return_value=True) as played:
   self.assertTrue(sports_jet.play(selected,lambda s:None))
   played.assert_called_once_with('independent-value',unittest.mock.ANY)
 def test_stopping_native_queue_does_not_start_another_provider(self):
  import sports_jet
  selected=router.automatic_source([source(),{'addon':'Independent','play':'independent-value'}])
  with patch.object(router,'play',side_effect=InterruptedError()),patch.object(sports_jet,'play_one') as played:
   self.assertFalse(sports_jet.play(selected,lambda s:None));played.assert_not_called()
 def exercise(self,ready=False,stopped=False,select=False,all_failed=False,replaced=False,http_error=False,frozen=False,takeover=False,timeout=.6,slow_play=False,late_stop=False,sources=3):
  state={'now':0,'entries':[],'clears':0,'stops':0,'prepared':[]};logs=[];props={}
  class Player:
   def play(self,playlist,**kwargs):
    state['player']=self;state['play_calls']=state.get('play_calls',0)+1;state['advanced']=state['play_calls']>1
    if slow_play and state['play_calls']==1:   # Kodi does not return from play() until Crew has resolved the link
     import time
     for _ in range(5):time.sleep(.2);state['now']+=.2
     state['picks_while_play_blocked']=sum('picked the first link' in line for line in logs)
   def isPlayingVideo(self):return ready or (http_error and state.get('advanced',False))
   def getTime(self):return 0 if frozen else state['now']
   def stop(self):
    if type(self) is Player:state['prior_stops']=state.get('prior_stops',0)+1
    else:state['stops']+=1
  class Playlist:
   def clear(self):state['clears']+=1;state['entries']=[]
   def add(self,address,item):state['entries'].append(address)
   def getposition(self):return -1 if all_failed or takeover else 0
   def size(self):return len(state['entries'])
  def sleep(ms):
   state['now']+=ms/1000
   if 'player' not in state:return
   if ready or (http_error and state.get('advanced',False)):state['player'].onAVStarted()
   if http_error and not state.get('advanced',False):state['player'].onPlayBackError()
   if stopped:state['player'].onPlayBackStarted();state['player'].onPlayBackStopped()
   if late_stop and state['now']>=state.get('late_after',3.2) and state.get('late_stops',0)<9:
    state['late_after']=state['now']+7;state['late_stops']=state.get('late_stops',0)+1;state['player'].onPlayBackStopped()   # a failed open: a Stop and no start, 3 s or more in
   if replaced:props[router.OWNER]='new-request'
  backend=NS(Player=Player,PlayList=lambda _:Playlist(),PLAYLIST_VIDEO=1,sleep=sleep,executebuiltin=lambda value:(state.__setitem__("error_dialog_closed",value),state.setdefault('closed',[]).append(value)),
    Monitor=lambda:NS(abortRequested=lambda:state['now']>2 if select else False),getCondVisibility=lambda cond:(takeover if 'HasMedia' in cond else select if "selectdialog" in cond else all_failed))
  home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
  gui=NS(ListItem=lambda **kw:NS(setProperty=lambda *a:None),Window=lambda ident:home)
  original_prepare=router.routes.prepare_source
  def prepare(candidate):
   state['prepared'].append(candidate['play']);return original_prepare(candidate)
  with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(router.routes,'prepare_proxy'),patch.object(router.routes,'prepare_source',side_effect=prepare):
   try:result=router.play([source(path='token-private'),source(path='second'),source(path='second')][:sources],logs.append,backend,lambda:state['now'],timeout=timeout)
   except Exception as error:result=error
  self.assertEqual(state["clears"],1 if replaced else 3 if (http_error or stopped) else 2) if not late_stop else None
  self.assertNotIn('token-private',' '.join(logs))
  return result,state,logs
 def test_native_success_clears_future_sources_without_stopping_video(self):
  result,state,logs=self.exercise(ready=True)
  self.assertTrue(result);self.assertEqual(state['stops'],0);self.assertEqual(len(state['prepared']),1)
  self.assertIn('sports: playing (native addon queue)',logs)
  self.assertEqual(sum('a source failed' in line for line in logs),0)
 def test_av_start_without_advancing_video_is_not_counted_as_success(self):
  result,state,logs=self.exercise(ready=True,frozen=True)
  self.assertIsInstance(result,InterruptedError)
  self.assertEqual(len(state['prepared']),1)
  self.assertNotIn('sports: playing (native addon queue)',logs)
 def test_media_http_error_after_resolution_advances_to_the_next_choice(self):
  result,state,logs=self.exercise(http_error=True)
  self.assertTrue(result)
  self.assertEqual(len(state['prepared']),2)
  self.assertTrue(state['advanced']);self.assertIn('Dialog.Close(okdialog)',state['closed'])
  self.assertEqual(sum('media open failed' in line for line in logs),1)
 def test_crew_playing_its_own_stream_is_not_taken_for_an_ended_opening(self):
  # Build 611: Crew plays the resolved stream itself (the playlist no longer holds our item) while it is still opening; the queue must wait
  # for it, not stop it as "ended without a confirmed error" (that check used to be held off by Crew's progress box, now silent).
  result,state,logs=self.exercise(takeover=True,timeout=3)
  self.assertNotIn('sports: native opening ended without a confirmed error; queue cancelled',logs)
  self.assertIn('timed out',str(result))
 def test_the_chooser_is_answered_while_play_is_still_blocked(self):
  # Build 611 phone log: play() blocked through Crew's chooser, the answering loop had not started, the owner had to tap.
  result,state,logs=self.exercise(select=True,slow_play=True)
  import time
  for _ in range(60):   # play() now runs on a helper thread (build 775): the queue goes on while it is blocked, so its end comes after the queue's
   if 'picks_while_play_blocked' in state:break
   time.sleep(.05)
  self.assertEqual(state['picks_while_play_blocked'],1)
  self.assertEqual(len([l for l in logs if 'picked the first link' in l]),1)
 def test_a_play_call_that_stays_blocked_does_not_hide_a_picture_that_has_started(self):
  # Build 775 log: The Loop plays the stream itself and its script (so play()) stays alive for the whole playback; the picture must still be judged and the queue return.
  result,state,logs=self.exercise(ready=True,slow_play=True,timeout=3)
  self.assertTrue(result);self.assertIn('sports: playing (native addon queue)',logs)
 def test_timeout_cancels_queue(self):
  result,state,_=self.exercise()
  self.assertIsInstance(result,InterruptedError);self.assertEqual(state['stops'],1);self.assertEqual(len(state['prepared']),1)
 def test_native_all_failed_dialog_finishes_without_waiting_for_timeout(self):
  result,state,_=self.exercise(all_failed=True)
  self.assertIsInstance(result,InterruptedError)
  self.assertIn('dialog',str(result));self.assertLess(state['now'],.6)
 def test_new_request_does_not_clear_or_stop_the_new_player(self):
  result,state,_=self.exercise(replaced=True)
  self.assertIsInstance(result,InterruptedError);self.assertEqual(state['stops'],0);self.assertEqual(len(state['prepared']),1)
 def test_a_stop_before_any_picture_with_the_queue_still_ours_is_a_failed_source_and_the_next_one_opens(self):
  # Build 619 log: Crew's streamers failed, Kodi's open failed and only a Stop ("current media") reported it; the app cancelled and said "check the log".
  # A person's own cancel clears the ownership first (see test_new_request_does_not_clear_or_stop_the_new_player), so this is a failure, not a cancel.
  result,state,logs=self.exercise(stopped=True)
  self.assertIsInstance(result,Exception)   # both fail in this scripted run, so it ends (exhausted or timed out), never as a cancel
  self.assertNotIn('sports: native opening stopped; queue cancelled',logs)
  self.assertTrue(state.get('advanced',False));self.assertEqual(len(state['prepared']),2)   # the second source was tried
  self.assertIn('Dialog.Close(yesnodialog)',state.get('closed',[]))
  self.assertTrue(any('stopped before any picture' in l for l in logs))
 def test_a_late_stop_with_no_start_is_a_failed_source_not_a_cancel(self):   # build 653 logs 5ee55982: HTTP 503 from the stream's host
  result,state,logs=self.exercise(late_stop=True,timeout=40,sources=2)
  self.assertNotIn('sports: native opening stopped; queue cancelled',logs)
  self.assertTrue(state.get('advanced',False));self.assertTrue(any('stopped before a picture' in l or 'stopped before any picture' in l for l in logs))
 def test_a_source_that_fails_quickly_is_tried_again_at_the_end_when_it_is_the_only_one(self):
  result,state,logs=self.exercise(late_stop=True,timeout=60,sources=1)
  self.assertTrue(any('failed quickly; it will be tried again' in l for l in logs))
  self.assertEqual(len(state['prepared']),1+router.SAME_RETRIES)   # the first try and the retries, then it gives up
 def test_nested_source_selection_does_not_consume_server_timeout(self):
  result,state,_=self.exercise(select=True)
  self.assertIsInstance(result,InterruptedError);self.assertGreater(state['now'],.6)
 def test_a_crew_link_chooser_is_answered_with_its_first_entry_once(self):
  # Owner, 2026-11-20: no Crew UI; the chooser Crew shows while it resolves is answered for the person.
  result,state,logs=self.exercise(select=True)
  self.assertEqual(state['error_dialog_closed'],'Action(Select)')   # the fake backend keeps the last builtin it was given
  self.assertEqual(len([l for l in logs if 'picked the first link' in l]),1)   # one answer for one appearance of the chooser
if __name__=='__main__':unittest.main()
