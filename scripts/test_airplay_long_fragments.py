"""ISSUE-326 (owner's log ebc9c063): AirPlay of a prepared movie was slow and failed first time. Its fragments ran up to
63 s / 49 MB, Apple's player waited for whole fragments, and a subtitle segment answered a 503 after 8 s, past Apple's
6-s timeout. The C host test test_long_fragments (migration/airplay-ios/remux/tests) plays it; this checks the wiring."""
import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
TEST=(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text()

class LongFragments(unittest.TestCase):
 def test_long_fragments_take_the_segmented_route_for_any_receiver(self):
  limit=float(re.search(r'#define PREPARED_MAX_FRAGMENT_SECONDS ([0-9.]+)',SRC).group(1))
  self.assertLessEqual(limit,10)
  self.assertIn('prepared_playlists(2)==0 && prepared_longest>limit',SRC)
  self.assertIn('segmented=1;',SRC)
  # Roku's codec limits stay Roku's: an Apple TV keeps a 4K H.264 picture.
  self.assertIn('if(roku && !compat && selected>=0)',SRC)
 def test_subtitle_waits_end_before_apples_timeout(self):
  wait=int(re.search(r'#define SUB_WAIT_SECONDS (\d+)',SRC).group(1))
  self.assertLess(wait,6)
  self.assertIn('subtitle_part(idx,seg,SUB_WAIT_SECONDS,&buf)',SRC)
  self.assertNotIn('until.tv_sec+=8',SRC)
 def test_cue_files_behind_the_resume_point_are_empty_at_once(self):
  self.assertIn('kr_remux_subtitle_answer_now(seg)',SRC)
  self.assertIn('atomic_store(&sub_resume_seg,at>1?at:-1)',SRC)
  self.assertIn('if(seg>=resume-1){atomic_store(&sub_resume_seg,-1);return 0;}',SRC)
 def test_host_test_runs(self):
  self.assertIn('static void test_long_fragments(void)',TEST)
  self.assertEqual(TEST.count('test_long_fragments();'),2)
  self.assertIn('setenv("KR_PREPARED_MAX_FRAGMENT_S", "1e9", 1);',TEST)

if __name__=='__main__':unittest.main()
