"""Roadmap 1B.4: start reading a debrid link while Umbrella's source window is still closing.

Umbrella resolves the picked source to a stream link (AllDebrid unlock) and only then closes its window, builds the
list item and hands the link to Kodi. umbrella_recovery.remember() already sees that link the moment it is resolved.
It calls start() here, which reads the first 512 KB and the last 256 KB of the file in a background thread. That wakes
the debrid server and its CDN (DNS, TLS, the file's start and index in its cache) so Kodi's own first requests,
which arrive a moment later, are answered at once. Umbrella's resolve is untouched. Best effort: every failure is
swallowed, one warm-up at a time, at most 768 KB, and the link (it carries an account token) is never logged."""
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HEAD = 512 * 1024
TAIL = 256 * 1024
TIMEOUT = 10
RESUME = 1024 * 1024   # around the place Continue resumes at: Kodi seeks there right after its probe
KEEP = 72 * 3600      # a remembered link is used for this long (ios_watch_dialog.STREAM_FRESH)
RECENT = 3            # only the first rows of Continue Watching are warmed, never the whole history
AGAIN = 25 * 60       # a link warmed this recently is left alone
EVERY = 10 * 60       # how often the service looks

_lock = threading.Lock()
_running = [False]


def _vint(data, at, keep_marker=False):
    """(value, length) of the EBML variable-size integer at `at`, or None. Unknown sizes (all ones) come back as None."""
    if at >= len(data) or not data[at]:
        return None
    first = data[at]
    length = 9 - first.bit_length()
    if at + length > len(data):
        return None
    value = first if keep_marker else first & ((1 << (8 - length)) - 1)
    for byte in data[at + 1:at + length]:
        value = (value << 8) | byte
    if not keep_marker and value == (1 << (7 * length)) - 1:
        return None
    return value, length


def _children(data, start, end):
    """[(id, payload_start, payload_end)] of the EBML elements laid end to end in data[start:end]."""
    found, at = [], start
    while at < end:
        ident = _vint(data, at, True)
        if not ident:
            break
        size = _vint(data, at + ident[1])
        if not size:
            break
        payload = at + ident[1] + size[1]
        found.append((ident[0], payload, min(payload + size[0], end)))
        at = payload + size[0]
    return found


def _uint(data, start, end):
    return int.from_bytes(data[start:end], 'big')


def resume_offset(head, tail, size, seconds):
    """The byte offset of the Matroska cluster Kodi seeks to for `seconds`, read the way Kodi reads it: the Segment's start and time scale from the file's start
    (`head`), the Cues from its end (`tail`, the last bytes of a file of `size`). None when the file is not Matroska or its Cues are not in `tail`. Kodi seeks to the cue just before the place (rig: 30.0 s went to the 28 s cue, byte 39427588). Measured in the rig:
    a guess from the share of the file was 2.8 MB off for a 60 s clip, and the 512 KB read around it missed Kodi's own seek completely."""
    try:
        marker = head.find(b'\x18\x53\x80\x67')
        if marker < 0:
            return None
        width = _vint(head, marker + 4)
        if not width:
            return None
        segment = marker + 4 + width[1]
        scale = 1000000
        spot = head.find(b'\x2a\xd7\xb1')
        if spot >= 0:
            length = _vint(head, spot + 3)
            if length:
                scale = _uint(head, spot + 3 + length[1], spot + 3 + length[1] + length[0]) or scale
        cues = tail.rfind(b'\x1c\x53\xbb\x6b')
        if cues < 0:
            return None
        length = _vint(tail, cues + 4)
        if not length:
            return None
        begin = cues + 4 + length[1]
        best = None
        for ident, a, b in _children(tail, begin, min(begin + length[0], len(tail))):
            if ident != 0xBB:
                continue
            when = place = None
            for inner, c, d in _children(tail, a, b):
                if inner == 0xB3:
                    when = _uint(tail, c, d)
                elif inner == 0xB7:
                    for deeper, e, f in _children(tail, c, d):
                        if deeper == 0xF1:
                            place = _uint(tail, e, f)
            if when is not None and place is not None and when * scale / 1e9 <= seconds - 0.5 and (best is None or when >= best[0]):
                best = (when, place)
        if best is None:
            return None
        offset = segment + best[1]
        return offset if 0 < offset < size else None
    except Exception:
        return None


def _split(url):
    """(address, headers) from Kodi's `address|Header=value` form."""
    address, _, tail = url.partition('|')
    headers = {'Range': '', 'User-Agent': 'Kodi/21.3 (iOS)'}
    headers.update({k: v for k, v in urllib.parse.parse_qsl(tail)})
    return address, headers


