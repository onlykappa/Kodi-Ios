"""AI Upscale copies (DEC-039/DEC-040): which videos get one, when the phone may make it, which file plays.

Pure decisions over plain dicts, no Kodi or Drive calls, so the queue step, the player and the Picture menu agree and
every rule is host-tested. The state file (upscale-copies.json) holds, per original Drive file id:
  {'label': '4K UHD', 'status': 'waiting'|'running'|'ready'|'failed'|'blocked'|'gone',
   'copy_id': Drive id of the copy when ready, 'size': bytes, 'progress': 0..100, 'error': text, ...}
DEC-044 (owner: "It wont allow me to cancel anything or open whats being done"): the page asks for Pause, Cancel this
copy, Remove from Up next, a new order and Cancel All through a small control file (upscale-control.json), which the
service applies (apply_control) at the start of each pass and checks while a copy is made, so a running copy never
writes over what the page asked. A cancelled copy ('cancelled') is not made again until its show's size is chosen again.
"""
import json
import os
import time

import picture

FILE = 'upscale-copies.json'
CONTROL = 'upscale-control.json'
RESERVE = 1024 ** 3                       # Drive space kept free beyond the copy's estimated size
LOW_BATTERY = 0.20                        # below this, no copy is made without a charger (board C wording)
HOT = ('serious', 'critical')             # iOS thermal states that hold the work
MBIT_PER_1080P = 4.0                      # kr_video's default rate for an upscaled copy (DEC-040 item 6)


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = {}
    data = data if isinstance(data, dict) else {}
    data.setdefault('copies', {})
    return data


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target + '.tmp', 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=1, sort_keys=True)
    os.replace(target + '.tmp', target)


def recover(data):
    """After the app was killed: a copy marked running is waiting again (it carries on from its last mark or starts
    over); nothing stays 'running' with no worker."""
    for entry in data.get('copies', {}).values():
        if entry.get('status') == 'running':
            entry['status'] = 'waiting'
            entry['resumed'] = entry.get('resumed', 0) + 1
    return data


def estimate_bytes(duration, label, width=1920, height=1080):
    size = picture.fitted(width, height, label) or picture.box(label)
    rate = max(6.0, MBIT_PER_1080P * size[0] * size[1] / (1920.0 * 1080.0)) * 1e6
    return int(float(duration or 0) * rate / 8 * 1.03)   # +3 % container and audio


def wanted_for(job, settings, media):
    """The size this prepared download should get, or None: the person's choice for its show (or the default for new
    downloads), only sizes above the picture, never larger than chosen, never HDR or 4K."""
    probe = (job or {}).get('probe') or {}
    if (job or {}).get('status') != 'done' or probe.get('hdr'):
        return None
    width, height = int(probe.get('width') or 0), int(probe.get('height') or 0)
    scope, entry = picture.resolve(settings, media)
    label = entry['upscale']
    if scope == 'default' and label == picture.OFF and settings.get('downloads', {}).get('prepare'):
        label = settings['downloads'].get('size') or '4K UHD'      # board G: automatic for new downloads
    return picture.target(width, height, label)


def plan(prep_state, data, settings, media_for, clock=time.time):
    """Adds a waiting entry for every prepared download that should have a copy and has none (or has one at another
    size). Returns the original ids added. media_for(job) gives the show/movie identity (TMDb) for per-show settings."""
    added = []
    copies = data.setdefault('copies', {})
    for job in (prep_state or {}).get('jobs', {}).values():
        original = str(job.get('prepared_id') or (job.get('source') or {}).get('id') or '')
        if not original:
            continue
        label = wanted_for(job, settings, media_for(job))
        entry = copies.get(original)
        if not label:
            continue
        if entry and entry.get('label') == label and entry.get('status') in ('waiting', 'running', 'ready', 'blocked'):
            continue
        if entry and entry.get('status') == 'failed' and entry.get('label') == label:
            continue                                   # retried by its own back-off, not re-added
        if entry and entry.get('status') == 'cancelled':
            continue                                   # the owner cancelled it (DEC-044); back only when the size is chosen again
        probe = job.get('probe') or {}
        copies[original] = {'label': label, 'status': 'waiting', 'name': (job.get('source') or {}).get('name', ''),
                            'width': int(probe.get('width') or 0), 'height': int(probe.get('height') or 0),
                            'duration': float(probe.get('duration') or 0),
                            'added': clock(),
                            'previous_copy': (entry or {}).get('copy_id') if entry and entry.get('status') == 'ready' else None}
        added.append(original)
    return added


