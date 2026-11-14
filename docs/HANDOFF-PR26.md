# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-14

Read first: AGENTS.md, docs/design/APPLE-UI-POLICY.md (for any UI work), docs/ISSUES.md ISSUE-226 to ISSUE-249,
docs/DECISIONS.md DEC-047 and DEC-048, ROADMAP.md. Rules: never merge, release or build an IPA without the owner's OK in
the current request; `python3 -B scripts/check_project.py` before every commit (run Python with `-B`, or __pycache__
fails it); new tests go in `.github/workflows/import-review.yml`; log every fix in docs/ISSUES.md; never offer AI Upscale in
quality messages; owner approves mockups before UI is coded. Native converter changes: read the airplay-remux host-tests
job as well as the framework build before pinning a KodiAirPlay release.

## State

- Owner's last IPA: **build-393** (8aa612d): everything through ISSUE-245.
- Committed and pushed after build-393, **not built**: ISSUE-246 (Refresh inspection waits while downloads are made ready;
  upload pieces grow on a steady line), ISSUE-247 / DEC-048 (smart Refresh; hold Refresh = Check Every Video), ISSUE-248
  (preparation carries on after a rename; version picker opens on Back), ISSUE-249 (rig render fixes).
- The owner asked for these recommendations and then an IPA. **Next step: finish the open items below, then build the IPA
  (`import-review.yml` workflow_dispatch on this branch; the release is `build-<run number>`) and send the link.** The
  owner said "push the ipa", so building is approved for this batch.
- All 96+ scripts in the import-review test list pass on the host (one known environment-only error in
  test_build193_pages `test_landscape_airplay_sheet_unchanged`: `git show` in a shallow clone).

## Open (do these)

1. ~~Done 2026-11-14: rig shows both glyph tiles.~~ **Re-render the Download problems choice sheet in the desktop Kodi rig** after the `choice_sheet.glyph_path` fix
   (ISSUE-249): tiles must show the eye-slash and trash glyphs, no bare squares. How: `python3 -B scripts/kodi_rig.py start`,
   `sync`, write fake data with the script below, `open copy_problems`, `click 9201`, `shot NAME` (screenshots stay out of
   Git; they are in ~/.cache/kodi-rig/shots). The fake Library data script used this session was in the scratchpad
   (not in Git): it writes drive-library.json (`tv:` with one show, `tv:<id>` with episodes), drive-library-art.json
   (`tv:<title lower>:<year>` → tmdb_id, `season:<tmdb>:<n>` → titles/thumbs), a preparation state (prepare_downloads.save)
   and two failed debrid jobs (debrid_drive.save) into ~/.cache/kodi-rig/home/.kodi/userdata/addon_data/service.kodi.ios.bootstrap.
   A Trakt 401 dialog may cover the rig: `builtin "Dialog.Close(all,true)"`.
2. ~~Done 2026-11-14: no square highlight.~~ Re-render the show page's ••• capsule after its focus change (no square highlight).
3. Optional (owner dislikes "…"): Download problems row titles truncate ("Naruto Shippuuden · S…"); would need the
   row to wrap or shorten (approved page; small change, mention to the owner).
4. Build the IPA, send the link, update the PR #26 description (ISSUE-246 to ISSUE-249 are not in it yet).

## Needs the owner's phone

Smart Refresh and Check Every Video; uploads while a season is made ready; AI Upscale only on request; Repair skipping
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

