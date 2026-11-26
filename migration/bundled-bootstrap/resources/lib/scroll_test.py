"""A scroll test that names what costs a frame (owner, build 623 log 8c570737: the Sports hub and Upcoming scroll at 24-27 fps on the phone, Home at 42-60).

Started from Settings search (type "scroll test", tap the one result): the Sports hub opens and scrolls itself down and up the same way five times, each time
leaving out a different part of what it draws (the Live Now card, the Upcoming and Leagues tiles, the Up next rows, all three), while the frame rate Kodi
reports is read ten times a second. One log line per run:

  Kodi iOS scroll test: everything drawn: 26 fps typical, 21 fps slowest tenth, 88 samples

If leaving out one part lifts the rate, that part is the cost; if leaving all out still reads about 25, the cost is not the content (the backdrop, the
tab bar over it, or the phone's drawing itself). The pages look exactly as before outside the test; the parts are only hidden while the Home window
property KodiIOS.ScrollTest names them. Everything the phone does is injected, so the rules are tested here.
"""
import statistics

PROPERTY = 'KodiIOS.ScrollTest'
# (what the log says, the parts left out)
RUNS = (
    ('everything drawn', ()),
    ('Live Now card left out', ('live',)),
    ('tiles left out', ('tiles',)),
    ('Up next rows left out', ('rows',)),
    ('card, tiles and rows left out', ('live', 'tiles', 'rows')),
)
STEPS = 16          # focus moves down, then the same up: the list scrolls with its own animation
PAUSE = 0.45        # seconds between moves (the scroll animation is 0.22 s)
SETTLE = 1.0        # seconds after changing what is drawn, before measuring
LOOK = 0.1          # seconds between readings
ANIMATING = 15.0    # fps: below this nothing is moving (an idle page reads about 3)


def value(parts):
    """The property text for the parts left out: '_live_tiles_' (what the skin's conditions look for), or '' for none."""
    return '_' + '_'.join(parts) + '_' if parts else ''


def summary(name, samples, minimum=8):
    ordered = sorted(samples)
    if len(ordered) < minimum:
        return 'Kodi iOS scroll test: %s: too few readings (%d)' % (name, len(ordered))
    return 'Kodi iOS scroll test: %s: %d fps typical, %d fps slowest tenth, %d samples' % (
        name, round(statistics.median(ordered)), round(ordered[(len(ordered) - 1) // 10]), len(ordered))


def measure(move, fps, wait, steps=STEPS, pause=PAUSE, look=LOOK):
    """Scroll down and up once and return the frame rates read while something moved. move(direction) presses the key, fps() reads Kodi's rate,
    wait(seconds) -> True when Kodi is closing (stop at once)."""
    samples = []
    for direction in ['Down'] * steps + ['Up'] * steps:
        move(direction)
        waited = 0.0
        while waited < pause:
            if wait(look):
                return samples
            waited += look
            rate = fps()
            if rate >= ANIMATING:
                samples.append(rate)
    return samples


def run(home, move, fps, wait, log, runs=RUNS, steps=STEPS, pause=PAUSE, settle=SETTLE):
    """Every run in turn; the property is always cleared at the end. Returns {name: samples}."""
    found = {}
    try:
        for name, parts in runs:
            home.setProperty(PROPERTY, value(parts))
            if wait(settle):
                break
            samples = measure(move, fps, wait, steps, pause)
            found[name] = samples
            log(summary(name, samples))
    finally:
        home.clearProperty(PROPERTY)
    return found


def start(page, xbmc, xbmcgui, log):
    """Called by the Sports hub when it was opened by the test: runs in its own thread, then says it is done."""
    home = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()

    def fps():
        try:
            return float(xbmc.getInfoLabel('System.FPS') or 0)
        except ValueError:
            return 0.0
    found = run(home, lambda direction: xbmc.executebuiltin('Action(%s)' % direction), fps, monitor.waitForAbort, log)
    try:
        xbmcgui.Dialog().notification('Scroll test', 'Done: send kodi.log', xbmcgui.NOTIFICATION_INFO, 4000, False)
    except Exception:
        pass
    return found
