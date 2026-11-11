"""Owner (build 205): "i want a button at the top to watch next episode"."""
import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ne=load('next_episode_t',BOOT/'next_episode.py')

class Plan(unittest.TestCase):
 item={'showtitle':'Dragon Ball Super: Beerus','season':1,'episode':1,'uniqueid':{'imdb':'tt39395275','tmdb':'999'}}
 def test_the_playlist_first(self):
  self.assertEqual(ne.plan(self.item,0,3),('playlist',None))
 def test_otherwise_tmdb_helper_plays_the_next_episode_of_the_show(self):
  how,url=ne.plan(self.item,0,1)
  self.assertEqual(how,'play')
  self.assertTrue(url.startswith('plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&season=1&episode=2&query=Dragon+Ball+Super'),url)
  self.assertNotIn('tmdb_id=999',url)   # a bare 'tmdb' may be the episode's own id
  how,url=ne.plan(dict(self.item,uniqueid={'tvshow.tmdb':'312359'}),-1,0)
  self.assertIn('tmdb_id=312359',url);self.assertNotIn('query=',url)
 def test_not_an_episode(self):
  self.assertEqual(ne.plan({'title':'Fall'},-1,0)[0],None)

class Button(unittest.TestCase):
 def test_top_left_beside_back_only_for_episodes(self):
  osd=load('player_osd_ne',LIB/'player_osd.py');xml=osd.window()
  self.assertIn('Next Episode',xml);self.assertIn('RunScript(service.kodi.ios.bootstrap,next_episode)',xml)
  self.assertIn('<visible>%s</visible>'%osd.EPISODE,xml)
  self.assertIn("'next_episode'",(BOOT/'default.py').read_text())

if __name__=='__main__':unittest.main()
