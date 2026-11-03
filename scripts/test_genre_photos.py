"""Owner (build-133): Search's genre tiles get a photo each (the genre's most popular show), cached for a week."""
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class GenrePhotos(unittest.TestCase):
 def run_once(self,cache='',now=1000.0,art=None):
  calls=[];props={};saved={}
  def rpc(method,params):
   calls.append(params['directory'])
   gid=params['directory'].split('with_genres=')[1].split('&')[0]
   return {'files':art(gid) if art else [{'art':{'fanart':'https://img/shared.jpg'}},{'art':{'fanart':'https://img/%s.jpg'%gid}}]}
  photos=p.genre_photos(rpc,props.__setitem__,lambda:cache,lambda t:saved.setdefault('text',t),lambda:now)
  return calls,props,saved,photos
 def test_one_photo_per_genre_no_repeats_and_cached(self):
  calls,props,saved,photos=self.run_once()
  self.assertEqual(len(calls),len(p.CATEGORIES))
  self.assertEqual(len(set(photos.values())),len(p.CATEGORIES))  # the shared top title is used once only
  self.assertEqual(props[p.GENRE_PHOTO+'18'],photos['18'])
  calls2,props2,_,_=self.run_once(cache=saved['text'],now=1000+3600)
  self.assertEqual(calls2,[]);self.assertEqual(props2,props)
  calls3,_,_,_=self.run_once(cache=saved['text'],now=1000+p.WEEK+1)
  self.assertEqual(len(calls3),len(p.CATEGORIES))
 def test_nothing_found_keeps_the_gradient(self):
  calls,props,saved,photos=self.run_once(art=lambda gid:[])
  self.assertEqual(props,{});self.assertNotIn('text',saved)
 def test_tiles_show_the_photo_under_a_tint(self):
  xml=p.search_window('<window><controls></controls></window>')
  xml=xml.decode() if isinstance(xml,bytes) else xml
  self.assertIn('$INFO[Window(Home).Property(Portrait.GenrePhoto.18)]',xml)
  # Style C: the photo, then a fade in the genre colour (Drama's dark blue) behind the label.
  self.assertLess(xml.index('ListItem.Property(photo)'),xml.index('colordiffuse="$INFO[ListItem.Property(tint)]"'))
  self.assertIn('<property name="tint">F20C1234</property>',xml)
 def test_loaded_only_when_search_opens(self):
  started=[];visible={'v':False}
  tick=p.genre_photos_tick(lambda c:visible['v'],lambda:started.append(1))
  tick();self.assertEqual(started,[])
  visible['v']=True;tick();tick();self.assertEqual(started,[1])

if __name__=='__main__':unittest.main()
