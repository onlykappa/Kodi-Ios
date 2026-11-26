# Sports as a separate source capability (roadmap step 10)

Code: `migration/bundled-bootstrap/resources/lib/sports_match.py` (policy), `Playback.start_resolved` in `backup_playback.py` (live hand-off), on `sports_merge.same_game` (teams, league, 45-minute start window) and `source_contract`. Tests: `scripts/test_sports_match.py` (18 tests, host only, loopback server).

**Identity.** ESPN supplies the game (id `espn:<league>:<event>`, league, both teams, start, live/upcoming state, scores); sources never define a game. Checked once against ESPN's public scoreboard on 2026-11-26 (point in time): the fields the app reads are present (`events[].id`, `status.type.state` `pre`/`in`/`post`, `competitors[].team.displayName`, `score`).

**Matching.** `unique_match` accepts exactly one current listing: same league, same two teams (`Chelsea` is not `Chelsea Women`), start inside the window, with sources. None is `empty`. Two listings that differ by more than 2 minutes in start (a second game, a lookalike) are `unsupported`: the closest is never guessed. The same listing seen twice merges its sources. A game ESPN says is live for over 8 h, upcoming but started over 3 h ago, more than a day away, finished, or in an unknown state is stale and nothing is matched.

**Starting.** `Launcher.start` hands the chosen source to the existing native Crew launch (`sports_provider.play`, unchanged) only if: the listing was read within 5 minutes (`LIVE_TTL`), a cancel has not come, ESPN asked again just before still says the game is current, and no start for this game is already opening (a second tap does nothing; a failed start releases the guard). `persistable` returns ids and labels only; the play request, links and headers are never saved or logged.

**Independent embeds.** `start_independent` resolves the embed page to a fresh HLS playlist now (`sports_independent.resolve`), fetches master, variant, key and segment with the required headers and cookies, then plays it through `Playback.start_resolved` (one session, time must advance, stop and cancel close it). Controlled test: game -> playlist -> advancing playback; a 429 playlist is `refused` before the player is touched; no advance is `timeout` and the player is stopped.

**Not done.** Not wired into the Sports screens or `sports_provider` (they keep their current paths); no real stream, Crew walk or embed site was contacted, so nothing says an actual game will open, and one game working says nothing about the next: sources for live games come and go. No device evidence.
