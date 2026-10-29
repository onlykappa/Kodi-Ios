# Persistent progress

Status: IN PROGRESS
Current phase: Phase 3 — P3-005/P3-006 validation and recovery documentation
Progress: 19/39 task IDs COMPLETE (48.72%); 20 awaiting implementation.
Last completed task: P3-004 credential-free integration, pinned add-on ZIPs and static dependency closure.
Next actionable task: finish P3-005/P3-006, record passing evidence and STOP at Phase 3 review gate.
Active blockers: local socket restriction persists, but approved CI resolved the required host tests (42/42). No Phase 3 host-test blocker remains. Actual iPhone/runtime/authorization tests remain Phase 4.
Pending decisions: none for approved direct architecture or capped test job; Phase 4 needs separate review/authorization.
Latest implementation commit SHA reviewed: ec1aace1e84044627649f48e6febc89b5956f0e3 (approved workflow publication).
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T19:46:51.748394+00:00
Last validation: CI run 40940315803 passed all 42 upstream tests; 12 provider tests and 9 mocked refresh/resume tests passed. Original failed local preflight retained; current static integration/ZIP checks pass.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. Follow P3-001 through P3-006, with owner architecture approval required at P3-002. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 3 authorized only. Architecture approved; Required host tests now pass in the approved CI executor. After resolving it, stop again for independent review after completing Phase 3. No Phase 4, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
