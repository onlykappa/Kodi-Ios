"""ISSUE-083: which videos go to Apple's player (directly, or converted on the phone by KodiAirPlay r5) and what the
person sees when AirPlay cannot play. The remuxer itself has C host tests (migration/airplay-ios/remux/tests)."""
import importlib.util,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
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
  self.assertIn('cast.airplay_source(playing,url,converting)',source)
  self.assertIn('AirPlay streams from this iPhone: keep Kodi open.',source)
 def test_a_prepared_mp4_also_uses_the_phones_own_link(self):
  # Owner build 157: Scary.Movie...mp4 (prepared) went out as http://10.0.0.247:57527/... and was refused.
  playing='http://127.0.0.1:57527/download/1/1/abc/Scary.Movie.2026.2160p.mp4'
  wifi='http://10.0.0.247:57527/download/1/1/abc/Scary.Movie.2026.2160p.mp4'
  self.assertEqual(cast.airplay_source(playing,wifi,True),playing)
  self.assertEqual(cast.airplay_source(playing,wifi,False),wifi)   # an older framework gives Apple's player the link

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
     def close(self):pass
    return R()
  last=dl.follow('plugin://plugin.video.elementum/show/95350/season/1/download',opener=Opener())
  self.assertEqual(seen[0],'http://127.0.0.1:65220/show/95350/season/1/download')
  self.assertEqual(last,'http://127.0.0.1:65220/play?uri=x&type=episode&background=true')
  self.assertIn("dl.follow(url)",(ROOT/'migration/bundled-bootstrap/download.py').read_text())

