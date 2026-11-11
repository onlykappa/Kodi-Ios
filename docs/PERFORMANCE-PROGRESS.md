# Performance roadmap — progress log

Read this first when taking over. The plan is docs/ROADMAP-PERFORMANCE.md. Update this file at every step:
what was done, where it lives (branch, commit, run), what was verified (and how), what is next.
Never claim a phone result without the owner's log or screenshot.

## Current state

- PR #16 (claude/trusting-euler-kgug98 → main): owner asked to merge (2026-11-11). Head eb91571. Merge only with green
  checks (review, host-tests, executable).
- Build 229 is the owner's current app. Build 230 (pending) = PR #16 merged + AirPlay r47 (kodi_http_send for uploads,
  EXT-X-START, MKV audio seek, attachments skip) + Kodi r30. Source of truth for what each build holds: docs/PROGRESS.md.
- Desktop Kodi rig: KODI_RIG_HOME=/root/.cache/kodi-rig-test. Restart with `kodi_rig.py start`; after copying the add-on
  run kodi_rig.bootstrap_copy (keeps the rig_builtin hook); `sync` regenerates pages; ReloadSkin. A Trakt sign-in prompt
  appears on Home in the rig only: send Input.Back twice before opening a page. Script windows (sheets) must be closed
  with Input.Back or an xdotool tap (DISPLAY=:5), not Dialog.Close.

## Steps

| When (UTC) | Step | Result |
|---|---|---|
| 2026-11-11 16:30 | Roadmap drafted (phases 0-3) after the 1-10 audit | docs/ROADMAP-PERFORMANCE.md |
| 2026-11-11 16:30 | Phony individually downloaded episodes added as 2.2 | finding only, not fixed |
| 2026-11-11 16:40 | 1B.1 version rows badge 10-bit H.264 "SLOW ON AIRPLAY" (deck_picker.converts_for_tv) | local branch phase1-work 6779f62; test_deck_picker TvReady |
- 1A.1 (code): interpreter_probe.py + service thread logs 'Kodi iOS interpreter wait: median/p95' once a minute while an AllDebrid→Drive copy runs. Test scripts/test_interpreter_probe.py. Needs a device log to read.
- 2.2 (code): cause found: a single-episode copy goes to Drive folder named from the file ('phony'), and the Library searched TMDb by that name only, so it could land on another show or none, with no episode names, stills or plots. Fix: finished copies record the job's show_tmdb under the title and folder names in drive-library-art.json (drivelibrary.remember_show, debrid_drive.remember_shows, plus a one-time backfill from finished jobs at service start). Episode rows with no TMDb name read 'Episode N', not the show name. Tests in test_library_pages and test_debrid_drive. Needs a device check on Phony.

## Handoff (2026-11-11 ~17:00 UTC)
- PR #16 head 027f4c3 (CI apt timeout fix); checks were running. Merge #16 when green.
- Do NOT merge #17 or #18 (owner, 2026-11-11): an agent works on them first. Their open work: 2.3 add-on settings tabs
  (board 08), 2.4 "- " dash (Kodi patch), 2.5 Kodi PIN/time number pads, 2.6 More/power-menu links to old windows,
  ISSUE-156 "Find subtitles online" against the real site.
- This branch (claude/performance-roadmap) = #16 + roadmap docs + 1B.1, 1A.1, 2.2. After #16 merges it shows only these.
- Then: pin AirPlay r47 from the airplay-remux run on 027f4c3 (framework zip sha256, exports _kodi_http_send, health,
  startup_budget; source_commit 027f4c3, previous r46), dispatch airplay-ios.yml publish_verified_candidate=true,
  import-review.yml for build 230, verify, record in PROGRESS/HANDOFF.
- Next items: 1A.2, 1B.3, 1B.2, 1C.1, 2.1, 2.3-2.6.

## 2026-11-11 investigation (owner: "investigate before we code")
- Read owner logs e8ab5995 and 396d5d67 (build 229) and the 37 earlier logs. Roadmap rewritten with measured timings,
  known causes and new items 1A-1G, 2.8-2.17, 3.5-3.6. No code changed for these yet.
- Biggest finds: Drive playback goes through plugin.googledrive's Python proxy (open 11-13 s, seek 4.2 s); Home rows
  reload on every tab return and around playback (31 Python runs each); Drive copies ignored outside Continue
  Watching (ios_watch_dialog cloud=resume) which also breaks Next Episode; subtitle site does not resolve.

## 2026-11-11 build 232 log (eabc204b)
- ISSUE-168 found and fixed: drive_uploads crashed at start (UnboundLocalError 'airplay'), so build 232 never uploads or
  copies. Fix in service.py; scripts/test_service_scoping.py catches it. Needs the next build.
- Roadmap: "Build 232 findings" B.1-B.11 and "UI" U.1-U.14 (Arctic Fuse/Kodi windows that need mockups) added.
- 2.8 (code): Drive copies found on every way in (Next Episode, spotlight Play, show pages) from the saved Drive listing, no network wait; a failed Drive check there counts as no copy. Continue Watching keeps the strict check. Fixes 2.9 when the episode is on Drive. Tests: test_drive_library (cached_only). Device check pending.
