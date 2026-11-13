# Roadmap: a faster whole pipeline (AllDebrid → Drive → ready to play)

Status: **plan only, no code in this PR.** Written for the next agent. Owner request (2026-11-13): "can we not convert
a lot at once, like how we uploaded? we need the entire process to be faster, not just uploading."

Read first: `ROADMAP.md`, `docs/PROGRESS.md`, `docs/ISSUES.md`, `docs/DECISIONS.md`, and the session protocol in
`AGENTS.md`. Branch per piece of work, PR to `main`, **no IPA build, merge or release without the owner's approval in
the current request.** Phone behaviour needs the owner's iPhone logs; host tests and rigs never prove it.

## Where this stands

PR #23 (branch `claude/trusting-euler-kgug98`, not merged when this was written) already made the *copy* step fast:
AirPlay r53 streams each AllDebrid piece straight into the Drive upload (ISSUE-201), lane learning (ISSUE-200, 206), and
network trouble never fails a copy (ISSUE-198). Build 356 measured 3 lanes at 13–17 MB/s on a 22 MB/s uplink
(owner's Speedtest: 254 down / 180 up Mbps, ping 36 ms).

The *preparation* step that follows (Library status "Up next · Convert") has not been touched, and it is now the slow part.

## Evidence (owner log 68d43660, build 356, 08:38–09:12)

| Fact | Where in the log |
|---|---|
| Naruto Shippuuden S1 E5: h264 1080p 8-bit, `copy=True`, reason `index_after_media` | `preparation: ... faster opening needed (index_after_media)` 08:51 |
| Inception: hevc 3840x1598 10-bit, `copy=True`, reason `not_mp4` (it is an MKV) | 09:06 |
| So both are **re-packages** (`job['repack']`): the picture is copied, only the container / index moves. Not re-encodes. | `fast_open.py:39-51` |
| A re-package reads the whole file back from Drive at 3–8 MB/s (`Drive reads: 176 MB in 60 s (2.93 MB/s)` … `6.80 MB/s`) while the copies run at ~15 MB/s beside it | `preparation: Drive reads:` every minute |
| Inception card: 17 %, 5.8 MB/s, "about 31 min to go"; 25 of 57 ready, 25 up next, all `Convert · 0.2–4.3 GB` | owner screenshot |
| Re-packages run **one at a time** (the queue shows 15 eligible, 1 working) | `scheduler` event: `eligible_jobs 15` |
| A 13-minute gap before the first preparation: queue empty until the library check found the new episodes | 08:38 → 08:51 |
| The season picker did its job (nothing needing a real re-encode was picked) but it does not look at the container or index position, so a release that plays fine still needs a re-package | `season_sheet.py`, `season_sources.py` |

Every byte of a re-packaged file makes two extra trips through the phone: AllDebrid → phone → Drive (the copy), then
Drive → phone (the re-package's read) → Drive (its write). That is the cost every option below attacks.

## The options (item ids are `F1`–`F6`; the reliability roadmap in PR #23 already uses R1–R17)

Recommended order: **F5 and F2 first** (cheap, visible at once), **F3** next, **F1** as the big rebuild, **F4** and **F6**
last. Each is its own branch and PR. Log each in `docs/ISSUES.md` (cause, fix, retest, regression protection) and add its
tests to `.github/workflows/import-review.yml`.

### F1. Make the file AirPlay-ready while it copies (the big win)

*Idea.* The copy already moves every byte of the file through the phone. Re-package it on the way, so it lands on Drive
as an AirPlay-ready MP4 and the second round trip (and the whole "Up next · Convert" wait) disappears for everything
that only needs a re-package. Real conversions (10-bit H.264, AV1, …) still run their own pass.

*Touches.* The native framework: `migration/airplay-ios/build-airplay.sh` embeds the Obj-C (`kodi_http_copy`, the
`KodiCopyLeg` / `KodiCopyDelegate` streaming added in r53) and the converter used by `native.convert_to`; pinned by
`migration/airplay-ios/source-lock.json` (stage with a zero sha256, CI `airplay-ios.yml` builds and publishes, then pin the
verified zip: see ISSUE-201 for the exact steps). Python: `debrid_drive.py` (copy lanes, `copy_to`), `drive_prepare.py`
(`Sink`), `prepare_downloads.py` / `prepare_cloud.py` (when a job is marked done / needs no preparation).

*Open design question: do a spike first.* A faststart MP4 needs its index (moov) before the media, which needs every
sample size, which a single streaming pass does not have. That is exactly `index_after_media`. Options to evaluate:
(a) fragmented MP4 (check Kodi, the AirPlay bridge and the TV accept it); (b) spool the re-packaged file to the phone's disk
(about 48 GB free in the build-356 snapshot) and upload it after, still skipping the Drive re-download; (c) write the movie
data to Drive first and patch the index in front with a second small upload if Drive's resumable upload allows it (it does
not allow rewriting earlier bytes, so probably not). Report which one works before building the rest.

*Acceptance.* A file that is a compatible-picture MKV, or an MP4 with the index at the end, arrives on Drive already
`ready()` (`appProperties` set, checksum recorded) with no preparation job created; the log shows no `Drive reads:` for it.
MKV subtitle / audio-language rules still apply (`audio kept` / `subtitles kept` log line). A cancel, a network drop and an
app restart mid-copy still resume from what Drive confirmed. Needs the owner's phone log.

*Risk.* Highest effort and the highest chance of a regression in the copy path that just got fast. Keep the current
copy-then-prepare path as the fallback and behind a setting until the owner's log proves it.

### F2. Run several re-packages at once

*Idea.* A re-package is limited by the connection, not the phone's CPU, so run 2–3 together (like the copy lanes: lane
learning in `debrid_drive.lane_plan`). Real re-encodes stay one at a time (the phone's video encoder and heat are the limit,
and `AirPlay`/playback already slow work: `slowdown.py`).

