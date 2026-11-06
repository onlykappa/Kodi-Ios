"""Downloads that go straight to Google Drive through AllDebrid (owner, build 160: "a movie im downloading goes onto my
phone still … if i do a large movie it wont ever download"; chose "AllDebrid straight to Drive").

Elementum's navigation and dedicated Download action queue the selected URI before its local engine starts.
AllDebrid fetches the torrent on its servers, then the service copies each video to Drive in bounded RAM chunks.
Nothing is written to phone media storage. Both download modes use this path; watch requests wait for a prepared
Drive copy. A restart resumes acknowledged Drive ranges. Legacy local torrents still use adopt() below.

State: addon_data/service.kodi.ios.bootstrap/debrid-drive.json {'jobs': [...], 'current': {...}}.
"""
import json
import fcntl
import os
import time
import urllib.request
from pathlib import Path

import alldebrid
import driveupload

FILE = 'debrid-drive.json'
TOP = driveupload.TOP


def location(profile):
    return Path(profile) / 'addon_data/service.kodi.ios.bootstrap' / FILE


def load(profile):
    try:
        state = json.loads(location(profile).read_text(encoding='utf-8'))
        return state if isinstance(state, dict) else {'jobs': []}
    except (OSError, ValueError):
        return {'jobs': []}


def save(profile, state, enqueue=False):
    # UI scripts can enqueue while the service is in a long HTTP transfer. Merge new
    # jobs and watch requests under a short cross-process lock; never lose that enqueue.
    path = location(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=load(profile)
        key=lambda j:(j['hash'],str(j.get('episode','')),j.get('added',0))
        pending={key(j):j for j in current.get('jobs',[])}
        for index,job in enumerate(state.get('jobs',[])):
            old=pending.pop(key(job),{})
            if enqueue and old:
                request=job.get('watch_requested',0)
                state['jobs'][index]=job=old
                job['watch_requested']=max(request,job.get('watch_requested',0))
            for field in ('watch_requested','watch_handled'):
                if old.get(field,0)>job.get(field,0):job[field]=old[field]
        state.setdefault('jobs',[]).extend(pending.values())
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=1), encoding='utf-8')
        os.replace(tmp, path)



def info_hash(torrent):
    """The torrent's info-hash from Elementum's list entry (its id is the hash)."""
    for key in ('id', 'hash', 'info_hash', 'infohash'):
        value = str(torrent.get(key) or '').strip().lower()
        if len(value) == 40 and all(c in '0123456789abcdef' for c in value):
            return value
    return ''


def queue(profile, torrent, kind, title='', season='', episode='', now=None, episodes=(), watch=False):
    """Add a Download to the queue (once per torrent and episode). Returns the job."""
    state = load(profile)
    h = info_hash(torrent)
    if not h:
        raise ValueError('torrent without an info-hash')
    for job in state['jobs']:
        if job['hash'] == h and job.get('episode', '') == str(episode or '') and job['status'] not in ('done', 'failed'):
            if watch:job['watch_requested']=time.time();save(profile,state,enqueue=True)
            return job
    job = {'hash': h, 'name': str(torrent.get('name') or title or h), 'title': title, 'kind': kind,
           'season': str(season or ''), 'episode': str(episode or ''), 'episodes': sorted(int(n) for n in episodes or ()),
           'status': 'new', 'files': [], 'watch_requested':(time.time() if watch else 0),
           'added': time.time() if now is None else now}
    state['jobs'].append(job)
    save(profile, state, enqueue=True)
    return job


def folders(kind, name, title=''):
    """Drive › Kodi Downloads › Movies, or › TV Shows › <show> (from the file's name, else the show's title)."""
    parts = driveupload.drive_folders(name, '/')
    if parts[1] == 'Movies' and kind in ('episode', 'season') and title:
        parts = [TOP, 'TV Shows', title]
    return parts


def kind_of(name):
    """movie, episode (SxxEyy) or season (a pack: S01, Season 1, Complete) from a torrent's name."""
    import re
    if re.search(r'(?i)\bS\d{1,2}[ ._-]?E\d{1,3}\b|\b\d{1,2}x\d{2,3}\b', name):
        return 'episode'
    if re.search(r'(?i)\bS\d{1,2}\b|\bseason[ ._-]*\d|\bcomplete\b', name):
        return 'season'
    return 'movie'


GRACE = 180   # seconds a torrent must sit unfinished with nothing playing before it is taken (buffering, choosing)


def adopt(profile, torrents, playing, now=None):
    """Owner (build 160): a version played from the source page kept downloading onto the phone (Elementum keeps
    downloading after playback). After GRACE seconds with nothing playing (so never while a video buffers or plays),
    every unfinished torrent is queued here instead; returns the Elementum ids to drop. A finished one stays: its file
    is on the phone already and goes to Drive the usual way."""
    import drivelibrary
    now = time.time() if now is None else now
    state = load(profile)
    seen = state.setdefault('idle_seen', {})
    if playing:
        if seen:
            state['idle_seen'] = {}
            save(profile, state)
        return []
    out = []
    current = set()
    for torrent in torrents or []:
        try:
            done = float(torrent.get('progress') or 0) >= 99.9
        except (TypeError, ValueError):
            done = False
        name = str(torrent.get('name') or '')
        h = info_hash(torrent)
        if done or not h or not name:
            continue
        current.add(h)
        first = seen.setdefault(h, now)
        if now - first < GRACE:
            continue
        info = drivelibrary.parse(name)
        kind = kind_of(name)
        queue(profile, torrent, kind, info.get('title') or drivelibrary.display_title(name), info.get('season') or '',
              info.get('episode') or '' if kind == 'episode' else '')
        out.append(str(torrent.get('id')))
    state = load(profile)   # queue() saved jobs; keep them and record what was seen
    state['idle_seen'] = {h: t for h, t in seen.items() if h in current and str(h) not in out}
    save(profile, state)
    return out


