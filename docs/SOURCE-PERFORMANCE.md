# Performance and the existing UI in Kodi (roadmap step 14)

Evidence class: **desktop Kodi 21.3 rig plus host measurements, 2026-11-26, from one cloud container**. Not the iPhone. Public sites and TMDb were live at that moment; nothing was downloaded; no account or key was used. Numbers: `reports/source-resilience-performance.json`. Scripts: `scripts/rig_backup_playback.py`, `scripts/rig_tmdb_films.py`, `scripts/measure_backup.py`. Screenshots stay in the rig folder (they show film artwork) and are not in Git.

## 1. Action to player, in real Kodi (no key, no account)
Each case runs through the repository's own `Playback`, `fresh_resolve` and `KodiPlayer` inside Kodi (RunScript), then reads the player clock and stops it. "Seconds" is from the start call until one second of picture has played (it includes resolving, checking the playlist chain and Kodi opening the stream).

| Case | Result | Seconds | Clock advanced, then stopped cleanly |
| --- | --- | --- | --- |
| Plain mp4 behind a required header | playing | 6.3 | yes |
| HLS behind a required header and a cookie (master, variant, segment) | playing | 6.6 | yes |
| The same HLS without the header | refused (typed) | - | not started |
| Real internet HLS test stream (Big Buck Bunny, no key) | playing | 9.7 | yes |
| Torrent: hash verified against a generated .torrent, fetched from a loopback seed with libtorrent, served by a small gateway | playing | 11.6 | yes |

The torrent row is a **stand-in**: libtorrent and a loopback gateway replace Elementum's iOS engine, and the sandbox cannot reach real swarms. It proves the hash check and the hand-off to Kodi, not the engine.

**Finding fixed during this step.** Kodi's player sends the `url|Header=value` headers only to the first request, so a header-guarded HLS stream was refused at its variant and segments and never started (first rig run: timeout). The app already has a loopback HLS proxy for this (`sports_hls_proxy`); `hls_bridge.py` now feeds it a standard-library session and `Playback` routes guarded HLS through it (and closes it on stop). Re-run: playing. Two earlier "failures" were mistakes in my test server (no Range support, an mp4 with its index at the end), fixed in the script.

## 2. TMDb and the Home page with Elementum and Burst disabled
Umbrella is not installed in the rig profile at all; Elementum and Burst were disabled through JSON-RPC for the run and restored afterwards. The Home page (screenshot, desktop rig) still drew its TMDb content (hero for a current film, "Netflix Originals" row). TMDb Helper directory listings with the engine off: popular, trending and top-rated movies returned 21 items each in 0.3 to 0.8 s.

Five films through the repository's TMDb code and the ten-site search (live):

| Film | TMDb facts (first / cached) | Search (s) | Verified candidates | Sites that did not answer |
| --- | --- | --- | --- | --- |
| The Dark Knight (2008) | 458 ms / 0 ms | 1.6 | 151 | 1337x refused (403) |
| Parasite (2019) | 193 ms / 0 ms | 1.3 | 123 | - |
| Spirited Away (2001) | 174 ms / 0 ms | 1.2 | 84 | - |
| Mad Max: Fury Road (2015) | 181 ms / 0 ms | 1.6 | 114 | - |
| Big Buck Bunny (2008) | 185 ms / 0 ms | 1.0 | 3 | - |

**Finding fixed during this step.** The first pass took 8.4 s for Spirited Away because one slow site (LimeTorrents) ran into the 7 s request limit and the search waited for it. `search_all` now returns once 5 candidates are in and 1.5 s of grace have passed; a site still answering is reported `pending` and is not penalised in health. Second pass: 1.2 s.

What this does **not** show: any of these films playing. Search finds torrents; playing one needs the debrid service or peers (steps 17 to 19), neither available here, so no film was opened from a search result. The first-result numbers are in the report; seeder counts are what the sites claim.

## 3. Before and after on identical fixtures (host, simulated latency)
Fixtures: five add-on providers at 50 ms each, ten site fetches at 150 ms each. `main` is the branch point before this work.

| Scenario | main (before) | this branch (after) |
| --- | --- | --- |
| Healthy primary | no backup work | no backup work (0 requests) |
| First backup answers | 51 ms, 1 request | 51 ms, 1 request |
| Three backups fail, fourth answers | 151 ms, 3 requests | 154 ms, 3 requests |
| Every add-on backup empty | 204 ms, nothing found | 204 ms, then the site searches |
| Ten site searches (new) | - | 306 ms, 8 requests (a sequential run would take 1200 ms) |
| Dead provider, first search / next search | - | 102 ms, 2 requests / 55 ms, 1 request (cooldown skips it) |
| Peak memory / threads left | 19.7 MB / 1 | 22.6 MB / 1 |

So the healthy path is untouched, the existing chain costs the same, and the new work only runs after every add-on failed or was empty.

## 4. UI
No screen was added or restyled. The only visible text added by these steps is one Notifications line (step 11), the plain "Waiting for peers" status property (not drawn by any skin element yet) and nothing else; the portrait Home page rendered normally in the rig with the new modules present. Policy section 7 and 9 review (mockup comparison, boards) was not run because no layout changed.

## 5. Realistic targets (from these measurements, not promises)
* Site search with the ten families: about 1 to 2 s on a good connection, bounded at 20 s; expect more on cellular.
* A direct link or guarded HLS opening in Kodi on the rig: 6 to 12 s to the first second of picture. The phone, a real provider and a slow CDN will differ; I do not promise five seconds.
* TMDb facts: about 0.2 to 0.5 s the first time, instant from the cache.

## 6. Not done
Phone timing; real provider or debrid links; a film opened end to end from a search result; Elementum's iOS engine; the Sports screens in the rig; the portrait boards comparison. No iPhone evidence.
