# Source coverage matrix (roadmap step 9, first increment)

Code: `migration/bundled-bootstrap/resources/lib/independent_sites.py` (one adapter class per site family, `search_all` merges them) on `independent_search.py` (1337x) and the strict identity check. Tests: `scripts/test_independent_sites.py` (17 tests, synthetic pages in each site's documented format, host only). **Nothing below was checked live or on a phone.**

## What exists today

| Family | Media | Transport | Needs | Status |
| --- | --- | --- | --- | --- |
| apibay | movie, episode | public JSON API | nothing | adapter + fixtures |
| YTS | movie | public JSON API | nothing | adapter + fixtures |
| EZTV | episode with IMDb id | public JSON API | nothing | adapter + fixtures; the site's own season/episode numbers must match before the name is read |
| Knaben | movie, episode | public JSON API | nothing | adapter + fixtures; an index over many trackers (an aggregator, so it shares those sites' dependence) |
| Bitsearch | movie, episode | HTML list page | nothing | adapter, parser checked against a real page captured 2026-11-26 |
| TorrentDownload | movie, episode | HTML list page | nothing | same: real capture |
| LimeTorrents | movie, episode | HTML list page (the .lol host redirects to another domain) | nothing | same: real capture |
| Kick4ss | movie, episode | HTML list page | nothing | same: real capture |
| Nyaa | episode | RSS feed | nothing | same: real capture; anime names rarely carry SxxEyy, so the strict check keeps only exact matches |
| 1337x | HTML list + detail pages | nothing | adapter + fixtures (step 5) |
| Add-on backups | movie, episode (otaku: anime) | Jacktook, POV, Otaku, Crew, Prism through their own add-ons | each add-on's upstream, usually a debrid account | wired in step 8; share backends (Torrentio/Comet and others) |
| Burst (84 definitions), CocoScrapers (26 torrent modules: 14 direct site/API scrapers, 12 aggregator or self-hosted service adapters, counted from each module's base link) | movie, episode | not adapted | varies | locked only; next increments |
| Umbrella-style resolution, Crew, Sports | | not adapted here | account / dynamic modules | step 10 and later |

Every family finds torrents only. Turning a hash into playback needs Elementum and, for streaming, a debrid account: **no debrid service is replaced or copied by any adapter**.

## Behaviour proven (host tests)

* All applicable families run at once (4 workers, 20 s total); each adapter's rows go through the same strict title/year/season/episode check as every other route; results merge by info hash keeping the best-seeded row.
* One family failing (timeout, offline, changed layout) is reported as its own typed outcome and the others still answer unchanged. A disabled family is never requested by any other adapter (checked per family). When every family fails the outcome is the typed failure (offline, unsupported), not `empty`; changed layout everywhere is `unsupported`.
* The search is the last resort in the fallback chain (step 8), so adding families costs nothing when the primary works.

## Live checks (owner-authorized 2026-11-26, point in time)

Public searches were requested once per site from this cloud container to capture real markup; no accounts, cookies or downloads. **These are evidence about that moment only; a site can change or vanish.**

* Reachable and used as fixtures: Bitsearch, TorrentDownload, LimeTorrents (redirected to a different domain), Kick4ss, Nyaa (RSS). The JSON formats of Knaben, EZTV and apibay matched the adapters (an empty YTS answer has no `movies` key, which the adapter already handles).
* Not captured: 1337x (HTTP 403 from its Cloudflare front, so its fixtures stay synthetic and its adapter is the least certain), Torlock (403), TorrentProject2 and Torrentz2 (no connection). Their adapters were not written. Rutor was reachable but is a Russian-language index and was not added.
* The captured names rarely carry a year, so the strict identity check rejects most real rows for a film (the Big Buck Bunny test shows zero accepted): that is the check working, not an adapter fault.

## Not done

Torlock, TorrentProject2, Torrentz2 (blocked from here), Rutor, mirrors per site, Burst's 84 definitions and CocoScrapers' remaining modules, rate limiting per site, and a repeat of these captures from the phone's network (a site that answers this container may block the phone, and the reverse). A season pack for the right season is accepted for an episode request, as the existing identity check allows. No device evidence.
