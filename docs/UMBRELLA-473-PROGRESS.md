# Umbrella build 473 opening repair

Status: implementation and focused host checks complete; final source review and IPA publication in progress. Owner approved a testing IPA on 2026-11-14. No merge requested.

Baseline: build 473, `ceb06e7f2b48136cb0d66d2d1552ad5a732d421f`, PR #28 (`claude/build442-feedback`).

## Evidence

- Read both supplied logs completely; originals and redacted working copies remain outside Git.
- Current log identifies build 473 and system networking. It records source selection and about 45 seconds without a player-open event. The owner's screenshot/report supplies the repeated 0/4/8 MB and never-opening behavior.
- Old log identifies build 470, with a separate “no picture after 126 s” event. Do not attribute that timeout to the shorter build-473 capture.
- Build 473 split each 4 MiB cache block into four parallel requests (eight at once), retaining the first/second/tail prefetch. Its readiness check accepted file size before complete blocks existed. On the iPhone, the native opener buffers a whole split piece, so one finished piece could signal readiness while other pieces stalled.
- Independently reproduced incomplete handoff, abandoned reads continuing after close, and conflicting range totals. The original opening fixture had five failures in seven tests on the unchanged baseline.

## Changes

- Admit the cache only after the complete, validated first/second/tail blocks are present. Smaller files require only their actual blocks.
- Apply one five-second opening deadline across probes, semaphore waits, redirects and renewed-link retries. Fall back to the exact original source and headers when the cache is not ready.
- Cancel queued and active cache reads on fallback; enforce the eight-request cap on split and unsplit reads. Reject inconsistent totals, wrong ranges and missing bytes.
- Add one diagnostic line containing route, elapsed time, block/request/byte counts and status; no source URL, account data or media IDs.
- Keep native pins and existing UI unchanged.

## Verification checkpoint

- Real HTTP opening suite: 12 passing, including native buffered responses and staggered probes.
- Range/cancellation suite: 10 passing, including renewal deadline/cancellation cases.
- Combined related suites: 125 tests pass (12 real HTTP opening, 10 integrity/cancellation, 14 native opener, 14 renewal, 55 remote media, 7 fallback, 4 parallel speed, 9 timing). Five macOS Foundation tests skip on Linux; no native code changed.
- Mandatory project check and staged-deliverable scan pass. Final review added protection against a ready stats reply arriving after its deadline.
- Commit, CI and testing IPA: source ready; publication/build requested next.
- Phone playback and elapsed time: unverified.

A slow but working provider may intentionally fall back to direct playback: completing all probes within five seconds is not guaranteed. This bounds cache admission; it does not promise that the upstream provider or Kodi's subsequent direct open finishes within five seconds. The exact cause of each UI reset is not provable from these logs, which lack transport diagnostics.

## Next

Publish the source fix to PR #28, request one IPA using its build label, verify the resulting artifact and send the download link. Retest the same source, another version and Continue Watching on the iPhone.
