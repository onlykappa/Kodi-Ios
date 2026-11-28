"""Unexpected-stop classification and bounded private evidence with a synthetic playback clock."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import airplay_diagnostics as recorder,diagnostics,airplay,remote_media

def sample(position=100,**changes):
 player=dict(generation=1,state=1,active=1,position=position,duration=7200,rate=1,time_control=1,external=1,stop_reason=0,sample_age_s=0)
 player.update(changes);return {'player':player,'network':{'tv_video':4},'source':{'cache_hits':5}}

class Classification(unittest.TestCase):
 def setUp(self):self.tracker=recorder.Tracker();self.tracker.observe(sample(),0)
 def test_real_continuous_hour_then_failure_retains_position_and_error(self):
  for now in range(5,3601,5):self.assertIsNone(self.tracker.observe(sample(100+now),now))
  report=self.tracker.observe(sample(3700,state=-1,active=0,stop_reason=2,error_code=-12889),3605)
  self.assertEqual(report['reason'],'player_failed');self.assertEqual(report['recent'][-1]['player']['error_code'],-12889)
  self.assertEqual(len(report['recent']),96);self.assertEqual(report['recent'][0]['at'],3130)
 def test_owner_close_and_normal_end_are_not_unexpected_stops(self):
  self.assertIsNone(self.tracker.observe(sample(7199,active=0,state=0,stop_reason=1),5))
  self.assertIsNone(self.tracker.observe(sample(100,active=0,state=0,stop_reason=3),10))
 def test_an_end_notification_halfway_through_the_movie_is_still_captured(self):
  report=self.tracker.observe(sample(3600,active=0,state=0,stop_reason=1),3600)
  self.assertEqual(report['reason'],'ended_before_duration')
 def test_pausing_is_not_a_buffering_stall(self):
  for now in range(5,101,5):self.assertIsNone(self.tracker.observe(sample(rate=0,time_control=0),now))
 def test_waiting_without_progress_is_captured_after_thirty_seconds(self):
  for now in range(5,30,5):self.assertIsNone(self.tracker.observe(sample(rate=0,time_control=2,buffer_empty=1),now))
  self.assertEqual(self.tracker.observe(sample(rate=0,time_control=2),30)['reason'],'buffering_without_progress')
  self.assertIsNone(self.tracker.observe(sample(rate=0,time_control=2),35))
 def test_progress_prevents_a_false_stall(self):
  for now in range(5,81,5):self.assertIsNone(self.tracker.observe(sample(100+now,time_control=2),now))
 def test_seek_and_suspension_restart_the_observation_interval(self):
  self.assertIsNone(self.tracker.observe(sample(5,time_control=2),120))
  self.assertIsNone(self.tracker.observe(sample(5,time_control=2),125))
 def test_new_generation_cannot_inherit_the_previous_movie_failure(self):
  self.assertIsNone(self.tracker.observe(sample(0,generation=2,active=0,state=0,stop_reason=2),5))
 def test_stale_native_sample_is_not_treated_as_live_evidence(self):
  self.assertIsNone(self.tracker.observe(sample(state=-1,stop_reason=2,sample_age_s=60),60))
 def test_receiver_route_loss_is_identified_separately(self):
  self.assertEqual(self.tracker.observe(sample(external=0),5)['reason'],'receiver_route_ended')
 def test_unexplained_active_to_idle_transition_is_captured(self):
  self.assertEqual(self.tracker.observe(sample(active=0,state=0),5)['reason'],'unexpected_player_stop')
 def test_source_allowlist_drops_media_identity_and_signed_urls(self):
  safe=recorder.selected({'cache_hits':1,'url':'https://private.invalid/?token=hidden','id':'secret'},recorder.SOURCE)
  self.assertEqual(safe,{'cache_hits':1})

class Evidence(unittest.TestCase):
 def test_rotation_and_export_preserve_bounded_redacted_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   logs=[]
   for i in range(5):recorder.capture(tmp,dict(reason='player_failed',generation=i,at=i,recent=[sample(i)]),logs.append,{'url':'https://private.invalid/secret'})
   folder=Path(tmp)/'addon_data/service.kodi.ios.bootstrap'
   self.assertEqual(len(list(folder.glob('airplay-stop-*.json'))),3)
   self.assertEqual(json.loads((folder/'airplay-stop-latest.json').read_text())['generation'],4)
   export=diagnostics.export(tmp,tmp,tmp,tmp)
   text=export.read_text();self.assertIn('airplay-stop-latest.json',text);self.assertNotIn('private.invalid',text)
   self.assertIn('unexpected_stop','\n'.join(logs))
 def test_closed_source_broker_does_not_hide_the_stop(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=iter([sample()['player'],sample(200,state=-1,active=0,stop_reason=2)['player']]);turns=iter([False,False,True]);log=[]
   with patch.object(airplay,'health',side_effect=lambda lib:next(rows)),patch.object(airplay,'network',return_value={}),patch.object(remote_media,'stats',side_effect=OSError('closed')):
    recorder.watch(SimpleNamespace(kodi_airplay_health=Mock()),tmp,Mock(),log.append,lambda sec:next(turns),clock=iter([0,5]).__next__)
   self.assertTrue((Path(tmp)/'addon_data/service.kodi.ios.bootstrap/airplay-stop-latest.json').exists())
 def test_old_framework_without_snapshot_api_is_compatible(self):
  wait=Mock();recorder.watch(SimpleNamespace(),'',None,Mock(),wait);wait.assert_not_called()

class JudderSamples(unittest.TestCase):
 # ISSUE-491 (owner log ad7d3e73): the 30 s samples caught a stall (position 2598 -> 2607 in 30 s) but nothing shorter
 def p(self,position,**k):
  d=dict(time_control=2,rate=1.0,buffer_empty=0,likely_to_keep_up=1,external=1,position=position);d.update(k);return d
 def test_steady_playback_says_nothing(self):
  j=recorder.Judder();self.assertEqual(j.observe(self.p(100),0),[])
  self.assertEqual(j.observe(self.p(105),5),[]);self.assertEqual(j.observe(self.p(110.2),10),[])
 def test_a_stretch_where_the_picture_clock_lagged_is_a_position_slip(self):
  j=recorder.Judder();j.observe(self.p(100),0)
  out=j.observe(self.p(102.5),5)
  self.assertEqual([n for n,_ in out],['position_slip']);f=out[0][1]
  self.assertEqual((f['wall_s'],f['advanced_s'],f['lost_s']),(5.0,2.5,2.5))
 def test_state_changes_are_events_at_once(self):
  j=recorder.Judder();j.observe(self.p(100),0)
  out=j.observe(self.p(105,buffer_empty=1,likely_to_keep_up=0),5)
  self.assertEqual(out[0][0],'state_change');self.assertEqual(out[0][1]['changes'],{'buffer_empty':[0,1],'likely_to_keep_up':[1,0]})
 def test_a_seek_a_pause_and_an_ios_suspension_are_not_slips(self):
  j=recorder.Judder();j.observe(self.p(100),0)
  self.assertEqual([n for n,_ in j.observe(self.p(900),5)],[])                                   # seek forward
  self.assertEqual([n for n,_ in j.observe(self.p(100),10)],[])                                   # seek back
  self.assertEqual([n for n,_ in j.observe(self.p(101,time_control=0,rate=0.0),15)],['state_change'])   # pause
  self.assertEqual([n for n,_ in j.observe(self.p(101),60)],['state_change'])                      # resumed after a 45 s gap: no slip
 def test_the_watch_loop_logs_them(self):
  text=(ROOT/'migration/bundled-bootstrap/resources/lib/airplay_diagnostics.py').read_text()
  self.assertIn("for name,fields in judder.observe(player,now):diagnostics.event(write,'airplay',name",text)

if __name__=='__main__':unittest.main()
