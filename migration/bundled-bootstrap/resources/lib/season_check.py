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
    return props
