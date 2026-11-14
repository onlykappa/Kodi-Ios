"""The Library index (DEC-052, PR #27): one coherent record of every movie and episode, and the only place that decides
what the Library screens show. Owner (2026-11-14): "it just needs to be one coherent brain instead of different pages doing
different things"; "if I delete or stop something in one place it stops it everywhere".

build() turns the raw state into one entry per video:
  {'key', 'kind' ('episode'|'movie'), 'show', 'show_key', 'tmdb', 'season', 'episode', 'title', 'year', 'id' (Drive id or
   None while not on Drive), 'name', 'size', 'quality', 'state', 'reason', 'progress', 'hidden', 'problem_key', 'ai'}
with one state from STATES:
  copying        AllDebrid -> Google Drive, not on Drive yet (or not finished)
  converting     on Drive, being prepared or waiting its turn for Kodi and AirPlay
  ready          on Drive and ready (a faster start that failed but plays counts as ready, as it always did)
  kept           the owner chose Keep as It Is
  problem        needs the owner (a copy that ended, a preparation that stopped or cannot keep the tracks); `hidden` when the
                 owner chose Don't Show Again for this exact reason (problem_ignore)
  cancelled      a copy the owner cancelled (listed in Download problems, never counted)
Rules decided once, here, for every screen:
  - a video on Drive is never also a copy problem (a failed earlier version of an episode that has since been copied is
    history, not a problem: owner screenshot, "S1 E6 · Unnamed download" while E6 played);
  - a video being copied again is not a problem;
  - one entry per video (an episode twice on Drive is one entry; the extra files are listed in 'duplicates').
counts(index, scope) gives every screen the same numbers. Pure: no Kodi, no network, so it is host-tested against the
owner's real states.
"""
import time

COPYING, CONVERTING, READY, KEPT, PROBLEM, CANCELLED = 'copying', 'converting', 'ready', 'kept', 'problem', 'cancelled'
STATES = (COPYING, CONVERTING, READY, KEPT, PROBLEM, CANCELLED)
WORKING = (COPYING, CONVERTING)
VERSION = 1


def show_key(title):
    import debrid_drive
    return debrid_drive.show_match(title)


def video_key(kind, show_or_title, season=0, episode=0, year=''):
    if kind == 'episode':
        return 'tv:%s:%d:%d' % (show_key(show_or_title), int(season or 0), int(episode or 0))
    return 'movie:%s:%s' % (show_key(show_or_title), str(year or ''))


def _parse(name, folder=''):
    import drivelibrary
    info = drivelibrary.parse(name) or {}
    if not info.get('title') and folder:
        info = dict(drivelibrary.parse(folder) or {}, season=info.get('season'), episode=info.get('episode'))
    return info


def _quality(name):
    try:
        import drivelibrary
        q = drivelibrary.quality(name)
        return '%dp' % q if q else ''
    except Exception:
        return ''


def _prep_state(job):
    """(state, reason, problem key) for a video on Drive from its preparation job (None: no job, it is ready as it is)."""
    if not job:
        return READY, '', ''
    source_id = str((job.get('source') or {}).get('id') or '')
    error = str(job.get('error') or '')
    if job.get('kept') and not job.get('replacing'):
        return KEPT, error or 'Kept as it is', ''
    if job.get('blocked'):
        if job.get('repack_failed'):
            return READY, '', ''          # it plays; only its faster start failed (ISSUE-230)
        return PROBLEM, error or 'Not made ready for AirPlay', 'prep:' + source_id
    status = job.get('status')
    if status in ('done', 'superseded'):
        return READY, '', ''
    if status == 'failed':
        return PROBLEM, error or 'Preparation stopped', 'prep:' + source_id
    return CONVERTING, '', ''


def _ignored(ignored, key, problem):
    if not ignored or not key:
        return False
    import problem_ignore
    return ignored.get(str(key)) == problem_ignore.signature(problem)


