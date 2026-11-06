"""Free phone space as the iPhone itself counts it (owner, build 160: "It says my phone has 30gb free but it has 50").

statvfs (shutil.disk_usage) counts only space that is free right now. iOS also counts space it clears on its own when an
app needs it (caches, offloaded media: "purgeable"), and Settings › General › iPhone Storage shows that larger figure.
Foundation reports it as NSURLVolumeAvailableCapacityForImportantUsageKey: the space an app may count on for something
the user asked for, which preparing a video is. Read through the Objective-C runtime with ctypes (no framework change);
anywhere else, or if anything fails, the statvfs figure.
"""
import ctypes
import shutil

KEY = 'NSURLVolumeAvailableCapacityForImportantUsageKey'
_runtime = {}


def _objc():
    """(send, cls, sel, key, push, pop) once per process, or None where there is no Objective-C runtime."""
    if 'objc' in _runtime:
        return _runtime['objc']
    found = None
    try:
        objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
        foundation = ctypes.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_autoreleasePoolPush.restype = ctypes.c_void_p
        objc.objc_autoreleasePoolPop.argtypes = [ctypes.c_void_p]
        address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value

        def send(restype, *argtypes):
            # objc_msgSend called through the exact prototype of each message (required on arm64).
            return ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(address)
        key = ctypes.c_void_p.in_dll(foundation, KEY).value
        if key:
            found = (send, lambda name: objc.objc_getClass(name.encode()), lambda name: objc.sel_registerName(name.encode()),
                     key, objc.objc_autoreleasePoolPush, objc.objc_autoreleasePoolPop)
    except (OSError, AttributeError, ValueError):
        found = None
    _runtime['objc'] = found
    return found


def important_usage(path):
    """Bytes iOS will make available at `path` for something the user asked for, or None."""
    runtime = _objc()
    if not runtime:
        return None
    send, cls, sel, key, push, pop = runtime
    pool = push()
    try:
        text = send(ctypes.c_void_p, ctypes.c_char_p)(cls('NSString'), sel('stringWithUTF8String:'), str(path).encode('utf-8'))
        url = send(ctypes.c_void_p, ctypes.c_void_p)(cls('NSURL'), sel('fileURLWithPath:'), text)
        keys = send(ctypes.c_void_p, ctypes.c_void_p)(cls('NSArray'), sel('arrayWithObject:'), key)
        values = send(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(url, sel('resourceValuesForKeys:error:'), keys, None)
        if not values:
            return None
        number = send(ctypes.c_void_p, ctypes.c_void_p)(values, sel('objectForKey:'), key)
        if not number:
            return None
        value = send(ctypes.c_longlong)(number, sel('longLongValue'))
        return value if value > 0 else None
    except Exception:
        return None
    finally:
        pop(pool)


def free(path):
    """Free space at `path` as the iPhone counts it; the statvfs figure when that is not available, or larger."""
    plain = shutil.disk_usage(str(path)).free
    counted = important_usage(path)
    return max(plain, counted) if counted else plain
