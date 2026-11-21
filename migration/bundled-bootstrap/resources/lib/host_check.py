"""Which layer keeps a Sports source's website from answering on this phone (owner, build 623 log 8c570737: a live game failed with Crew's
`Streamer [embedsports] failed ... SSLError ... (_ssl.c:1006)` for taifood-blog.asia, twice, then Crew handed Kodi an unresolved `$doregex` link).

The log cannot say whether the phone's DNS answers with something that does not speak TLS (a filter's block page, as with the subtitle sites: roadmap 2.13),
or the site refuses the handshake, or the sources are down. When a source fails, once every ten minutes, this looks at the few hosts Crew's streamers use:
what the phone's own lookup gives, what DNS over HTTPS gives (doh_fetch), and whether a TLS handshake succeeds to each. Hostnames and the kind of address
(public, private, loopback, unspecified) go to the log, never a path, a header or a link. Everything is injected so the rules are tested here."""
import ipaddress
import socket
import ssl
import threading
import time

HOSTS = ('taifood-blog.asia', 'mutstreams.pk', 'strmfree.st', 'streamcenter.st')
EVERY = 600
_last = [0.0]
_lock = threading.Lock()


def kind(address):
    """'public', 'private', 'loopback', 'unspecified' or 'invalid': a DNS filter often answers with the last three."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return 'invalid'
    if ip.is_unspecified:
        return 'unspecified'
    if ip.is_loopback:
        return 'loopback'
    if ip.is_private or ip.is_link_local or ip.is_reserved:
        return 'private'
    return 'public'


def system_lookup(host):
    return sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


def handshake(host, address, timeout=6):
    """'ok TLSv1.3' when a TLS connection to `address` for `host` completes (its certificate checked for the name), else the error's kind."""
    try:
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = ssl.create_default_context()
        with socket.create_connection((address, 443), timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                return 'ok ' + str(tls.version())
    except ssl.SSLCertVerificationError:
        return 'certificate not accepted'
    except ssl.SSLError as error:
        return 'tls refused (%s)' % (str(error).split('(')[0].strip()[:40] or type(error).__name__)
    except socket.timeout:
        return 'timed out'
    except OSError as error:
        return 'no connection (%s)' % type(error).__name__


def check_host(host, system=system_lookup, doh=None, tls=handshake):
    """One line about one host: 'taifood-blog.asia: phone DNS 1 address (public), TLS ok TLSv1.3 | DoH 1 address (public), TLS tls refused'."""
    parts = []
    try:
        found = system(host)
    except Exception as error:
        found = None
        parts.append('phone DNS failed (%s)' % type(error).__name__)
    if found is not None:
        kinds = sorted({kind(a) for a in found}) or ['none']
        parts.append('phone DNS %d address%s (%s), TLS %s' % (len(found), '' if len(found) == 1 else 'es', ','.join(kinds), tls(host, found[0]) if found else 'nothing to try'))
    try:
        if doh is None:
            import doh_fetch
            doh = doh_fetch.resolve
        via = doh(host)
        if via:
            same = found is not None and set(via) & set(found)
            parts.append('DoH %d address%s (%s%s), TLS %s' % (len(via), '' if len(via) == 1 else 'es', ','.join(sorted({kind(a) for a in via})),
                                                             ', same as the phone' if same else ', not the phone\'s', tls(host, via[0])))
        else:
            parts.append('DoH no answer')
    except Exception as error:
        parts.append('DoH failed (%s)' % type(error).__name__)
    return '%s: %s' % (host, ' | '.join(parts))


def check_later(log, hosts=HOSTS, now=time.monotonic, runner=None, **kwargs):
    """From a failed source: look at the hosts in a thread, at most once every EVERY seconds. Returns the thread or None. Never raises."""
    try:
        with _lock:
            if _last[0] and now() - _last[0] < EVERY:
                return None
            _last[0] = now()

        def work():
            for host in hosts:
                try:
                    log('host check: ' + check_host(host, **kwargs))
                except Exception as error:
                    log('host check: %s not checked (%s)' % (host, type(error).__name__))
        thread = threading.Thread(target=runner or work, daemon=True)
        thread.start()
        return thread
    except Exception:
        return None
