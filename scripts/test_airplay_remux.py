"""ISSUE-083: which videos go to Apple's player (directly, or converted on the phone by KodiAirPlay r5) and what the
person sees when AirPlay cannot play. The remuxer itself has C host tests (migration/airplay-ios/remux/tests)."""
import importlib.util,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
def load(name):
 spec=importlib.util.spec_from_file_location(name,LIB/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
cast=load('cast');airplay=load('airplay')

class Routing(unittest.TestCase):
 def test_old_framework_sends_only_apple_containers(self):
  self.assertTrue(cast.apple_playable('http://192.168.1.4:65220/files/a/Movie.mp4'))
  self.assertFalse(cast.apple_playable('http://192.168.1.4:65220/files/a/Movie.mkv'))
  self.assertFalse(cast.apple_playable('https://drive.google.com/uc?id=1&export=download'))
 def test_r5_converts_mkv_avi_webm_ts_and_unknown_links(self):
  for url in ('http://127.0.0.1:65220/files/Show/S01E01.mkv','http://x/a.AVI','http://x/a.webm','http://x/a.ts','http://x/a.m2ts'):
   self.assertTrue(cast.apple_playable(url,converts=True),url)
  self.assertTrue(cast.apple_playable('https://drive.google.com/uc?id=1&export=download',converts=True))
  self.assertTrue(cast.apple_playable('http://x/a.mkv|User-Agent=Kodi',converts=True))
  self.assertTrue(cast.apple_playable('http://x/stream','Movie.mkv',converts=True))
 def test_r5_still_refuses_known_other_formats(self):
  self.assertFalse(cast.apple_playable('http://x/a.wmv',converts=True))
  self.assertFalse(cast.apple_playable('http://x/a.flv','',converts=True))
  self.assertFalse(cast.apple_playable('',None,converts=True))

class PhoneSource(unittest.TestCase):
 def test_conversion_reads_the_link_kodi_plays(self):
  # Owner build-132: Drive's helper answers on 127.0.0.1 only; the Wi-Fi address was refused.
  playing='http://127.0.0.1:60047/download/1/1/abc/Movie.mkv|User-Agent=Kodi'
  self.assertEqual(cast.phone_source(playing,'http://192.168.1.11:60047/x'),'http://127.0.0.1:60047/download/1/1/abc/Movie.mkv')
  self.assertEqual(cast.phone_source('/var/mobile/Movie.mkv','http://fallback/x'),'http://fallback/x')
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  self.assertIn('cast.phone_source(playing,url)',source)
  self.assertIn('AirPlay converts this %s video on the phone',source)

class EpisodePicker(unittest.TestCase):
 def test_one_tap_picks_an_episode_and_empty_ticks_explain(self):
  source=(ROOT/'migration/bundled-bootstrap/download.py').read_text()
  self.assertIn("labels+['Several episodes...']",source)
  self.assertIn('No episode was ticked',source)
  self.assertLess(source.index("dialog.select('Season %s: which episode?'"),source.index('dialog.multiselect('))

class SeasonDownload(unittest.TestCase):
 def test_follows_elementum_redirects_over_http(self):
  import urllib.error,email.message
  dl=load('elementum_download');seen=[]
  hops={'/show/95350/season/1/download':'plugin://plugin.video.elementum/download?uri=x&type=episode',
        '/download':'plugin://plugin.video.elementum/play?uri=x&type=episode&background=true'}
  class Opener:
   def open(self,url,timeout):
    seen.append(url);path=url.split('65220',1)[1].split('?')[0]
    if path in hops:
     h=email.message.Message();h['Location']=hops[path];raise urllib.error.HTTPError(url,302,'Found',h,None)
    class R:
     def read(self):return b''
    return R()
  last=dl.follow('plugin://plugin.video.elementum/show/95350/season/1/download',opener=Opener())
  self.assertEqual(seen[0],'http://127.0.0.1:65220/show/95350/season/1/download')
  self.assertEqual(last,'http://127.0.0.1:65220/play?uri=x&type=episode&background=true')
  self.assertIn("if k=='movie'",(ROOT/'migration/bundled-bootstrap/download.py').read_text())

class Framework(unittest.TestCase):
 def test_message_only_from_r5(self):
  old=types.SimpleNamespace()
  self.assertFalse(airplay.converts(old));self.assertEqual(airplay.message(old),'')
  def fill(buffer,size):buffer.value=b'AirPlay cannot play this file: no video.';return 40
  new=types.SimpleNamespace(kodi_airplay_message=fill)
  self.assertTrue(airplay.converts(new));self.assertEqual(airplay.message(new),'AirPlay cannot play this file: no video.')
 def test_failure_text_names_the_reason_and_the_way_out(self):
  text=cast.CONVERT_FAILED%'AirPlay needs Wi-Fi.'
  self.assertIn('AirPlay needs Wi-Fi.',text);self.assertIn('Screen Mirroring',text)
 def test_converting_waits_longer_than_a_direct_link(self):
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  self.assertIn('60 if converting else 25',source)
  self.assertIn('airplay.message(lib)',source)
 def test_framework_exports_and_stops_the_server(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('kodi_airplay_message','kr_remux_start(copy, 1,','kr_remux_kind(url) == KR_DIRECT','stopRemux();','exported_symbols_list',
                 'FFmpeg symbols exported','showProblem(','THIRD-PARTY-NOTICES'):
   self.assertIn(needle,build)
  self.assertGreaterEqual(build.count('stopRemux();'),3)  # new direct play, Apple's player dismissed, kodi_airplay_close

if __name__=='__main__':unittest.main()
