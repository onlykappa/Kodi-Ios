"""Own Crew's normal Kodi container only while the Sports landing page is open."""
import threading
import time
import uuid

SESSION = 'KodiIOS.SportsCrewSession'
OWNER = 'KodiIOS.SportsNativeOwner'
ADDON = 'plugin.video.thecrew'
OPEN = 'open:'
CLOSED = 'closed:'


def ticket(home):
    return home.getProperty(SESSION) or None


def valid(home, value):
    # A missing ticket retains compatibility with standalone route callers.
    return value is None or (value.startswith(OPEN) and ticket(home) == value)


def cancel_current(home):
    value = ticket(home)
    if value and value.startswith(OPEN):
        home.setProperty(SESSION, CLOSED + value[len(OPEN):])


def wait_ready(home, value, xbmc, timeout=15):
    if value is None:
        return True
    until = time.monotonic() + timeout
    while valid(home, value) and not home.getProperty(OWNER):
        if xbmc.getInfoLabel('Container.PluginName') == ADDON:
            return True
        if time.monotonic() >= until:
            break
        xbmc.sleep(100)
    return False


class Context:
    """Activate the add-on without blocking the Sports dialog's UI thread."""
    def __init__(self, home, xbmc, xbmcgui):
        self.home, self.xbmc, self.xbmcgui = home, xbmc, xbmcgui
        self.value = OPEN + uuid.uuid4().hex
        self.started = self.finished = self.restored = self.dismissed = False
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.original_crew = xbmc.getInfoLabel('Container.PluginName') == ADDON

    def open(self):
        self.home.setProperty(SESSION, self.value)
        if self.original_crew or self.home.getProperty(OWNER) or self.xbmc.Player().isPlayingVideo():
            return
        if not self.xbmc.getCondVisibility('System.HasAddon(%s)' % ADDON):
            return
        threading.Thread(target=self._activate, daemon=True).start()
        # Kodi refuses to change the underlying window once a modal is open.
        # Give it a bounded head start before showing the Sports dialog.
        self.ready.wait(5)

    def _activate(self):
        with self.lock:
            if not valid(self.home, self.value):
                return
            self.started = True
        try:
            self.xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.thecrew/,return)', True)
        finally:
            with self.lock:
                self.finished = True
                self._restore_if_closed()
            self.ready.set()

    def cancel(self):
        with self.lock:
            if ticket(self.home) == self.value:
                self.home.setProperty(SESSION, CLOSED + self.value[len(OPEN):])

    def close(self):
        self.cancel()
        with self.lock:
            self.dismissed = True
            self._restore_if_closed()

    def _restore_if_closed(self):
        if self.restored or not self.started or not self.finished or not self.dismissed:
            return
        if ticket(self.home) != CLOSED + self.value[len(OPEN):]:
            return
        if self.home.getProperty(OWNER) or self.xbmc.Player().isPlayingVideo():
            return
        if self.xbmcgui.getCurrentWindowId() != 10025 or self.xbmc.getInfoLabel('Container.PluginName') != ADDON:
            return
        self.restored = True
        self.xbmc.executebuiltin('Action(Back)')
