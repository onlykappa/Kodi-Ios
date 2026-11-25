"""The episode card of the show page (owner, build 698 screenshot: the description was cut off after two lines)."""
import re, sys, unittest
import xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import portrait


class Card(unittest.TestCase):
    def test_four_lines_of_plot_fit_inside_the_card_and_the_card_inside_its_row(self):
        for focused in (False, True):
            root = ET.fromstring(portrait.episode_item(focused))
            plot = next(c for c in root.iter('control') if c.findtext('label') == '$INFO[ListItem.Plot]')
            top, height = int(plot.findtext('top')), int(plot.findtext('height'))
            self.assertGreaterEqual(height, 144)                      # four lines of about 36 units
            self.assertLessEqual(top + height, portrait.EPISODE_H - 20)   # the row keeps a gap below the text
    def test_no_row_is_drawn_as_chosen_and_a_tap_names_its_episode(self):
        self.assertEqual(portrait.episode_item(True), portrait.episode_item(False))   # the focused card (the highlight that stayed after scrolling) is gone
        self.assertNotIn('round_s.png', portrait.episode_item(True))
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertEqual(text.count('<onclick>SetProperty(KodiIOS.EpisodeTap,'), 1)   # one template, used by both episode lists
    def test_both_episode_lists_use_the_same_row_height(self):
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn("'<itemlayout height=\"%d\">%s</itemlayout><focusedlayout height=\"%d\">%s</focusedlayout>%s</control>')", text)
        self.assertEqual(text.count('EPISODE_H,episode_item(False),EPISODE_H,episode_item(True)'), 2)


if __name__ == '__main__':
    unittest.main()
