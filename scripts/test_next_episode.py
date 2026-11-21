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

class FromContinueWatching(unittest.TestCase):
 """ISSUE-331: the show's TMDb id and the playing episode's key come from Continue Watching's entry."""
 data={'current':'episode:312359:1:2','items':{'episode:312359:1:2':{'kind':'episode','tmdb_id':'312359','season':'1','episode':'2','player':'umbrella'}}}
 item={'type':'episode','showtitle':'Phony','season':1,'episode':2,'uniqueid':{}}
 def test_tmdb_id_and_next_key(self):
  current=ne.current_entry(self.data,self.item)
  how,url=ne.plan(self.item,-1,0,current)
  self.assertEqual(how,'play');self.assertIn('tmdb_id=312359',url);self.assertNotIn('query=',url)
  self.assertIn('ios_next=episode%3A312359%3A1%3A2',url);self.assertIn('episode=3',url)
 def test_another_episode_entry_is_not_used(self):
  self.assertIsNone(ne.current_entry(self.data,dict(self.item,episode=5)))
  how,url=ne.plan(dict(self.item,episode=5),-1,0,None);self.assertIn('query=Phony',url);self.assertNotIn('ios_next',url)
 def test_movies_never(self):
  self.assertEqual(ne.plan({'type':'movie','showtitle':'X','season':1,'episode':1},-1,0)[0],None)
  osd=load('player_osd_ne2',LIB/'player_osd.py');self.assertIn('![VideoPlayer.Content(movies)]',osd.EPISODE)
 def test_a_second_tap_is_ignored_while_starting(self):
  src=(BOOT/'next_episode.py').read_text()
  self.assertIn("home.setProperty(BUSY, str(time.time()))",src);self.assertIn('BUSY_SECONDS = 10',src)

class Button(unittest.TestCase):
 def test_top_left_beside_back_only_for_episodes(self):
  osd=load('player_osd_ne',LIB/'player_osd.py');xml=osd.window()
  self.assertIn('Next Episode',xml);self.assertIn('RunScript(service.kodi.ios.bootstrap,next_episode)',xml)
  self.assertIn('<visible>%s</visible>'%osd.EPISODE,xml)
  self.assertIn("'next_episode'",(BOOT/'default.py').read_text())

class StopFirst(unittest.TestCase):
    def test_waits_for_the_video_to_close_before_the_next_starts(self):
        import types
        state = {'video': 3, 'stopped': 0}
        class Monitor:
            def waitForAbort(self, t):
                state['video'] = max(0, state['video'] - 1)
                return False
        fake = types.SimpleNamespace(Player=lambda: types.SimpleNamespace(stop=lambda: state.__setitem__('stopped', 1)),
                                     Monitor=Monitor, getCondVisibility=lambda c: state['video'] > 0)
        self.assertTrue(ne.wait_stopped(fake))
        self.assertEqual((state['stopped'], state['video']), (1, 0))
        state['video'] = 10 ** 9
        self.assertFalse(ne.wait_stopped(fake, limit=0.3))


class AcrossSeasons(unittest.TestCase):
    """ISSUE-341 (owner): after a season's last episode, the next season's episode 1."""
    show = {'seasons': [{'season_number': 0, 'episode_count': 5}, {'season_number': 1, 'episode_count': 12},
                        {'season_number': 2, 'episode_count': 12}, {'season_number': 3, 'episode_count': 10}],
            'last_episode_to_air': {'season_number': 2, 'episode_number': 7}}
    item = {'type': 'episode', 'showtitle': 'Show', 'season': 1, 'episode': 12, 'uniqueid': {'tvshow.tmdb': '42'}}

    def test_aired_sizes(self):
        self.assertEqual(ne.aired_seasons(self.show), {1: 12, 2: 7, 3: 0})

    def test_the_last_episode_of_a_season_goes_to_the_next_seasons_first(self):
        how, url = ne.plan(self.item, -1, 0, None, ne.aired_seasons(self.show))
        self.assertEqual(how, 'play')
        self.assertIn('season=2&episode=1', url)

    def test_inside_a_season_it_is_the_next_episode(self):
        how, url = ne.plan(dict(self.item, season=2, episode=3), -1, 0, None, ne.aired_seasons(self.show))
        self.assertIn('season=2&episode=4', url)

    def test_after_the_last_aired_episode_there_is_none_yet(self):
        how, why = ne.plan(dict(self.item, season=2, episode=7), -1, 0, None, ne.aired_seasons(self.show))
        self.assertEqual(how, None)
        self.assertIn('last episode out', why)

    def test_without_tmdb_it_is_the_next_episode_as_before(self):
        how, url = ne.plan(self.item, -1, 0, None, None)
        self.assertIn('season=1&episode=13', url)


