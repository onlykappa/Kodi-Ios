"""ISSUE-291 (owner, build 442): tapping a row's title on Home, Movies and TV opens that row as an artwork-only grid."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import portrait  # noqa: E402


class TitleOpensGrid(unittest.TestCase):
    def test_each_row_title_has_a_tap_that_opens_its_list(self):
        widgets = [{'label': 'Trending Movies', 'path': 'plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie'},
                   {'label': 'Netflix Originals', 'path': 'plugin://x/?a=1&b=2'}]
        xml = ''.join(portrait.row(i, w, i == len(widgets) - 1, 'home', {}) for i, w in enumerate(widgets))
        for i, w in enumerate(widgets):
            button = re.search(r'<control type="button" id="%d">(.*?)</control>' % (5701 + i), xml)
            self.assertTrue(button, w['label'])
            self.assertIn('SetProperty(Portrait.Title,%s,home)' % w['label'], button.group(1))
            self.assertIn('ActivateWindow(Videos,%s,return)' % portrait.e(w['path']), button.group(1))
            self.assertIn('<height>128</height>', button.group(1))        # 44 pt or more

    def test_every_hub_row_gets_it(self):
        self.assertIn("title_tap(id,title,widget.get('path') or '',visible)", (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text())


if __name__ == '__main__':
    unittest.main()
