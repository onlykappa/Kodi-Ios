"""Streams a Google Drive file to the phone's own preparation step, so a movie is never downloaded first.

Owner (build 157): "my storage can't handle large scale downloads". KodiAirPlay r14 reads its source from
http://127.0.0.1; this tiny server answers there with byte ranges of one Drive file, fetched from Drive as they are
asked for (the converter reads, seeks to the index, reads on). Nothing is written to the phone.

Only 127.0.0.1, only with a random per-session token in the path, and only for the Drive files preparation registered.
"""
import collections
import http.server
import re
import secrets
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://www.googleapis.com/drive/v3/files'
CHUNK = 1024 * 1024
# Owner (build 175 log: "our converter is awful"): per 30 s of Inception the video took 37 s on the phone's hardware,
# but each of its two audio tracks took 23 s more, because every track opens the file on its own and reads all of it
# (picture included) and each of the converter's 1 MiB requests went to Drive separately (~1.3 MB/s). Drive is now
# read in BLOCK pieces, each fetched once and kept for KEEP blocks, so the other tracks read it from memory; the next
# block is fetched while one is being read.
BLOCK = 8 * 1024 * 1024
KEEP = 24            # 192 MB (build 181: two video lanes and the audio drift apart; build-176 read 3x the film)
READ_AHEAD = 4       # blocks fetched ahead in parallel (32 MB on its way while one block is read)
SPAN = re.compile(r'bytes (\d+)-(\d+)/(\d+)')


