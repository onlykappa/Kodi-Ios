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

## Owner decision 2026-11-01 — version 1 on main

The owner authorized merging the iOS work into `main` after the r13 review build (build-111) as version 1 (DEC-024). Task IDs and their states above are unchanged: device tasks still need the owner's evidence. The roadmap is to be reworked from version 1 at the owner's request.

## Roku Drive test delivery — 2026-11-09

Owner authorized a new test build. Existing r41 candidate delivered as build 213 from PR #16's feature branch;
main was not merged. Packaging and downloaded-IPA verification passed; see docs/PROGRESS.md and
reports/roku-drive-test-delivery.json. P4-005/P4-006 and task counts are unchanged: actual Drive/Roku startup,
sustained 4K playback and seeking still require owner evidence. The cold prepared-file cache limitation stays open.


## Build-213 Roku failure and repair — 2026-11-09

The owner reports both routes still fail and authorizes repairs and a new test IPA. ISSUE-139 tracks startup lane
waits, shared Drive reads, subtitle deadlines, false success/slow-internet diagnoses and resume ownership. Candidate
validation and delivery continue on PR #16, retaining the Drive workflow. Existing device task states and counts
remain unchanged; actual Roku playback is still an acceptance gate. See docs/PROGRESS.md and docs/ROKU-STREAMING.md.


## Roku repair r42 candidate verified — 2026-11-09

Owner-authorized repair source 0385902 passed native run 42639212562: 3,231 host checks, E2E conversion/resume and
an iPhoneOS framework compile. The r42 framework pin and IPA-CI casting coverage are prepared on PR #16. Test IPA
publication and artifact verification follow; device task states and counts remain unchanged. See PROGRESS and
reports/roku-streaming-repair-native.json for evidence and remaining device checks.


## Roku repair test build 214 delivered — 2026-11-09

The owner-authorized r42 repair is delivered on PR #16 as build 214. Native CI 42639212562 and IPA CI 42641842437
passed, and the downloaded archive/framework/Python code/ARM64 binaries were verified. Receipt:
reports/roku-drive-test-delivery-r42.json. Retained-4K Media Assistant and native AirPlay still need the owner's
actual device tests; task counts and pending device states remain unchanged. Main is unchanged.


## Build 214 owner retest and follow-up — 2026-11-09

The owner reports Media Assistant/captions still fail. ISSUE-140 and reports/roku-build214-retest.json record
reproduced packaging, partial-delivery and caption bugs, host repairs and passing focused tests. Native CI and
new IPA delivery are pending. Actual Roku acceptance remains open; task counts and main are unchanged.


## Touch seeking and download follow-up — 2026-11-09

ISSUE-141: native touch drag/seek ownership and streamed-upload progress/completion repairs implemented.
Compiled handler harness and 47 upload/download tests pass. Native delivery/device acceptance remain pending;
no phase counts or main merge changed.


2026-11-09 owner-approved recommendation follow-up: capability routing/one compatibility retry, bounded adaptive
read-ahead and obsolete-read cancellation, adaptive resumable upload chunks, existing-row transfer phases and
native seek diagnostics are implemented for the next test IPA. See ISSUE-142 and PROGRESS for validation/build
status. Device acceptance and phase counts remain unchanged; no main merge is authorized.


2026-11-09 delivery: owner-approved recommendations and repairs are pushed and included in verified test IPA 216
(run 42698801783), with AirPlay r43 and Kodi r25. Native checks/recovery, packaging and downloaded-asset validation
pass; see reports/streaming-recommendations-delivery.json and ISSUE-142. iPhone/Roku/visual acceptance remains
pending and existing phase counts are unchanged. Main was not merged.


2026-11-10 delivery: owner-approved seek-release and automatic-work repairs are included in verified test IPA 217
(run 42732787090), with Kodi r26 and retained AirPlay r43. Native gesture dispatch 32, scheduler 10, focused suites,
packaging and downloaded-asset validation pass. See ISSUE-143 and reports/seek-queue-repair-delivery.json.
Actual iPhone/Roku acceptance remains pending; existing phase counts are unchanged. Main was not merged.


Compatibility-first preparation checkpoint (2026-11-10, ISSUE-145 / DEC-031): supported inspected video keeps its
original Drive file; no background conversion/re-upload or optional ready-file repack. Umbrella remote file reads
separately reuse the Drive range-cache engine with a service-owned foreground profile. 17 focused suites / 442 tests
and unchanged native host streaming comparison pass (identical first segment, fewer upstream reads). Evidence:
reports/compatibility-filter-review.json and PROGRESS. UI text only; policy checked, device/visual acceptance pending.
No new IPA, native build or main merge. Next: authorized updated-IPA/device retest of compatible queue skip and
Umbrella AirPlay/Media Assistant separately. Existing roadmap phase/task completion counts are unchanged.


