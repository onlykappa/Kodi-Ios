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

