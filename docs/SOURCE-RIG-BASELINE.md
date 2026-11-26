# Source resilience step 2 — isolated desktop baseline

2026-11-23; runtime source commit 7e45dc6 (provider code inherited from main cf42c63).
Sanitized results: [source-rig-baseline.json](../reports/source-rig-baseline.json).

## What ran

A separate clean profile at `/workspace/scratch/source-resilience-rig` uses the cached
Debian Kodi **21.3**, revision 20261023-nogitfound, embedded Python **3.14.10**. The
executable is launched through `/home/agent/.cache/kodi-rig/kodi-build/kodi-x11`, using
its existing private dependency prefix. JSON-RPC confirmed the exact running version.
The old container has Kodi 21.2 and was not used for test evidence. No rebuild or IPA.

The prior container and profiles remain preserved. A local container-image clone
failed for lack of disk space; only our newly created asset copies were replaced with
read-only-use symlinks to existing image/font resources to reduce storage. No old
profile, database, account settings, media or cached source results were copied.
Pure Python provider trees came from existing staged inputs; the report records
actual installed versions. Compared with step 1's hash-verified archives, Crew plugin
Python files match, 234 Crew-module Python files match (9 adult-only files absent by
existing policy), and 318 ResolveURL Python files match. No mismatching Python files
were found in those comparisons; that is not verification of all staged add-ons.

Current bootstrap and picker code were copied from this checkout. Startup services
are disabled in the private rig, including Crew's service, so fixture tests own their
state. This differs from normal iPhone packaging and does not test Sports' proxy.

Arctic Fuse 3 is active, generated portrait files refreshed by kodi_rig.sync,
iOS skin conditions forced only in this profile, reference resolution 1080x2090,
Xvfb :17 at 603x1167. These are rig configuration facts, not visual acceptance.
The existing helper attempted screenshots on :5 and failed; no screenshots from
those attempts are evidence. Future screenshots must target :17 explicitly.
Native iOS tab bars, fonts, touch, receiver/AirPlay and iOS native frameworks are absent.
ALSA uses a private null sink: decoding/clock behavior can be tested, audible sound cannot.
PIL 5.1.0 is supplied by Kodi's system add-ons, despite being absent from the copied
profile add-ons. The initial preparation report's missing-PIL entry was checked and
resolved by Addons.GetAddonDetails, not by inventing a dependency stub.

## Results

All 13 distinct fixture scenarios passed after the documented rig repair:

- Primary picker accepts index 0 without querying backup workers.
- Cancel picker returns -1.
- Provider failure -> empty provider -> Prism fallback selects/resolves one result.
- Search cancellation and total timeout terminate with zero job mailboxes left.
- Jacktook, POV, Prism, Crew and Otaku adapters import their installed upstream modules
  and pass controlled search/resolve responses through production adapters/workers.
- Strict matching rejects wrong-title/episode/quality fixture candidates.
- Empty sources remain empty.
- A rejected resolver fixture advances to another source.

The harness replaces upstream search/resolve replies after importing genuine modules.
This validates integration against controlled interfaces, NOT live scraper parsing,
remote availability, valid accounts, independent source discovery or native engine operation.
The controlled HTTP endpoint in existing adapter tests does not deliver a real movie.

A separate private playback probe opened the actual production picker for the same
synthetic episode, accepted index 0, then explicitly handed a generated H.264/AAC
local MP4 to xbmc.Player. Kodi reported video playback and times advanced from
0.102 to 2.171 seconds, then Stop left no active playback. This proves picker selection
and actual VideoPlayer start/clock/stop in the harness. It is NOT proof that the full
production primary provider/Elementum handoff works; the harness supplies the final
local fixture path. Playback probe and fixture hashes are recorded in the report.

## Failure retained: Crew artwork

The initial adapter batch passed 7/8: Crew failed importing sources because
`script.thecrew.artwork` was not installed. The old staged Crew manifest omits that
dependency although Crew's runtime imports still reference it. Current repository lock
already includes artwork 3.2.0. The rig fetched that exact archive, verified its SHA256,
installed/enabled it and reran the Crew fixture: 1/1 passed. No production packaging
change was made. Inspect clean current build staging in step 3 rather than infer that
this old staging problem also affects the current phone IPA. See ISSUE-398.

Other setup failures retained in the JSON report: full disk during container cloning;
first profile's bootstrap-enable prompt; null audio sink setup; process lifetime/stale
private display lock on restart; wrong display in optional screenshot helper.

## Reproduce / continue safely

Use scripts/kodi_rig.py and docs/design/KODI-RIG.md. Do not run `prepare` against a
preserved profile. This rig's Kodi/Xvfb PIDs and startup scripts are private scratch
artifacts; use those exact PIDs if stopping it, not a global Kodi kill command.
The test commands were:

```
KODI_RIG_HOME=/workspace/scratch/source-resilience-rig python3 -B scripts/rig_provider_fallback.py primary-picker cancel-picker chain cancel timeout
KODI_RIG_HOME=/workspace/scratch/source-resilience-rig python3 -B scripts/rig_provider_fallback.py adapter:jacktook adapter:pov adapter:prism adapter:thecrew adapter:otaku strict empty resolver-offline
KODI_RIG_HOME=/workspace/scratch/source-resilience-rig python3 -B scripts/rig_provider_fallback.py adapter:thecrew
```

Before each rerun archive private reports: the harness overwrites its summary and
per-case results. Original selection and failed adapter batches were retained privately.
Playback probe uses generated ffmpeg testsrc2 320x180/24 fps plus sine audio, 30 seconds,
libx264 ultrafast/yuv420p and AAC. It runs as a private RunScript, invokes deck.run,
then plays the local fixture, waits for >2 seconds of advancing time, stops and checks
isPlaying false. Both probe source and generated media remain outside Git.

No live sources or owner accounts were contacted by test methods. Genuine module
imports may initialize optional upstream behavior; no outbound packet capture was
performed, so do not claim this rig was network-isolated. New outage testing needs
explicit controlled network instrumentation in later steps.

## Exit and remaining gaps

Step 2's isolated controlled baseline is complete. No production fix or implementation
of independent search was attempted. Step 3 is source/dependency preservation and
clean restore validation. Complete Umbrella source, phone versions, actual iOS
Elementum playback, ordinary Crew startup service, live remote content and portrait
visual acceptance remain separate unproven items. Passing baseline fixtures does not
close those gaps or authorize release/IPA/merge.
