# Provider health and recovery (roadmap step 11)

Code: `migration/bundled-bootstrap/resources/lib/source_health.py`; used by `provider_fallback.search` (the five add-on backups) and `independent_sites.search_all` (the ten site searches). Tests: `scripts/test_source_health.py` (19 tests, host only).

**What is recorded.** A source name, an outcome kind and times, in `source-health.json` in the app's profile (atomic write, at most 64 entries, entries unused for 7 days dropped). Never a link, title, header or token (a test reads the file and finds none).

**Cooldowns.** A confirmed failure cools the source down, growing with consecutive failures and expiring by itself: offline/timeout 2, 10, 30 minutes; refused (403/429/451) 15 minutes, 1 hour, 6 hours; account-required 1 hour then 6; unsupported (layout changed, unusable result) 6 hours then a day. A cooling source is skipped, so a dead or rate-limited source is not scanned again and cannot hold up the others. `retry(source)` is the deliberate "try again now": it clears the cooldown but keeps the failure count, so a second failure cools longer.

**What changes nothing.** Cancel is never recorded (it neither penalises a source nor advances to the next one; tested), and `empty` and `expired` carry no penalty (expired links are refreshed once by the step 6 resolution, then the next candidate is tried).

**Ordering.** Sources that succeeded in the last day come first, most recent first. Everything else keeps its given order. A source never tried is `unknown`: still eligible, never reported healthy.

**Bounds.** One provider is limited to 12 s and the whole fallback to 60 s (step 8), the site searches to 20 s; a timeout is recorded and cools that source. The first successful provider ends the search, so one source is selected once.

**Retry-After.** A 403/429/offline/timeout answer that carries a numeric `Retry-After` sets that source's cooldown to the server's own wait (at least 30 s, at most 6 h); a layout change is never shortened by it.

**Tuning against real traffic (what could and could not be done).** Measured 2026-11-26 from the cloud container, three requests each: every site answered in about 0.1 to 1.1 s (Bitsearch 0.6-0.9 s, TorrentDownload 0.4-0.5, LimeTorrents 0.7-1.1 including its redirect, Kick4ss 0.2-0.7, Nyaa 0.7-0.9, Knaben 0.3-0.7, EZTV 0.4, apibay 0.1-0.5, YTS 0.4-0.5), so the 7 s per-request limit leaves a wide margin and a timeout really means trouble. None rate-limited or refused those requests, so no real 429 or ban answer was observed and the refusal cooldowns stay my judgment, now replaced by the server's own wait whenever it gives one. The phone's cellular and home-Wi-Fi paths were not measured: the profile's health file (`source-health.json`) and `Health.report()` give the numbers to tune from once there are phone logs.

**Visible notice.** When a source starts resting, `Health.tell` adds one plain line to the Notifications list through `notices.note('info', ...)` (no popup): title "A source is resting" or "Some sources are resting", text such as "Apibay did not answer. Others are used, and it is tried again in about 3 min." At most one every 30 minutes, once per cooldown, at most three names ("and 3 more"), no link or error text, no ellipsis. It follows the UI policy's wording rules (plain words, nothing cut off, raw errors stay in the log); no layout or styling changed, and I did not look at it on a rig or the phone.

**Sports.** The Sports router keeps its per-stream ranking (`sports_stream_health`) and now also records every worked or failed stream under its source family (`sports:crew`, `sports:loop`) through `FamilyHealth`; a family cooling down is tried after the others, never dropped (a live game may have few sources), and the person's own pick keeps the lead. `sports_match.Launcher` and `start_independent` record into it too (failed launches cool their family, a cooling family goes behind the others, a source the person picked is not reordered, cancel is never recorded).

**Not done.** The cooldown tables are still untuned by phone traffic. The notice is untested on screen. `backup_playback` does not record health (its callers do). No device evidence.
