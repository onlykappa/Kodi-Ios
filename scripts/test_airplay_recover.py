"""A cast that sits still is started again once, then the person is told (owner, 2026-11-23). The sequences are shaped like the two real logs: 72c1c0ac / 7f62ba9c
(TV waiting at 1101.4 s for minutes; the second start moved at once)."""
import json, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import airplay_recover as r
import airplay


def sample(position, **kw):
    base = {'generation': 1, 'active': 1, 'external': 1, 'rate': 1.0, 'time_control': 2, 'position': position, 'buffer_empty': 0}
    base.update(kw); return base


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


class Rules(unittest.TestCase):
    def setUp(self):
        self.clock, self.actions, self.told, self.lines = Clock(), [], [], []
        self.ok = True
        self.guard = r.Recover(lambda position: self.actions.append(position) or self.ok, self.told.append, self.lines.append, self.clock)
    def run_for(self, seconds, player, step=5.0):
        out = []
        for _ in range(int(seconds / step)):
            self.clock.t += step; out.append(self.guard.observe(player))
        return [o for o in out if o]

    def test_a_tv_that_waits_without_moving_is_started_again_once_the_stall_is_long_enough(self):
        self.assertEqual(self.run_for(r.STALL - 5, sample(1101.4)), [])
        self.assertEqual(self.run_for(10, sample(1101.4)), ['restart']); self.assertEqual(self.actions, [1101.4])   # from where the TV was
    def test_a_second_stall_after_the_restart_tells_the_person_once_and_never_loops(self):
        self.run_for(r.STALL + 5, sample(1101.4)); self.assertEqual(len(self.actions), 1)
        self.assertEqual(self.run_for(r.GRACE + 10, sample(1101.4, generation=2)), ['tell'])
        self.assertEqual(self.run_for(120, sample(1101.4, generation=2)), []); self.assertEqual(len(self.actions), 1); self.assertEqual(len(self.told), 1)
    def test_a_restart_that_works_is_left_alone_and_a_later_stall_may_be_restarted_again(self):
        self.run_for(r.STALL + 5, sample(1101.4)); pos = 0.0
        for _ in range(int(r.HEALTHY / 5) + 2):
            pos += 5; self.clock.t += 5; self.assertIsNone(self.guard.observe(sample(pos, time_control=1, generation=2)))
        self.assertEqual(self.guard.restarts, 0)
        self.assertEqual(self.run_for(r.STALL + 5, sample(pos, generation=2)), ['restart']); self.assertEqual(len(self.actions), 2)
    def test_normal_playback_pause_and_a_tv_that_is_not_connected_never_trigger(self):
        pos = 0.0
        for _ in range(40):
            pos += 5; self.clock.t += 5; self.assertIsNone(self.guard.observe(sample(pos, time_control=1)))
        self.assertEqual(self.run_for(300, sample(100.0, rate=0.0, time_control=0)), [])   # paused on the TV
        self.assertEqual(self.run_for(300, sample(50.0, external=0)), [])                  # Apple's player, no TV yet
        self.assertEqual(self.run_for(300, sample(50.0, active=0)), []); self.assertEqual(self.actions, [])
    def test_a_slow_start_that_does_get_going_is_not_restarted(self):
        self.assertEqual(self.run_for(15, sample(0.0)), [])
        for p in (1102.4, 1108.4, 1114.4): self.clock.t += 5; self.assertIsNone(self.guard.observe(sample(p, time_control=1)))
        self.assertEqual(self.actions, [])
    def test_a_stream_that_cannot_be_restarted_tells_at_once(self):
        self.ok = False
        self.assertEqual(self.run_for(r.STALL + 5, sample(1101.4)), ['tell']); self.assertEqual(len(self.told), 1)
        self.assertIn('could not be restarted', ' '.join(self.lines))
    def test_a_seek_on_the_tv_is_movement_not_a_stall(self):
        self.run_for(r.STALL - 5, sample(1101.4)); self.clock.t += 5; self.assertIsNone(self.guard.observe(sample(2000.0)))
        self.assertEqual(self.run_for(r.STALL - 5, sample(2000.0)), [])
    def test_the_log_lines_carry_seconds_and_positions_only(self):
        self.run_for(r.STALL + 5, sample(1101.4)); self.assertTrue(all('http' not in l for l in self.lines)); self.assertIn('1101.4', self.lines[0])


class Window:
    def __init__(self): self.p = {}
    def setProperty(self, k, v): self.p[k] = v
    def getProperty(self, k): return self.p.get(k, '')


class Restart(unittest.TestCase):
    class Lib:
        def __init__(self): self.calls = []
        def kodi_airplay_close(self): self.calls.append('close')
        def kodi_airplay_start_at(self, seconds): self.calls.append(('start_at', seconds))
        def kodi_airplay_play(self, source, title): self.calls.append(('play', source, title))
    def test_it_closes_moves_the_start_and_plays_the_same_stream_again(self):
        window, lib = Window(), self.Lib(); airplay.remember_play(window, 'http://127.0.0.1:9/x.mkv', 'Movie')
        self.assertTrue(airplay.restart(lib, window, 1101.4, now=5.0))
        self.assertEqual(lib.calls, ['close', ('start_at', 1101.4), ('play', b'http://127.0.0.1:9/x.mkv', b'Movie')])
    def test_with_nothing_remembered_it_does_not_guess(self):
        lib = self.Lib(); self.assertFalse(airplay.restart(lib, Window(), 10.0)); self.assertEqual(lib.calls, [])
    def test_a_failing_framework_gives_false_not_an_error(self):
        window = Window(); airplay.remember_play(window, 's', 't')
        class Bad(self.Lib):
            def kodi_airplay_close(self): raise OSError('x')
        self.assertFalse(airplay.restart(Bad(), window, 1.0))


class Wiring(unittest.TestCase):
    def test_the_cast_remembers_what_it_played_and_the_service_watches(self):
        cast = (ROOT / 'migration/bundled-bootstrap/cast.py').read_text()
        self.assertLess(cast.index('airplay.remember_play(home,source,title)'), cast.index("lib.kodi_airplay_play(source.encode('utf-8')"))
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('airplay_recover.Recover(', service); self.assertIn("kwargs={'recover':recover}", service)
        diag = (ROOT / 'migration/bundled-bootstrap/resources/lib/airplay_diagnostics.py').read_text(); self.assertIn('recover.observe(player)', diag)


if __name__ == '__main__':
    unittest.main()
