"""One-file Drive replacement, boot/post-upload queue and failure/restart boundaries."""
import hashlib,importlib.util,json,os,sys,tempfile,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import prepare_downloads as prep
import driveupload

class Drive:
 def __init__(self):
  self.data=b'original video';self.version=1;self.props={};self.name='Movie.2160p.mkv'
  self.buffer=b'';self.requests=[];self.corrupt=False;self.pause_after=None
 def token(self):return 'synthetic'
 def meta(self):return {'id':'source-id','name':self.name,'size':str(len(self.data)),
  'version':str(self.version),'md5Checksum':hashlib.md5(self.data).hexdigest(),'appProperties':dict(self.props)}
 def call(self,method,url,body=None,headers=None):
  self.requests.append((method,url,body,headers or {}))
  if method=='GET':return 200,{'ETag':'version-'+str(self.version)},json.dumps(self.meta()).encode()
  if method=='PATCH' and 'uploadType=resumable' in url:
   self.pending_name=json.loads(body)['name'];self.buffer=b''
   return 200,{'Location':'https://upload.example/session'},b''
  if method=='PATCH':self.props.update(json.loads(body)['appProperties']);return 200,{},b'{}'
  if method=='PUT':
   cr=headers['Content-Range']
   if cr.startswith('bytes */'):return 308,{'Range':'bytes=0-%d'%(len(self.buffer)-1)} if self.buffer else {},b''
   a,b=cr[6:].split('/')[0].split('-');self.buffer=self.buffer[:int(a)]+body
   if int(b)+1==int(cr.split('/')[1]):
    self.data=b'corrupt' if self.corrupt else self.buffer;self.name=self.pending_name;self.version+=1
    return 200,{},json.dumps(self.meta()).encode()
   return 308,{'Range':'bytes=0-%d'%(len(self.buffer)-1)},b''
  raise AssertionError((method,url))

class Native:
 def __init__(self):self.calls=0;self.bad_resolution=False;self.pause=False
 def probe(self,path):
  converted=Path(path).read_bytes().startswith(b'prepared')
  return {'ready':converted,'width':1920 if converted and self.bad_resolution else 3840,
          'height':1080 if converted and self.bad_resolution else 2160,'hdr':True,'duration':1300}
 def convert(self,source,output,keep_going,progress):
  self.calls+=1
  if self.pause:raise driveupload.Stop()
  progress(2,650,1300);Path(output).write_bytes(b'prepared video')

