# Downloaded Drive startup and AirPlay investigation — 2026-11-16

Status: source fixes pushed in [draft PR #44](https://github.com/onlykappa/Kodi-Ios/pull/44); device validation pending. Branch: `fix/drive-startup-airplay-evidence`,
base main `222cd50`. One agent. No IPA, native release, publication or merge authorized.

## Scope and evidence rules

Investigate downloaded movie/TV Play → first picture first, preserving downloaded-first and resume.
Then investigate audio-playing AirPlay load failure, distinguishing receiver/video evidence from
state-machine inference. Raw supplied log, accounts, signed URLs and media stay outside Git.
Host fixtures and desktop Kodi are never iPhone/TV proof; comparable measured timings only.

## Checkpoint 1 — repository inspection

- Read AGENTS.md; reviewing ROADMAP, PROGRESS, ISSUES, DECISIONS and code.
- PR #32 merged 2026-11-15 (head `315ef79`); verify deployed source versus log separately.
- Open PRs #31 and #33–43 include unrelated subtitle/sports work; preserve those branches.
- Latest published IPA at inspection: build-557, 2026-11-16 15:47 UTC. Installed build pending log analysis.
- Native release list includes AirPlay r64 and portrait r33; main pins and installed pins pending.

## Validation and remaining checks

Initial checklist (results and deferrals recorded below): baseline measurements, focused regressions, available real Kodi rig tests, native tests,
`python3 -B scripts/check_project.py`, source review and draft PR. Device first-picture and actual
receiver playback/recovery checks require device evidence and remain explicitly unverified.

## Checkpoint 2 — downloaded playback findings and source fix

Installed build is **554**, source `7645171` on `claude/sports-jet`, run 43890669506;
AirPlay r64 (`5c122167…a028`), Kodi portrait r33, Glassbar r6. Main is older:
AirPlay r58 (`1bff47f3…c331`), same portrait/Glassbar. #32 and Umbrella repairs are
merged through main; their provider/cache route is bypassed by this completed Drive fast path.
Unmerged #42 fixes a startup-service syntax error on main; it is unrelated and not silently imported.

Supplied log (phone wall clock): Play-sheet tap 07:47:20.791; completed-copy handoff
21.275; OpenFile 21.312; demux 22.673; stream codecs 23.980; misleading streams-ready
line 24.009; decoded picture queued 24.959; fullscreen 24.976. Thus tap → decoded
picture queue **4.168 s**, not the logged 3.2 s. Actual display scanout is not logged.
Lookup/handoff is 0.484 s; InputStream 1.361 s; demux/probe 1.307 s; decoder/render
startup approximately 0.98 s to queued picture. These intervals overlap network work;
authentication versus each metadata/range read cannot be separated from this old log.
No comparable TV-episode/cold/warm device pair exists in the attachment.

Concrete source defect: first index range waits for an optional second live identity
request and cache disk write before returning already fetched bytes. Proxy now admits
indexes in bounded background work (two jobs, deduplicated per file). No unvalidated
index becomes reusable; changed identity, disk failure and failed reads preserve ordinary
streaming. Downloaded lookup, selected file, resume, codecs, tracks and seeking unchanged.
Safe auth/header timings added without addresses or identifiers. Streams-ready logging
now says first picture is not measured; native source adds a first-frame-render-submission
marker. **Native pin unchanged; renderer marker requires a future approved build.**

Comparable loopback HTTP fixture, five fresh-proxy repetitions per mode, 200 ms per
metadata response, identical 195-byte synthetic file and index range: synchronous cold
median **0.4098 s**, deferred cold **0.2021 s**; warm **0.00108 / 0.00137 s**. This
isolates removal of one optional metadata wait; it is not a device startup improvement.
25 index tests, 25 proxy tests and 9 timing tests pass. Required project scanner passes.
Original rig setup failed (no sudo); isolated desktop runtime setup continues.

## Validation prerequisite — main startup syntax defect

The AirPlay lifetime regression failed before exercising playback: main's `service.py`
places provider-hook statements between `if` and `elif` (SyntaxError, line 127).
PR #42 already contains the exact repair. Applied its service-only change and bundle
syntax regression here as a separate prerequisite; did not import sports/subtitle/native
pins or merge #42. This was present on the base and is not a new playback regression.
The project scanner alone did not catch it, so the syntax suite also runs explicitly.

## Checkpoint 3 — AirPlay findings and source repair

The receiver connected. It fetched its master, converted-video init and audio segment
(3,186,501 bytes, 200); `tv_media=1`, `tv_video=0`. The phone had earlier received an
8,525,981-byte copied-video segment; that is **not TV video delivery**. The TV retried
`cvideo/seg0` four times; all ended 500 / zero bytes after the player failed at
07:48:03.024. Its reported position stayed 3.555 s while rate=1 and external=1.
The owner's heard audio is consistent with these records. AVPlayer failed after 32.5 s;
this was not the controller's 105-s startup limit and not a false no-connection case.
No completed TV video payload or displayed receiver picture is established by the log.

Native inspection selected segmented playback because storage fragments reach 70.3 s,
then sample inspection failed and replaced the timeline with only 99 storage boundaries.
Those boundaries were also used by H.264 conversion, which needlessly had to encode a
large storage window before returning its first video unit. Its segment 0 was canceled
after 20,678 ms with cursor I/O 0 ms. A different copied-video read-ahead took 23,395 ms,
including 11,174 ms cursor I/O; the controller used that unrelated evidence to blame Drive.

**Important measurement limit:** 0 ms cursor I/O does not exclude waiting on another
cursor filling the shared cache. The old log lacks that counter and frame progress, so
it cannot divide all 20.7 s into encoder work versus shared-read waits, or explain why
the metadata scan failed. No common Drive bottleneck is established. The reproduced
source defect is the unbounded converted media window and the cross-lane diagnosis.

Repair: when copied windows exceed 10 s, conversion gets an immutable six-second timeline.
Its audio uses that same grid, separate `/caudio/` URLs and cache keys; the locked audio
reader adopts the appropriate grid per request. Copy clients retain their complete
original keyframe plan and compressed picture. Selected captions continue burning into
the converted picture; copy captions stay unchanged. Seeking, cache/prefetch bounds,
cancellation and cleanup choose the correct rendition timeline. No timeout increase,
codec/bitrate/resolution change or new visible wording. The existing failure/retry card
remains available; slow-Drive diagnosis now requires the failing conversion lane's read
measurements. Native logs distinguish this cursor's I/O from shared-cache wait time.

Before/fixed host reproduction (same 32-s long-GOP fixture and FFmpeg): old source exposes
one 32.023-s converted segment, regression fails; fixed exposes six segments, maximum 6 s,
matching audio, all 768 decoded frames, continuous packet timestamps after the initial
edit-list anchor, start/end A/V difference <80 ms, and actual burned-caption frames.
Copy packet digest remains exact. Out-of-order seek, restoration of copy-audio grid,
active read-ahead cancellation and next-session recovery pass. This compares media windows,
**not device startup time**. Test uses the host MPEG-4 encoder in place of VideoToolbox.

## Checkpoint 4 — validation and retained failures

- 16 Python suites / 265 tests pass (includes state-machine audio-only/video-delivered,
  failure, cancellation, recovery, native exports and compiled C++ startup snippets).
- Seven real native host groups: 375 checks, zero failures: source 39, startup 23, seek 12,
  subtitles 8, streaming 141, recommendations 41, long-fragment/Roku 111. The final shared
  library additionally passes `sparse_compat.py`; source transport retest against the final shared library passes 39/39 after added counters.
- Five actual Foundation transport tests **skip on Linux**. No Objective-C/VideoToolbox/iOS
  binary validation or receiver/device acceptance is inferred.
- Real desktop Kodi **21.2 Debian / Estuary / Xvfb** runs production proxy code against
  synthetic Drive-interface bytes. `scripts/rig_drive_startup.py` passes cold, warm,
  18-s resume, slow headers, failed requests, recovery, canceled open and next-open recovery.
  Saved screenshots inspected: real synthetic picture, resume frame at 18 s. These use
  JSON-RPC Player.Open, not the app's full watch/skin/library-lookup path. Timeline advance
  plus a later screenshot is not a precise first-picture measurement. No desktop before/after
  improvement asserted. Requested 21.3 portrait rig remains unrun (standard setup lacks sudo).
- Initial desktop fixture invocation incorrectly passed an unsupported JSON-RPC option;
  fixed the harness to check errors and removed it. Null ALSA sink configured for headless
  playback. These setup failures were not app regressions.
- Existing native string-wiring tests needed updates for the new audio paths; then passed.
- A stricter packet-continuity test initially rejected the first packet's existing edit-list
  anchor / missing reported duration. It now checks every later pair and all segment boundaries;
  A/V start/end bounds and 768-frame coverage remain asserted. No playback-code workaround.
- Renderer diagnostic patch applies to upstream 21.3 RenderManager sources; full Kodi engine
  compilation is not performed. Pins unchanged. Project scanner and diff whitespace check pass.
- Evidence receipt: `reports/drive-startup-airplay-validation.json`. Reproduce isolated cache
  timings with `python3 -B scripts/bench_drive_index_admission.py`; native regression is wired
  into the existing host CI job, without dispatching a build in this session.

## Remaining device checks / release boundary

Source work ready for draft review; no device fix claimed. Native source changes need a
future **explicitly approved** framework/engine build, verification and pin update before
an IPA could contain them. Main's r58 pin intentionally stays unchanged. The installed r64
branch has other later subtitle/cache work; that work was inspected and not overwritten or
pulled into this main-based repair. Integrate/verify against the chosen future native source
before packaging. No IPA, native release, publication or merge is authorized here.

On the actual iPhone/TV, after a separately approved build:
1. Same completed movie and TV episode, cold and warm, Play tap → visible first picture;
   correlate renderer marker, auth/header metrics, metadata/index and shared-cache waits.
2. Resume and restart on phone and TV; seek forward/back, captions on/off/text/bitmap,
   audio choices and A/V synchronization, original resolution/quality on capable receivers.
3. First AirPlay attempt on the reported MFi receiver and an Apple receiver: confirm actual
   picture (not audio/rate/route alone), first video payload, short converted windows, time
   advancing, no premature error; repeat resumed handoff.
4. Slow reads, token rejection, failed ranges, Wi-Fi change, cancel while opening/converting,
   Try Again and Keep Watching Here, background/foreground and repeated-session recovery.
5. Long playback/end-of-file and seeking after changing captions. Retain private device logs
   and media outside Git. Capture video/stopwatch for scanout timing not observable in old logs.

## Publication checkpoint

Draft [PR #44](https://github.com/onlykappa/Kodi-Ios/pull/44), targeting unchanged main
`222cd50`. Source commits: `cfcc4bd` (Drive startup), `a41511d` (PR #42 prerequisite),
`9f93167` (AirPlay conversion and validation). Source pushed with `[skip ci]`; no build
workflow dispatched. Required project check passes before each commit. Dedicated progress,
ROADMAP, PROGRESS, ISSUES and the structured test receipt are committed. Device, 21.3 rig
and native Apple-platform gaps above remain explicit; no publication/merge approval requested.
