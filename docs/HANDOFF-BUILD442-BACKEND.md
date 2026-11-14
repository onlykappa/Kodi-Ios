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
