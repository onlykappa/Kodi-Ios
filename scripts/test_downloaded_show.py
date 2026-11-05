"""Downloaded shows use seasons, real completed-copy playback and source-aware progress; no poster HTTP in UI."""
import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parents[1]
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch'
sys.path.insert(0,str(WATCH/'resources/lib'))
import ios_library as page,ios_continue as history,ios_downloaded
spec=importlib.util.spec_from_file_location('download_show_drive',ROOT/'migration/bundled-bootstrap/resources/lib/drivelibrary.py')
drive=importlib.util.module_from_spec(spec);spec.loader.exec_module(drive)
spec=importlib.util.spec_from_file_location('download_show_worker',ROOT/'migration/bundled-bootstrap/resources/lib/library_watch.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

def episode(path,season=1,number=1,**extra):
 return (path,'Pilot',{},dict(mediatype='episode',season=str(season),episode=str(number),tvshowtitle='Lanterns',tmdb_id='99',**extra),False)

def params(url):return {key:values[0] for key,values in parse_qs(urlsplit(url).query).items()}

class Item:
 def __init__(self,label='',path='',**kwargs):self.label=label;self.path=path;self.properties={};self.art={};self.tag=Mock()
 def getVideoInfoTag(self):return self.tag
 def setArt(self,art):self.art=art
 def setProperty(self,key,value):self.properties[key]=value
 def addContextMenuItems(self,items):self.context=items
 def setLabel2(self,value):self.label2=value

class Bookmarks(unittest.TestCase):
 def test_latest_unfinished_available_episode_wins_not_next_or_missing_episode(self):
  rows=[episode('/done/1'),episode('/done/2',number=2)]
  data={'items':{'one':dict(kind='episode',tvshowtitle='Lanterns',season=1,episode=2,position=40,total=100,played=10),
                 'missing':dict(kind='episode',tvshowtitle='Lanterns',season=1,episode=9,position=30,total=100,played=20),
                 'other':dict(kind='episode',tvshowtitle='Other',season=1,episode=1,position=80,total=100,played=30)}}
  found=page.resume_rows(rows,'Lanterns',lambda *a:{},data)
  target=page.play_properties(found)
  self.assertEqual(target['KodiIOS.PlayLabel'],'Continue Episode 2')
  self.assertEqual(params(target['KodiIOS.PlayPath'])['path'],'/done/2')
  self.assertEqual(params(target['KodiIOS.PlayPath'])['resume'],'40.0')
 def test_finished_episode_selects_next_available_unwatched(self):
  rows=[episode('/done/1'),episode('/done/2',number=2)]
  def rpc(method,args):return {'files':[{'file':'/done/1','playcount':1},{'file':'/done/2'}]}
  found=page.resume_rows(rows,'Lanterns',rpc,{})
  self.assertEqual(page.play_properties(found)['KodiIOS.PlayLabel'],'Play Episode 2')
 def test_kodi_bookmark_resumes_an_unscanned_local_file(self):
  found=page.resume_rows([episode('/done/1')],'Lanterns',lambda *a:{'files':[{'file':'/done/1','resume':{'position':75,'total':500}}]},{})
  self.assertEqual(page.play_properties(found)['KodiIOS.PlayLabel'],'Continue Episode 1')
  self.assertEqual(params(page.play_properties(found)['KodiIOS.PlayPath'])['resume'],'75.0')
 def test_finished_resume_never_labels_continue(self):
  row=episode('/done/1',resume={'position':98,'total':100},watched=True)
  self.assertEqual(page.play_properties([row])['KodiIOS.PlayLabel'],'Play Episode 1')
 def test_empty_completed_show_has_no_play_target(self):self.assertEqual(page.play_properties([])['KodiIOS.PlayPath'],'')
 def test_bookmarks_batch_local_parent_once_and_never_browse_a_plugin(self):
  rows=[episode('/done/1'),episode('/done/2',number=2),episode(drive.play_url('D','e3'),number=3)]
  rpc=Mock(return_value={});page.resume_rows(rows,'Lanterns',rpc,{})
  self.assertEqual([call.args[0] for call in rpc.call_args_list],['Files.GetDirectory','VideoLibrary.GetEpisodes'])
  self.assertEqual(rpc.call_args_list[0].args[1]['directory'],'/done')
 def test_newer_history_replay_overrides_old_watched_bookmark(self):
  data={'items':{'one':dict(kind='episode',tvshowtitle='Lanterns',season=1,episode=1,position=30,total=100,played=2000000000)}}
  rpc=lambda *a:{'files':[{'file':'/done/1','playcount':1,'lastplayed':'2020-01-01 00:00:00'}]}
  found=page.resume_rows([episode('/done/1')],'Lanterns',rpc,data)
  self.assertEqual(page.play_properties(found)['KodiIOS.PlayLabel'],'Continue Episode 1')
 def test_bad_and_non_finite_resume_values_do_not_enter_kodi(self):
  for value in ('nan','inf','bad',-5,None):self.assertEqual(page.seconds(value),0)
 def test_cloud_collection_reads_every_matching_show_folder_and_filters_loose_tv(self):
  shows=[{'id':'a','title':'Lanterns'},{'id':'b','title':'Lanterns'},{'id':'top','title':'Lanterns','loose':True,'year':''},{'id':'wrong','title':'Other'}]
  eps={'a':[{'id':'e1','title':'Lanterns','name':'S01E01.mkv'}], 'b':[{'id':'e2','title':'Lanterns','name':'S01E02.mkv'}],
       'top':[{'id':'e3','title':'Lanterns','year':'','name':'Lanterns.S01E03.mkv'},{'id':'other','title':'Other','year':'','name':'Other.S01E01.mkv'}]}
  def listing(kind,state,folder=None,**kwargs):return (eps[folder] if folder else shows,'D')
  with patch.object(drive,'listing',side_effect=listing):found=page.cloud_entries({'show':'Lanterns','folder':'a'},drive,'state')
  self.assertEqual([entry['id'] for entry in found],['e1','e2','e3'])
 def test_season_routes_preserve_actual_season_zero_and_show_context(self):
  rows=[episode('/special',season=0),episode('/first',season=1)]
  out=page.season_rows(rows,{'type':'tv','show':'Lanterns','merge':'1'},drive,{},'KEY')
  self.assertEqual([row[1] for row in out],['Specials','Season 1'])
  self.assertEqual([params(row[0])['season'] for row in out],['0','1'])
  self.assertTrue(all(row[4] for row in out));self.assertEqual(out[0][3]['properties']['KodiIOS.DownloadedShow'],'true')

class ShowMetadata(unittest.TestCase):
 def test_full_show_details_logo_genres_year_and_plot_cached_without_foreground_http(self):
  cache={};get=Mock(return_value=json.dumps({'id':99,'overview':'Show plot','vote_average':7.4,'first_air_date':'2026-08-16',
       'genres':[{'name':'Drama'},{'name':'Mystery'}],'images':{'logos':[{'iso_639_1':None,'file_path':'/neutral.png','vote_average':9},
                                                               {'iso_639_1':'en','file_path':'/english.png','vote_average':1}]}}).encode())
  self.assertEqual(drive.show_details(99,'KEY',cache,get,cached_only=True),{});get.assert_not_called()
  details=drive.show_details(99,'KEY',cache,get)
  self.assertEqual(details['genres'],['Drama','Mystery']);self.assertEqual(details['year'],'2026')
  self.assertEqual(details['plot'],'Show plot');self.assertTrue(details['clearlogo'].endswith('/english.png'))
  self.assertEqual(drive.show_details(99,'KEY',cache,None,cached_only=True),details)
  self.assertEqual(get.call_count,1)
 def test_failed_details_lookup_is_retried_later(self):
  cache={};get=Mock(side_effect=OSError('offline'))
  self.assertEqual(drive.show_details(99,'KEY',cache,get),{});self.assertEqual(cache,{})

class ResumeRefresh(unittest.TestCase):
 def test_resume_revision_refreshes_steady_membership_once_after_playback_and_never_reads_offpage(self):
  show=page.page_url({'type':'tv','local':'1','show':'Lanterns'})
  states=[('',False,1),(show,False,1),(show,True,2),(show,False,2),(show,False,2),('',False,3)]
  index=[-1];reads=[];refresh=[]
  def wait(seconds):index[0]+=1;return index[0]>=len(states)
  def progress():reads.append(index[0]);return (states[index[0]][2],100)
  worker.watch(lambda:states[index[0]][0],lambda:states[index[0]][1],lambda command:refresh.append(index[0]),wait,
               SimpleNamespace(current_params=page.current_params,local_entries=lambda *a:[]),SimpleNamespace(listing=lambda *a,**k:([],None)),
               'unused',clock=lambda:0,progress_signature=progress)
  self.assertEqual(reads,[1,3,4]);self.assertEqual(refresh,[1,3])
 def test_progress_stamp_detects_same_size_history_changes_and_missing_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'continue.json';self.assertIsNone(worker.progress_stamp(str(path)))
   path.write_text('{}');first=worker.progress_stamp(str(path))
   os.utime(path,ns=(first[0]+1000000,first[0]+1000000));second=worker.progress_stamp(str(path))
   self.assertNotEqual(first,second);self.assertEqual(first[1],second[1])

class Directory(unittest.TestCase):
 def render(self,route):
  self.plugin=Mock();self.files={history.STORE:json.dumps({'items':{'resume':dict(kind='episode',tmdb_id='99',tvshowtitle='Lanterns',season='1',episode='2',position=120,total=600,played=10)}})}
  class MemoryFile:
   def __init__(inner,path,mode='r'):inner.path=path
   def read(inner):return self.files.get(inner.path,'')
   def close(inner):pass
  xbmc=SimpleNamespace(getCondVisibility=lambda condition:False,executeJSONRPC=lambda request:json.dumps({'result':{}}))
  modules={'xbmc':xbmc,'xbmcgui':SimpleNamespace(ListItem=Item,Dialog=Mock()),'xbmcplugin':self.plugin,
           'xbmcaddon':SimpleNamespace(Addon=lambda *a:SimpleNamespace(getAddonInfo=lambda key:'fixture')),
           'xbmcvfs':SimpleNamespace(translatePath=lambda path:path,File=MemoryFile),'drivelibrary':drive}
  cache={'tv:lanterns:':{'tmdb_id':'99','fanart':'fan.jpg','poster':'poster.jpg'},
         'show:99':{'plot':'Show plot','genres':['Drama'],'rating':7.4,'year':'2026','clearlogo':'logo.png'},
         'season:99:1':{'1':{'title':'Pilot'},'2':{'title':'Trust Fall'}},'season:99:2':{'1':{'title':'Next season'}}}
  local=[dict(title='Lanterns',year='',season='1',episode='1',path='/done/one.mkv'),dict(title='Lanterns',year='',season='1',episode='2',path='/done/two.mkv'),
         dict(title='Lanterns',year='',season='2',episode='1',path='/done/three.mkv')]
  with patch.dict(sys.modules,modules),patch.object(page,'local_entries',return_value=local),patch.object(drive,'tmdb_key',return_value='KEY'),patch.object(drive,'load_json',return_value=cache),patch.object(drive,'save_json') as save:
   page.directory(7,route);save.assert_not_called()
  return self.plugin.addDirectoryItem.call_args_list
 def test_parent_show_is_seasons_with_rich_metadata_and_continue_action(self):
  calls=self.render({'type':'tv','local':'1','show':'Lanterns'})
  self.plugin.setContent.assert_called_once_with(7,'seasons')
  self.assertEqual([call.args[2].label for call in calls],['Season 1','Season 2'])
  item=calls[0].args[2];self.assertEqual(item.properties['KodiIOS.PlayLabel'],'Continue Episode 2')
  self.assertEqual(item.art['tvshow.clearlogo'],'logo.png');item.tag.setGenres.assert_called_once_with(['Drama'])
  self.plugin.setProperty.assert_any_call(7,'KodiIOS.ShowPlot','Show plot')
  self.assertFalse(any(call.args[2].label=='Refresh Library' for call in calls))
 def test_selected_season_lists_only_real_playable_episodes_without_refresh_tile(self):
  calls=self.render({'type':'tv','local':'1','show':'Lanterns','season':'1'})
  self.plugin.setContent.assert_called_once_with(7,'episodes')
  self.assertEqual([params(call.args[1])['path'] for call in calls],['/done/one.mkv','/done/two.mkv'])
  self.assertEqual([call.args[2].label for call in calls],['Pilot','Trust Fall'])
  self.assertTrue(all(not call.kwargs['isFolder'] and call.args[2].properties['IsPlayable']=='true' for call in calls))

class Playback(unittest.TestCase):
 def run_play(self,values,data=None):
  files={history.STORE:json.dumps(data or {'items':{}})};plugin=Mock()
  class MemoryFile:
   def __init__(inner,path,mode='r'):inner.path=path
   def read(inner):return files.get(inner.path,'')
   def write(inner,value):files[inner.path]=value
   def close(inner):pass
  modules={'xbmc':SimpleNamespace(log=Mock(),LOGWARNING=2),'xbmcgui':SimpleNamespace(ListItem=Item),'xbmcplugin':plugin,
           'xbmcvfs':SimpleNamespace(File=MemoryFile)}
  with patch.dict(sys.modules,modules):page.play_downloaded(7,values)
  return plugin,json.loads(files[history.STORE])
 def test_provider_or_external_url_cannot_be_resolved_as_a_download(self):
  for path in ('https://example.invalid/movie.mkv','plugin://plugin.video.elementum/movie/99/play','plugin://plugin.googledrive/?action=browse&item_id=x'):
   plugin,data=self.run_play({'path':path});self.assertFalse(plugin.setResolvedUrl.call_args.args[1])
 def test_drive_copy_resumes_and_preserves_existing_umbrella_choice(self):
  old={'items':{'episode:99:1:2':dict(kind='episode',tmdb_id='99',tvshowtitle='Lanterns',season='1',episode='2',player='umbrella',version={'name':'remembered'},position=50,total=600)},'current':'unrelated'}
  path=drive.play_url('D','e2');plugin,data=self.run_play(dict(path=path,resume='120',total='600',tmdb_id='99',season='1',episode='2',show='Lanterns',title='Trust Fall'),old)
  call=plugin.setResolvedUrl.call_args;self.assertTrue(call.args[1]);item=call.args[2]
  self.assertEqual(item.path,path);self.assertEqual(item.properties['StartOffset'],'120.0')
  item.tag.setResumePoint.assert_called_once_with(120.0,600.0)
  self.assertEqual(data['current'],'episode:99:1:2');self.assertEqual(data['items'][data['current']]['player'],'umbrella')
  self.assertEqual(data['items'][data['current']]['version'],{'name':'remembered'})
 def test_unknown_tmdb_id_clears_previous_history_current_without_inventing_provider_link(self):
  old={'items':{'unrelated':{'title':'Other'}},'current':'unrelated'}
  plugin,data=self.run_play({'path':drive.play_url('D','e1')},old)
  self.assertTrue(plugin.setResolvedUrl.call_args.args[1]);self.assertNotIn('current',data)
  self.assertEqual(data['items'],old['items'])
 def test_local_path_must_still_be_in_verified_completed_inventory(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'movie.mkv';path.write_bytes(b'video')
   with patch.object(ios_downloaded,'completed_files',return_value=[]):
    plugin,_=self.run_play({'path':str(path)});self.assertFalse(plugin.setResolvedUrl.call_args.args[1])
   with patch.object(ios_downloaded,'completed_files',return_value=[str(path)]):
    plugin,_=self.run_play({'path':str(path)});self.assertTrue(plugin.setResolvedUrl.call_args.args[1])

if __name__=='__main__':unittest.main()
