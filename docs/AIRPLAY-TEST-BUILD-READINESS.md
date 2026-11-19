# AirPlay remaining host work and device gate — 2026-11-18

## Empty audio (step 3)

ISSUE-375 is unresolved. `gm_stream.c` reports an empty segment when the
selected demuxer writes no packets in the requested window. This symptom
does not distinguish EOF, source read interruption, stream selection or
timestamp/seek behavior. Previously recorded 27-segment long-fragment and
transient-read tests did not reproduce the repeated phone failure. No new
production retry or timestamp change is justified by those results alone.

To reproduce the exact failure, retain an authorized source locally or provide
an independently reproducible sample preserving container fragmentation,
selected audio stream and timestamps around the failed segment windows.
Useful sanitized metadata: codec/profile, stream indices/time bases, start
times, packet PTS/DTS/duration and keyframes near the affected position,
whether the copy is complete, and whether failure occurs locally or only
through Drive. A fresh log should include the request preceding the first
empty segment and the selected audio track. Never commit raw media, source
URLs, headers, account information or unredacted logs. Owner testing can wait
until home; these are requirements for a future exact reproduction.

## Position retention (step 4)

The local controlled history suite passes 22 cases, including completion,
replacement, final position and deliberate zero rewind. This establishes the
local Python history behavior, not Kodi library/provider synchronization or
AVPlayer behavior after an actual receiver stall. Those remain device gates.

## Validation (step 5)

The latest controlled native callback run44384291944 passed. Original native
run44379604495 compiled sourcef4c8e44 successfully; its host dependency-install
failure is under retry. Tracing source789a3e3 has not independently passed a
full new iPhone framework compilation. All181 registered local import check/test
commands passed in the current tree; macOS-only tests skip on Linux and must
not be counted as native execution. The controlled callback has separate macOS
pass evidence. Native host run44379604495 failed again in FFmpeg fixture
dependency installation, before tests ran; this remains an infrastructure
blocker, not a passing host suite or a diagnosed playback regression.

## Concrete test-build recommendation (step 6)

Do not dispatch an IPA from the current r65 pin and expect the recovery fixes.
The previously inspected95bb0d2 candidate predates compatibility recovery and
tracing. Choose one final source revision after remaining host failures are
resolved, compile it, verify the exact archive/binary hashes, iPhoneOS platform
and exports, then obtain owner approval for immutable framework publication,
pin update and the test IPA. Keep PR46 draft; no merge is authorized.

The test build should contain the range-refusal retry-budget repair, local
history/ownership fixes, ready→owned seek→play recovery changes and transition
diagnostics. User-pause intent remains unimplemented and must be explicitly
identified as a test limitation; do not claim reliable pause recovery.

When authorized and the owner is home: measure time to first picture, watch
sustained playback, seek both directions, pause/resume during a buffer/recovery,
close AirPlay after a stall, reopen from Continue Watching, test a deliberate
rewind to zero, and replace the video. Export the log afterward. Actual TV
results, controlled fixtures, local history and native compilation are separate
evidence classes. No build/release is authorized by this document.
