# Build 193 roadmap: one status model, the approved pages, work that never stops

Owner, 2026-11-07, after build 192: "Notification center isn't linked with Library status properly or it is just
SUPER SLOW … it still says paused as a video plays and it seems to be converting … if I click on it it says nothing
is moving … stuff should ALWAYS be moving even if an AirPlay movie is playing, just slower … it needs to work like a
AAA game, not a buggy prototype." The owner then approved nine mockups ("Awesome work").

- Branch: `claude/trusting-euler-kgug98`. Draft PR: **#16** (base `main`). Old PRs #3, #11, #12 and #13 are merged.
- Mockups (approved, evidence class: mockup): [docs/design/library-status-mockups-r1.html](../design/library-status-mockups-r1.html).
  The interactive canvas is at https://claude.ai/artifact/LxhcCEKeHMD7JW2Gh57YwV (the owner's link).
- Build process, `[skip ci]` commits and the hand-started builds are in [docs/HANDOFF-R28.md](../HANDOFF-R28.md).
  **Do not build or publish an IPA until the owner says so.** Python-only work needs no converter (KodiAirPlay)
  release; r33 stays pinned.
- UI rules: read [docs/design/APPLE-UI-POLICY.md](../design/APPLE-UI-POLICY.md) first (AGENTS.md/CLAUDE.md). Load
  the `kodi-ios-ui` skill.

## Already on PR #16 (done, tested, not built)
- Drive sign-in: a refused refresh token (sign-in server 400/401) is never retried until the owner signs in again;
  a 429/5xx holds every refresh 120 s; one "Sign in to Google Drive again" notice (`driveupload.SignedOut`,
  `RefreshBusy`, `refresh_error`; `scripts/test_drive_signin.py`). Notice details render diagnostic JSON as sentences.
- AllDebrid replies that are not its JSON are retried and described (`alldebrid.Busy`; `test_alldebrid_busy.py`).
- Tabs & Rows › a tab matches Home (Continue Watching first, real count, rows Home never shows listed last), with
  ▲ ▼ always shown (`rows_editor.py`, `rows_page.py`, `customise_rows.py`; `test_customisation.py`).
- Transfers' Up next says "faster start" for re-packs (`transfers.queue_lists`; `test_repack_label.py`). Re-packs
  stay automatic (owner: "I would love for all my stuff to open quick").

## Phase 1: log review (finish this before the pages)
Two audits of the build-192 log were started and did not report back. Redo them. The owner must attach the log
again (`kodi.log`, 12:57:32 to 13:13:36, build 192). Decode the `Kodi iOS diagnostic {json}` lines; the `runtime`
snapshots carry the queue states.

Facts already known:
- From 12:57:45 until the owner re-signed in at about 13:09, the sign-in server refused the Drive refresh (400).
  Then 429 came from our own retries every 5-10 s (fixed above). All Drive work was blocked, yet the pages kept
  showing old states.
- Inception (AV1 4K HDR, re-encode, 1.5-1.8x real time) started at 13:09:56. Lanterns S1E1 (a re-pack,
  copy=True) took over at 13:13:05. Find out why Inception stopped (kept? replaced? the new AllDebrid source?).
- "Drive reads: 103 MB in 187 s (0.55 MB/s)" at 13:13: check whether reads limit the conversion.
- `prepare_cloud.py` ~line 141, `waiting()`: writes "Step 3 of 3 · Paused while a video plays" whenever the
  Sink is held. But `preparation.paused` (service.py) is also true for Pause converting (`transfer_control`) and
  for AirPlay (`airplay_busy`), and the stage stays in `prepare_downloads` state `current` until the next progress
  call. That is why it said "paused as a video plays" with nothing playing.
- Transfers shows "Nothing is moving right now" when `transfer_history.running/activity` finds no fresh record
  (fresh windows 10-15 s against saves every 10 s; see HANDOFF-R28 item 2 for the build-183 fix).

Deliver a short findings report (worker by worker, minute by minute, every idle stretch with its cause and
file:line), then the fixes below.

## Phase 2: one status model (the backbone of every page)
Today Library status, Notifications, Transfers and the bell each read different files at different ages. Build a
single `activity_state` (new module, e.g. `resources/lib/work_state.py`) that the service writes about every 2 s
and that every page and the bell read:

| State | Meaning | Words on screen | Colour |
|---|---|---|---|
| running | moving at full speed | "Converting" / "Making it start faster" / "AllDebrid → Drive" · speed · time left | purple (prepare), blue (download/upload) |
| slowed | a video or AirPlay plays; still moving, throttled | "Slower while AirPlay plays" / "Slower while a video plays" | grey ring |
| paused_by_you | long press › Pause | "Paused by you" + Resume | grey |
| needs_you | only the owner can fix it (Drive sign-in, AllDebrid key, no source) | one sentence + one button | red badge, orange card |
| waiting_network | offline, server busy, backoff | "Waiting for the network · trying again in 1 min" | grey |
| queued | in line | "Up next · #2" | blue number |
| ready / kept | done / kept as it is | "Ready" / "Kept as it is" | green / grey |

Rules: a state older than ~6 s is never shown as running; "paused by a video" only when `Player.HasVideo` is
really true; the reason is stored with the state (never guessed by the page); every page updates within 2 s.

