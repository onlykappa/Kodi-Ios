"""Picture settings (DEC-039/DEC-040): AI Upscale sizes, Saturation, per show / video / everything.

Pure logic, no Kodi imports, so the queue, the Picture menu, Settings › Picture and the player share one rule set.

Sizes are boxes; a picture is fitted inside with square pixels (kr_video_upscale_size does the same natively).
No "2K" step: the owner dropped it (2026-11-12, DEC-040 item 5).
"""
import json
import os
import time

SIZES = (('720p', 1280, 720), ('1080p', 1920, 1080), ('1440p', 2560, 1440), ('4K UHD', 3840, 2160))
LABELS = tuple(label for label, _, _ in SIZES)
OFF = 'Off'
# A picture counts as a size when it reaches 90 % of the box in width or height: 1920×800 (scope) is 1080p,
# 1916×1036 is 1080p, 1280×536 is 720p, 3840×1600 is 4K UHD.
REACH = 0.9
SATURATION = (-50, 50)
FILE = 'picture-settings.json'
DEFAULT = {'upscale': OFF, 'saturation': 0}
# Settings › Picture › AI Upscale for downloads (board G).
DOWNLOADS = {'prepare': False, 'size': '4K UHD', 'only_charging': True, 'keep_original': True}


def box(label):
    for name, width, height in SIZES:
        if name == label:
            return width, height
    raise ValueError('unknown size %r' % (label,))


def level(width, height):
    """Index in SIZES of the size this picture already is (-1: smaller than 720p)."""
    width, height = int(width or 0), int(height or 0)
    found = -1
    for index, (_, bw, bh) in enumerate(SIZES):
        if width >= bw * REACH or height >= bh * REACH:
            found = index
    return found


def above(width, height):
    """The sizes the slider offers for this picture: only those larger than it (none for 4K, none when unknown)."""
    if not width or not height:
        return []
    return list(LABELS[level(width, height) + 1:])


def target(width, height, wanted):
    """The size to make for a picture when the person asked for `wanted`: that size if it is above the picture, else the
    largest offered size below it (never larger than asked), else None (Off, unknown, or nothing above)."""
    if not wanted or wanted == OFF or wanted not in LABELS:
        return None
    offered = above(width, height)
    if not offered:
        return None
    limit = LABELS.index(wanted)
    fits = [label for label in offered if LABELS.index(label) <= limit]
    return fits[-1] if fits else None


def fitted(width, height, label):
    """(w, h) of the copy: the picture fitted inside the box, even numbers; None when it already fills the box."""
    bw, bh = box(label)
    width, height = float(width), float(height)
    if width <= 0 or height <= 0:
        return None
    scale = min(bw / width, bh / height)
    if scale <= 1.01:
        return None
    return min(bw, int(round(width * scale)) & ~1), min(bh, int(round(height * scale)) & ~1)


def clamp_saturation(value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(SATURATION[0], min(SATURATION[1], value))


# ── who keeps a picture: this video, this show, or every video ───────────────
def show_key(media):
    """'tv:1399', 'movie:157336' (TMDb), else 'title:<lower title>' so a show without TMDb still has its own."""
    media = media or {}
    kind = 'movie' if media.get('type') == 'movie' else 'tv'
    tmdb = str(media.get('tmdb') or '').strip()
    if tmdb.isdigit():
        return '%s:%s' % (kind, tmdb)
    title = ' '.join(str(media.get('show') or media.get('title') or '').lower().split())
    return 'title:%s' % title if title else ''


def video_key(media):
    media = media or {}
    return str(media.get('drive_id') or media.get('path') or '')


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault('default', dict(DEFAULT))
    data.setdefault('shows', {})
    data.setdefault('videos', {})
    data.setdefault('downloads', dict(DOWNLOADS))
    for key, value in DOWNLOADS.items():
        data['downloads'].setdefault(key, value)
    return data


def save(profile, data):
    target_path = path(profile)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp = target_path + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=1, sort_keys=True)
    os.replace(temp, target_path)


