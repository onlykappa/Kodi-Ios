"""Roadmap 1A.1: how long a Python thread waits for its turn in Kodi's interpreter (ISSUE-167 suspects that wait).

A thread asks to sleep a short time and measures how late it wakes. Late wake-ups mean every Python-side transfer
(uploads, Drive reads) is waiting too. One diagnostic line a minute: median and 95th percentile lateness."""
import time


def lateness(samples):
    """(median, p95) in milliseconds."""
    if not samples:
        return 0.0, 0.0
    ordered = sorted(samples)
    pick = lambda q: ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]
    return round(pick(0.5), 1), round(pick(0.95), 1)


def run(stop, report, step=0.02, every=60.0, clock=time.monotonic, sleep=time.sleep):
    """stop() -> True to end; report(median_ms, p95_ms, samples) once per `every` seconds."""
    samples = []
    began = clock()
    while not stop():
        asked = clock()
        sleep(step)
        samples.append(max(0.0, (clock() - asked - step) * 1000.0))
        if clock() - began >= every:
            median, p95 = lateness(samples)
            report(median, p95, len(samples))
            samples = []
            began = clock()
