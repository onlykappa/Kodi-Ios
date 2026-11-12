"""Roadmap 3.5: one performance line a minute in kodi.log, so every owner log answers "was it slow, and where" at a glance.

  Kodi iOS perf 60 s: rows watch 3 cached 2 tmdb 5 | opens 1 (5.8 s via library; resolve 0.3 s, open 4.2 s) |
  drive proxy 12 requests, 3 warm, seeks 2 (median 0.4 s, worst 0.9 s)

What each part counts:
  rows        Python runs that built a list in the last minute: the watch add-on's (watch), its cached rows (cached) and
              TMDb Helper's own (tmdb). Each run costs an interpreter start, so "0" while idle is the goal (roadmap 1D).
  opens       videos that reached a picture (open_timing.py: total, route, and the stage times when seen).
  drive proxy requests the app's Drive proxy served, how many were answered from the warmed start (1A.4), and the
              seeks among them with the time to the first byte (1A.5; a seek is a ranged request that does not start at 0).
Start-up stages are already one line each ('Kodi iOS startup: ...'). A minute with nothing to report writes nothing."""
import statistics

COUNTERS = ('watch', 'cached', 'tmdb')
PREFIX = 'KodiIOS.Count.'


def bump(window, name):
    """Count one list run (called by the watch add-on and the TMDb Helper patch); never raises."""
    try:
        window.setProperty(PREFIX + name, str(int(window.getProperty(PREFIX + name) or 0) + 1))
    except Exception:
        pass


def read(window):
    counts = {}
    for name in COUNTERS:
        try:
            counts[name] = int(window.getProperty(PREFIX + name) or 0)
        except (TypeError, ValueError):
            counts[name] = 0
    return counts


def line(seconds, rows, opens, proxy):
    """The summary text, or '' when nothing happened. rows: {name: count}; opens: [(took, via, stages text)]; proxy: Stats.take()."""
    parts = []
    if any(rows.values()):
        parts.append('rows ' + ' '.join('%s %d' % (name, rows[name]) for name in COUNTERS if rows.get(name)))
    if opens:
        shown = ['%d (%s)' % (len(opens), '; '.join('%.1f s via %s%s' % (took, via, ', ' + stages if stages else '') for took, via, stages in opens[-3:]))]
        parts.append('opens ' + shown[0])
    proxy = proxy or {}
    if proxy.get('requests'):
        text = 'drive proxy %d requests' % proxy['requests']
        if proxy.get('warm_hits'):
            text += ', %d warm' % proxy['warm_hits']
        seeks = proxy.get('seeks') or []
        if seeks:
            text += ', seeks %d (median %.1f s, worst %.1f s)' % (len(seeks), statistics.median(seeks), max(seeks))
        parts.append(text)
    return ('Kodi iOS perf %d s: ' % round(seconds) + ' | '.join(parts)) if parts else ''


def watch(window, take_opens, take_proxy, log, wait, every=60.0, clock=None):
    """Service thread: once a minute log the deltas since the last line (rows) and what open_timing / the proxy took."""
    import time
    clock = clock or time.monotonic
    before, last = read(window), clock()
    while not wait(every):
        now, at = read(window), clock()
        try:
            text = line(at - last, {k: max(0, now[k] - before[k]) for k in COUNTERS}, take_opens(), take_proxy())
        except Exception:
            text = ''
        before, last = now, at
        if text:
            log(text)
