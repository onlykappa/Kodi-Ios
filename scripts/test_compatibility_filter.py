"""Skip full Drive preparation only after codec inspection; retain original and transaction safety."""
import copy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import prepare_downloads as prep,library_rows
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
 def test_previously_prepared_files_are_not_queued_for_an_optional_repack(self):
  original=self.drive.files['source']
  original['appProperties']={prep.PROPERTY:prep.OLD_PROFILES[0],prep.CHECKSUM_PROPERTY:self.item['md5Checksum']}
  self.q.state['jobs'][self.slot]['repack']=True
  with patch.object(prep.library_scan,'remote_files',return_value=[self.item]):self.q.scan(force=True)
  self.assertEqual(self.q.state['library']['ready'],1)
  job=self.q.state['jobs'][self.slot];self.assertEqual(job['status'],'done');self.assertNotIn('repack',job)
  self.assertFalse(self.q.process_one());self.assertEqual(self.native.calls,0)
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
if __name__=='__main__':unittest.main()
