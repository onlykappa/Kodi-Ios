"""ISSUE-327: a viewer hanging up on a loopback stream server (Kodi seeking, AirPlay stopping) is normal and is not
logged as a traceback; other errors still are. Both servers: the Drive proxy and the stream cache."""
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import drive_proxy  # noqa: E402
import drive_stream  # noqa: E402


class Quiet(unittest.TestCase):
    def report(self, cls, error):
        server = cls.__new__(cls)
        out = io.StringIO()
        with redirect_stderr(out):
            try:
                raise error
            except Exception:
                cls.handle_error(server, None, ('127.0.0.1', 1))
        return out.getvalue()

    def test_hangups_are_quiet_on_both_servers(self):
        for cls in (drive_proxy.Server, drive_stream._Server):
            for error in (ConnectionResetError(54, 'Connection reset by peer'), BrokenPipeError(), ConnectionAbortedError()):
                self.assertEqual(self.report(cls, error), '', (cls.__name__, error))

    def test_other_errors_are_still_reported(self):
        self.assertIn('ValueError', self.report(drive_proxy.Server, ValueError('real problem')))


if __name__ == '__main__':
    unittest.main()
