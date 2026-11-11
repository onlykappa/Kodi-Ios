# PR #16 review handoff

Branch: `claude/trusting-euler-kgug98`. Owner explicitly holds the IPA and requests committing completed work now.
No main merge, IPA dispatch/publication or native pin change. Last delivered test app remains IPA 223 (r28/r44).

## Included

- Full season offers verified full-season-labelled packs, excluding single/partial-episode results. Cancel ends
  that interaction. Without a pack, inspect aired, unowned/unqueued episodes before showing quality choices.
- Only actual usable qualities appear, with episode coverage. No 4K option without usable 4K results. Selecting
  a quality queues individual episodes strictly at that quality; missing episodes persist for later opening checks.
- Scoped request IDs, cancellation guards and actual cloud queue receipts prevent scans/selected sources from
  being counted as downloads. Explicit back-catalogue plans remain separate from the future-release date floor.
  Manual batches defer the opening watcher. Keyboard busy detection uses Kodi's valid virtualkeyboard name.
- Library status shows saved pre-transfer/paused jobs and remaining Drive jobs. Refresh/Queue reread durable jobs
  and pause controls immediately, preserving published non-transfer progress/reorder freshness. Job identity stays
  stable when transfer details first appear. Resume/cancel use the owning transfer controls.
- New manual downloads while uploads are paused offer explicit resume or keep-queued choices. Quiet automation
  preserves the pause. Queue-save/source-scan diagnostics contain safe state/counts, not source URLs or credentials.
- Queue lists downloads once, includes all Drive pages, renders real Previous/More buttons, disables them at page
  boundaries, and labels transfer-only navigation View queue. Existing layout helpers, fonts and colours reused.
- Native Browse for subtitle guard: do not initialize its file picker from an HTTP(S) movie URL. A controlled slow
  parent-folder request reproduced the freeze; the rebuilt desktop engine opens the browser without that request.
  The complete patch applies to the pinned Kodi upstream. This guard is source-only until a new iOS build/pin.

## Still to do / deliberately left out

1. **Phony empty downloaded-show page.** Grid discovery lists Drive folders even when no playable episode exists.
   This explains the poster/empty page versus status mismatch. The unfinished empty-page UI/CTA changes were
   removed from the commit. In the rig its properties were present, but the header did not render correctly.
   Inspect `drivelibrary.shows`, `ios_library._directory` and `portrait.show_header`/the show grouplist. Avoid adding
   slow per-folder network scans to the foreground UI. Queue visibility fixes above remain included.
2. **AirPlay captions and five-second Media Assistant/Umbrella stall.** Owner confirms Download subtitle and phone
   captions work. Latest provided logs do not contain the corresponding TV session. Need a fresh post-failure log
   and whether captions were enabled before handoff or while TV playback was already active. Do not claim Wi-Fi,
   subtitle-service failure or a fixed receiver path from current evidence.
3. **Final UI smoke tests:** recheck actual Queue pagination after final boundary-state changes, Refresh after a
   newly saved job, per-job resume/cancel, genuine full-pack selection and picker cancellation. Unit/controller/XML
   cases pass; the owner stopped remaining work before all final desktop checks. Empty-show UI is not included.
4. **New iOS Kodi build:** compile, independently verify and pin a new executable before the next authorized IPA
   so the Browse guard is actually present. r28/r44 currently remain pinned. Do not package the old executable and
   describe the guard as delivered. Full packaging/native checks and actual iPhone/Roku/provider acceptance follow
   only when authorized; no new IPA requested now.

## Evidence and local workspace

`reports/season-source-queue-checks.json` records test counts, actual desktop cases and limitations. The related
Python suites pass, as do 46 actual C++ gesture/slider/info-refresh scenarios. The full portrait suite passed
before the final Queue fragment edits; affected generated XML/controller tests pass afterward.

Private evidence stays outside Git under `/workspace/scratch/season-fallback`. Controlled fixtures and images:
`rig/season-1080-only-result.json`, `rig/season-mixed-result.json`, `rig/shots/`, plus build/test logs. Kodi upstream
is `a3a448d26b8d560a65655dab2cd122994dc4e146`; add-ons are from verified IPA 223. Provider replies/account checks are
controlled fixtures; actual Kodi UI, source filtering, redirect interception and durable queue code run. This is
not evidence of live provider availability, real transfers or Roku playback.

The excluded empty-show patch is `/workspace/scratch/season-fallback/unfinished-empty-show.patch`. The rig contains
that experimental overlay, so sync/reprepare from the final branch before collecting new final UI evidence. Docker
container `kodi-season-rig` ended with exit 255, OOM=false; its stop was not diagnosed after the handoff request.
Do not restart this whole task or treat that stopped rig as completed device verification.

Setup/verification failures are retained in ISSUES: disk-full dependency install, initial raw-state refresh
regressions, account/provider fixture setup issues, duplicate Queue rows, absent pagination controls, and native
patch context whitespace corrected before full patch validation. No owner account/media was used for testing.
