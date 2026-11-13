"""Work never stops; it only slows down while a video or AirPlay plays (owner, build 192: "stuff should ALWAYS be moving
even if an AirPlay movie is playing, just slower"). Build 193 replaces every playback hold (service.py idle(),
preparation.paused, Sink.hold, DriveStream.hold, the AllDebrid copy's keep_going) with this one rule:

- reason() is 'airplay' while AirPlay plays, 'video' while Kodi plays a video, '' otherwise. The service tells it
  (configure) from Player.HasVideo and airplay.busy; it is never guessed from a page.
- Each worker calls Gate.after(seconds) after a piece of work that took `seconds` (a Drive block read, an upload
  piece, an AllDebrid copy piece, a converter progress tick). While slowed it rests so that it is busy only SHARE of
  the time: the line and the CPU are left to the video.
- AirPlay must not stutter: the TV reads the movie from Kodi's in-app server, whose request lines (KodiAirPlay
  "GET /video/x 206 1834567 B 412 ms") come through airplay.relay. A slow read (STRAIN_MS) cuts the share to
  STRAINED for STRAIN_HOLD seconds.
- The owner's Pause (transfer_control) is not this: it stays a real pause.
"""
import re
import threading
import time

SHARE = {'video': 0.35, 'airplay': 0.25, 'buffering': 0.05}
# Build 206 (owner, build 205: seeking an Umbrella episode "completely nearly broke the app ... it should use download
# speeds"): a share of the time still let a background read take the whole line in bursts (an AllDebrid copy read
# 32 MB in 2.4 s, 13 MB/s, while the episode played). Downloads get a speed cap while something plays, and none at all
# while Kodi buffers (after a seek, a stall): they wait until its buffer is full again. Uploads keep the time share.
CAP = {'video': 1.0 * 1024 * 1024, 'airplay': 1.0 * 1024 * 1024, 'buffering': 0.0}   # bytes/s for background downloads
HOLD = ('video', 'buffering')   # build 208: Kodi playing a video holds all background work (AirPlay only slows it)
BUFFER_WAIT = 30.0        # the longest one wait for Kodi's buffer (then a cap of 0.25 MB/s for that piece)
STRAINED = 0.08           # share while the TV's reads are slow
STRAIN_MS = 1500          # one TV read slower than this (for a sizeable range) counts as strain
STRAIN_BYTES = 256 * 1024
STRAIN_HOLD = 60
MAX_REST = 8.0            # never rest longer than this at once (a Stop or Pause is noticed within it)
WORDS = {'airplay': 'Slower while AirPlay plays', 'video': 'Slower while a video plays', 'buffering': 'Waiting while the video buffers'}
SERVED = re.compile(r'^(?:GET|HEAD) /\S+ (?:bytes=\S+ )?(\d{3}) (\d+) B (\d+) ms')

_lock = threading.Lock()
_state = {'reason': lambda: '', 'cached': '', 'at': -10.0, 'strain_until': 0.0, 'watched': False}


def configure(reason):
    """reason() -> 'airplay' | 'buffering' | 'video' | ''. Called once by the service."""
    with _lock:
        _state.update(reason=reason, at=-10.0)


def _ask():
    try:
        value = _state['reason']() or ''
    except Exception:
        value = ''
    return value if value in SHARE else ''


def reason(clock=time.monotonic):
    """Why work is slowed now ('' when it runs at full speed), checked at most once a second.

    Build 207 (build-206 log d85fe349: a season copy read AllDebrid at 1.3 MB/s with nothing playing, 13-16 MB/s in
    build 205): build 206 asks this after every 1 MB a download reads, and the answer comes from Kodi's GUI
    (Player.HasVideo, Player.Caching). In the background that call waits for Kodi's GUI lock, so each MB waited for
    it. Once watch() runs (the service starts it) the workers only read the value it keeps; nothing they call waits
    for Kodi."""
    with _lock:
        if _state['watched']:
            return _state['cached']
    now = clock()
    with _lock:
        if now - _state['at'] < 1.0:
            return _state['cached']
        _state['at'] = now
    value = _ask()
    with _lock:
        _state['cached'] = value
        return value


def watch(wait, every=1.0, log=lambda message: None):
    """The service's thread: asks reason() once a second so workers never do. wait(seconds) is True to stop.
    Each change is logged, so a slow download in a log says whether it was slowed on purpose."""
    with _lock:
        _state['watched'] = True
    last = None
    try:
        while True:
            value = _ask()
            with _lock:
                _state.update(cached=value, at=time.monotonic())
            if value != last:
                if last is not None or value:
                    log('Kodi iOS slowdown: ' + (WORDS.get(value, value) if value else 'full speed'))
                last = value
            if wait(every):
                break
    finally:
        with _lock:
            _state['watched'] = False


