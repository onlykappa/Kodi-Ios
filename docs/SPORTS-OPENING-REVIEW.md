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

## Critical review checkpoint (2026-11-19)

Reviewed the candidate against the ten open questions rather than accepting
passing tests as proof of correct wiring. Findings so far:

1. **Build-breaking defect, fixed.** `sports_opening_page.py` does
   `import pages`, but `portrait.py` loads every sibling module through
   `importlib.util.spec_from_file_location`/`exec_module` into local
   variables only; `pages` was never registered in `sys.modules` (unlike
   `sports_page`, which already had the precedented
   `sys.modules.setdefault('sports_page', sports_page)` opt-in because
   `sports_live_page` imports it by name). Reproduced deterministically in a
   clean environment (`env -i ... python3 -B -c "import portrait"`):
   `ModuleNotFoundError: No module named 'pages'` at `sports_opening_page.py`
   line 3. Both the real IPA build path (`scripts/ios_portrait.py`) and the
   desktop rig sync (`scripts/kodi_rig.py sync`) load `portrait.py` the same
   bare way and neither puts `resources/lib` on `sys.path`, so this broke
   the whole skin build, not only the Sports opening page. This is very
   likely the unexplained "XML File for Window is missing" rig failure
   referenced earlier. Fixed by adding the same `sys.modules.setdefault`
   opt-in for `pages`. Re-verified clean import and a clean
   `kodi_rig.py sync` ("synced 292 portrait files") after the fix.
2. **Regression in an existing covered test, fixed.** This PR made the
   native play path (`sports_jet.run_script`) unconditionally construct and
   `.open()` a real `xbmcgui.WindowXMLDialog` before calling `play()`.
   `scripts/test_sports_loop_router.py::test_native_script_does_not_replace_the_addon_constructor`
   stubs `xbmcgui` with an empty namespace and was never updated for the new
   step, so `opening.open()` raised inside the new code and `play()` was
   never reached (confirmed by reverting only the uncommitted fixes: the
   failure already existed on `b99d6ba` as submitted). Fixed by stubbing
   `sports_opening.Opening` in that one test so it still exercises its
   original intent (no addon-constructor replacement on the native path,
   `play()` called once).
3. **Review question 1 (window blocking), answered empirically, favorable.**
   Built a rig probe (`zorder_probe.py`, kept out of Git) that opens the
   real `Surface` class exactly as `sports_opening.py` does
   (`WindowXMLDialog(...).show()`), then creates a genuine
   `xbmcgui.DialogProgress()` carrying the same title/text Crew's
   `control.py`/`sources.py` use during a scraper search
   ("The Crew" / "Searching source N of 6"), confirmed by direct
   inspection of the pinned Crew add-on's source. Screenshot (desktop Kodi
   rig, controlled fixture, not device/not real Crew) shows the
   `DialogProgress` rendered on top of, and distinct from, the Sports
   Surface; the logged `xbmcgui.getCurrentWindowDialogId()` changed from
   `13001` (the Surface) to `10101` (the built-in progress dialog) once it
   was created, and stayed `10101` for the life of that dialog. This is one
   controlled observation of one native dialog type, not a proof covering
   every Crew dialog/selector Crew might show; it supports, but does not by
   itself fully settle, that the Surface (shown non-modally via `.show()`)
   does not sit above or capture input ahead of a genuine Kodi dialog.
   Separately, by design this PR's flow never activates Crew's own
   container/navigator window at all for `TheCrewRoute`: `refresh_link()`
   resolves a leaf file URL in-process and `xbmc.Player().play(file)` is
   called directly, so the historical ISSUE-369/370 failure mode (Crew's
   *container* window refusing to activate beneath an already-shown Sports
   modal) does not apply to this candidate's current route; only Crew's own
   dialogs (e.g. its scraper-search progress dialog) can appear during
   opening, and those were shown to render correctly on top.
4. **Stale/late `onAVStarted` callback risk (review question 4), partially
   mitigated.** `xbmc.Player` callbacks are dispatched to every live
   `Player` subclass instance for any playback in the app, not scoped to the
   instance that issued `play()`. A previous `Opening`'s `Observer` staying
   alive slightly past that opening's own close (normal Python GC timing)
   could in principle receive an `onAVStarted` meant for a different,
   unrelated later playback and call `started.set()` on an Opening that no
   longer owns the native playback. Added an ownership check inside
   `onAVStarted` matching the one `tick()` already does, and clear
   `self.observer` in `close()` so an already-closed Opening's Observer is
   released for garbage collection promptly instead of lingering. This
   narrows, but does not provably eliminate, the window, since Kodi's
   addon API does not expose a way to scope a `Player` callback to a single
   `play()` call. No other code path in this app calls `xbmc.Player().play()`
   concurrently with an open Sports loader in normal use, which limits the
   practical exposure.
5. New unit tests added (`scripts/test_sports_opening.py`, 9 total, up from
   5): long team-name matchup, malformed/empty `native_queue` descriptors,
   observer dropped on close, and a late ownership-mismatched callback not
   setting `started`. These remain pure logic tests of `Opening` (fakes for
   `home`/`window`); they do not exercise real Kodi XML generation or
   layout, consistent with the standing caution that passing tests are not
   proof of correct GUI wiring.

**Still outstanding, not yet done:** reviewing questions 2 (init/dispatch
ordering deeper than the existing 5s wait), 3 beyond the existing
cancel/ownership unit tests, 5 (app-shutdown path specifically), 6 (Kodi's
own thread-safety guarantee for `WindowXMLDialog.setProperty` from a
background thread — not independently verified, only consistent with
common addon practice), 7 beyond the new malformed/long-name tests
(repeated openings in sequence), 8 (confirmed by reading: `stage()` is
unconditional once not closed, so it can still overwrite the 10s
"taking longer than usual" text with real stage info afterward — not yet
confirmed against the actual call order from a live `sports_jet.py` run),
9 (cold-install robustness beyond the `pages` bug specifically), and 10
(pixel comparison against the approved mockup). No real Crew source has
been played end-to-end through this loader in this review pass; no native
Crew chooser interaction with a live provider has been exercised; no
before/after timing measurement has been taken. None of this is claimed as
done. This candidate remains not ready for IPA retest.
