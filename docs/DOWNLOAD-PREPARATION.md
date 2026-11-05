# One-file preparation for Kodi and AirPlay

Owner request, 2026-11-05: scan existing downloaded movies/shows at startup, show preparation progress,
and add preparation after each new Drive upload. Keep ONE file, matching the source's selected resolution:
4K stays 4K, 1080p stays 1080p, compatible HDR stays HDR. No permanent AirPlay variant.

## Supplied build-151 log

The new diagnostics establish the updated AirPlay framework ran. It cancels/retire speculative decoding,
but a forward seek requests converted segment 183 while another foreground request is still ahead of it.
That target waits 20,812 ms. The prior segment takes 20,770 ms, including 17,712 ms of source I/O.
The player stops; subsequent target requests report `session stopped`. This differs from the earlier
false-fatal `video conversion: cancelled` defect. Raw logs, Drive IDs and URLs remain private.

## Resulting behavior

- After setup, an idle worker scans app-created `Kodi Downloads/Movies` and `TV Shows`, including existing
  folder branches, and repeats after uploads and periodically for newly discovered files.
- Download → upload original → prepare and verify → update the SAME Drive ID using a resumable media
  PATCH. Library routes and saved IDs remain stable; no second folder/file is created.
- Compatible H.264/HEVC video is copied packet-for-packet, retaining selected resolution, frame rate and
  HDR/Dolby configuration. Unsupported SDR video uses source dimensions, not the live 1080p fallback.
  Non-AAC audio becomes AAC; selectable text subtitles become MP4 text tracks.
- The MP4 has a front-loaded sample index and must pass duration, dimensions, HDR, track-count and
  mid/end seek checks before its bytes can replace the original. Drive size/MD5 are verified again before
  marking ready and removing temporary work. Concurrent source version changes stop replacement.
- Notifications shows the running stage, percentage and queue count. The Library/Drive setting can pause
  preparation. Playback pauses it too. Download, conversion checkpoints and resumable upload survive restart.
- Prepared MP4 playback uses independent HTTP byte-range readers on the phone's Wi-Fi address. It has no
  conversion lane, subtitle burn-in, speculative segment queue or automatic 1080p compatibility restart.
  A long seek can request the indexed target directly. Network/receiver limits still apply.

## Storage and acceptance boundaries

Only one movie's temporary working set is allowed at a time. Source plus conversion spools/output require
free phone space; the worker pauses when space is insufficient. It never removes the Drive movie to free
space before verification. Failed preparation retains the existing file; unsupported tracks are reported,
not silently discarded. Image subtitles that cannot be preserved in MP4 and HDR codecs that cannot be
converted without losing HDR currently keep their original file and report a blocked job. H.264/HEVC
4K/HDR source copying is covered by real media fixtures; sustained iPhone throughput and the actual Roku's
4K/HDR decoding remain physical-device acceptance steps. No source-resolution claim means every receiver
supports every source profile.

Validation is tracked in `reports/download-preparation-validation.json`. Initial native tests exposed an
existing stop wait (5.27 s); sockets are now registered/shut down and requests finish before session state is
freed. A new idle-client regression covers this lifecycle. Earlier failures are retained in the report.
