"""Which Umbrella sources open fast on this phone, and which ones died (owner, 2026-11-20: a stream took 20 s to open).

Build 617's log: the chosen source's debrid server needed 5 s or more before its first byte and then delivered 0.2 MB/s, so the app's cache wait gave up
after 5 s and Kodi's own open then took another 7.5 s. Nothing the app does can speed one server up; what it can do is stop choosing slow ones. Each
time an Umbrella source is played, the time from choosing it to Kodi having the streams ready is remembered against its debrid service and provider
(labels only, never a link or a name), a source that never opened is remembered as failed, and the version page lists the sources of a quality fastest
first (ties keep Umbrella's own order). Unknown sources are not penalised: a new one is tried on its merits, a cached one a little ahead of an unchecked one.
"""
import json
import os
import tempfile
import time

PICK = 'KodiIOS.UmbrellaPick'
PICK_FILE = 'KodiIOS.OpenSourceFile'   # the picked source's file fingerprint, left by settle() for the late verdict (first picture, or none)
BAD_FOR = 6 * 3600.0                  # a file that never put a picture up, or took 25 s or more, is ranked last for this long
LATE_SLOW = 25.0
FRESH = 6 * 3600.0
KEEP = 60
SAMPLES = 5


import hashlib


def fingerprint(item):
    """A short fingerprint of the source's file name (the same file on the same service has the same name): '' when it has none. Never the name itself."""
    name = str((item or {}).get('name') or '').strip().lower()
    return hashlib.sha1(name.encode('utf-8')).hexdigest()[:10] if name else ''


def key(item):
    """'alldebrid|torrentio' for a source item (Umbrella's dict), '' when it names neither."""
    debrid = str((item or {}).get('debrid') or '').strip().lower()
    provider = str((item or {}).get('provider') or '').strip().lower()
    return '%s|%s' % (debrid, provider) if debrid or provider else ''


class Speed:
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
        if len(self.data) > KEEP:
            bad = self.data.pop('_bad', None)
            newest = sorted(self.data, key=lambda k: -max(self.data[k].get('ok_at', 0), self.data[k].get('fail_at', 0)))
            self.data = {k: self.data[k] for k in newest[:KEEP]}
            if bad:
                self.data['_bad'] = bad
        try:
            folder = os.path.dirname(self.path) or '.'
            os.makedirs(folder, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=folder)
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                json.dump(self.data, out, separators=(',', ':'))
            os.replace(temp, self.path)
        except OSError:
            pass

    def ok(self, name, seconds):
        """The source opened: `seconds` from choosing it to the streams being ready."""
        if not name:
            return
        item = self.data.setdefault(name, {})
        item['lat'] = (item.get('lat') or [])[-(SAMPLES - 1):] + [round(float(seconds), 1)]
        item['ok_at'] = self.clock()
        self._save()

    def fail(self, name):
        if not name:
            return
        item = self.data.setdefault(name, {})
        item['fail_at'] = self.clock()
        self._save()

    def bad(self, fp):
        """This file (fingerprint) did not put a picture up in time, or took LATE_SLOW seconds or more: it goes last in the version list for BAD_FOR. Owner, 2026-11-25 (build 698
        log f12dfcdd: one file read at 0.8 MB/s, stalled for minutes, and its source kept ranking first because the speed was only measured up to "streams ready")."""
        if not fp:
            return
        marks = self.data.setdefault('_bad', {})
        marks[fp] = self.clock()
        if len(marks) > KEEP:
            self.data['_bad'] = dict(sorted(marks.items(), key=lambda kv: -kv[1])[:KEEP])
        self._save()

    def is_bad(self, fp):
        at = (self.data.get('_bad') or {}).get(fp) if fp else None
        return at is not None and 0 <= self.clock() - float(at) < BAD_FOR

    def score(self, name, cached=False):
        """Higher is better. Fast and recent beats slow; a recent failure outweighs a good past; unknown is 0 (a cached one 0.5)."""
        item = self.data.get(name) or {}
        total = 0.5 if cached else 0.0
        lat = sorted(item.get('lat') or [])
        if lat:
            median = lat[len(lat) // 2]
            fade = max(0.0, 1 - (self.clock() - item.get('ok_at', 0)) / FRESH)
            total += (2.0 - min(median, 30.0) / 10.0) * (.4 + .6 * fade)   # 2 s opens +1.8, 13 s +0.7, 25 s -0.5, fading to 40 % after 6 h
        if item.get('fail_at') and item['fail_at'] > item.get('ok_at', 0):
            total -= 3.0 * max(0.0, 1 - (self.clock() - item['fail_at']) / FRESH)
        return total

    def order(self, pairs, cached=lambda item: False):
        """Source items fastest first; stable, so equal scores keep Umbrella's order. `pairs` is [(position, item)]."""
        return sorted(pairs, key=lambda pair: -(self.score(key(pair[1]), cached(pair[1])) - (10.0 if self.is_bad(fingerprint(pair[1])) else 0.0)))


def open_store(translate=None, clock=time.time):
    try:
        if translate is None:
            import xbmcvfs
            translate = xbmcvfs.translatePath
        return Speed(os.path.join(translate('special://profile/addon_data/service.kodi.ios.bootstrap'), 'umbrella-source-speed.json'), clock)
    except Exception:
        return Speed(None, clock)


def picked(window, item, now=None):
    """The viewer chose this source: remember which and when, so the open that follows can be credited to it."""
    try:
        name = key(item)
        if name:
            window.setProperty(PICK, json.dumps({'k': name, 'f': fingerprint(item), 't': time.time() if now is None else now}))
    except Exception:
        pass


def settle(window, store, ok, now=None, within=180.0):
    """An Umbrella open finished (`ok`: the streams were ready) or gave up: credit the source chosen just before. Returns (source label, seconds), or None."""
    try:
        raw = window.getProperty(PICK)
        if not raw:
            return None
        window.clearProperty(PICK)
        info = json.loads(raw)
        window.setProperty(PICK_FILE, str(info.get('f') or ''))
        now = time.time() if now is None else now
        seconds = now - float(info['t'])
        if seconds < 0 or seconds > within:
            return None
        if ok:
            store.ok(info['k'], seconds)
            return info['k'], seconds
        store.fail(info['k'])
        return info['k'], None
    except Exception:
        pass
    return None