## Phase 3: never stop, only slow down
Owner: always moving, slower while AirPlay plays. List every hold first (`service.py` `preparation.paused`,
`airplay_busy`, `idle()`, `uploading=`, `keep_going`, `drive_stream.hold`, debrid `keep_going`), then:
- While a video plays in Kodi, or AirPlay plays: keep converting at a reduced CPU share (`app_state.Pace`), and
  throttle Drive reads/uploads and AllDebrid copies to a share of bandwidth (for example 25-35 %). AirPlay must not
  stutter: the TV reads from Kodi's in-app server over Wi-Fi, so measure and back off if its read rate drops.
- Show it as "slowed", not "paused".
- Add tests for each rule (scripts/test_*.py style). Keep the owner's Pause as a real pause.

## Phase 4: the approved pages (Kodi skin XML generated by Python; policy §2)
Reuse `portrait.py`/`pages.py` helpers and tokens (policy §8). Mockup size 402 × 874 pt; 1 pt = 2.687 units; every
tap target ≥ 118 units; text never below 30 units (`p_cap`); one line per text run, truncated with "…".

1. **Library status** (`library_page.py` IOSLibraryStatus.xml, `library_status.py`, `library_rows.py`,
   `prepare_downloads.library_view`): header with back and refresh; "Working on now" card (poster, purple eyebrow,
   title, the step alone on line 2, progress ring with %, sparkline + "4.8 MB/s · 6 min left", tap opens the sheet);
   a summary card ("8 of 12 ready · about 1 h 20 min to go", one segmented bar, four tappable counts Ready / Working
   / Up next / Kept, replacing the ring and the filter row); "Up next" with numbers and Edit order; "Ready for Kodi
   and AirPlay" with green checks. Board 1.
2. **Needs you and slowed** (same page): an orange "Sign in to Google Drive again" card with a white Sign in button;
   the working card saying "Converting", then "Slower while AirPlay plays · 1.1 MB/s · 25 min left"; a
   "Downloading to Google Drive" section for AllDebrid copies (blue bar, "AllDebrid → Drive · 2.4 MB/s · 9 min
   left"); "Kept as it is" with "Being replaced by the new download above". Board 2.
3. **One movie sheet while working** (`IOSLibraryItem.xml`): sheet with grabber and ✕; poster, title, "4K · HEVC ·
   2.8 GB"; three step bars (Downloaded, On Drive, current step + %); a graph card ("Right now 4.8 MB/s", time
   left, the graph, Average / Done / Started); one plain sentence; Play (primary) and Pause. Board 3.
4. **Transfers** (`transfers_page.py`, `transfers.py`): "2 running · 2 up next"; chips per running job; card with
   the step + %, big number "4.8" + "MB/s · 6 min left", the new graph, a bar, Peak / Average / Started; Up next with
   "convert" / "faster start". "Nothing is moving" only when nothing runs or waits. Board 4.
5. **The new graph** (`transfer_history.render`): today 470 × 220 px stretched to ~924 × 430 units, 1 px aliased
   line, no labels. Render at the displayed size × device scale with anti-aliasing (supersample), a 2.5-pt
   rounded line, a gradient fill, faint guide lines; draw the axis numbers (MB/s), times and the peak label as Kodi
   labels; a dot for "now". Same renderer for the small sparkline. Boards 1, 3, 4.
6. **Notifications** (`portrait.notices_page` IOSNotifications.xml, `notifications.py`, `prepare_downloads.cards`):
   "Running now" uses the same card as Library status, smaller (poster, title, one status line with speed and time
   left, thin bar); an "Up next: …" line linking to Library status; "Earlier" rows with a coloured icon, unread
   dot and time. Read from the status model only. Board 5.
7. **Bell** (`portrait.bell`, `notices.py` Notices.Unread/Active): plain when idle; progress ring with the real %
   and a blue count of running jobs; grey ring when slowed; red badge only for needs-you. Board 6.
8. **Queue** (`library_tools_page.queue_page`, `tool_windows.open_queue`): "One at a time, top first · about 1 h 20
   min"; the job running now with %; numbered Up next with round ▲ ▼ (greyed at the ends); the note about
   faster-start jobs. Board 7.
9. **History** (`library_tools_page.history_page`, `transfer_history.py`): Today / Yesterday / 7 days; "Didn't
   finish" first (red mark, the reason in plain words, one "Try again"); "Finished" with time and what was done.
   Board 8.
10. **Movie sheet when ready**: three green steps; rows "Kodi · Opens in about 1 s", "AirPlay · Ready, seeks
    instantly", picture, sound and subtitles; a needs-you card only when relevant; Play and Play on TV. Board 9.

## Phase 5: tests and hand-over
- Unit tests for the status model, each state's words, the slow-down rules, the graph renderer (size, anti-aliased
  edge pixels, labels), and the page XML (ids, hit sizes, no overlapping labels: `test_notices.OverlapTests` style).
- Run every `scripts/test_*.py` (skip `test_drive_runtime.py`, which needs arguments),
  `python3 -B scripts/check_project.py` and `python3 -B scripts/check_ui_guidance.py`.
- Visual check (policy §7): render with `scripts/portrait_rig.py` if a desktop Kodi build is available. Otherwise
  report visual verification as pending, and say which evidence class each screenshot is.
- Update `docs/HANDOFF-R28.md` ("Next build (193)"), commit with `[skip ci]`, push to the branch, update PR #16's
  description. Do not build until the owner asks.
