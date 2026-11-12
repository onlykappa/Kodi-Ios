"""DEC-039 measurement build: the AI Upscale test request, the run's numbers and its failure paths (fake converter)."""
import json, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import driveupload
import upscale_measure as um


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeNative:
    upscales = True

    # A phone whose AI models take 1080p at 2x (the owner's iPhone offers only 4x: OWNER_PHONE below).
    SUPPORT = {'os26': 1, 'engine': 'ai-video', 'model': 'ready', 'video': {'supported': 1, 'fits': 1, 'scale': 2, 'factors': [2, 4]},
               'image': {'supported': 1, 'fits': 1, 'scale': 2, 'factors': [2, 4]}, 'fast': {'supported': 1, 'fits': 1, 'scale': 2, 'factors': [2]}}

    def __init__(self, clock, probe=None, model=(2,), fail=None, thermal='fair', support=None):
        self.clock, self.models, self.fail, self.thermal = clock, list(model), fail, thermal
        self.support = support or self.SUPPORT
        self.probed = probe or {'width': 1920, 'height': 1080, 'duration': 1200.0, 'fps': 23.976, 'hdr': False,
                                'codec': 'hevc', 'audio_tracks': 2, 'subtitle_tracks': 1}
        self.calls, self.started_download, self.battery = [], False, 0.9

    def probe(self, source):
        return dict(self.probed)

    def upscale_support(self, w, h, label, engine=0):
        return self.support

    def upscale_model(self, w, h, label, engine=0, start=False):
        if start:
            self.started_download = True
        return self.models.pop(0) if len(self.models) > 1 else self.models[0]

    def device_state(self):
        return {'battery': self.battery, 'charging': 1, 'thermal': self.thermal, 'thermal_id': 1, 'low_power': 0}

    def convert_to(self, source, sink, keep_going, progress, upscale=None):
        self.calls.append(upscale)
        if self.fail:
            raise RuntimeError(self.fail)
        for unit in range(40):   # 40 units of 30 s = 20 minutes of film; 90 s of wall time each
            if not keep_going():
                raise driveupload.Stop('Preparation paused')
            sink.write(0, '.mp4', b'x' * 1000)
            self.clock.t += 90
            self.battery -= 0.002
            progress(0, unit + 1, 40)


class Queue:
    def __init__(self, native, profile):
        self.native, self.profile = native, profile

        class Stream:
            forgotten = []

            def url(self, item_id):
                return 'http://127.0.0.1:1/' + item_id

            def forget(self, item_id):
                self.forgotten.append(item_id)
        self.stream = Stream()


