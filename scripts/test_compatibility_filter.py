"""Skip full Drive preparation only after codec inspection; retain original and transaction safety."""
import copy,sys,tempfile,threading,json,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import prepare_downloads as prep,library_rows,work_state
from test_drive_prepare import Drive,Native,Stream

class Filter(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.drive=Drive();self.native=Native();self.q=prep.Queue(self.tmp.name,self.drive,self.native,stream=Stream())
  self.item=prep.metadata(self.drive,'source');self.slot=prep.key(self.item)
  self.q.state={'jobs':{self.slot:{'source':self.item,'status':'waiting','retry_after':0}},'sessions':{},
                'library':{'items':[prep.entry(self.item,'todo')],'videos':1,'ready':0}}
  self.probe={'ready':False,'copy_video':True,'codec':'hevc','bit_depth':10,'width':3840,'height':2160,'hdr':True,'duration':1300,'audio_work_bytes':160000000}
  self.native.probe=lambda path:dict(self.probe)
  self.layout={'fast_open':True,'layout_reason':'front_moov'}
  self.q.layout_probe=lambda *args:dict(self.layout)
  self.q.commit()
 def test_compatible_mkv_keeps_original_without_conversion_or_upload(self):
  original=copy.deepcopy(self.drive.files['source'])
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,0)
  self.assertEqual(self.drive.files['source'],original);self.assertEqual(set(self.drive.files),{'source'})
  self.assertTrue(prep.playback_ready(self.tmp.name,prep.metadata(self.drive,'source')))
  row=prep.library_view(self.q.state)['rows']['ready'][0]
  self.assertTrue(row['stream_only']);self.assertEqual(library_rows.details(row,{})['status'],'Ready to stream')
 def test_audio_work_does_not_force_full_video_reupload(self):
  self.probe['audio_work_bytes']=99999999
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,0)
 def test_h264_is_also_streamed_without_permanent_conversion(self):
  self.probe.update(codec='h264',bit_depth=8)
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,0)
 def test_filename_is_not_evidence_of_codec_compatibility(self):
  self.item['name']='Movie.H265.4K.mp4'
  self.probe.update(codec='av1',copy_video=False)
  self.assertFalse(prep.streamable_video(self.probe))
  # Keep the pipeline's existing native-output probe/verification behavior for a required conversion.
  normal=Native.probe
  self.native.probe=lambda path:dict(normal(self.native,path),codec='av1',copy_video=False)
  self.q.process_one();self.assertEqual(self.native.calls,1)
 def test_unknown_or_unsupported_pixel_format_is_not_skipped(self):
  for probe in ({},dict(self.probe,codec='av1'),dict(self.probe,copy_video=False),dict(self.probe,codec=''),dict(self.probe,width='unknown')):
   self.assertFalse(prep.streamable_video(probe))
 def test_automatic_scan_keeps_prepared_files_without_a_requested_repair(self):
  original=self.drive.files['source']
  original['appProperties']={prep.PROPERTY:prep.OLD_PROFILES[0],prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  with patch.object(prep.library_scan,'remote_files',return_value=[self.item]):self.q.scan(force=True)
  self.assertEqual(self.q.state['library']['ready'],1)
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,0)
 def test_existing_queued_repack_of_a_ready_file_never_creates_a_sink(self):
  original=self.drive.files['source']
  original['appProperties']={prep.PROPERTY:prep.OLD_PROFILES[0],prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.q.state['jobs'][self.slot]['repack']=True
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,0)
  self.assertEqual(set(self.drive.files),{'source'})
 def test_changed_file_invalidates_local_ready_decision(self):
  self.q.process_one();changed=prep.metadata(self.drive,'source');changed['version']='new'
  self.assertFalse(prep.playback_ready(self.tmp.name,changed))
  changed['md5Checksum']='different';self.assertFalse(prep.playback_ready(self.tmp.name,changed))
 def test_rescan_uses_exact_cached_probe_and_removes_stale_waiting_conversion(self):
  self.q.state['jobs'][self.slot]['probe']=self.probe;self.q.commit()
  with patch.object(prep.library_scan,'remote_files',return_value=[self.item]):self.q.scan(force=True)
  self.assertEqual(self.q.state['library']['ready'],1)
  self.assertEqual(self.q.state['jobs'][self.slot]['status'],'done');self.assertEqual(self.native.calls,0)
 def test_source_version_change_requires_fresh_inspection(self):
  self.q.state['jobs'][self.slot]['probe']=self.probe
  self.drive.files['source']['version']='2'
  with patch.object(prep.library_scan,'remote_files',return_value=[self.item]):self.q.scan(force=True)
  self.assertNotIn('probe',self.q.state['jobs'][self.slot]);self.assertEqual(self.q.state['library']['ready'],0)
 def test_in_progress_commit_or_promoted_file_is_not_abandoned(self):
  job=self.q.state['jobs'][self.slot]
  for extra in ({'status':'committing'},{'status':'waiting','promoted':'new-id'},{'status':'waiting','kept':True}):
   copy_job=dict(job,**extra);self.assertFalse(self.q.skip_compatible(self.slot,copy_job,self.item,self.probe))
 def test_unneeded_staging_is_journaled_without_touching_the_original(self):
  job=self.q.state['jobs'][self.slot];job['cloud_output']={'0':{'id':'app-temp','moved':False}}
  self.assertTrue(self.q.skip_compatible(self.slot,job,self.item,self.probe))
  self.assertEqual(self.q.state['staging_cleanup'],['app-temp']);self.assertIn('source',self.drive.files)
 def refresh(self,beside=False):
  with patch.object(prep.library_scan,'remote_files',return_value=[self.item]):self.q.scan(force=True,beside=beside)
 def test_refresh_inspects_unknown_lanterns_episode_without_uploading_or_converting(self):
  self.drive.files['source']['name']='Lanterns.S01E06.2160p.mkv'
  original=copy.deepcopy(self.drive.files['source']);calls=[]
  self.native.probe=lambda url:(calls.append(url),dict(self.probe))[1]
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(len(calls),1);self.assertEqual(self.q.state['library']['ready'],1)
  self.assertEqual(self.native.calls,0);self.assertEqual(self.drive.files['source'],original)
  self.assertFalse(any(method in ('PUT','POST','PATCH') for method,*_ in self.drive.calls))
  self.assertFalse(self.q.process_one());self.assertFalse(prep.check_requested(self.tmp.name))
 def test_every_manual_refresh_rechecks_the_actual_file_even_after_restart(self):
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.q=prep.Queue(self.tmp.name,self.drive,self.native,stream=Stream())
  calls=[];self.native.probe=lambda url:(calls.append(url),dict(self.probe))[1]
  self.q.layout_probe=lambda *args:(calls.append('layout'),dict(self.layout))[1]
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],1);self.assertFalse(self.q.process_one());self.assertEqual(len(calls),2)
 def test_refresh_reinspects_changed_version_instead_of_trusting_stale_readiness(self):
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.drive.files['source']['version']='2';self.probe.update(copy_video=False,codec='av1')
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],0);self.assertEqual(self.q.state['jobs'][self.slot]['probe']['codec'],'av1')
 def test_refresh_beside_active_conversion_defers_native_probe_then_inspects_when_idle(self):
  with patch.object(self.native,'probe',side_effect=AssertionError('native instance is busy')):
   prep.request_check(self.tmp.name,inspect=True);self.refresh(beside=True)
  self.assertTrue(self.q.inspection_pending);self.assertTrue(prep.check_requested(self.tmp.name))
  self.refresh();self.assertEqual(self.q.state['library']['ready'],1);self.assertFalse(prep.check_requested(self.tmp.name))
 def test_failed_inspection_never_labels_an_unknown_file_ready(self):
  self.native.probe=lambda url:(_ for _ in ()).throw(TimeoutError())
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],0);self.assertNotIn('probe',self.q.state['jobs'][self.slot])
  self.assertIn('inspection_error',self.q.state['jobs'][self.slot]);self.assertEqual(self.native.calls,0)
 def test_source_change_during_probe_does_not_cache_a_false_ready_decision(self):
  def change(url):self.drive.files['source']['version']='2';return self.probe
  self.native.probe=change;prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],0);self.assertNotIn('probe',self.q.state['jobs'][self.slot])
 def test_automatic_requests_do_not_downgrade_manual_inspection(self):
  prep.request_check(self.tmp.name,inspect=True);prep.request_check(self.tmp.name);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],1)
 def test_new_refresh_during_scan_is_not_consumed_by_an_older_scan(self):
  def refresh_again(url):prep.request_check(self.tmp.name,inspect=True);return self.probe
  self.native.probe=refresh_again;prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertTrue(prep.check_requested(self.tmp.name))
 def test_refresh_repairs_only_missing_fast_open_and_keeps_playback_available(self):
  self.layout.update(fast_open=False,layout_reason='not_mp4')
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  job=self.q.state['jobs'][self.slot]
  self.assertTrue(job['repack']);self.assertEqual(job['status'],'waiting')
  self.assertTrue(job['probe']['copy_video']);self.assertTrue(prep.playback_ready(self.tmp.name,self.item))
  view=library_rows.with_model(prep.library_view(self.q.state),work_state.build({'prep':self.q.state},self.q.clock()))
  self.assertEqual((view['ready'],view['todo']),(0,1))
  row=view['rows']['waiting'][0];self.assertTrue(row['repack']);self.assertTrue(row['ready_now'])
  sheet=library_rows.details(row,view)
  self.assertIn(('Faster opening','Queued'),sheet['facts']);self.assertIn(('Play','play'),sheet['actions'])
  self.assertEqual(self.native.calls,0);self.assertFalse(any(m in ('PUT','POST','PATCH') for m,*_ in self.drive.calls))
  # A second Refresh must not reset a resumable task or its retry delay.
  job.update(status='failed',retry_after=12345,attempts=3,cloud_output={'0':{'id':'partial','moved':False}})
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual((job['status'],job['retry_after'],job['attempts']),('failed',12345,3))
  self.assertIn('cloud_output',job)
  self.assertEqual(prep.library_view(self.q.state)['rows']['waiting'][0]['state'],'problem')
 def test_refresh_reads_every_listed_movie_and_episode_on_each_tap(self):
  listed=[self.item];calls=[]
  for ident,name in (('episode','Lanterns.S01E06.mkv'),('movie','Another.Movie.mp4')):
   self.drive.files[ident]=dict(self.drive.files['source'],id=ident,name=name)
   listed.append(self.drive.meta(ident))
  self.native.probe=lambda url:(calls.append(url),dict(self.probe))[1]
  for _ in range(2):
   prep.request_check(self.tmp.name,inspect=True)
   with patch.object(prep.library_scan,'remote_files',return_value=listed):self.q.scan(force=True)
  self.assertEqual(len(calls),6);self.assertEqual(self.q.state['library']['videos'],3)
  self.assertEqual(self.q.state['library']['ready'],3);self.assertEqual(self.native.calls,0)
 def test_source_change_during_layout_inspection_invalidates_both_checks(self):
  def changed(*args):self.drive.files['source']['version']='2';return dict(self.layout)
  self.q.layout_probe=changed;prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertNotIn('probe',self.q.state['jobs'][self.slot]);self.assertEqual(self.q.state['library']['ready'],0)
 def test_refresh_checks_prepared_markers_again_and_queues_missing_layout(self):
  self.drive.files['source']['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.layout.update(fast_open=False,layout_reason='missing_fragment_index')
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  job=self.q.state['jobs'][self.slot]
  self.assertTrue(job['repack']);self.assertEqual(job['probe']['layout_reason'],'missing_fragment_index')
  # The ready marker must not short-circuit the repair when the worker starts.
  original=self.native.probe
  self.native.probe=lambda url:Native.probe(self.native,url) if 'temp-' in url else original(url)
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,1)
  self.assertTrue(self.drive.files['source']['trashed']);self.assertEqual(job['status'],'done')
 def test_refresh_skips_already_fast_prepared_files_without_uploads(self):
  self.drive.files['source']['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  calls=[];self.q.layout_probe=lambda *args:(calls.append(args),dict(self.layout))[1]
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(len(calls),1);self.assertFalse(self.q.process_one())
  self.assertFalse(any(m in ('PUT','POST','PATCH') for m,*_ in self.drive.calls))
 def test_refresh_repairs_known_old_fragment_layout_but_keeps_fast_progressive_originals(self):
  self.drive.files['source']['appProperties']={prep.PROPERTY:prep.OLD_PROFILES[0],prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.layout['layout_reason']='fragment_index'
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertTrue(self.q.state['jobs'][self.slot]['repack'])
  self.layout['layout_reason']='front_moov'
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertNotIn('repack',self.q.state['jobs'][self.slot]);self.assertFalse(self.q.process_one())
 def test_refresh_preserves_owner_kept_choice(self):
  self.q.state['jobs'][self.slot]['kept']=True
  self.native.probe=lambda url:self.fail('owner-kept original was probed')
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertTrue(self.q.state['jobs'][self.slot]['kept']);self.assertFalse(self.q.process_one())
 def test_prepared_marker_cannot_override_an_incompatible_track_inspection(self):
  self.drive.files['source']['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.probe.update(codec='av1',copy_video=False)
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  self.assertEqual(self.q.state['library']['ready'],0)
  job=self.q.state['jobs'][self.slot];self.assertTrue(job['audit'])
  original=self.native.probe
  self.native.probe=lambda url:Native.probe(self.native,url) if 'temp-' in url else original(url)
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,1)
 def test_incompatible_repair_remains_required_after_an_interrupted_attempt(self):
  self.drive.files['source']['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.probe.update(codec='av1',copy_video=False)
  prep.request_check(self.tmp.name,inspect=True);self.refresh();self.native.fail=True
  self.assertFalse(self.q.process_one());job=self.q.state['jobs'][self.slot]
  self.assertTrue(job['audit']);self.assertEqual(job['status'],'paused')
  self.refresh();self.assertEqual(self.q.state['library']['ready'],0)
  original=self.native.probe;self.native.fail=False
  self.native.probe=lambda url:Native.probe(self.native,url) if 'temp-' in url else original(url)
  self.assertTrue(self.q.process_one());self.assertEqual(self.native.calls,2)
 def test_refresh_failed_layout_read_does_not_reuse_a_stale_compatible_result(self):
  self.q.process_one()
  self.q.layout_probe=lambda *args:(_ for _ in ()).throw(TimeoutError())
  prep.request_check(self.tmp.name,inspect=True);self.refresh()
  job=self.q.state['jobs'][self.slot]
  self.assertNotIn('probe',job);self.assertTrue(job['audit']);self.assertEqual(job['status'],'failed')
 def test_concurrent_automatic_check_cannot_overwrite_a_manual_refresh(self):
  entered=threading.Event();continue_auto=threading.Event();manual_done=threading.Event();exists=Path.exists
  def delayed_exists(path):
   result=exists(path)
   if path.name==prep.RESCAN and threading.current_thread().name=='automatic':
    entered.set();self.assertTrue(continue_auto.wait(2))
   return result
  def manual():
   prep.request_check(self.tmp.name,inspect=True);manual_done.set()
  with patch.object(Path,'exists',delayed_exists):
   auto=threading.Thread(target=prep.request_check,args=(self.tmp.name,),name='automatic');auto.start()
   self.assertTrue(entered.wait(2));refresh=threading.Thread(target=manual);refresh.start()
   manual_done.wait(.1);continue_auto.set();auto.join(2);refresh.join(2)
  self.assertFalse(auto.is_alive());self.assertFalse(refresh.is_alive())
  marker=prep.location(self.tmp.name).parent/prep.RESCAN
  self.assertTrue(json.loads(marker.read_text())['inspect'])
if __name__=='__main__':unittest.main()
