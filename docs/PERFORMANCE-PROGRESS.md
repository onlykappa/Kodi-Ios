# Performance roadmap — progress log

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
- 1E.1 (code, needs the next IPA): Elementum's engine no longer starts at launch. The patched Elementum service waits until something asks (elementum_engine.ensure: Download, automatic episode download, any Elementum plugin request that is not handled by the cloud route) or until Elementum's download folder holds files (seeding / waiting for Drive); then it starts the engine in the same session. "Retry Elementum engine" unchanged. Expected: ~300 log lines, the libtorrent listener and the Go runtime gone from launch. Verified: test_speed_fixes, test_customized_ipa; device check pending.
- 1E.4 (code): service.py imports portrait (147 KB), driveupload, activity, signin_server, umbrella_ready, background and calibration on first use (a small _Late proxy; each is first used in a worker thread or later) instead of before "bootstrap entered". Expected: most of the 1.74 s moves off the main start-up path (host: these seven are about 0.1 s of 0.15 s on a laptop; the phone is ~10x slower with no .pyc). Verified: test_speed_fixes, test_bundled_bootstrap, test_episode_watch and every test that reads service.py; phone timing pending.
- 1E.6 (code): cause found in Kodi's PythonInvoker: a script stays open until every Python thread of its interpreter has ended, daemon threads included (it polls every 100 ms and logs "waiting on thread"). Our page refresh loops slept in monitor.waitForAbort(1-2) and ignored their page closing, so Notifications, Transfers, Accounts, Settings search, Library status and the tool pages waited up to 2 s on close. New page_wait.idle(stop, monitor, seconds) wakes the moment the page sets its stop event; the 9 loops use it. No non-daemon threads exist in our page scripts (checked by AST). TMDb Helper's own script.py waits are its own threads and are not changed. Tests: test_speed_fixes (idle wake/timeout/abort; no loop keeps the old sleep). Device check pending.
