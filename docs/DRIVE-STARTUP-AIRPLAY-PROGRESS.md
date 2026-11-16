# Downloaded Drive startup and AirPlay investigation — 2026-11-16

Status: investigating, source fixes only. Branch: `fix/drive-startup-airplay-evidence`,
base main `222cd50`. One agent. No IPA, native release, publication or merge authorized.

## Scope and evidence rules

Investigate downloaded movie/TV Play → first picture first, preserving downloaded-first and resume.
Then investigate audio-playing AirPlay load failure, distinguishing receiver/video evidence from
state-machine inference. Raw supplied log, accounts, signed URLs and media stay outside Git.
Host fixtures and desktop Kodi are never iPhone/TV proof; comparable measured timings only.

## Checkpoint 1 — repository inspection

- Read AGENTS.md; reviewing ROADMAP, PROGRESS, ISSUES, DECISIONS and code.
- PR #32 merged 2026-11-15 (head `315ef79`); verify deployed source versus log separately.
- Open PRs #31 and #33–43 include unrelated subtitle/sports work; preserve those branches.
- Latest published IPA at inspection: build-557, 2026-11-16 15:47 UTC. Installed build pending log analysis.
- Native release list includes AirPlay r64 and portrait r33; main pins and installed pins pending.

## Validation and remaining checks

Pending: baseline measurements, focused regressions, available real Kodi rig tests, native tests,
`python3 -B scripts/check_project.py`, source review and draft PR. Device first-picture and actual
receiver playback/recovery checks require device evidence and remain explicitly unverified.

## Checkpoint 2 — downloaded playback findings and source fix

Installed build is **554**, source `7645171` on `claude/sports-jet`, run 43890669506;
AirPlay r64 (`5c122167…a028`), Kodi portrait r33, Glassbar r6. Main is older:
AirPlay r58 (`1bff47f3…c331`), same portrait/Glassbar. #32 and Umbrella repairs are
merged through main; their provider/cache route is bypassed by this completed Drive fast path.
Unmerged #42 fixes a startup-service syntax error on main; it is unrelated and not silently imported.

Supplied log (phone wall clock): Play-sheet tap 07:47:20.791; completed-copy handoff
21.275; OpenFile 21.312; demux 22.673; stream codecs 23.980; misleading streams-ready
line 24.009; decoded picture queued 24.959; fullscreen 24.976. Thus tap → decoded
picture queue **4.168 s**, not the logged 3.2 s. Actual display scanout is not logged.
Lookup/handoff is 0.484 s; InputStream 1.361 s; demux/probe 1.307 s; decoder/render
startup approximately 0.98 s to queued picture. These intervals overlap network work;
authentication versus each metadata/range read cannot be separated from this old log.
No comparable TV-episode/cold/warm device pair exists in the attachment.

Concrete source defect: first index range waits for an optional second live identity
request and cache disk write before returning already fetched bytes. Proxy now admits
indexes in bounded background work (two jobs, deduplicated per file). No unvalidated
index becomes reusable; changed identity, disk failure and failed reads preserve ordinary
streaming. Downloaded lookup, selected file, resume, codecs, tracks and seeking unchanged.
Safe auth/header timings added without addresses or identifiers. Streams-ready logging
now says first picture is not measured; native source adds a first-frame-render-submission
marker. **Native pin unchanged; renderer marker requires a future approved build.**

Comparable loopback HTTP fixture, five fresh-proxy repetitions per mode, 200 ms per
metadata response, identical 195-byte synthetic file and index range: synchronous cold
median **0.4098 s**, deferred cold **0.2021 s**; warm **0.00108 / 0.00137 s**. This
isolates removal of one optional metadata wait; it is not a device startup improvement.
25 index tests, 25 proxy tests and 9 timing tests pass. Required project scanner passes.
Original rig setup failed (no sudo); isolated desktop runtime setup continues.
