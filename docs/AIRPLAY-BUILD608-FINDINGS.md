# Build608 phone AirPlay evidence — 2026-11-20

Owner reports audio without visible video across downloaded titles/qualities and
an Umbrella stream. The supplied log contains four native AirPlay starts. Raw
logs, media, addresses and account data remain outside Git.

## Installed build and diagnostic boundary

Installed-build event identifies build608, main source
f50f1a61e21d2fb86023e39cae457a73f3499f1f, AirPlay r67 archive
d7bb7cc432771bf4aa54244670e1396369df65e4bf03d75555f17f460d48f552.
The source lock at that exact GitHub commit independently matches r67/source
2fde082. This is not diagnostic IPA602/r68. There are zero new request trace
or audio-window diagnostic lines. Existing structured startup/network/player
diagnostics are useful, but r68's packet/reader evidence was not collected.

## Attempt breakdown (phone-local log times)

| Start | Observed source | Preparation / result |
| --- | --- | --- |
| 18:19:06 | Prepared MP4, H.264 High8-bit1080p, resume1075.3s | Copied video/audio prime succeeds in5.702s. Phone receives media; external route turns on then ends after about7s. No direct TV HTTP request is recorded. CoreMedia reports-12889, no response for seg182 in6.006s; an audio182 request is outstanding. Later HTTP500/session-stopped and audio result-5 occur during shutdown. Outcome unreachable; transport topology/cause remains unresolved. |
| 18:20:12 | Retry of same1080p prepared MP4, resume1110.9s | Copied video/audio prime succeeds in6.738s. TV reaches master after13.723s and is switched to converted H.264/subtitle-burn route. TV receives audio; no video media segment is successfully delivered to TV. Converted target184 stops after20.341s (10.406s source I/O,9.926s shared wait); player fails first, then conversion is canceled and pending requests return500. Total reported outcome49s. |
| 18:21:30 | Prepared MP4, HEVC Main10,3840x2160, resume101.4s | Source opening4.092s + inspection1.377s, then42.058s priming copied video/audio. Copy windows can reach70.3s; TV uses a separate1691-window six-second conversion plan. TV first request48.466s after start. TV asks converted video/audio segment16. Background converted0 is canceled for16. Converted16 spends8.126s (3.449s source I/O,4.653s shared wait) before shutdown. TV media/video counters both remain0. Outcome failed after59.5s. |
| 18:23:59 | MKV, H.264 High10/10-bit1080p, resume733.4s; consistent with owner's streaming attempt | Opening12.396s + inspection16.869s. Audio122 succeeds after24.183s. Video never finishes before outcome aborted at67.5s. Conversion stops afterward at38.832s, with14.371s source I/O and24.442s shared wait. No TV requests: preparation did not reach receiver playback. Source-cache counters report18 errors,6 retries and about88.2MB read. These counters do not identify a provider ban; later range reads succeed. |

Timing categories can overlap across threads and must not be summed as elapsed
wall time. Player presentation0x0 alone is not proof of missing external video;
here owner observation plus TV video-delivery counters and failed requests are
the stronger evidence. Audio heard on every attempt is owner's report; the log
does not independently prove TV audio playback on every attempt (especially the
last, which remains in preparation).

## Substantiated application-side investigation target

In r67 `kr_remux_prime_for` chooses copied video when `S.compat` is false. The
third-party receiver's master can instead select `/cvideo/` and `/caudio/` after
that priming has completed. Thus successful opening of the phone's copy does
not establish readiness of the TV's selected rendition. The master handler
also queues converted segment0 unconditionally. On resumed attempts this starts
the wrong window; both1080p retry and4K attempt log cancellation/reinitialization
when the actual target arrives. The4K path additionally primes long copy
windows before the receiver asks for its shorter conversion windows.

This establishes mismatched preparation and wasted work, not proof that fixing
it alone solves receiver playback. Next reproduce an MFi receiver master at a
nonzero resume point, verify the actual selected rendition/window is ready,
and compare copied/converted lane contention. Preserve receiver identity and
codec requirements. Subtitle burning is enabled in all four attempts; measure
its cost and explicit selection before changing subtitle policy.

The earlier ISSUE-392 empty audio window is not reproduced in this log: there
are no `empty segment` messages. The post-failure `stopped`/HTTP500 records must
not be labeled the initiating cause. Background preparation and upload activity
overlap these attempts; contention is plausible, but causation is unproven.

## Next evidence

Prioritize correct TV rendition/resume-window priming and removal of obsolete
segment0 work in a controlled test before altering retries/timeouts. Retain
ISSUE-392 separately pending packet-window evidence from r68. Build608 does not
contain the diagnostic framework published in IPA602; future phone evidence
must confirm the installed framework pin rather than rely on build number order.
No runtime change, framework publication, IPA build or merge is part of this log
review.
