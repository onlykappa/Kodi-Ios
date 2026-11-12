"""Roadmap 1C.1: one log line per video open, tap to playing picture, so every log shows where opens are slow.

The watch add-on marks the start (Home property KodiIOS.Open = {"t": time, "via": route}); the service waits for
Kodi's video to play and logs "Kodi iOS open timing: 5.8 s via library". Only polls while a mark is set."""
import json
import time

PROPERTY = 'KodiIOS.Open'
GIVE_UP = 120.0


def mark(home, via, now=None):
    home.setProperty(PROPERTY, json.dumps({'t': time.time() if now is None else now, 'via': via}))


def check(home, playing, log, now=None):
    """Log and clear the mark once the video plays; drop a stale one. True when a mark was handled."""
    raw = home.getProperty(PROPERTY)
    if not raw:
        return False
    now = time.time() if now is None else now
    try:
        m = json.loads(raw)
        took = now - float(m['t'])
    except (ValueError, KeyError, TypeError):
        home.clearProperty(PROPERTY)
        return True
    if playing():
        log('Kodi iOS open timing: %.1f s via %s' % (took, m.get('via') or '?'))
        home.clearProperty(PROPERTY)
        return True
    if took > GIVE_UP:
        log('Kodi iOS open timing: no picture after %d s via %s' % (int(took), m.get('via') or '?'))
        home.clearProperty(PROPERTY)
        return True
    return False


def watch(home, playing, log, wait, on_open=None):
    """Service thread: 0.2 s checks while a mark is set, 1 s otherwise. on_open() runs once per new mark, before Kodi
    opens the file (roadmap 1B.3 sets the cache read factor for the current connection there)."""
    seen = None
    while True:
        raw = home.getProperty(PROPERTY)
        busy = bool(raw)
        if busy and on_open and raw != seen:
            seen = raw
            try:
                on_open()
            except Exception:
                pass
        if busy:
            check(home, playing, log)
        if wait(0.2 if busy else 1.0):
            return
