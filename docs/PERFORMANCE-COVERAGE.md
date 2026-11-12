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
| 1A.4 | Warm the first megabytes and the index when a movie or episode page opens (not on every row focus) | Open | Implementation and regression coverage still required |
| 1A.5 | Seek on Drive copies through the native reader with read-ahead from the new position | Open | Implementation and regression coverage still required |
| 1B.1 | Apply the MKV skip-attachments patch (already in the AirPlay FFmpeg) to Kodi's own FFmpeg in the Kodi build | Native staged | Kodi FFmpeg attachment skip; new executable required |
| 1B.2 | Network-aware probe limits: smaller `probesize`/`analyzeduration` for http/plugin sources, larger for local files | Open | Implementation and regression coverage still required |
| 1B.3 | Cache settings for phones: start playback after a small cache fill; read factor tuned for 5G vs Wi-Fi | Open | Implementation and regression coverage still required |
| 1B.4 | Debrid links: keep Umbrella's resolve, but start Kodi reading the link while the source window closes | Open | Implementation and regression coverage still required |
| 1C.1 | One timing line per play: tap → plugin → resolve → OpenFile → stream open → first picture, in the diagnostics log | Partial | Total tap-to-playing line; stage breakdown still required |
| 1C.2 | Check for a completed copy before TMDb Helper builds its player list; play it straight away | Source | fast_copy before TMDb player construction |
| 1C.3 | Ship TMDb Helper's `resources/players/` folder (or point it at ours), so it stops failing two directory reads per play | Source | Bundle contains TMDb players directory |
| 1C.4 | Cache TMDb item details for the titles on screen (spotlight, Continue Watching) so Play needs no network | Open | Implementation and regression coverage still required |
| 1D.1 | Stop Home rows reloading on tab return: Kodi re-requests a plugin row whenever Home becomes visible again; give rows a stable path and refresh only when the listing cache says the content changed | Partial | Playback invalidation patched; Home-tab return not independently proved |
| 1D.2 | No row refresh while a video opens or closes; refresh Continue Watching once after playback stops | Native staged | Plugin-row invalidation guard; new executable required |
| 1D.3 | Load only the rows the visible tab shows; Movies and TV hubs load when opened | Open | Implementation and regression coverage still required |
| 1D.4 | Spotlight: show the loading ring only when the hero has no items (owner screenshot shows it over a loaded hero) | Open | Implementation and regression coverage still required |
| 1E.1 | Start Elementum's daemon only when Download is chosen (or a torrent is active), not at every launch | Source | Elementum demand startup |
| 1E.2 | Remove unused binary add-ons from the IPA: 20+ PVR clients, ~22 audio decoders, game add-ons | Source | 89c2f88 staged add-on pruning; package tests |
| 1E.3 | Trim services: Umbrella's update check, cocoscrapers' undesirables check, embuary's player monitor, Google Drive's export/download/player services and source port | Partial | fe88828 unused Drive services; provider/skin service audit remains |
| 1E.4 | Bootstrap imports 1.74 s: import page builders lazily | Source | Lazy bootstrap module imports |
| 1E.5 | TMDb Helper's Trakt check (1.66 s) after Home settles, not at launch | Source | Cached unexpired Trakt token; asynchronous confirmation |
| 1E.6 | Script windows close without "waiting on thread": daemon worker threads end with the window | Source | Stop-aware page workers |
| 1E.7 | Fewer always-on Python polling loops (0.1-1 s across the service) | Source | 8fb1c4b idle polling; six measured fake-clock cases |
| 1F.1 | Read the "interpreter wait" lines (probe in #19) and the system-networking upload speed from the r47 build | Measurement | Device showed ~3.3 MB/s, 4 ms interpreter wait; no remaining GIL-limit proof |
| 1F.2 | Drive and AllDebrid reads through system networking too (DriveStream, remote_media) | Native staged | Bounded NSURLSession reads; Foundation compile/fault tests pending |
| 1F.3 | AllDebrid → Drive copy loop in native code (read range, PUT piece), no bytes through Python | Native staged | Native validated range-to-PUT pieces; Python only handles receipts, session checkpoints and renewal |
| 1F.4 | More upload lanes once the bottleneck is gone (2 → 3-4) | Source | 80a082f at most three resumable file lanes |
| 1G.1 | 10-bit H.264 marked in the picker ("10-BIT · SLOW ON AIRPLAY", done in #19) | Source | Picker warns about 10-bit H.264 |
| 1G.2 | 10-bit conversion faster than real time (threads, two segments in parallel, GPU scaling) | Measurement required | GPU scaling/hardware decode and software all-core decode exist; <=70% real-time cannot be certified without phone input |
| 1G.3 | Pause Kodi's read-ahead while AirPlay starts | Partial | Kodi paused before native open; cache-reader contention needs evidence |
| 1G.4 | Hand the TV the playlist as soon as the first video segment is ready | Native staged | Prime target video/primary audio in parallel; new framework and timing required |
| 1G.5 | Blank AirPlay captions (ISSUE-147) | Device required | Subtitle worker/HTTP retry repairs exist; actual missing-TV-caption cause unconfirmed |
| 1G.6 | Hour-long AirPlay stop (ISSUE-147) | Device required | Stop diagnostics exist; no continuous-hour failure captured or attributed |
| 1G.7 | 10-bit H.264 ranked last in the picker (no hardware decoder on Apple devices) — **done** | Source | Stream ranking avoids live-conversion codecs when possible |
| 1G.8 | Play on TV on a download whose preparation has not finished: offer "Prepare first (about N min)" next to "Play now", move it to the front of the preparation queue, and play it as it is once ready (owner: "if the file is already good then no conversion is needed") | Source/native staged | Prepare-first plus ff04610 matched-Roku original-picture fallback |
| 3.1 | Background survival: iOS interrupts the silent-audio keep-alive | Device required | Interruption/foreground recovery exists; iOS suspension remains OS-managed |
| 3.2 | Transfers recover after Wi-Fi ↔ 5G changes without long waits | Native staged | Bounded HTTP/deadline recovery; real Wi-Fi/cellular handoff pending |
| 3.3 | Expired debrid links renewed mid-copy and mid-AirPlay | Source | e6041ae repeated long-play renewal and immediate copy reopen at same offset |
| 3.4 | Rig smoke list before every IPA (pickers, show page, settings, resume prompt, track menus) | Open | Automated pre-IPA real-rig smoke gate still required |
| 3.5 | Performance budget in diagnostics: tap-to-picture (1C.1), start-up stages, row requests per minute, seek-to-land; one summary line a minute | Partial | Total open timing exists; stage/row/seek summary still required |
| 3.6 | Log hygiene: Elementum config dump, deprecated `addStreamInfo`, duplicate keymap loads on resume | Open | Elementum config/legacy stream-info/keymap noise audit still required |
