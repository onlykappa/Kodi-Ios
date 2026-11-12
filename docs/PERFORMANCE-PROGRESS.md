# Performance and quality progress

## PR #19 review repair checkpoint — 2026-11-12

- Separate source commits: ISSUE-171 real token renewal; ISSUE-172 bounded HEAD; ISSUE-173 bounded season scans +
  active cancellation; ISSUE-174 Roku Media Assistant fallback preserving compatible 4K HEVC.
- Owner explicitly chose Media Assistant for Roku receivers that otherwise convert HEVC through AirPlay.
- Current pins are still Kodi r30 / AirPlay r46. New fallback is capability gated and requires the next native
  build's kodi_airplay_serve_copy + correlated receiver evidence. No IPA/native release dispatched here.
- Compiled recommendations suite: 41 checks, 0 failures. Phone/TV acceptance and hour-long/caption tests remain open.

## Current state and handoff (read this first; updated 2026-11-12)

Rule (owner, 2026-11-12): every fix is committed AND pushed to GitHub as soon as it is coded, by every agent, so a
later agent can see where things stand from the PR alone. Agents push only their own branch; no force-push.

Where everything lives
- Branch `claude/performance-roadmap`, PR #19 (draft, not merged). Every push builds an IPA (import-review workflow).
  Owner's last device build: 252. The roadmap is `docs/ROADMAP-PERFORMANCE.md`; issues in `docs/ISSUES.md`
  (latest ISSUE-169). Nothing is merged or released without the owner asking in the conversation.
- UI work from the approved mockups (PR #20, `docs/design/fuse-windows-mockups.html` on branch
  `claude/fuse-window-mockups-v9thgx`): coded on branch `claude/fuse-windows-code-2` (on GitHub; its agent stopped).
  Done there, not yet reviewed or merged: board 03 alert, 04/05 opening card + buffering bar, 06 bar (DEC-036),
  09 All Links states, 10 Umbrella page, 12 search. Not done: 07 context menu, 08 Info card, 11 options sheet,
  13 start-up. Review, rig-check, then merge into `claude/performance-roadmap`.
  Branch `claude/fuse-windows-code` (an earlier Haiku attempt) is superseded; ignore it.
- Speed work by the Sonnet speed agent (branch `claude/speed-fixes`) is merged into #19.

