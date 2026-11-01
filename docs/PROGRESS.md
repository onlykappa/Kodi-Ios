# Persistent progress

Status: IN PROGRESS — owner device testing of iPhone builds
Current phase: Phase 4 — portrait UI (r11), Elementum, Drive, Play on TV, video controls; owner tests each IPA on an iPhone 16 Pro
Last updated UTC: 2026-11-01T18:35Z
Latest installable IPA: build-94 (commit 93ba2ef, Kodi executable r5). Next: build with Kodi executable r6 (pending CI, see below).
Branches: feature/ios-migration (PR #1, all work), hold/ios-next (mirror), feature/settings-notifications (draft PR #3: plan only).

## Where things stand (2026-11-01)

Working on the owner's phone (owner-confirmed):
- Portrait-only menus (Apple TV-style mockup A: large titles, spotlight, rows, floating tab bar); fullscreen video turns landscape and back.
- Elementum in-process engine with Burst; Umbrella with CocoScrapers/AllDebrid; Google Drive sign-in (self-hosted worker, drive.file).
- Download with Elementum: button under Play on a show's season page (Full season / Choose episodes), long press › Download on movies, episodes, seasons, shows.
- "Choose a version" (Deck picker) for Elementum and Umbrella, portrait page; quality list shows only quality and version count.

Fixed today, awaiting owner retest:
- Setup crash (service.py reused `window`) that blocked every portrait refresh — fixed in build-88.
- Startup skin-reload loop (navigation framed the new video controls, portrait refresh rewrote them; 5 reloads per start) — fixed in build-94; owner log now shows 1 load, 0 files updated.
- Elementum: folders follow a reinstalled app's data folder; a start only counts as failed if the engine never answers; Retry starts it immediately.
- Long-press/Resume menus pinned (no 999 background), centred when there is no card; icons hidden when the list scrolls.
- Touch scrolling (Kodi patch): flick speed in pixels (r5), pan distance in skin units (r5), page group list takes momentum and receives vertical drags that start on a poster row (r6).
- Screen-size self-heal every 0.5 s (r6) for the "left 46% drawn" state seen after landscape video.
- Video controls redrawn from the owner's reference (plain white glyphs, thin bar with white knob, Info / Continue Watching as text); rig screenshot docs/player-controls-r2.png.
- Play on TV: TV search cancellable; Roku without "Play on Roku" (404) explained, AirPlay suggested.
- CI: IPA build retries mirrors.kodi.tv network errors; integrity check records portrait-written Fuse files.

Open / next:
1. Pin Kodi executable r6 when kodi-ios-portrait.yml publishes it, build and verify the IPA, send to owner.
2. Owner to retest scrolling smoothness, the video controls and the half-drawn-screen case; logs via the log uploader's previous log (kodi.old.log) or a screen recording.
3. Settings pages rework and notification center (planned in draft PR #3, not coded).
4. Roku: this TV has no Play on Roku receiver; AirPlay path only plays MP4/HLS.

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
