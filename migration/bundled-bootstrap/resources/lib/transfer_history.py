"""Transfers page (owner, build 170: "a graph showing the history of download like what steam does and peak and
everything"; approved mockup, opened only by tapping a transfer card in Notifications).

History: the bootstrap service records, every 2 s, how fast things move (bytes per second):
  down  downloading (Elementum torrents, AllDebrid to Drive copies)
  up    uploading to Google Drive (AllDebrid copies, phone uploads)
  conv  the conversion reading the movie from Drive
kept at three resolutions (5 min at 2 s, 1 hour at 30 s, 24 hours at 10 min) in transfer-history.json.

Graph: Kodi skins cannot draw charts, so the page paints the selected range into a small PNG (pure Python) and shows
it; the file name cycles through GRAPH_FILES names so Kodi's texture manager never shows a stale copy.
"""
import json
import os
import struct
import time
import zlib

FILE = 'transfer-history.json'
RANGES = {'5min': (2, 150), 'hour': (30, 120), 'day': (600, 144)}   # seconds per sample, samples kept
UPLOAD_LIMIT = 70e6 / 8          # the owner's upload (70 Mbps, speed test)
GRAPH_FILES = 10
W, H = 360, 150
DOWN, UP, CONV, LIMIT, GRID = (10, 132, 255), (48, 209, 88), (191, 90, 242), (255, 159, 10), (60, 60, 67)


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


def record(data, now, down, up, conv):
    """Add one sample to every range (a coarser range averages what falls into its slot). Returns data."""
    for key, (step, keep) in RANGES.items():
        ring = data.setdefault(key, [])
        slot = int(now // step) * step
        if ring and ring[-1][0] == slot:
            last = ring[-1]
            n = last[4] + 1
            ring[-1] = [slot, (last[1] * last[4] + down) / n, (last[2] * last[4] + up) / n, (last[3] * last[4] + conv) / n, n]
        else:
            ring.append([slot, down, up, conv, 1])
        del ring[:-keep]
    date = time.strftime('%Y-%m-%d', time.localtime(now))
    if data.get('date') != date:
        data['date'], data['moved'], data['peak'] = date, 0.0, 0.0
    data['moved'] = data.get('moved', 0.0) + max(down, up) * RANGES['5min'][0]
    data['peak'] = max(data.get('peak', 0.0), down, up)
    data['now'] = [now, down, up, conv]
    return data


def series(data, key, now):
    """[(down, up, conv)] for the range, oldest first, one per slot, gaps as 0."""
    step, keep = RANGES[key]
    by_slot = {s[0]: s for s in data.get(key, [])}
    end = int(now // step) * step
    return [tuple(by_slot.get(end - (keep - 1 - i) * step, [0, 0, 0, 0])[1:4]) for i in range(keep)]


def stats(data, key, now):
    """Current down/up/conv (0 when older than 10 s), the range's peak, and what moved today, in bytes(/s)."""
    cur = data.get('now') or [0, 0, 0, 0]
    fresh = now - cur[0] <= 10
    values = series(data, key, now)
    return {'down': cur[1] if fresh else 0.0, 'up': cur[2] if fresh else 0.0, 'conv': cur[3] if fresh else 0.0,
            'peak': max([max(v[0], v[1]) for v in values] + [0.0]), 'today': data.get('moved', 0.0)}


def mb(value):
    return '%.1f MB/s' % (value / 1048576.0)


def mbps(value):
    return '%d Mbps' % round(value * 8 / 1e6)


def rates(torrents, debrid_current, prep_current):
    """(down, up, conv) bytes per second right now: Elementum's torrents (download_rate is KB/s) plus a copy from
    AllDebrid (it flows in and out at the same speed), uploads to Drive, and the conversion's read speed."""
    down = 0.0
    for t in torrents or []:
        try:
            if str(t.get('status', '')).lower() not in ('paused', 'finished', 'seeding'):
                down += float(t.get('download_rate') or 0) * 1024
        except (TypeError, ValueError):
            pass
    copy = float((debrid_current or {}).get('rate') or 0) if (debrid_current or {}).get('stage') == 'copying' else 0.0
    conv = float((prep_current or {}).get('rate') or 0) if (prep_current or {}).get('running') else 0.0
    return down + copy, copy, conv


def watch(profile, read, wait, every=2, save_every=10, clock=time.time):
    """The service loop: read() -> (down, up, conv); records every `every` s, saves every `save_every` s."""
    data = load(profile)
    last_save = 0.0
    while not wait(every):
        try:
            now = clock()
            record(data, now, *read())
            if now - last_save >= save_every:
                save(profile, data)
                last_save = now
        except Exception:
            pass


# --- the graph -------------------------------------------------------------------------------------------------------
def render(values, width=W, height=H, limit=UPLOAD_LIMIT):
    """PNG bytes: down as bars, up as a 2-px line, conversion as a dotted line, the upload limit dashed, faint grid."""
    top = max([max(v) for v in values] + [limit * 1.15, 1.0])
    px = bytearray(width * height * 4)   # transparent

    def put(x, y, c, a=255):
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 4
            px[i:i + 4] = bytes((c[0], c[1], c[2], a))

    def ypos(v):
        return int(round((height - 2) - (v / top) * (height - 6)))
    for g in range(1, 4):   # grid
        y = int(height * g / 4)
        for x in range(0, width, 2):
            put(x, y, GRID, 160)
    n = len(values)
    col = width / float(n)
    for i, (down, up, conv) in enumerate(values):   # bars
        y0 = ypos(down)
        for x in range(int(i * col), max(int(i * col) + 1, int((i + 1) * col) - 1)):
            for y in range(y0, height):
                put(x, y, DOWN, 190)
    ly = ypos(limit)   # upload limit
    for x in range(width):
        if (x // 4) % 2 == 0:
            put(x, ly, LIMIT)

    def line(index, colour, dotted):
        prev = None
        for i, v in enumerate(values):
            x = int((i + 0.5) * col)
            y = ypos(v[index])
            if prev:
                x0, y0 = prev
                steps = max(abs(x - x0), abs(y - y0), 1)
                for s in range(steps + 1):
                    if dotted and (s // 2) % 2:
                        continue
                    xx = x0 + (x - x0) * s // steps
                    yy = y0 + (y - y0) * s // steps
                    put(xx, yy, colour)
                    put(xx, yy + 1, colour)
            prev = (x, y)
    line(1, UP, False)
    line(2, CONV, True)
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
