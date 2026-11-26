"""Guarded HLS through the local proxy (roadmap step 14 finding): a client that sends no headers (as Kodi's player does after the first request) still plays."""
import sys,unittest,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import hls_bridge as hb, fresh_resolve as fr, backup_playback as bp, source_contract as c
from test_fresh_resolve import Site
from test_backup_playback import Player,pb

def plain_get(url):
 with urllib.request.urlopen(url,timeout=5) as r:return r.status,r.read()

class Bridge(unittest.TestCase):
 def setUp(self):self.site=Site()
 def tearDown(self):self.site.srv.shutdown();self.site.srv.server_close()
 def resolved(self,mode=None,token='t1'):
  if mode:self.site.mode=mode
  return fr.Resolved(self.site.url(),{'X-Token':token},0)
 def test_a_header_less_client_plays_master_variant_key_and_segment_through_the_proxy(self):
  url,headers,close=hb.prepare(self.resolved());self.assertEqual(headers,{});self.assertTrue(url.startswith('http://127.0.0.1:') and url.endswith('.m3u8'))
  try:
   status,master=plain_get(url);self.assertEqual(status,200);variant=[l for l in master.decode().splitlines() if l and not l.startswith('#')][0]
   status,var=plain_get(variant);lines=var.decode().splitlines();key=[l.split('URI="')[1].split('"')[0] for l in lines if l.startswith('#EXT-X-KEY')][0];seg=[l for l in lines if l and not l.startswith('#')][0]
   self.assertEqual(plain_get(key)[0],200);self.assertEqual(plain_get(seg)[0],200)
   self.assertTrue(all(h[1]=='t1' for h in self.site.hits),'the proxy sent the header upstream every time');self.assertTrue(all('sid=abc123' in (h[2] or '') for h in self.site.hits[1:]),'and kept the cookie')
   self.assertNotIn(self.site.url(),master.decode()+var.decode(),'the real address never reaches the player')
  finally:close()
 def test_close_stops_the_proxy(self):
  url,_,close=hb.prepare(self.resolved());close()
  with self.assertRaises(OSError):plain_get(url)
 def test_unguarded_hls_and_plain_files_pass_through(self):
  for r in (fr.Resolved('https://a.invalid/x.m3u8',{},0),fr.Resolved('https://a.invalid/x.mp4',{'X-Token':'1'},0)):
   url,headers,close=hb.prepare(r);self.assertEqual((url,headers,close),(r.url,r.headers,None))
 def test_a_refused_playlist_is_a_typed_outcome_not_a_crash(self):
  with self.assertRaises(c.Outcome):hb.prepare(self.resolved(token='wrong'))
 def test_playback_hands_the_proxy_url_to_the_player_and_closes_it_on_stop(self):
  p=Player();play=pb(p);self.assertEqual(play.start_resolved(('g',),lambda:self.resolved()),'playing')
  url,headers=p.calls[0][0],p.calls[0][1];self.assertEqual(headers,{});self.assertNotEqual(url,self.site.url());self.assertEqual(plain_get(url)[0],200)
  play.stop()
  with self.assertRaises(OSError):plain_get(url)

if __name__=='__main__':unittest.main()
