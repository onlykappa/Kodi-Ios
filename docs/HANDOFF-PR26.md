# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-13

Read AGENTS.md, ROADMAP.md, docs/ISSUES.md (ISSUE-226 to ISSUE-236) first. No IPA, merge or release without the owner's
explicit OK in the current request. `python3 -B scripts/check_project.py` before every commit; new tests go in
`.github/workflows/import-review.yml`. The converter host tests are the **airplay-remux** workflow (job `host-tests`):
read it as well as the framework build before pinning any KodiAirPlay release (ISSUE-229 was missed that way).

## State

- Last IPA the owner has: **build-384** (commit db35cf0, 2026-11-14): everything up to ISSUE-237. **ISSUE-238 to ISSUE-242
  are committed after it and not built** (one IPA when the owner asks).
- AirPlay framework pinned: **r55** (DVD subtitles kept in the MP4 and counted as ready).
- The owner will re-download Naruto Shippuuden season 1 at 1080p once the next IPA has the quality fallback below.

## Committed after build-376 (needs one IPA, then an owner log)

1. **ISSUE-233** Deleting mid-conversion: both delete paths call `prepare_downloads.forget`; a trashed or missing source
   (`SourceGone`) leaves the queue quietly; a forget stops the running conversion.
2. **ISSUE-234** Library status Refresh: while videos wait, the Drive listing runs at once (`scan(listing_only=True)`, once
   per request); the inspection waits for an idle queue.
3. **ISSUE-235** Settings › AI Upscale row says what is on ("1 show · 4K", "New downloads · 4K", "Off", "Unavailable").
4. **ISSUE-236** Season quality:
   - The copy path (made ready while copying, F1, `debrid_ready.copy`, and plain copies through `check_quality`) probes
     the AllDebrid file and refuses one lower than the chosen quality before anything reaches Drive. The job ends
     `failed` + `low_quality`.
   - The owner's rule: **take a lower quality only when it is the absolute only one available.**
     - `deck_picker.auto_choose` (strict quality) takes a real match first.
     - Otherwise it takes the best that exists as a `fallback`: nearest quality first, versions already found lower
       (`lower_names`, from `low_quality` jobs, set in `episode_watch_runtime`) last.
     - A fallback pick is not refused at copy (`elementum_cloud` passes no `quality`), and the owner gets one notice
       ("No 1080p version … the best available was downloaded").
   - **The owner said: do NOT offer AI Upscale in that notice** (not tuned or tested).
   - Tests: `scripts/test_season_quality.py`.

## Not coded yet (owner asked for these; do them in this PR or a new one)

- **Check the season re-download end to end with the owner's log.** Early Naruto Shippuden exists mostly in SD; the
  expected result is real 1080p where any exists (e.g. "Naruto Shippuuden - 002 [1080p] 10bit"), otherwise one fallback
  per episode with one notice each.
  - Watch for a loop: a `low_quality` copy, then a re-search, then the same pack as fallback. The fallback is accepted,
    so the loop should end; verify it does.
  - Verify the re-search actually happens for a refused episode. `episode_watch` re-downloads missing episodes; confirm it
    picks a `low_quality`-failed episode up again.
- **AI Upscale encode failure:** "video conversion: encode: Generic error in an external library" (Phony S1 E2,
  1920x1080 → 4K, log 1ae21097). Not investigated.
- **"EXCEPTION: Window id does not exist"** after a page closes (logs 1ae21097 14:57, 15:14). A page thread touches a
  closed window. Not traced.
- **`native.verify` (C-level) failures still retry as full conversions** (ISSUE-230 only covered the probe and checksum).
  A read problem during verify is now treated as network (ISSUE-232), but a real verify failure repeats.
- **Prepared-file uploads are slow** (~1.3 MB/s total while reads run at 7–10 MB/s, log 47e2276a). Pieces fall back to
  1 MB after each dropped connection. Consider parallel piece uploads or a softer reset.
- **AI Upscale copies do not resume** from a mark after a stop or a network drop. They start again.
- **Unverified on the phone:**
  - DVD subtitle shown when playing a prepared Naruto episode.
  - AI Upscale hold menu and Cancel All (ISSUE-228).
  - Preparation waiting for Wi-Fi on mobile data.
  - The focus fix for "Control 9110".
  - Repair interrupting an upscale (ISSUE-227).

## Owner preferences seen in this session

- One IPA at the end of a batch; no builds per commit. Merge only when the owner says so.
- 480p is unacceptable unless nothing else exists. The owner wants plain status words, no stuck percentages, and
  instant reactions to taps (cancel, delete, refresh).

## Update 2026-11-14 (this session)

- **Built:** build-384 (db35cf0) = build-376 + ISSUE-233–237: the season quality rule (a real 1080p wins; lower only when
  nothing else exists, one plain notice, no AI Upscale offer) and Repair using the quality chosen for the show.
- **ISSUE-237:** owner log f63389f1 (build 376) showed Repair taking an uploader's upscale ("_2.25x_1920x1080_alq-10") at
  "any quality". Repair now uses the show's chosen quality; in a fallback, versions that only claim their quality come
  after every real one. PR check run 381 had failed on two season-source tests still expecting "never lower"; updated.
- **Coded after build-384 (not built):** ISSUE-238 (a failed `native.verify` stops after one conversion unless network),
  ISSUE-239 (TMDb Helper "Window id does not exist" after a page closes, build patch), ISSUE-240 (a dropped upload piece
  halves the piece size instead of 1 MB), ISSUE-241 (AI Upscale encoder stop: retry once on screen, wait for Kodi to be
  open in the background; cause not proven, log 1ae21097 not available), ISSUE-242 (AI Upscale copies resume from a mark).
- **Waiting for the owner's log of the Naruto season 1 re-download on build-384.** Check: every episode real 1080p where
  one exists, else one fallback with one notice; no repeat loop on a refused version; refused episodes searched again;
  the DVD subtitle still shows.
- **Phone checks still open:** AI Upscale hold menu and Cancel All (ISSUE-228); waiting for Wi-Fi on mobile data
  (ISSUE-230); Repair stopping an upscale (ISSUE-227); Library status Refresh (ISSUE-234); deleting while converting
  (ISSUE-233); DVD subtitle shown in Kodi; the "Control 9110" focus fix.

## Update 2026-11-14, later

- Owner approved DEC-047 (docs/design/library-show-mockups.html: board A without Ready and A2, B, C, D) and it is coded:
  ISSUE-243. Owner logs 3df2f247, 3a30b6ef, 6984524f (build 384) gave ISSUE-244 (Repair leaves out dead and low versions; a
  refused quality is never copied; Don't Show Again for Download problems; the sheet text and the red square) and ISSUE-245
  (AI Upscale makes copies only of videos the owner asked for on a show's page, or every new download with Upscale new
  downloads on).
- Next IPA dispatched from 8aa612d (everything through ISSUE-245). Desktop Kodi rig render of the DEC-047 pages: pending.
- Known, not fixed: "Control 32503 in window 13002 has been asked to focus, but it can't" (the version picker, harmless).
