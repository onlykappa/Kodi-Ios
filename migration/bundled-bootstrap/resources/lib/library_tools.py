"""What the four library tools show (owner-approved mockup, docs/design/library-tools-mockups.html; spec
docs/design/library-tools-spec.md). Pure functions, no Kodi imports, so each is tested on its own; library_tools_page.py
draws the pages and the bootstrap's library_tools.py runs them.

- Queue: Library status › Waiting › Edit order. Converting now, Up next in order (▲ ▼ write prepare_downloads requests
  'up' / 'down'; the running conversion is never stopped for them), Downloading to Google Drive (debrid_drive jobs).
- History: Transfers › History. What finished each day (transfer_history) and what failed (transfer_history.failures).
- AirPlay check: Play on TV › Last time, or an AirPlay notification. The last Play on TV as steps, from the KodiAirPlay
  log lines kept by note_airplay().
"""
import json
import os
import re
import threading
import time

GB = 1024 ** 3
MB = 1024 ** 2
ADDON_DATA = os.path.join('addon_data', 'service.kodi.ios.bootstrap')


def size_text(n):
    n = float(n or 0)
    return '%d MB' % round(n / MB) if n < GB else '%.1f GB' % (n / GB)


# --- Queue ------------------------------------------------------------------------------------------------------------
QUEUE_SLOTS = 10   # Up next rows with ▲ ▼ on the page; the rest are counted below them
DRIVE_SLOTS = 3
HELD_SLOTS = 3


def queue_view(view, debrid_jobs=(), now=None):
    """The Queue page from prepare_downloads.library_view() and debrid_drive's jobs:
    {'now': row or None, 'line': [rows that can move, top first], 'held': [rows waiting for something], 'drive': [...]}.
    Each line row has 'up' / 'down' ('true' when that arrow can move it)."""
    rows = view.get('rows') or {}
    current = (rows.get('preparing') or [None])[0]
    now_row = None
    if current:
        now_row = {'id': current['id'], 'title': current['title'],
                   'sub': ' · '.join(x for x in (current.get('video'), '%d%%' % current['pct'] if current.get('pct') else '',
                                                 current.get('eta')) if x) or current.get('sub', '')}
    waiting = rows.get('waiting') or []
    line = [r for r in waiting if r['state'] == 'waiting']
    out = []
    for n, r in enumerate(line):
        out.append({'id': r['id'], 'name': r.get('name', ''), 'title': r['title'],
                    'sub': ' · '.join(r['sub'].split(' · ')[1:]) or r['sub'],
                    'up': 'true' if n else '', 'down': 'true' if n < len(line) - 1 else ''})
    held = [{'id': r['id'], 'name': r.get('name', ''), 'title': r['title'], 'sub': r['sub']} for r in waiting if r['state'] != 'waiting']
    drive = []
    for job in debrid_jobs or ():
        status = job.get('status')
        if status in ('done', 'failed'):
            continue
        title = job.get('title') or job.get('name', '')
        if status == 'copying' and job.get('_current'):
            c = job['_current']
            pct = int(100 * float(c.get('sent') or 0) / float(c['total'])) if c.get('total') else 0
            rate = float(c.get('rate') or 0)
            eta = _eta(c.get('eta_s'))
            sub = ' · '.join(x for x in ('%d%%' % pct, '%.1f MB/s' % (rate / MB) if rate else '', eta) if x)
            drive.append({'title': title, 'sub': sub, 'tone': 'ok'})
        elif status == 'fetching':
            drive.append({'title': title, 'sub': 'AllDebrid is fetching it · %d%%' % int(job.get('fetched') or 0), 'tone': 'plain'})
        else:
            drive.append({'title': title, 'sub': 'Waiting · AllDebrid has it ready' if status == 'copying' else 'Waiting for AllDebrid',
                          'tone': 'plain'})
    model = view.get('model')
    if model is not None:
        import work_state
        c=work_state.job(model,'conv')
        now_row=dict(c,sub=c['line'],percent='%d%%'%float(c.get('pct') or 0),tint=c['tint_now']) if c else None
        eligible={r['id'] for r in rows.get('waiting') or [] if r['state']=='waiting'}
        nexts=[j for j in model.get('next') or [] if j['id'] in eligible]
        out=[dict(j,sub=j['what']+' · '+size_text(j.get('size')), up='true' if n else '',
                  down='true' if n<len(nexts)-1 else '') for n,j in enumerate(nexts)]
        drive=[dict(j,sub=j['line']) for j in model.get('jobs') or [] if j['kind'] in ('copy','upload','down')]
    import work_state
    estimate=work_state.remaining_text(model)
    return {'now': now_row, 'line': out, 'held': held, 'drive': drive,
            'subtitle':'One at a time, top first'+(' · '+estimate if estimate else '')}


