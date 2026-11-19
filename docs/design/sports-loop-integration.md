# Sports: The Loop integration — status and what comes next (DEC-055, DEC-057)

## What is done (code, tested)

- **Merging** (`sports_merge.py`, `scripts/test_sports_merge.py`): records from any add-on become the contract's games. One game from many add-ons;
  the same stream (picture size + language) from several add-ons is one line with "Also on …"; different choices stay as options, best first;
  `best` for the clearest picture, `good` for a second source from 720p up. Team names are matched across spellings ("Man City" = "Manchester City",
  accents and "FC" ignored) and a game from another day or league is never merged. Rule of thumb: when unsure it does not merge.
- **Discovery** (`sports_loop.py`, `scripts/test_sports_loop.py`): The Loop's code is not in this project and its listings must not be guessed.
  The first time the Sports page asks for data, a background thread lists the menu **folders** of `plugin.video.the-loop`, `plugin.video.loopguide`
  and `plugin.video.looptv` through Kodi (`Files.GetDirectory`: folders only, nothing is opened, played or resolved), at most 3 levels, 60 entries and 25 s
  each, at most once every 12 hours. It writes `special://profile/addon_data/service.kodi.ios.bootstrap/sports-discovery.json` and the first 120
  lines to `kodi.log` as `Kodi iOS Sports discovery: …`. A folder that fails is recorded on its entry; nothing here can break a page.
- **The provider** (`sports_provider.real()` → `LoopProvider`): until an adapter exists every call says "no source", so Live Now, the landing
  page and the other pages show their can't-load state. Sample data never reaches a phone (it is opt-in, `KODI_IOS_SPORTS=sample`).

## What is NOT done: the adapter

Turning The Loop's items into `sports_merge` records (league, teams, start time, clock, score, picture size, language, what to play) needs its real
listing, which only your phone can show. Nothing about its format is assumed.

## The next step (needs a build and your phone)

1. A build that has this code (an IPA with the Python add-on only; no AirPlay framework build is needed).
2. Open **Library › Sports** once, wait about a minute (it shows "Can't load sports right now": expected), then send the log (`kodi.log`).
   The lines to look for start with `Kodi iOS Sports discovery:`; `sports-discovery.json` in the add-on's data folder holds the same tree.
3. From that tree Claude writes the adapter (a `parse` per listing shape), with tests built from the real lines, and the pages fill with real games.
   The Loop Guide and Loop TV follow the same way, then the other pre-installed providers (DEC-055 needs no page change).

## Privacy

The tree holds menu labels, add-on folder paths and the first 80 characters of an item's description, cut at 160 characters. It holds no account,
key or stream address that the listing does not itself show. Read the log lines before sending if in doubt.
