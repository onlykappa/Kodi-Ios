"""Keeping the Drive playback cache alive while a TV is being fed (owner log f93a3233, build 657: a Drive episode cast to an Apple TV froze after 40 s).

Play on TV stops Kodi's own player, which fires Player.OnStop, and the service answered every OnStop by wiping the playback cache and stopping the filler
(drive_proxy.clear_cache): exactly when the converter starts reading the same file through the same proxy. This keeps both while AirPlay (or a TV fed by
the phone's server) is starting or running, and clears them once, when it has ended and Kodi is not playing.

Pure logic: the service passes the callables, tests pass fakes.
"""
import time

RECHECK = 2.0   # seconds between looks at whether the cast has ended


class Keep(object):
    def __init__(self, active, playing, clear, log=lambda text: None, clock=time.monotonic):
        """active() -> True while a TV is being fed or is starting; playing() -> True while Kodi plays something; clear() wipes the cache."""
        self.active, self.playing, self.clear, self.log, self.clock = active, playing, clear, log, clock
        self.kept = False   # a stop was answered with "keep" and the cache still has to be cleared when the cast ends

    def stopped(self):
        """Kodi's player stopped (Player.OnStop). Returns 'kept' or 'cleared'."""
        if self._casting():
            if not self.kept:
                self.log('Kodi iOS Drive cache: kept for the TV (Kodi stopped to hand the video over)')
            self.kept = True
            return 'kept'
        self.kept = False
        self.clear()
        return 'cleared'

    def tick(self):
        """Called every RECHECK seconds: clears a kept cache once the cast is over and nothing plays. Returns True when it cleared."""
        if not self.kept or self._casting():
            return False
        try:
            if self.playing():
                self.kept = False   # Kodi plays again (the next video); its own stop will clear
                return False
        except Exception:
            pass
        self.kept = False
        self.log('Kodi iOS Drive cache: the TV is done, cache cleared')
        self.clear()
        return True

    def _casting(self):
        try:
            return bool(self.active())
        except Exception:
            return False


# --- the cushion before the TV starts (owner log f93a3233) --------------------------------------------------------------------------------
# Build 657 told the TV to start after ONE segment (1.6 s of source reads) and the phone then made every next 6 s segment in about 6.4 s while also sending
# to the TV: no cushion, the TV starved at 40 s. Before native start, the app asks the Drive proxy to fill the file from where Kodi is and waits (bounded)
# until about 25 s of the video are already on the phone, so the converter reads the cache, not Drive, for the segments it makes first.
import json
import re
import urllib.parse

CUSHION_SECONDS = 25      # seconds of video that should be on the phone before the TV is told to start
CUSHION_LIMIT = 45        # the longest wait, in seconds; after it the TV starts anyway
CUSHION_MIN = 24 * 1024 * 1024
CUSHION_MAX = 240 * 1024 * 1024
POLL = 1.0
BACK_OFF = 0.02           # start the fill this share of the file before the estimated position (a bitrate that is not constant)
DRIVE_PATH = re.compile(r'^/drive/([^/]+)/')


def proxy_target(source):
    """(base, path) of a Drive proxy source on this phone ('http://127.0.0.1:PORT', '/drive/<id>/<name>'), or None for anything else."""
    try:
        parts = urllib.parse.urlsplit(str(source).split('|', 1)[0])
    except ValueError:
        return None
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or not parts.port or not DRIVE_PATH.match(parts.path):
        return None
    return 'http://127.0.0.1:%d' % parts.port, parts.path


def cushion_bytes(size, duration, seconds=CUSHION_SECONDS):
    """The bytes that make `seconds` of this video: size / duration * seconds, kept between sensible limits (the file's own size caps it)."""
    try:
        wanted = int(size / duration * seconds) if size and duration and duration > 0 else CUSHION_MIN
    except (TypeError, ValueError, ZeroDivisionError):
        wanted = CUSHION_MIN
    return max(1, min(int(size or CUSHION_MAX), max(CUSHION_MIN, min(CUSHION_MAX, wanted))))


