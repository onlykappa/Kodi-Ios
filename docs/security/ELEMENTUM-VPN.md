# Elementum and a VPN: source review, lab results and "Require VPN for torrents"

> **Update, 2026-11-23: the "Require VPN for torrents" guard described in sections 4 and 5 was removed at the owner's request.** Reason: every selected torrent already goes
> through AllDebrid (the phone never joins a swarm), so the guard added code for a path that is not used. What stays: the source review, the lab, the findings and the phone
> checks. What replaced it: Elementum's DHT is turned off once (ISSUE-455) and a confirmation popup is being designed for any request that would reach Elementum's own engine.
> The removed code is in this branch's history (commit `e6c5b87`) if it is ever wanted again. Sections 4-5 below describe it as it was; they are no longer implemented.

Status: **not claimed protected.** Host evidence only; nothing here was observed on an iPhone. Branch `claude/elementum-vpn-privacy`, base `main` at `cf42c63`.
**Headline finding (lab, libtorrent 2.1.1 on Linux): a wildcard-listening session sends tracker and uTP traffic out of the physical interface even with a VPN up as the default route. The guard therefore pins libtorrent to the tunnel's address while verified.**
No credentials, public addresses, torrent identifiers, captures or private logs are in this document or the repository (the lab uses reserved documentation
ranges: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24).

## 1. What the source review established

Pinned versions (`migration/elementum-ios/source-lock.json`): plugin `plugin.video.elementum` 0.1.114 (`8ea802e`), engine `cdab7e2`, libtorrent-go `d8763f5`
(libtorrent 2.0.x). The engine ships in the app as `Frameworks/elementum.framework` and runs inside Kodi's process; the add-on talks to it at `127.0.0.1:65220`.
Read from the engine source at that commit (`bittorrent/service.go`, `config/config.go`):

