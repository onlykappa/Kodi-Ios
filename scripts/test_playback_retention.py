"""Downloaded movie routing, explicit resume/restart and progress retention through actual shared history."""
import json,os,sys,tempfile,unittest,urllib.parse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
import ios_library as page,ios_continue as history,drivelibrary as drive,portrait,library_watch

def params(url):return {k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).items()}
def movie(path=None,title='Inception',year='2010',source='drive'):
 return (path or drive.play_url('D','file'),title,{},dict(mediatype='movie',source=source,year=year),False)

class MovieRows(unittest.TestCase):
 def old(self,**changes):
  value=dict(kind='movie',tmdb_id='27205',title='Inception',year='2010',position=3600,total=8800,played=2000000000,player='umbrella',version={'name':'saved'})
  value.update(changes);return {'items':{'movie:27205::':value}}
 def test_downloaded_movie_finds_the_same_progress_as_continue_watching(self):
  row=page.movie_resume_rows([movie()],lambda *a:{},self.old())[0];values=params(row[0])
  self.assertEqual(values['resume'],'3600.0');self.assertEqual(values['tmdb_id'],'27205');self.assertEqual(values['kind'],'movie');self.assertEqual(values['ask'],'1')
 def test_other_year_does_not_resume_a_different_movie(self):
  row=page.movie_resume_rows([movie(year='2020')],lambda *a:{},self.old())[0]
  self.assertEqual(params(row[0])['resume'],'0')
 def test_completed_movie_does_not_offer_continue(self):
  row=page.movie_resume_rows([movie()],lambda *a:{},self.old(position=8700))[0]
  self.assertEqual(params(row[0])['resume'],'0')
 def test_local_bookmarks_are_batched_and_provider_directories_never_browsed(self):
  rpc=Mock(return_value={'files':[{'file':'/done/a.mkv','resume':{'position':80,'total':500}}]})
  rows=page.movie_resume_rows([movie('/done/a.mkv',source='local'),movie(title='Other')],rpc,{})
  self.assertEqual(params(rows[0][0])['resume'],'80.0')
  self.assertEqual([call.args[0] for call in rpc.call_args_list],['Files.GetDirectory','VideoLibrary.GetMovies'])
 def test_native_scanned_movie_rows_keep_their_existing_path(self):
  row=movie('/library/movie.mkv',source='library');self.assertEqual(page.movie_resume_rows([row],Mock(return_value={}),{}),[row])

class Resolving(unittest.TestCase):
 def play(self,values,old=None,choice=0):
  files={history.STORE:json.dumps(old or {'items':{}})};plugin=Mock();dialog=Mock();dialog.select.return_value=choice
  class Item:
   def __init__(self,label='',path='',**kw):self.path=path;self.properties={};self.tag=Mock()
   def setProperty(self,k,v):self.properties[k]=v
   def getVideoInfoTag(self):return self.tag
  class MemoryFile:
   def __init__(self,path,mode='r'):self.path=path
   def read(self):return files.get(self.path,'')
   def write(self,value):files[self.path]=value
   def close(self):pass
  modules={'xbmc':SimpleNamespace(log=Mock(),LOGWARNING=2),'xbmcgui':SimpleNamespace(ListItem=Item,Dialog=lambda:dialog),
           'xbmcplugin':plugin,'xbmcvfs':SimpleNamespace(File=MemoryFile)}
  with patch.dict(sys.modules,modules):page.play_downloaded(7,values)
  return plugin,json.loads(files[history.STORE]),dialog
 def values(self,**kw):
  value=dict(path=drive.play_url('D','file'),kind='movie',title='Inception',year='2010',resume='3600',total='8800',ask='1');value.update(kw);return value
 def test_continue_applies_the_saved_offset_and_records_the_movie(self):
  plugin,data,dialog=self.play(self.values());item=plugin.setResolvedUrl.call_args.args[2]
  self.assertTrue(plugin.setResolvedUrl.call_args.args[1]);self.assertEqual(item.properties['StartOffset'],'3600.0')
  self.assertEqual(data['items'][data['current']]['position'],3600);self.assertIn('Continue from 1:00:00',dialog.select.call_args.args[1])
 def test_start_from_beginning_clears_the_start_offset_and_saved_seed(self):
  plugin,data,_=self.play(self.values(),choice=1);item=plugin.setResolvedUrl.call_args.args[2]
  self.assertNotIn('StartOffset',item.properties);self.assertEqual(data['items'][data['current']]['position'],0)
 def test_cancel_leaves_history_untouched_and_does_not_resolve_playback(self):
  old={'items':{'other':{'title':'Other'}},'current':'other'};plugin,data,_=self.play(self.values(),old,choice=-1)
  self.assertEqual(data,old);self.assertFalse(plugin.setResolvedUrl.call_args.args[1])
 def test_uncached_movie_gets_a_real_download_link_in_continue_watching(self):
  _,data,_=self.play(self.values(ask='0'));entry=data['items'][data['current']]
  self.assertFalse(entry['tmdb_id']);self.assertTrue(entry['download_key'].startswith('downloaded:'))
  route=params(history.play_url(entry));self.assertEqual(route['path'],drive.play_url('D','file'));self.assertEqual(route['ask'],'0');self.assertEqual(route['resume'],'3600.0')
 def test_existing_umbrella_choice_and_version_are_preserved(self):
  old=MovieRows().old();_,data,_=self.play(self.values(),old)
  self.assertEqual(data['current'],'movie:27205::');entry=data['items'][data['current']]
  self.assertEqual(entry['player'],'umbrella');self.assertEqual(entry['version'],{'name':'saved'})
 def test_new_movie_is_registered_on_the_first_play_even_without_a_resume(self):
  _,data,dialog=self.play(self.values(resume='0'));dialog.select.assert_not_called();self.assertIn(data['current'],data['items'])
 def test_local_movie_validation_uses_the_movie_inventory(self):
  import ios_downloaded
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'movie.mkv';path.write_bytes(b'synthetic fixture')
   with patch.object(ios_downloaded,'completed_files',return_value=[str(path)]) as inventory:
    plugin,_,_=self.play(self.values(path=str(path),resume='0'))
   inventory.assert_called_once_with('movie');self.assertTrue(plugin.setResolvedUrl.call_args.args[1])

