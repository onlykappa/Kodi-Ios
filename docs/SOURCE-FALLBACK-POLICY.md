# Fallback in the existing picker (roadmap step 8)

No new picker: `provider_fallback.py` and `provider_fallback_hooks.py` extend the Elementum/Umbrella flows and the Deck's "Choose a version" page. Tests: `scripts/test_provider_fallback.py` (14) and `scripts/test_provider_fallback_hooks.py` (20), host tests with fakes.

**When a backup runs.** Only after the primary route has failed, returned nothing, or returned nothing suitable (wrong title/year/episode, below the strict quality, unusable): Umbrella's no-results and zero-premium-provider paths, Elementum failures on download and season builds, and the Deck's empty or fully-filtered list. A healthy primary does no extra work (tested: `search` is never called). A source the user picked, and a manual cancel of the primary picker, never start a backup.

**When it must not.** `playback_uncertain()` (a player is open, opening or buffering: `Player.HasMedia | Player.Caching`) returns no fallback, so a second player is not started under an uncertain native one. A newer request replacing this one (its id left the Home window) or a cancel stops the search at the next check and again right after `search` returns, before anything is shown, resolved or played.

**Order and bounds.** Add-on backups in the existing order (jacktook, pov, otaku for episodes, thecrew, prism); the first one with a verified result wins. Only if every add-on failed or was empty does the first-party site search (`independent_search`) run, and only with the real transport (never in tests). Total search time stays 60 s, one provider 12 s, resolve 15 s, the site search at most 20 s of what is left. Within a picker round duplicates (same info hash, or same release name and size) collapse to the best-seeded row; a provider whose resolve failed is excluded for the next round, and another provider's copy of the same release stays available.

**Result handling.** Identity checks (`verified`, `check_usable`) apply to every candidate, including the site search. Streams go to the player once; magnets are never streamed: they use the existing download route and its torrent prompt. The independent candidates resolve to their magnet (no add-on to ask).

**Tested paths.** Movie: empty primary -> backup -> one `play`, wrong titles hidden, CAM/too small skipped. Episode: failure -> one search, one resolve, one URL; healthy primary -> no search. Failure and no-source: `None`, nothing started. Cancel and stale generation: no resolve, no picker. Uncertain playback: no search.

**Not done.** `backup_playback.Playback` (one-session player, time-advance check, fresh chain verification) is still not what the hooks call: `dispatch` and `umbrella_empty` keep their existing `xbmc.Player().play`/Umbrella `play_source` paths, whose tests would change with it. Adopting `Playback` there, and every device behaviour (picker display, real resolvers, receiver), need a phone run. No device evidence.
