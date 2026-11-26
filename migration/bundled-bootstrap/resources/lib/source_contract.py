"""Typed contract for the independent backup sources (roadmap step 4): outcomes, expiry, capabilities and redaction.

Plain Python, no Kodi imports. Identity checks stay in source_match / provider_fallback.verified; this module adds what
those leave implicit: one closed set of outcomes, how an error becomes one, when a resolver handle is stale, which
capabilities a candidate declares, and the form a candidate may take on disk or in a log (never a link, header or token).
"""
import socket
import time

EMPTY, OFFLINE, TIMEOUT, UNSUPPORTED = 'empty', 'offline', 'timeout', 'unsupported'
ACCOUNT_REQUIRED, REFUSED, EXPIRED, CANCELED = 'account-required', 'refused', 'expired', 'canceled'
OK = 'ok'
OUTCOMES = (OK, EMPTY, OFFLINE, TIMEOUT, UNSUPPORTED, ACCOUNT_REQUIRED, REFUSED, EXPIRED, CANCELED)
CAPABILITIES = ('stream', 'download', 'cached', 'torrent', 'subtitles')
DEFAULT_TTL = 1800
MAX_TTL = 6 * 3600
# Fields that may be persisted or logged. Everything else (url, headers, resolver payloads, tokens, cookies) is dropped.
PERSISTENT = ('_id', 'provider', 'name', 'quality', 'size', 'seeders', 'cached', 'transport', 'capabilities', 'expires_at')


class Outcome(Exception):
    """A typed failure raised by an adapter; `kind` is one of OUTCOMES."""
    def __init__(self, kind, detail=''):
        super().__init__(kind)
        self.kind = kind if kind in OUTCOMES else OFFLINE


def classify(error):
    """Map any exception to one outcome. The message is never read, so a URL in it cannot leak."""
    if isinstance(error, Outcome):
        return error.kind
    name = type(error).__name__
    if name in ('Canceled', 'Cancelled', 'CancelledError', 'KeyboardInterrupt'):
        return CANCELED
    if isinstance(error, (TimeoutError, socket.timeout)):
        return TIMEOUT
    status = getattr(error, 'code', None) or getattr(error, 'status', None)
    if status in (401, 402, 407):
        return ACCOUNT_REQUIRED
    if status in (403, 429, 451):
        return REFUSED
    if status in (404, 410):
        return EXPIRED
    if isinstance(error, (ConnectionError, OSError)):
        return OFFLINE
    if isinstance(error, (ValueError, TypeError, KeyError)):
        return UNSUPPORTED
    return OFFLINE


def search_outcome(found, error=None):
    if error is not None:
        return classify(error)
    return OK if found else EMPTY


def capabilities(candidate):
    """What this candidate can do, from facts it carries; never from what a provider claims about itself."""
    caps = set()
    if candidate.get('url') or candidate.get('cached') or candidate.get('resolver'):
        caps.add('stream')
    if candidate.get('torrent_hash'):
        caps.update(('torrent', 'download'))
    if candidate.get('cached'):
        caps.add('cached')
    if candidate.get('url') and not str(candidate.get('url')).startswith('magnet:'):
        caps.add('download')
    return tuple(c for c in CAPABILITIES if c in caps)


def expiry(candidate, now=None, ttl=None):
    """Absolute expiry time. A provider-given `expires_at` wins but is capped, so a bogus far-future value cannot pin a handle."""
    now = time.time() if now is None else now
    try:
        given = float(candidate.get('expires_at'))
    except (TypeError, ValueError):
        given = 0
    if given > 0:
        return min(given, now + MAX_TTL)
    return now + (DEFAULT_TTL if ttl is None else max(0, min(float(ttl), MAX_TTL)))


def expired(candidate, now=None):
    now = time.time() if now is None else now
    try:
        return not float(candidate.get('expires_at')) > now   # NaN counts as expired
    except (TypeError, ValueError):
        return True


def stamp(candidate, now=None, ttl=None):
    """A normalized candidate plus its capabilities and expiry."""
    item = dict(candidate)
    item['capabilities'] = capabilities(item)
    item['expires_at'] = expiry(item, now, ttl)
    return item


def redact(candidate):
    """The only form allowed in logs and on disk: no link, no header, no resolver payload."""
    return {k: candidate[k] for k in PERSISTENT if k in candidate}


def check_usable(candidate, request, now=None):
    """Raise Outcome unless this candidate may reach playback for this request: expiry, capability, then identity."""
    import provider_fallback
    if not provider_fallback.eligible(request):
        raise Outcome(UNSUPPORTED)      # no year or id for a film, no season/episode for a show: nothing can be matched
    if expired(candidate, now):
        raise Outcome(EXPIRED)
    needed = 'download' if request.get('purpose') == 'download' else 'stream'
    if needed not in (candidate.get('capabilities') or capabilities(candidate)):
        raise Outcome(UNSUPPORTED)
    if not provider_fallback.verified([candidate], request, candidate.get('provider')):
        raise Outcome(UNSUPPORTED)
    return candidate
