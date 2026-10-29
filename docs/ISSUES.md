# Issue register

No existing failure is erased; preserve failed attempts and append evidence on resolution.

## ISSUE-001

Severity: HIGH. Component: JetExtractors/The Loop.
Reproduction: Read inventory/addons.json: required manifest empty.
Root cause: Zero-byte manifest.
Proposed fix: Resolve or omit in target.
Fix status: NOT STARTED; linked task P2-004.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P2-004 before closing.

## ISSUE-002

Severity: MEDIUM. Component: Umbrella references.
Reproduction: Read reports/references.json and player definitions.
Root cause: Historical baseline retains excluded integration.
Proposed fix: Remove only from future iOS target.
Fix status: NOT STARTED; linked task P2-004.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P2-004 before closing.

## ISSUE-003

Severity: HIGH. Component: Native dependencies.
Reproduction: Review docs/compatibility.md.
Root cause: Desktop executables and subprocess assumptions.
Proposed fix: Research iOS alternatives.
Fix status: NOT STARTED; linked task P2-007.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P2-007 before closing.

## ISSUE-004

Severity: HIGH. Component: Device and signing.
Reproduction: No device facts or device test evidence recorded.
Root cause: Target unknown.
Proposed fix: Obtain owner facts and verify install method.
Fix status: NOT STARTED; linked task P2-002.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P2-002 before closing.

## ISSUE-005

Severity: MEDIUM. Component: Recovery coverage.
Reproduction: Review docs/inspection.md.
Root cause: Archive verified historically; no isolated restore/metadata rehearsal.
Proposed fix: Test isolated restoration; document external exclusions.
Fix status: NOT STARTED; linked task P1-006.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P1-006 before closing.

## ISSUE-006

Severity: HIGH. Component: Saved account reuse.
Reproduction: Review private account transfer limitations.
Root cause: Expired/device-bound sessions and external keychains may prevent reuse.
Proposed fix: Test selective private state reuse; do not promise universal login preservation.
Fix status: NOT STARTED; linked task P4-004.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P4-004 before closing.

## ISSUE-007

Severity: MEDIUM. Component: Scanner coverage.
Reproduction: Read docs/sanitization.md.
Root cause: Custom scanner, no external engine; patterns cannot prove absence.
Proposed fix: Review coverage and document residual risks.
Fix status: NOT STARTED; linked task P1-003.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P1-003 before closing.

## ISSUE-008

Severity: MEDIUM. Component: Target paths and Drive.
Reproduction: Read source placeholders and docs/google-drive.md.
Root cause: Target configuration and Drive implementation absent.
Proposed fix: Adapt paths and select evidenced Drive integration.
Fix status: NOT STARTED; linked task P3-001.
Verification evidence: historical baseline documents cited above; fix not verified.
Regression prevention: add targeted checks/retest evidence under P3-001 before closing.


## ISSUE-009 — Roadmap counts hardcoded

Severity: HIGH. Component: planning validator. Reproduction: add a task or complete P1-002 in the former validator; hardcoded total/completion IDs reject valid updates. Root cause: fixture constants used as live validation. Fix status: COMPLETE. Fix: derive totals, percentages and completion from task IDs and checked/status pairs; verify tracker consistency and phase gates. Evidence: scripts/test_roadmap.py (four tests), reports/roadmap-validation.json. Regression prevention: status-change, added-task, inconsistent-status and stale-tracker tests.

Failed attempt retained: initial dynamic parser used a greedy title expression under DOTALL and falsely rejected valid statuses. Root cause: title consumed task body. Fixed to a single-line title; all four regression tests pass.

## ISSUE-010 — Recovery verifier metadata filename

Severity: LOW. Component: local verification harness. Reproduction: first invocation requested backup-verification.json in private archive folder. Root cause: published report name differs from private verification.json. Fix status: COMPLETE; corrected lookup and reran both archive checks successfully (reports/phase1-validation.json). Regression prevention: checksum lookup is explicit in the documented procedure. No archive or source data changed.

