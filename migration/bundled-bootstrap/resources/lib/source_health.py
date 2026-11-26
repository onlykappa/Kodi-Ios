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


MIN_WAIT = 30
MAX_WAIT = 6 * 3600


def retry_after(error):
    """Seconds a server asked us to wait (Retry-After as a whole number), or 0. Only the header is read, never the message."""
    try:
        value = int(str(getattr(error, 'headers', {}).get('Retry-After', '')).strip())
    except (AttributeError, ValueError, TypeError):
        return 0
    return max(0, value)


class Health:
    def __init__(self, path='', clock=time.time, post=None):
        self.path, self.clock, self.post = path, clock, post     # post(kind, title, text): the app's notice list (notices.note)
        self.data = self._load()
        self.last_notice = 0

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

    def record(self, source, outcome, wait=0):
        """Count an outcome for a source. Canceled, empty and expired change nothing; ok clears failures."""
        if outcome == source_contract.CANCELED or outcome not in source_contract.OUTCOMES:
            return
        now, entry = self.clock(), self.data.setdefault(str(source), {})
        if outcome == source_contract.OK:
            entry.update(ok=now, fails=0, until=0, kind='')
        elif outcome in COOLDOWN:
            fails = int(entry.get('fails', 0)) + 1
            steps = COOLDOWN[outcome]
            span = steps[min(fails, len(steps)) - 1]
            if wait and outcome in (source_contract.REFUSED, source_contract.OFFLINE, source_contract.TIMEOUT):
                span = max(MIN_WAIT, min(MAX_WAIT, wait))        # the server said how long: honour that, not our table
            entry.update(failed=now, fails=fails, kind=outcome, until=now + span, said=0)
        self._save()
        self.tell()

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

    NOTICE_EVERY = 1800

    def tell(self, now=None):
        """One calm line in the Notifications list when a source starts resting: once per cooldown, at most one every 30 minutes, never a popup,
        never a name list longer than three, no link or error text. Does nothing without a `post`."""
        if self.post is None:
            return None
        now = self.clock() if now is None else now
        new = sorted(k for k, v in self.data.items() if v.get('until', 0) > now and not v.get('said') and ':' not in k)
        if not new or now - self.last_notice < self.NOTICE_EVERY:
            return None
        names = [n.replace('-', ' ').title() if n.islower() else n for n in new]
        shown = ', '.join(names[:3]) + (' and %d more' % (len(names) - 3) if len(names) > 3 else '')
        minutes = max(1, int(min(self.data[k]['until'] for k in new) - now) // 60 + 1)
        title = 'A source is resting' if len(new) == 1 else 'Some sources are resting'
        text = '%s did not answer. Others are used, and it is tried again in about %d min.' % (shown, minutes)
        for k in new:
            self.data[k]['said'] = 1
        self.last_notice = now
        self._save()
        try:
            self.post('info', title, text)
        except Exception:
            pass
        return title, text

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
        post = None
        try:
            import notices
            post = notices.note
        except Exception:
            post = None
        return Health(os.path.join(str(profile), NAME), post=post)
    except Exception:
        return Health('')


class FamilyHealth:
    """The Sports router's own per-stream health (sports_stream_health) plus a shared cooldown per source family ("Crew 720" -> family Crew):
    every ok/fail is also recorded as `sports:<family>`, and a family cooling down is tried after the others (never dropped: a live game
    may have few sources, and the person's own pick still leads)."""
    def __init__(self, inner, shared):
        self.inner, self.shared = inner, shared

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @staticmethod
    def family(name):
        return 'sports:' + (str(name).split() or ['sports'])[0].lower()

    def ok(self, name, stats=None):
        self.inner.ok(name, stats)
        self.shared.record(self.family(name), source_contract.OK)

    def fail(self, name, reason=''):
        self.inner.fail(name, reason)
        kind = source_contract.TIMEOUT if 'no picture' in str(reason) else source_contract.OFFLINE
        self.shared.record(self.family(name), kind)

    def order(self, choices, key=None, quality=None, first=None):
        ranked = self.inner.order(choices, key=key, quality=quality, first=first)
        cooling = [c for c in ranked if c is not first and self.shared.state(self.family(key(c) if key else c)) == 'cooldown']
        return [c for c in ranked if c not in cooling] + cooling
