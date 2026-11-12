"""Page loops sleep here instead of in monitor.waitForAbort(n) (performance 1E.6).

Kodi keeps a script open until every Python thread of it has ended ("CPythonInvoker ... waiting on thread"), daemon
threads included. A refresh loop asleep in waitForAbort(2) ignored its page closing, so closing Settings, Play on TV or
Notifications waited for the sleep to end. idle() wakes the moment the page sets its stop event."""
import time

def idle(stop,monitor,seconds,slice=0.5):
    """True when the loop should end (page closed or Kodi quitting); False after `seconds` of waiting."""
    end=time.monotonic()+seconds
    while True:
        if stop.is_set() or monitor.abortRequested():return True
        left=end-time.monotonic()
        if left<=0:return False
        stop.wait(min(slice,left))
