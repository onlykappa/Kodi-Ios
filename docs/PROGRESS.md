# Persistent progress

Status: BLOCKED
Current phase: Phase 2 — P2-002 target constraints
Progress: 7/32 task IDs COMPLETE (21.88%); 25 awaiting implementation.
Last completed task: P1-006; all six Phase 1 task IDs complete with evidence.
Next actionable task: obtain owner iPhone/signing details, record verified constraints, then complete P2-002 before P2-003.
Active blockers: Owner has a sideloader for unsigned IPAs. iPhone model, exact iOS, jailbreak status, existing Kodi build and sideloader name/version/input constraints remain missing. No target assumptions authorized.
Pending decisions: see docs/DECISIONS.md.
Latest implementation commit SHA reviewed: 13a7ec1b6c2809cb263b2c0de4cf0092f2d2f8e4 (Phase 1 remote publication).
Roadmap publication commit: resolve `git log -1 --format=%H -- ROADMAP.md`; this avoids a self-referential SHA. Verify against PR head before resuming.
Last updated UTC: 2026-10-29T18:38:15.039270+00:00
Last validation: reports/phase1-validation.json; dynamic roadmap tests (4), scanner tests (9), snapshot/history/private-value scan and isolated recovery verification passed.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. P2-002 is blocked pending owner facts; do not bypass dependency order. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 2 authorized only. Stop on the current missing-input blocker. After Phase 2 completion, STOP for independent review. No Phase 3, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.
