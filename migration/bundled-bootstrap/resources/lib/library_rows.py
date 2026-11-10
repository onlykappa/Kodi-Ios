"""What Settings › Library › Library status shows (library_page.py draws it, library_status.py runs it).

Pure functions over prepare_downloads.library_view(): the list rows of each section, the page's summary text and one
video's details with what can be done about it. No Kodi imports, so it is tested on its own.
"""
GB = 1024 ** 3
SECTIONS = (('preparing', 'Preparing now'), ('downloading', 'Downloading'), ('waiting', 'Waiting'),
            ('ready', 'Ready for Kodi and AirPlay'), ('kept', 'Kept as it is'))
# Owner (build 160): "make it look nice and it needs to be in like a folder so ready will show 7 then if i tap it it shows
# the movies". All shows what is happening now (preparing, downloading) as rows and the rest as folders.
FOLDERS = (('waiting', 'Waiting', 'clock-rotate-left.png', 'FFBF5AF2'), ('ready', 'Ready for Kodi and AirPlay', 'circle-check.png', 'FF30D158'),
           ('kept', 'Kept as it is', 'folder.png', 'FF8E8E93'))
SHOWN = {'ready': ('ready',), 'waiting': ('waiting',), 'kept': ('kept',),
         'working': ('preparing', 'downloading'), 'todo': ('preparing', 'waiting', 'kept'), 'downloading': ('downloading',)}
TITLES = {'all': 'Library status', 'ready': 'Ready', 'waiting': 'Waiting', 'kept': 'Kept as it is', 'todo': 'To do',
          'downloading': 'Downloading'}
DOT = '[COLOR %s]●[/COLOR]'
NOTE = 'Kodi prepares one video at a time; it slows down while a video plays.'


def ring_name(pct):
    """The ring texture for a percentage (activity_skin draws ring_00..ring_20)."""
    return 'ring_%02d.png' % max(0, min(20, int(round((pct or 0) / 5.0))))


def _positions(items):
    for n, item in enumerate(items):
        item['props']['pos'] = ('only' if len(items) == 1 else 'first' if n == 0 else 'last' if n == len(items) - 1 else 'mid')
    return items


def _video(r):
    props = {'kind': 'row', 'state': r['state'], 'id': r['id'], 'pct': str(r.get('pct', '')),
             'ring': ring_name(r.get('pct')), 'warn': 'true' if r.get('warn') else ''}
    return {'kind': 'row', 'label': r['title'], 'label2': r['sub'], 'props': props, 'row': r}


def _folder_line(key, rows):
    """The line under a folder: what is in it, in a few words."""
    titles = [r['title'] for r in rows]
    if key == 'waiting':
        first = rows[0]
        why = first['sub'].split(' · ')[0] if first['state'] != 'waiting' else 'next'
        return '%s · %s%s' % (first['title'], why, ' and %d more' % (len(rows) - 1) if len(rows) > 1 else '')
    shown = ', '.join(titles[:2])
    return shown + (' and %d more' % (len(titles) - 2) if len(titles) > 2 else '')


def list_items(view, filter_key='all'):
    """[{kind: row|folder|foot, label, label2, props}] for list 9300, in order. One layout draws them all (Kodi's
    conditional item layouts follow global conditions, not each item, so the kind is a property its parts show by)."""
    rows = view['rows']
    keys = ('downloading','waiting','ready','kept') if filter_key == 'all' else SHOWN.get(filter_key, ())
    out = []
    headings = dict(SECTIONS, preparing='WORKING ON NOW', downloading='DOWNLOADING TO GOOGLE DRIVE', waiting='UP NEXT')
    for key in keys:
        for n,r in enumerate(rows[key]):
            v = _video(r)
            v['props']['section'] = headings[key].upper() if n == 0 else ''
            v['props']['pos'] = 'only' if len(rows[key])==1 else 'first' if n==0 else 'last' if n==len(rows[key])-1 else 'mid'
            v['props']['number'] = str(n+1) if key == 'waiting' else ''
            if key == 'kept' and 'Being replaced' in r.get('sub',''):
                v['label2'] = 'Being replaced by the new download above'
            out.append(v)
    for item in out:
        item.setdefault('props', {'kind': item['kind']})
        item['props'].setdefault('kind', item['kind'])
    return out


