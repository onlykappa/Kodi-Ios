"""page_watch: the one line that says why the library page's folder changed."""
import sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import page_watch as pw

EPISODES = 'plugin://plugin.video.kodi.ios.watch/?action=library&kind=tv&season=4&driveid=14519795631397522902&token=SECRET'
SEASONS = 'plugin://plugin.video.kodi.ios.watch/?action=library&kind=tv&driveid=14519795631397522902'


class Watch(unittest.TestCase):
    def test_the_path_is_shortened_to_what_is_safe_to_log(self):
        text = pw.short(EPISODES)
        self.assertEqual(text, 'plugin.video.kodi.ios.watch action=library kind=tv season=4')
        for secret in ('14519795631397522902', 'SECRET', 'driveid', 'token'):
            self.assertNotIn(secret, text)
        self.assertEqual(pw.short(''), '')
        self.assertEqual(pw.short('videodb://tvshows/titles/12?x=1'), 'videodb://tvshows')
    def test_a_change_after_a_menu_closed_says_so(self):
        state, lines = {}, []
        for now, path, menu in ((0.0, EPISODES, False), (1.0, EPISODES, True), (2.0, EPISODES, True), (2.6, EPISODES, False), (3.0, SEASONS, False)):
            line = pw.step(state, now, path, menu, 'episodes')
            if line: lines.append(line)
        self.assertEqual(len(lines), 1)
        self.assertIn('from "plugin.video.kodi.ios.watch action=library kind=tv season=4" to "plugin.video.kodi.ios.watch action=library kind=tv"', lines[0])
        self.assertIn('the menu closed 0.4 s ago', lines[0])
    def test_a_drive_refresh_just_before_is_named_and_no_change_is_silent(self):
        state = {}
        self.assertIsNone(pw.step(state, 0.0, EPISODES, False, 'episodes'))        # the first reading is only remembered
        self.assertIsNone(pw.step(state, 1.0, EPISODES, False, 'episodes'))        # no change, no line
        line = pw.step(state, 10.0, SEASONS, False, 'seasons', refreshed_at=7.5)
        self.assertIn('the Drive lists were refreshed 2.5 s ago', line)
        self.assertNotIn('menu', line)
    def test_an_empty_path_while_the_window_changes_is_not_logged(self):
        state = {}
        pw.step(state, 0.0, EPISODES, False, 'episodes')
        self.assertIsNone(pw.step(state, 1.0, '', False, ''))


if __name__ == '__main__':
    unittest.main()
