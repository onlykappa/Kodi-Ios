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

class KodiStaysPaused(unittest.TestCase):
 def test_airplay_playing_does_not_stop_kodi(self):
  # Owner build-136 log: player.stop() right after "playing" rotated the app and the TV dropped the session.
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  body=source[source.index('def send_airplay('):source.index('def send(xbmc')]
  playing=body[body.index("if outcome=='playing':"):body.index("lib.kodi_airplay_close()")]
  self.assertNotIn('player.stop()',playing);self.assertIn('player.pause()',playing)

class RokuFallsBackToAirPlay(unittest.TestCase):
 def test_refused_roku_goes_to_airplay(self):
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  refused=source[source.index('except cast.TVRefused as error:'):]
  self.assertLess(refused.index("tv['kind']=='roku' and library"),refused.index('dialog.ok'))
  self.assertIn('send_airplay(xbmc,dialog,player,library,url,title,playing);return',refused)

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

class AirPlayLog(unittest.TestCase):
 def test_old_framework_has_no_log(self):
  old=types.SimpleNamespace()
  self.assertEqual(airplay.log_lines(old),[])
  written=[];airplay.relay(old,written.append,lambda s:True);self.assertEqual(written,[])
 def test_lines_are_drained_and_relayed(self):
  chunks=[b'master: BANDWIDTH=8000000,CODECS="hvc1.2.4.L120.90,mp4a.40.2"\nGET /video/seg0.m4s 200 1834 B 12 ms\n',b'']
  def fill(buffer,size):
   data=chunks.pop(0) if chunks else b'';buffer.value=data;return len(data)
  lib=types.SimpleNamespace(kodi_airplay_log=fill)
  self.assertEqual(airplay.log_lines(lib),['master: BANDWIDTH=8000000,CODECS="hvc1.2.4.L120.90,mp4a.40.2"','GET /video/seg0.m4s 200 1834 B 12 ms'])
  chunks[:]=[b'player: closed at 12.0 s\n',b''];written=[]
  airplay.relay(lib,written.append,lambda s:True)
  self.assertEqual(written,['Kodi iOS AirPlay: player: closed at 12.0 s'])
 def test_wired_into_cast_service_and_framework(self):
  self.assertIn("airplay.log_lines(lib)",(ROOT/'migration/bundled-bootstrap/cast.py').read_text())
  self.assertIn("target=airplay.relay",(ROOT/'migration/bundled-bootstrap/service.py').read_text())
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('_kodi_airplay_log','int kodi_airplay_log(char *buf, int len)','kr_remux_log(','showNoPicture(hevc)',
                 "can't play HEVC",'kr_remux_served(1) == video0','presentationSize'):
   self.assertIn(needle,build)
  lock=__import__('json').loads((ROOT/'migration/airplay-ios/source-lock.json').read_text())
  self.assertEqual(lock['framework_release']['tag'],'kodi-airplay-r9')
  self.assertEqual(lock['previous']['tag'],'kodi-airplay-r8')
  self.assertEqual(lock['previous']['sha256'],'4ab229cc846cd87dc417f770a24dc09ea011e7d7e92410a61c01ca808916ef9c')

