# Bug 4 — downloaded Library and iPhone scan

## Authorized merge and test delivery

Owner explicitly requests merging PR #8 and a test IPA. The earlier no-build/no-merge instructions below are historical and superseded for this delivery. Use unique native build tag **kodi-ios-portrait-r23** for the new whole-page scrolling/parent-row source; retain the r22 executable pin until r23 is built, downloaded and verified. Merge with `[skip ci]`, build r23 first, then pin it and package the IPA so the testing build includes the new native fix. Status: delivery in progress; no device success claimed. AirPlay r12/GlassBar r5 pins stay unchanged.

PR #8 merged successfully at `2a8bb1cb16dfa0984f7a1b3d974e20857c0f6d3c`. Native r23 build is the next delivery step; no intermediate IPA using old r22 is being published. Continue on main for this authorized delivery, preserve all merged changes and record final build/artifact evidence when available.

## Current continuation — downloaded show layout / scrolling

Owner supplied Claude screenshots and explicitly asked primary + agents to resume. Synced the clean worktree from `c815259` to current PR #8 head `46367aab6fb3fe3943ee202b1801ca0b002b14be` before editing; preserve all intervening Claude changes, including native r22/r12 pins. Do not build another IPA or merge.

The screenshots request: downloaded TV shows use the polished seasons page with logo/rating/genres/plot, a Play Episode 1 or Continue Episode N button, no Download action for existing downloads, no stray grey episode/play tile, correct Library/show titles, and fluid whole-page scrolling rather than an isolated episode list.

Committed Claude work (`91ff714`, `46367aa`) already merges duplicate show/movie cards, adds episode metadata/background season fetching, names plugin categories and changes navigation button styling. The screenshot's later seasons/Play/Download changes are **not present in this synced branch**: downloaded shows still return `episodes`, the skin still gates Play on `seasons`, and a Refresh Library folder is still appended to episode content. The source also fixes the episode list below a static header, explaining why only its lower portion scrolls.

Assignments completed: `downloaded_show` implemented seasons/episode routes, cached show metadata and exact completed-file Play/Continue state; `show_layout` implemented shared polished skin behavior, stray-item visibility and whole-page scrolling. Primary integrated/reviewed source, added parent-row suppression and ran combined checks. **362 tests across 24 suites pass**, with native methods compiled on the host and the complete patch applied to the exact Kodi pin. Delivery stays in existing draft PR #8 with `[skip ci]`; no new phone success claimed. Earlier validation below is historical to the previous bug-4 patch.

Continuation milestones:

