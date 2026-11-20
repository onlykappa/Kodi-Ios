"""ISSUE-311: the reviewer's low items: the video controls' Continue Watching panel refreshes on a removal like the hub
rows; the removed activity pill leaves no settings strings or rig checks behind."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
import player_osd  # noqa: E402
import portrait  # noqa: E402


class LowItems(unittest.TestCase):
    def test_the_osd_panel_carries_the_continue_stamp(self):
        self.assertEqual(player_osd.CONTINUE_STAMP, portrait.CONTINUE_STAMP)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(player_osd.window().split('\n', 2)[2])  # a bare & would not parse
        content = [c.text for c in root.iter('content') if 'Portrait_Osd_Continue' in (c.text or '')][0]
        self.assertEqual(content, '$VAR[Portrait_Osd_Continue]')
        # build 615 log: the stamp was appended to an empty path, so Kodi asked for the folder "&stamp=" each time the player opened
        variable = re.search(r'<variable name="Portrait_Osd_Continue">(.*?)</variable>', portrait.VARIABLES).group(1)
        self.assertIn('condition="!String.IsEmpty(Skin.String(ios_osd_continue_path))"', variable)
        self.assertIn('stamp=$INFO[Window(Home).Property(KodiIOS.ContinueStamp)]', variable)
        self.assertTrue(variable.endswith('<value></value>'))

    def test_no_pill_strings_or_rig_checks_are_left(self):
        po = (BOOT / 'resources/language/resource.language.en_gb/strings.po').read_text()
        self.assertNotIn('activity pill', po)
        for n in range(32001, 32011):
            self.assertNotIn('"#%d"' % n, po)
            self.assertFalse(re.search(r'\b%d\b' % n, (BOOT / 'resources/settings.xml').read_text()))
        self.assertNotIn('activity_page', (ROOT / 'scripts/rig_smoke.py').read_text())


if __name__ == '__main__':
    unittest.main()
