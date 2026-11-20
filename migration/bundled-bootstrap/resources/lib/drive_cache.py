"""Playback cache for Drive videos: whole 1 MB blocks kept in the app's temporary folder while a video plays, and a background filler that
fetches the rest of the file so every seek is instant (owner, 2026-11-20: "ideally i do want instant seeking for downloaded stuff"; "have it
clean up when i exit the show or movie so its always clean").

- DiskBlocks has the same put / get / known_size as drive_proxy.Blocks, but keeps each block in its own file, at most `cap` blocks (oldest
  deleted first), and is wiped when playback stops (clear()), when the proxy starts, and by iOS if it needs the space (the folder is temporary).
- Filler reads the file from the playing position onwards (then the part before it) on its own connection, only on Wi-Fi (never on cellular),
  only when the phone has the space, and only the whole file when it fits the cap (a larger file gets a window ahead of the position).
This is the one place a Drive movie touches the phone's disk; the Drive index design's "no movie payload on disk" rule is lifted for exactly this,
by the owner's decision, with the cleanup above.
"""
import collections
import hashlib
import os
import queue
import shutil
import threading
import time

CAP_BYTES = 3 * 1024 ** 3            # the most the cache keeps on the phone
FREE_MARGIN = 2 * 1024 ** 3          # the phone must have this much free beyond what the cache may use
HEAD_BLOCKS = 24                     # a prefetched video: its first 24 MB ...
TAIL_BLOCKS = 4                      # ... and its last 4 MB (an MP4's fragment index sits there)
PIN_SECONDS = 3600                   # a prefetched video survives the current video's stop for this long
CHUNK_BLOCKS = 32                    # blocks asked of Drive in one request (each request costs 0.3-0.7 s before its first byte)
CURSORS = 4                          # read positions the filler follows at once (see Filler._follow)
NEAR_BLOCKS = 2 * CHUNK_BLOCKS       # two reads this close are the same stretch of the file
WINDOW_DIVISOR = 3                   # a file bigger than the cap is cached this fraction of the cap ahead of the position


