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
# Most files copied at once (ISSUE-164; Roadmap 1F.4). Owner log 4beafff6 (build 314, a 101 Mbps upload): three copies
# ran at ~2.4 MB/s each, 7.2 MB/s together, each held by its own connection; a fourth adds a quarter more.
# ISSUE-200 (owner log a0a4e492 + Speedtest, build 350: 79.7 Mbps up but 469 ms ping; copies 1.4 MB/s with two lanes):
# on a high-latency line one connection waits through round trips before data flows, so filling it takes more of them.
LANES = 6
# A file whose copy failed goes back in line this many times in the same turn before it waits for the next one.
RETRIES_IN_RUN = 2


OFFSET = [lambda job: None]   # set by step(): tmdb, season -> episodes before that season (TMDb, cached)


def offset_for(job):
    """Episodes before the job's season, for absolute-numbered packs (season 1: 0; unknown: None)."""
    try:
        season = int(job.get('season') or 0)
    except (TypeError, ValueError):
        return None
    if season <= 1:
        return 0
    if job.get('offset') is not None:
        return int(job['offset'])
    value = OFFSET[0](job)
    if value is not None:
        job['offset'] = int(value)
    return value


def offset_lookup(profile):
    """job -> episodes before its season, from TMDb's season sizes (TMDb Helper's key), cached in drive-library-art.json."""
    import drivelibrary
    try:
        import xbmcvfs
        key = drivelibrary.tmdb_key(xbmcvfs.translatePath('special://home/addons/plugin.video.themoviedb.helper'))
    except Exception:
        key = ''
    path = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', 'drive-library-art.json')

    def lookup(job):
        tmdb = str(job.get('show_tmdb') or '')
        if not tmdb:
            return None
        cache = drivelibrary.load_json(path, {})
        known = 'counts:%s' % tmdb in cache
        counts = drivelibrary.season_counts(tmdb, key, cache, lambda url: urllib.request.urlopen(url, timeout=15).read(), cached_only=not key)
        if counts and not known:
            drivelibrary.save_json(path, cache)
        return drivelibrary.absolute_offset(counts, job.get('season'))
    return lookup


PRIORITY_LANES = 2  # F4: copy lanes while a next-to-watch video is being prepared
READY_TRIES = 3     # F1: starts of the made-ready-while-copying path per file before a plain copy
BUSY_LANES = 4      # beside a conversion (was 2: on the owner's Wi-Fi the conversion used a fraction of the line)
START_LANES = 3
CELLULAR_LANES = 2  # mobile data: E16's crawl (four lanes at ~0.2 MB/s each timed out)
GAIN = 1.15   # one more lane is kept only when it copies at least 15 % more in total


LANE_MEMORY = 6 * 3600   # ISSUE-206: what a lane count copied this long ago says nothing about the line now


def lane_plan(state, now=None):
    """E16 (owner logs 7698974a / ec3b0956: four lanes on a ~0.4 MB/s link each crawled and timed out): how many lanes
    the next run uses. Starts at START_LANES; tries one more while the last addition paid off (GAIN); otherwise the
    count that copied fastest. state['lane_speeds']: {lanes: bytes per second, smoothed}.
    ISSUE-206 (build-356 log: 3 lanes at 13-17 MB/s on a 22 MB/s uplink, never trying 4): speeds older than
    LANE_MEMORY (or with no time, from before) are forgotten, so a line that got faster is tried with more lanes again."""
    now = time.time() if now is None else now
    seen = state.get('lane_seen') or {}
    speeds = {int(k): float(v) for k, v in (state.get('lane_speeds') or {}).items()
              if now - float(seen.get(str(k)) or 0) < LANE_MEMORY}
    now = int(state.get('lanes_now') or START_LANES)
    if not speeds or now not in speeds:
        return max(1, min(LANES, now))
    below = speeds.get(now - 1)
    if now < LANES and (now + 1) not in speeds and (below is None or speeds[now] >= GAIN * below):
        return now + 1
    best = max(speeds.values())
    return min(n for n, rate in speeds.items() if rate * GAIN >= best)   # the fewest lanes within 15 % of the best


def learn_lanes(state, lanes, sent, seconds, now=None):
    """Record what a run with this many lanes copied (runs under a minute or a few MB say nothing)."""
    if seconds < 60 or sent < 8 * 1024 * 1024:
        return
    state.setdefault('lane_seen', {})[str(lanes)] = time.time() if now is None else now
    speeds = state.setdefault('lane_speeds', {})
    rate = sent / float(seconds)
    old = speeds.get(str(lanes))
    speeds[str(lanes)] = rate if old is None else 0.5 * float(old) + 0.5 * rate
    state['lanes_now'] = lanes


def converting():
    """Whether a conversion (prepare_downloads) is running now; set by step() for this turn."""
    return bool(CONVERTING[0]())


CONVERTING = [lambda: False]


# ISSUE-198 (owner logs 94711fae / b3c5d6eb, build 350: 65 of 116 copies "failed"): a dropped connection, a Wi-Fi /
# cellular switch, the phone sleeping or Kodi closing counted toward the 20 tries like a real problem, so a long night of
# network trouble ended copies for good. Network trouble now never fails a copy: it waits (up to 5 min between tries)
# and carries on from what Drive confirmed. Only AllDebrid's own answers and Drive refusing the file end it.
NETWORK_TYPES = ('ConnectionError', 'ConnectionResetError', 'ConnectionAbortedError', 'ConnectionRefusedError',
                 'BrokenPipeError', 'TimeoutError', 'timeout', 'OSError', 'URLError', 'RemoteDisconnected',
                 'IncompleteRead', 'SSLError', 'SSLEOFError', 'socket.timeout', 'gaierror', 'Stop')
NETWORK_WORDS = ('timed out', 'timeout', 'connection', 'network', 'temporarily', 'reset by peer', 'unreachable',
                 'not connected', 'offline', 'did not finish', 'did not confirm', 'input/output', 'broken pipe',
                 'name resolution', 'nodename nor servname', 'http 500', 'http 502', 'http 503', 'http 504', 'http 429',
                 'internet connection', 'stopped before the end')


