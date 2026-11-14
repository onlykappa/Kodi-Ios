# Build 442 backend contracts

Python data only. No layout changes, merge or IPA. Device retesting remains pending.

## Shared library / Queue / Notifications (ISSUE-290)

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


## Upload rates / ring / graphs (ISSUE-291)

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
