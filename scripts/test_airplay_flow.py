"""Play on TV card (owner-approved boards 1-3, 5 and 6, 2026-11-08): the words of each stage and problem, the buttons
and what they do, and the window's controls (ids, touch sizes, one-line text). Structural only; the look is checked in
the desktop Kodi rig and on the iPhone."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True
import airplay_flow as f  # noqa: E402
import pages  # noqa: E402


class Views(unittest.TestCase):
    def test_steps_follow_the_stage(self):
        v = f.stage_view('opening', 'Interstellar (2014)')
        self.assertEqual([v['step%d.state' % n] for n in range(3)], ['active', 'todo', 'todo'])
        self.assertEqual(v['step0.note'], 'reading its index')
        v = f.stage_view('connecting', 'Interstellar (2014)')
        self.assertEqual([v['step%d.state' % n] for n in range(3)], ['done', 'done', 'active'])
        self.assertEqual((v['step0.label'], v['step2.label']), ('Movie opened', 'Waiting for the TV to start playing'))
        self.assertEqual(v['cancel.label'], 'Cancel')
        self.assertLess(int(f.stage_view('opening')['bar']), int(v['bar']))

    def test_a_direct_link_skips_opening_but_still_shows_the_tv_choice_running(self):
        v = f.stage_view('waiting_tv', skipped=('opening', 'waiting_tv'))
        self.assertEqual([v['step%d.state' % n] for n in range(3)], ['done', 'active', 'todo'])

    def test_slow_opening_names_the_busy_line_and_never_the_network(self):
        model = {'jobs': [{'state': 'running', 'kind': 'repack', 'title': 'Interstellar (2014)', 'rate': 0.3 * 1048576}]}
        busy = f.busy_words(model)
        self.assertEqual(busy, 'Interstellar (2014) is uploading to Google Drive at 0.3 MB/s')
        v = f.problem_view('startup_timeout', 'Scary Movie', busy=busy)
        self.assertIn(busy, v['text']);self.assertNotIn('Local Network', v['text'])
        self.assertEqual((v['b1.label'], v['b1.action'], v['b2.action'], v['link.action']),
                         ('Pause uploads and try again', 'pause_retry', 'retry', 'watch'))
        quiet = f.problem_view('startup_timeout', 'Scary Movie')
        self.assertEqual((quiet['b1.action'], quiet['b2.label']), ('retry', ''))
        self.assertEqual(f.busy_words({'jobs': [{'state': 'paused_by_you', 'kind': 'conv', 'title': 'X'}]}), '')

    def test_unreachable_has_the_checklist_and_open_settings_when_the_framework_can(self):
        v = f.problem_view('unreachable', 'Scary Movie', settings=True)
        self.assertEqual((v['check1'], v['check1.note'], v['check2']),
                         ('Local Network is on for Kodi', 'Settings › Kodi', 'The TV and this iPhone are on the same Wi-Fi'))
        self.assertEqual([v['b%d.action' % n] for n in (1, 2, 3)], ['settings', 'retry', 'watch'])
        self.assertEqual(v['size'], 'long')
        self.assertEqual(f.problem_view('unreachable', 'X')['b1.action'], 'retry')   # an older framework: no Settings link

    def test_every_problem_has_a_way_out(self):
        for kind in ('startup_timeout', 'unreachable', 'selection_timeout', 'failed', 'mirroring'):
            v = f.problem_view(kind, 'X', 'reason')
            actions = {v[k] for k in ('b1.action', 'b2.action', 'b3.action', 'link.action') if v[k]}
            self.assertIn('watch', actions, kind);self.assertTrue(v['title'])
            self.assertNotEqual(v['b1.label'], 'OK' if kind != 'mirroring' else '', kind)


class EpisodeCard(unittest.TestCase):
    """Owner (build 229): the card said movie for an episode and its poster tile stayed grey."""
    def test_episode_words_and_poster(self):
        v = f.stage_view('opening', 'Dragon Ball Super \u00b7 S1 E1', kind='episode', poster='image://p.jpg/')
        self.assertEqual((v['step0.label'], v['poster']), ('Opening the episode', 'image://p.jpg/'))
        self.assertEqual(f.stage_view('waiting_tv', kind='episode')['step0.label'], 'Episode opened')
        self.assertEqual(f.stage_view('opening')['step0.label'], 'Opening the movie')
    def test_cast_sets_kind_and_poster(self):
        src = (ROOT / 'migration/bundled-bootstrap/cast.py').read_text()
        self.assertIn("Player.Art(tvshow.poster)", src); self.assertEqual(src.count('kind=self.kind,poster=self.poster'), 2)


class Window(unittest.TestCase):
    def setUp(self):
        self.xml = f.page(pages.close_button_1080)
        self.root = ET.fromstring(self.xml.split('\n', 2)[2])

    def test_controls_and_touch_sizes(self):
        ids = {c.get('id') for c in self.root.iter('control') if c.get('id')}
        for n in (f.CLOSE, f.B1, f.B2, f.B3, f.LINK, f.BAR, 9704):
            self.assertIn(str(n), ids)
        for c in self.root.iter('control'):
            if c.get('type') == 'button':
                self.assertGreaterEqual(int(c.findtext('height')), 118, c.get('id'))
            if c.get('type') == 'label':
                self.assertEqual(c.findtext('scroll'), 'false', c.findtext('label'))
        self.assertNotIn('!!', self.xml)

    def test_registered_for_landscape_only(self):
        import portrait
        self.assertIn('IOSAirPlayFlow.xml', portrait.VIDEO_ONLY);self.assertIn('IOSAirPlayFlow.xml', portrait.OWN_1080I)
        self.assertIn("'1080i/IOSAirPlayFlow.xml'", (LIB / 'pages.py').read_text())

    def test_the_bar_is_set_only_while_the_card_is_open(self):
        src = (LIB / 'airplay_flow.py').read_text()
        self.assertIn('self.guard.percent(BAR', src)   # from the attempt's thread; onInit sets the first value itself


if __name__ == '__main__':
    unittest.main()
