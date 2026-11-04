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
Status: PARTIAL SOURCE FIX; long Drive seek delays, all-format coverage and device acceptance remain OPEN.
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
