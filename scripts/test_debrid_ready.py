"""F1 (PR #24 roadmap): a download that only needs a re-package is made ready while it copies from AllDebrid to Drive.
Host simulation with test_drive_prepare's Drive stand-in and a fake converter; the phone is never proven here."""
import io, json, sys, tempfile, threading, types, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BOOT / 'resources/lib'))
sys.path.insert(0, str(ROOT / 'scripts'))
import debrid_drive, debrid_ready, drive_stream, driveupload, prepare_downloads as prep  # noqa: E402
from test_drive_prepare import Drive  # noqa: E402

SIZE = 1000


class Native:
    outputs = True

    def __init__(self, copy_video=True, codec='h264'):
        self.copy_video, self.codec, self.converted, self.bad, self.error = copy_video, codec, [], False, None

    def probe(self, url):
        return dict(ready='temp-' in url, width=1920, height=1080, hdr=False, duration=1400, codec=self.codec,
                    copy_video=self.copy_video)

    def convert_to(self, source, sink, keep_going, progress, paused=None, waiting=None, resume=None):
        self.converted.append(source)
        if self.error:
            raise self.error
        sink.write(0, '.mp4', b'ready movie')
        progress(2, 700, 1400)
        progress(2, 1400, 1400)

    def verify(self, source, target):
        if self.bad:
            raise RuntimeError('Output validation failed')


class Stream:
    def __init__(self):
        self.external, self.wide, self.forgotten = {}, [], []

    def add_external(self, key, with_link):
        self.external[key] = with_link
        return self.url(key)

    def url(self, key):
        return 'http://127.0.0.1:1/%s/source' % key

    def widen(self, key):
        self.wide.append(key)

    def unwide(self, key):
        pass

    def forget(self, key):
        self.forgotten.append(key)


