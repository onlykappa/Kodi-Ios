# Handoff: build 442 owner feedback (new PR)

The owner's checklist answers for build 442 (2026-11-14), plus log 6cf2a4c5. That log starts at 10:29, after the crash, so the crash itself is not in it. Each item gets an ISSUE entry in docs/ISSUES.md and a test in import-review.yml. Read the rules in AGENTS.md and docs/design/APPLE-UI-POLICY.md before any UI work. Get the owner's OK before any IPA. Never merge.

## Bugs (fix first)
1. **Umbrella stream never opened: stuck at "Opening the video · 0 of 12 MB", then the app crashed when Resume was pressed** (ISSUE-280 regression).
   - The stream cache route (`remote_media.for_kodi`, swapped in by `umbrella_recovery.remember`) handed Kodi a 127.0.0.1 address that served nothing.
   - Check the cache's block fetch for AllDebrid links: headers, Range, TLS context, and `native_reader` in the service's `remote_media.start`.
   - Check the Resume path: Kodi reopens the loopback URL.
   - Add a safety net: if the cache has served no bytes within N seconds, fall back to the real link. Also consider `KODI_PLAYBACK=False` until this is proven.
   - Ask the owner for the log of the crashed session (Kodi keeps it as kodi.old.log).
2. **`Kodi iOS Drive: downloads stopped (NameError); starting again in 30/60/120 s`** repeats from startup (log 6cf2a4c5, 10:29:55 onward).
   - Find the name; it was likely introduced on PR #27. The service's Drive download loop logs only the type, so log the message too.
3. **`AllDebrid: Rick and Morty: RuntimeError; trying it again after the others`** (10:31:39 to 10:31:44). Find out which RuntimeError it is.
4. **Delete of the "no name" (Unnamed download) item does nothing.** Delete through the library index (`library_index.intend_for`) must also cover entries that come only from AllDebrid copies or problems: remove the job or problem, not only Drive ids.
5. **AI Upscale is not linked to the brain.**
   - The AI Upscale page does not show Naruto season 2.
   - It must list every 480p / 720p / 1080p video from `library_index` (all shows, all seasons, movies), not from its own scan.
6. **Subtitles that don't match.** Naruto (DVD picture subtitles) showed subtitles that matched neither the timing nor the speech.
   - Add a filter that rejects a subtitle track whose timing or text does not fit the video: for example, cue times beyond the duration, a large offset against the audio, or a language or episode mismatch.
   - Prefer the matching track, and say so on the Subtitles menu.

## Changes the owner asked for
7. **Video controls hide after 3 s**, not 5 (`player_osd.DEFAULT_TIMEOUT`). The one-time default must also move existing 5 s installs to 3 (new flag). Keep: they stay when paused.
8. **Upload speed is the same as before, and the graphs don't show or are "chunky to update".** Investigate the Transfers and Library status speed graphs: their update rate and the data they draw. Then look at real speed: per-lane MB/s from the log's `Drive copy native: 32.0 MB piece in N s` lines.
9. **Notification detail sheets look poor.** Redesign them, mockups first (policy §7), and wait for the owner's approval.
10. **Scrolling is poor on almost every screen** ("the flick just sucks"). Only Home, Movies and TV Shows feel smooth.
    - Find what those three use: the Kodi patch's portrait scrolling, list `scrolltime` / tween, grouplist vs list.
    - Apply the same to every other page: Library status, the show page, Download problems, Notifications, Settings, the Queue, AI Upscale, Select, Transfers.
    - The rule is the same flick physics everywhere.

## Still untested by the owner (ask again later)
Play on TV of an Umbrella episode; Roku AirPlay of Naruto S1 E1 (r57); "AllDebrid is fetching it" notice; next episodes copy while one fetches; Wi-Fi ↔ cellular copies; Repair / Repair All; "Choose a version"; Pick Better Versions.

## Confirmed working (build 442)
- Opening card steps.
- Tap to hide the controls.
- Controls stay when paused.
- Download problems and Library status match.
- TV Shows, the show page and Library status numbers match.
- AI Upscale never starts by itself.
- Don't Show Again.
- The show page ••• menu and Select.