def default_open(url, offset, timeout=60):
    req = urllib.request.Request(url, headers={'Range': 'bytes=%d-' % offset} if offset else {})
    return urllib.request.urlopen(req, timeout=timeout)


def active(profile):
    return any(j['status'] not in ('done', 'failed') for j in load(profile).get('jobs', []))


def step(profile, api, drive, notify=lambda kind, title, text: None, open_url=default_open, keep_going=lambda: True,
         clock=time.time, on_done=lambda job: None):
    """Move the oldest unfinished job on by one step. Returns seconds until the next step is worth trying
    (None when nothing is queued)."""
    state = load(profile)
    jobs = [j for j in state['jobs'] if j['status'] not in ('done', 'failed')]
    if not jobs:
        if state.pop('current', None) is not None:
            save(profile, state)
        return None
    job = jobs[0]

    def commit():
        save(profile, state)

    title = job.get('title') or job['name']
    try:
        if job['status'] == 'new':
            job['magnet'], ready = api.add(job['hash'])
            job['status'] = 'copying' if ready else 'fetching'
            if not ready:
                notify('download', 'AllDebrid is fetching it', title)
            commit()
            return 1
        if job['status'] == 'fetching':
            code, fraction, words = api.status(job['magnet'])
            job['fetched'] = round(fraction * 100)
            if code >= alldebrid.FAILED:
                raise alldebrid.Problem('AllDebrid could not fetch this torrent (%s).' % (words or code))
            if code == alldebrid.READY:
                job['status'] = 'copying'
            state['current'] = {'name': title, 'folder': 'AllDebrid', 'sent': job['fetched'], 'total': 100, 'stage': 'fetching'}
            commit()
            return 1 if code == alldebrid.READY else 15
        if job['status'] == 'copying':
            if not job['files']:
                chosen = alldebrid.pick(api.files(job['magnet']), job['kind'], job.get('season'), job.get('episode'), job.get('episodes'))
                if not chosen:
                    raise alldebrid.Problem('This torrent has no video file.')
                job['files'] = [{'path': p, 'size': s, 'link': l, 'session': {}, 'done': False} for p, s, l in chosen]
                commit()
            for entry in job['files']:
                if entry['done']:
                    continue
                url, name, size = api.unlock(entry['link'])
                name = os.path.basename(name or entry['path'])
                size = size or entry['size']
                parts = folders(job['kind'], name, job.get('title') if job['kind'] != 'movie' else '')
                parent = drive.folder(parts)

                def progress(sent, total):
                    state['current'] = {'name': title, 'folder': parts[-1], 'sent': sent, 'total': total, 'stage': 'copying'}
                    commit()
                result = drive.upload_stream(lambda offset: open_url(url, offset), size, name, parent, entry['session'],
                                             commit, keep_going, progress)
                if int(result.get('size') or size) != size:
                    raise RuntimeError('Google Drive has a different size for %s' % name)
                entry.update(done=True, drive_id=result.get('id', ''), drive_name=name)
                entry['session'] = {}
                commit()
            job['status'] = 'done'
            job['finished'] = clock()
            state.pop('current', None)
            commit()
            notify('drive', 'Saved to Google Drive', '%s · straight from AllDebrid, nothing kept on the phone' % title)
            on_done(job)
            return 1
    except driveupload.Stop:
        return 30
    except alldebrid.Problem as problem:
        job['status'] = 'failed'
        job['error'] = str(problem)
        state.pop('current', None)
        commit()
        notify('problem', "Couldn't download to Google Drive", '%s: %s' % (title, problem))
        return 1
    except Exception as error:   # network, Drive: try again in a while, from where it got to
        job['tries'] = job.get('tries', 0) + 1
        job['error'] = '%s: %s' % (type(error).__name__, str(error)[:160])
        commit()
        if job['tries'] >= 20:
            job['status'] = 'failed'
            commit()
            notify('problem', "Couldn't download to Google Drive", '%s: %s' % (title, job['error']))
            return 1
        return min(600, 30 * job['tries'])
    return 5


def uploads(profile):
    """The copy in progress, for the Uploading card, the activity pill and Library status (as notices.uploads)."""
    current = load(profile).get('current')
    if not current or not current.get('total'):
        return []
    return [current]


def next_watch(profile,is_ready,playing=False,now=None):
    """Only the oldest outstanding watch request may play, and only after preparation.
    Mark before playback so a restart does not unexpectedly replay an already-opened movie.
    """
    if playing:return None
    state=load(profile)
    jobs=sorted((j for j in state.get('jobs',[]) if j.get('watch_requested',0)>j.get('watch_handled',0)),
                key=lambda j:j['watch_requested'])
    for job in jobs:
        if job['status']=='failed':
            job['watch_handled']=job['watch_requested'];save(profile,state);continue
        if job['status']!='done':return None
        files=[f for f in job.get('files',[]) if f.get('done') and f.get('drive_id')]
        if not files:return None
        first=files[0]
        if not is_ready(first['drive_id']):return None
        job['watch_handled']=job['watch_requested'];save(profile,state)
        return first['drive_id']
    return None
