# Handoff: state at 2026-11-07 (after build 182 started)

Branch `claude/trusting-euler-kgug98` = draft PR #14. `main` = same commit (b65cf2e). Every change below is
committed and pushed; nothing is only local. Builds are started by hand; commit with `[skip ci]`.

## Builds since r24 (details per build in docs/HANDOFF-PROGRESS.md)
| Build | What | State |
|---|---|---|
| 176 | r24: HEVC prio_speed, 2 hardware video lanes | verified, owner tested (~1.8x real time, upload-bound) |
| 178 | background 32 MB Drive upload thread, Transfers + movie sheet redesign, Play / Play on TV | verified, owner tested |
| 179 | r25 only | not given to the owner |
| 180 | r26: stuck unit remade after 90 s, off-screen CPU decode, Start converting now, audio = original + English | verified, owner tested |
| 181 | r27: upload once (promote + bin), English subtitles only, subtitle uploads on own threads, AllDebrid read-ahead | verified, owner testing (Interstellar ~40 min, works) |
| 182 | r28 keep-awake re-armed on background/foreground, Drive read 4 blocks ahead in parallel, Home hero copy compared without page, quick movies first | verified (IPA sha 90ead4df…, build.json b65cf2e, AirPlay binary = r28 release ec5249b9…) |
| 183 | 182 + Transfers never says "Nothing is moving" during a conversion | built (superseded by 184, not given) |
| 184 | r29 (prepared AirPlay through one source + 48 MB cache; pinned 80346abc…, run 42328810669) + upload and read-ahead wait while a video plays + 183 | verified (IPA sha f52c5e0f…, build.json df4b22c, AirPlay binary = r29 release 4a310154…). Owner testing AirPlay |

r28: pinned in `migration/airplay-ios/source-lock.json` (sha 34b0d61b…, CI run 42326849053) and published
(release kodi-airplay-r28, digest matches).

## Next steps, in order
1. **Build 182**: when run 42327383714 ends, download release build-182, check build.json commit = b65cf2e, airplay
   tag r28, binary sha = candidate of run 42326849053; record in HANDOFF-PROGRESS; give the owner the link.
2. **DONE in 183.** Transfers said "Nothing is moving right now" at random while converting (owner screenshot, build 181). Two
   causes, NOT fixed yet:
   - `transfer_history.running(fresh=10)` while `watch()` saves every 10 s: the page reads a record up to ~10+ s old.
     Fix: fresh=30 (and/or save every 4 s).
   - `transfer_history.activity`: conversion counted only if prep `current.updated` < 15 s old; the muxer's progress
     callback stalls while a 32 MB piece uploads. Fix: 60 s, and `prepare_downloads.cards` (line ~846, `<15`) too.
   Add tests in scripts/test_transfers.py. Ship in build 183 (Python only).
3. **Resume after Kodi is closed** (owner asked: "nice for app updates"). Not started beyond reading the code.
   Plan (kr_prepare.c `prepare()` with a writer): fMP4 with `+empty_moov+default_base_moof+frag_keyframe`,
   `frag_duration` 6 s. Record per confirmed Drive offset of the main track the last complete fragment (unit index,
   end time, fragment sequence, byte offset); on restart: skip units before it, open the muxer with `fragment_index`
   continuing, drop the new init, continue the Drive resumable session (drive_prepare.Sink keeps url + offset) at the
   confirmed offset. The trailing `mfra` must list every fragment: either write our own mfra from the recorded list
   or rebuild it; `kodi_airplay_verify` must pass. Host test: stop mid-file, resume, verify. Sidecars (.sup) and the
   audio tracks need the same treatment. Big change: its own native release (r29) and build.
4. Elementum download settings checked (rate limits 0, connections auto, DHT on): left as they are.

## Owner decisions in this session
- Prepare everything ahead of time once; only Umbrella streams play live.
- Upload once (new Drive file id; watched/resume may reset once: accepted).
- Keep only the original audio + English, and only English subtitles (untagged ones kept). No lower picture quality.
- Quick (repack-only) movies before re-encodes; Start converting now overrides; Prepare next waits its turn.
- Conversion must keep going in the background (keep-awake) and never freeze.

## Known numbers (owner's iPhone 16 Pro, his line)
- AV1 4K HDR re-encode: ~2.5x real time with 2 hardware lanes (chip-bound); Inception ~1 h.
- Drive upload: 32 MB pieces 3-4 s on a good line (8-10 MB/s), 6-17 s when the line is busy.
- Copy-only 4K (Interstellar 8.4 GB): ~40 min in build 181; 182 should be faster (parallel reads).

## Session 2026-11-07 (after 182)
- 183: Transfers fix (built from 59156d6). AirPlay of Buddy failed in the build-181 log ("Cannot Complete Action"):
  every AVPlayer range opened a new Drive connection (1-6 s) and the line was busy with Interstellar's upload.
- 34fcf8b: while a video/AirPlay plays, the conversion's upload pieces (Sink.hold) and Drive read-ahead
  (DriveStream.hold) wait too.
- r29 source: kr_remux serve_prepared reads through one kept-open source + 4 MB x 12 block cache (prepared_read).
  Next: CI, pin r29, publish, build (184). Then owner tests AirPlay; then optional "gentle mode" during AirPlay only
  (keep converting with 1 lane, no read-ahead, upload capped ~50%) — owner agreed to step 1 first.
- Resume design: docs/RESUME-DESIGN.md (not started).

