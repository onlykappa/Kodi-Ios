"""Build Season (owner, 2026-11-12; docs/design/season-pack-mockups.html boards B, C, D): the sheet models and the flow
in season_sources.build with Kodi's windows replaced."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import season_sheet as ss  # noqa: E402


class Models(unittest.TestCase):
    def test_1080p_is_picked_and_every_card_builds(self):
        props = ss.quality_props('Naruto Shippūden', 1, 26)
        self.assertEqual([props['q.%d.label' % n] for n in range(1, 5)], ['4K', '1080p', '720p', '480p'])
        self.assertEqual(props['q.2.on'], 'true')
        self.assertEqual(props['button'], 'Build 1080p Season')
        self.assertIn('26 episodes', props['how'])

    def test_an_episode_only_lower_takes_the_next_quality_down(self):
        self.assertEqual(ss.best_for(['1080p', '720p'], '1080p'), '1080p')
        self.assertEqual(ss.best_for(['720p', '480p'], '1080p'), '720p')
        self.assertIsNone(ss.best_for(['480p'], '1080p'))

    def test_ready_sheet_counts_marks_and_leaves_out(self):
        picks = {1: ('1080p', 0.38), 2: ('1080p', 0.37), 3: ('720p', 0.21), 4: (None, None), 5: ('1080p', 0.4), 6: ('1080p', 0.4)}
        m = ss.ready_model('Naruto', 1, '1080p', picks, {1: 'Homecoming', 3: 'The Results of Training'})
        self.assertEqual((m['count'], m['quality'], m['episodes']), ('5', '1080p', [1, 2, 3, 5, 6]))
        self.assertEqual(m['total'], '1.8 GB')
        self.assertIn(3, [int(r['no']) for r in m['rows']])                 # the lower one is always shown
        self.assertEqual([r['low'] for r in m['rows'] if r['no'] == '3'], ['720p'])
        self.assertEqual(m['more'], '1 more episode')
        self.assertIn('not found', m['warn'])
        self.assertFalse(m['ok'])
        self.assertEqual(m['button'], 'Download All 5 · 1.8 GB')

    def test_every_episode_found(self):
        m = ss.ready_model('Lanterns', 2, '1080p', {1: ('1080p', 1.0), 2: ('1080p', 1.1)}, {})
        self.assertTrue(m['ok'])
        self.assertTrue(m['warn'].startswith('Every episode found in 1080p'))

    def test_card_lines(self):
        props = ss.building_props(1, '1080p', 'Naruto', 12, 26, 12, 13)
        self.assertEqual(props['IOSSearch.Kicker'], 'Building Season 1 · 1080p')
        self.assertEqual((props['IOSSearch.Lines'], props['IOSSearch.Line.1.Count'], props['IOSSearch.Line.2.State']), ('2', '12 of 26', 'wait'))
        self.assertEqual(props['IOSSearch.Pct'], '46')


class Flow(unittest.TestCase):
    def run_build(self, answers, quality='1080p', confirm=True):
        import season_sources
        calls = {'queued': [], 'card': []}

        class Card:
            def __init__(self, gui): self.canceled = False
            def show(self, props): calls['card'].append(props['IOSSearch.Kicker'])
            def close(self): pass
        orig = (ss.pick_quality, ss.confirm_ready, ss.Card)
        ss.pick_quality = lambda gui, title, season, n: quality
        ss.confirm_ready = lambda gui, model: calls.setdefault('model', model) and confirm
        ss.Card = Card

        def search(n, purpose, q):
            if purpose == 'scan':
                return {'qualities': answers.get(n, []), 'sizes': {x: 0.4 for x in answers.get(n, [])}}
            calls['queued'].append((n, q))
            return {'queued': True}
        home = types.SimpleNamespace(props={}, getProperty=lambda k: home.props.get(k, ''),
                                     setProperty=lambda k, v: home.props.__setitem__(k, v), clearProperty=lambda k: home.props.pop(k, None))
        self.waits = []
        xbmc = types.SimpleNamespace(Monitor=lambda: types.SimpleNamespace(abortRequested=lambda: False,
                                                                           waitForAbort=lambda t: self.waits.append(t) or False),
                                     log=lambda *a: None, LOGINFO=1)
        dialog = types.SimpleNamespace(ok=lambda *a: calls.setdefault('ok', a), notification=lambda *a: None)
        gui = types.SimpleNamespace(NOTIFICATION_INFO=1)
        try:
            with unittest.mock.patch.object(season_sources, 'pending_episodes', lambda *a: set()), \
                 unittest.mock.patch.object(season_sources.watch, 'plan_season', lambda *a: None), \
                 unittest.mock.patch.object(season_sources.watch, 'record_planned', lambda *a: None), \
                 unittest.mock.patch.dict(sys.modules, {'transfer_control': types.SimpleNamespace(paused=lambda *a: False)}):
                out = season_sources._build(xbmc, gui, dialog, home, '/p', 31910, 'Naruto', 1, [1, 2, 3], set(), {}, search)
        finally:
            ss.pick_quality, ss.confirm_ready, ss.Card = orig
        return out, calls

    def test_builds_from_episodes_at_the_quality_with_fallback(self):
        import unittest.mock  # noqa: F401
        out, calls = self.run_build({1: ['1080p', '480p'], 2: ['720p'], 3: ['1080p']})
        # Owner log 5169a460: Close/Cancel taps reach the card only while the script waits in Kodi.
        self.assertTrue(self.waits and all(t <= 0.05 for t in self.waits))
        self.assertEqual(out, [1, 2, 3])
        self.assertEqual(calls['queued'], [(1, '1080p'), (2, '720p'), (3, '1080p')])
        self.assertIn('Building Season 1 · 1080p', calls['card'])

    def test_nothing_queues_without_download_all(self):
        import unittest.mock  # noqa: F401
        out, calls = self.run_build({1: ['1080p']}, confirm=False)
        self.assertEqual((out, calls['queued']), ([], []))


if __name__ == '__main__':
    import unittest.mock  # noqa: F401
    unittest.main()