class Progress(unittest.TestCase):
 def test_initial_zero_does_not_erase_resume_even_if_opening_is_stopped(self):
  files={history.STORE:json.dumps(dict(items={'movie:1::':dict(kind='movie',tmdb_id='1',title='Movie',position=3600,total=8800)},current='movie:1::'))}
  player=Mock();player.isPlayingVideo.return_value=True;player.getTime.return_value=0;player.getTotalTime.return_value=8800
  read=lambda p:files[p];write=lambda p,v:files.__setitem__(p,v);now=[0]
  tick=portrait.progress_tracker(player,history,read,write,lambda:now[0]);tick();now[0]=5;tick()
  player.isPlayingVideo.return_value=False;tick()
  self.assertEqual(json.loads(files[history.STORE])['items']['movie:1::']['position'],3600)
 def test_landed_resume_is_saved_and_zero_protection_is_bounded(self):
  store=Mock();store.load.return_value={'items':{'x':{'position':3600,'total':8800}},'current':'x'}
  player=Mock();player.isPlayingVideo.return_value=True;player.getTime.return_value=0;player.getTotalTime.return_value=8800;now=[0]
  tick=portrait.progress_tracker(player,store,None,None,lambda:now[0]);tick();store.update.assert_not_called()
  now[0]=21;tick();self.assertEqual(store.update.call_args.args[-2:],(0,8800))
 def test_tv_progress_is_saved_and_not_overwritten_during_handoff_to_paused_kodi(self):
  store=Mock();store.load.return_value={'items':{'x':{'position':120,'total':8800}},'current':'x'}
  player=Mock();player.isPlayingVideo.return_value=True;player.getTime.return_value=120;player.getTotalTime.return_value=8800
  remote=dict(active=1,state=1,position=500,duration=8800,sample_age_s=0);now=[0]
  tick=portrait.progress_tracker(player,store,None,None,lambda:now[0],external=lambda:remote)
  tick();now[0]=11;remote['position']=1800;tick();self.assertEqual(store.update.call_args.args[-2:],(1800,8800))
  now[0]=12;remote['active']=0;tick();self.assertEqual(store.update.call_args.args[-2:],(1800,8800))
  now[0]=22;player.getTime.return_value=1801;tick();self.assertEqual(store.update.call_args.args[-2:],(1801,8800))
 def test_idle_downloaded_movie_page_refreshes_after_progress_changes(self):
  route=page.page_url({'type':'movie'});states=[('',False,0),(route,False,1),(route,True,1),(route,False,2),(route,False,2)]
  i=[-1];refresh=[]
  def wait(seconds):i[0]+=1;return i[0]>=len(states)
  library_watch.watch(lambda:states[i[0]][0],lambda:states[i[0]][1],lambda cmd:refresh.append(i[0]),wait,
    SimpleNamespace(current_params=page.current_params,local_entries=lambda *a:[]),SimpleNamespace(listing=lambda *a,**k:([],None)),
    'unused',clock=lambda:0,progress_signature=lambda:(states[i[0]][2],100))
  self.assertEqual(refresh,[1,3])

if __name__=='__main__':unittest.main()
