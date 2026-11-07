"""Transfer posters use the library cache; lookups run with an explicit bounded worker budget."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import transfer_artwork as art,drivelibrary
class Artwork(unittest.TestCase):
 def test_movie_and_episode_use_readable_titles_and_shared_posters(self):
  cache={'movie:interstellar:2014':{'poster':'poster.jpg'},'tv:lanterns:':{'poster':'show.jpg'}}
  m=art.describe('Interstellar.2014.2160p.HDR.mkv',cache)
  self.assertEqual(m['title'],'Interstellar (2014)');self.assertEqual(m['poster'],'poster.jpg')
  e=art.describe('Lanterns.S01E01.Pilot.2160p.10bit.mkv',cache)
  self.assertEqual(e['poster'],'show.jpg');self.assertIn('Episode 1',e['detail']);self.assertIn('4K',e['detail'])
 def test_cached_render_never_needs_network(self):
  self.assertEqual(art.describe('Unknown.2026.1080p.mkv')['poster'],'')
 def test_hydration_stops_on_close_and_limits_lookups(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[]
   def get(url):calls.append(url);return b'{"results":[]}'
   art.hydrate(tmp,['One.2026.mkv'],'key',get,active=lambda:False);self.assertEqual(calls,[])
   art.hydrate(tmp,['One.2026.mkv','Two.2026.mkv'],'key',get,max_titles=1);self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
