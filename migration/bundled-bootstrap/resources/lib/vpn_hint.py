"""Is a VPN carrying this phone's traffic? A HINT for the torrent popup, never a proof (owner, 2026-11-23).

The phone's own answer to "which interface would you use to reach the internet" (cache_tune.local_address: a UDP connect that sends nothing) is looked up in the
interface list. With a VPN routing everything, the address belongs to a tunnel (`utunN`); on Wi-Fi it belongs to `enN`; on cellular to `pdp_ipN`. The build 664 log
with Proton connected is the only one of 119 logs whose link kind reads "other" (all the others: wifi or cellular), which is this signal. A helper tunnel such as
LocalDevVPN does not take the default route, so the answer stays Wi-Fi and the hint says no VPN. Nothing here asks a server anything, and only interface names reach a log."""
TUNNEL_PREFIXES = ('utun', 'ipsec', 'ppp', 'tun', 'tap', 'wg')
PHYSICAL_PREFIXES = ('en', 'pdp_ip', 'rmnet', 'ccmni', 'wlan', 'wl')


def kind(name):
    """'tunnel', 'direct' (Wi-Fi, cellular, ethernet) or 'unknown' for an interface name."""
    name = (name or '').lower()
    if name.startswith(TUNNEL_PREFIXES):
        return 'tunnel'
    if name.startswith(PHYSICAL_PREFIXES):
        return 'direct'
    return 'unknown'


def look(address, table):
    """{'state': 'tunnel' | 'direct' | 'unknown', 'route': interface name or '', 'tunnels': [names of tunnel interfaces with an IPv4 address]} from the address the phone
    uses to reach the internet and the interface list [(name, address)]."""
    route = next((name for name, found in table if address and found == address), '')
    tunnels = sorted({name for name, found in table if kind(name) == 'tunnel' and found and found.count('.') == 3})
    return {'state': kind(route) if route else 'unknown', 'route': route, 'tunnels': tunnels}


def line(found):
    """The log line: names only. Sent in every state so the four situations (VPN on, none, a helper tunnel, cellular) can be compared."""
    return 'vpn check: %s; default route via %s; tunnel interfaces: %s' % (
        {'tunnel': 'a VPN looks active', 'direct': 'no VPN', 'unknown': 'cannot tell'}[found['state']], found['route'] or 'unknown', ', '.join(found['tunnels']) or 'none')


def current(local_address, interfaces):
    """look() for this phone right now (the two readers are cache_tune's; passed in so tests and the service share one code path)."""
    try:
        return look(local_address(), interfaces())
    except Exception:
        return {'state': 'unknown', 'route': '', 'tunnels': []}
