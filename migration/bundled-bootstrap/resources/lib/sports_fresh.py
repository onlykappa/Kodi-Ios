"""A Sports page that opened on the answer remembered from last time redraws as soon as the real answer arrives.

Owner, build 618: the Sports pages opened as black screens for a second or more while ESPN answered. The provider now keeps its last answer on the
phone (sports_espn.EspnProvider.snapshot_path) and returns it at once after a restart while it refreshes in the background; this is the page's half:
watch until the provider says it is no longer showing a remembered answer, then draw again (instead of waiting for the page's next 30 s look)."""
import threading
import time


def remembered(provider):
    try:
        return bool(getattr(provider, 'remembered', lambda: False)())
    except Exception:
        return False


def start(provider, stop, on_fresh, step=.4, limit=25.0, sleep=time.sleep, clock=time.monotonic):
    """If the provider is showing a remembered answer, call `on_fresh()` once when it stops (at most `limit` s). Returns the thread, or None."""
    if not remembered(provider):
        return None

    def run():
        began = clock()
        while clock() - began < limit and not stop.is_set():
            if not remembered(provider):
                try:
                    on_fresh()
                except Exception:
                    pass
                return
            sleep(step)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
