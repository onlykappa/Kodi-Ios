# Independent backup source contract (roadmap step 4)

Code: `migration/bundled-bootstrap/resources/lib/source_contract.py`, on top of the existing `provider_fallback.py` (request, candidate, `verified`, `eligible`) and `source_match.py` (title/year/season/episode identity). Tests: `scripts/test_source_contract.py` (host test; not device evidence).

**Request.** `provider_fallback.request_from_expected`: media type, title and aliases, year, TMDb/IMDb/TVDB ids, season and episode, purpose (`stream` or `download`), quality profile. A request with no year/id for a film, or no season/episode for a show, is ineligible and nothing can be accepted for it.

**Candidate.** `provider_fallback.normalize`: provider, name (at most 2048 characters), quality, size, seeders, and at least one of a resolver, a link or a torrent hash. Non-finite or negative numbers, unknown providers and non-JSON payloads are dropped. `source_contract.stamp` adds `capabilities` (derived from facts the candidate carries, never from what a provider says) and `expires_at` (default 30 min, a provider value is capped at 6 h, a missing or invalid value counts as expired).

**Outcomes** (one closed set): `ok, empty, offline, timeout, unsupported, account-required, refused, expired, canceled`. `classify(error)` maps an exception without reading its message (so a URL in a message cannot leak): 401/402/407 account-required, 403/429/451 refused, 404/410 expired, timeouts timeout, cancel canceled, parse/type errors unsupported, other network errors offline.

**Gate before playback.** `check_usable(candidate, request)` raises a typed outcome unless the request is eligible, the handle has not expired, it has the capability for the purpose, and `verified` accepts the name for this exact title, year, season and episode. Wrong titles, wrong years, other episodes, season packs for a single episode, titles with no year when ambiguous, malformed payloads and unsupported results are tested to stop here.

**Secrets.** `redact(candidate)` is the only form for logs and disk: id, provider, name, quality, size, seeders, cached, capabilities and expiry. Links, headers, resolver payloads and tokens are never in it.

**Not done in step 4.** No adapter yet calls `classify` or `check_usable`; `provider_fallback.search` still logs its older status words (it has no `unsupported`, `account-required`, `refused` or `expired`). Wiring that, and any live provider, belongs to steps 5 onward. No device evidence.
