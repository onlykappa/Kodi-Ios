# Handoff: state at 2026-11-07 (after build 182 started)

Branch `claude/trusting-euler-kgug98` = draft PR #14. `main` = same commit (b65cf2e). Every change below is
committed and pushed; nothing is only local. Builds are started by hand; commit with `[skip ci]`.

## Builds since r24 (details per build in docs/HANDOFF-PROGRESS.md)
| Build | What | State |
|---|---|---|
| 176 | r24: HEVC prio_speed, 2 hardware video lanes | verified, owner tested (~1.8x real time, upload-bound) |
| 178 | background 32 MB Drive upload thread, Transfers + movie sheet redesign, Play / Play on TV | verified, owner tested |
| 179 | r25 only | not given to the owner |
| 180 | r26: stuck unit remade after 90 s, off-screen CPU decode, Start converting now, audio = original + English | verified, owner tested |
| 181 | r27: upload once (promote + bin), English subtitles only, subtitle uploads on own threads, AllDebrid read-ahead | verified, owner testing (Interstellar ~40 min, works) |
| 182 | r28 keep-awake re-armed on background/foreground, Drive read 4 blocks ahead in parallel, Home hero copy compared without page, quick movies first | verified (IPA sha 90ead4df…, build.json b65cf2e, AirPlay binary = r28 release ec5249b9…) |
| 183 | 182 + Transfers never says "Nothing is moving" during a conversion | built (superseded by 184, not given) |
| 184 | r29 (prepared AirPlay through one source + 48 MB cache; pinned 80346abc…, run 42328810669) + upload and read-ahead wait while a video plays + 183 | verified (IPA sha f52c5e0f…, build.json df4b22c, AirPlay binary = r29 release 4a310154…). Owner testing AirPlay |

r28: pinned in `migration/airplay-ios/source-lock.json` (sha 34b0d61b…, CI run 42326849053) and published
(release kodi-airplay-r28, digest matches).

## Next steps, in order
1. **Build 182**: when run 42327383714 ends, download release build-182, check build.json commit = b65cf2e, airplay
   tag r28, binary sha = candidate of run 42326849053; record in HANDOFF-PROGRESS; give the owner the link.
2. **DONE in 183.** Transfers said "Nothing is moving right now" at random while converting (owner screenshot, build 181). Two
   causes, NOT fixed yet:
   - `transfer_history.running(fresh=10)` while `watch()` saves every 10 s: the page reads a record up to ~10+ s old.
     Fix: fresh=30 (and/or save every 4 s).
   - `transfer_history.activity`: conversion counted only if prep `current.updated` < 15 s old; the muxer's progress
     callback stalls while a 32 MB piece uploads. Fix: 60 s, and `prepare_downloads.cards` (line ~846, `<15`) too.
   Add tests in scripts/test_transfers.py. Ship in build 183 (Python only).
3. **Resume after Kodi is closed** (owner asked: "nice for app updates"). Not started beyond reading the code.
   Plan (kr_prepare.c `prepare()` with a writer): fMP4 with `+empty_moov+default_base_moof+frag_keyframe`,
   `frag_duration` 6 s. Record per confirmed Drive offset of the main track the last complete fragment (unit index,
   end time, fragment sequence, byte offset); on restart: skip units before it, open the muxer with `fragment_index`
   continuing, drop the new init, continue the Drive resumable session (drive_prepare.Sink keeps url + offset) at the
   confirmed offset. The trailing `mfra` must list every fragment: either write our own mfra from the recorded list
   or rebuild it; `kodi_airplay_verify` must pass. Host test: stop mid-file, resume, verify. Sidecars (.sup) and the
   audio tracks need the same treatment. Big change: its own native release (r29) and build.
4. Elementum download settings checked (rate limits 0, connections auto, DHT on): left as they are.

## Owner decisions in this session
- Prepare everything ahead of time once; only Umbrella streams play live.
- Upload once (new Drive file id; watched/resume may reset once: accepted).
- Keep only the original audio + English, and only English subtitles (untagged ones kept). No lower picture quality.
- Quick (repack-only) movies before re-encodes; Start converting now overrides; Prepare next waits its turn.
- Conversion must keep going in the background (keep-awake) and never freeze.

## Known numbers (owner's iPhone 16 Pro, his line)
- AV1 4K HDR re-encode: ~2.5x real time with 2 hardware lanes (chip-bound); Inception ~1 h.
- Drive upload: 32 MB pieces 3-4 s on a good line (8-10 MB/s), 6-17 s when the line is busy.
- Copy-only 4K (Interstellar 8.4 GB): ~40 min in build 181; 182 should be faster (parallel reads).

