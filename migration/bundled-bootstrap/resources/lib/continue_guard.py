"""Continue must never be a dead end (owner, build 634 log 4b37fc5b: "resuming from Umbrella fails completely after loading forever").

Continue plays the link Umbrella gave last time, directly (ios_watch_dialog.fast_stream) so it starts fast. When that link will not open (log: Kodi's open of a
debrid link sat 30 s with no data, then "Open - Error, could not open file", then a "Playback failed" box) the person was left with nothing. fast_stream now
leaves a note (Home property KodiIOS.ContinueFast: when it started and the address that does it the normal way); this watcher, in the service, looks once a
half second: playing a picture clears the note; a failure box, or LIMIT seconds with no picture, stops what is opening, closes the box and plays the same
title the normal way (TMDb Helper and Umbrella find a fresh link, which Continue then remembers). The normal way carries ios_fast=0, so it never tries the
remembered link again and cannot loop. Everything the phone does is injected, so the rules are tested here."""
import json
import time

MARK = 'KodiIOS.ContinueFast'
LIMIT = 30.0      # seconds the remembered link gets to put a picture up (a good open takes 3-12 s; Kodi itself gave up at 30; build 660 log bbd44482: 25 s of waiting, then 17 s more the normal way)
LIMIT_OPENED = 45.0   # when Kodi has opened the streams (a video stream is there) but no picture yet - it is seeking to the resume point - the open is not cut off (build 663 log 63e92ff2: cut 3 s after the streams opened)
EARLY = 8.0   # seconds before a link that the server itself refuses (gone, or no connection) is given up on; slow is not dead, so a link that still answers keeps its LIMIT
STEP = 0.5
OPENING = 'KodiIOS.ContinueOpening'   # set when a Continue/Next Episode tap starts an open (skin play_now, fast_stream): the loading circle stays up while it is set
CIRCLE_CAP = 60.0


def retry_url(params):
    """The TMDb Helper address for the same title that skips the remembered link (ios_fast=0), from fast_stream's params."""
    import urllib.parse
    keep = {'info': 'play', 'tmdb_type': params.get('tmdb_type', ''), 'tmdb_id': params.get('tmdb_id', '')}
    if params.get('tmdb_type') == 'tv':
        keep.update(season=params.get('season', ''), episode=params.get('episode', ''))
    keep.update(ios_continue='1', ios_fast='0')
    return 'plugin://plugin.video.themoviedb.helper/?' + urllib.parse.urlencode(keep)


def note(params, now=time.time, url=''):
    """The text fast_stream leaves in MARK. `url` is the remembered link, kept only so the guard can ask the server whether it still answers (never logged)."""
    return json.dumps({'at': now(), 'retry': retry_url(params), 'url': url or ''})


def decide(mark, now, playing, failure_box, opened=False, refused=False):
    """'none' (no note), 'ok' (a picture is up: note done), 'wait', or 'fallback' (failure box up, or LIMIT seconds with no picture)."""
    try:
        data = json.loads(mark or '')
        started = float(data['at'])
        address = str(data['retry'])
    except (ValueError, KeyError, TypeError):
        return 'none' if not mark else 'ok'   # a note we cannot read is cleared by the caller
    if not address.startswith('plugin://'):
        return 'ok'
    if playing:
        return 'ok'
    if failure_box or now - started >= (LIMIT_OPENED if opened else LIMIT):
        return 'fallback'
    if refused and not opened and now - started >= EARLY:
        return 'fallback'   # the server refuses the link (twice): waiting longer cannot help
    return 'wait'


def step(home, playing, failure_box, stop, close_boxes, play, log, now=time.time, opened=lambda: False, probe=None):
    """One look. Returns what was decided."""
    mark = home.getProperty(MARK)
    refused = False
    if probe is not None:
        try:
            refused = bool(probe(json.loads(mark).get('url') or ''))
        except Exception:
            refused = False
    verdict = decide(mark, now(), playing(), failure_box(), opened(), refused)
    if verdict == 'ok':
        home.clearProperty(MARK)
    elif verdict == 'fallback':
        data = json.loads(mark)
        home.clearProperty(MARK)
        log('continue guard: the remembered link did not open (%d s%s); asking Umbrella for a fresh one' % (
            now() - float(data['at']), ', failure box up' if failure_box() else ''))
        home.setProperty(OPENING, '1')   # the circle stays up through the second try
        stop()
        close_boxes()
        play(data['retry'])
    return verdict


def watch(home, playing, failure_box, stop, close_boxes, play, log, wait, now=time.time, opened=lambda: False, circle=None, probe=None):
    """The service's loop: wait(STEP) returns True when Kodi is closing."""
    while not wait(STEP):
        try:
            if home.getProperty(MARK):
                step(home, playing, failure_box, stop, close_boxes, play, log, now, opened, probe)
            if circle is not None:
                circle.tick()
        except Exception as error:
            log('continue guard: %s' % type(error).__name__)



class Circle:
    """The loading circle of a Continue open stays up until a picture is playing, the failure box shows or CIRCLE_CAP seconds pass. Owner, build 663 log 63e92ff2:
    Kodi's own busy dialog closed a second after the tap (the plugin had answered) while the video took 20 s to open, so the Home page looked idle, was scrolled
    and tapped, and a second Continue tap restarted the open. The circle is modal, so taps wait. Everything the phone does is injected."""
    def __init__(self, home, playing, failure_box, visible, raise_it, close, log=lambda text: None, now=time.time):
        self.home, self.playing, self.failure_box, self.visible, self.raise_it, self.close, self.log, self.now = home, playing, failure_box, visible, raise_it, close, log, now
        self.since = None

    def tick(self):
        """One look: 'idle', 'keep', 'playing', 'failed' or 'gave up'."""
        if not self.home.getProperty(OPENING):
            self.since = None
            return 'idle'
        if self.since is None:
            self.since = self.now()
        verdict = 'keep'
        if self.playing():
            verdict = 'playing'
        elif self.failure_box():
            verdict = 'failed'
        elif self.now() - self.since >= CIRCLE_CAP:
            verdict = 'gave up'
        if verdict != 'keep':
            self.home.clearProperty(OPENING)
            self.since = None
            self.close()
            if verdict == 'gave up':
                self.log('continue circle: no picture in %d s; the circle is closed' % CIRCLE_CAP)
            return verdict
        if not self.visible():
            self.raise_it()
        return 'keep'


class Probe:
    """Asks the debrid server, from a thread, whether the remembered link is refused (gone, or no connection); a slow answer is not a refusal. Two refusals in a
    row make `refused` true. Called once a step; it starts at most one request at a time and never blocks the guard. Nothing of the address reaches the log."""
    EVERY = 2.0

    def __init__(self, ask, now=time.time, start=None):
        import threading
        self.ask, self.now = ask, now
        self.start = start or (lambda work: threading.Thread(target=work, daemon=True).start())
        self.busy, self.misses, self.last, self.url = False, 0, float('-inf'), ''

    def __call__(self, url):
        if url != self.url:
            self.url, self.misses, self.last, self.busy = url, 0, float('-inf'), False
        if url and not self.busy and self.now() - self.last >= self.EVERY:
            self.busy, self.last = True, self.now()
            asked = url

            def work():
                try:
                    gone = self.ask(asked) is False
                except Exception:
                    gone = False
                if self.url == asked:
                    self.misses = self.misses + 1 if gone else 0
                self.busy = False
            self.start(work)
        return self.misses >= 2
