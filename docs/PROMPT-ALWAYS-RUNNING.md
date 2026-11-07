# Prompt: Kodi keeps working whenever it is open (screen off, locked, in the background)

Paste everything below the line into a new session on this repository.

---

Goal: as long as Kodi iOS is not closed (swiped away in the app switcher), everything it is doing must carry on at
close to on-screen speed, exactly like other iPhone apps that download, upload or stream: Elementum downloads,
AllDebrid → Google Drive copies, Drive uploads, the AirPlay preparation (conversion + upload), and AirPlay playback to
the TV. Locking the phone, letting the screen turn off, or switching to another app must not stop or stall any of
them. Work on branch `claude/trusting-euler-kgug98` (repo onlykappa/Kodi-Ios), follow docs/HANDOFF-R28.md (build
table, `[skip ci]` commits, builds started by hand, framework releases pinned in migration/airplay-ios/source-lock.json),
and read docs/RESUME-DESIGN.md first.

## What the logs already show (build 187, the night of 6–7 Nov 2026)
- From 21:44 (screen still on) to 06:00, 402 Drive upload PUTs of 32 MB failed with "The write operation timed out"
  after 45 s (driveupload.STALL), about one a minute, from the conversion's uploader thread and a second thread.
  So the socket sent nothing for 45 s at a time. Interstellar (copied 4K HEVC, 2 h 49 min) took ~7 h to convert and
  upload. Kodi went to the background at 21:48 ("Kodi iOS background: silent audio running for queued work").
- Interstellar's last step, the read-back check of the 50 GB file on Drive (kodi_airplay_probe, 120 s limit), timed
  out. Build 188 retries the check three times and puts check-only jobs first; that's a fix for the symptom only.
- AirPlay: the TV reads the prepared movie from Kodi's own HTTP server inside KodiAirPlay. Until build 188 the
  keep-awake reasons (service.py `why()`) did not include AirPlay, so with no other work iOS suspended Kodi after the
  screen locked and the stream died. Build 188 adds AirPlay as a reason; confirm that's enough.
- The owner reports downloads stop when the screen turns off. Check which ones (Elementum, AllDebrid copy, Drive
  upload) with evidence; don't assume.

## How it works today (verify in the code)
- Keep-awake: KodiAirPlay plays mixable silent audio (`kodi_background_keep`, background.py watch / service.py why);
  app_state.Pace caps the converter at BACKGROUND_SHARE 0.7 of a core off screen (iOS ends background apps over ~80%
  of a core for a minute). VideoToolbox decoding is refused off screen, so re-encodes fall back to CPU (r26).
- Uploads: Python urllib PUTs of 32 MB pieces (drive_prepare.MAIN_CHUNK, AHEAD 4 queued) with a 45 s socket timeout;
  r30 ends pieces at resume marks. AllDebrid copies use driveupload.upload_stream. Elementum is a Go engine on
  127.0.0.1:65220.

## Do this
1. Measure before changing anything. Add one diagnostics event per change of: on screen / background / locked
   (UIApplication state, protectedDataAvailable), Low Power Mode, thermal state, and the network path (NWPathMonitor:
   Wi-Fi/cellular, isExpensive, isConstrained). Add a per-piece upload record: bytes, seconds, and the longest gap with no
   bytes sent, so a stall can be matched to a screen or network change. Ship it in a build, have the owner run one
   night with the screen off, and read the log.
2. Fix what the measurement shows. Options to judge with evidence, not guesses:
   - Uploads through URLSession instead of Python sockets: a background-configured URLSession upload task keeps
     sending while the app is suspended. It needs a file, so spool each piece to a small temp file and delete it once
     Drive confirms it. Keep "nothing big kept on the phone": a few pieces of 8–32 MB at most. Keep the 256 KiB / mark
     rules from r30.
   - Smaller pieces (8 MB) and a timeout that counts time with no progress, not one whole-request timeout, so one
     slow stretch doesn't throw away 32 MB.
   - Audio session: category playback, mixWithOthers, re-activated after interruptions (calls, Siri, other apps' audio).
     Log every interruption and route change.
   - AirPlay: AVPlayer external playback while locked (allowsExternalPlayback,
     usesExternalPlaybackWhileExternalScreenIsActive, audio session playback), and the in-app server's sockets kept
     alive in the background.
   - Elementum: check whether its listener and peer sockets survive the screen locking (network, not just CPU).
   - The conversion off screen: check whether the 0.7 CPU cap or the CPU decode is the limit; consider letting it run
     at full speed while charging (BGProcessingTask / Low Power Mode off).
3. Tests: unit tests for every new rule (Python scripts/test_*.py, native host tests in
   migration/airplay-ios/remux/tests), all of scripts/test_*.py and scripts/check_project.py green. Any framework change
   goes through airplay-remux CI → pin in source-lock.json → airplay-ios.yml publish_verified_candidate → import-review
   build → check the IPA (build.json commit, framework sha256).
4. Report to the owner in plain words: what stopped each kind of work with the screen off (with the log lines), what
   changed, what was tested, and what still needs a night-long test on the phone.

Don't: tell the owner to keep the screen on, add settings they have to find, or use private APIs or anything App
Store review forbids (the app is sideloaded, but stay within public APIs).