- Baseline synced-source suites passed: Library pages 8, refresh 16, artwork 14, Continue Watching 19 (57 tests before this continuation's changes).
- Downloaded-show seasons routes, cached full-show details and episode playback wrapper are implemented locally; resume/history tests are being added. Episode pages no longer append a refresh folder that could appear as a fake episode card.
- Whole-page scroll design is confirmed against Kodi source: a full-height lazy-rendered episode viewport inside one portrait Videos group, with a scoped native handoff that consumes the header offset first and then episode offset, reversing in the opposite order. XML-only nesting would leave the original swipe capture bug. New native code remains staged and requires a future executable build/pin before phone acceptance.
- Primary review found that Kodi's `Files.GetFileDetails` performs VFS existence/directory work, so calling it for every cloud episode could invoke Drive browsing and local calls could repeatedly rescan a folder. Agent is replacing this with safe/batched local and history/database lookup before final validation.
- Downloaded-show source is now complete: **20 new behavior tests** pass, including batched bookmarks, exact completed-copy resolution, provider/history preservation and Play/Continue refresh after playback. Refresh suite now has **17 passing tests**; artwork suite **14**.
- Layout/native source is complete: **7 tests** compile and exercise actual scroll methods (direction changes, bounds, short lists, isolation and selection). Existing portrait suite passes **44 tests**. Parent-row suppression adds a compiled native decision test. Full patch applies to all **30** affected pinned source files; applied-source comparison confirms only the five intended GUI files differ from Claude's baseline.
- Combined verification exposed two integration issues: unchanged native patch whitespace broke a literal existing tab-bar assertion (restored untouched hunks byte-for-byte; 25 tab-bar tests now pass), and an existing bundle-precompile test requires Python 3.11 while the executor defaults to 3.12. Installing a separate task-local 3.11 interpreter to run that check; no IPA is being built.
- Final verification: both issues above are repaired; **362/362 tests across 24 suites pass**. Full patched-source comparison confirms exactly five GUI files differ from Claude's baseline, with all unrelated native hunks preserved. Exact source hashes, original failures/rechecks and device tests are in [reports/downloaded-show-validation.json](../reports/downloaded-show-validation.json).
- Remaining: the new whole-page touch handoff and parent-row suppression are **staged source**, absent from the pinned r22 executable. A separately authorized executable build/release/pin and actual iPhone testing are needed to deliver/accept those native changes. No new IPA, executable/framework release, merge or owner-media operation occurred in this continuation.

## Scope and status

Owner requests: downloaded movies/shows appear automatically in Library; repair the grey `..` navigation tile; add manual refresh; add Settings › Library › Scan iPhone files for movies and shows, upload missing files to Drive, then delete only verified phone duplicates. Continue in draft PR #8. No IPA, release or merge.

Status: implementation, agent review and combined host verification complete: **258 tests across 15 suites pass**, plus project/iOS static checks and diff validation. Delivery stays in draft PR #8 on `fix/build-141-followup` using `[skip ci]`. No device success claimed. Owner explicitly requested parallel agents on 2026-11-05; three agents handled scan, Settings and regression review. This file is updated after implementation, review and validation milestones.

## Confirmed causes

- The Watch add-on root URL has no media parameters. Kodi's parent-folder entry navigates there and reached the incomplete-media error instead of a root directory.
- Library combined Kodi's scanned database and Drive but omitted completed phone downloads, including completed torrents still seeding.
- Drive TV discovery only included folders: single-file episodes uploaded directly into TV Shows were invisible.
- Drive listings could remain cached for five minutes; upload invalidation ran after a whole batch, so a later upload failure skipped it for earlier successful uploads.
- No explicit Library refresh or phone-file reconciliation action existed.

## Implemented locally

- Real Movies/TV root directory; completed phone listings; strict finished-torrent checks; local show episode navigation.
- Manual Refresh Library entry, context action, and portrait refresh button.
- Visible-page watcher checks phone membership every five seconds and Drive every thirty seconds, refreshing changed listings; no off-page network scans.
- Loose Drive episode discovery and show filtering; preserve strict Continue Watching matches.
- Unique atomic cache temporary files; invalidate after each uploaded file.
- Shared transfer lock and Drive size/checksum verification before automatic uploader deletes phone files.
- Settings › Library scan, folder selection, checksum-based duplicate cleanup, search integration, all-branch Drive indexing and cached-art-first foreground rendering.

## Remaining work

1. Owner device test remains pending: complete a movie/episode, observe Library, refresh, play, run scan with missing/duplicate files, confirm Drive playback and phone cleanup.

## Agent assignments

- Agent 1 (`library_scan`): implement phone-file scan and scan-specific tests. Entry point `RunScript(service.kodi.ios.bootstrap,library_scan)`.
- Agent 2: validate/review Library navigation, discovery, refresh and uploader changes; add focused regression tests.
- Agent 3 (`library_settings`): implement Settings › Library page, scan/refresh controls and Settings-specific tests; coordinate the scan entry point with Agent 1.
- Primary agent: integrate findings, fix remaining issues, run combined verification, update evidence and publish the draft PR.

## Latest review / verification milestone

- Initial existing Drive Library (8 tests) and listing-cache (27 tests) suites pass. Portrait and Continue Watching checks are running; these are provisional results before integration.
- Review identified two issues to repair: a busy refresh must retain its comparison baseline to prevent repeated refresh loops; download discovery/upload must reject symlink, hidden, sample and partial paths.
- Scan and Settings integration remain under active implementation. No upload or phone deletion has been executed by the development tools.
- Scan implementation now exists: streamed MD5 comparison, exhaustive Drive folder index, shared transfer lock, source-change detection, fresh remote verification before deletion, cancellable scan UI and accessible-folder chooser. Agent 1 is adding behavioral regressions and reviewing alias/cancellation edge cases.
- Initial review fixes applied: retain watcher baseline while busy; reject symlink files/directories in completed-file discovery and automatic upload; avoid repeated cloud retries when no cache/account exists; Settings refresh-all now invalidates cache even outside Library.
- Agent 3 has added Settings page wiring locally and is validating navigation/focus. Integration is still in progress; source tests are not phone acceptance.
- Scanner milestone: **29 behavioral/runtime-wrapper tests pass**, including unchanged-source checks, same-size/different-content files, fresh Drive verification, cancellation, active-download exclusions, folder selection and unsigned-Drive behavior.
- Settings milestone: **22 Settings page + 5 Settings search tests pass**. Settings › Library provides scan, refresh-all, fresh Movies/TV routes and Drive/transfer settings; searching “scan iPhone” finds the scan action.
- Existing portrait suite **43 tests** and Continue Watching suite **19 tests** pass. New focused Library/refresh/uploader suites are in final review.
- Final integration follow-up: foreground Library artwork lookup is being changed to cached-art-first with bounded visible-page hydration, preventing many new downloads from causing a series of synchronous poster requests.
- Scanner stale-settings regression added: selecting Documents cannot import preallocated videos from the current default Elementum Downloads folder even when saved settings point at an old sandbox. Scanner suite now **30 passing tests**.
- Review found a second concrete discovery gap: automatic folder lookup treated a Drive HTTP error as an empty result and could create duplicate folders. Folder creation now stops on lookup failure; Library reads every matching Kodi Downloads/Movies/TV branch instead of only the first. Scanner indexing is being aligned with that recovery behavior.
- Focused actual-directory tests now cover phone media with Drive disabled, signed out or offline, sanitized failures, working refresh on an empty page and season-zero episode playback. Uploader tests cover checksum mismatch, source mutation, cancellation before deletion, shared locking and invalidation before a later transfer failure.
- All agent work is integrated. Scanner is now **31 passing tests**, including duplicate-folder branches. Foreground artwork makes zero metadata HTTP calls; **14 artwork regressions** cover bounded visible-only hydration, transfers/playback yield, cache ownership and generic season-pack names. Source review found no remaining blocking defect in this scope.

The phone scan can access Kodi's sandbox and folders made available to Kodi; it cannot silently inspect every other iPhone app's storage. Phone deletion requires a fresh Drive metadata check matching the actual file size and MD5 checksum, with source-change and cancellation checks.

## Final integrated verification

**258/258 tests pass in 15 suites**, including the 43-test portrait layout run. Project and iOS static checks and `git diff --check` pass. Exact suite counts, source hashes, review findings and phone acceptance steps are in [the validation report](../reports/library-downloads-validation.json). Scanner, Settings and review agents completed their work; no source blocker remains in the verified scope. PR #8 remains the sole delivery target, draft and unmerged; main and native pins remain unchanged. No IPA, release or live owner media operation. Device acceptance is the remaining work.
