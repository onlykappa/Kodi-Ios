"""Require VPN for torrents (owner, 2026-11-22): Elementum's torrent networking runs only while a VPN is verified, and stops when that stops.

What this can and cannot do (docs/security/ELEMENTUM-VPN.md has the evidence):

- It works for any VPN that gives the phone a tunnel and a different public address. Proton VPN Plus is the one being used; nothing here is provider specific.
  Whether a provider PERMITS torrents is advice (docs), not something an iPhone app can read, and is kept apart from the check.
- "Verified" means: a tunnel-class interface exists, the public address the phone shows to the internet differs from every home address this phone has shown
  without a tunnel (stored only as salted hashes) and, when the owner names the VPN's network (words from the address owner, e.g. the provider's name), that
  name matches. Two checks in a row, with the interface list unchanged, are needed. LocalDevVPN (SideStore) never changes the public address, so it fails the
  second check; no interface name or address range is trusted.
- It is NOT a proof of routing for libtorrent's own sockets and NOT a kill switch: a tunnel can fail between two looks. What makes the block real is that it is
  applied to the engine itself (a forced proxy nobody listens on, plus the session pause), so every way into the engine, including magnet metadata, restored
  transfers, seeding and direct API calls, finds the door shut; and that it is applied first, before anything is checked. The VPN's own kill switch stays the
  protection against the gap between two looks.

Everything the phone does is injected (`Guard(...)`), so the rules are tested on a computer.
"""
import hashlib
import json
import os
import re
import time

TUNNEL_PREFIXES = ('utun', 'ipsec', 'ppp', 'tun', 'tap', 'wg')
PROPERTY = 'KodiIOS.VPNGuard'            # Home window: '' (feature off), 'blocked' or 'verified'
PROPERTY_TEXT = 'KodiIOS.VPNGuardText'   # the sentence to show
WATCH_EVERY = 1.0        # seconds between looks at the interface list (cheap, local)
PROBE_BLOCKED = 4.0      # seconds between address checks while blocked
PROBE_VERIFIED = 20.0    # ... while verified
PASSES = 2               # consecutive agreeing checks before the block is lifted
LEARN_EVERY = 300.0      # seconds between learning the home address while no tunnel exists
MAX_HOMES = 12           # home-address hashes kept (a home network and a mobile network change addresses)
REASSERT_EVERY = 10.0    # while blocked, the engine's settings are read back this often

# What blocks the engine: a SOCKS5 proxy on a port nobody listens on, forced for peers, trackers and names (libtorrent then makes no direct connection, resolves no
# names itself, and opens no listen sockets), plus Elementum's own proxy switch for its HTTP. use_proxy_http stays off: the add-on's searches are not torrent traffic.
TRAP = {'proxy_enabled': 'true', 'proxy_type': '1', 'proxy_host': '127.0.0.1', 'proxy_port': '1', 'proxy_login': '', 'proxy_password': '',
        'use_proxy_download': 'true', 'use_proxy_tracker': 'true', 'use_proxy_http': 'false', 'proxy_force': 'true'}
TRAP_KEYS = tuple(TRAP)

TEXT = {
    'off': '',
    'no_tunnel': 'Connect your VPN to continue. Torrents stay stopped until it is on.',
    'no_answer': 'Checking your VPN. Torrents stay stopped until its address is confirmed.',
    'same_as_home': 'Your address is the same as without a VPN. The VPN is off, or it is only the sideloading helper. Torrents stay stopped.',
    'unexpected_exit': 'The VPN address is not on the network you chose. Torrents stay stopped.',
    'no_home': 'Turn the VPN off once, on this network, so this iPhone can learn your home address, then turn it back on. Torrents stay stopped.',
    'changed': 'The network changed. Checking your VPN again. Torrents stay stopped.',
    'verified': 'VPN address check passed. Torrents may run.',
}


class Blocked(RuntimeError):
    """Raised by gate(): torrents are not allowed right now; str() is the sentence to show."""


# --- pure rules ------------------------------------------------------------------------------------------------------------------------------------------

def tunnels(table):
    """[(name, address)] of the tunnel-class interfaces with an IPv4 address (names are kept only to notice a change, never trusted)."""
    return sorted((n, a) for n, a in table if n.lower().startswith(TUNNEL_PREFIXES) and re.fullmatch(r'\d+\.\d+\.\d+\.\d+', a or ''))


def snapshot(table, kind):
    """What a change must be noticed in: the tunnel interfaces and addresses, and the kind of link (wifi, cellular, other)."""
    return {'tunnels': tunnels(table), 'link': kind}


def digest(address, salt):
    return hashlib.sha256((salt + '|' + str(address)).encode()).hexdigest()[:32]


