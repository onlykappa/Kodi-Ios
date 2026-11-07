# Conversion audit (build 190, KodiAirPlay r31)

Owner (after build 189: Interstellar "starting" for 5 minutes): "do a full rundown audit and tests on this conversion
shit im tired of going back and forth".

## How it was tested
`migration/airplay-ios/remux/tests/e2e_conversion.py` runs the real converter (KodiAirPlay built for Linux as a shared
library from the same sources and FFmpeg 8.1.1) and the add-on's real queue (prepare_cloud.process_one, drive_prepare.Sink,
resume_store, driveupload.sender over HTTP) against a local Google Drive stand-in: byte-range reads, resumable uploads
that keep only whole 256 KiB steps of an unfinished upload, optional slow uploads, sessions that can be forgotten.
Before this, the queue's tests used a fake converter, which is how the read-back problem below went unnoticed.

    bash migration/airplay-ios/build-remux-ffmpeg.sh host FF    # FFmpeg 8.1.1 for this computer
    cc -std=gnu11 -O2 -fPIC -shared -I FF/include remux/src/*.c remux/gmplayer/*.c -Wl,-Bsymbolic FF/lib/lib{avformat,avcodec,dav1d,swscale,swresample,avutil}.a \
       -lass -lx265 -lz -lm -lpthread -lstdc++ -ldl -o libkodiairplay.so
    python3 migration/airplay-ios/remux/tests/e2e_conversion.py libkodiairplay.so FIXTURES   # fixtures: run_host_tests.sh

Scenarios: copied H.264 with Blu-ray subtitles (sidecar), a 22-minute copy, a 100 MB copy, DTS → AAC audio, AV1 HDR →
HEVC re-encode (two sizes), each straight and interrupted ("Kodi closed": everything in memory dropped) at several
points, killed mid-upload (Drive kept part of a piece), an expired upload session, a corrupted checkpoint, a 300 KB/s
line. Checks: finished; in the movie's folder; original in the bin; marked prepared; subtitles beside it; nothing left
on the phone; how much the read-back check reads; carried on (or started again when it must); byte for byte the same
movie as a straight run where the picture is copied.

## What was wrong, and what changed
1. **Uploads cut off every 45 s on slow lines** (build 189). Python's socket timeout limits the whole request: a 32 MB
   piece needed 0.73 MB/s. Now 45 s + 1 s per 128 KiB.
2. **The read-back check read the whole movie** (r31). FFmpeg opens a fragmented MP4 by walking every fragment unless
   told to use its index (mfra); the check's second opener also lacked the network options. Interstellar: ~10 GB read,
   timed out. Now both openers use the index and the same options. 100 MB test movie: 1,305 reads / 46 MB before,
   14 reads / 0.9 MB now.
3. **Carrying on after Kodi closed mostly could not work** (build 190). On a slow line Drive is nearly always between
   two marks (past the saved one) when Kodi stops.
   - Copied picture: the converter makes the same bytes again, so it carries on from the mark and skips what Drive
     already has (`resume_store.fit`, `Sink.skip`). Proven byte for byte, including killed mid-upload.
   - The first run's FFmpeg moved the first packet after each fragment start by its rounding; a resumed run now moves it
     the same way when that is allowed (r31 `put`), so the bytes match (one tick of audio duration differed before).
   - Re-encoded picture (AV1): the movie is also written to files of 32 MB as it is made, each deleted once Drive has
     it (at most ~384 MB); every mark is saved at once with the files it needs, so a re-encode carries on from wherever
     Drive stopped. MARK_CAP raised from 96 MB to 256 MB (one 30 s unit of 4K).
4. **Interstellar's check waited behind Fall 2** (build 188): check-only jobs go first; the check is tried 3 times.

## Results (local, this computer)
- End-to-end: 200 checks, 0 failed (also run in CI host-tests from now on).
- Native host suite (run_host_tests.sh): 2,097 checks, 0 failed, including resume and "opens by its index".
- Python: every scripts/test_*.py and check_project.py.

## Still open
- Screen off / background networking: docs/PROMPT-ALWAYS-RUNNING.md (needs measuring on the phone).
- Not yet run on the phone: everything above is tested here with the real converter and a Drive stand-in.
- Kodi's own player opens a prepared movie with its own FFmpeg, which does not use the index either: playing a
  prepared movie from Drive in Kodi may start slowly. To check on the phone next.
