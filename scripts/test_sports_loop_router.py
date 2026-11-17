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
 def exercise(self,ready=False,stopped=False,select=False,all_failed=False,replaced=False):
  state={'now':0,'entries':[],'clears':0,'stops':0};logs=[];props={}
  class Player:
   def play(self,playlist):state['player']=self
   def isPlayingVideo(self):return ready
   def stop(self):state['stops']+=1
  class Playlist:
   def clear(self):state['clears']+=1;state['entries']=[]
   def add(self,address,item):state['entries'].append(address)
   def getposition(self):return -1 if all_failed else 1 if ready else 0
  def sleep(ms):
   state['now']+=ms/1000
   if ready:state['player'].onAVStarted()
   if stopped:state['player'].onPlayBackStopped()
   if replaced:props[router.OWNER]='new-request'
  backend=NS(Player=Player,PlayList=lambda _:Playlist(),PLAYLIST_VIDEO=1,sleep=sleep,
    Monitor=lambda:NS(abortRequested=lambda:state['now']>2 if select else False),getCondVisibility=lambda cond:(select if "selectdialog" in cond else all_failed))
  home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
  gui=NS(ListItem=lambda **kw:NS(setProperty=lambda *a:None),Window=lambda ident:home)
  with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(router.routes,'prepare_proxy'):
   try:result=router.play([source(path='token-private'),source(path='second'),source(path='second')],logs.append,backend,lambda:state['now'],timeout=.6)
   except Exception as error:result=error
  self.assertEqual(state['clears'],1 if replaced else 2)
  self.assertNotIn('token-private',' '.join(logs))
  return result,state,logs
 def test_native_success_clears_future_sources_without_stopping_video(self):
  result,state,logs=self.exercise(ready=True)
  self.assertTrue(result);self.assertEqual(state['stops'],0)
  self.assertIn('sports: playing (native Loop queue)',logs)
  self.assertEqual(sum('a source failed' in line for line in logs),1)
 def test_timeout_cancels_queue(self):
  result,state,_=self.exercise()
  self.assertIsInstance(result,RuntimeError);self.assertEqual(state['stops'],1)
 def test_native_all_failed_dialog_finishes_without_waiting_for_timeout(self):
  result,state,_=self.exercise(all_failed=True)
  self.assertIsInstance(result,RuntimeError)
  self.assertIn('no native source',str(result));self.assertLess(state['now'],.6)
 def test_new_request_does_not_clear_or_stop_the_new_player(self):
  result,state,_=self.exercise(replaced=True)
  self.assertIsInstance(result,InterruptedError);self.assertEqual(state['stops'],0)
 def test_user_stop_is_cancellation(self):
  result,_,_=self.exercise(stopped=True)
  self.assertIsInstance(result,InterruptedError)
 def test_nested_source_selection_does_not_consume_server_timeout(self):
  result,state,_=self.exercise(select=True)
  self.assertIsInstance(result,InterruptedError);self.assertGreater(state['now'],.6)
if __name__=='__main__':unittest.main()
