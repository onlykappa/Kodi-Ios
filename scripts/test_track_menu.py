"""Owner-approved Subtitles / Audio menus (mockup docs/design/player-subtitles-audio-mockups.html round 2): the rows,
Download and apply's Podnapisi search, ranking and zip, the window XML and the video-controls wiring."""
import io,json,sys,unittest,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import track_menu as tm,pages,player_osd

class Rows(unittest.TestCase):
 def test_subtitles_off_first_with_tags_and_check(self):
  subs=[{'index':0,'language':'eng','name':''},{'index':1,'language':'eng','name':'English SDH','isimpaired':True},
        {'index':2,'language':'spa','name':'Spanish (Latin America)'},{'index':3,'language':'eng','name':'Forced','isforced':True}]
  rows=tm.subtitle_rows(subs,0,True)
  self.assertEqual([(r['label'],r['tag'],r['on']) for r in rows],
                   [('Off','',False),('English','',True),('English','SDH',False),('Spanish','',False),('English','FORCED',False)])
  self.assertTrue(tm.subtitle_rows(subs,0,False)[0]['on'])            # subtitles disabled: Off is checked
  self.assertEqual(tm.subtitle_rows([dict(subs[0],downloaded=True)],0,True)[1]['tag'],'NEW')
 def test_audio_tags(self):
  rows=tm.audio_rows([{'index':0,'language':'eng','name':'TrueHD Atmos 7.1','channels':8},
                      {'index':1,'language':'eng','name':'Director\'s Commentary','channels':2},
                      {'index':2,'language':'spa','name':'','channels':6}],0)
  self.assertEqual([(r['label'],r['tag'],r['on']) for r in rows],[('English','ATMOS',True),('English','COMMENTARY',False),('Spanish','5.1',False)])
 def test_timing_text(self):
  self.assertEqual(tm.seconds_text('-0.300 s'),'−0.3 s');self.assertEqual(tm.seconds_text('0.000 s'),'0.0 s')
  self.assertEqual(tm.seconds_text('0.025 s','ms'),'+25 ms');self.assertEqual(tm.seconds_text('','ms'),'0 ms')

def zipped(name,data):
 b=io.BytesIO();z=zipfile.ZipFile(b,'w');z.writestr(name,data);z.writestr('readme.txt','x');z.close();return b.getvalue()

class DownloadAndApply(unittest.TestCase):
 ANSWER={'data':[{'id':'aaa','language':'en','releases':['Inception.2010.1080p.BluRay.x264-SPARKS'],'custom_releases':[],'flags':['hearing_impaired']},
                 {'id':'bbb','language':'en','releases':['Inception.2010.2160p.UHD.BluRay.REMUX-FraMeSToR'],'custom_releases':[],'flags':[]},
                 {'id':'bbb','language':'en','releases':[],'custom_releases':[],'flags':[]},          # duplicate
                 {'id':'ccc','language':'es','releases':['Inception.2010.2160p'],'custom_releases':[],'flags':[]}]}   # other language
 def test_search_rank_and_fetch(self):
  asked=[]
  def get(url):
   asked.append(url)
   if '/download' in url:return zipped('Inception.2010.srt',b'1\n00:00:01,000 --> 00:00:02,000\nHi\n')
   return json.dumps(self.ANSWER).encode()
  found=tm.find(get,'en','Inception',2010,None,None,'Inception.2010.2160p.UHD.BluRay.REMUX-FraMeSToR.mkv')
  self.assertEqual([r['id'] for r in found],['bbb','aaa'])             # the same release first; Spanish dropped
  self.assertIn('keywords=Inception',asked[0]);self.assertIn('language=en',asked[0]);self.assertIn('year=2010',asked[0])
  self.assertIn('movie_type=movie',asked[0])
  name,data=tm.fetch(get,found[0])
  self.assertEqual(name,'Inception.2010.srt');self.assertTrue(data.startswith(b'1\n'))
  self.assertTrue(asked[-1].endswith('/subtitles/bbb/download'))
 def test_episode_query_and_retry_without_year(self):
  urls=[]
  def get(url):urls.append(url);return b'{"data":[]}'
  self.assertEqual(tm.find(get,'en','Lanterns',2026,1,2,'x.mkv'),[])
  self.assertIn('seasons=1',urls[0]);self.assertIn('episodes=2',urls[0]);self.assertIn('movie_type=tv-series',urls[0])
  self.assertEqual(len(urls),1)                                          # episodes are not retried without a year
  urls.clear();tm.find(get,'en','Inception',2010);self.assertEqual(len(urls),2);self.assertNotIn('year=',urls[1])
 def test_bad_answers_are_empty(self):
  self.assertEqual(tm.parse(b'<html>',  'en'),[]);self.assertIsNone(tm.subtitle_from_zip(b'not a zip'))
  self.assertIsNone(tm.subtitle_from_zip(zipped('readme.nfo',b'x')))
 def test_button_words(self):
  self.assertEqual(tm.cta('idle','English'),'Download and apply');self.assertEqual(tm.cta('search','English'),'Searching for English…')
  self.assertEqual(tm.cta('done','English'),'Downloaded and on');self.assertEqual(tm.note('none','English'),'No English subtitles found for this video.')

class Window(unittest.TestCase):
 def test_xml_and_controls(self):
  xml=pages.track_menu();root=ET.fromstring(xml.split('\n',2)[2])
  all_ids=[c.get('id') for c in root.iter('control') if c.get('id')];ids=set(all_ids)
  self.assertEqual(len(all_ids),len(ids))                               # one copy of each control (the script reads them by id)
  for i in ('9500','9501','9510','9310','9401','9402','9403','9404','9099'):self.assertIn(i,ids)
  self.assertIn('Kodi-iOS player controls',xml)                         # navigation.patch_skin leaves it alone
  self.assertIn('pill_112.png',xml);self.assertIn('FF4FA8FF',xml)        # existing capsule texture; blue text token
 def test_wired_into_the_video_controls_and_skin(self):
  osd=player_osd.window()
  self.assertIn('RunScript(service.kodi.ios.bootstrap,tracks,subtitles)',osd);self.assertIn('RunScript(service.kodi.ios.bootstrap,tracks,audio)',osd)
  self.assertNotIn('osdsubtitlesettings',osd);self.assertNotIn('osdaudiosettings',osd)
  self.assertIn("'tracks'",(BOOT/'default.py').read_text())
  portrait=(LIB/'portrait.py').read_text();self.assertEqual(portrait.count("'IOSTrackMenu.xml'"),2)   # OWN_1080I and VIDEO_ONLY
  self.assertIn("'1080i/'+TRACK_MENU:track_menu()",(LIB/'pages.py').read_text())

if __name__=='__main__':unittest.main()