def parse_probe(body):
    """{'ip': text, 'org': text} from an address-echo answer: JSON with ip / query / origin and optionally org / isp / as / asn_org / asn, or the address alone."""
    text = body.decode('utf-8', 'replace') if isinstance(body, bytes) else str(body or '')
    text = text.strip()
    ip = org = ''
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            ip = str(data.get('ip') or data.get('query') or data.get('origin') or '').strip()
            org = ' '.join(str(data[k]) for k in ('org', 'asn_org', 'isp', 'as', 'asn', 'organization', 'hostname') if data.get(k))
    except ValueError:
        if re.fullmatch(r'[0-9a-fA-F:.]{3,45}', text):
            ip = text
    ip = ip.split(',')[0].strip()   # "x-forwarded" style lists
    return {'ip': ip, 'org': org.lower()} if re.fullmatch(r'[0-9a-fA-F:.]{3,45}', ip) else None


def probe(endpoints, get, timeout=6):
    """The public address and its owner as seen by every endpoint that answered. None unless at least one answered and all that did agree on the address (two
    services that disagree mean something rewrites the answers: not proof of anything). Never reads or logs more than the answer."""
    seen = []
    for url in endpoints:
        try:
            got = parse_probe(get(url, timeout))
        except Exception:
            got = None
        if got:
            seen.append(got)
    if not seen or len({s['ip'] for s in seen}) != 1:
        return None
    return {'ip': seen[0]['ip'], 'org': ' '.join(s['org'] for s in seen if s['org'])}


def decide(enabled, snap, answer, homes, salt, expected=()):
    """(state, reason): state 'off' | 'blocked' | 'verified'. `answer` is probe()'s result or None, `homes` the home-address hashes known for any link."""
    if not enabled:
        return 'off', 'off'
    if not snap['tunnels']:
        return 'blocked', 'no_tunnel'
    if not answer:
        return 'blocked', 'no_answer'
    if digest(answer['ip'], salt) in homes:
        return 'blocked', 'same_as_home'
    words = [w.strip().lower() for w in expected if w and w.strip()]
    if words:
        return ('verified', 'verified') if any(w in answer['org'] for w in words) else ('blocked', 'unexpected_exit')
    if not homes:
        return 'blocked', 'no_home'   # nothing to compare with, and no network named: the address alone proves nothing
    return 'verified', 'verified'


def gate(enabled, state):
    """For every place that is about to start torrent work: returns None when allowed, raises Blocked with the sentence to show when not."""
    if enabled and state != 'verified':
        raise Blocked(TEXT['no_tunnel'] if state in ('', None, 'blocked') else TEXT['changed'])


# --- the guard -------------------------------------------------------------------------------------------------------------------------------------------

class Store:
    """The guard's private memory (profile folder, never Git): the Elementum settings the block replaced, the home-address hashes and their salt."""
    def __init__(self, path, read=None, write=None):
        self.path, self.read, self.write = path, read or self._read, write or self._write
        try:
            self.data = json.loads(self.read(path) or '{}')
        except (ValueError, OSError):
            self.data = {}
        if not self.data.get('salt'):
            self.data['salt'] = hashlib.sha256(os.urandom(32)).hexdigest()[:24]
        self.data.setdefault('homes', [])
        self.data.setdefault('originals', None)

    @staticmethod
    def _read(path):
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except OSError:
            return ''

    @staticmethod
    def _write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(path + '.tmp', path)

    def save(self):
        self.write(self.path, json.dumps(self.data))

    @property
    def salt(self):
        return self.data['salt']

    def learn(self, address):
        mine = digest(address, self.salt)
        if mine not in self.data['homes']:
            self.data['homes'] = ([mine] + self.data['homes'])[:MAX_HOMES]
            self.save()
            return True
        return False


