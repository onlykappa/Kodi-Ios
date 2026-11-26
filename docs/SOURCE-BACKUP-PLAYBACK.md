# Backup transport and playback (roadmap step 7)

Code: `migration/bundled-bootstrap/resources/lib/backup_playback.py`; tests `scripts/test_backup_playback.py` (16 tests, host only: a loopback HLS server, a fake player and generated torrent bytes).

**HTTP / HLS.** `Playback.start` calls `fresh_resolve.play_ready` (fresh link, whole chain checked), then the player's `play(url, headers, resume)`, then waits until playback time advances by 1 s (20 s limit). Failing to advance is `timeout` and the player is stopped. `KodiPlayer` is the real adapter: headers appended as `url|Header=value` (the form the app already uses), resume through the `StartOffset` property. Inputstream properties are not set: the existing HLS path plays without them and this step adds none.

**One session.** The same request started twice is a no-op (`duplicate`, one `play` call). A different request stops the first. `stop()` from any thread, or `cancel`, before the player was started means it is never started (tested: stop and cancel while resolving leave zero `play` calls); after it started, the player is stopped exactly once.

**Torrent.** The candidate's hash must equal the magnet's `btih` (hex or base32), and a supplied `.torrent` file's info-hash (SHA-1 of its `info` dictionary, computed here); a mismatch is `unsupported` and nothing is sent. The candidate goes to the injected route, which in the app is the existing Elementum route (`elementum_cloud.route`, reached through `elementum_download`, which asks the torrent prompt first). A Stream request is never turned into a download. No VPN detection or traffic setting was added; the existing prompt and its hint are unchanged. A declined or refused route is `refused`; cancel sends nothing.

**Not done.** It is not called by the picker or `provider_fallback_hooks.dispatch` (which still plays and queues as before): connecting it is step 8. Nothing here proves the iOS Elementum engine, receiver behaviour, AirPlay, inputstream, real resume or duplicate-player behaviour in Kodi, and PR #55's VPN work is not coordinated with in code. No device evidence.
