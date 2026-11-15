"""C1 folded rows and N2 timed steps, separate from the notification store's add/load/filter routines."""
import json
import os
import tempfile
import threading
import time

_LOCK = threading.Lock()
COLOURS = {'copying': 'blue', 'problem': 'orange', 'retry': 'orange', 'ready': 'green', 'info': 'blue'}


def fold(items):
    """Exact kind/title/text matches only. Newest row keeps its action; all member IDs remain available."""
    groups, out = {}, []
    for item in sorted(items or [], key=lambda i: float(i.get('time') or 0), reverse=True):
        key = tuple(str(item.get(k) or '') for k in ('kind', 'title', 'text'))
        if key not in groups:
            row = dict(item, source_count=item.get('count'), count=0, ids=[], lines=3 if len(str(item.get('text') or '')) > 110 else 2)
            groups[key] = row
            out.append(row)
        row = groups[key]
        row['count'] += 1   # Stored count may mean episodes in a season, not repeated notices.
        if item.get('id'):
            row['ids'].append(item['id'])
        row['unread'] = row.get('unread', False) or not item.get('was_read', item.get('read', False))
    return out


def timeline(item, records=()):
    """At most three truthful timed steps. Explicit events first; logs are used only when supplied by the caller."""
    candidates = list((item or {}).get('timeline') or [])
    if not candidates:
        for record in records or []:
            if not record.get('time'):
                continue
            text = str(record.get('text') or record.get('message') or '').strip()
            if not text:
                continue
            kind = record.get('kind') or ('problem' if record.get('level') in ('error', 'warning') else 'info')
            candidates.append({'at': record['time'], 'kind': kind, 'text': text})
    unique, seen = [], set()
    for event in sorted(candidates, key=lambda e: float(e.get('at') or (e.get('time') if isinstance(e.get('time'), (int, float)) else 0) or 0)):
        at = float(event.get('at') or (event.get('time') if isinstance(event.get('time'), (int, float)) else 0) or 0)
        text = str(event.get('text') or '').strip()
        kind = event.get('kind') or 'info'
        signature = (at, kind, text)
        if not at or not text or signature in seen:
            continue
        seen.add(signature)
        unique.append({'at': at, 'time': time.strftime('%H:%M', time.localtime(at)), 'kind': kind,
                       'colour_kind': COLOURS.get(kind, 'blue'), 'text': text})
    return unique if len(unique) <= 3 else [unique[0]] + unique[-2:]


def path(profile):
    return os.path.join(str(profile), 'addon_data/service.kodi.ios.bootstrap/notice-steps.json')


def _load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def record_step(profile, job, kind, text, at=None):
    """Keep lifecycle evidence without changing stored notices. Concurrent lanes share one bounded season timeline."""
    import debrid_drive
    import diagnostics
    at = time.time() if at is None else float(at)
    group = str(job.get('batch') or 'video:' + debrid_drive.episode_label(job))
    text = diagnostics.redact(str(text))
    with _LOCK:
        store = _load(profile)
        row = store.setdefault(group, {'at': at, 'events': []})
        events = row['events']
        identity = '%s:%s:%s:%s' % (job.get('hash') or '', job.get('season') or '', job.get('episode') or '', job.get('timeline_file') or '')
        if kind == 'copying' and events and events[-1]['kind'] == 'copying' and at - events[-1]['at'] < 90:
            old = events[-1]
            identities = old.setdefault('identities', [])
            if identity not in identities:
                identities.append(identity)
                old['text'] = '%d episodes started copying' % len(identities)
        else:
            event = {'at': at, 'kind': kind, 'text': text}
            if kind == 'copying': event['identities'] = [identity]
            if not events or (events[-1]['kind'], events[-1]['text']) != (kind, text):
                events.append(event)
        row['at'] = at
        if len(events) > 3:
            row['events'] = events[:1] + events[-2:]
        store = dict(sorted(((k, v) for k, v in store.items() if at - v.get('at', 0) < 30 * 86400),
                            key=lambda kv: kv[1]['at'], reverse=True)[:200])
        target = path(profile)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=os.path.dirname(target), prefix='.notice-steps-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(store, handle)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)


def steps_for(profile, item):
    text = str(item.get('text') or '')
    import re
    video = text.split(': ', 1)[0] if ': ' in text else ''
    if not video:
        episode = re.match(r'^(.*? · S\d+ E\d+)(?: ·|$)', text)
        video = episode[1] if episode else text.split(' · ', 1)[0]
    group = str(item.get('group') or ('video:' + video if video else ''))
    return ((_load(profile).get(group) or {}).get('events')) or []