ISSUE-005 update: COMPLETE for isolated recovery. All 22,463 files restored and matched; modes, ownership, mtime and symlink checks pass. Source has zero extended attributes/ACL xattrs, confirmed equal in recovery. Nonempty ACL/xattr restoration is not exercised by this source. Evidence: reports/phase1-validation.json and scripts/verify_recovery.py.
ISSUE-007 update: current audit passed; custom scanner limitations remain documented as residual risk, not proof of universal secret absence. No external engine was installed.

ISSUE-004 update: BLOCKED at P2-002. Repository search found no supplied model, exact iOS, jailbreak status, existing Kodi installation or signing access. Requested owner facts; do not infer platform support or bypass dependencies. Verification: read docs/DECISIONS.md and PROGRESS.md; no target-specific configuration created. Resume after owner response and current upstream verification.

ISSUE-004 clarification: owner has an IPA signing/installing sideloader, so acquiring a signing method is no longer the blocker. Exact phone/iOS/jailbreak facts and sideloader identity/version remain required. P2-002 stays BLOCKED pending those facts; no unsupported compatibility assumptions.

## Phase 2 issue updates

ISSUE-004: COMPLETE for target-constraint discovery only. iPhone 16 Pro / iOS 27.0.1 / non-jailbroken / Kodi absent; owner-managed IPA sideloader identity waived by owner. Actual signing/OS behavior unverified (Phase 4).
ISSUE-001: DEFERRED with owner approval for the future target; not repaired upstream. The Loop/JetExtractors remain in baseline/private backup; absent from active target dependency closure.
ISSUE-002: COMPLETE for active target removal. Umbrella definitions/preferences removed only from generated userdata. Exclusion metadata and immutable baseline remain. Regression: excluded-backend negative test.
ISSUE-003: existing native payloads are excluded from target; alternative local-library browsing is explicit, remote Elementum/server mode is not implemented. iOS PIL/InputStream availability remains UNVERIFIED.
ISSUE-008: target paths converted to portable declared empty profile media folders; media access and Drive integration remain Phase 3/4 tasks. No source SSD access or modification.

## ISSUE-011 — Sanitized setting identifier is not loadable

Severity: MEDIUM. Component: target generator. Reproduction: initial target static check rejected REDACTED_OPAQUE_VALUE in skin preference identifier. Root cause: conservative baseline sanitization redacted an opaque identifier; blindly copying it cannot reconstruct a valid preference. Fix status: COMPLETE for safe target generation. Omit unknown/redacted setting from target only and record the adaptation; preserve original privately. Validation: target path/reference checks and six iOS regression tests pass after rebuild. Regression prevention: checker rejects every unresolved redaction and reproducibility test rebuilds from baseline. UI effect of omitted preference remains unverified.

## ISSUE-012 — Fuse touch and local skin-code parity

Severity: HIGH. Component: user experience. Reproduction/evidence: upstream touchscreen feature request dated October 2026; no actual iPhone tests performed. Root cause: full control-level touch behavior and differences between customized installed skin code and an upstream skin are unverified. Fix status: UNRESOLVED device-validation risk. Proposed fix: verify all retained slots/custom windows against installed target code, adapt controls if needed and test gestures on iPhone before claiming parity. Static gesture mapping exists but is not a proven control-layout fix. Regression prevention: Phase 4 per-control navigation tests; no switch to another skin or silent feature loss.

## ISSUE-013 — Exact OS and IPA initialization remain unverified

Severity: HIGH. Component: deployment. Evidence: official release is ARM64 21.3 DEB; exact iOS 27.0.1 support not confirmed in consulted primary sources. Profile/data paths are separate from application resources. Fix status: UNRESOLVED until Phase 4 binary/entitlement/signing/install tests. Preferred separate sanitized import needs owner review against the fully preconfigured IPA objective. No first-run bootstrap is implemented. Regression prevention: prohibit runtime-ready claims from static results.

Retrieval failures retained: guessed raw Kodi source URLs returned cache misses; tagged contents API succeeded. GitHub connector rejected tag/discussion listing endpoints; this limited source-parity investigation. No version support inferred from failed requests.
