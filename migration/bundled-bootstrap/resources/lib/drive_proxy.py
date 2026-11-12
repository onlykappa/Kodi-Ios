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
import mimetypes
import socketserver
import threading
import urllib.parse

HOST = 'www.googleapis.com'
PIECE = 256 * 1024
TIMEOUT = 30
PROPERTY = 'KodiIOS.DriveProxy'   # Home window property: the port while the proxy runs


def media_path(file_id):
    return '/drive/v3/files/%s?alt=media&supportsAllDrives=true' % urllib.parse.quote(file_id, safe='')


def parse_path(path):
    """file id from '/drive/<id>/<name>', or ''."""
    parts = urllib.parse.urlsplit(path).path.split('/')
    return urllib.parse.unquote(parts[2]) if len(parts) >= 3 and parts[1] == 'drive' and parts[2] else ''


def url(port, file_id, name):
    return 'http://127.0.0.1:%d/drive/%s/%s' % (int(port), urllib.parse.quote(file_id, safe=''), urllib.parse.quote(name or 'video'))


class Upstream(object):
    """One kept-alive HTTPS connection per thread to Drive; token(force) gives a bearer token (force: a fresh one)."""

    def __init__(self, token, connect=None):
        self.token = token
        self.connect = connect or (lambda: http.client.HTTPSConnection(HOST, timeout=TIMEOUT))
        self.local = threading.local()

    def _conn(self, fresh=False):
        conn = getattr(self.local, 'conn', None)
        if fresh or conn is None:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            conn = self.local.conn = self.connect()
        return conn

    def drop(self):
        self._conn(fresh=True)

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

    def log_message(self, *args):
        pass

    def _size(self, file_id):
        if file_id not in self.sizes:
            resp = self.upstream.get(file_id, 'bytes=0-0')
            body = resp.read()
            total = (resp.getheader('Content-Range') or '').rsplit('/', 1)[-1]
            if resp.status in (200, 206) and (total.isdigit() or resp.status == 200):
                self.sizes[file_id] = (int(total) if total.isdigit() else len(body), resp.getheader('Content-Type') or '')
            else:
                return None
        return self.sizes[file_id]

    def _type(self, name, given):
        if given and given != 'application/octet-stream':
            return given
        return mimetypes.guess_type(name)[0] or 'video/mp4'

    def do_HEAD(self):
        file_id = parse_path(self.path)
        info = self._size(file_id) if file_id else None
        if not info:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(info[0]))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Type', self._type(self.path, info[1]))
        self.end_headers()

    def do_GET(self):
        file_id = parse_path(self.path)
        if not file_id:
            self.send_error(404)
            return
        rng = self.headers.get('Range')
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
        try:
            while True:
                piece = resp.read(PIECE)
                if not piece:
                    break
                self.wfile.write(piece)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Kodi closed the request (a seek): the upstream response is half read, so its connection is not reused.
            self.upstream.drop()
            self.close_connection = True


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start(token, connect=None, port=0):
    """Start the proxy on 127.0.0.1; returns (server, port). token(force) -> bearer token."""
    handler = type('DriveProxyHandler', (Handler,), {'upstream': Upstream(token, connect), 'sizes': {}})
    server = Server(('127.0.0.1', port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]