POOL_OF = {'downloading': 'down', 'uploading': 'down', 'ready': 'ready', 'kept': 'kept'}


def pools(items):
    """Build 194: list_items() split into the page's row groups (library_page.POOLS): {'down'|'next'|'kept'|'ready': [item]},
    each with its card position ('only', 'first', 'mid', 'last') and, for Up next, its number."""
    out = {}
    for item in items:
        if item.get('kind') != 'row':
            continue
        state = item['props'].get('state', '')
        if state == 'preparing':
            continue
        out.setdefault(POOL_OF.get(state, 'next'), []).append(dict(item, props=dict(item['props'])))
    for key, rows in out.items():
        for n, item in enumerate(rows):
            item['props']['pos'] = 'only' if len(rows) == 1 else 'first' if n == 0 else 'last' if n == len(rows) - 1 else 'mid'
            item['props']['number'] = str(n + 1) if key == 'next' else ''
            if key == 'ready':
                item['label2'] = ready_quality(item.get('row') or {})
            elif item.get('label2'):
                item['label2'] = item['label2'][:1].upper() + item['label2'][1:]
    return out


def ready_quality(row):
    """Board 1's right-hand note on a ready row ('4K HDR', '1080p'): the picture only, never the size."""
    sub = str(row.get('sub') or '')
    first = sub.split(' · ')[0] if sub else ''
    return {'2160p': '4K', '4k': '4K'}.get(first.lower(), first) if first and not first.endswith('GB') else ''


def speed_left(job):
    """('4.8 MB/s', '· 6 min left') for the working card's second row; ('', '') with no measured speed yet."""
    import work_state
    if not job or job.get('state') not in work_state.MOVING or float(job.get('rate') or 0) <= 0:
        return '', ''
    left = work_state.left(job.get('eta_s')) if job.get('eta_s') else ''
    return work_state.speed(job.get('rate')), ('· ' + left) if left else ''


def segments(counts, width, gap):
    """[(x, w)] for the summary bar's four segments (ready, working, up next, kept), sized by count with `gap` units
    between the ones that show; zero-count segments get width 0."""
    shown = [c for c in counts if c > 0]
    total = sum(shown)
    if not total:
        return [(0, 0)] * len(counts)
    room = width - gap * (len(shown) - 1)
    out, x, used = [], 0, 0
    last = max(i for i, c in enumerate(counts) if c > 0)
    for i, c in enumerate(counts):
        if c <= 0:
            out.append((x, 0))
            continue
        w = room - used if i == last else max(8, int(round(room * c / float(total))))
        out.append((x, w))
        x += w + gap
        used += w
    return out


def page_properties(view, checking=False):
    """Window properties for the page's top: subtitle, ring, headline and legend."""
    rows = view['rows']
    counts = {'ready': view['ready'], 'working': len(rows['preparing'])+len(rows['downloading']),
              'next': len(rows['waiting']), 'kept': view['kept']}
    total = sum(counts.values())
    eta = sum(float(r.get('eta_s') or 0) for group in rows.values() for r in group)
    props = {'sub': 'Kodi Downloads on Google Drive · '+('checking now…' if checking else view['checked']),
             'headline': '%d of %d ready'%(view['ready'],view['total']) if view['total'] else 'Not checked yet',
             'ring': ring_name(view['pct']), 'pct': str(view['pct']), 'legend': ''}
    import work_state
    remaining=work_state.remaining_text(view.get('model')) if 'model' in view else ('about '+minutes_text(eta) if eta else '')
    props['remaining']=remaining+' to go' if remaining else ''
    cumulative=0
    for key,n in counts.items():
        cumulative+=n
        props['count.'+key]=str(n)
        props['summary.'+key]=str(100*cumulative/max(1,total))
    return props


def short_eta(text):
    """'about 25 min left' as 'about 25 min' (the fact is already called Time left)."""
    text = str(text or '')
    return text[:-5] if text.endswith(' left') else text


CONV, DOWN = 'FFBF5AF2', 'FF0A84FF'
FACTS = 5