def holding():
    """True while Kodi itself plays a video (or buffers one): background work waits until it stops."""
    return reason() in HOLD


def preparation_holding():
    """Owner (2026-11-13): "Id like it all to be ready before i watch ... preparing in the background if im watching
    something else". Preparation keeps going while a video plays, at its share of the time (SHARE) and the download cap
    (CAP), and waits only while Kodi buffers (after a seek), so the seek stays smooth (ISSUE-136/137: the freeze was the
    buffering dialog, background work was ruled out in build 209). Copies and uploads keep HOLD."""
    return reason() == 'buffering'


def strained(now=None):
    return (time.time() if now is None else now) < _state['strain_until']


def share(why=None, now=None):
    """The share of the time a worker may be busy (1.0 at full speed)."""
    why = reason() if why is None else why
    if not why:
        return 1.0
    if why == 'airplay' and strained(now):
        return STRAINED
    return SHARE[why]


def rest_for(seconds, part):
    """How long to rest after `seconds` of work so the work takes `part` of the time."""
    if part >= 1.0 or seconds <= 0:
        return 0.0
    return min(MAX_REST, seconds * (1.0 / part - 1.0))


def note_served(lines, now=None):
    """airplay.relay's lines: a slow read of the movie by the TV marks strain. Returns True when strain was marked."""
    now = time.time() if now is None else now
    hit = False
    for line in lines or ():
        m = SERVED.match(str(line))
        if not m:
            continue
        status, size, ms = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if status in (200, 206) and size >= STRAIN_BYTES and ms >= STRAIN_MS:
            hit = True
    if hit:
        with _lock:
            _state['strain_until'] = now + STRAIN_HOLD
    return hit


class Gate(object):
    """One per worker. after(seconds): rest while slowed. sleep() is replaceable for tests; keep_going() ends a rest
    early (Stop, Pause, Kodi closing)."""
    def __init__(self, why=None, sleep=time.sleep, keep_going=lambda: True, now=None):
        self.why = why or reason
        self.sleep = sleep
        self.keep_going = keep_going
        self.now = now
        self.rested = 0.0

    def after(self, seconds, nbytes=0, download=False):
        """Rest after a piece of work. A download (nbytes read in `seconds`) also keeps under CAP while something plays,
        and waits while Kodi buffers."""
        why = self.why()
        # Build 208 (owner, build 207: "completely freezing is unacceptable ... umbrella streams downloaded movies and
        # shows everywhere everything needs to be smooth"): while Kodi plays a video every worker waits until it
        # stops (an upload, an AllDebrid copy and the converter shared the phone with a 4K episode and its seek froze
        # for 100 s). AirPlay keeps the build-193 rule (slower, never stopped): the TV plays, not the phone.
        if why in HOLD:
            waited = 0.0
            while self.keep_going() and self.why() in HOLD:
                self.sleep(1.0)
                waited += 1.0
            self.rested += waited
            return waited
        # Build 208 (owner, build 207: seeking a downloaded episode "froze the app ... did nothing for 30 seconds"; log
        # 34cd7aac: a phone-to-Drive upload kept sending 8-28 MB/s and preparation kept reading Drive while Kodi
        # buffered from 15:07:09 to 15:08:38). Every worker waits while Kodi buffers, not only downloads, and uploads
        # (download=True with the bytes sent) keep under the same cap while something plays: Wi-Fi is shared both ways.
        if why == 'buffering':
            waited = 0.0
            while waited < BUFFER_WAIT and self.keep_going() and self.why() == 'buffering':
                self.sleep(0.5)
                waited += 0.5
            self.rested += waited
            why = self.why()
            if why == 'buffering':
                why = 'video'
        wait = rest_for(seconds, share(why, self.now() if self.now else None))
        cap = CAP.get(why) if download else None
        if cap and nbytes > 0:
            wait = max(wait, min(4 * MAX_REST, nbytes / cap - seconds))
        left = wait
        while left > 0 and self.keep_going():
            step = min(1.0, left)
            self.sleep(step)
            left -= step
        self.rested += wait - max(0.0, left)
        return wait

    def timed(self, fn, *args, **kwargs):
        """Run fn, then rest for its share."""
        began = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            self.after(time.monotonic() - began)
