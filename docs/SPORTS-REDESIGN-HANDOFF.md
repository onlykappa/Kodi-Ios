# Sports redesign and league filter: handoff (owner-approved, 2026-11-19)

**Branch:** `claude/sports-redesign`, started from `origin/main` (PR #43 to #47 already merged: ESPN schedule, Crew playback, Sports opening card). Do **not** work on `claude/build442-feedback` (PR #28): it is 162 commits behind main and has none of the Sports code.

**Mockups (owner: "I love it", with real league logos, "as long as we got UFC I don't care for boxing"):** `docs/design/sports-redesign-mockups.html`.
- Board A: the three pages remade cleaner: hub (`sports_page.py`, window `IOSSports.xml`), Upcoming (`sports_upcoming_page.py`, `IOSSportsUpcoming.xml`) and Leagues (`sports_leagues_page.py`, `IOSSportsLeagues.xml`).
- Board B: an **Edit** button at the top of every Sports page opens one sheet with a switch per league, grouped by sport, with an "Only" shortcut per sport, "All on", "All off", a count badge on the Edit button while a filter is on, "Showing NFL and NBA" under the hub title, and the empty state "No leagues are on".
- Owner choices not yet answered (defaults in the mockup): Edit as a text button; one filter shared by all three pages; every league on by default; keep the "Only" shortcut. Team crests beside each game were offered, not requested.

**Data:** the pages already read ESPN through `sports_espn.py` / `sports_model.py`; the Crew supplies sources only for ESPN-live games (see `docs/SPORTS-HANDOFF.md`). Do not touch playback.

**Logos (owner: real logos, not letters):**
- Fetch at runtime and cache on the phone, like posters. Never commit images (`check_project` rejects them; policy §5.4).
- League logos, checked 2026-11-19: `https://a.espncdn.com/i/teamlogos/leagues/500/<key>.png` works for nfl, nba, mlb, nhl, mls, lpga, ufc, f1, wwe. Others come from the scoreboard's `leagues[0].logos[0].href`: college football and basketball, pga, the Premier League, La Liga and the Champions League.
- Boxing has no logo: show a neutral sport icon from `special://skin/extras/icons/` on the same light tile, never letters. The same fallback covers any league without a logo.
- The logo tile is a light rounded square (38 units in rows, 20 for the small league mark on a game), so dark logos read on black.

**Filter:** store the chosen leagues (default all on) in one small JSON in the add-on's data folder; one pure module (host-tested) turns the games and leagues lists into the filtered ones; all three pages and their counts read it. Chips on Upcoming show only the leagues that are on.

**Rules:** read AGENTS.md, CLAUDE.md and `docs/design/APPLE-UI-POLICY.md`; every fix gets an ISSUE entry and a test in import-review.yml; run `check_project.py` and every test before each commit; check each board in the desktop rig (`scripts/kodi_rig.py`) next to the mockup with no cut-off text (DEC-050); keep rig screenshots out of Git; use one agent at a time; never merge a PR or publish an IPA without the owner's OK.

## Game page and reminders (mockups made 2026-11-19, awaiting owner approval)

`docs/design/sports-game-mockups.html` (board C): the page that opens when a game is tapped, from the owner's Apple Sports reference.
- Both team crests (fetched at runtime from ESPN's image host, cached, never committed), the start time or the live score, one action:
  **Remind me** (before a source exists) -> a sheet with two switches (when a source is ready; 15 minutes before it starts) ->
  **Reminder on** -> when a source is found the phone sends a notification and the button becomes **Play** with "Best source: The Loop · 1080p · English"
  and "Other sources (n)". Live games show the score and Play at once.
- Owner's words: "Follow should ask to send a reminder to your phone, then when the link is available it will replace the remind with the play button
  providing you with best source". Open question: name the button Follow or Remind me. Betting odds are left out; standings are optional.
- The data is in `sports_game_page.py` / `sports_game.py` (window `IOSSportsGame.xml`); sources already carry quality, language and a best/good tag.
- **Info and Standings tabs (board D, same file):** a two-tab switch under the action button. Info: kickoff, venue, broadcaster, recent form (last five) with each team's record; a row is left out when ESPN has no data for it. Standings: the division table with team crests (the game's two teams tinted) and a Divisional / Wild Card switch; leagues without a table hide the tab. Betting odds are not included.
- **Owner, 2026-11-19:** Kodi can send notifications (the reminder works as designed). The owner suggested standings go under Info instead of a separate tab: board D now shows both (D1/D2 tabs, D3/D4 one scrolling Info page with standings below, suggested). Standings = the division table (W, L, T, PCT) with crests; the game's two teams are tinted. Awaiting the owner's pick.
