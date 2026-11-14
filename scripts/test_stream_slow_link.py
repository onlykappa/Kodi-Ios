"""ISSUE-302 (owner, build 470, log 2979ea67: "Opening the video · 4 of 12 MB", AllDebrid at 0.2 MB/s, no picture after
126 s): a debrid link is slow per connection, so a block is read as parallel ranges and the opening blocks together."""
import io
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm  # noqa: E402

DATA = bytes(range(256)) * (13 * 1024 * 1024 // 256 + 5)     # 13 MiB: three blocks, the last one short
RATE = 16 * 1024 * 1024                                       # bytes a second ONE connection delivers


class Reply(io.BytesIO):
    def __init__(self, start, end):
        super().__init__(DATA[start:end + 1])
        self.status = 206
        self.headers = {'Content-Range': 'bytes %d-%d/%d' % (start, min(end, len(DATA) - 1), len(DATA))}

    def getcode(self):
        return self.status


class Slow(unittest.TestCase):
    def setUp(self):
        self.lock = threading.Lock()
        self.live = self.peak = 0

    def open(self, request, timeout):
        a, b = map(int, request.get_header('Range')[6:].split('-'))
        b = min(b, len(DATA) - 1)
        with self.lock:
            self.live += 1
            self.peak = max(self.peak, self.live)
        time.sleep((b - a + 1) / RATE)                      # this connection's own speed
        with self.lock:
            self.live -= 1
        return Reply(a, b)

    def source(self):
        s = rm.Foreground('https://media.example/e.mkv', open_url=self.open)
        self.addCleanup(s.close)
        return s

    def test_a_block_is_read_in_parallel_ranges_and_joined_in_order(self):
        s = self.source()
        began = time.monotonic()
        block = s.blocks.get('media', 0)
        took = time.monotonic() - began
        self.assertEqual(block, DATA[:rm.BLOCK])
        self.assertEqual(s.blocks.sizes['media'], len(DATA))
        self.assertLess(took, 0.6 * rm.BLOCK / RATE)        # one connection would take rm.BLOCK / RATE
        self.assertGreaterEqual(self.peak, 2)

    def test_the_short_last_block_is_exact(self):
        s = self.source()
        s.blocks.get('media', 0)
        last = (len(DATA) - 1) // rm.BLOCK
        self.assertEqual(s.blocks.get('media', last), DATA[last * rm.BLOCK:])

    def test_opening_blocks_are_fetched_together(self):
        s = self.source()
        began = time.monotonic()
        rm.prefetch(s)
        took = time.monotonic() - began
        self.assertEqual(len(s.blocks.data), 3)             # first, second, last
        serial = 3 * rm.BLOCK / RATE                        # what one connection, one block after another, takes
        self.assertLess(took, 0.5 * serial)

    def test_connections_are_capped(self):
        s = self.source()
        rm.prefetch(s)
        self.assertLessEqual(self.peak, rm.PIECES)


if __name__ == '__main__':
    unittest.main()
