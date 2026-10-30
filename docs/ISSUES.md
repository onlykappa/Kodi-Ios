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

## ISSUE-014 — Host streaming tests denied local sockets

Severity: HIGH. Component: Phase 3 upstream test executor. Fix status: BLOCKED. Reproduction: from the private pinned common-module cache, run `python3 -B -m unittest discover -s tests -v`; 42 tests run, 34 pass, eight stream tests error creating AF_INET sockets with PermissionError/EPERM. Root cause: executor socket restriction, before assertions; not a verified add-on defect. Proposed fix: run unchanged hash-verified suite in an authorized environment allowing loopback sockets. No sandbox bypass or source patch attempted. Evidence: reports/drive-upstream-validation.json. Regression prevention: retain all eight tests and full failure history; successful host results and real-device tests remain separate prerequisites. P3-004 is BLOCKED; P3-005/P3-006 incomplete.

## ISSUE-015 — Text-only connector cannot fetch binary add-on assets

Severity: MEDIUM. Component: upstream acquisition/package completeness. Status: OPEN. Reproduction: fetching a pinned icon blob through GitHub connector returns HTTP 400, UTF-8 text only. Root cause: tool capability limitation. All 97 file identities are recorded; 74 text files were fetched/hash-verified. No missing asset is replaced with invented bytes and no complete distributable ZIP is claimed. Proposed fix: use a permitted binary-capable acquisition path during package preparation and verify pinned hashes before claiming a complete package. Regression prevention: keep download-completeness distinct from source-lock metadata and host tests.

Research retrieval failures retained: guessed Kodi WebDAV wiki URLs were inaccessible. Bridge compatibility is reported as unverified; rclone protocol documentation is not treated as proof of exact iOS behavior. The selected add-on is not classified abandoned based on the stale Kodi catalogue; pinned upstream October 2026 updates are recorded separately.

ISSUE-015 update: COMPLETE for acquisition capability. The generic fetch rejected binary data, but the dedicated file-fetch tool supports explicit base64. Used that supported capability to fetch the remaining 23 files; all 97 pinned upstream files match hashes and sizes. Evidence: reports/drive-source-acquisition.json. First failed attempt retained above. No distributable ZIP or installed/runtime-ready add-on is implied.

ISSUE-014 update: RESOLVED for Phase 3 required host tests by the owner-approved capped Actions job. Run 40940315803 passed all 42 tests at the original source pin, including all eight previously blocked cases. The local socket restriction and failed report remain historical facts; no test was skipped or source changed. Evidence: reports/drive-ci-validation.json and linked job logs.

## ISSUE-016 — Nonfatal upstream cleanup warnings

Severity: MEDIUM (runtime impact unverified). Component: upstream test harness/lifecycle. Status: OPEN, non-blocking to the passing Phase 3 host suite. Evidence: successful CI logs include ResourceWarning for an unclosed stale-connection socket and ignored Source destructor AttributeError from a partially initialized mocked fixture. Tests exit successfully; warnings are retained, not called fixed. Proposed follow-up: inspect lifecycle/resource behavior during real-source comparison and repeated playback/seek/exit on iPhone in Phase 4; fix/retest minimal target or upstream code if reproduced. No upstream source patch or warning suppression was introduced.

Phase 3 closure update: ISSUE-008 is COMPLETE for portable static paths and credential-free Drive configuration only (reports/drive-integration-validation.json); actual media access remains Phase 4. ISSUE-015 also has two complete reproducible upstream-only ZIPs verified outside Git (reports/drive-addon-packages.json). ISSUE-001 remains owner-deferred; ISSUE-003 native availability and ISSUE-012/013 runtime/deployment risks remain unresolved. ISSUE-016 remains open; no warning suppression or unsupported runtime claim. See reports/phase3-validation.json for regression evidence.

## ISSUE-017 — Publication transport truncation

