# Handoff: Kodi iOS, PR #31 (branch claude/trusting-euler-kgug98)

Continue the owner's work on onlykappa/Kodi-Ios. Read AGENTS.md / CLAUDE.md first (UI work: docs/design/APPLE-UI-POLICY.md),
then ROADMAP.md, docs/PROGRESS.md, docs/ISSUES.md (newest entries ISSUE-333 to 340 near the top of the recent block),
docs/DECISIONS.md. Inspect the branch, recent commits and PR #31 before acting. Do not infer completion from chat.

## Rules (owner's, verbatim where quoted)
- Work only on branch `claude/trusting-euler-kgug98` (draft PR #31 to main) and push only there.
- "Every fix gets a docs/ISSUES.md entry (cause, fix, retest, test) and a test listed in .github/workflows/import-review.yml."
- Before every commit: `python3 -B scripts/check_project.py` (stray `.claude/worktrees` folders from old sub-agents make it
  report unexpected-file-type; those folders are not in Git), run every test listed in import-review.yml, delete stray
  `__pycache__` folders. `python3 -B scripts/check_ui_guidance.py` after UI-guidance changes.
- Check all UI in the desktop Kodi rig (`scripts/kodi_rig.py`: sync, restart, open PAGE args, shot NAME, builtin, rpc;
  xdotool taps on DISPLAY=:5). Keep screenshots out of Git. No text may be cut off (DEC-050). Kodi conditions use ![…],
  never !(…); never `$INFO[...]` inside a condition (use a bare infolabel as String.IsEqual's 2nd argument, ISSUE-333).
- Kodi list cells (itemlayout/focusedlayout) drop buttons (ISSUE-338).
- Never merge a PR or build/release anything without the owner's OK in the current request. The owner has approved:
  AirPlay framework builds for these fixes, and the IPA build for this round. Keep private data and model IDs out of commits.
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_018fd2YYLpBSJWiAokwPBzzz`.
- Pushes that touch `migration/airplay-ios/source-lock.json` or `build-airplay.sh` start an airplay-ios framework build that
  PUBLISHES the staged tag; a tag cannot be republished, so stage a new rNN for each native change.
- Releases: publish steps fall back to tagging the default branch on HTTP 403 (ISSUE-332); kodi-ios-portrait accepts
  `from_run` to publish an earlier run's executable without rebuilding.

## State at handoff
- Merged to main: PRs #24, #26, #28, #29 (owner asked "merge all pending prs").
- PR #31 commits: ISSUE-333 (show-page conditions), 334 (season row on a season's episodes page), 335 (AirPlay: quiet
  Drive read cut after 4 s, helper connections for slow sources, saved keyframe scan), 336 (TV stuck after a stall is
  played again then reloaded), 337 (out-of-order/missing prepared index repaired or served in segments; failed AVPlayer
  replaced on restart), 338 (Favourites picker search in place; "Most likely" badge as pill image), 339 (dubbed video
  prefers CC/SDH/dub captions), 340 (Umbrella cache wait stops early when it cannot finish).
- AirPlay r61 pinned (16f41999…17617, airplay-ios run 43731540855; host tests run 43730358862). r59/r60 never shipped.
- Kodi executable r33 pinned. IPA build 513 (from e9634c2, sha256 7993d7b0…5f01) published and checked: AirPlay r61 inside,
  the Python fixes inside. Sent to the owner with the test list below. (Earlier note: if a
  release `build-NNN` exists: verify (download, Kodi binary, AirPlay framework strings), record in docs/PROGRESS.md
  (commit with [skip ci]) and send the owner the link + test list below.
- Owner test list for this IPA: AirPlay a Drive copy (start, resume, subtitles on; Apple TV and Roku); no 20-30 s
  freezes; a second cast of the same file starts faster; a prepared episode that failed before (HEVC 10-bit) now plays;
  tapping a season keeps the season row and Back returns to the show; favourite show's Continue mark and the show
  bell; Favourites > Needs your answer: the "Most likely" badge and the search keeps the page; Umbrella opening time;
  a dubbed anime episode in English picks CC/SDH subtitles.

## Next (owner said "do 1-7")
1. Done in code (ISSUE-339). Still to do: when dubbed and no marked track exists, download a dub caption automatically
   at playback start (service side, needs the SubDL/OpenSubtitles keys the owner saved on the phone).
2. Speech check for subtitles (owner asked about it; get an explicit yes before building native code: iOS on-device
   speech recognition compares a few stretches of audio with candidate subtitles and aligns timing).
3. Save the keyframe scan while a download is prepared (kr_prepare), not only on the first cast.
4. Play on TV: show "Connecting…" with progress at once (owner pressed twice; log 53a92f39). UI change: policy + rig.
5. Done in code (ISSUE-340); confirm on the phone's log.
6. Next Episode across seasons (last episode of a season -> next season's episode 1; next_episode.py plan()).
7. Favourites search: fixed in code (ISSUE-338); confirm on the phone.
Also open: ISSUE-285 (waiting for an owner log after a Drive copy retry).

## Progress (2026-11-15, next session)
- Item 1 done in code: ISSUE-342 (`dub_captions.py`): a dubbed video with subtitles on and no CC/SDH/dub track gets a dub
  caption searched with the saved SubDL/OpenSubtitles keys, timing-checked and turned on, once per video (f1a00f1).
- Item 6 done in code: ISSUE-341 (`next_episode.py`): after a season's last aired episode, the next season's episode 1;
  after the show's last aired episode, a notice (f1a00f1).
- Item 4: mockup for owner approval, docs/design/play-on-tv-connecting-mockups.html (C: top banner, D: bottom pill; a
  second tap only shows the progress, Stop stops). Not built until the owner picks one.
- Item 3 (keyframe scan during kr_prepare): not started in code. The saved scan (kr_remux.c keyframe_cache_*) is keyed by
  the finished file's size, video track id and an FNV-1a hash of the exact mfra bytes; kr_prepare's write_mfra has those
  bytes and the final size, but the keyframe times must equal what kr_mp4_keyframes computes from the file (including
  both runs of a resumed preparation). Needs the AirPlay host tests (CI, or a host FFmpeg) and a new rNN tag + the owner's
  OK to build.
- Item 2 (speech check): waiting for the owner's explicit yes.

## Progress (2026-11-15, later)
- Owner chose mockup C and said yes to the speech check and to the keyframe scan during preparation.
- ISSUE-343 (AirPlay subtitles doubled and out of sync on the TV, log 1f143748): fixed in native code (MPEGTS:0, one
  cue per line drawn on layers). A host-test row shift it caused is fixed (`&fx[5]`).
- ISSUE-344 (AllDebrid refused ranged reads during an Umbrella cast, log a83e06c7): fixed in `remote_media.py`.
- ISSUE-345 (item 4): the Play on TV banner (mockup C) is built and checked in the desktop rig (landscape 1311x603).
- ISSUE-346 (item 3): the keyframe scan is saved while preparing, including resumed preparations (marks carry `kf`
  lines). Host tests passed in CI (run 43739879161: only the two `fx[4]` checks failed, fixed after).
- ISSUE-347 (item 2): the speech check is in code (`kr_speech.c/.m`, `speech_check.py`, wired into Download and apply
  and the dub captions). **Waiting for the owner's OK for the next framework build (r62)**, which must also change
  `build-airplay.sh` (pushing that file publishes the staged tag):
  - compile `"$REMUX/src/kr_speech.m"` like `kr_upscale.m` (`-fobjc-arc -fmodules -I"$REMUX/src"`) and add the object;
  - link `-framework Speech`;
  - add `_kodi_speech_words`, `_kodi_speech_authorize`, `_kodi_speech_state` to the exports list and to the `nm`
    export check (its count goes up by three).
  ISSUE-343 and ISSUE-346 are native too and ride the same build.
- Log a83e06c7, still open with the owner: which cast was audio-only (08:21 copied HEVC 10-bit to the Apple TV; an
  Apple TV that cannot show HEVC Main10 would play only the sound), and a screenshot of the "weird screen".
- AirPlay r62 pinned (6c5a441a…e349, airplay-ios run 43744491417 from c09d2f1). IPA build 528 (from 4b98b12, sha256
  07f2c97d…0a5b) published and checked: r62 inside (byte-identical), speech_check.py, the banner, the problem sheet,
  the Roku banner and NSSpeechRecognitionUsageDescription inside. Sent to the owner. Waiting for phone results, a Roku
  cast log and a log of a sound-only cast on the Apple TV 4K.
