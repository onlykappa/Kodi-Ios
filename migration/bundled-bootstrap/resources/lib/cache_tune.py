"""Roadmap 1B.3: Kodi's file-cache read factor follows the connection the phone is using.

Code reading (Kodi 21.3, VideoPlayer.cpp HandleCaching): playback starts as soon as the audio and video players have
their first data (CACHESTATE_INIT -> PLAY); it does not wait for the file cache to fill, so "start after a small
cache fill" already holds. What is left to tune is how hard the cache pulls: CFileCache reads filecache.readfactor
when a file opens (x10 = ten times the bitrate). On Wi-Fi that finishes a seek's refill quickly; on cellular x10 takes
all the radio's bandwidth (and data) from Drive uploads and the AirPlay conversion, so cellular gets x4.

The link is found from the interface that carries traffic to the internet (iOS: en0 = Wi-Fi, pdp_ipN = cellular).
A value the owner chose in Kodi's settings is never overwritten: only the value this module (or portrait.tune_cache)
last wrote is replaced."""
import json
import os
import socket
import sys

READ_FACTOR = {'wifi': 1000, 'cellular': 400, 'other': 1000}   # filecache.readfactor: 1000 = 10x the bitrate
SETTING = 'filecache.readfactor'
MARKER = 'addon_data/service.kodi.ios.bootstrap/cache-link.json'
DEFAULT_WRITTEN = 1000      # what portrait.tune_cache (build 206) wrote


def kind_of(name):
    """'wifi', 'cellular' or 'other' for an interface name."""
    name = (name or '').lower()
    if name.startswith('pdp_ip') or name.startswith('rmnet') or name.startswith('ccmni'):
        return 'cellular'
    if name.startswith('en') or name.startswith('wlan') or name.startswith('wl'):
        return 'wifi'
    return 'other'


def local_address():
    """The local address the phone would use to reach the internet (a UDP connect sends nothing)."""
    for family, target in ((socket.AF_INET, ('1.1.1.1', 53)), (socket.AF_INET6, ('2606:4700:4700::1111', 53))):
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                sock.connect(target)
                return sock.getsockname()[0]
        except OSError:
            continue
    return ''


def interfaces():
    """[(name, address)] from getifaddrs (the struct prefix is the same on Linux and Darwin)."""
    import ctypes

    class Ifaddrs(ctypes.Structure):
        pass
    Ifaddrs._fields_ = [('next', ctypes.POINTER(Ifaddrs)), ('name', ctypes.c_char_p), ('flags', ctypes.c_uint),
                        ('addr', ctypes.c_void_p)]
    libc = ctypes.CDLL(None)
    head = ctypes.POINTER(Ifaddrs)()
    if libc.getifaddrs(ctypes.byref(head)) != 0:
        return []
    out = []
    try:
        entry = head
        while entry:
            item = entry.contents
            if item.addr:
                raw = ctypes.string_at(item.addr, 32)
                family = raw[1] if sys.platform == 'darwin' else raw[0]
                try:
                    if family == socket.AF_INET:
                        out.append((item.name.decode(), socket.inet_ntop(socket.AF_INET, raw[4:8])))
                    elif family == socket.AF_INET6:
                        out.append((item.name.decode(), socket.inet_ntop(socket.AF_INET6, raw[8:24])))
                except (ValueError, OSError):
                    pass
            entry = item.next
    finally:
        libc.freeifaddrs(head)
    return out


def link_kind(address=None, table=None):
    """'wifi', 'cellular' or 'other' for the connection in use; 'other' when it cannot be told."""
    try:
        address = local_address() if address is None else address
        for name, found in (interfaces() if table is None else table):
            if found == address:
                return kind_of(name)
    except Exception:
        pass
    return 'other'


def apply(xbmc, profile, log, kind=None, read=None):
    """Set filecache.readfactor for the current link unless the owner changed it. Returns the value set, or None."""
    kind = kind or link_kind()
    want = READ_FACTOR.get(kind, READ_FACTOR['other'])
    marker = os.path.join(profile, MARKER)
    try:
        with open(marker, encoding='utf-8') as f:
            last = int(json.load(f).get('readfactor'))
    except (OSError, ValueError, TypeError):
        last = None
    try:
        current = int(read() if read else json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.GetSettingValue', 'params': {'setting': SETTING}}))).get('result', {}).get('value'))
    except (ValueError, TypeError, AttributeError):
        return None
    ours = {DEFAULT_WRITTEN, last}
    if current not in ours:
        return None            # the owner chose this value in Kodi's settings
    if current != want:
        xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
                                        'params': {'setting': SETTING, 'value': want}}))
        log('Kodi iOS cache: read factor %.1fx for %s (was %.1fx)' % (want / 100.0, kind, current / 100.0))
    if last != want:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, 'w', encoding='utf-8') as f:
            json.dump({'readfactor': want, 'link': kind}, f)
    return want
