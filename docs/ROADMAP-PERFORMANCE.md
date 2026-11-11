# Performance and quality roadmap (after PR #16)

Owner requests (2026-11-11): "a full roadmap with all listed features and bugs ... upgrading performance", then
"create a more defined and larger roadmap ... there are a lot of bugs and a lot of things making the app inefficient
and just overall slow ... just investigate before we code".

This document is the plan. Each item names its evidence (log id and time, ISSUE number or screenshot), the cause
when it is known, the fix, and the measurement that proves it on the phone. "Known cause" means the log or the code
shows it; "suspected" means it still needs a measurement first. Nothing here is started unless the progress file
(`docs/PERFORMANCE-PROGRESS.md`) says so.

## Evidence used

- Owner logs `e8ab5995` (09:31-09:33, build 229: Home, spotlight Play, Continue Watching, Settings, video controls,
  subtitles, playback speed, Next Episode) and `396d5d67` (09:35-09:37, build 229: Settings, Library, a prepared
  Drive movie opened twice, Play on TV, subtitles, seeks, notifications).
- The 37 earlier owner logs (start-up and opening times across builds 184-229).
- Owner screenshots (build 229): Download/Stream in Kodi's select box, a loading ring over the spotlight, the
  Playback speed list in Kodi's select box.
- Code reading on `main` after #16.

Build 229 predates #16's last fixes. The approved picker sheets, the show page text fixes, the native keyboard and
the resume-point AirPlay start are merged but not yet in an IPA (build 230, Phase 0).

## What the logs measure (build 229 on the iPhone 16 Pro)

| What the owner did | Time | Where it goes |
|---|---|---|
| Launch to Home drawn | 0.5 s (rows from the listing cache, 3-30 ms each) | fine |
| Launch to start-up complete | 5.4-9.5 s across 37 logs | add-on services, 31 Python row calls, Elementum daemon, bootstrap imports 1.74 s |
| Open a prepared movie from Library › Movies (Home Alone, on Drive) | **11.7 s and 13.0 s** tap to picture | watch add-on 2.2-2.5 s → Google Drive add-on 1.0 s → stream open **4.8-6.2 s** → MP4 index read 1.6-1.9 s → picture 1.6 s |
| Open a Drive episode from Continue Watching (Phony S1E1) | 5.8 s | TMDb Helper 1.9 s → hand-off 1 s → stream open 1.4 s → index 0.6 s |
| Open a debrid or unprepared Drive MKV (older logs) | 6-32 s (several 31 s) | Kodi's demuxer reads the MKV over the network for 24-30 s before the first stream |
| Seek on a Drive movie (24.7 %) | landed after **4.2 s**; buffer waits, audio timeouts, "large audio sync error" | same Python proxy as the open |
| Spotlight Play to the Download/Stream menu | 1.4 s | TMDb Helper builds its player list (1 s) |
| Next Episode on a downloaded show | menu flashed for 0.12 s, then "lib.player - Failure!" | bug (2.10, 2.11) |
| Tap the Home tab | 31 row requests (one Python run each) | rows reload on every return |
| Video starts or stops | 11-17 Home row requests while the video opens | rows refresh behind the player |
| Settings pages, Library pages, Notifications | 0.03-0.2 s | fine |
| Close a video | 0.6-1.0 s | fine |
| Subtitles › Find online | fails at once: `Errno 8 nodename nor servname` | podnapisi.net does not resolve on the owner's phone |

Per 2-minute session the phone ran 64 Home row requests, ~300 lines of Elementum start-up output, and a
"waiting on thread" stall each time a script page closed.

## Where things stand (audit, out of 10)

