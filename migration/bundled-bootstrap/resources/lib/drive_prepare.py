"""Preparation output → Drive, with bounded RAM and no media files on the phone.

A temporary remote object is verified before a resumable update replaces the
original ID. The sole final movie stays in Movies/TV Shows. Failed uploads and
process restarts keep the original, and completed staging files can be resumed.
"""
import hashlib
import json
import queue
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import driveupload

CHUNK = 8 * 1024 * 1024  # Drive requires multiples of 256 KiB
# Build 177 (build-176 log: the upload was busy 270 of 294 s at ~3 MB/s while the converter waited for each 8 MB
# piece): the movie goes up in 32 MB pieces on its own thread, AHEAD pieces may wait their turn, and the converter
# only waits when all of them are full.
MAIN_CHUNK = 32 * 1024 * 1024
AHEAD = 2


def discard(drive, item_id):
    """Remove only an app-owned staging object. Trash still consumes Drive quota."""
    status, _, _ = drive.call('DELETE', driveupload.API+'/'+urllib.parse.quote(str(item_id),safe=''))
    if status not in (204,404):raise RuntimeError('Temporary preparation cleanup: HTTP %d'%status)


class Sink:
    def __init__(self, drive, parent, name, keep_going, on_file=lambda track,item:None, background=True, clock=time.monotonic, sleep=None):
        self.drive, self.parent, self.name, self.keep_going = drive, parent, name, keep_going
        self.tracks = {}
        self.on_file = on_file
        self.background, self.clock, self.sleep = background, clock, sleep
        self.closed = False
        self.sent = 0            # bytes Drive has confirmed for the movie
        self.marks = []          # (time, sent) over the last 20 s, for the upload speed
        self.made = 0            # bytes of the movie the converter has handed over
        self.made_marks = []     # (time, made): how fast the converter makes the movie (shown before any upload)

    def rate(self):
        """How fast the movie goes up to Drive (bytes per second over the last ~20 s)."""
        marks = list(self.marks)
        if len(marks) < 2 or marks[-1][0] - marks[0][0] < 1:return 0.0
        return (marks[-1][1] - marks[0][1]) / (marks[-1][0] - marks[0][0])

    def made_rate(self):
        """How fast the converter hands over the movie (bytes per second over the last ~20 s)."""
        marks = list(self.made_marks)
        if len(marks) < 2 or marks[-1][0] - marks[0][0] < 1:return 0.0
        return (marks[-1][1] - marks[0][1]) / (marks[-1][0] - marks[0][0])

    def _confirmed(self, t, track):
        if track != 0:return
        self.sent = t['offset']
        now = self.clock()
        self.marks.append((now, self.sent))
        self.marks[:] = [m for m in self.marks if now - m[0] <= 20]

    def _uploader(self, t):
        """The movie's pieces, in order, to Drive. Errors are kept and raised in the converter's thread."""
        wire = t['wire']
        while True:
            try:piece = t['queue'].get(timeout=0.5)
            except queue.Empty:
                if self.closed:return
                continue
            if piece is None or self.closed:return
            try:
                wire['buffer'].extend(piece)
                self._send(wire, len(piece), final=False, sleep=self.sleep)
                self._confirmed(wire, 0)
            except BaseException as error:
                t['error'] = error
                return

    def _raise(self, t):
        if t.get('error') is not None:raise t['error']

    def close(self):
        """Stop the upload thread (a failed or cancelled conversion): it ends at its next piece."""
        self.closed = True
        for t in self.tracks.values():
            if t.get('thread'):
                t['thread'].join(timeout=60)

    def write(self, track, suffix, data):
        if not self.keep_going():raise driveupload.Stop('Preparation paused')
        if track not in self.tracks:
            name = self.name + suffix
            status, headers, _ = self.drive.call('POST', driveupload.UPLOAD + '?uploadType=resumable&fields=id,size,md5Checksum,name',
                json.dumps({'name':name, 'parents':[self.parent]}).encode(),
                {'Content-Type':'application/json', 'X-Upload-Content-Type':'video/mp4' if track == 0 else 'application/octet-stream'})
            url = headers.get('Location') or headers.get('location')
            if status != 200 or not url:raise RuntimeError('Preparation upload start: HTTP %d' % status)
            self.tracks[track] = dict(url=url, offset=0, buffer=bytearray(), md5=hashlib.md5(), name=name,
                                      chunk=(MAIN_CHUNK if self.background else CHUNK) if track == 0 else 256*1024)
            if track == 0 and self.background:
                t = self.tracks[0]
                t['wire'] = dict(url=url, offset=0, buffer=bytearray())
                t['queue'] = queue.Queue(maxsize=AHEAD)
                t['thread'] = threading.Thread(target=self._uploader, args=(t,), daemon=True)
                t['thread'].start()
        t = self.tracks[track]
        if t.get('queue') is not None:self._raise(t)
        if track == 0:
            self.made += len(data)
            now = self.clock()
            if not self.made_marks or now - self.made_marks[-1][0] >= 0.5:
                self.made_marks.append((now, self.made))
                self.made_marks[:] = [m for m in self.made_marks if now - m[0] <= 20]
        t['md5'].update(data)
        t['buffer'].extend(data)
        # Keep the last chunk until generation succeeds: cancellation cannot commit a truncated movie.
        while len(t['buffer']) > t['chunk']:
            if t.get('queue') is None:
                self._send(t, t['chunk'], final=False)
                self._confirmed(t, track)
                continue
            piece = bytes(t['buffer'][:t['chunk']])
            while True:   # wait for room, but never forever: an upload error or a pause ends the wait
                self._raise(t)
                if not self.keep_going():raise driveupload.Stop('Preparation paused')
                try:t['queue'].put(piece, timeout=0.5);break
                except queue.Full:continue
            del t['buffer'][:t['chunk']]

    def _send(self, t, length, final, attempts=8, sleep=None):
        """Send the first `length` buffered bytes. Drive may keep only part of a chunk (308 with a shorter Range) or
        answer 5xx: what it confirmed is dropped from the buffer and the rest is sent again (owner, build 169:
        Interstellar failed after two hours on "did not acknowledge its byte range")."""
        import time
        sleep = sleep or time.sleep
        target = t['offset'] + length
        for attempt in range(attempts):
            if not self.keep_going():raise driveupload.Stop('Preparation paused')
            start = t['offset']
            remaining = target - start
            body = bytes(t['buffer'][:remaining])
            content_range = 'bytes %d-%d/%s' % (start, target - 1, str(target) if final else '*')
            try:status, headers, answer = self.drive.call('PUT', t['url'], body, {'Content-Range':content_range})
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                status, headers, answer = 0, {}, b''
            if final and status in (200, 201):
                result = json.loads(answer)
                if int(result.get('size', -1)) != target or result.get('md5Checksum', '').lower() != t['md5'].hexdigest():
                    raise RuntimeError('Prepared Drive file checksum differs')
                t['result'] = result
                del t['buffer'][:remaining]
                t['offset'] = target
                return
            if status != 308:
                # Lost answer or a Drive hiccup: ask how far it got, then carry on from there.
                sleep(min(30, 2 ** attempt))
                try:status, headers, answer = self.drive.call('PUT', t['url'], b'', {'Content-Range':'bytes */%s' % (str(target) if final else '*')})
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):continue
                if final and status in (200, 201):
                    result = json.loads(answer)
                    if int(result.get('size', -1)) == target and result.get('md5Checksum', '').lower() == t['md5'].hexdigest():
                        t['result'] = result;del t['buffer'][:remaining];t['offset'] = target;return
                    raise RuntimeError('Prepared Drive file checksum differs')
                if status != 308:continue
            got = driveupload._next_offset(headers) if headers.get('Range') or headers.get('range') else start
            if got < start or got > target:raise RuntimeError('Preparation upload offset is invalid')
            del t['buffer'][:got - start]
            t['offset'] = got
            if got == target and not final:return
        raise RuntimeError('Preparation upload did not acknowledge its byte range')

    def finish(self):
        # Finish sidecars first. A failed main output leaves its source intact.
        for track in sorted(self.tracks, key=lambda n:n == 0):
            t = self.tracks[track]
            if t.get('queue') is not None:
                # Every piece handed over must be confirmed before the last one is sent.
                t['queue'].put(None)
                while t['thread'].is_alive():
                    t['thread'].join(timeout=0.5)
                    if not self.keep_going():
                        self.close();raise driveupload.Stop('Preparation paused')
                self._raise(t)
                t['offset'] = t['wire']['offset']
            self._send(t, len(t['buffer']), final=True)
            self._confirmed(t, track)
            self.on_file(str(track),t['result'])
        if 0 not in self.tracks:raise RuntimeError('Preparation produced no video')
        return {str(k):t['result'] for k,t in self.tracks.items()}


