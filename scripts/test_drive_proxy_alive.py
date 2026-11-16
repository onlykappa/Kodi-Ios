"""ISSUE-355 (owner log 46025e07, build 545): the Drive proxy that plays Library copies stopped answering after the app had been in the
background (iOS closes listening sockets) and nothing started it again, so every Drive copy failed with "Could not connect to server"."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import drive_proxy  # noqa: E402


class Fake:
    def __init__(self):
        self.closed = []

    def shutdown(self):
        self.closed.append('shutdown')

    def server_close(self):
        self.closed.append('close')


class Alive(unittest.TestCase):
    def test_a_running_proxy_is_healthy_and_a_stopped_one_is_not(self):
        server, port = drive_proxy.start(lambda force=False: 'token')
        try:
            self.assertTrue(drive_proxy.healthy(port))   # an unknown path answers 404: alive
        finally:
            server.shutdown()
            server.server_close()
        self.assertFalse(drive_proxy.healthy(port, timeout=0.5))

    def test_a_proxy_that_stops_answering_is_started_again_on_the_same_port(self):
        servers, ports, published, logs = [], [], [], []

        def make(port):
            ports.append(port)
            servers.append(Fake())
            return servers[-1], 4000 + len(servers)

        answers = iter([True, False])           # answers once, then stops
        waits = iter([False] * 5 + [True])      # five seconds, then Kodi closes after the restart
        drive_proxy.supervise(make, lambda seconds: next(waits), published.append, logs.append, interval=2, probe=lambda p: next(answers, True))
        self.assertEqual(ports, [0, 4001])                       # the second start asks for the first one's port
        self.assertEqual(published, [4001, None, 4002, None])    # the app is told each time, and when it stops
        self.assertEqual(servers[0].closed, ['shutdown', 'close'])
        self.assertTrue(any('stopped answering' in line for line in logs))
        self.assertEqual(sum('streaming Drive copies' in line for line in logs), 2)

    def test_a_port_that_cannot_be_taken_again_falls_back_to_any(self):
        calls = []

        def make(port):
            calls.append(port)
            if port:
                raise OSError('in use')
            return Fake(), 5000 + len(calls)

        answers = iter([False])
        waits = iter([False, False, True])
        drive_proxy.supervise(lambda p: make(p), lambda s: next(waits), lambda p: None, lambda t: None, interval=2, probe=lambda p: next(answers, True))
        self.assertEqual(calls, [0, 5001, 0])

    def test_kodi_closing_stops_it_without_a_restart(self):
        starts = []
        drive_proxy.supervise(lambda p: (starts.append(p) or (Fake(), 6000)), lambda s: True, lambda p: None, lambda t: None, probe=lambda p: True)
        self.assertEqual(starts, [0])

    def test_a_play_that_finds_the_proxy_dead_asks_for_a_restart_and_reads_the_new_port(self):
        ports = iter(['6000', '6000', '6001', '6001'])
        asked, slept = [], []
        probes = {6000: False, 6001: True}
        port = drive_proxy.live_port(lambda: next(ports), asked.append, slept.append, probe=lambda p, t: probes[p])
        self.assertEqual(port, 6001)
        self.assertEqual(asked, ['6000'])          # asked once
        self.assertTrue(slept)

    def test_a_proxy_that_never_answers_gives_none_so_the_drive_add_on_plays_the_copy(self):
        asked = []
        self.assertIsNone(drive_proxy.live_port(lambda: '6000', asked.append, lambda s: None, tries=4, probe=lambda p, t: False))
        self.assertEqual(asked, ['6000'])
        self.assertIsNone(drive_proxy.live_port(lambda: '', asked.append, lambda s: None))     # no proxy published at all
        self.assertEqual(drive_proxy.live_port(lambda: '6000', asked.append, lambda s: None, probe=lambda p, t: True), 6000)

    def test_the_nudge_restarts_it_at_once(self):
        starts, waits = [], iter([False, True, True])
        nudges = iter([True])
        drive_proxy.supervise(lambda p: (starts.append(p) or (Fake(), 7000 + len(starts))), lambda s: next(waits), lambda p: None, lambda t: None,
                              interval=999, probe=lambda p: True, nudge=lambda p: next(nudges, False))
        self.assertEqual(starts, [0, 7001])

    def test_the_library_play_checks_the_proxy_first(self):
        text = (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
        self.assertIn('live_proxy_port(xbmc,xbmcgui,xbmcvfs)', text)

    def test_the_service_uses_the_supervisor(self):
        text = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('drive_proxy.supervise(', text)


if __name__ == '__main__':
    unittest.main()
