"""Bug 4: real add-on dispatch/navigation and visible-page update behavior, without a Kodi GUI/network."""
import importlib.util,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parents[1]
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch'
sys.path.insert(0,str(WATCH/'resources/lib'))
import ios_library as page

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

entry=load('watch_entry',WATCH/'default.py')
worker=load('library_watch',ROOT/'migration/bundled-bootstrap/resources/lib/library_watch.py')
drive_lib=load('drive_library_fixture',ROOT/'migration/bundled-bootstrap/resources/lib/drivelibrary.py')
LIBRARY=page.page_url({'type':'movie'})

class Navigation(unittest.TestCase):
 def modules(self):
  self.dialog=mock.Mock();self.plugin=mock.Mock();self.gui=SimpleNamespace(ListItem=mock.Mock(side_effect=lambda **kw:mock.Mock(**{'label':kw.get('label')})),Dialog=lambda:self.dialog)
  self.xbmc=SimpleNamespace(getCondVisibility=mock.Mock(return_value=False),executebuiltin=mock.Mock(),getInfoLabel=mock.Mock(return_value=LIBRARY))
  return {'xbmc':self.xbmc,'xbmcgui':self.gui,'xbmcplugin':self.plugin,'xbmcaddon':mock.Mock()}
 def test_empty_root_and_parent_url_list_movies_tv_without_a_media_error(self):
  for query in ('','?','?content_type=video'):
   with self.subTest(query=query),mock.patch.dict(sys.modules,self.modules()):
    entry.run([page.ME,'7',query])
    calls=self.plugin.addDirectoryItem.call_args_list
    self.assertEqual([c.args[2].label for c in calls],['Movies','TV Shows'])
    self.assertEqual([parse_qs(urlsplit(c.args[1]).query)['type'][0] for c in calls],['movie','tv'])
    self.assertTrue(all(c.kwargs['isFolder'] for c in calls));self.dialog.ok.assert_not_called()
    self.plugin.endOfDirectory.assert_called_once_with(7,cacheToDisc=False)
 def test_refresh_dispatch_does_not_run_watch_options_or_list_a_fake_movie(self):
  with mock.patch.dict(sys.modules,self.modules()):
   entry.run([page.ME,'-1','?action=library_refresh'])
   self.xbmc.executebuiltin.assert_called_once_with('Container.Refresh('+page.page_url({'type':'movie','fresh':'1'})+')')
   self.dialog.ok.assert_not_called();self.plugin.addDirectoryItem.assert_not_called()
 def test_refresh_is_scoped_to_library_and_preserves_folder_selection(self):
  for path in ('plugin://untrusted/?action=library&type=movie',page.ME+'?action=continue',
               'https://plugin.video.kodi.ios.watch/?action=library',page.ME+'?action=library&action=play'):
   calls=[];page.refresh_current(lambda key:path,calls.append);self.assertEqual(calls,[])
  path=page.page_url({'type':'tv','folder':'remote id','show':'Show),RunScript(arbitrary)','loose':'1','year':'2024','unexpected':'discard','fresh':'0'})
  calls=[];page.refresh_current(lambda key:path,calls.append)
  self.assertEqual(len(calls),1);self.assertNotIn('unexpected',calls[0]);self.assertNotIn('fresh=0',calls[0]);self.assertIn('fresh=1',calls[0])
  self.assertIn('folder=remote+id',calls[0]);self.assertNotIn('Show),RunScript',calls[0])
 def test_legacy_incomplete_media_links_remain_an_explicit_error(self):
  with mock.patch.dict(sys.modules,self.modules()):
   entry.run([page.ME,'7','?kind=movie'])
   self.dialog.ok.assert_called_once();self.plugin.addDirectoryItem.assert_not_called()
 def test_settings_refresh_invalidates_cache_off_page_without_opening_a_movie(self):
  mods=self.modules();self.xbmc.getInfoLabel.return_value='plugin://other/'
  self.gui.NOTIFICATION_INFO='info';invalidate=mock.Mock()
  mods.update({'xbmcvfs':SimpleNamespace(translatePath=lambda path:'/state'),
               'driveupload':SimpleNamespace(invalidate_library=invalidate)})
  with mock.patch.dict(sys.modules,mods):entry.run([page.ME,'-1','?action=library_refresh&all=1'])
  invalidate.assert_called_once_with('/state');self.xbmc.executebuiltin.assert_not_called()
  self.plugin.addDirectoryItem.assert_not_called();self.dialog.notification.assert_called_once();self.dialog.ok.assert_not_called()

