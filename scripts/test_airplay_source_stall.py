"""ISSUE-335 (owner logs 87d9a389 and 65cca4ce, build 502): AirPlay of a Drive copy froze 30 s on one Drive read that
sent nothing, read a 1080p episode at ~0.5 MB/s over one connection, and rescanned keyframes (5.6 s) on every cast.
The C host tests test_quiet_connection and test_long_fragments play these; this checks the wiring."""
import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'migration/airplay-ios/remux/src/kr_source.c').read_text()
REMUX=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
TEST=(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text()
SERVER=(ROOT/'migration/airplay-ios/remux/tests/range_server.py').read_text()

class QuietConnection(unittest.TestCase):
 def test_compat_replacement_also_waits_before_playing(self):
  objc=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  section=objc[objc.index('watchPlayback(player,next,generation);'):objc.index('externalTicks = 0; video0')]
  self.assertNotIn('[player play];',section)
  self.assertIn('initialSeekAllowed = NO; recoveryDeadline = ticks + 30;',section)
 def test_a_quiet_read_is_cut_and_retried(self):
  self.assertLessEqual(int(re.search(r'#define STALL_SECONDS (\d+)',SRC).group(1)),5)
  self.assertIn('else if(now-s->progress_ns>(int64_t)STALL_SECONDS*1000000000LL){s->stalled=1;return 1;}',SRC)
  self.assertIn('if (s->io) avio_closep(&s->io);   // never read again from a connection that went quiet',SRC)
  # Elementum's server waits for torrent pieces: no watchdog there.
  self.assertIn('!strstr(url,":65220/")',SRC)
 def test_helpers_only_for_slow_sequential_reads(self):
  self.assertIn('#define AHEAD_HELPERS 2',SRC)
  self.assertIn('if(!sequential || !slow || AHEAD_HELPERS<1)return;',SRC)
  self.assertIn('pthread_join(c->ahead_thread[h],NULL);',SRC)   # helpers stop with the last reader
 def test_keyframe_scan_is_saved(self):
  # ISSUE-346: the cache moved to kr_mp4.c, which the preparation shares.
  MP4=(ROOT/'migration/airplay-ios/remux/src/kr_mp4.c').read_text()
  self.assertIn('kr_mp4_cache_load(key,&raw,&origin)==0',REMUX)
  self.assertIn('if(!ok)kr_mp4_cache_save(key,&raw,0);',REMUX)
  self.assertIn('Library/Caches/KodiAirPlay',MP4)
 def test_a_tv_stuck_after_a_stall_is_played_again_then_reloaded(self):
  # ISSUE-336 (owner log 53a92f39): the TV paused at 7.4 s after a source stall and never resumed.
  objc=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('if (errors.count > errorsSeen) lastErrorTick = ticks;',objc)
  self.assertIn('lastErrorTick >= stuckSince - 15',objc)
  self.assertIn('kr_remux_video_waiting() == 0',objc[objc.index('ISSUE-336 (owner log 53a92f39'):])
  self.assertIn('recoveries < 3',objc)
  self.assertIn('[player replaceCurrentItemWithPlayerItem:next];',objc[objc.index('ISSUE-336 (owner log 53a92f39'):])
 def test_stall_reload_waits_for_owned_successful_seek_and_has_deadline(self):
  objc=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  timer=objc[objc.index('stallWatch = [NSTimer scheduledTimerWithTimeInterval:1.0'):]
  reload=timer[timer.index('still stuck at %.1f s after a source stall'):timer.index('waiting = player.timeControlStatus')]
  self.assertLess(reload.index('[player pause];'),reload.index('[player replaceCurrentItemWithPlayerItem:next];'))
  self.assertNotIn('[player play];',reload)
  self.assertIn('initialSeekAllowed = NO;recoveryDeadline = ticks + 30;',reload)
  seek=timer[timer.index('if (resumeAt >= 0 && item.status'):timer.index('// r6: Apple')]
  self.assertIn('generation!=atomic_load(&playGeneration)',seek)
  self.assertIn('player.currentItem!=seekItem',seek)
  self.assertIn('if (!done)',seek)
  self.assertLess(seek.index('if (!done)'),seek.index('[player play]'))
  self.assertIn('if (recoveryDeadline) return;',seek)
  self.assertIn('ticks >= recoveryDeadline',timer)
  self.assertIn('playbackStateFor(generation,-1,0)',timer[:timer.index('// r6: Apple')])
 def test_prepared_index_is_repaired_or_segmented(self):
  # ISSUE-337 (owner log d8524f8d): "no usable fragment index; Apple's player gets the MP4 itself", then -11819.
  self.assertIn('qsort(fr,(size_t)n,sizeof *fr,frag_by_offset);',REMUX)
  self.assertIn('serving six-second segments instead of the MP4 itself',REMUX)
  self.assertIn('!indexed && S.prepared_size>0 && prepared_fragmented()',REMUX)
  self.assertNotIn('if(n && (o<=fr[n-1].offset || t<fr[n-1].time))goto end;',REMUX)
  objc=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('__block AVPlayer *player = [AVPlayer playerWithURL:address];',objc)
  self.assertIn('if (player.status == AVPlayerStatusFailed) {',objc)
  self.assertIn('airplayController.player = fresh;',objc)
  self.assertIn('test_prepared_index_repairs();',TEST)
 def test_host_tests_run(self):
  self.assertIn('static void test_quiet_connection(const char *base)',TEST)
  self.assertIn('test_quiet_connection(argv[2]);',TEST)
  self.assertIn("second cast uses the saved keyframe scan",TEST)
  self.assertIn("'quiet'",SERVER)

if __name__=='__main__':unittest.main()
