"""ISSUE-289: Trakt and Elementum starting are not notifications; their failures still are."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import notices  # noqa: E402


class Routine(unittest.TestCase):
    def test_starts_are_dropped(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertIsNone(notices.add(p, 'general', 'Elementum', 'Elementum daemon has started'))
            self.assertIsNone(notices.add(p, 'general', 'Trakt connected', 'Your Trakt lists can fill Home'))
            self.assertIsNone(notices.add(p, 'info', 'TMDb Helper', 'Trakt authorised'))
            self.assertEqual(notices.load(p), [])

    def test_failures_stay(self):
        with tempfile.TemporaryDirectory() as p:
            notices.add(p, 'general', 'Elementum', 'Elementum daemon failed to start')
            notices.add(p, 'problem', 'Elementum', 'Elementum daemon has started but its web server refused')
            notices.add(p, 'general', 'Trakt', 'Could not connect to Trakt: token expired')
            notices.add(p, 'download', 'Saved to Google Drive', 'Rick and Morty · S3 E10')
            self.assertEqual(len(notices.load(p)), 4)

    def test_old_start_notices_disappear(self):
        with tempfile.TemporaryDirectory() as p:
            notices.save(p, [{'id': '1', 'time': 1, 'kind': 'general', 'title': 'Trakt connected', 'text': 'Your Trakt lists can fill Home'},
                             {'id': '2', 'time': 1, 'kind': 'general', 'title': 'Elementum', 'text': 'Elementum daemon has started'},
                             {'id': '3', 'time': 1, 'kind': 'drive', 'title': 'Saved to Google Drive', 'text': 'x'}])
            self.assertEqual([i['id'] for i in notices.load(p)], ['3'])


if __name__ == '__main__':
    unittest.main()
