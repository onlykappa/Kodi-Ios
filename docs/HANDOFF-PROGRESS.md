# Kodi iOS — live progress (updated 2026-11-06, build 174; merged into main)

## Branches
- **`fix/elementum-cloud-164` (PR #13): current work.** Codex continued here from `feature/library-status` (`2b3cbb6`) and produced builds 164–168. KodiAirPlay r17, GlassBar r6, portrait r23. Its notes are in `docs/pr13-verification.md`, `docs/elementum-cloud-downloads.md` and `docs/diagnostic-logs.md`.
- `feature/library-status` (PR #12): older; everything on it is included in PR #13.
- PR #11 (Apple UI guidance): stays open and untouched. PR #9 and #10 are merged.
- Always commit with `[skip ci]`; builds are started by hand (import-review.yml).

## Builds
| Build | Branch | State |
|---|---|---|
| 163 | feature/library-status | AllDebrid→Drive, folders, r15. Verified |
| 164–168 | fix/elementum-cloud-164 | Codex: r16/r17 storage-free preparation, HDR re-encode, native Settings search, diagnostics/export. 168 tested by owner (log `Kodi-build-168-…log`) |
| 169 | fix/elementum-cloud-164 | This session: fixes below plus KodiAirPlay r18. Commit 36d528f; native CI run 42238135886 → pin r18 → publish → import-review |
| 170 | fix/elementum-cloud-164 | r19, speed text. Owner tested |
| 172 | fix/elementum-cloud-164 | cancelled (superseded by 173) |
| 174 | fix/elementum-cloud-164 | KodiAirPlay r21 (pinned 8e51391…, candidate run 42279166590) + library tools (Queue, History, AirPlay check), cleaner close button. Built and verified (run 42289027680, release build-174, IPA sha a175df70…): build.json commit c588cc7, AirPlay binary identical to the r21 candidate, `prepare: … made in … s` log line present, library tools pages and close_disc.png inside. Owner testing conversion |
| 173 | fix/elementum-cloud-164 | r20 + simple Transfers + sheet bar + checks no longer restart conversion. Built and verified (run 42266852853; r20 sha a5e323fe…, interrupts(), track(), sheet bar 9210) |

## Build-168 log findings (owner, 04:31–04:42 local)
- Inception (2010): AV1 10-bit HDR 3840×1600, copy=False, so it needs a full re-encode. It stayed at "0%" with about 79 MB read in 3 min. Kodi restarted at 04:39 and the conversion restarted.
- Fall 2 (AllDebrid → Drive, 18.1 GB): 52 MB copied. Codex measured 76–86 s for Drive to acknowledge each 16 MB (~0.2 MB/s), while the conversion was using Drive at the same time.
- Settings search: "Control 9160 in window 13000 has been asked to focus, but it can't". The search page was hidden while the field was empty, but its modal dialog stayed on top, so taps went nowhere and Back was hidden.

## Build 169 changes (this session)
- Settings search page always visible: before typing it lists Settings' own rows; list focus is set; Back always works (`settings_page.search_window`, `settings_search.py`).
- Each Drive copy chunk logs its source-read and Drive-send times and MB/s (`driveupload.upload_stream`), so the next log shows which side is slow.
- While an AllDebrid file is being copied into Drive, preparation waits its turn; it resumes afterwards (`debrid_drive.copying`, service loop).

## Build 174 (build-173 log 11:05–11:20)
- r20 did nothing on the phone: the storage-free path (`kodi_airplay_prepare_to` → `generated_open/read`) kept
  6-second units and had no timing. r21: PREP_UNIT there too, and each unit logs time and route. Host test checks
  the notes. Speed in 173 unchanged (~0.06 %/min).
- Transfers: "XML File for Window is missing" on every tap. Kodi's `CFile::Exists` answers from its directory cache
  when the portrait folder was listed before the file was written. Fix: `portrait.refresh_listing` lists the folder
  after writing; `transfers.run` re-lists and retries once.
- 11:19 restart from 0 was playback (owner played a video at 11:18), as expected.

## Build 173 (build-170 log 09:36–09:52, owner: "converter is like not working at all")
- Inception went back to 0% twice: the 09:36 Kodi start, and at 09:44, 15 s after the Fall 2 AllDebrid copy finished.
  Cause: the copy's on_done asks for a library check, and any check request stopped the running conversion
  (`converting` lambda in service.py). Storage-free conversion (prepare_cloud + Drive Sink) cannot resume, so the next
  attempt cleared its staging and started from 0. The Library status refresh button did the same.
- Fix: `prepare_downloads.interrupts(profile)`: only the owner's Prepare next / Keep stop a conversion; checks wait.
- Still restarts from 0: Kodi being closed or killed, and video playback (idle() is false). Real resume needs native
  work (resume the Sink at Drive's confirmed offset from a checkpoint). Not done yet.
- Speed in r19: about 0.055 % of the film per minute (~5 s of film per minute, ~0.08× real time, ~30 h for Inception),
  reading ~1.4 MB/s from Drive. r19 does not log the decode route; r20 (in 173) logs route and time for every 30 s unit.
  If the route is the CPU (dav1d) for AV1 HDR, hardware AV1 decode is the next fix.
- 172 was cancelled (built before this fix); 173 = 172 + this fix.

## Build 172 (owner: "converter is like not working at all but downloading is working great")
- Carries KodiAirPlay r20 (30-second preparation units; 171 was cancelled before it shipped). r20 is the converter fix to test.
- Transfers page redone (owner-approved mockup "simple graph"): one job at a time. The tapped card's job (down / up / conv) gets the graph,
  its speed now, peak, average, started; its bar and time left. When it ends, the page moves to the next running job. "Also running" rows
  switch the graph. Finished jobs (size, time, peak) and Up next below. No range switch, no upload-limit line.
  `transfer_history` now keeps one record per job (`activity`, `track`, `pick`, `finished`), not the build-171 5 min / 1 h / 24 h rings.
- Details sheet for converting/uploading: a progress bar in the job's colour (id 9210); Time left reads "about 25 min" (no doubled "left").
- Approved but not built yet: Phone space, Queue (Edit order), History (Transfers › History), AirPlay check (mockup
  https://claude.ai/artifact/3ajZJDwzALocLDJ4xxwE8n). Owner asked whether History needs a Library status row too: not answered yet.

## Build 171 (from the build-170 log): KodiAirPlay r20 (cancelled; shipped in 172)
- Inception converted at ~0.55 MB/s read (about a quarter of real time, ~10 h). Cause: preparation used the live-AirPlay 6-second units; each re-seeks to its keyframe, re-decodes from there, flushes the decoder and opens a new encoder.
- r20: whole-file preparation uses 30-second units (`PREP_UNIT`). The checkpoint stores the unit length, so a 6-second checkpoint starts over instead of being misread.
- Each unit logs "prepare: video i/n made in X s for 30 s of film (Nx real time) via <route>" (hardware HDR / GPU / CPU + decoder), through `kr_remux_note`.
- Screens (owner, build 170 screenshots: "no way for me to see download or upload speed anywhere … the details are blank and seem ugly"):
  - The upload card, Library row and pill show "86% · 8.4 MB/s · about 4 min left".
  - The conversion (prepare_cloud) records the read speed and a time left.
  - The details sheet for converting shows Step, Speed, Time left, the size on Drive, and Video ("AV1 10-bit HDR → HEVC (re-encoded)").
  - The details sheet for uploading shows Progress, Speed, Time left and Saving to.
  - The folder tiles' icons are fixed (ICONS path). The footnote is shorter.
- Steps: native CI → pin r20 (previous r19 785178e5…) → publish → build 171 → verify.

## Build 170 (from the build-169 log, owner: "downloading is alot quicker", "converting is having issues still")
- Copy speed is fixed: AllDebrid 12–17 MB/s in, Drive 6–8 MB/s out (it was 0.2 MB/s).
- Inception (build 168, 05:08) failed after 30 min on "Picture subtitle packet: Invalid data" (r15 sidecar writer). r19: a malformed or empty PGS packet is skipped, not fatal (`kr_prepare.c`).
- Interstellar (07:03) failed after about 2 h on "Preparation upload did not acknowledge its byte range". `drive_prepare.Sink._send` now keeps what Drive confirmed (partial 308) and resends the rest; it retries lost answers and 5xx up to 8 times with backoff.
- The 169 rule "preparation waits for AllDebrid copies" kept Inception paused; removed (both run at once).
- "Connection reset by peer" tracebacks from the loopback Drive reader (the converter hangs up when it seeks) are no longer logged (`drive_stream._Server.handle_error`).
- DONE: r19 pinned (785178e5…, run 42242998942, 1819 checks), published; build 170 built and verified (r19 inside, fixes present). Owner upload cap is 70 Mbps (~8.75 MB/s): Drive copy already at the cap.

## Build 169 additions (owner: iPhone 16 Pro, "add the decoder and everything you recommend", no torrent filter yet)
- KodiAirPlay r18 source (kr_video.c): HDR kept at its size passes the decoder's P010 VideoToolbox frames (AV1/HEVC hardware decode) straight to hevc_videotoolbox Main10. Before, the GPU path skipped HDR, so every 4K 10-bit frame was copied to the CPU and back. If the phone refuses once, the CPU path is used for the rest of the session.
- `app_state.Pace`: no CPU cap while Kodi is on screen; 60% of a core in the background (iOS kills apps over 80% for 60 s). If the state is unknown, it counts as background.
- Progress shows what was read from Drive and the MB/s (`speed_text`, `live_line`), never a bare 0%.
- Codex's `docs/pr13-simulation/*.png` were removed from Git (the project check bans binaries). Copies are in the scratchpad at `pr13-screenshots/`.
- Steps left: when the native CI passes, set source-lock to r18 (previous r17, source_commit 36d528f, verified_run = CI run id), update `test_airplay_remux` lock expectations, commit `[skip ci]`, dispatch airplay-ios.yml publish_verified_candidate=true, verify the release sha, then dispatch import-review → build 169 and verify the IPA.

## Lost from the Codex session (hit its usage limit before pushing). Redo if still wanted
- RAM range cache for Drive reads during conversion ("96 repeated reads → 2 upstream fetches").
- Remove the foreground CPU pacing in `Native.convert` (keep it only in the background). Needs a reliable foreground/background signal.
- Show conversion progress without a rounded "0%".

## Open questions
- Is Drive upload really ~0.2 MB/s from the owner's network? Build 169's chunk timing will show.
- Inception's AV1 4K HDR re-encode on the phone may take many hours. An alternative is to download a different (HEVC) version.
- The TCL Roku TV may play only the sound of HEVC.
