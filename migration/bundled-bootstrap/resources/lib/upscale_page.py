"""Settings › AI Upscale (docs/design/ai-upscale-settings-mockups.html, approved DEC-042): the rows of the page.

Pure logic over plain dicts (picture settings, upscale-copies.json, the preparation queue's jobs), so the page script
(upscale_settings.py), the Settings row and the tests agree. The page is drawn by the Skin Settings list window
(IOSSkinList.xml: section titles, switches and value rows with a grey second line), not a window of its own.

Rows are dicts: kind ('title' | 'switch' | 'button' | 'note'), label, sub (grey second line), value (right side),
on (switches) and action (what a tap does; upscale_settings.py runs it).
"""
import picture
import upscale_queue as uq

MODEL_TEXT = {2: 'ready', 1: 'downloading', 0: 'needed', -1: 'unavailable'}


def short(label):
    """'4K UHD' -> '4K' for the narrow places (the Settings row, chips)."""
    return '4K' if label == '4K UHD' else label


def size_name(width, height):
    index = picture.level(width, height)
    return short(picture.LABELS[index]) if index >= 0 else ('%dp' % int(height) if height else '?')


def summary(settings, engine=None):
    """The Settings row's value: 'On · 4K' only when something is really set (new downloads are upscaled, or a show / the
    default has a size), else 'Off'. engine ({'upscales', 'model'} from the queue step; {} or None before it has run):
    a phone with no AI engine (or no iOS 26 model) says 'Unavailable', because nothing can be made there."""
    if engine and (not engine.get('upscales') or engine.get('model') == -1):
        return 'Unavailable'
    # ISSUE-235 (owner: "this still says On · 4K" with Upscale new downloads off): it was on for shows set to a size (the
    # log made 4K copies of Phony). The row now says what is on: new downloads, every show, or how many shows.
    downloads = settings.get('downloads', {})
    if downloads.get('prepare'):
        return 'New downloads \u00b7 %s' % short(downloads.get('size') if downloads.get('size') in picture.LABELS else '4K UHD')
    default = settings.get('default', {})
    if isinstance(default, dict) and default.get('upscale') in picture.LABELS:
        return 'All shows \u00b7 %s' % short(default['upscale'])
    sizes = [e.get('upscale') for e in settings.get('shows', {}).values() if isinstance(e, dict) and e.get('upscale') in picture.LABELS]
    if sizes:
        return '%d show%s \u00b7 %s' % (len(sizes), '' if len(sizes) == 1 else 's', short(max(sizes, key=picture.LABELS.index)))
    return 'Off'


def status_row(engine):
    """Board B/C3: the status card as the first row. engine: {'upscales': bool, 'model': -1..2} from the queue step,
    or {} before the step has run once."""
    if not engine:
        return {'kind': 'button', 'label': 'Checking this iPhone', 'sub': 'Open the page again in a moment', 'action': ''}
    if not engine.get('upscales') or engine.get('model') == -1:
        return {'kind': 'button', 'label': 'Not available on this iPhone',
                'sub': "Apple's AI super resolution needs iOS 26. Videos play as they are.", 'action': ''}
    if engine.get('model') == 2:
        return {'kind': 'button', 'label': 'Ready on this iPhone', 'sub': "Apple's AI super resolution · iOS 26", 'action': ''}
    if engine.get('model') == 1:
        return {'kind': 'button', 'label': "Downloading Apple's AI model", 'sub': 'A one-time download from Apple', 'action': ''}
    return {'kind': 'button', 'label': "Apple's AI model is needed", 'sub': 'A one-time download from Apple · tap to get it',
            'value': 'Download', 'action': 'model'}