class DownloadedShow(unittest.TestCase):
 """Owner 2026-11-21: Next Episode on a downloaded (Elementum) show did nothing; build 619 shows Kodi's item had no show/season/episode."""
 LIB='plugin://plugin.video.kodi.ios.watch/?'
 def play(self,path,s,e):
  import urllib.parse
  return self.LIB+urllib.parse.urlencode({'action':'library_play','path':path,'show':'Phony','season':s,'episode':e})
 def rpc(self,pages):
  def call(method,params):
   self.assertEqual(method,'Files.GetDirectory');return {'result':{'files':pages.get(params['directory'],[])}}
  return call
 def pages(self):
  import urllib.parse
  root=self.LIB+urllib.parse.urlencode({'action':'library','type':'tv','show':'Phony','merge':'1'})
  s1=self.LIB+'action=library&type=tv&show=Phony&merge=1&season=1';s2=self.LIB+'action=library&type=tv&show=Phony&merge=1&season=2'
  return {root:[{'file':s1,'filetype':'directory'},{'file':s2,'filetype':'directory'}],
          s1:[{'file':self.play('/d/phony.s01e01.mkv',1,1)},{'file':self.play('/d/phony.s01e02.mkv',1,2)}],
          s2:[{'file':self.play('/d/phony.s02e01.mkv',2,1)}]}
 def record(self,path='/d/phony.s01e01.mkv',file='http://127.0.0.1:5000/x'):
  import json
  return json.dumps({'downloaded':True,'kind':'episode','show':'Phony','path':path,'file':file})
 def test_the_playing_download_is_recognised_by_what_kodi_plays(self):
  self.assertTrue(ne.playing_download(self.record(),'http://127.0.0.1:5000/x'))
  self.assertTrue(ne.playing_download(self.record(),self.play('/d/phony.s01e01.mkv',1,1)))   # Kodi reports the Library's link
  self.assertIsNone(ne.playing_download(self.record(),'https://debrid/other.mkv'))           # an Umbrella video after a download
  self.assertIsNone(ne.playing_download('',''))
 def test_the_next_downloaded_episode_in_library_order(self):
  rpc=self.rpc(self.pages())
  how,url,se=ne.downloaded_plan(rpc,{'show':'Phony','path':'/d/phony.s01e01.mkv'})
  self.assertEqual((how,se),('play',('1','2')));self.assertIn('phony.s01e02',url)
 def test_the_season_boundary_and_the_last_one(self):
  rpc=self.rpc(self.pages())
  self.assertEqual(ne.downloaded_plan(rpc,{'show':'Phony','path':'/d/phony.s01e02.mkv'})[2],('2','1'))
  self.assertEqual(ne.downloaded_plan(rpc,{'show':'Phony','path':'/d/phony.s02e01.mkv'}),(None,'That was the last downloaded episode.'))
 def test_an_unlisted_copy_falls_back_to_tmdb_helper(self):
  self.assertIsNone(ne.downloaded_plan(self.rpc(self.pages()),{'show':'Phony','path':'/d/elsewhere.mkv'}))
  def broken(method,params):raise RuntimeError('rpc')
  self.assertIsNone(ne.downloaded_plan(broken,{'show':'Phony','path':'/d/phony.s01e01.mkv'}))
 def test_the_library_records_its_paths(self):
  text=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
  self.assertIn("'path':params.get('path',''),'file':li.getPath(),'downloaded':True",text)
  self.assertIn("'file']})",(BOOT/'next_episode.py').read_text())

if __name__=='__main__':unittest.main()
