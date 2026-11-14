"""ISSUE-281 (owner, build 442: an Umbrella episode sat at "Opening the video · 0 of 12 MB", then the app crashed on Resume)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm  # noqa: E402


class Home:
    def __init__(self):
        self.props = {rm.PROPERTY: 'http://127.0.0.1:5000/s'}
    def getProperty(self, k): return self.props.get(k, '')
    def setProperty(self, k, v): self.props[k] = v


SRC = 'https://alldebrid.example/dl/abc/Episode.mkv'


class Fallback(unittest.TestCase):
    def run_for_kodi(self, sizes):
        calls, seen = [], iter(sizes)
        def call(endpoint, payload):
            calls.append(payload['action'])
            if payload['action'] == 'open':
                return {'url': 'http://127.0.0.1:6000/k/media', 'id': 'id1'}
            if payload['action'] == 'stats':
                return {'stats': {'source_id': rm.fingerprint('id1'), 'size': next(seen, 0)}}
            return {}
        t = [0.0]
        def wait(s): t[0] += s
        with mock.patch.object(rm, '_call', call), mock.patch.object(rm.umbrella_recovery, 'selected', lambda *a: None):
            out = rm.for_kodi(SRC, Home(), wait=wait, clock=lambda: t[0])
        return out, calls

    def test_the_cache_is_used_once_the_link_answered(self):
        out, calls = self.run_for_kodi([0, 0, 1700000000])
        self.assertEqual(out, 'http://127.0.0.1:6000/k/media');self.assertNotIn('drop', calls)

    def test_no_answer_in_time_gives_kodi_the_real_link_and_lets_the_cache_go(self):
        out, calls = self.run_for_kodi([0] * 100)
        self.assertEqual(out, SRC);self.assertEqual(calls[-1], 'drop')

    def test_one_cache_for_the_whole_run(self):
        class Fake:
            url = 'http://127.0.0.1:7000/x'
            stopped = type('E', (), {'is_set': lambda self: False})()
        rm._BROKER[0] = Fake()
        try:
            home = Home()
            self.assertIs(rm.start(None, home), rm._BROKER[0])
            self.assertEqual(home.props[rm.PROPERTY], 'http://127.0.0.1:7000/x')
        finally:
            rm._BROKER[0] = None

    def test_the_stats_never_carry_the_private_id(self):
        self.assertNotIn('id1', rm.fingerprint('id1'));self.assertEqual(rm.fingerprint(''), '')


if __name__ == '__main__':
    unittest.main()
