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
import threading
import time
import zlib

FILE = 'transfer-history.json'
KINDS = ('down', 'up', 'conv')
LABELS = {'down': 'Downloading', 'up': 'Saving to Google Drive', 'conv': 'Converting'}
TINTS = {'down': 'FF0A84FF', 'up': 'FF30D158', 'conv': 'FFBF5AF2'}
MAX_POINTS = 180
STALE = 30            # seconds without movement before a job counts as finished
# Owner (build 181): Transfers said "Nothing is moving right now" at random while a movie converted. The conversion's
# progress goes quiet while a 32 MB piece uploads (6-17 s on a busy line), so it counts as running for CONV_FRESH s
# after its last update; and the page reads a record saved every 5 s, so a job counts as running for 30 s, not 10.
CONV_FRESH = 60
FINISHED = 400       # History keeps 30 days (KEEP_DAYS); the Transfers page shows the last 24 hours
KEEP_DAYS = 30
FAILURES = 'transfer-failures.json'
GRAPH_FILES = 10
SMOOTH = 4          # points either side averaged in the graph
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
    # The library check also shows in the queue's 'current' ("Movies and shows", "Checking video 3 of 9"): not a
    # conversion (build 174: History listed it as a finished one).
    checking = str(c.get('stage') or '').startswith('Checking') or c.get('title') == 'Movies and shows'
    if c.get('running') and c.get('title') and not checking and time.time() - float(c.get('updated') or 0) < CONV_FRESH:
        out['conv'] = {'title': _title(c.get('title', '')), 'rate': float(c.get('rate') or 0),
                       'done': float(c.get('read') or 0), 'total': 0.0, 'pct': float(c.get('progress') or 0),
                       # Build 177: film position, pace and time left of this attempt (prepare_cloud).
                       'extra': {k: c[k] for k in ('film_done', 'film_total', 'pace', 'eta', 'out_bytes', 'out_total')
                                 if c.get(k) not in (None, '')}}
    return out


def _finish(data, job):
    n = max(1, job.get('n', 1))
    data.setdefault('finished', []).insert(0, {
        'kind': job['kind'], 'title': job['title'], 'start': job['start'], 'end': job['last'],
        'peak': job.get('peak', 0.0), 'avg': job.get('sum', 0.0) / n, 'size': job.get('total') or job.get('done') or 0,
        # How far it got: a job also "finishes" when it stops (Kodi closed, a video played), not only when it is done.
        'done': job.get('done') or 0, 'total': job.get('total') or 0, 'pct': job.get('pct')})
    cutoff = job['last'] - KEEP_DAYS * 86400
    data['finished'] = [f for f in data['finished'] if f.get('end', 0) >= cutoff][:FINISHED]


def outcome(f):
    """'done' (it completed), 'stopped' (it ended part-way) or 'unknown' (a record from before builds kept it)."""
    if f.get('kind') == 'conv':
        if f.get('pct') is None:
            return 'unknown'
        return 'done' if float(f['pct']) >= 99 else 'stopped'
    total, done = float(f.get('total') or 0), float(f.get('done') or 0)
    if not total:
        return 'unknown'
    return 'done' if done >= 0.99 * total else 'stopped'


# --- failures (History) -----------------------------------------------------------------------------------------------
_FAIL_LOCK = threading.Lock()


def failures_location(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FAILURES)


def failures(profile, now=None):
    """[{'kind', 'title', 'reason', 'time'}] newest first, the last KEEP_DAYS days."""
    try:
        with open(failures_location(profile), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    cutoff = (time.time() if now is None else now) - KEEP_DAYS * 86400
    return [x for x in data if isinstance(x, dict) and x.get('time', 0) >= cutoff] if isinstance(data, list) else []


def failed(profile, kind, title, reason, now=None):
    """Note a job that failed (a conversion that stopped, an AllDebrid copy that gave up) for History. Its own file:
    the watch loop rewrites transfer-history.json every few seconds from memory. Never raises."""
    try:
        now = time.time() if now is None else now
        with _FAIL_LOCK:
            items = failures(profile, now)
            items.insert(0, {'kind': kind, 'title': _title(title), 'reason': str(reason or '')[:160], 'time': now})
            path = failures_location(profile)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(items[:200], f)
            os.replace(path + '.tmp', path)
    except Exception:
        pass


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
                   done=a.get('done', 0), total=a.get('total', 0), pct=a.get('pct'), extra=a.get('extra') or {})
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


def running(data, now, fresh=30):
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


