# Kodi-iOS master roadmap

Status: BLOCKED. Current phase: Phase 4 — diagnostic launch owner-confirmed; fully bundled IPA approved; Touch-r1 startup failure recorded; Touch-r2 device evidence pending. Phase 3 approved; Phase 5 unauthorized.
Progress: 25/39 task IDs COMPLETE (64.10%); 14 awaiting implementation.

## Rules and session protocol

Only task IDs count toward progress; numbered subtasks do not. States: NOT STARTED, IN PROGRESS, BLOCKED, READY FOR REVIEW, COMPLETE. A checked task requires deliverable, passing validation, recorded evidence, updated docs and no unmet acceptance blocker. Device tasks require actual iPhone evidence. Never erase failures.
Owner approved Phases 1, 2 and 3 following their review gates and now authorizes Phase 4 only. Mandatory phase review gates remain in force. All subsequent phases require separate explicit owner authorization. Then use Inspect → Plan → Implement → Test → Diagnose → Fix → Retest → Document → Commit → Update Roadmap. Log failures in docs/ISSUES.md with root cause, smallest fix, retest and regression protection. Mark unresolved tasks BLOCKED.
Resume: read ROADMAP.md, docs/PROGRESS.md, docs/ISSUES.md and docs/DECISIONS.md; inspect branch/worktree, latest commits and PR #1; verify prerequisites and select the next unfinished unblocked task. At session end update tasks, evidence, blockers, next action, commit and push permitted files, and summarize. Do not infer completion from chat.
Only feature/ios-migration; preserve history and baseline; never merge/release without explicit approval. Source installation and SSD are read-only; all experiments use isolated project/target staging. Private backup archives, keys, tokens and media stay outside GitHub.

## Phase 1 — Security, Backup & Baseline Validation

Exit criteria: All baseline checks pass; recovery procedures are tested/documented and sensitive data protected.
Phase status: COMPLETE — owner reviewed and approved. All task acceptance criteria and dependency gates must pass before exit.

- [x] P1-001 — Review historical backup evidence
  - Status: COMPLETE. Dependencies: owner roadmap approval (historical evidence review exempt).
  - 1. Deliverable and acceptance: Review full and account-state verification reports and record scope and restore-test limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/backup-verification.json; reports/account-state-verification.json.
- [x] P1-002 — Verify current backup integrity and missing data
  - Status: COMPLETE. Dependencies: P1-001.
  - 1. Deliverable and acceptance: Recheck both archives and coverage read-only; identify external media, runtime, keychain and missing configuration boundaries.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase1-validation.json (P1-002).
- [x] P1-003 — Audit publication and credentials
  - Status: COMPLETE. Dependencies: P1-002.
  - 1. Deliverable and acceptance: Scan all published files and reachable Git history, check private archives remain outside Git and record scanner limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase1-validation.json (P1-003).
- [x] P1-004 — Verify source immutability
  - Status: COMPLETE. Dependencies: P1-003.
  - 1. Deliverable and acceptance: Compare original source file hashes and metadata with private manifest; never modify source or SSD media.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase1-validation.json (P1-004).
- [x] P1-005 — Validate baseline and regression checks
  - Status: COMPLETE. Dependencies: P1-004.
  - 1. Deliverable and acceptance: Verify snapshot hashes, references and negative security cases with recorded command results.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase1-validation.json (P1-005).
- [x] P1-006 — Rehearse recovery and rollback
  - Status: COMPLETE. Dependencies: P1-005.
  - 1. Deliverable and acceptance: Document and test extraction into isolated storage, verify restored contents and metadata; never restore over the working Deck.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase1-validation.json (P1-006).

## Phase 2 — Kodi Configuration & iOS Compatibility

Exit criteria: Target configuration passes static checks; all unresolved limitations documented; runtime remains unverified until device testing.
Phase status: COMPLETE — owner accepted static deliverables; runtime compatibility remains unverified. All task acceptance criteria and dependency gates must pass before exit.

- [x] P2-001 — Review existing inventory evidence
  - Status: COMPLETE. Dependencies: historical evidence review only; subsequent implementation depends on P1-006.
  - 1. Deliverable and acceptance: Review all 79 user and 161 bundled manifest records and carry forward incomplete manifests without claiming compatibility.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: inventory/addons.json; docs/compatibility.md.
