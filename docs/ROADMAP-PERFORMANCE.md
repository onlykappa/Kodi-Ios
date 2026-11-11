# Performance and quality roadmap (after PR #16)

Owner request (2026-11-11): "a full roadmap with all listed features and bugs that need to be addressed in a major
roadmap of upgrading performance, then we can dial it down". This lists everything open after build 229 and the
PR #16 merge, grouped into phases. Nothing here is started unless it says so. Scores are the audit of 2026-11-11.
Each item names its evidence (ISSUE number or log) and the measurement that proves it done on the phone.

## Where things stand (audit, out of 10)

| Area | Score | Main gap |
|---|---|---|
| Streaming (Umbrella on the phone) | 7 | Opening a debrid MKV takes ~20 s in Kodi itself |
| Downloads to Google Drive | 5 | Uploads ~0.3 MB/s on a 115 Mbps line (ISSUE-167 change pending device test) |
| AirPlay | 4 | Slow start (ISSUE-166 change pending); 10-bit H.264 converts slower than real time |
| Show and season pages | 6 | All Links page (board 4) not built; Phony empty page (ISSUE-155) |
| Pickers | 7 | Approved sheet built and rig-checked; device check pending |
| Continue Watching / resume | 6 | Resume card fixed (ISSUE-166); downloaded resume history (ISSUE-151) needs device check |
| Settings | 7 | Add-on settings tabs (board 08); "- " prefix needs a Kodi patch |
| Search | 7 | Bold matches unconfirmed on the phone |
| Subtitles / audio | 6 | "Download and apply" untested against the real site (ISSUE-156); blank AirPlay captions (ISSUE-147) |
| Follow new episodes | 5 | Never seen working on the phone (ISSUE-150) |
| Notifications / activity | 7 | — |
| Diagnostics | 8 | — |

## Phase 0 — Prove what is already built (device, no new code)

Each needs the owner's phone and a log. Nothing in later phases should assume these work.

| # | Check | Pass when |
|---|---|---|
| 0.1 | AirPlay starts at the resume point (EXT-X-START, ISSUE-166) | Log shows the TV's first video request is the resume segment, not seg0; picture in < 30 s |
| 0.2 | Uploads through system networking (ISSUE-167) | Log says "uploads use system networking"; pieces > 2 MB/s on Wi-Fi |
| 0.3 | Approved picker sheets on the phone | Watch / quality / season sheets look like boards 13-15, taps work |
| 0.4 | Show page: pinned seasons, text, buttons | No "...", season row stays when scrolled, tap on a pinned chip switches season |
| 0.5 | iPhone keyboard everywhere (Kodi r30, ISSUE-162) | No Arctic Fuse keyboard anywhere, including with a paired keyboard |
| 0.6 | Follow new episodes (ISSUE-150) | A followed show's new episode queues on app opening |
| 0.7 | Subtitles "Download and apply" (ISSUE-156) | A Podnapisi subtitle downloads and shows |
| 0.8 | Resume prompt shows no spotlight card (ISSUE-166) | Tapping a Continue Watching item asks to resume that item only |

## Phase 1 — Performance (the main upgrade)

### 1A. Transfers: take Python out of the data path
Evidence: ISSUE-167 (shared ~0.3 MB/s limit, one or two lanes, 5G or Wi-Fi); "Faster start" reading Drive at 3.7 MB/s.

| # | Work | Target |
|---|---|---|
| 1A.1 | Confirm 0.2. If uploads are still slow with system networking, measure interpreter wait (a latency probe thread) and Drive response times to find the real limit | Cause proven in a log |
| 1A.2 | Drive and AllDebrid reads (DriveStream, remote_media cache) through system networking too, not Python sockets | Preparation reads > 20 MB/s on Wi-Fi |
| 1A.3 | Stream AllDebrid → Drive without passing bytes through Python at all (native copy loop: read range, PUT piece) | Copy limited by the line, not the app |
| 1A.4 | More upload lanes once the bottleneck is gone (2 → 3-4), movies included (parallel resumable sessions per file are not possible; lanes are per file) | Season copies at line speed |
| 1A.5 | Fewer always-on Python threads (polling loops at 0.1-1 s across the service) | Idle CPU near zero; interpreter waits < 10 ms |

### 1B. AirPlay
Evidence: ISSUE-163/165/166 logs; segments 117-119 converted in 7-10 s for 6 s of video.