def build(listing, prep_state, debrid_state, upscale_state=None, ignored=None, clock=time.time):
    """The index from the Drive listing (the preparation scan's items: {'id', 'name', 'folder', 'size'}), the preparation
    state, the AllDebrid copies, the AI Upscale copies and the ignored problems ({key: signature})."""
    import debrid_drive
    import library_files as lf
    prep = lf._index_prep(prep_state)
    copies = lf._index_copies(upscale_state)
    videos, by_key, duplicates = [], {}, []

    def add(entry):
        if entry['key'] in by_key:
            duplicates.append(entry)
            return by_key[entry['key']]
        by_key[entry['key']] = entry
        videos.append(entry)
        return entry

    # 1. What is on Google Drive.
    for item in listing or []:
        name = str(item.get('name') or '')
        info = _parse(name, item.get('folder') or '')
        episode = bool(info.get('season') and info.get('episode'))
        kind = 'episode' if episode else 'movie'
        title = info.get('title') or name.rsplit('.', 1)[0]
        job = prep.get(str(item.get('id') or ''))
        state, reason, pkey = _prep_state(job)
        copy = copies.get(str(item.get('id') or '')) or {}
        entry = {'key': video_key(kind, title, info.get('season'), info.get('episode'), info.get('year')),
                 'kind': kind, 'show': title if episode else '', 'show_key': show_key(title) if episode else '',
                 'tmdb': '', 'season': int(info.get('season') or 0), 'episode': int(info.get('episode') or 0),
                 'title': title, 'year': str(info.get('year') or ''), 'id': str(item.get('id') or ''), 'name': name,
                 'size': int(item.get('size') or 0), 'quality': _quality(name), 'state': state, 'reason': reason,
                 'progress': None, 'hidden': False, 'problem_key': pkey,
                 'ai': copy.get('label', '') if copy.get('status') == 'ready' else ''}
        if state == PROBLEM:
            entry['hidden'] = _ignored(ignored, pkey, {'kind': 'prepare', 'error': reason})
        add(entry)

    # 2. What AllDebrid is copying (not on Drive yet).
    jobs = (debrid_state or {}).get('jobs', [])
    for job in jobs:
        if job.get('status') in ('done', 'failed'):
            continue
        title = debrid_drive.problem_title(job) if job.get('title') in (None, '') else job['title']
        numbers = ([int(job['episode'])] if str(job.get('episode') or '').isdigit() else
                   [int(n) for n in job.get('episodes') or [] if str(n).isdigit()])
        season = int(job['season']) if str(job.get('season') or '').isdigit() else 0
        done, total = float(job.get('copied') or 0), float(job.get('size') or 0)
        pct = int(100 * done / total) if total else None
        targets = [('episode', season, n) for n in numbers] if season and numbers else [('movie', 0, 0)]
        for kind, s, n in targets:
            key = video_key(kind, title, s, n, job.get('year') or '')
            if key in by_key:
                continue          # on Drive already (an extra version is copying): the video keeps its state
            add({'key': key, 'kind': kind, 'show': title if kind == 'episode' else '',
                 'show_key': show_key(title) if kind == 'episode' else '', 'tmdb': str(job.get('show_tmdb') or ''),
                 'season': s, 'episode': n, 'title': title, 'year': str(job.get('year') or ''), 'id': None,
                 'name': job.get('name') or '', 'size': int(job.get('size') or 0), 'quality': _quality(job.get('name') or ''),
                 'state': COPYING, 'reason': '', 'progress': pct, 'hidden': False, 'problem_key': '', 'ai': ''})

    # 3. Copies that ended (Download problems' own list), unless the video is on Drive or copying again. A copy saved
    # without a title (owner screenshot: "S1 E6 · Unnamed download") takes its show from its TMDb id, through the copies
    # that have both.
    titles = {str(j.get('show_tmdb')): j['title'] for j in jobs if j.get('show_tmdb') and j.get('title')}
    for p in debrid_drive.problems(debrid_state or {'jobs': []}):
        job = jobs[p['index']] if 0 <= p['index'] < len(jobs) else {}
        title = (str(job.get('title') or '') or titles.get(str(job.get('show_tmdb') or ''), '') or
                 debrid_drive.problem_title(job))
        season = int(p['season']) if str(p.get('season') or '').isdigit() else 0
        episode = int(p['episode']) if str(p.get('episode') or '').isdigit() else 0
        kind = 'episode' if season and episode else 'movie'
        key = video_key(kind, title, season, episode, job.get('year') or '')
        if key in by_key:
            continue          # rule: a video on Drive or copying again is never also a copy problem
        cancelled = p['kind'] == 'cancelled'
        add({'key': key, 'kind': kind, 'show': title if kind == 'episode' else '',
             'show_key': show_key(title) if kind == 'episode' else '', 'tmdb': p.get('show_tmdb') or '',
             'season': season, 'episode': episode, 'title': title, 'year': str(job.get('year') or ''), 'id': None,
             'name': p.get('name') or '', 'size': 0, 'quality': '', 'state': CANCELLED if cancelled else PROBLEM,
             'reason': p.get('error') or p.get('reason') or '', 'progress': None,
             'hidden': (not cancelled) and _ignored(ignored, p['key'], p), 'problem_key': p['key'], 'ai': ''})
    videos.sort(key=lambda e: (e['kind'] != 'episode', e['show_key'] or e['title'].casefold(), e['season'], e['episode']))
    return {'version': VERSION, 'built': clock(), 'videos': videos, 'duplicates': [d['id'] for d in duplicates if d.get('id')]}


