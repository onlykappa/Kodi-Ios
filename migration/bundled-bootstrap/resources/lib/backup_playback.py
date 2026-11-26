"""Hand a verified backup candidate to the player or the torrent route (roadmap step 7). Plain Python, Kodi imports are lazy.

* http/https (file or HLS): fresh_resolve.play_ready -> player.play, then wait until playback time really advances.
* torrent (magnet / info hash): the info hash is checked against the candidate (and against a .torrent file when one is given),
  then the existing Elementum route is used. Stream is never turned into a download and no torrent traffic starts here:
  the route is the app's own (Elementum download path, which asks the torrent prompt first). No VPN detection is added.
One Playback owns at most one session: a second start for the same request is a no-op, a different one stops the first.
stop() or cancel() before the player was started means it is never started (no late start); stop() closes what this module opened.
"""
import base64
import hashlib
import re
import threading
import time
import urllib.parse

import fresh_resolve
import provider_fallback
import source_contract

START_SECONDS = 20          # playback time must advance within this long after play()
ADVANCE = 1.0               # seconds of playback time that count as "started"
POLL = .25
BTIH = re.compile(r'urn:btih:([0-9a-fA-F]{40}(?![0-9a-zA-Z])|[A-Za-z2-7]{32}(?![0-9a-zA-Z]))')


def _hex(value):
    value = str(value or '').strip()
    if len(value) == 40 and re.fullmatch(r'[0-9a-fA-F]{40}', value):
        return value.lower()
    if len(value) == 32 and re.fullmatch(r'[A-Za-z2-7]{32}', value):
        return base64.b32decode(value.upper()).hex()
    return ''


def magnet_hash(magnet):
    found = BTIH.search(urllib.parse.unquote(str(magnet or '')))
    return _hex(found.group(1)) if found else ''


def _bdecode_span(data, i=0):
    """Return the end index of the bencoded value starting at i (enough to slice out the 'info' dictionary)."""
    c = data[i:i + 1]
    if c == b'i':
        return data.index(b'e', i) + 1
    if c in (b'l', b'd'):
        i += 1
        while data[i:i + 1] != b'e':
            i = _bdecode_span(data, i)
        return i + 1
    if c.isdigit():
        colon = data.index(b':', i)
        return colon + 1 + int(data[i:colon])
    raise ValueError('not bencoded')


def torrent_file_hash(data):
    """SHA-1 of the 'info' dictionary of a .torrent file: its content identity."""
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(b'd'):
        raise ValueError('not a torrent file')
    i = 1
    while data[i:i + 1] != b'e':
        key_end = _bdecode_span(data, i)
        key = data[data.index(b':', i) + 1:key_end]
        value_end = _bdecode_span(data, key_end)
        if key == b'info':
            return hashlib.sha1(bytes(data[key_end:value_end])).hexdigest()
        i = value_end
    raise ValueError('no info dictionary')


def verify_torrent(candidate, torrent_file=None):
    """The hash the candidate claims must equal the magnet's and, when given, the .torrent file's. Raises Outcome(unsupported)."""
    claimed = _hex(candidate.get('torrent_hash'))
    magnet = candidate.get('magnet') or candidate.get('url') or ''
    from_magnet = magnet_hash(magnet) if str(magnet).startswith('magnet:') else ''
    if not claimed and not from_magnet:
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    if claimed and from_magnet and claimed != from_magnet:
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    found = claimed or from_magnet
    if torrent_file is not None:
        try:
            if torrent_file_hash(torrent_file) != found:
                raise source_contract.Outcome(source_contract.UNSUPPORTED)
        except ValueError:
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
    return found


def route_of(candidate):
    """'play' for a direct http(s) link or a resolver handle, 'torrent' for a hash/magnet only, else None."""
    if candidate.get('url') and str(candidate['url']).startswith(('http://', 'https://')) or candidate.get('resolver'):
        return 'play'
    if candidate.get('torrent_hash') or str(candidate.get('magnet') or candidate.get('url') or '').startswith('magnet:'):
        return 'torrent'
    return None


