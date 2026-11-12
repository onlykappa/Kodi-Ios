"""AI Upscale measurement build (DEC-039: "measure before you build the full feature").

One prepared 720p/1080p video on Google Drive is upscaled with the real engine (KodiAirPlay r48) and the result is
counted, not uploaded: nothing on Drive changes. kodi.log gets one line per minute while it runs and one summary:
time per minute of video, frames per second, speed against real time, heat (iOS thermal state), battery used,
charging, and the copy's size (measured, and estimated for the whole video when only a part was made).

Started from Settings › Google Drive › "AI Upscale test" (upscale_test.py writes the request); the preparation
queue's thread runs it between videos, so it never runs beside another conversion (one AI engine at a time).
"""
import json
import os
import time

import driveupload
import picture

REQUEST = 'upscale-measure.json'
RESULTS = 'upscale-measure-results.json'
ENGINES = {'auto': 0, 'lanczos': 1, 'ai-video': 2, 'ai-image': 3, 'ai-fast': 4}
MODEL_WAIT = 15 * 60


def folder(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')


def request(profile, item, size='4K UHD', engines=('auto',), minutes=0, now=time.time):
    """Asks the queue to measure `item` (a Drive file dict with id and name)."""
    engines = [e for e in engines if e in ENGINES] or ['auto']
    if size not in picture.LABELS:
        raise ValueError('unknown size %r' % (size,))
    data = {'id': str(item['id']), 'name': str(item.get('name', '')), 'size': size, 'engines': engines,
            'minutes': max(0, float(minutes or 0)), 'requested': now()}
    os.makedirs(folder(profile), exist_ok=True)
    temp = os.path.join(folder(profile), REQUEST + '.tmp')
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.replace(temp, os.path.join(folder(profile), REQUEST))
    return data


def pending(profile):
    try:
        with open(os.path.join(folder(profile), REQUEST), encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) and data.get('id') else None
    except (OSError, ValueError):
        return None


def clear(profile):
    try:
        os.remove(os.path.join(folder(profile), REQUEST))
    except OSError:
        pass


class Counter:
    """A sink for convert_to that keeps nothing: it counts the bytes each track would put on Drive."""

    def __init__(self):
        self.bytes = {}
        self.sent = 0

    def write(self, track, suffix, data):
        self.bytes[track] = self.bytes.get(track, 0) + len(data)
        self.sent += len(data)


def _mb(n):
    return n / 1048576.0


def candidates(state):
    """Prepared 720p/1080p (and smaller) SDR videos the queue knows, newest first: what the test can use."""
    found = []
    for job in (state or {}).get('jobs', {}).values():
        probe = job.get('probe') or {}
        if job.get('status') != 'done' or probe.get('hdr'):
            continue
        width, height = int(probe.get('width') or 0), int(probe.get('height') or 0)
        if not width or not picture.above(width, height):
            continue
        source = job.get('source') or {}
        item_id = job.get('prepared_id') or source.get('id')
        if item_id:
            found.append({'id': item_id, 'name': source.get('name', ''), 'width': width, 'height': height,
                          'duration': float(probe.get('duration') or 0), 'completed': job.get('completed', 0)})
    found.sort(key=lambda row: -row['completed'])
    return found


def run(q, req, log, notify=lambda *args: None, clock=time.time, sleep=time.sleep, keep_going=lambda: True):
    """Measures one request with the queue's native library and Drive stream. Returns the results dict."""
    native = q.native
    name = req.get('name') or req['id']
    title = name
    try:
        import drivelibrary
        title = drivelibrary.display_title(name)
    except Exception:
        pass
    if not getattr(native, 'upscales', False):
        raise RuntimeError('This build has no AI upscaler (KodiAirPlay r48 or later is needed)')
    source = q.stream.url(req['id'])
    try:
        return _run(q, req, log, notify, clock, sleep, keep_going, native, title, name, source)
    finally:
        q.stream.forget(req['id'])   # the Drive read-ahead for this file is let go, as the queue does


def _run(q, req, log, notify, clock, sleep, keep_going, native, title, name, source):
    probe = native.probe(source)
    width, height = int(probe.get('width') or 0), int(probe.get('height') or 0)
    duration, fps = float(probe.get('duration') or 0), float(probe.get('fps') or 0)
    label = req.get('size') or '4K UHD'
    size = picture.fitted(width, height, label)
    log('upscale measurement: %s — %dx%d %s, %.1f fps, %.0f min, HDR=%s, audio tracks %s, subtitle tracks %s; target %s %s' % (
        title, width, height, probe.get('codec'), fps, duration / 60, probe.get('hdr'), probe.get('audio_tracks'),
        probe.get('subtitle_tracks'), label, '%dx%d' % size if size else '(already this size)'))
    results = {'name': name, 'source': {k: probe.get(k) for k in ('width', 'height', 'codec', 'bit_depth', 'fps', 'duration', 'hdr')},
               'target': label, 'runs': [], 'started': clock()}
    if not size or probe.get('hdr'):
        results['error'] = 'HDR video is kept as it is' if probe.get('hdr') else 'The video is already this size'
        log('upscale measurement: %s' % results['error'])
        return results
    support = native.upscale_support(width, height, label)
    log('upscale measurement: this iPhone: %s' % json.dumps(support, sort_keys=True))
    results['support'] = support
    for engine_name in req.get('engines') or ['auto']:
        engine = ENGINES.get(engine_name, 0)
        if engine != ENGINES['lanczos']:
            status = native.upscale_model(width, height, label, engine)
            if status == 0:
                log('upscale measurement: downloading the AI model (%s)' % engine_name)
                native.upscale_model(width, height, label, engine, start=True)
            waited = clock()
            while status in (0, 1) and clock() - waited < MODEL_WAIT and keep_going():
                sleep(5)
                status = native.upscale_model(width, height, label, engine)
            log('upscale measurement: model %s after %.0f s' % ({2: 'ready', 1: 'still downloading', 0: 'not downloaded', -1: 'not available for this size'}.get(status, status), clock() - waited))
            if status != 2:
                results['runs'].append({'engine': engine_name, 'error': 'model not ready (%s)' % status})
                continue
        results['runs'].append(measure(native, source, size, label, engine, engine_name, duration, fps, req, log, clock, keep_going))
    results['finished'] = clock()
    try:
        os.makedirs(folder(q.profile), exist_ok=True)
        with open(os.path.join(folder(q.profile), RESULTS), 'w', encoding='utf-8') as handle:
            json.dump(results, handle, indent=1)
    except OSError as error:
        log('upscale measurement: results not saved: %s' % error)
    done = [r for r in results['runs'] if not r.get('error')]
    if done:
        best = done[0]
        notify('info', 'AI Upscale test finished', '%s: %.1f min per minute of video, %.1f fps, %s, about %.1f GB for the whole video' % (
            title, best['minutes_per_minute'], best['fps'], best['thermal_peak'], best['estimated_bytes'] / 1e9))
    else:
        notify('problem', 'AI Upscale test stopped', '%s: %s' % (title, (results['runs'] or [{}])[0].get('error') or results.get('error') or 'no result'))
    return results


def measure(native, source, size, label, engine, engine_name, duration, fps, req, log, clock, keep_going):
    bw, bh = picture.box(label)
    counter = Counter()
    limit = float(req.get('minutes') or 0) * 60
    state = {'film': 0.0, 'fraction': 0.0, 'last_log': clock(), 'thermal': [], 'battery': [], 'charging': set(), 'stopped': False}
    began = clock()
    first = native.device_state()

    def sample():
        device = native.device_state()
        state['thermal'].append(int(device.get('thermal_id', -1)))
        if float(device.get('battery', -1)) >= 0:
            state['battery'].append(float(device['battery']))
        state['charging'].add(int(device.get('charging', -1)))
        return device

    def going():
        if not keep_going():
            return False
        if limit and state['film'] >= limit:
            state['stopped'] = True
            return False
        return True

    def progress(stage, n, t):
        if stage in (0, 2) and t:
            state['fraction'] = max(state['fraction'], min(1.0, float(n) / t))
            state['film'] = state['fraction'] * duration
        now = clock()
        if now - state['last_log'] >= 60:
            state['last_log'] = now
            device = sample()
            wall = now - began
            log('upscale measurement: %s %.1f of %.1f min of video in %.1f min (%.2fx real time), %.1f MB so far, thermal %s, battery %s, charging %s' % (
                engine_name, state['film'] / 60, duration / 60, wall / 60, state['film'] / wall if wall else 0, _mb(counter.sent),
                device.get('thermal'), device.get('battery'), device.get('charging')))

    sample()
    error = ''
    try:
        native.convert_to(source, counter, going, progress, upscale=(bw, bh, engine, int(req.get('kbps') or 0)))
    except driveupload.Stop:
        if not state['stopped']:
            error = 'stopped before the end'
    except Exception as problem:
        error = str(problem)[:240]
    wall = max(0.001, clock() - began)
    last = sample()
    film = duration if not error and not state['stopped'] else state['film']
    fraction = film / duration if duration else 0
    run = {'engine': engine_name, 'size': '%dx%d' % size, 'film_seconds': round(film, 1), 'wall_seconds': round(wall, 1),
           'minutes_per_minute': round((wall / 60) / (film / 60), 2) if film else 0,
           'speed': round(film / wall, 3), 'fps': round(film * fps / wall, 2) if fps else 0,
           'bytes': counter.sent, 'video_bytes': counter.bytes.get(0, 0),
           'estimated_bytes': int(counter.sent / fraction) if fraction > 0 else 0,
           'thermal_start': first.get('thermal'), 'thermal_end': last.get('thermal'),
           'thermal_peak': ['nominal', 'fair', 'serious', 'critical'][max(0, min(3, max(state['thermal'] or [0])))],
           'battery_start': first.get('battery'), 'battery_end': last.get('battery'),
           'battery_used': round(float(first.get('battery', -1)) - float(last.get('battery', -1)), 3)
           if float(first.get('battery', -1)) >= 0 and float(last.get('battery', -1)) >= 0 else None,
           'charging': sorted(state['charging']), 'low_power': last.get('low_power'), 'partial': bool(state['stopped'])}
    if error:
        run['error'] = error
    log('upscale measurement: RESULT %s' % json.dumps(run, sort_keys=True))
    return run
