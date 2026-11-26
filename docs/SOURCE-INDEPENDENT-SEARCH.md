# Independent search adapter (roadmap step 5)

Code: `migration/bundled-bootstrap/resources/lib/independent_search.py` (provider name `local`, accepted by `provider_fallback.normalize` through the new `INDEPENDENT` tuple; it is not in `PROVIDERS`, so the add-on fallback loop and its worker never call it). Tests: `scripts/test_independent_search.py`, 13 tests, run with the network off too (host tests).

**Choice.** From the step 1 inventory, the direct site scraper path (CocoScrapers 1.0.45 `1337x.py`, GPLv3, the same list/detail page structure) rather than an aggregator such as Torrentio or Comet, which only wraps a remote service. The adapter is new first-party code written from the page structure; no CocoScrapers code was copied, so its licensing is this repository's. It needs no add-on, no Burst and no Crew discovery service: it uses only the Python standard library and an injected `fetch`.

**What it does.** Builds the query from the strict identity (title + year, or title + SxxEyy), fetches one results page, drops rows with no seeders or a name that fails `provider_fallback.verified` (so wrong titles cost no further request), fetches at most 8 detail pages with 3 workers for the best-seeded plausible rows, reads the magnet and info hash, verifies again, and returns `(outcome, candidates)` using `source_contract` outcomes. Links that leave the site's host are dropped. Page size, per-request time (7 s), total time (20 s) and result count are bounded; cancel is checked before the first request and after the details.

**Outcomes.** A valid page with no usable rows is `empty`; a page without a results table (layout changed) is `unsupported`, never `empty`; HTTP and network errors map through `classify` (refused, expired, timeout, offline). A second domain is tried only after the first fails.

**Streaming.** The adapter finds torrents. A bare torrent has only `download`/`torrent` capability: `check_usable` rejects it for `stream` until Elementum or a debrid service resolves it. So this restores search independence, not playback independence; the debrid and tracker dependencies in step 1 still apply.

**Not done.** Fixtures are synthetic pages in the layout above, not live responses; no authorized live check was run, and the real site may differ, sit behind Cloudflare or have changed domains. The adapter is not wired into the playback loop or the picker. No device evidence.
