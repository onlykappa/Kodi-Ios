# Persistent progress

## Current handoff — 2026-11-04

The owner explicitly requested merging PR #7 into main without making an IPA, then opening one new draft PR for bugs handled one at a time. PR #7 is merged at `4a78efdeecbc6f9c47018682fbb60ff1829a8a95` (merge message contains `[skip ci]`). The existing build-141 was built from PR #7 head `c0d2746d76ff362bd18a9d1de30784ee375afa85` and includes KodiAirPlay r11. This supersedes the older unmerged/build-124/127 status below.

Follow-up branch: `fix/build-141-followup`, targeting main in a new draft PR. See [bug-fix handoff and log observations](BUGFIXES.md). A private owner log covers only 5.795 seconds of startup: four explicit warning entries, no error/fatal entries, no playback/AirPlay activity. No fix has started; next step is the owner's first bug, then diagnose/fix/verify one at a time in that same PR. No new IPA or follow-up merge until requested; use `[skip ci]` while the no-build instruction applies. Raw logs and private state stay outside GitHub. Host checks do not establish device success.

## Earlier progress (historical)

Status: IN PROGRESS — owner device testing of iPhone builds
Current phase: Phase 4 — portrait UI (r11), Elementum, Drive, Play on TV, video controls, notification center; owner tests each IPA on an iPhone 16 Pro
Last updated UTC: 2026-11-02T17:10Z
main (2026-11-02 17:10Z, owner: merge the new UI to main, no IPA unless required, everything merged before the audit): main = this branch, fast-forward, no force, commit message with [skip ci] so no build ran. It holds the r20 fixes (PR #5), UI round 2 (PR #6 feature/fuse-pages + design/settings-mockups) and Search (ISSUE-082, restored). No IPA has been built from it yet. Next: the owner's audit prompt (full audit, remove overlapping old code, hard simulation, before/after score; Elementum show download still broken). Performance pass (2026-11-02 23:00Z): draft PR #7, build-127 (f145ea1) for the owner's test, docs/PERFORMANCE.md; not merged. Latest installable IPA: build-124 (draft PR #5, commit 37331e3: Kodi app r20, KodiGlassBar r2, KodiAirPlay r4; ISSUE-076..081; Search held back), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-124 — sent to the owner for the r20 test; main untouched until the owner says to merge. Before: build-122 (commit a9cfd45, Kodi app r19: taps anywhere on the landscape video reach Kodi — play/pause, forward 10, CC, AirPlay), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-122 — sent to the owner for the button test. Earlier: build-120 (r18).
Branches: main (= feature/ios-migration since DEC-024; PR #1 merged), feature/ios-migration, claude/ios-migration-continue-3jjuif (this session, same commits), hold/ios-next (older mirror at f42dc07), feature/settings-notifications (draft PR #3: plan only).

## AirPlay MKV remuxer (2026-11-03, branch feature/airplay-mkv-remux)

BUILT ON HOST; device test pending (ISSUE-083). Remuxer + AAC audio bridge + HLS server in migration/airplay-ios/remux,
574 host checks pass on Linux; KodiAirPlay r5 links it (macOS CI job, not yet run). Not merged, no release, no PR.
Next: owner says whether to run CI on the branch and publish kodi-airplay-r5 for a test IPA.

## Where things stand (2026-11-01, night)

Working on the owner's phone (owner-confirmed):
- Portrait-only menus (Apple TV-style mockup A), fullscreen video turns landscape and back.
- Elementum in-process engine with Burst; Umbrella with CocoScrapers/AllDebrid; Google Drive sign-in (self-hosted worker, drive.file).
- Download with Elementum (season page button, long press › Download); "Choose a version" (Deck picker) for Elementum and Umbrella.

Owner-reported failures (build-104/106, 2026-11-01 night), see ISSUES:
- ISSUE-064 video: Fuse seek bar flashes at video start; taps register only on the left of the screen; controls do not respond, laggy. Seek bar and layout fixed on host; taps: UIKit window/root view left at the portrait width drops touches right of 46% — fixed in Kodi app r13 (from code reading).
- ISSUE-065 Arctic Fuse splash at start; slow start. Fixed on host.
- ISSUE-066 request: Continue Watching reuses the player and version picked first; long press › Choose source. Built on host.

Built, awaiting owner retest (none of this is device-verified):
- Startup skin-reload loop fixed (build-94); setup crash fixed (build-88).
- Touch scrolling momentum / drag routing (r5, r6); screen-size self-heal (r6).
- Landscape video fills the screen (r7); hubs scroll past the tab bar, Home/Movies/TV one preloaded window (d4bf39c).
- No skin reload on rotation; dialogs reload from the matching folder, fonts rescaled (r8).
- Notification center (47cf832); every pop-up goes to the bell, never shown (ISSUE-063, r10, build-106).

This session (2026-11-01, 20:40–22:20Z):
- Found PROGRESS.md behind the git log (stopped at 18:35Z); confirmed no branch newer than feature/ios-migration f42dc07.
- Pinned r8 (first with the zip digest by mistake: IPA runs 102/103 failed at 'Portrait executable digest mismatch'; scripts/ios_portrait.py hashes the Kodi binary inside the zip — use the hash in the release body). build-104 published.
- ISSUE-063 (bell only): Python ingest + Kodi r9, then r10 (never shows, creates the folder on a first start). r10 pinned; build-106 published.
- ISSUE-064/065/066 implemented on host; Kodi patch changed for r12 (tap logging, reload on layout width). Host tests: all 27 runnable scripts pass (test_drive_runtime needs the CI source cache).

Open / next (exact next step first):
1. DONE 22:11Z: build-107 (4be37f6: Kodi r10 + ISSUE-064/065/066 Python) published and sent to the owner.
2. DONE 23:22Z: r13 published by run 41357516449 (from 22e4349; Kodi 8574ab39…af23 from the release body) and pinned; build_tag left at r13 so no duplicate executable is published. r12 was never published (its queued run was replaced). Next: confirm the IPA run on the pin commit publishes, send the owner the link (full review build), then merge to main as the owner approved (record the decision).
2b. DONE 23:30Z: build-111 published and sent; merged to main as the owner approved (DEC-024): `git push origin e8a5bf4:main` (fast-forward from 644ce22, no force); GitHub marked PR #1 merged. IMPORTANT: every workflow triggers only on pull_request events (PR #1), so pushes no longer build anything until the workflows get push/workflow_dispatch triggers on main or a new PR is opened — first item of the cleanup.
3. Owner reviews everything at once on that build: video start (no Fuse bar), tapping anywhere on the video, controls, startup (no splash, time to Home), Continue Watching resume (no questions) and long press › Choose source, the new Settings / Accounts pages. If taps still fail, send kodi.old.log (the "Tap at …" lines).
4. Settings pages rework (owner-approved mockups, docs/design/settings-mockups.html), coded in another session on design/settings-mockups and MERGED here at the owner's request (22:35Z) for the next build: portrait Settings home + Customisation (settings_page.py), Accounts page (accounts.py, accounts_page.py) with sign-in state for Elementum, Umbrella, Google Drive, Trakt and TMDb Helper; Kodi's category pages (SettingsCategory) and add-on settings (DialogAddonSettings) in the same style. Rig-checked there in desktop Kodi 21.2 at 603x1167 (two rig bugs fixed); not device-verified. Roku: no Play on Roku receiver on this TV; AirPlay path only plays MP4/HLS. Round 2 (feature/fuse-pages, PR #6, merged 2026-11-02 at the owner's request): iOS alert/progress (DialogConfirm), text viewer, settings dialog, Add-ons, Event Log, System Info, File Manager, Umbrella's getting-ready window (umbrella_ready.py), Play on TV sheet (1080i/IOSPlayOnTV.xml; ISSUE-079 AirPlay routing kept in its send step). Checked in the Kodi 21.2 rig there; not device-verified. Not yet: Skin Settings, Hubs & Widgets (1115), add-on info, profiles, keyboard and the other shared dialogs.

Owner review of build-111/112 (23:40Z): video plays; play/pause and ±10 s still do not respond; controls laggy; one show crashed. r13 tap log disproved the window-size theory (all sizes correct, taps arrive in VideoOSD on the buttons) — see ISSUE-064. r14 (pushed): tap log no longer takes Kodi's GUI lock on the main thread (deadlock/crash candidate); builds run on pushes to main. Crash reports received: the video-start crash is a GL context race in the rotation code (ISSUE-067), fixed in Kodi app r15 — published 00:53Z and pinned (Kodi 50cab24b…fde1). Owner debug log: the OSD buttons do work; ±10 s failed on a raw 72 GB Blu-ray .m2ts from debrid (unseekable over HTTP); see ISSUE-064 follow-up. Log review fixes: ISSUE-068 (Elementum RPC after background), 069 (Umbrella double list), 070 (start-up errors), 071 (scripts by add-on id), 072 (custom windows parsed twice, Kodi app r16 building). Next: send the IPA built on the pin commit; r18 published 03:00Z (Kodi a30e92e4…3480, from 226755f: custom windows parsed once + click logging + full-screen GUI during video, ISSUE-074) and pinned; r16/r17 not pinned (Kodi hash from the release BODY), then ask for the button test (ISSUE-064); Library now lists Google Drive › Kodi Downloads with Kodi's library (ISSUE-073, ships in the next IPA); owner is testing Elementum download → Drive upload → play from Drive; owner: revoke the Trakt token exposed in the public paste, send a screenshot of the video controls, test with a normal .mkv source.

Owner log 03:45Z (pasted in chat; uploader failed, log too big): made by a build before r16, not build-120. The controls did respond (two taps on the drawn back-10 each sought −10 s; the third top-left tap stopped the video). New ISSUE-075: on the Elementum stream audio stalls 9 s after start and for seconds after each seek (large audio sync error, renderer timeouts) — the likely "lag". Exact next step: owner installs build-120 (https://github.com/onlykappa/Kodi-Ios/releases/tag/build-120), turns debug logging off, repeats the button test with an Elementum title and with a debrid/Drive file, sends kodi.log as a file (Files › On My iPhone › Kodi).

Root cause of the dead video buttons (07:00Z, ISSUE-064 follow-up 4): in landscape no tap right of the portrait width (1206 px) reaches Kodi — play/pause, forward 10, CC, AirPlay are all right of it; back and back-10 are left of it. Desktop Kodi simulation with Fuse + our controls: every button drives the player. Fix: Kodi app r19 (hit-test redirect + tap rescue from sendEvent:), published 07:12Z from 747ed40 and pinned (Kodi feb4a645…f7a4). Exact next step: when r19 is published, pin its Kodi hash from the release BODY in source-lock.json executable_release, push (fast-forward) to the three branches, DONE 07:18Z: build-122 published from the pin commit a9cfd45 and sent; owner: play/pause, CC, AirPlay, Continue Watching, then kodi.log as a file.

Owner report on build-122 (15:20Z, screenshot of Movies): tab-bar taps sometimes open Continue Watching behind it (ISSUE-076); downloads/uploads stop in the background (ISSUE-077); scrolling can be better (ISSUE-078); AirPlay connects but 0:00–0:00, no picture or sound (ISSUE-079). The owner's screenshot shows the debug overlay: debug logging is on, which itself slows scrolling. All four built in 3e851b5 (working branch only): Glass bar r2, KodiAirPlay r3 (sha256 null until published), Kodi app r20 (build_tag). Builds dispatched on the working branch 15:50Z (glassbar-ios, airplay-ios, kodi-ios-portrait). 16:30Z: owner added ISSUE-080 (download: no quality page, wants Download only / Download and watch) and ISSUE-081 (Kodi half drawn after AirPlay); both built; KodiAirPlay r4 staged, Kodi r20 build restarted with the ISSUE-081 change. Owner asked for a DRAFT PR for these bugs and to hold main until they test r20: test from the PR's build-N, merge only after their go-ahead. 16:20Z: owner added ISSUE-082 (Search like the Apple TV app); built and rig-rendered. All pinned on this branch: KodiGlassBar r3 (863dd6ef…), KodiAirPlay r4 (93739a92…), Kodi app r20 (47b98c8e…, from 6e52968, Kodi hash from the release body and checked in the zip). All tests pass. Draft PR opened from this branch to main; its import-review run publishes the test build-N. main untouched until the owner has tested r20 and says to merge. Earlier plan (done): when each release exists, pin glassbar-ios and airplay-ios sha256 from their release notes and executable_release r20 with the Kodi hash from the release BODY; run the tests (test_glassbar needs the bar pinned); push the pins to this branch and open the draft PR (claude/ios-migration-continue-3jjuif → main); its import-review run publishes build-N; send it with the test: tab bar near misses, download with Kodi in the background, vertical scroll on Home and the hero, Play on TV › AirPlay with an MKV (mirroring steps) — debug logging off.

Blockers: device verification needs the owner (review of build-111). Merge to main authorized and done (DEC-024); release and Phase 5 still need the owner's go-ahead.

Next after the owner's review: repository cleanup (version names such as 1.0 / Beta instead of rN, plainly named workflows and component releases, README, stale branches deleted only after the owner confirms the list) and a roadmap rework from version 1.

Verification method: unit tests (scripts/test_*.py), desktop Kodi 21.3 rig at the phone's portrait (603x1167) and landscape (19.5:9) shapes (not available in this session: the new layouts are not rig-rendered), IPA download checks (zip integrity, Kodi binary equal to the pinned executable apart from the code signature), owner device tests. Nothing is called device-verified without the owner's evidence.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.

## Owner-requested pause — 2026-10-30T14:02:35.605625+00:00

PAUSED at owner explicit request. Stop implementation/publication until resumed. Latest repair code is pushed: local 8363797 / remote 91ed4dd79d5637f57f2ae03fadc6cee4171fca06. GitHub Actions run 41068166024 continues independently as explained to owner; final artifact/result/checksum NOT YET retrieved or claimed. https://github.com/onlykappa/Kodi-Ios/actions/runs/41068166024 . On resume inspect that run/jobs/logs/artifacts, diagnose failures if any, verify the revised Touch-r1 IPA, and record/publish final evidence and link. Host tests: 165/20 suites (new live-setting readback regression passed). Original IPA retained; prior device failure remains unresolved until owner retest. No further feature development, Phase 5 or merge. This pause note is local/uncommitted to avoid starting another build.

## Resume after owner pause — 2026-10-30T14:24:00.732908+00:00

Owner explicitly resumed. Inspected run 41068166024: SUCCESS; revised artifact 12983492116 uploaded and not expired. Actual IPA checksum recorded in reports/ios-touch-r1-artifact.json. Prior pause above is historical and no longer active. Stop at Phase 4 device-test boundary after publishing evidence; do not infer the prior navigation failure is fixed on the phone.
