"""ISSUE-306 (owner, build 475, log eadd0349): Umbrella handed six sources over one after another and none played.
The address Kodi opens ends in the file's name with a video type, the bytes Kodi really reads are counted, and a hand-off
after one that Kodi never read goes direct."""
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm  # noqa: E402

SRC = 'https://alldebrid.example/dl/abc/Black.Clover.S02E07.1080p.mkv'
DATA = bytes(range(256)) * 4096


class Reply(io.BytesIO):
    def __init__(self, a, b):
        super().__init__(DATA[a:b + 1])
        self.status = 206
        self.headers = {'Content-Range': 'bytes %d-%d/%d' % (a, min(b, len(DATA) - 1), len(DATA))}

    def getcode(self):
        return self.status


class Home:
    def getProperty(self, k):
        return 'http://127.0.0.1:5000/s'


class Address(unittest.TestCase):
    def test_kodi_gets_the_files_own_name_and_a_video_type(self):
        def op(request, timeout):
            a, b = map(int, request.get_header('Range')[6:].split('-'))
            return Reply(a, min(b, len(DATA) - 1))
        s = rm.Foreground(SRC, open_url=op)
        self.addCleanup(s.close)
        self.assertTrue(s.media_url.endswith('/Black.Clover.S02E07.1080p.mkv'), s.media_url)
        import urllib.request
        with urllib.request.urlopen(urllib.request.Request(s.media_url, headers={'Range': 'bytes=0-99'}), timeout=5) as r:
            self.assertEqual(r.headers['Content-Type'], 'video/x-matroska')
            self.assertEqual(r.read(), DATA[:100])
        self.assertEqual(s.served, 100)                       # what a reader really took is counted

    def test_other_containers_have_their_types(self):
        self.assertEqual(rm.TYPES['avi'], 'video/x-msvideo')
        self.assertEqual(rm.TYPES['webm'], 'video/webm')


class Loop(unittest.TestCase):
    def setUp(self):
        for patcher in (mock.patch.object(rm, 'KODI_PLAYBACK', True), mock.patch.object(rm, '_LAST', [0.0]),
                        mock.patch.object(rm.umbrella_recovery, 'selected', lambda *a: None)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.now = [100.0]
        self.served = 0
        self.calls = []

    def hand_over(self):
        def call(endpoint, payload, timeout=5):
            self.calls.append(payload['action'])
            if payload['action'] == 'open':
                return {'url': 'http://127.0.0.1:6000/k/Black.Clover.mkv', 'id': 'id1'}
            if payload['action'] == 'stats':
                return {'stats': {'source_id': rm.fingerprint('id1'), 'kodi': True, 'served': self.served, 'opening_ready': True}}
            return {}
        with mock.patch.object(rm, '_call', call):
            return rm.for_kodi(SRC, Home(), wait=lambda s: None, clock=lambda: self.now[0])

    def test_a_second_hand_off_after_one_kodi_never_read_goes_direct(self):
        self.assertTrue(self.hand_over().startswith('http://127.0.0.1:'))      # the first one: the cache
        self.now[0] += 6
        self.calls.clear()
        self.assertEqual(self.hand_over(), SRC)                                  # Umbrella is cycling: direct
        self.assertIn('drop', self.calls)
        self.assertNotIn('open', self.calls)

    def test_a_source_kodi_did_read_is_not_a_loop(self):
        self.hand_over()
        self.now[0] += 6
        self.served = 4 * 1024 * 1024                                            # Kodi took data from it
        self.assertTrue(self.hand_over().startswith('http://127.0.0.1:'))

    def test_a_much_later_hand_off_is_a_new_play(self):
        self.hand_over()
        self.now[0] += rm.LOOP_WINDOW + 5
        self.assertTrue(self.hand_over().startswith('http://127.0.0.1:'))

    def test_the_log_line_says_what_kodi_took_and_why_direct(self):
        logged = []
        fake = type('X', (), {'LOGINFO': 1, 'log': staticmethod(lambda text, level=0: logged.append(text))})
        with mock.patch.dict(sys.modules, {'xbmc': fake}):
            rm.opening_log('direct', 1.0, {'served': 0}, reason='previous source never read by Kodi')
        self.assertIn('served=0 reason=previous source never read by Kodi', logged[0])


if __name__ == '__main__':
    unittest.main()