## Build 185 — verified (IPA sha 4721fe31…, build.json 1e8cc12, airplay r29 unchanged, find_quicker / STALL / deck_picker AVOID inside). Owner testing
(owner, build-184 log: AirPlay works; conversion slow and inconsistent for hours)
- Diagnosis from the log: converter ~2.5-3x real time on screen; the Drive upload stalled (32 MB piece hung 120 s,
  timed out) and the converter waited on the 2-piece queue; Kodi start restarted Inception from 0; playback paused it;
  off screen the picture decodes on the CPU (iOS refuses VideoToolbox off screen).
- 55b7309: stall retry after 45 s (driveupload.STALL), AHEAD 4, Elementum max_upload_rate 1024 KB/s when unlimited.
- 74f6129: background CPU share 0.7 (iOS ends background apps over ~80% of a core for a minute).
- 3154fd0: "Find a version without converting" (Library status sheet for re-encode movies → download.py replace=1 with
  Home property KodiIOS.AvoidAV1 "<quality>|<time>"; deck_picker shows only non-AV1 at that quality); AV1 links last
  and labelled in every picker; unique() keeps the copy that needs no re-encoding.
- Resume after Kodi closes: NOT in 185. docs/RESUME-DESIGN.md. Open question found while starting: the mfra rebuilt
  from parsed moofs must use movenc's tfra time (start_dts + tfdt + cts), and start_dts per track is not in the
  stream; options: write edts-free output (start at 0) or keep movenc's tfra entries by parsing each session's
  trailer. Do it as its own native release (r30) with a stop/resume host test.

## Build 186 — Python only (airplay r29 unchanged)
- 54d4e8e: picking "Find a version without converting" stops the AV1 conversion (prepare_downloads 'replace') and the
  AllDebrid download goes first.
- 426c094: long press on a transfer card in Notifications (the touch keymap's long press is a right click, which became
  "previous menu" and closed the page) → menu: pause / resume, cancel, speed graph. transfer_control.py holds the
  choices as files the service reads: paused-conv (same hold as playback), paused-up (Drive uploads and AllDebrid
  copies stop at the next piece, resumable), cancel-up (AllDebrid job ends as Cancelled). Cancel conversion = Keep as is.
- AirPlay (owner build-185 log, "airplay stops out of nowhere"): the TV's first range read of the prepared movie took
  12 s, the next ones ~19 s, while an AllDebrid copy went up to Drive and Kodi's paused player still read the movie;
  Apple's player timed out at 39 s. Now Window(10000) KodiIOS.AirPlay holds the time AirPlay was last seen working
  (cast.send_airplay marks it, airplay.relay refreshes it from Apple's player log lines, closed/stopped clears it,
  90 s expiry); while set, AllDebrid copies, Drive uploads, preparation (hold) and the library scan wait. A timeout at
  the start is retried once (cast.retry_airplay).
- Build 186 = run 42339610759 (Python only, the items above).

## Build 187 — resume after Kodi closes (KodiAirPlay r30)
- 5f1475b: native marks + kodi_airplay_prepare_resume (design in docs/RESUME-DESIGN.md, findings there): av_write_frame
  + flush per packet, own mfra (+skip_trailer), tfdt rebased, inputs restarted at their recorded next packets.
  Local FFmpeg 8.1.1 host run: 2087 checks, 0 failed (test_preparation_resume: copied tracks join byte for byte,
  PGS sidecars carry on, AV1 HDR -> HEVC + AC-3 -> AAC joined movie validates, a foreign mark is refused).
- Python: drive_prepare.Sink pieces end at floor256K(latest mark) (MARK_CAP 96 MB: past it the movie goes up anyway),
  checkpoint after Drive confirms (resume_store.py: preparation-resume/<slot>.json, <slot>.side<track>), sidecars
  spooled and uploaded at finish, md5 skipped on a resumed run (Drive md5 + verify decide), ResumeFailed -> start again.
  Tests: scripts/test_resume.py. Exports 23 (build-airplay.sh).
- Build 187 = run 42341483347 (r30 pinned, sha 4f102aad…). Owner ran it overnight: Kodi never closed, so resume was
  not exercised yet.

## Build 188 (Python only) — verified (IPA sha 981cc980…, build.json 8ee00ec, AirPlay binary = r30 release d4524be2…)
(owner, build-187 log: Interstellar "timed out"; downloads and AirPlay stop with the screen off)
- Interstellar converted and uploaded in ~7 h (402 PUT write timeouts of 45 s overnight), then the read-back probe of
  the Drive file (120 s) timed out and the retry waited behind Fall 2. Now check-only jobs go first (order_key) and the
  probe is tried 3 times.
- AirPlay is a keep-awake reason (service.py why): the TV reads from Kodi's in-app server.
- docs/PROMPT-ALWAYS-RUNNING.md: the owner's prompt for the "works whenever Kodi is open" project (measure first:
  lifecycle / network path / per-piece upload gaps; then URLSession background uploads, progress-based stalls, audio
  session, AirPlay while locked, Elementum sockets).

## Build 189 (Python only) — verified (IPA sha 8b3aa3fe…, build.json 4bc9ccf, AirPlay binary = r30 d4524be2…)
(owner: "why is fall 2 so so slow")
- Build-187 log, every drive_http event over 8 MB: 250 pieces went through at a median 0.43 MB/s, 399 failed with
  "The write operation timed out" at exactly ~45 s. Python's socket timeout limits the whole sendall (3.5+), so a 32 MB
  piece needed 0.73 MB/s; the effective rate was ~0.1 MB/s. driveupload.request_timeout: 45 s + 1 s per 128 KiB of
  body for uploads (32 MB → 301 s); read-only requests unchanged. Expect ~0.4 MB/s on the owner's line (~4x).

