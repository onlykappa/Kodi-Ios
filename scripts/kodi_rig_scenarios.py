"""Status scenarios for the desktop Kodi rig (scripts/kodi_rig.py): the states the approved boards show
(docs/design/library-status-mockups-r1.html), written into a rig profile with the app's own writers.

Synthetic data only (film names, sizes, speeds); never an account, token or Drive ID. The rig does not start the
bootstrap service, so nothing overwrites these files; `run` keeps work-state.json fresh (older than 6 s reads as stale).

usage: kodi_rig_scenarios.py PROFILE SCENARIO [seconds]
scenarios: running, airplay, paused, network, queued, idle, stale, long
"""
import json
import math
import os
import sys
import time
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True
import debrid_drive  # noqa: E402
import prepare_downloads  # noqa: E402
import transfer_history  # noqa: E402
import work_state  # noqa: E402

SCENARIOS = ('running', 'airplay', 'paused', 'network', 'queued', 'idle', 'stale', 'long')
GB = 1024 ** 3
MB = 1024 ** 2
LONG_TITLE = 'A.Very.Long.Movie.Title.That.Goes.On.And.On.Past.Sixty.Characters.2026.1080p.mkv'


def item(i, name, state, size_gb, folder='Movies'):
    return {'id': 'id%d' % i, 'name': name, 'folder': folder, 'size': int(size_gb * GB), 'state': state,
            'md5Checksum': 'x%d' % i}


def library(extra_title=None):
    names = [('Interstellar.2014.2160p.mkv', 'ready', 52), ('Fall.2.Deadpoint.2026.2160p.mkv', 'ready', 16.9),
             ('Arrival.2016.1080p.mkv', 'ready', 9), ('Dune.Part.Two.2024.2160p.mkv', 'ready', 31),
             ('Oppenheimer.2023.2160p.mkv', 'ready', 44), ('Tenet.2020.1080p.mkv', 'ready', 12),
             ('Heat.1995.1080p.mkv', 'ready', 11), ('Sicario.2015.1080p.mkv', 'ready', 10),
             ('Scary.Movie.2026.1080p.mkv', 'todo', 4.3), ('Lanterns.S01E01.2160p.mkv', 'todo', 2.8),
             ('Inception.2010.2160p.mkv', 'todo', 22)]
    if extra_title:
        names.append((extra_title, 'todo', 3.1))
    return [item(i, n, s, g, 'TV Shows' if 'S01' in n else 'Movies') for i, (n, s, g) in enumerate(names)]


def prep_state(now, current_name, kind, pct, rate, eta, items, kept=('Inception.2010.2160p.mkv',),
               repack=('Fall.2.Deadpoint.2026.2160p.mkv',)):
    jobs = {}
    for e in items:
        if e['name'] == current_name:
            jobs['s-' + e['id']] = {'source': e, 'status': 'running', 'attempts': 0, 'retry_after': 0, 'repack': kind == 'repack'}
        elif e['name'] in kept:
            jobs['s-' + e['id']] = {'source': e, 'status': 'waiting', 'kept': True, 'attempts': 0, 'retry_after': 0,
                                    'error': 'Being replaced by the new download above'}
        elif e['name'] in repack:
            jobs['s-' + e['id']] = {'source': e, 'status': 'waiting', 'repack': True, 'attempts': 0, 'retry_after': 0}
        elif e['state'] == 'todo':
            jobs['s-' + e['id']] = {'source': e, 'status': 'waiting', 'attempts': 0, 'retry_after': 0}
    current = {}
    if current_name:
        current = {'title': current_name, 'running': True, 'updated': now, 'progress': pct, 'rate': rate, 'eta_s': eta,
                   'kind': kind, 'stage': 'Step 3 of 3 · ' + ('Making it start faster' if kind == 'repack' else 'Converting')}
    return {'jobs': jobs, 'sessions': {}, 'last_scan': now - 30, 'current': current,
            'library': {'items': items, 'checked': now - 30}}


def debrid_state(now, copying):
    if not copying:
        return {'jobs': []}
    job = {'hash': 'a' * 40, 'name': 'Inception.2010.2160p.REMUX', 'title': 'Inception (2010)', 'kind': 'movie',
           'status': 'copying', 'files': [], 'added': now - 600}
    return {'jobs': [job], 'current': {'name': 'Inception.2010.2160p.REMUX', 'folder': 'Inception (2010)', 'sent': 0.38 * 22 * GB,
                                      'total': 22 * GB, 'stage': 'copying', 'rate': 2.4 * MB, 'eta_s': 540, 'updated': now}}


