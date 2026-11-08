# Build 194: prepared movies fail to start with AirPlay

Source follow-up on `claude/trusting-euler-kgug98`, PR #16. No build or release authorized for this pass.
The owner's supplied `kodi.log` stays outside Git. Times below are the log's local times on 2026-11-07;
the review/fix date is 2026-11-08. Build identity in the log: build 194, source `8e0a8a1`, KodiAirPlay r33.

## Evidence

| Log lines | Observation |
|---|---|
| 1701, 1709 | Play on TV opened at 18:11:08; native `start:` relayed at 18:11:15. |
| 1735, 1797, 1909, 1964 | AVPlayer repeatedly reports NSURLErrorDomain -1004, "Could not connect to the server." |
| 1770, 1784 | Two Play on TV invocations opened at 18:12:45 and 18:12:50. |
| 1798–1800, 1909–1912 | Failed-player events and prepared-file/start lines interleave across attempts. One outcome reports 24.5 seconds; the earlier attempt takes over a minute. |
| Entire supplied log | Zero `Kodi iOS AirPlay: GET /…` lines and no receiver `client:` evidence. No successful movie playback on the TV is demonstrated. |

The old `start:` line contains the **source** URL, not the LAN URL returned by `kr_remux_start`. The prepared
route listens on INADDR_ANY and hands AVPlayer a token-protected URL using `lan_address`. The host is absent
from this log. Earlier requests were logged only after serving them, and accepts were not logged at all, so
the log cannot distinguish no TCP connection from a connection that never completed a request/response.

## Findings and changes

1. **Permission metadata was missing.** Staging now adds `NSLocalNetworkUsageDescription` with the owner's exact
   purpose string, independently of portrait skin installation. Other plist keys and existing Bonjour declarations
   are preserved. No new `NSBonjourServices` entries: our TV discovery uses unicast probes, not Bonjour browsing
   or registration. The foreground Play on TV discovery is the network operation that can trigger the prompt.
2. **The cause is not proven to be permission denial.** Apple's current [TN3179](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy)
   exempts listening/accepting incoming TCP from Local Network access. The purpose string fixes discovery's
   missing declaration; it does not prove the reason AVPlayer failed. A wrong interface, Wi-Fi isolation, or
   overlapping sessions remain plausible. r34 source requires an up IPv4 `en0` on iOS instead of falling back to
   a cellular/VPN interface. Host tests may still use their first up non-loopback IPv4 interface.
3. **Useful connection evidence needs native support.** r34 source logs interface/IPv4, bind/listen success or
   errno, the served host:port without the token, each accepted peer and its first request line before serving,
   and start-to-first-TV-request time. A non-draining JSON snapshot exposes the endpoint and request counters to
   Python, avoiding a race with the service's log relay. The phone's own player does not count as a TV request.
   Python records host/port separately and preserves only the public route when sanitizing a served URL.
4. **Fail fast and recover.** The controller checks the first TV request with a 15-second start deadline.
   It closes AirPlay, resumes Kodi, and displays the requested Local Network/same-Wi-Fi instructions when the
   phone was not reached. It does not repeat that attempt automatically. Cancel remains quiet; an arrived
   request prevents a false network timeout while the source is being read. Direct HLS retains its player path.
   A persistent `work_state.need('airplay_network', …, profile)` marker crosses Kodi script/service interpreter
   boundaries, so the shared status snapshot and bell show the needs-you state. A successful connection clears
   it. Existing card/dialog controls and typography are reused; no new layout, colour or button style.
5. **One attempt owns the picker and connection.** The old guard was set after the picker returned: two pickers
   could pass the initial timestamp check. A kernel file lock now covers the entire invocation, including
   discovery and picker cancellation, with unconditional release. A rejected invocation cannot clear the owner's
   property. r34 source additionally orders native starts/stops on one queue and rejects late player presentation
   from a canceled generation.

## Delivery boundary

The Python/controller/plist changes are source-ready. They work with r33 using shared log evidence for request
tracking; that fallback depends on the native log/service relay and cannot report accepted peers or an authoritative
TV request count. The complete diagnostics, strict Wi-Fi interface selection, cancellation generation guard and
app Settings deep link require **KodiAirPlay r34**. Its source is prepared, but **no native build or release was
run and no r34 asset/hash was invented**. `migration/airplay-ios/source-lock.json` remains pinned to released r33.
The existing Kodi executable r24 pin is also unchanged.

After owner approval: run the native host/CI checks, build/release r34 from this exact source, verify the artifact,
then pin its real release hash in a separate `[skip ci]` commit. Only after the owner's further go-ahead should
an IPA be built. The r33 fallback shows manual Settings instructions; r34 uses
[`UIApplicationOpenSettingsURLString`](https://developer.apple.com/documentation/uikit/uiapplication/opensettingsurlstring)
on the main queue. It never attempts to change permission itself.

## Validation and device hand-over

- `test_play_on_tv_network.py`: 13 regressions exercise actual controller failure/success/cancellation, the
  15-second clock, early -1004 without retry, direct HLS, persisted needs across module instances, process-shared
  lock ownership, duplicate picker entry, cleanup after exceptions, token redaction, native source contracts,
  and Settings fallback. Native source contracts are static tests, not a compiled r34 runtime test.
- `test_customized_ipa.py`: staged plist purpose/preservation regression. Existing start/room assertions now
  follow the earlier lock, progress-before-start order and retry restriction. No regression was removed.
- The full sweep exposed an existing stale `test_glassbar.py` pin: the branch already pins Kodi r24, but the test
  still expected r23. Updated the exact tag/checksum assertion to the existing r24 lock; no lock was changed.
- Final validation: **82/82 test scripts pass**, excluding only `test_drive_runtime.py` as requested. The initial
  sweep had that one stale-pin failure; its 27 tests pass after correction. Final targeted controller/bridge
  retests also pass. `python3 -B scripts/check_project.py` and `python3 -B scripts/check_ui_guidance.py` pass;
  `bash -n migration/airplay-ios/build-airplay.sh` and `git diff --check` pass. No native compiler or app build ran.
- Visual/device verification remains **PENDING**. The supplied log is **device evidence of failure**. No new
  screenshot, desktop rig run, native binary, IPA or device-success result is claimed.

On the iPhone, check Local Network access when Play on TV is first used, tap Play on TV twice while its picker is
open, cancel and retry, and play a ready movie. With r34, the next log should show `interface=en0`, listen success,
the correct LAN host/port, `accept: peer=…`, the first token-redacted request, and its elapsed time. If no TV request
arrives, confirm the 15-second recovery and needs-you card, then its Settings button. Confirm the card clears after
a successful attempt and a source-read delay after a request is not reported as a LAN permission failure.
