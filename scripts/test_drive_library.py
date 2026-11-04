import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
spec=importlib.util.spec_from_file_location('drivelibrary',ROOT/'migration/bundled-bootstrap/resources/lib/drivelibrary.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
spec=importlib.util.spec_from_file_location('ios_library',ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py');page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)
FOLDER=lib.FOLDER

class FakeDrive:
 """Drive › Kodi Downloads › Movies (two releases, one in pages) and TV Shows › Orange Is the New Black › S01."""
 def __init__(self):
  self.tree={'root':[('top','Kodi Downloads',FOLDER)],'top':[('mov','Movies',FOLDER),('tv','TV Shows',FOLDER)],
   'mov':[('r1','The.Dark.Knight.2008.2160p.WEB-DL.x265-GRP',FOLDER),('f2','Inception (2010) 1080p BluRay.mkv','video/x-matroska')],
   'r1':[('f1','The.Dark.Knight.2008.2160p.WEB-DL.x265-GRP.mkv','video/x-matroska'),('s1','sample.mkv','video/x-matroska'),('n1','info.nfo','text/plain')],
   'tv':[('show','Orange Is the New Black',FOLDER)],'show':[('season','Season 1',FOLDER)],
   'season':[('e2','Orange.Is.the.New.Black.S01E02.1080p.mkv','v'),('e1','Orange.Is.the.New.Black.S01E01.1080p.mkv','v')]}
  self.calls=0
 def call(self,method,url,body=None,headers=None):
  self.calls+=1
  import urllib.parse
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
  query=q['q'][0]
  if query.startswith('name='):
   name=query.split("'")[1];parent=query.split("'")[5]
   found=[{'id':i} for i,n,m in self.tree.get(parent,[]) if n==name and m==FOLDER]
   return 200,{},json.dumps({'files':found}).encode()
  parent=query.split("'")[1];items=[{'id':i,'name':n,'mimeType':m,'size':'100'} for i,n,m in self.tree.get(parent,[])]
  # Paging: one item per page for the Movies folder.
  if parent=='mov':
   start=int(q.get('pageToken',['0'])[0]);data={'files':items[start:start+1]}
   if start+1<len(items):data['nextPageToken']=str(start+1)
   return 200,{},json.dumps(data).encode()
  return 200,{},json.dumps({'files':items}).encode()

class DriveLibrary(unittest.TestCase):
 def test_completed_copy_finds_movie_or_exact_episode_without_metadata_search(self):
  drive=FakeDrive()
  from unittest.mock import patch
  with patch.object(lib,'client',return_value=(drive,'D1')):
   with tempfile.TemporaryDirectory() as tmp:
    self.assertIn('item_id=f1',lib.completed_copy('movie','The Dark Knight','2008','','',tmp))
    self.assertIsNone(lib.completed_copy('movie','The Dark Knight','2012','','',tmp))
    self.assertIsNone(lib.completed_copy('movie','Dark','2008','','',tmp))
    self.assertIn('item_id=e2',lib.completed_copy('episode','Orange Is the New Black','',1,2,tmp))
    self.assertIsNone(lib.completed_copy('episode','Orange Is the New Black','',1,9,tmp))
 def test_failed_drive_folder_check_is_not_reported_as_no_download(self):
  denied=type('Denied',(),{'call':lambda *a:(403,{},b'{}')})()
  with self.assertRaises(RuntimeError):lib.find_folder(denied,[lib.TOP,'Movies'],strict=True)
 def test_cached_miss_is_refreshed_before_reporting_no_download(self):
  from unittest.mock import patch
  with patch.object(lib,'listing',side_effect=[([], 'D1'),([{'id':'new','title':'Inception','year':'2010','size':100}], 'D1')]) as listing:
   self.assertIn('item_id=new',lib.completed_copy('movie','Inception','2010','','','state'))
   self.assertFalse(listing.call_args_list[0].kwargs['fresh']);self.assertTrue(listing.call_args_list[1].kwargs['fresh'])
 def test_names(self):
  self.assertEqual(lib.parse('The.Dark.Knight.2008.2160p.WEB-DL.x265-GRP.mkv'),{'title':'The Dark Knight','year':'2008','season':'','episode':''})
  self.assertEqual(lib.parse('Inception (2010) 1080p BluRay.mkv')['title'],'Inception')
  p=lib.parse('Orange.Is.the.New.Black.S01E02.1080p.mkv');self.assertEqual((p['title'],p['season'],p['episode']),('Orange Is the New Black','1','2'))
  self.assertEqual(lib.parse('2012.2009.1080p.mkv'),{'title':'2012','year':'2009','season':'','episode':''})
  self.assertEqual(lib.parse('Orange Is the New Black')['title'],'Orange Is the New Black')
 def test_movies_shows_episodes_from_drive(self):
  drive=FakeDrive();top=lib.find_folder(drive,[lib.TOP,'Movies']);self.assertEqual(top,'mov')
  self.assertIsNone(lib.find_folder(drive,[lib.TOP,'Music']))
  movies=lib.movies(lib.videos(drive,top))
  self.assertEqual([(m['title'],m['year'],m['id']) for m in movies],[('Inception','2010','f2'),('The Dark Knight','2008','f1')])  # samples and .nfo left out
  shows=lib.shows(lib.children(drive,'tv'));self.assertEqual([(s['title'],s['id']) for s in shows],[('Orange Is the New Black','show')])
  eps=lib.episodes(lib.videos(drive,'show'),'Orange');self.assertEqual([e['id'] for e in eps],['e1','e2'])
  self.assertEqual(lib.play_url('D1','f1'),'plugin://plugin.googledrive/?action=play&content_type=video&driveid=D1&item_driveid=D1&item_id=f1')
 def test_artwork_cached_and_retried_after_errors(self):
  seen=[];cache={}
  get=lambda url:seen.append(url) or json.dumps({'results':[{'id':155,'poster_path':'/p.jpg','backdrop_path':'/b.jpg','overview':'Batman'}]}).encode()
  art=lib.artwork('movie','The Dark Knight','2008','KEY',cache,get)
  self.assertEqual((art['tmdb_id'],art['poster'],art['plot']),('155','https://image.tmdb.org/t/p/w500/p.jpg','Batman'))
  self.assertIn('year=2008',seen[0]);lib.artwork('movie','The Dark Knight','2008','KEY',cache,get);self.assertEqual(len(seen),1)
  def broken(url):raise OSError('offline')
  self.assertEqual(lib.artwork('tv','Lost','','KEY',cache,broken),{});self.assertNotIn('tv:lost:',cache)
  self.assertEqual(lib.artwork('movie','X','','',cache,get),{})   # no key: no request
 def test_tmdb_key_read_from_helper(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'resources/tmdbhelper/lib/api/api_keys';path.mkdir(parents=True);fake='ab'*16   # a stand-in, built here so it never looks like a real key
   (path/'tmdb.py').write_text('API_'+'KEY = '+repr(fake)+'\n')
   self.assertEqual(lib.tmdb_key(tmp),fake);self.assertEqual(lib.tmdb_key(tmp+'/missing'),'')
 def test_listing_cached_and_page_rows(self):
  drive=FakeDrive();real=lib.client
  try:
   lib.client=lambda:(drive,'D1')
   with tempfile.TemporaryDirectory() as tmp:
    entries,driveid=lib.listing('movie',tmp,now=lambda:1000);calls=drive.calls
    self.assertEqual((len(entries),driveid),(2,'D1'))
    lib.listing('movie',tmp,now=lambda:1100);self.assertEqual(drive.calls,calls)   # cached
    lib.listing('movie',tmp,now=lambda:1000+lib.LISTING_TTL+1);self.assertGreater(drive.calls,calls)
    get=lambda url:json.dumps({'results':[]}).encode()
    rows=page.drive_rows('tv',None,'',lib,tmp,{},'KEY',get)
    self.assertEqual(rows[0][1],'Orange Is the New Black');self.assertTrue(rows[0][4]);self.assertIn('folder=show',rows[0][0])
    eps=page.drive_rows('tv','show','Orange Is the New Black',lib,tmp,{},'KEY',get)
    self.assertEqual([r[1] for r in eps],['S01E01','S01E02']);self.assertTrue(eps[0][0].startswith('plugin://plugin.googledrive/'))
   lib.client=lambda:(None,None)
   with tempfile.TemporaryDirectory() as tmp:self.assertEqual(lib.listing('tv',tmp),([],None))
  finally:lib.client=real
if __name__=='__main__':unittest.main()
