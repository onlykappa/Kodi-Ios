"""The time a video will end at, under the finger (owner, 2026-11-24: "tap the end time and it shows the ends at time ... ensure it tracks seeking, pausing, skipping 10 seconds, live,
not just based on when it first plays").

The controls show Kodi's own Player.FinishTime when nothing is being dragged: it is the clock plus the time left, worked out again at every draw, so it moves on while the video is
paused and follows a skip, a seek that has landed and a speed change. Kodi's value ignores a drag until the seek lands, so while a finger is on the bar the service writes the
same sum for the moment under the finger into Home property KodiIOS.EndsAt (about ten times a second); the controls show that one while Player.Seeking is true.
Everything the phone does is injected, so the rules are tested here."""
import datetime
import time

PROPERTY = 'KodiIOS.EndsAt'
FAST = 0.1     # seconds between updates while a finger is on the bar
IDLE = 0.5     # how often it looks for a finger when none is


def clock_seconds(label):
    """Seconds in a player time label ("1:02:03", "12:34", "45"), or None."""
    try:
        parts = [int(x) for x in str(label or '').strip().split(':')]
    except ValueError:
        return None
    if not 1 <= len(parts) <= 3 or any(p < 0 for p in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def pattern_of(region_time):
    """The phone's own way of writing a time (xbmc.getRegion('time'), '%I:%M:%S %p' or '%H:%M:%S') without the seconds."""
    pattern = str(region_time or '%H:%M:%S').replace(':%S', '').replace('.%S', '')
    return pattern or '%H:%M'


def format_clock(moment, pattern):
    """"10:11 PM" or "22:11", as Kodi writes it: no leading zero on a 12-hour clock."""
    text = moment.strftime(pattern)
    return text[1:] if '%I' in pattern and text.startswith('0') else text


def ends_at(now, total, position, tempo=1.0, pattern='%H:%M'):
    """When a video of `total` seconds that is at `position` ends, if it plays on from `now` at speed `tempo`; None when the length is unknown."""
    if not total or total <= 0 or position is None:
        return None
    remaining = max(float(total) - float(position), 0.0) / (tempo if tempo and tempo > 0 else 1.0)
    return format_clock(now + datetime.timedelta(seconds=remaining), pattern)


def run(playing, seeking, seek_label, total, tempo, region_time, put, wait, now=datetime.datetime.now):
    """The service's loop: while a finger is on the seek bar, write the end time for the second under it, ten times a second. wait(seconds) returns True when Kodi is closing.
    put(text) writes the Home property; put('') clears it when the finger goes."""
    pattern = pattern_of(region_time())
    shown = None
    cached_tempo = 1.0
    was = False
    while True:
        try:
            if playing() and seeking():
                if not was:
                    was = True
                    try:
                        cached_tempo = float(tempo() or 1.0)
                    except (TypeError, ValueError):
                        cached_tempo = 1.0
                text = ends_at(now(), total(), clock_seconds(seek_label()), cached_tempo, pattern)
                if text is not None and text != shown:
                    shown = text
                    put(text)
                delay = FAST
            else:
                if was or shown is not None:
                    was, shown = False, None
                    put('')
                delay = IDLE
        except Exception:
            delay = IDLE
        if wait(delay):
            return
