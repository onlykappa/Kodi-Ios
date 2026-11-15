# Sports landing page: what it needs from the foundation

Read off the approved screens in [sports-approved-pages.html](sports-approved-pages.html) (DEC-054). It says nothing about
how any add-on works; that is the foundation's job. Every add-on will feed Sports eventually, so the page asks for **one
combined answer**, not one per add-on.

## The landing page shows

| On screen | Needs | When it is missing |
|---|---|---|
| Subtitle "Updated just now" | when the answer was last made (a time) | "Updating" while a refresh runs; "Not updated" after a failure |
| Live Now: "4 live" badge | number of games live right now | 0 means the tile goes grey and says when the next game starts |
| Live Now: "Football, Basketball and 2 more" | the sports with a live game, in a fixed order, plus how many more | omit the line when nothing is live |
| Upcoming: "Next at 7:30 PM, 9 more today" | the start time of the next game today and how many more today | "Nothing more today" |
| Leagues: "12 leagues" | number of leagues the add-ons list (the Leagues page lists every one, with or without games) | hide the number, keep the tile |
| Finished today: "6 replays" | number of games finished today that can be watched | hide the row when 0 |
| Refresh button (top right) | an action that asks for a fresh combined answer | |
| Can't load | one failure for the whole page (no add-on answered), with the reason kept in the log, not on the screen | plain words and "Try again" |

## Rules from the screens

- The page opens at once from the last answer it has (cached counts) and refreshes behind it; it never waits on a blank page.
- One slow or failing add-on must not blank the page: the answer is whatever the add-ons that did answer gave. "Can't load" is only for no
  answer at all.
- Text on the tiles never gets cut off (DEC-050): lines are short, or wrap; the foundation sends numbers and names, not sentences.
- Times are shown in the phone's own time zone.

## Not decided yet (do not build)

The pages behind each tile (Live Now, Upcoming, Leagues, a league, a game) and the tag order. Each is mocked up and approved first.
