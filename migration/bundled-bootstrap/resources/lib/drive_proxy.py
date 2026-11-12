"""Roadmap 1A.1: Drive copies stream through a lean local proxy in the app's own service instead of the Google Drive
add-on's (owner log 396d5d67: the add-on's proxy took 4.8-6.2 s to open a prepared movie and 4.2 s per seek; it runs
its account set-up and metadata calls on every request, and every seek is a new request).

Kodi plays http://127.0.0.1:<port>/drive/<file id>/<name>. Each request goes straight to Drive's media download
(https://www.googleapis.com/drive/v3/files/<id>?alt=media) with Kodi's Range header, over a kept-alive connection per
thread, and the body is passed on in 256 KB pieces. A 401 gets a fresh token and one retry. HEAD (and Kodi's size
probe) is answered from a 1-byte ranged GET, cached per file. Owner logs show Python reading Drive at up to 35 MB/s,
so the interpreter is not the limit here; the add-on's per-request work was."""
import http.client
import http.server
import collections
import mimetypes
import queue
import re
import socketserver
import threading
import time
import urllib.parse
import urllib.request

HOST = 'www.googleapis.com'
PIECE = 256 * 1024
TIMEOUT = 30
PROPERTY = 'KodiIOS.DriveProxy'   # Home window property: the port while the proxy runs
CURRENT = []                      # roadmap 3.5: the running server, so the one-minute summary can read its stats
WARM_HEAD = 4 * 1024 * 1024       # roadmap 1A.4: bytes from the start kept ready when a title's page opens
WARM_TAIL = 1024 * 1024           # ... and from the end (an MP4's fragment index sits there)
WARM_FILES = 2                    # at most this many titles are kept warm (about 10 MB)
WARM_MAX_AGE = 600                # seconds a warmed title stays usable
SPARE_MAX_AGE = 45                # seconds a pre-opened connection is trusted (Drive closes idle ones)
HOLD_MAX = 10                     # roadmap 1G.3: longest one wait is (below Kodi's 20 s low-speed limit), seconds
READ_AHEAD = 16                  # roadmap 1A.5: pieces (4 MB) the proxy reads ahead of Kodi after a seek


def media_path(file_id):
    return '/drive/v3/files/%s?alt=media&supportsAllDrives=true' % urllib.parse.quote(file_id, safe='')


def parse_path(path):
    """file id from '/drive/<id>/<name>', or ''."""
    parts = urllib.parse.urlsplit(path).path.split('/')
    return urllib.parse.unquote(parts[2]) if len(parts) >= 3 and parts[1] == 'drive' and parts[2] else ''


def url(port, file_id, name):
    return 'http://127.0.0.1:%d/drive/%s/%s' % (int(port), urllib.parse.quote(file_id, safe=''), urllib.parse.quote(name or 'video'))


