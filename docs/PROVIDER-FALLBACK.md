# Movie/TV backup providers — PR #32

The existing provider remains first. Backups are searched only when its results are empty, filtered out by the existing identity/quality rules, unavailable, or timed out. Primary success and user cancellation do not start backup searches.

## Routing

The lazy backup order is Jacktook, POV/Magneto, Otaku for mapped anime episodes, The Crew, then Prism. The first usable provider supplies candidates to the existing Deck picker and its automatic ranking. The original movie/show ID, season, episode, quality profile and request lane stay attached throughout selection. A failed origin resolver or unreachable HTTP link advances to the next provider within a shared deadline.

Stream requires a resolved HTTP media link. Raw torrents remain on the existing Download route: Elementum's play URLs are intercepted as downloads in this app, so the fallback never silently converts Stream into a download. Download accepts magnets through the existing AllDebrid/Drive interception and HTTP sources through the same Drive copy queue. Direct HTTP jobs prove an exact byte range and size, preserve headers and never masquerade as torrents sent to the AllDebrid torrent API. Their expiry stops cleanly rather than switching files beneath a partial upload.

The existing manual Download only / Download and watch choice is retained. Background queueing checks the active request ID, lane, coordinates, deadline and cancellation tombstone before publishing a receipt or enqueueing. Downloaded-first and Continue Watching checks remain ahead of source discovery.

## Provider execution

Each search or selected-source resolution runs in an isolated Kodi script with an owner-only temporary mailbox. Upstream add-on dependencies are loaded explicitly; account defaults, GUI suppression and network guards are scoped to that invocation. Requests share an absolute deadline; canceled/late workers cannot recreate removed mailboxes. Diagnostics contain only provider/status/counts.

Existing provider credentials/configuration take precedence. Missing supported AllDebrid settings read through the existing Umbrella account in memory; explicit saved disabled settings remain disabled. Tokens are not copied into the bundle or configuration files. An untouched Jacktook installation can use public Torrentio/Comet manifests in memory; existing or explicitly empty selections are preserved. Prism includes a pinned a4k provider package. Otaku includes a pinned public ID mapping database and additionally verifies exact TMDb/TVDB episode identity through AniZip before deriving an anime episode number; it never guesses from a title or assumes season ordering matches.

Packages, required modules, provider data and licences are pinned in `migration/provider-fallback/source-lock.json`. The builder verifies hashes and dependency minimums, preserves newer compatible foundation modules, disables redundant provider background services and hides unrelated context entries. The Crew artwork package is retained because a headless import actually requires it; unused adult-only scraper modules are excluded with explicit patch receipts. No native provider engines are added.

## Review and reproduction

Host tests run under Python 3.11, matching the iPhone bundle. Fetch reviewed fixtures outside the checkout:

```sh
python3 -B scripts/provider_addons.py --output /tmp/kodi-provider-inputs
KODI_PROVIDER_INPUTS=/tmp/kodi-provider-inputs KODI_REQUIRE_PROVIDER_FIXTURES=1 python3 -B scripts/test_provider_adapters_primary.py
PROVIDER_FIXTURES=/tmp/kodi-provider-inputs python3 -B scripts/test_provider_adapters_secondary.py
KODI_PROVIDER_INPUTS=/tmp/kodi-provider-inputs KODI_REQUIRE_PROVIDER_FIXTURES=1 python3 -B scripts/test_provider_addons.py
KODI_PROVIDER_INPUTS=/tmp/kodi-provider-inputs KODI_REQUIRE_PROVIDER_FIXTURES=1 python3 -B scripts/test_provider_worker.py
```

Other focused suites are `test_provider_fallback`, `test_provider_probe`, `test_provider_queue_bridge`, `test_provider_direct_queue` and `test_provider_fallback_hooks`. Existing picker, season, download, Continue Watching and builder suites provide regression coverage. CI acquires the same pinned fixtures; building an IPA remains separately gated.

See `scripts/rig_provider_fallback.py --help` and `docs/design/KODI-RIG.md` for the real Kodi scenarios. The rig needs the reviewed packages staged with `provider_addons.install` into an `addons` directory with sibling `bootstrap`, then `--staged-addons <directory>`. Reports and screenshots stay outside Git. The rig runs Kodi 21.3 with Python 3.14 in this environment; it is not an iPhone binary.

The recorded rig evidence uses deterministic upstream-interface replies, real installed add-on imports, production adapters/workers, local HTTP checks, the existing picker and actual queue persistence. Separate host fixtures execute selected APIs from hash-checked upstream packages. This establishes routing and failure behavior, not current public-provider uptime, account playback, iPhone UI or AirPlay. Those remain device/live-account acceptance checks. Providers sharing a backend can share its outage; a second add-on does not create an independent debrid service.
