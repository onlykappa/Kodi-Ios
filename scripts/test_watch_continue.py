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
if __name__=='__main__':unittest.main()