- [x] P2-002 — Establish target constraints early
  - Status: COMPLETE. Dependencies: P2-001.
  - 1. Deliverable and acceptance: Record owner-confirmed target: iPhone 16 Pro, iOS 27.0.1, non-jailbroken, Kodi absent; unsigned ARM64 IPA. Existing sideloader is owner-managed; its identity is explicitly waived for unsigned preparation. Exact signing/runtime behavior is a Phase 4 validation requirement.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/ios-target.json; docs/ios-foundation.md.
- [x] P2-003 — Classify dependency graph
  - Status: COMPLETE. Dependencies: P2-002.
  - 1. Deliverable and acceptance: Classify every relevant component compatible, incompatible or unverified with current upstream evidence, versions and replacement decisions.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/ios-compatibility.json; reports/ios-static-validation.json.
- [x] P2-004 — Resolve broken components
  - Status: COMPLETE. Dependencies: P2-003.
  - 1. Deliverable and acceptance: Resolve or omit JetExtractors/The Loop; remove Umbrella references only in a separate future target configuration.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: migration/ios/adaptations.json; migration/ios/addon-plan.json; reports/ios-static-validation.json.
- [x] P2-005 — Preserve Arctic Fuse experience
  - Status: COMPLETE. Dependencies: P2-004.
  - 1. Deliverable and acceptance: Map every retained menu, widget, layout, resource and player to its target equivalent; record owner-approved omissions.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: migration/ios/adaptations.json; docs/ios-configuration.md; reports/ios-static-validation.json.
- [x] P2-006 — Adapt paths and touch controls
  - Status: COMPLETE. Dependencies: P2-005.
  - 1. Deliverable and acceptance: Replace placeholders and Linux actions in target files; produce touch navigation test cases without editing source.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: migration/ios/userdata/keymaps/ios-touch.xml; docs/ios-configuration.md; reports/ios-static-validation.json.
- [x] P2-007 — Replace native functionality
  - Status: COMPLETE. Dependencies: P2-006.
  - 1. Deliverable and acceptance: Investigate Elementum, Deck Keeper, delete actions, InputStream and DRM dependencies; document alternatives and unsupported features.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/ios-foundation.md; docs/ios-configuration.md; reports/ios-compatibility.json.
- [x] P2-008 — Preserve private account state
  - Status: COMPLETE. Dependencies: P2-007.
  - 1. Deliverable and acceptance: Define per-add-on private restoration mappings and version compatibility; never publish account values; flag session expiry/device binding.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/ios-configuration.md (private account-state mapping); docs/private-account-transfer.md.
- [x] P2-009 — Build sanitized target configuration
  - Status: COMPLETE. Dependencies: P2-008.
  - 1. Deliverable and acceptance: Produce reproducible sanitized target configuration with manifest, provenance and static missing-file/dependency/reference checks; document IPA-bundling versus post-install import feasibility and constraints for Phase 4. Runtime status remains unverified; IPA assembly/deployment belongs to Phase 4.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: migration/ios/manifest.json; scripts/build_ios_config.py; reports/ios-static-validation.json.

## Phase 3 — Google Drive Media Integration

Exit criteria: Selected integration is implemented and passes available tests; live playback pending until actual iPhone testing.
Phase status: COMPLETE — owner independent review passed and Phase 4 authorized; live playback remains Phase 4 evidence.

- [x] P3-001 — Research maintained integrations
  - Status: COMPLETE. Dependencies: P2-009.
  - 1. Deliverable and acceptance: Compare direct Kodi add-ons and privately hosted bridges using dated upstream maintenance and actual iOS support evidence.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/google-drive.md; reports/google-drive-research.json; migration/google-drive/source-lock.json.
- [x] P3-002 — Select architecture with owner
  - Status: COMPLETE. Dependencies: P3-001.
  - 1. Deliverable and acceptance: Record authentication, hosting, cost, privacy, quotas and iOS compatibility tradeoffs; obtain owner choice before external infrastructure.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/DECISIONS.md (DEC-011); reports/google-drive-research.json.
