"""Require VPN for torrents: the rules and the guard's sequence, on a computer (docs/security/ELEMENTUM-VPN.md). The phone and a real VPN are not involved: every
claim here is about what the code decides and does to Elementum's settings and API, never about what an iPhone's network does."""
import json, sys, unittest, unittest.mock
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))   # elementum_download imports from here too
import vpn_guard as g
import vpn_probe

HOME_IP, VPN_IP, VPN2_IP = '198.51.100.7', '203.0.113.50', '203.0.113.77'
WIFI = [('lo0', '127.0.0.1'), ('en0', '192.168.1.20')]
CELL = [('lo0', '127.0.0.1'), ('pdp_ip0', '10.20.30.40')]
def with_tunnel(table, name='utun4', addr='10.2.0.2'):
    return table + [(name, addr)]


class Phone:
    """The phone as the guard sees it: interfaces, what the echo service answers, Elementum's settings and its API calls."""
    def __init__(self, table=WIFI, exit_ip=HOME_IP, org='home isp'):
        self.table, self.exit_ip, self.org, self.answering = table, exit_ip, org, True
        self.settings = {'proxy_enabled': 'false', 'proxy_type': '0', 'proxy_host': 'my.proxy', 'proxy_port': '1080', 'proxy_login': '', 'proxy_password': '',
                         'use_proxy_download': 'true', 'use_proxy_tracker': 'true', 'use_proxy_http': 'true', 'proxy_force': 'false',
                         'listen_autodetect_ip': 'true', 'listen_interfaces': '', 'outgoing_interfaces': ''}
        self.calls, self.clock, self.shown, self.published, self.files = [], 0.0, [], [], {}
        self.on, self.expected = True, []
        self.direct_ip, self.direct_works = HOME_IP, True   # what the physical link shows, and whether it can be asked at all
    def echo(self, url, timeout):
        if not self.answering:
            raise OSError('no answer')
        return json.dumps({'ip': self.exit_ip, 'org': self.org})
    def direct_echo(self, url, interface, timeout):
        if not self.direct_works or not self.answering:
            raise OSError('the physical path is closed')
        return json.dumps({'ip': self.direct_ip, 'org': 'home isp'})
    def guard(self, endpoints=('https://echo.example/a',)):
        store = g.Store('/p/vpn_guard.json', read=lambda path: self.files.get(path, ''), write=lambda path, text: self.files.__setitem__(path, text))
        return g.Guard(store, lambda: self.on, lambda: self.expected, lambda: list(endpoints), lambda: self.table, lambda t: 'wifi' if any(n == 'en0' for n, _ in t) else 'cellular',
                       self.echo, (lambda k: self.settings.get(k, ''), self.settings.__setitem__), self.calls.append,
                       lambda state, text: self.published.append((state, text)), lambda title, text: self.shown.append(text), lambda: self.clock,
                       direct=self.direct_echo, physical=vpn_probe.physical)
    def run(self, guard, seconds, step=1.0):
        for _ in range(int(seconds / step)):
            self.clock += step
            guard.step()
        return guard.state
    def blocked(self):
        return all(self.settings[k] == v for k, v in g.TRAP.items())


