"""1A.3: real proxy ranges plus bounded, versioned MP4 fragment-index persistence."""
import hashlib
import io
import json
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import drive_index as di
import drive_proxy as dp


def movie(time=0):
    entry = struct.pack('>QQBBB', time, 32, 1, 1, 1)
    tfra = struct.pack('>I4sIIII', 24 + len(entry), b'tfra', 1 << 24, 1, 0, 1) + entry
    length = 8 + len(tfra) + 16
    index = struct.pack('>I4s', length, b'mfra') + tfra + struct.pack('>I4sII', 16, b'mfro', 0, length)
    return bytes(range(128)) + index, index


class Response(io.BytesIO):
    def __init__(self, status, data, headers):
        super().__init__(data)
        self.status, self.headers = status, headers
        self.reads = []

    def read(self, amount=-1):
        self.reads.append(amount)
        if amount < 0:
            raise AssertionError('Unbounded optional index read')
        return super().read(amount)

    def getheader(self, key, default=None):
        return self.headers.get(key, default)


class Drive:
    def __init__(self):
        self.data, self.index = movie()
        self.calls, self.responses = [], []
        self.meta_calls = 0
        self.change_after_read = False
        self.missing_checksum = False
        self.version = '1'

    def metadata(self, file_id):
        self.meta_calls += 1
        return {'id': file_id, 'size': len(self.data), 'version': self.version,
                'modifiedTime': '2026-11-12T00:00:00Z', 'mimeType': 'video/mp4',
                'md5Checksum': '' if self.missing_checksum else hashlib.md5(self.data).hexdigest()}

    def get(self, file_id, rng=None):
        self.calls.append(rng)
        span = di.bounds(rng, len(self.data)) if rng else None
        if span:
            start, end = span
            response = Response(206, self.data[start:end + 1], {
                'Content-Range': 'bytes %d-%d/%d' % (start, end, len(self.data)),
                'Content-Length': str(end - start + 1), 'Content-Type': 'video/mp4'})
        else:
            response = Response(200, self.data, {'Content-Length': str(len(self.data))})
        self.responses.append(response)
        if self.change_after_read:
            self.data, self.index = movie(1)
        return response

    def drop(self):
        pass


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.drive = Drive()
        self.logs = []
        self.now = 1
        self.cache = di.Cache(self.directory.name, self.logs.append, lambda: self.now)
        self.meta = self.cache.begin('synthetic-file', self.drive, head=True)

    def read(self, rng, cache=None, meta=None):
        return (cache or self.cache).range('synthetic-file', rng, self.drive, meta or self.meta)

    def prime(self):
        return self.read('bytes=-%d' % len(self.drive.index))

    def test_first_mfro_does_not_prefetch_or_add_media_requests(self):
        self.assertEqual(self.read('bytes=-16')[3], self.drive.index[-16:])
        self.assertEqual(self.drive.calls, ['bytes=179-194'])
        self.assertEqual(self.drive.meta_calls, 1)
        self.assertEqual(self.cache.entries, {})

    def test_index_ranges_reuse_identical_bytes_without_remote_media(self):
        self.assertEqual(self.prime()[3], self.drive.index)
        calls = list(self.drive.calls)
        for rng, expected in [('bytes=-16', self.drive.index[-16:]),
                              ('bytes=128-', self.drive.index),
                              ('bytes=130-139', self.drive.index[2:12])]:
            self.assertEqual(self.read(rng)[3], expected)
        self.assertEqual(self.drive.calls, calls)
        self.assertEqual(self.drive.meta_calls, 2)
        self.assertTrue(any('served from cache' in line for line in self.logs))
        self.assertFalse(any('synthetic-file' in line or 'http' in line for line in self.logs))

    def test_cache_survives_restart_but_checks_fresh_metadata(self):
        self.prime()
        cache = di.Cache(self.directory.name)
        meta = cache.begin('synthetic-file', self.drive, head=True)
        calls = list(self.drive.calls)
        self.assertEqual(self.read('bytes=-16', cache, meta)[3], self.drive.index[-16:])
        self.assertEqual(calls, self.drive.calls)
        self.assertEqual(self.drive.meta_calls, 3)
        stored = json.loads(cache.path.read_text())
        self.assertEqual(len(stored['entries']), 1)
        self.assertNotIn('Authorization', cache.path.read_text())

    def test_head_and_immediate_front_share_one_identity_probe(self):
        self.cache.begin('synthetic-file', self.drive, front=True)
        self.assertEqual(self.drive.meta_calls, 1)
        self.cache.begin('synthetic-file', self.drive, front=True)
        self.assertEqual(self.drive.meta_calls, 2)
        self.now += 3
        self.cache.begin('synthetic-file', self.drive, front=True)
        self.assertEqual(self.drive.meta_calls, 3)

    def test_changed_checksum_same_id_and_size_discards_persisted_index(self):
        self.prime()
        self.drive.data, self.drive.index = movie(1)
        self.meta = self.cache.begin('synthetic-file', self.drive, head=True)
        self.assertEqual(self.cache.entries, {})
        self.assertEqual(di.Cache(self.directory.name).entries, {})
        self.assertEqual(self.prime()[3], self.drive.index)
        self.assertEqual(len(self.drive.calls), 2)

    def test_new_drive_version_invalidates_even_if_checksum_unchanged(self):
        self.prime()
        self.drive.version = '2'
        self.cache.begin('synthetic-file', self.drive, head=True)
        self.assertEqual(self.cache.entries, {})

    def test_change_during_index_read_is_not_persisted(self):
        self.drive.change_after_read = True
        self.prime()
        self.assertEqual(self.cache.entries, {})
        self.assertFalse(self.cache.path.exists())

    def test_capture_discards_adjacent_movie_bytes(self):
        self.assertEqual(self.read('bytes=-100')[3], self.drive.data[-100:])
        self.assertEqual(self.cache.entries['synthetic-file']['data'], self.drive.index)

    def test_malformed_index_is_passed_through_without_persistence(self):
        data = bytearray(self.drive.data)
        data[128 + 16] = 2  # Unsupported tfra version, after the mfra/tfra headers.
        self.drive.data = bytes(data)
        self.meta = self.cache.begin('synthetic-file', self.drive, head=True)
        self.assertEqual(self.prime()[3], self.drive.data[-len(self.drive.index):])
        self.assertEqual(self.cache.entries, {})

    def test_oversized_mfro_never_triggers_extra_read(self):
        self.drive.data = self.drive.data[:-4] + struct.pack('>I', di.MAX_INDEX + 1)
        self.meta = self.cache.begin('synthetic-file', self.drive, head=True)
        self.read('bytes=-16')
        self.assertEqual(len(self.drive.calls), 1)
        self.assertEqual(self.cache.entries, {})
        self.assertLessEqual(max(self.drive.responses[0].reads), 17)

    def test_invalid_tables_and_mfro_are_never_cached(self):
        original = self.drive.index
        for at, replacement in ((0, b'\x00\x00\x00\x01'), (28, b'\xff\xff\xff\xff'),
                                (40, struct.pack('>Q', 999999)), (-4, b'\x00\x00\x00\x01')):
            data = bytearray(original)
            at = at if at >= 0 else len(data) + at
            data[at:at + len(replacement)] = replacement
            self.assertFalse(di.valid(bytes(data), 128 + len(data)))

    def test_wrong_or_short_range_is_not_cached(self):
        original = self.drive.get
        for short in (False, True):
            def malformed(file_id, rng):
                response = original(file_id, rng)
                if short:
                    response.truncate(1)
                else:
                    response.headers['Content-Range'] = 'bytes 0-66/195'
                return response
            self.drive.get = malformed
            self.assertIsNone(self.prime())
            self.assertEqual(self.cache.entries, {})

    def test_missing_checksum_disables_cache_and_backs_off(self):
        self.prime()
        self.drive.missing_checksum = True
        self.assertIsNone(self.cache.begin('synthetic-file', self.drive, head=True))
        count = self.drive.meta_calls
        self.assertIsNone(self.cache.begin('synthetic-file', self.drive, head=True))
        self.assertEqual(self.drive.meta_calls, count)
        self.now += 31
        self.drive.missing_checksum = False
        self.assertIsNotNone(self.cache.begin('synthetic-file', self.drive, head=True))

    def test_bad_and_non_tail_ranges_are_not_intercepted(self):
        for rng in (None, 'bytes=1-2,4-5', 'bytes=-0', 'bytes=9-2', 'bytes=999-', 'bytes=0-15'):
            self.assertIsNone(self.read(rng))
        self.assertEqual(self.drive.calls, [])

    def test_disk_failures_do_not_break_index_read(self):
        with patch.object(di.os, 'replace', side_effect=OSError('synthetic full disk')):
            self.assertEqual(self.prime()[3], self.drive.index)
        self.assertEqual(list(Path(self.directory.name).glob('.drive-index-*')), [])

    def test_corrupt_or_oversized_cache_is_ignored(self):
        for data in (b'{broken', b'[]', b'{"entries":[null]}', b' ' * (di.MAX_JSON + 1)):
            self.cache.path.write_bytes(data)
            self.assertEqual(di.Cache(self.directory.name).entries, {})
        self.prime()
        rows = json.loads(self.cache.path.read_text())
        rows['entries'][0]['index'] = 'not-base64'
        self.cache.path.write_text(json.dumps(rows))
        self.assertEqual(di.Cache(self.directory.name).entries, {})

    def test_eviction_respects_entry_and_byte_limits(self):
        self.prime()
        row = self.cache.entries['synthetic-file']
        with patch.object(di, 'MAX_ENTRIES', 2), patch.object(di, 'MAX_TOTAL', len(row['data']) * 2):
            self.cache.entries.update({str(n): dict(row, used=n) for n in range(4)})
            self.cache._save()
            self.assertEqual(set(self.cache.entries), {'2', '3'})

    def test_failed_identity_contexts_remain_bounded(self):
        self.drive.missing_checksum = True
        with patch.object(di, 'MAX_ENTRIES', 2):
            for number in range(5):
                self.cache.begin('unavailable-%d' % number, self.drive)
            self.assertEqual(len(self.cache.failed), 2)

    def test_other_titles_are_not_blocked_by_network_wait(self):
        entered, release = threading.Event(), threading.Event()
        original = self.drive.metadata

        def blocked(file_id):
            if file_id == 'slow-title':
                entered.set()
                release.wait(2)
            return original(file_id)

        self.drive.metadata = blocked
        thread = threading.Thread(target=self.cache.begin, args=('slow-title', self.drive), daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertIsNotNone(self.cache.begin('other-title', self.drive))
            self.assertFalse(release.is_set())
        finally:
            release.set()
            thread.join(2)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.drive = Drive()
        drive = self.drive

        class Connection:
            def request(self, method, path, headers):
                self.path, self.headers = path, headers

            def getresponse(self):
                if 'fields=' in self.path:
                    return Response(200, json.dumps(drive.metadata('synthetic-file')).encode(), {})
                return drive.get('synthetic-file', self.headers.get('Range'))

            def close(self):
                pass

        self.server, port = dp.start(lambda force: 'synthetic', connect=Connection, state_dir=self.directory.name)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = dp.url(port, 'synthetic-file', 'Movie.mp4')

    def fetch(self, rng=None, method='GET'):
        return urllib.request.urlopen(urllib.request.Request(self.url, method=method,
                                      headers={'Range': rng} if rng else {}), timeout=5)

    def test_player_open_then_reopen_serves_exact_local_206s(self):
        with self.fetch(method='HEAD') as r:
            self.assertEqual(r.headers['Content-Length'], str(len(self.drive.data)))
        with self.fetch('bytes=0-15') as r:
            self.assertEqual(r.read(), self.drive.data[:16])
        for rng in ('bytes=-16', 'bytes=128-'):
            with self.fetch(rng) as r:
                self.assertEqual(r.status, 206)
                r.read()
        calls = list(self.drive.calls)
        with self.fetch(method='HEAD'):
            pass
        with self.fetch('bytes=-16') as r:
            self.assertEqual(r.headers['Content-Range'], 'bytes 179-194/195')
            self.assertEqual(r.headers['Content-Length'], '16')
            self.assertEqual(r.read(), self.drive.index[-16:])
        self.assertEqual(self.drive.calls, calls)

    def test_optional_cache_failure_leaves_stream_and_head_usable(self):
        cache = self.server.RequestHandlerClass.indices
        with patch.object(cache, 'begin', side_effect=OSError('synthetic metadata outage')):
            with self.fetch(method='HEAD') as r:
                self.assertEqual(r.headers['Content-Length'], str(len(self.drive.data)))
            with self.fetch('bytes=0-15') as r:
                self.assertEqual(r.read(), self.drive.data[:16])
        with patch.object(cache, 'range', side_effect=ValueError('synthetic malformed cache')):
            with self.fetch('bytes=-16') as r:
                self.assertEqual(r.read(), self.drive.index[-16:])

    def test_metadata_timeout_uses_one_bounded_attempt_then_media_fallback(self):
        upstream = self.server.RequestHandlerClass.upstream
        original = upstream.connect
        attempts = []

        def connect():
            conn = original()
            request = conn.request

            def get(method, path, headers):
                if 'fields=' in path:
                    attempts.append(conn.timeout)
                    raise TimeoutError('synthetic metadata timeout')
                return request(method, path, headers)

            conn.request = get
            return conn

        upstream.connect = connect
        with self.fetch('bytes=0-15') as r:
            self.assertEqual(r.read(), self.drive.data[:16])
        self.assertEqual(attempts, [3])


if __name__ == '__main__':
    unittest.main()
