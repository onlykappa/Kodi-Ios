"""One-file Drive replacement, boot/post-upload queue and failure/restart boundaries."""
import hashlib,importlib.util,io,json,os,sys,tempfile,unittest,urllib.parse
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
 def test_change_during_partial_upload_prevents_final_commit(self):
  original_call=self.drive.call;changed=[False]
  def call(method,url,body=None,headers=None):
   result=original_call(method,url,body,headers)
   if method=='PUT' and result[0]==308 and not changed[0]:
    self.drive.data=b'owner changed the movie';self.drive.version+=1;changed[0]=True
   return result
  self.drive.call=call
  with patch.object(driveupload,'CHUNK',4):
   with self.assertRaisesRegex(RuntimeError,'source changed'):self.replace()
  self.assertEqual(self.drive.data,b'owner changed the movie')

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
 def test_compatible_4k_uses_copy_budget_instead_of_full_reencode_budget(self):
  probe=self.native.probe
  self.native.probe=lambda path:dict(probe(path),copy_video=True,audio_work_bytes=0)
  with patch.object(prep.shutil,'disk_usage',return_value=type('Disk',(),{'free':512*1024*1024})()):
   self.assertTrue(self.queue.process_one())
  self.assertTrue(prep.ready(self.drive.meta()))
 def test_manual_upload_invalidation_requests_a_scan(self):
  self.queue.state['last_scan']=self.clock();self.queue.commit()
  driveupload.invalidate_library(str(prep.location(self.profile).parent))
  with patch.object(prep.library_scan,'remote_files',return_value=[self.drive.meta()]) as remote:
   self.queue.scan();remote.assert_called_once()
  self.assertFalse((prep.location(self.profile).parent/'airplay-preparation-rescan').exists())
 def test_external_mutation_of_tagged_file_is_scanned_again(self):
  item=self.drive.meta();item['appProperties']={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:'old'}
  self.assertFalse(prep.ready(item))
 def test_stale_running_card_does_not_hold_background_keepalive(self):
  self.queue.state['current']={'title':'Movie','stage':'Preparing','running':True,'updated':1,'progress':50};self.queue.commit()
  self.assertFalse(prep.cards(self.profile,self.clock)[0]['running'])

