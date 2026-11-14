# Investigation: one source of truth for the Library (owner, 2026-11-14)

Owner (screenshots IMG_0067/0069/0070, log 8d661d6e, build 424): "major bug … why the following screens are not showing
the same information": Download problems shows one problem, Library status says "84 of 87 ready", Library › TV Shows says
Naruto Shippuuden has 28 episodes and no season 2, although season 2 was downloading. "The system [should use] the same
information everywhere; it shouldn't be pulling different numbers from different places."

Evidence class: owner's device screenshots and kodi.log; code reading. Nothing below is verified on the phone yet.

## What each screen reads today

| Screen | Where its numbers come from | Refreshed by |
|---|---|---|
| Library › TV Shows / Movies, the show page, Select, Free Up Space | `drive-library.json` (`drivelibrary.listing`, slots `tv:`, `tv:<folder>`, `movie:`), through `library_manager.model` + `library_files.episode_rows` | the service's `library_lists` loop (`drivelibrary.refresh_stale`), which needs the Google Drive add-on's `clouddrive` module |
| Library status ("84 of 87 ready", Working / Up next / Kept) | the preparation queue's own Drive scan, saved in its state (`state['library']`, `prepare_downloads.library_view`), via `library_scan.remote_files` | the preparation worker's scan (`Queue.scan`), with the Drive client the service made at start |
| Download problems | `debrid-drive.json` failed jobs (`debrid_drive.problems`) + preparation problems (`prep_problems`), minus `ignored-problems.json` and Clear | read on open |
| Show card chips, show page "need you" | `library_files` over the TV listing + prep jobs + debrid jobs (no ignore list) | on open |
| Activity pill, Notifications, Library status lanes | `work_state` (debrid + prep + runtime) | every second |

So there are **two separate Drive listings** of the same `Kodi Downloads` folder (TV Shows reads one, Library status the other)
and **four places that decide what counts as a problem** (Download problems, the show card, the show page, Library status'
Kept list), each with its own rules.

## Why the three screens disagreed in log 8d661d6e

1. **TV Shows stuck at 28 episodes, no season 2 (the main bug).** From 07:32:39 a repository update had replaced the app's
   patched Google Drive add-on (`plugin.googledrive 1.6.13 … hid the app's patched 1.6.8`, `clouddrive.common 1.5.20 …
   moved aside`). Every `library_lists` refresh then failed, 207 times in 45 minutes: `ModuleNotFoundError: No module named
   'clouddrive.common.remote'` (service.py `library_lists` → `drivelibrary.refresh_stale` → `listing` → `client`). The TV
   Shows page kept showing the last good `drive-library.json` (season 1, 28 episodes). Season 2 episodes 33–53 were copied
   to Drive in that time ("made ready while it copies" 07:34–08:02) but never listed there. The preparation scan kept
   working (its Drive client was made before the add-on moved), so Library status counted them: 87 videos.
   ISSUE-270 (after build 424; in build 430) makes every `clouddrive` import use the app's own copy, so the lists refresh
   again. But nothing on the page told the owner that its list was stale, and nothing fell back to the other listing.
2. **"84 of 87 ready" vs "28 episodes".** Library status counts every video in Kodi Downloads (movies and every show), from
   its own scan; TV Shows counts one show's episodes, from the other listing. Even when both listings are fresh, the two
   pages count different things with different words.
3. **Download problems "1" vs Library status "2 Kept" vs the show page "0".** Download problems lists failed copies and
   preparation problems that are not owner-kept (ISSUE-226 P4); Library status lists every kept video under "Kept as it
   is" (including "the prepared copy did not pass its checks", Rick and Morty S1 E5, which Download problems leaves out as
   repack-failed); the show page counts episodes with a Repair. 94 failed copy jobs exist (212 jobs: 118 done, 94 failed);
   most are superseded by later copies of the same episode, refused for quality and replaced, or waiting for the quality
   choice, and are correctly not shown, but each page filters them differently.
4. **"S1 E6 · Unnamed download".** A failed copy job with no title, name or file name (`debrid_drive.problem_title` falls
   back to "Unnamed download"); its show is known from `show_tmdb` but not used for the title.

## Proposal: one Library index, every screen reads it

A service-owned `library-index.json`, rebuilt whenever its inputs change (and at most every few seconds), is the only
place that turns raw state into what the screens show:

- **One Drive listing.** The preparation scan's listing (`library_scan.remote_files`, already exhaustive, with metadata
  eight at a time) also feeds the TV Shows / Movies lists, so there is one listing, refreshed by one loop. `drive-library.json`
  becomes a cache written from it (or is retired); a listing that cannot refresh says "Last checked … · can't reach Google
  Drive" on every page instead of silently showing old data.
- **One entry per video**, movies and episodes alike: show (TMDb id when known), season, episode, title, Drive id, size,
  quality, and **one state** with its reason: `copying` (from debrid jobs, before it is on Drive), `getting ready`
  (made ready while copying), `converting`, `waiting` (up next, with its place), `ready`, `kept` (and why), `problem` (and
  why, and whether the owner hid it). Episodes still copying appear in their show with that state, so a season being
  downloaded shows its episodes and grows as they land (owner item 3).
- **One set of counting rules** (`library_index.counts(scope)`), used by Library status (whole library), TV Shows and the
  show card (one show), Download problems (problems, minus hidden), the show page's third number, the activity pill and
  Notifications. "Problem", "kept", "ready" and "working" are defined once, so the numbers always add up across pages.
- **Titles** come from the same place for every page (TMDb episode title, else the show and S/E, never "Unnamed download").

Pages keep their approved designs; only their data source changes. The work_state model (live lanes, speeds) stays as the
live layer on top for progress, reading the same entries.

### Steps (each one its own commit, tests first)

1. `library_index.py`: build entries from the preparation listing + prep jobs + debrid jobs + upscale + ignore list; pure, host
   tested against the owner's states (log 8d661d6e: season 2 copying and landing, 94 failed jobs, kept videos).
2. Service writes it after every scan, copy step, preparation step and Clear / Don't Show Again; TV Shows / Movies, the show
   page and Select read it (library_manager.model).
3. Library status, Download problems, the show card and the show page count with `library_index.counts`.
4. Stale-data line on each page when Drive cannot be listed; retire the second listing.
5. Desktop Kodi rig render of each page with the same fake library; numbers must match across pages.

Open question for the owner: should Library status show only the TV and movie totals that match Library › TV Shows /
Movies ("Naruto Shippuuden · 49 of 53 ready"), or keep the whole-library "84 of 87"? Both will come from the same index.
