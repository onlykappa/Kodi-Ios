"""Video controls › Picture (DEC-039 / DEC-042, docs/design/video-picture-mockups.html round 4, boards A, B, E).

Pure logic for the Picture menu over the video: what the AI Upscale slider offers (Off, then only the sizes above the
video: picture.above), what it is set to and who keeps it (this video / this show / all videos: picture.resolve),
Saturation, the AirPlay states (upscale_queue.menu_state) and what each tap changes. picture_page.py (the add-on's
script) draws it in 1080i/IOSPictureMenu.xml (picture_osd.py). No Kodi imports, so it is host-tested.
"""
import picture
import upscale_queue as uq

MEDIA_PROPERTY = 'KodiIOS.PictureMedia'   # Window(home): the download playing now, set by ios_library.upscaled_path
STEP = 5                                  # Saturation moves 5 at a tap (-50..+50)
MAX_STOPS = 5                             # Off + at most four sizes (720p, 1080p, 1440p, 4K UHD)
SHORT = {'720p': '720p', '1080p': '1080p', '1440p': '1440p', '4K UHD': '4K'}


def scope_words(scope, media):
    """The header link (board A): who keeps this picture."""
    if scope == 'video':
        return 'This video'
    if scope == 'show':
        return 'This movie' if (media or {}).get('type') == 'movie' else 'This show'
    return 'All videos'


def source_tag(width, height):
    """The video's own size, the grey tag beside AI Upscale ('1080p', '480p')."""
    level = picture.level(width, height)
    if level >= 0:
        return SHORT[picture.LABELS[level]]
    return '%dp' % int(height) if height else ''


def stops(width, height):
    """The slider's stops, left to right: 'Off', then only the sizes above the video. [] for a 4K video (no upscaler)."""
    above = picture.above(width, height)
    return [picture.OFF] + above if above else []


def model(media, width, height, settings, upscale_data=None, airplay=False, ai_available=True):
    """Everything the menu shows. media: {'tmdb','type','show','title','drive_id'} of the video playing ('' drive_id:
    a stream, which is not upscaled: DEC-039 makes copies of downloads)."""
    media = media or {}
    scope, entry = picture.resolve(settings, media)
    out = {'scope': scope, 'scope_words': scope_words(scope, media), 'title': 'Picture',
           'saturation': entry['saturation'], 'saturation_text': ('%+d' % entry['saturation']) if entry['saturation'] else '0',
           'upscale': entry['upscale'], 'src': source_tag(width, height), 'stops': [], 'sel': 0, 'chosen': 'Off',
           'show_upscale': False, 'note': '', 'airplay': None}
    offered = stops(width, height)
    if not offered:
        return out                                     # a 4K video: no AI Upscale at all (board A, third panel)
    out['show_upscale'] = True
    out['stops'] = [SHORT.get(s, s) for s in offered]
    target = picture.target(width, height, entry['upscale'])
    out['sel'] = offered.index(target) if target in offered else 0
    out['chosen'] = SHORT.get(target, 'Off') if target else 'Off'
    if not media.get('drive_id'):
        out['note'] = 'AI Upscale works on downloads (a copy is made on Google Drive).'
        return out
    if airplay:
        out['airplay'] = uq.menu_state(upscale_data or {}, media['drive_id'], width, height, entry['upscale'], ai_available)
    elif not ai_available:
        out['note'] = 'AI Upscale is not available on this iPhone.'
    return out


def airplay_lines(state):
    """Board E: (headline, line, button) for the AirPlay states; button '' when there is nothing to tap."""
    if not state:
        return '', '', ''
    label = state.get('label', '')
    if state['state'] == 'ready':
        return '%s copy ready on Google Drive' % label, 'The TV gets the upscaled copy; nothing is worked out live.', ''
    if state['state'] == 'preparing':
        bits = ['Upscaling to %s' % label, '%d %%' % int(state.get('progress') or 0)] + ([state['eta']] if state.get('eta') else [])
        return 'Preparing', ' · '.join(bits), ''
    if state['state'] == 'unavailable':
        return 'Not available on this iPhone', 'The TV plays the original.', ''
    return '', 'Made in the background like a conversion (best while charging). About 2.5× the file size on Drive.', \
        'Prepare a %s copy' % label


def props(m):
    """Window properties for 1080i/IOSPictureMenu.xml."""
    out = {'title': m['title'], 'scope': m['scope_words'], 'src': m['src'], 'chosen': m['chosen'],
           'sat': m['saturation_text'], 'satpct': str(int((m['saturation'] - picture.SATURATION[0]) * 100 /
                                                          (picture.SATURATION[1] - picture.SATURATION[0]))),
           'upscale': 'true' if m['show_upscale'] else '', 'stops': str(len(m['stops'])), 'sel': str(m['sel']),
           'note': m['note']}
    for k in range(MAX_STOPS):
        out['stop.%d' % k] = m['stops'][k] if k < len(m['stops']) else ''
    head, line, button = airplay_lines(m['airplay'])
    out.update({'tv': 'true' if m['airplay'] else '', 'tv.state': (m['airplay'] or {}).get('state', ''),
                'tv.head': head, 'tv.line': line, 'tv.button': button,
                'tv.pct': str(int((m['airplay'] or {}).get('progress') or 0))})
    return out


def write_scope(scope):
    """Where a change goes: the scope that keeps this picture now; a video with no own picture changes the default
    (board B: 'All videos (my default)' is where a picture lives until it is given to the show)."""
    return scope if scope in ('video', 'show') else 'default'


def choose_stop(settings, media, width, height, index):
    """A tap on a stop of the slider."""
    offered = stops(width, height)
    if not 0 <= index < len(offered):
        return settings
    scope, _ = picture.resolve(settings, media)
    return picture.apply(settings, write_scope(scope), media, upscale=offered[index])


def nudge_saturation(settings, media, step):
    scope, entry = picture.resolve(settings, media)
    return picture.apply(settings, write_scope(scope), media, saturation=entry['saturation'] + step * STEP)


def apply_to(settings, media, target):
    """Board B: move this picture to 'video', 'show' or 'default' (All videos), or 'reset' the show to the default."""
    _, entry = picture.resolve(settings, media)
    if target == 'reset':
        return picture.apply(settings, 'reset', media)
    return picture.apply(settings, target, media, upscale=entry['upscale'], saturation=entry['saturation'])


def apply_rows(m, media):
    """Board B's rows: (key, label, ticked)."""
    show = (media or {}).get('show') or (media or {}).get('title') or ''
    kind = 'This movie' if (media or {}).get('type') == 'movie' else 'This show'
    rows = [('video', 'This video only', m['scope'] == 'video'),
            ('show', '%s · %s' % (kind, show) if show else kind, m['scope'] == 'show'),
            ('default', 'All videos (my default)', m['scope'] == 'default')]
    if not (media or {}).get('drive_id'):
        rows = [r for r in rows if r[0] != 'video']   # a stream has no file of its own to remember
    return rows


def prepare_copy(data, media, width, height, label, clock=None):
    """Board E's 'Prepare a 4K UHD copy': a waiting entry the upscale step makes in the background."""
    import time
    original = str((media or {}).get('drive_id') or '')
    if not original or label not in picture.LABELS:
        return data
    entry = data.setdefault('copies', {}).get(original)
    if entry and entry.get('label') == label and entry.get('status') in ('waiting', 'running', 'ready'):
        return data
    data['copies'][original] = {'label': label, 'status': 'waiting', 'name': (media or {}).get('title', ''),
                                'width': int(width), 'height': int(height), 'duration': 0.0,
                                'added': (clock or time.time)(), 'asked': True}
    return data
