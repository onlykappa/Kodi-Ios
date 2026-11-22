#!/usr/bin/env python3
"""Network-namespace lab for the Elementum + VPN review (docs/security/ELEMENTUM-VPN.md). Linux, root, `iproute2`, `tcpdump`, and `pip install libtorrent`.

     phone ns ──eth0── home ns (household router, NAT -> 192.0.2.1) ──┐
         └─────utun0── exit ns (VPN exit,        NAT -> 198.51.100.1) ──┼── world ns: tracker, DNS and seeder at 203.0.113.10
                                                                       ┘   (and 2001:db8:203::10, reachable only on the household path)

The phone's default route is the only thing that decides which path a connection takes, as on an iPhone with a VPN: a tunnel up sends everything through
utun0, a failed tunnel with no kill switch leaves the household default route, and a kill switch is modelled by a blackhole default. What the remote side sees
is read at the `world` namespace boundary (tcpdump on each of its two uplinks) and from the tracker / DNS / peer logs. libtorrent here is the PyPI 2.1.x build,
a stand-in for Elementum's libtorrent 2.0.x; the engine itself is not run (see the document).

  sudo PYTHONPATH=/path/to/libtorrent python3 scripts/vpn_lab/lab.py [scenario ...]    (no arguments: all scenarios; results as JSON on stdout)
"""
import json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
NS = ('phone', 'home', 'exit', 'world', 'peer')
HAVE_V6 = os.path.exists('/proc/sys/net/ipv6')   # a kernel without IPv6 (this review's sandbox) cannot run the IPv6 scenarios: they are reported as not run
PYPATH = os.environ.get('PYTHONPATH', '')


