"""Continue Watching checks completed copies before reusing a provider; failures must never start a new torrent."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
BOOT=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path[:0]=[str(WATCH),str(BOOT)]
import ios_continue as history,ios_downloaded as downloads,ios_watch_dialog as watch,drivelibrary

TITLE='The Nightmare Before Christmas'
RELEASE=TITLE+' 1993 1080p BluRay HEVC x265 5.1 BONE.mkv'

class CompletedFiles(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.done=self.root/'Movies';self.done.mkdir();self.active=self.root/'Elementum Downloads';self.active.mkdir()
 def file(self,folder,name=RELEASE,size=10):
  p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'x'*size);return str(p)
 def test_screenshot_release_plays_completed_file_and_rejects_empty_files(self):
  path=self.file(self.done)
  self.assertEqual(downloads.find_downloaded('movie',TITLE,'1993',folder_list=[str(self.done),'',str(self.active)]),path)
  Path(path).write_bytes(b'');self.assertIsNone(downloads.find([str(self.done)],'movie',TITLE,'1993'))
 def test_missing_completed_slot_does_not_reclassify_active_torrents(self):
  self.file(self.active)
  self.assertIsNone(downloads.find_downloaded('movie',TITLE,'1993',folder_list=[str(self.done),'',str(self.active)],names=set()))
 def test_overlapping_completed_and_active_folders_still_require_completion(self):
  self.file(self.active)
  self.assertIsNone(downloads.find_downloaded('movie',TITLE,'1993',folder_list=[str(self.active),'',str(self.active)],names=set()))
 def test_movies_do_not_search_the_completed_show_folder(self):
  self.file(self.done)
  self.assertIsNone(downloads.find_downloaded('movie',TITLE,'1993',folder_list=['',str(self.done),'']))
 def test_smaller_finished_version_wins_over_larger_unfinished_version(self):
  large=self.file(self.active/'unfinished');small=self.file(self.active/'finished',size=5)
  with patch.object(downloads,'finished_only',side_effect=lambda path,root,names:'/finished/' in path):
   self.assertEqual(downloads.find_downloaded('movie',TITLE,'1993',folder_list=['','',str(self.active)],names={'finished'}),small)
  self.assertNotEqual(large,small)
 def test_progress_must_be_fully_complete_and_unknown_is_not_absence(self):
  data=json.dumps([{'name':'partial','progress':99.99},{'name':'done','progress':100}]).encode()
  self.assertEqual(downloads.finished_names(lambda url:data),{'done'})
  with self.assertRaises(LookupError):downloads.finished_names(lambda url:b'not json',strict=True)
 def test_similar_titles_wrong_years_and_sequels_do_not_match(self):
  self.assertFalse(downloads.matches(RELEASE,'movie','Christmas','1993'))
  self.assertFalse(downloads.matches('The.Dark.Knight.Rises.2012.mkv','movie','The Dark Knight'))
  self.assertFalse(downloads.matches(RELEASE,'movie',TITLE,'2003'))
 def test_empty_elementum_settings_keep_three_slots(self):
  settings=SimpleNamespace(getSetting=lambda key:{'completed_movies_path':'/done','download_path':'/active'}.get(key,''))
  with patch.dict(sys.modules,{'xbmcaddon':SimpleNamespace(Addon=lambda id:settings),'xbmcvfs':SimpleNamespace(translatePath=lambda path:path)}):
   self.assertEqual(downloads.folders(),['/done','','/active'])
 def test_current_app_downloads_survive_stale_or_missing_elementum_settings(self):
  docs=self.root/'Documents';home=docs/'Kodi';home.mkdir(parents=True)
  target=docs/'Kodi Downloads/Movies';target.mkdir(parents=True);path=self.file(target)
  settings=SimpleNamespace(getSetting=lambda key:'/old/container/Movies' if key=='completed_movies_path' else '')
  with patch.dict(sys.modules,{'xbmcaddon':SimpleNamespace(Addon=lambda id:settings),'xbmcvfs':SimpleNamespace(translatePath=lambda p:str(home) if p=='special://home/' else p)}):
   self.assertEqual(downloads.find_downloaded('movie',TITLE,'1993'),path)

class LocalMovie:
 is_local=True;file='';kodi_file=None
 def __init__(self,item=None):self.item=item
class LocalEpisode(LocalMovie):pass

class ResumeRouting(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.done=self.root/'Movies';self.done.mkdir();self.files={};self.props={};self.logs=[];self.drive=False
  self.enabled={'plugin.video.elementum','plugin.video.umbrella'}
  self.dialog=Mock();self.dialog.select.return_value=0
  self.engine=SimpleNamespace(file='ios.elementum.json',is_local=False,kodi_file=None)
  self.umbrella=SimpleNamespace(file='ios.umbrella.json',is_local=False,kodi_file=None)
  self.details=SimpleNamespace(infolabels={'title':TITLE,'year':1993},art={})
  self.dictionary=SimpleNamespace(details=self.details)
  self.player=SimpleNamespace(tmdb_type='movie',tmdb_id='9479',season='',episode='',details=self.details,
                              dictionary=self.dictionary,player_items=SimpleNamespace(items_play=[self.engine,self.umbrella]))
  history.record(self.player,self.read,self.write,choice='umbrella')
  self.settings=Mock();self.settings.getSettingBool.return_value=True
  self.settings.getSetting.side_effect=lambda key:str(self.done) if key=='completed_movies_path' else ''
  self.home=SimpleNamespace(clearProperty=lambda k:self.props.pop(k,None),setProperty=self.props.__setitem__)
  self.xbmc=SimpleNamespace(LOGINFO=1,LOGWARNING=2,log=lambda text,level:self.logs.append(text),getCondVisibility=self.installed)
  self.vfs=SimpleNamespace(File=lambda path,*a:SimpleNamespace(read=lambda:self.read(path),write=lambda text:self.write(path,text),close=lambda:None),
                           exists=lambda path:Path(path).exists(),mkdirs=lambda path:None,translatePath=self.translate)
  mods={'xbmc':self.xbmc,'xbmcgui':SimpleNamespace(Window=lambda id:self.home,Dialog=lambda:self.dialog,ListItem=Mock()),
        'xbmcaddon':SimpleNamespace(Addon=lambda id:self.settings),'xbmcvfs':self.vfs,
        'ios_continue':history,'tmdbhelper.lib.player.dialog.item.kodi':SimpleNamespace(PlayerItemLocalMovie=LocalMovie,PlayerItemLocalEpisode=LocalEpisode)}
  p=patch.dict(sys.modules,mods);p.start();self.addCleanup(p.stop)
  p=patch.object(sys,'argv',['plugin://helper','1','?info=play&tmdb_type=movie&tmdb_id=9479&ios_continue=1']);p.start();self.addCleanup(p.stop)
 def read(self,path):return self.files.get(path,'')
 def write(self,path,text):self.files[path]=text
 def saved(self):return json.loads(self.files[history.STORE])['items']['movie:9479::']
 def installed(self,condition):
  if condition=='System.AddonIsEnabled(plugin.googledrive)':return self.drive
  return any(condition=='System.AddonIsEnabled('+id+')' for id in self.enabled)
 def translate(self,path):
  if path.startswith('special://xbmc/addons/'):return str(BOOT)
  if path.startswith('special://profile/addon_data/service.'):return str(self.root/'state')
  return path
 def test_downloaded_file_wins_before_provider_and_has_resolver_metadata(self):
  path=self.done/RELEASE;path.write_bytes(b'completed')
  self.props[watch.RESUME_PROPERTY]='stale release from another title'
  item=watch.choose_player(self.player)
  self.assertEqual(item.actions,str(path));self.assertIs(item.item,self.dictionary)
  self.assertIs(item.item.details,self.details)  # Real TMDb Helper PlayerResolver requires this, not a dict.
  self.dialog.select.assert_not_called();self.assertEqual(self.saved()['player'],'umbrella')
  self.assertEqual(self.saved()['playback_source'],'local');self.assertNotIn(watch.RESUME_PROPERTY,self.props)
 def test_drive_download_wins_without_elementum_or_umbrella_selection(self):
  self.drive=True
  entries=[{'id':'completed-id','title':TITLE,'year':'1993','size':100}]
  with patch.object(drivelibrary,'listing',return_value=(entries,'account')):
   item=watch.choose_player(self.player)
  self.assertIn('plugin://plugin.googledrive/',item.actions);self.assertIn('item_id=completed-id',item.actions)
  self.assertIs(item.item,self.dictionary);self.dialog.select.assert_not_called()
  self.assertEqual((self.saved()['player'],self.saved()['playback_source']),('umbrella','drive'))
 def test_drive_lookup_failure_never_reuses_elementum(self):
  self.drive=True;history.record(self.player,self.read,self.write,choice='elementum')
  with patch.object(drivelibrary,'listing',side_effect=OSError('offline')):
   self.assertIsNone(watch.choose_player(self.player))
  self.dialog.select.assert_not_called();self.dialog.ok.assert_called_once()
 def test_downloaded_resolver_retry_stops_instead_of_redownloading(self):
  (self.done/RELEASE).write_bytes(b'completed')
  self.assertIsNotNone(watch.choose_player(self.player))
  self.assertIsNone(watch.choose_player(self.player));self.dialog.select.assert_not_called()
 def test_umbrella_origin_is_reused_without_a_player_question(self):
  self.assertIs(watch.choose_player(self.player),self.umbrella);self.dialog.select.assert_not_called()
 def test_unavailable_saved_umbrella_never_substitutes_elementum(self):
  self.enabled.remove('plugin.video.umbrella')
  self.assertIsNone(watch.choose_player(self.player));self.dialog.select.assert_not_called();self.dialog.ok.assert_called_once()
  self.assertEqual(self.saved()['player'],'umbrella')
 def test_lookup_error_stops_instead_of_redownloading(self):
  with patch.object(downloads,'completed_copy',side_effect=OSError('offline')):
   self.assertIsNone(watch.choose_player(self.player))
  self.dialog.select.assert_not_called();self.dialog.ok.assert_called_once();self.assertEqual(self.saved()['player'],'umbrella')
 def test_missing_previously_local_copy_does_not_start_a_torrent(self):
  history.record(self.player,self.read,self.write,choice='local')
  self.assertIsNone(watch.choose_player(self.player));self.dialog.select.assert_not_called()
 def test_resolver_retry_does_not_select_another_source(self):
  self.assertIs(watch.choose_player(self.player),self.umbrella)
  self.assertIsNone(watch.choose_player(self.player));self.dialog.select.assert_not_called()
 def test_explicit_normal_play_can_choose_a_new_provider(self):
  sys.argv[2]='?info=play&tmdb_type=movie&tmdb_id=9479'
  self.assertIs(watch.choose_player(self.player),self.engine);self.dialog.select.assert_called_once()
  self.assertEqual(self.saved()['player'],'elementum')

if __name__=='__main__':unittest.main()
