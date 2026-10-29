# Decision register

## DEC-001 — Accepted owner constraints

Retain Arctic Fuse 3 experience where feasible; exclude Umbrella from future target; keep original Deck/SSD read-only; preserve saved account state privately. Alternative of publishing raw backups rejected because they contain credentials. Evidence: README.md and docs/private-account-transfer.md. Roadmap approval does not approve merge or release.

## DEC-002 — Pending target decision

Owner must provide iPhone model, iOS version, jailbreak status, signing computer/access and acceptable renewal constraints. Compare supported installation methods with current primary sources before selection. Required before P2-003; reconfirm in P4-001.

## DEC-003 — Pending scope choices

Owner must prioritize retained menus/widgets/add-ons, acceptable native-feature replacements, account-login fallback, and private library/watch-state migration versus rebuild. Preserve Fuse by default; any omissions require explicit acceptance. No source cleanup is planned.

## DEC-004 — Pending Drive architecture

Compare maintained direct Kodi integration with a private streaming bridge for iOS support, OAuth, quotas, hosting cost and availability. No selection yet; owner approval required before external infrastructure or spending. Media stays in existing 5 TB Drive.

## DEC-005 — Planning and release gates

Five sequential phases with early device fact gathering; static validation cannot certify runtime support. Alternative of implementing immediately rejected by explicit owner instruction. Status: READY FOR REVIEW. Separate independent review then explicit owner roadmap approval required; final merge/release approval remains separate.

## DEC-006 — Phase 1 authorization and phase review gates

Owner approved Phase 1 starting P1-002, conditional on dynamic progress and regression tests. Implemented mandatory STOP/review gates after every phase. Phase 2 is not authorized.

## DEC-007 — Phase 1 approved; Phase 2 authorized

Owner reviewed Phase 1 and authorized P2-002 through P2-009 in dependency order. Preserve Arctic Fuse 3, exclude Umbrella only from future target, retain private state outside Git. P2-002 requires owner target facts; requested without asking for secrets. No Phase 3/merge/release authorization.

## DEC-008 — Unsigned IPA deployment

Owner has an existing sideloader capable of signing/installing unsigned IPAs. Final artifact is an unsigned Kodi iOS IPA using a trusted compatible foundation. Investigate safe bundle integration versus post-install import; do not assume user-writable profile placement inside the application bundle. Preserve Arctic Fuse where compatible. Keep credentials/account state/media external. Phase 4 validates structure, architectures, deployment target, dependencies, entitlements/signature handling, checksums, owner sideloader signing and actual iPhone behavior. Tool name/version and device facts still required; no successful-runtime claim from static checks.

## DEC-009 — Confirmed target and owner decisions

iPhone 16 Pro, iOS 27.0.1, non-jailbroken, Kodi absent. Final artifact unsigned ARM64 Kodi IPA. Owner manages signing with existing iPhone sideloader and waives its identity for unsigned preparation. Owner explicitly approves deferral of broken sports integration. Prefer matching stable official 21.3 DEB-to-IPA foundation; precise OS compatibility unverified. Separate sanitized import is the preferred initial engineering approach pending owner review of bundling tradeoff; investigate proven bootstrap during Phase 4. Evidence: reports/ios-target.json and docs/ios-foundation.md.

## DEC-010 — Phase 2 accepted; Phase 3 and visual-roadmap expansion

Owner approved Phase 2 static work and authorized Phase 3 only. Added seven unstarted tasks for real source/skin-code comparison, simulator feasibility, exhaustive screen roster/captures, side-by-side fixes/retests, final visual regressions and explicit owner screenshot-review gate. Real iPhone 16 Pro/iOS 27.0.1 evidence remains mandatory. Drive architecture requires owner selection before implementation or hosting/spending; no architecture selected.

## DEC-011 — Approved direct Drive integration

Owner explicitly chose direct Kodi add-on with maintainer OAuth relay (no separate media host). Prefer pinned plugin.googledrive 1.6.8/common 1.5.11 and current HTTPS drive.signinserver.com relay, with read-only Drive scope. No self-hosting, paid service, cloud billing or source-Deck server is approved. Relay trust includes token exchange/refresh; exact deployed-service behavior and iOS runtime remain unverified. See docs/google-drive.md and docs/google-drive-oauth-design.md. Required stream tests are blocked by sandbox socket denial, so integration/Phase 3 completion is not authorized by this choice alone.

## DEC-012 — Capped Actions executor approved

Owner approved the proposed isolated GitHub Actions job to resolve the local socket-test blocker. Job timeout five minutes, pinned public upstream source only, no repository checkout, Google account, personal media or secrets; no requested token permissions (GitHub exposes implicit metadata read). Does not authorize Phase 4 or media hosting. Publish the prepared workflow, inspect actual run/logs, and preserve the failed local preflight. Approval does not establish a passing test result.

## DEC-013 — Phase 3 evidence and mandatory stop

The approved run 40940315803 passed all 42 unchanged pinned common-module tests, resolving ISSUE-014 for host validation. Keep the original local EPERM report and nonfatal cleanup warnings. Phase 3 packages/configuration, 12 provider tests, nine source-backed refresh/resume mocks and recovery instructions are complete. No personal Google account or media was accessed. Phase 3 completion is limited to available host/static evidence: real iPhone authorization, playback, library persistence, source/skin parity, entitlements and IPA signing remain Phase 4. STOP at REVIEW-GATE-3; no Phase 4 work, merge or release authorized.

## DEC-014 — Phase 3 approved; Phase 4 authorized

Owner accepted independent Phase 3 review and authorized Phase 4 only. Owner supplies actual iPhone testing/screenshots later. No actual-device result may be inferred from host inspection. A capped five-minute Actions acquisition/static-inspection job is within the authorized foundation investigation; it fetches the official 21.3 HTTPS DEB, runs no package scripts or target executable, requests repository contents read only, uses SHA-pinned GitHub-owned actions and stores only public binary metadata as a short-lived private artifact. No media, secrets, account state or source Deck files enter the runner. No Phase 5, merge or release. P4-001 currently contains an actual-device behavior acceptance clause that also appears in P4-003/P4-005; retain that requirement and do not check it off prematurely.

## DEC-015 — Diagnostic unsigned candidate and separate runtime proof

Static acquisition found original native signatures. Deterministic candidate builder removes active LC_CODE_SIGNATURE commands, zeros corresponding original regions without changing file lengths, preserves executable modes/symlinks, and verifies all 151 recognized thin ARM64 images and bundled required dylib paths. This is a diagnostic foundation candidate only, not a fully migrated or certified signer-compatible IPA; 150 signatures removed. The owner must sign all native images and supply actual launch/OS evidence. No custom bootstrap/native executable is injected. Owner choice for separate first-run import versus automatic initialization is pending, so full migration packaging remains BLOCKED. Preserve original two generated Fuse files privately until target handling and visual retests are established. Simulator is locally infeasible and tagged Kodi build guide says unsupported; no screenshots are fabricated. P4-001 acceptance still includes actual behavior, so dependent tasks remain unchecked/blocked despite prepared host investigations. No requirement waived or phase gate passed.
