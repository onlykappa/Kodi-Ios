"""ISSUE-285: copy retries and stops say why, not only the error's type."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import debrid_drive  # noqa: E402


class RetryLog(unittest.TestCase):
    def test_retry_line_names_the_error(self):
        source = (LIB / 'debrid_drive.py').read_text()
        line = source[source.index("; trying it again after the others (%d of %d)"):][:200]
        self.assertIn('_said(error)', line)

    def test_said_keeps_words_and_removes_links(self):
        text = debrid_drive._said(RuntimeError('Drive upload: HTTP 403 https://www.googleapis.com/upload?key=abc'))
        self.assertIn('Drive upload: HTTP 403', text)
        self.assertNotIn('googleapis', text)
        self.assertLessEqual(len(debrid_drive._said(RuntimeError('x' * 500))), 160)

    def test_startup_stop_names_the_error(self):
        source = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn("downloads stopped (%s: %s)", source)


if __name__ == '__main__':
    unittest.main()