Refresh/recommendations checkpoint (2026-11-10, ISSUE-146): owner approves the three additions and file inspection
on Library status Refresh for another build/retest. Adaptive 1–8 MiB preparation HTTP uploads preserve 32 MiB
resume pieces/256 MiB window; independent transport progress reports upload waits; selected Umbrella/AllDebrid
links renew once; unknown files are inspected before readiness/conversion decisions on explicit Refresh. Exact
cached identities survive restart; active native work and transactions stay protected. 24 suites / 545 tests,
project/UI checks and real native host generated-source recovery pass. Evidence: reports/refresh-streaming-checks.json.
Next: package/verify the requested updated test IPA using unchanged verified Kodi r26/AirPlay r43, then owner tests
Refresh (ready count/no new Lanterns conversion), upload status, and Umbrella AirPlay/Media Assistant separately.
Device/visual/provider acceptance and roadmap phase/task counts remain unchanged; no main merge.

Packaging retry checkpoint (ISSUE-146): build 218 / 42755096028 failed before packaging on an obsolete AirPlay
wording assertion. Corrected, 29 routing tests and every subsequent CI test script pass locally; Python 3.11 path
supplied for bytecode tests as CI does. App sources/pins unchanged. Next: new packaging run, artifact verification
and owner delivery; 218 was never delivered. Failed attempt retained in ISSUES and checks report.

ISSUE-146 delivery (2026-11-10): test IPA 219 from 2d658de5ede446f9d8170a5c0185b1e5ee3c3efa published by
successful run 42755715794 and independently downloaded/verified (digest/ZIP, exact r26/r43, 18 sources/Python 3.11
hashes, 154 unsigned/unencrypted ARM64 images). Receipt: reports/refresh-streaming-delivery.json; download linked
at the top of PROGRESS. Source/build/delivery complete; owner retests Refresh/Ready count and Umbrella/Roku,
subtitles/seeking. Build 218's obsolete wording failure stays recorded. Device/visual/provider acceptance and
phase/task counts remain unchanged; no main merge.

ISSUE-147 investigation checkpoint (2026-11-10): owner adds seek-release, subtitles and a continuous-hour AirPlay
stop. Current five-minute build-217 capture shares r26/r43 with 219. Expanded real-slider/info-refresh reproduction
shows pending target display rollback and conditional target overwrite; every logged submission blocks 500 ms.
Selected captions repeatedly time out at the native 1.5 s budget and are returned as empty HTTP-200 WEBVTT. The
actual hour-long stop is absent, so exact stop cause is unresolved; need kodi.old.log/actual stop capture. Report:
reports/seek-subtitle-stop-review.json. Investigation only, no app fix/native build/IPA/merge or device acceptance.
Next: source repair with expanded refresh/event coverage; inspect actual stop evidence when available. Phase/task
counts remain unchanged.

ISSUE-147 old-log follow-up (2026-11-10): supplied old log exactly extends the prior 1,993 lines by 59 lines /
17.764 s of shutdown. It still covers only ~5.4 minutes, build 217, with no continuous-hour failure captured.
Shutdown begins three minutes after the captured AirPlay close. Existing seek/subtitle findings remain; hour-stop
attribution stays unresolved. Capture the next actual stop before restart. Report/progress updated; no app/native
change, build, IPA, main merge or phase/task-count change.


## Current repair checkpoint — 2026-11-10 (ISSUE-148)

Full Library status Refresh now audits actual codec and faster-open layout separately and queues only missing
preparation. Umbrella service cache registration now uses Kodi Home rather than a filesystem Path. See
reports/refresh-layout-cache-checks.json and docs/PROGRESS.md for verification/delivery. No phase/task acceptance
counts changed; device/Roku results and ISSUE-147 remain pending. Main is not merged.

Current checkpoint delivery: verified IPA 221 (source fcae63e, run 42842353113 success); see
reports/refresh-layout-cache-delivery.json. Source/host checks complete; owner iPhone/Roku acceptance pending.
Build 220 was superseded/cancelled before delivery. No main merge or phase/task completion change.

## Source checkpoint: AirPlay startup and opening episode checks — 2026-11-10

