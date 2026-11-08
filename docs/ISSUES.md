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

Severity: HIGH. Component: automatic first launch. Status: BLOCKED on actual iPhone acceptance; host implementation/build complete. Owner supersedes manual import. Implement optional packaged system service and full addon-manifest registration based on Kodi 21.3 tagged source; journal/backup configuration, preserve private unknown settings, activate via JSON-RPC, set skin via live API, repeat without overwrites, provide recovery script. Test missing/corrupt seeds, missing addon registration, partial writes, API failures, symlinks, clean recovery and immutable input app. Device execution, signing, rendering and Drive remain pending; do not infer runtime success from produced IPA. Source lookup for ServiceAddonManager.cpp returned missing; actual implementation is xbmc/addons/Service.cpp, reviewed directly.

## ISSUE-035 — Skin API acceptance is not proof of confirmed skin loading

Severity: HIGH. Component: bootstrap completion. Status: FIXED in implementation; device verification pending. Kodi's tagged ApplicationSkinHandling.cpp/h shows Settings.SetSettingValue queues ReloadSkin(confirm), whose normal ten-second confirmation can revert the skin. Initial host implementation marked completion immediately on API acceptance, so the first built IPA is superseded. Fix: runtime waits for actual xbmc.getSkinDir() == skin.arctic.fuse.3 and no active Yes/No dialog before completing, with timeout/recovery on refusal/load failure/abort. Add rejection regression. Do not automate or accept consent dialogs on the owner's behalf. The standard Kodi Keep Skin confirmation may require one tap on first launch; no manual import/file transfer is involved. SettingsOperations.cpp confirms live SetValue does not itself call Save; persistence through real background/restart remains an explicit device test, not inferred from host fixtures.

## ISSUE-036 — Mutable skin generators cannot target the signed app bundle

Severity: HIGH. Component: Fuse/skinvariables startup. Status: BLOCKED on device testing; replacement IPA build/host validation complete. Actual viewtypes.make_xmlfile delegates to jurialmunkey.futils.write_skinfile and generates includes in the selected skin directory. Signed app resources are not a safe writable target. Fix: package original sources, automatically stage both skins into special://home/addons on first launch, verify copied tree hashes, invoke Kodi UpdateLocalAddons and verify loaded addon paths before activation. Tagged AddonManager.cpp scans home last and replaces equal-version system entries; no version spoofing or database writes needed. Existing same-version writable skins are preserved rather than overwritten; conflicts stop for review. Runtime-generated files stay in the sandbox. Recovery restores configuration/Estuary while retaining the inactive skin installation as a package cache; no live skin-code deletion. No manual owner file copy/import. Earlier IPA candidates superseded.

ISSUE-034/035/036 final host resolution: run 41058684326 (source 0b169c6622031d4ca4ccdbbff6f4ef8d3523223a) built and uploaded the replacement full IPA. 149 tests/19 suites pass; source/seed bytes, dependency closure, ZIP integrity and all 151 ARM64 images validate. Mutable skin staging, Kodi rescan/path checks, loaded-skin confirmation/timeout and recovery are implemented/tested on host. These issues are COMPLETE for host deliverables and AWAITING DEVICE TESTING for actual iPhone behavior; no runtime compatibility, persistence or recovery evidence invented. Earlier bundled IPA candidates remain superseded.

## ISSUE-037 — Verified owner-reported Fuse navigation/setup failure

Severity: CRITICAL for iPhone usability. Status: IN PROGRESS; revised host-tested IPA pending. Evidence: reports/owner-fuse-navigation-failure.json, screenshot hash only (raw image kept private). Owner reports customized app launches, manually selected Fuse in Interface, no Keep Skin prompt, no menu even with two-finger-right swipe, and only No Results screen. This is failed skin validation, not successful navigation/playback. No phone journal/network trace is available.

Source-confirmed defect: Kodi 21.3 system/settings/darwin_ios.xml marks input.enablemouse invisible; SettingsOperations.cpp rejects invisible settings in GetSettingValue. Old bootstrap treated that API rejection as fatal and rolled back before skin activation. A new regression reproduces exactly Unknown GUI setting: input.enablemouse. Another regression proves a prior recovered FAILED marker prevented retry. Those failures are retained here. This strongly explains the manual selection/rollback path but is not asserted as the exclusive phone failure without its journal.

Structural contributors: old Home depends on generated hub controls/default focus 300/400, snapshot disables Home submenu and permits first-widget focus, and no permanent widget-independent settings/recovery strip existed. Local in-progress playlists and videodb routes are retained while personal media DB is intentionally absent; empty local widgets are expected without a populated library, but the image alone cannot diagnose authentication/network/helper errors. Screenshot On Deck labels do not by themselves prove the original shortcut generation completed.

Fixes: remove/skip the iOS-hidden preference; preserve failed journal in private history and retry once only for a changed seed revision; keep bootstrap as a required packaged system service so repair runs even if an earlier optional service is disabled; apply backed-up, idempotent navigation upgrades to existing writable skins even with COMPLETE markers. Inline large percent-width controls (Back/Home/Browse/Settings/Drive/Recovery) in 32 major non-dialog windows; keep dialogs/fullscreen playback unchanged. Focus safe Settings on hub entry, enable submenu, prevent first-empty-widget focus. Add native static navigation/recovery menu, source-backed rebuild actions, private metadata diagnostics, stock hit-tested long press, pan, two-finger navigation/back/page gestures and three-finger Settings. Sync saved preferences to loaded skin through supported setters/readback so old live settings do not overwrite the seed on reload. Pinned Settings.SetSkinSettingValue returns assigned values (including false/string), so verify readback rather than requiring literal True. Standard builtin fallback registers unknown skin settings; no direct database changes. No permanent Estuary substitution.

Validation: reports/ios-navigation-tests.json, reports/ios-navigation-audit.json; complete verified-copy XML patch audit (32 windows, second pass zero changes), corruption/collision/empty-state/focus/geometry/upgrade/live-setting regressions. Before fixes, hidden-mouse and recovered-marker regressions failed; after fixes they pass. Physical touch, alignment, helper generation and recovery remain AWAITING DEVICE TESTING after rebuild.

Simulator: no local xcodebuild/xcrun, no configured remote Mac simulator/runtime; tagged Kodi 21.3 README.iOS.md explicitly says simulator builds unsupported by that recipe. Historical capped Mac engine probe is not simulator infrastructure. No simulator build/run or screenshots claimed and no new Mac job launched.

## ISSUE-038 — Broad navigation patch included filename-defined dialogs

Severity: HIGH if shipped. Status: COMPLETE on host; no broad candidate IPA was published. Initial static audit found 76 windows matched by root type alone, including DialogKeyboard, Pointer and OSD files because Kodi identifies many dialogs by filename without type=dialog. Fix: explicit major-window/hub allowlist; preserve dialogs, pointer, playback/OSD, calibration, screensavers and script windows. Added untyped dialog/pointer/OSD regression cases. Final XML audit reports the reduced count and second-pass zero changes. Earlier 76-window candidate is discarded, not counted as UI success.

ISSUE-037 portability audit: canonicalize trusted Kodi VFS profile/home roots before checking child symlinks, and require profile within app home. Platform-level path aliases must not be mistaken for an owner skin symlink; child/file symlink rejection remains. No actual iPhone root path is available or inferred from the screenshot.

ISSUE-037 live-setting source audit correction: pinned Skin.cpp GetSkinSetting uses m_settings populated during LoadSettings, while TranslateString/TranslateBool can create entries only in runtime string/bool indexes. Therefore a newly created builtin setting is not reliably visible in JSON-RPC's lookup index before reload. Repair readback now uses native Skin.String/Skin.HasSetting for the running skin (registered API values still accepted), with standard builtins for unknown entries and Reset for empty strings. Added a regression with a deliberately stale JSON index, false booleans and comma-containing strings. Earlier unpublished Touch-r1 candidate is superseded; no device validation claimed.

ISSUE-037 Touch-r1 host/build result: run 41068166024 SUCCESS; artifact 12983492116 contains the revised IPA with SHA-256 9c72b195494924fddfa67f24627546ea59f64efe0f04b373647d907e9034db84. Source is 91ed4dd79d5637f57f2ae03fadc6cee4171fca06. 165 host tests/20 suites pass; 32 major-window patches, 31 seeds, dependency/source/ZIP/native checks pass. Status: BLOCKED on physical iPhone retest. The prior verified device failure is not marked fixed; no phone result, simulator or screenshot was fabricated. Prior IPA retained as rollback.

## ISSUE-039 — GitHub branch-reference API failed while publishing final evidence

Severity: LOW. Component: publication connector. Status: COMPLETE via supported fallback. Two update_ref calls returned internal GitHub GraphQL errors at 2026-10-30T14:24 UTC; read-back confirmed the branch remained unchanged. Root cause is external/unknown, not presumed permission denial. Preserved the local evidence commit. Published the same reviewed files sequentially through the GitHub contents API, retaining both histories and avoiding force-push. Artifact/code publication had already succeeded; no build failure or lost owner work. Verify final remote/local trees before claiming success.

## ISSUE-040 — Device log: Fuse reload/reversion and helper startup failure

Severity: CRITICAL. Status: OPEN; diagnosis recorded, no new fix/device success claimed. Owner-provided 783-line launch log is kept private; sanitized timeline/hash in reports/owner-touch-r1-launch-log.json. At 07:41:47 Fuse loads from writable skin copy, generated shortcut include is missing and Home widget includes are invalid. Fuse reloads at 07:41:48.023, then Estuary loads at .185. At .316/.326 queued skinvariables actions cannot parse splash/build-template JSON through special://skin. Bootstrap reports only RuntimeError at 07:42:07, without message/traceback. Skin-switch/confirmation/reload racing is consistent with this ordering; exact exception cause and on-phone JSON contents remain unverified. Do not treat JSONDecodeError alone as proof that bundled JSON is malformed. Next diagnosis/fix must serialize skin activation and helper generation, prevent early relative-path reads against the wrong skin, and improve sanitized bootstrap exception evidence. Fresh settings/default creation and Bonjour errors are separate observations, not proven root causes.

ISSUE-040 repair candidate (Touch-r2): guard Fuse Home/hub helper onloads and reload alarms during activation; preserve Kodi's owner-controlled Keep Skin dialog. Explicitly run real pinned skinvariables view generation then shortcut generation with supported no_reload=true; require newly written, valid required includes before one final reload and completion. Wrong-skin changes, cancellation, malformed inputs, stale/partial outputs and bounded timeouts fail visibly. Existing completed profiles receive one backed-up navigation repair per revision without resetting their preferences. Sanitized failure evidence now records stage, exception class and basename/line/function frames without exception messages, locals or account paths. Exact prior failure remains a race hypothesis, not proven on-device. Status: IN PROGRESS pending host/build and physical retest.

Validation invocation failure: the aggregate runner initially invoked test_drive_runtime.py without its required --source-cache argument. This was a test invocation error, not playback failure. Reran with the isolated pinned public Drive source cache: all 9 tests PASS. Future aggregate invocation supplies that argument. Raw owner log stays outside GitHub.

ISSUE-040 Touch-r2 result: host regression suite 174/21 PASS; build run 41078491846/job 124140996253 SUCCESS; artifact 12987708727 uploaded, source ea4d224bb3e5b762379b27df66031a4202da13b5. Inner IPA SHA-256 d67b59e286206c5a1b7abaee07d11720de87e2967c28182754c4da3594b7006e. Archive/source/dependency/seed/native checks pass. Status: BLOCKED ON OWNER IPHONE RETEST, not resolved on-device. Prior failure and all 184 capture requirements retained.

## ISSUE-041 — Touch-r2 phone review: inert tabs, forced focus, covering bar, Drive hang

Severity: CRITICAL for iPhone usability. Status: FIXED ON HOST (Touch-r3); awaiting iPhone retest.

Root causes, verified against pinned Arctic Fuse 3.4.8 and Kodi 21.3 source:
- Header tabs/search/gear are drawn in modeless dialog 1182; Kodi's HandleAction only routes input to modal dialogs and the active window, so taps on them were never delivered. Fuse switches hubs through off-screen button 300 (left/right only).
- r2 forced `defaultcontrol always=98104` and `SetFocus(98104)` on every hub, so the bar's Settings button stole focus from Fuse.
- r2's fixed bar covered widget rows; Browse and Recovery opened the same menu.
- Fuse clears `HomeSwitcher.IsVisible` when a widget gains focus, hiding the header with no touch way back.
- `script.module.clouddrive.common` calls `urlopen` with no timeout, so a stalled sign-in connection stays on "Connecting with server" indefinitely.

Fixes (navigation revision r3): transparent tap targets in each hub window mirroring the header geometry (tabs, search, right-side hub icons, gear); disabled spacers so they cannot take touches; bar and forced focus removed from existing installs; header kept visible on iOS only; Google Drive and the navigation/recovery menu added to the gear menu (and the mislabelled "Quit" entry that opened Settings relabelled); phone-loadable widgets ordered before library-only ones and untouched library spotlights pointed at TMDb, once per revision with backups; Drive request timeout patched at IPA build time. Library/Trakt widgets remain empty until media or Trakt sign-in exist. Safe-area borders come from Kodi core, not this project.

## ISSUE-042 — Touch-r3 phone review: no Back, dimmed un-tappable Home, Drive TLS failure

Severity: CRITICAL. Status: FIXED ON HOST (Touch-r4); awaiting iPhone retest.
- No way out of Drive/Settings/library windows without a remote Back. Fix: visible Back and Home buttons (98300) in every major non-hub window on iOS.
- Scrolling up on Home dimmed the screen and blocked taps: Fuse's Up/Left/Info actions open submenu 1181 or bumper 1180, modal dialogs that swallow input. Fix: those `ActivateWindow(1180/1181)` actions are disabled on iOS in Includes_Home/Hubs/Actions/Search.
- Hero showed "No Results": empty Trakt rows sat first. Fix: rows needing a Trakt sign-in now follow open TMDb rows.
- Drive sign-in failed with `[SSL] unknown error (_ssl.c:1006)` while TMDb Helper (certifi CA bundle) works. Fix: the packaged Cloud Drive Common module uses certifi's CA bundle for sign-in, API and streaming connections, and depends on script.module.certifi. Not yet verified on device; if it still fails, the next step is a Kodi debug log.
- Remaining black/purple bars are Kodi's iPhone safe-area insets (XBMCController guiInsets); reduce them with Settings → System → Display → Video calibration.

## ISSUE-043 — Touch-r4 phone review: purple bars, no vertical swipe, header lost on poster focus, Drive TLS