def _clean(entry):
    """Only the picture itself: an entry's title and time stay with the entry (they must never leak into the default)."""
    entry = entry or {}
    upscale = entry.get('upscale', OFF)
    return {'upscale': upscale if upscale in LABELS else OFF, 'saturation': clamp_saturation(entry.get('saturation', 0))}


def resolve(data, media):
    """The picture for this video and who keeps it: ('video'|'show'|'default', {'upscale','saturation'}).
    A video's own picture wins over its show's, which wins over the default (DEC-039)."""
    video = video_key(media)
    show = show_key(media)
    if video and video in data.get('videos', {}):
        return 'video', _clean(data['videos'][video])
    if show and show in data.get('shows', {}):
        return 'show', _clean(data['shows'][show])
    return 'default', _clean(data.get('default'))


def apply(data, scope, media, upscale=None, saturation=None, now=time.time):
    """Saves a change at 'video', 'show' or 'default'. Moving a show's picture to the default removes the show's own
    entry (board B: "All videos (my default)" makes it follow the default); 'reset' drops the show's own picture."""
    _, current = resolve(data, media)
    entry = dict(current)
    if upscale is not None:
        entry['upscale'] = upscale if upscale in LABELS else OFF
    if saturation is not None:
        entry['saturation'] = clamp_saturation(saturation)
    media = media or {}
    title = str(media.get('show') or media.get('title') or '')
    if scope == 'video':
        key = video_key(media)
        if not key:
            raise ValueError('this video has no key')
        data['videos'][key] = dict(_clean(entry), title=title, updated=int(now()))
    elif scope == 'show':
        key = show_key(media)
        if not key:
            raise ValueError('this show has no key')
        data['shows'][key] = dict(_clean(entry), title=title, updated=int(now()))
        data['videos'].pop(video_key(media), None)
    elif scope == 'default':
        data['default'] = _clean(entry)
        data['shows'].pop(show_key(media), None)
        data['videos'].pop(video_key(media), None)
    elif scope == 'reset':
        data['shows'].pop(show_key(media), None)
        data['videos'].pop(video_key(media), None)
    else:
        raise ValueError('unknown scope %r' % (scope,))
    return data


def summary(entry):
    """'Upscale to 4K UHD · Saturation +12' (board D rows)."""
    entry = _clean(entry)
    up = 'Upscale off' if entry['upscale'] == OFF else 'Upscale to %s' % entry['upscale']
    sat = entry['saturation']
    return '%s · Saturation %s' % (up, '%+d' % sat if sat else '0')


def own_pictures(data):
    """Board D's list: every show or movie with its own picture, newest change first."""
    rows = []
    for key, entry in data.get('shows', {}).items():
        rows.append({'key': key, 'title': entry.get('title') or key, 'line': summary(entry),
                     'movie': key.startswith('movie:'), 'updated': entry.get('updated', 0)})
    rows.sort(key=lambda row: -row['updated'])
    return rows


def builtin(value):
    """DEC-039 V2: the Kodi built-in that sets the picture's saturation (Kodi r32, kodi-21.3-portrait.patch)."""
    return 'SetVideoSaturation(%d)' % clamp_saturation(value)


class SaturationSync:
    """Sends the right saturation to Kodi once per video: when a video starts (or another one does), the saturation
    resolve() gives for it; a video with none set gets 0, so a show's +20 never stays on the next film.
    step(playing, media, data) returns the built-in to run, or None when nothing changed."""

    def __init__(self):
        self.key = None
        self.sent = None

    def step(self, playing, media, data):
        if not playing:
            self.key = None
            return None
        key = (video_key(media), show_key(media))
        value = resolve(data, media)[1]['saturation']
        if key == self.key and value == self.sent:
            return None
        self.key, self.sent = key, value
        return builtin(value)