ISSUE-149 / ISSUE-150 / DEC-033: shared native startup deadline, parallel audio/video priming at resume position,
reused target init and safe source/cache/timing diagnostics implemented. Newly downloaded TV shows are followed;
existing shows can opt in through Follow new episodes only. Bounded app-opening/foreground checks use real air
dates, selected quality and actual ownership/queue deduplication through the existing Drive download path. Existing
UI controls only; policy checked. Host evidence: reports/airplay-opening-episodes-checks.json and PROGRESS.
Owner holds IPA publication. No native iPhone framework build/release, workflow dispatch, IPA, push or main merge.
Native pins stay r26/r43; next authorized IPA requires rebuilding/verifying/pinning the changed AirPlay component
first. Actual iPhone/Roku, provider/new-release and visual acceptance remain pending. ISSUE-147 remains separate;
no roadmap phase/task acceptance counts change.

## Playback retention verified; owner-approved test IPA packaging next — 2026-11-10

DEC-034 / ISSUE-147/151: seek retention (including fractional baseline), retained subtitle worker/cache, automatic
stop evidence and downloaded-movie Continue from/restart implemented. Native local 3252 checks, 1094 Python tests
and 46 real slider/gesture/info-refresh scenarios pass. Verified Kodi r28 run 42881626230, AirPlay candidate run
42883448916 host/framework/end-to-end success; new immutable pin/publication follows checks receipt. See
reports/playback-retention-checks.json and PROGRESS. Owner approves IPA and prior opening-episode/startup changes
are included. Next publish verified framework, package/independently verify IPA and deliver. No main merge;
actual iPhone/Roku/provider/visual acceptance and existing roadmap task counts stay unchanged.

Playback retention delivery checkpoint (ISSUE-147/151 / DEC-034, 2026-11-10): verified IPA 223 from f6b4098,
run 42887751497 success, Kodi r28 / AirPlay r44. Downloaded digest/ZIP/native/source/bytecode/154 unsigned ARM64
images checked. 1094 Python tests + 46 actual slider cases, native CI 3336 and local 3252 checks plus end-to-end
conversion pass. Receipt reports/playback-retention-delivery.json; source checks/failures retained separately.
Failed 222 was not delivered. Next owner device checks: saved downloaded-movie Continue/Start from beginning,
seek landing, captions and actual AirPlay/Roku; new-episode provider/visual acceptance pending. Historical hour-stop
cause remains unknown; local/exported evidence added. No main merge or roadmap phase/task-count change.

## Source work in progress: season source availability and visible paused queues — 2026-11-11 UTC

DEC-035 / ISSUE-152/153: owner holds IPA publication and requests real desktop rig tests. Genuine pack filtering,
a source-derived exact-quality episode fallback with opening retries, and durable paused/queued transfer visibility
(including Refresh and Queue pagination) are implemented with focused regressions. No native pin change or IPA
workflow dispatch. Desktop Kodi 21.3 rig is compiling in an isolated container using build-223 add-ons; visual/app
flow checks remain pending. ISSUE-154 subtitle Browse freeze is under investigation; Download subtitle/phone
captions work per owner. AirPlay captions and the Media Assistant five-second stall still need matching session
evidence. No phase/task acceptance count changes or main merge. Final validation/evidence checkpoint will follow.

Source handoff requested by owner (2026-11-11 UTC): commit completed ISSUE-152/153 repairs and ISSUE-154 native
HTTP Browse guard to PR #16 on claude/trusting-euler-kgug98; keep IPA held. Real desktop quality/queue-save and
Browse guard evidence plus passing related checks recorded in reports/season-source-queue-checks.json. Unfinished
empty-show UI excluded (ISSUE-155). Remaining TV-session evidence, final UI smoke tests and required new iOS
engine build/pin are listed in docs/REVIEW-HANDOFF-PR16.md. No main merge or phase acceptance-count changes.

## Mockup roadmap — 2026-11-12 (DEC-039, DEC-042, DEC-043)

Approved mockups still to build, in order. Planning only: no code until the owner says start. Each step ends with
host tests, the desktop Kodi rig next to its board (APPLE-UI-POLICY §7, screenshots labelled), an IPA and the owner's
iPhone log; phone behaviour is never assumed from the rig.

Library file manager (docs/design/library-files-mockups.html, round 3, DEC-043). Kodi skin XML from pages.py and the
portrait helpers; data from what the app already records.
- L1 Data model (pure Python, host-tested): one list of downloaded shows and movies from the Drive library listing,
  the phone's completed downloads, debrid_drive jobs (copying), the preparation queue (converting, ready, problem),
  upscale-copies.json (AI copies) and Continue Watching (watched); per show: seasons, episodes, sizes, state counts.
- L2 Board A, TV Shows: the TV Shows / Movies switch, the storage card (Drive used by shows, movies, AI copies; phone),
  search and sort (Recent, Name, Size), show rows with state chips. Replaces the Library tab's current downloaded-
  movies list.
- L3 Board B, one show: art, three numbers, season chips, episode rows with one state line (bars only while
  something runs); the round back, ••• and Select controls (round 3).
