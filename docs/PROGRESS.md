# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — owner-confirmed diagnostic launch; customized import and phone-local Elementum investigation in progress
Progress: 25/39 task IDs COMPLETE (64.10%); 14 awaiting implementation.
Last completed task: P4-009 capture requirement inventory (184 retained IDs, zero actual captures); P4-007/008 static source and simulator investigations completed.
Next actionable task: Produce and inspect the customized public-source import artifact in the isolated Linux workflow. Then await owner phone export/import, functional, screenshot and rollback evidence.
Active blockers: complete source-acquired import artifact pending; actual phone profile access/clean export, customized import/activation, visuals, Google Drive and rollback unverified. Native Elementum explicitly DEFERRED BY OWNER, no replacement primary or remote host.
Pending decisions: no architecture decision pending; separate import approved. Further Mac runs require new approval; native engine deferred. Owner supplies phone tests/screenshots privately when package is ready.
Latest implementation commit SHA reviewed: local 6d72cc8123ad387c1464cdf779300468a9079528 / published fb7d3474ef019f63268a8cf3c6cfd958001d9ad2 (equal tree). Resolve current tracker commit with git log and PR head after this checkpoint.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-30T00:35:01.582386+00:00
Last validation: per-script regression suites pass; generic discovery failure retained in ISSUE-031. Static iOS target has 43 candidate dependencies, 32 payload files plus manifest. Foundation audit confirms supplied ARM64 PIL/API dependencies. Mac probe failed missing Go before compilation; no retry.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
