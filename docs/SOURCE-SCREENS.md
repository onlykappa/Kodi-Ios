# New screens for the source-resilience routes (steps 17 to 19)

Evidence class: **desktop Kodi 21.3 rig** (Apple UI policy section 9), 2026-11-26. Not the iPhone: no touch, safe areas, SF font or native tab bar. Screenshots show film artwork and stay in the rig folder (`shots/screen-*.png`), not in Git. Script: `scripts/rig_screens.py` (fake sign-in code; no request goes to AllDebrid). Tests: `scripts/test_signin_screens.py`.

Policy followed: no new layout or renderer; everything reuses what the app already draws (Accounts rows, the choice sheet, Kodi's question and progress boxes, the Notifications list). Wording is plain and short; raw errors stay in the log; nothing is cut off.

| Screen | Where it comes from | What it shows |
| --- | --- | --- |
| Accounts, new **AllDebrid** row | `accounts.SERVICES` (the page builds its rows from it) | amber cloud tile, "Not signed in" / "Signed in", Sign In button; tapping a signed-in row opens the sign-out sheet |
| **Sign in to AllDebrid** | the choice sheet (`debrid_signin_ui.py`, `debrid_signin_page.py`) | "Waiting for you to enter the code", the code spaced as "A B C D", "Enter it at alldebrid.com/pin on any device. It works for 10 minutes.", Cancel. The sheet closes by itself when the key arrives; a short Notifications line says "AllDebrid is signed in" |
| **AllDebrid** (signed in) | same sheet | "Signed in on this phone", a Sign out row ("Removes the key from this phone. If Umbrella has a key, that one is used."), Done |
| **Stream this torrent directly?** | the existing torrent prompt with a stream variant (`torrent_prompt`) | three lines of body, the VPN hint in bold, Cancel (default) and "Stream anyway" ("Stream" when a VPN looks active). Download wording is unchanged |
| **Streaming from peers** | Kodi's own progress box, skin-styled, with its Cancel button | "Waiting for peers · 54 s" counting down, a progress bar for the wait, Cancel ends the wait and never moves on to another swarm |

Failures use one Notifications line with one next step (for example "AllDebrid could not be reached. Check your connection and try again.").

## Found on the rig while building them
* The stream prompt first read "AllDebrid is not answering right now. This would stream ..." and Kodi's question box clipped its first lines (and its button). Shortened to fit (three lines); a test caps the body length.
* **The existing, owner-approved "Download this torrent directly?" prompt is also clipped on the rig**: its first line is cut and its button reads "Download any...". I did not change it (approved wording); it needs a decision: shorten it the same way (about 90 characters of body, a shorter button) after a phone check, since the phone may draw it differently.
* The Home page and TMDb rows rendered normally with the new modules present.

## Not done
* The code row on the sign-in sheet shows a chevron like every sheet row, but tapping it simply cancels (a sheet row cannot be inert). A mock-up round for a read-only row is the proper fix.
* The "Stream directly" prompt only appears after debrid is marked unavailable (three failures) or when the person has no key; there is still no manual "Stream directly" choice on a source row.
* The stale-metadata hint was not built (only the `metadata` field exists).
* None of this was looked at on the iPhone; the policy's mock-up comparison (boards) was not run for these screens.
