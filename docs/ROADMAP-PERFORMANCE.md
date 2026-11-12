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

Build 229 predates #16's last fixes. Build 232 (run 43066517004, `main` after the #16 merge) has the approved picker
sheets, the show page fixes, the native keyboard (Kodi r30) and the new settings pages. It still uses AirPlay r46, so
the resume-point AirPlay start and uploads through system networking need AirPlay r47 (0.0). #19's fixes are not in it.

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
| Downloads to Google Drive | 5 | ~0.3 MB/s uploads (ISSUE-167; system networking needs AirPlay r47, not in build 232) |
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
| 0.0 | Next build after 232 from `main` + #19: pin AirPlay r47 (resume-point start, LAN retry, system networking for uploads), build and verify the IPA | IPA verified; owner installs |
| 0.0a | Owner tests build 232 (pickers, show page, keyboard, settings, resume prompt) with a log | log and screenshots |
| 0.1 | AirPlay starts at the resume point (ISSUE-166) | TV's first video request is the resume segment; picture < 30 s |
| 0.2 | Uploads through system networking (ISSUE-167) | log "uploads use system networking"; pieces > 2 MB/s on Wi-Fi; "interpreter wait" lines (1A.1) |
| 0.3 | Approved picker sheets replace Kodi's select box for Watch / quality / season | screenshots like boards 13-15; taps pick the row |
| 0.4 | Show page: pinned seasons, text fits, buttons | no "...", season row stays when scrolled |
| 0.5 | iPhone keyboard everywhere (Kodi r30) | no Arctic Fuse keyboard |
| 0.6 | Single-episode downloads show real episode names and stills (2.2, in #19) | Phony page shows "Pilot", stills, plots |
| 0.7 | Follow new episodes (ISSUE-150) | a followed show's new episode queues |
| 0.8 | Resume prompt shows only the tapped item (ISSUE-166) | no spotlight card |

## Build 232 findings (owner log `eabc204b` and screenshots, 09:57-10:00)

| # | Finding | Evidence and cause | Fix |
|---|---|---|---|
| B.1 | **Uploads and AllDebrid copies never start in build 232** | `Thread-16 (drive_uploads)` UnboundLocalError at 09:57:06; the Maze Runner download queued at 09:58:05 and never copied (ISSUE-168) | **fixed in #19**; needs the next build |
| B.2 | Volume boost opens Kodi's own volume slider at the top, which disappears; the boost row shows no value | taps on control 9404 open `DialogSlider.xml` (09:59:04-09:59:13); screenshot 1 | change the gain in the menu itself (VolAmpUp/VolAmpDown, value shown in the row, 0-12 dB); no Kodi slider |
| B.3 | Info in the video controls shows nothing useful | 7141 opens `Custom_1193_VideoOSDInfo.xml`; the item had no metadata (B.4) | fill the info from the episode, and restyle Info (U.6) |
| B.4 | Episodes played from Library › downloaded show have no metadata: the title is the file name (`phony.s01e01.1080p.web.h264-cakes[EZTVx.to].mp4`) | screenshots 1-2; `library_play` passes the Drive file without show, season, episode or plot | `library_play` sets the ListItem's tvshowtitle, season, episode, title, plot and art from the TMDb details already cached for the page |
| B.5 | Subtitles › Find online searches the file name with no season or episode | 09:58:43 `search en 'phony.s01e01…mp4' 0 SNoneENone`; the site is also unreachable (2.13) | B.4 gives the right title; parse the file name as a fallback; 2.13 for the provider |
| B.6 | Subtitles › More (Choose another, Add from a file, Use for all videos) opens Kodi's select box over the menu | 9501 → `DialogSelect.xml` 09:58:51; screenshot 3 | rows inside the track menu (approved #17 design) |
| B.7 | Playback speed still opens Kodi's select box | 7121 → `DialogSelect.xml` 09:59:18; screenshot 4 (= 2.12) | track-menu style |
| B.8 | "EXCEPTION: Window id does not exist" when the subtitle menu closes | 09:58:45.673 | close by the window the menu owns |
| B.9 | After a version is picked, Kodi's select box asks the next question | `DeckSourceSelect.xml` → `DialogSelect.xml` 09:58:04 | the approved sheet |
| B.10 | Elementum's link search held the Download flow for 20.4 s (`/forcelinks` 302 after 20.407 s), of which ~6 s was provider search and the rest the owner choosing | 09:57:43-09:58:04 | show search progress in the sheet; drop providers that return nothing (1337x, BT4G, Torrentio returned 0 every time in the logs) |
| B.11 | Download queue diagnostics say `"build":"unknown"` | 09:58:05 download_queue line | stamp the build in the Elementum-side writer |

## UI — Arctic Fuse and Kodi windows still on screen (owner: "we need mocks of the pages that are Arctic Fuse")

Counted from every owner log (how often each window opened). Already redesigned and not listed: Home, hubs, Library
lists, video controls, notifications banner, volume banner, settings home and the `IOS*` pages. Each item needs a
mockup board first (APPLE-UI-POLICY §7), then the skin change, then a rig check.

| # | Window | Where the owner meets it | Notes |
|---|---|---|---|
| U.1 | `DialogSelect.xml` (20 opens) | Playback speed, Subtitles › More, the question after a version, resume from Library, any add-on list | one sheet style for every list choice; most callers can use choice_sheet |
| U.2 | `DialogConfirm.xml` (20) | yes/no and OK messages (Download not available, errors) | iOS alert style |
| U.3 | `DialogBusy.xml` (98) and `Custom_1156_Buffering.xml` (14) | every open and wait; the ring over the spotlight | opening card with stage and Cancel (2.18) |
| U.4 | `DialogExtendedProgressBar.xml` (50) | TMDb Helper's "Constructing players…" and add-on progress | thin progress in the activity pill, or hidden |
| U.5 | `DialogContextMenu.xml` (11) | long press on rows and Continue Watching | iOS context menu (2.19) |
| U.6 | `Custom_1193_VideoOSDInfo.xml` | Info in the video controls | episode card: still, title, S·E, plot, runtime, ends at |
| U.7 | `DeckSourceSelect.xml` (10) | the version list after Download | All Links page (board 4, item 2.1) |
| U.8 | `DialogSlider.xml` | Volume boost | removed by B.2 |
| U.9 | `source_progress.xml` (4) | Umbrella's source scraping progress | progress sheet matching U.3 |
| U.10 | `Custom_1170_Dialog_Options.xml` (3) | Fuse options dialog | sheet |
| U.11 | `DialogSubtitles.xml` | Kodi's subtitle search window | replaced by the track menu (B.6) |
| U.12 | `Custom_1105_Search.xml` (7) | search results | iOS search results list |
| U.13 | `Startup.xml`, `Custom_1198_Dialog_Startup.xml` | launch | match the launch screen |
| U.14 | `DialogAddonSettings.xml`, `DialogSettings.xml`, `SettingsCategory.xml`, `SkinSettings.xml`, `SettingsSystemInfo.xml`, `DialogAddonInfo.xml`, `AddonBrowser.xml`, `Custom_1118_Dialog_Settings.xml`, `Custom_1160_Dialog_Favourites.xml`, `pin-dialog.xml` | settings, add-ons, favourites, PIN | **owner's agent (#17/#18, 2.3-2.6)**; coordinate before changing |

## Phase 1 — Speed

### 1A. Opening a video from Google Drive (11-13 s → target 3 s)
Evidence: `396d5d67` 09:35:41-09:35:53 and 09:36:29-09:36:43; `e8ab5995` 09:32:23-09:32:29.

| # | Work | Cause | Target |
|---|---|---|---|
| 1A.1 | Serve Drive playback from native code: a range server in KodiAirPlay (it already reads Drive for AirPlay) or a direct Drive URL with the OAuth header that Kodi's curl reads, instead of plugin.googledrive's Python proxy | Known: Kodi reads the movie through `plugin.googledrive`'s local Python proxy; opening takes 4.8-6.2 s and every seek waits on it | stream open < 1 s |
| 1A.2 | One hop instead of two: the watch add-on resolves the Drive file itself (id → URL, token cached) and hands Kodi the final URL, instead of `library_play` → `plugin.googledrive` `play` | Known: 2.2-2.5 s in `library_play`, then 1.0 s in the Drive add-on, before Kodi starts reading | < 0.3 s to OpenFile |
| 1A.3 | Keep the prepared file's fragment index (mfra) with its Drive metadata, so the player starts from it instead of reading the end of the file first | Known: "opening MP4 by its fragment index" costs 0.6-1.9 s on every open | index read 0 s |
| 1A.4 | Warm the first megabytes and the index when a movie or episode page opens (not on every row focus) | Suspected; measure after 1A.1 | first picture < 1 s after OpenFile — **Coded (host-tested) (speed-reliability-fixes): drive_proxy Warm: page open reads first 4 MB + last 1 MB; first requests answered locally; device timing pending** |
| 1A.5 | Seek on Drive copies through the native reader with read-ahead from the new position | Known: seek landed after 4.2 s with buffer and audio timeouts | seek < 1.5 s — **Coded (host-tested) (speed-reliability-fixes): drive_proxy: pre-opened spare Drive connection, 4 MB read-ahead queue, seek first-byte timing; device seek time pending** |

### 1B. Opening streams and unprepared MKVs (6-32 s → target 8 s)
Evidence: older logs `41de3707`, `18b7b4b0`, `9e2568a7` (Demuxer → first stream 24-30 s); ISSUE-145.

| # | Work | Cause | Target |
|---|---|---|---|
| 1B.1 | Apply the MKV skip-attachments patch (already in the AirPlay FFmpeg) to Kodi's own FFmpeg in the Kodi build | Known: Kodi's demuxer reads every attachment (fonts, covers) over the network before playing | MKV first stream < 5 s |
| 1B.2 | Network-aware probe limits: smaller `probesize`/`analyzeduration` for http/plugin sources, larger for local files | Suspected; measure with 1C.1 | − 1-3 s per open — **Kodi patch (needs Kodi r31) (speed-reliability-fixes): DVDDemuxFFmpeg: 3 MB / 3 s probe for http(s) sources, 20 MB / 10 s for local files, one retry at FFmpeg's defaults; patch applies to Kodi 21.3, not compiled** |
| 1B.3 | Cache settings for phones: start playback after a small cache fill; read factor tuned for 5G vs Wi-Fi | Suspected (Buffer mode 4, 96 MB, read factor 10) | picture before the cache is full — **Coded (host-tested) (speed-reliability-fixes): cache_tune: read factor 10x on Wi-Fi, 4x on cellular, set as a video opens, owner's own value kept; values are unmeasured defaults** |
| 1B.4 | Debrid links: keep Umbrella's resolve, but start Kodi reading the link while the source window closes | Suspected | − 1 s — **Coded (host-tested) (speed-reliability-fixes): link_warm: the resolved debrid link's first 512 KB and last 256 KB are read in the background as Umbrella's unlock returns; saving unmeasured** |

### 1C. Taps that wait for TMDb Helper (1-2 s each)
Evidence: `e8ab5995` 09:31:25 (1.4 s), 09:32:23 (1.9 s), 09:32:45 (2.1 s).

| # | Work | Cause | Target |
|---|---|---|---|
| 1C.1 | One timing line per play: tap → plugin → resolve → OpenFile → stream open → first picture, in the diagnostics log | We infer stages from gaps today | every open has a breakdown — **Coded (host-tested) (speed-reliability-fixes): open timing line now breaks the time into resolve / handoff / open / picture; needs a device log to read** |
| 1C.2 | Check for a completed copy before TMDb Helper builds its player list; play it straight away | Known: TMDb Helper constructs players, reads item details and the library (1-2 s), then our hook finds the Drive copy | Drive copy plays < 0.3 s after the tap's plugin call |
| 1C.3 | Ship TMDb Helper's `resources/players/` folder (or point it at ours), so it stops failing two directory reads per play | Known: `GetDirectory - Error getting …/resources/players/` twice on every play | no errors |
| 1C.4 | Cache TMDb item details for the titles on screen (spotlight, Continue Watching) so Play needs no network | Suspected | Play menu < 0.4 s — **Coded (host-tested; needs the next IPA) (speed-reliability-fixes): details_warm: after each listing-cache refresh the hero titles and Continue Watching have TMDb Helper's details fetched in the background (info=ios_warm); effect on Play unmeasured** |

### 1D. Home rows and navigation
Evidence: 31 row requests per launch in every log since build 184; 64 in a 2-minute session; 31 after one tap on the
Home tab (`396d5d67` 09:36:48); 11-17 while a video opened or closed (`e8ab5995` 09:32:26, 09:32:45).

| # | Work | Cause | Target |
|---|---|---|---|
| 1D.1 | Stop Home rows reloading on tab return: Kodi re-requests a plugin row whenever Home becomes visible again; give rows a stable path and refresh only when the listing cache says the content changed | Known: each request starts a Python interpreter (the cache answers in 3-30 ms, but the interpreter start costs far more) | 0 requests on tab return when nothing changed — **Verified by code reading + pinned (tab return); playback part native staged (Kodi r31); device check pending (speed-reliability-fixes): Kodi 21.3 source: returning to Home does not refetch rows unless a row's address changes; a test now pins that no row address reads window-dependent info** |
| 1D.2 | No row refresh while a video opens or closes; refresh Continue Watching once after playback stops | Known: rows reload behind the player at its busiest moment | 0 requests during OpenFile |
| 1D.3 | Load only the rows the visible tab shows; Movies and TV hubs load when opened | Known: hero.1101/hero.1102 (other tabs) load at start-up | start-up row requests 31 → ~10 |
| 1D.4 | Spotlight: show the loading ring only when the hero has no items (owner screenshot shows it over a loaded hero) | Owner screenshot 2 | no ring over content — **Already done in 4fc1157 (hero placeholder only while empty); now pinned by tests; device check pending (speed-reliability-fixes): portrait.hero draws loading feedback only while Container(4000) has no items; test_portrait.HeroLoadingFeedback pins it** |

### 1E. Start-up and background work (5.4-9.5 s → target 3 s)
Evidence: `e8ab5995` and `396d5d67` start-up; 37 logs.

| # | Work | Cause | Target |
|---|---|---|---|
| 1E.1 | Start Elementum's daemon only when Download is chosen (or a torrent is active), not at every launch | Known: daemon, libtorrent listener and ~300 log lines every launch | no Elementum at launch |
| 1E.2 | Remove unused binary add-ons from the IPA: 20+ PVR clients, ~22 audio decoders, game add-ons | Known: 205 add-ons scanned at launch; app size | − scan time and IPA size |
| 1E.3 | Trim services: Umbrella's update check, cocoscrapers' undesirables check, embuary's player monitor, Google Drive's export/download/player services and source port | Known: all start at launch | services that do work only on demand — **Partly done: Embuary Helper service off; audit recorded; Umbrella/cocoscrapers not patchable here (speed-reliability-fixes): bootstrap housekeeping switches off script.embuary.helper's service (fanart grabber, widget timer, player monitor); other services audited and kept; Umbrella/cocoscrapers need their source** |
| 1E.4 | Bootstrap imports 1.74 s: import page builders lazily | Known: "bootstrap entered (imports 1.743s)" | < 0.4 s |
| 1E.5 | TMDb Helper's Trakt check (1.66 s) after Home settles, not at launch | Known | deferred |
| 1E.6 | Script windows close without "waiting on thread": daemon worker threads end with the window | Known: each Settings/Notifications/Play on TV close waits on a thread | instant close |
| 1E.7 | Fewer always-on Python polling loops (0.1-1 s across the service) | Known (code) | idle CPU near zero |

### 1F. Transfers (uploads ~0.3 MB/s on a 115 Mbps line)
Evidence: ISSUE-167.

| # | Work | Target |
|---|---|---|
| 1F.1 | Read the "interpreter wait" lines (probe in #19) and the system-networking upload speed from the r47 build | cause proven |
| 1F.2 | Drive and AllDebrid reads through system networking too (DriveStream, remote_media) | preparation reads > 20 MB/s |
| 1F.3 | AllDebrid → Drive copy loop in native code (read range, PUT piece), no bytes through Python | line speed |
| 1F.4 | More upload lanes once the bottleneck is gone (2 → 3-4) | season copies at line speed |

### 1G. AirPlay
Evidence: ISSUE-163/165/166.

| # | Work | Target |
|---|---|---|
| 1G.1 | 10-bit H.264 marked in the picker ("10-BIT · SLOW ON AIRPLAY", done in #19) | most streams need no conversion |
| 1G.2 | 10-bit conversion faster than real time (threads, two segments in parallel, GPU scaling) | ≤ 70 % of real time — **Measurement tool added; no speed change made blind; needs the owner's device log (speed-reliability-fixes): scripts/conversion_log.py reads the 'compat: segment N converted in MS ms (P% of realtime) via ROUTE' lines and says whether the 70 % target holds; levers listed below** |
| 1G.3 | Pause Kodi's read-ahead while AirPlay starts | one reader during start — **Coded for Drive copies (host-tested); debrid streams not covered; device check pending (speed-reliability-fixes): Play on TV marks KodiIOS.AirPlay.Starting; the Drive proxy holds Kodi's own requests (not the AirPlay reader's) while it is fresh; debrid links Kodi reads directly are not controlled** |
| 1G.4 | Hand the TV the playlist as soon as the first video segment is ready | TV picture < 20 s on a debrid link |
| 1G.5 | Blank AirPlay captions (ISSUE-147) | captions show on the TV — **Partly done: caption path mapped and a log reader added; cause still needs the owner's device log (speed-reliability-fixes): scripts/caption_log.py turns a kodi.log into one verdict on how captions reached the TV (off / burned in / WebVTT served / never read); the cause of the blank captions is unconfirmed** |
| 1G.6 | Hour-long AirPlay stop (ISSUE-147) | one hour without a stop — **Partly done: stop evidence reader added; no hour-long log exists, cause not established, nothing to fix yet (speed-reliability-fixes): scripts/stop_log.py rebuilds the session timeline from the service's diagnostic lines and attributes a stop (expired token/link near 3600 s, failing reads, phone suspended, receiver)** |
| 1G.7 | 10-bit H.264 ranked last in the picker (no hardware decoder on Apple devices) — **done** | streams pick versions that play as they are |
| 1G.8 | Play on TV on a download whose preparation has not finished: offer "Prepare first (about N min)" next to "Play now", move it to the front of the preparation queue, and play it as it is once ready (owner: "if the file is already good then no conversion is needed") | no live conversion of downloads |

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
| 2.11 | Taps on Kodi's select box can return "nothing picked" | `e8ab5995` 09:31:36: tap on the Download/Stream box returned -1 while Kodi ignored actions during the closing animation | replaced by the sheet in build 232 (0.3); confirm |
| 2.12 | Playback speed still uses Kodi's select box | owner screenshot 3 | the track-menu style (same as Subtitles/Audio) |
| 2.13 | Subtitles › Find online always fails | both logs: podnapisi.net does not resolve (`Errno 8`) | second provider (OpenSubtitles.com API or SubDL), requests through system networking, a clear message when every provider is unreachable (ISSUE-156) |
| 2.14 | Track menu opens with an unfocusable control | "Control 9310 in window 13000 has been asked to focus, but it can't" on every open | focus the first row |
| 2.15 | Skin expression errors on the Settings section page | "Error parsing boolean expression $exp[exp_tmdbhelper_isdata]" / isblur in IOSSection | define or remove the expressions |
| 2.16 | Library list focus errors | "Control 53 in window 10025 … can't" on each Library open/close | valid default focus |
| 2.17 | Phony / single-episode show with no finished episode (old ISSUE-155) | ISSUE-155 | empty state on the show page |
| 2.18 | No feedback or cancel while a video opens | `396d5d67` 09:36:37: the owner tapped the busy ring 4 s into a 13 s open and nothing happened | an opening card that says the stage (finding the copy, connecting, reading) with Cancel; goes away when 1A makes opens fast |
| 2.19 | Long-pressing Continue Watching opens Kodi's context menu, then Play needs a second tap | `e8ab5995` 09:32:09-09:32:23 | one tap plays; long press shows the iOS-style menu |

## Phase 3 — Reliability and measurement

| # | Item | Evidence |
|---|---|---|
| 3.1 | Background survival: iOS interrupts the silent-audio keep-alive | logs 9e2568a7, 5331b718 — **Coded (host-tested); iOS suspension itself is OS-managed; needs the owner's device log (speed-reliability-fixes): background.watch: re-asks each tick, times recovery, and after 3 minutes of lost background audio with work waiting adds one Notifications entry; native restart logic unchanged** |
| 3.2 | Transfers recover after Wi-Fi ↔ 5G changes without long waits | ISSUE-167 |
| 3.3 | Expired debrid links renewed mid-copy and mid-AirPlay | ISSUE-146 |
| 3.4 | Rig smoke list before every IPA (pickers, show page, settings, resume prompt, track menus) | this session |
| 3.5 | Performance budget in diagnostics: tap-to-picture (1C.1), start-up stages, row requests per minute, seek-to-land; one summary line a minute | this investigation |
| 3.6 | Log hygiene: Elementum config dump, deprecated `addStreamInfo`, duplicate keymap loads on resume | `e8ab5995`, `396d5d67` |

## Suggested order

1. **B.1 is fixed in #19: build 232 cannot upload or copy.** Ship the next build first (r47 + #19). **0.0a** test build 232 for UI only; **0.0** the r47 build with #19, then one Phase 0 test session with a log (0.1-0.8).
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

## PR #19 review repairs (2026-11-12)

- 1A.1 reliability: ISSUE-171 rejected-token renewal repaired and host tested; device check pending.
- This checkpoint authorizes source fixes and separate commits, not native releases or an IPA. r31/r47 delivery
  remains a separate verified-build step; do not change pins to unbuilt artifacts.

- 1A.1 reliability: ISSUE-172 bounded size probes repaired and host tested; no full movie read during HEAD.

- Season reliability: ISSUE-173 bounded source discovery and active cancellation repaired; live provider check pending.

- 1G receiver readiness: ISSUE-174 implements the owner's 4K-preserving Media Assistant fallback for a confirmed
  Roku converting HEVC over AirPlay. New native API is capability gated; verified framework delivery/device tests
  remain required. Generic preparation is not proof that every AirPlay receiver accepts the original picture.