Severity: LOW. Component: local-to-connector content transport. Status: COMPLETE. Reproduction: reading the entire 178,684-character publication JSON through one shell result yielded truncated text and JSON parsing failed before a GitHub mutation. Root cause: shell tool output cap. Fix: transfer bounded 12,000-character chunks, reconstruct and parse the entire payload, then require remote-created tree equality with the local commit tree before updating the branch using an expected-SHA lease. Verification: published integration commit d6ba8c508a9f5981a2ef85bd19f56a045dc9aee2 has tree d53e676a29e47ae1a24fa3c962106816f432befe, equal to local 4a3f04a. Regression prevention: use bounded transport and exact tree comparison for subsequent publications; no force push or history rewrite.

## ISSUE-018 — Local official binary acquisition unavailable

Severity: HIGH. Component: Phase 4 foundation acquisition. Status: IN PROGRESS. Reproduction: HTTPS curl HEAD to the official 21.3 ARM64 DEB exits 6, could not resolve mirrors.kodi.tv. Root cause: local executor DNS/network unavailable. Fix attempted: capped GitHub Actions HTTPS acquisition and static inspection, no sandbox changes. Validation pending actual run. No binary download, checksum or IPA success claimed. Regression prevention: record run outcome and real bytes before completing acquisition.

## ISSUE-019 — Phase 4 prerequisite includes future device behavior

Severity: MEDIUM. Component: roadmap sequencing. Status: OPEN. P4-001 requires actual device behavior before P4-007/008/002 preparation can complete, while installation and runtime proof are explicitly P4-003/005. Owner now assigns device testing to themselves when ready. Preserve the runtime requirement; record host prerequisites separately and do not silently mark P4-001 complete. Dependency/scope reconciliation must be explicit before advancing beyond this prerequisite.

Phase 4 source lookup attempts retained: skin tags collection was rejected by the GitHub connector; exact tag 3.4.8 returned 404. Kodi 21.3-Omega resolves to a3a448d26b8d560a65655dab2cd122994dc4e146. Neither a version label nor a failed tag lookup establishes installed skin/code parity.

ISSUE-018 update: acquisition RESOLVED via run 40951457120 (official HTTPS DEB, static ARM64 inspection). Local DNS remains unavailable. Diagnostic unsigned candidate built successfully in run 40952213893; it does not resolve migration completeness or iOS runtime compatibility. New parser tests cover malformed commands, encryption/platform distinction and signature bounds; unsigned ZIP tests preserve payload, executable mode and symlinks.

## ISSUE-020 — Real generated Fuse source differs from upstream

Severity: HIGH for unverified visual parity. Component: Arctic Fuse 3 view generation. Status: OPEN. Reproduction: compare pinned v3.4.8 tree with isolated verified recovery using scripts/compare_skin_source.py. Evidence: 3,336 exact matches, one changed generated view include and one extra generated skinvariables include (reports/fuse-source-comparison.json). Root cause: installed generated state versus upstream rebuild templates; exact device effect not tested. Proposed fix: preserve both private originals, validate target helper regeneration/retention and compare actual screens before acceptance. No source file changed or silently omitted. Regression prevention: full blob comparison plus owner screen/functional retests.

## ISSUE-021 — Full migration IPA and first-run import not established

Severity: HIGH. Component: deployment. Status: BLOCKED awaiting owner deployment choice and device evidence. Reproduction: diagnostic candidate report declares configuration_bundled=false/addons_added=false. Root cause: source separates app resources and writable profile; a safe automated importer, complete iOS dependency closure and signer compatibility are unproven. Prepared 33-file target and Drive ZIPs remain separate; no functionality is deleted. Proposed fix: owner selects separate first-run import or requires a proven automatic bootstrap; then complete dependency/skin import and actual-device tests. Candidate must not be called the final migrated IPA. Evidence: docs/phase4-source-findings.md, docs/phase4-device-testing.md, reports/unsigned-ipa-candidate.json. Regression prevention: task completion requires real evidence and no bundled-config claims from a foundation-only ZIP.

CI observations retained: pull_request path filters inspect the cumulative PR diff, so later publications also rerun the unchanged capped Drive job. This was previously assumed to be per-commit; no unchanged-source rerun is evidence of new functionality. GitHub warns pinned v4 actions use deprecated Node 20 and runner forces Node 24; observed runs pass. Keep timeout/permissions and inspect failures rather than suppressing warnings.

