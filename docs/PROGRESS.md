# Persistent progress

Status: IN PROGRESS — owner device testing of iPhone builds
Current phase: Phase 4 — portrait UI (r11), Elementum, Drive, Play on TV, video controls, notification center; owner tests each IPA on an iPhone 16 Pro
Last updated UTC: 2026-11-01T21:17Z
Latest installable IPA: build-104 (commit 2a31ebd, Kodi executable r8 + bell ingest), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-104 . Builds 102/103 failed (wrong pin hash); build-101 must not be used. build-101 (f42dc07) must NOT be used: its Python relies on r8 but it carries r7.
Branches: feature/ios-migration (PR #1, all work), claude/ios-migration-continue-3jjuif (this session, same commits), hold/ios-next (older mirror at f42dc07), feature/settings-notifications (draft PR #3: plan only).

## Where things stand (2026-11-01, evening)

Working on the owner's phone (owner-confirmed):
- Portrait-only menus (Apple TV-style mockup A), fullscreen video turns landscape and back.
- Elementum in-process engine with Burst; Umbrella with CocoScrapers/AllDebrid; Google Drive sign-in (self-hosted worker, drive.file).
- Download with Elementum (season page button, long press › Download); "Choose a version" (Deck picker) for Elementum and Umbrella.

Built, awaiting owner retest (none of this is device-verified):
- Startup skin-reload loop fixed (build-94); setup crash fixed (build-88).
- Touch scrolling momentum / drag routing (r5, r6); screen-size self-heal (r6).
- Landscape video fills the screen: window follows the scene on rotation (r7, ISSUE in d4bf39c).
- Hubs scroll past the floating tab bar; Home, Movies and TV are one preloaded window (d4bf39c).
- Turning the phone no longer reloads the skin; dialogs reload from the matching folder, fonts rescaled (r8, f42dc07).
- Notification center: bell, page, live downloads and Drive upload (47cf832).
- Every pop-up goes to the bell instead of the screen, never shown, also at start (ISSUE-063): Python in build-102; the Kodi side needs executable r10.

This session (2026-11-01, 20:40–21:10Z):
- Found PROGRESS.md behind the git log (stopped at 18:35Z); confirmed no branch newer than feature/ios-migration f42dc07.
- r8 executable published by run 41347339284 (release kodi-ios-portrait-r8; Kodi binary sha256 388560c2…7580 from the release notes). First pinned in 27371e9 with the zip's digest by mistake: IPA runs 102/103 failed at 'Portrait executable digest mismatch' (scripts/ios_portrait.py hashes the Kodi binary inside the zip). Fixed by pinning the binary hash. Rule for the next pin: use the hash in the release body, not the asset digest.
- Owner request (screenshots of cut-off pop-ups): all notifications in the bell under General; owner chose bell only. Implemented ISSUE-063 (Python + r9 patch). Host tests: 27 scripts pass (test_drive_runtime needs the CI source cache, not run here).

Open / next (exact next step first):
1. DONE 21:12Z: build-104 published and sent to the owner. r9 executable compiled and published (Kodi ca8d9fa8…04df) — proves the GUIDialogKaiToast change builds; r9 is not pinned.
2. Watch the executable runs: r9 (from 0005312) publishes first and is NOT to be pinned (it showed pop-ups on a first start); r10 (queued behind it, concurrency waits) is the one to pin. If either fails to compile, read the log and fix GUIDialogKaiToast.cpp in the patch. When r10 publishes, pin kodi-ios-portrait-r10 with the Kodi binary hash from the release body and send the next IPA.
3. Owner retests build-102 (see list above) and later the r10 build (pop-ups appear in the bell, none on screen); evidence by screen recording or kodi.old.log via the log uploader.
4. Settings pages rework: owner approved the mockups (docs/design/settings-mockups.html). Coded on branch design/settings-mockups (not built into an IPA yet, not device-verified): portrait Settings home + Customisation page (settings_page.py) and the Accounts page (accounts.py, accounts_page.py) with sign-in state for Elementum, Umbrella, Google Drive, Trakt and TMDb Helper. Next: SettingsCategory/DialogAddonSettings in the same style (Kodi's own leaf pages), then build and owner retest. Roku: this TV has no Play on Roku receiver; AirPlay path only plays MP4/HLS.

Blockers: device verification needs the owner. Phase 5, merge and release are not authorized.

Verification method: unit tests (scripts/test_*.py), desktop Kodi 21.3 rig at the phone's portrait (603x1167) and landscape (19.5:9) shapes, IPA download checks (zip integrity, Kodi binary equal to the pinned executable apart from the code signature), owner device tests. Nothing is called device-verified without the owner's evidence.

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
