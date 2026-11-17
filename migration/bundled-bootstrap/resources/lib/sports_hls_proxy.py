"""Loopback HLS proxy with opaque, media-suffixed paths and shared upstream session."""
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin, urlsplit


class Proxy:
    def __init__(self, address, headers, session=None):
        if session is None:
            import requests
            session = requests.Session()
        self.session, self.headers = session, dict(headers)
        try:
            with self.session.get(address, headers=self.headers, timeout=(5, 15), stream=True) as response:
                if response.status_code != 200:
                    raise RuntimeError('HLS playlist refused (HTTP %d)' % response.status_code)
                prefix = next(iter(response.iter_content(65536)), b'')
                if not prefix.lstrip().startswith(b'#EXTM3U'):
                    raise RuntimeError('source did not return HLS')
        except Exception:
            self.session.close()
            raise
        self.lock = threading.Lock()
        self.paths, self.reverse = {}, {}
        self.token = uuid.uuid4().hex
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                owner.serve(self, False)
            def do_HEAD(self):
                owner.serve(self, True)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.base = 'http://127.0.0.1:%d' % self.server.server_port
        self.url = self.register(address, 'm3u8')
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def register(self, address, extension):
        parts = urlsplit(address)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            raise ValueError('invalid HLS resource')
        with self.lock:
            key = (address, extension)
            if key not in self.reverse:
                path = '/%s/%d.%s' % (self.token, len(self.paths), extension)
                self.paths[path], self.reverse[key] = address, path
            return self.base + self.reverse[key]

    def rewrite(self, text, final):
        result = []
        variant = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                result.append(line)
                continue
            if stripped.startswith('#'):
                extension = 'key' if stripped.startswith('#EXT-X-KEY:') else ('mp4' if stripped.startswith('#EXT-X-MAP:') else 'm3u8')
                line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="'+self.register(urljoin(final, m.group(1)), extension)+'"', line)
                variant = stripped.startswith('#EXT-X-STREAM-INF:') or variant
            else:
                line = self.register(urljoin(final, stripped), 'm3u8' if variant else 'ts')
                variant = False
            result.append(line)
        return '\n'.join(result)+'\n'

    def serve(self, handler, head):
        with self.lock:
            address = self.paths.get(urlsplit(handler.path).path)
        if address is None:
            handler.send_error(404)
            return
        headers = dict(self.headers)
        if handler.headers.get('Range'):
            headers['Range'] = handler.headers['Range']
        try:
            with self.session.get(address, headers=headers, timeout=(5, 15), stream=True) as response:
                if response.status_code not in (200, 206):
                    handler.send_error(response.status_code if 400 <= response.status_code < 600 else 502)
                    return
                chunks, length = [], 0
                for chunk in response.iter_content(65536):
                    length += len(chunk)
                    if length > 32 * 1024 * 1024:
                        raise ValueError('HLS resource too large')
                    chunks.append(chunk)
                data = b''.join(chunks)
                ctype = response.headers.get('Content-Type', 'application/octet-stream')
                if data.lstrip().startswith(b'#EXTM3U'):
                    data = self.rewrite(data.decode('utf-8-sig'), response.url).encode()
                    ctype = 'application/vnd.apple.mpegurl'
                handler.send_response(response.status_code)
                handler.send_header('Content-Type', ctype)
                handler.send_header('Content-Length', str(len(data)))
                if response.headers.get('Content-Range'):
                    handler.send_header('Content-Range', response.headers['Content-Range'])
                handler.end_headers()
                if not head:
                    handler.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            try:
                handler.send_error(502)
            except OSError:
                pass

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.session.close()