def film_text(done, total):
    """'46 of 148 min of the film' ('' while the film's length is unknown)."""
    try:
        done, total = float(done or 0), float(total or 0)
    except (TypeError, ValueError):
        return ''
    return '%d of %d min of the film' % (done // 60, round(total / 60)) if total > 0 else ''


def clock_text(seconds, now=None):
    """'4:35 PM' when something `seconds` from now ends ('' when unknown or more than a day away)."""
    import time as _time
    try:
        seconds = float(seconds or 0)
    except (TypeError, ValueError):
        return ''
    if seconds <= 0 or seconds > 86400:
        return ''
    t = _time.localtime((_time.time() if now is None else now) + seconds)
    return _time.strftime('%I:%M %p', t).lstrip('0')


def day_text(when, now=None):
    """'Today', 'Yesterday' or '6 Nov' ('' when unknown)."""
    import time as _time
    if not when:
        return ''
    now = _time.time() if now is None else now
    a, b = _time.localtime(when), _time.localtime(now)
    days = (_time.mktime(b[:3] + (0, 0, 0, 0, 0, -1)) - _time.mktime(a[:3] + (0, 0, 0, 0, 0, -1))) // 86400
    return 'Today' if days == 0 else 'Yesterday' if days == 1 else '%d %s' % (a.tm_mday, _time.strftime('%b', a))


def minutes_text(seconds):
    m = int(max(0, seconds) // 60)
    return 'under a minute' if m < 1 else '%d min' % m if m < 60 else '%d h %d min' % (m // 60, m % 60)


def picture_text(probe, kept=False):
    """'4K HDR', 'HD' ... from the native probe; kept=True adds ', kept as 4K HDR' (the picture is not made smaller)."""
    if not probe:
        return ''
    w = int(probe.get('width') or 0)
    res = '4K' if w >= 3000 else 'HD' if w >= 1200 else 'SD' if w else ''
    what = ' '.join(x for x in (res, 'HDR' if probe.get('hdr') else '') if x)
    return '%s, kept as %s' % (what, what) if kept and what else what


QUICKER = ('Find a version without converting', 'quicker')


def matches_job(job, row):
    """Only conversions may borrow library metadata by title. Transfer rows carry their own job key."""
    import work_state
    if row.get('work_key'):
        return tuple(row['work_key']) == work_state.job_key(job)
    same_id=bool(job.get('id') and row.get('id') and str(job['id'])==str(row['id']))
    return same_id or (job.get('kind') in ('conv','repack') and bool(job.get('title')) and job['title']==row.get('title'))


def details(row, view):
    """One video's details sheet: title, status (tone ok|warn|plain), quality, up to 4 facts and up to 2 actions
    (label, request) where request is prepare_downloads.request's action, or None."""
    size = row.get('size') or 0
    on_drive = ('On Google Drive', '%.1f GB' % (size / GB)) if size else None
    folder = ('Folder', row.get('folder') or 'Kodi Downloads') if row.get('folder') else None
    state = 'ready' if row.get('ready_now') else row['state']
    sheet = {'title': row['title'], 'quality': '', 'facts': [], 'actions': [], 'tone': 'plain', 'status': row.get('sub', ''),
             'bar': '', 'bar_tint': ''}
    # Build 177 (owner-approved movie sheet): a live speed card for anything moving, and rows that each answer one
    # question. "On Google Drive" (the original's size) and "Speed: 1.8 GB read" are gone (owner: they "dont make sense").
    sheet['card'] = ''
    sheet['step'] = str(row.get('step') or '')
    if state == 'ready':
        probe = row.get('probe') or {}
        sheet.update(status='Ready on iPhone and Apple TV', tone='ok', quality='Seeks straight away over AirPlay',
                     facts=[f for f in (('Kodi', 'Opens in about 1 s' if not row.get('repack') else 'Ready to play'),
                                        ('AirPlay', 'Ready, seeks instantly'),
                                        ('Picture', picture_text(probe, kept=False) or row.get('sub', '')),
                                        ('Sound and subtitles', probe.get('audio_description') or 'See playback options')) if f],
                     actions=[('Play', 'play'), ('Play on TV', 'tv')])
        if row.get('stream_only'):
            sheet.update(status='Ready to stream',quality='Original file · No background conversion',
                         facts=[('Picture','Original quality'),
                                ('Faster opening','Queued' if row.get('repack') else 'Checked' if probe.get('fast_open') else 'Not checked yet'),
                                ('AirPlay','Prepared during playback if needed'),('On Google Drive','Original file kept')])
    elif state == 'preparing':
        pct = row.get('pct', 0)
        out_total = row.get('out_total') or 0
        sheet.update(status='Converting for Apple TV' + (' · %s%%' % pct if pct and not row.get('indeterminate') else ''),
                     tone='conv', quality='Plays on iPhone already · TV after this', card='conv',
                     facts=[f for f in (('Done so far', film_text(row.get('film_done'), row.get('film_total')) or 'starting'),
                                        ('Ready around', clock_text(row.get('eta_s')) or 'working it out'),
                                        ('Pace', '%.1f× faster than the film plays' % float(row['pace'])) if row.get('pace') else None,
                                        ('Picture', picture_text(row.get('probe'), kept=True)) if row.get('probe') else None,
                                        ('Size', '%.1f GB now' % (size / GB) + (' · about %.1f GB after' % (out_total / GB) if out_total else ''))
                                        if size else None) if f])
        if not row.get('probe') and row.get('step') in ('Checking compatibility','Reading from Google Drive','Inspecting video and track index','Opening conversion tracks'):
            sheet.update(status='Checking compatibility',quality='Only needed preparation will run')
        if pct and not row.get('indeterminate'):
            sheet.update(bar=str(pct), bar_tint=CONV)
    elif state in ('downloading', 'uploading'):
        sent, total = row.get('sent') or 0, row.get('total') or 0
        fetching = row.get('stage') == 'fetching'
        debrid = state == 'uploading'
        sheet.update(status=('AllDebrid is fetching it' if fetching else 'Downloading') + ' · %s%%' % row.get('pct', 0),
                     tone='down', quality='Straight to Google Drive, not the phone' if debrid else 'To this iPhone, then to Google Drive',
                     card='up' if debrid else 'down',
                     facts=[f for f in (('Downloaded', '%.1f of %.1f GB' % (sent / GB, total / GB)) if total and not fetching else None,
                                        ('Done around', clock_text(row.get('eta_s')) or 'working it out'),
                                        ('Through', 'AllDebrid' if debrid else 'Elementum (torrent)'),
                                        ('Saving to', 'Drive › Kodi Downloads' + (' › ' + row['folder'] if row.get('folder') else '')),
                                        ('After that', 'Converted for Apple TV if it needs it')) if f])
        sheet.update(bar=str(row.get('pct', 0)), bar_tint=DOWN)
    elif state == 'waiting':
        sheet.update(status=row.get('sub', '').split(' · ')[0], quality=' · '.join(row.get('sub', '').split(' · ')[1:]),
                     facts=[f for f in (on_drive, folder) if f],
                     actions=[('Start converting now', 'now'), ('Prepare next', 'next'), ('Keep as it is', 'keep')])
    elif state == 'space':
        free = view.get('free') or 0
        sheet.update(status='Waiting for phone space', tone='warn',
                     facts=[f for f in (on_drive, ('Needs free', '%.0f GB, incl. 5 GB kept for you' % (row.get('needs', 0) / GB)),
                                        ('Free now', '%.0f GB' % (free / GB)), ('Why', row['why'][:1].upper() + row['why'][1:]) if row.get('why') else None) if f],
                     actions=[("Prepare first when there's room", 'next'), ('Keep as it is', 'keep')])
    elif state == 'problem':
        sheet.update(status='Paused · %s' % row.get('reason', 'a problem'), tone='warn',
                     facts=[f for f in (on_drive, ('What happened', row.get('reason', '')), ('Next try', row.get('sub', '').split(' · ')[0])) if f])
        if row.get('reason'):
            sheet['actions'] = [('Try again now', 'retry'), ('Keep as it is', 'keep')]
    elif state == 'kept':
        sheet.update(status='Kept as it is', facts=[f for f in (on_drive, ('Why', row.get('sub', '').replace('Kept as it is · ', ''))) if f])
        if row.get('owner'):
            sheet['actions'] = [('Prepare it after all', 'prepare')]
    # Owner (build 184): a movie that must be re-encoded (AV1) can be swapped for a version that is only repackaged.
    if row.get('reencode') and state in ('waiting', 'space', 'problem', 'preparing'):
        sheet['actions'] = ([QUICKER] + [a for a in sheet['actions'] if a[1] != 'next'])[:3]
        sheet['facts'] = sheet['facts'][:FACTS - 1] + [('Why it is slow', 'AV1 is re-encoded on the phone; HEVC and H.264 are only repackaged')]
    model = view.get('model')
    import work_state
    live = next((j for j in (model or {}).get('jobs',[]) if matches_job(j,row)), None)
    if live:
        converting=live['kind'] in ('conv','repack')
        actions=[('Resume' if live['state']=='paused_by_you' else 'Pause','toggle')]
        if converting:
            actions.insert(0,('Play','play'))
            if row.get('reencode'):actions.append(QUICKER)
        elif (live['kind']=='down' and live.get('id')) or (live['kind']=='copy' and live.get('hash')):
            actions.append(('Cancel','cancel'))
        sheet.update(status=live['line'], step=live['step'], bar=str(live.get('pct') or 0), bar_tint=live['tint_now'],
                     card='conv' if live['kind'] in ('conv','repack') else 'up' if live['kind'] in ('copy','upload') else 'down',
                     actions=actions)
    probe = row.get('probe') or {}
    picture, codec = picture_text(probe), str(probe.get('codec') or '').upper()
    if not picture or not codec:
        guess_picture, guess_codec = name_quality(row.get('name') or row.get('title') or '')
        picture, codec = picture or guess_picture, codec or guess_codec
    sheet['quality'] = ' · '.join(x for x in (picture, codec, '%.1f GB'%(size/GB) if size else '') if x)
    sheet['sentence'] = ('Preparing faster opening while keeping the original picture quality.' if live['kind']=='repack' else 'Play on this iPhone while Kodi gets it ready for AirPlay.') if live and live['kind'] in ('conv','repack') else ''
    ready = state == 'ready'
    sheet['steps'] = [('Downloaded', 'FF30D158'), ('On Drive' if state not in ('downloading','uploading') else 'On Drive…',
                      'FF30D158' if state not in ('downloading','uploading') else DOWN),
                     ('Ready' if ready else SHORT_STEP.get((live or {}).get('step') or sheet['step'] or sheet['status'], (live or {}).get('step') or sheet['step'] or sheet['status']) + (' · %d%%'%float(live.get('pct') or 0) if live and not live.get('indeterminate') else ''),
                      'FF30D158' if ready else (live or {}).get('tint_now') or CONV)]
    sheet['live'] = live
    sheet['need'] = ((model or {}).get('needs') or [{}])[0]
    sheet['facts'] = sheet['facts'][:FACTS]
    return sheet


SHORT_STEP = {'Making it start faster': 'Faster start'}


def clock12(when):
    """'1:13 PM' (board 3's Started, the phone's clock style)."""
    import time
    t = time.localtime(when)
    return '%d:%02d %s' % ((t.tm_hour % 12) or 12, t.tm_min, 'AM' if t.tm_hour < 12 else 'PM')


def speed_card_text(live, history_job, size=0, bar=0):
    """Board 3's speed card words: the number and its unit apart ('4.8', 'MB/s'), time left, Average, Done, Started.
    No speed measured yet: no number (never '0.0 MB/s'); the graph area then says what it is doing."""
    import transfer_history as th
    live, j = live or {}, history_job or {}
    rate = float(live.get('rate') or 0)
    moving = live.get('state') in ('running', 'slowed') and rate > 0
    num, unit = (th.mb(rate).split(' ', 1) + [''])[:2] if moving else ('—', '')
    import prepare_downloads
    avg = j.get('sum', 0) / max(1, j.get('n', 1)) if j.get('n') else 0
    done = float(j.get('done') or 0)
    return {'card.num': num, 'card.unit': unit,
            'card.left': prepare_downloads.eta_text(live.get('eta_s')).replace('about ', '') if moving and live.get('eta_s') else '',
            'card.avg': th.mb(avg) if avg > 0 else '—',
            'card.done': ('%.1f of %.1f GB' % (done / GB, float(size) / GB)) if size and done else '%d%%' % int(float(bar or 0)),
            'card.started': clock12(j['start']) if j.get('start') else '—'}   # board 3's third step label


def name_quality(name):
    """('4K HDR', 'HEVC') guessed from a release name when the movie has no probe yet (board 3: '4K · HEVC · 2.8 GB')."""
    import re
    n = str(name or '').lower()
    picture = '4K' if re.search(r'2160p|\b4k\b|uhd', n) else '1080p' if '1080p' in n else '720p' if '720p' in n else ''
    if picture and re.search(r'\bhdr|dolby.?vision|\bdv\b', n):
        picture += ' HDR'
    codec = ('AV1' if re.search(r'\bav1\b', n) else 'HEVC' if re.search(r'x265|hevc|h\.?265', n) else
             'H.264' if re.search(r'x264|h\.?264|avc', n) else '')
    return picture, codec


def card(history, kind, title, now, step=''):
    """The live speed card of a movie's sheet (build 177): window properties and the points to paint, from
    transfer_history's job of that kind when it is this movie's. ({}, []) when there is none yet ("Measuring…").
    step: what the movie is doing now; shown instead of "starting" while nothing moves yet (build 192, owner:
    "seems to just be stuck on starting ... its not showing me what its doing")."""
    import transfer_history as th
    job = (history.get('jobs') or {}).get(kind)
    if not job or job.get('title') != title or now - job.get('last', 0) > 15:
        return {'card.now': step or 'starting', 'card.peak': '–', 'card.avg': '–', 'card.left': '–', 'card.from': ''}, []
    pts = job.get('points') or []
    rate = pts[-1][1] if pts else 0.0
    left = ''
    if kind == 'conv':
        left = short_eta((job.get('extra') or {}).get('eta'))
    elif rate and job.get('total'):
        import prepare_downloads
        left = short_eta(prepare_downloads.eta_text((float(job['total']) - float(job.get('done') or 0)) / rate))
    return ({'card.now': th.mb(rate) if rate > 0 else 'Starting…', 'card.peak': th.mb(job.get('peak')),
             'card.avg': th.mb(job.get('sum', 0) / max(1, job.get('n', 1))), 'card.left': left or '–',
             'card.from': th.ago(now - job['start']).replace('just now', 'a moment ago')}, pts)


def with_model(view, model):
    """Metadata stays in the library; only work_state decides current jobs and queue order."""
    import work_state
    rows=view['rows']
    lookup={r['id']:r for rr in rows.values() for r in rr}
    by_title={r['title']:r for r in lookup.values()}
    rows['preparing']=[];rows['downloading']=[]
    active_ids=set()
    for j in (model or {}).get('jobs') or []:
        if j['kind']=='check':continue
        base=lookup.get(j.get('id')) or (by_title.get(j['title']) if j['kind'] in ('conv','repack') else None) or {}
        state='preparing' if j['kind'] in ('conv','repack') else 'downloading' if j['kind']=='down' else 'uploading'
        r=dict(base,**{k:v for k,v in j.items() if k not in ('state',)})
        r.update(id=base.get('id') or j.get('id') or 'work:'+':'.join(work_state.job_key(j)),work_key=work_state.job_key(j),state=state,sub=j['line'],step=j['step'],size=base.get('size') or j.get('total') or 0)
        rows['preparing' if state=='preparing' else 'downloading'].append(r)
        active_ids.add(r['id'])
    # A ready faster-start job may run; it appears once in the summary.
    for key in ('ready','kept'):
        rows[key]=[r for r in rows[key] if r['id'] not in active_ids]
    waiting=[]
    for j in (model or {}).get('next') or []:
        base=lookup.get(j['id']) or by_title.get(j['title']) or {}
        waiting.append(dict(base,**j,state=base.get('state') if base.get('state') in ('space','problem') else 'waiting',ready_now=base.get('state')=='ready',repack=j['what']=='faster start',sub=base.get('sub','') if base.get('state') in ('space','problem') else ('Ready now · ' if base.get('state')=='ready' else '')+j['what']+' · %.1f GB'%(float(j.get('size') or 0)/GB)))
    # Retain actionable problems and phone-space explanations, but never invent queued jobs.
    rows['waiting']=waiting+[r for r in rows['waiting'] if r['state']!='waiting' and r['id'] not in active_ids and r['id'] not in {j['id'] for j in waiting}]
    queued_ids={j['id'] for j in waiting}
    rows['ready']=[r for r in rows['ready'] if r['id'] not in queued_ids]
    view.update(model=model,ready=len(rows['ready']),kept=len(rows['kept']),todo=len(rows['preparing'])+len(rows['waiting']),
                downloading=len(rows['downloading']))
    view['total']=sum(len(rr) for rr in rows.values())
    view['pct']=round(100*view['ready']/max(1,view['total']))
    return view
