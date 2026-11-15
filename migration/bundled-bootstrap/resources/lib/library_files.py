"""Library file manager, step L1 (ROADMAP "Mockup roadmap", DEC-043): one model of everything downloaded.

Pure Python over what the app already records, no Kodi or Drive calls, so the TV Shows, show, episode, Movies and Free
Up Space pages (boards A-F of docs/design/library-files-mockups.html) read one consistent picture:
- the Drive library listing (drivelibrary.listing: show folders, a show's episode files, movie files),
- the preparation queue (prepare_downloads state: converting, ready, problem),
- AllDebrid → Drive copies (debrid_drive jobs: copying, failed),
- AI Upscale copies (upscale_queue state),
- what was watched (a set of Drive file ids or names).

States, one per file, in the order a file goes through them: copying → converting → ready; problem at any step;
an AI copy is an extra fact on a ready file. 'unknown' when nothing the app records says otherwise (a file another
build prepared); it is drawn as ready-for-Kodi only when the Drive file carries the prepared marker.
"""
import re

COPYING, CONVERTING, READY, PROBLEM, UNKNOWN = 'copying', 'converting', 'ready', 'problem', 'unknown'
WORKING_PREP = ('waiting', 'running', 'paused', 'committing', 'new')
PROBLEM_PREP = ('failed',)
EPISODE = re.compile(r'(?i)\bS(\d{1,3})E(\d{1,4})\b')


def _index_prep(prep_state):
    """Drive file id → its preparation job (by the original id and by the prepared file's id)."""
    out = {}
    for job in (prep_state or {}).get('jobs', {}).values():
        source = job.get('source') or {}
        for key in (source.get('id'), job.get('prepared_id')):
            if key:
                out[str(key)] = job
    return out


def _index_copies(upscale_state):
    out = {}
    for original, entry in (upscale_state or {}).get('copies', {}).items():
        out[str(original)] = entry
    return out


def file_state(item, prep, copies, watched=()):
    """The state of one Drive file: {'state', 'line', 'progress', 'ai', 'ai_label', 'watched', 'problem'}."""
    item_id = str(item.get('id') or '')
    job = prep.get(item_id)
    out = {'state': UNKNOWN, 'progress': None, 'ai': False, 'ai_label': '', 'problem': '',
           'watched': item_id in watched or str(item.get('name') or '') in watched,
           'job_id': str(((job or {}).get('source') or {}).get('id') or ''), 'probe': dict((job or {}).get('probe') or {}),
           'ai_size': 0}
    if job:
        status = job.get('status')
        if job.get('blocked'):
            out.update(state=READY if job.get('repack_failed') else PROBLEM, problem=str(job.get('error') or ''))
        elif status == 'done' or status == 'superseded':
            out['state'] = READY
        elif status in PROBLEM_PREP:
            out.update(state=PROBLEM, problem=str(job.get('error') or 'Preparation paused'))
        elif status in WORKING_PREP:
            out['state'] = CONVERTING
        else:
            out['state'] = UNKNOWN
    elif item.get('prepared'):
        out['state'] = READY
    copy = copies.get(item_id)
    if copy and copy.get('status') == 'ready':
        out.update(ai=True, ai_label=copy.get('label', ''), ai_size=int(copy.get('size') or 0))
    return out


def _copying_episodes(debrid_state):
    """(show title casefold, season, episode) → progress 0..100 for AllDebrid copies still running, and failed ones."""
    running, failed = {}, {}
    # ISSUE-250: a failure is not a problem while another version of that episode is copying or done.
    alive = {(str(j.get('title') or '').casefold(), str(j.get('season') or ''), str(j.get('episode') or ''))
             for j in (debrid_state or {}).get('jobs', []) if j.get('status') != 'failed'}
    for job in (debrid_state or {}).get('jobs', []):
        if job.get('status') == 'failed' and (str(job.get('title') or '').casefold(), str(job.get('season') or ''),
                                               str(job.get('episode') or '')) in alive:
            continue
        title = str(job.get('title') or '').casefold()
        if job.get('kind') == 'movie' or not title:
            continue
        numbers = [int(job['episode'])] if str(job.get('episode') or '').isdigit() else list(job.get('episodes') or [])
        season = int(job['season']) if str(job.get('season') or '').isdigit() else 0
        target = failed if job.get('status') == 'failed' and job.get('error') != 'Cancelled' else (
            running if job.get('status') not in ('done', 'failed') else None)
        if target is None:
            continue
        done, total = float(job.get('copied') or 0), float(job.get('size') or 0)
        for n in numbers:
            target[(title, season, int(n))] = int(100 * done / total) if total else None
    return running, failed