## Build 190 — verified (IPA sha 071e5efd…, build.json eb616e9, AirPlay binary = r31 60dbeed8…). KodiAirPlay r31 + resume rework (docs/AUDIT-CONVERSION.md)
(owner, build-189: Interstellar "starting" for 5 min; "do a full rundown audit and tests on this conversion")
- Read-back check walked every fragment (no mfra use, validate without network options): fixed in r31.
- Resume: copies skip what Drive has past the mark (byte-identical, r31 first-packet move); re-encodes keep the movie in
  32 MB files until Drive has them and save every mark at once; MARK_CAP 256 MB.
- New end-to-end test migration/airplay-ios/remux/tests/e2e_conversion.py, run in CI host-tests (airplay-remux.yml).
  Local: e2e 200/0, native 2,097/0.

## Build 191 — verified (IPA sha 5826e4be…, build.json e6da035, AirPlay binary = r32 e785ea37…)
- r32: interleaved samples + ~64 MB fragments (Kodi plays converted movies smoothly, opens faster; earlier conversions
  keep their layout), 4 MB output buffer, "Finding where it left off" (stage 4); library check beside a conversion.
- UI (second agent): DialogBusy is a centred pill in portrait and landscape (was Fuse's Kodi-logo badge floating on the
  poster grid / over video); Fuse's landscape video info inset 140 from both sides (Dynamic Island); OSD taps ≥150.
- Open UI items found: DialogNotification / DialogVolumeBar / Custom_1193 still stock; Custom_1152 can show while our
  OSD is up (title twice); portrait.fingerprint() does not hash activity_skin.py. Local: e2e 194/0, native 3,143/0.

## Build 192 — verified (IPA sha 41477d75…, build.json be5358b, AirPlay binary = r33 2111267… from release 86ce5247…, run 42411704392)
KodiAirPlay r33 (source 53c7968, CI run 42410566627, published by airplay-ios run 42411384562). Contents:
(owner, build-191 log: Fall 2 "stuck on starting / 67%")
- Fall 2 carried on at byte 15,807,214,282 (as on build 190) and reached the mux loop: its only progress call was the
  audio lane's unit 166 of 196 (67.76% = 80 x 166/196), then nothing for 3 min and no Drive upload at all: the lane was
  reading the ~30 s of 4K it re-encodes from. Not reproduced locally (e2e incl. TrueHD + skip 11.75 MB + 32 MB pieces).
  Now: the unit a resumed run waits for reports stage 4 ("Finding where it left off"), the bar starts at the mark's
  place in the film, the sheet's "Right now" names the step instead of "starting", and Drive read speed / last read /
  error are logged every minute while converting (service.py check_beside) — the next log will show the cause.
- "Converting and saving to Drive" → "Converting" (owner). Library status / sheet default focus on controls that exist.
(owner, build-191 log 18b7b4b0: Interstellar "takes forever" to open; Library › Movies "takes a few seconds" with
"kodi ios something" over the page; a clean loading circle)
- Interstellar: Kodi's demuxer took 30 s (11:11:06 → 11:11:37) walking the r31-layout fragments. PROFILE is now
  source-resolution-mp4-v2; v1 still counts as ready (plays, AirPlay) and is queued as a 'repack' job after all others
  ("Making it start faster": a straight remux into r32's layout, uploaded again, original binned).
- Movies tab: the Drive listing cache lasted 5 min and invalidate_library deleted it, so most opens listed Drive live
  while Kodi showed the add-on's progress box ("Kodi iOS Watch Options"). Now the page shows the saved list
  (listing(stale_ok=True)), invalidate marks it stale, and service.library_lists refreshes stale lists every 10 s.
  The page logs "Kodi iOS Library: <type> page in N s".
- DialogBusy: just the spinning ring in the centre (no pill, no "Loading…").
- Local: e2e 199/0 (adds the repack scenario), native 3,143/0, all scripts/test_*.py.
(owner: Customisation mockups, round 4: first pages; scripts/test_customisation.py)
- Settings › Customisation: "Widgets" → "Tabs & Rows", "Indicators" → "Poster Badges"; Poster Badges and Video
  Controls show "N on" (customise_counts.py, counted from the same skin settings).
- Poster Badges is a native page (9330): 11 of Fuse's indicator switches in three groups with a preview. Our own
  posters (Home/Movies/TV rows, Library grid) and episode rows now draw those badges: one corner badge (watched,
  Trakt watchlist, Trakt favourite, collection, in library), episodes left, progress bar, video version, premiere /
  finale. Before this only the Library grid had a watched tick, so Fuse's switches changed nothing on our pages.
  Fuse's "Recently Added" switch is left out: Fuse itself never reads Indicator.DisableLatest.
- Video Controls is a native page (9340): Hide Controls After (Fuse's OSD_Timeout, now honoured by our controls:
  they close that long after opening or the last tap, never while paused or with Continue Watching open), and the
  two switches of the info shown over the video at start/pause (Custom_1152/1153). Fuse's Details panel and
  swipe-up rows are not on the page: our Apple TV-style controls do not have them.
- Not yet: Info Page still opens Fuse's box, but our portrait info page has none of those sections (Starring,
  Seasons, Recommendations…), so its switches do nothing on the phone. Tabs & Rows, Rows editing, View Types and
  Skin Settings pages come next.
- portrait.fingerprint now includes activity_skin.py.
(owner: "add 1-3 and the customisation pages too … then 5 and 6 in the next build")
- Quick wins: Fuse's info over the video (Custom_1152/1153) hides while our controls are up (the title showed twice);
  Kodi's notifications and volume bar are iOS banners at the top (portrait and landscape, pages.NOTIFY / VOLUME); the
  controls' Info wait (Custom_1193) shows the centred ring instead of Fuse's corner spinner; fingerprint as above.