class Playback:
    def __init__(self, player, torrent_route=None, clock=time.monotonic, sleep=time.sleep):
        self.player, self.torrent_route, self.clock, self.sleep = player, torrent_route, clock, sleep
        self.lock = threading.Lock()
        self.current = None          # {'key', 'stop': Event, 'started': bool}

    @staticmethod
    def key(request):
        return tuple(str(request.get(k) or '') for k in ('media_type', 'tmdb', 'imdb', 'title', 'season', 'episode'))

    def stop(self):
        """Stop what this module started. Safe from any thread; a start still resolving will not begin playing."""
        with self.lock:
            cur, self.current = self.current, None
        if cur:
            self._close(cur)
        return bool(cur)

    def _close(self, session):
        session['stop'].set()
        if session['started'] and not session.get('closed'):
            session['closed'] = True
            self.player.stop()

    def _open(self, key):
        """A new session, or None when this key is already running. Replaces (and closes) a different running session."""
        with self.lock:
            if self.current and self.current['key'] == key:
                return None
            old = self.current
            session = self.current = {'key': key, 'stop': threading.Event(), 'started': False}
        if old:
            self._close(old)
        return session

    def start(self, candidate, request, transport=None, cancel=None, resume=0, torrent_file=None):
        """Returns ('playing' | 'sent' | 'duplicate') or raises source_contract.Outcome. Typed failures only."""
        route = route_of(candidate)
        if route is None:
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
        session = self._open(self.key(request))
        if session is None:
            return 'duplicate'
        stopped = lambda: session['stop'].is_set() or (cancel is not None and cancel())
        try:
            if route == 'torrent':
                return self._torrent(candidate, request, torrent_file, stopped)
            return self._play(lambda: fresh_resolve.play_ready(candidate, request, transport, cancel=stopped), stopped, session, resume)
        except provider_fallback.Canceled:
            raise source_contract.Outcome(source_contract.CANCELED)
        except BaseException:
            self._finish(session)
            raise

    def start_resolved(self, key, resolve, cancel=None, resume=0):
        """Same hand-off for a source with its own resolver (live sports): `resolve()` returns a fresh fresh_resolve.Resolved, already verified."""
        session = self._open(('resolved',) + tuple(key))
        if session is None:
            return 'duplicate'
        stopped = lambda: session['stop'].is_set() or (cancel is not None and cancel())
        try:
            return self._play(resolve, stopped, session, resume)
        except provider_fallback.Canceled:
            self._finish(session)
            raise source_contract.Outcome(source_contract.CANCELED)
        except BaseException:
            self._finish(session)
            raise

    def _finish(self, session):
        with self.lock:
            if self.current is session:
                self.current = None
        self._close(session)

    def _torrent(self, candidate, request, torrent_file, stopped):
        if request.get('purpose') == 'stream':
            raise source_contract.Outcome(source_contract.UNSUPPORTED)      # never an implicit download
        source_contract.check_usable(dict(candidate, capabilities=candidate.get('capabilities') or source_contract.capabilities(candidate),
                                          expires_at=candidate.get('expires_at') or source_contract.expiry(candidate)), dict(request, purpose='download'))
        found = verify_torrent(candidate, torrent_file)
        if stopped():
            raise source_contract.Outcome(source_contract.CANCELED)
        magnet = candidate.get('magnet') or candidate.get('url')
        if not str(magnet).startswith('magnet:'):
            magnet = 'magnet:?xt=urn:btih:' + found
        if not self.torrent_route:
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
        if not self.torrent_route(magnet, request):
            raise source_contract.Outcome(source_contract.REFUSED)       # declined at the app's own prompt, or the route refused
        return 'sent'

    def _play(self, resolve, stopped, session, resume):
        resolved = resolve()
        if stopped():                                                       # cancel or stop while resolving: nothing started
            raise source_contract.Outcome(source_contract.CANCELED)
        session['started'] = True
        self.player.play(resolved.url, resolved.headers, resume)
        begin, base = self.clock(), self.player.time()
        while True:
            if stopped():
                raise source_contract.Outcome(source_contract.CANCELED)
            now = self.player.time()
            if now - base >= ADVANCE:
                return 'playing'
            if self.clock() - begin > START_SECONDS:
                raise source_contract.Outcome(source_contract.TIMEOUT)
            self.sleep(POLL)


class KodiPlayer:
    """The real player: one xbmc.Player, headers appended the way the app already does ('url|Header=value'), resume by StartOffset."""
    def __init__(self):
        import xbmc
        self.xbmc, self.player = xbmc, xbmc.Player()

    def play(self, url, headers, resume=0):
        import xbmcgui
        target = url + ('|' + urllib.parse.urlencode(headers) if headers else '')
        item = xbmcgui.ListItem(path=target)
        if resume and resume > 0:
            item.setProperty('StartOffset', str(float(resume)))
        self.player.play(target, item)

    def time(self):
        try:
            return float(self.player.getTime()) if self.player.isPlaying() else 0.0
        except RuntimeError:
            return 0.0

    def stop(self):
        self.player.stop()
