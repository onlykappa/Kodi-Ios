# Movie/TV provider fallback

Status: implementation in progress. Owner requested a draft PR and extensive desktop Kodi rig testing, 2026-11-15. No IPA or merge requested.

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
