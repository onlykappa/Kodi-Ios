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
    def test_round_3_rows_recommend_the_highest_light_quality(self):
        # Board B3·2 (DEC-041): 4K exists and is light, so it is recommended and picked.
        found = ss.survey({1: {'qualities': ['4k', '1080p', '720p'], 'sizes': {'4k': 1.4, '1080p': 0.45, '720p': 0.25}},
                           6: {'qualities': ['4k', '1080p'], 'sizes': {'4k': 1.4, '1080p': 0.45}}})
        props = ss.quality_props('Rick and Morty', 1, 11, found)
        self.assertEqual([props['q.%d.label' % n] for n in range(1, 4)], ['4K', '1080p', '720p'])
        self.assertNotIn('q.4.label', props)                       # 480p is gone
        self.assertEqual((props['q.1.rec'], props['q.1.on'], props['q.1.size'], props['q.1.each']), ('RECOMMENDED', 'true', '15 GB season', '1.4 GB each'))
        self.assertEqual(props['button'], 'Build 4K Season · 15 GB')
        self.assertIn('small for this show', props['how'])

    def test_a_quality_nobody_has_is_greyed(self):
        # Board B3·3: no 4K copy, 1080p recommended.
        found = ss.survey({1: {'qualities': ['1080p', '720p'], 'sizes': {'1080p': 0.26, '720p': 0.15}}})
        props = ss.quality_props('Naruto Shippūden', 1, 32, found)
        self.assertEqual((props['q.1.off'], props['q.1.size'], props['q.1.each'], props['q.1.on']), ('true', 'Not found', 'No copy exists', ''))
        self.assertEqual((props['q.2.rec'], props['q.2.on'], props['q.2.size']), ('RECOMMENDED', 'true', '8.3 GB season'))
        self.assertTrue(props['how'].startswith('No 4K copy exists, so it is greyed'))
        self.assertEqual(props['button'], 'Build 1080p Season · 8.3 GB')

    def test_a_huge_4k_season_recommends_1080p_but_4k_can_be_chosen(self):
        # Board B3·4: 9.5 GB an episode, 76 GB the season.
        found = ss.survey({1: {'qualities': ['4k', '1080p', '720p'], 'sizes': {'4k': 9.5, '1080p': 2.1, '720p': 1.1}}})
        props = ss.quality_props('Lanterns', 2, 8, found)
        self.assertEqual((props['q.2.rec'], props['q.2.on'], props['q.1.off']), ('RECOMMENDED', 'true', ''))
        self.assertIn('4K is very large[/B] here (76 GB)', props['how'])
        chose = ss.quality_props('Lanterns', 2, 8, found, '4k')
        self.assertEqual((chose['q.1.on'], chose['q.2.rec'], chose['button']), ('true', 'RECOMMENDED', 'Build 4K Season · 76 GB'))
        # A 40 GB season limit as well as 3 GB an episode.
        self.assertEqual(ss.recommend({'4k': [2.5], '1080p': [1.0]}, 20), '1080p')
        self.assertEqual(ss.recommend({'4k': [9.0]}, 8), '4k')         # the only one there is
        self.assertIsNone(ss.recommend({}, 8))

    def test_check_looks_at_start_middle_end_and_counts_lower_for_720p(self):
        self.assertEqual(ss.check_numbers(range(1, 12)), [1, 6, 11])
        self.assertEqual(ss.check_numbers([4, 5]), [4, 5])
        self.assertEqual(ss.survey({1: {'qualities': ['480p'], 'sizes': {'480p': 0.1}}}), {'720p': [0.1]})
        props = ss.checking_props('Rick and Morty', 1, 11, [1, 6, 11], 2, {'4k': 'found', '1080p': 'found'})
        self.assertEqual((props['check.sub'], props['check.q.3'], props['button.off'], props['check.pct']),
                         ('Looking at episodes 1, 6 and 11', '720p · \u2026', 'true', '66'))

    def test_nothing_found_cannot_build_and_no_answer_lets_every_row_be_chosen(self):
        props = ss.quality_props('X', 1, 8, {})
        self.assertEqual((props['button.off'], props['q.1.off'], props['q.2.off'], props['q.3.off']), ('true',) * 4)
        props = ss.quality_props('X', 1, 8, None)
        self.assertEqual((props['button.off'], props['q.2.on'], props['button']), ('', 'true', 'Build 1080p Season'))

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
        def pick(gui, title, season, n, check=None, wait=None):
            calls['checked'] = check(lambda done, states: None, lambda: False) if check else None
            return quality
        ss.pick_quality = pick
        ss.confirm_ready = lambda gui, model: calls.setdefault('model', model) and confirm
        ss.Card = Card

        def search(n, purpose, q):
            if purpose == 'scan':
                got = answers.get(n, [])
                got = got() if callable(got) else got
                calls.setdefault('scans', []).append(n)
                return {'qualities': got, 'sizes': {x: 0.4 for x in got}}
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
        # Board B3: the check answers are used for the build, not looked up again.
        self.assertEqual(sorted(calls['checked']), [1, 2, 3])
        self.assertEqual(sorted(calls['scans']), [1, 2, 3])

    def test_an_episode_missed_by_the_lanes_is_looked_up_once_more(self):
        # ISSUE-178 (owner log 77b35834): episodes 9 and 22 timed out with three lookups at once and were "not found".
        import unittest.mock  # noqa: F401
        tries = iter([[], ['1080p']])
        out, calls = self.run_build({1: ['1080p'], 2: lambda: next(tries), 3: ['1080p']})
        self.assertEqual(sorted(calls['scans']), [1, 2, 2, 3])
        self.assertEqual(sorted(n for n, q in calls['queued']), [1, 2, 3])
        self.assertEqual(out, [1, 2, 3])

    def test_a_retry_that_still_finds_nothing_leaves_it_out(self):
        import unittest.mock  # noqa: F401
        out, calls = self.run_build({1: ['1080p'], 3: ['1080p']})
        self.assertEqual(sorted(calls['scans']), [1, 2, 2, 3])
        self.assertEqual(sorted(n for n, q in calls['queued']), [1, 3])

    def test_nothing_queues_without_download_all(self):
        import unittest.mock  # noqa: F401
        out, calls = self.run_build({1: ['1080p']}, confirm=False)
        self.assertEqual((out, calls['queued']), ([], []))


