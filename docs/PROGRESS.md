# Persistent progress

## TV handoff step1 reproduction candidate — 2026-11-20

Step1 complete: native run44664113987 on5ccd958 passed19 observation checks. Prepared and long-GOP MP4 fixtures both reproduce copied target ready / converted target cold, followed by obsolete converted0; desired contract fails exactly four named assertions and no others. Long-GOP fixture confirms different copy/conversion grids. Details and step2 regression gate transition: [TV handoff reproduction](AIRPLAY-TV-HANDOFF-REPRO.md). This is native HTTP/cache/converter evidence, not AVPlayer/TV or full-suite validation. No runtime fix or release.

Added real native HTTP/cache/converter host reproduction for copy→MFi converted handoff at20s in prepared and long-GOP MP4 fixtures, including different copy/conversion segment grids. Read-only test observers are excluded from shipped frameworks. Focused CI must pass observation checks and demonstrate exactly four expected RED desired-contract failures (cold converted target and obsolete segment0, two fixtures). Execution pending. No runtime behavior/release changes; actual iPhone/TV remains untested.

## New phone log is build608/r67 — 2026-11-20

Reviewed four native AirPlay starts; see [build608 findings](AIRPLAY-BUILD608-FINDINGS.md). Exact installed build/source lock is608/main/f50f1a6/r67, not diagnostic602/r68; no r68 packet-window/request-correlation lines.1080p first handoff has no direct TV HTTP requests; retry and4K reach TV but deliver no successful TV video media. Copied video/audio prime precedes late receiver-selected converted rendition, and resumed conversion starts obsolete0 before target184/16. High10 MKV remains in preparation until aborted67.5s. No empty-audio-window reproduction here; later HTTP500/canceled records follow shutdown. Prioritize actual TV rendition/resume-window readiness and duplicate-lane contention, retaining source/receiver uncertainty. No runtime code or release changed.

## While awaiting IPA602 phone logs — 2026-11-20

Result: focused native run44648845367 on cfa3a1c passed84 audio-replay checks. Both indexed/fragmented finite-duration MP4s produced nonempty media fragments identical between reused/fresh readers for0,9,132,171,178,1,178,178,9,0. First full run44647499269 failed24 checks because the fragmented test fixture had zero-duration init metadata (corrected), plus a separate pre-existing retry-evidence assertion: lower transport/cache recovery made both lanes succeed after35s without the app retry. That full-suite failure remains recorded; the focused pass is not a full regression pass. No runtime fix or new release. Next compare IPA602 packet/window/reader traces to these controlled results, then target original media timing and concurrent lane ordering.

Added ISSUE-392 controlled audio-reader replay matrix: indexed/fragmented MP4, the observed long-seek windows plus backwards/repeated windows, reused versus independently opened reader media-fragment comparison over HTTP. Native CI execution pending. No playback implementation, released framework or IPA602 baseline changed. Actual receiver concurrency and original media remain separate gaps.

## r68 diagnostic publication / IPA602 — 2026-11-20

Completion: import workflow44642982544 passed and published IPA602 from2896dfdabdcf543c68f792d2fa0dbf9d2ef33717. Downloaded589,160,451-byte IPA passes ZIP CRC, embedded build/source/r68 identity and exact framework binary hash verification. IPA SHA2564f9843f181b3683ef66fb2a8f195009e5bb46cb098a8d30db9bc49ac83769fa1. Phone test: AirPlay downloaded and streamed titles separately, short seek then>10minute seek, export kodi.log promptly on failure. Diagnostics are shipped; phone root cause and fix remain unproven.

Native candidate9e65561 passed full host, end-to-end and iPhone framework workflow44640470233. Inspection44642746618 verified IOS14.0/SDK26.2, required exports, archive afd7ef59f739d80aad0db793f3601907cf271af03d8179f550a8b36abe05d6c1 and binary4656acbb04c1702798d0ac9b254220613fb8c7b65ec4a4e5d109e1c8b84ea883. Published exact r68 via44642895770; local release download matches archive hash. Owner-authorized IPA602 workflow44642982544 builds source2896dfd with r68 pinned; completion and packaged binary verification pending. This diagnostic release does not establish a fix for the owner's seek failures. PR50 stays draft.

## Diagnostic framework validation — 2026-11-19

Native run44639179231 compiled the iPhone framework but passed3810/3811 host checks. The earlier three request-history retention failures are resolved. The remaining retry-evidence assertion reads only8192 bytes from the expanded bounded log and can miss later retry lines. Its drain buffer now matches the full-history test (1MiB); the assertion remains unchanged. Retest is required before framework publication and the owner-authorized diagnostic IPA. This does not fix or prove the phone's seek failure.

## Build600 phone seek failures / new follow-up — 2026-11-19

Owner authorized PR49 merge; merged as2629184. New phone log confirms build600/r67 and contains two MKV openings then MP4. Likely streamed MKV attempts show31.6–41.6s priming and slow converted video delivery. MP4 long-target video178 succeeds, but audio178 repeatedly returns empty with2scanned packets and no new source I/O; nativeHTTP500 then buffering/failure. Source provenance and the reported>10minute stream-seek command need confirmation; not every server-successful segment proves receiver playback. Start with reproducible MP4 audio-window/reader reuse failure, then MKV source/conversion waits. See [new roadmap](AIRPLAY-BUILD600-ROADMAP.md). No new runtime fix or IPA.

## AirPlay seek retry test IPA600 — 2026-11-19

Owner authorized repair and testing IPA. Resolved PR49 documentation conflict by preserving both histories and renumbering AirPlay to ISSUE-391; merged main8e707e5 into the feature branch, without changing tested native source2fde082. Candidate44612304285 passed native host tests and iPhone compilation; inspection44617321795 verified archive d7bb7cc432771bf4aa54244670e1396369df65e4bf03d75555f17f460d48f552, iPhoneOS platform and45-export parity. Published exact r67 via44617373885 and pinned it. Build600 from684d54b57208cfdff637f6a7ae39da3f0c0a322e passed full import workflow44617491985. Downloaded589,157,845-byte IPA: SHA256abe3a0eab7d028757317d6146acc149408f8ea10aee96c6a7b1d903dc59b016c; ZIP CRC, embedded build identity, selected Python sources and exact r67 binary c874d74a315f42a067bd02e6e50439baf269fb87429780c203d971f088571cbd pass. PR49 remains open/unmerged to main. Phone test: same failing source, AirPlay, seek forward about10minutes then backward, sustain playback and export log. This bounded retry is controlled-host-proven, not universal source/receiver acceptance.

## Owner-authorized diagnostic IPA588 published — 2026-11-18

Build588 from24ba0c4ebfa9b7c4b4b3ba6ea7e740a5df94c674 passed workflow44420277871 and published. Downloaded588,979,457-byte IPA: SHA2567c63b2231ab9bff0b19e9349fbe864e15e4ca22537eea1a5ccd5003f3c7a7794; ZIP CRC and build identity passed; exact AirPlay/source/history Python files matched source; packaged r66 binary SHA2569e6bc5dc4e0b2c6dd1100285cd8f660bae91d7aee92f6429a77568391e3dbc8d matched verified candidate. Framework publication44420093836 initially hit integration release-creation403; owner-authorized repository access created the empty release, then rerun uploaded/verified immutable archive. Device acceptance, empty audio and pause intent remain open. Sports loading review/mockup is isolated in draftPR47 and absent from this IPA. Test when home: open/seek/sustain/pause during recovery/close/reopen Continue Watching and export log. PR46 unmerged.

## Latest-source native artifact verified — 2026-11-18

Step2 (compile/inspect latest source) completed: native run44399079914 passed host tests and iPhone framework compilation for4b72d9c35da51b51bae6127ec1979607dcdffa51. Its AirPlay source tree is unchanged on the current branch. Independent inspection run44403574416 passed ZIP integrity, native callback tests, hashes/platform/required exports and retained its report via check-run API. Archive SHA256bab8cbcf6549eff5c1c57e18327a08aaa696b6c82d1d4445895d560184ed16e8; binary SHA2569e6bc5dc4e0b2c6dd1100285cd8f660bae91d7aee92f6429a77568391e3dbc8d. LC_BUILD_VERSION: IOS, minimum14.0, SDK26.2. All45 public symbol names exactly match the previously inspected candidate (no missing/added exports); explicit preparation/probe/stream serving/HDR/subtitle/background checks passed. No framework publication or pin update; r65 remains pinned. This completes artifact verification, not pause-intent implementation or device acceptance.

## Native host CI dependency-install repair — 2026-11-18

Run44379604495 failed twice at dependency installation: regional Ubuntu mirror downloads were slow and the three-attempt command budget exceeded the12-minute step cap. Candidate4b72d9c uses the standard signed Ubuntu HTTPS archive, excludes recommended packages and bounds two update/install attempts within15minutes. In run44399079914 the dependency-install step passed and the host FFmpeg build started. Native host tests/conversion results remain pending; installation success is not a test pass. No runtime code, framework pin or publication changed.

## AirPlay steps 3–6 host checkpoint — 2026-11-18

All181 registered local import check/test commands passed; platform-specific skips are not native execution. Separately reran22 history cases and2 production source-cache HTTP fixture tests successfully. The range fixture again showed mixed timing (concurrency-limited case improved, repeated fallback-refusal case did not), without real playback claims. No new substantiated cause for ISSUE-375; exact original-source packet/timestamp/selected-audio evidence is required to reproduce the repeated empty segments. Native host retry44379604495 failed again during FFmpeg fixture dependency installation before executing tests, while the iPhone framework job passed. New [test-build readiness document](AIRPLAY-TEST-BUILD-READINESS.md) records evidence, remaining native/pause/source gates, required final-source compile/inspection/publication/pin sequence and concise future phone tests. No framework pin, IPA, release or merge changed.

## Step 2 validation clarification — 2026-11-18

Run44384291944 passed the controlled native callback test from789a3e3. Host run44379604495 failed during FFmpeg fixture dependency installation, before host tests executed; it is not an observed recovery assertion failure. Failed-job retry requested. User-pause intent remains unresolved; transition tracing is preparation for establishing the missing command-origin evidence, not an intent implementation. Step2 remains incomplete. No device result or publication.

## Pause/recovery tracing preparation — 2026-11-18

Added bounded state-change diagnostics (generation/rate/time-control/item status) and recovery-completion ownership/state diagnostics without URLs. Sampling is every0.5s and may miss short transitions; logs cannot alone establish the origin of a pause. Controlled callback harness explicitly retains the known active-session pause ambiguity instead of claiming pause intent is solved. Eight source-wiring cases and shell syntax pass. Previous run44379604495 framework compilation succeeded but host-tests failed; this remains unresolved and must not be presented as full validation. New framework publication/IPA remains unauthorized. Future device acceptance requires usual receiver and pause during recovery; no test required while owner is away.

## Step 2 native callback evidence — 2026-11-18

Run44380509148 passed the new macOS Foundation harness, compiling the actual production seek-completion body and executing five controlled cases: owned success plays once/clears deadline; changed generation, changed item, inactive playback (including timeout/close), and interrupted seek do not play. This is native callback execution against a controlled object, not AVPlayer readiness or receiver simulation. Run44379604495 successfully compiled the compatibility-recovery sourcef4c8e44 for iPhone; its host suite was still running at this checkpoint. Pause intent remains a concrete evidence gap: the current integration observes rate/status but has no independent user-command signal while recovery itself pauses the item. Correctness for AVKit controls/receiver remote pause cannot be established by a fake object's rate. Need actual command/transition tracing on an Apple runtime and eventual receiver test before claiming it is solved. No subclass/swizzle or guessed rate heuristic introduced. No publication/pin/IPA.

## Step 2 compatibility recovery follow-up — 2026-11-18

Found another premature-play path in compatibility conversion replacement. Candidate now pauses before replacement and uses the shared readiness/owned-seek/deadline path before playing, with initial-seek suppression. Eight stall source-wiring checks and shell syntax pass; these do not execute AVPlayer. This source differs from the previously inspected95bb0d2 artifact and needs new native compilation/inspection before publication. User-pause intent and actual receiver behavior remain unproven; step2 is not complete.

## AirPlay step 2 review — 2026-11-18

Reviewed ready/seek/deadline and cancellation/replacement wiring; timeout deactivates playback so late completion is rejected. Seven stall wiring tests and22 local-history tests pass; these are not AVPlayer execution. Concrete remaining gap: user-pause intent is not separately tracked from recovery's programmatic pause, and owned successful completion calls play. A rate check alone cannot resolve that ambiguity. Actual AVPlayer readiness/seek/pause tests require an Apple runtime; Linux fixtures cannot prove external-receiver behavior. No runtime change or publication. Step2 remains incomplete pending meaningful native behavioral tests and pause-intent design.

## AirPlay step 1 candidate inspection complete — 2026-11-18

Import CI44360201249 passed for86b6eb9. Workspace artifact/log downloads remained forbidden; verification-only run44378712092 downloaded the original candidate from run44343640378 on a GitHub macOS runner and saved its verified report as a check-run summary accessible through GitHub API. Original source95bb0d23fd5cb53c3b450e8a839c0b2fab3c611e; framework archive SHA25643ed7f35b5333670852f6beaaa84531982eb266f77a4fec23285c91edbb4569c; binary SHA2565d07a3671bf3eb67652d288368bd6034742b59e0156421af29c78b065c624a7d. ZIP integrity passed. Mach-O build platform IOS, minimum14.0, SDK26.2. Native preparation/probe/streamed preparation/verification/HDR/subtitle/start-at/serving/background exports verified with nm. This establishes artifact identity/platform/exports, not AVPlayer recovery behavior. No framework publication or pin change; r65 remains pinned. Ready for step2 controlled stall-recovery review/testing.

## Sports source selection follow-up — 2026-11-18

Owner approved investigating Crew's shared segment proxy and tracking reliable source outcomes. Build 575 phone log reports 28 proxy-not-running failures across seven streamer names; exact cause and the successful provider remain unknown. Roadmap now prioritizes inspecting the service's bundled manifest, lifecycle and startup, then ranking candidates using confirmed video outcomes without storing private stream data or treating cancellation as failure. No implementation or IPA in this update.

## Sports discovery candidate — 2026-11-18

Step 1 candidate rotates serial Crew discovery by folder and publishes category matches incrementally, avoiding a complete first-league traversal before starting the next. Existing session and playback cancellation checks remain in each traversal. A single slow folder can still delay other categories; phone behavior is unverified. Focused Crew and Jet tests pass. No IPA or merge.

## Build 575 phone result and fresh roadmap — 2026-11-18

Owner reports ESPN cards but no source choices in Sports; manual Crew browsing eventually played a game after several failed sources. Phone log confirms build575, ESPN18live/51upcoming in1.62s, NHL36 matched streams after53.37s, and NBA/NCAAB/FullLiveSites zero visited folders. Live Now visits ended before the first scan completed; Sports closed immediately before skipped-category summaries. Session cancellation/serial category starvation needs reproduction, not a speculative code change. Manual media opened with H.264/AAC later; exact successful provider is not established. All existing code is pushed through30722ac; only an obsolete build568 documentation stash is retained privately. Owner requests roadmap only: [fresh-agent roadmap](SPORTS-PHONE-SOURCE-ROADMAP.md). No implementation, IPA or merge in this follow-up.

## Owner-authorized testing IPA 575 — 2026-11-18

Published build 575 from `63b4434013d947e6e45973b4f17908331329e4a4` after successful full import-review workflow 44220815857. Downloaded the 588,958,897-byte IPA and verified ZIP CRC, embedded build/commit identity, and six exact Sports UI/native routing source files. SHA256: `bb0927b28faabd51753b1b8f493e5a2304ed9900094b873239bfc98d9c463d18`. Release: https://github.com/onlykappa/Kodi-Ios/releases/tag/build-575. PR #43 remains draft and unmerged. Phone acceptance pending: open Library > Sports > Live Now, tap a live game's Crew source, select any native feed, and export kodi.log including `Kodi iOS Sports:` events. Test another source if the first fails and cancel an opening to check it does not restart unexpectedly. Real automatic best-pick/cancellation/fallback coverage remains incomplete; one real Sports-selected broadcast played in the desktop rig.

## Step 3 resumed from 8806189 — 2026-11-18 (real UI playback proven; validation ongoing)

Remote PR head verified before work; stale local build-568 documentation preserved in a stash. Missing documented rig recreated in a separate preserved profile/container using Kodi 21.2/Python3.13. Forced portrait skin canvas 1080×2090 at 603×1167, with portrait/Font.xml confirmed. Rig-only Home isolation and managed CA trust repair; Crew authorization and source code unchanged. The iPhone remains Kodi21.3/Python3.11 with native rotation/bar; those are not reproduced by this Linux renderer.

