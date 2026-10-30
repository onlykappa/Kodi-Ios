# Changelog

## 2026-10-29T18:27:38.692486+00:00 — roadmap planning

Created five-phase roadmap and persistent trackers, reviewed historical backup/inventory evidence, retained existing documentation and known failures, and added planning consistency validation. No migration implementation started.

## Historical baseline

Commits 3bf0e63 and c5aecaf introduced the sanitized snapshot, verified backup metadata, private account preservation instructions and scanner/tests. Those reports describe prior results, not new device or recovery tests.

## Phase 1 — security, baseline and isolated recovery

Replaced fixed roadmap totals/status lists with task-derived progress; added four regression tests and mandatory review gates. Verified both archives, original source immutability, publication exclusions, snapshot/history/private-value checks and isolated recovery. Logged parser and report-name failures with fixes/retests. Retained private recovery copy and documented rollback; no source or media changes. Phase 1 READY FOR REVIEW; Phase 2 requires authorization.

## Phase 2 authorization — P2-002 blocked

Recorded owner approval of Phase 1 and authorization of Phase 2. Requested missing target and signing details. No task completion added; progress remains 7/32. Phase 2 dependency order prevents compatibility implementation before target constraints are established.

Deployment requirement update: prioritize an unsigned IPA and existing owner sideloader; Phase 2 now includes bundling/import feasibility and Phase 4 explicitly covers artifact structure, provenance, entitlements, integrity and real-device signing/install tests. Credentials remain external. No IPA assembled or device compatibility asserted.

## Phase 2 — static target and compatibility review

Recorded confirmed non-jailbroken iPhone 16 Pro/iOS 27.0.1 target; owner waived sideloader identity and approved sports deferral. Researched official matching 21.3 ARM64 DEB foundation and conversion; exact OS support remains unverified. Classified all 240 baseline manifest records, produced a deterministic 32-file provisional import configuration with a 48-entry candidate dependency closure, portable paths, menu-slot adaptation mapping and upstream-syntax touch adapter. Removed active Umbrella/native/backend references from target only. Documented private account mappings and separate-import packaging tradeoff. Six new target regressions pass; source/baseline unchanged. No IPA assembled, no device success claimed, no Phase 3 started.

## Phase 3 authorization and visual requirements

Phase 2 static review passed. Added seven future tasks (39 total), preserving completed history and dynamic counts. Added real-code comparison, simulator investigation, actual-device screen captures, visual regression fixes/retests and mandatory final owner screenshot approval. Phase 4 work has not begun.

## Phase 3 research, owner choice and test-executor blocker

Compared maintained direct add-on/public or private relay, rclone bridge and older alternative using primary sources. Owner selected direct add-on/public relay. Recorded read-only OAuth trust/lifecycle design, current endpoint and imminent legacy endpoint retirement, cost/quota caveats and source pins. Verified 74 upstream text files outside Git. Preflight ran 42 upstream tests: 34 pass, eight error on denied local sockets. Preserved failure evidence and blocked P3-004; no integration-ready claim or Phase 4 work. No Google account or media accessed.

## Approved alternate test executor

Owner approved the capped GitHub Actions job. Prepared the reviewed workflow with pinned public source, five-minute timeout, no checkout/secrets/token permissions. Added a single-path workflow exception to the publication allowlist; all other unexpected workflows remain rejected. Run results pending; original failed tests retained.

## Drive integration implementation and host-test recovery

Owner-approved capped Actions run passed all 42 pinned upstream tests. Retained original EPERM failure and cleanup warnings. Added credential-free Drive menu/preferences, disabled optional directory listing and export-folder cleanup, extended candidate dependencies to 51, built two upstream-only reproducible add-on ZIPs outside Git, and verified package hashes/contents/secret boundaries. Provider tests (12) and actual pinned-source refresh/resume mocks (9) pass. No Google account or iPhone accessed; no IPA built.

Phase 3 available validation complete: 43 project regressions, 42 upstream CI cases, 12 provider cases and nine source-backed refresh/resume mocks pass. Read-only source comparison verifies all 22,463 original files unchanged. Added setup/recovery, scope/cost/authentication limitations and pending real-device matrix. Task-derived progress 21/39 (53.85%); STOP for independent Phase 3 review. Unsigned ARM64 IPA objective preserved; no Phase 4 implementation, account access, media upload, merge or release.

Phase 3 owner review accepted; Phase 4 authorized. Began P4-001 acquisition/static investigation only. Local DNS prevented foundation download; prepared capped isolated official-DEB inspection with pinned GitHub-owned actions and eight Mach-O parser regressions. Device acceptance and roadmap sequencing remain unresolved; no Phase 4 task marked complete.

Phase 4 partial delivery: official foundation SHA-256 recorded; unsigned diagnostic IPA built in capped CI with 151 ARM64 native images audited and 150 active signatures removed, ZIP/layout checks passed. Source comparison verified 3,336 identical Fuse files and preserved two generated differences privately. Installed Flatpak and official iOS build reference the same Kodi source revision. Documented simulator constraints; prepared 184 capture-checklist entries and owner signing/import/functional/rollback procedure. Full migration/import decision, signing/device/screenshot evidence remain blocked; no Phase 4 task checked complete and no Phase 5 work. Added IPA/DEB/signing-artifact ignore/scanner protections.