Severity: HIGH. Status: FIXED ON HOST (Touch-r5); awaiting iPhone retest.
- Purple/brown bars: Fuse's Background_Blur_Quadrants draws a 200% image anchored top-right, and rows spill past 1080; Kodi does not clip to the safe-area canvas. Fix: a black frame (98400) outside the 1920x1080 canvas, last in every window/dialog, iOS only. Window-level animations in Fuse are fades only, so the frame never sweeps over content.
- Vertical swipes did nothing over posters: every horizontal row returns PAN_HORIZONTAL to GESTURE_NOTIFY and grabs the whole gesture, so grouplist 602 never scrolls. Fix: one-finger swipe up/down maps to Down/Up (row-by-row, using Fuse's smooth grouplist scroll).
- Header vanished and art zoomed when a poster was focused: rows generated on the device from shortcuts/generator/data/parts/*.xmltemplate clear HomeSwitcher.IsVisible, and Background_Main_Zoomer zooms fanart to 150%. Fix: templates patched like the includes; zoom disabled on iOS.
- Drive still failed with `[SSL] unknown error` using certifi. Fix: requests step through certifi, TLS 1.2 only, then Kodi's own curl transport, keeping the first that works. Added "Google Drive network diagnostics" to the iPhone menu (versions, DNS families and per-transport results for the sign-in server, Google API and TMDb; no bodies or account data) to pin down the root cause if it persists.

## ISSUE-044 — Touch-r5: black block over the right of every screen; Back/Home misplaced; no swipe after tapping a tab

Severity: CRITICAL (Settings unreachable). Status: FIXED ON HOST (Touch-r6), verified by rendering the patched skin in desktop Kodi 20 under Xvfb at the iPhone's 2.17:1 aspect with iOS conditions forced on.
- Root cause: Kodi keeps pixels square, so on a 2.17:1 screen the 1080-high skin canvas is ~2350 units wide, not 1920. The frame's right piece at a fixed left=1920 covered the right ~18% (clock, gear, menus). Reproduced in the rig, then confirmed fixed: every frame piece is now anchored outside an edge with left/right/top/bottom=-1000.
- Back/Home used a fixed left=1380 and overlapped the clock; now anchored bottom-right (right 60, bottom 24), clicked in the rig and returns to the previous window.
- After a tapped tab kept focus, Down (one-finger swipe up) did nothing; header tap targets now use Fuse's Hub_Action_Down. Verified in the rig that Down moves into the rows and the header stays.
- Rig limits: no touch gestures, iOS safe areas, TMDb network or Drive; those still need the phone.

## ISSUE-045 — Owner requests: calibration reset, in-app updates

Status: IMPLEMENTED ON HOST (Touch-r7); awaiting iPhone retest.
- Screen calibration: Kodi has no overscan API. On first start after the update, if guisettings.xml records a non-default overscan, the bootstrap opens Kodi's calibration window, triggers Kodi's own reset (its Yes/No confirmation) and leaves the window so Kodi saves it. Runs once; also available as "Reset screen calibration" in the iPhone menu. The default (reset) calibration is correct for iPhone: Kodi already keeps the GUI inside the safe areas.
- Updates: each IPA records its CI run number (build.json). "Check for updates" (gear menu, iPhone menu, add-on settings) reads this repository's build-N prereleases through Kodi's curl, downloads the newer .ipa into Documents/Kodi Updates (visible in the Files app) for the sideloader to install, and a quiet check runs at startup (toggle in settings). While the repository is private, a read-only GitHub token must be entered in the bootstrap add-on settings.
- Local rig limits: Kodi 20 from Ubuntu segfaults inside Python 3.12 (PyObject_GC_UnTrack) for Python add-ons, so these Python flows are unit-tested only; XML/layout checks in the rig remain valid.

## ISSUE-046 — Owner decision: Deck-style player choice

Status: IMPLEMENTED ON HOST (Touch-r8). Owner wants tapping to behave like the Deck: a movie or episode asks "How would you like to watch?" listing players (Elementum, Umbrella once ported); a TV show opens its seasons. The chooser now lists Elementum (unavailable until a native engine exists), Umbrella (offered automatically when the add-on and a TMDb Helper Umbrella player are installed; otherwise "coming soon"), local files and Google Drive. TV shows no longer detour through a watch-options folder; old plugin:// links still work. Because the watch-options add-on is part of the import bundle, the IPA step now pins to the bundle SHA-256 reported by the same CI run (built from pinned, hash-checked sources) instead of a hardcoded value.

## ISSUE-047 — Umbrella installed by the owner should appear in the player choice

Status: IMPLEMENTED ON HOST (Touch-r9). Umbrella stays unbundled (inventory exclusion unchanged). The bootstrap now carries the Deck's TMDb Helper Umbrella player (template URLs only, no account data) and copies it into addon_data/plugin.video.themoviedb.helper/players/ at startup only when plugin.video.umbrella is installed, never over an existing owner file. The chooser then lists "Umbrella" as a working option.

## ISSUE-048 — r9: scrolling in menus, Drive "unable to retrieve a pin", Drive title search

Status: FIXED ON HOST (Touch-r9); rig-verified where noted.
- Scrolling: the global one-finger swipe→Up/Down sent an extra focus move after a native flick; at a list's top this pushed focus out of the list, so later swipes went elsewhere. Row swipes now apply only to Home, the hub windows (11101–11109), Search and the video info page; every other list uses native drag scrolling.
- Drive sign-in: root cause found in the Kodi 21.3 rig with a local stand-in for the sign-in server. Kodi sent the POST correctly and the server replied, but xbmcvfs.File.readBytes() returns nothing when a response has no Content-Length (Kodi clamps the read to GetLength()==0). The fallback now copies the response to a temp file (xbmcvfs.copy reads to EOF) and reports a real error when the request fails. Same fix in the updater's release check and the network diagnostic. Verified in the rig: PIN JSON, 202 polling, IP, unreachable-host error, and the updater reading this repository's releases.
- Watch menu: "Search Google Drive for <title>" opens Drive's search on the first signed-in drive with the title filled in (packaged Drive module patched to accept a query and no drive id); "Browse Google Drive" remains.
- Home stutter: not changed without measurements; TMDb hosts are blocked in the build environment.

## ISSUE-049 — Rows unreachable while the spotlight's big info is shown
Status: FIXED ON HOST (navigation r9); rig-verified.
- With the spotlight's Play / More Information row focused, Fuse fills the screen with the hero info and pushes the poster rows to the bottom edge. A slow drag over the info text reaches no list, so only a quick flick moved focus. Hub windows now carry a transparent touch area over the hero info, shown only while the spotlight has focus; any touch there moves focus to the rows (Fuse's own Hub_Action_Widgets), which slide back up and scroll natively. Verified in the Kodi 21.3 rig: focus moved from Play to the first row and nothing opened.

## ISSUE-050 — Elementum on iPhone (r10)
Status: BUILT AND BUNDLED ON HOST; DEVICE TEST PENDING.
- iOS apps cannot start a second program, so the pinned Elementum engine (cdab7e2, libtorrent RC_1_1 760f948) is built on macOS CI as `elementum.framework` (arm64, iOS 14+, only system libraries) by `migration/elementum-ios/build-ios-engine.sh`, published once per engine tag and pinned by sha256 in `migration/elementum-ios/source-lock.json`.
- The IPA build adds the pinned Elementum 0.1.114 client, Elementum Burst 0.0.99 (the Deck's search providers; pure Python) and kodi-six/future (official repo-scripts, git-tree-verified), puts the framework in `Kodi.app/Frameworks`, and patches the add-on's existing library mode: on iOS it loads the framework in-process with ctypes, keeps its profile and log in Elementum's add-on data, and skips the ELF/PE platform probes (removed from the bundle).
- First start sets Elementum's download folder to `Documents/Elementum Downloads` (visible in the Files app) unless one is already set. The watch menu offers Elementum through TMDb Helper's `ios.elementum.json` player, installed once Elementum is present.
- Untested on a device: Go runtime start-up inside Kodi, Kodi's JSON-RPC on 9090, sideloader re-signing of the nested framework, and which Burst providers answer from the phone's network.

## ISSUE-051 — Search field opened a hub instead of the keyboard
Status: FIXED ON HOST (navigation r10); rig-verified.
- On the Search screen Fuse draws its text field where the hub tabs are, and the touch header's invisible tab targets sat over it, so a tap on the field switched hubs (rig: it opened Movies). The tab and search targets now hide on Search; a tap reaches Fuse's edit control, which opens Kodi's text input (on iPhone, the native keyboard; with a hardware keyboard attached, Kodi's dialog accepts typing). Search also gets the Back/Home pair, since its tab row is no longer tappable.

## ISSUE-052 — Elementum engine thread never started on iPhone
Status: FIXED ON HOST; device test pending.
- Debug log from the phone (build-40): Elementum's service started its JSON-RPC thread, but its engine thread is created only when the platform can fork, and the iOS patch (correctly) reports that it cannot, so no engine ever ran and every Elementum request got no answer from 127.0.0.1:65220. The service now also starts the engine thread on iOS, where it loads the framework in-process.

## ISSUE-054 — Engine stops itself inside Kodi ("Parent shut down")
Status: FIXED IN ENGINE BUILD r2; device test pending.
- build-42's safety net captured the engine log: the engine started (libtorrent session, HTTP server on 65220, TMDB key check), then logged "Parent shut down, shutting down too...". It watches for its parent process to become pid 1; inside Kodi on iOS the parent of the process is launchd (pid 1), so the watch fired immediately, and the shutdown inside the host process ended Kodi. The iOS engine build now skips the parent watch in shared-library mode (`migration/elementum-ios/build-ios-engine.sh`), published as framework tag `elementum-engine-cdab7e2-r2`.
- The same log showed Elementum's download folder still pointing at a previous install's data container (iOS moves it on reinstall). The setup add-on now follows a folder it set earlier to the current path, leaving an owner-chosen folder alone.

## ISSUE-055 — Umbrella "no providers"; Drive sign-in error 1010 on a workers.dev server
Status: FIXED ON HOST (not yet released); device test pending.
- Umbrella finds sources through an external scraper module. The Deck used CocoScrapers 1.0.45 (and had ResolveURL 5.1.212); neither was on the phone. Both are now pinned by sha256 to their publishers' repositories. ResolveURL ships inside the app. Umbrella imports its scraper module only from `special://home/addons`, so CocoScrapers ships in the setup add-on's payload and is copied into the writable add-ons folder at first start (never over an existing copy), enabled, and Umbrella is pointed at it unless the owner already chose a module. Debrid accounts still need signing in on the phone.
- A self-hosted sign-in server on a free `*.workers.dev` address answered the add-on with Cloudflare error 1010: the Browser Integrity Check can't be turned off there, and it rejects the add-on's non-browser user agent (the /ip probe sent none). The sign-in requests now send a browser-style user agent that still names the add-on, Kodi and Python versions. If 1010 persists, the fallback is a custom domain on Cloudflare with the check turned off (the sign-in server's SETUP.md).
- Also from the Deck, pinned to their publishers: repository.jurialmunkey 3.4 and repository.cocoscrapers 1.0.0 (updates), plugin.program.autocompletion 2.1.2 + script.module.autocompletion 2.1.1 (search suggestions) and script.module.inputstreamhelper 0.8.6, the last three from Kodi's official repo-plugins/repo-scripts trees (git-tree-verified). YouTube stays out at the owner's request.

## ISSUE-056 — AirPlay button
Status: BUILT ON HOST; device test pending.
- Kodi's skin cannot draw Apple's AirPlay control, so `migration/airplay-ios/build-airplay.sh` builds KodiAirPlay.framework (an AVRoutePickerView, the same "AirPlay & Bluetooth devices" sheet as Control Center) on macOS CI, published once per tag and pinned in `migration/airplay-ios/source-lock.json`. The setup add-on loads it with ctypes and shows the button in the top-right corner while video or music plays full screen (setting: Playback › Show the AirPlay button); the iPhone recovery menu has "AirPlay & Bluetooth devices" to open the sheet any time.
- The route picker sends audio to AirPlay speakers and TVs. Kodi draws video with OpenGL, not AVPlayer, so video on a TV goes through Screen Mirroring (Control Center), where Kodi shows full-screen on the TV.
- Changed at the owner's request (audio + video, phone free, Roku as the main TV): the video controls get a top-right **Play on TV** button. It finds a Roku on the phone's Wi-Fi (asking each address of the /24 on port 8060, since iOS blocks multicast discovery for sideloaded apps), remembers it, and sends the playing link to Roku's built-in "Play on Roku" receiver through the External Control Protocol. The Roku then streams straight from the internet (MKV included), and Kodi on the phone stops. A link served by Elementum on the phone is rewritten to the phone's Wi-Fi address and needs Kodi kept open. Apple's AirPlay button stays available for audio (gear menu; optional button during playback, off by default).

## ISSUE-057 — Drive sign-in still 403 (Cloudflare 1010) on the owner's workers.dev server
Status: FIXED ON HOST; verified against the owner's server up to the Google step.
- Tested from the build environment against the owner's sign-in server: only requests with Python's default "Python-urllib" user agent get 403 / error 1010; the add-on's own user agent passes. The sign-in screen's first request (`GET /ip`, in ui/signin.py and ui/addon.py) is sent with no headers, so it carried the default agent and failed before a code was ever requested. The packaged Drive module now gives every request a user agent when none is set. With it, the full sequence answers correctly from the owner's server: /ip 200, POST /pin 200 (code issued), /ip probe 200, code poll 202 (waiting for the browser).

## ISSUE-058 — Play on TV for any TV on the Wi-Fi
Status: BUILT ON HOST; device test pending.
- The video controls' Play on TV button now finds Rokus (ECP, port 8060), Chromecast / Google TV (name from port 8008, Cast protocol on 8009 with the Default Media Receiver) and DLNA/UPnP smart TVs (unicast M-SEARCH to each address, AVTransport Stop / SetAVTransportURI / Play with DIDL-Lite metadata), all probed together, and lists them with Apple TV / AirPlay. Roku, smart TVs and Chromecast stream the link themselves (phone free; Elementum links use the phone's Wi-Fi address). AirPlay opens Apple's player with external playback and the AirPlay sheet (KodiAirPlay.framework r2, `kodi_airplay_play`): real AirPlay video with audio for MP4/MOV/HLS; MKV is flagged as likely to fail there.
- Verified on host: protocol units (DLNA description and SOAP, SSDP parsing, Cast message encoding and a simulated Chromecast LOAD exchange) and a DLNA run over HTTP against a local stand-in renderer.
- Downloads (owner: Umbrella streams only; Elementum should ask): Elementum writes what plays to files and asks afterwards (keep downloading? / delete the files?); kept videos are moved into Documents/Kodi Downloads/Movies or TV Shows, deleted ones leave nothing. Umbrella is set back to streaming only where an earlier test build had pointed it at those folders.

## ISSUE-059 — Kept Elementum videos go to Google Drive
Status: BUILT ON HOST; needs the drive.file sign-in (deploy workflow) and a device test.
- The owner wants kept downloads in Google Drive, not on the phone. The Drive sign-in only had drive.readonly, so `.github/workflows/signin-server.yml` redeploys the owner's sign-in Worker (pinned cguZZman/signin-server, run from GitHub on the phone) asking for drive.readonly plus drive.file, which reaches only files this app creates. Credentials come from repository secrets; the Google client secret stays on the Worker.
- `driveupload.py` (setup add-on, background thread, idle only, never during video playback) uploads finished videos from Kodi Downloads/Movies and TV Shows to Google Drive › Kodi Downloads › Movies / TV Shows › <show> with Drive's resumable protocol (16 MiB pieces; an interrupted upload resumes from Drive's confirmed offset, also after a restart), using the Google Drive add-on's tokens, refreshed through the owner's sign-in server. The phone copy is removed only when Drive reports the same size (setting). Verified on host against a stand-in Drive server: folder reuse, apostrophes in names, an upload interrupted by server errors and resumed byte-exact, phone copies and empty folders removed, partial and non-video files left alone.

## ISSUE-060 — Elementum showed its plain link list instead of the Deck's "Choose a version" page
Status: PORTED ON HOST; rig-verified; held for the UI update (not pushed to the build branch).
- On the Deck, Elementum's `rpc.py` `Dialog_Select_Large` hands the link list to `deck_picker.py`: a quality choice (only qualities present, or "Show all"), then the five best different links in that quality on `DeckSourceSelect.xml` with the title's poster, background, year/runtime and plot. Those files existed only on the Deck; the owner sent the Deck Keeper snapshot. They are now in `migration/deck-picker/` unchanged, installed into the bundled Elementum with the same `rpc.py` edit; the two full-screen background layers reach the right edge on the phone's wider canvas. The watch menu leaves the title's details on the Home window, as the Deck's Sources chooser did.
- Verified: the picker parses the 9 streams the phone listed (owner's screenshot) and offers "1080p Full HD — 8 versions" / "720p HD"; its top-5 choice maps back to Elementum's original index; cancel and "Show all" fall back to Elementum's own dialog. Rendered in the Kodi 21.3 rig at the phone's proportions.
## ISSUE-060 — r11: portrait mode (owner design "layout A")

Status: IMPLEMENTED ON HOST; rig-verified layout; native build in CI; awaiting iPhone test. Details: docs/portrait/README.md.
- Kodi 21.3 iOS cannot rotate by configuration: `XBMCController` returns a landscape-only mask, `WinSystemIOS` caches the first screen size forever, and nothing resizes the GL framebuffer or safe-area insets. Patching only the mask would leave a clipped landscape picture with misplaced taps. Fix: `migration/ios-portrait/kodi-21.3-portrait.patch` (rotation handler that resizes the framebuffer, resets the cached size, rebuilds RES_DESKTOP and insets on Kodi's thread; fullscreen video stays landscape), built on macOS by `.github/workflows/kodi-ios-portrait.yml`. Only the main executable is swapped in, after checking it loads the same libraries as the official one.
- Found in the rig: a grouplist passes taps only to children that are fully on screen (`CGUIControlGroupList::IsControlOnScreen`), so a poster row partly under the tab bar ignored taps. The same patch lets partly visible rows take taps inside the list's own area.
- Skin: Kodi picks the closest `<res>` folder, but loads includes/fonts once per skin load, so the bootstrap reloads the skin after a rotation settles. Fuse gets a generated `portrait` folder (1080x2090 = square pixels in the 16 Pro's portrait safe area): Home/TV/Movies/Downloads hubs (hero card, Fuse widget rows, bottom tab bar), show page (season chips + episodes), info page, centred select dialog (watch chooser) and More menu; every other window is the landscape window shrunk into the middle (taps verified).
- Rig bug fixed before shipping: a loop variable overwrote the window name, giving every shrunk dialog a full black background (black screens behind notifications).
- Owner change: Google Drive rows removed from "How would you like to watch?" (Elementum will play Drive sources itself).
- Limits: rig has no touch gestures, safe areas or rotation; rotation and the native build need the phone.
- r3 (owner review, "Netflix and Apple Home had a baby"): Apple TV app look (large titles, full-bleed hero, frosted floating tab bar
  Home · Movies · TV · Library · Search, no Drive tab), Library (Movies / TV Shows → poster grid), Search (field + category tiles),
  iOS-style long-press menu (title card + icon rows), Continue Watching first on Home (movies and episodes mixed), TV (episodes)
  and Movies (movies). Kodi's library rarely knows phone playback (TMDb Helper/Elementum), so the watch chooser records what it
  starts and the bootstrap service saves progress; `plugin.video.kodi.ios.watch/?action=continue` lists it with library
  in-progress items. Kodi does not pass Home's focused item to the context menu, so the service publishes it as Portrait.Item.*.
  Rig findings fixed: page lists end above the tab bar (focused rows could hide under it), 4-px gradient textures stretched badly,
  `String.IsEqual` cannot compare two infolabels, `colordiffuse="00000000"` means "untinted".
- r4 (owner request): real Liquid Glass tab bar. The web/SwiftUI "liquid glass" projects cannot run in Kodi's OpenGL skin,
  which can neither blur nor refract what lies behind a control. `migration/glassbar-ios` builds KodiGlassBar.framework, a
  native bar using Apple's UIGlassEffect (iOS 26; frosted material before), with a glass lens that follows the finger and
  springs to the chosen tab. The bootstrap loads it like the AirPlay button, shows it on the five tab pages in portrait when no
  dialog is open, marks the page and runs tapped tabs; the skin hides its own bar meanwhile. Not testable in the Linux rig.

## ISSUE-061 — r11 portrait merged with the Deck picker
Status: MERGED ON HOST; device test pending.
- `feature/ios-portrait` (layout A: rotation-aware Kodi executable `kodi-ios-portrait-r1`, Liquid Glass tab bar `kodi-glassbar-r1`, portrait Fuse windows, Continue Watching) is merged with the Deck "Choose a version" page and the drive.file sign-in deploy. The watch chooser keeps both sides: Continue Watching records the title it starts, and an Elementum choice leaves the title's details for the Deck page. Both pinned portrait downloads were fetched and verified on host before the build.

## ISSUE-062 — Portrait: Kodi drew a squashed landscape picture when started upright (build-74)
Status: FIXED IN PATCH; executable rebuild (kodi-ios-portrait-r2) pending, then pin.
- Phone log: the screen mode was 1206x2622 but Kodi started at 2622x1206 and never logged a rotation. Kodi creates its GL view once in loadView from the landscape frame it starts with, and the view does not autoresize; the patch only re-read the size in viewWillTransitionToSize, which iOS does not call when the app simply launches in portrait. The patch now also handles viewDidLayoutSubviews: whenever the GL view's size differs from the controller view's, it resizes the view and framebuffer and rebuilds Kodi's desktop resolution (same path as a rotation). The IPA keeps the r1 executable until r2 is built and pinned.

## ISSUE-063 — Pop-ups covered the portrait screen and were lost; owner wants them in the bell
Status: BUILT; Kodi app r10 compiled and pinned (r9 superseded, not pinned); IPA with r10 pending; device test pending.
- Owner screenshots (build-101): "Update available" and "TMDbHelper: Trakt authorized" pop-ups drawn as the landscape notification shrunk into portrait, cut off at the right and covering the Info button. Owner wants every notification kept in the bell under General, so failures at startup can be seen later, and chose "bell only, no pop-ups".
- Root cause: Kodi has no Python hook for other add-ons' toasts (`CGUIDialogKaiToast::AddToQueue` is internal), so the bell only knew the app's own messages.
- Fix: Kodi app r9 (`kodi-21.3-portrait.patch`, GUIDialogKaiToast.cpp) appends each pop-up as a JSON line (time, type, image, caption, description) to `addon_data/service.kodi.ios.bootstrap/toasts.jsonl` and does not show it. Owner follow-up ("never show up at start, straight to the notification area"): r10 creates that folder itself on a first start instead of showing the pop-up, and the `toasts.popups` switch is gone; a pop-up is shown only if it cannot be written at all, so nothing is lost silently. r9 (already building) has the earlier behaviour and is not pinned. The bootstrap service (`notices.ingest`, every 3 s, also during playback) renames the file before reading it and adds each entry to the bell: warnings and errors under Problems, the rest under General (new filter chip). Pop-ups from before the service starts are taken at its first pass.
- The app's own pop-ups that already wrote a bell message (update available, season downloads, Playing on TV) were removed.
- Regression protection: scripts/test_notices.py (ingest of good, broken and empty lines; types; resume of an interrupted take; General/Problems filters). The C++ change is compiled only by the macOS workflow; it is not proven until r9 builds and the owner sees pop-ups in the bell.

## ISSUE-064 — Video: Fuse's seek bar flashed up, taps only worked on the left, controls laggy (owner, build-104/106)
Status: FIXED ON HOST; tap fix in Kodi app r13 (published and pinned 23:22Z); tap root cause from code reading, not device-confirmed; device test pending.
- Owner report with screenshot: the old (Fuse) seek bar shows for a second when a video opens ("Seeking +00:09", clock and °F top right); tapping the video only registers on the left side of the screen; the play/pause controls don't respond and are laggy and glitchy.
- Seek bar root cause: Fuse's DialogSeekBar is visible on `Player.Caching | Player.HasPerformedSeek(2) | Player.Paused…`, so it appears at every start (buffering, the resume jump). Fix: `player_osd.seekbar_window()` replaces it in 1080i, in the controls' look, shown only while the owner seeks (`Player.Seeking | Forwarding | Rewinding | SeekNumeric`) and never with the controls open; keeps Kodi's progress control 401.
- Layout risk found while reading Kodi: `CGUIDialogSeekBar` is `LOAD_ON_GUI_INIT`, i.e. loaded upright, where 1080i falls back to Fuse's 16:9 res (1920 wide); the r8 reload only compared folder names (`strMode` is "1080i" for both the 1920 and the 2340 layouts). A window kept at 1920 but drawn from 2340 coordinates puts everything right of 1920 off-screen. Fixes: the controls (player controls r3) and the seek bar are pinned to the left edge / centre (`centerleft 50%`) / right edge instead of fixed 2340 coordinates; Kodi app r12 also reloads a dialog when the wanted layout's width or height differs, not only its folder.
- Taps, likely root cause (owner asked to investigate, not yet device-confirmed): Kodi's touch path passes view pixels straight through with no clamping, so the limit must be UIKit's: a touch reaches a view only inside the bounds of every view above it. Kodi makes its UIWindow with a fixed frame (`initWithFrame:[screen bounds]`, autoresizing off). If the window or the controller's root view stays at the portrait size (402 pt wide) in landscape (874 pt) while the GL view is stretched to full size (r7), the picture fills the screen but only touches left of 402/874 = 46% are delivered: the video centre (play/pause at 50%) and the top-right buttons are just outside, the back button inside. Same 46% as the earlier "left 46% drawn" state.
- Fix in Kodi app r13: the window (KodiTouchWindow) and root view (KodiTouchRootView) accept every point of the screen and of their visible subviews whatever their own size, so touches always reach the GL view; the half-second size check also compares the root view's size. r12 (built from the previous commit) only has the tap logging: the first 12 taps after every change of screen shape with tap position, scene/window/view/GL-view sizes, scale, Kodi's size and the active window. r13 keeps the logging, so a failure there still shows its cause in kodi.old.log.
- Lag: during fullscreen video the bootstrap no longer runs the focused-item publisher (up to 10 GUI-locked infolabel calls every 0.5 s) and polls the tab bar every 0.5 s instead of 20 times a second. Elementum streaming itself also uses the CPU; not measured.
- Regression protection: test_portrait (seek bar conditions, single control 401, no fixed x beyond 1920 in the controls or seek bar).

## ISSUE-065 — Arctic Fuse splash at startup; slow start
Status: FIXED ON HOST; device test pending.
- The "KODI Arctic Fuse 3 — Reticulating Splines…" box over Home is Fuse's startup dialog (Custom_1198_Dialog_Startup.xml), shrunk into portrait, visible up to 59 s (SplashTimeOut). The portrait folder now has an invisible window 1198 (`<visible>false</visible>`), so Fuse can still keep its startup properties there.
- Start work removed: (1) the portrait refresh rebuilt every portrait window (≈300 Fuse files parsed, textures drawn in Python) at every start; it now runs only when an input changed (fingerprint of this code, Fuse's 1080i files except the two written here, addon.xml, the widget lists; stored in addon_data/service.kodi.ios.bootstrap/portrait-inputs.json). (2) Fuse's `Startup.EnableHubPreloading` (opened each hub window in turn) is reset and `Startup.DisableWaitForLoad` set (its splash script re-ran every 0.5 s for up to a minute while widgets loaded).
- Not measured on the phone; widget loading (TMDb Helper, add-on requests) remains the main cost.
- Regression protection: test_portrait (splash window, unchanged-refresh skipped, own 1080i writes are not inputs, a Fuse file change is).

## ISSUE-066 — Continue Watching asks for the player and version again
Status: BUILT ON HOST; device test pending.
- Owner request: resuming from Continue Watching should reuse the provider and quality picked the first time; a long press should allow picking again.
- Continue Watching links carry `ios_continue=1`; TMDb Helper passes unknown parameters on (its Player takes **kwargs) and the watch menu, running inside its resolver, reads it from sys.argv. The store (continue.json) keeps per title the player (elementum / umbrella / local) and the version picked on the "Choose a version" page (release name, quality, size; written by deck_picker.remember for the title just started, ≤15 min old and matching title). A Continue Watching tap skips "How would you like to watch?" and the version page finds the same release name (quality as tie-break) and plays it; if it is gone, the normal page shows. A normal tap anywhere else always asks.
- Long press › Choose source (context item on phone entries) forgets the saved pick and plays the item as a tap does, so the new pick is remembered.
- Not covered: Elementum's own list (≤5 links or "Show all") — the choice there is not seen, so the next resume asks again.
- Regression protection: test_watch_dialog (reuse, normal play still asks, no saved pick asks), test_watch_continue (kept while the same player, dropped on another, forget, context action), test_deck_picker (same version without asking, stale/missing falls back, remember only for the title just started).
- Owner retest of build-111/112 (2026-11-01 ~23:40Z, Logfile Uploader paste, kept outside Git): video plays, but play/pause and back/forward 10 still do not respond, the controls are laggy, and one later show crashed. The r13 tap log DISPROVES the window-size theory: in landscape scene, window, root view and GL view are all 874 x 402 pt and Kodi 2622 x 1206; taps arrive at the touched pixel, in VideoOSD (12901), one exactly on the back-10 button's area (877 x 523 px), and a top-left tap stopped the video. So the remaining cause is after the tap reaches Kodi (button action not taking effect, or the GUI thread too slow to show it); not yet known. The log also shows two "OutputPicture - timeout waiting for buffer" warnings (render loop stalling; hardware decoding was in use: CVBREF render method). The uploaded log is the session after the crash, so the crash itself is not in it.
- r14 (native): the tap log no longer asks the window manager for the active window from UIKit's main thread (that took Kodi's graphics-context lock, which the render thread holds while it may wait on the main thread: a freeze that iOS kills, a likely candidate for the crash). Builds now run on pushes to main as well as pull requests (PR #1 is merged).
- Evidence needed next: the crash (iOS Settings › Privacy & Security › Analytics & Improvements › Analytics Data › newest "Kodi…" report, or kodi.old.log uploaded right after the crash), and a debug log (Settings › System › Logging › debug logging on) of: play, open controls, tap play/pause, wait 3 s, tap forward 10, stop.

## ISSUE-067 — Crash when a video starts (owner, build-111/112)
Status: FIXED IN PATCH (Kodi app r15, building); device test pending.
- Evidence: the owner's iOS crash reports (kept outside Git). Kodi-2026-11-01-154021.ips and -154056.ips: EXC_BAD_ACCESS (SIGSEGV) on XBMC_Run (Kodi's render thread) inside the GL driver: `glDrawArrays` from `CLinuxRendererGLES::DrawBlackBars` ← `CGUIWindowFullScreen::Render`, faulting in `GLDContextRec::beginRenderPass` (`getTextureResource` / `addResource` on a null resource): the bound framebuffer's attachment was no longer valid. -154737.ips is not a playback crash: SIGKILL while the app was being closed (main thread in `-[IOSEAGLView stopAnimation]`, XBMC_Run in `CApplication::Stop` waiting in `CPythonInvoker::stop` for a service add-on to stop), i.e. a slow exit.
- Root cause (from the code): since r11 every rotation called `[m_glView setScreen:… withFrameBufferResize:YES]` on UIKit's main thread. `resizeFrameBuffer` compares the framebuffer size in pixels with the view size in points, so it always asks for a resize, and `layoutSubviews` then deleted and recreated the framebuffer on the main thread, making Kodi's EAGL context current there while the render thread was drawing with it. Two threads using one GL context: the next draw crashes in the driver. Video start is a rotation, hence "crashes when I play a video", not every time.
- Fix (r15): `-[IOSEAGLView recreateFramebuffer]` rebuilds the framebuffer on the calling thread; `ApplyRotatedScreen`, which already runs on Kodi's application thread (the render thread), calls it first; the main thread only sets frames and the content scale (`withFrameBufferResize:NO`).
- Not addressed yet: the slow exit (a Python service add-on not stopping when Kodi closes).

## ISSUE-064 follow-up — owner debug log (2026-11-01 16:00 local, build-111/112, kept outside Git)
- The OSD buttons work: the tap on back-10 (891 x 551 px) was followed at once by `demuxer seek to: -4382.77`. The seek failed because the stream was a raw Blu-ray `00030.m2ts` of about 72 GB from a debrid host: no index, so the file cache jumped to byte 4 and then to the end of the file ("seek failed or hit end of stream"), with "stream stalled" / caching meanwhile. Neither control tap was on play/pause (both at 891 px = back-10; play/pause is the centre, about 1311 px). Open: a screenshot of the controls to confirm the drawn positions match; raw .m2ts / BDMV sources are a poor fit for phone streaming. Both owner logs played the same file: ffmpeg reports HEVC Main 10, 3840x2160 HDR (bt2020/smpte2084), 63 Mbps, raw UHD Blu-ray .m2ts — the stalls, the frozen controls while Kodi waits on the stream and the failed seeks all follow from it. Owner (02:20Z): "all the buttons don't work, it really lags out". Fix: deck_picker.too_heavy (disc copies: m2ts / BDMV / ISO / complete Blu-ray; or > 40 GB) lists them after the versions a phone streams well, labelled MAY STUTTER (still offered). A Continue Watching pick already saved for such a file is reused until long press › Choose source. Device test with a normal source pending.

## ISSUE-068 — Elementum stopped answering after the app was in the background
Status: FIXED IN BUILD SCRIPT; device test pending.
- Log: `JSONRPC Server: Accept of new connection failed: 9` (Kodi, recovers by itself) and an Elementum traceback `server_thread … accept() … OSError: [Errno 9] Bad file descriptor` at the same moment: iOS closed the listening sockets while the app was suspended; Elementum's RPC thread died, so its dialogs (including Choose a version) could not open again until Kodi restarted.
- Fix: scripts/build_customized_ipa.py patches elementum/rpc.py `server_thread` to make a new server and serve again until Kodi exits (checked against the pinned 0.1.114 client: all Elementum patches apply and compile).

## ISSUE-069 — Umbrella showed its own source list after the Choose a version page
Status: FIXED ON HOST; device test pending.
- Debug log: after the Deck page closed, `EXCEPTION: Window id does not exist`, then Umbrella's own source window opened and the owner picked a second time. The r1 hook called `self.clearProperties()` on Umbrella's never-shown window; the exception fell through to `self.doModal()`.
- Fix: hook r2 returns the Deck choice without touching Umbrella's window; phones with the r1 hook get it replaced in place at the next start. Test: test_deck_picker (r1 → r2 upgrade, Umbrella window never shown).

## ISSUE-070 — Errors logged at every start (missing folders, network discovery)
Status: FIXED ON HOST (once per phone); device test pending.
- `GetDirectory - Error getting special://profile/media/local_media_root_04/` (a Deck source and home row pointing at a folder that does not exist here), TMDb Helper's missing `reconfigured_players`, Elementum `lsd_error_alert` / `portmap_error_alert: no router found` / NAT mapping time-outs, and Kodi `CZeroconfDarwin … -72008` (Bonjour publishing refused by iOS).
- Fix: `bootstrap.phone_housekeeping`, once per phone (marker): creates the media folders named in sources.xml and TMDb Helper's players folder, turns Elementum's UPnP / NAT-PMP / LSD off and Kodi's zeroconf off. A setting the owner turns back on stays on. Test: test_updates_calibration.
- Left as is (upstream, harmless): Fuse's AddonBrowser uses an undefined include `Settings_InfoText` ("unsupported control type 7"); `skinvariables-…-standard-onunload` includes missing for hubs without generated widget rows; "startup.xml taints init process"; "Could not parse type Setting.Details.SettingList"; Umbrella's player monitor asking the time after a stop.

## ISSUE-071 — "Script invoked without an addon" when opening the bell, Accounts, Play on TV, speed
Status: FIXED ON HOST; device test pending.
- The phone's buttons ran their scripts by file path, so Kodi could not tell the add-on and put every installed add-on's modules on the Python path first (slower to open). The setup add-on's script entry is now default.py, a dispatcher: `RunScript(service.kodi.ios.bootstrap,<page>[,args])`; without a page it is still recovery. The generated skin files use it; menu entries already saved by navigation keep the old (working) form. Test: test_portrait (every RunScript names a page default.py knows, and the page exists).

## ISSUE-072 — Custom windows parsed twice at every start
Status: FIXED IN PATCH (Kodi app r16, building); device test pending.
- ~40 × `No id specified or id already in use for custom window in Custom_*.xml`: LoadCustomWindows reads the portrait folder then 1080i and parsed every 1080i copy in full before refusing it. r16 skips a file name already loaded from an earlier folder before reading it (same windows result, no second parse).
- Owner (02:30Z): the file itself plays fine; the buttons are what does not work well. Kodi app r17 logs every tap on a window as "Click at X x Y in <window> (<W> x <H> layout): control <id> (handled/not handled)" — the skin coordinates after Kodi's transform, the layout the window was loaded with (1920 vs 2340 wide) and the control that took the tap. Next: owner test on the r17 build (open the controls, tap play/pause three times two seconds apart, tap forward 10 once, close) + Logfile Uploader link + a screenshot with the controls up.

## ISSUE-073 — Library showed nothing; downloads only reachable through the gear menu's Google Drive browser
Status: BUILT ON HOST; device test pending.
- Owner (2026-11-02, screenshot of an empty Library › Movies): kept downloads live in Google Drive (uploaded by driveupload.py, the phone copy removed), so they "need to be linked to Library, not gear → Drive". Library › Movies / TV Shows listed only Kodi's own (empty) video library.
- Fix: Library opens `plugin://plugin.video.kodi.ios.watch/?action=library&type=movie|tv` (ios_library.py): Kodi's library items plus Google Drive › Kodi Downloads › Movies (video files, release subfolders included, samples left out) and › TV Shows (one folder per show → its episodes in SxxEyy order). Titles, years and SxxEyy come from the release names; posters, backgrounds and plots from TMDb (TMDb Helper's API key read from its add-on at run time; cached in addon_data). Playing goes through the Google Drive add-on (`plugin://plugin.googledrive/?action=play&…&item_id=<file>`), which streams from Drive. Listings are cached 5 minutes; a finished upload clears the cache. drivelibrary.py (bootstrap lib) holds the Drive / naming / art logic; test: scripts/test_drive_library.py (names, paging, folders, art cache and retry, rows).
- Needs the Google Drive add-on signed in (as for the uploads). Not yet seen on a device.

## ISSUE-074 — Video controls drawn in a narrower box than the video; the separate bar still appears
Status: FIXED (Python now; Kodi app r18 building); device test pending.
- Owner screenshots (02:55Z, landscape video): the controls' shade, bar and top-right buttons stop about 7% short of each side and the separate seek bar (ours since r3) still pops up, its times cut off; "it doesn't match up right". Cause: Kodi maps the GUI into the iOS safe area (`insets: {0, 62, 21, 62}` pt in landscape → 186 px each side of 2622; CGraphicContext::GetGUIScaling) while the picture fills the screen. The logged taps do land on the drawn buttons (891 x 551 px = the drawn back-10).
- Fix: Kodi app r18 sets no GUI insets during landscape video (and clears them when the safe area is zero; upstream returned and kept the old ones), so the controls cover the same screen as the picture. Player controls r4: 150-unit margins clear of the rounded corners and the Dynamic Island; the seek bar window never shows (kept for Kodi's progress control 401).
- Still open: whether the buttons then act reliably — r17/r18 log every tap's skin coordinates, layout size and control.

## ISSUE-064 follow-up 2 — owner log pasted in chat (2026-11-02 03:45Z, kept outside Git)
- The Logfile Uploader failed ("unable to retrieve the paste url", the debug log is too big for paste.kodi.tv); the owner pasted the log into chat. It contains a Trakt bearer token (TMDb Helper scrobble error) — not copied anywhere.
- Built before r16: the 40 "id already in use" custom-window errors are still there and no "Click at" line (r17) appears, so the phone was not on build-120 (published 03:39Z, six minutes before this session).
- What the taps did (Elementum, Scary Movie, 1080p HEVC mkv): tap 1 opened the controls; taps at 912 x 552 and 857 x 572 px each ran Seek(-10) (30 s → 20 s → 10 s; Elementum's "Watched" agrees) — with the r15 safe-area mapping the drawn back-10 spans about 792–1023 px, so both taps hit the button under the finger. Three taps top-left: the first two fell just outside the back button's hit box (too low, then too far left, with the 186 px inset), the third stopped the video. The buttons respond; what feels like lag is ISSUE-075.
- Next: the same test on build-120 (r18: no insets during video, every tap logged with its control).

## ISSUE-075 — Elementum stream: audio stops for seconds after start and after each seek (owner log, 03:45Z)
Status: OPEN; needs the build-120 log to confirm.
- 2 s after the video started (right after the rotation to landscape) `CVideoPlayerAudio::Process - stream stalled`; no audio for 9 s until `audio stream stalled, triggering re-sync` (VideoPlayer flushed and re-seeked). Elementum also asked Kodi to seek to 0 three times at start (`OnPlay. Triggering Seek to 0`).
- After the two back-10 seeks: `ActiveAE - large audio sync error: 8018` for 3 s, then `CDVDAudio::AddPacketsRenderer - timeout adding data to renderer` ×3; closing the video waited 2.2 s for the audio thread, so the next tap went through to Home and opened another title.
- Torrent had 4 peer connections (`Con: 0/350 + 4/1200`); the audio sink was reopened from 44.1 kHz float to 48 kHz 16-bit only at the re-sync. Candidates: torrent pieces not arriving (starved demuxer), the audio sink not reconfiguring when playback starts during rotation. Next: compare with a debrid (Umbrella) mkv and a downloaded file from Library (Drive) on build-120.

## ISSUE-064 follow-up 3 — desktop simulation of the controls (2026-11-02 04:10Z)
- Owner (04:00Z): the stream is fine; pause, AirPlay, subtitles and Continue Watching do not work — "the buttons must not be linked to the player". ISSUE-075 (stream) is the owner's call against; kept only as log evidence.
- Simulated in a real Kodi (Debian Kodi 20.5 — the phone runs 21.3 — under Xvfb at 2340 x 1080) with Arctic Fuse 3 (current main, dependencies stripped), our generated 1080i VideoOSD.xml / DialogSeekBar.xml, the ios-touch keymap, the bootstrap add-on (service off) and a 5-minute test mkv with an .srt, played from a file and over HTTP. Taps sent as left clicks (what a touch tap becomes through the keymap):
  - tap on the video → Fullscreen OSD (12901);
  - play/pause → Player speed 1 → 0 (paused), tap again → 1;
  - CC → Subtitle OSD settings (10159), subtitle drawn;
  - Continue Watching → Skin.HasSetting(ios_osd_continue) true, path set, row shown ("Nothing in progress yet": watch add-on not installed in the rig);
  - AirPlay → "Kodi iOS Play on TV: opened", "Looking for TVs on this Wi-Fi..." progress dialog, then "No TV answered" (no network in the rig).
- So the controls' XML drives the player in Kodi; what fails on the phone is in the iOS app or its input. The 03:45Z phone log has no tap on play/pause (two taps on back-10, which sought, then the back button). Next: build-120 log with the "Click at" lines for a pause tap, CC, AirPlay, Continue Watching.
- AirPlay opens our network search first (several seconds), not Apple's AirPlay sheet; offer the owner the iPhone's own AirPlay picker instead.

## ISSUE-064 follow-up 4 — taps right of the portrait width never reach Kodi (root cause of the dead buttons)
Status: FIXED IN PATCH (Kodi app r19, building 06:56Z, run 41403074559); device test pending.
- All three owner logs (15:43, 16:00, 19:45 local): every landscape tap logged by the tap recognizer is left of 912 px of 2622 — under the portrait width (402 pt = 1206 px). Portrait taps span the full width. The owner certainly tapped play/pause (centre, 1311 px), forward 10 and the top-right CC / AirPlay buttons: none of those taps was logged, so they never reached Kodi. Back (≈300 px) and back-10 (≈900 px) are inside the reachable part — exactly the two that worked.
- The r12/r13 fix (window and root view accept every point) was not enough: the logged sizes of window, root view and GL view are all landscape, so the view or UIKit path still at the portrait size is not identified.
- r19 does not depend on finding it: KodiTouchWindow.hitTest returns the GL view (which has Kodi's gesture recognizers) whenever nothing below the window claims a point on the screen; and a UIApplication.sendEvent: hook hands a short single tap that reached no Kodi view (no view, a bare window or the root view) to Kodi as a tap, as the tap recognizer would. Real views under the finger (Liquid Glass tab bar, AirPlay button, keyboard) still get their touches. The first 12 taps after each screen-shape change are logged as "Touch at X x Y pt went to <view> … Kodi has it / handed to Kodi / left to that view", with the Kodi window's frame — the next log shows which path a tap took.
- Desktop simulation (follow-up 3) had already shown the buttons themselves drive the player.

## ISSUE-076 — Tapping the tab bar sometimes opened the Continue Watching item behind it (owner, build-122)
Status: FIXED IN FRAMEWORK SOURCE (KodiGlassBar r2, building); device test pending.
- The native glass bar took touches only on its 62 pt capsule. Kodi draws the hub rows behind and around it: 14 pt each side, the home-indicator area below (about 38 pt), and the Continue Watching posters just above. A tap that missed the capsule by a little went to Kodi and opened the item under it.
- Fix: KodiGlassBar.pointInside claims the whole strip from 12 pt above the capsule to the bottom edge, edge to edge, like iOS's tab bar; the tab follows the finger's x (end tabs clamped). Not claimed while the bar is hidden or faded out (dialogs, landscape).

## ISSUE-077 — Downloads and Drive uploads stopped whenever Kodi left the screen (owner request)
Status: BUILT (Python + KodiAirPlay r3, building); device test pending.
- iOS suspends an app seconds after it leaves the screen; Kodi only stays running while it plays sound (Info.plist already has the audio background mode). The Elementum engine and the Drive uploader run inside Kodi, so they stopped.
- Fix: background.py tells KodiAirPlay.framework (kodi_background_keep) every 5 s whether an Elementum download is running, a Drive upload is in progress, or kept videos wait for Drive. While that holds and Kodi is in the background, the framework plays silence on a loop with MixWithOthers (other apps' sound carries on), restarts it after a call, and restores the audio session when Kodi returns or the work ends. Not used while Kodi plays music. Setting: Google Drive › "Keep downloading and uploading while Kodi is in the background" (on). Swiping Kodi away still ends everything (iOS rule).

## ISSUE-078 — Vertical scrolling on Home/Movies/TV moved one row per swipe and jumped mid-flick (owner: "scrolling can be optimized")
Status: FIXED IN PATCH (Kodi app r20, building) + keymap; device test pending.
- The keymap from ISSUE-043 still mapped one-finger swipes up/down to Down/Up on Home, Library and Search. Since r5/r6 a vertical drag over a row already scrolls the page list, so every flick did both: the page glided, then jumped to the next focused row. A drag starting on the hero did not scroll at all (its list sits in a plain group; the handoff only looked at the direct parent).
- The direction was decided from the first pan step (a few pixels, noisy).
- Fix: r20 sends the finger's whole movement so far with the start of a drag (UIKit waits about 10 pt). A list (or a group list) leaves a drag across its own direction to the nearest group list above it that scrolls the other way, through plain groups. Row swipes removed on Home (all three hubs), Library and Search; kept on Fuse's other hubs and the info page.

## ISSUE-079 — AirPlay connected but showed 0:00–0:00, no picture or sound (owner, build-122)
Status: BUILT (Python + KodiAirPlay r3); device test pending.
- Play on TV › AirPlay stopped Kodi and handed the stream to Apple's player (AVPlayer, external playback). Apple's player opens MP4/MOV/HLS only; Elementum streams are nearly always MKV, so it never loaded (0:00–0:00), and Kodi's playback was already gone. It also needs the phone's Wi-Fi address to answer (not verified for Elementum's engine).
- Fix: an MKV (or any non-Apple) stream gets Screen Mirroring steps and Kodi keeps playing. iOS mirroring carries Kodi's picture and sound to the TV, whatever the format; apps cannot start mirroring themselves. For MP4/HLS, Kodi pauses and Apple's player tries for up to 25 s (r3 kodi_airplay_state): on success Kodi stops; on failure the player closes, Kodi resumes, and the mirroring steps are shown.
- Possible later improvement: while mirroring, move Kodi's output to the TV at its own resolution (Kodi's external-screen mode; videoscreen.monitor) for a sharper picture.

## ISSUE-080 — Download › episodes: no quality page, no "watch" option; it just closed (owner, build-122)
Status: BUILT (Python); device test pending.
- Elementum's download action does show its version list (ListDialogLarge → the Deck "Choose a version" page) unless it skips it, and its defaults skip it in three cases: a version picked earlier for the title is reused (use_cache_selection); a torrent on the phone that already holds the episode is reused silently (smart_episode_choose, e.g. a season pack streamed before); its "use that one?" question answers Yes by itself after 5 s (autoyes_enabled). Pinned engine cdab7e2 api/shows.go ShowEpisodeLinks, api/torrents.go InTorrentsMap.
- Fix: once per phone (housekeeping 'elementum_always_ask'), use_cache_selection, smart_episode_choose, autoyes_enabled and silent_stream_start go off, so Elementum always shows its version page and waits for an answer. Set once, not around each download: every Elementum settings change reconfigures its engine. Continue Watching keeps its own saved pick (ISSUE-066).
- New choice after the episodes (or movie, or full season): "Download only" / "Download and watch". Watching starts the download first (quality and version pages), then plays from that same torrent once Elementum adds it (movie: /play?resume=<torrent>; episode: the episode page with silent=1). With several episodes every version is chosen first, then the first episode plays, so no page opens over the video.

## ISSUE-081 — After AirPlay, Kodi drew only the left 46% of the screen and no text (owner screenshots, build-122)
Status: FIXED IN SOURCE (KodiAirPlay r4 + Kodi app r20); device test pending.
- 46% = portrait width ÷ landscape width (402/874 pt), and text was gone while pictures still drew full width: Kodi was left half-switched between landscape and portrait. Apple's player (Play on TV › AirPlay) was presented full screen and allows landscape; iOS turned the phone and took Kodi's view off the screen, so Kodi never saw the turn back (no viewWillTransitionToSize; its size check found the window, root and GL view sizes in step).
- Fix: KodiAirPlay r4 shows Apple's player inside a holder that keeps Kodi's current orientation, presented over Kodi (Kodi's view stays), with a close button; when it closes it calls XBMCController applyRotatedScreen (twice, 0.8 s apart). Kodi r20: whenever Kodi comes back on screen after a full-screen presentation (viewWillDisappear → viewDidAppear), it rebuilds its framebuffer, resolution, fonts and layout. That also covers other full-screen sheets.

## ISSUE-082 — Search: field at the top, results as you type (owner request with Apple TV app screenshot)
Status: BUILT (KodiGlassBar r3 + Python + portrait layout); rig-rendered; native field compile-checked only, device test pending.
- Held back for a while (37331e3) so it ships with the UI round 2; restored with that merge (KodiGlassBar r3 pinned again).
- Before: the Search field opened TMDb Helper's search, which showed Kodi's keyboard page ("Enter Search Query" on black).
- Now (Apple TV app style): a native iOS search field in a dark band at the top (magnifier, clear button, round X), typed with iOS's own keyboard. searchbar.py reads it twenty times a second and, once typing pauses for 0.45 s (at once on the Search key), points the page's poster grid (3 a row) at TMDb Helper's multi search; X clears it and lowers the keyboard; dragging the results lowers the keyboard. The category tiles show while the field is empty. A phone without the r3 framework keeps the old field.
- Rig check (desktop Kodi 20.5, Fuse 3.4.8 at 603x1167, the phone's portrait safe area; native field not drawn there): old layout unchanged; native mode puts the categories under the band; "scary movie" lists 12 TMDb results in the grid ("No results"/"Searching…" states included); tapping a result runs TMDb Helper's play (the player chooser), as the Home rows do. Kodi 20.5 in the rig crashed once in Python teardown of Fuse's skinvariables script (rig-only, Python 3.12).

## ISSUE-083 — AirPlay could not play MKV (and AVI, WebM, MPEG-TS): only Screen Mirroring steps (owner brief)
Status: BUILT ON HOST; device test pending. Branch feature/airplay-mkv-remux (not merged, no release, no PR).
- Before: Play on TV › AirPlay handed the link to Apple's player, which opens MP4/MOV/HLS only; MKV showed Screen Mirroring steps.
- Now (KodiAirPlay r5): kodi_airplay_play() keeps MP4/MOV/HLS direct. MKV/AVI/WebM/TS, and links without an extension whose bytes are not MP4 (Drive), go through a remuxer on the phone: GMPlayer's C core (MIT) on a remux-only LGPL FFmpeg 8.1.1 cuts the file into fragmented-MP4 HLS segments on demand (video never re-encoded); DTS, TrueHD, FLAC, Opus and Vorbis are re-encoded to AAC (stereo or 5.1); text subtitles (SRT/ASS) become WebVTT renditions (picture subtitles such as PGS are not offered). The Apple TV fetches the segments itself, so the server listens on the phone's Wi-Fi address on a port the system picks, with a random 128-bit token in every path (404 without it). It reads the source with Range requests (Elementum 127.0.0.1:65220, Drive links).
- Failures never hang silently: the framework sets state -1 with a reason (kodi_airplay_message) that Kodi shows with Screen Mirroring steps; a converted stream that fails or stalls 20 s while the remuxer reports an error shows an "AirPlay stopped" alert. The server, its sockets and source connections stop when Apple's player closes, on a new play and on kodi_airplay_close. A video Apple cannot decode (VP9, AV1 in WebM) or audio that cannot be converted gives a message instead of silent playback.
- Host tests (migration/airplay-ios/remux/tests, CI airplay-remux.yml): 574 checks on generated H.264, HEVC HDR10, AAC, AC-3, DTS, TrueHD, SRT, ASS and MPEG-TS files, from files and over HTTP with Range: playlists, segment boundaries, audio timeline without gaps, seeks, token, errors, shutdown; scripts/test_airplay_remux.py for Kodi's routing.
- Not verified: AVPlayer/Apple TV accepting the stream, lock screen and background behaviour, the iOS build itself (macOS CI job added, not run yet from here), timings on real files, 7.1 sources (down-mixed to 5.1), Dolby Vision (profile 5 will not show correct colours on SDR fallback).
- Phone tests needed: MKV H.264+AAC; HEVC HDR; DTS audio; TrueHD; subtitles on and off; seek; pause/resume; lock the phone; Elementum stream; Drive file; AirPlay to Apple TV; AirPlay to a speaker.

## ISSUE-084 — Build 133–136 feedback: AirPlay without picture, slow start, downloads (owner)
Status: FIXED IN SOURCE (build 137); device test pending.
- AirPlay (build-136 log): Python stopped Kodi's video 7 ms after Apple's player reported "playing"; the app rotated to portrait under Apple's player (cut-off controls) and the TV (TCL Roku TV, "MFi_AirPlay_Device") hung up on video and audio, AirPlay off 4 s later. Kodi now stays paused. KodiAirPlay r8: third-party receivers get an H.264 picture (VideoToolbox) from the first request; early-dropout fallback restart; segment cache, prefetch and parallel audio/video; Apple's player follows the screen orientation.
- Start: the preloader is back (every hub row loads when Home opens); the tab bar starts before the bootstrap's 2 s wait; TMDb Helper keeps its Python interpreter between lists (reuselanguageinvoker), so only the first list pays the 2–3 s start.
- Full-season download: Elementum's redirects after the version page are followed over HTTP (they were dropped with RunPlugin). Downloaded titles play from Kodi Downloads when opened from Home.
- Reverted after build 134: the listing cache (Home showed no rows) and the collapsing show-page header (jumped instead of scrolling).


## ISSUE-085 — Empty generated widget unload include is rejected by Kodi
Status: FIXED ON HOST; device test pending.
- Owner startup log (2026-11-04, line 331) reports `skinvariables-homewidgets-standard-onunload` unavailable.
- Pinned Fuse 3.4.8 template `widgets_standard_include.xmltemplate` emits a named include even when no combined widget needs cleanup. Kodi 21.3 `CGUIIncludes::LoadIncludes` registers a named include only if it has a child; an empty generated include is ignored, then Home's reference warns.
- Fix in navigation.py: normalize existing empty `skinvariables-*-standard-onunload` definitions to an empty `<definition />`, and wrap the template's future cleanup actions in `<definition>`. Real cleanup actions, unrelated includes and widget definitions are preserved. Normal backed-up navigation upgrade applies to existing profiles; no profile reset.
- Three new navigation regressions cover empty/nonempty output, future generation, idempotence and repair of existing generated files.

## ISSUE-086 — Repeated iOS audio INIT is not acknowledged when already configured
Status: FIXED IN PATCH; full iOS build and device verification pending.
- Startup log line 292: signal 0 on OutputControlPort in state 7. Pinned Kodi's protocol identifies 0 as INIT; state 7 is CONFIGURED_IDLE (the enum's old comments are off by one). Configured idle/play inherit CONFIGURED but none acknowledged INIT, so it reached the unhandled warning.
- CActiveAE::Resume uses a synchronous INIT with a five-second reply timeout. Whether this particular logged request came from Resume or an asynchronous startup retry is NOT established; no timeout error appears in this capture.
- Fix: iOS CONFIGURED handles INIT by replying ACC without restarting the sink. SUSPENDED still handles INIT in its more-specific state and performs its normal reconfiguration. Other platforms unchanged.
- C++ host branch checks exercise repeated iOS replies, non-iOS behavior and unrelated signals. Full patch applies to pinned `a3a448d26b8d560a65655dab2cd122994dc4e146`. These are stubbed branch tests, not a full ActiveAE integration or Apple SDK compile.
- The first host harness incorrectly used an int return for a void handler; corrected the harness, then all tests passed. Staged build tag r22; verified executable pin stays r21. No build run or IPA requested.

## ISSUE-087 — Expected JSON-RPC schema dependency is logged as a parse warning
Status: DIAGNOSTIC CORRECTED IN PATCH; iOS build/device pending.
- Setting.Details.SettingList refers to Setting.Details.Setting, whose union in turn includes SettingList. The existing resolver intentionally defers the forward reference and resolves it later; the supplied log confirms successful JSON-RPC v13.5.0 initialization.
- Log expected missing-reference deferral at DEBUG; retain WARNING when parsing fails without a missing dependency. Resolver behavior and INFO dependency-registration messages remain. A compiled host branch test checks both classifications; no claim that a failed RPC was repaired.

## ISSUE-088 — Opening Kodi until posters appear is slow
Status: PARTIAL HOST FIX; end-to-end iPhone cause and timing remain open.
- Owner clarified the problem is opening Kodi until posters appear, not switching already-preloaded tabs. Historical 0.1–0.2-second numbers describe tab switching, not full app launch. Supplied log reaches Home.xml after 1.100 s and running application after 1.175 s, then ends at 5.795 s without custom bootstrap/cache diagnostics or a first-poster measurement.
- Found redundant work: service.py calls navigation.upgrade twice per startup; each re-read/parses the skin files and generator templates even when unchanged. Add a source/code/keymap fingerprint to skip repeated parsing. File additions/removals/replacements, template/XML edits, keymap edits and code updates invalidate it. Keymap/skin symlink checks remain; invalid marker JSON falls back to the full scan. Backups and actual repairs remain.
- Repeatable isolated benchmark: scripts/bench_startup_checks.py on text-only pinned Fuse (223 XMLs, 19 templates), five samples, two upgrade calls/sample, current portrait generator used for both variants. Median 0.266 s before versus 0.0175 s after. This measures the navigation subsystem on Linux only. First repair/update still scans; no iPhone or first-poster speedup claimed.
- Full portrait regeneration separately measured around 2.5 s on this host, versus ~0.003 s for an unchanged portrait fingerprint; regeneration/reload can discard preloaded rows. Not proven to recur on this phone.
- Cached feeds still require a Python plugin (one per row/hero); uncached feeds invoke TMDb Helper. Background copies begin after 20 s and may not all exist after a brief first session. No capture here establishes actual cache coverage, Python-entry latency or time to rendered poster textures.
- Add bounded startup-only list readiness milestones (hero/first provider row, at most 60 s), bootstrap stage/import timing, portrait refresh duration and cache-hit timings. Logs contain stage names/keys/counts, no titles or stream URLs. List-item readiness is distinct from image rendering. Preloader retained; no lazy-hub rollback.
- Evidence and 361 passing host tests/25 suites: reports/startup-followup-validation.json. Next: a complete startup capture extending until posters appear, then separate bootstrap delay, rebuild/reload, cache miss/live TMDb work and image decode. No IPA built.

## ISSUE-089 — Startup iOS audio underrun
Status: OPEN; warning intentionally preserved pending diagnosis.
- Supplied log line 358 reports 7456 available bytes for an 8200-byte callback. The preceding startup negotiates 44.1 kHz float input over a 48 kHz hardware route; Kodi explicitly allows Core Audio resampling, so that fact alone is not an error or proof of the underrun's cause.
- Pinned AESinkDARWINIOS renderCallback logs actual ring-buffer shortages. The log has no playback event, repeat pattern, audible symptom, crash or callback timing. Startup/tail handling versus scheduling/producer starvation remains undetermined.
- Do not hide the warning, arbitrarily change sample rates or enlarge audio buffers based on this one line. A longer run/callback evidence is required before a root-cause fix can be claimed. Separate from the old ISSUE-075 playback/seek stall.


## ISSUE-090 — Bottom menu bar takes at least five seconds to appear
Status: SOURCE REORDERED; five host regressions pass, device timing pending.
- Owner reports the bottom navigation bar appears at least ~5 s after opening Kodi. This joins ISSUE-088's launch-to-posters complaint; the supplied log does not identify when the native bar appeared.
- Before: service.py imported the full bootstrap/generator/provider stack, then portrait.run_service initialized Continue Watching, the listing cache and GUI publishers before creating its native bar controller. The first tick waited another 0.5 s. Python runtime scheduling and native main-queue delay remain unmeasured.
- Now: a lightweight native_ui worker is started before the heavy setup imports. It requests the bar immediately before search setup or its first polling wait, then owns the bar/search field independently of provider/cache/layout work. ios_tabs.py supplies the same actions to the skin and native controller; there is one native owner. Recovery does not start a duplicate worker; standalone portrait service retains a fallback start. Missing/failed native frameworks restore the skin bar.
- INFO timestamps distinguish native worker entry, first native show REQUEST, full bootstrap entry and data readiness. A show request is not proof the UIKit view has appeared; Python startup and main-queue/UI work still need a phone capture. No fixed five-second win or restored 0.1 s launch is claimed.
- Five tests: immediate first show without provider/GUI modules, landscape exclusion, missing framework fallback, load-failure fallback, and early-entry/recovery contract. Existing glassbar/search actions and portrait generation regressions also run. No native framework changed and no IPA built.


## ISSUE-091 — Owner bug 1: Continue Watching redownloads a completed movie; retain Umbrella origin
Status: FIXED ON HOST / PINNED RESOLVER CONTRACT; device playback retest pending.
- Owner confirms the completed copy is playable in Google Drive / Library. Completed movies tapped in Continue Watching reopen Elementum buffering/downloading rather than use that existing copy. Attached screenshot shows this behavior for a reported completed movie. The owner also requires titles originally opened through Umbrella to resume through Umbrella. No new reproduction log was required to locate the source defects; the exact phone failure path is not yet established.
- Pinned TMDb Helper 6.18.1 source reveals an invalid local-player construction: `PlayerItemLocalMovie({'tmdb': ...})` supplies no `item.details`, which its real resolver accesses when building a ListItem. Use the proper movie/episode class with `player.dictionary`, retaining metadata and literal file/Drive actions. Reproduced the old AttributeError against the actual pinned resolver; corrected local movie, local episode and Drive paths pass that same resolver/ListItem contract with Kodi API stubs.
- Completed-copy checks now run before reusing the saved provider or asking for a player. Search the correct completed movie/show folder and the current app's standard Kodi Downloads location (covers stale absolute container settings); require a positive-sized matching file. Retain empty Elementum folder slots, exclude active-folder overlap from completed-folder claims, require 100% torrent completion for seeding files, and filter each matching file before choosing the largest completed version. Tighten title/year matching against unrelated titles/remakes/sequels.
- Continue Watching also checks the existing signed-in Drive › Kodi Downloads catalog, since the uploader defaults to deleting the confirmed phone copy. Use Drive's existing play route, without rescraping or presenting another download. Refresh cached misses before declaring the file absent; Drive HTTP failures are not treated as absence. Read requests use an eight-second timeout; uploads retain their existing 120-second timeout.
- Playing a completed local/Drive copy preserves the original provider and remembered version; record the playback location separately. With no completed copy, reuse the saved Umbrella/Elementum player. An unavailable saved provider or missing previously local copy stops with a message instead of substituting Elementum. A failed completed-copy lookup and TMDb resolver retry stop rather than start a replacement download. Ordinary explicit player selection can still change the chosen provider.
- Kodi iOS Watch Options version 1.4.2. Added 19 behavioral regressions; updated existing Drive, history and player tests. 140 affected host tests/12 suites pass; three checks exercise actual pinned helper resolver classes with dependency/Kodi stubs. Evidence: reports/continue-watching-validation.json. No live account/media access, native build, IPA or device success claimed. This fix remains in draft PR #8.
- Validation recovery: an old test asserted the literal text of a function call and failed after adding an argument. Replaced it with real routing/negative-path tests; retained the failure here rather than treating string presence as behavioral proof.
- Device acceptance after a separately requested build: (1) completed phone movie from Continue Watching, (2) Drive-only completed movie after phone cleanup, (3) Umbrella-origin title without a completed copy, (4) unavailable provider/offline Drive must not silently start Elementum, and (5) playback resumes at the expected position. Do not retest these changes on the unchanged build-141 and call that validation of this fix.


## ISSUE-092 — Search genre categories ignore Movies/Shows filter; lag during downloads
Status: CATEGORY ROUTES FIXED ON HOST; phone acceptance and multi-download lag remain open.
- Owner: Movies → Drama/Sci-Fi shows television series; Shows must likewise remain strictly television. Typed query + media filter already works (e.g. Lanterns) and must be preserved. Screenshot matches the hardcoded TV discovery path in every category tile; no extra reproduction log required to locate this source defect.
- Generated static tiles now condition their actions on the existing Portrait.Search.Type property at click time. Movies uses `discover/movie`, Shows uses `discover/tv`. Shared genre IDs retain their values; movie Sci-Fi/Fantasy maps to 878 OR 14, Action/Adventure to 28 OR 12, War to 10752. Reality and Kids are TV-only and hidden for Movies. All preserves existing TV-category behavior. No changes to typed-search routing/controller or the native search field.
- Pinned Kodi GUIStaticItem reads conditional item visibility and click actions; GUIAction snapshots matching conditions before execution. Checked against Kodi a3a448d26b8d560a65655dab2cd122994dc4e146. Pinned TMDb Helper 6.18.1's actual discovery translation methods retain media/genre constraints for all 22 supported routes with dependency stubs; no live TMDb/media requests.
- Found avoidable contention: tile artwork can invoke twelve background TMDb Helper listings on a first/stale Search visit. Publish cached artwork immediately, defer further cosmetic requests while off Search, a query is present, downloads/uploads are active, video plays or a modal is open; pace requests by 0.2 s and honor abort. Uses Notices.Active rather than adding engine polling. Existing artwork and tile gradients remain available while refresh waits. Cannot cancel an already-running listing. No evidence yet establishes all download-related lag causes or an actual phone speedup.
- Six new regressions cover all generated movie/TV routes, correct combined movie genres, TV-only visibility, cached artwork while blocked, abort and resumed/paced refresh. Existing typed-search, portrait, artwork, native UI, startup, notification, page, performance-budget and bootstrap tests are included in reports/search-categories-validation.json. Future requested CI runs include the new suite; this publication skips CI to honor the no-IPA instruction.
- Phone acceptance after a separately requested build: Movies → Drama/Sci-Fi must contain movies only; Shows → Drama/Sci-Fi must contain shows only; repeat switching types; verify typed search remains correct; compare search responsiveness with multiple active downloads and no downloads. Installed build-141 lacks these fixes. No IPA, native build, merge or device acceptance claimed; keep draft PR #8.


## ISSUE-093 — AirPlay forward seek stops; cancellation, 4K and format coverage
Status: SOURCE FIXES VERIFIED BY CLEAN HOST/SDK CI; actual Drive/TV performance, all-format acceptance and device verification remain OPEN.
- Owner supplied a screenshot (`video conversion: cancelled`) and a later playback log (1,565 lines, SHA-256 abc1311ef27c1fb8d970ad11e03c86accff5622d0de2f2a8921db0ccecda5dd5). Owner clarifies the screenshot is a new error variant; typical forward seeks stop playback. Raw log/private media paths and IDs remain outside GitHub.
- New log confirms Drive download proxy, 3840×1608 HEVC 10-bit/23.976 fps, advertised SDR. The TV receives 1920×804 H.264 through actual VideoToolbox + GPU transfer, so CPU fallback is not this capture's explanation. Conversions include 2.7–3.8 s per six-second segment; later request 4.8 s total. Audio requests reach 7.0/8.4 s. Large seek to about 52:06 has repeated requests waiting up to 26.7 s before final `session stopped` errors. This capture does not contain the screenshot's exact segment-37 error.
- Reproduced screenshot-class failure in the old server scheduler: concurrent forward request cancels a connected foreground conversion and produces HTTP 500 plus fatal message (two of twelve targeted checks fail). Now cancel only speculative jobs; clear background ownership before releasing its lane so a stale marker cannot cancel the next foreground conversion. Prioritize foreground work and distinguish typed cancellation from genuine conversion errors. Slow-request diagnostics separate lane wait from production; genuine errors remain visible.
- Expanded format tests exposed VP9+Opus rejection before either bridge could run: the segment planner required a copy-compatible track. Allow planning on decodable video while retaining no-copy selection, making conversion mandatory. Unsupported conversion now reports a clear failure instead of succeeding with sound only. AVI/MPEG-4/MP3 and WebM/VP9/Opus media/timeline tests pass.
- 1,095 native host checks and 33 Python/static tests pass. An actual 3840×2160 10-bit HEVC fixture verifies downscale, tail seek/keyframe/decoded frames and backward seek; it is six fps and uses the Linux MPEG-4 Part 2 test encoder. No iPhone throughput, VideoToolbox/H.264 output or TV acceptance claim. Corrected an existing synthetic PQ fixture that lacked frame transfer metadata on this host; failure and recovery retained in reports/airplay-seek-validation.json.
- Remaining work and compatibility matrix: docs/AIRPLAY.md. Long Drive source/production delay is not fully diagnosed; current source still has MP4 direct-routing, AV1, additional demuxer/decoder, HDR tone-mapping/Dolby Vision and bitmap-subtitle gaps. No universal every-file support claim. Retest small/large/repeated seeks on phone/Drive/active Elementum, subtitles on/off, after a separately requested build.
- Source-only staging in draft PR #8. Published framework pin stays r11. A future requested IPA must first build/publish a NEW KodiAirPlay framework release and verify/pin its hash; reusing r11 will omit these C fixes. No workflow dispatch, native framework build, IPA, release or merge.


### ISSUE-093 continuation — compatibility expansion requested now
- Owner explicitly asks to fix source gaps now, then says resume. Same draft PR #8, no IPA/merge. Source now inspects MP4/MOV codecs, retaining copy on capable routes and conversion for other receivers/profiles; HLS remains native. Native Dolby Vision profile-5 MP4 with compatible audio preserves the original direct route.
- Add checksum-pinned dav1d 1.5.3 (BSD-2-Clause) and iOS AV1 VideoToolbox request with software fallback. Expand legacy container/decoder and audio bridge coverage. Real AV1, WMV/WMA, FLV, Theora/Vorbis, MPEG-PS/MP2, RM, WTV, NUT/float PCM and ProRes/24-bit PCM conversion/seek tests pass.
- HDR correction: pinned FFmpeg 8.1.1 does provide tone/gamut mapping through its frame API; the previous legacy caller bypassed it. Use high-precision RGB mapping, downsize before the expensive map, preserve HDR metadata and retain SDR GPU behavior. Pixel checks caught a neutral-chroma defect in managed YUV output; the final RGB-to-YUV pack avoids it. PQ/HLG and full HDR media tests cover actual pixels, not just tags. Phone speed/color acceptance pending.
- Open-GOP MP4 sample indexes contain decode timestamps with varying presentation offsets. A constant shift failed receiver alignment tests. A small shipped LGPL patch exposes existing MOV table presentation timestamps with no media scan; copy/conversion alignment now passes. Raw MPEG-video probing and sparse-index checks also fix program-stream admission and giant-segment planning. The patch applies to clean pinned upstream source and matches the compiled file.
- Embedded PGS/DVD/DVB/XSUB palette burn-in uses a 32 MiB/256-rectangle cache, time/clear handling, scaling/clipping/alpha and backward seek. Actual synthetic PGS packets and burned-video comparison pass. Additional I/O timing separates source wait/reconnect from conversion production for later Drive diagnosis.
- Remaining limits: profile-5 Dolby conversion requires an RPU-aware renderer; native routing test is synthetic configuration, not color validation. External bitmap files and arbitrary HLS codec conversion are not implemented; not every enabled codec/profile has an individual fixture. Long Drive seek timing and iOS hardware/24–60 fps/TV acceptance remain device-unverified. Evidence: reports/airplay-coverage-validation.json and docs/AIRPLAY.md. Framework pin remains r11; no release or IPA was produced.


### ISSUE-093 continuation — Drive transport and external bitmap inputs
- Bound HTTP probing to 256 KiB and following ranges to 1 MiB, with keep-alive where supported. This limits the pinned Drive proxy's open-ended chunk growth/wasted reads; extra request latency and sustained high-bitrate performance still need device results.
- Replace the retry path's reused AVIO context and nested HTTP backoff with fresh contexts at the requested offset under one monotonic read deadline. Keep the existing configured timeout and explicit stop. Previous committed reader fails two transport regressions; a synthetic one-second stall budget took 5.211 s before, about 1.002 s after. This is not owner movie-seek timing.
- Add local external SUP and IDX/SUB demuxers, bounded/lazy bitmap rendering, future clear retention and backward replay, without scanning movie bytes for a long external cue. Connect app subtitle discovery/selection; require IDX's companion data. Later read failures propagate through conversion. Real PGS/DVD decoder, pixel, long-cue, far/backward/clear/cache and whole burned-video comparisons pass in focused validation. Missing/corrupt input checks retained.
- Remaining: embedded fresh-seek lookback can miss very long cues; external multi-language VobSub currently chooses its first supported stream. Dolby profile-5 rendering for incompatible TVs, arbitrary HLS conversion, full iOS compilation/TV acceptance and long Drive seek/4K throughput are still open. Framework r11 pin unchanged; no IPA, framework release, workflow dispatch or merge. Latest evidence/totals: reports/airplay-coverage-validation.json.


### ISSUE-093 continuation — close renderer/subtitle source gaps; native candidate validation
- Add validated profile-5 RPU polynomial/MMR reshaping, nonlinear offsets/matrices, PQ transfer and RPU/HPE linear conversion before SDR tone mapping, retaining high precision/source mastering luminance. Profile-5 files now use compatibility conversion across receivers; missing RPU errors explicitly. Pinned libplacebo LGPL attribution/full licence shipped; no iOS libplacebo/Vulkan dependency.
- Independent libplacebo comparison passes 172,800 channel samples: mean absolute luminance error about 0.0105 nits, maximum 0.3604 nits. Negative control ignoring RPU differs substantially. One-dimensional PQ tables replace a rejected inaccurate 3D LUT. Test image is synthetic IPT from physical RGB with generated RPU metadata, not owner media; MMR orders/cross terms also have exact algebraic pixel tests.
- Old embedded-subtitle preroll discards video and may scan until the next caption/clear beyond the target. Observe video timestamps, stop at the target, widen cold lookback when no display state is recovered, retain sequential coverage. Real 59-second PGS cue fresh/far/backward/decoded-pixel tests and scan-end diagnostics added. Owner log confirms embedded subtitles were selected; full 26.7-second cause/resolution remains device-unverified.
- External VobSub language aliases follow Kodi's selected language and persist through replay. Distinct English/Spanish bitmaps verify selection. Corrected the generated second-language IDX byte offset after its initial test failure. Initial native-test compile also needed the fixture_dir forward declaration; obsolete source assertions and generated-mux timestamp failure retained in validation notes.
- 1,381 native checks plus 35 Python/static checks pass. Isolated validation/airplay-source push is for host and iPhoneOS framework candidate only; no IPA/release workflow trigger on that branch. PR stays draft with skip-ci commits. Source-lock published r11 pin unchanged. Native result and device acceptance are recorded separately in the coverage report; no perfect/every-file/device success claim.


### ISSUE-093 final automated verification — 2026-11-05
- Clean run https://github.com/onlykappa/Kodi-Ios/actions/runs/41946561571 passes both jobs: 1,385 host checks / zero failures and iPhoneOS arm64 framework compile, required symbols present and source availability warnings resolved. 35 Python/static checks and independent numerical color comparison pass.
- Confirmed RPU failure by downloading the synthetic CI movie: an extra trailing NAL zero causes FFmpeg 8.1.1 to misdetect DM v2 metadata. Shipped LGPL padding patch fixes the exact reproduction; 29 focused checks pass with CRC validation and deliberate padding. Original parser/insertion-order hypothesis was disproved; all failed attempts retained in the report.
- Cancelled speculative decoder/source is retired before reuse; preroll stops at target video timestamp; long cues, VobSub language, profile-5 rendering and format/HTTP seek regressions pass. Test source: b148d23f819b5e427c294ed5a075aafbabf858f6; isolated CI differs only by a validation marker.
- Physical iPhone/Drive/Roku acceptance still pending. No IPA, release or merge. Published r11 pin unchanged; a future authorized IPA requires a new verified framework release/pin. Evidence: reports/airplay-coverage-validation.json; no universal/device success claim.

## ISSUE-094 — Owner bug 4: downloaded Library, refresh and phone-file reconciliation

- **Reported:** completed movies/shows missing from Library; grey `..` tile opens “The media route is incomplete.” Owner requests manual refresh and Settings › Library scan to upload missing phone videos to Drive and remove verified phone duplicates.
- **Causes confirmed in source:** plugin root treated navigation as an incomplete media request; no completed-phone listing; Drive TV only included folders and missed loose episodes; five-minute cached listings; upload invalidation skipped earlier successful files when a later batch transfer failed. Drive folder creation also treated a failed lookup as no folder, potentially creating duplicate folder branches that first-match discovery ignored.
- **Changes:** real root directory; completed phone and verified finished-seeding discovery; local show episode navigation; loose Drive episode filtering; all matching Drive folder branches/pagination; HTTP folder failures stop creation; manual refresh in Library/context/header and Settings; visible-page membership polling with busy/selection guards. Foreground artwork uses cache only; bounded background hydration yields during playback/transfers and cannot overwrite newer cache with stale foreground data.
- **Phone scan:** Settings › Library › Scan iPhone files for movies and shows selects Kodi Downloads or another accessible local folder. Index all app-created Kodi Downloads movie/TV branches, hash in bounded memory, upload missing media and remove duplicates only after an unchanged source, matching size/MD5 and fresh non-trashed Drive metadata. Name/size alone is insufficient. Automatic uploader now verifies checksums too and shares a cross-process transfer lock. Active/default/stale-sandbox torrent roots, symlinks, samples/partials, empty files and app data are excluded. Errors/cancellation retain unverified originals.
- **Verification:** **258 tests across 15 suites pass**, plus project/iOS static and diff checks; exact results/source hashes are recorded in reports/library-downloads-validation.json and docs/BUG-4-PROGRESS.md. Tests include actual plugin/directory dispatch with Kodi API stubs and local HTTP upload/verification integration; no live owner account changes.
- **Device acceptance pending:** complete a movie and episode; observe phone/seeding and Drive appearance, refresh an empty Library, navigate `..`, play exact episodes including specials, scan a missing file and a duplicate, verify Drive playback and phone cleanup, cancel a scan and retry offline. iOS permits only Kodi's files and folders made available to it. Source tests cannot establish these phone outcomes. No IPA, release or merge; continue in draft PR #8.

## ISSUE-095 — Launch shows logo, then Kodi splash, then menus; tab bar appears last

Status: SOURCE CHANGED; native r22/r5 builds and phone timing pending.
- Owner logs (2026-11-03): Home active 0.5-0.9 s after Kodi's first log line; first Python output 1.65-4.5 s after Home; the Python-driven bar cannot precede that. Timeline in docs/PERFORMANCE.md.
- Kodi splash off via special://xbmc/system/advancedsettings.xml (applies to existing installs); launch-screen logo replaced by a black PNG of the same size.
- Kodi executable r22 (staged) drives KodiGlassBar r5 (staged) from CApplication::Process with the add-on's rules and tab actions; the add-on attaches (owner flag) and keeps only the Search field. Old executable or framework: unchanged add-on behaviour.
- Static skin rows before Python considered and rejected (static items cannot carry the rows' art, playable semantics or context entries). No IPA built; no phone timing claimed.

## ISSUE-096 — Build 142: Home rows missing, app quits about 35 s after launch

Status: ROWS AND CPU-KILL FIXES IN SOURCE; device evidence pending.
- Owner log (build 142, 2026-11-05): Kodi read the skin includes from 1080i at 04.65 s, before the screen turned portrait (05.87 s, "Screen size out of step"). Kodi then reloaded each window for the portrait layout but not the includes, so Home logged every portrait variable as undefined (`Portrait_Hero_Art`, `Portrait_Card_Art`, `Portrait_Cache_Row_*`). With no row content, tab taps failed to focus rows 4000/14000/24000.
- Fix: the same variables are also written to `1080i/Includes_Portrait.xml`, and one include line (added once) in Fuse's `1080i/Includes.xml` loads it, so they are defined whichever folder Kodi reads first. Both files count as written by us in the portrait fingerprint. Test: `test_variables_defined_when_kodi_reads_1080i_includes`.
- Crash: the Kodi log just stops at 06:12:40 with no error. The owner's iOS report `Kodi.cpu_resource_fatal-2026-11-05-061610.ips` (r22 binary, UUID 861CCE81, symbolicated with llvm-symbolizer) says iOS **killed the process for CPU use**: 48 s of CPU in 53 s (91%) against a limit of 80% over 60 s, while Kodi was not the frontmost app in 9 of 12 samples. 765 MB footprint, so not a memory kill.
  - 7 of 12 samples: `WSDiscovery::CWSDiscoveryListenerUDP::Process`, mostly in the kernel (Kodi's SMB/Windows-network discovery listener spinning). Fix: one-time `services.wsdiscovery` = false (bootstrap `phone_housekeeping`); Kodi stops the listener when the setting changes (NetworkServices.cpp). Nothing here uses SMB.
  - Python samples: `builtin___import__` → `builtin_compile` → `Py_CompileStringObject`, i.e. modules compiled from source. The bundle is read-only and shipped no .pyc for the standard library (1089 .py, 0 cached) or most add-ons (TMDb Helper 371, ResolveURL 318, Burst 224 files). Fix: the IPA build precompiles both with CPython 3.11 as unchecked-hash .pyc (`build_customized_ipa.precompile`, setup-python 3.11 in import-review.yml); the build fails if os/json .pyc are missing from the IPA.
  - Not device-verified. The two 2160p torrents resuming on the phone at launch remain worth watching.

## ISSUE-097 — Build 145: downloaded movies grey in Library; phone copies of Drive videos stay on the phone

Status: FIXED IN SOURCE; device evidence pending.
- Owner screenshot and log (build 145, 2026-11-05): Library › Movies showed Hell House LLC, Inception and The Blair Witch Project grey (no poster). All three played from `Documents/Kodi Downloads/Movies/<Title (Year)>/` on the phone; the Drive items had art. Rows on Home now load (listing cache 5–30 ms per row), and Kodi did not quit.
- Grey cards: the visible-page art worker (library_watch) skipped while `Notices.Active` was 'true', which is the case for as long as any Elementum download runs (one was running at 12 MB/s). Parsing and TMDb lookups for the three file names were checked on the host and all return posters. The download condition is removed; art still waits for playback, dialogs and page loads.
- Phone duplicates: the automatic uploader (`driveupload.run_once`) never checked Drive for an existing identical copy (only the manual "Scan iPhone files" did). It now lists Drive › Kodi Downloads once per pass (`library_scan.remote_files`), skips the upload when size + MD5 match with fresh Drive metadata, and removes the phone copy under the existing verification rules. With "Remove the phone copy" off, a file already on Drive is remembered and never uploaded or hashed again.
- Also: the first upload pass runs 30 s after start (was 120 s; the owner's log ended at 91 s with no pass), each pass logs what it found, and background hashing is paced to half a core (CPU kill, ISSUE-096).

## ISSUE-098 — Build 146: Library shows listed three times, pages titled "Kodi iOS W", bare downloaded-show page

Status: FIXED IN SOURCE; device evidence pending.
- Owner screenshots (build 146): Library › TV Shows listed Lanterns three times. The same show came from the phone episode file, a season pack still seeding (folder "Lanterns (2026) …", so a different year) and the Drive folder. The page header read "Kodi iOS W" (Container.FolderName falls back to the add-on name when the page is opened from the Library tile). The show page had no background, no episode names, plots or stills, and the same episode twice (phone + Drive).
- One card per downloaded show (same name ignoring case, punctuation and year; Kodi's own library rows untouched). It opens `?action=library&type=tv&show=…&merge=1[&folder=…]`, listing the phone's and Drive's episodes. A movie both on the phone and on Drive shows once (the phone copy).
- Show page: each episode once (phone copy first), in season/episode order, with the show's TMDb background and poster (`tvshow.fanart`/`tvshow.poster` for the existing show header) and TMDb episode name, plot, still, runtime and air date (`drivelibrary.season`, cached; fetched by the visible-page worker like posters).
- Titles: "Downloaded Movies", "Downloaded TV Shows" or the show name (`Container.PluginCategory`, now used by `Portrait_Page_Title` before the folder name). Test: `scripts/test_library_pages.py` (in CI).

## ISSUE-099 — Owner request: the video player's back button everywhere

Status: DONE IN SOURCE; device check pending.
- Owner (build 146, screenshot): prefers the video player's back button (a bold white chevron with no circle, 104 in a 150 touch area) to the 108 glass circle with a 46 glyph used on the other pages.
- `portrait.nav_button` draws back and refresh that way (same size on the phone in both layouts) and is used for: video/Library/episode pages (back + refresh), Choose a version, Notifications, and the Settings header (Settings, Accounts and the pages built on it). The glyph dims while focused. Test: `test_back_and_refresh_look_like_the_player_everywhere`.

### ISSUE-098 screenshot continuation — downloaded seasons / Play and Continue

- Owner's Claude screenshots showed the unfinished follow-up: downloaded Lanterns still used a bare episode page, with no logo/genres/Play and an extra grey play tile; movies/TV could show the Watch add-on name.
- Downloaded shows now return seasons and season-specific episode routes, cached full-show metadata and exact completed-file Play/Continue state. Background fetches remain bounded; metadata is also allowed during downloads as fixed by Claude. All matching Drive folders participate, with phone copies preferred. Bookmark reads batch local directories; plugin paths never trigger filesystem bookmark RPCs.
- Actual local/Drive playback resolver retains resume and provider/version history, and clears unrelated history when TMDb identity is unavailable. Returning from playback refreshes the button after progress changes. Refresh stays in header/context instead of a fake episode folder; non-episode decorations are hidden. Titles use show/plugin category fallbacks. Watch add-on version 1.4.4.
- Evidence: reports/downloaded-show-validation.json; 362 tests/24 suites pass. New native layout behavior is tracked in ISSUE-100; phone acceptance pending.

## ISSUE-100 — Show page scrolls only the lower episode list

Status: FIXED IN SOURCE, NATIVE PATCH STAGED; pinned r22 lacks the new code.
- Root cause: portrait seasons/episodes lived in a fixed lower list below an unscrolling header. Simply nesting another vertical list does not help because Kodi's child list captures same-axis gestures.
- One portrait Videos group (window 10025, group 9900, lists 52/60) now contains header, actions, plot, seasons and a full-height lazy episode viewport. A single native pan delta moves the header first then episode offset; reverse gestures rewind episodes before restoring the header. Short seasons avoid extra blank extent, edge/inertial scrolling clamps, horizontal chips retain independent movement, and keyboard focus keeps ordinary scroll-into-view behavior. Touch selection cannot jump the header away.
- A downloaded-show-only parent-row guard suppresses Kodi's synthetic `..` item so it cannot occupy a blank season/episode slot; back navigation remains available. Unrelated native patch sections are preserved byte-for-byte.
- Validation: production method bodies compiled/executed with GUI geometry stubs, scoped parent-row branch compiled/executed, generated layout/visibility checks, 44 portrait regressions, full patch applied against 30 original files at Kodi a3a448d26b8d560a65655dab2cd122994dc4e146. Applied-source comparison changes only five intended GUI files. Total 362 tests/24 suites pass; first formatting/interpreter failures and successful rechecks retained in the report.
- Remaining: full iPhoneOS SDK build/release/verified executable pin, then actual phone touch/momentum, short/long seasons, local/Drive resume and visual acceptance. No new native build, IPA, release or merge performed; current executable pin stays r22.

## ISSUE-101 — Notifications › Preparing row: two text lines overlap (build-152)

Status: FIXED IN SOURCE; device check pending.
- Owner screenshot (build-152): "Step 3 of 3 · Preparing audio · 40% · 8 remaining" was drawn over "…one file · source resolution"; the title was a raw release name and "8 remaining" appeared twice.
- Root cause: the upload card drew its status line (left) and a fixed hint (right) as two labels in the same box (`SIDE+184, 158, w-210`); the preparation card was a string-replaced copy of it. The download card did the same with progress (left) and speed (right). The hint also used `DIM` (≈2.2:1, below the text-contrast minimum).
- Fix (`portrait.notices_page`): one `transfer()` builder for upload and preparation cards with one label per line (title, summary, bar, status); the hint moves into the summary ("Movies · then off the phone"); the download card's progress and speed share one truncating line; section summaries and timestamps get reserved widths and readable grey; titles go through `drivelibrary.display_title` ("Lanterns · S1 E1", "Inception (2010)"); the preparation count appears only in the summary. Text widths measured with Inter: typical lines 389–678 of 762 units; longer titles and folders truncate.
- Regression: `test_notices.OverlapTests` checks that no two labels on the page share space (it caught two further 2–4 unit box overlaps, now fixed), that the detector flags the build-152 layout, and that no `DIM` text remains. Policy: docs/design/APPLE-UI-POLICY.md (PR #11) §4.2.

## ISSUE-105 — Portrait pages drawn 9 % too tall; Activity sheet off the bottom; pill without a picture (build 154)

Status: FIXED IN SOURCE (local draft, not pushed: owner testing); rig and device checks pending.
- Owner screenshot (build 154, device): the Activity sheet's bottom runs off the screen, the ring around the app tile is an oval blob, and the owner wants the pill to show a photo of what is downloading instead of the blue app tile.
- Root cause (confirmed in Kodi 21.3's xbmc/addons/Skin.cpp `closestRes` and `RESOLUTION_INFO::DisplayRatio`): Kodi chooses a skin resolution by the ratio its `aspect` *label* states, not by its width and height.
  - The portrait entries were labelled `9:19.5` (0.462) and `9:16` (0.563). On the iPhone 16 Pro's 0.517 safe area, `9:16` was closer, so every portrait page was drawn on 1080 × 1920 and stretched into the 1080 × 2090 space it was designed for.
  - The result: everything 9 % taller (rings and circles were ovals: the screenshot's tile ring is 116 × 128 px, the bell 90 × 95), and anything placed by absolute position near the bottom 170 units low. The sheet's top measured exactly at 2090 − 570 in 1920-unit space.
  - The desktop rig (603 × 1167, the same ratio) had the same choice, which is why the round-3/4 rig renders showed the sheet cut off too.
- Fix:
  - The portrait entry is labelled with its true ratio, `1080:2090`. `9:16` stays for home-button phones.
  - `add_resolutions` now also upgrades a phone's existing writable skin copy on every start. Kodi reads the skin's resolutions when it loads the skin, so the change shows from the next start.
  - The pill and the Activity sheet rows show the TMDb poster of the download (or upload) inside the progress ring, cropped to the rounded tile. It comes from the Library's cached `drivelibrary.artwork` with TMDb Helper's key, is looked up once per title in a background thread, and falls back to the app tile while loading or when there is no match. A finished job shows the green check.
- Expect every portrait page to look about 9 % shorter (as designed), with things previously cut off at the bottom now visible. This needs a rig re-render and an owner check on the phone.
- Regression: `test_portrait.ResolutionChoice` (Kodi's rule replayed: 16 Pro → 1080 × 2090, old labels → 1920, home-button phones → 9:16, in-place upgrade once), `test_activity.Posters` (4).
## ISSUE-103 — The same show in two Drive folders, the same episode prepared twice (build 152)

Status: FIXED IN SOURCE; device check pending.
- Owner screenshots (build 152): Drive › Kodi Downloads › TV Shows held "Lanterns" and "Lanterns (2026)", the same show, each with S1 E1. Both were queued for preparation ("7 remaining"). The owner asked for a duplicate check before any uploading or downloading, then (DEC-028) for the extra copy to be deleted and for a check before Elementum downloads.
- Root cause: upload folders were named from each release's file name ("Lanterns.S01E01…" gives "Lanterns", a release with the year gives "Lanterns (2026)"). Duplicates were only identical bytes (size + MD5), so two releases of one episode were both uploaded and both queued.
- Fix:
  - One rule, `drivelibrary.media_key`: the same episode means the same show name, ignoring case, punctuation and year (the Library's merge rule), plus the same season and episode. The same movie means the same title and year. Copies whose named years disagree are never treated as one: "The Office (2001)" and "The Office (2005)" are different shows. A bare `S01E01.mkv` in a "Season 1" folder gets no key.
  - Before an Elementum download (`download.py`, using `ios_downloaded.completed_copy`, the same phone + Drive lookup as Continue Watching):
    - A movie or episode already downloaded asks "Download again?" and names where it is.
    - The episode chooser marks downloaded episodes, and picking them asks first.
    - A whole season says how many of its episodes are already downloaded.
    - A failed check never blocks the download.
  - Before an upload: an episode goes into the show's existing Drive folder. If Drive already has the same episode or movie at equal or higher resolution, the phone copy is the extra one. It is removed once Drive's copy is confirmed with fresh metadata, and only with the "remove phone copies" setting on (otherwise it is kept and reported once). A seeding torrent is removed through Elementum. A better phone copy is uploaded, verified, and then the worse Drive copy goes to Drive's Trash. Settings › Library scan follows the same rule.
  - Before preparation downloads a Drive file: one copy per episode or movie is kept. The kept copy is chosen in this order: already prepared, then being saved or with working files, then the highest resolution, then the largest. Once the kept copy is confirmed on Drive, the others go to Drive's Trash, along with a show/release folder left empty (never Kodi Downloads' own folders). A copy being saved, or changed since it was listed, is never trashed.
  - Deletion on Drive is always to the Trash, restorable there for 30 days, never permanent. Every removal produces one notification naming what was kept and what went.
  - "Ready for Kodi and AirPlay" names the title ("Lanterns · S1 E1"), not the file.
- Regression: `test_drive_library.Duplicates`, `test_drive_upload.SameEpisode` (6), `test_prepare_downloads.OneCopyEach` (8: best copy kept, trash plus empty folder, shared folder kept, prepared or in-progress copy wins, unconfirmed or changed copies kept, different years), `test_library_scan` (same movie replaces the phone copy only when confirmed; different years upload), and `test_updates_calibration.AlreadyDownloaded`.

## ISSUE-104 — Owner sees no movies being converted (build 156)

Status: FIXED IN SOURCE (local draft, not pushed: owner is testing build 156); device check pending.
- Owner: "check if the auto converter starts at launch because I don't see any files being converted and I know all my movies need to be", and asked for a Settings entry to check the library.
- Launch: the service's first pass runs 5 s after start (idle, Drive signed in, setting on). The owner's build-152 screenshot showed it preparing Lanterns, so it starts.
- Two queue bugs could keep every movie waiting:
  1. One video Drive could not describe (`metadata` error) aborted the whole launch scan, so nothing after it was queued, on every pass.
  2. The queue only resumed a half-downloaded video (to save phone space). If that video was in a retry wait (low space, network), nothing else could start, for up to an hour each time, indefinitely.
- Fix:
  - The scan skips an unreadable file (keeping its existing work) and records totals: videos, ready, unreadable, checked time.
  - A stuck half-downloaded video no longer holds the queue. A resumable one still goes first, and every job checks free space itself.
  - New Settings › Library › Kodi and AirPlay › **Check library for conversion** (also in the add-on's Google Drive settings). It asks the service to check now; a conversion in progress pauses and resumes where it was. It then shows how many videos are ready, waiting or paused, with the reasons.
- Regression: `test_prepare_downloads.LibraryCheck` (7) plus the updated service wiring test.
- Open question for the owner: are the movies in Google Drive › Kodi Downloads › Movies? Videos elsewhere on Drive are not scanned.

## ISSUE-106 — "Best" 4K source for Fall (2022) downloaded Fall.2.Deadpoint.2026 (build 156)

Status: FIXED IN SOURCE (local draft, not pushed); device check pending.
- Owner screenshot (build 156): after choosing Fall (2022) › 4K › the best source, Elementum's buffering dialog showed `Fall.2.Deadpoint.2026.2160p.4K.WEB.x265.10bit.AAC5.1-[YTS.GG - YTS.BZ].mkv`.
- Root cause: the source check (`source_match`, run on every provider's results in Burst) is correct for this name: it returns "wrong title" for the 2026 sequel and accepts `Fall.2022…`. But some sites (YTS look-alikes such as YTS.GG/YTS.BZ) label each result from their own movie catalogue ("Fall 2022 2160p"), so the label passed. The torrent's real name only exists once Elementum has its metadata, after the choice was made.
- Fix: `source_guard.py`, a service thread reusing the shared engine list every 2 s.
  - Every torrent added after a source search is judged against the search current when it first appeared (so several chosen episodes never judge each other), for 5 minutes, once its real name is known.
  - A clear mismatch stops the download: for a film, another title or year, or an episode; for a show, another show. The torrent and its files are removed, with a Notifications › Problems entry ("Fall.2.Deadpoint.2026… is not Fall (2022) (wrong title)… choose another version").
  - Uncertain names (no year, hash-only names before metadata), torrents that were already there, searches over 30 minutes old, and a hidden source the owner chose deliberately are left alone.
- Not changed: Elementum's own ranking of the "best" source (it re-sorts Burst's results by its quality/seeds setting).
- Regression: `test_source_match.WhatTheTorrentReallyIs` (7, including the owner's exact name and the several-episodes race).

## ISSUE-107 — AirPlay refused for every prepared movie; preparation stuck on phone space (build 157)

Status: FIXED IN SOURCE; device check pending.
- Owner (build 157): "AirPlay won't work at all" ("AirPlay: cannot open the stream (Connection refused)") and repeated "Video preparation paused: Free phone space is needed" (5 times). The phone had about 51 GB free of 256 GB.
- AirPlay root cause (kodi.log): KodiAirPlay was given `http://10.0.0.247:57527/…/Scary.Movie…mp4`, the Wi-Fi address of the Google Drive add-on's helper, which only answers on 127.0.0.1 (the same refusal as build 132). `cast.py` used the phone's own link only for files that were not Apple-playable. Prepared movies are `.mp4`, so every prepared movie got the Wi-Fi link. Fix: `cast.airplay_source`. A converting framework (r5+) always reads the video itself and gets the 127.0.0.1 link; an older framework keeps the Wi-Fi link for Apple's player.
- Space root cause: preparing a video needs the Drive file and the prepared copy on the phone at the same time (about twice its size; the native step takes local files). The queue started videos without checking that, kept a stuck video's partial download on the phone, and notified on every retry.
- Fix:
  - A video starts only when twice its size plus a margin fits while leaving 5 GB free for the owner (`KEEP_FREE`). Videos that fit go first.
  - A half-prepared video that cannot finish gives its space back.
  - Running out midway frees the working files quietly and waits.
  - "Waiting for phone space" is notified once when the list grows; other problems are notified once per video and reason.
  - Settings › Check library for conversion shows how many videos wait for space.
- Not solved here: a video larger than (free space − 5 GB) / 2 still waits. Halving the need means reading straight from Drive instead of downloading first, which requires a KodiAirPlay native change (local-path-only input today) and a macOS framework build.
- Regression: `test_prepare_downloads.NeverRunsOutOfSpace` (5), `test_airplay_remux.PhoneSource.test_a_prepared_mp4_also_uses_the_phones_own_link`.

## ISSUE-108 — Preparation must not download movies first (owner, after build 157)

Status: IN SOURCE; KodiAirPlay r14 build, then device check pending.
- Owner: "Please have it read from the drive as my storage can't handle large scale downloads." Before this, a movie needed its Drive file and its prepared copy on the phone at once (about twice its size; ISSUE-107).
- Native (KodiAirPlay r14, `kr_prepare.c`): probe and prepare accept `http://127.0.0.1:` sources as well as local paths (loopback only, never the internet), opened with bounded timeouts, reconnects at the same offset and Range seeks. The spool passes already read through `kr_source`, which handles HTTP. `kodi_airplay_prepare_streams()` (exported) tells the add-on the build can do it. Host test: `test_preparation_http` prepares two fixtures through the range server, gets byte-identical video packets to the file version, and refuses a non-loopback URL.
- Add-on: `drive_stream.DriveStream`, a 127.0.0.1 server (random session secret, registered Drive files only) that answers byte ranges by fetching them from Drive as the converter asks; nothing is written to the phone. With r14, `prepare_downloads` streams instead of downloading, skips the local-copy checksum (a Drive change meanwhile is still refused by `replace()`'s fresh version/checksum check, and the output is still validated for resolution, HDR and duration), deletes any copy an older build left, and plans space for about 1× the movie (`space_needed(item, streaming=True)`). An older framework keeps the download path.
- Trade-off: more data is read from Drive (a movie whose audio needs converting is read twice), in exchange for half the phone space.
- Regression: `test_prepare_downloads.StreamFromDrive` (8).

## ISSUE-109 — "Check library for conversion" did not seem to work; no view of what is ready (owner, after build 157)

Status: FIXED IN SOURCE; device check pending (build 158).
- Owner: "when i click library check for conversion it doesnt seem to work, I want it to open a menu showing me whats converted and is good to go and what still needs to be converted or if its still downloading."
- Root cause: the row asked the service for a check and then waited up to two minutes behind a progress dialog for a plain-text summary; while a video played or a long check ran, nothing visible happened, and the summary gave counts, not videos.
- Fix: Settings › Library › Library status (owner-approved mockup, `docs/design/library-status-mockup.html`), skin `library_page.py`, rows `library_rows.py`, controller `library_status.py`. Every video in Google Drive › Kodi Downloads grouped as preparing now, downloading, waiting (in line, waiting for phone space, retrying after a problem), ready for Kodi and AirPlay, kept as it is; a ring with ready of total, phone space, four filters, Check now, and a details sheet per video. Its actions (Prepare next, Try again now, Keep as it is, Prepare it after all) go to the service through `preparation-requests.json` (`prepare_downloads.request` / `Queue.apply_requests`), so the page never writes the queue's state. The library check now records each video (`state['library']['items']`).
- Owner (build 158): "the buttons i press better work". A choice made while a video was being prepared only reached the service after that video (it reads choices between videos), so the page looked as if nothing happened. The page now shows a choice at once (`prepare_downloads.apply_to` on a copy of the state, with `pending_requests`), the service wakes within 5 s for one, and a choice with preparation turned off asks to turn it on instead of doing nothing.
- Regression: `test_library_status` (32): view, rows, filters, details actions, requests applied once, kept videos skipped, every button at least 44 pt, ids and properties the controller uses, wiring; `TapEveryButton` runs the real controller against a fake Kodi and taps Back, Check now, the four filters, Show all, every row action (Prepare next, Keep as it is, Prepare it after all, Try again now), the sheet's ✕, the dimmed backdrop and the back key.

## ISSUE-110 — Library status did nothing when tapped (build 159)

Status: FIXED IN SOURCE; device check pending.
- Owner (build 159, kodi.log): tapping Settings › Library › Library status did nothing. Every tap logged `RuntimeError: No valid addon id could be obtained` at `library_status.py` `xbmcaddon.Addon()`.
- Root cause: scripts started as `RunScript(service.kodi.ios.bootstrap,page)` run through `default.py`'s `runpy`, so Kodi cannot tell which add-on a bare `xbmcaddon.Addon()` means. The old Check library for conversion (`prepare_check.py`) had the same call, which is why it "didn't seem to work" (ISSUE-109). The fake Kodi in `test_library_status` accepted the bare call, so the tests passed.
- Fix: both scripts name the add-on (`Addon('service.kodi.ios.bootstrap')`). The fake Kodi now refuses a bare `Addon()` as Kodi does.
- Regression: `test_library_status.EveryScriptNamesItsAddon` (no RunScript page calls a bare `Addon()`); `TapEveryButton` runs the real controller against the strict fake.

## ISSUE-111 — Kodi uses about 10 GB of the phone (owner, build 159)

Status: PARTLY FIXED IN SOURCE; what the 10 GB is will show on Library status (device check pending).
- Owner: "does this fix why kodi is eating 10gb?" The bundled log showed only startup, so the 10 GB could not be attributed from it.
- Found while checking: a video whose preparation failed, or that the owner chose to keep as it is, kept its half-made working files until its next try (or forever when kept). With KodiAirPlay r14 a streamed preparation cannot resume, so those files were only taking space.
- Fix: `Queue.tidy()` before every video: working files stay only for a video that carries on where it was (waiting, paused for playback, saving to Drive); failed, kept, blocked, done and unknown ones give their space back at once. Library status's Phone space card now measures what Kodi keeps on the phone (preparation, Elementum downloads and data, videos on this iPhone, artwork, temporary files, add-on downloads and data; each file counted once) and names the two largest, and its bar shows Kodi's share.
- Regression: `test_library_status.PhoneSpace` (5).

## ISSUE-112 — Tapping a notification should show its log (owner, build 159)

Status: IN SOURCE, not yet built (owner: "dont build this just have it ready for next round"); device check pending.
- Owner: "when i tap a notification it brings me to that log." Kodi's own pop-ups ("Kodi iOS Automatic Setup and Recovery… Check the log for more information.") said only that, and a row did nothing unless the message carried an action.
- Kodi writes a new kodi.log at every launch, so the lines are kept with the message when it arrives: the bootstrap service's bell loop (`notices.publish`) calls `notices.attach_logs` with `special://logpath/kodi.log`; each new message gets, 2 s after it arrived, the records from 90 s before to 1 s after it (`notices.excerpt`): every error (a Python error report is one record, said in one sentence with its file and line: `plain_record`), warnings that name the message's add-on, Kodi iOS lines that report trouble from the last 15 s; Elementum's web server and its own info lines, add-on config dumps and touch tracing are left out, repeats merged with a count. Kept in `notice-logs/<id>.json` (removed with the message and by Clear All).
- Tapping a message opens `portrait/IOSNoticeDetail.xml` (`notice_page.py`, built from the Library status sheet's pieces): the message, "What happened" (the worst record in one sentence), and "From kodi.log" (newest first, error red, warning orange, app folders shortened). A message's own action is the sheet's Open button. A message from before this build reads the current launch's log when tapped.
- Checked against the owner's build-159 log: the crash pop-up shows "RuntimeError: No valid addon id could be obtained… (library_status.py, line 39)", 5 times; an Elementum message shows only Elementum's repository error, not its ~280 lines of chatter.
- Regression: `test_notice_log` (14): parsing, excerpt choices, attach once / clear, the sheet (44 pt buttons, ids, properties, fits above the button), and taps on the real Notifications page in the fake Kodi (crash → log; action → Open; dimmed page and back close).
- Visual check pending: no render in this environment; first seen on the device.

## ISSUE-113 — Library status: grey boxes for section names; owner wants folders (build 160)

Status: FIXED IN SOURCE; device check pending (build 161).
- Owner (build 160 screenshots): "I hate the grey boxes next to 'waiting' and 'ready for kodi and airplay' … it needs to be in like a folder so ready will show 7 then if i tap it it shows the movies." The footnote also showed as a row with an empty poster.
- Root cause: the list used conditional item layouts (`<itemlayout condition="String.IsEqual(ListItem.Property(kind),header)">`). Kodi chooses among them by global conditions, not per item, so every item, the section names too, was drawn with the video row layout.
- Fix: one layout for every item whose parts show by `ListItem.Property(kind)` (row, folder, foot). All shows what is happening now (preparing, downloading) as rows, then folders (Waiting, Ready for Kodi and AirPlay, Kept as it is) with a coloured tile, what is in them and the count; a folder opens its videos and the page title becomes its name; Back (arrow, gesture or back key) returns to All and closes only from All (the skin's Close is conditional too).
- Regression: `test_library_status` (folders, one layout, positions, folder open and back in the fake Kodi).

## ISSUE-114 — Phone space: 29 GB shown, iPhone says about 49; Inception waited on a figure the page did not show (build 160)

Status: FIXED IN SOURCE; device check pending (build 161).
- Owner: "It says my phone has 30gb free but it has 50 and we made it so my phone storage doesnt matter so it shouldnt be waiting at all."
- Root cause 1: `shutil.disk_usage` (statvfs) counts only space free right now; iOS Settings also counts space it clears on its own when an app needs it. Fix: `phone_space.free` reads `NSURLVolumeAvailableCapacityForImportantUsageKey` through the Objective-C runtime (ctypes; never less than statvfs; statvfs elsewhere or on any failure); used by the queue, the preparation step and the page.
- Root cause 2: the queue and the page used "the file's size", the preparation step its own estimate from the native probe (picture copied, or re-encoded at about 7 Mbit/s per 1080p, twice while it is made). Inception's step wanted far more than the 14 GB the page showed. Fix: the probe is kept with the job; `work_bytes` / `space_needed` give one figure for all three; a video that waits says why ("its picture (AV1 10-bit) cannot go into MP4 as it is, so it is re-encoded") in its details.
- Not solved here: a movie whose picture must be re-encoded still needs room for the new picture on the phone while it is made (MP4's index is written after the picture). Which codec Inception has will show on its details sheet with KodiAirPlay r15 (the probe now reports codec and bit depth).
- Regression: `test_library_status.SpaceAsTheIPhoneCountsIt` (4).

## ISSUE-115 — Interstellar kept as it is: picture subtitles (build 160)

Status: IN SOURCE (KodiAirPlay r15); CI build, then device check pending.
- Owner: "Interstellar isnt being transferred and doesnt say ready … It needs to be ready for airplay."
- Root cause: its Blu-ray picture subtitles (PGS) cannot go into MP4, and preparation never drops subtitles silently, so the file was kept as it is.
- Fix: KodiAirPlay r15 `kodi_airplay_prepare_keep_image_subs(1)` writes each PGS track, untouched, to `output.sub<track>.<lang>[.forced].sup` (FFmpeg's `sup` muxer, now built) and prepares the MP4 without them. The add-on saves them next to the video on Google Drive as `<video>.<lang>[.forced].sup` (as Kodi names external subtitles) before replacing the video, and gives videos kept only for that one new try. Off by default in the framework. DVD picture subtitles or a second video track still keep a file as it is.
- Regression: host `test_remux.c` (the .sup holds every PGS byte, none in the MP4, probe reports codec and PGS count), `test_image_subtitles` (9).

## ISSUE-116 — Play on TV: a Ready movie "can't play (MP4)"; Play on TV pressed twice (build 160)

Status: FIXED IN SOURCE; device check pending (build 162).
- Owner: "this movie is under ready and it gives me this bs" (Apple's AirPlay player can't play this video (MP4)…) and "its super buggy i like have to press it twice for it too work".
- Log (build 160, The Nightmare Before Christmas, prepared MP4, TCL Roku TV): every attempt shows "Play on TV: opened" twice about 10 s apart. Nothing was on screen while the TV connected, so Play on TV was pressed again; the second session's start tore down the first session's file server (the first failed with -1004 "Could not connect to the server"), and the first session, failing, closed the second one's. The failure then fell through to the Screen Mirroring text, which names the file's extension (MP4).
- Fix: one Play on TV at a time (Home property `KodiIOS.PlayOnTV`, 90 s; a second press says "Still connecting to the TV…"); a "Connecting to the TV…" progress with Cancel from the moment AirPlay starts (Cancel and failures let Kodi's video carry on); with a converting framework a failure says what Apple's player reported in everyday words ("AirPlay didn't start on the TV: the TV could not connect to the phone") instead of blaming the format.
- Still to see: whether this TCL Roku TV shows the picture of a prepared HEVC MP4 (prepared files go to the TV as they are; build 136-era logs needed the H.264 picture for this TV). If it plays sound only, the existing "No picture on the TV" alert says so.
- Regression: `test_play_on_tv_start` (5).

## ISSUE-117 — Downloads fill the phone; a large movie can never download (build 160)

Status: IN SOURCE; device check pending (build 162).
- Owner: "a movie im downloading goes onto my phone still … its eating all my storage and if i do a large movie it wont ever download" (Files: Fall.2022.2160p.WEB-DL… 19.83 GB). Chose "AllDebrid straight to Drive".
- Root cause: Download always went through Elementum; a torrent is written to the phone, uploaded to Drive, then deleted, so it needs its whole size free.
- Fix: with AllDebrid signed in (Umbrella › Accounts, `alldebridtoken`), Download only (movie, episode, chosen episodes, whole season) hands the version picked to AllDebrid (`alldebrid.py`) and Elementum drops it and its files; the service (`debrid_loop`, `debrid_drive.step`) waits while AllDebrid fetches it on its servers, then copies each video into Drive › Kodi Downloads › Movies / TV Shows › <show> with `Drive.upload_stream` (16 MB at a time, resumes at Drive's offset; nothing written to the phone), rescans the library and asks preparation to check. Progress shows on the Uploading card, the pill and Library status. Without AllDebrid, or with Download and watch, Elementum as before.
- Owner, same day: "Download only or download and watch doesnt appear when i select the source it just starts downloading". Playing a version from the source page goes through Elementum, which this app sets to keep downloading after playback, so the whole movie still landed on the phone. Fix: with AllDebrid signed in, the service takes every unfinished Elementum torrent after 3 minutes with nothing playing (never while a video plays or buffers; `debrid_drive.adopt`), queues it for AllDebrid and Drive, and Elementum drops it and its files. A finished one goes to Drive the usual way.
- Regression: `test_debrid_drive` (16).

## ISSUE-102 — Activity pill and sheet (PR #9): review against the Apple UI policy (rig screenshots, 2026-11-05)

Status: OPEN; findings only, no code changed. Evidence class: **desktop Kodi rig** renders of unmerged PR #9 (603 × 1311 with the safe-area bars, owner-supplied), not device. The owner's installed build-151 does not contain the pill. Measured approximately, taking the image width as 402 pt.
- **Progress ring badge renders empty:** PR #9 deliberately draws a 72-unit ring badge on the tile corner (`activity_skin.py`: `ring_20.png` track at 25 % white plus `Activity.Ring` fill tinted `Activity.RingTint`). In the pill render only the faint track shows, while the same job has visible progress in the sheet (≈17 % bar) and a time estimate. So the fill is missing or near zero for this job, which was fed by the rig's stand-in Elementum engine. Cause not yet established, and it may differ with the real engine. Check `ring_name()`/`Pct` for engine-sourced jobs and the badge's legibility (a grey ring on a dark dot reads as a stray circle). If there's no percentage, show the spinner instead of an empty ring.
- **Touch targets below 44 pt (confirmed in PR #9 source):** the pill's pause group is 104 units (≈ 39 pt) and the sheet's pause button is 96 units (≈ 36 pt). Both are below the 118-unit minimum (policy §4.5). Enlarge the touch area to 118 or more and keep the drawn circle. The bell and profile circles measure ≈ 39 pt on screen; check their touch areas the same way.
- **Tiny, inconsistent glyphs:** the bell, profile and Info "i" glyphs are about 7–8 pt, while the Play triangle is about 13 pt and the tab bar icons are much larger. Icons inside buttons should share one size (46 units ≈ 17 pt, policy §5.5).
- **The pill repeats the sheet's row instead of summarising:** same tile, title and status line. That is fine for one job. With several jobs it must switch to "N running" (PR #9 does this). Confirm on device with 2+ jobs.
- **Tab bar in the renders is Kodi's fallback, not the native bar:** the rig cannot load `KodiGlassBar`, so the renders say nothing about the native bar's material. On the device, check that the pill sits correctly above the native Liquid Glass bar and that labels stay legible over bright artwork (HIG `materials.md`, `tab-bars.md`).
- **Blue accents:** the Movies tab, the "Done" button, the progress bar and the app tile use at least two blues (see policy §4.3 drift). Pick one per role when the pill is restyled.
- What already matches the policy: floating capsule pill above the tab bar, one line per text run with no overlap, white primary/secondary text hierarchy, sheet with grabber, large title and Done, dimmed backdrop, thin progress bar, one primary (white) action on the hero.
- Next: fix as part of the pill work on PR #9 (rebase onto main first), re-render in the rig, then build a test IPA when the owner authorises it so the pill can be checked on the phone for the first time.

## ISSUE-118 — Pages disagree; "Paused while a video plays" with nothing playing; work stops for playback (build 192)

Status: IN SOURCE on PR #16 (build 193 Phases 1–5, not built); visual and device checks pending.
- Owner (build 192): "Notification center isn't linked with Library status properly or it is just SUPER SLOW … it still says paused as a video plays and it seems to be converting … if I click on it it says nothing is moving … stuff should ALWAYS be moving even if an AirPlay movie is playing, just slower."
- Root causes (full review with log lines and file:line: docs/LOG-REVIEW-192.md): (1) the converter's own `prepare: …` lines went through the AirPlay log and `airplay.activity` took them as AirPlay playing for 90 s, which held the conversion, its Drive reads and uploads and the AllDebrid copy, and made the queue wait 120 s; (2) `prepare_cloud.waiting()` always said "a video plays"; (3) a stopped job and a failed library check kept running words; (4) each page used its own freshness clock (1, 15, 30, 60 s, none).
- Fix: only the AirPlay server's and Apple's player's lines mark AirPlay (`airplay.airplay_lines`); playback never holds work any more, it slows it to a share of the line and CPU (`slowdown.py`: video 35 %, AirPlay 25 %, 8 % for 60 s after a TV read slower than 1.5 s; used by the converter pace, Drive reads, upload pieces, phone uploads and AllDebrid copies); the owner's Pause stays a real pause and now says "Paused by you"; one status model (`work_state.py`, written every 2 s, older than 6 s never shown as running, the reason stored with the state) read by Library status, the Queue, Notifications, Transfers and the bell; a failed check clears its card; AllDebrid progress carries its time, tries reset after a piece goes up, a retry says "trying again in N min".
- Retest: all scripts/test_*.py, check_project, check_ui_guidance (local). Device: needs a build-193 log with a video and with AirPlay playing during a conversion.
- Second log (13:49-14:16): Fall 2's faster start failed on "MP4 packet: Invalid argument" at 22 %; a re-pack that fails on a converter writing error now stays as it is (it plays) instead of restarting from 0 % for ever (`prepare_cloud.REPACK_STOPS`; `test_drive_prepare` 2 tests). Converter cause not yet found (needs time stamps in its log).
- Regression: `test_slowdown` (10), `test_work_state` (20); old pins updated in test_airplay_room, test_conversion_speed, test_hold_menu, test_notices, test_prepare_downloads.


### ISSUE-118 — Phase 4/5 follow-through (2026-11-07)
- The approved nine boards are implemented in portrait XML; working cards and graph labels are shared, all live
  wording comes from `work_state`, and unread messages no longer create a red bell badge. Full source matrix and
  remaining evidence requirements: [BUILD-193-UI-HANDOVER.md](BUILD-193-UI-HANDOVER.md).
- Validation found standalone import/texture/XML defects and an inherited Queue label overlap; fixed with
  generated-XML/asset checks. A queued ready faster-start movie was initially counted twice and dropped by the
  Queue's eligibility filter: it now occupies one summary category, remains reorderable and keeps Play actions.
  Regression: `test_build193_pages.test_queued_faster_start_is_counted_once_and_keeps_play`.
- All initial failures were diagnosed and retested. Visual verification remains PENDING without a Kodi rig;
  build-193 iPhone results are still required. No converter change or device-success claim.


### ISSUE-118 — Eight build-193 review findings

- Owner supplied a source review: title-only transfer joins hid the kept original; download Pause used an unsupported
  pause-file kind; incomplete transfers offered Play; notification cards lacked cancel identifiers; live actions
  dropped QUICKER; recovery opened behind modal windows; graphs re-rendered unchanged samples; first-seen starts reset
  and blocked faster-start jobs showed ineffective retry.
- Fixed all eight in the page/data controllers. Graph files are cached by job and sample signature; stopped
  faster-start retries are hidden rather than unblocking a known converter failure. No converter or slowdown rules
  changed. Per-item fixes and regression names: [BUILD-193-UI-HANDOVER.md](BUILD-193-UI-HANDOVER.md).
- Regression protection: ten additional `test_build193_pages.ReviewFindings` tests, including real controllers with
  fake Kodi controls, correct engine/cancel targets, recovery dismissal ordering and renderer call counts. Device
  verification remains with the owner; the desktop rig is not being used as acceptance evidence.
- Retest: **80/80 test scripts passed** (only `test_drive_runtime.py` excluded); the page suite passes **24 tests**.
  `check_project.py` and `check_ui_guidance.py` both pass with zero issues/problems. No app/IPA build was run.

## ISSUE-119 — Build-193 pages look nothing like the approved mockups (device screenshots, 2026-11-08)

Status: FIXED IN SOURCE on PR #16 (build 194, not built); checked in the desktop Kodi 21.3 rig; iPhone check pending.
- Owner (build 193 on the iPhone): "this looks nothing like the mocs i approved". Empty bars, a filter row and a
  ring instead of the summary card, posters in Up next, "•••" on the cards, a clipped "Library status" link, the step
  repeated under the title, a flat zero graph, half-size icons and a red bell count that never showed.
- Root causes, found by rendering every page in a real Kodi 21.3 build (desktop rig, Xvfb, 603 × 1167):
  (1) a `<control type="progress">` bound to `Window().Property(x)` stays empty in Kodi 21; bars now have ids and are
  set with `setPercent` (`status_ui.id_bar`, summary segments with `setWidth`/`setPosition`);
  (2) a label whose text is only a number ("1") is read as a localized string id; the Queue uses `$NUMBER[n]`;
  (3) Kodi reads `!!X` as `!X`, so `'!' + has(x)` inverted conditions (the bell's count badge never showed, History's
  retry card); `status_ui.neg()` writes the opposite of a condition;
  (4) the icon PNGs keep their shape in the middle half of the 128 px canvas, so a 59-unit icon drew a 30-unit
  shape; `status_ui.glyph()` draws at twice the size around the same centre;
  (5) the generators were written from the roadmap text, not measured against the boards.
- Fix: every board measured with Playwright (`docs/design/build-193-measurements.md`) and rebuilt to it; details per
  board in [BUILD-193-UI-HANDOVER.md](BUILD-193-UI-HANDOVER.md) ("Build 194 visual pass"). No change to
  `work_state.py`, `slowdown.py` or the converter.
- Regression: `test_build193_pages.Board194` (11 tests: sizes against the measurement table within 4 units, segment
  widths and colours, the step bars at 100 % when done, the graph placeholder at rate 0, no "•••", the always-visible
  link, the bell's grey track and count, `$NUMBER`, no `!!` on any page, History card heights); old pins updated in
  test_library_status, test_library_tools, test_notices, test_transfers, test_prepare_downloads, test_check_beside.
- Retest: 80/80 test scripts (only `test_drive_runtime.py` excluded), `check_project.py` and `check_ui_guidance.py`
  pass. Known leftover outside these boards: the landscape AirPlay sheet (`library_tools_page.airplay_sheet`) still
  has one `!!` condition; it is pinned to its earlier source by a test and was left unchanged.

## ISSUE-120 — Ready movies cannot connect over AirPlay (build-194 device log)

Status: FIXED IN SOURCE / DEVICE RETEST PENDING on PR #16. Native r34 diagnostics are staged in source;
build/release/pinning await owner approval. Released KodiAirPlay r33 remains pinned.

- Evidence: owner log 18:11–18:15, repeated AVPlayer -1004, zero server `GET /…`/receiver `client:` lines;
  Play on TV opened twice at 18:12:45 and 18:12:50. Full sanitized analysis:
  [LOG-REVIEW-194.md](LOG-REVIEW-194.md). Raw log stays outside Git.
- Root causes found in source: missing Local Network purpose declaration; picker check/set race; no first-request
  deadline; source URLs mistaken for server diagnostics; incoming accepts/early requests not recorded. The log
  does not prove permission denial: Apple's TN3179 exempts incoming TCP, while unicast TV discovery needs access.
- Fix: stage the purpose string; hold a process-shared lock before the picker; stop an unreachable attempt at
  15 seconds without retry; resume Kodi and persist a needs-you recovery card across script/service interpreters.
  r33 uses shared request-log evidence. r34 source adds strict en0 selection, endpoint/listen/peer/request/timing
  diagnostics with a non-draining API, ordered native session work, cancellation generations and app Settings.
- Regression: 13 tests in `test_play_on_tv_network.py`, plus the staged-plist test in `test_customized_ipa.py`.
  Updated old lock/progress/retry assertions to the corrected behavior. The full sweep also found a pre-existing
  r23 tag/hash assertion after this branch had pinned r24; updated the exact assertion without changing the pin.
- Retest: **82/82 test scripts pass** after that correction/retest (only `test_drive_runtime.py` excluded).
  `check_project.py`, `check_ui_guidance.py`, shell syntax and diff checks pass. Native r34 runtime tests and
  iPhone playback remain pending; no app/native build, release or merge was run in this pass.
- Owner subsequently approved native verification/release and explicitly requested an installable iPhone IPA.
  Added compiled host regressions for non-draining network snapshots, reported listener/endpoint, and excluding
  phone/loopback requests from TV evidence. Preflight found that only `127.0.0.1` was excluded; the whole `127/8`
  range is now excluded and phone User-Agent checks ignore case. Candidate CI must pass before r34 is pinned.
- Delivered in **build 196** after owner approval: native run 42441688126 passed 3,107 checks and 199 end-to-end
  checks with zero failures; r34 publication 42442400925 and IPA run 42442484724 succeeded. Release equals the
  candidate; the downloaded IPA's purpose string, identity and normalized r34/r24 binaries are verified.
  [Delivery evidence](../reports/airplay-r34-delivery.json). Device playback retest remains pending.
- Final 82-script sweep had one scheduling-sensitive `test_drive_prepare.BackgroundUpload` timing failure
  (1.2217 s against 1.0 s). All 26 tests passed unchanged on focused rerun; no worker code or timing threshold was
  altered. All other scripts passed; `test_drive_runtime.py` remained excluded as requested.

## ISSUE-121 — Kodi r24 pin used the archive hash instead of the executable hash

Status: FIXED; verified against the immutable `kodi-ios-portrait-r24` release before the next IPA build.
- Preflight for the owner's approved AirPlay IPA found `executable_release.sha256` contained the ZIP's hash
  (`efdc2f0e…`), while `ios_portrait.fetch` verifies the unpacked `Kodi` executable. Build 195 had failed earlier
  at the stale r23 test assertion, before it reached this fetch; the wrong pin would block the next build too.
- Downloaded the r24 release, checked ZIP integrity and its GitHub asset digest, then hashed `Kodi` inside it:
  `02d5357af48bbf991efddc9ed5babecf06e19b826c5c648cf335c7073d767a80`. Corrected only the checksum; r24 is unchanged.
- Regression: `test_glassbar.IpaTests.test_executable_pin_checks_the_binary_inside_the_zip` accepts the binary pin
  and rejects the archive pin. The repository's exact pin assertion now checks that verified binary digest.
- Build 196 successfully fetched r24 using the corrected pin. Its downloaded executable equals the verified r24
  release after signature removal; the app's build identity records the corrected `02d5357a…` binary checksum.

## ISSUE-122 — Build 196 declares the TV unreachable before the stream opens; screen-lock lifetime is fragile

Status: FIXED IN SOURCE, native candidate verification and device retest pending on PR #16.

- Device evidence: two attempts expire at 15 seconds, but the first listener appears about 129 seconds after
  startup. No TV request or successful playback appears. Local Network is enabled. Full timeline and limits:
  [LOG-REVIEW-196.md](LOG-REVIEW-196.md).
- Root cause: one startup/connection deadline and queued cancellation behind blocking source I/O. AirPlay's
  fragmented-MP4 opener also missed the index option already present in preparation/Kodi r24. Background lifetime
  depended on a diagnostic lease and the download preference; the silent download helper could replace the
  player's audio session. The log proves startup ordering, not the result of the screen-lock fix.
- Fix: indexed opening, interruptible initial HTTP open, 45-second native startup bound, reserved session tickets,
  scoped immediate cancellation, separate TV-choice/connection clocks, no automatic retry, and native playback
  ownership independent of logs/download settings. Preserve the playback/movie audio session and audio background
  mode through screen lock; clear active on completion/failure/close and allow legitimate replay.
- Regression: Python controller/network/lifetime tests; compiled native cancellation, stale work/cleanup and
  indexed-request/byte bounds; staged IPA preserves existing background modes and adds audio. Old source API pins
  now assert the ticket implementation. Candidate build/release, complete suite and iPhone results follow below.
- Owner explicitly requested a new build and screen-locked playback; native r35 release and IPA are authorized.

## ISSUE-123 — Build 194 crashes Kodi when a live page's controls are freed (desktop Kodi rig, 2026-11-08)

Status: FIXED IN SOURCE (not built). **Build 194 must not be installed.**
- Found while running the new rig from scratch: two segfaults in a Python thread, in
  `CGUIProgressControl::SetPercentage` and `Control::setWidth` (addr2line on the rig's kodi-x11).
- Root cause: build 194's pages set bars, segment widths and positions from their 2 s refresh threads. xbmcgui caches
  the Control objects it hands out; Kodi frees a script window's controls when the window closes (WindowXML loads every
  time) and when the skin reloads (Fuse rebuilds its menus on a first start or after an update) while the page stays
  open. The next refresh wrote into freed memory. Reproduced: open Library status, `ReloadSkin()` — crash on cycle 0.
  Notifications' and Transfers' single setPercent (since earlier builds) had the same latent risk.
- Fix: `resources/lib/live_window.Guard` — control changes run only while `Window.IsActive(id)` (false as soon as a
  window starts closing), under a lock the page's own close also takes, and each control is looked up afresh through a
  new `xbmcgui.Window(id)` wrapper instead of the cached one. Used by Library status, its sheet, Notifications,
  Transfers and the Queue.
- Retest in the rig: 20 open → ReloadSkin → close cycles over the four live pages, no crash (build 194 code: crash on
  the first). Regression: `test_build193_pages.Board194.test_issue120_controls_only_while_the_window_is_open`; the
  fake Kodi in test_library_status now refuses a control used after its window closed.

## ISSUE-124 — AirPlay plays only the sound of a prepared HEVC movie on a TCL Roku TV (build 198, 2026-11-08)

Status: FIXED IN SOURCE (native r36 candidate pending); device retest pending.
- Owner: "airplay is connecting to tv but it says action cant be completed and only audio plays on my tv" (photo: a
  music note on the TCL TV). Log (build 198, AirPlay r35): the movie opened in 0.4 s and was inspected by its index in
  1 s (r35 works); every request to the phone's server came from the iPhone itself (AppleCoreMedia, 192.168.1.24);
  the player reported `presentation 0x0, external 0`, then -11819 "Cannot Complete Action".
- Root cause: iOS gave the TV the AirPlay route as sound only: this third-party receiver cannot take the prepared
  4K HEVC picture (already noted in ISSUE-116 and HANDOFF-PROGRESS: "The TCL Roku TV may play only the sound of HEVC";
  build-136-era logs needed H.264 for it). The H.264 compat restart existed for live HLS only: `build-airplay.sh`
  disabled it for `/prepared.mp4`, no trigger covered "external playback never starts", and `kr_remux.c` served the
  prepared file again even in compat mode.
- Fix (r36 source): `kr_remux.c` converts a prepared file in compat mode; the player restarts once with the H.264
  picture when the TV is on an AirPlay route but external playback has not started for 4 s (or Apple's player fails
  that way), unless the picture is already H.264. Prepared movies keep the fast as-is path for TVs that take them.
  Python: going back to opening restarts the TV-choice and connection clocks (`cast.airplay_outcome`), so the
  restart is not cut off as "unreachable"; the card says "Converting the picture for your TV".
- Regression: `test_remux.c` (compat start of a prepared file is converted HLS, then as-is again);
  `test_play_on_tv_network.SoundOnlyRestart` (3). Native compile and host/E2E: candidate CI.

## ISSUE-125 — Build 200: Kodi's plain dialogs instead of the Play on TV card, and the H.264 restart cancelled (2026-11-08)

Status: FIXED IN SOURCE (card: Python; restart: native r37 candidate pending); device retest pending.
- Owner (build 200, photo of Kodi's OK dialog): "didnt work and doesnt look pretty", "none of the new cards ported".
- Cause 1 (the card): `EXCEPTION: XML File for Window is missing`, then "card unavailable (RuntimeError), using Kodi's
  dialogs". The start-up refresh wrote `1080i/IOSAirPlayFlow.xml` after Kodi had listed `1080i`, and Kodi answers
  "does this window file exist" from its directory cache (as for Transfers, build 173). `portrait.refresh_skin`
  re-listed only the portrait folder. Reproduced in the desktop Kodi rig: the same exception before a re-list, the card
  opens after one.
- Fix 1: `refresh_skin` re-lists every folder it wrote a file to (1080i included); `cast.FlowUI` re-lists `1080i`
  and tries once more on RuntimeError.
- Cause 2 (sound only again): r36 began its H.264 restart ("the TV took the sound only … restarting in compat mode"),
  but in the same second `airplayWatch` logged "could not open the stream" (-11819) and set the state to -1. Python
  showed "failed" (its reason was the restart's own note "Converting the picture for this TV…") and closed the player,
  so the restart was cancelled ("start result -1: AirPlay canceled").
- Fix 2 (r37 source): `compatBusy` is set while a restart runs. `airplayWatch`, `routeWatch` and the failed-to-play
  observer ignore the old item's failure while it is set, and a failure counts only after 1.5 s, so the 1 s player
  timer can start the restart first.
- Regression: `test_transfers.NewPageFound` (2 new), `test_play_on_tv_network.SoundOnlyRestart` (old item's failure).
  Native compile and host/E2E: candidate CI.

## ISSUE-126 — Build 201: the TV took the H.264 picture, then stopped (phone reading Drive too slowly); bare Apple alert (2026-11-08)

Status: FIXED IN SOURCE (Python card; native r38 candidate, not published or built: owner tests the Apple TV first).
- Owner (build 201, two photos): "did not work … It didnt even play audio". Apple's "AirPlay stopped: The operation could
  not be completed"; earlier, "Converting the picture for this TV…" written across Apple's skip-10 s buttons.
- Log: the card loaded and the r37 restart held (ISSUE-125 fixed). The TCL TV (MFi AirPlay, 192.168.1.8) took the
  H.264 master for the first time and asked for video segment 0. Converting it needed the movie from Drive: "segment 0
  stopped after 21817 ms, source I/O 20689 ms". The TV gave up after 10 s. The 4K movie is 24.7 Mbit/s (about 3 MB/s);
  Drive delivered about 0.9 MB/s; Kodi's own playback had stalled before Play on TV; a Drive upload ran at 0.20 MB/s.
  The sound waits for the picture, so nothing played. Python had already reported "playing" (on the TV's first
  request) and closed its card, so Apple's alert was all the owner saw.
- Fix: Kodi keeps watching for 45 s after "playing" (`cast.airplay_settle`). While Kodi polls `kodi_airplay_state`,
  native r38 (clock: NSProcessInfo systemUptime; QuartzCore is not linked) leaves a stop to Kodi's card instead of Apple's alert. After the close, `cast.slow_source` reads the
  waits (requests or source reads of 5 s or more, or a near-empty served range) and shows the slow-internet card
  (`airplay_flow` kind `slow_source`, wifi icon, Try again / Keep watching here). The owner wants uploads to keep
  working in the background, so this card has no pause button and nothing is paused. The converting text is now a
  pill at the top, clear of Apple's controls.
- Not fixable in code: converting a 4K movie streamed live from Drive needs about 3 MB/s. A downloaded movie, or an
  HEVC-capable receiver such as the owner's Apple TV (the prepared file plays as-is), avoids it.
- Regression: `test_play_on_tv_network.SlowSource` (7). Desktop Kodi rig: the card renders (3 lines, fits).

## ISSUE-127 — Apple TV: black screen, the Apple TV never asked for the movie (build 201, 2026-11-08)

Status: FIXED IN SOURCE (native r38 candidate pending); device retest pending.
- Owner: "it just gives me a black screen on my phone and nothing changes on the tv" (photo: Apple's player, black,
  only its close button). Log: the prepared movie (7.1 GB, 22 s fragments, 24.7 Mbit/s) opened in 0.26 s and its
  index in 0.8 s; then only the iPhone's own player (AppleCoreMedia) read prepared.mp4, in open ranges at 73, 112, 136,
  168, 214 ... 592 MB, 0.4-3.9 MB each, 3-7 s apart. The Apple TV made no request; the player never became ready.
- Root cause: given a progressive fragmented MP4, AVFoundation walks every fragment header (moof) before it plays; it
  does not use the fragment index at the end (mfra). Across about 400 fragments of a Drive file that would take
  half an hour. The same was measured by karbassi/undertone#8 ("AVFoundation reads the whole fragmented MP4
  regardless"); their fix, like Beamly #11 and Pley #83 for HEVC/HDR, is fMP4 HLS. This probably also explains the
  "sound only" starts of ISSUE-124 (external playback never started because the item was never ready).
- Fix (r38): at start the server reads the prepared file's mfra (two small reads) and serves `prepared.m3u8` (one
  variant: CODECS from the hvcC/avcC and every copied audio codec, RESOLUTION, FRAME-RATE, VIDEO-RANGE PQ/HLG/SDR,
  BANDWIDTH = the largest fragment's rate) and `prepared-media.m3u8` (EXT-X-MAP = ftyp+moov byte range, one
  EXT-X-BYTERANGE per fragment, ENDLIST). Apple's player and the TV fetch only the fragments that play. Without a
  usable index the MP4 itself is served as before.
- Open: the movie's audio tracks are muxed in each fragment, so the TV plays the file's first audio track; picking
  another needs separate renditions. 4K streamed from Drive still needs about 3 MB/s from Drive.
- Regression: test_remux.c (master and media playlists, first range is a moof, init range is ftyp+moov);
  `test_play_on_tv_network.PreparedAsHls`. Device: owner's Apple TV.

## ISSUE-128 — Build 202: AirPlay works on the Apple TV; stopping it went back to the start; no subtitles (2026-11-08)

Status: FIXED IN SOURCE (native r39 candidate pending); device retest pending.
- Owner: "IT WORKED ... if i stop airplay it restarts the movie it seems or goes back to where it started airplaying?
  And subtitles didnt work". Log: prepared HLS over 141 fragments; the Apple TV (10.0.0.40) asked 3.3 s after start
  and played; the player started at 0.0 s although Kodi was further in, and "closed at 246.9 s" left Kodi where it
  had paused. Subtitles: Kodi's choice -2 (the file's default); the prepared file's English text subtitles ride in
  the fragments as mov_text, which HLS ignores.
- Fix (r39): `kodi_airplay_start_at(seconds)` (new export, 27 checked) is set from Kodi's position before
  `kodi_airplay_play`; the native player seeks there once ready. `airplay.activity` (both readers of the native log)
  moves Kodi's paused video to "closed at X s" (`airplay.back_to_kodi`, nothing under 5 s). The prepared master
  lists the file's text subtitles as WebVTT renditions (the converted path's /subs/ playlists and cue files), the
  one Kodi shows (else forced/default/first) as DEFAULT; the native player selects the DEFAULT legible option.
- Not covered: image subtitles (PGS, kept beside the movie as .sup) and external subtitle files over AirPlay.
- Regression: test_remux.c (h264_aac_srt prepared: SUBTITLES group with DEFAULT=YES, playlist and WEBVTT cue file);
  `test_play_on_tv_network.AfterAirPlay` (4).

## ISSUE-129 — Play on TV for any TV on the Wi-Fi: Roku, Chromecast and DLNA got a link they could not open (2026-11-08)

Status: FIXED IN SOURCE (native r40 candidate pending; build 204); device test pending.
- Owner (build 203): "ideally i want it to work on any tv thats connected to the same wifi". Research:
  Roku locked "Play on Roku" (channel 15985) in Roku OS 11.5 (home-assistant/core#83819: it opens and exits), which is
  why this TCL Roku TV answered 404 (build 138); Home Assistant moved to the free Media Assistant channel
  (MedievalApple/Media-Assistant, Channel Store id 782875: /launch/782875 or /input with u, t=v, videoName,
  videoFormat). Roku is not a DLNA renderer. No maintained iOS library covers every TV; every caster combines
  AirPlay, Cast, DLNA and Roku ECP, as Play on TV already does.
- Root cause for the non-AirPlay TVs: they were sent Kodi's link with the phone's address; Drive's and Elementum's
  helpers answer on 127.0.0.1 only, so the TV could never open it, and Drive links need the phone anyway.
- Fix (r40): `kodi_airplay_serve(url, compat, out)` (export 28) starts the phone's server on the Wi-Fi address without
  Apple's player and returns its link: prepared movies as the byte-range HLS (ISSUE-127), other files remuxed.
  Play on TV (`cast.tv_link`) gives Roku and Chromecast that playlist, DLNA the prepared MP4 itself; an HLS source
  or an unavailable server keeps Kodi's link. Roku: Media Assistant first, then the old channel; a 404 says to add
  Media Assistant (or use AirPlay on a Roku TV). Chromecast starts at Kodi's position. Kodi must stay open (the
  phone serves the movie).
- Open: TVs without HEVC get the picture as it is (compat 0); a per-TV H.264 choice needs each TV's capabilities.
- Regression: `test_play_on_tv_network.AnyTv` (4), `test_updates_calibration` (Media Assistant URL, order, 404 text).

## ISSUE-130 — Customisation said 15 rows on Home (7 showed) and Add seemed to do nothing (build 202, 2026-11-08)

Status: FIXED IN SOURCE (Python; build 204); device retest pending.
- Owner (screenshot of Tabs & Rows › Home, "15 rows on the page"): "i only have 7 rows ... when i press add and
  nothing is added ... this applies to all, home movies and tv". The editor and Home read the same Skin Variables
  lists (rows_editor.NODES = portrait.NODES), so changes did reach Home; but Home hides a row while its list is empty
  (portrait.row: visible while NumItems > 0), e.g. Trakt rows without a Trakt sign-in (the desktop Kodi rig shows the
  Trakt 401) and empty library rows, while the page counted every row that could show. Add appended the new row
  after all the others, below the fold on the page and at the very end of Home.
- Fix: `rows_editor.empty_rows` judges each row as Home does: TMDb Helper rows by the service's listing copy (it keeps
  one for every list with items; without any copy, nothing is judged), library rows by a one-item JSON-RPC
  Files.GetDirectory (`folder_counter`), add-on rows not at all. Empty rows are faded with "Empty now · hidden on Home"
  or "Empty · sign in to Trakt", and the header counts only what shows ("10 rows on the page · 2 empty right now");
  the Customisation counts use the same rule. Add puts the new row first, under Continue Watching, and says so.
- Regression: `test_customisation.RowsScript` (count, empty marks, no-copy case, folder counter, Add first). Desktop
  Kodi rig: page renders, text fits (screenshot not committed).

## ISSUE-131 — Tabs & Rows: trending lists to add, rows added at the bottom, and a 4.7 s wait after every change (2026-11-08)

Status: FIXED IN SOURCE (Python; desktop Kodi rig verified); device retest pending.
- Owner (build 204): "I want trending movies to be a option and trending shows, and Now Playing under movies ... I do
  like the home how it is but make it so i can add the rows i want ... add a row and see if it populates correctly at
  the bottom and switch rows around ... ensure its quick".
- Add Row lists: Home: Trending Movies, Trending Shows, Trakt Trending Movies/Shows, Now Playing, Airing Today,
  Popular, Recommended (Trakt), Recently Added; Movies: Trending Movies, Trakt Trending Movies, Now Playing first;
  TV: Trending Shows, Trakt Trending Shows, Airing Today first. Home's own rows are unchanged.
- A new row goes last among the rows Home shows (ISSUE-130 had put it first) and the page moves its focus to it.
- Speed: closing the page ran the full portrait refresh (every texture drawn in Python): 4.7 s in the rig before Home
  changed. `portrait.refresh_rows` rewrites only the hub files (`row_files`, identical to the full build's; a test
  compares them) and brings the start-up marker up to date: 0.055-0.063 s in the rig.
- Desktop Kodi rig (real UI, SendClick): Add → Trending Movies landed at the bottom of Home with 21 titles; moved up
  three places and the rows around it kept their titles (21 each); Netflix Original Movies moved to the top; TV:
  Trending Shows added at the bottom with 21 titles. The rig's lists were put back afterwards.
- Regression: `test_customisation` (Add Row lists, add position and focus, row_files = full build).

## ISSUE-132 — Build 205: seeking nearly froze the app; one season showed as one download; no buffering progress (2026-11-08)

Status: FIXED IN SOURCE (Python; build 206); device retest pending.
- Owner: seeking an Umbrella episode (Dragon Ball Super: Beerus, H.264 + E-AC3 + ASS) "completely nearly broke the
  app ... have it show like a buffer percentage ... it should use download speeds"; "i went to download a entire
  season and it seems only 1 thing is downloading".
- Log: `AddVideoPicture - timeout waiting for render` at 11:25:20 and :26 while an AllDebrid → Drive copy read 32 MB in
  2.4 s (13 MB/s) during playback (slowdown gave background work 35% of the time but each read ran at line speed);
  Kodi's cache was 20 MB at 4x.
- Fix: background downloads (AllDebrid copy reads, preparation's Drive reads) keep under 1 MB/s while a video or
  AirPlay plays and wait while Kodi buffers (`slowdown` reason 'buffering' from Player.Caching); uploads keep the
  time share. Kodi's cache set once to 96 MB at 10x (`portrait.tune_cache`). "Buffering 45%" pill
  (`Custom_1156_Buffering.xml`, Player.CacheLevel) between the centre controls and the title; rendered in the desktop
  Kodi rig (forced visible: "Buffering 99%"). A video window control was not drawn in the rig, hence its own dialog.
- Season queue: the copy names its episode and "N of M"; the season's other episodes and the other AllDebrid jobs are
  listed as up next (`work_state.drive_next`, Queue page).
- Regression: test_slowdown.DownloadCap (5), test_work_state.SeasonQueue (4), test_portrait.BufferingPill (2).

## ISSUE-133 — "I pressed full season" (Lanterns) and got episode 1 only; Next Episode button (2026-11-08)

Status: FIXED IN SOURCE (Python; build 206); device retest pending.
- Log: Elementum's season download (/show/95350/season/1/download) used the version picked from 29 results of
  "lanterns season 1"; it held one 8.4 GB file, S01E01 (4K HEVC HDR), which was copied, listed and prepared. A season
  search lists single-episode releases too and the version page did not say which was which.
- Fix: `source_match.coverage` tells a season pack from "Episode 1 only"; the version page lists full seasons first with
  a FULL SEASON / EPISODE N ONLY badge. A season download that held one episode ends with "Only one episode was in
  that download" instead of "Saved to Google Drive".
- Next Episode (owner: "i want a button at the top to watch next episode"): top left beside back, episodes only;
  `next_episode.py` plays the playlist's next item, else TMDb Helper's play for the same show and episode + 1 (by the
  show's TMDb id when tagged, else its title). Not yet seen in the rig (the owner stopped that run).
- Regression: test_source_match.SeasonCoverage (2), test_debrid_drive (one-episode season), test_next_episode (4).
