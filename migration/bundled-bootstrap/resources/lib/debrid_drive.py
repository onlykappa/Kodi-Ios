"""Downloads that go straight to Google Drive through AllDebrid (owner, build 160: "a movie im downloading goes onto my
phone still … if i do a large movie it wont ever download"; chose "AllDebrid straight to Drive").

Download › a version, as before; download.py then takes the torrent back from Elementum (with what it had fetched) and
queues it here. The bootstrap service gives AllDebrid the torrent, waits while AllDebrid fetches it on its own servers,
then copies each video into Google Drive › Kodi Downloads › Movies (or › TV Shows › <show>), CHUNK at a time:
nothing is written to the phone, so any size works. A restart carries on where Drive got to. Preparation for Kodi
and AirPlay then reads it from Drive as it does every other download.

State: addon_data/service.kodi.ios.bootstrap/debrid-drive.json {'jobs': [...], 'current': {...}}.
"""
import json
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


def save(profile, state):
    path = location(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
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


def queue(profile, torrent, kind, title='', season='', episode='', now=None, episodes=()):
    """Add a Download to the queue (once per torrent and episode). Returns the job."""
    state = load(profile)
    h = info_hash(torrent)
    if not h:
        raise ValueError('torrent without an info-hash')
    for job in state['jobs']:
        if job['hash'] == h and job.get('episode', '') == str(episode or '') and job['status'] not in ('done', 'failed'):
            return job
    job = {'hash': h, 'name': str(torrent.get('name') or title or h), 'title': title, 'kind': kind,
           'season': str(season or ''), 'episode': str(episode or ''), 'episodes': sorted(int(n) for n in episodes or ()),
           'status': 'new', 'files': [],
           'added': time.time() if now is None else now}
    state['jobs'].append(job)
    save(profile, state)
    return job


def folders(kind, name, title=''):
    """Drive › Kodi Downloads › Movies, or › TV Shows › <show> (from the file's name, else the show's title)."""
    parts = driveupload.drive_folders(name, '/')
    if parts[1] == 'Movies' and kind in ('episode', 'season') and title:
        parts = [TOP, 'TV Shows', title]
    return parts


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
