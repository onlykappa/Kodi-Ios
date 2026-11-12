"""Long press › Remove on a downloaded title (owner, 2026-11-12): which copies go, and nothing else."""
import os,sys,tempfile,unittest,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import ios_remove as rm
import drivelibrary
ME='plugin://plugin.video.kodi.ios.watch/'
def page(**q):return ME+'?'+urllib.parse.urlencode(dict(action='library',**q))

class Targets(unittest.TestCase):
 def test_nameless_drive_show_folder_is_removed_whole(self):
  t=rm.target(page(type='tv',folder='F1',show='45e2c1e044af0'),'45e2c1e044af0',{'mediatype':'tvshow','source':'drive'})
  self.assertEqual(t,{'kind':'tv','name':'45e2c1e044af0','drive':'F1'})
 def test_drive_episode_and_movie_files(self):
  url=drivelibrary.play_url('D','FILE9')
  self.assertEqual(rm.target(url,'Episode 1',{'mediatype':'episode','source':'drive'})['drive'],'FILE9')
  route=ME+'?'+urllib.parse.urlencode({'action':'library_play','path':url})
  self.assertEqual(rm.target(route,'Episode 1',{'mediatype':'episode','source':'drive'})['drive'],'FILE9')
  self.assertEqual(rm.target(url,'Inception',{'mediatype':'movie','source':'drive'})['kind'],'movie')
 def test_phone_and_merged_shows(self):
  t=rm.target(page(type='tv',local='1',show='Phony',year='2026'),'Phony',{'mediatype':'tvshow','source':'local'})
  self.assertEqual((t['show'],t['year'],'drive' in t),('Phony','2026',False))
  t=rm.target(page(type='tv',show='Phony',merge='1',folder='F2'),'Phony',{'mediatype':'tvshow','source':'both'})
  self.assertEqual((t['drive'],t['show'],t['any']),('F2','Phony','1'))
  self.assertEqual(rm.target('/x/Kodi Downloads/Movies/A.2010.mkv','A',{'mediatype':'movie','source':'local'})['file'],'/x/Kodi Downloads/Movies/A.2010.mkv')
 def test_kodi_library_rows_and_refresh_have_no_remove(self):
  self.assertIsNone(rm.menu_entry('videodb://tvshows/titles/3/','Show',{'mediatype':'tvshow'}))
  self.assertIsNone(rm.menu_entry(page(type='tv',fresh='1'),'Refresh Library',{}))
  label,action=rm.menu_entry(page(type='tv',folder='F1',show='X'),'X',{'mediatype':'tvshow','source':'drive'})
  self.assertEqual(label,'Remove');self.assertIn('action=library_remove',action);self.assertTrue(action.startswith('RunPlugin('))

class PhoneFiles(unittest.TestCase):
 def test_only_listed_completed_files_of_that_show(self):
  done=['/d/Kodi Downloads/TV Shows/Phony.S01E01.mkv','/d/Kodi Downloads/TV Shows/Phony S01/S01E02.mkv',
        '/d/Kodi Downloads/TV Shows/Lanterns.S01E01.mkv']
  self.assertEqual(rm.local_files({'show':'Phony'},done,drivelibrary.parse),sorted(done[:2]))
  self.assertEqual(rm.local_files({'file':'/etc/passwd'},done,drivelibrary.parse),[])
  self.assertEqual(rm.local_files({'file':done[2]},done,drivelibrary.parse),[done[2]])
 def test_files_and_emptied_folders_go_but_kodi_downloads_stays(self):
  with tempfile.TemporaryDirectory() as tmp:
   show=Path(tmp,'Kodi Downloads','TV Shows','Phony S01');show.mkdir(parents=True)
   a=show/'S01E01.mkv';a.write_bytes(b'x')
   self.assertEqual(rm.delete_files([str(a)]),1)
   self.assertFalse(show.exists());self.assertTrue(Path(tmp,'Kodi Downloads','TV Shows').exists())

class Records(unittest.TestCase):
 def test_listing_and_continue_watching_forget_the_removed_copy(self):
  cache={'tv:':{'time':1,'entries':[{'id':'F1'},{'id':'F2'}],'driveid':'D'},'tv:F1':{'time':1,'entries':[{'id':'E'}]}}
  out=rm.forget_listing(cache,'F1')
  self.assertEqual(out['tv:']['entries'],[{'id':'F2'}]);self.assertNotIn('tv:F1',out)
  data={'items':{'a':{'path':drivelibrary.play_url('D','FILE9')},'b':{'path':'/p/x.mkv'},'c':{'path':'other'}}}
  self.assertEqual(set(rm.forget_continue(data,'FILE9',{'/p/x.mkv'})['items']),{'c'})

if __name__=='__main__':unittest.main()
