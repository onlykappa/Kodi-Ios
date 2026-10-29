# Kodi-iOS master roadmap

Status: READY FOR REVIEW. Current phase: PRE-IMPLEMENTATION REVIEW GATE. Implementation phases have NOT STARTED.
Progress: 2/32 task IDs COMPLETE (6.25%); 30 awaiting implementation. Historical evidence reviews only; no phase is complete.

## Rules and session protocol

Only task IDs count toward progress; numbered subtasks do not. States: NOT STARTED, IN PROGRESS, BLOCKED, READY FOR REVIEW, COMPLETE. A checked task requires deliverable, passing validation, recorded evidence, updated docs and no unmet acceptance blocker. Device tasks require actual iPhone evidence. Never erase failures.
All future tasks require owner approval of this roadmap first. Then use Inspect → Plan → Implement → Test → Diagnose → Fix → Retest → Document → Commit → Update Roadmap. Log failures in docs/ISSUES.md with root cause, smallest fix, retest and regression protection. Mark unresolved tasks BLOCKED.
Resume: read ROADMAP.md, docs/PROGRESS.md, docs/ISSUES.md and docs/DECISIONS.md; inspect branch/worktree, latest commits and PR #1; verify prerequisites and select the next unfinished unblocked task. At session end update tasks, evidence, blockers, next action, commit and push permitted files, and summarize. Do not infer completion from chat.
Only feature/ios-migration; preserve history and baseline; never merge/release without explicit approval. Source installation and SSD are read-only; all experiments use isolated project/target staging. Private backup archives, keys, tokens and media stay outside GitHub.

## Phase 1 — Security, Backup & Baseline Validation

Exit criteria: All baseline checks pass; recovery procedures are tested/documented and sensitive data protected.
Phase status: NOT STARTED. All task acceptance criteria and dependency gates must pass before exit.

- [x] P1-001 — Review historical backup evidence
  - Status: COMPLETE. Dependencies: owner roadmap approval (historical evidence review exempt).
  - 1. Deliverable and acceptance: Review full and account-state verification reports and record scope and restore-test limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/backup-verification.json; reports/account-state-verification.json.
- [ ] P1-002 — Verify current backup integrity and missing data
  - Status: NOT STARTED. Dependencies: P1-001.
  - 1. Deliverable and acceptance: Recheck both archives and coverage read-only; identify external media, runtime, keychain and missing configuration boundaries.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P1-003 — Audit publication and credentials
  - Status: NOT STARTED. Dependencies: P1-002.
  - 1. Deliverable and acceptance: Scan all published files and reachable Git history, check private archives remain outside Git and record scanner limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P1-004 — Verify source immutability
  - Status: NOT STARTED. Dependencies: P1-003.
  - 1. Deliverable and acceptance: Compare original source file hashes and metadata with private manifest; never modify source or SSD media.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P1-005 — Validate baseline and regression checks
  - Status: NOT STARTED. Dependencies: P1-004.
  - 1. Deliverable and acceptance: Verify snapshot hashes, references and negative security cases with recorded command results.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P1-006 — Rehearse recovery and rollback
  - Status: NOT STARTED. Dependencies: P1-005.
  - 1. Deliverable and acceptance: Document and test extraction into isolated storage, verify restored contents and metadata; never restore over the working Deck.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

## Phase 2 — Kodi Configuration & iOS Compatibility

Exit criteria: Target configuration passes static checks; all unresolved limitations documented; runtime remains unverified until device testing.
Phase status: NOT STARTED. All task acceptance criteria and dependency gates must pass before exit.

- [x] P2-001 — Review existing inventory evidence
  - Status: COMPLETE. Dependencies: historical evidence review only; subsequent implementation depends on P1-006.
  - 1. Deliverable and acceptance: Review all 79 user and 161 bundled manifest records and carry forward incomplete manifests without claiming compatibility.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: inventory/addons.json; docs/compatibility.md.
- [ ] P2-002 — Establish target constraints early
  - Status: NOT STARTED. Dependencies: P2-001.
  - 1. Deliverable and acceptance: Obtain model, iOS, jailbreak status and signing access before platform-specific design; record owner-approved constraints.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-003 — Classify dependency graph
  - Status: NOT STARTED. Dependencies: P2-002.
  - 1. Deliverable and acceptance: Classify every relevant component compatible, incompatible or unverified with current upstream evidence, versions and replacement decisions.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-004 — Resolve broken components
  - Status: NOT STARTED. Dependencies: P2-003.
  - 1. Deliverable and acceptance: Resolve or omit JetExtractors/The Loop; remove Umbrella references only in a separate future target configuration.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-005 — Preserve Arctic Fuse experience
  - Status: NOT STARTED. Dependencies: P2-004.
  - 1. Deliverable and acceptance: Map every retained menu, widget, layout, resource and player to its target equivalent; record owner-approved omissions.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-006 — Adapt paths and touch controls
  - Status: NOT STARTED. Dependencies: P2-005.
  - 1. Deliverable and acceptance: Replace placeholders and Linux actions in target files; produce touch navigation test cases without editing source.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-007 — Replace native functionality
  - Status: NOT STARTED. Dependencies: P2-006.
  - 1. Deliverable and acceptance: Investigate Elementum, Deck Keeper, delete actions, InputStream and DRM dependencies; document alternatives and unsupported features.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-008 — Preserve private account state
  - Status: NOT STARTED. Dependencies: P2-007.
  - 1. Deliverable and acceptance: Define per-add-on private restoration mappings and version compatibility; never publish account values; flag session expiry/device binding.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P2-009 — Build sanitized target configuration
  - Status: NOT STARTED. Dependencies: P2-008.
  - 1. Deliverable and acceptance: Produce reproducible target configuration with manifest, provenance and static missing-file/dependency/reference checks; runtime status remains unverified.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

