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

## DEC-016 — Owner-reported diagnostic install/launch and import approval

Recorded 2026-10-29T23:31:52.469988+00:00. Owner explicitly confirms successful diagnostic Kodi 21.3 ARM64 installation/launch on iPhone 16 Pro/iOS 27.0.1 and approves separate sanitized first-run configuration/add-on import. Prior reviewer recommendation alone was not treated as approval. Evidence: reports/owner-device-evidence.json. Basic operation is an observation, not a complete runtime test suite. No migrated skin, dependencies, playback, screenshots or rollback success inferred.

## DEC-017 — Elementum primary and navigation priorities

Owner explicitly selects Elementum, without substitution. Native iOS engine and remote-client alternatives must be investigated. No external hosting or Deck always-on service approved. Single tap should expose available watch options, Elementum first when usable; long press opens ordinary Kodi context actions. Preserve metadata/artwork/episode navigation; Google Drive is separate, not automatic per-title mapping. Umbrella remains deferred with existing target exclusions. Remote host choice is pending and no engine is provisioned.

## DEC-018 — Owner requires phone-local Elementum engine

Owner answered the remote-host question by requesting the engine on the phone. This is not approval for a remote host, cloud service or Deck daemon. Investigate a real native iOS port, dependencies and in-process Kodi integration. The existing IPA has no Elementum engine. Native build tools/Apple SDK are unavailable locally; the concrete capped Mac compilation-probe proposal is docs/elementum-ios-port.md. No engine success or build-executor approval inferred. Continue independent safe import preparation while this prerequisite is blocked.

## DEC-019 — One capped macOS engine build probe approved

Owner explicitly approved one GitHub Actions macOS probe with an eight-minute maximum, consuming Actions allowance. Workflow is edited-event/temporary-marker gated, same-repository PR #1 only, contents-read token, SHA-pinned checkout, no secrets/media/signing keys. Remove marker immediately after triggering once. Actual source compilation failure is valid blocker evidence, not engine success; no automatic retry, build-server provisioning or playback hosting approved.

DEC-019 result: one actual Mac job executed (40975489124) and failed at missing Go before compilation; the two earlier event runs were skipped. Marker is removed. Another Mac attempt requires owner approval after explicit toolchain setup. Native functionality remains unverified.

## DEC-020 — YouTube fully excluded from iOS target

Owner explicitly authorizes removing YouTube and YouTube Fusion. Remove their target roots, shortcuts/widgets, saved view overrides and now-unneeded dependency closure; retain baseline, source Deck and private backups. Unpublished copied Fusion code/UI assets and their proposed PNG exception were discarded before publication; no image allowlist is introduced. Original 184 capture records remain, with owner-approved absence expectations for affected target routes. No Elementum replacement or Umbrella activation follows from this instruction.

## DEC-021 — Defer the native Elementum engine during Phase 4 preparation

Owner explicitly says to skip the engine for now and finish Phase 4. Keep the phone-local requirement open; no remote fallback, alternative primary or working-engine claim. Preserve the diagnostic IPA; prepare separate sanitized Fuse/Drive import for testing. Engine compilation/playback remain deferred and unverified. Phase 5 remains unauthorized.

## DEC-022 — Owner replaces manual import with fully bundled IPA

Owner explicitly authorizes implementation/build/test/debug of Kodi-iOS-Customized.ipa with automatic setup, no ZIP import/file copying/profile transfer. This supersedes DEC-016's separate-import deployment choice. Reuse the validated cc5d7eb7... configuration contents; package addons as optional system addons in Kodi's real addon-manifest.xml (normal discovery/registration), plus an optional startup service. Optional system addons are initially enabled by tagged CAddonDatabase::SyncInstalled; existing disabled state is changed only by documented JSON-RPC after private recovery journal is created. Seed userdata once through a packaged service, use live Settings APIs rather than replacing live guisettings.xml, preserve unknown/private add-on settings, and retain private rollback copies. No native binary/entitlement injection, Apple SDK/Mac job or Elementum engine is needed for this resource-only approach. Existing diagnostic IPA remains fallback. Host build/source evidence does not prove actual iPhone startup, signing, UI, Drive or recovery. Phase 4 only; no merge/release.

