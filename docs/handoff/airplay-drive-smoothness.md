# Handoff: Play on TV of a Google Drive episode stalls (owner log f93a3233, build 657)

Paste this whole file as the first message of a fresh session on branch `claude/sports-instant-open` (or its successor). Read first, in this order:
`AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `docs/PROGRESS.md`, `docs/ISSUES.md` (last entries ISSUE-436..442), `docs/DECISIONS.md`, `docs/AIRPLAY.md`,
`migration/airplay-ios/remux/FINDINGS.md`. Project rules that apply here: host checks never prove phone behaviour (label every claim host test / desktop rig /
device); never merge, release or publish an IPA or a framework without the owner's explicit request in the current message; new tests go in
`.github/workflows/import-review.yml`; `python3 -B scripts/check_project.py` and `check_ui_guidance.py` pass before every commit; no private data, tokens or
stream links in logs or commits; commit trailers as in recent commits; never force-push; another agent also pushes to this repo.

## 1. What the owner saw

Casting a Google Drive library episode (TMDb 124364 S4E4, 1080p H.264, about 12.3 Mbit/s video, 7727 MiB, 520 six-second segments) to an Apple TV on the same
Wi-Fi: it played for about 40 s, then froze and ended with "The TV could not play the converted stream". "The connection speed is amazing": a speed test is fine.
Note "downloaded" in the owner's words means *in the Google Drive library*; the log says `Drive copy opened through the app proxy`. Nothing is on the phone.

## 2. What the log proves (log f93a3233, 18:18:56-18:20:24, build 657, AirPlay framework r71 in that build)

- The TV reported `player: error log: -16830 CoreMediaErrorDomain Media file not received in 13s (seg110.m4s)` at 18:19:36.8. The app's recovery then ran
  (`stuck ... playing again` 18:19:41, `reloading the stream there` 18:19:46, `stall recovery timed out before the seek completed`, `stopped: The TV could not
  play the converted stream` 18:20:19) and failed.
- The phone made each 6-second video segment slower than real time: `copy: video segment N in X ms` = 109: 9063, 110: 7276, 111: 3160, 112: 5446, 113: 7297 ms
  (about 6.4 s average for 6 s of video). The first segment took 1627 ms (cache). The TV was started after ONE segment (`startup: buffered video and audio at 649.2 s
  (segment 108) in 1627 ms`), so there was no cushion.
- The Drive reads behind each segment are many small ranges: the proxy logs `Drive range: start=... cached=0` at steps of 128 KiB-1 MiB, each preceded by
  `Drive read: kind=range ... headers_ms=300-1700` (time to first byte), and 22 of 91 reads were `attempt=2` (a retry). Per-request latency, not bandwidth, is the limit.
- Sending to the TV collapsed while the phone was also reading Drive: `GET /video/seg110.m4s 200 2908698 B 19285 ms` (about 1.2 Mbit/s) and seg111 16347 ms, against
  `GET /video/seg111.m4s 200 3225592 B 773 ms` (about 33 Mbit/s) when the same segment was resent from cache with nothing else running. The best sends while
  producing were 0.7-1.0 MB/s (6-8.6 Mbit/s), below the stream's 12.3 Mbit/s. The link can do 33 Mbit/s idle; it cannot do Drive-down plus TV-up at once (half-duplex
  airtime, the TV also on Wi-Fi through the router, unknown band: not in the log).
- `Receiver write failed (32)` (TV hung up mid-request) at 18:19:09, 18:19:54, 18:20:24: the TV's own per-request timeouts.
- No `Drive cache:` filler line appears at all in the AirPlay minute (only `prefetched ... (28 of 7727 blocks)`, which is the head and tail only).

## 3. Root causes, ranked, with where to look

A. **The Drive playback cache does not help a Play on TV conversion.** `migration/bundled-bootstrap/service.py` (~line 310) installs `CacheCleaner`: on Kodi's
   `Player.OnStop` it calls `drive_proxy.clear_cache()` (`drive_proxy.py` ~704), which `stop_all()`s the fillers and clears the blocks. Handing a video to the TV
   stops Kodi's own player, so the cache and the filler are wiped exactly when the converter starts reading. After that `Filler.want()`
   (`drive_cache.py` ~205) restarts a job only when `allowed()` (Wi-Fi) is true AND `free() >= min(size, CAP_BYTES) + FREE_MARGIN` = 3 GB + 2 GB, silently returning
   otherwise (no log), and for a 7.5 GB file it only fills a window of CAP/3 (1 GB) ahead. The log shows no filler at all. This is a Python-side, host-testable fix.
B. **The native reader is latency-bound.** `migration/airplay-ios/remux/src/kr_source.c`: `SOURCE_BLOCK` 128 KiB, `AHEAD_HELPERS` 2, `AHEAD_CHUNK` 8 blocks (1 MiB per
   helper request), and the helpers start only when the source is judged slow (`AHEAD_BELOW` 1.5 MiB/s) and the cursor reads sequentially. With 0.3-1.7 s to first byte
   per request, 1 MiB requests give roughly 1 MB/s per helper. Larger helper requests (for example 8 MiB), more helpers (3-4) and an earlier switch-on would cut the
   overhead. Native change: needs a new framework revision (r73) and the pin process in section 6.
C. **No cushion before the TV starts.** `kr_remux_prime_for` (`kr_remux.c` ~2145) and the Python start-up (`cast.py`, `airplay_flow.py`) start the TV after one segment.
   r71 added a longer read-ahead lead (ISSUE-393, `test_video_lead_is_long_enough`) but the TV is still told to start at once. Start the TV only when about 25 s
   (4 segments) of video and audio are made, with a bounded wait and a visible "Getting it ready" state.
D. **Drive reads and TV sends compete for one radio.** Nothing in the app orders them. Options: hold the proxy's background reads while a segment is being written to
   the TV (the native server knows; `kr_http`/`kr_remux.c` send path), or stage ahead in bursts so the TV link has the radio to itself (A does this).
E. **Recovery is too slow.** A stall is noticed at 668 s, retried at 5 s and 10 s, and given up at 45 s. For a segment the TV already timed out on, resend or restart the
   one request at once; if the buffer is empty, show "Buffering on the TV" and wait for the cushion (C) instead of ending.
F. Possible, unverified: 1 in 4 Drive reads is `attempt=2` (stale pooled connection, `drive_proxy.Upstream.request`, SPARE_MAX_AGE 45 s). Measure why before changing it.

## 4. Task

Make a Drive library episode cast to an Apple TV play without stalls on a home Wi-Fi where one direction tests fast. Do A, C and D-as-staging first (Python and
Python-driven start-up, no native build), prove them with host tests, then B and E if the log of a phone test still shows production slower than real time.
Do not lower picture quality or switch to converting the picture.

Concrete steps:
1. Reproduce the wipe in a host test: start a proxy with a `DiskBlocks` cache and a `Filler`, serve a fake Drive file, fire `Player.OnStop` handling, then read ranges as the
   converter would; show the cache is empty and the filler stopped. Fix: keep the cache and the filler alive when the stop is the hand-off to AirPlay
   (`airplay.starting(home_window)` / the Play on TV opened property, see `cast.py` and `airplay_flow.py`), clear it when AirPlay itself ends.
2. Make the filler serve the converter: follow its read positions (video, audio and subtitle stretches: `Filler._follow`, `CURSORS`), fill sequential 8-32 MiB chunks
   ahead of the TV's playhead, and keep a window in memory or on disk big enough for the cushion in step 3 (CAP_BYTES is 3 GB; the file here is 7.5 GB, so the window is
   about 7 minutes). Log why it declines (not Wi-Fi, not enough free space, over the window) once per file.
3. Delay the TV start until about 25 s of video and audio are made (config constant, with a timeout of about 45 s after which it starts anyway) and say so on screen.
4. Order Drive reads and sends: while a segment is being written to the TV, background read-ahead waits (a Home property the native layer or the proxy can read), with a
   cap so it never starves production.
5. Add an on-phone diagnostic line per cast every 30 s: segments made vs played, seconds of cushion, Drive read rate, TV send rate, filler state. The next owner log must
   say which of A-F is still true.
6. Only if needed, B (kr_source.c constants) and E (native recovery), following section 6.

## 5. Acceptance (host tests; label everything else "device, unproven")

New or changed tests, each listed in `.github/workflows/import-review.yml`: cache survives the hand-off and clears when AirPlay ends; filler starts for a 7.5 GB file with
a window, declines with a logged reason below the free-space limit; start-up waits for the cushion and has a timeout; reads are held while a send is in flight and
released after; the diagnostic line carries no URL or token. Run the whole suite (about 220 tests, `portrait` is slow) before committing. Then an owner test on the phone: cast
a Drive episode of 12+ Mbit/s for 10 minutes on the same Wi-Fi with the TV on Wi-Fi and on Ethernet; the log must show cushion above 10 s throughout, no
`-16830`, and send times per segment well under the segment length.

## 6. Native change process (only for B and E)

Follow `docs/AIRPLAY.md` and the r71/r72 commits: edit `migration/airplay-ios/remux`, run the host tests (`airplay-remux.yml`, `scripts/test_*airplay*`), push so the
PR run builds the iPhone candidate, run the inspect-only dispatch (edit the run id and `head_sha` in the inspect step first), pin `migration/airplay-ios/source-lock.json`
(`kodi-airplay-r73`, sha256, `verified_run`), publish with `airplay-ios.yml` (`publish_verified_candidate`), verify the release digest, then build the IPA. Never publish or
build without the owner's request in the current message.

## 7. Risks and open questions

Disk: a Drive staging window needs free space (the proxy already checks 5 GB free); say so when it declines. Heat and battery: filling at full speed while casting; keep Wi-Fi-only.
iOS may suspend the app: the log has a 53-minute silent gap before the cast, so the app was suspended earlier; confirm "stays awake for AirPlay" holds. The TV model, its
network (Wi-Fi band or cable) and the router are unknown: ask the owner. Whether A alone fixes it is unproven; the diagnostic in step 5 decides.
