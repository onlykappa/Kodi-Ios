"""Roadmap 1G.5: the caption log reader, and that the lines it reads still exist in the Python and native sources."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import caption_log as cl


def run(*lines):
    return cl.analyze(['2026-11-12 10:00:00.000 T:1 INFO <general>: ' + line for line in lines])


class Verdicts(unittest.TestCase):
    def test_subtitles_off_when_airplay_started(self):
        r = run('Kodi iOS Play on TV: subtitles for AirPlay off', 'Kodi iOS AirPlay: compat: segment 0 converted in 5000 ms (83% of realtime) via GPU, source I/O 10 ms, 0 subtitle events, 0 frames drawn, subtitle preroll through 0.000 s')
        self.assertIn('subtitles off', r['verdict'])

    def test_burned_in_with_events_and_frames(self):
        r = run('Kodi iOS Play on TV: subtitles for AirPlay stream 2', 'AirPlay: subtitles: burning source stream 2 into the converted picture',
                'AirPlay: compat: segment 0 converted in 5000 ms (83% of realtime) via GPU, source I/O 10 ms, 14 subtitle events, 6 frames drawn, subtitle preroll through 3.000 s')
        self.assertEqual((r['burn'], r['events'], r['drawn']), (True, 14, 6))
        self.assertIn('burned into the picture (14 events, 6 frames drawn', r['verdict'])

    def test_burned_in_but_nothing_found_or_drawn(self):
        seg = 'AirPlay: compat: segment %d converted in 5000 ms (83%% of realtime) via GPU, source I/O 10 ms, %d subtitle events, %d frames drawn, subtitle preroll through 0.000 s'
        self.assertIn('no subtitle events', run('Kodi iOS Play on TV: subtitles for AirPlay stream 0', 'AirPlay: compat: burning subtitles in (source stream 0: events load as each segment is converted)', seg % (0, 0, 0))['verdict'])
        self.assertIn('no frame had a caption drawn', run('Kodi iOS Play on TV: subtitles for AirPlay stream 0', 'AirPlay: compat: burning subtitles in (source stream 0: events load as each segment is converted)', seg % (0, 9, 0))['verdict'])
        self.assertIn('could not be burned', run('Kodi iOS Play on TV: subtitles for AirPlay external file', 'AirPlay: error: subtitles not burned in: file not found')['verdict'])

    def test_webvtt_served_never_read_or_not_asked(self):
        head = ['Kodi iOS Play on TV: subtitles for AirPlay stream 0', "AirPlay: prepared: 2 text subtitle track(s) as WebVTT, Kodi's on"]
        served = run(*head, 'AirPlay: subs: stream 0 segment 1 worker result=0 elapsed_ms=420; cached', 'AirPlay: subs: stream 0 segment 2 worker result=-1 elapsed_ms=2600; retryable failure')
        self.assertIn('WebVTT captions served (1 cached, 1 failed reads, slowest 2600 ms)', served['verdict'])
        never = run(*head, 'AirPlay: subs: stream 0 segment 1 pending or failed; returning retryable 503', 'AirPlay: subs: stream 0 segment 1 worker result=-1 elapsed_ms=45000; retryable failure')
        self.assertIn('offered but never read: 1 failed reads, 1 retryable 503s', never['verdict'])
        self.assertIn('the TV asked for none', run(*head)['verdict'])

    def test_a_new_play_on_tv_starts_a_new_record(self):
        r = run('Kodi iOS Play on TV: subtitles for AirPlay stream 0', 'AirPlay: subs: stream 0 segment 1 worker result=-1 elapsed_ms=900; retryable failure',
                'Kodi iOS Play on TV: subtitles for AirPlay off')
        self.assertEqual((r['failed'], r['selected']), (0, 'off'))

    def test_no_choice_in_the_log(self):
        self.assertIn('no Play on TV', run('something else')['verdict'])

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'kodi.log'
            path.write_text('Kodi iOS Play on TV: subtitles for AirPlay off\n')
            self.assertEqual(cl.main([str(path)]), 0)
        self.assertEqual(cl.main([]), 2)


class LinesStillExist(unittest.TestCase):
    """If a source line is reworded the reader goes blind; this fails first."""

    def test_python_and_native_sources_still_write_the_lines(self):
        cast = (ROOT / 'migration/bundled-bootstrap/cast.py').read_text()
        self.assertIn("Kodi iOS Play on TV: subtitles for AirPlay %s", cast)
        self.assertIn("Kodi iOS Play on TV: TV subtitles %s", cast)
        native = (ROOT / 'migration/airplay-ios/remux/src/kr_remux.c').read_text()
        for needle in ('subtitles: burning source stream %d into the converted picture', 'compat: burning subtitles in',
                       'error: subtitles not burned in: %s', 'prepared: %d text subtitle track(s) as WebVTT%s',
                       'subs: stream %d segment %d worker result=%d elapsed_ms=%.0f; %s',
                       'subs: stream %d segment %d pending or failed; returning retryable 503', 'subs: no subtitle connection',
                       '%d subtitle events, %ld frames drawn'):
            self.assertIn(needle, native)


if __name__ == '__main__':
    unittest.main()
