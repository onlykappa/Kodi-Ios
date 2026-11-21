"""Subtitles that are there without asking (owner, build 646 logs: "make subtitles work reliably everytime everywhere").

Every failure in the logs came down to one situation: the video starts with no usable subtitle in the viewer's language (none at all, a track marked forced that
holds only signs and songs, or an embedded track whose cues have no length) and nothing happens until the viewer opens the menu and taps Download and apply. When
a video starts, after the service's own check of what Kodi came up on (subtitle_memory.at_start), this decides whether that is the case and, if so, starts the
same search, download and apply the menu's button does (tracks.py, mode `auto`), once per video every few hours so a provider's quota is not spent twice.

It acts only when a subtitle is wanted: the viewer asked Kodi for subtitles in a language all the time (Settings > Subtitles), or the sound is in another language
than the subtitles. Everything outside Kodi is passed in, so the rules are tested here."""
import json
import os
import time

EVERY = 6 * 3600          # seconds before the same video is tried again
MIN_DURATION = 600        # seconds: shorter things (clips, live streams that report no length) are left alone
INDEX = 'subtitle-auto.json'


def _language(value):
    import subtitle_match as sm
    return sm.language(value) or ''


def usable(stream, wanted, zero=lambda index: None):
    """True for a subtitle stream that shows the dialogue in `wanted`: that language, not marked forced (signs and songs only), cues with a length."""
    if _language(stream.get('language')) != wanted:
        return False
    name = str(stream.get('name') or '')
    if stream.get('isforced') or 'forced' in name.lower():
        return False
    try:
        if zero(stream.get('index')):
            return False
    except Exception:
        pass
    return True


def needed(streams, wanted, audio, always, zero=lambda index: None):
    """(True/False, why): is there no usable subtitle in `wanted` while a subtitle is wanted."""
    wanted = _language(wanted)
    audio = _language(audio)
    if not wanted:
        return False, 'no subtitle language chosen'
    if not (always or (audio and audio != wanted)):
        return False, 'the sound is in the subtitle language and subtitles are not asked for all the time'
    for stream in streams or ():
        if usable(stream, wanted, zero):
            return False, 'a usable %s track is there (#%s)' % (wanted, stream.get('index'))
    return True, 'no usable %s track (%d stream%s)' % (wanted, len(streams or ()), '' if len(streams or ()) == 1 else 's')


def _load(root):
    try:
        with open(os.path.join(root, INDEX), encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def allowed(root, key, now=time.time, record=True):
    """True when this video has not been tried in the last EVERY seconds (and notes it now)."""
    if not key:
        return False
    data = _load(root)
    at = data.get(key)
    if at is not None and 0 <= now() - float(at) < EVERY:
        return False
    if record:
        data[key] = int(now())
        for old in [k for k, v in data.items() if now() - float(v) >= EVERY]:
            del data[old]
        try:
            os.makedirs(root, exist_ok=True)
            with open(os.path.join(root, INDEX), 'w', encoding='utf-8') as out:
                json.dump(data, out, separators=(',', ':'))
        except OSError:
            pass
    return True


def consider(root, key, duration, streams, wanted, audio, always, zero, launch, log, now=time.time):
    """Called when a video has started and subtitle_memory has had its say. Returns 'started', or why not."""
    try:
        if float(duration or 0) < MIN_DURATION:
            return 'too short'
        yes, why = needed(streams, wanted, audio, always, zero)
        if not yes:
            return why
        if not allowed(root, key, now):
            return 'tried lately'
        log('auto subtitles: %s; fetching them' % why)
        launch()
        return 'started'
    except Exception as error:
        try:
            log('auto subtitles: not started (%s)' % type(error).__name__)
        except Exception:
            pass
        return 'failed'