def watch(profile, read, wait, every=2, save_every=5, clock=time.time):
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
def smoothed(points, window=SMOOTH):
    """Each point as the average of its neighbours (owner, build 176: "the graph is a little ugly": Drive moves the
    data in bursts, so the raw speed is all spikes)."""
    out = []
    for i, p in enumerate(points):
        near = points[max(0, i - window):i + window + 1]
        weight = sum(q[2] if len(q) > 2 else 1 for q in near) or 1
        out.append([p[0], sum(q[1] * (q[2] if len(q) > 2 else 1) for q in near) / weight] + list(p[2:3]))
    return out


def device_scale():
    """Physical output pixels per portrait unit; host tests default to one."""
    try:
        import xbmc
        return max(.5, min(3., float(xbmc.getInfoLabel('System.ScreenWidth')) / 1080))
    except (ImportError, AttributeError, TypeError, ValueError):
        return 1.


def _axis(value):
    """'6', '4.5', '0.8': the graph's right-hand axis numbers (MB/s)."""
    return ('%.1f' % value).rstrip('0').rstrip('.') if value < 10 else '%d' % round(value)


def axis_top(points):
    """The graph's top value (bytes/s): a round number so the three guide lines read 6 / 4 / 2 (board 3)."""
    import math
    peak = max([p[1] for p in points] + [1.]) * 1.25 / 1048576
    step = peak / 4
    mag = 10 ** math.floor(math.log10(step)) if step > 0 else 1
    nice = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= step)
    return nice * 4 * 1048576


def ago_text(seconds):
    """'10 min ago', '1 h 5 min ago' for the graph's left time."""
    minutes = max(1, int(round(seconds / 60.)))
    return ('%d min ago' % minutes) if minutes < 60 else ('%d h %d min ago' % divmod(minutes, 60)).replace(' 0 min', '')


def graph_labels(points, start=None, now=None):
    """Kodi labels for a graph (board 3/4): the MB/s value at each of the three guide lines (top to bottom), the start
    time in the phone's clock style, the peak in MB/s and where it is along the plot (0..1)."""
    points = smoothed(points)
    top = axis_top(points) / 1048576
    peak = max(points, key=lambda p: p[1]) if points else None
    t0 = start if start is not None else (points[0][0] if points else 0)
    t1 = max((now if now is not None else (points[-1][0] if points else t0)), t0 + 1)
    when = time.localtime(t0) if points or start is not None else None
    return {'axis0': _axis(top * .75), 'axis1': _axis(top * .5), 'axis2': _axis(top * .25),
            'peak': '%.1f' % (peak[1] / 1048576) if peak else '',
            'peak_x': (peak[0] - t0) / (t1 - t0) if peak else 0.,
            'from': ago_text(t1 - t0) if when else ''}