def replace(drive, source, prepared, session, commit, keep_going, open_at, progress):
    """Copy the validated remote temporary output into the same movie ID, without disk or full RAM copy."""
    import prepare_downloads as prep
    size, digest = int(prepared['size']), prepared['md5Checksum'].lower()
    current = prep.metadata(drive, source['id'])
    if int(current['size']) == size and current['md5Checksum'].lower() == digest:return current
    if prep.identity(current) != prep.identity(source):raise RuntimeError('Drive source changed; preparation will rescan')
    staged = prep.metadata(drive,prepared['id'])
    if int(staged['size']) != size or staged['md5Checksum'].lower() != digest:
        raise RuntimeError('Prepared Drive file checksum differs; original retained')
    offset = 0
    if session.get('url'):
        status, headers, _ = drive.call('PUT', session['url'], b'', {'Content-Range':'bytes */%d' % size})
        if status in (200,201):return prep.metadata(drive, source['id'])
        if status == 308:offset = driveupload._next_offset(headers)
        else:session.clear()
    if not session.get('url'):
        headers = {'Content-Type':'application/json', 'X-Upload-Content-Length':str(size), 'X-Upload-Content-Type':'video/mp4'}
        if current.get('_etag'):headers['If-Match'] = current['_etag']
        status, answer, _ = drive.call('PATCH', driveupload.UPLOAD + '/' + urllib.parse.quote(source['id'], safe='') + '?uploadType=resumable&fields=id,size,md5Checksum',
                                     json.dumps({'name':source['name'].rsplit('.',1)[0] + '.mp4', 'mimeType':'video/mp4'}).encode(), headers)
        url = answer.get('Location') or answer.get('location')
        if status != 200 or not url:raise RuntimeError('Prepared file replacement start: HTTP %d' % status)
        session['url'] = url;commit()
    if offset < 0 or offset >= size:raise RuntimeError('Prepared upload offset is invalid')
    with open_at(offset) as response:
        if response.status != 206 or response.headers.get('Content-Range','') != 'bytes %d-%d/%d' % (offset,size-1,size):
            raise RuntimeError('Drive returned the wrong prepared byte range')
        while offset < size:
            if not keep_going():raise driveupload.Stop('Preparation paused')
            data = response.read(min(CHUNK, size-offset))
            if not data:raise RuntimeError('Prepared Drive file read was incomplete')
            # read() may return short; a nonfinal upload must still align to 256 KiB.
            while len(data) < min(CHUNK,size-offset):
                more = response.read(min(CHUNK,size-offset)-len(data))
                if not more:raise RuntimeError('Prepared Drive file read was incomplete')
                data += more
            end = offset + len(data)
            headers = {'Content-Range':'bytes %d-%d/%d' % (offset,end-1,size)}
            if end == size:
                if prep.identity(prep.metadata(drive,prepared['id'])) != prep.identity(staged):
                    raise RuntimeError('Prepared Drive file changed during upload; original retained')
                fresh = prep.metadata(drive, source['id'])
                if prep.identity(fresh) != prep.identity(source):raise RuntimeError('Drive source changed during preparation; not replaced')
                if fresh.get('_etag'):headers['If-Match'] = fresh['_etag']
            status, answer, _ = drive.call('PUT', session['url'], data, headers)
            if status in (200,201):
                result = prep.metadata(drive, source['id'])
                if int(result['size']) != size or result['md5Checksum'].lower() != digest:raise RuntimeError('Prepared Drive file checksum differs')
                session.clear();commit();progress(size,size);return result
            if status != 308 or driveupload._next_offset(answer) != end:raise RuntimeError('Prepared upload byte range was not acknowledged')
            offset = end;progress(offset,size)
    raise RuntimeError('Drive did not confirm the prepared file')
