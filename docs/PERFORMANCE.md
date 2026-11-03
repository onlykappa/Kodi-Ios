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

## Listing cache (build-134)

Owner, build-133: "startup is extremely slow every time; menus always say Loading; the preloader no longer works".
The lazy hubs above cut how many lists start together, but every row was still a TMDb Helper list: one Python run of
TMDb Helper per row, a few seconds each on the phone, queued one behind another, at **every** launch and on the first
visit of Movies and TV. Nothing was kept between launches, so the first view of every menu always waited.

Design (stale-while-revalidate, like a native app's feed cache):

1. **Cached route.** Each TMDb Helper row and each hub hero is now
   `plugin://plugin.video.kodi.ios.watch/?action=cached&url=<TMDb Helper path>` (portrait.py `cached()` /
   `spotlight_path()`, the plugin's `resources/lib/ios_cache.py`). The watch plugin is small (no TMDb Helper import,
   no network); with a copy in `addon_data/plugin.video.kodi.ios.watch/listings/<sha1>.json` it lists it at once.
   The row path is URL-encoded and last; the hero's comes raw from the skin string (`url=` is read as everything after
   it), and a hero that is not a TMDb Helper list (library, other add-on) is passed through live and never stored.
2. **First visit of a row** (no copy yet, i.e. once after the update): the plugin runs the real list once through
   `Files.GetDirectory` (the same TMDb Helper run as before), shows it and keeps it.
3. **Refresh in the background, one at a time.** The bootstrap service (portrait.py `listing_refresher`) waits
   `REFRESH_AFTER` (30 s: past Home's rows and the Movies/TV prefetch), then refreshes copies older than
   `MAX_AGE` (3 h) and fills rows never visited, serially with a 2 s pause: never several TMDb Helper runs at start.
   A failed refresh keeps the old copy. The new titles show on the next visit of the row / next launch.
4. **Preloading restored.** Movies and TV prefetch at 4 s and 7 s after Home (were 6 s / 10 s); with the cache that
   is a cheap plugin run per row, so the first tab switch shows filled rows.

Taps are unchanged: each item keeps the TMDb Helper path and its folder/playable kind (IsPlayable), mediatype (the
hero's Play reads DBType), art, title, year, genre, rating, plot, MPAA, uniqueids and tmdb_id/tmdb_type properties.
Not kept: item-specific context-menu entries TMDb Helper adds per item (its add-on wide entries keyed on
`ListItem.Property(tmdb_type)` still apply). No skin reload at start; the generated Home.xml changes once with this
build (one refresh, as for any portrait.py change).

Expected on the phone (not measured there yet): from the second launch on, every hub row filled in roughly one light
plugin start each instead of a TMDb Helper run each; Movies/TV filled before the first tab switch.
Guard rails: `scripts/test_listing_cache.py`, `test_performance_budget.py`
(`test_hub_rows_answer_from_the_listing_cache`, `test_movies_and_tv_prefetched_early_and_cache_refreshed_one_at_a_time_after_start`).
