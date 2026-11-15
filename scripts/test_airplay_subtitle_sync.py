"""ISSUE-343 (owner log 1f143748, build 513: subtitles on the Apple TV "doubled up" and "so out of sync").

The WebVTT cue files said MPEGTS:900000 <-> LOCAL 0 (Apple's segmenter value for media that starts at 10 s) while the
video and audio segments keep the source's own absolute times, so every subtitle was 10 s late; and a line the subtitle
file draws on stacked layers became two cues. The C host tests (tests/test_remux.c, fixture h264_aac_layers.mkv) check
the served files; this checks the wiring."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMUX = ROOT / 'migration/airplay-ios/remux'


class SubtitleSync(unittest.TestCase):
    def test_one_header_with_media_time_zero(self):
        header = (REMUX / 'gmplayer/gm_stream.h').read_text()
        self.assertIn('#define GM_VTT_HEADER "WEBVTT\\nX-TIMESTAMP-MAP=MPEGTS:0,LOCAL:00:00:00.000\\n\\n"', header)
        for path in ('gmplayer/gm_stream.c', 'src/kr_remux.c'):
            source = (REMUX / path).read_text()
            self.assertNotIn('MPEGTS:900000', source, path)
            self.assertIn('GM_VTT_HEADER', source, path)

    def test_a_line_drawn_on_layers_is_one_cue(self):
        source = (REMUX / 'gmplayer/gm_stream.c').read_text()
        self.assertIn('vtt_seen seen[SEEN_MAX]', source)
        self.assertRegex(source, r'dup = seen\[k\]\.hash == hash && seen\[k\]\.len == text\.len')

    def test_the_host_tests_cover_it(self):
        tests = (REMUX / 'tests/test_remux.c').read_text()
        fixtures = (REMUX / 'tests/make_fixtures.sh').read_text()
        self.assertIn('"h264_aac_layers.mkv"', tests)
        self.assertIn('X-TIMESTAMP-MAP=MPEGTS:0,LOCAL:00:00:00.000', tests)
        self.assertIn('copies == 1', tests)
        self.assertEqual(len(re.findall(r'^Dialogue: [01],0:00:02.00,0:00:04.00,Default,,0,0,0,,.*Hello from layers$', fixtures, re.M)), 2)


if __name__ == '__main__':
    unittest.main()