- L4 Board C, the episode / movie sheet: steps (on Drive, ready for Kodi and AirPlay, AI copy, subtitles), facts,
  Play, Play on TV or Pause converting, Delete. C3: a problem's cause in one line and Repair as the main action.
- L5 Repair and Find Missing Episodes: Repair looks one episode up again at the season's quality through Build
  Season's lookup (season_sources.request, purpose queue) and adds it; Find Missing Episodes runs the Build Season
  check for the season and adds only what is not there; Repair All Problems repairs each in turn. All in the •••
  menu except the per-row Repair.
- L6 Board D, select and delete: checkboxes, Select All / watched, the bottom bar with count and size, the iOS
  confirmation (Drive files to Drive's Trash for 30 days, phone copies deleted, AI copies optional, Cancel). Built on
  ios_remove (long press › Remove), extended to several items and to AI copies.
- L7 Board E, Movies: three-column poster grid with size and state badge, the same sheet (C).
- L8 Board F, Free Up Space: watched episodes, AI copies, largest movies, phone copies already on Drive; each opens
  board D with its items ticked.

Video and AI Upscale (approved DEC-039 / DEC-042, not built yet).
- V1 Picture button and menu in the video controls (docs/design/video-picture-mockups.html round 4): AI Upscale
  slider (Off, then sizes above the video) and Saturation, per video / show / every video (picture.py rules exist).
- V2 Saturation: a GLES shader change in migration/ios-portrait/kodi-21.3-portrait.patch, Kodi r32 staged, CI build,
  downloaded and verified, pinned by checksum.
- V3 Settings › AI Upscale board C (docs/design/ai-upscale-settings-mockups.html): one show's own page with its
  episodes and Remove the copies (today a size list).

Waiting on owner logs from build-314 before more AI Upscale work: the tiled upscaler test (speed, heat, battery,
size, joins) and the copy speed (three copies at once, 32 MB pieces).

### Fixes from the owner's logs (2026-11-12) — status

| Issue | What | State |
|---|---|---|
| ISSUE-179 | Build Season found every episode, queued none | Fixed; phone: 31/32 queued (build 309) |
| ISSUE-180 | AI Upscale test closed Kodi (4x model made 8K frames) | Guard in build 309; tiled 720p/1080p upscaling in AirPlay r49 (build 314), phone test pending |
| ISSUE-181 | Version menu opened mid-season; lost episode identity | Fixed in build 314; phone log pending |
| ISSUE-182 | AllDebrid → Drive one episode at a time, 8 MB pieces | Build 314: 3 at once, 7.2 MB/s (was 2.8) |
| ISSUE-183 | Build Season downloads named after the torrent hash, no metadata | Fixed after build 314 (title in the request, files moved and renamed); phone proof pending |
| ISSUE-184 | Pieces ramp slowly; per-connection limit ~2.4 MB/s | 4 lanes, 8 MB first pieces; phone proof pending |

Next owner checks on the next IPA: the hash cards become "Naruto Shippūden" with episodes and art; four copy threads;
the AI Upscale test (Settings › AI Upscale › Test on one video): speed, heat, battery, size and whether the tile joins
show.

### Open bugs, not coded yet (owner screenshots after build 314, 2026-11-12) — for the next agent

1. **Activity shows one upload while several copy.** debrid_drive.uploads() returns only state['current']; 'current_also'
   is saved but never read, and lanes 3-4 live only in the local `extra` dict (never saved). activity.current() also
   gives every upload the same key 'drive', so rows collapse into one. Fix: save every lane (e.g. state['current_more']),
   return all of them from uploads(), and key each Activity row by lane or file.
2. **Raw hashes as titles** ("Ee34425D5595F37297Bc8C94Dab…" in Activity and the upload card). The row title is
   display_title(job name), and jobs queued before ISSUE-183 are named after the info-hash. ISSUE-183's retitle()
   renames queued jobs, but every display path should also refuse a hash: use the show (folder) + episode label from
   the file name, never the hash (debrid_drive.is_hash exists).
3. **No metadata/poster anywhere for anime-style names** (Library status "Naruto Shippuuden - 002", Notifications,
   Downloaded TV Shows). drivelibrary.parse keeps " - 002" and "Episode 006 …" in the title and finds no episode, so the
   poster lookup (activity.Posters, transfer_artwork) and the Library grouping miss. Fix: parse absolute-numbered names
   ("Show - 002", "Show Episode 006 Title", "Show 002 [1080p]") into title + episode, with tests; ISSUE-183's
   episode_name() covers new copies only.
4. Check after the fix: Library status "Working on now", Notifications "Running now" and Activity show the show's
   poster and "Naruto Shippūden · S1 E2" for every lane.