## DEC-023 — iOS Fuse usability and repair before features

Owner confirms device failure and prioritizes Arctic Fuse usability, not a skin substitute. Add permanent native skin controls and widget-independent Settings/recovery access; preserve appearance/content layouts except the intentional iOS navigation strip and safe initial focus. Keep all original widget definitions, clearly distinguish empty local library from unverified provider failures, and retain 184 screenshot requirements. Targeted repair must run on already initialized phones without deleting profiles or requiring manual imports; failed recovered setup may retry once on changed seed with history preserved. Bootstrap is a required packaged component, while other approved addons stay optional. Publish a separately named Touch-r1 IPA artifact and preserve prior build. Real-device touch success remains unverified until owner retests. No Phase 5, merge or Elementum work.

## DEC-024 — Owner merges the iOS work to main as version 1 (2026-11-01)

The owner explicitly authorized merging the iOS work into `main` once the r13 build was out ("we can merge our work to main once R13 is pushed … r13 is basically version 1 out of the beta"). The review build is build-111 (commit 03e22c6, Kodi executable r13). `main` (644ce22, project init) is an ancestor of `feature/ios-migration`, so the merge is a fast-forward through PR #1; no history is rewritten and no force-push is used. This supersedes the "no merge" stop gate for this merge only. It does not mark any device test as passed: the owner's review of build-111 is still pending and device results are recorded only with the owner's evidence. Next, at the owner's request: repository cleanup (version names instead of rN, plainly named workflows and component releases, README, stale branches removed only after the owner confirms the list) and a roadmap rework from version 1.

- 2026-11-05 (PR 8): Drive OAuth sign-in moves from the public relay `drive.signinserver.com` to the owner's own worker `https://kodi-signin.ballaking1738.workers.dev`, so refresh tokens no longer pass through a third-party server. Older docs that name the public relay describe the earlier design.

## DEC-025 — Merge PR #8 and publish a fresh test IPA

Owner explicitly requests: "merge pr 8 so we can start fresh and push me ipa for testing". This authorizes merging the completed draft and the native build/release/pin plus IPA delivery needed to test all changes, superseding the prior no-merge/no-IPA restriction for this delivery. The new show-scroll/parent-row patch is not in r22: build unique r23, verify binary/release/provenance, then pin r23 and publish the test IPA. Avoid a misleading intermediate IPA from the old native pin by skipping merge-triggered CI and starting the native build first. Preserve AirPlay r12/GlassBar r5 and owner data; no branch deletion or device-success claim is implied.

## DEC-028 — Duplicates: the extra copy is deleted; check before downloading

Owner (2026-11-05), on "Lanterns" and "Lanterns (2026)" each holding S1 E1: "it should be deleted", and yes to a duplicate check before Elementum downloads. The extra copy is removed only after the kept copy is confirmed on Drive. Drive copies go to Drive's Trash (restorable for 30 days), never a permanent delete. Phone copies are removed under the existing "remove phone copies after upload" setting. Copies with different named years are never treated as duplicates. Details: ISSUE-103. No merge or release implied.

## DEC-026 — Permanent Apple UI guidance for agents (PR #11)

