# iPhone bug-fix follow-up — 2026-11-04

## Baseline and owner instruction

PR #7 was merged into main at `4a78efdeecbc6f9c47018682fbb60ff1829a8a95` with a merge commit containing `[skip ci]`, at the owner's explicit request. Its head was `c0d2746d76ff362bd18a9d1de30784ee375afa85`, the source of the existing build-141 (KodiAirPlay r11). No new IPA was requested.

Follow-up branch: `fix/build-141-followup`. Keep all subsequent fixes together in one draft PR targeting main, and tackle one bug at a time with the owner. This initial change records the baseline and log observations only; no runtime fix or device acceptance is claimed. Do not build/publish another IPA or merge this follow-up PR until the owner requests it. Changes matching the current build workflow paths can automatically build an IPA; use `[skip ci]` on follow-up commits while that instruction applies.

## Supplied startup log

The owner supplied a private Kodi log on 2026-11-04. Only this summary is published; the raw log, private paths and account state remain outside GitHub.

- SHA-256: `862e20942d59b8919f19fc7ee8de023119b63d37a937ca2fdf8b48bb113170e0`.
- Size: 43,577 bytes; 364 lines.
- Logged interval: 2026-11-04 06:13:33.288 through 06:13:39.083 (5.795 seconds; the log does not state a timezone).
- Platform: Kodi 21.3, iPhone17,1 (iPhone 16 Pro), iOS 27.0.1.
- Debug logging is disabled.
- Four explicit warning entries; zero error/fatal entries. Kodi also reports suppressed duplicate messages, so four is not a count of all underlying warning occurrences.
- Home.xml opens and Kodi reaches "Running the application"; Umbrella and CocoScrapers begin their service startup.
- No video playback, AirPlay session, download attempt or custom "Kodi iOS" diagnostic entries are present in this short capture.
- The log does not identify the IPA's build-N tag; build-141 is the code baseline, not a version independently established by this capture.

## Observations to investigate

These are log leads, not diagnosed user-facing bugs. No root cause or fix has been established.

| Lead | Line | Evidence | What it establishes |
| --- | --- | --- | --- |
| LOG-001 | 331 | Skin has invalid include: `skinvariables-homewidgets-standard-onunload` | A missing/unavailable include is referenced while Home loads. Its effect on navigation or widgets needs reproduction. |
| LOG-002 | 292 | `CActiveAE::StateMachine`: signal 0 from OutputControlPort not handled for state 7 | Audio engine warning during startup; no playback failure demonstrated. |
| LOG-003 | 358 | `DARWINIOS: underflow (7456 vs 8200 bytes)` | Audio underflow reported during startup; audible effect and cause unverified. |
| LOG-004 | 333 | JSONRPC could not parse `Setting.Details.SettingList` | The next messages defer/resolve type definitions and report successful JSONRPC v13.5.0 initialization. Not enough evidence to label an RPC failure. |

## Current focused bug — owner item 3

Latest source pass adds profile-5 RPU rendering with independent numerical pixel comparison, selected-language VobSub, and target-bounded/adaptive embedded subtitle preroll. The supplied log had embedded subtitles enabled; the previous preroll could continue until the next caption during a gap. 1,385 native checks and 35 Python/static checks pass; native candidate compilation and actual phone/Drive/TV acceptance remain separate pending gates. See [AirPlay investigation](AIRPLAY.md).

Latest follow-up bounds HTTP ranges and replaces nested retries with fresh connections sharing one read deadline. A one-second synthetic stalled-read budget returns in about 1.002 s versus 5.211 s with the previous reader; this is not measured phone seek speed. External SUP and IDX/SUB burn-in is now connected through app discovery and dedicated subtitle I/O, with real decoder/pixel/seek/video checks. Long Drive seek and sustained 4K phone acceptance remain open, alongside the documented embedded long-cue and Dolby profile-5 gaps. Final evidence/totals: [coverage validation](../reports/airplay-coverage-validation.json).

Owner requested proceeding with the gaps immediately. Compatibility source is now expanded: MP4 codec-aware routing, AV1 with dav1d software fallback/iOS hardware request, additional demuxers/decoders and audio bridges, HDR10/HLG tone/gamut mapping, and embedded bitmap subtitles. 1,248 native host checks plus 33 Python/static tests pass; real-format and pixel/seek coverage added. A small FFmpeg MOV accessor patch fixes open-GOP presentation-time planning without scanning the movie. Details and remaining limits: [AirPlay investigation](AIRPLAY.md), [new evidence](../reports/airplay-coverage-validation.json). Native Dolby profile-5 MP4 routing is preserved, while profile-5 conversion for incompatible receivers remains open. All changes require a new framework; r11 stays pinned.

ISSUE-093: AirPlay forward seeking usually stops playback; the screenshot records a new cancellation-error variant. New playback log confirms a Drive source (4K, 10-bit HEVC), VideoToolbox/GPU conversion and large source/queue stalls, including a 26.7-second seek before shutdown. Its final error is `session stopped`, not the screenshot's exact segment-37 cancellation.