class VisibleLibrary(unittest.TestCase):
 def simulate(self,paths,busy=None,locals=None,remote=None):
  state={'tick':-1};calls=[];busy=busy or [False]*len(paths)
  def wait(seconds):state['tick']+=1;return state['tick']>=len(paths)
  info=lambda:paths[state['tick']]
  drive=SimpleNamespace(listing=mock.Mock(side_effect=remote) if remote else mock.Mock(return_value=([],None)))
  local=mock.Mock(side_effect=lambda kind,lib:(locals[state['tick']] if locals is not None else []))
  facade=SimpleNamespace(current_params=page.current_params,local_entries=local)
  with tempfile.TemporaryDirectory() as tmp:
   worker.watch(info,lambda:busy[state['tick']],calls.append,wait,facade,drive,tmp,clock=lambda:state['tick']*5)
  return calls,local,drive.listing
 def test_no_listing_or_network_work_off_page_or_while_busy(self):
  calls,local,cloud=self.simulate(['',page.ME+'?action=continue',LIBRARY,LIBRARY],[False,False,True,True])
  self.assertEqual(calls,[]);local.assert_not_called();cloud.assert_not_called()
 def test_initial_entry_refreshes_cached_empty_page_once_and_completed_local_file_refreshes_again(self):
  calls,local,cloud=self.simulate([LIBRARY]*4,locals=[[],[],[{'path':'/completed.mkv'}],[{'path':'/completed.mkv'}]])
  self.assertEqual(calls,['Container.Refresh','Container.Refresh']);self.assertEqual(cloud.call_count,1)
 def test_a_busy_refresh_tick_does_not_erase_the_membership_baseline(self):
  calls,local,cloud=self.simulate([LIBRARY]*4,busy=[False,True,False,False])
  self.assertEqual(calls,['Container.Refresh']);self.assertEqual(cloud.call_count,1)
 def test_drive_poll_is_bounded_and_new_cloud_membership_refreshes(self):
  calls,local,cloud=self.simulate([LIBRARY]*8,remote=[([], 'drive'),([{'id':'new'}],'drive')])
  self.assertEqual(cloud.call_count,2);self.assertEqual(calls,['Container.Refresh','Container.Refresh'])
  self.assertTrue(all(call.kwargs=={'strict':True,'fresh':True} for call in cloud.call_args_list))
 def test_offline_drive_does_not_prevent_completed_phone_discovery(self):
  calls,local,cloud=self.simulate([LIBRARY]*3,locals=[[],[{'path':'/completed.mkv'}],[{'path':'/completed.mkv'}]],remote=[OSError('offline')])
  self.assertEqual(calls,['Container.Refresh','Container.Refresh']);self.assertEqual(cloud.call_count,1)
 def test_local_show_directory_never_queries_drive(self):
  path=page.page_url({'type':'tv','local':'1','show':'Lanterns'})
  calls,local,cloud=self.simulate([path]*3)
  self.assertEqual(calls,['Container.Refresh']);cloud.assert_not_called()
 def test_leaving_library_during_a_network_request_does_not_refresh_new_page(self):
  path=[LIBRARY];refresh=[];waits=iter([False,True])
  def listing(*args,**kwargs):path[0]='plugin://other/';return [],None
  worker.watch(lambda:path[0],lambda:False,refresh.append,lambda seconds:next(waits),
               SimpleNamespace(current_params=page.current_params,local_entries=lambda *a:[]),
               SimpleNamespace(listing=listing),'unused',clock=lambda:0)
  self.assertEqual(refresh,[])

