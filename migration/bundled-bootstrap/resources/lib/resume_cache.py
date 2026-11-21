"""The opening of the last Umbrella stream, kept on the phone so Continue starts from disk (owner, build 623 log 8c570737: a second Continue of the same episode
took 10.7 s, the first 11.3 s: 1.9 s connecting to the debrid server, 5.4 s reading the file's start at about 0.5 MB/s, 3.4 s for the first picture).

When an Umbrella stream stops, the service reads a few blocks of it into this folder (the file's start, its last block, and the blocks around where the person
stopped; Wi-Fi only) and Continue's cache source starts with them in memory, so Kodi's opening reads and its resume seek are answered at once while everything
else is fetched from the link as before. One stream at a time (the last one), at most MAX_BLOCKS blocks, wiped when another is saved. The link itself is never
written down: the folder is named by a hash of it. If the folder has nothing for a link, nothing changes: Continue plays the link directly.
"""
import hashlib
import json
import os
import shutil
import threading
import time

BLOCK = 4 * 1024 * 1024        # remote_media.BLOCK: blocks are saved as that cache holds them
HEAD_BLOCKS = 6               # what Kodi's open of an MKV reads: build 639 log aec66fce had it read blocks 0, 2, 3 and 5 (offsets 0, 9 MB, 13 MB, 22 MB) before the first picture; two kept blocks left it waiting 2.9 s on the server for the rest
AROUND = 3                    # remote_media.RESUME_BLOCKS: the block at the resume point and its neighbours
MAX_BLOCKS = 12
CAPTURE_LIMIT = 90            # seconds a capture may take
_lock = threading.Lock()
_busy = [False]


def folder():
    """Where the blocks live (None outside Kodi unless KODI_IOS_RESUME_CACHE names a folder: tests)."""
    override = os.environ.get('KODI_IOS_RESUME_CACHE')
    if override:
        return override
    try:
        import xbmcvfs
        return os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap'), 'umbrella-opening')
    except Exception:
        return None


def key(link):
    """A name for a link that gives nothing of it away."""
    return hashlib.sha256(('kodi-ios-opening:' + str(link or '')).encode()).hexdigest()[:24]


def plan(size, fraction, block=BLOCK):
    """The block indexes worth keeping for a file of `size` bytes resumed at `fraction`: its start, its last block and the blocks around the resume point
    (a guess from time: the bitrate varies). Never more than MAX_BLOCKS."""
    if size <= 0:
        return []
    last = (size - 1) // block
    wanted = set(range(min(HEAD_BLOCKS, last + 1))) | {last}
    try:
        fraction = float(fraction)
    except (TypeError, ValueError):
        fraction = 0.0
    if 0 < fraction < 1:
        at = int(fraction * size) // block
        wanted |= {i for i in range(at - 1, at - 1 + AROUND) if 0 <= i <= last}
    return sorted(wanted)[:MAX_BLOCKS]


