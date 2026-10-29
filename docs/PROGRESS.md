# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — host candidate prepared; physical testing and deployment decision pending
Progress: 21/39 task IDs COMPLETE (53.85%); 18 awaiting implementation.
Last completed task: P3-006 (Phase 3 passed owner independent review). No Phase 4 task is marked complete without its acceptance evidence.
Next actionable task: Owner chooses first-run import versus automatic bootstrap, then supplies actual signer/launch/profile-access evidence for diagnostic candidate. Resume P4-001 dependency order; no Phase 5.
Active blockers: P4-001 actual signing/OS behavior unverified; P4-002 full migrated IPA/import and clean target recovery absent; ISSUE-020 generated skin parity; real screenshots and functional/rollback evidence absent. Local DNS unavailable; CI acquisition succeeded.
Pending decisions: Separate first-run configuration/add-on import versus proven automatic IPA initialization (question sent); actual iPhone testing/screenshots supplied by owner when ready.
Latest implementation commit SHA reviewed: Local 34a476f; published equivalent e7a657ba73fab2381112ce29004a3d55c2687262. Resolve latest tracker commit using git log -- docs/PROGRESS.md and inspect PR head; preserve both histories.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T23:03:10.907434+00:00
Last validation: 11 static Mach-O/entitlement parser tests, five unsigned ZIP/signature tests and three source-comparison tests pass. Foundation CI 40951457120 and unsigned candidate CI 40952213893 passed. Project checks/secret scans must pass before each publication; final results in reports/phase4-validation.json.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Wait for pending choice and actual-device evidence; no Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
