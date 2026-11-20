"""Scroll smoothness, measured on the phone (owner, 2026-11-20: Sports Upcoming and Favourites flick choppily; Home, Movies and TV are fluid).

While a finger is on the screen (no input idle for a second) the frame rate Kodi reports is sampled five times a second and kept per window. Once a
minute, and when the window changes, one line says how smooth each window was:

  Kodi iOS scroll: window 13005 'Home': 58 fps typical, 41 fps slowest tenth, 34 samples while touched

so a log from a short test of every page ranks them with real numbers instead of impressions. Windows with fewer than MIN samples say nothing."""
import statistics

MIN = 8
EVERY = 0.2


def line(window, name, samples):
    """The log line for one window's samples, or '' when there are too few to mean anything."""
    if len(samples) < MIN:
        return ''
    ordered = sorted(samples)
    return "Kodi iOS scroll: window %s%s: %d fps typical, %d fps slowest tenth, %d samples while touched" % (
        window, " '%s'" % name if name else '', round(statistics.median(ordered)), round(ordered[(len(ordered) - 1) // 10]), len(ordered))


class Probe:
    def __init__(self, fps, touched, current, log, busy=lambda: False):
        self.fps, self.touched, self.current, self.log, self.busy = fps, touched, current, log, busy
        self.samples = {}   # (window id, name) -> [fps]
        self.last = None

    def tick(self):
        """One sample. Never raises: a probe must not disturb the screen it measures."""
        try:
            if self.busy() or not self.touched():
                return
            key = self.current()
            if self.last is not None and key != self.last:
                self.flush(self.last)
            self.last = key
            value = float(self.fps())
            if value > 0:
                self.samples.setdefault(key, []).append(value)
        except Exception:
            pass

    def flush(self, only=None):
        for key in ([only] if only is not None else list(self.samples)):
            text = line(key[0], key[1], self.samples.pop(key, []))
            if text:
                self.log(text)


def watch(probe, wait, flush_every=60.0, step=EVERY, clock=None):
    """Service thread: sample every `step` s until Kodi stops (`wait(seconds)` is Monitor.waitForAbort); flush once a minute."""
    import time
    clock = clock or time.monotonic
    last = clock()
    while not wait(step):
        probe.tick()
        if clock() - last >= flush_every:
            probe.flush()
            last = clock()
    probe.flush()