class DiskBlocks(object):
    def __init__(self, folder, block, cap_bytes=CAP_BYTES, log=lambda text: None):
        self.folder, self.block, self.log = folder, block, log
        self.cap = max(1, cap_bytes // block)
        self.lock = threading.Lock()
        self.order = collections.OrderedDict()   # (file_id, size, index) -> None, least recently used first
        self.size = {}                           # file_id -> the size its blocks belong to
        self.pending = {}                        # blocks accepted but not yet on disk
        self.generation = 0                      # bumped by clear(): work begun before it is dropped
        self.pins = {}                           # file_id -> when its pin ends: a prefetched video that clear() keeps
        self.queue = queue.Queue(128)
        self.wipe()
        threading.Thread(target=self._writer, daemon=True).start()

    # -- paths ---------------------------------------------------------------------------------------------------------------------
    def _dir(self, file_id, size):
        return os.path.join(self.folder, '%s-%d' % (hashlib.sha1(str(file_id).encode()).hexdigest()[:16], size))

    def _path(self, file_id, size, index):
        return os.path.join(self._dir(file_id, size), '%d.blk' % index)

    def wipe(self):
        shutil.rmtree(self.folder, ignore_errors=True)
        try:
            os.makedirs(self.folder, exist_ok=True)
        except OSError:
            pass

    # -- the Blocks interface --------------------------------------------------------------------------------------------------------
    def put(self, file_id, size, index, data):
        key = (file_id, size, index)
        with self.lock:
            old = self.size.get(file_id)
            if old is not None and old != size:
                self._forget(file_id)
            self.size[file_id] = size
            if key in self.order:
                self.order.move_to_end(key)
                return
            self.pending[key] = data
            self.order[key] = None
            gone = []
            while len(self.order) > self.cap:
                dead, _ = self.order.popitem(last=False)
                self.pending.pop(dead, None)
                gone.append(dead)
            generation = self.generation
        for dead in gone:
            self._unlink(dead)
        try:
            self.queue.put_nowait((generation, key, data))
        except queue.Full:   # the disk is behind: this block simply stays uncached
            with self.lock:
                self.order.pop(key, None)
                self.pending.pop(key, None)

    def get(self, file_id, size, index):
        key = (file_id, size, index)
        with self.lock:
            if key not in self.order:
                return None
            data = self.pending.get(key)
            self.order.move_to_end(key)
        if data is not None:
            return data
        try:
            with open(self._path(*key), 'rb') as handle:
                data = handle.read()
            return data if data else None
        except OSError:
            with self.lock:
                self.order.pop(key, None)
            return None

    def known_size(self, file_id):
        with self.lock:
            return self.size.get(file_id)

    def has(self, file_id, size, index):
        with self.lock:
            return (file_id, size, index) in self.order

    def used_blocks(self):
        with self.lock:
            return len(self.order)

    # -- cleanup ---------------------------------------------------------------------------------------------------------------------
    def _forget(self, file_id):
        for key in [k for k in self.order if k[0] == file_id]:
            self.order.pop(key, None)
            self.pending.pop(key, None)
            self._unlink(key)

    def _unlink(self, key):
        try:
            os.unlink(self._path(*key))
        except OSError:
            pass

    def pin(self, file_id, until):
        with self.lock:
            self.pins[file_id] = until

    def unpin(self, file_id):
        with self.lock:
            self.pins.pop(file_id, None)

    def clear(self, keep_pins=False, now=None):
        """Playback stopped: nothing of any video stays on the phone, except (keep_pins) a video prefetched for the next play, until its pin ends."""
        now = time.time() if now is None else now
        with self.lock:
            self.generation += 1
            self.pins = {k: v for k, v in self.pins.items() if v > now} if keep_pins else {}
            keep = set(self.pins)
            doomed = [k for k in self.order if k[0] not in keep]
            for key in doomed:
                self.order.pop(key, None)
                self.pending.pop(key, None)
            for gone in [f for f in self.size if f not in keep]:
                del self.size[gone]
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        if not keep:
            self.wipe()
        else:
            for key in doomed:
                self._unlink(key)
            for entry in os.listdir(self.folder) if os.path.isdir(self.folder) else []:
                path = os.path.join(self.folder, entry)
                if not any(self._dir(k[0], k[1]) == path for k in self.order):
                    shutil.rmtree(path, ignore_errors=True)
        self.log('Kodi iOS Drive cache: cleared%s' % (' (kept %d prefetched)' % len(keep) if keep else ''))

    def _writer(self):
        while True:
            generation, key, data = self.queue.get()
            with self.lock:
                if generation != self.generation or key not in self.order:
                    continue
            try:
                os.makedirs(self._dir(key[0], key[1]), exist_ok=True)
                tmp = self._path(*key) + '.tmp'
                with open(tmp, 'wb') as handle:
                    handle.write(data)
                with self.lock:
                    stale = generation != self.generation or key not in self.order
                if stale:
                    os.unlink(tmp)
                else:
                    os.replace(tmp, self._path(*key))
                    with self.lock:
                        if generation == self.generation:
                            self.pending.pop(key, None)
            except OSError:
                with self.lock:   # no room or no folder: the block stays uncached
                    self.order.pop(key, None)
                    self.pending.pop(key, None)


class Filler(object):
    """One background reader per playing file: fetches the blocks the store does not have, from the playing position onwards."""

    def __init__(self, store, upstream, block, tee, allowed=lambda: True, cap_bytes=CAP_BYTES, log=lambda text: None, free=None):
        self.store, self.upstream, self.block, self.tee_class = store, upstream, block, tee
        self.allowed, self.cap_bytes, self.log = allowed, cap_bytes, log
        self.free = free or (lambda: shutil.disk_usage(store.folder).free)
        self.lock = threading.Lock()
        self.jobs = {}   # file_id -> {'size', 'at' (block), 'stop'}
        self.prefetching = set()   # videos being prefetched now
        self.done = threading.Event()   # set for tests when a worker has finished

    def want(self, file_id, size, position):
        """Playback is at byte `position` of the file: make sure it is being filled from there."""
        if not size or not self.allowed():
            return
        at = position // self.block
        self.store.unpin(file_id)   # it is playing now: the next stop clears it like any other
        with self.lock:
            job = self.jobs.get(file_id)
            if job and job['size'] == size:
                self._follow(job, at)   # a seek (or another track's stretch): the worker follows this position too
                return
            try:
                if self.free() < min(size, self.cap_bytes) + FREE_MARGIN:
                    return
            except OSError:
                return
            job = {'size': size, 'at': at, 'cursors': [at], 'turn': 0, 'stop': False, 'generation': self.store.generation}
            self.jobs[file_id] = job
        threading.Thread(target=self._run, args=(file_id, job), daemon=True).start()

    @staticmethod
    def _follow(job, at):
        """Keep up to CURSORS read positions. An MP4 stores its video and each audio/subtitle track in separate stretches of the file, so Kodi reads
        two or three places at once and every request tells us only one of them. With a single position the filler jumped between them on each
        request and, by the seek rule below, abandoned every fetch it had begun (build 617 log: all of a seek's Drive requests were cold, the
        connection was dropped each time); each stretch now keeps its own position and they are filled in turn."""
        cursors = job['cursors']
        for n, known in enumerate(cursors):
            if abs(known - at) <= NEAR_BLOCKS:
                del cursors[n]   # the same stretch moved on (or back a little): this position replaces it
                break
        cursors.append(at)
        del cursors[:-CURSORS]
        job['at'] = at

    @staticmethod
    def _moved_away(job, started_at):
        """True when no followed position is still near where this pass began: the viewer seeked away from it."""
        return not any(abs(known - started_at) <= CHUNK_BLOCKS for known in job.get('cursors') or [job['at']])

    def prefetch(self, file_id, size, now=None):
        """A video that may play next (the next episode, the top Continue Watching item): its start and its end are fetched once and kept past
        the current video's stop, so it opens without a Drive wait (owner, 2026-11-20). Wi-Fi only and only with room, like the filler."""
        if not size or not self.allowed():
            return False
        try:
            if self.free() < min(size, self.cap_bytes) + FREE_MARGIN:
                return False
        except OSError:
            return False
        total = (size + self.block - 1) // self.block
        now = time.time() if now is None else now
        self.store.pin(file_id, now + PIN_SECONDS)
        wanted = [(0, min(HEAD_BLOCKS, total))]
        if total > HEAD_BLOCKS:
            wanted.append((max(HEAD_BLOCKS, total - TAIL_BLOCKS), total - max(HEAD_BLOCKS, total - TAIL_BLOCKS)))
        with self.lock:   # a page loads two or three times per open (build 616 log: the same file prefetched twice a moment apart): once is enough
            if file_id in self.prefetching or all(self.store.has(file_id, size, n) for first, count in wanted for n in range(first, first + count)):
                return True
            self.prefetching.add(file_id)

        def run():
            job = {'at': 0, 'stop': False, 'generation': self.store.generation}
            try:
                for first, count in wanted:
                    last = first + count
                    while first < last and not job['stop'] and self.allowed():
                        if self.store.has(file_id, size, first):
                            first += 1
                            continue
                        run_len = 1
                        while first + run_len < last and run_len < CHUNK_BLOCKS and not self.store.has(file_id, size, first + run_len):
                            run_len += 1
                        self._fetch(file_id, size, first, run_len, job, 0)
                        if not self.store.has(file_id, size, first):
                            break
                        first += run_len
                self.log('Kodi iOS Drive cache: prefetched %s (%d of %d blocks)' % (file_id[:8], sum(1 for n in range(total) if self.store.has(file_id, size, n)), total))
            except Exception as error:
                self.log('Kodi iOS Drive cache: prefetch stopped (%s)' % type(error).__name__)
            finally:
                with self.lock:
                    self.prefetching.discard(file_id)
                self.done.set()
        threading.Thread(target=run, daemon=True).start()
        return True

    def stop_all(self):
        with self.lock:
            for job in self.jobs.values():
                job['stop'] = True
            self.jobs.clear()

    def _run(self, file_id, job):
        size, block = job['size'], self.block
        total = (size + block - 1) // block
        window = total if size <= self.cap_bytes else min(self.cap_bytes // block, max(CHUNK_BLOCKS, self.cap_bytes // block // WINDOW_DIVISOR))
        try:
            while not job['stop'] and job['generation'] == self.store.generation and self.allowed():
                cursors = list(job['cursors'])
                run = start = None
                for step in range(len(cursors)):   # the positions take turns; one with nothing left to fill is skipped
                    start = cursors[(job['turn'] + step) % len(cursors)]
                    run = self._next_run(file_id, size, start, total, window)
                    if run is not None:
                        job['turn'] = (job['turn'] + step + 1) % len(cursors)
                        break
                if run is None:
                    break
                first, count = run
                self._fetch(file_id, size, first, count, job, start)
                if not self.store.has(file_id, size, first) and not job['stop']:
                    break   # the fetch stored nothing (or the block was evicted at once): never spin on it
        except Exception as error:
            self.log('Kodi iOS Drive cache: filler stopped (%s)' % type(error).__name__)
        finally:
            with self.lock:
                if self.jobs.get(file_id) is job:
                    del self.jobs[file_id]
            self.done.set()

    def _next_run(self, file_id, size, start, total, window):
        """The first missing block from `start` (wrapping to the start of the file once), and how many missing blocks follow it, up to CHUNK_BLOCKS."""
        limit = total if total <= window else min(total, start + window)
        order = list(range(start, limit)) + (list(range(0, start)) if total <= window else [])
        for n, index in enumerate(order):
            if not self.store.has(file_id, size, index):
                count = 1
                while count < CHUNK_BLOCKS and n + count < len(order) and order[n + count] == index + count and not self.store.has(file_id, size, index + count) and index + count < total:
                    count += 1
                return index, count
        return None

    def _fetch(self, file_id, size, first, count, job, started_at):
        a = first * self.block
        b = min(size, (first + count) * self.block) - 1
        response = self.upstream.get(file_id, 'bytes=%d-%d' % (a, b))
        tee = self.tee_class(self.store, file_id, size, a)
        got = 0
        try:
            if response.status != 206:
                job['stop'] = True
                return
            read = getattr(response, 'read1', None) or response.read
            while not job['stop'] and job['generation'] == self.store.generation and self.allowed() and got < b - a + 1:
                piece = read(256 * 1024)
                if not piece:
                    break
                tee.feed(piece)
                got += len(piece)
                if self._moved_away(job, started_at):
                    break   # the viewer seeked away from where this pass began: scan again from the new position
        finally:
            try:
                response.close()
            finally:
                if got < b - a + 1:
                    self.upstream.drop()   # a half-read response cannot be reused; a fully read one keeps its connection
        if got == 0:
            job['stop'] = True   # nothing came back: do not spin
