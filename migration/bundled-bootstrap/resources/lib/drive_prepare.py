"""Preparation output → Drive, with bounded RAM and no media files on the phone.

A temporary remote object is verified before a resumable update replaces the
original ID. The sole final movie stays in Movies/TV Shows. Failed uploads and
process restarts keep the original, and completed staging files can be resumed.
"""
import hashlib
import json
import urllib.parse
import urllib.request
import driveupload

CHUNK = 1024 * 1024  # Drive requires multiples of 256 KiB


class Sink:
    def __init__(self, drive, parent, name, keep_going, on_file=lambda track,item:None):
        self.drive, self.parent, self.name, self.keep_going = drive, parent, name, keep_going
        self.tracks = {}
        self.on_file = on_file

    def write(self, track, suffix, data):
        if not self.keep_going():raise driveupload.Stop('Preparation paused')
        if track not in self.tracks:
            name = self.name + suffix
            status, headers, _ = self.drive.call('POST', driveupload.UPLOAD + '?uploadType=resumable&fields=id,size,md5Checksum,name',
                json.dumps({'name':name, 'parents':[self.parent]}).encode(),
                {'Content-Type':'application/json', 'X-Upload-Content-Type':'video/mp4' if track == 0 else 'application/octet-stream'})
            url = headers.get('Location') or headers.get('location')
            if status != 200 or not url:raise RuntimeError('Preparation upload start: HTTP %d' % status)
            self.tracks[track] = dict(url=url, offset=0, buffer=bytearray(), md5=hashlib.md5(), name=name)
        t = self.tracks[track]
        t['md5'].update(data)
        t['buffer'].extend(data)
        # Keep the last chunk until generation succeeds: cancellation cannot commit a truncated movie.
        while len(t['buffer']) > CHUNK:self._send(t, CHUNK, final=False)

    def _send(self, t, length, final):
        if not self.keep_going():raise driveupload.Stop('Preparation paused')
        start, end = t['offset'], t['offset'] + length
        body = bytes(t['buffer'][:length])
        status, headers, answer = self.drive.call('PUT', t['url'], body,
            {'Content-Range':'bytes %d-%d/%s' % (start, end - 1, str(end) if final else '*')})
        if final:
            if status not in (200, 201):raise RuntimeError('Preparation upload finish: HTTP %d' % status)
            result = json.loads(answer)
            if int(result.get('size', -1)) != end or result.get('md5Checksum', '').lower() != t['md5'].hexdigest():
                raise RuntimeError('Prepared Drive file checksum differs')
            t['result'] = result
        elif status != 308 or driveupload._next_offset(headers) != end:
            raise RuntimeError('Preparation upload did not acknowledge its byte range')
        del t['buffer'][:length]
        t['offset'] = end

    def finish(self):
        # Finish sidecars first. A failed main output leaves its source intact.
        for track in sorted(self.tracks, key=lambda n:n == 0):
            t = self.tracks[track]
            self._send(t, len(t['buffer']), final=True)
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
