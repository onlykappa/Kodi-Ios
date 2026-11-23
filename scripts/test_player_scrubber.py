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
        self.assertEqual(heights['!Player.Seeking'], 16); self.assertEqual(heights['Player.Seeking'], 32)   # Player.Seeking: Kodi iOS patch (IOSScrub), true under the finger
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
        rest = [c for c in controls('label') if c.findtext('label') == '$INFO[Player.Time]']
        drag = [c for c in controls('label') if c.findtext('label') == '$INFO[Player.SeekTime]' and c.findtext('visible') == 'Player.Seeking']
        self.assertEqual({c.findtext('textcolor'): c.findtext('visible') for c in rest}, {'B3FFFFFF': '!Player.Seeking'})
        self.assertEqual([c.findtext('textcolor') for c in drag], ['FFFFFFFF'])   # the time under the finger, white
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

    def test_the_frame_card_rides_above_the_finger_one_copy_per_percent(self):
        """Mockup 'while dragging': a card with the time under the finger and the jump from where you were. Kodi cannot place a control by a value, so each whole percent has
        its own copy at that share of the bar's width, shown only while Player.Seeking and Player.Progress is that percent (verified in the desktop rig with real mouse drags)."""
        groups = [g for g in controls('group') if 'Integer.IsEqual(Player.Progress,' in (g.findtext('visible') or '')]
        self.assertEqual(len(groups), 101)
        shown = {int(re.search(r'Progress,(\d+)', g.findtext('visible')).group(1)): g for g in groups}
        self.assertEqual(sorted(shown), list(range(101)))
        for n, g in shown.items():
            self.assertTrue(g.findtext('visible').startswith('Player.Seeking + '))
            self.assertEqual(g.findtext('left'), '%d%%' % min(88, max(12, n)))   # a share of the bar, kept 12-88 % so the card stays on the screen
            labels = [c.findtext('label') for c in g.iter('control') if c.get('type') == 'label']
            self.assertEqual(labels, ['$INFO[Player.SeekTime]', '$INFO[Player.SeekOffset]'])
        card = shown[50]
        self.assertTrue(any((c.findtext('texture') or '').endswith('scrub_card.png') for c in card.iter('control')))
    def test_the_card_picture_is_generated_at_its_own_size(self):
        import portrait
        self.assertIn("'scrub_card.png':scrub_card(470,264,26,5)", Path(portrait.__file__).read_text())
    def test_the_native_patch_carries_the_scrub_state(self):
        patch = (ROOT / 'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()
        for needle in ('+++ b/xbmc/guilib/IOSScrub.h', 'IOSScrub::percent = GetPercentage();', 'IOSScrub::Active() ? IOSScrub::percent.load()',
                       'value = IOSScrub::Active() || m_appPlayer->GetSeekHandler().InProgress();', 'm_fPercent = std::max(0.0f, std::min(IOSScrub::percent.load(), 100.0f));'):
            self.assertIn(needle, patch)


if __name__ == '__main__':
    unittest.main()
