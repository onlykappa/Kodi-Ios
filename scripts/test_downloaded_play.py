"""Owner build-132: a downloaded movie opened from Home fetched the torrent again. The watch menu now plays the copy
in Kodi Downloads (ios_downloaded) before offering players."""
import importlib.util,sys,tempfile,types,unittest
from unittest import mock
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
sys.path.insert(0,str(LIB))
import ios_downloaded as d

def walker(tree):
 def walk(top):
  for root,files in tree.items():
   if root.startswith(top):yield root,[],files
 return walk

class Matching(unittest.TestCase):
 def test_movies(self):
  self.assertTrue(d.matches('The Nightmare Before Christmas 1993 1080p BluRay HEVC x265 5.1 BONE.mkv','movie','The Nightmare Before Christmas','1993'))
  self.assertTrue(d.matches('Nightmare.Before.Christmas.1993.mkv','movie','The Nightmare Before Christmas','1993'))
  self.assertFalse(d.matches('The Dark Knight Rises 2012.mkv','movie','The Dark Knight','2008'))
  self.assertTrue(d.matches('The.Dark.Knight.2008.2160p.mkv','movie','The Dark Knight','2008'))
  self.assertFalse(d.matches('The Nightmare Before Christmas 1993.mkv','movie','Christmas','1993'))
  self.assertTrue(d.matches('Amélie (2001).mkv','movie','Amélie','2001'))
  self.assertTrue(d.matches('Fast & Furious 2009.mkv','movie','Fast and Furious','2009'))
 def test_episodes(self):
  self.assertTrue(d.matches('Breaking.Bad.S01E02.720p.mkv','episode','Breaking Bad','',1,2))
  self.assertTrue(d.matches('Breaking Bad 1x02.mkv','episode','Breaking Bad','',1,2))
  self.assertFalse(d.matches('Breaking.Bad.S01E12.mkv','episode','Breaking Bad','',1,2))
  self.assertFalse(d.matches('Breaking.Bad.S01E02.mkv','episode','Better Call Saul','',1,2))
 def test_find_prefers_the_big_file_and_season_packs(self):
  tree={'/dl/Movies':['The Nightmare Before Christmas 1993 1080p.mkv','notes.txt'],
        '/dl/Movies/Nightmare Before Christmas (1993)':['sample.mkv','movie.mkv'],
        '/dl/TV Shows/Breaking Bad Season 1':['Episode S01E02.mkv','Episode S01E03.mkv']}
  sizes={}
  import os
  real=os.path.getsize
  os.path.getsize=lambda p:{'/dl/Movies/Nightmare Before Christmas (1993)/movie.mkv':9}.get(p,1)
  try:
   self.assertEqual(d.find(['/dl/Movies'],'movie','The Nightmare Before Christmas','1993',walk=walker(tree)),'/dl/Movies/Nightmare Before Christmas (1993)/movie.mkv')
   self.assertEqual(d.find(['/dl/TV Shows'],'episode','Breaking Bad','',1,2,walk=walker(tree)),'/dl/TV Shows/Breaking Bad Season 1/Episode S01E02.mkv')
   self.assertIsNone(d.find(['/dl/TV Shows'],'episode','Breaking Bad','',1,9,walk=walker(tree)))
   self.assertIsNone(d.find(['/dl/Movies'],'movie','Coco','2017',walk=walker(tree)))
   self.assertIsNone(d.find([''],'movie','Coco','2017',walk=walker(tree)))
  finally:os.path.getsize=real

