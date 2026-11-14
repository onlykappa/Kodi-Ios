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
MAIN_CHUNK = 32 * 1024 * 1024  # producer batches / existing on-disk resume pieces, not HTTP request size
# Owner log (2026-11-13): a 200 MB episode spent much of its upload at 1-4 MB pieces because every file started again at
# 1 MB and grew only after three fast pieces. What one file learned is kept here for the next (per link kind; a failed or
# timed-out piece, or a change from Wi-Fi to cellular, forgets it).
_learned = {'size': 0, 'kind': None}
_learned_lock = threading.Lock()


def _link_kind():
    try:
        import cache_tune
        return cache_tune.link_kind()
    except Exception:
        return 'other'


def learned_piece(limit):
    """The piece size the last file ended on, for this link, or 0: never above `limit`."""
    kind = _link_kind()
    with _learned_lock:
        if _learned['kind'] != kind:
            _learned.update(size=0, kind=kind)
            return 0
        return min(int(_learned['size']), limit)


def learn_piece(size):
    """A piece of `size` bytes went through well: start the next file here. 0 forgets (a failure or timeout)."""
    kind = _link_kind() if size else None
    with _learned_lock:
        if size:
            _learned.update(size=int(size), kind=kind)
        else:
            _learned.update(size=0)


AHEAD = 4   # build 185: 4 x 32 MB may wait, so a short upload stall does not stop the converter
# r30 (owner: "fix restarting when its closed and have it keep progress"): Drive can only carry on from what it
# confirmed, in 256 KiB steps, and a converter can only carry on from a mark (KodiAirPlay's safe places). So pieces end
# at the latest mark rounded down to 256 KiB, the few bytes from there to the mark are kept with the checkpoint, and
# Drive never gets past a mark the app could not make again. Far from a mark (more than MARK_CAP buffered) the movie
# goes up anyway and the next mark is used.
STEP = 256 * 1024
# Build 190 (end-to-end test of an interrupted AV1 → HEVC conversion): a re-encode only has a mark every 30 s unit,
# and 30 s of 4K HEVC is 75-300 MB. With 96 MB the movie went up past the saved mark inside every unit, so closing
# Kodi there started the movie again. 256 MB holds a unit up to ~68 Mbit/s in memory.
MARK_CAP = 256 * 1024 * 1024  # independent of adaptive HTTP pieces; retain large 4K resume windows


def parse_mark(text):
    """(offset, header lines, tfra lines) of a KodiAirPlay mark."""
    head, tfra, offset = [], [], -1
    for line in text.splitlines():
        if line.startswith('tfra '):tfra.append(line)
        else:
            head.append(line)
            if line.startswith('offset '):offset = int(line.split()[1])
    return offset, head, tfra


def mark_sides(text):
    """{sink track: bytes} of the picture subtitle files at a mark (native track i is sink track i + 1)."""
    out = {}
    for line in text.splitlines():
        if line.startswith('side '):
            _, i, n = line.split();out[int(i) + 1] = int(n)
    return out


def discard(drive, item_id):
    """Remove only an app-owned staging object. Trash still consumes Drive quota."""
    status, _, _ = drive.call('DELETE', driveupload.API+'/'+urllib.parse.quote(str(item_id),safe=''))
    if status not in (204,404):raise RuntimeError('Temporary preparation cleanup: HTTP %d'%status)


