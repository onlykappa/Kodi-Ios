# Fresh resolution (roadmap step 6)

Code: `migration/bundled-bootstrap/resources/lib/fresh_resolve.py`, on `provider_fallback.resolve` (identity check, link-scheme check, provider's own resolver) and `source_contract` outcomes. Tests: `scripts/test_fresh_resolve.py`, 13 tests against a loopback HTTP server (host tests, not device).

**Resolve at use.** `resolve_fresh` always asks the provider's resolver (ResolveURL or the add-on's native path, through the existing transport) for a new link; a candidate's saved link is never played. Candidates that fail the strict identity check never reach the resolver (tested: zero resolver calls).

**Continuity.** `Session` keeps one cookie jar and the provider's headers for every request. The controlled server requires the header on all requests and the cookie it sets at the master playlist on every later one; the test shows master, variant, key and first segment succeed, the segment is read with a one-byte range, and the saved link is not requested. Redirects stay on http(s), never from https to http, and Authorization, Cookie and Host headers are dropped when a redirect changes host.

**Typed failures.** 401/402 account-required, 403/429 refused, 404/410 expired, no segments empty, SAMPLE-AES or other non-AES-128 key methods and non-playlist responses unsupported, timeouts timeout, cancel canceled. An expired link is re-resolved once; a second expiry returns `expired` without looping.

**Secrets.** `Resolved` hides its link and headers from `repr`/`str`; `scrub()` removes URLs, magnets and token/key/sig/session/cookie parameters from any text that is logged. Nothing is written to disk.

**Not done.** Only a loopback server was used: no real provider, ResolveURL host, debrid account or CDN, and no authorized live check. HLS behaviour on the phone (inputstream, AirPlay, resume) is step 7's work. The module is not called from the playback loop yet. Playlists: master/variant, `EXT-X-MAP` init segments and up to four rotating keys are checked; byte-range maps, multi-variant switching and encrypted init segments are not. No device evidence.
