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

    def test_a_cycling_umbrella_gets_no_checks_after_the_first_few_hand_offs(self):
        # ISSUE-488: 1,571 hand-offs in 7 minutes in owner log ff742bd7, each a cache attempt or a 1 s direct check
        rm._CALLS.clear()
        verdicts = [rm.cycling(100.0 + n * 0.5) for n in range(8)]
        self.assertEqual(verdicts[:rm.CYCLE_MAX], [False] * rm.CYCLE_MAX)   # the picked source and its first neighbours are checked as before
        self.assertTrue(all(verdicts[rm.CYCLE_MAX:]))
        rm._CALLS.clear()
        self.assertFalse(any(rm.cycling(1000.0 + n * 30) for n in range(8)))   # one hand-off every 30 s is ordinary use
    def test_the_unlock_hook_makes_no_hand_off_for_a_cycling_umbrella(self):
        import umbrella_recovery as ur
        rm._CALLS.clear()
        asked = []
        home = Home()
        response = lambda n: {'link': 'https://h.example/f%d.mkv' % n, 'filesize': 5, 'filename': 'f%d.mkv' % n}
        with mock.patch.object(rm, 'for_kodi', side_effect=lambda link, h, **k: asked.append(link) or link), mock.patch.object(rm.time, 'monotonic', return_value=500.0):
            # the module-level `real` flag is "home is None": a real call; give it a stand-in window so the hook runs its real branch
            import types, sys
            fake = types.SimpleNamespace(Window=lambda n: home)
            with mock.patch.dict(sys.modules, {'xbmcgui': fake}):
                for n in range(rm.CYCLE_MAX + 3):
                    ur.remember('link%d' % n, response(n), home=None, warm=lambda *a: None)
        self.assertEqual(len(asked), rm.CYCLE_MAX)   # the picked source and its first neighbours are handed over as before; the rest are not
    def test_continue_and_play_on_tv_never_count_as_cycling(self):
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/remote_media.py').read_text()
        body = text[text.index('def for_kodi'):text.index('def _note_route')]
        self.assertNotIn('cycling(', body)   # for_kodi, used by Continue, is untouched


if __name__ == '__main__':
    unittest.main()
