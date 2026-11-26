# Direct peer-to-peer stream route (roadmap step 18)

Code: `migration/bundled-bootstrap/resources/lib/direct_stream.py`; hooks in `elementum_cloud.route` and `provider_fallback_hooks.dispatch`; `Playback.start_resolved(..., wait=)` in `backup_playback.py`. Tests: `scripts/test_direct_stream.py` (12 tests, host only: fake player, fake prompt, fake Home window).

**What it does.** The app normally sends a chosen torrent to AllDebrid and Google Drive: `elementum_cloud.route` intercepts Elementum's `/play`. When debrid is unavailable (step 17: three service-level failures in a row, still cooling down), a torrent Stream picked from the fallback picker (`dispatch`) now goes to peers instead of being refused: the person is asked with the existing torrent prompt (its VPN hint, Cancel by default), then Elementum's own play URL (`plugin://plugin.video.elementum/play?uri=magnet:...`) is handed to the player through `Playback`, which waits up to 90 s for the picture to really move (a direct link gets 20 s; step 19 refines the wait) and then stops or cancels like any other session.

**Guards.**
* Only a verified torrent: the info hash must equal the magnet's, and the title, year or episode must pass the same strict check as every candidate; a link that is not a torrent, a wrong title or a zero-seeder torrent never streams.
* Only when debrid is the worse choice: unavailable, no key at all, or `force=True` (the person asked). A working debrid keeps the old route and the old refusal.
* Never silent: the prompt must be accepted (a decline is `refused`, nothing starts); a cancel after the prompt starts nothing.
* A Stream never becomes a Drive download, and nothing touches VPN or network settings (PR #55's work is not duplicated).
* Approval is a one-time, 2-minute grant on the Home window for exactly that info hash. `elementum_cloud.route` lets that one request through to Elementum and spends the grant; a retry, another torrent or a stale grant goes back to the debrid route (tested).
* No peers: `timeout`, the grant is revoked and the player stopped. The same torrent twice is one session.

**Not done.** `dispatch` only reaches this path once debrid is marked unavailable; a person cannot yet choose "Stream directly" on screen (it needs a UI design under the Apple UI policy and a rig look, planned for the end). Not tested against the iOS Elementum engine, real swarms, background suspension or speed: this sandbox cannot reach swarms, so those need your phone. No device evidence.