*Touches.* The preparation queue worker in `prepare_downloads.py` (it runs one job: `self.busy`, the single `current` card)
and `service.py`'s preparation loop; the status model that shows one "working" card (`work_state._conversion`) and the
bell/pill/Library status counts (`work_state.build`, `notifications.py`'s cards); `preparation_runtime` heartbeats
(`stats`, `phase`) are single-job today. Likely needs `current` to become a list of lane cards like `debrid['lanes']`.

*Rules.* Only jobs with `copy_video` true and the same simple shape (`repack`) share lanes; one re-encode at a time, and not
beside a re-package if the phone is warm or on battery. Respect the owner pause, playback / AirPlay holds, and `BUSY_LANES`
style caps so copies and re-packages together do not starve each other (the build-356 copies took ~15 MB/s).

*Acceptance.* With 5 re-package jobs queued the log shows 2–3 `preparation:` jobs reading at once, each card shows its own
percentage, Library status says "N working", and total read MB/s rises above the single-lane 3–6 MB/s. A conversion mid-way
through still resumes from its mark (`resume_store`).

### F3. Read one file over several connections

*Idea.* Drive serves each connection at only a few MB/s, so a single file read 3–4 chunks at a time could be 2–3× faster.
This speeds up every conversion and re-package read, including the real re-encodes F2 leaves single.

*Touches.* `drive_stream.py` (the local range proxy the converter reads: `BLOCK = 8 MB`, a `KEEP` cache of blocks, one
upstream request per block, `Range: bytes=...`). Check what read-ahead it already does and whether blocks are fetched in
parallel; if not, add a small prefetch pool for sequential reads (and keep the seek behaviour for the MP4 index probe and
`verify`). The HTTP/2 or per-connection limits of Drive's API may cap this; measure first.

*Acceptance.* The once-a-minute `Drive reads: ... MB/s` line rises for the same file with the copies running; no extra
`Drive file check` / 403 / rate-limit errors; memory stays bounded (a fixed block count).

### F4. Share the connection between copies and preparation by priority

*Idea.* When copies and a preparation both want the line, give the share to what the owner will watch next (next episode in
a started season, anything in Continue Watching) instead of splitting evenly. This is the "priority scheduler" left open in
PR #23's description (playback > next-to-watch preparation > copies > checks).

*Touches.* The copy lane cap (`BUSY_LANES` in `debrid_drive.py`, set by `converting()`), the preparation `next` ordering
(`work_state._next`, `prepare_downloads` queue order, the owner's "Edit order"), and `slowdown.py`.

*Acceptance.* With a next-to-watch episode in the preparation queue and copies running, its read rate is visibly higher than
the copies'; with nothing next-to-watch the copies keep the full line. Needs the `network` snapshot line (`copy_mb_s`,
`prep_read_mb_s`, from `diagnostics.network`).

### F5. Make the season picker prefer files that need no work

*Idea.* Rank releases that are already AirPlay-ready (MP4, index at the front, compatible picture) above equal-quality
releases that need a re-package (MKV, index at the end), and above those that need a real re-encode. Those episodes then land
on Drive playable and F1 / F2 never need to run for them.

*Touches.* `season_sources.py` / `season_sheet.py` (the quality sheet and exact-quality episode pick), `source_guard.py`,
`source_match.py`, and the title / file-name signals in `drivelibrary.parse`. The picker cannot know the index position from
a name, so use cheap signals: the extension (`.mp4` / `.m4v` vs `.mkv`), codec and bit depth when the source gives them
(`h264` 8-bit first, `hevc` next, 10-bit h264 / AV1 last). Never rank below the owner's chosen quality (the picker's rule:
"Episodes without your quality are not downloaded in a lower one").

