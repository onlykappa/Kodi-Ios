"""HTTPS GET that survives a DNS that refuses a name (roadmap 2.13).

Owner logs e8ab5995, 396d5d67, eabc204b: every subtitle search failed at once with `Errno 8 nodename nor servname`
for www.podnapisi.net, a live site, while Drive and TMDb worked. The phone's DNS (carrier or a filtering profile)
does not answer for that name. When the normal lookup fails, ask Cloudflare's DNS over HTTPS at its IP address
(1.1.1.1, so no DNS is needed to reach it) and connect to the answer, still checking the site's certificate for its
own name (TLS SNI and verification use the host name, only the TCP connection uses the IP)."""
import http.client
import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

DOH = 'https://1.1.1.1/dns-query?name=%s&type=A'


def resolve(host, opener=None, timeout=8):
    """IPv4 addresses for host from DNS over HTTPS, [] when none."""
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(DOH % urllib.parse.quote(host), headers={'Accept': 'application/dns-json'})
    with opener(req, timeout=timeout) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    return [a['data'] for a in data.get('Answer') or [] if a.get('type') == 1 and a.get('data')]


class _Pinned(http.client.HTTPSConnection):
    def __init__(self, host, ip, timeout, context):
        super().__init__(host, 443, timeout=timeout, context=context)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _dns_failure(error):
    reason = getattr(error, 'reason', error)
    return isinstance(reason, socket.gaierror) or isinstance(error, socket.gaierror)


def get(url, headers=None, timeout=20, opener=None, resolver=None, connect=None, redirects=4):
    """Body of url; on a DNS failure, again through DNS over HTTPS. Raises like urllib on other errors."""
    opener = opener or urllib.request.urlopen
    try:
        with opener(urllib.request.Request(url, headers=headers or {}), timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, OSError) as error:
        if isinstance(error, urllib.error.HTTPError) or not _dns_failure(error):
            raise
        first = error
    resolver = resolver or resolve
    connect = connect or (lambda host, ip: _Pinned(host, ip, timeout, ssl.create_default_context()))
    for _ in range(redirects + 1):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != 'https':
            raise first
        ips = resolver(parts.hostname)
        if not ips:
            raise first
        conn = connect(parts.hostname, ips[0])
        try:
            path = parts.path or '/'
            if parts.query:
                path += '?' + parts.query
            conn.request('GET', path, headers=dict(headers or {}, Host=parts.hostname))
            resp = conn.getresponse()
            body = resp.read()
            if resp.status in (301, 302, 303, 307, 308) and resp.getheader('Location'):
                url = urllib.parse.urljoin(url, resp.getheader('Location'))
                continue
            if resp.status >= 400:
                raise urllib.error.HTTPError(url, resp.status, resp.reason, resp.headers, None)
            return body
        finally:
            conn.close()
    raise first