class Replacement(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'out.mp4';self.path.write_bytes(b'prepared video')
  self.drive=Drive();self.source=prep.metadata(self.drive,'source-id');self.sessions={}
 def tearDown(self):self.tmp.cleanup()
 def replace(self,keep=lambda:True):return prep.replace(self.drive,self.source,str(self.path),self.sessions,lambda:None,keep,lambda n,t:None)
 def test_same_drive_id_is_updated_no_second_file_created(self):
  result=self.replace();self.assertEqual(result['id'],'source-id');self.assertEqual(self.drive.data,self.path.read_bytes())
  self.assertEqual(self.drive.name,'Movie.2160p.mp4');self.assertFalse(any(m=='POST' for m,*_ in self.drive.requests))
  initial=[r for r in self.drive.requests if r[0]=='PATCH' and 'uploadType' in r[1]][0]
  self.assertEqual(initial[3]['If-Match'],'version-1')
 def test_partial_upload_keeps_existing_movie_and_resumes(self):
  calls=[0]
  def keep():calls[0]+=1;return calls[0]<4
  with patch.object(driveupload,'CHUNK',4):
   with self.assertRaises(driveupload.Stop):self.replace(keep)
   self.assertEqual(self.drive.data,b'original video')
   self.replace()
  self.assertEqual(self.drive.data,self.path.read_bytes())
 def test_changed_source_is_not_overwritten(self):
  self.drive.data=b'another movie';self.drive.version+=1
  with self.assertRaisesRegex(RuntimeError,'source changed'):self.replace()
  self.assertEqual(self.drive.data,b'another movie')
  self.assertFalse(any(m=='PUT' for m,*_ in self.drive.requests))
 def test_corrupt_upload_is_never_marked_verified(self):
  self.drive.corrupt=True
  with self.assertRaisesRegex(RuntimeError,'checksum differs'):self.replace()
  self.assertTrue(self.path.exists());self.assertFalse(self.drive.props)
 def test_completed_but_unacknowledged_upload_recovers_without_reupload(self):
  self.drive.data=self.path.read_bytes();result=self.replace()
  self.assertEqual(result['id'],'source-id');self.assertFalse(any(m=='PUT' for m,*_ in self.drive.requests))

class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.profile=Path(self.tmp.name);self.drive=Drive();self.native=Native();self.notes=[]
  self.space=patch.object(prep.shutil,'disk_usage',return_value=type('Disk',(),{'free':10**15})());self.space.start();self.addCleanup(self.space.stop)
  self.clock=lambda:10000
  def download(drive,item,path,keep,progress):Path(path).write_bytes(drive.data);progress(len(drive.data),len(drive.data))
  self.download=download
  self.queue=prep.Queue(self.profile,self.drive,self.native,download,self.notes.append,self.clock)
  self.queue.notify=lambda *args:self.notes.append(args)
  self.source=prep.metadata(self.drive,'source-id');self.slot=prep.key(self.source)
  self.queue.state['jobs'][self.slot]={'source':self.source,'status':'waiting','retry_after':0};self.queue.commit()
 def tearDown(self):self.tmp.cleanup()
 def test_full_job_keeps_id_resolution_and_one_file_then_removes_scratch(self):
  self.assertTrue(self.queue.process_one());self.assertEqual(self.drive.data,b'prepared video')
  self.assertEqual(self.native.calls,1);self.assertTrue(prep.ready(self.drive.meta()))
  self.assertFalse((self.queue.work/self.slot).exists());self.assertEqual(self.queue.state['jobs'][self.slot]['status'],'done')
  self.assertEqual(self.notes[-1][1],'Ready for Kodi and AirPlay')
 def test_quality_downgrade_rejected_before_drive_replacement(self):
  self.native.bad_resolution=True
  self.assertFalse(self.queue.process_one());self.assertEqual(self.drive.data,b'original video');self.assertFalse(self.drive.props)
  self.assertFalse(any(m=='PUT' for m,*_ in self.drive.requests))
 def test_pause_keeps_original_and_progress_is_trackable(self):
  self.native.pause=True
  self.assertFalse(self.queue.process_one());self.assertEqual(self.drive.data,b'original video')
  cards=prep.cards(self.profile,self.clock);self.assertTrue(cards);self.assertFalse(cards[0]['running'])
  self.assertEqual(self.queue.state['jobs'][self.slot]['status'],'paused')
 def test_no_work_starts_during_playback(self):
  self.assertFalse(self.queue.process_one(lambda:False));self.assertEqual(self.native.calls,0)
  self.assertEqual(self.drive.data,b'original video')
 def test_restart_after_media_commit_tags_without_reconversion(self):
  folder=self.queue.work/self.slot;folder.mkdir();(folder/'prepared.mp4').write_bytes(b'prepared video')
  self.drive.data=b'prepared video';self.drive.version+=1
  self.queue.state['jobs'][self.slot]['status']='committing';self.queue.commit()
  new=prep.Queue(self.profile,self.drive,self.native,self.download,clock=self.clock)
  self.assertTrue(new.process_one());self.assertEqual(self.native.calls,0);self.assertTrue(prep.ready(self.drive.meta()))
 def test_boot_scan_includes_existing_movies_and_new_uploads_without_duplicates(self):
  with patch.object(prep.library_scan,'remote_files',return_value=[self.drive.meta()]):
   self.queue.scan(force=True);self.queue.scan(force=True)
  self.assertEqual(len(self.queue.state['jobs']),1)
 def test_scan_retains_unacknowledged_commit_for_recovery(self):
  self.queue.state['jobs'][self.slot]['status']='committing';self.drive.data=b'prepared video';self.drive.version+=1
  with patch.object(prep.library_scan,'remote_files',return_value=[self.drive.meta()]):self.queue.scan(force=True)
  self.assertIn(self.slot,self.queue.state['jobs']);self.assertEqual(len(self.queue.state['jobs']),1)
 def test_low_space_never_replaces_original(self):
  with patch.object(prep.shutil,'disk_usage',return_value=type('Disk',(),{'free':0})()):self.assertFalse(self.queue.process_one())
  self.assertEqual(self.native.calls,0);self.assertEqual(self.drive.data,b'original video')
 def test_external_mutation_of_tagged_file_is_scanned_again(self):
  item=self.drive.meta();item['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:'old'}
  self.assertFalse(prep.ready(item))
 def test_stale_running_card_does_not_hold_background_keepalive(self):
  self.queue.state['current']={'title':'Movie','stage':'Preparing','running':True,'updated':1,'progress':50};self.queue.commit()
  self.assertFalse(prep.cards(self.profile,self.clock)[0]['running'])

class Integration(unittest.TestCase):
 def test_service_scans_on_boot_and_after_uploads_and_settings_enable_it(self):
  service=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('preparation.scan(can_prepare,force=bool(count))',service);self.assertIn('preparation.process_one(can_prepare)',service)
  import xml.etree.ElementTree as ET
  setting=ET.parse(ROOT/'migration/bundled-bootstrap/resources/settings.xml').find(".//setting[@id='prepare_downloads']")
  self.assertEqual(setting.findtext('default'),'true')
 def test_notifications_have_preparation_progress(self):
  source=(ROOT/'migration/bundled-bootstrap/notifications.py').read_text();self.assertIn('prepare_downloads.cards(profile)',source)
  self.assertIn('self.percent(9431,',source)
 def test_framework_exports_probe_and_preparation(self):
  source=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('_kodi_airplay_prepare\\n_kodi_airplay_probe\\n',source)
  self.assertIn('[link hasSuffix:@"/prepared.mp4"]',source)

if __name__=='__main__':unittest.main()
