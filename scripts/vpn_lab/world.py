"""The remote side of the lab (runs inside the `world` namespace): a seeder for a generated torrent, an HTTP tracker and a DNS server. Each records the source
address of everything that reaches it, as JSON lines. Test data is random bytes; nothing here is real media or a real tracker."""
import json, os, socket, struct, sys, threading, time, http.server, urllib.parse
import libtorrent as lt

PEER = '203.0.113.10'
PEER6 = '2001:db8:203::10'
OUT = sys.argv[1]
WORK = sys.argv[2]
SIZE = 12 * 1024 * 1024
log_lock = threading.Lock()


def note(kind, addr):
    with log_lock, open(OUT, 'a') as f:
        f.write(json.dumps({'t': round(time.time(), 2), 'kind': kind, 'src': addr}) + '\n')


def benc(v):
    if isinstance(v, int): return b'i%de' % v
    if isinstance(v, bytes): return b'%d:' % len(v) + v
    if isinstance(v, str): return benc(v.encode())
    if isinstance(v, list): return b'l' + b''.join(benc(x) for x in v) + b'e'
    return b'd' + b''.join(benc(k) + benc(v[k]) for k in sorted(v)) + b'e'


def make_torrent():
    path = os.path.join(WORK, 'payload.bin')
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(os.urandom(SIZE))
    fs = lt.file_storage(); lt.add_files(fs, path)
    t = lt.create_torrent(fs, 262144); t.add_tracker('http://tracker.test:6969/announce')
    lt.set_piece_hashes(t, WORK)
    data = lt.bencode(t.generate())
    open(os.path.join(WORK, 'test.torrent'), 'wb').write(data)


class Tracker(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        note('tracker', self.client_address[0])
        body = {'interval': 5, 'min interval': 5, 'peers': socket.inet_aton(PEER) + struct.pack('>H', 6881)}
        if os.environ.get('LAB_V6_PEER'):
            body['peers6'] = socket.inet_pton(socket.AF_INET6, PEER6) + struct.pack('>H', 6881)
        out = benc(body)
        self.send_response(200); self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)


class Echo(http.server.BaseHTTPRequestHandler):   # what an address-echo service does: says which address it sees
    def log_message(self, *a): pass
    def do_GET(self):
        note('echo', self.client_address[0])
        out = json.dumps({'ip': self.client_address[0]}).encode()
        self.send_response(200); self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)


import socketserver


class Server(http.server.ThreadingHTTPServer):
    def server_bind(self):   # HTTPServer.server_bind asks DNS for the host's name, which can stall for seconds in a namespace with no resolver
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[0], self.server_address[1]


def dns():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind((PEER, 53))
    while True:
        data, addr = s.recvfrom(512); note('dns', addr[0])
        q = data[12:]; end = q.index(b'\0') + 5; qtype = struct.unpack('>H', q[end - 4:end - 2])[0]
        head = data[:2] + b'\x81\x80' + data[4:6] + (b'\x00\x01' if qtype == 1 else b'\x00\x00') + b'\x00\x00\x00\x00'
        ans = b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + socket.inet_aton(PEER) if qtype == 1 else b''
        s.sendto(head + q[:end] + ans, addr)


def main():
    make_torrent()
    servers = [Server((PEER, 6969), Tracker), Server((PEER, 8080), Echo)]   # bound before `ready` is written
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=dns, daemon=True).start()
    ses = lt.session({'listen_interfaces': ('%s:6881,[%s]:6881' % (PEER, PEER6)) if os.path.exists('/proc/sys/net/ipv6') else '%s:6881' % PEER, 'enable_dht': False, 'enable_lsd': False, 'enable_upnp': False,
                      'enable_natpmp': False, 'upload_rate_limit': 300000, 'alert_mask': lt.alert.category_t.all_categories})
    ti = lt.torrent_info(os.path.join(WORK, 'test.torrent'))
    ses.add_torrent({'ti': ti, 'save_path': WORK, 'flags': lt.torrent_flags.seed_mode})
    open(os.path.join(WORK, 'ready'), 'w').write('1')
    while True:
        for a in ses.pop_alerts():
            if isinstance(a, lt.incoming_connection_alert):
                note('peer-%s' % ('utp' if a.socket_type == lt.socket_type_t.utp else 'tcp'), a.endpoint[0])
        time.sleep(.2)


main()