ISSUE-013 Phase 4 signing evidence: original official DEB main signature carries jailbreak/private entitlements (reports/ios-foundation-entitlements.json). They are not a valid ordinary sideloading entitlement template. Candidate active signatures/entitlement regions are removed; permitted provisioning and actual acceptance remain unverified. Two independent CI builds yielded identical full IPA SHA-256 (reports/ipa-reproducibility.json). No device result inferred.

## ISSUE-022 — Capture generator could overwrite future failure evidence

Severity: MEDIUM. Component: persistent visual tracking. Status: COMPLETE. Reproduction: former roster generator recreated every row with empty evidence on rerun. Root cause: generated checklist did not merge existing review records. Fix: retain status/evidence for unchanged routes, preserve previous versions when a route changes, and keep removed routes pending owner exclusion review. Evidence: scripts/test_visual_roster.py (three regressions); current roster retains all 184 entries and no actual captures are claimed. Regression prevention: same-route failure, changed-route history and removed-route retention tests.

## ISSUE-023 — Enforce isolated IPA staging before writes

Severity: MEDIUM. Component: packaging safety. Status: COMPLETE. Static audit found the builder checked output freshness/outside-repository placement but did not explicitly reject an output nested inside its input app. Fix: validate distinct non-overlapping resolved input/output paths and reject existing output before any writes. Actual hosted paths were already isolated; no source mutation or damaged build occurred. Evidence: scripts/test_unsigned_ipa.py now has seven passing tests, including input-descendant and existing-output rejection. Regression prevention: both staging tests remain mandatory.

## ISSUE-024 — Missing preserved Fuse view-layout input

Severity: HIGH. Component: sanitized layout export. Status: IN PROGRESS. Existing export omitted script.skinvariables/skin.arctic.fuse.3-viewtypes.json even though a generated skin include reflected it. Recovered the input from the verified private backup and validated every content/view pair against real 3.4.8 skin rules; only known noncredential locations are allowed. Evidence: reports/fuse-layout-input-recovery.json. No original source altered. Target generator integration/regeneration and device parity still need tests; do not claim resolved prematurely.

## ISSUE-025 — Phone-local Elementum engine has no upstream iOS artifact

Severity: HIGH. Component: primary playback/native build. Status: BLOCKED. Current release assets/source target tables omit iOS. Stable source shared C entry points exist, but libtorrent/OpenSSL iOS builds, Kodi bridge, signing and lifecycle have not been proven. Local environment has no Go/C++/Xcode SDK tools. Evidence: docs/elementum-ios-port.md and migration/elementum-ios/source-lock.json. Proposed next step: approved capped Mac source compilation probe, then actual dependency/bridge work and owner-device tests. No remote alternative selected; no fake/stub engine created.

## ISSUE-026 — Elementum stable remote-auth debug log exposes values

Severity: HIGH. Component: optional remote client, not selected. Status: OPEN. Pinned v0.1.114 monitor.py logs remote_login/remote_password when configured. No owner values were supplied or used. Remote use would require a source-pinned redaction patch, safe transport/callback review and owner host approval. Native primary path remains separate. Regression prevention: assert no auth-value logging in any future enabled client package.

Additional source lookup failures retained: repository.jurialmunkey root addon.xml returned 404; actual configured omega/zips directories were found through installed public repository metadata. A guessed skinvariables-click filename did not exist; navigation investigation moved to real helper listitem/player code. No behavior inferred from missing files.

ISSUE-024 correction: initial missing-input diagnosis was incorrect. The 76-choice viewtypes JSON already exists in the immutable sanitized snapshot and target. A direct semantic comparison proves the duplicate new validation input was identical; the duplicate is removed, without altering the snapshot. Real helper generation reproduces all 68 baseline expressions (reports/fuse-generation-validation.json). This resolves the data-preservation concern statically; first-run shortcut regeneration and visual equivalence still require device tests. Keep the original misdiagnosis above rather than erasing it.

## ISSUE-027 — First two native workflow events skipped

