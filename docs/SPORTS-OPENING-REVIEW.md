# Sports opening review — 2026-11-18

Fresh follow-up to PR46; a runtime loader candidate is now wired in this PR.
Owner phone report says Sports playback works, but Crew's root and progress
dialog appear during opening. The supplied log shows ESPN1live/82upcoming in
1.32s, first matched game about12s after discovery began, Crew handoff at
15:21:59.007, media open at15:22:12.235 (13.228s later), first H.264 codec
at15:22:13.338. Another media open/codec event occurs nearby; do not infer
distinct successful games or assign the full wait to a single operation.

Source review confirms the opening-via-Crew log occurs after refresh_link,
so the13.228s gap is after app menu refresh, in native resolver/opening work.
Sports closes at15:21:54.909 and dispatch logs at15:21:59.007:4.098s includes
script startup and preparation, not solely menu network time. Two media opens
have different addresses, so duplicate playback cannot be concluded from
their proximity. Added safe per-folder refresh duration/entry-count diagnostics.
The log does not separate native provider resolution, user
selection and source network time. Measure those phases before promising a
speed improvement. Do not skip ancestry refresh blindly: Crew clears resolver
cache at league roots, and prior stale expressions failed to play.

## Existing UI and proposed reuse

`pages.py` already generates a video-opening DialogBusy card using
`IOSOpen.Title/Source/Stage/Slow`, a thin moving bar and Cancel. Sports native
handoff does not yet provide a complete Sports-owned opening presentation.
Reuse its tokens/helpers with Sports-specific observed stages, not movie/file
wording or fake percentages. [Interactive mockup](design/sports-opening-mockup.html)
is a proposal, not Kodi implementation or device evidence. Browser and rig
visual validation remain pending; no design approval is inferred.

## Next implementation and acceptance

1. Instrument monotonic preparation, native dispatch, chooser wait and actual
   AV startup separately with no private routes/headers. Establish a baseline
   over multiple real openings; distinguish cold from warm.
2. Test a Sports-owned opaque background/progress surface while Crew remains
   the native container underneath. Preserve normal add-on identity. Do not
   hide necessary source/quality choices or cancel/error dialogs. A modal
   overlay can reproduce the historical blocked-picker problem; validate the
   window ownership/z-order before implementing blanket dialog suppression.
3. Close the opening surface on real AV startup, failure, cancellation or
   ownership replacement. Cancel must stop this opening and prevent fallback
   from starting afterward. Bound waits and expose retry/manual source choice.
4. Optimize only measured app overhead: avoid redundant refresh where a valid
   owned resolver context is proved; serialize native access safely. Do not
   promise removal of provider/network latency or disable authorization.
5. Test direct source, nested choice, error, timeout, Cancel/Stop, replacement,
   cold/warm opening and no flashing Crew root. Use actual portrait rig renders
   and real source taps as well as deterministic fixtures; phone verification
   remains separate. Follow mandatory UI policy and register any new tests.

This branch is separate from the already-dispatched AirPlay testing IPA588;
this mockup/review is not included in that build. No new IPA or merge here.

## Implemented candidate checkpoint

`sports_opening.py` opens the generated Kodi surface before native dispatch,
waits for onInit, updates elapsed seconds and observed preparation wording,
and closes on AV-start, cancellation, timeout or ownership replacement.
It reports no fabricated percentage/throughput. Cancel only stops the owned
opening and invalidates that request. The page is generated with portrait
helpers and participates in the skin refresh hash. Five lifecycle unit cases,
53 Crew,23 Jet,22 Live and20 Game tests pass. Actual portrait rig rendered the
page with a controlled matchup; pressing Cancel changed window13001 to Home.
Early rig attempts hit Kodi's XML directory cache; retry after listing the
skin folder succeeded. This is controlled loader evidence, not a completed
real stream handoff. Native Crew chooser interaction, actual AV-start close,
error/replacement/timeout rendering and full workflow/UI tests remain pending.
Rig screenshots stay outside Git. This candidate is not ready for IPA retest.
