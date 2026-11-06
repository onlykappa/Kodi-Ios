# UI session progress: library tools, header buttons, Customisation (updated 2026-11-06, second session)

This session's own progress file, so it does not touch `HANDOFF-PROGRESS.md` (the build session's). Commits use
`[skip ci]`. No builds are started here: the other session is building 174 with converter r21.

## Branches
| Branch | Based on | State |
|---|---|---|
| `fix/elementum-cloud-164` (PR #13) | — | Base for the library tools. |
| `claude/trusting-euler-kgug98` | `fix/elementum-cloud-164` (c5e9eb6) | Library tools (Queue, History, AirPlay check), built and tested (second session took over here); merged into PR #13. No build started. |
| `design/customisation-mockups` | rebased onto `fix/elementum-cloud-164` (7cf3643) | Round-4 Customisation mockups and round-5 header-buttons mockups. Pushed (4420307). No PR. |
| `feature/customisation-header-buttons` | rebased onto `fix/elementum-cloud-164` (7cf3643) | Work in progress: header buttons (gear, refresh, bell arc). Pushed (0ee8aca). No PR. |

## 1. Library tools (spec `docs/design/library-tools-spec.md`, mockup `library-tools-mockups.html`)
Spec, its two traps and `APPLE-UI-POLICY.md` (on `design/apple-ui-guidance`, not on this branch) are read.
Code read: `library_page.py`, `library_status.py`, `transfers_page.py`, `transfers.py`, `transfer_history.py`,
`prepare_downloads.py`, `debrid_drive.py`, `airplay.py`, `cast.py`, `pages.play_on_tv`, `notifications.py`.

| Page | State |
|---|---|
| Queue (Edit order) | built: `up` / `down` requests, `queue_order`, page, Library status › Waiting › "Edit order" |
| Phone space | removed by the owner (build 173): page and Library status card |
| History | built: `transfer_history.failed()` from prepare_cloud / prepare_downloads / debrid_drive, 30 days, Today / Yesterday / 7 days, Transfers › "History" |
| AirPlay check | built: `airplay-last.json` from `cast.send_airplay` and `airplay.relay`, portrait page and 1080i sheet, Play on TV › "Last time", AirPlay notifications |

Details and the safety rules are in the "Built" section of `docs/design/library-tools-spec.md`. Merged into PR #13 at the owner's request; check the pages on a device build.
Also done: one close button everywhere (larger cross, smooth circle), larger centred ▲ ▼, titles that fit.

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
1. ~~Library tools, the four pages, with tests~~ (done on `claude/trusting-euler-kgug98`; device check pending).
2. Header buttons and refresh rows, after the owner decides on the back-button circle.
3. Customisation pages.

## After build 174 (merged into main)
- Owner: Back stays the bold chevron with **no circle**. Header buttons (gear, thin bell arc, refresh on Home/Movies/TV)
  are unblocked: rebase `feature/customisation-header-buttons` onto main and finish it (glyph sizes, test_portrait speed).
- The Home / Movies / TV refresh ("new picks") is designed (section 3) but not coded; not in build 174.

## Ready for build 175 (branch `claude/trusting-euler-kgug98`, not on main yet; owner testing 174 first)
- Header buttons (round 5, option A): gear (opens Settings) instead of the profile picture, thin busy arc on the bell,
  refresh on Home / Movies / TV, glyphs 46 (policy §5.5). Back unchanged (no circle, owner's answer).
- Refresh: `refresh_rows.py` moves the tab to the next page (2..5, then 1) in `Skin.String(Portrait.Page.<tab>)`,
  turns that tab's copies off, waits for the rows, then "New picks on <tab>". Rows and hero: cached copy, else the live
  list at that page, else the plain list. Copies keep their key without the page (`ios_cache.unpaged`); the service
  copies the new page (`cache_lists(..., page)`). Continue Watching, Up Next and library rows never change.
- Settings gets the More menu's rows: Google Drive, Favourites, Check for updates, iPhone navigation / recovery.
- test_portrait: the gear texture is drawn once and only its teeth band uses the polygon test (same pixels); 109 s, all pass.
- Tests: `scripts/test_header_buttons.py`; listing-cache and performance tests updated for the page value.
