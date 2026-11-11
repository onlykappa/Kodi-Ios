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
import threading
import time
import urllib.request
from pathlib import Path

import alldebrid
import driveupload
import transfer_history

FILE = 'debrid-drive.json'
LANES = 2   # episodes of one season uploaded at once (ISSUE-164)
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
        key=lambda j:(j['hash'],str(j.get('season','')),str(j.get('episode','')),j.get('added',0))
        pending={key(j):j for j in current.get('jobs',[])}
        for index,job in enumerate(state.get('jobs',[])):
            old=pending.pop(key(job),{})
            if enqueue and old:
                request=job.get('watch_requested',0)
                if job.get('show_tmdb') and not old.get('show_tmdb'):old['show_tmdb']=job['show_tmdb']
                state['jobs'][index]=job=old
                job['watch_requested']=max(request,job.get('watch_requested',0))
            for field in ('watch_requested','watch_handled'):
                if old.get(field,0)>job.get(field,0):job[field]=old[field]
            if old.get('show_tmdb') and not job.get('show_tmdb'):job['show_tmdb']=old['show_tmdb']
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


def queue(profile, torrent, kind, title='', season='', episode='', now=None, episodes=(), watch=False,show_tmdb=None):
    # Serialize the read/deduplicate/save transaction across the foreground picker and opening watcher.
    target=location(profile);target.parent.mkdir(parents=True,exist_ok=True)
    with open(str(target)+'.enqueue.lock','a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        return _queue(profile,torrent,kind,title,season,episode,now,episodes,watch,show_tmdb)


def _queue(profile, torrent, kind, title='', season='', episode='', now=None, episodes=(), watch=False,show_tmdb=None):
    """Add a Download to the queue (once per torrent and episode). Returns the job."""
    state = load(profile)
    h = info_hash(torrent)
    if not h:
        raise ValueError('torrent without an info-hash')
    for job in state['jobs']:
        if job['hash'] == h and job.get('season','')==str(season or '') and job.get('episode', '') == str(episode or '') and job['status'] not in ('done', 'failed'):
            changed=False
            if show_tmdb and not job.get('show_tmdb'):job['show_tmdb']=str(show_tmdb);changed=True
            if watch:job['watch_requested']=time.time();changed=True
            if changed:save(profile,state,enqueue=True)
            return job
    job = {'hash': h, 'name': str(torrent.get('name') or title or h), 'title': title, 'kind': kind,
           'season': str(season or ''), 'episode': str(episode or ''), 'episodes': sorted(int(n) for n in episodes or ()),
           'status': 'new', 'files': [], 'watch_requested':(time.time() if watch else 0),
           'added': time.time() if now is None else now}
    if show_tmdb:job['show_tmdb']=str(show_tmdb)
    state['jobs'].append(job)
    save(profile, state, enqueue=True)
    return job


def folders(kind, name, title=''):
    """Drive › Kodi Downloads › Movies, or › TV Shows › <show> (from the file's name, else the show's title)."""
    parts = driveupload.drive_folders(name, '/')
    if parts[1] == 'Movies' and kind in ('episode', 'season') and title:
        parts = [TOP, 'TV Shows', title]
    return parts


def remember_shows(profile, jobs, remember):
    """Roadmap 2.2: tell the Library which TMDb show each finished episode or season copy belongs to, under the job's
    title and every Drive folder name its files went to. remember(titles, tmdb_id) -> True when anything changed."""
    changed = False
    for job in jobs:
        if job.get('status') != 'done' or not job.get('show_tmdb') or job.get('kind') == 'movie':
            continue
        names = [job.get('title')] + [folders(job['kind'], f.get('drive_name') or os.path.basename(f.get('path') or ''),
                                              job.get('title'))[-1]
                                      for f in job.get('files') or [] if f.get('drive_name') or f.get('path')]
        changed = remember(names, job['show_tmdb']) or changed
    return changed


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


def copying(profile):
    """A file is being copied from AllDebrid into Drive right now (not just waiting for AllDebrid's servers)."""
    current = load(profile).get('current') or {}
    return current.get('stage') == 'copying'


def active(profile):
    return any(j['status'] not in ('done', 'failed') for j in load(profile).get('jobs', []))


def step(profile, api, drive, notify=lambda kind, title, text: None, open_url=default_open, keep_going=lambda: True,
         clock=time.time, on_done=lambda job: None, cancelled=lambda: set(), forget=lambda info_hash: None, log=lambda text: None):
    """Move the oldest unfinished job on by one step. Returns seconds until the next step is worth trying
    (None when nothing is queued). cancelled(): info hashes the owner cancelled (long press in Notifications);
    those jobs end as failed with 'Cancelled' and forget(hash) clears each request."""
    state = load(profile)
    drop = {str(h).lower() for h in cancelled()}
    for job in state['jobs']:
        if job['status'] not in ('done', 'failed') and str(job.get('hash', '')).lower() in drop:
            job.update(status='failed', error='Cancelled', finished=clock())
            state.pop('current', None)
            save(profile, state)
            transfer_history.failed(profile, 'up', job.get('title') or job['name'], 'cancelled by you', clock())
            forget(job['hash'])
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
                try:
                    chosen = alldebrid.pick(api.files(job['magnet']), job['kind'], job.get('season'), job.get('episode'), job.get('episodes'))
                except alldebrid.TooMany as many:
                    raise alldebrid.Problem(str(many))
                if not chosen:
                    raise alldebrid.Problem('This version has no video for season %s. Pick a season pack.' % job.get('season')
                                            if job.get('kind') == 'season' and job.get('season') else 'This torrent has no video file.')
                job['files'] = [{'path': p, 'size': s, 'link': l, 'session': {}, 'done': False} for p, s, l in chosen]
                commit()
            # ISSUE-164 (owner: "upload speed is so slow"; build-224 log ~0.3 MB/s on a 0.49 MB/s line): one Drive upload
            # is one connection and rarely fills a phone's upload. A season's episodes now go up two at a time; the
            # pages show one upload whose speed is both together. A movie (one file) is unchanged.
            guard = threading.RLock()
            todo = [e for e in job['files'] if not e['done']]
            plain_commit = commit

            def commit():   # both lanes change `state`; it is written whole, one lane at a time
                with guard:
                    plain_commit()

            def key_for(slot):
                with guard:
                    owner = (state.get('current') or {}).get('slot')
                    return 'current' if owner in (None, slot) else 'current_also'

            def show(slot, fields):
                with guard:
                    key = key_for(slot)
                    # rate_own: each lane's speed; rate: what the pages show, both lanes on the shown upload ('current').
                    fields = dict(fields, slot=slot)
                    fields['rate'] = fields.get('rate_own') or 0
                    state[key] = fields
                    shown, also = state.get('current'), state.get('current_also')
                    if shown:
                        shown.pop('parallel', None)
                        shown['rate'] = shown.get('rate_own') or 0
                        if also and clock() - (also.get('updated') or also.get('phase_at') or 0) < 60:
                            shown['rate'] += also.get('rate_own') or 0
                            shown['parallel'] = 2
                commit()

            def release(slot):
                with guard:
                    if (state.get('current') or {}).get('slot') == slot:
                        state.pop('current', None)
                        if state.get('current_also'):
                            state['current'] = state.pop('current_also')
                    elif (state.get('current_also') or {}).get('slot') == slot:
                        state.pop('current_also', None)

            def copy(entry, slot):
                url, name, size = api.unlock(entry['link'])
                name = os.path.basename(name or entry['path'])
                size = size or entry['size']
                parts = folders(job['kind'], name, job.get('title') if job['kind'] != 'movie' else '')
                with guard:   # two uploads must not both create the season's folder
                    parent = drive.folder(parts)

                marks = []

                def progress(sent, total):
                    # Owner (build 170): the speed and the time left, measured over the last ~20 s.
                    now = clock()
                    marks.append((now, sent))
                    # Build 207 (build-206 log: pieces 20-30 s apart): the window always keeps the piece before, or a
                    # slow copy read 0 MB/s on every page between pieces (no graph, Peak and Average 0.0).
                    recent = [m for m in marks if now - m[0] <= 20]
                    marks[:] = recent if len(recent) > 1 else marks[-2:]
                    span = marks[-1][0] - marks[0][0]
                    rate = (marks[-1][1] - marks[0][1]) / span if span >= 1 else 0.0
                    # Build 193 (build-192 log): progress carries its time, so a hung piece is never shown as moving,
                    # and a piece that went up resets the tries (six AllDebrid 500s made a later timeout wait 210 s).
                    # Owner (build 205: "i went to download a entire season and it seems only 1 thing is downloading"):
                    # which file of the job this is, so the pages name the episode and count the season.
                    show(slot, {'name': title, 'folder': parts[-1], 'sent': sent, 'total': total, 'stage': 'copying',
                                        'rate_own': rate, 'eta_s': (total - sent) / rate if rate else 0, 'updated': now,
                                        'file': name, 'index': job['files'].index(entry) + 1, 'count': len(job['files'])})
                    with guard:
                        if job.get('tries') and sent > (marks[0][1] if len(marks) > 1 else 0):
                            job['tries'] = 0
                            job.pop('error', None)
                    commit()
                hash_ = str(job['hash']).lower()
                going = lambda: keep_going() and hash_ not in {str(h).lower() for h in cancelled()}
                def activity(phase,sent,total):
                    # Called on the owner thread, never the read-ahead thread. Percent remains confirmed bytes.
                    now=clock()
                    with guard:
                        current=dict(state.get(key_for(slot)) or {})
                    current.update(name=title,folder=parts[-1],file=name,index=job['files'].index(entry)+1,
                                   count=len(job['files']),sent=sent,total=total,stage='copying',phase=phase,phase_at=now)
                    if phase=='paused_playback':current.update(rate_own=0,eta_s=0)
                    show(slot,current)
                # Each lane works on its own copy of the resumable session, copied back when it is saved.
                with guard:
                    session = dict(entry.get('session') or {})

                def keep():
                    with guard:
                        entry['session'] = dict(session)
                    commit()
                result = drive.upload_stream(lambda offset: open_url(url, offset), size, name, parent, session,
                                             keep, going, progress,activity=activity)
                if int(result.get('size') or size) != size:
                    raise RuntimeError('Google Drive has a different size for %s' % name)
                with guard:
                    entry.update(done=True, drive_id=result.get('id', ''), drive_name=name)
                    entry['session'] = {}
                commit()

            def worker(slot):
                try:
                    while True:
                        with guard:
                            entry = todo.pop(0) if todo else None
                        if entry is None:
                            return
                        copy(entry, slot)
                finally:
                    release(slot)

            lanes = LANES if len(todo) > 1 else 1
            if lanes == 1:
                worker(0)
            else:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=lanes) as pool:
                    running = [pool.submit(worker, slot) for slot in range(lanes)]
                    problems = [f.exception() for f in running]
                for problem in problems:
                    if problem is not None:
                        raise problem
            job['status'] = 'done'
            job['finished'] = clock()
            state.pop('current', None)
            state.pop('current_also', None)
            commit()
            files = job.get('files') or []
            if job['kind'] not in ('movie', 'episode') and len(files) == 1:
                # Owner (build 205): "i pressed full season" and the version picked held episode 1 alone. Say so.
                import work_state
                notify('problem', 'Only one episode was in that download',
                       '%s · %s is in Google Drive; the version you picked had no other episodes. Pick a FULL SEASON '
                       'version for the rest.' % (title, work_state.episode_label(files[0].get('drive_name') or files[0].get('path'))))
            else:
                notify('drive', 'Saved to Google Drive', '%s%s · straight from AllDebrid, nothing kept on the phone'
                       % (title, ' · %d episodes' % len(files) if len(files) > 1 else ''))
            on_done(job)
            return 1
    except driveupload.Stop:
        return 30
    except alldebrid.Problem as problem:
        log('%s: failed: %s' % (title, problem))
        job['status'] = 'failed'
        job['error'] = str(problem)
        state.pop('current', None)
        commit()
        notify('problem', "Couldn't download to Google Drive", '%s: %s' % (title, problem))
        transfer_history.failed(profile, 'up', title, str(problem), clock())
        return 1
    except Exception as error:   # network, Drive: try again in a while, from where it got to
        job['tries'] = job.get('tries', 0) + 1
        job['error'] = '%s: %s' % (type(error).__name__, str(error)[:160])
        log('%s: try %d, again in %d s: %s' % (title, job['tries'], min(600, 30 * job['tries']), job['error']))
        job['retry_at'] = clock() + min(600, 30 * job['tries'])   # build 193: pages say "trying again in N min"
        commit()
        if job['tries'] >= 20:
            job['status'] = 'failed'
            commit()
            notify('problem', "Couldn't download to Google Drive", '%s: %s' % (title, job['error']))
            transfer_history.failed(profile, 'up', title, 'gave up after 20 tries: ' + job['error'].split(': ', 1)[0], clock())
            return 1
        return min(600, 30 * job['tries'])
    return 5


def uploads(profile):
    """The copy in progress, for the Uploading card, the activity pill and Library status (as notices.uploads)."""
    current = load(profile).get('current')
    if not current or not current.get('total'):
        return []
    return [current]


def renamed(profile, old_id, new_id):
    """A prepared movie took the original's place under a new Drive id (build 181): a waiting "download and watch"
    plays the new file."""
    if not old_id or old_id == new_id:
        return False
    state = load(profile)
    changed = False
    for job in state.get('jobs', []):
        for f in job.get('files', []):
            if f.get('drive_id') == old_id:
                f['drive_id'] = new_id
                changed = True
    if changed:
        save(profile, state)
    return changed


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
