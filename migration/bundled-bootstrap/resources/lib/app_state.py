"""Whether Kodi is on screen, and how hard background work may run (owner, build 168: "increase cpu limit to how all
other apps operate so max it out to a point that it wont fail on my device or other devices").

iOS ends an app that uses more than 80% CPU over 60 seconds while it is in the background ("exceeding limit of 80% cpu
over 60 seconds"); on screen there is no such limit. So preparation runs flat out while Kodi is open and keeps the
working thread to BACKGROUND_SHARE of a core in the background, leaving room for Kodi's other threads under 80%.
The state is read from UIApplication through the Objective-C runtime (ctypes, like phone_space). If it cannot be read,
work is paced as in the background: never a CPU-limit kill because a reading failed.
"""
import ctypes
import time

BACKGROUND_SHARE = 0.7   # build 185: iOS ends background apps over ~80% of a core for a minute; 70% keeps a margin
ACTIVE, INACTIVE, BACKGROUND = 0, 1, 2
_cache = {'at': -10.0, 'value': None}
_runtime = {}


def _read():
    if 'send' not in _runtime:
        try:
            objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
            objc.objc_getClass.restype = ctypes.c_void_p
            objc.objc_getClass.argtypes = [ctypes.c_char_p]
            objc.sel_registerName.restype = ctypes.c_void_p
            objc.sel_registerName.argtypes = [ctypes.c_char_p]
            address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
            _runtime['send'] = (objc, address)
        except (OSError, AttributeError):
            _runtime['send'] = None
    if not _runtime['send']:
        return None
    objc, address = _runtime['send']
    try:
        app_class = objc.objc_getClass(b'UIApplication')
        if not app_class:
            return None
        shared = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)(
            app_class, objc.sel_registerName(b'sharedApplication'))
        if not shared:
            return None
        return int(ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(address)(
            shared, objc.sel_registerName(b'applicationState')))
    except Exception:
        return None


def foreground(clock=time.monotonic, read=_read):
    """True while Kodi is on screen (checked at most once a second)."""
    now = clock()
    if now - _cache['at'] >= 1.0:
        _cache['value'] = read()
        _cache['at'] = now
    return _cache['value'] in (ACTIVE, INACTIVE)


class Pace(object):
    """Call tick() from a long native job's progress callback: no pause on screen; in the background, sleeps so the
    calling thread stays at about BACKGROUND_SHARE of a core."""
    def __init__(self, on_screen=foreground, cpu_clock=None, clock=time.monotonic, sleep=time.sleep):
        self.on_screen = on_screen
        # r25: the whole app's CPU time, not this thread's: off screen the picture may be decoded on the CPU by
        # several decoder threads (VideoToolbox refused, build-178 log), and iOS judges the app, not one thread.
        self.cpu_clock = cpu_clock or time.process_time
        self.clock = clock
        self.sleep = sleep
        self.window = [clock(), self.cpu_clock()]

    def tick(self):
        wall = self.clock() - self.window[0]
        if wall < 0.1:
            return 0.0
        cpu = self.cpu_clock() - self.window[1]
        pause = 0.0 if self.on_screen() else min(0.25, max(0.0, cpu / BACKGROUND_SHARE - wall))
        if pause:
            self.sleep(pause)
        self.window[:] = [self.clock(), self.cpu_clock()]
        return pause