def in_scope(entry, scope=None):
    """scope: None (the whole library), 'tv', 'movies', ('show', show title or key), ('season', show, season)."""
    if scope is None:
        return True
    if scope == 'tv':
        return entry['kind'] == 'episode'
    if scope == 'movies':
        return entry['kind'] == 'movie'
    if isinstance(scope, tuple) and scope[0] == 'show':
        return entry['kind'] == 'episode' and entry['show_key'] == show_key(scope[1])
    if isinstance(scope, tuple) and scope[0] == 'season':
        return entry['kind'] == 'episode' and entry['show_key'] == show_key(scope[1]) and entry['season'] == int(scope[2])
    return False


def counts(index, scope=None):
    """The numbers every screen shows, from one place: total (cancelled copies are not videos), ready, working, copying,
    converting, kept, problems (needing the owner, hidden ones left out) and hidden."""
    out = dict.fromkeys(('total', 'ready', 'working', 'copying', 'converting', 'kept', 'problems', 'hidden', 'cancelled'), 0)
    for e in (index or {}).get('videos', []):
        if not in_scope(e, scope):
            continue
        state = e['state']
        if state == CANCELLED:
            out['cancelled'] += 1
            continue
        out['total'] += 1
        if state == READY:
            out['ready'] += 1
        elif state in WORKING:
            out['working'] += 1
            out[state] += 1
        elif state == KEPT:
            out['kept'] += 1
        elif state == PROBLEM:
            out['hidden' if e['hidden'] else 'problems'] += 1
    return out


def shows(index):
    """Every show with episodes on Drive or on their way: [{'key', 'title', 'tmdb', 'seasons': {n: counts}}]."""
    out = {}
    for e in (index or {}).get('videos', []):
        if e['kind'] != 'episode' or e['state'] == CANCELLED:
            continue
        s = out.setdefault(e['show_key'], {'key': e['show_key'], 'title': e['show'], 'tmdb': e['tmdb'], 'seasons': {}})
        s['tmdb'] = s['tmdb'] or e['tmdb']
        s['seasons'].setdefault(e['season'], None)
    for s in out.values():
        s['seasons'] = {n: counts(index, ('season', s['key'], n)) for n in sorted(s['seasons'])}
    return sorted(out.values(), key=lambda s: s['title'].casefold())


def problems(index, include_hidden=False):
    """Download problems' rows, from the same entries: problems (and cancelled copies), hidden ones only when asked."""
    return [e for e in (index or {}).get('videos', [])
            if e['state'] == CANCELLED or (e['state'] == PROBLEM and (include_hidden or not e['hidden']))]


# ---- The shared record on disk (step 2): written by the service, read by every page -------------------------------------

FILE = 'library-index.json'
INTENTS = 'library-intents.json'
PROPERTY = 'KodiIOS.LibraryIndex'   # Window(Home) property: the change counter, so open pages redraw when it moves
INTENT_TTL = 180                    # an action shows on every page at once; after this the real state has caught up


def _dir(profile):
    import os
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')


def path(profile, name=FILE):
    import os
    return os.path.join(_dir(profile), name)