def _meta(path):
    try:
        with open(os.path.join(path, 'meta.json'), encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def ready(link, root=None):
    """True when blocks for exactly this link are on the phone (cheap: one small file)."""
    root = root or folder()
    if not root:
        return False
    meta = _meta(root)
    return bool(meta and meta.get('key') == key(link) and meta.get('size', 0) > 0 and meta.get('blocks') and meta.get('block') == BLOCK)


def store(link, size, blocks, fraction=None, root=None, now=time.time):
    """Replace what is kept with these blocks ({index: bytes}) of `link`. Incomplete blocks are not kept. Returns how many were saved."""
    root = root or folder()
    if not root or size <= 0:
        return 0
    good = {i: b for i, b in blocks.items() if len(b) == min(BLOCK, size - i * BLOCK) and 0 <= i * BLOCK < size}
    if not good:
        return 0
    with _lock:
        shutil.rmtree(root, ignore_errors=True)
        try:
            os.makedirs(root, exist_ok=True)
            for index, data in good.items():
                with open(os.path.join(root, '%d.blk' % index), 'wb') as out:
                    out.write(data)
            with open(os.path.join(root, 'meta.json'), 'w', encoding='utf-8') as out:   # last: a folder without it is nothing
                json.dump({'key': key(link), 'size': size, 'block': BLOCK, 'blocks': sorted(good), 'fraction': fraction, 'at': int(now())}, out)
        except OSError:
            shutil.rmtree(root, ignore_errors=True)
            return 0
    return len(good)


def load(link, root=None):
    """(size, {index: bytes}) kept for this link, with every block checked against its length; None when there is nothing usable."""
    root = root or folder()
    if not root or not ready(link, root):
        return None
    meta = _meta(root)
    size = int(meta['size'])
    blocks = {}
    for index in meta['blocks']:
        try:
            with open(os.path.join(root, '%d.blk' % int(index)), 'rb') as handle:
                data = handle.read()
        except (OSError, ValueError):
            continue
        if len(data) == min(BLOCK, size - int(index) * BLOCK):
            blocks[int(index)] = data
    return (size, blocks) if blocks else None


def seed(source, link, root=None):
    """Put the kept blocks into a remote_media.Foreground cache source before Kodi reads from it. Returns how many blocks went in."""
    found = load(link, root)
    if not found or getattr(source, 'block_size', BLOCK) != BLOCK:
        return 0
    size, blocks = found
    cache = source.blocks
    with cache.lock:
        cache.sizes['media'] = size
        for index, data in blocks.items():
            cache.data[('media', index)] = data
    try:
        source.answered_size = size
    except AttributeError:
        pass
    return len(blocks)


def capture(link, fraction, make_source, root=None, log=lambda text: None, clock=time.monotonic, stop=lambda: False, poll=0.2):
    """Read the plan's blocks of `link` through a cache source (`make_source(link)` -> remote_media.Foreground, several connections at once) and keep
    them. One capture at a time; returns how many blocks were kept (0: busy, nothing to keep, or it failed). `stop()` true (a new video is opening: owner, build
    639 log 9f7b4ab2, the capture's six connections were still reading the debrid server when Continue's own check of the same link timed out, and the title
    opened the slow way in 22 s): the capture lets go at once and keeps the blocks it already has."""
    with _lock:
        if _busy[0]:
            return 0
        _busy[0] = True
    began = clock()
    source = None
    try:
        source = make_source(link)
        cache = source.blocks
        cache.get('media', 0)
        size = int(cache.sizes.get('media') or 0)
        wanted = plan(size, fraction)
        meta = _meta(root or folder() or '') if (root or folder()) else None
        if meta and meta.get('key') == key(link) and meta.get('size') == size and set(wanted) <= set(meta.get('blocks') or ()):
            return 0   # already kept (the same stream stopped again near the same place)

        def one(index):
            try:
                cache.get('media', index)
            except Exception:
                pass
        threads = [threading.Thread(target=one, args=(i,), daemon=True) for i in wanted]
        for thread in threads:
            thread.start()
        yielded = False
        while any(t.is_alive() for t in threads) and clock() - began < CAPTURE_LIMIT:
            if stop():
                yielded = True
                break
            threads[0].join(poll) if threads[0].is_alive() else time.sleep(poll)
        with cache.lock:
            have = {i: cache.data.get(('media', i), b'') for i in wanted}
        saved = store(link, size, have, fraction, root)
        log('resume cache: kept %d of %d blocks (%d MiB) in %.1f s%s' % (saved, len(wanted), saved * BLOCK // (1024 * 1024), clock() - began, ' (stopped early: a video is opening)' if yielded else ''))
        return saved
    except Exception as error:
        log('resume cache: not kept (%s)' % type(error).__name__)
        return 0
    finally:
        with _lock:
            _busy[0] = False
        if source is not None:
            try:
                source.close()
            except Exception:
                pass


def capture_later(entry, make_source, wifi=lambda: True, log=lambda text: None, root=None, stop=lambda: False):
    """From the progress tracker when a title stops: if it was an Umbrella stream with a place to resume, keep its opening, in a thread, on Wi-Fi only."""
    try:
        stream = (entry or {}).get('stream') or {}
        link = str(stream.get('url') or '')
        position, total = float((entry or {}).get('position') or 0), float((entry or {}).get('total') or 0)
        if (entry or {}).get('player') != 'umbrella' or not link.startswith(('http://', 'https://')) or link.startswith(('http://127.0.0.1', 'http://localhost')) or position < 5 or total <= 0 or position >= 0.92 * total:
            return None
        if not wifi():
            return None
        thread = threading.Thread(target=capture, args=(link, position / total, make_source, root, log, time.monotonic, stop), daemon=True)
        thread.start()
        return thread
    except Exception:
        return None
