# Sports on JetExtractors: what is tested, what is not, and what to suspect (2026-11-16)

Branch `claude/sports-jet` (ISSUE-362, ISSUE-363, DEC-061). Device behaviour is unproven until the owner's phone log exists.

## Tested here (host tests and the desktop Kodi rig; none of this proves the phone)
- Upcoming, Leagues and Game open as `WindowXMLDialog` (rig A/B; `test_sports_dialogs`).
- `sports_jet.py` with duck-typed JetItem/JetLink fakes (`test_sports_jet`): title/league/quality/language parsing, live/upcoming/finished state,
  one record per stream, two scrapers merged into one game with two sources, a failing scraper, a slow scraper finishing in the background,
  "nothing answered" gives `SportsUnavailable`, JetProxy path encoding, the provider door leaves sample play values alone.
- All Sports tests, `test_provider_addons` and `check_project.py` pass. ESPN is still reachable with `KODI_IOS_SPORTS=espn`.

## NOT tested (needs the phone, an evening with live games, and the log)
1. **Whether JetExtractors answers a caller that is not The Loop.** Never run against the real add-on: its `config.py` is obfuscated and ISSUE-357 says it refuses callers it does not recognise.
2. Real scrapers: which of ~45 answer, how long they take (the page waits 18 s), whether titles parse as "A vs B" (single-name events and channels are dropped).
3. Whether scrapers return `starttime`/`status` we classify correctly (live window is 4 h from start; "Ended/Final/Replay" is dropped).
4. Playing: `expand()` (links flagged `links` go through `get_links`, others `get_link`), ResolveURL streams, and the JetProxy route.
5. League and sport labels for add-on text we do not map (shown as "Other"); duplicate games when two scrapers list "A vs B" and "B vs A" (they would not merge).
6. Live scores and clocks: scrapers give none, so live games show 0-0 and no time left (ESPN gave these; a later step could take them from ESPN).
7. Popups: whether Kodi asks the JetProxy "use inputstream?" question when its setting is unset.

## If it does not work: what I suspect, in order
1. **Refused or no config** (`jet: ... refused or failed`): JetExtractors checks who calls it, or cannot fetch its config. Fix is on The Loop's side (a hook that lets the Loop list games for us), not a workaround here. I will write the prompt for the owner's agent.
2. **Not installed or not importable** (`JetExtractors is not installed`): the Loop install (ISSUE-357 follow-up) did not bring `script.module.jetextractors`, or its `lib` path is not found.
3. **Scrapers answer but zero games**: domains/config blocked, or the sites need a network the phone lacks; look at per-scraper lines in the log.
4. **Games list but nothing plays**: the `plugin://plugin.video.jetproxy/play/...` path decoding (I encode `?`/`&`), a missing JetProxy setting, or a stream behind `links` that needs the add-on's own player.
5. **Slow page**: 18 s wait is too long or too short; tune `LOAD_SECONDS`.

## Log lines to send (no stream addresses are logged)
`Kodi iOS Sports: jet: N scrapers (configured)`, `jet: <name> X games, Y streams, e.g. ...`, `jet: <name> failed (...)`, `jet: all scrapers answered after Ns`, `sports: playing <scraper> via JetProxy|Kodi`.