class Measure(unittest.TestCase):
    def setUp(self):
        self.profile = tempfile.mkdtemp()
        self.clock = Clock()
        self.lines, self.notes = [], []

    def run_req(self, native, **req):
        req = dict({'id': 'abc', 'name': 'Naruto S01E03 1080p.mp4', 'size': '4K UHD', 'engines': ['auto'], 'minutes': 0}, **req)
        return um.run(Queue(native, self.profile), req, self.lines.append, lambda *a: self.notes.append(a),
                      clock=self.clock, sleep=self.clock.sleep)

    def test_whole_video_numbers(self):
        native = FakeNative(self.clock)
        result = self.run_req(native)
        run = result['runs'][0]
        self.assertEqual(native.calls, [(3840, 2160, 2, 0)])     # auto: the video model, which fits
        self.assertEqual(run['size'], '3840x2160')
        self.assertEqual(run['film_seconds'], 1200.0)
        self.assertEqual(run['wall_seconds'], 3600.0)
        self.assertEqual(run['minutes_per_minute'], 3.0)
        self.assertAlmostEqual(run['fps'], 7.99, places=2)
        self.assertEqual(run['bytes'], 40000)
        self.assertEqual(run['estimated_bytes'], 40000)
        self.assertEqual(run['battery_used'], 0.08)
        self.assertEqual(run['thermal_peak'], 'fair')
        self.assertFalse(run['partial'])
        self.assertTrue(any('RESULT' in line for line in self.lines))
        self.assertTrue(any('of 20.0 min of video' in line for line in self.lines))   # one line a minute
        self.assertEqual(self.notes[0][1], 'AI Upscale test finished')
        saved = json.loads(Path(self.profile, 'addon_data/service.kodi.ios.bootstrap', um.RESULTS).read_text())
        self.assertEqual(saved['runs'][0]['engine'], 'auto')

    def test_first_minutes_only_estimates_the_whole(self):
        native = FakeNative(self.clock)
        run = self.run_req(native, minutes=5)['runs'][0]
        self.assertTrue(run['partial'])
        self.assertEqual(run['film_seconds'], 300.0)
        self.assertEqual(run['estimated_bytes'], 40000)    # 10 units of 40 counted, scaled to the whole
        self.assertNotIn('error', run)

    def test_compare_runs_each_engine_with_its_number(self):
        native = FakeNative(self.clock)
        result = self.run_req(native, engines=['ai-video', 'ai-image', 'ai-fast', 'lanczos'], minutes=1)
        self.assertEqual([c[2] for c in native.calls], [2, 3, 4, 1])
        self.assertEqual([r['engine'] for r in result['runs']], ['ai-video', 'ai-image', 'ai-fast', 'lanczos'])

    def test_model_download_is_started_and_waited_for(self):
        native = FakeNative(self.clock, model=(0, 1, 1, 2))
        run = self.run_req(native)['runs'][0]
        self.assertTrue(native.started_download)
        self.assertNotIn('error', run)
        self.assertTrue(any('model ready' in line for line in self.lines))

    def test_model_never_arrives(self):
        native = FakeNative(self.clock, model=(0, 1))
        result = self.run_req(native)
        self.assertEqual(native.calls, [])
        self.assertIn('model not ready', result['runs'][0]['error'])
        self.assertEqual(self.notes[0][1], 'AI Upscale test stopped')

    def test_a_phone_with_only_4x_models_does_not_make_8k_frames(self):
        # Owner logs 0afdfd7b / 1ff17f50 (build 302): 1920x1080 -> 7680x4320 with the 4x image model; iOS closed Kodi.
        owner = {'os26': 1, 'engine': 'ai-image', 'model': 'ready', 'video': {'factors': [4], 'fits': 0, 'scale': 0, 'supported': 1},
                 'image': {'factors': [4], 'fits': 1, 'scale': 4, 'supported': 1},
                 'fast': {'factors': [], 'fits': 0, 'scale': 0, 'supported': 1, 'max': '1280x1280'}}
        native = FakeNative(self.clock, support=owner)
        result = self.run_req(native)
        self.assertEqual(native.calls, [])
        self.assertIn('7680x4320', result['runs'][0]['error'])
        self.assertEqual(self.notes[0][1], 'AI Upscale test stopped')
        # Compare mode: the image model is skipped, Lanczos still runs.
        native = FakeNative(self.clock, support=owner)
        result = self.run_req(native, engines=['ai-image', 'lanczos'], minutes=1)
        self.assertEqual([c[2] for c in native.calls], [1])
        # A 720p video on the same phone: the 4x image model would make 5120x2880, still larger than 4K UHD.
        import upscale_queue
        self.assertIsNone(upscale_queue.pick_engine(owner, 1280, 720, '4K UHD')[0])
        self.assertEqual(upscale_queue.pick_engine(owner, 960, 540, '4K UHD')[0], 3)
        # r49: the same phone with the low-latency model in tiles (2x) takes 1080p -> 4K UHD and 720p -> 1440p.
        tiled = dict(owner, fast={'factors': [2], 'fits': 1, 'scale': 2, 'supported': 1, 'max': '1280x1280', 'tiles': '2x1'})
        self.assertEqual(upscale_queue.pick_engine(tiled, 1920, 1080, '4K UHD'), (4, 'fast model, 2x'))
        self.assertEqual(upscale_queue.pick_engine(tiled, 1280, 720, '1440p')[0], 4)

    def test_hdr_and_4k_are_not_measured(self):
        hdr = FakeNative(self.clock, probe={'width': 1920, 'height': 1080, 'duration': 60, 'hdr': True})
        self.assertIn('HDR', self.run_req(hdr)['error'])
        uhd = FakeNative(self.clock, probe={'width': 3840, 'height': 2160, 'duration': 60, 'hdr': False})
        self.assertIn('already', self.run_req(uhd)['error'])
        self.assertEqual(hdr.calls + uhd.calls, [])

    def test_drive_read_ahead_is_let_go(self):
        native = FakeNative(self.clock, fail='boom')
        q = Queue(native, self.profile)
        um.run(q, {'id': 'abc', 'engines': ['auto']}, self.lines.append, clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(q.stream.forgotten[-1], 'abc')

    def test_converter_failure_is_reported(self):
        native = FakeNative(self.clock, fail='video conversion: AI upscaling is not available on this device')
        run = self.run_req(native)['runs'][0]
        self.assertIn('not available', run['error'])

    def test_old_framework_is_refused(self):
        native = FakeNative(self.clock)
        native.upscales = False
        with self.assertRaises(RuntimeError):
            self.run_req(native)


class Request(unittest.TestCase):
    def test_request_once(self):
        profile = tempfile.mkdtemp()
        self.assertIsNone(um.pending(profile))
        um.request(profile, {'id': 'x', 'name': 'a'}, '4K UHD', ['auto', 'bogus'], 5, now=lambda: 7)
        self.assertEqual(um.pending(profile), {'id': 'x', 'name': 'a', 'size': '4K UHD', 'engines': ['auto'], 'minutes': 5.0, 'requested': 7})
        um.clear(profile)
        self.assertIsNone(um.pending(profile))
        with self.assertRaises(ValueError):
            um.request(profile, {'id': 'x'}, '8K')

    def test_candidates_are_prepared_sdr_below_4k(self):
        state = {'jobs': {
            'a': {'status': 'done', 'completed': 2, 'prepared_id': 'A', 'source': {'id': 'a0', 'name': 'Ep 1'}, 'probe': {'width': 1920, 'height': 1080, 'duration': 1400}},
            'b': {'status': 'done', 'completed': 3, 'source': {'id': 'b', 'name': 'Movie 4K'}, 'probe': {'width': 3840, 'height': 2160}},
            'c': {'status': 'done', 'completed': 4, 'source': {'id': 'c', 'name': 'HDR'}, 'probe': {'width': 1920, 'height': 1080, 'hdr': True}},
            'd': {'status': 'waiting', 'source': {'id': 'd', 'name': 'Not yet'}, 'probe': {'width': 1280, 'height': 720}},
            'e': {'status': 'done', 'completed': 5, 'source': {'id': 'e', 'name': 'Ep 2'}, 'probe': {'width': 1280, 'height': 720, 'duration': 1300}}}}
        found = um.candidates(state)
        self.assertEqual([(f['id'], f['name']) for f in found], [('e', 'Ep 2'), ('A', 'Ep 1')])


if __name__ == '__main__':
    unittest.main()