def wait_for_cushion(source, position, duration, get_json, wait, log=lambda text: None, canceled=lambda: False, publish=lambda need: None):
    """Ask the proxy to fill the file from about `position` seconds and wait until the cushion is there, the limit passes, the user cancels or the proxy
    says it is not filling (not on Wi-Fi, no room, no cache). get_json(url) -> dict or raises; wait(seconds) -> True when the user cancelled or Kodi quits.
    Returns 'ready', 'timeout', 'not filling', 'canceled' or 'not a Drive source'; always logs one summary line (no ids, no links)."""
    target = proxy_target(source)
    if not target:
        return 'not a Drive source'
    base, path = target
    waited, size, need, answer = 0.0, 0, 0, {}
    at = 0
    outcome = 'timeout'
    while True:
        try:
            answer = get_json('%s%s?at=%d%s' % (base, path.replace('/drive/', '/cushion/', 1), at, '&need=%d' % need if need else '')) or {}
        except Exception:
            answer = {}
            outcome = 'not filling'
            log('Kodi iOS Play on TV: cushion: the proxy did not answer; the TV starts now')
            break
        if not answer.get('size'):
            outcome = 'not filling'
            log('Kodi iOS Play on TV: cushion: no Drive cache for this source (%s); the TV starts now' % answer.get('state', 'unknown'))
            break
        if not size:
            size = int(answer['size'])
            need = cushion_bytes(size, duration)
            try:
                share = max(0.0, min(0.999, float(position) / float(duration)))
            except (TypeError, ValueError, ZeroDivisionError):
                share = 0.0
            at = max(0, int(size * max(0.0, share - BACK_OFF)))
            need = max(1, min(need, size - at))   # near the end of the file there is less than a cushion left to have
            try:
                publish(need)   # the filler's pacing reads it while the TV is fed
            except Exception:
                pass
            continue   # ask again from the estimated byte; the first answer only told us the size
        if int(answer.get('ahead') or 0) >= need and answer.get('ready', True):   # 'ready' (when the proxy says) also needs the audio stretch ahead
            outcome = 'ready'
            break
        if str(answer.get('state', '')).startswith('filler idle') and waited >= 2 * POLL:
            outcome = 'not filling'   # asked twice and nothing is filling: not on Wi-Fi, or no room (the proxy logged why)
            break
        if waited >= CUSHION_LIMIT:
            outcome = 'timeout'
            break
        if canceled() or wait(POLL):
            outcome = 'canceled'
            break
        waited += POLL
    log('Kodi iOS Play on TV: cushion: %s, %d of %d MB ahead after %d s (%s)' % (outcome, int(answer.get('ahead') or 0) // 1048576, need // 1048576, int(waited),
                                                                                    answer.get('state', 'no answer')))
    return outcome


# --- the TV's link first (cause D of the handoff) -----------------------------------------------------------------------------------------
# The phone's radio cannot read Drive and send to the TV at full speed at once (build 657: sends of 6-8 Mbit/s while producing, 33 Mbit/s with nothing else
# running). Once the cushion is comfortably full the filler rests, and it goes on when the cushion has shrunk to about one and a half times the minimum:
# bursts of Drive reading with the TV link free in between. Production is never starved: below LOW the filler always runs.
CUSHION_PROPERTY = 'KodiIOS.CastCushion'   # Home window property: the bytes that make the cushion of the file being cast (set by cast.py)
HIGH = 3.0                                  # the filler rests when this many cushions are ahead
LOW = 1.5                                   # ... and goes on when fewer than this many are ahead
REST = 0.5                                  # seconds it sleeps between looks while resting


