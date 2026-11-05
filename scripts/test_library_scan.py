"""Behavioral checks for explicit phone-file reconciliation and verified Drive cleanup."""
import hashlib,importlib.util,json,os,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
import library_scan as scan,driveupload as upload,drivelibrary as drive_lib

class Drive:
 def __init__(self):self.files={};self.uploaded=[];self.checked=[];self.denied=False;self.bad_upload=False;self.after_upload=lambda path:None
 def folder(self,parts):self.parts=parts;return 'destination'
 def upload(self,path,parent,sessions,save,keep_going,progress):
  if not keep_going():raise upload.Stop()
  data=Path(path).read_bytes();item='uploaded-'+str(len(self.uploaded))
  meta={'id':item,'size':str(len(data)),'md5Checksum':hashlib.md5(data).hexdigest()}
  if self.bad_upload:meta['md5Checksum']='0'*32
  self.files[item]=meta;self.uploaded.append(path);self.after_upload(path)
  return dict(meta)
 def call(self,method,url,body=None,headers=None):
  from urllib.parse import urlsplit
  item=urlsplit(url).path.rsplit('/',1)[1];self.checked.append(item)
  if self.denied:return 503,{},b'{}'
  return 200,{},json.dumps(self.files.get(item,{})).encode()
 def duplicate(self,path,item='existing',**overrides):
  meta={'id':item,'name':'a renamed copy.mkv','size':str(Path(path).stat().st_size),'md5Checksum':hashlib.md5(Path(path).read_bytes()).hexdigest()}
  meta.update(overrides);self.files[item]=dict(meta);return dict(meta)

class ScanTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.state=self.root/'state';self.drive=Drive()
 def tearDown(self):self.tmp.cleanup()
 def file(self,name='Heat.1995.mkv',data=b'video bytes'):
  path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);os.utime(path,(time.time()-1000,)*2);return path
 def run_scan(self,paths,remote=(),**kwargs):return scan.scan([str(p) for p in paths],self.drive,str(self.state),remote=remote,**kwargs)
 def test_missing_movie_is_uploaded_verified_then_removed(self):
  path=self.file();cache=self.state/'drive-library.json';cache.parent.mkdir();cache.write_text('{}')
  result=self.run_scan([path]);self.assertEqual((result['uploaded'],result['deleted'],result['failed']),(1,1,0))
  self.assertFalse(path.exists());self.assertFalse(cache.exists());self.assertEqual(self.drive.parts,['Kodi Downloads','Movies'])
  self.assertIn('uploaded-0',self.drive.checked)
 def test_identical_bytes_with_different_name_remove_duplicate_without_upload(self):
  path=self.file();remote=self.drive.duplicate(path)
  result=self.run_scan([path],remote=[remote]);self.assertEqual((result['duplicates'],result['uploaded'],result['deleted']),(1,0,1))
  self.assertFalse(path.exists());self.assertEqual(self.drive.checked,['existing','existing'])
 def test_matching_name_and_size_but_different_bytes_are_not_a_duplicate(self):
  path=self.file();remote=self.drive.duplicate(path,md5Checksum='0'*32,name=path.name)
  result=self.run_scan([path],remote=[remote])
  # Same name, different bytes: never a byte duplicate, so the phone copy is never deleted on its name alone. Since the
  # owner's duplicate rule (build 152), it is the same episode/movie already on Drive, so it is not uploaded either.
  self.assertEqual((result['duplicates'],result['uploaded'],result['deleted'],result['same_media']),(0,0,0,1))
  self.assertNotIn('existing',self.drive.checked)
 def test_absent_listing_checksum_is_verified_from_fresh_metadata(self):
  path=self.file();remote=self.drive.duplicate(path);remote.pop('md5Checksum')
  result=self.run_scan([path],remote=[remote]);self.assertEqual(result['deleted'],1);self.assertEqual(result['uploaded'],0)
 def test_failed_remote_verification_keeps_phone_file(self):
  path=self.file();self.drive.bad_upload=True
  result=self.run_scan([path]);self.assertTrue(path.exists());self.assertEqual((result['deleted'],result['kept']),(0,1))
 def test_size_only_or_trashed_remote_copy_never_authorizes_delete(self):
  for override in ({'md5Checksum':''},{'trashed':True}):
   with self.subTest(override=override):
    path=self.file();self.drive.bad_upload=True;remote=self.drive.duplicate(path,**override)
    result=self.run_scan([path],remote=[remote]);self.assertTrue(path.exists());self.assertEqual(result['deleted'],0)
 def test_drive_http_failure_keeps_file_and_does_not_upload_blindly(self):
  path=self.file();remote=self.drive.duplicate(path);self.drive.denied=True
  result=self.run_scan([path],remote=[remote]);self.assertTrue(path.exists());self.assertEqual(result['failed'],1);self.assertEqual(self.drive.uploaded,[])
 def test_changed_phone_file_during_upload_is_preserved(self):
  path=self.file();self.drive.after_upload=lambda p:Path(p).write_bytes(b'other bytes')
  result=self.run_scan([path]);self.assertTrue(path.exists());self.assertEqual(result['deleted'],0)
 def test_cancel_after_upload_preserves_file(self):
  path=self.file();state={'cancel':False};self.drive.after_upload=lambda p:state.update(cancel=True)
  result=self.run_scan([path],keep_going=lambda:not state['cancel']);self.assertTrue(path.exists());self.assertTrue(result['cancelled']);self.assertEqual(result['kept'],1)
 def test_cancellation_before_scan_keeps_all_files(self):
  paths=[self.file(),self.file('Show.S01E01.mkv')]
  result=self.run_scan(paths,keep_going=lambda:False);self.assertTrue(result['cancelled']);self.assertEqual(result['kept'],2);self.assertEqual(self.drive.uploaded,[])
 def test_episode_is_uploaded_to_tv_show_folder(self):
  path=self.file('Show.Name.S02E03.mkv');result=self.run_scan([path])
  self.assertEqual(self.drive.parts,['Kodi Downloads','TV Shows','Show Name']);self.assertEqual(result['deleted'],1)
 def test_episode_only_filename_uses_named_show_folder(self):
  path=self.file('Show Name/Season 2/S02E03.mkv');self.run_scan([path])
  self.assertEqual(self.drive.parts,['Kodi Downloads','TV Shows','Show Name'])
 def test_episode_only_alternate_number_format_uses_show_folder(self):
  path=self.file('Show Name/Season 2/2x03.mkv');self.run_scan([path])
  self.assertEqual(self.drive.parts,['Kodi Downloads','TV Shows','Show Name'])
 def test_selected_folder_discovery_excludes_active_partial_symlink_and_app_data(self):
  done=self.file('selected/Heat.1995.mkv');self.file('selected/active/Partial.2020.mkv');self.file('selected/Other.partial.mkv')
  self.file('selected/sample.mkv');self.file('selected/empty.mkv',b'');self.file('selected/userdata/cached.mkv')
  self.file('selected/recent.mkv');os.utime(self.root/'selected/recent.mkv',None)
  target=self.file('outside/Else.2000.mkv');(self.root/'selected/link.mkv').symlink_to(target)
  (self.root/'selected/linked-dir').symlink_to(self.root/'outside',target_is_directory=True)
  self.assertEqual(scan.discover([str(self.root/'selected')],[str(self.root/'selected/active')]),[str(done)])
 def test_active_folder_selected_as_root_is_not_scanned(self):
  self.file('active/Partial.2020.mkv');self.assertEqual(scan.discover([str(self.root/'active')],[str(self.root/'active')]),[])
 def test_active_root_alias_in_ancestor_cannot_bypass_exclusion(self):
  self.file('active/child/Partial.2020.mkv');(self.root/'alias').symlink_to(self.root/'active',target_is_directory=True)
  self.assertEqual(scan.discover([str(self.root/'alias/child')],[str(self.root/'active')]),[])
 def test_folder_walk_can_be_cancelled_before_finishing(self):
  self.file('selected/nested/Heat.1995.mkv');calls=iter([True,True,False])
  with self.assertRaises(upload.Stop):scan.discover([str(self.root/'selected')],keep_going=lambda:next(calls,False))
 def test_duplicate_paths_are_only_scanned_once(self):
  path=self.file('selected/Heat.1995.mkv');self.assertEqual(scan.discover([str(self.root/'selected')]*2),[str(path)])
 def test_symlink_passed_directly_is_never_deleted_or_uploaded(self):
  path=self.file();link=self.root/'alias.mkv';link.symlink_to(path)
  result=self.run_scan([link]);self.assertTrue(link.is_symlink());self.assertTrue(path.exists());self.assertEqual(result['deleted'],0)
 def test_resumable_session_is_discarded_when_same_sized_source_bytes_changed(self):
  path=self.file();self.state.mkdir();(self.state/'library-scan.json').write_text(json.dumps({'sessions':{str(path):{'url':'old-session','size':path.stat().st_size}},'digests':{str(path):'old-digest'}}))
  previous=self.drive.upload
  def upload_new(path,parent,sessions,*args):self.assertNotIn(path,sessions);return previous(path,parent,sessions,*args)
  self.drive.upload=upload_new;self.run_scan([path])
 def test_existing_remote_copy_is_rechecked_before_deletion(self):
  path=self.file();remote=self.drive.duplicate(path);previous=self.drive.call
  def changing(*args,**kwargs):
   if self.drive.checked:self.drive.files['existing']['trashed']=True
   return previous(*args,**kwargs)
  self.drive.call=changing;result=self.run_scan([path],remote=[remote]);self.assertTrue(path.exists());self.assertEqual(result['deleted'],0)
 def test_index_handles_loose_episodes_and_arbitrarily_nested_release_folders(self):
  folders={'movies':[{'id':'nested','name':'release','mimeType':drive_lib.FOLDER}],
           'nested':[{'id':'movie','name':'Heat.1995.mkv','size':'100'}],
           'tv':[{'id':'episode','name':'Show.S01E01.mkv','size':'200'}]}
  with patch.object(drive_lib,'find_folders',side_effect=[['movies'],['tv']]),patch.object(drive_lib,'children',side_effect=lambda drive,folder:folders[folder]):
   self.assertEqual({f['id'] for f in scan.remote_files(self.drive)},{'movie','episode'})
 def test_index_includes_all_duplicate_drive_folder_branches(self):
  folders={'movies-a':[{'id':'film-a','name':'Film.A.mkv','size':'100'}],
           'movies-b':[{'id':'film-b','name':'Film.B.mkv','size':'200'}],
           'tv-a':[{'id':'episode-a','name':'Show.A.S01E01.mkv','size':'300'}],
           'tv-b':[{'id':'episode-b','name':'Show.B.S01E01.mkv','size':'400'}]}
  with patch.object(drive_lib,'find_folders',side_effect=[['movies-a','movies-b'],['tv-a','tv-b']]),patch.object(drive_lib,'children',side_effect=lambda drive,folder:folders[folder]):
   self.assertEqual({f['id'] for f in scan.remote_files(self.drive)},{'film-a','film-b','episode-a','episode-b'})
 def test_remote_index_failure_precedes_upload_and_deletion(self):
  path=self.file()
  with patch.object(scan,'remote_files',side_effect=RuntimeError('offline')):
   with self.assertRaises(RuntimeError):scan.scan([str(path)],self.drive,str(self.state))
  self.assertTrue(path.exists());self.assertEqual(self.drive.uploaded,[])

