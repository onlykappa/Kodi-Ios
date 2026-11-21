"""Opaque full-screen pages tell the window under them to stop drawing while they are open (owner, 2026-11-21: "keep the current UI and have it
scroll smoothly"; build 621 swipe log 5b1f4222: Sports pages at 21-34 fps against Home's 60).

The Sports pages are dialogs, and Kodi draws the window under a dialog on every frame even when the dialog covers it completely. In the desktop Kodi
rig the window under Upcoming took 60 % of the drawing time and the page itself 40 % (GUI profiler, 200 frames while scrolling). Nothing visible
changes: the page is opaque. The windows portrait.py builds hide their controls while COVERED lists an open page AND a modal dialog is open
(`portrait.COVERED_CONDITION`), so a page that dies can never leave a window blank; the service also clears a stale list when no dialog is open.
"""
import contextlib
import threading
import uuid

COVERED = 'KodiIOS.Covered'   # Home window property: space-separated tokens of the open covering pages
_lock = threading.Lock()


def _home():
    import xbmcgui
    return xbmcgui.Window(10000)


def add(token, home=None):
    with _lock:
        home = home or _home()
        tokens = [t for t in home.getProperty(COVERED).split() if t != token]
        home.setProperty(COVERED, ' '.join(tokens + [token]))


def remove(token, home=None):
    with _lock:
        home = home or _home()
        tokens = [t for t in home.getProperty(COVERED).split() if t != token]
        if tokens:
            home.setProperty(COVERED, ' '.join(tokens))
        else:
            home.clearProperty(COVERED)


@contextlib.contextmanager
def covering(home=None):
    """Around an opaque page's doModal(): the window under it stops drawing until the page closes. Never raises."""
    token = uuid.uuid4().hex[:8]
    try:
        add(token, home)
    except Exception:
        token = None
    try:
        yield
    finally:
        if token:
            try:
                remove(token, home)
            except Exception:
                pass


def tidy(home, modal_open):
    """Service check: with no modal dialog open nothing can be covering, so a list left by a page that died is cleared."""
    if not modal_open and home.getProperty(COVERED):
        home.clearProperty(COVERED)
        return True
    return False