def may_run(device, settings, now_playing=False):
    """(True, '') when the phone may make a copy now, else (False, the reason shown on the card)."""
    downloads = settings.get('downloads', {})
    charging = int(device.get('charging', -1))
    battery = float(device.get('battery', -1))
    if downloads.get('only_charging', True) and charging != 1:
        return False, 'Waiting for a charger'
    if charging != 1 and 0 <= battery < LOW_BATTERY:
        return False, 'Battery low · waiting for a charger'
    if int(device.get('low_power', 0)):
        return False, 'Low Power Mode is on'
    if device.get('thermal') in HOT:
        return False, 'Phone is warm · waiting'
    return True, ''


def drive_room(free_bytes, entry):
    """(True, needed) when Drive has room for the copy (plus RESERVE), else (False, needed). free_bytes None: unknown,
    allowed (the upload itself reports a full Drive)."""
    needed = estimate_bytes(entry.get('duration'), entry['label'], entry.get('width') or 1920, entry.get('height') or 1080)
    if free_bytes is None:
        return True, needed
    return free_bytes >= needed + RESERVE, needed


def next_job(data, clock=time.time):
    """The one copy to make next (one AI engine at a time): one already running first, else the oldest waiting whose
    back-off has passed. None when nothing is due."""
    copies = data.get('copies', {})
    running = [k for k, e in copies.items() if e.get('status') == 'running']
    if running:
        return running[0]
    due = [(e.get('order', float('inf')), e.get('added', 0), k) for k, e in copies.items()
           if e.get('status') in ('waiting', 'failed') and e.get('retry_after', 0) <= clock()]
    return min(due)[2] if due else None


def up_next(data, clock=time.time):
    """Up next in the order they will be made (the running one is not in it): [original id]."""
    copies = data.get('copies', {})
    due = [(e.get('order', float('inf')), e.get('added', 0), k) for k, e in copies.items() if e.get('status') in ('waiting', 'failed')]
    return [k for _, _, k in sorted(due)]


def control_path(profile):
    return os.path.join(os.path.dirname(path(profile)), CONTROL)


def control(profile):
    try:
        with open(control_path(profile), encoding='utf-8') as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        found = {}
    found = found if isinstance(found, dict) else {}
    for key in ('cancel', 'order'):
        found.setdefault(key, [])
    found.setdefault('paused', False)
    return found


def _write_control(profile, found):
    target = control_path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target + '.tmp', 'w', encoding='utf-8') as handle:
        json.dump(found, handle, sort_keys=True)
    os.replace(target + '.tmp', target)


def set_paused(profile, on):
    found = control(profile)
    found['paused'] = bool(on)
    _write_control(profile, found)


def paused(profile):
    return bool(control(profile).get('paused'))


def cancel(profile, originals):
    """Cancel this copy (B1) or Remove from Up next (B2): the copy stops or never starts; the original is not touched."""
    found = control(profile)
    found['cancel'] = sorted(set(found['cancel']) | {str(o) for o in originals})
    _write_control(profile, found)


def cancel_all(profile):
    found = control(profile)
    found['cancel_all'] = True
    found['paused'] = False
    _write_control(profile, found)


def reorder(profile, originals):
    found = control(profile)
    found['order'] = [str(o) for o in originals]
    _write_control(profile, found)


def cancelling(profile, original):
    found = control(profile)
    return bool(found.get('cancel_all')) or str(original) in found['cancel']


def apply_control(profile, data, clock=time.time):
    """The page's requests, applied to the copies (the service, once per pass). Returns True when data changed."""
    found = control(profile)
    copies = data.get('copies', {})
    changed = False
    gone = set(found['cancel'])
    if found.get('cancel_all'):
        gone |= {k for k, e in copies.items() if e.get('status') in ('waiting', 'running', 'failed')}
    for key in gone:
        entry = copies.get(key)
        if entry and entry.get('status') in ('waiting', 'running', 'failed'):
            entry.update(status='cancelled', cancelled=clock(), progress=0)
            for field in ('eta', 'note', 'retry_after'):
                entry.pop(field, None)
            changed = True
    if found['order']:
        for n, key in enumerate(found['order']):
            if key in copies:
                copies[key]['order'] = n
                changed = True
    if gone or found['order'] or found.get('cancel_all'):
        found.update(cancel=[], order=[], cancel_all=False)
        _write_control(profile, found)
    return changed


def revive(data, originals):
    """The show's size was chosen again: its cancelled copies may be made again (plan() adds them)."""
    for key in originals:
        entry = data.get('copies', {}).get(str(key))
        if entry and entry.get('status') == 'cancelled':
            del data['copies'][str(key)]
    return data


