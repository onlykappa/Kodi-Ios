# Handoff: AV1 speed (r24), state at 2026-11-06 ~22:30 UTC

Branch `claude/trusting-euler-kgug98`. `main` is at 1ce20eb (r23 pinned). This branch adds the r24 source (below),
NOT built, NOT pinned. Owner: "max this out, we got great hardware in this phone".

## Done and on main
- Build 175 (main ddeeb35): r22 converter (per-frame notes), History fixes, header buttons (gear, thin bell arc,
  refresh on Home/Movies/TV), Settings keeps the More menu rows. Verified IPA.
- f92238b: `drive_stream._Blocks`: Drive read in 8 MB blocks, fetched once, 12 kept, next fetched ahead.
- 3bdb079 + 1ce20eb: r23 (each converted track made on its own thread) pinned (sha dabd6c69…, run 42303303269) and
  PUBLISHED as release kodi-airplay-r23. Python: a playing video pauses a conversion in place (Native.convert_to
  paused/waiting, prepare_cloud Sink alive=keep_going or paused, service `preparation.paused`).
- Build 176 made and verified (main 55dd44d, r24 pinned and published). Waiting for the owner's 10-minute log.

## On this branch only (uncommitted before this file; now committed): r24 source
- `kr_video.c`: hevc_videotoolbox gets `prio_speed=1` during preparation (v->offline).
- `kr_prepare.c`: generated tracks are "lanes": a hardware-decoded picture uses VIDEO_LANES=2 lanes (own source,
  decoder, encoder each); lane l makes units l, l+n, ...; muxer takes them in order (`next_segment` check).
  `KR_PREP_LANES` env forces lanes for host tests. Audio = 1 lane.
- `tests/test_remux.c`: two-lane AV1 HDR conversion test in `test_hdr_preparation`.
- `scripts/test_conversion_speed.py`: AV1Speed tests; Build173/175 tests updated to lane names. All Python tests pass.

## Next steps (in order)
1. Dispatch `airplay-remux.yml` on this branch; if green (both jobs), take the candidate artifact's inner
   KodiAirPlay.framework.zip sha256 (download via actions artifact, unzip), pin r24 in
   `migration/airplay-ios/source-lock.json` (previous = r23 dabd6c69…), update `scripts/test_airplay_remux.py`
   expectations, commit, fast-forward main, dispatch `airplay-ios.yml` with publish_verified_candidate=true on main,
   then `import-review.yml` on main → build 176. Verify IPA (build.json commit, AirPlay binary sha equals candidate).
   If host tests hang on apt: cancel run, `rerun_failed_jobs` (framework artifact keeps its sha).
2. Consider raising `drive_stream.KEEP` to 16 (two video lanes ~2 units apart + audio).
3. "Max it out" ideas not done: 3 lanes if the device log shows the engine is not saturated; resume after Kodi restart
   (fMP4 fragment_index continuation) — biggest remaining loss; make AV1 movies wait behind quick ones (owner offered).
4. Owner asks for logs: look for `prepare: unit started via`, `N frames in S s (F fps)`, `video i/n made in`, `lane 1/2`.

## Context
- Build-175 log: video 37 s per 30 s unit (22.5 fps, hardware HDR av1→hevc_videotoolbox), each audio track 23 s,
  serial → 83 s/30 s. Expected after r23+blocks: ~37 s/30 s; r24 should approach 2x on top.
- UI work notes: docs/UI-SESSION-PROGRESS.md; build history: docs/HANDOFF-PROGRESS.md.

## Roadmap (priority order)

### 1. Ship what is written (small, do first)
- r24 through CI → pin → publish → build 176 → verify IPA (steps above).
- Ask the owner to leave Inception converting 10 min with Kodi on screen and send the log; confirm the
  `fps` lines and `lane 1` / `lane 2` both appear, and that audio units no longer add time.

### 2. Measure, then tune (needs the 176 log)
- If video fps roughly doubled: try VIDEO_LANES=3 (one constant) and watch memory (iOS kills apps over the limit,
  lower in the background). Raise `drive_stream.KEEP` to 16–24 if the lanes drift apart (log: read_bytes grows
  faster than film time → blocks are being fetched twice).
- If fps did not move: the engine is saturated. Then options are lower output bitrate for re-encodes (`kr_video.c`
  offline bit_rate, now ~7 Mbit/s per 1080p area) or HEVC 8-bit SDR for non-HDR AV1.
- Background: `app_state.Pace` caps CPU at 60% of a core when Kodi is not on screen; hardware lanes use little CPU,
  but check the log's fps with the screen off too.

### 3. Resume after Kodi closes (biggest remaining time loss)
- Today a closed/killed Kodi restarts the movie from 0% (storage-free output cannot resume).
- Approach: the fMP4 output is init + moof/mdat fragments with absolute timestamps. Record, per committed Drive
  upload offset, the last complete fragment's end time and unit index; on restart skip units before it, open the
  muxer with `fragment_index` continuing and skip writing the init; the Drive resumable session (`drive_prepare.Sink`)
  continues at the confirmed offset. Needs a host test that stops mid-file, resumes, and `kodi_airplay_verify`s.
- Until then: pause-in-place covers video playback; tell the owner not to close Kodi during long AV1 jobs.

### 4. Queue behaviour (quick wins)
- Put re-encode jobs (probe `copy_video=False`, e.g. AV1) behind copy-only jobs so one long AV1 never blocks quick
  ones (owner offered this; not built). `prepare_cloud.process_one` candidate sort: add `job['probe']['copy_video']`.
- Show an estimate on Library status for AV1 ("about 1 h 30 min") from fps × duration once known.

### 5. UI still open (docs/UI-SESSION-PROGRESS.md)
- Customisation pages (round-4 mockups, `design/customisation-mockups`): not built.
- History as a row on Library status: owner not asked again.
- PR #13 still open against `feature/library-status`; its content is on main — can be closed.

## Recommendations
- Keep every converter change behind a host test (two-lane test exists) and verify each IPA's AirPlay sha against
  the candidate artifact before telling the owner it is ready.
- Do not raise lanes and cache together; change one, read one log.
- Advise the owner to prefer HEVC/x265 HDR10 releases: they prepare in minutes (picture copied); AV1 will always
  cost a real-time-or-slower re-encode on the phone.
- Pace builds: one build per verified fix, with the owner's log in between.
