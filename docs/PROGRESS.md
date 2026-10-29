# Persistent progress

Status: IN PROGRESS
Current phase: Phase 4 — P4-001 trusted foundation acquisition and target constraints
Progress: 21/39 task IDs COMPLETE (53.85%); 18 awaiting implementation.
Last completed task: P3-006 operational recovery and device-test plan (P3-005 host/mock evidence passed).
Next actionable task: inspect the capped foundation acquisition job and record actual results before advancing dependencies.
Active blockers: local socket restriction persists, but approved CI resolved the required host tests (42/42). No Phase 3 host-test blocker remains. Actual iPhone/runtime/authorization tests remain Phase 4.
Pending decisions: no new hosting/spending; owner provides physical iPhone tests/screenshots when ready. Actual signing behavior remains unknown.
Latest implementation commit SHA reviewed: 4a3f04a7f2618152191c15bd1ff5f0c193b4a5f9 (local). Published equivalent: d6ba8c508a9f5981a2ef85bd19f56a045dc9aee2; tree d53e676a29e47ae1a24fa3c962106816f432befe. Latest tracker commit: resolve `git log -1 --format=%H -- docs/PROGRESS.md`.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T20:42:18.519179+00:00
Last validation: 43 project regression tests; 42 common upstream CI tests; 12 provider tests; 9 pinned-source mocked refresh/resume tests passed. Static/integrity, source comparison (22,463 files unchanged), package reproducibility and secret/history checks passed. reports/phase3-validation.json records commands and scope.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 authorized. Stop at its review gate or an unresolved prerequisite blocker; no Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
