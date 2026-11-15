"""ISSUE-309 (owner, build 477, log 47ee1590): background downloads ran at full speed while an Umbrella stream opened and
in its first seconds; now a play starting holds them (as Kodi buffering does) until the video has played SETTLE s."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import slowdown as sd  # noqa: E402


def mark(t):
    return json.dumps({'t': t, 'via': 'umbrella'})


class Opening(unittest.TestCase):
    def setUp(self):
        sd._play['video_since'] = None

    def test_the_opening_holds_downloads_until_the_video_has_settled(self):
        self.assertEqual(sd.play_reason(False, False, False, mark(100), now=101), 'buffering')    # Umbrella resolving
        self.assertEqual(sd.play_reason(False, False, False, mark(100), now=109), 'buffering')    # Kodi opening the file
        self.assertEqual(sd.play_reason(False, False, True, mark(100), now=110), 'buffering')     # the picture: still settling
        self.assertEqual(sd.play_reason(False, False, True, mark(100), now=124), 'buffering')
        self.assertEqual(sd.play_reason(False, False, True, mark(100), now=126), 'video')         # 16 s of video: slowed only

    def test_an_old_mark_or_none_changes_nothing(self):
        self.assertEqual(sd.play_reason(False, False, False, '', now=500), '')
        self.assertEqual(sd.play_reason(False, False, False, mark(100), now=100 + sd.OPENING_LIMIT + 1), '')
        self.assertEqual(sd.play_reason(False, False, True, 'not json', now=10), 'video')

    def test_airplay_and_kodi_buffering_keep_their_rules(self):
        self.assertEqual(sd.play_reason(True, False, False, mark(100), now=101), 'airplay')
        self.assertEqual(sd.play_reason(False, True, True, '', now=101), 'buffering')

    def test_buffering_holds_copies_preparation_and_downloads(self):
        self.assertIn('buffering', sd.HOLD)
        self.assertEqual(sd.CAP['buffering'], 0.0)

    def test_the_service_uses_it(self):
        source = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertEqual(source.count("slowdown.play_reason("), 2)
        self.assertIn("getProperty('KodiIOS.Open')", source)


if __name__ == '__main__':
    unittest.main()
