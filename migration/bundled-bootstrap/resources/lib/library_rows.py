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


def usage_text(usage):
    """'Kodi uses 9.8 GB · Elementum downloads 6.1 GB · artwork 1.2 GB' from {name: bytes} (largest two named)."""
    total = sum(usage.values())
    big = [(n, b) for n, b in sorted(usage.items(), key=lambda kv: -kv[1]) if b >= 0.1 * GB][:2]
    return ' · '.join(['Kodi uses %.1f GB' % (total / GB)] + ['%s %.1f GB' % (n, b / GB) for n, b in big])


def page_properties(view, checking=False, usage=None):
    """Window properties for the page's top: subtitle, ring, headline, legend and phone space. usage: {what: bytes}
    Kodi keeps on the phone (library_status measures it), or None while it is being measured."""
    free, working = view.get('free'), view.get('working') or 0
    legend = '  '.join('%s %d %s' % (DOT % colour, n, word) for colour, n, word in (
        ('FF30D158', view['ready'], 'ready'), ('FFBF5AF2', view['todo'], 'to do'),
        ('FF0A84FF', view['downloading'], 'downloading'), ('FF8E8E93', view['kept'], 'kept')))
    space = 'Kodi always leaves you 5 GB'
    if working >= 0.1 * GB:
        space = 'Preparing now uses %.0f GB · %s' % (working / GB, space)
    props = {'sub': 'Kodi Downloads on Google Drive · ' + ('checking now…' if checking else view['checked']),
            'ring': ring_name(view['pct']), 'pct': str(view['pct']),
            'headline': '%d of %d ready' % (view['ready'], view['total']) if view['total'] else 'Not checked yet',
            'legend': legend, 'free': '' if free is None else '%.0f GB free' % (free / GB), 'space': space,
            'space_pct': '0' if not free else str(int(100 * working / (working + free)))}
    if usage:
        used = sum(usage.values())
        props['space'] = usage_text(usage)
        props['space_pct'] = '0' if not free else str(int(100 * used / (used + free)))
    return props


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
        # Owner (build 170): "the details are blank and seem ugly": what it is doing, how fast and how long.
        pct = row.get('pct', 0)
        sheet.update(status='Preparing now' + (' · %s%%' % pct if pct and not row.get('indeterminate') else ''),
                     quality=row.get('video', ''),
                     facts=[f for f in (('Step', row.get('step') or row.get('sub', '')),
                                        ('Speed', row.get('speed') or 'starting'),
                                        ('Time left', row.get('eta') or 'working it out'),
                                        on_drive) if f])
    elif state in ('downloading', 'uploading'):
        sent, total, rate = row.get('sent') or 0, row.get('total') or 0, row.get('rate') or 0
        sheet.update(status=('AllDebrid is fetching it' if row.get('stage') == 'fetching' else
                             'Uploading to Google Drive' if state == 'uploading' else 'Downloading'),
                     facts=[f for f in (('Progress', '%s%%' % row.get('pct', 0) + (' · %.1f of %.1f GB' % (sent / GB, total / GB) if total else '')),
                                        ('Speed', '%.1f MB/s' % (rate / 1024 ** 2) if rate else 'measuring'),
                                        ('Time left', row.get('eta') or 'working it out'),
                                        ('Saving to', 'Google Drive › Kodi Downloads' + (' › ' + row['folder'] if row.get('folder') else ''))) if f])
    elif state == 'waiting':
        sheet.update(status=row.get('sub', '').split(' · ')[0], quality=' · '.join(row.get('sub', '').split(' · ')[1:]),
                     facts=[f for f in (on_drive, folder) if f],
                     actions=[('Prepare next', 'next'), ('Keep as it is', 'keep')])
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
    sheet['facts'] = sheet['facts'][:4]
    return sheet