class Warm(object):
    """Roadmap 1A.4: the first and last megabytes of the title whose page is open, read from Drive before Play is tapped,
    so Kodi's first requests (start of the file, the index at its end) are answered locally."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.files = collections.OrderedDict()   # file id -> {'size', 'type', 'at', 'chunks': [(start, bytes)]}
        self.running = set()

    def get(self, file_id):
        with self.lock:
            entry = self.files.get(file_id)
            if entry and self.clock() - entry['at'] > WARM_MAX_AGE:
                del self.files[file_id]
                entry = None
            return entry

    def start(self, upstream, sizes, file_id):
        """Begin warming file_id in the background; 'cached', 'running' or 'started'."""
        with self.lock:
            if file_id in self.running:
                return 'running'
            entry = self.files.get(file_id)
            if entry and self.clock() - entry['at'] <= WARM_MAX_AGE:
                return 'cached'
            self.running.add(file_id)
        threading.Thread(target=self._fill, args=(upstream, sizes, file_id), daemon=True).start()
        return 'started'

    def _read(self, upstream, file_id, rng):
        resp = upstream.get(file_id, rng)
        try:
            if resp.status != 206:
                return None, None
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', resp.getheader('Content-Range') or '')
            if not match:
                return None, None
            first, last, total = (int(v) for v in match.groups())
            data = resp.read(last - first + 1)
            return (first, data, total, resp.getheader('Content-Type') or '') if len(data) == last - first + 1 else (None, None)
        finally:
            resp.close()

    def _fill(self, upstream, sizes, file_id):
        try:
            head = self._read(upstream, file_id, 'bytes=0-%d' % (WARM_HEAD - 1))
            if not head or head[0] is None:
                return
            _, data, total, ctype = head
            chunks = [(0, data)]
            sizes.setdefault(file_id, (total, ctype))
            if total > len(data):
                tail_start = max(len(data), total - WARM_TAIL)
                tail = self._read(upstream, file_id, 'bytes=%d-%d' % (tail_start, total - 1))
                if tail and tail[0] is not None:
                    chunks.append((tail[0], tail[1]))
            with self.lock:
                self.files[file_id] = {'size': total, 'type': ctype, 'at': self.clock(), 'chunks': chunks}
                self.files.move_to_end(file_id)
                while len(self.files) > WARM_FILES:
                    self.files.popitem(last=False)
        except Exception:
            pass
        finally:
            upstream.drop()
            with self.lock:
                self.running.discard(file_id)


class Stats(object):
    """Roadmap 3.5: what the proxy did since the last summary (read by the service once a minute)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.requests = 0
            self.warm_hits = 0
            self.seeks = []        # seconds from a ranged request that does not start at 0 to its first byte

    def add(self, seek=None, warm=False):
        with self.lock:
            self.requests += 1
            self.warm_hits += 1 if warm else 0
            if seek is not None:
                self.seeks.append(seek)

    def take(self):
        with self.lock:
            out = {'requests': self.requests, 'warm_hits': self.warm_hits, 'seeks': list(self.seeks)}
        self.reset()
        return out