def failed(entry, error, clock=time.time):
    """A failure: HDR / same size / no AI engine are final ('blocked'); others retry with a back-off."""
    text = str(error)[:240]
    entry['error'] = text
    if any(word in text for word in ('HDR', 'already this size', 'not available on this device', 'needs iOS 26')):
        entry['status'] = 'blocked'
        return entry
    entry['status'] = 'failed'
    entry['attempts'] = entry.get('attempts', 0) + 1
    entry['retry_after'] = clock() + min(6 * 3600, 300 * 2 ** min(entry['attempts'] - 1, 6))
    return entry


def choose(data, original_id, wanted, on_drive):
    """The file to play: (drive id, label) of the copy when AI Upscale is on, the copy is ready and still on Drive,
    else (original_id, None). on_drive(id) says whether a file still exists; a deleted copy is marked 'gone' so the
    queue makes it again."""
    entry = data.get('copies', {}).get(str(original_id))
    if not wanted or wanted == picture.OFF or not entry or entry.get('status') != 'ready' or not entry.get('copy_id'):
        return str(original_id), None
    if picture.LABELS.index(entry['label']) > picture.LABELS.index(wanted):
        return str(original_id), None                    # never larger than chosen now
    if not on_drive(entry['copy_id']):
        entry['status'] = 'gone'
        entry.pop('copy_id', None)
        return str(original_id), None
    return entry['copy_id'], entry['label']


def menu_state(data, original_id, width, height, wanted, ai_available=True):
    """What the Picture menu says on AirPlay (board E): one of
    {'state': 'ready', 'label'} — the TV gets the copy;
    {'state': 'preparing', 'label', 'progress', 'eta'} — the original plays meanwhile;
    {'state': 'offer', 'label'} — "Prepare a 4K UHD copy";
    {'state': 'unavailable'} — "Not available on this iPhone";
    None — no upscaler for this video (4K, HDR, unknown size)."""
    offered = picture.above(width, height)
    if not offered:
        return None
    entry = data.get('copies', {}).get(str(original_id)) or {}
    label = picture.target(width, height, wanted) if wanted and wanted != picture.OFF else offered[-1]
    if entry.get('status') == 'ready' and entry.get('label') == label:
        return {'state': 'ready', 'label': label}
    if not ai_available:
        return {'state': 'unavailable'}
    if entry.get('status') in ('waiting', 'running') and entry.get('label') == label:
        return {'state': 'preparing', 'label': label, 'progress': int(entry.get('progress') or 0), 'eta': entry.get('eta', '')}
    if entry.get('status') == 'blocked':
        return None
    return {'state': 'offer', 'label': label}


ENGINE_IDS = {'video': 2, 'image': 3, 'fast': 4}
SLACK = 1.05


def pick_engine(support, width, height, label):
    """(engine id, words) of the AI model to use for this picture, or (None, why). Owner logs 0afdfd7b / 1ff17f50
    (build 302): this iPhone's AI models make 4x pictures only and the video model does not take 1080p, so "auto" took
    the image model and a 1920x1080 episode became 7680x4320 frames (about 265 MB each); iOS closed Kodi seconds later.
    An engine is used only when what it makes is no larger than the size asked for (the converter then fits it)."""
    support = support or {}
    if not support.get('os26'):
        return None, 'AI Upscale needs iOS 26 (not available on this device)'
    bw, bh = picture.box(label)
    made = []
    for name in ('video', 'image', 'fast'):
        e = support.get(name) or {}
        scale = float(e.get('scale') or 0)
        if not e.get('supported') or not e.get('fits') or scale < 1.2:
            continue
        w, h = int(width * scale), int(height * scale)
        if w > bw * SLACK or h > bh * SLACK:
            made.append('%s model %gx = %dx%d' % (name, scale, w, h))
            continue
        return ENGINE_IDS[name], '%s model, %gx' % (name, scale)
    if made:
        return None, ('not available on this device for %dx%d: its AI models would make %s, more than %s and more '
                      'memory than iOS gives an app' % (width, height, '; '.join(made), label))
    return None, 'not available on this device for %dx%d' % (width, height)


def copy_name(original_name, label):
    """'Naruto S01E03 [AI 4K UHD].mp4' beside the original on Drive."""
    stem = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
    return '%s [AI %s].mp4' % (stem, label)


def is_copy_name(name):
    return any(str(name).endswith(' [AI %s].mp4' % label) for label in picture.LABELS)
