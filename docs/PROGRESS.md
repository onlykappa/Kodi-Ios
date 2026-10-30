# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — verified owner-reported Fuse navigation failure; touch/recovery revision rebuilding
Progress: 25/39 task IDs COMPLETE (64.10%); 14 awaiting implementation.
Last completed task: P4-009 capture requirement inventory (184 retained IDs, zero actual captures); P4-007/008 static source and simulator investigations completed.
Next actionable task: build the revised all-in-one Touch-r1 IPA, inspect actual CI contents/results, publish a separate artifact, then obtain owner Settings/menu/scroll/select/long-press and empty-state retest evidence.
Active blockers: owner confirms prior Fuse navigation/setup failure. Hidden input.enablemouse API rejection and recovered-marker retry defects are reproduced/fixed on host; exact phone journal unavailable. Revised touch alignment, menus, generated includes, Drive and recovery require device retest.
Pending decisions: fully bundled IPA implementation/build explicitly approved. No additional Mac run authorized or required for resource-only packaging. Owner supplies physical device evidence after artifact is ready.
Latest implementation commit SHA reviewed: local a115193 / published 0b169c6622031d4ca4ccdbbff6f4ef8d3523223a, successful final IPA source; resolve this later evidence commit from git log/PR head.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-30T13:48:25.519377+00:00
Last validation: see reports/ios-navigation-tests.json; 76 actual verified-copy window XMLs patched idempotently, no application rendering claimed. Screenshot/owner statements recorded as failure. Previous IPA kept for rollback; no simulator support established.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
