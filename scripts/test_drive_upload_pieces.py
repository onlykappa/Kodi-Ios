"""Build 197 (owner's build-196 log): every 32 MB piece of a resumable Drive upload answered 308, Drive's normal
"kept, send the next", and each was logged as an http_error. The log now says what it is, with the piece's speed."""
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True
import driveupload  # noqa: E402


class Pieces(unittest.TestCase):
    def send(self, code, method='PUT', body=b'x' * (32 * 1024 * 1024)):
        lines = []
        error = urllib.error.HTTPError('https://www.googleapis.com/upload?upload_id=SECRET', code, 'r', {}, io.BytesIO(b''))
        opener = type('O', (), {'open': lambda self, *a, **k: (_ for _ in ()).throw(error)})()
        clock = iter([0.0, 100.0, 100.0, 100.0])
        with patch.object(driveupload.urllib.request, 'build_opener', return_value=opener), \
                patch.object(driveupload.time, 'monotonic', lambda: next(clock)):
            status = driveupload.sender(None, log=lines.append)(method, 'https://www.googleapis.com/upload', body, {})[0]
        return status, lines

    def records(self, lines):
        return [json.loads(l.split('Kodi iOS diagnostic ', 1)[1]) for l in lines if 'Kodi iOS diagnostic ' in l]

    def test_a_kept_piece_is_logged_with_its_speed_not_as_an_error(self):
        status, lines = self.send(308)
        self.assertEqual(status, 308)
        self.assertIn('Drive upload: 32.0 MB piece in 100 s (0.32 MB/s)', lines)
        events = [r['event'] for r in self.records(lines)]
        self.assertEqual(events, ['piece'])
        self.assertNotIn('SECRET', ''.join(lines))

    def test_a_real_error_is_still_an_error(self):
        status, lines = self.send(403)
        self.assertEqual(status, 403)
        self.assertEqual([r['event'] for r in self.records(lines)], ['http_error'])


if __name__ == '__main__':
    unittest.main()