| Question | Finding |
|---|---|
| Interface selection | `calcInterfaces()` starts from `listen_interfaces = "0.0.0.0"` when `listen_autodetect_ip` is on (default). `outgoing_interfaces` is empty by default. Nothing in the engine knows about a VPN or refuses to run without one. |
| What the wildcard means | libtorrent expands it into per-interface listen sockets. In the lab those are bound to the interface's device. The outgoing TCP socket binds `0.0.0.0:0` (route decides); outgoing uTP and tracker requests leave from a listen socket (`LOCAL_ENDPOINT` was the tunnel's address). |
| IPv6 | With the default wildcard only IPv4 listen addresses result (`GetInterfaceAddrs` returns v4 and v6 only for a named interface). `internal_dns_skip_ipv6` defaults on. A user who types an interface name gets both families. **IPv6 was not tested** (the sandbox kernel has no IPv6). |
| Peers, uTP, trackers, web seeds | All inside libtorrent. They go through a proxy only if `proxy_enabled` with a host is set (`service.go` ~376-411): `proxy_peer_connections`/`proxy_hostnames` follow `use_proxy_download`, `proxy_tracker_connections` follows `use_proxy_tracker`, `force_proxy` follows `proxy_force`. Proxy types are SOCKS4/5, SOCKS-with-HTTP and I2P: **Proton does not offer SOCKS5** ([Proton: "Why Proton VPN does not offer a SOCKS5 proxy"](https://protonvpn.com/support/socks5)), so the proxy feature cannot point at Proton. |
| DNS | libtorrent resolves tracker and web-seed names with the system resolver (inside the same process, over whatever route the OS gives it) unless `proxy_hostnames` is on. Elementum's own DNS client (`internal_dns_enabled`, default **off**) is for the add-on's HTTP, not libtorrent. |
| DHT / LSD / UPnP / NAT-PMP | `startServices()` enables DHT unless `disable_dht`, LSD unless `disable_lsd`. On this phone `phone_housekeeping` turns UPnP, NAT-PMP and LSD off once (`bootstrap.py`, ISSUE-070); an owner who turns them back on keeps them. NAT-PMP scans only run with it enabled (`VPNIPs()` is used only there). |
| Startup and restored transfers | `loadTorrentFiles()` runs at engine start; `autoload_torrents` defaults on but `autoload_torrents_paused` also defaults **on**, so restored torrents start paused. Completed torrents seed until ratio 7 (`seed_time_ratio_limit` 700) unless `seed_forever`. |
| Reconfiguration | `/reload` calls `Reconfigure()` (re-reads settings through the add-on). `networkRefresh()` re-evaluates the interface list every 5 minutes and the NAT port every 45 s. |
| Local API | `/torrents/pause` and `/torrents/resume` pause and resume the whole libtorrent session. |

Concrete defects found: **none in the engine to fix** (it has no VPN concept by design). The gap is ours: nothing stops it from running while no VPN is on.
Normal settings that matter: the wildcard listen address, system-resolver DNS, DHT on by default, seeding after completion.

## 2. Proton VPN Plus and Apple, what is and is not verified

I could not read Proton's pages from this session (the host is outside the network allowlist; a fetch agent failed the same way). What follows comes from search
excerpts of Proton's own support pages and must be confirmed on the phone. Apple's `NEVPNProtocol` property pages were read from Apple's documentation data.

- **Kill switch.** Proton's iOS pages describe a standard kill switch that blocks traffic when the VPN drops unexpectedly and stays inactive after a deliberate disconnect, and
  an *advanced* kill switch (beta on iOS) that also applies after a manual disconnect, so the phone has no internet until it connects or the switch is turned off
  ([How to use kill switch](https://protonvpn.com/support/what-is-kill-switch), [advanced kill switch](https://protonvpn.com/support/advanced-kill-switch)).
  Known limits stated there: some Apple-service DNS requests can bypass the VPN; LAN access improved in later releases. Mechanism not documented in what I read.
- **P2P and ports.** Proton describes P2P on its P2P servers and port forwarding only for desktop clients; nothing found mentions port forwarding on iOS.
  *Provider P2P support says torrents are allowed; it is not evidence about routing.*
- **IPv6.** Proton's IPv6 page says IPv6 is turned off in the Windows, macOS and iOS/iPadOS apps so an IPv6 address cannot be exposed; a later recap says iOS IPv6 support is still being added (state may have changed).
- **No SOCKS5** (above).
- **Apple.** `includeAllNetworks` routes traffic through the tunnel except designated system traffic (DHCP, captive portal, cellular services, companion device). `excludeLocalNetworks` defaults to **true on iOS** and applies only with `includeAllNetworks` or `enforceRoutes`; AirPlay is named as local traffic. `enforceRoutes` makes the tunnel's routes win over the local routing table. Only the VPN app can set these; a third-party app cannot read or change another VPN's configuration.
- **Not verified:** whether Proton's iOS kill switch uses `includeAllNetworks`; whether iOS allows two VPN configurations at once (I could not confirm it from a source and the answer to "what does activating LocalDevVPN do to Proton" must be observed on the phone: section 7).

### Recommended Proton settings (to be confirmed on the phone)
1. Plus subscription, connect to a **P2P-marked server**.
2. Kill switch: the **advanced** one if it is offered on your app version (blocks internet whenever you are not connected, including after a manual disconnect); otherwise the standard one, and understand that a manual disconnect then leaves the phone unprotected.
3. Auto-connect on, where the app has it. Keep LAN access on so Kodi and AirPlay keep working.
4. Open Kodi **after** Proton connects; do SideStore refreshes with Kodi closed.

## 3. The lab, and what it shows

`scripts/vpn_lab/` builds five Linux network namespaces (phone, household router, VPN exit, world, remote peer). The phone's routing table is the only thing deciding the path,
as on a phone with a VPN: with the VPN up the tunnel's default route wins by metric **and the physical network's own default route stays in the table** (iOS keeps one
scoped to each interface). The remote side records the source address of every tracker, DNS, echo and peer connection, and `tcpdump` at the world namespace's two
uplinks independently counts what arrived by which path. Run as root with `pip install libtorrent`. **The client is libtorrent 2.1.1 from PyPI configured like
Elementum (wildcard listen, DHT/LSD/UPnP/NAT-PMP off, announce to all), not the Elementum engine and not libtorrent 2.0.x**; the engine could not be built and run in this
session, so these results describe libtorrent on Linux, not Elementum on an iPhone. No firewall is used: "nothing arrived" is claimed only where the capture shows nothing arrived.

**An earlier run of this lab had no physical default route while the tunnel was up and showed a clean result for a plain wildcard session. That model was wrong:
with the physical default route present, as on a real phone, the same session leaks. Both are in the table; only the second is a fair test.**

| Scenario (realistic routes unless noted) | What the remote side saw |
|---|---|
| Tunnel up, wildcard listen (Elementum's default), uTP | **Leak with the VPN on:** the household address reached the tracker (84 packets) and the peer over uTP (386 packets); DNS and part of the tracker traffic came from the exit. libtorrent's per-interface listen socket for the physical interface sends out of that interface, whatever the default route says. |
| Same, TCP only | Peer connection from the exit, but 68 tracker packets from the household address. |
| Tunnel fails while running, wildcard, no kill switch | Everything continued from the household address (uTP 439, tracker 82 packets); the download went on. |
| Tunnel fails, kill switch (blackhole) then reconnect | Nothing arrived while blocked; after reconnect traffic resumed by the exit, with some tracker packets still by the household path. |
| Started before the VPN, then VPN connected, no kill switch | Household address throughout, including after the VPN came up (sockets stay on the physical interface). Connect the VPN first. |
| `outgoing_interfaces` = tunnel, listen still wildcard | Peer traffic from the exit, tracker still from the household address (39 then 77 packets). |
| **Listen and outgoing both pinned to the tunnel's address** | **Zero packets by the household path with the VPN up** (6.9 MB downloaded, tracker/DNS/uTP all from the exit); **when the tunnel then fails (household default route present) zero packets by either path: it fails closed.** |
| **Block applied (forced SOCKS5 proxy on a closed port + paused session), no VPN, household route** | **Zero packets on either path** (no DNS, tracker, peer or uTP) over 25 s. |
| Block applied, then released with the pin and the tunnel up | Zero packets while blocked; after release everything arrived only from the exit and the download ran. (Released without the pin, as the first design did, it leaked the household address again: the pin is required.) |
| Echo probe by the default route and straight out of the physical interface (`vpn_probe`, `SO_BINDTODEVICE`; Darwin would use `IP_BOUND_IF`) | VPN carrying the traffic: default route showed the exit, the physical interface the household address → `verified`. Tunnel up but default route direct (what LocalDevVPN looks like), and tunnel failed: both answers the household address → `blocked: same as direct`. Kill-switch blackhole: both failed → `blocked`. |
| IPv6 (default listen / `[::]` listen) | **Not run**: the sandbox kernel has no IPv6. Unverified. |

Raw captures and addresses are not kept.

## 4. Feasibility of "Require VPN for torrents"

| Option | Verdict |
|---|---|
| Pin libtorrent by a fixed interface name | Rejected: iOS tunnel names (`utunN`) change per connection and per VPN app. |
| Pin libtorrent to whatever tunnel address the interface list shows **right now**, set by the guard each time it verifies, removed when it stops | **Adopted.** It is not a hard-coded name; Elementum accepts an address in `listen_interfaces`/`outgoing_interfaces` (`GetInterfaceAddrs` parses an IP first). Lab: no household packets with the VPN up, fail-closed when the tunnel dies. |
| Read another VPN app's status through NetworkExtension | Not available: an app sees only its own `NEVPNManager` configuration; Network Extension entitlements are not part of the free SideStore provisioning (per Apple's account model; not tested here). |
| A tunnel-class interface exists | Necessary, not sufficient. |
| The address by the default route differs from the address straight out of the physical interface | **Adopted as the test that a VPN really carries the traffic.** It needs no list of home networks, so it holds on any network and rejects LocalDevVPN and a split-tunnelled "on" VPN. A VPN kill switch can close the physical path; then the question fails and the guard falls back to the learned home addresses or a network name you gave (never a pass by itself). |
| Ask the engine what address peers see | Not possible without a tracker or peer we control (no infrastructure is deployed or approved). |
| Block at the engine, not at the button | **Adopted:** a forced SOCKS5 proxy on a closed local port covers every entry point at once (lab: zero packets), plus `/torrents/pause`. |

**Conclusion.** Generic detection cannot prove protection, but it is strong enough to be a **gate**, and pinning makes the engine itself unable to use the physical network
while the gate is open (in the lab). What remains: the guard is a thread inside Kodi that looks at the interface list every second and at the addresses every 10 s, so there
is a window of up to ~10 s in which a *changed route* is not yet noticed; with the pin, a dead tunnel address stops the engine by itself in that window (lab), which is the
Kodi-side kill switch. The VPN's own kill switch stays the protection for everything else. The app never shows "protected", only "VPN address check passed".

## 5. What was implemented (REMOVED 2026-11-23, see the note at the top)

- `resources/lib/vpn_probe.py`: the two-way address question (`SO_BINDTODEVICE` on Linux for the lab, `IP_BOUND_IF` on Darwin, whose effect on iOS is **unverified**).
- `resources/lib/vpn_guard.py`: pure rules plus a `Guard` with everything injected; `service.py` runs it from startup (`vpn_guard_loop`).
- Setting `Require VPN for torrents` (Settings › Transfer settings › Privacy; off by default), optional "name of my VPN network" words, address-check services (two must agree).
- Sequence: feature on → **block first** (pause the session, then the closed-port proxy, reload); every second the interface list is read; a change in tunnels or link kind blocks at once;
  with a tunnel present the address is asked by the default route and straight out of each physical interface; **two agreeing checks 4 s apart** lift the block: the owner's own proxy settings
  are put back, listen/outgoing are pinned to the tunnel's address(es), the engine reloaded and resumed; **while verified a check every 10 s (one service)**; any failed or
  differing check blocks again. Turning the feature off restores every setting the guard touched (the owner's originals are saved first, kept across restarts). Progress is kept: pausing a session removes nothing.
- Notifications: "Torrents stopped: Connect your VPN to continue…" (and the other reasons, in words) and once "VPN is on. Torrents are running again."; seamless when the VPN is simply on.
- `elementum_download.follow` refuses to contact the engine while blocked and shows the dialog; the debrid cloud route is not gated because it makes no torrent connection.
  Other entries (plugin menus, API calls, restored or seeding torrents) meet the engine-level block.
- LocalDevVPN: not recognised by name or range; the two-way question gives equal answers, so it is `blocked`.
- Ordinary Kodi playback and AirPlay do not use libtorrent and are untouched.

Tests: `scripts/test_vpn_guard.py` (37, registered in `import-review.yml`) cover the rules and the whole sequence (VPN up on an unseen network, no VPN, a helper tunnel on an unseen network, a tunnel that
stays but stops carrying traffic, unexpected failure, deliberate disconnect, Wi-Fi to cellular, VPN replacement and re-pinning, restart with saved state, feature off undoing
proxy and pin, engine restart, no repeated reconfigure, hashed storage, the gated entry points, the probe's interface options). They test the code's decisions and its writes to Elementum's settings and API,
**not** an iPhone's network.

## 6. Limits and open items (do not call this protected)

- The real engine was not run: the trap and pin are shown only for libtorrent 2.1.1 on Linux. That Elementum applies them on `/reload` through the add-on's settings is read from source, not observed.
- Whether `IP_BOUND_IF` to the physical interface bypasses a running VPN on iOS (and what a VPN kill switch does to it) is the key unknown for the two-way question; if iOS refuses or the kill switch closes it, the guard needs a learned home address or a network name (the setting) instead.
- A window of up to ~10 s remains between address checks (1 s for interface changes). The pin closes most of it in the lab; the lab is not iOS.
- On iOS libtorrent may enumerate more than IPv4 interfaces; the pin names only IPv4 tunnel addresses, so IPv6 is not used while pinned. IPv6 was not tested.
- Two public address-echo services are asked and see the phone's current public address, with or without the VPN; the direct question goes to the first only.
- The guard needs Elementum installed, and Kodi running: it is a thread inside Kodi.
- A first run with the VPN already on and the physical path closed by the VPN cannot learn a home address: name the VPN's network in the setting, or turn the VPN off once.

## 7. Phone checks (not done; each is unverified until you run it)

Use only a torrent you are allowed to download (for example a public Linux ISO), and have the log (Settings › Export logs) ready. In Settings › Transfer settings › Privacy turn **Require VPN for torrents** on.
1. **No VPN:** start a torrent download. Expect the "Connect your VPN to continue" dialog; nothing downloads; the log says `vpn guard: on; torrents blocked`.
2. **Learn home:** with the VPN off, wait a minute (log: `learned a home address`). Connect Proton (P2P server). Within ~10 s the log says `VPN address check passed twice`; the download runs.
3. **Remote observer:** while it runs, open a tracker-seeded torrent from a peer you control (or a public tracker's IP report) and confirm the address seen is Proton's exit, not your home address.
4. **Unexpected failure:** with Proton's kill switch **off**, turn Wi-Fi off and on / force the tunnel down; expect the block within a few seconds; with the kill switch **on**, expect no traffic at all.
5. **Deliberate disconnect:** disconnect in the Proton app; expect the block at the next look; reconnect; expect a fresh verification (not an instant resume).
6. **Wi-Fi to cellular and back** with the download running; expect a block and re-verification each time.
7. **LocalDevVPN:** run a SideStore refresh (Kodi open, then closed). Record whether Proton stays connected, is replaced or is interrupted, and whether the guard blocked. Expect `same address as without a VPN` blocks.
8. **Replace the VPN** with another app's tunnel while downloading; expect a block and re-check.
9. **Restart Kodi** with a saved transfer and the VPN off: nothing may start; with the VPN on: it resumes after verification only. Progress must be unchanged.
10. **IPv6:** on a network with IPv6, run a torrent against an IPv6-reachable peer you control and confirm that peer never sees an IPv6 address from the phone (a browser IPv6 test does not show what the engine does).
11. Check AirPlay and an ordinary Drive/Umbrella video still play with the guard blocked.
