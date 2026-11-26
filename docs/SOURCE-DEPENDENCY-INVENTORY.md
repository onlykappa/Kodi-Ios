# Step 1 — Source dependency inventory

Date: 2026-11-23. Baseline: main cf42c63; roadmap PR #56.
Evidence: [machine-readable inventory](../reports/source-dependency-inventory.json).
This is a static package/source audit, not an installed-phone inventory or live test.

## Findings that affect the backup architecture

1. Burst already contains local search definitions: 84 entries in its pinned
   `burst/providers/providers.json`. Its definitions loader reads bundled JSON,
   profile JSON and optional Python overrides. Search websites remain external.
   This is a stronger independent-search starting point than another remote aggregator.
2. CocoScrapers 1.0.45 contains 27 Python files in its torrent directory (including
   support/init files, not 27 proven working providers). Some are ordinary site
   scrapers; others call aggregators, e.g. Torrentio. Independence must be assessed
   per module, not per add-on label.
3. Crew's pinned source dynamically loads `crewproxy`, `crewstreamer`, `crewschedule`
   and `crewreplays` from the posadka/xmls2 repository. `control.cdnImport` attempts
   remote download first, then a cached profile Python file. Warm-cache survival is
   not fresh-install survival. Copying the base add-on alone misses this dependency.
4. Umbrella's available scratch snapshot is incomplete: manifest and two Python
   modules only. Its version is 6.8.01 but no complete matching package was verified.
   `sources.py` proves external provider selection and debrid resolution, not every
   implementation behind them. Do not label this the phone's exact Umbrella version.
5. Existing backup adapters delegate to installed code. Jacktook defaults to
   Torrentio/Comet; POV loads providers and selected debrid; Prism/Otaku retain upstream
   resolver dependencies. Several apparently different providers may share a backend.
6. Elementum client manifest labels its license non-commercial, but the actual
   hash-verified client LICENSE is MIT; the pinned engine LICENSE is also MIT.
   Record this discrepancy; preserve actual notices and audit each bundled dependency
   separately before redistribution. Do not infer the whole dependency closure is MIT.

## Verified package identity and provenance

Six package archives were freshly retrieved and their full SHA256 matched the
existing locks. No account was used or profile copied. The JSON report includes each
manifest SHA256, declared import/version constraints and safe literal hostname index.

| Component | Exact inspected version / revision | Evidence / licensing | Installation / role |
| --- | --- | --- | --- |
| Elementum client | 0.1.114; 8ea802e705c28fef692aef7908e8a7cfce9a55f0 | Verified client archive; LICENSE MIT vs contradictory manifest | Bundled plugin; local engine API/provider registration |
| Elementum engine | cdab7e2ed69122e048be158e2ebea70dbda789ee | Pinned config/service/API source and MIT LICENSE retrieved; binary not re-inspected | Existing iPhone framework, local HTTP 65220; torrent transport |
| libtorrent-go | d8763f5e17831acd4ec0a2841074113ae571157f | Build/source lock, not newly compiled | Go/C++ bridge |
| libtorrent | 760f94862ef6b76a13bba0a68d55ca6507aef7c2, RC_1_1 | Build script pin; dependency license review still separate | Peer/tracker/DHT networking |
| Burst | 0.0.99 | Verified archive; metadata WTFPL, included LICENSE | Bundled script; search definitions and parsers |
| CocoScrapers | 1.0.45; package revision f1772775291a432cf2a7c6e45ea038c894ea8b70 | Verified archive; metadata GPLv3 | Profile-installed module; search adapters |
| Umbrella | 6.8.01 partial snapshot | Manifest GPLv3; incomplete and not package-verified | Imported/profile provenance needs phone confirmation |
| Crew plugin | 3.2.2; package revision 68e8a45518d0ff60db0f315b87c0178edcf100d7 | Verified archive; metadata GPLv3 | App-bundled plugin, supported startup service |
| Crew module | 3.2.29; same package revision | Verified archive; GPLv3 headers/metadata | Profile-copy policy; scrapers, resolvers, dynamic modules |
| ResolveURL | 5.1.212; package revision 535d4dcc42145e2bfeaa3e0c6d5ec3d91a449c94 | Verified archive; lock records retained GPL-3.0-or-later headers | App-bundled host-specific resolvers |
| Fallback adapters | main cf42c63 | In-tree source | Bootstrap provider workers; lazy bounded movie/episode backups |

