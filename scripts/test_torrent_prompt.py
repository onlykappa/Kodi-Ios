"""The torrent popup and the VPN hint (owner, 2026-11-23). The hint is read from the phone's own interface list; these tests use lists shaped like the ones the logs imply,
and prove what the code decides, not what an iPhone's network does."""
import sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import vpn_hint, torrent_prompt, elementum_download as ed

WIFI = [('lo0', '127.0.0.1'), ('en0', '192.168.1.20')]
CELL = [('lo0', '127.0.0.1'), ('pdp_ip0', '10.20.30.40')]
VPN_ON_WIFI = WIFI + [('utun4', '10.2.0.2')]


class Hint(unittest.TestCase):
    def test_a_vpn_carrying_the_traffic_is_the_route_through_a_tunnel(self):
        found = vpn_hint.look('10.2.0.2', VPN_ON_WIFI)
        self.assertEqual((found['state'], found['route'], found['tunnels']), ('tunnel', 'utun4', ['utun4']))
    def test_wifi_and_cellular_without_a_vpn_are_direct(self):
        self.assertEqual(vpn_hint.look('192.168.1.20', WIFI)['state'], 'direct'); self.assertEqual(vpn_hint.look('10.20.30.40', CELL)['state'], 'direct')
    def test_a_helper_tunnel_that_does_not_take_the_route_is_not_a_vpn(self):   # LocalDevVPN: a tunnel exists, the default route stays on Wi-Fi
        found = vpn_hint.look('192.168.1.20', WIFI + [('utun5', '10.7.0.1')])
        self.assertEqual((found['state'], found['tunnels']), ('direct', ['utun5']))
    def test_no_route_or_an_unknown_interface_is_unknown(self):
        self.assertEqual(vpn_hint.look('', WIFI)['state'], 'unknown'); self.assertEqual(vpn_hint.look('9.9.9.9', WIFI)['state'], 'unknown')
        self.assertEqual(vpn_hint.look('10.1.1.1', [('awdl0', '10.1.1.1')])['state'], 'unknown')
    def test_the_log_line_has_names_only(self):
        text = vpn_hint.line(vpn_hint.look('10.2.0.2', VPN_ON_WIFI))
        self.assertEqual(text, 'vpn check: a VPN looks active; default route via utun4; tunnel interfaces: utun4'); self.assertNotIn('10.2', text)
        self.assertIn('no VPN', vpn_hint.line(vpn_hint.look('192.168.1.20', WIFI)))
    def test_a_failing_reader_gives_unknown_not_an_error(self):
        self.assertEqual(vpn_hint.current(lambda: 1 / 0, lambda: [])['state'], 'unknown')


class Prompt(unittest.TestCase):
    class Dialog:
        def __init__(self, answer): self.answer, self.shown = answer, []
        def yesno(self, heading, message, nolabel='', yeslabel=''): self.shown.append((heading, message, nolabel, yeslabel)); return self.answer
    def test_the_words_follow_the_hint_and_cancel_is_the_first_choice(self):
        for state, status, yes in (('direct', 'No VPN detected', 'Download anyway'), ('unknown', 'Cannot tell if a VPN is on', 'Download anyway'), ('tunnel', 'A VPN looks active', 'Download')):
            dialog = self.Dialog(False); torrent_prompt.ask({'state': state, 'route': 'x', 'tunnels': []}, dialog)
            heading, text, no, yes_label = dialog.shown[0]
            self.assertEqual((heading, no, yes_label), ('Download this torrent directly?', 'Cancel', yes)); self.assertIn(status, text); self.assertIn('BitTorrent', text); self.assertIn('AllDebrid', text)
    def test_a_vpn_look_is_never_called_protected_or_verified_as_true(self):
        text = torrent_prompt.message({'state': 'tunnel', 'route': 'utun4', 'tunnels': ['utun4']})[0]
        self.assertIn('Not verified', text); self.assertNotIn('protected', text.lower())
    def test_the_answer_is_returned_and_logged_without_addresses(self):
        lines = []; self.assertTrue(torrent_prompt.ask({'state': 'direct', 'route': 'en0', 'tunnels': []}, self.Dialog(True), lines.append))
        self.assertFalse(torrent_prompt.ask({'state': 'direct', 'route': 'en0', 'tunnels': []}, self.Dialog(False), lines.append))
        self.assertTrue(any('cancelled; nothing started' in l for l in lines))


class Gate(unittest.TestCase):
    def follow(self, gate, route=lambda url: False):
        touched = []
        class Response:
            def read(self): return b''
            def close(self): pass
        class Opener:
            def open(self, url, timeout=0): touched.append(url); return Response()
        try:
            ed.follow('plugin://plugin.video.elementum/movie/1/download', opener=Opener(), route=route, gate=gate)
            return touched, None
        except ed.Canceled as error:
            return touched, error
    def test_declining_never_contacts_the_engine(self):
        def declined(): raise ed.Canceled('Nothing was started.')
        touched, error = self.follow(declined); self.assertEqual(touched, []); self.assertIsNotNone(error)
    def test_accepting_goes_on_to_the_engine(self):
        touched, error = self.follow(lambda: None); self.assertEqual(len(touched), 1); self.assertIsNone(error)
    def test_the_allDebrid_route_is_not_asked_about_and_the_gate_is_a_no_op_outside_kodi(self):
        asked = []; touched, _ = self.follow(lambda: asked.append(1), route=lambda url: True); self.assertEqual((asked, touched), ([], []))
        self.assertIsNone(ed._torrent_gate())
    def test_the_service_logs_the_hint_and_the_gate_is_wired_before_the_engine(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text(); self.assertIn('vpn_hint.line(found)', service); self.assertIn("KodiIOS.VPNLook", service)
        src = (ROOT / 'migration/bundled-bootstrap/resources/lib/elementum_download.py').read_text()
        self.assertLess(src.index('(gate or _torrent_gate)()'), src.index('if engine is not None:engine()'))


if __name__ == '__main__':
    unittest.main()
