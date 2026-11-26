"""Bounded local health of each source (roadmap step 11). Plain Python, no Kodi imports.

Records only a source name, an outcome kind and times: never a link, title, header or token. A confirmed failure puts a source in a
cooldown that grows with repeats and expires by itself; a refusal or rate limit (403/429/451) cools longest and is never hammered. A
cancel is never recorded, so cancelling can never penalise or advance a source. A success clears the cooldown and is remembered for a day,
so recent winners are tried first; a source never tried stays `unknown` (never called healthy). `retry(source)` is the deliberate
"try again now". The file is small, bounded and written atomically.
"""
import json
import os
import tempfile
import time

import source_contract

COOLDOWN = {                      # seconds for the 1st, 2nd, 3rd+ consecutive failure of that kind
    source_contract.OFFLINE: (120, 600, 1800),
    source_contract.TIMEOUT: (120, 600, 1800),
    source_contract.REFUSED: (900, 3600, 21600),
    source_contract.ACCOUNT_REQUIRED: (3600, 3600, 21600),
    source_contract.UNSUPPORTED: (21600, 21600, 86400),     # layout changed or unusable result
}
NO_PENALTY = (source_contract.EMPTY, source_contract.EXPIRED, source_contract.CANCELED, source_contract.OK)
RECENT = 24 * 3600
KEEP = 7 * 86400
MAX_ENTRIES = 64
NAME = 'source-health.json'


class Health:
    def __init__(self, path='', clock=time.time):
        self.path, self.clock = path, clock
        self.data = self._load()

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
            return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, dict)} if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self):
        if not self.path:
            return
        now = self.clock()
        live = {k: v for k, v in self.data.items() if now - max(v.get('ok', 0), v.get('failed', 0)) <= KEEP}
        for k in sorted(live, key=lambda k: max(live[k].get('ok', 0), live[k].get('failed', 0)))[:-MAX_ENTRIES]:
            live.pop(k)
        self.data = live
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), prefix='.health-')
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(live, handle)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def record(self, source, outcome):
        """Count an outcome for a source. Canceled, empty and expired change nothing; ok clears failures."""
        if outcome == source_contract.CANCELED or outcome not in source_contract.OUTCOMES:
            return
        now, entry = self.clock(), self.data.setdefault(str(source), {})
        if outcome == source_contract.OK:
            entry.update(ok=now, fails=0, until=0, kind='')
        elif outcome in COOLDOWN:
            fails = int(entry.get('fails', 0)) + 1
            steps = COOLDOWN[outcome]
            entry.update(failed=now, fails=fails, kind=outcome, until=now + steps[min(fails, len(steps)) - 1])
        self._save()

    def state(self, source, now=None):
        """'cooldown' (skip), 'recent' (worked in the last day), or 'unknown' (no news: still eligible, not called healthy)."""
        now = self.clock() if now is None else now
        entry = self.data.get(str(source)) or {}
        if entry.get('until', 0) > now:
            return 'cooldown'
        return 'recent' if entry.get('ok', 0) and now - entry['ok'] <= RECENT and not entry.get('fails') else 'unknown'

    def retry(self, source):
        """The deliberate retry: forget the cooldown now (the failure count stays, so a second failure cools longer)."""
        entry = self.data.get(str(source))
        if entry:
            entry['until'] = 0
            self._save()

    def order(self, sources, now=None, retry=()):
        """Eligible sources: not cooling down (unless asked again), recent winners first by recency, the rest in their given order."""
        now = self.clock() if now is None else now
        sources = [s for s in sources if s in retry or self.state(s, now) != 'cooldown']
        recent = sorted([s for s in sources if self.state(s, now) == 'recent'], key=lambda s: -self.data[str(s)]['ok'])
        return recent + [s for s in sources if s not in recent]

    def report(self, now=None):
        """Names and states only, for a log line."""
        now = self.clock() if now is None else now
        return {k: self.state(k, now) for k in sorted(self.data)}


def default(profile=None):
    """The app's own store, or an in-memory one when there is no profile."""
    try:
        if profile is None:
            import xbmcvfs
            profile = xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')
        return Health(os.path.join(str(profile), NAME))
    except Exception:
        return Health('')