def _eta(seconds):
    try:
        import prepare_downloads
        return prepare_downloads.eta_text(seconds)
    except Exception:
        return ''


def debrid_jobs(state):
    """debrid_drive's jobs in their order, the one copying now carrying the live figures as '_current'."""
    jobs = [dict(j) for j in (state or {}).get('jobs') or []]
    current = (state or {}).get('current') or {}
    live = [j for j in jobs if j.get('status') not in ('done', 'failed')]
    if live and current.get('stage') == 'copying':
        live[0]['_current'] = current
    return jobs


def queue_properties(q):
    """Window properties for the Queue page (every slot set, empty when unused)."""
    props = {'now.title': '', 'now.sub': '', 'now.pct':'0', 'now.percent':'', 'now.tint':'FFBF5AF2', 'subtitle':q.get('subtitle','One at a time, top first')}
    if q['now']:
        props.update({'now.title': q['now']['title'], 'now.sub': q['now']['sub']})
    if q['now']:
        for k in ('pct','percent','tint'):props['now.'+k]=str(q['now'].get(k,''))
    for n in range(1, QUEUE_SLOTS + 1):
        r = q['line'][n - 1] if n <= len(q['line']) else {}
        for k in ('title', 'sub', 'up', 'down'):
            props['line.%d.%s' % (n, k)] = r.get(k, '')
    more = len(q['line']) - QUEUE_SLOTS
    props['line.more'] = ('and %d more below: move one up to see it' % more) if more > 0 else ''
    props['line.count'] = '%d video%s' % (len(q['line']), '' if len(q['line']) == 1 else 's') if q['line'] else ''
    for n in range(1, HELD_SLOTS + 1):
        r = q['held'][n - 1] if n <= len(q['held']) else {}
        props['held.%d.title' % n], props['held.%d.sub' % n] = r.get('title', ''), r.get('sub', '')
    for n in range(1, DRIVE_SLOTS + 1):
        r = q['drive'][n - 1] if n <= len(q['drive']) else {}
        props['drive.%d.title' % n], props['drive.%d.sub' % n] = r.get('title', ''), r.get('sub', '')
        props['drive.%d.tone' % n] = r.get('tone', '')
    props['empty'] = '' if (q['now'] or q['line'] or q['held'] or q['drive']) else 'Nothing is waiting to be converted.'
    return props


# --- History ----------------------------------------------------------------------------------------------------------
DAYS = (('today', 'Today'), ('yesterday', 'Yesterday'), ('week', '7 days'))
HISTORY_SLOTS = 12
RESULT = {'down': 'Downloaded', 'up': 'On Google Drive', 'conv': 'Ready for AirPlay'}


def midnight(now):
    t = time.localtime(now)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def _speed(value):
    value = float(value or 0)
    return '%d KB/s' % round(value / 1024) if 0 < value < MB else '%.1f MB/s' % (value / MB) if value else ''


