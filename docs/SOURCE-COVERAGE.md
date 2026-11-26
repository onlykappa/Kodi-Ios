# Source coverage matrix (roadmap step 9, first increment)

Code: `migration/bundled-bootstrap/resources/lib/independent_sites.py` (one adapter class per site family, `search_all` merges them) on `independent_search.py` (1337x) and the strict identity check. Tests: `scripts/test_independent_sites.py` (13 tests, synthetic pages in each site's documented format, host only). **Nothing below was checked live or on a phone.**

## What exists today

| Family | Media | Transport | Needs | Status |
| --- | --- | --- | --- | --- |
| apibay | movie, episode | public JSON API | nothing | adapter + fixtures |
| YTS | movie | public JSON API | nothing | adapter + fixtures |
| EZTV | episode with IMDb id | public JSON API | nothing | adapter + fixtures; the site's own season/episode numbers must match before the name is read |
| Knaben | movie, episode | public JSON API | nothing | adapter + fixtures; an index over many trackers (an aggregator, so it shares those sites' dependence) |
| 1337x | movie, episode | HTML list + detail pages | nothing | adapter + fixtures (step 5) |
| Add-on backups | movie, episode (otaku: anime) | Jacktook, POV, Otaku, Crew, Prism through their own add-ons | each add-on's upstream, usually a debrid account | wired in step 8; share backends (Torrentio/Comet and others) |
| Burst (84 definitions), CocoScrapers (26 torrent modules: 14 direct site/API scrapers, 12 aggregator or self-hosted service adapters, counted from each module's base link) | movie, episode | not adapted | varies | locked only; next increments |
| Umbrella-style resolution, Crew, Sports | | not adapted here | account / dynamic modules | step 10 and later |

Every family finds torrents only. Turning a hash into playback needs Elementum and, for streaming, a debrid account: **no debrid service is replaced or copied by any adapter**.

## Behaviour proven (host tests)

* All applicable families run at once (4 workers, 20 s total); each adapter's rows go through the same strict title/year/season/episode check as every other route; results merge by info hash keeping the best-seeded row.
* One family failing (timeout, offline, changed layout) is reported as its own typed outcome and the others still answer unchanged. A disabled family is never requested by any other adapter (checked per family). When every family fails the outcome is the typed failure (offline, unsupported), not `empty`; changed layout everywhere is `unsupported`.
* The search is the last resort in the fallback chain (step 8), so adding families costs nothing when the primary works.

## Not done in this increment

More families: the other HTML scrapers (bitsearch, LimeTorrents, torrentproject2, torlock, torrentdownload, kickass2, torrentz2, torrentgalaxy, rutor, nyaa) are deliberately not guessed: their page layouts can only be written correctly from a live capture, which needs the owner's go-ahead, and a fixture invented from memory would give false confidence. Also not done: Burst definitions, mirrors per site, live verification, rate limiting per site, and pack handling beyond the existing right-season rule (a season pack for the right season is accepted for an episode request, as the current identity check allows). Commit each future adapter separately with its fixtures.