Follow-up Phase 4 validation: independent rebuild produced the same complete IPA checksum. Recorded original private/jailbreak entitlement metadata without carrying it into the unsigned candidate. Capture generator now preserves future failed captures and changed/removed route history, covered by three regressions. Phase 3 phase status reconciled to owner-approved COMPLETE; Phase 4 tasks remain unchecked/blocked pending full acceptance.

Packaging safety audit added explicit source/output isolation guards with two regression cases; valid build layout/bytes are unchanged. Final local project regression count is derived from test-runner results (68 passing tests), plus static checks and secret/history/private-source-value comparison. All original 22,463 source files remain unchanged.

Owner reports diagnostic IPA install/launch success and explicitly approves separate import; recorded scope-limited evidence and completed P4-001 after roadmap validation. Elementum is the primary, phone-local engine is requested, and no remote host is approved. Recovered previously missing vetted Fuse view inputs. Prepared source-pinned native build investigation and one owner-approved eight-minute macOS probe; no iOS engine exists yet. Foundation job now audits provided native/API dependencies without regenerating/uploading duplicate diagnostic IPAs.

## Phase 4 — customized import preparation and owner scope changes

Owner confirms diagnostic installation/launch and approves separate import; no other device result inferred. Owner removes YouTube/Fusion and defers native Elementum. Preserve 184 screenshot requirements with stable identities when routes move. Add isolated offline import, dependency/hash/ZIP validation, repeated-import conflict protection, private clean snapshots and rollback/export tests. Add iOS-only first-run enable helper using Kodi JSON-RPC, explicit watch-choice integration and normal long-press context action; actual phone behavior remains unverified. Validate preserved Fuse view expressions, retract the mistaken missing-input diagnosis and remove the duplicate. Audit actual foundation dependencies. Prepare pinned-public-source acquisition/build workflow; artifact completion pending real CI. Record failed Mac missing-Go probe and test-invocation/fixture failures with retests. No original Deck writes, engine, Phase 5, merge or release.

## Phase 4 — fixed import test kit ready for owner testing

Published validated kit (run 40981957027/artifact 12945112472), 38 add-on packages and 30 configuration files; fixed importer preserves all 7324 source files. Complete-bundle repeat/rollback synthetic smoke passes and 133 host regressions pass. Retained failed packaging attempts and superseded artifact. Steam Deck immutability and secret checks pass. No new IPA/signing change; use owner-tested foundation. Actual phone export/import, Fuse UI/touch, Drive playback, screenshots/comparisons and rollback remain blocked. Native Elementum deferred. Phase 4 review package is partial; no Phase 5, merge or release.

## Phase 4 — fully bundled automatic IPA implementation

Owner supersedes manual import (DEC-022). Implement optional packaged bootstrap service, automatic profile initialization with hashes/private recovery journal, live settings/skin APIs, repeat-launch no-overwrite behavior and program recovery entrypoint. Bundle all validated source addon/configuration payloads, register through Kodi's system addon manifest and normal JSON-RPC; no SQLite edits/native injection. Add eight bootstrap and three packaging regressions; all 144 tests in 19 suites pass. Extend isolated Linux workflow to build/inspect/upload Kodi-iOS-Customized.ipa; actual run pending. Diagnostic artifact remains intact; no actual-device success or Elementum support claimed.

## Phase 4 — downloadable fully customized unsigned IPA

Successful CI 41058684326/artifact 12978745226 supplies Kodi-iOS-Customized.ipa (577498519 bytes, SHA-256 2eac079b95b0f666298717ad47e77bb476ac82c956c5b997982191ddc40593b2). Bundle includes approved 38 addon packages plus bootstrap, 30 configurations and automatic writable skin initialization/normal Kodi registration/activation/recovery. 149 host tests pass; archive/source/seed/native structure checks pass. Normal Keep Skin confirmation may require one tap; no consent auto-accepted. Diagnostic artifact preserved; no owner secrets/media or Elementum engine. Owner-device signing/startup, UI/touch, Drive, screenshots/restart/rollback still require evidence. No Phase 5, merge or release.

## Phase 4 — owner-reported Fuse failure and Touch-r1 repair

Recorded actual failure/screenshot privately; no skin success inferred. Reproduced iOS-hidden mouse-setting bootstrap rollback and permanent failed-marker behavior. Add revision-scoped retry/history, mandatory repair service, inline widget-independent navigation in 32 windows, native recovery/browse/settings menu, gestures and local helper diagnostics. Preserve widgets, original layout assets, original Steam Deck and prior IPA. Add targeted upgrade for already initialized phones and live skin preference synchronization/rebuild. Host tests/XML audit pass; new artifact and physical retest pending. No further feature development/Phase 5.

## Phase 4 — Touch-r1 IPA available for owner retest

Resumed owner pause and verified successful run 41068166024/artifact 12983492116. Publish Kodi-iOS-Customized-Touch-r1.ipa (577522290 bytes; SHA-256 9c72b195494924fddfa67f24627546ea59f64efe0f04b373647d907e9034db84). Reproduced bootstrap defects fixed, permanent native Settings/Recovery and touch navigation host-tested, existing profiles upgraded with backups/history, all 165 tests pass. Actual phone usability remains pending and prior failure stays recorded. Preserve previous IPA, source Deck, credentials and 184 capture requirements. No Phase 5/merge.
