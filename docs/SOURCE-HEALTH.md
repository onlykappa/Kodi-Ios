# Provider health and recovery (roadmap step 11)

Code: `migration/bundled-bootstrap/resources/lib/source_health.py`; used by `provider_fallback.search` (the five add-on backups) and `independent_sites.search_all` (the ten site searches). Tests: `scripts/test_source_health.py` (13 tests, host only).

**What is recorded.** A source name, an outcome kind and times, in `source-health.json` in the app's profile (atomic write, at most 64 entries, entries unused for 7 days dropped). Never a link, title, header or token (a test reads the file and finds none).

**Cooldowns.** A confirmed failure cools the source down, growing with consecutive failures and expiring by itself: offline/timeout 2, 10, 30 minutes; refused (403/429/451) 15 minutes, 1 hour, 6 hours; account-required 1 hour then 6; unsupported (layout changed, unusable result) 6 hours then a day. A cooling source is skipped, so a dead or rate-limited source is not scanned again and cannot hold up the others. `retry(source)` is the deliberate "try again now": it clears the cooldown but keeps the failure count, so a second failure cools longer.

**What changes nothing.** Cancel is never recorded (it neither penalises a source nor advances to the next one; tested), and `empty` and `expired` carry no penalty (expired links are refreshed once by the step 6 resolution, then the next candidate is tried).

**Ordering.** Sources that succeeded in the last day come first, most recent first. Everything else keeps its given order. A source never tried is `unknown`: still eligible, never reported healthy.

**Bounds.** One provider is limited to 12 s and the whole fallback to 60 s (step 8), the site searches to 20 s; a timeout is recorded and cools that source. The first successful provider ends the search, so one source is selected once.

**Not done.** Nothing here measures speed beyond the timeouts, and health is per source, not per title. The cooldown tables are my choices, not tuned on real traffic. It does not surface a message to you (no popup by design). Not wired into the Sports routes or `backup_playback`. No device evidence.