class QualityWindow(unittest.TestCase):
    def test_round_3_window_has_three_rows_a_check_card_and_a_grey_build(self):
        import xml.etree.ElementTree as ET
        portrait = importlib.util.module_from_spec(importlib.util.spec_from_file_location('portrait_b3', LIB / 'portrait.py'))
        portrait.__spec__.loader.exec_module(portrait)
        import pages
        xml = pages.season_quality_sheet(portrait)
        root = ET.fromstring(xml)
        ids = {c.get('id') for c in root.iter('control') if c.get('id')}
        self.assertTrue({'9701', '9702', '9703', '9720', '9721'} <= ids)
        self.assertNotIn('9704', ids)                                   # 480p is gone
        self.assertIn('Integer.IsGreaterOrEqual(Window().Property(check.pct),35)', xml)
        self.assertIn('<enable>String.IsEmpty(Window().Property(q.1.off))</enable>', xml)   # greyed rows cannot be chosen
        self.assertIn('<enable>String.IsEmpty(Window().Property(button.off))</enable>', xml)
        self.assertIn('circle_line.png', xml)
        self.assertNotIn('!!', xml)
        self.assertIn('circle_line.png', portrait.textures())


class EveryEpisode(unittest.TestCase):
    def test_full_list_tags_lower_and_left_out_with_details(self):
        # Board F (owner 2026-11-12): "28 more episodes" shows every episode with its details, 720p only and so on.
        picks = {1: ('1080p', 0.26), 7: ('720p', 0.2), 30: (None, 0)}
        m = ss.ready_model('Naruto Shippuden', 1, '1080p', picks, {1: 'Homecoming'}, {1: 'HEVC \u00b7 232 seeds', 7: 'H.264 \u00b7 9 seeds'})
        rows = {r['no']: r for r in m['all']}
        self.assertEqual((rows['1']['detail'], rows['1']['low'], rows['1']['kind']), ('1080p \u00b7 HEVC \u00b7 232 seeds', '', 'ok'))
        self.assertEqual((rows['7']['detail'], rows['7']['low'], rows['7']['kind']), ('720p only \u00b7 H.264 \u00b7 9 seeds', '720p', 'lower'))
        self.assertEqual((rows['30']['gone'], rows['30']['kind'], rows['30']['detail']), ('true', 'gone', 'Not found in any quality yet'))
        self.assertEqual([r['no'] for r in ss.filter_rows(m['all'], 'lower')], ['7'])
        props = ss.episodes_props(m, 'all')
        self.assertEqual((props['title'], props['back'], props['f.lower'], props['f.gone']), ('All 3 episodes', '\u2039 Season 1', 'Lower 1', 'Not found 1'))

if __name__ == '__main__':
    import unittest.mock  # noqa: F401
    unittest.main()
