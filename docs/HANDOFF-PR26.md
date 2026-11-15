# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-14

Read first: AGENTS.md, docs/design/APPLE-UI-POLICY.md (for any UI work), docs/ISSUES.md ISSUE-226 to ISSUE-249,
docs/DECISIONS.md DEC-047 and DEC-048, ROADMAP.md. Rules: never merge, release or build an IPA without the owner's OK in
the current request; `python3 -B scripts/check_project.py` before every commit (run Python with `-B`, or __pycache__
fails it); new tests go in `.github/workflows/import-review.yml`; log every fix in docs/ISSUES.md; never offer AI Upscale in
quality messages; owner approves mockups before UI is coded. Native converter changes: read the airplay-remux host-tests
job as well as the framework build before pinning a KodiAirPlay release.

## State (2026-11-14, end of session; the next agent takes over from here)

- **Owner's last IPA: build-424** (14ed931). Everything after it is committed and pushed on this branch and **NOT built**:
  ISSUE-270 to ISSUE-275 (see docs/ISSUES.md). The owner asked for an IPA with these ("push out the ipa"), so build it as soon
  as the full test list and check_project pass: `import-review.yml` workflow_dispatch on `claude/preparation-repair`; the
  release is `build-<run number>`; send the owner the .ipa link.
- Before building: run every import-review test (`for t in $(grep -oE "python3 -B scripts/test_[A-Za-z0-9_]+\.py"
  .github/workflows/import-review.yml | sed 's/python3 -B //' | sort -u); do python3 -B $t; done`); the last full run was before
  ISSUE-273-275, whose own suites pass (test_copy_status, test_netwatch, test_pinned_addons, test_work_state,
  test_quality_choice, test_season_quality, test_deck_picker, test_debrid_drive).

## Open (do these, in order)

1. **Build the IPA** (above) with ISSUE-268 to ISSUE-275.
2. **Wi-Fi <-> cellular (owner: "ensure seamless downloads work at all times", "a quicker and smoother recovery")**:
   - Built-in fix not yet on the phone: ISSUE-271 (`netwatch` 2 s link watcher; a copy run ends at the next piece on a
     switch and restarts after 1 s; `driveupload.LinkMemory` per-link piece size and speed; diagnostics count only fresh
     lanes) and ISSUE-270 (`pinned_addons.use_clouddrive` everywhere clouddrive is loaded).
   - Ask the owner for one log: start a season copy on Wi-Fi, turn Wi-Fi off for ~3 min, back on, then share the log.
     Check: "connection changed to cellular while copying: carrying on at once" within seconds of the switch, lane count
     changes (2 on cellular), no 20 s piece timeouts after the switch, pieces start at the remembered size, and back on
     Wi-Fi the lanes go up within seconds (logs 4e5fb2dd / 18a4f9c7 / 8de561f4 show the old 3-7 min delays).
   - Known limit: the one native piece in flight at the switch cannot be cancelled from Python (46-68 s in the logs).
     If the owner wants that shorter, the native copier (KodiAirPlay copy_piece) needs a cancel; framework release rules
     apply (airplay-ios + airplay-remux host-tests green, sha256 checked, then pin).
   - Log 3848afa9 07:53-07:59: three "made ready while it copies" lanes (704x480 HEVC) crawled at 0.03-0.1 MB/s on Wi-Fi
     that did ~24 MB/s a minute earlier, and sat at 92-94 %. Cause not proven (likely three converters reading AllDebrid
     at once). Look in the next log; consider at most one made-ready lane at a time if it repeats.
3. **Code the approved Library status redesign (DEC-051, docs/design/unified-status-mockups.html, boards A round 2 and B).**
   All mockups are approved, including DEC-049 (already coded) and DEC-051. Kodi skin XML, portrait units (2.687/pt):
   - Board A: replace the "Downloading to Google Drive" cards and the Working section of IOSLibraryStatus.xml
     (resources/lib/library_page.py `_lanes`/`_work`/`_pool`, filled by library_status.py and library_rows/work_state) with
     one grouped list of slim rows (~118 units tall). Each row has a 34 pt ring with its percentage, the title (episode
     first, e.g. "S2 E48 · Naruto Shippuden"), one status line, and a small speed line.
     - The status line is short enough for one line ("Downloading · 7.2 MB/s · 1 min", "Getting ready · 3.1 MB/s · 3 min",
       "Converting · 1.4× · 22 min", "AI Upscale · needs a charger" in orange).
     - Kinds: copies (work_state copy cards, smooth glide already in code), getting ready while copying (mode 'ready'),
       conversions (conv/repack), AI Upscale (upscale_queue).
     - Up next becomes a grouped list with numbered circles.
   - Rings in Kodi: no arc drawing. Use pre-rendered ring textures, one PNG per 5 % step (portrait.py has texture
     generators: `ring`), chosen by a window property (the ring's step), tinted per kind. The speed line can reuse
     transfer_history.render at a small size, or a set of tiny textures.
   - Board B: in resources/lib/library_page.py `item_sheet`/`speed_card`, add the large ring beside the speed number (same
     texture approach, larger size). The graph already exists; ISSUE-273 gives every copy lane its own graph.
   - Keep everything updating every 1-2 s (the page loop is library_status.py `loop`).
   - Verify in the desktop Kodi rig (`python3 -B scripts/kodi_rig.py setup/start/sync`, fake debrid lanes as in
     docs/ISSUES.md ISSUE-257/273), with the longest real titles. Nothing may be cut off (DEC-050). Then build.
4. **Already in code, needs the phone**: one notice per season request (ISSUE-268); the quality question (DEC-049, boards
   A-D; board D rig render still pending); pinned add-ons restored ("Add-ons put back" then restart, ISSUE-267/270);
   "Downloads stopped" watchdog (ISSUE-269); pseudo/Anime4K treated as upscales (ISSUE-272); smooth copy cards, "Getting it
   ready for Kodi and AirPlay", a graph per copy lane (ISSUE-273); one release per season (ISSUE-274); preparation waits
   while copies run, "Starts when the downloads finish" (ISSUE-275).
5. Update the PR #26 description (it stops at ISSUE-261 / build-411) with ISSUE-262 to ISSUE-275 and builds 415/421/424.

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