def show_rows(shows, episodes_by_show, prep_state, debrid_state=None, upscale_state=None, watched=()):
    """Board A: one row per show: title, year, seasons, episodes, size, counts per state and the chips to draw.
    episodes_by_show: show folder id → its drivelibrary.episodes() list."""
    prep, copies = _index_prep(prep_state), _index_copies(upscale_state)
    running, failed = _copying_episodes(debrid_state)
    rows = []
    for show in shows:
        files = episodes_by_show.get(show['id']) or []
        counts = {READY: 0, CONVERTING: 0, COPYING: 0, PROBLEM: 0, UNKNOWN: 0}
        ai = size = 0
        seasons = set()
        have = set()
        for f in files:
            state = file_state(f, prep, copies, watched)
            counts[state['state']] += 1
            ai += state['ai']
            size += int(f.get('size') or 0)
            if f.get('season'):
                seasons.add(int(f['season']))
                have.add((int(f['season']), int(f.get('episode') or 0)))
        key = str(show.get('title') or '').casefold()
        copying = [k for k in running if k[0] == key and (k[1], k[2]) not in have]
        problems = [k for k in failed if k[0] == key and (k[1], k[2]) not in have and k not in running]   # ISSUE-250: copying again is not a problem
        counts[COPYING] += len(copying)
        counts[PROBLEM] += len(problems)
        seasons |= {k[1] for k in copying + problems if k[1]}
        rows.append({'id': show['id'], 'title': show.get('title') or show.get('name') or '', 'year': show.get('year'),
                     'seasons': sorted(seasons), 'episodes': len(files) + len(copying) + len(problems), 'size': size,
                     'counts': counts, 'ai': ai, 'chips': chips(counts, ai, len(files) + len(copying) + len(problems))})
    return rows


def chips(counts, ai, total):
    """Board A's chips: ('All ready', 'green') or ('29 ready', 'green'), ('3 converting', 'orange'), ('1 problem', 'red'),
    ('AI 4K · 11', 'purple'), at most three."""
    out = []
    ready = counts.get(READY, 0) + counts.get(UNKNOWN, 0)
    if total and ready == total:
        out.append(('All ready', 'green'))
    elif ready:
        out.append(('%d ready' % ready, 'green'))
    if counts.get(PROBLEM):   # never dropped by the three-chip limit: what needs the owner comes first
        out.append(('%d problem%s' % (counts[PROBLEM], '' if counts[PROBLEM] == 1 else 's'), 'red'))
    if counts.get(CONVERTING):
        out.append(('%d converting' % counts[CONVERTING], 'orange'))
    if counts.get(COPYING):
        out.append(('%d copying' % counts[COPYING], 'blue'))
    if ai:
        out.append(('AI · %d' % ai, 'purple'))
    return out[:3]


def episode_rows(show, files, prep_state, debrid_state=None, upscale_state=None, watched=(), names=None):
    """Board B: one season's episodes (all seasons, season-major), each with one state line. names: (season, episode)
    → TMDb episode name. Episodes still copying or failed to copy appear with that state (Repair on a problem)."""
    prep, copies = _index_prep(prep_state), _index_copies(upscale_state)
    running, failed = _copying_episodes(debrid_state)
    names = names or {}
    rows, have = [], set()
    for f in files:
        state = file_state(f, prep, copies, watched)
        season, number = int(f.get('season') or 0), int(f.get('episode') or 0)
        have.add((season, number))
        rows.append(dict(state, id=f.get('id'), file=f.get('name') or '', quality=f.get('quality') or '', season=season, episode=number, size=int(f.get('size') or 0),
                         name=names.get((season, number)) or f.get('title') or f.get('name'),
                         line=state_line(state, f), repair=state['state'] == PROBLEM))
    key = str(show.get('title') or '').casefold()
    for (title, season, number), pct in list(running.items()) + [(k, None) for k in failed]:
        if title != key or (season, number) in have:
            continue
        problem = (title, season, number) in failed
        state = {'state': PROBLEM if problem else COPYING, 'progress': pct, 'ai': False, 'ai_label': '',
                 'problem': 'Not added' if problem else '', 'watched': False, 'job_id': '', 'probe': {}, 'ai_size': 0}
        rows.append(dict(state, id=None, season=season, episode=number, size=0, name=names.get((season, number)) or '',
                         line='Not added' if problem else ('Copying to Drive · %d %%' % pct if pct is not None else 'Copying to Drive'),
                         repair=problem))
        have.add((season, number))
    rows.sort(key=lambda r: (r['season'], r['episode']))
    return rows