class Guard:
    """One look per step(): block first, verify, release. enabled() / expected() read the owner's settings; table() is cache_tune.interfaces(); kind(table) the link kind;
    get(url, timeout) one address-echo request; settings = (get, put) for Elementum's settings; engine(path) calls its local API; publish(state, text) tells the rest of
    the app; notify(text) shows the short message; now() the clock."""
    def __init__(self, store, enabled, expected, endpoints, table, kind, get, settings, engine, publish, notify=lambda text: None, now=time.monotonic, log=lambda text: None):
        self.store, self.enabled, self.expected, self.endpoints = store, enabled, expected, endpoints
        self.table, self.kind, self.get, self.settings, self.engine = table, kind, get, settings, engine
        self.publish, self.notify, self.now, self.log = publish, notify, now, log
        self.state = None            # None until the first look; then 'off' | 'blocked' | 'verified'
        self.reason = ''
        self.snap = None
        self.passes, self.last_exit = 0, None
        self.next_probe = self.next_learn = self.next_reassert = 0.0
        self.noted = ''
        self.reloaded = False

    # -- the two actions on Elementum --
    def block(self):
        """Close the door: remember the owner's own proxy settings once, write the trap, make the engine read it, pause its session. Idempotent."""
        get, put = self.settings
        changed = False
        if self.store.data.get('originals') is None:
            self.store.data['originals'] = {k: get(k) for k in TRAP_KEYS}
            self.store.save()
        for key, value in TRAP.items():
            if get(key) != value:
                put(key, value)
                changed = True
        if changed or not self.reloaded:
            self.engine('/reload')   # the engine reads its settings again (a reconfigure is heavy: only when something changed)
            self.reloaded = True
        self.engine('/torrents/pause')

    def release(self):
        """Open the door again: the owner's own settings back, the engine reloaded, the session resumed (torrents the owner paused one by one stay paused)."""
        get, put = self.settings
        originals = self.store.data.get('originals')
        if originals is not None:
            for key, value in originals.items():
                if get(key) != value:
                    put(key, value)
            self.store.data['originals'] = None
            self.store.save()
            self.engine('/reload')
        self.reloaded = False
        self.engine('/torrents/resume')

    def reassert(self):
        """While blocked: the engine may have restarted (a new session, settings read afresh) or the add-on may have reset its settings: close the door again."""
        get, _ = self.settings
        if any(get(k) != v for k, v in TRAP.items()):
            self.log('vpn guard: the engine settings no longer block; blocked again')
        self.block()

    # -- the look --
    def step(self):
        """Returns the state after this look."""
        now = self.now()
        try:
            on = bool(self.enabled())
        except Exception:
            on = True   # unreadable setting: stay on the safe side
        if not on:
            if self.state not in (None, 'off') or self.store.data.get('originals') is not None:
                self.release()
                self.log('vpn guard: off, the engine settings are back')
            self._set('off', 'off')
            return self.state
        table = self.table()
        snap = snapshot(table, self.kind(table))
        if self.state in (None, 'off'):
            self.block()   # first, before anything is checked
            self.log('vpn guard: on; torrents blocked until the VPN is verified')
            self._set('blocked', 'changed')
            self.snap = snap
            self.next_reassert = now + REASSERT_EVERY
        if snap != self.snap:
            self.snap = snap
            self.passes, self.last_exit, self.next_probe = 0, None, 0.0
            if self.state == 'verified':
                self.block()
                self.log('vpn guard: the network changed; torrents blocked again')
                self._set('blocked', 'changed')
        if not snap['tunnels']:
            if self.state == 'verified':
                self.block()
                self._set('blocked', 'no_tunnel')
            if now >= self.next_learn:   # no tunnel: what this phone shows to the internet is its home address
                self.next_learn = now + LEARN_EVERY
                found = probe(self.endpoints(), self.get)
                if found and self.store.learn(found['ip']):
                    self.log('vpn guard: learned a home address (kept as a hash)')
            self._set('blocked', 'no_tunnel')
        elif now >= self.next_probe:
            found = probe(self.endpoints(), self.get)
            self.next_probe = now + (PROBE_VERIFIED if self.state == 'verified' else PROBE_BLOCKED)
            state, reason = decide(True, snap, found, self.store.data['homes'], self.store.salt, self.expected())
            if state == 'verified':
                mine = digest(found['ip'], self.store.salt)
                self.passes = self.passes + 1 if mine == self.last_exit or self.last_exit is None else 1
                self.last_exit = mine
                if self.state != 'verified' and self.passes >= PASSES:
                    self.release()
                    self.log('vpn guard: VPN address check passed twice; torrents may run')
                    self._set('verified', 'verified')
                elif self.state == 'verified':
                    self._set('verified', 'verified')
            else:
                self.passes, self.last_exit = 0, None
                if self.state == 'verified':
                    self.block()
                    self.log('vpn guard: the check failed (%s); torrents blocked again' % reason)
                self._set('blocked', reason)
        if self.state == 'blocked' and now >= self.next_reassert:
            self.next_reassert = now + REASSERT_EVERY
            self.reassert()
        return self.state

    def _set(self, state, reason):
        changed = (state, reason) != (self.state, self.reason)
        self.state, self.reason = state, reason
        self.publish(state if state != 'off' else '', TEXT[reason])
        if changed and state == 'blocked' and reason != 'changed' and TEXT[reason] != self.noted:
            self.noted = TEXT[reason]
            self.notify(TEXT[reason])
        if state != 'blocked':
            self.noted = ''
