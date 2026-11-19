# Sports › Live Now: what the page needs from the foundation

Read off the approved Live Now page ([sports-approved-pages.html](sports-approved-pages.html), DEC-055). It says nothing about how any
add-on works. The page asks for **one combined answer** for all add-ons, never one per add-on.

## For each live game

| On screen | Needs |
|---|---|
| League label (NFL, NBA, UCL, NHL …) | a short code (up to four letters) and, for the game page, the full league name |
| Two teams | a name each (the longest are about 25 characters: they wrap, they are never cut), a three-letter code, a crest picture if the add-on has one |
| Score | one number per team |
| How far in | one short text the foundation builds from the sport: "Q3 · 8:41", "P2 · 8:40", "67′", "Top 6" |
| Sources | a list, best first (below) |

## A source

- the add-on it came from (The Loop, Loop Guide, Loop TV, Loop Sports Hub);
- picture size and language, as two short fields ("1080p", "English");
- a tag: `best`, `good` or none;
- the other add-ons that have the same stream (names only);
- what to play: whatever the existing play path needs (the foundation decides; the page only taps it).

## Combining (DEC-055)

1. One game from many add-ons: match on league, both teams and start time.
2. Same picture size and language: one line, chosen by quality, and the other add-ons are named under it.
3. A different size or language: its own line.
4. Order: best first; `best` goes to the clearest picture; at most one more `good`.
5. The list of games is ordered **closest to the end first** (DEC-055): the share of the game left, worked out per sport (clock and
   period for NFL, NBA and NHL, the minute for football). A game whose end cannot be told goes last, by start time.
6. A tap on a source **plays it at once**: the page needs one thing to hand to the play path per source.

## Rules from the screens

- The page opens at once from the last answer it has and refreshes behind it.
- A failing or slow add-on never blanks the page; "can't load" is only for no answer at all, with the reason in the log.
- Counts and text are short or wrap; nothing is cut off (DEC-050).

## Decided

Option B (sources under each game), closest to the end first, a tap plays at once (DEC-055). Not decided yet: the Upcoming, Leagues,
League and Game pages.
