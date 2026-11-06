# UI session progress: library tools, header buttons, Customisation (updated 2026-11-06)

This session's own progress file, so it does not touch `HANDOFF-PROGRESS.md` (the build session's). Commits use
`[skip ci]`. No builds are started here: the other session is building 174 with converter r21.

## Branches
| Branch | Based on | State |
|---|---|---|
| `fix/elementum-cloud-164` (PR #13) | — | The four library-tools pages are built here. **Not started in code yet.** |
| `design/customisation-mockups` | rebased onto `fix/elementum-cloud-164` (7cf3643) | Round-4 Customisation mockups and round-5 header-buttons mockups. Pushed (4420307). No PR. |
| `feature/customisation-header-buttons` | rebased onto `fix/elementum-cloud-164` (7cf3643) | Work in progress: header buttons (gear, refresh, bell arc). Pushed (0ee8aca). No PR. |

## 1. Library tools (spec `docs/design/library-tools-spec.md`, mockup `library-tools-mockups.html`)
Spec, its two traps and `APPLE-UI-POLICY.md` (on `design/apple-ui-guidance`, not on this branch) are read.
Code read: `library_page.py`, `library_status.py`, `transfers_page.py`, `transfers.py`, `transfer_history.py`,
`prepare_downloads.py`, `debrid_drive.py`, `airplay.py`, `cast.py`, `pages.play_on_tv`, `notifications.py`.

| Page | State | Plan |
|---|---|---|
| Phone space | not started | Tap the Phone space card on Library status. Reuse `library_status.places/usage`, measured in a thread. Clear (yes/no first) for artwork cache, Elementum leftovers and temporary files. Never touch a file Elementum is still downloading or a preparation working folder in use. |
| Queue (Edit order) | not started | Library status › Waiting folder › "Edit order". New `up` / `down` requests applied in `apply_to`, which reorders the waiting videos by giving them `priority = now - rank`. They are not in `interrupts()`, so the running conversion is never stopped. `request()` must keep repeated up/down taps (it currently keeps one request per video). "Downloading to Google Drive" comes from the `debrid_drive` jobs. |
| History | not started | Transfers › "History" (top right). `transfer_history.FINISHED` raised, 30 days kept. Failures added from `prepare_downloads` (`error`) and `debrid_drive` (`failed`, `error`). Today / Yesterday / 7 days, week totals. |
| AirPlay check | not started | Play on TV sheet › "Last time", and a tap on an AirPlay notification (opened directly from `notifications.py`). The last session's KodiAirPlay lines are kept in a small JSON file by `cast.send_airplay` and `airplay.relay`. The steps are read from them: `client:` (third-party TV or Apple TV), `master:` CODECS/RESOLUTION, `prepared:` / `compat:` (converted to H.264), `GET /video/seg… 200` (the TV asked for video), and `player:` ready / could not open / external playback ended / closed. The sheet is landscape (1080i), so this page needs a 1080i layout as well as the portrait one. |

Rules to keep: window files added while Kodi runs need the `RuntimeError` → `xbmcvfs.listdir` → retry once pattern
(`transfers.run`). Use one item layout per list, with parts shown by `ListItem.Property`. Every control at least
118 units. Back is `nav_button`. Tests like `scripts/test_transfers.py`. Run every `scripts/test_*.py` and
`check_project.py` before pushing.

## 2. Header buttons (round 5, owner picked option A)
- Mockup done: bell with an unread count and a thin busy arc, a gear in place of the profile picture (opens Settings), and refresh on Home, Movies and TV. The gear was cleaned up at the owner's request: rounded teeth and a centred hole, the same shape for the mockup SVG and the Kodi texture (`portrait.gear_outline`).
- Policy changes made: Kodi-drawn buttons are called "glass-styled", never Liquid Glass. Back stays the bold chevron with no circle (ISSUE-099), although the mockup the owner approved showed a circle. **Waiting for the owner** on that.
- Code in progress (`feature/customisation-header-buttons`): textures `hdr_gear.png`, `hdr_refresh.png`, `ring_arc.png`; `header_buttons()`, `gear()`, `refresh_button()`, `refreshed_toast()` in the hubs and `page_header`.
- Open:
  - The glyph size (52) must follow policy §5.5 (46 for button glyphs, 104 for navigation glyphs).
  - The More menu entries Settings lacks (Favourites, Check for updates, iPhone navigation / recovery) need a home in Settings.
  - `test_portrait.py` has one failure and takes 268 s on that branch, probably from the gear rasteriser (a polygon test per sub-sample). Speed it up and fix the failure.

## 3. Refresh rows (Home / Movies / TV): designed, not coded
- One page number per tab in `Skin.String(Portrait.Page.<tab>)`. TMDb Helper rows and the hero load `&page=N` (TMDb Helper's own `page` parameter). Continue Watching, Up Next and library rows never change.
- The script `refresh_rows` moves to the next page (or a random one, as a setting). It turns off that tab's listing-cache flags so the new page shows at once, and the service then caches the new page (`ios_cache` keys use the path without `&page=`).
- The button spins while the rows load, then "New picks on <tab>" shows.

## 4. Customisation pages (round 4): mockups approved, not coded
15 screens in `customisation-mockups.html`, mapped to Fuse's settings (Custom_1115/1116/1118 item lists, Skin
Variables `buildviews`, SkinSettings categories).

## Order of work
1. Library tools, the four pages on `fix/elementum-cloud-164`, with tests.
2. Header buttons and refresh rows, after the owner decides on the back-button circle.
3. Customisation pages.