def library(prep_state, media_for, data):
    """Every prepared download grouped by show/movie: [{'key', 'title', 'kind', 'videos': [...], 'source', 'ready',
    'making', 'waiting', 'kept'}], largest first; 'kept' counts 4K and HDR videos (kept as they are)."""
    groups = {}
    for job in (prep_state or {}).get('jobs', {}).values():
        if job.get('status') != 'done':
            continue
        probe = job.get('probe') or {}
        original = str(job.get('prepared_id') or (job.get('source') or {}).get('id') or '')
        media = media_for(job) or {}
        key = picture.show_key(media) or 'video:' + original
        title = media.get('show') or (job.get('source') or {}).get('name', '')
        g = groups.setdefault(key, {'key': key, 'title': title, 'kind': media.get('type', 'tv'), 'media': media, 'videos': [],
                                    'ready': 0, 'making': 0, 'waiting': 0, 'kept': 0, 'levels': []})
        width, height = int(probe.get('width') or 0), int(probe.get('height') or 0)
        if probe.get('hdr') or not picture.above(width, height):
            g['kept'] += 1
            continue
        g['videos'].append(original)
        g['levels'].append(picture.level(width, height))
        copy = data.get('copies', {}).get(original) or {}
        state = copy.get('status')
        name = (job.get('source') or {}).get('name', '')
        g.setdefault('items', []).append({'id': original, 'name': name, 'season': int(media.get('season') or 0),
                                          'episode': int(media.get('episode') or 0), 'level': picture.level(width, height),
                                          'state': state or '', 'label': copy.get('label', ''), 'size': int(copy.get('size') or 0),
                                          'progress': int(copy.get('progress') or 0), 'eta': copy.get('eta', ''),
                                          'duration': float(probe.get('duration') or 0), 'width': width, 'height': height})
        if state == 'ready':
            g['ready'] += 1
        elif state == 'running':
            g['making'] += 1
        elif state in ('waiting', 'failed'):
            g['waiting'] += 1
    # Owner screenshot (2026-11-13): "Phony" twice: some episodes matched TMDb ('tv:<id>'), others only by name
    # ('title:phony'). A name-only group joins the TMDb group of the same show.
    def same(title):
        import debrid_drive
        return debrid_drive.show_match(title)
    for key in [k for k in groups if k.startswith('title:')]:
        g = groups[key]
        home = next((o for k, o in groups.items() if not k.startswith('title:') and o['kind'] == g['kind'] and same(o['title']) == same(g['title'])), None)
        if home is None:
            continue
        for field in ('videos', 'levels'):
            home[field] += g[field]
        home.setdefault('items', []).extend(g.get('items') or [])
        for field in ('ready', 'making', 'waiting', 'kept'):
            home[field] += g[field]
        del groups[key]
    out = []
    for g in groups.values():
        g['source'] = short(picture.LABELS[min(g['levels'])]) if g['levels'] and min(g['levels']) >= 0 else ('480p' if g['levels'] else '')
        out.append(g)
    return sorted(out, key=lambda g: (-len(g['videos']), g['title'].lower()))


def show_sub(g, label):
    count = len(g['videos'])
    what = 'Movie' if g['kind'] == 'movie' else '%d ep' % count
    if label in picture.LABELS:
        done = 'all ready' if g['ready'] == count else ('%d ready' % g['ready'] if g['ready'] else
                                                         ('making' if g['making'] else 'waiting'))
        return '%s · %s → %s · %s' % (what, g['source'], short(label), done)
    return '%s · %s · can go 4K' % (what, g['source'])