Root cause established: Crew create_list clears its entire regex table at every league root. A multi-league scan therefore invalidates earlier saved routes; all three saved choices for one game had missing cache keys. Refreshing Crew's ordinary parent menus restored them and native Crew played 1080p H.264/AAC. Candidate fix stores each route's native menu ancestry and ESPN match, refreshes that chain immediately before playback, and uses only the fresh returned route. Native queues now stage one refreshed candidate at a time; preparing all at once would repeat the invalidation. Unknown/cancelled preparation aborts conservatively.

Real acceptance checkpoint: actual Live Now NHL-filter/source control selected the ESPN-live Buffalo–Philadelphia game; its rebuilt Crew feed opened real 1080p H.264/AAC, speed1, with time advancing through 49s. This follows the actual app controls, not a media fixture or injected game. A second actual Sports route, Ottawa–Winnipeg, reached Crew's normal two-feed picker but its selected feed did not begin video in this run; source availability is not claimed. Portrait Sports/Live Now screenshots captured privately. iPhone cancellation, confirmed-error fallback and playback remain unproven. No IPA, merge or iPhone acceptance claim.

## Sports opening cancellation and testing build — 2026-11-17

Kodi reports failed opens and user stops with the same pre-AV Stop callback. Ambiguous stops, timeouts and unclassified empty queues now cancel, avoiding an alternate after a user stop; explicit errors can still advance. The tradeoff is that some true failed opens require manual retry. A slow HTTP fixture in desktop Kodi 21.2 opened no second source after Stop, but took about 21 seconds to unwind. ESPN and Crew timing logs use aggregate counts and no source URLs. The owner authorized one testing IPA; build and phone acceptance pending. Prior test releases are preserved.

## Sports: ESPN live-first Crew discovery — 2026-11-17

Owner requests ESPN for live and upcoming games, with Crew scanned only when ESPN marks games live. Crew discovery now skips entirely with no live games and limits league traversal to live games; normal page entry reuses fresh results, with explicit refresh retained and a 45-second cache. A real ESPN check returned 75 upcoming, zero live and zero Crew calls. The owner reports Crew works; build 568 logs show repeated scans and menu taps, not video playback. Existing stop-before-AV ambiguity, actual live matching, iPhone smoothness and long-scan schedule staleness remain open. No IPA built.


## Crew provider + American ESPN schedule — 2026-11-17 (candidate validated; phone acceptance pending)

Owner chooses The Crew instead of The Loop. ESPN controls event ids, teams, live/upcoming status, scores and clock; Crew supplies uniquely matched native playback routes. Defaults: NFL/NBA/WNBA/MLB/NHL/NCAAF/NCAAB/MLS, including Canadian teams within those leagues. Filters, Formula 1 and boxing are deferred. Broad Crew category browsing was prototyped and removed after clarification; existing Live/Upcoming/Leagues/game pages remain the interface.

Candidate implemented: selected schedule publishes before source scanning, source-free games remain visible, exact Crew routes/query parameters survive serialization, independent native choices remain distinct, Crew-only real provider never discovers Loop/direct Jet/independent sources. Discovery is serial, bounded and yields to requested/active playback. An active listing has a bounded wait before playback. ESPN aliases are used only for unique paired-team matches; wrong league/date and ambiguous matches are rejected.

Validation: 179 workflow commands passed, then all 23 affected Sports suites reran successfully; latest Crew regression suite has 23 passing cases. check_project passes. Desktop rig loaded 75 U.S. games (none live) in 1.25s. Controlled Upcoming card → game → Crew source → actual Crew sports player → Kodi VideoPlayer passed, speed 1 and time 0 → 0.602 → 1.604s. Uses an owned local video, not a broadcast. Real source matching/availability during a live U.S. event and iPhone acceptance remain unproven. No new IPA or merge.

Failure retained: broad scans exit this desktop Kodi in Python 3.14 interpreter cleanup (GDB: PyThreadState_Swap / CPythonInvoker::onExecutionDone); reducing concurrency did not establish a fix. Phone uses Python 3.11, so applicability is unknown. Final UI check isolated unrelated rig background addons/Home; Crew sources were unchanged. Initial private fixture omitted content=addons and selected movie scraping; corrected fixture passed. Evidence: reports/sports-crew-validation.json; ISSUE-367; DEC-062.

## Owner-authorized native Loop test IPA — 2026-11-17

Preparing one new test build from claude/sports-jet so the owner can open The Loop directly and export a phone log. Startup applies the same recognized-source proxy repair without opening menus; legacy discovery is off and normal Sports catalog remains on demand. Controlled HTTP-error fallback is verified; actual automatic-picker dialog waiting remains unresolved. No merge. Build source and release will be recorded after checks.

## Sports automatic routing candidate — 2026-11-17

Play best available, native failure skipping, AV-start cleanup, request ownership and playlist timer default are implemented. All 178 workflow commands passed plus final affected retests. Controlled native routing skipped a failed route and played video; actual seven-source Loop queue from a game card currently stalls. This is an unresolved candidate, not a live-provider/device fix. Continuing diagnosis; no IPA. [Current checkpoint](SPORTS-HANDOFF.md).

## Sports native Loop cards checkpoint — 2026-11-17

Native Loop catalog discovery now feeds schedule-matched cards; real rig found 43 eligible provider routes and 61 upcoming games. Exact routes dispatch via normal Loop without direct bootstrap Jet import. Failed initial Upcoming loads retry automatically, and distinct native source choices remain selectable when quality is unknown. All 177 workflow commands, affected final reruns and project/UI checks pass. A tapped provider returned HTTP 403; this checkpoint does not claim every provider plays. See [sports progress](SPORTS-PLAYBACK-PROGRESS.md). No IPA generated; continuing rig investigation.

## Sports playback and opening rig follow-up — 2026-11-16

Build 563: an incomplete source scan repeatedly delayed Leagues/Upcoming; an already available snapshot is now reused and identical merges cached briefly. The playback adapter tries remaining nested candidates and the scraper’s own resolver after resolution failure, and hands Kodi the resolved address, including resolver and extractor headers. All 14 sports suites (189 tests) pass. Desktop Kodi 21.3 displayed both pages with a 300-game synthetic partial snapshot and played a local video after a mocked first resolver failed; four provider calls took 0.281 s versus 0.939 s for four uncached merges. This is synthetic rig evidence; real providers and iPhone behavior need testing. Details and retained failures: [sports progress](SPORTS-PLAYBACK-PROGRESS.md) and [validation](../reports/sports-563-rig-validation.json).

## Build 561 published and verified — 2026-11-16

PR #44 merged as 9b276e7. Testing [build 561](https://github.com/onlykappa/Kodi-Ios/releases/tag/build-561), source a16a3ef, includes the sports playback/resolver/refresh repairs and the merged Drive/AirPlay fixes in newly compiled **AirPlay r65**. PR #43 remains open for testing. Final import CI run 43913240719 passed all tests, bundle apply/restore smoke checks and IPA validation. Downloaded the 588,860,520-byte IPA: release SHA **d60999a057fbb21ca6397fda1b2bf17aca3daa9945c282fe99eb0be928a815cb**, full ZIP CRC, eight exact repaired source files, exact r65 binary and exact unsigned r33 executable all pass. Glass bar r6 preserved.

The raw r33 executable has an embedded signature; the first private verifier incorrectly compared the unsigned IPA against that signed digest. After verifying the original pinned r33 archive/binary and applying the existing packer's unsign operation, the packaged executable matches byte for byte (one signature command removed). This was a verifier assumption, not an app change. No extra IPA was built. Optional first-frame renderer logging from #44 remains deferred with the r33 executable; the functional Drive and AirPlay fixes ship. Phone acceptance remains pending: Sports play/scroll, completed Drive movie/show cold and warm opens, AirPlay picture/audio/captions and forward/back seek.

Evidence: [sports validation](../reports/sports-playback-validation.json). Native compile 43911296606 / host evidence 43907784636; immutable r65 publisher 43912960249. Local/CI validation includes 170 Python suites (2,483 tests with targeted final retests), five real Foundation tests, native conversion/seek/cancel/caption checks, six matching converted A/V segments, 768 frames and exact copied picture packets. Desktop portrait scrolling/live-provider behavior was not established; no phone performance or universal provider availability claim.

## Sports playback repair and combined build — 2026-11-16

Owner build 557 log confirms an asynchronous Jet play request returned True and Live Now passed it to Player.play; ResolveURL was installed but absent from the script import path; failed extractor resolution could pass a webpage to Kodi. Load ResolveURL's declared dependency graph, accept only actual playback strings at the page boundary, and reject unresolved links. Forced refresh now joins an active collection, with a process-wide file lock preventing simultaneous interpreter scans. Keep existing results during refresh and avoid rewriting unchanged page properties. Provider outages in the log remain upstream failures; these changes cannot guarantee their availability or phone frame rate.

All 14 sports suites pass (179 tests). Seven focused regression cases cover dependency loading, the asynchronous acknowledgement, refresh joining and failed/successful link resolution. Existing mock window failures exposed the need to cache previous properties within each page; corrected and all suites rerun. Owner also approved review/merge of PR #44 and one combined testing IPA. PR #44 merged as 9b276e7 after its 265 Python tests and project check passed. Next: integrate newer sports/subtitle source with main, run native candidate CI, verify/pin its framework, then package and verify the IPA. Actual iPhone playback/scrolling/AirPlay checks remain pending.

## Build 544 log (owner, 2026-11-16): sports discovery skipped, AirPlay slow starts, banner bar — 2026-11-16

Sports showed "Can't load" as expected (no adapter yet) and the discovery walk did not run: build 538's empty result blocked it for 12 hours (ISSUE-352, fixed:
retry after 10 minutes). AirPlay played everything. Starts took 5.5 s (Naruto, on the phone), 10.5 s (Phony 1080p), 25.5 s and 28.5 s (4K HEVC from Drive):
the cost is the keyframe scan of a prepared file with no saved scan (12-14 s, saved after the first cast) plus cold Drive reads of the first segments (7-9 s).
The banner's bar now moves the whole time (ISSUE-353). Not done: scanning the existing prepared library in the background (needs a native AirPlay change
and a new framework tag) and faster first-segment reads from Drive (native). Phone results pending.

## Sports: ChatGPT's Upcoming, game page and Leagues merged with the stack; league page added — 2026-11-16

Branch `claude/sports-full` = the sports stack + The Loop/Crew bundling (DEC-058) + ChatGPT's pages (`codex/sports-upcoming-leagues`). Conflicts were only
list unions (PAGES, portrait loads/files, workflow, docs). Review: the pages follow the contract and the sample provider; all sports suites pass;
Upcoming and Leagues were rendered in the desktop Kodi rig (sample data) and match boards 10 and 16. A league's page (`sports_league.py`) opens Live Now
on the league's chip when it has a live game, else Upcoming on it (both pages already filter). Phone results pending.

## Sports: Loop family and The Crew bundled; PR #32 merged; build 538 checked — 2026-11-15

