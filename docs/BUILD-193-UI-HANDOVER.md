# Build 193: approved pages, Phase 4 and Phase 5

Source implementation on `claude/trusting-euler-kgug98`, draft PR #16, base `main`.
No app build, IPA, release or merge. KodiAirPlay r33 and its pin are unchanged.
Phases 1–3 remain the completed work in ab5ce91 and ecfbecc.

## Phase 4 delivery

| Item | Source status | Implementation |
|---|---|---|
| 1 | Done | Library working card with poster, separate step, ring, percentage and sparkline; segmented summary and four count buttons; numbered Up next, Edit order, checked ready rows. |
| 2 | Done | Model-owned needs-you action, orange warning tile, slowed wording/grey progress, AllDebrid copy section and replacement explanation. |
| 3 | Done | Working movie sheet: grabber, Close, poster/metadata, three step bars, live graph, Average/Done/Started, explanation, Play and Pause/Resume. |
| 4 | Done | Transfers headline and one selectable chip per job (including jobs of the same kind); selected job's step, percentage, speed, graph, progress, metrics and queue; History link. |
| 5 | Done | Shared raster plot at displayed dimensions × device scale, 4× edge supersampling, rounded 2.5 pt stroke, fading fill, guides and now dot; axes, units, peak and times are Kodi labels. |
| 6 | Done | Notifications uses the shared compact working card with the model's exact status line, queue link and Earlier rows; long press and visible ellipsis open the same control menu. |
| 7 | Done | Idle plain bell; model percentage/tint ring and blue running count; grey when slowed; red only for needs-you, never unread messages; no spinning arc. |
| 8 | Done | Queue shares the model's order/estimate, current job percentage/bar, numbered rows, disabled grey end arrows, and faster-start explanation. |
| 9 | Done | History day selection, unfinished attempts first, plain reasons, one contextual retry per identifiable job, then finished rows with time and result. |
| 10 | Done | Ready sheet's three green steps, Kodi/AirPlay/Picture/Sound and subtitles rows, conditional needs-you action, Play and Play on TV. |

“Done” means source and host checks, **not visual or device approval**.

## Files changed

- Controllers: `migration/bundled-bootstrap/{library_status,notifications,transfers}.py`.
- Portrait generators/data/helpers under `migration/bundled-bootstrap/resources/lib/`:
  `library_page.py`, `library_rows.py`, `library_tools_page.py`, `library_tools.py`, `portrait.py`,
  `notifications_skin.py`, `status_ui.py`, `tool_windows.py`, `transfer_history.py`, `work_state.py`.
- Tests: the new `scripts/test_build193_pages.py` and the nine existing suites named under Validation.
- Docs: this report, `docs/HANDOFF-R28.md`, `docs/ISSUES.md`, `docs/plans/build-193-roadmap.md`.

## Model and controls

Live jobs, queue order, tint, speed, percentage, needs-you actions and wording come from `work_state`.
Library/Queue retain preparation metadata for posters, capability facts and actionable historical problems;
they no longer poll the download engine or reconstruct current copy status independently. History supplies
sampled points, peak/average, start time and bytes only. Samples for a different title are discarded.
Missing snapshots show Updating rather than idle. A sheet can follow a completed movie to its new Drive ID.

Two small model presentation helpers supply the Library sparkline caption and the shared remaining-time estimate.
The estimate uses the current preparation rate for queued source sizes and takes the maximum with parallel copy
ETAs. It is deliberately approximate, and disappears when the snapshot is stale, paused, waiting, or lacks a
measured rate/known size. No slowdown or worker scheduling rule changed.

Summary categories are disjoint: a ready movie queued for a faster start belongs to Up next, still says Ready now,
and retains Play/Play on TV. It appears only once in the summary. Summary totals include current downloads.

Existing helpers/tokens are reused: `label`, `image`, `surface`, `pill_button(primary/glass)`, `nav_button`,
`close_button`, `ring_00..ring_20`, `FONTS`, `SIDE`, `RADIUS`, the existing surfaces and status colours.
`status_ui.py` consolidates the existing borderless row/link button pattern, cards, bars and graph labels;
`notifications_skin.py` composes those controls. No new colour, font size, radius or capsule style was added.
The portrait fingerprint includes both helpers so existing installs regenerate the pages.
Landscape AirPlay sheet output remains unchanged; no 1080i layout was restyled.

## Validation

Run every `scripts/test_*.py` separately with `python3 -B`, except `test_drive_runtime.py` (requires account/runtime
arguments). Packaging unit tests need Python 3.11 via `KODI_IOS_PYTHON311`; a prebuilt interpreter was installed
in the execution environment for this test dependency. These are host tests, not an app/IPA build invocation.

The new `test_build193_pages.py` covers generated XML IDs, unique controls, both hit dimensions ≥118, text ≥30,
explicit widths and truncation, non-overlapping text boxes, shared card/step/graph structure, bell states,
requested plot pixel dimensions and partially transparent stroke edges, summary counts, same-kind job chips,
ready faster-start counts/actions, shared ETA rules, Queue end arrows, unfinished-first History and retry dispatch.
The unchanged landscape sheet function is compared with ecfbecc.

Old layout pins were updated in `test_library_status`, `test_library_tools`, `test_notices`, `test_transfers`,
`test_header_buttons`, `test_conversion_speed`, `test_prepare_downloads`, `test_check_beside` and `test_work_state`:
folder summaries become sections; filter buttons become summary counts; the spinning bell becomes determinate;
summary text/progress-control assertions follow model properties and step bars; History metrics share the result
line. Existing request, navigation, pause/cancel, playback, retry, queue-order and backend tests remain.