def rows(settings, data, groups, engine):
    """The whole page, top to bottom (boards B1 and B2)."""
    out = [status_row(engine)]
    downloads = settings.get('downloads', {})
    out += [{'kind': 'title', 'label': 'New downloads'},
            {'kind': 'switch', 'label': 'Upscale new downloads', 'sub': '720p and 1080p only', 'on': bool(downloads.get('prepare')),
             'action': 'toggle:prepare'},
            {'kind': 'button', 'label': 'Upscale to', 'value': downloads.get('size') or '4K UHD', 'action': 'size'},
            {'kind': 'switch', 'label': 'Only while charging', 'on': bool(downloads.get('only_charging', True)),
             'action': 'toggle:only_charging'},
            {'kind': 'note', 'label': 'Copies are made in the background like a conversion and play on the TV with AirPlay. '
                                      'The original stays for the phone and older TVs. About 2.5× the size on Google Drive.'}]
    copies = data.get('copies', {})
    running = [e for e in copies.values() if e.get('status') == 'running']
    waiting = [e for e in copies.values() if e.get('status') in ('waiting', 'failed')]
    out.append({'kind': 'title', 'label': 'Making now'})
    if running:
        e = running[0]
        bits = ['To %s' % e['label'], '%d %%' % int(e.get('progress') or 0)] + ([e['eta']] if e.get('eta') else [])
        out.append({'kind': 'button', 'label': _title(e.get('name')), 'sub': ' · '.join(bits), 'action': ''})
    elif waiting:
        note = waiting[0].get('note') or 'Starts when nothing is converting'
        out.append({'kind': 'button', 'label': _title(waiting[0].get('name')), 'sub': note, 'action': ''})
    else:
        out.append({'kind': 'button', 'label': 'Nothing being made', 'sub': 'Choose a size for a show below', 'action': ''})
    more = len(waiting) - (0 if running else 1)
    if more > 0:
        out.append({'kind': 'button', 'label': '%d more waiting' % more, 'action': ''})
    out.append({'kind': 'title', 'label': 'Shows and movies'})
    kept = sum(g['kept'] for g in groups)
    for g in groups:
        if not g['videos']:
            continue
        scope, entry = picture.resolve(settings, g['media'])
        label = entry['upscale'] if scope != 'default' or entry['upscale'] in picture.LABELS else picture.OFF
        out.append({'kind': 'button', 'label': g['title'], 'sub': show_sub(g, label),
                    'value': short(label) if label in picture.LABELS else 'Off', 'action': 'show:' + g['key']})
    if not any(g['videos'] for g in groups):
        out.append({'kind': 'note', 'label': 'No prepared 720p or 1080p download on Google Drive yet.'})
    if kept:
        out += [{'kind': 'title', 'label': 'Kept as they are'},
                {'kind': 'button', 'label': '%d video%s already in 4K or HDR' % (kept, '' if kept == 1 else 's'), 'action': ''}]
    used = sum(int(e.get('size') or 0) for e in copies.values() if e.get('status') == 'ready')
    if used:
        out.append({'kind': 'note', 'label': 'Upscaled copies use %.1f GB on Google Drive.' % (used / 1e9)})
    out.append({'kind': 'button', 'label': 'Test on one video', 'sub': 'Speed, heat, battery; nothing uploaded', 'action': 'test'})
    return out


def _title(name):
    try:
        import drivelibrary
        return drivelibrary.display_title(name or '') or name or ''
    except Exception:
        return name or ''


def show_sizes(g):
    """The choices for one show (board C slider as a list): Off, then only sizes above its videos."""
    levels = [lv for lv in g['levels']] or [1]
    return [picture.OFF] + list(picture.LABELS[max(levels) + 1:])


def set_show(settings, g, label):
    """This show's own size (DEC-039 per show); Off keeps it off even when new downloads are upscaled."""
    return picture.apply(settings, 'show', g['media'], upscale=label)


def toggle(settings, key):
    settings.setdefault('downloads', dict(picture.DOWNLOADS))[key] = not settings['downloads'].get(key, picture.DOWNLOADS.get(key))
    return settings


def engine_state(native, width=1920, height=1080, label='4K UHD'):
    """What the status row needs, from the native library (the queue step saves it in upscale-copies.json)."""
    if not getattr(native, 'upscales', False):
        return {'upscales': False, 'model': -1}
    try:
        return {'upscales': True, 'model': int(native.upscale_model(width, height, label, 0))}
    except Exception:
        return {'upscales': True, 'model': -1}


# --- Board C: one show's page (V3; upscale_show_page.py draws it, upscale_settings.py fills it) ----------------------
CHIPS = {'ready': ('Ready', 'green'), 'running': ('Making', 'blue'), 'waiting': ('Waiting', 'grey'),
         'failed': ('Waiting', 'grey'), 'blocked': ('Kept', 'grey'), 'gone': ('Off', 'grey'), '': ('Off', 'grey')}


