"""One status model for every page and the bell (build 193, owner: "Notification center isn't linked with Library
status properly … it still says paused as a video plays … if I click on it it says nothing is moving").

Before this, Library status, Notifications, Transfers and the bell each read different files at different ages
(1 s, 15 s, 30 s, 60 s, none; docs/LOG-REVIEW-192.md cause 8) and guessed the reason for a pause. Now the bootstrap
service builds one snapshot about every EVERY seconds from the workers' own files and its own knowledge (who paused,
what plays, what needs the owner) and writes it to work-state.json; every page and the bell read only that.

States (docs/plans/build-193-roadmap.md, Phase 2):
  running          moving at full speed
  slowed           a video or AirPlay plays: still moving, at a share of the line (slowdown.py)
  paused_by_you    the owner's long press › Pause
  needs_you        only the owner can fix it (Drive sign-in, AllDebrid key): one sentence and one button
  waiting_network  offline, a server busy, a retry wait
  queued           in line ("Up next · #2")
  ready / kept     done / kept as it is (Library status rows)
Rules: a snapshot older than STALE seconds is never shown as running (load() marks it stale); "slower while a video
plays" only when Player.HasVideo is true (the service passes slowdown.reason(), never a page); the reason is stored
with the state.

build() is pure (no Kodi), so every rule is tested on its own (scripts/test_work_state.py).
"""
import json
import os
import threading
import time

FILE = 'work-state.json'
EVERY = 2            # seconds between snapshots
STALE = 6            # older than this, nothing in it is shown as running
ALIVE = 15           # a conversion with no heartbeat and no progress for this long is not running
COPY_QUIET = 60      # an AllDebrid copy with no progress for this long waits for the network
PURPLE, BLUE, GREY = 'FFBF5AF2', 'FF0A84FF', 'FF8E8E93'
RUNNING, SLOWED, PAUSED, NEEDS, NETWORK, QUEUED, IDLE, STALE_STATE = (
    'running', 'slowed', 'paused_by_you', 'needs_you', 'waiting_network', 'queued', 'idle', 'stale')
MOVING = (RUNNING, SLOWED)
SLOW_WORDS = {'airplay': 'Slower while AirPlay plays', 'video': 'Slower while a video plays'}
STEP = {'conv': 'Converting', 'repack': 'Making it start faster', 'copy': 'AllDebrid → Drive',
        'upload': 'Uploading to Google Drive', 'down': 'Downloading', 'check': 'Checking Google Drive'}
NEEDS_TEXT = {
    'drive_signin': {'title': 'Sign in to Google Drive again',
                     'text': 'Google stopped accepting the saved sign-in. Downloads and conversions wait until you sign in; nothing is lost.',
                     'button': 'Sign in', 'action': 'ActivateWindow(Videos,plugin://plugin.googledrive/,return)'},
    'alldebrid_key': {'title': 'Add your AllDebrid key',
                      'text': 'Downloads to Google Drive wait until Umbrella has your AllDebrid key.',
                      'button': 'Open Umbrella', 'action': 'Addon.OpenSettings(plugin.video.umbrella)'},
}

# What the service knows that no file says (set from service.py's loops; one Kodi process).
_flags_lock = threading.Lock()
_flags = {'needs': {}, 'network': {}}


def need(key, on=True):
    """Mark (or clear) something only the owner can fix (a NEEDS_TEXT key)."""
    with _flags_lock:
        if on and key in NEEDS_TEXT:
            _flags['needs'][key] = dict(NEEDS_TEXT[key])
        else:
            _flags['needs'].pop(key, None)


def network(key, until=0.0, why=''):
    """Mark (or clear, until=0) a wait for the network or a busy server, retried at `until`."""
    with _flags_lock:
        if until:
            _flags['network'][key] = {'until': float(until), 'why': why}
        else:
            _flags['network'].pop(key, None)


def flags():
    with _flags_lock:
        return {'needs': [dict(v, key=k) for k, v in sorted(_flags['needs'].items())],
                'network': [dict(v, key=k) for k, v in sorted(_flags['network'].items())]}


