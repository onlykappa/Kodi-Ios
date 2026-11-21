"""Scroll smoothness, measured on the phone (owner, 2026-11-20: Sports Upcoming and Favourites flick choppily; Home, Movies and TV are fluid).

The frame rate Kodi reports is read five times a second and kept per window while the screen is moving: a touch is seen (no input idle for a
second), or the rate itself is at least ANIMATING. Build 619 (log d366ccf2) showed why both are needed: Kodi's idle timer never saw a touch on the
phone, while an idle page reads about 3 fps (Kodi draws only when something changes), so a rate of 15 or more means a list is scrolling or a page
is animating. Once a minute, and when the window changes, one line says how smooth each window was:

  Kodi iOS scroll: window 13005 'Home': 58 fps typical, 41 fps slowest tenth, 34 samples while moving

so a log from a short test of every page ranks them with real numbers instead of impressions. Windows with fewer than MIN samples say nothing."""
import statistics

MIN = 8
EVERY = 0.2
ANIMATING = 15.0   # fps: below this the page is idle (an idle Kodi page reads about 3 fps on the phone)


def page(window, dialog, info):
    """(id, name) of what is on top: a dialog when one is open (the Sports pages are dialogs over window 11103), named by its skin file. Build 621
    (log 5b1f4222): keyed by the window under them and named by System.CurrentWindow, every Sports line said window 11103 with a stray label."""
    top = dialog if dialog and dialog != 9999 else window
    try:
        name = info('Window(%d).Property(xmlfile)' % top) or ''
    except Exception:
        name = ''
    name = name.rsplit('/', 1)[-1]
    return top, name[:-4] if name.lower().endswith('.xml') else name


def line(window, name, samples):
    """The log line for one window's samples, or '' when there are too few to mean anything."""
    if len(samples) < MIN:
        return ''
    ordered = sorted(samples)
    return "Kodi iOS scroll: window %s%s: %d fps typical, %d fps slowest tenth, %d samples while moving" % (
        window, " '%s'" % name if name else '', round(statistics.median(ordered)), round(ordered[(len(ordered) - 1) // 10]), len(ordered))


class Probe:
    def __init__(self, fps, touched, current, log, busy=lambda: False):
        self.fps, self.touched, self.current, self.log, self.busy = fps, touched, current, log, busy
        self.samples = {}   # (window id, name) -> [fps]
        self.last = None
        self.looked, self.said, self.seen = 0, False, False

    def tick(self):
        """One sample. Never raises: a probe must not disturb the screen it measures."""
        try:
            if self.busy():
                return
            touched = bool(self.touched())
            raw = self.reading()
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0.0
            self.looked += 1
            if not touched and value < ANIMATING:
                if self.looked % 150 == 1 and not self.said:   # build 618 logged no line at all: say what the two readings were, once
                    self.said = True
                    self.log('Kodi iOS scroll probe: idle (touch reading %s, System.FPS %r)' % (touched, raw))
                return
            key = self.current()
            if self.last is not None and key != self.last:
                self.flush(self.last)
            self.last = key
            if not self.seen:
                self.seen = True
                self.log('Kodi iOS scroll probe: first moving reading System.FPS %r (%s)' % (raw, 'touch' if touched else 'animating'))
            if value > 0:
                self.samples.setdefault(key, []).append(value)
        except Exception:
            pass

    def reading(self):
        try:
            return self.fps()
        except Exception:
            return None

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