Validation caught and fixed standalone helper imports, malformed image aspect-ratio XML, a nonexistent 118-unit
capsule texture (reuse 124), a two-unit overlap in the reused Queue row, and double counting/dropping a queued
ready faster-start movie. These failures were retained in the work log and retested with the new regressions.
Final validation (2026-11-07): **80/80 test scripts passed**, with only `test_drive_runtime.py` excluded.
`check_project.py` and `check_ui_guidance.py` passed (zero issues/problems). The final focused page suite passes
all 14 tests; Library (48), Transfers (22), Queue/History (31) and model (20) retests also pass.
The full sweep was followed by focused retests for the final caption/tint and same-kind-chip changes.

## Evidence and iPhone review

- **Mockup:** `docs/design/library-status-mockups-r1.html` is the owner's approved reference. No new mockup screenshot
  is presented as app evidence.
- **Desktop Kodi rig:** a later desktop experiment was stopped at the owner's request. Its uncommitted layout
  changes are excluded; no rig capture is acceptance evidence. Visual verification is **PENDING** on the iPhone.
- **Device:** PENDING. The owner must check all nine boards, scrolling/taps, ring colours/percentage, long titles,
  graph clarity, movie-sheet transition to ready, and two-second agreement while converting, paused, signed out,
  retrying, playing a video, and using AirPlay. Confirm Play/Play on TV, Pause/Resume, Queue arrows and History retry.

Differences/limits to check against the mockup:

- Kodi uses the prescribed existing fonts/radii, PNG ring steps (5% increments), static textures and fixed safe-area
  canvas rather than the browser's SVG/CSS curves. Pixel-exact matching has not been established without a rig.
- Real metadata replaces example values. Missing language/channel/HDR details are not invented: the Sound and
  subtitles row falls back to See playback options, and quality includes only known fields. Existing old-layout
  faster-start jobs say Ready to play rather than promising a one-second open before optimization.
- The Library working caption uses model speed/ETA when running (the step is already above it), and the full model
  line when slowed/paused/waiting. Notifications and Transfers retain the full model line.
- Ellipsis controls provide the policy-required visible alternative to long press. Previous/More appears only
  beyond 40 Library rows, 10 Queue jobs or 12 History entries, keeping larger libraries/history accessible.
- Legacy History records have no stable job ID. Retry resolves only an unambiguous current preparation ID or
  failed AllDebrid hash/episode; unmatched or ambiguous records have no unsafe guessed retry action.


## Owner review follow-up (build 193, source only)

The owner chose device review instead of continuing the desktop rig. The rig processes were stopped;
its uncommitted layout experiments were set aside. This follow-up preserves the committed layout and
addresses the eight supplied behavior findings. No app/IPA build, converter change, release or merge.

| Review item | Root cause and fix | Regression in `test_build193_pages.ReviewFindings` |
|---|---|---|
| 1 | Transfer titles borrowed the kept Drive file's metadata/identity. Copy/upload/download joins now require a nonempty matching ID; synthetic transfer rows retain a separate model job key. Only conversion/re-pack joins may fall back to a title. The kept row and its sheet stay independent. | `test_1_transfer_titles_cannot_replace_or_bind_the_kept_drive_copy` |
| 2 | Movie-sheet Pause passed Elementum's `down` kind to the pause-file API. Down jobs now call the engine's pause/resume endpoint with the model's torrent ID. | `test_2_elementum_pause_and_resume_use_the_engine` |
| 3 | Every live sheet received Play, including incomplete transfers. Play is limited to conv/repack; downloads/copies have Pause/Resume and confirmed Cancel when their target ID/hash is known. Plain phone uploads keep Pause/Resume. | `test_3_transfer_sheets_have_pause_cancel_without_play` |
| 4 | Notification model cards dropped the control metadata. Conversion cards retain the running Drive ID; AllDebrid cards retain `source=debrid` and their hash, restoring both Cancel menu entries. | `test_4_notification_cards_keep_both_cancel_targets` |
| 5 | Live-action replacement discarded QUICKER. Re-encoding movies retain it as the third action beside Play and Pause/Resume. | `test_5_reencoding_keeps_quicker_as_the_third_sheet_button` |
| 6 | Recovery ran underneath a modal. Sheet recovery is returned to its parent; the sheet and page close before executing the action. A page's own recovery button closes the page first. | `test_6_recovery_dismisses_all_modals_before_running_its_action` |
| 7 | Polling re-rendered unchanged samples. Per-job plot caches reuse the previous file until point count or last sample time changes. Item, sparkline and Transfers caches have separate namespaces and job paths. | Both `test_7_*` tests (cache invalidation and repeated actual-controller refreshes) |
| 8 | Synthetic history reset start to each refresh's clock; failed re-packs offered an ineffective retry. Transfers now retain first-seen times per job, accepting earlier sampled starts. History hides retry when the matched job is both blocked and repack_failed, preserving REPACK_STOPS. | Both `test_8_*` tests (clock persistence and stopped faster-start recovery) |

Ten new regressions cover all eight findings. `test_transfers.py`'s graph-path assertion now checks the job-scoped
cache path rather than the old shared filename. No existing test was removed. Device behavior remains pending.

Final follow-up validation: **80/80 test scripts passed**, excluding only `test_drive_runtime.py` as requested.
`test_build193_pages.py` passes **24 tests** (14 existing plus ten review regressions). Both
`python3 -B scripts/check_project.py` and `python3 -B scripts/check_ui_guidance.py` pass with zero issues/problems.