def location(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


# --- words -------------------------------------------------------------------------------------------------------------
def speed(rate):
    rate = float(rate or 0)
    if rate <= 0:
        return ''
    return '%d KB/s' % round(rate / 1024) if rate < 1048576 else '%.1f MB/s' % (rate / 1048576.0)


def left(seconds):
    """'6 min left', '1 h 20 min left', 'less than a minute left' ('' when unknown)."""
    try:
        seconds = float(seconds or 0)
    except (TypeError, ValueError):
        return ''
    if seconds <= 0 or seconds > 14 * 86400:
        return ''
    m = int(seconds // 60)
    if m < 1:
        return 'less than a minute left'
    return '%d min left' % m if m < 60 else '%d h%s left' % (m // 60, ' %d min' % (m % 60) if m % 60 else '')


def retry_text(until, now):
    wait = max(0, float(until or 0) - now)
    if wait < 60:
        return 'trying again in a moment'
    m = int(round(wait / 60.0))
    return 'trying again in %d min' % m if m < 60 else 'trying again in %d h' % (m // 60)


def line(job):
    """The one status line of a job (the same on every page): its step or why it waits, its speed, its time left."""
    state = job['state']
    if state == PAUSED:
        return 'Paused by you'
    if state == NETWORK:
        return job.get('why') or 'Waiting for the network'
    if state == STALE_STATE:
        return 'Updating…'
    first = job['slow_words'] if state == SLOWED else job['step']
    return ' · '.join(x for x in (first, speed(job.get('rate')), left(job.get('eta_s'))) if x)


# --- the snapshot ------------------------------------------------------------------------------------------------------
def _title(name):
    try:
        import drivelibrary
        return drivelibrary.display_title(name)
    except Exception:
        return str(name or '')


def _conversion(prep, runtime, now):
    """The conversion (or library check) running now, from the queue's 'current' and the heartbeat, or None."""
    current = dict((prep or {}).get('current') or {})
    if not current.get('running') or not current.get('title'):
        return None
    fresh = bool(runtime) or now - float(current.get('updated') or 0) < ALIVE
    if not fresh:
        return None
    if current.get('title') == 'Movies and shows' or str(current.get('stage', '')).startswith('Checking'):
        return {'kind': 'check', 'title': 'Google Drive', 'name': '', 'step': STEP['check'], 'pct': int(current.get('progress') or 0),
                'indeterminate': True, 'rate': 0.0, 'eta_s': 0, 'tint': BLUE}
    stage = str((runtime or {}).get('phase') if runtime and not runtime.get('known') else current.get('stage') or '')
    stage = stage.replace('Step 3 of 3 · ', '').strip()
    kind = current.get('kind') or ('repack' if stage == STEP['repack'] else 'conv')
    if stage in ('', 'Paused by you', 'Paused while a video plays', 'Stopped', 'Will try again'):
        stage = STEP[kind]
    return {'kind': kind, 'title': _title(current['title']), 'name': current['title'], 'step': stage,
            'pct': int(round(float(current.get('progress') or 0))), 'indeterminate': bool(current.get('indeterminate')),
            'rate': float(current.get('rate') or 0), 'eta_s': float(current.get('eta_s') or 0), 'tint': PURPLE,
            'held': bool(current.get('paused'))}


def _copy(debrid, now):
    """The AllDebrid → Drive copy, or None."""
    current = (debrid or {}).get('current') or {}
    jobs = [j for j in (debrid or {}).get('jobs') or [] if j.get('status') not in ('done', 'failed')]
    if not jobs:
        return None
    job = jobs[0]
    title = _title(job.get('title') or job.get('name') or current.get('name', ''))
    retry = float(job.get('retry_at') or 0)
    if current.get('stage') == 'copying' and current.get('total'):
        sent, total = float(current.get('sent') or 0), float(current.get('total') or 0)
        updated = current.get('updated')
        quiet = updated is not None and now - float(updated) > COPY_QUIET
        out = {'kind': 'copy', 'title': title, 'name': current.get('name', ''), 'step': STEP['copy'], 'pct': int(100 * sent / total),
               'indeterminate': False, 'rate': 0.0 if quiet else float(current.get('rate') or 0),
               'eta_s': 0 if quiet else float(current.get('eta_s') or 0), 'tint': BLUE, 'sent': sent, 'total': total,
               'hash': job.get('hash', ''), 'folder': current.get('folder', '')}
        if quiet:
            out['wait'] = 'Waiting for Google Drive · no answer for %d min' % max(1, int((now - float(updated)) // 60))
        if job.get('tries') and retry > now:
            out['wait'] = 'Waiting for the network · %s' % retry_text(retry, now)
        return out
    if current.get('stage') == 'fetching':
        return {'kind': 'copy', 'title': title, 'name': current.get('name', ''), 'step': 'AllDebrid is fetching it',
                'pct': int(current.get('sent') or 0), 'indeterminate': False, 'rate': 0.0, 'eta_s': 0, 'tint': BLUE,
                'hash': job.get('hash', '')}
    if job.get('tries') and retry > now:
        return {'kind': 'copy', 'title': title, 'name': job.get('name', ''), 'step': STEP['copy'], 'pct': 0, 'indeterminate': False,
                'rate': 0.0, 'eta_s': 0, 'tint': BLUE, 'hash': job.get('hash', ''),
                'wait': 'Waiting for the network · %s' % retry_text(retry, now)}
    return None


def _next(prep, running_name):
    """Up next, in the order the queue picks: [{'title', 'what', 'size', 'id'}]."""
    try:
        import prepare_downloads
        order = prepare_downloads.order_key
    except Exception:
        order = lambda slot, job: (-job.get('priority', 0), 1 if job.get('repack') else 0, slot)
    jobs = [(slot, j) for slot, j in ((prep or {}).get('jobs') or {}).items()
            if j.get('status') in ('waiting', 'paused') and not j.get('kept') and not j.get('blocked')
            and (j.get('source') or {}).get('name') not in (running_name, _title(running_name) if running_name else None)]
    jobs.sort(key=lambda pair: order(*pair))
    return [{'id': str((j.get('source') or {}).get('id', '')), 'title': _title((j.get('source') or {}).get('name', '')),
             'what': 'faster start' if j.get('repack') else 'convert', 'size': int((j.get('source') or {}).get('size') or 0)}
            for _, j in jobs]


def build(inp, now):
    """The snapshot every page and the bell show. inp: {'prep': queue state, 'runtime': heartbeat or {}, 'debrid': AllDebrid
    state, 'phone': [notices.uploads phone entries], 'torrents': [notices.downloads entries], 'paused': {'conv', 'up'},
    'slow': '' | 'video' | 'airplay', 'needs': [...], 'network': [...]}."""
    slow = inp.get('slow') or ''
    slow = slow if slow in SLOW_WORDS else ''
    paused = inp.get('paused') or {}
    jobs = []

    def add(job, held=False, wait=''):
        if held:
            state = PAUSED
        elif wait:
            state = NETWORK
        elif slow:
            state = SLOWED
        else:
            state = RUNNING
        job = dict(job, state=state, slow=slow if state == SLOWED else '', slow_words=SLOW_WORDS.get(slow, ''), why=wait)
        job['line'] = line(job)
        job['tint_now'] = GREY if state != RUNNING else job['tint']
        jobs.append(job)

    conv = _conversion(inp.get('prep'), inp.get('runtime'), now)
    if conv:
        add(conv, held=conv.pop('held', False) or (paused.get('conv') and conv['kind'] != 'check'))
    copy = _copy(inp.get('debrid'), now)
    if copy:
        add(copy, held=bool(paused.get('up')), wait=copy.pop('wait', ''))
    for u in inp.get('phone') or ():
        add({'kind': 'upload', 'title': u.get('title', ''), 'name': u.get('title', ''), 'step': STEP['upload'],
             'pct': int(u.get('progress') or 0), 'indeterminate': False, 'rate': float(u.get('rate') or 0), 'eta_s': 0,
             'tint': BLUE, 'folder': u.get('folder', '')}, held=bool(paused.get('up')))
    for d in inp.get('torrents') or ():
        add({'kind': 'down', 'title': d.get('title', ''), 'name': d.get('title', ''), 'step': STEP['down'],
             'pct': int(d.get('progress') or 0), 'indeterminate': False, 'rate': float(d.get('rate') or 0),
             'eta_s': float(d.get('eta_s') or 0), 'tint': BLUE, 'id': d.get('id', '')}, held=bool(d.get('paused')))
    needs = list(inp.get('needs') or ())
    waits = [w for w in inp.get('network') or () if float(w.get('until') or 0) > now]
    nexts = _next(inp.get('prep'), conv['name'] if conv else '')
    if paused.get('conv') and not conv and nexts:
        # Paused while nothing converts: the next one waits for the owner, and says so.
        nexts[0]['paused'] = True
    moving = [j for j in jobs if j['state'] in MOVING]
    if needs:
        mode = NEEDS
    elif moving:
        mode = SLOWED if all(j['state'] == SLOWED for j in moving) else RUNNING
    elif any(j['state'] == PAUSED for j in jobs) or (paused.get('conv') and nexts):
        mode = PAUSED
    elif waits or any(j['state'] == NETWORK for j in jobs):
        mode = NETWORK
    elif nexts:
        mode = QUEUED
    else:
        mode = IDLE
    wait_text = ''
    if waits:
        w = min(waits, key=lambda x: x['until'])
        wait_text = '%s · %s' % (w.get('why') or 'Waiting for the network', retry_text(w['until'], now))
    lead = (moving or jobs or [None])[0]
    return {'at': now, 'mode': mode, 'slow': slow, 'slow_words': SLOW_WORDS.get(slow, ''), 'jobs': jobs, 'next': nexts,
            'needs': needs, 'wait': wait_text,
            'running': len(moving), 'headline': headline(mode, jobs, nexts, needs, wait_text, slow),
            'bell': {'state': mode, 'pct': lead['pct'] if lead and lead['state'] in MOVING else 0,
                     'tint': (GREY if mode == SLOWED else lead['tint']) if lead and mode in MOVING else '',
                     'count': len(moving), 'needs': len(needs)}}


def headline(mode, jobs, nexts, needs, wait_text, slow):
    """The page-top line ('2 running · 2 up next') and the empty state's words. 'Nothing is moving' only when nothing
    runs, waits or needs the owner."""
    if mode == IDLE:
        return 'Nothing is moving right now'
    parts = []
    moving = sum(1 for j in jobs if j['state'] in MOVING)
    if moving:
        parts.append('%d running' % moving)
    held = sum(1 for j in jobs if j['state'] == PAUSED)
    if held or mode == PAUSED:
        parts.append('paused by you')
    if needs:
        parts.append('%d need%s you' % (len(needs), 's' if len(needs) == 1 else ''))
    if nexts:
        parts.append('%d up next' % len(nexts))
    if mode == NETWORK and wait_text and not moving:
        parts.insert(0, wait_text)
    if mode == SLOWED and slow:
        parts.append(SLOW_WORDS[slow].lower())
    return ' · '.join(parts)


# --- writing and reading -----------------------------------------------------------------------------------------------
def save(profile, state):
    path = location(profile)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f)
    os.replace(tmp, path)


def load(profile, now=None):
    """The latest snapshot. Older than STALE seconds (the service stopped, Kodi was closed): nothing in it is shown as
    running; the jobs say 'Updating…' and the mode is 'stale'. None when there is none."""
    now = time.time() if now is None else now
    try:
        with open(location(profile), encoding='utf-8') as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    return stale(state, now)


def stale(state, now):
    if now - float(state.get('at') or 0) <= STALE:
        return state
    state = dict(state, mode=STALE_STATE, running=0)
    state['jobs'] = [dict(j, state=STALE_STATE, line='Updating…', rate=0, tint_now=GREY) if j.get('state') in MOVING else j
                     for j in state.get('jobs') or []]
    state['bell'] = {'state': STALE_STATE, 'pct': 0, 'tint': '', 'count': 0, 'needs': len(state.get('needs') or [])}
    if state.get('headline') and any(j.get('state') == STALE_STATE for j in state['jobs']):
        state['headline'] = 'Updating…'
    return state


def job(state, kind):
    """The first job of a kind ('conv' includes 're-pack'), or None."""
    kinds = ('conv', 'repack') if kind == 'conv' else ('copy', 'upload') if kind == 'up' else (kind,)
    for j in (state or {}).get('jobs') or []:
        if j.get('kind') in kinds:
            return j
    return None


BELL = ('Notices.Active', 'Notices.State', 'Notices.Pct', 'Notices.Tint', 'Notices.Count', 'Notices.Needs')


def bell_properties(state):
    """Home window properties for the bell: active while something moves; the state, its %, ring tint, how many run,
    how many need the owner."""
    b = (state or {}).get('bell') or {}
    moving = b.get('state') in MOVING
    return {'Notices.Active': 'true' if moving else '', 'Notices.State': b.get('state', ''),
            'Notices.Pct': str(int(b.get('pct') or 0)) if moving else '', 'Notices.Tint': b.get('tint', '') if moving else '',
            'Notices.Count': str(b.get('count') or '') if moving and b.get('count') else '',
            'Notices.Needs': str(b.get('needs')) if b.get('needs') else ''}


def publish(profile, gather, wait, every=EVERY, set_property=None, clock=time.time, log=lambda text: None):
    """The service loop: gather() -> build() input; write the snapshot every `every` seconds and keep the bell's
    properties current (only when they change)."""
    last = None
    while not wait(every):
        try:
            state = build(gather(), clock())
            save(profile, state)
            if set_property:
                props = bell_properties(state)
                if props != last:
                    for k, v in props.items():
                        set_property(k, v)
                    last = props
        except Exception as error:
            log('work state: %s: %s' % (type(error).__name__, error))


def align(prep_state, state):
    """Library status and the Queue still lay out from the queue's own state; this makes them agree with the model:
    the movie is 'preparing' only while the model has it moving or paused by the owner, with the model's line."""
    current = (prep_state or {}).get('current')
    if not current or state is None:
        return prep_state
    conv = job(state, 'conv')
    current = dict(current)
    if conv and conv.get('name') == current.get('title') and conv['state'] in MOVING + (PAUSED,):
        current.update(running=True, stage='Step 3 of 3 · ' + (conv['line'] if conv['state'] != RUNNING else conv['step']))
        if conv['state'] != RUNNING:
            current['detail'] = ''
            current['eta'] = ''
    else:
        current['running'] = False
    return dict(prep_state, current=current)


def remaining_text(state):
    """One queue estimate for the summary and Queue, from the published model only.

    Sequential preparation uses the current read rate for the queued source sizes;
    parallel copies contribute their remaining time via max, not by double counting.
    No estimate while paused, stale, waiting, or before the rate is measured.
    """
    if not state or state.get('mode') not in MOVING:
        return ''
    conv = job(state, 'conv')
    nexts = state.get('next') or []
    seconds = float((conv or {}).get('eta_s') or 0)
    rate = float((conv or {}).get('rate') or 0)
    if nexts:
        if rate <= 0 or any(not j.get('size') for j in nexts):
            return ''
        seconds += sum(float(j['size']) / rate for j in nexts)
    seconds = max([seconds] + [float(j.get('eta_s') or 0) for j in state.get('jobs') or []])
    if seconds <= 0:
        return ''
    m = max(1, int(seconds // 60))
    return 'about ' + ('%d min' % m if m < 60 else '%d h%s' % (m // 60, ' %d min' % (m % 60) if m % 60 else ''))


def metrics_line(job):
    """Library's sparkline caption; the step already has its own line above it."""
    if not job:
        return ''
    if job.get('state') != RUNNING:
        return job['line']
    return ' · '.join(x for x in (speed(job.get('rate')), left(job.get('eta_s'))) if x) or job['line']



def job_key(job):
    """Stable identity for per-job presentation state; titles never identify Drive copies."""
    job=job or {}
    return (job.get('kind',''), str(job.get('id') or job.get('hash') or job.get('name') or job.get('title') or ''),
            str(job.get('folder') or ''))