Severity: LOW. Component: one-shot trigger. Status: COMPLETE for activation. Initial marker add/remove edits produced skipped runs 40975216092/40975216341 and no Mac compilation. Cause: condition was not met; immediate marker removal may have raced evaluation (not proven from skip logs). Keeping the marker until the job was accepted produced exactly one actual Mac job, run 40975489124, then the marker was removed. No skipped event is called a compilation attempt or success. No marker remains armed.

## ISSUE-028 — Approved Mac probe lacks Go

Severity: HIGH. Component: native engine build executor. Status: BLOCKED. Run 40975489124/job 123802357346 reached the actual macOS runner, then exited 2 at the explicit missing-go guard before source checkout/engine compilation. Root cause: proposal assumed an existing Go installation; the runner does not supply one on PATH. Smallest proposed fix: SHA-pinned Go setup with an explicit version, then another capped probe only after owner approval. No native iOS engine was built, no test was suppressed and no automatic second Mac attempt is authorized.

## ISSUE-029 — Reviewed GUI asset exception initially incomplete

Severity: LOW. Component: repository scanner. Status: COMPLETE after retest. Initial clean-baseline regression failed because the exact-hash PNG exception ran after the generic extension check. Fix: exempt only manifest-listed source GUI paths from that extension gate, then enforce exact path/name/hash and private-value checks. Reachable-history scanning permits only those same reviewed image hashes; other binaries/images remain rejected. Evidence: scanner clean-baseline and GUI-tamper regressions; nine actual icon/mask/gradient/placeholder assets were visually reviewed, with no screenshots or personal media. No scan failure was bypassed or file pushed before the fix passed.

ISSUE-029 disposition update: the reviewed-GUI exception passed its clean/tamper regressions, but owner subsequently removed YouTube/Fusion from target scope. The unpublished custom copies and scanner/image exceptions are discarded; the standard binary/image exclusions remain. No private or GUI image was pushed.

## ISSUE-030 — Private staging guard rejected shared temp root

Severity: MEDIUM. Component: offline importer. Status: COMPLETE after retest. Initial 16 fixture tests errored in setup because the guard rejected any ancestor Git metadata; this managed session has /tmp/.git. Fix: ignore only shared system temp/home workspace Git metadata while still rejecting nested project repositories and all known original Kodi/backup paths. Added a nested-project rejection regression; no original profile was mutated by failed tests. Evidence: scripts/test_import_profile.py.

## ISSUE-031 — Generic unittest discovery cannot run two existing command-line suites

Severity: LOW. Component: validation invocation. Status: COMPLETE for invocation fix. Running unittest discovery produced SystemExit errors because test_checks.py invokes unittest at import time and test_drive_runtime.py requires --source-cache. No product failure inferred. Fix: invoke each existing suite as its supported script and pass the verified private Drive source cache explicitly. All 16 suites then pass (117 tests before capture regression addition). Retain failed command in the session evidence. Regression prevention: documented per-script runner; do not use generic discovery for this repository without refactoring those entry points.

ISSUE-028 disposition: owner defers native engine work; missing-Go failure retained in reports/elementum-ios-probe.json. No retry and no compiled engine.

ISSUE-031 test extension: the new non-iOS entrypoint guard regression initially raised NameError because its fixture lacked ROOT. Defined the test root and reran successfully; this was a fixture setup failure, not a Kodi/device test.

## ISSUE-032 — Public source ZIP root assumption stops import build

Severity: MEDIUM. Component: public-source packaging. Status: IN PROGRESS pending actual CI retest. Run 40980673919 passed its host tests/acquisition but failed clean_addon with Unexpected archive root; no complete import artifact produced. Exact offending source was not included in the first traceback, so its layout remains unconfirmed. Fix preparation: locate exactly one manifest matching the pinned ID/version, normalize its archive root, drop only recognized __MACOSX/.DS_Store packaging metadata, reject unknown sibling content, and record source-specific failure metadata. Added versioned-root/metadata and unexpected-sibling regressions. Do not claim the observed failure fixed before hosted retest.

ISSUE-032 test setup note: the successful-normalization fixture initially omitted the required source URL receipt field; added that public fixture field and reran all six builder tests. No source validation was disabled.