class Upstream(object):
    """One kept-alive HTTPS connection per thread to Drive; token(force) gives a bearer token (force: a fresh one)."""

    def __init__(self, token, connect=None, spare=False):
        self.token = token
        self.connect = connect or (lambda: http.client.HTTPSConnection(HOST, timeout=TIMEOUT))
        self.local = threading.local()
        self.keep_spare = spare       # roadmap 1A.5: keep one connected (TLS done) connection ready for the next request
        self.lock = threading.Lock()
        self.spare = None
        self.spare_at = 0.0
        self.preparing = False

    def prepare(self):
        """Open the next connection in the background so a seek's new request skips the TLS handshake."""
        if not self.keep_spare:
            return
        with self.lock:
            if self.spare is not None or self.preparing:
                return
            self.preparing = True

        def run():
            conn = None
            try:
                conn = self.connect()
                if hasattr(conn, 'connect'):
                    conn.connect()
            except Exception:
                conn = None
            with self.lock:
                self.preparing = False
                self.spare, self.spare_at = conn, time.time()
        threading.Thread(target=run, daemon=True).start()

    def _take_spare(self):
        with self.lock:
            conn, self.spare = self.spare, None
            fresh = time.time() - self.spare_at < SPARE_MAX_AGE
        if conn is not None and not fresh:
            try:
                conn.close()
            except Exception:
                pass
            return None
        return conn

    def _conn(self, fresh=False):
        conn = getattr(self.local, 'conn', None)
        if fresh or conn is None:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            conn = None if fresh else self._take_spare()
            self.local.conn = conn or self.connect()
            conn = self.local.conn
            self.prepare()
        return conn

    def drop(self):
        conn = getattr(self.local, 'conn', None)
        if conn is not None:
            conn.close()
            self.local.conn = None

    def get(self, file_id, rng=None):
        """The open upstream response for file_id (status 200/206/...), retrying once on a stale connection or 401."""
        force = False
        for attempt in range(3):
            access = self.token(force)
            headers = {'Authorization': 'Bearer ' + access}
            if rng:
                headers['Range'] = rng
            conn = self._conn(fresh=attempt > 0)
            try:
                conn.request('GET', media_path(file_id), headers=headers)
                resp = conn.getresponse()
            except (http.client.HTTPException, OSError):
                if attempt == 2:
                    raise
                continue
            if resp.status == 401 and not force:
                resp.read()
                force = access
                continue
            return resp
        return resp


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    upstream = None
    sizes = {}
    warm = None
    stats = None
    hold = None

    def log_message(self, *args):
        pass

    def _size(self, file_id):
        if file_id not in self.sizes:
            resp = self.upstream.get(file_id, 'bytes=0-0')
            consumed = False
            try:
                total = re.fullmatch(r'bytes 0-0/([1-9][0-9]*)', resp.getheader('Content-Range') or '')
                if resp.status == 206 and total:
                    # Read at most the requested byte. Never drain a malformed or ignored range response.
                    if len(resp.read(1)) != 1:
                        return None
                    consumed = resp.getheader('Content-Length') == '1'
                    size = int(total.group(1))
                elif resp.status == 200 and (resp.getheader('Content-Length') or '').isdigit():
                    # Drive may ignore Range. The length already tells us the size; close without reading video.
                    size = int(resp.getheader('Content-Length'))
                else:
                    return None
                self.sizes[file_id] = (size, resp.getheader('Content-Type') or '')
            finally:
                resp.close()
                if not consumed:
                    self.upstream.drop()
        return self.sizes[file_id]

    def _type(self, name, given):
        if given and given != 'application/octet-stream':
            return given
        return mimetypes.guess_type(name)[0] or 'video/mp4'

    def do_HEAD(self):
        file_id = parse_path(self.path)
        try:
            info = self._size(file_id) if file_id else None
        except Exception:
            self.upstream.drop()
            self.send_error(502)
            return
        if not info:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(info[0]))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Type', self._type(self.path, info[1]))
        self.end_headers()

    def _stream(self, resp):
        """Pieces of the upstream body, read ahead by a helper thread (roadmap 1A.5) so Drive keeps flowing at line
        speed from a seek's new position while Kodi is busy; the queue holds at most READ_AHEAD pieces."""
        read = getattr(resp, 'read1', None) or resp.read
        pieces = queue.Queue(READ_AHEAD)
        stop = threading.Event()

        def put(item):
            while not stop.is_set():
                try:
                    pieces.put(item, timeout=0.5)
                    return
                except queue.Full:
                    pass

        def produce():
            try:
                while not stop.is_set():
                    piece = read(PIECE)
                    put(piece)
                    if not piece:
                        return
            except Exception as error:
                put(error)
        threading.Thread(target=produce, daemon=True).start()
        try:
            while True:
                piece = pieces.get()
                if isinstance(piece, Exception):
                    raise piece
                if not piece:
                    return
                self._hold()
                yield piece
        finally:
            stop.set()

    def _hold(self):
        """Roadmap 1G.3: while Play on TV is starting, Kodi's own request (its file cache reading ahead of a paused
        video) waits here, so the converter reading the same file through this proxy has the line. Only requests from
        Kodi (user agent 'Kodi/...') wait, never the AirPlay reader (FFmpeg's), and never longer than HOLD_MAX."""
        hold = self.hold
        if not hold or not (self.headers.get('User-Agent') or '').startswith('Kodi/'):
            return
        waited = 0.0
        while waited < HOLD_MAX and hold():
            time.sleep(0.25)
            waited += 0.25

    def _range(self, rng, size):
        match = re.fullmatch(r'bytes=(\d+)-(\d*)', rng or '')
        if not match:
            return None
        first = int(match.group(1))
        last = min(int(match.group(2)), size - 1) if match.group(2) else size - 1
        return (first, last) if first <= last else None

    def _from_warm(self, file_id, rng, started):
        """Answer a ranged request that starts inside the warmed start or end of the file; the rest comes from Drive."""
        entry = self.warm.get(file_id) if self.warm else None
        span = self._range(rng, entry['size']) if entry else None
        if not span:
            return False
        first, last = span
        chunk = next(((start, data) for start, data in entry['chunks'] if start <= first < start + len(data)), None)
        if not chunk:
            return False
        start, data = chunk
        end = min(last, start + len(data) - 1)
        rest = None
        if last > end:
            try:
                rest = self.upstream.get(file_id, 'bytes=%d-%d' % (end + 1, last))
            except Exception:
                return False
            if rest.status != 206:
                rest.read()
                return False
        self.send_response(206)
        self.send_header('Content-Length', str(last - first + 1))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (first, last, entry['size']))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Type', self._type(self.path, entry['type']))
        self.end_headers()
        if self.stats:
            self.stats.add(seek=(time.time() - started) if first else None, warm=True)
        try:
            self.wfile.write(data[first - start:end - start + 1])
            if rest is not None:
                for piece in self._stream(rest):
                    self.wfile.write(piece)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.upstream.drop()
            self.close_connection = True
        return True

    def _warm_request(self):
        """GET /warm/<file id>/<name>: the page of this title opened; read its start and end now (roadmap 1A.4)."""
        parts = urllib.parse.urlsplit(self.path).path.split('/')
        file_id = urllib.parse.unquote(parts[2]) if len(parts) >= 3 else ''
        state = self.warm.start(self.upstream, self.sizes, file_id) if (file_id and self.warm) else 'unavailable'
        self.send_response(202 if state != 'unavailable' else 404)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        started = time.time()
        if self.path.startswith('/warm/'):
            self._warm_request()
            return
        file_id = parse_path(self.path)
        if not file_id:
            self.send_error(404)
            return
        rng = self.headers.get('Range')
        if rng and self._from_warm(file_id, rng, started):
            return
        try:
            resp = self.upstream.get(file_id, rng)
        except Exception:
            self.send_error(502)
            return
        if resp.status not in (200, 206):
            resp.read()
            self.send_error(resp.status if resp.status in (404, 416) else 502)
            return
        self.send_response(resp.status)
        for name in ('Content-Length', 'Content-Range'):
            if resp.getheader(name):
                self.send_header(name, resp.getheader(name))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Type', self._type(self.path, resp.getheader('Content-Type')))
        self.end_headers()
        if self.stats:
            begins = re.match(r'bytes=(\d+)-', rng or '')
            self.stats.add(seek=(time.time() - started) if begins and int(begins.group(1)) else None)
        try:
            for piece in self._stream(resp):
                self.wfile.write(piece)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Kodi closed the request (a seek): the upstream response is half read, so its connection is not reused.
            self.upstream.drop()
            self.close_connection = True


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start(token, connect=None, port=0, hold=None):
    """Start the proxy on 127.0.0.1; returns (server, port). token(force) -> bearer token."""
    stats = Stats()
    handler = type('DriveProxyHandler', (Handler,), {'upstream': Upstream(token, connect, spare=connect is None), 'sizes': {},
                                                     'warm': Warm(), 'stats': stats, 'hold': staticmethod(hold) if hold else None})
    server = Server(('127.0.0.1', port), handler)
    server.stats = stats
    CURRENT[:] = [server]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def ask_warm(port, file_id, name='', timeout=0.6):
    """Called from the Library page when a title's page opens: the proxy reads its start and index now (roadmap 1A.4).
    True when the proxy accepted."""
    address = 'http://127.0.0.1:%d/warm/%s/%s' % (int(port), urllib.parse.quote(file_id, safe=''), urllib.parse.quote(name or 'video'))
    try:
        with urllib.request.urlopen(address, timeout=timeout) as resp:
            return resp.status == 202
    except Exception:
        return False
