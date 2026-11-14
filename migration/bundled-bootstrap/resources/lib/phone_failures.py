"""Terminal legacy phone uploads, mirrored into the shared Download problems records. Media is never removed here."""
import hashlib
import os
import time
from pathlib import Path


def profile_for(state_path):
    folder = Path(state_path).parent
    if folder.name == 'service.kodi.ios.bootstrap' and folder.parent.name == 'addon_data':
        return str(folder.parent.parent)
    return None  # Standalone upload tools may use an unrelated state file, not an app profile.


def retry_marker(profile, path):
    return (Path(profile) / 'addon_data/service.kodi.ios.bootstrap/phone-upload-retries' /
            hashlib.sha1(str(path).encode('utf-8')).hexdigest())


def request_retry(profile, path):
    """A separate request file avoids racing the uploader's in-memory state during a long HTTP request."""
    marker = retry_marker(profile, path)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def take_retry(profile, path):
    if profile is None:
        return False
    try:
        retry_marker(profile, path).unlink()
        return True
    except FileNotFoundError:
        return False


def remove_from_state(state, path):
    """Remove only synthetic phone failures, preserving concurrent real AllDebrid enqueues on save."""
    found = [j for j in state.get('jobs', []) if j.get('source') == 'phone' and j.get('phone_path') == str(path)]
    state.setdefault('removed', []).extend([[j['hash'], str(j.get('season', '')), str(j.get('episode', '')), j.get('added', 0)] for j in found])
    state['jobs'] = [j for j in state.get('jobs', []) if j not in found]
    return bool(found)


def clear_problem(profile, path):
    if profile is None:
        return
    import debrid_drive
    state = debrid_drive.load(profile)
    if remove_from_state(state, path):
        debrid_drive.save(profile, state)


def record(profile, path, fingerprint, reason, now=None, invalid_drive_id=''):
    if profile is None:
        return
    import debrid_drive
    import drivelibrary
    import diagnostics
    state = debrid_drive.load(profile)
    job = next((j for j in state.get('jobs', []) if j.get('source') == 'phone' and j.get('phone_path') == str(path)), None)
    name = os.path.basename(path)
    info = drivelibrary.parse(name)
    now = time.time() if now is None else now
    reason = diagnostics.redact(str(reason), 160)
    if job is None:
        job = {'hash': hashlib.sha1(('phone:' + str(path)).encode('utf-8')).hexdigest(),
               'added': now, 'files': [], 'source': 'phone', 'phone_path': str(path)}
        state['jobs'].append(job)
    episode = bool(info.get('season') and info.get('episode'))
    job.update(name=name, title=info.get('title') or name.rsplit('.', 1)[0], kind='episode' if episode else 'movie',
               season=str(info.get('season') or ''), episode=str(info.get('episode') or ''), year=str(info.get('year') or ''),
               status='failed', error=reason, terminal=True, terminal_reason=reason, finished=now, retry_at=0,
               phone_fp=list(fingerprint), size=int(fingerprint[2]))
    if invalid_drive_id:
        job['invalid_drive_id'] = invalid_drive_id
    debrid_drive.save(profile, state)
