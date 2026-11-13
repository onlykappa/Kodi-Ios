import importlib.util,json,unittest
from pathlib import Path
from types import SimpleNamespace
path=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_continue.py'
spec=importlib.util.spec_from_file_location('ios_continue',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ContinueTests(unittest.TestCase):
 def setUp(self):
  self.files={};self.read=lambda p:self.files.get(p,'');self.write=self.files.__setitem__;self.t=1000
 def player(self,kind,tmdb,season=None,episode=None,title='Pilot',show=''):
  details=SimpleNamespace(infolabels={'title':title,'tvshowtitle':show,'year':2020},art={'fanart':'f.jpg','poster':'p.jpg','clearart':'x'})
  return SimpleNamespace(tmdb_type=kind,tmdb_id=tmdb,season=season,episode=episode,details=details)
 def record(self,*a,**k):
  self.t+=10;return module.record(self.player(*a,**k),self.read,self.write,lambda:self.t)
 def data(self):return json.loads(self.files[module.STORE])
 def test_started_titles_listed_newest_first_movies_and_episodes(self):
  self.record('movie','1',title='Movie');module.update(self.read,self.write,300,6000,lambda:self.t)
  self.record('tv','2','1','3',title='Ep',show='Show');module.update(self.read,self.write,100,2400,lambda:self.t+5)
  rows=module.entries(self.data())
  self.assertEqual([r['kind'] for r in rows],['episode','movie'])
  self.assertEqual([r['kind'] for r in module.entries(self.data(),'movie')],['movie'])
  self.assertEqual(module.play_url(rows[0]),'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=2&season=1&episode=3&ios_continue=1')
  self.assertNotIn('clearart',rows[1]['art'])
 def test_not_started_is_hidden_and_finished_is_dropped(self):
  self.record('movie','1');self.assertEqual(module.entries(self.data()),[])
  module.update(self.read,self.write,5900,6000);module.stopped(self.read,self.write)
  self.assertEqual(self.data()['items'],{})
 def test_a_finished_drive_episode_is_remembered_as_watched(self):
  # ISSUE-197: Free Up Space › Watched episodes needs what was watched; a finished title leaves Continue Watching.
  data={'current':'k','items':{'k':{'kind':'episode','tmdb_id':'31910','position':1390,'total':1400,
        'path':'plugin://plugin.video.kodi.ios.watch/?action=library_play&path=plugin%3A%2F%2Fplugin.googledrive%2F%3Faction%3Dplay%26item_id%3De7'},
        'n':{'kind':'movie','tmdb_id':'1','position':10,'total':100,'download_path':'/phone/Kodi Downloads/Movies/Heat.mkv'}}}
  self.files[module.STORE]=json.dumps(data)
  module.stopped(self.read,self.write,lambda:5)
  self.assertEqual(module.watched_set(self.data()),{'e7'})
  d=self.data();d['current']='n';d['items']['n']['position']=99;self.files[module.STORE]=json.dumps(d)
  module.stopped(self.read,self.write,lambda:6)
  self.assertEqual(module.watched_set(self.data()),{'e7','/phone/Kodi Downloads/Movies/Heat.mkv'})
 def test_unfinished_stays_after_stop(self):
  self.record('movie','1');module.update(self.read,self.write,3000,6000);module.stopped(self.read,self.write)
  self.assertEqual(len(module.entries(self.data())),1)
 def test_library_items_merge_by_last_played(self):
  self.record('movie','1');module.update(self.read,self.write,300,6000,lambda:50)
  lib=[{'kind':'episode','title':'Local','played':100,'position':10,'total':20,'file':'/x.mkv','source':'library'}]
  self.assertEqual([r['title'] for r in module.entries(self.data(),'all',lib)],['Local','Pilot'])
 def test_title_without_tmdb_id_is_not_recorded(self):
  self.assertIsNone(self.record('movie',''))
 def test_player_and_version_kept_for_continue_watching(self):
  key=module.record(self.player('movie','1'),self.read,self.write,lambda:1,choice='umbrella')
  data=self.data();data['items'][key]['version']={'name':'Film.1080p','quality':'1080p'};self.write(module.STORE,__import__('json').dumps(data))
  self.assertEqual(module.player_key(self.player('movie','1')),key)
  self.assertEqual(module.saved_choice(self.read,key),{'player':'umbrella','version':{'name':'Film.1080p','quality':'1080p'}})
  # Same player again: the version stays; another player: it goes.
  module.record(self.player('movie','1'),self.read,self.write,lambda:2,choice='umbrella');self.assertIn('version',module.saved_choice(self.read,key))
  module.record(self.player('movie','1'),self.read,self.write,lambda:3,choice='elementum');self.assertEqual(module.saved_choice(self.read,key),{'player':'elementum'})
  self.assertTrue(module.forget_choice(self.read,self.write,key));self.assertEqual(module.saved_choice(self.read,key),{})
  self.assertFalse(module.forget_choice(self.read,self.write,'movie:9::'))
 def test_long_press_offers_choose_source(self):
  entry={'kind':'episode','tmdb_id':'2','season':'1','episode':'3'}
  self.assertEqual(module.choose_source_action(entry),'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=choose_source&key=episode%3A2%3A1%3A3)')
 def test_remove_from_continue_watching_keeps_progress_and_returns_when_played(self):
  # Owner (2026-11-13): "remove from continue watching ... dont make it erase the continue from progress ... if i watch
  # it again it can show back up".
  key=self.record('movie','1',title='Ghost Soldier');module.update(self.read,self.write,52,6000,lambda:self.t)
  self.record('tv','2','1','3',title='Ep',show='Show');module.update(self.read,self.write,100,2400,lambda:self.t)
  movie=next(e for e in module.entries(self.data()) if e['kind']=='movie')
  self.assertEqual(module.hide_action(movie),'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=continue_hide&key=movie%3A1%3A%3A)')
  module.hide(self.read,self.write,module.hide_key(movie),lambda:self.t+1)
  self.assertEqual([e['kind'] for e in module.entries(self.data())],['episode'])          # off the row
  self.assertEqual(self.data()['items'][key]['position'],52)                               # progress kept
  self.assertEqual(module.entry_for(self.read,key)['position'],52)
  module.stopped(self.read,self.write);self.assertEqual([e['kind'] for e in module.entries(self.data())],['episode'])  # still off
  # Watched again: the chooser records it and the service updates the position: back on the row, newest first.
  self.t+=100;self.record('movie','1',title='Ghost Soldier');module.update(self.read,self.write,400,6000,lambda:self.t)
  self.assertEqual([e['kind'] for e in module.entries(self.data())],['movie','episode'])
 def test_remove_a_library_item(self):
  lib=[{'kind':'episode','title':'Local','played':100,'position':10,'total':20,'file':'/x.mkv','source':'library'}]
  self.assertEqual(module.hide_key(lib[0]),'file:/x.mkv')
  module.hide(self.read,self.write,'file:/x.mkv',lambda:150)
  self.assertEqual(module.entries(self.data(),'all',lib),[])
  self.assertEqual(len(module.entries(self.data(),'all',[dict(lib[0],played=200)])),1)   # played again in Kodi
 def test_every_row_offers_remove_and_the_route_exists(self):
  root=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch'
  self.assertIn("li.addContextMenuItems(menu+[('Remove from Continue Watching',hide_action(entry))])",(root/'resources/lib/ios_continue.py').read_text())
  self.assertIn("if params.get('action')=='continue_hide':",(root/'default.py').read_text())
 def test_completed_copy_preserves_original_provider_and_version(self):
  player=self.player('movie','1')
  key=module.record(player,self.read,self.write,choice='umbrella')
  data=self.data();data['items'][key]['version']={'name':'original release','quality':'1080p'};self.write(module.STORE,json.dumps(data))
  for source in ('local','drive'):
   module.record(player,self.read,self.write,choice=source,preserve_player=True)
   saved=module.saved_choice(self.read,key)
   self.assertEqual(saved['player'],'umbrella');self.assertEqual(saved['version']['name'],'original release')
   self.assertEqual(self.data()['items'][key]['playback_source'],source)
  module.record(player,self.read,self.write,choice='elementum')
  self.assertEqual(module.saved_choice(self.read,key),{'player':'elementum'})
if __name__=='__main__':unittest.main()
