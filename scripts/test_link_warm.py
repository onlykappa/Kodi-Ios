"""Roadmap 1B.4: a resolved debrid link is read (start and end) in the background while Umbrella's window closes."""
import http.server
import socketserver
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import link_warm as lw
import umbrella_recovery as recovery

DATA = bytes(range(256)) * 8192   # 2 MiB


class Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        rng = self.headers.get('Range', '')
        Handler.seen.append(rng)
        first, last = (int(v) for v in rng.split('=')[1].split('-'))
        body = DATA[first:last + 1]
        self.send_response(206)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (first, first + len(body) - 1, len(DATA)))
        self.end_headers()
        self.wfile.write(body)


class Warm(unittest.TestCase):
    def setUp(self):
        Handler.seen = []
        self.server = socketserver.TCPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = 'http://127.0.0.1:%d/file.mkv' % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_reads_the_start_and_the_end_of_the_file(self):
        self.assertEqual(lw.warm(self.url, len(DATA)), 2)
        self.assertEqual(Handler.seen, ['bytes=0-%d' % (lw.HEAD - 1), 'bytes=%d-%d' % (len(DATA) - lw.TAIL, len(DATA) - 1)])

    def test_unknown_or_small_size_reads_only_the_start(self):
        self.assertEqual(lw.warm(self.url, 0), 1)
        self.assertEqual(lw.warm(self.url, lw.HEAD), 1)

    def test_a_failing_link_is_swallowed(self):
        self.assertEqual(lw.warm('http://127.0.0.1:9/never', 5), 0)

    def test_start_runs_in_the_background_one_at_a_time_and_only_for_web_links(self):
        gate, release = threading.Event(), threading.Event()

        def slow(request, timeout):
            gate.set()
            release.wait(5)
            raise OSError('synthetic')
        first = lw.start('https://media.example/a.mkv', 1, urlopen=slow)
        self.assertTrue(gate.wait(5))
        self.assertIsNone(lw.start('https://media.example/b.mkv', 1, urlopen=slow))   # one at a time
        release.set()
        first.join(5)
        self.assertIsNotNone(lw.start(self.url, 0))                                      # free again
        for other in ('file:///movie.mkv', '', None, 5):
            self.assertIsNone(lw.start(other))
        for _ in range(100):
            if not lw._running[0]:
                break
            threading.Event().wait(0.02)


class Hook(unittest.TestCase):
    def test_remember_starts_the_warm_up_with_the_resolved_link_and_size(self):
        class Home(object):
            props = {}

            def setProperty(self, k, v):
                self.props[k] = v
        asked = []
        recovery.remember('https://alldebrid.com/f/x', {'link': 'https://media.example/a.mkv', 'filesize': 123, 'filename': 'a.mkv'},
                          Home(), warm=lambda url, size: asked.append((url, size)))
        self.assertEqual(asked, [('https://media.example/a.mkv', 123)])

    def test_a_broken_warm_up_never_breaks_the_unlock(self):
        class Home(object):
            def setProperty(self, k, v):
                pass

        def boom(url, size):
            raise RuntimeError('synthetic')
        recovery.remember('https://alldebrid.com/f/x', {'link': 'https://media.example/a.mkv'}, Home(), warm=boom)

    def test_the_link_is_never_logged(self):
        source = (ROOT / 'migration/bundled-bootstrap/resources/lib/link_warm.py').read_text()
        self.assertNotIn('xbmc.log', source)
        self.assertNotIn('print(', source)


if __name__ == '__main__':
    unittest.main()