class Pacing(object):
    """Filler.pace: how many seconds the filler should rest before its next chunk (0 = go on). Callable as pacing(file_id, ahead_bytes)."""
    def __init__(self, casting, cushion, log=lambda text: None):
        self.casting, self.cushion, self.log = casting, cushion, log
        self.resting = False

    def __call__(self, file_id, ahead):
        try:
            if not self.casting():
                self.resting = False
                return 0
            cushion = int(self.cushion() or 0)
        except Exception:
            self.resting = False
            return 0
        if cushion <= 0:
            self.resting = False
            return 0
        if self.resting:
            if ahead < LOW * cushion:
                self.resting = False
                self.log('Kodi iOS Drive cache: the TV link has had its rest, filling again (%d MB ahead)' % (ahead // 1048576))
                return 0
            return REST
        if ahead >= HIGH * cushion:
            self.resting = True
            self.log('Kodi iOS Drive cache: %d MB ahead, resting so the TV link has the radio' % (ahead // 1048576))
            return REST
        return 0


# --- one line every 30 s while a TV is fed (so the next owner log says which cause is still true) ------------------------------------------
SEG_MADE = re.compile(r'^copy: video segment (\d+) in (\d+) ms')
SEG_SENT = re.compile(r'^GET /video/seg(\d+)\.m4s 200 (\d+) B (\d+) ms')
SEGMENT_SECONDS = 6
INTERVAL = 30.0


class CastDiag(object):
    """Counts the AirPlay server's own lines (segments made, segments sent) and says it once per INTERVAL seconds: no URLs, no ids, no tokens."""
    def __init__(self, log=lambda text: None, state=lambda: '', clock=time.monotonic):
        self.log, self.state, self.clock = log, state, clock
        self.reset()

    def reset(self):
        self.began = None
        self.made, self.sent_to = [], []
        self.top_made = self.top_sent = 0
        self.last = None

    def feed(self, lines, now=None):
        now = self.clock() if now is None else now
        for line in lines or ():
            text = str(line).strip()
            made = SEG_MADE.match(text)
            sent = SEG_SENT.match(text)
            if made:
                self.began = now if self.began is None else self.began
                self.made.append(int(made.group(2)))
                self.top_made = max(self.top_made, int(made.group(1)))
            elif sent:
                self.began = now if self.began is None else self.began
                self.sent_to.append((int(sent.group(2)), int(sent.group(3))))
                self.top_sent = max(self.top_sent, int(sent.group(1)))
            elif text.startswith(('player: closed', 'player: stopped')):
                self.reset()
        if self.began is None:
            return None
        if self.last is None:
            self.last = now
        if now - self.last < INTERVAL:
            return None
        self.last = now
        return self.emit()

    def emit(self):
        made, sent = self.made, self.sent_to
        self.made, self.sent_to = [], []
        lead = max(0, self.top_made - self.top_sent)
        parts = ['segment %d made, the TV has asked for %d: a lead of %d segments (%d s)' % (self.top_made, self.top_sent, lead, lead * SEGMENT_SECONDS)]
        if made:
            parts.append('%d made in %.1f s each on average (a segment is %d s)' % (len(made), sum(made) / len(made) / 1000.0, SEGMENT_SECONDS))
        if sent:
            rate = sum(b for b, ms in sent) * 8.0 / max(1, sum(ms for b, ms in sent)) / 1000.0
            parts.append('%d sent at %.1f Mbit/s, the slowest took %.1f s' % (len(sent), rate, max(ms for b, ms in sent) / 1000.0))
        try:
            parts.append(self.state() or '')
        except Exception:
            pass
        text = 'Kodi iOS Play on TV: cast: ' + ', '.join(p for p in parts if p)
        self.log(text)
        return text


DIAG = CastDiag()   # the service gives it a logger and the filler's state (service.py); airplay.activity() feeds it the server's lines


# --- a TV seek (owner log 4f1691fe: after every jump the converter read a cold place; segment 54 took 14 s and segment 76 took 17 s) ---------------
JUMP = re.compile(r'^seek: the receiver jumped from segment (\d+) to (\d+) \((\d+(?:\.\d+)?) s\)')


class Reseek(object):
    """When the TV jumps to another part of the video, tell the proxy to start filling there at once (no waiting: the TV is already asking)."""
    def __init__(self, fetch=None, log=lambda text: None):
        self.fetch, self.log = fetch, log
        self.source, self.duration = '', 0.0
        self.last = None

    def arm(self, source, duration):
        """Set by cast.py when a Drive source is being cast."""
        self.source, self.duration, self.last = source, float(duration or 0), None

    def disarm(self):
        self.source, self.duration, self.last = '', 0.0, None

    def feed(self, lines):
        """Returns the number of requests started (for tests)."""
        started = 0
        for line in lines or ():
            match = JUMP.match(str(line).strip())
            if not match or not self.source or self.duration <= 0 or not self.fetch:
                continue
            target = proxy_target(self.source)
            if not target:
                continue
            second = float(match.group(3))
            if self.last is not None and abs(self.last - second) < 2:
                continue   # the same jump said twice
            self.last = second
            base, path = target
            try:
                self.fetch(base, path, second, self.duration)
                started += 1
            except Exception:
                pass
        return started


def reseek_fetch(get_json, wait_thread=None):
    """The callable Reseek uses: asks the proxy for /cushion/ at the byte of `second` (size and byte estimate as wait_for_cushion makes them), in a thread."""
    import threading

    def run(base, path, second, duration):
        def work():
            try:
                url = '%s%s' % (base, path.replace('/drive/', '/cushion/', 1))
                size = int((get_json(url + '?at=0') or {}).get('size') or 0)
                if size:
                    share = max(0.0, min(0.999, second / duration))
                    get_json('%s?at=%d' % (url, int(size * max(0.0, share - BACK_OFF))))
            except Exception:
                pass
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        if wait_thread:
            thread.join(5)
    return run


SEEK = Reseek()   # cast.py arms it and gives it the fetch; airplay.activity() feeds it the server's lines
