# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-14

Read first: AGENTS.md, docs/design/APPLE-UI-POLICY.md (for any UI work), docs/ISSUES.md ISSUE-226 to ISSUE-249,
docs/DECISIONS.md DEC-047 and DEC-048, ROADMAP.md. Rules: never merge, release or build an IPA without the owner's OK in
the current request; `python3 -B scripts/check_project.py` before every commit (run Python with `-B`, or __pycache__
fails it); new tests go in `.github/workflows/import-review.yml`; log every fix in docs/ISSUES.md; never offer AI Upscale in
quality messages; owner approves mockups before UI is coded. Native converter changes: read the airplay-remux host-tests
job as well as the framework build before pinning a KodiAirPlay release.

## State

- Owner's last IPA: **build-406** (7a50b2a): everything through ISSUE-258, AirPlay r56 pinned, Media Assistant kept
  (`cast.DIRECT_AIRPLAY = False`). Any new IPA needs the owner's OK in the current request.
- After build-406: ISSUE-257 rig label fix, ISSUE-259 (warm the video Kodi plays for Play on TV), ISSUE-261 (background work
  waits while the TV is short of the movie). Later speed-up, not started: a second conversion lane for 10-bit H.264 (native; a
  new KodiAirPlay release needs both the airplay-ios run and the airplay-remux host-tests job green, and the sha256 checked).
- All scripts in the import-review test list pass on the host.

## Open

1. ~~Done 2026-11-14 (rows and sheet fit; label changed).~~ Desktop Kodi rig check of the Download problems page after ISSUE-257 (episode-first titles, "Clear All for <show>" row
   in the sheet). How: `python3 -B scripts/kodi_rig.py setup` (once), `start`, `sync`, fake data (two failed debrid jobs
   of one show via `debrid_drive.save`), `open copy_problems`, `click 9201`, `shot NAME`.
2. Delete the Roku / Media Assistant route only after the owner confirms Rokus play well through AirPlay (ISSUE-252).
3. AI Upscale: the host tests pass; the phone proof is a 4K copy that finishes (ISSUE-241).

## Needs the owner's phone

Build-406: Play on TV opens Apple's list at once, tapping it again stops a start, the 10-bit question; Naruto season 2
copies; no "Waiting for the network" while online; Clear All for a show; a season without real 1080p stops looping.
Earlier: Smart Refresh and Check Every Video; uploads while a season is made ready; AI Upscale only on request; Repair skipping
dead/low versions and its live "Looking for 1080p…" ✕; show page ••• menu, Select toolbar and Better Version (old file to
Trash after the new one is saved); Don't Show Again; no "Window id does not exist"; DVD subtitles shown; AI Upscale hold menu
and Cancel All; waiting for Wi-Fi on mobile data; deleting while converting.

## 2026-11-14 (later): Play on TV work in progress (NOT built; the owner is testing build-398 first)

Build-398 (8781cdc) went to the owner. After it: ISSUE-250 (Download problems and the show card agree) is committed and
tested. The owner then asked for three things about Play on TV:

1. **Remove the "Play on TV" progress card everywhere and open Apple's AirPlay list at once** (owner screenshots: the card
   "Opening the episode · reading its index", and the system "iPhone Speaker / Bedroom / Kannon basement tv / Kannons bedroom
   roku tv / Living room" list).
   - WIP in this commit (ISSUE-251):
     - `cast.py`: `QUIET_PROGRESS=True`, so `FlowUI.show` shows nothing.
     - `lib.kodi_airplay_open()` is called right after `kodi_airplay_play`.
     - `build-airplay.sh`: when the stream is ready, the native player opens the list again only if no AirPlay output is
       already the audio route.
   - Problem cards (`ui.ask`) still show.
   - **To do:**
     - `scripts/test_play_on_tv_network.py` has 6 failures. They assert the card is shown. Update them to the new rule.
     - The Roku paths (cast.py ~542/571) used `ui.show('connecting')`; they are quiet now too. Check they still say
       something on failure.
     - The native change needs a KodiAirPlay release after r55 (r56): stage it, read the airplay-remux host-tests and the
       framework build, pin it, then one IPA. Only with the owner's OK.
     - Check on the phone that choosing a TV before the stream is ready sends the video there. iOS sets the AirPlay route
       for the app's audio session and the AVPlayer follows it.
2. **Why an Umbrella stream takes long to AirPlay** (owner log a176bcec, Dragon Ball Super: Beerus S1 E1, 10-bit H.264
   1080p MKV with subtitles):
   - Play on TV 17:55:49.4: source opened at +1.8 s, its index read at +4.6 s.
   - The first segment needed a software decode of the 10-bit picture, a VideoToolbox encode and the subtitles burnt in:
     9.7 s (162 % of real time). Audio for that segment took 8.8 s, because its own reader scanned the remote file
     (`scan_ms=8785`).
   - Stream ready +18 s, player ready +22.6 s, TV playing +28 s. Then every converted segment kept the TV waiting
     1-3 s (the converter is barely ahead).
   - Speed-ups to do, best first:
     - (a) Open the AirPlay list at once (item 1), so choosing the TV overlaps the preparation.
     - (b) Start reading the source and its index when a video starts playing in Kodi (prefetch), not when Play on TV is
       tapped. That saves about 6 s.
     - (c) Take audio for the first segment from the video reader's pass (or seek audio by its own index) instead of a
       separate full scan. That saves about 8 s.
     - (d) Make the first segment shorter (2 s), so the first conversion finishes sooner.
     - (e) In the source picker, prefer 8-bit H.264 / HEVC versions when Play on TV is likely. They need no conversion
       and start in a few seconds.
3. **Roku: drop Media Assistant and use AirPlay** (owner log 9c11baa7: "Roku took the link via media-assistant", 10 s from
   Play on TV; Roku/DVP-16.0 fetched the phone's master.m3u8).
   - Findings: there is no Roku API that starts its AirPlay receiver with a link. AirPlay to a Roku goes only through
     Apple's AirPlay (the system list, where "Kannons bedroom roku tv" already appears).
   - Removing Media Assistant therefore means:
     - every TV, Roku included, goes through the system list (item 1);
     - delete the ECP / Media Assistant route (`cast.roku_play`, `assistant_url`, `roku_copy*`, the Roku branches in
       cast.py) and its settings;
     - keep the problem cards.
   - Both paths are served by the phone (the same HLS server), so the phone must stay on either way.
   - Media Assistant played the phone's HLS directly. AirPlay goes through Apple's player (no HDR passthrough
     difference for SDR files).
   - Ask the owner before deleting the Roku code if anything still depends on it.
   - **Owner (2026-11-14): keep Media Assistant until AirPlay is confirmed on the Rokus.** `cast.DIRECT_AIRPLAY` is
     False; nothing is deleted. ISSUE-252 update.

