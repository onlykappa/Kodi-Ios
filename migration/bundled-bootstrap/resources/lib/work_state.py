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
import re
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
SLOW_WORDS = {'airplay': 'Slower while AirPlay plays', 'video': 'Slower while a video plays', 'buffering': 'Waiting while the video buffers'}
STEP = {'conv': 'Converting', 'repack': 'Making it start faster', 'copy': 'AllDebrid → Drive',
        'upload': 'Uploading to Google Drive', 'down': 'Downloading', 'check': 'Checking Google Drive'}
NEEDS_TEXT = {
    'drive_signin': {'title': 'Sign in to Google Drive again',
                     'text': 'Google stopped accepting the saved sign-in. Downloads and conversions wait until you sign in; nothing is lost.',
                     'button': 'Sign in', 'action': 'ActivateWindow(Videos,plugin://plugin.googledrive/,return)'},
    'alldebrid_key': {'title': 'Add your AllDebrid key',
                      'text': 'Downloads to Google Drive wait until Umbrella has your AllDebrid key.',
                      'button': 'Open Umbrella', 'action': 'Addon.OpenSettings(plugin.video.umbrella)'},
    # Build 224 (build-223 log 27f59dcd: uploads paused for two hours, four downloads waiting, and only a grey line said
    # so): a paused upload with downloads waiting is a card at the top of Library status with Resume.
    'uploads_paused': {'title': 'Downloads are paused',
                       'text': 'Uploads to Google Drive are paused, so downloads from AllDebrid wait. Resume to continue where they stopped.',
                       'button': 'Resume', 'action': 'RunScript(service.kodi.ios.bootstrap,resume_uploads)'},
    'airplay_network': {'title': "Your TV couldn't reach this iPhone",
                       'text': "Your TV couldn't reach this iPhone. Check Settings › Privacy & Security › Local Network › Kodi, and that the TV and iPhone are on the same Wi-Fi.",
                       'button': 'Open Settings', 'action': 'RunScript(service.kodi.ios.bootstrap,airplay_settings)'},
}

# What the service knows that no file says (set from service.py's loops; one Kodi process).
_flags_lock = threading.Lock()
_flags = {'needs': {}, 'network': {}}


def need(key, on=True, profile=None):
    """Mark (or clear) something only the owner can fix (a NEEDS_TEXT key)."""
    with _flags_lock:
        if on and key in NEEDS_TEXT:
            _flags['needs'][key] = dict(NEEDS_TEXT[key])
        else:
            _flags['needs'].pop(key, None)
    if profile is not None and key in NEEDS_TEXT:
        # Kodi scripts and the service have separate Python interpreters. One marker per key avoids lost updates.
        path=os.path.join(str(profile),'addon_data','service.kodi.ios.bootstrap','needs',key)
        if on:
            os.makedirs(os.path.dirname(path),exist_ok=True)
            with open(path,'w',encoding='utf-8') as f:f.write('1')
        else:
            try:os.unlink(path)
            except FileNotFoundError:pass


def network(key, until=0.0, why=''):
    """Mark (or clear, until=0) a wait for the network or a busy server, retried at `until`."""
    with _flags_lock:
        if until:
            _flags['network'][key] = {'until': float(until), 'why': why}
        else:
            _flags['network'].pop(key, None)