class KodiStaysPaused(unittest.TestCase):
 def test_airplay_playing_does_not_stop_kodi(self):
  # Owner build-136 log: player.stop() right after "playing" rotated the app and the TV dropped the session.
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  body=source[source.index('def send_airplay('):source.index('def send(xbmc')]
  playing=body[body.rindex("if outcome=='playing':"):body.rindex("lib.kodi_airplay_close();airplay.clear_busy(home)")]
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
  for needle in ('kodi_airplay_message','kr_remux_start_for(ticket,copy, 1,','kr_remux_kind(url) == KR_DIRECT','retirePlaybackFor(self.generation)','exported_symbols_list',
                 'FFmpeg symbols exported','showProblem(','THIRD-PARTY-NOTICES'):
   self.assertIn(needle,build)
  self.assertGreaterEqual(build.count('stopRemuxFor('),4)  # wrapper, new direct play and explicit close
  stop=build[build.index('static void stopRemuxFor('):build.index('static BOOL tvRoute(')]
  self.assertLess(stop.index('kr_remux_cancel(ticket)'),stop.index('dispatch_async(remuxQueue()'))

 def test_native_ownership_and_screen_lock_lifetime(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  restart=build[build.index('BOOL (^restartCompat)'):build.index('return YES;',build.index('BOOL (^restartCompat)'))]
  self.assertLess(restart.index('kr_remux_begin(1)'),restart.index('dispatch_async(remuxQueue()'))
  self.assertIn('os_unfair_lock_lock(&ownershipLock)',restart)
  presentation=build[build.index('[top presentViewController:holder animated:YES completion:'):]
  self.assertIn('routeWatch=[NSTimer',presentation)
  self.assertIn('kr_remux_player(holder.ticket',presentation)
  self.assertIn('atomic_load(&airplayState)>=0 && player.timeControlStatus',presentation)
  observer=build[build.index('static void watchPlayback('):build.index('static void presentPlayer(')]
  for needle in ('AVPlayerItemDidPlayToEndTimeNotification','AVPlayerItemFailedToPlayToEndTimeNotification',
                 '__weak AVPlayer','current.currentItem!=note.object','playbackStateFor(generation,0,0)',
                 'playbackStateFor(generation,-1,0)'):
   self.assertIn(needle,observer)
  self.assertIn('AVPlayerAudiovisualBackgroundPlaybackPolicyContinuesIfPossible',build)
  keep=build[build.index('static void keepUpdate(void) {'):]
  owned=keep[:keep.index('const BOOL run')]
  self.assertIn('atomic_load(&playbackActive)',owned)
  self.assertIn('[keepPlayer stop]',owned)

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
  import re
  # The pinned framework is r48 or newer (AI upscaling), and 'previous' is the one before it.
  tag=lock['framework_release']['tag'];number=int(re.fullmatch(r'kodi-airplay-r(\d+)',tag).group(1))
  self.assertGreaterEqual(number,48)
  self.assertRegex(lock['framework_release']['sha256'],r'^[0-9a-f]{64}$')
  self.assertEqual(lock['previous']['tag'],'kodi-airplay-r%d'%(number-1))
  # The digests come from each pin's own verified run (recorded in pin_note); a pin always names its run.
  self.assertRegex(lock['previous']['sha256'],r'^[0-9a-f]{64}$')
  self.assertNotEqual(lock['previous']['sha256'],lock['framework_release']['sha256'])
  self.assertIsInstance(lock['verified_run'],int)
  if 'staged_note' not in lock:   # a staged release (zero sha, built by CI on its branch) is pinned after its run is checked
   self.assertIn(str(lock['verified_run']),lock.get('pin_note',''))
 def test_r48_upscaler_in_the_framework(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('kr_upscale.m','kr_upscale_stub.c ]] && continue','_kodi_airplay_prepare_upscale','_kodi_device_state',
                 'VTSuperResolutionScalerConfiguration','weak external','Xcode_2[6-9]','iOS 26 SDK'):
   self.assertIn(needle,build)
  engine=(ROOT/'migration/airplay-ios/remux/src/kr_upscale.m').read_text()
  for needle in ('isSupported','configurationModelStatus','downloadConfigurationModelWithCompletionHandler','startSessionWithConfiguration',
                 'processWithParameters','endSession','VTSuperResolutionScalerParametersSubmissionModeSequential',
                 'VTLowLatencySuperResolutionScalerConfiguration','@available(iOS 26.0, *)','thermalState','batteryMonitoringEnabled'):
   self.assertIn(needle,engine)
  ci=(ROOT/'.github/workflows/airplay-remux.yml').read_text()
  self.assertIn('tests/upscale_host.py',ci)

class BackgroundRetry(unittest.TestCase):
 def test_r51_silence_is_tried_again_after_an_interruption(self):
  # Owner log ed63fe73 (build 317): iOS interrupted the silent audio and never said it ended; the framework refused
  # every restart for 62 minutes while the add-on asked every second, and copies crawled.
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  keep=build.split('static void keepUpdate(void) {',1)[1].split('__attribute__((visibility("default"))) void kodi_background_keep',1)[0]
  for needle in ('KEEP_FIRST_RETRY_S','KEEP_RETRY_S','keepRetriedAt=now;keepInterrupted=NO;retrying=YES','if(retrying && !playing){keepInterrupted=YES'):
   self.assertIn(needle,keep)
  self.assertNotIn('if(keepInterrupted){atomic_store(&keepState,-2);return;}',keep)
  self.assertIn('keepInterruptedAt=NSProcessInfo.processInfo.systemUptime',build)

class SlowSource(unittest.TestCase):
 def test_r52_a_slow_source_is_not_taken_for_sound_only(self):
  # Owner log 3b94b426 (build 319, Umbrella stream): video segment 1 took 39 s; the TV had asked for it all along, and
  # the sound-only check restarted an H.264 movie in compat mode (a long wait, then broken sound).
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  src=ROOT/'migration/airplay-ios/remux/src'
  self.assertIn('int kr_remux_video_waiting(void);',(src/'kr_remux.h').read_text())
  self.assertIn('int kr_remux_video_waiting(void) { return atomic_load(&demand[R_VCOPY]) + atomic_load(&demand[R_VCOMPAT]); }',(src/'kr_remux.c').read_text())
  guard=build.index('externalTicks >= 30 && kr_remux_video_waiting() > 0')
  self.assertLess(guard,build.index('playerNote(@"the TV takes audio segments but no video ones'))
  self.assertIn('} else if (!warned && external && externalTicks >= 30 && player.timeControlStatus',build)

class SlowSourceNote(unittest.TestCase):
 def test_a_slow_stream_is_told_once(self):
  # E18 / ISSUE-186 (owner log 3b94b426): segment 0 in 18 s, segment 1 in 39 s of source reading.
  sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
  import airplay
  class W:
   def __init__(self):self.p={}
   def getProperty(self,k):return self.p.get(k,'')
   def setProperty(self,k,v):self.p[k]=v
  w=W()
  fast='copy: video segment 3 in 900 ms, source I/O 800 ms, result 0'
  slow0='copy: video segment 0 in 17977 ms, source I/O 17957 ms, result 0'
  slow1='copy: video segment 1 in 39128 ms, source I/O 35055 ms, result -5'
  self.assertFalse(airplay.slow_source([fast],w,1000))
  self.assertFalse(airplay.slow_source([slow0],w,1000))              # one slow segment is not yet a pattern
  self.assertTrue(airplay.slow_source([slow1],w,1005))
  self.assertFalse(airplay.slow_source([slow1],w,1010))              # told once
  w2=W()
  self.assertTrue(airplay.slow_source(['player: the TV is waiting for a video segment the source has not delivered yet (slow source, not the codec)'],w2,5))
  self.assertTrue(airplay.slow_source([slow0,slow1],w,1000+4000))    # a new session an hour later
  self.assertIn("slow_note(lines))},daemon=True).start()",(ROOT/'migration/bundled-bootstrap/service.py').read_text())

class PictureBridge(unittest.TestCase):
 def test_compat_restart_once_in_the_framework(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  for needle in ('kr_remux_start_for(ticket,copy, 1, 0,','kr_remux_start_for(restartTicket,source, 1, keepPicture ? KR_COMPAT_SEGMENTED : 1,','compatTried','Converting the picture for this TV',
                 'replaceCurrentItemWithPlayerItem','seekToTime:','showNoPicture(hevc)','kr_remux_compat()',
                 '-framework VideoToolbox','-framework CoreVideo','libswscale.a','h264_videotoolbox'):
   self.assertIn(needle,build)
  self.assertIn('r7:',build.split('set -euo pipefail')[0])
 def test_ffmpeg_lgpl_with_videotoolbox(self):
  ff=(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text()
  for needle in ('--enable-decoder=hevc','--enable-swscale','--enable-videotoolbox','--enable-encoder=h264_videotoolbox',
                 '--enable-hwaccel=hevc_videotoolbox'):
   self.assertIn(needle,ff)
  ios=ff.split('case "$TARGET" in',1)[0]+ff.split('  ios)',1)[1].split('  host)',1)[0]
  code=[l.split('#')[0] for l in ios.splitlines()]
  self.assertIn('if [[ "${KR_HDR_TESTS:-0}" == 1 ]]',ff)
  self.assertIn('--enable-encoder=hevc_videotoolbox',ios)
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
  for needle in ('mfi_airplay_device','kr_hls_master_selected(S.gm,S.base,1,"cvideo",S.burn_index)','prefetch_after(rend','cache_take(',
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
  self.assertEqual(build.count('kr_remux_start_for(restartTicket,source, 1, keepPicture ? KR_COMPAT_SEGMENTED : 1,'),1)  # one guarded restart path


class R9Speed(unittest.TestCase):
 """r9 (owner build-138): converted 4K HEVC segments took 5-9 s, skips stalled, subtitle segments were empty."""
 def test_gpu_scaling_and_seek_robustness(self):
  src=ROOT/'migration/airplay-ios/remux/src'
  video=(src/'kr_video.c').read_text()+(src/'kr_color.c').read_text()
  for needle in ('VTPixelTransferSessionTransferImage','AV_PIX_FMT_VIDEOTOOLBOX; c->sw_pix_fmt = AV_PIX_FMT_NV12',
                 'TARGET_OS_IPHONE','__builtin_available(iOS 16.0, *)','"threads", 0','prio_speed'):
   self.assertIn(needle,video)
  code=(src/'kr_remux.c').read_text()
  for needle in ('t_err','session stopped','atomic_store(&vc_seg, seg)','pthread_cond_timedwait(&SC.changed',
                 'if (third || S.compat) prefetch_push(R_VCOMPAT, 0);'):
   self.assertIn(needle,code)
  # Source retry/seek behavior is exercised by compiled fault-injection tests; do not require the old
  # nested HTTP reconnect/AVSEEK_FORCE implementation, which could exceed its timeout repeatedly.
  gm=(src.parent/'gmplayer/gm_stream.c').read_text()
  # Caption seeks and first-cue fallback are covered by native remote-MP4 regressions.
  self.assertIn('"subtitle read"',gm)
  self.assertIn('Second line',(src.parent/'tests/test_remux.c').read_text())
  self.assertIn('r9:',(ROOT/'migration/airplay-ios/build-airplay.sh').read_text().split('set -euo pipefail')[0])
class R10BurnedSubtitles(unittest.TestCase):
 """r10: third-party AirPlay TVs ignore WebVTT; Kodi's current subtitle is burned into the converted picture."""
 def test_choice_follows_kodi(self):
  now=10_000_000
  on=lambda **c:{'subtitleenabled':True,'currentsubtitle':c}
  self.assertEqual(airplay.subtitle_choice({},[],now),(-2,'',''))
  self.assertEqual(airplay.subtitle_choice({'subtitleenabled':False,'currentsubtitle':{'index':1}},[],now),(-1,'',''))
  self.assertEqual(airplay.subtitle_choice(on(index=1,language='eng',name='English'),[],now),(1,'','eng'))
  self.assertEqual(airplay.subtitle_choice(on(index=None,language='eng'),[],now),(-2,'','eng'))
  files=[('/t/a4ksubtitles/Movie.2024.WEB.eng.srt',now-60),('/t/old.srt',now-5*3600),('/t/notes.txt',now)]
  # Kodi names an external subtitle after its file: that file is the choice.
  self.assertEqual(airplay.subtitle_choice(on(index=3,language='eng',name='Movie.2024.WEB.eng'),files,now),
                   (-2,'/t/a4ksubtitles/Movie.2024.WEB.eng.srt','eng'))
  # An embedded one keeps its number; the recent file is only the fallback past the file's own subtitles.
  self.assertEqual(airplay.subtitle_choice(on(index=0,language='fre',name='French'),files,now),
                   (0,'/t/a4ksubtitles/Movie.2024.WEB.eng.srt','fre'))
  self.assertEqual(airplay.subtitle_choice(on(index=0,language='fre',name='French'),files[1:],now),(0,'','fre'))
 def test_sent_before_playing(self):
  calls=[]
  class X:
   LOGINFO=1
   @staticmethod
   def executeJSONRPC(q):
    import json
    m=json.loads(q)['method']
    return json.dumps({'result':[{'playerid':1,'type':'video'}]} if m=='Player.GetActivePlayers' else
                      {'result':{'subtitleenabled':True,'currentsubtitle':{'index':2,'language':'eng','name':'English'}}})
  vfs=types.SimpleNamespace(translatePath=lambda p:'/nonexistent/'+p.split('//')[1])
  lib=types.SimpleNamespace(kodi_airplay_subtitles=lambda *a:calls.append(a))
  self.assertEqual(airplay.send_subtitles(lib,X,vfs,0),(2,'','eng'))
  self.assertEqual(calls,[(2,b'',b'eng')])
  X.ISO_639_1=1;X.ISO_639_2=2;X.convertLanguage=staticmethod(lambda lang,fmt:'en' if fmt==1 else 'eng')
  self.assertEqual(airplay.send_subtitles(lib,X,vfs,0),(2,'','eng|en'))
  self.assertEqual(calls[-1],(2,b'',b'eng|en'))
  self.assertIsNone(airplay.send_subtitles(types.SimpleNamespace(),X,vfs,0))
  source=(ROOT/'migration/bundled-bootstrap/cast.py').read_text()
  self.assertLess(source.index('airplay.send_subtitles('),source.index("lib.kodi_airplay_play(source.encode"))
 def test_external_bitmap_choice(self):
  now=10_000_000
  props={'subtitleenabled':True,'currentsubtitle':{'index':4,'language':'eng','name':'Movie.PGS'}}
  files=[('/t/Movie.PGS.sup',now-60),('/t/other.srt',now)]
  self.assertEqual(airplay.subtitle_choice(props,files,now),(-2,'/t/Movie.PGS.sup','eng'))
  props['currentsubtitle']['name']='Movie.DVD.sub'
  self.assertEqual(airplay.subtitle_choice(props,[('/t/Movie.DVD.idx',now-30)],now),(-2,'/t/Movie.DVD.idx','eng'))
  props['subtitleenabled']=False
  self.assertEqual(airplay.subtitle_choice(props,files,now),(-1,'',''))
 def test_bitmap_discovery_keeps_vobsub_pair(self):
  def translate(folder):
   if folder==airplay.SUB_DIRS[0]:return '/subs'
   raise OSError('not present')
  entries=['Movie.sup','Other.idx','Other.sub','UPPER.IDX','UPPER.SUB','partial.idx','notes.txt']
  found=airplay.recent_subtitle_files(translate,lambda p:entries,lambda p:123)
  self.assertEqual(set(found),{('/subs/Movie.sup',123),('/subs/Other.idx',123),('/subs/UPPER.IDX',123)})
 def test_framework_r11(self):
  """r11 (owner logs): audio waited 5.5 s behind WebVTT reads on its shared lane and the TV hung up."""
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('r11:',build.split('set -euo pipefail')[0])
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  for needle in ('subs_demuxer()','sgm_lock','strip_subtitles(S.master_compat)','PF_DEPTH_AUDIO 6','kr_video_path(v)'):
   self.assertIn(needle,remux)
  subs=remux[remux.index('/subs/%d/seg%d.vtt'):remux.index('sscanf(path, "/audio/%d/", &idx) == 1) {')]
  self.assertNotIn('agm_lock',subs);self.assertNotIn('gm_lock)',subs.replace('sgm_lock)',''))
 def test_framework_r10(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('r10:',build.split('set -euo pipefail')[0])
  for needle in ('_kodi_airplay_subtitles','kr_remux_set_subtitles(ordinal, file, lang)','build-libass.sh','libass.a','r10 libass burn-in missing'):
   self.assertIn(needle,build)
  libass=(ROOT/'migration/airplay-ios/build-libass.sh').read_text()
  self.assertEqual(libass.count('_SHA256='),4);self.assertIn('sha256sum -c',libass);self.assertIn('--disable-fontconfig',libass)
  self.assertNotIn('--enable-libass',(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text())
  notices=(ROOT/'migration/airplay-ios/remux/THIRD-PARTY-NOTICES').read_text()
  for needle in ('libass 0.17.4','ISC License','FreeType License (FTL','FriBidi 1.0.16','Lesser General Public License version 2.1',
                 'REMUX_LIBASS','HarfBuzz 11.2.1','Fonts: none are shipped'):
   self.assertIn(needle,notices)
  src=ROOT/'migration/airplay-ios/remux/src'
  video=(src/'kr_video.c').read_text()+(src/'kr_color.c').read_text()
  for needle in ('kr_subs_blend','CVPixelBufferLockBaseAddress','sub_lookback'):self.assertIn(needle,video)
  self.assertIn('test_burn_video',(src.parent/'tests/test_remux.c').read_text())
if __name__=='__main__':unittest.main()