def _read(target, default):
    import json
    try:
        with open(target, encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def _write(target, data):
    import json
    import os
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.replace(tmp, target)


def load(profile):
    """The index every page reads: {'counter', 'built', 'videos', 'duplicates', 'drive' ({'ok', 'checked', 'error'})}."""
    return _read(path(profile), {'counter': 0, 'built': 0, 'videos': [], 'duplicates': [], 'drive': {}})


def inputs(profile):
    """The files the index is built from (their change times tell the service when to rebuild)."""
    import prepare_downloads
    import debrid_drive
    import upscale_queue
    import problem_ignore
    return [str(prepare_downloads.location(profile)), str(debrid_drive.location(profile)), upscale_queue.path(profile),
            problem_ignore.path(profile), path(profile, INTENTS)]


def fingerprint(profile):
    import os
    out = []
    for target in inputs(profile):
        try:
            out.append(os.stat(target).st_mtime_ns)
        except OSError:
            out.append(0)
    return tuple(out)


def refresh(profile, drive=None, clock=time.time):
    """Rebuild the index from what the service holds now and save it; the counter moves only when something a page shows
    changed. drive: {'ok', 'checked', 'error'} for the health line (None keeps the last). Returns the index."""
    import prepare_downloads
    import debrid_drive
    import upscale_queue
    import problem_ignore
    now = clock()
    prep = prepare_downloads.apply_to(prepare_downloads.load(profile), prepare_downloads.pending_requests(profile), now)
    listing = ((prep.get('library') or {}).get('items')) or []
    index = build(listing, prep, debrid_drive.load(profile), upscale_queue.load(profile), problem_ignore.load(profile), clock)
    intents = pending_intents(profile, now)
    for entry in index['videos']:
        intent = intents.get(entry['key'])
        if intent:
            entry['pending'] = intent['action']
    before = load(profile)
    index['drive'] = drive if drive is not None else before.get('drive') or {}
    index['checked'] = float((prep.get('library') or {}).get('checked') or 0)
    same = (before.get('videos') == index['videos'] and before.get('drive') == index['drive']
            and before.get('duplicates') == index['duplicates'])
    index['counter'] = int(before.get('counter') or 0) + (0 if same else 1)
    _write(path(profile), index)
    return index


def publish(profile, wait, every=2.0, set_property=None, drive_health=lambda: None, log=lambda text: None, clock=time.time):
    """The service loop: rebuild when an input changed (and at least every 30 s), keep the counter property current."""
    last_print, last_at, last_counter = None, 0.0, None
    while not wait(every):
        try:
            mark = fingerprint(profile)
            if mark == last_print and clock() - last_at < 30:
                continue
            index = refresh(profile, drive_health(), clock)
            last_print, last_at = mark, clock()
            if set_property and index['counter'] != last_counter:
                set_property(PROPERTY, str(index['counter']))
                last_counter = index['counter']
        except Exception as error:
            log('library index: %s: %s' % (type(error).__name__, error))


# ---- One action path (DEC-052 item 1): whatever page it is pressed on, every page shows it at once ---------------------

ACTIONS = ('delete', 'stop', 'retry', 'hide', 'clear')
WORDS = {'delete': 'Deleting…', 'stop': 'Stopping…', 'retry': 'Trying again…', 'hide': '', 'clear': ''}


def pending_intents(profile, now=None):
    now = time.time() if now is None else now
    data = _read(path(profile, INTENTS), {})
    return {k: v for k, v in data.items() if isinstance(v, dict) and now - float(v.get('at') or 0) < INTENT_TTL}


def intend(profile, keys, action, now=None):
    """Mark videos (index keys) with what the owner just asked; refresh() puts it on their entries, so every page shows
    "Deleting…" / "Stopping…" until the service has done it and the real state replaces it."""
    if action not in ACTIONS:
        raise ValueError('unknown action %r' % (action,))
    now = time.time() if now is None else now
    data = pending_intents(profile, now)
    for key in keys:
        data[str(key)] = {'action': action, 'at': now}
    _write(path(profile, INTENTS), data)
    return data


def entry_line(entry):
    """The one state line every page shows for a video (a pending action first)."""
    if entry.get('pending') and WORDS.get(entry['pending']):
        return WORDS[entry['pending']]
    state = entry['state']
    if state == COPYING:
        return 'Copying to Google Drive' + (' · %d%%' % entry['progress'] if entry.get('progress') is not None else '')
    if state == CONVERTING:
        return 'Getting it ready for Kodi and AirPlay'
    if state == READY:
        return ' · '.join(x for x in ('Ready', entry.get('quality') or '') if x)
    if state == KEPT:
        return 'Kept as it is'
    if state == CANCELLED:
        return 'Cancelled'
    return entry.get('reason') or 'Needs you'