Build 538 (commit 4961d11, pre-release) showed on the phone that The Loop add-ons were not installed (`Unable to find plugin`, ISSUE-350 notes the
10-minute build limit that also hit it; now 25 minutes). PR #32 (movie/TV backup providers) was merged by the owner's instruction after review. It
contained a syntax error in `service.py` (ISSUE-351, PR #42 fixes it, not merged). DEC-058: The Loop family and The Crew are the sports providers; the
Loop packages are pinned in the provider source lock (fetched as Kodi, owner allowed). Host checks only. The Loop's tree could not be read in the
desktop rig because the sandbox network does not reach its servers; `KODI_RIG_NETWORK=1 kodi_rig.py start` keeps the proxy for such checks. Phone
results pending: next IPA build (owner's OK needed) will log The Loop's and The Crew's menus for the adapter.

## Sports: merging and The Loop discovery — 2026-11-15

`sports_merge.py` combines several add-ons' answers into the contract's games (DEC-055: one game, one line per distinct stream with "Also on …",
Best / Also good). `sports_loop.py` is The Loop's provider, step 1: it has no adapter yet (its code is not in this project and its listings are not
guessed), so every page shows its can't-load state, and it lists the Loop add-ons' menu folders once every 12 hours (folders only, bounded) into
`sports-discovery.json` and `kodi.log` for the adapter to be written from. Status and next step: [design/sports-loop-integration.md](design/sports-loop-integration.md).

## Sports page 2 coded: Live Now — 2026-11-15

`Library › Sports › Live Now` opens `IOSSportsLive.xml` (`sports_live_page.py`, filled by `sports_live.py`), approved boards 6-9 (option B): league chips,
then one card per live game (closest to its end first) with the league label, the clock, both teams and scores, and the game's sources under it
(best first, "Also on …", Best / Also good), a tap on a source plays it at once; nothing-live and can't-load pages. Checked in the **desktop Kodi rig**
against the boards (the list, the NBA chip, a tap on a source, nothing live, can't load); not yet on the iPhone. Capacity: 12 cards and 4 sources
a card (the rest is behind the chips and a "N more games not shown" line); chips wrap to up to three rows. `sports_provider.play` hands a real source's
`play` path to Kodi's player; the sample provider only logs.

## Sports page 1 coded: Library › Sports and the landing page — 2026-11-15

`Library › Sports` (between TV Shows and Favourites) opens `IOSSports.xml` (`sports_page.py`, filled by `sports.py`): back, refresh, "Sports" with
"Updated just now", the Live Now / Upcoming / Leagues tiles and the Finished today row, plus the updating, nothing-live and can't-load states, as
approved board 2 of [sports-approved-pages.html](design/sports-approved-pages.html). Checked in the **desktop Kodi rig** against the board (live,
nothing live, can't load, the Library row, a tile tap and refresh); not yet on the iPhone. The tiles open Live Now, Upcoming and Leagues only once
those pages exist (an unknown RunScript name would run the recovery script, so the tile says it is coming). Sample data is opt-in
(`KODI_IOS_SPORTS=sample` in the rig); with no setting the page says it can't load until The Loop's provider lands.

## Sports › Leagues: boards 16–17 and 20 — 2026-11-15

Implemented the Leagues list, scrolled view and unavailable-provider state. `order_leagues` and `league_detail`
supply ordering and wording; live fragments are red, empty leagues say Nothing coming up, and long names wrap.
The sample therefore places live UCL before EPL, following the contract rather than the static mockup order.
See Leagues now opens this page with the same provider/clock. League rows log their destination and call the
separately owned league route only when its file and route registration both exist. Boards 18–19 remain separate.

Evidence: approved HTML rendered in Chromium and compared with desktop Kodi 21.3 at 603 × 1167. Checked top and
scrolled list, complete UEFA name and an extended long-name fixture, the error layout, repeated failure and retry
recovery and Upcoming → See Leagues → Back navigation. The final Motorsport row clears the fixed fallback tab bar. Screenshots remain outside Git. No iPhone,
native-bar, real-provider or playback result is claimed. Reused existing fonts, badge textures and state art.
Twelve new cases in `scripts/test_sports_leagues.py` are listed in import-review; the Upcoming state test now
checks its live Leagues callback. All 139 listed scripts pass against the combined PR/base tree; project and UI guidance checks pass before commit.

## Sports › Upcoming: empty and error states, boards 14–15 — 2026-11-15

Built the approved calendar empty state with Updated just now, No games coming up, Nothing is scheduled yet and
See Leagues; the warning state has Not updated, Can’t load games right now, the approved two-line explanation and
Try again. Empty results hide all chips and stale rows. Errors survive timer redraws and retries; a successful
refresh restores the list, and cached data remains visible when a refresh fails (ISSUE-335). See Leagues currently
logs the pending route; the Leagues page and its navigation are the next separate piece of work.

The 20 pt state headline uses the existing Inter Bold asset at 54 units: the adjacent existing sizes are 17 and
22 pt. Runtime-generated outline calendar/warning masks reproduce the approved symbols; Fuse's available versions
are filled. Body and buttons reuse the existing fonts, surfaces and primary-pill helper. No artwork is committed.
The rig pass corrected translucent circle scaling and explicit description-line spacing (ISSUE-336).

Evidence: Chromium mockups compared with desktop Kodi 21.3 at 603 × 1167. Checked both layouts; the error screen
using the updated base's normal, unavailable provider door (no implicit sample data); a 31-second timer advance;
repeated failed retry; successful retry with an explicitly injected test provider; empty → refresh → six games;
Back; visible button focus; and the pending See Leagues log. Screenshots stay outside Git. The rig uses the fallback
tab bar; iPhone, native-bar and real-provider/playback results remain unverified.

Validation: thirteen cases in `scripts/test_sports_upcoming_states.py`, listed in import-review, plus the existing
Upcoming/game suites. All 138 listed scripts pass against the current combined PR/base tree; the affected suites
also pass after the final visual adjustments. Project and UI guidance checks pass in both checkouts.

## Sports: updated provider snapshot contract — 2026-11-15

The base branch advanced after the local checks: sample data is now opt-in, and Sample hands out independent
copies. GitHub caught one test fixture that had assumed mutable provider records (ISSUE-334). The fixture now
supplies the next snapshot explicitly. All 137 listed scripts pass against the PR's combined tree with the
updated base, and the feature checkout's game-page tests pass. The UI continues to use the same public provider
door. GitHub's review check passed after the fixture correction. No sample fallback is added to the application.

## Sports › A game's page: boards 12–13 implemented — 2026-11-15

Upcoming rows now open `IOSSportsGame.xml` with the same game, provider and clock. The card shows the league code,
start status, time/day and both teams. Crests use the provider's runtime image, with code-in-circle fallbacks for
the sample's empty crests. Sources are ranked Best, Also good, then the remaining provider order; tapping any part
of a source row calls `sports_provider.play` with the original source and opaque play value. Board 13 keeps the
same card and shows the approved no-sources message. Fetching and refresh run behind the cached card; errors go
to the log with plain recovery wording on screen when no game is available. Back keeps the Upcoming league filter
and focus (ISSUE-331); long source descriptions grow their rows (ISSUE-332), and two-digit start hours fit in full
between the crests (ISSUE-333).

Evidence: compared the approved HTML in Chromium with both actual windows in desktop Kodi 21.3 at 603 × 1167,
using sample data and a fixed sample clock. Checked board 12, board 13, refresh, both sample source taps through
the play door, Upcoming → NBA game → Back, and long team/source wrapping. Borussia Mönchengladbach, Brighton &
Hove Albion, Golden State Warriors and the long source fixture display completely. The game's board uses UCL,
not the full league name; UEFA Champions League belongs to the later Leagues page. No new artwork is committed.
The rig isolates Sports windows from background add-on services and uses the Kodi fallback tab bar. Screenshots
remain outside Git; this is not iPhone, native-bar, live-provider, real-crest or actual-stream playback evidence.
The sample play door only logs, as specified in the brief. Boards 14–15 and the Leagues pages remain pending.

Validation: thirteen new cases in `scripts/test_sports_game.py` (listed in import-review), two new shared-rule cases
in `test_sports_model.py`, and a returning-window check in `test_sports_upcoming.py`. All 137 listed scripts and the
project/UI guidance checks pass before commit. The preceding board-11 commit also passed all 136 scripts then listed.

## Sports › Upcoming: board 11 scrolled view — 2026-11-15

Verified the remaining day groups in desktop Kodi 21.3 against approved board 11. The list now leaves enough room
below the final day to reach the board's scrolled position (ISSUE-330). Tomorrow's two games and the last day's
Manchester City / Brighton & Hove Albion row remain complete and clear of the fixed fallback tab bar. The header
and the owner's six wrapped league chips scroll with the list. Checked wheel scrolling and the list's Last Page
action using the same fixed sample clock as board 10. Screenshots remain outside Git; iPhone scrolling is pending.
The shared Upcoming fixture and XML checks in `test_sports_upcoming.py` still cover all six games and three days.
The game's page follows in its own commit.

## Sports › Upcoming: board 10 implemented — 2026-11-15

`RunScript(service.kodi.ios.bootstrap,sports_upcoming)` opens the Upcoming list with the shared Sports provider and
model helpers: day groups, start times, countdowns, sources, league filters and background refresh. The owner's
clarification keeps `league_codes` order (All, EPL, LIGA, NBA, NFL, NHL for the sample), wrapping onto a second row.
Rows grow for long team names. Game taps currently log the stable game ID; the game's page is the next separate
commit after the owner's board-10 review. See Leagues is also a temporary logged action until that page is built.

Evidence: compared the approved HTML in Chromium with the actual window in a desktop Kodi 21.3 rig at 603 × 1167,
using the provider's sample data and a fixed sample clock. Checked the six wrapped chips, NBA filtering, refresh,
game-row tap logging, Back, and full wrapping of Borussia Mönchengladbach, Brighton & Hove Albion and Golden State
Warriors. Upcoming displays the contract's short league code (UCL), rather than the full UEFA Champions League
name. The header, cards, spacing and text follow board 10; the extra chip row is the owner's approved difference.
Screenshots remain outside Git. The rig uses Kodi's fallback tab bar and has no iPhone safe-area/status-bar proof.
No iPhone result is claimed. Board 11's scrolled view and boards 14–15's empty/error layouts remain for review;
their initial state projections are covered by tests, not a visual approval. No real sports add-on was called.

Validation: `scripts/test_sports_upcoming.py` covers seven projection, XML and asynchronous-controller cases and is
listed in import-review. Project and UI guidance checks pass; all 136 listed scripts pass after correcting the
stop-aware timer regression recorded in ISSUE-329 and rerunning its affected checks.

## Sports: every page approved; the work is split (DEC-057) — 2026-11-15

The owner approved Leagues option A, live-first order and the empty league page: all pages of the section are approved
([docs/design/sports-approved-pages.html](design/sports-approved-pages.html)). Claude wrote the data contract (`sports_model.py`,
`sports_provider.py`, `scripts/test_sports_model.py`) and codes The Loop provider, the landing, Live Now and a league's page; ChatGPT codes
Upcoming, a game's page and Leagues from [design/sports-chatgpt-brief.md](design/sports-chatgpt-brief.md), and Claude reviews and fixes
them. Each page is checked in the desktop Kodi rig, then on the iPhone.

## Sports › Upcoming: option A approved — 2026-11-15

The owner chose option A (a compact list by day, soonest first) and that a tap opens the game's page (DEC-056). The approved boards are
in [docs/design/sports-approved-pages.html](design/sports-approved-pages.html); the options are in
[sports-upcoming-mockups.html](design/sports-upcoming-mockups.html). Mockups only; no app code.

## Sports › Live Now: option B approved — 2026-11-15

The owner chose option B ("I like B"): one card per live game with its sources under it, the game closest to its end first,
a tap on a source plays it at once; all four add-ons feed it and duplicate streams are merged (DEC-055). The approved boards are
in [docs/design/sports-approved-pages.html](design/sports-approved-pages.html); the options are in
[sports-live-now-mockups.html](design/sports-live-now-mockups.html). Mockups only; no app code. Next: Upcoming, then Leagues.

## Sports: landing page approved (option A) — 2026-11-15

The owner approved option A (tiles) and its can't-load state after viewing the mockups on the iPhone ("these are money").
Recorded as DEC-054 and in [docs/design/sports-approved-pages.html](design/sports-approved-pages.html), which gains one
page per round (next: Live Now, Upcoming, Leagues, a league, a game). Still mockups only; no app code. PR #33 holds the
round-1 options.
Owner: all sports add-ons will feed Sports eventually; ChatGPT codes the foundation. What the landing page needs from it:
[design/sports-landing-data.md](design/sports-landing-data.md).

## Sports: landing page mockups, round 1 — 2026-11-15

Mockups only, nothing built: [docs/design/sports-landing-mockups.html](design/sports-landing-mockups.html) (evidence class:
mockup). Library gets a **Sports** row between TV Shows and Favourites; it opens a landing page with three tags (Live Now,
Upcoming, Leagues). Three options for the landing page (A tiles, B grouped rows, C previews), the states of A (nothing
live, updating, can't load) and a map of every page the section needs. The owner's pick and four questions (finished-today
row, which add-ons feed it, tag order) come before the tag pages are designed. Separate PR from #31.

## Build 528: AirPlay r62 + Play on TV banner, speech subtitle check, Roku banner — 2026-11-15

[Testing IPA 528](https://github.com/onlykappa/Kodi-Ios/releases/download/build-528/Kodi-iOS-Customized-Touch-r10.ipa)
(commit 4b98b12, PR #31 unmerged; IPA sha256 07f2c97d…0a5b). AirPlay r62 (ISSUE-343 TV subtitles in sync and single,
ISSUE-346 keyframe scan saved while preparing, ISSUE-347 on-device speech check; host tests green; the framework in
the IPA is byte-identical to the pinned r62), ISSUE-341, 342, 344, 345, 348, 349. All workflow Python suites passed;
banner, problem sheet and Roku banner checked in the desktop Kodi rig. Phone results pending.

## Build 513: AirPlay r61 + subtitle, Umbrella, Favourites and show-page fixes — 2026-11-15

[Testing IPA 513](https://github.com/onlykappa/Kodi-Ios/releases/download/build-513/Kodi-iOS-Customized-Touch-r10.ipa)
(commit e9634c2, PR #31 unmerged; IPA sha256 7993d7b0…5f01). AirPlay r61 (ISSUE-335, 336, 337; host tests green),
ISSUE-333, 334, 338, 339, 340. 136 Python suites passed; season row and Favourites picker checked in the desktop
Kodi rig. Phone results pending. Next steps and rules: [HANDOFF-PR31.md](HANDOFF-PR31.md).

## Subtitles drawer + hold menu coded, not pushed — 2026-11-16

Branch `claude/subtitles-drawer` (local only, owner asked not to push yet). `pages.track_menu` draws the subtitles drawer (own list 9312, Timing 9405/9406,
hold menu 9601/9602, removal question 9611/9612); `tracks.py` runs Find another (searches the held track's language) and Remove; `track_menu.py` has the
rows and wording. Tests: `test_subtitle_hold.py` (15, real controller on a fake Kodi), `test_track_menu.py`. Rendered in the desktop Kodi rig at 2340x1080
(tracks, hold, remove question, More, results): evidence class desktop Kodi rig, not device. The rig has no player, so the flows were not run against real
playback. Release names in results are shortened to fit two lines (DEC-050).
## Drive startup and audio-only AirPlay — source fixes, device retest pending (2026-11-16)

Build 554/r64 identified from the supplied log; latest published IPA at inspection was 557.
Completed Drive playback queued its first decoded picture 4.168 s after Play; the old 3.2-s
log measured streams ready. Removed optional index cache admission from the player response.
AirPlay delivered audio, but no completed converted video; long storage windows also drove
conversion, and unrelated copied-read I/O produced the Drive diagnosis. Converted picture/audio
now share a separate six-second grid, preserving copied video and selected captions.
265 Python tests, 375 native host checks, new native sparse-window regression and desktop
Kodi 21.2 fixture flows pass; iPhone/TV and Kodi 21.3 portrait acceptance remain pending.
Native pins unchanged; no IPA/release/merge. See [progress](DRIVE-STARTUP-AIRPLAY-PROGRESS.md)
and `reports/drive-startup-airplay-validation.json`. PR #42's startup syntax prerequisite is
included separately; unrelated sports/subtitle branches remain untouched.


## PR #32 — movie/TV fallback providers — ready for draft review

Existing provider stays first; Jacktook, POV/Magneto, mapped Otaku, The Crew and Prism supply backups through the existing picker. 431 Python3.11 tests and17/17 realKodi desktop fixture scenarios pass. See [implementation](PROVIDER-FALLBACK.md), [progress](PROVIDER-FALLBACK-PROGRESS.md) and reports/provider-fallback-validation.json. Live accounts/iPhone/AirPlay remain unverified; noIPA or merge.

## Build 502: one IPA with everything from the build-486 feedback — 2026-11-15

[Testing IPA 502](https://github.com/onlykappa/Kodi-Ios/releases/download/build-502/Kodi-iOS-Customized-Touch-r10.ipa)
(commit e9d93ac, PR #28 unmerged; IPA sha256 6df332e1…8498). Kodi r33 (ISSUE-316 smooth long pages; executable
091eb4a4…1435 checked at build) and AirPlay r58 (ISSUE-326; framework zip 1bff47f3…fc331, segment and empty-cue code
present in the IPA's binary). Also: Favourites manager (ISSUE-325), Continue Watching per show (ISSUE-330), Next
Episode (ISSUE-331), shorter Settings › Library (ISSUE-329), quiet Drive proxy hang-ups (ISSUE-327), Continue Watching
entry fix (ISSUE-328). Publishing needed a workaround (ISSUE-332). 134 Python suites and the AirPlay host tests passed;
the Library page was checked in the desktop Kodi rig. Phone results pending.

## Umbrella build 473 never-opening repair — 2026-11-14

ISSUE-303 fix published as `2f447c7` in PR #28. [Testing IPA 475](https://github.com/onlykappa/Kodi-Ios/releases/download/build-475/Kodi-iOS-Customized-Touch-r10.ipa) is ready: 125 focused host tests plus the full Python 3.11 CI suite pass. Download digest, ZIP integrity, packaged source and framework pins verified. Cache admission requires complete opening probes within a shared five-second budget; failed probes cancel and preserve direct playback. Phone retest pending; PR remains unmerged. Full evidence: [UMBRELLA-473-PROGRESS.md](UMBRELLA-473-PROGRESS.md).

## Favourites import + anticipated-episodes bell — coded, host-tested — 2026-11-14

Owner approved the mockups (DEC-053) and asked for the code. Draft PR #29. Library gets a Favourites row; Favourites has Import a List
(paste or text file; names only, "(3)" = watch count, "//" splits; TMDb matching with duplicates / questions / not-found report), sort
by list/year/name/list name/date added, rank and 3× badges, Continue Watching for a stopped movie. The show page has a bare bell (top
right, only with an upcoming episode) opening Alert me / Add to downloads switches per show; the season Download sheet is two rows;
alerts work with automatic downloads off. 53 new host tests pass (import, flow, bell); test_episode_watch updated for the removed
"Follow new episodes" row; existing portrait/pages/settings/choice-sheet suites pass. test_build193_pages has one error that also fails
on the base commit (Monitor.abortRequested in a landscape AirPlay test), unrelated. **Not seen in Kodi or on the phone:** see
[docs/FAVOURITES-IMPORT-BELL-RIG.md](FAVOURITES-IMPORT-BELL-RIG.md) for the rig checklist and known differences from the mockups. No IPA,
release or merge.

## PR #19 — 1A.3 fragment-index cache — 2026-11-12

Owner narrowed the remaining work to one item at a time, starting with 1A.3. The Drive proxy now saves only
validated mfra bytes in the private profile, bounded to 2 MiB per index / 8 MiB total / 64 entries. HEAD/front
opens check live Drive ID, checksum, size, version and modification time; changed identity invalidates old data.
The existing player tail read populates the cache; subsequent index ranges use local bytes, also after restart.
Metadata failure, corrupt cache or full/read-only storage leaves normal streaming available. Diagnostics log
safe byte counts without file IDs or credentials. 55 focused tests pass (22 new); project check passes.
Source repair only: phone timings pending; no IPA, native release/pin or merge. Movies/TV preloading retained
per owner choice. Other open speed/reliability items remain in PERFORMANCE-COVERAGE.md.

## PR #19 review fixes committed separately — 2026-11-12

Owner requested source fixes and individual commits, then chose Media Assistant to preserve 4K when a Roku
AirPlay receiver needs H.264. Work is on claude/performance-roadmap (PR #19), with [skip ci] source pushes.
- 8baacad: ISSUE-171 real rejected-token renewal, concurrent reuse and existing backoff preserved.
- f048abb: ISSUE-172 bounded Drive HEAD probes; ignored Range cannot load the movie into memory.
- dd5c996: ISSUE-173 bounded season source discovery and active HTTP cancellation; strict-quality retries retained.
- ISSUE-174: matched-Roku Media Assistant fallback with native copy-only serving, no silent picture downgrade,
  resume-position handoff, cancellation and phone recovery. Compiled host recommendations: 41 checks, 0 failures.
  Focused Python suites total 297 passing cases. Project/UI guidance/shell checks pass.
Current native pins remain Kodi r30 / AirPlay r46. The fourth repair is capability gated until a new framework
with kodi_airplay_serve_copy is built, verified and pinned. Kodi r31's existing staged improvements also await
verified binary delivery. No native/IPA workflow, release or main merge performed. Device/TV and visual acceptance,
AirPlay captions and continuous-hour playback remain unproven. See ISSUE-171–174 and PERFORMANCE-PROGRESS.md.

## Verified test IPA 229 delivered — 2026-11-11

[Download IPA 229](https://github.com/onlykappa/Kodi-Ios/releases/download/build-229/Kodi-iOS-Customized-Touch-r10.ipa).
Source c26971ec2d3f3b0562dd862d29ec025ee6d53127; run 43035125470. IPA sha256
ad62361857711bdafcbd47e8c726a1d708f420838455ff0ee70912b4a01bbf9a matches the release digest; ZIP integrity passes;
build.json 229 / c26971e. AirPlay r46 (candidate run 42965789430, host suite green; framework in the IPA equals the
release), Kodi r30 (equals the release after signature removal), glassbar r6. Adds ISSUE-165: MKV audio seeks by the
video index, Wi-Fi checked for 5 s, season menus restyled (board 3, rig-checked). 105 local suites pass.
Builds 227/228 were pull-request runs (cancelled / failed test fake) and are not deliveries. Device results pending.

## Verified test IPA 226 delivered — 2026-11-11

[Download IPA 226](https://github.com/onlykappa/Kodi-Ios/releases/download/build-226/Kodi-iOS-Customized-Touch-r10.ipa).
Source 78041117ce833deb5874c7b20c2c403d3fd3b526; run 42957128306. IPA sha256
9f04487dd19e86e69734d7e45c5d9b6e23ae3b47f4de45e44d48d34e0b481943 matches the release digest; ZIP integrity passes;
build.json 226 / 7804111. Kodi r30 (run 42953009766; IPA executable equals the r30 release after signature removal),
AirPlay r45 (run 42955579547; framework binary in the IPA equals the release; exports health and startup_budget),
glassbar r6. Contains ISSUE-160 settings redesign, 161 AirPlay exports, 162 native keyboard, 163 AirPlay start speed,
164 upload lanes/pieces. Build 225 was a pull-request run on the old pins and is not the delivery.
Device results pending; nothing here is proven on the phone.

## Verified test IPA 224 delivered — 2026-11-11

[Download IPA 224](https://github.com/onlykappa/Kodi-Ios/releases/download/build-224/Kodi-iOS-Customized-Touch-r10.ipa).
Source f410a83b91ad587459bdc72eadee687f1dec9cec; run 42944518367. IPA sha256
df2f152c457e8ea528e6cc80cfc8d507dba5fc2c89cd4288b3ca49f9723c54bc matches the release digest; build.json 224 / f410a83;
Kodi r29 (executable sha256 070b0baf…, re-checked after download), AirPlay r44, glassbar r6.
Fixes ISSUE-158 (uploads left paused after AirPlay's Pause and retry: lifted after AirPlay, old pauses lifted once,
"Downloads are paused" card with Resume) and ISSUE-159 (Kodi r29 Browse for subtitle guard). Includes d058ca2 (season
packs, quality coverage, visible paused queue), the Subtitles / Audio menus with Download and apply (Podnapisi; not
yet tried against the real site) and the settings label / footer fixes. The Settings redesign is not in it.
Device acceptance pending; no owner account or media accessed.

## Source handoff to PR #16; IPA held — 2026-11-11 UTC

Owner requests committing completed work now and leaving unfinished work out for another agent. Branch:
`claude/trusting-euler-kgug98`. Included: source-derived full-season quality selection, exact-quality pending opening
retries, real queue receipts, visible paused/pre-transfer jobs, local queue rereads on Refresh, explicit resume/keep
queued choices, stable job identity, Queue paging controls and deduplication, and the native subtitle Browse HTTP
start-path guard. Existing UI helpers/tokens reused; UI policy/HIG followed. No IPA/workflow dispatch or main merge.

Real desktop Kodi 21.3 checks: unavailable 4K hidden; 1080p queues two of three episodes; selecting 4K from mixed
sources queues only its available episode and retains the others in 4K. Five paused jobs appear despite an idle
published model. Browse freeze reproduced with a 25-second HTTP folder; compiled guard opens the browser without
requesting that parent. Full native patch applies to pinned upstream. Related Python/controller/XML checks and 46
actual C++ seek scenarios pass; receipt: reports/season-source-queue-checks.json. Native iOS pins remain r28/r44;
next IPA requires a rebuilt/verified Kodi executable to include the Browse guard. Phone/provider/Roku acceptance
and final paging/action smoke tests remain pending.

Left out: unfinished Phony empty-show UI. The downloaded grid lists folders, so a poster does not prove completed
episodes; source queue/status repairs are included, but the separate empty-page redesign was excluded. A local WIP
patch is saved outside Git. AirPlay captions and the five-second Media Assistant/Umbrella stall need matching TV
session logs; no repair claimed. See docs/REVIEW-HANDOFF-PR16.md for included/remaining work and test limitations.


## In progress: season quality availability and missing paused queues — 2026-11-11 UTC

Owner holds the IPA (DEC-035). ISSUE-152: real packs only, otherwise inspect aired episode sources and offer actual
available qualities with coverage; exact chosen quality, real queue receipts and explicit pending opening retries.
ISSUE-153: logs prove a saved new movie job while uploads remained paused; missing pre-transfer rows, omitted Drive
queue rows, hidden Queue access and its three-row limit repaired. Refresh rereads durable jobs/pause state locally;
published native progress/reorder freshness is preserved. Existing dialogs/rows/tokens only, UI policy/HIG read.
Focused picker/redirect/save/retry/controller tests pass; expanded tests and desktop Kodi 21.3 rig checks running.
No new IPA, native build dispatch, pin update or main merge. Native r28/r44 remain delivered in IPA 223.

Owner corrects subtitle report: Download subtitle and phone captions work. Browse opens FileBrowser.xml then Kodi
stops handling taps while background diagnostics continue (ISSUE-154). Remote initial-directory enumeration is a
candidate, not a proven stack-level root cause. Reported Media Assistant five-second stall and AirPlay captions
need matching TV-session evidence; requested the post-test log and subtitle-enable timing. Do not mark them fixed.
Private logs and rig images remain outside Git; initial verification/setup failures retained in ISSUES.

## Verified test IPA 223 delivered — 2026-11-10

[Download IPA 223](https://github.com/onlykappa/Kodi-Ios/releases/download/build-223/Kodi-iOS-Customized-Touch-r10.ipa).
Owner-approved source f6b40982b97c8d67976e748e98381cfe7fd03759; successful run 42887751497. Includes all three
playback recommendations, downloaded-movie Continue from/Start from beginning, and the earlier startup/automatic
new-episode source checkpoint. Kodi r28 and AirPlay r44 are rebuilt, verified and pinned; this includes the native
repairs, rather than repackaging old r26/r43 binaries. Failed 222 stopped at an old test pin and was never delivered.

Seek target survives unrelated pointer events/progress polling until observed landing or a bounded timeout,
including fractional baseline cases. Subtitle work is retained/cached on an independent reader; unfinished/failed
cues are retryable rather than blank successful captions. Safe native/player/source/receiver snapshots retain
unexpected/early ends and stalls locally and in log export. Downloaded movies reuse shared history/bookmarks,
offer Continue from or Start from beginning, record uncached media without inventing provider IDs, preserve
provider choices, protect opening/handoff progress and save actual TV time. Existing saved progress is reused;
progress that old versions never recorded cannot be reconstructed. Existing Kodi controls/select menu only.

Final IPA CI passes 62 Python suites / 1094 tests and 46 actual slider/gesture/info-refresh scenarios. Native CI
passes 3336 checks plus end-to-end conversion; full local native suite passes 3252 checks with the documented
host font. Downloaded IPA is 620,552,475 bytes; SHA256
03a48d7e72560de5e03f1d0690e7d44fb210584fd78b1c374c3358930666366a. ZIP/asset digest, exact independently verified
r28/r44 binaries after signature removal, new native exports, 22 source helpers, 21 matching Python 3.11 hashes and
154 unsigned/unencrypted ARM64 images verified. Native artifact/release/upstream/source/patch provenance recorded.
Receipts: reports/playback-retention-delivery.json and reports/playback-retention-checks.json. PR #16 updated;
main remains unchanged. No owner media/account accessed. UI policy/HIG followed; actual iPhone/Roku/provider/new-
episode and visual acceptance remain pending. Historical continuous-hour stop cause remains unknown; this update
adds retained stop evidence. Install as an update, then test saved library resume/restart, seek landing, captions
and AirPlay on the receiver. Existing roadmap acceptance counts remain unchanged.

## Code ready, IPA held: AirPlay startup and followed episodes — 2026-11-10

Owner requests the AirPlay repair/diagnostics and automatic downloads for newly aired episodes, checking on app
opening rather than continuously; explicitly holds IPA publication. ISSUE-149 / ISSUE-150 / DEC-033 record scope.
AirPlay source now uses a shared 100-second native startup deadline measured from reservation, with a 5-second
controller grace advertised by a new optional native API. Legacy frameworks retain their 60-second controller
behavior. Initial video/audio priming runs in parallel at the actual resume segment, reuses that segment's init,
and no longer speculatively produces segment zero. Logs separate source codec/profile/depth, audio open/seek/scan,
HTTP/cache timings, cancellation/deadline evidence and background pause state without source URLs or credentials.

Confirmed TV downloads enroll their canonical show ID and chosen source preferences. A bounded opening/foreground
pass reads fresh show/season dates, skips future/undated/special/old episodes, checks existing Drive/phone files and
queue jobs, and uses the existing Elementum → AllDebrid → Drive route for new episodes. Failed sources retry on
later eligible openings; cancellations are respected. Request IDs prevent stale/background choices from becoming
manual dialogs or a different episode. Queue writes serialize deduplication and distinguish seasons of one pack.
Library settings has an automatic-download switch; the existing season menu offers Follow new episodes only for
already downloaded shows. The Apple UI policy and routed project/HIG guidance were followed; existing controls
only. No available desktop Kodi binary was found; visual/device acceptance remains pending.

Host verification: 32 Python suites / 742 tests and 211 native checks pass; project/UI/diff checks pass.
Evidence and retained test failures/retests: reports/airplay-opening-episodes-checks.json. Native streaming,
startup, cancellation and seeking checks pass against generated media; calendar/provider selection and actual
queue integration are exercised with synthetic dependencies. No owner account/media accessed. No native iPhone
framework, IPA, workflow dispatch, release, push or main merge is part of this checkpoint. Pins remain verified
Kodi r26/AirPlay r43. Before an eventual IPA, rebuild/verify/pin the changed AirPlay framework so these native
repairs are actually included. Real iPhone/Roku/provider and future-episode acceptance remain pending. ISSUE-147
seek intent/captions/continuous-hour failure remains separate and unrepaired; roadmap acceptance counts unchanged.

## Verified test IPA 221 delivered — 2026-11-10

[Download IPA 221](https://github.com/onlykappa/Kodi-Ios/releases/download/build-221/Kodi-iOS-Customized-Touch-r10.ipa).
Source fcae63e0f3dc83a8fb537cbea4d863e3ebfc5b29; successful run 42842353113. Supersedes cancelled build 220
(no delivery) after the final active-file/transaction audit-request guard. Refresh now re-inspects every eligible
file for compatibility and faster opening, including cached/prepared files, and queues only missing work.
Supported picture stays at source quality; faster-open preparation copies it. Already fast files stay unchanged.
Umbrella's actual service cache registers on Kodi Home instead of the filesystem Path. See ISSUE-148 / DEC-032.

66 host suites / 1,174 unit tests plus 32 existing slider scenarios pass; all CI stages, including bundle
reapplication/restore, pinned native acquisition, IPA validation and publication, pass. Downloaded IPA is
620,497,669 bytes, SHA256 701e8147920a6c504890c0331b7e5e37cde26a8890925518946254166d4f7838.
ZIP integrity, all 19 relevant source helpers and matching Python 3.11 source hashes, exact verified r26/r43 native
binaries after signature removal and 154 unsigned/unencrypted ARM64 images verified. No native pin change.
Receipts: reports/refresh-layout-cache-delivery.json and reports/refresh-layout-cache-checks.json.

Install as an update, open Library status and press Refresh; allow the full audit to finish. Already fast files
should remain ready; compatible files missing layout work should queue faster opening, without video re-encoding.
Test Umbrella AirPlay and Media Assistant on the actual receiver. UI policy followed; existing fact/status slots
only, with device/visual acceptance pending. No owner account/media accessed. ISSUE-147 seek/subtitle/hour-stop
issues remain separate and unrepaired. Main and roadmap task acceptance counts unchanged.

## Full Refresh audit and Umbrella cache startup repair — 2026-11-10

Owner build-219 log confirms compatible files skip conversion, but faster-open work was also suppressed.
Explicit Refresh now repeats native track inspection and bounded MP4 layout reads for every eligible listed file,
including cached/prepared files. It distinguishes a copy-safe picture from a front-indexed progressive MP4 or a
fragmented MP4 with a completed, valid random-access index. Known v1 fragment layouts still need the v2 repack.
Already fast files stay unchanged; a missing container/index step queues faster opening with the picture copied.
Unsupported picture keeps the conversion path. No complete local movie download is needed for this inspection.
Exact source identity is checked again after inspection. Active native work defers full checks, including when it is the only library file; transaction recovery also
retains the explicit audit request until it can read the resulting file. Newer requests,
owner-kept choices, commit recovery, staging/resume checkpoints and retry delays remain protected.

The same log reports PosixPath.setProperty in media_source_bridge at startup. Both recorded Umbrella attempts
have source_cache=false; one aborts and another exceeds its 45-second pre-TV opening deadline. Registering the
broker through xbmcgui.Window(10000) fixes that concrete wiring defect. Shutdown removes only its own property
and closes its source; a registration failure closes the already-started server. The integration regression
executes the real service setup with a Path home, opens/range-reads its selected source, then checks shutdown.
It fails against the previous service and passes with the repair. This does not establish a Wi-Fi fault or prove
that every provider/receiver combination now plays. Native seek/subtitle/hour-stop ISSUE-147 remains separate.

UI policy/skill followed; existing fact slots distinguish faster opening from picture compatibility, with no
layout/style changes. Actual iPhone/Roku/provider and visual acceptance remain pending. No native pin changes;
no owner Drive/media account access. Host verification and delivery status: reports/refresh-layout-cache-checks.json.
Main and roadmap task counts remain unchanged.

## Supplied old log matches the same short session — 2026-11-10

The new kodi.old.log contains the exact 1,993 lines already reviewed plus 59 shutdown lines (17.764 s). It spans
21:38:48.457–21:44:14.627, still build 217. Kodi starts orderly shutdown at 21:44:10, three minutes after the
captured AirPlay player closed; that shutdown does not explain the earlier playback failure. The added tail has
no crash trace and ends during teardown, not a proven final exit. Continuous-hour playback/stop remains absent.
Seek/subtitle defects remain confirmed; the hour-stop cause remains unknown. See ISSUE-147/report follow-up.
Next occurrence: export before closing/restarting Kodi. Review only; no app changes, new build or main merge.

## New seek/subtitle/AirPlay-stop log reviewed — 2026-11-10

Owner asks to investigate seek release, missing captions and continuous AirPlay stopping after about an hour.
The five-minute log identifies build 217, sharing native r26/r43 with 219. Eight seek releases each block 500 ms;
video after-flush markers reach 7.561 s. Expanded actual-slider/info-refresh host reproduction shows normal 50%
release immediately redraws old 3% while a seek is pending; an intervening mouse event can also make it submit 3%.
The log lacks target/landing/event detail, so exact device-path attribution remains unproven. Earlier 32 r26 cases
omitted those refresh/interleaving paths; no prior device acceptance is retroactively claimed.

Captions are selected, but 32 native subtitle-read failures and 31 successful HTTP responses containing empty
8-byte WEBVTT match the native 1.5-second caption deadline. Failure is masked as a blank successful caption. The
short AirPlay session also shows slow reads/CoreMedia errors, but the owner's continuous-hour stop is not present
in this capture; need kodi.old.log or a capture of that stop. See ISSUE-147 and reports/seek-subtitle-stop-review.json.
Investigation only: no app/native source change, new build, account/media access, or merge. Source repair/device
acceptance remain open; existing build 219 should not be presented as fixing these newly reviewed native defects.

## Build 219: Refresh inspection and streaming recommendations delivered — 2026-11-10

[Download test IPA 219](https://github.com/onlykappa/Kodi-Ios/releases/download/build-219/Kodi-iOS-Customized-Touch-r10.ipa).
Run 42755715794 passed all test, bundle reapplication/restore, native acquisition, IPA build/validation and publication
stages from 2d658de5ede446f9d8170a5c0185b1e5ee3c3efa. Includes compatibility-first originals, explicit Refresh
inspection, adaptive preparation uploads, independent upload/wait progress, and one selected Umbrella/AllDebrid
link renewal. Existing verified Kodi r26 / AirPlay r43 and seek/scheduler repairs are retained.

Downloaded 620,487,865-byte IPA matches release SHA256
a9b36d4ef3c8bcdc66a422ffa8e4c30cb83637125f8d893387e7a3dd47af224b, passes ZIP integrity, and embeds exact
verified native binaries after signature removal. All 18 relevant source helpers and their Python 3.11 source hashes
match; 154 ARM64 images are unsigned/unencrypted. Receipt: reports/refresh-streaming-delivery.json. Source checks:
24 focused suites / 545 tests plus 38 remaining packaging test scripts and all CI gates. Failed build 218 is retained
in ISSUE-146; it produced no IPA. Main and roadmap phase/task counts are unchanged.

Install as an update, open Library status and press Refresh. Allow track inspection to finish; compatible Lanterns
should stay Ready without conversion/upload. Unknown probes defer while an active conversion uses the same native
instance. Test Umbrella AirPlay and Roku Media Assistant separately with captions and seeking. UI policy read,
existing layout/style retained; actual iPhone/Roku/provider and visual acceptance remain pending. No owner media or
Drive account was accessed during these host tests.

## Upload, progress, expired-link recovery and Refresh inspection — 2026-11-10

Packaging checkpoint: build 218 / run 42755096028 stopped before IPA creation on an obsolete AirPlay wording
assertion. Corrected it; all 29 remux/routing tests and all subsequent packaging test scripts pass locally. The
customized-IPA test also passes with the installed Python 3.11 environment configured as in CI. Details and the
failed run are preserved in ISSUE-146/report. No app source/pin change was needed. A new packaging run follows.

Owner authorizes all three recommendations in the build and asks Library status Refresh to read files so a ready
Lanterns episode is not converted again. HTTP preparation uploads now start at 1 MiB, adapt to 1–8 MiB aligned
pieces, and retain the existing 32 MiB producer/resume pieces plus 256 MiB checkpoint window. Every acknowledged
HTTP piece refreshes confirmed-byte/speed evidence. A full failed upload queue cannot hang finalization.

Independent heartbeat carries upload bytes, speed and request age while native progress callbacks are blocked.
Existing UI slots say Checking compatibility, Uploading to Google Drive or Waiting for Drive as appropriate;
explicit pauses and verification stages remain authoritative. No layout/style changes; UI policy read.

Refresh requests native track inspection of unknown streamed files before conversion is queued. Exact unchanged
Drive identities reuse saved compatibility after restart; changed files are inspected again. Prepared originals
stay ready, unknown/failed inspections are never labeled ready, and owner-kept/committing files are protected.
Beside an active conversion, metadata/cached decisions update immediately and native inspection waits for idle;
newer/manual requests survive automatic checks and an older scan finishing.

Umbrella/AllDebrid remembers only the selected unlock link in RAM. The existing foreground cache renews that same
file once on HTTP 401/403/404/410 with the existing account; no new scrape/torrent/download. Concurrent readers
share one renewal, provider headers persist, and changed filename/size/range totals are refused. The guarded hook
was compiled and executed against current public upstream code; unknown versions stay untouched.

Validation: 24 focused suites / 545 tests pass, including refresh/compatibility 21, transfer efficiency 9, selected
link recovery 13, cloud transactions 26 and existing resume/scheduler/casting/status tests. Project scanner and UI
guidance pass. Unchanged real native host bridge yields the same first video-segment hash in all modes: direct
8 requests / 1.255 s; cache 3 / 0.378 s; simulated expired link 4 / 0.511 s with exactly one API renewal. Generated
fixture and mocked unlock API/local HTTP only; no owner media/account access. Host timing is not a Roku/device pass.
Evidence: reports/refresh-streaming-checks.json; failures and fixes: ISSUE-146. Verified Kodi r26/AirPlay r43 pins
are reused. Updated test IPA packaging follows for the owner's requested retest; no main merge. Visual and actual
iPhone/Roku/AllDebrid acceptance remain pending. Previous build 217 does not contain these latest changes.

## Compatibility-first preparation and separate Umbrella cache repair — 2026-11-10

Owner asks to avoid unnecessary conversion, keeping the working Elementum/Drive workflow, and identifies
Umbrella AirPlay as a separate bug. Native inspection now skips background conversion/upload for copy-safe
H.264/HEVC, keeping the original Drive file and exact-source local readiness. Container/audio adaptation remains
on demand during playback. Already prepared files no longer get optional automatic repacks. Unknown/unsupported
video retains preparation, original protection, resumable commit recovery and owner-kept choices.

The latest Umbrella log fails at the 45-second source-opening deadline, with 43.045 seconds in index inspection,
before TV handoff. Remote MKV/AVI/WebM now reuse Drive's byte-range engine through a service-owned foreground
cache (2 MiB blocks, 32 MiB retained cache, no background throttle, original provider headers, no Drive OAuth).
Successful AirPlay/Media Assistant handoff retains it after the UI interpreter exits; failed/cancelled startup closes
it. Existing loopback Drive/Elementum, MP4 and HLS paths retain their routes. This is a repair candidate, not proof
of device/provider/receiver success. Native host test with a generated MKV and 150 ms request delay produced an
identical 467,251-byte first video segment: direct 7 requests / 1.080 s; cache 3 requests / 0.335 s. Counts/timing can
vary with concurrent read-ahead. No owner's media URL or account was accessed.

Validation: 17 focused suites / 442 tests, UI guidance and project checks pass. Test failures and the newly caught
cache lifetime bug are preserved in ISSUE-145. Report: reports/compatibility-filter-review.json. Existing status
wording now says Checking compatibility and Ready to stream; UI policy read, layout/style unchanged. Visual and
iPhone/Roku acceptance remain pending; desktop rig binary is absent and was not rebuilt. No new native binaries,
IPA publication or main merge in this source change. Next: owner device retest using an authorized updated IPA;
verify existing compatible queue drains without Drive uploads, then test Umbrella AirPlay/Media Assistant separately.

## Build 217 conversion stall review — 2026-11-10

New device log confirms automatic recovery of the saved conversion pause and pending starts. Conversion runs
and advances to 7.519% (displayed as 8%), while 32 MiB Drive uploads take 121–146 s at 0.22–0.26 MiB/s. A
successful acknowledgement occurs eighteen seconds before the log ends. This is slow ongoing work with long
backpressure stalls; no permanent app freeze is established. The separate conversion uploader still uses fixed
32 MiB pieces, and its upload waits do not independently update the progress/speed UI. See ISSUE-144. Review
only; no new code/build. Seek and Roku acceptance remain pending.

## Build 217: seek release and automatic-work repairs delivered — 2026-11-10

[Download test IPA 217](https://github.com/onlykappa/Kodi-Ios/releases/download/build-217/Kodi-iOS-Customized-Touch-r10.ipa).
Packaging run 42732787090 passed from 16daca2621ad1272a84991e4fcb9b5c4cd051c30. Includes verified Kodi r26
(native run 42705743785) and unchanged AirPlay r43. Gesture release commits the displayed percentage; Start now
resumes valid queued conversions and recovers requests left pending by older builds before the pause skip.
Eligible work starts automatically after five seconds at startup and is polled every twenty seconds while idle.
Explicit pauses and retry delays retain their effect. New logs distinguish pause, retry, account and lock gates.
The old device log did not establish which saved gate was active, so no retrospective pause-state claim is made.

Validation: 32 compiled real gesture/slider scenarios, 10 actual-service-loop scheduler scenarios, existing focused
Python suites, the native ARM64 build, actual native fetch contract, and all IPA workflow stages pass. Downloaded
IPA: 620,457,135 bytes, SHA256 206a63b5e1496130e0dd19e7bb20ef6c9a3f654f469e38979a5dcb122de78749.
Checksum, ZIP integrity, exact r26 executable/r43 framework after signature removal, current helpers, four changed
modules' Python 3.11 source hashes, and 154 unsigned/unencrypted ARM64 images verified. Receipt:
[reports/seek-queue-repair-delivery.json](../reports/seek-queue-repair-delivery.json).

Install as an update and keep Kodi open at the menus for twenty seconds; check queued work starts, drag and release
at several positions, and try Start now on a queued conversion. Drive setup and layouts are preserved; the UI policy
was read. Actual iPhone touch, automatic-work behavior and Roku playback/captions remain pending device retest.
Main and roadmap phase counts are unchanged. ISSUE-143 preserves the prior device failure and harness failure.

## Seek release and automatic-work repairs authorized — 2026-11-09

Owner requests fixes plus a new IPA and automatic background work while idle. Native r26 retains the dragged
percentage on release; 32 compiled real gesture/slider scenarios pass, while r25 fails the same regression.
Native r26 build/publication passed in run 42705743785, including the 32 scenarios against the actual native
tree. Release binary/artifact, archive and patch hashes and the real fetch contract verified. Scheduler fixes and
diagnostics pass 10 tests, and portrait 50/glass-bar 28 regressions pass. Verified IPA 217 is delivered above.
Start now resumes the conversion channel and recovers old pending requests before pause gating. Eligible idle
work is checked automatically after 5 s at startup and at most 20 s between idle passes; explicit pauses and
retry backoff remain respected (ISSUE-143).

## Build 216 owner retest: seek/queue failures reviewed — 2026-11-09

Owner confirms smoother dragging but releasing seeks to the start. Exact pinned Kodi event packing exposes a
regression in the new release handler: velocity is interpreted as slider position; reproduced 50% → 0%.
The log/screenshot show seven waiting conversions, zero active, rather than evidence of a hung encoder.
Start now also has a reproduced conditional bug: a persistent conversion pause prevents request consumption and
is not cleared by the action. The device pause flag is absent from this log, so the exact queue blocker is still
unconfirmed. See ISSUE-143. Findings review only; no behavior edits or new IPA. Device acceptance remains open.

## Build 216: recommendations and repairs delivered — 2026-11-09

[Download test IPA 216](https://github.com/onlykappa/Kodi-Ios/releases/download/build-216/Kodi-iOS-Customized-Touch-r10.ipa).
Packaged from fd6ef1cdc7ca26397d1cfea0c0486bb270490417 by successful run 42698801783. Includes verified AirPlay
r43 (3,319 host checks, zero failures, E2E recovery and ARM64 compile) and Kodi r25 (touch drag/seek diagnostics).
The downloaded 620,454,027-byte IPA matches asset SHA256 df65bccbbc3d22ca09d65b17309f58014911f810ce9818406ecdb2ce96c1ef93,
passes ZIP integrity, and embeds the exact verified framework/executable after signature removal. Current helper
sources, Python 3.11 bytecode, diagnostics and 154 unsigned/unencrypted ARM64 images verified.
Receipt: [reports/streaming-recommendations-delivery.json](../reports/streaming-recommendations-delivery.json).

Install as an update, keep the existing Drive setup, and test Media Assistant first with captions enabled in Kodi
and Roku. Check five minutes of playback, forward/backward seeks, then native AirPlay separately. Compatible
4K HEVC stays copied; Roku H.264/compatibility conversion can use 1080p SDR. Actual fluidity, captions, sound and
visual/device acceptance remain pending. The UI policy was read and existing controls/layouts reused. The local
software reference was slower than real time, retained in its report; it does not measure iPhone hardware speed.
Main and device phase counts are unchanged. Build 215 stopped on an incorrectly typed digest pin; the corrected
binary pin passed the actual fetch contract before this successful build. ISSUE-142 preserves all failures.

## Owner-approved recommendations: implementation and IPA — 2026-11-09

All five recommendations are implemented: explicit receiver capability routing and one compatibility retry,
bounded adaptive prefetch with cancellation of obsolete copied reads, aligned 1–8 MiB upload chunks, explicit
read/upload/playback-hold stages, and native seek timing diagnostics. The r25 executable passed native build/publication in run
42692028826 and its release binary equals the CI artifact. Focused native checks passed (37 recommendation checks and 103 Roku regressions), along with
62 casting, 24 direct-transfer, 23 upload, 27 status, 29 remux-contract, 41 calibration and 50 portrait checks.
The UI guidance and project scans pass. Existing layouts and controls are reused; starting the existing desktop
rig confirms no Kodi binary is installed, so visual/device review remains pending. No desktop rebuild was started.
ISSUE-142 retains both native fixture failures and their diagnoses. Corrected native run 42695837108 passed
3,319 checks, zero failures, end-to-end conversion/recovery and the iPhoneOS framework compile. The candidate is
pinned as r43 alongside verified Kodi r25. Verified test IPA 216 is delivered above. Main is unchanged.

## Public 4K movie check — 2026-11-09

At the owner's request, downloaded Blender's public Big Buck Bunny 2160p movie and used this branch's native
streaming code against a 2 MiB/s HTTP source. Startup and five out-of-order seek requests passed; all retained
3840×2160, keyframe starts and monotonic decode timestamps. Four unique samples also decoded their first frame.
Cold fetches took 3.4–19.4 s; repeated segment zero took 5 ms. Receipt: reports/public-movie-seek-check.json.
The first test attempt used a stopped HTTP stand-in; restarting it and rerunning passed. GitHub release/artifact
inspection found rig scripts and iOS builds, no prebuilt Linux rig. No desktop Kodi rebuild was started, following
the owner's preference. These are host pipeline checks, not GUI, iPhone touch or Roku decoding acceptance.
The native AirPlay candidate framework compiled; its full host CI is still in dependency installation.

## Touch seeking and download progress repairs — 2026-11-09

ISSUE-141 records the new log review, native touch-slider fix and streamed-upload repairs. A compiled 100-move
gesture sequence now commits one seek on release; 47 download/upload tests passed. Streamed Drive copies use
8 MiB checkpoints, preserve read-ahead/resume, and commit success before playback throttling. These changes need
a new native build and actual iPhone test; no device pass is claimed. The Roku/caption candidate is source
`99fa9bd`; native CI 42685265901 is running, with the framework compile passed at this checkpoint.

## Build 214 owner retest: concrete Roku/caption repairs — 2026-11-09

The owner reports build 214 still fails on Media Assistant and has no captions; Apple TV works. ISSUE-140 records
four reproduced sender bugs and their repairs. Coalesced storage fragments now expose internal keyframes to the
Roku streaming plan without changing Drive files or 4K picture; partial segment writes report progress; captions
seek/read only their track; and the TV server receives Kodi's actual caption selection. Optional safe Roku ECP
feedback records receiver state/model and distinguishes buffering/error from delivered bytes.

Before: 46 regression checks, four failures. After: 102 checks, zero failed, including decoding all 768 video frames
exactly once, caption forward/backward seeks, partial delivery and corrupt-header rejection. Local streaming (141),
startup (13) and Python (142) checks also passed. Native CI and a new IPA follow. This is a repair candidate,
not a real Roku playback pass. See [receipt](../reports/roku-build214-retest.json) and ISSUE-140. Main and device
roadmap counts are unchanged.

An additional signed-CTS/B-frame fixture exposed a FFmpeg MOV timestamp sign error, per-fragment presentation
offset resets and average-frame-rate decode drift. The patch keeps signed offsets signed, uses TFDT for actual
decode time while MFRA locates fragments, and uses one presentation offset plus the nominal frame rate. All 768
frames in that fixture now decode once, too. The FFmpeg patch and relink notice ship with the framework.

## Roku/Drive build 214 delivered — 2026-11-09

[Download test build 214](https://github.com/onlykappa/Kodi-Ios/releases/download/build-214/Kodi-iOS-Customized-Touch-r10.ipa).
The owner authorized repairs and a test build, preserving the current Drive workflow.
[IPA run 42641842437](https://github.com/onlykappa/Kodi-Ios/actions/runs/42641842437) passed all app/casting,
assembly and packaging gates from `f523dfca7fc9525436024e0b6efeaf9214b64bf5`. It embeds verified r42 source
`03859028e2fb5abda6888101ba5f8a3cf7a0ab8b`; native run 42639212562 passed 3,231 checks, E2E conversion/resume
and the iPhoneOS compile. The saved-file playback check used 39 requests (budget 60).

Downloaded IPA: 620,439,230 bytes, SHA256 `7decfff5fa03b593844e940d02f7e5e7a3ba4e4d28814ddaf7dc220cba44ad46`.
Asset digest, ZIP integrity, build/commit identity, exact r42 framework equality after signature removal, current
controller/helper sources, Python 3.11 bytecode and 154 unsigned/unencrypted ARM64 images verified.
Receipt: [reports/roku-drive-test-delivery-r42.json](../reports/roku-drive-test-delivery-r42.json).

Install as an update and reopen Kodi. Test the same two Drive movies, Media Assistant first for retained compatible
4K, then native AirPlay; check startup, sound, several minutes of playback and forward/backward seeks. AirPlay's
compatibility conversion can use 1080p SDR. Older prepared movies keep truthful longer random-access windows,
which can need more initial buffering. See [ROKU-STREAMING.md](ROKU-STREAMING.md) for the local-network/Drive
explanation and recommendations.

Device acceptance remains open. The local non-assembly software HDR cancellation timing limitation remains in the
native receipt/ISSUE-139; accelerated native CI passed its timing check. No live Drive account/media was accessed,
no main merge occurred, and device task counts are unchanged.

## Verified r42 Roku/Drive candidate — 2026-11-09

Final source `03859028e2fb5abda6888101ba5f8a3cf7a0ab8b` passed
[native CI 42639212562](https://github.com/onlykappa/Kodi-Ios/actions/runs/42639212562):
3,231 host checks, zero failures, E2E conversion/resume checks, and the iPhoneOS ARM64 framework compile.
Sequential Kodi-style playback used 39 upstream requests (budget 60), retaining the efficient saved-file layout.
The archive for r42 is SHA256 `1f7432be8794997c17b821bb6521fa8aa55349dd0cd5f2c54d56e6b0f5cf661b`.
Native receipt: [reports/roku-streaming-repair-native.json](../reports/roku-streaming-repair-native.json).

Fixes include shared requested-byte reads, independent init delivery, initial media buffering, truthful
random-access windows for long-GOP prepared movies, bounded subtitles, resume ownership and video-delivery
readiness. The error card no longer labels queue waits or canceled requests as slow internet. Existing Drive
movies remain the source; compatible 4K is copied by Media Assistant. Newly converted video has frequent keyframes;
the saved-file fragments remain coalesced/interleaved for Kodi efficiency.

Focused Python checks: 100 casting/UI and 48 conversion checks pass; project and UI guidance checks pass.
The new casting regressions now run in IPA CI. The local non-assembly Linux reference exceeded the software HDR
cancellation timing budget; tracing isolated the wait to color conversion, while SDR cancellation passed 20/20
and the accelerated native CI passed its timing check. Actual iPhone HDR/cancellation behavior remains pending.
The existing card layout is reused; this workspace cannot start the desktop Kodi rig because its binary is absent.

Publishing the verified framework and packaging the test IPA are next. Device picture, sound, sustained playback,
HDR and seeks still require owner testing. Main is unchanged. See [ROKU-STREAMING.md](ROKU-STREAMING.md).

## Build-213 Roku repair — 2026-11-09

The owner's new log confirms r41 failed for two movies over both Media Assistant and AirPlay. The owner explicitly
requests repairs and a test build, retaining the current Drive workflow. ISSUE-139 records the log evidence and
root causes; ISSUE-138 is now marked failed on the owner's device rather than merely pending.

Implemented shared cached Drive reads, independent fast init delivery, first-segment buffering before receiver
launch, a whole-request subtitle deadline, video-delivery readiness, prepared-range progress counters, resume
ownership and factual timeout wording. Media Assistant retains compatible 4K; native compatibility conversion may
use 1080p SDR. Recommendations and acceptance steps: [ROKU-STREAMING.md](ROKU-STREAMING.md).

Focused validation: 39 source/init checks, 13 startup/early-header/subtitle checks and 117 focused streaming checks pass; 100 Python casting/UI
checks and the project/UI guidance checks pass. The first candidate (4ad5b34, run 42558496051) passed 3,207 native checks, E2E conversion and iPhoneOS compilation;
its local suite passed 3,114 checks. A later long-GOP fixture exposed repeated/mislabelled copy windows. The final
repair uses the prepared file's complete random-access index, retains older long windows at source resolution,
and gives newly converted video frequent keyframes. The coalesced saved-file layout remains for efficient Kodi reads. Targeted streaming checks now pass 141 checks;
full validation of this additional source change is in progress. The desktop rig cannot start in this workspace because its Kodi binary is absent; existing card layout
is reused, with device visual review pending. Native publication, IPA packaging and device acceptance are not yet
complete. Work stays on PR #16's feature branch; main is unchanged.

## Roku from Drive: test build 213 — 2026-11-09

Owner explicitly requested a test build in the current session. Packaged the existing r41 candidate from
`551f32c876df6bbabce4148a96ff3f00d6076dcd` on PR #16's feature branch; no main merge or new streaming-source change.
[Download build 213](https://github.com/onlykappa/Kodi-Ios/releases/download/build-213/Kodi-iOS-Customized-Touch-r10.ipa).
[IPA workflow 42550189064](https://github.com/onlykappa/Kodi-Ios/actions/runs/42550189064) passed all stages.
The r41 native candidate run 42547843379 passed 3,177 host checks, the end-to-end conversion checks and the iPhoneOS
framework compile. Local project checks and 127 focused Python tests passed.

Downloaded IPA: 620,433,205 bytes, SHA256 `fabcb829d99c2f737f7206ecd697b6e3193d79266e1ebad3b8a5a63721175945`,
equal to the GitHub asset digest. ZIP integrity, build/commit identity, embedded framework equality with the verified
r41 release after signature removal, Roku segmented route, Python 3.11 bytecode and 154 unsigned, unencrypted ARM64
images verified. Receipt: [reports/roku-drive-test-delivery.json](../reports/roku-drive-test-delivery.json).

Next: install as an update and play the same 4K movie from the existing Drive library using Media Assistant first,
then AirPlay; check startup, sustained playback and forward/backward seeking. Media Assistant copies compatible
4K video; the AirPlay compatibility fallback converts video and can reduce resolution. Cold prepared-file cache
misses still fill a complete block; r41 changes the Roku route and warms the as-is path, not demand-first reads.
Device/Drive/Roku acceptance remains pending; no live account or media was accessed. Main is unchanged.

## One-file source-resolution preparation — 2026-11-05

Owner reports build-151 stops on a long AirPlay seek and requests startup scanning plus a third preparation step after Drive upload. Owner explicitly rejected a separate AirPlay copy and requires the selected resolution: **4K stays 4K; 1080p stays 1080p; preserve compatible HDR**. Implemented on `feature/preconvert-downloads`, draft PR #10; main has not been merged.

The new private log establishes current r12 diagnostics and a 20.812-second target lane wait, with 17.712 seconds of source I/O in an older foreground segment. Preparation now updates the same Drive file ID with a validated, indexed MP4. Compatible H.264/HEVC video packets are copied unchanged; audio/text are prepared for MP4. Notifications shows progress and queue status; work is resumable, pauses during playback and uses one temporary working set. Changed Drive source versions and verification failures stop replacement. Unpreservable bitmap tracks/HDR conversions retain the existing file rather than discard tracks or downgrade quality.

Prepared playback uses independent authenticated-by-path HTTP byte ranges on the phone's Wi-Fi address, without live conversion, subtitle burn, prefetch lanes or automatic 1080p fallback. Source resolution/HDR are checked again before replacement. Full details: [one-file preparation](DOWNLOAD-PREPARATION.md); evidence: reports/download-preparation-validation.json.

Final candidate source `c7a5e1250a5ad53854674dc453dcbf368de53c5a`, clean native CI [42099308207](https://github.com/onlykappa/Kodi-Ios/actions/runs/42099308207): **1,579 checks, zero failures; iPhoneOS ARM64 framework compile passed**. AirPlay r13 published via [42100250341](https://github.com/onlykappa/Kodi-Ios/actions/runs/42100250341); downloaded archive matches the verified candidate SHA256 `e5e45d2ea2c08208127fba5ad9d9bcde0da0f0a7f16db994c869cd233ca7dce2`. **[Download build-152](https://github.com/onlykappa/Kodi-Ios/releases/download/build-152/Kodi-iOS-Customized-Touch-r10.ipa)** from `cf2ef5d`; [IPA run 42100422540](https://github.com/onlykappa/Kodi-Ios/actions/runs/42100422540) passed. Downloaded IPA SHA256 `3b5a50c338277aca77256b0926ca62fe47892b2aa8e3b8047394319becd634b2` matches GitHub asset digest (619,464,663 bytes). ZIP integrity, r23 executable, r13 AirPlay/r5 GlassBar binary equality after signature removal, all 154 unsigned ARM64 images, tested preparation Python/3.11 bytecode, default-on startup worker and notification progress are verified. Next: install as an update, let preparation finish in Notifications > Downloads, then retest the long seek. Physical iPhone/Drive/Roku acceptance remains pending; no owner media was accessed or converted by this executor.

## Apple UI guidance integration (PR #11) — 2026-11-05

Owner asked to permanently integrate Apple UI design resources before the activity pill work continues, after build-152 showed overlapping text in Notifications (logged as ISSUE-101, to be fixed on PR #10). Branch `design/apple-ui-guidance`, draft PR #11; no merge or release. Added: root [AGENTS.md](../AGENTS.md) and [CLAUDE.md](../CLAUDE.md) (neither existed), canonical [Apple UI policy](design/APPLE-UI-POLICY.md), [resource provenance and update procedure](design/apple-ui-resources.md) with a SHA-256 lock, vendored `apple-hig` and `apple-liquid-glass` skills under `.agents/skills/` (Codex discovery) with pointers in `.claude/skills/` (Claude Code discovery), a project `kodi-ios-ui` skill, and `scripts/check_ui_guidance.py`. `check_project.py` now allows those paths and vendored licence files. Decision: DEC-026. Checks: check_ui_guidance passes (186 vendored files hash-verified; negative tests detect modified/missing/extra files, broken links, unknown routing topics, renamed helpers and bad skill names); check_project passes (565 files); test_checks, test_portrait, test_pages, test_settings_page, test_notices, test_glassbar, test_native_ui, test_ios_navigation and check_ios pass. Pre-existing: `check_roadmap.py` fails on main with "Stale progress" (unchanged here). No UI was changed, so no rendering was needed; the policy itself was not visually verified on device. The owner then supplied two desktop Kodi rig renders of PR #9's pill and sheet (not device; build-151 lacks the pill). They are recorded as the reference look in policy §4, and the review findings are in ISSUE-102 (empty progress ring, small touch areas and glyphs, two blues; the native bar is untested in the rig). Next: fix ISSUE-101 on PR #10 under the new policy, then rebase/restyle PR #9's activity pill against it.

## Latest delivery and supplied AirPlay log — 2026-11-05

Owner requested completion of the fresh r23 test IPA and reports scrolling is fine. r23 native run 42078285510 passed compile and publication. Downloaded release binary equals the native CI artifact byte-for-byte; executable SHA256 `9fa9ad78f8613bf4ce4b369eb19e46bfe5a99bc934f568d16dd0953c946fb7fd`, patch SHA256 `054c3ff6ea11ebcdc3f95cf422627193335ceb34d4d770247da83b002c5f25cf`, and pinned upstream commit all verified. Pin updated on main at `463bbae440d4302bf68cbe7a84197f6fe8be9084`, triggering the test IPA workflow. AirPlay r12 and GlassBar r5 retained. First IPA attempt (run 42090224927 / build 150) stopped before packaging: test_glassbar still hardcoded r22/r21. Updated the regression to require verified r23 and previous r22 binary hashes (25 tests pass), committed at d95295e, and dispatched a fresh IPA run. Redundant native rebuild 42090224839 cancelled because r23 was already built/verified. **Delivery complete: [build-151](https://github.com/onlykappa/Kodi-Ios/releases/tag/build-151)** from d95295e, [CI run 42090634251](https://github.com/onlykappa/Kodi-Ios/actions/runs/42090634251) passed. Downloaded IPA: 619,424,613 bytes; SHA256 `da6b7bf89a0f41869e754c378a9bdc378c4b333b9b968263f7c0c6f009963549`, matching GitHub asset digest. ZIP integrity passes; executable equals verified r23 after signature removal; AirPlay r12 and GlassBar r5 equal their pinned releases after signature removal; all 154 native images are unsigned, unencrypted ARM64; required add-ons and Python bytecode present. Local suites: portrait 44, glassbar 25, AirPlay static/routing 27, foundation 11, native show scrolling 7 and parent navigation 1 pass, plus project/iOS static checks. See reports/ipa-test-delivery.json. Next: install as an update and retest AirPlay seeking; no new-device success claimed. Older handoffs below retain history and may describe superseded pins/build restrictions.

AirPlay screenshot and supplied private kodi.log agree: HTTP 500 on `/cvideo/seg8.m4s`, `video conversion: cancelled`, followed by player stopped. The completed movie was uploaded to Drive before playback; playback then opens through plugin.googledrive and its local HTTP proxy, so the capture does not establish direct phone-file playback. Source is 4K HEVC/10-bit; the Roku receives H.264 1080p from VideoToolbox conversion. Typical six-second segments take 3.581–5.914 seconds; a later segment takes 6.834 seconds. This is conversion/scheduling pressure, not evidence of an incomplete torrent.

The captured AirPlay binary logs the older conversion-message format without the source-I/O/preroll and queue/production diagnostics present in current source and the downloaded, checksum-verified r12 binary. This strongly indicates an older framework; the log does not record a framework hash/version, so the exact installed release is not proven. Current r12 contains the background-only cancellation/ownership fix and retires cancelled decoder/source state. Do not claim current r12 reproduces or fully fixes this phone failure without a new-build retest. Raw log, Drive IDs, proxy URLs and account state remain private. No speculative new AirPlay source patch was made for this review.

## Current handoff — 2026-11-05

Owner now explicitly authorizes **merging PR #8 and publishing a test IPA** ("merge pr 8 so we can start fresh and push me ipa for testing"). This supersedes the no-merge/no-IPA restriction for this delivery. Build the staged show-scroll/parent-row changes as **kodi-ios-portrait-r23**, verify the released executable and patch provenance, then update the executable pin before packaging the IPA. Merge with `[skip ci]` to avoid an intermediate IPA containing old r22, trigger the native build first, and trigger the IPA only after r23 is verified/pinned. Keep current AirPlay r12 and GlassBar r5. Merge/build/publication in progress; no device acceptance claimed.

PR #8 is merged at **2a8bb1cb16dfa0984f7a1b3d974e20857c0f6d3c**; its message contains `[skip ci]`, and the merged tree includes the r23 build tag with the executable pin still safely at r22. Native build is triggered separately by the focused native workflow update; the IPA workflow is not triggered by that workflow file. After r23 succeeds, download/check its binary and patch provenance, pin its verified hash on main, then the normal IPA workflow packages it. No new bug PR or branch deletion yet.

Latest continuation: owner supplied screenshots of Claude's unfinished downloaded-show/scrolling fixes. Synced PR #8 from `46367aab6fb3fe3943ee202b1801ca0b002b14be`, preserving all intervening changes and published r22 executable/r12 AirPlay pins. Downloaded seasons pages now have cached full-show metadata, exact completed-copy Play/Continue with progress/history, no Download action or fake refresh episode, and human page titles. Shared show-page layout and a narrowly scoped native header/episode gesture handoff provide whole-page scrolling in source; parent-row suppression prevents blank season/episode slots. **362 tests across 24 suites pass**, including host-compiled native methods, and the full patch applies to 30 pinned source files with semantic changes limited to five intended GUI files. See [current screenshot handoff](BUG-4-PROGRESS.md) and reports/downloaded-show-validation.json. **Native changes remain staged: the pinned r22 binary does not include the new scrolling code.** A separately authorized executable build/release/pin and phone test are still required. No new IPA, release or merge in this continuation; no new device success claimed. Earlier handoffs below describe previous commits, not this screenshot follow-up.

Current focus: owner bug **4 / ISSUE-094**, downloaded Library discovery and Settings › Library phone-file scan. See [live bug-4 progress](BUG-4-PROGRESS.md). Root navigation, completed phone/seeding discovery, loose Drive episodes, manual refresh, visible-page updates, checksum-verified upload/duplicate cleanup and Settings/search integration are implemented and pass **258 tests in 15 suites** plus project/iOS static and diff checks; evidence is in reports/library-downloads-validation.json. Delivery stays in draft PR #8 using `[skip ci]`. The owner explicitly requested parallel agents; scanner, Settings and regression/review work are split between three agents. No IPA, release, main merge, live account upload or phone deletion has been performed. Device Library/scan acceptance remains pending.

Latest AirPlay / owner bug **3 / ISSUE-093** source pass is verified in [clean CI run 41946561571](https://github.com/onlykappa/Kodi-Ios/actions/runs/41946561571): **1,385 native host checks, zero failures; iPhoneOS arm64 framework build passed**, with required symbols present and no source availability warnings. Also 35 Python/static tests and independent libplacebo pixel comparison pass. Tested source commit: `b148d23f819b5e427c294ed5a075aafbabf858f6`; CI differs only by a validation marker.

Changes: protect connected foreground requests while canceling speculative work; bound HTTP ranges/retry deadlines and interrupt canceled background waits; retire canceled decoder/source before foreground reuse; stop subtitle preroll on target video time instead of the next caption; recover long cues and preserve VobSub language; add profile-5 RPU reshaping/matrices/PQ mapping, HDR and format compatibility. Exact clean-CI reproduction exposed FFmpeg 8.1.1 misreading RPU trailing zero padding; the shipped LGPL patch fixes it with CRC validation retained. Previous failures are preserved in reports/airplay-coverage-validation.json and docs/AIRPLAY.md.

**Remaining acceptance:** actual iPhone/Drive/Roku forward/backward seek, picture/color/audio synchronization and sustained 4K throughput. No IPA was built, no framework release published, and PR #8 remains draft/unmerged. The owner previously prohibited an IPA; device testing requires that restriction to be lifted. Published framework pin stays r11. A future authorized test IPA must use a new verified framework release/pin; the candidate is not silently substituted for r11.

Owner-requested planning estimate: **about 90% overall; source readiness 4/10 before → 9/10 now**. These are subjective estimates, not measured phone performance. Automated/source verification is complete for this pass; do not label device acceptance or universal every-file support 100%.

Previous focused owner bug **2 / ISSUE-092**: Search category tiles ignored the selected Movies/Shows filter and always discovered TV. Source fix routes Movies to movie discovery and maps TV genre IDs to movie IDs (including Sci-Fi/Fantasy OR, Action/Adventure OR and War); Shows retains TV discovery. TV-only Reality/Kids are hidden under Movies. All retains its existing TV-category behavior. Working typed search and its filter controller are unchanged. Search tile-artwork refresh now yields off-page, while typing, playing video, showing dialogs or downloading/uploading, using existing activity state and cached artwork. This reduces avoidable contention but does not establish the cause or resolution of all download-related search lag. 143 affected host tests/10 suites pass; pinned Helper translation preserves 22 supported routes. Evidence: reports/search-categories-validation.json. Phone category results and lag remain pending; no IPA or merge. Continue one bug at a time in draft PR #8.

Previous focused owner bug **1 / ISSUE-091** (owner confirms completed copy in Google Drive / Library): Continue Watching must check completed downloads before selecting a provider, and Umbrella-origin titles must return to Umbrella. Source fix in draft PR #8 checks phone/seeding/Drive copies first, fixes the actual TMDb Helper metadata object, preserves saved provider/version, and stops failed lookups/retries or unavailable-provider substitution. Watch add-on version 1.4.2. 140 affected host tests/12 suites and three actual pinned-resolver contract checks pass; phone/Drive playback and resume position remain pending. No IPA or merge. See reports/continue-watching-validation.json and docs/BUGFIXES.md. Continue Watching device acceptance remains pending; Search and AirPlay follow-up work is described above.

Latest steering: owner also reports the bottom menu bar takes at least five seconds to appear. ISSUE-090 now starts a lightweight native UI worker before heavy setup imports and provider work; first show request precedes the first polling wait. Five host regressions pass; phone visibility timing remains unverified. Shared tab actions and one controller owner are retained.

Latest work on draft PR #8: owner selected warnings, then slow **opening Kodi until posters appear**. ISSUE-085 repairs empty generated widget unload includes; ISSUE-086 stages an iOS audio INIT acknowledgement; ISSUE-087 corrects expected schema-deferral diagnostics. ISSUE-089 (real startup audio underrun) remains open. ISSUE-088 skips redundant unchanged navigation scans (host median 0.266 s → 0.0175 s for two calls) and adds bounded startup/feed/cache timings. 361 tests in 25 host suites pass; full native patch applies to pinned Kodi source. Native r22 is staged only; executable_release still r21. No iOS SDK build, IPA, phone performance result or merge. See docs/BUGFIXES.md, docs/PERFORMANCE.md and reports/startup-followup-validation.json.

Next: retain one draft PR, get complete startup evidence through visible posters and diagnose the remaining delay/underrun. The original six-second startup log had no custom service/cache entries or first-poster timing; the newer bug-3 playback capture is recorded separately above. 0.1–0.2 s historical measurements were preloaded tab switches. Do not claim cold launch restored to that value. Keep using [skip ci] and do not build an IPA until requested.

The owner explicitly requested merging PR #7 into main without making an IPA, then opening one new draft PR for bugs handled one at a time. PR #7 is merged at `4a78efdeecbc6f9c47018682fbb60ff1829a8a95` (merge message contains `[skip ci]`). The existing build-141 was built from PR #7 head `c0d2746d76ff362bd18a9d1de30784ee375afa85` and includes KodiAirPlay r11. This supersedes the older unmerged/build-124/127 status below.

Build 142 (PR 8, commit b0d154f): unsigned IPA `Kodi-iOS-Customized-Touch-r10.ipa`, https://github.com/onlykappa/Kodi-Ios/releases/tag/build-142. Includes Drive-only downloads, strict torrent filter, Choose source/player fix, splash removal with native tab bar (r22 + KodiGlassBar r5), AirPlay r12 and the owner's Drive sign-in worker. Device test PENDING owner evidence.

Native pins (PR 8, 2026-11-05): Kodi executable r22 (native tab bar owner), KodiGlassBar r5 and KodiAirPlay r12 are published and pinned; each sha256 was checked against the downloaded release. The Kodi release call returned HTTP 403 three times although the token had contents: write, so publishing now runs as a separate short job after the macOS build. None of the three is device-verified yet.

Drive sign-in (repo review fix 1, PR 8): the app now uses the owner's own sign-in worker `https://kodi-signin.ballaking1738.workers.dev` instead of the public relay `drive.signinserver.com`. Existing installs whose setting is blank or the public relay are switched at service start (`signin_server.migrate`). If the current Drive sign-in came from the public relay, signing in to Drive again may be needed. Not yet device-verified.

Follow-up branch: `fix/build-141-followup`, targeting main in a new draft PR. See [bug-fix handoff and log observations](BUGFIXES.md). A private owner log covers only 5.795 seconds of startup: four explicit warning entries, no error/fatal entries, no playback/AirPlay activity. The initial handoff below predates the warning/startup work described above; continue diagnosing and verifying in that same PR. No new IPA or follow-up merge until requested; use `[skip ci]` while the no-build instruction applies. Raw logs and private state stay outside GitHub. Host checks do not establish device success.

## Earlier progress (historical)

Status: IN PROGRESS — owner device testing of iPhone builds
Current phase: Phase 4 — portrait UI (r11), Elementum, Drive, Play on TV, video controls, notification center; owner tests each IPA on an iPhone 16 Pro
Last updated UTC: 2026-11-02T17:10Z
main (2026-11-02 17:10Z, owner: merge the new UI to main, no IPA unless required, everything merged before the audit): main = this branch, fast-forward, no force, commit message with [skip ci] so no build ran. It holds the r20 fixes (PR #5), UI round 2 (PR #6 feature/fuse-pages + design/settings-mockups) and Search (ISSUE-082, restored). No IPA has been built from it yet. Next: the owner's audit prompt (full audit, remove overlapping old code, hard simulation, before/after score; Elementum show download still broken). Performance pass (2026-11-02 23:00Z): draft PR #7, build-127 (f145ea1) for the owner's test, docs/PERFORMANCE.md; not merged. Latest installable IPA: build-124 (draft PR #5, commit 37331e3: Kodi app r20, KodiGlassBar r2, KodiAirPlay r4; ISSUE-076..081; Search held back), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-124 — sent to the owner for the r20 test; main untouched until the owner says to merge. Before: build-122 (commit a9cfd45, Kodi app r19: taps anywhere on the landscape video reach Kodi — play/pause, forward 10, CC, AirPlay), https://github.com/onlykappa/Kodi-Ios/releases/tag/build-122 — sent to the owner for the button test. Earlier: build-120 (r18).
Branches: main (= feature/ios-migration since DEC-024; PR #1 merged), feature/ios-migration, claude/ios-migration-continue-3jjuif (this session, same commits), hold/ios-next (older mirror at f42dc07), feature/settings-notifications (draft PR #3: plan only).

## AirPlay MKV remuxer (2026-11-03, branch feature/airplay-mkv-remux)

BUILT ON HOST; device test pending (ISSUE-083). Remuxer + AAC audio bridge + HLS server in migration/airplay-ios/remux,
574 host checks pass on Linux; KodiAirPlay r5 links it (macOS CI job, not yet run). Not merged, no release, no PR.
Next: owner says whether to run CI on the branch and publish kodi-airplay-r5 for a test IPA.

Activity pill (branch feature/activity-pill, PR not merged, owner: no IPA): Kodi's background progress box (DialogExtendedProgressBar) is drawn invisible in portrait and 1080i; the service reads it (heading/text buttons 30/31, bar 32), rewrites each job (activity.py) and publishes Activity.*; the pill is the modeless Custom_1187 dialog; every portrait page carries its tap area (Kodi sends taps only to the active window); Activity sheet IOSActivity.xml; switches in the setup add-on's Activity category (Settings › Activity). Rig-checked in Kodi 21.2 with a stand-in Elementum engine.

## Where things stand (2026-11-01, night)

Working on the owner's phone (owner-confirmed):
- Portrait-only menus (Apple TV-style mockup A), fullscreen video turns landscape and back.
- Elementum in-process engine with Burst; Umbrella with CocoScrapers/AllDebrid; Google Drive sign-in (self-hosted worker, drive.file).
- Download with Elementum (season page button, long press › Download); "Choose a version" (Deck picker) for Elementum and Umbrella.

Owner-reported failures (build-104/106, 2026-11-01 night), see ISSUES:
- ISSUE-064 video: Fuse seek bar flashes at video start; taps register only on the left of the screen; controls do not respond, laggy. Seek bar and layout fixed on host; taps: UIKit window/root view left at the portrait width drops touches right of 46% — fixed in Kodi app r13 (from code reading).
- ISSUE-065 Arctic Fuse splash at start; slow start. Fixed on host.
- ISSUE-066 request: Continue Watching reuses the player and version picked first; long press › Choose source. Built on host.

Built, awaiting owner retest (none of this is device-verified):
- Startup skin-reload loop fixed (build-94); setup crash fixed (build-88).
- Touch scrolling momentum / drag routing (r5, r6); screen-size self-heal (r6).
- Landscape video fills the screen (r7); hubs scroll past the tab bar, Home/Movies/TV one preloaded window (d4bf39c).
- No skin reload on rotation; dialogs reload from the matching folder, fonts rescaled (r8).
- Notification center (47cf832); every pop-up goes to the bell, never shown (ISSUE-063, r10, build-106).

This session (2026-11-01, 20:40–22:20Z):
- Found PROGRESS.md behind the git log (stopped at 18:35Z); confirmed no branch newer than feature/ios-migration f42dc07.
- Pinned r8 (first with the zip digest by mistake: IPA runs 102/103 failed at 'Portrait executable digest mismatch'; scripts/ios_portrait.py hashes the Kodi binary inside the zip — use the hash in the release body). build-104 published.
- ISSUE-063 (bell only): Python ingest + Kodi r9, then r10 (never shows, creates the folder on a first start). r10 pinned; build-106 published.
- ISSUE-064/065/066 implemented on host; Kodi patch changed for r12 (tap logging, reload on layout width). Host tests: all 27 runnable scripts pass (test_drive_runtime needs the CI source cache).

Open / next (exact next step first):
1. DONE 22:11Z: build-107 (4be37f6: Kodi r10 + ISSUE-064/065/066 Python) published and sent to the owner.
2. DONE 23:22Z: r13 published by run 41357516449 (from 22e4349; Kodi 8574ab39…af23 from the release body) and pinned; build_tag left at r13 so no duplicate executable is published. r12 was never published (its queued run was replaced). Next: confirm the IPA run on the pin commit publishes, send the owner the link (full review build), then merge to main as the owner approved (record the decision).
2b. DONE 23:30Z: build-111 published and sent; merged to main as the owner approved (DEC-024): `git push origin e8a5bf4:main` (fast-forward from 644ce22, no force); GitHub marked PR #1 merged. IMPORTANT: every workflow triggers only on pull_request events (PR #1), so pushes no longer build anything until the workflows get push/workflow_dispatch triggers on main or a new PR is opened — first item of the cleanup.
3. Owner reviews everything at once on that build: video start (no Fuse bar), tapping anywhere on the video, controls, startup (no splash, time to Home), Continue Watching resume (no questions) and long press › Choose source, the new Settings / Accounts pages. If taps still fail, send kodi.old.log (the "Tap at …" lines).
4. Settings pages rework (owner-approved mockups, docs/design/settings-mockups.html), coded in another session on design/settings-mockups and MERGED here at the owner's request (22:35Z) for the next build: portrait Settings home + Customisation (settings_page.py), Accounts page (accounts.py, accounts_page.py) with sign-in state for Elementum, Umbrella, Google Drive, Trakt and TMDb Helper; Kodi's category pages (SettingsCategory) and add-on settings (DialogAddonSettings) in the same style. Rig-checked there in desktop Kodi 21.2 at 603x1167 (two rig bugs fixed); not device-verified. Roku: no Play on Roku receiver on this TV; AirPlay path only plays MP4/HLS. Round 2 (feature/fuse-pages, PR #6, merged 2026-11-02 at the owner's request): iOS alert/progress (DialogConfirm), text viewer, settings dialog, Add-ons, Event Log, System Info, File Manager, Umbrella's getting-ready window (umbrella_ready.py), Play on TV sheet (1080i/IOSPlayOnTV.xml; ISSUE-079 AirPlay routing kept in its send step). Checked in the Kodi 21.2 rig there; not device-verified. Not yet: Skin Settings, Hubs & Widgets (1115), add-on info, profiles, keyboard and the other shared dialogs.

Owner review of build-111/112 (23:40Z): video plays; play/pause and ±10 s still do not respond; controls laggy; one show crashed. r13 tap log disproved the window-size theory (all sizes correct, taps arrive in VideoOSD on the buttons) — see ISSUE-064. r14 (pushed): tap log no longer takes Kodi's GUI lock on the main thread (deadlock/crash candidate); builds run on pushes to main. Crash reports received: the video-start crash is a GL context race in the rotation code (ISSUE-067), fixed in Kodi app r15 — published 00:53Z and pinned (Kodi 50cab24b…fde1). Owner debug log: the OSD buttons do work; ±10 s failed on a raw 72 GB Blu-ray .m2ts from debrid (unseekable over HTTP); see ISSUE-064 follow-up. Log review fixes: ISSUE-068 (Elementum RPC after background), 069 (Umbrella double list), 070 (start-up errors), 071 (scripts by add-on id), 072 (custom windows parsed twice, Kodi app r16 building). Next: send the IPA built on the pin commit; r18 published 03:00Z (Kodi a30e92e4…3480, from 226755f: custom windows parsed once + click logging + full-screen GUI during video, ISSUE-074) and pinned; r16/r17 not pinned (Kodi hash from the release BODY), then ask for the button test (ISSUE-064); Library now lists Google Drive › Kodi Downloads with Kodi's library (ISSUE-073, ships in the next IPA); owner is testing Elementum download → Drive upload → play from Drive; owner: revoke the Trakt token exposed in the public paste, send a screenshot of the video controls, test with a normal .mkv source.

Owner log 03:45Z (pasted in chat; uploader failed, log too big): made by a build before r16, not build-120. The controls did respond (two taps on the drawn back-10 each sought −10 s; the third top-left tap stopped the video). New ISSUE-075: on the Elementum stream audio stalls 9 s after start and for seconds after each seek (large audio sync error, renderer timeouts) — the likely "lag". Exact next step: owner installs build-120 (https://github.com/onlykappa/Kodi-Ios/releases/tag/build-120), turns debug logging off, repeats the button test with an Elementum title and with a debrid/Drive file, sends kodi.log as a file (Files › On My iPhone › Kodi).

Root cause of the dead video buttons (07:00Z, ISSUE-064 follow-up 4): in landscape no tap right of the portrait width (1206 px) reaches Kodi — play/pause, forward 10, CC, AirPlay are all right of it; back and back-10 are left of it. Desktop Kodi simulation with Fuse + our controls: every button drives the player. Fix: Kodi app r19 (hit-test redirect + tap rescue from sendEvent:), published 07:12Z from 747ed40 and pinned (Kodi feb4a645…f7a4). Exact next step: when r19 is published, pin its Kodi hash from the release BODY in source-lock.json executable_release, push (fast-forward) to the three branches, DONE 07:18Z: build-122 published from the pin commit a9cfd45 and sent; owner: play/pause, CC, AirPlay, Continue Watching, then kodi.log as a file.

Owner report on build-122 (15:20Z, screenshot of Movies): tab-bar taps sometimes open Continue Watching behind it (ISSUE-076); downloads/uploads stop in the background (ISSUE-077); scrolling can be better (ISSUE-078); AirPlay connects but 0:00–0:00, no picture or sound (ISSUE-079). The owner's screenshot shows the debug overlay: debug logging is on, which itself slows scrolling. All four built in 3e851b5 (working branch only): Glass bar r2, KodiAirPlay r3 (sha256 null until published), Kodi app r20 (build_tag). Builds dispatched on the working branch 15:50Z (glassbar-ios, airplay-ios, kodi-ios-portrait). 16:30Z: owner added ISSUE-080 (download: no quality page, wants Download only / Download and watch) and ISSUE-081 (Kodi half drawn after AirPlay); both built; KodiAirPlay r4 staged, Kodi r20 build restarted with the ISSUE-081 change. Owner asked for a DRAFT PR for these bugs and to hold main until they test r20: test from the PR's build-N, merge only after their go-ahead. 16:20Z: owner added ISSUE-082 (Search like the Apple TV app); built and rig-rendered. All pinned on this branch: KodiGlassBar r3 (863dd6ef…), KodiAirPlay r4 (93739a92…), Kodi app r20 (47b98c8e…, from 6e52968, Kodi hash from the release body and checked in the zip). All tests pass. Draft PR opened from this branch to main; its import-review run publishes the test build-N. main untouched until the owner has tested r20 and says to merge. Earlier plan (done): when each release exists, pin glassbar-ios and airplay-ios sha256 from their release notes and executable_release r20 with the Kodi hash from the release BODY; run the tests (test_glassbar needs the bar pinned); push the pins to this branch and open the draft PR (claude/ios-migration-continue-3jjuif → main); its import-review run publishes build-N; send it with the test: tab bar near misses, download with Kodi in the background, vertical scroll on Home and the hero, Play on TV › AirPlay with an MKV (mirroring steps) — debug logging off.

Blockers: device verification needs the owner (review of build-111). Merge to main authorized and done (DEC-024); release and Phase 5 still need the owner's go-ahead.

Next after the owner's review: repository cleanup (version names such as 1.0 / Beta instead of rN, plainly named workflows and component releases, README, stale branches deleted only after the owner confirms the list) and a roadmap rework from version 1.

Verification method: unit tests (scripts/test_*.py), desktop Kodi 21.3 rig at the phone's portrait (603x1167) and landscape (19.5:9) shapes (not available in this session: the new layouts are not rig-rendered), IPA download checks (zip integrity, Kodi binary equal to the pinned executable apart from the code signature), owner device tests. Nothing is called device-verified without the owner's evidence.

## Resume instructions

Read ROADMAP.md, this file, ISSUES.md and DECISIONS.md. Check branch/worktree and latest commits, inspect PR #1 and approval evidence. Recompute completed task IDs. Phase 1 passed owner review and Phase 2 is explicitly authorized. Phase 2 review passed and Phase 3 authorized. P3-001 through P3-006 are complete for their documented host/static scope. Architecture and capped CI approvals are recorded in DEC-011/012. Phase 3 has now passed independent review and the owner authorized Phase 4. Follow dependency order and never mark device tests passed without owner evidence. Owner waives sideloader identity for unsigned preparation. Verify prerequisites rather than trusting prior messages. Follow the roadmap workflow and record failures, evidence, decisions and end-of-session state. Keep source and SSD read-only and private data outside Git.

## Stop gate

Phase 4 BLOCKED: no device or full migration completion claimed. Available host candidate/evidence submitted for owner review. Continue authorized independent Phase 4 preparation; customized-device evidence remains required. No Phase 5, merge or release authorized.

Publication uses the GitHub connector because this shell has no authenticated GitHub CLI/network path. Local and remote commit IDs can differ for identical trees; preserve both histories. Verify remote branch SHA and tree before publication; never force-push or reset history. Resolve latest published SHA from PR #1 and record it in the next session.

Deployment objective: unsigned Kodi iOS IPA based on trusted compatible upstream build, with only compatible sanitized customizations. Phase 2 investigates bundling/import feasibility; Phase 4 assembles, validates and signs/installs with owner sideloader. Account state, secrets and media remain external. Static structure checks cannot prove sideloader/device compatibility.

Proposed alternate test executor: docs/proposed-drive-test-workflow.md. Published and executed with owner approval; CI run 40940315803 passed. Owner has now approved publishing the exact capped workflow. Actual job logs have been inspected; no iPhone success is implied.

## Owner-requested pause — 2026-10-30T14:02:35.605625+00:00

PAUSED at owner explicit request. Stop implementation/publication until resumed. Latest repair code is pushed: local 8363797 / remote 91ed4dd79d5637f57f2ae03fadc6cee4171fca06. GitHub Actions run 41068166024 continues independently as explained to owner; final artifact/result/checksum NOT YET retrieved or claimed. https://github.com/onlykappa/Kodi-Ios/actions/runs/41068166024 . On resume inspect that run/jobs/logs/artifacts, diagnose failures if any, verify the revised Touch-r1 IPA, and record/publish final evidence and link. Host tests: 165/20 suites (new live-setting readback regression passed). Original IPA retained; prior device failure remains unresolved until owner retest. No further feature development, Phase 5 or merge. This pause note is local/uncommitted to avoid starting another build.

## Resume after owner pause — 2026-10-30T14:24:00.732908+00:00

Owner explicitly resumed. Inspected run 41068166024: SUCCESS; revised artifact 12983492116 uploaded and not expired. Actual IPA checksum recorded in reports/ios-touch-r1-artifact.json. Prior pause above is historical and no longer active. Stop at Phase 4 device-test boundary after publishing evidence; do not infer the prior navigation failure is fixed on the phone.

## Test delivery build tracker

PR #8 merged at `2a8bb1cb16dfa0984f7a1b3d974e20857c0f6d3c`. Native r23 source: `d13ec87c3db61a1667de0023450a8acc1f4d033b`; [native run 42078285510](https://github.com/onlykappa/Kodi-Ios/actions/runs/42078285510) queued/running. The pin intentionally remains r22 until the native output is verified; no intermediate IPA job was started. Resume by inspecting this run and reports/ipa-test-delivery.json, verify/pin r23, then build and verify the test IPA. Owner authorizes this delivery; device results still pending.

## Mockup roadmap opened — 2026-11-12

PR #21 merged (build-314: Kodi r31, AirPlay r50). The owner approved the Library file manager mockup (DEC-043, round 3
buttons) and asked for the work to be planned before coding: ROADMAP.md "Mockup roadmap" (L1-L8 Library, V1-V3
Picture menu, Saturation, AI Upscale show page). No code yet; the owner says when to start. Owner logs from
build-314 (Build Season, copy speed, AI Upscale tiles) are awaited.

## Integration checkpoint — 2026-11-16

Combined source 38dad1e is pushed on PR #43. Native candidate run 43907784636 tests and builds that source, including r64 subtitle changes and PR #44's separate six-second converted timeline. No IPA has been built yet. The ordinary import CI caught a portrait patch digest mismatch: PR #44 adds an optional first-frame logging marker, but the approved r33 executable was built without that marker. The testing branch now retains the exact r33 patch and pin together; the marker remains in main for a future Kodi executable build. This does not remove the Drive admission or native AirPlay playback fixes; first-picture timing remains explicitly unmeasured. test_smooth_pages passes after restoring that consistency.

Native candidate pending; after it passes, verify the archive, publish/pin r65, run the full IPA workflow once. A redundant old-tag AirPlay build was canceled; the candidate build remains running. New playback regressions are now added to import CI. Desktop Kodi 21.3 rig initially crashed while starting many third-party Python services; services were isolated in the private rig, not in shipped code. Rig playback/scroll validation remains in progress and is not a phone result.

Follow-up evidence: combined-source loopback index benchmark cold median 0.4022 → 0.2019 s, warm 0.00110 → 0.00110 s (five trials, synthetic 200-ms metadata; not device measurements). Sports regressions include actual process-lock contention and release after collection failure. The Loop installer exits when its installed dependencies are present; this change does not reinstall JetExtractors or overwrite the owner's whitelist patch. Desktop rig startup recovered after isolating private third-party services, but a skin reload closed the sports window and subsequent skeleton/first-run dialogs prevented a useful scrolling measurement. No desktop frame-rate or live-provider playback claim. Full import-suite rerun continues; stale local provider fixtures were replaced with the current lock's verified archives.

Full local import/packaging validation: 170 suites, 2482 tests run; every suite passes. Native host job 133441177291 in candidate run 43907784636 passes. Apple framework compilation remains queued. Evidence: reports/sports-playback-validation.json.

Native infrastructure failure retained: candidate run 43907784636 passed host tests but GitHub canceled its unassigned macos-15 ARM64 compile after 15 minutes: "The job was not acquired by Runner of type hosted even after multiple attempts"; annotations report ARM64 capacity constraints. Retry compilation on the documented macos-15-intel image (Xcode 26 available). A manual reuse_host_run option verifies the earlier host job succeeded and the entire migration/airplay-ios Git tree is identical before allowing the compile; default PR runs still execute the full host suite. This reuses evidence, not an older binary.

Native compile checkpoint: candidate **43911296606** succeeds on Intel, including five real Foundation transport fault tests. Xcode 26.3 / iPhoneOS SDK 26.2 produced r65 archive SHA **05ef394f931b321dda54e0c8378e6420c912d4cf525602bb70529d8c864acf7a**, read from its successful compiler log. The workspace cannot download the Actions artifact's Azure URL (Forbidden); the existing verified-candidate publisher will validate SHA/ZIP/exports inside GitHub before immutable publication. Local public-release download and binary/CRC inspection are required before the IPA workflow. r65 pin prepared; publication and IPA pending.

Ready-to-package checkpoint: **AirPlay r65 published** by verified-candidate run **43912960249**. The public 4,083,768-byte ZIP was downloaded locally: SHA **05ef394f…acf7a**, ZIP CRC, thin arm64 Mach-O, required exported API and six-second converted-timeline/shared-wait markers pass. Binary SHA **7b2f4692aa8fc56a711156180d69908fc911461f5af23ae89ad6f3971888053c** retained for IPA comparison. Owner-approved manual import-review/IPA build is next, with r33 Kodi and r6 bar pins preserved. PR #44 is merged; PR #43 remains open. Actual phone playback/scrolling/AirPlay results pending.

AirPlay position follow-up (ISSUE-377): build 578's stalled recovery produced an unready, empty player at zero before close, so the existing handoff could not return Kodi to the last TV position. A guarded candidate retains the last usable TV sample through that specific state and seeks only the same Kodi file on the same ended native generation. Controlled regression tests pass; phone behavior and watch-history persistence need device validation. Startup latency and buffering remain under investigation; no new IPA is authorized by this change.

AirPlay step 1 (ISSUE-378): a registered loopback HTTP fixture now reproduces rejected ranges, retries, slow inspection and two waiting media readers through the production cache. The fixture intentionally disables speculative prefetch and does not play video; its timings are controlled baselines rather than phone measurements. Step 2 is to investigate and test a source-read repair against these cases and production read-ahead.

AirPlay step 2 source candidate (ISSUE-378): a refused parallel range now reaches the existing constrained single-connection fallback without three attempts per split piece. Controlled tests include a concurrency-limited source, a source that refuses the fallback too, and production read-ahead with healthy fast/slow and rejected-range sources. The concurrency-limited case improved in one run; the fallback-refusal case did not. Relevant suites and project check pass; two optional slowdown-suite text checks already disagree with committed service code. This is a narrow cache change, not proof of reliable video startup or iPhone buffering performance.

AirPlay step 3 investigation (ISSUE-379): Apple's HLS authoring specification limits H.264 to High Profile or below while allowing HEVC Main 10; the owner's source is H.264 High 10. Existing native host tests from successful job 133441177291 exercised synthetic High 10 conversion and HEVC copying, with native source matching this branch. They are not receiver tests. Retain automatic conversion; no safe receiver-specific direct playback or fallback is proven, and no new IPA was requested. Exact Apple TV behavior remains open.

AirPlay step 4 candidate (ISSUE-380): stall recovery previously played a replacement item before seeking to the saved stall position; the owner's log subsequently shows an earlier media segment requested. The source now waits for an owned successful seek before play, blocks repeated recoveries while waiting and bounds that wait. Source-wiring checks and shell syntax pass; actual AVPlayer behavior and native compilation remain unverified. The pinned r65 framework and existing IPA do not contain this change.

AirPlay step 5 candidate (ISSUE-377): the latest trustworthy final player snapshot is saved before same-file handoff; a confirmed rewind to zero is preserved, and a different Kodi file cannot inherit the old AirPlay position. The independent native-close log path now checks the original file fingerprint. Real local-history tests cover final position, completion and replacement alongside controlled rewind/stall tests. iPhone, Kodi library and provider-specific resume remain unverified. Step 4's GitHub host job passed, but the framework runner was not acquired and the failed job was retried; check run 44343640378 for status. No IPA is authorized.

AirPlay step 6 validation: native run 44343640378 succeeded on retry, including host tests and iPhone framework compilation for `95bb0d2`; this did not publish or pin a framework. Import CI on `369bab3` exposed a real step-2 fallback regression after prolonged range refusal. ISSUE-378 records the bounded retry repair and local retests; the full workflow is being rerun. Existing AirPlay IPA and r65 binary do not contain the native stall-recovery change. Device tests and a separately authorized testing build remain open.

AirPlay step 6 results: import CI run 44358013453 passed on `3bb8bf5`. A separate local run of all 180 then-registered workflow test commands passed 179 initially; `test_customized_ipa.py` failed because the host lacked CPython 3.11, then passed all 14 cases with a task-local CPython 3.11.18. All 26 separately run slowdown tests pass and are now registered in CI. The native host tests and candidate compile passed, but GitHub's temporary artifact download returned Forbidden, so independent binary inspection remains open. Synthetic long-fragment host audio generated 27 segments without failure; deliberately injected EOF produced an empty segment that recovered on retry. This does not reproduce the owner's original audio issue or establish iPhone playback, buffering, stall recovery or resume. No framework release, new IPA or merge is authorized.

AirPlay TV handoff step 2 (ISSUE-393, 2026-11-20): `receiver_prepare()` prepares the third-party receiver's converted init and resume-position unit (video, and converted audio with a converted plan) through the converted plan's own grid when its master request arrives; the obsolete converted-segment-0 queue is removed (a zero start still gets segment 0); an init request now schedules after the resume segment. The step1 expected-red wrapper is a normal regression gate (`--receiver-handoff`, also in the full native run). Python AirPlay suites pass locally; the native gate has not yet run. Host evidence only: no AVPlayer, TV or phone result, no framework, IPA or merge.

AirPlay build611 seek/empty-segment log (ISSUE-393, 2026-11-20): the seek-restart cause is a stall reload at the player's stale clock; the server now keeps the receiver's latest jump and the reload resumes there with EXT-X-START (`kr_remux_recent_seek_target`, `kr_remux_set_resume`). The "empty segment" stop (stream 2 window after a jump, two packets, no I/O) gets one fresh audio reader with both attempts logged; its root cause is unproven. Native test `test_seek_target_and_empty_window` added; not yet run. Host evidence only.

AirPlay r69 candidate (ISSUE-393, 2026-11-20): native full run 44672682972 on 82bebbb passed host (3966+ checks incl. receiver handoff, seek target and empty-window tests), end-to-end and iPhone framework jobs; inspection 44674563427 verified IOS 14.0/SDK 26.2 and required exports. Archive SHA256 abcc6bc16c32c3fc3bb3644002ae42245ce38cd1e38ea6852641ee7d98e2b5e8, binary SHA256 6efa3c5e0338cee0d07e512e55cc0b780eabc4e99caed67c1932230abd65c785. Owner authorized publication of r69 and one combined testing IPA with the Sports fixes; PR50 stays draft and nothing is merged to main. Host evidence only; the phone/TV result is not established.

AirPlay r69 published and combined testing IPA (2026-11-20, owner-authorized): release kodi-airplay-r69 (publish run 44675687847 after a first run, 44675178398, was refused HTTP 403 creating the tag on a commit with workflow changes; the ISSUE-332 default-branch fallback and an asset re-verify were added). Asset sha256 abcc6bc16c32c3fc3bb3644002ae42245ce38cd1e38ea6852641ee7d98e2b5e8 matches the pin. Combined IPA: import run 44676131375 (build 612, branch claude/airplay-sports-combined at 2bbd629 = AirPlay branch + main + claude/sports-redesign), IPA sha256 0c9d4359cbe6fd3d713369905f5c19a210399850554bd1e451974b21a89603bb, release https://github.com/onlykappa/Kodi-Ios/releases/tag/build-612. PR50 stays draft; nothing was merged to main. Phone/TV results are not yet established.