| # | Work | Target |
|---|---|---|
| 1B.1 | For a TV, prefer versions that need no conversion (8-bit H.264 / HEVC Main / Main10) in the picker, marked "Plays on TV as is" | Most streams start with no conversion |
| 1B.2 | 10-bit H.264 conversion faster than real time: decode with more threads, convert two segments in parallel, scale on the GPU instead of libswscale | ≤ 70% of real time per segment |
| 1B.3 | Pause Kodi's own read-ahead while AirPlay starts (it competes for the same link) without closing the paused video | No second reader during startup |
| 1B.4 | Start the TV earlier: hand the playlist over once the first video segment is ready, prime audio in parallel (already), skip the phone-side preflight load | TV picture < 20 s on a debrid link |
| 1B.5 | Blank AirPlay captions (ISSUE-147) | Burned-in or WebVTT captions show on the TV |
| 1B.6 | Hour-long AirPlay stop (ISSUE-147): capture a continuous session log, then fix | One hour without a stop |

### 1C. Opening and playback on the phone
| # | Work | Target |
|---|---|---|
| 1C.1 | Kodi takes ~20-24 s to open a debrid MKV (log 5331b718 and ISSUE-145): measure where (Umbrella resolve, Kodi demux reading fonts/attachments, cache fill) | Breakdown in a log |
| 1C.2 | Act on 1C.1 (e.g. start playback before attachments are read; smaller initial cache fill) | Picture < 8 s |
| 1C.3 | Seek release on slow links (ISSUE-147: 500 ms synchronous seek wait on the GUI thread) | Seek lands where released, UI never freezes |
| 1C.4 | Home and hub load time (listing cache already); measure cold start to Home | Home usable < 3 s after launch |

## Phase 2 — Bugs and missing screens

| # | Item | Evidence |
|---|---|---|
| 2.1 | All Links page (board 4): release type, 4K / HDR10 / HEVC / AV1 tags, size and seeds, sort menu | Approved mockup round 3 |
| 2.2 | Shows downloaded episode by episode look wrong in the Library (owner, build 229 screenshot: "1. phony", "2. Phony", the show poster as every thumbnail, no plots); season packs look right. Episode rows take names/stills/plots from cached TMDb season data only (ios_library.episode_rows cached_only=True); library_watch.hydrate_artwork should fill it while the page is visible but evidently does not for these. Find why (show identity / tmdb id key, season numbers of single-episode entries, folder layout of single downloads), fix, and also handle a folder with no finished episode (old ISSUE-155) | Owner screenshot 2026-11-11; ISSUE-155 |
| 2.3 | Add-on settings sheet with segmented tabs | Mockup board 08 |
| 2.4 | "- " prefix on sub-settings (Kodi core string 168; needs a Kodi patch) | ISSUE-160 |
| 2.5 | Kodi's own PIN/time number pads (not changed by the keyboard patch) | ISSUE-162 |
| 2.6 | Remaining More-menu / power-menu links that open old native windows | ISSUE-160 |
| 2.7 | Bold search matches verified on the phone (Inter bold face) | ISSUE-160 |

## Phase 3 — Reliability

| # | Item | Evidence |
|---|---|---|
| 3.1 | Background survival: iOS interrupts the silent-audio keep-alive ("audio interrupted by iOS"); work resumes only when allowed | Logs 9e2568a7, 5331b718 |
| 3.2 | Transfers recover after network changes (Wi-Fi ↔ 5G) without long retry waits | ISSUE-167 logs |
| 3.3 | Expired debrid links renewed transparently mid-copy and mid-AirPlay | ISSUE-146 |
| 3.4 | One end-to-end smoke list run on the rig before every IPA (pickers, show page, settings, resume prompt) | This session |

## Suggested order

1. Phase 0 on build 230 (one test session, one log).
2. 1A.1 → 1A.2 → 1A.3 (transfers are the biggest gap and unblock AirPlay reads).
3. 1B.1 (cheap, big win) → 1B.3 → 1B.2.
4. 1C.1 measurement, then decide.
5. Phase 2 items as UI rounds with mockups where new screens are needed.
6. Phase 3 alongside.

## Rules that stay

- Device behaviour needs the owner's phone and log; the rig and CI never prove phone results.
- No merge, release or IPA without the owner's request in the conversation.
- UI work follows docs/design/APPLE-UI-POLICY.md and is checked in the rig before it is called done.
