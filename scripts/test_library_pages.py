"""Owner (build 146): Library listed one show three times, titled its pages "Kodi iOS W", and a downloaded show
opened a bare page. One card per show, named pages, and the show page filled like TMDb Helper's."""
import importlib.util,json,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
import ios_library as page

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
lib=load('pages_drive_fixture',BOOT/'drivelibrary.py')
worker=load('pages_worker_fixture',BOOT/'library_watch.py')

def show_row(title,source,year='',folder=None):
 params={'type':'tv','show':title}
 if source=='local':params.update(local='1',year=year)
 else:params={'type':'tv','folder':folder,'show':title}
 return (page.page_url(params),title,{'poster':'p.jpg' if source=='drive' else ''},{'mediatype':'tvshow','year':year,'source':source},True)

def episode(path,season,ep,source):
 return (path,'S%02dE%02d'%(season,ep),{},{'mediatype':'episode','season':str(season),'episode':str(ep),'tvshowtitle':'Lanterns','source':source},False)

class Pages(unittest.TestCase):
 def test_three_lanterns_become_one_card(self):
  rows=page.merge_shows([show_row('Lanterns','local'),show_row('Lanterns','local','2026'),show_row('Lanterns','drive',folder='F1'),
                         show_row('Other Show','drive',folder='F2')])
  self.assertEqual([r[1] for r in rows],['Lanterns','Other Show'])
  params=page.current_params(rows[0][0])
  self.assertEqual((params['merge'],params['folder'],params['show']),('1','F1','Lanterns'))
  self.assertEqual(rows[0][2]['poster'],'p.jpg');self.assertEqual(rows[0][3]['source'],'both')
 def test_kodi_library_shows_untouched_and_single_show_kept(self):
  library=('videodb://tvshows/titles/1/','Lanterns',{},{'mediatype':'tvshow'},True)
  single=show_row('Solo','drive',folder='F')
  self.assertEqual(page.merge_shows([library,single]),[library,single])
 def test_movie_on_phone_and_drive_listed_once_phone_first(self):
  phone=('/phone/Inception.mkv','Inception',{},{'mediatype':'movie','year':'2010','source':'local'},False)
  cloud=('plugin://drive/x','Inception',{},{'mediatype':'movie','year':'2010','source':'drive'},False)
  remake=('plugin://drive/y','Inception',{},{'mediatype':'movie','year':'2030','source':'drive'},False)
  self.assertEqual(page.merge_movies([phone,cloud,remake]),[phone,remake])
 def test_episode_page_once_each_in_order_with_tmdb_details(self):
  cache={'tv:lanterns:':{'tmdb_id':'99','fanart':'fan.jpg','poster':'poster.jpg','rating':7.5},
         'season:99:1':{'1':{'title':'Pilot','plot':'It begins.','thumb':'still.jpg','runtime':56,'aired':'2026-08-17'}}}
  rows=[episode('/phone/S01E02.mkv',1,2,'local'),episode('/phone/S01E01.mkv',1,1,'local'),episode('plugin://drive/e1',1,1,'drive')]
  out=page.episode_rows(rows,'Lanterns',lib,cache,'KEY',None)
  self.assertEqual([r[0] for r in out],['/phone/S01E01.mkv','/phone/S01E02.mkv'])  # phone copy kept, Drive duplicate dropped
  path,label,art,info,_=out[0]
  self.assertEqual(label,'Pilot');self.assertEqual((art['thumb'],art['tvshow.fanart'],art['tvshow.poster']),('still.jpg','fan.jpg','poster.jpg'))
  self.assertEqual((info['plot'],info['duration'],info['premiered'],info['rating']),('It begins.',3360,'2026-08-17',7.5))
  self.assertEqual(out[1][1],'S01E02');self.assertEqual(out[1][2]['thumb'],'fan.jpg')  # no TMDb entry yet: show art
 def test_single_episode_files_named_by_the_show_read_episode_n(self):
  # Roadmap 2.2 (owner, build 229): 'phony.s01e01…' and 'Phony.S01E02…' listed as "1. phony", "2. Phony".
  rows=[('plugin://drive/a','phony',{},{'mediatype':'episode','season':'1','episode':'1','tvshowtitle':'phony','source':'drive'},False),
        ('plugin://drive/b','Phony',{},{'mediatype':'episode','season':'1','episode':'2','tvshowtitle':'phony','source':'drive'},False)]
  out=page.episode_rows(rows,'phony',lib,{},'KEY',None)
  self.assertEqual([r[1] for r in out],['Episode 1','Episode 2'])
 def test_download_records_its_shows_tmdb_id(self):
  import tempfile,os
  with tempfile.TemporaryDirectory() as d:
   path=os.path.join(d,'drive-library-art.json')
   lib.save_json(path,{'tv:phony:':{'tmdb_id':'1','poster':'wrong.jpg'},'tv:other:':{'tmdb_id':'5'}})
   self.assertTrue(lib.remember_show(d,['Phony','phony','Phony (2025)',''],'275139'))
   cache=lib.load_json(path,{})
   self.assertEqual(cache['tv:phony:'],{'tmdb_id':'275139'});self.assertEqual(cache['tv:phony (2025):'],{'tmdb_id':'275139'})
   self.assertEqual(cache['tv:other:'],{'tmdb_id':'5'})
   self.assertFalse(lib.remember_show(d,['Phony'],'275139'))   # unchanged: no write
   self.assertFalse(lib.remember_show(d,['Phony'],None))
 def test_library_play_carries_episode_details_not_the_file_name(self):
  # Owner (build 232): Library played 'phony.s01e01.1080p.web.h264-cakes[EZTVx.to].mp4' as the title.
  cache={'tv:phony:':{'tmdb_id':'275139','poster':'p.jpg','fanart':'f.jpg'},
         'show:275139':{'plot':'Show plot','clearlogo':'logo.png'},
         'season:275139:1':{'1':{'title':'Pilot','plot':'Sonny awakens.','thumb':'s.jpg','runtime':35,'aired':'2026-10-20'}}}
  params={'kind':'episode','title':'phony.s01e01.1080p.web.h264-cakes[EZTVx.to].mp4','show':'phony','season':'1','episode':'1','tmdb_id':''}
  name,info,art=page.playback_details(params,lib,cache)
  self.assertEqual(name,'Pilot')
  self.assertEqual((info['tvshowtitle'],info['season'],info['episode'],info['plot'],info['duration']),('Phony',1,1,'Sonny awakens.',2100))  # never the file's lower-case name
  self.assertEqual((art['thumb'],art['tvshow.clearlogo']),('s.jpg','logo.png'))
  name,info,_=page.playback_details(dict(params,episode='2'),lib,cache)
  self.assertEqual((name,info['plot']),('Episode 2','Show plot'))   # no TMDb entry yet: never the file name
  name,info,art=page.playback_details({'kind':'movie','title':'Home Alone','year':'1990'},lib,{'movie:home alone:1990':{'plot':'Kevin.','poster':'h.jpg'}})
  self.assertEqual((name,info['plot'],art['poster']),('Home Alone','Kevin.','h.jpg'))
 def test_show_with_nothing_finished_says_so(self):
  path,label,art,info,folder=page.empty_show_row({'poster':'p.jpg'})
  self.assertEqual((label,art['poster'],info['properties']['KodiIOS.EmptyShow']),('No finished episodes yet','p.jpg','true'))
  self.assertIn('Notifications',info['plot'])
 def test_continue_watching_cards_heal_from_saved_details(self):
  # Owner (build 252 screenshot): "the maze runner" and "phony" with no picture on Continue Watching.
  import ios_continue as cw
  saved={('movie','the maze runner'):{'name':'The Maze Runner','poster':'m.jpg','fanart':'mf.jpg'},('tv','phony'):{'poster':'p.jpg'}}
  look=lambda kind,title,year,tmdb:saved.get((kind,title.lower()),{})
  movie=cw.heal({'kind':'movie','title':'the maze runner','year':'2014'},look)
  self.assertEqual((movie['title'],movie['art']['poster']),('The Maze Runner','m.jpg'))
  ep=cw.heal({'kind':'episode','title':'Pilot','tvshowtitle':'phony','season':'1','episode':'1'},look)
  self.assertEqual((ep['tvshowtitle'],ep['art']['tvshow.poster']),('Phony','p.jpg'))
  fine={'kind':'movie','title':'Inception','art':{'poster':'i.jpg'}}
  self.assertIs(cw.heal(fine,lambda *a:self.fail('looked up')),fine)
  self.assertEqual(page.nice_title('the maze runner'),'The Maze Runner');self.assertEqual(page.nice_title('WALL-E'),'WALL-E')
 def test_season_lookup_parses_and_caches(self):
  answer=json.dumps({'episodes':[{'episode_number':1,'name':'Pilot','overview':'x','still_path':'/s.jpg','runtime':56,'air_date':'2026-08-17'}]}).encode()
  urls=[];cache={}
  found=lib.season('99',1,'KEY',cache,lambda url:urls.append(url) or answer)
  self.assertEqual(found['1']['thumb'],lib.IMAGE+'w780/s.jpg');self.assertIn('/tv/99/season/1?',urls[0])
  self.assertEqual(lib.season('99',1,'KEY',cache,None),found)       # cached
  self.assertEqual(lib.season('99',2,'KEY',{},None,cached_only=True),{})
  def offline(url):raise OSError('offline')
  cache2={};self.assertEqual(lib.season('99',1,'KEY',cache2,offline),{});self.assertEqual(cache2,{})  # retried later
 def test_worker_fetches_show_art_then_seasons_for_a_merged_page(self):
  params={'type':'tv','show':'Lanterns','merge':'1','folder':'F1'}
  local=[{'title':'Lanterns','year':'2026','season':'1','episode':'1'}];cloud=[{'title':'Lanterns','year':'','season':'2','episode':'1'}]
  self.assertEqual(list(worker.art_titles(params,local,cloud)),[('tv','Lanterns','')])
  answers={'search':json.dumps({'results':[{'id':99,'poster_path':'/p.jpg','backdrop_path':'/b.jpg'}]}).encode(),
           'season':json.dumps({'episodes':[{'episode_number':1,'name':'Pilot'}]}).encode(),
           'show':json.dumps({'id':99,'overview':'Show overview','genres':[{'name':'Drama'}],'images':{'logos':[{'iso_639_1':'en','file_path':'/logo.png'}]}}).encode()}
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   urls=[]
   def get(url,timeout):urls.append(url);return answers['season' if '/season/' in url else ('show' if '/tv/99?' in url else 'search')]
   self.assertTrue(worker.hydrate_artwork(params,local,cloud,lib,tmp,'KEY',get,lambda:True))
   cache=lib.load_json(tmp+'/drive-library-art.json',{})
  self.assertIn('season:99:1',cache);self.assertIn('season:99:2',cache);self.assertEqual(len(urls),4)
  self.assertEqual(cache['show:99']['genres'],['Drama']);self.assertTrue(cache['show:99']['clearlogo'].endswith('/logo.png'))
 def test_pages_are_named(self):
  source=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
  self.assertIn("'Downloaded Movies' if kind=='movie' else 'Downloaded TV Shows'",source)
  skin=(BOOT/'portrait.py').read_text()
  self.assertIn('<value condition="!String.IsEmpty(Container.PluginCategory)">$INFO[Container.PluginCategory]</value>',skin)
  self.assertEqual(page.current_params(page.page_url({'type':'tv','show':'A','merge':'1'}))['merge'],'1')
 def test_back_and_refresh_look_like_the_player_everywhere(self):
  # Owner (build 146): "I love this back button and want it applied everywhere" (the video player's back).
  for name in ('portrait.py','settings_page.py'):
   source=(BOOT/name).read_text()
   for line in source.splitlines():
    if ('chevron-left.png' in line or 'arrows-rotate.png' in line) and ('circle_button(' in line or "'glass','chevron-left.png'" in line):
     self.fail('%s still draws a glass circle: %s'%(name,line.strip()[:90]))
  sys.path.insert(0,str(BOOT))
  import portrait
  xml=portrait.nav_button(9001,48,36,'chevron-left.png','Back')
  self.assertIn('<width>150</width>',xml);self.assertIn('<width>104</width>',xml);self.assertNotIn('glass_',xml)
  self.assertIn('<left>48</left><top>36</top>',xml)


if __name__=='__main__':unittest.main()
