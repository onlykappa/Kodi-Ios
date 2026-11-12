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

# Owner log 89a98e5b (build 275): the fallback still ended in the phone's own Errno 8, so Cloudflare at 1.1.1.1 gave no
# IPv4 answer (or could not be asked). Three resolvers, each by IP address, then IPv6; what each said goes to the log.
RESOLVERS = ('https://1.1.1.1/dns-query?name=%s&type=%s', 'https://8.8.8.8/resolve?name=%s&type=%s',
             'https://1.0.0.1/dns-query?name=%s&type=%s')
DOH = RESOLVERS[0]
TRIED = []    # (resolver, type, answer or error) of the last resolve(), for the log


def _ask(url, opener, timeout, rtype):
    req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
    with opener(req, timeout=timeout) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    return [a['data'] for a in data.get('Answer') or [] if a.get('type') == rtype and a.get('data')]


def resolve(host, opener=None, timeout=8):
    """Addresses for host from DNS over HTTPS (IPv4 first, then IPv6), [] when no resolver has one."""
    opener = opener or urllib.request.urlopen
    del TRIED[:]
    for rtype, code in (('A', 1), ('AAAA', 28)):
        for template in RESOLVERS:
            url = template % (urllib.parse.quote(host), rtype)
            try:
                found = _ask(url, opener, timeout, code)
            except Exception as error:
                TRIED.append((urllib.parse.urlsplit(url).hostname, rtype, type(error).__name__))
                continue
            TRIED.append((urllib.parse.urlsplit(url).hostname, rtype, ','.join(found) or 'no answer'))
            if found:
                return found
    return []


def tried_text():
    """'1.1.1.1 A: no answer; 8.8.8.8 A: URLError; ...' for the log."""
    return '; '.join('%s %s: %s' % t for t in TRIED)


class _Pinned(http.client.HTTPSConnection):
    def __init__(self, host, ip, timeout, context):
        super().__init__(host, 443, timeout=timeout, context=context)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, 443), self.timeout)   # an IPv6 answer connects the same way
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
            raise urllib.error.URLError('%s (DNS over HTTPS: %s)' % (getattr(first, 'reason', first), tried_text() or 'not asked'))
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
