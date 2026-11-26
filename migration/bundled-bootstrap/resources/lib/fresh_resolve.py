"""Fresh resolution of a backup candidate right before playback (roadmap step 6). Plain Python, no Kodi imports.

resolve_fresh() asks the provider's own resolver for a new link at the moment of use (never a saved one), then
verify_chain() fetches the master playlist, a variant, a segment and the key with one session, so the cookies and headers the
provider requires reach every request. Failures are source_contract outcomes: 401/402 account-required, 403/429 refused,
404/410 expired (one re-resolve is tried), timeouts timeout. Links, headers and cookies are never logged or stored; `Resolved`
hides them from repr, and `scrub()` removes any URL from text that must be logged.
"""
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import provider_fallback
import source_contract

MAX_REDIRECTS = 6
MAX_PLAYLIST = 1 << 20
CHAIN_SECONDS = 12
URL = re.compile(r'(?i)\b(?:https?|magnet):[^\s\'"<>]+')
TOKENISH = re.compile(r'(?i)(token|key|sig|signature|auth|session|cookie)=[^&\s]+')


def scrub(text):
    """For logs: URLs and token-looking parameters removed."""
    return TOKENISH.sub(r'\1=…', URL.sub('<link>', str(text)))


class Resolved:
    """A fresh link with its required headers. Not printable, not copyable into logs by accident."""
    __slots__ = ('url', 'headers', 'made_at', 'ttl')

    def __init__(self, url, headers, made_at, ttl=source_contract.DEFAULT_TTL):
        self.url, self.headers, self.made_at, self.ttl = url, dict(headers), made_at, ttl

    def __repr__(self):
        return '<Resolved %s headers=%d>' % ('hls' if '.m3u8' in self.url.partition('?')[0].lower() else 'link', len(self.headers))

    __str__ = __repr__

    def stale(self, now):
        return now >= self.made_at + self.ttl


def split(raw):
    """'url|Header=value&…' (what provider_fallback.safe_url returns) -> (url, headers)."""
    url, _, extra = raw.partition('|')
    return url, dict(urllib.parse.parse_qsl(extra, keep_blank_values=True))


class _Redirect(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if new.scheme not in ('http', 'https') or (old.scheme == 'https' and new.scheme != 'https'):
            raise urllib.error.URLError('unsafe redirect')
        fresh = super().redirect_request(req, fp, code, msg, headers, newurl)
        if fresh is not None and (old.scheme, old.hostname, old.port) != (new.scheme, new.hostname, new.port):
            for key in list(fresh.headers):                 # credentials never follow a redirect to another host
                if key.lower() in ('authorization', 'cookie', 'host'):
                    fresh.remove_header(key)
        return fresh


class Session:
    """One cookie jar and one header set for master, variant, segment and key requests."""
    def __init__(self, resolved, opener=None):
        self.jar = http.cookiejar.CookieJar()
        self.headers = dict(resolved.headers)
        self.opener = opener or urllib.request.build_opener(_Redirect, urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, url, timeout, limit=MAX_PLAYLIST, byte_range=None):
        headers = dict(self.headers)
        if byte_range:
            headers['Range'] = byte_range
        req = urllib.request.Request(url, headers=headers)
        try:
            with self.opener.open(req, timeout=max(.5, timeout)) as resp:
                return resp.read(limit)
        except urllib.error.HTTPError as error:
            raise source_contract.Outcome(source_contract.classify(error))
        except Exception as error:
            raise source_contract.Outcome(source_contract.classify(error))


def _uris(playlist):
    """Non-comment lines (variants/segments) of an HLS playlist."""
    return [line.strip() for line in playlist.splitlines() if line.strip() and not line.startswith('#')]


MAX_KEYS = 4


def _keys(playlist):
    """Distinct key URIs, in order (a playlist may rotate keys); only the first few are checked."""
    seen = []
    for uri in re.findall(r'#EXT-X-KEY:[^\n]*URI="([^"]+)"', playlist):
        if uri not in seen:
            seen.append(uri)
    return seen[:MAX_KEYS]


def verify_chain(resolved, session=None, clock=time.monotonic, timeout=CHAIN_SECONDS):
    """Fetch master -> variant -> first segment (+ key). Returns a short report with counts only; raises Outcome."""
    session = session or Session(resolved)
    deadline = clock() + timeout
    left = lambda: deadline - clock()
    base = resolved.url
    if '.m3u8' not in base.partition('?')[0].lower():
        session.get(base, left(), limit=1, byte_range='bytes=0-0')       # plain file: the first byte must be readable
        return {'kind': 'file', 'requests': 1}
    page = session.get(base, left()).decode('utf-8', 'replace')
    if not page.lstrip().startswith('#EXTM3U'):
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    requests = 1
    if '#EXT-X-STREAM-INF' in page:
        variants = _uris(page)
        if not variants:
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
        base = urllib.parse.urljoin(base, variants[0])
        page = session.get(base, left()).decode('utf-8', 'replace')
        requests += 1
        if not page.lstrip().startswith('#EXTM3U'):
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
    if re.search(r'#EXT-X-KEY:[^\n]*METHOD=(?!NONE|AES-128)', page):
        raise source_contract.Outcome(source_contract.UNSUPPORTED)        # DRM we cannot honestly open
    segments = _uris(page)
    if not segments:
        raise source_contract.Outcome(source_contract.EMPTY)
    keys = _keys(page)
    for uri in keys:
        session.get(urllib.parse.urljoin(base, uri), left(), limit=64)
        requests += 1
    init = re.search(r'#EXT-X-MAP:[^\n]*URI="([^"]+)"', page)
    if init:                                        # fMP4: the init segment comes before any media segment
        session.get(urllib.parse.urljoin(base, init.group(1)), left(), limit=1, byte_range='bytes=0-0')
        requests += 1
    session.get(urllib.parse.urljoin(base, segments[0]), left(), limit=1, byte_range='bytes=0-0')
    return {'kind': 'hls', 'requests': requests + 1, 'keyed': bool(keys), 'mapped': bool(init)}


def resolve_fresh(candidate, request, transport, cancel=None, clock=time.monotonic, now=time.time):
    """A new, probed link for this candidate. The candidate's own saved link is never reused: the provider resolves again."""
    try:
        raw = provider_fallback.resolve(candidate, request, cancel=cancel, transport=transport)
    except provider_fallback.Canceled:
        raise source_contract.Outcome(source_contract.CANCELED)
    except source_contract.Outcome:
        raise
    except Exception as error:
        raise source_contract.Outcome(source_contract.classify(error))
    url, headers = split(raw)
    return Resolved(url, headers, now())


def play_ready(candidate, request, transport, cancel=None, session_factory=Session, clock=time.monotonic, now=time.time):
    """Resolve, then verify the whole chain. One re-resolve if the link is already dead (expired token); never more."""
    last = None
    for attempt in (0, 1):
        resolved = resolve_fresh(candidate, request, transport, cancel, clock, now)
        try:
            verify_chain(resolved, session_factory(resolved), clock)
            return resolved
        except source_contract.Outcome as outcome:
            last = outcome
            if outcome.kind != source_contract.EXPIRED:
                raise
    raise last
