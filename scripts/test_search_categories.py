"""Generated category clicks must respect the selected media filter and TMDb genre taxonomy."""
import sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import portrait as p

class Categories(unittest.TestCase):
 def setUp(self):self.items=ET.fromstring(p.search_window('<window/>')).findall(".//control[@id='5100']/content/item")
 def route(self,name,kind):
  item=next(i for i in self.items if i.findtext('label')==name)
  condition=p.MOVIE_FILTER if kind=='movie' else '!'+p.MOVIE_FILTER
  click=next(c.text for c in item.findall('onclick') if c.get('condition')==condition and c.text.startswith('ActivateWindow'))
  return parse_qs(urlsplit(click[len('ActivateWindow(Videos,'):-len(',return)')]).query)
 def test_drama_and_every_supported_movie_category_use_movies(self):
  for name,gid,*_ in p.CATEGORIES:
   if gid not in p.MOVIE_GENRES:continue
   q=self.route(name,'movie');self.assertEqual(q['tmdb_type'],['movie']);self.assertEqual(q['with_genres'],[p.MOVIE_GENRES[gid]])
  self.assertEqual(self.route('Drama','movie')['with_genres'],['18'])
 def test_tv_category_routes_remain_tv_with_tv_genres(self):
  for name,gid,*_ in p.CATEGORIES:
   q=self.route(name,'tv');self.assertEqual(q['tmdb_type'],['tv']);self.assertEqual(q['with_genres'],[str(gid)])
 def test_movie_scifi_action_and_war_do_not_reuse_tv_only_ids(self):
  self.assertEqual(self.route('Sci-Fi & Fantasy','movie')['with_genres'],['878|14'])
  self.assertEqual(self.route('Action & Adventure','movie')['with_genres'],['28|12'])
  self.assertEqual(self.route('War & Politics','movie')['with_genres'],['10752'])
 def test_tv_only_categories_hidden_for_movies(self):
  for name in ('Kids','Reality'):
   item=next(i for i in self.items if i.findtext('label')==name)
   self.assertEqual(item.findtext('visible'),'!'+p.MOVIE_FILTER)
   self.assertFalse(any(c.get('condition')==p.MOVIE_FILTER for c in item.findall('onclick')))
 def test_tile_artwork_yields_without_requests_and_can_abort(self):
  requests=[];props={}
  p.genre_photos(lambda *a:requests.append(a),props.__setitem__,lambda:'{"time":0,"photos":{"18":"cached-photo"}}',lambda t:None,
                 lambda:10**9,busy=lambda:True,wait=lambda seconds:True)
  self.assertEqual(requests,[]);self.assertEqual(props[p.GENRE_PHOTO+'18'],'cached-photo')
 def test_refresh_resumes_after_busy_period_and_is_paced(self):
  waits=[];busy=iter([True,False]);requests=[]
  p.genre_photos(lambda *a:requests.append(a) or {'files':[]},lambda *a:None,lambda:'',lambda t:None,lambda:1000,
                 busy=lambda:next(busy,False),wait=lambda seconds:waits.append(seconds) or False)
  self.assertEqual(len(requests),len(p.CATEGORIES));self.assertEqual(waits[0],2);self.assertEqual(waits.count(0.2),len(p.CATEGORIES))

if __name__=='__main__':unittest.main()
