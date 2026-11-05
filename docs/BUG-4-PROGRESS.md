# Bug 4 — downloaded Library and iPhone scan

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
