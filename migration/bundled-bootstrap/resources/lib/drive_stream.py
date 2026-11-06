"""Streams a Google Drive file to the phone's own preparation step, so a movie is never downloaded first.

Owner (build 157): "my storage can't handle large scale downloads". KodiAirPlay r14 reads its source from
http://127.0.0.1; this tiny server answers there with byte ranges of one Drive file, fetched from Drive as they are
asked for (the converter reads, seeks to the index, reads on). Nothing is written to the phone.

Only 127.0.0.1, only with a random per-session token in the path, and only for the Drive files preparation registered.
"""
import http.server
import secrets
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://www.googleapis.com/drive/v3/files'
CHUNK = 1024 * 1024


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


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
                headers = {'Authorization': 'Bearer ' + stream.token()}
                wanted = self.headers.get('Range')
                headers['Range'] = wanted or 'bytes=0-'
                request = urllib.request.Request(API + '/' + urllib.parse.quote(item, safe='') + '?alt=media', headers=headers)
                try:
                    for attempt in range(3):
                        try:
                            upstream = stream.open_url(request, 20)
                            stream.last_problem='';break
                        except urllib.error.HTTPError as error:
                            if error.code not in (429,500,502,503,504) or attempt==2:raise
                        except (urllib.error.URLError,TimeoutError,ConnectionError) as error:
                            if 'CERTIFICATE_VERIFY_FAILED' in str(error) or attempt==2:raise
                        time.sleep(.25*(attempt+1))
                except urllib.error.HTTPError as error:
                    stream.last_problem='Drive media request failed: HTTP %d'%error.code
                    self.send_error(error.code if error.code in (404, 416) else 502)
                    return
                except Exception as error:
                    import preparation_runtime
                    stream.last_problem=preparation_runtime.problem(error)
                    self.send_error(502)
                    return
                try:
                    status = getattr(upstream, 'status', None) or upstream.getcode()
                    length = upstream.headers.get('Content-Length')
                    span = upstream.headers.get('Content-Range')
                    if not wanted and status == 206 and span:
                        status = 200    # the client asked for the whole file: answer as such, with its full length
                    self.send_response(status)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Type', 'application/octet-stream')
                    if length:
                        self.send_header('Content-Length', length)
                    if span and status == 206:
                        self.send_header('Content-Range', span)
                    self.end_headers()
                    if not body:
                        return
                    while True:
                        try:data = upstream.read(CHUNK)
                        except (OSError,urllib.error.URLError) as error:
                            import preparation_runtime
                            stream.last_problem=preparation_runtime.problem(error)
                            self.close_connection=True;break
                        if not data:
                            break
                        stream.bytes_read+=len(data)
                        stream.last_read=time.time()
                        self.wfile.write(data)    # the converter closing to seek ends this read: that is fine
                except (BrokenPipeError, ConnectionResetError, OSError):
                    self.close_connection = True
                finally:
                    try:
                        upstream.close()
                    except Exception:
                        pass

        self.server = _Server(('127.0.0.1', 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stats(self):
        return {'read_bytes':self.bytes_read,'last_read':self.last_read,'read_error':self.last_problem}

    def url(self, item_id):
        """The loopback link KodiAirPlay reads for one Drive file."""
        self.allowed.add(str(item_id))
        return 'http://127.0.0.1:%d/%s/%s/source' % (self.port, self.secret, urllib.parse.quote(str(item_id), safe=''))

    def forget(self, item_id):
        self.allowed.discard(str(item_id))

    def close(self):
        self.server.shutdown()
        self.server.server_close()
