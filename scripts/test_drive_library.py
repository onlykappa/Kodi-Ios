import importlib.util,json,sys,tempfile,unittest
from unittest.mock import Mock,patch
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
  self.calls=0;self.methods=[]
 def call(self,method,url,body=None,headers=None):
  self.calls+=1;self.methods.append(method)
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
 def test_single_file_tv_uploads_appear_and_open_only_the_selected_show(self):
  drive=FakeDrive()
  drive.tree['tv'] += [('loose1','Lanterns.S01E01.2160p.mkv','video/x-matroska'),
                       ('loose2','Lanterns.S01E02.2160p.mkv','video/x-matroska'),
                       ('other','Other.Show.S01E01.2160p.mkv','video/x-matroska')]
  with patch.object(lib,'client',return_value=(drive,'D1')),tempfile.TemporaryDirectory() as tmp:
   entries,_=lib.listing('tv',tmp,fresh=True)
   self.assertEqual([(e['title'],e['id']) for e in entries if e.get('loose')],[('Lanterns','tv'),('Other Show','tv')])
   rows=page.drive_rows('tv',None,'',lib,tmp,{},'',lambda url:b'{}')
   show=next(r for r in rows if r[1]=='Lanterns');self.assertIn('loose=1',show[0]);self.assertTrue(show[4])
   eps=page.drive_rows('tv','tv','Lanterns',lib,tmp,{},'',lambda url:b'{}',loose=True)
   self.assertEqual([r[1] for r in eps],['S01E01','S01E02'])
   self.assertTrue(all('item_id=loose' in r[0] for r in eps))
   self.assertIn('item_id=loose1',lib.completed_copy('episode','Lanterns','',1,1,tmp))
   self.assertNotIn('item_id=other',lib.completed_copy('episode','Lanterns','',1,1,tmp))
   self.assertIsNone(lib.completed_copy('episode','Lanterns','',1,3,tmp))
 def test_manual_fresh_listing_bypasses_an_existing_empty_cache(self):
  drive=FakeDrive();drive.tree['mov']=[]
  with patch.object(lib,'client',return_value=(drive,'D1')),tempfile.TemporaryDirectory() as tmp:
   self.assertEqual(lib.listing('movie',tmp)[0],[])
   drive.tree['mov']=[('new','Heat.1995.mkv','video/x-matroska')]
   self.assertEqual(lib.listing('movie',tmp)[0],[])
   self.assertEqual(lib.listing('movie',tmp,fresh=True)[0][0]['id'],'new')
 def test_existing_duplicate_download_folders_are_all_listed_without_creating_more(self):
  drive=FakeDrive()
  drive.tree['root'].append(('top2','Kodi Downloads',FOLDER))
  drive.tree['top2']=[('mov2','Movies',FOLDER),('tv2','TV Shows',FOLDER)]
  drive.tree['mov2']=[('heat','Heat.1995.mkv','video/x-matroska')]
  drive.tree['tv2']=[('lanterns','Lanterns',FOLDER)]
  drive.tree['lanterns']=[('lantern1','Lanterns.S01E01.mkv','video/x-matroska')]
  with patch.object(lib,'client',return_value=(drive,'D1')),tempfile.TemporaryDirectory() as tmp:
   movies,_=lib.listing('movie',tmp,fresh=True)
   self.assertEqual({e['id'] for e in movies},{'f1','f2','heat'})
   shows,_=lib.listing('tv',tmp,fresh=True)
   self.assertEqual({e['id'] for e in shows},{'show','lanterns'})
   self.assertIn('item_id=lantern1',lib.completed_copy('episode','Lanterns','',1,1,tmp))
  self.assertTrue(drive.methods);self.assertEqual(set(drive.methods),{'GET'})
 def test_duplicate_folder_discovery_follows_all_pages_and_each_parent_branch(self):
  from urllib.parse import parse_qs,urlsplit
  seen=[]
  def call(method,url,body=None,headers=None):
   q=parse_qs(urlsplit(url).query);seen.append(q)
   if "name='Kodi Downloads'" in q['q'][0]:
    data={'files':[{'id':'top2'}]} if q.get('pageToken')==['second'] else {'files':[{'id':'top1'}],'nextPageToken':'second'}
   else:data={'files':[{'id':'movies2' if "'top2' in parents" in q['q'][0] else 'movies1'}]}
   return 200,{},json.dumps(data).encode()
  self.assertEqual(lib.find_folders(type('PagedDrive',(),{'call':staticmethod(call)})(),[lib.TOP,'Movies'],strict=True),['movies1','movies2'])
  self.assertEqual(len(seen),4)
 def test_local_show_groups_generic_pack_names_and_preserves_episode_coordinates(self):
  import ios_downloaded
  paths=['/phone/Kodi Downloads/TV Shows/Breaking Bad/Season 1/S01E02.mkv',
         '/phone/Kodi Downloads/TV Shows/Breaking Bad/Season 1/Episode S01E01.mkv',
         '/phone/Kodi Downloads/TV Shows/Other Show/Season 1/S01E01.mkv']
  with patch.object(ios_downloaded,'completed_files',return_value=paths):entries=page.local_entries('tv',lib)
  self.assertEqual([e['title'] for e in entries],['Breaking Bad','Breaking Bad','Other Show'])
  rows=page.local_rows('tv','','',entries,lib,{},'',lambda url:b'{}')
  self.assertEqual([r[1] for r in rows],['Breaking Bad','Other Show']);self.assertTrue(all(r[4] for r in rows))
  self.assertIn('local=1',rows[0][0])
  episodes=page.local_rows('tv','Breaking Bad','',entries,lib,{},'',lambda url:b'{}')
  self.assertEqual([r[1] for r in episodes],['S01E01','S01E02'])
  self.assertEqual([r[3]['episode'] for r in episodes],['1','2']);self.assertTrue(all(not r[4] for r in episodes))
  self.assertTrue(all(r[0] in paths[:2] for r in episodes))
 def test_local_season_pack_alternate_coordinate_names_keep_the_show_identity(self):
  import ios_downloaded
  with patch.object(ios_downloaded,'completed_files',return_value=[
       '/phone/Kodi Downloads/TV Shows/Lanterns/Season 1/S01 E02.mkv',
       '/phone/Kodi Downloads/TV Shows/Lanterns/Season 1/1x03.mkv']):
   entries=page.local_entries('tv',lib)
  self.assertEqual([e['title'] for e in entries],['Lanterns','Lanterns'])
  self.assertEqual([e['episode'] for e in entries],['2','3'])
 def test_local_movie_infers_generic_filename_from_release_folder_and_filters_tv(self):
  import ios_downloaded
  with patch.object(ios_downloaded,'completed_files',return_value=[
       '/phone/Kodi Downloads/Movies/Heat (1995)/movie.mkv','/phone/Kodi Downloads/Movies/Show.S01E01.mkv']):
   entries=page.local_entries('movie',lib)
  self.assertEqual([(e['title'],e['year']) for e in entries],[('Heat','1995')])
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
 def test_foreground_cached_art_never_waits_for_a_metadata_request(self):
  get=Mock(side_effect=AssertionError('foreground metadata request'))
  cache={'movie:heat:1995':{'poster':'cached-poster'}}
  self.assertEqual(lib.artwork('movie','Heat','1995','KEY',cache,get,cached_only=True),{'poster':'cached-poster'})
  self.assertEqual(lib.artwork('movie','New title','2024','KEY',cache,get,cached_only=True),{})
  get.assert_not_called()
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
 def test_concurrent_cache_writers_publish_complete_json_without_shared_temp_failures(self):
  from concurrent.futures import ThreadPoolExecutor
  with tempfile.TemporaryDirectory() as tmp:
   path=str(Path(tmp)/'drive-library.json')
   def save(index):lib.save_json(path,{'writer':index,'entries':['entry']*1000})
   with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(save,range(32)))
   result=lib.load_json(path,None)
   self.assertIn(result['writer'],range(32));self.assertEqual(len(result['entries']),1000)
   self.assertEqual([p.name for p in Path(tmp).iterdir()],['drive-library.json'])