## Session 2026-11-07 (after 182)
- 183: Transfers fix (built from 59156d6). AirPlay of Buddy failed in the build-181 log ("Cannot Complete Action"):
  every AVPlayer range opened a new Drive connection (1-6 s) and the line was busy with Interstellar's upload.
- 34fcf8b: while a video/AirPlay plays, the conversion's upload pieces (Sink.hold) and Drive read-ahead
  (DriveStream.hold) wait too.
- r29 source: kr_remux serve_prepared reads through one kept-open source + 4 MB x 12 block cache (prepared_read).
  Next: CI, pin r29, publish, build (184). Then owner tests AirPlay; then optional "gentle mode" during AirPlay only
  (keep converting with 1 lane, no read-ahead, upload capped ~50%) — owner agreed to step 1 first.
- Resume design: docs/RESUME-DESIGN.md (not started).

## Build 185 — verified (IPA sha 4721fe31…, build.json 1e8cc12, airplay r29 unchanged, find_quicker / STALL / deck_picker AVOID inside). Owner testing
(owner, build-184 log: AirPlay works; conversion slow and inconsistent for hours)
- Diagnosis from the log: converter ~2.5-3x real time on screen; the Drive upload stalled (32 MB piece hung 120 s,
  timed out) and the converter waited on the 2-piece queue; Kodi start restarted Inception from 0; playback paused it;
  off screen the picture decodes on the CPU (iOS refuses VideoToolbox off screen).
- 55b7309: stall retry after 45 s (driveupload.STALL), AHEAD 4, Elementum max_upload_rate 1024 KB/s when unlimited.
- 74f6129: background CPU share 0.7 (iOS ends background apps over ~80% of a core for a minute).
- 3154fd0: "Find a version without converting" (Library status sheet for re-encode movies → download.py replace=1 with
  Home property KodiIOS.AvoidAV1 "<quality>|<time>"; deck_picker shows only non-AV1 at that quality); AV1 links last
  and labelled in every picker; unique() keeps the copy that needs no re-encoding.
- Resume after Kodi closes: NOT in 185. docs/RESUME-DESIGN.md. Open question found while starting: the mfra rebuilt
  from parsed moofs must use movenc's tfra time (start_dts + tfdt + cts), and start_dts per track is not in the
  stream; options: write edts-free output (start at 0) or keep movenc's tfra entries by parsing each session's
  trailer. Do it as its own native release (r30) with a stop/resume host test.

## Build 186 — Python only (airplay r29 unchanged)
- 54d4e8e: picking "Find a version without converting" stops the AV1 conversion (prepare_downloads 'replace') and the
  AllDebrid download goes first.
- 426c094: long press on a transfer card in Notifications (the touch keymap's long press is a right click, which became
  "previous menu" and closed the page) → menu: pause / resume, cancel, speed graph. transfer_control.py holds the
  choices as files the service reads: paused-conv (same hold as playback), paused-up (Drive uploads and AllDebrid
  copies stop at the next piece, resumable), cancel-up (AllDebrid job ends as Cancelled). Cancel conversion = Keep as is.
- AirPlay (owner build-185 log, "airplay stops out of nowhere"): the TV's first range read of the prepared movie took
  12 s, the next ones ~19 s, while an AllDebrid copy went up to Drive and Kodi's paused player still read the movie;
  Apple's player timed out at 39 s. Now Window(10000) KodiIOS.AirPlay holds the time AirPlay was last seen working
  (cast.send_airplay marks it, airplay.relay refreshes it from Apple's player log lines, closed/stopped clears it,
  90 s expiry); while set, AllDebrid copies, Drive uploads, preparation (hold) and the library scan wait. A timeout at
  the start is retried once (cast.retry_airplay).
- Resume after Kodi closes (r30): native work in progress, NOT in 186. Design settled and coded, saved as docs/R30-RESUME-WIP.md (a diff; not built):
  av_write_frame + flush per packet so each fragment = packets between two fragment starts; sink parses moofs,
  rewrites tfdt onto run-1 timeline, builds its own mfra (+skip_trailer; tfra time = start_dts(first dts + FFmpeg's
  make-non-negative shift) + tfdt + first cts); marks via write(-1,"mark",text) at fragments starting on a video
  keyframe (re-encoded picture: unit start); kodi_airplay_prepare_resume seeks each input to its recorded next
  packet (original: pos/stream/dts; generated: unit containing the time, then exact dts). Host test
  test_preparation_resume (straight run vs run from a middle mark, byte-identical for copied tracks). Next: run the
  host test locally (FFmpeg 8.1.1 host builds fine from git clones; codeload/ffmpeg.org are blocked), then the
  Python side (Sink sends only up to the latest mark rounded to 256 KiB, checkpoint after Drive confirms, sidecars
  spooled locally), CI, pin r30.
