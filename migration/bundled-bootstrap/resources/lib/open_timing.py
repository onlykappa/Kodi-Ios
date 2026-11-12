"""Roadmap 1C.1: one log line per video open, tap to playing picture, with where the time went.

The watch add-on marks the start (Home property KodiIOS.Open = {"t": time, "via": route}) and, on the Library route,
stamps when it handed Kodi the address (KodiIOS.OpenResolved). The service polls every 0.2 s while a mark is set and
notes when Kodi first has the item (Player.HasMedia: OpenFile began) and when its streams are ready (Player.HasVideo:
stream open, index read and probe done). One line when the picture plays:

  Kodi iOS open timing: 5.8 s via library (resolve 0.3 s, handoff 0.4 s, open 4.2 s, picture 0.9 s)

resolve = mark to the address handed to Kodi, handoff = until Kodi starts opening it, open = Kodi opening the stream
(the Drive proxy / network read, MP4 index, probe), picture = until a frame plays. Stages that could not be seen are
left out and their time joins the next one. Resolution is the 0.2 s poll. Only polls while a mark is set."""
import json
import time

PROPERTY = 'KodiIOS.Open'
RESOLVED = 'KodiIOS.OpenResolved'
GIVE_UP = 120.0
NAMES = (('resolved', 'resolve'), ('media', 'handoff'), ('video', 'open'))
_seen = {}      # mark time -> {'armed': {flag: True}, 'at': {flag: time}}


def mark(home, via, now=None):
    home.clearProperty(RESOLVED)
    home.setProperty(PROPERTY, json.dumps({'t': time.time() if now is None else now, 'via': via}))


def stamp_resolved(home, now=None):
    """The plugin handed Kodi the address of the video."""
    home.setProperty(RESOLVED, repr(time.time() if now is None else now))


def breakdown(start, stamps, end):
    """'resolve 0.3 s, handoff 0.4 s, ...' from the seen stage times; '' when no stage was seen."""
    points = [(label, stamps[key]) for key, label in NAMES if stamps.get(key) is not None and start <= stamps[key] <= end]
    points.sort(key=lambda item: item[1])
    parts, last = [], start
    for label, at in points + [('picture', end)]:
        parts.append('%s %.1f s' % (label, max(0.0, at - last)))
        last = max(last, at)
    return ', '.join(parts) if len(parts) > 1 else ''


def _note(home, probe, started, now):
    state = _seen.setdefault(started, {'armed': {}, 'at': {}})
    if len(_seen) > 8:
        for old in sorted(_seen)[:-4]:
            _seen.pop(old, None)
    try:
        flags = probe() if probe else {}
    except Exception:
        flags = {}
    for key, on in flags.items():
        if not on:
            state['armed'][key] = True                  # seen off first, so an earlier video cannot count
        elif state['armed'].get(key) and key not in state['at']:
            state['at'][key] = now
    try:
        resolved = float(home.getProperty(RESOLVED) or 0)
    except ValueError:
        resolved = 0.0
    if resolved > 0 and resolved >= started:
        state['at']['resolved'] = resolved
    return state['at']


def check(home, playing, log, now=None, probe=None):
    """Log and clear the mark once the video plays; drop a stale one. True when a mark was handled.
    probe() -> {'media': bool, 'video': bool} lets the line show the stages."""
    raw = home.getProperty(PROPERTY)
    if not raw:
        return False
    now = time.time() if now is None else now
    try:
        m = json.loads(raw)
        started = float(m['t'])
        took = now - started
    except (ValueError, KeyError, TypeError):
        home.clearProperty(PROPERTY)
        return True
    stamps = _note(home, probe, started, now)
    if playing():
        stages = breakdown(started, stamps, now)
        log('Kodi iOS open timing: %.1f s via %s%s' % (took, m.get('via') or '?', ' (%s)' % stages if stages else ''))
        _finish(home, started)
        return True
    if took > GIVE_UP:
        seen = ', '.join('%s at %.1f s' % (key, at - started) for key, at in sorted(stamps.items(), key=lambda i: i[1]))
        log('Kodi iOS open timing: no picture after %d s via %s%s' % (int(took), m.get('via') or '?', ' (%s)' % seen if seen else ''))
        _finish(home, started)
        return True
    return False


def _finish(home, started):
    _seen.pop(started, None)
    home.clearProperty(PROPERTY)
    home.clearProperty(RESOLVED)


def watch(home, playing, log, wait, on_open=None, probe=None):
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
            check(home, playing, log, probe=probe)
        if wait(0.2 if busy else 1.0):
            return
