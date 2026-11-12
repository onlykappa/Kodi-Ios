"""Subtitles for every movie and episode (owner, 2026-11-12): SubDL and OpenSubtitles with the owner's free keys,
Podnapisi last; ranked together; season-pack zips give the right episode; keys stay on the phone."""
import io,json,sys,tempfile,unittest,zipfile,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import subtitle_sources as ss,track_menu as tm

def zipped(files):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  for n,d in files.items():z.writestr(n,d)
 return b.getvalue()

KEYS={'subdl':'K1','opensubtitles':'K2','opensubtitles_user':'','opensubtitles_password':''}

class Urls(unittest.TestCase):
 def test_subdl_movie_and_episode(self):
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(ss.subdl_url('K','en','Interstellar',2014)).query)
  self.assertEqual((q['film_name'],q['type'],q['year'],q['languages']),(['Interstellar'],['movie'],['2014'],['EN']))
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(ss.subdl_url('K','en','Naruto Shippuden',None,1,5)).query)
  self.assertEqual((q['type'],q['season_number'],q['episode_number']),(['tv'],['1'],['5']))
 def test_opensubtitles_parameters_sorted_lower_case(self):
  url=ss.os_url('en','Interstellar',2014)
  keys=[k for k,v in urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)]
  self.assertEqual(keys,sorted(keys));self.assertIn('query=interstellar',url)
  self.assertIn('parent_tmdb_id=46260',ss.os_url('en','Naruto',None,1,5,46260))

class Parsing(unittest.TestCase):
 def test_subdl_keeps_this_episode_and_language(self):
  body=json.dumps({'status':True,'subtitles':[
   {'release_name':'Naruto.Shippuden.S01E05.720p','lang':'english','url':'/subtitle/1.zip','episode':5,'hi':False},
   {'release_name':'Naruto.Shippuden.S01E06.720p','lang':'english','url':'/subtitle/2.zip','episode':6},
   {'release_name':'Naruto.Shippuden.S01.Complete','lang':'english','url':'/subtitle/3.zip','episode':None},
   {'release_name':'x','lang':'spanish','url':'/subtitle/4.zip'}]})
  self.assertEqual([r['id'] for r in ss.subdl_parse(body,'en',1,5)],['/subtitle/1.zip','/subtitle/3.zip'])
  self.assertEqual(ss.subdl_parse(json.dumps({'status':False,'error':'bad key'}),'en'),[])
 def test_opensubtitles_file_ids(self):
  body=json.dumps({'data':[{'attributes':{'language':'en','release':'Interstellar.2014.2160p.BluRay','hearing_impaired':True,'files':[{'file_id':7,'file_name':'a.srt'}]}},
                           {'attributes':{'language':'fr','files':[{'file_id':8}]}},{'attributes':{'language':'en','files':[]}}]})
  r=ss.os_parse(body,'en');self.assertEqual([(x['id'],x['impaired']) for x in r],[('7',True)])
 def test_season_zip_gives_the_episode(self):
  blob=zipped({'Naruto S01E04.srt':b'four','Naruto S01E05.srt':b'five','Naruto 1x06.srt':b'six'})
  self.assertEqual(tm.subtitle_from_zip(blob,1,5),('Naruto S01E05.srt',b'five'))
  self.assertEqual(tm.subtitle_from_zip(blob,1,6)[1],b'six')
  self.assertEqual(tm.subtitle_from_zip(zipped({'movie.srt':b'm'}))[1],b'm')