class SeedingTorrents(unittest.TestCase):
 def test_library_lists_completed_folders_and_only_verified_finished_seeds(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);movies=root/'Movies';tv=root/'TV Shows';active=root/'Elementum Downloads'
   def file(rel,data=b'video'):
    path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return str(path)
   done=file('Movies/Heat.1995.mkv');show=file('TV Shows/Lanterns.S01E01.mkv')
   seed=file('Elementum Downloads/Finished.2000/Finished.2000.mkv')
   file('Elementum Downloads/Unfinished.2001/Unfinished.2001.mkv',b'x'*4096)  # preallocated size is not completion
   file('Movies/sample.mkv');file('Movies/empty.mkv',b'');file('Movies/notes.txt');file('Movies/Heat.mkv.part')
   folders=[str(movies),str(tv),str(active)]
   self.assertEqual(set(d.completed_files('movie',folders,names={'Finished.2000'})),{done,seed})
   self.assertEqual(set(d.completed_files('tv',folders,names=set())),{show})
 def test_library_overlapping_active_root_stays_unfinished_and_symlinks_are_skipped(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);active=root/'active';active.mkdir();file=active/'Partial.2000.mkv';file.write_bytes(b'preallocated')
   link=root/'linked.mkv';link.symlink_to(file)
   self.assertEqual(d.completed_files('movie',[str(root),'',str(active)],names=set()),[])
   alias=root/'alias';alias.symlink_to(active,target_is_directory=True)
   self.assertEqual(d.completed_files('movie',[str(alias),'',str(active)],names=set()),[])
 def test_library_falls_back_to_current_sandbox_when_elementum_setting_is_stale(self):
  with tempfile.TemporaryDirectory() as tmp:
   movie=Path(tmp)/'Heat.1995.mkv';movie.write_bytes(b'video')
   with mock.patch.object(d,'folders',return_value=['/old/app/Movies','','']),mock.patch.object(d,'default_completed_folder',return_value=[tmp]):
    self.assertEqual(d.completed_files('movie'),[str(movie)])
 def test_finished_torrent_in_download_folder_counts_unfinished_does_not(self):
  tree={'/c/Movies':[],'/c/TV':[],'/e/The Nightmare Before Christmas 1993 1080p':['Nightmare.1993.mkv'],
        '/e/Coco 2017 1080p':['Coco.2017.mkv']}
  folders=['/c/Movies','/c/TV','/e']
  names={'The Nightmare Before Christmas 1993 1080p'}
  with mock.patch.object(d.os.path,'getsize',return_value=1):
   self.assertEqual(d.find_downloaded('movie','The Nightmare Before Christmas','1993',folder_list=folders,names=names,walk=walker(tree)),
                    '/e/The Nightmare Before Christmas 1993 1080p/Nightmare.1993.mkv')
   self.assertIsNone(d.find_downloaded('movie','Coco','2017',folder_list=folders,names=names,walk=walker(tree)))
   self.assertIsNone(d.find_downloaded('movie','Coco','2017',folder_list=folders,names=set(),walk=walker(tree)))
 def test_finished_names_reads_elementum_progress(self):
  import json
  data=json.dumps([{'name':'A','progress':100},{'name':'B','progress':42.5}]).encode()
  self.assertEqual(d.finished_names(lambda url:data),{'A'})
  self.assertEqual(d.finished_names(lambda url:b'oops'),set())

class WatchMenu(unittest.TestCase):
 def load(self):
  spec=importlib.util.spec_from_file_location('watch',LIB/'ios_watch_dialog.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_downloaded_copy_becomes_a_local_item(self):
  m=self.load()
  class Local:
   is_local=True;kodi_file=None;actions=None
  player=types.SimpleNamespace(tmdb_type='movie',tmdb_id='9479',season='',episode='',
                               details=types.SimpleNamespace(infolabels={'title':'The Nightmare Before Christmas','year':1993}))
  local=Local()
  item=m.downloaded_item(player,[object(),local],find=lambda folders,*a:'/dl/x.mkv',folders=lambda:['/dl'])
  self.assertIsNot(item,local)
  self.assertEqual((item.kodi_file,item.actions,item.is_local),('/dl/x.mkv','/dl/x.mkv',True))
  self.assertIsNone(m.downloaded_item(player,[local],find=lambda *a:None,folders=lambda:['/dl']))
if __name__=='__main__':unittest.main()
