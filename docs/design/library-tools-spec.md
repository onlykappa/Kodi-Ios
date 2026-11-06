# Library tools: Phone space, Queue, History, AirPlay check

Owner-approved 2026-11-06 ("these look great"). Mockup: `library-tools-mockups.html` (also
https://claude.ai/artifact/3ajZJDwzALocLDJ4xxwE8n). Built 2026-11-06 on `claude/trusting-euler-kgug98` (based on `fix/elementum-cloud-164`); see "Built" at the end. Build on `fix/elementum-cloud-164` (PR #13), not
`main`: Library status, Transfers, `transfer_history` and the details sheet only exist there.

Read `docs/design/APPLE-UI-POLICY.md` first. Kodi skin XML generated in Python like `library_page.py` and
`transfers_page.py`; every control at least 118 units (44 pt); reuse `portrait.py` helpers (`label`, `image`,
`surface`, `nav_button`, `pill_button`, SURFACE/SURFACE2/GREY/SEP tokens).

Two traps found on device:
- A window file added while Kodi runs is "missing" until Kodi's directory cache is refreshed. `portrait.refresh_skin`
  now lists the folder after writing; a page's `run()` should still catch `RuntimeError` on construction, list the
  portrait folder (`xbmcvfs.listdir`) and retry once (see `transfers.run`).
- Kodi picks among conditional itemlayouts globally, not per item: one layout per list, parts shown by `visible` on
  ListItem.Property.

## 1. Phone space (removed by the owner, build 173)
- Opened from Library status: tap the "Phone space" card (today it is display-only).
- One bar: what Kodi keeps on the phone. Rows: Artwork cache, Elementum leftovers, Temporary files (each with
  Clear), Add-on data and the Kodi app (Keep, no button).
- Measure in a thread; Clear asks once (yes/no), then refreshes the numbers. Never touch a file Elementum is still
  downloading or a preparation working file in use.

## 2. Queue (Edit order)
- Opened from Library status › Waiting folder › "Edit order" at the top.
- "Converting now" (fixed on top), "Up next" in order with ▲ ▼ buttons (118 units each; no drag on iPhone),
  "Downloading to Drive" (AllDebrid jobs) as its own list.
- Order is `job['priority']` in `prepare_downloads` state. Write through `prepare_downloads.request(profile,
  action, id)` with a new action (e.g. `up` / `down`) applied in `apply_to`; the page never writes the queue state
  itself. Moving a waiting item must NOT interrupt the running conversion (`prepare_downloads.interrupts` only
  stops for `next` / `keep`; storage-free conversion cannot resume).

## 3. History
- Opened from Transfers › "History" at the top right. Open question to the owner: also a row on Library status?
- Today / Yesterday / 7 days switch; each finished job with size, time taken, average speed; failures with their
  reason; week totals at the top. Keep 30 days.
- Source: `transfer_history` already keeps `finished` (kind, title, start, end, peak, avg, size; newest 20). Raise
  the cap and keep 30 days; add failures from `prepare_downloads` jobs (`error`) and `debrid_drive` jobs.

## 4. AirPlay check
- Opened from the Play on TV sheet › "Last time", and by tapping an AirPlay notification.
- The last Play on TV as steps: which TV, whether the picture had to be converted, whether the TV asked for the
  video, how it ended; then what to try.
- Source: the KodiAirPlay log lines the service relays into kodi.log ("Kodi iOS AirPlay: ..."); keep the last
  session's lines in a small JSON in the bootstrap profile when they are relayed (`airplay.relay`).

## Process
Tests like `scripts/test_transfers.py` (page XML, 44 pt, every property set, fake-Kodi navigation). Run every
`scripts/test_*.py` and `python3 -B scripts/check_project.py` before pushing. Commit with `[skip ci]`; builds are
started by hand (`import-review.yml`). No merge or release without the owner.

## Built (2026-11-06, not yet on a device)
| Part | Where |
|---|---|
| What each page shows (pure, tested) | `resources/lib/library_tools.py` |
| Page XML (portrait; AirPlay check also 1080i) | `resources/lib/library_tools_page.py`, registered in `portrait.py` |
| Controllers | `resources/lib/tool_windows.py`; `RunScript(service.kodi.ios.bootstrap,tool_pages,<queue/history/airplay>)` |
| Queue order | `prepare_downloads` `up` / `down` requests, `queue_order`, `apply_to` (line numbered `now-1-rank`, so a Prepare next of the same moment still wins); `request()` keeps every up / down tap; `interrupts()` unchanged. Library status's Waiting order now breaks ties by job key, as `prepare_cloud` does. |
| History data | `transfer_history.FINISHED` 400, 30 days; `transfer_history.failed()` / `failures()` (own file) from `prepare_cloud`, `prepare_downloads` and `debrid_drive` |
| AirPlay data | `library_tools.begin_airplay` / `note_airplay` (`airplay-last.json`), fed by `cast.send_airplay` and `airplay.relay(keep=...)` |
| Entry points | Library status: "Edit order" (Waiting folder, top right); Transfers: "History" (top right); Play on TV sheet: "Last time" (once there has been an AirPlay session); Notifications: an AirPlay message opens the check instead of its details sheet |
| Tests | `scripts/test_library_tools.py` |

Owner review (build 173, previews): Phone space removed, page and the card on Library status ("everything is in
drive"); ▲ ▼ larger and centred (128 px chevron centred in its texture, 68 in a 104 circle); one close button
everywhere (`portrait.close_button`, `pages.close_button_1080`: smooth 128 px circle, larger 128 px cross); titles fit
(the AirPlay check's large title is "AirPlay check", the video's name scrolls on the line under it).
Still open for the owner: History also as a row on Library status?
