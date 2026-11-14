"""Live, exact season-quality coverage. A scan of one episode checks every offered quality."""
import threading

QUALITIES = ('4k', '1080p', '720p')
LABELS = {'4k': '4K', '1080p': '1080p', '720p': '720p'}


class Survey:
    def __init__(self, episodes):
        self.episodes = tuple(dict.fromkeys(episodes))
        self.answers, self.completed = {}, set()
        self.lock = threading.Lock()

    def record(self, episode, answer):
        valid = isinstance(answer, dict) and isinstance(answer.get('qualities'), (list, tuple)) and not answer.get('error')
        with self.lock:
            self.completed.add(episode)
            if valid:
                self.answers[episode] = answer
        return valid

    def model(self):
        with self.lock:
            answers, completed = dict(self.answers), set(self.completed)
        total = len(self.episodes)
        pending = total - len(completed)
        unknown = len(completed - answers.keys())
        return {'total': total, 'completed': len(completed), 'pending': pending, 'unknown': unknown,
                'checking_qualities': list(QUALITIES) if pending else [],
                'qualities': [{'key': q, 'label': LABELS[q],
                               'found': sum(q in (answer.get('qualities') or []) for answer in answers.values()),
                               'total': total, 'checked': len(answers), 'pending': pending, 'unknown': unknown,
                               'state': 'checking' if pending else 'incomplete' if unknown else 'done'} for q in QUALITIES]}


def properties(model):
    """String window properties; the nested model is also available to Python callers."""
    props = {'check.total': str(model['total']), 'check.completed': str(model['completed']),
             'check.pending': str(model['pending']), 'check.unknown': str(model['unknown']),
             'check.checking_qualities': ','.join(model['checking_qualities'])}
    for n, row in enumerate(model['qualities'], 1):
        prefix = 'check.quality.%d.' % n
        props.update({prefix + k: str(row[k]) for k in ('key', 'label', 'found', 'total', 'checked', 'pending', 'unknown', 'state')})
        props[prefix + 'text'] = '%d of %d episodes found' % (row['found'], row['total'])
        props['check.q.%d' % n] = '%s · %s%s' % (row['label'], props[prefix + 'text'],
                                                ' · checking' if row['state'] == 'checking' else '')
    props.update(chips(model))
    return props


CHIPS = 3


def chips(model):
    """Q2 (owner-approved, docs/design/build442-mockups.html): found qualities as chips, in quality order. Green
    ('whole') when every episode has it, orange ('part') otherwise; 'check.looking' says what is still being checked,
    and nothing names sample episodes (owner, build 442: "always says looking at episodes 1, 6 and 10")."""
    rows = model['qualities']
    found = [r for r in rows if r['found'] > 0]
    out = {}
    for n in range(1, CHIPS + 1):
        r = found[n - 1] if n <= len(found) else None
        whole = bool(r) and r['found'] >= r['total']
        out['check.chip.%d.text' % n] = '' if not r else '%s · %s' % (r['label'], 'all %d' % r['total'] if whole else '%d of %d' % (r['found'], r['total']))
        out['check.chip.%d.whole' % n] = 'true' if whole else ''
        out['check.chip.%d.part' % n] = 'true' if r and not whole else ''
    pending = model['pending'] > 0
    missing = [r['label'] for r in rows if r['found'] < r['total']]
    none = [r['label'] for r in rows if r['found'] == 0]
    out['check.found'] = 'Found so far:' if found else ''
    out['check.intro'] = '' if found else ('Looking through the sources for whole-season and single-episode versions. '
                                           'This takes about half a minute.')
    if pending:
        out['check.looking'] = 'Still looking \u00b7 %s' % ', '.join(missing) if missing else 'Still looking'
    elif none:
        out['check.looking'] = 'None found \u00b7 %s' % ', '.join(none)
    else:
        out['check.looking'] = ''
    out['check.busy'] = 'true' if pending else ''
    return out
