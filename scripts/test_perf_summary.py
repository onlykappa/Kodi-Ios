"""Roadmap 3.5: one performance line a minute: list runs, opens, Drive proxy requests and seeks."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
sys.path.insert(0, str(ROOT / 'scripts'))
import open_timing
import perf_summary as ps


class Home(dict):
    def getProperty(self, key):
        return self.get(key, '')

    def setProperty(self, key, value):
        self[key] = value

    def clearProperty(self, key):
        self.pop(key, None)


class Line(unittest.TestCase):
    def test_a_quiet_minute_writes_nothing(self):
        self.assertEqual(ps.line(60, {'watch': 0, 'cached': 0, 'tmdb': 0}, [], {}), '')
        self.assertEqual(ps.line(60, {}, [], {'requests': 0, 'warm_hits': 0, 'seeks': []}), '')

    def test_a_busy_minute_is_one_line_with_every_part(self):
        text = ps.line(60.2, {'watch': 3, 'cached': 2, 'tmdb': 5}, [(5.84, 'library', 'resolve 0.3 s, open 4.2 s, picture 1.0 s')],
                       {'requests': 12, 'warm_hits': 3, 'seeks': [0.2, 0.4, 0.9]})
        self.assertEqual(text, 'Kodi iOS perf 60 s: rows watch 3 cached 2 tmdb 5 | opens 1 (5.8 s via library, resolve 0.3 s, open 4.2 s, picture 1.0 s) | '
                               'drive proxy 12 requests, 3 warm, seeks 3 (median 0.4 s, worst 0.9 s)')
        self.assertNotIn('\n', text)

    def test_parts_appear_only_when_they_have_something(self):
        self.assertEqual(ps.line(60, {'watch': 0, 'cached': 4, 'tmdb': 0}, [], {}), 'Kodi iOS perf 60 s: rows cached 4')
        self.assertEqual(ps.line(60, {}, [], {'requests': 2}), 'Kodi iOS perf 60 s: drive proxy 2 requests')


class Counters(unittest.TestCase):
    def test_bump_and_read(self):
        home = Home()
        for _ in range(3):
            ps.bump(home, 'watch')
        ps.bump(home, 'tmdb')
        self.assertEqual(ps.read(home), {'watch': 3, 'cached': 0, 'tmdb': 1})
        home['KodiIOS.Count.cached'] = 'garbage'
        self.assertEqual(ps.read(home)['cached'], 0)

    def test_watch_logs_deltas_each_minute_and_survives_errors(self):
        home, logs, ticks = Home(), [], []

        def wait(seconds):
            ticks.append(seconds)
            if len(ticks) == 1:
                ps.bump(home, 'watch')
                ps.bump(home, 'watch')
            if len(ticks) == 2:
                ps.bump(home, 'tmdb')
            return len(ticks) > 3
        clock = iter(range(0, 1000, 60))
        calls = []

        def opens():
            calls.append(1)
            if len(calls) == 3:
                raise RuntimeError('synthetic')
            return []
        ps.watch(home, opens, lambda: {}, logs.append, wait, every=60, clock=lambda: float(next(clock)))
        self.assertEqual(logs, ['Kodi iOS perf 60 s: rows watch 2', 'Kodi iOS perf 60 s: rows tmdb 1'])   # the failing minute is skipped
        self.assertEqual(ticks[0], 60)


class Sources(unittest.TestCase):
    def test_open_timing_hands_over_its_opens_once(self):
        home, lines = Home(), []
        open_timing.RECENT[:] = []
        open_timing.mark(home, 'library', now=100.0)
        open_timing.check(home, lambda: True, lines.append, now=105.8)
        taken = open_timing.take()
        self.assertEqual((len(taken), taken[0][1], taken[0][2]), (1, 'library', ''))
        self.assertAlmostEqual(taken[0][0], 5.8, places=3)
        self.assertEqual(open_timing.take(), [])

    def test_the_drive_proxy_exposes_its_stats_to_the_summary(self):
        import drive_proxy
        server, _ = drive_proxy.start(lambda force: 't')
        try:
            self.assertIs(drive_proxy.CURRENT[0], server)
            self.assertEqual(server.stats.take(), {'requests': 0, 'warm_hits': 0, 'seeks': []})
        finally:
            server.shutdown()
            server.server_close()

    def test_the_watch_plugin_and_tmdb_helper_patch_count_their_runs(self):
        plugin = (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/default.py').read_text()
        self.assertIn("'KodiIOS.Count.'+('cached' if argv[2].startswith('?action=cached&key=') else 'watch')", plugin)
        self.assertEqual(ps.PREFIX, 'KodiIOS.Count.')
        import ios_watch_dialog
        home = Home()
        import types
        fake = types.ModuleType('xbmcgui')
        fake.Window = lambda ident: home
        sys.modules['xbmcgui'] = fake
        try:
            ios_watch_dialog.count_run('tmdb')
            ios_watch_dialog.count_run('tmdb')
        finally:
            sys.modules.pop('xbmcgui', None)
        self.assertEqual(ps.read(home)['tmdb'], 2)
        build = (ROOT / 'scripts/build_import_review.py').read_text()
        self.assertIn("count_run('tmdb')", build)

    def test_the_service_starts_the_summary_thread(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('target=perf_summary.watch', service)
        self.assertIn('open_timing.take', service)


if __name__ == '__main__':
    unittest.main()
