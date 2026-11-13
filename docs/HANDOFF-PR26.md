# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-13

Read AGENTS.md, ROADMAP.md, docs/ISSUES.md (ISSUE-226 to ISSUE-236) first. No IPA, merge or release without the owner's
explicit OK in the current request. `python3 -B scripts/check_project.py` before every commit; new tests go in
`.github/workflows/import-review.yml`. The converter host tests are the **airplay-remux** workflow (job `host-tests`):
read it as well as the framework build before pinning any KodiAirPlay release (ISSUE-229 was missed that way).

## State

- Last IPA the owner has: **build-376** (commit 7ea9a5f). Everything after it is committed but **not built**.
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
