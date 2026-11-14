"""ISSUE-292: actual piece timings, independent lane speeds and regular histories without fabricated progress."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'migration/bundled-bootstrap/resources/lib'), str(ROOT / 'migration/bundled-bootstrap')]
import driveupload
import slowdown
import transfer_speed as speed
import work_state
import transfers

MB = 1048576


def lane(key, rate, state='running'):
    return {'kind': 'copy', 'key': key, 'title': key, 'state': state, 'rate': rate, 'pct': 25,
            'sent': 32 * MB, 'confirmed_bytes': 32 * MB, 'total': 128 * MB, 'measured_at': 1000.0}


class Measured(unittest.TestCase):
    def test_weighted_rolling_rate_includes_first_piece(self):
        pieces = speed.Pieces()
        pieces.observe(32 * MB, 8, 1000)
        self.assertEqual(pieces.fields(1000)['rate_own'], 4 * MB)
        pieces.observe(32 * MB, 16, 1016)
        self.assertAlmostEqual(pieces.fields(1016)['rate_own'], 64 * MB / 24)
        self.assertEqual(pieces.fields(1080)['rate_own'], 0)

    def test_actual_native_copier_reports_first_and_final_piece(self):
        now = [0.0]
        measured, progress = [], []
        def report(done, total): progress.append((done, total))
        report.piece = lambda advanced, elapsed, count: measured.append((advanced, elapsed, count))
        def copier(target, headers, offset, count, total, timeout):
            now[0] += 8.0
            if offset + count == total:
                return 200, {}, json.dumps({'id': 'fixture-result', 'size': total}).encode()
            return 308, {'Range': 'bytes=0-%d' % (offset + count - 1)}, b''
        copier.max = 32 * MB; copier.streams = True
        drive = driveupload.Drive(lambda *a: 'test-access', lambda *a: None)
        driveupload.LinkMemory.clear()
        with patch.object(driveupload.time, 'monotonic', side_effect=lambda: now[0]), patch.object(slowdown.Gate, 'after'), patch.object(slowdown, 'reason', return_value=''):
            drive._native_stream(copier, 64 * MB, {'url': 'https://example.invalid/session'}, 0,
                                 lambda: None, lambda: True, report, lambda *a: None)
        self.assertEqual(measured, [(32 * MB, 8.0, 32 * MB), (32 * MB, 8.0, 32 * MB)])
        self.assertEqual(progress[-1], (64 * MB, 64 * MB))

    def test_two_lanes_never_show_aggregate_speed_as_their_own(self):
        state = {'jobs': [lane('one', 2 * MB), lane('two', 3 * MB)]}
        speed.History().sample(state, 1000)
        self.assertEqual([j['speed_mb_s'] for j in state['jobs']], [2.0, 3.0])
        self.assertEqual(state['upload']['speed_mb_s'], 5.0)
        self.assertEqual(state['jobs'][0]['eta_s'], 48.0)
        current = {'stage': 'copying', 'name': 'One', 'total': 128 * MB, 'sent': 32 * MB,
                   'rate': 99 * MB, 'rate_own': 2 * MB, 'updated': 1000}
        card = work_state._copy({'jobs': [{'title': 'One', 'status': 'copying'}], 'current': current}, 1000)
        self.assertEqual(card['rate'], 2 * MB)

    def test_one_second_samples_bounded_history_and_no_progress_invention(self):
        history = speed.History()
        for now in range(1000, 1070):
            state = history.sample({'jobs': [lane('one', 2 * MB)]}, now)
            self.assertEqual(state['jobs'][0]['sent'], 32 * MB)
        points = state['upload']['speed_history']
        self.assertEqual(len(points), 60)
        self.assertTrue(all(b[0] - a[0] == 1 for a, b in zip(points, points[1:])))
        self.assertEqual(points[-1][1], 0)  # old receipt goes quiet, never endless nonzero speed
        history.sample(state, 1069.9)
        self.assertEqual(len(state['upload']['speed_history']), 60)
        restored = speed.History(); restored.restore(state)
        state = restored.sample({'jobs': [lane('one', 2 * MB, 'paused_by_you')]}, 1070)
        self.assertEqual(state['upload']['rate'], 0)
        self.assertEqual(state['jobs'][0]['eta_s'], 0)
        state = restored.sample({'jobs': [lane('new job same slot', MB)]}, 1071)
        self.assertEqual(len(state['jobs'][0]['speed_history']), 1)

    def test_transfers_uses_published_lane_history(self):
        state = speed.History().sample({'jobs': [dict(lane('one', 2 * MB), id='copy-one',
                                                       line='Copying', step='Copying', tint='FF0A84FF')]}, 1000)
        state = speed.History().sample(state, 1001)
        props, _, _, _ = transfers.page_state({}, 1001, 'up', [], model=state)
        self.assertEqual(props['number'], '2.0')
        self.assertEqual(props['peak'], '2.0 MB/s')
        self.assertEqual(props['avg'], '2.0 MB/s')


if __name__ == '__main__': unittest.main()
