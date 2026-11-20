"""A modal busy dialog that stays up with nothing to wait for is closed (owner, 2026-11-20: "the loading circle keeps loading and it makes it so i
cant scroll or do anything").

Build 616's log: Crew's "busydialognocancel" (raised by the background source search) covered the Home screen and every tap landed on it
(`Click at ... in DialogBusy.xml ... control 0 (not handled)`, `Activate of window refused because there are active modal dialogs`). The search now
closes the dialog itself (sports_crew_routes.listing); this is the safety net for any other add-on that raises it and never lowers it: if it has been
visible for GRACE seconds while no video is opening or playing, it is closed. Nothing here ever closes the busy dialog of a video that is opening.
"""
import time

GRACE = 4.0   # seconds a busy dialog may stay up before it is closed
NAMES = ('busydialognocancel', 'busydialog')


class Watchdog:
    def __init__(self, visible, active_video, close, log=lambda text: None, clock=time.monotonic):
        self.visible, self.active_video, self.close, self.log, self.clock = visible, active_video, close, log, clock
        self.since = {}   # dialog name -> when it was first seen up

    def tick(self):
        """One look; returns the names closed."""
        now = self.clock()
        closed = []
        busy_video = False
        try:
            busy_video = bool(self.active_video())
        except Exception:
            busy_video = False
        for name in NAMES:
            try:
                up = bool(self.visible(name))
            except Exception:
                up = False
            if not up or busy_video:
                self.since.pop(name, None)
                continue
            first = self.since.setdefault(name, now)
            if now - first >= GRACE:
                self.close(name)
                self.log('busy: closed %s after %.0f s with nothing to wait for' % (name, now - first))
                self.since.pop(name, None)
                closed.append(name)
        return closed


def watch(visible, active_video, close, wait, log=lambda text: None, every=0.5):
    dog = Watchdog(visible, active_video, close, log)
    while not wait(every):
        try:
            dog.tick()
        except Exception as error:
            log('busy: watchdog failed (%s)' % type(error).__name__)
