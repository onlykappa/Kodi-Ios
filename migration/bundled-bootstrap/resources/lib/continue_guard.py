"""Continue must never be a dead end (owner, build 634 log 4b37fc5b: "resuming from Umbrella fails completely after loading forever").

Continue plays the link Umbrella gave last time, directly (ios_watch_dialog.fast_stream) so it starts fast. When that link will not open (log: Kodi's open of a
debrid link sat 30 s with no data, then "Open - Error, could not open file", then a "Playback failed" box) the person was left with nothing. fast_stream now
leaves a note (Home property KodiIOS.ContinueFast: when it started and the address that does it the normal way); this watcher, in the service, looks once a
half second: playing a picture clears the note; a failure box, or LIMIT seconds with no picture, stops what is opening, closes the box and plays the same
title the normal way (TMDb Helper and Umbrella find a fresh link, which Continue then remembers). The normal way carries ios_fast=0, so it never tries the
remembered link again and cannot loop. Everything the phone does is injected, so the rules are tested here."""
import json
import time

MARK = 'KodiIOS.ContinueFast'
LIMIT = 25.0      # seconds the remembered link gets to put a picture up (a good open takes 3-12 s; Kodi itself gave up at 30)
STEP = 0.5


def retry_url(params):
    """The TMDb Helper address for the same title that skips the remembered link (ios_fast=0), from fast_stream's params."""
    import urllib.parse
    keep = {'info': 'play', 'tmdb_type': params.get('tmdb_type', ''), 'tmdb_id': params.get('tmdb_id', '')}
    if params.get('tmdb_type') == 'tv':
        keep.update(season=params.get('season', ''), episode=params.get('episode', ''))
    keep.update(ios_continue='1', ios_fast='0')
    return 'plugin://plugin.video.themoviedb.helper/?' + urllib.parse.urlencode(keep)


def note(params, now=time.time):
    """The text fast_stream leaves in MARK."""
    return json.dumps({'at': now(), 'retry': retry_url(params)})


def decide(mark, now, playing, failure_box):
    """'none' (no note), 'ok' (a picture is up: note done), 'wait', or 'fallback' (failure box up, or LIMIT seconds with no picture)."""
    try:
        data = json.loads(mark or '')
        started = float(data['at'])
        address = str(data['retry'])
    except (ValueError, KeyError, TypeError):
        return 'none' if not mark else 'ok'   # a note we cannot read is cleared by the caller
    if not address.startswith('plugin://'):
        return 'ok'
    if playing:
        return 'ok'
    if failure_box or now - started >= LIMIT:
        return 'fallback'
    return 'wait'


def step(home, playing, failure_box, stop, close_boxes, play, log, now=time.time):
    """One look. Returns what was decided."""
    mark = home.getProperty(MARK)
    verdict = decide(mark, now(), playing(), failure_box())
    if verdict == 'ok':
        home.clearProperty(MARK)
    elif verdict == 'fallback':
        data = json.loads(mark)
        home.clearProperty(MARK)
        log('continue guard: the remembered link did not open (%d s%s); asking Umbrella for a fresh one' % (
            now() - float(data['at']), ', failure box up' if failure_box() else ''))
        stop()
        close_boxes()
        play(data['retry'])
    return verdict


def watch(home, playing, failure_box, stop, close_boxes, play, log, wait, now=time.time):
    """The service's loop: wait(STEP) returns True when Kodi is closing."""
    while not wait(STEP):
        try:
            if home.getProperty(MARK):
                step(home, playing, failure_box, stop, close_boxes, play, log, now)
        except Exception as error:
            log('continue guard: %s' % type(error).__name__)