class Rules(unittest.TestCase):
    def test_only_tunnel_class_interfaces_with_an_address_are_tunnels(self):
        table = WIFI + [('utun3', '10.8.0.2'), ('utun4', ''), ('awdl0', '169.254.1.1'), ('pdp_ip0', '10.1.1.1'), ('ipsec0', '10.9.9.9')]
        self.assertEqual(g.tunnels(table), [('ipsec0', '10.9.9.9'), ('utun3', '10.8.0.2')])
    def test_probe_formats_and_disagreement(self):
        self.assertEqual(g.parse_probe(b'{"ip": "203.0.113.5", "org": "AS1 Example VPN"}'), {'ip': '203.0.113.5', 'org': 'as1 example vpn'})
        self.assertEqual(g.parse_probe('203.0.113.5\n')['ip'], '203.0.113.5')
        self.assertIsNone(g.parse_probe('<html>blocked</html>'))
        answers = {'a': '{"ip": "203.0.113.5"}', 'b': '{"ip": "203.0.113.6"}'}
        self.assertIsNone(g.probe(['a', 'b'], lambda u, t: answers[u]))   # two services that disagree prove nothing
        self.assertEqual(g.probe(['a', 'a'], lambda u, t: answers[u])['ip'], '203.0.113.5')
        self.assertIsNone(g.probe(['a'], lambda u, t: 1 / 0))
    def test_decisions(self):
        salt = 's'; homes = [g.digest(HOME_IP, salt)]
        snap = {'tunnels': [('utun4', '10.2.0.2')], 'link': 'wifi'}
        self.assertEqual(g.decide(False, snap, None, homes, salt), ('off', 'off'))
        self.assertEqual(g.decide(True, {'tunnels': [], 'link': 'wifi'}, {'ip': VPN_IP, 'org': ''}, homes, salt), ('blocked', 'no_tunnel'))
        self.assertEqual(g.decide(True, snap, None, homes, salt), ('blocked', 'no_answer'))
        self.assertEqual(g.decide(True, snap, {'ip': HOME_IP, 'org': ''}, homes, salt), ('blocked', 'same_as_home'))
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': ''}, homes, salt), ('verified', 'verified'))
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': ''}, [], salt, (), [HOME_IP]), ('verified', 'verified'))   # asked both ways, differ
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': ''}, [], salt, (), [VPN_IP]), ('blocked', 'same_as_direct'))
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': ''}, [], salt), ('blocked', 'no_home'))   # nothing to compare with
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': 'example vpn ab'}, [], salt, ['Example VPN']), ('verified', 'verified'))
        self.assertEqual(g.decide(True, snap, {'ip': VPN_IP, 'org': 'some host'}, homes, salt, ['Example VPN']), ('blocked', 'unexpected_exit'))
    def test_gate_raises_with_a_sentence_and_lets_the_rest_through(self):
        self.assertIsNone(g.gate(False, ''));self.assertIsNone(g.gate(True, 'verified'))
        for state in ('', 'blocked', None):
            with self.assertRaises(g.Blocked) as caught:
                g.gate(True, state)
            self.assertIn('Connect your VPN to continue', str(caught.exception))


class Probe(unittest.TestCase):
    def test_only_wifi_and_cellular_interfaces_with_a_usable_address_are_physical(self):
        table = [('lo0', '127.0.0.1'), ('en0', '192.168.1.5'), ('en1', '169.254.1.2'), ('pdp_ip0', '10.20.30.40'), ('utun4', '10.2.0.2'), ('awdl0', '10.9.9.9'),
                 ('bridge100', '192.168.2.1'), ('en0', '192.168.1.5'), ('en2', '')]
        self.assertEqual(vpn_probe.physical(table), ['en0', 'pdp_ip0'])
    def test_the_interface_is_bound_with_the_systems_own_option(self):
        calls = []
        class Sock:
            def setsockopt(self, *args): calls.append(args)
        import socket as so
        orig = vpn_probe.sys.platform
        try:
            vpn_probe.sys.platform = 'darwin'; so.if_nametoindex = (lambda name: 7) if not hasattr(so, 'if_nametoindex') else so.if_nametoindex
            with unittest.mock.patch.object(so, 'if_nametoindex', lambda name: 7):
                vpn_probe.bind_interface(Sock(), 'en0')
            vpn_probe.sys.platform = 'linux'; vpn_probe.bind_interface(Sock(), 'eth0')
        finally:
            vpn_probe.sys.platform = orig
        self.assertEqual(calls[0], (so.IPPROTO_IP, vpn_probe.IP_BOUND_IF, 7)); self.assertEqual(calls[1], (so.SOL_SOCKET, vpn_probe.SO_BINDTODEVICE, b'eth0\0'))
    def test_get_reads_a_plain_http_answer_by_the_default_route(self):
        import http.server, threading
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                body = b'{"ip": "203.0.113.5"}'; self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        server = http.server.HTTPServer(('127.0.0.1', 0), H); threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            self.assertEqual(g.parse_probe(vpn_probe.get('http://127.0.0.1:%d/x?y=1' % server.server_port))['ip'], '203.0.113.5')
        finally:
            server.shutdown(); server.server_close()
        with self.assertRaises(ValueError): vpn_probe.get('ftp://x/')


