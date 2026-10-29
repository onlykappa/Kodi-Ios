# Persistent progress

Status: BLOCKED
Current phase: Phase 3 — P3-004 blocked by upstream host-test preflight
Progress: 18/39 task IDs COMPLETE (46.15%); 21 awaiting implementation.
Last completed task: P3-003 OAuth design; P3-001 research and P3-002 owner architecture choice recorded.
Next actionable task: obtain results from an authorized test executor with loopback sockets, rerun the pinned upstream suite, then complete P3-004 through P3-006. Do not skip the eight failed tests.
Active blockers: local AF_INET sockets denied (EPERM); upstream suite 42 run / 34 passed / 8 errors. No integration-ready or Phase 3-complete claim. Binary asset acquisition was resolved using explicit base64 retrieval; all 97 source files verified privately. No complete distributable archive claimed.
Pending decisions: architecture selected by owner (direct add-on/public OAuth relay); no new hosting/spending approved. Need an authorized test executor with loopback sockets, not account credentials.
Latest implementation commit SHA reviewed: a6163a3c74c3ab9762ca403a8f7fab7bbe09e213 (published visual-roadmap expansion).
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T19:26:35.663824+00:00
Last validation: project regressions 27 passed; pinned upstream suite FAILED with 8 environment errors (reports/drive-upstream-validation.json). All 97 upstream source identities verified privately after supported base64 acquisition. Phase 3 not ready.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. Follow P3-001 through P3-006, with owner architecture approval required at P3-002. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 3 authorized only. Architecture approved; STOP on current test-executor blocker. After resolving it, stop again for independent review after completing Phase 3. No Phase 4, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Prepared for publication; owner approved capped Actions job; run result pending because Actions minutes may be consumed. Owner has now approved publishing the exact capped workflow. Do not claim test success until actual run logs are inspected.
