"""Asking an address-echo service "what address do you see?" twice: the way the phone normally goes out (the default route: through a VPN when one is routing), and
straight out of the physical interface (Wi-Fi or cellular), bypassing the default route. Two different answers mean the default route really exits somewhere else
than the physical link does: a VPN is routing. Two equal answers mean it is not, whatever interfaces exist (the sideloading helper, a VPN app that is "on" but
split-tunnelled, a tunnel that came up empty). That comparison needs no list of home networks, so it works on any network the phone joins.

The physical path is asked by binding the socket to the interface (Darwin: IP_BOUND_IF with the interface index; Linux: SO_BINDTODEVICE, for the lab). A VPN whose own
kill switch closes the physical path makes that question fail; the guard treats a failed direct question as "not comparable" and falls back to its other signals, never
as a pass. Nothing here logs an address."""
import http.client
import socket
import ssl
import sys
import urllib.parse

IP_BOUND_IF = 25   # Darwin, level IPPROTO_IP (also used for IPv6 with IPV6_BOUND_IF = 125)
SO_BINDTODEVICE = 25   # Linux, level SOL_SOCKET


def bind_interface(sock, name):
    """Tie the socket's traffic to one interface. Raises OSError when the system refuses."""
    if sys.platform == 'darwin':
        sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(name))
    else:
        sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, name.encode() + b'\0')


def _connection(parts, interface, timeout):
    host, port = parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80)

    class Conn((http.client.HTTPSConnection if parts.scheme == 'https' else http.client.HTTPConnection)):
        def connect(self):
            last = None
            for family, kind, proto, _, address in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
                sock = socket.socket(family, kind, proto)
                sock.settimeout(timeout)
                try:
                    if interface:
                        bind_interface(sock, interface)
                    sock.connect(address)
                except OSError as error:
                    sock.close()
                    last = error
                    continue
                self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host) if parts.scheme == 'https' else sock
                return
            raise last or OSError('no address')
    return Conn(host, port, timeout=timeout)


def get(url, interface=None, timeout=6):
    """The body (at most 4 KB) of an http(s) GET, out of `interface` when one is given, else by the default route."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('not an http(s) address')
    connection = _connection(parts, interface, timeout)
    try:
        connection.request('GET', parts.path + ('?' + parts.query if parts.query else '') or '/', headers={'User-Agent': 'Kodi-iOS', 'Accept': '*/*'})
        response = connection.getresponse()
        if response.status != 200:
            raise OSError('status %d' % response.status)
        return response.read(4000)
    finally:
        connection.close()


PHYSICAL_PREFIXES = ('en', 'pdp_ip')   # iOS Wi-Fi / Ethernet and cellular


def physical(table):
    """Names of the interfaces that have a usable IPv4 address and are Wi-Fi/cellular/ethernet (never tunnels, loopback, AirDrop/AWDL, bridges), in the order given."""
    seen = []
    for name, address in table:
        if name.lower().startswith(PHYSICAL_PREFIXES) and address and address.count('.') == 3 and not address.startswith(('169.254.', '127.')) and name not in seen:
            seen.append(name)
    return seen