def network_error(error):
    """True when an exception (or a saved 'Type: text' error) is network trouble that goes away by itself."""
    if isinstance(error, BaseException):
        code = getattr(error, 'code', None)
        if isinstance(code, int):
            return code >= 500 or code in (408, 429)
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return True
        text = '%s: %s' % (type(error).__name__, error)
    else:
        text = str(error or '')
    if text.split(':', 1)[0].strip() in NETWORK_TYPES:
        return True
    low = text.lower()
    return any(w in low for w in NETWORK_WORDS)


def net_wait(tries):
    """Seconds before the next try after network trouble: 15, 30, 60, 120, then every 5 minutes."""
    return min(300, 15 * 2 ** max(0, min(int(tries) - 1, 5)))


def revive(state, clock=time.time):
    """Copies that ended 'failed' for network trouble (before ISSUE-198) go back in line, once, from where Drive got
    to (their sessions are kept). Returns the jobs revived."""
    back = []
    have = finished_keys(state)
    for job in state.get('jobs', []):
        if job.get('status') != 'failed' or job.get('error') == 'Cancelled' or job.get('revived'):
            continue
        if same_video(job) in have:   # another source already put this video on Drive
            continue
        if not network_error(job.get('error')):
            continue
        job.update(status='copying' if job.get('files') else 'new', tries=0, net_tries=0, retry_at=0, revived=clock())
        job.pop('finished', None)
        back.append(job)
    return back


def same_video(job):
    """What a copy is, whatever its source: (title, season, episode)."""
    return (str(job.get('title') or '').strip().lower(), str(job.get('season') or ''), str(job.get('episode') or ''))


def finished_keys(state):
    return {same_video(j) for j in state.get('jobs', []) if j.get('status') == 'done' and j.get('title')}


def problem_title(job):
    """Owner screenshot (build 356): rows read "45e2c1e0…" when a copy had no title; its file name says what it is."""
    # Owner screenshot (2026-11-13): cancelled seasons still read "45e2c1e044af006c8fbf…": the job's title and name
    # were the hash itself. A hash is never a title; the files, then the season's show, name it.
    title = job.get('title') or ''
    if is_hash(title):
        title = ''
    if not title:
        files = job.get('files') or []
        first = files[0] if files and isinstance(files[0], dict) else {}
        candidates = [job.get('name'), first.get('drive_name'), first.get('name'), first.get('path')]
        name = next((str(c) for c in candidates if c and not is_hash(str(c).rsplit('/', 1)[-1])), '')
        title = name.rsplit('/', 1)[-1]
        if title:
            try:
                import drivelibrary
                title = drivelibrary.display_title(title) or title
            except Exception:
                pass
    return title or 'Unnamed download'


def problem_key(job):
    """Which copy a problem row is, steady while the service saves the list (indexes can move)."""
    return '%s:%s:%s:%s' % (job.get('hash', ''), job.get('season', ''), job.get('episode', ''), job.get('added', 0))


def problems(state):
    """The copies that ended: [{'title', 'reason', 'kind' ('network', 'source', 'cancelled'), 'hash', 'index'}]."""
    out = []
    for n, job in enumerate(state.get('jobs', [])):
        if job.get('status') != 'failed':
            continue
        error = str(job.get('error') or 'unknown')
        kind = 'cancelled' if error == 'Cancelled' else 'network' if network_error(error) else 'source'
        title = problem_title(job)
        if job.get('kind') == 'episode' and job.get('season') and job.get('episode'):
            title = '%s · S%s E%s' % (title, job['season'], job['episode'])
        out.append({'title': title, 'reason': error.split(': ', 1)[-1][:120], 'kind': kind, 'hash': job.get('hash'), 'index': n,
                    'error': error.split(': ', 1)[-1] if error.split(': ', 1)[0].isidentifier() else error,
                    'job_kind': job.get('kind') or '', 'name': job.get('name') or '', 'finished': job.get('finished') or 0,
                    'season': job.get('season') or '', 'episode': job.get('episode') or '', 'count': len(job.get('files') or []),
                    'key': problem_key(job)})
    return out


def retry_failed(profile, kinds=('network', 'source'), only=None):
    """Settings › Library › Download problems › Retry: those copies go back in line (only: the problems' keys, from
    problems()). Returns how many."""
    state = load(profile)
    have = finished_keys(state)
    picked = {p['index'] for p in problems(state) if p['kind'] in kinds and same_video(state['jobs'][p['index']]) not in have
              and (only is None or p['key'] in only)}
    for n in picked:
        job = state['jobs'][n]
        job.update(status='copying' if job.get('files') else 'new', tries=0, net_tries=0, retry_at=0)
        job.pop('finished', None)
        job.pop('error', None)
    if picked:
        save(profile, state)
    return len(picked)


def clear_failed(profile, kinds=None, only=None):
    """Clear: copies that ended leave the list (the AllDebrid request stays at AllDebrid); kinds limits it to some
    problem kinds, only to some problems' keys. Returns how many."""
    state = load(profile)
    picked = {p['index'] for p in problems(state) if (kinds is None or p['kind'] in kinds) and (only is None or p['key'] in only)}
    jobs = state.get('jobs', [])
    keep = [j for n, j in enumerate(jobs) if n not in picked]
    cleared = [j for n, j in enumerate(jobs) if n in picked]
    if cleared:
        state['jobs'] = keep
        removed = state.setdefault('removed', [])   # save() must not merge them back from the file
        removed += [[j['hash'], str(j.get('season', '')), str(j.get('episode', '')), j.get('added', 0)] for j in cleared]
        save(profile, state)
    return len(cleared)


