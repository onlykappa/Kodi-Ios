"""ISSUE-315 (owner, build 479, log bdbdac02): two hand-offs 0.7 s apart for one play; the second closed the first's
cache source, so the first went direct after 1 s and Kodi opened it in 24 s. A Kodi source opened under RACE s ago stays
open beside the new one, each hand-off sees its own source, and the next blocks Kodi reads are fetched with the opening."""
import io
import sys
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm  # noqa: E402

DATA = bytes(range(256)) * (30 * 1024 * 1024 // 256)       # 30 MiB: 8 blocks


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


class Race(unittest.TestCase):
    def setUp(self):
        self.broker = rm.Broker(source_factory=lambda source: rm.Foreground(source, open_url=opener))
        self.addCleanup(self.broker.close)

    def call(self, payload):
        return rm._call(self.broker.url, payload)

    def test_a_second_hand_off_keeps_the_first_source_alive(self):
        first = self.call({'action': 'open', 'source': 'https://x.example/a/One.mkv', 'player': 'kodi'})
        second = self.call({'action': 'open', 'source': 'https://x.example/b/Two.mkv', 'player': 'kodi'})
        self.assertNotEqual(first['id'], second['id'])
        mine = self.call({'action': 'stats', 'id': first['id']})['stats']
        self.assertEqual(mine['source_id'], rm.fingerprint(first['id']))                # the first still sees its own source
        theirs = self.call({'action': 'stats', 'id': second['id']})['stats']
        self.assertEqual(theirs['source_id'], rm.fingerprint(second['id']))
        with urllib.request.urlopen(urllib.request.Request(first['url'], headers={'Range': 'bytes=0-99'}), timeout=5) as r:
            self.assertEqual(r.read(), DATA[:100])                                         # and still serves Kodi
        self.assertEqual(self.call({'action': 'origin', 'url': first['url']})['source'], 'https://x.example/a/One.mkv')
        self.call({'action': 'drop', 'id': first['id']})
        self.assertIsNone(self.broker.previous)

    def test_a_third_hand_off_keeps_only_one_previous(self):
        ids = [self.call({'action': 'open', 'source': 'https://x.example/%d/V.mkv' % n, 'player': 'kodi'})['id'] for n in range(3)]
        self.assertEqual(self.broker.previous[0], ids[1])

    def test_the_answered_check_asks_for_its_own_source(self):
        source = (ROOT / 'migration/bundled-bootstrap/resources/lib/remote_media.py').read_text()
        self.assertIn("{'action':'stats','id':ident}", source)


class Ahead(unittest.TestCase):
    def test_the_next_blocks_are_fetched_with_the_opening(self):
        s = rm.Foreground('https://x.example/c/E.mkv', open_url=opener)
        self.addCleanup(s.close)
        rm.prefetch(s, extra=rm.KODI_AHEAD)
        import time
        deadline = time.time() + 5
        want = {0, 1, 2, 3, 4, 5, (len(DATA) - 1) // rm.BLOCK}
        while time.time() < deadline and not want <= {k[1] for k in s.blocks.data}:
            time.sleep(0.05)
        self.assertTrue(want <= {k[1] for k in s.blocks.data}, sorted(k[1] for k in s.blocks.data))


class Resume(unittest.TestCase):
    def test_continue_asks_for_the_resume_point_with_the_opening(self):
        # Step 2 (owner, build 620 log 80ea6c76): the resume seek read cold for 3.6 s; the block where playback resumes is fetched with the opening blocks
        broker = rm.Broker(source_factory=lambda source: rm.Foreground(source, open_url=opener))
        self.addCleanup(broker.close)
        rm._call(broker.url, {'action': 'open', 'source': 'https://x.example/r/Ep.mkv', 'player': 'kodi', 'resume': 0.5})
        import time
        last = (len(DATA) - 1) // rm.BLOCK
        want = {0, last} | set(rm.resume_blocks(0.5, len(DATA), rm.BLOCK))
        self.assertTrue(rm.resume_blocks(0.5, len(DATA), rm.BLOCK))
        deadline = time.time() + 5
        while time.time() < deadline and not want <= {k[1] for k in broker.current.blocks.data}:
            time.sleep(0.05)
        self.assertTrue(want <= {k[1] for k in broker.current.blocks.data}, sorted(k[1] for k in broker.current.blocks.data))

    def test_a_bad_resume_value_is_ignored(self):
        broker = rm.Broker(source_factory=lambda source: rm.Foreground(source, open_url=opener))
        self.addCleanup(broker.close)
        answer = rm._call(broker.url, {'action': 'open', 'source': 'https://x.example/r/Ep2.mkv', 'player': 'kodi', 'resume': 'x'})
        self.assertTrue(answer['url'].startswith('http://127.0.0.1'))


if __name__ == '__main__':
    unittest.main()