ISSUE-032 hosted retest: run 40980888449 passed the earlier root handling, then stopped at script.trakt 3.9.0 with duplicate/case-colliding source ZIP members. New source-only normalization permits duplicate aliases only when decompressed bytes are identical; different content still fails. Final/import ZIP validation remains strict and rejects all duplicate/case aliases. Added strict-import and differing-content regressions, and preserve precise validation errors instead of wrapping them as a generic corrupt ZIP. No complete artifact or phone success claimed.

ISSUE-032 exact diagnosis: run 40981093445 identifies differing script.trakt/resources/language/resource.language.es_mx/strings.po and es_MX/strings.po aliases. Kodi's official Language_support guide requires lowercase language folders (https://kodi.wiki/view/Language_support). Add a Trakt-only translation normalization: keep the existing lowercase variant; rename uppercase-only folders without changing their bytes; record discarded source hashes/provenance. Source-code collisions still block, and final bundle/import duplicate checks stay strict. Added three regression tests for ordering, unique-language preservation and code-collision refusal. Hosted retest pending.

ISSUE-032 next hosted retest: run 40981317944 passed Trakt normalization, then Drive acquisition raised KeyError for .gitattributes. Confirmed both pinned upstream .gitattributes explicitly export-ignore repository metadata/tests; GitHub source archives correctly omit those files. Fix: skip excluded metadata/tests before lookup, verify every retained runtime blob against the source lock, report actual verified payload counts rather than claiming omitted metadata verified. Two new regressions cover allowed metadata absence and required-runtime absence rejection. No missing runtime file is skipped.

## ISSUE-033 — Importer merged add-on setting definitions as private settings

Severity: HIGH. Component: offline apply. Status: FIXED in code; full-bundle hosted retest pending. Static end-to-end audit found the settings.xml suffix check also matched addons/<id>/resources/settings.xml. A new regression reproduced corruption: nested category definitions became an empty settings root. Fix: merge only userdata/addon_data/*/settings.xml and userdata/guisettings.xml; copy add-on source definitions byte-for-byte. All 19 importer regressions pass after the fix. The first successful acquisition artifact from run 40981565041 is superseded and must not be used for import; no owner/device import occurred. Add complete-bundle apply/repeat/restore smoke validation before the replacement artifact is offered.

ISSUE-032 resolution: COMPLETE for host/source packaging. Run 40981957027 completed acquisition, exact-version/dependency/ZIP validation, full apply/repeat/restore and artifact upload. All original failures above remain. Source normalization receipts are in the artifact; no runtime success inferred.

ISSUE-033 resolution: COMPLETE for host importer fix. Run 40981957027 verifies all 7324 actual add-on source files byte-for-byte after apply, repeated apply has zero writes, and clean restore matches all original synthetic-profile hashes. Replacement artifact 12945112472 uses the fixed importer. Actual iPhone import/rollback remains BLOCKED separately.

ISSUE-021 update: separate import is owner-approved and complete host-reviewed kit now exists; actual target profile access, private clean export, installation/enable and runtime acceptance remain BLOCKED. ISSUE-020's two generated Fuse differences are resolved statically by preserved view input and rebuilding stale shortcut output; actual phone generation/visual parity still requires evidence. Retained Trailer controls may depend on the owner-excluded YouTube add-on; those trailers are unsupported in this kit and must not trigger an unreviewed installation.

## ISSUE-034 — Single-IPA bootstrap runtime not yet device verified

Severity: HIGH. Component: automatic first launch. Status: IN PROGRESS (host implementation/build tests underway). Owner supersedes manual import. Implement optional packaged system service and full addon-manifest registration based on Kodi 21.3 tagged source; journal/backup configuration, preserve private unknown settings, activate via JSON-RPC, set skin via live API, repeat without overwrites, provide recovery script. Test missing/corrupt seeds, missing addon registration, partial writes, API failures, symlinks, clean recovery and immutable input app. Device execution, signing, rendering and Drive remain pending; do not infer runtime success from produced IPA. Source lookup for ServiceAddonManager.cpp returned missing; actual implementation is xbmc/addons/Service.cpp, reviewed directly.
