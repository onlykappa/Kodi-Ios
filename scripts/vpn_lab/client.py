"""The phone side of the lab (runs inside the `phone` namespace): a libtorrent session configured the way Elementum configures its own (see docs/security/
ELEMENTUM-VPN.md for the source lines), downloading the generated torrent. Prints one JSON line per second."""
import json, os, sys, time
import libtorrent as lt

WORK, SECONDS = sys.argv[1], int(sys.argv[2])
listen = os.environ.get('LAB_LISTEN', '0.0.0.0:6891')   # Elementum's default: calcInterfaces() starts from "0.0.0.0"
settings = {'listen_interfaces': listen, 'enable_dht': False, 'enable_lsd': False, 'enable_upnp': False, 'enable_natpmp': False,   # phone_housekeeping + startServices
            'announce_to_all_tiers': True, 'announce_to_all_trackers': True, 'min_reconnect_time': 5,   # Elementum sets 20; shorter so the 40 s runs see reconnects
            'user_agent': 'Elementum-lab', 'alert_mask': 0}
if os.environ.get('LAB_TCP_ONLY'):   # Elementum's DisableUTP
    settings.update({'enable_outgoing_utp': False, 'enable_incoming_utp': False})
if os.environ.get('LAB_OUTGOING'):
    settings['outgoing_interfaces'] = os.environ['LAB_OUTGOING']
TRAP = {'proxy_type': lt.proxy_type_t.socks5, 'proxy_hostname': '127.0.0.1', 'proxy_port': 1, 'proxy_peer_connections': True,
        'proxy_tracker_connections': True, 'proxy_hostnames': True, 'force_proxy': True}   # the guard's block: a SOCKS5 proxy nobody listens on, forced (vpn_guard.TRAP)
RELEASE = {'proxy_type': lt.proxy_type_t.none, 'force_proxy': False}
if os.environ.get('LAB_PIN_ADDR'):   # the guard's release: libtorrent listens and goes out by the tunnel's own address only
    RELEASE.update({'listen_interfaces': os.environ['LAB_PIN_ADDR'] + ':6891', 'outgoing_interfaces': os.environ['LAB_PIN_ADDR']})
trap_from_start = bool(os.environ.get('LAB_TRAP'))
if trap_from_start:
    settings.update(TRAP)
ses = lt.session(settings)
if trap_from_start:
    ses.pause()
h = ses.add_torrent({'ti': lt.torrent_info(os.path.join(WORK, 'test.torrent')), 'save_path': os.path.join(WORK, 'dl')})
t0 = time.time(); last = 0
while time.time() - t0 < SECONDS:
    time.sleep(1)
    now = time.time() - t0
    if os.environ.get('LAB_TRAP_AT') and now >= int(os.environ['LAB_TRAP_AT']) and not os.environ.get('_TRAPPED'):
        os.environ['_TRAPPED'] = '1'; ses.apply_settings(TRAP); ses.pause(); print(json.dumps({'event': 'trap', 't': round(now)}), flush=True)
    if os.environ.get('LAB_RELEASE_AT') and now >= int(os.environ['LAB_RELEASE_AT']) and not os.environ.get('_RELEASED'):
        os.environ['_RELEASED'] = '1'; ses.apply_settings(RELEASE); ses.resume(); print(json.dumps({'event': 'release', 't': round(now)}), flush=True)
    s = h.status()
    if int(time.time() - t0) % 5 == 0:
        h.force_reannounce()   # the tracker interval Elementum would have run into over a longer transfer
    print(json.dumps({'t': round(time.time() - t0), 'bytes': s.total_done, 'peers': s.num_peers, 'state': str(s.state)}), flush=True)
    if s.is_seeding: break
