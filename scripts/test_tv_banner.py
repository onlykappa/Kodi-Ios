"""ISSUE-345 (owner logs 53a92f39, a83e06c7: Play on TV pressed again and again while nothing showed): the owner-approved
mockup C, a slim banner at the top of the video from the moment a TV is picked: the step, a thin bar and Stop; then
"Playing on your TV" for two seconds. A second press only leaves it there."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
sys.dont_write_bytecode = True
import airplay_flow as af  # noqa: E402


class Words(unittest.TestCase):
    def test_each_step_has_its_line_and_bar(self):
        for stage, bar in (('opening', '22'), ('waiting_tv', '48'), ('connecting', '74')):
            v = af.banner_view(stage)
            self.assertEqual((v['bar'], v['stop']), (bar, 'Stop'))
            self.assertTrue(v['sub'].startswith('Step '))
        self.assertIn('Converting', af.banner_view('opening', converting=True)['title'])

    def test_done_says_where_the_tv_starts_and_has_no_stop(self):
        d = af.banner_done(1623.8)
        self.assertEqual((d['title'], d['sub'], d['stop'], d['bar']), ('Playing on your TV', 'From 27:03', '', ''))
        self.assertEqual(af.banner_done(3725)['sub'], 'From 1:02:05')


class Window(unittest.TestCase):
    def test_the_page(self):
        xml = af.banner_page()
        root = ET.fromstring(xml.split('\n', 2)[2])
        ids = {c.get('id') for c in root.iter('control') if c.get('id')}
        self.assertEqual(ids, {str(af.BANNER_BAR), str(af.BANNER_STOP)})
        self.assertNotIn('!!', xml)
        self.assertNotIn('!(', xml)
        pages = (BOOT / 'resources/lib/pages.py').read_text()
        self.assertIn("'1080i/IOSTVBanner.xml':_airplay_flow().banner_page()", pages)


class Wiring(unittest.TestCase):
    src = (BOOT / 'cast.py').read_text()

    def test_shown_before_the_source_is_opened(self):
        start = self.src.index('def send_airplay(')
        self.assertLess(self.src.index('_BANNER[0]=Banner(xbmc,_g)', start), self.src.index('remote_media.acquire(', start))

    def test_a_second_press_never_stops_and_shows_no_notice(self):
        self.assertNotIn("dialog.notification('Play on TV','Stopped'", self.src)
        self.assertNotIn('Still connecting to the TV', self.src)
        self.assertNotIn('tap Play on TV again to stop', self.src)

    def test_playing_then_two_seconds_then_gone(self):
        self.assertIn('_BANNER[0].done(at);_BANNER[0]=None', self.src)
        self.assertIn('self.apply(self.flow.banner_done(at));self.xbmc.sleep(2000);self.close()', self.src)


if __name__ == '__main__':
    unittest.main()
