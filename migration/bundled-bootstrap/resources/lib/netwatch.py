"""ISSUE-271 (owner logs 4e5fb2dd and 18a4f9c7, build 424: "it did take a long time, ensure a quicker and smoother
recovery when switching from Wi-Fi to cellular or cellular to Wi-Fi").

What the logs showed: the copies carried on across the switch, but slowly. The link was read only when a copy run started
(debrid_drive.step), and a run holds whole episodes (minutes on mobile data), so the lane count and the piece sizes kept
the old link's values; the piece in flight when Wi-Fi went hung 46 s; back on Wi-Fi one lane ran for over a minute and the
pieces had to grow again from the cellular size.

This watcher reads the link every POLL seconds in its own thread. A change counts once the new link is seen twice in a
row and is not 'other' (a switch passes through moments with no address). Copy runs compare generation() with the value
they started with and end at the next piece boundary when it moved (debrid_drive), and the native piece loop starts each
link at what worked on it last time (driveupload.LinkMemory).
"""
import threading
import time

POLL = 2.0
_lock = threading.Lock()
_state = {'link': '', 'pending': '', 'generation': 0, 'changed_at': 0.0, 'started': False}


def _read():
    try:
        import cache_tune
        return cache_tune.link_kind()
    except Exception:
        return 'other'


def observe(value, now=None):
    """Feed one reading (the thread does; tests call it). Returns True when the link changed."""
    now = time.time() if now is None else now
    with _lock:
        if not value or value == 'other':
            _state['pending'] = ''
            return False
        if not _state['link']:
            _state['link'] = value
            return False
        if value == _state['link']:
            _state['pending'] = ''
            return False
        if _state['pending'] != value:
            _state['pending'] = value          # seen once: wait for the next reading
            return False
        _state.update(link=value, pending='', generation=_state['generation'] + 1, changed_at=now)
        return True


def _loop(read, sleep):
    while True:
        try:
            observe(read())
        except Exception:
            pass
        sleep(POLL)


def start(read=None, sleep=time.sleep):
    """Start the watcher once (idempotent)."""
    with _lock:
        if _state['started']:
            return
        _state['started'] = True
    threading.Thread(target=_loop, args=(read or _read, sleep), daemon=True).start()


def generation():
    start()
    with _lock:
        return _state['generation']


def link():
    start()
    with _lock:
        return _state['link'] or ''


def reset():
    """Tests: forget everything (the thread, if any, keeps running)."""
    with _lock:
        _state.update(link='', pending='', generation=0, changed_at=0.0)