- Tabs & Rows (9350): Home, Movies, TV Shows with their row counts; each opens IOSRows.xml (customise_rows.py,
  rows_editor.py): rows with style and source, Edit (delete disc, ▲ ▼), a row's page (Show This Row, Name, Style
  Poster/Landscape, its content, Delete), Add Row (ready-made TMDb Helper / library rows, or any add-on folder), Restore
  Default Rows (the list as it was before the first change here). Writes the same Skin Variables lists Home reads; a
  row that is off keeps "disabled": "true" (portrait.usable skips it). On close after a change: portrait.refresh_skin
  (rebuild + reload). Search Page row removed: our Search page never read searchwidgets.
- Info Page (9360): Starring, Crew, Seasons, Collection, More Like This, Videos & Trailers, now rows under the plot on our
  info page from TMDb Helper (by tmdb id, else title + year), each behind Fuse's VideoInfo.Widgets switch; a row
  that is off has no path, so it asks TMDb Helper for nothing.
- View Types (9370): Poster Grid (3 across) or Large Posters (2 across) for the Library / category / search grid
  (Skin.String(Portrait.Grid), conditional layouts on panel 53).
- Skin Settings still opens Fuse's window: its options change Fuse's own (shrunk) windows, not our pages.
(owner, build 191: new source for Inception → "AllDebrid gave an answer this app cannot read", details showed a
"Control 9201 … asked to focus" line; the log sent started after a restart, so the reply itself is unknown)
- alldebrid.Busy: no connection, HTTP errors and replies that are not AllDebrid's JSON are tried again (debrid_drive's
  retry, up to 20 times) instead of failing the job at once, and say what came back ("HTTP 503, a web page: …" and the
  endpoint). Every retry and failure is logged ("Kodi iOS AllDebrid: …"). Focus chatter is no longer picked as a
  message's "What happened". scripts/test_alldebrid_busy.py.

## Next build (193, source implementation complete; not built)
(owner, build-192 log: "Google Drive upload paused · Drive sign-in refresh: HTTP 429")
- The sign-in server's refresh answered 400 from Kodi's start (Google refused the saved sign-in: re-sign-in needed;
  likely the OAuth app is in Testing, whose refresh tokens Google ends after 7 days). Two threads then asked again
  every 5-10 s until the server answered 429. Now: driveupload.SignedOut (400/401) is never retried with the same
  refresh token (signing in again saves a new one); RefreshBusy (429/5xx) holds every refresh 120 s; the message is
  "Sign in to Google Drive again" once; notification details show diagnostic lines as sentences. test_drive_signin.py.