def _read(url, rng, urlopen, cap=HEAD, keep=None):
    """Read up to cap bytes of the range; returns the file's size when the server says it (Content-Range), else 0. `keep` (a list) gets the bytes read."""
    address, headers = _split(url)
    headers['Range'] = rng
    request = urllib.request.Request(address, headers=headers)
    with urlopen(request, timeout=TIMEOUT) as response:
        size = 0
        try:
            size = int(str(response.headers.get('Content-Range') or '').rpartition('/')[2])
        except (ValueError, AttributeError):
            size = 0
        total = 0
        while total < cap:
            piece = response.read(64 * 1024)
            if not piece:
                break
            total += len(piece)
            if keep is not None:
                keep.append(piece)
        return size


def warm(url, size, urlopen=urllib.request.urlopen, fraction=None, seconds=None):
    """Blocking: read the start and the end of url, and the place Continue resumes at: the cluster Kodi seeks to when `seconds` is given and the file is Matroska
    (its Cues are in the end that was just read), else a guess from `fraction` (0-1). Returns the number of requests made."""
    made = 0
    try:
        head, tail = [], []
        found = _read(url, 'bytes=0-%d' % (HEAD - 1), urlopen, keep=head)
        made += 1
        size = size or found
        if size and size > HEAD + TAIL:
            _read(url, 'bytes=%d-%d' % (size - TAIL, size - 1), urlopen, TAIL, keep=tail)
            made += 1
        at = None
        if size and seconds and tail:
            at = resume_offset(b''.join(head), b''.join(tail), size, seconds)
        if at is None and size and fraction and 0 < fraction < 1:
            at = int(size * fraction)
        if at is not None and size:
            at = max(HEAD, min(at, size - TAIL - RESUME))
            if at > HEAD:
                _read(url, 'bytes=%d-%d' % (at, at + RESUME - 1), urlopen, RESUME)
                made += 1
    except Exception:
        pass
    return made


def link_answers(url, timeout=4):
    """False only when the server refuses the link (gone, or no connection); slow or busy is True. Nothing of the address is logged."""
    address, headers = _split(url)
    headers['Range'] = 'bytes=0-0'
    try:
        with urllib.request.urlopen(urllib.request.Request(address, headers=headers), timeout=timeout) as answer:
            return answer.status in (200, 206)
    except urllib.error.HTTPError as error:
        return error.code == 429 or error.code >= 500
    except (socket.timeout, TimeoutError):
        return True
    except urllib.error.URLError as error:
        return isinstance(getattr(error, 'reason', None), (socket.timeout, TimeoutError))
    except Exception:
        return False


def recent_links(rows, now, limit=RECENT):
    """The remembered Umbrella links of the first `limit` Continue Watching rows (rows: ios_continue.entries order) that Continue could still use:
    [(url, fraction, seconds)]. Rows from the library or another player, old links and rows with no place to resume are skipped."""
    out = []
    for row in rows[:limit]:
        stream = row.get('stream') or {}
        url = str(stream.get('url') or '')
        position, total = float(row.get('position') or 0), float(row.get('total') or 0)
        if row.get('player') != 'umbrella' or not url.startswith(('http://', 'https://')):
            continue
        if now - float(stream.get('at') or 0) > KEEP or position < 5 or (total and position >= 0.92 * total):
            continue
        out.append((url, position / total if total else None, position))
    return out


def start(url, size=0, urlopen=urllib.request.urlopen):
    """Warm url in a background thread; the thread (or None when not started: not http(s), or one already running)."""
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return None
    with _lock:
        if _running[0]:
            return None
        _running[0] = True

    def run():
        try:
            warm(url, int(size or 0), urlopen)
        finally:
            with _lock:
                _running[0] = False
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def watch(rows_now, busy, wait, log, now=time.time, warm_it=warm):
    """The service's loop. rows_now() gives the Continue Watching rows (newest first); busy() is true while a video plays or opens (nothing is warmed then, so
    playback never shares the phone's connection with a warm-up). Warms the first RECENT links one after the other, a link at most once per AGAIN seconds.
    wait(seconds) returns True when Kodi is closing. The log says how many links and how long, never the addresses."""
    done = {}
    if wait(20):
        return
    while True:
        try:
            if not busy():
                links = recent_links(rows_now(), now())
                started, count = time.time(), 0
                for url, fraction, seconds in links:
                    if busy():
                        break
                    if now() - done.get(url, 0) < AGAIN:
                        continue
                    done[url] = now()
                    began = time.time()
                    made = warm_it(url, 0, fraction=fraction, seconds=seconds)
                    count += 1
                    log('link warm: %d reads in %.1f s' % (made, time.time() - began))
                for old in [u for u in done if now() - done[u] > KEEP]:
                    del done[old]
        except Exception as error:
            log('link warm: %s' % type(error).__name__)
        if wait(EVERY):
            return