Owner asked (2026-11-05) to permanently integrate Apple UI design resources so every agent consults them for UI work, and to evaluate nine named candidate repositories rather than install them all. Selected and vendored unchanged at pinned commits: `apple-hig` (justinwetch/HIGAgentSkills 2206ff9…, MIT; source-reviewed HIG distillation) and `apple-liquid-glass` (DanielJamesTronca/apple-liquid-glass-skill 324b668…, MIT; native UIKit glass only). skin.apptv (Apache-2.0, 695b739…) is a pinned Kodi technique reference, not vendored. Deferred: both SwiftUI skills (no SwiftUI here) and MobileBuildMCP (macOS/Xcode/Node tooling). Rejected: apple-design-skill (redundant, unreviewed synthesis, web focus), swiftui-microinteractions (SwiftUI-only), skin.tvOS-X (2016, CC BY-SA). Canonical policy: docs/design/APPLE-UI-POLICY.md, referenced from new root AGENTS.md and CLAUDE.md; provenance and update procedure: docs/design/apple-ui-resources.md; integrity check: scripts/check_ui_guidance.py. The UI architecture is unchanged (Kodi skin XML plus the native KodiGlassBar); Kodi-drawn translucency is not Liquid Glass. No UI redesign, merge or release is implied. The owner then supplied two desktop Kodi rig renders of the unmerged PR #9 activity pill and sheet (not device; build-151 lacks the pill); they are recorded in the policy (§4) as the reference look, and their defects are in ISSUE-102. The images themselves are not committed because they contain film artwork.

## DEC-027 — Activity design approved: rings, two blues, Close

Owner reviewed the round-4 mockups (2026-11-05: "this looks great. I like ur sheet … Lock it in") and approved:
- progress rings around the app tile in both the pill and the sheet (replacing the sheet's bars and the pill's corner badge);
- blue by role: `0A84FF` for fills, `4FA8FF` for blue text;
- Close (✕) for status-only sheets.

Recorded in docs/design/APPLE-UI-POLICY.md §4.3 and §4.7. The owner declined a test build of PR #10's Notifications fix for now ("not yet pr 10 is different then ui stuff"). Next: implement the approved design on PR #9. No merge or release implied.

## DEC-029 — Build 194: the approved boards are the measured specification (2026-11-08)

Owner, after build 193 on the iPhone: "this looks nothing like the mocs i approved", with a fix prompt naming the
approved boards in `docs/design/library-status-mockups-r1.html` as the specification ("look EXACTLY like the
owner-approved mockups"). Decisions taken in this pass, each citing that approved mockup:
- New generated textures at the boards' radii (`status_ui.textures`, never committed): `r27.png` (10 pt tiles and
  segmented controls), `r21.png` (selected segment), `pill21/16/11.png` (8 pt summary bar, 6 pt card bars, 4 pt step
  bars), `poster27/21/16.png` (rounded posters 64 × 96, 52 × 78 and 40 × 60 pt), `pill_134.png` (50 pt Play/Pause
  capsules, boards 3 and 9). Cards use the existing 16 pt `row_*` textures.
- Board 5 drops the "•••" buttons on the running cards (owner: "remove •••"). Long press on a card still opens
  Pause / Cancel, and the on-screen alternative the policy (§ gestures) requires is the job's row in Library status,
  whose sheet carries Pause and Cancel; the Notifications page links there ("Library status").
- While AirPlay or a video slows a job (still moving), its ring and bars keep the job's colour as boards 2 and 5 show;
  grey stays for paused, stale and the slowed bell (board 6).