- [x] P3-003 — Design private OAuth lifecycle
  - Status: COMPLETE. Dependencies: P3-002.
  - 1. Deliverable and acceptance: Specify least privilege, local token storage, refresh, revocation and recovery; keep credentials, folder links and media out of Git.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/google-drive-oauth-design.md; reports/drive-upstream-validation.json (mocked OAuth checks only).
- [x] P3-004 — Implement Drive integration
  - Status: COMPLETE. Dependencies: P3-003.
  - 1. Deliverable and acceptance: Implement selected configuration and reproducible setup without media uploads or credentials in repository.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: migration/ios; reports/drive-addon-packages.json; reports/drive-integration-validation.json; reports/drive-ci-validation.json.
- [x] P3-005 — Test available integration behavior
  - Status: COMPLETE. Dependencies: P3-004.
  - 1. Deliverable and acceptance: Run feasible mocked/host tests for startup, range seeking, subtitles, resume, refresh and failure recovery; explicitly defer live iPhone claims.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/phase3-validation.json; reports/drive-ci-validation.json; reports/drive-provider-validation.json; reports/drive-runtime-mock-validation.json; ISSUE-014/016.
- [x] P3-006 — Document operational recovery
  - Status: COMPLETE. Dependencies: P3-005.
  - 1. Deliverable and acceptance: Record test evidence, token renewal, quota errors, offline/network failures and live-device test plan.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/google-drive-setup.md; docs/google-drive-oauth-design.md; reports/phase3-validation.json; docs/PROGRESS.md.

## Phase 4 — iPhone Deployment & Migration

Exit criteria: Kodi launches on target iPhone, source/skin comparison and simulator feasibility are documented, supported configuration and real-device tests pass, every required screenshot/comparison exists, and visual regressions are fixed or explicitly accepted.
Phase status: BLOCKED — host preparation exists; actual device/visual exit criteria not met. All task acceptance criteria and dependency gates must pass before exit.

- [x] P4-001 — Confirm device and install method
  - Status: COMPLETE. Dependencies: P2-002; P3-006 (target facts must already inform Phase 2).
  - 1. Deliverable and acceptance: Reconfirm iPhone 16 Pro / iOS 27.0.1 / non-jailbroken / Kodi initially absent / unsigned ARM64 IPA. Verify candidate Kodi 21.3 official foundation, owner-managed sideloader, provenance, signing entitlements, renewal/trust and actual device behavior using current evidence; none is certified by Phase 2 static tests.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: reports/owner-device-evidence.json (owner-reported actual diagnostic installation/launch on iPhone 16 Pro/iOS 27.0.1); reports/ios-foundation-inspection.json; reports/ios-foundation-entitlements.json; reports/ipa-reproducibility.json. Scope: diagnostic foundation only; customized skin, playback, touch, screenshots and rollback remain unverified.
- [ ] P4-002 — Prepare safe deployment and rollback
  - Status: BLOCKED. Dependencies: P4-008.
  - 1. Deliverable and acceptance: Prepare a reproducible unsigned Kodi iOS IPA from a trusted compatible foundation, with provenance/checksums and clean target backup. Determine which sanitized Fuse configuration/add-ons can be bundled versus imported after install; exclude credentials, account state and media. Validate ZIP/Payload/application layout, Info.plist, executable architecture, minimum iOS, load dependencies, entitlements/signature state and integrity; document rollback without touching source Deck.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: scripts/build_unsigned_ipa.py; reports/unsigned-ipa-candidate.json. Owner now requires fully bundled IPA with automatic first launch (DEC-022), superseding separate import. Foundation dependency audit and host recovery tests prepared. Fixed public-source artifact passed CI (reports/phase4-import-artifact.json); manual phone export/import is superseded by bundled IPA (DEC-022). Automatic private recovery journal creation and real first launch remain device prerequisites. Host build evidence: reports/customized-ipa-artifact.json. Native Elementum deferred; no replacement primary.
- [ ] P4-003 — Install Kodi and dependencies
  - Status: BLOCKED. Dependencies: P4-002.
  - 1. Deliverable and acceptance: Sign the unsigned IPA using the owner's existing sideloader and install on the actual iPhone; verify required entitlements, signing/renewal limits and compatible add-on versions. No working-IPA claim before successful real-device tests.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.
- [ ] P4-004 — Restore target and private account state
  - Status: BLOCKED. Dependencies: P4-003.
  - 1. Deliverable and acceptance: Apply reviewed target config and selectively transfer compatible account state privately; test recognition before requesting login; exclude Umbrella.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.