def state_line(state, item=None):
    """Board B's one line: 'Ready · 1080p · 262 MB', 'Converting · 42 %', 'Problem: …'."""
    size = _size(int((item or {}).get('size') or 0))
    quality = (item or {}).get('quality') or ''
    if state['state'] == PROBLEM:
        return 'Problem · ' + (state.get('problem') or 'tap for why')[:60]
    if state['state'] == CONVERTING:
        return 'Converting' + (' · %d %%' % state['progress'] if state.get('progress') is not None else '')
    if state['state'] == COPYING:
        return 'Copying to Drive'
    parts = ['Ready'] + ([quality] if quality else []) + ([size] if size else [])
    if state.get('ai'):
        parts.append('AI ' + (state.get('ai_label') or ''))
    return ' · '.join(p.strip() for p in parts if p.strip())


def movie_rows(movies, prep_state, upscale_state=None, watched=(), sort='recent'):
    """Board E: posters with size and a state badge, sorted by 'recent' (listing order), 'name' or 'size'."""
    prep, copies = _index_prep(prep_state), _index_copies(upscale_state)
    rows = []
    for m in movies:
        state = file_state(m, prep, copies, watched)
        badge = {READY: 'Ready', UNKNOWN: 'Ready', CONVERTING: 'Converting', PROBLEM: 'Problem', COPYING: 'Copying'}[state['state']]
        if state['state'] == CONVERTING and state.get('progress') is not None:
            badge = '%d %%' % state['progress']   # board E: "42 %" on a movie still converting
        if state['ai']:
            badge = 'AI ' + (state['ai_label'] or '4K')
        rows.append(dict(state, id=m.get('id'), title=m.get('title') or m.get('name'), year=m.get('year'),
                         size=int(m.get('size') or 0), quality=m.get('quality') or '', badge=badge))
    if sort == 'name':
        rows.sort(key=lambda r: str(r['title']).casefold())
    elif sort == 'size':
        rows.sort(key=lambda r: -r['size'])
    return rows


def storage(show_rows_, movie_rows_, upscale_state=None, quota=None):
    """Board A's storage card: bytes for shows, movies, AI copies, and Drive's quota (used, limit) when known."""
    ai = sum(int(e.get('size') or 0) for e in (upscale_state or {}).get('copies', {}).values() if e.get('status') == 'ready')
    shows = sum(r['size'] for r in show_rows_)
    movies = sum(r['size'] for r in movie_rows_)
    out = {'shows': shows, 'movies': movies, 'ai': ai, 'total': shows + movies + ai}
    if quota:
        out.update(used=int(quota.get('usage') or 0), limit=int(quota.get('limit') or 0))
    return out


def free_up(show_rows_, episodes_by_show, movie_rows_, upscale_state=None, watched=()):
    """Board F: groups of things that can go, each with its bytes: watched episodes, AI copies, the largest movies."""
    watched_eps = []
    for show in show_rows_:
        for f in episodes_by_show.get(show['id']) or []:
            if str(f.get('id')) in watched or str(f.get('name')) in watched:
                watched_eps.append(f)
    ai = [dict(e, original=k) for k, e in (upscale_state or {}).get('copies', {}).items() if e.get('status') == 'ready']
    largest = sorted(movie_rows_, key=lambda r: -r['size'])[:5]
    return [
        {'key': 'watched', 'title': 'Watched episodes', 'count': len(watched_eps),
         'bytes': sum(int(f.get('size') or 0) for f in watched_eps), 'items': [f.get('id') for f in watched_eps]},
        {'key': 'ai', 'title': 'AI Upscale copies', 'count': len(ai),
         'bytes': sum(int(e.get('size') or 0) for e in ai), 'items': [e.get('copy_id') for e in ai]},
        {'key': 'largest', 'title': 'Largest movies', 'count': len(largest),
         'bytes': sum(r['size'] for r in largest), 'items': [r['id'] for r in largest]},
    ]


def search(rows, text):
    text = ' '.join(str(text or '').casefold().split())
    return [r for r in rows if text in str(r.get('title') or '').casefold()] if text else list(rows)


def sort_shows(rows, how='recent'):
    if how == 'name':
        return sorted(rows, key=lambda r: str(r['title']).casefold())
    if how == 'size':
        return sorted(rows, key=lambda r: -r['size'])
    return list(rows)


def _size(n):
    if n <= 0:
        return ''
    if n >= 1024 ** 3:
        return '%.1f GB' % (n / 1024.0 ** 3)
    return '%d MB' % round(n / 1024.0 ** 2)


size_text = _size
