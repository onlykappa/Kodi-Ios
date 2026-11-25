"""Hosts this phone's DNS answers wrongly, connected by DNS over HTTPS's address instead (owner, build 634 log 89646295: "we cant have failed sources").

host_check's line proved it for Crew's embedsports host: `taifood-blog.asia: phone DNS 4 addresses (public), TLS tls refused ([SSL] unknown error) | default roots:
tls refused | DoH 1 address (public, not the phone's), TLS ok TLSv1.3`: the phone's lookup returns addresses that cannot complete a TLS handshake (a filtered or
stale DNS answer), another resolver's address works. Crew's streamers (and any add-on) resolve the name with the phone's DNS, so they fail.

This checks the hosts the Sports sources use, on a timer in the service: for a host whose phone addresses fail TLS while DoH's address succeeds, it writes
{host: {ip, at}} to dns-overrides.json (profile addon_data). A small name-lookup wrapper in Crew's own module (sports_crew_patch.apply_dns, which runs where
Crew's streamers run) answers that host from the file, so the connection goes to the working address while TLS still checks the certificate for the host's own
name. A host whose phone addresses work has no entry. Entries older than KEEP seconds are ignored. Only the names listed here are ever touched."""
import json
import os
import time

HOSTS = ('taifood-blog.asia', 'v2.streameast.ga', 'thedaddy.li', 'mutstreams.pk', 'strmfree.st', 'streamcenter.st')
FILE = 'dns-overrides.json'
KEEP = 12 * 3600
EVERY = 30 * 60


def path():
    try:
        import xbmcvfs
        return os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap'), FILE)
    except Exception:
        return None


def load(file):
    try:
        with open(file, encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(file, table):
    os.makedirs(os.path.dirname(file) or '.', exist_ok=True)
    temp = file + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(table, handle, separators=(',', ':'))
    os.replace(temp, file)


def decide(host, system, doh, tls):
    """('override', ip) when the phone's addresses all fail TLS and DoH has one that works; ('fine', '') when the phone's work or there is nothing to fix;
    ('none', '') when nothing could be resolved or tried."""
    try:
        own = list(system(host))
    except Exception:
        own = []
    if any(tls(host, address).startswith('ok') for address in own[:3]):
        return 'fine', ''
    try:
        other = [a for a in doh(host) if a not in own]
    except Exception:
        other = []
    for address in other[:3]:
        if tls(host, address).startswith('ok'):
            return 'override', address
    return 'none', ''


def refresh(file, hosts=HOSTS, system=None, doh=None, tls=None, now=time.time, log=lambda text: None):
    """Re-check `hosts` and rewrite the table. Returns {host: ip} now in force."""
    import host_check
    system = system or host_check.system_lookup
    if doh is None:
        import doh_fetch
        doh = doh_fetch.resolve
    tls = tls or host_check.handshake
    table = load(file)
    for host in hosts:
        verdict, ip = decide(host, system, doh, tls)
        if verdict == 'override':
            if (table.get(host) or {}).get('ip') != ip:
                log('dns override: %s connects by %s address from DNS over HTTPS (the phone\'s DNS answer fails TLS)' % (host, host_check.kind(ip)))
            table[host] = {'ip': ip, 'at': int(now())}
        elif verdict == 'fine':
            if table.pop(host, None) is not None:
                log('dns override: %s works with the phone\'s DNS again; override removed' % host)
        elif host in table and now() - float((table[host] or {}).get('at', 0)) > KEEP:
            table.pop(host, None)
    save(file, {h: e for h, e in table.items() if h in hosts})
    return {h: e['ip'] for h, e in table.items() if h in hosts}


def watch(file, wait, log, hosts=HOSTS, first=2.0, now=time.time):
    """The service's loop: look soon after start, then every EVERY seconds; wait(seconds) is True when Kodi is closing."""
    delay = first
    while not wait(delay):
        try:
            refresh(file, hosts, now=now, log=log)
        except Exception as error:
            log('dns override: not checked (%s)' % type(error).__name__)
        delay = EVERY