- [ ] P4-005 — Test real-device user experience
  - Status: BLOCKED. Dependencies: P4-004; P4-009.
  - 1. Deliverable and acceptance: On the actual non-jailbroken iPhone 16 Pro running iOS 27.0.1, test launch, Arctic Fuse menus/widgets, touch, add-ons, codecs, subtitles, seeking, resume, foreground/background and Drive playback/refresh. Record actual OS/build/signing versions; simulator results never substitute for these real-device tests.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.
- [ ] P4-006 — Resolve device failures and validate rollback
  - Status: BLOCKED. Dependencies: P4-011.
  - 1. Deliverable and acceptance: Log failures, root causes, fixes and retests; test safe target recovery and reproducible installation on device.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.

- [x] P4-007 — Compare real Kodi and Arctic Fuse source code
  - Status: COMPLETE. Dependencies: P4-001.
  - 1. Deliverable and acceptance: Obtain trusted pinned Kodi 21.3 source/build provenance and matching Arctic Fuse 3 source. Compare real code/assets to verified private Steam Deck copies; record file hashes, local modifications, platform-specific startup/path/native-code differences, licenses and migration patches. Do not equate version strings or static settings mapping with code parity. Block on unavailable source/provenance; never alter original installation.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: reports/phase4-source-validation.json; reports/fuse-source-comparison.json; reports/fuse-generation-validation.json; reports/kodi-source-provenance.json; docs/phase4-source-findings.md. Source comparison complete; native port and phone rendering remain separate unfinished tasks.
- [x] P4-008 — Investigate iPhone 16 Pro simulator feasibility
  - Status: COMPLETE. Dependencies: P4-007.
  - 1. Deliverable and acceptance: Determine available Mac/Xcode/runtime access and iPhone 16 Pro simulator profiles. Verify whether an appropriate Kodi simulator-target build exists or can be built from trusted source; an ARM64 iPhoneOS IPA is not proof of simulator compatibility. Record supported/unsupported/infeasible outcome and evidence. Do not purchase hosting or tools without owner approval. A documented infeasibility finding completes the investigation, not simulator/device testing.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: reports/phase4-source-validation.json; docs/phase4-source-findings.md; tagged official Kodi iOS build guide. Investigation concludes infeasible within current authorized resources; no simulator run or profile compatibility claimed.
- [x] P4-009 — Inventory every major screen and visual fixture
  - Status: COMPLETE. Dependencies: P4-008.
  - 1. Deliverable and acceptance: Create a route-by-route capture roster covering startup, every main menu/submenu, every retained widget category, media lists/details/search, add-ons, relevant settings pages, dialogs, authentication error states and playback/OSD/seek/subtitle/resume interfaces. Include portrait/landscape and loading/empty/error states where applicable. Use matching synthetic nonpersonal fixtures; define baseline/target pairing, tolerances and justified differences in docs/visual-validation-plan.md. Do not silently drop unrenderable screens.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: reports/device-capture-roster.json (184 entries); docs/phase4-device-testing.md. 184 requirements preserved across the owner-approved YouTube exclusion and menu slot movement; four capture-ledger regressions pass. Checklist completion only: zero screenshots captured and all device evidence remains pending.
- [ ] P4-010 — Capture baseline and real iPhone screenshots
  - Status: BLOCKED. Dependencies: P4-005; P4-009.
  - 1. Deliverable and acceptance: Capture every roster entry on a safe isolated Steam Deck configuration copy and the actual iPhone 16 Pro/iOS 27.0.1. Original Kodi installation/SSD remain untouched, including avoiding source startup writes. Record app/skin/code hashes, route, fixture, orientation, resolution and timestamp. Keep raw captures private; sanitize account data/media before any sharing. Missing screenshots block completion; simulator captures must be labeled and cannot replace actual-device images.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.
