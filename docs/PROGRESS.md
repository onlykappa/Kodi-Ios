# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — Touch-r2 serialized startup repair; host validated, IPA build pending
Progress: 25/39 task IDs COMPLETE (64.10%); 14 awaiting implementation.
Last completed task: P4-009 capture requirement inventory (184 retained IDs, zero actual captures); P4-007/008 static source and simulator investigations completed.
Next actionable task: build/publish Touch-r2, inspect actual Actions results, then owner retests Keep Skin, Settings/Recovery and navigation. Preserve both older IPAs.
Active blockers: owner Touch-r1 launch log verifies reversion/helper failure (ISSUE-040). New sequencing repair not yet phone-tested. Simulator unavailable; all 184 capture requirements retained. No Phase 5.
Pending decisions: fully bundled IPA implementation/build explicitly approved. No additional Mac run authorized or required for resource-only packaging. Owner supplies physical device evidence after artifact is ready.
Latest implementation commit SHA reviewed: local 8363797 / published 91ed4dd79d5637f57f2ae03fadc6cee4171fca06, successful Touch-r1 artifact source. Resolve later evidence-only commit from git log/PR head.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-30T15:11:28.675497+00:00
Last validation: 174 host tests/21 suites PASS including nine new sequencing regressions; roadmap 25/39 unchanged. Reachable-history/private-source secret scan PASS. Touch-r2 CI build pending; Touch-r1 device failure remains open. Sanitized evidence: reports/owner-touch-r1-launch-log.json; no raw log uploaded.

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
