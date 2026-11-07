# Resume a conversion after Kodi closes (design for r29)

Owner: a closed/updated/killed Kodi restarts the movie at 0% ("nice for app updates"). Playback already pauses in place
(build 176+). This is the design for continuing after a process restart. Not implemented yet.

## Why the simple plan in HANDOFF-R28 is not enough
Drive's resumable upload only continues at the offset Drive confirmed, and confirms in 256 KiB multiples (we send
32 MB pieces). A fragment boundary (where a muxer can restart) almost never equals that offset, and the bytes after the
boundary cannot be made again identically (the hardware HEVC encoder is not bit-exact). So the upload must never send
past the last safe boundary, and the few bytes between Drive's confirmed offset and that boundary must be kept.

## Pieces
1. **Safe marks (native, kr_prepare.c, main output sink).** Parse the top-level boxes of the main MP4 as they stream
   through `sink_write` (sizes from box headers; mdat skipped by size). A *mark* is the byte offset of a `moof` whose
   video `traf` starts with a sync sample (first_sample_flags / tfhd default flags, non-sync bit 0x10000 clear). For
   each mark record: offset, mfhd sequence number, and per track_ID the decode end time so far (tfdt + sum of sample
   durations of its previous trafs; durations from trun or tfhd/trex defaults, trex from the init's mvex). Report each
   mark to Python through the writer callback (a reserved track number, JSON payload), and keep every moof's
   (track_ID, tfdt, offset) for the final `mfra`.
2. **Upload only up to a mark (Python, drive_prepare.Sink).** Track 0 sends pieces that end at or before the latest
   mark, rounded down to 256 KiB (still 32 MB pieces when far from a mark). When Drive confirms C: checkpoint =
   {mark M (largest mark ≥ C... ≤ buffered), its JSON, Drive session url, C, bytes [C, M) — under 256 KiB — saved to a
   small file next to preparation state}. Write the checkpoint atomically in the job.
3. **Sidecars (.sup).** Write them to small local files (append) instead of uploading on the fly; the mark records
   each sidecar's length. Upload them when the movie finishes (they are a few MB). On resume truncate to the recorded
   length.
4. **Restart (native).** New entry `kodi_airplay_prepare_resume(input, resume_json, ...)` or a resume argument:
   - generated video: start both lanes at the unit whose start time equals the video end time (it is a unit start
     because marks need a sync sample and generated video only has keyframes at unit starts);
   - generated audio: start at the unit containing its end time, drop packets with dts < end time;
   - copied tracks (original source): seek the source before the smallest end time, drop packets with dts < each
     track's end time;
   - muxer: same output streams, `fragment_index` = next sequence, the init it writes is discarded (already on Drive);
   - trailer: replace movenc's `mfra` in the stream with one built from every recorded moof (both sessions); `mfro`
     with its size. `trun` data offsets are moof-relative (default_base_moof), so no other absolute offsets exist.
5. **Restart (Python, prepare_cloud).** If the job has a checkpoint and the source identity is unchanged: open the
   Sink on the saved session at C, feed it the saved [C, M) bytes, then the converter's output from M. Skip the local
   md5 (Drive's md5 + kodi_airplay_verify decide). Otherwise start over as today.

## Tests
- Host (test_remux.c): convert half (cancel after N units through the progress callback), take the last mark, resume,
  concatenate output = first part up to the mark + resumed output; `kodi_airplay_verify` passes, sample count and
  duration equal a full conversion; for copied-video files the result is byte-identical to a straight run.
- Python: Sink never sends past the latest mark; checkpoint written only after Drive confirms; resume feeds the saved
  tail first; a changed source discards the checkpoint.

## Effort and order
Native parser + marks + mfra rewrite (largest), Sink mark-aware upload + checkpoint, sidecars to local files,
resume entry + Python restart, tests. Own release r29 and build. Do it as one PR with the host test first.

## Findings from FFmpeg 8 movenc.c (read 2026-11-07)
- `tfdt` = `cluster[0].dts - track->start_dts`: decode time relative to the FIRST packet the muxer saw for that track
  in this session. A resumed muxer would restart every track's tfdt at 0 → broken timeline. Fix: before the resumed
  packets, write one priming packet per track with dts = that track's first dts of session 1 (recorded), force a
  fragment flush (`movflags +frag_custom`, `av_write_frame(out, NULL)`), and drop that fragment's bytes (and the
  init) in the sink. Then start_dts matches session 1 and tfdt continues.
- tfra entry: `time = cluster[0].dts + cluster[0].cts` (absolute, clamped at 0), `offset = moof start + data_offset`,
  traf/trun/sample numbers all 1, one `tfra` per track that had fragments; `mfro` holds the mfra size. Rebuild it from
  parsed moofs as `time = tfdt + start_dts + first sample's cts` (cts from trun when its flags carry composition
  offsets; copied HEVC can have B-frames).
- Record per output track at session start: first dts (track timescale = out->streams[i]->time_base after
  avformat_write_header).
