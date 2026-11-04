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
