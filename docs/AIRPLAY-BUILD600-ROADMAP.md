# AirPlay build 600 phone findings and next work

Post-IPA602 controlled checkpoint: native run44648845367 passed84 audio replay
checks for finite-duration indexed/fragmented MP4s over HTTP. Reused readers
match fresh-reader media fragments across0→9→132→171→178 and backward/repeated
windows. This does not reproduce the phone's empty-audio window. Compare the
owner's r68 packet/window diagnostics next; exact source timing and concurrent
receiver ordering remain untested. Full run44647499269 also exposed a separate
retry-fixture assumption failure (transport recovery succeeded without the app
retry); do not describe the focused pass as a full regression pass.

Owner requested PR49 merge and a separate AirPlay follow-up. PR49 merged as
26291848d879989f78cb308ff761adec59d74bcf. This investigation preserves its bounded
priming retry; it does not claim that change solves all receiver-driven seeks.
The supplied phone log identifies build600/source684d54b and the r67 archive.
Raw logs/media/addresses remain outside Git.

## Evidence boundaries

Owner tested an Umbrella stream and a downloaded show, reporting TV response
timeouts on long streaming seeks and unreliable short/long downloaded seeks.
The log contains two MKV AirPlay openings, then an MP4 opening. The chronology
fits the owner's two workflows; container alone does not prove source origin.
Treat the MKV pair as the likely streamed attempts and MP4 as the likely
downloaded attempt until provenance is confirmed. A downloaded copy can still
be read from Drive, not necessarily phone-local storage. Successful segment
production is not proof of a visible picture or uninterrupted receiver playback.

## MKV / likely Umbrella attempts

- 14:52:39 starts MKV opening. Inspection reports H.264 High10/10-bit1080p;
  conversion to8-bit H.264 and subtitle burning are enabled.
- 14:52:53 primes at727.719s (segment121). Video+audio finish31.583s later.
  Audio read31.389s includes26.384s source I/O; video reports13.618s source I/O
  and15.737s shared wait. These overlapping parallel timings must not be summed.
- 14:53:30 player is near729.1s with external route active. By14:53:40 it is
  near729.4s. Segment122 needs5.251s wait plus9.683s production.
- 14:53:50 reports player failure. Segment123's subsequent cancellation is
  marked canceled=1; do not label that cleanup failure as the original cause.
- 14:54:05 second MKV opening; primes733.380s in41.607s. Some six-second video
  windows take7.456s or16.224s to produce, while later cached windows are fast.
  Playback samples advance to833.3s before close. A segment jump is not proof
  of a user command: AVPlayer prefetch/retry can change request order.

This shows slow preparation and inadequate per-window delivery in some periods,
not an independently established provider block or an isolated>10minute seek.
The on-screen TV timeout wording is owner's report; its exact origin/code
needs correlation. Conversion, source I/O, shared waits and receiver behavior
must be separated before changing timeouts or bypassing codec compatibility.

## MP4 / likely downloaded attempt

- 14:56:28 starts MP4 opening; inspection shows H.264 High/8-bit1080p. A converted
  video route is used; determine why (for example subtitle policy), rather than
  assuming compatible video should always be passed through.
- Primes from0 in3.621s. Requests then jump to segment9 (~54s); video production
  takes15.658s, although later requests reuse cached output.
- Further requests jump to132 (~792s) and171 (~1026s); video production takes
 9.551s and8.454s respectively. These outputs succeed server-side.
- 14:57:48 requests segment178 (~1068s). Its converted video succeeds in4.135s.
  The audio request first waits4.201s behind segment1, then returns empty with
  two scanned packets,0ms source I/O and result-1. Packet count is not a count
  of packets successfully muxed into the requested audio window.
- The same audio segment repeatedly fails in0–2ms with two packets and no source
  I/O, HTTP500, canceled=0 and deadline_expired=0. At14:58:18 the app reports
  buffering_without_progress; at14:58:23 native failure names empty audio178.
  Closed position is1073.1s, which is not proof the target played successfully.

