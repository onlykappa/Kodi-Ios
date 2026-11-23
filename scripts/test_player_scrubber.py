"""The Apple-style scrubber of the video controls (owner-approved mockup docs/design/player-scrubber-mockup.html, 2026-11-23): what the generated VideoOSD holds."""
import re, sys, unittest
import xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import player_osd as osd

XML = osd.window()
ROOT_EL = ET.fromstring(XML.split('\n', 2)[2] if XML.startswith('<?xml') else XML)


def controls(kind=None):
    return [c for c in ROOT_EL.iter('control') if kind is None or c.get('type') == kind]


class Scrubber(unittest.TestCase):
    def test_two_thin_rounded_bars_one_thick_while_the_slider_is_dragged(self):
        bars = [c for c in controls('progress') if c.findtext('info') == 'Player.Progress']
        heights = {c.findtext('visible'): int(c.findtext('height')) for c in bars}
        self.assertEqual(sorted(heights.values()), [16, 32])
        self.assertEqual(heights['!Control.HasFocus(7131)'], 16); self.assertEqual(heights['Control.HasFocus(7131)'], 32)
        for c in bars:
            h = int(c.findtext('height')); self.assertEqual(int(c.find('texturebg').get('border')), h // 2)   # fully rounded ends
    def test_there_is_no_knob_at_rest_or_while_dragging(self):
        slider = next(c for c in controls('slider') if c.get('id') == '7131')
        for tag in ('textureslidernib', 'textureslidernibfocus'):
            self.assertTrue(slider.findtext(tag).endswith('clear48.png'))
        self.assertNotIn('knob.png', XML)
    def test_elapsed_left_and_remaining_or_total_right_and_the_right_one_toggles(self):
        labels = [c.findtext('label') for c in controls('label')]
        self.assertIn('$INFO[Player.Time]', labels); self.assertIn('-$INFO[Player.TimeRemaining]', labels); self.assertIn('$INFO[Player.Duration]', labels)
        toggle = next(c for c in controls('button') if c.get('id') == '7132')
        self.assertIn('Skin.ToggleSetting(ios_osd_total)', [c.text for c in toggle.findall('onclick')])   # after the controls' own re-arm clicks
    def test_the_times_turn_white_while_dragging(self):
        left = [c for c in controls('label') if c.findtext('label') == '$INFO[Player.Time]']
        self.assertEqual({c.findtext('textcolor'): c.findtext('visible') for c in left}, {'B3FFFFFF': '!Control.HasFocus(7131)', 'FFFFFFFF': 'Control.HasFocus(7131)'})
    def test_info_and_continue_watching_moved_down_and_nothing_else_lost(self):
        tops = {c.get('id'): int(c.findtext('top')) for c in controls('button') if c.get('id') in ('7141', '7142')}
        self.assertEqual(tops, {'7141': 970, '7142': 970})
        ids = {c.get('id') for c in controls() if c.get('id')}
        self.assertTrue({'7101', '7102', '7111', '7112', '7113', '7121', '7122', '7123', '7131', '7132', '7141', '7142', '7201'} <= ids)
        all_ids = [c.get('id') for c in controls() if c.get('id')]; self.assertEqual(len(all_ids), len(set(all_ids)))
    def test_kodi_condition_rules(self):
        for cond in re.findall(r'<visible>(.*?)</visible>', XML):
            self.assertNotIn('$INFO', cond); self.assertNotIn('!(', cond)
    def test_the_times_clear_the_bar_and_the_bottom_edge(self):
        for c in controls('label'):
            if c.findtext('label') in ('$INFO[Player.Time]',):
                self.assertGreaterEqual(int(c.findtext('top')), 906)   # under the bar (bar group 862 + thick bar ends at 862+46)
        self.assertLessEqual(970 + 54, 1080 - 21 * 2.68 // 1 + 0.5 or 1080)   # the row ends above the home indicator's strip (about 56 units)


if __name__ == '__main__':
    unittest.main()