Reproduced the cancellation/HTTP-500 defect on the host. Restrict cancellation to speculative work, fix stale worker ownership, prioritize foreground requests and separate cancellation from real errors. Also fix VP9+Opus files rejected before both converters could run, and reject unavailable video conversion instead of silently playing only audio. Add slow-request queue/production diagnostics.

1,095 native host checks plus 33 Python/static tests pass; actual 4K/10-bit structural seeking (six fps), AVI and WebM coverage added. Long Drive stalls and device acceptance remain open; the subsequent compatibility expansion is described above. See [compatibility and investigation](AIRPLAY.md) and [validation](../reports/airplay-seek-validation.json). No further log needed now to establish the cancellation defect. Published framework pin remains r11; a future requested IPA must first build/publish/verify/pin a new framework. No iOS/framework build, IPA, release or merge.

## Previous focused bug — owner item 2

ISSUE-092: selecting Movies and then Drama/Sci-Fi still opened TV discovery. Every category had a hardcoded `tmdb_type=tv`, independently of the working typed-search filter. Category actions now use the selected Movies/Shows type at click time, with the appropriate genre IDs: movie Sci-Fi/Fantasy uses 878 OR 14, Action/Adventure uses 28 OR 12, and War uses 10752. Shared IDs such as Drama 18 remain correct for both endpoints. Reality/Kids have no movie counterpart and are hidden for Movies; All retains its existing TV-category behavior. Typed-search code and result filtering are unchanged.

Search can also issue twelve background TMDb artwork lookups on first/stale visits. Reuse cached artwork immediately and defer each cosmetic request while downloads/uploads, a text query, playback, a dialog or another page is active; pace requests and honor shutdown. Reuse the existing download activity property, with no additional engine polling. An already-running RPC cannot be canceled. This is a targeted reduction in contention; the cause and resolution of all owner-reported multi-download lag remain unverified.

Validation: 143 host tests in 10 suites (including six new behavior regressions), generated XML and pinned Helper discovery translation checks (22 supported movie/TV routes). See [evidence](../reports/search-categories-validation.json). Device retest after a requested build: Movies → Drama/Sci-Fi, Shows → same categories, switching Movies/Shows repeatedly, and typed search with/without multiple active downloads. No IPA, merge or device-success claim.

## Previous focused bug — owner item 1

ISSUE-091: the owner confirmed the completed copy is in Google Drive / Library. Completed movies in Continue Watching must use their existing copy before provider selection; a title previously played through Umbrella must return to Umbrella when there is no completed copy.

Source implementation is ready for review: phone completed files (including current app folders despite stale settings), 100%-finished seeding files, then signed-in Drive copies. Failed checks do not mean "not downloaded"; unavailable saved providers and resolver retries do not silently start Elementum. Existing copies retain the correct TMDb Helper metadata object and preserve the original provider/version in history. Watch add-on version 1.4.2.

Validation: 140 affected tests in 12 host suites, including 19 new behavior regressions; the actual pinned helper resolver also passes local movie, episode and Drive metadata/path checks with Kodi API stubs. See [evidence](../reports/continue-watching-validation.json). The installed build-141 has not changed. No IPA or device acceptance claimed.

Future device retest after a requested build: completed phone movie, Drive-only completed movie, Umbrella-origin title, failed/absent download/provider checks, and expected resume position. No further reproduction is needed to implement the identified source fixes; phone results remain necessary for acceptance.

## Fix queue and verification

Owner selected startup warnings first, then slow opening-to-posters (not tab switching).

| Item | Current state |
| --- | --- |
| LOG-001 / ISSUE-085: empty widget unload include | Existing files and future generation repaired; host tests pass, device pending. |
| LOG-002 / ISSUE-086: duplicate audio INIT | Native source fix staged; three host C++ branch checks cover the native changes. iOS compilation/device pending; executable pin unchanged. |
| LOG-004 / ISSUE-087: schema dependency warning | Expected deferral uses DEBUG; genuine nondependency parse failures still warn. Native build/device pending. |
| LOG-003 / ISSUE-089: audio underflow | Open: genuine buffer shortage; warning preserved until its cause can be diagnosed. |
| ISSUE-090: bottom menu bar delayed ≥5 s | Lightweight native UI worker starts before setup imports/providers and requests display before the first polling wait; phone timing pending. |
| ISSUE-088: launch until posters appear | Repeated skin scanning reduced on host; timing instrumentation added; end-to-end phone performance unverified. |

See [validation evidence](../reports/startup-followup-validation.json), [performance findings](PERFORMANCE.md#startup-follow-up--2026-11-04), and the detailed ISSUE-085 through ISSUE-090 records. No IPA or native build was triggered.

For each bug, record reproduction, relevant evidence, diagnosis, focused change, appropriate host checks, device-test status and commit here and in docs/ISSUES.md as warranted. Preserve failures and distinguish host results from actual phone results.

Validation of this handoff: read the complete supplied log locally, checked PR #7's head/base and mergeability, inspected workflow triggers, verified the merge commit and existing build-141 provenance. No tests or builds were launched for this documentation-only setup.
