"""Look at our own sources before they are tapped (owner, 2026-11-28: "it should check sources or try them upon opening"). For LiveFeeds, 720pStream and FawaNews the stream is resolved the way a tap
does it and its master playlist is read: picture size, frame rate and bitrate (the best variant) go onto the row. Nothing is played; Crew and The Loop rows cannot be measured this way
and say so. Results are kept for two minutes (memory), so reopening the page does not ask the sites again. Pure Python (no Kodi) except the callers' threads."""
import json
import re
import threading
import time
import urllib.parse
import urllib.request

KEEP = 120            # seconds a result is reused
TIMEOUT = 8
MAX_BYTES = 256 * 1024
MAX_SEGMENT = 3 * 1024 * 1024
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'
_results = {}         # play value -> (when, result)
_running = set()
_lock = threading.Lock()


def own_name(play):
    """The own site a source belongs to ('LiveFeeds' ...), or '' (Crew, The Loop, anything else)."""
    try:
        value = json.loads(play)
    except (TypeError, ValueError):
        return ''
    import sports_fawa
    import sports_livefeeds
    import sports_p720
    name = value.get('e') if isinstance(value, dict) else ''
    return name if name in (sports_fawa.NAME, sports_livefeeds.NAME, sports_p720.NAME) else ''


def resolve(play):
    """(address, headers) of the stream a tap would open."""
    value = json.loads(play)
    import sports_fawa
    import sports_livefeeds
    import sports_p720
    address = value['l']['address']
    if value['e'] == sports_fawa.NAME:
        return sports_fawa.resolve(address), {}
    module = sports_p720 if value['e'] == sports_p720.NAME else sports_livefeeds
    return module.resolve(address, note=lambda text: None)


def fetch_text(address, headers, opener=None):
    request = urllib.request.Request(address, headers=dict({'User-Agent': UA}, **(headers or {})))
    with (opener or urllib.request.urlopen)(request, timeout=TIMEOUT) as response:
        return response.read(MAX_BYTES).decode('utf-8', 'replace')


def parse_master(text):
    """The best variant of a master playlist: {'height','width','fps','kbps','variants'}; {'single': True} for a plain (media) playlist; None when it is not a playlist."""
    if '#EXTM3U' not in (text or ''):
        return None
    best, count = None, 0
    for line in text.splitlines():
        if not line.startswith('#EXT-X-STREAM-INF'):
            continue
        count += 1
        size = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
        rate = re.search(r'(?<![A-Z-])BANDWIDTH=(\d+)', line)
        fps = re.search(r'FRAME-RATE=([\d.]+)', line)
        entry = {'width': int(size.group(1)) if size else 0, 'height': int(size.group(2)) if size else 0,
                 'kbps': int(rate.group(1)) // 1000 if rate else 0, 'fps': int(round(float(fps.group(1)))) if fps else 0}
        if best is None or (entry['height'], entry['kbps']) > (best['height'], best['kbps']):
            best = entry
    if best is None:
        return {'single': True}
    best['variants'] = count
    return best


def last_segment(text):
    """(seconds, address) of the newest segment of a media playlist, or None."""
    seconds, found = 0.0, None
    for line in (text or '').splitlines():
        line = line.strip()
        if line.startswith('#EXTINF:'):
            try:
                seconds = float(line[8:].split(',')[0])
            except ValueError:
                seconds = 0.0
        elif line and not line.startswith('#'):
            found = (seconds, line)
    return found


def fetch_bytes(address, headers, clock=time.monotonic):
    """(bytes read, seconds it took) of one segment (at most MAX_SEGMENT)."""
    request = urllib.request.Request(address, headers=dict({'User-Agent': UA}, **(headers or {})))
    began = clock()
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = response.read(MAX_SEGMENT)
    return len(data), max(clock() - began, 0.001)


def measure_segment(address, headers, text, get=fetch_bytes):
    """A plain playlist has no sizes in it, so the newest segment is downloaded and weighed: the stream's bitrate, and how many times faster than playing it downloads (below 1.5 it will stall)."""
    found = last_segment(text)
    if not found or not found[0]:
        return {}
    size, took = get(urllib.parse.urljoin(address, found[1]), headers)
    if size < 20000:   # an error page or an empty answer, not a segment
        return {}
    return {'kbps': int(size * 8 / found[0] / 1000), 'speed': round(found[0] / took, 1)}


def probe(play, resolver=resolve, fetch=fetch_text, clock=time.monotonic, measure=measure_segment):
    """{'ok': True, ...picture...} or {'ok': False, 'why': ...}; never raises. 'took' is how long the resolve and the playlist took, in seconds."""
    began = clock()
    try:
        address, headers = resolver(play)
        text = fetch(address, headers)
        found = parse_master(text)
        if found and found.get('single'):
            try:
                found.update(measure(address, headers, text))
            except Exception:
                pass   # the playlist answered; only the weighing failed
    except Exception as error:
        return {'ok': False, 'why': type(error).__name__, 'took': round(clock() - began, 1)}
    if found is None:
        return {'ok': False, 'why': 'not a playlist', 'took': round(clock() - began, 1)}
    return dict(found, ok=True, took=round(clock() - began, 1))


def cached(play, clock=time.time):
    with _lock:
        held = _results.get(play)
    return held[1] if held and clock() - held[0] < KEEP else None


def checked_at(play):
    """When the kept result for this source was made (epoch seconds), or None."""
    with _lock:
        held = _results.get(play)
    return held[0] if held else None


def start(sources, done=None, run=probe, clock=time.time, spawn=None, log=None):
    """Check every own source that has no fresh result, each in its own thread; `done()` is called after each so the page can draw it. Returns how many were started."""
    spawn = spawn or (lambda target: threading.Thread(target=target, daemon=True).start())
    started = 0
    for source in sources:
        play = str(source.get('play') or '')
        if not own_name(play) or cached(play, clock) is not None:
            continue
        with _lock:
            if play in _running:
                continue
            _running.add(play)

        def work(play=play, name=own_name(play)):
            result = run(play)
            with _lock:
                _results[play] = (clock(), result)
                _running.discard(play)
            if log:
                log('sports: checked %s: %s (%ss)' % (name, describe(result), result.get('took')))
            if done:
                try:
                    done()
                except Exception:
                    pass
        spawn(work)
        started += 1
    return started


def describe(result):
    """'1080p · 60 fps · 5.2 Mbps' for a row; 'didn't respond' for a failed check; '' for nothing to say."""
    if not result:
        return ''
    if not result.get('ok'):
        return "didn't respond"
    parts = []
    if result.get('height'):
        parts.append('%dp' % result['height'])
    if result.get('fps'):
        parts.append('%d fps' % result['fps'])
    if result.get('kbps'):
        parts.append('%.1f Mbps' % (result['kbps'] / 1000.0))
    if result.get('speed'):
        parts.append('downloads %.1fx faster than it plays' % result['speed'] if result['speed'] >= 1.5 else 'too slow (%.1fx)' % result['speed'])
    return ' · '.join(parts) or 'playlist found (size shown once it plays)'