def sh(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def ns(name, cmd, check=True):
    return sh('ip netns exec %s %s' % (name, cmd), check)


def popen(name, cmd, out=None):
    return subprocess.Popen('ip netns exec %s env PYTHONPATH=%s %s' % (name, PYPATH, cmd), shell=True, stdout=out or subprocess.DEVNULL, stderr=subprocess.STDOUT)


def teardown():
    for n in NS:
        pids = sh('ip netns pids %s' % n, check=False).stdout.split()
        if pids:
            sh('kill -9 %s' % ' '.join(pids), check=False)
        sh('ip netns del %s' % n, check=False)
    shutil.rmtree('/etc/netns', ignore_errors=True)


def setup():
    teardown()
    for n in NS:
        sh('ip netns add %s' % n)
        ns(n, 'ip link set lo up')

    def pair(a, ia, b, ib, a4, b4, a6=None, b6=None):
        sh('ip link add %s netns %s type veth peer name %s netns %s' % (ia, a, ib, b))
        for n, i, ip4, ip6 in ((a, ia, a4, a6), (b, ib, b4, b6)):
            ns(n, 'ip addr add %s dev %s' % (ip4, i))
            if ip6 and HAVE_V6:
                ns(n, 'ip -6 addr add %s dev %s nodad' % (ip6, i))
            ns(n, 'ip link set %s up' % i)
    pair('phone', 'eth0', 'home', 'h-p0', '192.168.1.2/24', '192.168.1.1/24', '2001:db8:1::2/64', '2001:db8:1::1/64')
    pair('phone', 'utun0', 'exit', 'x-p0', '10.8.0.2/24', '10.8.0.1/24')
    pair('home', 'h-w0', 'world', 'w-h0', '192.0.2.1/30', '192.0.2.2/30', '2001:db8:100::1/64', '2001:db8:100::2/64')
    pair('exit', 'x-w0', 'world', 'w-x0', '198.51.100.1/30', '198.51.100.2/30')
    # The remote peer sits one hop behind `world` in its own namespace: libtorrent binds a listen address to its device, so the address must live on the
    # interface the traffic arrives on.
    pair('world', 'w-peer0', 'peer', 'peer0', '10.99.0.1/30', '10.99.0.2/30')
    ns('peer', 'ip addr add 203.0.113.10/32 dev peer0'); ns('peer', 'ip route add default via 10.99.0.1')
    ns('world', 'ip route add 203.0.113.10/32 via 10.99.0.2'); ns('world', 'sysctl -qw net.ipv4.ip_forward=1')
    ns('home', 'ip route add 203.0.113.0/24 via 192.0.2.2')
    ns('exit', 'ip route add 203.0.113.0/24 via 198.51.100.2')
    if HAVE_V6:
        ns('peer', 'ip -6 addr add 2001:db8:203::10/128 dev peer0 nodad'); ns('peer', 'ip -6 route add default via 2001:db8:203::1'); ns('world', 'ip -6 addr add 2001:db8:203::1/64 dev w-peer0 nodad'); ns('home', 'ip -6 route add 2001:db8:203::/64 via 2001:db8:100::2')
        ns('world', 'ip -6 route add 2001:db8:1::/64 via 2001:db8:100::1')
    for n in ('home', 'exit'):
        ns(n, 'sysctl -qw net.ipv4.ip_forward=1')
    if HAVE_V6:
        ns('home', 'sysctl -qw net.ipv6.conf.all.forwarding=1')
    ns('home', 'iptables -t nat -A POSTROUTING -o h-w0 -j MASQUERADE'); ns('exit', 'iptables -t nat -A POSTROUTING -o x-w0 -j MASQUERADE')
    if HAVE_V6:
        ns('phone', 'ip -6 route add default via 2001:db8:1::1 dev eth0')   # IPv6 only has the household path
    os.makedirs('/etc/netns/phone', exist_ok=True)
    open('/etc/netns/phone/resolv.conf', 'w').write('nameserver 203.0.113.10\n')


def route(mode):
    """The phone's IPv4 default route: vpn (through the tunnel), direct (the household router, as after a tunnel failure with no kill switch), killed (blackhole)."""
    ns('phone', 'ip route flush 0.0.0.0/0', check=False)
    if mode == 'vpn':
        # As on a real phone the physical network's own default route stays in the table (iOS keeps one scoped to each interface); the tunnel's wins by metric.
        ns('phone', 'ip route add default via 10.8.0.1 dev utun0 metric 10')
        ns('phone', 'ip route add default via 192.168.1.1 dev eth0 metric 100')
    elif mode == 'direct':
        ns('phone', 'ip route add default via 192.168.1.1 dev eth0')
    elif mode == 'killed':
        ns('phone', 'ip route add blackhole default')


class Capture:
    """tcpdump at the world namespace's two uplinks: what the remote side's network actually receives from the phone, by source address and service."""
    def __init__(self, tag):
        self.files = {}
        self.procs = []
        for iface, label in (('w-h0', 'household'), ('w-x0', 'vpn-exit')):
            f = tempfile.NamedTemporaryFile('w+', suffix='.%s.%s' % (tag, label), delete=False)
            self.files[label] = f
            self.procs.append(popen('world', 'tcpdump -l -nn -q -i %s "dst host 203.0.113.10 or dst host 2001:db8:203::10"' % iface, out=f))
        time.sleep(1)

    def stop(self):
        time.sleep(1)
        for p in self.procs:
            p.terminate(); p.wait()
        found = {}
        for label, f in self.files.items():
            f.flush(); f.seek(0)
            seen = {}
            for line in f:
                parts = line.split()
                if len(parts) < 5 or parts[1] not in ('IP', 'IP6'):
                    continue
                src, dst = parts[2], parts[4].rstrip(':')
                port = dst.rsplit('.', 1)[1]
                proto = parts[5] if len(parts) > 5 else ''
                service = {'53': 'dns', '6969': 'tracker', '6881': 'peer-' + ('udp' if proto == 'UDP,' or proto == 'UDP' else 'tcp')}.get(port)
                if not service:
                    continue
                key = (src.rsplit('.', 1)[0], service)
                seen[key] = seen.get(key, 0) + 1
            found[label] = {'%s %s' % k: v for k, v in sorted(seen.items())}
            os.unlink(f.name)
        return found


def run_client(work, seconds, env='', out=None):
    return popen('phone', '%s python3 %s/client.py %s %d' % (env, HERE, work, seconds), out=out)


def last(path):
    try:
        lines = [json.loads(l) for l in open(path) if l.startswith('{')]
        return lines[-1] if lines else {}
    except OSError:
        return {}


def world_log(path):
    out = {}
    try:
        for l in open(path):
            r = json.loads(l); out.setdefault(r['kind'], set()).add(r['src'])
    except OSError:
        pass
    return {k: sorted(v) for k, v in out.items()}


def probe_pair():
    """vpn_probe + vpn_guard.decide() in the phone namespace for four situations. Linux binds to the device with SO_BINDTODEVICE (Darwin uses IP_BOUND_IF)."""
    out = {}
    def ask():
        r = ns('phone', 'python3 %s/probe_client.py' % HERE, check=False)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {'error': r.stderr[-200:]}
    route('vpn'); out['vpn_carrying_the_traffic'] = ask()
    route('direct'); out['helper_tunnel_up_but_default_route_direct'] = ask()   # what LocalDevVPN looks like: a tunnel exists, the route does not use it
    ns('phone', 'ip link set utun0 down'); out['tunnel_failed_no_kill_switch'] = ask(); ns('phone', 'ip link set utun0 up')
    route('killed'); out['kill_switch_blackhole'] = ask()
    return out


def scenario(name, work):
    """Returns a dict of observations for one scenario."""
    if name.startswith('ipv6') and not HAVE_V6:
        return {'not_run': 'this kernel has no IPv6 (/proc/sys/net/ipv6 is absent), so the household-only IPv6 path cannot be built'}
    for f in ('dl', 'world.jsonl'):
        shutil.rmtree(os.path.join(work, f), ignore_errors=True) if f == 'dl' else (os.path.exists(os.path.join(work, f)) and os.unlink(os.path.join(work, f)))
    log = os.path.join(work, 'world.jsonl')
    env_v6 = 'LAB_V6_PEER=1 ' if name.startswith('ipv6') else ''
    w = popen('peer', '%spython3 %s/world.py %s %s' % (env_v6, HERE, log, work), out=open(os.path.join(work, 'world.out'), 'w'))
    for _ in range(100):
        if os.path.exists(os.path.join(work, 'ready')): break
        time.sleep(.3)
    report = {}
    out = os.path.join(work, 'client.out')
    try:
        if name == 'vpn_up':
            route('vpn'); cap = Capture('a'); c = run_client(work, 25, out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'vpn_up_tcp_only':
            route('vpn'); cap = Capture('a'); c = run_client(work, 20, env='LAB_TCP_ONLY=1', out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'probe_pair':   # the address seen by the default route against the address seen straight out of the physical interface
            report['probe_pair'] = probe_pair()
        elif name == 'pinned_to_tunnel_address':   # what the guard sets while verified: listen and outgoing both the tunnel's own address (Elementum accepts an address or a name)
            route('vpn'); cap = Capture('a'); c = run_client(work, 25, env='LAB_LISTEN=10.8.0.2:6891 LAB_OUTGOING=10.8.0.2', out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'pinned_tunnel_fails':
            route('vpn'); cap = Capture('a'); c = run_client(work, 40, env='LAB_LISTEN=10.8.0.2:6891 LAB_OUTGOING=10.8.0.2', out=open(out, 'w')); time.sleep(12); report['before'] = cap.stop()
            ns('phone', 'ip link set utun0 down'); route('direct'); cap = Capture('b'); c.wait(); report['after_failure'] = cap.stop()
        elif name == 'blocked_without_vpn':    # the guard's block while no VPN exists: the household route is the only way out
            route('direct'); cap = Capture('a'); c = run_client(work, 25, env='LAB_TRAP=1', out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'blocked_then_vpn_verified_then_released_unpinned':   # the first design: the release restores the wildcard
            route('direct'); cap = Capture('a'); c = run_client(work, 40, env='LAB_TRAP=1 LAB_RELEASE_AT=15', out=open(out, 'w')); time.sleep(13); report['blocked'] = cap.stop()
            route('vpn'); cap = Capture('b'); c.wait(); report['after_release'] = cap.stop()
        elif name == 'blocked_then_vpn_verified_then_released':
            route('direct'); cap = Capture('a'); c = run_client(work, 40, env='LAB_TRAP=1 LAB_RELEASE_AT=15 LAB_PIN_ADDR=10.8.0.2', out=open(out, 'w')); time.sleep(13); report['blocked'] = cap.stop()
            route('vpn'); cap = Capture('b'); c.wait(); report['after_release'] = cap.stop()
        elif name == 'tunnel_fails_then_block':    # the failure is followed by the guard's block (as soon as its next look): what escapes in between is what matters
            route('vpn'); cap = Capture('a'); c = run_client(work, 45, env='LAB_TRAP_AT=22', out=open(out, 'w')); time.sleep(12); report['before'] = cap.stop()
            ns('phone', 'ip link set utun0 down'); route('direct'); cap = Capture('b'); time.sleep(8); report['failed_not_yet_blocked'] = cap.stop()
            cap = Capture('c'); c.wait(); report['after_block'] = cap.stop()
        elif name == 'tunnel_fails_no_kill_switch':
            route('vpn'); cap = Capture('a'); c = run_client(work, 40, out=open(out, 'w')); time.sleep(12); report['before'] = cap.stop()
            ns('phone', 'ip link set utun0 down'); route('direct'); cap = Capture('b'); c.wait(); report['after_failure'] = cap.stop()
        elif name == 'tunnel_fails_with_kill_switch':
            route('vpn'); cap = Capture('a'); c = run_client(work, 50, out=open(out, 'w')); time.sleep(12); report['before'] = cap.stop()
            route('killed'); ns('phone', 'ip link set utun0 down'); cap = Capture('b'); time.sleep(15); report['while_blocked'] = cap.stop()
            ns('phone', 'ip link set utun0 up'); route('vpn'); cap = Capture('c'); c.wait(); report['after_reconnect'] = cap.stop()
        elif name == 'started_before_vpn_no_kill_switch':
            route('direct'); cap = Capture('a'); c = run_client(work, 30, out=open(out, 'w')); time.sleep(10); report['before_vpn'] = cap.stop()
            route('vpn'); cap = Capture('b'); c.wait(); report['after_vpn'] = cap.stop()
        elif name == 'started_before_vpn_kill_switch':
            route('killed'); cap = Capture('a'); c = run_client(work, 30, out=open(out, 'w')); time.sleep(10); report['before_vpn'] = cap.stop()
            route('vpn'); cap = Capture('b'); c.wait(); report['after_vpn'] = cap.stop()
        elif name == 'ipv6_default_listen':
            route('vpn'); cap = Capture('a'); c = run_client(work, 20, out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'ipv6_listen_all':
            route('vpn'); cap = Capture('a'); c = run_client(work, 20, env='LAB_LISTEN="[::]:6891,0.0.0.0:6891"', out=open(out, 'w')); c.wait(); report['capture'] = cap.stop()
        elif name == 'outgoing_interface_pinned':
            route('vpn'); cap = Capture('a'); c = run_client(work, 40, env='LAB_OUTGOING=10.8.0.2', out=open(out, 'w')); time.sleep(12); report['before'] = cap.stop()
            ns('phone', 'ip link set utun0 down'); route('direct'); cap = Capture('b'); c.wait(); report['after_failure'] = cap.stop()
        else:
            raise SystemExit('unknown scenario %s' % name)
    finally:
        w.terminate(); w.wait()
    report['client_last'] = last(out)
    report['remote_saw'] = world_log(log)
    return report


ALL = ('probe_pair', 'pinned_to_tunnel_address', 'pinned_tunnel_fails', 'blocked_without_vpn', 'blocked_then_vpn_verified_then_released', 'tunnel_fails_then_block', 'vpn_up', 'vpn_up_tcp_only', 'tunnel_fails_no_kill_switch', 'tunnel_fails_with_kill_switch', 'started_before_vpn_no_kill_switch', 'started_before_vpn_kill_switch',
       'ipv6_default_listen', 'ipv6_listen_all', 'outgoing_interface_pinned')

if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('run as root (network namespaces)')
    work = tempfile.mkdtemp(prefix='vpnlab-')
    results = {}
    try:
        for name in (sys.argv[1:] or ALL):
            setup(); ns('phone', 'ip link set utun0 up', check=False)
            for f in ('ready',):
                if os.path.exists(os.path.join(work, f)): os.unlink(os.path.join(work, f))
            results[name] = scenario(name, work)
            print('done', name, file=sys.stderr)
    finally:
        teardown(); shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(results, indent=1))
