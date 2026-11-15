# Movie/TV provider fallback

Status: implementation and host/desktop rig validation complete; ready for draft review. Owner requested a draft PR and extensive desktop Kodi rig testing, 2026-11-15. No IPA or merge requested.

Base: current main `b54ce369da7d25d7440c29e58f9cc97fa8bafb0d`. Feature branch: `feature/source-provider-fallback`.

## Required behavior

- Preserve the current source provider and automatic picker's ranking, exact-title/episode checks, quality requirements and downloaded-first behavior.
- Search backups only after the active provider returns no usable source, fails or exceeds its deadline. Never treat user cancellation as permission to try another provider.
- Add Jacktook, POV/Magneto, The Crew, Otaku and Prism with their required source packages/dependencies. Otaku applies only to verified anime episodes. These are movie/TV fallback adapters, not extra home widgets, sports or live-TV entries.
- Resolve the selected candidate through its originating provider, then use the existing playback/download route. Empty, offline, unconfigured or unsupported providers must yield the next candidate without loops.
- Bound requests, attempts and cancellation. Keep authentication, source URLs and private rig artifacts outside Git. Log safe provider/status counts only.

## Work tracks

- Root: existing source-picker routing, fallback broker/worker, cancellation, identity/quality integration and draft PR.
- Adapter track A: Jacktook and POV/Magneto against real upstream APIs.
- Adapter track B: The Crew, Otaku and Prism against real upstream APIs.
- Packaging: immutable upstream pins and dependency closure, builder integration and archive checks.
- Rig: set up real Kodi 21.3, run deterministic provider-failure and success scenarios through the actual app path.

## Validation plan

Primary success with zero backup calls; primary empty/offline/timeout; each backup selected and resolved; multiple failures followed by recovery; all providers empty; missing account/provider package; strict movie/episode/quality rejection; duplicate releases; expired resolution; cancellation without further attempts; downloaded-first and Continue Watching retained. Test both movie and episode routes, background auto-source/season behavior, and existing picker regressions. Real Kodi evidence is recorded separately from host tests; neither proves iPhone/AirPlay behavior or all public endpoints' availability.

## Checkpoints

- Inspected fresh main and open PRs; main includes earlier PR #28. Another draft PR #31 exists for build-502 feedback and is not modified by this work.
- Integration and rig setup started. Findings, test failures and completed checks will be recorded here as they arrive.

## Resume checkpoint

- Agent turns stopped at an account usage limit; their saved files were retained.
- All five adapter modules, core fallback search/verification, isolated worker and packaging helper exist locally; eight new Python files pass AST parsing. This is syntax evidence only.
- Packaging builder edits are present but unvalidated. Automatic picker/no-results hooks and direct-HTTP download queue integration remain unfinished.
- A real user-space Debian Kodi 21.3 rig was brought up with build-513 add-ons; its embedded Python is 3.14, unlike the iPhone's 3.11. Provider routing scenarios have not yet run.
- Remaining: review adapters/worker cancellation and account defaults, complete application hooks and direct-download handling, wire packaging into CI, add focused regressions, run actual Kodi scenarios, then publish tested source to the draft. Draft currently contains the tracking document, not a completed integration.

- Resumed implementation: initial core policy regressions pass (11 cases: lazy success, offline/empty recovery, strict title/year/episode/quality, cancellation, deadlines, origin resolution, duplicate rejection and URL/header safety). These are host policy tests; real upstream and rig tests are still in progress.
- Corrected Otaku token key and read-through defaults so an explicit saved disabled account remains disabled. Added direct HTTP queue bridge and CI provider acquisition wiring; validation pending.

## Integration checks in progress

- Pinned provider packaging and required dependencies install successfully in a synthetic app staging tree, with no IPA produced. Existing builder tests pass with a newly installed user-space Python 3.11 interpreter.
- Core policy, direct HTTP copy queue, adapter and existing source-matching/Continue Watching suites are running on Python 3.11. One season-quality receipt regression was found and returned to the integration track for repair; it is not being waived.
- Review found and is addressing: cached sources losing their cached marker; stale automatic download ownership; decoded HTTP header injection; a filtered-out backup mistaken for cancellation; and fresh-install Otaku mapping availability.
- Worker validation now covers isolated dependency import paths, shared deadlines and interrupting abandoned network reads. Real Kodi scenario testing is still underway; review readiness is not claimed.

## Final review checkpoint

- Implemented fallback routing and pinned26add-on dependency graph, Prism provider package and Otaku public mapping asset. The Crew artwork restored after real imports proved it required.
- 431 tests across 21 focused/regression suites pass on Python3.11. Real Kodi21.3 desktop rig:17/17 scenarios pass, including actual primary/empty-primary automatic picker, all5adapters, resolver404 recovery, cancel/deadline, strict identity/quality and mapped anime original queue coordinates.
- Fixed failures found: missing Crew artwork, worker argument/plugin handle mismatch, dependency path/calendar shadowing, canceled primary starting backups, rejected backups mistaken for cancel, stale queue ownership, cached-source markers, anime coordinate mapping and unsupported raw-magnet Stream routing.
- Evidence and limitations: reports/provider-fallback-validation.json; usage/reproduction: docs/PROVIDER-FALLBACK.md. No live-account/iPhone/AirPlay verification, IPA, release or main merge.
