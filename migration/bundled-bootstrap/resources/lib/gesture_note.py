"""One log line per touch gesture on the dialog pages (owner, build 622, log ac85bba1: "flicks do nothing" on the Sports pages and Favourites).

Kodi decides on momentum when the finger lifts. If it starts the glide it withholds the gesture's end marker (ACTION_GESTURE_END) and keeps sending
pan events itself, one a frame, until the glide is over (about a second); if it does not, the end marker arrives at once. A Python page sees every
action, so its onAction can tell the two apart without any native change:

  Kodi iOS gesture: 12 pans over 0.31 s, moved 640 px, end after 0.31 s (stopped at once)
  Kodi iOS gesture: 70 pans over 1.20 s, moved 2210 px, end after 1.20 s (glided on: 58 pans after the last 0.18 s of dragging)

A drag that ends without a glide and a flick that glides differ in how long the pans go on and how far they move. Never raises; at most MAX lines."""
import time

BEGIN, PAN, END, ABORT = 501, 504, 599, 505   # ActionIDs.h: ACTION_GESTURE_END is 599, ACTION_GESTURE_ABORT 505 (build 623 log 8c570737: 35 swipe lines and no pan line, because END was 505 here)
SWIPES = (511, 521, 531, 541)   # left, right, up, down: Kodi's swipe actions
MAX = 40


class Tracker:
    def __init__(self, log, clock=time.monotonic):
        self.log, self.clock = log, clock
        self.reset()
        self.said = 0

    def reset(self):
        self.began = None
        self.pans = []   # (time, y)

    def feed(self, action):
        """Call from a page's onAction with the action. Never raises."""
        try:
            ident = action.getId()
            if ident == BEGIN:
                self.reset()
                self.began = self.clock()
            elif ident == PAN:
                if self.began is None:
                    self.began = self.clock()
                self.pans.append((self.clock(), float(action.getAmount2())))
            elif ident in (END, ABORT):
                self.finish('end' if ident == END else 'abort')
            elif ident in SWIPES:
                self.say('swipe action %d (Kodi saw a swipe, not a drag)' % ident)
        except Exception:
            pass

    def finish(self, how):
        pans, began = self.pans, self.began
        self.reset()
        if began is None or not pans:
            return
        now = self.clock()
        span = pans[-1][0] - pans[0][0]
        moved = abs(pans[-1][1] - pans[0][1])
        # the dragging part: the pans that came while the finger moved, taken as the first run whose gaps stay small; a glide is the long tail of
        # evenly spaced pans after it. Without the finger's lift time the best sign is how long the pans lasted: a plain drag ends within a
        # moment of the last movement, a glide runs about a second more.
        kind = 'glided on' if span > 0.6 else 'stopped at once'
        self.say('%d pans over %.2f s, moved %d px, %s after %.2f s (%s)' % (len(pans), span, moved, how, now - began, kind))

    def say(self, text):
        if self.said < MAX:
            self.said += 1
            self.log('Kodi iOS gesture: ' + text)
