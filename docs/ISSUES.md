# Issue register

No existing failure is erased; preserve failed attempts and append evidence on resolution.

ISSUE-001 to ISSUE-138 are in [ISSUES-ARCHIVE.md](ISSUES-ARCHIVE.md), unchanged.

## ISSUE-139 — Build 213: Drive startup stalls and false slow-internet diagnosis (2026-11-09)

Status: REPAIRED TEST CANDIDATE DELIVERED in build 214 with r42. Native CI 42639212562 and IPA CI 42641842437 passed; downloaded artifact verified. Actual iPhone/Roku acceptance remains pending. Owner authorizes repairs and a new test
build in the current request. Keep the existing Drive library and file identities; no required local download.

The private build-213 log (two movies, Media Assistant and AirPlay) provides concrete failures:

- Media Assistant's tiny audio/video init responses took 17.5/26.0 seconds for one movie and 23.0/45.3 seconds for
  the other. The log attributes the delay to waiting for a production lane, with zero production in the request.
  `get_part` took the segment lane and `make_part` generated the whole first segment before splitting its init.
- A prepared-file request for 128 KiB waited 18.3 seconds while warming the first 8 MiB held the same 4 MiB cache
  lock. Cached prefixes could not bypass warming, and a partial block was marked present without a refill path.
- Separate video/audio/subtitle sources fetched/probed the same Drive bytes independently. The converted-video
  path records actual source I/O of 12.7–13.8 seconds; queue waits alone do not identify its cause or Wi-Fi speed.
- A subtitle response took 43 seconds. The existing 1.5-second limit covered only waiting for its mutex;
  opening/probing/reading afterward had no whole-request deadline.
- The slow-source classifier treated any five-second lane wait or near-empty canceled HTTP response as slow
  internet. A successful playlist fetch also counted as playing before any video media had reached the TV.
- The initial resume timer and compatibility restart both sought on a replacement item (requested position versus
  0.0 seconds). Prepared-file delivery counters were updated only after an entire long range finished.
- Roku was launched before the asynchronous first-segment producer finished, leaving its own timeout to absorb
  the Drive startup delay. A launch acknowledgement also stopped Kodi and reported success immediately.

Repair:

1. Per-movie shared byte cache (128 KiB blocks, 128 MiB maximum, first block retained), with independent cursors,
   cancellation and connections. Duplicate in-flight reads share a fill; cached prefixes bypass missing-block I/O.
   Cache locks never span network reads. Partial blocks extend on demand; premature EOF reconnects at the missing
   offset within one timeout budget. The cache is released with the session, never shared across movie versions.
2. Copy-track init headers are built from probed codec metadata before producers start. Converted-video headers
   publish after the first encoded packet; an init waiter can take them while the full media producer continues.
   AC-3/E-AC-3 retain their first-packet parser path when their codec configuration cannot be synthesized safely.
3. Prepared reads request only the needed bytes, share the source cache, and use one kept-open foreground cursor.
   Warming uses another cursor and at most 1 MiB, so it cannot own the foreground connection or a 4 MiB lock.
4. Before launching Roku, buffer the first video and default audio segment. Native segmented AirPlay and its
   compatibility restart buffer the actual requested resume segment. Preparation remains bounded and cancelable;
   subsequent segments use existing prefetch. Compatible 4K HEVC is copied by the Roku path.
5. Optional subtitle opening, probing, reading and lane waiting share a 1.5-second deadline. An expired demuxer is
   retired; media lanes continue, and later cues can retry using the session cache.
6. Network snapshots distinguish TV requests, delivered media and delivered video. Playlists and audio alone
   remain connecting. Prepared-video counters update during delivery. Media Assistant waits for video before
   stopping Kodi; failure restores playback and never launches a known-unavailable phone stream.
7. Slow-source classification requires measured source I/O. The card reports a movie-loading timeout, without
   asserting slow internet or recommending local files. One timer owns the replacement item's resume seek. Kodi pauses its own playback before buffering a TV
   handoff and resumes it on failure/cancel; background work slows from the start of buffering.

Regression protection: native shared-read/stall/cancellation/partial-refill and no-media-read init tests; real
converted init callback timing; startup priming at a resume position; bounded distant subtitle request; existing
packet/frame/timestamp/seek/shutdown suite. Python regressions cover playlist/audio-only false readiness, launch
monitor bounds, and queue/cancellation false source diagnoses. Full validation and build receipts are recorded in
PROGRESS when completed. An early local harness run hit a shell parse error because its script changed while it was
running; rerun from stable files is required. The first new startup test also omitted the session token prefix and
received HTTP 404; its request setup was corrected before retesting. Neither is device evidence. The full host run then exposed a 167 ms copy/converted timestamp mismatch in
metadata-only init headers (the normal delayed header carries a decode-lead edit list) and incorrect buffered HTTP
seeks after opening a clone at a nonzero offset (the protocol and AVIO cursors started at different positions).
Added the matching metadata-derived edit list and synchronized the AVIO cursor; regression tests retain both
cases. Early init also exposed an FLV rewind failure after canceling the initial segment: a failed seek to zero left
no frames. The converter now reopens once for an empty rewind and uses its buffered beginning. The targeted
streaming regression passes 117 checks, including all these failures; the expanded source and startup sets pass
39 and 13 checks. Full-suite and iPhoneOS candidate validation still must pass before framework publication.

Recommendations and acceptance steps: docs/ROKU-STREAMING.md. Device startup, sustained playback, sound, HDR and
forward/backward seeks remain unverified until the owner tests the resulting IPA. The log proves contact with the
TV; it cannot establish a Wi-Fi throughput problem. Main is unchanged.


ISSUE-139 follow-up found during final review: a generated 32-second movie with a 30-second GOP advertised six
six-second windows, but segment 0 carried about 30 seconds and later requests repeated the same tail. The prepared
file's fragment lengths in the owner log do not by themselves prove its GOP structure, but the existing source
path cannot safely assume a short keyframe interval. For indexed MP4s, Roku now takes real random-access boundaries
from the complete mfra index; video and audio use the same truthful plan. Old long-GOP files retain longer windows
and their original 4K picture. The output and byte caches are bounded at 128 MiB each to retain an old prepared
unit without discarding it before launch. Copy demuxers discard other tracks to avoid duplicate 4K reads for audio.
Newly converted video uses two-second encoder keyframes with the existing preparation workflow, resolution
and HDR policy. This does not require downloading/replacing old Drive movies to use the repaired route.
The long-GOP regression decodes the complete picture and checks every frame once, plus the audio timeline.

The first long-GOP test used FFmpeg's raw empty-moov output, whose zero init duration hid the final two seconds;
the fixture now carries the finite init duration written by the real preparation path. The corrected regression
passes all 141 streaming checks. The older r32 assertion requiring only 1–3 large fragments in a 65-second file
was updated to require about eleven six-second fragments, with its sample-interleaving check retained.


Final-candidate run 42635055257 passed 3,223 native checks and the iPhoneOS compile but failed one E2E performance
budget: a saved 65-second-style short-fragment layout caused 226 sequential Kodi range requests for long_big.mkv
(limit 60). Restored the established coalesced/interleaved saved-file layout; Roku still uses truthful random-access
windows, and new video encodes retain frequent keyframes. This preserves the r32 efficiency requirement instead
of accepting more Drive requests. The earlier fragment-count assertion is restored with the saved-file layout.
Local non-assembly FFmpeg also exceeded the 4.5-second HDR-cancellation timing budget in repeated runs; CI's
accelerated host build passed that check. Further tracing isolates the delay to the first synchronous HDR color conversion (6–7 seconds), including with
input on tmpfs; cleanup itself completes within milliseconds. This local FFmpeg was built with `--disable-x86asm`.
The cancellation callback cannot interrupt an in-progress scaler call. The native close API remains asynchronous,
but actual iPhone HDR/cancellation timing still needs device evidence. Added the native demuxer's interrupt callback so its own parse/seek loops
observe cancellation too; device timing remains unverified. Do not report the slow local timing run as passing.

Final retest: source 0385902, native run 42639212562 passed 3,231 checks and the E2E conversion/resume suite.
Sequential playback now uses 39 requests (budget 60). The verified r42 pin is recorded in source-lock.json and
reports/roku-streaming-repair-native.json. The local software-HDR timing limitation remains explicitly recorded;
SDR cancellation passed 20/20, and accelerated CI passed its cancellation check. Device acceptance is still open.

Delivery retest: build 214 (IPA run 42641842437) passed the app tests and full packaging. The downloaded IPA's
SHA256 is 7decfff5fa03b593844e940d02f7e5e7a3ba4e4d28814ddaf7dc220cba44ad46; its r42 framework, casting Python
sources/3.11 bytecode and 154 unsigned, unencrypted ARM64 images were verified. Receipt:
reports/roku-drive-test-delivery-r42.json. The owner must still check real TV startup, sustained picture/sound and
seeks. This delivery does not mark device behavior as passing.


## ISSUE-140 — Build 214: coalesced fragments, partial delivery and missing captions (2026-11-09)

Status: owner's device retest failed; host repair candidate implemented, native CI and new test IPA pending.
The latest owner-provided log identifies build 214/r42. Media Assistant takes the link and Roku reads both
playlists and both init headers immediately; Wi-Fi discovery/connection succeeded. Its segment responses then
show cancellations and zero-byte totals. Those totals are unreliable: `respond` recorded bytes/counters only
when the entire body finished, so a canceled large response erased its delivered prefix. They do not establish
zero network transfer or establish a decoded picture. Apple TV's subsequent native AirPlay requests are visible;
this log does not establish a successful attempt through Roku's built-in AirPlay receiver.

Root causes and repairs:

- The prepared writer coalesces several GOPs into large storage fragments. The r42 plan used only each fragment's
  first indexed sample, so even frequent-keyframe movies became 30–70-second HLS segments. A bounded four-cursor
  metadata scan now reads moof sample durations/flags/CTS offsets, gathers the complete keyframe timeline and
  chooses actual boundaries around six seconds. It leaves the saved file, Drive workflow, resolution and encoded
  picture alone. Invalid metadata falls back without publishing a partial plan; true long GOPs still need longer
  windows. The saved-file fragment layout stays coalesced for efficient normal Kodi playback.
- Segment sends now report actual partial bytes and media progress while writing, preserving cancellation evidence.
  Headers, HEAD and one-byte range probes do not count as delivered picture. Optional Roku ECP feedback adds actual
  play/buffering/error state when available. Unsupported feedback remains optional. Model and playback logs contain
  an explicit safe field list, excluding media URLs, serials, MACs and account state.
- Caption requests used the video seek index, read every stream, then filtered packets. The 1.5-second deadline
  repeatedly produced eight-byte empty WebVTT responses. The dedicated caption demuxer now discards video/audio
  before reading and seeks its own subtitle index. If a backward seek before the first indexed cue fails, a forward
  seek recovers that cue instead of retaining the probe's later buffered position. This keeps overlap cues and
  forward/backward caption seeks. Media Assistant also receives Kodi's current subtitle choice; its master now
  marks that text rendition as default. Roku's caption visibility setting still applies.

Research: Roku's streaming/closed-caption/ECP specifications, Media Assistant's published deeplink parameters,
Home Assistant's Roku media path and KSPlayer's AirPlay picker were reviewed. The existing AVPlayer/AVRoutePicker
approach matches those native AirPlay patterns. No third-party player/UI code was imported. Receiver projects are
not drop-in sender/packaging repairs; the concrete fixes above address the observed sender failures.

Regression protection: a private generated 32-second, constant-bitrate MP4 has coalesced storage, internal two-second
GOPs and text captions. Before changes: 46 checks, four failures (oversized HLS window, missing partial delivery,
zero-byte cancellation log and lost captions). After changes plus selection, seek and malformed-header checks:
102 checks, zero failed. The copied movie decodes every one of 768 frames exactly once. Additional local checks:
141 streaming, 13 startup and 142 Python checks passed. The initial caption test used a master-only path helper and
was corrected to strip either playlist filename before confirming the real deadline failure. The first code compile
needed a forward declaration for the moved sender helper. A mistakenly named Python test path was corrected to
`test_play_on_tv_start.py`. The first project scan rejected the two new native source files; their exact paths are
now allowlisted, retaining all other scanner rules. These setup failures are not hidden as passing device tests.

Receipt: reports/roku-build214-retest.json. Native CI/new IPA and real phone/Roku acceptance remain pending.

Additional regression finding (synthetic evidence, not inferred from the owner's raw movie): a B-frame fixture
using signed composition offsets initially returned HTTP 500 for later segments. FFmpeg 8.1.1's `mov_read_trun`
read version-1 offsets as unsigned during MFRA-to-DTS arithmetic. The shipped LGPL patch sign-extends these offsets
and prefers explicit TFDT for actual sample decode timestamps, retaining MFRA for fragment lookup. The first local
patch rebuild needed a PRId64 string correction; the final patch reverse dry-run passed. A remaining first-cue
presentation offset was corrected to one stream-wide offset instead of re-anchoring each fragment to TFRA. Finally,
the container average rate made decode ladders overlap and MOV marked opening keyframes as discard; the nominal
rate selected by `av_guess_frame_rate` keeps those boundaries monotonic. The expanded 102-check suite now decodes
all 768 B-frames as well as the original 768-frame fixture exactly once, with no failed segment requests. Existing
static tests were updated for the selected-subtitle master and functional native caption-seek coverage.


## ISSUE-141 — Touch seeking and apparent download stalls, build 214 (2026-11-09)

Owner supplies a new private log and the player-bar screenshot. The supplied log ends during Settings/Library
navigation; it does not record the actual playback/drag gesture. The native slider bug was established from
Kodi 21.3 source and a compiled handler harness, not inferred as a measured device frame rate.

Touch root cause: GUISliderControl's mouse-drag branch marks `m_dragging`, but the touch gesture branch did not.
Consequently every PAN ran the seek action and Process kept replacing the thumb with Player.Progress. The native
patch marks touch BEGIN/PAN as dragging, commits the seek once on END, and restores playback progress after ABORT.
A compiled harness using the actual handler reproduced failure before the patch and passed after it: 100 PAN
moves, no intermediate seek, one seek on release, cancellation and mouse-click behavior. The patch applies cleanly
to the pinned upstream slider source. Actual iPhone touch smoothness and a new native build remain unverified.
No player layout or artwork changes are made.

Download evidence: AllDebrid-to-phone reads varied from about 1.1–11.9 seconds per 32 MiB; Google Drive PUTs took
about 8.3–31.4 seconds. HTTP 308 means Drive accepted a resumable-upload piece, not a failed download. Progress
updated only after a whole 32 MiB upload, so the bar stayed still for those intervals. The streamer now uses at
most 8 MiB per piece, preserving the existing one-piece read-ahead and resume checks. A bytearray avoids repeated
copying of an ever-growing immutable buffer. Source reads check cancellation between 1 MiB reads.

A second confirmed bug put the playback throttle before processing successful upload responses. An upload that
had already finished could wait through playback before being marked done. Confirmed offsets and final success
are now processed before throttling the next piece, for both streamed and local uploads. Existing intentional
playback pauses and buffering protection remain; this is not a claim that real network slowdowns disappeared.

Validation: 22 AllDebrid/streaming tests, 23 upload tests and two HTTP-piece tests passed, including resumed bytes,
8 MiB progress checkpoints, progress-before-throttle and no throttle after completed upload. The first new test
run lacked the mock patch import, now corrected. A patch-check command initially used a not-yet-created working
directory; rerunning after creating it passed. Raw logs/media stay outside Git. Actual-device retest is pending.

An owner-attached episode can be used as a private rig fixture for decode, timeline and seeking tests. Keep it
outside Git, use its existing path in the rig and compare with synthetic fixtures. Desktop rig results cannot
establish iPhone gesture dispatch, networking or background behavior. No episode was attached in this turn.


ISSUE-141 follow-up: the public 4K movie host check passed startup, five seek requests and four first-frame decodes.
The first run could not connect because its private HTTP stand-in had stopped; restarting that stand-in resolved
the harness failure. No desktop app is claimed: release/artifact inspection found no compatible Linux rig binary.
See reports/public-movie-seek-check.json. The native CI host job remains in package installation, so its full suite
and new IPA are not represented as passed. No additional desktop Kodi build was started after the owner asked to
reuse the branch version.


## ISSUE-142 — Owner-approved streaming recommendations and test IPA (2026-11-09)

Owner explicitly requests adding the recommended capability checks, buffering/cancellation, adaptive chunks,
clear transfer stages and seek diagnostics to this IPA and pushing it. Main merge is not authorized. Native r25
includes the prior touch seek fix plus gesture duration/submission timing and elapsed video-flush-to-first-decoded
picture queued to the renderer. The latter is queue readiness, not a measured display-vsync event. Host handler
checks and pinned-file patch application passed; native build and device acceptance follow. Other recommendations
are in progress. UI policy and its project skill were read before changing visible stages; reuse existing layouts.
The first diagnostic patch-write helper ran from the fixture directory with a relative repository path; rerunning
with the absolute repository root passed.

The preceding native run 42685265901 passed the framework compile but failed one of 3,307 host checks: the signed-CTS
B-frame fixture decoded 769 frames instead of the local expected 768. Investigate source fixture frame count and
packet preservation before accepting any candidate; do not relabel that run as a full pass.


ISSUE-142 implementation: explicit HD-only Roku capabilities start in H.264 SDR/AAC stereo mode; unknown
capabilities preserve the existing route. A connected receiver failure gets one compatibility retry, preserving
phone pause ownership. Native buffering uses a bounded 12–18 s target and cancels obsolete copied-video reads
on seek, then clears interrupted demux read state before reuse. Upload chunks adapt at 256 KiB boundaries within
1–8 MiB, retaining one-piece read-ahead and Drive-confirmed resumability. Existing transfer rows name the active
read/upload/hold stage. A regression test ensures playback labels never hide a real scheduled network retry.

Fixture diagnosis: FFmpeg versions can duplicate a frame under the default output cadence when transcoding
negative-composition-offset input. The fixture now explicitly passes timestamps through. The assertion compares
all decoded output frames with actual input frames and the ordered compressed video packet digest, rather than
a local hardcoded frame count. The digest helper reports track count (not frame count); an initial new comparison
mistakenly compared the three-track source with the video-only output, corrected before commit. Focused tests
now pass 103 checks, including signed CTS. Recommendation checks pass 37 checks, including actual stereo audio,
retaining compatible 4K HEVC and successful decoding after canceling an old copied read. Full native CI is required.

Python checks pass: casting 61, direct transfer 24, upload 23, status 26, remux contract 29, calibration 41 and
portrait 50. UI guidance/project scans pass. The patch checker initially flagged whitespace-only unified-diff
context; preserving valid empty context lines fixed it, and pinned upstream patch application passes. Existing
rig start fails because the desktop Kodi binary is absent; visual and iPhone/Roku acceptance remain pending.


ISSUE-142 follow-up checks: slow-source latency passed 46 checks; prefetched segments returned in 4.3/1.8 ms.
Casting now passes 62 tests with additional failed/canceled fallback, HD-only capability and already-paused-phone
cases. Compatibility preparation itself is inside the exception handler so an interrupted retry also restores
phone playback. A CLI artifact download was rejected by the artifact storage endpoint; the GitHub connector
successfully fetched the same candidate archive, which was downloaded and SHA256 checked locally. No release
pin is accepted until the full native suite passes.


ISSUE-142 full candidate run 42694006257: framework compilation passed; host suite failed 3 of 3,319 checks
(all one legacy prepared-file test), so no framework release or IPA was published from it. The synthetic DoVi
fixture has HEVC level 255. The new documented Roku codec limit correctly requires conversion, while the old test
required copy mode and had restored the unavailable host H.264 encoder. Update that test to require conversion
for this invalid-level fixture, retaining packet-copy assertions for the compatible sources including 4K HEVC,
and use the same MPEG4 host reference encoder as other conversion tests. Full native retest follows.
The public 4K H.264 test produced valid 1080p seek output and three decoded samples, but cold Linux software
conversion took 31–133 s, which fails real-time performance. This is retained in its report; iPhone hardware
conversion and actual Roku/caption acceptance remain pending.

The precommit scanner blocked a generated Python bytecode file from the private native-artifact inspection
(import run without `-B`). Removed that generated file, reran with bytecode disabled, and rescanned before commit.
No binary, media or private account data was committed.


Packaging checks: the initial customized-IPA unit run failed its Python 3.11 bytecode check because only 3.12 was
installed locally. Installed an isolated managed Python 3.11 under private scratch storage; all 11 customized-IPA
checks then passed, alongside 7 unsigned-IPA and 11 foundation checks. No packaging requirement was relaxed.
The corrected candidate is run 42695837108 from source 0a5ad576ad757233384532186a105a096a8517fc; its framework
compile passes and full host/E2E checks remain pending at this checkpoint.

Follow-up status regression: a resumed transfer used its last pre-pause byte acknowledgement to calculate silence,
briefly labeling the playback hold as a network delay. Status now uses the latest explicit phase transition for
that timer while retaining Drive-confirmed percentage; 27 state tests pass, including a real subsequent stall.
The glass-bar contract test also matched a literal space on an otherwise blank patch context line. Aligning it
with the whitespace-clean native patch retains the surrounding frame-loop code assertion and updates verified
r25/previous-r24 release expectations; no native behavior change is required.


ISSUE-142 verified candidate: run 42695837108 from 0a5ad576ad757233384532186a105a096a8517fc passed all 3,319 host
checks, end-to-end conversion/interruption/resume/expired-session/slow-source checks (zero failures), and the
ARM64 iPhoneOS compile. Its candidate archive SHA256 is c1562e136d42d3fe694435b6175bfdac600a08bcdd450946e9e227210d243be8.
The r25 executable was separately built, released, hash checked and compared exactly with its CI artifact.
Publication and IPA packaging are authorized by the owner; actual phone/Roku/visual acceptance remains pending.


ISSUE-142 packaging failure: run 42697763579 (build 215) passed app regression tests and bundle apply/restore,
then stopped fetching the portrait executable. The new r25 pin mistakenly used the release ZIP hash; the existing
fetch contract checks the extracted executable hash. Corrected `executable_release.sha256` to verified binary
c3f0560c3731f53408a9e7c202b7108ef472272e72c873042e7b400bc1c79e2c and retained the archive digest separately
as `archive_sha256`. The binary still equals the successful native CI artifact; no native rebuild or behavior
change is needed. Validate through the actual portrait fetch helper before retrying packaging. No build-215 IPA
was published. This was a pinning mistake, not an upstream download or runtime streaming failure.


ISSUE-142 delivery/retest: the actual portrait fetch helper accepted the corrected r25 binary digest and published
r6 glass bar; all 28 glass-bar contract tests passed. Packaging run 42698801783 then passed every stage and
published build 216 from fd6ef1cdc7ca26397d1cfea0c0486bb270490417. The downloaded public asset matched SHA256,
ZIP integrity, exact verified r43 framework and r25 executable after signature removal, current casting/transfer
helpers, Python 3.11 bytecode, seek markers and 154 unsigned/unencrypted ARM64 images. Delivery receipt is
reports/streaming-recommendations-delivery.json. Native/software gates are complete; actual iPhone/Roku smoothness,
caption rendering, sound and visual acceptance remain pending. No live Drive account access or main merge.


## ISSUE-143 — Build 216 device retest: seek release resets position; conversion queue idle (2026-11-09)

Owner reports smooth dragging but release jumps to the beginning, seven conversions stay queued, and Start now
has no effect. This request is a findings review. Raw log and device screenshot remain outside Git.

Confirmed log evidence: build 216 with Kodi r25 and AirPlay r43 is installed. At 13:18:14, 13:19:14, 13:20:14
and 13:21:14 the preparation state has seven waiting jobs and empty current; no worker heartbeat is present.
The screenshot independently shows zero Working/seven Up next. Conversion is not observed actively encoding.
The library refresh and local playback from Drive succeed, with about 23.2 GB free. No Drive authentication,
network-timeout or out-of-space error establishes those as the cause in this capture. No new TV casting result
is established by this log.

Confirmed seek regression in the previous slider repair: pinned Kodi GenericTouchActionHandler sends gesture
END as velocityX/velocityY followed by finger x/y. GUIWindow turns the first two amounts into the point passed
to the exclusive slider. The new END handler calls SetFromPosition(point), treating velocity as a coordinate;
a stationary release clamps to zero. A 50%-pan/zero-velocity-release reproduction produces a 0% seek. Four device
release logs at 13:20:15/19/25/30 and subsequent flushes/sync warnings corroborate the owner report. The prior
handler harness checked drag ownership and seek count but stubbed coordinates, so it missed the resulting
position. Future regression protection must exercise real END payload packing and target percentage.

Confirmed conditional Start now bug: the action writes priority/retry state but never clears persistent paused-conv.
The service skips process_one while that pause exists and no current job is running; request consumption occurs
inside process_one. Reproduced with actual request/pause files in an isolated synthetic profile: the request stays
pending and applying it does not clear the pause. The device log does not include the saved pause flag, so this
is a proven blocking code path and a plausible queue explanation, not a confirmed on-device pause-state diagnosis.
A future fix should process explicit start requests before the pause skip and retain the intended pause ownership.

Review only: source behavior unchanged; no new IPA published. Device acceptance remains failed/open for these
symptoms. The new build's prior host/build passes do not override this actual device evidence.


ISSUE-143 repair authorized: owner requests fixes and a new IPA, then clarifies that eligible downloads/uploads/
conversions must automatically start while idle. Native r26 commits the already-dragged percentage via SendClick
on END; no release velocity is interpreted as position. A new compiled test extracts the actual pinned Kodi
slider methods, generic gesture-END packing and window dispatch, with platform/rendering stubs. All 32 target,
velocity, scale, cancel and tap scenarios pass; the previous r25 patch fails the same test (target 0 becomes 100
with a high release velocity). Initial harness compilation lacked two control-ID stub members; adding these
platform fields fixed compilation without changing tested Kodi methods. The native build runs this test against
its actual patched source tree, and IPA CI repeats it. Queue/scheduler repairs are in progress; device acceptance
remains pending and no new build is represented as delivered.


ISSUE-143 implementation follow-up: Start now resumes only the conversion channel for a valid pending job;
upload pauses and unrelated queue actions retain their ownership. The service reads saved requests before its
pause skip, recovering requests left pending by older builds, and checks for new idle work every 20 s instead
of 120 s (startup remains 5 s, pending commands 5 s, known retry backoff remains respected). Diagnostics now include
pause flags, request counts and scheduler reasons, without file IDs/names. The old log lacks the pause flag, so
the exact prior idle gate is not retrospectively established. The new evidence makes that gate observable.

The first r26 native run 42705056711 stopped in the new host regression harness, before native compilation:
the actual patched GUIWindow also references layout/property helpers that the initial harness omitted. Added
those platform stubs and made default tests apply the window patch too; all 32 scenarios pass against that path.
The first scheduler harness missed the service function-attribute stub, and the initial diagnostic request counter
used a dict-only reader for a JSON list. Added the function stub and explicitly counted list requests; the
scheduler/control diagnostics tests now pass. Full native rebuild and IPA validation follow.


ISSUE-143 scheduler coverage now executes the actual service loop with isolated queue/control files. Ten tests
pass: automatic idle conversion, upload followed by conversion, old/new Start now, preserving unrelated upload
pauses, invalid/blocked requests, honoring explicit conversion pause, retry eligibility, missing account, busy
transfer lock and privacy-safe control counters. Silent missing-account/lock skips now emit a scheduler reason.
Focused existing suites also pass: preparation 59, runtime 4, diagnostics 14, slowdown 21, library status 48,
status model 27, pages 37, direct downloads 24 and uploads 23. Portrait suite is still running at this checkpoint.
Native r26 run 42705743785 from 403bd10e683e8054c6437a1883895d662f80d1d9 is building; the previous failed
harness run remains recorded above. No app layout, styling, Drive library, credentials or main branch changes.


ISSUE-143 native verification (2026-11-10): run 42705743785 from 403bd10e683e8054c6437a1883895d662f80d1d9
passed all 32 real gesture/slider dispatch scenarios against the patched native tree, then compiled and published
Kodi r26. The public release executable equals the CI artifact, with binary SHA256
f4379642605486f9a09f16366e9d2f32279f3ce8c8c0b665a7465a17404678d3. Archive SHA256 is recorded separately as
d34ea5d0c349906b428a406ebf4a1dc4dfcf4e765223bec4a516d609ed2e220b. Native patch and pinned upstream commit
also match. The actual portrait fetch helper accepts the new binary pin; glass-bar contract 28, portrait 50,
scheduler 10 and the other focused suites pass. IPA packaging follows. Owner authorized this test IPA; no main
merge or device acceptance is implied. AirPlay r43 is reused unchanged.


ISSUE-143 delivery (2026-11-10): run 42732787090 passed every packaging gate and published build 217 from
16daca2621ad1272a84991e4fcb9b5c4cd051c30. Downloaded public IPA matches the release digest, ZIP integrity,
exact verified r26 executable and unchanged r43 framework after signature removal, current scheduler/controller
helpers, compiled Python 3.11 hashes for all four changed helper modules, and 154 unsigned/unencrypted ARM64
images. Receipt: reports/seek-queue-repair-delivery.json. The current worktree scan and UI guidance pass.
This closes the source/build/delivery work, while actual device seek release, automatic background work and
Roku/caption acceptance stay open. No live Drive credentials/media access or main merge occurred.


## ISSUE-144 — Build 217: conversion appears frozen behind slow Drive uploads (2026-11-10)

Owner supplies a screenshot rounded to Converting 8% and a new log. Review only; raw log/screenshot stay outside
Git. The log confirms build 217. At launch conversion_paused=true and 15 pending preparation requests; the service
clears that pause, consumes the requests, reports seven eligible jobs and automatically opens an episode. This
provides actual device evidence that the ISSUE-143 pending-start recovery works; it does not accept seek behavior.

Conversion progress advances from 3.024% at 18:57:04 to 5.992%, then 7.519% at 19:02:04 (device log time).
The worker heartbeat remains fresh (0–1 s), pause flags are false, and no Drive-read error is recorded. Most
importantly, Drive PUTs continue to succeed: 32 MiB in 145.655 s at 18:58:55, 141.016 s at 19:01:16, and
121.274 s at 19:03:18, all HTTP 308 acknowledgements (0.22–0.26 MiB/s). The capture ends at 19:03:36, eighteen
seconds after the last acknowledged piece. This is ongoing work with long stalls, not evidence of a permanent
app freeze. The upload path is the measured bottleneck; the log does not identify whether the underlying cause
is local uplink, carrier/router, Drive routing/throttling, or another transport factor.

Source confirms conversion output still uses drive_prepare.Sink MAIN_CHUNK=32 MiB and a bounded four-piece
queue. The earlier adaptive chunks changed Drive.upload_stream for direct copies, not this separate conversion
sink. A full output queue blocks the producer, so source reads and converter progress can remain unchanged for
minutes while a large PUT is in flight. prepare_cloud publishes current/rate from native progress callbacks;
upload acknowledgement alone does not refresh that UI model. Consequently stale/dash speed fields and the
unchanged generic Converting label conceal the upload wait. The source video is copied (HEVC 3840x1920, 10-bit,
copy=True), with audio processing; this log does not establish a slow 4K picture encoder.

Future repair should adapt aligned upload pieces in the conversion sink and expose upload/backpressure metrics
independently of native progress. Keep checkpoint windows independently sized: reducing MAIN_CHUNK must not
silently reduce MARK_CAP and break large-fragment/re-encode resume. Smaller pieces improve responsiveness and
recovery, but cannot establish increased uplink bandwidth. No code repair, new IPA, or runtime completion is
claimed in this review.


## ISSUE-145 — Unnecessary Drive preparation and separate Umbrella source-opening timeout (2026-11-10)

Owner wants compatible files kept unchanged, distinguishing this efficiency change from Umbrella's AirPlay bug.
The supplied latest build-217 log has Umbrella playing H.264 + EAC3 + ASS in MKV; Kodi demux takes 22 s and later
buffers once. First AirPlay attempt opens the source in 1.954 s, spends 43.045 s inspecting its index and reaches the
45 s startup deadline. There is no HLS endpoint or TV handoff. Later attempts are cancelled after 2 and 7 s, so they
are not codec-rejection evidence. A concurrent 32 MiB upload takes 128 s, but the log does not establish contention
or Wi-Fi as the sole cause. Raw log, source URLs/headers and test media stay outside Git.

Efficiency fix: actual native copy-video/codec inspection now stops full preparation for supported H.264/HEVC
video before creating an upload sink. Exact ID/checksum/size/version binds local readiness; a changed file must be
inspected again. The original keeps its ID/content/properties, with no false remote prepared markers. On-demand
container/audio adaptation still serves playback. Optional automatic repacks of already prepared movies stop.
Pending app-owned staging is journaled for cleanup; committing/promoted transactions and owner-kept choices are
protected. Watch-after-download and existing-file reuse recognize inspected originals.

Separate Umbrella candidate: reuse Drive's bounded HTTP byte-range cache for resolved remote MKV/AVI/WebM before
the existing native bridge opens them. Foreground profile uses 2 MiB blocks, 16 retained blocks, two-block read-ahead
and no background slowdown gate. Preserve provider headers; do not forward Drive authorization. Loopback control
and media URLs have random per-launch tokens. The service owns the source through TV playback; secrets/source
URLs stay in memory. New sources replace old ones; stale leases cannot close new sessions. Existing Drive/Elementum
loopback and direct MP4/HLS routes remain as before. This reduces repeated remote opens; it does not prove the
owner's provider or Roku now works.

Failures and corrections: (1) Initial wrapper would close the service source after AirPlay's 45-second settle check
returned successfully. Code review caught native playback outliving the script. Successful playing handoff now
retains the source; cancelled/failed/exception paths release it. Runtime tests verify both AirPlay and TV handoff,
including native exceptions. (2) The conversion-speed suite failed two source-string checks: one omitted the new
foreground read-ahead profile, and the other predated adaptive direct-copy chunk arguments already in the branch.
Updated expected wiring while retaining actual range, cache, background slowdown and adaptive upload tests.
(3) A build-192 wiring check required optional automatic repacks; updated to the newly owner-requested policy.
An attempted nonexistent test_drive_stream.py invocation also failed; actual range-cache coverage is in
conversion-speed and the new remote-media suite. No failed attempt is treated as a device regression/pass.

Retest: 17 focused suites, 442 tests pass, including compatibility 12, remote cache/controller 19, casting 62,
preparation 59, cloud transactions 26, conversion-speed 48, resume 12, scheduler 10, status 48, tools 31 and existing
library/watch/bootstrap suites. Real unchanged native host bridge streamed a generated H.264 MKV with identical
first video segment hash both ways: direct 7 upstream requests / 1.080 s; cache 3 / 0.335 s under 150 ms per-request
latency. Earlier run varied to 9 / 1.406 s versus 3 / 0.363 s; report records the latest repeat. These are host source
measurements, not iPhone/Roku acceptance. New suites run in import-review CI. UI guidance and project scanner pass;
policy read, existing text slots reused, visual/device review pending. Evidence: reports/compatibility-filter-review.json.
No native source/pin change, new IPA publication, account access or main merge in this patch.


## ISSUE-146 — Adaptive preparation uploads, accurate transport status, expired links and explicit Refresh (2026-11-10)

Owner approves the three recommendations and asks Refresh to inspect files before converting an already ready
episode. Root causes extend ISSUE-144/145: conversion output still issued whole 32 MiB PUTs; upload evidence only
updated at the end of the producer batch and UI relied on native callbacks; Refresh could only reuse an existing
probe rather than inspect a previously unknown original; retrying an expired resolved Umbrella URL reused it.

Repairs: preserve 32 MiB producer/on-disk pieces and the independent 256 MiB resume window, while each PUT starts
at 1 MiB and adapts between 1–8 MiB in 256 KiB multiples. Successful small pieces do not consume the retry budget.
Partial/lost ACKs query/resume only unconfirmed bytes and every confirmed piece updates speed. Final size/checksum
verification still protects the original. Finalization now checks upload-thread errors while waiting for queue room.

The independent runtime heartbeat exposes confirmed bytes, upload speed, active request age and transport phase.
It updates existing progress slots even while the producer waits for queue room or final flushing. Upload waits
longer than ten seconds say Waiting for Drive, with no invented ETA. Owner pauses and source verification retain
priority. Library status's explicit Refresh requests actual native inspection over the Drive range stream. Exact
identity caching survives restart; unknown/changed/failed sources cannot inherit readiness. Active conversion's
native instance is never probed beside itself: metadata/cache refresh runs beside it and unknown probes remain
requested until idle. Newer refresh requests and owner-kept/committing files are protected.

Umbrella AllDebrid's recognized unlock method registers selected link, resolved URL, name and size in a RAM-only
Home property, then the service broker keeps it with that exact source. HTTP 401/403/404/410 gets one unlock through
the existing account, shared between readers. A new filename/size/range total is rejected; provider headers/ranges
are preserved and the account credential goes only to the AllDebrid API. No new scrape, torrent, file download or
account flow. Unrecognized upstream hook shape is left unchanged. Other providers retain their current route.
Current public upstream blob 181335b6a51ff73575bbcef10935edfa248c30b6 was patched, compiled, executed with stubs
and checked for idempotence outside Git; actual owner provider access was not used.

Failures/diagnosis/retest: the existing upload concurrency test expected literal 32 MiB HTTP requests; its byte
integrity/nonblocking checks remain, now asserting bounded requests and exact total. The first adaptive sender
review caught that an eight-iteration loop would count successful pieces as retries; the revised loop counts
failures and a >8-piece regression passes. Another review caught finalization's blocking sentinel enqueue after
an uploader fails; a regression now fails promptly instead. The slowdown source-string test predated the foreground
cache profile from ISSUE-145; expected wiring now includes it, retaining actual background slowdown tests. A
heartbeat test's fixed 40 ms wait failed under host load (initial phase observed); it now waits up to one second
for the actual phase, retaining heartbeat/expiry assertions. All failure records remain; no device pass is implied.

Validation: 24 focused suites / 545 tests pass (report includes exact scripts/counts), scanner and UI guidance pass.
Native host comparison with 150 ms local request latency produces identical 467,251-byte video segments: direct
8 requests / 1.255 s, cached 3 / 0.378 s, cached+simulated HTTP expiry 4 / 0.511 s and exactly one API renewal.
These are generated fixtures/local HTTP/mocked AllDebrid responses, not live provider/iPhone/Roku results. Source:
reports/refresh-streaming-checks.json. Existing UI layout/style and verified r26/r43 native pins are unchanged.
Owner requests this updated test build for a retest; IPA packaging follows. Device and visual acceptance remain open.


ISSUE-146 packaging attempt: build 218 / run 42755096028 from 7c27f81d9d17bdfab366da0776d49af57607e2d6
stopped before IPA creation/publication. test_airplay_remux still required the old "AirPlay converts this video"
label, removed under ISSUE-145 because supported originals do not require background conversion. Corrected the
wording assertion while retaining functional source-routing checks; all 29 tests pass. The subsequent artifact
upload failure was secondary: tests stopped before producing the review ZIP. Ran every remaining packaging-test
script locally; all pass after setting the installed KODI_IOS_PYTHON311 path for the customized-IPA bytecode test
(the first local run omitted that environment variable; CI already supplies it). The app source/pins did not change
for this CI correction. Exact additional scripts/counts are in the checks report. A new source checkout/build run
is required; rerunning the immutable failed checkout would retain the old assertion. Build 218 was never delivered.


ISSUE-146 delivery: corrected source/test checkout 2d658de5ede446f9d8170a5c0185b1e5ee3c3efa passed every
workflow stage in run 42755715794 and published IPA 219. Downloaded release digest/ZIP, exact r26/r43 native
binaries after unsigning, 18 current helper sources and Python 3.11 source hashes, and 154 unsigned/unencrypted
ARM64 images independently verified. 24 focused suites / 545 tests and 38 remaining packaging test scripts pass;
all actual CI gates pass. Receipt: reports/refresh-streaming-delivery.json. This closes source/build/delivery work;
actual iPhone/Roku/provider behavior remains pending owner retest. Build 218 failure is preserved above. No main
merge or live owner-account/media access occurred. UI status values/text reuse the existing layout; visual review
remains pending.


## ISSUE-147 — Seek intent rollback, blank AirPlay captions and missing continuous-hour stop evidence (2026-11-10)

Owner supplies a new log, reporting that releasing the seek bar does not retain/play the chosen point. They add
missing subtitles and a stop after about an hour, and confirm the hour was continuous TV playback through AirPlay.
This is an investigation request; no new app fix/native release/IPA is produced in this review. Raw logs, URLs,
identifiers and the expanded host harness stay outside Git. Report: reports/seek-subtitle-stop-review.json.

Capture identity/limits: device log spans 21:38:48.457–21:43:56.863 (308.406 s, device clock), identifies build 217
with Kodi r26/AirPlay r43, the same native components retained in build 219. The logged TV user-agent reports Apple
TV. The hour-long session itself is absent; do not call a short-session error proof of that earlier hour-long stop.

Seek evidence: eight release handlers run and every submission takes 500 ms. Video first-picture-after-flush
markers range 846–7561 ms (some also occur during startup/return from AirPlay, not only seek release). The info-level
log does not include requested/landed times or all pointer-event IDs. Source trace explains the synchronous 500 ms
submission wait: VideoPlayer::SeekTime calls SynchronizeDemuxer, which can wait 500 ms on the calling GUI thread.

Expanded host reproduction compiles pinned real SendClick/SetFromPosition/OnMouseEvent, window gesture dispatch,
generic END packing and the actual Process player-info refresh block, with platform stubs. Normal drag 50% releases
50%, then the next info refresh while the backend is still at 3% redraws 3%. Insert an unrelated mouse-motion event
before that refresh/release and OnMouseEvent's unconditional m_dragging=false lets it overwrite intent: release
submits 3%. This is a concrete code defect and a plausible path for the reported behavior, not proof that this
exact event interleaving occurred on the phone. The earlier 32 r26 scenarios passed their limited dispatch cases;
they omitted render refresh/unrelated events and did not prove retention during an unfinished seek. First expanded
harness compile failed because its SetIntValue stub omitted default arguments; adding those defaults allowed the
actual-method reproduction. Product code is unchanged in this review.

Subtitle evidence: Kodi selects ordinal 0 and Apple's player selects English. Prepared fast path advertises two
text renditions. There are 32 subtitle-read I/O failures and 31 HTTP 200 responses containing only 8 bytes of empty
WEBVTT, completing in 1509–1599 ms. Native serve() gives lock acquisition, demux opening and cue reading a single
1500 ms deadline, closes the demuxer/source on expiry, and responds successfully with empty WEBVTT after failure.
Repeated requests can therefore keep opening/aborting the reader and serve blank captions as successful content.
A cue-free interval is valid, but these logged I/O failures are not evidence that captions were disabled or absent.

Stop evidence: this short session reaches playing and later closes with Apple's local clock at 16.6 s. Source reads
of 64 KiB take 1011–3453 ms, video byte-range responses repeatedly end partially, and Apple reports -12889 plus two
-15628 CoreMedia errors. These show real source/streaming trouble during this captured session. An incomplete range
can also result from a receiver closing/reseeking, so do not label every partial response an upstream failure.
There is no basis here to assign the earlier hour-long stop to Wi-Fi, an expired link, or a hard time limit. Need
kodi.old.log or the actual log covering that continuous hour and its stop, before further restarts rotate it away.

Repair direction: keep dragged/pending seek intent independent of progress polling and unrelated pointer events;
avoid a synchronous demux wait in the touch UI path; record requested and landed times. Warm/prefetch/cache captions
on an independent worker, retain unfinished work and distinguish failure from a genuinely cue-free interval. Native
rebuild/device retest would be required for a shipped native repair. These are findings/directions, not a claim
that build 219 fixes them. Device acceptance and main remain unchanged.


ISSUE-147 supplied kodi.old.log follow-up (2026-11-10): the new file is the same build-217 session, with all
1,993 prior lines an exact prefix. It adds 59 lines / 17.764 seconds, ending at 21:44:14.627; total capture length
326.170 seconds. Added lines show Kodi starting orderly application shutdown at 21:44:10.741 and services exiting.
The captured AirPlay player had already closed at 21:41:10.298, so this later shutdown is not the initiating cause
of that earlier AirPlay failure. There is no crash trace in the added tail; the file ends during teardown, so this
is not proof of final process exit status or an OS-level absence of termination. No hour-long playback/stop is
present in either file. The seek/caption findings stand; the specific continuous-hour stop cause remains unknown.
For a future recurrence, export immediately after the actual stop before exiting/restarting Kodi, since rotation
can replace the needed session. Follow-up recorded in reports/seek-subtitle-stop-review.json. Review only; no app
source change, new tests/build/IPA, account access or main merge.


## ISSUE-148 — Build 219 skips faster opening; Umbrella cache fails to register (2026-11-10)

Severity: HIGH. Components: Library status Refresh / preparation policy; service-owned foreground source cache.
Owner: compatible video skipped conversion successfully, but also skipped faster opening; Refresh should audit
the entire library and repair missing preparation. Umbrella stays loading and never connects.

Evidence: supplied build-219 session spans 06:35:11–06:43:22 (device clock). At 06:35:24 the media_source_bridge
startup raises AttributeError: PosixPath has no setProperty. Both Umbrella starts report source_cache=false.
First attempt is cancelled after about 36 seconds; the next takes about 42 seconds inspecting its index and
reaches the 45-second opening deadline. This fails before TV connection; Wi-Fi failure is not established.
Raw logs remain outside Git.

Root causes:
- DEC-031's codec-only skip also cancelled repack jobs and trusted prepared/cache flags before any full file audit.
  Manual Refresh inspected only unknown files, so a compatible cached file could never regain missing faster-open work.
- The source broker was registered on the service's home filesystem Path rather than Kodi's Home window.
  Standalone cache tests passed but never executed the service setup, missing the integration error.

Repair:
- Manual Refresh re-reads every eligible file, probes actual tracks and checks bounded MP4 box/index ranges.
  Compatibility and fast-open evidence are separate. Naturally front-indexed MP4 and valid indexed prepared files
  are kept; MKV, tail-moov MP4, unindexed fragments and known older prepared layouts queue only missing layout work.
  Supported picture is copied; unsupported video retains native conversion. Source identity is rechecked afterwards.
- Already-ready metadata cannot bypass a requested repair. Owner-kept/committing/promoted originals stay protected;
  active native conversion defers inspection; failed reads retry without reporting a fresh successful audit.
  Repeated Refresh preserves existing output/checkpoints and failure backoff for a still-needed repack.
- Service registers the cache through Window(10000); lifecycle closes startup failures and clears its own endpoint
  on abort. Drive/Elementum loopback and already-working MP4/HLS routes are unchanged.
- Existing status fact slots show faster opening independently; no redesign or native component rebuild.

Regression evidence: full-library/repeated-refresh tests, prepared-marker override, missing-layout repair through
actual queue promotion/verification, changed-source rejection, owner/commit safety, cancellation and range guards;
real generated native MP4 layouts checked. Actual service startup regression fails against original HEAD and passes
with Path home after the repair, including selected-source range read and shutdown. See checks report for totals.

Status: source repair implemented; host checks recorded separately. iPhone/Roku/provider acceptance is pending.
The source-opening timeout can have additional provider causes; this fixes the observed missing cache route.
ISSUE-147 seek intent, subtitle timeout and unobserved continuous-hour stop remain open; no repair is claimed here.

ISSUE-148 follow-up before delivery: final review found the full-audit marker could be consumed when its only
file was actively converting or recovering a transaction. The marker now remains pending through both cases,
then inspects the resulting file when safe. Two actual-queue regressions cover this. Build-220 packaging was
superseded and cancellation requested before delivery; its workflow outcome is recorded in the checks report.

ISSUE-148 delivery: verified IPA 221 from fcae63e0f3dc83a8fb537cbea4d863e3ebfc5b29, run 42842353113 success.
66 suites / 1,174 unit tests plus 32 existing slider scenarios and all CI stages pass. Downloaded IPA checksum/ZIP,
19 helpers and Python 3.11 source hashes, verified native binaries and 154 unsigned ARM64 images checked.
See reports/refresh-layout-cache-delivery.json. Source/host repair complete; actual iPhone/Roku/provider and UI
acceptance remain pending. ISSUE-147 is not included. Main remains unchanged.

## ISSUE-149 — Build 221 cancels AirPlay during native startup (2026-11-10)

Severity: HIGH. Components: AirPlay controller, native first-segment priming, source diagnostics.
The supplied build-221 capture has two Umbrella attempts with source_cache=true. Inspection takes about
13 and 15 seconds. Both hit the controller's 60-second startup_timeout before TV handoff. Pausing background
uploads/conversion does not remove the second timeout. Video production takes about 14 seconds; audio finishes
with result -5 only after cancellation, so that result alone does not establish corrupt media/provider failure.
The older native “not H.264/HEVC” message is also misleading: copy eligibility can reject profiles/chroma/depth.
The capture does not identify the exact source-I/O bottleneck or establish a Wi-Fi fault.

Root cause: independent, overlapping clocks. The outer 60 seconds includes inspection; native priming starts its
own 55-second budget afterwards and produces video then audio sequentially. Unconditional segment-zero prefetch
can also compete with the resumed segment (63/64 in the capture); missing init can regenerate zero again.

Source repair: preserve a single native 100-second reservation-to-buffer deadline across queued work, inspection
and priming; advertise it to Python with 5 seconds of controller grace (old frameworks keep legacy behavior).
Prime video and audio concurrently at the actual resume target, cache that target's init and avoid unrelated zero
prefetch. Cancellation and bounded startup remain enforced. Logs now report codec/profile/pixel depth, separate
audio open/seek/scan/packet/I-O time, cache hit/miss/wait counts, HTTP status/retry/error/read time, deadline versus
cancellation and background pause state. Signed source URLs and account state are not added to diagnostics.

Host regressions: reservation includes queued delay; resumed first video/audio units are cached; copied and
converted target segments decode with their init; cancellation/readahead, streaming and seeking pass. The initial
recommendations run had 1/37 failures because its cancellation setup depended on old implicit zero-prefetch. It
now explicitly consumes zero to schedule real readahead, preserving its cancellation assertions; 37/37 pass.
One run against a separately launched range server failed after that server exited on resume, and the harness
continued into an unavailable playlist. The server is now owned by the same orchestration as the test, and failed
source-open assertions return before dereferencing missing playlists. Four healthy-server native suites pass
(211 checks). This environment failure is retained, not attributed to the iOS app.

Python test adapters initially assumed the source URL was the last controller argument, an exact old broker-status
shape and a pre-metrics unlocked DriveStream mock. Updated adapters assert the URL/lease separately and preserve
renewal/privacy assertions while checking safe metrics. Final targeted suites pass. Settings tests initially
assumed every Library option was an action; they now distinguish the new boolean and verify its default/help.
See reports/airplay-opening-episodes-checks.json for final counts and acceptance limits.

Status: implemented/tested as source only. No iPhone native framework rebuild, native pin update, workflow,
IPA/publication/push or main merge; owner explicitly holds the IPA. Verified AirPlay r43 remains pinned and does
not contain these new native changes. Rebuild/verify/pin native AirPlay before the next authorized IPA. Actual
provider/iPhone/Roku acceptance remains pending. ISSUE-147 seek/caption/hour-stop issues are not repaired here.

## ISSUE-150 — Newly released episodes require manual downloads (2026-11-10)

Owner requests automatic downloads for anticipated episodes of shows they download, checking on opening rather
than continuously. Source now enrolls confirmed TV downloads with canonical show TMDb ID and selected quality/
HDR/codec/source/size preferences. Existing shows can use Follow new episodes only in the season download menu;
Library settings offers Download new episodes automatically, default enabled. Registration is after confirmation,
not after a canceled picker; manual show registration does not require a running download engine.

Opening/foreground passes use fresh TMDb show/season dates, never episode titles as release proof. Future,
undated, special and older episodes are skipped. Bounds: 25 shows, 8 source attempts, 180-second planning budget,
30-minute per-show cooldown; an already-started source request can extend the pass up to its 120-second timeout.
A lightweight 15-second app-state check schedules only launch/foreground passes, postponing busy UI; it does not
periodically search sources while the app stays open. Media playback, background state, disabled setting, transfer
pauses and abort stop further work. Network/ownership failures defer; missing accounts/engine do not open dialogs.

Actual Drive/phone inventory plus matching queue jobs prevent repeats. Failed jobs retry a different source on a
later eligible opening; cancellations remain protected. Request IDs and exact show/season/episode matching ensure
only the requested automatic choice is queued. Late timed-out responses are suppressed rather than opening a
manual picker. Queue deduplication is now serialized and includes season, fixing the concrete collision between
same-number episodes from two seasons of one pack. Stale service saves preserve newly attached show identity.

Thirty watcher tests include advancing a synthetic future episode's actual date, restarts/preferences, ownership
failure, bounds/cooldowns, later seasons, dates versus names, cancellations, retrying failed queues, fresh exact
selection, canonical ID recovery, cross-season/concurrent queue writes, late/empty automatic results and the real
catalog-adapter → deck picker → queue integration with synthetic network/Kodi dependencies. Initial calendar test
incorrectly treated every season's episode 1 as owned; fixed the fixture to S1E1 and hardened season-row checks.
UI policy/routed HIG guidance read; existing settings/menu/notification controls only. No desktop Kodi binary
available, so visual/device and real provider/new-release acceptance are pending. No owner account/media accessed.
Status: code/host verification ready; held with ISSUE-149 for an eventual authorized native/IPA build. No release,
push or main merge. The owner should use Follow new episodes only for shows downloaded before this feature.

ISSUE-147 authorized repair follow-up (DEC-034, 2026-11-10): owner requests the three recommendations and a test
IPA. Slider polling now holds the dragged/pending percentage until reported landing or a bounded 15-second timeout;
unrelated mouse movement cannot end a drag. Progress actions use SendThreadMessage outside touch dispatch, with
requested/observed target and timing logs. Expanded actual slider/gesture/info-refresh harness passes 45 scenarios.
Native Kodi r27 candidate source 780c990 / run 42878755013 compiled and published successfully; artifact verification
and pinning precede IPA packaging. Patch generation initially introduced context trailing spaces; normalized them,
reran the harness/project/diff checks and published the corrected source, retaining both source commits.

Subtitle requests now use a bounded independent worker/cache. A request waits up to eight seconds without canceling
its in-flight read; pending/failed work is retryable HTTP 503 with Retry-After, and only successfully read cues enter
the cache (including legitimately cue-free intervals). Worker reading has a separate 45-second bound and media
lanes remain independent. Selected/next cues warm in the background; session cancellation wakes waiters, aborts the
reader and joins before freeing the plan. A generated-media regression deliberately delays a subtitle read ten
seconds: first request gets 503, the same work completes with actual text, a repeat hits the cache, invalid track
gets 404. Eight native checks pass. First compile inserted the worker before helper definitions; moved it behind
those definitions and recompiled. First delay test's control reply used HTTP/1.0 against a helper expecting 1.1;
the seven caption checks passed, control-response assertion failed. Fixed the control fixture's protocol/close,
then all eight passed. One old Python source assertion required the replaced trylock approach; updated it to the
bounded worker wait; actual delayed native test protects behavior. Full native/CI evidence follows in the report.

Automatic stop evidence samples safe native player/time/buffer/error/route fields, source cache/HTTP counters and
network progress. A bounded eight-minute local history and three rotating stop files are retained, the useful tail
is also emitted into kodi.log, and Export diagnostics includes them. A continuous-hour synthetic test verifies
capture after failure; normal end, explicit close, pause, seek and suspension are distinguished. This adds evidence
for the previously uncaptured hour-stop; it does not identify that historical failure's cause or guarantee a fix
for every receiver. No account/media URLs are added to these snapshots. Device and visual acceptance pending.

## ISSUE-151 — Downloaded movies bypass resume history (2026-11-10)

Owner adds: downloaded-library movies start at the beginning instead of offering Continue. Local and Drive movie
rows bypassed the shared history/resolver, unlike downloaded episode rows; initial zero during opening and paused
Kodi time during TV playback could also overwrite a saved point. Movie rows now batch actual local/Kodi bookmarks,
match shared history by title plus year, offer Continue from / Start from beginning / Cancel in existing Kodi select
controls, resolve the exact completed copy with its chosen offset and register it in shared progress. No TMDb ID
is fabricated: uncached movies retain a valid downloaded-copy route in Continue Watching. Existing provider/version
choices remain intact. Provider URLs are never browsed by filesystem RPCs; local copies still require the actual
completed-movie inventory. Native-library rows keep their existing route. The idle movie page refreshes when the
history revision changes. Initial near-zero opening samples cannot erase a saved point for twenty seconds; live
AirPlay position is saved and a bounded handoff guard protects it while Kodi moves from its old paused position.
Sixteen focused regressions pass; expanded packaging/UI/library/progress checks and device review follow. UI policy
and routed HIG playback/slider guidance read; existing controls and select menu, no layout/style redesign. Owner
approved native builds/IPA under DEC-034; no main merge. No owner account or media was accessed.

ISSUE-147 final regression follow-up: found that integer player progress within one percent of a fractional target
could still clear against the unchanged baseline. Record the pre-submit observed percentage and require it to
change before accepting landing; the fractional regression fails without this guard and passes with it. Kodi r27
is superseded before IPA; r28 source c829a92 / run 42881626230 passes 46 local scenarios and is building. Full native
suite also retained two assertions against the previous misleading conversion log string; update to the corrected
conversion reason while retaining actual decode/format checks. The first AirPlay candidate run 42881365570 compiled
its framework but is superseded for that test correction. Python restart assertion likewise needed its new diagnostic
wrapper reflected; library refresh's old raw-path assertion now checks the exact copy inside the resume route.
One unrelated upload nonblocking timing check measured 1.074 seconds against a 1-second bound while native/video,
portrait generation and parallel suites competed; retain the bound and rerun in isolation. No product relaxation.

ISSUE-147 verification follow-up: isolated nonblocking upload test passed unchanged, but full-file reruns measured
2.729 and 1.116 seconds at the one-second wall-clock assertion. Replace that timing proxy with a deterministic
blocked-upload event: the producer must finish all three writes while PUT is still deliberately blocked, then
release the network and verify the exact stored bytes. This strengthens the nonblocking guarantee without changing
application upload behavior or simply raising the old limit. The full 26-test preparation suite is rerun with it.
Local full native run (3251 checks) also lacked KR_TEST_FONT, causing 14 text-render failures despite valid cue
parsing. Use the host runner's documented DejaVu fallback for retest; no iOS font change. Four old burned-text
checks now assert the intentional unadvertised-track 404 and the old optional-caption timeout check now asserts
bounded retryable 503 plus prompt cancellation. One prefetch latency assertion ran under concurrent generation
load and is retained for isolated retest. Original full-run failures are kept in the checks report.

ISSUE-147/151 verification: final local native suite passes 3252/3252 with documented host font, strict prefetch
timing unchanged. All 62 Python suites / 1094 tests and 46 actual gesture/info-refresh scenarios pass; a final
post-pin packaging test needed its existing Python 3.11 environment variable restored and then passed. Stop
classification also captures an apparent end notification well before known duration and retains the final
snapshot on normal closes. Kodi r28 artifact/release/upstream/patch/ARM64 verified; AirPlay final candidate
923131c / 42883448916 passes native host, framework and end-to-end conversion jobs; exact artifact digest/ZIP,
new exports and ARM64 checked. Pins r28/r44 staged for verified framework publication then requested test IPA.
Device/provider/visual acceptance and historical hour-stop attribution remain pending. No main merge.

ISSUE-147/151 native publication verified: Kodi r28 release binary equals run 42881626230 artifact; exact patch
and upstream digest checked. AirPlay final 42883448916 passed host/framework/end-to-end jobs; verified artifact
digest/ZIP/new APIs/ARM64, publication 42886188374 succeeded and release archive independently downloaded and
compared byte-for-byte. Pins r28/r44 now point at these verified immutable releases. IPA packaging is next;
device/provider/visual behavior remains pending and the historical continuous-hour cause is still unknown.

ISSUE-147/151 packaging retry: build 222 / run 42886688945 stopped before packaging at GlassBar's stale r26
tag/digest snapshot after the verified r28 pin update; no IPA was produced or delivered. Subsequent audit found
AirPlay's old r43/previous-release snapshots too. Updated strict expectations to independently verified r28/r44
and their actual previous pins, rather than weakening/removing the checks. All workflow scripts from GlassBar
onward rerun under the existing Python 3.11.17 and pass, including 46 actual seek scenarios. Native app sources
and binaries are unchanged. Missing upload artifact was a secondary consequence of the early test failure.
Next dispatch a fresh packaging run from these verified test-only corrections; keep 222 in failure history.

ISSUE-147/151 delivered as verified test IPA 223: source f6b40982b97c8d67976e748e98381cfe7fd03759, run
42887751497 success. All 62 CI Python suites / 1094 tests, 46 actual slider scenarios, native CI 3336 checks plus
end-to-end conversion and local native 3252 checks pass. Downloaded asset digest/ZIP, exact r28/r44 binaries after
signature removal, 22 source helpers / 21 matching Python 3.11 hashes and 154 unsigned ARM64 images verified.
See reports/playback-retention-delivery.json. Failed 222 remains recorded; no app/native change was needed for
its strict test-pin correction. Historical hour-stop cause remains unknown; automatic evidence is added. Resume
reuses saved history; a progress point never recorded by old builds cannot be recreated. Device/provider/visual
acceptance pending, no main merge or roadmap acceptance-count change.

## ISSUE-152 — Full season offers individual episodes; quality must reflect usable sources (2026-11-11 UTC)

Owner found a Full season search offering an episode when no pack exists. Sorting partial releases below packs
still allowed a partial to satisfy that interaction. Automatic rest-of-season selection could also lower quality;
counting a source-picker result as a queued download was insufficient proof of acceptance.

Source repair: a scoped pack request exposes only verified, seeded, non-bad releases with full coverage. Cancel
ends the pack interaction. With no genuine pack, list aired episodes, exclude owned/queued entries, inspect their
sources without selection, then offer only qualities actually returned by the verified picker with episode
coverage. Exact-quality selection never falls back to a lower resolution. Queue receipts must match the request
ID and require the real cloud queue save. Explicit old episodes awaiting that quality are persisted separately
from following future releases and retried on opening/foreground. A foreground season interaction holds the
opening watcher's search lane. No source URLs or credentials are persisted. Unknown source formats/identity fail
closed; a completed no-results search can enter the fallback. Existing manual non-season pickers retain behavior.

Regression coverage includes real picker filtering and the HTTP redirect/cloud-save boundary, not just selected
source mocks: unavailable 4K, zero seeds/wrong titles/episodes, full versus partial packs including long lists,
empty/malformed sources, vanished chosen quality, actual queue receipt, cancellation and old-episode strict retry.
Initial new retry test exposed a pre-existing default logging callback that rejected keyword fields; corrected
the no-op callback. An inflight-filter edit initially shadowed the queued-result list; renamed the helper and
reran the focused suite. Desktop Kodi rig evidence and final check counts are recorded at the delivery checkpoint;
no device/provider success is inferred and no IPA is published under the current hold.

## ISSUE-153 — Accepted downloads invisible while uploads are paused, including after Refresh (2026-11-11 UTC)

Owner's build-223 logs show an accepted new job after the movie selection: total debrid jobs 11 → 12, new jobs
2 → 3, while one older job remained copying with an empty current record. uploads_paused=true throughout the
relevant interval and through the end of the later log. The second attempt did not increase the count again.
This proves a durable acceptance and a persistent pause, rather than proving a missing job or a Wi-Fi failure.
The older show report has the same paused/pre-transfer condition. Private log paths and media IDs stay outside Git.

Concrete model/UI defects: _copy returned None before any transfer progress; Library status ignored drive_next;
Queue access depended only on preparation jobs; Queue drew only the first three Drive entries without paging.
Refresh rescanned Drive media while these accepted transfers were omitted, yielding 0 Working / 0 Up next.

Repair: publish the first pre-transfer job as queued/indeterminate or explicitly paused, include remaining
transfers in Library status with stable identities and their owning actions, and make Queue reachable for Drive
work. Page all Drive entries using the existing page controls; never send transfer IDs to preparation reorder
handlers. Library/Queue reread durable transfer jobs and pause controls locally, retaining the service's freshness
for other jobs. Resume/cancel go to transfer_control. A new download while paused offers explicit resume-upload or
keep-queued choices and a truthful notification. Quiet automatic jobs preserve the pause. Safe queue-save events
record kind/status/pause/count without media names or identifiers.

Verification failures retained: rebuilding every model from raw state initially discarded the published native
heartbeat and immediate reorder previews (three status tests and one Queue test failed); changed to refreshing
only durable Drive transfers while preserving the published non-transfer model, and all affected tests pass.
The first paused-notification regression exposed an incomplete old fake Kodi lacking Window; completed the fake
so it now exercises the success notification instead of silently catching an AttributeError after queue save.
The desktop rig dependency install first ran out of disk; removed reproducible old downloaded IPA duplicates and
one public-media archive, retained build 223 and all receipts, repaired dependencies and resumed the isolated rig.
Final desktop evidence/check counts follow; this does not prove actual phone transfer throughput or receiver use.

## ISSUE-154 — Browse for subtitle blocks the interface during streamed movie playback (2026-11-11 UTC)

Owner screenshot and build-223 log: FileBrowser.xml loads at 15:47:16 device time; subsequent touch events reach the
iOS view but produce no handled Kodi clicks, while background diagnostics continue through 15:47:39. This narrows
the failure to opening/browsing the subtitle file dialog. It is not evidence of an online subtitle-service failure:
owner subsequently confirms Download subtitle works and captions appear on the phone. The later attempted taps do
not establish a separately handled Download action after Browse blocked the UI.

Kodi 21.3 BrowseForSubtitle starts the file browser at the playing item's dynamic path and its browser performs a
synchronous directory listing. A streamed movie URL is therefore a candidate blocking directory. The log contains
no completed directory error or thread stack proving the precise blocked operation. Investigate/reproduce with a
controlled slow HTTP folder in the desktop rig before attributing the exact root cause or changing native code.
Current source repair does not claim to fix Browse. AirPlay captions and Media Assistant's reported five-second
stall are separate follow-ups to ISSUE-147/149; latest received logs contain no corresponding AirPlay session.
Requested a fresh post-test log and whether captions were enabled before or after TV handoff. Native pins remain
r28/r44; owner holds the IPA.

ISSUE-153 final source handoff: desktop UI exposed queued transfers duplicated in Waiting and Drive sections;
exclude transfer rows from preparation holds. QPREV/QNEXT existed in controllers but were never rendered; add the
actual controls with disabled boundary states. A conditional link also unnecessarily shortened a header; use the
full-width header when the link is elsewhere. Relevant controller/generated XML regressions pass. Final real UI
paging/action recheck remains pending at the owner's handoff request.

ISSUE-154 follow-up: reproduced in real desktop Kodi with a synthetic HTTP movie and a parent directory delayed
25 seconds. The subtitle settings UI stays on screen and cannot process Close during that directory request.
Source guard clears an HTTP(S) initial browser path; local/SMB paths retain behavior. Complete patch applies to
pinned upstream, Linux engine rebuild passes, and the same browser opens without another parent request afterward.
Normalized added patch context whitespace and rechecked the complete patch. No iOS binary rebuilt/pinned and no
IPA published; device acceptance remains pending. Native r28 is still the old delivered engine.

## ISSUE-155 — Downloaded show folder opens an empty page (Phony) (2026-11-11 UTC)

Owner's show is present in source-search logs. Downloaded TV discovery includes Drive folders without requiring
completed episode files; preparation/status discovery indexes video files and jobs. A folder poster therefore
cannot prove a completed episode. Paused queue omission is repaired under ISSUE-153. The distinct empty show page
still needs a truthful empty state and action, or completed-membership filtering without foreground network cost.
An attempted empty-page CTA populated properties in the desktop rig but did not render its header correctly;
owner requested committing completed work and leaving the rest out. Those UI/backend/test changes were removed
and saved as a local patch outside Git. No completed fix claimed for this page. See REVIEW-HANDOFF-PR16.md.

Rig failure history: stock Home widgets produced unauthenticated Trakt prompts, isolated by moving to Settings.
A real engine occupied the fixture's initial port; move controlled provider replies to another port through a
transport adapter. Add the actual Kodi Six dependency to the direct picker fixture. Missing Umbrella metadata in
the desktop add-on subset required intercepting its account adapter before constructing the absent add-on. The
phone's bundled bootstrap path also required a rig-only resource alias. These were fixture/environment issues,
not product account failures. The final container stopped with exit 255/OOM=false; further diagnosis and smoke
tests were stopped at the owner's explicit handoff request. Completed evidence remains on disk.
## ISSUE-156 — Subtitles and Audio menus with Download and apply (2026-11-11)

Status: IN SOURCE, LOCAL ONLY (not pushed, not built; owner: "code it but dont push it").
- Owner: the CC and waveform buttons opened Kodi's settings dialog ("those look meh"); wanted working download /
  find subtitles, "a button that will find, download and apply the subtitles". Mockup approved: PR #17 round 2.
- Done: `tracks.py` (page `tracks`) + `1080i/IOSTrackMenu.xml` (`pages.track_menu`) replace
  `osdsubtitlesettings` / `osdaudiosettings`. Tracks from Player.GetProperties, one tap switches and closes with a
  notice; Timing (subtitle / audio delay), Volume boost (volume amplification); More: Choose another, Add from a
  file, Use for all videos (`locale.subtitlelanguage`). Download and apply: no subtitle add-on is installed on the
  phone, so `track_menu.py` searches Podnapisi (free, no account) by title, year and episode in Kodi's subtitle
  download language, ranks by the file's release name, downloads the zip and `setSubtitles()`.
- Verified (desktop Kodi rig, landscape 1311x603, a generated test video with 2 audio and 2 subtitle tracks): both
  menus render like the mockup with the real tracks. Not verified: tapping in the rig (stopped by the owner), the
  Podnapisi answer (this sandbox cannot reach podnapisi.net; API shape from subliminal's provider), the phone.
- Known gaps: Volume boost shows no value (Kodi has no info label for it); the More page is Kodi's select list, not
  the drawn sub-page; a downloaded subtitle is not remembered for the next play yet.
- Regression: scripts/test_track_menu.py (9).

## ISSUE-157 — Settings rig audit: blank app settings, labels under switches, cut footers (2026-11-11)

Status: FIXED IN SOURCE, LOCAL ONLY (not pushed, not built). Desktop Kodi rig (portrait 603x1167), every Settings route.
- Routing: all 23 Settings routes open the right window with no errors (Settings, Interface, Player, Media, Services,
  System, PVR, Games, Skin Settings, Profiles, System info, Event log, File manager, Add-ons, Add-on updates,
  Favourites, Accounts, Search, Tabs & Rows, Library status, Customisation and its four pages, Library). The
  navigation menu only runs on iOS (System.Platform.IOS); customise_counts has no window by design.
- Fixed: the app's own add-on settings (Activity, Updates, Library…) showed no labels at all: settings.xml used
  plain-text labels, which Kodi 21 shows blank. 27 labels now numbered (32001+) with
  resources/language/resource.language.en_gb/strings.po (check_project allows .po).
- Fixed: toggle rows let long labels run under the switch (Media "Ignore different video versions on scan",
  Services "Announce services to other systems", add-on settings): the label now ends before the switch.
- Fixed: the add-on settings title scrolled sideways (caught mid-word); it now truncates.
- Fixed: footers had fixed heights, so longer ones lost their last line (Library › Library status); they grow
  with their text.
- Not fixed (belongs to the Settings inside-pages redesign, PR #18): Skin Settings, Profiles, Favourites and the
  Settings search keyboard are still Fuse's landscape windows letterboxed in portrait; Kodi's settings pages keep
  category chips, "- " sub-setting dashes and one help paragraph at the bottom; Add-on updates with nothing to
  update shows only "..". Check for updates in the rig says the private repository needs a token (rig only).

## ISSUE-158 — Downloads stopped for days: uploads stayed paused (build 223, 2026-11-11)

Status: FIXED IN SOURCE (build 224); device test pending.
- Owner: "I need downloading to work asap, its currently completely broken". Build-223 log 27f59dcd: uploads_paused
  true in all 122 status snapshots over two hours; debrid queue 1 copying + 3 new, none moved. AllDebrid itself
  answered (one transient URLError retried).
- Cause: Play on TV's "Pause and retry" (cast.py) set the owner's own pause on uploads and conversion "until resumed
  in Library status"; nothing lifted it, and Library status only said "Uploads paused · resume to download" in grey.
- Fix: that pause is now marked as AirPlay's (transfer_control why='airplay') and is lifted two minutes after
  AirPlay stops (release_airplay, from the service's AllDebrid loop); the first start of build 224 lifts any pause
  carried over, logged with a notice (reset_once); a paused upload with downloads waiting raises a "Downloads are
  paused" card with Resume at the top of Library status (work_state 'uploads_paused', page resume_uploads). Owner
  pauses still last until Resume.
- Desktop Kodi rig: the card renders; Resume removes the pause and reopens Library status. Also found: the rig's
  scenario wrote a new 'added' time every second and debrid_drive.save merges by it (468 duplicate jobs); scenario
  fixed, not an app defect.
- Regression: scripts/test_pause_release.py (6).

## ISSUE-159 — Kodi r29: Browse for subtitle guard built and pinned for build 224 (2026-11-11)

Status: BUILT, VERIFIED AND PINNED; device test pending.
- r29 = r28 plus the ISSUE-154 guard (no file browser started at an HTTP(S) movie URL). Run 42942056360 (macos-15,
  cached depends, about 20 min). Release kodi-ios-portrait-r29: zip sha256 9e1d40b9…, executable sha256 070b0baf…
  (both re-checked after download; arm64 Mach-O). Pinned in migration/ios-portrait/source-lock.json with r28 as the
  previous executable; test_glassbar's pin assertions moved to r29/r28 (the old-pin trap that failed build 222).

## ISSUE-160 — Settings redesign coded locally from the approved boards (2026-11-11)

Status: CODED AND RIG-CHECKED ON THE DESKTOP RIG; NOT PUSHED, NOT BUILT; device untested.
- Section pages (Interface, Player, Media, Services, System, PVR, Games) with category rows, big-title category
  pages without chips (Back returns to the section), Skin Settings landing + per-section lists with the Settings
  Level row, Download/Stream and quality pickers (tiles, second line), Profiles, Favourites, Search Settings
  (own edit field) and Add-on Updates pages. Wording: "Download" / "Stream" replace Elementum / Umbrella.
- Merge traps found: helper patches conflicted on PAGES, the portrait fingerprint, settings_page.files() and
  test routes; a bad merge duplicated the ROOT rows (caught by test_settings_page: duplicate control ids).
  Add-on Updates said "Everything Is Up to Date" even when Kodi's list could not be read; heading is now a property.
- Not done / unverified: add-on settings sheet tabs (board 08); "- " sub-setting prefix (Kodi core string); More
  menu links still use old native windows; Search keyboard (Action(Select) opens Kodi's own keyboard on desktop,
  iPhone behaviour unverified); [B] bold in search results; Favourites with real items (empty state only seen).
- Regression: test_settings_sections, test_skin_settings, test_pickers_redesign, test_profiles_favourites,
  test_search_updates, test_settings_search.

## ISSUE-161 — Umbrella AirPlay still cancelled at 60 s in build 224 (2026-11-11)

Status: ROOT CAUSE FIXED IN SOURCE (local); needs AirPlay framework r45 rebuild + pin; device untested.
- Owner log (build 224, Dragon Ball Super Beerus S01E01, debrid.it MKV, H.264 High 10 → converts): attempt 1 opened
  in 6 s, inspection took 21 s, the TV endpoint was ready at 27 s, then the sheet was closed at 31 s (aborted).
  Attempt 2 needed 3 open attempts (10 s) and 50 s of inspection; cast.py cancelled at exactly 60 s
  ("controller_budget_s":60, "start result -1: AirPlay canceled") before the first segment reached the TV.
- Root cause: ISSUE-149 gave the native side one 100 s startup deadline and exported kodi_airplay_startup_budget so
  Python waits 105 s. The function is defined in build-airplay.sh but missing from the -exported_symbols_list, so
  r44 hides it; airplay.startup_budget() hits AttributeError and keeps the legacy 60 s. kodi_airplay_health was hidden
  the same way (native health diagnostics never reached the log).
- Fix: both symbols added to the exports list. Regression: scripts/test_airplay_exports.py (every default-visibility
  native function and every lib.kodi_airplay_* call must be exported); fails on the old list, passes now.
- Secondary, not fixed: the source is slow per request (~2.6–3 s per 2 MiB range, about 0.7 MB/s) and Kodi's own
  paused player keeps reading the same debrid URL (CFileCache) during AirPlay startup. Even with 105 s, a 50 s
  inspection plus conversion of the first segment is tight. Next step if r45 still times out: stop Kodi's read-ahead
  (or stop playback) before inspection, and log inspection bytes/requests.

## ISSUE-162 — Owner: no Arctic Fuse keyboard on the phone; native keyboard everywhere (2026-11-11)

Status: CODED LOCALLY; Kodi patch needs the r30 executable build; device untested.
- Kodi 21.3 on iOS picks the skin's keyboard (DialogKeyboard) whenever CDarwinEmbedKeyboard::hasExternalKeyboard()
  says a hardware keyboard exists (GCKeyboard.coalescedKeyboard), otherwise the native one (DialogKeyboardTouch).
  Patch (kodi-21.3-portrait.patch, GUIKeyboardFactory.cpp): iPhone always uses the native keyboard; a paired keyboard
  types into the same native field. Applies cleanly to Kodi 21.3 (git apply --check). patch_sha256 in source-lock
  changes when r30 is built and pinned.
- Settings search: the board-11 rewrite had dropped the native search field and used a Kodi edit control plus
  Action(Select) (rig: Kodi's keyboard over the results). Restored: with the glassbar the iPhone's own search field
  sits where the board's field is (y 340), results update as you type, keyboard raised on open; the edit control is
  only the fallback without the glassbar.
- Season prompt in download.py used Kodi's number pad (Dialog.numeric); now Dialog.input (native keyboard), digits
  checked. Kodi's own PIN/time pads (CGUIDialogNumeric) are not changed.

## ISSUE-163 — AirPlay takes 60-90 s to start on debrid streams (build 224, 2026-11-11)

Status: FIXED IN SOURCE; needs AirPlay r45; host-measured, device untested.
- Build-224 log: before the first picture the native side read ~27 MB of the episode at ~0.7 MB/s (2 MiB requests,
  2.6-3 s each, two in flight) while Kodi's paused player kept downloading the same link.
- Cause 1: FFmpeg's Matroska demuxer reads every attachment (anime releases carry 10-30 MB of fonts) while opening;
  AirPlay never uses them (burn-in renders with its own fonts). Patch ffmpeg-mkv-skip-attachments.patch skips the
  data (EBML_NONE seeks past it). Host check, FFmpeg 8.1.1: MKV with a 20 MB attachment, open+probe read 20,459,324
  bytes before, 196,608 after; plain MKV unchanged (131,072).
- Cause 2: the TV's source cache fetched 2 MiB blocks two at a time. Now 4 MiB blocks, four in flight, 24 kept
  (96 MiB). Test SlowLink (0.5 s per request, 24 MB in order): 2.0 s, four in flight; old profile two in flight.
- Not changed: stopping Kodi's paused player during startup. It would break "AirPlay stop returns to the same spot"
  (back_to_kodi needs the open video) and a cancelled start would wait ~25 s for Kodi to reopen this file.
- Regression: test_airplay_exports (SkipAttachments), test_remote_media (SlowLink), test_conversion_speed.

## ISSUE-164 — Uploads to Drive at ~0.3 MB/s (owner, build 224, 2026-11-11)

Status: CHANGED IN SOURCE; device untested.
- Owner's Speedtest (5G) 3.94 Mbps up = ~0.49 MB/s. Build-224 log (Wi-Fi, while an episode streamed): 1 MiB pieces at
  0.14-0.33 MB/s, each waiting for Drive's 308 before the next. Mbps vs MB/s explained to the owner.
- Season jobs upload two episodes at once (debrid_drive LANES=2): each lane has its own resumable session copy written
  back under one lock; the season folder is created under the lock; `current` shows one upload whose rate is both
  lanes (parallel=2); the other lane is `current_also`. A failed lane keeps the other's finished episodes and its own
  session; the job retries as before. Movies (one file) are unchanged.
- Piece policy (StreamChunks): aim at ~10 s per piece (was 3 s), cut only past 15 s, grow under 6 s. At 0.3 MB/s a piece
  is ~2.75 MiB instead of 1 MiB.
- Not changed: two different jobs still go one after another (one `current` per job on the pages).
- Regression: test_debrid_drive (TwoLanes: two in flight, both speeds shown, one lane failing keeps the session; chunk
  policy), test_transfer_efficiency (slow line now 0.1 MB/s).

## ISSUE-165 — Build 226: Umbrella AirPlay still never reaches the TV; show downloads use the old menus (2026-11-11)

Status: FIXED IN SOURCE; needs AirPlay r46; host-measured, device untested.
- Owner log 9e2568a7 (build 226, Dragon Ball Super episode at 9 min, debrid MKV): attempt 1 inspected in 36 s, then
  "no usable Wi-Fi en0 IPv4" and blamed Wi-Fi; the retry 20 s later had 192.168.1.24. Attempt 2: video segment 91
  converted in 7.2 s, but the independent audio reader's seek took 100,004 ms with 0 packets; the 100 s deadline
  expired. The source cache meanwhile read 757 MB at ~8 MB/s (four parallel reads worked).
- Root cause: Matroska cues index only the video track. The audio-only rendition (gm_stream produce_sel) seeked by
  the audio stream, so FFmpeg walked every cluster from the start to 9 min. Present since independent audio readers
  (it was the "audio -5" seen in builds 221 and 224). Fix: an audio-only rendition seeks by the video index (backward),
  then the existing time window drops audio before the segment. Host check, 10-min MKV (video-only cues): audio segment
  80 read 42.2 MB before, 0.6 MB after; audio output byte-identical for segments 0, 1, 37, 80, 99.
- Wi-Fi: the address check now looks for en0 IPv4 for up to 5 s before failing.
- Show downloads: the season menu and the season quality list were still the old text lists. Now board 3: heading
  "<show> · Season N", choices with a second line, and each quality with its coverage ("All 8 episodes" in green, or
  "6 of 8 · episodes 1–6 now; 7–8 wait for 4K Ultra HD" in orange). Still not built: the All Links page with badges
  (board 4).
- CI host suite first failed (23 checks: every h264_ac3.ts audio segment, "seek input"): MPEG-TS seeks by reading the
  seek stream's timestamps, which this reader discards. Fix limited to Matroska; MKV result unchanged.
- Regression: test_season_sources (Rows); host measurement recorded here; CI host suite covers audio renditions.

## ISSUE-166 — Build 229 owner test: slow AirPlay connect, wrong card text, resume card, show page, ugly pickers (2026-11-11)

Status: FIXED IN SOURCE (rig-checked where possible); AirPlay part needs r47; device untested.
- AirPlay (log 5331b718): the phone primed the resume segment (118, 11:53) in 15 s, but Apple's player then loaded
  segments 0-6 from the start (each converted, up to 45 s) and seeked to 11:53 only once ready, a minute later; then
  converted 117-119 again. Media playlists now carry #EXT-X-START:TIME-OFFSET=<resume>,PRECISE=YES so the receiver
  fetches the resume segment first. Host test: primed at 9.1 s, both playlists carry the tag.
- Card said "Opening the movie" for an episode and its poster tile was grey (never set): now "episode" wording, the
  show's poster, and "Show · S1 E1" as the subtitle.
- Resume prompt showed the spotlight's card (owner: "asks me to resume the show at the top"): the 11:53 offer was
  Dragon Ball's own; Kodi's resume prompt is the context-menu window and its card used the focused spotlight item.
  The card is hidden when the second row is Kodi string 12021 (Play from beginning). Rig: centred menu, no card.
- Show page: Play/Download text ran under their glyphs (fixed glyph x). Inline capsule (glyph + auto-width label in a
  centred grouplist); labels "Play/Download Season N". Season chips scrolled away: a pinned row (same folder) appears
  once the page scrolls (Container(9900).HasPrevious); tap selects that season (SetFocus absolute + Control.Move -1).
  Chips read "Season N" (were "S1 • Kazeka..."). Episode titles/plots now wrap (Kodi draws list labels on one line;
  textboxes wrap and show whole lines); show plot shows 3 whole lines (was 4, the last cut). Rig screenshots checked.
- Pickers (owner: "still ugly"): the approved round-3 boards were built as Kodi's select box with second lines. Now one
  bottom sheet (choice_sheet.py, IOSChoiceSheet.xml): art card with kind badge and title, rows with tiles, detail
  lines, BEST / ALL n / k OF n tags, coverage bars, blue Show All row, footer, separate Cancel capsule. Used by How
  would you like to watch (watch add-on), Pick a quality (deck picker), the season menu and season qualities.
  Rig: real TMDb Helper play flow opens it; Back, Cancel tap and a row tap answer correctly. (A rig-only Trakt sign-in
  prompt opened under it once and froze input; not reproducible after dismissing it.)
- Regression: test_choice_sheet (new), test_airplay_flow, test_show_scrolling, test_source_match, test_deck_picker,
  test_season_sources, host test_remux EXT-X-START check.

## ISSUE-167 — Uploads to Drive at ~0.3 MB/s on a 115 Mbps line (owner, build 229, 2026-11-11)

Status: CHANGED IN SOURCE; needs AirPlay r47; device untested (the cause is inferred, not proven).
- Owner: Speedtest 512 down / 115 up Mbps on Wi-Fi. Log 5331b718, 06:48-06:57 with nothing playing ("full speed", no
  slowdown): Drive copy read the source at 110-360 MB/s, but each upload PUT ran 0.12-0.23 MB/s per lane; two lanes
  together ~0.35 MB/s, the same total as one lane earlier, and the same as on 5G. A shared limit inside the app, not
  the line or Google. No cap applies when nothing plays (slowdown.CAP is only for video/AirPlay).
- Likely cause: Python's TLS sends a body 16 KB at a time and every step waits for the interpreter shared by all the
  add-ons' threads. Change: upload pieces go through kodi_http_send (KodiAirPlay, NSURLSession: connection reuse,
  HTTP/2) while the Python thread waits outside the interpreter; everything else keeps urllib. The log says which path
  is used ("uploads use system networking") and each piece says "system networking".
- Regression: test_native_http (status/headers/body/error mapping; only PUT pieces >= 256 KB go native; wiring),
  test_airplay_exports (export list includes kodi_http_send; the build fails without it).

## ISSUE-168 — Build 232: uploads and AllDebrid copies never start (owner log eabc204b, 2026-11-11)

Status: FIXED IN SOURCE (#19); device untested.
- Log eabc204b 09:57:06: `Thread-16 (drive_uploads)` raised `UnboundLocalError: cannot access local variable 'airplay'`
  at `playback_lib=airplay.cached_load(...)`. The owner's download (Maze Runner, 09:58:05) was queued and never copied.
- Root cause: ISSUE-167's change added `import airplay,native_http` inside `drive_uploads`. Python makes a name local to
  the whole function when it is imported anywhere in it, so the earlier module-level use of `airplay` (line 277) failed.
  The thread also runs phone uploads and the AllDebrid → Drive loop, so all transfers stopped.
- Fix: import only `native_http` there; `airplay` is the module imported at the top of service.py.
- Regression: scripts/test_service_scoping.py fails on the old code ("drive_uploads: airplay used at line 277, imported at
  295") and passes on the fix. Host tests do not start the service's threads, which is why CI missed it.

## ISSUE-169 — A season download from a complete-series pack queued the whole series (owner log 10b3eee1, build 252)

Status: FIXED IN SOURCE (#19); device untested.
- Owner: "My queue is over 500 as I tried to download season 1-3 of Naruto Shippuden and somehow it's downloading
  everything." Log 13:50-13:56: the season searches kept file results from inside complete-series packs ("Naruto
  Shippuden (001-500) [Complete Series + Movies] … Season 01 (001-032)/Naruto Shippuden Episode 001 Homecoming.mkv").
  Drive then received episode 001 onwards and the films (preparation lines 14:57-15:39).
- Root cause: alldebrid.pick for a season kept only SxxEyy-named files and, when none matched (absolute numbering),
  fell back to every video in the torrent, once per season job.
- Fix: a season takes SxxEyy names of that season, else files under a "Season NN" / "S01" folder; a pack numbered for
  other seasons gives nothing; more than 60 unknowable files is refused with "This version holds N videos (a whole
  series), not one season. Pick a season pack." Owner request: "Cancel all downloads to Drive" in the upload card's
  long-press menu (Notifications) and "Cancel All" in the Library status sheet of a copy, with a confirmation.
- Regression: test_debrid_drive SeriesPack (Naruto layout: season 2 takes its 21 files, films never), CancelAll.

## ISSUE-170 — Continue Watching cards from Library playback had the file's name and no picture (owner, build 252)

Status: FIXED IN SOURCE (#19); device untested.
- Owner screenshot: "the maze runner" and "phony" (S1, E1) with blank cards. Both were started from Library.
- Root cause: ios_library.play_downloaded recorded Continue Watching with the row's label (the release name) and no
  art or TMDb id (record_downloaded_movie took params only; episodes got art={}). The card is drawn from that record.
- Fix: play_downloaded records the Library's saved TMDb name, id and art (playback_details); drivelibrary keeps TMDb's
  own name ('name') in its art cache; an all-lower-case file name is capitalised until then. Existing cards heal when
  drawn (ios_continue.heal: missing art or lower-case name -> saved TMDb name and art, no network).
- Regression: test_library_pages (heal, nice_title, Phony name).


## ISSUE-171 — Drive streaming retries rejected credentials without refreshing (PR #19 review, 2026-11-12)

Status: FIXED IN SOURCE; host tested, device acceptance pending.
- Root cause: drive_proxy asked token(force) after HTTP 401, but service.py discarded force and token_source only
  refreshed near expiry. A rejected, unexpired token was therefore sent twice, with no refresh.
- Fix: wire the real Drive token provider into the proxy; accept the rejected token as a refresh hint. Serialize
  refreshes and reuse a token another reader already renewed. Refused-refresh and busy-server backoff still apply.
- Verification: test_drive_proxy (6 cases, actual token_source through local HTTP) and test_drive_signin (7 cases,
  concurrent rejection, existing expiry, busy/refused recovery). Synthetic accounts only; no live provider claim.


## ISSUE-172 — Drive size checks can read an entire movie (PR #19 review, 2026-11-12)

Status: FIXED IN SOURCE; host tested, device acceptance pending.
- Root cause: HEAD used an unbounded read of the one-byte Range response, including HTTP 200 when Range was
  ignored. A large movie could therefore be downloaded into Python memory just to learn its size.
- Fix: validate the partial Content-Range and read at most one byte; use Content-Length without any body read
  for HTTP 200. Close/discard unread responses instead of reusing their connection. Metadata transport failures
  now produce HTTP 502 instead of silently terminating the local request.
- Verification: test_drive_proxy 10 cases pass, including a synthetic 20 GB size, ignored Range, malformed or
  missing size, and upstream failure. The metadata fixture fails any unbounded read; no media is allocated.


## ISSUE-173 — Season quality discovery waits for every slow episode; Cancel waits for HTTP (2026-11-12)

Status: FIXED IN SOURCE; host tested, live provider/iPhone acceptance pending.
- Cause: sequential 120-second episode searches had no whole-scan budget and only checked Cancel between calls.
- Fix: source discovery has a 60-second total budget and 25-second individual waits. Offer only qualities actually
  observed within that budget; unseen episodes join the existing exact-quality retry plan after selection.
  The shared automatic-picker lane remains serial: parallel requests would overwrite its window properties.
- Active HTTP header/body waits now run through an interruptible transport. Cancel closes/shuts down the socket,
  and redirect/queue actions remain on the caller after the cancellation check. Engine startup waits also honor
  Cancel. Failed/canceled requests retain the existing late-response tombstones; canceled queue work removes
  unprocessed planned retries. No new UI layout or visible wording.
- Verification: 29 season/source tests, 14 speed tests, 30 episode-watch tests, 13 cloud-route tests and 6 auto-season
  tests pass. Real local HTTP fixtures deliberately stall headers/body (including Connection: close): cancellation
  and timeout return under 1.5 s and never follow a late download redirect. A synthetic clock verifies the total
  scan budget and strict-quality retries for unscanned episodes.
- Test repair history: the first test insertion put four existing methods under the wrong fixture; moved them
  back. Closing a previously leaked HTTP response exposed an old fake with no close(); completed the fixture.
  All affected suites pass afterward. No real account/media was used.


## ISSUE-174 — Copy-safe HEVC still converts live on Roku AirPlay (PR #19 review, 2026-11-12)

Status: SOURCE REPAIR + COMPILED HOST CHECKS PASS; new native AirPlay build and device acceptance pending.
- Cause: generic preparation's copy_video says whether the original picture can be carried, not whether every
  receiver route accepts it. A third-party AirPlay receiver can still select the H.264 compatibility rendition
  of an otherwise ready HEVC movie. Re-running generic preparation cannot fix that receiver-specific mismatch.
- Owner chose to keep 4K via Media Assistant instead of preparing a separate H.264 copy. When an inspected,
  supported HEVC source is being converted for a connected Roku, the controller verifies that exact receiver's
  4K capability and installed Media Assistant, then switches its route. It never guesses from a discovered TV.
  Peer + User-Agent are correlated in a new native log record; separate old log records cannot activate it.
- The new kodi_airplay_serve_copy API explicitly forbids picture conversion. Unsupported profiles, oversized
  pictures and Dolby Vision-only inputs fail closed; a Media Assistant failure restores the phone instead of
  trying H.264 or looping back to AirPlay. The existing direct Media Assistant and Apple TV paths retain their
  behavior. No original is replaced or uploaded. TV serving now receives Kodi's current position and primes
  that position; the existing EXT-X-START behavior requires the new framework too.
- Host checks: 68 TV/network controller cases, 9 TV/start cases, 29 remux Python cases, 3 export cases, 10 flow
  cases, 3 preparation-gate cases pass. Compiled native recommendations suite: 41 checks, 0 failures, including
  4K HEVC copy under an MFi receiver and rejection of unsupported video without conversion. Shell syntax, project
  and UI-guidance checks pass. Completed an older fake response's close() method exposed by response cleanup.
- Native iOS/Objective-C compilation and actual TV acceptance are not established by host checks. Current pins
  remain Kodi r30 / AirPlay r46. The automatic fallback requires the new exported copy-only API and correlated
  receiver record, so an old framework cannot misinterpret the mode as a request to convert.
- UI policy/project skill and relevant HIG writing/feedback/loading/media guidance read. Reuse existing Play on TV
  flow/error card; no layout, style or control added. New error sentence is plain; device visual review pending.


## ISSUE-175 — Remaining speed/reliability roadmap coverage (2026-11-12)

Owner requests every speed and reliability item in PR #19. The screenshot's 34 speed rows precede 1G.7/1G.8;
the current scope is 36 speed + 6 reliability/measurement rows. An implemented source repair is distinct from
its measured phone target; unknown causes and unmeasured hardware/receiver behavior cannot be marked proved.
- 1E.7: reviewed and imported 5acee50's idle polling changes. Visible/active work retains fast polling; idle
  loops back off. 6 fake-clock polling, 36 activity and 7 native UI tests pass. Existing packaging suite initially
  lacked Python 3.11 on PATH; use the retained Python 3.11 runtime for bytecode tests, rather than alter the app.
- Integration history: the donor branch's appended progress notes conflicted with the PR's newer notes. Both
  histories retained; source changes were clean. No native/IPA workflow or main merge authorized here.

- 1E.2: imported/reviewed a334592's staging-only removal of unused binary add-ons. Required imports and mandatory
  system-manifest entries are checked before deletion, with media/input/archive support retained. Packaging suite
  passes 13 cases under the matching Python 3.11 bytecode runtime. The donor test context referenced its separate
  Drive-service change; excluded that unrelated fixture until its own repair. No base installation is modified.

- 1E.3 (Drive portion): imported/reviewed 5804295, then corrected its blanket service filter to preserve configured
  exports and source/favourite integrations. Unused workers stop; the stream proxy remains. Unknown configuration
  fails conservatively by keeping its worker. Fourteen packaging tests pass, including saved exports/sources.
  Umbrella/account update services and the skin's required monitor are not blindly disabled.

- 1F.4: imported/reviewed 99ab30a's bounded three-lane season copying, per-file resumable sessions and truthful
  aggregate rates. Movies stay single-lane; two remaining episodes use two lanes. Tests: 33 debrid, 9 transfer
  efficiency and 29 season/source cases pass. More lanes are capacity, not proof of 1.5x speed on the phone.

- 3.3: found two remaining expiry gaps: the foreground bridge allowed only one renewal per movie, and queued
  copies waited for a full job retry when a resumed source URL expired. Renewals now coalesce with a 60-second
  cooldown instead of a lifetime limit; copy source reopen renews the selected file at the same offset and checks
  its name/size before accepting bytes. Original source selection and resumable upload sessions are preserved.
  New host cases cover a second expiry an hour later and a queued copy recovering without a job delay. This
  is a concrete recovery repair, not attribution of the owner's earlier hour-long stop.

- 1F.2 / 3.2: native HTTP now owns its upload bytes, bounds response buffering before/while data arrives, and
  enforces an absolute deadline with task cancellation (the old semaphore waited forever). A new capability
  gates bounded NSURLSession range reads for preparation and foreground media. Redirects cannot forward private
  credentials to another origin; ranges and renewed Drive credentials are checked. Old frameworks use Python.
  Seven native-adapter, 59 preparation, 14 renewal, 29 remux and 3 export cases pass locally. Foundation itself
  is unavailable on Linux: three real compiled transport/fault cases are added to the macOS candidate workflow.
- Validation history: the service excerpt fixture needed its new native_reader dependency; completed it. A
  stale exact-source assertion was updated to the actual constructor. The existing 24 MiB slow-link benchmark
  exceeds its 3-second wall budget on this execution host (new source 6.68 s; unmodified e6041ae baseline 9.47 s).
  Its byte-integrity/concurrency assertions pass; no performance acceptance or app regression attribution is
  inferred. The threshold was not weakened. Real provider speed and Wi-Fi/cellular handoff remain device checks.

- 1F.3: a capability-gated native range-to-PUT piece keeps media bytes out of Python. Native code checks exact
  source offsets/total, bounds memory, follows safe redirects without forwarding credentials to another origin,
  and applies one overall deadline. Python retains per-file sessions, confirmed offsets, pause/cancel, source
  renewal and receipt checks. An uncertain PUT is queried before retrying; no progress is invented.
  Nine adapter cases and 35 debrid cases pass, including a committed piece whose receipt is lost and a Python
  reader that fails if any video bytes reach it. Five real Foundation fault/copy cases are queued for macOS.
- Native candidate 43138216141 at 1de2395: framework compilation and the first three actual Foundation transport
  tests passed. This validates the bounded transport, not the later copy API or iPhone/TV performance. Linux
  native host job was still running at this checkpoint. No native release/pin or IPA was made.

## ISSUE-176 — Repeated Drive MP4 fragment-index reads (1A.3, 2026-11-12)

The lean proxy previously forwarded every mfro/mfra range to Drive, including unchanged prepared files on
repeat opens. Add a private persistent index cache, bound to fresh Drive ID/checksum/size/version/modifiedTime.
Capture only a complete validated mfra from the player's existing bounded EOF read; no extra movie prefetch.
Recheck identity before saving. HEAD/front opens validate live identity (immediate HEAD-to-front shares it);
within a playback, identity expires after five minutes. A changed version/checksum discards the saved index.
Index bytes are bounded to 2 MiB each, 8 MiB total, 64 entries; cache writes are atomic and optional. Network
waits do not hold the shared cache lock. Metadata gets one three-second transport attempt, then a 30-second
failure cooldown; streaming keeps its existing authenticated path. Metadata checks still require connectivity.

Validation: 22 new tests cover exact HTTP 206 ranges, restart reuse without remote index reads, same-size content
changes, version changes, mid-read changes, malformed/oversized/short/wrong ranges, bounded contexts/eviction,
disk failure, metadata timeout and fail-open streaming. Existing proxy 10, library 22 and service-scoping one
also pass. The first malformed-index fixture changed a valid track ID rather than the version byte; corrected
the fixture offset and retained the negative regression. Project checks pass. Logs contain only safe byte counts.
Actual iPhone opening-time improvement is unmeasured. No IPA or native binary/pin change.

## ISSUE-177 — AI Upscale (DEC-039/DEC-040): bugs found while building the measurement build (2026-11-12)

Found by the new host tests before any phone build; each is fixed, retested and kept as a regression test.

1. **The converter refused an upscaled copy before it started** ("video conversion: no H.264 encoder in this
   build"). Root cause: `kr_video_open` checks for the H.264 encoder up front (the live AirPlay bridge needs it); an
   upscaled copy only needs HEVC, which is checked when its encoder opens. On the phone both exist, so this would only
   have hidden on builds without H.264, but it blocked every host test of the path. Fix: skip the H.264 check while an
   upscale is set for the conversion. Retest: `remux/tests/upscale_host.py` 23/23 (Lanczos engine on the host:
   1280×720 HEVC, both audio and both subtitle tracks kept, tag read back, HDR and same-size refused, the setting used
   once, cancel mid-copy then a fresh copy). Protection: that test runs in airplay-remux CI.
2. **"All videos (my default)" copied the show's title and date into the default** (picture.apply). Root cause:
   `_clean` kept every key of the entry it was given, and the resolved show entry carries title/updated. Fix: `_clean`
   returns only upscale and saturation. Retest/protection: `scripts/test_picture.py` (13 tests; in import-review).
3. **The measurement results file was never written on a fresh profile** and the error was swallowed. Root cause:
   the add-on data folder may not exist yet; `open()` failed inside a bare `except: pass`. Fix: create the folder and
   log the reason if saving still fails. Retest/protection: `scripts/test_upscale_measure.py` (10 tests; in
   import-review).

4. **The measurement kept the Drive read-ahead for its video after the run.** Root cause: `upscale_measure` called
   `DriveStream.url()` (which registers the file) but never `forget()`, unlike the queue. Fix: forget in a `finally`.
   Retest/protection: `test_upscale_measure` `test_drive_read_ahead_is_let_go`.

Regression check: the existing remux host suite (run_host_tests.sh, KR_HDR_TESTS=1) passes with the r48 changes:
3341 checks, 0 failed. AirPlay r48 built with Xcode 26.3 / iPhoneOS 26.2 SDK (airplay-ios run 43263786191).

Not yet checked (needs the owner's iPhone, measurement build): the AI engine itself (model download, speed, heat,
battery, output size), Xcode 26 building the framework in CI.

## ISSUE-178 — Build Season leaves out episodes that exist, and sizes one from a box set (owner logs 77b35834, 7027e593, build 300)

Naruto Shippuden S1: episodes 1, 9, 17 and 22 "Not found in any quality", although Burst found 11 sources for every
episode; episode 5 read 4.1 GB. Rick and Morty S1: 3 of 11 left out the same way.

Root causes (all from the three-lane Build Season of PR #21):
1. **One shared identity slot.** Burst publishes the episode a search is for in one Home-window property; with three
   searches at once the version page read whichever finished last (log: two pages checked against S01E03 at the same
   millisecond; episode 1's page hid its own links as "wrong episode"; Rick and Morty: E02, E05, E08 reused).
2. **Unsafe lane fallback.** A page whose episode matched no lane answered into the first live lane, so another
   episode's lookup took this page's links and the real episode got nothing.
3. **Scan limit too short with three lanes.** Elementum answered episodes 9 and 22 in 22-26 s; the limit was 25 s and
   nothing retried.
4. **Box set out-seeded the single files.** The scan reported the best-seeded copy's size and the automatic pick did not
   prefer one-episode files over season packs / box sets, so episode 5 would also have downloaded a 4.1 GB box.

Fixes: source_match keeps the last 8 identities and a page takes only the one for its own SxxEyy (never another
episode's); deck_picker answers no lane when several are live and none matches; Build Season scans get 45 s in lanes
and one 60 s retry each, on their own, for any episode still missing; deck_picker.mark_multi marks links holding more
than the episode (season pack, range, box set by name, or > 3x the median size) and ranks them last for sizes and
automatic picks (still used when alone).

Retest: new tests in test_source_match (each page its own identity), test_deck_picker (no-lane page answers nobody;
one lane keeps the old behaviour; box set neither sizes nor picks the episode; box used when alone), test_season_sheet
(missed episode looked up once more; still nothing → left out). Each fails on the old code and passes now; the
related suites (auto_season, episode_watch, import_builder, customized_ipa) pass. Phone check: next IPA.

## ISSUE-179 — Build Season: every episode found but none queued (build 302, owner logs dab02446 / 0296adce / 1138649a) — FIXED on host, owner retest pending

After ISSUE-178 the scan works (build_scanned found 32/32, scan_retry found episode 9). The queue phase fails for all
32: episode_result queued:false, one queue_deferred TimeoutError, card "No episode could be added". For each episode
the picker logs "Choose a version (automatic): … S01E0N: <name>" and elementum_cloud then logs
"automatic pick refused (different version)" followed by "automatic pick refused (no matching automatic request)"
(elementum_cloud.auto_season → refusal(wanted, selected, choice)). So the queue receipt
(KodiIOS.AutoPick.Queued<lane>) is never written.
Also: for E01, E03-E08 the automatic pick was a file inside "Naruto Shippuden (001-500) [Complete Series + Movies
(1080p)] … Season 01 (001-032)/…" although WHOLE_SERIES / mark_multi should rank it last; check what auto_choose had
to choose from (strict_quality 1080p may have filtered every single-episode file).
Suspects to check first: (1) refusal() compares the picker's Result (`name` of the chosen link) with what Elementum
resolved (`choice`): for a file inside a pack the names differ → "different version"; (2) with three lanes, the
cloud route's lane lookup (auto_season loops lanes and checks each lane's Result) may test the wrong lane's Result;
(3) ISSUE-178's `_unmatched` guard must not affect the queue phase. Reproduce with a host test of
season_sources._build's queue phase + deck_picker.run(purpose='queue') + elementum_cloud.auto_season with three lanes.
Not fixed (session ran out); build 290 queued episodes one lane at a time, so compare with the pre-lane code.

Root cause (owner log 1138649a, build 302): suspect (1), and it was not only packs. Elementum's link names the torrent
its own way (the magnet's dn, else the search query), while the picker's Result `name` is Elementum's whole label line
with Torrentio's stats ("Naruto Shippuuden - 002 [1080p] dual audio 10bit.mkv 👤 10 💾 945.19 MB ⚙️ NyaaSi…"). Even the
single-file episode 2 was refused "different version". With no lane accepted, route's request_id check then logged
"no matching automatic request" and returned without the receipt. Yet route already had the answer: each lane's lookup
calls route(url, request_id=<that lane's id>), so the link's lane is known and the name test was never needed there.
Fix (elementum_cloud): auto_season(…, request_id) looks only at the lane whose AutoPick has that request id and calls
refusal(…, own=True), which skips the name comparison and still checks found, request id and (when the link carries
them) season and episode. Without a request id (a hand pick while a season runs) names are still compared, now with the
stats suffix cut and a file-in-pack vs bare file match, and a refusal logs both names
('different version (picked "…", Elementum "…")').
Pack question: the "001-500 Complete Series" file was chosen only where it was the sole 1080p copy the title/episode
check kept (E01: the other 1080p links were hidden as "no season/episode in the name"); auto_choose already ranks
WHOLE_SERIES last and E02 took the single file. AllDebrid's pick() downloads just that episode's file from the pack.
Retest: scripts/test_elementum_cloud.py SeasonQueueThreeLanes (three lanes, deck_picker.run answers each, Elementum
links named differently from the picker reach auto_season in shuffled order: every lane accepted; another lane's link is
refused "different episode"; a hand pick with a different name is refused with both names logged). It fails on the
old code. Related suites (episode_watch, auto_season, season_sources, deck_picker, debrid_drive) pass.
Regression protection: that test in import-review.yml (test_elementum_cloud already runs there). Phone proof: the owner's
next Build Season log should show episode_result queued:true and no "refused" lines.

## ISSUE-180 — AI Upscale test closes Kodi (build 302, owner logs 0afdfd7b / 1ff17f50) — guarded on host, retest pending

Symptom: Settings › AI Upscale test, "First 5 minutes, best AI engine", on Hell House LLC Origins (1920x1040) and Phony
S01E02 (1920x1080). Kodi closes seconds after "upscale: AI super resolution (image model, 4x), 1920x1080 -> 7680x4320";
the log just ends (no Python error), which points at iOS stopping the app, most likely for memory.
Root cause: this iPhone's support line says the AI models make 4x pictures only ("image": factors [4]; "video":
factors [4], fits 0 for 1080p; "fast": max 1280x1280, so not 1080p). kr_upscale.pick_factor falls back to the largest
factor when none is near the 2x needed, so "auto" took the image model at 4x: 7680x4320 frames in the engine's
half-float format (about 265 MB each, several held at once), then scaled down to 4K. Run 1 also logged "model download
failed (VTFrameProcessorErrorDomain error -19743)" at the moment the conversion opened, although the status said ready
10 s earlier (to look at with the native code; not the crash's cause on run 2, where the model was ready).
Fix (Python, no new framework): upscale_queue.pick_engine uses an AI model only when what it makes is no larger than
the size asked for (5 % slack); otherwise the test stops with the reason ("its AI models would make image model 4x =
7680x4320, more than 4K UHD …") and the background step marks the copy 'blocked'. On this iPhone that means 1080p and
720p videos cannot be AI-upscaled with Apple's models as they are; 540p and smaller can (4x = 4K).
Retest: test_upscale_measure.test_a_phone_with_only_4x_models_does_not_make_8k_frames (the owner's support line; no
conversion starts; compare mode skips the image model and still runs Lanczos) and test_upscale_cloud
test_only_4x_models_block_a_1080p_copy_instead_of_closing_kodi. Phone proof: the next test log should say why it
stopped instead of Kodi closing.
Open: a way to get 1080p -> 4K on a 4x-only phone needs native work (for example tiles of the frame through the
low-latency model, or the 4x model on a smaller source) and a new KodiAirPlay build; to decide with the owner.
Follow-up (owner: "i want 720 and 1080 to be upscaled"): KodiAirPlay r49 (staged) runs the low-latency AI model on
tiles. A 1920x1080 picture is cut into overlapping tiles no larger than the model's 1280x1280 (2x1 tiles of about
992x1080, 16 px shared margin); each tile is enlarged 2x, and the tiles' middles are joined into one 3840x2160 RGBA
half-float picture (about 66 MB), which kr_video fits and encodes as before. Tiles are cut with a clean-aperture
attachment and CropSourceToCleanAperture (no copy on the CPU); the join is a row copy. The 4x video/image models are
now refused natively too when they would overshoot. 720p gets 2x (2560x1440), then kr_video fits it to the size chosen.
Not compiled here (no iOS SDK): the airplay-ios run is the compile check, the owner's AI Upscale test log the proof
(speed, heat, joins). pick_engine already chooses the tiled fast model from the r49 support line ("fast" fits 1).

## ISSUE-181 — Build Season: one episode opened the version menu; card text cut (build 309, owner log 8bb997da) — FIXED on host

Result of ISSUE-179's fix on the phone: 31 of 32 Naruto episodes queued (episode_result queued:true) and Drive copies
started. Episode 9 was not: its version page ("Available streams for Naruto Shippūden S01E09 (2007)") came with no
identity ("not checked (the title being played is not known)"), so the picker opened the version menu in the middle
of the season (owner screenshot: "this menu also shows up as its downloading"). The card read "Adding to your do…".
Root cause: Burst's searches for episodes 8 and 9 finished in the same millisecond (11:38:21.393); both rewrote
source_match's shared KodiIOS.SourceMatch.Recent list and episode 9's entry was lost.
Fix: source_match.published lets a page that names its episode take a recent identity of the same show (title in the
page heading) with the page's own season and episode ('borrowed'); deck_picker.run never shows a menu for a page with
no identity while a Build Season lookup is running (that lookup gets nothing); season_sources._build tries every
episode not added once more on its own before the season is done ('queue_retry' event); the card says "Adding
episodes".
Retest: test_source_match (borrowed identity, other show refused), test_deck_picker NoMenuDuringBuildSeason,
test_season_sheet test_an_episode_not_added_is_tried_once_more; season suites pass. Phone proof: next Build Season log.

## ISSUE-182 — AllDebrid to Drive copies far below the line (build 309, owner log 31996cd8) — FIXED on host, r50 staged

Owner: "my upload and download are super high ensure there are no app caps" (Speedtest: 182 Mbps down, 101 up).
Log: 124 "Drive copy native" pieces, all on one thread, 8 MB in 2.9 s on average (~2.8 MB/s, ~22 Mbps), later
4-8 s a piece. Two caps:
1. One episode at a time. The three upload lanes (ISSUE-164, Roadmap 1F.4) only run the files of one job (a season
   pack); Build Season makes one job per episode, so a season copied one episode after another.
2. 8 MB pieces. Each native piece reads its range from AllDebrid, then PUTs it to Drive and waits for Drive's answer;
   with nothing overlapping, the fixed waits (first byte from AllDebrid, Drive's confirmation) dominate. The native
   copier refused pieces over 8 MB (kodi_http_copy), and StreamChunks was capped at 8 MB too.
Fix: debrid_drive.step takes up to two more ready one-file jobs (debrid_drive.companions: AllDebrid has them, their
file picked) beside a one-file job, so three episodes copy side by side; a companion's failure stays its own (tries,
retry_at), never the first job's. KodiAirPlay r50 (staged) takes pieces up to 32 MB (kodi_http_copy_max) and allows
up to 180 s for one; native_http.copier reads the limit (8 MB on older frameworks) and gives a piece at least 1 s per
MB; driveupload's native path grows pieces to that limit after three fast pieces.
Retest: test_debrid_drive (build_season_episodes_one_job_each_copy_three_at_a_time; a companion failing does not fail
the first), test_native_http (r50 32 MB pieces, older frameworks keep 8 MB, pieces grow to 32 MB). Phone proof: the
next log should show three "Drive copy native" threads and pieces growing to 32 MB.

## ISSUE-183 — Build Season downloads show as hash-named cards with no metadata (build 314, owner screenshot) — FIXED on host

Owner screenshot: Library › Downloaded TV Shows lists "3c90db2e052…" and "ee34425d559…" with no title or poster, and
the upload card names the hash; "awh man and i forgot meta data not working".
Root cause: Build Season's automatic picks often reach elementum_cloud.route with no torrent name (no magnet dn, no
query), so name fell back to the info-hash; the job's title, its Drive folder (Kodi Downloads › TV Shows › <hash>)
and the Library card came from it. Second, anime files number episodes absolutely ("Naruto Shippuuden - 002
[1080p].mkv"), so even in the right folder the Library could not tell which episode a file is.
Fix: season_sources.request puts the show's title in the automatic request's target; route names such a job
'<show> S01E02' with the show's title. debrid_drive.retitle gives jobs already queued under a hash the show's title
from the season plan (episode_watch, by TMDb id); rehome moves files already copied into a hash folder into the show's
folder (and trashes the empty hash folder); episode_name names an episode's Drive file '<show> S01E02 - <original>'
when the original does not say its season and episode (new copies and moved ones).
Retest: test_debrid_drive HashNamedJobs (retitle, move, rename, parse back to show/season/episode),
test_elementum_cloud SeasonQueueNames; related suites pass. Phone proof: after the next IPA, the two hash cards become
Naruto Shippūden with its episodes (the service moves them on its next AllDebrid step).

## ISSUE-184 — Copy speed on build 314: three lanes work, pieces ramp too slowly (owner log 4beafff6) — tuned on host

Build 314 (ISSUE-182 fixes) on the owner's 101 Mbps upload: three "Drive copy native" threads at once, 950 MB in
132 s = 7.2 MB/s (~58 Mbps), up from 2.8 MB/s on build 309; each lane ~2.4 MB/s (per-connection limit, AllDebrid or
Drive). Pieces started at 1 MB and needed most of the two minutes to double up to 16 MB.
Change: LANES 3 → 4 (a fourth connection adds about a quarter); native pieces start at 8 MB (every framework takes it)
and still halve after a lost answer. Retest: test_debrid_drive (four lanes; native copy resumes after a lost answer
with 8, then 4 MB pieces). Phone proof: four threads and 8 MB first pieces in the next log.
Also in the log: one "Drive source changed; preparation will rescan" for episode 2 at start (the file was still
arriving); the rescan then kept every episode unchanged (compatible). No action.

## ISSUE-185 — Downloads "frozen" in the background: iOS took the silent audio and it never came back (owner log ed63fe73, build 317)

What the log shows: copies ran well (8-16 MB pieces, three at a time) until 13:18:14 "audio interrupted by iOS; work
will resume when allowed". The silent audio that keeps Kodi working in the background came back only at 14:19:59
("running again after 3705 s", when the owner opened Kodi). In between, iOS throttled the app: from about 13:42 copy
pieces timed out at ~20 s, each timeout halved the piece size down to 1 MB, and the copy crawled from 0.1 % to 3.1 % in
32 minutes. No slowdown reason was set (nothing was playing), so playback throttling was not the cause.

Root cause: KodiAirPlay's keepUpdate() returned at once while `keepInterrupted` was set, so the add-on's restart
request every second (background.watch) was ignored. Only iOS's "interruption ended" (often never sent), or Kodi
leaving/returning to the screen, cleared it.

Fix (KodiAirPlay r51, staged): while work waits in the background, the mixable silent audio is tried again 15 s after
the interruption and every 10 s after that; a refused try stays interrupted until the next. Retest: test_airplay_remux
BackgroundRetry (fails on r50's code). Phone check on the next IPA: lock the phone with a season copying, play music
in another app, stop it; the log should show "silent audio running again after N s" within ~10-30 s, not an hour.
Also seen (not fixed yet): episode 006's preparation restarted from the beginning at 13:38 after 20 min of work while
throttled; and piece sizes recover slowly after timeouts. Both to recheck once the audio no longer drops.

## ISSUE-186 — AirPlay of an Umbrella stream: long start, then broken sound (owner log 3b94b426, build 319) — FIXED on host, r52 staged

What the log shows (The Lorax via Umbrella, 1920x1040 H.264, 27.8 Mbit/s): the stream reached the phone at about
0.6 MB/s, under a fifth of what the movie needs (3.5 MB/s). Video segment 0 (11.6 MB) took 18 s, segment 1 took 39 s.
Kodi's own playback of the same link buffered again and again afterwards ("Waiting while the video buffers" 10 times),
and the AllDebrid → Drive copy ran at 1 MB per 6-20 s, so the connection itself was slow at the time.
The TV (Apple TV, external playback on) asked for video segment 1 all along ("No response for media file in 6s"),
took audio segments meanwhile, and after 30 s the r6 "sound only" check took that for a TV that cannot decode the
picture: "the TV takes audio segments but no video ones (avc1.640029)", then "restarting in compat mode". An H.264
movie was re-encoded to H.264 on the phone from the same slow source: another 80 s with "presentation 0x0", the
picture lost and the sound out of step. The second try (16:28) took 18 s just to open the source and 36 s for the first
segment, and the owner gave up.

Root cause (the part we can fix): the sound-only check counted segments served, not requests still waiting, so a
slow source looked like a codec refusal. The slow source itself (Umbrella's host / Wi-Fi at that moment) is outside
the app.

Fix (KodiAirPlay r52, staged): kr_remux_video_waiting() counts video requests still being made; while the TV waits
for one, the player logs "the TV is waiting for a video segment the source has not delivered yet (slow source, not the
codec)" and never restarts in compat mode. Retest: test_airplay_remux SlowSource; test_play_on_tv_network updated.
Phone check on the next IPA: the same kind of stream should either play (late) or stay on the waiting line, never
"restarting in compat mode" for an avc1 movie. A faster source (a Drive copy, or a smaller Umbrella result) is the real
cure for a 28 Mbit/s file on a ~5 Mbit/s link.
Background in the same log: no queued work was left waiting with the app in the background, so r51's retry did not need
to fire (the "running again after 5494 s" line follows 2 h of foreground playback, where the silence is not used). The
Drive copy held while the movie played and buffered (by design: the video goes first) and resumed at 18:45.

## ISSUE-187 — Library status "Up next" out of order: E006, 002, 006, S1 E6, E4… (build 319, owner screenshot) — FIXED on host

Root cause: within the same priority the queue (prepare_downloads.order_key and library_view) broke ties by the job
key, which is a SHA-256 of the file's identity, so episodes came out in a random but stable order.
Fix: prepare_downloads.line_key sorts by show, season, episode (from SxxEyy, "Episode 006", "E004" or " - 002"; an
episode with no season counts as season 1), before the job key; the owner's own choices (Start now, ▲ ▼) still go
first. Retest: test_prepare_downloads EpisodeOrder. Also: test_work_state had a stale needle after the debrid_drive
rename (job → owner) and was not in the CI list; fixed and added to import-review.yml.
Not fixed here: the same episode can appear twice (two releases of episode 6 from different sources); that is the
source matching, to look at with the next log.

## ISSUE-188 — Season copy crawled on one lane for hours; "Invalid Drive confirmed position" (owner log 3b94b426, build 319) — FIXED on host

What the log shows: Build Season started four lanes at 16:01. Pieces timed out at 20 s and halved (8 → 3.8 → 1.8 MB).
At 16:02:37 and 16:02:56 two lanes failed with "Invalid Drive confirmed position"; a third ended silently (the job's own
episode: its error is only raised when every lane is done). From 16:03 to 19:17 one lane (one episode) copied alone at
1-4 MB per 5-20 s, and the season's other episodes waited.
Root cause: (1) after a timed-out piece, Drive went on to keep that piece's bytes, so its next answer confirmed more
than the piece just sent, which driveupload treated as fatal; (2) a lane whose episode failed dropped it for the whole
turn, and with nothing left in the list the lane ended.
Fix: driveupload accepts any Drive position up to the file's size and carries on from there (logs "Drive kept N MB more
from an earlier piece"); debrid_drive puts a failed episode back in line up to RETRIES_IN_RUN (2) times in the same turn,
its Drive session kept, before it waits for the next turn. Retest: test_debrid_drive LateBytes and
TwoLanes.test_a_lane_whose_episode_fails_once_tries_it_again_in_the_same_turn (both fail on the old code).
Also: a job still named after its info-hash with no saved season plan now takes its show's title from another job of
the same show (retitle; HashNamedJobs test) — the "ee34425d5595…" card. The slow pieces themselves matched a slow
connection at that time (Kodi's own playback buffered too), see ISSUE-186.

## ISSUE-189 — Downloads still named after the hash, the same episode queued several times, no posters (build 325, owner screenshots and log 7698974a)

What the screenshots show: Library › TV Shows lists "3c90db2e05217cc29aef549b4…" (1 copying) and
"ee34425d5595f37297bc8c94…" (31 copying) with no poster; Library status › Up next lists "Naruto Shippuden Episode 006
Missi…" three times, "Naruto Shippuuden - 002" twice (one already on Drive and converting) and "Download · S1 E4/E8/E9".
Root cause: (1) these jobs were queued by builds before 315 with the info-hash as their title; queuing the same
torrent again returned the old job without renaming it, and retitle only knew the season plan or a sibling job, and the
Library had no cached name for Naruto (its files went into hash-named folders), so the pages fell back to the hash or
"Download"; (2) the queue was de-duplicated per torrent only, so each Build Season or download from another version
added the same episode again.
Fix: retitle also takes the Library's cached name, TMDb's (by the show's TMDb id, cached in drive-library-art.json,
so posters follow; a failed lookup waits 10 min), or the release / file name (title_from_name); a new request for a
hash-named job renames it. queue() returns the episode already waiting from another torrent (same show, season,
episode); drop_duplicates removes not-started duplicates already in the queue (the one copying stays). Retest:
test_debrid_drive HashNamedJobs, Duplicates. Phone check: the hash cards become "Naruto Shippūden" with a poster; Up next
lists each episode once.
Also in the log: four copies at 0.2 MB/s each (8-20 s per 2 MB piece) while a conversion read from Drive at the same
time; the connection was the limit (see ISSUE-186). Not changed. Not fixed: an episode already on Drive under an
absolute number ("Naruto Shippuuden - 002") can still be queued as S1 E2 by an older job; it needs the Drive listing in
the queue check.

## ISSUE-190 — Stuck copy card, episodes already on Drive copied again, four slow lanes (build 325, owner screenshots, log 7698974a) — FIXED on host

- Stuck card ("Waiting for Google Drive · no answer for 23 min" at 0 % while other copies moved): the card is the
  'current' lane saved in the state; a new run's lanes did not always write over a lane of the earlier run. Fix: each run
  clears the old lane cards before it starts, and the status card shows whichever lane moved last (current or
  current_also). Tests: test_debrid_drive (old card cleared), test_work_state FreshLane.
- "Naruto Shippuuden - 002" on Drive and converting while S1 E2 waited to be copied: the queue never looked at Drive.
  Fix: drive_episodes reads the Library's saved Drive listing (number-only names count as season 1) and drop_on_drive
  removes a waiting episode job that has not copied anything when the episode is there; show_match makes "Shippūden",
  "Shippuden" and "Shippuuden" one show. Test: Duplicates.test_an_episode_already_on_drive_leaves_the_queue.
- Four lanes at ~0.2 MB/s with every piece timing out at 20 s, beside a conversion reading and writing Drive on the
  same connection: two lanes while a conversion runs (BUSY_LANES). The connection is still the ceiling (the log does
  not say Wi-Fi or cellular; the owner's screenshot shows 5G).

## ISSUE-191 — Season copies sent their bytes twice on a slow link (owner log ec3b0956, build 325, 24 min) — FIXED on host

What the log shows: four lanes for 24 minutes; each sent 143-203 MB in 104-111 pieces but Drive confirmed only 3-4 %
of a ~2 GB episode (~60-80 MB). 37-40 pieces per lane (about 40 %) ended at 20.2-21.6 s: the native copier's deadline
is max(20 s, 1 s per MB), which assumes 1 MB/s, and the lanes got ~0.1 MB/s each (~0.5 MB/s together). A piece cut
off at its deadline kept only what Drive had confirmed and the rest went again. One ConnectionError was retried in the
same turn (ISSUE-188 working). The conversion of "Naruto Shippuuden - 002" beside it failed with a Drive read error at
20:28 and waits for a retry.
Root cause: a deadline that does not follow the link's real speed.
Fix: driveupload.Pace measures the speed Drive confirms and gives each piece three times its expected time (20 s floor,
the framework's 180 s cap); debrid_drive's copier passes it on. The log line now says the deadline. Retest:
test_debrid_drive Paced. Phone check: "piece in … (deadline N s)" with few pieces at their deadline, and the confirmed %
rising about as fast as the MB sent.

## ISSUE-192 — Copies still slow: 4-6 GB episodes; two spellings of Naruto; empty hash folder; stray bar (build 327, owner log b2f10d1f and screenshots) — FIXED on host

What the log shows: the ISSUE-191 deadline works (4 of 57 pieces at their deadline; nothing sent twice). Two lanes
(a conversion was running) at ~0.13 MB/s each. The card says "S1 E3 · 3 % · 303 KB/s · 3 h 56 min left": ~4.4 GB for a
23-minute episode. Build Season's automatic pick took 1440x1080 10-bit H.264 releases of 4-6 GB, which then also need
converting for AirPlay. Owner asked whether downloading first and uploading last would help: no, the upload to Drive is
the slow side and the bytes go up either way (and it would need 4-6 GB of phone space per episode); smaller files help.
Fixes:
- deck_picker.auto_choose: at the same quality, a version that needs no conversion (not 10-bit H.264), then one of a
  normal episode size (EPISODE_GB: 1080p 3 GB, 720p 1.5 GB, 4K 10 GB) before a bigger one; a huge one is still taken
  when nothing else has the episode. Test: test_deck_picker SmallerEpisodes. Already queued picks are not changed.
- "Naruto Shippuden" and "Naruto Shippuuden" as two shows (titles from different release names): one_spelling gives a
  show's jobs one title (the TMDb one when known); files already copied move over (rehome). Test: one_title_per_show.
- An empty "3c90db2e05…" folder (0 episodes) stayed while its episodes copied into the show's folder: rehome now runs
  for renamed jobs that are not finished too, and trashes the old folder once it is empty.
- Library status: a flat purple speed graph under a conversion with no speed yet; it now shows only beside a speed.
- Up next: "Naruto Shippuden · S1 E1 · Naruto Shi…": a one-episode job's title already names the episode.

## ISSUE-193 — End-to-end check of season downloads: wrong file from absolute-numbered packs, removals undone, folders per release name (owner request, build 328) — FIXED on host

Owner: "before u push ipa ensure the show download system fully works". The desktop rig cannot reach AllDebrid or
Drive, so scripts/test_download_e2e.py runs the real queue, lanes, retries, naming, duplicate and Drive checks, rehome
and the status cards against a fake AllDebrid and a fake Drive that speaks Drive's HTTP (resumable sessions, folders,
moves, Trash), on the owner's situation: a complete-series pack named by absolute number with 32 episode jobs from an
old build titled by hash, episode 2 already on Drive in a hash folder, episode 6 asked for from two more torrents, a slow
link (timeouts with part kept, lost answers after Drive took the bytes, dropped connections), a conversion beside it and
the app closed mid-copy. It found three bugs the unit tests did not:
1. alldebrid.pick for an episode found no S01E06 in "Naruto Shippuden Episode 006 ….mkv" and copied the pack's
   largest file (its film) as "S01E01" for every episode: likely the 4-6 GB "episodes" on the phone. Fix: absolute
   numbers count as season 1 episodes; with several videos and none matching, nothing is copied (the job says so).
2. Jobs removed as duplicates or already on Drive came back at the next save (save merges jobs found on disk), so the
   ISSUE-189/190 removals never held. Fix: removed jobs are remembered (state['removed']) and never merged back.
3. A show's folder came from each release's file name ("Show/…", "Naruto Shippuuden/…"): the two-Naruto folders. Fix:
   an episode with its show's title goes into that show's folder.
Result: 4 scenarios (the owner's season, Pick Better Versions, a new Build Season, Up next order) × 20 fault patterns:
80 of 80 pass. Evidence class: host simulation, not the phone.

## ISSUE-194 — Absolute-numbered packs copied nothing past season 1 (found while checking, 2026-11-13) — FIXED on host

ISSUE-193's fix mapped "Naruto Shippuden Episode 006" to season 1 only; a season 2+ episode job on such a pack copied
nothing (and the source filter took "Episode 013" for S2E13, which is really S1E13). Fix: drivelibrary.season_counts
(TMDb's per-season episode counts, cached as counts:ID) and absolute_offset; debrid_drive passes the offset to
alldebrid.pick (episodes and season lists), and waits instead of failing while TMDb is unknown; source_match fills the
absolute number from TMDb when Elementum did not and, for season 2+, takes only that number. Retest:
test_download_e2e test_season_two_of_an_absolute_pack / test_season_two_waits_when_tmdb_is_unknown, test_source_match
LaterSeasonAbsolute.

## ISSUE-195 — Library status: one card for four copies, Up next out of order, slow scrolling, wrong time left (build 329, owner screenshots) — FIXED on host

- Four copies ran, one card ("1 working"): only 'current' / 'current_also' were saved and read. Every lane is kept
  (state 'lanes', with the job it copies); work_state._copies makes a card per lane; notices.uploads names each
  episode. Up next leaves out the episodes being copied and goes in episode order (debrid_drive.in_line, which the
  copier also follows). Rig: four cards, Working 4, Up next from E5.
- Scrolling "doesnt scroll far": the page rewrote ~1,130 window properties every 2 s (141 pooled rows x 8) plus every
  bar, each taking Kodi's GUI lock. Only changed values are written now. Phone check needed (the rig cannot fling).
- "About 16 min to go" with 31 waiting / "84 h": see E17 (work_state.copy_bytes_left).
Also from the same round: the picker (source_match) hid a file named after its pack ("[uP] … Vol.01 (…) [uP] … - 005")
as the wrong title, so episodes 5-6 got 4 GB upscaled copies (4a3ab1f).

## Build pipeline (2026-11-13)

- import-review builds the IPA only on Run workflow or the build-ipa label; every push runs the tests (owner: "one new
  build with everything not 1000").
- kodi-ios-portrait skips its one-hour build when the locked release exists from the same patch (a check job).

## ISSUE-196 — Library status: a long press closed the page; download rows had no menu; Show page Back dead; graph error hid rows (build 347, owner) — FIXED on host (rows) / OPEN (poster, refresh card)
- **Seen:** owner screenshot + log f96cd4bd (build 347). Holding the Working-on-now card showed Pause/Cancel but Library status had closed behind it. Holding a download/transfer row did nothing. IOSLibraryShow.xml control 9001 tapped 12 times, never handled. `Library status: [Errno 2] … extras/portrait/spark/spark-…` twice.
- **Root cause:** iOS delivers a long press as action 10 (also Back) plus 117; library_status treated 10 as Back. The Show window's round back button had no onclick and `Show.onClick` ignored 9001. Two open copies of Library status share the `spark` graph namespace and `GraphCache._tidy` deleted the other copy's folder; the exception aborted `refresh()` before the download rows were drawn.
- **Fix:** library_status.onAction reads 10/101/117 on a card (Working on now, Downloading and Up next transfer rows) as a long press with a 1.5 s debounce, else Back. `transfer_control.row_menu` gives copy/upload/Elementum menus (Pause/Resume uploads, Cancel this download, Cancel all…); `held` flag carried in library_rows.with_model. Show Back closes. Select/FreeUp ignore 10 on a row. GraphCache only removes its own stale folders or foreign ones untouched for 60 s; write retried once; graph failure no longer stops the row redraw.
- **Retest:** test_library_status LongPressCancel (fake Kodi: one menu per press, page stays open, cancel copy / pause uploads / Elementum resume, 10 off a card still Back), test_library_files ShowBack, test_build193_pages plot cache. Phone retest pending.
- **Still open (owner, same session):** (a) Downloaded TV Shows: Naruto Shippuden card has no poster; (b) remove the "Refresh Library" card from Downloaded TV Shows / Movies (ios_library.py ~line 641, the `if not show_page:` refresh item) since the page has a refresh button; (c) Free Up Space "Watched episodes" not wired (library_manager.model passes no watched set; library_delete.free_up_groups takes `watched`).

## ISSUE-197 — Downloaded TV Shows: Naruto with no poster; a "Refresh Library" card; Free Up Space › Watched never filled (build 347, owner) — FIXED on host

- **Seen:** owner (same session as ISSUE-196): the Naruto Shippūden card in Downloaded TV Shows had no poster; the
  grid ended with a "Refresh Library" card although the page has a refresh button; Free Up Space never offered
  Watched episodes.
- **Root cause:** (1) drivelibrary.remember_show records a downloaded show by TMDb id alone (`{'tmdb_id'}`) under its
  names; artwork() returned that cache hit as is, so the poster was empty and the show was never looked up. A folder
  named without the macron ("Naruto Shippuden") also missed the recorded "Shippūden" slot. (2) ios_library.directory
  always added the refresh item. (3) Nothing kept what was watched: Continue Watching drops a title once it is
  finished, and library_manager.model passed no watched set to the rows or to free_up_groups.
- **Fix:** artwork() fills poster, fanart and plot from show_details(tmdb_id) for such hits (cached or fetched) and
  caches the result; remember_show also records accent-free names. The refresh card is gone (the header button and the
  long-press Refresh Library stay). ios_continue.stopped() remembers each finished title's Drive file id / phone path
  (data['watched'], newest 2000); library_manager.model reads it and passes it to show, episode and movie rows and to
  free_up_groups.
- **Retest:** test_drive_library (tmdb-id-only hit gets its poster, cached, plain spelling too), test_library_refresh
  (no card, empty library renders nothing), test_watch_continue (finished Drive episode and phone movie remembered),
  test_library_files WatchedFreeUp (model → Watched episodes group). The whole import-review test list and
  check_project pass. Phone retest pending (the one IPA).

## ISSUE-198 — Network trouble ended copies and conversions for good; no way to tell Wi-Fi from cellular (build 350, owner logs 94711fae / b3c5d6eb) — FIXED on host

- **Seen:** 33 minutes with nothing playing: AllDebrid → Drive pieces fell to 1 MB at ~0.1 MB/s per lane (one Drive PUT
  of 1 MB took 16 s, 0.06 MB/s); preparation's Drive reads were 0 MB/s for over 5 minutes, then "Source read:
  Input/output error"; four compatibility checks timed out. The minute snapshot: 65 of 116 copy jobs "failed",
  8 of 29 preparation jobs failed. The log never said whether the phone was on Wi-Fi or cellular.
- **Root cause:** every error counted toward a copy's 20 tries (debrid_drive.step) or a conversion's back-off of up to
  an hour (prepare_cloud), including network trouble that goes away by itself (a dropped or switched connection, the
  phone asleep, Kodi closed, HTTP 5xx). After a long stretch of it, jobs ended "failed" for good although Drive kept
  their sessions. A copy waiting out its back-off did not notice a new connection.
- **Fix:** debrid_drive.network_error() classifies such errors; they wait 15 s, 30 s … up to 5 min (net_wait),
  never count toward giving up, and carry on from what Drive confirmed (copies) or the last mark (conversions:
  status 'waiting', net_attempts). revive() puts copies that had failed for network trouble back in line once.
  kick_on_new_link(): when the connection changes, waiting copies try again at once. Settings › Library › Download
  problems (copy_problems.py) lists what ended, with its reason, Retry All and Clear. The minute snapshot gains
  `network`: link (wifi / cellular), copy lanes and MB/s, preparation read MB/s, copies waiting for the network, and
  link_changed_from.
- **Retest:** test_debrid_drive NetworkTrouble (what counts; 50 drops never fail a copy and it finishes; revive once;
  problems / retry / clear; a new connection wakes waiting copies), DownloadProblemsPage, test_drive_prepare (an I/O
  error waits 15 s and the conversion then finishes), test_diagnostics (network summary). Phone proof: next log.
- **Already covered (checked):** Kodi stays awake with the screen off while any copy is unfinished (service `why`:
  debrid_drive.active), including copies waiting for the network; a killed app resumes copies from their saved Drive
  sessions and conversions from their marks; the picker already ranks 10-bit H.264 as "needs conversion" (PR #22).

## ISSUE-199 — Mobile data, a Wi-Fi switch and other apps: what the app did (build 350, owner log a0a4e492) — partly FIXED on host

Owner test 06:16–07:15: mobile data, then a better Wi-Fi source (~07:05), opening other apps meanwhile.
- **Copies:** 0.15–0.43 MB/s on mobile data with pieces stuck at 1–2 MB; after the switch 1.1–1.4 MB/s, pieces back to
  16 MB, and preparation reads 1–3 MB/s. Two lanes dropped together at 07:12:40 (ConnectionError) and went on. The
  switch itself was handled; ISSUE-198 (PR #23) also wakes waiting copies on the new connection.
- **Compatibility checks on mobile data:** 27 timeouts from 06:32 to 07:01, each marked the file failed and tried again
  60 s later, spending bandwidth on an optional check. **Fixed:** on cellular the checks wait for Wi-Fi
  (prepare_downloads.cellular_now; "compatibility checks wait for Wi-Fi" logged once); a check that hits network
  trouble is 'waiting' with the 15 s–5 min back-off, never 'failed'. Retest: test_compatibility_filter
  (on_mobile_data_checks_wait_for_wifi, a_check_that_times_out_waits_instead_of_failing).
- **Other apps:** at 06:25:17 iOS took the audio session ("audio interrupted by iOS") and Kodi was suspended for
  581 s: every copy and read stopped until 06:34:59. Two later interruptions recovered in 5 s and 3 s. The silent-audio
  method cannot stop another app from taking the audio. **Open (native):** iOS 26's BGContinuedProcessingTask lets
  user-started long work (our copies and conversions) carry on in the background with a system progress item; needs
  KodiAirPlay code and Info.plist task identifiers (ROADMAP R7).
- Harmless: TMDb Helper's missing log_tagger folder (GetDirectory, 15×), audio underflow warnings at start.

## ISSUE-200 — Copies use a fraction of a fast but high-latency Wi-Fi (owner log a0a4e492 + Speedtest, build 350) — partly FIXED on host

- **Seen:** owner: "1.4mb compared to 70 is crazy". Speedtest on that Wi-Fi: 441 Mbps down, 79.7 Mbps up (~10 MB/s), ping
  469 ms, jitter 216 ms. After the switch the copies ran at 1.1–1.4 MB/s with **two lanes the whole time**; Drive PUTs of
  4–8 MB took 1.6–17 s (0.5–2.5 MB/s each).
- **Root cause:** (1) two lanes is the cap beside a conversion (BUSY_LANES = 2), and a conversion ran most of the time;
  (2) lane learning kept the speeds measured on mobile data after the switch, so more lanes looked useless; (3) the
  ceiling was 4; (4) each piece reads its range from AllDebrid, then sends it to Drive, then waits for Drive's answer,
  one after another, and on a 469 ms line each request spends several round trips before data flows, so few serial
  connections cannot fill the uplink.
- **Fix:** LANES 6, START_LANES 3, BUSY_LANES 4, CELLULAR_LANES 2 (E16's crawl on mobile data); lane learning starts
  again when the connection changes. Retest: test_debrid_drive LaneLearning (up to six; a new connection forgets),
  TwoLanes (four beside a conversion, five files five at once).
- **Owner follow-up (7:19):** the 469 ms ping was a VPN; without it the same Wi-Fi tests 355 Mbps down, 115 Mbps up,
  22 ms ping. The lane changes still apply (two lanes beside a conversion was the cap either way); the next log, without
  the VPN, shows how close six lanes get to ~14 MB/s. If the phone uses a VPN, copies are limited by it.
- **Open (native, ROADMAP R10):** within a piece, start the Drive PUT while the AllDebrid read is still arriving (one
  streamed pass instead of read-then-send) and keep the connections open between pieces (no new handshake per piece).

## ISSUE-201 — One copy lane uses well under the line: read-then-send pieces (owner: "drastically speed up downloads") — fixed in code (AirPlay r53 pinned)

- **Cause:** kodi_http_copy read a whole piece from AllDebrid into memory, then sent it to Drive, then waited for
  Drive's answer: each side idle more than half the time, and pieces capped at 32 MB by the memory they held.
- **Research:** a server-side relay (Cloudflare Worker / VPS) would skip the phone, but AllDebrid is reported to refuse
  datacenter IPs and to flag several IPs at once (ElfHosted docs, a Trustpilot report); rclone confirms a plain URL
  always passes through the copying machine. The phone stays the copier; the known-good pattern is streaming the
  download straight into Drive's resumable upload (Node.js stream → resumable gists, rclone's chunked Drive upload).
- **Fix (r53):** each piece streams: the PUT starts at once and reads a 1 MB pipe (CFStreamCreateBoundPair) that the
  GET fills as bytes arrive (back-pressure: the GET waits when the pipe is full); a short or refused source ends the
  PUT short and Python asks Drive what it kept (existing path). Pieces up to 256 MB, starting at 32 MB when the
  framework streams (kodi_http_copy_streams). Redirects: https only, no source credentials to another host.
- **Pinned:** r53 built by airplay-ios run 43455191676 from 83ebc88; asset digest and downloaded zip both sha256
  10df323f…02b8; the binary exports kodi_http_copy_streams and kodi_http_copy_max.
- **Retest:** test_native_http (streams flag, 256 MB limit); the native code compiles in the airplay-ios run (macOS);
  phone proof: the next log's "Drive copy native" pieces (size, seconds) and the network line (MB/s per lane).

## ISSUE-202 — A finished conversion reads "Converting 79%" for 20 minutes while it uploads (build-350 log) — fixed in code

- **Evidence:** Naruto S1 E2 (CPU re-encode) made 47 of 47 units by 07:19:30; the job then showed "Step 3 of 3 ·
  Converting" at 79.48% past 07:42, Drive reads stopped, the worker heartbeat stayed fresh, and the conversion's
  own Drive pieces kept going up every minute ("4.0 MB piece in 14 s, 0.30 MB/s"). Not a hang: the converter was done
  and the upload backlog drained over a slow line, with no word of it on screen.
- **Cause:** the "Uploading to Google Drive" wording only showed while the converter was blocked on a full queue;
  after the last unit nothing said the rest was the upload. Movie pieces were also capped at 8 MB, a Drive round trip
  for every 0.6 s of a fast line.
- **Fix:** once every unit is made (stage 3, or n of n), the Sink reports upload_left / upload_total and the line
  reads "Uploading to Google Drive · N%" with "X MB left to upload" and a time from the upload speed; the bar holds at
  80 so the Drive check (82) never steps back. Movie pieces start at 1 MB and may grow to 32 MB (still aimed at ten
  seconds each, so a slow line keeps small pieces).
- **Retest:** test_drive_prepare (upload share after the last unit; 32 MB limit, 1 MB start; slow-upload test bound
  is MAIN_CHUNK), test_preparation_runtime (the wording, 300 MB left, ETA from speed).
- **Regression protection:** those tests in import-review.yml. Phone proof: the next log's preparation after its last
  unit shows the upload share rising.

## ISSUE-203 — The bell page showed one copy while the pill said "3 running" (owner screenshot, build 356) — fixed in code

- **Evidence:** the activity pill read "3 running · Uploading to Google Drive · 74%"; the bell's Notifications page
  listed only Inception under RUNNING NOW.
- **Cause:** the page had one upload card ('up.'), filled from the first copy; Library status and the pill already
  show one card per copy lane (work_state._copies).
- **Fix:** six copy cards (notifications_skin.cards(): 'up.', 'up.2.'..'up.6.', ids 9432 and 9441-9445, bars
  9471 and 9476-9480), each with its own poster, line, bar, tap (the speed graph) and long-press menu (cancels that
  copy). Same compact card, no new style.
- **Retest:** test_build193_pages (two copies fill up. and up.2.), test_hold_menu (9441/9445 are copy cards).
- **Visual check:** pending (desktop Kodi rig, then the owner's iPhone).

## ISSUE-204 — "It's doing Inception again?" and hash-named rows in Download problems (build 356) — fixed in code

- **Evidence:** log 96e194ae: "Inception: back in line (it had stopped for network trouble: write operation timed
  out)" at start; it then copied at 6 MB/s (77% of 4.4 GB by 08:42). Download problems listed another Inception with a
  source error and two rows named "45e2c1e0…".
- **What happened:** ISSUE-198 brings each copy that failed for the network back once. This Inception copy had never
  finished (0.5% confirmed at start), so copying it was right; but nothing stopped a revive or Retry when another
  source of the same video had finished.
- **Fix:** revive() and Retry skip a copy whose title, season and episode match a finished copy; problem rows with no
  title use the cleaned file name, else "Unnamed download", never the hash.
- **Retest:** test_debrid_drive (a finished Inception keeps the failed one from coming back or being retried;
  untitled rows).
- **Follow-up:** the Download problems page redesign is a mockup awaiting approval
  (docs/design/download-problems-mockups.html).

## ISSUE-205 — Download problems was a plain select list (owner: "that is ugly!") — fixed in code (approved mockup)

- **Evidence:** owner screenshot (build 356): "Retry All (2)", "Clear All (64)" and 64 rows, two named by hash, every
  reason cut off.
- **Fix:** the approved mockup (docs/design/download-problems-mockups.html) as a real page,
  portrait/IOSDownloadProblems.xml (copy_problems_page.py), filled by copy_problems.py:
  - a summary (can try again · new source · cancelled) and the segmented filter (All · Retry · Source · Cancelled);
  - rows grouped by what you can do, each with a poster, the title, what it is, a plain reason in the group's colour
    and one action (Retry · Find · Restart);
  - Retry N (white capsule); Clear Cancelled (red, behind an alert) on the Cancelled filter;
  - tapping a row opens the choice sheet with the whole reason (Find Another Source · Try This Source Again /
    Restart · Remove From List, which asks first);
  - the empty state.
  Find opens the title's TMDb search (movies or shows). Restart clears the old cancel request first. Retry and remove
  name a copy by its key (hash, season, episode, added), not its place in the list.
- **Retest:** test_debrid_drive DownloadProblemsPage (groups, plain reasons, colours, row ends, the Cancelled filter, the
  sheet's choices, one problem retried or removed by key, the page XML).
- **Visual check:** desktop Kodi rig renders of the All and Cancelled filters match boards A and B; the footnote height
  was raised after the rig showed its third line clipped. The iPhone check is still pending.

## ISSUE-206 — Copies stayed at 3 lanes on a faster line (build-356 log) — fixed in code

- **Evidence:** log 96e194ae: "network" snapshot copy_lanes 3 throughout at 13-17 MB/s; the owner's speed test:
  254 Mbps down, 180 Mbps up (about 22 MB/s). Each lane ran 4-7 MB/s ("32.0 MB piece in 5.5 s").
- **Cause:** lane learning remembered the 4-6 lane speeds measured on the slow VPN line, so 3 always looked best.
- **Fix:** each measured lane speed has a time; anything older than six hours is forgotten (a new connection already
  forgets all), so a line that got faster is tried with one more lane while each addition pays off (15 %).
- **Retest:** test_debrid_drive LaneLearning (old speeds forgotten, 3 → 4 → 5 → back to 4 on +2.5 %).

## ISSUE-207 — The Library file manager offered the grid on Movies only (owner, build 356) — fixed in code

- **Fix:** the list/grid button shows on TV Shows too; the grid shows each show's poster, "N ep · size" and its first
  state chip as the badge; a tap opens the show (board B). Each side remembers its own choice (library-view.json
  'movies' and 'tv').
- **Retest:** test_library_files (TV grid properties, per-side view memory, the button on both sides).
- **Visual check:** pending (the rig has no Drive library to show).

## ISSUE-208 — Cancelling the download queue and Library status's Refresh were slow (owner, build 356) — fixed in code

- **Owner:** "the refresh in the library status is super slow and deleting the download queue is also slow as hell, it
  needs to be instant; it seems it only refreshes after I press the refresh".
- **Causes:**
  - Cancel and Cancel All write a request at once. The copier applied it only on its next turn: after the running
    piece and its wait (20 s to 5 min). Until then every page read the copier's saved list, so the copies still showed.
  - The "copies waiting" count came from the service's last snapshot.
  - Refresh (the library check) asked Drive for each video's details one after another, hundreds of round trips, and
    saved the state file after every video.
- **Fix:**
  - The pages apply pending cancels to what they show (work_state.pending_cancels), so cancelled copies leave Library
    status, the bell and the pill at once, and the waiting count is recounted on every read.
  - The copier's wait wakes within a second when a cancel request is waiting.
  - A request with no unfinished copy left is forgotten, so the copier never spins on it.
  - The library check asks for video details eight at a time (prepare_downloads.fetch_metadata) and saves every ten
    videos.
- **Retest:** test_work_state InstantCancel (cancelled copies vanish before the copier runs; stale requests
  forgotten), test_prepare_downloads QuickCheck (eight at a time, order kept, a failed file reported).
- **Phone check:** pending: Cancel All on a long queue, and a Refresh's time in the next log.


## ISSUE-209 — Continue Watching had no way to tidy a title off the row without losing its place (owner request, 2026-11-13) — fixed in code
- **Seen:** owner screenshot (Ghost Soldier long press: Choose source, Resume from 00:00:52, … Reset resume position): "put a remove from continue watching, dont make it erase the continue from progress … if i watch it again it can show back up".
- **Cause:** the row (ios_continue.entries) listed every started title; the only ways off it were finishing it or Kodi's Reset resume position, which loses the place.
- **Fix:** long press › **Remove from Continue Watching** on every row (phone titles and Kodi library items). `ios_continue.hide` records the title in `continue.json`'s `hidden` map (key → time, capped at 400); `entries` leaves a title out while it has not been played since. The saved position, player and version are untouched. Playing it again updates `played`, so it returns, newest first. Route `?action=continue_hide` in default.py, then Container.Refresh (as ios_remove does). Icon: the existing "Remove" glyph in the skin's context menu (CTX_ICONS); no new UI.
- **Retest:** test_watch_continue (removed row keeps position 52 s and comes back after a new play; a library item by its file; the menu entry and route). Phone: hold a Continue Watching card › Remove; check the Home row refreshes at once (if not, it does on the next Home visit).

## ISSUE-211 — F3: a re-package read Drive at 3–7 MB/s while copies moved ~15 MB/s (PR #24 roadmap, build-356 log 68d43660) — fixed in code
- **Seen:** `preparation: Drive reads: … (2.93 MB/s)` … `6.80 MB/s` every minute for re-packages (Naruto `index_after_media`, Inception `not_mp4`), copies beside them at ~15 MB/s (roadmap Evidence table).
- **Cause:** drive_stream already fetched READ_AHEAD = 4 blocks (8 MB each) in parallel, and Drive serves one connection at about 1.5 MB/s on that line, so a read ran at about 4 × 1.5 MB/s. A re-package only moves bytes (picture copied), so its speed is the blocks in flight.
- **Fix:** `drive_stream.ahead_count(playback, slowed, wide)`: READ_AHEAD_WIDE = 8 blocks when the job is a re-package (`prepare_downloads` sets `stream.wide` from the probe's `copy_video`, cleared at each job start). Playback (2), a video / AirPlay playing (1) and the owner's pause (0) are unchanged; 8 blocks stay inside KEEP (24 blocks, 192 MB). Real conversions keep 4 (CPU-bound).
- **Retest:** test_slowdown WideReadAhead; test_conversion_speed's read-ahead check updated. Phone: the once-a-minute `Drive reads:` line during a re-package should rise toward the copy speed (needs the owner's log). test_conversion_speed's AV1Speed / QuickFirst failures predate this (native-source text checks; that file is not in the CI list).
- **Follow-up (same day):** the first commit set `stream.wide` only in `prepare_downloads.process_one`'s local-copy path; the phone runs `prepare_cloud.process_one` (native outputs), so it had no effect there. Now set in prepare_cloud after the probe and cleared at each job start; test_slowdown checks both paths.

## ISSUE-210 — F5: the picker did not prefer files that need no preparation (PR #24 roadmap) — fixed in code

- Seen: owner log 68d43660 (build 356, via the PR #24 roadmap): Naruto Shippuuden S1 E5 (index at the end) and Inception (MKV)
  were queued for a re-package that reads the whole file back from Drive at 3 to 8 MB/s. Whether an equal-quality MP4 was on
  offer for them is not in the log.
- Cause: `deck_picker.auto_choose` ranked by quality, HDR, codec, AV1, size and seeds, never by container, so among releases of
  the same quality an MKV could win over an MP4 that lands ready to play.
- Fix: `deck_picker.prep_cost` = (container: .mp4 / .m4v / .mov 0, anything else 1; picture: H.264 and HEVC 0, because
  preparation keeps their packets, 10-bit H.264 and AV1 2, reusing `slow_to_prepare` / `converts_for_tv`). It sits in the
  `auto_choose` score after the no-conversion and heavy-file terms and before size fit, seeds and source, so quality and the
  rule "Episodes without your quality are not downloaded in a lower one" come first; wording unchanged. (A first version
  ranked HEVC below H.264; that broke test_deck_picker's "seeds still matter" case, and HEVC is not re-encoded, so it was
  dropped.)
- Retest: test_auto_season NeedsNoWork (MP4 beats MKV; H.264 = HEVC before Hi10P / AV1; a lower-quality MP4 never beats the
  chosen-quality MKV); test_deck_picker, test_season_sources, test_season_sheet, test_source_match, test_download_e2e pass.
  Phone: the next Build Season log should show fewer `repack` preparations when MP4 releases exist.

## ISSUE-212 — Up next called every unread job "Convert", most of them re-packages (PR #24 roadmap ticket, build-356 screenshot) — fixed in code
- **Seen:** Library status Up next: 25 rows "Convert · 0.2–4.3 GB" while the log showed them to be re-packages (picture copied, only the container / index moved).
- **Cause:** `job['repack']` is set only when a job is read (`skip_compatible`, at its turn), so every job not yet read fell to "convert".
- **Fix:** `work_state.next_what(job)`: "faster start" for a known re-package (repack, or a probe with `copy_video`), "convert" only when the probe says the picture is re-encoded, "prepare" while it is not known yet. Used by Up next (work_state._next → Library status, bell) and the Transfers page (transfers.queue_lists). Wording only, no new colours, tokens or helpers (APPLE-UI-POLICY).
- **Retest:** test_work_state (next_what cases, Up next list), test_repack_label (prepare for an unread job), test_library_status.

## ISSUE-213 — Preparation stopped while a video played; the first check after opening the app came 12.5 min late (owner, build-356 log 7249de4d) — fixed in code
- **Owner (2026-11-13, F6 answer):** "Id like it all to be ready before i watch, if they are not prepared ensure they are in the queue to be prepared … preparing in the backround if im watching something else or if the app is in the background". Decision: F6 is closed as *no skipping*; every video on Drive that is not ready is queued (as today), nothing waits for Play on TV.
- **Seen (log 7249de4d, 08:38–09:31):** preparation idle from 08:38:46 (`scheduler … reason no_jobs`) until 08:51:08 while three videos already on Drive waited; the next ones joined within a minute of each copy finishing (09:02–09:11: copies done 23→52, preparation jobs 31→56), so the done → check path works. From 09:06 27 jobs waited behind one Inception re-package reading at 3–7 MB/s (`prep_read_mb_s`), the case F2 / F3 address.
- **Cause:** (1) the service's first `preparation.scan` was not forced, so a recent `last_scan` from before the app was closed delayed it; (2) build 208 (ISSUE-136) held the converter's upload (`Sink.hold`) and Drive read-ahead (`DriveStream.hold`) the whole time Kodi played, so preparation stalled during every video. ISSUE-137 later showed that freeze was the buffering dialog; background work was ruled out in build 209.
- **Fix:** the first scan after the service starts is forced (`checked_at_start`). New `slowdown.preparation_holding()` (only while Kodi buffers) for the converter's sink and read-ahead: while a video plays preparation keeps its SHARE (35 %) of the time and the 1 MB/s download cap (Gate), so playback keeps the line; AirPlay unchanged (slowed, never stopped). AllDebrid copies and phone uploads keep `holding()` (unchanged). In the background preparation already runs at BACKGROUND_SHARE of a core (app_state.Pace), the iOS limit.
- **Retest:** test_slowdown (preparation goes on for 'video', waits for 'buffering'; copies keep HOLD; first check forced), test_prepare_downloads, test_conversion_speed wiring. Phone: watch something with Up next waiting; Library status should keep moving slowly, and seeking must stay smooth (if it is not, that is the regression to report).

## ISSUE-214 — F2: one re-package at a time while 27 waited (PR #24 roadmap, build-356 log 7249de4d) — fixed in code
- **Seen:** from 09:06 one Inception re-package read Drive at 3–7 MB/s (`prep_read_mb_s`) and uploaded its output over one connection at 5–8 MB/s, while 27 jobs waited (snapshots `waiting: 27`, `eligible_jobs 15`) and copies used ~15 MB/s of a 22 MB/s line.
- **Cause:** the preparation queue ran one job (`process_one`, one `current` card); a re-package only moves bytes, so one connection each way was the limit, not the phone.
- **Native check:** kr_prepare.c's per-run state is allocated per call (source, plan, fragment writer); the shared settings (`marks_on`, audio / subtitle languages, keep image subtitles) are fixed configuration; only the AI Upscale box changes per call. New host test `test_preparation_parallel` (test_remux.c) runs three re-packages at once over HTTP and checks each validates and keeps the original packets.
- **Fix:** `prepare_cloud.process_one(q, keep_going, lane)`: lane None is the main lane (any job, heartbeat, `current` card); lanes '2' and '3' (`prepare_downloads.REPACK_LANES = 2`) take only known re-packages (`known_repack`: `repack` or a probe with `copy_video`, not under audit), claim their job in `q.running_slots` so no two lanes run one job, and write their card to `state['lanes'][N]`. Service: a worker per lane runs only while the main lane is busy, nothing plays (`slowdown.reason()` empty), the owner has not paused converting, no Prepare next / Keep request is pending, and no AI Upscale copy is being made (`q.upscaling`; the upscale step also waits until no lane runs, since it changes converter settings). Drive reads: each re-package lane's file is "wide" (`DriveStream.widen`), read-ahead 8 / 8 / 6 blocks for 1 / 2 / 3 lanes so the 24-block cache is never overrun. Status model: `work_state._lanes` adds a card per lane (kind repack, its own percentage), Up next leaves those titles out.
- **Retest:** test_repack_lanes (lanes claim distinct jobs, extra lanes never take a real conversion or an unread job, lane cards reach the model and leave Up next, read-ahead fits the cache, service rules), test_drive_prepare, test_slowdown, test_work_state, native test_preparation_parallel (airplay-remux CI). Phone: with several re-packages waiting, the log should show 2–3 `preparation: … opening Drive file` running together and `prep_read_mb_s` above the single-lane 3–7 MB/s.
- **Not done here:** Library status draws the main lane's card in "Working on now"; extra lanes show in the counts and the model, not as their own cards on that page (a layout change needs an approved mockup, APPLE-UI-POLICY).
- **Unrelated CI note:** airplay-remux.yml's macOS "Foundation HTTP transport" check fails on PR #23 as well: r53's `kodi_http_copy` refuses a non-https upload target (right for Drive) and the test's local stand-in uploads to http://127.0.0.1, so `test_copy_stays_native_and_preserves_range_after_a_redirect` gets -1 before any redirect. The product path is unaffected. Fixed in the test (2026-11-13): the guard is asserted present in the shipped source and lifted for 127.0.0.1 in the test build only; the stand-in reads a chunked streamed upload; a mismatched source range must send no bytes (the streamed PUT may open first). airplay-remux run 43477344783: the transport step passes.

## ISSUE-215 — F1: every re-packaged file crossed the phone three times (PR #24 roadmap, build-356 log 7249de4d) — fixed in code, device proof pending
- **Seen:** AllDebrid → phone → Drive (the copy), then Drive → phone → Drive again (the re-package): Naruto S1 E5 `index_after_media`, Inception `not_mp4`, both `copy=True`; 27 jobs in Up next behind them.
- **Spike result (the roadmap's open question):** no new native work is needed. The converter already writes a fragmented MP4 with its index (mfra) as a stream through `drive_prepare.Sink` (option (a) of the roadmap; this is the format every prepared file already has, and Kodi, the AirPlay bridge and the TV play it today). It only needed to read the AllDebrid link instead of Drive.
- **Fix:** `DriveStream.add_external(key, with_link)`: the local block proxy serves a file from another server through the same cache and read-ahead (no Drive token on those requests; an expired link is renewed by the copier's `with_source`). New `debrid_ready.copy`: probe the file through the proxy; if the picture is copied (`streamable_video`) and it does not open fast as it is (`fast_open` False), convert it straight into Drive's staging folder, verify it against the source (marker, size, picture, duration, tracks, seeks: the same checks as a preparation), then `drive_prepare.promote` it into the show's folder as `<name>.mp4` with the preparation marker. `debrid_drive.step(ready_copy=…)` offers each fresh file once (not one whose plain copy is already under way; at most READY_TRIES = 3 starts); the service wires it to the preparation queue's converter and stream. At most `debrid_ready.LANES` = 3 at once (the native test runs three).
- **Fallbacks:** a file that needs a real re-encode, or already opens fast, is copied as before (the fastest path for it). A converter or verification problem → the staged file is discarded and the file is copied plainly (`entry['plain']`), so a download never depends on this path. Network trouble / pause / cancel → raised to the copier as before; the upload carries on from its checkpoint (`resume_store`, slot `f1-…`). Setting **Make downloads ready while they copy** (Transfers, default on; `prepare_while_copying`).
- **Retest:** test_debrid_ready (ready file in the show's folder with the marker and nothing left in staging; plain copy for re-encodes / fast-opening files / converter errors; unverified output never placed; cancel; three at once; the proxy reads an outside link, renews it, sends no Drive token), test_download_e2e (`test_a_file_made_ready_on_its_way_is_not_copied_again` through the real `step`). Phone: the log should show `AllDebrid: … made ready while it copies`, no `preparation: … opening Drive file` for that episode, and it should play on the TV at once. If anything looks wrong, turn the setting off: the previous path is unchanged.
- **Not proven:** speed on the phone (the read goes through the Python block proxy and one Drive upload per file, not r53's native streamed copy; expected about the same per lane, with the second trip saved), and resume after the app is closed mid-file.

## ISSUE-216 — F4: copies and preparation split the line with no regard for what is watched next (PR #24 roadmap) — fixed in code
- **Seen:** build-356 log 7249de4d: copies ~15 MB/s, the preparation beside them 3–7 MB/s, whatever was being prepared; Up next went re-packages first, then by name.
- **Fix:** `watch_next.py` reads Continue Watching (continue.json, no network): each started episode and the next 3 of its season are "next to watch", matched by show / season / episode whatever the file is called (`debrid_drive.show_match`, so Shippūden = Shippuden = Shippuuden). (1) Preparation order: `prepare_downloads.order_key` puts them right after the owner's own choices (Start now, Prepare next, ▲▼), before all other work. (2) The line: while such a video is being prepared its card carries `watch_next`, and the copier caps itself at `PRIORITY_LANES` = 2 lanes (`debrid_drive.priority_running`) instead of 4, so the preparation gets most of the line; with nothing next-to-watch in preparation the copies keep their lanes. F1 (ISSUE-215) already makes most next episodes ready as they copy.
- **Retest:** test_watch_next (episode 5 started → 5–8 wanted, any spelling; order after owner choices and before other re-packages; cached reader follows the file; lane cap only for a fresh `watch_next` card), test_repack_label, test_prepare_downloads, test_download_e2e. Phone: needs the `network` snapshot (`copy_lanes`, `prep_read_mb_s`) while a next episode is prepared beside copies.

## ISSUE-217 — "Phony" listed twice on AI Upscale; cancelled seasons named by their hash on Download problems (owner screenshots, 2026-11-13) — fixed in code
- **Seen:** AI Upscale › Shows and movies: "Phony · 3 ep" and "Phony · 2 ep" as two rows. Download problems › Cancelled by you: "45e2c1e044af006c8fbf…" rows (Season).
- **Cause:** (1) `upscale_page.library` grouped by `picture.show_key`: episodes with a TMDb id went to `tv:<id>`, the others to `title:phony`. (2) `debrid_drive.problem_title` returned the job's title even when the title (and name) was the torrent hash, which Build Season jobs of builds 317-319 carry.
- **Fix:** a name-only group joins the TMDb group of the same show (`debrid_drive.show_match`), counts and episodes merged; different shows stay apart. A hash is never a title: the job's files (drive name, name, path) name it, else "Unnamed download".
- **Retest:** test_upscale_page OneRowPerShow, test_debrid_drive ProblemTitles; test_upscale_e2e, test_library_files, test_library_status pass.

## ISSUE-218 — Download problems: Clear on the "Cancelled by you" heading (DEC-044 board C) — built, rig-checked
- **Owner:** "I want a clear by the 'cancelled by you' under download problems so i can remove that list" (62 cancelled rows under the two fixable ones; Clear only existed inside the Cancelled filter).
- **Fix:** copy_problems.model gives the Cancelled heading `headclear='Clear'`; copy_problems_page draws a blue text link on that heading (status_ui.link, 118-unit hit area, ids 9500+slot), and onClick runs the existing Clear with its alert ("Clear N cancelled downloads?"). "Season · 1 episodes" now reads "1 episode".
- **Retest:** test_debrid_drive DownloadProblemsPage. Desktop Kodi rig render (evidence class: rig): All view with "CANCELLED BY YOU · 2 … Clear", hash-named season shown by its file name (ISSUE-217).

## ISSUE-219 — AI Upscale had no way to pause, cancel or reorder a copy (owner, 2026-11-13; DEC-044 boards A/B) — built, rig-checked
- **Owner:** "It wont allow me to cancel anything or open whats being done and overall looks poor".
- **Fix (engine):** upscale_queue gets a control file (upscale-control.json) the page writes and the service applies each pass (`apply_control`): `set_paused`, `cancel` (Cancel this copy / Remove from Up next → status `cancelled`, never re-added by `plan` until `revive` when the show's size is chosen again), `reorder` (an `order` field `next_job` and `up_next` follow), `cancel_all`. upscale_cloud: a paused queue makes nothing; a copy being made holds in place while paused (and stops if a video waits to be prepared, which goes first); Cancel mid-copy stops it and marks it cancelled. Originals are never touched.
- **Retest:** test_upscale_e2e OwnerControls (pause/resume, remove two from Up next, revive, cancel mid-copy, new order, cancel all).
- **Fix (page, boards A/B):** new windows drawn by upscale_main_page.py and filled by upscale_settings.py from upscale_page.main_view / copy_sheet / next_rows: IOSUpscale.xml (Making now card with the bar and a round pause/resume, Up next with Edit and up to three rows plus Show all, one row per show, Settings, This iPhone, Space → Free Up Space, red Cancel All Upscaling behind an alert; refreshes every 2 s), IOSUpscaleCopy.xml (the copy's sheet: poster, title, line, bar, stages, Pause/Resume and Cancel Copy behind an alert), IOSUpscaleNext.xml (Up next › Edit: – removes behind an alert, the lines icon opens Move to Top / Up / Down because Kodi cannot drag rows, Remove All, Done). A tap on an Up next row offers Make Next / Remove From Up Next. A copy saved without a file name takes its prepared video's name (the rig showed a blank "Making now" row). Choosing a show's size again revives its cancelled copies.
- **Rig (evidence class: desktop Kodi rig):** page, sheet and edit list rendered with the rig's sample copies; Edit had opened behind its parent (a full window from a dialog) and is now a dialog. Phone check pending.

## ISSUE-220 — Library status showed one preparation while three ran (F2; DEC-044 board D) — built, rig-checked
- **Fix:** library_page draws up to two lane rows (ids 9360+, bars 9370+) under the Working on now card, in the copy rows' card style with a purple percentage and bar; the card's eyebrow reads "WORKING ON NOW · N". library_status fills them from the model's lane jobs (work_state._lanes); tap opens the video's details sheet, long press gives the conversion menu (Pause converting / Cancel conversion) for that video.
- **Retest:** test_library_status PreparationLanes (two lanes → "· 3", 63 % / 22 %, none → as before, ids drawn). Desktop Kodi rig (`kodi_rig.py scenario lanes`, new): card plus two lane rows, each with its own bar. Phone check pending.

## ISSUE-221 — The Queue page still paged with Previous / More and had no posters (DEC-045 board E) — built, rig-checked
- **Fix:** new IOSQueueList.xml (queue_page.py), filled by tool_windows.open_queue from library_tools.queue_page_view: one scrolling list, "Downloading to Google Drive · N" then "Preparing for Kodi and AirPlay · N" (the main preparation, the extra lanes, then the line), posters, a percentage and bar on what moves. Edit switches the same window to edit mode: red – (stop a copy / keep a video as it is, each behind its alert), the lines icon on movable rows (Move to Top / Up / Down → prepare_downloads requests next / up / down), Done, and the red "Cancel All Downloads to Drive". A tap on a row offers Prepare Next / Keep as It Is (or cancels a copy).
- **Retest:** test_library_tools (one list with every copy, Edit + moves send down / up / next, the window's ids). Desktop Kodi rig (scenario lanes): list and edit mode rendered.

## ISSUE-222 — Favourites showed its title twice and a plain empty line (DEC-045 board F) — built, rig-checked
- **Fix:** settings_page.favourites_page: the header keeps the back button and drops its small centred title (the large one stays); the empty state is the star in a yellow-tinted disc, "No favourites yet" and "Hold a poster anywhere and choose Add to Favourites."; with favourites, the segmented All / Movies / Shows (notifications_skin.segmented, ids 9020+) over the same poster grid. favourites_rows.kind_of reads movie / tv from the favourite's link (TMDb Helper's tmdb_type, Kodi's videodb paths); a filter with nothing in it says "No movies in your favourites".
- **Retest:** test_profiles_favourites (one title, empty line, the filter's ids, kinds and filtering). Desktop Kodi rig: empty state and three favourites with the filter.

## ISSUE-223 — "Video preparation paused" for a video that is kept as it is (owner screenshot, Naruto Shippuuden S1 E16, build 360) — wording fixed; the track not yet identified
- **Seen:** Notifications: "Video preparation paused · Naruto Shippuuden · S1 E16: This file has tracks MP4 cannot preserve; original retained".
- **Cause:** kr_prepare refuses to replace a file when that would drop a kept-language picture subtitle it cannot save beside the MP4 (a DVD / VobSub subtitle) or a second video track (by design: never silently discard tracks in an in-place replacement). prepare_cloud already marks the job blocked (one more try through retry_image_subtitles), but the notice said "paused" with the converter's words.
- **Fix:** the notice is now "Kept as it is · <video> still plays in Kodi as it is; it has DVD picture subtitles or a second video track an MP4 can't keep, so it isn't made ready for AirPlay.", once per video (flag `kept_told`, kept across the retry), and Transfers › History says "kept as it is: …".
- **Open:** which track S1 E16 has: the log line's `video={…}` (cut off in the screenshot) lists the tracks; with it, dropping a non-kept-language DVD subtitle could be allowed in a later native release.
- **Retest:** test_drive_prepare test_a_track_mp4_cannot_keep_is_kept_as_it_is_with_plain_words (one notice across two passes, original untouched), test_image_subtitles.

## ISSUE-224 — Preparation stopped while AI Upscale made a copy (owner log 20d8a992, build 360) — fixed in code
- **Seen:** 09:57 Naruto S1 E15 failed ("tracks MP4 cannot preserve"); 09:58 an AI Upscale copy started (Hell House LLC), then Phony S1 E2 from 10:01 to 10:16 at 0.7 MB/s, while the scheduler counted 23 eligible videos and Library status showed nothing moving. Both copies ended in "Source read: Input/output error". Once upscaling stopped, preparation went through 20+ videos in minutes (23 MB/s reads).
- **Cause:** service.py started AI Upscale whenever `process_one` returned False, which a failed preparation also does, not only an empty queue.
- **Fix:** AI Upscale starts only when no video waits to be prepared (`upscale_cloud._prep_waiting`), and a copy being made stops as soon as one does (it starts again later; the owner wants everything prepared before watching). The page shows it waiting.
- **Also in this log, not a bug:** Naruto Shippuuden S1 E9–E16 (640x480 release) carry their English subtitles as a DVD picture subtitle (`other_image_subtitles: 1`, the only subtitle); the converter will not replace a file and drop it, so they are kept as they are (ISSUE-223 makes the notice say so). A release with text subtitles avoids it.
- **Retest:** test_upscale_e2e PreparationFirst (a download landing mid-copy stops it; it is made once the queue is empty), test_upscale_e2e, test_upscale_cloud.

## ISSUE-225 — Notification details showed raw errors twice and log lines with JSON; vague problems had nothing to do (owner screenshots; DEC-046 boards G/H) — built, rig-checked
- **Fix:** notice_help.explain turns a notice into plain parts: a title that names the video, one line for the list, "What happened", a "Nothing was lost" line when true, and up to three fixes mapped to things the app can do (Library page / Library status / Download problems / Accounts / Run Setup Again / Share the log / AI Upscale / Retry the copies / the notice's own action). Known errors: picture-subtitle files, preparation failures, copies (blocked sign-in, busy), setup, Drive sign-in, kept as it is, Trakt, AI Upscale ready; anything else gets plain words and Share the log. IOSNoticeDetail.xml: the plain view (card, white capsule, fix rows, Technical details ›) and, in the same sheet, Technical details (a facts table read from the failure line: step, video, picture subtitles, when; the kodi.log lines; Share Log). Notifications list rows wrap the title and line to two lines (textboxes, owner: "ensure text fits and its not just ...") and problems with a fix get a Fix button (9601+).
- **Not done from the mockup:** "Copy Details" (Kodi has no clipboard on iOS) and "Restart Kodi" (no reliable restart from a script on iOS); Run Setup Again and Share the log cover them.
- **Retest:** test_notice_log (the owner's three notices explained, copies and unknown problems, facts from a failure line, rows wrap and get Fix, the sheet's ids), test_notices, test_build193_pages. Desktop Kodi rig: list with Fix buttons and two-line titles, the sheet, Technical details.

## ISSUE-226 — Repair / Repair All did nothing for Naruto, preparation never retried, and Download problems did not list it (owner log a1729c16, build 361) — found, not coded
- **Seen:** 11:54:21 Repair on a Naruto Shippuuden episode, 11:54:25 show ••• › Repair All Problems; no preparation started afterwards (only library checks: "compatible video kept unchanged" ×20), scheduler `queued_jobs 0, reason no_jobs`. Download problems (11:56:53) showed no Naruto row although the show page counted problems.
- **Cause 1:** Repair sends the `retry` request; `prepare_downloads.apply_requests` resets status/attempts/error but not `blocked`, and every queue filter skips blocked jobs, so a video kept for "tracks MP4 cannot preserve" stays out of the queue for ever.
- **Cause 2:** the converter (kr_prepare.c) saves only PGS picture subtitles beside the MP4; Naruto S1 E9–E16's only (English) subtitle is a DVD/VobSub picture subtitle, so it refuses to replace the file.
- **Cause 3:** Download problems shows only AllDebrid copy problems; preparation problems live in Library status / the show page.
- **Plan:** ROADMAP "Preparation repair roadmap — 2026-11-13" P1–P6. Not coded (owner: findings only).
- **P1 fixed (branch claude/preparation-repair):** `prepare_downloads.apply_to` ('retry' and 'now') calls `forgive(job)`, which clears `blocked`, `kept_told`, `repack_failed`, `image_subs_retried` and `hdr_retried`, so Repair / Repair All puts a kept video back in the queue and it says what happened again. Test: test_drive_prepare `test_repair_puts_a_kept_video_back_in_the_queue` (a blocked job retried by request is queued, really runs again, and Start now clears it too). Device check pending.
- **P6 fixed:** Repair no longer looks like it worked when it can't. `prepare_downloads.cannot_prepare` names a video the converter can't keep the tracks of (DVD picture subtitles or a second video track) while the converter lacks the capability (`preparation-capabilities.json`, written by the service from `native.keeps_dvd_subs`, the `kodi_airplay_prepare_keep_dvd_subs` export P2 will add). Repair on one episode says why, that it still plays in Kodi, and offers Find Another Version; Repair All Problems retries the rest and gives one message for the stuck ones. The "Kept as it is" notice and its help page already said the same (notice_help `_kept_tracks`). Tests: test_library_files `RepairSaysWhy`. Device check pending.
- **P4 mockup (approved by the owner 2026-11-13):** docs/design/download-problems-mockups.html board E: a "Preparing for Kodi and AirPlay" group and Prepare filter on Download problems, a row sheet (Find Another Version · Try Again · Keep as It Is) and the Library status "can't be made ready" count opening it.
- **P4 coded:** Download problems lists preparation problems (`prepare_downloads.preparation_problems`: kept or stopped, not owner-kept, done or faster-start-failed). New "Preparing for Kodi and AirPlay" group, a fourth summary tile ("Not ready"), a Prepare filter, per-row Find / Retry, the row sheet (Find Another Version · Try Again · Keep as It Is, no red) and Try Again N. The service adds a Library status "N can't be made ready · Review" Needs-you entry that opens the page on the Prepare filter (`copy_problems,prepare`). Retry on a video the converter can't keep the tracks of explains why instead (P6). Tests: test_debrid_drive (`test_preparation_problems_are_listed_with_the_copy_problems`, `test_the_page_has_four_tiles_and_five_filters`). Desktop Kodi rig render of the Prepare filter matches board E1; the iPhone check is pending.
- **P2/P3 coded (native, KodiAirPlay r54 staged):** `kr_prepare.c` copies a kept-language DVD picture subtitle (`dvd_subtitle`, VobSub) into the MP4 as `mp4s` (FFmpeg's mov muxer stores it with its palette; checked with the FFmpeg CLI in faststart and fragmented modes) when `kodi_airplay_prepare_keep_dvd_subs(1)` is set, and leaves out a second video track no bigger than the main picture (noted in the converter log); a bigger one still refuses. The refusal now names the track: `...tracks MP4 cannot preserve (video track 1: mpeg2video 720x480); original retained` (the add-on still matches the same words). New fixtures (`h264_dvdsub.mkv`, `h264_second_video.mkv`, `h264_bigger_second_video.mkv`) and `test_remux.c` `test_dvd_subtitles_and_extra_video`. The host test and the iOS build run only in the airplay-ios CI (the code needs a newer FFmpeg than this container has; `kr_prepare.c` and the new test compile syntax-clean here apart from an unrelated FFmpeg-version error).
- **P5 coded:** `Queue.retry_dvd_subtitles` gives a video kept for tracks MP4 cannot preserve one automatic new try once the framework exports the DVD switch (`native.keeps_dvd_subs`); `FORGIVEN` includes `dvd_subs_retried` so an owner's Repair gives another. Tests: test_image_subtitles `DvdSubtitles` (added to import-review.yml).
- **r54 pinned:** airplay-ios run 43500839856 (30cacbe, host tests and iOS build passed) published kodi-airplay-r54; the release notes, asset digest and downloaded zip all give sha256 0a00cb69…06315 and the binary contains the DVD switch. **Open:** phone proof is Naruto Shippuuden S1 E9-E16 preparing by themselves and showing the DVD subtitle in Kodi.

## ISSUE-227 — Repair taps seemed to do nothing, then everything happened a minute or two later (owner log 0b5ecceb, build 368) — fixed in code

- **Owner:** "my taps did nothing for repair all or repair, it was just super slow to do anything for a moment."
- **Seen (13:15–13:19):** the worker made an AI Upscale copy of The Cat In The Hat from 13:15:44 to 13:17:38 (it then failed on "Source read: Input/output error"). The Repair requests sat in the request file until then; at 13:17:43 the scheduler showed 29 videos eligible (the Naruto set, back in the queue), then a library check ("Checking compatibility and faster opening", 58 videos, one at a time) used the worker for the rest of the log. The episode page ignored pending requests, so nothing changed on screen meanwhile. The Repair itself worked: r54 loaded (`dvd_subtitles: true`) and 29 videos queued.
- **Cause:** (1) AI Upscale started because nothing was waiting (the Naruto jobs were blocked) and a Repair does not stop it; (2) the show / episode page read the saved queue without the owner's pending requests (Library status and Download problems already applied them).
- **Fix:** an owner's Repair / Try Again / Start now / Prepare next stops a running AI Upscale copy (`prepare_downloads.wakes_work`, used as its keep-going in service.py; the copy starts again later); `library_manager.model` applies pending requests, so the episode row moves to "Converting" at once.
- **Retest:** test_library_files `RepairShowsAtOnce`.
- **Not fixed (found in the same log):** the AI Upscale copy failed with "Source read: Input/output error" after 2 minutes; and a Library status Refresh (an inspecting check) probes every video one at a time and holds the worker (ISSUE-208 made only the metadata requests parallel).

## ISSUE-228 — Hold on the AI Upscale copy closed the page; Cancel All Upscaling did nothing (owner, build 368) — fixed in code

- **Owner:** "if I hold down on a movie that is currently downloading it closes out the setting; I want the option to cancel instead of only pausing. And cancel all upscaling isn't working."
- **Causes:** a long press is a right click, which Kodi turns into "previous menu" (the page's Back); and Cancel All wrote a request that only the upscale pass applied, a pass that waits behind every preparation, while the pages never showed it and the Up next pages consumed requests the copy being made still had to see.
- **Fix:** a long press on the copy being made opens Pause / Resume, Cancel This Copy and Cancel All Upscaling (an Up next row: Make Next / Remove); pages show a pending cancel at once (`upscale_queue.preview`) and never consume it (`apply_control(keep=True)`); the service applies requests within seconds (`upscale_control` thread, except while a copy is being made, which sees them itself).
- **Retest:** test_upscale_cancel (new, in import-review.yml). Device check pending.

## ISSUE-229 — r54 wrote a prepared MP4 with the DVD subtitle and then rejected it: 30 failed conversions (owner log 5f05cd99, build 368) — fixed in code (AirPlay r55 staged)

- **Seen:** Naruto Shippuuden S1 E1, 3, 4, 7, 8, 9, 17-20: 30 attempts, each a full read and write on Google Drive, every one ending "Prepared video did not preserve resolution/HDR; original retained" at "Verifying the Drive file and seek index". The picture was fine (640x480, 8-bit, copied); the real cause was `kr_prepare_ready`, which accepted only text subtitles, so a prepared MP4 holding a DVD subtitle was "not ready". None finished in 39 minutes.
- **Missed:** the converter host test (workflow "AirPlay MKV remuxer", job host-tests) failed on exactly this on every commit of PR #26 (4 checks: the kept DVD subtitle, its palette, verification) and I read only the framework build, so r54 was pinned as checked. Both jobs are now read before pinning.
- **Fix:** `kr_prepare_ready` accepts `dvd_subtitle`; the test also asserts a prepared MP4 with a kept DVD subtitle counts as ready. **r55 pinned:** airplay-remux host-tests (run 43515845318, 3,3xx checks, 0 failed) and the framework build (airplay-ios run 43515845857) are green; release notes, asset digest and downloaded zip give sha256 5ba3eca8…23f1c94 and the binary exports the DVD switch.

## ISSUE-230 — Verification failures retried as full conversions; preparation ran on mobile data; Refresh held the converter; AI Upscale read errors failed the copy; small items (owner log 5f05cd99)

- **Final check:** a failed final verification (picture / ready / HDR mismatch, checksum) now stops after ONE attempt: `VerifyFailed` blocks the job, clears the staging files, notifies once and names the failed check ("The prepared file is not marked ready…", "The prepared picture is WxH, the original is WxH", "HDR changed…"). A re-package that plays shows as Ready; others stay in Download problems; Repair clears it. Network errors in the final check still retry. (Errors from the C-level `native.verify` still retry as before.)
- **Mobile data:** preparation does not start new videos on mobile data (Start now overrides); a running one stops cleanly and resumes from its mark when Wi-Fi returns; Library status says "Waiting for Wi-Fi · videos are prepared on Wi-Fi only".
- **Refresh:** an inspecting check no longer runs while a video is ready to prepare; the waiting videos go first, the request stays and the check runs when the queue is idle; a video inspected during the same request is not re-read after a stop or restart (a new Refresh still re-reads every file).
- **AI Upscale read errors:** a network-class error (including "Source read: Input/output error") leaves the copy waiting with "Waiting for the network" and a 15 s to 5 min back-off instead of failing it; permanent failures still fail. It restarts from the start (no resume mark yet).
- **Upload piece size:** the first main-track piece of a prepared file starts at the size the last good one reached (per link kind), not at 1 MB; a failure or slow piece forgets it.
- **Settings root "AI Upscale · On · 4K" when off:** the summary says On only when something is really set (Upscale new downloads on, or a show/default size), and "Unavailable" when the device has no AI engine; the root and the page pass the engine state.
- **"Control 9110 in window 13002 has been asked to focus, but it can't":** the AI Upscale show page's default control was its size segments, which show only after the page fills them; its default is now Back (the window id could not be mapped from the source, so this is the best match; pending a log check).
- **Retest:** test_drive_prepare (FinalCheck, MobileData, LearnedPieceSize), test_compatibility_filter, test_work_state, test_upscale_cloud, test_upscale_page. Device checks pending.

## ISSUE-231 — A season built at 1080p came in at 480p (owner, build 374) — fixed in code

- **Owner:** "why does it say Naruto is in 480p? I selected 1080 … 480p is ass, I never selected it."
- **Cause:** the automatic season pick took every episode from "Naruto Shippuden (001-500) [Complete Series + Movies (1080p)]". The 1080p is the pack's label: most of its files are 640x480 DVD episodes ("Naruto Shippuden Episode 001 Homecoming.mkv", 262 MB) and a few are the uploader's own upscales ("…_2.25x_1920x1080_alq-10"). The picker trusted the label; nothing checked each file.
- **Fix, before the download** (deck_picker `below_quality`, strict quality 720p and above): a version whose own name says SD (480p, 576p, DVD, SD…), that is an upscale of a lower quality (a "2.25x_1920x1080" scale, alq, waifu2x, ESRGAN, Topaz, "upscaled"), or whose file is far too small for the quality (bitrate under a third of the quality's floor; HEVC and unknown codecs judged leniently so small HEVC anime encodes still count) is never picked. A file named only "Episode 001" cannot be judged by name, so:
- **Fix, after the copy** (prepare_cloud, before any preparation): the copy job now remembers the quality chosen (automatic strict picks only); when the probed picture is clearly lower (1080p needs 1700 wide or 1000 high, so 4:3 and scope 1080p count), the copy ends failed "Not the quality you picked: 640x480, you chose 1080p" (Download problems, Find), the file goes to Google Drive's Trash (30 days), it is not prepared, the owner is told once, and the next automatic search for that episode leaves that version out.
- **Retest:** test_season_quality (new, in import-review.yml). Phone proof: a fresh Naruto season at 1080p.

## ISSUE-232 — A read-back during a dropped connection counted as a failed file; the card froze while the made movie uploaded (owner log 47e2276a, build 374) — fixed in code

- **Seen:** 9 Naruto episodes prepared in 22 min (done 28 → 37) with r55. E10's final read-back failed while Drive dropped the connection 7 times (-1005) and read "Prepared Drive file validation failed" (its 6th try). After the last unit, the card read "Making it start faster · 78.7 %" for 6 min while the made movie went up at ~1.3 MB/s.
- **Fix:** a read-back that fails while the Drive stream reports a read problem is network trouble (waits 15 s to 5 min, no attempt counted). Once every unit is made, each confirmed upload piece updates the card: "Uploading to Google Drive · N%" and what is left (`Sink.on_confirmed`).
- **Retest:** test_season_quality `UploadAndReadBack`.

## ISSUE-233 — Deleting videos mid-conversion left them in the preparation queue, failing every minute (owner log 1ae21097, build 374) — fixed in code

- **Owner:** "deleting stuff seems to bug out if it's mid conversion."
- **Seen:** Naruto was deleted around 15:14 while E24 converted; then every deleted episode (E10, E23, E25-E32) was opened again and failed "Drive video is unavailable or incomplete" (32 times by 15:20, attempts 1, 2, 3 …), each counted as a problem and holding the converter.
- **Cause:** neither delete path (Library › select and Delete, `library_delete.delete`; the long-press Remove, `ios_remove`) told the preparation queue, and a trashed or missing source counted as an ordinary failure.
- **Fix:** both delete paths ask the queue to forget the deleted videos (`prepare_downloads.forget`, a whole show folder included); a forget stops the running conversion of a deleted video (`interrupts`); a source that is trashed or gone (`SourceGone`: 404 or trashed) leaves the queue quietly instead of failing and retrying.
- **Retest:** test_season_quality `DeletedMidConversion`.
- **Also seen, not fixed:** an AI Upscale copy (Phony S1 E2, 1920x1080 to 4K) failed after 2 min with "video conversion: encode: Generic error in an external library" (the next copy carried on); "EXCEPTION: Window id does not exist" after a page closed (14:57, 15:14).

## ISSUE-234 — Library status Refresh did nothing while videos waited (owner: "library status doesn't really refresh, it's awful") — fixed in code

- **Cause:** ISSUE-230 made an inspecting check wait while any video was ready to prepare. That deferred the whole check, including the Drive listing, so with a season in the queue a Refresh listed nothing (new, removed or changed videos stayed as they were) and the page sat on "Checking…" until it gave up after 5 minutes.
- **Fix:** while the inspection waits, the Drive listing runs at once, once per Refresh (`scan(listing_only=True)`): the page shows new and removed videos and "checked just now"; the per-video inspection keeps its request and runs when the queue is idle.
- **Retest:** test_season_quality `RefreshLists`. Phone check pending.

## ISSUE-235 — Settings › AI Upscale still read "On · 4K" with Upscale new downloads off (owner screenshot, build 374) — fixed in code

- **Cause:** the row was right that something was on: a show was set to 4K (the log made 4K copies of Phony at 15:15-15:20). "On" did not say what.
- **Fix:** the row says what is on: "New downloads · 4K", "All shows · 4K", "1 show · 4K" / "N shows · 4K", "Off", or "Unavailable".
- **Retest:** test_upscale_page.


## ISSUE-237 — Repair took an uploader's upscale ("_2.25x_1920x1080_alq-10") for Naruto S1 E5/E6 (owner log f63389f1, build 376) — fixed in code

- **Seen:** 15:48:52 and 15:49:21 `Kodi iOS repair: S01E05 / S01E06 queued (any quality)`; the automatic pick took "Naruto Shippuden Episode 005 The Kazekage Stands Tall_2.25x_1920x1080_alq-10.mp4" (4.14 GB) from the Complete Series pack, and it was made ready while copying at 1920x1080. S01E06 was queued twice (two Repair taps 6 s apart; the copier keeps one per hash).
- **Cause:** Repair took its quality from the show's ready episodes (`library_repair.qualities`), and those were the 480p DVD episodes, so no quality applied, then the "any quality" pass ran. Without a chosen quality the ISSUE-231 checks (SD names, upscales, too small) never run. In a fallback, an upscale still ranked as 1080p (distance 0), ahead of a real 720p.
- **Fix:** `library_repair.chosen` uses the quality the owner chose for the show (episode_watch's planned episodes, then the show's strict preference), and the ready episodes only when nothing was chosen; `tries_for` drops the "any quality" pass after a chosen quality (the strict pick already falls back to the best available, with one notice). In a fallback, a version that only claims its quality (`below_quality`: upscale, SD name, far too small) comes after every real version, so a real 720p, then the original DVD episode, are taken before the same episode blown up 16 times; it is still taken when it is the only one.
- **Retest:** test_season_quality `RepairQuality`; test_season_sources now expects ISSUE-236's fallback (a strict pick with nothing at the chosen quality queues the best available, marked fallback), which PR check run 381 caught as the old "never lower" rule. Phone proof: the season re-download log.

## ISSUE-238 — A failed converter check (native.verify) still repeated whole conversions (handoff open item from ISSUE-230) — fixed in code

- **Cause:** ISSUE-230 stopped a video after one failed final check only for the add-on's own checks (picture, ready, HDR, checksum). The converter's check (`native.verify`: duration, every track, middle and end seeks over HTTP) raised a plain RuntimeError, so it counted as an ordinary failure and the video was made again after the back-off, each time a full read and write on Drive.
- **Fix:** `prepare_cloud.native_verify_problem` turns a failed `native.verify` into `VerifyFailed` (one conversion, the original kept, one "Kept as it is" notice, listed in Download problems, Repair clears it), except when it is network trouble (`debrid_drive.network_error`, or the Drive stream reports a read problem): that still waits 15 s to 5 min and carries on.
- **Retest:** test_drive_prepare `FinalCheck` (`test_the_converters_own_check_failing_stops_after_one_too`, `test_the_converters_check_during_network_trouble_waits`); `test_invalid_completed_temp_is_regenerated_on_retry` now regenerates through Repair instead of by itself.

## ISSUE-239 — "EXCEPTION: Window id does not exist" just after a page closed (owner logs 1ae21097 14:57 / 15:14, a1729c16 11:55:11) — fixed in the build

- **Traced:** in a1729c16 the line comes from thread T:2925927, the thread that logs `[plugin.video.themoviedb.helper]` at start-up: TMDb Helper's list-item monitor, not one of the app's pages (their refresh threads go through `live_window.Guard`, which never touches a closed window). When the window changes, the monitor empties its list on the window it last saw (`ListItemMonitorFunctions.add_item_listcontainer` → `xbmcgui.Window(self.cur_window)`); that was the page that had just closed, so Kodi raised and logged the exception, which TMDb Helper then caught. Harmless, but it read as a crash in the log.
- **Fix:** the build's TMDb Helper patch (`build_import_review.patch_listitem_tools`) checks `Window.IsVisible(id)` first and skips a closed window; skipped, not failed, if a later TMDb Helper changes that line.
- **Retest:** test_import_builder `test_tmdb_helper_checks_the_window_is_open_before_emptying_its_list`. Phone proof: no such line after closing Notifications in the next log.

## ISSUE-240 — Prepared files uploaded at ~1.3 MB/s while reads ran at 7–10 MB/s; pieces fell back to 1 MB after every dropped connection (owner log 47e2276a, handoff open item) — fixed in code

- **Cause:** a prepared file's upload is one resumable Drive session, so its pieces go one after another (Drive does not accept parallel pieces in one session); what a piece costs is the round trip plus its size. On a failed piece (a dropped connection, -1005, or a 5xx), `Sink._send_parts` judged the piece as slow over at least 6 s (`observe(len, 0, max(6, elapsed))`), which cut it toward 1 MB after a long drop, and `learn_piece(0)` made the next file start at 1 MB again. Seven drops in that log kept every piece small for the rest of the file and the files after it.
- **Fix:** a failed piece halves the piece size once (256 KiB aligned, never below 1 MB) and the next file starts from that halved size; three fast pieces double it again as before. Repeated drops still reach 1 MB. Build 376's log f63389f1 (no drops) shows 3.5–6.7 MB/s in total across the parallel uploads with pieces growing to 30 MB, so the drops, not the piece logic, were the slow part.
- **Retest:** test_drive_prepare `LearnedPieceSize` (`test_a_dropped_connection_halves_the_piece_and_it_grows_back`; a failure now leaves 8 MB learned from 16 MB, not 0).

## ISSUE-241 — An AI Upscale copy failed with "video conversion: encode: Generic error in an external library" (owner log 1ae21097, Phony S1 E2, 1920x1080 to 4K) — handled in code; cause not proven

- **What the error is:** FFmpeg's AVERROR_EXTERNAL from `avcodec_send_frame` (kr_video.c `send_conv`, "encode"), which the VideoToolbox encoders return when Apple's encoder session refuses a frame. iOS ends encoder sessions and GPU work (the upscaler runs on the GPU) when an app goes to the background, and under memory pressure; a new session normally works. The log was not available in this session, so which of these it was is not proven.
- **Before:** an ordinary failure, with the 5 min to 6 h back-off, and the copy started again from the beginning.
- **Fix:** `upscale_cloud._encoder_trouble` recognises encoder and GPU refusals (`Generic error in an external library`, `Insufficient Permission`, `kVTInvalidSessionErr`, -12902/-12903/-12905). Stopped in the background: the copy waits with "Waits for Kodi to be open" and is made when Kodi is on screen, never counted as a failure. Stopped on screen: one more try with a new encoder in 30 s ("Starting the AI engine again"); a second refusal on screen is a real failure with the usual back-off. The log line says whether Kodi was on screen, so the next log shows which case it is.
- **Retest:** test_upscale_cloud `test_an_encoder_that_stops_is_tried_again_not_failed`. Phone proof: a 4K copy that finishes; the log line names on screen / background if it happens again.

## ISSUE-242 — AI Upscale copies started again from the beginning after every stop (handoff open item) — fixed in code

- **Cause:** a copy is stopped often by design: a video waiting to be prepared goes first (ISSUE-224), the owner's Pause, Kodi closing, network trouble (ISSUE-230) and now an encoder that stops (ISSUE-241). `upscale_cloud` made its Sink without the resume store, so every stop threw away the work done (a 4K copy of a 23-minute episode is several minutes of GPU work and a large upload).
- **Fix:** the copy uses the same resume path as a preparation: `resume_store` keeps the Drive upload session and the converter's last mark (`Sink(spool, checkpoint, keep_pieces, on_checkpoint)`), and the next run calls `convert_to(..., resume=mark, upscale=...)` (KodiAirPlay's resume works with the upscaler: the copy's picture is an ordinary re-encoded track, and the mark's track layout is checked). The identity names the size asked for, the source's size and the bit rate, so a mark from another size never carries on; a mark that no longer fits (`ResumeFailed`) or a Drive session that is gone starts the copy again. Finishing, cancelling (Cancel This Copy / Cancel All) and a real failure forget the mark; a stop, network trouble and an encoder that stopped keep it. The log says "carrying on from N s".
- **Retest:** test_upscale_cloud `CarriesOn` (a stopped copy carries on from its mark and the mark is gone once it is ready; another size never carries on; a failure forgets the mark). Phone proof: a copy paused or stopped by a preparation that carries on instead of restarting.

## ISSUE-243 — Show page: the ••• menu let taps fall through and sent the owner out; rows showed the show's name; Select was bare (owner screenshots, build 384; DEC-047) — fixed in code

- **Seen:** tapping ••• on a show (Naruto Shippuuden) drew Home's artwork behind Kodi's menu, and the next tap left the page. Every row read "3 · Naruto Shippuuden" (the show's name), with no pictures and a big red Repair; Select listed "S1 E1 · 189 MB" with grey circles and no actions; Library status listed 140 ready videos that Library › Movies / TV Shows already show.
- **Cause:** the show page was a full Kodi window (`WindowXML`) opened over the Library dialog; `Dialog().contextmenu` then made Kodi draw and route taps to the window stack underneath. Episode titles came from the file name (`episode_rows` was never given TMDb's names, though the Library's art cache has them).
- **Fix (DEC-047):**
  - Board A: Library status no longer lists ready videos (no Ready list, no Ready filter); the summary keeps its count.
  - Board B: rows show the episode's TMDb still and title (`episode_meta` from the art cache, fetched once in the background for a season not cached yet), "E3" on the still, the title on one or two lines (`ep.N.two`, never "…"), one state line, a round outlined Repair; the third number becomes "N not added / need you" in red when something needs the owner. While Repair looks an episode up, its row says "Looking for 1080p…" at once with a ✕ that stops that search (`library_repair.mark_searching` / `cancelled`, Window(Home) properties read every 2 s).
  - Board C: the show page is a dialog and draws its own ••• menu (ids 9799-9804: Repair N Episodes, Find Missing Episodes, Pick Better Versions, Select Episodes, Delete Season…); a tap outside closes only the menu; Delete Season asks first and uses the same delete as Select (`delete_items`).
  - Board D: Select shows stills, titles, season chips, "N selected · size", and a toolbar: Better Version (looks the episodes up again at the show's quality; `better_version` lets the new download past the copier's "already on Drive" check and sends the old file to Drive's Trash once the new one is saved), Prepare Again (the retry request), Delete (asks first). Other lists (Free Up Space, Check Drive) keep the red capsule.
- **Retest:** test_library_show_menu (new, in import-review.yml), test_library_files, test_library_status, test_build193_pages, test_season_quality, test_speed_fixes. Desktop Kodi rig render: pending. Phone proof: the owner's next log.

## ISSUE-244 — Repair stuck on a dead torrent; six 640x480 episodes copied in full and then trashed; Download problems repeated a reason and drew a red square; no way to hide a problem for good (owner log 3df2f247 and screenshot, build 384) — fixed in code

- **Stuck after Repair (S1 E5/E6):** Repair goes through `season_sources.request`, which, unlike the automatic episode checks, never left out versions that had failed before. The pick for E5 was a torrent AllDebrid could not fetch ("File not available due to no peer", 16:25:43), and a Repair could pick it again. In the meantime the copier logged "left for its own turn (Problem)" for it every pass. **Fix:** `debrid_drive.avoid_names` (one helper for episode_watch and Repair): failed versions of that episode are never picked again; ones found lower than the chosen quality only when nothing else exists.
- **Copied, then trashed:** 16:15–16:19, E27–E32 from the "Complete Series (1080p)" pack were each probed as 640x480 on the copy-while-preparing path ("not made ready while copying (LowQuality …); copying it as it is"), copied in full anyway, and sent to the Trash by the after-copy check a few minutes later. **Cause:** `debrid_ready.copy`'s general error handler turned the refusal into a plain copy. **Fix:** a refused quality is raised to the copier, which ends the copy before anything reaches Drive (ISSUE-236's path).
- **The sheet said it twice:** "Not the quality you picked. Not the quality you picked: 640x480, you chose 1080p". **Fix:** `copy_problems.detail_text` shows the full reason once when it starts with the short one. "File not available due to no peer" now reads "No one is sharing this source".
- **Red square:** "Remove From List" set a red tile with no glyph. It has the trash glyph now.
- **Hide for good (owner: "one more option that clears it for good and only will show up if there is a different issue … for all problems"):** every row sheet in Download problems has "Don't Show Again" (grey tile, eye-slash; "It comes back only if something else goes wrong"). `problem_ignore` keeps {problem key: signature of its reason, numbers ignored}; a hidden problem shows again only when it fails another way. Library status' "N can't be made ready" count leaves hidden ones out.
- **Retest:** test_debrid_drive (Don't Show Again, the sheet text, no bare red tile), test_season_quality, test_debrid_ready.

## ISSUE-245 — AI Upscale made a copy by itself with Upscale new downloads off (owner log 3a30b6ef, 16:26, build 384) — fixed in code

- **Seen:** "upscale: 1 copy to make (4K UHD) … Naruto Shippuuden · S1 E2 — 1440x1080 to 4K UHD". Upscale new downloads was off. Owner: "I want full control over it".
- **Cause:** `upscale_queue.plan` made a copy of every finished video whose show (or all videos) had a size chosen, so every later download of that show got one too.
- **Fix:** a copy is made only of a video the owner asked for. Choosing a size on a show's AI Upscale page asks for the videos there at that moment (`upscale_queue.ask`; Off and Remove the copies take them back). Every new download gets a copy only when Upscale new downloads is on. Copies already waiting or made are untouched; to make copies of a show's later episodes, choose its size again.
- **Not changed:** the Picture menu on AirPlay still sets which copy plays; it does not ask for new copies.
- **Retest:** test_upscale_queue `test_a_later_download_gets_no_copy_unless_asked`, test_upscale_cloud, test_upscale_e2e (the page's choice now asks, as the app does).

## ISSUE-246 — Uploads sluggish while Rick and Morty episodes were made ready as they copied (owner log bfde8a13, build 384) — fixed in code

- **Seen (16:46–16:50, Wi-Fi):** three episodes (S01E01–E03) made ready while copying at once; their uploads ran at 3.7–5 MB/s together (~1.3 MB/s each), pieces of 4–8 MB taking 4–9 s, while plain copies had measured 13.6 MB/s on the same line. The first unit took 20.3 s for 30 s of film (later units 1.3–1.8 s). Meanwhile a Refresh's file inspection re-read the library ("Checking compatibility and faster opening", "compatible video kept unchanged" 47 times in 4 minutes), probing through the same converter. The interface was fine (interpreter wait p95 5–6 ms).
- **Causes:** (1) ISSUE-230/234 made a Refresh's inspection wait for queued preparations, not for downloads being made ready while they copy (F1); (2) a made-ready upload's pieces grew only after three pieces under 6 s, which a line shared by three uploads never gives, so each upload paid a Drive round trip every few MB.
- **Fix:** `debrid_ready.active()` counts the copies being made ready; while any run, a Refresh lists Drive at once and keeps its file inspection for later (`listing_only`), as with queued videos. In `drive_prepare.Sink`, a steady piece (6–15 s) grows the next one toward about ten seconds at the speed it just had (never above 32 MB); slow pieces still shrink, drops still halve (ISSUE-240).
- **Retest:** test_debrid_ready `test_a_refresh_inspection_waits_while_copies_are_made_ready`, test_drive_prepare `test_steady_pieces_grow_toward_ten_seconds` (it also caught a name clash in the first version that ended the upload early). Phone proof: a season made ready while copying, with a Refresh during it.

## ISSUE-247 — Refresh re-read every video, even ones already good to go (owner: "make a smarter refresh system") — fixed in code

- **Before:** every Refresh opened every video on Google Drive (a few seconds each through the converter: 47 in 4 minutes in log bfde8a13), by an earlier owner rule ("a new Refresh still re-reads every file").
- **Now (DEC-048):** Refresh lists Drive at once (eight metadata requests at a time, ISSUE-208) and opens only the videos that are new, changed (id, checksum, size or version differ from their last check), not done, kept, blocked, waiting for a faster start, whose last check failed, or that were checked by an older version of the checks (`INSPECT_VERSION`, raised whenever the checks change). A settled video (`prepare_downloads.settled`) keeps its stored check. Holding Refresh offers "Check Every Video" (asks first), which reads all of them as before (`request_check(inspect='full')`; an automatic request never downgrades it).
- **Retest:** test_compatibility_filter (`test_smart_refresh_reads_only_what_is_new_changed_or_not_ready`, `test_a_full_check_rechecks_the_actual_file_even_after_restart`, `test_refresh_reads_each_listed_video_once_until_it_changes`, a restarted Refresh).

## ISSUE-248 — "Drive source changed; preparation will rescan" right after a copy landed; "Control 32503 … can't" in every log (owner logs 3df2f247, 6984524f, bfde8a13) — fixed in code

- **Source changed:** seconds after a download was saved, its preparation failed with "Drive source changed" and waited for another library check: the copier names and files a new download just after saving it, which changes Drive's `version` but not the video. **Fix:** when the Drive record differs only in name, folder or version (`prepare_downloads.same_content`: same id, checksum and size) and nothing has been made yet, preparation carries on with the current record. New bytes are still a changed source.
- **Control 32503:** the version picker's page asked Kodi to focus its list before the picker had filled it. **Fix:** the page opens on Back (32500); `deck_picker.fill` focuses the list once its rows are in.
- **Retest:** test_drive_prepare (`test_a_rename_right_after_the_copy_does_not_fail_the_preparation`, `test_new_bytes_are_still_a_changed_source`), test_library_show_menu `VersionPickerFocus`.

## ISSUE-249 — Desktop Kodi rig render of the DEC-047 pages found layout faults (2026-11-14, evidence class: desktop Kodi rig) — fixed in code, re-render partly done

- **Show page:** a title that fits on one line was laid out as two (status line too low). Wrap cut-off is now 28 characters, 20 beside Repair (`library_manager.TWO_LINES*`). Re-rendered: OK.
- **••• menu:** the card behind it was missing (Kodi takes no window property as a height). Each row draws its piece of the card (`row_back`, `menu.N.pos`). Re-rendered: OK, matches board C1. Tapping outside closes only the menu: OK. The ••• focus highlight was a square over the round capsule; now a fade. Not re-rendered.
- **Select:** the size line sat far below one-line titles, and two-line titles ran into it (`it.N.two`, 30 characters); the empty check drew as a filled dot, then as a broken ring (now `circle_line.png`). Re-rendered: OK, matches board D1.
- **Choice sheet tiles (Download problems):** "Don't Show Again" and "Remove From List" drew bare coloured squares because the glyph was a bare name; `choice_sheet.glyph_path` adds the skin's icon path. Its grey line is shorter. **Not re-rendered yet** (interrupted).
- **Retest:** test_library_show_menu (`SheetGlyphs`), test_library_files, test_choice_sheet. Rig: re-render the Download problems sheet.
- **Seen, not changed (older page):** Download problems row titles end in "…" ("Naruto Shippuuden · S…"); the owner dislikes "…" (DEC-046).
- **Rig re-render (2026-11-14, desktop Kodi rig):** the Download problems choice sheet shows the eye-slash (Don't Show Again) and trash (Remove From List) tiles, no bare squares; the show page's Select · ••• capsule with focus on ••• has no square highlight. Phone check pending.

## ISSUE-250 — Download problems listed 13 Naruto problems while the show's card said 2 (owner screenshots and log 2095825c, build 393) — fixed in code

- **Seen:** TV Shows › Naruto Shippuuden: "28 ready · 2 problems · 21 copying"; Download problems: about 13 Naruto rows ("No one is sharing this source", "Not the quality you picked"). The log: 16 failed copy jobs, 21 copying.
- **Cause:** Download problems listed every failed copy job, once per version tried, including episodes since copied from another version or being copied again right now. The card counted each episode once and left out those on Drive (but counted ones being copied again as both copying and a problem).
- **Fix:** one rule on both: an episode (or movie) is a problem only while no other version of it is copying, waiting or done, and it is listed once (its latest failure). `debrid_drive.problems` and `library_files._copying_episodes`.
- **Retest:** test_season_quality `ProblemsAgree`; test_debrid_drive updated (a failed Inception is no longer listed beside a finished one).

## ISSUE-251 — Play on TV: the progress card goes, Apple's AirPlay list opens at once (owner, build 393) — fixed in code (AirPlay r56 pinned)

- **Owner:** "I would like this page removed everywhere and have it open straight to the AirPlay list instead of the ugly loading screen"; also "investigate why an Umbrella stream takes so long to AirPlay"; and "remove Media Assistant and just have it open to AirPlay".
- **Done so far:** `cast.py` hides the progress card (`QUIET_PROGRESS`) and calls `kodi_airplay_open()` right after `kodi_airplay_play`; the framework opens the list again only when no AirPlay output is chosen (needs r56).
- **Open:** the test updates (test_play_on_tv_network: 6 failures expect the card), the r56 release, the phone check, the speed-ups and the Media Assistant removal: docs/HANDOFF-PR26.md "Play on TV work in progress".
- **Done:** tests updated (the card's deadline/cancel tests run with the card on; `QuietPlayOnTV` checks the owner's flow). **r56 pinned:** airplay-ios run 43545050950 and airplay-remux host-tests (run 43545050788) green; digest 91be96af…416f7 checked by download.

## ISSUE-252 — Play on TV goes straight to AirPlay; Media Assistant is no longer used (owner, build 393) — fixed in code (Media Assistant kept, see the update)

- **Owner:** "Media Assistant does work … why can't we make it play natively on the Roku AirPlay app instead? I'd love to remove Media Assistant and just have it open to AirPlay."
- **Findings (log 9c11baa7):** "Roku took the link via media-assistant" in ~10 s; the Roku fetched the phone's own master.m3u8 (the same server AirPlay uses). Roku has no API that starts its AirPlay receiver with a link: a Roku TV is reached as an AirPlay receiver only through Apple's AirPlay list, where it already appears ("Kannons bedroom roku tv").
- **Fix:** `cast.DIRECT_AIRPLAY`: Play on TV skips the in-app TV list and the Roku search and goes to AirPlay (Apple's list opens at once, ISSUE-251); the automatic switch of a converting stream on a Roku to Media Assistant is off. The Roku code stays dormant behind the flag (its tests still run) and can be deleted once the owner confirms Rokus play well through AirPlay.
- **Retest:** test_play_on_tv_network `QuietPlayOnTV`. Phone check pending.
- **Update (owner, 2026-11-14):** "I'll keep Media Assistant until I know AirPlay works": `DIRECT_AIRPLAY` is False again, so the in-app TV list, the Roku search and the Media Assistant hand-off are back. The quiet start (no card, Apple's list at once) stays for AirPlay TVs. `QuietPlayOnTV` now checks the flag is off.

## ISSUE-253 — AirPlay of a 10-bit H.264 stream took 28 s to reach the TV (owner log a176bcec, build 393) — partly fixed in code

- **Seen:** Dragon Ball Super: Beerus S1 E1, 10-bit H.264 1080p MKV with a subtitle: source opened +1.8 s, index +4.6 s, first segment converted in 9.7 s (software decode of the 10-bit picture, VideoToolbox encode, subtitles burnt in; audio 8.8 s in parallel), stream ready +18 s, TV playing +28 s; then each segment kept the TV waiting 1-3 s (conversion ~160 % of real time).
- **Analysis (native code read):** the audio reader already seeks by the file's index and shares the video reader's byte cache; the converter already works three segments ahead; the limit is decoding 10-bit H.264 on the CPU (the phone's hardware decoder does not take it) and the source's speed. A shorter first segment would touch the uniform segment math (gm_stream) for little gain.
- **Fix:** Apple's AirPlay list opens at once, so choosing the TV overlaps the preparation (ISSUE-251); the source picker treats a "10bit" release that names no codec as 10-bit H.264 (badged "10-BIT · SLOW ON AIRPLAY", ranked after versions that play as they are), so a version that needs no conversion is preferred.
- **Not done:** a second conversion lane and a lower output size for 10-bit H.264. Prefetching the source while Kodi plays: done in ISSUE-259.
- **Retest:** test_season_quality `SlowOnAirPlay`.

## ISSUE-254 — "Waiting for the network" while online; season 2 of Naruto never started (owner screenshot and log fd2ee25a, build 398) — fixed in code

- **Owner:** "fix the waiting for network issue, it should only appear if I'm fully offline."
- **Seen:** Library status: "Naruto Shippuuden · S2 E33 · 0% · Waiting for the network · trying again in 5 min" on Wi-Fi. The log: "AllDebrid: Naruto Shippuuden: try 12, again in 360 s: RuntimeError: Waiting for TMDb to say where season 2 starts". Not the network at all.
- **Causes:** (1) the card said "Waiting for the network" for any copy waiting to try again, whatever the reason; (2) the season sizes that place an absolute-numbered pack episode (S2 E33 = episode 65) come from TMDb with TMDb Helper's key, read from special://home/addons, but TMDb Helper is bundled with the app, so no key was found, the sizes were never asked, and every season-2 episode waited; (3) that wait counted toward the 20 tries that end a copy.
- **Fix:** the card says why a copy waits: "Waiting for the network" only when the phone has no connection at all; online network trouble reads "Couldn't reach AllDebrid or Google Drive"; the TMDb wait reads "Waiting for TMDb's episode numbers"; anything else gives its own short reason. TMDb Helper's key is found through Kodi (getAddonInfo path, then the old paths). A TMDb wait never counts toward giving up (1 to 10 minutes between tries).
- **Retest:** test_work_state `WaitWords` (and the two older network tests updated). Phone check pending: Naruto S2 should start copying.


## ISSUE-255 — No way to stop Play on TV while the TV starts, now the card is gone (owner, 2026-11-14) — fixed in code

- **Owner:** "do 2": a plain Stop while the TV starts, with no loading screen.
- **Cause:** ISSUE-251 removed the progress card, and its Cancel with it.
- **Fix:** while a TV is getting ready the app keeps `KodiIOS.TV.Starting`; a short notice says "Getting it ready · tap Play on TV again to stop"; tapping Play on TV again within 3 minutes sets `KodiIOS.TV.Stop`, which the quiet flow treats as Cancel. Both are cleared when the start ends. Setting or clearing them never stops Play on TV when the window is unavailable.
- **Retest:** test_play_on_tv_network `StopAndSlowWarning`; test_remote_media (window doubles without clearProperty).

## ISSUE-256 — A 10-bit H.264 version went to AirPlay without warning (owner, 2026-11-14) — fixed in code

- **Owner:** "do 3": ask before a 10-bit version on AirPlay.
- **Fix:** Play on TV with a 10-bit H.264 version (HI10P, 10BIT, "10 bit" naming no HEVC, x265, H.265 or AV1) asks first: "Slow on AirPlay … Cancel / Play Anyway". HEVC and 8-bit versions do not ask (ISSUE-253 explains why only 10-bit H.264 is slow).
- **Retest:** test_play_on_tv_network `StopAndSlowWarning`.

## ISSUE-257 — Download problems: episode titles cut off before the episode; no way to clear a whole show (owner, 2026-11-14) — fixed in code

- **Owner:** "do 4": "Naruto Shippuuden · S…" was cut off before the part that matters.
- **Fix:** the row title puts the episode first ("S1 E5 · Naruto Shippuuden"). A copy problem's sheet adds "Clear All for <show>", which asks, then removes every non-prepare problem of that show.
- **Retest:** test_season_quality `ProblemsPageAndMemory`.
- **Desktop Kodi rig (2026-11-14, build-406 add-ons):** rows read "S1 E14 · Naruto Shipp…", so the episode is always visible. The first sheet label "Clear All for Naruto Shipp…" was cut off, so it now reads "Clear All for This Show" with the show name on the grey line below, which fits.

## ISSUE-258 — "Not the quality you picked" loop for a season with no real 1080p (owner, 2026-11-14) — fixed in code

- **Owner:** "do 5": early Naruto Shippuuden has no real 1080p, and each episode was copied, refused and searched again.
- **Fix:** when the picker takes a fallback for a tracked show, `debrid_drive.remember_fallback` records show, season and quality in `addon_data/service.kodi.ios.bootstrap/quality-fallbacks.json` (on the phone, not in Git). Later episodes of that season are copied without the strict-quality refusal. The picker still prefers a real match whenever one exists.
- **Retest:** test_season_quality `ProblemsPageAndMemory`.

## ISSUE-261 — AirPlay to the Apple TV sat loading for 2 minutes (owner photo and log dd13eb14, build 406) — fixed in code

- **Seen:** a Drive movie (MP4, 8-bit H.264 1920x1040, AAC 5.1; no conversion) sent to an Apple TV: source opened at +0.6 s,
  index at +8.4 s, first segment ready at +14.1 s, the TV asked at +14.5 s. Then the phone sent the TV its first video segment
  at about 1 Mbit/s: 786 KB in 12 s ("Receiver write failed"), then 3.3 MB in 29.8 s. Apple's player gave up ("Media file not
  received in 29s (seg0)", "No response for media file in 10.4 s (seg1)"), so the TV showed the spinner at 0:00 until the
  owner stopped it at +125 s.
- **Causes (log):**
  - The segments were already in the phone's memory, so this was the phone-to-TV Wi-Fi, not the converter. That link was
    shared with two AllDebrid copies, a "made ready while it copies" preparation of two Rick and Morty episodes, and the
    movie's own Drive reads.
  - While AirPlay plays, background downloads were still allowed 1 MB/s (8 Mbit/s), several times what reached the TV.
  - The strain check that should slow them saw none of it: a write the TV gave up on is logged as "-200 …" and did not
    match, and Apple's "Media file not received" lines were ignored.
  - The Drive reads themselves crawled: audio segment 1's reader waited 50 s and video segment 1 took 60 s for about 3 MB
    (about 0.4 Mbit/s). This is not a double read: kr_source's cache is shared by the video, audio and subtitle readers,
    and a reader waits for a block another is loading (checked in kr_source.c). The cause is the same shared Wi-Fi.
- **Fix:** `slowdown`:
  - A failed write and Apple's "not received" or "no response" lines now count as strain. So does KodiAirPlay's
    "the TV is waiting for a video segment".
  - While the TV is short of the movie, every background worker waits up to 30 s per piece. Then downloads keep under
    0.25 MB/s until the TV keeps up again (60 s after the last strain).
  - Work still never stops for good while AirPlay plays (owner rule, build 192).
- **Retest:** test_slowdown `TVShortOfTheMovie`.
- **Phone check:** the same movie on the Apple TV, and the log's TV GET times. If segments still take more than about 6 s
  with nothing else running (try Pause on transfers), the Wi-Fi between the phone and the TV is the limit.

## ISSUE-259 — Play on TV opened the source and read its index only when tapped (owner: "faster start", item 7) — fixed in code

- **Seen (ISSUE-253, log a176bcec):** Play on TV spent about 6 s opening an Umbrella or AllDebrid source and reading its index
  before the first segment could start, although Kodi had been playing that same file.
- **Fix:**
  - While Kodi plays a remote file (an http(s) link, not local, not Drive through the app proxy, not HLS), the service's
    `remote_media.watch` waits for 8 s of steady play on Wi-Fi. It then asks the media broker to warm that file once:
    it reads the first two 4 MiB blocks and the last block (the start, and Matroska's or MP4's index).
  - Play on TV's `acquire` then takes the warm source with its blocks (`warmed` in the source_cache event).
  - Stopping or changing the video releases a warm source no TV took. A TV playing from the cache is never disturbed
    (`busy`).
  - Nothing is read on cellular or while Kodi buffers.
- **Not done:** a second conversion lane for 10-bit H.264 (native; needs a KodiAirPlay release), kept as a later speed-up.
- **Retest:** test_remote_media `Warm` (5 tests). Phone check: the log says "the playing video is ready for the TV", and the
  next Play on TV's source_cache event has warmed=true and a shorter "indexed inspection finished after".

## ISSUE-262 — 22 Naruto Shippuden season 2 episodes failed "This torrent has no video file" (owner screenshot and log e56f8adf, build 406) — fixed in code

- **Seen:** Download problems: "NEED A NEW SOURCE · 22", rows S2 E36, E41, E42, E43, E44 … "This source has no video file". The picker
  chose "Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio)", whose season 2 files are
  "Season 02 (033-053)/Naruto Shippuden Episode 033 The New Target.mkv".
- **Cause:** ISSUE-254 let the season sizes through (season 2 starts after 32 episodes). But TMDb numbers this show's later
  seasons on from the last (S02E33 is the 33rd episode), and `alldebrid.pick` always added the 32. So S02E33 looked for
  episode 65, found nothing, and failed.
- **Fix:**
  - `alldebrid.pack_number`: an episode number past the episodes before its season is already absolute; otherwise the
    offset is added (S02E13 is still 45).
  - `debrid_drive.repick_packs`: later-season episodes that failed "has no video file" go back in line once, so the 22
    copies start by themselves.
- **Retest:** test_debrid_drive `PackNumbering`; test_download_e2e `test_season_two_of_an_absolute_pack` (relative numbering)
  still passes.
- **Also on the page, not this bug:** "S1 E6 · Unnamed download · No one is sharing this source" is a dead torrent whose job
  had no title.

## ISSUE-263 — Find on a dead or missing episode opened a manual search instead of taking the best version (owner, 2026-11-14) — fixed in code

- **Owner:** "it's probably because I asked for 1080p and it only is in 480p. As I said earlier have it select highest quality
  available then I can upscale later."
- **Before:** "Find" on a Download problems row ("No one is sharing this source", "no video file") opened the TMDb search,
  and the owner had to pick a version by hand.
- **Fix:**
  - Find on an episode of a known show runs the automatic Repair search (library_repair_page) for that episode at the
    show's chosen quality. Its pick takes a real match when one exists, otherwise the best version that exists, with one
    notice (ISSUE-236), and leaves out dead torrents (ISSUE-244). ISSUE-258 then remembers that season.
  - Movies and downloads with no show keep the manual search. `problems()` now carries `show_tmdb`.
- **Retest:** test_season_quality `FindTakesTheBestVersion`.

## ISSUE-264 — Repair looped on a "1080p" pack whose season 2 is 640x480 (owner screenshot and log bd7af2c1, build 415) — loop fixed in code; approval question in mockup

- **Seen:** Notifications full of "Repair: looking up Naruto Shippuuden S02E38 again at 1080p", "S02E38 is downloading ·
  1080p", "Not the quality you picked: 640x480, you chose 1080p". The log shows "repair: S02E33 … S02E47 queued (1080p)" and
  matching refusals.
- **Cause:**
  - ISSUE-262 made the pack's episodes findable, and Repair picked "Naruto Shippuden (001-500) [Complete Series + Movies
    (1080p)]" for each episode. Its season 2 files are 640x480, so each copy was refused.
  - The refusal was remembered only for that episode and only under the job's name. That name was the info-hash, while
    the list shows the version by its folder and file name. So E34 picked the same pack again, as real 1080p (no fallback
    flag), and was refused again.
- **Fix:**
  - The job keeps the name the version had in the list (`pick_name`, from the automatic pick's result).
  - `avoid_names` counts a refusal for the whole season, by that name and by its pack folder (`pack:<folder>`).
  - `deck_picker.is_lower` matches either.
  - The season's next episode therefore takes a real 1080p if one exists, otherwise the best that exists as a fallback.
    The copy is then not refused, and ISSUE-258 remembers the season.
- **Owner's request, mockup only (not coded):** docs/design/quality-choice-mockups.html. It shows one notice per season, a
  choice sheet ("Use the Best · 480p / Choose Another Version / Keep Looking / Always Use the Best for This Show"), a
  versions list with each version's real picture size, and the show page's waiting card. It waits for approval.
- **Retest:** test_season_quality `RefusedPackForTheSeason`.

## ISSUE-265 — AI Upscale said "Starts when nothing is converting" with nothing converting (owner log 0b99a266, build 415) — fixed in code

- **Owner:** "fix AI upscaling … it doesn't start, it says after a conversion but there is no conversion".
- **Cause:** "Starts when nothing is converting" was the page's default line for a waiting copy, whatever held it. The real
  holds were `upscale_queue.may_run`: copies are made only while charging (default on; the log says charging 0) and not
  while the phone is hot (the log says thermal serious). The service writes those reasons only once it reaches the copy,
  and it does not reach it while a video waits to be prepared, so that reason was never written either.
- **Fix:**
  - The service writes "Waits while a video is made ready for Kodi" on the next copy when preparation goes first
    (`upscale_cloud.hold`).
  - The page's default is "Up next".
  - The charger, battery, Low Power Mode and heat reasons were already written by process_one, and now show.
- **The test (measurement) did run:** the AI video model (4x) on a 640x480 episode made 122 pictures in 60 s at 485 ms each,
  about 0.07x real time, with the phone at thermal "serious". The log ends 1.2 min in. A 24-minute SD episode to 4K is
  hours of work, which is why copies are made in the background while charging.
- **Retest:** test_upscale_cloud `RealWaitingReason`.

## ISSUE-266 — DEC-049 coded: ask once per season when the chosen quality does not exist; DEC-050 no cut-off text (2026-11-14) — fixed in code

- **Owner:** approved docs/design/quality-choice-mockups.html ("Yes"). "We need a fully working repair system." On the rig
  renders: "ensure there is no … texts can't be cut off, maybe put that in the policy for mockups".
- **Done (DEC-049):**
  - A fallback pick for an unanswered season is not queued (`elementum_cloud.held_for_choice`). The episode is held, the
    season asks once, and the search is told "held".
  - Board A: one notice, "No real 1080p for season 2 · <show> · the best is 480p (…). Tap to choose.", whose detail page
    offers Choose.
  - Board B and C: the `quality_choice` script and choice sheets. The answer is kept in quality-choices.json:
    - Use the Best, and Always Use the Best: the held episodes go to Repair, the fallback is let through, and the copy is
      not refused (ISSUE-258).
    - Choose Another Version: that version's pack goes first in automatic picks (`deck_picker` `prefer_names`).
    - Keep Looking: nothing downloads, and the season asks again after a day.
  - Board D: the show page's season card "Waiting for your choice" with Choose. Waiting episodes say so instead of
    "Looking for 1080p…".
  - Repair:
    - Several episodes give one start line and one summary, not two lines per episode.
    - A season that waits is not searched.
    - A held episode reads "Waiting for your choice", not "nothing found".
  - A copy refused for its quality records the real size for board C, and is not announced again while its season waits.
- **Done (DEC-050):**
  - The choice sheet has wrapped row forms: the title on up to three lines, the detail on up to two, the row as tall as
    its text.
  - Version names are cleaned, not cut (`quality_choice.short`).
  - Download problems rows wrap a long title onto two or three lines, and a long reason onto two. The fallback reason is
    no longer cut at 60 characters.
  - APPLE-UI-POLICY §4.2 and §7: no "…" or clipped text in pages or mockups.
- **Evidence (desktop Kodi rig, 2026-11-14):** board B, board C (the pack name on three lines, the real-size chip "480p" in
  orange), and Download problems with a three-line film title: nothing cut off. Board D's rig render is pending (no
  Library fixture in this rig).
- **Retest:** test_quality_choice (new, in import-review.yml); test_season_sources
  `test_selected_quality_missing_queues_the_best_available_as_a_fallback` (held first, queued after "Use the Best", end to
  end through the real route).

## ISSUE-267 — No AllDebrid copy or Drive upload ran ("frozen waiting for AllDebrid"); Repair queued the 640x480 "1080p" pack again (owner log b98d5fc2, build 421) — fixed in code

- **Seen:** 21 Naruto S2 episodes "new" for 7 minutes, with no copy lane and nothing logged by the copy loop.
- **Cause 1, the freeze:** the service thread that runs every AllDebrid copy and Drive upload died at start: "cannot import
  name 'tls_context' from 'clouddrive.common.remote.request'". Kodi's own add-on updater had installed
  plugin.googledrive 1.6.13 and script.module.clouddrive.common 1.5.20 from the official repository into
  special://home/addons. Those copies shadow the app's patched 1.6.8 / 1.5.11 (scripts/build_customized_ipa.py
  DRIVE_PATCHES).
- **Fix 1 (`pinned_addons`, run by the service before the copy thread starts):**
  - Kodi's per-add-on "don't update automatically" rule (Addons DB update_rules, rule 1) for the four add-ons the build
    patches: Google Drive, its library, Elementum and Burst.
  - A home copy whose version differs from the bundled one is moved to special://temp/shadowed-addons. Kodi rescans
    (UpdateLocalAddons), and a notice asks for a restart. A home copy of the same version, as in the desktop rig, stays.
  - The copy thread puts the bundled clouddrive first on its path. If `tls_context` is still missing it uses a plain
    certifi one instead of dying.
- **Cause 2, the pack again:** Repair queued all 21 episodes from "Naruto Shippuden (001-500) [Complete Series + Movies
  (1080p)]". The refusals made by build 415 were saved without the version's list name, so ISSUE-264's season-wide match
  had nothing to match.
- **Fix 2:** the first refused copy of a pack holds the season's other unstarted episodes from the same torrent
  (`debrid_drive.hold_pack`), records the real size, and asks once (DEC-049 notice: "the version named 1080p is really
  640×480"). Board B then offers "Use the Best Available". The jobs now carry `pick_name`, so the next pick knows the pack.
- **Retest:** test_pinned_addons (new); test_quality_choice `RefusedPackHoldsItsSeason`.
- **Phone check:** after installing, the log says "automatic updates blocked for …" and "… was moved aside", with one
  "Add-ons put back" notice. After a restart, copies start.

## ISSUE-268 — One message per season request, one per episode only for a single episode (owner, 2026-11-14) — fixed in code

- **Owner:** "ensure it's only one stating the full season needs help, not 23 notifications if there are 23 episodes" and
  "per episode alerts should only appear when I download per episode, and full season alerts need to appear when I do a
  full season".
- **Before:** every download in a season posted its own messages ("AllDebrid is fetching it", "Saved to Google Drive",
  "Couldn't download to Google Drive", "No 1080p version"). A season meant tens of entries. "Saved to Google Drive" did not
  even name the episode.
- **Fix:**
  - A season request tags its downloads with a batch: Build Season (both paths), Repair of several episodes, and the
    quality choice's look-up (it runs Repair).
  - `notices.add(group=…)` merges a message of the same kind and title from the same batch into one unread entry, which
    moves to the top: "Naruto Shippuuden · 21 episodes · straight from AllDebrid…".
  - A single episode (no batch) keeps its own message, which now names the episode ("Naruto Shippuuden · S2 E33").
  - The quality question was already once per season (DEC-049). Repair already gives one start line and one summary.
- **Retest:** test_notices `OnePerSeasonRequest`.

## ISSUE-269 — A stopped download service was silent (owner log b98d5fc2, build 421) — fixed in code

- **Owner:** "it seems frozen waiting for AllDebrid". The copy thread had died at start (ISSUE-267), and nothing said so.
- **Fix:** the service runs drive_uploads under `keep_copying`. If it stops with an error, one notice says "Downloads
  stopped (<reason>). It starts again by itself; if this keeps coming back, share the log." It is merged into one entry
  (ISSUE-268 group), and the service starts again after 30 s, doubling up to 10 min.
- **Also looked at in the same log (no change):**
  - TMDb Helper's "GetDirectory … plugin.video.themoviedb.helper/resources/players/": it checks an optional home folder;
    the bundled copy is used and playback continues.
  - "…discover…with_companies=178464…page=3": the owner's Refresh moved the TMDb rows to page 3, which that studio row
    does not have. The row hides itself for that page (it shows only with items).
- **Retest:** test_pinned_addons `Watchdog`.

## ISSUE-270 — Wi-Fi to cellular deep dive; Library lists and the Drive proxy failed after the add-on restore (owner log 4e5fb2dd, build 424) — fixed in code

- **Owner:** "look what happens when I disconnect from Wi-Fi, ensure the download begins again on cellular, do a deep dive."
- **Wi-Fi to cellular (07:36:32, log):**
  - Copies did not stop. Two lanes were running (Naruto S02E33/E34, made ready while they copy). The piece in flight when
    Wi-Fi went took 46 s (14 MB at 0.30 MB/s) and finished without an error or a retry; system networking moved the
    connection over.
  - On cellular, pieces adapted from 10–16 MB to 1.5–6 MB, at 0.2–2.2 MB/s per lane. The snapshot's link went
    "cellular", link_changed_from "wifi", with copies_waiting_for_network 0 and copy lanes 2 (CELLULAR_LANES).
  - Preparation (conversion reading Drive) waits for Wi-Fi on mobile data by design (ISSUE-232).
  - Nothing to fix in the switch itself.
- **Found:**
  - From 07:35 every Library list refresh (every 10 s) and the Drive proxy failed with "No module named
    'clouddrive.common.remote'". ISSUE-267's restore had moved the repository copy aside while the session still had its
    half-imported clouddrive package and path, so later imports looked in the moved folder.
  - The copy thread itself ran, with the plain tls_context fallback.
- **Fix:** `pinned_addons.use_clouddrive()` is used everywhere clouddrive is loaded (service, drivelibrary.client, the
  Accounts page, elementum_cloud). It drops clouddrive modules loaded from another or a moved folder, removes stale path
  entries, and puts the app's bundled patched copy first. So it works in the same session, before the restart.
- **Retest:** test_pinned_addons; the full import-review list.
- **Next:** the owner's log after reconnecting to Wi-Fi (same session). Check the lanes and piece sizes grow back, and that
  preparation starts again.

## ISSUE-271 — Copies recovered slowly after a Wi-Fi <-> cellular switch (owner logs 4e5fb2dd and 18a4f9c7, build 424) — fixed in code

- **Owner:** "it appears it may already be working now, but it did take a long time; ensure it has a quicker and smoother
  recovery when switching from Wi-Fi to cellular or cellular to Wi-Fi."
- **Seen:**
  - Copies never stopped, but the run kept the old link's plan. The connection was read only when a copy run started, and
    a run holds whole episodes (minutes on mobile data).
  - The piece in flight at the switch hung 46 s.
  - Pieces on cellular started from Wi-Fi sizes and timed out, or started small and took minutes to grow again on Wi-Fi.
  - Back on Wi-Fi one lane ran, still with the cellular plan.
  - The snapshot's copy speed (1.19 MB/s) did not change for four minutes.
- **Fix:**
  - `netwatch` reads the connection every 2 s. A switch counts when the new link is seen twice and is not "no address",
    so a flicker does not restart anything.
  - A copy run that sees the switch ends at the next piece boundary. The upload sessions are saved, so nothing is sent
    again. The next run starts after 1 s, not the 30 s of a pause, with the new link's lane count (CELLULAR_LANES on
    mobile data, the Wi-Fi lane plan learned again, ISSUE-200).
  - `driveupload.LinkMemory`: the piece size and the Drive-confirmed speed that last worked on each link. A copy on a link
    starts there. A link not seen yet starts at 4 MB on cellular and at the framework's size on Wi-Fi. So the first
    pieces after a switch neither time out nor creep up from 1 MB.
  - Diagnostics count only lanes that reported in the last 90 s (`quiet_lanes` for the rest).
- **Not changed:** the one native piece already in flight at the moment Wi-Fi goes cannot be cancelled from Python. It
  ends at its paced deadline (here 46 s) and is then confirmed against Drive, so no bytes are lost.
- **Retest:** test_netwatch (new); test_diagnostics `test_network_summary_says_link_lanes_and_speeds`.
- **Phone check:** turn Wi-Fi off and on during a season copy. The log should say "connection changed to cellular while
  copying: carrying on at once", lanes should change within seconds, and there should be no 20 s piece timeouts after
  the switch.

## ISSUE-272 — Reconnect-to-Wi-Fi review; "[pseudo] 1080p" upscales passed as real 1080p (owner log 8de561f4, build 424) — partly fixed in code

- **Owner:** "here is a log after I have reconnected to Wi-Fi, review it and see what you can improve."
- **Timeline (same session as ISSUE-270/271):**
  - Cellular from 07:36. The copy run noticed Wi-Fi to cellular only at 07:43:19, 7 min late.
  - Wi-Fi came back about 07:45:46. The piece in flight took 68 s (0.18 MB/s), then pieces restarted at 1.8–2 MB and needed
    about 30 s to reach 16–28 MB. The run noticed cellular to Wi-Fi only at 07:49:12, 3.5 min late. Three lanes ran from
    07:49 at 2–11 MB/s each (snapshot 16–27 MB/s).
  - From 07:48 a preparation ("Checking downloaded videos") read Drive at 49 MB/s on the same Wi-Fi, and the copies'
    pieces fell to 0.8–3 MB/s.
  - ISSUE-271 (not in build 424) removes the late detection and the slow regrowth. The in-flight piece at the switch moment
    remains, bounded by its paced deadline.
- **Found:** S02E33–E38 were copied as "[AnimeRG] Naruto Shippuden - 0xx [1080p] [x265] [pseudo]" (1404x1080).
  "pseudo" marks an upscale of the DVD, so it passed the height check while not being real 1080p. E39 then came from
  another release (704x480).
- **Fix:** `deck_picker.UPSCALED_NAME` also matches "pseudo" (as a word) and "Anime4K". Such a version counts as lower than
  the quality it names, so a season with no real 1080p asks (DEC-049) instead of taking an upscale.
- **Also seen, harmless:** TMDb Helper's daily clean-up listing log folders that do not exist yet; the Library list
  errors (64) are ISSUE-270.
- **Open ideas, not done:**
  - Keep one release for a whole season (mixed AnimeRG / Anime Time episodes).
  - Let copies go first while a preparation reads Drive on the same Wi-Fi.
- **Retest:** test_season_quality `test_versions_that_are_not_really_the_chosen_quality_are_left_out`.

## ISSUE-273 — Copy cards choppy, no graph on a copy's sheet, nothing said "getting it ready" (owner screenshots and log 3848afa9, build 424) — fixed in code; circle design in mockup

- **Owner:** "these are super choppy to update, not smooth like the conversion pages"; "have the AllDebrid to Drive look just
  like the conversion tab … a graph of speed and a circle of progression"; "it doesn't show anything about getting things
  ready; ensure all downloads and preparation and everything shows in the status".
- **Seen:**
  - S2 E48/E49/E50 sat at 92/91/94 % with "Waiting for Google Drive · no answer for 1 min".
  - Their sheet showed "Right now —" and no graph.
  - All three were "made ready while it copies" (704x480 HEVC). From 07:53 every Drive piece crawled at 0.03–0.1 MB/s,
    against about 24 MB/s a minute earlier on the same Wi-Fi.
- **Causes:**
  - A copy reports when a piece is confirmed: 6–30 s apart, longer at low speed. Conversions report every second.
  - The transfer history kept one copy ("up"), the shown one, so the other lanes had no graph. The sheet also matched it
    by title, which differs for single-episode jobs.
  - Copies made ready on their way had no words of their own.
- **Fix:**
  - work_state glides a copy card between reports at its measured speed: at most MAX_GLIDE 20 s, never to 100 %.
  - A copy made ready on its way says "Getting it ready for Kodi and AirPlay", and when quiet "Getting it ready · waiting
    for Google Drive · no answer for N min".
  - transfer_history records every fresh copy lane ('up', 'up.<slot>') with its job. The sheet finds the lane by the job
    and draws its graph.
- **Mockup:** docs/design/unified-status-mockups.html, waiting for approval.
  - Board A: one card style for every job, with a progress circle, the step, speed/left or why it waits, and a speed line.
  - Board B: the copy sheet like the conversion sheet, with a large circle and the speed graph.
  - It changes DEC-036 (bars everywhere), so it waits for the owner.
- **Retest:** test_copy_status `Card`, `Graphs`.

## ISSUE-274 — One release per season (owner, from ISSUE-272) — fixed in code

- **Seen:** S2 mixed "[AnimeRG] … [pseudo]" 1404x1080 and "[Anime Time]" 704x480 episodes.
- **Fix:** `debrid_drive.season_names` (the list names of the season's copied episodes) goes with each automatic request.
  `deck_picker.release_group` reads the "[Group]" tag or the scene "-Group". At equal quality a version from the season's
  group goes first; it never wins over a better quality.
- **Retest:** test_copy_status `OneReleasePerSeason`.

## ISSUE-275 — A preparation read Drive at 49 MB/s while copies crawled (owner log 8de561f4 / 3848afa9) — fixed in code

- **Fix:** while an AllDebrid copy lane reported in the last 30 s, prepare_cloud starts no new preparation, except the next
  to watch or one the owner asked for now. Its Up next row says "Starts when the downloads finish". Copies made ready on
  their way are copies, so they are not held.
- **Retest:** test_copy_status `CopiesFirst`.

## ISSUE-276 — Library pages showed different numbers: TV Shows stuck at 28 Naruto episodes with no season 2 while Library status said 84 of 87 ready (owner screenshots and log 8d661d6e, build 424) — investigated; proposal in a new draft PR

- **Root cause of the season 2 gap:** after a repository update replaced the app's patched Google Drive add-on, every TV Shows list refresh failed (`No module named 'clouddrive.common.remote'`, 207 times in 45 min), so Library › TV Shows kept its last good list (28 episodes) while season 2 was copied. Library status uses a second, separate Drive listing (the preparation scan), which kept working. ISSUE-270 (in build 430) fixes the import; nothing told the owner the list was stale.
- **Design cause:** two Drive listings of the same folder and four sets of counting rules (Download problems, show card, show page, Library status' Kept). Details and the proposal (one Library index every screen reads): docs/investigations/library-one-source.md.
- **Step 1 coded (PR #27):** `library_index.py` builds one entry per movie and episode from the Drive listing, preparation jobs, AllDebrid copies, AI Upscale copies and the Don't Show Again list, with one state each (copying, converting, ready, kept, problem, cancelled) and one set of counting rules (`counts(scope)`: whole library, TV, movies, one show, one season). Rules decided once: a failed copy of a video on Drive or copying again is not a problem; a copy saved without a title takes its show from its TMDb id; one entry per video (extra files listed as duplicates). Test: test_library_index (the owner's state from log 8d661d6e: every screen's numbers add up; S1 E6 is not a problem; season 2 grows as it lands).
- **Step 2 coded:** the service keeps `library-index.json` (a background thread rebuilds it when the preparation state, the copies, the AI Upscale queue, the Don't Show Again list or a pending action changes, and at least every 30 s); a change counter in `Window(Home).Property(KodiIOS.LibraryIndex)` lets open pages redraw at once. `library_index.intend` is the one action path: a video the owner deletes, stops, retries or hides shows "Deleting…" / "Stopping…" on every page until the real state takes over. The TV Shows list refresh now records Drive health (ok / "Can't reach Google Drive") in the index for the health line.
- **Step 3a coded:** Library › TV Shows, Movies, the show page, Select and Delete Season read their videos and states from the index (`library_index.show_rows` / `episode_rows` / `movie_rows`, `library_manager.episodes_of`); the saved Drive listing only gives posters, years and TMDb ids. A season being copied shows in its show and grows; the show page's numbers are `counts()`. Test: test_library_index `PagesReadTheIndex` (a stale saved list of 28 season 1 episodes: TV Shows still shows seasons 1 and 2, with Library status' numbers).
- **Step 3b coded:** Download problems keeps its rows and sheet but lists only the problems the index has (`copy_problems.from_index`): a failed copy of a video on Drive or copying again is gone, and a copy saved without a title is named after its show. Library status' "N of M ready" and its Ready / Working / Kept tiles are `library_index.counts` (`library_rows.page_properties(index=…)`). Tests: test_library_index `DownloadProblemsReadTheIndex`, `LibraryStatusReadsTheIndex`.
- **Still to do (DEC-052):** the self-check (Drive vs copies vs preparation), the minute log line with the same numbers, and, after mockups: the health line, season progress on the chips, Undo after Delete, and each page redrawing on the counter. Then a desktop Kodi rig render with one fake library, and an IPA with the owner's OK.
- **Step 4 (no new UI) coded:** every minute the log carries the numbers the screens show (`library: 84 of 87 ready · 3 working (… copying, … converting) · 2 kept · 1 need you · 0 hidden · Drive ok`), and every five minutes a self-check logs duplicate files, copies saved but not on Drive, and preparations of files no longer on Drive (`library_index.summary` / `check`). Test: test_library_index `SelfCheckAndLogLine`.
- **Step 5 (one action path) coded:** Delete (Library pages) and Stop (any copy, from any page that calls `transfer_control.cancel_copy`) now record an intent in the index (`library_index.intend_for`, by Drive id or torrent hash), so every page shows "Deleting…" / "Stopping…" for that video at once; a preparation job the owner chose to forget no longer counts its file as in the library. Test: test_library_index `StopOrDeleteEverywhere`.

## ISSUE-277 — "Couldn't download to Google Drive · The copy to Google Drive stopped: Rick and Morty · S2 E7" while nothing had failed, Download problems showed 0, and E8–E10 never started (owner screenshot and log 27c3ca14, build 430) — fixed in PR #27

- **What happened (log):** Download Season queued Rick and Morty S2 E1–E10 at 08:34. E1–E6 were stored on AllDebrid and were copied by 08:39. E7's version was not: from 08:40 to the end of the log (08:44) it sat at AllDebrid "fetching 0%" (`debrid` statuses `fetching 1, new 3`), and nothing failed in this run (no `failed:` line, the failed count stayed 94).
- **Root cause 1 (the notice):** the notice was "AllDebrid is fetching it · Rick and Morty · S2 E7" (Downloads group, download icon). The notification sheet (`notice_help.RULES`) treated any notice with "AllDebrid" anywhere in its title or text as a failed copy, so it opened as "Couldn't download to Google Drive · The copy to Google Drive stopped". Every "Saved to Google Drive · … straight from AllDebrid" notice opened the same way. Download problems showed 0 because nothing had failed.
- **Root cause 2 (the line):** a torrent AllDebrid is fetching stayed at the head of the copy line (`step` took `jobs[0]`), so E8–E10 waited behind E7. With no peers, AllDebrid keeps a magnet at 0% for up to 72 hours, so it never became a problem anywhere.
- **Root cause 3 (the brain):** the Library index counted it as "Copying to Google Drive · 0%".
- **Fix:**
  - The sheet matches the notice's title. "AllDebrid is fetching …" explains that AllDebrid is downloading it first and that the copy starts by itself. "Saved to Google Drive" is good news. A real failure says "Couldn't copy <video>" ("is waiting" only when AllDebrid is busy or blocked).
  - `debrid_drive.poll_fetching` checks fetching torrents beside the line every 15 s, so the next episode copies meanwhile.
  - A fetch that has not moved for 30 minutes ends failed with "Nobody is sharing this version: AllDebrid got no further than N% in 30 minutes. Pick another version." It sends a real notice, joins Download problems, and the next automatic search leaves that version out.
  - The index says "AllDebrid is fetching it · N%" / "Waiting to copy", and a stalled fetch counts as a problem on every page (Download problems, the show page, the season, Library status).
- **Tests:**
  - test_debrid_drive `FetchingDoesNotHoldTheLine`: E8 starts while E7 fetches; no progress for 30 min ends in `problems()`; progress keeps it going. These failed on the old code.
  - test_notice_log: fetching / saved / failed sheets.
  - test_library_index `StalledFetchIsAProblemEverywhere`.
- **Phone check still needed:** on the next build, a version AllDebrid has to fetch shows "AllDebrid is fetching it · N%". The next episodes copy meanwhile. If it never moves, after 30 min it is in Download problems with the same count on Library status. The minute `library:` log line carries the counts.
- **Not proven from this log:** the 94 older failed copies. Download problems lists a video only when no other version of it is on Drive, copying or hidden, and the log does not carry the phone's copy list. The new build's minute `library:` line (… need you · … hidden) will show whether the count is right.

## ISSUE-278 — AirPlay of Naruto S1 E1: only the sound reached the Roku TV, then "AirPlay couldn't play this · Cannot Complete Action" (owner screenshot and log 33942e4f, build 430, AirPlay r56) — fixed in native source (r57 build pending)

- **Seen (09:00:11–12):** Play on TV › AirPlay with the prepared file of Naruto Shippuuden S1 E1 (H.264 `avc1.640028` and AAC, served as HLS over the file's 23 stored fragments of up to 69.3 s, audio and video muxed together).
  - Every request came from the iPhone itself (AppleCoreMedia), none from the TV, and external playback never came on.
  - The phone's player read 3.4 MB of the first 10.7 MB range, hung up, and stopped "Cannot Complete Action" 1.5 s after start. The native player then logged "problem left to Kodi's card", with no restart.
- **Root cause:** the same receiver shape as ISSUE-124 and ISSUE-138. Roku's streaming specifications do not support muxed audio-and-video fMP4 and want segments under 10 s, and the prepared playlist breaks both. The restart rules missed this case:
  - r36's "sound only" and "player failed" restarts skip any H.264 picture: they were written for HEVC.
  - r41's prepared-playlist restart needs external playback to have come on once (`everExternal`). This time the TV got the sound only, so external playback never came on.
  - So nothing ran, and Kodi showed the card.
- **Fix (`build-airplay.sh`, r57 source):**
  - A prepared file that the TV takes as sound only, or that fails while the TV has only the sound, restarts once, H.264 too.
  - A prepared H.264 picture is kept as it is: it restarts in `KR_COMPAT_SEGMENTED` mode (6 s segments with the audio as its own rendition, the picture copied). This is the stream ISSUE-138 made for Roku's own player, so the phone does no conversion work.
  - Any other codec keeps the H.264 conversion.
  - Log line: "restarting in 6-s segments for this TV (H.264 picture kept as it is)".
- **Tests:**
  - test_play_on_tv_network `test_a_prepared_h264_file_the_tv_turns_down_restarts_in_segments`.
  - test_airplay_remux updated for the one guarded restart path.
  - Host checks only: the Objective-C compiles in the airplay-ios workflow on macOS.
- **Built and pinned (owner OK, 2026-11-14):** r57 was published by airplay-ios run 43622274914. Digest 9a112807…42fbda was checked by download, and the binary carries the new restart notes. Host tests: airplay-remux run 43621764007.
- **Phone check:** AirPlay a prepared H.264 episode to the Roku. The log should show "restarting in 6-s segments", then `/video/` and `/audio/` segment requests from the TV, and the picture on the TV.
- **Not done yet:** remembering that this TV needs segments, so the next start skips the failed first try (about 1.5 s).

## ISSUE-279 — The video controls never went away: a tap outside the buttons did nothing and they never timed out (owner, build 430, log 72b62563) — fixed in code

- **Seen:**
  - 09:03:23–09:03:40: ten taps on the playing video's controls landed on no button and were logged "Click at … in VideoOSD.xml: control 0 (not handled)". The controls stayed.
  - After the last tap they were still up 12 s later, until the owner tapped back.
- **Root cause:**
  - The controls (`player_osd.window`) had nothing under the buttons to take a tap.
  - Kodi only auto-closes its controls when a mouse move opened them, never after a tap.
  - The app's own timer (Settings › Customisation › Video Controls › Hide Controls After, Fuse's `OSD_Timeout`) ships empty, and empty means never.
- **Fix:**
  - A clear full-screen button (id 7100) under every other control closes the controls, as a tap does in Apple's player. Real buttons above it keep their taps, and arrow-key focus never reaches it.
  - Hide Controls After becomes 5 s the first time the controls open (once, `ios_osd_timeout_default`). The shipped skin settings stay as they are: they are pinned by hash.
  - Emptying it later, or setting 0, still means never. While paused or with Continue Watching open, the controls stay, as before. Nothing new is drawn.
- **Tests:** test_customisation `test_tap_anywhere_hides_and_five_seconds_by_default` (plus the updated alarm test); test_portrait skips the clear area in its safe-inset check.
- **Phone check:** while a video plays, tap the picture away from the buttons and the controls hide. Leave them and they hide after 5 s. Paused, they stay.

## ISSUE-280 — Umbrella streams sat at "Getting ready to play… 0%" for about 30 s, then the video appeared (owner screenshots, build 430, log 72b62563) — speed fixed in code; the card's new line waits for mockup approval

- **Seen (Black Clover S02E07, 1.70 GB WEB MKV through AllDebrid):** the open took 32.2 s ("handoff 11.3 s, open 21.0 s"), and 27.8 s the second time. Kodi's own open of the file accounts for 19 s, from `Creating Demuxer` at 09:03:01.5 to the probe at 09:03:20.2, inside FFmpeg's `avformat_open_input`.
- **Root cause (inferred, not measured on the phone):**
  - Kodi reads an Umbrella link itself, over one connection. ISSUE-163 measured AllDebrid at about 0.7 MB/s per connection.
  - An MKV's start (header, tracks, the first clusters for probing) plus a jump to its end (tags and index) is roughly 13 MB of reads and reconnects at that speed: about 19 s. Kodi's FFmpeg already skips attached fonts (roadmap 1B.1).
  - Umbrella's card percentage stops once it has the link, so the card said 0% throughout.
- **Fix (speed):** an Umbrella MKV / AVI / WebM now opens through the service's stream cache (`remote_media`, ISSUE-145/163/259), which until now served only AirPlay.
  - `umbrella_recovery.remember`, which already runs inside Umbrella's AllDebrid unlock, swaps `response['link']` for the cache's 127.0.0.1 address (`remote_media.for_kodi`). The cache reads with four connections at once, and asks for the file's first two 4 MB blocks and its last block the moment the link is known.
  - Fallback: any failure, a missing service or another kind of link leaves Umbrella's link unchanged. Already-patched Umbrella installs need no re-patch.
  - Play on TV translates the cache address back to the real link (`remote_media.original`), so a TV never gets 127.0.0.1, and it shares the same cache instead of reading the file again.
  - The source Kodi reads is released after 120 s with no reads; a TV reading it keeps it alive.
- **Tests:** test_remote_media `KodiPlays` (6) covers: the cache route with start and end asked for; other links unchanged; Play on TV gets the real link and shares the cache; idle release; the Umbrella unlock hands Kodi the cache; cast translation.
- **Card (UI):** `docs/design/stream-opening-mockups.html` board S1 has three honest stages under the bar: getting the link (sliding bar, seconds), opening the video (real MB read of 12 MB), and a slow-source note with the real speed. It waits for the owner's approval before code.
- **Phone check:** an Umbrella MKV opens in a few seconds rather than about 30. The `open timing … via umbrella` line shows the new open time. Play on TV of the same episode still works.
- **Card coded (board S1, owner-approved 2026-11-14):**
  - `umbrella_ready.stage` writes IOSReady.Line / Right / Fill / Slow every quarter second from two sources: the unlocked link (`KodiIOS.UmbrellaRenewal`) and the stream cache's counts (`remote_media` stats now include `kodi`, `cached_blocks`, `block_size`).
  - `pages.umbrella_ready` shows the line. The bar fills by Fill or slides, and Umbrella's own percent stays the fallback.
  - Test: test_pages `OpeningStages` (3).
  - Desktop Kodi rig render of stages a, b and c: matches the boards, no cut-off text (screenshots kept out of Git). Phone check pending.

**Delivery (owner OK, 2026-11-14):** IPA build-442 was built from f1d6447 (import-review run 43623141308) and carries ISSUE-276 to 280 and AirPlay r57. It was downloaded and checked: sha256 982d4a24…4ed7dbb, the zip is valid, and the framework carries the r57 restart note. The library index, poll_fetching, the for_kodi route, the tap-to-hide area and the stage line are all inside. Phone checks are pending for every item.

## ISSUE-281 — Umbrella stream stuck at "Opening the video · 0 of 12 MB", then a crash on Resume (owner, build 442; ISSUE-280 regression) — fixed in code; crash log asked for

- **Seen:** an Umbrella episode never opened; the opening card stayed at "0 of 12 MB". Pressing Resume crashed the app.
  Log 6cf2a4c5 starts after the crash, so it does not hold the crash itself.
- **Cause (from the code and log 6cf2a4c5):**
  - `remote_media.start` runs inside `drive_uploads` before the ISSUE-282 NameError. Every watchdog restart (30 s, 60 s,
    120 s … 600 s) made a new cache and moved the Home property to it.
  - Umbrella's unlock (`for_kodi`) could hand Kodi an address on one cache while the opening card (`umbrella_ready`, reading
    the property's stats) counted another, empty one: "0 of 12 MB" for good.
  - A later Resume reopened an address whose cache was no longer the one in charge.
  - `for_kodi` also handed Kodi the cache before knowing the link answered at all.
- **Fix:**
  - `remote_media.start` keeps one cache per service run (`_BROKER`). A restarted Drive loop reuses it and points the
    property back at it.
  - `for_kodi` gives Kodi the cache only once the cache knows the file's size (the link answered) within FIRST_ANSWER = 5 s.
    Otherwise Kodi gets the real link, as before ISSUE-280, and the cache lets the source go (`drop`).
  - The stats name their source by a fingerprint (`source_id`), never the private id.
  - With ISSUE-282 fixed, the restarts themselves stop.
- **Asked for:** the crashed session's log (kodi.old.log), to confirm the crash's own cause.
- **Test:** test_stream_fallback (new: the cache used once the link answered; the real link and `drop` when it does not;
  one cache per run; no private id in the stats); test_remote_media (52) still passes.

## ISSUE-282 — "Kodi iOS Drive: downloads stopped (NameError); starting again in 30/60/120 s" from startup (owner log 6cf2a4c5, build 442) — fixed in code

- **Seen:** from 10:29:55 the service's Drive loop stopped at once on every start, and the ISSUE-269 watchdog restarted it.
  The log gave only the error's type.
- **Cause:** PR #27 (DEC-052, library index step 2) starts `library_index.publish` inside `drive_uploads` with
  `set_property=window.setProperty`. `window` is a name of `run()`, not of `drive_uploads` (which calls the Home window
  `home`, a path, and has `xbmcgui`). So `drive_uploads` raised NameError right after the Library lists thread started.
  Nothing after it ran: no AllDebrid copies, no Drive uploads, no preparation, and the library index never published.
- **Fix:**
  - `xbmcgui.Window(10000).setProperty`.
  - The watchdog logs the message too ("downloads stopped (NameError: name 'window' is not defined)"), redacted, 200
    characters.
  - Two latent undefined names in `library_tools_page` (`u` in `_card_row` / `_arrow`) are fixed as well.
- **Test:** test_undefined_names (new; symtable over the service, the page scripts and every library module: a function
  may only use its own, an enclosing function's, the module's or a builtin name). It reports `drive_uploads uses window`
  on the old code.
- **Also:** test_library_tools `test_failures_are_noted_where_jobs_fail` expects 4 failure records in debrid_drive. PR #27
  added one for jobs that end while AllDebrid fetches, and the test still said 3, so the import-review list failed on
  this branch before this change.

## ISSUE-283 — Video controls hide after 3 s, not 5 (owner, build 442) — fixed in code

- **Owner:** the controls should hide after 3 s. They still stay up while paused (confirmed working on build 442).
- **Fix:** `player_osd.DEFAULT_TIMEOUT` is 3. A second one-time step (`ios_osd_timeout_3`) moves installs that got the earlier
  5 s default (ISSUE-279) to 3 s. A value the owner sets later, 5 included, is kept. `ARM_WHEN` still waits while paused.
- **Test:** test_customisation `test_tap_anywhere_hides_and_five_seconds_by_default` (the first default is 3, the 5 to 3 move
  happens once, paused keeps them).

## ISSUE-284 — "Remove From Continue Watching" did nothing (owner, build 442) — fixed in code

- **Cause:** the long-press entry (`plugin.video.kodi.ios.watch` `continue_hide`) recorded the title as removed and ran
  `Container.Refresh`. That reloads only the page's own list, never a row of the Home, Movies or TV hubs, so the row kept
  showing the title until the app reloaded it for some other reason.
- **Fix:**
  - The rows' path carries `&stamp=$INFO[Window(Home).Property(KodiIOS.ContinueStamp)]` (`portrait.CONTINUE_STAMP`).
  - A removal sets that property, so Kodi loads every Continue Watching row again at once.
  - A library item (a downloaded movie or episode, key `file:…`) also has its resume point in Kodi cleared
    (`VideoLibrary.SetMovieDetails` / `SetEpisodeDetails`, resume 0), so Kodi's own in-progress lists drop it.
  - A phone title (Umbrella / Elementum / TMDb) keeps its saved position: owner, 2026-11-13, "don't make it erase the
    progress … if I watch it again it can show back up". It stays off the rows until it is played again.
- **Test:** test_watch_continue `RemoveFromContinue`; test_portrait `test_continue_watching_leads_each_hub` (the stamp is in
  the row's path).
- **Retest (follow-up):** test_listing_cache `test_a_rows_address_cannot_change_when_the_home_tab_is_shown_again`
  failed on the stamp (it reads `Window(Home)`). The stamp changes only when a title is removed, never on a tab return,
  so the test now ignores exactly `portrait.CONTINUE_STAMP` and still rejects any other window info in a row address.

## ISSUE-285 — "AllDebrid … RuntimeError; trying it again after the others" named no cause (owner, build 442) — logging fixed; cause waits for the next log

- **Cause of the blind spot:** `debrid_drive` logged only the error's type (`RuntimeError`) when a copy was queued for a
  retry. A RuntimeError there can be any of eight things (Drive upload start / upload HTTP status, Drive did not confirm
  the upload, the download stopped before the end, an invalid receipt or confirmed position, the refreshed download is
  a different file, Drive has a different size). Log 6cf2a4c5 was not available in this session, so the cause could not
  be read from it.
- **Fix:** the retry line now names the episode (`episode_label`) and the error's own words, redacted
  (`diagnostics.redact`: links, keys, magnets) and cut at 160 characters (`debrid_drive._said`). The startup line of
  ISSUE-282 does the same for `keep_copying`.
- **Next:** the owner's next log after a retry shows which one it is; the fix follows in its own entry.
- **Test:** test_build442_logs (the retry line carries `_said(error)`; `_said` keeps the words and removes a link).

## ISSUE-286 — Deleting the "Unnamed download" did nothing (owner, build 442) — fixed in code

- **Cause:** two parts.
  - A video that is only an AllDebrid copy or problem (no Drive file) showed "Remove from Library…" on its sheet
    (`library_manager.fill_item`), but its action was empty, so the tap closed nothing and changed nothing. Delete
    Season and Select only passed videos with a Drive id, so they left these behind too.
  - `debrid_drive.clear_failed` removed only the failure Download problems shows. An older failed version of the same
    video then became the latest, so the problem came back.
- **Fix:**
  - `library_index.remove(profile, keys)` is the one path for videos not on Drive: a copy that ended leaves with every
    failed version (`clear_failed(..., whole_video=True)`), and a running copy is stopped (`transfer_control.cancel_copy`).
    "Deleting…" shows on every page at once (`intend`), and the index is rebuilt.
  - The item sheet's "Remove from Library…" (problem) and new "Stop and Remove…" (copying) call it after a confirmation.
    Delete Season also removes the season's copies and problems that are not on Drive.
  - Videos on Drive keep the existing Delete (Drive's Trash).
- **Test:** test_library_remove (two failed versions of an untitled episode both go; a running copy is stopped; a Drive
  video is untouched; the sheet and Delete Season use the path). The test fails with `whole_video=False`.

## ISSUE-288 — AI Upscale did not list Naruto season 2 (owner, build 442) — fixed in code

- **Cause:** the AI Upscale page (`upscale_page.library`) and its copy planner (`upscale_queue.plan`) read only the
  preparation queue's finished jobs (`status == 'done'`). A video that was never prepared (it played as it was), was kept
  as it is, or whose job was superseded never appeared, while Library (library_index) showed it.
- **Fix:** `upscale_page.jobs_from_index(index, prep)` turns every video in library_index that is on Drive and plays
  (ready or kept) into a finished job: its own probe when it has one, otherwise the size from the quality in its name
  (480p, 576p, 720p, 1080p). A video of unknown size is left out. `upscale_cloud.planning_state` feeds it to both the
  page (`upscale_settings.model`) and the service's planner, falling back to the queue before the first index exists.
  Videos that were never prepared get a copy only when the owner chooses a size on their show's page, never from
  "Upscale new downloads" (ISSUE-245: "I want full control").
- **Test:** test_upscale_from_index (season 2 episodes without a finished job are listed; unknown size and converting are
  not; never-prepared videos wait for the owner; service and page share the path).

## ISSUE-289 — "Trakt connected" and "Elementum daemon has started" filled Notifications at every start (owner, build 442) — fixed in code

- **Request:** owner, 2026-11-14: "hide these notifications permanently; the only time it should appear is if it doesn't
  start or there is an error with Trakt/Elementum, because it's a given that Elementum will start and Trakt will start
  every time".
- **Cause:** Kodi's own pop-ups (`toasts.jsonl`) are all recorded (`notices.ingest`), so each start added the two
  successes again (twice after a restart).
- **Fix:** `notices.routine(item)` marks a Trakt connected/authorised/signed-in or Elementum started/running notice
  that is not a problem and has no trouble words (failed, error, could not, stopped, refused, timed out, not started).
  `notices.add` does not record it, and `notices.load` drops ones already saved, so they leave the page and the unread
  count at once. A failure still shows.
- **Test:** test_routine_notices (starts dropped, failures kept, old saved ones disappear).

## ISSUE-290 — Notification centre: a lot of grey space, cut-off text (owner, build 442) — fixed in code (C1, approved)

- **Request:** owner screenshot, 2026-11-14: "there is a lot of grey open space, can be cleaner … the notifications
  themselves look good but the grey space and everything just looks poor". C1 in `docs/design/build442-mockups.html`
  approved the same day ("i love the mock, code it").
- **Cause:** every message row was a fixed 236-unit block: a 97-unit tile, the title, then the text pinned at y=138
  whatever the title's length, so a one-line title left a grey band and a long text was clipped ("stopped (name
  'window' is not"). Repeated notices took a row each. The Fix capsule took the text's width.
- **Fix (`notifications_skin.py`, `notifications.py`):**
  - A message row is stacked from parts the page's grouplist lays out: the title part (1, 2 or 3 lines, `msg.N.tl`),
    the text part (1 to 4 lines, `msg.N.ll`), a Fix part, and an end part. `notifications_skin.lines` counts the
    lines conservatively (whole words, a few characters short of the real width), so a row can be a little tall but
    text is never cut (DEC-050).
  - 30 pt tiles, the time on the right with the unread dot before it, "Fix ›" as a blue text action under the text.
  - The same notice again (kind, title, text) folds into one row with a "×N" chip (`notifications.fold`).
  - TODAY and EARLIER are separate grouped cards (first/last per section).
  - Running now is one grouped card of 64 pt rows: poster, title, line and a progress ring (ring_00..20).
  - One tap area per row reaches under its parts (each part has no button of its own).
- **Retest:** desktop Kodi rig (Kodi 21.3, synthetic notices with a 168-character text, a two-line title, a repeat
  and an old notice): rows sized to their content, corners round per card, nothing cut. Rig evidence, not the phone.
  Two faults found on the rig and fixed before commit: `!(…)` is not a Kodi condition (Kodi uses `![…]`), so the
  square background covered the rounded one; and a one-line title's header is shorter than its tile, so the tile is
  drawn by the following part.
- **Unlike the mockup:** the unread dot sits before the time, not after the title (Kodi cannot place an image after
  wrapped text). A two- or three-line title shows its "×N" under the time.
- **Test:** test_notification_centre_c1 (line counting, every height has its part, no `!(` and no "…" in the window,
  folding, sections and per-section positions).

## ISSUE-291 — A row's title opens the row as a poster grid (owner, build 442) — done in code

- **Request:** owner, build 442 screenshots: "when I tap these bars it opens a grid view of the shows with the meta art
  only, like how downloaded movies and TV shows work; apply this to all rows".
- **Cause:** the title above each row ("Trending Movies ›") was a label; the chevron promised a page that did not exist.
- **Fix:** `portrait.title_tap` lays a 128-unit (44 pt+) borderless button over every row's title on Home, Movies and
  TV (`row()`, ids 5701+). It runs `titled_page`, the same action as Library › Movies: the Videos window with the
  poster grid, titled with the row's name, showing the row's own list. A 1-unit group, so the page's layout is unchanged.
- **Retest:** desktop Kodi rig, a real pointer tap on "Netflix Originals ›" on Home: the grid opened with the row's
  titles and the heading "Netflix Originals". Rig evidence, not the phone. (SendClick from a script did not reach it; a
  pointer tap did.)
- **Test:** test_row_title_grid.

## ISSUE-292 — Library status still showed the big "Working on now" card and thick copy cards (owner, build 442; DEC-051) — board A coded

- **Request:** owner, build 442: "the agent didn't update Library status to make AllDebrid downloads look like the
  others". DEC-051 board A round 2 (unified-status-mockups.html), approved 2026-11-14.
- **Cause:** DEC-051 was approved but not coded: the conversion had its 398-unit card, each AllDebrid copy its own
  231-unit card with a bar, and the extra lanes their own cards. The subtitle line was also cut ("checked just n…").
- **Fix (`library_page.py`, `library_status.py`):**
  - The summary card moves to the top. Then one grouped card "WORKING NOW · N" with one slim row per running job (the
    conversion, each extra lane, each AllDebrid copy; `RUN_SLOTS`): a 34 pt ring with the percentage, the title, one
    status line (step · speed · time left; orange when it waits), the speed line for the conversion. About 47 pt a row;
    a long title or status grows the row to two lines instead of cutting it (`k.tl` / `k.sl`, DEC-050).
  - The tap targets stay (WORK / WORK+100, LANE+n, 9310+n), so each row opens the sheet it opened before.
  - Up next and Kept rows are slim too (126 units). The subtitle under the title wraps.
  - `library_status.slim_rows` builds the rows' properties (ring, number, status, first/mid/last, the heading).
- **Not yet:** board B (a copy's sheet like the conversion sheet). The copy rows open their existing sheet.
- **Retest:** desktop Kodi rig, scenario `lanes`: three running rows in one card, Up next and Kept slim, nothing cut.
  Rig evidence, not the phone.
- **Test:** test_slim_status; test_library_status `test_the_rows_are_drawn` now looks for the WORKING NOW heading.
- **Follow-up (owner screenshot of the rig render: "no graph on the bottom 2 and no time, they should all look like the
  first one; uneven spacing"):** every row now has the same parts. Its speed line comes from the service's history for
  that title (transfer_history) or from the speeds the page has seen for the row (`sparks`). Its time left is the
  job's own estimate or, without one, worked out from how fast its percentage moves (`with_eta`, after 10 s). Each copy
  row is matched to its model job by title for speed and time. Line counts now come from the text's estimated width in
  Inter (`notifications_skin.lines_in`), not a character count, so a one-line status is never given two lines (that was
  the uneven first row). Retest on the rig: three even rows, a speed line on each. The rig's lanes scenario keeps the
  lanes' percentages fixed, so their time left could not show there; test_slim_status covers the estimate.

## ISSUE-293 — Queue and Notifications bypassed the shared library record — fixed in backend

- **Request:** Build 442 item 15: Rick and Morty season 3 must agree in Library status, Transfers and Running now.
- **Cause:** work-state independently inferred membership and titles from lane/preparation snapshots; a quiet or missing
  worker report hid indexed videos. The ISSUE-282 NameError previously prevented the index publisher starting at all.
- **Fix:** library_index decides video membership, titles and counts; work_state attaches worker telemetry by identity.
  All three consumers use that projection; missing measurements leave the video queued. Ready/problems cannot reappear
  as active transfers. Pending cancellations are applied to the index. Its publisher refreshes on every service pass,
  survives a failed pass and updates KodiIOS.LibraryIndex only on a visible change. Concurrent writes use unique temp files.
- **Retest:** The supplied current build-442 log has 12 repeated NameError restarts, no library summaries and no upload
  piece timings (raw log retained outside Git). A four-video fixture (copying, converting, problem, ready) agrees across all consumers; missing telemetry and
  transient publisher failure are covered. Host checks do not establish device behaviour; owner retest remains pending.
- **Test:** scripts/test_queue_index.py; updated publisher fixture in test_work_state.py; check_project and every test
  listed in import-review.yml run before commit.


## ISSUE-294 — Upload speed omitted first pieces and mixed lane/total rates; graphs arrived in bursts — fixed in backend

- **Request:** Build 442 item 8: actual per-lane rolling MB/s, regular history, total, ETA and progress-ring data.
- **Cause:** Rate marks started after the first acknowledgement, and the primary lane's rate was overwritten with a sum.
  History saved every five seconds, independent of the shared work model. An index reader could briefly retain a completed
  job until the next service pass (caught by the full-suite queue visibility test during ISSUE-293 validation).
- **Fix:** driveupload emits acknowledged bytes and measured request duration for the first, intermediate and final pieces.
  Native rates use the very timings printed by the native piece log; partial/recovered acknowledgements cannot multiply
  the bytes just sent. Each copier lane keeps a time-weighted rolling rate. Ready-on-copy uses Sink upload statistics,
  never its film percentage as byte speed. Phone uploads carry the same measurements. Work state samples measured rates
  once per second (60 samples per lane and total); paused/stale work becomes zero, and job changes reset lane history.
  Transfers and copy detail graphs can read these points directly. Index input fingerprints make current() reflect a
  newly finished job without waiting for the service. The first piece is also included in lane-count learning.
- **Retest:** Deterministic 32 MiB / 8 s native pieces report 4 MiB/s including the final piece; two lanes at 2 and 3 MiB/s
  total 5, with independent graphs. 70 ticks retain 60 one-second points, preserve confirmed bytes and expire stale speed.
  The supplied build-442 log has no piece timings because startup keeps failing; it cannot establish actual bandwidth.
  Code already permits six lanes (starts at three, learns gains), native pieces up to 32 MiB, with lower cellular/playback
  limits. No evidence justifies increasing these caps. The clearly wrong aggregation/first-piece accounting is fixed;
  native/framework/network limits still require a post-fix device log.
- **Test:** scripts/test_upload_speed.py; test_season_sources queue visibility; check_project and all workflow-listed tests
  before commit. Host validation only; device throughput and rendering remain unverified.


## ISSUE-295 — Subtitle tracks could belong to another episode or fail the video's timing — filtered in backend

- **Request:** Build 442 item 6: reject clear subtitle mismatches, rank the rest, select the best and expose short reasons.
- **Cause:** Streams were shown by language only; downloads were ranked by release words and installed without checking
  cues. A ZIP containing one subtitle from the wrong episode bypassed the episode check. No playback-start matcher ran.
- **Fix:** A pure scorer reads SRT/VTT/ASS/SSA/MicroDVD and VobSub IDX timestamps, checks duration bounds, distant first/last
  cues, empty/short tracks (forced tracks exempt), filename/declared/preferred language, episode/absolute numbering and
  strong supplied/measured timing offsets. Ambiguous offsets do not prove mismatch. Tracks are ranked and clear mismatches
  cannot be installed. The downloader tries up to five candidates, validating before setSubtitles. A playback-start
  monitor automatically prefers the best allowed stream, preserves Off/current ties and later manual choices. Rows and
  KodiIOS.SubtitleMatches expose score/rejection/reason/timing evidence; no menu layout changed.
- **Retest:** Sixteen host cases include wrong-episode ZIP, bounds, formats, offset, language, forced captions, short/empty,
  conservative movie filenames, actual controller rejection/fallback, and the service adapter selecting the best stream.
  Important boundary: Kodi's Python/native probe currently exports embedded subtitle counts/names/languages, not DVD cue
  packets or speech timing. Such tracks say “Timing not checked”; their speech/timing cannot be verified in Python here.
  The scorer can use cue/speech intervals when supplied. Naruto DVD speech alignment still needs device/native evidence;
  no claim that text/speech recognition or an unavailable native cue API was implemented.
- **Test:** scripts/test_subtitle_match.py; existing test_track_menu, test_subtitle_sources and test_undefined_names;
  check_project and all workflow-listed tests before commit. Host checks only, owner playback retest pending.


## ISSUE-296 — Data for folded notifications, timed steps and live season-quality coverage — implemented without layouts

- **Request:** C1 identical-notice folding and 2/3-line data; N2 up to three timed steps; Q2 per-quality episode coverage
  as answers arrive, without sample-episode wording or any sheet/menu layout change.
- **Cause:** Raw notices had no reusable list/detail projection or retained lifecycle times. The quality sheet reported
  start/middle/end sample episodes and only a found/not-found flag; that was not whole-season coverage.
- **Fix:** notice_help.folded / notice_models.fold combine exact kind/title/text matches, preserve member IDs/unread state,
  count notice occurrences (not a stored season's episode count), and expose lines=2/3 from text length. A separate bounded
  runtime sidecar records copy-start/problem/retry/ready steps, folding starts across a season's concurrent episodes/files;
  notice_help.detail_model exposes timeline with actual time, colour_kind, kind and text. No notices.py routines changed.
  The Build Season check now scans every remaining episode once, reuses those answers for the build, and publishes exact
  found/total/checked/pending/unknown counts per quality plus checking_qualities. Empty/error responses stay unknown,
  never proof of absence; incomplete checks do not disable a quality. Sample-episode wording/helpers were removed.
- **Retest:** Exact-repeat folding with an existing episode count, immutable inputs, line count, timed-step reload/cap,
  pack-file identity, single-episode lookup, the real copier retry producer, partial/failed quality replies, and the real
  season builder publishing before completion all pass. Existing season sheet/source tests pass. UI binding and visual
  behaviour belong to the UI agent; this entry makes no rendering/device claim.
- **Test:** scripts/test_notice_season_data.py (seven cases), updated test_season_sheet, check_project and every listed
  import-review test before commit.


## ISSUE-297 — Permanent copy failures retried unchanged files — stopped and sent to Download problems

- **Request:** Follow up ISSUE-285: audit every RuntimeError in debrid_drive, driveupload and debrid_ready; stop retries
  that cannot repair a changed source, wrong size or invalid result, and explain the problem.
- **Cause:** Generic RuntimeErrors all entered the inline/later retry budgets. Permanent source/receipt/position failures
  were treated like connection failures; a main failure could be overwritten as done. Legacy phone uploads also retried
  the same unchanged file on each service pass. HTTP 403 was ambiguous without inspecting its reason code.
- **Fix:** copy_errors distinguishes permanent identity/integrity/access/input failures from transient network/rate/server
  and expired-session failures. Drive renews a refused access token once before a terminal refusal. All upload paths
  validate final receipts and confirmed positions. Permanent workers stop before inline retry, retain a clear reason,
  notify/history once, and expose a Download problem; companion failures stay isolated and completed companions still
  get their completion callback. Saved known permanent failures retire without another copy/unlock call. Terminal notice
  details keep the real reason and no longer offer an unhelpful Retry now.
  An explicitly rejected Drive ID stays a problem even when listed on Drive; a separate valid duplicate still wins.
  Phone uploads retain a failure fingerprint and mirror a source=phone failed job into the same index/problems record;
  automatic passes skip that unchanged file. A changed fingerprint or explicit manual retry clears the block/session;
  synthetic phone hashes are never submitted to AllDebrid. Failure/retry handling never deletes phone media.
- **Retest:** Changed source/size, native/buffered/resumed receipt/position, HDR verification, permission/quota errors,
  transient 403/429/5xx, expired sessions, token refresh, persisted errors, companion isolation and phone repeated-pass /
  fingerprint/manual-retry/index consistency cases pass. Remaining raw RuntimeErrors are recoverable metadata wait,
  premature source EOF and an upload not yet confirmed. The supplied private log has no RuntimeError or piece lines;
  it cannot identify the owner's original individual failure. Host checks do not prove device recovery.
- **Test:** scripts/test_terminal_copy_errors.py (26 cases); updated test_debrid_drive, test_drive_upload and
  test_library_tools fixtures; check_project and every workflow-listed test before commit.

## ISSUE-298 — Review of the PR #30 backend (Agent C, host review of 2cd5cdd): four fixes — fixed in code

- **Sign-out retired the whole copy queue.**
  - Cause: `copy_errors` treated "Sign in to Google Drive", folder access (401/403) and a full Drive as permanent. `debrid_drive` then failed every queued copy for good, which contradicts the Sign-in notice ("copies wait until you sign in").
  - Fix: `copy_errors.needs_owner()`. AllDebrid copies keep their place and wait 10 min between tries, with no try counted. Phone uploads still record the file's own problem row, so one file never holds up the others.
- **A blanket HTTP 4xx rule.**
  - Cause: any saved error text containing "http 4xx" retired the copy, including source/AllDebrid texts.
  - Fix: the rule now applies only to Google Drive's own answers.
- **The subtitle filter switched subtitles off.**
  - Cause: when no track was usable (all rejected), `PlaybackMatcher` selected Off.
  - Fix: subtitles now stay as they are. The reasons are still published.
- **Controls timer, first open after an update.**
  - Cause: Kodi evaluates all onload conditions first, so the open that set or moved the timer armed the old value (none, or 5 s).
  - Fix: that open is re-armed with a literal 00:03.
- **Tests:**
  - test_terminal_copy_errors: `needs_owner` cases, Drive-only 4xx, `test_signed_out_copy_waits_for_the_owner_and_keeps_its_place`.
  - test_subtitle_match: `test_no_usable_track_never_turns_subtitles_off`.
  - test_customisation: FIRST_ARM.
- **Handed to Agent A:** the reviewer's other high finding, the Umbrella source closed after 120 s of pause (the Resume crash, ISSUE-281).

## ISSUE-299 — Continue Watching did nothing for an Umbrella stream; the row only showed downloaded titles (owner, build 442, log beee3eba) — fixed in code

- **Seen (13:18:04 and 13:18:09):**
  - Two taps on Black Clover S2 E7 from Continue Watching. Each time: "watch: completed-copy check failed: SignedOut", and the menu stopped. Google Drive's sign-in had expired.
  - A fresh Umbrella play (13:18:37) reached the source card, but Umbrella had not handed the link to Kodi when the owner cancelled 15 s later. That is part of the stream fix (ISSUE-281/280 follow-up).
- **Cause:** `ios_watch_dialog.choose_player` stopped on any failed completed-copy check, so that a download would never start a second time. That also stopped every stream whenever Drive was signed out.
  - The row lists only titles with a saved position above 0. A stream that never starts never gets one, which is why only downloaded titles showed.
- **Fix:**
  - A failed check now carries on without a copy. Only Elementum (a real download) still stops with the old message.
  - `portrait.progress_tracker` logs one line per playback: "continue watching: following episode · umbrella", or "nothing recorded for this video". The next log shows what the row follows.
- **Tests:**
  - test_continue_downloads: `test_lookup_error_lets_a_stream_carry_on` (replaces the old stop-on-any-error test), `SignedOutDriveDoesNotBlockStreams`, and Elementum still stopping.
  - test_playback_retention: `ContinueWatchingSaysWhatItFollows`.
- **Also for the owner:** sign in to Google Drive again (Settings › Accounts). Copies wait for it (ISSUE-298).

## ISSUE-287 — The activity pill and its sheet are removed (owner, build 442: "I use Library status or the notification tray") — done in code

- **Owner decision (2026-11-14):** remove the activity pill and its sheet entirely.
- **Removed:**
  - `activity.py`, `activity_skin.py`, `activity_page.py` and the service loop that read Kodi's background box every half second.
  - The pill windows (Custom_1187_Activity.xml, portrait and landscape) and the sheet (IOSActivity.xml).
  - The pill's tap area injected into every page.
  - The start-up box that fed the pill ("Getting things ready").
  - The add-on settings category "activity".
  - Existing installs: `portrait.write` deletes the old pill windows.
- **Kept (moved to `skin_textures.py`):**
  - The ring_00–ring_20 textures (Notifications, Library status).
  - sheet_bg and row_only/first/last.
  - Kodi's background progress box drawn invisible (otherwise Kodi's own box would show again).
  - The fonts p_pill and p_pill_s (Notifications).
- **Kept (new `background_box.py`):** Elementum Burst's error lines in that box still reach Notifications, once per appearance. It looks every 2 s while nothing shows (the pill's loop looked every 0.5–1.5 s).
- **More menu:** "Transfers" (which opened the pill's sheet) is now "Library status".
- **Tests:**
  - test_skin_textures (new): textures and hidden box generated, no pill anywhere, old windows deleted, Burst error reported once, service wiring.
  - test_polling_loops (Burst watcher wake-ups), test_library_status, test_notice_log, test_speed_fixes (updated).
- **Phone check:**
  - No pill on any page, nothing where it used to be.
  - Kodi's own grey progress box never appears.
  - More › Library status opens Library status.
  - A Burst error still shows in Notifications.

## ISSUE-281 (continued) — No Umbrella stream played in build 442; Resume after a pause crashed — fixed in code

- **Owner, build 442:** no Umbrella stream plays, either fresh or from Continue Watching. Log beee3eba: the source card showed for 15 s with no hand-off to Kodi.
- **Fix 1:** the stream cache route for Kodi's own player (ISSUE-280) is off: `remote_media.KODI_PLAYBACK=False`. Kodi reads the AllDebrid link itself, as in build 430, so Umbrella's unlock no longer waits on the cache. Play on TV still uses the cache. The route can come back once it is proven on the phone.
- **Fix 2:** the broker never closes a source that is still Kodi's playing file, paused or not, up to 30 min with no read. Before, it closed it after 120 s with no read, so Resume met a dead 127.0.0.1 address (found by the PR #30 review).
- **Tests:** test_remote_media `test_the_route_is_off_by_default` and `test_a_paused_source_survives_while_kodi_has_it_open`. The ISSUE-280 route tests still run with the route switched on.

## ISSUE-300 — A resumed Umbrella episode took 23.5 s to open (owner, build 466, log 074adcd9) — fixed in code; rig-measured

- **Seen:** Continue Watching › Black Clover S2 E7: "open timing: 23.5 s via umbrella (handoff 3.2 s, open 20.2 s)". The hand-off was already quick; the 20 s was Kodi opening the MKV over one AllDebrid connection.
- **Cause (desktop Kodi rig, a local server at 0.7 MB/s per connection with 0.4 s per request):**
  - A plain MKV opened in 2.2 s. The same MKV with 20 MB of attached fonts, as Crunchyroll WEB releases carry, took 29 s.
  - Kodi read it in one sequential pass from byte 0, through all the font data, over one connection.
- **Fix:**
  - The stream cache route is back on (`remote_media.KODI_PLAYBACK=True`). It was switched off for build 466 because of the build-442 failure, which came from the ISSUE-282 restart loop (a new cache on every restart, with Kodi pointed at an old one); that loop is fixed.
  - The ISSUE-281 fallback was effectively always taken: it waited for the file's size, which was only known after the whole first 4 MB block (~6 s at 0.7 MB/s, more than its 5 s limit). The size now comes from the link's first answer (`Foreground.answered_size`), so the cache is used and the fallback is kept for a link that truly doesn't answer.
- **Rig result (`for_kodi` end to end, same file and speed):** hand-off 0.5 s, then Kodi's open 7.3 s, against 29 s direct. The cache read the start with four connections at once.
- **Tests:** test_remote_media `test_the_route_is_on_by_default` and `test_size_is_known_from_the_first_answer`; test_stream_fallback is unchanged and passes.
- **Phone check:** the `open timing … via umbrella` line for a resume, expected about 5–8 s instead of 20 s.

## ISSUE-301 — Refresh Library read every video one by one (owner, build 466, log 074adcd9: "the scan was a little slow") — resolved (owner log 181477d9, build 486)

- **Confirmed (build 486, log 181477d9):** Library status › Refresh: lists refreshed from Drive in 5.3 s (20:15:31.5 tap,
  20:15:36.9 done); only three videos were read again, each with its reason: Rick and Morty S1 E5 (repack), Iron Man
  (never checked), Fall 2 Deadpoint (repack). The build-466 slowness was the first Refresh after the library came back.

- **Seen:** 49 "preparation: compatible video kept unchanged" lines from 13:46:58 to 13:54:39, about 9.4 s per video, one at a time.
- **Code:** plain Refresh (`request_check(inspect=True)`) already skips a video whose last check was good and whose Drive file is the same (ISSUE-247, `settled`); only Check Every Video reads them all. Nothing in these checks changed since build 442 (INSPECT_VERSION 1).
- **Likely cause:** this was the first Refresh after the library came back from Drive, so no video had a settled check yet and all were read once. The log did not say why each video was opened.
- **Fix:** each re-read now logs its reason: never checked, last check failed, changed on Drive, checks updated, audit, repack, blocked, kept, not ready, or Check Every Video (`prepare_downloads.reread_reason`). The next Refresh shows whether anything is read again without a reason to.
- **Not done:** reading several videos at once. The native prober is shared with the converter (`inspection_deferred`), so it needs its own design.
- **Test:** test_compatibility_filter `RereadReason`.
## ISSUE-302 — Umbrella episode sat at "Opening the video · 4 of 12 MB", AllDebrid at 0.2 MB/s, no picture after 126 s (owner, build 470, log 2979ea67) — fixed in code, needs the phone

- **What the log shows:** Black Clover S02E07, Wi-Fi, nothing copying (`link: wifi`, 0 copy lanes). The cache was
  handed to Kodi (the opening card read its stats), the card said "AllDebrid is sending it slowly right now
  (0.2 MB/s)", and `open timing: no picture after 126 s via umbrella`. The log holds no line from the stream cache
  itself, so the link's own speed per connection is read from the card: 4 MB in about 20 s.
- **Cause:** ISSUE-280/281 put the cache between Kodi and the AllDebrid link. A block is 4 MiB and is fetched as ONE
  request; nothing is served until the whole block is here. Debrid links are slow per connection (ISSUE-163), so at
  0.2 MB/s a block took 20 s. The three opening blocks (first, second, last: 12 MB) were also fetched one after
  another, 60 s in all, and Kodi's own open waits for them (the first bytes, then the file's tail). Before the cache,
  Kodi read the link itself with no whole-block wait; the cache made a slow link look broken.
- **Not a regression of the source:** the link is genuinely slow (AllDebrid, cold file). This change makes the app
  use more connections on it; it cannot make AllDebrid faster. If the same file stays at 0.2 MB/s per connection,
  the opening takes about 12 MB / (8 connections x 0.2) = 8 s instead of 60 s.
- **Fix (`remote_media.py`):**
  - `Foreground._fetch` reads a block as `SPLIT` (4) ranges at once, joined in order (short last block and files that end
    inside a block are exact). At most `PIECES` (8) requests run at once for the source.
  - `prefetch` fetches the second and last opening blocks together, not one after another.
- **Retest:** host tests with a link throttled per connection (test_stream_slow_link): a block takes under 0.6 x the
  single-connection time, the three opening blocks under 0.5 x the serial time, the short last block is exact, at most
  8 connections. Both timing tests fail with `SPLIT = 1`. **Not proven on the phone**: it needs the owner's iPhone.
- **If it is still slow on the phone:** send the next log. The cache logs nothing about itself, so the next step is a
  log line with the first block's time and the connection count, and a fallback to the direct link when the first
  block has not arrived after about 15 s.
- **Test:** test_stream_slow_link (new); test_remote_media now counts blocks, not requests.


## ISSUE-303 — Umbrella never opens in build 473 after partial opening progress — source fix; device retest pending

- **Owner:** build 473, opening card repeatedly moves between 0, 4 and 8 MB; video never opens.
- **Evidence:** current private log SHA-256 `3ea31786284de14c35e2a9c98a9a74f22012dbd91f20b881d5aacc9ad0b5bb8c`, build `ceb06e7`: system networking, source selection, roughly 45 seconds without a player-open event. Old log SHA-256 `97c9e567dd5cb200afe227276fc7d9b71573504ed2a64539eb5f8791d816dcf8`, build 470 `1bc5d1e`: separate no-picture timeout after 126 seconds. No evidence of concurrent copy traffic in the relevant snapshots. No claim that the shorter build-473 capture contains that timeout. Private logs remain outside Git.
- **Reproduced cause:** `answered()` accepted Content-Range size before the opening blocks were complete. The iPhone's system opener buffers a split piece before returning; one finished piece can still expose the size while the rest of that block stalls. The loopback handler needs a complete block before answering HEAD, so premature handoff strands Kodi behind an unfinished probe. Five of the original seven real-HTTP regression cases fail on unchanged build-473 source.
- **Additional reproduced gaps:** closing the cache left active upstream readers alive; split pieces with conflicting totals could be joined; the request cap missed unsplit reads; independent timeout budgets could extend opening across later probes and redirects.
- **Fix:** require complete validated first/second/tail blocks (deduplicated and clipped for small files) within one five-second opening budget. Otherwise drop the cache and return the original direct URL and pipe headers unchanged. Track/interrupt active reads, stop queued requests, cap every request, validate complete joined ranges and consistent file identity. Native redirect sends and renewed-link retries use the same deadline. No native rebuild or UI redesign.
- **Diagnostics:** one safe opening line logs route, elapsed milliseconds, completed/required/pending blocks, byte/request/error counts and status, without URLs, credentials or media IDs. The supplied logs do not establish the exact mechanism behind every progress reset; this line makes the next phone report distinguish fallback from cache admission.
- **Validation failure retained:** initial combined checks found stale fallback mocks expecting size alone, a brittle source-text assertion, and a real regression in changed-file rejection when only `blocks.sizes` knew the prior total. Restored that identity check; renewed-file regression suite passes. Updated the old readiness fixtures to assert actual completed readiness.
- **Regression protection:** real socket stalled-body/native-buffered/next-playback/resume tests, range-integrity and resource-cleanup tests, native redirect/deadline tests; added the new suites to the IPA workflow. Final counts and artifact follow in [UMBRELLA-473-PROGRESS.md](UMBRELLA-473-PROGRESS.md).
- **Limits:** all-probe admission can deliberately fall back on a valid slow provider. Five seconds bounds the cache attempt, not total playback time; direct Kodi/provider throughput remains independent. Host tests cannot prove a fix on the owner's iPhone. Owner authorized a testing IPA on 2026-11-14; no merge requested.

## ISSUE-304 — Favourites import glued an unnumbered line onto the line before it (owner, PR #29 review, 2026-11-14) — fixed in code

- **Seen:** in a numbered list, "‼️ Attack on Titan" (no number) merged into "Naruto Shippuden", giving one entry
  "Naruto Shippuden Attack on Titan". The numbered-list reader joined every line before splitting at the numbers, so a
  title without a number vanished into its neighbour.
- **Owner's real list** (56 lines: numbers, ✅ ‼️ 🎥 markers, "(3)" watch counts, "(STARTED)", "//" splits, "RYANNE"
  notes) is now the test's sample.
- **Fix (`favourites_import._lines`):** a line without a number is its own entry. It rejoins the line before only when it
  is plainly the tail of a wrapped title: it starts in lower case or with a bracket and the line before ends in a letter
  or digit (no tick or marker). Whatever precedes number 1 (the list's key or legend) is still dropped. A paste with no
  line breaks still splits at each number.
- **Test:** test_favourites_import `OwnersList` (the real list reads one title per number; an unnumbered line is its own
  entry, with or without markers; a wrapped tail rejoins).

## ISSUE-305 — PR #29 merged into build442: Favourites list import and the anticipated-episodes bell (DEC-053)

- **What:** PR #29's branch (claude/modest-hopper-8z5ar8, features coded 2026-11-14, owner-approved mockups G–J) is merged
  into this branch. Conflicts: default.py's page list keeps both lists and drops `activity_page` (ISSUE-287);
  check_project's mockup list, DECISIONS.md and PROGRESS.md keep both. Its decision, which used DEC-047 (taken by the show
  page here), is DEC-053.
- **Host tests:** test_favourites_import, test_favourites_flow, test_anticipated_bell; the full list passes.
- **Gaps against the approved mockups (from the review), handled in the next entries:** the bell sheet (G3), the import
  report, J3.

- **ISSUE-303 delivery checkpoint:** testing IPA [475](https://github.com/onlykappa/Kodi-Ios/releases/download/build-475/Kodi-iOS-Customized-Touch-r10.ipa), source `2f447c7`, CI run 43653853433 succeeded. 125 focused host checks pass; downloaded IPA digest/ZIP/source/pins verified. Owner iPhone retest remains pending.

## ISSUE-306 — Umbrella still never opens in build 475: six sources handed over in a cycle, none plays (owner, log eadd0349) — loop broken; cause on the phone still to confirm

- **What the log proves (build 475, c1bb11c, Black Clover S02E07):**
  - Every hand-off to Kodi is a `stream opening: route=cache … ready=True blocks=3/3 errors=0 status=206`, 3 to 4.4 s
    each. The ISSUE-293/303 cache fixes work: the three opening blocks (9 to 12 MB) arrive in about 4 s.
  - Ten of them follow one another about 5 s apart, from 15:50:26 to 15:51:08, until the owner cancels. Their byte
    counts repeat in a cycle of six (9.2, 10.2, 11.9, 9.9, 9.8, 8.6 MB, then 9.2, 10.2, 11.9 again): Umbrella goes
    through its six sources ("kept 6") and starts again. Each hand-off is Umbrella resolving a source; it moves on 1 to
    2 s after it is given the cache's address.
  - Kodi logs no error in that window (`OpenInputStream`, `CDVDInputStream…` and similar are errors and would show), so
    Kodi was not asked to play, or did not report failing. Umbrella moves on without playing.
  - Where the cache route was off (build 466, log 074adcd9) the same episode played, after 23.5 s. Every build with it
    on (470, 473, 475) has not opened on the phone.
- **What it cannot prove:** why Umbrella rejects the address. Its code is not in the repo or the IPA (it is installed
  when the app first runs), and the log has no line from Umbrella. A host test shows the cache answers HEAD, plain GET and
  Range requests correctly, so the address's shape is the difference we can act on:
  - the cache's address was `http://127.0.0.1:PORT/SECRET/media/source` with `Content-Type: application/octet-stream`.
    The Drive proxy, the loopback server Kodi really plays Drive copies from on the phone, serves `/drive/<id>/<file
    name>` with a video type. No Kodi video path had ever played from the cache's shape on the phone.
- **Fix (`remote_media.py`, `drive_stream.py`):**
  - Kodi now opens `…/media/<the file's own name>.mkv` and the reply says `video/x-matroska` (`video/x-msvideo`,
    `video/webm` for those). The AirPlay engine reads the same server and ignores the last part.
  - The cache counts the bytes a reader really took (`served`, in the stats and in the `stream opening` log line).
  - A hand-off made within 90 s of one whose bytes Kodi never read (`served == 0`) is played DIRECTLY, and the old
    cache source is dropped: the cycle stops at the second source instead of going round. The log line says
    `route=direct … served=0 reason=previous source never read by Kodi`.
- **Phone check (this is the step that settles it):** play the same episode. In the log, after the first
  `route=cache` line, expect either playback (and no second hand-off) or one `route=direct reason=previous source
  never read by Kodi` line and playback from the direct link (about 20 s, as build 466). `served=N` on the later lines
  says how much Kodi took from the cache. If it still cycles, the log now shows `served`, which says whether Kodi
  ever connects to the cache.
- **Test:** test_stream_loop (address and type, served count, loop goes direct, a read source and a later play are not
  loops, the log line).

## ISSUE-307 — The bell sheet as approved (G3): real switches and Done, slim pill switches (owner, 2026-11-15) — done in code; rig-checked

- **Request:** PR #29's review: the bell sheet was the choice sheet with On/Off tags and Cancel, not board G3. Owner, on the
  rig render: "the s is cut off and the switches look a little bulky, should be more pill shaped, not so fat".
- **Fix (`choice_sheet.py`, `anticipated.py`, `anticipated_bell.py`):** rows can carry a `switch` (on/off): the chevron is
  replaced by a 112 x 56 full pill (green on, grey off, white 46 knob). `choose(..., toggle=)` flips a switch in place:
  the sheet stays open and saves each flip at once; the bottom button says Done. A switch row's text column is 110 units
  narrower, so long lines wrap clear of the switch. Other sheets keep their chevron and Cancel.
- **Retest:** desktop Kodi rig (rig_smoke_sheet.py bell): two rows, slim pills, Done, nothing cut. Not the phone.
- **Test:** test_anticipated_bell (switch rows, properties, a switch flips in place and Done closes); test_favourites_flow.

## ISSUE-308 — The import report: a full page (board I3) from Notifications or Import a List, never popped up (owner, 2026-11-15) — done in code; rig-checked

- **Request:** owner: "full page … don't make it pull up when it's done, make a place for me to manually check"; then "put
  the notice in notification center … if I tap it, it can open that page"; mockup N/R/S approved ("moneyyyy").
- **Fix:**
  - `favourites_import.save_report` keeps the last import (duplicates, open questions with their choices, names not found);
    `report_properties` builds the page; group texts list whole names, then "and N more" (`listed`, measured to three lines).
  - `favourites_report_page.py` (IOSImportReport.xml): Last import, the added card, Duplicates / Needs your answer (blue) /
    Not found (orange), each as tall as its text, a footnote, View Favourites. Needs your answer asks one "Did you mean…"
    per name; Not found opens the keyboard with the name to search again; answered names leave the report.
  - After an import nothing opens: a Notifications message "Import finished · N added … · M need a look" with a star and
    Review ›; tapping it opens the page (`favourites_import_page report`). Import a List has a third row, Last import.
- **Retest:** desktop Kodi rig: the message with the star and Review ›, the report page; nothing cut. Not the phone.
- **Test:** test_favourites_flow (no pop-up, the message, the saved report, the page's groups act, Last import row, "and N
  more", the message's star/Review and its tap).

## ISSUE-309 — Umbrella still took 13-28 s to open and glitched just after it started (owner, build 477, log 47ee1590) — fixed in code; needs the phone

- **What the log shows (build 477, Black Clover S02E07, three plays):** ISSUE-306 worked: no more source cycling, every
  play started. Timings: 15.9 s (cache; hand-off 7.5 s, Kodi's open 8.4 s), 28.4 s (direct: the cache had 1 of its 3
  opening blocks after its 5 s budget; Kodi's open 20.5 s), 12.9 s (cache; 5.2 + 7.7 s).
- **Concrete cause:** while each stream opened, the app was copying a 4K film (Iron Man 2160p) from AllDebrid to Drive
  and preparing it for AirPlay ("AirPlay: prepare: carrying on from 6206 s, byte 4978723283") at full speed. Its Drive
  pieces took 0.2-0.7 s before the open and 3.6-9 s during it: the phone's line was shared. The slowdown rule
  (`slowdown.reason`) only looked at `Player.HasVideo` and `Player.Caching`, which are false while Umbrella resolves a
  link and Kodi opens the file, so nothing slowed until the picture appeared (16:31:45.48 "Slower while a video plays",
  9 s after the open began). Then copies were held but preparation went on at its share; the audio stalled 4 s after the
  picture ("CVideoPlayerAudio::Process - stream stalled"): the glitch the owner saw.
- **Fix (`slowdown.play_reason`, service.py):** the watch add-on's start mark (Home `KodiIOS.Open`, set when Stream is
  tapped) counts as `buffering` (copies, uploads, preparation and background downloads wait) until the video has played
  for 15 s (`SETTLE`), 120 s at most (`OPENING_LIMIT`). Then the usual 'video' rule applies. AirPlay and Kodi's own
  buffering keep their rules. The stream cache's own reads are not slowed (its gate is the foreground one).
- **Expected on the phone:** the cache's opening blocks within its budget every time (no `route=direct` from a busy
  line), Kodi's open close to the rig's 7 s, no stall after the picture. Background work pauses for about 15-30 s per play.
- **Test:** test_opening_hold.

## ISSUE-310 — A movie copying (and being made ready) showed nowhere as running (owner, build 477, log 47ee1590) — fixed in code

- **Seen:** Iron Man 4K was copying from AllDebrid and being made ready for AirPlay ("made ready while it copies",
  5.1 of 6.0 GB). The library index logged it every minute ("1 working (1 copying)"), but Library status and the
  Notifications page never showed anything running when the app opened.
- **Cause:** every screen (Library status, Transfers/Queue, Running now, the bell) reads one model that
  `work_state.from_index` builds from the library index (ISSUE-293); a live copy is attached to its index entry by
  `same_copy`. That compared the copy's job id (`hash:season:episode`) with the entry's season/episode: a movie's job id
  is `hash::` and its entry is season 0, episode 0, so no movie ever matched. Each running movie copy was demoted to a
  quiet "queued" row (`drive_next`): not under Working now, not in Running now, no bell ring. Episodes have numbers, so
  they matched; that is why only films disappeared.
- **Fix:** an empty season or episode counts as 0 when matching; a positive match returns at once, anything else falls
  through to the existing file-name and season-pack checks.
- **Audit (owner: "ensure all screens use the library index"):** Library status, Transfers/Queue, Notifications' Running
  now and the bell all read that one model; the remaining direct reads of the copy/preparation state only pick which
  job a card's Cancel/Pause acts on. Library, AI Upscale (ISSUE-288), Download problems and deletes use the index.
- **Test:** test_queue_index `test_a_movie_copy_being_made_ready_shows_as_running` (running, not queued; "Getting it
  ready for Kodi and AirPlay"; the same in Library status, the Queue, Running now and the bell). Fails on the old code.

## ISSUE-311 — Reviewer low items: orphaned pill strings, Continue Watching panel on the video controls not refreshing

- **Cause:** (1) ten settings strings (#32001-#32010) of the removed activity pill were still in `strings.po`, and
  `rig_smoke` had a pill entry (already removed). (2) The video controls' Continue Watching panel (`player_osd.py`) did not
  end with the hubs' `&stamp=` (`portrait.CONTINUE_STAMP`), so Remove From Continue Watching did not refresh it.
- **Fix:** the strings are deleted. The panel's path now ends with `CONTINUE_STAMP`, XML-escaped (`&amp;`) at the use site;
  an unescaped `&` made the controls window not well-formed (found by test_customisation, two errors).
- **Retest:** test_customisation passes again.
- **Test:** test_review_low_items (no pill strings, the controls window parses and its panel ends with the stamp).

## ISSUE-312 — J3: opening a favourite show did not mark its in-progress episode "Continue"

- **Cause:** the show page is TMDb Helper's seasons/episodes list; the app's own progress (continue.json) never reached it,
  so only Kodi-library items drew a progress bar. The page docstring claimed episodes carried Continue; nothing did.
- **Fix:** `favourites_import_page.mark_show` (on opening an imported show) finds the show's latest unfinished episode in
  continue.json (30 s in, under 92 %) and sets Home properties `KodiIOS.ShowContinue{Tmdb,Season,Episode,Left}` (cleared when
  none). `portrait.episode_item` shows a blue "Continue · 11:20 left" line on the matching episode of that show only
  (season, episode and the folder path's tmdb_id must all match).
- **Retest:** host test only; the rig cannot list a show without TMDb (network). Needs the phone.
- **Test:** test_favourites_flow `test_a_show_page_marks_the_episode_in_progress_continue`.

## ISSUE-314 — A show added by hand with Add to Favourites did not appear once a list was imported (owner)

- **Cause:** `favourites_page.read` returned `(imported + own)[:90]`. The owner's import fills the 90 cells, so Kodi's own
  favourites (long-press > Add to favourites), which came after it, were cut off.
- **Fix:** `favourites_rows.merged`: hand-added favourites lead, newest first (Kodi appends new ones, so its order is
  reversed), and are never trimmed; the imported list follows, trimmed to what is left of the 90 cells. A title in both
  shows once, as the hand-added one (same TMDb id and type, or the same name, and year when both have one). `entries`
  now carries each favourite's `tmdb` id. TMDb Helper tv/movie favourites already count for the Shows/Movies chips (`kind_of`).
  Rank badges (#n) stay on imported rows only.
- **Retest:** desktop Kodi rig: a show added with Favourites.AddFavourite while 90 imported titles are seeded shows first.
  Not the phone.
- **Test:** test_favourites_flow `HandAdded`.

## ISSUE-315 — An Umbrella episode took 41.8 s to open: two hand-offs raced; the cache route's own open took 9 s (owner, build 479, log bdbdac02) — fixed in code; needs the phone

- **What the log shows (Black Clover S02E07, good network):**
  - 18:00:04 play: 41.8 s (hand-off 17.9 s, Kodi's open 24.0 s). TWO `stream opening` lines for this one play, from two
    threads: hand-off A began about 18:00:16.9, hand-off B about 18:00:17.6, for different links. The cache holds one
    source, so B's `open` closed A's. A's readiness check then saw another source's stats and returned at once:
    `route=direct wait_ms=1019 blocks=0/0`. Kodi played A's link directly (`VideoPlayer::OpenFile` 18:00:22.7, demuxer to
    probe 26.7 → 46.4: 20 s over one AllDebrid connection). B finished at 18:00:22.98 (1 of 3 blocks), too late.
  - 18:00:55 play: 16.6 s on the cache route (hand-off 7.3 s, of which 4.6 s fetching the 9 MB opening blocks; Kodi's
    open 9.3 s). Kodi reads on past the three opening blocks while it opens an MKV (tracks, attached fonts), and those
    blocks were only fetched once Kodi asked for them.
  - The opening hold (ISSUE-309) worked: "Waiting while a video opens or buffers" at each play, "Slower while a video
    plays" after.
- **Fix (`remote_media.py`):**
  - A Kodi source opened under `RACE` (20 s) ago is kept beside a new one (`Broker.previous`, one at most) instead of
    being closed. `stats`, `drop` and `origin` take the hand-off's own id, so each hand-off checks, keeps or lets go of its
    own source. The kept one closes when Kodi has left it alone for KODI_IDLE (or never read it), after a minute at least.
  - Once the opening blocks are in, the next `KODI_AHEAD` (4) blocks (16 MB) are fetched at once (`prefetch(extra=)`).
- **Unknown:** why Umbrella resolves two links for one play (its code is not in the repo). Both now finish on the cache.
- **Test:** test_stream_race (a second hand-off keeps the first source alive and serving; each sees its own stats; one
  previous at most; the next blocks are fetched with the opening). Fails on the old code.

## ISSUE-316 — Scrolling is poor on every page but Home, Movies and TV (owner, build 442 item 9) — Kodi patch ready; needs a native build (r33) and the phone

- **Measured (desktop Kodi rig, System.FPS while dragging, uncapped):** Home ~135-139; Notifications ~70-97; Library
  status ~86; Favourites ~64-68. The page under a dialog is not the cause (Favourites opened over an almost empty window
  was no faster).
- **Cause (Kodi 21.3 `CGUIControlGroupList::Process`):** "we render all controls, even if they're offscreen": a group
  list calls `DoProcess` on every child on every frame. Home, Movies and TV are a group list of rows that are *lists*,
  which process only the items on screen; every other page is one long group list (90 favourite cells, every
  notification row, every status row), all processed on every frame wherever the page is scrolled. The touch flick and
  its momentum are the same for both (portrait patch, ISSUE r20); the frame rate is not.
- **Fix (`kodi-21.3-portrait.patch`, GUIControlGroupList.cpp):** a visible child more than one screen above or two screens
  below the visible part (and without focus) is not processed; its visibility is still updated (sizes stay right) and it
  is processed again as it comes near.
- **Retest (rig A/B, same session, same pages):** original Home 139 / Favourites 68 / Notifications 70; patched Home 140 /
  Favourites 83 / Notifications 88 fps. The phone's CPU has far less headroom, so the gain there should matter more; only
  the phone can say how it feels.
- **Release:** needs the native executable rebuilt as `kodi-ios-portrait-r33` (source-lock `build_tag`, `patch_sha256`
  updated; `executable_release` stays r32 until r33 is built and its digests checked), then the IPA pinned to it. Held
  for the owner's OK; the change waits on branch claude/wip-smooth-scroll.
- **Test:** test_smooth_pages (the patch skips far children; the lock names r33 and this patch).

## ISSUE-317 — Umbrella: 12 MB loads fast, then "loading video" sits ~30 s (owner, build 482, logs d3c14036 / cf038697) — fixed in code; needs the phone

- **Seen (owner):** play 1 on the cache route, all 3 opening blocks ready in 4.3 s, then Kodi's open took 31.3 s. Play 2
  fell back to the direct link (2/3 blocks after 5.3 s) and opened in 19.6 s. The card loads 0–12 MB quickly, then sits
  at "loading video". So the network was fine, and the time goes after the hand-off, inside Kodi's open through the cache.
- **Rig (desktop Kodi rig, set up like the phone):** the portrait patch's 3 MB / 3 s probe limits, filecache 96 MB /
  readfactor 1000, a null ALSA device. The test MKV's attachment data was turned into EBML Void elements, so FFmpeg
  seeks past each font as the phone's patched FFmpeg does. A throttled server ran at 0.7 MB/s per connection with
  0.4 s per request, and `for_kodi` was tested end to end.
  - Kodi's open seeks across the font area (e.g. 10.8, 17.0, 20.7, 21.0 MB), then reads from the first cluster. Those
    offsets are in blocks 2–5, outside the three opening blocks, so Kodi waits for them.
  - 30-font MKV (about 20 MB): direct 16.9 s (15.2 s seeking); cache as in build 482 3.8 s hand-off + 4.7 s = 8.5 s;
    24 MB before admission with a 15 s wait 7.4 s + 1.1 s = 8.5 s (only moves the wait); 16 connections instead of 8:
    Kodi's demux wait 3.7 → 1.9 s.
  - The rig does not reproduce a 30 s stall with a fast link.
- **Concrete cause (owner log cf038697, play 1, 18:35):** `stream opening: route=cache wait_ms=4282 blocks=3/3 errors=0`,
  `Creating Demuxer` 46.21, then Kodi's reads from the cache were cut three times: `CCurlFile … Transferred a partial
  file(18)` at 51.60, 05.45 and 16.61 (with `CFileCache::Seek … failed to get remaining data` and `source read returned 0!
  Will retry`), and `probe limits` only at 17.46: 31.3 s. The loopback server cuts a read only when the block it waits on
  fails (`drive_stream` closes the connection), and each cut cost Kodi 5-14 s before it read again. Weak spots found in
  the code: (1) the opening's 5 s budget (deadline + 5 s connect timeout) applied to every request of the source,
  including the KODI_AHEAD blocks started at ~4.3 s, which got well under a second to download a 1 MB piece (the phone's
  native opener buffers the whole piece within that timeout), and to Kodi's own reads made before the budget was cleared;
  (2) a block that failed after its 3 tries per piece cut Kodi's read instead of being fetched again. The exact error of
  each failed block is not in the build-482 log; the new `cache block: … error=` lines will name it.
- **Changed (`remote_media.py`, `drive_stream.py`):**
  - Every read Kodi makes through the cache is logged as it starts and as it ends (`Kodi iOS cache read: at= offset=
    asked=` / `read done: sent= took= waited= waited_for=`), and every block fetch with its time or error (`Kodi iOS
    cache block:`). This covers the first READ_LOG_FOR (90) seconds, at most 150 lines, with no URLs.
  - Served bytes are written in 1 MiB slices, so `sent=` and `served=` count what a reader really took.
  - Upstream requests go through `_Gate`: the same cap (PIECES), but a free place goes to a block Kodi waits on, then
    the opening blocks, then read-ahead. The KODI_AHEAD blocks start with the opening ones once those have queued.
  - `OPEN_BLOCKS` (default 2, as before) sets how many leading blocks must be in before Kodi is handed the cache.
  - The opening budget applies only to the blocks that decide the route (the opening blocks and the last); the next
    blocks, read-ahead and blocks Kodi waits on always get the normal 20 s timeout (`budgeted` in `remote`, the deadline
    read live so a renewal still uses up the budget).
  - A block a reader waits on is fetched again up to BLOCK_RETRIES (2) more times before the read is cut.
- **Rig after the fix:** same file and speed, the cache route 3.8 s + 4.6-4.7 s, no block errors, 60 read lines logged.
- **Expected on the phone:** no `Transferred a partial file` while an Umbrella stream opens; `open` a few seconds. If it is
  still slow, the `cache read` / `cache block` lines show which read waits and why.
- **Test:** test_stream_reads (read trace without the address, the log window, gate order, priorities, OPEN_BLOCKS, the
  budget only for the opening blocks, a failed block fetched again; the last two fail on the build-482 code).
  test_stream_opening_fallback now counts only the `stream opening` line, and still checks all lines for private data.

## ISSUE-318 — Build Season check named sample episodes, showed empty "4K · …" placeholders and a gap (owner, build 442) — Q2 done; rig-checked

- **Cause:** the check card was drawn for a fixed three-episode lookup ("Looking at episodes 1, 6 and 10"), with one
  placeholder slot per quality, a fixed 3-row card and empty space under it. The header read "· 10 episodes" when the
  show title was empty.
- **Fix:** owner-approved Q2 (docs/design/build442-mockups.html), on the backend's live coverage (ISSUE-296).
  - `season_check.chips`: the found qualities as up to three chips, green "1080p · all 21" for the whole season and
    orange "720p · 18 of 21" for part of it. One plain intro line until something is found; "Still looking · …" or
    "None found · …" under the bar. No sample-episode numbers.
  - `pages.season_quality_sheet`: the card ends right under the bar and its line (one or two chip rows). While it
    checks, the sheet's top comes down to meet Build (conditional slides; `_sheet(shift=)`), so there is no gap. A
    sliding bar while it looks.
  - `season.sub` drops an empty title.
- **Rig (desktop Kodi rig, `IOSSeasonQuality.xml` with properties from the real model):** nothing found yet, two partial
  chips, three chips (two rows), done with "None found · 4K". No gap, nothing cut off.
- **Test:** test_build442_sheets `Q2Chips`; test_season_sheet (the 20-step bar is gone; chips and the slide are present).

## ISSUE-319 — Notification detail: a fixed tall sheet with gaps, no sense of what happened when (owner, build 442) — N2 done; rig-checked

- **Fix:** owner-approved N2 (docs/design/build442-mockups.html).
  - `notifications.detail_properties` reads `notice_help.detail_model` with the profile, which loads the retained steps
    (ISSUE-296), and publishes up to three `tl.N.time / text / tint` steps (blue copying, orange problem or retry,
    green ready). Old notices get no invented steps.
  - `notice_page.sheet`: what happened, the timeline, then the actions as one grouped list (`status_ui.row_back`; each
    row's place set as `fixN.pos` / `tech.pos`): the main fix in blue, the other fixes, and Technical details as the
    last row ("What the app logged, Share Log"). Parts that are not there close up (grouplist), and the sheet comes down
    by their height, so it is as tall as what it says. Technical details keeps the full-height view.
  - Also fixed: the plain view's condition was built as `!!String.IsEmpty`; it now uses `status_ui.neg`.
- **Rig:** with a timeline and without one, plus the Technical details view. Nothing cut off.
- **Test:** test_build442_sheets `N2Timeline`; test_notice_log (every property the sheet uses).

## ISSUE-320 — A copy's details sheet: conversion steps, blank Average / Started, cut-off text (DEC-051 board B) — done; rig-checked

- **Fix:** owner-approved board B (docs/design/unified-status-mockups.html).
  - A copy's sheet keeps the conversion sheet's layout (speed card, Pause and Cancel) with its own steps: "Found on
    AllDebrid" (or "Fetching on AllDebrid"), "Copying to Drive · N%", "Ready for Kodi and AirPlay".
  - `library_rows.speed_card_text` fills Average, Done and Started from the lane's own samples and Drive's confirmed
    bytes (ISSUE-294) when there is no older history record.
  - Rig found two cut-off texts (DEC-050): the step labels ("Found on AllDeb…", "Ready for Kodi …") now wrap to a second
    line, and the needs card's sentence ("…saved sign-in. Downloa…") wraps to three lines (`status_ui.NEEDS_H`).
- **Rig:** the `airplay` scenario's Inception copy and the Scary Movie conversion sheet: everything fits above the
  buttons, nothing cut off.
- **Test:** test_build442_sheets `BoardBCopySheet`; test_build193_pages allows wrapping for exactly these two labels.

## ISSUE-321 — Umbrella stream stuttered just after it started; glitchy on exit (owner, build 486, log a30fb0aa) — fixed in code; needs the phone

- **Seen:** two plays of Black Clover S2 E7, both opened in 8.6-9.1 s (open 2.1-2.2 s: ISSUE-317 holds). About 1-2 s
  after the picture, every block fetch in flight failed with `ConnectionError` (blocks 2-4 after 5.7 s, 6-9 after 2-5 s),
  Kodi's reads waited 6.6-22.9 s (`waited_for=6,7,…`) and the audio stalled ("stream stalled"); later fetches of the
  same blocks succeeded, block by block at 5-8 s each.
- **Causes found in the code:**
  - The ISSUE-309 settle hold never held: `slowdown.play_reason` read the start of the play from `KodiIOS.Open`, which the
    open-timing line clears as soon as the picture plays, so "Slower while a video plays" came 1 s after the picture
    instead of 15 s.
  - The next blocks fetched after the opening (KODI_AHEAD, blocks 2-5) were the MKV's attached fonts, which this Kodi
    skips: Kodi read 0-6.3 MB and then went straight to the first video at 22.57 MB (block 5). 12 MB of unused fetches
    competed with the video's blocks at the moment playback began.
  - A failed block cost Kodi a full new block fetch through the same crowded connections; the trace logged only the
    error's type.
- **Fix:**
  - `play_reason` remembers the play's start until the video stops (SETTLE 15 s now holds after the picture).
  - `remote_media.video_start` walks the MKV's top-level elements in block 0 (tracks, attachments, tags) to where the
    first video begins; the next blocks are fetched from there.
  - A block that fails on the way (not an answer that contradicts the file: `INTEGRITY`) is fetched once more over one
    connection, and the request gate gives half its places for CALM_FOR (30) s.
  - The trace names the error and its words, with addresses removed (`describe`).
- **Rig (desktop Kodi rig, 30-font MKV, 0.7 MB/s, a 6 s window where the server drops every connection):** old and new
  both rebuffer about 5-6 times. A total outage cannot be retried around, and the phone's failure (slow, partial) is
  not reproduced. The new trace line will name the phone's error.
- **Test:** test_stream_reads `Stutter`, `SettleHold`.

## ISSUE-322 — Holding a favourite closed Favourites and opened Kodi's menu with "Add to favourites" (owner, build 486) — fixed in code; rig-checked

- **Cause (log 181477d9):** iOS sends a long press as Back (10) and then the context menu (117); Favourites closed on the
  Back and Kodi's own context menu opened over Home.
- **Fix (`favourites_page.py`):** on a poster a long press opens the page's own menu (the choice sheet): Download (the
  existing download script: a movie, or a season of a show), View Details (TMDb Helper's info window, 1190), and Remove
  from Favourites last, in red. No "Add to favourites". The second action of the same press is ignored, as in Library
  status (ISSUE-196).
- **Rig:** the menu renders with all three rows and Cancel, nothing cut off. Download and View Details need the phone
  (TMDb and Elementum are offline in the rig).
- **Test:** test_favourites_menu `Menu`.

## ISSUE-323 — A 96-name list added 58; 20 "not found" (owner, build 486, log 181477d9) — lookups retried; names logged

- **Seen:** "favourites import: 96 lines, 57 added, 1 known, 21 questions, 20 not found". The 21 questions wait for a
  pick in Import a List › Last import (several titles close to the name); the 20 are listed there as not found.
- **Cause found:** a lookup that raised (a timeout, TMDb busy) was counted as "not found" without a second try.
- **Fix:** each lookup is tried up to three times; one that keeps failing is marked and logged as "could not be looked
  up". The log names the titles not found, failed and waiting for an answer, so the next import shows which it was.
- **Test:** test_favourites_menu `Lookups`.


## ISSUE-324 — "Seven deadly sins" asked between four obscure shows and never offered the anime (owner, build 486) — matcher fixed; poster picker mocked up

- **Seen (screenshot):** Last import › Needs your answer: "Seven deadly sins" offered four "Seven Deadly Sins" (TV 2010,
  1966, 2008, 1993), each shown only by its year; "The Seven Deadly Sins" (the 2014 anime) was not among them. Not found
  opened the keyboard for each name in turn ("a typing page").
- **Cause:** `favourites_match.norm` kept a leading "the", so the exact-named obscure titles scored 1.0 and the anime
  scored lower; only titles within 0.02 of the top are offered.
- **Fix:** a leading The / A / An is ignored when matching. The anime now scores 1.0 too and, being far more popular
  (ISSUE-305's 3x rule), is matched without asking.
- **Not built yet:** choosing by poster instead of by year (boards K7 and K8 in docs/design/favourites-manager-mockups.html,
  for owner approval with K1-K6).
- **Test:** test_favourites_import `test_a_leading_article_does_not_hide_the_famous_title` (the fake search now
  normalises its own keys).

## ISSUE-350 — The IPA build was killed by its own 10-minute limit while publishing (run 43769622376, build of claude/sports-ipa) — fixed in the workflow

- **Seen (2026-11-15, 22:30–22:40 UTC):** `import-review.yml` dispatched on `claude/sports-ipa` (PR #31's head plus the Sports work). Steps 1–11
  passed, including "Build and validate full customized unsigned ARM64 IPA"; step 12 "Publish raw IPA as a prerelease download" was cancelled after
  the job had run 10 minutes 12 seconds. No release was made.
- **Cause:** the `review` job's `timeout-minutes: 10`. Each added test suite (the Sports work added five) and step makes the job longer; build 528 had
  finished just inside the limit.
- **Fix:** `timeout-minutes: 25`.
- **Retest:** the build is dispatched again; a release `build-NNN` must appear (recorded in docs/PROGRESS.md).
- **Test:** `scripts/test_workflow_limits.py` (the limit is at least 20 minutes, the publish step is still there).

## ISSUE-349 — Play on TV to a Roku (its own player) showed no progress while the phone made the stream ready (owner: "make airplay work seemless on any device mainly roku") — fixed in code

- **Seen (review):** ISSUE-345's banner was only made on the AirPlay route (`send_airplay`). Play on TV to a Roku, a
  smart TV (DLNA) or a Chromecast goes through `send`, where the progress card has been hidden since ISSUE-251
  (`QUIET_PROGRESS`): nothing showed while the stream was made and the Roku launched it, so a second tap started it
  again.
- **Fix (`cast.send`):** that route makes the banner too, in two steps (getting ready → waiting for the TV, no AirPlay
  list), with the TV's name on the small line ("Step 2 of 2 · TCL 55 inch Roku TV Living Room"; in the title a long
  name was cut off in the rig), "Playing on your TV · <name> · From m:ss" before the phone's video stops, and the
  same start guard (a second tap only logs, Stop stops). A Roku that refuses and hands over to AirPlay keeps one
  banner.
- **Retest:** desktop Kodi rig, landscape 1311x603, with a 30-character TV name: all three states fit. Device: needs
  the owner's iPhone and Roku.
- **Test:** `scripts/test_tv_banner.py` (`RokuToo`).

## ISSUE-348 — Play on TV's problem card drawn stretched over the upright app, title cut off (owner screenshot IMG_0156, log a83e06c7) — fixed in code

- **Seen:** "The movie took too long …" with the icon tile, the close button and "Try again" drawn as tall ovals over the
  show page ("Starting the video… 7 s"): the owner had closed the video (08:32:18) while Play on TV was still starting,
  and its problem card opened afterwards.
- **Cause:** the card (`IOSAirPlayFlow.xml`) and ISSUE-345's banner (`IOSTVBanner.xml`) are landscape (1080i) windows
  with no portrait copy (`portrait.VIDEO_ONLY`); opened with no video on screen, Kodi draws them on the upright screen,
  stretched.
- **Fix (`cast.py`, `airplay_flow.sheet_spec`):** with no full-screen video (`video_on_screen`), the problem is asked in
  the app's portrait choice sheet: the title, the first sentence under it, one row per action (Try again, Pause uploads
  and try again, Open Settings), the rest of the advice and the checklist as its footnote, and "Not now" (no video
  to keep watching). The banner opens only over the video (waiting up to 3 s for Library's Play on TV to bring it up)
  and closes itself when the video goes.
- **Also (`choice_sheet.py`):** a row title wraps from 24 characters beside a tile (was 30): "Pause uploads and try
  again" (27) was cut at 24 in the rig.
- **Retest:** desktop Kodi rig (portrait 603x1167): the slow-source, unreachable and busy-internet sheets; every word
  shows, nothing cut off. Device: needs the owner's iPhone.
- **Test:** `scripts/test_tv_banner.py` (`NoVideoOnScreen`).

## ISSUE-347 — Subtitles were checked by timing and names only, never against what is said (owner: "match subtitle check needs to be added") — built in code (needs an AirPlay framework build)

- **Seen:** a downloaded subtitle could be for another release or for the original script of a dub, or seconds out of
  time, and nothing could tell: `subtitle_match` only had cue times, names and languages.
- **Fix:** the phone listens to two 45-second stretches of the playing video (about 30 % and 60 % in) and compares
  the words with each candidate subtitle before it is turned on (Subtitles › Download and apply, and ISSUE-342's
  dub captions):
  - `kr_speech.c`: the chosen audio track (Kodi's audio stream number) as 16 kHz mono, at most 48 MB read per stretch;
  - `kr_speech.m` (`kodi_speech_words`, `kodi_speech_authorize`, `kodi_speech_state`): Apple's speech recognition,
    **on the phone only** (`requiresOnDeviceRecognition`; a language the phone cannot recognise by itself is not
    sent anywhere and the check is skipped); words with their times;
  - `speech_check.py`: the share of heard words found in a cue at the best shift. Almost none of plenty of words
    (≤12 %): "Words do not match the speech", the next result is tried. A clear shift of 0.4 s or more: every cue in
    the file is moved by it before it is turned on. Agreement: +10 to the match score. Too few words, or sound in
    another language than the subtitles: no claim.
  - It listens only when a download is checked (not at every playback start: another reader on a debrid link can make
    the host refuse ranges, ISSUE-344), once per video (`KodiIOS.SpeechHeard`). The first time, iOS asks for
    permission (`NSSpeechRecognitionUsageDescription` in the IPA's Info.plist).
- **Build:** `build-airplay.sh` compiles `kr_speech.m`, links `-framework Speech`, exports the three `kodi_speech_*`
  functions and checks them with `nm`; staged as AirPlay r62 with the owner's OK (2026-11-15). Before r62 is in the
  app, `listen()` finds no `kodi_speech_words` and the check is skipped (logged).
- **Follow-up (airplay-ios run 43743217717, nothing published):** the first r62 build failed to link
  (`_kr_speech_pcm` undefined): `kr_speech.m` was compiled to `kr_speech.o`, over `kr_speech.c`'s object. It is now
  `kr_speech_objc.o`; `test_airplay_exports.py` checks that no two sources make the same object.
- **Retest:** CI host tests (`test_speech_sound`). Device: needs the framework build; the owner's iPhone log should
  show `speech check: ok at … s: N words` and `applied … (speech fits|shift …)`.
- **Test:** `scripts/test_speech_check.py`; `tests/test_remux.c` (`test_speech_sound`: a tone is heard after the
  5.1 downmix, from the asked time, past the end, missing track, byte budget, over HTTP);
  `scripts/test_customized_ipa.py` (the purpose string).

## ISSUE-346 — A prepared movie's first cast still scanned every storage fragment for keyframes (owner: "do the keyframe during prep") — fixed in code (needs an AirPlay framework build)

- **Seen:** ISSUE-335 saved the keyframe scan only after a cast had made it, so each prepared movie's first cast still
  read every fragment header before the TV got its playlist (`segmented: 171 keyframes inside 29 storage fragments …
  (metadata 5587 ms)`, owner log 65cca4ce).
- **Cause:** nothing knew the keyframes until a cast read the finished file.
- **Fix:** the preparation reads each fragment header as it goes out (`kr_mp4_moof_keys`, the same parser the cast
  uses) and, after the index (mfra) is written, saves the list under the key a cast computes (mfra bytes, file size,
  picture track; `kr_mp4_cache_*`, moved from `kr_remux.c` to `kr_mp4.c`). The saved list is in the track's own ticks
  (`KRKF2`) and the cast turns it into seconds as before, so a saved and a fresh scan give the same segments. A
  preparation that carries on after Kodi was closed gets the earlier keyframes from its mark (`kfirst`, `kcount`,
  `kf` lines, kept across marks by `drive_prepare.parse_mark` like the `tfra` lines); a mark without them (an older
  one) or with some missing still resumes, and then nothing is saved and the first cast scans. The cast logs
  `from this phone's saved scan (made while preparing)`. Saved scans from before (`KRKF1`) are read again once.
- **Retest:** CI host tests (`airplay-remux`). Device: needs a framework build (new rNN tag) and the owner's iPhone:
  the first cast of a movie prepared after the update should log "made while preparing".
- **Test:** `tests/test_remux.c` (`prepared_scan_matches`: a straight and a resumed preparation save exactly the
  keyframes a fresh scan finds; a record missing keyframe lines saves none); `scripts/test_prepared_keyframes.py`;
  `scripts/test_resume.py` (marks keep the `kf` lines).

## ISSUE-345 — Play on TV showed nothing while the stream was made ready, so it was tapped again and again (owner log a83e06c7, build 513; mockup C chosen) — fixed in code

- **Seen (08:31):** after Play on TV the phone showed no progress for about 25 s while the source was inspected and
  converted; Play on TV was tapped 13 more times ("second press ignored"). Before ISSUE-251 removed the full progress
  card, a second tap stopped the start (ISSUE-255).
- **Cause:** with the card gone (`QUIET_PROGRESS`), the only sign was a notification, sent late, after
  `remote_media.acquire`, and a second tap during the start stopped it.
- **Fix:** a slim banner at the top of the video (owner's choice, mockup C in
  `docs/design/play-on-tv-connecting-mockups.html`): `1080i/IOSTVBanner.xml` from `airplay_flow.banner_page()`, shown
  modeless by `cast.Banner` before anything else happens. It names the step (getting ready or converting → choose your
  TV → waiting for the TV), a thin bar and a red Stop capsule (100 px, about 45 pt); when the TV plays it says
  "Playing on your TV · From m:ss" for two seconds and goes. A second tap on Play on TV only logs; only Stop stops.
  Apple's AirPlay list (`FlowUI.ask`) closes the banner. If Kodi says the window file is missing (written after it
  listed the skin), the skin's 1080i folder is listed again and the window opened once more.
- **Also:** `airplay_flow._capsule` takes a height; short capsules use `pill_96.png` (cutting the 128 px pill's border
  pointed its ends).
- **Retest:** desktop Kodi rig, landscape 1311x603: getting ready, converting, choose your TV, waiting for the TV and
  done all fit on one line, nothing cut off. Device: needs the owner's iPhone.
- **Test:** `scripts/test_tv_banner.py`; `scripts/test_play_on_tv_network.py` (a second tap gives no notice and does
  not stop; the banner's Stop stops a start).

## ISSUE-344 — AirPlay of an Umbrella stream: AllDebrid refused ranged reads, the start took 25 s and then failed (owner log a83e06c7, build 513) — fixed in code

- **Seen (08:31:43, a 10-bit H.264 Umbrella episode, converted for the TV):** the stream cache's blocks failed again and
  again with `ConnectionError: Drive answered without the asked byte range` (ISSUE-321's error text) while Kodi and the
  AirPlay converter read the same AllDebrid link; single fetches went through. The source took 24 s to inspect
  (`indexed inspection finished after 23895 ms`), Play on TV was tapped 13 more times meanwhile ("second press
  ignored"), the video on the phone was closed at 08:32:18, and the cast ended with `audio segment 118 … result=-5`
  (source I/O). The same refusal is the likely cause of ISSUE-321's failures just after a stream starts.
- **Cause:** the server answers a ranged request with the whole file (status 200) when too many connections ask at once;
  the cache treated that like any failure (half its 8 places for 30 s) and never retried the block over one connection
  (it was listed as an integrity error).
- **Fix (`remote_media.py`):** that answer leaves 2 request places for 60 s (`REFUSED_PLACES`, `REFUSED_FOR`; a later
  looser calm never loosens it), and the block is fetched again over one connection (the answer is still checked; it is
  no longer in `INTEGRITY`).
- **Also:** the Play on TV banner (mockup C, ISSUE-345) shows progress at once, so a slow start is not tapped again.
- **Open:** "sometimes only audio": the 08:21 cast to the Apple TV sent the picture as HEVC 10-bit unchanged and the TV
  fetched video segments, so the existing sound-only restart did not apply; which cast was audio-only is asked of the owner.
- **Test:** test_stream_reads `test_a_refused_range_leaves_two_places_for_a_minute`, the INTEGRITY check.

## ISSUE-343 — AirPlay subtitles on the Apple TV doubled and badly out of sync (owner log 1f143748, build 513) — fixed in code (needs an AirPlay framework build)

- **Seen:** a prepared HEVC episode cast to the Apple TV (`segmented: … 148 streaming segments`, picture copied,
  `SUBTITLES="subs"`, `player: subtitles on: Unknown`): the owner saw each line twice and the timing far off. On the Apple TV
  the subtitles come only from the WebVTT rendition (the burn-in is for third-party receivers' converted picture).
- **Causes (gm_stream.c):**
  - Every WebVTT segment said `X-TIMESTAMP-MAP=MPEGTS:900000,LOCAL:00:00:00.000`, the value Apple's segmenter writes for
    media that starts at 10 s. Our video and audio segments keep the source's own absolute times (`gm_ts`, the test
    table's "absolute tfdt"), and the cue times are those same times, so every subtitle was shown 10 s late (also the
    "subtitles delayed" of ISSUE-335).
  - Anime subtitle files draw one line several times on stacked layers (outline, fill, sign copies). Kodi's renderer
    stacks them into one line; each became its own WebVTT cue and the TV showed the line twice.
- **Fix:** one header for every cue file and the empty answer (`GM_VTT_HEADER`: `MPEGTS:0` ↔ `LOCAL 0`); in a segment, a
  cue with the same text as one already written that overlaps it in time is skipped.
- **Retest:** the AirPlay host tests (CI `airplay-remux`); the phone check needs the next AirPlay framework (rNN) and IPA.
- **Test:** test_remux.c (every subtitle fixture: the media-time map and the line exactly once; new fixture
  h264_aac_layers.mkv with a line on two layers); test_airplay_subtitle_sync (wiring).
- **Follow-up (CI run 43736061457, 2 of 3461 host checks failed):** the new fixture row moved the table, so the HTTP
  check of `h264_ac3_dts_srt.mkv` used TrueHD's expectations (`&fx[4]`); it now uses its own row (`&fx[5]`).

## ISSUE-342 — Dubbed video with no caption made from the dub: none was downloaded at playback start (owner, after ISSUE-339) — fixed in code

- **Seen:** ISSUE-339 ranks CC / SDH / dub tracks first, but when the file had only a plain English track (the translation
  of the original script) nothing better was fetched by itself; the owner had to open Subtitles › Download and apply.
- **Fix (`dub_captions.py`, started from `subtitle_match.run`):** once the playback-start check has run for a video, when
  it is dubbed (`subtitle_match.dubbed`), subtitles are on, no track is marked CC / SDH / dub (`dub_marked`) and a SubDL or
  OpenSubtitles key is saved, a background thread searches with the dub preference (`subtitle_sources.find(dubbed=True)`),
  keeps only results marked CC / SDH / dub, downloads up to three with the usual timing check (`choose_download`), and turns
  the best on with `Player.setSubtitles`, only if the same video is still playing. Once per video; logged as
  "Kodi iOS dub captions: …". Without a key, or with no marked result, nothing changes.
- **Retest:** host tests; the phone check is a dubbed anime episode whose file has only plain English subtitles.
- **Test:** test_subtitle_match `DubCaptions`.

## ISSUE-341 — Next Episode after a season's last episode asked for an episode that does not exist (owner) — fixed in code

- **Cause:** `next_episode.plan` always asked TMDb Helper for episode + 1 of the same season.
- **Fix:** `show_seasons` reads the show's seasons from TMDb (TMDb Helper's key, 4 s) and `aired_seasons` counts the
  episodes aired in each (specials left out; the airing season up to its last aired episode; later seasons 0). After a
  season's last aired episode `next_of` gives the next season's episode 1; after the last aired episode of the show,
  "That was the last episode out so far." Without TMDb it is episode + 1, as before. The notice and log name the episode.
- **Test:** test_next_episode `AcrossSeasons`.

## ISSUE-340 — Umbrella: a 5 s cache wait that could not finish before opening directly (owner log 218a6000, build 502) — fixed in code

- **Seen:** "route=direct wait_ms=5017 ready=False blocks=0/3 … bytes=3145728": the opening blocks (3 × 4 MB) were
  arriving at ~0.6 MB/s, the cache waited its whole 5 s budget, then Kodi opened the link directly; 15.8 s in all.
- **Fix (remote_media.hopeless):** after 1.5 s the wait stops when, at the speed so far, the opening blocks cannot be
  complete within the budget, or nothing has arrived; fast sources keep the cache route.
- **Test:** test_umbrella_early_exit. Needs the phone: Umbrella opening times in the log.

## ISSUE-339 — Dubbed episodes: the file's English subtitles translate the original script (owner, Naruto Shippuden 1x01) — fixed in code

- **Seen:** English audio, the file's one "English" track on: "near but not exactly what they say".
- **Cause:** for dual-audio anime the English track is usually the translation of the Japanese dialogue, not the dub's
  words; downloads put hearing-impaired (CC/SDH) versions after plain ones.
- **Fix:** `subtitle_match.dubbed` (more than one audio language, the one playing is the subtitle language): tracks and
  downloads marked CC / SDH / dub / hearing impaired come first, an unmarked one is ranked down (playback-start choice,
  the Subtitles menu and Download and apply). Not yet: a dub caption is not downloaded on its own at playback start.
- **Test:** test_subtitle_match `Dubbed`.

## ISSUE-338 — Favourites search "nearly kicks me out"; the "Most likely" badge never showed (owner log a42d17d7, build 502) — fixed in code; rig-checked

- **Seen:** on the poster picker (IOSFavPick) Kodi logged "Trying to add unsupported control type 7" four times and
  "Control 9600/9601 … asked to focus, but it can't"; tapping the search field closed the picker, opened the iPhone
  keyboard over a blank landscape-sized screen ("Click … in (1280 x 720 layout): control 0 (not handled)"), and a tap
  outside it cancelled; the picker was then built again.
- **Cause:** (1) the search closed the picker for the keyboard and rebuilt it afterwards; (2) type 7 is Kodi's button:
  list cells take no buttons (GUIListGroup), so the auto-width "Most likely" pill added in ISSUE-325 was dropped on the
  phone (the desktop rig render had looked right).
- **Fix:** the keyboard opens over the picker and the results refill it in place (`Pick.refresh`); the badge is a fixed
  240-unit pill image with a centred label.
- **Test:** test_favourites_manager `Picker` (no button/edit/toggle inside any cell; the badge label is at least the pill
  wide; the search refreshes in place). **Rig:** K7 "one peice": "Most likely" shows in full on the first poster.

## ISSUE-337 — AirPlay of a prepared episode: the TV got the raw MP4, then "Cannot Complete Action" (owner log d8524f8d, build 502) — fixed in code (AirPlay r60 staged); needs phone retest

- **Seen:** Kodi opened the prepared HEVC 10-bit episode "by its fragment index", but Play on TV logged "prepared: no
  usable fragment index; Apple's player gets the MP4 itself": the TV read the 168 MB file in jumps for 12 s, then "the
  player failed while the TV had the sound only"; the H.264 restart made its first segment in 2.9 s, yet 1.3 s later
  "could not open the stream: … -11819 Cannot Complete Action". The owner's retry took the raw MP4 path again and failed
  the same way.
- **Cause:** (1) the AirPlay index reader rejected the whole index when one entry did not run forward (preparations that
  resumed write it from both runs; Kodi's reader tolerates that), and with no index the TV was given the MP4 itself;
  (2) the first failure left Apple's player itself failed (AVPlayerStatusFailed), which cannot be used again, and the
  restart put the converted stream into that same player.
- **Fix:** (1) entries are sorted by offset and only those that do not run forward are dropped; why an index is
  unusable is logged; a fragmented prepared file without a usable index goes as six-second segments (picture copied),
  never as the MP4 itself (a plain MP4 with its moov in front still plays as it is: CI run 43729474040 caught the first
  version sending those to segments too). (2) A restart replaces a failed player with a new one of the same settings (every watcher follows it).
- **Test:** C host test `test_prepared_index_repairs` (a copy with two index entries swapped, and one without an index:
  both served in segments covering the whole film, each logs why); test_airplay_source_stall (wiring). The player
  replacement runs only on the phone.

## ISSUE-336 — After a source stall the TV paused itself and never resumed (owner log 53a92f39, build 502) — fixed in code (AirPlay r60 staged); needs phone retest

- **Seen:** casting a Drive copy (06:26): video segment 1 took 32.6 s (one quiet Drive read, ISSUE-335); the TV logged
  "-12889 No response for media file in 10.416s (seg1.m4s)" and "-15628", then sat at 7.4 s with rate 0.0 for 7 minutes
  ("120s: at 7.4 s, rate 0.0 … segments served video 26") although every later segment had been made. The owner gave up
  and pressed Play on TV again (06:34; a second press 10 s later was ignored while it started). The same session's audio
  segment 1 also took 32 s with 1.3 s of its own I/O: it waited on a cache block the stuck video read was loading.
- **Cause:** the player watcher restarts for receivers that refuse the picture and reports a failed item, but a TV that
  paused itself after a stall (item not failed) was left alone.
- **Fix (build-airplay.sh, the native player watcher):** when the TV's position has not moved for 6 s, an error-log entry
  came within 15 s of it stopping, and no video segment is still owed, the player is told to play again; if it still
  does not move, the stream is reloaded at that position (at most three recoveries). A pause long after any error is
  left alone. The quiet read itself is cut after 4 s (ISSUE-335), which also frees the waiting audio.
- **Test:** test_airplay_source_stall (wiring). The watcher runs only in the iOS framework (macOS build): phone retest.

## ISSUE-335 — AirPlay froze 30 s and read Drive too slowly (owner logs 87d9a389, 65cca4ce, build 502) — fixed in code (AirPlay r59 staged); needs phone retest

- **Seen:** casting a Drive copy took 10.6 s to the first picture (0.6 open, 1.2 index, **5.6 keyframe scan**, 2.8 first
  segment), then the TV sat at 1.5 s for ~30 s: video segment 1 took **31.7 s** of source I/O while every other segment
  took 1-3 s, and the TV logged "-12889 No response for media file in 10.416s (seg1.m4s)". The Naruto cast (06:24) read
  6-s segments in 6.5-12.5 s (~0.5 MB/s over one connection), slower than playback, so the TV kept stalling around 45 s
  while subtitles came and went ("subtitles delayed and not working").
- **Cause:** a read only gave up at its whole 15-30 s budget, so one Drive connection that stopped sending held the
  segment; each cursor read over one connection; the prepared file's keyframe timeline was rebuilt on every cast.
- **Fix (kr_source.c, kr_remux.c):** (1) a no-progress watchdog: a read that receives nothing for 4 s is cut, its
  connection closed, and the read retried on a fresh one (not for Elementum's local server, which waits for torrent
  pieces); (2) the keyframe scan is saved on the phone (Library/Caches/KodiAirPlay), keyed by size, track and a hash of the
  file's fragment index, so later casts of the file skip it; (3) when a cursor reads in order and measures slower than
  1.5 MB/s, two helper connections fetch the 1 MiB chunks ahead of it and publish each 128 KiB block as it arrives.
- **Host measurements (system FFmpeg, local range server, 6 MB):** quiet connection once 30 s → 4.2 s; 0.4 MB/s per
  connection 15.3 → 8.7 s; 1 MB/s 6.3 → 4.3 s; 1 MB/s with a quiet connection 10.6 → 4.3 s; a fast high-latency source
  unchanged (0.31 s; helpers stay off). Every byte matched in every run.
- **Test:** C host tests `test_quiet_connection` (range_server `/quiet/`: every byte, under 15 s) and `test_long_fragments`
  (second cast uses the saved scan, same segments); test_airplay_source_stall (wiring).
- **Not done:** the scan is saved on the first cast, not yet while a download is prepared.

## ISSUE-334 — Tapping a season hid the season row; it came back only after Back (owner screenshot + log 88be95be, build 502) — fixed in code; rig-checked

- **Seen:** on a show page (Naruto), tapping Season 2 showed its episodes under the show's header with no season row;
  the row returned only after Back. Log: `Click … MyVideoNav.xml … control 50 (handled)`.
- **Cause:** the season row is the page's own view list (id 50). Kodi sends a tap on a view list to the window, which opens
  the season as its own episodes page (Content(episodes), list 52); a skin `<onclick>` cannot stop that (CGUIBaseContainer
  OnClick: only lists with their own `<content>` run their onclick). The episodes page had no season row. Reproduced in
  the desktop Kodi rig (Naruto, Season 2: Content episodes, no row).
- **Fix:** the episodes page of a TMDb Helper show now shows the same season row (list 48, from the show's seasons folder,
  `tvshow.tmdb_id` of its episodes), the shown season white. A tap goes up to the show and into the other season
  (`Action(ParentDir)` then `Container.Update`), so Back still returns to the show; `Container.Update(…,replace)` was
  tried first and cleared the history (Back left the add-on).
- **Rig (desktop Kodi rig):** Naruto Season 2 page shows Season 1-4 chips with Season 2 white; Season 3 chip opens Season 3;
  Back returns to the seasons page. Needs the phone: tapping chips, scrolling the page.
- **Test:** test_portrait `test_episode_page_keeps_the_season_row`.

## ISSUE-333 — Show page: "Misplaced [" errors; Continue badge and bell condition never true (owner log 218a6000, build 502) — fixed in code

- **Seen:** opening a TV show page logged `Misplaced [` and `Error parsing boolean expression
  string.isequal(listitem.season,$info[window(home).property(kodiios.showcontinueseason)]) …` and the same for the bell
  (`… string.isequal(window(home).property(kodiios.bell.tmdb),$info[container(50).listitem.…`).
- **Cause:** Kodi does not resolve `$INFO[...]` inside a condition. Its string conditions compare against another infolabel
  when the second argument is a bare infolabel (GUIInfoManager.cpp, string bools: TranslateSingleString of param 2).
  So the show page's "Continue" episode mark (ISSUE-312) and the anticipated-episodes bell never showed.
- **Fix:** both conditions use bare infolabels; the Continue mark matches the show by `ListItem.Property(tvshow.tmdb_id)`
  instead of a `String.Contains` on the folder path with `$INFO`.
- **Test:** test_portrait `test_no_infolabel_markup_inside_conditions`: no `$INFO[`, `$VAR[` or `$ESCINFO[` in any
  generated `<visible>` or `condition=""`. Needs the phone: the Continue mark on a favourite show's episode, the bell.

## ISSUE-332 — Actions can no longer publish releases: r33 built but "HTTP 403: Resource not accessible by integration" (2026-11-15) — blocked on a repository setting

- **Seen:** kodi-ios-portrait run 43681992197 (workflow_dispatch, r33 for ISSUE-316): the executable built; the publish job's
  `gh release create` failed with HTTP 403, and again on a re-run of that job alone. The pull_request run before it
  failed the same way. r32 was published by the same workflow from a workflow_dispatch run on 2026-11-13 (run 43362838057).
- **Cause (likely):** the workflow asks for `contents: write`; a 403 from the releases API means the token was given
  less, so a repository or organisation setting changed after 2026-11-13 (Settings › Actions › General › Workflow
  permissions, or a ruleset on tags/releases). Not visible from this session.
- **Fix:** owner: allow "Read and write" workflow permissions (or lift the rule), then re-run only the failed publish job
  of run 43681992197: the built executable is kept as the run's artifact (no one-hour rebuild). The AirPlay framework
  build (airplay-ios.yml, ISSUE-326) also publishes a release and waits for the same change.
- **Retest:** release kodi-ios-portrait-r33 exists; then pin it (digests checked by download) and build the IPA.
- **Update (owner, 13:30Z):** workflow permissions were already "Read and write" and there are no rules, so the setting
  was not the cause. The publish steps (Kodi, AirPlay framework, IPA) now fall back to tagging the default branch when
  the branch commit is refused, and kodi-ios-portrait takes `from_run` to publish an earlier run's executable without
  building. Run 43719679425 (from_run 43681992197) published r33 on its first try, tagged on b6f75b9 (the fallback was
  not needed): the refusals were tied to tagging 04ffff0; the exact reason is still unknown. Zip 7ebe1377…fb00 and
  executable 091eb4a4…1435 checked after download (arm64 Mach-O) and pinned. Status: worked around.

## ISSUE-331 — Next Episode lagged and asked again; it should pick the next episode by itself (owner, build 486) — fixed in code; needs phone retest

- **Request:** "review the next episode button as it seemed to lag out … it should only show up for tv shows and it should
  simply select the next episode if its downloaded through elementum then it should find and recognize that, if its
  through umbrella it should auto select best source based off the first quality i originally picked".
- **Cause:** the button sent TMDb Helper a link without the show's TMDb id whenever the playing item had no
  `tvshow.tmdb` id (a search by name, slower, and it skipped the fast path that plays a downloaded copy at once), and
  without any sign that it came from Next Episode, so the watch menu asked "How would you like to watch?" again and the
  version page asked for a quality again. A second tap while it was starting started it twice.
- **Fix:** `next_episode.py` takes the show's TMDb id from Continue Watching's entry for the playing episode and adds
  `ios_next=<that episode's key>`; a second tap within 10 s is ignored and a short "S1, E3" notice shows at once; a
  movie never gets it (the button also hides when `VideoPlayer.Content(movies)`). With the TMDb id, a downloaded copy
  (Elementum on the phone or Drive) plays before TMDb Helper loads (fast_copy, unchanged). Otherwise the watch menu
  (`ios_watch_dialog.following`) uses the player the previous episode used, without asking, and passes its quality and
  size; the version page (`deck_picker.next_wanted`) takes the version closest to them (`auto_choose`, the Build Season
  ranking) without showing, and remembers it so the episode after follows the same way. With no saved player it asks
  as before.
- **Not covered:** the last episode of a season does not move on to the next season's first episode.
- **Test:** test_next_episode (FromContinueWatching), test_watch_dialog (next episode reuses the player and quality;
  without a saved player it asks), test_deck_picker (next episode picks the closest quality without the page).
- **Retest:** phone: Next Episode on an Umbrella episode (no menus, same quality), on a downloaded episode (plays the
  copy), and on a movie (no button).

## ISSUE-330 — Continue Watching showed every episode of a show (owner screenshot, build 486) — fixed in code

- **Seen:** "Phony S1, E2" and "Phony S1, E1" as two cards. Owner: "it needs to go by per show and keep the most recent
  episode i watched".
- **Cause:** `ios_continue.entries` listed every started title; each episode is its own entry.
- **Fix:** one card per show, its most recently played episode, matching the show by TMDb id or by name (Kodi's library
  copies have no TMDb id). When an episode is finished, older unfinished episodes of that show stay off the row
  (`show_done`); a later episode played afterwards shows again. Saved positions are untouched.
- **Test:** test_watch_continue (test_one_card_per_show_with_the_latest_episode).

## ISSUE-329 — Settings › Library: four rows the owner no longer needs (owner screenshot, 2026-11-15) — done in code; rig-checked

- **Request:** "remove check drive for problems and download problems, as all problems will show elsewhere … we can also
  remove scan iphone files with refresh library since there is a refresh in the status".
- **Checked first:** the service already scans Kodi Downloads on the iPhone by itself; Library status and the Movies/TV
  pages have Refresh; Download problems opens from Notifications ("Open Download problems" in its help). Check Drive for
  problems was reachable only from Settings.
- **Fix:** the iPhone Files section, Refresh Library, Check Drive for problems and Download problems left the page;
  Library now holds Movies and TV Shows, and focus starts on Movies. So that Drive problems still "show elsewhere",
  the service now posts one Notifications message ("Problems on Google Drive", tap to review the same list) when it
  lists Drive again and finds problems it has not reported before (`library_delete.notify_drive_problems`). The
  scripts stay (the add-on's own settings and the service use them). Lost: choosing another folder to scan from Settings.
- **Test:** test_settings_page (rows gone, Movies first, navigation), test_settings_search, test_library_files
  (test_drive_problem_notice: one message, not repeated, new again after a fix), test_debrid_drive.
- **Rig:** Settings › Library rendered in the desktop Kodi rig: three groups, nothing cut off. Needs a look on the phone.

## ISSUE-326 — AirPlay of a prepared movie slow to start, first try failed (owner log ebc9c063, build 486) — fixed in code; needs phone retest

- **Seen:** casting a prepared (Drive copy) movie took long to start and the first try failed on the Roku; the log shows
  `prepared.mp4 bytes=0-53040145`, "HLS over the file's 36 fragments (… longest 63.0 s …)", `seg0.vtt` answered 503 after
  8010 ms and Apple's player stopping with -12889 "No response for media file in 6s (seg0.vtt)". The movie resumed at
  about 40 min, yet the player first asked for subtitle segment 0.
- **Cause:** a prepared file stores fragments of about 64 MB (6-60 s by bitrate) for efficient Kodi reads. Served as HLS
  over those fragments, Apple's player must fetch a whole fragment (up to 63 s, 49 MB) before it can show it, and one
  slow fragment hits its 6-s timeout. The subtitle server waited up to 8 s for a cue file, also past that timeout, and
  answered the player's early segment-0 request (before it moved to the resume point) the same slow way.
- **Fix (kr_remux.c):** before choosing the prepared route the fragment index is measured; when a fragment runs longer
  than 10 s the movie goes the six-second keyframe-segment route the Roku already uses (picture and audio copied,
  nothing converted; Roku's codec limits still apply only to Roku). Subtitle waits end after 4 s (a retryable 503 inside
  Apple's 6 s). While resuming, a cue file behind the resume point is answered empty at once; once the player reaches
  the resume point the ordinary path returns, so seeking back still gets real captions.
- **Trade-off:** this deliberately breaks the old rule "an unfinished cue is never a blank 200" for cue files behind the
  resume point only, before the player gets there.
- **Test:** test_airplay_long_fragments (wiring) and the C host test test_long_fragments in test_remux.c (a 30-s-fragment
  prepared movie is segmented with keyframe segments ≤ 8.1 s, picture copied; seg0.vtt after priming at 20 s is empty in
  < 500 ms; real captions after the player reaches the resume point); subtitle wait bounds tightened to < 5.5 s; the
  slow-cue test retries after each 503 like a player (CI run 225: its 10-s stall outlasted two 4-s waits).
- **Retest:** phone: AirPlay a prepared movie to the Apple TV and the Roku, from the start and resumed; first try plays.

## ISSUE-327 — 165 "Connection reset by peer" tracebacks filled the log (owner log ebc9c063, build 486) — fixed in code

- **Seen:** 165 Python tracebacks (`socketserver … http/server.py handle_one_request … ConnectionResetError: [Errno 54]`),
  two or three a second whenever a Drive copy played or went to AirPlay; about 40 lines each, most of the 1.1 MB log.
- **Cause:** the Drive proxy's server (`drive_proxy.Server`, which Kodi and AirPlay read Drive copies from) had no
  `handle_error`, so Python's default printed a full traceback each time a reader hung up (Kodi seeks, AirPlay stops a
  range). The stream cache's server (`drive_stream._Server`) already ignores these (build 169).
- **Fix:** the same `handle_error`: a reset, broken pipe, aborted connection or timeout from a reader is ignored; any other
  error is still reported. Less log I/O while playing, and logs readable again.
- **Test:** test_quiet_hangups (both servers stay quiet on hang-ups and still report other errors).

## ISSUE-325 — Settings › Favourites as the Favourites manager (boards K1-K8, owner-approved) — done in code; rig-checked

- **Request:** the owner-approved boards K1-K8 (docs/design/favourites-manager-mockups.html): a manager page from Settings
  with what needs a look (Needs your answer, Not found, Duplicates), each imported list, and Import / Order / Open
  Favourites; K7/K8 pick a title by its poster.
- **Cause of the draft's failure (rig render):** the WIP drew every page as ONE Kodi list whose `<itemlayout>`s had
  `condition="String.IsEqual(ListItem.Property(kind),…)"`. Kodi picks one layout for the whole list
  (`CGUIListItemLayout::CheckCondition` evaluates with DEFAULT_CONTEXT, no item), so every row came out as the first
  layout (grey section captions) and the cards, counts, chips and buttons never showed.
- **Fix:** IOSFavManage.xml is a column of `SLOTS` (70) slots, filled from window properties (`r.N.kind`, `r.N.label`, …);
  each slot holds every kind's drawing (the WIP's layouts, `to_slot` points them at the slot) and shows the one its row
  is; a slot is tapped through its own button (`ROW_TAP` + N). The segmented control is the column's first group. A page
  clears what the last one set (`slot_properties`). Rig fixes on the way: the stat tiles' number colour, row icons'
  path, round count/action/chip pills, the poster row's text full-width unless a chip or action sits at its right
  ("Best guess: The Eminence in Shadow · TV" was cut), "Most likely" sized to its text. `start=ask|missing|dups|list:<name>`
  opens a page directly. Settings › Favourites opens it.
- **Retest:** desktop Kodi rig: K1 landing (stats, Needs a look with counts, Your lists, Manage), K2 Needs your answer,
  K3 Not found (segments, Search, Skip All), K4 Duplicates, K5 a list (segments, stats, ranked poster rows, Added chips),
  K7 picker (three posters, kind · year · seasons, Most likely). Nothing cut off. Not the phone; posters need TMDb art.
- **Test:** test_favourites_manager (no per-row list layouts; every slot has every kind and its tap; every kind the model
  makes is drawn; slots never keep a previous page's values; Settings opens it).

## ISSUE-328 — One Continue Watching entry without a show title emptied the whole row (rig) — fixed in code

- **Seen:** `KeyError: 'tvshowtitle'` in `ios_continue.directory` (plugin.video.kodi.ios.watch): the whole Continue
  Watching row failed to list because one saved episode had no show title.
- **Fix:** a missing title or show title takes the other; an entry with neither is skipped; the row lists the rest.
- **Test:** test_favourites_manager `ContinueRow`.


## Provider fallback integration failure log — PR #32

Real rig testing exposed required Crew artwork imports despite a guarded main artwork helper; restored the pinned dependency. Worker RunScript UUID arguments broke Otaku numeric plugin handles and broad library paths shadowed stdlib calendar; scoped numeric plugin arguments and dependency module paths fix both. Host and rig regressions caught canceled primary searches starting backups, unusable backup quality being treated as cancellation, cached zero-seeder sources being dropped, and verified anime coordinates being rejected again by the picker. Explicit cancellation markers, reusable source-check callbacks and exact authoritative mapping retain original TMDb queue coordinates. Direct downloads validate request ownership and byte ranges and preserve headers; Stream rejects unresolved magnets instead of initiating a download. Final regression and real rig counts are recorded in reports/provider-fallback-validation.json. Live provider/account availability and phone behavior remain unverified.

## ISSUE-351 — PR #32 shipped a syntax error in the startup service (found after merge)

- **Seen:** after PR #32 merged, `service.py` in the app did not parse: its two provider-fallback lines sat between an
  `if` and its `elif` (line 127). On the phone that would have stopped the setup service from starting at all. PR #32's
  commits skipped CI (`[skip ci]`), so nothing compiled the file; six existing suites (notices, service_scoping,
  undefined_names, pinned_addons, speed_fixes, updates_calibration) failed with `SyntaxError` as soon as they ran.
- **Cause:** the hook install was inserted into the middle of an if/elif chain.
- **Fix:** the install now runs after the chain (Umbrella present, whichever source window it has).
- **Retest:** all suites in the workflow run; the six pass again.
- **Test:** `scripts/test_bundle_syntax.py` parses every shipped Python file and pins the order.

## ISSUE-329 — Upcoming timer could delay closing the page — fixed before first commit

- **Seen:** the host `test_speed_fixes.py` regression check rejected the new Upcoming timer's use of
  `Monitor.waitForAbort(1)` while a separate stop event controlled the page lifetime.
- **Cause:** Kodi waits for a script's background threads at exit; that sleep would ignore Back until its timeout.
- **Fix:** use the existing `page_wait.idle` helper, which wakes when the page closes or Kodi exits.
- **Retest:** the page controller tests and the stop-aware-loop regression checks pass. The desktop rendering was
  checked before this wait-only correction; it is not iPhone evidence.
- **Test:** `scripts/test_speed_fixes.py` (`PageLoops`) and `scripts/test_sports_upcoming.py` (controller lifecycle).

## ISSUE-330 — Upcoming could not reach the approved scrolled position — fixed in the desktop rig

- **Seen:** board 11 needs the later days higher in the viewport than the original list's scroll range allowed.
- **Cause:** its 260-unit trailing clearance allowed only about 208 pt of scrolling with the sample's wrapped
  league chips; the approved board scrolls 330 pt before allowing for the extra chip row.
- **Fix:** reserve 720 units after the final day, so the header can scroll away and the later games can occupy
  the approved positions without the tab bar covering their text.
- **Retest:** desktop Kodi 21.3: wheel scrolling and Last Page show Tomorrow and Sat, Nov 21 with complete titles,
  times, counts and source details above the fallback tab bar. Device gestures remain unverified.
- **Test:** `scripts/test_sports_upcoming.py` checks the shared six-game, three-day projection and generated XML;
  the actual scroll range was checked visually in the desktop rig.

## ISSUE-331 — Returning from a game reset the Upcoming filter — fixed in the desktop rig

- **Seen:** choosing NBA, opening its game, then pressing Back restored All rather than the chosen league.
- **Cause:** Kodi calls the parent window's `onInit` again when the child closes; it reset the filter and created
  another timer. The unconditional default focus also discarded the row's navigation position.
- **Fix:** initialize each Sports window once and let Kodi restore its existing focus on return.
- **Retest:** desktop Kodi 21.3: NBA → game → Back preserves the NBA chip, one-game count and selected row. The
  controller regression simulates the repeated `onInit` and checks the existing filter and stop event survive.
- **Test:** `scripts/test_sports_upcoming.py` and `scripts/test_sports_game.py` cover re-entry without new workers.

## ISSUE-332 — A long source description lost its final line — fixed in the desktop rig

- **Seen:** the long-source fixture ended after “Loop Guide, Sports”, clipping “Hub” in the Also on line.
- **Cause:** the estimate allowed too many characters per line beside the Also good badge. The language and
  alternative-provider text needed six actual Kodi lines, while the model reserved five.
- **Fix:** use more conservative wrapping estimates for each badge width, grow the row to fit and provide forms
  for up to nine detail lines. The source title and details remain complete.
- **Retest:** desktop Kodi 21.3: International Sports Network, French Canadian commentary and all three alternative
  provider names now fit, including the final Hub line. Standard board 12's row sizes remain the same.
- **Test:** `scripts/test_sports_game.py` keeps the exact long fixture and checks its required line allocation.

## ISSUE-333 — Two-digit start hours were shortened in the game card — fixed in the desktop rig

- **Seen:** opening the later Manchester City game drew “12:30 …” instead of its complete start time.
- **Cause:** the central clock's 360-unit label was narrower than the existing headline font's 12:30 PM text.
- **Fix:** widen the centered label to 430 units, within the gap between the crest/code columns. Keep the same font
  and center point, so board 12's 7:30 PM appearance is unchanged.
- **Retest:** desktop Kodi 21.3 shows 12:30 PM and the day in full without touching either crest. An offline font
  check of every 12-hour clock string found a maximum width of 386 units.
- **Test:** `scripts/test_sports_game.py` checks the later-day value and enough clock space between the crests.

## ISSUE-334 — Game refresh test assumed mutable provider snapshots — fixed for the updated contract

- **Seen:** GitHub's PR check failed the empty-after-refresh test although all local scripts passed.
- **Cause:** the base branch advanced: Sample now returns independent copies. The fixture edited a returned game
  and expected that edit to change the provider's next response, which the updated contract deliberately prevents.
- **Fix:** have the test provider explicitly return the next empty-source snapshot. The application still reads
  only the public provider methods and needs no change.
- **Retest:** all 137 listed scripts, including the thirteen game-page cases, pass against the actual PR tree
  combined with the updated base. The feature checkout's game-page tests also pass; GitHub is checked after push.
- **Test:** `scripts/test_sports_game.py`, `test_failed_refresh_keeps_seed_and_success_can_remove_sources`.

## ISSUE-335 — Upcoming's timer could replace a failure with loading placeholders — fixed in the desktop rig

- **Seen:** a cold provider failure was drawn once, but the next normal redraw no longer knew the request failed.
- **Cause:** `draw(error=False)` used a temporary argument rather than preserving the last fetch result. With no
  cached data, the periodic redraw selected loading again until another request finished.
- **Fix:** retain the failure flag across redraws; clear it only when a fetch succeeds. Keep cached games visible
  when refresh fails, and distinguish a successful empty result from an unavailable provider.
- **Retest:** desktop Kodi 21.3: advancing the fixture clock by 31 seconds keeps board 15 visible. Repeated failure
  stays on the error screen; Try again with a recovered test provider restores the game list.
- **Test:** `scripts/test_sports_upcoming_states.py` covers persistent error, retries, successful emptiness, cached
  results, stale rows/chips and closing during a fetch.

## ISSUE-336 — State icon backgrounds and error text needed renderer corrections — fixed before commit

- **Seen:** the first desktop render showed a thin seam across a translucent icon circle; automatic body wrapping
  also put Check on the wrong line and used tighter line spacing than approved board 15.
- **Cause:** nine-slice scaling was unnecessary for a circular texture, and the generic textbox's wrap/line spacing
  differed from the approved two-line state message.
- **Fix:** scale the circular mask uniformly and expose the approved description lines separately, preserving the
  complete plain-text message. Draw them at the board's 21 pt spacing and keep both primary controls' focus visible.
- **Retest:** desktop Kodi 21.3: both icon circles are seamless; boards 14–15 match the approved copy, line breaks and
  action positions. Retry and See Leagues show focus feedback without moving the layout.
- **Test:** state projection checks preserve the complete message across the rendered lines; the seam, typography
  and button feedback were checked visually in Kodi, not inferred from a unit test.

## ISSUE-337 — Leagues badges initially referenced unavailable resources — fixed before commit

- **Seen:** implementation review caught references to a 118-unit capsule asset and bold-caption font that the
  existing generator did not supply.
- **Cause:** the approved 44 pt badge's display size was mistaken for an existing texture/font resource name.
- **Fix:** scale the existing circular pill_124 texture and use the existing caption font with bold text markup.
- **Retest:** desktop Kodi shows full league codes and badges in boards 16–17, including the scrolled sections.
- **Test:** `scripts/test_sports_leagues.py` covers generated controls and registration; actual font/texture rendering
  was checked in Kodi. No new asset or font variant was added.

## ISSUE-352 — Sports discovery was skipped for twelve hours after an earlier empty run (owner log 0d2dbf1a, build 544)

- **Seen:** build 544 opened Sports but logged nothing from the discovery walk, although The Loop family and The Crew were installed.
- **Cause:** build 538's walk (the add-ons were not installed then) had saved an empty answer, and the walk is only repeated every 12 hours.
- **Fix:** an earlier answer that listed no add-on at all is retried after ten minutes (`sports_loop.wait_for`).
- **Retest:** host tests only; the phone needs the next build.
- **Test:** `test_sports_loop` (`test_an_empty_earlier_discovery_is_retried_soon_but_a_good_one_keeps_for_twelve_hours`).

## ISSUE-353 — The Play on TV banner's bar sat at one number for the whole first step (owner, build 544: "show progress when it's preparing TV")

- **Seen:** casting a 4K movie took 25-28 s to start and the banner's bar stayed at 22 % throughout; short starts (5-10 s) looked the same.
- **Cause:** one fixed percent per step (`BAR_PCT`), and "usually a few seconds" as the only words.
- **Fix:** the bar climbs the whole time inside each step toward the next step's start (estimates: the native side reports no
  percentage), is lifted by the native phase (opening, inspecting, ready), never goes back, and stops short of full until the TV plays.
  The first step's line names the phase ("Reading the video", "Getting the first seconds ready"). `cast.airplay_outcome` calls a
  `tick` twice a second; a failing tick never stops the start.
- **What the log showed about the slow starts (not changed here):** 4K 10-bit HEVC casts took 25-28 s: the keyframe scan of a prepared file
  that has no saved scan (12-14 s, `segmented: ... (metadata 13926 ms)`) plus the first picture and sound segments read cold from Drive (7-9 s).
  A phone-local show (Naruto) took 5.5 s; a 1080p Umbrella show 10.5 s. Quality is not the cause; file size and where it is read from are.
  The scan is saved after the first cast of each movie, so a second cast of the same movie skips it.
- **Test:** `test_tv_banner` (bar bands, phase floor and words, the controller tick).

## ISSUE-354 — The first cast of a 4K movie from Drive spent 12-14 s scanning for keyframes (owner log 0d2dbf1a, build 544)

- **Seen:** `segmented: 1697 keyframes inside 109 storage fragments give 772 streaming segments (metadata 13926 ms)` on a first cast; 12.4 s on a second
  4K movie; 4 s on 1080p. The scan is saved afterwards (ISSUE-335/346), so later casts skip it, but every library title pays once.
- **Cause:** the scan read each fragment's index with two requests (the 8-byte box header, then the moof) on four connections: about 0.5 s per
  fragment per connection against Drive.
- **Fix (r63, `kr_mp4.c`):** one request of 40 KB per fragment (a fragment's index is about 30 KB; a larger one reads the rest) and eight
  connections. Same parser, same saved result, so the segments are unchanged. Expected: roughly a quarter of the time (about 3-4 s for the 4K movie); to be measured on the phone.
- **Not changed:** the 7-9 s the first picture and sound segments take to arrive from Drive (cold connections; the source reader already adds helper
  connections on a slow link). The next log will show the scan time and, with it, what remains.
- **Test:** the converter host tests (airplay-remux) cover the scan; a phone log gives the time.

## ISSUE-355 — Drive copies would not play after the app had been in the background ("Umbrella streams not working", owner log 46025e07, build 545)

- **Seen:** Phony S01E04 (an Umbrella show kept as a Drive copy) failed to open with `CCurlFile::Open - http://127.0.0.1:62654/drive/... Could not connect to
  server(7)`, over and over. Before it, `JSONRPC Server: Accept of new connection failed: 9` and Elementum's `jsonrpc service stopped ([Errno 9] Bad file
  descriptor), starting it again` (it restarts itself).
- **Cause:** iOS closed the app's listening sockets while it sat suspended (about 25 minutes). The Drive proxy (`drive_proxy`, the loopback server every
  Library play of a Drive copy goes through) was started once and never checked, so it stayed dead until the app was quit and opened again.
- **Fix:** `drive_proxy.supervise` asks the proxy for a page every 4 seconds; one that does not answer is stopped and started again (on the same port when it
  can be, else another; the Home window property follows), and the log says so.
- **Retest:** host tests; on the phone: leave the app in the background for half an hour, then play a Library episode.
- **Test:** `test_drive_proxy_alive` (health probe on a real server, restart on the same port, fallback port, clean stop when Kodi closes).

## ISSUE-356 — Sports discovery never finished: its walk ran on a thread of the page's own script (owner logs 3633b638, 70f32729, builds 544-545)

- **Seen:** with The Loop family and The Crew installed, three logs had no "Kodi iOS Sports discovery" line at all, even after the per-build fix.
- **Cause:** the walk (a minute or more: every folder is a call to an add-on that goes to the internet) ran on a daemon thread of the Sports
  page's RunScript process. Kodi ends that process when the page closes, so the walk died before it logged or saved anything.
- **Fix:** the page only sets `KodiIOS.SportsDiscover`; the service (alive as long as the app) walks 45 s after start and whenever asked
  (`sports_loop.serve`), and logs "started", "walking <add-on>" and one line per folder with its time as each answers, so a log exported at
  any moment shows how far it got.
- **Also (ISSUE-355 follow-up):** a Library play checks the Drive proxy first; a dead one is restarted at once and its new port read, else
  the Drive add-on's stream plays the copy (`drive_proxy.live_port`, `supervise(nudge=...)`).
- **Test:** `test_sports_loop` (per-folder log, the page's ask, the service loop), `test_drive_proxy_alive`.

## ISSUE-357 — Walking The Crew's menu ended the app, and the walk came back 45 s after every start (owner log f8d75848, build 548)

- **Seen:** the discovery walk ran in the service as designed (ISSUE-356) and showed what the add-ons do: The Loop failed (`Invalid params`, after a
  confirm box), Loop TV's own server answered 404 when it registered, Loop Guide listed five buttons (Open EPG, Open Sports Guide, Refresh Guide, Settings, Exit).
  Then, four seconds after "walking plugin.video.thecrew", Kodi started again from the top: the app ended during The Crew's menu.
- **Cause:** not known (no crash report). Because the walk never finished, no result was saved and it was due again 45 s after each start: a repeating crash.
- **Fix (build 549):** The Crew is not walked (`HELD_BACK`); each add-on's walk is wrapped in a marker file (`Guard`), and an add-on whose walk ended the app is never
  walked again for that build; the service walks only when the Sports page asks, not at every start.
- **Test:** `test_sports_loop` (held-back Crew, the guard, ask-only walk).
- **Still open:** the sports data itself. None of the three Loop add-ons gives games on this phone (The Loop errors, Loop TV's server is gone, Loop Guide has only buttons).

## ISSUE-358 — No sports walk until a source is chosen: The Loop blocked for 22 minutes, and none of the add-ons gives games (owner log c22859a4, build 548)

- **Seen:** (build 548, 18:56-19:19) Library shows and AirPlay worked: the Drive proxy served the episode, AirPlay r63 started in 11.5 s, and the saved keyframe scan was
  used ("148 keyframes from this phone's saved scan ... 1 ms"). The sports walk: The Loop took 1352.8 s (22 minutes) to fail with `Invalid params`, Loop TV 1.7 s (its server
  answers 404), Loop Guide listed five buttons; then The Crew's walk began and the log stops.
- **Cause:** The Loop's plugin waits (probably on a dialog nobody sees); a walk can also raise dialogs over the screen. None of the add-ons returned games.
- **Fix (build 550):** `sports_loop.WALK = False`: the service never walks and never calls an add-on until the sports source is chosen. The Sports pages say "Can't load" as before.
- **Test:** `test_sports_loop` (`test_no_walk_runs_while_the_sources_are_not_chosen`).

## ISSUE-359 — Subtitle lines stacked on the TV instead of replacing the old one (owner photo, build 549)

- **Seen:** four caption lines at once on the TV ("[group] Hi, Sharla!", "I'm back doing PI work", "[Sharla]", "Yeah, it's been a stressful time."); the old line did not leave when the new one came.
- **Cause:** each WebVTT cue stayed up until its own end time (a 5 s fallback when a sample has no duration, or a file whose end times overrun), past the start of the next cue. The TV shows
  overlapping cues stacked.
- **Fix (r64, `gm_stream.c`):** each cue now ends where the next one starts (the next cue of the segment, or the first cue after the segment, which is read but not used); cues that begin
  together stay together. Segment by segment the same rule gives the same result.
- **Retest:** the converter host tests (airplay-remux) must still pass; on the TV a new caption replaces the old.

## ISSUE-360 — Sports had no data source (DEC-060)

- **Fix:** ESPN's public scoreboard feed (see DEC-060). First run: `HTTP 400` because the feed rejects a date range; fixed by asking for the plain scoreboard and tomorrow's date; the "Live Now" tile
  no longer splits "1 / more".
- **Retest:** desktop Kodi rig with the live feed (Live Now with crests, scores and clocks; Upcoming; Leagues; the landing): evidence class desktop Kodi rig, not device.
- **Test:** `test_sports_espn` (11), `test_sports_landing`.

## ISSUE-361 — The Play on TV bar reached about 50 % and then the TV played (owner, build 549, with a screenshot)

- **Seen:** the banner's bar (Step 1 of 3 · Opening the video) stopped near half and the TV started at once; the first version of the moving bar (ISSUE-353) was built from three bands per step, with
  step 1 capped at 52 %, and a repeat cast now takes only about 6-11 s.
- **Fix:** one curve for the whole start, tuned to how long this phone's last start took (`KodiIOS.TVStartSeconds`, blended 60/40 with the one before; 14 s until measured), lifted to the native phase's floor
  (reading the video 15, first seconds ready 40, the TV connecting 70), never going back, under 97 % until the TV plays; on playing the bar fills to 100 % for a moment before "Playing on your TV".
- **Not changed:** the native side reports no percentage, so the bar stays an estimate. The 7.5 s cold read of the first segments from Drive is not changed (owner: skip it for now).
- **Test:** `test_tv_banner` (curve, floors, expected time).
- **AirPlay stopping when the phone locks or another app opens (owner):** the 548 log shows a 22-minute cast with the app off the screen playing on ("stays awake for AirPlay", segments served all the way), so
  the framework's silent-audio keep-alive works there. The case that quits is not in any log yet: after it happens, export the log at once.

## ISSUE-357 follow-up — The Loop failed because it was unzipped in place, not installed (owner Steam Deck files + rig, 2026-11-16)

- **Correction:** an earlier message claimed the desktop rig had reproduced the exact "unofficial repository" popup from the owner's phone.
  That rig test used a hand-copied file drop outside any Kodi install process, which is not how the real IPA ships add-ons, so it did not
  actually confirm the phone's cause. The Loop/JetExtractors files from the owner's Steam Deck matched our bundled copies byte for byte,
  ruling out a bad package.
- **Real cause:** the build unzipped The Loop's files straight into the add-ons folder. Kodi then has no record of where the add-on came
  from (no repository origin), and The Loop's own code treats that as untrusted and fails ("Invalid params" in the owner's log).
- **Fix:** only a small pointer add-on, `repository.loop` (The Loop's real repository, pinned with a checksum), is bundled now. The app's
  background service calls Kodi's own `Addons.InstallAddon` once (no confirm box; it is the JSON-RPC method, not the `InstallAddon()`
  builtin) to fetch `plugin.video.the-loop` properly, which brings LoopTV, Loop Guide and JetExtractors with it as declared dependencies —
  proven in the desktop Kodi rig: the live-installed Loop listed real sport links ("Todays Football", "Todays Rugby", schedules) with no
  popup and no crash, where the old unzip-in-place method failed. The discovery walk (`sports_loop.WALK`) is on again.
- **JetExtractors' own protection is untouched.** It still refuses a caller it does not recognize; this fix never calls it directly — The
  Loop calls it the way it is designed to, because The Loop is now a real, properly-installed add-on.
- **The Crew stays held back** (`HELD_BACK`): its own walk ended the app earlier and the cause is still unknown. The per-add-on guard
  (ISSUE-357) still protects every add-on this discovery walks, including The Loop, in case anything regresses.
- **Test:** `test_sports_loop` (`ensure_installed`: installs once, retries bounded, no-op without the repository bundled, never raises),
  `test_provider_addons` (`SportsLock`: only the pointer add-on is bundled, not the Loop files themselves).


## ISSUE-362 — Sports "See upcoming", Upcoming and Leagues did nothing (owner log 6f2ebc1a, 2026-11-16)

- **Seen:** Live Now opened ("no games are live"), but "See upcoming", the Upcoming tile and Leagues did not open; kodi.log: "Activate of window ... refused because there are active modal dialogs".
- **Cause:** the Sports landing and Live pages are `WindowXMLDialog` (modal); Upcoming, Leagues and Game were full `WindowXML` windows, which Kodi will not open over a modal dialog.
- **Fix:** those three pages are `WindowXMLDialog` too (they stack). Verified in the desktop Kodi rig, before and after.
- **Test:** `test_sports_dialogs` (every Sports page class derives from `WindowXMLDialog`).

## ISSUE-363 — Sports had no real games or streams: ESPN gave games but no streams, The Loop had no adapter (owner, 2026-11-16)

- **Seen:** every game said "No sources yet"; the owner wants The Loop family's own source add-on (JetExtractors) as the source of games and streams, not ESPN.
- **Fix:** `sports_jet.py` asks the JetExtractors scrapers (through the add-on's own `get_extractors()`; nothing is worked around), turns each JetItem into merge records, merges them, and plays a source through
  JetProxy (`plugin://plugin.video.jetproxy/play/...?h=`) or Kodi's player. A page waits 18 s, then shows what has answered; slow scrapers finish in the background. ESPN stays in the app (`KODI_IOS_SPORTS=espn`).
- **Unknown until a phone log exists:** JetExtractors may refuse a caller that is not The Loop. The first build logs why (`Kodi iOS Sports: jet: ...`: scraper counts, names, a few titles; never a stream address). If it refuses, the
  fix is on The Loop's side (a prompt for the owner's agent), not a workaround here.
- **Test:** `test_sports_jet` (titles, leagues, state, records, merge of two scrapers, failing and slow scrapers, nothing-answers, JetProxy path).

## ISSUE-364 — Sports said "The sports add-ons didn't answer": our script could not import `requests` (owner build 552 log 916e0a6a)

- **Seen:** every Sports page showed "Can't load sports right now"; the log said `jet: no scrapers (JetExtractors is not installed (ModuleNotFoundError: No module named 'requests'))` although
  JetExtractors 3.3.33 and requests 2.31.0 were both installed.
- **Cause:** Kodi puts a module add-on on the python path only for an add-on that declares it. The Sports script is not JetExtractors, so JetExtractors' own imports (requests, bs4, dateutil...) failed.
  JetExtractors was never asked anything, so this says nothing yet about whether it accepts our caller.
- **Fix:** `sports_jet.add_module_paths` adds the module folder of JetExtractors and of every add-on it requires, recursively, from their addon.xml files; a missing one is skipped.
- **Test:** `test_sports_jet.ModulePaths`.

## ISSUE-365 — Sports: JetExtractors failed with "No valid addon id could be obtained" (owner build 554 log a01ae2c6)

- **Seen:** with the modules importable (ISSUE-364) every page still said "Can't load sports right now"; log: `jet: no scrapers (JetExtractors refused or failed (RuntimeError: No valid addon id could be obtained...))`.
- **Cause:** JetExtractors asks Kodi for "the current add-on" with a bare `xbmcaddon.Addon()`. Our scripts run through `default.py`'s `runpy`, where Kodi cannot tell which add-on that is (the same cause as the Library status failure in the build 159 log, test_library_status.EveryScriptNamesItsAddon),
  so it raises. (A first guess, that only a page's worker thread was the problem, was wrong; a separate script alone does not fix it.)
- **Fix:** Jet's work runs in its own script `sports_jet_run` (a page's thread is not used, and the page only reads the answer from a Home window property: partial answers after 6 s, the rest as they come, 2 min reuse; playing
  a source goes the same way), and while that script runs `sports_jet.named_addon` makes a bare `Addon()` mean this add-on (`service.kodi.ios.bootstrap`). JetExtractors is not changed and its own checks stay; this only says who we are.
  If it still refuses, the next step is a prompt for The Loop's side with the exact error.
- **Test:** `test_sports_jet.Remote` and `NamedAddon`.

## ISSUE-366 — Sports: tapping a stream did nothing (owner, after JetExtractors accepted the add-on)

- **Seen:** games list from JetExtractors (owner's config.py change on their side), but no stream opens.
- **Found so far:** the Live page handed whatever `sports_provider.play` returned to `xbmc.Player().play`; the Jet route returns `True` after starting the play script, so Live would try to play "True". Fixed (skips `True`).
- **Still to check on the phone:** the Game page route (`sports_jet_run play`) and what `expand()`/JetProxy do with a real stream. Needs the kodi.log from just after a tap (look for `jet: play failed` or `sports: playing`).
- **Test:** `test_sports_jet.LivePageDoesNotPlayTrue`.

## Sports build 557: source tap fails and collection work repeats — 2026-11-16

Owner build 557 log confirms an asynchronous Jet play request returned True and Live Now passed it to Player.play; ResolveURL was installed but absent from the script import path; failed extractor resolution could pass a webpage to Kodi. Load ResolveURL's declared dependency graph, accept only actual playback strings at the page boundary, and reject unresolved links. Forced refresh now joins an active collection, with a process-wide file lock preventing simultaneous interpreter scans. Keep existing results during refresh and avoid rewriting unchanged page properties. Provider outages in the log remain upstream failures; these changes cannot guarantee their availability or phone frame rate.

All 14 sports suites pass (179 tests). Seven focused regression cases cover dependency loading, the asynchronous acknowledgement, refresh joining and failed/successful link resolution. Existing mock window failures exposed the need to cache previous properties within each page; corrected and all suites rerun. Owner also approved review/merge of PR #44 and one combined testing IPA. PR #44 merged as 9b276e7 after its 265 Python tests and project check passed. Next: integrate newer sports/subtitle source with main, run native candidate CI, verify/pin its framework, then package and verify the IPA. Actual iPhone playback/scrolling/AirPlay checks remain pending.

## Drive startup follow-up — optional index admission blocks playback (2026-11-16)

Build 554's first decoded picture was queued 4.168 s after Play, while the streams-ready
poll logged 3.2 s. First display scanout was not measured. Index capture synchronously
revalidated Drive metadata and persisted the optional cache before returning player bytes.
The proxy now performs that admission in bounded background work, preserving live identity
checks before reuse. Added blocked-validation/changed-identity/bounded-admission regressions;
25 index + 25 proxy + 9 timing tests and check_project pass. Five-run loopback medians with
200 ms metadata: cold 0.4098 → 0.2021 s, warm 0.00108 / 0.00137 s. This is a fixture,
not iPhone evidence. Full findings and device gaps: DRIVE-STARTUP-AIRPLAY-PROGRESS.md.

## AirPlay audio without completed TV video — source fix (2026-11-16, build 554)

Receiver fetched audio and converted init, retried converted segment 0, and received zero video
bytes before AVPlayer failure at 32.5 s. Phone-only copied video must not count as TV picture.
After MP4 sample-scan failure, the storage-index plan (up to 70.3 s) also drove conversion,
making a first converted segment much too long. The failure card blamed Drive using I/O from
a different copied-video read-ahead; zero converted-cursor I/O does not rule out shared-cache
waits. Exact scan-failure cause and encoder-versus-shared-wait split remain unproven.

Fix: separate six-second converted timeline plus matching audio routes/cache keys; preserve
copy keyframe windows, packet quality and selected subtitles. Diagnose converted failures
only with that lane's measurements; add shared-cache wait metric. Same host fixture fails on
old source (32-s conversion window) and passes fixed (6-s windows, all 768 frames, A/V bounds,
caption drawing, exact copied packet digest, seek/cancel/recovery). 375 related native checks
and 265 Python tests pass. Device success remains pending; no native pin/release/IPA change.

Retained validation failures: main service SyntaxError required PR #42's existing prerequisite;
native string-wiring assertions needed audio-route updates; initial continuity assertion
misinterpreted the first packet edit-list anchor (all later pairs and boundaries now checked);
standard rig setup lacks sudo; first desktop harness used an unsupported JSON-RPC option.
Detailed evidence/remaining checks: DRIVE-STARTUP-AIRPLAY-PROGRESS.md.

## Combined build integration: portrait source digest mismatch — 2026-11-16

 38dad1e is pushed on PR #43. Native candidate run 43907784636 tests and builds that source, including r64 subtitle changes and PR #44's separate six-second converted timeline. No IPA has been built yet. The ordinary import CI caught a portrait patch digest mismatch: PR #44 adds an optional first-frame logging marker, but the approved r33 executable was built without that marker. The testing branch now retains the exact r33 patch and pin together; the marker remains in main for a future Kodi executable build. This does not remove the Drive admission or native AirPlay playback fixes; first-picture timing remains explicitly unmeasured. test_smooth_pages passes after restoring that consistency.

Native infrastructure failure retained: candidate run 43907784636 passed host tests but GitHub canceled its unassigned macos-15 ARM64 compile after 15 minutes: "The job was not acquired by Runner of type hosted even after multiple attempts"; annotations report ARM64 capacity constraints. Retry compilation on the documented macos-15-intel image (Xcode 26 available). A manual reuse_host_run option verifies the earlier host job succeeded and the entire migration/airplay-ios Git tree is identical before allowing the compile; default PR runs still execute the full host suite. This reuses evidence, not an older binary.

## Build 561 artifact validation: signed versus unsigned r33 comparison — 2026-11-16

The private verification helper initially compared the unsigned packaged executable to the signed r33 pin. It now verifies the pinned original archive/binary and compares the exact result of the existing unsign function. One signature command removed; all other bytes match. Release SHA, ZIP CRC, repaired source and exact r65 framework checks pass. Build 561 published; device acceptance remains pending. No app change or extra IPA was needed.

- **Update (owner log b7b8ef70, build 557):** games load (9 scrapers: LiveFeeds 229 games, Embedsport2 160, ...). Every tap chose Embedsport2, whose own stream request to its helper host failed on the phone (`[SSL] unknown error`),
  while other scrapers list the same matches; and quick taps raced on one Home window property (`KeyError: 'play'`, 3 times).
  **Fix:** a game's source now carries the other add-ons' play values as `alts`; `play` tries the source's own add-on and then up to four others until one opens (one log line per failure, no addresses); each tap uses its own
  property. **Not fixed (not ours):** Embedsport2's helper server failing on iOS. **Test:** `test_sports_jet.Fallback`, `test_sports_merge` (unchanged and still passing).

## Build 563: Sports playback candidates and repeated snapshot work — 2026-11-16

A 36-second scraper run contained upstream DNS failures; Leagues and Upcoming called the provider repeatedly while partial data was available. Snapshot reuse avoids repeated waits and briefly caches the same merged result, invalidating when the snapshot changes. The adapter also abandoned sibling streams after one ResolveURL failure and passed the original embed URL after a successful resolution. It now tries nested candidates and the scraper’s own resolver, passes the resolved address, and combines resolver/extractor headers for Kodi or JetProxy; app-owned failure logs omit exception URLs. The full sports suites pass. Desktop Kodi 21.3 with 300 synthetic games rendered both pages, reused one merge across four provider calls, and played a local video after a failed first mocked resolver and again via a mocked scraper-owned fallback. No live-provider or iPhone acceptance claim. Evidence: reports/sports-563-rig-validation.json.

Rig follow-up: a Python optimized-mode assertion initially skipped a synthetic probe; explicit runtime checks and two independent reruns corrected that harness error. Two orphaned desktop Kodi rig processes also competed for port 8089; only those test processes were stopped, the rig was restarted, and the final probe passed. These were rig issues, not diagnosed phone failures.


## Sports provider refusal repeats after refresh — 2026-11-17

- **Seen:** build 566 repeatedly displayed JetExtractors refusal dialogs during Sports refresh; independent listings continued.
- **Cause:** every collection launched JetExtractors again, and the previous in-memory pause only handled one refusal string for the current Kodi session.
- **Fix:** explicit ban or authorization refusal pauses JetExtractors for six hours in a profile file and Home-window property; a changed build or expiry permits another attempt. Paused playback skips JetExtractors and allows alternate sources. This does not lift a ban or restore access.
- **Test:** `test_sports_pause`, `test_sports_independent`, and `test_sports_playback_repair`; phone validation remains pending.

## Independent sports playlist rejected — 2026-11-17

- **Seen:** build 566 phone log and host checks show HTTP 403 on the initial HLS playlist before Kodi requests segments.
- **Cause:** unknown. Player embed exposes a playlist URL; header, cookie, URL-query and access-decision requirements are not established. Host response passed through an intermediary; no conclusion about the upstream decision is justified.
- **Fix:** unresolved; no protection bypass or speculative playback change.
- **Test:** `test_sports_independent` covers header propagation at resolution and safe failure diagnostics, not successful live playback.


## Import test batch: intermittent stream accounting assertion — 2026-11-17

- **Seen:** `test_stream_loop.py` reported 0 rather than 100 served bytes once during the 173-command batch; the same suite passed immediately when rerun alone.
- **Cause:** not established; the failure occurred in the existing asynchronous stream accounting assertion.
- **Fix:** none made for this unrelated intermittent failure.
- **Test:** standalone `python3 -B scripts/test_stream_loop.py` passed; retain this observation for future investigation.

Public reference investigation: a plaintext Kodi extractor describes a source-issued access-grant playlist for one embed format; the currently observed embed did not contain that grant marker. A separate Android WebView project names the embed host. Neither establishes the cause of this phone’s 403 or proves a working stream; no third-party code was copied.


## FawaNews independent source candidate — implementation pending validation

- Seen: owner Deck shows FawaNews local-proxy playback, while phone StreamsCenter returns 403.
- Cause: providers differ; FawaNews has no explicit schedule in the extractor, so existing Sports classification drops unknown-time entries.
- Fix candidate: independent FawaNews parsing matched only to unique live ESPN schedule events; isolated MIT local proxy from the owner Deck bundle, no JetExtractors authorization import; direct ffmpegdirect HLS handoff and existing script lifetime handling.
- Test: test_sports_fawa, existing Sports tests; real rig proxy playback pending. No phone or real-playback claim.


## Local FawaNews HLS resource paths rejected by FFmpeg — candidate fix

- Seen: real Linux Kodi ffmpegdirect 21.3.8 / FFmpeg 9 rejected proxy segment addresses with a query encoded into the pathname.
- Cause: exposed local URL did not end in an allowed media extension.
- Fix candidate: new loopback proxy assigns opaque media-suffixed paths and keeps the complete source URLs server-side; shares session and headers for playlists, segments and URI attributes. No token mutation or authorization bypass.
- Test: test_sports_hls_proxy uses a real controlled HTTP server and verifies master, media, key and segment traversal with headers/cookies and unchanged query. Real playback retest pending.

- Real retest: Linux Kodi with ffmpegdirect 21.3.8 / FFmpeg 9 played an actual FawaNews source through the new proxy; after initialization time advanced 9267.7 -> 9272.7 -> 9277.7 -> 9282.7 in five-second intervals and remained playing. This verifies desktop playback, not stream identity or iPhone behavior. Removed the unused vendored proxy after replacement.


## Shared Loop proxy media-path compatibility — rig verified candidate

- Seen: fresh unmodified Loop route reached ffmpegdirect but FFmpeg 9 rejected local resource paths; extension-only patch then produced segment failures.
- Cause: local proxy embedded query strings in pathname, and variant flattening returned relative media references without retaining their child-playlist base.
- Fix candidate: version/hash-guarded compatibility patch gives local resource aliases media suffixes and preserves exact original references; variant resolver rebases child media/key references before flattening. Only two readable proxy modules change; authorization and caller identity are untouched.
- Test: test_sports_loop_proxy_compat, test_sports_loop_routes, actual fresh Loop/FawaNews first-link rig playback. Kodi speed 1, time advanced 1:41:53 -> 1:42:08 across fifteen seconds. No claim that all scrapers or iPhone are verified.


## Sports cards lacked normal Loop plugin routes — catalog integration checkpoint

- **Seen:** normal Loop playback worked in the rig, but our cards still used direct JetExtractors discovery under the bootstrap caller.
- **Cause:** the real plugin listing/route handoff had no catalog adapter.
- **Fix:** discover native Loop Scraper Zone listings, schedule-match unambiguous team pairs, retain exact plugin routes, and dispatch through normal Loop. Skip replay/account menus. When Loop is installed, avoid direct bootstrap Jet imports and the inferred-live independent StreamsCenter listing.
- **Test:** test_sports_loop_routes covers discovery, ambiguous matches, exact route/card preservation and no direct Jet import. Real desktop scan discovered 43 eligible routes; Upcoming displayed 61 games. Actual card tap reached Loop; selected source returned HTTP 403. This establishes UI dispatch, not successful playback for that source or all providers. Upcoming initial-error recovery and asynchronous playback fallback still need work.


## Sports Upcoming stayed in error after late scan results

- **Seen:** real Loop scan produced its first usable result after the page's bounded initial wait; Upcoming remained in error until Retry.
- **Cause:** the periodic timer only redrew old page data.
- **Fix:** timer retries failed/uninitialized data loads through the existing guarded refresh; closing the page prevents retry.
- **Test:** test_sports_upcoming_states covers late recovery and closed-page suppression; fresh real desktop scan recovered automatically to 57 games without a Retry tap. Later snapshot contained 61 upcoming games and no confirmed live games.

## Different native Loop providers collapsed into one unknown-quality card

- **Seen:** several unrelated Loop providers appeared as one source because each reported blank quality/language; asynchronous native-plugin failures could not reach synchronous fallback.
- **Cause:** source merge treated identical missing metadata as proof of the same stream.
- **Fix:** native Loop records retain separate selectable routes with unique source identities; unknown quality is stated plainly and receives no Best claim. Existing synchronous alts behavior is unchanged.
- **Test:** test_sports_merge verifies separate choices and identities; test_sports_game verifies readable missing-quality copy. Real desktop game page displayed four separate provider buttons without clipped text. Native plugin dispatch is not proof that a source plays; automatic fallback after asynchronous native failure remains unresolved.


## Slow native Loop workers outlived the collection lock

- **Seen:** real native Loop discovery needed roughly 113 seconds, while refreshes started another collector after the original 40-second wait; the new collector overlapped older workers.
- **Cause:** run_script released its process lock and marked the snapshot complete after a bounded wait even though provider workers were still active.
- **Fix:** retain scan ownership until completion, update the heartbeat while waiting, and honor Kodi shutdown. Page waits remain bounded. Upcoming and game timers reread incremental snapshots without forcing a new scan.
- **Test:** test_sports_playback_repair checks lock ownership throughout late completion and release afterward; test_sports_upcoming_states/test_sports_game cover incremental results without another forced refresh. Real rig retest pending.


## Background native channel catalogs interrupt Sports pages

- **Seen:** native Loop Foxxy listing displayed a modal progress dialog over another Sports page.
- **Cause:** source discovery included standalone channel catalogs and several replay menus that cannot yield schedule-matched game cards.
- **Fix:** omit Foxxy/CDNLiveTV channel catalogs and explicit legacy Video replay menus from automatic game discovery; their original add-ons remain available normally. No third-party dialog or authorization code modified.
- **Test:** test_sports_loop_routes checks replay/account/channel menu exclusion. Fresh rig candidate scan/visual retest pending; retain the observed failure rather than claiming every native catalog is quiet.


## Native Sports opening acknowledged before fallback could observe failure

- **Seen:** a card dispatched Loop but downstream 403/404 occurred asynchronously, after the old synchronous fallback returned success. Distinct buttons helped manual selection but not automatic routing.
- **Cause:** Player.play acceptance is not AV startup.
- **Fix candidate:** Play best available ranks reported quality and provider priority, puts native Loop routes into Kodi's video playlist, and lets native playback skip unplayable routes. The observer only reports playing after AV startup/video state, then clears remaining entries so the game does not replay from another provider. Non-native alternatives retain the existing resolver door; user Stop prevents another fallback. Manual provider choices remain available. Native nested-link choosers can still require selection.
- **Test:** test_sports_loop_router, test_sports_game and import-review registration. Real Kodi controlled plugin test: failed route skipped, next fixture video played (1.0 -> 2.03 -> 3.03 seconds), remaining playlist empty without stopping video. Test-only validator accepted a separately named fixture addon, with no identity/auth changes. This is not a live-provider success claim. Real card/queue retest pending.

## Kodi playlist timeout carried into a later Sports request

- **Seen:** controlled all-failed queue followed later by a failed-first/good-second queue aborted before the good entry.
- **Cause:** upstream Kodi 21.3 PlayListPlayer.cpp leaves the consecutive-failure timestamp/counter after the no-playable-items branch; the default elapsed-time threshold can abort a subsequent queue at its first failure. Verified in source and rig.
- **Fix candidate:** packaged system advancedsettings sets playlisttimeout to 0, keeping Kodi's retry-count cap and profile overrides. App queue monitoring still has its own opening timeout, but cannot interrupt a blocking native Player.play call. This changes the system default for playlists, not authorization or provider rules.
- **Test:** test_customized_ipa checks the installed setting and receipt hash; repeated controlled native routing succeeds in the restarted rig using that packaged default. Native/iPhone behavior remains unproven.

## Rig process exited during simultaneous native plugin initialization

- **Seen:** third stress scan ended the private Kodi process as eight Loop Python interpreters initialized together; cgroup reported no OOM kills.
- **Cause:** unproven; no usable native crash backtrace captured.
- **Mitigation candidate:** limit native Loop discovery to two concurrent starts and prioritize providers already seen returning matched games. Direct extractor concurrency is unchanged.
- **Test:** test_sports_loop_routes checks peak native concurrency of two. Fresh real scan underway; this is not a proven native crash fix.


## Automatic queue's real Loop opening still stalls — unresolved

- **Seen:** Play best available from a real game card logs seven native choices, then shows Kodi busy opening; controlled separately named plugin fallback succeeds.
- **Cause:** unknown; native Loop initialization/GUI calls, observer callbacks and overlapping listing are candidates, not diagnoses.
- **Fix:** unresolved. Async payload now preserves the queue and UUID ownership; old requests cannot clear a replacement queue.
- **Test:** test_sports_loop_router covers payload roundtrip and cancellation/replacement; controlled Kodi fixture proves native skip/AV cleanup, not Loop success. Real provider opening remains blocked. No IPA or completion claim.


## Direct Loop playback missed the shared proxy repair

- **Seen:** owner requested a phone test by opening The Loop directly, outside our Sports pages.
- **Cause:** hash-guarded proxy preparation only ran from our playback handoff, so direct addon playback could still import the original proxy files.
- **Fix:** startup worker prepares the same two recognized readable proxy modules after a short abort-aware delay, without listing menus or touching authorization/configuration. Legacy menu discovery is disabled because the on-demand native catalog supersedes it. Native dispatch/collection no longer enters the bootstrap bare-Addon replacement context.
- **Test:** test_sports_loop_routes covers startup preparation, shutdown and secret-safe failure; test_sports_loop covers disabled default/explicit diagnostic mode; test_sports_loop_router covers native context and staged handoff. Phone direct-addon playback remains to be tested.

## Resolved media HTTP errors did not advance the native source queue

- **Seen:** a plugin can resolve successfully, then its media HTTP request fails; native resolver skipping alone did not advance that case.
- **Cause:** this real Kodi build delivered Started/Stopped before AV startup without the expected Error callback.
- **Fix candidate:** pre-AV media failure advances an explicit candidate cursor, reconstructs a cleared playlist when necessary, and preserves current request ownership across independent alternatives. Stale requests are discarded. Playback dispatch is staged until the Sports modal stack closes.
- **Test:** controlled actual HTTP 404 -> fixture video succeeded and advanced 1 -> 2 -> 3 seconds with no remaining queue; test_sports_loop_router/test_sports_game cover failure, ownership and deferred dispatch. Actual Loop/card dialog wait remains unresolved; debugger captured the provider waiting in Dialog.select/CGUIDialog.Open, not an established network wait. No universal source or iPhone success claim.


## ISSUE-367 — Sports needs ESPN games with Crew playback (2026-11-17)

Seen: owner phone report confirms Crew plays; build 567 log opens live HLS with inputstream.adaptive, H.264/AAC decoding and fullscreen about 2.2s after OpenFile. The log does not independently attribute the opener; Loop's analytics observer runs globally. Loop still refuses its recorded repository origin. Owner chooses Crew and American ESPN leagues only, filters/motorsport/boxing later.

Cause: existing catalog discovers Loop routes and creates games only when a source lists a matching pair. It has no Crew adapter, and source absence prevents scheduled games appearing. Native unknown-quality Crew routes would also collapse behind one source.

Fix candidate: read Crew's normal plugin directories, retain exact native playback routes, publish authoritative selected ESPN schedule before source discovery, overlay uniquely matching sources while retaining ESPN ids/scores/status, and keep native choices distinct. Crew-only playback does not initialize Loop/JetExtractors. Reuse existing Live/Upcoming/Leagues/game UI; no category/filter redesign.

Test: new test_sports_crew_routes.py (registered in import-review) covers matching, dates/league separation, native identity/route validation, Crew priority, no Loop calls, source-free/empty schedule snapshots and American league selection. Full workflow suite and serial rig retest pending. Parallel rig source scan exited the process after the first 75-game schedule published; source matching and live playback are not yet proven. Do not mark device integration fixed from listing success.


ISSUE-367 validation follow-up: 179 import-review commands passed; all 23 affected Sports suites reran with no failures and the final Crew regression suite has 23 passing cases. check_project passes. Selected ESPN schedule published 75 upcoming games in 1.25s (zero live). Exact routes include Crew's content=addons selector; stripping it would incorrectly select movie scraping (observed in an initially incorrect private fixture, corrected before accepting the result). Actual Upcoming → game card → Crew source → native Crew sports player → VideoPlayer played owned fixture media at speed 1, time 0 → 0.602 → 1.604s. No real broadcast/source match was verified in that schedule; phone acceptance is pending.

Discovery/playback resource handling: serial bounded Crew traversal skips search/replay/account menus and yields to new play ownership or active video; a per-listing Home marker clears in finally and playback waits up to 10s for the outstanding listing. Tests cover preemption, marker cleanup, wait, complete query retention, aliases/ambiguity/date/league, missing Crew and failed source discovery retaining the ESPN schedule. Crew-only real pages and collector do not call Loop, direct Jet or the independent adapters.

Failure retained: both broad parallel and serial native scans exited the desktop rig; GDB captured SIGSEGV in Python 3.14 PyThreadState_Swap called from CPythonInvoker::onExecutionDone. Another startup stopped in PyEval_RestoreThread. No OOM was recorded. This is a host-runtime failure, not proof of equivalent failure or success on the iPhone's Python 3.11. Final controlled UI check used private background-addon isolation/minimal Home, with Crew files unchanged. No production Python/Kodi binary patch, authorisation change, IPA or merge. See reports/sports-crew-validation.json.

## Build 568 Sports repeated discovery and refresh — 2026-11-17

- **Seen:** owner log captured three complete Crew scans lasting 150, 146 and 177 seconds, each with zero matched streams, followed by another. It also shows ignored taps during dialog closing; no causal link to discovery is established. The owner reports Crew works, but this log contains no video-start event.
- **Cause:** Crew discovery included leagues with only upcoming ESPN games, and opening Upcoming, Leagues or a game forced a new scan despite a fresh snapshot.
- **Fix:** use ESPN for both upcoming and live games, but start Crew discovery only for live games and their leagues; no live games means no Crew root listing. Reuse fresh snapshots on page entry, keep explicit refresh, and recheck stale snapshots after 45 seconds. A long scan can still delay reflecting an ESPN state change until it finishes.
- **Retest:** regressions cover zero live games, mixed live/upcoming leagues, cached snapshot expiry and no forced page-entry refresh. A real ESPN host check returned 75 upcoming, zero live, and made zero Crew calls. First test run failed because older window tests blocked forced refresh; updated them to block the actual background reads and reran. iPhone smoothness, real live source matching and cancellation during startup remain open.

## Sports stop while a native source is opening — 2026-11-17

- **Cause:** Kodi can emit the same pre-AV stopped callback for a user stop and a failed media open. Treating it as a failure could start the next source after cancellation; an ambiguous timeout or empty queue could also trigger an independent alternative.
- **Fix:** cancel on ambiguous Stop, timeout, unclassified empty queue or generic dialog; only a definite playback-error callback advances the native queue. Some real failed opens that Kodi reports only as Stop now require manual retry.
- **Retest and limitation:** focused regressions cover stop, timeout, dialog, definite error and replaced request. A desktop Kodi 21.2 slow HTTP fixture initially reached a RuntimeError after the stop and could have triggered another adapter; after fixing the timeout, it returned InterruptedError and did not invoke the second source. Kodi took about 21 seconds to unwind, so immediate stop and iPhone behavior remain unproven.
- **Diagnostics:** ESPN scheduling and Crew source traversal now log elapsed times and aggregate counts without URLs or headers. The test IPA workflow now preserves older test releases instead of deleting them.
## ISSUE-368 — Crew live title decorations prevent ESPN matching (2026-11-17)

- **Seen:** a desktop Kodi rig showed an ESPN-live college basketball game in three Crew provider listings, but the collector matched no sources for the observed decorated titles.
- **Cause:** provider-added live text, a half clock or an Eastern broadcast time became part of a team name or was parsed as a team separator.
- **Fix:** remove only the observed decorations before comparing both teams against ESPN names and aliases; reject ambiguous games and different teams.
- **Retest:** with Crew active, a rig collector matched three native routes for the real game. Regression tests cover the observed titles, distinct and ambiguous games, and source collection through direct and nested routes. This does not establish video playback or iPhone behavior. Automatic Crew activation beneath Sports remains open.

## ISSUE-369 — Crew listing needs its Kodi container beneath Sports (2026-11-17)

- **Seen:** outside Crew, real provider folders returned no results; when Crew was active, listings included a live ESPN game. Kodi refused to activate Crew after the Sports modal was already displayed. Crew also opened a non-cancelable busy dialog during some background listing requests, blocking Sports interaction.
- **Fix candidate:** open Crew's normal Kodi container before the Sports dialog, bound the startup wait, and tie discovery to a session token. Close the Sports-owned scan on exit and restore the preceding container if this session opened Crew. During a Sports-owned listing only, dismiss Crew's blocking busy dialog; stop doing so for playback ownership. Playback requests cancel the scan before the native handoff.
- **Rig retest:** actual Sports dialog over Crew found three routes for one live game. Back during an active listing closed Sports and returned to Home; another test restored the previous video folder, and a pre-existing Crew folder remained open. Quick exit/reopen started a fresh scan. A controlled immediate playback handoff retained Crew and ownership while the Sports script closed. The current in-flight request can finish after exit. A separate existing Kodi modal can prevent activation; a desktop rig cannot establish iPhone responsiveness or video playback. Visual review in the custom portrait skin and device testing remain pending.

## ISSUE-370 — Live source handoff and unresolved Crew list expressions (2026-11-18)

- **Seen:** a real Live Now source tap reached Kodi VideoPlayer but no video started; its input was an unresolved `$doregex[makelist2]` expression. All 24 sampled Crew source choices had the same structural form. A private attempt to resolve one through Crew's native directory action returned a listing error.
- **Cause:** the Live Now page previously dispatched native playback before dismissing its Sports modal stack. This ordering could block the native picker. The separate reason Crew exposes unresolved list expressions as playable entries remains undiagnosed.
- **Fix candidate:** stage native dispatch until Live Now and its modal stack close, matching the existing game-page handoff. Preserve normal direct-source behavior and report dispatch failures without private data.
- **Retest:** the actual Live Now tap closed the page and reached Kodi VideoPlayer, but the unresolved expression did not play. Focused tests cover modal/dispatch ordering, direct playback and failure notification. Full real-provider playback, safe fallback, portrait review and iPhone validation remain open.

## ISSUE-371 — Crew resolver cache is invalidated between Sports league scans (2026-11-18)

- **Seen:** an ESPN-live source selected from Sports reached Kodi with Crew's unresolved `$doregex[makelist2]` expression. The same source plays when opened through Crew after its normal parent menus are reopened.
- **Cause:** Crew clears its whole regex resolver table when each league root opens. Sports collects more than one league, so a saved route from an earlier league can outlive its resolver entry.
- **Fix:** retain the genuine Crew menu ancestry and ESPN team match with each native choice. Immediately before play, reopen the ordinary Crew path and accept only a uniquely matching fresh route. The automatic queue stages one refreshed candidate at a time, because refreshing a later league can invalidate an earlier candidate. Unknown, ambiguous, replaced, stopped or timed-out handoffs cancel safely.
- **Test:** `test_sports_crew_routes.py` covers stale-route renewal, ancestry validation, ambiguity and ownership replacement; `test_sports_loop_router.py` covers one-at-a-time staging and confirmed-error progression. In the portrait desktop rig, actual Sports Live Now → NHL → Buffalo–Philadelphia → Crew feed played H.264/AAC at 1080p with time advancing past 49 seconds. A second real Ottawa–Winnipeg route reached Crew's normal feed picker, but its selected feed did not produce video in this run; it is retained as an availability result, not treated as a routing success. iPhone playback, cancellation and source failure behavior remain to be tested.

## ISSUE-372 — Build 575 phone cards have no source choices before discovery ends (2026-11-18)

- **Seen:** owner sees ESPN cards without Sports sources, then plays manually in Crew after several failed links. Phone log identifies build575; NHL returns36 matched streams after53.37s, while NBA/NCAAB/FullLiveSites each visit0folders. Both completed Live Now visits end before the first discovery completes. Direct Crew later opens media with H.264/AAC.
- **Cause:** unresolved. The category gate and session cancellation can explain later categories not starting when Sports closes; this needs reproduction. The log does not prove incorrect team matching, permanent source failure, or which direct provider succeeded.
- **Fix candidate:** scan one Crew folder at a time, rotate among live categories after each folder, and publish partial category matches immediately. Each category retains its own traversal, unique matches, folder limit and cancellation checks. A slow individual listing can still block the next turn.
- **Test:** Crew scheduling regression checks category rotation and partial publication; Crew and Jet suites pass. Actual phone discovery, exit/reopen and live playback are not yet verified. The remaining roadmap covers game routing and fallback.

## ISSUE-373 — Crew segment proxy service removed during packaging (2026-11-18)

- **Seen:** build 575 phone log contains 28 segment-proxy-service-not-running failures across seven streamer names.
- **Cause:** the verified pinned upstream Crew manifest declares `service.py`, but the provider lock instructs packaging to remove Crew's service. The pinned launcher starts Crew's service, which starts the segment proxy. Build 565 also contained Crew without the declaration, so merely changing the lock for newly installed add-ons does not repair an already bundled copy.
- **Fix candidate:** preserve the pinned Crew service as the exception in DEC-064. For an existing pinned-version Crew copy, restore its upstream service declaration only after confirming the launcher matches the verified archive; reject a different version or launcher. Other provider services stay disabled.
- **Retest:** the genuine upstream archive digest and rig launcher/module files matched. With the original service declaration restored, a normal Kodi restart published Crew's segment-proxy port and the proxy accepted a loopback connection inside the isolated rig. A direct script launch failed because Kodi did not provide normal add-on identity; it is not used. A build 565 staged-copy check restored the declaration idempotently. This does not establish that the service starts on iPhone or that any particular source plays.

## ISSUE-374 — Round-robin Crew discovery can revisit expired league folders (2026-11-18)

- **Seen:** Crew root navigation clears a shared resolver cache. In the real Kodi rig, an NBA provider folder returned an error after opening the NHL root, but reopening NBA and uniquely finding that provider again returned five entries. The earlier fair-scheduling candidate published matches for NBA, NHL and NCAAB, so this observation does not mean every later category was empty.
- **Fix candidate:** keep Crew requests serial and reopen the genuine, uniquely identified parent folders after switching league roots before traversing the next folder. Honor session cancellation between every ancestor; do not guess ambiguous folders. Publish partial matches after each scheduled turn.
- **Retest:** a controlled regression reproduces stale-cache loss before the fix and matches both leagues afterward; additional tests reject ambiguous folders and stop on cancellation. In the real rig baseline, the league-specific NCAAB/NHL/NBA traversals logged 16/22/22 unavailable folders, while the shared live-sites route supplied the nine matches. With the candidate, NCAAB completed with zero unavailable folders and five matches; partial results included NBA, NHL and NCAAB. Parent reopening adds latency: the full scan was still running after 250 seconds. Schedules changed between runs, so this is not a controlled speed comparison. No phone result is implied.

## ISSUE-375 — AirPlay copied-audio segment failures and recovery loop (2026-11-18)

- **Seen:** owner-supplied build 575 log has two native AirPlay sessions reporting `playing`, with an external receiver active. In the second, copied-audio requests repeatedly failed with `empty segment`, followed by 36 receiver HTTP 500 errors and repeated player stall/reload recovery. At 20:15:51 the player reported being stuck around 125 seconds; it reloaded after the stall, and the 20:16:11 sample was around 81 seconds. The log contains 62 conversion-failure messages and retries of segments 12, 13, 18 and 19; these counts are repeated events, not distinct media files. The owner reports choppiness and screen mirroring as a workaround.
- **Cause:** not yet established. The conversion/serving path reports audio segment generation failed, and `gm_stream.c` marks a segment empty when no packet was written. The logs alone do not establish why packets were outside the segment or whether network conditions contributed. Some earlier receiver-write failures also occurred; their cause is unproven.
- **Next:** reproduce with an authorized local fixture matching the logged stream timing and audio layout; inspect packet timestamps, segment boundaries, seek and selected-stream behavior. Fix and regression-test only after establishing the cause; any native AirPlay rebuild/release requires the owner's separate authorization. Keep private log and media details outside Git.
- **Host investigation:** a synthetic 160-second H.264/AAC fragmented MP4 with approximately 70-second fragments successfully generated all 27 requested audio segments. An injected transient end-of-file yielded an empty segment, but a retry on the same reader succeeded. These host tests use system FFmpeg and a test-only index stub; they do not reproduce the phone's HEVC source, timestamps or iOS build. Long fragments alone and a single transient EOF therefore do not establish the phone failure's cause or justify a production retry change.

## ISSUE-376 — A source-free live game has no focused search action (2026-11-18)

- **Seen:** the phone showed live ESPN cards without source rows before the first Crew scan completed; such a card had no usable game action. A full serial rig scan with cache-safe ancestor refresh took almost five minutes.
- **Fix candidate:** show an existing-style Find sources button on a source-free live card, open the existing game page with searching/empty/error states, and temporarily prioritize that ESPN-live game in the one-at-a-time collector. Restart its genuine category traversal if necessary, retain other games' already-published records, resume fair discovery afterward, and cancel only the owned request when the game closes. Do not search upcoming or ambiguous events.
- **Rig retest:** on a cold Sports scan, tapping Find sources on the real UNLV–Kansas card opened its game page in the searching state; that page updated to three matched Crew choices. One choice opened Crew's native sport picker; its downstream provider reported an authorization block and Kodi showed playback failure. This is not successful real video or unattended nested selection. The Live Now polling thread was also found running after a child playback handoff, and is now stopped on changed playback ownership; rig validation of that cleanup remains pending.
- **Safety:** automatic native playback still advances only on a confirmed playback-error callback; ambiguous Stop, cancellation and timeouts do not select another source. The candidate now requires advancing video time after AV start before reporting success. Real fallback, current native picker behavior, portrait review and iPhone acceptance remain open.
- **Controlled rig follow-up:** injecting a first-choice error callback caused the production queue to try the second local fixture, whose video advanced from 1.14 to 2.99 seconds; an injected Stop callback cancelled after one attempt. These are controlled callbacks, not evidence that a real failed provider emits the required error. A separate actual HTTP-failure experiment produced an ambiguous interruption, and another attempt ended in a Kodi 21.2 rig process abort with a busy-dialog error. Its cause and applicability to the phone are unknown; do not claim reliable real-source fallback from these fixtures.

## ISSUE-377 — AirPlay position lost after a stalled reload (2026-11-18)

- **Seen:** the owner's build 578 session stalled near 948 seconds, reloaded, then reported an empty player at zero before it was closed. The existing close-log handoff ignores zero, leaving Kodi at its earlier position. The existing Continue Watching tracker could also overwrite its last TV position with that zero during a prolonged reload.
- **Fix candidate:** retain the last sampled position when the AirPlay item is unready, its buffer is empty and its position temporarily reports zero. When that same native generation ends, return the retained position to Kodi only if the same Kodi file is still open. A ready player reporting a deliberate rewind is followed normally; an unavailable or replaced file is never sought. This is limited to a sampled position and does not establish sync for other AirPlay failure modes or items without a Continue Watching entry.
- **Validation:** controlled Python regressions cover a prolonged zero during stalled reload, same-file handoff, deliberate rewind and replacement video. Relevant playback and project checks pass. Actual iPhone/Apple TV close, watched-status persistence and accuracy remain unverified. The owner separately confirmed switching apps and locking the phone work.
- **Step 5 follow-up:** the last native snapshot can be newer than the last periodic history update; use and persist it for the same file and generation before seeking Kodi. A ready, nonempty final snapshot at zero can represent a deliberate rewind, while a stalled unready zero remains ignored. A changed Kodi file detaches the old generation so it cannot update the next video's history. The independent close-log handler now fingerprints the originating Kodi file in memory and refuses to seek a different video. Controlled tests use the real local history implementation for final position, completion and replacement and cover rewind and close ownership. The first run exposed a test window without `clearProperty` on an absent owner; the handler now returns before clearing an absent mark and the suite passes. Native player, Kodi library/provider-specific history and iPhone behavior remain unverified.

## ISSUE-378 — Build 578 slow AirPlay source ranges (2026-11-18)

- **Seen:** the owner's phone log shows range responses without the requested byte range, repeated source retries and cache waits during inspection and playback; the TV reported six-second media request timeouts. It does not prove why the upstream server refused requests or how much of the stall was conversion versus source contention.
- **Step 1 fixture:** `scripts/test_airplay_range_fixture.py` runs a real loopback HTTP source through the production foreground cache. It injects 80 ms per request and two status-200 responses without Content-Range for each piece of one block, either during simulated inspection or concurrent simulated media reads. It verifies exact returned bytes, range rejections, retries and a shared cache wait. Speculative read-ahead is disabled in this fixture to isolate the injected faults; production settings are unchanged. The HTTP readers do not decode media or emulate iOS, FFmpeg, AirPlay or a TV.
- **One controlled run:** healthy inspection 0.298 s and concurrent reads 0.116 s; inspection faults 1.159 s and playback faults 1.095 s, with eight rejected responses and eight retries in each fault scenario. These numbers describe this fixture, not the phone. Step 2 must compare any candidate under the same fixture as well as slow/fast sources and production read-ahead; no latency or buffering fix is claimed yet.
- **Step 2 candidate:** distinguish an upstream range refusal from a wrong or inconsistent range. Split-piece reads now stop retrying that refusal and use the existing constrained single-connection block fallback; ordinary Drive reads and other transient errors retain their previous retries. Existing consistency checks remain in force. In one synthetic concurrency-limited comparison, concurrent reads fell from 0.597 to 0.368 s. When both split and fallback ranges were refused twice, the candidate reduced requests from 20 to 15 but took 1.172 s versus 1.061 s before: it is not a universal speedup. Fixture read-ahead tests returned exact bytes for fast, slow and rejected-range sources; single noisy timing samples are not evidence of no performance regression. Actual conversion, stream playback and iPhone results remain unverified.
- **Checks:** relevant source, opening, native transport, preparation, conversion and fixture suites pass, as does `check_project.py`. Optional `test_slowdown.py` has two failing source-text assertions that predate this change: they expect an older inline service implementation, while the committed service uses `slowdown.play_reason`. No slowdown production code was changed for this candidate.
- **Step 6 regression:** full import CI run 44347647630 failed `test_stream_reads.py`: after an early split-range refusal the fallback exhausted its three attempts before the synthetic server recovered. Preserve a bounded additional fallback budget specifically for range refusal; do not retry forever or change other error types. The original recovery regression and a new permanent-refusal bound both pass locally. Re-run the full workflow; fixture improvements do not establish real phone buffering.
- **Slowdown check repair:** the two optional source-wiring assertions described above referred to the service before its `slowdown.play_reason` refactor. Updated them to verify the current service wiring; all 26 slowdown tests pass, and the suite is registered in import CI. No slowdown production behavior changed.
- **Full retest:** GitHub import run 44358013453 passed after the bounded-fallback repair. All 180 then-registered commands also completed locally: 179 passed on the first run, and the Python 3.11 packaging case passed after installing an isolated interpreter. The initially missing interpreter was a local test prerequisite, not an IPA build. No real iPhone playback result follows from these tests.

## ISSUE-379 — H.264 High 10 AirPlay compatibility investigation (2026-11-18)

- **Seen:** build 578 inspected the owner's H.264 High 10, 10-bit 4:2:0 video and enabled conversion to 8-bit H.264. The normal app policy explicitly converts H.264 above High Profile or 8-bit. Conversion is a cause of work at startup, but the same log also contains slow source reads; bypassing conversion cannot be assumed to eliminate buffering.
- **Apple documentation:** the general Apple-device HLS authoring specification limits H.264 to High Profile or below and separately allows HEVC Main 10: https://developer.apple.com/streaming/hls-authoring-specification-for-apple-devices.html. High 10 H.264 is a different profile from High and is outside that stated HLS limit. Apple TV generation/model and actual High 10 decoding in the owner's particular receiver remain unverified. Do not claim every Apple receiver necessarily fails every nonconforming file.
- **Existing host evidence:** successful `host-tests` job 133441177291 in run 43907784636 exercised a synthetic H.264 High 10 input through the normal converted route, fetched a seek segment and decoded host-encoder output; it also tested compatible HEVC copying and strict original-picture refusal for High 10. The job uses a host MPEG-4 encoder, not iPhone VideoToolbox or a real Apple TV. The current native source and host test scripts match that run; the source-lock metadata later changed. Its overall run failed only because the separate macOS framework job was canceled, while a subsequent framework candidate succeeded as documented in progress.
- **Decision / limitation:** retain the existing conservative conversion rather than silently enabling an HLS profile outside Apple's specification. No receiver-specific passthrough or fallback was implemented or tested. The owner's model and a direct iPhone/Apple TV experiment would be needed to establish that receiver's behavior; the user has not requested a new IPA. 10-bit HEVC is a possible alternate source, subject to receiver and subtitle compatibility and device testing. Applicable Python AirPlay remux and long-fragment checks pass.

## ISSUE-380 — Stall reload plays before seeking (2026-11-18)

- **Step 2 review:** replacement waits for item readiness, seeks once, checks generation/current item/active ownership on completion, and plays only after successful completion. Timeout calls playbackStateFor with active=0, preventing a later seek callback from playing; generation replacement also rejects old callbacks. Seven source-wiring and22 local-history cases pass, but these do not execute AVPlayer. User-pause intent is not explicitly captured: recovery itself pauses the replacement and completion calls play, so rate=0 alone cannot distinguish recovery's pause from a user pause. The earlier first-stage stall recovery can also call play after a recent error. A reliable intent signal and controlled AVPlayer test are still needed before claiming user-pause correctness. Linux cannot run UIKit/AVKit or reproduce external-receiver scheduling; native compilation is insufficient. No speculative pause-policy patch made.

- **Seen:** build 578 logged a stall near 948 seconds and replacement of the player item, after which the receiver requested a segment near the initial 732-second start; the replacement never became ready and playback remained at zero. The native recovery code calls `play` on the new item before waiting for readiness and seeking to the saved stall position. The log is consistent with premature opening but does not prove AVPlayer's internal request cause.
- **Fix candidate:** pause before replacing the item, retain the saved position, wait for the replacement to be ready and play only after an uninterrupted seek completes on the same live player generation and item. Prevent further automatic reloads during the pending recovery, and end that recovery with the existing error presentation after 30 seconds rather than waiting indefinitely. Disable a late initial seek for the replacement. A new native framework build and pin are necessary before any IPA can contain this source.
- **Validation / limitations:** Python source-wiring regressions check ordering, completion ownership, cancellation and the deadline; shell syntax and the applicable existing AirPlay tests pass. These are static checks, not a simulated or real AVPlayer. Native framework compilation and device behavior are still unverified; a paused replacement may still need its initial HLS media to become ready and can time out. Do not claim the backwards request or buffering is fixed on iPhone without a real retest.
- **CI follow-up:** run 44343640378 passed native host tests; its framework job was canceled because a hosted runner was not acquired. A failed-job rerun has been started; see the run for its current status. No native framework release or IPA was published.
- **Native retry result:** run 44343640378 attempt 2 passed the host job and compiled the iPhone framework candidate for commit `95bb0d2`. This is not execution of the stall path on AVPlayer. The candidate is not published or pinned; the existing r65 pin and build 578 still lack the source change.
- **Artifact access:** the Actions artifact exists but this workspace receives a storage-service Forbidden response when downloading it. The successful GitHub compilation is verified through job status; independent local binary inspection remains open.

## ISSUE-381 — Sports opening candidate critical review (2026-11-19)

- **Seen:** PR47's opening-surface candidate (b99d6ba) passed its own stated checkpoint (five lifecycle unit tests, 53 Crew/23 Jet/22 Live/20 Game tests, a controlled rig render) but was explicitly flagged as not yet critically reviewed: no real source had played through the new loader, and the checkpoint itself warned passing tests do not prove correct wiring.
- **Defect 1, build-breaking, fixed:** `sports_opening_page.py` does `import pages`, but `portrait.py` loads every sibling module (including `pages` itself) via `importlib.util.spec_from_file_location`/`exec_module` into local variables only, registering just two explicit `sys.modules` opt-ins (`status_ui`/`notifications_skin`, and `sports_page` for the same reason). `pages` was never one of them. Reproduced deterministically in a clean environment: `ModuleNotFoundError: No module named 'pages'` at import time. Both the real IPA build (`scripts/ios_portrait.py`) and the desktop rig sync load `portrait.py` the same bare way, so this broke the entire skin build, not only Sports. Fixed with the same `sys.modules.setdefault('pages', pages)` precedent already used for `sports_page`; verified a clean import and a clean `kodi_rig.py sync`.
- **Defect 2, existing regression test broken, fixed:** this PR made the native play path in `sports_jet.run_script` unconditionally construct and `.open()` a real `xbmcgui.WindowXMLDialog` before calling `play()`. `test_sports_loop_router.py::test_native_script_does_not_replace_the_addon_constructor` stubs `xbmcgui` as an empty namespace and was not updated for this new step, so `opening.open()` raised and `play()` was never reached — confirmed present on b99d6ba before any of this review's fixes. Fixed by stubbing `sports_opening.Opening` in that one test so its original intent (no addon-constructor replacement on the native path) is still exercised.
- **Review question 1 (can the opening Surface block Crew's native picker), empirically checked, favorable but partial:** a rig probe opened the real `Surface` class exactly as `sports_opening.py` does (`WindowXMLDialog(...).show()`), then created a genuine `xbmcgui.DialogProgress()` carrying Crew's own confirmed scraper-search title/text (read from the pinned Crew add-on's `control.py`/`sources.py`). The rig screenshot (controlled fixture, not device, not real Crew) and logged `xbmcgui.getCurrentWindowDialogId()` show the `DialogProgress` (window id 10101) rendering on top of the Surface (window id 13001) and remaining the current dialog for its duration. Separately, by design this candidate's route for `TheCrewRoute` never activates Crew's own container/navigator window — `refresh_link()` resolves a leaf file URL in-process and `xbmc.Player().play(file)` is called directly — so the historical ISSUE-369/370 failure (Crew's container refusing to activate beneath an already-shown Sports modal) does not apply to this flow as written. This is one controlled observation of one native dialog type, not proof covering every Crew dialog/selector.
- **Review question 4 (stale/late `onAVStarted`), partially mitigated:** `xbmc.Player` callbacks fire for any playback in the app on every live `Player` subclass instance, not scoped to the instance that issued `play()`. Added an ownership check inside `Observer.onAVStarted` (matching the one `tick()` already performs) and clear `self.observer` in `close()` so a finished Opening's Observer is released for GC promptly. This narrows but does not provably eliminate the exposure, since Kodi's API does not expose per-call-scoped playback callbacks; no other code path in this app calls `xbmc.Player().play()` concurrently with an open Sports loader in normal use.
- **New tests:** `scripts/test_sports_opening.py` grew from 5 to 9 cases (long team names, malformed/empty native-queue descriptors, observer dropped on close, late ownership-mismatched callback ignored). These remain pure logic tests of `Opening` with fakes for `home`/`window`; they do not exercise real Kodi XML generation, consistent with the standing caution against treating passing tests as proof of correct GUI wiring.
- **Checks:** `scripts/test_sports_opening.py` (9), `test_sports_jet.py` (23), `test_sports_crew_routes.py` (53), `test_sports_live.py`, `test_sports_game.py`, `test_sports_loop_router.py` (17, after the fix above) all pass; `check_project.py` and `check_ui_guidance.py` pass; `kodi_rig.py sync` succeeds cold. See `docs/SPORTS-OPENING-REVIEW.md` for the full per-question checkpoint, including what is still outstanding (app-shutdown path, background-thread `setProperty` safety, slow-wait text/stage ordering under a live call sequence, cold-install robustness beyond the `pages` fix, pixel comparison to the approved mockup, and any real Crew source played end-to-end through this loader). No real-source playback demonstration, no native Crew chooser interaction with a live provider, and no before/after timing measurement were produced in this review pass; none of that is claimed as done.

## ISSUE-392 — Build600 receiver seek repeats an empty MP4 audio window (2026-11-19)

- **Post-IPA602 investigation:** added continuous-audio indexed and fragmented MP4 fixtures and replay of windows0,9,132,171,178,1,178,178,9,0 over HTTP. Each reused-reader fragment must be nonempty and byte-match an independently opened fresh-reader fragment (excluding init metadata). This distinguishes request-history corruption from content/window differences in controlled media. Native execution pending; no playback behavior or r68 pin changed. It does not simulate the phone's exact source, receiver timing or lane contention.

- **First replay result, run44647499269:** indexed MP4 comparisons passed. Fragmented cases rejected windows after0 because empty_moov fixture headers advertise no finite duration and probing saw only5.04s; corrected fixture duration metadata to1300s, matching its generated media. This is a test setup correction, not the phone's empty-audio failure. A separate pre-existing retry assertion also failed: both lanes succeeded after35s without an application retry, so the assumed fault path was not reached. Preserve that failure rather than weaken its assertion. Added focused audio-replay mode for independent diagnosis; corrected matrix retest pending.

- **Corrected matrix result:** focused native run44648845367 (cfa3a1c) passed84/84 checks for indexed/fragmented MP4 seek replay and fresh/reused media-fragment equality. The synthetic continuous-audio files do not reproduce the owner's failure. Full regression status is not inferred from this focused run; original-source timing and simultaneous receiver/audio lane contention remain open. IPA602/r68 remains unchanged.

- **Diagnostic candidate:** bounded packet-window summaries now record selected audio stream/timebase, requested window, packet timestamps, filter/write counts and scan exit, correlated with request/session IDs, cache state, lane wait and reader reuse. No URLs, headers or packet payloads are added. A deliberately absent-audio fixture verifies empty-window reporting followed by successful later audio on the same reader; this is not reproduction of the owner's source. Native run44640470233 is the final validation gate. Earlier run44639179231 passed3810/3811 checks; its retry-log assertion used an8192-byte partial drain, now enlarged without weakening the assertion. Owner authorized diagnostic framework/IPA publication; phone root cause remains unresolved.

- **Seen:** owner reports downloaded short/long seek failures. MP4 attempt requests video178 successfully, but audio178 repeatedly returns HTTP500/empty segment,2scanned packets,0ms source I/O, without cancellation/deadline expiry; receiver/app eventually fail.
- **Cause:** unresolved; inspect independent audio reader reuse, seek/window timestamps and out-of-order requests. Do not equate packets scanned with packets muxed or infer corrupt media. Container/order align with the downloaded report but do not independently prove origin.
- **Fix:** none yet. Prioritize deterministic reproduction of0→9→132→171→178 including audio1 contention; see docs/AIRPLAY-BUILD600-ROADMAP.md.
- **Test:** phone regression evidence, not a passing fix. Verify ordinary receiver HTTP requests separately from PR49's initial-priming retry; no new runtime tests in this documentation checkpoint.

## ISSUE-393 — Build600 MKV AirPlay preparation/delivery remains slow (2026-11-19)

- **Build608 step1 reproduction candidate:** native host test `test_receiver_resume_handoff` exercises phone copy master/prime followed by an MFi receiver master at20s, with subtitle-burn routing. Indexed prepared MP4 and long-GOP MP4 cover same/different copy/conversion grids. Read-only cache/plan observers are compiled only under KR_REMUX_TEST and absent from frameworks. Observation mode must show cached copy, cold converted target and background conversion of0; desired-contract mode must fail exactly the four readiness/obsolete-zero checks, with other requests succeeding. Registered via import workflow shell validation and focused native workflow receiver_handoff_only; execution pending. No playback behavior, framework pin or IPA changed. This does not reproduce AVPlayer/receiver failure or prove all latency comes from these defects.

- **Step1 result:** run44664113987 on5ccd958 passed19 observation checks and confirmed exactly four expected desired-contract failures across both fixtures. Actual production HTTP/cache/converter reproduces cold TV target after copy priming plus obsolete0 work. See docs/AIRPLAY-TV-HANDOFF-REPRO.md for limits and the step2 red-to-green transition. No fix/device result is claimed.

- **Step2 repair (source, native result pending):** `kr_remux.c` now prepares, on a third-party receiver's master request, the converted init and the converted unit holding the resume position (and converted audio when a converted plan exists), mapped through the converted plan's own grid (`resume_segment`, `receiver_prepare`), instead of queueing converted segment 0; after an init the following units are those after the resume segment of that rendition. The phone/Apple route still converts nothing. The expected-red wrapper was replaced by a normal regression gate `--receiver-handoff` (also in the full native run): copy cached, converted cold for the phone, converted target (and audio) cached after the MFi master, zero never made, repeated masters safe, init+window decode frames, zero-start still prepares segment 0. `test_airplay_remux.py` now forbids `prefetch_push(R_VCOMPAT, 0)`. Native result: run 44666362184 (27fbb06) failed only the decode check because the focused run does not create its output folder (test defect, fixed in 5a60990); run 44667223229 (5a60990) passed: **40 receiver handoff checks, 0 failed** (copy cached, converted cold for the phone, converted resume window prepared after the MFi master on both grids, no segment 0, repeat masters safe, init+window decode frames, zero start OK). Edge cases added afterwards (subtitles off, backward seek, rewind to 0, stop during preparation, next session unaffected) are in `test_receiver_handoff_edges`; their native result is recorded when run. No framework pin, IPA or merge changed.

- **Build611 phone log (owner, TV "Bedroom" = an Apple TV, copy route; installed AirPlay r67, so no r68 request traces): seeks restart near the beginning, then AirPlay stops with "empty segment".** Seen in the log: (1) a seek asks for `/video/seg24` (about 2:24); producing it took 5.9 s (source I/O 4.1 s, audio window 3.7 s on a second lane) and the TV gave up after its 6.006 s limit ("-12889 No response for media file in 6.006s", "Receiver write failed (32)"); (2) the player's clock still read the old position (14.9 s), so the existing stall recovery "reloading the stream there" reloaded at 14.9 s, the new item began at segment 0 and was moved only 8 s later ("compat stream ready, resuming at 14.9 s"): the viewer's seek was lost and playback restarted near the beginning; (3) later, `audio: copy segment=16 ... packets=2 result=-1`, "empty segment" for a window inside the movie (stream 2, jump from segment 8, reader reused, no scan, no source I/O), repeated for segments 10 and 11, then HTTP 500 and "AirPlay stopped ... /audio/2/seg10.m4s: empty segment". Same signature as the earlier ISSUE-392 window (two packets, zero I/O, no cancel/deadline).
- **Build611 changes (source, native result pending):** (a) the server remembers the latest receiver jump (`note_video_request`, start of the requested video segment, `kr_remux_recent_seek_target`); the stall reload now resumes at that target when it is recent (60 s), else at the player's clock as before, and names the position with `kr_remux_set_resume` so the reloaded stream's playlists carry `EXT-X-START` and a TV's converted resume window is prepared for it (no first fetch of segment 0); (b) an empty copied-audio window on a reused shared reader (at most 8 packets, under 1.5 s, inside the movie, not stopped or canceled) closes that reader, opens a fresh independent one and retries once; both attempts are logged ("reopening the independent reader once", "audio: reopened reader ..."). The cause of the empty answer itself is still not proven (a local reproduction with PyAV on a two-audio fragmented MP4 did not show it), so (b) resets suspect reader state and is evidence-producing, not a claim of root cause; if the reopened reader also answers empty the log will show it. Not changed: the slow production of seek targets (copied video 4-6 s, audio window scan 3-9 s competing on the same source), which remains the measured smoothness target.
- **Build611 tests:** `test_seek_target_and_empty_window` (native: in-order reads are not a seek, a jump and a jump back set the target, an old jump expires, a reload's playlist starts at the resume position, an injected empty audio window is recovered by one fresh reader and the next window is served); `test_airplay_remux.py` requires the new symbols. Host fixtures only; the TV result needs the owner's phone.

- **Build612 phone log (owner: "airplay didn't connect to TV again"; installed r69, request traces present, Apple TV "Bedroom", Drive copy, no uploads running):** the TV (and the phone's own player) chose audio track 2 while priming had chosen track 1 (the engine's default). Priming then made audio ahead for track 1 (`prefetch_after`), and the background worker kept starting track 1's next windows (5-6 s each, source I/O 2-3.5 s) because audio "demand" was counted per track while all copied audio shares one lane and one independent reader. The TV's first audio window (track 2, segment 0) waited 11.3 s (`waited 11305 ms`), the TV hit AVPlayer's 6.006 s limit ("-12889 No response for media file ... seg0.m4s"), cancelled its video request after 720 KB ("Receiver write failed (32)"), and after one reload ("still stuck at 0.0 s ... reloading") the stall recovery gave up ("stall recovery timed out before the seek completed" -> "The TV could not play the converted stream"). Build611's log showed the same wait (9.7 s) for the same reason. Also seen and NOT fixed: after audio was ready the TV took 16.6 s to receive a 4.4 MB video segment (about 2 Mbit/s; the stream needs about 12 Mbit/s) with the library idle, i.e. a slow phone-to-TV Wi-Fi path at that moment (the same TV took a 4.4 MB segment in 1.3 s in the build611 log); no source change can make a path faster, and a lower-bitrate variant for a slow path is a separate design.
- **Build612 changes (source, native result pending):** audio demand now counts for the whole shared lane (`lane_demand`), so background audio work waits while any audio track has a request waiting; a foreground request for one audio track drops queued windows of the other tracks; priming no longer makes audio ahead (the receiver's first audio request does, for the track it actually picked). Test `test_audio_lane_follows_the_receiver` (new two-AAC fixture, injected slow source via `kr_remux_test_audio_delay`): priming makes one window, nothing runs ahead, the other track's first window is served after at most the window in progress and the primed track's later windows did not run ahead of it. Host evidence only; a TV result needs the owner's phone.

- **Build612 downloaded-show log (owner, r69 installed, "airplay did seem to work"; correction of the Wi-Fi remark above):** 7 minutes of real-time playback after a 16-25 s start stall; the r69 seek resume worked ("reloading the stream there (resuming at 498.5 s, the seek the viewer made)"). Windows already cached when the TV asked reached it at a median 36.5 Mbit/s and none took longer than real time, so the earlier "slow Wi-Fi" reading was wrong: those slow sends were waiting for Drive production, not for the network. What was slow: 64 audio requests waited over 2 s (worst 10.4 s; the shared audio lane, fixed in r70), and even in steady state 16 of 71 video and 25 of 74 audio requests waited over 2 s because the lead made ahead was only 12-18 s while a Drive-bound window costs about 60% of its playing time. The Drive proxy log line showed 75-150 ranged requests a minute at a 0.5 s median first byte.
- **Retry-evidence test (ISSUE-393, runs 44647499269 and 44685089607; owner approved the change, 2026-11-20):** `test_seek_audio_retry` asserted that the application's own "retrying ... segment" line appears. The fixture's fault (the first qualifying request is never answered for 35 s) is recovered by whichever layer meets it first: the application retry or the byte source's fresh-connection retry below it. In run 44685089607 the whole prime lasted 35 005 ms and succeeded with no application retry line, so the assertion failed although the recovery was real. The assertion now accepts either recovery but still requires proof that the fault fired (the application retry logged, or a prime that lasted at least 25 s and succeeded); a run in which the fault never fires still fails. The earlier failures stay recorded here. A fully deterministic fault (forcing which lane meets it) was not built.
- **Build613 follow-up change (source, native result pending):** the lead made ahead is longer: 5 video windows deep and 24 s (30 s when a window costs over 70% of its time), audio 18 s. Test `test_video_lead_is_long_enough` (after one served window the next four video windows are made). Evidence limit: host fixture; whether the phone buffers less depends on Drive speed on the day.

- **Seen:** likely streamed MKV attempts prime video/audio in31.6–41.6s; High10 video is converted with subtitles, some6s video windows take7–16s production. One attempt fails, another advances before close. Owner reports long-seek TV response timeouts.
- **Cause:** not isolated. Source I/O, shared waits and conversion overlap; summing them would be wrong. The log does not independently isolate a>10minute user seek in these MKV sessions. Canceled requests following receiver failure are not automatically the initiating cause.
- **Fix/test:** none yet; reproduce constrained source+conversion workload and separate timings before changing retries or timeouts. Preserve codec compatibility. Roadmap and phone acceptance remain open.

## ISSUE-391 — AirPlay seek kills the session when its parallel audio fetch fails once (2026-11-19)

- **Release validation follow-up:** native host/compiler run44612304285 and independent artifact inspection44617321795 passed; verified r67 is in testing IPA600 (source684d54b), confirmed by exact packaged binary hash. Earlier verification status below is historical. The deterministic fixture creates a read timeout and confirms retry recovery; it does not prove the owner's provider enforces a particular concurrency rule. Real receiver/source acceptance remains pending. PR49 is not merged to main.

- **Seen:** owner's phone log, build 596 (AirPlay r66, already includes the ISSUE-377/380 stall-recovery fix), a real Umbrella episode streamed from Drive. A seek roughly 10 minutes forward sent the video and its independent audio connection new byte-range requests together. The video segment buffered successfully but slowly (23.5 s, of which 15.2 s was raw source I/O); the audio segment failed outright about 1 s later (zero packets, result -5). AirPlay reported "The operation could not be completed" and stopped. The owner's retry got stuck in "opening" for 97 s (against the code's own 100 s deadline) and failed for real: "The movie could not be buffered from Drive in time." The owner confirmed seeking in local (non-AirPlay) playback on the same kind of stream is fine, which points at this native remux/seek path specifically, not general source slowness; "Drive" in that message is this pipeline's generic buffering-failure wording, not a claim that Google Drive itself was the source.
- **Root cause:** `kr_remux_prime_for` (`migration/airplay-ios/remux/src/kr_remux.c`) fetches the video segment on the main thread and the audio segment on a parallel thread (`prime_audio`), each via `get_part` exactly once with no retry. The independent audio reader (`audio_demuxer`/`S.asrc`) is a second long-lived connection to the same resource, opened once per session and reused; a big seek makes both connections issue new range requests to the same resource at roughly the same moment. The evidence (one succeeds slowly, the other fails fast with zero bytes) matches a server refusing a second concurrent connection to the same resource more than it matches a timeout. Because `prime_audio` never retries, that single fast failure overrides an otherwise-successful video fetch and fails the whole seek.
- **Fix:** on an audio-fetch failure during a parallel prime, retry it once, serially, after the video fetch's own connection traffic has settled — still bounded by the existing overall startup deadline (`S.startup_end_ms`) and the request's own cancellation/ticket checks, so it cannot hang past what was already enforced. A first-try success is unaffected.
- **Test:** added a `/busy/` fault mode to the host-test fixture server (`migration/airplay-ios/remux/tests/range_server.py`) that refuses a second concurrent connection to the same resource and recovers once the first connection finishes — the same shape as the observed failure, not a plain dropped-connection truncation (`kr_source_read` already recovers those transparently; this is a different failure class). New host test `test_seek_audio_retry` (`migration/airplay-ios/remux/tests/test_remux.c`) opens a real session against a 1300 s / 600+64 kbit/s fixture, seeks to 40 s (comfortably past the fault's 256 KiB-per-connection threshold on both tracks), and asserts the seek recovers to `KR_READY` and that the retry actually ran (checks the log line, so the test cannot pass on a lucky first try).
- **Verification status:** both changed C files compile cleanly (`gcc -fsyntax-only`); the full host-test suite needs this project's pinned FFmpeg/libass host build, which exists only in CI (building it from scratch locally was judged too slow/expensive for this session), so it has not run locally. Dispatched on branch `fix/airplay-seek-audio-retry` via the `airplay-remux.yml` workflow (host tests + native framework compile) — see that run for the actual result before this is pinned or shipped. Not merged to `main`. No framework publish, pin or IPA build has happened yet for this change.
## ISSUE-382 — Sports: a league filter, applied to every page (owner request, 2026-11-19) — backend done; pages and logos next

- **Owner:** "make a way to edit what leagues show up … so if you only want to see NFL games then that's the only option picked" (approved board B, docs/design/sports-redesign-mockups.html).
- **Done:**
  - `sports_filter.py` keeps the leagues turned off in `sports-leagues.json` (default none, so every league and any new one shows).
  - `FilteredProvider` wraps the one provider every Sports page reads (`sports_provider.get()`). It filters live games, upcoming games and leagues, and recomputes the overview (live count, sports, next game, more today, league count), so the hub, Upcoming and Leagues always agree.
  - `all_leagues()` lists every league for the Edit sheet, filtered or not.
  - `summary()` gives "Showing NFL and NBA", "Showing 4 leagues" or "No leagues selected".
- **Tests:** test_sports_filter (12). test_sports_espn, test_sports_loop and test_sports_model now look through the wrapper (`sports_filter.unwrap`).
- **Done in the app (desktop Kodi rig, sample data; screenshots kept out of Git):**
  - **Edit button** on the hub, Upcoming and Leagues (`sports_edit_button.py`): blue "Edit", white "Edit · 11" while a filter is on.
  - **Edit sheet** (`sports_edit.py`, on the app's choice sheet): step 1 lists the sports with "3 of 4 leagues on" and an icon each, plus "Turn every league on"; step 2 shows one green switch per league with its logo. Every flip is saved at once and the pages follow (Bundesliga off: the Leagues page showed 11 leagues).
  - **Real league logos** (`sports_logos.py`) on the Leagues rows, the Edit sheet and each Upcoming game, replacing the letters. Fetched from ESPN's image host on first use and kept on the phone; never committed. A league with none (boxing) gets a neutral ring.
  - A test had written logo files beside the code (a stand-in for Kodi's path translation, with network access). `sports_logos.fetch` now writes nothing unless the profile path is a real folder (test added). The commit that shipped it contained no images.
- **Tests:** test_sports_filter (20), test_sports_logos (4), test_sports_leagues (RealLogos).
- **Not done yet:**
  - The cleaner page layouts of board A (the hub keeps its approved gradient tiles; Upcoming and Leagues keep their rows).
  - "Only" per sport and "All off" shortcuts in the sheet.
  - The hub's "Showing NFL and NBA" line is coded but not seen in the rig with a filter on.
  - Logos on the Live Now page and the game page.
  - The phone check.

## ISSUE-383 — Sports game page: Remind me, then Play with the best source (owner request, 2026-11-19)

- **Owner:** "follow should ask to send a reminder to your phone, then when the link is available it will replace the remind with the play button providing you with best source" (approved board C, docs/design/sports-game-mockups.html). Kodi can notify, so the reminder is real.
- **Done:**
  - `sports_reminders.py` keeps `sports-reminders.json` (one record per game, two switches: "when a source is ready", "15 minutes before it starts"), decides what is due, and `watch()` runs in the service (`sports_reminder_loop`), searching for sources about every 10 minutes for reminded games. Each notice is sent once, pruned 6 hours after the game, and opens the game on tap (`RunScript(...,sports_game,<id>)`).
  - `sports_remind.py` is the reminder sheet on the app's choice sheet. A new reminder is saved only by "Turn on reminder"; an existing one saves each flip at once and can be turned off.
  - Game page: no sources → white "Remind me" capsule; reminder set → "Reminder on" capsule plus a note of what we'll notify; sources → "Play" with "Best source: …" under it.
- **Tests:** test_sports_reminders (13), RemindThenPlay in test_sports_game (the old "sports_game is not in default.py" assertion was inverted on purpose: a notification opens a game by id).
- **Desktop Kodi rig (sample data):** Remind me → sheet (no cut-off text) → "Reminder on" with its note. Not seen on a phone yet.
- **Not done yet:** see ISSUE-384 (Info and standings).

## ISSUE-384 — Sports game page: Info, recent form and standings (owner request, 2026-11-19)

- **Owner:** approved board D (one scrolling Info page), minus the "Watch on" row ("this is literally the player").
- **Done:**
  - `sports_game_info.py`: venue (from the scoreboard), each team's record and home/away split, the last five results (ESPN team schedule, W / L / D) and the standings (ESPN standings, `level=3`). The table shown is the smallest one holding a game team (division, or a league table for soccer); sports with divisions also get a "Wild Card" view (the conference by playoff seed). A game team below the 8-row cut replaces the last row. A feed that fails leaves only its own part out; answers are reused for 10 minutes.
  - `sports_espn.parse` now keeps team id, record, split, venue and the league path on each game.
  - Game page: Kickoff / Venue card, "Recent form" card with W / L / D dots, "Standings · AFC South" with crests, the two game teams tinted, and a Divisional / Wild Card switch. A part with no data is not drawn.
  - `KODI_IOS_SPORTS=sample` shows board D's Colts at Texans fixture in the desktop rig (never used in the app).
- **Tests:** test_sports_game_info (15), listed in import-review.yml.
- **Desktop Kodi rig (sample data):** Info card, recent form, standings (tint, header, rows) and the switch to Wild Card and back, no cut-off text. Checked live ESPN answers for NFL, NBA and EPL with a script.
- **Not built:** the "Full standings" link (the app's choice sheet holds 8 rows, so a 32-team table does not fit it; needs its own page). Not seen on a phone yet.

## ISSUE-385 — Sports pages rebuilt to the owner's mockups, one page at a time (2026-11-19)

- **Owner:** eight mockup screens (hub, Upcoming, Leagues, Edit sheet x2, game page, Remind sheet, Game info) — "this is ideally how I want it", "one at a time … show me the rig match".
- **Page 1, the hub (mockup A1):** compact Live Now card (grey "Nothing live right now · Next game starts at …", or the red gradient with the "4 live" capsule), "Up next" (the next three games in the Upcoming page's own rows, with See all) and two short Upcoming / Leagues tiles ("59 games · 2 more today"). The "Finished today" placeholder row is gone (it only said "coming in an update"). The page scrolls as one list.
- **Time style (A1 and A2):** the time is "4:30" large and blue with "PM" under it, and "in 44 min" under that when the game is close; Upcoming uses the same rows (`sports_upcoming_page.game_row`, now shared).
- **Tests:** test_sports_landing updated to the new properties plus a test for the Up next rows.
- **Desktop Kodi rig (sample data):** live state and idle state (filter hides the live leagues) checked against the mockup. Not seen on a phone yet.
- **Page 2 follow-up (owner):** the Upcoming league chips wrapped and left one chip alone on a second line. They are now one row that scrolls sideways (the screen edge cuts what does not fit), `CHIP_LINES = 1`; test_sports_upcoming updated. The Live Now page's chip grid is not in the owner's mockups and is unchanged.
- **Page 2, second follow-up (owner: "is that even needed if we have our filter?"):** the chip row is removed from Upcoming; the Edit filter already chooses leagues for every page. A league opened from the Leagues page still filters to that league and the subtitle names it ("NBA · 1 game coming up · …"). test_sports_upcoming updated.
- **Page 2, option A withdrawn (owner):** the League capsule is removed again; the Leagues page already opens a league's games, so Upcoming has no picker (state of caebe63).

## ISSUE-386 — Sports Edit sheet rebuilt to the mockups; golf, UFC and F1 added (owner request, 2026-11-19)

- **Owner:** the Edit filter must look like mockups B1/B2 "and actually work", and "include app data" for the sports the mockup shows.
- **Data (`sports_espn.py`):** PGA Tour, LPGA Tour (golf), UFC (combat sports) and Formula 1 (motorsport) from ESPN's public scoreboards. A tournament or race weekend is one game with just its title (`sm.versus` returns it alone; a golf tournament in progress is live and its round is the clock); a UFC card is its main event's two fighters. Golf joins `sm.SPORT_ORDER`. The game page draws only the first side when there is no opponent. Boxing has no ESPN feed (owner: does not matter), so it is not listed.
- **Sheet (`sports_edit_page.py`, `sports_edit.py`, `sports_filter.sheet_items`):** one scrolling sheet instead of the two-step choice sheet: "Leagues" with a white Done capsule, the help line, All on / All off, then each sport with "Only" and a row per league (real logo, name, next game, green switch). Every tap is saved at once and the page behind redraws when the sheet closes. The old two-step specs are removed.
- **Not built:** the third chip "Only what I picked · N" from the mockup (it is a status, not an action; the Edit pill already says "Edit · N").
- **Tests:** test_sports_filter (sheet items, properties, actions, sheet XML, the new leagues' parsing); sample data gained a PGA league, so the sample league count is 13 in three tests.
- **Desktop Kodi rig (sample data):** sheet, "Only" on Hockey (the file and the hub behind it follow). Live golf, UFC and F1 data checked against ESPN with a script. Not seen on a phone yet.

## ISSUE-387 — Sports game page rebuilt to the owner's mockup (page 6) (2026-11-19)

- **Owner:** page 6 of the eight mockups: "Remind me if there are no sources, and then game info", plus (later the same day) "remove the Only button, it should only be simple switches".
- **Game page (`sports_game_page.py`, `sports_game.py`):** each team's colour glows behind it; big crests (a ring with the code when there is none), the short name ("Colts") and the record under it; the time in the middle with "Today · in 2 h 10 min"; the league's code above. A narrower centred capsule: Remind me / Reminder on / Play. Under Remind me: "No source yet. We'll tell you when one is ready." (the reminder's own line once it is on). **Sources** is a card: "None yet · Checked 2 minutes ago · Check now" (Check now looks for sources again, for upcoming and live games), or the source rows. **Game info** is a card ("NFL · Week 11 / Today at 5:15 PM") that opens the facts page.
- **Facts page (`sports_game_facts_page.py`, `sports_game_facts.py`):** the Info section that used to sit under the sources moved here unchanged (kickoff, venue, recent form, standings with the Divisional / Wild Card switch). Page 8 of the mockups (tabs, compact hero) is next.
- **Data:** ESPN's team colour, short name and the week number are kept on each game; `sm.until_text`; sample teams RS and AC carry colours so the glow can be seen in the rig.
- **Edit sheet:** the per-sport "Only" links are removed (plain switches only), All on / All off stay.
- **Tests:** test_sports_game (+5, Hero), test_sports_game_info (facts window), test_sports_filter (colour, short name, week).
- **Desktop Kodi rig (sample data):** page 6 and the facts page opened from the Game info card. Not seen on a phone yet.
- **Page 6 / 8 follow-up (owner: "page 6 needs help", "the info page should look like the photo, not whatever you provided"):** the Info page is now the mockup's (board D1/D2): the same hero and action capsule as the game page, an Info | Standings switch, Kickoff / Venue / Recent form, or the table with the Divisional / Wild Card switch; a game with no table has no tabs. The hero is one shared module (`sports_hero.py`). Game page cleanup: richer team glows (ESPN's dark colours are lightened), "We'll tell you" and "Best source:" are bold white inside the grey line, the live game shows "● LIVE", the score and the clock (mockup C5), "Other sources (n)" jumps to the list, and the "Choose a source to play." line and the Sources count are gone. Standings headings are the table's own name ("AFC South"). Tests: test_sports_game (live, lighten, other sources), test_sports_game_info (tabs, page content).
- **Page 6 wording and logos (owner):** no bold "We'll tell you": the note under Remind me is plain, "No source yet. Tap Remind me for a notification when one is ready.", and once a reminder is on it says "Reminders are set for this game." Real team logos, not circles: crests are downloaded once from ESPN's image host and kept on the phone (`sports_logos.crest` / `crests`, ESPN host and PNG only, 400 KB cap, never beside the code), for the hero and for every standings row; the ring with the team code now shows only while a crest is not there yet. The sample teams carry real ESPN crest addresses so the rig shows logos. Tests: test_sports_logos (Crests), test_sports_game (crests, note wording).

## ISSUE-388 — Sports reminder sheet to the owner's mockup (page 7) (2026-11-19)

- **Owner:** "lets do the remind sheet".
- **Done (`sports_remind_page.py`, `sports_remind.py`):** its own bottom sheet over the dimmed game page instead of the app's choice sheet: grabber, "Remind me about Colts at Texans", "A notification on this phone. It opens this game.", a card with the two green switches ("When a source is ready · Then Play appears here", "15 minutes before it starts · Today at 5:00 PM"), a wide white "Turn on reminder" capsule with the bell and a blue "Cancel". With a reminder already on it shows the same switches (each flip is saved at once), a white "Done" and a red "Turn reminder off". The save / cancel / turn-off rules are unchanged (`ask()` and its tests).
- **Tests:** test_sports_reminders (SheetWindow: wording, which tap answers what, the XML).
- **Desktop Kodi rig (sample data):** both versions, and Turn on reminder → "Reminder on" → reopened as Done / Turn reminder off. Not seen on a phone yet.

## ISSUE-389 — Sports: scores, clocks and times were not live (owner, 2026-11-19)

- **Owner:** "we need to ensure times and scores are live, directly from ESPN, and update on the second; I remember times were not syncing or updating regularly."
- **Root causes (read in the code):** on the phone the games come from the Crew provider and ESPN only overlays live scores: asked at most every 45 s and trusted for 90 s (`sports_jet._with_scores`); the game page drew every 30 s and asked for data every 30 s; the game clock text ("Q3 · 4:12") only changed when a new answer arrived; the hub never refreshed itself; and a start time uses Python's idea of the time zone, which can be UTC inside an iOS app.
- **Fix:**
  - Scores are asked for at most every 8 s while a page polls and trusted for 40 s (`SCORE_EVERY`, `SCORE_STALE`).
  - ESPN's countdown clock seconds are kept on each live game (`clock_secs`, `clock_mark`) and `sports_jet.annotate_clocks` stamps when they were read and whether the clock is running (it moved since the last answer, or ESPN says in progress; a timeout or end of period stops it). `sports_model.live_clock` counts it down second by second between answers, never more than 90 s without a fresh one; soccer and baseball keep ESPN's own text.
  - The game page redraws every second (only changed values are written) and asks for fresh scores every 5 s while the game is live (30 s otherwise); Live Now ticks every card's clock every second; the hub refreshes itself every 15 s.
  - `sports_model.device_offset` takes the phone's time zone from Kodi's own clock (`System.Time`) when asked about now, falling back to Python's table, so a Python that believes it is UTC no longer shifts every game.
- **Tests:** test_sports_game (live clock, ticking page), test_sports_filter (clock seconds from ESPN), test_sports_jet (clock stamps, cadence), test_sports_model (Kodi clock), test_sports_scores updated.
- **Limit, stated plainly:** ESPN's scoreboard changes every few seconds, not every second, so a score appears within about 5-10 s of ESPN having it; the clock itself moves every second. The sample data in the desktop rig counts a basketball clock down for real (4:03 → 3:55 over 8 s); a running clock on a real ESPN game was not seen because the only live game at the time was at half time. Not checked on a phone.

## ISSUE-390 — Home / Movies / TV header icons: no circle, one size, a light ring (owner, 2026-11-19)

- **Owner:** "a clear background behind the settings and refresh button, make the settings icon cleaner and the refresh button a bit bigger so all of the icons are the same size; the bell can stay as it has the ring" and, after seeing it, "make the settings look like this (the 6-tooth gear), maybe a light ring around them, Apple glass style, so they know where to tap".
- **Done (`portrait.py`: `header_button`, `refresh_button`, `bell`, `bare_glyph`, `hdr_ring`):** the filled glass circles behind settings and refresh are gone. All three icons come from the skin's one solid family: the 6-tooth `gear.png` (replacing the chunky 8-tooth drawn gear), `arrow-rotate-right.png` (replacing the thin drawn arc; it still spins while the rows load and ticks when done) and the bell, each shown at the same size (`HDR_BOX`, 40 units visible). Each has a hairline ring (white at about 40 %, no fill, `hdr_ring.png`) and a faint shadow copy under the glyph so it stays readable over artwork. The bell shows the ring only while idle (its progress ring takes over while something runs). Hit targets stay 118 units (44 pt). Settings, Movies and TV share the same helpers, so they follow.
- **Policy note:** APPLE-UI-POLICY §5.5 says to match the existing glyph size; the ring and the 40-unit glyphs are the owner's call (Kodi cannot blur, so the faint shadow is what keeps a bare glyph legible on bright artwork).
- **Tests:** test_header_icons (new, registered). `test_header_buttons.py` is not in import-review.yml and four of its tests (list URLs, row hashes, favourites route) already failed before this change; its one header assertion was updated.
- **Desktop Kodi rig:** Home before and after. Not seen on a phone yet.

## ISSUE-391 — Sports on the phone: wrong AM/PM, no UFC/F1/golf, sources not found, Crew overlapping the lists (owner screenshots, 2026-11-20)

- **Owner:** game times read "4:00 AM" where they should be PM; only basketball, soccer and football showed (no UFC, F1 or golf); opening a game said "Can't search for sources right now"; Crew ran behind the lists and overlapped the loader.
- **Times (root cause, found in `sports_model.kodi_offset`):** Kodi's clock text on a 12-hour phone ("04:00:00 PM") did not parse, so the offset fell back to Python's zone, which is UTC inside the iOS app, and every game showed in UTC. `parse_clock` now reads 24-hour and 12-hour text. Tests: `test_sports_model` (KodiClock: 12-hour text, New York and India cases).
- **Leagues and scores (root cause):** the phone's provider was JetExtractors, which only lists what Crew's add-ons carry, and it started Crew's collector each time a list loaded. Now `sports_hybrid.HybridProvider` takes every game, league and score from ESPN (lists refresh every 8 s, so scores and clocks are live), and Crew is asked only for one game's sources.
- **Sources:** `request_game` runs `sports_provider.crew_sources(game)` on a thread and matches Crew's games by league, start and team names (`sports_merge.same_game`). Opening a game (from Upcoming, the hub or Live Now) now searches on open. A search that Crew cannot answer shows "Can't search for sources right now" with Try again; one that finds nothing shows "None yet".
- **Tests:** test_sports_hybrid (new, registered): lists from ESPN including UFC, no Crew start on a list, sources only for a page that asks, failure vs "none yet", the one-game match, the eight-second refresh. test_sports_loop and test_sports_game updated to the new provider and the open-on-search call.
- **Not verified:** Crew's sources on a real phone (the owner's device); the rig runs sample data only. Whether Crew finds the streams for a given ESPN game is what the next phone check decides.

## ISSUE-392 — Live Now rebuilt as option B (owner picked B, 2026-11-20): big cards, real logos, no league tabs

- **Owner:** "I would like B now, code it all and ensure it matches with the rig and logos instead of circles of letters"; then "clean that up and remove the tabs at top".
- **Done (`sports_live_page.py`, `sports_live.py`):** each live game is one big card: the league and the clock on top, both crests (230 units, in a light circle) with the names under them, and the score in the middle with a red LIVE above it. A tap anywhere on the card opens the game page (where Play is). Source rows and "Find sources" buttons are gone from this page. Team crests are downloaded once and kept on the phone (`sports_live.with_crests`, through `sports_logos.crests`); a team with no crest shows an empty ring, never letters. The league chip row (All, NBA, NFL…) is removed.
- **Fixes found in the rig:** a score that wrapped into "88 – …" (the centre column is now wider); a team name that broke mid-word (names use the smaller font).
- **Tests:** test_sports_live (24, updated to the card model; the crest tests use temporary folders).
- **Desktop Kodi rig (sample data):** the card layout with real NBA crests; empty rings for teams without a crest. Not seen on a phone yet.

## ISSUE-393 — "THE CREW" menu showing behind Sports (owner screenshots, 2026-11-20)

- **Owner:** the Crew's own menu ("THE CREW: Movies, TV Shows, Sports…") and its "The Crew Is Finding Your Event…" dialog appeared behind and in front of our pages when a game opened. "No more Crew UI, only the code needed to play the film."
- **Root cause (found in the code):** the Sports hub opened Crew's own Kodi window under itself every time it was entered (`sports_crew_context.Context.open`: `ActivateWindow(Videos, plugin://plugin.video.thecrew/)`), so that Crew's menus could be listed while Crew supplied the games. Since DEC-065 ESPN supplies the games, so nothing needs that window.
- **Fix:** the hub no longer creates or opens a Crew context (`sports.py`); test_sports_landing (NoCrewWindow) pins it. The source search runs Crew's collector as a standalone caller (no session), which already works without the window.
- **Not fixed, on purpose:** the "The Crew Is Finding Your Event…" progress dialog is Crew's own, shown by its resolver while it opens a stream (a Play). DEC-062 keeps playback inside Crew's resolver (no importing its protected code, no altering its authorization), and an earlier note in `sports_crew_routes.py` warns against hiding Crew's dialogs during a playback handoff. Closing it risks cancelling the resolve. Whether it can be covered safely needs a phone log of a Play on the new build.
- **Not verified:** on a phone (no Crew add-on in the rig).
- **ISSUE-393 follow-up (2026-11-20):** read the pinned Crew (plugin.video.thecrew 3.2.2, script.module.thecrew 3.2.29, hashes match `migration/provider-fallback/source-lock.json`; unpacked outside Git, read only). Findings: Crew's own resolve overlay (`ResolveStatusOverlay`, "Finding your stream…") is a WindowXMLDialog whose cancel flag is set only by its own cancel/back handlers, so closing it from outside would not by itself cancel a resolve; but the "THE CREW SPORTS / The Crew Is Finding Your Event…" dialog in the owner's screenshot is not in these pinned versions (the phone's Crew is probably newer), so its window id is unknown and nothing is hidden yet. Crew's Blue Hat menu has UFC, F1 and PGA sections: the app now scans them too (`sports_crew_routes.ACTIONS`); UFC fights can match by fighter names, F1 and golf (title-only events) will not match a source yet.
- **ISSUE-393, from the owner's build-600 log (2026-11-20):** the phone's Crew is plugin 3.2.2 / module 3.2.29, the pinned version. One game opened scanned every Crew sports menu in turn (NFL 17 s, NBA 4 s, NCAAB 2.6 s; "0 matched streams" for NHL), then Crew's own "choose a stream" dialog (`DialogSelect`) appeared and was tapped; "addons must not activate DialogBusy" is logged for Crew's listing. Stream resolving itself ("Streamer embedsports … .m3u8") runs in the Loop / JetExtractors add-ons, which DEC-062 says not to import. **Fix now:** a game page's search reads only that game's league menu in Crew (`KodiIOS.SportsCrewOnlyLeague`, set by `sports_provider.crew_sources`, read by `sports_crew_routes.discover`) instead of every menu; Crew's UFC, F1 and PGA menus are mapped to those leagues. **Still open:** Crew's own pop-ups during a Play (the stream chooser, the busy and resolve dialogs); the log is from build 600, before the hybrid provider, so it is not yet known which of them the current build still shows.
- **ISSUE-393, Crew's link chooser (2026-11-20):** during a Play, Crew's own "choose a link" dialog (`selectdialog`) was left for the person to tap (the router only stopped counting its time against the timeout). The router now answers it with the first, best entry through Kodi's own select action, once per appearance, after 0.4 s for the list to build (`sports_loop_router.play`, `auto_pick=True`); no Crew code is called. The dialog may still flash for an instant; a skin-level hide needs the owner's next log. Test: `test_sports_loop_router` (a chooser is answered once). Not verified on a phone.

### ISSUE-394: game page still showed 5:00 AM for a 5:00 PM game, and Crew found no source (build 608 phone log)

- **Evidence:** owner screenshot and kodi.log of build 608. The Game info row said "Today at 5:00 AM"; no Play button because Sources said "None yet"; the log shows Crew walked 23 NHL folders and 24 "Full live sites" folders and matched 0 streams in about 110 s each.
- **Root cause (time):** a 12-hour phone's `System.Time(hh:mm:ss)` is "06:15:30" with no AM/PM marker, so `kodi_offset` read the evening as morning and every time was 12 hours off.
- **Fix:** `kodi_offset` also asks `System.Time(xx)` for the marker when the text has none. Test: `test_sports_model` KodiClock (marker-less 12-hour phone).
- **Not fixed, still open:** why Crew's menus gave no match (not provable from this log; the scan is slow and found nothing). `CrewSource` now logs how many event-looking titles matched no live game (a count, never the names) so the next log shows whether titles were seen at all.
- **Retest:** host tests only; needs the owner's phone.

### ISSUE-395: a game's Crew source search read once and gave up; it also walked every site menu (build 608 phone log)

- **Evidence:** build 608 logs. The search finished within seconds as "None yet" while Crew's collector kept walking for about 110 s and its late results were never read; the walk covered the league menu and the 24-folder all-sites menu.
- **Root cause:** `crew_sources` called `jet.refresh()` once, which returns as soon as the collector has published the ESPN schedule, and matched against that snapshot.
- **Fix:** `crew_sources` keeps reading what the collector publishes until the game matches with a source, the collector finishes, or 150 s pass (one fresh pass if the answer predates the request). A game's search no longer reads the all-sites menu (owner: only that league's folders). A game whose sources are already known is not searched again.
- **Retest:** host tests only (`test_sports_hybrid` SourceSearchKeepsReading, `test_sports_crew_routes`); the phone is the proof. Not built or merged.

### ISSUE-396: Crew's event lists came back empty once Crew's window was no longer opened under Sports (build 608)

- **Evidence:** build 608 log: the league menu and the all-sites menu listed their folders (23 and 24 walked, 0 unavailable) but matched 0 streams. ISSUE-369 recorded that outside Crew's own window the real provider folders returned no results. Crew's NBA menu file (a third-party XML fetched at run time) starts its event list with `if not Container.PluginName == 'plugin.video.thecrew': return`.
- **Cause:** commit 5577b03 stopped opening Crew's window under Sports (owner: no Crew UI), so that check failed and every event list was empty. Team-name matching was not at fault.
- **Fix (owner chose option A, 2026-11-20):** `sports_crew_patch` changes one line of the pinned `script.module.thecrew` 3.2.29 `control.py` so `Container.PluginName` reads as Crew only while the Home property `KodiIOS.SportsCrewScan` is set (set by a game's source search, cleared when the last search ends). Any other version, or a file that does not match, is left alone and logged ("crew: scan patch left alone").
- **Retest:** host tests only (`test_sports_crew_patch`: patch once, idempotent, label reads as Crew only during a scan, other version/file untouched). I could not run Crew's downloaded menus in the desktop rig (they need network from Kodi's Python). The phone is the proof: look for "crew: scan patch applied" and a non-zero match count.

### ISSUE-397: Crew's "THE CREW SPORTS / The Crew Is Finding Your Event…" box on every Sports play (build 608)

- **Where it comes from:** not the Crew add-on. Each league's menu file, downloaded at run time from github.com/posadka/xmls2 (`sports/<league>/<league>.xml`, the `makelist2` link resolver), builds an `xbmcgui.DialogProgress` ("Loading Your Event" → "Finding Your Event…" → "Playing Your Event!"), and waits a fixed 2 s after "Playing". Crew's own `control.py` also creates a progress box and a background progress bar at import. The link chooser is the separate `_select` in the downloaded `crewstreamer.xml` (auto-answered since ISSUE-393).
- **Fix:** the same pinned-line patch as ISSUE-396 (`sports_crew_patch`) now also swaps `xbmcgui.DialogProgress` and `DialogProgressBG` for a silent stand-in, but only while the Home property `KodiIOS.SportsCrewScan` holds a time in the future. A game's source search and a Sports play (`sports_loop_router.play`) set it; being a time, it can never stay on after a crash. Crew used from its own menus is unchanged.
- **Not removed:** the 2 s wait inside Crew's downloaded code, and Crew's small "X failed, using Y" notification when a link fails over.
- **Retest:** host tests (`test_sports_crew_patch`). On the phone, a Play should show no Crew box; the log shows "crew: scan patch applied".

### ISSUE-398: sources found quickly in build 611 but the stream was stopped as soon as Crew opened it (owner phone log, build 611)

- **Seen:** build 611 log. "crew: scan patch applied"; NBA matched 6 streams in 14 s (ISSUE-396/395 worked). Playing one: Crew's chooser appeared and the owner had to tap it; Kodi then opened Crew's resolved stream (H.264/AAC codecs opened), and 0.2 s later "sports: native opening ended without a confirmed error; queue cancelled" and `CVideoPlayer::CloseFile()` stopped it.
- **Cause (two):** (1) `player.play(playlist)` does not return until Crew has resolved the link, and the chooser appears during that wait, so the chooser-answering loop had not started. (2) Crew plays its resolved stream itself, so the playlist no longer holds the queued item (position -1) while that stream is still opening; the router's "ended" check was only held off by Crew's progress box (`progressdialog`), which ISSUE-397 made silent.
- **Fix:** a watcher thread answers the chooser while `play()` is blocked (state shared with the loop, one answer per appearance); an opening is not "ended" while the observer has seen playback start or `Player.HasMedia` is true.
- **Test:** `test_sports_loop_router`: chooser answered while play is blocked; Crew playing its own stream is not an ended opening (fails without the fix). Host only; the phone is the proof (look for "picked the first link" before the stream opens and "playing (native addon queue)").

### ISSUE-399: Sports said "Nothing live right now, next game tomorrow" while today's games were still to come (owner, 2026-11-20, 7:24 AM Pacific)

- **Seen:** owner screenshots: our Sports page showed no games today and the first "Up next" game "Tomorrow at 10:00 AM"; Apple Sports showed that day's NBA games (4:00 PM, 4:30 PM, 5:00 PM ... local) under Today.
- **Cause:** the lists ask ESPN for the plain scoreboard and tomorrow's date only. ESPN's plain scoreboard is its own idea of "today" and it lags: at 15:25 UTC (10:25 ET) it still answered the finished 2026-11-19 slate (checked live from the build container: `day.date` 2026-11-19, every game `post`), and nothing asked for the 20th itself.
- **Fix:** each league is also asked for today's date, in the feed's own days (US Eastern: `now - 5 h`), so the plain scoreboard, today and tomorrow are merged by event id (three requests a league instead of two). Tests: `test_sports_espn` (today's games show when the plain scoreboard answers yesterday; the feed's day is the Eastern day). Host tests plus one live fetch of the feed from the build container; not seen on the phone.

### ISSUE-400: a downloaded show's season page had no season row, so another season meant backing out (owner, build 615, 2026-11-20)

- **Seen:** tapping a season on a downloaded (library) show opened that season's episodes with the page scrolled down to them; scrolling up showed no season selector. The log has `GetDirectory - Error getting plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=` (empty id) when the page opened.
- **Cause:** ISSUE-334 drew a season row on an episodes page only for TMDb Helper shows (their folder path, their `tvshow.tmdb_id`). A library show's episodes carry neither, so the row's list was empty and hidden.
- **Fix:** the library plugin puts `KodiIOS.SeasonsPath` (the show's own season list) on every episode of a season page; the show page draws a second season list (id 47) from it, highlighting the season shown; a tap goes up to the show then into the other season, as the TMDb row does. Test `test_show_season_row`; checked in the desktop Kodi rig with a fake three-season show (the row appears and highlights Season 2). **Not changed:** a tap on a season on the show page still opens that season as its own page (a view container's click cannot be stopped by a skin, ISSUE-334); on the phone the page may still open scrolled to the episodes. Phone check pending.

### ISSUE-401: the Subtitles menu listed several English tracks, UND and broken ones (owner, build 615, 2026-11-20)

- **Seen:** the menu showed Off, English, English SDH, UND; "none of them work". Owner: one English only, the CC version; Spanish is Spanish.
- **Fix:** `track_menu.pick`: one row per language (a viewer-added track first, then CC/SDH, then a full track before a forced one), UND dropped when any stream names its language, tracks the matcher found broken (empty, out of sync, wrong episode) dropped, other languages kept; CC is the tag. Tests in `test_track_menu` / `test_subtitle_hold`. **Not found:** why the embedded tracks show nothing on the phone. The log shows the track switching on ("English subtitles on", libass track created) and nothing else, and the phone's player gives no cue data for embedded tracks, so they cannot be checked in the menu. Needs a log taken with English CC on during dialogue and a note of what the screen shows (nothing, wrong text, or out of sync).

### ISSUE-402: a Drive show took 3-4 s to show its first picture and every seek landed 0.6-3.5 s later, then stuttered (owner, build 615 log, 2026-11-20)

- **Seen:** Naruto S2: click at 10:55:50.9, streams ready 51.98, first picture ~55.3; 7 sequential Drive range reads of 0.26-0.72 s each between. Seeks: "landed after 604 ms ... 3488 ms", "first decoded picture queued 1401-1977 ms after video flush", then "Slower while a video plays". Perf line: `drive proxy 68 requests, 1 warm, seeks 68 (median 0.4 s, worst 0.9 s)`. These videos play from Drive through the app's proxy (`Drive copy opened through the app proxy`), not from the phone.
- **Cause (from the log):** every Kodi request is a new Drive request with 0.26-0.72 s to the first byte; the proxy read ahead only 4 MB and kept nothing, so a seek back, a re-read, or a request inside what was just played still paid a full Drive round trip, and after a seek Kodi's buffer starved.
- **Fix (memory only):** `drive_proxy.Blocks` keeps the last 96 MB of movie in whole 1 MB blocks, filled as pieces stream; a ranged request that starts in cached blocks is answered at once and only the missing tail goes to Drive; the read-ahead behind a request is 24 MB (was 4). The proxy logs `Kodi iOS Drive range: start=N cached=M` for every request, so the next log shows which offsets Kodi asks for. Tests in `test_drive_proxy` (exact bytes, tail-only Drive request, eviction, size change, aligned tee). **Not fixed and not provable here:** a seek to a place not yet played still costs the Drive first-byte time (about 0.3-0.7 s) plus the key frame, so a seek cannot be instant while the video streams from Drive. Keeping played parts on the phone's disk would make revisits instant but conflicts with the Drive index rule (no movie payload on disk): needs the owner's decision.

- **Update (same day, owner decision: "instant seeking for downloaded stuff", "clean up when i exit the show or movie"):** `drive_cache.py`. While a Drive video plays, the proxy keeps its 1 MB blocks as files in `special://temp/drive-playback-cache` (3 GB cap, oldest deleted first) and a background filler fetches the rest of the file from the playing position (then the part before it) so seeks inside it need no Drive request. Wi-Fi only (never on cellular; an unknown link counts as allowed), only when the phone has the cache's size plus 2 GB free, whole file when it fits the cap, otherwise a window ahead of the position. The folder is wiped on `Player.OnStop`, at every proxy start (a crash leaves nothing) and may be cleared by iOS. Tests: `test_drive_cache` (disk round trip, cap, size change, wipe, filler fills the file and every seek is served with zero Drive requests, cellular and no-space fetch nothing, big files get a window, a seek moves the filler). The Drive index design's "no movie payload on disk" rule is lifted for this cache only. Not proven on the phone: real speed, how long a full episode takes to fill, whether iOS counts `special://temp` toward Documents & Data (it is emptied on stop, so only while playing).

### ISSUE-403: sports sources never populated for a game that had been on 25 minutes (owner, build 615 log, 2026-11-20)

- **Seen:** the owner tapped check on a live game 25 minutes in: nothing. The log: every game-page search ends in under a second with `jet: ESPN schedule ready in 0.8s (0 live, 118 upcoming)`, `jet: 0 scrapers (Crew routes)`, `jet: 0 Crew source routes discovered`. At that moment ESPN had two live games, Bundesliga KOE @ MUN (kicked off 19:30 UTC) and Ligue 1 HAC @ TRY (19:45 UTC), checked live from the build container.
- **Cause:** `sports_crew_routes.schedule()` asked ESPN only for American leagues (NFL, NBA, WNBA, MLB, NHL, NCAAF, NCAAB, MLS), so a live soccer match was never "live" for Crew and `discover` returned no routes without asking Crew anything. Separately, Crew's menu map knew its soccer menu (`fifa`) only as MLS, and a single-game search never read the all-sites menu, so a league with no menu of its own (LPGA) could not be searched either. Nothing looked for sources until check was tapped.
- **Fix:** the schedule covers every league (just the game's own league during a game search, which is faster); Crew's soccer menu serves every soccer league; the all-sites menu is read for a game whose league has no Crew menu of its own; the log names the leagues that were live. New `sports_sources_prefetch` service loop: every 60 s, when no video is playing and no game page is searching, it searches the soonest live game that has no source (one at a time, retried after 3 minutes while it is live), so a live game's page opens with its sources listed. Tests: `test_sports_crew_routes` (soccer leagues and LPGA), `test_sports_sources_prefetch`.
- **Not proven:** Crew's real answer (the private add-ons are not in the build container). The same log shows `[JetExtractors] Import failed ... cannot import name 'config' from 'jetextractors'` for every Loop scraper and `SportsX refresh failed`: the Loop's own scrapers cannot load (separate from this; the owner will deal with the Loop later). Look in the next log for `prefetch: BUN espn:...: N source(s) ready`.

### ISSUE-404: wasted background work, no first-picture time, no pre-loading of the next video (owner asked for "so fast you never think about it", 2026-11-20)

- **Seen in the build 615 logs:** the Loop's `Analytics poll: playback detected but no session synced yet` 56 times in 7 minutes and its scrapers failing to import (`cannot import name 'config'`) and retrying; the service asking Elementum for its list every 20 s and failing every time (`Elementum list unavailable`, a diagnostic record each time); `GetDirectory - Error getting plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=` (empty id) on every season page and `Error getting &stamp=` (the player panel's Continue Watching list with no path) on every panel open; show pages loaded 2-3 times per open; opens logged as "1.3 s" while the tap to first picture took about 4.4 s.
- **Fixed:** `loop_quiet` switches the Loop add-on off while the new setting "Pause The Loop's background work" is on (default; switching the setting off enables it again, but only if this app disabled it; checked at start and every 15 minutes). The Elementum poll backs off 20, 40, 80 ... 300 s while it does not answer and logs once, then every tenth failure. `open_timing.check_moving` logs `first picture (playback clock moving) N s after the tap` for every open, so the next log shows where the time goes. Next-video prefetch: the proxy's `/prefetch/<file id>` keeps a video's first 24 MB and last 4 MB on the phone (Wi-Fi only, with room, pinned for an hour and kept past the stop of the video that is playing); asked for the play target and the episode after it when a show or season page opens, for the movie most likely to be resumed, and for the first two Continue Watching items. Tests: `test_loop_quiet`, `test_open_timing`, `test_drive_cache` (prefetch, pins, endpoint), `test_prefetch_copy`.
- **Not changed (and why):** the empty-id TMDb season call and the empty `&stamp=` list: each is one fast failed call per page or panel open, and the real fix restructures the show page / player panel XML, which is not worth the risk without the phone. Show pages still load 2-3 times (the pinned season row and the embedded list read the same cached listing, 0.03-0.5 s). Elementum's torrent engine still starts with the app (it is needed for downloads). Not proven on the phone: that prefetch makes the next episode start faster, and that pausing the Loop leaves nothing else broken.

### ISSUE-405: a loading circle covered the Home screen and blocked every tap; sources slow; hero flashed white (owner, build 616 log, 2026-11-20)

- **Seen:** on opening the app a spinner stayed over Home and nothing could be scrolled or tapped. The log: `Click at ... in DialogBusy.xml (1080 x 2090 layout): control 0 (not handled)` six times between 12:32:54 and 12:34:51, and `Activate of window '11103' refused because there are active modal dialogs` at 12:32:49 (the Sports tile tap). The game page also flashed white and then went white.
- **Cause (circle):** my own background source search from build 616. `sports_sources_prefetch` began 30 s after launch, while the owner was on Home, and walked Crew's menus (dozens of listings, `Crew refresh folder completed ... 143 entries`). Crew raises a modal `busydialognocancel` for each dynamic list. `sports_crew_routes.listing` only closed it when a game page's search session was valid, which a background search never has, so the dialog stayed up over whatever screen was showing. Reproduced in `test_sports_crew_routes` (a listing with no session leaves the dialog up before the fix). Separate: the Loop imported 45 failing scrapers 10 s after launch (the pause came 30 s after start).
- **Cause (slow sources):** the same walk: Crew's own scrapers hit dead sites on every search (`Schedule [daddylive] / [fsportshd] / [streameast_ga] error ... Max retries exceeded`, three to four times in two minutes), the soccer menu had 680 titles to match, and the first source came 17 s after the search began, the fifth after 59 s. The busy dialog then covered each wait.
- **Cause (white):** the hero glow is a white texture tinted with the team's ESPN colour at 72 % opacity. Cologne's colour is `ffffff`, so its glow was white; two light teams wash the whole hero out.
- **Fixed:** (1) the busy dialog is closed within 50 ms for every Crew listing, session or not (both `busydialognocancel` and `busydialog`); (2) a watchdog (`busy_watchdog`) closes any busy dialog that stays up 4 s with no video opening or playing; (3) the prefetch search waits until a Sports page has been opened this session (for 3 hours after), instead of starting at launch; (4) the Loop pause runs 2 s after the service starts, not 30 s; (5) a glow colour is lightened less and never brighter than luminance 0.62, and a near-white colour gets the soft grey; (6) the same file is no longer prefetched twice a moment apart (a show page loads two or three times). Tests: `test_sports_crew_routes`, `test_busy_watchdog`, `test_sports_game` (white and light colours), `test_drive_cache`.
- **Found, not fixed:** pressing Play on Crew 720 failed: `Streamer [generic] failed | https://sportsframe.me/soccer/fc-bayern-munich-stream-1 | module 'resources.lib.modules.client' has no attribute 'parseDOM'`, then Kodi was handed the unresolved `$doregex[makelist2]` address and could not open it. That is a defect inside Crew's own resolver (private add-on code, version 3.2.29), so that source cannot play whatever we do; the other four may. Next step if wanted: after a source fails, try the next one automatically.

### ISSUE-406: subtitle "Download and apply" spun for a minute and applied nothing visible; CC shown as on but no subtitles (owner, build 616 log d35b8625, 2026-11-20)

- **Seen:** tapping Download and apply showed nothing happening; the owner left the menu. The Lanterns file said CC was on but no subtitles drew.
- **Cause (slow):** search took 0.6 s (SubDL found 13) but `download_and_apply` then ran the speech check *before* applying: two 45 s samples of about 48 MB each read over Drive took 58 s, heard 7 and 2 words (too few to judge) and the subtitle was applied at 12:40:04, after the owner had left at 12:39:29.
- **Fixed:** the chosen subtitle is applied at once; the speech check now runs in the background (`check_by_speech`), and only swaps to a better-timed one or shifts timing with a notification if it hears a clear mismatch. Speech budget cut (STRETCH 45 to 30 s, BYTE_BUDGET 48 to 24 MB).
- **Not determined:** why the embedded "CC" track drew nothing. The log shows English on and a libass track created, with no cue evidence. Added diagnostics: a `streams:` line (index, language, name, forced/SDH, which is on) and `file subtitle tracks:` (track fourccs from the MP4 moov, `mp4_tracks.py`). Hypotheses: a codec Kodi cannot draw (wvtt/stpp/c608) or empty cues.
- **Retest:** host tests `test_subtitle_hold`, `test_track_menu`, `test_mp4_tracks`, `test_speech_check`. Not proven on the phone; needs the next log with the two new lines.

### ISSUE-407: tapping a sports source could open a dead link and stop there (owner, build 616 log 551591c4, 2026-11-20)

- **Seen:** tapping "Crew 720" for Cologne v Bayern: `Streamer [generic] failed ... module 'resources.lib.modules.client' has no attribute 'parseDOM'`, then Kodi tried to open `$doregex[makelist2]` twice (`CVideoPlayer::OpenInputStream - error opening`), Crew showed a dialog and nothing played. The owner: "there should be something checking what is actually playing video, then what has the best stats ... and provide that stream, not some dead link".
- **Cause:** a tap on one source went through `play_one`, which calls `xbmc.Player().play(route)` and returns `True` at once: no check that a picture ever appeared and no other source tried. Only the automatic Play button used the queue (`sports_loop_router.play`), and even that counted a stream as playing after 0.1 s of clock movement, so a link that opened and froze passed. Crew lists no size or bitrate for its sources, so nothing ranked them.
- **Fixed:** (1) a tap now builds a queue (`tapped_source`): the tapped source first, then the game's other sources; (2) `sports_stream_health.Watch` judges what is really playing: the picture must move at about real time for 5 s, a clock frozen for 6 s or crawling below 60 % of real time is "not usable" and the next source opens by itself; a source that shows no picture in 40 s is dropped (while others remain); (3) `Health` remembers per source name (labels and numbers only, `sports-source-health.json`) what worked, what failed in the last half hour and how sharp it was (height, fps, bitrate when the stream states one), and orders the queue by it; the tapped source still leads unless it failed recently and has not worked since. Log lines: `sports: stream check: Crew 720 is playing (720p 30 fps)`, `... is not usable (the picture froze ...)`, `sports: source order from what worked before: ...`.
- **Not fixable here:** Crew's own `generic` streamer error (`parseDOM` missing in Crew's `client` module) is inside the private add-on. The queue now moves past it, but that source stays dead.
- **Retest:** `scripts/test_sports_stream_health.py` (Watch, Health, a scripted Kodi with good, frozen, dead and silent sources) and `test_sports_loop_router.py`. Not proven on the phone: needs a live game.

### ISSUE-408: two empty-path requests on every player open and on downloaded shows (build 615 log 5e731e8a)

- **Seen:** `GetDirectory - Error getting &stamp=` six times (each time the player opened) and `GetDirectory - Error getting plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=` once on a downloaded show.
- **Cause:** the player panel's Continue Watching list read its path from a skin string that is empty until the button is tapped, with the stamp appended (`&stamp=`); the TMDb Helper season row asked for a show with no id.
- **Fixed:** both paths are now skin variables that are empty when their input is empty (`Portrait_Osd_Continue`, `Portrait_Season_Chips_Path`), so Kodi makes no request. Tests: `test_review_low_items.py`, `test_portrait.py`.
- **Checked, not a bug:** the "tv page" log line twice about 0.1 s apart is the show page and its season row, two folders by design (about 0.1 s each).

### ISSUE-409: a downloaded subtitle could not be turned back on; the menu closed and nothing showed (owner, build 617 log e7aaa913, 2026-11-20)

- **Seen:** Download and apply worked. Turning subtitles off and picking English again closed the menu and nothing drew. The new log lines explained it: `streams: #0 eng; #1 eng sdh; #2 und; #3 eng "4168484231 (External)" | on #1` right after the download was applied, and `file subtitle tracks: #3 eng tx3g; #4 eng tx3g; #5 und tx3g`.
- **Cause:** the downloaded track is stream #3, but the menu object that downloaded it was the only thing that knew (`self.added` is per open), so the next open saw an ordinary English track. `pick` then preferred the embedded CC (#1) for the English row, and the menu's automatic chooser switched Kodi to #1 the moment it opened, turning the download off. Choosing English afterwards selected the embedded CC again, which is the "CC on but nothing shows" track (its tx3g text is empty or unreadable).
- **Fixed:** (1) every stream Kodi names `<file> (External)` counts as the viewer's own (downloaded, removable) whatever menu learned of it, so it wins its language; (2) opening the menu never swaps a downloaded track for an embedded one; (3) removing a download is remembered for the video (`KodiIOS.SubsRemoved`) and its file is found again from Kodi's name; (4) the file's own subtitle tracks are now counted (`stsz` in `mp4_tracks`, `... N samples` in the log) and an embedded track holding 0 or 1 subtitle is refused as empty, so the menu stops offering a track that cannot show anything. Tests: `test_subtitle_hold` (reopen keeps the download on, off-and-on selects the download, empty embedded track hidden; each fails on the old code).
- **Not proven on the phone.** Still unknown: whether the Lanterns embedded tracks really are empty; the next log shows the sample counts.

### ISSUE-410: seeking still lagged, and scrubbing back and forth froze (owner, build 617 log e7aaa913, 2026-11-20)

- **Seen:** seeks landed after 0.65 to 1.0 s and the first picture came 0.5 to 1.9 s after the flush; every Drive request of a seek was cold (`cached=0`) and each took 250 to 400 ms (`headers_ms` minimum 238, median 351, 502 requests).
- **Cause (found in the log, partly inferred):** this MP4 keeps its video, audio and subtitle tracks in separate stretches of the file (a seek to 52 % read near 1.78 GB, 268 MB and 357 MB; a seek to 24 % read near 790 MB, 88 MB and 265 MB), so Kodi reads two or three places at once. The playback cache's filler followed ONE position, set by whichever request arrived last, and its stale-fetch rule dropped the fetch (and the Drive connection, so the next request paid a new handshake) whenever that position moved more than 32 blocks. With reads alternating between stretches it kept abandoning its own fetches and filled little.
- **Fixed:** the filler follows up to four positions (`Filler._follow`, `CURSORS`), reads near each other (64 blocks) count as one stretch, the stretches are filled in turn, and a fetch is abandoned only when no followed position is near where it began. Tests in `test_drive_cache.py` (two stretches both followed; alternating reads still fill everything).
- **Limit:** the first request into any new stretch after a far seek is still cold (about 0.3 s each, one per track), so a long jump will still take a moment; the change should remove the freezes when scrubbing back and forth and make playback after a seek fill faster. Not proven on the phone.

### ISSUE-411: leaving a show shows the Home screen turning and squeezed (owner, IMG_0522, 2026-11-20) - fixed in native r34, pinned; device check pending

- **Seen:** on exit from a video the Home screen is drawn turned (about 45 degrees) and squashed for a moment before settling upright. Home does stay loaded behind the player (Kodi keeps the window stack), which is why it returns at once; the odd frame is the screen turning.
- **Cause:** the log shows the app turning the screen itself (`Video orientation: portrait`, then `Screen rotated: 1206 x 2622` about 0.5 s later). During that animation Kodi's picture is still the old size and iOS turns and squeezes it with the view.
- **Proposed fix (not applied):** in `viewWillTransitionToSize` of the portrait patch, add a black cover view above the GL view without animation and remove it 0.3 s after `applyRotatedScreen`, so nothing turning is visible. A trial copy applied cleanly to Kodi 21.3 (`git apply --check`). It is NOT in the patch because the lock (`source-lock.json`, `test_smooth_pages`) ties the patch hash to the built executable (r33); changing it needs a new native Kodi build (hours) and a new pinned release. Do that build together with any other native change.

- **Fix (2026-11-21, owner approved the native build):** portrait patch for r34. At the start of every turn `viewWillTransitionToSize` puts a black view over the whole window (above Kodi and the glass tab bar). It fades out (0.15 s) once Kodi has rebuilt its framebuffer and laid out its windows for the new size: at the end of `ApplyRotatedScreen`, after one more frame. If that does not happen, it is removed 0.6 s after the turn ends (owner: Home must show within 1 s of leaving a video), so it can never stay. A newer turn keeps its own cover. Owner's wish ("no pages showing while a film is playing"): Home stays loaded behind the player on purpose, so leaving a video is instant. What showed was the squeezed frame during the turn, and the cover hides it.
- **Patch check:** the new patch applies to pristine Kodi 21.3 (a3a448d), and the tree it produces is byte-identical to the edited source. Only the `XBMCController.mm` section changed. `source-lock.json`: `build_tag` r34 and the new `patch_sha256`; `executable_release` stays r33 until r34 is built and checked.
- **Retest:** `test_smooth_pages.py` (cover in the patch; lock names r34 and this patch). Not compiled here (no Xcode): the workflow's build is the first compile. Not proven on the phone.
- **Built and pinned (2026-11-21):** run 44845188966 (commit 70b81ed, 48 min) published `kodi-ios-portrait-r34`. Downloaded: zip sha256 5fff7ae8…8970, executable 8f2ad9fd…45bf (arm64 Mach-O), both match the release. `executable_release` is r34 now, r33 previous (`test_glassbar.py`).
### ISSUE-412: Sports Upcoming, Leagues and Favourites flick choppily; Home, Movies and TV are fluid (owner, build 617, log b06951ce, 2026-11-20) - partly fixed, needs the phone

- **Seen:** the owner's swipe test of the Sports hub, Upcoming and Favourites. The log holds only taps (no scroll data), so the frame rate could not be read from it.
- **Why Home is different (ISSUE-316, confirmed):** Home, Movies and TV are rows that are `list` containers, which draw and process only the items on screen. Every other page is one long group list of hand-placed slots. The touch flick and its momentum are the same code for both; the frame cost is not. The portrait patch r33 (in build 617) already skips group-list children more than a screen away; it does not remove the cost of the slots near the screen or of evaluating the rest.
- **Measured in the desktop rig (stock Kodi, software GL, so only the ratios mean anything), System.FPS while dragging, fresh start:** Home 148; Upcoming with 6 games on the old 120-slot window 75; the new 30-slot window 101. Later pairs in the same run were noisier (74 vs 69, 71) because the rig slows as it runs, but the short window was never slower. Sizes of the generated windows: Leagues 17,167 controls (80 slots x 16 text-height forms), Upcoming 4,461, Favourites 1,424, Notifications 1,422, Sports hub 377.
- **Not the cause (tested, rejected):** nesting the slots in blocks of eight inside group lists (one condition per empty block): layout identical but slower (53 fps vs 64), nested group lists cost more than they save. Not shipped.
- **Changed:** (1) Upcoming now has a short window (30 rows, 407 KB) and a long one (120 rows, 1.18 MB) with the same control ids; the page opens the one that fits the games it remembers and reopens into the long one only when a list is longer than 30 (`window_for`, `Upcoming` in `sports_upcoming.py`); (2) Leagues has 36 slots instead of 80 (ESPN lists 18 leagues), which halves its 17,000 controls; (3) `scroll_probe.py` logs, once a minute and when the window changes, `Kodi iOS scroll: window N 'Name': X fps typical, Y fps slowest tenth, N samples while touched` while a finger is on the screen, for every window, so the next phone log ranks all pages with real numbers.
- **Not done (the real fix):** pages whose rows are all one height (the Favourites poster grid, and any list with a fixed row height) can become native `panel`/`list` containers like Home, which process only what is on screen. Rows of different heights (Upcoming's day headings, Notifications) cannot: Kodi list items share one size, so those pages stay group lists and can only be made smaller. The Favourites conversion is a page rewrite that needs its own mockup check and the phone; it waits for the next scroll log.
- **Retest:** `test_sports_upcoming.py` (window sizes, ids, projection), `test_scroll_probe.py`. Rig screenshot of the short window matches the long one. Not proven on the phone.

### ISSUE-413: an Umbrella stream took 22 s from tap to first picture (owner, build 617, log f6a2f92e, 2026-11-20)

- **Timeline (tap 14:14:07 to first picture 14:14:31, about 24 s):** TMDb Helper setup 2 s (item details, library check) | Umbrella search 3 s (41 sources) | resolving the chosen link 2 s | the app's cache wait 5.0 s (`route=direct ... blocks=0/3 bytes=1048576`: the debrid server had delivered 1 MB in 5 s, so the cache gave up and Kodi opened the link directly) | Kodi's open 7.5 s (2 s to connect, 5 s reading the start of the file at about 0.2 MB/s) | first picture 3.5 s (decoder start and the first frames).
- **Cause:** the chosen source's debrid server needed 5 s or more before its first byte (the file's size was not even known to the cache at 1.5 s, so the early-exit rule of ISSUE-340 could not apply) and then delivered slowly. Two older logs (218a6000, one more) show the same: `route=direct` after the full 5 s. Nothing in the app speeds one server up. The cache wait is kept: Kodi's own open after it connected in 2 s where the cache's request had needed 5 s or more, so the wait appears to have warmed the server.
- **Fixed (not proven on the phone):** (1) `source_speed.py` remembers, per debrid service and provider (labels only, `umbrella-source-speed.json`), how long each opened source took from the choice to the streams being ready, and which never opened; the version page now lists the sources of a quality fastest first (a recent failure last, unknown sources unpenalised, a cached one ahead of an unchecked one, ties in Umbrella's own order). The choice is recorded when the viewer picks (`umbrella_picker.run`), credited when `open_timing` sees the streams ready or gives up (`open_timing.LISTENERS`), and logged as `Kodi iOS Umbrella source alldebrid|torrentio: opened in 13.1 s ...`. (2) The `stream opening` log line now ends `origin_answered=yes|no`, so the next log says at once whether the server had even answered.
- **Not done:** skipping TMDb Helper's 2 s setup by starting Umbrella directly (it needs the metadata Umbrella expects; not testable without the add-on here); trying a second source in parallel while the first warms (needs Umbrella's own resolver, which this app does not own).
- **Home loaded during playback:** checked in the desktop rig: Kodi neither draws nor processes Home while a video plays; over 25 s of playback and 20 s idle there were 0 widget refreshes. Only its memory stays, which is why Back is instant. Unloading it would save almost nothing and slow the return. Left as it is.
- **Tests:** `test_source_speed.py` (ranking, failure fade, persistence, the picker lists a fast source first, open_timing credits the source), `test_stream_loop.py`.

### ISSUE-414: build 618 log 067121ef: subtitles not found, Sports sources slow to appear, black Sports pages, spinner over the opening card, white line, Umbrella continue 15 s (owner, 2026-11-20)

- **Subtitles "unable to find any":** a Drive episode played through the fast path searched as `'Trust Fall' None SNoneENone` (Kodi's own item lacked show, season and episode), so SubDL returned 0. Fixed: the add-on that starts a Drive video now leaves what it knows (`KodiIOS.Playing`: title, show, season, episode, year, the show's TMDb id) and the search uses it when Kodi's item lacks them and the title agrees; the show's TMDb id is now sent for episodes too. Also found: my 617 empty-track rule read "0 samples" for every embedded track of a fragmented MP4 (the samples live in moof boxes), which would have hidden every embedded track; `mp4_tracks` now reports no count for a fragmented file (`mvex`). Tests: `test_subtitle_hold.py` (the search uses the add-on's knowledge, ignores a different video), `test_mp4_tracks.py`.
- **Sports sources appeared a minute after tapping a live game (owner screenshot "Searching for sources"):** the service's prefetch found the sources, but each Kodi script has its own provider, so the game page saw nothing and searched again. Fixed: found sources are shared through a Home window property (`KodiIOS.SportsFound`, 30 minutes, 12 games; `HybridProvider._publish` / `_adopt`), and opening any Sports page now pokes the prefetch so it looks at once instead of at the next minute (`sports_sources_prefetch.watch(poke=)`). Tests: `test_sports_hybrid.py`, `test_sports_sources_prefetch.py`.
- **Black Sports pages for a second or more:** every page waited for ESPN (0.7 to 2 s, under one lock). ESPN's last answer is now kept on the phone (`sports-snapshot.json`, 6 hours) and offered at once after a restart while the real answer loads in the background; each page redraws when it arrives (`sports_fresh.py`). Tests: `test_sports_fresh.py`.
- **White line down the left edge of Leagues and Upcoming:** a 1 px white image used as spacing under the list (colour 00000000) drew bright while the page loaded; it is now an empty group.
- **White spinner over the "Opening your game" text:** Crew's own busy dialog; the opening card now closes busy dialogs every 0.2 s while it is up (it is the loader).
- **Umbrella continue still 15 s:** tap to first picture was TMDb Helper 2.2 s, Umbrella 1.2 s (cached), choosing 1.4 s, the cache wait 2.0 s (the early-exit from ISSUE-413 worked), Kodi's open 7.2 s (the debrid server again: 2 s to connect, 5 s reading the start of the file), first picture 3.2 s. The same source (`alldebrid|torrentio`) took 11 s both times. Fixed for Continue of an episode that was already being watched: the link it was playing (a remote link, never the phone's own proxy) is remembered for Umbrella titles and, within 4 hours, Continue resumes from it directly when it still answers a one-byte read, skipping TMDb Helper and Umbrella (`ios_watch_dialog.fast_stream`, `ios_library.play_stream`, `ios_continue.update(stream=)`); otherwise the normal way runs. A next episode still needs Umbrella: it is a different file. Tests: `test_fast_stream.py`.
- **Sports Play tap to picture (about 16 s):** 3 s waiting for the background search to finish its current Crew folder, 2.8 s re-listing Crew's folders, 8.4 s for Crew's own resolver to scrape the stream site, 1 s to open. Only the first two are ours and both are needed by Crew; not changed. A picture cannot be instant before Crew has resolved the link.
- **Seeking (build 618):** landing 0.7 to 1.3 s, first picture 0.4 to 2.3 s after the flush, similar to build 617. After a seek Kodi makes about 8 sequential cold reads inside a 60 MB window, 0.3 s each, because this Drive copy is a fragmented MP4 (`opening MP4 by its fragment index`): the demuxer reads many fragment headers. Not fixed: that needs either a native pre-warm while the slider is dragged (the seek is only submitted on release) or non-fragmented, interleaved output from the app's own conversions. Recorded as the next step.
- **Scroll fps lines:** none appeared in this log although the probe was running: the idle or the frame-rate reading failed. The probe now logs once what it read (`Kodi iOS scroll probe: ...`) so the next log shows which.

### ISSUE-415: Crew's generic streamer failed with "no attribute 'parseDOM'"; Favourites scroll cost (2026-11-21, after build 619)

- **Crew:** Crew 3.2.29's `client.py` defines `parseDom` but not `parseDOM`, which its own downloaded streamers (generic, rapidmoviez) call; build 616's log: `Streamer [generic] failed | ... has no attribute 'parseDOM'`. `sports_crew_patch.apply_client` adds `parseDOM = parseDom` once (pinned version and exact anchor line checked, as for the scan patch); `ensure()` and the service at start run it, so Movies and TV Crew sources benefit too. Verified against the pinned module on this machine (`test_sports_crew_patch.py`). Not proven on the phone.
- **Favourites:** each poster cell carried a conditional focus zoom; in the desktop rig (30 favourites) removing it gave 107 fps against 73-81 in one run and 94 against 92 in a clean pair after a restart (the rig slows as it runs, so only the direction is reliable). Masks, badges and the placeholder were also tried: small gains, not taken (they change what is drawn). Layout unchanged; only the 4 % press zoom is gone. Not proven on the phone.
- **Not changed:** speeding up Crew's own site scraping (timeouts, dead sites) lives in code Crew downloads at run time, which this app cannot see or safely patch.

### ISSUE-416: Sports data still took a second; a failed source stopped instead of trying the next (owner, build 619, log b8b9d448, 2026-11-21)

- **Sports data:** ESPN's games, scores and times are now fetched by the service from 4 s after launch and kept on the phone (`sports_data_loop`: every 10 s while a game is live and Sports was opened in the last 15 minutes, 30 s otherwise, 60 s to 6 hours after, 300 s after that; three times slower on cellular; never while a video plays). Every Sports page takes that answer at once: an answer under 45 s old is used as it is, a page's own refresh is skipped when the file is under 10 s old, and a newer file replaces a page's older answer without a request (`EspnProvider._adopt_newer_disk`). A page therefore only waits for ESPN when the service has not run yet (the first open after installing). The manual refresh button is removed from the hub, Live Now, Upcoming, Leagues and the game page (the Edit capsule moved to the right edge). Crew stays what it was: sources only, for the game whose page is open. Tests: `test_sports_fresh.py`, `test_sports_landing.py`, `test_sports_live.py`.
- **Failed source:** the log shows Crew's streamers failing (`Streamer [embedsports] failed ... SSLError`), Crew handing Kodi an unresolved `$doregex[makelist2]` link, Kodi's open failing, and only a Stop ("current media") reporting it; the router read that as a cancel and stopped, and Kodi's Yes/No "playback failed" box asked the person to check the log. Now (1) a Stop after the media started but before any picture, with the queue still the person's (a real cancel clears ownership first), is a failed source and the next choice opens by itself; (2) Kodi's OK and Yes/No failure boxes are closed; (3) when Crew's link chooser was answered for a route that then fails, the same route is retried with the chooser's next link (up to three links), by moving down before selecting. Not changed: a game with a single source and a single link has nothing to fall back to, and what Crew's own fallback does. Tests: `test_sports_loop_router.py`, `test_sports_stream_health.py`.


### ISSUE-417: the scroll probe logged no frame rates on the phone (owner, build 619, log d366ccf2, 2026-11-21)

- **Seen:** only `Kodi iOS scroll probe: idle (touch reading False, System.FPS '3.12')`, no `Kodi iOS scroll:` lines, after swiping Upcoming, Leagues, Favourites and Notifications.
- **Cause:** the probe sampled only while `System.IdleTime(1)` was false, and on the phone Kodi's idle timer never saw the touches. The frame-rate reading itself works: an idle page reads about 3 fps because Kodi draws only when something changes.
- **Fix:** a sample counts when a touch is seen **or** the rate is at least 15 fps (`scroll_probe.ANIMATING`), so scrolling and page animations are measured without a touch reading; video stays excluded. Lines now say "samples while moving", and the first such reading logs whether it came from a touch or from animation.
- **Retest:** `test_scroll_probe.py` (idle 3 fps ignored, animation without touch counted, slow touched scroll counted). Not proven on the phone: the next log should hold `Kodi iOS scroll:` lines for each swiped page.

### ISSUE-418: Next Episode did nothing on a downloaded (Elementum) show (owner, 2026-11-21; build 619 log bb2b3e35)

- **Seen:** while a downloaded episode played, tapping Next Episode (16:16:19 and 16:16:23) started `next_episode` twice; each ended after 0.03 s and logged nothing.
- **Cause:** `plan()` needs Kodi's item to carry the show, season and episode. The Library's player sets them only when its row knew them, so for these copies `plan()` returned "not an episode", and that path wrote no log line.
- **Fix:** the Library's player adds the copy's Library path and the address Kodi plays to its `KodiIOS.Playing` record. When the video playing is that download, Next Episode lists the show's downloaded episodes in the Library's own order (the show page with `merge=1`, so phone and Drive copies together, season by season), finds the playing copy and plays the one after it, across a season boundary. It needs no TMDb or Umbrella; after the last one it says "That was the last downloaded episode." If the copy is not in the list, the old TMDb Helper way runs, and a "not an episode" result is now logged with what Kodi's item held.
- **Umbrella:** Next Episode already hands the previous episode's quality and size to the version page, which picks the same one by itself (ISSUE-331, `deck_picker.next_wanted`).
- **Retest:** `test_next_episode.py` (`DownloadedShow`: recognised by the played address or the Library link, next in order, season boundary, last one, fallback). Not proven on the phone.

### ISSUE-419: every Sports page sat on "Checking…" / "Updating" (owner, build 620, log 02bd6dd7 and screenshots IMG_0536/0538/0539, 2026-11-21)

- **Seen:** the hub's tiles said "Checking what is on / Checking games / Checking leagues"; Live Now and Leagues were blank under "Updating". The only ESPN lines are from Crew's collector script, and the service's loop left no trace in the log.
- **Cause:** every Sports page asks the provider to refresh when it opens. `EspnProvider.refresh` skipped the network only when the saved answer was under 10 s old, but the service saves one every 10–30 s, so most opens downloaded ESPN again (about 30 leagues, two requests each) while the page showed "Checking…". The quick first draw (`sports_fresh.remembered`) ran only for answers over 45 s old, so between 10 and 45 s nothing was drawn first.
- **Fix:** a page's refresh (`refresh(block=False)`) never waits when an answer is saved. Under 10 s old it is used as it is. Under 10 minutes it is drawn at once and the newer one is fetched in the background (one at a time); the pages re-read every second or two and pick it up. Only with nothing saved, or something older, does a page wait, and that wait is now logged ("a page waited N s for ESPN"). The service's loop uses `refresh(block=True)` and always fetches, and it logs its first saved answer ("background refresh: ESPN saved in N s").
- **Retest:** `test_sports_fresh.py` (a page with a 40 s old answer returns in under 0.5 s and gets the newer one in the background; it waits only with nothing saved), `test_sports_espn.py`, `test_sports_hybrid.py`. Not proven on the phone: the next log should show the service's "ESPN saved" line and no "a page waited" lines after it.

- **Regression in build 621 (owner log 0ee2c2eb: "sports doesn't work at all"):** opened 0.4 s after launch on a very slow network (a Drive request took 15 s; YouTube could not get a network address), with the saved answer from 3 hours earlier. The change above made a page wait for ESPN whenever the saved answer was over 10 minutes old, where the older code had drawn it at once as "remembered", so every page stayed empty. **Fix:** a page draws any saved answer up to 6 hours old at once (`SNAPSHOT_KEEP`): under 10 minutes as current, older as remembered ("Updated at …"); the fresh one replaces it when ESPN answers. A page waits only when nothing is saved. Checked with the real provider and the hub's own `load()`: a 3-hour-old answer with ESPN not answering fills the hub in 0.44 s with "Updated at 1:50 AM". `test_sports_fresh.py` (`test_an_old_saved_answer_is_drawn_as_remembered_never_a_blank_page`).
### ISSUE-420: about 3 s of a Sports tap was ours, reopening Crew's menus one after the other (bug 1, owner 2026-11-21; build 619 log bb2b3e35 16:10:06)

- **Seen (timeline):** tap 06.67; queue opened 07.37; Crew's sports root reopened (1.03 s), then the game's folder (1.91 s), to 10.32; Crew's chooser up 11.92, picked 12.54 (we wait 0.4 s); Crew's resolver until 15.94 (its embedsports host failed: Crew's side). Build 620 logs (02bd6dd7, 8ba13ecd) hold no Sports play tap.
- **Cause:** `refresh_link` reopens the whole menu chain, root first, because opening another league clears Crew's link rules (`$doregex`). The root listing only re-finds the game's folder, whose address the link already holds, and the two listings run one after the other.
- **Fix:** a link found in the last 10 minutes (the prefetch's) opens its game folder directly, which rebuilds Crew's rules for the items in it, when that address is a plain route (no `$doregex` from its parent). If the game's link is not uniquely there, the whole chain is reopened as before; older links (folder addresses can expire) always reopen it. Links now carry when they were found (`at`). Crew's chooser is answered after 0.2 s instead of 0.4 s. Expected: about 1.2 s less per tap. Crew's own chooser build (about 1.6 s) and resolver (3–4 s) stay.
- **Retest:** `test_sports_crew_routes.py` (recent link: one listing; folder lost: whole chain; parent-rule folder never opened alone; old link: whole chain as before). Not proven on the phone: the next log should show one "Crew refresh folder" line per tap.

### ISSUE-421: Umbrella Continue took 12.3 s to the first picture (step 2, owner, build 620 log 80ea6c76, 2026-11-21)

- **Seen (18:00:57, on cellular):** "continued episode from its last Umbrella link (Umbrella skipped)" at once; then Kodi took 2.8 s to connect to the debrid server, 5.1 s to read the file's start (3 MB probe), and 3.6 s from streams ready to the first picture (the seek to the resume point).
- **Cause:** Umbrella's own path hands Kodi the service's cache (`umbrella_recovery` calls `remote_media.for_kodi`: several connections, the file's start and end asked for at once). The Continue fast path (`ios_watch_dialog.fast_stream`) skips Umbrella and with it that hand-off, so Kodi read the debrid link itself over one connection (about 0.6 MB/s), three times cold.
- **Fix:** Continue now goes through `remote_media.for_kodi` too, and passes the resume point (position ÷ length). The cache fetches the block where playback resumes and its two neighbours (`RESUME_BLOCKS`) together with the opening blocks, so the resume seek reads from memory. When the cache does not answer within its usual limit (5 s), the link itself plays, as before. The remembered link stays the real one (the phone's own address is never stored).
- **Retest:** `test_fast_stream.py` (Continue uses the cache with the resume share; without it the link plays; `resume_blocks`), `test_stream_race.py` (`Resume`: an open with resume 0.5 fetches the opening, last and middle blocks through the real cache; a bad value is ignored). Not proven on the phone: the next log should show "Kodi iOS opening: cache" for a Continue tap and a shorter "first picture" time.

### ISSUE-422: the jump to where a Drive copy was left took 3.5 s (step 3, owner 2026-11-21; build 619 log bb2b3e35)

- **What the logs show:** Kodi's own seeks in the app's Drive copies are mostly quick now (53–383 ms after ISSUE-410); the slow ones are the first seek after opening, to the resume point: 3.46 s for a Drive copy (16:15:23), 3.29 s for an Umbrella Continue (build 620, step 2 / ISSUE-421), plus one of 1.07 s. Every read of that jump is cold (about 0.3 s each).
- **Corrected diagnosis:** the long walk through every fragment from byte 0 at 16:16:14 (88 MB, 143 MB … 2.2 GB, cold reads 0.25–0.37 s) was not a Kodi seek. It is the app's speech check (`speech_check.listen`, the subtitle-timing check), which listens at 30 % and 60 % through the AirPlay framework; it read alongside playback for 14 s and 32 s. Kodi's demuxer does use the copy's index: FFmpeg 6.0.1 reads `mfra` at the first `moof` when `use_mfra_for` is set (our patch sets it since r24) and marks the fragment list complete, so its seeks jump straight to a fragment. A native change to the copies' layout is therefore not needed for Kodi's seeking.
- **Fix:** when a Drive copy opens with a resume point (Library, Continue, Next Episode), the app's proxy prefetches what Kodi reads first, from the copy's own cached index (`drive_index.resume_plan`): the header of the fragment holding that point and of the one before, then 6 MB around the point inside that fragment (time and bytes go together within one fragment), ahead of the copy's start and end (`Filler.prefetch(first=)`, `/prefetch/<id>?at=`). Kodi's jump then reads from the phone.
- **Limits:** needs the copy's index already cached (it is after the first play; 64 copies kept), and follows the cache's own rule (Wi-Fi only, room on the phone). The speech check's walk is left for later: it now has its own line here.
- **Retest:** `test_drive_index.py` (`ResumeOffsets`: the video track's fragments not a sparse track's, the fragment and the point inside it, bad values, the proxy request reaching the filler), `test_drive_cache.py` (resume blocks fetched first, then start and end). Not proven on the phone: the next log should show the first "Kodi iOS seek" after a resumed Drive copy well under a second.

### ISSUE-423: Sports pages scroll at about half the frame rate of Home; the probe named the wrong page (owner, build 621, log 5b1f4222, 2026-11-21)

- **Seen (first real numbers, ISSUE-417's probe):** Sports pages 21–34 fps typical, 17–25 fps for the slowest tenth (one Live stretch 55/36); Favourites/Sports 41/20; Home 60/60 (build 620 log 80ea6c76). Every line said "window 11103" with a stray label ("Video only", "- Delay").
- **Probe cause:** the Sports pages are dialogs over window 11103; the probe keyed by `getCurrentWindowId()` and named by `System.CurrentWindow`. **Fix:** `scroll_probe.page` keys by the top dialog when one is open and names it by its skin file (`Window(id).Property(xmlfile)`), e.g. `IOSSportsUpcoming`. `test_scroll_probe.py`.
- **Scroll cost (cause, from the page code):** Upcoming and Live are group lists of up to 120 rows, each row a nested group list of labels, crests and a focus fade, so Kodi processes every control of every row each frame. Home, Movies and TV use native list containers, which lay out only the visible rows. **Not changed yet:** turning these pages into list containers keeps their look but needs one row height (the day headers are the question); waiting for the owner's choice.
- **Fixed (2026-11-21, owner: "keep the current UI and have it scroll smoothly"):** the day-header mockup was declined; the UI stays as it is. Measured instead of guessed: in the desktop Kodi rig (Upcoming with 120 games, wheel-scrolling, Kodi's GUI profiler over 200 frames) the page's own controls drew in about 0.64 ms per frame and their conditions cost nothing measurable, but the window *under* the page (Kodi draws it every frame although the opaque dialog covers it) took 60 % of all drawing time. Now opaque full-screen pages list themselves in `KodiIOS.Covered` while open (`page_cover.covering()` around `doModal()`: Sports hub, Live, Upcoming, Leagues, Game, Favourites, Notifications), and the windows that can be under them (Home, the hubs, the Library hub, Search; `portrait.covered`) keep their controls in one group that hides while that list is not empty **and** a modal dialog is open (`portrait.COVERED_CONDITION`). Opt-in, not every window: a first version wrapped every non-dialog window, and `test_portrait` caught the context menu (a dialog whose skin file does not say so) being wrapped too, which would have hidden it over a Sports page. A page that dies cannot leave a window blank: the condition needs a modal dialog, `covering()` uncovers in `finally`, and the service clears a leftover list every 2 s when no modal dialog is open. Rig, same scroll, window under hidden vs drawn: Upcoming 65 → 118–133 fps (CPU 2.70 → 2.36 s/s; 106–115 with the opt-in version while another test ran), Favourites 78 → 159, Notifications 84 → 169; page screenshots unchanged; Home back at once on close (flag cleared). `test_page_cover.py`. Not proven on the phone: the next swipe log should show these pages' `Kodi iOS scroll:` lines (now named by page) near 60 fps.

### ISSUE-424: build 622 test (owner, log ac85bba1, 2026-11-21): Sports still waits a little; flicks do nothing; Continue failed once; Next Episode does nothing; Lanterns captions do not show

- **Sports waits (fixed in code):** the hub opened 4 s after launch (08:24:43); the service's first ESPN answer came at 08:24:55, and the last saved one was from the night before, over the 6-hour limit, so the page waited. A saved answer is now drawn for 48 h (as "Updated at …" when old), and the service fetches 0.5 s after it starts instead of 4 s. `test_sports_fresh.py` (`test_last_nights_answer_is_still_drawn`).
- **Continue failed (step 2 undone):** with the cache route, the cache had 1 of 3 opening blocks after about 2 s (judged hopeless: `route=direct wait_ms=2010 blocks=1/3 pending=9 requests=40`), handed Kodi the link with reads still running, and the debrid server refused Kodi's range request ("Requested range was not delivered by the server"): "could not open file". Continue plays the remembered link directly again, as in build 620. The cache's early fall-back leaving reads running is a cause to fix before routing anything else through it. `test_fast_stream.py`.
- **Next Episode (fixed in code):** "not an episode (item: type 'unknown', show False, S-1 E-1)": the copy opened by Continue plays inside TMDb Helper, so Kodi's item is TMDb Helper's link and did not match the copy the Library recorded. The player's own file (`getPlayingFile()`) is checked too. `test_next_episode.py`.
- **Flicks do nothing (cause found by reading Kodi's source, fix written as native r35; see ISSUE-425):** a flick on a Python dialog page was refused by the window *under* the page, not by the page. The per-gesture log (`gesture_note`) stays as the phone evidence. `test_gesture_note.py`.
- **Captions (open, evidence still missing; diagnostics extended 2026-11-21):** tracks `#0 eng; #1 eng sdh; #2 und | on #1`; the file's subtitle tracks are three tx3g (Apple text) tracks; "on" but nothing drawn; Kodi opens the stream each time ("Creating new ASS track"). The log ac85bba1 holds no cue counts, so the three causes cannot be told apart yet. Checked without the log: (a) the writer's options (`+empty_moov+default_base_moof+frag_keyframe`, `min_frag_duration`/`frag_duration` from the bitrate, `frag_size`, `frag_interleave 12`) given to a muxer with three text tracks (synthetic 260 s video, 40/40/5 cues; system FFmpeg 6.1, not our remuxer build) wrote cues into 24-26 of 26 fragments for each track (8.9 s and 17 s fragments), with the cue gaps filled by empty samples, so a generic layout bug in the options is not it; (b) `kr_prepare.c` converts any decoded text subtitle to `mov_text` with the cue's start and the packet duration, and picture subtitles go beside the MP4 (or are refused), so an empty or short track can only come from the source's own tracks (for example captions held inside the video stream, which are no subtitle stream at all); (c) the tx3g tracks open in Kodi (stream opened, ASS track made), so the container side is readable. **New in the log (`mp4_tracks.fragment_spans`, `track_timescales`):** next to "N fragments hold it" each track now says `fragments from A s to B s`, with the picture's own span (`| video fragments from 0 s to T s`). How to read the next log: N <= 1 -> the converted track is empty (cause 1: conversion or source; the menu hides it and offers Download and apply); N normal and A..B inside 0..T -> cues exist and Kodi cannot draw them (cause 2/3: then read `Kodi says subtitles enabled=... current #...`: enabled false -> Kodi's state; true -> drawing: overlay position or 4K path, needs a log with the player's subtitle lines); A..B far outside 0..T -> timestamps (cause 2). `test_mp4_tracks.py`. Nothing here is proven on the phone.
- **Scroll numbers:** Sports pages 16–43 fps typical, Favourites 25–41, Home 28–61 in this log (the probe now names pages); the ISSUE-423 change is not proven to help on the phone.

### ISSUE-425: flicks do nothing on the Sports pages and Favourites: the window under the modal page overwrites its inertia answer (owner, build 622, log ac85bba1; found 2026-11-21 by reading Kodi 21.3)

- **Seen:** dragging scrolls Sports (hub, Live, Upcoming, Leagues, Game) and Favourites smoothly; a flick does nothing once the finger lifts. Home, Movies and TV glide. In build 617 the same pages' flicks "moved, choppily"; in build 622 (ISSUE-423 added) they do nothing.
- **Path read, step by step (Kodi 21.3-Omega a3a448d, our patch applied):** the pan handler sends BEGIN, PAN (with pixel velocity) and END; `CInertialScrollingHandler::CheckForInertialScrolling` keeps pan points of the last 200 ms and on END (speed above 200 x dpi scale) sends `GUI_MSG_GESTURE_NOTIFY` with sender id 0 through `CGUIWindowManager::SendMessage`; the answer must come back as an `int*` in `message.GetPointer()` equal to `EVENT_RESULT_PAN_VERTICAL`. Checked and fine for these pages: the vertical group list has an id (`LIST`, e.g. `sports_upcoming_page.py`), BEGIN reaches it (the chip rows are horizontal and hand a vertical drag up, r20), so `m_exclusiveMouseControl` is its id and our patch answers PAN_VERTICAL; the Python dialog's `OnAction` runs Kodi's own handling first, then Python, so nothing in the page code swallows PAN; the group list returns HANDLED to each PAN.
- **Cause:** `SendMessage` hands the message to the topmost modal dialog (the page: PAN_VERTICAL), then to every modeless dialog, then **also to the window under** the dialog because the sender id is 0. `CGUIWindow::OnMessage(GUI_MSG_GESTURE_NOTIFY)` stores its own answer with `message.SetPointer(new int(result))` every time, so the last window asked wins. The window under has no exclusive control, reads the flick's speed (px/s) as a screen position, and finds nothing there: it answers UNHANDLED and overwrites the page's PAN_VERTICAL. Kodi then sees no inertia and the page stops dead. Stock Kodi has the same flaw for any dialog over a window. It explains both builds: before ISSUE-423 the window under had its controls visible, so a flick's speed read as a position sometimes landed on one of its lists (they answer PAN_VERTICAL for any NOTIFY), so flicks sometimes glided; with ISSUE-423 (`page_cover` hides the window's controls while a page is open) nothing can be hit and it never glides. So ISSUE-423 is a trigger, not the cause: removing it would bring back luck, not a fix, and it costs the frame rate it bought (65 -> 118-133 fps in the rig). Not changed.
- **Fix (native, patch revision r35, `kodi-21.3-portrait.patch`, `CGUIWindow::OnMessage`):** an answer already stored that is not UNHANDLED stays (the window asked later returns at once, without its pointless `UnfocusFromPoint` on a speed-as-position); an UNHANDLED one is replaced and freed (stock leaked it). The patch applies to pristine 21.3-Omega (`git apply --check` on a fresh clone, checked). `source-lock.json`: `build_tag` r35, new `patch_sha256`; `executable_release` stays r34 until r35 is built and its digests are checked, so **the IPA built from this branch still carries r34 and flicks stay dead until the owner asks for the r35 build** (workflow `kodi-ios-portrait.yml`, about 50 minutes). No Python or skin change is possible: the window under has no point that always answers.
- **Retest:** host `test_smooth_pages.py` (the r35 hunk: accepted answer kept, replaced one freed, returned before the window's own mouse handling; lock names r35 and this patch's digest). Not proven: only the owner's phone shows a glide. After the r35 build, the log's `Kodi iOS gesture:` lines (ISSUE-424) should read `glided on` for a flick and `stopped at once` for a slow drag; no such line shows momentum starting.

### ISSUE-426: the Sports hub is still not instant after a force-quit (owner, build 623, log 8c570737, 2026-11-21)

- **Seen:** build 623 (branch airplay-sports-combined, native still r34): Sports opened 4 s after launch (09:39:46.6); the service's first ESPN answer was saved at 09:39:50.7 (ESPN itself took 1.4 s); a first Sports tap right after launch drew the "Updating / Checking games" tiles, then the games. The owner: the page "needs to be instant like every other page ... it shouldn't need to load", and ESPN should refresh when the app opens.
- **Cause (from the code and the log):** (1) the ESPN loop thread started at the end of the service's set-up and then waited 0.5 s and imported its modules, so its first answer came about 4 s after launch; (2) the page opened on `props_updating()` placeholders and drew the saved answer from a worker thread afterwards, so the first frame was never the real hub; (3) every refresh drew "Updating" and "Checking games" over games already on screen.
- **Fix (host tests only):** the loop is the first thing the service starts, loads the hub's modules (so a page opened at once finds them), and asks ESPN with no wait; the page sets its properties from the saved answer before `doModal()` (`sports.draw_first`, using the new `has_answer()`, which only looks at memory and the file, never at ESPN) so the first frame holds the games; with nothing saved it still shows the placeholders (it never blocks on ESPN); a refresh no longer covers drawn games with "Updating" (Retry still says it is trying). The log says `Kodi iOS Sports: hub: first frame from the saved answer (N ms)` or `waits for ESPN`, to read the real time on the phone. `test_sports_instant.py`.
- **Not fixed:** a launch with no saved answer at all (first ever run, or over 48 h) still waits for ESPN's first answer. Not proven on the phone: the next log's "hub: first frame" line and the owner's eye on a force-quit then Sports test.


- **Log f5848994 (2026-11-21, still build 623, so the old code; a baseline):** first tap on Sports 2 s after launch (10:03:14.35) -> the page script ran at 16.25, 1.9 s later, right after the service's own imports ended (`bootstrap entered (imports 2.059s)` at 15.86; 0.08 s on a computer); the ESPN loop did not start until the service's whole set-up was done (`startup: complete` 19.05) and saved its answer at 21.4 (9 s after launch; ESPN took 1.7 s). Later taps: Live 0.44 s to the script, Upcoming 0.2 s then a **second** window load 0.2 s later (the short window opened, then the long one: on a fresh start nothing is in memory, so it picked the short window and `draw` found more games than it has rows), Leagues 0.1 s; closing is immediate. Not measured: when the hub's games first appeared (no log line, now added).
- **Added from that log (host tests only):** the Upcoming page reads the saved answer before choosing its window, so the right one opens once and its first frame holds the games (`sports_upcoming.run`); the service's startup line now splits its imports by line (`imports 2.059s: bootstrap A, navigation B, startup C, airplay..transfer_control D`) because the 25x gap between phone and computer is unexplained (a tap in that window waits for it; the page scripts share the add-on's interpreter). **Still needed to finish item 1:** a log from a build that has these changes (a force-quit, then Sports tap straight away, then Live, Upcoming, Leagues): the `hub: first frame ... ms` line and the split import line say what is left.

### ISSUE-425 (continued): the build 623 flick log, and a wrong id in the diagnostic (log 8c570737, 2026-11-21)

- **Seen:** 35 `Kodi iOS gesture:` lines over the Sports pages, Favourites and Home, **all** "swipe action 531/541" (Kodi's swipe up/down, one per hard flick) and **no** pan line at all, not even for plain drags. So the page's `onAction` did receive the flick's swipe actions, and the pan run was never summarised.
- **Cause of the missing lines (my diagnostic, fixed):** `gesture_note` took ACTION_GESTURE_END as 505 and ABORT as 506; in Kodi 21.3's `ActionIDs.h` ABORT is 505 and END is 599, so no gesture ever finished and nothing was logged. A test now pins the ids. The next log will carry the pan lines (`glided on` / `stopped at once`).
- **What the log does and does not say about the cause (ISSUE-425 above):** a swipe action per flick is Kodi's own swipe detector (a fast one-finger move), separate from the pan; it does not start or stop a glide. Nothing in this log contradicts or proves the diagnosis that the window under the page overwrites the page's inertia answer; only a build with native r35 and a flick log can show it. r35 is built by the repo's PR workflow (run 44933200650 on this branch; the workflow publishes a prerelease `kodi-ios-portrait-r35`), then `source-lock.json` takes its digests and the IPA is rebuilt from it. Not proven on the phone.

### ISSUE-424 (captions, build 623 log 8c570737, 2026-11-21): the embedded tracks are not empty; Kodi can draw subtitles; what is left is what the cues hold and when

- **Seen (The Lanterns S01E02, 2026-11-21 09:41):** `file subtitle tracks: #3 eng tx3g (sbtl), 51 fragments hold it; #4 eng ..., 51 fragments hold it; #5 und ..., 51 fragments hold it` (51 fragments for each of the three), `Kodi says subtitles enabled=True (info True), current #1 eng`, nothing drawn. A downloaded subtitle (subdl, 13 results, the first applied, "speech not checked") **was** drawn, by the owner's own report ("they dont match and timing is off"). Two later speech checks: "ok at 928 s: 1 words", "ok at 1856 s: 16 words".
- **Ruled out by this log:** cause 1 (an empty or near-empty converted track: all three are in every fragment; though a fragment can hold only the blank samples that clear the screen, which the next probe tells apart) and cause 3 (Kodi's own state: enabled, track #1 current). Kodi draws a subtitle on this video, so the drawing path (position, 4K) is working for an external track.
- **Still open:** the embedded cues' content or timing (blank-only samples; times far from the picture's). **Added (host tests only, the next build's log):** `file subtitle cues: #3 [0 s: 2 samples, 1 with text, first text at 5.0 s (16 bytes), 6.0 s of text | 11 s: ...]; #4 [...]` (`mp4_tracks.fragment_entries`, `moof_samples`, `cue_summary`; reads the first three fragments' headers through the proxy, three 256 KB ranges, once per track menu open) next to the existing span line (`fragments from A s to B s | video fragments from ...`). Reading it: "none with text" in every fragment: the conversion wrote blanks only (source or `kr_prepare.c`); text present with `first text at` times matching the video's scenes: the cues are fine and Kodi's stream choice or the demuxer's reading of fragmented tx3g is the next suspect; times far from the video's own span: the offset. Checked on a real ffmpeg-written fragmented file (3 tracks, cues at known times); not the owner's file.
- **Separate finding (downloaded subtitles "do not match, timing off"):** "Download and apply" applied the first of 13 results unchecked, and the speech check counted 1 heard word (at 928 s) as "ok". A check that heard fewer than a handful of words says nothing and should not be reported ok, nor stop a second look. Not changed yet.

### ISSUE-427: a second Continue of the same Umbrella episode is as slow as the first (owner, build 623, log 8c570737, 2026-11-21)

- **Seen:** Continue of an Umbrella episode: tap to first picture 11.3 s (09:42:33) and, a second time, 10.7 s (09:42:51). Each: `Creating InputStream` to `Creating Demuxer` 1.9 s (connecting to the debrid server), `Creating Demuxer` to `Open - probe limits` 5.4 s (reading the file's start, about 0.5 MB/s), streams ready to first picture 3.4 s (the resume seek, read cold). The log has no `stream opening: route=` line: Continue played the link directly (build 622 undid the cache route, ISSUE-424) and nothing was kept between the two taps.
- **Cause:** the cache source is memory only, one source, thrown away when Kodi lets go; and its hand-off raced a slow server for five seconds (the 622 failure: 1 of 3 opening blocks after 2 s, then the direct link refused a range request while reads were still running).
- **Fix (host tests only, no build):** `resume_cache.py`. When an Umbrella stream stops (the progress tracker's stop, `portrait.progress_tracker(on_stop=)`), on Wi-Fi only, the service reads the file's first two blocks, its last block and the three blocks around where it stopped (the blocks Kodi reads first, by `RESUME_BLOCKS`; at most 8 blocks = 32 MiB, one stream, the last one replaces it) through the existing parallel cache source and keeps them in `addon_data/service.kodi.ios.bootstrap/umbrella-opening/` (named by a hash of the link; no address is written). Continue (`ios_watch_dialog.fast_stream`) uses the cache route only when those blocks are there for exactly that link (`_opening_kept`); the cache source starts with them in memory (`resume_cache.seed`, in the broker's open), so the opening is ready at once and Kodi's open and resume seek need no network; everything after is fetched on demand as before. With nothing kept, or another link, Continue plays the link directly as in build 620. A failed capture keeps nothing. The log says `resume cache: kept N of M blocks (X MiB) in T s` after a stop and `resume cache: N kept blocks given to the opening` on Continue, then the existing `stream opening: route=cache wait_ms=...` line.
- **Expected, not measured:** a repeat Continue of the same stream about 2-3 s instead of 10-11 s (connect and the first network read leave the critical path); the first Continue of a stream stays as slow as before (nothing kept yet). The resume point is a guess from time (the bitrate varies): a resume that lands outside the three kept blocks reads the rest from the link.
- **Retest:** `test_resume_cache.py` (plan; round trip; no address written; short/damaged blocks refused; capture through a fake origin keeps the planned blocks and skips a repeat; failures keep nothing; only an Umbrella stream with a resume point on Wi-Fi is kept; a broker open with a dead network reaches `opening_ready` and serves the start, the resume point and the end from the kept blocks; another link gets nothing; Continue uses the cache route only when kept), `test_fast_stream.py`. Not proven on the phone.

### ISSUE-428: Next Episode took 45 s and nearly crashed: the old video's close waited 40 s on Drive reads (owner, build 623, log 8c570737, 2026-11-21)

- **Seen (downloaded episode, Next Episode at 09:43:33):** the tap to the decision took 0.5 s (`next downloaded episode S1E3`); `CVideoPlayer::CloseFile()` at 33.61, then `OutputPicture - timeout waiting for buffer` (34.1), `CVideoPlayerAudio::Process - stream stalled` (39.7), two `CCurlFile ... Timeout was reached(28)` (53.6 and 09:44:13.7) and `CFileCache::Process - source read didn't return any data before eof!`: Kodi finished closing the old video only at 44:13.7, 40 s after the tap. Four Drive range reads of the playing copy show `headers_ms=40330 / 40149 / 40354 / 40576` and returned at that same moment. Then the next episode opened and showed a picture in 3.7 s (44:14.5 to 44:18.2), and the new open itself was fine. The video thread was held for 40 s, which is the "nearly crashes".
- **Not known:** why Drive's side was slow to answer those four requests (they began about 33.4, right after the tap, at the same offset region). Nothing in the log says.
- **Fix (host tests only; removes the wait, not the stall):** before the video is stopped, `next_episode` asks the Drive proxy (`GET /abort`, `drive_proxy.ask_abort`) to cut every upstream connection and refuse new upstream requests for 4 s (`Upstream.abort_all`); Kodi's cache read then fails at once instead of waiting out curl's two 20 s timeouts, so the close should take a moment. Only a video read through the proxy (a Drive copy) is touched. The log now says `Next Episode: old video closed after X s` for both routes.
- **Not done:** the cause of the 40 s (Drive or the phone's network starving right after the tap). Not proven on the phone: the next log's `old video closed after X s` line is the measure; if the video still takes long to close, the log's next lines show what Kodi waited on. `test_drive_abort.py`.

### ISSUE-424 (speech check, build 623 log 8c570737, 2026-11-21): "Download and apply" kept a subtitle whose timing the check could not establish

- **Seen:** `speech check: ok at 928 s: 1 words` and `ok at 1856 s: 16 words`: "ok" is the recognizer's status for one 30 s stretch (`speech_check.listen`), not a verdict; 1 + 16 = 17 words is above the 12 needed (`MIN_WORDS`), so `compare` ran, and `check_by_speech` logged nothing more: a verdict of `unknown` (agreement between 12 % and 30 %, or no confident shift) keeps the first of the 13 results as applied. The owner: the downloaded subtitle "does not match, timing is off".
- **Fix (host tests only):** the log now says `speech check: N words heard, this subtitle: unknown (agreement 0.21, shift 0.0 s)`; when the verdict is `unknown` the next three results are downloaded and compared (`speech_check.best_fit`): the one with the most agreement that the words establish (`fits`, or `shift` with its seconds taken out) replaces it (notification "Better-matched English subtitles on"); if none is established the subtitle stays as applied and the log says so. `test_speech_check.py` (`Choosing`: the right one of several is kept, a subtitle 6 s early is shifted by 6 s, nothing established gives none, too few words make no claim, the verdict is worded for the log, the menu wiring).
- **Not changed:** a stretch that hears 1 word (music, silence, or a recognizer miss) still counts as one of the two samples; more stretches when few words are heard is a later change. Not proven on the phone: the next log's verdict line and whether a better result is found.

### ISSUE-429: scroll numbers, build 623 (owner swiped every page for about a minute; log 8c570737, 2026-11-21)

- **Numbers (`Kodi iOS scroll:`, fps while the screen moved, typical / slowest tenth, samples):** Sports hub 27/20 (39), 26/17 (11), 24/24 (18), 25/24 (30); Upcoming (long) 24/24 (14); Home 42/42, 60/60, 45/45; Library hub 56-61; Sports Opening 40-61; busy dialog 30-60; context menu 41. Build 621-622: Sports 16-43, Favourites 25-41. Every Sports line is 24-27 fps; the Sports pages have few samples (8-39 each: flicks stop at once, ISSUE-425).
- **What the numbers say:** ISSUE-423 (the window under a page stops drawing) lifted the rig from 65 to 118 fps and did **not** lift the phone: the Sports hub and Upcoming read the same 24-27 fps as before. The same dialog mechanism gives 60 fps for Sports Opening, so the cover works; the cost is in the hub's and Upcoming's own rendering on the phone (the rig measured their controls at 0.64 ms a frame, so it is not control processing). It is the same while Crew's source search runs in the background (09:40:41) and when it does not (09:40:48), so it is not that load either. The probe counts any animating frame (15 fps or more), so some samples are fades, not scrolls; it cannot say which.
- **Not known:** what costs a frame on the phone. Candidates, none tested: GPU fill (several full-width gradient and rounded textures at 3x on a 1206 x 2622 screen, overdraw under the tiles and rows), the many conditional groups (12 Up next rows x 4 forms), the native glass tab bar compositing over a moving page.
- **Next (needs the phone, no code yet):** an A/B build, a debug switch that draws the hub without its gradient tiles, then without the rows, then without the tab bar, with the scroll line after each, would name the cost in one test. Not started; no UI change is made by this entry.
- **Built (2026-11-21, host tests only, no IPA, nothing on screen changes outside the test):** the scroll test. In Settings search type exactly `scroll test`: the only result, "Run the scroll test", opens the Sports hub, which waits 3 s for its games and then scrolls itself down and up (16 focus moves each way, 0.45 s apart) five times while Kodi's frame rate is read ten times a second, leaving out in turn nothing, the Live Now card, the two tiles, the Up next rows, and all three (their drawing only: the buttons stay, so the layout and focus are the same; `sports_upcoming_page.quiet`, hidden while the Home property `KodiIOS.ScrollTest` names the part; the Upcoming and Live pages' rows carry the same hook). One log line per run, `Kodi iOS scroll test: Up next rows left out: 31 fps typical, 24 fps slowest tenth, 88 samples`, then a notice "Scroll test: Done: send kodi.log". Reading it: a part whose removal lifts the rate is the cost; "card, tiles and rows left out" still near 25 means the cost is not the content (the backdrop, the native tab bar over a moving page, or the phone's drawing). The hooks add one visibility test per group per frame and stay in the skin until the cost is found; they are to be removed with the test. The test also starts the same background Sports work as opening the page (the search for sources), as in the earlier numbers. `test_scroll_test.py` (the runner with injected phone calls; the property always cleared, also on a failure or when Kodi closes; the hooks hide no button; the hidden trigger).

### ISSUE-430: the live game failed to stream (owner, build 623, log 8c570737, 2026-11-21, 09:44-09:46; Detroit Mercy at Michigan State, Crew "MUT")

- **Timeline (two attempts, 09:44:41 and 09:45:39):** the card's tap, `opening native addon queue (1 choices)`, Crew's folder refreshed twice (0.9 s, 2.0 s: ISSUE-420's direct game folder), Crew's chooser answered at 09:44:48.7 ("picked the first link"), then Crew's resolver: `Streamer [embedsports] failed | <the embed address> | HTTPSConnectionPool(host='taifood-blog.asia', port=443): Max retries exceeded with url: /fetch (Caused by SSLError(SSLError(1, '[SSL] unknown error (_ssl.c:1006)')))`, `Streamer fallback: PPV - HD | BTN (English) did not resolve, trying PPV - SD | BTN (English)` (the same host failed again at 09:44:49.9), and at 09:44:52.07 Crew handed Kodi the unresolved text `$doregex[makelist2]|regex=...` (then `plugin://plugin.video.thecrew/?action=play&url=%24doregex...`), which Kodi cannot open (`CVideoPlayer::OpenInputStream - error opening`). The app saw only the Stop ("stopped before any picture"), had one choice and no more, and said `play failed (RuntimeError)`. The second attempt (09:45:50-09:46:03) is the same.
- **Cause (what the log supports):** none of this game's sources could be resolved because Crew's embedsports extractor could not complete a TLS connection to its own host, `taifood-blog.asia` (both qualities of the one source go through it). Not our playback, the cache, the router or the link chooser: they behaved as designed (ISSUE-420: the failed source is reported and the queue ends; a single source has nothing to fall back to). Why the handshake fails is **not known**: this phone's DNS may answer for that name with something that does not speak TLS (a filter's block page; the same phone's DNS refused podnapisi.net: roadmap 2.13, and an earlier Sports log could not resolve this very host), or the site refuses the handshake, or the source is down. An OpenSSL "unknown error" with no certificate message fits an aborted handshake, not a missing CA bundle (that reads "certificate verify failed"). Not reproducible from here (the sandbox's network goes through its own gateway).
- **Done (host tests only):** `host_check.py`: after a failed source, once every ten minutes, the log gets one line per host Crew's streamers use (taifood-blog.asia, mutstreams.pk, strmfree.st, streamcenter.st): `host check: taifood-blog.asia: phone DNS 1 address (public), TLS ok TLSv1.3 | DoH 1 address (public, same as the phone), TLS tls refused (unknown error)`: what the phone's own lookup gives (the kind of address, so a block page's 0.0.0.0 or private address shows), what DNS over HTTPS gives (`doh_fetch`), and whether a TLS handshake completes to each; no path, link or header. `test_host_check.py`.
- **Next, depending on that line:** the phone's DNS gives a non-public address and DoH a public one that handshakes: Crew's requests in its streamer must connect through DoH's address (the pinned-line patch of Crew, `sports_crew_patch.py`, can carry a name-resolution fallback while a Sports play runs; `doh_fetch` already does it for the subtitle sites); the same address both ways and the handshake refused: the site is refusing this phone and only another source helps (the game needs a second source: more Crew menus, or a different provider); handshakes ok: the failure is Crew's own request (its headers or the API's answer) and the next log needs Crew's reply status. Nothing here changes what plays. Not proven on the phone.

### ISSUE-431: the Sports opening loader looks bad (owner, build 623: "I want this loader for the sports to work, its ugly"; screenshot IMG_0541)

- **What is wrong with it (read from the screenshot, mockup-class review, not a device test):** the card floats over the un-dimmed page (the Library's "Favourites" row shows behind it and is cut by it); the game, the one thing that matters, is the smallest grey text, below a bigger generic title; the progress bar is a faint hairline with a short segment; "2 seconds elapsed" is tiny; a gap of about 200 units sits between the teams and the status (the matchup box is sized for four lines); Cancel is an outlined box.
- **Mockup (2026-11-21, `docs/design/sports-opening-options.html`, HTML in a browser, **not** the app):** three options with the project's tokens, Inter, a 4-pt bar (DEC-036), one primary action, 44-pt targets, no text under 11 pt: **A** a centered card with the page dimmed and the matchup (crest, name, "at", crest, name) as the headline, **B** an opaque full page (like Umbrella's "getting ready"), **C** a bottom sheet in the Activity sheet's family. States: connecting, trying the next source, slow, **failed (a proposal: today the card just closes)**; a switch for the longest team names. Rendered in a browser at 402 x 874 and checked for overflow with usual and longest names (none; the long names wrap to three lines in A, two in B and C); crests are grey initials standing in for the real ones the Sports pages fetch. Nothing is implemented; the owner picks one (or says what to change) before any skin change, per the visual review process.

### ISSUE-431: the Sports opening loader looks bad (owner, build 623: "I want this loader for the sports to work, its ugly"; screenshot IMG_0541)

- **What is wrong with it (read from the screenshot, mockup-class review, not a device test):** the card floats over the un-dimmed page (the Library's "Favourites" row shows behind it and is cut by it); the game, the one thing that matters, is the smallest grey text, below a bigger generic title; the progress bar is a faint hairline with a short segment; "2 seconds elapsed" is tiny; a gap of about 200 units sits between the teams and the status (the matchup box is sized for four lines); Cancel is an outlined box.
- **Mockup, round 1 (2026-11-21):** three options (A centered card, B full page, C bottom sheet). The owner chose **A**.
- **Mockup, round 2 (`docs/design/sports-opening-options.html`, HTML in a browser, **not** the app):** A refined as asked: LIVE on its own line at the top with the league tag under it; the teams' real crests, no circles (ESPN's `500-dark` versions: a dark crest such as Michigan State's green disappeared on the dark card in the first render); the team's short name on one line under its logo (the short names the Sports rows use). Same card as before otherwise: page dimmed, 4-pt bar (DEC-036), one stage line, "Source 1 of 2 · 0:03", Cancel. States: connecting, trying the next source, slow, and **failed (a proposal: today the card just closes)**; a switch for the longest short names (Timberwolves, Trail Blazers). Rendered in a browser at 402 x 874 and checked: both crests load, both names fit on one line in every state. Crests load from ESPN's image server in the browser; nothing is committed. Nothing is implemented; the owner approves (or changes) this before any skin change.
- **Ported (2026-11-21, host tests only; no render of the real page yet: rig and device pending):** the owner chose option A and the round-2 mockup ("cleannn port that in"): `sports_opening_page.py` and `sports_opening.py` now draw it in the real skin: the page behind dimmed (black 62 %), one centered 900-unit card, "LIVE" with its dot over the league tag (only for a live game), each team's crest (the file the hub already fetched; the team's code until it is in) with its short name on one line under it (ESPN's short name, or the code when it would not measure under its column: `notifications_skin.text_width` at the card's size, never cut), the stage line, `Source 2 of 3 · 0:09` (the count from the router's queue, `KodiIOS.SportsOpeningChoice`; after ten seconds "Taking longer than usual" and "· You can cancel"), the 4-pt bar and Cancel. **Failed:** when every source fails the card stays, says "This game didn’t open / None of its sources worked." and has one button, Back to Sports (it used to close and leave a toast); a Try again button is not built (a retry has to come from the game page, which owns the queue). `test_sports_opening_card.py` (structure, dimming, LIVE over the tag, failed swaps the bar and Cancel for Back, every line measured to fit one line, the longest real short names stay whole, bad data, the card's states and wiring). The text widths are the project's conservative estimate, not Kodi's drawing: the desktop rig render and the phone are the proof.

### ISSUE-430 (continued): the failed sources, a fix to try (2026-11-21, host tests only)

- **Why it is probably this (not proven):** the exact text of Crew's failure, `[SSL] unknown error (_ssl.c:1006)`, is what this app saw before for Drive sign-in on this phone (ISSUES, early): Python's default SSL context has no CA roots there, so an add-on that builds its own context (instead of requests' certifi) cannot verify any site; `netcheck.py` already tests "python default" against certifi for that reason. An aborted handshake or a filtered DNS would not usually give this text. Crew's embedsports extractor is the add-on code that fails, twice, on the same host.
- **Fix:** `tls_roots.apply()`, the first thing the service does: SSL_CERT_FILE is pointed at certifi's bundle unless it already names a file. Kodi runs every Python add-on in one process, so every context built afterwards gets roots; add-ons that use certifi are unaffected. The startup log says `TLS roots set from certifi for every add-on` (or why not). `host_check` now also probes the same address with Python's default roots (`default roots: ...`): "unknown error" there and "ok" beside it proves the cause; "ok" with the default roots means the fix was not needed and the DNS/handshake lines say where to look. If Crew builds its context before the service has run (it starts at the same time at launch) the first play after a launch could still fail; the log's order will show it. `test_tls_roots.py`, `test_host_check.py`.

### ISSUE-425 (continued): native r35 is built and pinned (2026-11-21)

- The pull request's build workflow built and published `kodi-ios-portrait-r35` (run 44933200650, from 695bebe, patch unchanged since): the archive's digest and the executable's digest match the release; the executable is an arm64 Mach-O. `source-lock.json` now pins r35 (r34 kept as previous) and the next IPA built from this branch carries it. **Flicks are still unproven: only the owner's phone shows a glide**; the log's `Kodi iOS gesture:` lines (end id fixed) say `glided on` or `stopped at once`.

### Build 634 test (owner, 2026-11-21, logs e3be05f1 old, 89646295, 4b37fc5b): what the logs show, and four fixes (host tests only)

- **Flicks (ISSUE-425): fixed on the phone.** 11 of 12 logged gestures `glided on` (a 7-pan, 0.08 s drag was `stopped at once`), with native r35. Scroll while moving: Sports hub 60 fps (24-27 in build 623), Upcoming 60/51, Favourites 45, Library hub 41-60, Settings 54. The window under a modal page overwriting the page's inertia answer was the cause; the page cover was never it. The scroll test (ISSUE-429) is no longer needed for the hub; the owner could not find its entry (Settings search, exact words "scroll test") and the flicks work.
- **Failed sources (ISSUE-430): the cause is proven.** The host check line, twice: `taifood-blog.asia: phone DNS 4 addresses (public), TLS tls refused ([SSL] unknown error) | default roots: tls refused ([SSL] unknown error) | DoH 1 address (public, not the phone's), TLS ok TLSv1.3`; the other three hosts work on the phone's own DNS. So the phone's DNS answers for that name with addresses that cannot complete TLS (a filtered or stale answer); another resolver's address works. The certificate-roots guess was wrong (the startup line says `TLS roots left as they were (SSL_CERT_FILE is a file)`: roots were already there) and is harmless. Two more hosts failed TLS in the same log (`v2.streameast.ga` for a schedule, `thedaddy.li`). **Fix:** `dns_override.py` (service, 2 s after start then every 30 minutes) tries each listed host: when the phone's addresses all fail TLS and a DoH address works it writes it to `dns-overrides.json`; a lookup wrapper appended to Crew's own `control.py` (`sports_crew_patch.apply_dns`, pinned version only, added once; the service patches Crew at startup, not at the first game) answers that host from the file, so Crew connects to the working address while TLS still checks the certificate for the host's own name. Other names and any failure use the normal lookup; entries over 12 h are ignored. The log says `dns override: <host> connects by a public address from DNS over HTTPS`. Not proven on the phone: whether Crew's streamers use `socket.getaddrinfo` in the interpreter the patch runs in (they use requests/urllib3, which do), and a first game right after a first install can still fail if Crew imported its module before the patch was written (the second launch is covered). `test_dns_override.py` (the wrapper code is run for real).
- **Continue with an Umbrella link failed completely (log 4b37fc5b):** Black Clover S02E08, remembered link `...debrid.it/dl/...mkv`: `Creating Demuxer` 12:09:36, then 30 s with no data, `Open - Error, could not open file`, `Playback failed` box. The direct link is Continue's fast path; it had no fallback. **Fix:** `continue_guard.py` (service): `fast_stream` leaves a note; if a picture is not up in 25 s, or Kodi's failure box shows, the guard stops what is opening, closes the box and plays the same title the normal way (`ios_fast=0`, so it never tries the remembered link again; TMDb Helper and Umbrella find a fresh one, which Continue remembers). The log says `continue guard: the remembered link did not open (N s ...); asking Umbrella for a fresh one`. `test_continue_guard.py`. **Not known:** why that link did not open (an expired or throttled debrid link; `_link_alive`'s one-byte read passed).
- **The app closing on the same Continue (log 89646295, ends abruptly at 12:08:37, 0.9 s after `Creating InputStream` for the same title, no error line):** the log shows no cause. The resume cache (ISSUE-427) was not involved (no `resume cache` line; nothing was kept: no Umbrella stream had stopped in that session); the second attempt (4b37fc5b) did not close. Candidates, none shown: the phone ending the app for memory, or a native fault. **Needed:** the iPhone's own crash report: Settings > Privacy & Security > Analytics & Improvements > Analytics Data, newest file named `Kodi` (or `JetsamEvent`), shared as text.
- **Lag on Sports pages (review of 89646295):** `hub: first frame from the saved answer` took 1087 ms (3 s after launch), 72 ms (a later open), then 1938 ms and 1609 ms (the opens right after a failed game, with Crew's resolver and the host check running). The page work is the same each time, so the time is waiting for the processor: the source search and Crew's resolver run in the same process and compete with the page (one Python lock). **Change:** the background source search no longer starts until 3 s after a Sports page opened (`poke()` in the service). Not proven; the next log's `first frame` times say.

### ISSUE-424 (captions): the cause is found; "on" that shows nothing, and a download that is forgotten (owner, build 634, log f75957fe, 2026-11-21)

- **Cause (read from the new `file subtitle cues:` line, four opens of The Lanterns S01E03):** `#3 [17 s: 3 samples, 1 with text, ... 0.0 s of text | 34 s: 7 samples, 3 with text ... 0.0 s of text | ...]` and the same for #4 and #5: every text cue of all three converted tracks is **0 s long** (the blank sample that clears the screen starts at the same instant as the text). Kodi opens the stream, reports `enabled=True ... current #1`, and each cue is gone as it appears. Not Kodi's state, not the fragments (52 hold them, spanning the whole video), not the 4K path: the cues the converter wrote. `kr_prepare.c` wrote `end_display_time - start_display_time` as the cue's duration; a source whose subtitle packets carry no duration decodes with an end time equal to its start, so 0. The downloaded SRT worked because its cues have lengths (owner: "they did work when i downloaded and applied them").
- **What the owner saw, and why:** (1) the CC button and the menu said "English CC on" while nothing showed: Kodi picked the embedded track and called it on; (2) a downloaded subtitle was forgotten when the show was left: the file lived in `special://temp` (emptied at every start; the log's "removing tempfiles") and nothing re-applied it.
- **Fixed in the app (host tests only; works for every existing copy, no new conversion needed):** `mp4_tracks.zero_length` / `probe` find tracks whose text cues have no length; the Subtitles menu leaves such a track out like an empty one (the existing rule then turns the subtitles off instead of leaving "on" ticked), and a video that starts on one has its subtitles turned off by the service. The menu keeps what it downloads under the profile (`addon_data/service.kodi.ios.bootstrap/subtitles/`, not temp) and remembers it for that video (`subtitle_memory.py`: the show, season and episode, or title and year, or the file's name); when that video starts again the service puts it back on (`subtitle memory: the subtitles you downloaded for this video are on again`); removing it forgets it. Up to 60 videos are kept. `test_subtitle_memory.py` (identity, remember/recall/forget and the limit, the start rules, the probe on a synthetic fragmented file with and without cue lengths).
- **Fixed in the converter (source only; takes effect only in a new AirPlay framework build, r56 of the remuxer, not built, needs the owner's go):** a cue with no duration gets the source packet's duration when it has one, else a reading time from its text (1.2 s + 70 ms a character, 2 s at least, 7 s at most), `kr_cue_reading_ms` in `kr_prepare.c`; compiled against FFmpeg 6.1's headers (the pin is 6.0.1) and the helper run for real in `test_cue_length.py`. Copies prepared before that build keep their zero-length cues, which the app-side fix above covers. Not proven on the phone.

### ISSUE-428 (continued): Next Episode, build 634 log 4c4cf619: slow, a stray page opened, an empty box, the episode stopped (owner, 2026-11-21)

- **Timeline (S1E3 to S1E4, 12:14):** tap 12:14:21.97; `next downloaded episode S1E4` 22.49; `CloseFile` 22.59; the player's threads closed at 23.6; then 25 s with nothing until `CCurlFile ... Timeout was reached(28)` and `CFileCache::Process - <http://127.0.0.1:64441/download/...mp4> source read didn't return any data` at 48.66; `old video closed after 26.5 s`. The file was read through **the Google Drive add-on's own download server** (`/download/`, port 64441), not the app's Drive proxy: the proxy (`Drive proxy: streaming Drive copies on port 64543`) only came up at 12:14:14.6, 8 s after launch, and the Continue that started this episode was tapped at 12:14:12. `ask_abort` (ISSUE-428) cuts only the app's own proxy, so nothing could cut this read. The next episode itself opened in 2.5 s and showed a picture at 6.9 s.
- **The stray page and the empty box:** the moment the old video closed (12:14:48.7) Kodi reopened `DialogVideoInfo` (the page of the film "Madden", opened earlier in the session). It stayed over the new episode, unseen. A tap on the video at 12:14:59 landed on that page's Play button: TMDb Helper started to play the film (`play_player ... tmdb_type movie tmdb_id 1131943`), our "Download or Stream" sheet failed (`sheet_choice: RuntimeError: XML File for Window is missing`, the landscape layout has no such window), Kodi's own select box came up empty (the grey square in the owner's second screenshot, six taps "not handled"), nothing was picked, `lib.player - Failure!`, `Playlist Player: skipping unplayable item`, and the episode was closed at 12:15:07.
- **Changed (host tests only):** (1) Next Episode shows the white loading circle from the tap (`ActivateWindow(busydialognocancel)`) until the next video has a picture or 45 s (`next_episode.finish`), closed in every case; (2) after the old video has stopped, and again once the new one plays, it closes the pages Kodi may have reopened (film info, context menu, select box, OK and Yes/No boxes), by name, never "all" (that would close the circle); (3) a library play in the first 40 s after the service started waits up to 5 s for the app's Drive proxy instead of using the add-on's server (`KodiIOS.ServiceStart`, `ios_library.live_proxy_port`), so the abort can cut it; (4) the bundled `advancedsettings.xml` gets `<curllowspeedtime>8</curllowspeedtime>` (Kodi's default is 20 s): a stalled loopback read no longer holds a stop for 20+ s, whichever server it is; an owner's own setting is kept; it is applied when the IPA is built, so it shows only in the next IPA. `test_drive_abort.py`, `test_customized_ipa.py`.
- **Not changed:** the empty landscape select box and the missing landscape sheet window (they only appeared because the stray page started a film play); the reason Kodi reopens the earlier info page when a video stops (not shown by the log). Not proven on the phone.

### ISSUE-431 (continued): the opening card on the phone did not look like the mockup (owner, build 634, screenshot IMG_0543 and log 9d155e7a, 2026-11-21)

- **Seen:** NBA game, Milwaukee at Philadelphia: no LIVE line, "NBA" alone at the top with a gap above it, the teams' letters "MILW" and "PHIL" big in grey where the crests belong, and the names "Milwau" and "Philadelphia 76e" (cut), "Connecting to the source / 0:02", the bar, Cancel. The card's layout, dimming, bar and button were as built; its data was not.
- **Cause:** the card reads the game from the Crew link's descriptor (`CrewLink.game`), which kept only the league, the start time and each team's `name` and `aliases`: no short name, code, crest or live state. So no LIVE (state empty), no crest to load (the letters show instead), and the name fell back to `name[:6]` or `name[:16]` (a cut). The mockup was made from ESPN's full game, which the card never had.
- **Fix (host tests only):** `CrewLink.game` now also keeps `state` and each team's `short`, `code` and `crest`; for a link saved before that (the prefetch's saved links) the card looks the game up in ESPN's saved answer by its team names (`sports_opening.enrich`); crests are ESPN's dark-background versions (`500-dark`, the hub's small 96 px size); a name is chosen so it is never cut: the short name, else the full name, else its last word ("Bucks", "76ers"), else the code, the first that measures under the column. `test_sports_opening_card.py` (the logged names, the lookup, dark crests, what the Crew link keeps).
- **Timing from the same log (the live game did play: `Crew TS is playing (1088p 59 fps 9500 kbps)`; first tap cancelled by the owner):** tap 12:26:37.5 to the card 0.6 s, to the queue opening 1.35 s, Crew's folder refreshed twice (0.96 s, 1.88 s), chooser answered at 43.5 (6 s after the tap), Kodi's open 46.2, first AV 47.17: **9.6 s from tap to picture** (second attempt 11.8 s). The source was already found (`prefetch: NBA ... 1 source(s) ready` at 37.17); the time is Crew's own folder refresh, its chooser and its resolver (ISSUE-420), not the search. Not changed here.


### ISSUE-432: Continue through Umbrella took 26.9 s the second time, as long as the first (owner, build 639, log 9f7b4ab2, 2026-11-21)

- **Seen:** Black Clover S02E08 through Umbrella: first open 29.4 s (handoff 7.2 s, Kodi's open 22.2 s); stopped; Continue again 26.9 s (handoff 4.5 s, open 22.4 s). The owner had it under 11 s in build 623.
- **What the log shows:** the second Continue went the full way (TMDb Helper, "Choose a version: kept 21", Umbrella again) instead of `ios_watch_dialog.fast_stream`, and Kodi opened a link with `route=direct ... served=0`: none of the kept opening was used. There is **no line saying why** `fast_stream` declined. Its checks, in order: not Umbrella or no remembered link, link older than 4 h, nothing to resume, **the one-byte liveness check of the link** (3 s timeout). At the same moment the resume cache's own capture (ISSUE-427) was reading six 4 MiB blocks of the same link through six connections (`cache block ... took=5.32s / 5.64s / 8.00s`, ending 13:11:03.96, 4 s after Continue was tapped at 13:10:59). A debrid server needs 2-3 s to connect; answering one more request while six were running took longer than 3 s.
- **Cause (probable, not proven):** the capture started right after the stop and was still running when Continue was tapped, so the liveness check timed out, `fast_stream` returned False with no log, and the normal 22 s way ran; the capture also slowed that open's own reads. Even a finished capture would not have helped: the normal way fetches a fresh debrid link, and the kept blocks belong to the old link's name.
- **Fix (host tests only):** (1) the capture lets go at once when a title is asked for (`KodiIOS.OpenWanted`, set by `fast_copy`) or a video plays, and keeps the blocks it already has; (2) a timeout of the link check no longer means "dead" (only a refusal or an unreachable server does), its timeout is 6 s, and the continue guard remains the safety if the link really does not open; (3) every decline now logs `Kodi iOS watch: Continue did not use the remembered link: <reason>`. `test_resume_cache.py`, `test_fast_stream.py`.
- **Not fixed / not known:** the first open (29 s) is the debrid server's slow start for a new episode (4 MiB blocks at 0.5-0.8 MB/s) and Umbrella's own scrape; it needs a different source or server, not this code. Phone retest needed: the next log must show either `continued ... from its last Umbrella link` or the reason line.

### ISSUE-433: Next Episode of a Drive show failed with HTTP 502 (owner, build 639, log 9f7b4ab2, 2026-11-21)

- **Seen:** Lanterns S01E01 to E02, twice: `Next Episode: old video closed after 0.4 s`, then `CCurlFile::Open ... /drive/<id>/Lanterns.S01E02... Failed with code 502`, `CVideoPlayer::OpenInputStream - error opening`; the owner's retry from the Library played.
- **Cause (from the log):** ISSUE-428's cut. `cut_drive_reads` makes the Drive proxy refuse requests for 4 s (`aborted_until`) so Kodi's close does not wait; the next episode's first request came 0.4 s after the close, inside those 4 s, and the proxy answered 502.
- **Fix (host tests only):** after the old video is closed Next Episode asks the proxy to release (`/abort?release=1`, `Upstream.release`), so the next video's first request is answered. `test_drive_abort.py`.

### ISSUE-434: A downloaded subtitle for an Umbrella episode was for the wrong thing; no English track in the new episode (owner, build 639, log 9f7b4ab2, 2026-11-21)

- **Seen:** Black Clover S02E08 (released that day): the file has Arabic, German, Spanish, French, Italian, Polish, Portuguese, Russian, Thai and Chinese tracks and **no English one** (`tracks: streams: #0 ara ... #10 chi`), so there is nothing in the file for the app to show. The subtitle search then logged `search en 'Episode 8' None SNoneENone via subdl`: the title Kodi has for the item is "Episode 8", with no show, season, episode or year, so SubDL was asked for "Episode 8" and returned one subtitle (`subdl: 1 found`) from some other show, "wrong".
- **Cause:** `KodiIOS.Playing` (what the add-on that started the video knew) is set only for downloaded copies; for an Umbrella stream nothing supplied the show, season and episode, though Continue Watching's own entry holds them (`tvshowtitle`, `season`, `episode`, `tmdb_id`).
- **Fix (host tests only):** when Kodi's item lacks them, the search takes show, season, episode, year and TMDb id from Continue Watching's current entry if its title agrees and it is under 6 h old (`tracks.continue_known`). The search will then ask for "Black Clover" S2E8. `test_continue_known.py`.
- **Not known:** whether subtitle sites carry this brand-new episode at all, or number it as season 2 episode 8 (a long-running anime is often listed by absolute number); the next log shows what the corrected search finds. The English track missing from the file is the release's, not the app's.

- **ISSUE-433 addendum (same log, 13:13:03):** the abort that makes Next Episode close fast also left a Drive proxy request thread with `AttributeError: 'NoneType' object has no attribute 'close'` (http.client's response lost its socket when the connection was cut) and a long traceback in the log. It is now read as an abort (`ConnectionAbortedError`). `test_drive_abort.py`. Other items found in the same log and not changed: see the report to the owner (2 s cache wait on every Umbrella open, speech check never decides on Drive episodes, one widget page that always fails, scroll at 24-36 fps while a video opens).

### ISSUE-435: Umbrella's wasted 2 s, the speech check that never heard anything, and captions that stay invisible in already-converted copies (owner asked for all three, build 639 log 9f7b4ab2, 2026-11-21)

- **1. The cache's 2 s wait on every Umbrella open.** Both opens logged `route=direct wait_ms=2008 ready=False blocks=0/3`: the service's cache is asked for its opening blocks, the server (a debrid link at 0.5-0.8 MB/s) does not deliver them in time, and the link is handed to Kodi directly 2 s later. **Fix (host tests only):** a server that missed the cache's opening is remembered by host in the Home window for 20 min (`KodiIOS.CacheSlowHost`, no path or token) and its next link is played directly at once, unless the opening of that very link is on the phone (resume cache); the cache is tried again after 20 min. `test_cache_skip.py`. Expected gain: about 2 s per open on a slow server; unproven on the phone.
- **2. Speech check heard nothing.** Three times on a 4K Drive episode: `no_sound at 1016 s / 2033 s: less than a second of sound`, then "nothing to compare", so a wrong downloaded subtitle could never be caught. The 24 MB byte budget per sample is about 8 s of a 25 Mb/s file, mostly picture. **Fix (host tests only):** a place that gave no sound is read again once with four times the budget, and if nothing at all was heard a third place (45 % in) is tried. `test_speech_check.py`. Whether the on-device recognizer then hears enough is unproven.
- **3. Converted copies with zero-length cues.** The converter fix (r72) only reaches newly prepared copies; the Lanterns copies already on Drive keep their zero-length cues. **Fix (host tests only; needs the r72 IPA):** when the installed framework is r72 or newer, the library's check of a ready, fragmented MP4 also probes its subtitle tracks (`caption_repair.due`, `mp4_tracks.probe`); a copy with zero-length cues takes the existing re-package path ("Making it start faster", `layout_reason: caption_lengths`), once per framework revision per copy, so a converter that did not fix it cannot make the library repack the same file repeatedly. Nothing runs before r72. `test_caption_repair.py`.
- **Not done / not proven:** the library check only reaches copies the existing inspection visits; whether a re-package of an already prepared MP4 keeps its other tracks and passes the existing verification is the repack path's own behaviour and has not been run on the phone or a rig. Re-packaging uploads a new copy to Drive: watch the first one.

### ISSUE-436: Sports: the Play button took about 30 s on the first game, and every tap spent about 12 s before a picture (owner, build 639, log fd1d028c, 2026-11-21)

- **Seen:** (a) first game after launch: its page opened 13:47:17, Crew's first scan found the stream at 13:47:45, the prefetch had it ready at 13:47:47: about 30 s, 42 s after launch, with no Play button until then. (b) Two taps (game 1: tap 13:50:03.96, first AV about 13:50:17.3; game 2: 13:50:30.95, AV 11.7 s after dispatch): about 1.2 s tap to queue; **2.7 s of Crew folder listings** (0.95 s with 20 entries, then 1.76 s with 58: the root, then the game's folder); **about 6 s** between handing Kodi Crew's play route and Kodi opening the stream (`VideoPlayer::OpenFile` of Crew's own manifest), silent in the log; about 2 s from open to picture.
- **Cause:** (a) nothing looked for sources until Sports had been opened (the gate added for build 616's busy dialog), then Crew's cold first scan ran. (b) the direct-folder shortcut (ISSUE-420's bug 1) was not taken (the log says nothing about why) so the whole chain was listed at the tap; the 6 s is inside Crew's plugin resolving its `$doregex` link and cannot be seen from outside.
- **Fix (host tests only):** (1) sources are looked for from 30 s after launch, on Wi-Fi, before Sports is opened (`sports_sources_prefetch.idle_for_search`; the service's other checks stay: not while a video plays or a game page searches; the Crew busy dialog is still closed within 50 ms). (2) a game page that has a Crew best source lists that source's folder when it opens (`sports_game.warm_best`, `sports_crew_routes.warm`); a tap within 120 s, with no other Crew listing in between (`_LISTED` counter: another folder clears Crew's link rules), reuses the answer and lists nothing. (3) when the direct folder is not used the log now says why; the time to hand-over is logged (`Crew link ready after Xs`) and the time Crew's plugin takes to give Kodi a stream (`Crew handed Kodi its stream Xs after the play call`). `test_crew_warm.py`, `test_sports_sources_prefetch.py`.
- **Expected, unproven:** about 2.7 s off a tap when the page was open for a few seconds first; the cold-start Play wait mostly gone if the scan finishes before the first game is opened. **The 6 s inside Crew is not changed**: the new line shows it per tap; if it stays at 6 s the next step is Crew's own resolver (its site's DNS/TLS, `host_check`), not this code.
- **Risk to watch:** a background Crew scan 30 s after launch uses CPU and Crew's interpreter while the Home screen is up; if the Home scroll or the first Sports open lags in the next log, this is the first thing to move later.

### ISSUE-438: Umbrella reliability and speed, Sports tap and scan, Black Clover subtitles (owner, build 646, logs aec66fce and d8f39741, 2026-11-21)

Build 646 is the Sports build line with the other agent's Live Now rows merged in (commit 1acae17 contains bb98bcc and r72). Findings and host-tested fixes:

- **Umbrella first open failed after a 2 s cache wait (log aec66fce 14:41:10-14:41:14):** `route=direct wait_ms=2011 ready=False blocks=1/3 pending=6 requests=28`, then Kodi's own range read of the debrid link failed with `Requested range was not delivered by the server(33)` and `could not open file`; the owner tapped again and the second try (cache skipped by ISSUE-435's memory) played in 9.8 s. 28 requests in two seconds is more than the debrid service accepts; its refusal outlived the cache's aborted connections. **Fix:** the "slow server" memory is now per server family (`debrid.it`, since every link has its own sub-domain) and kept on disk (6 h), so the first open after a launch skips the cache too. `test_cache_skip.py`.
- **Continue's kept opening was too small:** Kodi read blocks 0, 2, 3 and 5 (offsets 0, 9 MB, 13 MB, 22 MB) before the first picture; only 0 and 1 were kept, so blocks 2-4 took 2.9 s each from the server (`cache block: index=2..4 took=2.9s`). **Fix:** the opening kept is blocks 0-5 (24 MiB), at most 12 blocks in all. `test_resume_cache.py`.
- **Continue's link check "refused" a busy server:** a second Continue 3 s after the first got a refusal from the debrid server (the first's reads were still running) and took the normal 10 s way. **Fix:** 429 and 5xx count as busy, not dead; only other refusals (401/403/404/410) skip the link,. `test_fast_stream.py`.
- **Sports tap listed the folders twice again (log aec66fce 14:40:27-14:40:33):** the game page's warm listing was 2 s old when the tap came, so the tap started a second listing beside it (1.3 s + 1.9 s each, `Crew game folder not opened directly (its address holds a $doregex rule)`). **Fix:** a tap waits (up to 8 s) for the warm listing of its own link and uses its answer. `test_crew_warm.py`.
- **Sports Live page scrolled at 16-18 fps during Crew's 28 s scan (same log, 14:40:16-14:40:26; 59 fps before it):** the scan's folder listings run Crew's page parsing while the page draws. **Fix:** a background listing (the scan, never a tap's) waits while Kodi reports 15 fps or more (the page moving) for at most 3 s before starting. Expected: smoother scrolling during the scan; the scan itself takes longer only while the screen moves. `test_crew_warm.py`.
- **Black Clover subtitles (log d8f39741):** the file the owner first played has one embedded English track, marked **forced**, "American English"; the Continue and the second source (no English at all) both searched `Black Clover S2E8` correctly and SubDL found 5, but every download failed with `Mismatch: No subtitle file for this episode`: the zips' file names carry another season number for the same episode (the sites number a long-running show differently from TMDb). **Fix:** when SubDL itself marks the result as this episode, the one file naming the same episode number under another season is used (never when two seasons have it, never for another episode); the log now names the files in a zip that gave nothing. `test_zip_loose.py`. **Not fixed:** the English track marked forced may only hold signs and songs; the app still offers it as "English". Whether it shows dialogue on the first open and not after Continue is not explained by this log.
- **Not found:** "one source failed and never tried the second" does not occur in these logs (one Sports play, which worked after the stream reconnected itself at 14:40:41 following a `ConnectionResetError`). Needs the log of that run.

### ISSUE-437: Live Now rebuilt as grouped, compact rows (owner, 2026-11-21: build 622 screenshot, then the ESPN-app reference; mockup rounds approved the same day)

- **Asked:** clean up the big cards; the league tag and a red clock; real logos; no Watch or sources button. Then, from the owner's ESPN-app crops: hairline rows with each team's logo and short name at its edge, a big condensed score beside the logo, the clock in the middle with the quarter, the grey down-and-distance under it, a football on the side that has the ball (it must follow possession as ESPN updates), the league's real logo in a small header per league (NFL games with NFL games), live games only (no upcoming). The owner approved the final HTML mockup ("MONEY now thats the mock up i approve build it") and asked for code only: no IPA.
- **Measured from the crops (3 px per pt):** row 89 pt, logo 36 pt, names 13 pt bold grey, score 28 pt tall and about 14 pt a digit (a condensed bold), clock about 15 pt bold, the situation line about 10 pt. Names longer than 10 letters are drawn as the team code (UNC, WVU, MSST), as the ESPN app does, so nothing sits near the clock.
- **Done:** `sports_live_page.py` (rows and league headers; the header has no line under it and is not a button; `GAMES` 30 rows; the tap area per row keeps `CARD0`), `sports_live.py` (`grouped`: big leagues first, order inside a league kept; `team_label`, `league_title`; properties `g.N.gn/gs/hp/gl` on a league's first game, `dn/yd/rz/ball` for football, per-team `short`/`score`; the old combined score, league tag and source slots are gone), `sports_espn.py` (ESPN's `situation`: `shortDownDistanceText` -> `detail`, `possessionText` -> `yard`, `isRedZone` -> `redzone`, `possession` team id -> `ball` 'a'/'h'; each refresh rewrites them, so the football moves when possession changes), `sports_merge.py` (carries those four through the merge; it used to drop them), `sports_logos.py` (`dark_url`/`fetch_dark`: ESPN's 500-dark league logos for a black page, kept on the phone like the others; NCAAF and NCAAB draw the skin's football and basketball glyphs), `portrait.py` (`p_score` style and the font and football files written with the pages).
- **Score font:** Barlow Condensed ExtraBold, digits only (7 KB), SIL Open Font License (`resources/fonts/OFL-BarlowCondensed.md`). It keeps its own file even where every other style is the phone's San Francisco, and it is not bolded (Kodi's bold on a font that is already ExtraBold would smear it). The repository takes no binary files, so the font is base64 text in `score_font.py` (decoded and written to the skin's fonts folder with the pages) and the football is drawn in Python (`portrait.football()`, 96 px, laces and seams, antialiased) and written to `extras/portrait/`.
- **Checked in the desktop Kodi rig with live ESPN data (33 games): headers with the NHL logo and the football glyph for NCAAF, football on the possession side, "1st & 10 · MTSU 39", scores in the condensed font, three-letter codes for long names. Rig screenshots stay out of Git. Not proven on the phone.**
- **Team logos on black:** ESPN's default logo for Iowa is black and vanished on the page (found in the rig: an empty logo spot). Team colours do not say it (Iowa's ESPN colour is not black), so the page measures the logo itself: ESPN's 96 px version is decoded in pure Python (`sports_logos.brightness`, 8-bit RGB/RGBA PNG) and a logo whose visible pixels average darker than 0.12 is fetched from ESPN's dark-page folder (`/500-dark/`, `dark_crest`); the answer is remembered in a `.dark` marker beside the crest. Every other team keeps its plain, coloured logo (a first try used the dark logo for everyone and turned Charlotte and Sam Houston white, which the approved mockup does not show; a second tried the team colour and still missed Iowa). A dark logo ESPN does not have falls back to the plain one. Tests: `DarkCrests`.
- **Mistakes on the way (kept):** (1) the headers did not show at first because the `page()` loop was never changed to add them (the edit missed its target); found from the XML in the rig, which had one `g.1.gn` instead of two. (2) A header written as two groups with a combined `A + B` visibility left a blank 128-unit gap; each variant now has one plain property (`hp` or `gs`). (3) `sports_merge` dropped the football fields, so the rig showed no situation until they were carried.
- **Not yet true:** the yard line is red only when ESPN says `isRedZone`; none of the live games in the rig were in the red zone, so the red drawing is covered by the test (`CleanCard`, `Grouping`) and the mockup, not seen in the rig. A game with no ESPN possession shows no football.
- **Test:** `test_sports_live` (`CleanCard`, `Grouping`, `Properties`), `test_sports_espn` (situation, yard line, red zone, possession), `test_sports_merge` (the fields survive the merge), `test_sports_logos` (`DarkLogos`), `test_portrait` (the score font and football ship, the font keeps its file under SF).

### ISSUE-444: Umbrella's "getting ready to play" page redrawn without the card (owner, 2026-11-21, screenshot of the opening page)

- **Asked:** "this bottom section just seems a little poor, wanna remodel it to make it look beautiful?" Three mockup rounds in a day (HTML, from the owner's screenshot and real data). The owner chose option B first, asked for the purple umbrella and the file name gone and the tags cleaner, then "are those tags even needed?" and a fresh redesign; from four options he chose **centred**. (He added that it is "not really a redesign", so the next round, if he wants more, should change the page above the bar too.)
- **Done:** `pages.umbrella_ready` draws no card: the source in small capitals ("ALLDEBRID · TORRENTIO"), the stage as a large headline (`p_h2`), one thin bar (the same 20-segment bar and slide, DEC-036 and board S1, now 100 units in from each side), the numbers under it ("4 of 12 MB · 2.56 GB file"), Umbrella's slow-source note under that, and Cancel as a blue text button (`ACCENT`, 118-unit hit area). The Umbrella tile, the quality pill, the badges and the file name are gone from the page (the service still publishes them). Before a source is known it says "Looking for a source" with "UMBRELLA · YOUR ACCOUNTS" and Umbrella's own words under the bar. `umbrella_ready.stage` adds `Head` and `Sub` (the old `Line` split at the dot); for the link step `Head` is just "Getting the link…" because the service is already in the capitals line and a long name ("Real-Debrid") must not run out of the headline.
- **Checked in the desktop Kodi rig (a small script opens `source_progress.xml` with the published properties):** opening 4 of 12 MB, getting the link, a slow source with its note, and "Looking for a source". Rig screenshots stay out of Git. Not proven on the phone.
- **Owner, same day: "No ..."** (the rig screenshot showed "Getting the link from AllDebrid..."). The ellipsis is gone from every line of this page ("Getting the link", "Getting the link from X" in `Line`, "Starting the video", "Getting ready to play"); a test fails if one comes back. Real progress is covered end to end on the host: the link step, then the bytes Kodi has read (0, 4, 8 of 12 MB) filling the bar, then "Starting the video" (`test_no_dots_and_the_bar_follows_the_real_progress`). Only the phone can show that the numbers really move; the rig has no Umbrella.
- **Owner, same day: "why does the bar not load 1 at a time? I'd like a smooth loading experience, not 0 33 66 100 and 0 4 8 12"**. Cause: the opening waits for three 4 MB blocks that each land whole, and the page counted only finished blocks, so both the bar and the megabytes moved in steps of one block. Fix: the source already counts every chunk it reads (`read_bytes` in the stats), so `umbrella_ready._stage` now follows those real bytes ("0.3, 2.2, 5.4 of 12 MB", rounded down), held just under the opening's end until the blocks are all in memory (only then "Starting the video"), and the page's bar has 50 segments (2 % each) instead of 20. A source with no byte count still moves by blocks. No change to what is read or cached. Test: `test_the_bar_follows_the_bytes_read_not_only_whole_blocks`. Not proven on the phone: the size of the steps depends on how often a chunk lands (about every 0.25 s the page reads the counter).
- **A test that failed under load (kept):** `test_sports_fresh.test_a_page_never_waits_when_an_answer_is_saved` failed twice when it ran beside the 4-minute portrait test (the run took 15 s instead of 0.1 s): its fake slow ESPN gave up after 5 s and the follow-up wait was 1 s. It now waits 60 s and up to 10 s; the check it makes is unchanged.
- **Not done / known:** Cancel's focus texture is a faint capsule (it shows while the button holds focus on a touch device; if it looks like a button on the phone, the texture goes). The fanart behind the title was not exercised in the rig (no Umbrella artwork there).
- **Test:** `test_pages` (`OpeningStages.test_the_centred_opening_page`, `test_the_getting_the_link_headline...`, the stage dictionaries with `Head` and `Sub`, the page reads the new fields and no longer the removed ones).
### ISSUE-439: instant loading circle on a Continue tap, subtitles that are there without asking, fewer refused ranges (owner, 2026-11-21, after build 646)

- **Asked:** "make it start loading when i click it ... i shouldnt have time to tap it again"; "make subtitles work reliably everytime everywhere"; do the connection change if it helps speed.
- **Loading circle (host test only):** the Home screen's Continue Watching row now raises the busy circle and then plays on the tap itself (`portrait.play_now`: `ActivateWindow(busydialognocancel)`, `PlayMedia($ESCINFO[ListItem.FileNameAndPath])`), instead of waiting for the plugin to start about a second later; a modal circle also takes a second tap. The service closes it when the video starts (`subtitles_back`), the busy watchdog after 4 s if nothing opens. **Not covered yet:** other entry points (the long-press menu, library pages, the hero's Play). **Risk to check on the phone:** that the card still plays exactly as before (resume point, source choice), and that the circle never stays over a chooser (the sheet opens above it).
- **Subtitles (host tests only), three parts:** (1) **automatic:** when a video of 10 minutes or more starts, after the remembered-subtitle check, and a subtitle is wanted (Kodi's subtitle language is set to a language, or the sound is in another language than the subtitles) but no stream is usable (none in that language, only one marked forced, or cues with no length), the service starts the menu's own search, download and apply with no window (`auto_subtitles.py`, `tracks.py auto`); once per video per 6 h; "English subtitles on" or "No English subtitles found" for 2-3 s. (2) **remembered:** an Umbrella stream's subtitle is now filed under show, season and episode from Continue Watching (`subtitle_memory.known_from`), the same key the service looks it up with when Continue opens the stream again with a new link. (3) **found:** SubDL zips under another season number (ISSUE-438). `test_auto_subtitles.py`, `test_subtitle_memory.py`, `test_zip_loose.py`. **Not true yet:** this finds subtitles only when a site has them; a brand-new episode may have none for a day.
- **Fewer refused ranges:** the debrid link's simultaneous pieces 8 -> 6 and the blocks read ahead of Kodi 4 -> 2 (the read-ahead and resume blocks were the ones refused, 4.6-6.5 s, in log d8f39741). A slow link gets slightly less parallelism; check the first open on a slow server.

### ISSUE-440: a live game's page said "None yet" until "Check now" (owner, build 646, log 317cd411, 2026-11-21)

- **Seen:** the owner opened Sports 3 s after launch and a live game's page 6 s later. Crew's first scan (the jet) ran from 15:00:31 and published the first sources at 15:00:54 (prefetch: "1 source(s) ready" at 15:00:56 and :58, 35 s after launch); the page's own search had ended earlier with no source, so it showed "None yet" and only a new search (Check now) found them, at once.
- **Cause:** a page's search ends empty when the scan has not reached its game yet, and nothing started another when the scan published later. The background look for sources began 30 s after launch (build 645).
- **Fix (host tests only):** a live game's page now keeps looking by itself, every 5 s for 3 minutes (`sports_game.auto_wanted`/`auto_due`), and says "Searching for sources" meanwhile instead of "None yet"; a game that has not started keeps Remind me. The background look for sources starts 8 s after launch (was 30). `test_crew_warm.py`, `test_sports_sources_prefetch.py`.
- **Not changed:** Crew's first scan takes 25-30 s on the phone; a source cannot appear sooner than that after launch, only without a tap. Expected: a live game tapped within the first half minute shows "Searching for sources" and then the Play button by itself.
- **Correction (same day):** the first version of the page's own looking asked for a real search every 5 s; a search makes Crew walk its menus again (`crew_sources` refreshes the scan), which would have kept the phone scanning for three minutes. The page now reads what the service has published every 5 s and starts a real search only every 90 s (`AUTO_ASK`).

### ISSUE-441: faster Crew scanning and reopening (owner, 2026-11-21: "1, 2 and 4 ... same logic for umbrella streams")

- **Measured (logs aec66fce, 317cd411):** a cold walk of one league's 14 folders took 28.5 s (about 2 s per folder, one at a time: opening another Crew folder clears Crew's link table, so they cannot run side by side); later walks took 15-74 s; the first source of a walk came only at its end in the sense that the next folder was never chosen by what it held. Every search, the background prefetch's included, started a new walk when it found the published answer older than 45 s (`TTL`).
- **1. A walk answers for 3 minutes (host tests only):** `sports_jet.WALK_TTL = 180` (a finished walk that listed games is not started again by a read), and `sports_provider.crew_sources` reuses a finished walk of the same league (published with its league, `sports_jet` payload key `league`) younger than `REUSE_WALK = 180` s: a game it did not list is answered "none" at once instead of starting another walk; "Check now" (`find_sources(fresh=True)`, `request_game(fresh=True)`) always walks again. The page's own 90 s search ask (ISSUE-440) still re-walks once the answer is older than the window.
- **2 and 4. Productive folders first, and where each game was last found:** a walk saves, per league, how many games each folder held (counts fade 20 % per walk) and, per live game, the folder labels it was found under (`crew-yield.json` in the profile, games kept 6 h). The next walk visits the folder a live game was last found in first, then the folders that held most, then the rest in Crew's order (`sports_crew_routes.order_key`, `remember_walk`); partial results were already published after each folder, so the first source now comes after the first productive folder. `test_crew_memory.py`.
- **Umbrella, same idea:** any play of a title streamed through Umbrella in the last 4 hours with a place to resume (a show page's Play, Next Episode, not only Continue) reopens from its remembered link and the kept opening, skipping TMDb Helper, Umbrella's search and the Download/Stream question; never with "Choose source" and never on the continue guard's second try (`ios_watch_dialog.fast_stream`). `test_fast_stream.py`. **Risk:** a title streamed lately now skips the Download/Stream question when played again; "Choose source" still asks.
- **Not changed:** Crew's own plugin time per folder (about 2 s) and its 6 s resolver.

### ISSUE-442: build 653 logs 5ee55982 and d63069c3: Live Now pressed three times, failed streams, choppy Umbrella (owner, 2026-11-21)

- **Live Now / Sports pressed three times (first run after install):** the tap at 15:53:13 on Live Now opened its page at 15:53:19.6 (6.5 s), so it was tapped again (15:53:19.4, 15:53:26). Nothing in the app was waiting on the tap: the service's own start-up (Crew, Drive proxy, Elementum) and the background source search I had set to begin 8 s after launch (ISSUE-440) were all running; the skin was also regenerated and reloaded at 15:53:20 (`1 updated (portrait/Home.xml)`, once per update). **Fix (host tests only):** the background look begins 25 s after launch (was 8) and waits while the screen is animating or a dialog is up (`service.py busy`). Not fixed: the one-time skin reload after an update.
- **Failed streams (both plays, one source each):** Kodi asked Crew's SegmentProxy for the stream's manifest and the stream host (`edgestream3.pro`) answered HTTP 503 three times in 0.4 s, Kodi's open failed, and Kodi reported only a Stop with no start. The queue took that for the person's own cancel (`native opening stopped; queue cancelled`) and ended, although the game's queue could have tried again. **Fix (host tests only):** a Stop with no start that arrives 3 s or more after the source was handed to Kodi, or while Kodi's own failure box is up, with the queue still ours, is a failed source (a person's cancel clears the ownership first); a source that fails within 30 s is put back at the end of the queue, after the others, up to twice, with 2.5 s between (`sports_loop_router`: `LATE_STOP`, `SAME_FAST`, `SAME_RETRIES`). `test_sports_loop_router.py`. Not fixed: a host that stays at 503 stays failed; the game needs another source.
- **Choppy Umbrella:** Continue opened in 1.2 s (first picture 5.8 s after the tap, much better) through the service's cache, then every block after the opening came back `RangeRefused: Drive answered without the asked byte range` after 4-30 s and Kodi's reads waited up to 28 s (`cache read done ... took=35.20s waited=28.76s`). The debrid server answers one or two connections and refuses a crowd, even at 6 pieces; the bigger kept opening made Continue use the cache more often. The subtitle download in the same minute (`tracks: applied`) ran for 1.7 s and is not what stalled the reads. **Fix (host tests only):** links of a debrid service (`SERIAL_FAMILIES`) and of any server that refused a crowd (remembered 6 h, per server family) are read one request at a time in 2 places, with no split pieces and one block of read-ahead, as Kodi's own player reads such a link (`remote_media.Foreground.serial`). `test_cache_skip.py`. **To check on the phone:** that Continue still opens in about 6 s and now plays without stalls.
- **Subtitles for a Continue:** the menu still searched `Episode 8` with no season or episode (`tracks: search en 'Episode 8' None SNoneENone`): the Continue item's title need not equal the entry's title. **Fix (host tests only):** the video read from the very link Continue Watching remembers (turned back from the cache's address by `remote_media.original`) now counts as the same title (`tracks.continue_known`, `subtitle_memory.known_from`). `test_continue_known.py`.
- **ISSUE-442 (continued): Continue must stay fast and play smoothly (owner, 2026-11-21: "we cant sacrifice speed here"):** reading a debrid link serially through 4 MiB block requests (the first fix above) is still not how Kodi's own player reads it (one connection, streaming) and each block pays the server's 1-3 s connect, so it could stall too. In the older logs the same server was never refused while Kodi read it directly (no `RangeRefused` in the direct plays; every burst was the cache or the opening-keeping job). **Fix (host tests only):** for a serial source the service's cache keeps answering the opening from the phone's disk (Continue's 1.2 s open, first picture about 6 s) and relays everything it does not hold from ONE streaming request from where Kodi reads, to the end of what it asked (`Foreground.relay_tail`, hooked in `drive_stream`'s read loop); no read-ahead of blocks for such a source; at a kept block the relay stops and the block is served from memory. A server that does not answer the relay falls back to the block path. `test_relay_tail.py`. **Unproven on the phone:** that the server accepts the one streaming request the way it accepts Kodi's own, and that the keep-the-opening job (which still reads blocks, serially) is accepted too.

### ISSUE-443: Play on TV of a Google Drive episode freezes after about 40 s (owner log f93a3233, build 657, 2026-11-21; handoff d5f0cab)

- **Seen:** a Drive library episode (TMDb 124364 S4E4, 1080p H.264, 12.3 Mbit/s, 7727 MiB, 520 six-second segments) cast to an Apple TV on the same Wi-Fi played for about 40 s, then froze: `-16830 Media file not received in 13s (seg110.m4s)`, recovery failed, "The TV could not play the converted stream". A speed test on that Wi-Fi is fine.
- **What the log proved (device log, not reproduced here):** the TV was told to start after ONE segment (1627 ms); the phone then made each next 6 s segment in 3-9 s (about 6.4 s average) while reading Drive in many small ranges (0.3-1.7 s to the first byte each, 22 of 91 reads were retries), and sends to the TV collapsed to 1.2 Mbit/s while Drive was being read (the same segment resent from cache: 33 Mbit/s). No cache or filler line appeared at all.
- **Cause, as far as host work can say:** (C) no cushion before the TV started; (D) Drive reads and TV sends share one radio and nothing ordered them; (A, unproven) the service answered Kodi's `Player.OnStop` by wiping the playback cache and stopping the filler, which can fire when Play on TV takes Kodi's player over. Honest note: the log has no "Drive cache: cleared" line either, so A may not have been what happened; the changes below do not depend on it, and the new log lines will say. (B) the native reader's small 1 MiB helper requests and (E) the slow native recovery are NOT changed (they need a new framework revision and the owner's request).
- **Done (Python only, host-tested):** `cast_cache.py` (new). (1) `Keep`: the service no longer clears the cache on a stop while a TV is starting or fed (`airplay.starting/busy/serve_busy`); it clears once when the cast is over and Kodi plays nothing. (2) `drive_cache.Filler`: says once per file why it is not filling ("not on Wi-Fi", "free space: N MB free, M MB needed"), says "filling X from N MB, the whole file / a window of N MB ahead" when it starts, and can report the bytes in a row on the phone from the readers' position (`ahead_bytes`, `state`). (3) The proxy's new `/cushion/<id>/<name>?at=<byte>` starts or moves the filler there and answers `{ahead, state, size}`; `cast.py` calls it before the native start and waits until about 25 s of the video are on the phone (`CUSHION_SECONDS`, the bytes follow the file's own bitrate, 24-240 MB), at most 45 s (`CUSHION_LIMIT`), cancellable, and starts the TV at once when the proxy is not filling (cellular, no room, no cache) or fails. (4) `Pacing`: once the cushion is three times full the filler rests so the TV link has the radio, and goes on below one and a half (never starved below that). (5) One line every 30 s while a TV is fed: segment made vs asked for, the lead in seconds, the average make time per 6 s segment, the sends' rate and the slowest, and the filler's state (`Kodi iOS Play on TV: cast: ...`; no URL, id or token).
- **Test:** `test_cast_cache` (Keep, the proxy hand-off with a disk cache and filler, the cushion endpoint and wait against the real proxy, pacing, the diagnostic line, the wiring), `test_drive_cache` (`FillerForTheTv`).
- **Not proven:** everything about the phone. The owner test is a 10-minute cast of a 12+ Mbit/s Drive episode with the TV on Wi-Fi and on Ethernet; the log must show a cushion above 10 s throughout, no -16830 and sends well under the segment length. If the 30 s lines still show production slower than real time with the filler ahead, the next step is B (native).

- **Second log, 4f1691fe (6 min, 5 casts, none played steadily), the review:** Kodi's own playback of the episode was fine (open 2.6 s, first picture 3.4 s). Casting: nothing is converted ahead of time for an H.264 file (the picture is copied and each 6 s segment is repackaged on demand); of 25 video segments made on demand only about 8 were made faster than real time (some took 9-22 s); 456 Drive range reads in 6 min, median 0.47 s to the first byte, 14 % slower than 0.8 s, worst 8.2 s, 15 % retried; sends to the TV ran 15-30 Mbit/s when nothing else was happening and 3-8 Mbit/s while the phone was also reading; 43 x -12889 "no response in 6 s", 4 x -16830, 17 x "Receiver write failed". The first 4 segments after a cast start were instant only because Kodi had read that part; the 5th and later went to Drive. Every TV jump (7 seen) restarted at a cold place (segment 54: 14 s, 76: 17 s). After a slow segment 175 (22 s) the native layer took the TV's missing video requests for "sound only" and restarted in compat mode (re-encode), which then converted a segment in 1.8 s: the encoder is not the slow part. The phone's address changed from 192.168.1.3 to 192.168.1.24 between two attempts 34 s apart (a router reservation would rule that out).
- **Added after that log (Python, host-tested):** the cushion check also needs the audio stretch ahead, not only the picture (the picture and audio lie about 60 MB apart in an MP4: `Filler.cushion_ready`, the proxy's `ready` answer, `need=`); after every TV jump ("seek: the receiver jumped from segment N to M (T s)") the proxy is told to fill at the new place at once (`cast_cache.Reseek`, armed by `cast.py`, fed by `airplay.activity`, disarmed when the cast ends). **Not changed:** the native "sound only, restart in compat mode" decision (`kr_remux.c`) still takes a slow source for a TV that cannot decode the picture; with the cushion it should happen less, but changing it needs a new framework revision (r73) and the owner's request.

### ISSUE-445: Continue on an Umbrella show took 36 s and failed; the Sports hub took 5.5 s; an NBA game showed no streams (owner, build 659, log 4a05fc8f, 2026-11-21)

- **Continue (device log):** the show had last played more than 4 h earlier, so `fast_stream` declined ("the remembered link is older than 4 h") and the normal way ran: TMDb Helper's player dialog 4.7 s (21:04:10.5 to 15.2), Umbrella resolving 3 s, the cache route skipped ("this server did not answer the cache in time a moment ago", route direct), then Kodi waited 27.6 s for the AllDebrid server's first bytes ("Creating Demuxer" 21:04:21.7, "Open - probe limits" 21:04:49.3), opened the streams and read end-of-file at once: the open took 36.7 s and ended without playing. Two parts: the 4 h limit was too short for a link that `_link_alive` can check (**fixed: 24 h**, `STREAM_FRESH`; a dead link still goes the normal way after the probe), and a slow debrid server (27 s to the first byte, then an empty file) which the app cannot speed up (a different source is the only answer; not changed).
- **Elapsed time (asked):** the Umbrella opening page now shows how long the open has taken under the line with the file's size ("7 s", then "1:05" from a minute on; `IOSReady.Elapsed`, counted from when Umbrella's window appears; `umbrella_ready.elapsed_text`, `watch`).
- **Sports hub 5.4-5.8 s (device log):** three opens, three first frames from the saved answer at 5551, 5776 and 5407 ms, while the same draw takes about 55 ms on a computer (file read 47 ms, load 6 ms). The log does not say where the time goes (a second open 0.4 s after the first took 221 ms in the build 657 log, so it is what a new script start costs, or the Crew walks running at the same time; both unproven). **Not fixed.** The hub's first-frame line now names each step (window, provider, saved answer, load, edit state, upcoming, next game, properties) so the next log decides.
- **NBA game without streams (device log):** the owner opened an NCAAF game first, so Crew's search was scoped to NCAAF (schedule "2 live, 0 upcoming"); the NBA game's page started its own search at 21:04:01 (6.4 s for the schedule, then Crew's menus) and the streams arrived at 21:04:49, 48 s after the tap, by which time the owner had left the page after 5 s. The prefetch had said "NBA ... no source yet" at 21:03:55. This is the Sports source search (ISSUE-440 and 441 are on the same code); **not changed here**: the first search for a league takes about 50 s, so streams only show once that has finished and the page is still open (or the game is opened again after).
- **Test:** `test_pages` (the elapsed time published and drawn under the size, a link tried for a day), `test_sports_instant` (the first-frame line names its steps).

### ISSUE-446: Formula 1 listed as having no streams while the Las Vegas Grand Prix was on (owner, 2026-11-21)

- **Seen:** "it says there is no f1 streams and there is? vegas is rn". The build 659 log shows the Crew routes found for "LPGA, NBA, NCAAB, NCAAF, NHL, PGA" and no F1.
- **Cause (checked against ESPN's own answer, host):** a race weekend is one ESPN event whose status is `post / STATUS_FINAL` from the first practice on (its date is the first session's, 2026-11-20), while its Race competition is `in / STATUS_IN_PROGRESS`. `sports_espn.parse_events` read only the event's status, counted the weekend as finished and never listed it, so F1 was never "live in the schedule" and no F1 sources were looked for.
- **Fix:** for an event league the sessions decide: one in progress makes the weekend live with that session as its clock ("Race", "Qualifying", "Practice 1"); with every earlier session done and one still to come it is upcoming at that session's time; all done is finished. Golf is unchanged (its event status is right). Live Now draws an event row (no two teams): the title and the session, centred (`g.N.et`).
- **Checked (host, live ESPN answer):** F1 now parses as live with clock "Race" and is the ninth game; PGA and LPGA rows draw as event rows in the desktop Kodi rig. Whether Crew has F1 streams that match is not known: the search now looks for them, which it did not before. Not proven on the phone.
- **Test:** `test_sports_espn.test_a_race_weekend_is_live_while_its_race_is_in_progress` (the real answer's shape, qualifying, all sessions done, a race still to come), `test_sports_live.EventRow`.

### ISSUE-447: 27.6 s of nothing before an Umbrella stream, and 48 s before an NBA game's streams (owner, build 659, log 4a05fc8f, 2026-11-21: "streams for games should appear much faster ... under 5 or 10 seconds", "27 seconds of doing nothing, that's why it's taking so long")

- **The 27.6 s (device log):** the opening went direct ("this server did not answer the cache in time a moment ago", `origin_answered=no`) and Kodi was handed a link whose server was not answering. `remote_media` remembers a slow server FAMILY for six hours (`SLOW_SKIP`) and plays every link of it blind and direct. Kodi's own network timeouts then waited 27.6 s for the first byte and the file read as empty.
- **Fix (`remote_media.preflight`, `first_byte`):** a link that is about to be played directly (the slow-server shortcut and the cache that did not answer) is first asked for one byte over two connections at once, for at most 5 s (`PREFLIGHT`). An answer: the link plays as before. No answer: the same file is unlocked again with the account's token (`umbrella_recovery.renew`: a debrid service serves it from another node) and that link is asked the same way; an answer uses the new link. No answer from either, no unlock possible, or an unlock that fails: the old link plays as before. Worst case 5 s + the unlock + 5 s instead of 27.6 s and an empty file; the common case adds one round trip. Log lines say what happened and carry no address. Outside Kodi nothing is asked of the network.
- **Not fixed, said plainly:** a server that really takes 27 s for its first byte on every node is still slow; the elapsed time under the size (ISSUE-445) shows it. A different source (Umbrella's next) would be the only answer, and Umbrella's own source loop is not ours to change from here.
- **The 48 s for an NBA game's streams (device log):** the background look searched ONE game per minute (`EVERY = 60`) in the order of their start times; after launch the first game took 15 s, the next look came a minute later, so the NBA game had "no source yet" at 21:03:55 and its own search (21:04:01) found the stream only 48 s later (Crew's NBA menus are deep). **Changed (`sports_sources_prefetch`):** the FIRST pass over the live games runs back to back (the next game 3 s after the last, `AFTER_SEARCH`), the leagues people open first go first (NFL, NBA, NHL, MLB, NCAAF, NCAAB ...); a game searched again (no source last time) keeps the usual minute and its retry is now 5 minutes (was 3), so the phone does not scan all day. A parallel scan was NOT built: Crew's collector reads one league at a time and walks 18 pages per league, so several at once is more heat and the same Crew limit; a single back-to-back pass at launch costs the same work as before, done sooner. That makes every live game's streams ready within a few minutes of launch instead of one game a minute; it does NOT make a first-ever search faster (Crew walks 18 folders of provider pages, 15-66 s). A game that already has its streams from the look opens with them at once. **Under 10 s for a game nobody searched yet is not achieved**; the streams do show up one after another while the page is open (the first one 8-11 s into a walk in the log).
- **Test:** `test_remote_media.Preflight` (first answer of several connections, the limit, the header suffix, the unlock-again failover and its failures, no address in a log line, both direct routes use it), `test_sports_sources_prefetch.BackToBack` (the big leagues first, the next game within seconds, the usual minute when nothing is left).

### ISSUE-448: Play on TV stuck on "preparing" for 25-33 s before it started (owner, build 659, log a8919a24, 2026-11-22; a regression of ISSUE-443's cushion wait)

- **Seen:** "airplay didnt connect to tv it seems it was stuck on preparing". Two casts, each ended by the owner's Stop on the banner after 33 s and 25 s: `Play on TV: cushion: canceled, 64 of 24 MB ahead after 33 s` and `96 of 24 MB ahead after 25 s`.
- **Cause (my own change):** the picture's cushion was there almost at once (24 MB needed, 64-96 MB ahead) but the wait also required every other stretch the filler follows (the audio, and an MP4's index near the end of the file) to have 12 MB ahead; a stretch with less than 12 MB left to the end of the file can never get it, so the check stayed false until the owner gave up. (The rest worked: the filler said "filling ... the whole file", "96 MB ahead, resting so the TV link has the radio".)
- **Fix:** a stretch needs at most what is left to the end of the file (`Filler.cushion_ready`); once the picture's cushion is there the audio stretch gets `AUDIO_GRACE` = 4 s and the TV starts anyway; the longest wait is 20 s (was 45). Test: `test_cast_cache.AudioStretchAndSeek` (a stretch near the end, the grace).
- **Lesson kept:** a wait before a start needs an exit that does not depend on the thing it waits for; the host test covered "audio thin" but not "audio can never fill".


## ISSUE-449: Continue from Umbrella failed twice, 28 s stall although the link "answered" (build 660, log bbd44482)
- Symptom: owner continued two Umbrella streams, both failed. Log: preflight answered in 1.4 s, Kodi opened the same link and got no data for ~29.6 s; the continue guard fired at 25 s, the normal route then took ~17 s more and the second try ended unfinished.
- Root cause: the preflight asked for one byte (`Range: bytes=0-0`). A debrid node can answer that at once and then stall on a real read, so the check proved nothing. The guard limit (25 s) also made every failed open cost almost as long as Kodi's own 30 s.
- Fix: the preflight now has to receive 32 KB of the real start of the file within 6 s (two connections, first to deliver counts); headers alone do not count. Continue guard limit 25 s → 14 s.
- Retest: test_remote_media (headers without data give None, Range is the 64 KB read), test_continue_guard, test_slowdown pass on the host.
- Regression protection: `Preflight.test_headers_without_data_do_not_count`. Device result unproven; needs the owner's phone.

## ISSUE-450: Subtitles on but not lined up after a Continue fallback (build 660, log dc74b76b)
- Symptom: Umbrella episode continued, English subtitles applied automatically but did not line up with the speech.
- Findings: speech recognition did not fail. The log has no "speech check:" line at all; it needs 20-60 s to listen and the file was closed 43 s after the subtitle was applied. The real fault: the subtitle search ran as `search en 'Episode 8' None SNoneENone`, with no show, season or episode, so SubDL returned its one guess for that title ("speech not checked").
- Root cause: the Continue guard fell back to a new link, and `continue_known` matched only by title or by the old link. The entry's title was the episode's own name and the link was new, so nothing matched and the show/season/episode (known from the play URL: tmdb 73223 S2E8) was dropped.
- Fix: `continue_known` also accepts a Continue entry (no older than the existing 6 h) when Kodi's item says "Episode N" and the entry's episode is N.
- Retest: `test_continue_known` (6 tests) pass on host. Regression protection: `test_a_recent_start_of_episode_n_counts_after_a_fallback_link`. Device unproven.
- Not changed: a speech check that is still listening when playback closes simply never reports; a note for later if the owner wants it shortened.
- Added a log line when the speech check starts listening, so the next log shows whether it finished and what it heard. Which SubDL file was fetched (id 301379-1803985) cannot be told from the log; it was a title-only match for 'Episode 8', so the content was most likely another episode or show, not a timing offset of the right one.

## ISSUE-451: Subtitles still for another show after build 662 (log 3173e72b)
- Symptom: build 662, Continue on Black Clover S2E8: English subtitles about "Toothless" (a dragon cartoon). Same SubDL file as build 660 (301379-1803985); search was still `'Episode 8' None SNoneENone`.
- Root cause: `Window.played()` read the `KodiIOS.Playing` property first; when it was unset, `float(known.get('t') or 0)` made the entry "older than 6 h" and the method returned {} at once, so Continue's own record (`continue_known`, which knows tmdb 73223 S2E8) was never consulted. ISSUE-450's change sat behind that early return, which is why it did nothing. Older fixes (builds 639/653) were behind the same line.
- Fix: new `playing_known()` returns {} for an unset or stale property and lets the lookup go on to `continue_known`. A search whose title is only an episode label ('Episode 8', 'E08') with no show, season, episode or TMDb id is skipped ("search skipped") rather than guessed: no subtitle beats another show's.
- Retest: `test_continue_known` (9 tests). Regression protection: `test_an_unset_playing_property_does_not_end_the_lookup`, `test_the_search_asks_continue_after_the_property`, `test_a_bare_episode_label_names_no_show`. Device unproven.
- Also seen: Continue itself opened in 9.3 s (fast remembered link, route=cache). The speech check cannot run on this video: `not listening (sound jpn, subtitles en)`, Japanese sound with English subtitles, so Auto sync by speech cannot work for dubbed or foreign-audio titles; the planned Auto sync button must say so.

## ISSUE-452: Auto sync for subtitles (owner, 2026-11-22: "a button in settings to auto sync ... it will immediately sync subtitles")
- Added: Subtitles › More › Auto sync (control 9407) under Timing; mockup docs/design/subtitles-autosync-mockup.html (mockup, not Kodi). Tap: listens to the video (the same speech check as after a download, listened again), finds the offset of the downloaded subtitle that is on and moves the file at once. Lines shown: Listening / Moved N s later|earlier / Already in sync / These subtitles are for another video / Not enough speech heard / The sound is in another language than the subtitles / Turn on a downloaded subtitle first.
- Limits (stated in the log and on the row): only a downloaded subtitle can be moved; the sound must be in the subtitle language (a Japanese dub with English subtitles cannot be listened to, log 3173e72b).
- Tests: `test_speech_check.AutoSync` (5), `test_subtitle_hold` (control id shared and unique, states, handler). Not seen in Kodi yet (no rig screenshot) and device unproven.

## ISSUE-453: Continue looked idle while it opened, taps restarted it, then the guard cut a working open (build 663, log 63e92ff2)
- Symptom (owner): Continuing an Umbrella stream felt glitchy and laggy: it seemed to start, then nothing showed; pages could be switched and scrolled; no circle stopped further taps.
- Log timeline: Continue tap 13:13:32.7 (remembered link, `route` direct) → DialogBusy up only ~1 s (10 samples at 13:13:33.3: Kodi's own busy dialog closes when the plugin answers) → Home at 16 fps while the demuxer opened (Creating Demuxer 13:13:34.6, probe done 13:13:53.9, ~19 s) → the owner tapped Continue again 13:13:42 (second OpenFile 13:13:43.5, the guard's clock restarted) → taps on Hub/Settings → streams ready 13:13:54.5 → guard fired 13:13:57.6 ("did not open (14 s)") three seconds after the streams were up and CloseFile cut a working open → fallback through Umbrella took 26.9 s to the first picture (preflight 1.3 s, yet Kodi's demuxer open took another ~18 s: this file/server is slow to open on any link).
- Root causes: (1) nothing showed or blocked while the video opened after Kodi's own circle closed; a second tap restarted the open; (2) the guard's 14 s limit (ISSUE-449) counted from the last tap and ignored that Kodi already had the streams (resume seek still running).
- Fix: a loading circle (`continue_guard.Circle`) is kept up while `KodiIOS.ContinueOpening` is set (set by the Continue row's tap, fast_stream, and the guard's fallback) until a picture plays, the failure box shows or 60 s pass; it is modal, so taps wait; the busy watchdog leaves it alone. The guard waits up to 35 s instead of 14 s when Kodi has a video stream (`Player.HasVideo`) but no picture yet.
- Retest: `test_continue_guard.OpenedAndCircle` (6), `test_play_now`, `test_busy_watchdog`, `test_fast_stream`, `test_resume_cache`, `test_pages` pass on host. Device unproven.
- Not fixed: the ~19-21 s demuxer open on this file's links (preflight reads the start fine; cause unknown, perhaps the file's index at its end or a slow node); needs a log with the new circle and the stream-opening lines.

## ISSUE-454: Sports pages 2-5 s to open (owner, 2026-11-22, log 71e31b26, build 663)
- Symptom: Sports hub ~5 s, Upcoming 3-5 s, Leagues ~2 s, Live Now 3-5 s; "i want it instant like all other pages".
- Log findings: (1) the Sports tap was 5 s after a cold launch (startup services, System.FPS 4.7): click 13:46:39.77 → hub first frame 13:46:42.0, of which the hub's own work was 631 ms (provider 604); build 659's 5.5 s hub is gone when nothing competes. (2) The Crew/jet source search ran back to back through every page switch (jet lines 13:46:52, 53.8, 55.5, 57.2, 59.5, 01.4 on one thread, plus `Schedule [gstream24]/[volokit]` scraper errors): click→window load was Upcoming 2.3 s, Leagues 0.5 s, Live 0.27 s while it ran. The service's `busy()` only held it off when System.FPS ≥ 15, which a tap on a mostly still page never reaches. (3) Live Now drew nothing until a thread had loaded the games AND `with_crests` had fetched every unseen team's logo (an 8 s timeout each, probes one after another), so its first frame was empty/"Updating" for seconds whenever a new game appeared.
- Fix: (a) the prefetch search also waits until nothing has touched the screen for 5 s (`System.IdleTime(5)`); (b) Live Now draws the saved answer before the window opens (`first_frame`, as the hub does), with only the crests already on the phone (`_offline`), and the logos still to be fetched follow; (c) every sports page logs `page: <name>: first frame in N ms (steps)` (`page_clock.py`) so the next log shows where any remaining time goes.
- Retest: `test_page_clock` (5), `test_sports_live` (46, incl. `FirstFrame`) and all other sports tests pass on host. Device unproven; I could not measure the phone from the log beyond the step times above.
- Not done: pages are still separate RunScript processes (each re-imports its modules); if the new timing lines show that import time dominates, the next step is one long-lived process for the Sports pages.

## ISSUE-455: Elementum's DHT announced the phone at every launch although AllDebrid does all downloading (owner, 2026-11-23)
- Evidence: 119 logs since 6 Nov show `Starting DHT...` 124 times and not one "Adding torrent"; since the AllDebrid→Drive route (6 Nov) every selected torrent is consumed by `elementum_cloud.route`.
- Fix: `phone_housekeeping` sets Elementum's `disable_dht` once (marker `elementum_dht`); effective at the next engine start; a setting the owner turns back on stays on. `test_updates_calibration` covers it.
- Built (owner approved the mockup, 2026-11-23): `torrent_prompt.py` + a gate in `elementum_download.follow` right where our code would hand a request to Elementum's own engine (never reached while `elementum_cloud.route` consumes the pick). Standard Kodi confirmation (DialogConfirm, styled as the app's alert): Cancel first and default; the status line follows `vpn_hint`.
- VPN hint (`vpn_hint.py`): the interface that holds the address the phone uses to reach the internet (cache_tune.local_address) is a tunnel (`utunN`) -> "A VPN looks active"; Wi-Fi/cellular -> "No VPN detected"; unknown -> "Cannot tell". Evidence: of 119 logs the build-664 log with Proton on is the only one whose link kind reads "other"; all others wifi/cellular. The service logs `vpn check: ...; default route via <name>; tunnel interfaces: <names>` whenever it changes (names only). A hint, not a proof; LocalDevVPN is expected to read "no VPN" (its tunnel does not take the default route; to be confirmed from a log).
- Tests: `test_torrent_prompt` (13).

## ISSUE-456: a cast that sat still was detected and ignored for 2 min 40 s (owner, 2026-11-23, logs 72c1c0ac / 7f62ba9c, build 664)
- Evidence: first start 18:36: "playing" after 8.5 s, then the TV's position stayed at 1101.4 s (`player: 5s/15s/60s/120s: at 1101.4 s`, `time_control` 2 = waiting) while the TV pulled video at ~0.2 MB/s (segment 183, 3.8 MB, 16.6 s; segment 184, 4.7 MB, 19.8 s; `Receiver write failed (32)` after exactly 128 KB). The service logged `unexpected_stop: buffering_without_progress` at 18:36:49, 18:37:49 and 18:38:49 and did nothing until the TV dropped (`receiver_route_ended` 18:39:19). Second start 18:41 (phone address 192.168.1.3 → .24): "playing" after 5.5 s, segments 2-9 MB/s (segment 184: 517 ms). Same TV, same file, same code. Drive reads were ~0 during the stalled minutes, so the Drive downloader was not the cause of the stall; what made the first connection slow is not visible in the logs.
- Fix: `airplay_recover.py` (watched from `airplay_diagnostics.watch` every 5 s): TV connected (`external`), waiting (`time_control` 2 or buffer empty) and the position unmoved for 25 s → `airplay.restart` (close Apple's player, start where the TV was, play the same stream again; the source and title are remembered in memory by `cast.py` before `kodi_airplay_play`); if it still does not move within 30 s → one message ("The TV is not receiving the video fast enough…", notification + the problems list), never a loop. A restart that moves for 60 s counts as fixed. No-op when nothing is remembered.
- Retest: `test_airplay_recover` (12) on the host, with sequences shaped like the two logs. DEVICE UNPROVEN: whether closing and replaying while the TV route is active reconnects the TV by itself is not known from the logs.
- Not changed: the phone's own player prefetches 9 segments before the TV connects and the producer works ahead (segment 193: 2.3 s wasted); fixing that is in the native framework.

## ISSUE-457: Apple-style scrubber in the video controls (owner-approved mockup docs/design/player-scrubber-mockup.html, 2026-11-23)
- Changed (`player_osd.py`): the 10-unit bar with a white knob became a 16-unit fully rounded bar with no knob at rest (two progress controls: thin while the slider is not focused, 32 units under the finger, since the slider has focus while dragged); the slider's knob is clear; elapsed time under the left end and the time left under the right end (70 % white, white while dragging); the right time is a button (7132) that toggles total length (`ios_osd_total`); Info and Continue Watching moved from top 936 to 970 to make room. Everything else in the controls is untouched.
- Not in this version (stated to the owner): the frame preview above the finger (Kodi has no thumbnails to show) and the minute haptic (needs a native call).
- Tests: `test_player_scrubber` (7) plus test_portrait, test_customisation, test_next_episode, test_review_low_items, test_track_menu. The desktop rig plays no video, so the controls were NOT seen rendered: layout and the rounded ends (dot.png with border = half the height) need a look on the phone.

## ISSUE-458: Sports pages slow, dead controls after a drag, Continue cut a working open (owner, 2026-11-23, build 669, logs e38980c3 / 17c3bb8b)
- Sports: `EspnProvider._load` held the provider state lock for the whole ESPN fetch, so every page that only wanted the saved snapshot waited behind a background refresh. Fix: the state lock is held only to read/write the snapshot; a separate `fetch_lock` serialises fetches; a read with a saved snapshot returns it at once while a fetch runs. Test: `scripts/test_sports_nonblocking.py` (4; the old code hangs).
- Controls: dragging the scrubber slider did not re-arm the 3 s close timer, so the controls closed under the finger and the next taps landed in the closing animation (`ignoring action 504/107/100, because topmost modal dialog closing animation is running`). The slider now holds the timer at 15 s while focused and re-arms the normal one on release. Device-unproven; the rig cannot drag.
- Continue: the guard cut a working 19 s open at 14 s, then the normal way took 30+ s. `LIMIT` 14 -> 30 s, `LIMIT_OPENED` 35 -> 45 s; remembered link kept 72 h (`STREAM_FRESH`; `_link_alive` still rejects a dead link). The stored link was not the cause (it opened in about 19 s).

## ISSUE-459: Continue's remembered link: warm the last 3, cut only a refused link (owner, 2026-11-23, logs 63e92ff2 / 17c3bb8b)
- Measured (all logs): fastest Umbrella open 10.4 s to the first picture (streams ready 7.4 s, then 3 s); the remembered link had streams ready in 11.1 s (63e92ff2) and was cut at 14 s, 3 s before its picture. The wait is Kodi opening the debrid link, not Umbrella's lookup.
- Fix: (1) `continue_guard.Probe` asks the server (range 0-0, in a thread) whether the link is refused; two refusals cut the open after 8 s, a slow or busy answer never does, the 30 s / 45 s limits stay for the rest. (2) `link_warm.watch` (service): the first 3 Continue Watching rows with a remembered Umbrella link under 72 h old, a place to resume, are read at their start, end and resume point (about 1.3 MB each) every 10 min, never while a video plays or opens, a link at most once per 25 min; the log says reads and seconds, never an address. Links are kept 72 h (STREAM_FRESH).
- Tests: `scripts/test_link_warm_recent.py` (14). Device-unproven: whether warming shortens the open is for the next log to show (`link warm:` lines, then the open timing line).

## ISSUE-460: the kept opening covers the last 3 titles, not 1 (owner, 2026-11-23)
- `resume_cache` kept the opening (start, end, resume point; up to 12 x 4 MiB blocks) of only the last stream. Each link now has its own folder (named by a hash), the newest 3 are kept (at most 144 MiB, usually far less), the oldest goes when a fourth is saved or after 72 h, and the one-title files of builds 623-669 are removed. Continue's rule is unchanged: the cache route is used only for a link whose capture finished.
- Tests: `scripts/test_resume_cache.py` (16, 5 new for the three-title rules). Device-unproven.

## ISSUE-461: the warm-up read the wrong place for the resume point (found by measuring in the desktop rig, 2026-11-23)
- Measured with Kodi 21.3 in the rig on an 81 MiB Matroska file resumed at 30 s: Kodi reads its start, its last 128 KB, then seeks to byte 39427588 (the cue at 28 s). `link_warm` guessed that point as the share of the file (42.2 MB): 2.8 MB away, outside its 512 KB read, so the part Kodi needs was never warmed.
- Fix: `link_warm.resume_offset` reads the Segment start and time scale from the file's start and the Cues from its end (both already read), and warms the cluster Kodi seeks to (1 MB there); the guess is the fallback for files that are not Matroska. It returns 39427588 for this file, exactly Kodi's own read.
- Rig results (a local server standing in for a debrid link: 0.3 s to connect, 1.5 MB/s, and 2 s the first time any 4 MiB part is read; a MODEL, not AllDebrid): Kodi's open to the resume point took 8.3 s untouched, 2.2 s after the warm-up (every one of Kodi's four reads then hit a warmed part). `resume_cache` on a server of 1.2 s connect and 1.5 MB/s: the opening reads took 5.4 s cold, 0.0 s from the kept blocks. Whether AllDebrid's servers behave like the model is for the next device log to show (`link warm:` lines, then the open timing).
- Tests: `scripts/test_link_warm_recent.py` (16, with the cue lookup on a built Matroska index).

## ISSUE-462: the seek bar did not follow the finger, no card, no times under it (owner, 2026-11-23, build 671, log 1b574ee3 and his Apple reference screenshot)
- Reproduced in the desktop rig with real mouse presses and drags (xdotool; `Player.Open` of an 81 MiB MKV): mid-drag at 58 % the white fill stayed at 21 %, the elapsed/remaining times stayed put, the thick bar never showed (`Control.HasFocus(7131)` is false under a drag) and there was no card. Kodi's progress info is the player's position; the slider's dragged value reached nothing but the slider's own invisible knob.
- Skin alone cannot fix it: Kodi cannot size or place a control by a value, and a progress control reads only whole percents from player info (tried in the rig: `Control.GetLabel`, a window property, `$INFO` in a width: all show nothing or 100 %).
- Fix, native (patch, rig-built and tested; needs the next Kodi executable, r36): `xbmc/guilib/IOSScrub.h` holds the dragged percent (or the target until the seek lands). The slider publishes it while dragging and while a seek is pending; `Player.Progress`, `Player.SeekTime`, `Player.SeekOffset`, `Player.TimeRemaining` and `Player.Seeking` follow it; the progress control draws the exact float percent, so the fill ends at the finger to the pixel; the controls' close timer (`osd_timeout`) is renewed while dragging; a seek to where the progress already is lands after 0.6 s instead of holding the bar for 15 s.
- Fix, skin: thick bar and white times while `Player.Seeking`; the elapsed time under the finger on the left, time left on the right; the card of the mockup (rounded white outline, time under the finger, the jump from where you were, `+14:51`) with one copy per whole percent at that share of the bar's width (`left` in percent), kept between 12 and 88 %.
- Rig result (landscape 1311 x 603, real drags): the fill ended within 2 px of the finger at 11 positions, forward and back; `SeekTime` and `SeekOffset` matched the finger to the second; the card followed; after release the bar stayed at the target and the card went when the seek landed; pause, play and +10 worked by mouse click, including right after a drag; a 7 s slow drag renewed the 3 s close timer four times.
- The card holds no picture of the frame: Kodi has no thumbnails of a stream and none can be made from a debrid link without reading it. The title's artwork shows inside it when the player has some.
- Not proven: a finger on the phone (the rig uses mouse events; the phone's touch gestures reach the same slider code through `ACTION_GESTURE_*`, covered by `scripts/test_seek_release.py`, 48 scenarios). Until the new executable is built, a build with these skin files shows the controls without the thick bar and card (nothing is lost).
- Tests: `scripts/test_player_scrubber.py` (10), `scripts/test_seek_release.py` (48, compiles Kodi's real slider code from the patch).

## ISSUE-463: Continue took 22-23 s on mobile data and the warm-up and the kept opening did nothing there (owner, 2026-11-23, build 671, log 1b574ee3)
- The log: `vpn check: no VPN; default route via pdp_ip0` (mobile data). Both Continues opened in 22.6 s and 23.4 s: Kodi's demuxer sat about 20 s in "Creating Demuxer" on the debrid link (its open is four requests, one after another: the whole file, the whole file again, the file's end, the resume point, each a new connection). The warm-up ran (3 reads in 4.3 s, 4.5 s) and did not change it; the opening cache kept nothing (Wi-Fi only, and the log did not say so).
- Changes: the warm-up now waits for Wi-Fi (it moved 1.3 MB x 3 over mobile data every 25 minutes); the opening cache says why it kept nothing. The warm-up's value on Wi-Fi is unproven; the log of a Wi-Fi Continue is what decides.
- Open: on mobile data the open is slow because each of Kodi's four requests pays the connection cost; the fix that removes them (a local relay with one kept connection) is what build 622 tried and the server refused. Needs a log from Wi-Fi first.

## ISSUE-464: the buffer bar sat at 0 and jumped to 100 (owner, 2026-11-23: "keep the current buffer bar, tweak it so it doesn't just jump to 100 and have it actually load")
- The ring mockup (docs/design/player-buffering-mockup.html) was rejected by the owner; the bar stays.
- Measured in the desktop rig (a server holding any new 4 MiB region back 5 s; the bar forced on to watch it): `Player.CacheLevel` stays 0 for the whole stall, then arrives in a burst (15 -> 71 -> 86 -> 98 within 0.3 s) because the data lands in blocks. The bar followed it step for step: empty, then full, never seen moving. (In a plain seek Kodi does not even set `Player.Caching`; in a stall of the playing stream it does.)
- Fix: (1) native (patch, r36): a progress control bound to `Player.CacheLevel` runs up to the level at 125 % a second (a full queue in 0.8 s) and follows a falling level at once (a new stall starts empty); (2) skin: no percentage in the words (it jumped the same way) - "Buffering"; a blue pulse at the bar's start while the level is under 4 % (it shows it is working while empty); the words and bar stay 0.5 s after the buffer is full and fade (a Hidden animation), so the fill is seen finishing.
- Rig result: bar 11 -> 22 -> 36 -> 56 -> 74 -> 95 -> 98 over 0.7 s for the same burst; pulse visible while empty; after the condition ended the bar stayed about 0.8 s and faded by 1.5 s.
- Not proven: a stall on the phone. The data is bursty by nature (4 MiB blocks), so the bar can only move as fast as data arrives: the easing makes the burst visible, it cannot invent progress in the empty seconds before it. Needs r36 (see ISSUE-462) to reach the phone; until then the skin shows "Buffering" with the old bar.
- Tests: `scripts/test_player_scrubber.py` (12), `scripts/test_portrait.py` (label), `scripts/test_smooth_pages.py` (lock names r36 and this patch).

## ISSUE-465: Sports opened 1-2 s late and Umbrella was slow at points (owner, 2026-11-23, build 676, log d78de521, on Wi-Fi)
- Umbrella: the first Continue after the app opened took 24.4 s to a picture (open 20.9 s); two later ones 6.6 s and 7.2 s (open 2.7 s). The two fast ones are exactly the ones whose opening was kept on the phone (`resume cache: 10 kept blocks given to the opening`). The link warm-up (3 reads of 1.3 MB per link, 4.3 s) did nothing: it ran at 12:13:17 and the open at 12:13:53 still took 20.9 s. So "slow at points" = a title with no kept opening.
- Sports: tapped at 12:21:34.8, four seconds after leaving a video; first frame 1238 ms (load 1163 ms), the Home list scrolled at 16 fps. At 12:13:31, nothing in the background: 153 ms. The difference is the opening cache saving 40 MB in the background at 12:21:30-12:21:40, ten blocks at once (ten threads, each waking 20 times a second to ask the gate for a place, on a phone whose Python is shared with Kodi's own add-ons).
- Fix: (1) `resume_cache.capture` reads two blocks at a time, the file's start and end first, then the resume point, and starts a block only after 6 s without a touch (`xbmc.getGlobalIdleTime`); it stops at once when a video opens. Same 40 MB for the same title, about a third less Python CPU on the desktop (1.28 s -> 0.87 s for 10 blocks); the real change is that nothing starts while a finger is on the screen. (2) The warm-up loop now keeps the opening of the first 3 Continue Watching titles (Wi-Fi, nothing playing, screen untouched) instead of reading 1.3 MB of each, so the first Continue of a recent title opens like the second (about 6.6 s instead of 24 s). At most 3 titles, 144 MiB.
- Not proven: the phone. The desktop cannot show the eight-fold slowdown (its Python is fast), so the Sports result is for the next log: the hub's `first frame` line after leaving a video should read about 150 ms again.
- Also in the log: six `OutputPicture - timeout waiting for buffer` during the 24 s playback (a link with nothing kept), one `CDVDAudio timeout` at the end of the third playback; the Sports game-facts page scrolled at 22 fps and the upcoming page at 42 (not investigated).

## ISSUE-466: the 10-second arrows (owner, 2026-11-23, build 676 screenshot): a little bigger, the 10 not touching the arrowhead
- Rig, zoomed: the digits were centred in the whole circle but the arrowhead sits in its upper left (back) / upper right (forward), and the 1 touched it. Glyph 160 -> 200 units, touch area 240 -> 280, digits 7 units towards the open side and 5 down (mirrored on the forward arrow). Test: `test_player_scrubber`.

## Seek card picture (owner, 2026-11-23: the card should show the frame where the seek is going; it shows the title's art)
- Not done, said plainly: Kodi has no thumbnails of a stream and the phone has no way to decode a frame at another time while a video plays. Options for the owner: (a) keep the artwork; (b) a thumbnail strip made in the background by the AirPlay framework's FFmpeg (one small frame every 10 s from keyframes; reads a few percent of the file; iOS-only, so it cannot be tested in the rig, and for debrid links it costs data); (c) frames captured while playing (only parts already watched).

## ISSUE-467: the seek card shows the real frame near the finger (owner, 2026-11-23, build 676: "the photo doesn't match where the film is going ... it needs to update as it's seeking ... I kind of want the strip")
- Design (prior art checked: Jellyfin's trickplay decodes keyframes only, `-skip_frame nokey`, and accepts "the nearest keyframe"; Roku's BIF is a file of small pictures at a fixed interval; ffmpegthumbnailer is GPL-2+, so only a reference): one small picture per whole percent (0.jpg ... 100.jpg), because the card moves in whole percents and 101 files need no index. Made BEFORE they are needed, never while a video plays or opens (the debrid server refuses a crowd of connections, which is what broke build 622), only on Wi-Fi, for the first 3 Continue Watching titles with a remembered Umbrella link; the newest 6 strips are kept (about 1 MB each). A title with no strip yet shows a dark card with the time and the jump (the owner's "black until it loads").
- Native (framework r73, `remux/src/kr_thumbs.c`, entry points `kodi_thumbs_make` / `kodi_thumbs_cancel`): opens the title over the remuxer's own HTTP Range source (128 KB blocks), software-decodes ONE keyframe per percent (seek backward to a keyframe, feed that packet, drain), fits it into 320 x 180 with black bars, writes a JPEG (public-domain stb_image_write.h; FFmpeg has no JPEG encoder in this build), then a `done` marker. Existing pictures are kept (a second run resumes), a cancel stops it between pictures and inside a read.
- Python: `thumb_strip.py` (folder named by a hash of the link, never the link; the loop; `show()` sets Home property `KodiIOS.Strip` when playback starts), wired in `service.py` and `portrait.py`; the skin's card copy N loads `$INFO[Window(Home).Property(KodiIOS.Strip)]N.jpg` with a 150 ms fade; the generic artwork is gone.
- Measured on the desktop against the system FFmpeg 6.1 (the AirPlay CI runs the same test against the project's FFmpeg 8.1.1): an 81 MB MKV (16 Mb/s, a keyframe every 2 s): 101 pictures, 816 KB, 1.4 s from a file, 9.1 s over HTTP at a modelled 3 MB/s with 0.15 s to connect (67 range requests), 19.7 MB read. A 120 s video whose colour is its time: every picture is the keyframe at or just before its moment (median 0.5 s, worst 1.4 s from it, measurement noise included). A debrid link at 0.5-2 MB/s with 2-3 s to connect costs about 3 minutes in the background per title.
- Rig (Kodi 21.3 with the r36 patch, real mouse drags, landscape): the picture in the card follows the finger (card pixel colour 0 -> 35 -> 61 -> 88 -> 109 s at 10 -> 32 -> 54 -> 76 -> 93 % of the colour-coded video).
- Not proven: the phone. iOS FFmpeg (8.1.1, built for iPhoneOS) compiling this file, the real speed of a debrid link, and the picture appearing on the phone: the AirPlay candidate build (`airplay-remux.yml`: host tests with FFmpeg 8.1.1 and the iPhoneOS compile) is the next check, then device. A title's first watch has no strip (the next one does).
- Tests: `scripts/test_thumb_strip.py` (14: the rules, the native maker compiled and run on a colour-coded video, the wiring).

## ISSUE-468: the seek card stayed grey; the torrent question appeared over Sports; Umbrella still 7.5 s (owner, 2026-11-24, build 677, log 94a6a00c)
- Log facts: build 677; `vpn check: ... default route via pdp_ip0` = mobile data for the whole 90-second session; no `preview strip:` line at all (strips were Wi-Fi only and idle only, so nothing was made); `torrent prompt: asked` at 16:04:02, 8 s after the Leagues page was opened, from `episode_watch` (`check_deferred ... Canceled`): a followed show's automatic download that AllDebrid did not take; one Continue: open 2.8 s (kept opening used), first picture 7.5 s, 4.7 s of it after the streams were ready.
- Torrent question: `elementum_download.background_gate` (the follow-shows job passes it): when AllDebrid does not take an automatic download nothing starts and nothing is asked (Canceled, tried again later; the log says why). The download button the person presses keeps the question (`download.py` passes no gate). Tests: `test_torrent_prompt.py` (3 new).
- Umbrella: the kept opening had blocks 0-5 and a percentage guess for the resume point; Kodi read blocks 6 and 7 (offset 25.8 MB) and block 97 (offset 410 MB) over mobile data at 1.7-1.9 s each. `resume_cache`: 8 head blocks, the resume block found from the file's own Matroska Cues (`link_warm.resume_offset`, the same lookup Kodi's seek makes) and the one after it, the cap of 12 blocks keeps the resume point and the end first (the worst case stays 144 MiB for 3 titles). Tests: `test_resume_cache.py` (21, one builds a real 60 s MKV with ffmpeg and checks the kept block is the one the index names). Expected: the open from 2.8 s towards 0.3 s and the first picture 4.7 s after the streams towards about 1 s; for the next log to show.
- Seek card (the owner: "it needs to work easily and smoothly, like how do other sites operate?", then "ideally the seeker is instant, no loading ... plays the movie in that small box quick or slow depending on the speed of the swipe"): other sites (Netflix, YouTube, Jellyfin, Plex, Roku BIF) make the pictures on a SERVER when the video is ingested and the player only downloads small sprite sheets; this app has no server. Design now (AirPlay framework r74, native `kr_thumbs.c` session API: `kodi_thumbs_open/frame/fill/stop/resume/close`):
  - ONE PICTURE EVERY 5 s (256x144, about 5 KB; a 2-hour film is 1,441 pictures, 7 MB), picture i = the keyframe at or before i*5 s; the framework writes the grid (`step count seconds`) to the title's folder. A film longer than 3.3 h gets a wider step (cap 2,400 pictures).
  - While a drag is on, `thumb_strip.follow` chooses the NEAREST picture the phone holds for the second under the finger (`Player.SeekTime`, so not limited to whole percents) every 50 ms and sets Home property `KodiIOS.StripFrame` to it: the card flips through the film at the speed of the swipe and is never empty once one picture exists. The card's 101 copies share that one property (no per-percent files). A picture missing under a resting finger (0.2 s) is made on its own on the open session and takes over when it lands.
  - Build order: coarse first (every 6th = 30 s, then every 3rd, then all) from where the person is outwards, so any point of the film has a picture within 30 s as early as possible. One session per playback keeps the container open (opening a debrid file from nothing is seconds, a picture from an open session one seek and one keyframe). Reads are interrupted the moment the buffer runs low or a drag starts (the debrid server refuses a crowd of connections, playback has priority), and the build rests 150 ms between pictures.
  - Data: keyframes are about 8 % of a file, so a stream has an allowance for the playing title per playback: 120 MB on mobile data (the coarse pass over a film, then it stops), 1,200 MB on Wi-Fi. Pictures beyond the allowance are still made on request when the finger rests. A DOWNLOADED file is read locally (no allowance, no waiting): the rig made all 121 pictures of a 10-minute 1280x720 file in 2.3-2.7 s, 8.5 MB read.
  - Ring: the big turning ring (96 units, centre of the card, under the picture) shows only while no picture exists at all.
  - The idle pre-build for the first 3 Continue titles stays (Wi-Fi, nothing playing).
- Honest limit: a brand-new stream on a slow link has gaps until the coarse pass has covered the film; the nearest picture shows meanwhile (within 30 s of the finger once the pass has passed it). A modelled slow link measured 1.3-2.6 s for a far-jump picture made on request, so "under 3 s" holds there, but real cellular debrid latency is not proven.
- Rig (desktop Kodi 21.3 with the repo's skin, a 10-minute test video whose frames carry their own timestamp, the real follow() running inside the rig's Kodi, real mouse drags): a drag to 02:09 showed the picture stamped 00:02:04, to 04:52 showed 00:04:50, to 07:56 showed 00:07:54 (the keyframe at or before the grid point); with no picture the big ring turns in the card's middle. Rig screenshots are not in Git.
- Native signature: `kodi_thumbs_fill(handle, pause_ms, center, budget_mb, out, len)` and `kodi_thumbs_frame(handle, index, err, len)`.
- Tests: `test_thumb_strip.py` (29: follow rules on a virtual clock, 6 native tests through ctypes on a 120 s colour-coded video: one picture per 5 s from its own moment, coarse-first from the centre, a picture asked while the build runs within 1.5 s, stop/resume, black bars, no video), `test_player_scrubber.py` (13).

## ISSUE-469: the seek card showed another title's pictures; Drive copies had none; the strip slowed Umbrella's own opening (owner, 2026-11-24, build 679, log 1841aa21)
- Owner: "the seeker seems slowish for Umbrella, then I try a downloaded movie and it uses the seek photo from Umbrella, and opening Umbrella has never been so slow, or it failed at one point". Log facts (build 679, mostly mobile data `pdp_ip0`):
  - Wrong pictures: the card's Home properties (`KodiIOS.StripFrame`, `KodiIOS.Strip`) were set by the Umbrella episode's builder and never cleared when the next video began. The old `follow()` thread also kept running (it only ended when the player stopped, and a Drive movie has no remembered Umbrella link, so no new `follow()` replaced it), choosing pictures from the Umbrella folder by the movie's seek time. The "downloaded movie" here was a Google Drive copy (`Library: Drive copy opened through the app proxy`, `http://127.0.0.1:PORT/drive/...`), which had no strip at all.
  - Slow Umbrella opening: `preview strip: video opened in 27.1 s` began the moment playback began, on a link measured at about 1 MB/s (`cache read ... took=61 s` for 53 MB around the resume point). The strip's own reads shared the link with the player's: first picture 13.5 s after the tap (10.3 s after the streams were ready), a seek landed after 6 s. The kept opening also had no blocks 6-7 and the old percentage-guessed resume block (a capture made by an older build; the new capture 9 minutes later, on Wi-Fi, kept blocks 0-7, the exact resume blocks and the last: `kept 11 of 11 blocks (44 MiB) in 15.3 s`).
  - The idle pre-build kept running after the phone left Wi-Fi (156 pictures, 51 MB, partly on mobile data: it checked Wi-Fi only between titles).
  - "Failed at one point": twice a movie never reached Kodi's player (`continue circle: no picture in 60 s`). Both times the choice sheet was closed without a row (`IOSChoiceSheet control 9099` is the dimmed area around the sheet, a tap outside it; the second time `picked -1`). Not a playback failure in the log; the next log should show whether a row was tapped.
- Fixes: `thumb_strip.begin()` runs the moment a video starts: it ends the last builder (generation) and clears the card's properties. The source is chosen from the PLAYING file (`thumb_strip.source_of`): a file on the phone, a Drive copy through the app's own proxy (read like a stream; its folder is named by the path, not the proxy's port), or the Umbrella title's remembered link; a remembered link is never used for a file playing from elsewhere. A stream's strip waits until the player has settled (`thumb_strip.settled`: 10 s played, buffer healthy for 5 s, gives up after 150 s), so it never shares a slow link with the player's own opening. The idle pre-build stops when the phone leaves Wi-Fi. Native (framework r75): the first coarse pass is every 12th picture (one a minute), then 6th, 3rd, then all; `kr_source_open_tuned` makes the strip's range requests 512 KB so a keyframe is one request that is read to its end (less unread data in flight).
- Measured (host, `kodi_thumbs_*` against a 15-minute 1080p file behind a server with 0.4 s per request and 0.9 s per new connection, a stand-in for a phone's network): open 1.3 s, a picture on request 1.3 s; every random jump in the file costs one new connection in FFmpeg's HTTP protocol, which is the floor on a phone's network (about 2 s a picture on mobile data in the log). The rig (desktop Kodi, the real follower, a Drive-style loopback address behind that slow server): 48 pictures (every 15 s) in 71 s, 3.4 MB; the card showed the frame for 04:13 and 10:39 while dragging.
- Not changed, said plainly: on mobile data a brand-new stream still has no strip for about 40-70 s after it starts (settle wait, open, one picture about every 2 s from where the person is). A title built on Wi-Fi beforehand (the first three Continue titles, when nothing plays) is instant. Drive Continue rows are not pre-built yet.
- Tests: `test_thumb_strip.py` (33): a new video clears the card and ends the old builder; source choice from the playing file; the Drive copy's folder ignores the port; settle/give-up; coarse-first native order.

## ISSUE-470: the IPA build failed fetching POV: its upstream repository returned 404 (2026-11-24, runs 45317535861 and its re-run)
- Symptom: step "Acquire pinned provider fixtures" (`scripts/provider_addons.py`) ended with `HTTP Error 404` twice; the same step had passed for build 679 about 2 hours earlier. Found by running the lock's addresses from a clean shell: only `raw.githubusercontent.com/kodifitzwell/repo/2c8390c.../plugin.video.pov/...` and `.../script.module.magneto/...` answered 404 (the repository, or that commit, is gone upstream); every other pinned address answered. Not caused by this branch's changes.
- Decision (owner, 2026-11-24, asked in chat; options were: keep POV from build 679, drop POV, or supply the originals): keep POV. The lock's two packages now carry `from_ipa`: the archive is rebuilt from the reviewed tree that shipped in build 679 (the published IPA, a release asset the project keeps: "publishing a build must not delete earlier test artifacts"), pinned by that IPA's sha256, bytecode left out, entries sorted with fixed dates and no compression so the archive's digest is the same on every machine. The lock keeps `upstream_sha256` of the original archives and a note. `provider_addons.source()` picks `from_ipa` when named, else the pinned address; the digest and manifest checks are unchanged. Binary files stay out of Git (the repository check rejects them).
- Honest limits: the pinned bytes are the processed tree, not upstream's originals; the build now downloads build 679's IPA (about 590 MB) once per run; if that release asset were ever deleted the lock must be repointed at a newer build. POV's licence (GPL-3) is in its `addon.xml` and travels with the app as before.
- Tests: `test_provider_addons.py` (3 new): the rebuilt archive is deterministic and holds no bytecode; a build that is not the pinned one is refused; the lock names the preserved build for exactly POV and its helper.
- Follow-up (owner: "ensure u fork them so this doesn't happen again"): a fork of the upstream repositories is not possible for one that no longer exists, and forks would still be someone else's code to track. Instead every pinned third-party source (27 add-ons, the a4k scrapers, the Otaku mapping database) is kept as an archive in this repository's own `provider-sources-1` release, each named `<id>-<version>.zip` (or its data file's name), made by `scripts/preserve_provider_sources.py` from the files the build has just downloaded and checked against their sha256. `import-review.yml` publishes it (and refreshes it with `--clobber`) in every requested IPA build, after the IPA. `provider_addons.source()` tries the pinned upstream address first and, when it fails or answers other bytes, the lock's `mirror_base`; the digest still decides. The release does not exist until the first build with this step has finished; after that an upstream disappearance no longer stops a build. Not covered: other pinned inputs outside `provider-fallback` (the Kodi foundation, Elementum, portrait pieces) fetch their own pinned addresses.
- Tests: `test_provider_addons.py` (36): fallback order, the digest still decides, unique names, the preserve script verifies and renames.

## ISSUE-471: a tap on a Continue Watching card played another title, or nothing (owner, 2026-11-24, build 682, log 1355c1d8)
- Owner: "when I am on the home page and click Black Clover even though Dragon Ball is first, it glitches out and doesn't load anything ... I should be able to click the edge of Black Clover and it should open that". Also: "Umbrella is still very inconsistent" and "a Drive movie shows a loading circle when I seek".
- Cause found (rig, desktop Kodi 21.3 with this skin, Home page): the Continue row's `<onclick>` was `PlayMedia($ESCINFO[ListItem.FileNameAndPath])`. A bare `ListItem` is the item of whichever control holds the WINDOW's focus, and a touch does not move focus into the row. In the rig, with the row showing its card and no focus in it, `ListItem.Label` was empty while `Container(5001).ListItem(0).Label` was the card ("Ep") and `Container(5001).ListItem(0).FileNameAndPath` its play path. In the phone log: a tap on the second card gave `PlayMedia` of nothing (`continue circle: no picture in 60 s`, no `OpenFile`, no `watch:` line), a tap on the first card opened Inception (`tmdb_id=27205`, the item of another control), and a tap at the back button of the player was followed by TMDb Helper asking how to watch Madden (the hero's item, `tmdb_id=1131943`). Which of these happened depended on where the focus last was, hence "inconsistent".
- Fix: the row plays its own list's selected card, named explicitly: `PlayMedia($ESCINFO[Container(<row id>).ListItem(0).FileNameAndPath])`. The tap itself selects the card under the finger (Kodi's `CGUIListContainer::SelectItemFromPoint` maps the touch to the row of the list, edge cards included), so the second card, partly off-screen, opens Black Clover. Test: `test_play_now.py` (row text names its own container; no bare `ListItem`). Not proven on the phone.
- Umbrella openings in this log (all via the remembered link, `route=cache`): Black Clover 2.1 s and 1.5 s to the first picture (11 kept blocks); Dragon Ball 11.4 s the first time (no kept opening: its capture was cut short three times, `stopped early: a video is opening`, because the next video was opened within seconds) and 4.7 s the second time (all 11 blocks kept, but the resume point had moved after they were kept: Kodi read blocks 220 and 271 from the network at about 1.5 MB/s). Inconsistent because it depends on whether the opening has been kept for exactly the place where the title was left; a title that is opened and left within seconds, over and over, never gets it. Not changed in this build.
- Seek card on a Drive movie (screenshot: the ring in the card): the strip never opened: no `preview strip:` line after the Drive movie began. The builder waits for the player to be calm (`thumb_strip.settled`, 150 s) and the movie was being sought through all the time (Drive answers each jump in 1-2 s, `Player.Caching` stayed true). The wait is now 900 s and the calm spell 4 s, so it starts at the first pause in the seeking. Umbrella strips in this log: `video opened in 9.6 s` and `9.7 s` (mobile data), `holds 1 pictures` after 4 s (cut short by the next video).

## ISSUE-472: video controls round 2: no film information or ratings, tap the time left for "Ends at", a smaller 10-second arrow that goes round its 10 (owner, 2026-11-24, build 682; mockup `docs/design/player-controls-mockup-r2.html`, sizes approved)
- Film information: Fuse's info over the video (logo, "4K · 2 hr 28 mins", plot, ratings, ends at) was seen over our controls in the owner's screenshots, although `safe_inset` already hid it `!Window.IsVisible(videoosd)`. Whatever kept that condition from holding on the phone, the controls now also say that they are up: Home property `KodiIOS.OsdOpen` is set when they open and cleared when they close, and the overlay's group hides under it too (`player_osd.HIDE_CONDITION`, moved in place in files an earlier build already inset). The plot and the ratings of Fuse's pause and start info are switched off once by default (`OSD.InfoOverlay.DisablePlotRatingsOnInfo`; Settings › Customisation turns them back on). Info (the episode card) still has the plot and "Ends at". Not reproduced in the rig (it needs a title with a logo and a plot); the property and the condition are checked, the look is for the phone.
- "Ends at": the time left (bottom right) is a button; a tap shows "Ends at 10:11 PM" instead, a second tap goes back (setting `ios_osd_ends`; the earlier "total length" state of that tap is gone, as the owner asked for Ends at in its place). It is Kodi's `Player.FinishTime`, which is the clock plus the time left worked out again at every draw: rig, a 10-minute video: 06:06:57 with 9:48 left read 6:16 AM; after a seek to 90 % it read 6:08 AM; paused with 1:00 left it read 6:08 AM and 75 seconds later 6:09 AM (it moves on while paused). Under a finger Kodi's value does not move until the seek lands (rig: 6:19 AM at 04:15 and at 08:01), so the service's `ends_at.run` writes `KodiIOS.EndsAt` ten times a second from the second under the finger and the clock, divided by the tempo; the controls show that one while `Player.Seeking`. Rig: 6:15 AM at 04:15 and 6:11 AM at 08:01 while Kodi's own read 6:19 AM; it cleared when the finger lifted. A skip of 10 seconds changes the position and so Kodi's value.
- Arrows: `portrait.skip_arrow` draws a circle that goes all the way round, open only at the top where the head sits (the forward arrow is the same picture flipped); 130 units instead of 200 so they stay clear of the title; the touch area stays 280; the 10 sits in the middle of each circle.
- Tests: `test_ends_at.py` (8, new, in the CI list), `test_player_scrubber.py`, `test_customisation.py`.
- Follow-up (owner, 2026-11-24: "upload the POV repo that was shut down into the Kodi iOS repo, an agent needs it ... ideally fork all repos Kodi iOS uses"): the text of both add-ons (POV 6.11.03: 125 files, magneto 6.11.01: 32 files; `.py .xml .json .po` only, the repository's file rule) is in `migration/provider-fallback/preserved/` for reading, with a README; the build does not use it. One value is redacted there: POV's default `tmdb_read_token` (an access token its author embedded; the JWT rule of `check_project` found it). The byte-exact archives (artwork included) are in the release `provider-sources-1`. A GitHub fork of a repository that is gone is impossible, and this session may only touch this repository, so other repositories are not forked; instead the release holds a verified copy of every pinned provider archive (29 files) and the build falls back to it. Not yet kept: the other pinned inputs outside `provider-fallback` (Elementum client and Burst from `elgatito`, CocoScrapers and the jurialmunkey repository, the Kodi 21.3 foundation `.deb` from `mirrors.kodi.tv`); each fetches its own pinned address with a digest and has no copy to fall back to.

## ISSUE-473: "Ends at" tap did nothing, Fuse's film info still showed, huge title, Drive pictures slow (owner, 2026-11-24, build 686, log b142eafc)
- "Ends at" tap: the log has no click on control 7132; taps at (2130-2157, 940-961) of the 2340-wide layout went to control 7100, the clear button behind everything, which closes the controls. The toggle button was drawn 100 units LEFT of the time (`left -100` in a group that I had widened to 500): the rig click happened to land inside it, the owner's taps did not. The touch area now spans the right end under the bar (x 1590-2190, y 912-1012: clear of the bar's own touch area, which ends at 916) and a test checks the owner's tap points against the generated XML.
- Fuse's film info (logo, "FHD · 23 mins", the episode line, "Ends at 8:12 AM", "Returning ...") was still over the Continue panel in build 686. The log line `portrait files checked ... 3 updated (portrait/Home.xml, 1080i/VideoOSD.xml)` shows why: neither `Custom_1152` nor `Custom_1153` was among the updated files. The phone's copies were inset by build 191, before the hide-under-the-controls condition existed, and `safe_inset` returns a file that already has its marker untouched (my in-place update of build 686 only replaced the older condition, not an absent one). It now sets the condition whether the file has none or an older one (`player_osd.safe_inset`, a regex on the inset group's header), and the plot and ratings of the pause info stay off by default. Rig: a file without the condition gets it, one with the old text moves to the new, a current one is left alone.
- The title above the bar was `font_title_midi` (68 units): it is `font_head_bold` (40), and wraps to a second line growing upward from the bar instead of running on.
- Seek pictures, from the log: a Drive movie (2 h 28 min, count=1778): `preview strip: video opened in 71.9 s` (the player itself opened it in 2.9 s, because Kodi's demuxer opens a fragmented MP4 by its fragment index, `use_mfra_for`, and ours did not: it read every fragment), then 185 pictures in 121 s (33 MB, 0.65 s a picture) before the next video began: one picture a minute, which is not a fluid card. An Umbrella title: opened in 7.6-10.5 s, 18 pictures in 44 s. The touch itself was fine: 55 moves a second, seeks landed in 0.6-1.5 s.
- Changes: (1) native (framework r76) `kodi_thumbs_open2` takes the length the player knows and opens a fragmented MP4 by its fragment index: model of a phone's network, a 10-minute 450 MB fragmented MP4: open 139 s (476 requests) -> 2.7 s (6 requests); the length comes from the hint, or, with none, the file is opened the old way; (2) the idle Wi-Fi build now also takes Drive copies in Continue Watching (the first three rows; the proxy's address, the same folder the card reads), so a Drive movie watched before has its pictures before it is opened again; (3) a heap corruption found in `test_thumb_strip` (an abort, "malloc(): unsorted double linked list corrupted"): `kr_thumbs_close` freed the session while a fill or a frame in another thread was still running; close now waits for them (an `active` count), with a test that closes during both six times.
- Not changed: a brand-new stream still has few pictures at first (about one every 2 s on mobile data; coarse pass of one a minute first). The card shows the nearest picture. A complete 5-second strip of a 2.5 h 4K film is about 320 MB over Drive and takes about 20 minutes, so it exists for titles built on Wi-Fi beforehand, not for the first minutes of a title.
- Mockup of the Continue Watching sheet (glass-styled, flat, about 92 % dark, not Liquid Glass; `docs/design/player-continue-panel-mockup.html`): awaiting the owner's approval, not built.
- Follow-up (owner, build 687: "wait you got rid of the logo?? I loved the logos ... I just didn't want the other [info] removed"): hiding Fuse's whole info over the video also hid its title logo. The controls now draw the logo themselves, above the title (left 150, 520 x 135 units, bottom 725; the same choice as Fuse's `Info_Title`: TMDb Helper's cropped logo when `TMDbHelper.EnableCrop` is on, else the film's clearlogo, else the show's, else only the text title below), and none of the rest (quality, length, the episode line, plot, ratings). Not shown over the Continue Watching panel. Rig (desktop Kodi with the skin; the crop-logo path, since the rig's test file has no artwork): the logo sits above the smaller title, clear of the arrows. The clearlogo branches use the same labels as Fuse's, not run in the rig. Test: `test_player_scrubber.py`.

## ISSUE-474: logo and title too high; Continue Watching row overwhelming; Info card empty for shows (owner, 2026-11-24, build 688, log 00838bcd)
- Build 688 log: the "Ends at" tap works now (`Click at 2123 x 932 ... control 7132 (handled)` four times); Umbrella opened in 2.3 s and 3.2 s to the first picture; the strip of an Umbrella title opened in 7.9 s and made 11 pictures in 33 s.
- Logo and title: `aligny` in Kodi has no `bottom`, so the title box (top 730, height 130) put its text at the top of the box, about 100 units above the bar; the logo sat above that. The title is now a 100-unit box at top 760 centred on 810 (the bar is at 862) and the logo's bottom meets the box's top (top 625, 135 high). Rig: the logo and title sit just above the bar.
- Continue Watching row: two mockups for the owner to choose (`docs/design/player-continue-panel-mockup.html`): A, a nearly black bottom sheet carrying the row, the bar and the times; B, a light grey floating box around the header and the cards. Neither is a blur (Kodi cannot blur what is behind it). Not built until one is chosen.
- Info card: an episode started from Continue Watching said "No description for this video yet.". Continue plays the remembered link without TMDb Helper (`fast_stream` -> `play_stream`), so the playing item had title, show, season, episode and art but no plot. Now: `ios_continue.record` keeps the plot TMDb Helper gave when the title was first started, and `update` fills it from the playing item if the record has none; `play_stream` gives it to the playing item; and for a record that has none (every title started before this build) the service looks it up on TMDb once the video plays (`info_fill.py`: the season for an episode, the film's page for a movie; TMDb Helper's own key and the Library's cache) and keeps it with the record and in Home property `KodiIOS.Plot`, which the Info card shows when the playing item has no plot. Rig: with a video that has no plot and the property set, the card shows the plot. The lookup itself (network, key) is covered by tests with a fake TMDb and not run on the phone. The show's name, season and episode, the runtime and "Ends at" were already right in the screenshot (Ends at 11:00 AM with 12:00 left).
- Tests: `test_info_fill.py` (9, new, in the CI list), `test_player_scrubber.py`.

## ISSUE-475: Continue Watching sheet (mockup A) with swipe-down hide; Info card X without a grey disc (owner, 2026-11-24, build 689)
- Owner: chose mockup A (dark sheet with grabber), asked that a swipe down hides it, and that the Info card's X is just the X.
- Sheet: a rounded dark group (`EB18181C`, grabber `4DFFFFFF`) behind the Continue row, bar and times, shown only with the panel, sliding in and out. Flat texture, not Liquid Glass (Kodi cannot blur). Rig capture (desktop Kodi rig) checked on and off.
- Swipe down: keymap `<videoosd><touch><swipe direction="down">Skin.Reset(ios_osd_continue)</swipe>`; the keymap is rewritten because navigation.py bytes changed.
- Info card X: `close_button_1080(..., circle=False)` draws no disc; Play on TV keeps its disc.
- Tests: `test_player_scrubber.py` (sheet, keymap, no disc). Not proven on the phone.

## ISSUE-476: Continue Watching button ignored taps; Info plot cut off (owner, 2026-11-24, build 693, log f11c1077)
- Log: four taps at (489-519, 963-1042) of the 2340 layout all went to control 7100 (the clear background): the Continue Watching button was only 54 units tall (970-1024) and the fingers landed above and below it. Info (7141) worked at y 1008.
- Fix: both buttons are 100 units tall (947-1047, same text centre y 997); Continue Watching starts 170 right of the edge and is 520 wide.
- Info plot cut mid-sentence (four-line box). Owner: "ensure there is a way that it will auto fill text". Kodi cannot shrink text to fit, so the service measures the plot once (`info_fill.tier`: up to 230 characters normal, up to 420 the smaller `font_mini`, longer the smaller size with a slow scroll) and sets Home property `KodiIOS.PlotTier`; the card has one textbox per size and shows the one that fits. Normal size is `font_main` in a 232-unit box (six lines). Desktop rig captures of all three sizes checked.
- Tests: `test_player_scrubber.py` (hit area covers the logged taps), `test_info_fill.py` (tiers, card wiring).
- Not proven on the phone.

## ISSUE-477: Umbrella openings inconsistent (owner, 2026-11-24: "super inconsistent and nearly the only thing inconsistent"); third-party sources not kept
- Evidence: every Umbrella `open timing` in the logs of builds 640-693 (about 60 opens), joined to the `stream opening: route=` line before it. With the opening blocks in (`cache 3/3`, wait 0-240 ms) the open took 0.2-3.2 s (first picture 4.4-13.5 s). When the cache gave up at about 2.0 s (`direct 0-2/3 wait 2.0 s`) the direct open then took 6-8 s, first picture 10-18 s, and no opening was kept for next time. A third group has no route line at all and 21-23 s opens: the cache only takes .mkv/.avi/.webm links, so these were other file types opened directly by Kodi (not proven: the file type was not logged).
- Cause of the first group: `answered()` waits up to FIRST_ANSWER = 5 s but `hopeless()` leaves after 1.5 s when the projected finish is past 1.2 x the time left: one 4 MB block at 2 MB/s with two to come projected 4 s > 3.6 s. The direct fallback costs more than the wait it avoided. `note_slow` then played that server's family directly for 6 hours.
- Changes (no preparing ahead: only what the owner selects opens): FIRST_ANSWER 8 s (a block-by-block rate of 2 MB/s now continues; a dead server or 0.2 MB/s is still dropped at 1.5 s); SLOW_SKIP 30 minutes instead of 6 hours; the route field says `not cached (.mp4)` for a link the cache does not take (file type only, never the address); ONE `Kodi iOS open record:` line per open with the same fields (via, source, route, streams ready, stages, first picture) so a table of openings can be read straight from a log.
- Not changed, and why: letting the cache take MP4 links (needs the log's file types first); the 10 s between streams ready and first picture in one open (build 1841aa21) is Kodi's own probe, to be read from the record lines; Drive openings are covered by the same record line (via=library).
- Third-party copies (owner: "back up all 3rd party add-ons in case what happened last night happens"): `scripts/source_mirror.py` keeps every verified third-party download of a run (official Kodi add-on archives, jurialmunkey's, Elementum client/Burst/CocoScrapers/ResolveURL, the kodi-six module trees as a tar, the Kodi 21.3 package) in release `third-party-sources-1` with a MANIFEST.json; each downloader tries upstream first and uses the kept copy only when upstream fails and the pin (sha256, Git blob, tree hash, or the manifest digest) matches. The first run fills the release.
- Tests: `test_source_mirror.py` (8), `test_open_budget.py` (3), `test_open_timing.py` (13).
- Not proven on the phone.

## ISSUE-478: episode description cut off on the show page; wrong episode opened by a tap (owner, 2026-11-25, build 698, log c170fd54)
- Cut off (screenshot IMG_0681): the plot under each episode was a two-line box (84 units) in a 420-unit row. Fix: `portrait.EPISODE_H` = 440, the plot box starts at thumb_h+30 and is 150 units (four lines of about 36), the focused card is 196 units taller than the picture. Test: `test_episode_card.py`.
- Taps (owner: "it opens the top show or middle show", like Continue Watching): the log has one episode-list tap (17:35:22, `Click at 288 x 1080 in MyVideoNav.xml ... control 60`). Layout y 1080 is the bottom edge of the Episode 7 card, 35 px above Episode 8, and Episode 7 opened: that tap is consistent with what was drawn. Across 69 episode-list clicks in all logs, no pattern with scrolling was found (tap to click 0.03-0.44 s). Hypothesis, not proven: the native portrait scroll keeps the previously selected row after a pan (`CGUIBaseContainer::PortraitScroll` preserves the selection), so a tap soon after scrolling may open that row. Asked the owner what was tapped and what opened, and whether the list was still moving. No change made for the taps yet.
- **Answer to the owner's latest message (build 698, log c4a0c119, "can't you remove that highlight feature and only register taps?"):** that log has no playback at all: each episode tap shows Kodi's "Resume / Play from beginning" menu, and a tap outside it closes it and goes through to the show page (`Click ... DialogContextMenu control 0`, then `MyVideoNav`). Changes: (1) the focused-row card is gone (`episode_item(True)` equals `episode_item(False)`), so no row looks chosen after a scroll; (2) both episode lists set `KodiIOS.EpisodeTap` on a tap (season, episode, title, row) and the next `open record:` line carries `tap=...` and clears it, so a log can show which row was tapped against which episode opened. Still unproven: whether Kodi activates the focused row instead of the tapped one after a scroll (native `PortraitScroll` keeps the selection); the `tap=` field is how the next log will tell.
- **The menu dismissal (owner, same day: "it takes me out of the show to the show selection page, not the episode list, it should close the menu, not the whole page"):** the log lines "Click ... DialogContextMenu ... control 0" and a later "Click ... MyVideoNav" are ONE tap: the page's click line prints only when its handler returns, and the handler was blocked inside the Resume / Play from beginning menu (Kodi's own `VideoPlayActionProcessor`, whose cancel path does nothing else). Two library page loads follow the menu's close; what asked for them is not in the log. Rig test (desktop Kodi, a Python context menu over the System information page): the outside tap closed only the menu with the old `Close` and with the new `Dialog.Close(contextmenu)` alike, so the rig does not show the page going back. Precaution kept: the context menu's backdrop now runs `Dialog.Close(contextmenu)` (`Close` is Kodi's Back action, which can also reach the page behind). New: `page_watch.py` logs `Kodi iOS page: folder changed from ... to ... (content) - the menu closed 0.4 s ago; the Drive lists were refreshed 2.5 s ago` (action, season and episode only, no Drive ids), so the next log names the cause. Candidates: `library_watch` / `library_lists` run `Container.Refresh` while the menu is open; the native touch layer. Not fixed, not proven.

## ISSUE-479: the automatic episode check never fetched a new episode of Phony (owner, 2026-11-25: "a episode came out of Phony today and it never updated, and it's marked in the system")
- **Evidence (device logs, build 698):** the launch's one pass ended with `check_deferred error=Canceled` at 19:27:26 (c4a0c119) and `error=Stop` at 17:21:37 (c170fd54), each followed at once by `opening_check queued=0`. At 19:27:26 the pass had found an episode to fetch, asked Elementum, and the log says `torrent prompt: not asked; an automatic download that AllDebrid did not take is skipped, never started as a direct torrent`: a new episode is often not cached at AllDebrid yet. At 17:21:37 a video had just started (Player.HasMedia stops the pass; `remote_files` raises Stop).
- **Cause (code):** (1) `run_open_checks` ran ONE pass per launch/foreground transition and never again, whatever the pass did; (2) an exception during a show ended its whole pass (so one episode AllDebrid had not taken also stopped the show's later episodes and their alerts); (3) the `finally` block started the show's 30 minute cooldown even when the pass was only interrupted, so even a manual re-open soon after skipped the show.
- **Fix (host-tested):** `sweep` tells an interruption (Stop, Canceled while the app is leaving or a video plays, "deferred") from a result: an interruption leaves the show unchecked (no cooldown) and sets `sweep.last['deferred']`; a download that found nothing is that episode's `not_found` only (`episode_not_taken` is logged), the other episodes are still tried and alerted. `run_open_checks` now looks again: two minutes after an interrupted pass; every 30 minutes while an aired episode is still not found, at most 12 times per launch (about six hours); and once when the date changes while the app stays open. The opening log line carries `checked`, `unresolved`, `deferred`.
- **Not changed:** the app still checks only while it is open (iOS does not run it otherwise); a pass still needs `ready`, the app in the foreground and no video, menu or search dialog. Nothing tells the owner when an episode is out but not found: proposed (a notice "S1E3 is out; no source yet, still looking").
- **Tests:** `test_episode_watch.py` (Retries, Scheduling: 7 new). Not proven on the phone.

## ISSUE-480: "select source" did not work properly: the same slow version replayed, the loading circle over the list, a slow source ranked first (owner, 2026-11-25, builds 698 logs f12dfcdd / 6fea5b20)
- **Evidence:** one source (Phony S1E7, HEVC, `alldebrid|torrentio`) read at 0.7-0.8 MB/s: the cache got 1 of 3 blocks in 5.5 s, `audio stream stalled`, six `OutputPicture timeout`, "playback clock still not moving 30 s after the tap", then the Continue guard (`the remembered link did not open (30 s)`) asked Umbrella again; the second try listed `kept 31` and a source started 1.2 s later with no list for the owner (`ios_continue=1&ios_fast=0`: the saved player and version are replayed without asking) and the owner's taps went to `DialogBusy control 0 (not handled)` (the guard keeps the modal loading circle up through the second try).
- **Causes:** (1) the guard's second try still carried the saved version; (2) the circle (`KodiIOS.ContinueOpening`) was never closed when the version list opened; (3) `source_speed` measured a source only up to "streams ready" (12.8 s here), so a source whose picture never came kept its rank.
- **Fix (host-tested):** (1) on a dead link the guard forgets the title's saved player and version (`ios_continue.forget_choice`, the same as long press > Choose source), so the second try shows the Download / Stream sheet, the quality list and the version list; the place to resume is kept; (2) `umbrella_picker.run` clears the circle and closes the busy dialogs right before the list opens; (3) `open_timing.LATE` tells the service the first picture (or that none came in 30 s): `source_speed` records the real time, a failure for the source, and a six-hour "bad file" mark by a fingerprint of the file name (never the name) that ranks that file last (`order()`); a picture later than 25 s counts as bad too. Log lines: `Umbrella source <key>: first picture after N s` / `no picture (ranked last for a while)`.
- **Not changed:** the guard's limit (LIMIT 30 s, 45 s once the streams are open; ISSUE-449 says 14 s, the code says 30); the rank is per debrid + provider, so one bad file lowers that pair a little, the file itself goes last. A source that is slow but starts (a picture in under 25 s) keeps its place.
- **Tests:** `test_continue_guard.py` (ForgetsTheSavedVersion), `test_source_speed.py` (LateVerdict), `test_open_timing.py`. Not proven on the phone.

## ISSUE-481: seek box showed when the 10 second buttons were pressed; the +/-10 buttons a little smaller (owner, 2026-11-25)
- Cause: `Player.Seeking` (Kodi iOS patch) is true while the player carries out `Seek(+-10)` as well as under a finger on the bar, so the seek card, the thick bar and the white times appeared after a skip.
- Fix: the drag is `Player.Seeking + Control.HasFocus(7131)` (the slider has focus only under the finger; a skip button has focus when pressed); the same rule in the strip's `seeking` and the Ends at loop. Kodi accepts `![A + B]` (checked in the desktop rig). The +/-10 glyphs are 112 units (130 before); the tap area is unchanged. Tests: `test_player_scrubber.py`. Not proven on the phone.

## ISSUE-482: Choose source missing from the TV show menu; the Continue guard waited 30 s (owner, 2026-11-25, log 4b2caae7: "choose source works on Home, not in the TV show menu"; "the guard needs to work")
- **Choose source:** Home's Continue Watching cards had a long press > Choose source (`ios_continue.choose_source_action`), but the long-press menu of an episode on the TV show page (TMDb Helper's list) held only Kodi's items and Download: there was no such entry, and log 4b2caae7 shows the Home flow (`ios_choose=1`, "choose source asked; offering 2 options", the Download / Stream sheet, the quality sheet, the version list) working. New: a context item "Choose source" (bundled `choose_source.py`, addon.xml) for movies and episodes of TMDb Helper pages (not Home's cards, not library pages, which have their own), which asks the plugin's `choose_source` action with the TMDb ids; the plugin offers the place to resume when the title has one and plays with `ios_choose=1`: nothing saved is used. The Download / Stream sheet lists Download first: in that log the tap picked Download (Elementum's torrent list), not Stream.
- **Guard:** LIMIT 30 s -> 20 s for an open whose streams are not there, 45 s kept once Kodi has the streams; new NOTHING = 10 s when Kodi has no media at all (build 698 log f12dfcdd: after the TV cast, `continued ... from its last link` at 20:04:02 and no `OpenFile` for 30 s). Together with ISSUE-480 a dead Continue now ends in the list, not a replay.
- **Tests:** `test_choose_source.py` (new, in the CI list), `test_continue_guard.py` (SmarterLimits), `test_link_warm_recent.py`. Not proven on the phone.

## ISSUE-483: Library status said "Paused for playback" with nothing playing, and there was no way to go on (owner, 2026-11-25, build 698 log 8e545f74, screenshot IMG_0686)
- **Evidence:** the Download choice (Elementum, "Download only") left the "a play is opening" mark `KodiIOS.Open` (via elementum, set by `ios_watch_dialog.choose_player`) up: `slowdown: Waiting while a video opens or buffers` at 20:09:12, `open timing: no picture after 120 s via elementum` and `slowdown: full speed` at 20:11:12. For those 120 s every copy was held and Library status showed its line "Paused for playback" for S1 E7 Phony.
- **Fix (host-tested):** (1) a download that is not watched (mode 0 Download only, or a cancel) clears the mark at once (`elementum_cloud`), so nothing is held; (2) Library status > WORKING NOW has a "Resume now" link (top right of the card, `library_page.RESUME` = 9007), visible only while a row says "for playback" and nothing plays (`!Player.HasVideo`): it sets `KodiIOS.ForceRun` for 180 s and clears the open marks (`slowdown.force_run`); while nothing is playing, caching or casting, `play_reason` ignores the opening mark. A real video, a stalled buffer or a cast hold work as before. Log: `Library status: Resume now pressed`.
- **Evidence class for the link:** desktop Kodi rig capture (the link forced on for the picture), not the phone. Style: the page's own `u.link` (the same as "Edit order").
- **Tests:** `test_resume_now.py` (new, in the CI list). `test_build193_pages.py` fails the same 9 ways on a clean tree and is not in the CI list.

## ISSUE-484: Build 702 failed CI at test_airplay_room
- Cause: the service's two `slowdown.configure` lines gained `forced=` (ISSUE-483 Resume now); test_airplay_room still asserted the old exact text.
- Fix: test updated to the new wiring. Retest: every test in the CI step run locally, all pass.
- Protection: the wiring assertion now covers the Resume now argument.

## ISSUE-485: One-hour copy looked stuck (owner log 9ba9b5b5)
- Finding: not stuck. A 1 GB AllDebrid to Drive copy ran at ~0.42 MB/s on Wi-Fi (the phone's upload line), 22% to 97% in 34 min with no stall; 8 timed-out pieces cost ~3.6 min. After a Wi-Fi to cellular switch the last 3% took 10 min at 0.03-0.2 MB/s. Resume across the switch worked.
- Fix: a copy under 1 MB/s with over 15 min left says "slow upload line, still working"; a copy under 0.25 MB/s for 3 min on cellular waits for Wi-Fi ("Waiting for Wi-Fi · cellular is too slow...") and carries on from what Drive has. Retest: test_slow_copy (host). Device behaviour unverified.

## ISSUE-486: Iron Man showed "preparing", then vanished with no notice (owner log 0d8c75c0)
- Root cause: the library check asks `caption_repair.due()` whether a ready copy has zero-length subtitle cues; it answers True once and records the try. The check queued a repack ("faster opening needed (caption_lengths)"). When the run opened the video to make it, its own inspection called `due()` again, got False, saw a compatible video and dropped the job ("kept unchanged", `skip_compatible`). No conversion ran, so no "Ready" notice, and the record of the try meant it was never asked again. Log: Iron Man 21:08:47 asked, 21:08:59 opened, 21:09:17 kept unchanged; Library status 21:09:28 showed 0 converting.
- Fix: `caption_repair.carry(prior_probe, probe)` keeps a caption-length repack asked by the check when the run inspects the video (prepare_cloud). Retest: test_caption_repair (host). Device unverified.
- Also seen: after an update every video is inspected once ("never checked", 10-20 s each) which shared the line with a copy; this is the one-time sweep, not a loop (my earlier "re-listing loop" guess in this session was wrong).

## ISSUE-487: Episode taps on the show page did nothing (owner log f8c6f27b, build 705)
- Symptom: "I tap and tap but nothing shows". Log: Click ... control 60 (handled) with no folder change and no OpenFile; control 52 taps still played.
- Root cause: ISSUE-478 (build 699) added an `<onclick>` that names the tapped episode to both episode lists. List 60 loads its items through `<content>` (a list provider). In Kodi 21.3 `CGUIBaseContainer::OnClick` runs the container's own click actions INSTEAD of `m_listProvider->OnClick(item)` when it has any, so the item was never opened. Only list 52 (no content) goes through the window's click message.
- Fix: the tap-naming onclick is only on list 52; list 60 keeps the default open. Retest: test_episode_card (fails on the old code at list 60, passes now). Rig/device unverified. Regression: the test forbids an onclick on any episode list that has `<content>`.
- Cost: taps on list 60 no longer appear as `tap=` in the open record (the Click log line still names the control).

## ISSUE-488: Umbrella opens inconsistent over mobile data; first show never loaded (owner log ff742bd7, build 706)
- Per-open facts (pick of the version -> first picture; tap-to-picture where the log has it): Godfather 13.1 s (streams ready 8.1 s after the pick, handoff 3.3 s); La Bola Negra streams ready 7.6 s after the pick, player closed by the owner 3 s later; 9 Songs streams ready 8.4 s, closed 2.8 s later; Family Guy S1E1 streams ready 17.1 s after the pick (pick to OpenFile 12.8 s); Two and a Half Men S1E1 30.8 s (pick to OpenFile 26.5 s); Dragon Ball Z S1E1 and E2 never reached OpenFile.
- Proven in the log: (1) from 13:35:48 to the end of the log (13:42) Umbrella ran three plugin invocations that never finished and handed over 1,571 links (about 4 a second) through `remote_media.for_kodi`, each a cache attempt or a direct check (two 64 KB reads, about 1 s) on the mobile data line, during every later open and during playback ("stream stalled" 13:39:04). It began when two hand-offs came 2.7 s apart with Kodi reading neither ("previous source never read by Kodi"). (2) The "no picture, ranked last" verdict fired for a source whose player the owner had closed 12 s earlier (La Bola Negra), so a good source was demoted.
- Not proven: why Umbrella cycles after the first hand-off, and what takes 13-26 s between picking an episode's version and Kodi's OpenFile (movies take 2-3 s). Umbrella's own sources are not in this repository.
- Fixes: `remote_media.cycling()` is asked by `umbrella_recovery.remember` (Umbrella's unlock hook only; Continue, Play on TV and the library never count): after 4 unlocks in 20 s the rest get no cache attempt, direct check or warm-up, and the first ones log `Umbrella unlock: <release name>, <MB>, <s> after the tap` so the next log shows what Umbrella went through between the pick and Kodi; open_timing: a closed player gives no verdict (`alive`). Tests: test_open_budget, test_open_timing (host). Device unverified; the Wi-Fi log decides whether the episode hand-off gap (movies 2-3 s, episodes 13-26 s from pick to OpenFile, at the same hand-off rate) needs more.
- Not a cause (checked): the storm's rate was the same during movie and episode picks (2.7-4.2 and 3.3 per second), so it does not by itself explain the episode gap.

## ISSUE-489: Recently opened titles took the whole slow way again (owner, 2026-11-25)
- Cause: `fast_stream` (reopen from the remembered Umbrella link, skipping details, the 5-13 s scrape, the version list and the pick) required 5 s of watched position. The ten test titles were each stopped within seconds, so every second open said "no place to resume (0 of 1351 s)" and went the full way.
- Fix: a title stopped before 5 s reopens from its remembered link at the start (finished titles still go the normal way; a dead link still does; the continue guard plays the normal way if the link does not open). Test: test_fast_stream. Device unverified.
- Still the slow way, not changed: a title never opened before (details + scrape 5-13 s + the version list + the pick) because Umbrella's own scrape is outside this repository.

## ISSUE-490: Episodes take 8-17 s from the pick to the player, movies 4 s, on Wi-Fi (owner log f155938b, build 706)
- Measured (pick on the version list to Kodi's OpenFile, hand-offs counted in `remote_media.for_kodi`, each followed by the 1.3 s direct check, `preflight`): movies 4.4 / 4.5 / 3.6 s, exactly 1 hand-off each (1.3 s of check, 29-38 % of the gap); episodes 12.6 s with 20 hand-offs (two threads), 16.7 s with 10 hand-offs (14.3 s of checks, 86 %), 8.2 s with 3 (4.0 s, 49 %). Scrape before the list: about 5 s for every title. Not network speed: the checks are one-second round trips and the gap is the number of them.
- Cause: after an episode pick Umbrella unlocks several links one after another before one is handed to Kodi (what they are is not in this log; build 709 logs each unlock's release name); every unlock goes through `umbrella_recovery.remember`, which ran the full direct check (two 64 KB reads) on each. Umbrella's own part of a step is about 0.2 s.
- Fix: `worth_checking`: one check per pick, and for an episode only for a file that names that season and episode; every other unlock is returned at once, untouched (the 4-in-20-s limit of ISSUE-488 stays as a backstop). The picker leaves a `KodiIOS.UnlockWant` note at the pick. Test: test_umbrella_recovery (host). Device unverified: if the extra unlocks are other sources that all name the episode, only the first is checked and the rest still cost Umbrella's own ~0.2 s each.
- Not changed: the cache route is skipped for 30 minutes after any slow answer from a server family (SLOW_SKIP), so on these logs every open is `direct`; a movie open could be faster with the cache route (first picture 1.3 s in an earlier log) but it also risked refused ranges (ISSUE-306/344), so it is a separate decision.

## ISSUE-491: AirPlay fps lag at random times (owner log ad7d3e73, 2026-11-26) - tracking added, cause not proven
- What the phone side shows (2 sessions, Wi-Fi, 1080p H.264 17.3 Mbit/s): playback never stopped for long, but 13 of 116 video and 11 of 208 audio segments took longer to make than the 6 s they cover, the TV waited more than 1 s for 11 video segments (up to 5 s), and the 30 s sample caught a stall at 16:43:40-16:44:40 (buffer empty, position 2598 -> 2607 in 30 s) that the segment lines do not show. Late segments were not the high-bitrate ones (0 of 11), Drive first-byte time was the same in good and late windows (330-390 ms), no uploads or conversions ran. 1,003 of 2,737 Drive reads needed a second try on a fresh connection (reason not logged).
- Tracking added (no behaviour change): `airplay_diagnostics.Judder` logs `state_change` (TV player waiting / playing / buffer empty / likely to keep up / rate) the moment it happens and `position_slip` (wall time against the picture clock, how many seconds lost) from the 5 s samples, each with the source and network counters; `drive_proxy.ReadStats` logs one line a minute: reads, second tries by exception name, first-byte median / 90th / slowest. Tests: test_airplay_diagnostics, test_drive_read_stats (host).
- Next: with the owner's clock times of felt lag, match `position_slip` / `state_change` to the segment and Drive lines; then decide between the stale-connection retries, sharing the video bytes with the audio read (native), or a deeper segment lead.

## ISSUE-492: Episodes from big packs open slowly (owner log 4e3d5e2c, build 710)
- Measured (pick on the version list -> first Umbrella unlock -> Kodi OpenFile): Black Mirror E01 1.3 s -> 3 unlocks -> 2.2 s; E02 2.6 s -> 3 -> 3.6 s; Dragon Ball Z E01 10.1 s -> 92 unlocks (a whole-series pack, files from S09E273 on, each logged "(not checked)" by ISSUE-490) -> 27.3 s; DBZ E02 7.1 s -> 4 -> 8.1 s; E03 8.8 s -> 1 -> 9.1 s. Films (single files) 3-4 s. Our own check is no longer part of it (ISSUE-490 worked); what remains is Umbrella listing the pack (7-10 s) and unlocking its files one by one (about 0.2 s each) until it reaches the episode.
- Fix (ours, no Umbrella change): `deck_picker.pick` puts, for a streamed episode, releases whose name carries that season and episode ahead of season and series packs (stable inside each group, nothing is dropped, downloads and films unchanged). A release name that already names the episode means the torrent's file is known, so Umbrella does not scan the pack. Test: test_deck_picker (host). Device unverified.
- Not fixed: a pack is still slow when it is the only choice, and the 7-10 s listing is Umbrella's own (its source is not in this repository; it comes from the owner's backup). Patching Umbrella's pack resolver would need that source.
- Checked and not a cause of the AirPlay lag (ISSUE-491): second tries on Drive reads cost 40 ms (attempt 1 median 349 ms, attempt 2 386 ms), but each read runs on its own thread and so opens its own connection (1,644 threads for 2,737 reads), about 350 ms of handshake per 1 MB block; sharing connections across threads is a possible later saving, not done.

## ISSUE-493: Two season rows at the top of a show page (owner screenshot IMG_0693, 2026-11-26)
- Symptom: the pinned season row (meant for after scrolling) showed above the page's own season row with the header hidden behind its black backdrop; "it should only appear when I scroll down".
- Cause: its condition was `Container(9900).HasPrevious`; for a group list Kodi 21.3 answers that from `m_scroller.GetValue() > 0` (CGUIControlGroupList::GetCondition), i.e. from the first pixel of scroll.
- Fix: `pinned_visible` also needs `!Container(9900).HasNext`: the page's own season row is the last thing before the episode list, so the group list is scrolled to its end exactly when that row has left the screen. Test: test_show_season_row (host, source-read semantics of HasNext). Not seen in the desktop rig or on the device.

## ISSUE-494: Umbrella episode opens 16-38 s when the pick is a big pack (owner log e41f48ad, build 711)
- Measured (pick -> OpenFile, unlocks): Dragon Ball E01 15.8 s, 26 unlocks (files from S01E03 on, in no episode order); E02 3.1 s, 2 unlocks; Fullmetal Alchemist: Brotherhood E03 38.2 s, 158 unlocks of 3.4 GB remux files; scrape before the list 4.9-6.4 s. After the pick Umbrella unlocks the files of the picked pack one after another (about 0.25 s each) until it has the episode; ISSUE-490 keeps our own check out of it ("not checked"), ISSUE-492's ordering did not help here (the lists named only packs).
- Also wrong: the "no picture" verdict (and the source ranked last) fired at the very moment "streams ready" was logged after 38 s of Umbrella scanning: the 30 s clock ran from the tap.
- Fix 1: Umbrella AllDebrid's `_get` is wrapped (`umbrella_recovery.cache_hook` / `wrap_get`, one block appended to its alldebrid.py, idempotent, a no-op on another shape) so a repeated 'link/unlock' of the same locked link is answered from memory for 10 minutes; the selected-file record and the one check per pick still run on every unlock. The first pass over a pack is as slow as before; the next episode of it and a reopen are not. Fix 2: no picture is judged 20 s after streams ready (and 30 s after the tap). Tests: test_umbrella_recovery (UnlockCache), test_open_timing (host). Device unverified.
- Not fixed, needs Umbrella's source (permission to fetch it was declined): pick the file by name from the pack listing so the first pass unlocks one file, not all.

## ISSUE-495: AirPlay picture stutters for a few seconds, 10-bit HEVC (owner, 2026-11-25, build 722) - cause not proven; one timestamp defect reproduced on the host; tracking extended; Python tracking in build 725; timestamp fix and counters in framework r77 and build 730; device unverified
Owner times (episode timer): 12:30 and 13:50-14:00; an earlier report of 2 stutters in about 8 minutes had no times. Logs 51880851 / f63176b1 / 6d593313 are one session (each longer than the one before).

Phone side at those times (log evidence; AirPlay log lines are drained every 5 s, so their clock is +-5 s):
- 12:30 is about 21:01:26. The segments covering it (89-90; segment 91 starts at 758.506 s) were sent by 21:00:26. 13:50-14:00 is about 21:02:46-56; segments up to 103 were sent by 21:02:21 (segment durations seen are 6 s or more, so those cover it). No buffer-empty or waiting state in the 30 s samples, which are too far apart to show a short stutter. Dropped frames are not recorded by build 722.
- A Drive cache refill began 21:01:23.9 (to 21:01:40.9), next to the first stutter; no refill is logged near the second.
- Separate trouble, 21:00:26-46: video segments 91/92/93 took 3.7/9.4/7.7 s (source I/O 2.4/8.4/6.7 s), audio 92/93 waited 9.1/8.2 s, one audio send failed, and the TV player logged -12889 "No response for media file" for seg92 (6.506 s) and seg93 (7.132 s). The same two texts were logged again at 21:01:01, 21:01:31, 21:01:41 and 21:02:21 (each is a further entry in Apple's error log; no new request for those segments is logged then; meaning unknown). The TV had asked about a minute ahead of its picture. Drive first-byte times 21:00:20-50: median 389 ms, slowest 1058 ms.

Stream structure review (source reading and host script; the MP4 muxer output was NOT checked: FFmpeg 8.1.1 could not be downloaded here, ffmpeg.org and codeload refused, and it is not in third-party-sources-1):
- DEFECT (host reproduced, scripts/airplay_ladder_check.py, real gm_ts.c, imitated segment cut, synthetic 60 s Main10 23.976 fps): the video decode ladder starts `video_delay + 2` frames (4) before the segment's first keyframe. In open-GOP HEVC, frames shown before that keyframe are decoded after it; with 8 B-frames (5 such frames) gm_ts raises the picture time of 148 of 192 frames in each segment by up to 3 frames, and 274 of 1439 frames end up sharing a time with another (adaptive B-frames: segments 1,2,4,5 moved 134/68/119/154 frames, up to 4 frames; 172 shared). Decode times also jump or overlap by up to 5 frames at joins when the count differs between keyframes. Closed GOP and open GOP with 4 B-frames: none of this in the same script. This breaks gm_ts.h's promise that PTS is never altered. NOT known: whether the owner's episode is open GOP with more than 2-3 leading frames, and whether the TV shows this as the reported stutter.
- Same cause class: both playlists declare EXT-X-INDEPENDENT-SEGMENTS whatever the keyframes are; a segment opening on an open-GOP (CRA) keyframe with skipped leading frames is not independent.
- BANDWIDTH is max(8e6, 2.5 x file average) (kr_hls.c), here 10,975,491; segment 92 alone is about 18.6 Mbit/s (video 14,789,108 + audio 313,998 bytes over 6.506 s). Apple's authoring appendix asks the measured peak to be within 10% of BANDWIDTH for VOD. One variant only, so no link to stutter is shown.
- Segments follow the source keyframes: 6.05 to 13.35 s seen (Apple: about 6 s, keyframes every 2 s, SHOULD). Only a re-encode changes that.
- Read as correct in source: version 7, EXT-X-MAP, TARGETDURATION = ceil of the longest, hvc1 tag, VIDEO-RANGE=SDR, FRAME-RATE from the stream. Not checked: tfdt/trun/edit list in produced files, variable frame rate sources, A/V drift, anything specific to 1920x960.

Candidate fix for the defect (not applied): one constant lead of 16 frames in both ts_init_for and metadata_edit (gm_stream.c; they must agree, the init segment's edit list is built from it). On the same samples lead 16 moves no frame and shares no time, but the uneven joins remain; removing them needs the ladder anchored on the earliest picture time of each segment, which must be checked against movenc's tfdt/edit-list handling. Keeping the source's own DTS looked clean in the script but changes pts-dts per segment, so it is not safe without that check. test_remux.c's start (+-0.15 s) and gap (<0.17 s) checks may need review. Add an open-GOP B-frame fixture there.

Late-segment candidates (none applied; no change to drive_proxy):
- Pooled keep-alive connections in drive_proxy.Upstream: saves the ~350 ms handshake per block; shared with normal Kodi playback, risk of stale or cross-thread connections.
- Audio reusing the video read's bytes (native): at 21:00:41 audio waited on its own source read (9.5 s) beside the video read (8.4 s); needs a framework rebuild and a bounded shared cache.
- Deeper segment lead: the cast lines mostly show a lead of 0 segments; costs memory (segments up to 14.8 MB) and Drive reads in advance.
- Pausing background Drive jobs: no upload or preparation job was running in these snapshots, so no evidence for it.

Tracking added (no playback change): Python logs `Kodi iOS AirPlay sample:` every 5 s while a cast is active and a `counter_change` event when dropped frames or stalls rise. Native (build-airplay.sh, NOT compiled): kodi_airplay_health also reports access-log events, dropped frames, stalls, observed/indicated bit rate, downloaded and transfer seconds, and seconds loaded ahead (-1 = no value; Apple may give none while the TV fetches the stream). With pinned r76 only position and state appear. The Apple TV's frame-rate or dynamic-range switch is not available to the phone's player and is not logged.
Framework rebuild needed (owner to be told first, not started): airplay-remux.yml (host tests + iPhoneOS candidate, publishes nothing), pin the new tag/sha256/run in source-lock.json, airplay-ios.yml with publish_verified_candidate (publishes a release: needs owner approval), then the IPA build.
Build: import-review run 725 on 4ac6b2f succeeded (its test step included), IPA in prerelease build-725; framework still r76, so no native counters.
Retest: scripts/test_airplay_diagnostics.py (host). Regression protection: its counter, sample-line and native-key tests. Device unverified. Owner test: replay the same two spots (a repeat at the same spot points to the file/stream), same spots on the phone itself, an 8-bit H.264 episode cast to the TV, note clock times and any frame-rate/HDR switch.
Host run 2026-11-25 of the import-review test step on Python 3.13 (not the CI's 3.11 and provider fixtures): 241 of 242 commands passed; scripts/test_seek_release.py could not run here (it downloads Kodi source from raw.githubusercontent.com, refused by the network; it fails the same way on a clean copy of 6788558).
Fix, 2026-11-26 (owner approved a test rebuild, not publication): gm_stream.c video_lead() gives HEVC a 16-frame ladder in both ts_init_for and metadata_edit; other codecs unchanged. Local real-muxer check (system FFmpeg 6.1.1 movenc, timestamps set with the setts filter to imitate gm_ts, not our code path): lead 4 wrote 287 of 1439 and 169 of 1439 wrong picture times on two open-GOP samples and 210 of 960 on the new fixture; lead 16 wrote none on any sample. Not fixed: decode-time overlap or gap of a few frames where two segments have different leading-frame counts; EXT-X-INDEPENDENT-SEGMENTS on open GOP. Regression protection: test_remux.c test_open_gop_times (fixture hevc_open_gop.mkv) compares every served picture time with the source; check_rendition now measures a video rendition's start and end by picture time. CI, 2026-11-26: run 45836652644 on 2fddc56 failed to compile the new test (start_session used before its declaration; fixed in 62b3656 by declaring it first; the host-test compile is the regression check). Run 45838061070 on 62b3656 passed: host tests with FFmpeg 8.1.1 (3990 checks, 0 failed, including the open-GOP picture times), preview strip, end-to-end conversion, and the iPhoneOS framework compile with the native counters (artifact KodiAirPlay-source-candidate). The old 4-frame lead was not rerun in CI, so the defect under 8.1.1 is shown by source and the 6.1.1 check, not by a failing CI run. Framework not published, pin still r76, IPA unchanged, device unverified.
Release, 2026-11-26 (owner approved publishing the component and building an IPA): airplay-ios run 45841020117 published kodi-airplay-r77 from the verified candidate (sha256 5e26637e..., matches the pin); import-review run 730 on f07c173 passed and published prerelease build-730. Nothing merged. Phone and Apple TV retest pending.

## ISSUE-496: check_project.py failed on the branch: docs/ISSUES.md over 1,000,000 bytes (2026-11-25)
- Seen: `oversized-file` for docs/ISSUES.md on a clean copy of 6788558 (1,004,083 bytes), before any change of this session. The import-review workflow does not run check_project.py, so the build did not show it.
- Cause: the register grew past the limit with 8e76faf, the ISSUE-491/492 commit (1,001,686 bytes; 998,497 one commit earlier).
- Fix: ISSUE-001 to ISSUE-138 moved verbatim to docs/ISSUES-ARCHIVE.md, with a pointer here.
- Retest: python3 -B scripts/check_project.py (host). Regression protection: the same check, which must pass before committing.

## ISSUE-497: test_conversion_speed.py has one stale source-text check (2026-11-26) - open
- Seen: AirPlayGetsTheLine.test_read_ahead_while_a_video_plays fails on a clean copy of 6788558 as well as here. The import-review workflow does not run this file.
- Cause: the test expects the read-ahead loop in drive_stream.py without the later `or getattr(stream, 'serial', False)` condition.
- Fix: not made (unrelated to ISSUE-495). Retest and protection: python3 -B scripts/test_conversion_speed.py.
