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
- Build 176 has NOT been made yet. Next build number from import-review will be 176.

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