def lanes_for(files_left):
    """One lane per file still to copy, up to LANES: 3 when three or more remain, 2 for two, 1 for one."""
    return max(1, min(LANES, files_left))
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
        # Jobs this process removed on purpose (a duplicate, an episode already on Drive) stay removed: the merge below
        # brings back only jobs another process queued (end-to-end check: removed jobs came back at every save).
        gone={tuple(k) for k in state.get('removed') or []}
        pending={key(j):j for j in current.get('jobs',[]) if key(j) not in gone}
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
    try:
        import transfer_control
        leaving = transfer_control.cancelled_copies(profile)
    except Exception:
        leaving = set()
    for job in state['jobs']:
        if str(job.get('hash', '')).lower() in leaving:
            continue   # being cancelled (Pick Better Versions): never stands in for the new pick
        same_torrent = job['hash'] == h
        # Owner screenshots (build 325): episode 6 waited three times and episode 2 twice, each from another torrent.
        # An episode already waiting or copying is not queued again from a different version.
        same_episode = (kind == 'episode' and episode and job.get('kind') == 'episode' and show_tmdb and
                        str(job.get('show_tmdb') or '') == str(show_tmdb) and job.get('season', '') == str(season or '') and
                        job.get('episode', '') == str(episode or ''))
        if (same_episode or (same_torrent and job.get('season','')==str(season or '') and job.get('episode', '') == str(episode or ''))) and job['status'] not in ('done', 'failed'):
            changed=False
            if show_tmdb and not job.get('show_tmdb'):job['show_tmdb']=str(show_tmdb);changed=True
            # Owner (build 325): jobs queued by older builds kept their hash as the title; a new request names them.
            if title and not is_hash(title) and is_hash(job.get('title') or job.get('name')):
                job.setdefault('moved_from', job.get('title') or job['name'])
                job['title'] = title
                if is_hash(job.get('name')):
                    job['name'] = str(torrent.get('name') or title)
                changed=True
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