(owner, build 192 screenshots: Tabs & Rows said 17 rows, Home has 7 and starts with Continue Watching; "arrows to easily
change up the layouts")
- The Rows page now matches Home: Continue Watching fixed first, then the rows Home shows in Home's order; rows Home
  never shows (in-progress lists Continue Watching replaces, menus such as Video add-ons) are listed last, faded, with
  why. Counts are rows on the page. ▲ ▼ on every row at all times (they move among Home's rows); Edit adds delete.

(build-193 roadmap Phases 1-3, completed 2026-11-07; Phase 4/5 authorized by the owner and implemented below; not built)
- Phase 1: docs/LOG-REVIEW-192.md (two audits of the build-192 log). Main cause: the converter's own `prepare:` log lines
  counted as AirPlay playing and held every worker 90 s ("Paused while a video plays" seven times; no video played).
- Phase 3: `slowdown.py`: nothing waits for playback; a video plays → 35 % share, AirPlay → 25 % (8 % for 60 s after a
  slow TV read); converter pace (`app_state.Pace`), Drive reads (one block ahead), Sink upload pieces, phone uploads,
  AllDebrid copies. `service.idle()` is only "not closing". The owner's Pause holds as before and says "Paused by you".
- Phase 2: `work_state.py` (work-state.json every 2 s; bell properties Notices.Active/State/Pct/Tint/Count/Needs).
  Library status and the Queue (`align`), Notifications (`model_cards`), Transfers (`page_state(model=…)`) and the bell
  (`notices.badge`) read it. Needs-you: Drive sign-in refused, no AllDebrid key. Waiting: Drive busy, AllDebrid retry.
- Python only (KodiAirPlay r33 unchanged). Tests: test_slowdown.py, test_work_state.py; all scripts/test_*.py pass.


(build-193 roadmap Phases 4–5, 2026-11-07; owner authorized source implementation and branch push, never a build)
- All ten Phase 4 source items are implemented: the nine approved boards now compose shared model-owned cards,
  three-step sheets, summary counts, per-job chips, graph labels, bell states, Queue and unfinished-first History.
  Full item matrix, files/architecture, validation changes, known mockup differences and iPhone checks:
  [BUILD-193-UI-HANDOVER.md](BUILD-193-UI-HANDOVER.md).
- Only `claude/trusting-euler-kgug98` was used. Draft PR #16 remains based on `main`. Every new commit uses `[skip ci]`.
  No converter or native pin changes (KodiAirPlay r33), no app/IPA build, release or merge.
- Visual verification is **PENDING** on the owner's iPhone; the later desktop rig experiment was stopped at the
  owner's request. Approved HTML is evidence class **mockup**; host XML/pixel tests do not prove appearance.
- Validation: **80/80** `scripts/test_*.py` passed (only `test_drive_runtime.py` excluded); final focused
  `test_build193_pages.py` passes 14 tests. `check_project.py` and `check_ui_guidance.py` both pass, with zero issues.
  Updated old layout pins follow the approved boards; no test was removed or weakened to hide a failure.


(build-193 owner review, eight findings; source only, no build)
- Separate transfer identity from titles so the kept old Drive copy and its sheet survive a replacement download.
  Elementum Pause/Resume/Cancel uses the engine; incomplete transfer sheets do not offer Play. Notification cards
  retain conversion IDs and AllDebrid source/hash metadata, and AV1 conversions retain QUICKER as the third action.
- Needs-you recovery closes sheet/page before executing its action. Graphs cache per job/sample count/last time;
  Transfers retain first-seen starts while history catches up. History hides retry for blocked + repack_failed jobs
  instead of bypassing the deliberate REPACK_STOPS block.
- Ten added regression tests in `test_build193_pages.ReviewFindings`; item-by-item rationale and test names are in
  [BUILD-193-UI-HANDOVER.md](BUILD-193-UI-HANDOVER.md). The owner prefers the iPhone for the next visual review;
  desktop rig work was stopped and no uncommitted rig layout changes are included.
- Follow-up validation: **80/80 test scripts passed**, excluding only `test_drive_runtime.py`.
  `test_build193_pages.py` passes **24 tests**; `check_project.py` and `check_ui_guidance.py` pass with zero issues.

## Build 193 — built (run 42427536454, release build-193, IPA sha256 5de60540…, commit 11599d0; AirPlay lock r33 unchanged). Owner testing
Phases 1-3 (status model, slow-down instead of holds, docs/LOG-REVIEW-192.md), Phase 4 pages (Codex 317e128 + review fixes
5df3e24), graphs redraw at most every 10 s with old graph folders deleted (11599d0). Visual check: device only (no rig).

## Next: Kodi r24 (prepared movies open by their index) -> build 195
(owner, build-194 log: Fall (2022) took ~40 s to open; "Creating Demuxer" -> "Opening stream" = 30.3 s and 30.7 s)
- Cause: Kodi's FFmpeg mov demuxer walks every fragment header over Google Drive; KodiAirPlay's own opener uses
  use_mfra_for=pts (kr_prepare.c:139). Fix: kodi-21.3-portrait.patch, CDVDDemuxFFmpeg::Open (Kodi I/O path) sets
  use_mfra_for=pts for mov/mp4 (logs "opening MP4 by its fragment index"). build_tag = kodi-ios-portrait-r24.
- Steps: kodi-ios-portrait.yml run on this branch publishes release kodi-ios-portrait-r24 -> set source-lock
  executable_release (tag r24, sha256 of Kodi-portrait-executable.zip) -> import-review.yml = build 195.
- Check on the phone: Fall opens in a few seconds (log line above), seeking/resume right, MKV unaffected.
  Evidence for the option so far: KodiAirPlay's FFmpeg 8.1.1 (1,305 reads -> 14); Kodi bundles its own FFmpeg: unproven there.
## Build-194 log follow-up — Play on TV, source only (2026-11-08)

- Owner's ready movies repeatedly fail with AVPlayer -1004 and no server request evidence. Analysis, exact log
  references, delivery boundary and iPhone steps: [LOG-REVIEW-194.md](LOG-REVIEW-194.md), ISSUE-120.
- Python/plist: Local Network purpose string, lock acquired before discovery/picker, 15-second first-TV-request
  deadline, no unreachable retry, Kodi resume, and a persistent `work_state` needs-you card with Settings action.
  r33 falls back to shared native log evidence and manual Settings instructions.
- Native **r34 source is staged, not built or released**: en0-only iOS LAN address, served host/port, listen result,
  accepted peers/early token-redacted requests, first-TV-request timing and a non-draining network API; ordered
  starts/stops and canceled-generation protection; `UIApplicationOpenSettingsURLString` bridge.
- **Do not treat source changes as delivered in r33.** After owner approval, run native host/CI verification,
  build/release r34 and verify its real asset before changing `migration/airplay-ios/source-lock.json` in another
  `[skip ci]` commit. No r34 pin/hash was fabricated. Both existing AirPlay r33 and Kodi r24 pins are unchanged.
  An app/IPA build or release still needs the owner's go-ahead.
- Validation: **82/82** test scripts pass, excluding `test_drive_runtime.py`; 13 new AirPlay network tests and the
  staged-plist regression pass. Fixed the pre-existing stale r23 pin assertion to match this branch's r24 pin and
  retested all 27 GlassBar tests. Project/UI guidance, shell syntax and diff checks pass. Device review is pending;
  the supplied log is device failure evidence, not proof of a successful fix. No new layout or rig work in this pass.

## Owner-approved native delivery — r34 (2026-11-08)

- Owner approved the native release and explicitly chose an installable iPhone IPA. Candidate run
  [42441688126](https://github.com/onlykappa/Kodi-Ios/actions/runs/42441688126), source `1ea6307`, passed:
  iPhoneOS framework compilation, **3,107 host checks / zero failures**, end-to-end conversion / zero failures.
- Downloaded the candidate, verified GitHub's artifact digest, ZIP integrity, ARM64, all 25 ABI exports and no
  exported FFmpeg/libass internals. Real framework ZIP SHA256 `1831b9ea…`, binary `c4d4e932…`; detailed evidence:
  [airplay-r34-delivery.json](../reports/airplay-r34-delivery.json). Pin updated to this candidate; publish it via
  `airplay-ios.yml` with `publish_verified_candidate=true`, then verify the release equals the candidate before
  starting the IPA workflow. r33 is preserved as previous. No merge authorized.
- Preflight also corrected the existing r24 pin from ZIP checksum to the verified executable checksum (ISSUE-121).
  The Kodi version/tag remains r24. Native and host evidence still does not prove device playback.

## Build 196 — published and verified (owner-approved, device retest pending)

- [Installable IPA](https://github.com/onlykappa/Kodi-Ios/releases/download/build-196/Kodi-iOS-Customized-Touch-r10.ipa),
  [release](https://github.com/onlykappa/Kodi-Ios/releases/tag/build-196),
  [successful build 42442484724](https://github.com/onlykappa/Kodi-Ios/actions/runs/42442484724).
  Built from `a2b9b8b` on this branch; no merge. IPA SHA256 `40dc7d15…`, 620,333,330 bytes.
- r34 [publication 42442400925](https://github.com/onlykappa/Kodi-Ios/actions/runs/42442400925) succeeded.
  Downloaded release ZIP equals the tested candidate byte-for-byte, with the immutable tag targeting `1ea6307`.
- Downloaded the actual IPA and checked ZIP integrity, GitHub's asset digest, source/build identity, r34/r24/r6
  pins, the Local Network purpose string and Settings script. AirPlay r34 and the corrected Kodi r24 executable
  match their verified release binaries after signature removal. Full checksums/evidence:
  [airplay-r34-delivery.json](../reports/airplay-r34-delivery.json).
- Final repeat of **82/82** test scripts passes (only `test_drive_runtime.py` excluded). One unchanged upload timing
  test measured 1.2217 s against a 1 s threshold under host load; all 26 tests passed on the unchanged focused rerun.
  No worker/test threshold was changed. Project/UI guidance checks pass. Native: 3,107 checks and 199 end-to-end
  checks, zero failures; 13 Python network regressions and the r24 archive-vs-executable regression also pass.
- Owner: install the IPA as an update with the sideloader, allow Local Network when prompted, test a ready movie,
  two quick Play on TV presses, Cancel, and the 15-second recovery/Settings button with an unreachable TV. Capture
  the new log if it still fails. Only the iPhone can establish that playback works; this delivery is host-verified.

## Build 196 device follow-up — r35 candidate (owner-approved new IPA)

- [Device log analysis](LOG-REVIEW-196.md), ISSUE-122: the old watchdog reported a LAN failure at 15 seconds;
  the listener appeared about 129 seconds after first startup. Local Network was enabled. No TV request occurred.
- Fix the actual startup path: indexed fragmented-MP4 opening, cancellable initial HTTP headers, bounded native
  startup, pre-reserved tickets and stale-work/cleanup protection. TV selection and its connection have separate
  deadlines. Opening a slow source never becomes a permission warning.
- Screen-locked playback: AVPlayer retains Playback/MoviePlayback, continues-if-possible background policy and
  the IPA's audio background mode. Native active ownership overrides an expired log lease and background-download
  preference; download silence cannot replace the player's audio session. Natural end/failure/close release it.
- The owner authorized a new native release and installable IPA. Verify the candidate first, then pin/release
  the actual r35 artifact and build the IPA; r34 stays pinned until the candidate passes. No merge. Screen-lock
  behavior and successful TV playback remain **PENDING** on the owner's iPhone.
- Source is pushed in `9976d705e60b92d6094cf124018a95735cbd9722`. Candidate verification:
  [42448621268](https://github.com/onlykappa/Kodi-Ios/actions/runs/42448621268), dispatched explicitly on this
  branch. The iPhoneOS framework compilation has passed; host/E2E checks are still running at this checkpoint.
  The full 82-script Python sweep is also running (only `test_drive_runtime.py` excluded). It found an old
  23-export source assertion in `test_conversion_speed.py`; updated to the actual 26-export ABI and all 48 tests
  pass on focused rerun. Project/UI guidance and shell syntax checks pass. No r35 pin/release or new IPA yet.
- Resume delivery: wait for **both** native jobs and all Python scripts; download and independently verify the
  candidate ZIP/hash/ARM64/26 exports. Only then pin r35 with the real digest, source `9976d70` and run above,
  preserving r34 as previous; update exact-pin tests. Push with `[skip ci]`, publish through `airplay-ios.yml`
  with `publish_verified_candidate=true` (publish the tested candidate without rebuilding), verify release bytes,
  then dispatch `import-review.yml` on this branch for the authorized IPA. Download/verify the actual IPA's
  identity, audio background mode and native binaries; record full delivery results and update PR #16.
- Python sweep finished: **82/82 scripts pass after the corrected ABI assertion**, only `test_drive_runtime.py`
  excluded. Both guidance/project checks pass. Downloaded candidate matches GitHub's artifact digest; ZIP, ARM64
  iPhoneOS binary and all 26 exports verified. Candidate/provisional delivery evidence is preserved in
  [airplay-r35-delivery.json](../reports/airplay-r35-delivery.json). Compiled host/E2E verification is still pending;
  the report explicitly records that pending state and does not claim publication or device success.

## Build 199 — verified (run 42450976942, release build-199, IPA sha256 6794810f…, commit 2a95041; AirPlay r35). Owner testing

- **AirPlay r35** pinned from candidate run 42448621268 (source 9976d70; archive 0a61e958…, binary 2a0dbdcd…) and
  published without rebuilding (run 42449531141). Owner's build-196 log: Play on TV gave "unreachable" after exactly
  15.0 s with no server line while the phone was still opening the movie (ISSUE-122); r35 opens by the index and gives
  opening, TV choice and connection their own deadlines.
- **Play on TV card** (DEC-030, owner-approved boards 1-3, 5, 6): `airplay_flow.py`, `1080i/IOSAirPlayFlow.xml`. Board 4
  (remote while the TV plays) needs native pause/seek: not built.
- **ISSUE-123** live pages change controls only while open (the build-194 crash on a skin reload), Drive upload pieces
  logged with their speed (no false http_error), the desktop Kodi rig (`scripts/kodi_rig.py`, docs/design/KODI-RIG.md).
- Build 197 failed at its test gate on one stale assertion (fixed in 2d76c28); build 198 (2d76c28) is green but has no
  Play on TV card; 199 supersedes it.
- Verified in the downloaded IPA: build.json build 199 / commit 2a95041 / run 42450976942; KodiAirPlay binary 2a0dbdcd…
  with `_kodi_airplay_active` and `_kodi_airplay_settings`; airplay_flow.py, live_window.py and the new cast.py present.
- Owner to check on the iPhone: Play on TV steps and the problem buttons (Try again, Pause uploads and try again, Open
  Settings), AirPlay playback and screen lock, the live pages after an update (no crash), the nine boards.

## Build 200 — verified (run 42452868611, release build-200, IPA sha256 829234f6…, commit 68d2e26; AirPlay r36). Owner testing

- **AirPlay r36** (ISSUE-124): candidate run 42452271611 (source 46b199f) passed the framework, host and end-to-end
  jobs (the first run 42451808459 failed only the new host check, which needed the mpeg4 stand-in encoder);
  published by run 42452830779; release digest 10285d76… equals the pin. A TV that takes only the sound of a prepared
  movie (the owner's TCL Roku TV with HEVC) gets the picture converted to H.264 after 4 s.
- Verified in the downloaded IPA: build.json build 200 / commit 68d2e26 / run 42452868611; KodiAirPlay binary
  4f377156… with the sound-only fallback; cast.py resets the deadlines after the restart; the card's "Converting the
  picture for your TV"; live_window.py present. Everything in build 199 is included.
- Owner to check: Play on TV to the TCL Roku TV shows the picture (expect the converting step after ~4 s of sound);
  the Play on TV card; screen lock; the live pages after an update.

## Build 201 — verified (run 42494735003, release build-201, IPA sha256 8ad43633…, commit 5c39256; AirPlay r37). Owner testing

- **ISSUE-125** (build 200 on the phone): the Play on TV card was never loaded (Kodi's directory cache: "XML File for
  Window is missing"), and r36's H.264 restart was cancelled by an immediate "could not open the stream" -1.
  Python: `portrait.refresh_skin` re-lists every written folder; `cast.FlowUI` retries once after re-listing 1080i
  (reproduced and confirmed in the desktop Kodi rig). Native r37: `compatBusy` and a 1.5 s failure grace.
- **AirPlay r37**: candidate run 42456369892 (source fb7c714) green; published by run 42494696805; release digest
  c1448149… equals the pin.
- Verified in the downloaded IPA: build.json build 201 / commit 5c39256 / run 42494735003 / airplay r37 c1448149…;
  KodiAirPlay binary 6b3a7327… identical to the candidate's; cast.py has the card retry; portrait.py re-lists every
  written folder.
- Owner to check: Play on TV shows the new card (not Kodi's OK dialog); to the TCL Roku TV, sound first, then
  "Converting the picture for your TV", then the picture.

## Build 202 — verified (release build-202, IPA sha256 1c26f482…, commit 1057ad8; AirPlay r38). Owner testing

- **ISSUE-127** (build 201, Apple TV black screen): Apple's player walked the prepared fragmented MP4 fragment by
  fragment and never became ready. r38 serves prepared movies as HLS byte ranges from the file's own fragment index
  (`prepared.m3u8`, `prepared-media.m3u8`); files without an index keep the plain MP4.
- **ISSUE-126** (build 201, TCL): Kodi watches 45 s after "playing"; a stop goes to Kodi's slow-internet card (no
  pause button, uploads keep running) instead of Apple's bare alert; the converting text is a pill at the top.
- **AirPlay r38**: candidate run 42500369872 (source 361a9d9) green, 3,143 host checks plus end-to-end (the new
  checks: streamed prepared movies come out as HLS, the first and last ranges are moofs, the last ends at the mfra,
  the init is ftyp+moov). Two earlier r38 candidates failed (CACurrentMediaTime needs QuartzCore, not linked; an
  unchecked strstr in the new test on a faststart fixture). Published by run 42501396321; release digest 598cb990… =
  the pin.
- Verified in the downloaded IPA: build.json build 202 / commit 1057ad8 / airplay r38 598cb990…; KodiAirPlay binary
  0411ba79… identical to the candidate's; cast.py has airplay_settle; airplay_flow has slow_source.
- Owner to check: (1) Apple TV with a prepared movie: starts within seconds in 4K/HDR; (2) TCL TV: converting pill at
  the top, then the picture or the slow-internet card; send logs either way.

## Build 203 — verified (release build-203, IPA sha256 6fd2b0d1…, commit 66084d1; AirPlay r39). Owner testing

- **ISSUE-128** (build 202 worked on the Apple TV): the TV starts where Kodi was (`kodi_airplay_start_at`), Kodi
  continues where the TV stopped (`airplay.back_to_kodi`), prepared movies' text subtitles go as WebVTT renditions
  with Kodi's one selected.
- **AirPlay r39**: candidate run 42504243855 (source a13154a) green (the first r39 candidate failed one new check: the
  test inherited "subtitles off" from an earlier test). Published by run 42505585480; release digest 60379f9b… = pin.
- Verified in the downloaded IPA: build.json build 203 / commit 66084d1 / airplay r39 60379f9b…; KodiAirPlay binary
  a368da87… identical to the candidate's; airplay.py has back_to_kodi.
- Owner to check: Apple TV (start position, Kodi position after stopping, subtitles); TCL Roku TV with a prepared
  movie (the earlier "sound only" was probably ISSUE-127's fragment walk, so HEVC may now play).
- Next (build 204, owner: "work on any TV on the same Wi-Fi"): Roku's Play on Roku channel (15985) was locked in
  Roku OS 11.5 (home-assistant/core#83819); Rokus without AirPlay can use the free Media Assistant channel via ECP
  launch; Chromecast/DLNA should get the phone's prepared playlist instead of the Drive link. Roku is not a DLNA
  renderer.

## Build 204 — verified (release build-204, IPA sha256 28a37188…, commit 98eb3f2; AirPlay r40). Owner testing

- **ISSUE-129** (any TV on the Wi-Fi): `kodi_airplay_serve` (r40) gives Roku (Media Assistant, channel 782875),
  Chromecast and DLNA TVs the phone's playlist / prepared MP4 instead of Kodi's 127.0.0.1 link.
- **ISSUE-130** (Customisation): rows marked and counted as Home shows them; Add puts the row first.
- Includes builds 202-203 (prepared HLS, start/resume position, subtitles). Owner linked Trakt in TMDb Helper
  ("Trakt authenticated successfully!", 10:10:53 phone time); Elementum's own Trakt link is still off.
- **AirPlay r40**: candidate run 42506835029 (source 8e160ce) green; published 18:03 UTC; digest 9a3415cd… = pin.
- Verified in the downloaded IPA: build.json build 204 / commit 98eb3f2 / airplay r40 9a3415cd…; KodiAirPlay binary
  145f122f… identical to the candidate's; cast.py and airplay.py use kodi_airplay_serve; rows_editor has empty_rows.
- Owner to check: Apple TV; the TCL over AirPlay; the TCL as a Roku with Media Assistant; Customisation counts;
  the Trakt rows on Home.

## Build 205 — verified (release build-205, IPA sha256 78ab48be…, commit d317d12; AirPlay r40). Owner testing

- **ISSUE-131**: Add Row offers TMDb and Trakt trending, Now Playing and Airing Today; new rows go at the bottom and
  the page moves to them; a row change rebuilds only the hub files (0.06 s in the rig instead of 4.7 s).
- Everything in build 204 (any-TV routes, Customisation counts), AirPlay r40 unchanged.
- Verified in the downloaded IPA: build.json build 205 / commit d317d12 / airplay r40 9a3415cd…; rows_editor has the
  new lists and slot_of; portrait.refresh_rows is used by customise_rows.

## Build 212 — verified (release build-212, IPA sha256 dcc94e10…, commit 551f32c; AirPlay r41). Owner testing (ISSUE-138)

- **ISSUE-138** (Roku): Media Assistant gets the prepared movie remuxed (`kodi_airplay_serve_segmented`: picture
  copied, 6-s segments, audio apart) instead of the muxed byte-range playlist Roku does not support; Roku's AirPlay
  turning the prepared playlist down converts once to H.264; the first 8 MB of a prepared file are read ahead and
  the init is kept in memory.
- **AirPlay r41**: candidate run 42547843379 (source 29b128f) green, 3,177 host checks, 0 failed, plus end-to-end;
  published by run 42549203217; release digest aea92b57… = the pin.
- Verified in the downloaded IPA: build.json build 212 / commit 551f32c / run 42549244096 / airplay r41 aea92b57…;
  KodiAirPlay binary 7c3f2f1e… identical to the candidate's, with `_kodi_airplay_serve_segmented`; cast.py and
  airplay.py use it.
- Owner to check: (1) Roku › Media Assistant with a prepared movie: the picture starts; (2) the Roku's AirPlay:
  "Converting the picture for your TV", then the picture or the slow-internet card; send kodi.log either way, the
  Roku model, and what the TV screen says if it fails.

## Build 210 — ISSUE-137: buffering % moved into the video controls; its own dialog (which froze Kodi) never opens

## Build 208 — ISSUE-136: all background work (uploads, copies, conversion) waits while Kodi plays or buffers a video; AirPlay unchanged

## Build 207 — verified (release build-207, IPA sha256 f5a94ad5…, commit d4fd6d6; AirPlay r40). Owner testing (ISSUE-135)

- Season copy speed: build 206's per-MB download gate asked Kodi's GUI each time and waited on its lock in the
  background (1.3 MB/s instead of 13-16). `slowdown.watch` now asks once a second on its own thread; workers only read.
- Transfers / Library status: per-episode history title (graph, Peak, Average); speed window keeps the previous piece;
  `live_window.Guard` works on Kodi 21 (no `getId()`) and keeps its wrapper alive (rig crash fixed). Rig-checked.
- Built with owner approval; IPA checked: build.json 207 / d4fd6d6, frameworks airplay 9a3415cd, glassbar ecc883d2,
  ios-portrait 02d5357a; the new slowdown, live_window and transfer_history code is inside.

## Build 206 — verified (release build-206, IPA sha256 538b4a70…, commit 789de12; AirPlay r40). Owner testing

- ISSUE-132 (seeking: download cap while playing, wait while Kodi buffers, 96 MB / 10x cache, Buffering NN% pill;
  season queue per episode), ISSUE-133 (FULL SEASON / EPISODE N ONLY versions, one-episode season notice, Next
  Episode button), ISSUE-134 (the rest of a season follows the first quality pick).
- Verified in the downloaded IPA: build.json build 206 / commit 789de12 / airplay r40; next_episode.py;
  download.rest_of_season; deck_picker.auto_choose and source_match.coverage in Elementum's site-packages;
  slowdown.CAP; portrait generates Custom_1156_Buffering.xml.
- Owner to check: Lanterns › Download Season 1 (FULL SEASON first; else "Get them"); seeking while a download runs;
  Buffering %; Next Episode; the queue listing episodes.
