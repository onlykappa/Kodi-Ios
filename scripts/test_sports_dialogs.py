"""ISSUE-362 (owner log 6f2ebc1a, build 551): the Sports landing page and Live Now are dialogs (WindowXMLDialog, modal). Upcoming,
Leagues and a game's page were full windows (WindowXML), and Kodi refuses to open a full window while a dialog is open:
"Activate of window '13001' refused because there are active modal dialogs". Upcoming (tile and Live's "See upcoming"), Leagues
and every game tap did nothing. Every Sports page opened from another Sports page must be a dialog too. (Host tests use fakes,
so this reads the source.)"""
import re
import unittest
from pathlib import Path

BOOT = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap'
PAGES = ('sports', 'sports_live', 'sports_upcoming', 'sports_leagues', 'sports_game', 'sports_league')


class Dialogs(unittest.TestCase):
    def test_every_sports_page_is_a_dialog(self):
        for name in PAGES:
            path = BOOT / (name + '.py')
            if not path.is_file():
                continue
            source = path.read_text()
            bases = re.findall(r'class \w+\(xbmcgui\.(\w+)\)', source)
            for base in bases:
                self.assertEqual(base, 'WindowXMLDialog', '%s opens from another Sports page: it must be a dialog' % name)

    def test_the_pages_that_were_full_windows_are_covered(self):
        for name in ('sports_upcoming', 'sports_leagues', 'sports_game'):
            self.assertIn('(xbmcgui.WindowXMLDialog):', (BOOT / (name + '.py')).read_text())


if __name__ == '__main__':
    unittest.main()