def order_season(profile, show_tmdb, season):
    """Build Season adds three episodes at once (owner, 2026-11-12: "fix the speed for shows"), so they can land out of
    order; the season's jobs not started yet go back into episode order, in the same places of the queue."""
    target=location(profile)
    with open(str(target)+'.enqueue.lock','a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        state=load(profile)
        jobs=state.get('jobs',[])
        mine=[i for i,j in enumerate(jobs) if j.get('status')=='new' and str(j.get('show_tmdb') or '')==str(show_tmdb)
              and str(j.get('season') or '')==str(season) and str(j.get('episode') or '').isdigit()]
        ordered=sorted((jobs[i] for i in mine), key=lambda j:int(j['episode']))
        if [jobs[i] for i in mine]==ordered:
            return False
        for i,job in zip(mine,ordered):
            jobs[i]=job
        save(profile,state)
        return True


def is_hash(text):
    """A torrent info-hash (40 hex or 32 base32), not a name."""
    import re
    text = str(text or '').strip()
    return bool(re.fullmatch(r'[0-9a-fA-F]{40}|[A-Z2-7]{32}', text))


EPISODE_MARK = None


def title_from_name(name):
    """The show's name from a release or file name: 'Naruto Shippuden Episode 006 Mission…' -> 'Naruto Shippuden',
    'Naruto.Shippuuden.-.002.[1080p].mkv' -> 'Naruto Shippuuden', 'Show.S01E04.mkv' -> 'Show'. '' for a hash."""
    import re
    import drivelibrary
    global EPISODE_MARK
    if EPISODE_MARK is None:
        EPISODE_MARK = re.compile(r'(?i)(\bS\d{1,2}\s*E\d{1,4}\b|\bepisode\s*\d{1,4}\b|\bep\.?\s*\d{1,4}\b|\bE\d{2,4}\b|\s[-–]\s*\d{1,4}\b|\b\d{1,2}x\d{2,3}\b|\bseason\s*\d)')
    base = str(name or '').rsplit('/', 1)[-1]
    if not base or is_hash(base) or is_hash(base.rsplit('.', 1)[0]):
        return ''
    text = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', re.sub(r'\.(mkv|mp4|avi|m4v|ts|webm)$', '', base, flags=re.I))
    text = re.sub(r'[._]+', ' ', text)
    mark = EPISODE_MARK.search(text)
    title = text[:mark.start()] if mark and mark.start() > 0 else drivelibrary.parse(base)['title']
    title = re.sub(r'\s{2,}', ' ', re.sub(r'[\s\-–(]+$', '', title)).strip()
    return '' if not title or is_hash(title) else title


def retitle(profile, state, plans=None, names=None, lookup=None):
    """Jobs named after their info-hash take their show's title. Where from, in order: the season plan (episode_watch,
    by TMDb id); another job of the same show; the show's name cached by the Library (names: {tmdb id: name}); TMDb
    itself (lookup(tmdb id) -> name, owner build 325); the release or file name. Returns [(job, old title)]."""
    if plans is None:
        try:
            import episode_watch
            plans = episode_watch.load(profile).get('shows', {})
        except Exception:
            plans = {}
    changed = []
    # Owner (build 319: an "ee34425d5595…" card in Downloaded TV Shows): with no saved season plan for the show, a job
    # takes the title another job of the same show (same TMDb id) already has.
    known = {}
    for other in state.get('jobs', []):
        if other.get('show_tmdb') and other.get('title') and not is_hash(other.get('title')):
            known.setdefault(str(other['show_tmdb']), other['title'])
    names = names or {}
    for job in state.get('jobs', []):
        old = job.get('title') or ''
        if not (is_hash(old) or is_hash(job.get('name')) or not old):
            continue
        tmdb = str(job.get('show_tmdb') or '')
        title = ((plans.get(tmdb) or {}).get('title') or known.get(tmdb) or names.get(tmdb) or '') if tmdb else ''
        if not title and tmdb and lookup:
            try:
                title = lookup(tmdb) or ''
            except Exception:
                title = ''
            if title:
                known[tmdb] = title
        if not title:
            for source in [job.get('name')] + [f.get('path') for f in job.get('files') or []]:
                title = title_from_name(source)
                if title:
                    break
        if not title or title == old:
            continue
        job['title'] = title
        if is_hash(job.get('name')):
            job['name'] = '%s S%02dE%02d' % (title, int(job.get('season') or 0), int(job.get('episode') or 0)) \
                if job.get('season') and job.get('episode') else title
        job.setdefault('moved_from', old)
        changed.append((job, old))
    return changed


def one_spelling(state):
    """Owner screenshot (build 327): "Naruto Shippuden" and "Naruto Shippuuden" were two shows, one without a poster:
    titles from different release names. Jobs of one show (show_match) take one title: the one a job with a TMDb id has,
    else the most common; files already copied move from the other spelling's folder (rehome). Returns [(job, old)]."""
    import collections
    groups = collections.defaultdict(list)
    for job in state.get('jobs', []):
        title = job.get('title') or ''
        if job.get('kind') in ('episode', 'season') and title and not is_hash(title):
            groups[show_match(title)].append(job)
    changed = []
    for jobs in groups.values():
        titles = collections.Counter(j['title'] for j in jobs)
        if len(titles) < 2:
            continue
        tmdb = collections.Counter(j['title'] for j in jobs if j.get('show_tmdb'))
        best = (tmdb or titles).most_common(1)[0][0]
        for job in jobs:
            if job['title'] != best:
                old = job['title']
                job.setdefault('moved_from', old)
                job['title'] = best
                changed.append((job, old))
    return changed


def repick_plan(state, title, tmdb=''):
    """Owner (build 328): episodes already queued with oversized versions get a better pick. The show's waiting
    episode jobs that have copied nothing: (info hashes to cancel, [(season, episode)]). A torrent that also holds an
    episode already copying, or done, is left alone."""
    key = show_match(title)
    mine = lambda j: (tmdb and str(j.get('show_tmdb') or '') == str(tmdb)) or (key and show_match(j.get('title') or '') == key)
    busy = {str(j.get('hash', '')).lower() for j in state.get('jobs', []) if _started(j) or j.get('status') == 'done'}
    hashes, episodes = set(), set()
    for job in state.get('jobs', []):
        if job.get('status') in ('done', 'failed') or job.get('kind') != 'episode' or not mine(job):
            continue
        h = str(job.get('hash', '')).lower()
        if h in busy or _started(job):
            continue
        try:
            episodes.add((int(job.get('season') or 0), int(job.get('episode') or 0)))
        except (TypeError, ValueError):
            continue
        hashes.add(h)
    return sorted(hashes), sorted(e for e in episodes if e[1])


def show_names(profile):
    """{tmdb id: name} the Library has cached (drive-library-art.json 'show:ID'); no network."""
    try:
        import work_state
        return work_state.show_names(profile)
    except Exception:
        return {}


LOOKED_UP = {}


def show_lookup(profile):
    """tmdb id -> the show's name from TMDb (TMDb Helper's key), cached in drive-library-art.json so the Library and
    the pages find the name and poster too. None when there is no key."""
    import drivelibrary
    try:
        import xbmcvfs
        key = drivelibrary.tmdb_key(xbmcvfs.translatePath('special://home/addons/plugin.video.themoviedb.helper'))
    except Exception:
        return None
    if not key:
        return None
    path = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', 'drive-library-art.json')

    def lookup(tmdb_id):
        if time.time() - LOOKED_UP.get(str(tmdb_id), 0) < 600:   # a failed lookup waits ten minutes
            return ''
        LOOKED_UP[str(tmdb_id)] = time.time()
        cache = drivelibrary.load_json(path, {})
        found = drivelibrary.show_details(tmdb_id, key, cache, lambda url: urllib.request.urlopen(url, timeout=15).read())
        if found:
            drivelibrary.save_json(path, cache)
        return found.get('name', '')
    return lookup


def _started(job):
    return any(f.get('done') or (f.get('session') or {}).get('url') for f in job.get('files') or [])


def drop_duplicates(state):
    """Owner (build 325): the same episode waited several times, each from another torrent. Among the jobs not done,
    one per show, season and episode stays (the one already copying, else the oldest); the others leave the queue if
    they have not copied anything yet. Returns the jobs removed."""
    import drivelibrary
    keep, dropped = {}, []
    for job in state.get('jobs', []):
        if job.get('status') in ('done', 'failed') or job.get('kind') != 'episode' or not job.get('episode') or not job.get('season'):
            continue
        show = str(job.get('show_tmdb') or '') or drivelibrary.show_key(job.get('title') or '')
        if not show or is_hash(job.get('title') or ''):
            continue
        key = (show, str(int(job['season'])), str(int(job['episode'])))
        first = keep.get(key)
        if first is None:
            keep[key] = job
            continue
        loser = job if _started(first) or not _started(job) else first
        if _started(loser):
            continue
        if loser is first:
            keep[key] = job
        dropped.append(loser)
    forget_jobs(state, dropped)
    return dropped


def show_match(title):
    """One key for the spellings of a show: 'Naruto Shippūden', 'Naruto Shippuden' and 'Naruto Shippuuden' match."""
    import re
    import unicodedata
    text = unicodedata.normalize('NFKD', str(title or '')).encode('ascii', 'ignore').decode().lower()
    text = re.sub(r'[^a-z0-9]+', '', re.sub(r'\b(19|20)\d\d\b', '', text))
    return re.sub(r'(.)\1+', r'\1', text)


def forget_jobs(state, jobs):
    """Remove jobs from the queue for good: save() never merges them back from disk."""
    if not jobs:
        return
    state['jobs'] = [j for j in state['jobs'] if all(j is not d for d in jobs)]
    removed = state.setdefault('removed', [])
    removed += [[j['hash'], str(j.get('season', '')), str(j.get('episode', '')), j.get('added', 0)] for j in jobs]
    del removed[:-500]


def drive_episodes(profile):
    """{(show key, season, episode)} of every episode file the Library has listed on Drive (drive-library.json, no
    network). Names with only a number ('Naruto Shippuuden - 002') count as season 1."""
    import drivelibrary
    import prepare_downloads
    cache = drivelibrary.load_json(str(location(profile).parent / 'drive-library.json'), {})
    found = set()
    for slot, hit in cache.items():
        if not slot.startswith('tv:') or slot == 'tv:':
            continue
        for e in (hit or {}).get('entries') or []:
            show, season, episode = prepare_downloads.line_key(e.get('name') or '')[:3]
            if e.get('season') and e.get('episode'):
                season, episode = int(e['season']), int(e['episode'])
            name = e.get('show') or title_from_name(e.get('name') or '') or show
            if episode:
                found.add((show_match(name), int(season or 1), int(episode)))
    return found


def drop_on_drive(state, on_drive):
    """Owner (build 325): "Naruto Shippuuden - 002" was on Drive and converting while S1 E2 waited to be copied again.
    A waiting episode job that has not copied anything leaves the queue when that episode is already on Drive."""
    dropped = []
    if not on_drive:
        return dropped
    for job in state.get('jobs', []):
        if job.get('status') in ('done', 'failed') or job.get('kind') != 'episode' or _started(job):
            continue
        try:
            key = (show_match(job.get('title') or title_from_name(job.get('name'))), int(job.get('season') or 0), int(job.get('episode') or 0))
        except (TypeError, ValueError):
            continue
        if key[0] and key[2] and key in on_drive:
            dropped.append(job)
    forget_jobs(state, dropped)
    return dropped


def priority_running(profile, now):
    """F4: the video being prepared now is one the owner will watch next (prepare_cloud marks its card): the copies
    leave it most of the line (PRIORITY_LANES)."""
    try:
        import prepare_downloads
        current = prepare_downloads.load(profile).get('current') or {}
    except Exception:
        return False
    return bool(current.get('running') and current.get('watch_next')) and now - float(current.get('updated') or 0) < 300


def conversion_running(profile, now):
    try:
        import prepare_downloads
        current = prepare_downloads.load(profile).get('current') or {}
    except Exception:
        return False
    return bool(current.get('running')) and now - float(current.get('updated') or 0) < 300


def episode_name(job, name):
    """The Drive name of an episode's file: the original when it says its season and episode, else '<show> S01E02 -
    <original>' (owner screenshot, build 314: "Naruto Shippuuden - 002 [1080p].mkv" gave the Library no episode)."""
    import drivelibrary
    info = drivelibrary.parse(name)
    if info.get('season') and info.get('episode'):
        return name
    if job.get('kind') != 'episode' or not job.get('season') or not job.get('episode') or not job.get('title') or is_hash(job['title']):
        return name
    return '%s S%02dE%02d - %s' % (job['title'], int(job['season']), int(job['episode']), name)


def rehome(drive, job, log=lambda text: None):
    """Files a job already copied into a folder named after the hash move into the show's folder; the empty hash folder
    goes to Drive's Trash. Returns how many files moved."""
    old = job.get('moved_from')
    if not old:
        return 0
    moved = 0
    import json as _json
    import urllib.parse as _p
    wrong = drive.folder([TOP, 'TV Shows', old])
    for f in job.get('files') or []:
        if not f.get('drive_id') or f.get('rehomed'):
            continue
        right = drive.folder(folders(job['kind'], f.get('drive_name') or f.get('path') or '', job.get('title') or ''))
        if right == wrong:
            continue
        named = episode_name(job, f.get('drive_name') or os.path.basename(f.get('path') or ''))
        status, _, _ = drive.call('PATCH', driveupload.API + '/' + _p.quote(str(f['drive_id']), safe='') + '?addParents=' +
                                  _p.quote(right, safe='') + '&removeParents=' + _p.quote(wrong, safe=''),
                                  _json.dumps({'name': named}).encode(), {'Content-Type': 'application/json'})
        if status == 200:
            f['rehomed'] = True
            f['drive_name'] = named
            moved += 1
        else:
            log('%s: could not move it into %s (HTTP %s)' % (f.get('drive_name') or f.get('path'), job.get('title'), status))
    if all(f.get('rehomed') or not f.get('drive_id') for f in job.get('files') or []):
        try:
            status, _, body = drive.call('GET', driveupload.API + '?q=' + _p.quote("'%s' in parents and trashed=false" % wrong) +
                                         '&fields=files(id)&pageSize=1')
            if status == 200 and not _json.loads(body or b'{}').get('files'):
                drive.call('PATCH', driveupload.API + '/' + _p.quote(wrong, safe=''), _json.dumps({'trashed': True}).encode(),
                           {'Content-Type': 'application/json'})
        except Exception:
            pass
        job.pop('moved_from', None)
    return moved


def folders(kind, name, title=''):
    """Drive › Kodi Downloads › Movies, or › TV Shows › <show> (from the file's name, else the show's title)."""
    parts = driveupload.drive_folders(name, '/')
    # End-to-end check (scripts/test_download_e2e.py): the show's folder came from each release's file name, so
    # "Naruto.Shippuden.S01E06…" and "Naruto Shippuuden - 002" made two shows (owner screenshot, build 327). An episode
    # with its show's title goes into that show's folder whatever the release calls it.
    if kind in ('episode', 'season') and title and not is_hash(title):
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


def companions(state, later, api, clock, log=lambda text: None):
    """Up to LANES-1 later jobs that hold one file each and can copy now (AllDebrid has them): their files are picked
    here. A job that AllDebrid still has to fetch, has several files, or waits for a retry is left for its own turn."""
    out = []
    for other in later:
        if len(out) >= LANES - 1:
            break
        if other['status'] not in ('new', 'copying') or other.get('retry_at', 0) > clock():
            continue
        try:
            if other['status'] == 'new':
                other['magnet'], ready = api.add(other['hash'])
                other['status'] = 'copying' if ready else 'fetching'
                if not ready:
                    continue
            if not other.get('files'):
                chosen = alldebrid.pick(api.files(other['magnet']), other['kind'], other.get('season'), other.get('episode'),
                                        other.get('episodes'), offset=offset_for(other))
                if not chosen:
                    continue
                other['files'] = [{'path': p, 'size': s, 'link': l, 'session': {}, 'done': False} for p, s, l in chosen]
        except Exception as error:   # its own turn deals with it (and says so)
            log('%s: left for its own turn (%s)' % (other.get('title') or other['name'], type(error).__name__))
            continue
        if len(other['files']) == 1 and not other['files'][0]['done']:
            out.append(other)
    return out


def link_now():
    try:
        import cache_tune
        return cache_tune.link_kind()
    except Exception:
        return None


def kick_on_new_link(state, link, clock=time.time):
    """ISSUE-198: Wi-Fi to cellular (or back, or a new Wi-Fi): copies waiting out network trouble try again at once
    instead of finishing their wait. Returns the previous link when it changed, else None."""
    before = state.get('link')
    if link:
        state['link'] = link
    if not link or not before or before == link:
        return None
    # ISSUE-200: what a lane count copied on mobile data says nothing about the new Wi-Fi (and back): learn again.
    state.pop('lane_speeds', None)
    state.pop('lane_seen', None)
    state.pop('lanes_now', None)
    for job in state.get('jobs', []):
        if job.get('net_tries') and job.get('status') not in ('done', 'failed') and float(job.get('retry_at') or 0) > clock():
            job['retry_at'] = 0
    return before


def step(profile, api, drive, notify=lambda kind, title, text: None, open_url=default_open, keep_going=lambda: True,
         clock=time.time, on_done=lambda job: None, cancelled=lambda: set(), forget=lambda info_hash: None, log=lambda text: None, ready_copy=None,
         link=link_now):
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
    # ISSUE-208: a request with no unfinished copy left is forgotten (the service wakes on any request it holds).
    for gone in drop - {str(j.get('hash', '')).lower() for j in state['jobs'] if j['status'] not in ('done', 'failed')}:
        forget(gone)
    # Owner screenshot (build 314): Build Season jobs named after their hash; give them the show's title and move what
    # was already copied into the show's folder.
    changed = kick_on_new_link(state, link(), clock)
    if changed:
        log('connection changed (%s to %s): waiting copies carry on now' % (changed, state.get('link')))
        save(profile, state)
    for job_ in revive(state, clock):
        log('%s: back in line (it had stopped for network trouble: %s)' % (job_.get('title') or job_['name'], str(job_.get('error'))[:80]))
        save(profile, state)
    renamed = retitle(profile, state, names=show_names(profile), lookup=show_lookup(profile)) + one_spelling(state)
    dropped = drop_duplicates(state) + drop_on_drive(state, drive_episodes(profile))
    CONVERTING[0] = lambda: conversion_running(profile, clock())
    OFFSET[0] = offset_lookup(profile)
    for job_ in dropped:
        log('%s S%sE%s: already on Drive or downloading from another version; this one is removed' % (
            job_.get('title') or job_['name'], job_.get('season'), job_.get('episode')))
    if dropped:
        save(profile, state)
    if renamed:
        for job_, old in renamed:
            log('%s: named after its show (was %s)' % (job_['title'], old[:12]))
        save(profile, state)
    # Owner screenshot (build 327): an empty "3c90db2e05…" folder stayed in the Library while its show's episodes were
    # still copying (into the show's folder); a renamed job moves what it has and trashes the old folder once empty.
    for job_ in [j for j in state['jobs'] if j.get('moved_from') and j['status'] != 'failed']:
        try:
            if rehome(drive, job_, log):
                driveupload.invalidate_library(str(location(profile).parent))   # the Library lists the show again
        except Exception as error:
            log('%s: moving into its show folder failed (%s)' % (job_.get('title'), type(error).__name__))
        else:
            save(profile, state)
    jobs = in_line([j for j in state['jobs'] if j['status'] not in ('done', 'failed')])
    if not jobs:
        state.pop('lanes', None)
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
                    chosen = alldebrid.pick(api.files(job['magnet']), job['kind'], job.get('season'), job.get('episode'), job.get('episodes'),
                                            offset=offset_for(job))
                except alldebrid.TooMany as many:
                    raise alldebrid.Problem(str(many))
                if not chosen and int(job.get('season') or 0) > 1 and offset_for(job) is None:
                    # An absolute-numbered pack needs TMDb's season sizes; without them, try again later (not a failure).
                    raise RuntimeError('Waiting for TMDb to say where season %s starts' % job.get('season'))
                if not chosen:
                    raise alldebrid.Problem('This version has no video for season %s. Pick a season pack.' % job.get('season')
                                            if job.get('kind') == 'season' and job.get('season') else 'This torrent has no video file.')
                job['files'] = [{'path': p, 'size': s, 'link': l, 'session': {}, 'done': False} for p, s, l in chosen]
                commit()
            # ISSUE-164 (owner: "upload speed is so slow"; build-224 log ~0.3 MB/s on a 0.49 MB/s line): one Drive upload
            # is one connection and rarely fills a phone's upload. A season's episodes now go up two at a time; the
            # pages show one upload whose speed is both together. A movie (one file) is unchanged.
            guard = threading.RLock()
            # Owner log 31996cd8 (build 309, a 182/101 Mbps line): Build Season makes one job per episode, so the three
            # lanes above never applied and the 31 episodes went up one at a time (~2.8 MB/s). A one-file job now takes
            # up to LANES-1 more ready one-file jobs (an episode each) and they copy side by side.
            group = [job] + (companions(state, jobs[1:], api, clock, log) if len(job['files']) == 1 else [])
            if len(group) > 1:
                commit()
            todo = [(j, e) for j in group for e in j['files'] if not e['done']]
            plain_commit = commit

            def commit():   # both lanes change `state`; it is written whole, one lane at a time
                with guard:
                    plain_commit()

            extra = {}   # lanes beyond the two the pages know ('current', 'current_also'): their numbers only add to the speed

            def key_for(slot):
                with guard:
                    first = (state.get('current') or {}).get('slot')
                    second = (state.get('current_also') or {}).get('slot')
                    if first in (None, slot):
                        return 'current'
                    return 'current_also' if second in (None, slot) else None

            def show(slot, fields):
                with guard:
                    # Owner screenshot (build 329): four copies ran, Library status showed one ("1 working"). Every lane is
                    # kept here for the pages (uploads()); 'current' / 'current_also' stay for the older readers.
                    state.setdefault('lanes', {})[str(slot)] = dict(fields, slot=slot)
                    key = key_for(slot)
                    # rate_own: each lane's speed; rate: what the pages show, both lanes on the shown upload ('current').
                    fields = dict(fields, slot=slot)
                    fields['rate'] = fields.get('rate_own') or 0
                    if key:
                        state[key] = fields
                    else:
                        extra[slot] = fields
                    shown, also = state.get('current'), state.get('current_also')
                    if shown:
                        shown.pop('parallel', None)
                        shown['rate'] = shown.get('rate_own') or 0
                        live = [f for f in [also] + list(extra.values())
                                if f and clock() - (f.get('updated') or f.get('phase_at') or 0) < 60]
                        if live:
                            shown['rate'] += sum(f.get('rate_own') or 0 for f in live)
                            shown['parallel'] = 1 + len(live)
                commit()

            def release(slot):
                with guard:
                    extra.pop(slot, None)
                    (state.get('lanes') or {}).pop(str(slot), None)
                    if (state.get('current') or {}).get('slot') == slot:
                        state.pop('current', None)
                        if state.get('current_also'):
                            state['current'] = state.pop('current_also')
                    elif (state.get('current_also') or {}).get('slot') == slot:
                        state.pop('current_also', None)
                    if extra and not state.get('current_also') and state.get('current'):
                        state['current_also'] = extra.pop(next(iter(extra)))   # a third lane moves up into the free place
                    elif extra and not state.get('current'):
                        state['current'] = extra.pop(next(iter(extra)))

            def copy(item, slot):
                owner, entry = item
                job_title = owner.get('title') or owner['name']
                url, name, size = api.unlock(entry['link'])
                original_name=name
                source_link=[url];source_guard=threading.Lock();renew_after=[0.0]
                def with_source(action):
                    attempted=source_link[0]
                    try:return action(attempted)
                    except urllib.error.HTTPError as error:
                        error.close()
                        if error.code not in (401,403,404,410):raise
                        with source_guard:
                            if source_link[0]==attempted:
                                if clock()<renew_after[0]:raise
                                renew_after[0]=clock()+60
                                fresh,fresh_name,fresh_size=api.unlock(entry['link'])
                                if fresh_name!=original_name or fresh_size!=size:
                                    raise RuntimeError('The refreshed download is a different file')
                                source_link[0]=fresh
                        return action(source_link[0])
                def open_source(offset):return with_source(lambda source:open_url(source,offset))
                if callable(getattr(drive,'copy_piece',None)):
                    def copy_to(target,headers,offset,count,total,timeout=20):
                        return with_source(lambda source:drive.copy_piece(source,{},target,headers,offset,count,total,timeout))
                    copy_to.max=getattr(drive.copy_piece,'max',8*1024*1024)
                    copy_to.streams=getattr(drive.copy_piece,'streams',False)
                    open_source.copy_to=copy_to
                name = episode_name(owner, os.path.basename(name or entry['path']))
                size = size or entry['size']
                parts = folders(owner['kind'], name, owner.get('title') if owner['kind'] != 'movie' else '')
                with guard:   # two uploads must not both create the season's folder
                    parent = drive.folder(parts)

                marks = []
                lane_job = '%s:%s:%s' % (owner.get('hash', ''), owner.get('season', ''), owner.get('episode', ''))

                def progress(sent, total):
                    # Owner (build 170): the speed and the time left, measured over the last ~20 s.
                    now = clock()
                    with guard:   # E16: this run's confirmed bytes, for the lane count of the next run
                        moved.setdefault(id(entry), [sent, sent])[1] = sent
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
                    show(slot, {'name': job_title, 'folder': parts[-1], 'sent': sent, 'total': total, 'stage': 'copying', 'job': lane_job,
                                        'rate_own': rate, 'eta_s': (total - sent) / rate if rate else 0, 'updated': now,
                                        'file': name, 'index': owner['files'].index(entry) + 1, 'count': len(owner['files'])})
                    with guard:
                        if owner.get('tries') and sent > (marks[0][1] if len(marks) > 1 else 0):
                            owner['tries'] = 0
                            owner.pop('error', None)
                    commit()
                hash_ = str(owner['hash']).lower()
                going = lambda: keep_going() and hash_ not in {str(h).lower() for h in cancelled()}
                def activity(phase,sent,total):
                    # Called on the owner thread, never the read-ahead thread. Percent remains confirmed bytes.
                    now=clock()
                    with guard:
                        current=dict((state.get(key_for(slot)) if key_for(slot) else extra.get(slot)) or {})
                    current.update(name=job_title,folder=parts[-1],file=name,index=owner['files'].index(entry)+1,job=lane_job,
                                   count=len(owner['files']),sent=sent,total=total,stage='copying',phase=phase,phase_at=now)
                    if phase=='paused_playback':current.update(rate_own=0,eta_s=0)
                    show(slot,current)
                # Each lane works on its own copy of the resumable session, copied back when it is saved.
                with guard:
                    session = dict(entry.get('session') or {})

                def keep():
                    with guard:
                        entry['session'] = dict(session)
                    commit()
                # F1 (PR #24): a file that would only need a re-package is made ready on its way (debrid_ready): no second
                # trip through the phone. Not for a copy already under way, and at most READY_TRIES starts per file.
                result = None
                if ready_copy is not None and not entry.get('plain') and not session.get('url'):
                    with guard:
                        entry['ready_tries'] = entry.get('ready_tries', 0) + 1
                        attempt_ready = entry['ready_tries'] <= READY_TRIES
                    if attempt_ready:
                        result = ready_copy(with_source, name, size, parent, going, progress,
                                            '%s:%s' % (hash_, entry.get('path') or name))
                    if result is None:
                        with guard:
                            entry['plain'] = True
                    else:
                        name = result.get('name') or name
                if result is None:
                    result = drive.upload_stream(open_source, size, name, parent, session,
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
                        try:
                            copy(entry, slot)
                            continue
                        except driveupload.Stop:
                            raise
                        except Exception as error:
                            # Owner log 3b94b426 (build 319): a lane whose episode failed once ended there, and one lane
                            # copied the season alone for hours. The episode goes back in line (its Drive session kept)
                            # up to RETRIES_IN_RUN times before it is left for the next turn.
                            with guard:
                                retried[id(entry[1])] = retried.get(id(entry[1]), 0) + 1
                                again = retried[id(entry[1])] <= RETRIES_IN_RUN
                                if again:
                                    todo.append(entry)
                            if again:
                                log('%s: %s; trying it again after the others (%d of %d)' % (
                                    entry[0].get('title') or entry[0]['name'], type(error).__name__, retried[id(entry[1])], RETRIES_IN_RUN))
                                continue
                            if entry[0] is job:
                                raise
                            # A companion's problem stays its own; it carries on in its own turn.
                            with guard:
                                other = entry[0]
                                other['error'] = '%s: %s' % (type(error).__name__, str(error)[:160])
                                if network_error(error):   # ISSUE-198: waits, never counts toward giving up
                                    other['net_tries'] = other.get('net_tries', 0) + 1
                                    other['retry_at'] = clock() + net_wait(other['net_tries'])
                                else:
                                    other['tries'] = other.get('tries', 0) + 1
                                    other['retry_at'] = clock() + min(600, 30 * other['tries'])
                            log('%s: try %d (beside %s): %s' % (other.get('title') or other['name'], other.get('tries', 0), title, other['error']))
                            commit()
                finally:
                    release(slot)

            retried = {}
            # Owner screenshot (build 325): "Waiting for Google Drive · no answer for 23 min" at 0 % while other copies
            # moved: the card was a lane of an earlier run (saved in the state), and the new lanes never wrote over it.
            with guard:
                state.pop('current', None)
                state.pop('current_also', None)
                state.pop('lanes', None)
            # Owner log 7698974a (build 325): four copies at ~0.2 MB/s each while a conversion read and wrote Drive on
            # the same connection; every piece timed out at 20 s and halved. Two lanes while a conversion runs.
            # E16: as many lanes as the link rewards (lane_plan), never more than files, and two beside a conversion.
            busy = converting()
            cap = CELLULAR_LANES if state.get('link') == 'cellular' else (BUSY_LANES if busy else LANES)
            if busy and priority_running(profile, clock()):
                cap = min(cap, PRIORITY_LANES)   # F4: a next-to-watch video is being prepared; it gets the line first
            lanes = min(lanes_for(len(todo)), lane_plan(state, clock()), cap)
            moved = {}
            began = clock()
            try:
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
            finally:
                # E19: a run beside a conversion shares the link with it (and is capped), so it says nothing about lanes.
                if not busy and not converting():
                    with guard:
                        learn_lanes(state, lanes, sum(b - a for a, b in moved.values()), clock() - began, clock())
            for other in group[1:]:
                if all(e['done'] for e in other['files']):
                    other['status'] = 'done'
                    other['finished'] = clock()
                    notify('drive', 'Saved to Google Drive', '%s · straight from AllDebrid, nothing kept on the phone'
                           % (other.get('title') or other['name']))
            job['status'] = 'done'
            job['finished'] = clock()
            state.pop('current', None)
            state.pop('current_also', None)
            commit()
            for other in group[1:]:
                if other['status'] == 'done':
                    on_done(other)
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
        if network_error(error):
            # ISSUE-198: a dropped connection, a Wi-Fi / cellular switch, the phone asleep: wait and carry on from what
            # Drive confirmed; never counts toward giving up.
            job['net_tries'] = job.get('net_tries', 0) + 1
            job['error'] = '%s: %s' % (type(error).__name__, str(error)[:160])
            wait = net_wait(job['net_tries'])
            job['retry_at'] = clock() + wait
            log('%s: network trouble (%s); carrying on in %d s' % (title, job['error'][:100], wait))
            commit()
            return wait
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


def hold(profile, reason):
    """Why copies wait outside the queue's own rules ('wifi': Copy only on Wi-Fi while on cellular), or '' to go on.
    Kept in the state for the pages (work_state shows "Waiting for Wi-Fi")."""
    state = load(profile)
    if (state.get('hold') or '') == (reason or ''):
        return
    if reason:
        state['hold'] = reason
    else:
        state.pop('hold', None)
    save(profile, state)


def uploads(profile, now=None):
    """The copies in progress, one per lane, for the Uploading card, the activity pill and Library status (as
    notices.uploads); a lane quiet for ten minutes is left out."""
    state = load(profile)
    now = time.time() if now is None else now
    lanes = [c for _, c in sorted((state.get('lanes') or {}).items(), key=lambda kv: int(kv[0]))
             if c.get('total') and now - max(float(c.get('updated') or 0), float(c.get('phase_at') or 0)) < 600]
    if lanes:
        return lanes
    current = state.get('current')
    if not current or not current.get('total'):
        return []
    return [current]


def in_line(jobs):
    """Owner screenshot (build 329): Up next read E3, E1, E4. Shows keep the order they were asked for; within a show
    the episodes go in season and episode order."""
    first = {}
    for n, job in enumerate(jobs):
        first.setdefault(show_match(job.get('title') or job.get('name') or ''), n)
    def key(job):
        try:
            number = (int(job.get('season') or 0), int(job.get('episode') or 0))
        except (TypeError, ValueError):
            number = (0, 0)
        return (first[show_match(job.get('title') or job.get('name') or '')], number)
    return sorted(jobs, key=key)


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