- [ ] P4-011 — Compare screenshots side by side and fix visual regressions
  - Status: BLOCKED. Dependencies: P4-010.
  - 1. Deliverable and acceptance: Produce paired baseline/iPhone screenshot comparisons for every roster entry. Track issue ID, severity, expected aspect-ratio differences, missing controls/widgets, clipped text, color/layout deviations and touch accessibility. Preserve failed captures/diffs, make minimal target-only fixes, recapture and retest affected routes plus regression neighbors; obtain owner decisions for intentional differences. Private images stay outside Git; publish only reviewed sanitized metadata.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: docs/phase4-device-testing.md; reports/device-capture-roster.json. AWAITING DEVICE TESTING: owner supplies actual-device results/screenshots; upstream dependencies not complete.

## Phase 5 — Final Validation, Regression & Release

Exit criteria: Required functional and visual regression tests pass, all screenshot comparisons receive explicit final owner approval, remaining limitations are accepted and owner approves release.
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
  - Status: NOT STARTED. Dependencies: P5-003; P5-006.
  - 1. Deliverable and acceptance: Build final reproducible package/checksums and release checklist; document unsupported features and obtain explicit acceptance of remaining limitations.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.
- [ ] P5-005 — Obtain final owner review
  - Status: NOT STARTED. Dependencies: P5-007.
  - 1. Deliverable and acceptance: Present evidence and request explicit merge and release approval; neither is authorized by roadmap approval alone.
  - 2. Validation: record command/device procedure, expected and observed result, artifact/commit and date; diagnose any failure before completion.
  - Evidence: pending.

- [ ] P5-006 — Run complete visual regression matrix
  - Status: NOT STARTED. Dependencies: P5-001.
  - 1. Deliverable and acceptance: Repeat the full approved screenshot roster and side-by-side comparisons against the accepted safe-copy baseline after final fixes. Record before/after artifacts and failing/passing tests; close each visual issue only with retest evidence. Recheck source immutability and private screenshot handling. No unrecorded omissions or simulator-only substitutions.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: pending.
- [ ] P5-007 — Obtain final owner screenshot review
  - Status: NOT STARTED. Dependencies: P5-004.
  - 1. Deliverable and acceptance: Present every major screen/menu/widget/settings/playback comparison through a private or explicitly approved sanitized review channel. Record owner acceptance of screenshots and intentional differences, unresolved rejection items and re-review evidence. Explicit screenshot approval is mandatory before final release approval; absence of a response is not approval.
  - 2. Validation: record exact versions, procedures, observed results, artifact hashes and review evidence; never mark complete with missing evidence.
  - Evidence: pending.

## Roadmap quality audit

Planning audit: five phases, dynamic unique task IDs, explicit acceptance, dependency chains, baseline issues, security, Drive lifecycle, real-device gates, regression and rollback are represented. P2-002 gathers device facts before design; P4-001 reconfirms them. Historical reviews do not certify present archive integrity or real-device compatibility.
Independent reviews passed through Phase 2 static deliverables; owner authorized Phase 3 only. See docs/PROGRESS.md for the mandatory stop gate.

## Mandatory phase review gates

REVIEW-GATE-1: After Phase 1, update roadmap, PROGRESS, ISSUES, validation evidence and PR #1; commit and publish validated work, then STOP and request owner review. Do not begin the next phase without explicit authorization.

REVIEW-GATE-2: After Phase 2, update roadmap, PROGRESS, ISSUES, validation evidence and PR #1; commit and publish validated work, then STOP and request owner review. Do not begin the next phase without explicit authorization.

REVIEW-GATE-3: After Phase 3, update roadmap, PROGRESS, ISSUES, validation evidence and PR #1; commit and publish validated work, then STOP and request owner review. Do not begin the next phase without explicit authorization.

REVIEW-GATE-4: After Phase 4, update roadmap, PROGRESS, ISSUES, validation evidence and PR #1; commit and publish validated work, then STOP and request owner review. Do not begin the next phase without explicit authorization.

REVIEW-GATE-5: After Phase 5, update roadmap, PROGRESS, ISSUES, validation evidence and PR #1; commit and publish validated work, then STOP and request owner review. Do not merge or release without explicit owner authorization.


Phase 2 completion means static deliverables, not certified iPhone functionality. Exact skin-code parity, native binary availability, touch behavior and OS/runtime compatibility remain explicit Phase 4 validation risks. That tradeoff was open during Phase 2. Owner now requires the fully bundled IPA (DEC-022); the automatic bootstrap and IPA are implemented and host-validated in Phase 4. Actual device startup/compatibility remains unverified.
