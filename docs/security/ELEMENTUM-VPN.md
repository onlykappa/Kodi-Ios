# Elementum and a VPN: source review, lab results and "Require VPN for torrents"

Status: **not claimed protected.** Host evidence only; nothing here was observed on an iPhone. Branch `claude/elementum-vpn-privacy`, base `main` at `cf42c63`.
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

`scripts/vpn_lab/` builds five Linux network namespaces (phone, household router, VPN exit, world, remote peer). The phone's default route decides the path; the remote
side records the source address of every tracker, DNS and peer connection, and `tcpdump` at the world namespace's two uplinks independently counts what arrived by
which path. Run as root with `pip install libtorrent`. **The client is libtorrent 2.1.1 from PyPI configured like Elementum (listen wildcard, DHT/LSD/UPnP/NAT-PMP off, announce to all), not the Elementum engine and not libtorrent 2.0.x:** the engine could not be built and run in this session, so these results describe libtorrent's behaviour, not Elementum's. A firewall does not hide anything: the capture is taken at the remote side, and "nothing arrived" is only claimed where the capture shows nothing arrived.

| Scenario | What the remote side saw (summary) |
|---|---|
| Tunnel up (uTP, then TCP only) | Tracker, DNS and peer traffic arrived **only** from the VPN exit's address; none on the household path. Download progressed. |
| Client started while no VPN, no kill switch | DNS, tracker and uTP arrived from the **household** address immediately. (This is the leak the feature exists to prevent.) |
| Tunnel fails while running, no kill switch | Over the 28 s observed after the failure nothing new arrived by either path; the transfer stalled. libtorrent's tracker and uTP sockets are bound to the tunnel's address, so on Linux they could not use the household route. **This is a property of those sockets on Linux; it was not shown for Darwin/iOS and must not be relied on.** |
| Tunnel fails, kill switch (blackhole) then reconnect | Nothing escaped while blocked; announces resumed through the exit after reconnect (data resumed slowly). |
| Started before the VPN, then route switched to VPN (no kill switch) | Leaked to the household address before the switch; after it nothing flowed (stale sockets) until restarted. Order matters: connect the VPN **first**. |
| Interface pinned (`outgoing_interfaces` = tunnel address) | Same observations as the unpinned tunnel failure. Pinning by name or address needs the tunnel's name or address, which on iOS changes: not used. |
| **Block applied (forced SOCKS5 proxy nobody listens on + session paused), no VPN, household route** | **Zero packets on either path**: no DNS, no tracker, no peer, no uTP, over 25 s. |
| Block applied, then lifted with the tunnel up | Zero packets while blocked; after the release all traffic arrived only from the VPN exit and the download ran (6.9 MB in the run). |
| Tunnel fails then block applied | Nothing arrived by the household path between the failure and the block, and nothing after (see the caveat on the third row). |
| IPv6 (default listen / `[::]` listen) | **Not run**: the sandbox kernel has no IPv6. Marked unverified. |

Raw capture files and addresses are not kept.

## 4. Feasibility of "Require VPN for torrents"

Options considered:

