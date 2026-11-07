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

## Next build (192, not built yet: owner collects more bugs first)
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