class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.messages=[];self.logs=[];self.commands=[];self.choice=0;self.selected='';self.cancel=False;self.closed=0
  self.movies=self.root/'Documents/Kodi Downloads/Movies';self.tv=self.root/'Documents/Kodi Downloads/TV Shows';self.active=self.root/'Documents/Elementum Downloads'
  self.drive=Drive()
  outer=self
  class Dialog:
   def select(self,*args):return outer.choice
   def browseSingle(self,*args,**kwargs):return outer.selected
   def ok(self,*args):outer.messages.append(args)
  class Progress:
   def create(self,*args):pass
   def update(self,*args):pass
   def iscanceled(self):return outer.cancel
   def close(self):outer.closed+=1
  translations={'special://home/':str(self.root/'Documents/home'),
                'special://profile/addon_data/service.kodi.ios.bootstrap/':str(self.root/'state')}
  xbmc=types.SimpleNamespace(Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:False),
    Player=lambda:types.SimpleNamespace(isPlayingVideo=lambda:False),log=lambda message,*args:self.logs.append(message),
    LOGWARNING=2,executebuiltin=self.commands.append)
  self.modules={'xbmc':xbmc,'xbmcgui':types.SimpleNamespace(Dialog=Dialog,DialogProgress=Progress),
   'xbmcaddon':types.SimpleNamespace(Addon=lambda addon:types.SimpleNamespace(getAddonInfo=lambda key:str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch'))),
   'xbmcvfs':types.SimpleNamespace(translatePath=lambda path:translations.get(path,path)),
   'ios_downloaded':types.SimpleNamespace(folders=lambda:[str(self.movies),str(self.tv),str(self.active)],default_completed_folder=lambda kind:[])}
 def tearDown(self):self.tmp.cleanup()
 def run_entry(self):
  with patch.dict(sys.modules,self.modules),patch.object(drive_lib,'client',return_value=(self.drive,'drive')),patch.object(scan,'remote_files',return_value=[]):scan.run()
 def media(self,path):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'file');os.utime(path,(time.time()-1000,)*2);return path
 def test_default_scan_wires_completed_folders_and_reports_verified_cleanup(self):
  path=self.media(self.movies/'Heat.1995.mkv');active=self.media(self.active/'Partial.2020.mkv')
  self.run_entry();self.assertFalse(path.exists());self.assertTrue(active.exists());self.assertTrue(any('1 phone copies removed' in message[1] for message in self.messages));self.assertIn('Container.Refresh',self.commands)
 def test_choosing_accessible_folder_scans_it_without_app_data(self):
  self.choice=1;self.selected=str(self.root/'chosen');path=self.media(Path(self.selected)/'Heat.1995.mkv');cached=self.media(self.root/'Documents/home/userdata/cache/other.mkv')
  self.run_entry();self.assertFalse(path.exists());self.assertTrue(cached.exists())
 def test_stale_elementum_settings_do_not_import_current_preallocated_torrents(self):
  self.choice=1;self.selected=str(self.root/'Documents')
  movie=self.media(self.movies/'Heat.1995.mkv');partial=self.media(self.active/'Preallocated.2020.mkv')
  self.modules['ios_downloaded'].folders=lambda:['','','/old-install/Elementum Downloads']
  self.run_entry();self.assertFalse(movie.exists());self.assertTrue(partial.exists())
  self.assertEqual(len(self.drive.uploaded),1)
 def test_cancel_folder_picker_performs_no_drive_work(self):
  self.choice=-1;self.run_entry();self.assertEqual(self.drive.uploaded,[]);self.assertEqual(self.messages,[])
 def test_cancel_progress_before_hash_preserves_phone_copy(self):
  path=self.media(self.movies/'Heat.1995.mkv');self.cancel=True;self.run_entry();self.assertTrue(path.exists());self.assertEqual(self.drive.uploaded,[]);self.assertGreater(self.closed,0)
 def test_unsigned_drive_retains_phone_files_and_requests_sign_in(self):
  path=self.media(self.movies/'Heat.1995.mkv')
  with patch.dict(sys.modules,self.modules),patch.object(drive_lib,'client',return_value=(None,None)):scan.run()
  self.assertTrue(path.exists());self.assertIn('Sign in',self.messages[0][1])
 def test_runtime_error_logging_omits_exception_urls_and_source_paths(self):
  path=self.media(self.movies/'Heat.1995.mkv')
  with patch.dict(sys.modules,self.modules),patch.object(drive_lib,'client',side_effect=RuntimeError('https://example.invalid/private-token')):scan.run()
  self.assertTrue(path.exists());self.assertTrue(self.logs);self.assertNotIn('private-token',''.join(self.logs));self.assertNotIn(str(path),''.join(self.logs))

if __name__=='__main__':unittest.main()
