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

11. **"Remove From Continue Watching" does nothing.**
    - Find the action (the watch add-on's continue row, and the long-press or sheet entry).
    - Make it remove the item from Kodi's resume points and every Continue Watching row, then refresh the row.
    - Add a test.
12. **Build Season "Checking which qualities exist…" sheet: redesign it.**
    - The owner says it always says "Looking at episodes 1, 6 and 10", which reads as wrong, and the sheet looks ugly.
    - The empty placeholders "4K · … 1080p · … 720p · …" and the large empty gap also look bad.
    - Make a new page: mockups first, sent to the owner for approval before any code (policy §7).
    - Say what it is doing in plain words, without naming sample episodes, and show the qualities as they are found.

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

## Progress (2026-11-14, this session)
- **Done:** item 2 is ISSUE-282 (`window` NameError in `drive_uploads`, test_undefined_names); item 1 is ISSUE-281 (one stream
  cache per run, the real link if the link does not answer within 5 s, test_stream_fallback). Both are pushed on this branch.
  The owner was asked for kodi.old.log of the crash.
- **Key finding (owner log b9a3a059, build 442):** "Drive: downloads stopped (NameError)" six seconds after every start.
  On build 442 nothing in `drive_uploads` past that point ran:
  - no AllDebrid copies or Drive uploads;
  - no preparation;
  - **the library index (`library_index.publish`) never published.**

  That is why the owner saw Rick and Morty season 3 "downloading" but not in Library status, the Queue or Notifications
  ("not linked to our one synced library"). ISSUE-282 fixes the cause. After the next build, check with a log that the
  index publishes (its change counter property moves) and that the Queue, Notifications, Library status and Download
  problems all read `library_index`.
- Items 3 to 12 above are still to do (item 3's RuntimeError may also come from the dead loop; re-check after ISSUE-282).

## New owner requests (2026-11-14, after build 442)
13. **Row titles open a grid.** Tapping a row's title on Home / Movies / TV ("Trending Movies ›", "Trakt Trending Movies ›",
    "Continue Watching ›", and every other row) opens a grid view of that row's items, with the artwork only. Make it like
    the Downloaded Movies / TV Shows grid. Apply it to all rows.
    - Reuse the existing downloaded grid layout (portrait.py / pages.py). The row's `path` is the grid's content.
    - Check in the desktop Kodi rig.
14. **Library status still shows AllDebrid copies the old way.** DEC-051 (approved, unified-status-mockups.html boards A
    round 2 and B) was never coded on PR #26. Code it: slim rows with a 34 pt ring, the title with the episode first, one
    status line and a small speed line, for every kind of job, plus the copy sheet like the conversion sheet. See
    docs/HANDOFF-PR26.md "Open" item 3 for files and approach.
15. **One brain everywhere.** The Queue and the notification centre must read the same library index (`library_index`)
    as Library status, TV Shows and Download problems: counts, titles and states agree everywhere. Add a test that compares
    them for one fixture (e.g. Rick and Morty S3 copying).

## Handover, 2026-11-14 (end of the second session)

Done on `claude/build442-feedback` (each has its ISSUE entry and test):
- ISSUE-281 stream fallback · 282 NameError · 283 controls 3 s · 284 Remove From Continue Watching
- ISSUE-285 retry log names the error (cause still waits for a log) · 286 remove videos not on Drive · 288 AI Upscale from
  library_index · 289 no Trakt/Elementum start notices · 290 notification centre C1 · 291 row title opens a grid ·
  292 Library status slim rows (DEC-051 board A) with speed line and time left on every row.

Owner decisions this session: N2 (notification detail with timeline) and Q2 (Build Season chips) approved; C1 approved
and coded; the activity pill and its sheet are to be removed entirely ("I use Library status or the notification tray").

Open:
1. **Activity pill removal (ISSUE-287 reserved).** A helper agent worked on it in a local worktree that is not pushed;
   it is lost if the container ended. Redo it if branch `claude/remove-activity-pill` is not on the remote: remove
   activity.py, activity_page.py, activity_skin.py and its service loop, keep the ring_00..20 textures (now used by
   Notifications and Library status) and the fonts `p_pill`/`p_pill_s` (used by Notifications).
2. **Backend from the owner's ChatGPT agent** (branch `codex/build442-backend`, PR into this branch): one brain for
   Queue/Notifications (item 15), real upload speed and graph data (item 8), subtitle filter (item 6), the data for N2
   (timeline) and Q2 (per-quality counts), RuntimeError follow-up. Review it in the rig; never merge without the owner.
3. **UI to code (Claude):** N2 sheet and Q2 sheet skins on that data; DEC-051 board B (copy sheet like the conversion
   sheet); item 9 smooth scrolling on every page (compare Home/Movies/TV grouplist settings with the other pages).
4. Ask the owner for kodi.old.log (ISSUE-281 crash) and a log after a copy retry (ISSUE-285).
5. Update PR #28's description; list phone tests; no IPA without the owner's OK.

Rig notes: the profile is `~/.cache/kodi-rig/home/.kodi/userdata`; `SendClick` does not reach buttons inside the hub
grouplist, use `DISPLAY=:5 xdotool mousemove X Y click 1`; Kodi conditions group with `![…]`, never `!(…)`.

## Handover, 2026-11-14 (end of the third session) — read this first

**State.**
- `claude/build442-feedback` (PR #28) is pushed and the full import-review list passes.
- Last owner build: **build-470** (from 1bc5d1e). It carries everything below plus ISSUE-300/301.
- PR #30 (ChatGPT backend) is merged into this branch (ISSUE-293 to 297, renumbered).

**Done this session:**
- ISSUE-287: activity pill removed.
- ISSUE-298: review fixes. A sign-in waits instead of failing copies; the HTTP 4xx rule is Drive-only; subtitles are never switched off; the 3 s timer applies on first open.
- ISSUE-299: Continue Watching works while Drive is signed out, and logs what it follows.
- ISSUE-281 continued: a paused stream keeps its source.
- ISSUE-300: Umbrella opens through the stream cache again; desktop rig 29 s → 7.3 s.
- ISSUE-301: Refresh logs why each video is re-read.

**Unfinished agent work, on its own branches (WIP, untested; review before using):**
- `claude/wip-scroll-and-logs` (91b67f5): item 9 smooth scrolling (`portrait.py` hook, `scripts/test_smooth_scroll.py`). It also holds the remote_media/service changes already applied on PR #28; take only the scrolling part.
- `claude/wip-n2-q2-copy-sheets` (8389839): N2 notification detail, Q2 Build Season sheet and the copy sheet (`notice_page.py`, `season_sheet.py`, `season_check.py`, `library_rows.py`, `pages.py`, `notifications.py`, `scripts/test_build442_sheets.py`). Unfinished, with no rig check.

### Next, in this order (the owner's priority)

**1. Finish PR #29 (Favourites list import and the anticipated-episodes bell), test it, then build an IPA for the owner.**
- Branch `claude/modest-hopper-8z5ar8`, based on old `main`.
- Review findings (third session, a throwaway merge into PR #28's head):
  - It merges with only three conflicts. In `default.py` PAGES, keep both lists but drop `activity_page`, which was removed in ISSUE-287. `scripts/check_project.py`'s mockup list keeps both. `docs/DECISIONS.md` keeps both.
  - **Renumber its decision**: it uses DEC-047, which this branch already uses for the show page. Use the next free DEC number and update references.
  - After that, every import-review test passes. Its own tests are test_favourites_import, test_favourites_flow and test_anticipated_bell.
- To do before an IPA:
  1. Merge it into `claude/build442-feedback` (or rebase it onto it), with the fixes above. Give each feature an ISSUE entry.
  2. Render boards G–J in the desktop rig next to `docs/design/favourites-import-bell-mockups.html`, following `docs/FAVOURITES-IMPORT-BELL-RIG.md`. Nothing has been seen in Kodi yet. Check: the bell on a TMDb Helper seasons page (that `Container(50).ListItem.Property(tvshow.tmdb_id)` is set, else `bell_lookup_failed`); no bell on an ended show; the "New episodes" sheet; the Download sheet has two rows; Library › Favourites, the empty state, the chips, the Import/Sort toolbar, `#rank`/`3×` badges; Import → Paste/Text file → progress → report; the sort sheet; open a show, and resume or start a movie. No cut-off text (DEC-050).
  3. Recommended fixes from the review, mostly where it differs from the approved mockups. Do them, or ask the owner when it is a choice:
     - **The bell sheet.** The mockup (G3) has real switches and a Done button. The code uses On/Off rows on the choice sheet with Cancel. Recommend building G3 as drawn: the owner approved it.
     - **Import.** No "Name this list…" step and no search-by-hand for Not found. The report is a choice sheet, not the page in the mockup. Ask the owner whether the sheet is acceptable; otherwise build the approved page.
     - **J3** (a show's in-progress episode marked Continue) was not built. Check whether the show page already shows it; if not, add it.
     - **The grid** now shows up to 90 favourites (was 36). Check that scrolling stays smooth.
  4. Run the whole test list, then build an IPA (`import-review.yml` workflow_dispatch on this branch; the release is `build-<run>`). Check the download, then send the link with a phone test list. The owner asked for this IPA in the current request.

**2. Then the remaining gaps:**
- **Item 9: smooth scrolling on every page.** Take it from `claude/wip-scroll-and-logs`. Compare the Home/Movies/TV grouplist settings with the other pages, and check in the rig.
- **N2 notification detail (timeline), Q2 Build Season chips, DEC-051 board B copy sheet.** Owner-approved, in `docs/design/build442-mockups.html` and `unified-status-mockups.html`. Start from `claude/wip-n2-q2-copy-sheets`. The data is from PR #30 (`docs/HANDOFF-BUILD442-BACKEND.md`). The owner wants PR #29 before N2.
- **ISSUE-301: Refresh speed.** Read the owner's next log for the new `preparation: checking <title> (<reason>)` lines. If unchanged videos are still re-read, find out why `settled()` misses them. Reading several videos at once needs its own design: the native prober is shared with the converter.
- **ISSUE-300 on the phone:** confirm `open timing … via umbrella` for a resume is about 5–8 s.
- **ISSUE-285:** the cause of the copy `RuntimeError` retries still waits for a log taken after a copy retries.
- **Reviewer's low items:**
  - Remove the orphaned settings strings #32001–#32010 in `strings.po`.
  - The video controls' Continue Watching panel path has no stamp (`player_osd.py`, `CONTINUE`).
  - `scripts/rig_smoke.py` still references the pill.

**Rules:**
- AGENTS.md and docs/design/APPLE-UI-POLICY.md apply.
- Every fix gets an ISSUE entry and a test listed in import-review.yml.
- Run check_project and every test before each commit; commit and push as you go.
- Check UI in the rig, and keep screenshots out of Git.
- Never merge a PR without the owner's OK.
- Leave model IDs out of commits and PRs.
- Use one agent at a time: the owner asked for no parallel sub-agents, to save usage.

## Handover, 2026-11-15 (end of the fourth session) — read this first

**State.** `claude/build442-feedback` (PR #28) is pushed; the full import-review list passes (127 tests). Latest owner
build: **build-482** (5f930a5). Nothing merged. Work since the third handover: ISSUE-302/306/309/315 (Umbrella opening),
ISSUE-304/305/307/308/311/312/314 (PR #29 merged: Favourites import, bell sheet G3, import report page from
Notifications, hand-added favourites first, J3), ISSUE-310 (a movie copy shows as running on every screen), ISSUE-316
(smooth scrolling, on its own branch, see below).

**Owner report on build-482: Umbrella still takes up to 30 s to open. No log yet for build 482: ask for it first.**
What the earlier logs established (47ee1590 build 477, bdbdac02 build 479):
- The `Kodi iOS open timing: N s via umbrella (handoff X s, open Y s)` line splits the time. Hand-off = tap to address
  handed to Kodi (Umbrella resolving + AllDebrid unlock + our cache's 3 opening blocks, `stream opening: … wait_ms`).
  Open = Kodi's demuxer open (`Creating Demuxer` → `Open - probe limits`).
- Cache route good case: 12.9-16.6 s (hand-off 5-7 s, of which ~4 s our 9 MB opening blocks; open 7.7-9.3 s).
  Direct route (cache not ready in 5 s, or the race of ISSUE-315): 28-42 s, Kodi's open 20-24 s over one connection.
- Kodi's open reads far past the start of these MKVs (Crunchyroll WEB releases carry ~20 MB of attached fonts):
  ISSUE-300 rig: plain MKV 2.2 s, with fonts 29 s direct.
- Ideas not yet tried: admit the cache on block 0 + last instead of 3 complete blocks; raise KODI_AHEAD / start the
  extra blocks with the opening ones; check `served=` and whether Kodi reads sequentially through attachments (if so,
  an ffmpeg option to skip attachment reads, or a larger first range); measure Umbrella's own resolve time between
  "playing with umbrella" and the first `stream opening` (5-12 s seen); a slow AllDebrid unlock (log bdbdac02 18:00:05
  → 18:00:17).
- Rig: `scripts/kodi_rig.py` + a local throttled HTTP server reproduces the open (ISSUE-300 method). Umbrella itself is
  not in the repo or IPA (installed on first run), so test `remote_media.for_kodi` end to end, as ISSUE-300 did.

**Smooth scrolling (ISSUE-316)** is on branch `claude/wip-smooth-scroll` (a2999ef): a Kodi patch change (group lists skip
children far off screen; rig A/B Favourites 68→83 fps, Notifications 70→88, Home unchanged) and source-lock `build_tag`
r33. It needs the native build `kodi-ios-portrait.yml` (hours, publishes r33) → check digests → set
`executable_release` to r33 → IPA. **Ask the owner before starting it** (it publishes a release). Pushing the patch to
the PR branch triggers that build, so merge it only once approved.

**Remaining gaps after Umbrella:**
- N2 notification detail (timeline), Q2 Build Season chips, DEC-051 board B copy sheet: approved mockups in
  docs/design/build442-mockups.html and unified-status-mockups.html; data from PR #30 (docs/HANDOFF-BUILD442-BACKEND.md);
  unfinished start on branch `claude/wip-n2-q2-copy-sheets`.
- ISSUE-301 Refresh speed: needs the owner's next log (`preparation: checking <title> (<reason>)` lines).
- ISSUE-285 copy RuntimeError: needs a log taken after a copy retries.
- Phone checks pending: the long-press "Add to favourites" on a Home poster; the 90-item Favourites grid scrolling;
  J3 Continue line (rig cannot list episodes offline).
- Offered, not yet asked for: a clear message when a Wi-Fi intercepts HTTPS (log a296afa2: certificate hostname
  mismatch for googleapis.com, Umbrella sat at "Getting the link from AllDebrid…").

**Rig notes:** profile `~/.cache/kodi-rig/home/.kodi/userdata`; real taps `DISPLAY=:5 xdotool mousemove X Y click 1`;
`System.FPS` via `kodi_rig.py rpc XBMC.GetInfoLabels '{"labels":["System.FPS"]}'` while dragging with xdotool; the rig's
Kodi source (`~/.cache/kodi-rig/kodi-src`) currently has the ISSUE-316 change applied (rebuild: `make -j kodi` in
kodi-build, ~15 s). Kodi conditions use `![…]`, never `!(…)`. Screenshots never go into Git.

## Progress, 2026-11-15 (fifth session): Umbrella opening (ISSUE-317)

- Owner logs cf038697 / 6fb90ab2 (build 482). The cache route admitted all 3 blocks in 4.3 s, then Kodi's reads from the
  cache were cut three times (`Transferred a partial file(18)`), giving 31.3 s. Fixed in code: the opening budget covers
  only the route-deciding blocks, a failed block is fetched again before a read is cut, blocks Kodi waits on get request
  places first, and every read and block is logged for 90 s (`Kodi iOS cache read` / `cache block`). See ISSUE-317.
- Rig set up like the phone: probe-limit hunk applied to the rig's Kodi source; null ALSA device in the rig HOME
  (`.asoundrc`), without which Kodi's start waits 5 s for audio; TMDb Helper disabled (the rig crashed loading its Home
  widgets). Test MKVs had their font data turned into EBML Void elements, so FFmpeg seeks past fonts as the phone's
  patched FFmpeg does. 30 fonts at 0.7 MB/s and 0.4 s per request: direct 16.9 s, cache 8.5 s, and 24 MB before
  admission 8.5 s (it only moves the wait).
- Next: the owner's log from this IPA after an Umbrella play. If it is still slow, read the `cache read` lines.
