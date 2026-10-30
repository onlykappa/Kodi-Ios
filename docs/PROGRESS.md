# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — building owner-authorized fully bundled IPA with automatic startup service; Elementum deferred
Progress: 25/39 task IDs COMPLETE (64.10%); 14 awaiting implementation.
Last completed task: P4-009 capture requirement inventory (184 retained IDs, zero actual captures); P4-007/008 static source and simulator investigations completed.
Next actionable task: run all regressions, publish validated bootstrap/builder changes, execute isolated Linux IPA workflow, inspect/fix real failures, record checksum/artifact; then stop for actual iPhone testing.
Active blockers: customized IPA build pending; real iPhone signing/bootstrap/UI/Drive/screenshots/rollback unverified. Manual-import requirement superseded. No Elementum engine.
Pending decisions: fully bundled IPA implementation/build explicitly approved. No additional Mac run authorized or required for resource-only packaging. Owner supplies physical device evidence after artifact is ready.
Latest implementation commit SHA reviewed: local a143c53 / published a2ce3cb5ca7e5520d5a7da0e848ac86709db1737 (equal code tree); successful artifact source. Resolve this final evidence commit from Git/PR head.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-30T01:06:45.279643+00:00
Last validation: 133 tests in 17 host suites pass; run 40981957027 validates 38 add-ons/30 configs and full apply/repeat-zero-writes/clean-restore with 7324 source files identical. Source Deck: 22463 files hashed, zero changes/additions/missing. Secret/history/private-value scans pass. 184 capture requirements retained, zero captures. See reports/phase4-import-artifact.json.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