class Sequence(unittest.TestCase):
    def setUp(self):
        self.p = Phone()
    def learned(self, guard):
        self.p.run(guard, 2)   # no tunnel: the home address is learned
    def connect(self, guard, seconds=12):
        self.p.table, self.p.exit_ip, self.p.org = with_tunnel(WIFI), VPN_IP, 'example vpn ab'
        return self.p.run(guard, seconds)

    def test_enabling_blocks_first_and_keeps_the_owners_own_settings(self):
        guard = self.p.guard(); self.p.run(guard, 1)
        self.assertTrue(self.p.blocked()); self.assertEqual(guard.state, 'blocked')
        self.assertIn('/reload', self.p.calls); self.assertIn('/torrents/pause', self.p.calls)
        self.assertEqual(guard.store.data['originals']['proxy_host'], 'my.proxy')   # what the owner had is remembered, not lost
    def test_no_vpn_stays_blocked_and_says_what_to_do(self):
        guard = self.p.guard(); self.p.run(guard, 30)
        self.assertEqual(guard.state, 'blocked'); self.assertTrue(self.p.blocked())
        self.assertTrue(any('Connect your VPN to continue' in text for text in self.p.shown))
        self.assertNotIn('/torrents/resume', self.p.calls)
    def test_vpn_connected_after_a_home_address_was_learned_lifts_the_block_after_two_checks(self):
        guard = self.p.guard(); self.learned(guard)
        self.assertEqual(self.connect(guard, 3), 'blocked')   # one check is not enough
        self.assertEqual(self.connect(guard, 12), 'verified')
        self.assertFalse(self.p.blocked()); self.assertEqual(self.p.settings['proxy_host'], 'my.proxy'); self.assertEqual(self.p.settings['proxy_force'], 'false')
        self.assertEqual((self.p.settings['listen_autodetect_ip'], self.p.settings['listen_interfaces'], self.p.settings['outgoing_interfaces']), ('false', '10.2.0.2', '10.2.0.2'))   # pinned to the tunnel's own address
        self.assertIn('/torrents/resume', self.p.calls); self.assertEqual(self.p.published[-1][0], 'verified')
    def test_a_tunnel_that_does_not_change_the_address_is_localdevvpn_or_a_dead_vpn(self):
        guard = self.p.guard(); self.learned(guard)
        self.p.table = with_tunnel(WIFI, 'utun5', '10.7.0.1')   # a helper tunnel; the public address is still home
        self.assertEqual(self.p.run(guard, 40), 'blocked'); self.assertEqual(guard.reason, 'same_as_home'); self.assertTrue(self.p.blocked())
    def test_vpn_on_a_network_never_seen_before_is_verified_without_learning_anything(self):
        # the owner: "anything without a vpn": no list of home networks is needed when the physical link can be asked directly
        self.p.table, self.p.exit_ip, self.p.direct_ip = with_tunnel(CELL), VPN_IP, '192.0.2.99'
        guard = self.p.guard(); self.assertEqual(self.p.run(guard, 12), 'verified'); self.assertFalse(self.p.blocked())
    def test_a_helper_tunnel_on_a_never_seen_network_is_not_a_vpn(self):
        self.p.table, self.p.exit_ip, self.p.direct_ip = with_tunnel(WIFI, 'utun5', '10.7.0.1'), '192.0.2.99', '192.0.2.99'   # LocalDevVPN: nothing changes the address
        guard = self.p.guard(); self.assertEqual(self.p.run(guard, 40), 'blocked'); self.assertEqual(guard.reason, 'same_as_direct'); self.assertTrue(self.p.blocked())
    def test_a_vpn_that_is_on_but_not_carrying_the_traffic_is_blocked_on_any_network(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard); self.assertEqual(guard.state, 'verified')
        self.p.exit_ip = HOME_IP; self.p.direct_ip = HOME_IP; self.p.run(guard, g.PROBE_VERIFIED + 2)   # the tunnel stays but traffic leaves directly
        self.assertEqual(guard.state, 'blocked'); self.assertTrue(self.p.blocked())
    def test_no_network_at_all_or_no_tunnel_on_a_new_network_is_blocked(self):
        self.p.table, self.p.exit_ip, self.p.direct_ip = CELL, '192.0.2.99', '192.0.2.99'
        guard = self.p.guard(); self.assertEqual(self.p.run(guard, 30), 'blocked'); self.assertEqual(guard.reason, 'no_tunnel')
    def test_a_closed_physical_path_is_not_comparable_and_falls_back_to_the_other_signals(self):
        self.p.direct_works = False   # a VPN kill switch that also closes the direct path
        self.p.table, self.p.exit_ip = with_tunnel(WIFI), VPN_IP
        guard = self.p.guard(); self.assertEqual(self.p.run(guard, 40), 'blocked'); self.assertEqual(guard.reason, 'no_home')   # never a pass by itself
        self.p.expected = ['example vpn']; self.p.org = 'AS1 Example VPN AB'
        self.assertEqual(self.p.run(guard, 12), 'verified')
    def test_no_home_address_known_and_no_network_named_and_nothing_to_compare_stays_blocked(self):
        self.p.table, self.p.exit_ip, self.p.direct_works = with_tunnel(WIFI), VPN_IP, False   # the VPN was already on at the first start
        guard = self.p.guard(); self.assertEqual(self.p.run(guard, 40), 'blocked'); self.assertEqual(guard.reason, 'no_home')
    def test_unexpected_vpn_failure_blocks_at_the_next_look(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.table = WIFI; self.p.exit_ip = HOME_IP   # the tunnel is gone
        self.p.run(guard, 1.0)
        self.assertEqual(guard.state, 'blocked'); self.assertTrue(self.p.blocked()); self.assertEqual(guard.reason, 'no_tunnel')
    def test_while_verified_it_looks_every_ten_seconds_with_one_service_and_blocks_at_the_first_failed_look(self):
        urls = []
        guard = self.p.guard(('https://a.example/x', 'https://b.example/y')); self.learned(guard)
        self.p.table, self.p.exit_ip, self.p.org = with_tunnel(WIFI), VPN_IP, 'example vpn ab'; self.p.run(guard, 12); self.assertEqual(guard.state, 'verified')
        asked = []; original = guard.get; guard.get = lambda url, timeout: asked.append(url) or original(url, timeout)
        self.p.run(guard, g.PROBE_VERIFIED * 3 + 1); self.assertEqual(set(asked), {'https://a.example/x'}); self.assertEqual(len(asked), 3)
        self.p.answering = False; self.p.run(guard, g.PROBE_VERIFIED + 1); self.assertEqual(guard.state, 'blocked')
    def test_a_tunnel_that_stays_but_stops_answering_is_blocked_at_the_next_check(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.answering = False; self.p.run(guard, g.PROBE_VERIFIED + 2)
        self.assertEqual(guard.state, 'blocked'); self.assertEqual(guard.reason, 'no_answer'); self.assertTrue(self.p.blocked())
    def test_deliberate_disconnect_and_reconnect_need_a_fresh_verification(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.table, self.p.exit_ip = WIFI, HOME_IP; self.p.run(guard, 2); self.assertEqual(guard.state, 'blocked')
        self.assertEqual(self.connect(guard, 3), 'blocked'); self.assertEqual(self.connect(guard, 12), 'verified')
    def test_wifi_to_cellular_is_a_change_and_blocks_until_verified_again(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard); self.assertEqual(guard.state, 'verified')
        self.p.table = with_tunnel(CELL, 'utun4', '10.2.0.2'); self.p.run(guard, 1)
        self.assertEqual(guard.state, 'blocked'); self.assertTrue(self.p.blocked())
        self.assertEqual(self.p.run(guard, 12), 'verified')   # same VPN exit over the new link
    def test_a_replacement_vpn_is_a_change_and_is_checked_afresh(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.table = with_tunnel(WIFI, 'utun6', '10.9.0.2'); self.p.exit_ip = VPN2_IP; self.p.run(guard, 1)
        self.assertEqual(guard.state, 'blocked')
        self.assertEqual(self.p.run(guard, 12), 'verified')
        self.assertEqual(self.p.settings['listen_interfaces'], '10.9.0.2')   # re-pinned to the replacement's address, not the old one
        self.p.exit_ip = HOME_IP; self.p.run(guard, g.PROBE_VERIFIED + 2)   # the replacement leaks the home address
        self.assertEqual(guard.state, 'blocked'); self.assertEqual(guard.reason, 'same_as_home')
    def test_restart_with_saved_state_blocks_first_and_restores_the_owners_settings_when_turned_off(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.table, self.p.exit_ip = WIFI, HOME_IP; self.p.run(guard, 2)   # failure, then Kodi is killed while blocked
        again = self.p.guard(); self.assertEqual(again.store.data['originals']['proxy_host'], 'my.proxy')   # remembered across the restart
        self.p.settings.update(g.TRAP); self.p.run(again, 1); self.assertTrue(self.p.blocked())
        self.p.on = False; self.p.run(again, 1)
        self.assertEqual(self.p.settings['proxy_host'], 'my.proxy'); self.assertEqual(self.p.settings['proxy_enabled'], 'false'); self.assertEqual(again.state, 'off')
        self.assertEqual((self.p.settings['listen_autodetect_ip'], self.p.settings['listen_interfaces']), ('true', ''))
        self.assertEqual(self.p.published[-1][0], '')
    def test_turning_the_feature_off_also_undoes_the_pin(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard); self.assertEqual(self.p.settings['listen_interfaces'], '10.2.0.2')
        self.p.on = False; self.p.run(guard, 2)
        self.assertEqual((self.p.settings['listen_autodetect_ip'], self.p.settings['listen_interfaces'], self.p.settings['outgoing_interfaces']), ('true', '', ''))
    def test_a_failure_leaves_the_pin_on_a_dead_address_which_is_closed_by_itself_and_by_the_block(self):
        guard = self.p.guard(); self.learned(guard); self.connect(guard)
        self.p.table = WIFI; self.p.run(guard, 2)
        self.assertTrue(self.p.blocked()); self.assertEqual(self.p.settings['listen_interfaces'], '10.2.0.2')
    def test_turning_the_feature_off_never_leaves_the_trap_behind(self):
        guard = self.p.guard(); self.p.run(guard, 2); self.assertTrue(self.p.blocked())
        self.p.on = False; self.p.run(guard, 2)
        self.assertFalse(self.p.blocked()); self.assertIn('/torrents/resume', self.p.calls)
    def test_the_engine_restarting_while_blocked_gets_the_block_again(self):
        guard = self.p.guard(); self.p.run(guard, 2)
        self.p.settings.update({k: self.p.settings['proxy_host'] if False else v for k, v in {'proxy_enabled': 'false', 'proxy_force': 'false'}.items()})   # the add-on reset them
        self.p.calls.clear(); self.p.run(guard, g.REASSERT_EVERY + 2)
        self.assertTrue(self.p.blocked()); self.assertIn('/reload', self.p.calls); self.assertIn('/torrents/pause', self.p.calls)
    def test_a_settled_block_does_not_reconfigure_the_engine_again_and_again(self):
        guard = self.p.guard(); self.p.run(guard, 2); self.p.calls.clear(); self.p.run(guard, 60)
        self.assertEqual(self.p.calls.count('/reload'), 0); self.assertGreater(self.p.calls.count('/torrents/pause'), 0)
    def test_the_home_address_is_only_ever_stored_as_a_salted_hash(self):
        guard = self.p.guard(); self.learned(guard)
        self.assertNotIn(HOME_IP, json.dumps(self.p.files)); self.assertEqual(len(guard.store.data['homes']), 1)
    def test_an_unreadable_setting_means_on(self):
        guard = self.p.guard(); guard.enabled = lambda: 1 / 0; self.p.run(guard, 2); self.assertTrue(self.p.blocked())
    def test_the_trap_is_what_libtorrent_needs_to_make_no_direct_connection(self):
        self.assertEqual((g.TRAP['proxy_enabled'], g.TRAP['proxy_type'], g.TRAP['proxy_force']), ('true', '1', 'true'))
        self.assertEqual((g.TRAP['use_proxy_download'], g.TRAP['use_proxy_tracker']), ('true', 'true'))   # peers, names and trackers
        self.assertEqual(g.TRAP['use_proxy_http'], 'false')   # the add-on's own searches stay ordinary Kodi traffic


class Setting(unittest.TestCase):
    """The keys exist in the pinned Elementum plugin (0.1.114), so the engine really reads them."""
    def test_every_trap_key_is_a_setting_of_the_add_on(self):
        text = ' '.join(a for a in [(ROOT / 'migration/elementum-ios/source-lock.json').read_text()])
        self.assertIn('0.1.114', text)
        known = {'proxy_enabled', 'proxy_type', 'proxy_host', 'proxy_port', 'proxy_login', 'proxy_password', 'use_proxy_http', 'use_proxy_tracker', 'use_proxy_download', 'proxy_force'}
        self.assertEqual(set(g.TRAP_KEYS), known)
        self.assertEqual(set(g.PIN_KEYS), {'listen_autodetect_ip', 'listen_interfaces', 'outgoing_interfaces'})   # also settings of the add-on (settings.xml of 0.1.114)
        self.assertEqual(g.pin_for({'tunnels': [('utun4', '10.2.0.2'), ('utun5', '10.7.0.1')], 'link': 'wifi'})['listen_interfaces'], '10.2.0.2,10.7.0.1')


class EntryPoints(unittest.TestCase):
    """Every way into the torrent engine finds the door shut: the engine itself is blocked (settings + paused session), and our own Download / episode entry says why."""
    def test_the_download_entry_does_not_touch_the_engine_while_blocked(self):
        import elementum_download as ed
        touched = []
        class Opener:
            def open(self, url, timeout=0):
                touched.append(url)
                raise AssertionError('the engine must not be contacted')
        def blocked():
            raise ed.Canceled('Connect your VPN to continue')
        with self.assertRaises(ed.Canceled):
            ed.follow('plugin://plugin.video.elementum/movie/1/download', opener=Opener(), gate=blocked)
        self.assertEqual(touched, [])
    def test_allowed_goes_through_and_outside_kodi_the_gate_is_a_no_op(self):
        import elementum_download as ed
        seen = []
        class Response:
            def read(self): return b''
            def close(self): pass
        class Opener:
            def open(self, url, timeout=0):
                seen.append(url); return Response()
        ed.follow('plugin://plugin.video.elementum/movie/1/download', opener=Opener(), gate=lambda: None)
        self.assertEqual(len(seen), 1)
        self.assertIsNone(ed._vpn_gate())   # no Kodi modules on this computer
    def test_the_cloud_route_is_not_gated_because_it_makes_no_torrent_connection(self):
        import elementum_download as ed
        calls = []
        ed.follow('plugin://plugin.video.elementum/movie/1/download', opener=object(), route=lambda url: calls.append(url) or True, gate=lambda: calls.append('gate'))
        self.assertEqual(len(calls), 1)   # consumed by the debrid route: the gate never ran
    def test_the_service_runs_the_guard_early_and_the_setting_exists(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('vpn_guard.Guard(', service); self.assertLess(service.index('vpn_guard_loop'), service.index('def stage(value)'))
        settings = (ROOT / 'migration/bundled-bootstrap/resources/settings.xml').read_text()
        for key in ('require_vpn', 'vpn_expected', 'vpn_echo'):
            self.assertIn('<setting id="%s"' % key, settings)
        self.assertIn('<default>false</default>', settings[settings.index('id="require_vpn"'):settings.index('id="vpn_expected"')])   # off until the owner turns it on


if __name__ == '__main__':
    unittest.main()
