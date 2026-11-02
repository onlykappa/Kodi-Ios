# Performance pass (2026-11-02)

Desktop rig figures (Kodi 21.3 from Flathub, x86, software GL, at the iPhone 16 Pro portrait safe area 603x1167),
measured with `scripts/perf_rig_bench.py`. They compare builds with each other; they are **not** iPhone timings.
iPhone facts come from the owner's build-124 log (iPhone17,1, iOS 27.0.1).

## Bottlenecks found

1. **All three hubs loaded at every start.** Home.xml holds Home, Movies and TV; every row (36 add-on lists, each a
   new Python run of TMDb Helper) was marked to load while hidden. On the phone they queued one behind another and the
   hero sat on "Loading...".
2. **Fuse code under the launcher.** Fuse's startup script ran at every launch (~60 skin settings rewritten, a blurred
   background made with TMDb Helper, a fixed one-second wait); its splash script and helpers ran at every Home open,
   including each switch back from Library or Search; skin settings were rewritten (guisettings.xml saved) each time.
3. **Two tab bars.** The skin's bar appeared whenever the native glass bar hid (dialogs, page changes).
4. **Elementum engine off for good** after two app ends during its start (the crash guard never reset its marker):
   downloads and "open with Elementum" did nothing until "Retry Elementum engine" (owner log: engine started 80 s late).
5. **Service order and duplicates.** Tab bar and Continue Watching waited a fixed 10 s (glass bar ~19 s after launch);
   Elementum's folders were fixed twice per start (two engine reloads); bell and keep-alive polled the engine
   separately; focused-item details asked every 0.5 s; Kodi's version check service ran.

## Measurements (desktop rig, warm cache unless noted)

| | before (main) | after |
|---|---|---|
| Launch to Home | 8.3 s | 6.9-7.0 s |
| Hero filled, cold cache | 17.2 s | 6.0-9.6 s |
| First open of Movies/TV | 0.1-0.2 s (all preloaded) | 0.6-0.9 s (background prefetch not yet effective) |
| Hero filled, warm | 0.8-0.9 s | 0.9-1.1 s |
| Add-on runs at start | 33 (69 with prompts) | 10 |
| Resident memory | ~490 MB | ~415 MB |
| Idle CPU on Home | 4 % | 4-5 % |

Not measured on a phone. The rig's Kodi (Python 3.14) crashes now and then when several add-ons start together
(Kodi 21 supports Python up to 3.11, the phone's); the benchmark records such runs as crashed and skips them.

## Guard rails

`scripts/test_performance_budget.py` (in CI) fails if any of the five bottlenecks returns; all of its tests fail on the
code before this pass. Each change is a separate, revertible piece (portrait.py lazy load and Startup, glassbar.py,
service.py order, build_customized_ipa.py guard). The last known-good build is build-124.
