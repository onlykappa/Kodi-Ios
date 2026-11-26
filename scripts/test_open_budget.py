"""Umbrella opening budget (ISSUE-477): the cache is given long enough to finish a cold opening, a link the cache does not take says why in the open record."""
import sys, unittest
from pathlib import Path
from unittest import mock
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm


class Home(dict):
    def setProperty(self, k, v): self[k] = v
    def getProperty(self, k): return self.get(k, '')


class Budget(unittest.TestCase):
    def test_the_cases_from_the_logs_are_no_longer_given_up_on(self):
        self.assertEqual((rm.FIRST_ANSWER, rm.SLOW_SKIP), (8.0, 1800))
        # `direct 1/3 wait 2.0 s` in build 693's neighbours: one 4 MB block in at 2 s (2 MB/s), two blocks still to come
        st = {'opening_blocks': 3, 'read_bytes': rm.BLOCK}
        self.assertFalse(rm.hopeless(st, 2.0, rm.FIRST_ANSWER))
        self.assertTrue(rm.hopeless(st, 2.0, 5.0))   # the old budget gave up here
    def test_a_dead_or_really_slow_server_is_still_dropped_early(self):
        self.assertTrue(rm.hopeless({'opening_blocks': 3, 'read_bytes': 0}, 1.6, rm.FIRST_ANSWER))                       # nothing arrived
        self.assertTrue(rm.hopeless({'opening_blocks': 3, 'read_bytes': int(0.2e6 * 2)}, 2.0, rm.FIRST_ANSWER))          # 0.2 MB/s: about a minute
    def test_a_link_the_cache_does_not_take_names_its_file_type_only(self):
        home = Home()
        with mock.patch.object(rm, 'KODI_PLAYBACK', True):
            link = 'https://host.example/dl/abc123token/Show.S01E01.mp4'
            self.assertEqual(rm.for_kodi(link, home), link)
        self.assertEqual(home['KodiIOS.OpenRoute'], 'not cached (.mp4)')
        self.assertNotIn('abc123', home['KodiIOS.OpenRoute'])
        home = Home()
        with mock.patch.object(rm, 'KODI_PLAYBACK', True):
            rm.for_kodi('https://host.example/stream/12345', home)
        self.assertEqual(home['KodiIOS.OpenRoute'], 'not cached (.none)')


if __name__ == '__main__':
    unittest.main()