Done (code in #19; device checks pending unless the owner said otherwise)
- Bugs: 26 of 30 (B.1-B.11, 2.1-2.6, 2.8, 2.9, 2.11-2.15, 2.17, 2.18); 2.19 checked as working. Open: 2.10 (needs a
  screen recording), 2.7 (device check), 2.16 (log noise only).
- ISSUE-169: season downloads never take a whole-series pack; "Cancel all downloads to Drive" (Notifications long
  press on the upload card, Library status sheet "Cancel All"); whole-series packs marked WHOLE SERIES.
- Speed: 1A.2, 1B.1*, 1C.1, 1C.2, 1C.3, 1D.1/1D.2*, 1E.1, 1E.4, 1E.5, 1E.6, 1F.1 (answered: uploads ~3.3 MB/s,
  Python waits 4 ms), 1G.1, 1G.7 (10-bit H.264 last for streams), 1G.8 (Play on TV on an unprepared download:
  "Preparing first", front of the queue, no live conversion). Picker modes: Umbrella = stream (AirPlay-ready first:
  AV1, 10-bit H.264, DV-only last); Elementum = download (best seeded at the chosen quality; AV1 last).
  * needs Kodi r31 (Kodi patch: MKV attachments skipped, Home plugin rows kept around playback; also the 2.4 "- "
  prefix and 2.5 PIN keyboard).

Builds still to make (owner approval for the IPA is in the conversation; merging is not)
1. Kodi r31 from `migration/ios-portrait/kodi-21.3-portrait.patch` (kodi-ios-portrait workflow, then pin in
   `migration/ios-portrait/source-lock.json`; patch_sha256 there is stale, nothing reads it).
2. AirPlay r47 (system networking for uploads, resume-point start): candidate from the airplay-remux run on the PR
   head; pin in `migration/airplay-ios/source-lock.json` + `scripts/test_airplay_remux.py`, then airplay-ios with
   publish_verified_candidate=true.
3. IPA via import-review (runs on every push to #19).

Next work (in order)
1. Review/merge the mockup agent's branch (rig-check each board: scripts/kodi_rig.py, docs/design/KODI-RIG.md).
2. 1A.1 DONE as the app's own Drive proxy (drive_proxy.py, Python; no framework build): check open timing and seeks
   in the owner's next log. 1A.3 (keep the MP4 index) can now cache the tail in drive_proxy. A second Sonnet agent
   works on 1E.7, 1E.3, 1E.2, 1D.3, 1F.4 on branch claude/speed-fixes-2 (local until reviewed).
3. 1G.2 conversion faster than real time (only AV1 / 10-bit H.264 / unprepared downloads need it now).
4. 1E.2/1E.3/1E.7 start-up trims, 1F.2-1F.4 uploads to line speed, 1D.3 rows for the visible tab only.
5. MKV fonts trade-off (1B.1): owner chose faster opens with the plain subtitle font (2026-11-12). Applies to every MKV Kodi opens: Umbrella streams and Elementum; prepared Drive MP4s are unaffected.

## Log (newest last)

Read this first when taking over. The plan is docs/ROADMAP-PERFORMANCE.md. Update this file at every step:
what was done, where it lives (branch, commit, run), what was verified (and how), what is next.
Never claim a phone result without the owner's log or screenshot.

## Current state

- PR #16 (claude/trusting-euler-kgug98 → main): owner asked to merge (2026-11-11). Head eb91571. Merge only with green
  checks (review, host-tests, executable).
- Build 229 is the owner's current app. Build 230 (pending) = PR #16 merged + AirPlay r47 (kodi_http_send for uploads,
  EXT-X-START, MKV audio seek, attachments skip) + Kodi r30. Source of truth for what each build holds: docs/PROGRESS.md.
- Desktop Kodi rig: KODI_RIG_HOME=/root/.cache/kodi-rig-test. Restart with `kodi_rig.py start`; after copying the add-on
  run kodi_rig.bootstrap_copy (keeps the rig_builtin hook); `sync` regenerates pages; ReloadSkin. A Trakt sign-in prompt
  appears on Home in the rig only: send Input.Back twice before opening a page. Script windows (sheets) must be closed
  with Input.Back or an xdotool tap (DISPLAY=:5), not Dialog.Close.

## Steps

| When (UTC) | Step | Result |
|---|---|---|
| 2026-11-11 16:30 | Roadmap drafted (phases 0-3) after the 1-10 audit | docs/ROADMAP-PERFORMANCE.md |
| 2026-11-11 16:30 | Phony individually downloaded episodes added as 2.2 | finding only, not fixed |
| 2026-11-11 16:40 | 1B.1 version rows badge 10-bit H.264 "SLOW ON AIRPLAY" (deck_picker.converts_for_tv) | local branch phase1-work 6779f62; test_deck_picker TvReady |
- 1A.1 (code): interpreter_probe.py + service thread logs 'Kodi iOS interpreter wait: median/p95' once a minute while an AllDebrid→Drive copy runs. Test scripts/test_interpreter_probe.py. Needs a device log to read.
- 2.2 (code): cause found: a single-episode copy goes to Drive folder named from the file ('phony'), and the Library searched TMDb by that name only, so it could land on another show or none, with no episode names, stills or plots. Fix: finished copies record the job's show_tmdb under the title and folder names in drive-library-art.json (drivelibrary.remember_show, debrid_drive.remember_shows, plus a one-time backfill from finished jobs at service start). Episode rows with no TMDb name read 'Episode N', not the show name. Tests in test_library_pages and test_debrid_drive. Needs a device check on Phony.

## Handoff (2026-11-11 ~17:00 UTC)
- PR #16 head 027f4c3 (CI apt timeout fix); checks were running. Merge #16 when green.
- Do NOT merge #17 or #18 (owner, 2026-11-11): an agent works on them first. Their open work: 2.3 add-on settings tabs
  (board 08), 2.4 "- " dash (Kodi patch), 2.5 Kodi PIN/time number pads, 2.6 More/power-menu links to old windows,
  ISSUE-156 "Find subtitles online" against the real site.
- This branch (claude/performance-roadmap) = #16 + roadmap docs + 1B.1, 1A.1, 2.2. After #16 merges it shows only these.
- Then: pin AirPlay r47 from the airplay-remux run on 027f4c3 (framework zip sha256, exports _kodi_http_send, health,
  startup_budget; source_commit 027f4c3, previous r46), dispatch airplay-ios.yml publish_verified_candidate=true,
  import-review.yml for build 230, verify, record in PROGRESS/HANDOFF.
- Next items: 1A.2, 1B.3, 1B.2, 1C.1, 2.1, 2.3-2.6.

## 2026-11-11 investigation (owner: "investigate before we code")
- Read owner logs e8ab5995 and 396d5d67 (build 229) and the 37 earlier logs. Roadmap rewritten with measured timings,
  known causes and new items 1A-1G, 2.8-2.17, 3.5-3.6. No code changed for these yet.
- Biggest finds: Drive playback goes through plugin.googledrive's Python proxy (open 11-13 s, seek 4.2 s); Home rows
  reload on every tab return and around playback (31 Python runs each); Drive copies ignored outside Continue
  Watching (ios_watch_dialog cloud=resume) which also breaks Next Episode; subtitle site does not resolve.

## 2026-11-11 build 232 log (eabc204b)
- ISSUE-168 found and fixed: drive_uploads crashed at start (UnboundLocalError 'airplay'), so build 232 never uploads or
  copies. Fix in service.py; scripts/test_service_scoping.py catches it. Needs the next build.
- Roadmap: "Build 232 findings" B.1-B.11 and "UI" U.1-U.14 (Arctic Fuse/Kodi windows that need mockups) added.
- 2.8 (code): Drive copies found on every way in (Next Episode, spotlight Play, show pages) from the saved Drive listing, no network wait; a failed Drive check there counts as no copy. Continue Watching keeps the strict check. Fixes 2.9 when the episode is on Drive. Tests: test_drive_library (cached_only). Device check pending.
- B.3/B.4/B.5 (code): Library playback carries title, show, S/E, plot, runtime and art from the saved TMDb details (ios_library.playback_details); never the file name. Subtitle search reads show/S/E from the release name when Kodi has none (track_menu.from_release). Tests: test_library_pages, test_doh_fetch.
- 2.13 (code): subtitle downloads retry through DNS over HTTPS (1.1.1.1) when the phone's DNS refuses the site (doh_fetch.py); certificate still checked for the site's name. Device check pending.
- B.2, B.6, B.7/2.12, B.8, 2.14 (code): Volume boost 3 dB a tap with the value in the row and Kodi's slider closed; Subtitles › More and found subtitles as rows in the menu; Playback speed as a track-menu mode; no updates after the menu closes; menu opens on Close then focuses its filled list. Tests: test_track_menu. Rig check pending (layout).
- B.9 (code): Save to Google Drive / Uploads paused questions use the approved sheet (elementum_cloud.ask), Kodi's box only as fallback. B.11: Elementum-side diagnostics attach to the app session (build named). Tests: test_elementum_cloud, test_auto_season.
- B.10 (code): 1337x and BT4G (0 results in all 10 owner searches, ~2.4 s each) turned off once per phone (bootstrap.burst_providers); a later choice to turn one on stays. Search-progress display waits for mockup U.9. Test: test_bundled_bootstrap.
- 2.9 (code): Next Episode stops the video and waits until it has closed before asking for the next one, so the source question is no longer dismissed by the closing player. Test: test_next_episode.
- 2.15 (code): Skin Settings checks Fuse's conditions with $EXP[...] names expanded from the skin's own <expression> definitions (unknown ones false), so Python no longer logs parse errors. Test: test_skin_settings.
- 2.17 (code): a show with no finished episode shows one row 'No finished episodes yet' with where to see progress, not a blank page. 2.16 left as log noise (Kodi's remembered view control hidden on some pages). 2.10: no code defect found (Play reads the spotlight item at tap time; no auto-rotation); needs a screen recording to reproduce.
- 2.11 (code): the Library movie resume question uses the approved sheet (Kodi's box only as fallback); Download/Stream already uses the sheet in build 232 (seen working in log eabc204b: picked 0).
- 2.4/2.5 (Kodi patch, needs Kodi r31): sub-settings without the '- ' prefix on iOS; number and PIN prompts (ShowAndGetNumber, ShowAndVerifyInput) on the iPhone keyboard, digits kept; time/date/IP pads stay Kodi's. git apply --check passes on Kodi 21.3. Test: test_kodi_patch_ios.
- 2.6 (code): More › File manager → Transfers (our page); recovery menu Skin settings → our Skin Settings page, Local videos → Library.
- 2.3 (code, rig-checked: desktop Kodi rig, TMDb Helper settings): add-on settings as board 08: add-on name as title (System.AddonTitle), Cancel / Done, sections in a segmented control (4 wide, more scroll). The '- ' prefix there goes with the Kodi r31 patch (2.4).
- Rig check (desktop Kodi rig, landscape menus drawn squashed into the portrait rig window): Playback speed opens as a track-menu list with 1x ticked; Audio shows the boost value; tapping + logs 'volume boost +3 dB', the row reads +3 dB and Kodi's slider does not appear. Title widened so 'Playback speed' fits.
- 2.1 (code, rig-checked: desktop Kodi rig, sample links via umbrella_picker): Show All Links opens the All Links page (board 16): back, sort menu (Best First / Smallest / Most Seeds, re-sorts in place), large title, title · N versions, rows with release title, up to four tag pills (AV1 orange) and size · seeds. The quality page keeps its poster layout. Tests: test_deck_picker (sort, row fields).
- 2.18 (code, rig-checked as a script window: Kodi blocks add-ons from opening DialogBusy): after 2 s the busy ring gets 'Still working…' and Cancel (Kodi's Back, which stops an add-on resolve) on a dark backing; short loads keep the bare ring. Test: test_pages.
- 2.19: checked, no change: a tap on a Continue Watching card plays it (the item's own path); the menu in log e8ab5995 came from a long press (keymap longpress = RightClick), which opens the restyled context menu.
- Status 2026-11-11 evening: of the 30 bugs, 26 fixed in code (B.1-B.11, 2.1-2.6, 2.8, 2.9, 2.11-2.15, 2.17, 2.18), 2.19 checked as working (long press = menu, tap = play). Left: 2.10 (no defect found; needs a screen recording), 2.7 (bold search: device check only), 2.16 (Library focus errors are log noise; changing the declared views risks the show page). Kodi patch changes (2.4, 2.5) need Kodi r31; uploads (B.1) and native uploads need the next IPA with AirPlay r47.
- 1C.2 (code): TMDb Helper's router calls ios_watch_dialog.fast_copy before building players: a copy already on the phone or Drive (title from the Library's saved art, saved Drive listing) plays through ios_library.play_downloaded with full details; Continue Watching and Choose source keep the full path. Saves the 1.4-2.1 s TMDb details fetch on Next Episode, spotlight Play and show pages. Tests: test_downloaded_play (FastPath), test_import_builder.
- 1D.1 finding: Home's 31 rows reload after every video because the phone rotates back to portrait and the Kodi patch reloads windows for the new layout (log 396d5d67 09:36:46 'Screen rotated' then 32 rows in 2.0 s). Fix belongs in the Kodi patch (keep Home's list providers across a rotation); next Kodi build.
- 1A.2 (code): Library playback of a Drive copy hands Kodi the Drive add-on's local stream address directly (port from its settings, file name from the saved listing), skipping its play step (a Drive request, ~1 s). Falls back to the add-on link when unknown. AirPlay/cast read the resolved address either way. Test: test_drive_library. The proxy's own 5-6 s open remains (1A.1 native reader).
- 1C.3 (code): TMDb Helper gets an empty resources/players folder in the IPA, ending two failed directory reads per play. Test: test_import_builder.
- ISSUE-169 (code): season downloads never take a whole-series pack; Cancel all downloads to Drive (Notifications long press, Library status sheet). Owner's build-252 log also shows uploads at ~3.3 MB/s and interpreter wait median 4 ms: Python is not the upload limit any more (1F.1 answered).
- ISSUE-169 follow-up (code): source_match.coverage marks complete-series / 'Collection of 500' / '001-250' packs 'Whole series' (badge WHOLE SERIES), ranked after real season packs and never auto-picked for a season. Test: test_source_match.
- 10-bit finding: of 56 prepared downloads, 48 are 10-bit HEVC (copy=True: an Apple TV plays them as they are), 5 AV1 (converted), 3 H.264. AirPlay clients in the logs: Apple TV and a Roku TV. Stutter comes from the Roku path, which needs H.264 and converts the picture live on the phone; fix is 1G.2 (conversion faster than real time) plus 1G.7 below.
- 1C.1 (code): every video open from the Library, the watch menu or a completed copy logs 'Kodi iOS open timing: X s via <route>' once the picture plays (open_timing.py; service polls 0.2 s only while a mark is set). Test: test_open_timing.
- 1E.1 (code, needs the next IPA): Elementum's engine no longer starts at launch. The patched Elementum service waits until something asks (elementum_engine.ensure: Download, automatic episode download, any Elementum plugin request that is not handled by the cloud route) or until Elementum's download folder holds files (seeding / waiting for Drive); then it starts the engine in the same session. "Retry Elementum engine" unchanged. Expected: ~300 log lines, the libtorrent listener and the Go runtime gone from launch. Verified: test_speed_fixes, test_customized_ipa; device check pending.
- 1E.4 (code): service.py imports portrait (147 KB), driveupload, activity, signin_server, umbrella_ready, background and calibration on first use (a small _Late proxy; each is first used in a worker thread or later) instead of before "bootstrap entered". Expected: most of the 1.74 s moves off the main start-up path (host: these seven are about 0.1 s of 0.15 s on a laptop; the phone is ~10x slower with no .pyc). Verified: test_speed_fixes, test_bundled_bootstrap, test_episode_watch and every test that reads service.py; phone timing pending.
- 1E.6 (code): cause found in Kodi's PythonInvoker: a script stays open until every Python thread of its interpreter has ended, daemon threads included (it polls every 100 ms and logs "waiting on thread"). Our page refresh loops slept in monitor.waitForAbort(1-2) and ignored their page closing, so Notifications, Transfers, Accounts, Settings search, Library status and the tool pages waited up to 2 s on close. New page_wait.idle(stop, monitor, seconds) wakes the moment the page sets its stop event; the 9 loops use it. No non-daemon threads exist in our page scripts (checked by AST). TMDb Helper's own script.py waits are its own threads and are not changed. Tests: test_speed_fixes (idle wake/timeout/abort; no loop keeps the old sleep). Device check pending.
- 1E.5 (code, needs the next TMDb Helper build): patch_helper (build_import_review.py) makes TMDb Helper trust a saved, unexpired Trakt token at once and confirm it with the network in a daemon thread (a rejection clears TraktIsAuth so the next use checks again; an expired or missing token still takes the old blocking path). Expected: the first Trakt-using row/page no longer waits ~1.7 s. Asserts the hook text exists exactly once. Verified: test_speed_fixes (behaviour on stubs), patched the real 6.18.1 token.py in the rig copy and parsed it; phone check pending. Not "after Home settles" literally: the check was lazy inside the first Trakt use, so removing the wait there is the safer equivalent.
- 1B.1 (Kodi patch, needs Kodi r31 incl. a depends rebuild): kodi-21.3-portrait.patch now adds tools/depends/target/ffmpeg/kodi-ios-mkv-skip-attachments.patch (the AirPlay FFmpeg change: MATROSKA_ID_FILEDATA read as EBML_NONE, so the demuxer seeks past fonts/covers instead of downloading them) and makes the FFmpeg Makefile apply it after unpacking (and depend on it). build-kodi-ios.sh drops a cached "depends built" state once so FFmpeg rebuilds. The Kodi patch applies cleanly (apply --check on the Kodi 21.3 source copy); the embedded FFmpeg patch dry-runs clean with patch(1) against an unpatched matroskadec.c (not the exact 6.0.1 tarball: mirrors.kodi.tv is unreachable here, so the CI depends build is the real proof). Expected: MKV opens drop the 24-30 s attachment read. Side effect: embedded fonts of styled ASS subtitles are no longer loaded by libass (Kodi falls back to its default font; text still shows). Tests: test_kodi_patch_ios.
- 1D.1/1D.2 (Kodi patch, needs Kodi r31): CORRECTION of the earlier finding: the rotation is not the cause. Kodi's CDirectoryProvider::Announce marks every list provider invalid on Player OnPlay/OnResume/OnStop when its sort is "none" (every plugin row) and on VideoLibrary updates, so all Home plugin rows are fetched again when the video opens and when it closes (log 396d5d67: rows at 09:36:48 came with Home becoming visible after the stop; e8ab5995 09:32:27 rows before any rotation). Home itself is KEEP_IN_MEMORY and is not reloaded by the rotation. The Kodi patch now (iOS only, #if TARGET_DARWIN_EMBEDDED) skips those invalidations for plugin:// rows except the watch add-on's own rows (Continue Watching, Up Next, library), which refresh on stop and library change but not on play; the cached route (action=cached, the TMDb Helper rows) is excluded from refreshing. apply --check passes on Kodi 21.3. Expected: 11-17 row requests while a video opens and the burst after it closes disappear. Tests: test_kodi_patch_ios (hunk asserted). Not covered: the Home-tab tap (1D.1 "31 requests on tab return"), which needs a device log to separate from this.
- 1A.3 (NOT implemented, plan): the index read is Kodi's FFmpeg (use_mfra_for=pts, kodi-21.3-portrait.patch, DVDDemuxFFmpeg) asking for the last 16 bytes (mfro) and then the mfra box through the Google Drive add-on's local stream server: two ranged Drive requests (0.6-1.9 s) per open, for bytes that never change. Only whatever answers those Range requests can serve them locally, and today that is the third-party Drive add-on's Python proxy (patched in build_customized_ipa.py DRIVE_PATCHES), which 1A.1 replaces with a native range server; a cache in the old proxy would be thrown away, so this waits for 1A.1. Plan: (1) when preparation finishes (prepare_downloads layout_probe = fast_open.inspect, which already reads mfro and mfra to validate them) store the tail (the last `length` bytes named by mfro, a few KB) base64 in the file's Drive-library entry beside its size and modified time (drivelibrary.py; dropped when either changes); (2) the 1A.1 range server answers any Range wholly inside [size-length, size) from that entry with no Drive request (1A.2's direct_url already reads drive-library.json and can pass the entry on); (3) log "index served from cache" and compare the open timing line (1C.1) before and after. Needs a device log of an open to confirm those two requests are the whole 0.6-1.9 s.
- No-stutter (code): the version picker ranks 10-bit H.264 after every version that plays on the TV as it is (no hardware decoder on Apple devices: live AirPlay conversion runs slower than real time). Downloads were already safe: preparation re-encodes 10-bit H.264 to 8-bit H.264 once on Drive (kr_prepare copy_video). Remaining stutter case: AirPlay of a download before its preparation finished; next: 1G.8 prepare that video first / say so on the Play on TV card. Test: test_deck_picker NoStutter.
- Stream vs download (code): deck_picker.run(mode=) — Umbrella (umbrella_picker, live playback) uses 'stream': AV1, 10-bit H.264 and Dolby Vision without HDR10 go after versions AirPlay sends as they are. Elementum downloads keep Elementum's best-seeded order at the chosen quality (AV1 still after, slow to prepare); preparation converts anything else once on Drive. Tests: test_deck_picker NoStutter, test_source_match.
- 1G.8 (code): Play on TV on a Drive download whose preparation is waiting or running and whose picture needs converting (or not probed yet) asks first with the approved sheet: Prepare first (front of the queue, then it plays as it is) or Play now (live conversion, may stutter). Copy-only files (HEVC / 8-bit H.264 that only need repackaging) and ready files go straight on. Test: test_cast_ready.

- 1G.8 change (owner: "it should say prepare first"): no choice; Play on TV on an unprepared download that needs converting queues it first and says 'Preparing first'.
- ISSUE-170 (code): Continue Watching cards from Library playback get the TMDb name and art; old cards heal when shown.
- 2.10 (code): spotlight Play and Info ignore a tap while the spotlight is still sliding (!Container(4000).Scrolling), so they act on the title on screen. Tests: test_pages HeroTaps, test_portrait. 2.7 stays a device check; 2.16 stays log noise (changing the declared views risks the show page).
- 1A.1 (code): Drive copies from the Library stream through the app's own proxy (drive_proxy.py in the bootstrap service): Kodi's Range requests go straight to Drive's media download over kept-alive connections, 256 KB pieces, HEAD answered from a 1-byte read, one retry with a fresh token on 401. Replaces the Google Drive add-on's proxy (4.8-6.2 s opens, 4.2 s seeks: per-request account set-up and metadata). Falls back to the add-on's stream when the proxy is not running. Python-only (owner log: Python reads Drive at up to 35 MB/s); no framework build. Tests: test_drive_proxy (real HTTP: whole file, seek, HEAD, token retry), test_drive_library, test_cast_ready. Device check: 'open timing' lines and seek times in the next log.
- Fuse windows board 03 (alerts): DialogConfirm is the iOS alert (title, one line, hairline-divided buttons, one/two/three-button layouts, red destructive verb); ids 1/9/10/11/12/20 kept. Rig-checked (OK, Delete, three-button).
- Fuse windows boards 04/05 (opening card): DialogBusy is a centred card with a sliding bar instead of the ring (stages and slow text from Window(home) IOSOpen.Title/Source/Stage/Slow, which the opener must set; otherwise a small "Working…" card, Cancel 9850 after 2 s). Rig-checked in portrait via a script window; the opener does not set IOSOpen.* yet. Buffering capsule (Custom_1156) not done.
- Fuse windows board 06 (background progress): Kodi's progress box was already drawn by the activity pill; the pill and the Activity sheet rows now show a thin 4 pt bar (20 % white track, 0A84FF fill, grey paused, green done, sliding segment without a percentage) instead of the ring around the tile (DEC-036); the Home bell ring is untouched. Rig-checked (pill and sheet, 40 % job set through window properties).
- Fuse windows board 10 (Umbrella getting ready): source_progress.xml uses one 4 pt bar (follows Umbrella's percent once a source is known, slides before), percent only when known, icon-only mode a sliding bar instead of a ring. Rig-checked (source known 62 %, still looking). Routing Umbrella's list through the picker and closing the page before the sheet are not done.
- Fuse windows board 13 (startup): nothing to change, already in code: Startup.xml goes straight to Home after the first launch and Custom_1198 is never shown. The black launch screen is the existing black_launch_screen; the slow-first-run pill is not wired.
- Fuse windows board 09 (All Links states): the portrait DeckSourceSelect page gains "Still searching" (deck.status line, sliding bar, Stop 32511 sets deck.stop) and "No versions found" (deck.empty text, Try Again 32512 sets deck.retry); the picker does not set these properties yet. Rig-checked with a script window.
- Fuse windows board 12 (search results): results panel 5200 is now a list of 210-unit rows (poster, title, year and kind), with "No results for “x”" and a hint; bold matching letters not done (ISSUE-160). Rig-checked (real multi-search rows).
- Fuse windows board 05 (buffering, part 2): the OSD's "Buffering NN%" gets a thin bar (Player.CacheLevel) under it; Custom_1156 stays disabled (it froze Kodi, build 210). Not rig-checked (needs playing video).
- Fuse windows boards 07, 08, 11: not built, see the final report (07 and 11 already drawn by portrait with different content than the mockup assumes; 08 needs the Info button rewired).

## PR #19 review repairs — 2026-11-12

Owner asks for fixes committed separately. Source commits use [skip ci] to preserve the current no-IPA scope.
- ISSUE-171: rejected Drive tokens now really refresh, once across concurrent readers, without bypassing backoff.
  Host: test_drive_proxy 6 / test_drive_signin 7 pass. iPhone acceptance pending.

- ISSUE-172: size probes read at most one byte, even if Drive ignores Range. HTTP 200 uses its length and drops
  the unread connection. Host: test_drive_proxy 10 pass, including synthetic 20 GB metadata and transport failure.

- ISSUE-173: discovery is bounded to 60 seconds total / 25 per episode; Cancel interrupts the active HTTP wait.
  Unscanned episodes retain strict-quality retry eligibility. 92 focused host cases pass (29 season, 14 speed,
  30 watch, 13 cloud, 6 auto-season), including stalled local HTTP and late-redirect cancellation. No layout change.

- ISSUE-174: verified same-Roku fallback from live HEVC conversion to Media Assistant. Strict native copy-only
  serving refuses a downgrade, carries the playback position, and restores phone playback on failure. Source
  only until the new native framework is built/verified/pinned. Compiled host recommendations: 41/41.
