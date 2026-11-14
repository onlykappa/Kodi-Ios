"""DEC-049 (owner-approved docs/design/quality-choice-mockups.html): when the chosen quality does not exist for a season,
the app asks once (boards A-D) instead of downloading a lower version or looping (ISSUE-264)."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(ROOT / 'migration/deck-picker'))
import quality_choice as qc  # noqa: E402
import elementum_cloud  # noqa: E402
import deck_picker as dp  # noqa: E402

FOLDER = 'Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio) Season 02 (033-053)/'


class Lifecycle(unittest.TestCase):
    def test_ask_once_then_the_answer_is_kept(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertEqual(qc.state(p, '31910', 2), '')
            self.assertTrue(qc.hold(p, '31910', 2, 33, '1080p', 'Naruto Shippuden', best={'name': 'x.480p', 'quality': '480p'}))
            self.assertFalse(qc.hold(p, '31910', 2, 34, '1080p', 'Naruto Shippuden'))      # one notice per season
            self.assertEqual(qc.state(p, '31910', 2), 'asking')
            self.assertEqual(list(qc.waiting(p, '31910')), [2])
            self.assertEqual(qc.answer(p, '31910', 2, 'best'), [33, 34])                   # the held episodes, looked up again
            self.assertTrue(qc.lets_fallback(qc.state(p, '31910', 2)))
            self.assertEqual(qc.waiting(p, '31910'), {})
            self.assertEqual(qc.state(p, '31910', 3), '')                                   # another season still asks

    def test_keep_looking_holds_for_a_day_and_always_answers_the_show(self):
        with tempfile.TemporaryDirectory() as p:
            qc.hold(p, '1', 1, 5, '1080p', 'Show', now=0)
            self.assertEqual(qc.answer(p, '1', 1, 'looking', now=100), [5])
            self.assertEqual(qc.state(p, '1', 1, now=200), 'looking')
            self.assertEqual(qc.state(p, '1', 1, now=100 + qc.LOOK_AGAIN), '')              # asks again tomorrow
            qc.answer(p, '1', 1, 'always')
            self.assertEqual(qc.state(p, '1', 7), 'best')                                   # every season of the show
            qc.hold(p, '9', 1, 1, '1080p', 'Other');qc.answer(p, '9', 1, 'chosen', FOLDER + 'Episode 033.mkv')
            self.assertEqual(qc.preferred(p, '9', 1), FOLDER + 'Episode 033.mkv')


class Boards(unittest.TestCase):
    def test_board_a_b_c_words(self):
        record = {'quality': '1080p', 'title': 'Naruto Shippuden', 'episodes': [33, 34],
                  'best': {'name': 'Naruto.Shippuden.S02E33.480p.NF.WEB-DL.mkv', 'quality': '480p'},
                  'found': {FOLDER.rstrip('/').casefold(): '640x480'},
                  'versions': [{'name': 'Naruto.Shippuden.S02E33.480p.NF.WEB-DL.mkv', 'quality': '480p', 'seeds': 1, 'size': 0.18},
                               {'name': FOLDER + 'Naruto Shippuden Episode 033 T.mkv', 'quality': '1080p', 'seeds': 232, 'size': 0.26}]}
        title, text = qc.notice(record, 2)
        self.assertEqual(title, 'No real 1080p for season 2')
        self.assertIn('the best is 480p', text);self.assertTrue(text.endswith('Tap to choose.'))
        spec, actions = qc.sheet(record, 2)
        self.assertEqual(actions, ['best', 'versions', 'looking', 'always'])
        self.assertEqual(spec['heading'], 'Season 2 isn’t in real 1080p')
        self.assertIn('640×480', spec['sub']);self.assertEqual(spec['rows'][0]['label'], 'Use the Best · 480p')
        self.assertTrue(spec['rows'][0]['detail'].startswith('2 episodes waiting'));self.assertEqual(spec['rows'][3]['label'], 'Always Use the Best')
        vspec, names = qc.versions_sheet(record, 2)
        self.assertEqual(len(names), 2)
        self.assertEqual((vspec['rows'][1]['tag'], vspec['rows'][1]['tag_kind']), ('480p', 'warn'))   # found lower: marked
        self.assertEqual(vspec['rows'][0]['tag'], '480p')
        self.assertIn('Says 1080p · really 640×480', vspec['rows'][1]['detail'])
        help_ = importlib.import_module('notice_help').explain({'title': title, 'text': text, 'kind': 'problem', 'action': 'x'})
        self.assertEqual(help_['fixes'][0][0], 'Choose')

    def test_board_d_on_the_show_page(self):
        page = (LIB / 'library_show_page.py').read_text()
        self.assertIn("'Waiting for your choice'", page);self.assertIn('CHOOSE', page)
        manager = (ROOT / 'migration/bundled-bootstrap/library_manager.py').read_text()
        self.assertIn("quality_choice.waiting(profile, self.tmdb())", manager)
        self.assertIn("RunScript(service.kodi.ios.bootstrap,quality_choice,tmdb=%s,season=%d)", manager)
        self.assertIn("'quality_choice'", (ROOT / 'migration/bundled-bootstrap/default.py').read_text())


class Gate(unittest.TestCase):
    """The automatic pick: a fallback for an unanswered season is held, not queued; an answered one goes through."""
    def auto(self):
        return {'_fallback': True, 'profile': {'quality': '1080p', 'strict_quality': True}, '_pick_name': 'x.480p.mkv',
                '_pick_quality': '480p', '_versions': [], 'request_id': 'r1'}

    def test_held_until_answered(self):
        with tempfile.TemporaryDirectory() as p:
            noted = []
            fake = types.SimpleNamespace(note=lambda *a: noted.append(a))
            with mock.patch.dict(sys.modules, {'notices': fake}):
                tracked = {'tmdb': '31910', 'season': 2, 'title': 'Naruto Shippuden'}
                self.assertTrue(elementum_cloud.held_for_choice(p, self.auto(), tracked, {'episode': 33}, 'Naruto Shippuden'))
                self.assertTrue(elementum_cloud.held_for_choice(p, self.auto(), tracked, {'episode': 34}, 'Naruto Shippuden'))
                self.assertEqual(len(noted), 1)                                                  # board A once
                self.assertIn('quality_choice,tmdb=31910,season=2', noted[0][3])
                qc.answer(p, '31910', 2, 'best')
                self.assertFalse(elementum_cloud.held_for_choice(p, self.auto(), tracked, {'episode': 35}, 'Naruto Shippuden'))
                real = dict(self.auto(), _fallback=False)
                self.assertFalse(elementum_cloud.held_for_choice(p, real, {'tmdb': '7', 'season': 1}, {'episode': 1}, 'X'))

    def test_the_chosen_version_is_taken_first(self):
        mine = {'idx': 0, 'name': FOLDER + 'Naruto Shippuden Episode 034 T.mkv', 'size': 0.26, 'quality': '1080p', 'tags_text': '',
                'multi': False, 'seeds': 232, 'peers': 0, 'providers': []}
        other = dict(mine, name='Naruto.Shippuden.S02E34.480p.mkv', quality='480p', seeds=9, size=0.18)
        best = dp.auto_choose([other, mine], {'quality': '1080p', 'strict_quality': True, 'runtime': 23,
                                              'prefer_names': [FOLDER + 'Naruto Shippuden Episode 033 T.mkv']})
        self.assertEqual(best['name'], mine['name']);self.assertTrue(best['fallback'])
        ranked = []
        dp.auto_choose([other, mine], {'quality': '720p', 'strict_quality': True, 'runtime': 23}, ranked)
        self.assertEqual(len(ranked), 2)


class Repair(unittest.TestCase):
    def test_a_held_episode_is_not_nothing_found(self):
        import library_repair
        state, why = library_repair.repair(lambda *a, **k: {'held': True}, None, '1', 'Show', 2, 33, ['1080p'])
        self.assertEqual((state, why), ('held', 'Waiting for your choice'))
        page = (ROOT / 'migration/bundled-bootstrap/library_repair_page.py').read_text()
        self.assertIn("Looking up %d episodes", page)
        self.assertIn("quality_choice.state(profile, tmdb, season) in ('asking', 'looking')", page)


if __name__ == '__main__':
    unittest.main()