Source and package locks are migration/elementum-ios/source-lock.json and
migration/provider-fallback/source-lock.json. Native build pins also include Go
1.21.1, Boost 1.72.0 and OpenSSL 1.1.1f: old inputs are a maintenance risk, not an
instruction to upgrade them without compatibility tests.

### Declared dependency closure and installation boundaries

The JSON captures every declared `requires/import` for the seven inspected manifests
and the complete two build locks (including supporting package/module pins). These
are declared dependencies, not proof all imports/optional branches are satisfied.

- Elementum: Kodi addon API, repository.elementumorg, kodi-six, requests.
- Burst: Elementum, Kodi addon API, kodi-six, requests, future, pycryptodome.
- CocoScrapers: Python 3 Kodi runtime and requests.
- Umbrella partial manifest: Python 3 Kodi runtime, requests, YouTube. Selected
  external scraper and account modules are runtime dependencies beyond that manifest.
- Crew plugin/module: Python runtime, Crew module/artwork, ResolveURL, requests,
  simplejson, BeautifulSoup4, six, YouTube and inputstreamhelper; upstream also declares
  ResolveURL's adult extension. Existing packaging deliberately removes that extension
  and adult-only content; preserve that policy, do not reintroduce it as closure work.
- ResolveURL: six, kodi-six, pyqrcode, cloudrequest, YouTube, python.twitch and
  googledrive. Some paths are service-specific; do not fetch all optional accounts.
- Other backup roots: Jacktook 1.22.0; POV 6.11.03 plus Magneto 6.11.01; Otaku
  5.3.4; Prism 5.0.69, with scraper/data assets and transitives in provider-fallback lock.
  Their full runtime call graphs are not audited by this primary-stack step.

A clean dependency restoration/closure test belongs to steps 2–3. No installed
add-on-database, native framework binary or owner phone profile was inspected here.

## External dependency matrix

Required means required for the named path, not every possible path through Kodi.
All hostnames are ordinary public source/configuration references; no private stream
addresses, cookies, tokens or account identifiers are recorded.

| Family / example | Role and requirement | Account | Can local files replace it? | Failure / independence implication |
| --- | --- | --- | --- | --- |
| GitHub releases/raw/codeload, Kodi mirrors | Package retrieval at build/update time | Usually no | Preserve approved package/source inputs + notices; not yet mirrored by this step | Fresh build may fail even if installed app continues |
| onlykappa release assets | Native engine/framework build input | Repository access as applicable | Retain verified framework and source/build toolchain | Owner-hosted package availability is a separate dependency |
| Localhost 65220 | Elementum control/provider API | No remote account | Already local; preserve native engine | Not a remote media server |
| Burst's bundled site definitions | Local discovery configuration | Provider-dependent | Yes, exact licensed definitions and loader | Not dependent on fetching GitHub on each search; sites still required |
| Torrent search sites, e.g. 1337x.to | Search page/torrent discovery | Some sites require accounts | Local scraper can replace parser software, not the remote index | Layout/domain changes need fixtures and maintenance |
| torrentio.strem.fun; comet.elfhosted.com | Remote aggregation used by some backup paths | Path-dependent | Local search implementation can replace the role, not recover their private index | Shared aggregator outage may hit multiple add-ons |
| TMDb and other metadata APIs | IDs/title/year/episode/catalog enrichment | API access as configured | Cache known IDs/metadata; fresh catalog needs alternative/local input | Search must accept known identity without forcing catalog access where feasible |
| ESPN public schedules | Sports event identity, state, score/clock | No account in current public flow | Cached snapshot only temporarily; not future live updates | Does not provide playable streams |
| raw.githubusercontent.com / posadka/xmls2 | Crew Sports runtime modules and menus | Public source retrieval | Eligible exact modules/data could be bundled after provenance/license review | Current warm cache fallback fails if neither cache nor backend available |
| Real-Debrid, AllDebrid, Premiumize, TorBox, Offcloud | Cached torrent/unrestricted host resolution in selected paths | Yes, service-specific | No; local code cannot substitute server storage/entitlement | Try independent authorized transport; never assume accountless fallback equivalent |
| Host-specific pages, redirects, stream CDNs | Resolve and deliver bytes; required per selected source | Sometimes | Resolver code yes; content service and source-issued session no | Final addresses expire; resolve fresh; honor refusal/limits |
| Trackers, DHT bootstrap, peers, optional web seeds | Swarm discovery and content transfer | Public/private torrent-dependent | Engine local; optional discovery alternatives, but content still needs holders | Tracker outage may be survivable; no reachable content holders is not repairable by parser code |
| Trakt/Simkl, artwork services, optional YouTube/Twitch/Drive paths | Optional tracking/artwork/particular source features | Varies | Disable/cache optional features where supported | Do not make them compulsory for basic backup search |