def _took(seconds):
    m = int(max(0, seconds) // 60)
    return 'under a minute' if m < 1 else '%d min' % m if m < 60 else '%d h %d min' % (m // 60, m % 60)


def history_entries(finished, failures):
    """One list, newest first: finished jobs ('ok') and failures ('bad'). A conversion that stopped and a failure
    noted for the same video at that time are one entry (the failure, with how long it ran)."""
    out = []
    fails = [dict(f) for f in failures or ()]
    for f in finished or ():
        match = None
        for x in fails:
            if x.get('kind') == f.get('kind') and x.get('title') == f.get('title') and abs(float(x.get('time', 0)) - float(f.get('end', 0))) < 180:
                match = x
                break
        if match:
            fails.remove(match)
            out.append({'title': f['title'], 'kind': f['kind'], 'end': f['end'], 'tone': 'bad',
                        'result': match.get('reason') or 'Stopped', 'line': 'after %s' % _took(f['end'] - f['start']), 'size': 0})
            continue
        import transfer_history
        state = transfer_history.outcome(f)
        if state != 'done':
            # Ended part-way (Kodi closed, a video played): not "Ready" (build 174: two Inception restarts said so).
            how = ('at %d%%' % float(f['pct'])) if f.get('kind') == 'conv' and f.get('pct') is not None else (
                'at %s of %s' % (size_text(f.get('done')), size_text(f.get('total'))) if f.get('total') else '')
            out.append({'title': f['title'], 'kind': f['kind'], 'end': f['end'], 'tone': 'plain',
                        'result': ('Stopped %s' % how).strip() if state == 'stopped' else 'Ended',
                        'line': ' · '.join(x for x in (_took(f['end'] - f['start']), _speed(f.get('avg'))) if x), 'size': 0})
            continue
        line = ' · '.join(x for x in (size_text(f['size']) if f.get('size') else '', _took(f['end'] - f['start']),
                                      _speed(f.get('avg'))) if x)
        out.append({'title': f['title'], 'kind': f['kind'], 'end': f['end'], 'tone': 'ok', 'result': RESULT.get(f['kind'], 'Done'),
                    'line': line, 'size': float(f.get('size') or 0)})
    for x in fails:
        out.append({'title': x.get('title', ''), 'kind': x.get('kind', ''), 'end': float(x.get('time', 0)), 'tone': 'bad',
                    'result': x.get('reason') or 'Failed', 'line': '', 'size': 0})
    out.sort(key=lambda e: -e['end'])
    return out


def history_view(finished, failures, now, day='today'):
    """{'rows': entries of that day (or the last 7 days), 'total', 'count', 'busiest', 'failed'}."""
    today = midnight(now)
    entries = history_entries(finished, failures)
    week = [e for e in entries if e['end'] >= today - 6 * 86400]
    if day == 'today':
        rows = [e for e in entries if e['end'] >= today]
    elif day == 'yesterday':
        rows = [e for e in entries if today - 86400 <= e['end'] < today]
    else:
        rows = week
    per_day = {}
    for e in week:
        if e['tone'] == 'ok':
            per_day[midnight(e['end'])] = per_day.get(midnight(e['end']), 0) + e['size']
    busiest = ''
    if per_day and max(per_day.values()) > 0:
        when = max(per_day, key=per_day.get)
        busiest = 'Busiest: %s · %s' % ('today' if when == today else 'yesterday' if when == today - 86400 else time.strftime('%A', time.localtime(when)),
                                        size_text(per_day[when]))
    done = [e for e in week if e['tone'] == 'ok']
    rows.sort(key=lambda e:(e['tone']=='ok',-e['end']))
    return {'rows': rows, 'total': size_text(sum(e['size'] for e in done)), 'count': len(done),
            'failed': len([e for e in week if e['tone'] == 'bad']), 'busiest': busiest}


def history_properties(h, day):
    props = {'day': day, 'week.total': h['total'],
             'week.line': ' · '.join(x for x in ('%d finished' % h['count'], '%d failed' % h['failed'] if h['failed'] else '', h['busiest']) if x),
             'empty': '' if h['rows'] else {'today': 'Nothing finished today yet.', 'yesterday': 'Nothing finished yesterday.'}.get(day, 'Nothing in the last 7 days.')}
    props['unfinished']='true' if any(e['tone']!='ok' for e in h['rows']) else ''
    props['finished']='true' if any(e['tone']=='ok' for e in h['rows']) else ''
    for n in range(1, HISTORY_SLOTS + 1):
        e = h['rows'][n - 1] if n <= len(h['rows']) else {}
        props['h.%d.title' % n] = e.get('title', '')
        when = time.strftime('%a' if day == 'week' else '%H:%M', time.localtime(e['end'])) if e else ''
        props['h.%d.line' % n] = ' · '.join(x for x in (e.get('line', ''), when) if x)
        props['h.%d.when' % n] = when
        props['h.%d.section' % n] = 'finished' if e.get('tone')=='ok' else 'unfinished'
        props['h.%d.retry' % n] = 'true' if e.get('retry') else ''
        props['h.%d.result' % n] = ' · '.join(x for x in (e.get('result',''),e.get('line','') if e.get('tone')=='ok' else '') if x)
        props['h.%d.tone' % n] = e.get('tone', '')
    props['more'] = 'and %d more' % (len(h['rows']) - HISTORY_SLOTS) if len(h['rows']) > HISTORY_SLOTS else ''
    return props


# --- AirPlay check ----------------------------------------------------------------------------------------------------
AIRPLAY_FILE = 'airplay-last.json'
KEEP_LINES = 120
_LOCK = threading.Lock()
VIDEO_GET = re.compile(r'^(?:GET|HEAD) /(?:c?video)/\S+ (?:bytes=\S+ )?(\d{3}) ')
ANY_GET = re.compile(r'^(?:GET|HEAD) \S+ (?:bytes=\S+ )?(\d{3}) ')


AIRPLAY_NOTICES = ('Playing with AirPlay', "AirPlay couldn't play this", "AirPlay didn't start")


def airplay_notice(item):
    """Whether a Notifications message is about AirPlay (cast.send_airplay's notes): it opens the AirPlay check."""
    return str((item or {}).get('title', '')) in AIRPLAY_NOTICES


def airplay_location(profile):
    return os.path.join(str(profile), ADDON_DATA, AIRPLAY_FILE)


def load_airplay(profile):
    try:
        with open(airplay_location(profile), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_airplay(profile, data):
    path = airplay_location(profile)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(tmp, path)


def begin_airplay(profile, title, now=None):
    """A new Play on TV over AirPlay (cast.send_airplay, before the framework starts)."""
    with _LOCK:
        _save_airplay(profile, {'title': title or '', 'started': time.time() if now is None else now, 'lines': [],
                                'video': 0, 'requests': 0, 'refused': 0, 'begun': True})


def note_airplay(profile, lines, now=None):
    """Keep the session's KodiAirPlay lines (cast.send_airplay and airplay.relay hand over what they read). Segment
    requests are counted, not kept; a 'start:' line after the session's own start begins a new session."""
    lines = [str(x) for x in lines or () if x]
    if not lines:
        return
    with _LOCK:
        data = load_airplay(profile)
        now = time.time() if now is None else now
        for line in lines:
            if line.startswith('start:') and any(x.startswith('start:') for x in data.get('lines') or []):
                data = {'title': '', 'started': now, 'lines': [], 'video': 0, 'requests': 0, 'refused': 0}
            data.setdefault('started', now)
            data.setdefault('lines', [])
            m = ANY_GET.match(line)
            if m:
                data['requests'] = data.get('requests', 0) + 1
                ok = m.group(1) in ('200', '206')
                if VIDEO_GET.match(line) and ok:
                    data['video'] = data.get('video', 0) + 1
                if not ok:
                    data['refused'] = data.get('refused', 0) + 1
                    data['last_refused'] = line[:200]
                continue
            if line.startswith(('compat: segment', 'prefetch:', 'request:', 'seek:', 'subs: cue')):
                continue
            data['lines'].append(line[:300])
        del data['lines'][:-KEEP_LINES]
        data['updated'] = now
        _save_airplay(profile, data)


def _codec(master):
    m = re.search(r'CODECS="([^"]*)"', master or '')
    codecs = (m.group(1) if m else '').lower()
    video = ('HEVC' if re.search(r'\b(hvc1|hev1)', codecs) else 'H.264' if 'avc1' in codecs else
             'Dolby Vision' if re.search(r'\b(dvh1|dvhe)', codecs) else 'AV1' if 'av01' in codecs else '')
    r = re.search(r'RESOLUTION=(\d+)x(\d+)', master or '')
    res = ''
    if r:
        h = int(r.group(2))
        res = '4K' if h >= 2000 else '%dp' % h
    hdr = 'HDR' if re.search(r'VIDEO-RANGE=PQ|VIDEO-RANGE=HLG', master or '') else ''
    return ' '.join(x for x in (video, res, hdr) if x)


def airplay_steps(session, problem_words=None):
    """{'title', 'when', 'tone', 'steps': [(name, detail, tone ok|warn|bad)], 'try'} for the AirPlay check page, or
    None when there is no Play on TV yet. problem_words: cast.player_problem (a player line in everyday words)."""
    lines = (session or {}).get('lines') or []
    if not session or not (lines or session.get('begun')):
        return None
    has = lambda prefix: [x for x in lines if x.startswith(prefix)]
    steps = []
    clients = [x[len('client:'):].strip() for x in has('client:')]
    tvs = [c for c in clients if 'mfi_airplay_device' in c.lower() or '(apple tv' in c.lower() or 'appletv' in c.lower()]
    if any('(apple tv' in c.lower() or 'appletv' in c.lower() for c in tvs):
        steps.append(('The TV', 'An Apple TV', 'ok'))
    elif tvs:
        model = re.search(r'MFiModelGroup/([\w.\-]+)', tvs[0])
        steps.append(('The TV', 'A TV with AirPlay built in' + (' (%s)' % model.group(1) if model else ''), 'ok'))
    elif clients:
        steps.append(('The TV', "Only this iPhone's player connected: the TV never asked", 'bad'))
    else:
        steps.append(('The TV', 'No TV connected', 'bad'))
    master = (has('master:') or [''])[-1]
    what = _codec(master)
    converted = [x for x in lines if x.startswith('compat:') and ('gets the picture as H.264' in x or 'converting video stream' in x
                                                                  or 'converting it' in x)]
    if has('prepared:'):
        steps.append(('The picture', 'Sent as it is%s: this video is already prepared' % (' (%s)' % what if what else ''), 'ok'))
    elif converted:
        steps.append(('The picture', 'Converted to H.264%s (this TV needs it)' % (' from %s' % what if what else ''), 'ok'))
    elif master:
        steps.append(('The picture', 'Sent as it is' + (' (%s)' % what if what else ''), 'ok'))
    else:
        steps.append(('The picture', 'Not sent: the video never started on the phone', 'bad'))
    video, refused = int(session.get('video') or 0), int(session.get('refused') or 0)
    if video:
        steps.append(('The video', 'The TV asked for the video (%d part%s sent)' % (video, '' if video == 1 else 's'), 'ok'))
    elif refused:
        steps.append(('The video', 'The TV asked, but the phone could not send it', 'bad'))
    else:
        steps.append(('The video', 'The TV never asked for the video', 'bad' if session.get('requests') or master else 'warn'))
    player = has('player:')
    errors = [x for x in player if 'could not open' in x or 'stopped:' in x or 'failed:' in x]
    closed = [x for x in player if 'closed at' in x]
    if errors:
        why = (problem_words(errors) if problem_words else '') or errors[-1].split(':', 2)[-1].strip()[:120]
        steps.append(('How it ended', 'It stopped: %s' % why, 'bad'))
    elif any('external playback ended' in x for x in player):
        steps.append(('How it ended', 'AirPlay ended on the TV' + (' after %s' % _closed(closed[-1]) if closed else ''), 'ok'))
    elif closed:
        steps.append(('How it ended', 'Closed after %s' % _closed(closed[-1]), 'ok' if any('ready' in x for x in player) else 'warn'))
    elif any(x.strip() == 'player: ready' or 'ready' in x for x in player):
        steps.append(('How it ended', 'It played on the TV', 'ok'))
    else:
        steps.append(('How it ended', "Apple's player did not start", 'bad'))
    bad = [s for s in steps if s[2] == 'bad']
    tip = ''
    if bad:
        first = bad[0][0]
        tip = {'The TV': 'Make sure the TV is on and on the same Wi-Fi as the phone, then try Play on TV again.',
               'The picture': 'Play the video on the phone for a few seconds first, then Play on TV.',
               'The video': ('The TV connected but did not fetch the video. Keep Kodi open on the phone, or try Screen Mirroring: '
                             'swipe down from the top-right corner and tap Screen Mirroring.'),
               'How it ended': 'Try again. If it stops at the same point, Screen Mirroring still works: swipe down from the top-right corner.'}[first]
    started = float(session.get('started') or 0)
    return {'title': session.get('title') or 'Last Play on TV', 'when': started, 'tone': 'bad' if bad else 'ok', 'steps': steps,
            'try': tip}


def _closed(line):
    m = re.search(r'closed at ([\d.]+) s', line)
    if not m:
        return 'a while'
    s = float(m.group(1))
    return '%d s' % s if s < 60 else _took(s)


def airplay_properties(check, now):
    props = {'title': '', 'when': '', 'tone': '', 'try': '', 'headline': '', 'empty': 'No Play on TV yet. After one, this shows how it went.'}
    for n in range(1, 5):
        props['step.%d.name' % n] = props['step.%d.detail' % n] = props['step.%d.tone' % n] = ''
    if not check:
        return props
    m = int(max(0, now - check['when']) // 60) if check['when'] else None
    props.update(title=check['title'], tone=check['tone'], empty='',
                 when='' if m is None else 'just now' if m < 1 else '%d min ago' % m if m < 60 else
                 '%d h ago' % (m // 60) if m < 24 * 60 else time.strftime('%d %b, %H:%M', time.localtime(check['when'])),
                 **{'try': check['try']})
    props['headline'] = 'It worked' if check['tone'] == 'ok' else "It didn't work"
    for n, (name, detail, tone) in enumerate(check['steps'][:4], 1):
        props['step.%d.name' % n], props['step.%d.detail' % n], props['step.%d.tone' % n] = name, detail, tone
    return props