## Phase 3 — Google Drive Media Integration

Exit criteria: Selected integration is implemented and passes available tests; live playback pending until actual iPhone testing.
Phase status: NOT STARTED. All task acceptance criteria and dependency gates must pass before exit.

- [ ] P3-001 — Research maintained integrations
  - Status: NOT STARTED. Dependencies: P2-009.
  - 1. Deliverable and acceptance: Compare direct Kodi add-ons and privately hosted bridges using dated upstream maintenance and actual iOS support evidence.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P3-002 — Select architecture with owner
  - Status: NOT STARTED. Dependencies: P3-001.
  - 1. Deliverable and acceptance: Record authentication, hosting, cost, privacy, quotas and iOS compatibility tradeoffs; obtain owner choice before external infrastructure.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P3-003 — Design private OAuth lifecycle
  - Status: NOT STARTED. Dependencies: P3-002.
  - 1. Deliverable and acceptance: Specify least privilege, local token storage, refresh, revocation and recovery; keep credentials, folder links and media out of Git.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P3-004 — Implement Drive integration
  - Status: NOT STARTED. Dependencies: P3-003.
  - 1. Deliverable and acceptance: Implement selected configuration and reproducible setup without media uploads or credentials in repository.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P3-005 — Test available integration behavior
  - Status: NOT STARTED. Dependencies: P3-004.
  - 1. Deliverable and acceptance: Run feasible mocked/host tests for startup, range seeking, subtitles, resume, refresh and failure recovery; explicitly defer live iPhone claims.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P3-006 — Document operational recovery
  - Status: NOT STARTED. Dependencies: P3-005.
  - 1. Deliverable and acceptance: Record test evidence, token renewal, quota errors, offline/network failures and live-device test plan.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

## Phase 4 — iPhone Deployment & Migration

Exit criteria: Kodi launches on target iPhone, supported configuration works and required device tests pass.
Phase status: NOT STARTED. All task acceptance criteria and dependency gates must pass before exit.

- [ ] P4-001 — Confirm device and install method
  - Status: NOT STARTED. Dependencies: P2-002; P3-006 (target facts must already inform Phase 2).
  - 1. Deliverable and acceptance: Reconfirm model/iOS/jailbreak, supported Kodi build, IPA provenance, signing tools/access, renewal and trust requirements using current primary sources.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P4-002 — Prepare safe deployment and rollback
  - Status: NOT STARTED. Dependencies: P4-001.
  - 1. Deliverable and acceptance: Prepare reproducible package/checksums and clean target backup; document removal/reinstall/rollback without touching source Deck.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P4-003 — Install Kodi and dependencies
  - Status: NOT STARTED. Dependencies: P4-002.
  - 1. Deliverable and acceptance: Install verified iOS application and compatible dependency versions on actual iPhone; record signing/renewal behavior.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P4-004 — Restore target and private account state
  - Status: NOT STARTED. Dependencies: P4-003.
  - 1. Deliverable and acceptance: Apply reviewed target config and selectively transfer compatible account state privately; test recognition before requesting login; exclude Umbrella.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P4-005 — Test real-device user experience
  - Status: NOT STARTED. Dependencies: P4-004.
  - 1. Deliverable and acceptance: On actual iPhone test launch, Arctic Fuse menus/widgets, touch, add-ons, codecs, subtitles, seeking, resume, foreground/background and Drive playback/refresh.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P4-006 — Resolve device failures and validate rollback
  - Status: NOT STARTED. Dependencies: P4-005.
  - 1. Deliverable and acceptance: Log failures, root causes, fixes and retests; test safe target recovery and reproducible installation on device.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

## Phase 5 — Final Validation, Regression & Release

Exit criteria: Required tests pass, remaining limitations explicitly accepted and owner approves release.
Phase status: NOT STARTED. All task acceptance criteria and dependency gates must pass before exit.

- [ ] P5-001 — Run complete regression matrix
  - Status: NOT STARTED. Dependencies: P4-006.
  - 1. Deliverable and acceptance: Run static and device regressions across configuration, menus/widgets/skins/add-ons and Drive playback/auth recovery with evidence.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P5-002 — Audit security and source preservation
  - Status: NOT STARTED. Dependencies: P5-001.
  - 1. Deliverable and acceptance: Audit package, Git and reachable history; verify credentials/media exclusions and unchanged original source with private hashes.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P5-003 — Validate installation and recovery guide
  - Status: NOT STARTED. Dependencies: P5-002.
  - 1. Deliverable and acceptance: Reproduce installation, private account transfer, renewal and rollback on target; record results and exact versions.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P5-004 — Finalize package and limitations
  - Status: NOT STARTED. Dependencies: P5-003.
  - 1. Deliverable and acceptance: Build final reproducible package/checksums and release checklist; document unsupported features and obtain explicit acceptance of remaining limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P5-005 — Obtain final owner review
  - Status: NOT STARTED. Dependencies: P5-004.
  - 1. Deliverable and acceptance: Present evidence and request explicit merge and release approval; neither is authorized by roadmap approval alone.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

## Roadmap quality audit

Planning audit: five phases, 32 unique IDs, explicit acceptance, dependency chains, baseline issues, security, Drive lifecycle, real-device gates, regression and rollback are represented. P2-002 gathers device facts before design; P4-001 reconfirms them. Historical reviews do not certify present archive integrity or real-device compatibility.
Independent review by the owner or a separate future reviewer is still required before implementation. See docs/PROGRESS.md for the mandatory stop gate.
