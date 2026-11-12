"""Roadmap 1E.7: idle wake-ups per minute of the service's always-on loops, measured with a fake clock.
Each loop is run for 60 simulated seconds with nothing to do; the count is the number of times it wakes."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import activity,background,native_ui,searchbar,source_guard,transfer_history

class Clock:
 """wait(seconds) advances time and counts a wake-up; True (stop) once `limit` seconds have passed."""
 def __init__(self,limit=60.0):self.now=0.0;self.wakes=0;self.limit=limit;self.waits=[]
 def wait(self,seconds):
  self.waits.append(seconds)
  if self.now+seconds>self.limit:return True
  self.now+=seconds;self.wakes+=1;return False
 def time(self):return self.now

class IdleWakeups(unittest.TestCase):
 def test_activity_idle_slows_and_busy_does_not(self):
  clock=Clock()
  activity.watch(lambda:None,lambda:[],lambda:[],lambda k,d:True,lambda:False,lambda p:None,lambda t:None,clock.wait,clock=clock.time)
  self.assertLessEqual(clock.wakes,55)            # was 120 a minute
  clock=Clock()
  activity.watch(lambda:('Downloading','x',None),lambda:[],lambda:[],lambda k,d:True,lambda:False,lambda p:None,lambda t:None,clock.wait,clock=clock.time)
  self.assertEqual(set(clock.waits),{0.5})        # a visible box keeps the half-second look

 def test_source_guard_idle_and_active(self):
  clock=Clock();source_guard.run(object(),lambda:[],lambda *a:None,lambda *a:None,clock.wait)
  self.assertLessEqual(clock.wakes,10)            # was 30
  clock=Clock()
  with patch.object(source_guard,'identity',return_value=None),patch.object(source_guard.Guard,'tick',return_value=None):
   source_guard.run(object(),lambda:[{'id':'1','name':'x'}],lambda *a:None,lambda *a:None,clock.wait)
  self.assertEqual(clock.wakes,30)                # a torrent keeps the 2 s look

 def test_transfer_history_idle_and_running(self):
  clock=Clock()
  with patch.object(transfer_history,'load',return_value={}),patch.object(transfer_history,'save'):
   transfer_history.watch('p',lambda:{},clock.wait,clock=clock.time)
  self.assertLessEqual(clock.wakes,13)            # was 30
  clock=Clock()
  with patch.object(transfer_history,'load',return_value={}),patch.object(transfer_history,'save'):
   transfer_history.watch('p',lambda:{'download':{'title':'a','rate':1,'done':1,'total':2}},clock.wait,clock=clock.time)
  self.assertEqual(clock.wakes,30)                # a running transfer is still drawn every 2 s

 def test_background_idle_and_busy(self):
  clock=Clock();background.watch(lambda v:None,lambda:'',clock.wait)
  self.assertLessEqual(clock.wakes,20)            # was 60
  clock=Clock();background.watch(lambda v:None,lambda:'a download',clock.wait)
  self.assertEqual(clock.wakes,60)                # keeps the one-second renewal while work exists

 def test_native_ui_poll_rhythm(self):
  quiet=type('P',(),{})();quiet.needed=lambda:False
  typing=type('P',(),{})();typing.needed=lambda:True
  self.assertEqual(native_ui.poll_wait([quiet],False),native_ui.SLOW)
  self.assertEqual(native_ui.poll_wait([typing],False),native_ui.FAST)
  self.assertEqual(native_ui.poll_wait([quiet,typing],False),native_ui.FAST)
  self.assertEqual(native_ui.poll_wait([typing],True),native_ui.SLOW)
  self.assertEqual(native_ui.poll_wait([lambda:None],False),native_ui.FAST)   # a poll with no hook (tab bar taps) stays fast
  self.assertEqual(60/native_ui.SLOW,120)         # was 60/0.05 = 1200 wake-ups a minute

 def test_search_poll_is_needed_only_when_field_shown(self):
  class Lib:
   def kodi_search_show(self,v):pass
   def kodi_search_set(self,t):pass
  tick,poll,close=searchbar.controller(Lib(),lambda:(0,''),lambda c:c!="System.HasActiveModalDialog",lambda:True,lambda k,v:None,lambda:0.0)
  self.assertFalse(poll.needed())
  tick();self.assertTrue(poll.needed())

if __name__=='__main__':unittest.main()