class Together(unittest.TestCase):
 def test_every_source_ranked_and_one_failing_is_skipped(self):
  calls=[]
  def get(url,headers):
   calls.append(url)
   if 'subdl' in url:return json.dumps({'status':True,'subtitles':[{'release_name':'Interstellar.2014.1080p.WEB','lang':'english','url':'/s.zip'}]}).encode()
   if 'opensubtitles' in url:return json.dumps({'data':[{'attributes':{'language':'en','release':'Interstellar.2014.2160p.4K.BluRay.x265.10bit.AAC5.1-YTS.MX','files':[{'file_id':9}]}}]}).encode()
   raise OSError('unexpected source')
  logged=[]
  r=ss.find(get,KEYS,'en','Interstellar',2014,filename='Interstellar.2014.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mp4',log=logged.append)
  self.assertEqual([x['source'] for x in r],['opensubtitles','subdl'])   # the closer release first
  self.assertEqual(sorted(logged),['opensubtitles: 1 found','subdl: 1 found'])   # Podnapisi is not asked
 def test_all_failing_raises_and_no_key_uses_podnapisi_only(self):
  def dead(url,headers):raise OSError('down')
  with self.assertRaises(OSError):ss.find(dead,dict(KEYS,opensubtitles=''),'en','X',2000)
  self.assertEqual(ss.sources({k:'' for k in ss.KEY_NAMES}),[])
  self.assertEqual(ss.find(dead,{k:'' for k in ss.KEY_NAMES},'en','X',2000),[])   # no key: nothing to ask
 def test_opensubtitles_download_uses_the_link(self):
  posts=[]
  def post(url,body,headers):
   posts.append((url,json.loads(body),headers.get('Api-Key')));return json.dumps({'link':'https://dl.example/file/abc.srt','remaining':4}).encode()
  name,data=ss.fetch(lambda url,h:b'1\n00:00:01,000 --> 00:00:02,000\nHi\n',post,KEYS,{'source':'opensubtitles','id':'9'})
  self.assertEqual((name,posts[0][0].rsplit('/',1)[-1],posts[0][1],posts[0][2]),('abc.srt','download',{'file_id':9},'K2'))

class Keys(unittest.TestCase):
 def test_saved_on_the_phone_only(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(ss.load_keys(d)['subdl'],'')
   ss.save_keys(d,dict(KEYS,subdl=' abc '));self.assertEqual(ss.load_keys(d)['subdl'],'abc')
   self.assertEqual(oct(Path(d,ss.KEYS_FILE).stat().st_mode&0o777),'0o600')

class FileNames(unittest.TestCase):
 def test_movie_from_release(self):
  self.assertEqual(tm.movie_from_release('Interstellar.2014.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mp4'),{'title':'Interstellar','year':2014})
  self.assertEqual(tm.movie_from_release('Blade.Runner.2049.2017.2160p.mkv'),{'title':'Blade Runner 2049','year':2017})
  self.assertIsNone(tm.movie_from_release('Home Alone'))

class NoKeysInTheLog(unittest.TestCase):
 def test_redact_and_safe_file_name(self):
  # Owner log 20b1ca76: an error line carried the SubDL key; the file was named after the download path.
  import importlib.util
  root=Path(__file__).resolve().parents[1]
  sp=importlib.util.spec_from_file_location('tracks_page',root/'migration/bundled-bootstrap/tracks.py');t=importlib.util.module_from_spec(sp);sp.loader.exec_module(t)
  self.assertNotIn('SECRET',t.redact("No such file: '/subtitle/1.zip?api_key=SECRET.en.srt'"))
  self.assertNotIn('SECRET',t.redact("{'Api-Key': 'SECRET', 'Authorization': 'Bearer SECRET'}"))
  src=(root/'migration/bundled-bootstrap/tracks.py').read_text()
  self.assertIn("zlib.crc32(str(result['id'])",src);self.assertIn('redact(m)',src)

class MenuPages(unittest.TestCase):
 def test_keys_and_files_are_rows_of_the_menu(self):
  rows=tm.keys_rows(dict(KEYS,opensubtitles=''))
  self.assertEqual([(r['label'],r['tag'],r['index']) for r in rows[:2]],[('SubDL key','SET','key:subdl'),('OpenSubtitles key','ADD','key:opensubtitles')])
  self.assertEqual(tm.file_rows([])[0]['index'],'nofiles')
  self.assertEqual(tm.file_rows(['/d/Inbox/Interstellar.en.srt'])[0],{'label':'Interstellar.en.srt','tag':'INBOX','on':False,'index':'sub:0'})
 def test_subtitle_files_newest_first_skipping_kodi_folders(self):
  with tempfile.TemporaryDirectory() as d:
   import os,time
   for rel,age in (('Inbox/a.srt',30),('Kodi Downloads/Movies/b.ass',10),('Kodi/userdata/c.srt',1),('notes.txt',1)):
    p=Path(d,rel);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('x');os.utime(p,(time.time()-age,time.time()-age))
   got=[Path(x).name for x in tm.subtitle_files([d,str(Path(d,'Inbox'))])]
   self.assertEqual(got,['b.ass','a.srt'])

if __name__=='__main__':unittest.main()
