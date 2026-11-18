"""Controlled loopback source for the build 578 AirPlay range-read investigation.

This exercises the actual foreground cache over HTTP, not AVPlayer, FFmpeg or an iPhone.
The byte ranges stand in for inspection and concurrent audio/video reads; no media is played.
"""
import concurrent.futures
import http.server
import json
import re
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import remote_media

BLOCK = remote_media.BLOCK
DATA = bytes(range(256)) * (6 * BLOCK // 256)


class Source(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, delay, failures, fault_block, overload=False):
        super().__init__(('127.0.0.1', 0), Handler)
        self.delay, self.failures, self.fault_block = delay, failures, fault_block
        self.inject = False
        self.overload = overload
        self.lock = threading.Lock()
        self.attempts = {}
        self.refused = 0
        self.concurrent = self.peak = 0


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        match = re.fullmatch(r'bytes=(\d+)-(\d+)', self.headers.get('Range', ''))
        if not match:
            self.send_error(400)
            return
        start, end = map(int, match.groups())
        end = min(end, len(DATA) - 1)
        with self.server.lock:
            key = (start, end)
            attempt = self.server.attempts.get(key, 0) + 1
            self.server.attempts[key] = attempt
            self.server.concurrent += 1
            self.server.peak = max(self.server.peak, self.server.concurrent)
            reject = (self.server.inject and start // BLOCK == self.server.fault_block and
                      (self.server.concurrent > 2 if self.server.overload else attempt <= self.server.failures))
            if reject:
                self.server.refused += 1
        try:
            time.sleep(self.server.delay)
            if reject:
                # A server that ignores Range answers 200 without Content-Range. The cache must reject it.
                self.send_response(200)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            self.send_response(206)
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, len(DATA)))
            self.send_header('Content-Length', str(end - start + 1))
            self.end_headers()
            self.wfile.write(DATA[start:end + 1])
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with self.server.lock:
                self.server.concurrent -= 1


def measure(failures=0, delay=.08, fault_phase='playback', overload=False, read_ahead=False):
    server = Source(delay, failures, 5 if fault_phase == 'inspection' else 2, overload)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cache = remote_media.Foreground('http://127.0.0.1:%d/fixture.mkv' % server.server_port)
    # Stop speculative prefetch so the experiment controls exactly when faults begin. Real app prefetch remains enabled.
    if not read_ahead:
        cache.hold = lambda: True

    def read(start, length):
        request = urllib.request.Request(cache.media_url, headers={'Range': 'bytes=%d-%d' % (start, start + length - 1)})
        begin = time.monotonic()
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read()
        if data != DATA[start:start + length]:
            raise AssertionError('source bytes changed or read was incomplete')
        return time.monotonic() - begin

    try:
        begin = time.monotonic()
        read(0, 65536)
        if fault_phase == 'inspection':
            server.inject = True
        read(len(DATA) - 65536, 65536)
        inspection = time.monotonic() - begin
        server.inject = True
        # Two readers need the same not-yet-cached block at once, like separate audio and video demuxers.
        barrier = threading.Barrier(2)
        def consumer(offset):
            barrier.wait(timeout=5)
            return read(2 * BLOCK + offset, 65536)
        begin = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            reads = list(pool.map(consumer, (0, 131072)))
        stats = cache.stats()
        return {'inspection_s': round(inspection, 3), 'concurrent_reads_s': round(time.monotonic() - begin, 3),
                'reader_s': [round(x, 3) for x in reads], 'refused_ranges': server.refused,
                'upstream_requests': stats['http_requests'], 'retries': stats['http_retries'],
                'http_errors': stats['http_errors'], 'cache_waits': stats['cache_waits'],
                'peak_upstream_connections': server.peak}
    finally:
        cache.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class RangeFixture(unittest.TestCase):
    def test_slow_refusals_are_retried_and_readers_get_exact_bytes(self):
        healthy = measure(failures=0)
        original = remote_media.drive_stream.DriveStream._fetch
        def old_retry_policy(self, item, start, end, fail_fast_range=False):
            return original(self, item, start, end)
        with patch.object(remote_media.drive_stream.DriveStream, '_fetch', old_retry_policy):
            faulty_before = measure(failures=2)
        opening = measure(failures=2, fault_phase='inspection')
        faulty = measure(failures=2)
        self.assertEqual(healthy['refused_ranges'], 0)
        self.assertGreaterEqual(opening['refused_ranges'], 2)
        self.assertGreater(opening['retries'], 0)
        self.assertGreaterEqual(faulty['refused_ranges'], 2)
        self.assertGreaterEqual(faulty['http_errors'], faulty['refused_ranges'])
        self.assertGreater(faulty['retries'], 0)
        self.assertLess(faulty['retries'], faulty_before['retries'])
        self.assertGreater(faulty['cache_waits'], 0)
        print('\nControlled range fixture: ' + json.dumps({'healthy': healthy, 'playback_fault_before': faulty_before, 'inspection_fault': opening,
                                                          'playback_fault': faulty}, sort_keys=True))

    def test_connection_limited_source_and_production_read_ahead(self):
        # Compare with the original per-piece retry policy in the same process and on the same synthetic source.
        original = remote_media.drive_stream.DriveStream._fetch
        def old_retry_policy(self, item, start, end, fail_fast_range=False):
            return original(self, item, start, end)
        with patch.object(remote_media.drive_stream.DriveStream, '_fetch', old_retry_policy):
            before = measure(delay=.15, overload=True)
            fast_before = measure(delay=.005, read_ahead=True)
            slow_before = measure(delay=.15, read_ahead=True)
        after = measure(delay=.15, overload=True)
        fast = measure(delay=.005, read_ahead=True)
        slow = measure(delay=.15, read_ahead=True)
        faulty_ahead = measure(failures=2, fault_phase='inspection', read_ahead=True)
        self.assertGreater(before['refused_ranges'], 0)
        self.assertGreater(after['refused_ranges'], 0)
        self.assertEqual(fast['refused_ranges'], 0)
        self.assertEqual(slow['refused_ranges'], 0)
        self.assertGreater(faulty_ahead['refused_ranges'], 0)
        print('\nConnection-limited fixture: ' + json.dumps({'before': before, 'after': after,
              'healthy_fast_before': fast_before, 'healthy_fast_after': fast,
              'healthy_slow_before': slow_before, 'healthy_slow_after': slow,
              'fault_with_read_ahead': faulty_ahead}, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
