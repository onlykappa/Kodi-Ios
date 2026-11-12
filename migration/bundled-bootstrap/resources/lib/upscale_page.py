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


def summary(settings):
    """The Settings row's value: 'On · 4K' when new downloads are upscaled or any show has a size, else 'Off'."""
    downloads = settings.get('downloads', {})
    if downloads.get('prepare'):
        return 'On · %s' % short(downloads.get('size') or '4K UHD')
    sizes = [e.get('upscale') for e in list(settings.get('shows', {}).values()) + [settings.get('default', {})]
             if e.get('upscale') in picture.LABELS]
    if sizes:
        return 'On · %s' % short(max(sizes, key=picture.LABELS.index))
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
        state = (data.get('copies', {}).get(original) or {}).get('status')
        if state == 'ready':
            g['ready'] += 1
        elif state == 'running':
            g['making'] += 1
        elif state in ('waiting', 'failed'):
            g['waiting'] += 1
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