def flags(profile=None):
    with _flags_lock:
        needs=dict(_flags['needs'])
        if profile is not None:
            for key in NEEDS_TEXT:
                if os.path.isfile(os.path.join(str(profile),'addon_data','service.kodi.ios.bootstrap','needs',key)):
                    needs[key]=NEEDS_TEXT[key]
        return {'needs': [dict(v, key=k) for k, v in sorted(needs.items())],
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
    first = job['slow_words'] if state == SLOWED and not job.get('phase_detail') else job['step']
    return ' · '.join(x for x in (first, speed(job.get('rate')), left(job.get('eta_s'))) if x)


# --- the snapshot ------------------------------------------------------------------------------------------------------
def _title(name):
    try:
        import drivelibrary
        return drivelibrary.display_title(name)
    except Exception:
        return str(name or '')

# Owner screenshot (2026-11-12): queued copies read '45e2c1e044af006c...' when Elementum handed over a pick without a
# release name, so the job's name was the torrent's id. A name that is only an id is replaced by, in order: the
# first file's name, the show's name from the cached TMDb details (show_names: {tmdb id: name}), then 'Download'.
HASH=re.compile(r'^[0-9a-fA-F]{32,40}$')
_NAMES = {}


def show_names(profile):
    """{show tmdb id: name} from the Library's cached show details (drive-library-art.json; no network)."""
    import json, os
    try:
        with open(os.path.join(str(profile), 'addon_data/service.kodi.ios.bootstrap/drive-library-art.json'), encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k.split(':', 1)[1]: v.get('name') for k, v in cache.items()
            if k.startswith('show:') and isinstance(v, dict) and v.get('name')}


def _download_title(job):
    title=_title(job.get('title') or job.get('name') or '')
    if not title or HASH.match(title.split(' · ')[0].strip()):
        files=[f.get('path') for f in job.get('files') or [] if f.get('path')]
        named=_title(files[0].rsplit('/',1)[-1]) if files else ''
        title=(named if named and not HASH.match(named) else '') or _NAMES.get(str(job.get('show_tmdb') or '')) or 'Download'
    try:
        if int(job.get('season') or 0)>0 and int(job.get('episode') or 0)>0 and ' · S' not in title:
            title+=' · S%d E%d'%(int(job['season']),int(job['episode']))
    except (TypeError,ValueError):pass
    return title


def _conversion(prep, runtime, now):
    """The conversion (or library check) running now, from the queue's 'current' and the heartbeat, or None."""
    import preparation_runtime
    current = preparation_runtime.current((prep or {}).get('current') or {},runtime)
    if not current.get('running') or not current.get('title'):
        return None
    fresh = bool(runtime) or now - float(current.get('updated') or 0) < ALIVE
    if not fresh:
        return None
    if current.get('title') == 'Movies and shows' or str(current.get('stage', '')).startswith('Checking'):
        return {'kind': 'check', 'title': 'Google Drive', 'name': '', 'step': STEP['check'], 'pct': int(current.get('progress') or 0),
                'indeterminate': True, 'rate': 0.0, 'eta_s': 0, 'tint': BLUE}
    stage = str(current.get('stage') or '')
    stage = stage.replace('Step 3 of 3 · ', '').strip()
    kind = current.get('kind') or ('repack' if stage == STEP['repack'] else 'conv')
    if stage in ('', 'Paused by you', 'Paused while a video plays', 'Stopped', 'Will try again'):
        stage = STEP[kind]
    return {'kind': kind, 'title': _title(current['title']), 'name': current['title'], 'step': stage,
            'pct': int(round(float(current.get('progress') or 0))), 'indeterminate': bool(current.get('indeterminate')),
            'rate': float(current.get('rate') or 0), 'eta_s': float(current.get('eta_s') or 0), 'tint': PURPLE,
            'held': bool(current.get('paused'))}


def _lanes(prep, now):
    """F2: the extra re-package lanes' cards (prep['lanes'], written by prepare_cloud.process_one(lane=N)), freshest
    first; a lane that stopped writing for ALIVE seconds is not shown."""
    out = []
    for key, current in sorted(((prep or {}).get('lanes') or {}).items()):
        if not isinstance(current, dict) or not current.get('running') or not current.get('title'):
            continue
        if now - float(current.get('updated') or 0) >= ALIVE:
            continue
        stage = str(current.get('stage') or '').replace('Step 3 of 3 · ', '').strip()
        if stage in ('', 'Paused by you', 'Paused while a video plays', 'Stopped', 'Will try again'):
            stage = STEP['repack']
        out.append({'kind': 'repack', 'title': _title(current['title']), 'name': current['title'], 'step': stage,
                    'pct': int(round(float(current.get('progress') or 0))), 'indeterminate': bool(current.get('indeterminate')),
                    'rate': float(current.get('rate') or 0), 'eta_s': float(current.get('eta_s') or 0), 'tint': PURPLE,
                    'held': bool(current.get('paused')), 'lane': key})
    return out


def episode_label(name):
    """'S01E03' from a file name (or '1x03'), else the cleaned file name."""
    import re
    base = str(name or '').rsplit('/', 1)[-1]
    m = re.search(r'(?i)\bS(\d{1,2})[ ._-]?E(\d{1,3})\b', base) or re.search(r'\b(\d{1,2})x(\d{2,3})\b', base)
    return 'S%02dE%02d' % (int(m.group(1)), int(m.group(2))) if m else _title(base.rsplit('.', 1)[0])


def _in_line(jobs):
    """The order the copier takes them in (debrid_drive.in_line): episode order within a show."""
    try:
        import debrid_drive
        return debrid_drive.in_line(jobs)
    except Exception:
        return jobs


def _copy_next(debrid):
    """What the AllDebrid → Drive copy does after the file it copies now (owner, build 205: a whole season showed as
    one download): the season's other episodes, then the other jobs, [{'kind', 'title', 'line'}] in that order."""
    copying = {str(c.get('job')) for c in ((debrid or {}).get('lanes') or {}).values() if c.get('job')}
    jobs = _in_line([j for j in (debrid or {}).get('jobs') or [] if j.get('status') not in ('done', 'failed')])
    # A job a lane copies now is on its own card, not in Up next (owner, build 329: four copies, one card).
    lead = jobs[:1]
    jobs = lead + [j for j in jobs[1:] if '%s:%s:%s' % (j.get('hash', ''), j.get('season', ''), j.get('episode', '')) not in copying]
    out = []
    for n, job in enumerate(jobs):
        title = _download_title(job)
        identity = {'hash':job.get('hash',''), 'id':'debrid:%s:%s:%s'%(job.get('hash',''),job.get('season',''),job.get('episode',''))}
        pending = [f for f in job.get('files') or [] if not f.get('done')]
        if n == 0:
            pending = pending[1:]   # the first one left is the one copying now
        if pending:
            for f in pending:
                # Owner screenshot (build 327): "Naruto Shippuden · S1 E1 · Naruto Shi…": a one-episode job's title already
                # names the episode; only a pack's files add theirs.
                named = title if ' · S' in title else '%s · %s' % (title, episode_label(f.get('path')))
                out.append(dict(identity, **{'id':identity['id']+':'+f.get('path',''), 'folder':f.get('path',''), 'kind': 'copy', 'title': named,
                            'line': 'Waiting · %s' % STEP['copy']}))
        elif n:
            out.append(dict(identity, **{'kind': 'copy', 'title': title,
                        'line': 'Waiting for AllDebrid' if job.get('status') in ('new', 'fetching') else 'Waiting · %s' % STEP['copy']}))
    return out


def _copies(debrid, now):
    """Owner screenshot (build 329): four copies ran, the status showed one ("1 working"). One card per lane that
    copies now (debrid_drive's 'lanes', each with the job it copies), else the single card _copy() makes:
    [(card, owner job)]."""
    debrid = debrid or {}
    jobs = _in_line([j for j in debrid.get('jobs') or [] if j.get('status') not in ('done', 'failed')])
    if not jobs:
        return []
    by_key = {'%s:%s:%s' % (j.get('hash', ''), j.get('season', ''), j.get('episode', '')): j for j in jobs}
    fresh = lambda c: now - max(float(c.get('updated') or 0), float(c.get('phase_at') or 0)) < 600
    lanes = [c for _, c in sorted((debrid.get('lanes') or {}).items(), key=lambda kv: int(kv[0]))
             if c.get('total') and fresh(c) and by_key.get(str(c.get('job')))]
    if len(lanes) > 1:
        out = []
        for lane in lanes:
            owner = by_key[str(lane['job'])]
            card = _copy({'jobs': [owner], 'current': lane}, now)
            if card:
                out.append((card, owner))
        if out:
            return out
    card = _copy(debrid, now)
    return [(card, jobs[0])] if card else []


def _copy(debrid, now):
    """The AllDebrid → Drive copy, or None."""
    # Owner (build 325): the card sat at "no answer for 23 min" while other lanes copied; show the lane that moved last.
    fresh = lambda c: max(float(c.get('updated') or 0), float(c.get('phase_at') or 0))
    lanes = [c for c in ((debrid or {}).get('current'), (debrid or {}).get('current_also')) if c]
    current = max(lanes, key=fresh) if lanes else {}
    jobs = _in_line([j for j in (debrid or {}).get('jobs') or [] if j.get('status') not in ('done', 'failed')])
    if not jobs:
        return None
    job = jobs[0]
    title = _download_title(job) or _title(current.get('name',''))
    retry = float(job.get('retry_at') or 0)
    if current.get('stage') == 'copying' and current.get('total'):
        sent, total = float(current.get('sent') or 0), float(current.get('total') or 0)
        count = int(current.get('count') or 0)
        if count > 1:   # one file of a season: name the episode, count the season
            title = '%s · %s' % (title, episode_label(current.get('file')))
        updated = current.get('updated')
        phase=current.get('phase','')
        if phase in ('reading','uploading','paused_playback') and current.get('phase_at') is not None:
            updated=max(float(updated or 0),float(current['phase_at']))
        quiet = updated is not None and now - float(updated) > COPY_QUIET
        step = '%s · %d of %d' % (STEP['copy'], int(current.get('index') or 1), count) if count > 1 else STEP['copy']
        words={'reading':'Reading download','uploading':'Uploading to Google Drive','paused_playback':'Paused for playback'}
        if phase in words:step=words[phase]+(' · %d of %d'%(int(current.get('index') or 1),count) if count>1 else '')
        out = {'kind': 'copy', 'title': title, 'name': current.get('name', ''), 'step': step, 'pct': int(100 * sent / total),
               'indeterminate': False, 'rate': 0.0 if quiet else float(current.get('rate') or 0),
               'eta_s': 0 if quiet else float(current.get('eta_s') or 0), 'tint': BLUE, 'sent': sent, 'total': total,
               'hash': job.get('hash', ''), 'folder': current.get('folder', ''),'phase_detail':phase in words,'transfer_phase':phase}
        if quiet and phase!='paused_playback':
            out['wait'] = ('Waiting for download' if phase=='reading' else 'Waiting for Google Drive')+' · no answer for %d min' % max(1,int((now-float(updated))//60))
        if (job.get('tries') or job.get('net_tries')) and retry > now:
            out['wait'] = 'Waiting for the network · %s' % retry_text(retry, now)
        if (debrid or {}).get('hold') == 'wifi':
            out['wait'] = 'Waiting for Wi-Fi · copies run on Wi-Fi only (Transfer settings)'
        out['playback_held']=phase=='paused_playback' and not ((job.get('tries') or job.get('net_tries')) and retry>now)
        return out
    if current.get('stage') == 'fetching':
        return {'kind': 'copy', 'title': title, 'name': current.get('name', ''), 'step': 'AllDebrid is fetching it',
                'pct': int(current.get('sent') or 0), 'indeterminate': False, 'rate': 0.0, 'eta_s': 0, 'tint': BLUE,
                'hash': job.get('hash', '')}
    if (job.get('tries') or job.get('net_tries')) and retry > now:
        return {'kind': 'copy', 'title': title, 'name': job.get('name', ''), 'step': STEP['copy'], 'pct': 0, 'indeterminate': False,
                'rate': 0.0, 'eta_s': 0, 'tint': BLUE, 'hash': job.get('hash', ''),
                'wait': 'Waiting for the network · %s' % retry_text(retry, now)}
    if (debrid or {}).get('hold') == 'wifi':
        return {'kind': 'copy', 'title': title, 'name': job.get('name', ''), 'step': STEP['copy'], 'pct': 0, 'indeterminate': False,
                'rate': 0.0, 'eta_s': 0, 'tint': BLUE, 'hash': job.get('hash', ''),
                'wait': 'Waiting for Wi-Fi · copies run on Wi-Fi only (Transfer settings)'}
    return {'kind':'copy','title':title,'name':job.get('name',''),'step':
            'Waiting for AllDebrid' if job.get('status') in ('new','fetching') else 'Starting transfer to Google Drive',
            'pct':0,'indeterminate':True,'queued':True,'rate':0.0,'eta_s':0,'tint':BLUE,'hash':job.get('hash','')}


def next_what(job):
    """Up next's word for a waiting job (PR #24 roadmap ticket, build-356 screenshot: re-packages read "Convert · 4.3 GB").
    'faster start' for a known re-package (the picture is copied), 'convert' only when the probe says the picture is
    re-encoded, 'prepare' while it is not known yet (a job is read when its turn comes)."""
    if job.get('repack'):
        return 'faster start'
    probe = job.get('probe') or {}
    if probe and probe.get('copy_video') is False:
        return 'convert'
    if probe.get('copy_video'):
        return 'faster start'
    return 'prepare'


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
             'what': next_what(j), 'size': int((j.get('source') or {}).get('size') or 0)}
            for _, j in jobs]


def build(inp, now):
    """The snapshot every page and the bell show. inp: {'prep': queue state, 'runtime': heartbeat or {}, 'debrid': AllDebrid
    state, 'phone': [notices.uploads phone entries], 'torrents': [notices.downloads entries], 'paused': {'conv', 'up'},
    'slow': '' | 'video' | 'airplay', 'needs': [...], 'network': [...]}."""
    _NAMES.clear()
    _NAMES.update(inp.get('show_names') or {})
    slow = inp.get('slow') or ''
    slow = slow if slow in SLOW_WORDS else ''
    paused = inp.get('paused') or {}
    jobs = []

    def add(job, held=False, wait=''):
        if held:
            state = PAUSED
        elif wait:
            state = NETWORK
        elif job.get('queued'):
            state = QUEUED
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
    # F2 (PR #24): re-packages running in extra lanes beside the main one, each with its own card and percentage.
    lane_names = []
    for lane in _lanes(inp.get('prep'), now):
        lane_names.append(lane['name'])
        add(lane, held=lane.pop('held', False) or bool(paused.get('conv')))
    for copy, owner in _copies(inp.get('debrid'), now):
        copy['id']='debrid:%s:%s:%s'%(owner.get('hash',''),owner.get('season',''),owner.get('episode',''))
        playback_held=copy.pop('playback_held',False)
        add(copy, held=bool(paused.get('up')), wait=copy.pop('wait', ''))
        if paused.get('up'):jobs[-1]['line']='Uploads paused · resume to download'
        if (playback_held or slow in ('video','buffering')) and not paused.get('up') and jobs[-1]['state'] != NETWORK:
            # Preserve the approved slowed-state surface; describe the actual hold in its existing line.
            text='Pausing for playback' if copy.get('transfer_phase')=='uploading' and not playback_held else 'Paused for playback'
            jobs[-1].update(line=text,rate=0,eta_s=0)
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
    nexts = [n for n in _next(inp.get('prep'), conv['name'] if conv else '')
             if n['title'] not in {_title(x) for x in lane_names}]
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
    elif nexts or any(j['state']==QUEUED for j in jobs):
        mode = QUEUED
    else:
        mode = IDLE
    wait_text = ''
    if waits:
        w = min(waits, key=lambda x: x['until'])
        wait_text = '%s · %s' % (w.get('why') or 'Waiting for the network', retry_text(w['until'], now))
    lead = (moving or jobs or [None])[0]
    drive_next = _copy_next(inp.get('debrid'))
    for j in drive_next:
        j.update(state=PAUSED if paused.get('up') else QUEUED,step=j['line'],pct=0,indeterminate=True,
                 tint=BLUE,tint_now=GREY if paused.get('up') else BLUE,rate=0,eta_s=0)
        if paused.get('up'):j['line']='Uploads paused · waiting to download'
    return {'at': now, 'mode': mode, 'slow': slow, 'slow_words': SLOW_WORDS.get(slow, ''), 'jobs': jobs, 'next': nexts,
            'drive_next': drive_next,
            # Unfinished AllDebrid -> Drive copies (the Library status sheet offers Cancel All when there are several).
            'copies_waiting': sum(1 for j in ((inp.get('debrid') or {}).get('jobs') or []) if j.get('status') not in ('done', 'failed')),
            'needs': needs, 'wait': wait_text,
            'running': len(moving), 'headline': headline(mode, jobs, nexts + drive_next, needs, wait_text, slow),
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
    queued=len(nexts)+sum(j['state']==QUEUED for j in jobs)
    if queued:
        parts.append('%d up next' % queued)
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


def pending_cancels(debrid, leaving, now):
    """ISSUE-208 (owner: "deleting the download queue is also slow as hell, it needs to be instant"): a Cancel or
    Cancel All is written at once but the copier applies it on its next turn; the pages show it as done straight away."""
    leaving = {str(h).lower() for h in leaving or ()}
    if not leaving:
        return debrid
    jobs = [dict(j, status='failed', error='Cancelled', finished=now)
            if j.get('status') not in ('done', 'failed') and str(j.get('hash', '')).lower() in leaving else j
            for j in (debrid or {}).get('jobs') or []]
    out = dict(debrid or {}, jobs=jobs)
    out.pop('current', None)   # a cancelled copy's card goes; the lanes left show their own cards
    return out


def current(profile, now=None):
    """Refresh durable Drive transfers immediately; retain the service's other jobs and their freshness.

    No network calls. Rereading the queue must not revive stale conversion or torrent measurements.
    """
    import debrid_drive,transfer_control
    now=time.time() if now is None else now
    state=load(profile,now) or build({},now)
    paused={k:transfer_control.paused(profile,k) for k in transfer_control.KINDS}
    debrid=pending_cancels(debrid_drive.load(profile),transfer_control.cancelled_copies(profile),now)
    copies=build({'debrid':debrid,'paused':paused,'slow':state.get('slow',''),'show_names':show_names(profile)},now)
    state=dict(state,copy_left=copy_bytes_left(debrid),
               copies_waiting=sum(1 for j in debrid.get('jobs') or [] if j.get('status') not in ('done','failed')))
    jobs=[j for j in state.get('jobs',[]) if j.get('kind')!='copy']+copies['jobs']
    nexts=state.get('next') or [];drive_next=copies['drive_next'];needs=state.get('needs') or []
    moving=[j for j in jobs if j['state'] in MOVING]
    if needs:mode=NEEDS
    elif moving:mode=SLOWED if all(j['state']==SLOWED for j in moving) else RUNNING
    elif any(j['state']==PAUSED for j in jobs) or any(j.get('paused') for j in nexts):mode=PAUSED
    elif any(j['state']==NETWORK for j in jobs) or state.get('wait'):mode=NETWORK
    elif nexts or drive_next or any(j['state']==QUEUED for j in jobs):mode=QUEUED
    elif any(j['state']==STALE_STATE for j in jobs):mode=STALE_STATE
    else:mode=IDLE
    lead=(moving or jobs or [None])[0]
    return dict(state,jobs=jobs,drive_next=drive_next,mode=mode,running=len(moving),
                headline=headline(mode,jobs,nexts+drive_next,needs,state.get('wait',''),state.get('slow','')),
                bell={'state':mode,'pct':lead['pct'] if lead and lead['state'] in MOVING else 0,
                      'tint':(GREY if mode==SLOWED else lead['tint']) if lead and mode in MOVING else '',
                      'count':len(moving),'needs':len(needs)})


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
            inp = gather()
            inp.setdefault('show_names', show_names(profile))
            state = build(inp, clock())
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


def copy_bytes_left(debrid):
    """E17: bytes still to copy to Drive across every unfinished job (Drive's confirmed position for a file under way;
    jobs AllDebrid has not listed yet count as the average file seen). None when nothing is known."""
    jobs = [j for j in (debrid or {}).get('jobs') or [] if j.get('status') not in ('done', 'failed')]
    lanes = {str(c.get('file')): float(c.get('sent') or 0) for c in ((debrid or {}).get('lanes') or {}).values()}
    sizes, left, unknown = [], 0.0, 0
    for job in jobs:
        files = [f for f in job.get('files') or [] if not f.get('done')]
        if not job.get('files'):
            unknown += 1
            continue
        for f in files:
            size = float(f.get('size') or 0)
            sizes.append(size)
            sent = max([v for k, v in lanes.items() if k and (k == f.get('drive_name') or k.endswith(str(f.get('path', '')).rsplit('/', 1)[-1]))] or [0])
            left += max(0.0, size - sent)
        sizes += [float(f.get('size') or 0) for f in job.get('files') or [] if f.get('done')]
    if unknown:
        known = [x for x in sizes if x > 0]
        if not known:
            return None
        left += unknown * sum(known) / len(known)
    return left if jobs else 0.0


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
        if (rate <= 0 or any(not j.get('size') for j in nexts)) and not state.get('copy_left'):
            return ''
        if rate > 0 and all(j.get('size') for j in nexts):
            seconds += sum(float(j['size']) / rate for j in nexts)
    # E17 (owner screenshots: "about 84 h 40 min" from a starved conversion rate; "about 16 min" with 31 episodes waiting,
    # counting the copy under way only): copies are the bytes left in every waiting and running copy over all lanes'
    # speed together; conversions run beside them, so the longer of the two.
    copy_rate = sum(float(j.get('rate') or 0) for j in state.get('jobs') or [] if j.get('kind') == 'copy' and j.get('state') in MOVING)
    copies = (float(state['copy_left']) / copy_rate) if state.get('copy_left') and copy_rate > 0 else 0.0
    if conv and rate < 64 * 1024 and copies:
        seconds = float((conv or {}).get('eta_s') or 0) if not nexts else 0.0   # a starved read rate says nothing about the queue
    seconds = max([seconds, copies] + [float(j.get('eta_s') or 0) for j in state.get('jobs') or []])
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
            '' if job.get('kind')=='copy' and job.get('id') else str(job.get('folder') or ''))
