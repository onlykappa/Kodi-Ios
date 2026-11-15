"""ISSUE-317 (owner log d3c14036, build 482: the cache route had all three opening blocks in 4.3 s, then Kodi took 31.3 s
to open; the card sat at "loading video" after 12 MB). Every read Kodi makes through the cache is logged (offset, bytes,
time, blocks waited for), blocks Kodi waits on get request places before read-ahead, and the opening set is sized by
OPEN_BLOCKS."""
import io
import sys
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm  # noqa: E402

DATA = bytes(range(256)) * (30 * 1024 * 1024 // 256)


class Reply(io.BytesIO):
    def __init__(self, a, b):
        super().__init__(DATA[a:b + 1])
        self.status = 206
        self.headers = {'Content-Range': 'bytes %d-%d/%d' % (a, min(b, len(DATA) - 1), len(DATA))}

    def getcode(self):
        return self.status


def opener(request, timeout):
    a, b = map(int, request.get_header('Range')[6:].split('-'))
    return Reply(a, min(b, len(DATA) - 1))


class ReadTrace(unittest.TestCase):
    def test_each_read_is_logged_without_the_address(self):
        logged = []
        xbmc = types.SimpleNamespace(LOGINFO=1, log=lambda m, l=1: logged.append(m))
        with mock.patch.dict(sys.modules, {'xbmc': xbmc}):
            s = rm.Foreground('https://secret.example/tok/E.mkv', open_url=opener)
            self.addCleanup(s.close)
            with urllib.request.urlopen(urllib.request.Request(s.media_url, headers={'Range': 'bytes=5000000-5000099'}), timeout=5) as r:
                self.assertEqual(r.read(), DATA[5000000:5000100])
            time.sleep(0.2)
        reads = [l for l in logged if 'cache read' in l]
        self.assertTrue(any('offset=5000000 asked=100' in l for l in reads), reads)
        self.assertTrue(any('read done' in l and 'sent=100' in l for l in reads), reads)
        self.assertTrue(any('cache block: index=1' in l for l in logged), logged)
        self.assertEqual(s.reads[-1][1:4], (5000000, 5000099, 100))
        self.assertFalse(any('secret.example' in l or 'tok' in l for l in logged))

    def test_logging_stops_after_its_window(self):
        logged = []
        xbmc = types.SimpleNamespace(LOGINFO=1, log=lambda m, l=1: logged.append(m))
        with mock.patch.dict(sys.modules, {'xbmc': xbmc}):
            s = rm.Foreground('https://x.example/E.mkv', open_url=opener)
            self.addCleanup(s.close)
            s.born -= rm.READ_LOG_FOR + 1
            s._log('late')
        self.assertEqual(logged, [])


class Gate(unittest.TestCase):
    def test_a_waited_on_block_goes_before_read_ahead(self):
        g = rm._Gate(1)
        g.acquire(priority=1)
        order = []

        def wait(priority, name):
            since = time.monotonic()
            while not g.acquire(timeout=.05, priority=priority, since=since):
                pass
            order.append(name)
            g.release()
        ts = [threading.Thread(target=wait, args=(2, 'ahead')), threading.Thread(target=wait, args=(0, 'kodi'))]
        for t in ts:
            t.start()
            time.sleep(.05)
        g.release()
        for t in ts:
            t.join(5)
        self.assertEqual(order, ['kodi', 'ahead'])

    def test_priorities(self):
        s = rm.Foreground('https://x.example/E.mkv', open_url=opener)
        self.addCleanup(s.close)
        s.answered_size = len(DATA)
        req = lambda i: urllib.request.Request('http://x', headers={'Range': 'bytes=%d-' % (i * s.block_size)})
        self.assertEqual(s._priority(req(1)), 1)                       # opening
        self.assertEqual(s._priority(req((len(DATA) - 1) // s.block_size)), 1)   # last block
        self.assertEqual(s._priority(req(4)), 2)                       # read-ahead
        s.want(4)
        self.assertEqual(s._priority(req(4)), 0)                       # Kodi waits on it


class Opening(unittest.TestCase):
    def test_open_blocks_sets_what_the_cache_needs_before_kodi(self):
        broker = rm.Broker(source_factory=lambda source: rm.Foreground(source, open_url=opener))
        self.addCleanup(broker.close)
        with mock.patch.object(rm, 'OPEN_BLOCKS', 4):
            answer = rm._call(broker.url, {'action': 'open', 'source': 'https://x.example/a/E.mkv', 'player': 'kodi'})
            deadline = time.time() + 5
            st = {}
            while time.time() < deadline and not st.get('opening_ready'):
                st = rm._call(broker.url, {'action': 'stats', 'id': answer['id']})['stats']
                time.sleep(.05)
        self.assertTrue(st['opening_ready'])
        self.assertEqual(st['opening_blocks'], 5)                      # blocks 0-3 and the last


class Budget(unittest.TestCase):
    """Owner log cf038697: three 'Transferred a partial file' cuts while Kodi opened through the cache (31.3 s)."""
    def test_blocks_after_the_opening_never_get_its_budget(self):
        seen = []

        def timed(request, timeout):
            seen.append((int(request.get_header('Range')[6:].split('-')[0]) // rm.BLOCK, timeout))
            return opener(request, timeout)
        s = rm.Foreground('https://x.example/E.mkv', open_url=timed)
        self.addCleanup(s.close)
        s.answered_size = len(DATA)
        s.opening_deadline = time.monotonic() + 0.3
        s.connect_timeout = 5
        s.blocks.get('media', 0)
        time.sleep(0.4)                                   # the budget is spent
        s.blocks.get('media', 4)                          # a next block (KODI_AHEAD) still opens, with the normal timeout
        self.assertTrue(all(t <= 0.3 for i, t in seen if i == 0), seen)
        self.assertTrue(all(t == 20 for i, t in seen if i == 4), seen)
        with self.assertRaises(Exception):
            s.blocks.get('media', 1)                      # an opening block past the budget still fails, as before

    def test_a_failed_block_is_fetched_again_instead_of_cutting_the_read(self):
        failures = {'left': 12}             # every request of the block's first try fails

        def flaky(request, timeout):
            start = int(request.get_header('Range')[6:].split('-')[0])
            if start // rm.BLOCK == 1 and failures['left']:
                failures['left'] -= 1
                raise urllib.error.HTTPError('x', 500, 'Fixture', {}, None)
            return opener(request, timeout)
        s = rm.Foreground('https://x.example/E.mkv', open_url=flaky)
        self.addCleanup(s.close)
        with mock.patch.object(rm.drive_stream.time, 'sleep', lambda x: None):
            s.blocks.get('media', 0)                      # the size is known; the read starts in block 1 itself
            want = DATA[rm.BLOCK + 10:rm.BLOCK + 30]
            req = urllib.request.Request(s.media_url, headers={'Range': 'bytes=%d-%d' % (rm.BLOCK + 10, rm.BLOCK + 29)})
            with urllib.request.urlopen(req, timeout=10) as r:
                self.assertEqual(r.read(), want)


if __name__ == '__main__':
    unittest.main()
