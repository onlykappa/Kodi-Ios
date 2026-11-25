"""The controls' "Ends at" (owner, 2026-11-24): tap the time left to see when the video ends; it must follow seeking, pausing, skipping 10 s and a speed change, live. Kodi's own
Player.FinishTime covers everything but a drag in progress; ends_at.py covers the drag. The service's loop is run here on a virtual clock."""
import datetime, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import ends_at as ea


class Rules(unittest.TestCase):
    def test_clock_labels_and_the_phones_own_time_format(self):
        self.assertEqual((ea.clock_seconds('1:02:03'), ea.clock_seconds('12:34'), ea.clock_seconds('45'), ea.clock_seconds(''), ea.clock_seconds('x')), (3723, 754, 45, None, None))
        self.assertEqual((ea.pattern_of('%I:%M:%S %p'), ea.pattern_of('%H:%M:%S'), ea.pattern_of('')), ('%I:%M %p', '%H:%M', '%H:%M'))
    def test_the_end_time_is_now_plus_what_is_left_at_the_speed_it_plays(self):
        now = datetime.datetime(2026, 11, 24, 21, 0, 0)
        self.assertEqual(ea.ends_at(now, 7200, 3600, 1.0, '%I:%M %p'), '10:00 PM')             # an hour left from nine: no leading zero on a 12-hour clock
        self.assertEqual(ea.ends_at(now, 7200, 3600, 1.0, '%H:%M'), '22:00')
        self.assertEqual(ea.ends_at(now, 7200, 3600, 2.0, '%H:%M'), '21:30')                   # twice as fast: half the time
        self.assertEqual(ea.ends_at(now, 7200, 0, 1.0, '%H:%M'), '23:00')
        self.assertEqual(ea.ends_at(now, 7200, 9000, 1.0, '%H:%M'), '21:00')                   # past the end: now
        self.assertIsNone(ea.ends_at(now, 0, 10)); self.assertIsNone(ea.ends_at(now, 7200, None))
        self.assertEqual(ea.ends_at(datetime.datetime(2026, 11, 24, 9, 5), 3600, 1800, 1.0, '%I:%M %p'), '9:35 AM')


class Loop(unittest.TestCase):
    def drive(self, plan, steps, tempo_value=1.0):
        """plan(step) -> dict(playing, seeking, label, total); the clock moves by the loop's own waits."""
        clock = [datetime.datetime(2026, 11, 24, 21, 0, 0)]; step = [0]; written = []; waits = []
        def wait(sec):
            waits.append(sec); clock[0] += datetime.timedelta(seconds=sec); step[0] += 1; return step[0] >= steps
        read = lambda key: plan(step[0]).get(key)
        ea.run(lambda: read('playing') is not False, lambda: bool(read('seeking')), lambda: read('label'), lambda: read('total') or 7200, lambda: tempo_value, lambda: '%H:%M:%S', written.append, wait, now=lambda: clock[0])
        return written, waits
    def test_it_writes_nothing_until_a_finger_is_on_the_bar_and_polls_slowly_meanwhile(self):
        written, waits = self.drive(lambda step: {'seeking': False}, 6)
        self.assertEqual(written, []); self.assertEqual(set(waits), {ea.IDLE})
    def test_it_follows_the_finger_to_the_second_and_clears_when_it_lifts(self):
        def plan(step):
            if step < 2: return {'seeking': False}
            if step < 5: return {'seeking': True, 'label': '1:00:00'}            # an hour left
            if step < 8: return {'seeking': True, 'label': '1:30:00'}            # dragged on: 30 minutes left
            return {'seeking': False}
        written, waits = self.drive(plan, 11)
        self.assertEqual(written[0][:2], '22'); self.assertTrue(any(w.startswith('21:') for w in written))
        self.assertEqual(written[-1], '')                                         # the finger lifted: cleared, Kodi's own value takes over
        self.assertIn(ea.FAST, waits)
    def test_the_end_time_moves_on_with_the_clock_while_the_finger_rests(self):
        written, waits = self.drive(lambda step: {'seeking': True, 'label': '1:00:00'}, 800)   # a minute and a bit of resting at 0.1 s a tick
        self.assertGreaterEqual(len(set(written)), 2)                             # an hour left from 21:00 is 22:00, then 22:01 as the clock moves
        self.assertEqual(written[0], '22:00')
    def test_a_speed_change_is_taken_into_account(self):
        written, _ = self.drive(lambda step: {'seeking': True, 'label': '1:00:00'}, 3, tempo_value=2.0)
        self.assertEqual(written[0], '21:30')
    def test_nothing_is_written_for_a_label_it_cannot_read_and_it_never_raises(self):
        written, _ = self.drive(lambda step: {'seeking': True, 'label': ''}, 4)
        self.assertEqual(written, [])
        def bad(step): raise RuntimeError('boom')
        clock = [datetime.datetime(2026, 11, 24, 21, 0, 0)]; step = [0]
        def wait(sec): step[0] += 1; return step[0] > 3
        ea.run(bad, bad, bad, bad, bad, lambda: '%H:%M:%S', lambda t: None, wait, now=lambda: clock[0])


class Wiring(unittest.TestCase):
    def test_the_service_runs_it_and_the_controls_read_it(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('ends_at.run(', service); self.assertIn('ends_at.PROPERTY', service)
        import player_osd
        self.assertIn('KodiIOS.EndsAt', player_osd.window()); self.assertEqual(ea.PROPERTY, 'KodiIOS.EndsAt')


if __name__ == '__main__':
    unittest.main()
