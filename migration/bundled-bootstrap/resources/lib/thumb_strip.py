"""The seek bar's preview strip (owner, 2026-11-23, build 676: "the photo doesn't match where the film is going"; the card now shows the real frame).

One small picture per whole percent of a title (0.jpg ... 100.jpg, 320 x 180, about 8 KB each), made by the AirPlay framework (kodi_thumbs_make: the keyframe at or
before each moment, over the remuxer's own HTTP Range reader) and kept in a folder named by a hash of the link, so no link is written down. The video controls' card
reads the picture for the percent under the finger from the playing title's folder (Home property KodiIOS.Strip); a missing picture is just the dark card.

Made quietly, never while a video plays or opens (the debrid server refuses a crowd of connections, and the player has priority), only on Wi-Fi, for the first rows of
Continue Watching, the newest first; the last KEEP_TITLES strips are kept (about 1 MB each), older ones go. A title never played from a remembered Umbrella link has
none: its card is dark with the time until its strip exists (the next time). Everything the phone does is injected, so the rules are tested here."""
import hashlib
import json
import os
import shutil
import threading
import time

COUNT = 101
WIDTH, HEIGHT, QUALITY = 320, 180, 62
PAUSE_MS = 120              # rest between pictures: the work stays gentle
KEEP_TITLES = 6
RECENT = 3                  # Continue Watching rows looked at
KEEP = 72 * 3600            # a remembered link is used this long (ios_watch_dialog.STREAM_FRESH)
AGAIN = 25 * 60             # a title whose strip could not be finished is not tried again for this long
EVERY = 10 * 60             # how often the service looks
PROPERTY = 'KodiIOS.Strip'


def key(link):
    """A name for a link that gives nothing of it away."""
    return hashlib.sha256(('kodi-ios-strip:' + str(link or '').partition('|')[0]).encode()).hexdigest()[:24]


def root_folder(translate=None):
    """Where the strips live (tests: KODI_IOS_STRIPS)."""
    override = os.environ.get('KODI_IOS_STRIPS')
    if override:
        return override
    try:
        if translate is None:
            import xbmcvfs
            translate = xbmcvfs.translatePath
        return os.path.join(translate('special://profile/addon_data/service.kodi.ios.bootstrap'), 'strips')
    except Exception:
        return None


def special_path(link):
    """The folder as the skin names it (an image path), with a closing slash."""
    return 'special://profile/addon_data/service.kodi.ios.bootstrap/strips/%s/' % key(link)


def held(folder):
    """How many pictures the folder has."""
    try:
        return sum(1 for n in range(COUNT) if os.path.exists(os.path.join(folder, '%d.jpg' % n)))
    except OSError:
        return 0


def complete(folder):
    return os.path.exists(os.path.join(folder, 'done')) and held(folder) >= COUNT


def prune(root, keep_folder=None, keep=KEEP_TITLES):
    """The newest `keep` strips stay (and keep_folder), the rest go."""
    try:
        folders = [os.path.join(root, n) for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))]
    except OSError:
        return
    folders.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    for index, folder in enumerate(folders):
        if index >= keep and folder != keep_folder:
            shutil.rmtree(folder, ignore_errors=True)


def available(lib):
    """True when the AirPlay framework can make strips (older frameworks cannot)."""
    return bool(lib) and hasattr(lib, 'kodi_thumbs_make') and hasattr(lib, 'kodi_thumbs_cancel')


def make(lib, link, root, log=lambda text: None, stop=lambda: False, poll=0.5, pause_ms=PAUSE_MS):
    """Makes (or finishes) the strip of `link`. Blocking: returns the pictures the folder holds, or -1. `stop()` true cancels at once (a video opens)."""
    import ctypes
    if not available(lib) or not root:
        return -1
    address = str(link or '').partition('|')[0]
    if not address.startswith(('http://', 'https://')):
        return -1
    folder = os.path.join(root, key(link))
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return -1
    lib.kodi_thumbs_make.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.kodi_thumbs_make.restype = ctypes.c_int
    lib.kodi_thumbs_cancel.argtypes = []
    lib.kodi_thumbs_cancel.restype = None
    finished = threading.Event()

    def watcher():
        while not finished.wait(poll):
            try:
                if stop():
                    lib.kodi_thumbs_cancel()
                    return
            except Exception:
                return
    threading.Thread(target=watcher, daemon=True).start()
    out = ctypes.create_string_buffer(300)
    began = time.monotonic()
    try:
        n = lib.kodi_thumbs_make(address.encode('utf-8'), folder.encode('utf-8'), WIDTH, HEIGHT, QUALITY, pause_ms, out, len(out))
    except Exception as error:
        log('preview strip: failed (%s)' % type(error).__name__)
        return -1
    finally:
        finished.set()
    reason, _, facts = out.value.decode('utf-8', 'replace').partition('|')
    if n < 0:
        log('preview strip: not made (%s)' % (reason or 'unknown'))
        shutil.rmtree(folder, ignore_errors=True) if not held(folder) else None
        return -1
    log('preview strip: holds %d of %d pictures (%s) in %.0f s' % (n, COUNT, facts.replace('|', ', '), time.monotonic() - began))
    prune(root, folder)
    return n


def recent_links(rows, now, limit=RECENT):
    """[link] of the first `limit` Continue Watching rows (ios_continue.entries order) with a remembered Umbrella link that Continue could still use."""
    out = []
    for row in rows[:limit]:
        stream = row.get('stream') or {}
        link = str(stream.get('url') or '')
        position, total = float(row.get('position') or 0), float(row.get('total') or 0)
        if row.get('player') != 'umbrella' or not link.startswith(('http://', 'https://')):
            continue
        if link.startswith(('http://127.0.0.1', 'http://localhost')):
            continue
        if now - float(stream.get('at') or 0) > KEEP or position < 5 or (total and position >= 0.92 * total):
            continue
        out.append(link)
    return out


def watch(rows_now, busy, wait, log, make_it, root, allowed=lambda: True, now=time.time):
    """The service's loop: every EVERY seconds, for the first rows of Continue Watching whose strip is not complete, make it (Wi-Fi, nothing playing or opening).
    wait(seconds) returns True when Kodi is closing. The log never holds an address."""
    tried = {}
    if wait(45):
        return
    while True:
        try:
            if root and not busy() and allowed():
                for link in recent_links(rows_now(), now()):
                    if busy() or not allowed():
                        break
                    folder = os.path.join(root, key(link))
                    if complete(folder) or now() - tried.get(link, 0) < AGAIN:
                        continue
                    tried[link] = now()
                    make_it(link)
                for old in [u for u in tried if now() - tried[u] > KEEP]:
                    del tried[old]
        except Exception as error:
            log('preview strip: %s' % type(error).__name__)
        if wait(EVERY):
            return


def show(home, link, root):
    """Playback of `link` began: the card reads its folder (when it has pictures); otherwise the property is cleared. True when a folder is shown."""
    try:
        if link and root and held(os.path.join(root, key(link))):
            home.setProperty(PROPERTY, special_path(link))
            return True
    except Exception:
        pass
    try:
        home.clearProperty(PROPERTY)
    except Exception:
        pass
    return False
