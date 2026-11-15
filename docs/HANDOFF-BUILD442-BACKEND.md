# Build 442 backend contracts

Python data only. No layout changes, merge or IPA. Device retesting remains pending.

## Shared library / Queue / Notifications (ISSUE-291)

Read `work_state.current(profile)` for the current backend model (also persisted by the service).
`library_index` is the authoritative record; workers only contribute measurements.

- `library_counts`: e.g. `{"total":4,"ready":1,"working":2,"copying":1,"converting":1,"problems":1,
  "kept":0,"hidden":0,"cancelled":0}`. Count videos, not worker lanes.
- `library_videos`: the identical records Library status uses, e.g. `{"key":"tv:rickandmorty:3:1",
  "state":"copying","title":"Rick and Morty","season":3,"episode":1,...}`.
- `jobs`: measured live work; `next` and `drive_next`: indexed work without live measurements / waiting its turn.
  All carry `key`, `library_state`, canonical `title` (e.g. `S3 E1 · Rick and Morty`) and stable worker action `id`.
- `library_index.entry_title(entry)` and `entry_line(entry)` give the common title and state words.
- `KodiIOS.LibraryIndex` on Window(Home) remains the visible-change counter, e.g. `"17"`.

The existing Notifications layout has one preparation slot and a fixed number of copy slots. The full set is exposed
in the model; the UI agent should draw all required rows from it. Missing telemetry means queued, never invented speed.


## Upload rates / ring / graphs (ISSUE-292)

`work_state.current(profile)` and the persisted work-state share these fields. Rate units are bytes/s;
`speed_mb_s` uses 1,048,576 bytes/MB, matching the existing app/log convention.

- Each upload/copy in `jobs`: `lane_id` (stable video/worker identity), `key`, `title`, `rate`, `speed_mb_s` (e.g. `4.0`),
  `speed_history` (up to 60 `[unix_second, bytes_per_second]` pairs, e.g. `[[1000,4194304],[1001,4194304]]`),
  `eta_s` (e.g. `24.0`, zero when unknown/paused), `progress_pct` (e.g. `25.0`).
- `confirmed_bytes` is Drive's actual position; `sent`/`pct` may retain the existing bounded display glide. Use
  `confirmed_bytes / total` for a strictly acknowledged ring. `piece_bytes=33554432`, `piece_seconds=8.0`,
  `measured_at=1000.0` explain a native measurement. `slot` is the physical lane; identity must use `lane_id`.
- Ready-on-copy jobs expose `ready_copy=true`, `out_bytes` and `upload_total` (zero until known); their percentage is
  film progress, while speed comes from confirmed output uploads. ETA is unknown until remaining output is known.
- `upload`: `rate`, `speed_mb_s`, `eta_s`, `lane_count`, `speed_history`, `lanes` (per-lane field dictionaries).
  Example: two lanes at 2 and 3 MB/s give `speed_mb_s=5.0`, `lane_count=2`.
- Measurements are held between confirmed pieces for graph continuity, then expire after 60 seconds; pauses sample zero.
  Scheduler gaps are left as gaps. No graph sample advances confirmed bytes. The publisher runs every second.

Use per-job points in the slim status row and large copy graph; use `upload.speed_history` for a combined graph.
Existing backend graph binding now prefers these points; no layout or ring drawing was changed.


## Subtitle match evidence (ISSUE-293)

`subtitle_match.assess(track, video)` accepts a track's `filename`, `language`, `data` or `cues=[(start,end)]`, and a video's
`duration`, `season`, `episode`, preferred `language`, optional `absolute_episode`, optional measured `speech` intervals.
A trusted `offset_s` plus `offset_confidence` can also be supplied. It never invents speech evidence.

- `track_menu.subtitle_rows(..., video)` and `result_rows(...)` keep `match_reason`, `match_score`, `match_rejected`,
  `match_timing_checked`, `match_offset_s`, `match_cue_count`, `match_offset_confidence` in each row model.
  Example: `match_reason="Matches this episode", match_score=98, match_rejected=false, match_timing_checked=true`.
  Rejection example: `match_reason="Timing does not fit this video", match_score=0, match_rejected=true`.
- Existing Subtitles ListItems bind the first five `match_*` fields as strings (`"false"`, `"98"`, empty offset when
  unknown). The UI agent can show `ListItem.Property(match_reason)` without changing the selection logic.
- Window(Home) `KodiIOS.SubtitleMatches` is JSON of stream `index` and every `match_*` field, refreshed per opened video.
  Example: `[{"index":1,"match_reason":"Timing not checked","match_score":88,"match_rejected":false,
  "match_timing_checked":false,"match_cue_count":0,"match_offset_s":null,"match_offset_confidence":0.0}]`.

