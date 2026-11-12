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
import json
import mimetypes
import re
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
        conn = getattr(self.local, 'conn', None)
        if conn is not None:
            conn.close()
            self.local.conn = None

    def get(self, file_id, rng=None):
        return self.request(media_path(file_id),rng)

    def metadata(self,file_id):
        """Fresh small Drive identity, on a separate bounded connection so a live movie read is untouched."""
        def connect():
            conn=self.connect();conn.timeout=3;return conn
        channel=Upstream(self.token,connect)
        response=None
        try:
            path='/drive/v3/files/%s?fields=id,size,md5Checksum,version,modifiedTime,mimeType&supportsAllDrives=true'%urllib.parse.quote(file_id,safe='')
            response=channel.request(path,attempts=1)
            if response.status!=200:return None
            raw=response.read(8193)
            return json.loads(raw) if len(raw)<=8192 else None
        except Exception:return None
        finally:
            try:
                if response is not None:response.close()
            except Exception:pass
            try:channel.drop()
            except Exception:pass

    def request(self,path,rng=None,attempts=3):
        """The open upstream response for file_id (status 200/206/...), retrying once on a stale connection or 401."""
        force = False
        for attempt in range(attempts):
            access = self.token(force)
            headers = {'Authorization': 'Bearer ' + access}
            if rng:
                headers['Range'] = rng
            conn = self._conn(fresh=attempt > 0)
            try:
                conn.request('GET', path, headers=headers)
                resp = conn.getresponse()
            except (http.client.HTTPException, OSError):
                if attempt == attempts-1:
                    raise
                continue
            if resp.status == 401 and not force and attempt < attempts-1:
                resp.read()
                force = access
                continue
            return resp
        return resp


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    upstream = None
    sizes = {}
    indices = None

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

    def _index_meta(self,file_id,**options):
        try:return self.indices.begin(file_id,self.upstream,**options) if self.indices else None
        except Exception:return None  # Optional acceleration must leave the ordinary stream usable.

    def _index_range(self,file_id,rng,meta):
        try:return self.indices.range(file_id,rng,self.upstream,meta) if self.indices else None
        except Exception:return None

    def do_HEAD(self):
        file_id = parse_path(self.path)
        try:
            if self.indices and file_id:
                meta=self._index_meta(file_id,head=True)
                if meta:self.sizes[file_id]=(meta['size'],meta.get('mimeType') or '')
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

    def do_GET(self):
        file_id = parse_path(self.path)
        if not file_id:
            self.send_error(404)
            return
        rng = self.headers.get('Range')
        try:
            if self.indices:
                meta=self._index_meta(file_id,front=not rng or bool(re.match(r'bytes=0-',rng)))
                hit=self._index_range(file_id,rng,meta)
                if hit:
                    start,end,total,data=hit
                    self.send_response(206);self.send_header('Content-Length',str(len(data)))
                    self.send_header('Content-Range','bytes %d-%d/%d'%(start,end,total));self.send_header('Accept-Ranges','bytes')
                    self.send_header('Content-Type',self._type(self.path,(meta or {}).get('mimeType')));self.end_headers()
                    self.wfile.write(data);return
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


def start(token, connect=None, port=0,state_dir=None,log=lambda text:None):
    """Start the proxy on 127.0.0.1; returns (server, port). token(force) -> bearer token."""
    indices=None
    if state_dir is not None:
        import drive_index
        indices=drive_index.Cache(state_dir,log)
    handler = type('DriveProxyHandler', (Handler,), {'upstream': Upstream(token, connect), 'sizes': {},'indices':indices})
    server = Server(('127.0.0.1', port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]