This is the highest-priority concrete failure: video can be generated at the
target, but the independent audio reader repeatedly produces no usable output.
Fast repeated failures with no new I/O suggest reader/seek/window state to
investigate; they do not prove corrupt media, a dead source, or a particular
timestamp bug. PR49 retries in kr_remux_prime_for; ordinary receiver requests
go through get_part/HTTP serving. Test those actual call paths separately.

## Ordered roadmap and acceptance

### Source trace: why conversion does not repair this audio failure

The MP4 log explicitly enables subtitle burning from source stream2, despite
its video being compatible8-bit H.264. Only the picture takes that conversion
path. `kr_remux.c` selects `KR_AUDIO_COPY` for the compatible audio track;
`audio_demuxer()` opens/reuses `S.agm`/`S.asrc`, adopts the segment plan, and
`gm_stream_track_unit()` reaches `produce_single()`/`produce_sel()` in
`gm_stream.c`. It seeks the selected stream backwards, scans packets, drops
packets before the window and stops audio-only production at the first packet
at/after its end. Zero written packets produce the literal `empty segment`.
The HTTP handler reports500, even if converted video succeeds independently.
Thus the confirmed failure mechanism is the copied-audio window producing no
muxed packets; the causal reason those two scanned packets do not fill the
window is still unknown. Native logs do not report their stream indices,
PTS/DTS or which loop exit occurred. Do not call this an encoder failure or
claim a particular seek-index/timestamp defect without reproducing it.

Next discriminating evidence: requested start/end, selected stream/time base,
seek return, bounded first/last packet stream+PTS/DTS, counts skipped before
the window/wrong stream, count written, and EOF versus end-window break. These
values should distinguish reader/seek position, timestamp alignment and actual
audio absence. Use synthetic fixtures first; keep any original media/packet
dump private. A repeated HTTP retry already occurs in the phone log and fails
the same way, so more blind retries are not a demonstrated solution.

1. **Reproduce MP4 audio178 first.** Use an authorized synthetic fragmented MP4
   with compatible H.264 and matching audio layout/time bases; reproduce the
  0→9→132→171→178 request sequence and out-of-order audio1 versus178. Trace
   selected-stream packets, seek return/cursor, timestamp origin, end-of-window
   breaks, reader reuse and cancellation. Keep diagnostic packet metadata
   bounded and private. If the exact source is essential, request a local
   authorized sample or sanitized stream/packet metadata around the failure.
2. **Fix only the demonstrated cause.** Verify whether resetting/reopening the
   audio reader or correcting window/seek logic is necessary. Do not add an
   unlimited empty-segment retry or mask errors with a silent successful audio
   segment. Test receiver HTTP seeks as well as initial priming, backward and
   short seeks, repeated target, concurrent old/new requests and replacement.
3. **Investigate MKV delivery latency.** Reproduce High10 decode + subtitle burn,
   independent audio and constrained source reads. Measure I/O, lock/shared
   wait, conversion and HTTP delivery independently, cold and warm. Preserve
   the supported codec conversion policy and compare subtitle on/off where
   appropriate. Do not treat a larger timeout as a performance repair.
4. **Verify recovery and position.** Distinguish receiver failure from ensuing
   cancellation; exercise failed seek, normal close, rewind0, Continue Watching,
   replacement and pause intent. Mark phone/provider-specific behavior pending.
5. **Validation/release gate.** Register meaningful regressions, run full import
   and native host suites, compile/inspect a new candidate if native code changes,
   document failed reproductions, and obtain new owner approval before another
   framework publication/IPA. No build/merge is authorized by this roadmap.

Do not claim an arbitrary completion percentage or universal seek reliability.
The next deliverable is a deterministic audio-window failure reproduction and
measured explanation, followed by a tested minimal fix.