def episode_rows(g):
    """Board C1: one row per video, in episode order: title, grey line (copy size, progress, or what it waits for), chip."""
    import drivelibrary
    out = []
    for item in sorted(g.get('items') or [], key=lambda i: (i['season'], i['episode'], i['name'].lower())):
        chip, tone = CHIPS.get(item['state'], CHIPS[''])
        if item['episode']:
            title = '%d · %s' % (item['episode'], episode_name(item['name']) or 'Episode %d' % item['episode'])
        else:
            title = drivelibrary.display_title(item['name']) or item['name']
        if item['state'] == 'ready':
            line = '%s copy · %s' % (short(item['label']), _gb(item['size']))
        elif item['state'] == 'running':
            line = ' · '.join(x for x in ('%d %%' % item['progress'], item.get('eta') or '') if x)
        elif item['state'] in ('waiting', 'failed'):
            line = 'Up next'
        else:
            line = size_name(item['width'], item['height'])
        out.append({'id': item['id'], 'title': title, 'line': line, 'chip': chip, 'tone': tone})
    return out


def episode_name(name):
    """The episode's own name from a file name ('Naruto Shippuden S01E01 Homecoming.1080p.mkv' -> 'Homecoming'), or ''
    when the name has none (board C1 rows: "1 · Homecoming")."""
    import re
    base = re.sub(r'\.[A-Za-z0-9]{2,4}$', '', str(name or '').rsplit('/', 1)[-1])
    base = re.sub(r'[._]+', ' ', re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', base))
    m = re.search(r'(?i)\bS\d{1,2}\s*E\d{1,4}\b|\bepisode\s*\d{1,4}\b|\s[-–]\s*\d{1,4}\b', base)
    if not m:
        return ''
    tail = base[m.end():]
    cut = re.search(r'(?i)\b(2160p|1080p|720p|480p|4k|web[ -]?dl|webrip|bluray|bdrip|hdtv|x26[45]|h ?26[45]|hevc|10bit|aac|dual audio)\b', tail)
    tail = tail[:cut.start()] if cut else tail
    return re.sub(r'^[\s\-–:]+|[\s\-–:]+$', '', re.sub(r'\s{2,}', ' ', tail))


def _gb(size):
    return '%.1f GB' % (size / 1e9) if size >= 1e9 else '%d MB' % max(1, round(size / 1e6))


def show_view(settings, g, best=None):
    """Board C for one show or movie: {'title', 'sub', 'choices', 'chosen', 'rows', 'primary', 'primary_size',
    'remove', 'note'}. choices: Off, then only the sizes above its videos (the Picture menu's slider)."""
    scope, entry = picture.resolve(settings, g['media'])
    chosen = entry['upscale'] if scope != 'default' or entry['upscale'] in picture.LABELS else picture.OFF
    choices = show_sizes(g)
    rows = episode_rows(g)
    items = g.get('items') or []
    count = len(items)
    what = 'Movie' if g['kind'] == 'movie' else '%d episode%s' % (count, '' if count == 1 else 's')
    sub = ' · '.join(x for x in (what, g.get('source', '')) if x)
    target = best or (choices[-1] if len(choices) > 1 else picture.OFF)
    todo = [i for i in items if i['state'] not in ('ready', 'running', 'waiting')]
    estimate = sum(uq.estimate_bytes(i['duration'], target, i['width'] or 1920, i['height'] or 1080) for i in todo) if target in picture.LABELS else 0
    primary = ''
    if chosen not in picture.LABELS and target in picture.LABELS and todo:
        primary = ('Upscale to %s' % target if g['kind'] == 'movie' else
                   'Upscale %s %d · about %s' % ('all' if len(todo) == count else 'the other', len(todo), _gb(estimate)))
    ready = [i for i in items if i['state'] == 'ready']
    label = ready[0]['label'] if ready else ''
    remove = 'Remove the %s cop%s…' % (short(label), 'y' if len(ready) == 1 else 'ies') if ready else ''
    if chosen in picture.LABELS:
        waiting = sum(1 for i in items if i['state'] in ('waiting', 'failed', 'running'))
        note = ('%d being made, one at a time%s.' % (waiting, ' while charging' if settings.get('downloads', {}).get('only_charging', True) else '')
                if waiting else 'Every video has its %s copy.' % short(chosen) if ready and len(ready) == count else '')
    else:
        note = 'The original stays for the phone and older TVs.'
    return {'title': g['title'], 'sub': sub, 'choices': choices, 'chosen': chosen, 'rows': rows, 'primary': primary,
            'primary_size': target, 'remove': remove, 'note': note}


def remove_copies(settings, data, g):
    """Board C "Remove the copies…" (after the alert): the show goes Off (so nothing is made again) and the service
    sends each copy to Drive's Trash (upscale_cloud.process_one). Returns (settings, data)."""
    settings = set_show(settings, g, picture.OFF)
    import upscale_queue
    upscale_queue.ask(data, g.get('videos') or [], picture.OFF)   # ISSUE-245: no longer asked for
    ids = [i['id'] for i in g.get('items') or [] if i['state'] in ('ready', 'waiting', 'failed', 'running')]
    data.setdefault('remove', [])
    data['remove'] = sorted(set(data['remove']) | set(ids))
    return settings, data


# --- DEC-044 boards A and B: the AI Upscale page (upscale_main_page.py draws it, upscale_settings.py fills it) -------
def copy_title(entry, key=''):
    """'Hell House LLC Origins · E1' from the copy's file name; never empty (the rig showed a blank "Making now" row)."""
    import drivelibrary
    name = (entry or {}).get('name') or ''
    info = drivelibrary.parse(name) if name else {}
    title = drivelibrary.display_title(name) if name else ''
    if info.get('episode'):
        show = info.get('title') or title
        season = int(info.get('season') or 0)
        title = '%s · %s' % (show, ('S%d E%d' % (season, int(info['episode'])) if season > 1 else 'E%d' % int(info['episode'])))
    return title or name or key or 'Video'


def _minutes(entry):
    """'about 1 h 10 min' from the copy's length at the speed copies are made (about real time on a charger)."""
    minutes = int(float(entry.get('duration') or 0) / 60 * 1.6)
    if minutes <= 0:
        return ''
    return 'about %d h %d min' % (minutes // 60, minutes % 60) if minutes >= 60 else 'about %d min' % max(1, minutes)


def making(data, paused=False):
    """Board A1/A3: the Making now card, or None. {'key', 'title', 'line', 'pct', 'grey', 'paused', 'name'}."""
    import upscale_queue as uq
    copies = data.get('copies', {})
    key = next((k for k, e in copies.items() if e.get('status') == 'running'), None)
    running = key is not None
    if key is None:
        order = uq.up_next(data)
        key = order[0] if order else None
    if key is None:
        return None
    e = copies[key]
    note = 'Paused by you' if paused else e.get('note') or ''
    if running and not note:
        bits = ['To %s' % short(e['label']), '%d %%' % int(e.get('progress') or 0)] + (['%s left' % e['eta']] if e.get('eta') else [])
        line = ' · '.join(bits)
    else:
        line = note or 'Starts when nothing is being prepared'
    return {'key': key, 'title': copy_title(e, key), 'name': e.get('name') or '', 'line': line,
            'pct': int(e.get('progress') or 0), 'grey': bool(note) or not running, 'paused': bool(paused), 'running': running}


def next_rows(data, skip=None):
    """Board A1/B2: Up next in order (the card's copy left out): [{'key', 'title', 'line', 'name'}]."""
    import upscale_queue as uq
    out = []
    for key in uq.up_next(data):
        if key == skip:
            continue
        e = data['copies'][key]
        source = size_name(e.get('width') or 0, e.get('height') or 0) if e.get('height') else ''
        line = ' · '.join(x for x in (('%s → %s' % (source, short(e['label']))) if source else 'To %s' % short(e['label']),
                                      _minutes(e)) if x)
        if e.get('status') == 'failed':
            line = 'Trying again later'
        out.append({'key': key, 'title': copy_title(e, key), 'line': line, 'name': e.get('name') or ''})
    return out


def show_rows(settings, groups):
    """Board A1: one row per show or movie: title, '5 episodes · 0 of 5 ready', the size on the right."""
    out = []
    for g in groups:
        if not g['videos']:
            continue
        scope, entry = picture.resolve(settings, g['media'])
        label = entry['upscale'] if scope != 'default' or entry['upscale'] in picture.LABELS else picture.OFF
        count = len(g['videos'])
        what = 'Movie' if g['kind'] == 'movie' else '%d episode%s' % (count, '' if count == 1 else 's')
        if label in picture.LABELS:
            state = 'making 1' if g['making'] else '%d of %d ready' % (g['ready'], count)
        else:
            state = 'not upscaled'
        out.append({'key': g['key'], 'title': g['title'], 'sub': '%s · %s' % (what, state),
                    'value': short(label) if label in picture.LABELS else 'Off', 'name': (g.get('items') or [{}])[0].get('name', '')})
    return out


def space_line(data):
    ready = [e for e in data.get('copies', {}).values() if e.get('status') == 'ready']
    if not ready:
        return 'No copies yet'
    return '%d cop%s · %s' % (len(ready), 'y' if len(ready) == 1 else 'ies', _gb(sum(int(e.get('size') or 0) for e in ready)))


def main_view(settings, data, groups, engine, paused=False):
    """Everything board A shows, as plain values (upscale_settings.py turns them into window properties)."""
    # A copy saved without its file name (older builds) takes it from its prepared video, so no row shows an id.
    names = {str(i['id']): i.get('name') for g in groups for i in (g.get('items') or []) if i.get('name')}
    for key, e in (data.get('copies') or {}).items():
        if not e.get('name') and names.get(str(key)):
            e['name'] = names[str(key)]
    card = making(data, paused)
    nexts = next_rows(data, card['key'] if card else None)
    downloads = settings.get('downloads', {})
    status = status_row(engine)
    return {'making': card, 'next': nexts, 'shows': show_rows(settings, groups),
            'prepare': bool(downloads.get('prepare')), 'size': downloads.get('size') or '4K UHD',
            'only_charging': bool(downloads.get('only_charging', True)),
            'engine': {'title': status['label'], 'sub': status.get('sub', ''), 'action': status.get('action', '')},
            'space': space_line(data), 'can_cancel_all': bool(card or nexts)}


def copy_sheet(data, key, paused=False, device=None):
    """Board B1: the copy's sheet. Stages: AI model ready → making the copy → saving to Google Drive."""
    e = (data.get('copies') or {}).get(key) or {}
    device = device or {}
    bits = []
    if int(device.get('charging', -1)) == 1:
        bits.append('On charger')
    if device.get('thermal') in ('nominal', 'fair'):
        bits.append('phone cool')
    elif device.get('thermal'):
        bits.append('phone warm')
    pct = int(e.get('progress') or 0)
    duration = float(e.get('duration') or 0)
    made = ('%d min of %d made' % (int(duration * pct / 100 / 60), int(duration / 60))) if duration else ''
    running = e.get('status') == 'running'
    note = 'Paused by you' if paused else e.get('note') or ''
    model_ready = int((data.get('engine') or {}).get('model', 0) or 0) == 2
    est = 0
    try:
        import upscale_queue as uq
        est = uq.estimate_bytes(duration, e.get('label') or '4K UHD', e.get('width') or 1920, e.get('height') or 1080)
    except Exception:
        pass
    info = {}
    try:
        import drivelibrary
        info = drivelibrary.parse(e.get('name') or '')
    except Exception:
        pass
    source = size_name(e.get('width') or 0, e.get('height') or 0) if e.get('height') else ''
    sub = ' · '.join(x for x in (('Episode %d' % int(info['episode'])) if info.get('episode') else '',
                                 ('%s → %s' % (source, e.get('label') or '4K UHD')) if source else 'To %s' % (e.get('label') or '4K UHD')) if x)
    return {'title': copy_title(e, key) if not info.get('episode') else (info.get('title') or copy_title(e, key)),
            'sub': sub, 'device': ' · '.join(bits) or note, 'pct': pct,
            'stats': ' · '.join(x for x in ('%d %%' % pct, made) if x), 'left': ('%s left' % e['eta']) if e.get('eta') else (note or ''),
            'stages': [('done' if model_ready else 'now', 'AI model ready' if model_ready else "Getting Apple's AI model"),
                       ('now' if running and model_ready else 'done' if e.get('status') == 'ready' else 'next', 'Making the %s copy' % short(e.get('label') or '4K UHD')),
                       ('next' if e.get('status') != 'ready' else 'done', 'Saving to Google Drive' + (' · %s' % _gb(est) if est else ''))],
            'pause': 'Resume' if paused else 'Pause', 'grey': bool(note) or not running, 'name': e.get('name') or ''}