class Sink:
    def __init__(self, drive, parent, name, keep_going, on_file=lambda track,item:None, background=True, clock=time.monotonic, sleep=None,
                 hold=lambda:False, spool=None, checkpoint=None, on_checkpoint=None, keep_pieces=False):
        self.drive, self.parent, self.name, self.keep_going = drive, parent, name, keep_going
        # Owner (build 181: AirPlay of Buddy failed while Interstellar's 32 MB pieces went up, one took 94 s): while a
        # video plays, hold() is true and the pieces wait, so playback gets the whole line.
        self.hold = hold          # build 193: only the owner's Pause holds now; playback slows it (gate)
        import slowdown
        self.gate = slowdown.Gate(keep_going=lambda: not self.closed)
        self.tracks = {}
        self.on_file = on_file
        self.background, self.clock, self.sleep = background, clock, sleep
        self.closed = False
        self.sent = 0            # bytes Drive has confirmed for the movie
        self.marks = []          # (time, sent) over the last 20 s, for the upload speed
        self.upload_lock = threading.Lock()
        self.uploads = {}
        self.upload_wait = threading.Event()
        self.finishing = False
        self.made_all = False    # ISSUE-202: the converter has made every unit; what is left is the upload
        self.made = 0            # bytes of the movie the converter has handed over
        self.made_marks = []     # (time, made): how fast the converter makes the movie (shown before any upload)
        # r30: spool (a folder) keeps picture subtitle files there until the movie is done, so a mark can say how much
        # of them to keep; marks bound the movie's pieces; on_checkpoint(dict) is told what Drive holds at a mark.
        self.spool, self.on_checkpoint = spool, on_checkpoint
        self.mark = None         # (offset, full text) of the latest mark
        self.skip = 0            # bytes of the converter's output Drive already has (carrying on past a mark)
        # Build 190: a re-encoded picture does not come out the same twice, and Drive is nearly always past the last
        # mark (pieces are on their way to the next one), so a re-encode could not be carried on. With keep_pieces the
        # movie is also written, as it is made, to files of MAIN_CHUNK in `spool`; each is deleted once Drive has it
        # (at most MARK_CAP plus the AHEAD queue, ~384 MB). Every mark is saved at once, naming the files from what Drive
        # may not have up to the mark, so the next run can send Drive the rest of them and carry on from the mark.
        self.keep_pieces = bool(keep_pieces and spool)
        self.pieces = {}         # start -> [start, end, path] of kept parts of the movie
        self.tfra = []
        self.spooled = {}
        if checkpoint:
            offset, _, tfra = parse_mark(checkpoint['mark'])
            self.tfra = list(tfra)
            tail = bytes(checkpoint.get('tail') or b'')
            # skip: Drive already holds this many bytes past the mark (a copied picture comes out the same again).
            self.skip = int(checkpoint.get('skip') or 0)
            if checkpoint['offset'] + len(tail) - self.skip != offset or (self.skip and tail):
                raise ValueError('Checkpoint does not end at its mark')
            t = self._new_track(0, checkpoint['url'], checkpoint['offset'])
            t['md5'] = None      # the earlier bytes are on Drive only: Drive's checksum and verification decide
            t['buffer'].extend(tail)
            self.made = offset
            if self.keep_pieces:
                # The kept files go on from the mark: what an earlier run wrote past it is cut off.
                import os
                for start, end, path in checkpoint.get('pieces') or []:
                    if start >= offset or end <= checkpoint['offset']:
                        try:os.remove(path)
                        except OSError:pass
                        continue
                    try:
                        with open(path, 'r+b') as f:f.truncate(min(end, offset) - start)
                    except OSError:continue
                    self.pieces[start] = [start, min(end, offset), path]
            for track, length in mark_sides(checkpoint['mark']).items():
                path = self._spool_path(track)
                with open(path, 'ab') as f:f.truncate(length)
                self.spooled[track] = path

    def _spool_path(self, track):
        import os
        return os.path.join(self.spool, '%s.side%d' % (self.name, track))

    def mark_from(self, text):
        """A mark from the converter (write track -1)."""
        offset, head, tfra = parse_mark(text)
        self.tfra.extend(tfra)
        if offset > 0:self.mark = (offset, '\n'.join(head + self.tfra) + '\n')
        t = self.tracks.get(0)
        if offset > 0 and self.keep_pieces and t is not None:
            # Everything Drive may not have yet, up to the mark, is in the kept files: save the mark now.
            self._checkpoint(t['url'], offset, dict(tail=b'', mark=self.mark[1]),
                             [p for p in sorted(self.pieces.values()) if p[0] < offset])

    def _keep(self, pos, data):
        """Write the movie's bytes [pos, pos + len(data)) to the kept files (one per MAIN_CHUNK of the movie)."""
        import os
        size = MAIN_CHUNK
        while data:
            start = pos // size * size
            n = min(len(data), start + size - pos)
            part = self.pieces.get(start)
            if part is None:
                part = self.pieces[start] = [start, start, os.path.join(self.spool, '%s.piece%d' % (self.name, start))]
                open(part[2], 'wb').close()
            if part[1] != pos:raise RuntimeError('Kept movie file out of order')
            with open(part[2], 'ab') as f:f.write(data[:n])
            part[1] = pos + n
            pos += n;data = data[n:]

    def rate(self):
        """How fast the movie goes up to Drive (bytes per second over the last ~20 s)."""
        marks = list(self.marks)
        now = self.clock()
        if not marks or now - marks[0][0] < 1:return 0.0
        return (self.sent - marks[0][1]) / (now - marks[0][0])

    def stats(self):
        """Read by the independent heartbeat even when native progress is blocked on an upload."""
        with self.upload_lock:uploads=list(self.uploads.values())
        age=max((self.clock()-started for started in uploads),default=0)
        waiting=self.upload_wait.is_set() or self.finishing
        phase=('waiting_drive' if age>=10 else 'uploading') if waiting and uploads else ''
        # ISSUE-202 (build-350 log: 47 of 47 units made, then "Converting 79%" for 20 min while 0.3 MB/s pieces went
        # up): once every unit is made, the rest is the upload, and it says so with its own share.
        left=self.made-self.sent
        if self.made_all and left>0 and not phase:phase='uploading'
        out={'out_bytes':self.sent,'up_rate':self.rate(),'upload_inflight_s':round(age,1),
             'upload_pending':bool(uploads),'transfer_phase':phase}
        if self.made_all and self.made>0:out.update(upload_left=max(0,left),upload_total=self.made)
        return out

    def made_rate(self):
        """How fast the converter hands over the movie (bytes per second over the last ~20 s)."""
        marks = list(self.made_marks)
        if len(marks) < 2 or marks[-1][0] - marks[0][0] < 1:return 0.0
        return (marks[-1][1] - marks[0][1]) / (marks[-1][0] - marks[0][0])

    def _confirmed(self, t, track):
        if track != 0:return
        self.sent = t['offset']
        now = self.clock()
        if self.marks and self.marks[-1][1]==self.sent:return
        self.marks.append((now, self.sent))
        # Retain the preceding anchor, including a slow first piece, so its confirmed speed is measurable.
        old=[m for m in self.marks if now-m[0]>20]
        self.marks[:] = old[-1:]+[m for m in self.marks if now-m[0]<=20]
        hook = getattr(self, 'on_confirmed', None)   # ISSUE-232: the page's card follows the upload once the movie is made
        if hook:
            try:hook()
            except Exception:pass

    def _uploader(self, t, track=0):
        """A track's pieces, in order, to Drive. Errors are kept and raised in the converter's thread."""
        wire = t['wire']
        while True:
            try:piece = t['queue'].get(timeout=0.5)
            except queue.Empty:
                if self.closed:return
                continue
            if piece is None or self.closed:return
            piece, saved = piece
            while not self.closed and self.hold():
                time.sleep(1)
            if self.closed:return
            try:
                wire['buffer'].extend(piece)
                began = time.monotonic()
                self._send(wire, len(piece), final=False, sleep=self.sleep)
                # Build 193: while a video or AirPlay plays the movie still goes up, at a share of the line.
                self.gate.after(time.monotonic() - began)
                self._confirmed(wire, track)
                if saved:self._checkpoint(wire['url'], wire['offset'], saved)
                if track == 0 and self.keep_pieces:self._drop_confirmed(wire['offset'])
            except BaseException as error:
                t['error'] = error
                return

    def _checkpoint(self, url, offset, saved, pieces=()):
        if self.on_checkpoint is None:return
        try:self.on_checkpoint(dict(url=url, offset=offset, tail=saved['tail'], mark=saved['mark'], pieces=[list(p) for p in pieces]))
        except Exception:pass   # a checkpoint that cannot be saved only means a restart starts over

    def _drop_confirmed(self, offset):
        """Drive has the movie up to offset: kept files wholly before it go."""
        import os
        for start, part in list(self.pieces.items()):
            if start + MAIN_CHUNK <= offset:
                self.pieces.pop(start, None)
                try:os.remove(part[2])
                except OSError:pass

    def _raise(self, t):
        if t.get('error') is not None:raise t['error']

    def close(self):
        """Stop the upload thread (a failed or cancelled conversion): it ends at its next piece."""
        self.closed = True
        for t in self.tracks.values():
            if t.get('thread'):
                t['thread'].join(timeout=60)

    def _new_track(self, track, url, offset, suffix='.mp4', background=None):
        background = self.background if background is None else background
        name = self.name + suffix
        if url is None:
            status, headers, _ = self.drive.call('POST', driveupload.UPLOAD + '?uploadType=resumable&fields=id,size,md5Checksum,name',
                json.dumps({'name':name, 'parents':[self.parent]}).encode(),
                {'Content-Type':'application/json', 'X-Upload-Content-Type':'video/mp4' if track == 0 else 'application/octet-stream'})
            url = headers.get('Location') or headers.get('location')
            if status != 200 or not url:raise RuntimeError('Preparation upload start: HTTP %d' % status)
        # Build 181 (build-180 log: Interstellar's subtitle files went up 256 KB at a time in the converter's own
        # thread, 100 of its first 180 s): subtitle files go up on their own thread too, 8 MB at a time.
        self.tracks[track] = t = dict(url=url, offset=offset, queued=offset, buffer=bytearray(), md5=hashlib.md5(), name=name,
                                      chunk=(MAIN_CHUNK if track == 0 else CHUNK) if background else
                                      (CHUNK if track == 0 else 256*1024))
        t['track']=track
        if track==0:self.sent=offset;self.marks=[(self.clock(),offset)]
        if background:
            t['wire'] = dict(url=url, offset=offset, buffer=bytearray(),track=track)
            t['queue'] = queue.Queue(maxsize=AHEAD)
            t['thread'] = threading.Thread(target=self._uploader, args=(t, track), daemon=True)
            t['thread'].start()
        return t

    def _piece(self, t, track):
        """How many buffered bytes go up now (0: wait for more), and the checkpoint if the piece ends at a mark."""
        have, chunk = len(t['buffer']), t['chunk']
        if track != 0 or self.mark is None:
            return (chunk, None) if have > chunk else (0, None)
        offset, text = self.mark
        limit = (offset - t['queued']) // STEP * STEP
        if limit >= have:limit -= STEP          # the last bytes stay for the final piece
        if limit > chunk:return chunk, None
        if limit > 0 and (limit == chunk or have > chunk):   # this piece ends at the mark: a checkpoint
            tail = bytes(t['buffer'][limit:offset - t['queued']])
            return limit, dict(mark=text, tail=tail)
        if have > MARK_CAP:return chunk, None
        return 0, None

    def write(self, track, suffix, data):
        if not self.keep_going():raise driveupload.Stop('Preparation paused')
        if track != 0 and self.spool:
            # r30: picture subtitles wait on the phone (a few MB) and go up with the movie's end.
            path = self.spooled.get(track)
            if path is None:
                path = self.spooled[track] = self._spool_path(track)
                open(path, 'wb').close()
                self.suffixes = getattr(self, 'suffixes', {});self.suffixes[track] = suffix
            self.suffixes = getattr(self, 'suffixes', {});self.suffixes.setdefault(track, suffix)
            with open(path, 'ab') as f:f.write(data)
            return
        if track == 0 and self.skip:
            drop = min(self.skip, len(data));self.skip -= drop;self.made += drop;data = data[drop:]
            if not data:return
        if track not in self.tracks:self._new_track(track, None, 0, suffix)
        t = self.tracks[track]
        if t.get('queue') is not None:self._raise(t)
        if track == 0:
            self.made += len(data)
            now = self.clock()
            if not self.made_marks or now - self.made_marks[-1][0] >= 0.5:
                self.made_marks.append((now, self.made))
                self.made_marks[:] = [m for m in self.made_marks if now - m[0] <= 20]
        if t['md5'] is not None:t['md5'].update(data)
        if track == 0 and self.keep_pieces:self._keep(t['queued'] + len(t['buffer']), data)
        t['buffer'].extend(data)
        # Keep the last chunk until generation succeeds: cancellation cannot commit a truncated movie.
        while True:
            n, saved = self._piece(t, track)
            if n <= 0:break
            if t.get('queue') is None:
                self._send(t, n, final=False)
                self._confirmed(t, track)
                t['queued'] = t['offset']
                if saved:self._checkpoint(t['url'], t['offset'], saved)
                continue
            piece = bytes(t['buffer'][:n])
            if track == 0 and self.keep_pieces:saved = None   # marks are saved as they come (mark_from)
            try:
                while True:   # wait for room, but never forever: an upload error or a pause ends the wait
                    self._raise(t)
                    if not self.keep_going():raise driveupload.Stop('Preparation paused')
                    try:t['queue'].put((piece, saved), timeout=0.5);break
                    except queue.Full:self.upload_wait.set()
            finally:self.upload_wait.clear()
            del t['buffer'][:n]
            t['queued'] += n

    def _send(self, t, length, final, attempts=8, sleep=None):
        with self.upload_lock:self.uploads[id(t)]=self.clock()
        try:return self._send_parts(t,length,final,attempts,sleep)
        finally:
            with self.upload_lock:self.uploads.pop(id(t),None)

    def _send_parts(self, t, length, final, attempts=8, sleep=None):
        """Send the first `length` buffered bytes. Drive may keep only part of a chunk (308 with a shorter Range) or
        answer 5xx: what it confirmed is dropped from the buffer and the rest is sent again (owner, build 169:
        Interstellar failed after two hours on "did not acknowledge its byte range")."""
        sleep = sleep or time.sleep
        target = t['offset'] + length
        chunks=t.get('chunks')
        if chunks is None:
            # ISSUE-202: the movie's pieces may grow to 32 MB on a fast line (8 MB cost a Drive round trip per 0.6 s at
            # 14 MB/s); they still start at 1 MB and shrink toward ten seconds each on a slow one.
            chunks=t['chunks']=driveupload.StreamChunks(MAIN_CHUNK if t.get('track',0)==0 else None,MAIN_CHUNK if t.get('track',0)==0 else None)
            chunks.current=chunks.minimum  # first acknowledgement is quick even on an unknown slow uplink
            if t.get('track',0)==0:
                # ... but a line the last file already measured is not tried from 1 MB again (never below 1 MB, never above the cap).
                chunks.current=max(chunks.minimum,min(chunks.limit,learned_piece(chunks.limit)))
        failures=0
        while failures<attempts:
            if self.closed or not self.keep_going():raise driveupload.Stop('Preparation paused')
            while self.hold():
                if self.closed or not self.keep_going():raise driveupload.Stop('Preparation paused')
                time.sleep(.25)
            start = t['offset']
            remaining = target-start
            end=start+min(remaining,chunks.current)
            body=bytes(t['buffer'][:end-start])
            content_range=('bytes %d-%d/%s'%(start,end-1,str(target) if final else '*')) if remaining else 'bytes */%d'%target
            began=self.clock()
            with self.upload_lock:self.uploads[id(t)]=began
            try:status, headers, answer = self.drive.call('PUT', t['url'], body, {'Content-Range':content_range})
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                status, headers, answer = 0, {}, b''
            elapsed=max(.001,self.clock()-began)
            if final and status in (200, 201):
                result = json.loads(answer)
                if int(result.get('size', -1)) != target or (t['md5'] is not None and result.get('md5Checksum', '').lower() != t['md5'].hexdigest()):
                    raise RuntimeError('Prepared Drive file checksum differs')
                t['result'] = result
                del t['buffer'][:remaining]
                t['offset'] = target
                self._confirmed(t,t.get('track',0))
                return
            if status != 308:
                # Lost answer or a Drive hiccup: ask how far it got, then carry on from there.
                failures+=1
                # ISSUE-240 (owner log 47e2276a: ~1.3 MB/s while Drive dropped the connection 7 times, each drop sending
                # the pieces back to 1 MB and forgetting the line): a dropped piece halves the piece size once, and the
                # next file starts at the halved size; three fast pieces double it again. Only repeated drops reach 1 MB.
                chunks.current=max(chunks.minimum,(chunks.current//2)//(256*1024)*(256*1024));chunks.fast=0
                if t.get('track',0)==0:learn_piece(chunks.current)
                sleep(min(30, 2 ** (failures-1)))
                try:status, headers, answer = self.drive.call('PUT', t['url'], b'', {'Content-Range':'bytes */%s' % (str(target) if final else '*')})
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):continue
                if final and status in (200, 201):
                    result = json.loads(answer)
                    if int(result.get('size', -1)) == target and (t['md5'] is None or result.get('md5Checksum', '').lower() == t['md5'].hexdigest()):
                        t['result'] = result;del t['buffer'][:remaining];t['offset'] = target
                        self._confirmed(t,t.get('track',0));return
                    raise RuntimeError('Prepared Drive file checksum differs')
                if status != 308:continue
            got = driveupload._next_offset(headers) if headers.get('Range') or headers.get('range') else start
            if got < start or got > end:raise RuntimeError('Preparation upload offset is invalid')
            del t['buffer'][:got - start]
            t['offset'] = got
            self._confirmed(t,t.get('track',0))
            if got>start:
                chunks.observe(got-start,0,elapsed);failures=0
                if chunks.FAST<=elapsed<=chunks.SLOW and chunks.current<chunks.limit:
                    # ISSUE-246 (owner log bfde8a13: three episodes made ready at once sent 4-8 MB pieces taking 4-9 s each,
                    # ~1.3 MB/s per upload, while plain copies reached 13.6 MB/s): pieces grew only after three under 6 s,
                    # which a shared line never gives. A steady piece now grows toward about ten seconds at the speed it
                    # just had, so fewer Drive round trips; a slow piece (over 15 s) still shrinks it.
                    step=256*1024
                    steady=int((got-start)*chunks.TARGET/elapsed)//step*step
                    chunks.current=max(chunks.current,min(chunks.limit,steady))
                if t.get('track',0)==0:learn_piece(chunks.current if elapsed<chunks.SLOW else 0)
            else:failures+=1
            if got == target and not final:return
        raise RuntimeError('Preparation upload did not acknowledge its byte range')

    def finish(self):
        self.finishing=True
        # r30: picture subtitle files kept on the phone go up now, before the movie.
        for track, path in sorted(self.spooled.items()):
            if track in self.tracks:continue
            t = self._new_track(track, None, 0, getattr(self, 'suffixes', {}).get(track, '.%d.sup' % track), background=False)
            with open(path, 'rb') as f:
                while True:
                    if not self.keep_going():raise driveupload.Stop('Preparation paused')
                    block = f.read(CHUNK)
                    if not block:break
                    t['md5'].update(block);t['buffer'].extend(block)
                    while len(t['buffer']) > t['chunk']:self._send(t, t['chunk'], final=False)
        # Finish sidecars first. A failed main output leaves its source intact.
        for track in sorted(self.tracks, key=lambda n:n == 0):
            t = self.tracks[track]
            if t.get('queue') is not None:
                # Every piece handed over must be confirmed before the last one is sent.
                while True:
                    self._raise(t)
                    if not self.keep_going():raise driveupload.Stop('Preparation paused')
                    try:t['queue'].put(None,timeout=.5);break
                    except queue.Full:continue
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
        self.finishing=False
        return {str(k):t['result'] for k,t in self.tracks.items()}


def promote(drive, source, prepared, folder, staging):
    """Build 181 (owner: "we need to upload once not twice"): the verified staged movie takes the original's place.
    It moves from .Preparation into the movie's folder under the original's name (.mp4), with the preparation marker;
    then bin() sends the original to Drive's bin. replace() used to upload the whole movie a second time into the
    original's file ID. Safe to call again after a restart: a staged file already moved is only renamed/marked."""
    import prepare_downloads as prep
    status, _, body = drive.call('GET', driveupload.API + '/' + urllib.parse.quote(str(prepared['id']), safe='') +
                                 '?fields=id,name,size,md5Checksum,appProperties,parents')
    if status != 200:raise RuntimeError('Prepared Drive file check: HTTP %d' % status)
    staged = json.loads(body)
    digest = prepared['md5Checksum'].lower()
    if int(staged.get('size') or -1) != int(prepared['size']) or str(staged.get('md5Checksum', '')).lower() != digest:
        raise RuntimeError('Prepared Drive file checksum differs; original retained')
    props = dict(staged.get('appProperties') or {})
    props.update({prep.PROPERTY: prep.PROFILE, prep.CHECKSUM_PROPERTY: digest})
    move = ''
    if folder not in (staged.get('parents') or []):
        move = '&addParents=' + urllib.parse.quote(folder, safe='') + '&removeParents=' + urllib.parse.quote(staging, safe='')
    status, _, body = drive.call('PATCH', driveupload.API + '/' + urllib.parse.quote(str(prepared['id']), safe='') +
                                 '?fields=id,name,size,md5Checksum,appProperties,parents,version' + move,
                                 json.dumps({'name': source['name'].rsplit('.', 1)[0] + '.mp4', 'appProperties': props}).encode(),
                                 {'Content-Type': 'application/json'})
    if status != 200:raise RuntimeError('Prepared file move: HTTP %d' % status)
    return json.loads(body)


def bin(drive, item_id):
    """Send the original to Drive's bin (Drive empties it after 30 days); already gone is fine."""
    status, _, _ = drive.call('PATCH', driveupload.API + '/' + urllib.parse.quote(str(item_id), safe=''),
                              json.dumps({'trashed': True}).encode(), {'Content-Type': 'application/json'})
    if status not in (200, 404):raise RuntimeError('Original to the bin: HTTP %d' % status)


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
