"""Bounded, lazy movie/episode backups for the existing source picker.

Provider code runs in separate Kodi interpreters. Signed links/native resolver payloads only
cross owner-only temporary files; diagnostics contain provider names and counts, never URLs.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
import urllib.parse

import source_contract

PROVIDERS = ('jacktook', 'pov', 'otaku', 'thecrew', 'prism')
ADDONS = {'jacktook': 'plugin.video.jacktook', 'pov': 'plugin.video.pov',
          'otaku': 'plugin.video.otaku', 'thecrew': 'plugin.video.thecrew', 'prism': 'plugin.video.prism'}
INDEPENDENT = ('local',)   # first-party search that needs no add-on (independent_search.py); not in the add-on loop
TOTAL_SECONDS = 60
PROVIDER_SECONDS = 12
RESOLVE_SECONDS = 15
MAX_CANDIDATES = 200
MAX_JOB_BYTES = 2 * 1024 * 1024
QUALITY = {'2160p': '4k', 'uhd': '4k', '4k': '4k', '1440p': '1440p',
           '1080p': '1080p', '720p': '720p', '576p': '480p', '480p': '480p', 'sd': 'sd'}


class Canceled(RuntimeError):
    pass


Cancelled = Canceled


def _check(cancel, deadline, clock=time.monotonic):
    if cancel and cancel():
        raise Canceled('Source search canceled')
    if clock() >= deadline:
        raise TimeoutError('Source search deadline reached')


def note(provider, status, count=0):
    try:
        import xbmc
        if provider not in PROVIDERS + INDEPENDENT:
            provider = 'primary'
        if status not in ('search', 'ready', 'unconfigured', 'resolve', 'resolved') + source_contract.OUTCOMES:
            status = 'offline'
        xbmc.log('Kodi iOS provider fallback: provider=%s status=%s count=%d' %
                 (provider, status, max(0, int(count))), xbmc.LOGINFO)
    except Exception:
        pass


def request_from_expected(exp, purpose='stream', profile=None):
    exp = dict(exp or {})
    titles = list(exp.get('titles') or [])
    request = {'media_type': 'movie' if exp.get('kind') == 'movie' else 'episode',
               'title': titles[0] if titles else '', 'aliases': titles[1:],
               'show_title': titles[0] if titles and exp.get('kind') != 'movie' else '',
               'year': exp.get('year') if exp.get('kind') == 'movie' else exp.get('show_year'),
               'tmdb': exp.get('tmdb'), 'imdb': exp.get('imdb'), 'tvdb': exp.get('tvdb'),
               'season': exp.get('season'), 'episode': exp.get('episode'),
               'expected': exp, 'purpose': purpose, 'profile': dict(profile or {})}
    request['quality'] = request['profile'].get('quality') or ''
    if exp.get('anime_mapping'):
        request['anime_mapping'] = exp['anime_mapping']
    if exp.get('kind') == 'anime' or exp.get('anime'):
        request['anime'] = True
    return request


def expected(request):
    import source_match
    exp = request.get('expected')
    if exp and exp.get('titles'):
        return exp
    movie = request.get('media_type') == 'movie'
    title = request.get('title') if movie else request.get('show_title') or request.get('title')
    return source_match.expected('movie' if movie else 'episode',
        [title] + list(request.get('aliases') or []), year=request.get('year') if movie else None,
        show_year=request.get('year') if not movie else None, imdb=request.get('imdb'), tmdb=request.get('tmdb'),
        season=request.get('season'), episode=request.get('episode'))


def eligible(request):
    if request.get('media_type') not in ('movie', 'episode'):
        return False
    exp = expected(request)
    if not exp.get('titles'):
        return False
    if request['media_type'] == 'episode':
        try:
            return int(exp.get('season')) >= 0 and int(exp.get('episode')) > 0
        except (TypeError, ValueError):
            return False
    return bool(exp.get('year') or exp.get('imdb') or exp.get('tmdb'))


def normalize(candidate, provider):
    if provider not in PROVIDERS + INDEPENDENT or not isinstance(candidate, dict):
        return None
    name = str(candidate.get('name') or '').strip()
    if not name or len(name) > 2048:
        return None
    quality = QUALITY.get(str(candidate.get('quality') or '').lower())
    if not quality:
        found = re.search(r'(?i)(2160p|1440p|1080p|720p|480p|4k)', name)
        quality = QUALITY.get(found.group(1).lower()) if found else 'sd'
    try:
        size = float(candidate.get('size') or 0)
        seeds = int(candidate.get('seeders') or 0)
        if not math.isfinite(size) or size < 0 or seeds < 0:
            return None
        # Only JSON primitives cross the isolated interpreter boundary.
        json.dumps(candidate, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        return None
    if not any(candidate.get(k) for k in ('resolver', 'url', 'torrent_hash')):
        return None
    item = dict(candidate, provider=provider, name=name, quality=quality, size=size, seeders=seeds)
    ident = candidate.get('torrent_hash') or candidate.get('url') or name
    item['_id'] = hashlib.sha256((provider + ':' + str(ident)).encode()).hexdigest()[:24]
    return item


def verified(candidates, request, provider):
    import source_match
    exp = expected(request)
    if not exp.get('titles'):
        return []
    wanted = QUALITY.get(str(request.get('quality') or (request.get('profile') or {}).get('quality') or '').lower())
    strict = bool((request.get('profile') or {}).get('strict_quality'))
    excluded = set(request.get('excluded_names') or [])
    kept, seen = [], set()
    for candidate in list(candidates or [])[:MAX_CANDIDATES]:
        item = normalize(candidate, provider)
        if item is None or item['name'] in excluded or (strict and wanted and item['quality'] != wanted):
            continue
        identity = exp
        if provider == 'otaku':
            origin = (item.get('resolver') or {}).get('request') or {}
            mapping = origin.get('anime_mapping') or {}
            if mapping.get('source') == 'otaku-db+tmdb-episode+ani.zip' and mapping.get('verified') is True:
                try:
                    same = all(str(mapping.get(k)) == str(request.get(k)) == str(origin.get(k))
                               for k in ('tmdb', 'season', 'episode'))
                    absolute = int(mapping.get('absolute_episode') or 0)
                    if not same or absolute <= 0 or int(mapping.get('mal_id') or 0) <= 0: continue
                    identity = source_match.expected('anime', [mapping.get('title')] + exp['titles'],
                        season=mapping.get('anime_season') if mapping.get('anime_season') is not None else exp.get('season'),
                        episode=absolute, absolute=absolute, tmdb=exp.get('tmdb'), imdb=exp.get('imdb'))
                except (TypeError, ValueError):
                    continue
        ok, _ = source_match.check(item['name'], identity, result=item)
        if not ok or item['_id'] in seen:
            continue
        # Uncached torrents need peers; direct and cached links do not have a seed count.
        if item.get('torrent_hash') and not item.get('url') and not item.get('cached') and not item['seeders']:
            continue
        seen.add(item['_id'])
        kept.append(item)
    return kept


def search(request, primary='elementum', cancel=None, timeout=TOTAL_SECONDS, transport=None, exclude=(), clock=time.monotonic, independent=None):
    """Called only after primary failure/empty results. First usable backup wins; success remains lazy."""
    if not eligible(request):
        return []
    transport = transport or KodiTransport()
    deadline = clock() + max(0, float(timeout))
    skipped = set(exclude) | {primary}
    for provider in PROVIDERS:
        _check(cancel, deadline, clock)
        if provider in skipped or (provider == 'otaku' and request.get('media_type') != 'episode'):
            continue
        if not transport.available(provider):
            note(provider, 'unconfigured')
            continue
        note(provider, 'search')
        try:
            values = transport.search(provider, request, min(deadline, clock() + PROVIDER_SECONDS), cancel)
            _check(cancel, deadline, clock)
            found = verified(values, request, provider)
        except Canceled:
            note(provider, 'canceled')
            raise
        except Exception as error:
            _check(cancel, deadline, clock)
            # One typed outcome per failure (source_contract.classify never reads the message, so no link can leak).
            note(provider, source_contract.classify(error))
            continue
        note(provider, 'ready' if found else 'empty', len(found))
        if found:
            return found
    return _independent(request, independent, transport, cancel, deadline, skipped, clock)


def _independent(request, search_fn, transport, cancel, deadline, skipped, clock):
    """Last resort once every add-on backup came back empty or failed: the first-party site search (independent_search).
    Only with the real transport unless a function is given, so tests never touch the network."""
    if search_fn is None and isinstance(transport, KodiTransport):
        import independent_sites
        search_fn = lambda request, cancel=None, timeout=0: independent_sites.search_all(request, cancel=cancel, timeout=timeout)[:2]
    if search_fn is None or 'local' in skipped:
        return []
    _check(cancel, deadline, clock)
    note('local', 'search')
    outcome, found = search_fn(request, cancel=cancel, timeout=max(.5, deadline - clock()))
    note('local', 'ready' if found else outcome, len(found))
    if outcome == 'canceled':
        raise Canceled('Source search canceled')
    return found


def safe_url(value):
    """Only the existing movie transport schemes; never execute arbitrary plugin/script/file URLs."""
    if isinstance(value, dict):
        headers = value.get('headers') or {}
        raw = str(value.get('url') or '')
        if not isinstance(headers, dict):
            raise ValueError('Invalid stream headers')
        if any('\r' in str(k) + str(v) or '\n' in str(k) + str(v) for k, v in headers.items()):
            raise ValueError('Invalid stream headers')
        if headers:
            raw += ('&' if '|' in raw else '|') + urllib.parse.urlencode(headers)
    else:
        raw = str(value or '')
    if len(raw) > 65536 or any(c in raw for c in ('\r', '\n', '\x00')):
        raise ValueError('Invalid stream address')
    parsed = urllib.parse.urlsplit(raw.partition('|')[0])
    if '|' in raw:
        for key, value in urllib.parse.parse_qsl(raw.partition('|')[2], keep_blank_values=True):
            if any(c in key + value for c in ('\r', '\n', '\x00')):
                raise ValueError('Invalid stream headers')
    if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
        return raw
    if parsed.scheme == 'magnet':
        hashes = urllib.parse.parse_qs(parsed.query).get('xt', [])
        if any(re.fullmatch(r'urn:btih:(?:[0-9a-fA-F]{40}|[a-zA-Z2-7]{32})', h) for h in hashes):
            return raw
    raise ValueError('Provider did not return a supported media source')


def resolve(candidate, request, cancel=None, transport=None, timeout=RESOLVE_SECONDS, clock=time.monotonic):
    provider = candidate.get('provider')
    if not verified([candidate], request, provider):
        raise ValueError('Source does not match this movie or episode')
    transport = transport or KodiTransport()
    deadline = clock() + max(0, float(timeout))
    _check(cancel, deadline, clock)
    note(provider, 'resolve')
    if provider in INDEPENDENT:
        result = candidate.get('magnet') or ''       # no add-on to ask: the hash is the handle
    else:
        result = transport.resolve(provider, candidate, request, deadline, cancel)
    _check(cancel, deadline, clock)
    result = safe_url(result)
    if request.get('purpose') == 'stream' and result.startswith('magnet:'):
        # This app intercepts Elementum play routes as downloads. Never turn Stream into an implicit download.
        raise ValueError('Streaming requires a resolved media link')
    probe = getattr(transport, 'probe', None)
    if probe is not None and result.startswith(('http://', 'https://')):
        probe(result, deadline, cancel)
        _check(cancel, deadline, clock)
    note(provider, 'resolved')
    return result


def picker_items(candidates):
    import umbrella_picker
    labels = []
    for c in candidates:
        # The Deck's existing parser/ranker is shared with Elementum and Umbrella.
        item = {'name': c['name'], 'quality': c['quality'], 'size': c.get('size', 0),
                'seeders': c.get('seeders') or (1 if c.get('cached') or c.get('url') else 0),
                'provider': c['provider'], 'info': c.get('info') or '',
                'source': 'CACHED' if c.get('cached') or c.get('url') else 'torrent',
                'debrid': c.get('debrid') or ('backup' if c.get('url') else '')}
        labels.append(umbrella_picker.label(item))
    return labels


def write_private(path, data):
    path = Path(path)
    encoded = json.dumps(data, allow_nan=False).encode()
    if len(encoded) > MAX_JOB_BYTES:
        raise ValueError('Provider response exceeds its limit')
    temp = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(encoded)
        os.replace(temp, path)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass


class KodiTransport:
    """A bounded, cancelable owner-only file mailbox; one fresh RunScript interpreter per provider call."""
    def __init__(self, profile=None, launch=None, wait=None, clock=time.monotonic):
        import xbmc, xbmcvfs
        self.xbmc = xbmc
        self.profile = profile or xbmcvfs.translatePath('special://profile/')
        self.root = Path(self.profile) / 'addon_data/service.kodi.ios.bootstrap/provider-fallback-jobs'
        self.launch = launch or xbmc.executebuiltin
        self.wait = wait or xbmc.Monitor().waitForAbort
        self.clock = clock

    def available(self, provider):
        return bool(self.xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % ADDONS[provider]))

    def search(self, provider, request, deadline, cancel):
        return self.call(provider, 'search', request, None, deadline, cancel)

    def resolve(self, provider, candidate, request, deadline, cancel):
        return self.call(provider, 'resolve', request, candidate, deadline, cancel)

    def probe(self, url, deadline, cancel):
        """Reject an offline resolved link before handing it to playback; never fetch the media body."""
        import urllib.request, urllib.error
        raw, _, extra = url.partition('|')
        headers = dict(urllib.parse.parse_qsl(extra))
        class Redirect(urllib.request.HTTPRedirectHandler):
            max_redirections = 6
            def redirect_request(self, request, fp, code, message, answer_headers, target):
                old, new = urllib.parse.urlsplit(request.full_url), urllib.parse.urlsplit(target)
                if new.scheme not in ('http', 'https') or (old.scheme == 'https' and new.scheme != 'https'):
                    raise ConnectionError('Unsafe media redirect')
                fresh = super().redirect_request(request, fp, code, message, answer_headers, target)
                if fresh is not None and (old.scheme, old.hostname, old.port) != (new.scheme, new.hostname, new.port):
                    for key in list(fresh.headers):
                        if key.lower() in ('authorization', 'cookie', 'host'): fresh.remove_header(key)
                return fresh
        opener = urllib.request.build_opener(Redirect)
        result, responses = {}, []
        finished = threading.Event()
        def run():
            try:
                for method in ('HEAD', 'GET'):
                    try:
                        request = urllib.request.Request(raw, headers=dict(headers, Range='bytes=0-0'), method=method)
                        response = opener.open(request, timeout=max(.001, min(3, deadline-self.clock())))
                        responses.append(response)
                        with response:
                            if response.getcode() not in (200, 206): raise ConnectionError('Source unavailable')
                            if 'text/html' in response.headers.get('Content-Type', '').lower():
                                raise ConnectionError('Source returned a web page')
                        return
                    except urllib.error.HTTPError as error:
                        error.close()
                        if method != 'HEAD' or error.code not in (403, 405, 501): raise
            except Exception as error:
                result['error'] = error
            finally:
                finished.set()
        threading.Thread(target=run, daemon=True).start()
        try:
            while not finished.wait(.025): _check(cancel, deadline, self.clock)
            _check(cancel, deadline, self.clock)
            if 'error' in result: raise ConnectionError('Resolved source is unavailable') from None
        finally:
            for response in responses:
                try: response.close()
                except Exception: pass

    def call(self, provider, operation, request, candidate, deadline, cancel):
        _check(cancel, deadline, self.clock)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        ident = secrets.token_hex(16)
        folder = self.root / ident
        folder.mkdir(mode=0o700)
        try:
            write_private(folder / 'request.json', {'provider': provider, 'operation': operation,
                'request': request, 'candidate': candidate, 'deadline': deadline})
            # No media metadata, source URL or credentials enter a Kodi builtin command.
            self.launch('RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/provider_worker.py,%s)' % ident)
            output = folder / 'result.json'
            while not output.exists():
                _check(cancel, deadline, self.clock)
                if self.wait(min(.05, max(0, deadline - self.clock()))):
                    raise Canceled('Source search canceled')
            _check(cancel, deadline, self.clock)
            if output.stat().st_size > MAX_JOB_BYTES:
                raise ValueError('Provider response exceeds its limit')
            answer = json.loads(output.read_text())
            if answer.get('status') == 'canceled':
                raise Canceled('Source search canceled')
            if answer.get('status') == 'timeout':
                raise TimeoutError('Provider source search timed out')
            if answer.get('status') != 'ok':
                raise RuntimeError('Provider unavailable')
            return answer.get('value') or ([] if operation == 'search' else '')
        finally:
            # Workers treat a removed mailbox as cancellation and cannot recreate it for a late reply.
            shutil.rmtree(folder, ignore_errors=True)


def queue_download(candidate, url, request, auto=None, cancel=None):
    """Persist a selected HTTP backup using the same Drive copy queue and automatic receipt contract."""
    if cancel and cancel():
        raise Canceled('Source search canceled')
    if not verified([candidate], request, candidate.get('provider')):
        raise ValueError('Source does not match this movie or episode')
    url = safe_url(url)
    if not url.startswith(('http://', 'https://')):
        raise ValueError('This source uses the torrent download route')
    import xbmcgui, xbmcvfs, debrid_drive
    home = xbmcgui.Window(10000)
    watch = bool((auto or {}).get('mode') == 1)
    if auto is None:
        import elementum_cloud, transfer_control
        profile = xbmcvfs.translatePath('special://profile/')
        held = transfer_control.paused(profile, 'up')
        rows = [('Download now', 'Uploads resume'), ('Download and watch', 'Uploads resume; plays when ready'),
                ('Keep it queued', 'Uploads stay paused')] if held else [
                ('Download only', 'Saved to Google Drive · watch any time'),
                ('Download and watch', 'Plays as soon as it is ready on Drive')]
        mode = elementum_cloud.ask(xbmcgui.Dialog(), 'Uploads are paused' if held else 'Save to Google Drive', rows)
        if mode < 0: raise Canceled('Download canceled')
        if held and mode in (0, 1): transfer_control.set_paused(profile, 'up', False)
        watch = mode == 1
    def owned():
        if cancel and cancel(): return False
        if not auto: return True
        import episode_watch
        current = episode_watch.active_request(home, lane=str(auto.get('_lane') or ''))
        return bool(current and current.get('request_id') == auto.get('request_id')
                    and all(str((current.get('target') or {}).get(k) or '') == str(request.get(k) or '')
                            for k in ('tmdb', 'season', 'episode'))
                    and not episode_watch.canceled(home, current.get('target') or {}))
    if not owned(): raise Canceled('Source request no longer owns this download')
    profile = xbmcvfs.translatePath('special://profile/')
    job = debrid_drive.queue_direct(profile, url, candidate, request, watch=watch, cancel=lambda:not owned())
    if not job:
        return False
    if auto:
        if auto.get('batch'):
            debrid_drive.tag(profile, job, batch=auto['batch'])
        xbmcgui.Window(10000).setProperty('KodiIOS.AutoPick.Queued' + str(auto.get('_lane') or ''),
            json.dumps({'request_id': auto.get('request_id'), 'queued': True}))
    return True
