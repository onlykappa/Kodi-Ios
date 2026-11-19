"""The Home / Movies / TV header icons (owner, 2026-11-19): no filled circle behind settings and refresh, one solid icon family with the bell
(the skin's 6-tooth gear, the clockwise arrow), all three the same size, a light hairline ring to show where to tap, a 44 pt hit target."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB))
spec = importlib.util.spec_from_file_location('portrait_header_icons', LIB / 'portrait.py')
portrait = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portrait)


class HeaderIcons(unittest.TestCase):
    def pieces(self):
        return {'settings': portrait.header_button(9206, 0, 0, 'gear.png', 'noop'), 'refresh': portrait.refresh_button(0, 0, 'home'),
                'bell': portrait.bell(0, 0)}

    def test_no_glass_circle_behind_any_of_them(self):
        for name, xml in self.pieces().items():
            self.assertNotIn('glass_', xml, name)
            self.assertNotIn('pill_108', xml, name)

    def test_one_size_a_ring_and_a_real_hit_target(self):
        for name, xml in self.pieces().items():
            self.assertIn('hdr_ring.png', xml, name)
            self.assertIn('<width>%d</width><height>%d</height>' % (portrait.HDR_BOX, portrait.HDR_BOX), xml, name)
            self.assertIn('<width>118</width><height>118</height>', xml, name)   # 44 pt

    def test_the_icons_are_the_skins_solid_family(self):
        pieces = self.pieces()
        self.assertIn('gear.png', pieces['settings'])
        self.assertNotIn('hdr_gear.png', pieces['settings'])   # the old chunky 8-tooth gear is gone
        self.assertIn('arrow-rotate-right.png', pieces['refresh'])
        self.assertIn('bell.png', pieces['bell'])

    def test_the_ring_texture_is_generated_and_the_bell_hides_it_while_its_progress_ring_shows(self):
        self.assertIn('hdr_ring.png', portrait.header_glyphs())
        ring = portrait.bell(0, 0).split('hdr_ring.png</texture>')[1]
        self.assertTrue(ring.startswith('<visible>String.IsEmpty(Window(Home).Property(Notices.Active))</visible>'))   # idle only

    def test_refresh_still_spins_while_loading_and_ticks_when_done(self):
        xml = self.pieces()['refresh']
        self.assertIn('effect="rotate"', xml)
        self.assertIn('circle-check.png', xml)
        self.assertIn('refresh_rows,tab=home', xml)


if __name__ == '__main__':
    unittest.main()