def history(now, conv_title, conv_rate, copy=False):
    """Finished jobs end inside today (History's Today tab) and five minutes of graph samples."""
    data = {'jobs': {}, 'finished': [
        {'kind': 'conv', 'title': 'Interstellar (2014)', 'start': now - 1500, 'end': now - 420, 'peak': 9 * MB, 'avg': 6 * MB,
         'done': 52 * GB, 'total': 52 * GB, 'pct': 100, 'size': 52 * GB},
        {'kind': 'down', 'title': 'Lanterns · S1 E2', 'start': now - 1700, 'end': now - 900, 'peak': 5 * MB, 'avg': 3 * MB,
         'done': 2.6 * GB, 'total': 2.6 * GB, 'size': 2.6 * GB}]}
    for k in range(300, 0, -2):
        act = {}
        if conv_title:
            act['conv'] = {'title': conv_title, 'rate': conv_rate * (0.85 + 0.15 * math.sin(k / 23.0) + (0.05 if k < 60 else 0)),
                           'done': 0, 'total': 0, 'pct': 42}
        if copy:
            act['up'] = {'title': 'Inception (2010)', 'rate': 2.4 * MB * (0.9 + 0.1 * math.cos(k / 17.0)), 'done': 0, 'total': 0}
        transfer_history.track(data, now - k, act)
    return data


def failures(profile, now):
    path = transfer_history.failures_location(profile)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump([{'kind': 'up', 'title': 'Inception (2010)', 'reason': 'AllDebrid was busy and did not answer properly',
                    'time': now - 240}], f)


def scenario(name, now):
    if name not in SCENARIOS:
        raise SystemExit('unknown scenario %r; one of %s' % (name, ', '.join(SCENARIOS)))
    items = library(LONG_TITLE if name == 'long' else None)
    slow, needs, network, paused, copying = '', [], [], {}, False
    cur, kind, pct, rate, eta = 'Lanterns.S01E01.2160p.mkv', 'repack', 42, 4.8 * MB, 360
    if name == 'long':
        cur, kind = items[-1]['name'], 'conv'
    if name == 'airplay':
        slow, copying = 'airplay', True
        needs = [dict(work_state.NEEDS_TEXT['drive_signin'], key='drive_signin')]
        cur, kind, pct, rate, eta = 'Scary.Movie.2026.1080p.mkv', 'conv', 18, 1.1 * MB, 1500
    if name == 'paused':
        paused = {'conv': True}
    if name == 'network':
        cur = None
        network = [{'key': 'drive', 'until': now + 60, 'why': 'Waiting for the network'}]
    if name in ('queued', 'idle', 'stale'):
        cur = None
    if name == 'idle':
        items = [dict(e, state='ready') for e in items]
    prep = prep_state(now, cur, kind, pct, rate, eta, items)
    if name == 'idle':
        prep['jobs'] = {}
    if name == 'paused':
        prep['current']['paused'] = True
    debrid = debrid_state(now, copying)
    built = work_state.build({'prep': prep, 'runtime': {}, 'debrid': debrid, 'phone': [], 'torrents': [], 'paused': paused,
                              'slow': slow, 'needs': needs, 'network': network}, now if name != 'stale' else now - 60)
    return prep, debrid, history(now, work_state._title(cur) if cur else '', rate, copying), built


def write(profile, name):
    now = time.time()
    prep, debrid, hist, built = scenario(name, now)
    prepare_downloads.save(profile, prep)
    debrid_drive.save(profile, debrid)
    transfer_history.save(profile, hist)
    work_state.save(profile, built)
    return built


def run(profile, name, seconds=0.0):
    """Write the scenario once, then every second for `seconds`. Returns the last model's mode and bell properties."""
    failures(profile, time.time())
    end = time.time() + seconds
    while True:
        built = write(profile, name)
        if time.time() >= end:
            return {'mode': built['mode'], 'headline': built['headline'], 'bell': work_state.bell_properties(built)}
        time.sleep(1)


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0)))
