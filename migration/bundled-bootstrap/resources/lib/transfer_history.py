"""Transfers page speed history, one job at a time (owner, build 172: "I want the graph to be simple and show me only
what its doing at that time like if its downloading then i can tap on it and it will show me the downloading peak, then
once done with that it can show me conversion"; approved mockup).

The bootstrap service looks every 2 s at what is moving and keeps one record per kind of job:
  down  an Elementum torrent downloading to the phone
  up    a copy going to Google Drive (AllDebrid → Drive; it comes in and goes out at one speed, so it is one job)
  conv  the conversion reading the movie from Drive
Each record has the job's title, when it started, its peak and average, and its speed over time (at most MAX_POINTS
points: when full, neighbours are merged and the spacing doubles, so the graph always covers the whole job). A job that
changes title or stops for STALE seconds moves to `finished` (the newest FINISHED kept) with its size, time and peak.

Graph: Kodi skins cannot draw charts, so the page paints the chosen job into a small PNG (pure Python); the file name
cycles through GRAPH_FILES names so Kodi's texture manager never shows a stale copy.
"""
import json
import os
import struct
import time
import zlib

FILE = 'transfer-history.json'
KINDS = ('down', 'up', 'conv')
LABELS = {'down': 'Downloading', 'up': 'Saving to Google Drive', 'conv': 'Converting'}
TINTS = {'down': 'FF0A84FF', 'up': 'FF30D158', 'conv': 'FFBF5AF2'}
MAX_POINTS = 180
STALE = 30            # seconds without movement before a job counts as finished
FINISHED = 20
GRAPH_FILES = 10
W, H = 470, 220


