"""Checking our own sources on opening: master playlist reading, caching, failures, row text. No network."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
import sports_probe as sp  # noqa: E402
import sports_game  # noqa: E402

MASTER = '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2500000,AVERAGE-BANDWIDTH=2400000,RESOLUTION=1280x720,FRAME-RATE=30.000\na.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=5200000,RESOLUTION=1920x1080,FRAME-RATE=59.940\nb.m3u8\n'
MEDIA = '#EXTM3U\n#EXTINF:6,\nseg1.ts\n'


def play(name):
    return json.dumps({'e': name, 'l': {'address': 'https://x/' + name}})


class Parse(unittest.TestCase):
    def test_best_variant(self):
        r = sp.parse_master(MASTER)
        self.assertEqual((r['height'], r['fps'], r['kbps'], r['variants']), (1080, 60, 5200, 2))
        self.assertEqual(sp.describe(dict(r, ok=True)), '1080p · 60 fps · 5.2 Mbps')

    def test_media_playlist_and_garbage(self):
        self.assertEqual(sp.parse_master(MEDIA), {'single': True})
        self.assertIsNone(sp.parse_master('<html>no</html>'))
        self.assertIn('size shown once it plays', sp.describe({'ok': True, 'single': True}))


class Probe(unittest.TestCase):
    def test_ok_failure_and_not_a_playlist(self):
        ok = sp.probe('p', resolver=lambda p: ('https://a', {}), fetch=lambda a, h: MASTER)
        self.assertTrue(ok['ok'])
        bad = sp.probe('p', resolver=lambda p: 1 / 0, fetch=None)
        self.assertEqual((bad['ok'], bad['why']), (False, 'ZeroDivisionError'))
        self.assertEqual(sp.describe(bad), "didn't respond")
        self.assertFalse(sp.probe('p', resolver=lambda p: ('a', {}), fetch=lambda a, h: 'x')['ok'])


class Segment(unittest.TestCase):
    def test_plain_playlist_is_weighed_by_its_newest_segment(self):
        text = '#EXTM3U\n#EXTINF:6.0,\nold.ts\n#EXTINF:4.0,\nseg/new.ts\n'
        self.assertEqual(sp.last_segment(text), (4.0, 'seg/new.ts'))
        asked = []
        get = lambda a, h: asked.append(a) or (2_500_000, 1.0)
        r = sp.measure_segment('https://h/p/list.m3u8', {}, text, get)
        self.assertEqual((r['kbps'], r['speed'], asked), (5000, 4.0, ['https://h/p/seg/new.ts']))
        self.assertEqual(sp.measure_segment('https://h/a', {}, text, lambda a, h: (500, 1.0)), {})   # an error page is not a segment
        ok = sp.probe('p', resolver=lambda p: ('https://h/a', {}), fetch=lambda a, h: text, measure=lambda a, h, t: r)
        self.assertEqual(sp.describe(ok), '5.0 Mbps · downloads 4.0x faster than it plays')
        slow = sp.describe({'ok': True, 'kbps': 5000, 'speed': 0.9})
        self.assertIn('too slow', slow)


class Start(unittest.TestCase):
    def setUp(self):
        sp._results.clear()
        sp._running.clear()

    def test_only_own_sites_are_checked_once_and_kept(self):
        import sports_livefeeds
        own, crew = play(sports_livefeeds.NAME), json.dumps({'e': 'TheCrewRoute', 'l': {}})
        calls = []
        run = lambda p: calls.append(p) or {'ok': True, 'height': 720, 'fps': 30, 'kbps': 2500}
        now = [100.0]
        started = sp.start([{'play': own}, {'play': crew}], run=run, clock=lambda: now[0], spawn=lambda t: t())
        self.assertEqual((started, calls), (1, [own]))
        self.assertEqual(sp.start([{'play': own}], run=run, clock=lambda: now[0], spawn=lambda t: t()), 0)   # kept
        now[0] += sp.KEEP + 1
        self.assertEqual(sp.start([{'play': own}], run=run, clock=lambda: now[0], spawn=lambda t: t()), 1)   # expired
        self.assertEqual(len(calls), 2)

    def test_row_lines(self):
        import sports_livefeeds
        own = play(sports_livefeeds.NAME)
        self.assertEqual(sports_game.check_line({'play': own}), '\nChecking…')
        sp._results[own] = (__import__('time').time(), {'ok': True, 'height': 1080, 'fps': 60, 'kbps': 5200})
        self.assertEqual(sports_game.check_line({'play': own}), '\nChecked: 1080p · 60 fps · 5.2 Mbps')
        crew = json.dumps({'e': 'TheCrewRoute', 'l': {}})
        self.assertEqual(sports_game.check_line({'play': crew}), '\nChecked when played')
        self.assertEqual(sports_game.check_line({'play': crew, 'record': '720p'}), '')


if __name__ == '__main__':
    unittest.main()
