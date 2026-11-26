"""Plays a header- or cookie-guarded HLS stream in Kodi (roadmap step 14 finding). Plain Python, no `requests` needed.

Kodi's player forwards the `url|Header=value` headers only to the first request: the variant playlists, keys and segments of a guarded stream are then
refused (seen on the desktop rig: the master was fetched with the header, nothing after it, and playback never started). The app already has a loopback
HLS proxy for this (sports_hls_proxy.Proxy: opaque local paths, one shared upstream session); this module gives it a standard-library session and decides
when it is needed: an HLS address that comes with headers. Plain files and unguarded HLS are handed to the player as before.
"""
import http.cookiejar
import urllib.error
import urllib.request

import fresh_resolve


class _Response:
    """The few requests.Response members sports_hls_proxy uses."""
    def __init__(self, resp, status, url):
        self._resp, self.status_code, self.url = resp, status, url
        self.headers = {k: v for k, v in resp.headers.items()} if resp is not None else {}

    def iter_content(self, size):
        while self._resp is not None:
            chunk = self._resp.read(size)
            if not chunk:
                break
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self._resp is not None:
            self._resp.close()


class Session:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(fresh_resolve._Redirect, urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, url, headers=None, timeout=(5, 15), stream=True):
        req = urllib.request.Request(url, headers=dict(headers or {}))
        try:
            resp = self.opener.open(req, timeout=max(timeout) if isinstance(timeout, tuple) else timeout)
            return _Response(resp, resp.status, resp.geturl())
        except urllib.error.HTTPError as error:
            return _Response(error, error.code, url)

    def close(self):
        self.jar.clear()


def needs_bridge(resolved):
    return '.m3u8' in resolved.url.partition('?')[0].lower() and bool(resolved.headers)


def prepare(resolved):
    """-> (url, headers, close). A guarded HLS stream comes back as a local unguarded URL with no headers and a close() to call on stop."""
    if not needs_bridge(resolved):
        return resolved.url, resolved.headers, None
    import sports_hls_proxy
    import source_contract
    try:
        proxy = sports_hls_proxy.Proxy(resolved.url, resolved.headers, session=Session())
    except Exception as error:
        raise source_contract.Outcome(source_contract.classify(error))
    return proxy.url, {}, proxy.close
