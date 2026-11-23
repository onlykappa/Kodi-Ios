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
RESUME = 512 * 1024   # around the place Continue resumes at: Kodi seeks there right after its probe
KEEP = 72 * 3600      # a remembered link is used for this long (ios_watch_dialog.STREAM_FRESH)
RECENT = 3            # only the first rows of Continue Watching are warmed, never the whole history
AGAIN = 25 * 60       # a link warmed this recently is left alone
EVERY = 10 * 60       # how often the service looks

_lock = threading.Lock()
_running = [False]


def _split(url):
    """(address, headers) from Kodi's `address|Header=value` form."""
    address, _, tail = url.partition('|')
    headers = {'Range': '', 'User-Agent': 'Kodi/21.3 (iOS)'}
    headers.update({k: v for k, v in urllib.parse.parse_qsl(tail)})
    return address, headers


def _read(url, rng, urlopen, cap=HEAD):
    """Read up to cap bytes of the range; returns the file's size when the server says it (Content-Range), else 0."""
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
        return size


def warm(url, size, urlopen=urllib.request.urlopen, fraction=None):
    """Blocking: read the start and the end of url, and (fraction 0-1 given) the place Continue resumes at. Returns the number of requests made."""
    made = 0
    try:
        found = _read(url, 'bytes=0-%d' % (HEAD - 1), urlopen)
        made += 1
        size = size or found
        if size and size > HEAD + TAIL:
            _read(url, 'bytes=%d-%d' % (size - TAIL, size - 1), urlopen, TAIL)
            made += 1
        if size and fraction and 0 < fraction < 1:
            at = max(HEAD, min(int(size * fraction), size - TAIL - RESUME))
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
    [(url, fraction)]. Rows from the library or another player, old links and rows with no place to resume are skipped."""
    out = []
    for row in rows[:limit]:
        stream = row.get('stream') or {}
        url = str(stream.get('url') or '')
        position, total = float(row.get('position') or 0), float(row.get('total') or 0)
        if row.get('player') != 'umbrella' or not url.startswith(('http://', 'https://')):
            continue
        if now - float(stream.get('at') or 0) > KEEP or position < 5 or (total and position >= 0.92 * total):
            continue
        out.append((url, position / total if total else None))
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
                for url, fraction in links:
                    if busy():
                        break
                    if now() - done.get(url, 0) < AGAIN:
                        continue
                    done[url] = now()
                    began = time.time()
                    made = warm_it(url, 0, fraction=fraction)
                    count += 1
                    log('link warm: %d reads in %.1f s' % (made, time.time() - began))
                for old in [u for u in done if now() - done[u] > KEEP]:
                    del done[old]
        except Exception as error:
            log('link warm: %s' % type(error).__name__)
        if wait(EVERY):
            return
