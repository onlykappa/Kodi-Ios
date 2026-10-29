# Persistent progress

Status: BLOCKED
Current phase: Phase 4 — owner-confirmed diagnostic launch; customized import and phone-local Elementum investigation in progress
Progress: 22/39 task IDs COMPLETE (56.41%); 17 awaiting implementation.
Last completed task: P4-001 — owner-reported diagnostic install/launch plus foundation provenance/entitlement inspection; no migrated-feature inference.
Next actionable task: Execute exactly one approved eight-minute macOS probe; inspect actual failure/success and foundation dependencies. Continue safe import preparation independently.
Active blockers: customized import not complete; missing layout input recovered and under validation; Elementum native iOS engine has no upstream release and requires port feasibility/build investigation. No remote host approved. Customized runtime, screenshots and rollback remain unverified.
Pending decisions: Separate import explicitly approved. One capped Mac build probe approved. No remote engine host or further Mac retries approved.
Latest implementation commit SHA reviewed: local b00991a / published a563adb2f4ac57414ad5c0ed7ce7a10848e6b0dc (equal content tree). Resolve latest tracker commit using git log -- docs/PROGRESS.md and PR head.
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T23:44:06.906798+00:00
Last validation: Roadmap seven regressions, scanner eleven, foundation parser eleven, unsigned builder seven pass; full secret/history/private-source comparison passes. Native probe bash syntax passes and local missing-SDK guard correctly blocks with exit 2; no engine compiled.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.
