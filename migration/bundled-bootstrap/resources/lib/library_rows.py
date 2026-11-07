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
         'todo': ('preparing', 'waiting', 'kept'), 'downloading': ('downloading',)}
TITLES = {'all': 'Library status', 'ready': 'Ready', 'waiting': 'Waiting', 'kept': 'Kept as it is', 'todo': 'To do',
          'downloading': 'Downloading'}
DOT = '[COLOR %s]●[/COLOR]'
NOTE = 'Kodi prepares one video at a time from Google Drive while nothing plays.'


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
    if filter_key == 'all':
        active = _positions([_video(r) for key in ('preparing', 'downloading') for r in rows[key]])
        folders = _positions([{'kind': 'folder', 'label': title, 'label2': _folder_line(key, rows[key]),
                               'props': {'kind': 'folder', 'folder': key, 'icon': glyph, 'tint': tint, 'count': str(len(rows[key]))}}
                              for key, title, glyph, tint in FOLDERS if rows[key]])
        out = active + folders
        if not out:
            out = [{'kind': 'foot', 'label': 'Nothing here yet. Check now (top right) to look at Google Drive › Kodi Downloads again.'}]
        else:
            out.append({'kind': 'foot', 'label': NOTE})
    else:
        out = _positions([_video(r) for key in SHOWN.get(filter_key, ()) for r in rows[key]])
        if not out:
            empty = {'ready': 'Nothing is ready yet.', 'todo': 'Nothing left to prepare.', 'waiting': 'Nothing is waiting.',
                     'kept': 'Nothing is kept as it is.', 'downloading': 'Nothing is downloading.'}.get(filter_key, 'Nothing here yet.')
            out = [{'kind': 'foot', 'label': empty}]
    for item in out:
        item.setdefault('props', {'kind': item['kind']})
        item['props'].setdefault('kind', item['kind'])
    return out


def page_properties(view, checking=False):
    """Window properties for the page's top: subtitle, ring, headline and legend."""
    legend = '  '.join('%s %d %s' % (DOT % colour, n, word) for colour, n, word in (
        ('FF30D158', view['ready'], 'ready'), ('FFBF5AF2', view['todo'], 'to do'),
        ('FF0A84FF', view['downloading'], 'downloading'), ('FF8E8E93', view['kept'], 'kept')))
    return {'sub': 'Kodi Downloads on Google Drive · ' + ('checking now…' if checking else view['checked']),
            'ring': ring_name(view['pct']), 'pct': str(view['pct']),
            'headline': '%d of %d ready' % (view['ready'], view['total']) if view['total'] else 'Not checked yet',
            'legend': legend}


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


def details(row, view):
    """One video's details sheet: title, status (tone ok|warn|plain), quality, up to 4 facts and up to 2 actions
    (label, request) where request is prepare_downloads.request's action, or None."""
    size = row.get('size') or 0
    on_drive = ('On Google Drive', '%.1f GB' % (size / GB)) if size else None
    folder = ('Folder', row.get('folder') or 'Kodi Downloads') if row.get('folder') else None
    state = row['state']
    sheet = {'title': row['title'], 'quality': '', 'facts': [], 'actions': [], 'tone': 'plain', 'status': row.get('sub', ''),
             'bar': '', 'bar_tint': ''}
    # Build 177 (owner-approved movie sheet): a live speed card for anything moving, and rows that each answer one
    # question. "On Google Drive" (the original's size) and "Speed: 1.8 GB read" are gone (owner: they "dont make sense").
    sheet['card'] = ''
    if state == 'ready':
        probe = row.get('probe') or {}
        took = (row['completed'] - row['started_at']) if row.get('completed') and row.get('started_at') else 0
        made = ' · '.join(x for x in (day_text(row.get('completed')), 'took %s' % minutes_text(took) if took > 0 else '') if x)
        sheet.update(status='Ready on iPhone and Apple TV', tone='ok', quality='Seeks straight away over AirPlay',
                     facts=[f for f in (('Picture', picture_text(probe, kept=False) or row.get('sub', '')),
                                        ('Size', '%.1f GB' % (size / GB)) if size else None,
                                        ('Folder', 'Kodi Downloads › ' + row['folder']) if row.get('folder') else None,
                                        ('Made ready', made) if made else None) if f],
                     actions=[('Play', 'play'), ('Play on TV', 'tv')])
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
    sheet['facts'] = sheet['facts'][:FACTS]
    return sheet


def card(history, kind, title, now):
    """The live speed card of a movie's sheet (build 177): window properties and the points to paint, from
    transfer_history's job of that kind when it is this movie's. ({}, []) when there is none yet ("Measuring…")."""
    import transfer_history as th
    job = (history.get('jobs') or {}).get(kind)
    if not job or job.get('title') != title or now - job.get('last', 0) > 15:
        return {'card.now': 'starting', 'card.peak': '–', 'card.avg': '–', 'card.left': '–', 'card.from': ''}, []
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