The JSON's literal-host index is reproducible static evidence, NOT a verified list
of contacted servers. Dynamic URLs, provider settings, remote feeds, DNS/CDN changes,
comments and optional imports make static counts unsuitable for availability claims.

## Representative traced paths and code anchors

### Torrent search -> local engine

Elementum client `resources/site-packages/elementum/provider.py:156` registers movie,
episode and general search handlers. Burst `burst/burst.py` imports definitions and
runs selected provider parsers; `burst/providers/definitions.py:136` loads bundled JSON
and subsequently custom definitions/overrides. Provider results are sent through
Elementum's provider bridge; pinned engine `api/torrents.go` accepts/persists torrent
identity and `bittorrent/service.go` configures the libtorrent session. Discovery and
pieces then depend on trackers/peers/DHT, not a central Elementum video host.
This is a source trace, not a newly executed torrent transfer.

### Umbrella -> external scraper -> debrid

Partial `resources/lib/modules/sources.py:80` reads external_provider.module;
near 1892 it imports the configured provider name's `sources`; near 1532
`sourcesResolve` selects the debrid implementation and calls `resolve_magnet` for
eligible magnet results. Verified Coco modules include a direct site adapter
(`1337x.py`) and an aggregator adapter (`torrentio.py`). Missing Umbrella debrid,
settings and remaining runtime modules mean its exact complete resolution path and
phone configuration remain unknown. No account was probed.

### Crew movie/episode -> native resolver

In-tree `provider_adapters/thecrew.py` imports `resources.lib.modules.sources`, calls
`Sources.getSources`, then `Sources.sourcesResolve`. The verified Crew module defines
these at sources.py:2369 and :5679. Resolver/selected account dependencies remain;
the wrapper is not an independent reimplementation.

### Sports -> Crew dynamic modules -> local proxy -> player

Current `sports_hybrid`/`sports_provider` supply ESPN events; source selection routes
through `sports_loop_router` and `sports_native_routes` preserving native add-on
identity. Crew `crewservice.py:241` names remote crewproxy; :261–263 names streamer,
schedule and replay modules. `client.py:496–514` imports those on demand.
`control.py:547–571` downloads first and falls back to cached Python.
`segmentproxy.py:249–267` rewrites key/submanifest/segment references to loopback.
This establishes dependencies, not that the current external source opens or every
follow-up request is correct. Do not bypass refused JetExtractors access.

## Preservation priorities and next step

- First candidates: Burst's local definition/parser framework and permitted Coco
  site modules, with small adapter interfaces and deterministic fixtures.
- Preserve exact approved package/source baseline before extracting modules; distinguish
  remote aggregator adapters from independent website scrapers.
- Crew requires a separate eligible dynamic-module baseline and cache-cold outage tests.
  Do not download/execute arbitrary remote code during this inventory.
- Runtime backups currently remain downstream of upstream modules; do not declare the
  new independent pipeline implemented.

## Explicit missing evidence / owner files if exact phone parity is needed

No upload is required to begin isolated rig work from verified pins. For exact phone
parity later, obtain a sanitized add-on ID/version list and complete source-only copies
of Umbrella, selected scraper modules and any Crew downloaded runtime modules, with
checksums. Exclude settings.xml, databases, cookies, logs, caches and account data;
review individual runtime code files for embedded secrets before sharing. Preserve
private originals locally. Do not transfer a whole addon_data/profile directory.

Step 1's available-source audit is complete; exact phone versions, complete Umbrella
source, optional runtime import closure and dynamically contacted endpoints remain
explicit gaps. Step 2 can establish the isolated pinned baseline and record these
phone-parity limitations; it cannot silently claim them resolved.

Validation: six pinned archive SHA256 comparisons passed; seven manifests and safe
hostname references inventoried; actual LICENSE text checked for client/engine;
project/reference scan and diff whitespace checks run before commit. No production
code, live stream test, rig run, build, release or merge in this step.