class _Blocks(object):
    """Blocks of Drive files: one upstream fetch per block however many readers want it at once."""
    def __init__(self, fetch, keep=KEEP):
        self.fetch = fetch          # fetch(item, start, end) -> (bytes, total size)
        self.keep = keep
        self.lock = threading.Lock()
        self.data = collections.OrderedDict()
        self.pending = {}
        self.sizes = {}

    def get(self, item, index):
        key = (item, index)
        for _ in range(4):
            with self.lock:
                if key in self.data:
                    self.data.move_to_end(key)
                    return self.data[key]
                waiting = self.pending.get(key)
                if waiting is None:
                    mine = self.pending[key] = threading.Event()
                    break
            waiting.wait(120)   # another reader is fetching it: use theirs (or fetch it ourselves if that failed)
        else:
            raise TimeoutError('Drive block was not read in time')
        try:
            body, total = self.fetch(item, index * BLOCK, index * BLOCK + BLOCK - 1)
            with self.lock:
                self.data[key] = body
                self.sizes[item] = total
                while len(self.data) > self.keep:
                    self.data.popitem(last=False)
            return body
        finally:
            with self.lock:
                self.pending.pop(key, None)
            mine.set()

    def size(self, item):
        with self.lock:
            if item in self.sizes:
                return self.sizes[item]
        self.get(item, 0)
        return self.sizes[item]

    def ahead(self, item, index):
        """Fetch a block in the background unless it is here, on its way, or past the end."""
        with self.lock:
            total = self.sizes.get(item)
            if (item, index) in self.data or (item, index) in self.pending or total is None or index * BLOCK >= total:
                return

        def run():
            try:
                self.get(item, index)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def forget(self, item):
        with self.lock:
            for key in [k for k in self.data if k[0] == item]:
                del self.data[key]
            self.sizes.pop(item, None)


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # The converter hangs up whenever it seeks (owner, build 169 log: dozens of "Connection reset by peer"
        # tracebacks a minute). That is normal here; anything else is still reported.
        import sys
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class DriveStream(object):
    def __init__(self, token, context=None, open_url=None):
        """token() -> a Drive access token (driveupload.Drive.token); open_url(request, timeout) for tests."""
        self.token = token
        self.open_url = open_url or (lambda request, timeout: urllib.request.urlopen(request, timeout=timeout, context=context))
        self.secret = secrets.token_urlsafe(18)
        self.allowed = set()
        self.bytes_read=0
        self.last_read=0
        self.last_problem=''
        self.blocks = _Blocks(self._fetch)
        stream = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def file_id(self):
                parts = urllib.parse.urlsplit(self.path).path.strip('/').split('/')
                if len(parts) != 3 or not secrets.compare_digest(parts[0], stream.secret) or parts[1] not in stream.allowed:
                    return None
                return parts[1]

            def do_HEAD(self):
                self.relay(body=False)

            def do_GET(self):
                self.relay(body=True)

            def relay(self, body):
                item = self.file_id()
                if item is None:
                    self.send_error(404)
                    return
                wanted = self.headers.get('Range')
                try:
                    total = stream.blocks.size(item)
                    start, end = 0, total - 1
                    if wanted:
                        m = re.match(r'bytes=(\d*)-(\d*)$', wanted.strip())
                        if not m or not (m.group(1) or m.group(2)):
                            self.send_error(416)
                            return
                        if m.group(1):
                            start = int(m.group(1))
                            end = min(int(m.group(2)), total - 1) if m.group(2) else total - 1
                        else:
                            start = max(0, total - int(m.group(2)))
                    if start > end or start >= total:
                        self.send_response(416)
                        self.send_header('Content-Range', 'bytes */%d' % total)
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                        return
                except urllib.error.HTTPError as error:
                    stream.last_problem = 'Drive media request failed: HTTP %d' % error.code
                    self.send_error(error.code if error.code in (404, 416) else 502)
                    return
                except Exception as error:
                    import preparation_runtime
                    stream.last_problem = preparation_runtime.problem(error)
                    self.send_error(502)
                    return
                self.send_response(206 if wanted else 200)
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(end - start + 1))
                if wanted:
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, total))
                self.end_headers()
                if not body:
                    return
                try:
                    position = start
                    while position <= end:
                        index = position // BLOCK
                        try:
                            block = stream.blocks.get(item, index)
                        except Exception as error:
                            import preparation_runtime
                            stream.last_problem = preparation_runtime.problem(error)
                            self.close_connection = True
                            return
                        # Build 182 (build-181 log: the upload waited for the Drive read 45% of the time at ~4-5 MB/s):
                        # the next READ_AHEAD blocks are fetched at once, in parallel, not one after another.
                        for step in range(1, READ_AHEAD + 1):
                            stream.blocks.ahead(item, index + step)
                        piece = block[position - index * BLOCK:end - index * BLOCK + 1]
                        if not piece:
                            self.close_connection = True
                            return
                        self.wfile.write(piece)    # the converter closing to seek ends this read: that is fine
                        position += len(piece)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    self.close_connection = True

        self.server = _Server(('127.0.0.1', 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def _fetch(self, item, start, end):
        """Bytes start..end of a Drive file, read whole, and the file's size; transient failures retried."""
        request = urllib.request.Request(API + '/' + urllib.parse.quote(item, safe='') + '?alt=media',
                                         headers={'Authorization': 'Bearer ' + self.token(), 'Range': 'bytes=%d-%d' % (start, end)})
        for attempt in range(3):
            try:
                upstream = self.open_url(request, 20)
                try:
                    status = getattr(upstream, 'status', None) or upstream.getcode()
                    span = SPAN.match(upstream.headers.get('Content-Range') or '')
                    if status == 206 and span:
                        total = int(span.group(3))
                    elif status == 200 and start == 0:
                        total = int(upstream.headers.get('Content-Length') or 0)
                    else:
                        raise ConnectionError('Drive answered without the asked byte range')
                    want = min(end, total - 1) - start + 1
                    parts = []
                    got = 0
                    while got < want:
                        data = upstream.read(min(CHUNK, want - got))
                        if not data:
                            break
                        parts.append(data)
                        got += len(data)
                        self.bytes_read += len(data)
                        self.last_read = time.time()
                    if got < want:
                        raise ConnectionError('Drive ended a block early')
                finally:
                    try:
                        upstream.close()
                    except Exception:
                        pass
                self.last_problem = ''
                return b''.join(parts), total
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
                if 'CERTIFICATE_VERIFY_FAILED' in str(error) or attempt == 2:
                    raise
            time.sleep(.25 * (attempt + 1))

    def stats(self):
        return {'read_bytes':self.bytes_read,'last_read':self.last_read,'read_error':self.last_problem}

    def url(self, item_id):
        """The loopback link KodiAirPlay reads for one Drive file."""
        self.allowed.add(str(item_id))
        return 'http://127.0.0.1:%d/%s/%s/source' % (self.port, self.secret, urllib.parse.quote(str(item_id), safe=''))

    def forget(self, item_id):
        self.allowed.discard(str(item_id))
        self.blocks.forget(str(item_id))

    def close(self):
        self.server.shutdown()
        self.server.server_close()
