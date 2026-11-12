# PR #19 speed and reliability coverage

Updated 2026-11-12. The original screenshot lists 34 speed items. Two later AirPlay additions (1G.7/1G.8) make
**36 speed + 6 reliability/measurement items = 42**. Every current ID is listed below.

This is a live audit, not a claim that all targets passed. **Source** means a coded repair with host checks;
**Native staged** requires a rebuilt/verified/pinned binary. **Device required / Measurement required** cannot
be closed by a Linux rig or source assertion. Current binary pins remain Kodi r30 / AirPlay r46. No IPA requested.

| ID | Item | Coverage | Evidence / next check |
|---|---|---|---|
| 1A.1 | Serve Drive playback from native code: a range server in KodiAirPlay (it already reads Drive for AirPlay) or a direct Drive URL with the OAuth header that Kodi's curl reads, instead of plugin.googledrive's Python proxy | Source | Lean Drive proxy; token/HEAD repairs; device open target pending |
| 1A.2 | One hop instead of two: the watch add-on resolves the Drive file itself (id → URL, token cached) and hands Kodi the final URL, instead of `library_play` → `plugin.googledrive` `play` | Source | drivelibrary.direct_url skips the add-on hop |
| 1A.3 | Keep the prepared file's fragment index (mfra) with its Drive metadata, so the player starts from it instead of reading the end of the file first | Open | Implementation and regression coverage still required |
| 1A.4 | Warm the first megabytes and the index when a movie or episode page opens (not on every row focus) | Coded (host-tested) | drive_proxy Warm: page open reads first 4 MB + last 1 MB; first requests answered locally; device timing pending |
| 1A.5 | Seek on Drive copies through the native reader with read-ahead from the new position | Coded (host-tested) | drive_proxy: pre-opened spare Drive connection, 4 MB read-ahead queue, seek first-byte timing; device seek time pending |
| 1B.1 | Apply the MKV skip-attachments patch (already in the AirPlay FFmpeg) to Kodi's own FFmpeg in the Kodi build | Native staged | Kodi FFmpeg attachment skip; new executable required |
| 1B.2 | Network-aware probe limits: smaller `probesize`/`analyzeduration` for http/plugin sources, larger for local files | Kodi patch (needs Kodi r31) | DVDDemuxFFmpeg: 3 MB / 3 s probe for http(s) sources, 20 MB / 10 s for local files, one retry at FFmpeg's defaults; patch applies to Kodi 21.3, not compiled |
| 1B.3 | Cache settings for phones: start playback after a small cache fill; read factor tuned for 5G vs Wi-Fi | Coded (host-tested) | cache_tune: read factor 10x on Wi-Fi, 4x on cellular, set as a video opens, owner's own value kept; values are unmeasured defaults |
| 1B.4 | Debrid links: keep Umbrella's resolve, but start Kodi reading the link while the source window closes | Coded (host-tested) | link_warm: the resolved debrid link's first 512 KB and last 256 KB are read in the background as Umbrella's unlock returns; saving unmeasured |
| 1C.1 | One timing line per play: tap → plugin → resolve → OpenFile → stream open → first picture, in the diagnostics log | Coded (host-tested) | open timing line now breaks the time into resolve / handoff / open / picture; needs a device log to read |
| 1C.2 | Check for a completed copy before TMDb Helper builds its player list; play it straight away | Source | fast_copy before TMDb player construction |
| 1C.3 | Ship TMDb Helper's `resources/players/` folder (or point it at ours), so it stops failing two directory reads per play | Source | Bundle contains TMDb players directory |
| 1C.4 | Cache TMDb item details for the titles on screen (spotlight, Continue Watching) so Play needs no network | Coded (host-tested; needs the next IPA) | details_warm: after each listing-cache refresh the hero titles and Continue Watching have TMDb Helper's details fetched in the background (info=ios_warm); effect on Play unmeasured |
| 1D.1 | Stop Home rows reloading on tab return: Kodi re-requests a plugin row whenever Home becomes visible again; give rows a stable path and refresh only when the listing cache says the content changed | Verified by code reading + pinned (tab return); playback part native staged (Kodi r31); device check pending | Kodi 21.3 source: returning to Home does not refetch rows unless a row's address changes; a test now pins that no row address reads window-dependent info |
| 1D.2 | No row refresh while a video opens or closes; refresh Continue Watching once after playback stops | Native staged | Plugin-row invalidation guard; new executable required |
| 1D.3 | Load only the rows the visible tab shows; Movies and TV hubs load when opened | Open | Implementation and regression coverage still required |
| 1D.4 | Spotlight: show the loading ring only when the hero has no items (owner screenshot shows it over a loaded hero) | Already done in 4fc1157 (hero placeholder only while empty); now pinned by tests; device check pending | portrait.hero draws loading feedback only while Container(4000) has no items; test_portrait.HeroLoadingFeedback pins it |
| 1E.1 | Start Elementum's daemon only when Download is chosen (or a torrent is active), not at every launch | Source | Elementum demand startup |
| 1E.2 | Remove unused binary add-ons from the IPA: 20+ PVR clients, ~22 audio decoders, game add-ons | Source | 89c2f88 staged add-on pruning; package tests |
| 1E.3 | Trim services: Umbrella's update check, cocoscrapers' undesirables check, embuary's player monitor, Google Drive's export/download/player services and source port | Partly done: Embuary Helper service off; audit recorded; Umbrella/cocoscrapers not patchable here | bootstrap housekeeping switches off script.embuary.helper's service (fanart grabber, widget timer, player monitor); other services audited and kept; Umbrella/cocoscrapers need their source |
| 1E.4 | Bootstrap imports 1.74 s: import page builders lazily | Source | Lazy bootstrap module imports |
| 1E.5 | TMDb Helper's Trakt check (1.66 s) after Home settles, not at launch | Source | Cached unexpired Trakt token; asynchronous confirmation |
| 1E.6 | Script windows close without "waiting on thread": daemon worker threads end with the window | Source | Stop-aware page workers |
| 1E.7 | Fewer always-on Python polling loops (0.1-1 s across the service) | Source | 8fb1c4b idle polling; six measured fake-clock cases |
| 1F.1 | Read the "interpreter wait" lines (probe in #19) and the system-networking upload speed from the r47 build | Measurement | Device showed ~3.3 MB/s, 4 ms interpreter wait; no remaining GIL-limit proof |
| 1F.2 | Drive and AllDebrid reads through system networking too (DriveStream, remote_media) | Native staged | Bounded NSURLSession reads; Foundation compile/fault tests pending |
| 1F.3 | AllDebrid → Drive copy loop in native code (read range, PUT piece), no bytes through Python | Native staged | Native validated range-to-PUT pieces; Python only handles receipts, session checkpoints and renewal |
| 1F.4 | More upload lanes once the bottleneck is gone (2 → 3-4) | Source | 80a082f at most three resumable file lanes |
| 1G.1 | 10-bit H.264 marked in the picker ("10-BIT · SLOW ON AIRPLAY", done in #19) | Source | Picker warns about 10-bit H.264 |
| 1G.2 | 10-bit conversion faster than real time (threads, two segments in parallel, GPU scaling) | Measurement tool added; no speed change made blind; needs the owner's device log | scripts/conversion_log.py reads the 'compat: segment N converted in MS ms (P% of realtime) via ROUTE' lines and says whether the 70 % target holds; levers listed below |
| 1G.3 | Pause Kodi's read-ahead while AirPlay starts | Coded for Drive copies (host-tested); debrid streams not covered; device check pending | Play on TV marks KodiIOS.AirPlay.Starting; the Drive proxy holds Kodi's own requests (not the AirPlay reader's) while it is fresh; debrid links Kodi reads directly are not controlled |
| 1G.4 | Hand the TV the playlist as soon as the first video segment is ready | Native staged | Prime target video/primary audio in parallel; new framework and timing required |
| 1G.5 | Blank AirPlay captions (ISSUE-147) | Partly done: caption path mapped and a log reader added; cause still needs the owner's device log | scripts/caption_log.py turns a kodi.log into one verdict on how captions reached the TV (off / burned in / WebVTT served / never read); the cause of the blank captions is unconfirmed |
| 1G.6 | Hour-long AirPlay stop (ISSUE-147) | Partly done: stop evidence reader added; no hour-long log exists, cause not established, nothing to fix yet | scripts/stop_log.py rebuilds the session timeline from the service's diagnostic lines and attributes a stop (expired token/link near 3600 s, failing reads, phone suspended, receiver) |
| 1G.7 | 10-bit H.264 ranked last in the picker (no hardware decoder on Apple devices) — **done** | Source | Stream ranking avoids live-conversion codecs when possible |
| 1G.8 | Play on TV on a download whose preparation has not finished: offer "Prepare first (about N min)" next to "Play now", move it to the front of the preparation queue, and play it as it is once ready (owner: "if the file is already good then no conversion is needed") | Source/native staged | Prepare-first plus ff04610 matched-Roku original-picture fallback |
| 3.1 | Background survival: iOS interrupts the silent-audio keep-alive | Coded (host-tested); iOS suspension itself is OS-managed; needs the owner's device log | background.watch: re-asks each tick, times recovery, and after 3 minutes of lost background audio with work waiting adds one Notifications entry; native restart logic unchanged |
| 3.2 | Transfers recover after Wi-Fi ↔ 5G changes without long waits | Native staged | Bounded HTTP/deadline recovery; real Wi-Fi/cellular handoff pending |
| 3.3 | Expired debrid links renewed mid-copy and mid-AirPlay | Source | e6041ae repeated long-play renewal and immediate copy reopen at same offset |
| 3.4 | Rig smoke list before every IPA (pickers, show page, settings, resume prompt, track menus) | Open | Automated pre-IPA real-rig smoke gate still required |
| 3.5 | Performance budget in diagnostics: tap-to-picture (1C.1), start-up stages, row requests per minute, seek-to-land; one summary line a minute | Partial | Total open timing exists; stage/row/seek summary still required |
| 3.6 | Log hygiene: Elementum config dump, deprecated `addStreamInfo`, duplicate keymap loads on resume | Open | Elementum config/legacy stream-info/keymap noise audit still required |
