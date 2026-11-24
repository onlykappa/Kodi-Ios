"""The seek bar's preview strip (owner, 2026-11-24: "ideally the seeker is instant, no loading ... plays the movie in that small box quick or slow depending on the speed of the swipe").

One small picture every 5 seconds of a title (0.jpg, 1.jpg ...: picture i is the keyframe at or before i*5 s, 256 x 144, about 5 KB), made by the AirPlay framework (the
kodi_thumbs_* session over the remuxer's own HTTP Range reader or a local file) in a folder named by a hash of the link, so no link is written down; the framework writes the
grid (step, count, seconds) to the folder's `grid` file. While a drag is on, follow() sets Home property KodiIOS.StripFrame to the NEAREST picture the phone holds for the moment
under the finger, many times a second, so the card flips through the film at the speed of the swipe and is never empty once the first picture exists; a picture that is missing
under a resting finger is made on its own (a seek and a keyframe on the open session) and takes over when it lands.

Where the pictures come from: a downloaded file is local (the whole strip in under a minute, no network); a stream is built from the playing title's link, coarse first (every
30 s, then 15 s, then 5 s) from where the person is, one picture at a time, stepping aside the moment the buffer runs low (the debrid server refuses a crowd of connections and
playback has priority). It is allowed on mobile data with a small data allowance and on Wi-Fi with a larger one (keyframes are about 8 % of a file). Before it is needed the
service also builds the first Continue Watching titles quietly on Wi-Fi when nothing plays (watch()). The last KEEP_TITLES strips are kept. The card shows a turning ring in its
middle only while no picture exists yet (Home property KodiIOS.StripBuilding). Everything the phone does is injected, so the rules are tested here."""
import bisect
import hashlib
import json
import os
import shutil
import threading
import time

STEP = 5                    # seconds between pictures (the framework decides the real grid and writes it to the folder's `grid` file)
WIDTH, HEIGHT, QUALITY = 256, 144, 58
PAUSE_MS = 120              # rest between pictures: the work stays gentle
KEEP_TITLES = 6
RECENT = 3                  # Continue Watching rows looked at
KEEP = 72 * 3600            # a remembered link is used this long (ios_watch_dialog.STREAM_FRESH)
AGAIN = 25 * 60             # a title whose strip could not be finished is not tried again for this long
EVERY = 10 * 60             # how often the service looks
PROPERTY = 'KodiIOS.Strip'
FRAME = 'KodiIOS.StripFrame'   # the picture the card shows now (a full path), or empty
BUILDING = 'KodiIOS.StripBuilding'   # set while the playing title's strip is not complete: the card shows a turning ring
MOBILE_MB, WIFI_MB = 120, 1200   # what the framework may read from the source for one title in one playback (a stream), by connection
LOCAL_PAUSE_MS = 10         # a downloaded file is local: no need to be gentle
PLAY_PAUSE_MS = 150         # rest between pictures while the title plays: gentler than when idle
RETRY = 6                   # seconds to wait before building again after the buffer ran low
GIVE_UP = 4                 # rounds in a row that added no picture (the file cannot be read, no decoder): this playback tries no more


def key(link):
    """A name for a link that gives nothing of it away. The app's own loopback proxy (a Drive copy) is named by its path, not its port, which changes at every launch."""
    address = str(link or '').partition('|')[0]
    if address.startswith(('http://127.0.0.1', 'http://localhost')):
        address = 'loopback:' + address.split('/', 3)[-1].split('?')[0]
    return hashlib.sha256(('kodi-ios-strip:' + address).encode()).hexdigest()[:24]


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


def pictures(folder):
    """The sorted picture numbers the folder has."""
    try:
        return sorted(int(n[:-4]) for n in os.listdir(folder) if n.endswith('.jpg') and n[:-4].isdigit())
    except OSError:
        return []


def held(folder):
    """How many pictures the folder has."""
    return len(pictures(folder))


def grid(folder):
    """(step, count, seconds) the framework wrote for this title, or None."""
    try:
        with open(os.path.join(folder, 'grid')) as handle:
            step, count, seconds = (int(x) for x in handle.read().split()[:3])
        return (step, count, seconds) if step > 0 and count > 1 else None
    except (OSError, ValueError):
        return None


def complete(folder):
    layout = grid(folder)
    return os.path.exists(os.path.join(folder, 'done')) and layout is not None and held(folder) >= layout[1]