| Area | Score | Main gap |
|---|---|---|
| Opening a video | 4 | 6-13 s for Drive copies, up to 32 s for MKV streams |
| Seeking | 5 | 4 s to land on Drive copies |
| Home and navigation | 6 | rows reload on every tab return and around playback |
| Start-up | 6 | 5-9 s of background work after Home appears |
| Downloads to Google Drive | 5 | ~0.3 MB/s uploads (ISSUE-167; native networking in build 230 pending a device test) |
| AirPlay | 4 | slow start; 10-bit H.264 converts slower than real time |
| Source and player choice | 5 | Drive copies ignored outside Continue Watching; Next Episode fails |
| Subtitles / audio | 4 | online search unreachable; blank AirPlay captions |
| Show and season pages | 7 | All Links page (board 4) not built |
| Settings | 7 | add-on settings tabs and Kodi leftovers (owner's agent, #17/#18) |
| Notifications / activity | 7 | — |
| Diagnostics | 7 | no single tap-to-picture timing line |

## Phase 0 — Ship and prove what is already built

| # | Work | Pass when |
|---|---|---|
| 0.0 | Build 230 from `main` (+ #19): pin AirPlay r47 (system networking for uploads), build and verify the IPA | IPA verified; owner installs |
| 0.1 | AirPlay starts at the resume point (ISSUE-166) | TV's first video request is the resume segment; picture < 30 s |
| 0.2 | Uploads through system networking (ISSUE-167) | log "uploads use system networking"; pieces > 2 MB/s on Wi-Fi; "interpreter wait" lines (1A.1) |
| 0.3 | Approved picker sheets replace Kodi's select box for Watch / quality / season | screenshots like boards 13-15; taps pick the row |
| 0.4 | Show page: pinned seasons, text fits, buttons | no "...", season row stays when scrolled |
| 0.5 | iPhone keyboard everywhere (Kodi r30) | no Arctic Fuse keyboard |
| 0.6 | Single-episode downloads show real episode names and stills (2.2, in #19) | Phony page shows "Pilot", stills, plots |
| 0.7 | Follow new episodes (ISSUE-150) | a followed show's new episode queues |
| 0.8 | Resume prompt shows only the tapped item (ISSUE-166) | no spotlight card |

## Phase 1 — Speed

### 1A. Opening a video from Google Drive (11-13 s → target 3 s)
Evidence: `396d5d67` 09:35:41-09:35:53 and 09:36:29-09:36:43; `e8ab5995` 09:32:23-09:32:29.

| # | Work | Cause | Target |
|---|---|---|---|
| 1A.1 | Serve Drive playback from native code: a range server in KodiAirPlay (it already reads Drive for AirPlay) or a direct Drive URL with the OAuth header that Kodi's curl reads, instead of plugin.googledrive's Python proxy | Known: Kodi reads the movie through `plugin.googledrive`'s local Python proxy; opening takes 4.8-6.2 s and every seek waits on it | stream open < 1 s |
| 1A.2 | One hop instead of two: the watch add-on resolves the Drive file itself (id → URL, token cached) and hands Kodi the final URL, instead of `library_play` → `plugin.googledrive` `play` | Known: 2.2-2.5 s in `library_play`, then 1.0 s in the Drive add-on, before Kodi starts reading | < 0.3 s to OpenFile |
| 1A.3 | Keep the prepared file's fragment index (mfra) with its Drive metadata, so the player starts from it instead of reading the end of the file first | Known: "opening MP4 by its fragment index" costs 0.6-1.9 s on every open | index read 0 s |
| 1A.4 | Warm the first megabytes and the index when a movie or episode page opens (not on every row focus) | Suspected; measure after 1A.1 | first picture < 1 s after OpenFile |
| 1A.5 | Seek on Drive copies through the native reader with read-ahead from the new position | Known: seek landed after 4.2 s with buffer and audio timeouts | seek < 1.5 s |

### 1B. Opening streams and unprepared MKVs (6-32 s → target 8 s)
Evidence: older logs `41de3707`, `18b7b4b0`, `9e2568a7` (Demuxer → first stream 24-30 s); ISSUE-145.

| # | Work | Cause | Target |
|---|---|---|---|
| 1B.1 | Apply the MKV skip-attachments patch (already in the AirPlay FFmpeg) to Kodi's own FFmpeg in the Kodi build | Known: Kodi's demuxer reads every attachment (fonts, covers) over the network before playing | MKV first stream < 5 s |
| 1B.2 | Network-aware probe limits: smaller `probesize`/`analyzeduration` for http/plugin sources, larger for local files | Suspected; measure with 1C.1 | − 1-3 s per open |
| 1B.3 | Cache settings for phones: start playback after a small cache fill; read factor tuned for 5G vs Wi-Fi | Suspected (Buffer mode 4, 96 MB, read factor 10) | picture before the cache is full |
| 1B.4 | Debrid links: keep Umbrella's resolve, but start Kodi reading the link while the source window closes | Suspected | − 1 s |

### 1C. Taps that wait for TMDb Helper (1-2 s each)
Evidence: `e8ab5995` 09:31:25 (1.4 s), 09:32:23 (1.9 s), 09:32:45 (2.1 s).

| # | Work | Cause | Target |
|---|---|---|---|
| 1C.1 | One timing line per play: tap → plugin → resolve → OpenFile → stream open → first picture, in the diagnostics log | We infer stages from gaps today | every open has a breakdown |
| 1C.2 | Check for a completed copy before TMDb Helper builds its player list; play it straight away | Known: TMDb Helper constructs players, reads item details and the library (1-2 s), then our hook finds the Drive copy | Drive copy plays < 0.3 s after the tap's plugin call |
| 1C.3 | Ship TMDb Helper's `resources/players/` folder (or point it at ours), so it stops failing two directory reads per play | Known: `GetDirectory - Error getting …/resources/players/` twice on every play | no errors |
| 1C.4 | Cache TMDb item details for the titles on screen (spotlight, Continue Watching) so Play needs no network | Suspected | Play menu < 0.4 s |

### 1D. Home rows and navigation
Evidence: 31 row requests per launch in every log since build 184; 64 in a 2-minute session; 31 after one tap on the
Home tab (`396d5d67` 09:36:48); 11-17 while a video opened or closed (`e8ab5995` 09:32:26, 09:32:45).

| # | Work | Cause | Target |
|---|---|---|---|
| 1D.1 | Stop Home rows reloading on tab return: Kodi re-requests a plugin row whenever Home becomes visible again; give rows a stable path and refresh only when the listing cache says the content changed | Known: each request starts a Python interpreter (the cache answers in 3-30 ms, but the interpreter start costs far more) | 0 requests on tab return when nothing changed |
| 1D.2 | No row refresh while a video opens or closes; refresh Continue Watching once after playback stops | Known: rows reload behind the player at its busiest moment | 0 requests during OpenFile |
| 1D.3 | Load only the rows the visible tab shows; Movies and TV hubs load when opened | Known: hero.1101/hero.1102 (other tabs) load at start-up | start-up row requests 31 → ~10 |
| 1D.4 | Spotlight: show the loading ring only when the hero has no items (owner screenshot shows it over a loaded hero) | Owner screenshot 2 | no ring over content |

### 1E. Start-up and background work (5.4-9.5 s → target 3 s)
Evidence: `e8ab5995` and `396d5d67` start-up; 37 logs.

| # | Work | Cause | Target |
|---|---|---|---|
| 1E.1 | Start Elementum's daemon only when Download is chosen (or a torrent is active), not at every launch | Known: daemon, libtorrent listener and ~300 log lines every launch | no Elementum at launch |
| 1E.2 | Remove unused binary add-ons from the IPA: 20+ PVR clients, ~22 audio decoders, game add-ons | Known: 205 add-ons scanned at launch; app size | − scan time and IPA size |
| 1E.3 | Trim services: Umbrella's update check, cocoscrapers' undesirables check, embuary's player monitor, Google Drive's export/download/player services and source port | Known: all start at launch | services that do work only on demand |
| 1E.4 | Bootstrap imports 1.74 s: import page builders lazily | Known: "bootstrap entered (imports 1.743s)" | < 0.4 s |
| 1E.5 | TMDb Helper's Trakt check (1.66 s) after Home settles, not at launch | Known | deferred |
| 1E.6 | Script windows close without "waiting on thread": daemon worker threads end with the window | Known: each Settings/Notifications/Play on TV close waits on a thread | instant close |
| 1E.7 | Fewer always-on Python polling loops (0.1-1 s across the service) | Known (code) | idle CPU near zero |

### 1F. Transfers (uploads ~0.3 MB/s on a 115 Mbps line)
Evidence: ISSUE-167.

| # | Work | Target |
|---|---|---|
| 1F.1 | Read the "interpreter wait" lines (1A.1 probe, in #19) and the system-networking upload speed from build 230 | cause proven |
| 1F.2 | Drive and AllDebrid reads through system networking too (DriveStream, remote_media) | preparation reads > 20 MB/s |
| 1F.3 | AllDebrid → Drive copy loop in native code (read range, PUT piece), no bytes through Python | line speed |
| 1F.4 | More upload lanes once the bottleneck is gone (2 → 3-4) | season copies at line speed |

### 1G. AirPlay
Evidence: ISSUE-163/165/166.

| # | Work | Target |
|---|---|---|
| 1G.1 | 10-bit H.264 marked in the picker ("10-BIT · SLOW ON AIRPLAY", done in #19) | most streams need no conversion |
| 1G.2 | 10-bit conversion faster than real time (threads, two segments in parallel, GPU scaling) | ≤ 70 % of real time |
| 1G.3 | Pause Kodi's read-ahead while AirPlay starts | one reader during start |
| 1G.4 | Hand the TV the playlist as soon as the first video segment is ready | TV picture < 20 s on a debrid link |
| 1G.5 | Blank AirPlay captions (ISSUE-147) | captions show on the TV |
| 1G.6 | Hour-long AirPlay stop (ISSUE-147) | one hour without a stop |

## Phase 2 — Bugs

| # | Bug | Evidence and cause | Fix |
|---|---|---|---|
| 2.1 | All Links page (board 4) not built | approved mockup | build it |
| 2.2 | Single-episode downloads look wrong in the Library | owner screenshot; folder named from the file, TMDb lookup by that name | **done in #19**; device check 0.6 |
| 2.3-2.6 | Add-on settings tabs, "- " prefix, Kodi number pads, More/power-menu links | #17/#18 follow-ups | **owner's agent** |
| 2.7 | Bold search matches unconfirmed | ISSUE-160 | device check |
| 2.8 | Drive copies are ignored unless playback starts from Continue Watching | Known: `ios_watch_dialog.choose_player` calls `downloaded_item(..., cloud=resume)`; Next Episode, spotlight Play and show pages check only phone copies (`e8ab5995` 09:32:47: Phony S1E2 "completed-copy check: none" although E2 is on Drive) | check Drive copies on every entry point (cached Drive listing, no network wait) |
| 2.9 | Next Episode on a downloaded show fails | `e8ab5995` 09:32:47: menu offered then "picked -1" 0.12 s later, "lib.player - Failure!" — the select box opened while the player was closing and was dismissed | with 2.8 the copy plays directly; otherwise open the sheet after the player has closed |
| 2.10 | Spotlight Play may open a different title than the one shown (suspected) | owner screenshot 1: the menu asks about "Crosby, Stills a…" over The Awakening's artwork; the hero may have rotated as it was tapped | Play reads the focused hero item at tap time, not the rotation's next item; same family as the resume-card bug (ISSUE-166) |
| 2.11 | Taps on Kodi's select box can return "nothing picked" | `e8ab5995` 09:31:36: tap on the Download/Stream box returned -1 while Kodi ignored actions during the closing animation | replaced by the sheet in build 230 (0.3); confirm |
| 2.12 | Playback speed still uses Kodi's select box | owner screenshot 3 | the track-menu style (same as Subtitles/Audio) |
| 2.13 | Subtitles › Find online always fails | both logs: podnapisi.net does not resolve (`Errno 8`) | second provider (OpenSubtitles.com API or SubDL), requests through system networking, a clear message when every provider is unreachable (ISSUE-156) |
| 2.14 | Track menu opens with an unfocusable control | "Control 9310 in window 13000 has been asked to focus, but it can't" on every open | focus the first row |
| 2.15 | Skin expression errors on the Settings section page | "Error parsing boolean expression $exp[exp_tmdbhelper_isdata]" / isblur in IOSSection | define or remove the expressions |
| 2.16 | Library list focus errors | "Control 53 in window 10025 … can't" on each Library open/close | valid default focus |
| 2.17 | Phony / single-episode show with no finished episode (old ISSUE-155) | ISSUE-155 | empty state on the show page |

## Phase 3 — Reliability and measurement

| # | Item | Evidence |
|---|---|---|
| 3.1 | Background survival: iOS interrupts the silent-audio keep-alive | logs 9e2568a7, 5331b718 |
| 3.2 | Transfers recover after Wi-Fi ↔ 5G changes without long waits | ISSUE-167 |
| 3.3 | Expired debrid links renewed mid-copy and mid-AirPlay | ISSUE-146 |
| 3.4 | Rig smoke list before every IPA (pickers, show page, settings, resume prompt, track menus) | this session |
| 3.5 | Performance budget in diagnostics: tap-to-picture (1C.1), start-up stages, row requests per minute, seek-to-land; one summary line a minute | this investigation |
| 3.6 | Log hygiene: Elementum config dump, deprecated `addStreamInfo`, duplicate keymap loads on resume | `e8ab5995`, `396d5d67` |

## Suggested order

1. **0.0** build 230, then one Phase 0 test session with a log (covers 0.1-0.8).
2. **2.8 + 2.9 + 2.10** (Drive copies everywhere, Next Episode, spotlight item): small code, big daily effect.
3. **1D.1-1D.3** (rows): removes most of the background Python work while navigating.
4. **1A.2 → 1A.1 → 1A.3 → 1A.5** (Drive playback without Python): 11-13 s opens → ~3 s, seeks < 1.5 s.
5. **1C.1** timing line, then **1B.1** (Kodi MKV patch, rides on the next Kodi build).
6. **1E** start-up trims; **2.12-2.16** small UI fixes; **1F/1G** with device evidence.
7. Phase 3 alongside.

## Rules that stay

- Device behaviour needs the owner's phone and log; the rig and CI never prove phone results.
- No merge, release or IPA without the owner's request in the conversation.
- UI work follows docs/design/APPLE-UI-POLICY.md and is checked in the rig before it is called done.
- #17/#18 and items 2.3-2.6 belong to the owner's agent; coordinate before changing the Kodi pin.
