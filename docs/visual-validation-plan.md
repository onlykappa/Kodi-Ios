# Future source, simulator and visual validation plan

Status: NOT STARTED. This document plans Phase 4/5 requirements; no screenshots, source comparison, simulator execution or device tests are claimed.

Task ownership: P4-007 real Kodi/Arctic Fuse source comparison; P4-008 simulator feasibility; P4-009 exhaustive screen roster; P4-010 captures; P4-011 side-by-side comparison/fixes; P5-006 visual regression; P5-007 final owner screenshot review. All depend on explicit Phase 4 authorization after the Phase 3 review gate. Final owner screenshot approval precedes final release approval.

## Real code, not settings-only comparison

Pin official Kodi source revision, build recipe/toolchain, upstream patches and matching Arctic Fuse 3 revision. Compare actual source and assets against verified private copied source/skin files, with hashes and a diff manifest. Identify source-local modifications and the target replacement for each. Do not certify parity from matching version labels, Python manifest declarations or exported preferences alone. Licenses/provenance and unavailable revisions are recorded; failed retrievals stay in the issue register.

## Simulator feasibility

Inventory available macOS/Xcode/simulator runtime and iPhone 16 Pro profiles. Determine whether a simulator-specific Kodi binary can be built or obtained from trusted source. An ARM64 iPhoneOS binary and an ARM64 simulator binary have different platform targets; CPU architecture alone is insufficient. Record a supported, unsupported or infeasible conclusion with evidence and actual constraints. Simulator tests may help layout iteration if feasible but never substitute for real-device testing on the non-jailbroken iPhone 16 Pro running iOS 27.0.1. No cloud Mac rental, account access or spending without approval.

## Exhaustive roster and fixture contract

Inventory the union of major original and target routes before capture, including every top-level menu and submenu; every retained widget category/loading/empty/error state; media lists, details, artwork and search; add-on browser/configuration; skin/layout/navigation and applicable general/system/player/interface/media/services/settings pages; selection/context/confirmation/error dialogs; playback launch, video OSD, controls, seek, subtitles, audio options, pause and resume. Include portrait/landscape and keyboard/safe-area states where relevant. Every omission needs an issue and owner acceptance, not a deleted row.

Use synthetic metadata and nonpersonal licensed test videos only. A capture record includes stable screen/route ID, menu/widget identity, fixture ID, platform, app/skin/source hashes, OS/device, orientation, viewport, resolution, timestamp, expected behavior, original/target capture hashes, privacy-review status and issue/retest links. No live account identifiers, private folder names, tokens, personal artwork or media frames may reach GitHub.

## Safe original baseline and capture storage

Reproduce the original appearance from a verified private isolated configuration copy. Do not launch the working Steam Deck profile or mount/write original media just to capture screens. Label the baseline as a safe-copy reproduction and document discrepancies. If an original screen cannot be rendered safely, preserve that gap as a blocker rather than inventing a screenshot.

Raw screenshots and videos stay outside Git, alongside a private capture manifest. Current repository image exclusions remain in place. Record only sanitized evidence metadata/hashes in Git; use a trusted private channel for owner image review. Any future publication of sanitized screenshots needs an explicit privacy check and a narrowly scoped allowlist; no wholesale image-unignore rule.

## Comparison, diagnosis and retesting

Present every baseline/iPhone pair side by side using the same fixture. Normalize viewports only for the comparison copy; preserve untouched captures and record crop/scale parameters. Record intentional aspect-ratio, safe-area and OS font differences separately from lost menus/widgets, clipped labels, inaccessible controls and unwanted layout/color changes. Visual similarity does not establish functional/touch equivalence; exercise each relevant touch action.

Log every regression with issue ID, severity, reproduction, root cause, expected/observed behavior, artifact hashes, fix revision and retest result. Do not remove failed captures. Apply minimal fixes to target copies only, recapture affected screens plus neighboring routes, then rerun the complete roster at P5-006. A final P5-007 owner review must explicitly accept all comparisons and justified differences. Missing screenshots or unresolved rejected changes block release, regardless of static test success.
