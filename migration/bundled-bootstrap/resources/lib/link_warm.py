"""Roadmap 1B.4: start reading a debrid link while Umbrella's source window is still closing.

Umbrella resolves the picked source to a stream link (AllDebrid unlock) and only then closes its window, builds the
list item and hands the link to Kodi. umbrella_recovery.remember() already sees that link the moment it is resolved.
It calls start() here, which reads the first 512 KB and the last 256 KB of the file in a background thread. That wakes
the debrid server and its CDN (DNS, TLS, the file's start and index in its cache) so Kodi's own first requests,
which arrive a moment later, are answered at once. Umbrella's resolve is untouched. Best effort: every failure is
swallowed, one warm-up at a time, at most 768 KB, and the link (it carries an account token) is never logged."""
import threading
import urllib.request

HEAD = 512 * 1024
TAIL = 256 * 1024
TIMEOUT = 10

_lock = threading.Lock()
_running = [False]


def _read(url, rng, urlopen):
    request = urllib.request.Request(url, headers={'Range': rng, 'User-Agent': 'Kodi/21.3 (iOS)'})
    with urlopen(request, timeout=TIMEOUT) as response:
        total = 0
        while total < HEAD:
            piece = response.read(64 * 1024)
            if not piece:
                break
            total += len(piece)


def warm(url, size, urlopen=urllib.request.urlopen):
    """Blocking: read the start and the end of url. Returns the number of requests made."""
    made = 0
    try:
        _read(url, 'bytes=0-%d' % (HEAD - 1), urlopen)
        made += 1
        if size and size > HEAD + TAIL:
            _read(url, 'bytes=%d-%d' % (size - TAIL, size - 1), urlopen)
            made += 1
    except Exception:
        pass
    return made


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
