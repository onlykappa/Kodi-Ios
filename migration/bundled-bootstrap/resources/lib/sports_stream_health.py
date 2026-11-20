"""Sports: is a source really playing video, and which source is best (owner, 2026-11-20).

Owner: "when I select a source there should be something checking what is actually playing video, then what has the best stats (bitrate or
whatever is best) to rank the best stream and provide that stream, not some dead link like before".

Three parts, all free of Kodi so they can be tested here:

  Watch   judges a stream that Kodi has begun to play from samples of the playback clock: it is `good` once the picture has really moved for
          a few seconds at about real time, `bad` when the clock stops or crawls (a dead or starved link that opened and then froze).
  Stats   what Kodi reports about the picture it is showing (height, frame rate, video bitrate when the stream states it).
  Health  what the phone has learned about each source name ("Crew 720"): worked / failed recently, how sharp, how smooth. It orders the
          choices so a source that died ten minutes ago is tried after one that worked, and a 1080p one before a 480p one. Only the source's
          label and numbers are stored, never an address, token or header.
"""
import json
import os
import tempfile
import time

OBSERVE = 5.0        # seconds of picture to see before a source counts as good
MIN_RATE = .6        # picture seconds per real second; below this the stream is starving (buffering over and over)
STALL = 6.0          # real seconds without the clock moving, after the picture began, is a frozen stream
FIRST_PICTURE = 40.0  # real seconds a chosen source may take to show its first moving picture before the next one is tried
HOUR = 3600.0


def number(text):
    """'1,080' / '720' / '' / None -> int (0 when it is not a number)."""
    try:
        return int(float(str(text).replace(',', '').strip()))
    except (TypeError, ValueError):
        return 0


def read_stats(info):
    """What Kodi says about the picture on screen. `info` is xbmc.getInfoLabel; any label may be empty (not every stream states a bitrate)."""
    def ask(label):
        try:
            return number(info(label))
        except Exception:
            return 0
    return {'height': ask('Player.Process(videoheight)'), 'width': ask('Player.Process(videowidth)'),
            'fps': ask('Player.Process(videofps)'), 'kbps': ask('VideoPlayer.VideoBitrate')}


def describe(stats):
    """'720p 30 fps 2400 kbps' for the log; only what is known."""
    parts = []
    if stats.get('height'):
        parts.append('%dp' % stats['height'])
    if stats.get('fps'):
        parts.append('%d fps' % stats['fps'])
    if stats.get('kbps'):
        parts.append('%d kbps' % stats['kbps'])
    return ' '.join(parts) or 'no picture details reported'


class Watch:
    """Feed it (now, picture position in seconds, stats) as often as you like; it answers 'wait', 'good' or 'bad' (with `reason`).

    It starts judging at the first sample where the picture position has moved. 'good' needs OBSERVE seconds of picture at about real time and,
    where Kodi reports a size, a picture with a height. 'bad' is a clock that has stopped for STALL seconds, or one that advances slower than
    MIN_RATE of real time over the observation (a link that opens and then starves).
    """
    def __init__(self):
        self.first_position = self.first_time = None   # where and when the picture first moved
        self.last_position = self.last_move = None
        self.reason = ''
        self.stats = {}
        self.samples = 0

    def feed(self, now, position, stats=None):
        self.samples += 1
        if stats and (stats.get('height') or not self.stats):
            self.stats = dict(stats)
        if position is None:
            return 'wait'
        if self.last_position is None:
            self.last_position, self.last_move = position, now
            return 'wait'
        if self.first_position is None:
            if position > self.last_position + .05:   # the first real movement
                self.first_position, self.first_time = self.last_position, self.last_move
                self.last_position, self.last_move = position, now
            else:
                self.last_position = min(self.last_position, position)
                if now - self.last_move >= STALL * 2:
                    self.reason = 'the picture never moved'
                    return 'bad'
            return 'wait'
        if position > self.last_position + .05:
            self.last_position, self.last_move = position, now
        elif now - self.last_move >= STALL:
            self.reason = 'the picture froze for %d s' % STALL
            return 'bad'
        elapsed, moved = now - self.first_time, self.last_position - self.first_position
        if elapsed < OBSERVE:
            return 'wait'
        if moved < elapsed * MIN_RATE:
            if now - self.last_move >= 2:
                self.reason = 'the picture froze after %.1f s' % moved
                return 'bad'
            self.reason = 'too slow (%.1f s of picture in %.1f s)' % (moved, elapsed)
            return 'bad'
        return 'good'


