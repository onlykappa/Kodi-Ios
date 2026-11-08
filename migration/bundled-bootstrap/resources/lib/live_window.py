"""Change a window's controls from its refresh thread only while that window is open (ISSUE-123).

Kodi frees a script window's controls when it closes (WindowXML loads its XML every time), but xbmcgui keeps the
Control objects it handed out earlier and returns them again from getControl(). Setting a bar, a width or a position
on one after the close writes into freed memory: Kodi crashes (seen in the desktop Kodi rig as a segfault in
CGUIProgressControl::SetPercentage). Window properties are safe; control calls go through `Guard.run`.

`Window.IsActive(id)` turns false as soon as the window starts closing, before Kodi frees anything; the page's own
close (`Guard.close`) takes the same lock, so a refresh can never be half-way through a control when it closes.
A skin reload (Fuse's menus are rebuilt on a first start or after an update) frees and recreates the controls of a
window that stays open, so `Guard.control` looks each control up afresh through a new xbmcgui.Window(id) wrapper
instead of the window's own cache (the way Fuse's script.skinvariables sets its sliders).
"""
import threading


class Guard:
    def __init__(self, window):
        self.window = window
        self.lock = threading.RLock()
        self.closed = False
        self.ident = None
        self.wrapper = None
        self.resolve()

    def resolve(self):
        """The page's window id. Build 207 (owner, build-206 Transfers: "46%" with the bar at the start; reproduced in
        the rig): Kodi 21's script windows have no getId(), so open() always failed and no bar, width or position was
        ever set. The id is the current dialog's (or window's), confirmed by a marker property set on this page: a
        property lives on the window, so a new xbmcgui.Window(id) wrapper reads it back only for this page."""
        if self.ident is not None:
            return self.ident
        try:
            self.ident = int(self.window.getId())
            return self.ident
        except Exception:
            pass
        try:
            import xbmcgui
            mark = 'guard.%x' % id(self)
            self.window.setProperty('kodiios.guard', mark)
            for candidate in (xbmcgui.getCurrentWindowDialogId(), xbmcgui.getCurrentWindowId()):
                try:
                    if candidate and xbmcgui.Window(int(candidate)).getProperty('kodiios.guard') == mark:
                        self.ident = int(candidate)
                        break
                except Exception:
                    pass
        except Exception:
            pass
        return self.ident

    def open(self):
        if self.closed:
            return False
        ident = self.resolve()
        if ident is None:
            return False
        try:
            import xbmc
            return bool(xbmc.getCondVisibility('Window.IsActive(%d)' % ident))
        except Exception:
            return False

    def run(self, change):
        """Run change() (it touches controls) if the window is still open. False if it was skipped or failed."""
        with self.lock:
            if not self.open():
                return False
            try:
                import xbmcgui
                # Build 207 (rig, gdb: SIGSEGV in ControlProgress_setPercent): a control taken from a wrapper that is
                # freed at once is left dangling. One fresh wrapper per change, kept until the change is over.
                self.wrapper = xbmcgui.Window(self.ident)
                change()
                return True
            except Exception:
                return False
            finally:
                self.wrapper = None

    def control(self, ident):
        """The control as Kodi has it now (call inside run())."""
        return self.wrapper.getControl(ident)

    def percent(self, ident, value):
        return self.run(lambda: self.control(ident).setPercent(float(value)))

    def close(self):
        with self.lock:
            self.closed = True
            self.window.close()
