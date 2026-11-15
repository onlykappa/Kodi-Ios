"""Download problems › "Don't Show Again" (owner, 2026-11-14: "needs to be a way to permanently override these errors …
clears it for good and only will show up if there is a different issue … make it like that for all problems because
some are not actually problems").

ignored-problems.json in the add-on's data folder: {problem key: signature}. A problem is hidden while its key is there
with the same signature; when the same download or video fails in another way (a different reason), it shows again.
Keys are the page's own (debrid_drive.problem_key for copies, 'prep:<Drive id>' for preparation). Pure apart from the
JSON file, so it is host-tested.
"""
import json
import os
import re

FILE = 'ignored-problems.json'


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.replace(tmp, target)


def signature(problem):
    """What went wrong, without the parts that change on their own (numbers such as attempts, sizes and times)."""
    text = str(problem.get('error') or problem.get('reason') or problem.get('kind') or '').lower()
    text = re.sub(r'\d+', '#', text)
    return '%s|%s' % (problem.get('kind') or '', ' '.join(text.split())[:160])


def ignore(profile, problem):
    data = load(profile)
    data[str(problem['key'])] = signature(problem)
    save(profile, data)


def hidden(profile, problem, data=None):
    data = load(profile) if data is None else data
    return data.get(str(problem.get('key'))) == signature(problem)


def visible(profile, found):
    """The problems that still show: not ignored, or ignored for a different reason."""
    data = load(profile)
    return [p for p in found if not hidden(profile, p, data)]


def hidden_prep_ids(profile, state):
    """Drive ids of preparation problems the owner chose not to see again (for Library status' "can't be made ready")."""
    import prepare_downloads
    data = load(profile)
    out = set()
    for p in prepare_downloads.preparation_problems(state):
        if data.get('prep:' + str(p['id'])) == signature({'kind': 'prepare', 'error': p['error']}):
            out.add(str(p['id']))
    return out