class Health:
    """What has worked. A small JSON file in the add-on's data folder (or memory when `path` is None)."""
    KEEP = 40            # source names remembered
    FRESH = 6 * HOUR     # a success or a failure counts for this long, fading out

    def __init__(self, path=None, clock=time.time):
        self.path, self.clock = path, clock
        self.data = {}
        try:
            if path and os.path.exists(path):
                with open(path, encoding='utf-8') as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    self.data = {str(k): v for k, v in loaded.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            self.data = {}

    def _save(self):
        if not self.path:
            return
        if len(self.data) > self.KEEP:
            newest = sorted(self.data, key=lambda k: -max(self.data[k].get('ok_at', 0), self.data[k].get('fail_at', 0)))
            self.data = {k: self.data[k] for k in newest[:self.KEEP]}
        try:
            folder = os.path.dirname(self.path) or '.'
            os.makedirs(folder, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=folder)
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                json.dump(self.data, out, separators=(',', ':'))
            os.replace(temp, self.path)
        except OSError:
            pass

    def ok(self, key, stats=None):
        item = self.data.setdefault(key, {})
        item['ok_at'] = self.clock()
        item['ok'] = item.get('ok', 0) + 1
        for name in ('height', 'fps', 'kbps'):
            value = (stats or {}).get(name) or 0
            if value:
                item[name] = value
        self._save()

    def fail(self, key, reason=''):
        item = self.data.setdefault(key, {})
        item['fail_at'] = self.clock()
        item['fail'] = item.get('fail', 0) + 1
        item['why'] = str(reason)[:60]
        self._save()

    def dead(self, key):
        """Failed within the last half hour and has not worked since."""
        item = self.data.get(key) or {}
        failed, worked = item.get('fail_at', 0), item.get('ok_at', 0)
        return bool(failed) and failed > worked and self.clock() - failed < 1800

    def score(self, key, quality=0):
        """Higher is better. A recent success counts most, a recent failure subtracts more; sharpness and bitrate break ties."""
        item = self.data.get(key) or {}
        now = self.clock()
        total = float(quality)   # the add-on's own reported size (0-3), if any
        if item.get('ok_at'):
            total += 2.0 * max(0.0, 1 - (now - item['ok_at']) / self.FRESH)
        if item.get('fail_at'):
            age = now - item['fail_at']
            total -= (3.0 if item['fail_at'] > item.get('ok_at', 0) else 1.0) * max(0.0, 1 - age / self.FRESH)
        if item.get('height'):
            total += min(item['height'], 1080) / 1080.0 * 1.5
        if item.get('kbps'):
            total += min(item['kbps'], 6000) / 6000.0
        return total

    def order(self, entries, key=lambda entry: entry, quality=lambda entry: 0, first=None):
        """Best first, stable for equal scores. `first` (the source the person tapped) leads unless it failed recently and has not worked since."""
        ranked = sorted(entries, key=lambda entry: -self.score(key(entry), quality(entry)))
        if first is not None and not self.dead(key(first)):
            ranked = [entry for entry in ranked if entry is not first]
            ranked.insert(0, first)
        return ranked


def open_health(translate=None, clock=time.time):
    """The phone's Health file under the bootstrap add-on's data folder; memory-only when Kodi's path functions are not there."""
    try:
        if translate is None:
            import xbmcvfs
            translate = xbmcvfs.translatePath
        return Health(os.path.join(translate('special://profile/addon_data/service.kodi.ios.bootstrap'), 'sports-source-health.json'), clock)
    except Exception:
        return Health(None, clock)