def location(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(location(profile), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(profile, data):
    path = location(profile)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _title(name):
    try:
        import drivelibrary
        return drivelibrary.display_title(name)
    except Exception:
        return str(name or '')


def activity(torrents, debrid_current, prep_current):
    """What is moving right now: {kind: {'title', 'rate' (bytes/s), 'done', 'total'}} for each kind that runs."""
    out = {}
    live = []
    for t in torrents or []:
        try:
            if str(t.get('status', '')).lower() in ('paused', 'finished', 'seeding') or float(t.get('progress') or 0) >= 100:
                continue
            live.append(t)
        except (AttributeError, TypeError, ValueError):
            pass
    if live:
        size = sum(float(t.get('size_bytes') or 0) for t in live)
        out['down'] = {'title': _title(live[0].get('name', '')) + (' and %d more' % (len(live) - 1) if len(live) > 1 else ''),
                       'rate': sum(float(t.get('download_rate') or 0) for t in live) * 1024,   # Elementum reports KB/s
                       'done': sum(float(t.get('size_bytes') or 0) * float(t.get('progress') or 0) / 100 for t in live),
                       'total': size}
    d = debrid_current or {}
    if d.get('stage') == 'copying' and d.get('total'):
        out['up'] = {'title': _title(d.get('name', '')), 'rate': float(d.get('rate') or 0),
                     'done': float(d.get('sent') or 0), 'total': float(d.get('total') or 0)}
    c = prep_current or {}
    if c.get('running') and c.get('title') and time.time() - float(c.get('updated') or 0) < 15:
        out['conv'] = {'title': _title(c.get('title', '')), 'rate': float(c.get('rate') or 0),
                       'done': float(c.get('read') or 0), 'total': 0.0, 'pct': float(c.get('progress') or 0)}
    return out


def _finish(data, job):
    n = max(1, job.get('n', 1))
    data.setdefault('finished', []).insert(0, {
        'kind': job['kind'], 'title': job['title'], 'start': job['start'], 'end': job['last'],
        'peak': job.get('peak', 0.0), 'avg': job.get('sum', 0.0) / n, 'size': job.get('total') or job.get('done') or 0})
    del data['finished'][FINISHED:]


def track(data, now, active):
    """Add one look at `active` (from activity()) to the running jobs; close jobs that ended. Returns data."""
    jobs = data.setdefault('jobs', {})
    for kind in KINDS:
        a = active.get(kind)
        job = jobs.get(kind)
        if job and ((a and a['title'] != job['title']) or (not a and now - job['last'] > STALE)):
            _finish(data, job)
            del jobs[kind]
            job = None
        if not a:
            continue
        rate = max(0.0, float(a.get('rate') or 0))
        if not job:
            job = jobs[kind] = {'kind': kind, 'title': a['title'], 'start': now, 'last': now, 'peak': 0.0, 'sum': 0.0,
                                'n': 0, 'step': 2, 'points': []}
        job.update(last=now, peak=max(job['peak'], rate), sum=job['sum'] + rate, n=job['n'] + 1,
                   done=a.get('done', 0), total=a.get('total', 0), pct=a.get('pct'))
        pts = job['points']
        if pts and now - pts[-1][0] < job['step']:
            last = pts[-1]
            last[1] = (last[1] * last[2] + rate) / (last[2] + 1)
            last[2] += 1
        else:
            pts.append([now, rate, 1])
        if len(pts) > MAX_POINTS:
            merged = []
            for i in range(0, len(pts), 2):
                pair = pts[i:i + 2]
                count = sum(p[2] for p in pair)
                merged.append([pair[0][0], sum(p[1] * p[2] for p in pair) / count, count])
            job['points'] = merged
            job['step'] *= 2
    return data


def running(data, now, fresh=10):
    """The kinds with a job that moved in the last `fresh` seconds, in KINDS order."""
    jobs = data.get('jobs') or {}
    return [k for k in KINDS if k in jobs and now - jobs[k].get('last', 0) <= fresh]


def pick(data, wanted, now):
    """The job the graph shows: the one tapped while it runs, otherwise the next one still running, or None."""
    live = running(data, now)
    if wanted in live:
        return wanted
    for kind in ('conv', 'up', 'down'):
        if kind in live:
            return kind
    return None


def watch(profile, read, wait, every=2, save_every=10, clock=time.time):
    """The service loop: read() -> activity(); looks every `every` s, saves every `save_every` s."""
    data = load(profile)
    data.pop('5min', None), data.pop('hour', None), data.pop('day', None)   # the build-171 ranges
    last_save = 0.0
    while not wait(every):
        try:
            now = clock()
            track(data, now, read())
            if now - last_save >= save_every:
                save(profile, data)
                last_save = now
        except Exception:
            pass


# --- words ------------------------------------------------------------------------------------------------------------
def mb(value):
    value = float(value or 0)
    return '%d KB/s' % round(value / 1024) if 0 < value < 1048576 else '%.1f MB/s' % (value / 1048576.0)


def size(value):
    value = float(value or 0)
    return '%.1f GB' % (value / 1024 ** 3) if value >= 1024 ** 3 else '%d MB' % (value // 1024 ** 2)


def ago(seconds):
    m = int(max(0, seconds) // 60)
    if m < 1:
        return 'just now'
    return '%d min ago' % m if m < 60 else '%d h %d min ago' % (m // 60, m % 60) if m % 60 else '%d h ago' % (m // 60)


def took(seconds):
    m = int(max(0, seconds) // 60)
    return 'under a minute' if m < 1 else '%d min' % m if m < 60 else '%d h %d min' % (m // 60, m % 60)


# --- the graph -------------------------------------------------------------------------------------------------------
def render(points, colour, width=W, height=H, start=None, now=None):
    """PNG bytes: the job's speed as one line over a fading fill, with its peak as a faint dashed line."""
    rgb = tuple(int(colour[i:i + 2], 16) for i in (2, 4, 6)) if isinstance(colour, str) else colour
    top = max([p[1] for p in points] + [1.0]) * 1.12
    px = bytearray(width * height * 4)
    if not points:
        return _png(px, width, height)
    t0 = points[0][0] if start is None else start
    t1 = max(points[-1][0] if now is None else now, t0 + 1)

    def put(x, y, c, a):
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 4
            px[i:i + 4] = bytes((c[0], c[1], c[2], a))

    def ypos(v):
        return int(round((height - 3) - (v / top) * (height - 12)))
    xy = [(int(round((p[0] - t0) / (t1 - t0) * (width - 4))) + 2, ypos(p[1])) for p in points]
    if len(xy) == 1:
        xy = [(2, xy[0][1]), (width - 3, xy[0][1])]
    line = {}
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            line[x] = min(line.get(x, height), y)
            for dy in (-1, 0, 1):
                put(x, y + dy, rgb, 255)
    for x, y in line.items():   # fill fades towards the bottom
        for yy in range(y + 2, height):
            put(x, yy, rgb, int(110 * (1 - (yy - y) / float(height - y + 1))))
    py = ypos(max(p[1] for p in points))   # the peak
    for x in range(width):
        if (x // 6) % 2 == 0 and px[(py * width + x) * 4 + 3] == 0:
            put(x, py, (255, 255, 255), 70)
    return _png(px, width, height)


def _png(px, width, height):
    rows = b''.join(b'\0' + bytes(px[y * width * 4:(y + 1) * width * 4]) for y in range(height))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows, 6)) + chunk(b'IEND', b''))


def write_graph(folder, counter, png):
    """Write the graph under a cycling name and return that name (the page points its image at it)."""
    os.makedirs(folder, exist_ok=True)
    name = 'graph_%d.png' % (counter % GRAPH_FILES)
    path = os.path.join(folder, name)
    with open(path + '.tmp', 'wb') as f:
        f.write(png)
    os.replace(path + '.tmp', path)
    return name
