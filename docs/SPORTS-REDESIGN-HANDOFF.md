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