- Multi-line text (board 2's sign-in sentence, board 3's sentence, board 7's note) is a Kodi textbox
  (`status_ui.paragraph`); every one-line run stays a label with scroll off and "…".
No build, release or merge implied; device review pending (ISSUE-119).

## DEC-030 — Play on TV becomes one card over the video (owner-approved mockups, 2026-11-08)

Owner, on Kodi's generic "Connecting to the TV…" progress box and "Your TV couldn't reach this iPhone" OK alert:
"can we get a moc up of a better pages for this? these are uglyy". Six boards were made
(https://claude.ai/artifact/6rg8jopnvJRVKRUotRgNZM); the owner approved all ("i approve all mocs").
- One landscape card (`resources/lib/airplay_flow.py`, `1080i/IOSAirPlayFlow.xml`) from Play on TV until the TV plays:
  three steps (open the movie, choose your TV, connect and play), a bar, and Cancel. Problems stay on the same card with
  plain words and buttons that act: Try again, Pause uploads and try again (the owner's own Pause), Open Settings
  (KodiAirPlay r34+), Keep watching here / Cancel. A slow open is never described as a network or permission problem.
- Kodi's own progress box and alert remain only as a fallback when the card cannot load.
- Board 4 (the phone as a remote while the TV plays: pause, ±10 s, Play on iPhone, Stop) needs native pause/seek in
  KodiAirPlay; it is not built yet.
- Surfaces: the solid 16 pt card texture (`row_only.png`, SURFACE2), not the translucent sheet texture (policy §2: text
  cards ≥ ~90 % opaque). Desktop Kodi rig renders checked; device review pending.


## DEC-031 — Keep compatible original video; prepare only when needed (2026-11-10)

Owner: "only converts formats that are needed" and "the airplay is a separate bug, it works for elementum drive
downloads so just apply the same logic". Use actual native video codec/copy safety inspection before background
preparation. Copy-safe H.264/HEVC originals stay on Drive without conversion/re-upload; playback can adapt their
container/audio on demand. Unknown/unsupported video keeps the existing preparation path. Disable optional
automatic repacks of already ready files. Readiness is tied to the inspected Drive version/checksum/size/ID;
transaction recovery and owner-kept choices remain protected. This does not declare MKV universally receiver-native,
remove runtime subtitle/audio handling, or accept the separate Umbrella/Roku bug as fixed on a device.


## DEC-032 — Audit compatibility and faster opening separately on every Refresh (2026-11-10)

Owner: “anytime i press the refresh button i want it to read my entire library and check if faster open has been
done and conversion is good, and if one of then is missing something it will fix it”. This revises DEC-031's
disabling of faster-open background repacks: keep compatible picture quality, but restore a missing fast-open
container/index step. Every explicit Refresh reopens all eligible library files, including cached/prepared ones;
automatic scans can reuse exact identity results. Inspect native tracks plus bounded byte ranges; never infer
compatibility/layout from extension alone. Front-indexed MP4 and valid completed prepared layouts skip rewrites.
Protect owner-kept originals, transaction recovery, current conversion and checkpoints/backoff. A layout audit
requires access to the Drive bytes (internet if those bytes are cloud-only); it does not download a full local copy.
Existing UI fact slots report faster opening independently; no layout or native framework change.

## DEC-033 — Repair AirPlay startup and follow newly aired episodes; hold IPA (2026-11-10)

Owner asks to code the reviewed AirPlay fix/log upgrades and add automatic downloads for anticipated episodes,
preferably checking on app opening, then explicitly says “don't push ipa yet.” This authorizes source changes and
host validation; no IPA/native release, publication, push or main merge in this checkpoint. AirPlay receives a
shared bounded startup deadline and parallel target priming, with safe diagnostic measurements. Codec safety
predicates remain enforced; no unsupported picture is silently declared compatible. Existing native pins remain
unchanged until a later authorized rebuild/verification/pin step, which must precede an IPA containing this repair.

Confirmed TV downloads follow their canonical show identity and selected source preferences. Check fresh actual
air dates on launch/foreground, with a cooldown and work caps, rather than continuously scraping. Use the existing
Elementum → AllDebrid → Google Drive flow, verifying actual ownership/inflight jobs before searching. Failed
sources retry later; cancellation is respected. Existing downloaded shows have an explicit Follow new episodes
only season-menu action; Library settings can turn automatic downloading off. Reuse established Kodi controls
under the Apple UI policy; device/visual/provider acceptance stays pending. ISSUE-147 remains separate.

## DEC-034 — Build and deliver seek/subtitle/stop diagnostics, including downloaded movie resume (2026-11-10)

Owner approves the three recommendations: seek-position retention, retained/cached subtitle loading and automatic
unexpected AirPlay stop evidence, and requests “push the ipa please.” This supersedes DEC-033's IPA hold for this
update and authorizes the required native builds, artifact verification/pins, source push and test IPA publication.
Owner then adds Continue from for downloaded-library movies; include it with retention. Preserve restart choice,
existing Drive setup and source-quality policy. No main merge is requested. Device acceptance remains pending.

Native Kodi r27 candidate: retain dragged/pending target across progress refresh and unrelated pointer events;
queue progress actions outside the touch callback, log target/observed landing and bound stale-target display.
Expanded real slider/gesture/info-refresh harness passes 45 scenarios. Verified r26 executable remains pinned
until the new candidate passes native compilation/artifact provenance checks. UI policy/routed HIG guidance read;
behavior repair only, existing playback controls. AirPlay and downloaded resume repairs follow in this delivery.

## DEC-035 — Full-season quality comes from verified sources; hold the IPA (2026-11-11 UTC)

Owner requests Full season to offer genuine season packs, otherwise select a quality and download episodes one
by one. The quality menu must read actual available sources: never offer 4K if there are no usable 4K results.
Owner explicitly chooses skip and retry the same quality later rather than automatic quality downgrades, asks
for desktop rig testing, and holds IPA publication. This supersedes DEC-034's publication authorization for new
work. No IPA dispatch/publication, main merge or native pin change is authorized by this checkpoint.

Use existing Kodi selection/progress dialogs and status rows, following APPLE-UI-POLICY and routed HIG guidance.
Only aired, dated episodes are considered. Existing copies and accepted transfers are excluded. Source scans do
not select/download media; only an actual saved queue receipt counts as queued. Persist explicit missing episodes
separately from the future-release date floor; retry on opening/foreground with the same strict quality and
ownership checks. Preserve cancellation and existing followed-show behavior. A paused upload queue remains paused
unless the owner explicitly picks the option to resume uploads. Refresh must also read the saved transfer queue,
without waiting for the next service snapshot or doing network work on the page's UI thread.

Later reports add invisible Maze Runner downloads, a blocking subtitle file browser, Media Assistant stalling after
about five seconds, and missing AirPlay captions. Owner corrects the initial subtitle report: Download subtitle
and phone captions work; only Browse freezes. These reports require their own evidence. Do not describe the
unobserved AirPlay/caption causes as fixed or infer Wi-Fi failure from the queue pause.

## DEC-036 — Progress is a bar everywhere; the ring stays only on the Home bell (2026-11-11)

Owner reviewed the Fuse-windows mockups (PR #20, board 06): "I like the bar … the ring is a little hard to look at
… I'd like the bar for everything, it seems more trackable than the ring. Only ring can be around the Bell icon on
the home." This supersedes the "rings" part of DEC-027 (progress rings around the app tile in the pill and the
sheet). The blue-by-role and Close (✕) parts of DEC-027 stand.

- Progress is a thin bar in the activity pill, the activity sheet rows, the opening card, Umbrella's "getting ready to play" page and
  the buffering capsule; with no percentage a short segment slides along it. No spinners for work whose progress can
  be shown.
- The only ring is around the bell icon on Home.
- Recorded in docs/design/APPLE-UI-POLICY.md §4.3 and §4.7 and drawn in docs/design/fuse-windows-mockups.html.
  PR #9's activity code, `portrait.ring()` and the round-4 mockup still draw rings; they change when the activity
  skin is next touched. No build, merge or release implied.

## PR #19 review decision — preserve 4K on Roku (2026-11-12)

Owner selected "Keep 4K via Media Assistant" for a Roku AirPlay receiver that requires H.264. Prefer the confirmed
Roku's Media Assistant route for copy-safe HEVC instead of a new H.264 derivative or a silent picture downgrade.
Verify the actual receiver, 4K support and installed channel. Preserve playback position, cancellation, phone
recovery and source ownership. A strict copy-only native API must fail rather than re-encode. Unknown evidence
keeps the existing route. Source fixes and separate commits are authorized; no native release/IPA is requested.

## PR #19 scope and preloading — 2026-11-12

Owner keeps Movies/TV preloading for instant tab switching; do not implement deferred first-tab loading (1D.3).
Owner now requests remaining items one at a time, starting with 1A.3 only. Commit/push the source repair for
review; no IPA, native release/pin update or main merge is requested.

## DEC-037 — The white loading circle is back for plain waits (2026-11-12)

Owner, build 280 (Kodi iOS Watch Options showed the "Working…" card with Cancel): "I miss my white loading circle
instead of working/cancel". Kodi's busy dialog shows the white spinning circle for any wait, with no card and no
Cancel (Back still leaves). The opening card (boards 04/05) stays only while a video opens, where its stages and
Cancel help. This narrows DEC-036 for the busy dialog; progress elsewhere stays a bar.

## DEC-038 — Merge PR #19 with the mockup PRs; carry the rest into a fresh PR (2026-11-12)

Owner: "merge all pending prs so we can start fresh today", then chose "Merge now, fresh PR". PR #19 (with the mockup
PRs #17, #18 and #20 merged into it) goes to main. Carried into the next PR, from main: phone checks (season queue,
Continue Watching timing, AirPlay captions, Remove); the Kodi r31 and AirPlay r47 native builds and pins (coded, not
built); boards 11 (options sheet) and 13 (slow-start pill) and the buffering capsule; the log-lag review and faster
season scanning. No native release or pin change is part of this merge.

## DEC-039 — Picture: AI Upscale through prepared copies, Saturation only (2026-11-12)

Owner approved the Picture mockups (docs/design/video-picture-mockups.html, round 4): a Picture button in the video
controls with **AI Upscale** (one slider: Off, then only the sizes above the video among 720p, 1080p, 1440p, 2K and
4K UHD; none for a 4K video) and **Saturation** as the only picture slider; per show / movie / all videos; Settings ›
Picture with the default and the shows that have their own. AI Upscale must work on AirPlay: the upscaled copy is
**prepared in the background** like a conversion, only for 720p and 1080p downloads (4K sources are downloaded as
4K), with Apple's VTSuperResolutionScaler (iOS 26+) in the KodiAirPlay converter. Start with a measurement build that
upscales one episode (time, heat, size on Drive). Another agent codes it.

## DEC-040 — AI Upscale engine: Apple's super resolution in KodiAirPlay; no "AI" fallback that is not AI (2026-11-12)

Research for DEC-039, before any code (sources: Apple's VideoToolbox documentation and the iOS 26.0 SDK headers
`VTFrameProcessor_SuperResolutionScaler.h` / `VTFrameProcessor_LowLatencySuperResolutionScaler.h`; Apple's WWDC25
session 300 and its sample code "Enhancing your app with machine learning-based video effects" (MIT-style licence,
read, not copied); MetalFX documentation; Anime4K and its Metal port).

| Option | Quality | Speed / cost | Licence | Fit here |
|---|---|---|---|---|
| **VTSuperResolutionScaler** (VTFrameProcessor, iOS 26+) | ML model; the **video** model uses the previous frame and previous output (temporal, fewer flickers); an **image** model per frame | Apple Neural Engine/GPU; not measured on this phone yet | System framework, no licence to carry | Fits the converter: CVPixelBuffer in/out like the existing VTPixelTransferSession path. Limits on iOS: video model input **at most 1440×1080**, image model at most 1920×1080; integer factors (`supportedScaleFactors`); the model may need a **download** (`configurationModelStatus`, `downloadConfigurationModel`) |
| VTLowLatencySuperResolutionScaler (iOS 26+) | lighter ML model made for video calls (sharper edges, fewer coding artefacts) | made for real time, low power | System | Takes fractional factors (Apple's sample: 1.5, 2, 4) and runtime `maximumDimensions`; a fallback when the main model does not take the size |
| MetalFX spatial scaler (`MTLFXSpatialScaler`) | spatial, not ML; built for rendered game frames | very fast | System | Not designed for compressed video; quality close to a good resize. Not chosen |
| Anime4K (bloc97, MIT) / Anime4KMetal (Apache-2.0) | strong on line art (anime such as Naruto); weak on live action | fast GPU shaders | MIT / Apache-2.0, compatible with the framework's LGPL | Would need a GLSL→Metal port inside our converter and a per-show "anime" choice. Kept as a candidate if the measurement shows Apple's model is too slow or soft on anime; not built now |
| Lanczos resize (libswscale `SWS_LANCZOS`) | classic resize, no new detail | CPU, slow at 4K | LGPL (already linked) | Not AI. A TV's own scaler does as well, so a Lanczos copy would cost 2.5× Drive space for nothing visible |

Decision:
1. The engine is Apple's **VTSuperResolutionScaler** inside KodiAirPlay's preparation converter (r48,
   `remux/src/kr_upscale.m`): decode (VideoToolbox, or software for 10-bit H.264) → super resolution → fit to the exact
   target size on the GPU (VTPixelTransferSession) → HEVC with VideoToolbox; audio and subtitles go through the existing
   preparation path unchanged (copied when they are already AAC / mov_text, which every prepared download is).
2. Automatic order: video model (temporal) when the source fits it (720p, 1440×1080), else the image model (1920×1080
   sources on iOS), else the low-latency model. The measurement build logs which one ran and can force each.
3. `isSupported` and the model status are checked at run time; the model is downloaded by an explicit step (Settings or
   the measurement), never in the middle of a conversion. When no AI engine takes the source, the person sees **"Not
   available on this iPhone"**: there is no silent fallback. The converter has a Lanczos engine, named "Lanczos resize
   (not AI)" everywhere, for host tests and the measurement's comparison only; it is never offered as AI Upscale.
4. HDR sources are not upscaled (the models take SDR pictures; 720p/1080p HDR downloads are rare). 4K sources never.
5. Sizes are boxes (720p 1280×720, 1080p 1920×1080, 1440p 2560×1440, 4K UHD 3840×2160) and the picture is fitted
   inside with square pixels. **No "2K" step**: the round-4 slider had one between 1440p and 4K UHD, but no standard
   size sits there; owner, 2026-11-12: "we can skip 2K".
6. Bit rate: HEVC at about 4 Mbit/s per 1080p of area (16 Mbit/s at 4K UHD): about 2.9 GB for a 24-minute episode.
   The measurement build reports the real size; the rate is a parameter.
7. One AI engine at a time: an upscale conversion uses one lane (each lane holds its own engine and 4K buffers), and
   the upscale step runs in the preparation queue's thread, after ordinary preparation work.

## DEC-041 — Build Season quality sheet round 3 approved; AI Upscale stays on prepared copies for now (2026-11-12)

Owner approved board B3 of docs/design/season-pack-mockups.html ("it looks good"): 4K, 1080p and 720p only (480p
removed); a quick check of three episodes first so a quality nobody has is greyed and cannot be chosen; one row marked
RECOMMENDED and picked: the highest quality that exists unless it is over about 3 GB an episode or 40 GB a season,
then the next one down; season size and size per episode on each row. To be coded next.
Owner asked why an Umbrella stream (Dragon Ball) has no AI Upscale: by DEC-039 the upscaler works on prepared copies of
downloads (which also reach AirPlay); live upscaling of streams on the phone screen is a separate option, to decide
after the measurement log.

## DEC-042 — Owner approved every open mockup (2026-11-12)

Owner: "I approve all mocs". Approved: docs/design/ai-upscale-settings-mockups.html (Settings › AI Upscale: row under
Library, status card, new-download settings, making now, every show and movie with chips, one show with its own size,
movie off, not-available and model-download states), docs/design/season-pack-mockups.html board B3 (DEC-041), and
docs/design/video-picture-mockups.html round 4 (DEC-039). Work continues in a fresh agent session (handoff in
docs/PERFORMANCE-PROGRESS.md).

## DEC-043 — Library file manager mockup approved; buttons cleaned (2026-11-12)

Owner, on docs/design/library-files-mockups.html round 2: "clean up the buttons otherwise i approve! … open pr and
begin implementing the moc roadmap … no need to code yet". Round 3 makes the controls over the show art one set: a
round back button, a round ••• and a Select capsule, same 32 pt height, same dark translucent fill, one line.
Approved scope: boards A (TV Shows list with storage card and state chips), B (one show: episodes, Repair only on a
problem episode, the ••• menu with Find Missing Episodes and Repair All Problems), C (episode/movie sheet: steps,
facts, Play, Delete; Repair as the main action for a problem), D (select and delete with the iOS confirmation; Drive
files to Drive's Trash), E (Movies poster grid), F (Free Up Space). The work is planned in ROADMAP.md "Mockup
roadmap"; coding starts when the owner says so.

## DEC-044 — AI Upscale page, Download problems Clear and Library status lanes mockups approved (2026-11-13)

Owner, on docs/design/ai-upscale-library-mockups.html: "i approve those moc ups!". Approved scope: board A (AI Upscale
page: Making now card first with pause/resume and a plain reason when waiting, Up next with Edit, one row per show,
settings and the iPhone's AI status below, Cancel All Upscaling), board B (the copy's status sheet with stages, Pause
and Cancel Copy behind an alert; Up next › Edit with remove and reorder), board C (Clear on the "Cancelled by you"
heading in Download problems' All view, behind the existing alert), board D (Library status "Working on now · N": the
main card plus a compact row per extra preparation lane). Cancel and Remove never touch the original video; Clear only
empties the list. Owner: no IPA until these are built.

## DEC-045 — Queue page and Favourites mockups approved (2026-11-13)

Owner, on docs/design/queue-favourites-mockups.html: "i approve E and F". Approved scope: board E (Queue: one scrolling
list with posters, "Downloading to Google Drive" then "Preparing for Kodi and AirPlay", running rows with their bar,
waiting rows saying why, Edit with – / ≡ remove and reorder, "Cancel All Downloads to Drive" as a red action at the
bottom) and board F (Favourites: one large title, the empty state, the Library's poster grid with All / Movies / Shows).
The notification details mockup (G–H) is not yet approved.

## DEC-046 — Notification details mockup approved, on condition that text fits (2026-11-13)

Owner, on docs/design/notification-detail-mockups.html: "ensure text fits and its not just ... otherwise i approve and you
can code it all in". Approved scope: boards G (a problem with a fix: plain "What happened", "nothing was lost" when true,
the fixes as one primary capsule and rows, Technical details behind a link with a facts table and short log lines, Copy
Details / Share Log; a Fix button on problem rows in the Notifications list) and H (good news in one line with no log;
a vague problem with plain words, Run Setup Again / Share the log / Restart Kodi; a warning that fixes itself). Condition:
titles and lines wrap to a second line instead of ending in "…" (the list rows and the sheet).

## DEC-047 — Library status without Ready, the show page, its ••• menu and Select approved (2026-11-14)

Owner, on docs/design/library-show-mockups.html: "for board a, we can remove the ready and a2. We have a section for it
elsewhere so it can be removed entirely otherwise i approve and it looks good". Approved scope: board A1 without its Ready
card and tiles (Library status lists only what needs the owner, what is working and what is up next; ready videos are listed
in Library › Movies / TV Shows), no A2; board B (episode stills and titles, one state line, a round outlined Repair, titles
that wrap, the row changing at once after Repair); board C (the ••• menu drawn by the show page, which becomes a dialog,
with Delete asking first); board D (Select with stills, names, checks, a count and a toolbar: Better Version, Prepare Again,
Delete with confirmation). No IPA until the owner has tested build 384 and sent its log; the work is committed without
being pushed until then.
