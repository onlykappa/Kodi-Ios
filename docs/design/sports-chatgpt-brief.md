# Sports: brief for ChatGPT (Codex) — Upcoming, a game's page, Leagues

Written 2026-11-15 for the owner's ChatGPT. Claude wrote the data contract and the other pages and will review and fix what you build.
Read this whole file, then `AGENTS.md`, then `docs/design/APPLE-UI-POLICY.md` (mandatory for any UI work) before you write anything.

## What you build (three pages, in this order)

| # | Page | Approved board in [sports-approved-pages.html](sports-approved-pages.html) | Window file |
|---|---|---|---|
| 1 | **Upcoming** (option A: a list by day) | boards 10, 11 (and 14 nothing, 15 can't load) | `IOSSportsUpcoming.xml` |
| 2 | **A game's page** (a game that has not started) | boards 12, 13 | `IOSSportsGame.xml` |
| 3 | **Leagues** (option A: by sport) | boards 16, 17 (and 20 can't load) | `IOSSportsLeagues.xml` |

Open the HTML in a browser: it is the look to match (iPhone 16 Pro, 402 × 874 pt; 1 pt = 2.687 Kodi units). The page behind each approved
choice is recorded in `docs/DECISIONS.md` DEC-054 to DEC-057. **Do not change an approved design.** If something cannot be done in Kodi skin
XML, say so in your report and propose the smallest change; do not redesign.

**Not yours (Claude does these):** the Library › Sports row, the Sports landing page, Live Now, a *league's* page (it is the Live Now cards plus
the Upcoming list, filtered), The Loop provider, merging add-ons, and wiring a tap on a source to real playback. Do not touch them.
When a tap should open one of those pages, call the route named below and log it; Claude connects it.

## The data: use only this (never an add-on)

`migration/bundled-bootstrap/resources/lib/sports_model.py` is the contract (read its docstring: the shape of a game, a source, a league and the
overview) and holds the shared rules and wording. `sports_provider.py` is the one door:

```python
import sports_provider, sports_model as sm
provider = sports_provider.get()          # real data; the same methods as the sample. Until The Loop lands it raises SportsUnavailable.
provider.upcoming_games(league=None)      # list of games; raises sm.SportsUnavailable when no add-on answered
provider.game('epl-1'); provider.leagues(); provider.overview(); provider.refresh()
sports_provider.play(source, log)          # a tap on a source line plays it at once
```

Use the helpers instead of writing your own wording or ordering: `group_by_day`, `clock_text`, `soon_text`, `sources_text`, `count_text`,
`versus`, `league_codes` (the chips), `order_leagues`, `league_detail`, `updated_text`, `device_offset()`. They are tested
(`scripts/test_sports_model.py`); if you need a new rule, add it to `sports_model.py` with a test in the same style.
**Sample data is opt-in** so invented games never reach a phone: set `KODI_IOS_SPORTS=sample` for the rig and in tests (or build `sports_model.Sample(...)` directly in
unit tests). `KODI_IOS_SPORTS=quiet` has nothing live; `=down` makes every call raise `SportsUnavailable`, to look at the can't-load pages. With no setting a page
shows its can't-load state until The Loop's provider lands; that is correct, not a bug.

## Routes (RunScript names)

Add to `PAGES` in `migration/bundled-bootstrap/default.py`: `sports_upcoming`, `sports_leagues`. The game's page opens from inside
`sports_upcoming` (no route of its own). Tapping a league row runs `RunScript(service.kodi.ios.bootstrap,sports_league,<league code>)`:
that page is Claude's; until it exists just log `sports: league <code>`. The Back button closes the window.

## Where the code goes (copy the pattern of the Library file manager)

- `migration/bundled-bootstrap/resources/lib/sports_upcoming_page.py` and `sports_leagues_page.py`: draw the window XML in portrait units from the
  existing helpers and tokens (`portrait.py`: `label`, `image`, `surface`, `nav_button`, `pill_button`; colours, fonts and radii from the policy §4).
  Model: `resources/lib/library_files_page.py` (its `files(ns)` returns `{ 'portrait/IOSLibraryFiles.xml': ... }`).
- `migration/bundled-bootstrap/sports_upcoming.py` and `sports_leagues.py`: the controller (window class, fetching, clicks). Model: `library_manager.py`
  (`class Files(xbmcgui.WindowXML)`, open with `(WINDOW, HERE, 'Default', '1080i')`, and the retry that lists the skin folder when Kodi says
  "XML File for Window is missing", see `transfers.run`).
- Register each page file the way `library_files_page` is registered in `portrait.py` (its `_spec` load, `files.update(...)`, and the code-hash list).
- `scripts/test_sports_upcoming.py`, `scripts/test_sports_leagues.py`: tests, and **list every new test in `.github/workflows/import-review.yml`**.
- If you add a new file type or a mockup, allowlist it in `scripts/check_project.py`.

## Behaviour (from the approved boards and decisions)

- **Upcoming:** header with Back and a refresh button; large title; the subtitle `updated_text(...)` and the count; league chips from `league_codes`
  (All selected; a chip filters). **The chips are the data, not the board's sample text** (the board draws All, NFL, NBA, EPL, NHL; the helper gives All, EPL, LIGA,
  NBA, NFL, NHL for the sample games): use the helper's list, in its order. When they do not fit on one line they **wrap onto a second row**; never scroll them sideways
  and never cut one off (DEC-050; Claude's Live Now page does the same); then a section per day (`group_by_day`): heading with the game count, a card of rows. A row: the start time (blue) and
  `soon_text` under it when within the hour, who plays whom (`versus`, wraps to two lines, never cut), the league label chip and `sources_text`, a
  chevron. A tap opens the game's page.
- **A game's page:** Back, refresh; the card with the league label, "Starts in 45 min" (blue), the two crests, the start time in the middle with
  the day under it; then **Sources** with the sources best first, each: the add-on, picture size and language, "Also on …" when `also` is set, the
  `Best` / `Also good` tag, a play button; a tap on a source calls `sports_provider.play(source, log)`. No sources: "No sources yet. Check back closer to the start."
- **Leagues:** title, `12 leagues · updated just now`-style subtitle, a section per sport (`order_leagues`), a card of rows: the league code in a
  circle, the name, and `league_detail` (the live part in red). A tap opens `sports_league` (above).
- **States on every page (policy §6):** open at once from what the provider has and refresh behind it (fetch in a thread; never block the UI thread);
  *updating* keeps the page's shape; **nothing coming up** ("No games coming up", button "See Leagues"); **can't load** (`SportsUnavailable`: "Can't load games
  right now", one "Try again" button; details go to the log, never the screen).
- Crests are pictures the add-ons supply at run time (`team['crest']`); when empty draw the three-letter code in a circle, as in the boards. Never commit artwork.
- Hit areas at least 118 units; focus is visible; text is Inter via the existing fonts; no size below 30 units.

## Rules you must follow (from AGENTS.md and the owner)

- **No text is ever cut off (DEC-050):** no "…", no clipped chips. Wrap or say it shorter. Test with the longest sample text
  (`Borussia Mönchengladbach`, `Brighton & Hove Albion`, `UEFA Champions League`, `Golden State Warriors`).
- Kodi conditions use `![…]`, never `!(…)`, and never `$INFO[...]` inside a condition. Kodi list cells drop buttons: do not put buttons in list items.
- Check the page in the **desktop Kodi rig** (`python3 -B scripts/kodi_rig.py setup` once, about 15 min; then `start`, `sync`; guide `docs/design/KODI-RIG.md`),
  compare with the approved board, and fix what differs. Screenshots stay out of Git. Label what you checked (mockup, desktop Kodi rig, device) and say
  plainly what is only checked by tests. **Never claim a phone result:** only the owner's iPhone proves that.
- Before every commit: `python3 -B scripts/check_project.py` and `python3 -B scripts/check_ui_guidance.py` pass, every test listed in
  `.github/workflows/import-review.yml` passes, and stray `__pycache__` folders are deleted.
- Every fix gets a `docs/ISSUES.md` entry (cause, fix, retest, test) if it fixes a bug; new work gets a note in `docs/PROGRESS.md`.
- Keep private data, keys, tokens, logs and model names out of commits. Do not merge anything, build or publish an IPA, or touch
  `migration/airplay-ios/source-lock.json`. Commit trailers: none needed from you beyond a clear message.

## Git

Branch from `claude/sports-leagues` (it holds the approved mockups, the contract and this brief), e.g. `codex/sports-upcoming-leagues`.
One draft PR whose base is `claude/sports-leagues`; do **one page per commit** (Upcoming, then the game's page, then Leagues) so each can be
reviewed on its own. Push only to your own branch.

## When you are done

Report, in plain words: what you built, what you checked and in which evidence class, anything that differs from a board and why, and anything
you could not do. Claude then reviews and fixes the PR, wires the real data and the league page, and the owner tests on the iPhone.