class Ready(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.drive, self.native, self.stream = Drive(), Native(), Stream()
        self.layout = {'fast_open': False, 'layout_reason': 'not_mp4'}
        self.q = types.SimpleNamespace(native=self.native, stream=self.stream, drive=self.drive,
                                       layout_probe=lambda url, size, going: dict(self.layout))
        self.progress, self.logs = [], []

    def copy(self, going=lambda: True):
        return debrid_ready.copy(self.q, self.tmp.name, lambda action: action('https://debrid/file'), 'Naruto S01E05.mkv', SIZE,
                                 'show-folder', going, lambda sent, total: self.progress.append((sent, total)), 'hash:ep5',
                                 log=self.logs.append, clock=iter(range(0, 1000, 2)).__next__)

    def test_a_repackage_lands_on_drive_ready_in_the_shows_folder(self):
        result = self.copy()
        f = self.drive.files[result['id']]
        self.assertEqual((result['name'], f['name'], f['parents']), ('Naruto S01E05.mp4', 'Naruto S01E05.mp4', ['show-folder']))
        self.assertEqual(f['data'], b'ready movie')
        self.assertTrue(prep.ready(self.drive.meta(result['id'])))             # the preparation marker: no "Up next" job
        self.assertEqual(self.progress[-1], (SIZE, SIZE))
        self.assertEqual(len(self.native.converted), 1)
        self.assertEqual(len(self.stream.wide), 1)                              # read with the wide read-ahead
        self.assertIn('made ready while it copies', self.logs[0])
        self.assertEqual([k for k in self.drive.files if k not in ('source', result['id'])], [])   # nothing left in staging

    def test_a_real_conversion_or_a_file_that_already_opens_fast_is_copied_plainly(self):
        self.native.copy_video = False
        self.assertIsNone(self.copy())
        self.native.copy_video = True
        self.layout = {'fast_open': True}
        self.assertIsNone(self.copy())
        self.native.codec = 'av1'
        self.layout = {'fast_open': False}
        self.assertIsNone(self.copy())
        self.assertEqual(self.native.converted, [])
        self.assertEqual(list(self.drive.files), ['source'])

    def test_a_converter_problem_falls_back_to_the_plain_copy(self):
        self.native.error = RuntimeError('MP4 packet: Invalid argument')
        self.assertIsNone(self.copy())
        self.assertIn('copying it as it is', self.logs[-1])
        self.assertEqual(list(self.drive.files), ['source'])

    def test_network_trouble_is_raised_for_the_copiers_wait_and_retry(self):
        self.native.error = RuntimeError('Source read: Input/output error')
        with self.assertRaises(RuntimeError):
            self.copy()

    def test_an_unverified_file_is_never_put_in_place(self):
        self.native.bad = True
        self.assertIsNone(self.copy())
        self.assertEqual(list(self.drive.files), ['source'])                    # the staged file was discarded
        self.assertFalse(any('show-folder' in (f.get('parents') or []) for f in self.drive.files.values()))

    def test_a_cancel_stops_it(self):
        def stopped(*a, **k):
            raise driveupload.Stop('Download paused')
        self.native.convert_to = stopped
        with self.assertRaises(driveupload.Stop):
            self.copy()

    def test_without_the_converter_or_stream_it_is_a_plain_copy(self):
        self.q.stream = types.SimpleNamespace(url=lambda k: '', forget=lambda k: None)   # an older stream: no add_external
        self.assertIsNone(self.copy())
        self.q.native = types.SimpleNamespace(outputs=False)
        self.assertIsNone(self.copy())

    def test_at_most_three_at_once(self):
        self.assertEqual(debrid_ready.LANES, 3)
        inside, peak, gate = [0], [0], threading.Event()

        def slow(source, sink, keep_going, progress, paused=None, waiting=None, resume=None):
            inside[0] += 1
            peak[0] = max(peak[0], inside[0])
            gate.wait(1)
            inside[0] -= 1
            raise RuntimeError('MP4 packet: Invalid argument')
        self.native.convert_to = slow
        threads = [threading.Thread(target=self.copy) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(15)
        self.assertEqual(peak[0], 3)


class OutsideLink(unittest.TestCase):
    """DriveStream reads a file from another server through its block cache (no Drive token on that request)."""
    def test_blocks_come_from_the_link_and_an_expired_link_is_renewed(self):
        data = bytes(range(256)) * 40
        seen = []

        def open_url(request, timeout):
            seen.append((request.full_url, dict(request.header_items())))
            if request.full_url.endswith('/old'):
                raise urllib.error.HTTPError(request.full_url, 403, 'expired', {}, io.BytesIO())
            start, end = [int(x) for x in request.get_header('Range')[6:].split('-')]
            end = min(end, len(data) - 1)
            r = io.BytesIO(data[start:end + 1])
            r.status = 206
            r.headers = {'Content-Range': 'bytes %d-%d/%d' % (start, end, len(data))}
            return r
        link = ['https://debrid/old']

        def with_link(action):
            try:
                return action(link[0])
            except urllib.error.HTTPError:
                link[0] = 'https://debrid/new'
                return action(link[0])
        s = drive_stream.DriveStream(lambda: 'drive-token', open_url=open_url, block_size=4096)
        self.addCleanup(s.close)
        s.add_external('debrid-x', with_link)
        body, total = s._fetch('debrid-x', 4096, 8191)
        self.assertEqual((body, total), (data[4096:8192], len(data)))
        self.assertEqual([u for u, _ in seen], ['https://debrid/old', 'https://debrid/new'])
        self.assertFalse(any('Authorization' in h for _, h in seen))            # the Drive token never goes to another host
        s.forget('debrid-x')
        self.assertNotIn('debrid-x', s.external)


class Wiring(unittest.TestCase):
    def test_the_copier_tries_it_once_per_fresh_file_and_the_service_passes_it(self):
        src = (BOOT / 'resources/lib/debrid_drive.py').read_text()
        self.assertIn("if ready_copy is not None and not entry.get('plain') and not session.get('url'):", src)
        self.assertIn("attempt_ready = entry['ready_tries'] <= READY_TRIES", src)
        self.assertEqual(debrid_drive.READY_TRIES, 3)
        service = (BOOT / 'service.py').read_text()
        self.assertIn("ready_copy=ready_copy,", service)
        self.assertIn("not addon.getSettingBool('prepare_while_copying')", service)
        settings = (BOOT / 'resources/settings.xml').read_text()
        self.assertIn('<setting id="prepare_while_copying" type="boolean" label="32030"><level>0</level><default>true</default>', settings)


if __name__ == '__main__':
    unittest.main()
