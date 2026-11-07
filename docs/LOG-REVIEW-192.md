# Build 192 log review (Phase 1 of the build-193 roadmap)

Log: the owner's `kodi.log`, build 192 (be5358b), 2026-11-07 12:57:32 to 13:49:21, 2,054 lines. Two audits ran in parallel
(why the pages disagree; what each worker did minute by minute). Both read the decoded `Kodi iOS diagnostic {json}`
lines and the queue snapshots. Code lines below are at 5336638 (the build-193 base); `L1450` means log line 1450.

## In one paragraph
**No video played and AirPlay was never used in this log** (no player lines; the only "VideoPlayer" lines are Kodi's
start-up). Yet "Paused while a video plays" was written seven times. The converter writes its own `prepare: …` lines
into the AirPlay log; `airplay.activity` took any line there as "AirPlay is playing" for 90 s, and that held the
conversion, its Drive reads, its uploads and the AllDebrid copy, and made the main loop wait 120 s. On top of that,
each page judged "running" by a different clock (1 s, 15 s, 30 s, 60 s, none), a failed library check left
"Checking…" running, and a stopped job kept its last words. So Notifications said paused, Library status said
converting, and Transfers said "Nothing is moving", all at once.

## Causes, worker by worker

| # | What | Log | Code (5336638) | Fixed in 193 |
|---|---|---|---|---|
| 1 | Converter's own `prepare:` lines marked AirPlay busy for 90 s; every worker held | L1449 13:10:20 `prepare: video 2/297…` → L1450 13:10:36 "Paused while a video plays"; L1557-1572 (Lanterns, 13:13:10 → 13:14:36); L1785-1787 (Fall 2, 13:29:06 → 13:30:36); 13:30:10 "Drive reads: 0.0 MB in 60 s, last read 64 s ago" | `airplay.py:132-136`, relayed by `service.py:237-238`; holds at `service.py:252, 302, 325, 410, 415, 419`, `prepare_downloads.py:224-229`, `drive_stream.py:200`, `drive_prepare.py:179` | Only AirPlay server and Apple player lines count (`airplay.airplay_lines`); playback no longer holds anything, it slows (`slowdown.py`) |
| 2 | "Paused while a video plays" hard-coded for every hold (also the owner's Pause and AirPlay) | L1450 | `prepare_cloud.py:140-145` | The reason is stored with the state (`work_state.py`); hold words are only "Paused by you" |
| 3 | The main loop waited 120 s after one busy check | 13:11:05 pass skipped; next pass exactly 13:13:05 (L1562) | `service.py:355-356` (`if not idle(): continue` with `delay=120`) | `idle()` is only "Kodi is not closing" |
| 4 | A stopped job kept its last words ("Paused while a video plays") with `running=False` | snapshots 13:11:36, 13:12:36 (L1542, L1557) after Inception stopped at ~13:11:00 | `prepare_cloud.py:259` | Pages read the status model; a non-running job is never shown as working |
| 5 | Inception stopped because the owner chose "Find a version without converting" (not Lanterns) | L1453 13:10:51 → `replace` request 13:10:59 | `prepare_downloads.py:548-557` (`interrupts`), `:386` (kept + replacing) | As intended; it now shows under "Kept as it is · Being replaced by the new download above" |
| 6 | A failed library check left "Checking downloaded videos" running for 12 min | 12:57:45-13:09:46: 138 refresh failures (400, then 400/429); snapshots show running, age 0-4 s | `prepare_downloads.py:626-629` (never cleared on failure) | `Queue.scan` drops the check card when the check fails |
| 7 | Sign-in refused (400) from start; our own retries every 5-10 s caused the 429s | 12:57:45 → 13:09:46 | b192 `service.py:266, 430` | Already on PR #16 (0a95082: `SignedOut`, `RefreshBusy`); 193 adds the "Sign in to Google Drive again" needs-you card |
| 8 | Each page used its own freshness clock | `current` reached 31-37 s old at 13:28:36 and 13:39:37-13:41:37 | `prepare_downloads.py:922` (60 s), `transfer_history.py:96, 279` (60 s, 30 s), `library_rows.py` card (15 s), Library rows (none) | One status model, written every 2 s; older than 6 s is never shown as running |
| 9 | AllDebrid copy progress had no time stamp; a hung 32 MB piece (301 s write timeout) kept the last speed on screen | 13:23:56 → 13:28:57; sent stuck at 234,881,024 bytes 13:24:36-13:32:36 | `debrid_drive.py:228-237`, `driveupload.py:397` | Progress carries `updated`; the model shows a copy with no progress for 60 s as "Waiting for the network" |
| 10 | AllDebrid try counter never reset: six AllDebrid HTTP 500s at the start made the later Drive timeout wait 210 s | 13:11:12-13:18:43 (6 × HTTP 500), 13:28:57 → retry 13:32:27 | `debrid_drive.py:265-276` | Tries reset after a piece goes up |
| 11 | "103 MB in 187 s (0.55 MB/s)" is not a speed: its window spanned the held and idle time | L1564 13:13:08 | `service.py:381-395` | The window restarts when a new movie starts |
| 12 | Queue counts disagree (Notifications counted kept/blocked jobs) | "N remaining" vs Library status vs Transfers | `prepare_downloads.py:920` | One "Up next" list in the model |

## What limited speed
- Drive reads did not limit the conversion: Lanterns read at 2.1-4.5 MB/s and uploaded at 3.2-3.9 MB/s; reads reached
  6.37 MB/s at 13:29.
- The phone's upload is the limit: 200-270 MB a minute in total, shared by the re-pack and the AllDebrid copy.

## Minute by minute (short)
- 12:57:45-13:09:49: the Drive sign-in is refused; nothing can list Drive, so no conversion starts. The pages show "Checking downloaded videos" running.
- 13:09:49: the owner signs in again. 13:09:56: Inception (AV1 4K HDR re-encode) starts; 2 units at 1.82x and 1.45x real time.
- 13:10:00-13:11:50: held by its own `prepare:` lines (cause 1). 13:10:51-59: the owner picks a version without converting; Inception stops (~13:11:00).
- 13:11:05-13:13:05: the queue waits 120 s (cause 3). 13:11:12-13:18:43: AllDebrid answers HTTP 500 six times.
- 13:13:05-13:28:59: Lanterns S1E1 re-pack (90 s of it held by cause 1), 10 % → 80 %, done.
- 13:21:43: the AllDebrid → Drive copy of Inception starts (1.5-2.8 MB/s); 13:23:56-13:28:57: one piece hangs; 13:32:27: carries on; 32.8 % at 13:49:19.
- 13:29:00: Fall 2 re-pack starts (90 s held, cause 1), ~1 %/min, 20.1 % at 13:48:36.

## Still open after 193
- A hung upload piece is noticed only after its timeout (45 s + 1 s per 128 KiB: 301 s for 32 MB). A progress-based
  stall check is the next step (docs/PROMPT-ALWAYS-RUNNING.md).
- Whether a re-encode's checkpoint was dropped at 13:09:56 cannot be told from the log (the held offset is not logged).

## Second log (same session, 13:49 to 14:16)
- Cause 1 again: Scary Movie's own `prepare: fragments …` line (13:55:52) held it; the 13:56:37 snapshot says "Paused while
  a video plays", 13:56:51 "last read 58 s ago", and uploads fell to 64 MB that minute. Fixed by `airplay.airplay_lines`.
- **New: Fall 2's faster start failed** at 13:55:08, 22 % after 26 min: `MP4 packet: Invalid argument` (the converter's MP4
  writer refused a packet, `kr_prepare.c:1012`; most likely a time stamp in the older prepared file). A retry starts at 0 %
  and would fail at the same packet, with waits growing to an hour. Fix (Python): a re-pack that fails on a converter
  writing error stops and stays as it is (it plays); one "Kept as it is" notice (`prepare_cloud.REPACK_STOPS`). The
  converter itself is unchanged: finding the packet needs a converter log line with its time stamps (own release).
- Speed: the total upload to Drive is flat at 4.0-4.5 MB/s (about 32-36 Mbit/s) whether one or two uploads run; the
  AllDebrid copy reads at 15-25 MB/s but sends 1.5-2.5 MB/s because the re-pack shares the same upload. The line's upload
  is the limit.
- Transfers 14:16:09-18: seven taps on "Also running" (9721), each handled (the graph switches); the approved page
  replaces that row with chips.
- TMDb Helper's "GetDirectory - Error" lines (log_library, log_tagger, timer_report) are its own missing log folders: harmless.
