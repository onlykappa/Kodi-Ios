# Build 196: AirPlay startup expires before the server is ready

Owner device log reviewed on 2026-11-08, branch `claude/trusting-euler-kgug98`, PR #16.
The owner confirmed Local Network access is enabled, requested fixes and a new IPA, and clarified that playback
must continue with the screen locked. Native verification/release and the IPA build are authorized. The raw log
and private media identifiers remain outside Git. Times below are the log's local times.

| Log lines | Device evidence |
|---|---|
| 888, 891 | Attempt starts at 20:21:48.476; native source startup follows at 20:21:49.000. |
| 892 | Python reports `unreachable` after 15 seconds, at 20:22:03.578. |
| 917, 920 | Second attempt starts at 20:22:48.734 and gets the same outcome at 20:23:03.843. |
| 976–980 | Only at 20:23:57.676–677 does native code log en0, a successful listener, the prepared endpoint, then another source start. This is about 129 seconds after the first attempt. |
| Entire supplied log | No accepted TV connection/request or successful TV playback. This log does not contain a new AVPlayer -1004 error. |

The immediate cause is proven: the old 15-second watchdog starts while native code is still opening the movie.
It reports a network problem before there is a server for the TV to reach. Cleanup sits behind that blocking
source operation on the serial native queue; canceled work can still consume startup time before its player is
discarded. This log does not establish a Local Network permission failure.

Source inspection also found that AirPlay's demuxer lacked `use_mfra_for=pts`, already used by preparation and
Kodi r24. Opening a prepared fragmented MP4 can therefore walk fragment headers remotely instead of reading its
index. The native regression measures real HTTP requests and transferred bytes for a large indexed movie.

Changes for r35:

- Open fragmented MP4s through their index. Give native startup a 45-second interruptible deadline; install
  cancellation before opening the initial HTTP connection, including stalled response headers.
- Reserve session tickets before queueing; immediately interrupt canceled I/O. Discard stale queued starts and
  scope cleanup, route polling and receiver evidence to the owning ticket. Compat restarts share that ownership.
- Separate opening, TV choice and connecting. The owner gets up to 120 seconds to choose a TV; the 15-second
  reachability timer starts after route selection. Startup failures do not create a false permission card.
  No automatic repeated session. Cancel and controller exceptions resume Kodi and close native playback.
- Keep AVPlayer's playback/movie audio session and `continuesIfPossible` policy through screen lock/background.
  Ensure the IPA declares the audio background mode. Background downloads cannot replace that session with
  their silent-audio helper. The native active flag survives an expired diagnostic-log lease, works with background
  downloads disabled, and clears on close, natural completion and failure. Legitimate replay can reactivate it.
- Record source-open/index-inspection elapsed times and expose independent player/connection clocks. Tokens and
  private source URLs stay redacted.

Regression coverage includes the real Python controller's phase deadlines, slow opening, cancellation, failed
source versus failed TV connection, native lifetime and background preferences. Compiled native tests exercise
cancel during initial HTTP headers, stale cleanup, separate TV-selection clocks and bounded indexed startup.
Older source-pin assertions are updated to the ticket API; no timing threshold is weakened.

Delivery and complete test results will be recorded in HANDOFF-R28 and the r35 delivery report after verification.
Device success and screen-lock playback are **PENDING**. Evidence here is a **device failure log**; source tests
and compiled host checks cannot prove iPhone playback.

For the owner: install as an update, start a ready movie, select the TV, then lock the screen after picture and
sound begin. Test at least several minutes, seek after unlocking, Cancel/retry, two quick taps, and playback with
background downloads disabled. Keep the phone and TV on the same reachable Wi-Fi, avoid guest/client isolation,
and use a stable signal (Ethernet for the receiver where available). Keep Kodi running rather than force-quitting.
A powered-off phone cannot serve a movie; calls, route changes and network loss may interrupt playback. TV-side
cloud playback would be a separate design if playback independent of the phone is needed.
