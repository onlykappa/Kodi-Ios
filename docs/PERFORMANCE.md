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

## Listing cache (build-137)

Owner, build-136: the preloader is back (every Home, Movies and TV row loads when Home opens), but the rows still take
5-10 s at every launch. Build-136 log: Kodi starts 07:37:04.5, Home 07:37:05.0, Python (services and plugins) from
~07:37:07.1, TMDb Helper busy until ~07:37:10.4; each row is a TMDb Helper run of 2-3 s on the phone, ~36 at once.

**Design.** A native app shows its last feed at once and refreshes it behind the scenes. Here:

1. **Copies.** The bootstrap service keeps a JSON copy of every TMDb Helper hub row and hero in
   `addon_data/plugin.video.kodi.ios.watch/listings/<key>.json` (`r` + 15 hex of the path's SHA-1; heroes
   `hero.<spotlight id>`). It makes them with `Files.GetDirectory` **from the service thread**, one list at a time,
   never during video, starting 20 s after the service starts (`portrait.REFRESH_AFTER`), then every 10 min for copies
   older than 3 h (`ios_cache.MAX_AGE`). Each copy is written to a temporary file, renamed, then read back.
   `customproperties` (JSON-RPC 13.5) brings TMDb Helper's own properties (`isplayable`, `tmdb_id`, `item.*`...) and
   its long-press entries (`contextmenulabel(n)` / `contextmenuaction(n)`), so taps and long presses are unchanged.
2. **Flags.** Only after a copy reads back does the service turn the row's flag on: `Skin.SetBool(PortraitCache.<key>)`,
   or for a hero `Skin.SetString(PortraitCache.hero.<id>,"<path the copy was made from>")`. Kodi saves skin settings,
   so the next launch knows at once.
3. **Skin choice without Python.** Each TMDb Helper row and hero is an Includes.xml variable
   (`portrait.cached_content`): `plugin://plugin.video.kodi.ios.watch/?action=cached&key=<key>` when
   `Skin.HasSetting(PortraitCache.<key>) + System.AddonIsEnabled(plugin.video.kodi.ios.watch)` (heroes:
   `String.IsEqual(Skin.String(PortraitCache.hero.<id>),Skin.String(HomeSwitcher.<id>.Spotlight.Path))`), else the
   real TMDb Helper path. Continue Watching, library and other add-on rows keep their path.
4. **The cached route only reads.** `ios_cache.serve` reads the copy and lists it: no JSON-RPC, no TMDb Helper, no
   network. Build-134's attempt ran `Files.GetDirectory` inside the plugin and asked for a field Kodi 21 does not have
   (`tvshowtitle`, refused with "Invalid params"), so every row came back empty and nothing was logged; both are gone.

**Failure modes** (none can leave Home blank for more than one live TMDb Helper run of the affected row):

| Situation | What happens |
|---|---|
| No copy yet (first launch after the update, a new row) | Flag off: the row loads TMDb Helper as before. The service fills it later; that row reloads once from its copy (same titles). |
| Copy deleted or damaged while its flag is on | The route lists nothing, runs `Skin.Reset(PortraitCache.<key>)` and logs a warning; the variable switches and Kodi loads the TMDb Helper path. The service's start check turns such flags off as well (~2 s after start on the phone). In a hidden hub the switch happens when that hub is shown (see below). |
| Any error inside the route | Same as above (default.py catches everything, resets the flag, ends the directory). |
| Skin settings lost (app killed before Kodi saved them) | Flags off: live rows. The start check turns flags back on for good copies. |
| Watch plugin missing or disabled | `System.AddonIsEnabled` is false: live rows. |
| Service not running (crash, other skin) | Copies age; the route refuses copies older than 3 days (`ios_cache.KEEP`): live rows. |
| TMDb Helper fails or returns nothing (offline, Trakt not signed in) | The old copy stays; an empty list never becomes a copy (unauthorised Trakt rows stay live, as before). |
| Hero spotlight changed in the skin settings | The flag string no longer equals the spotlight path: live hero at once; the service makes a new copy. |
| Widget lists changed | New Home.xml/Includes.xml (skin reload as before); new rows have new keys, so no flag: live until filled. |
| Copy refreshed during a session | Rows already showing the copy keep it until the next launch (stale-while-revalidate). |
| `Files.GetDirectory` never returns (rig: a TMDb Helper Trakt list answered 401 and exited without `endOfDirectory`; Kodi's call hung for good) | Each fetch runs on its own thread with a 90 s limit (`portrait.bounded`); on timeout the list is marked stuck in `listings/stuck.txt` (skipped for a day) and the refresh stops for the session. Rows keep what their flags say. |

**Hidden hubs and the preloader (checked in Kodi's source).** Movies and TV are groups hidden by `Portrait.Tab`.
`CGUIControlGroup::Process` (children's `UpdateVisibility`) does not run for a hidden group, and
`CGUIBaseContainer::UpdateVisibility` returns early for a hidden control that cannot focus, but
`CGUIBaseContainer::AllocResources` calls `UpdateListProvider(true)` for every container when Home opens, so every row
of every hub starts loading at once (the preloader works) and its items are taken in the first frame the hub shows.
A variable whose value changes while its hub is hidden (a flag set by the service, or reset by the route) is noticed
only when that hub shows: that row then reloads (cached route: a fraction of a second; live: one TMDb Helper run).

**Desktop rig (2026-11-03, Kodi 21.3 Flathub, warm TMDb Helper cache; not iPhone timings).** Seconds after Home
opens until the list has items (`/tmp` measuring script around the same JSON-RPC polls as `perf_rig_bench.py`; the
bench itself crashed at start on every run that day, a known Python 3.14 problem of the rig):

| | hero | Home rows 1-3 | Movies / TV tab | TMDb Helper runs in 25 s |
|---|---|---|---|---|
| Preloader, live (build-136 code) | 0.87-1.02 | 0.87-1.84 | 0.15-0.31 / 0.09-0.10 | 27-29 |
| This build, no copies yet | 1.06 | 0.98-1.38 | 0.15 / 0.09 | 28 |
| This build, copies and flags (10 lists cached) | 0.29 | 0.23-0.68 | 0.14 / 0.14 | 14 (the uncached rows) |
| Hero and two rows' copies deleted/damaged | 4.89 (live) | 4.89-4.95 live, 0.66 cached | 0.25 / 0.11 | 20 |

In the last run the route logged "no copy for ..." and turned the three flags off (saved in the skin's settings.xml),
and Kodi loaded those lists from TMDb Helper; they came late only because they queued behind the other live rows.
Tab switches stay at ~0.1-0.3 s (script round trip included): the hidden hubs are preloaded. Skin flags were saved to
`addon_data/skin.arctic.fuse.3/settings.xml` at once (ids lowercased by Kodi; `Skin.HasSetting` ignores case).

**Expected on the phone (not measured there).** Python itself starts ~2 s after Home (build-136 log), and the cached
route is a Python plugin too, so rows cannot appear before then. From the second launch on, each row is a light plugin
run (read one JSON file) instead of a 2-3 s TMDb Helper run, and no TMDb Helper run happens at start at all: Home,
Movies and TV should be filled within about a second of Python starting, instead of ~3-5 s later. The background fill
costs one TMDb Helper run at a time (about 36 on the first launch, then only lists older than 3 h).

Guard rails: `scripts/test_listing_cache.py` (in CI) and `test_performance_budget.py`
(`test_preloader_every_hub_row_loads_when_home_opens`).