def render(points, colour, width=W, height=H, start=None, now=None, scale=1., line_pt=2.5, guides=True):
    """Display size × device scale; rounded 2.5 pt stroke with 4× edge supersampling.

    Fill interiors are exact; only boundary pixels need subpixel samples. This keeps
    the pure-Python renderer cheap enough for Kodi's two-second refresh, without PIL.
    No words are baked into the raster (graph_labels supplies Kodi labels).
    """
    import math
    width, height = max(1, round(width * scale)), max(1, round(height * scale))
    rgb = tuple(int(colour[i:i+2],16) for i in (2,4,6)) if isinstance(colour,str) else colour
    points = smoothed(points)
    px = bytearray(width * height * 4)
    if not points:
        return _png(px,width,height)
    top = axis_top(points) if guides else max([p[1] for p in points] + [1.]) * 1.25
    radius = max(.75, line_pt * 2.687 * scale / 2)
    pad = radius + 2
    t0 = points[0][0] if start is None else start
    t1 = max(points[-1][0] if now is None else now, t0+1)
    padx = max(pad, 9 * 2.687 * scale + 1) if guides else pad    # room for the now dot's halo (board 3)
    xy = [(max(padx,min(width-padx,(p[0]-t0)/(t1-t0)*(width-2*padx)+padx)),
           height-pad-max(0,p[1])/top*(height-2*pad)) for p in points]
    if len(xy)==1: xy = [(pad,xy[0][1]),(width-pad,xy[0][1])]
    def put(x,y,c,a):
        if 0<=x<width and 0<=y<height:
            i=(y*width+x)*4; px[i:i+4]=bytes((*c,max(0,min(255,round(a)))))
    if guides:
        for g in (.25,.5,.75):
            y=round(pad+g*(height-2*pad))
            for x in range(width): put(x,y,(255,255,255),22)
    # Monotonic time samples: one segment per column, supersample the rounded stroke.
    seg=0
    for x in range(max(0,math.floor(xy[0][0]-radius)),min(width,math.ceil(xy[-1][0]+radius)+1)):
        while seg<len(xy)-2 and x>xy[seg+1][0]: seg+=1
        ax,ay=xy[seg]; bx,by=xy[seg+1]; dx,dy=bx-ax,by-ay
        length=max(1e-9,dx*dx+dy*dy)
        at=ay+(by-ay)*max(0,min(1,(x+.5-ax)/max(1e-9,dx)))
        if xy[0][0]<=x<=xy[-1][0]:
            for y in range(max(0,math.ceil(at)),height):
                put(x,y,rgb,90*max(0,1-(y-at)/max(1,height-at)))
        reach=radius*(1+abs(dy)/max(1,abs(dx)))+2
        for y in range(max(0,math.floor(at-reach)),min(height,math.ceil(at+reach)+1)):
            hits=0
            for sy in (.125,.375,.625,.875):
                for sx in (.125,.375,.625,.875):
                    t=max(0,min(1,((x+sx-ax)*dx+(y+sy-ay)*dy)/length))
                    hits+=((x+sx-ax-t*dx)**2+(y+sy-ay-t*dy)**2<=radius**2)
            if hits: put(x,y,rgb,255*hits/16)
    # Peak marker (board 3): a faint dashed line from the highest point down to the base.
    if guides and len(xy) > 2:
        k = max(range(len(points)), key=lambda i: points[i][1])
        mx, my = round(xy[k][0]), xy[k][1]
        dash = max(3, round(3 * 2.687 * scale))
        for y in range(max(0, round(my + radius * 2)), height):
            if (y // dash) % 2 == 0:
                put(mx, y, (235, 235, 245), 64)
    # Now marker, with the same edge sampling.
    cx,cy=xy[-1]; dot=radius*1.65
    for y in range(max(0,int(cy-dot-1)),min(height,int(cy+dot+2))):
        for x in range(max(0,int(cx-dot-1)),min(width,int(cx+dot+2))):
            hits=sum((x+sx-cx)**2+(y+sy-cy)**2<=dot**2 for sx in (.125,.375,.625,.875) for sy in (.125,.375,.625,.875))
            if hits: put(x,y,rgb,255*hits/16)
    # A white "now" dot with a soft halo (board 3/4), over the line's colour.
    if guides:
        dot = 5 * 2.687 * scale          # board 3: a 5 pt white dot with a 9 pt halo
        halo = 9 * 2.687 * scale
        for y in range(max(0,int(cy-halo-1)),min(height,int(cy+halo+2))):
            for x in range(max(0,int(cx-halo-1)),min(width,int(cx+halo+2))):
                d2=(x+.5-cx)**2+(y+.5-cy)**2
                if d2<=dot**2: put(x,y,(255,255,255),255)
                elif d2<=halo**2:
                    i=(y*width+x)*4
                    if px[i+3]<46: put(x,y,(255,255,255),46)
    return _png(px,width,height)


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



class GraphCache:
    """A page's plots, repainted only when that job has new points and at most every REDRAW seconds (build 193,
    owner: drawing costs the conversion CPU). Images live in one folder per job; folders of jobs no longer shown and
    the loose files of older builds are deleted, so nothing piles up."""
    REDRAW = 10.0
    KEEP = 60.0          # a job not drawn for this long gives its folder back

    def __init__(self, namespace, clock=time.monotonic):
        self.namespace = namespace
        self.clock = clock
        self.entries = {}      # identity -> (signature, path, drawn_at, used_at, stream)
        self.counter = 0
        self.tidied = set()

    def _tidy(self, folder, keep):
        import shutil
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for name in names:
            path = os.path.join(folder, name)
            if name.startswith(self.namespace + '-') and name not in keep and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif folder not in self.tidied and name.startswith('graph_') and name.endswith(('.png', '.tmp')):
                try:
                    os.remove(path)   # build-192 pages wrote loose graph_N.png here
                except OSError:
                    pass
        self.tidied.add(folder)

    def image(self, identity, points, colour, folder, prefix, **options):
        if not points:
            return ''
        now = self.clock()
        identity = tuple(identity)
        signature = (len(points), points[-1][0])
        previous = self.entries.get(identity)
        if previous and (previous[0] == signature or now - previous[2] < self.REDRAW):
            self.entries[identity] = previous[:3] + (now,) + previous[4:]
            return previous[1]
        import hashlib
        stream = self.namespace + '-' + hashlib.sha256(repr(identity).encode()).hexdigest()[:12]
        self.counter += 1
        name = write_graph(os.path.join(folder, stream), self.counter, render(points, colour, **options))
        path = prefix.rstrip('/') + '/' + stream + '/' + name
        self.entries[identity] = (signature, path, now, now, stream)
        for key in [k for k, e in self.entries.items() if now - e[3] > self.KEEP]:
            del self.entries[key]
        self._tidy(folder, {e[4] for e in self.entries.values()})
        return path
