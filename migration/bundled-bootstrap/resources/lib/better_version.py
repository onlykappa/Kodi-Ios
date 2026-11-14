"""DEC-047 board D, "Better Version": episodes on Google Drive are looked up again at the show's quality, and each one's old
file goes to Drive's Trash once its new copy is saved.

better-versions.json in the add-on's data folder: {'tmdb:season:episode': {'old': Drive id, 'name': file name, 'at': time}}.
- remember() is called by Library › Select before Repair looks the episodes up again;
- replacing(job) lets that episode's new download through the copier's "already on Drive" check (debrid_drive.drop_on_drive,
  build 325), which otherwise drops a waiting episode that is on Drive;
- finished(job) runs when a copy is saved: a different file for that episode sends the old one to the Trash (restorable for
  30 days) and takes it out of the preparation queue. A copy refused for being lower than the chosen quality (ISSUE-236)
  never reaches this, so the old file stays. Entries older than DAYS are forgotten.
Pure apart from the JSON file; trash and forget are passed in, so it is host-tested.
"""
import json
import os
import time

FILE = 'better-versions.json'
DAYS = 7


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile, now=None):
    now = time.time() if now is None else now
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict) and now - float(v.get('at') or 0) < DAYS * 86400}


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.replace(tmp, target)


def key(tmdb, season, episode):
    return '%s:%d:%d' % (tmdb, int(season), int(episode))


def remember(profile, entries, now=None):
    """entries: [(tmdb, season, episode, old Drive id, name)]."""
    now = time.time() if now is None else now
    data = load(profile, now)
    for tmdb, season, episode, old, name in entries:
        if tmdb and old:
            data[key(tmdb, season, episode)] = {'old': str(old), 'name': str(name or ''), 'at': now}
    save(profile, data)
    return len(entries)


def _job_key(job):
    try:
        return key(job.get('show_tmdb') or '', int(job.get('season') or 0), int(job.get('episode') or 0))
    except (TypeError, ValueError):
        return ''


def replacing(profile, job):
    """True for an episode download that replaces a file on Drive (it must not be dropped as 'already on Drive')."""
    k = _job_key(job)
    return bool(k and job.get('show_tmdb') and k in load(profile))


def finished(profile, job, trash, forget=lambda ids: None, log=lambda text: None):
    """A copy was saved: if it replaces an episode, the old file goes to the Trash. Returns the ids sent to the Trash."""
    data = load(profile)
    k = _job_key(job)
    entry = data.get(k) if k else None
    if not entry:
        return []
    new = {str(f.get('drive_id')) for f in job.get('files') or [] if f.get('drive_id')}
    if not new or entry['old'] in new:
        return []
    try:
        trash(entry['old'])
    except Exception as error:   # tried again after the next copy; the new file is already there
        log('better version: the old file was not sent to the Trash (%s)' % error)
        return []
    data.pop(k, None)
    save(profile, data)
    try:
        forget([entry['old']])
    except Exception:
        pass
    log('better version: %s replaced; the old file is in Google Drive\'s Trash' % (entry.get('name') or k))
    return [entry['old']]
