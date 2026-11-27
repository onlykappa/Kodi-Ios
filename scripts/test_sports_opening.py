"""Opening ownership/cancellation controls; actual GUI/native choices need rig evidence."""
import sys,json,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_opening as opening
class Tests(unittest.TestCase):
 def make(self,owner='mine'):
  self.props={opening.OWNER:owner};self.calls=[]
  home=NS(getProperty=lambda k:self.props.get(k,''),clearProperty=lambda k:self.props.pop(k,None))
  obj=opening.Opening({'native_owner':'mine'},home)
  obj.window=NS(close=lambda:self.calls.append('close'))
  return obj
 def test_cancel_stops_owned_opening_and_invalidates_ownership(self):
  obj=self.make()
  with patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(stop=lambda:self.calls.append('stop')))}):obj.cancel()
  self.assertEqual(self.calls,['stop','close']);self.assertTrue(obj.cancelled)
  self.assertNotIn(opening.OWNER,self.props)
 def test_old_cancel_never_stops_replacement(self):
  obj=self.make('new')
  with patch.dict(sys.modules,{'xbmc':NS(Player=lambda:self.fail('replacement stopped'))}):obj.cancel()
  self.assertEqual(self.props[opening.OWNER],'new');self.assertEqual(self.calls,['close'])
 def test_close_is_idempotent(self):
  obj=self.make();obj.close();obj.close();self.assertEqual(self.calls,['close'])
 def test_timeout_stops_owned_opening(self):
  obj=self.make()
  with patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(stop=lambda:self.calls.append('stop')))}):obj.wait(timeout=0)
  self.assertTrue(obj.cancelled);self.assertEqual(self.calls,['stop','close'])
 def test_a_playing_picture_closes_the_card_even_without_a_player_callback(self):
  # Build 775: The Loop plays the stream from its own script; the callbacks never reached this one and the card stayed over the picture.
  states={'Player.HasVideo':True,'Player.Playing':True,'Player.Paused':False}
  xbmc=NS(getCondVisibility=lambda c:states[c])
  self.assertTrue(opening.picture_on_screen(xbmc))
  states['Player.Paused']=True;self.assertFalse(opening.picture_on_screen(xbmc))
  states.update({'Player.Paused':False,'Player.HasVideo':False});self.assertFalse(opening.picture_on_screen(xbmc))
 def test_matchup_from_descriptor_not_url(self):
  self.assertEqual(opening.matchup({'play':json.dumps({'l':{'game':{'away':{'name':'Alpha'},'home':{'name':'Beta'}}}})}),'Alpha\nBeta')
  self.assertEqual(opening.matchup({'play':'not-json'}),'Live game')
 def test_matchup_handles_long_team_names(self):
  long_name='A'*500
  value=opening.matchup({'play':json.dumps({'l':{'game':{'away':{'name':long_name},'home':{'name':'Beta'}}}})})
  self.assertEqual(value,'%s\nBeta'%long_name)
 def test_matchup_handles_malformed_queue(self):
  self.assertEqual(opening.matchup({'native_queue':[],'play':'{}'}),'Live game')
  self.assertEqual(opening.matchup({'native_queue':[{'play':123}]}),'Live game')
 def test_close_drops_observer_so_stale_callback_is_inert(self):
  obj=self.make();obj.observer='sentinel';obj.close()
  self.assertIsNone(obj.observer)
 def test_late_avstarted_from_replaced_opening_does_not_set_started(self):
  obj=self.make('mine');self.props[opening.OWNER]='someone-else'
  class FakeObserver:
   def onAVStarted(inner_self):
    if obj.owner and obj.home.getProperty(opening.OWNER)!=obj.owner:return
    obj.started.set()
  FakeObserver().onAVStarted()
  self.assertFalse(obj.started.is_set())
if __name__=='__main__':unittest.main()