class Duplicates(unittest.TestCase):
 """Owner (build 152): the same show must not get two Drive folders, nor the same episode two preparations."""
 def setUp(self):
  self.lib=lib
 def test_same_show_and_episode_match_across_releases_and_years(self):
  k=self.lib.media_key
  self.assertEqual(k('Lanterns.S01E01.Pilot.2160p.10bit.AMZN.WEB-DL.DDP5.1.HEVC-Vyndros.mkv'),('episode','lanterns',1,1))
  self.assertEqual(k('Lanterns (2026) - S01E01 - 1080p.mkv'),k('Lanterns.S01E01.Pilot.2160p.mkv'))
  self.assertEqual(k('S01E01.mkv','Lanterns (2026)'),('episode','lanterns',1,1))
  self.assertIsNone(k('S01E01.mkv','Season 1'))   # a season folder names no show: never guess
  self.assertNotEqual(k('Lanterns.S01E02.mkv'),k('Lanterns.S01E01.mkv'))
  self.assertEqual(k('Inception.2010.2160p.mkv'),('movie','inception','2010'))
  self.assertNotEqual(k('Dune.2021.mkv'),k('Dune.1984.mkv'))
  self.assertEqual(self.lib.show_key('Lanterns (2026)'),self.lib.show_key('lanterns'))
 def test_quality(self):
  q=self.lib.quality
  self.assertEqual((q('a.2160p.mkv'),q('a 4K HDR.mkv'),q('a.1080p.mkv'),q('a.mkv')),(2160,2160,1080,0))
 def test_episode_goes_into_the_shows_existing_folder(self):
  from unittest import mock
  folders=[{'name':'Lanterns','mimeType':self.lib.FOLDER},{'name':'Other Show','mimeType':self.lib.FOLDER}]
  with mock.patch.object(self.lib,'find_folders',lambda drive,parts,strict=False:['tv']),mock.patch.object(self.lib,'children',lambda drive,fid:folders):
   self.assertEqual(self.lib.show_folder(None,['Kodi Downloads','TV Shows','Lanterns (2026)']),['Kodi Downloads','TV Shows','Lanterns'])
   self.assertEqual(self.lib.show_folder(None,['Kodi Downloads','TV Shows','New Show']),['Kodi Downloads','TV Shows','New Show'])
   self.assertEqual(self.lib.show_folder(None,['Kodi Downloads','Movies']),['Kodi Downloads','Movies'])
  def broken(*a,**k):raise RuntimeError('offline')
  with mock.patch.object(self.lib,'find_folders',broken):
   self.assertEqual(self.lib.show_folder(None,['Kodi Downloads','TV Shows','Lanterns (2026)']),['Kodi Downloads','TV Shows','Lanterns (2026)'])

if __name__=='__main__':unittest.main()