def nearest(have, index):
    """The picture number in the sorted list `have` closest to `index` (the earlier one on a tie: a keyframe at or before), or None when there are none."""
    if not have:
        return None
    at = bisect.bisect_left(have, index)
    before = have[at - 1] if at > 0 else None
    after = have[at] if at < len(have) else None
    if before is None:
        return after
    if after is None or index - before <= after - index:
        return before
    return after


def clock_seconds(label):
    """Seconds in a player time label ("1:02:03", "12:34", "45"), or None."""
    try:
        parts = [int(x) for x in str(label or '').strip().split(':')]
    except ValueError:
        return None
    if not 1 <= len(parts) <= 3 or any(p < 0 for p in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


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
    return bool(lib) and all(hasattr(lib, n) for n in ('kodi_thumbs_open', 'kodi_thumbs_frame', 'kodi_thumbs_fill', 'kodi_thumbs_stop', 'kodi_thumbs_resume', 'kodi_thumbs_close'))


class Session:
    """One video kept open in the AirPlay framework (kodi_thumbs_open): its container is probed once, so a picture costs a seek and a keyframe (1-3 s on a debrid link) instead of
    the several seconds opening the file takes. fill() makes the strip in the background, frame() makes ONE picture now; they can run in different threads; stop() interrupts
    reads at once (a fill ends), resume() lets the session work again."""

    def __init__(self, lib, handle, log=lambda text: None):
        import ctypes
        self.lib, self.handle, self.log, self.closed, self.spent_mb = lib, handle, log, False, 0.0
        lib.kodi_thumbs_frame.argtypes = [ctypes.c_int64, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        lib.kodi_thumbs_frame.restype = ctypes.c_int
        lib.kodi_thumbs_fill.argtypes = [ctypes.c_int64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        lib.kodi_thumbs_fill.restype = ctypes.c_int
        for name in ('kodi_thumbs_stop', 'kodi_thumbs_resume', 'kodi_thumbs_close'):
            getattr(lib, name).argtypes = [ctypes.c_int64]
            getattr(lib, name).restype = None

    @staticmethod
    def open(lib, link, root, log=lambda text: None, duration=0):
        """The session for `link` (its folder is made), or None: an older framework, an address that is not http(s), a video this build cannot read."""
        import ctypes
        if not available(lib) or not root:
            return None
        address = str(link or '').partition('|')[0]
        if not (address.startswith(('http://', 'https://')) or address.startswith('/')):
            return None
        folder = os.path.join(root, key(link))
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            return None
        lib.kodi_thumbs_open.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        lib.kodi_thumbs_open.restype = ctypes.c_int64
        err = ctypes.create_string_buffer(200)
        began = time.monotonic()
        try:
            if hasattr(lib, 'kodi_thumbs_open2'):
                # With the length the player knows, a fragmented MP4 (a Drive copy) opens by its fragment index in about 3 s instead of reading every fragment (72 s, owner log b142eafc).
                lib.kodi_thumbs_open2.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
                lib.kodi_thumbs_open2.restype = ctypes.c_int64
                handle = lib.kodi_thumbs_open2(address.encode('utf-8'), folder.encode('utf-8'), WIDTH, HEIGHT, QUALITY, int(duration or 0), err, len(err))
            else:
                handle = lib.kodi_thumbs_open(address.encode('utf-8'), folder.encode('utf-8'), WIDTH, HEIGHT, QUALITY, err, len(err))
        except Exception as error:
            log('preview strip: failed (%s)' % type(error).__name__)
            return None
        if not handle:
            log('preview strip: not made (%s)' % (err.value.decode('utf-8', 'replace') or 'unknown'))
            if not held(folder):
                shutil.rmtree(folder, ignore_errors=True)
            return None
        log('preview strip: video opened in %.1f s' % (time.monotonic() - began))
        prune(root, folder)
        return Session(lib, handle, log)

    def frame(self, index):
        """One picture now: 1 made, 0 there already, -1 failed."""
        import ctypes
        if self.closed:
            return -1
        err = ctypes.create_string_buffer(120)
        try:
            return int(self.lib.kodi_thumbs_frame(self.handle, int(index), err, len(err)))
        except Exception:
            return -1

    def fill(self, center=-1, pause_ms=PAUSE_MS, budget_mb=0):
        """Makes the missing pictures, coarse first from picture `center`, until the session has read `budget_mb` from the source (0: no limit). Blocking. Returns the pictures
        held (-1 on failure); self.spent_mb is what the session has read so far."""
        import ctypes
        if self.closed:
            return -1
        out = ctypes.create_string_buffer(200)
        began = time.monotonic()
        try:
            n = int(self.lib.kodi_thumbs_fill(self.handle, int(pause_ms), int(center), int(budget_mb), out, len(out)))
        except Exception as error:
            self.log('preview strip: failed (%s)' % type(error).__name__)
            return -1
        said = out.value.decode('utf-8', 'replace')
        try:
            self.spent_mb = int(dict(x.split('=') for x in said.split('|')).get('bytes', 0)) / 1048576.0
        except ValueError:
            pass
        self.log('preview strip: holds %d pictures (%s) in %.0f s' % (n, said.replace('|', ', '), time.monotonic() - began))
        return n

    def stop(self):
        if not self.closed:
            self.lib.kodi_thumbs_stop(self.handle)

    def resume(self):
        if not self.closed:
            self.lib.kodi_thumbs_resume(self.handle)

    def close(self):
        if not self.closed:
            self.closed = True
            self.lib.kodi_thumbs_close(self.handle)


def make(lib, link, root, log=lambda text: None, stop=lambda: False, poll=0.5, pause_ms=PAUSE_MS, center=-1, opener=None, budget_mb=WIFI_MB, duration=0):
    """Makes (or finishes) the whole strip of `link`: open a session, fill, close. Blocking: returns the pictures the folder holds, or -1. `stop()` true ends it at once
    (a video opens). The idle pre-build of Continue Watching's first titles uses this."""
    session = opener(lib, link, root, log) if opener else Session.open(lib, link, root, log, duration=duration)
    if session is None:
        return -1
    finished = threading.Event()

    def watcher():
        while not finished.wait(poll):
            try:
                if stop():
                    session.stop()
                    return
            except Exception:
                return
    threading.Thread(target=watcher, daemon=True).start()
    try:
        n = session.fill(center, pause_ms, budget_mb)
    finally:
        finished.set()
        session.close()
    prune(root, os.path.join(root, key(link)))
    return n


def recent_rows(rows, now, limit=RECENT, drive_link=lambda row: ''):
    """[link] of the first `limit` Continue Watching rows (ios_continue.entries order) with something to build from: a remembered Umbrella link that Continue could still use, or
    (owner, 2026-11-24: "fix it for the drive") a Drive copy, whose address is the app's own proxy's (`drive_link(row)`, '' when unknown). A title that is finished or only just
    begun is skipped."""
    out = []
    for row in rows[:limit]:
        position, total = float(row.get('position') or 0), float(row.get('total') or 0)
        if position < 5 or (total and position >= 0.92 * total):
            continue
        if row.get('player') == 'drive':
            try:
                link = str(drive_link(row) or '')
            except Exception:
                link = ''
            if link.startswith('http://127.0.0.1'):
                out.append((link, int(total)))
            continue
        stream = row.get('stream') or {}
        link = str(stream.get('url') or '')
        if row.get('player') != 'umbrella' or not link.startswith(('http://', 'https://')):
            continue
        if link.startswith(('http://127.0.0.1', 'http://localhost')):
            continue
        if now - float(stream.get('at') or 0) > KEEP:
            continue
        out.append((link, int(total)))
    return out


def recent_links(rows, now, limit=RECENT, drive_link=lambda row: ''):
    """[link] of recent_rows."""
    return [link for link, _ in recent_rows(rows, now, limit, drive_link)]


def watch(rows_now, busy, wait, log, make_it, root, allowed=lambda: True, now=time.time, drive_link=lambda row: ''):
    """The service's loop: every EVERY seconds, for the first rows of Continue Watching whose strip is not complete, make it (Wi-Fi, nothing playing or opening).
    wait(seconds) returns True when Kodi is closing. The log never holds an address."""
    tried = {}
    if wait(45):
        return
    while True:
        try:
            if root and not busy() and allowed():
                for link, total in recent_rows(rows_now(), now(), drive_link=drive_link):
                    if busy() or not allowed():
                        break
                    folder = os.path.join(root, key(link))
                    if complete(folder) or now() - tried.get(link, 0) < AGAIN:
                        continue
                    tried[link] = now()
                    make_it(link, total)
                for old in [u for u in tried if now() - tried[u] > KEEP]:
                    del tried[old]
        except Exception as error:
            log('preview strip: %s' % type(error).__name__)
        if wait(EVERY):
            return


def show(home, link, root):
    """Playback of `link` began: the card's picture is cleared and the ring turns until the first picture exists. With no link (a title with no remembered link) everything is
    cleared and the card stays dark. True when there is something to show."""
    for name in (PROPERTY, FRAME, BUILDING):
        try:
            home.clearProperty(name)
        except Exception:
            pass
    try:
        address = str(link or '').partition('|')[0]
        if link and root and (address.startswith(('http://', 'https://')) or address.startswith('/')):
            home.setProperty(PROPERTY, special_path(link))
            if not complete(os.path.join(root, key(link))):
                home.setProperty(BUILDING, '1')
            return True
    except Exception:
        pass
    return False


_generation = [0]


def _seconds(duration):
    try:
        return int(duration() or 0)
    except Exception:
        return 0


def begin(home):
    """A new video began: whatever the last one was building ends (its follow() sees a newer generation) and the card is cleared at once, so it can never show another
    title's picture (owner, build 679 log 1841aa21: a downloaded movie's card showed the Umbrella episode's frames)."""
    _generation[0] += 1
    for name in (PROPERTY, FRAME, BUILDING):
        try:
            home.clearProperty(name)
        except Exception:
            pass
    return _generation[0]


SETTLE_AFTER = 10     # seconds of playback before a stream's strip starts: the player's own opening reads come first
QUIET = 4             # seconds the buffer must have been healthy
GIVE_UP_WAITING = 900  # a Drive copy that is being sought through keeps buffering: the builder waits for the first calm spell (build 682 log: 150 s was never enough)


def settled(playing, healthy, played, wait, now=time.monotonic):
    """True once the video has played SETTLE_AFTER seconds and its buffer has been healthy for QUIET seconds; False when it stops, Kodi closes or it never settles within
    GIVE_UP_WAITING seconds. (Owner, build 679 log 1841aa21: the strip's own connection, opened the moment playback began on mobile data, took 27 s to open and shared a
    1 MB/s link with the player: the first picture came after 13.5 s and a seek landed after 6 s.)"""
    began, calm = now(), None
    while playing():
        if now() - began > GIVE_UP_WAITING:
            return False
        if healthy():
            calm = calm if calm is not None else now()
            if now() - calm >= QUIET and (played() or 0) >= SETTLE_AFTER:
                return True
        else:
            calm = None
        if wait(1.0):
            return False
    return False


def source_of(playing_file, remembered, translate=lambda p: p, isfile=os.path.isfile):
    """(address, kind) the strip is made from, or (None, None). The PLAYING file is the truth: a downloaded file on the phone ('local'), a Drive copy through the app's own proxy
    ('drive': read like a stream, over the network), else the remembered debrid link of an Umbrella title ('stream'). A remembered link of another title is never used for a
    file that is playing from somewhere else."""
    name = str(playing_file or '')
    try:
        if name.startswith('special://'):
            name = translate(name)
    except Exception:
        pass
    if name.startswith('/') and isfile(name):
        return name, 'local'
    if name.startswith(('http://127.0.0.1', 'http://localhost')):
        if '/drive/' in name:
            return name, 'drive'
        remembered = str(remembered or '')
        if remembered.startswith(('http://', 'https://')) and not remembered.startswith(('http://127.0.0.1', 'http://localhost')):
            return remembered, 'stream'
        return None, None
    if name.startswith(('http://', 'https://')):
        return name, 'stream'
    remembered = str(remembered or '')
    if remembered.startswith(('http://', 'https://')) and not remembered.startswith(('http://127.0.0.1', 'http://localhost')):
        return remembered, 'stream'
    return None, None


REST = 0.2    # seconds the finger rests on a moment before its own picture is asked for
TICK = 0.05   # how often the card's picture is chosen while a drag is on
IDLE_TICK = 0.25


def follow(lib, link, root, home, log, playing, healthy, position, seeking, wait, session=None, now=time.monotonic, budget_mb=WIFI_MB, local=False, tick=TICK, listing=0.4, duration=lambda: 0):
    """For the title that plays now. Opens one session for the playback and keeps it, then:
    - builds the strip in the background (coarse first, from where the person is) while the buffer is healthy, nobody is dragging and the data allowance `budget_mb` is not spent;
    - while a drag is on, many times a second: the card's picture (Home property KodiIOS.StripFrame, a full path) is the NEAREST picture the phone holds to the moment under the
      finger, so fast swipes flip through the film and slow ones step through it, with no wait;
    - the build steps aside for a drag (its reads are interrupted), and the picture for the moment the finger RESTS on, when it is missing, is made on its own (a seek and a keyframe
      on the open session) and takes over when it lands;
    playing() false ends it (a new title does too: only the newest follow() runs); healthy() false (the buffer is low) stops the build and waits; position() is the second the
    card shows (the finger's while seeking() is true, else the player's); wait(seconds) returns True when Kodi is closing. KodiIOS.StripBuilding is set while there is no picture
    at all. `local` is a downloaded file: nothing is waited for and there is no allowance. Returns True when the strip is complete. Blocking: run it in a thread."""
    _generation[0] += 1
    mine = _generation[0]
    address = str(link or '').partition('|')[0]
    if not (address.startswith(('http://', 'https://')) or address.startswith('/')) or not root:
        return False
    folder = os.path.join(root, key(link))
    live = lambda: playing() and _generation[0] == mine
    own = session is None
    complete_now = complete(folder)
    if not complete_now:
        session = session or Session.open(lib, link, root, log, duration=_seconds(duration))
        if session is None or not live():
            if session is not None and own:
                session.close()
            return False
    pause_ms = LOCAL_PAUSE_MS if local else PLAY_PAUSE_MS
    budget = 0 if local else budget_mb
    state = {'fill': None, 'barren': 0, 'spent': False}
    cur = {'shown': None, 'index': None, 'since': 0.0, 'asked': None, 'have': [], 'listed': -1e9, 'request': None}
    quiet_since = [now()]

    def running(thread):
        return thread is not None and thread.is_alive()

    def relist(force=False):
        if force or now() - cur['listed'] >= listing:
            cur['have'], cur['listed'] = pictures(folder), now()
        return cur['have']

    def index_of(seconds):
        layout = grid(folder)
        if layout is None or seconds is None:
            return None
        step, count, _ = layout
        return max(0, min(count - 1, int(seconds // step)))

    def show_picture(n):
        if n == cur['shown']:
            return
        cur['shown'] = n
        try:
            if n is None:
                home.clearProperty(FRAME)
            else:
                home.setProperty(FRAME, special_path(link) + '%d.jpg' % n)
                home.clearProperty(BUILDING)
        except Exception:
            pass

    def start_fill():
        centre = -1
        try:
            centre = index_of(position()) or -1
        except Exception:
            pass

        def work():
            before = held(folder)
            session.fill(centre, pause_ms, budget)
            if budget and session.spent_mb >= budget:
                state['spent'] = True
            state['barren'] = state['barren'] + 1 if held(folder) <= before and live() and healthy() and not seeking() and not state['spent'] else 0
        thread = threading.Thread(target=work, daemon=True)
        state['fill'] = thread
        thread.start()

    def halt_fill():
        """Stop the build now and wait for it to end (its read is interrupted), so the session is free for a picture."""
        if running(state['fill']):
            session.stop()
            state['fill'].join(3)
            session.resume()

    def ask(n):
        def work():
            session.frame(n)
            relist(True)
        thread = threading.Thread(target=work, daemon=True)
        cur['request'] = thread
        cur['asked'] = n
        thread.start()

    done = complete_now
    try:
        while live():
            scrubbing = bool(seeking())
            have = relist()
            if scrubbing:
                quiet_since[0] = now()
                halt_fill()
                n = index_of(position())
                if n is not None:
                    if n != cur['index']:
                        cur.update(index=n, since=now(), asked=None)
                    show_picture(nearest(have, n))
                    if n not in have and now() - cur['since'] >= REST and not running(cur['request']) and cur['asked'] != n and session is not None and not done:
                        ask(n)
                elif have:
                    show_picture(nearest(have, 0))
            else:
                if cur['index'] is not None and now() - quiet_since[0] > 1.0:
                    cur.update(index=None, asked=None)
                if have and cur['shown'] is None:
                    show_picture(nearest(have, index_of(position()) or 0))
                if complete(folder):
                    done = True
                elif running(state['fill']) and not healthy():
                    halt_fill()
                elif session is not None and not running(state['fill']) and healthy() and not state['spent'] and now() - quiet_since[0] > 1.0:
                    if state['barren'] >= GIVE_UP:
                        log('preview strip: gave up for this playback (no picture could be made)')
                        break
                    start_fill()
            if wait(tick if scrubbing else IDLE_TICK):
                break
        done = done or complete(folder)
    finally:
        try:
            halt_fill()
        except Exception:
            pass
        if own and session is not None:
            session.close()
        if _generation[0] == mine:
            try:
                home.clearProperty(BUILDING)
            except Exception:
                pass
    return done
