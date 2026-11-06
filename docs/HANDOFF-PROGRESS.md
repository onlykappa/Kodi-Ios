# Kodi iOS — live progress (updated 2026-11-06 ~04:45 UTC)

Working branch: `feature/library-status` (PR #12, draft). Worktree: `/tmp/claude-0/-home-user-Kodi-Ios/06c10366-b20c-55b8-ac88-a3d2020d9a15/scratchpad/libstatus`.
PR #9 and #10 merged into main. PR #11 (Apple UI guidance) stays open, untouched.
Always commit with `[skip ci]`; builds are started by hand (import-review.yml = IPA, airplay-remux.yml = native CI).

## Builds
| Build | What | State |
|---|---|---|
| 160 | Library status opens (Addon id fix), leftovers freed, phone-space card | Released; owner tested |
| 161 | Folders on Library status, iPhone free-space figure, one space estimate, KodiAirPlay r15 (Interstellar .sup subtitles), notification log sheet | Built (run 42160779351), **not verified / not sent**: superseded by 162 |
| 162 | 161 + Play on TV fix + AllDebrid-to-Drive downloads | **Not started yet** |

KodiAirPlay r15 is published and pinned (`8afe0096…55a9`, verified run 42160014524, 1605 host checks).

## Done in source, committed and pushed (head 60c4f12)
- ISSUE-113: Library status as folders (one layout; Waiting / Ready / Kept folders; Back returns to All).
- ISSUE-114: `phone_space.free` (iPhone's "important usage" figure); `work_bytes`/`space_needed` with the probe, plus a "Why" line on a waiting video.
- ISSUE-115: KodiAirPlay r15 keeps PGS subtitles as `.sup` beside the MP4 and uploads them next to the video on Drive. Interstellar gets one retry.
- ISSUE-112: notification tap opens a sheet with its kodi.log lines.
- ISSUE-116: Play on TV runs one at a time, shows "Connecting…" with Cancel, and gives a plain reason instead of "can't play (MP4)". Root cause in the build-160 log: the second press tore down the first AirPlay session (-1004).

## In progress: AllDebrid straight to Drive (owner chose this; NOT committed yet)
Owner: "a movie im downloading goes onto my phone still … large movie wont ever download". Elementum torrents land on the phone first.
Files written, not yet tested or committed:
- `resources/lib/alldebrid.py`: API v4 client (`add`, `status`, `files`, `unlock`, `pick`). Key = Umbrella setting `alldebridtoken`.
- `resources/lib/driveupload.py`: `Drive.upload_stream` (web file → Drive resumable upload, 16 MB chunks, resumes at Drive's offset).
- `resources/lib/debrid_drive.py`: job queue `debrid-drive.json` and `step()` (new → fetching → copying → done/failed); `uploads()` for the cards.
- `resources/lib/notices.py`: `uploads()` also shows the AllDebrid copy.
- `service.py`: `debrid_loop` thread inside `drive_uploads` (runs during playback, then rescans the library and asks preparation to check).
- `download.py`: `to_drive()` hands the picked torrent to AllDebrid for Download only and seasons, and removes it from Elementum along with its files. Download and watch still uses Elementum.

### Next steps
1. Write `scripts/test_debrid_drive.py`: fake AllDebrid answers (add, status, files tree, unlock, errors), `pick` (movie / episode / season with episodes), `upload_stream` resume, `step` end to end, `to_drive` wiring, `notices.uploads` showing the copy.
2. Run all `scripts/test_*.py` (skip `test_drive_runtime.py`, which needs args) and `python3 -B scripts/check_project.py`.
3. Add ISSUE-117 (AllDebrid to Drive) to docs/ISSUES.md, commit `[skip ci]`, push.
4. Dispatch import-review.yml on `feature/library-status` → build-162. Verify the IPA: r15 binary sha `aac8ee21…`, plus `debrid_drive.py`, `alldebrid.py`, `phone_space.py` and `IOSNoticeDetail.xml` present.
5. Send the owner the build-162 link and a test list:
   - Folders.
   - Phone space vs iPhone Storage.
   - Inception's "Why" line.
   - Interstellar becomes Ready with a `.sup` on Drive.
   - Play on TV: press once, see Connecting; on the TCL Roku TV watch for sound-only with HEVC.
   - Download a movie: nothing should go to the phone; the Uploading card should show AllDebrid then Drive.
   - Tap a notification for its log.
   - Delete the old 19.8 GB `Fall.2022.2160p.WEB-DL…` file from Elementum Downloads.

## Waiting on the owner
- Log sheet and Settings search mockup: BOTH APPROVED (https://claude.ai/artifact/BNL6H5zvTd1tXmF7oEUUiT). Log sheet is built (ships in 162).
- TODO build 163, Settings search: native iOS search field (KodiGlassBar r3 `kodi_search_*`, as `searchbar.py` drives it on the Search page) at the top of Settings; results listed under it as you type from `settings_search.search`, grouped "Kodi iOS" / "Kodi settings", each with where it lives and a chevron; tap runs the row's action; Cancel or clear restores Settings. Today `settings_search.py` opens Kodi's keyboard page (black "Enter Search Query", see ISSUES).
- Merge PR #12 only with the owner's approval.

## Known open questions
- The TCL Roku TV may play only the sound of prepared HEVC MP4s (it needed H.264 before).
- Inception probably needs a re-encode (its codec will show on its details sheet with r15).
- The `.sup` subtitles are saved on Drive, but playback from Drive does not attach them yet.