Embedded DVD tracks without cues remain explicitly unchecked for timing/speech. Their language/name evidence is still
scored. Python has no exposed DVD cue or speech API in the current native framework; do not label these as verified.


Issue numbering note: the target branch added its own UI ISSUE-290 while this work was underway. The backend entries
are ISSUE-291 onward. The first two commit subjects retain their original pre-collision references (queue 290→291,
upload metrics 291→292); no pushed history was rewritten.


## Notification and season data (ISSUE-294)

- **C1:** `notice_help.folded(items)` returns copies with `count` (notice occurrences, e.g. `2`), `lines` (`2` or `3`,
  text length over 110 characters selects `3`), `ids` (e.g. `["new","old"]`), `unread` (any member unread), and
  `source_count` (the original store count, which may describe episodes). Exact kind/title/text only; no store mutation.
  Newest time/action stays on the row. The UI agent can replace its list projection with this helper.
- **N2:** `notice_help.detail_model(item, records=(), profile=profile)["timeline"]` loads retained producer steps.
  `notice_help.explain(item)["timeline"]` also accepts an explicit item timeline. Up to three entries, e.g.
  `[{"at":1001,"time":"10:29","kind":"copying","colour_kind":"blue","text":"3 episodes started copying"},
  {"at":1120,"time":"10:31","kind":"problem","colour_kind":"orange","text":"AllDebrid stopped answering"},
  {"at":1420,"time":"10:36","kind":"retry","colour_kind":"orange","text":"Tries again in 5 min"}]`.
  Clock strings use the phone's local timezone; the numeric timestamps above are illustrative. Old notices without timed
  evidence get no invented steps. The UI agent should pass profile to load the sidecar; no detail layout was changed.
- **Q2:** `season_check.Survey.model()` has `total`, `completed`, `pending`, `unknown`, `checking_qualities`, `qualities`.
  Example quality: `{"key":"1080p","label":"1080p","found":4,"total":10,"checked":6,"pending":4,
  "unknown":0,"state":"checking"}`. Total is episodes still needed for this Build Season request.
  State becomes `done` or `incomplete`; failed scans stay unknown. Exact 720p counts do not count a 480p fallback as 720p.
- `season_sheet.checking_props` / the existing sheet controller publish string properties:
  `check.total="10"`, `check.completed="6"`, `check.pending="4"`, `check.unknown="0"`,
  `check.checking_qualities="4k,1080p,720p"` (empty when no scans remain), and `check.quality.N.{key,label,found,total,
  checked,pending,unknown,state,text}` for N=1 (4K), 2 (1080p), 3 (720p). Example:
  `check.quality.2.found="4"`, `.total="10"`, `.text="4 of 10 episodes found"`, `.state="checking"`.
  `check.sub="6 of 10 episodes checked"`; no sample-episode wording. Counts are retained after the check completes.


## Permanent copy failures (ISSUE-295)

- `debrid_drive.problems(state)` rows expose `terminal=true`, `retryable=false`, `source="debrid"` or `"phone"`, and
  `error`/`reason`, e.g. `"The refreshed download is a different file. Choose another source."`.
- Known bad receipts also retain a private `invalid_drive_id`; only that file is marked as a problem. A separate valid
  copy remains ready. Do not use the private ID as a UI label.
- Durable failed jobs have `status="failed"`, `terminal=true`, `terminal_reason=<clear reason>`, `retry_at=0`.
  `library_index` projects the same video as `state="problem"` and the same `reason`; Library status/Download problems
  should show that reason. Use `retryable` when offering a retry; terminal failures need corrective action first.
- `notice_help.explain` / `detail_model` keep a permanent failure's actual words and omit the retry fix.
- Legacy phone state keeps `failures[path]={fp,reason,time}` in private runtime state. This is internal, never a UI label.
  The existing explicit `debrid_drive.retry_failed` route handles phone failures via a per-file retry request, not an
  AllDebrid request. Changed files become eligible automatically; original phone files remain intact on failure.

## Validation and integration boundary

All added tests are registered in import-review.yml. Host checks are separate from device verification. No IPA, native
build, merge, skin/layout/mockup change or notices.py edit was performed.

The target branch advanced during the task. A read-only conflict check found only docs/ISSUES.md's concurrent appended
entries conflict; workflow and notification controller changes otherwise combine. Keep this PR draft and resolve that
text-only integration conflict with the UI work when the owner authorizes integration. No merge was performed here.