class Download(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'source';self.drive=Drive();self.data=self.drive.data
 def tearDown(self):self.tmp.cleanup()
 def response(self,body,status=200,range=None):
  result=io.BytesIO(body);result.status=status;result.headers={'Content-Range':range} if range else {};return result
 def run_download(self,response,keep=lambda:True):
  return prep.download(self.drive,self.drive.meta(),str(self.path),keep,lambda n,t:None,open_url=lambda req:response)
 def test_resume_uses_exact_byte_range(self):
  self.path.write_bytes(self.data[:4]);requests=[]
  def open_url(req):
   requests.append(req);return self.response(self.data[4:],206,'bytes 4-%d/%d'%(len(self.data)-1,len(self.data)))
  prep.download(self.drive,self.drive.meta(),str(self.path),lambda:True,lambda n,t:None,open_url=open_url)
  self.assertEqual(requests[0].get_header('Range'),'bytes=4-');self.assertEqual(self.path.read_bytes(),self.data)
 def test_server_ignoring_range_restarts_instead_of_appending_duplicate_bytes(self):
  self.path.write_bytes(self.data[:4]);self.run_download(self.response(self.data))
  self.assertEqual(self.path.read_bytes(),self.data)
 def test_wrong_range_is_rejected_without_damaging_checkpoint(self):
  self.path.write_bytes(self.data[:4])
  with self.assertRaisesRegex(RuntimeError,'wrong byte range'):self.run_download(self.response(self.data,206,'bytes 0-13/14'))
  self.assertEqual(self.path.read_bytes(),self.data[:4])
 def test_cancelled_read_preserves_resume_prefix(self):
  self.path.write_bytes(self.data[:4])
  with self.assertRaises(driveupload.Stop):self.run_download(self.response(self.data[4:],206,'bytes 4-13/14'),lambda:False)
  self.assertEqual(self.path.read_bytes(),self.data[:4])
 def test_oversized_response_is_never_accepted(self):
  with self.assertRaisesRegex(RuntimeError,'size changed'):self.run_download(self.response(self.data+b'extra'))

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

class Shelf:
 """A Drive with several files and folders, a Trash, and the calls preparation's duplicate step makes."""
 def __init__(self):self.files={};self.trashed=[]
 def add(self,id,name,folder,size=10,**extra):
  self.files[id]=dict({'id':id,'name':name,'size':str(size),'md5Checksum':id*4,'parent':folder,'version':'1'},**extra)
  return dict(self.files[id],folderName={'f1':'Lanterns','f2':'Lanterns (2026)','f3':'Movies'}[folder],folderId=folder)
 def call(self,method,url,body=None,headers=None):
  parsed=urllib.parse.urlsplit(url);fid=urllib.parse.unquote(parsed.path.rsplit('/',1)[1])
  if method=='PATCH' and json.loads(body).get('trashed'):self.trashed.append(fid);self.files.get(fid,{})['trashed']=True;return 200,{},b'{}'
  if method=='GET' and fid=='files':
   parent=urllib.parse.parse_qs(parsed.query)['q'][0].split("'")[1]
   return 200,{},json.dumps({'files':[f for f in self.files.values() if f['parent']==parent and not f.get('trashed')]}).encode()
  if method=='GET' and fid in self.files:return 200,{},json.dumps(self.files[fid]).encode()
  return 404,{},b'{}'

class OneCopyEach(unittest.TestCase):
 """Owner (build 152): S1 E1 in 'Lanterns' and 'Lanterns (2026)' was queued twice; the extra copy should be deleted."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.notes=[];self.shelf=Shelf()
  self.queue=prep.Queue(self.tmp.name,self.shelf,Native(),notify=lambda *a:self.notes.append(a),clock=lambda:1000)
 def tearDown(self):self.tmp.cleanup()
 def test_keeps_the_best_copy_and_trashes_the_other_with_its_empty_folder(self):
  a=self.shelf.add('a','Lanterns.S01E01.Pilot.2160p.mkv','f1');b=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2',size=99)
  c=self.shelf.add('c','Lanterns.S01E02.2160p.mkv','f1');m=self.shelf.add('m','Inception.2010.mkv','f3')
  kept=self.queue.unique([b,a,c,m])
  self.assertEqual(sorted(x['id'] for x in kept),['a','c','m'])
  self.assertEqual(self.shelf.trashed,['b','f2'])   # the copy, then its now-empty "Lanterns (2026)" folder
  self.assertEqual(len(self.notes),1);self.assertIn('Lanterns · S1 E1',self.notes[0][2]);self.assertIn('Trash',self.notes[0][2])
 def test_a_shared_folder_is_not_trashed(self):
  a=self.shelf.add('a','Lanterns.S01E01.2160p.mkv','f1');b=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2')
  self.shelf.add('e','Lanterns (2026) - S01E02 - 1080p.mkv','f2')
  self.queue.unique([a,b]);self.assertEqual(self.shelf.trashed,['b'])
 def test_an_already_prepared_copy_wins(self):
  ready=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2',appProperties={prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:'bbbb'})
  other=self.shelf.add('a','Lanterns.S01E01.2160p.mkv','f1')
  self.assertTrue(prep.ready(ready))
  self.assertEqual([x['id'] for x in self.queue.unique([other,ready])],['b']);self.assertEqual(self.shelf.trashed,['a','f1'])
 def test_a_copy_being_saved_wins_and_is_never_trashed(self):
  saving=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2')
  self.queue.state['jobs']['slot-b']={'source':saving,'status':'committing'}
  self.assertEqual([x['id'] for x in self.queue.unique([self.shelf.add('a','Lanterns.S01E01.2160p.mkv','f1'),saving])],['b'])
  self.assertNotIn('b',self.shelf.trashed)
 def test_nothing_is_trashed_when_the_kept_copy_cannot_be_confirmed(self):
  a=self.shelf.add('a','Lanterns.S01E01.2160p.mkv','f1');b=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2')
  del self.shelf.files['a']   # listed, but gone when checked
  kept=self.queue.unique([a,b]);self.assertEqual(self.shelf.trashed,[]);self.assertEqual(sorted(x['id'] for x in kept),['a','b'])
 def test_a_copy_changed_since_listing_is_kept(self):
  a=self.shelf.add('a','Lanterns.S01E01.2160p.mkv','f1');b=self.shelf.add('b','Lanterns (2026) - S01E01 - 1080p.mkv','f2')
  self.shelf.files['b']['md5Checksum']='changed'
  self.queue.unique([a,b]);self.assertEqual(self.shelf.trashed,[])
 def test_different_years_are_different_shows(self):
  a=self.shelf.add('a','The Office (2001) - S01E01.mkv','f1');b=self.shelf.add('b','The Office (2005) - S01E01.mkv','f2')
  self.assertEqual(sorted(x['id'] for x in self.queue.unique([a,b])),['a','b']);self.assertEqual(self.shelf.trashed,[])
 def test_scan_queues_one_job_for_two_copies(self):
  d=self.queue.drive=Drive();listed=[dict(d.meta(),folderName='Lanterns',name='Lanterns.S01E01.2160p.mkv'),
   {'id':'other','name':'Lanterns (2026) - S01E01 - 1080p.mkv','folderName':'Lanterns (2026)','size':'5'}]
  with patch.object(prep.library_scan,'remote_files',return_value=listed):self.queue.scan(force=True)
  self.assertEqual(len(self.queue.state['jobs']),1)

if __name__=='__main__':unittest.main()