*Acceptance.* For a season with both an MP4 and an MKV of the same quality the MP4 is queued; the sheet's wording does not
change; existing picker tests still pass (`test_season_sources`, `test_season_sheet`). Add a test per ranking rule.

### F6. Re-package only when it is needed

*Idea.* A compatible-picture file whose only issue is the index at the end (or a container AirPlay does not need yet) plays
on the phone as it is; its only cost is a slower start on the TV. Skip it until the owner actually sends it to the TV
("Play on TV"), or do it only for the next episodes to watch, so a 57-episode season does not queue 25 re-packages up front.

*Touches.* `prepare_downloads.py` (the scan decides `repack`; Library status "Up next" and `request(..., 'keep' | 'retry')`),
the owner's "keep as it is" path (`Kept` count on Library status), `cast.py` (Play on TV) for an on-demand prepare.

*Open question for the owner before coding:* is a slower start on the TV acceptable for episodes not yet prepared, or must
everything be ready before it is watched? This changes how aggressive F6 can be.

## Also worth a ticket (found in the same log)

- **The 13-minute gap before preparation starts.** A copy that lands on Drive should ask for its own preparation check
  straight away (`service.py` `done()` → `request_check`), not wait for the next library scan. Check why the 08:38–08:51
  window had `eligible_jobs 0` while 15 episodes were already on Drive.
- **Progress shown while queued.** Library status says "Convert · 4.3 GB" for a re-package. Say "Re-package" so the owner can
  see these are not slow re-encodes (wording only; no new colours, tokens or helpers: `docs/design/APPLE-UI-POLICY.md`).

## Measuring success (ask the owner for one log)

The `network` object in the once-a-minute snapshot (ISSUE-198, `diagnostics.network`) already reports the link type, copy
lanes and MB/s, and preparation read MB/s. Add the number of parallel preparation lanes and a "ready minutes per GB" line when
F2 lands. Target to confirm in a device log: a 30-episode season that only needs re-packaging finishes preparation within
minutes of its last copy, instead of one 3–6 MB/s file after another.

## Process reminders for whoever picks this up

- `python3 -B scripts/check_project.py` must pass before every commit; run the affected tests, add new ones to
  `.github/workflows/import-review.yml`.
- UI wording or layout changes need `docs/design/APPLE-UI-POLICY.md` and a mockup first; the owner approves mockups
  before they are coded.
- Native (F1, maybe F3): the Obj-C lives in `build-airplay.sh`; CI builds it, so a compile error only shows in the
  `airplay-ios` run. Fix by reading the job log, never by guessing.
- Private backups, keys, tokens, Drive ids, logs and media stay out of Git.
