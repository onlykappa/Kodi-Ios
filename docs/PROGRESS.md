# Persistent progress

Status: IN PROGRESS — owner device testing of iPhone builds
Current phase: Phase 4 — portrait UI (r11), Elementum, Drive, Play on TV, video controls, notification center; owner tests each IPA on an iPhone 16 Pro
Last updated UTC: 2026-11-01T22:30Z
Latest installable IPA: build-106 (commit 0e89856, Kodi executable r10: pop-ups only in the bell), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-106 . build-104 = r8. Builds 102/103 failed (wrong pin hash). build-101 must NOT be used (r8 Python on r7).
Branches: feature/ios-migration (PR #1, all work), claude/ios-migration-continue-3jjuif (this session, same commits), hold/ios-next (older mirror at f42dc07), feature/settings-notifications (draft PR #3: plan only).

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
1. Confirm the IPA run on this session's last commit publishes (Kodi r10 + ISSUE-064/065/066 Python) and send the owner the link.
2. Kodi executables: r11 = r10 (do not pin); r12 (run 41355566946, from 4be37f6) = tap logging + reload on layout width, no tap fix; r13 (queued, from this session's last commit) = r12 + KodiTouchWindow/KodiTouchRootView tap fix. Pin r13 with the Kodi hash from the release BODY and send that IPA (skip pinning r12 unless r13 fails to compile; then fix the patch).
3. Owner tests: video start (no Fuse bar), tapping anywhere on the video, controls, startup (no splash, time to Home), Continue Watching resume (no questions) and long press › Choose source. For the tap bug on r13: if taps still fail, send kodi.old.log (the "Tap at …" lines).
4. Settings pages rework (draft PR #3, not coded). Roku: no Play on Roku receiver on this TV; AirPlay path only plays MP4/HLS.

Blockers: device verification needs the owner; the tap bug needs the r12 log. Phase 5, merge and release are not authorized.

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
