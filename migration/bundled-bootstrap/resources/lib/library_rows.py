"""What Settings › Library › Library status shows (library_page.py draws it, library_status.py runs it).

Pure functions over prepare_downloads.library_view(): the list rows of each section, the page's summary text and one
video's details with what can be done about it. No Kodi imports, so it is tested on its own.
"""
GB = 1024 ** 3
SECTIONS = (('preparing', 'Preparing now'), ('downloading', 'Downloading'), ('waiting', 'Waiting'),
            ('ready', 'Ready for Kodi and AirPlay'), ('kept', 'Kept as it is'))
SHOWN = {'all': ('preparing', 'downloading', 'waiting', 'ready', 'kept'), 'ready': ('ready',),
         'todo': ('preparing', 'waiting', 'kept'), 'downloading': ('downloading',)}
READY_PREVIEW = 6     # "All" shows the first few ready videos and a "Show all N" row
DOT = '[COLOR %s]●[/COLOR]'


def ring_name(pct):
    """The ring texture for a percentage (activity_skin draws ring_00..ring_20)."""
    return 'ring_%02d.png' % max(0, min(20, int(round((pct or 0) / 5.0))))


def list_items(view, filter_key='all'):
    """[{kind: header|row|more|foot, label, label2, props}] for list 9300, in order."""
    out = []
    rows = view['rows']
    for key, title in SECTIONS:
        if key not in SHOWN.get(filter_key, SHOWN['all']) or not rows[key]:
            continue
        items = rows[key]
        count = len(items)
        right = {'waiting': '%d in line' % sum(1 for r in items if r['state'] == 'waiting')} \
            if key == 'waiting' and any(r['state'] == 'waiting' for r in items) else {}
        out.append({'kind': 'header', 'label': title, 'label2': right.get('waiting', str(count))})
        cut = items[:READY_PREVIEW] if key == 'ready' and filter_key == 'all' else items
        for n, r in enumerate(cut):
            pos = 'only' if len(cut) == 1 else 'first' if n == 0 else 'last' if n == len(cut) - 1 else 'mid'
            props = {'kind': 'row', 'state': r['state'], 'pos': pos, 'id': r['id'],
                     'pct': str(r.get('pct', '')), 'ring': ring_name(r.get('pct')), 'warn': 'true' if r.get('warn') else ''}
            out.append({'kind': 'row', 'label': r['title'], 'label2': r['sub'], 'props': props, 'row': r})
        if len(cut) < count:
            out.append({'kind': 'more', 'label': 'Show all %d' % count, 'props': {'kind': 'more', 'filter': 'ready'}})
    if not any(i['kind'] == 'row' for i in out):
        empty = {'ready': 'Nothing is ready yet.', 'todo': 'Nothing left to prepare.',
                 'downloading': 'Nothing is downloading.'}.get(filter_key, 'Nothing here yet.')
        out.append({'kind': 'foot', 'label': empty + ' Check now (top right) to look at Google Drive › Kodi Downloads again.'})
    else:
        out.append({'kind': 'foot', 'label': 'Kodi prepares one video at a time while nothing is playing, reading it from '
                                             'Google Drive. A video that needs more phone space than is free waits until there is room.'})
    for item in out:
        item.setdefault('props', {'kind': item['kind']})
        item['props'].setdefault('kind', item['kind'])
    return out


def page_properties(view, checking=False):
    """Window properties for the page's top: subtitle, ring, headline, legend and phone space."""
    free, working = view.get('free'), view.get('working') or 0
    legend = '  '.join('%s %d %s' % (DOT % colour, n, word) for colour, n, word in (
        ('FF30D158', view['ready'], 'ready'), ('FFBF5AF2', view['todo'], 'to do'),
        ('FF0A84FF', view['downloading'], 'downloading'), ('FF8E8E93', view['kept'], 'kept')))
    space = 'Kodi always leaves you 5 GB'
    if working >= 0.1 * GB:
        space = 'Preparing now uses %.0f GB · %s' % (working / GB, space)
    return {'sub': 'Kodi Downloads on Google Drive · ' + ('checking now…' if checking else view['checked']),
            'ring': ring_name(view['pct']), 'pct': str(view['pct']),
            'headline': '%d of %d ready' % (view['ready'], view['total']) if view['total'] else 'Not checked yet',
            'legend': legend, 'free': '' if free is None else '%.0f GB free' % (free / GB), 'space': space,
            'space_pct': '0' if not free else str(int(100 * working / (working + free)))}


def details(row, view):
    """One video's details sheet: title, status (tone ok|warn|plain), quality, up to 4 facts and up to 2 actions
    (label, request) where request is prepare_downloads.request's action, or None."""
    size = row.get('size') or 0
    on_drive = ('On Google Drive', '%.1f GB' % (size / GB)) if size else None
    folder = ('Folder', row.get('folder') or 'Kodi Downloads') if row.get('folder') else None
    state = row['state']
    sheet = {'title': row['title'], 'quality': '', 'facts': [], 'actions': [], 'tone': 'plain', 'status': row.get('sub', '')}
    if state == 'ready':
        sheet.update(status='Ready for Kodi and AirPlay', tone='ok', quality=row.get('sub', ''),
                     facts=[f for f in (on_drive, folder, ('Plays', 'on this iPhone and over AirPlay, seeking straight away')) if f])
    elif state == 'preparing':
        sheet.update(status='Preparing now · %s%%' % row.get('pct', 0), facts=[f for f in (on_drive, ('Step', row.get('sub', ''))) if f])
    elif state in ('downloading', 'uploading'):
        sheet.update(status=row.get('sub', ''), facts=[('Progress', '%s%%' % row.get('pct', 0))])
    elif state == 'waiting':
        sheet.update(status=row.get('sub', '').split(' · ')[0], quality=' · '.join(row.get('sub', '').split(' · ')[1:]),
                     facts=[f for f in (on_drive, folder) if f],
                     actions=[('Prepare next', 'next'), ('Keep as it is', 'keep')])
    elif state == 'space':
        free = view.get('free') or 0
        sheet.update(status='Waiting for phone space', tone='warn',
                     facts=[f for f in (on_drive, ('Needs free', '%.0f GB, incl. 5 GB kept for you' % (row.get('needs', 0) / GB)),
                                        ('Free now', '%.0f GB' % (free / GB))) if f],
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
    sheet['facts'] = sheet['facts'][:4]
    return sheet