| Option | Verdict |
|---|---|
| Pin libtorrent to the tunnel interface (`listen_interfaces`/`outgoing_interfaces` by name) | Rejected: iOS tunnel names (`utunN`) change per connection and across VPN apps; hard-coding is brittle and the engine would stay pinned to a dead name. |
| Read another VPN app's status through NetworkExtension | Not available: an app sees only its own `NEVPNManager` configuration; Network Extension entitlements are not part of the free SideStore provisioning (per Apple's account model; not tested here). |
| Detect a tunnel-class interface | Cheap and useful as a *necessary* signal; not a proof (LocalDevVPN is one; so is any dead tunnel). |
| Compare the public address with the home address (the owner's idea) | Adopted as the *second* necessary signal. It proves the phone's default route currently exits somewhere other than home, which LocalDevVPN does not. It does not prove libtorrent's device-bound sockets take the same route, and a tunnel can fail between checks. |
| Ask the engine itself what address peers see | Not possible without a tracker or peer we control (no infrastructure is deployed or approved). |
| Block at the engine, not at the button | **Adopted** (section 5): a forced SOCKS5 proxy on a closed local port covers every entry point at once, because libtorrent then makes no direct connection (lab: zero packets), plus `/torrents/pause`. |

**Conclusion.** Generic detection cannot prove protection. What can be supported is a *fail-closed gate with best-effort verification*: the engine is blocked first and by
construction, unblocked only after two agreeing checks, re-blocked at the next look when anything changes. There is a gap of up to one look (1 s for the interface list,
20 s for the address) in which a tunnel can fail while the gate is open. **Only the VPN's own kill switch closes that gap**; the app says so and never shows a green "protected".

## 5. What was implemented

- `resources/lib/vpn_guard.py`: pure rules plus a `Guard` with everything injected; `service.py` runs it from startup (`vpn_guard_loop`).
- Setting `Require VPN for torrents` (Settings › Transfer settings › Privacy; off by default), optional "name of my VPN network" words, and the address-check services.
- States: `blocked` (no tunnel / no answer / same address as home / unexpected network / no home address learned / network changed) and `verified`
  ("VPN address check passed", deliberately not "protected"). Home addresses are learned only while no tunnel interface exists and kept as salted hashes in the profile folder.
- Block: Elementum's settings are replaced by the trap (`proxy_enabled`, SOCKS5 `127.0.0.1:1`, forced for peers, trackers and names, `use_proxy_http` off), the engine is
  reloaded and its session paused. The owner's own proxy settings are saved first and restored on release, when the feature is turned off, and after a restart. Progress is kept: pausing a session does not remove torrents.
- `elementum_download.follow` refuses to contact the engine while blocked and shows "Connect your VPN to continue"; the debrid cloud route is not gated because it makes no torrent connection. Direct entries to the engine (plugin menus, API calls, restored or seeding torrents) meet the engine-level block; they get the rate-limited notification, not a dialog.
- LocalDevVPN: not recognised by name or range; it fails the address comparison (its public address is unchanged) or, with no home address known, fails `no_home`.
- Normal Kodi playback and AirPlay do not use libtorrent and are untouched (the trap affects only the torrent engine; the add-on's HTTP stays direct).

Tests: `scripts/test_vpn_guard.py` (26 tests, registered in `import-review.yml`): rules, the whole sequence (VPN up, no VPN, LocalDevVPN-like tunnel, unexpected failure, deliberate disconnect, Wi-Fi to cellular, VPN replacement, restart with saved state, feature turned off, engine restart, no repeated reconfigure, hashed storage), the gated entry points. These test the code's decisions and its writes to Elementum's settings and API, **not** an iPhone's network.

## 6. Limits and open items (do not call this protected)

- The real engine was not run: the trap's effect on **Elementum 0.1.114 / libtorrent 2.0.x on iOS** is shown only for libtorrent 2.1.1 on Linux. Elementum applies the proxy keys as read in `service.go`; whether the add-on's settings write is picked up by `/reload` on the phone is unverified.
- A short window of up to ~20 s exists between address checks; a failing tunnel and a replaced VPN are noticed at the next interface change (1 s) or check.
- libtorrent's own sockets are not asked what they see; on iOS they might choose a physical interface when a tunnel changes. The block, not the check, is what protects, and only while the guard runs (the guard is a thread inside Kodi: if Kodi is suspended or killed while the door is open, nothing re-closes it until the next launch; the engine dies with Kodi, but a background-running engine with the VPN lost is exactly the case for the VPN's kill switch).
- Two public address-echo services are asked (defaults in the setting) and see the phone's current public address, with or without the VPN.
- The guard needs Elementum installed to write the trap; without it nothing runs and nothing is blocked.
- IPv6 untested; DNS and DHT only observed in the lab (zero packets when blocked; exit only when open).
- A first run with the VPN already on cannot learn the home address: turn the VPN off once, or name the VPN's network in the setting.

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
