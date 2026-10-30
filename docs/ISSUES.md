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