class ActualDirectory(unittest.TestCase):
 def render(self,files=(),drive_enabled=False,drive_failure=False,params=None):
  import ios_downloaded
  self.items=[];self.dialog=mock.Mock();self.plugin=mock.Mock();self.logs=[]
  def item(**kwargs):
   value=mock.Mock();value.label=kwargs.get('label');return value
  def add(handle,path,li,isFolder=False):self.items.append((path,li,isFolder))
  self.plugin.addDirectoryItem.side_effect=add
  listing=mock.Mock(side_effect=OSError('private URL must not be logged')) if drive_failure else mock.Mock(return_value=([],None))
  fake_drive=SimpleNamespace(parse=drive_lib.parse,tmdb_key=lambda path:'',load_json=lambda path,default:default,
    save_json=mock.Mock(),artwork=mock.Mock(return_value={}),show_details=lambda *a,**k:{},listing=listing)
  self.xbmc=SimpleNamespace(executeJSONRPC=lambda payload:'{"result":{}}',getCondVisibility=lambda condition:drive_enabled,
    log=lambda text,level:self.logs.append(text),LOGWARNING=2)
  with tempfile.TemporaryDirectory() as tmp:
   mods={'xbmc':self.xbmc,'xbmcaddon':SimpleNamespace(Addon=lambda id:SimpleNamespace(getAddonInfo=lambda key:'/helper')),
         'xbmcgui':SimpleNamespace(ListItem=item,Dialog=lambda:self.dialog,NOTIFICATION_WARNING='warning'),
         'xbmcplugin':self.plugin,'xbmcvfs':SimpleNamespace(translatePath=lambda path:tmp if path==page.STATE else '/boot'),
         'drivelibrary':fake_drive}
   with mock.patch.dict(sys.modules,mods),mock.patch.object(ios_downloaded,'completed_files',return_value=files):
    page.directory(7,params or {'action':'library','type':'movie'})
  return listing
 def test_phone_download_is_rendered_when_drive_is_disabled_or_signed_out(self):
  for enabled in (False,True):
   with self.subTest(drive_enabled=enabled):
    listing=self.render(['/phone/Kodi Downloads/Movies/Heat.1995.mkv'],drive_enabled=enabled)
    self.assertEqual([li.label for path,li,folder in self.items],['Heat','Refresh Library'])
    self.assertEqual(parse_qs(urlsplit(self.items[0][0]).query)['path'],['/phone/Kodi Downloads/Movies/Heat.1995.mkv']);self.assertFalse(self.items[0][2])
    self.items[0][1].setProperty.assert_called_with('IsPlayable','true')
    self.items[0][1].getVideoInfoTag.return_value.setYear.assert_called_once_with(1995)
    self.items[0][1].addContextMenuItems.assert_called_once_with([('Refresh Library',page.REFRESH)])
    self.assertEqual(listing.call_count,int(enabled));self.dialog.ok.assert_not_called()
 def test_drive_failure_preserves_phone_items_and_does_not_publish_private_error_text(self):
  self.render(['/phone/Kodi Downloads/Movies/Heat.1995.mkv'],drive_enabled=True,drive_failure=True)
  self.assertEqual(self.items[0][1].label,'Heat');self.dialog.notification.assert_called_once()
  self.assertFalse(any('private URL' in text for text in self.logs));self.plugin.endOfDirectory.assert_called_once_with(7,cacheToDisc=False)
 def test_empty_library_still_renders_a_working_nonplayable_refresh(self):
  self.render()
  self.assertEqual(len(self.items),1);path,li,folder=self.items[0]
  self.assertEqual(li.label,'Refresh Library');self.assertTrue(folder)
  li.setProperty.assert_called_once_with('IsPlayable','false')
  self.assertEqual(parse_qs(urlsplit(path).query),{'action':['library'],'type':['movie'],'fresh':['1']})
  self.plugin.setContent.assert_called_once_with(7,'movies')
 def test_local_tv_episode_renders_resume_safe_exact_path_and_zero_season(self):
  file='/phone/Kodi Downloads/TV Shows/Lanterns/Season 0/S00E02.mkv'
  self.render([file],params={'action':'library','type':'tv','local':'1','show':'Lanterns','fresh':'1','season':'0'})
  self.assertEqual(parse_qs(urlsplit(self.items[0][0]).query)['path'],[file]);self.assertFalse(self.items[0][2]);tag=self.items[0][1].getVideoInfoTag.return_value
  tag.setMediaType.assert_called_once_with('episode');tag.setSeason.assert_called_once_with(0);tag.setEpisode.assert_called_once_with(2)
  self.plugin.setContent.assert_called_once_with(7,'episodes')
  self.assertEqual(len(self.items),1)  # no Refresh folder drawn as a fake episode
 def test_local_show_root_lists_seasons_with_working_downloaded_play_properties(self):
  file='/phone/Kodi Downloads/TV Shows/Lanterns/Season 1/S01E01.mkv'
  self.render([file],params={'action':'library','type':'tv','local':'1','show':'Lanterns'})
  self.assertEqual(len(self.items),1);path,item,folder=self.items[0]
  self.assertTrue(folder);self.assertEqual(parse_qs(urlsplit(path).query)['season'],['1'])
  self.plugin.setContent.assert_called_once_with(7,'seasons')
  properties={call.args[1]:call.args[2] for call in self.plugin.setProperty.call_args_list}
  self.assertEqual(properties['KodiIOS.DownloadedShow'],'true');self.assertEqual(properties['KodiIOS.PlayLabel'],'Play Episode 1')
  self.assertEqual(parse_qs(urlsplit(properties['KodiIOS.PlayPath']).query)['path'],[file])

if __name__=='__main__':unittest.main()
