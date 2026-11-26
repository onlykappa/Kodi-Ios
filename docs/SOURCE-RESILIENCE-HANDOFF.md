# Source resilience: regression review and handoff (roadmap step 15)

Branch `codex/source-resilience-roadmap`, PR #56 (draft), reviewed at commit 5222ee9 plus the follow-up commit that adds this file. The PR title and description still say "documentation-only, implementation 0/16"; that is no longer true (see below) and is the owner's to update.

## What exists (all host-tested; none of it is in an IPA)
| Step | What | Doc |
| --- | --- | --- |
| 3 | licensed source baseline, offline restore, owner decisions | SOURCE-PRESERVATION-STEP3.md |
| 4-6 | typed contract, first-party search, fresh resolution with header/cookie continuity | SOURCE-BACKUP-CONTRACT.md, SOURCE-INDEPENDENT-SEARCH.md, SOURCE-FRESH-RESOLUTION.md |
| 7-8 | one-session playback hand-off, torrent hash check, picker policy | SOURCE-BACKUP-PLAYBACK.md, SOURCE-FALLBACK-POLICY.md |
| 9 | ten site families (five parsed from real captured pages) | SOURCE-COVERAGE.md |
| 10 | Sports: unique current game match, live start rules | SOURCE-SPORTS.md |
| 11 | source health: cooldowns, Retry-After, one Notifications line | SOURCE-HEALTH.md |
| 12 | build from preserved inputs by digest, no runtime code downloads | SOURCE-PACKAGING.md |
| 13 | outage / correctness / privacy matrix (25 scenarios) | SOURCE-RESILIENCE-MATRIX.md |
| 14 | desktop rig run and timing | SOURCE-PERFORMANCE.md |
| 17-20 | own AllDebrid sign-in, direct peer-to-peer route, peer rules, metadata outages | SOURCE-DEBRID-ACCOUNT.md, SOURCE-DIRECT-STREAM.md, SOURCE-P2P-RULES.md, SOURCE-METADATA.md |

Issues: ISSUE-488 to ISSUE-495 (seen / cause / fix / retest). Progress: docs/PROGRESS.md (2026-11-26 entry). Roadmap table: docs/SOURCE-RESILIENCE-ROADMAP.md.

## Results at this commit
* `python3 -B scripts/check_project.py`: 0 issues. `python3 -B scripts/check_ui_guidance.py`: no problems. `__pycache__` removed before each commit.
* All 255 test files listed in `.github/workflows/import-review.yml` were run under Python 3.11 (4 in parallel). **Passed:** all except one run of `test_backup_playback.py`, which failed because the guarded-HLS change (ISSUE-489) legitimately changed what the player receives; the test (and the same assertion in `test_sports_match.py`) was updated and both pass. Known flakes, not explained: `test_stream_loop` sometimes fails when run in parallel and passes alone; `test_umbrella_recovery` printed OK and then segfaulted at interpreter exit once under load (no repeat in 16 further runs, with and without this branch).
* Step 13 matrix: 25 scenarios plus a leaked-thread check, all pass; step 14 rig run: five cases with the clock advancing.
* Every new test file is registered in `import-review.yml` (a fixture module, `fixtures_independent_sites.py`, holds no tests). Many older test files in `scripts/` are not in that workflow (they were not added by this work).

## Not tested / not done
The phone; real AllDebrid (sign-in, errors); real swarms and the iOS Elementum engine (the rig torrent case is a libtorrent plus gateway stand-in on a loopback seed); Crew's own remote modules at run time; any film opened end to end from a search result; Sports screens calling `sports_match`; any on-screen control for the new routes (AllDebrid sign-in, "Stream directly", the peer status line, a stale-metadata hint); a full IPA build with upstream hosts blocked (needs the macOS toolchain); the portrait boards comparison (no layout changed). Sites, TMDb and ESPN were live only at the captured moment, 2026-11-26; 1337x, Torlock, TorrentProject2 and Torrentz2 could not be captured from the container.

## Review checklist
* **Licenses.** All new modules are first-party (this repository's licence); no CocoScrapers or Burst code was copied; page layouts were read from live pages and the adapters written from them. `libtorrent` and `ffmpeg` are used only by the rig script (not shipped). Third-party package rights are as in SOURCE-PROVIDER-RIGHTS-REVIEW.md and the step 3 decisions (private preservation, not a redistribution clearance).
* **Dependencies.** The new modules use only the Python standard library. The loopback HLS proxy already in the app (`sports_hls_proxy`) is reused; its `requests` import is avoided by `hls_bridge.Session`.
* **Cancellation.** A cancel never advances to another source, is never recorded in health, starts nothing late, and closes the player and the proxy (matrix, test_backup_playback, test_direct_stream, test_p2p_rules).
* **Secret redaction.** No log line, notice, health file or report carries a key, link, header or magnet (matrix privacy rows; `Resolved` hides its link; `scrub()` for logs); the key lives only in the phone's profile folder.
* **Forbidden traffic.** A tripwire recorded zero non-loopback connections from the search and fallback paths during the matrix; offline behaviour was tested in a real network-less namespace, not a fixture firewall. No VPN or network setting is touched, and direct torrenting only happens after the existing prompt.
* **Remote work preserved.** No force-push; main was merged into the branch; the PR stays draft.

## Update 2026-11-26 (add-on backup pass)
Full suite of 261 registered tests, 4 in parallel: everything passed except `test_sports_stream_health.py`, which printed its normal OK (28 tests) and then the interpreter segfaulted at exit once; it passed 3 of 3 reruns alone. This is the same behaviour seen once earlier in `test_umbrella_recovery.py`: Python 3.11 in this container crashing at exit under parallel load after a finished test run, not a failing assertion. It is recorded, not explained. `check_project.py` 0 issues, `check_ui_guidance.py` clean.
