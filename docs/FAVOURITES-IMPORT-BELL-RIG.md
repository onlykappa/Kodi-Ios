# Favourites import + anticipated-episodes bell: rig and device checklist

Code is in draft PR #29 (branch `claude/modest-hopper-8z5ar8`). Approved mockups: `docs/design/favourites-import-bell-mockups.html`
(boards G–J, DEC-047). **Nothing here has been seen in Kodi.** Host tests pass (`test_favourites_import.py`,
`test_favourites_flow.py`, `test_anticipated_bell.py`); no desktop rig or phone was available when this was written. Please render
with `python3 -B scripts/kodi_rig.py start` and label screenshots *desktop Kodi rig* (policy §9).

## 1. Bell on the show page (board G)
- Open a TMDb Helper TV show page (seasons view) that has an upcoming episode (e.g. a returning anime). A bare bell sits top right,
  opposite Back; no circle. Off = thick white outline with a black edge, on = solid white.
- Open a show with no upcoming episode (an ended show): **no bell** and nothing else moves. Leaving the page hides it again.
- Tap the bell: the choice sheet "New episodes · <show>" shows "Next: Season N · Episode N · Day D Mon" and two rows, **Alert me**
  and **Add to downloads automatically**, each with an On/Off tag. Tapping a row flips it and reopens the sheet; Cancel closes.
  The bell on the page fills white as soon as either is On.
- Season ⌄ Download sheet: exactly two rows (Full season, Choose episodes…). "Follow new episodes" is gone.
- Alert behaviour (host-tested only): an alert-only show is checked on app opening/foreground (existing cooldown), posts a
  Notifications message and a toast once per episode, and never searches or touches Drive. Alerts still fire if the Library
  automatic-download setting is off.
- **Known simplification:** the switches are rows with On/Off tags on the existing choice sheet (tap to flip), not iOS toggles, and the
  bottom button says "Cancel", not "Done". The mockup (G3) shows real switches; say if the owner wants a purpose-built sheet.
- **Needs the rig/phone to confirm:** that `Container(50).ListItem.Property(tvshow.tmdb_id)` is set on a TMDb Helper seasons page
  (the Download button already reads it), so `anticipated.bell_service` finds the show. If the bell never appears, that is the first
  thing to check (`kodi.log`: `bell_lookup_failed`).

## 2. Library > Favourites and import (boards H–J)
- Library page now lists Movies, TV Shows, **Favourites** (opens the Favourites page).
- Empty Favourites: star, "No favourites yet", an **Import a List** primary capsule.
- With favourites: All / Movies / Shows chips, then a toolbar row: **Import a List** (left, blue) and **Sort: <name>** (right, blue).
  Posters show `#rank` top-left (only while sorted by List order) and `3×` bottom-left when the list gave a watch count.
  Edit mode still shows the red remove badge top-right.
- Import a List → sheet (Paste a list / Choose a text file). Paste uses Kodi's keyboard (long-press paste on the phone); a paste that lost
  its line breaks still splits on the numbers. A progress dialog runs while titles are looked up; then the "Import finished" sheet:
  "N added to Favourites · M lines read" with rows **Duplicates**, **Needs your answer**, **Not found** (each with a count). Duplicates
  and Not found open a text view; Needs your answer opens one "Did you mean…" sheet per name (Cancel skips it).
- Test list: a numbered Notes list with ✅ ‼️ 🎥, "(STARTED)", "(3)", a trailing capitalised name, "dragon ball//Z//super" and a
  duplicate. Expect only names to be matched; "(3)" becomes 3×.
- Sort sheet: List order, Year, Name, List, Date added; the choice is remembered.
- Open: a show opens its seasons page; a movie stopped part-way asks **Continue Watching / Start Over**; a new movie goes straight to
  the app's "How would you like to watch" chooser.

## Not done / differs from the mockups
- No "Name this list…" step (the list is named from the file, or "Notes list <date>"); no share-sheet import from Notes (paste or a text file).
- The report is the choice sheet (counts + text views), not a full page; "Not found" has no search-by-hand button.
- J3 (a show's in-progress episode marked Continue) relies on the existing show page; nothing new was drawn for it.
- Up to 90 favourites show in the grid (was 36).
