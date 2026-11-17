import json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_independent as si
import sports_jet as sj

class Independent(unittest.TestCase):
 def test_listings_and_no_jet(self):
  body='<article class="game-card-row"><h3 aria-label="A vs B"></h3><a href="/watch/match-1">watch</a><p class="game-card-league">NBA</p><time dateTime="2026-11-17T01:15:00Z"></time></article>'
  item=si.StreamsCenter(get=lambda url:(url,body)).get_items()[0]
  self.assertEqual((item.title,item.league,item.links[0].address),('A vs B','NBA','https://streamcenter.st/watch/match-1'))
  with patch.object(sj,'import_jet',return_value=(None,'missing')):
   sources,kind=sj.JetProvider()._extractors()
  self.assertEqual((sources[0].name,kind),(si.NAME,'independent'))
 def test_resolves_only_verified_hls_after_embed(self):
  uid='12345678-1234-1234-1234-123456789abc';calls=[]
  def get(url,referer=si.BASE+'/'):
   calls.append(url)
   if '/watch/' in url:return url,'{"id":"%s","provider":"one"}'%uid
   if '/api/' in url:return 'https://embed.invalid/a','<iframe src="https://embed.invalid/b"></iframe>'
   if url.endswith('/b'):return url,'<script>"https://video.invalid/live.m3u8"</script>'
   return url,'#EXTM3U\n#EXT-X-VERSION:3\n'
  address,headers=si.resolve(si.BASE+'/watch/test',get)
  self.assertEqual(address,'https://video.invalid/live.m3u8');self.assertEqual(headers['Referer'],'https://embed.invalid/b');self.assertEqual(headers['Origin'],'https://embed.invalid')
  with self.assertRaises(RuntimeError):si.resolve(si.BASE+'/watch/test',lambda *a:(a[0],'<html>not a video</html>'))
 def test_rejects_local_and_bad_game_urls(self):
  for address in ['http://127.0.0.1/x','http://localhost/x','http://[::1]/x','file:///x']:
   self.assertFalse(si.public_url(address))
  with self.assertRaises(ValueError):si.resolve('https://attacker.invalid/watch/one')
 def test_independent_listing_does_not_wait_for_jet_initialization(self):
  import threading,datetime
  release=threading.Event();published=[]
  item=NS(title='A vs B',links=[si.Link(si.BASE+'/watch/test')],starttime=datetime.datetime.now(),status='LIVE',league='NBA')
  def blocked():
   release.wait(3)
   return None,'blocked'
  with patch.object(si.StreamsCenter,'get_items',return_value=[item]),patch.object(sj,'import_jet',side_effect=blocked):
   provider=sj.JetProvider(publish=lambda data:published.append(data))
   done=provider._start()
   for _ in range(100):
    if any(x.get('records') for x in published):break
    threading.Event().wait(.01)
   self.assertTrue(any(x.get('records') for x in published))
   self.assertFalse(done.is_set())
   release.set();self.assertTrue(done.wait(2))
 def test_play_request_routes_independent_without_jet_import(self):
  calls=[]
  with patch.object(si,'resolve',return_value=('https://video.invalid/live.m3u8',{})),patch.object(sj,'import_jet',side_effect=AssertionError('Jet called')),patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda path:calls.append(path))),'xbmcgui':NS()}):
   self.assertTrue(sj.play_one(json.dumps({'e':si.NAME,'l':{'address':si.BASE+'/watch/test'}}),lambda s:None))
  self.assertTrue(calls[0].startswith(sj.JETPROXY))
if __name__=='__main__':unittest.main()
