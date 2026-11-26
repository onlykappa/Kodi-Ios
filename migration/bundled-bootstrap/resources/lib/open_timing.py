"""Tap to streams-ready timing, not first-picture evidence.

Player.HasVideo/Playing become true before a decoded picture reaches the renderer.
The native renderer marker in kodi.log supplies the later presentation boundary;
never treat a zero final stage here as instant picture presentation.
Resolution is the service's 0.2 s poll. Only polls while a mark is set.
"""
import json
import time

PROPERTY = 'KodiIOS.Open'
RESOLVED = 'KodiIOS.OpenResolved'
ROUTE = 'KodiIOS.OpenRoute'     # set by remote_media.opening_log: 'cache 3/3 wait 0.1 s' or 'direct 1/3 wait 2.0 s (reason)'
TAP = 'KodiIOS.EpisodeTap'      # set by the show page's episode lists on a tap: season, episode, title, row; named in the open record, then cleared
SOURCE = 'KodiIOS.OpenSource'   # set by the service when an Umbrella source was credited: 'alldebrid|torrentio'
DETAIL = {}     # mark time -> (seconds to streams ready, stages text): kept for the one record line written at the first picture
GIVE_UP = 120.0
NAMES = (('resolved', 'resolve'), ('media', 'handoff'), ('video', 'open'))
_seen = {}      # mark time -> {'armed': {flag: True}, 'at': {flag: time}}
WAITING = {}    # mark time -> (when streams were ready, route): videos whose playback clock has not moved yet (first picture)
MOVING_GIVE_UP = 30.0   # seconds after the tap (kept for the log line)
MOVING_AFTER_READY = 20.0   # ISSUE-494: seconds after "streams ready" before a video that has not started counts as no picture
LATE = []       # fn(ok, via, seconds): told when the first picture came (ok, seconds after the tap) or never came (not ok); the source's real speed is judged here
LISTENERS = []  # fn(ok, via): told once per open that finished (streams ready) or gave up; source_speed credits the Umbrella source just chosen
RECENT = []     # roadmap 3.5: (seconds, route, stages text) of the opens since perf_summary last asked


def take():
    """The opens since the last call (for the one-minute performance line)."""
    out = list(RECENT)
    del RECENT[:]
    return out


def mark(home, via, now=None):
    home.clearProperty(RESOLVED)
    home.clearProperty(ROUTE)
    home.clearProperty(SOURCE)
    home.setProperty(PROPERTY, json.dumps({'t': time.time() if now is None else now, 'via': via}))


def stamp_resolved(home, now=None):
    """The plugin handed Kodi the address of the video."""
    home.setProperty(RESOLVED, repr(time.time() if now is None else now))


def breakdown(start, stamps, end):
    """'resolve 0.3 s, handoff 0.4 s, ...' from the seen stage times; '' when no stage was seen."""
    points = [(label, stamps[key]) for key, label in NAMES if stamps.get(key) is not None and start <= stamps[key] <= end]
    points.sort(key=lambda item: item[1])
    parts, last = [], start
    for label, at in points + [('ready', end)]:
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
        log('Kodi iOS open timing: %.1f s via %s%s' % (took, m.get('via') or '?', ' (%s)' % stages if stages else '') + ' [streams ready; first picture not measured]')
        RECENT.append((took, m.get('via') or '?', stages))
        del RECENT[:-20]
        _tell(True, m.get('via'))
        WAITING[started] = (now, m.get('via') or '?')
        DETAIL[started] = (took, stages)
        del_old(DETAIL)
        _finish(home, started)
        return True
    if took > GIVE_UP:
        seen = ', '.join('%s at %.1f s' % (key, at - started) for key, at in sorted(stamps.items(), key=lambda i: i[1]))
        log('Kodi iOS open timing: no picture after %d s via %s%s' % (int(took), m.get('via') or '?', ' (%s)' % seen if seen else ''))
        _tell(False, m.get('via'))
        _finish(home, started)
        return True
    return False


def del_old(table, keep=8):
    for old in sorted(table)[:-keep]:
        table.pop(old, None)


def record(started, via, picture, ready_after, home=None):
    """ONE line per open with the same fields every time (owner, 2026-11-24: Umbrella openings were inconsistent and the log showed a different set of lines for each),
    so a table of openings can be read straight from a log: how it was opened (Umbrella/library/Drive), which source, whether the kept first blocks were there,
    and where the time went. Fields not known read '-'."""
    def prop(name):
        try:
            return (home.getProperty(name) if home is not None else '') or '-'
        except Exception:
            return '-'
    took, stages = DETAIL.pop(started, (None, ''))
    tap = prop(TAP)
    try:
        if home is not None:
            home.clearProperty(TAP)
    except Exception:
        pass
    return ('Kodi iOS open record: via=%s | source=%s | route=%s | tap=%s | streams ready %s | stages %s | first picture %.1f s' % (
        via, prop(SOURCE), prop(ROUTE), tap, '%.1f s' % took if took is not None else '-', stages or '-', picture))


def check_moving(log, moving, now=None, home=None, alive=None):
    """Once a video that was logged as 'streams ready' has its playback clock moving, log the tap-to-picture time (owner, 2026-11-20: the open took about
    4.4 s from tap to first picture in build 615 while the line said 1.3 s). Returns True when something was logged."""
    if not WAITING:
        return False
    now = time.time() if now is None else now
    try:
        running = bool(moving())
    except Exception:
        running = False
    done = False
    for started, (ready, via) in list(WAITING.items()):
        if running:
            log('Kodi iOS open timing: first picture (playback clock moving) %.1f s after the tap via %s, %.1f s after streams ready' % (now - started, via, now - ready))
            log(record(started, via, now - started, now - ready, home))
            _tell_late(True, via, now - started)
            del WAITING[started]
            done = True
        elif alive is not None and not _safe(alive, True):
            # ISSUE-488 (owner log ff742bd7): the owner closed the player 3 s after "streams ready"; 12 s later this said "still not moving" and ranked a good
            # source last. A video that is no longer there says nothing about its source.
            log('Kodi iOS open timing: the player was closed before a picture (%d s after the tap via %s): no verdict on the source' % (int(now - started), via))
            DETAIL.pop(started, None)
            del WAITING[started]
            done = True
        elif now - max(ready, started) > MOVING_AFTER_READY and now - started > MOVING_GIVE_UP:
            log('Kodi iOS open timing: playback clock still not moving %d s after the tap via %s' % (int(now - started), via))
            DETAIL.pop(started, None)
            _tell_late(False, via, now - started)
            del WAITING[started]
            done = True
    return done


def _safe(fn, default):
    try:
        return bool(fn())
    except Exception:
        return default


def _tell_late(ok, via, seconds):
    for listener in list(LATE):
        try:
            listener(ok, via, seconds)
        except Exception:
            pass


def _tell(ok, via):
    for listener in list(LISTENERS):
        try:
            listener(ok, via)
        except Exception:
            pass


def _finish(home, started):
    _seen.pop(started, None)
    home.clearProperty(PROPERTY)
    home.clearProperty(RESOLVED)


def watch(home, playing, log, wait, on_open=None, probe=None, moving=None, alive=None):
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
        if WAITING and moving:
            check_moving(log, moving, home=home, alive=alive)
        if wait(0.2 if busy or WAITING else 1.0):
            return
