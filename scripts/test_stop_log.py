"""Roadmap 1G.6: the long-session stop reader, built on lines written by the real airplay_diagnostics code."""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import stop_log as sl

BASE = datetime.datetime(2026, 11, 12, 20, 0, 0)


def line(seconds, record):
    when = (BASE + datetime.timedelta(seconds=seconds)).strftime('%Y-%m-%d %H:%M:%S.000')
    return '%s T:1 INFO <general>: Kodi iOS diagnostic %s' % (when, json.dumps(dict(component='airplay', **record), sort_keys=True, separators=(',', ':')))


def progress(seconds, position, status=206, errors=0, retries=0, read_error='', generation=7):
    return line(seconds, {'event': 'playback_progress', 'player': {'generation': generation, 'active': True, 'state': 1, 'position': position, 'duration': 7200},
                          'source': {'last_status': status, 'http_errors': errors, 'http_retries': retries, 'read_error': read_error}})


def stop(seconds, reason, code=0, generation=7):
    row = {'player': {'generation': generation, 'stop_reason': code, 'error_domain': 'CoreMediaErrorDomain', 'error_code': -12889}}
    return line(seconds, {'event': 'unexpected_stop', 'reason': reason, 'generation': generation, 'recent': [row]})


class Timeline(unittest.TestCase):
    def session(self, seconds, **last):
        return [progress(t, t, **(last if t >= seconds - 120 else {})) for t in range(0, seconds + 1, 30)]

    def test_a_source_rejection_near_the_hour_is_named_as_an_expiry(self):
        lines = self.session(3600, status=403, errors=3, retries=3) + [stop(3606, 'unexpected_player_stop')]
        r = sl.analyze(lines)
        self.assertEqual((r['session_s'], r['last_status']), (3600, 403))
        self.assertIn('answered 403 near the one-hour mark', r['verdict'])

    def test_a_rejection_at_another_time_is_not_blamed_on_the_hour(self):
        r = sl.analyze(self.session(900, status=401) + [stop(905, 'player_failed')])
        self.assertIn('rejected token or link', r['verdict'])
        self.assertNotIn('one-hour', r['verdict'])

    def test_failing_reads_before_the_stop_point_at_the_network(self):
        lines = [progress(t, t, errors=t // 30, retries=t // 30) for t in range(0, 1201, 30)] + [stop(1210, 'buffering_without_progress')]
        self.assertIn('the source was failing before the stop', sl.analyze(lines)['verdict'])

    def test_healthy_source_at_one_hour_points_at_the_receiver(self):
        r = sl.analyze(self.session(3600) + [stop(3605, 'receiver_route_ended')])
        self.assertIn('about an hour, with healthy source reads: look at the receiver side', r['verdict'])
        self.assertIn('-12889', r['error'])

    def test_a_long_gap_means_the_phone_was_suspended(self):
        lines = [progress(t, t) for t in range(0, 301, 30)] + [stop(1500, 'unexpected_player_stop')]
        lines.insert(len(lines) - 1, progress(1490, 1490))
        r = sl.analyze(lines)
        self.assertIn('suspended or locked', r['verdict'])
        self.assertTrue(r['gaps_s'])

    def test_a_normal_end_and_a_log_without_evidence(self):
        ended = line(1800, {'event': 'playback_ended', 'player': {'generation': 7}, 'source': {}})
        self.assertIn('ended playback normally', sl.analyze(self.session(1790) + [ended])['verdict'])
        self.assertIn('no AirPlay diagnostic lines', sl.analyze(['2026-11-12 20:00:00.000 T:1 INFO <general>: nothing'])['verdict'])
        self.assertIn('no stop in this log', sl.analyze(self.session(600))['verdict'])

    def test_only_the_latest_session_counts(self):
        old = [progress(t, t, status=403, generation=3) for t in range(0, 600, 30)]
        new = [progress(2000 + t, t, generation=9) for t in range(0, 301, 30)]
        r = sl.analyze(old + new)
        self.assertEqual(r['session_s'], 300)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'kodi.log'
            path.write_text('\n'.join(self.session(300)) + '\n')
            self.assertEqual(sl.main([str(path)]), 0)
        self.assertEqual(sl.main([]), 2)


class RealWriter(unittest.TestCase):
    def test_the_line_the_service_writes_is_what_the_reader_parses(self):
        import airplay_diagnostics as ad
        import diagnostics
        out = []
        sample = {'player': {'generation': 5, 'active': True, 'state': 1, 'position': 12.5, 'duration': 600},
                  'network': {'phase': 'playing'}, 'source': {'last_status': 206, 'http_errors': 0}}
        diagnostics.event(lambda text: out.append('2026-11-12 20:00:00.000 T:1 INFO <general>: ' + text), 'airplay', 'playback_progress', **sample)
        rows = sl.events(out)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]['source']['last_status'], 206)
        self.assertEqual(rows[0][1]['player']['position'], 12.5)


if __name__ == '__main__':
    unittest.main()