class PictureBridge(unittest.TestCase):
 def test_compat_restart_once_in_the_framework(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('kr_remux_start(copy, 1, 0,','kr_remux_start(source, 1, 1,','compatTried','Converting the picture for this TV',
                 'replaceCurrentItemWithPlayerItem','seekToTime:','showNoPicture(hevc)','kr_remux_compat()',
                 '-framework VideoToolbox','-framework CoreVideo','libswscale.a','h264_videotoolbox'):
   self.assertIn(needle,build)
  self.assertIn('r7:',build.split('set -euo pipefail')[0])
 def test_ffmpeg_lgpl_with_videotoolbox(self):
  ff=(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text()
  for needle in ('--enable-decoder=hevc','--enable-swscale','--enable-videotoolbox','--enable-encoder=h264_videotoolbox',
                 '--enable-hwaccel=hevc_videotoolbox'):
   self.assertIn(needle,ff)
  code=[l.split('#')[0] for l in ff.splitlines()]
  for banned in ('--enable-gpl','--enable-nonfree','libx264','openh264','--disable-swscale'):
   self.assertFalse(any(banned in l for l in code),banned)
 def test_remuxer_compat_api_and_codecs(self):
  src=ROOT/'migration/airplay-ios/remux/src'
  self.assertIn('int kr_remux_start(const char *url, int lan, int compat, char *out, int outlen);',(src/'kr_remux.h').read_text())
  self.assertIn('#define KR_VIDEO_CODECS "avc1.640028"',(src/'kr_video.h').read_text())
  self.assertIn('kr_video_abort(S.video)',(src/'kr_remux.c').read_text())
  self.assertIn('libswscale.a',(src.parent/'tests/run_host_tests.sh').read_text())
  self.assertIn('AetherEngine',(src.parent/'THIRD-PARTY-NOTICES').read_text())

class PerReceiver(unittest.TestCase):
 """r8 (owner build-136): a TCL Roku TV read the HEVC master and init, hung up on the segments and AirPlay went off
 within ~10 s, before r7's 30 s sound-only check."""
 def test_remuxer_tells_receivers_apart(self):
  src=ROOT/'migration/airplay-ios/remux/src'
  header=(src/'kr_remux.h').read_text();code=(src/'kr_remux.c').read_text()
  for needle in ('int kr_remux_third_party_receiver(const char *ua);','int kr_remux_compat_clients(void);',
                 'int kr_remux_served_external(int video);','int kr_remux_prefetched(void);'):
   self.assertIn(needle,header)
  for needle in ('mfi_airplay_device','kr_hls_master_at(S.gm, S.base, 1, "cvideo")','prefetch_after(rend','cache_take(',
                 'audio_demuxer()','kr_video_cancel(S.video)','prefetch_stop();'):
   self.assertIn(needle,code)
  tests=(src.parent/'tests/test_remux.c').read_text()
  for needle in ('MFi_AirPlay_Device','AppleCoreMedia/1.0.0.24A446 (iPhone','(Apple TV;','test_receivers(','test_latency(','/slow/'):
   self.assertIn(needle,tests)
  self.assertIn("startswith('/slow/')",(src.parent/'tests/range_server.py').read_text())
 def test_framework_falls_back_and_follows_the_screen(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('kr_remux_served_external(1) == 0','lasted <= 20','restartCompat(hevc)','kr_remux_compat_clients()',
                 'UIInterfaceOrientationMaskAllButUpsideDown','viewWillTransitionToSize:','setNeedsUpdateOfSupportedInterfaceOrientations',
                 'healKodi();','third_party_receiver|served_external|compat_clients'):
   self.assertIn(needle,build)
  self.assertNotIn('holder.mask',build)
  self.assertIn('r8:',build.split('set -euo pipefail')[0])
  self.assertEqual(build.count('kr_remux_start(source, 1, 1,'),1)  # one restart path for both triggers


class R9Speed(unittest.TestCase):
 """r9 (owner build-138): converted 4K HEVC segments took 5-9 s, skips stalled, subtitle segments were empty."""
 def test_gpu_scaling_and_seek_robustness(self):
  src=ROOT/'migration/airplay-ios/remux/src'
  video=(src/'kr_video.c').read_text()
  for needle in ('VTPixelTransferSessionTransferImage','AV_PIX_FMT_VIDEOTOOLBOX; c->sw_pix_fmt = AV_PIX_FMT_NV12',
                 'TARGET_OS_IPHONE','__builtin_available(iOS 16.0, *)','"threads", 0','prio_speed'):
   self.assertIn(needle,video)
  code=(src/'kr_remux.c').read_text()
  for needle in ('t_err','session stopped','atomic_store(&vc_seg, seg)','pthread_mutex_trylock(&S.gm_lock)',
                 'if (third || S.compat) prefetch_push(R_VCOMPAT, 0);'):
   self.assertIn(needle,code)
  source=(src/'kr_source.c').read_text()
  for needle in ('reconnect_delay_max','AVSEEK_FORCE','read_once('):
   self.assertIn(needle,source)
  gm=(src.parent/'gmplayer/gm_stream.c').read_text()
  self.assertIn('av_seek_frame(s->in, -1, (int64_t)(seek_to * AV_TIME_BASE)',gm)
  self.assertIn('"subtitle read"',gm)
  self.assertIn('Second line',(src.parent/'tests/test_remux.c').read_text())
  self.assertIn('r9:',(ROOT/'migration/airplay-ios/build-airplay.sh').read_text().split('set -euo pipefail')[0])
if __name__=='__main__':unittest.main()
