"""Where the time goes when a page opens (owner, 2026-11-22, log 71e31b26: Sports pages took 2-5 s). One log line per page: the first frame's total and each step.
Pure; the page passes its logger."""
import time


class Clock:
    def __init__(self, name, log, now=time.monotonic):
        self.name, self.log, self.now = name, log, now
        self.began = now()
        self.laps = []
        self.mark = self.began

    def lap(self, step):
        """Closes a step: the time since the last one."""
        at = self.now()
        self.laps.append((step, (at - self.mark) * 1000))
        self.mark = at

    def done(self, what='first frame'):
        """Logs 'page: <name>: <what> in N ms (step a N, step b N)' once."""
        if getattr(self, 'logged', False):
            return
        self.logged = True
        steps = ', '.join('%s %.0f' % (step, ms) for step, ms in self.laps)
        self.log('page: %s: %s in %.0f ms%s' % (self.name, what, (self.now() - self.began) * 1000, ' (%s)' % steps if steps else ''))
