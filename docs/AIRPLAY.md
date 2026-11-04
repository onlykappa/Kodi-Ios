# AirPlay playback and seeking — owner bug 3 / ISSUE-093

Status: source compatibility expansion in draft PR #8, following the seek-cancellation fix. AV1, common legacy formats, MP4 codec-aware routing, HDR10/HLG tone/gamut mapping and embedded bitmap burn-in are implemented and host-tested. The next source pass adds bounded HTTP requests, fresh-connection retry deadlines and external SUP/IDX bitmap subtitles. Converting Dolby Vision profile 5 for incompatible receivers, long Drive seek acceptance and device verification remain open. No IPA, iOS framework build or merge.

## What the new phone log establishes

The private 199,922-byte log spans 07:50:28.818–07:53:28.472 on 2026-11-04 (log timezone unstated). Its movie source is the Google Drive download proxy. The source is 3840×1608, 10-bit HEVC at 23.976 fps, advertised SDR; 10-bit alone does not establish HDR. This third-party AirPlay receiver gets 1920×804 H.264. VideoToolbox decoding and GPU transfer are confirmed by the actual conversion log, so CPU fallback is not this capture's explanation.

Converted six-second segments include 3,782, 3,526 and 2,667 ms of conversion; a later converted request takes 4,844 ms in total. Copied audio requests also take 7,007 and 8,388 ms, and CoreMedia reports six-second media-response timeouts. A large seek to segment 521 (about 52:06) has repeated audio/video requests outstanding for up to 26,669 ms before shutdown. Its final 500s say `session stopped`. The screenshot's `seg37` foreground cancellation is a separate error variant; the owner confirms that forward seeking typically stops playback. This log does not contain that exact screenshot failure.

The screenshot error is reproduced against the old server scheduler with synthetic media: a request for the forward position cancels another connected request's video conversion; the old request returns HTTP 500 and sets a persistent fatal message. Two of twelve targeted checks fail before the fix. This is a demonstrated source defect, not proof that it explains all 26-second Drive delays.

## Focused source changes

- Cancel only speculative conversion identified under the background scheduler lock. Connected foreground requests no longer cancel each other; init reads do not refocus background work to time zero.
- Clear a background worker's ownership while it still holds the lane, preventing a stale marker from canceling the next foreground conversion.
- Give queued foreground work priority over speculative work. Keep expected cancellation as a typed result, distinct from decode/read/encode failure; genuine failures remain visible.
- Log slow requests with separate lane-wait and production times. Production still includes source I/O, seek/preroll, subtitles and encoding; this does not identify their individual costs.
- Let the segment planner accept decodable video with no copy-compatible stream. VP9 + Opus previously failed before the converters could run, despite both decoders being present. Keep the no-copy marker so video conversion is mandatory. If conversion is required but unavailable, fail clearly instead of silently succeeding with audio only.

Foreground work already running may still delay a new seek. A read already blocked on Drive is not interrupted by speculative cancellation. These limits remain explicit; no fast-seek or restored 4K throughput claim is made.

## Compatibility expansion — source/host scope

The earlier audit described published r11 and the previous source. It incorrectly described all libswscale as lacking tone mapping: pinned FFmpeg 8.1.1 supports it through the dynamic frame API, which the old caller bypassed. The source now uses that API. **Published r11 remains unchanged; these capabilities require a newly built framework.**

| Input/feature | New source behavior | Verification and limits |
| --- | --- | --- |
| MP4 / M4V / MOV, including extensionless bytes | Inspect file codecs and provide HLS receiver-specific copy/conversion; the extension no longer bypasses conversion. Ordinary compatible video remains copied. | H.264/AAC MP4, HEVC/AC-3 MP4 with its extension hidden, native vs third-party receiver routing, actual decoded seeks. |
| AV1 | Pinned dav1d 1.5.3 software decoder; iOS requests VideoToolbox AV1 and falls back to dav1d if hardware initialization/initial decoding fails. | Actual AV1/Opus MKV conversion, decoded seek target, backward/retry and audio. iOS hardware selection and sustained 4K throughput pending. |
| WMV/ASF, FLV, Ogg video | Additional input demuxers and corresponding decoders. | WMV2/WMA2 ASF, FLV1/MP3 FLV and Theora/Vorbis OGV conversion and seeking pass. |
| MPEG-PS / MPG / VOB | Program-stream and raw-video probing enabled; sparse beginning/end-only indexes cannot create a movie-sized segment. | Actual MPEG-2/MP2 program-stream target/backward/retry and audio. VOB navigation/menu behavior is not claimed. |
| RM, WTV, NUT, ProRes MOV | Corresponding demuxers/native decoders; supported audio bridges to AAC. | RV20/AC-3 RM, MPEG-2/AC-3 WTV, MPEG-4/float-PCM NUT and ProRes/24-bit-PCM MOV files convert and seek. |
| H.264/HEVC profiles | Convert H.264 high-bit-depth/non-4:2:0 and unsupported HEVC profile/bit-depth combinations; third-party TV compatibility is also offered for 4K H.264. | Actual 10-bit H.264 MP4 automatic-conversion test; all possible profiles are not individually device-verified. |
| Audio | Any enabled audio decoder can bridge an otherwise unsupported track to AAC, including WMA, MP2, WavPack and additional PCM types. Existing compatible copy routes retained. | Real audio seeking in format fixtures, prior DTS/TrueHD/Opus tests, Blu-ray LPCM route check. Converted output remains at most 5.1; no lossless/Atmos preservation claim. |
| HDR10 / HLG | High-precision RGB tone/gamut mapping to BT.709 SDR, resizing before the expensive map. Preserve HDR metadata into mapping; retain the SDR GPU path. | PQ black/highlight/neutral-chroma tests, pixels differ from SDR transfer, HLG conversion, actual 10-bit HDR video decode. HDR software mapping performance needs an iPhone measurement. |
| Embedded bitmap subtitles | PGS/DVD/DVB/XSUB decoders and bounded palette-bitmap cache; scaling, alpha, timing/clear and backward seek. | Generated real PGS packets/Matroska, decoded palette pixels in NV12 and planar output, and full conversion compared frame-for-frame with no subtitles. DVD has a separate external VobSub fixture; DVB/XSUB still lack individual fixtures. External IDX/SUP loading is covered in the follow-up below; embedded long-cue lookback remains limited. |
| Dolby Vision profile 5 | Preserve native MP4 playback when its audio is compatible; conversion refuses to treat profile-5 IPT/RPU pixels as ordinary HDR. | Synthetic Dolby configuration verifies native routing only. A compatible receiver is required; an RPU-aware converter for other TVs is still needed. No profile-5 color-accuracy claim. |
| HLS/M3U8 | Keep Apple's native adaptive-playlist path, including playlists identified by bytes without an extension. | Native routing tested; this does not add conversion for unsupported codecs inside arbitrary HLS playlists. |

Existing MKV/WebM/AVI/MPEG-TS copy, audio bridge and conversion checks remain. A container or enabled decoder alone does not establish every profile, malformed file, delivery method or receiver combination.

## MP4 seeking and dependency changes

Open-GOP HEVC MP4 revealed varying decode-to-presentation offsets at keyframes. A constant correction was insufficient: copied and converted segments still differed by about 125 ms. A small LGPL patch to pinned FFmpeg exposes the presentation timestamps already held in MOV's sample tables. The planner uses them without fetching every keyframe or scanning the movie; receiver copy/conversion alignment checks now pass. The patch applies cleanly to the independently pinned upstream commit, and the compiled source matches the clean patched source.

The HDR pixel tests also caught neutral chroma saturating in the pinned library's managed YUV output. The implemented path maps to 16-bit RGB first, then uses the proven range/matrix pack to NV12/planar output. It resizes before the color map to reduce 4K CPU work. This is actual tone/gamut processing, not an SDR tag change. Correct color processing and real-time phone throughput remain separate acceptance checks.

Build recipes add checksum-pinned BSD-2-Clause dav1d, preserve optimized ARM assembly on iOS, and ship its licence/configuration. FFmpeg remains LGPL-2.1+ without GPL/nonfree components; its MOV accessor patch is shipped with the framework. A separately pinned archive of the same upstream FFmpeg release commit is available when the release download site fails. CI cache keys cover dependency recipes and the FFmpeg patch.

Slow conversion logs now separate source seek/read/reconnect time from total production, in addition to queue wait. This narrows a future Drive capture; the old 26.7-second phone stall is not declared fixed by host tests.

## Drive transport and external subtitle follow-up

HTTP probing now requests at most 256 KiB, then at most 1 MiB per range, with connection reuse where the server permits it. This bounds read-ahead after a seek: the pinned Drive proxy can grow open-ended requests to 8 MiB and may drain abandoned data to preserve its upstream connection. The reader previously described a fresh retry but reused the same AVIO context. It now opens a fresh context directly at the requested byte offset, with all attempts sharing one monotonic read deadline. Stop still interrupts network waits. The normal configured timeout is unchanged; this is not a one-second production timeout.

Fault injection against the previous committed reader fails two targeted checks: an endpoint requiring finite ranges rejects its open-ended request, and a one-second read budget takes 5.211 seconds under repeated stalls. The new reader passes byte-for-byte sequential/cross-boundary/EOF and forward/backward checks, dropped-response recovery and a 1.002-second deadline measurement. Those timings describe this synthetic fault, not movie-seek latency or the owner's 26.7-second Drive stall. Smaller ranges can add HTTP round trips; high-bitrate Drive throughput still needs a phone measurement.

External PGS `.sup` and VobSub `.idx` + companion `.sub` now use a dedicated local subtitle demuxer and the existing bounded bitmap renderer. Decode only through the requested frame, retain the first future packet (including clear sets), and replay the small subtitle input on backward seeks. A fresh seek 45 seconds into a long cue works without reading 45 seconds of 4K video. SUP/IDX discovery and Kodi's selected-file forwarding are connected; incomplete IDX/SUB pairs are skipped. Network subtitle protocols are disabled. Missing/corrupt files fail loading; later subtitle read errors propagate through video conversion instead of silently dropping captions.

Real generated SUP and DVD/VobSub decode/pixel tests cover planar/NV12 output, long cues, clear/duration timing, far/backward seeks, 302 cues with a 256-rectangle cache, and complete burned-video frame/timestamp comparisons. External multi-language VobSub currently picks the first supported stream. The separate embedded-subtitle lookback is still ten seconds: a fresh seek into an unusually long embedded cue can miss its initial display set. This pass does not claim that embedded limitation is resolved.

## Validation and next device test

1,355 expanded native host checks pass, plus 27 AirPlay Python tests and eight iOS static tests. Latest totals, dependency provenance and retained failure/recovery evidence are in [coverage validation](../reports/airplay-coverage-validation.json). The earlier cancellation evidence remains in [seek validation](../reports/airplay-seek-validation.json). The tests cover overlapping seek requests with prefetch off/on, backward/forward retries, actual 4K 10-bit decode/downscale, WebM/VP9/Opus and AVI/MPEG-4/MP3, and existing audio/subtitle/copy/remux/HTTP/stop paths. Genuine failure tests still return errors.

The actual 4K fixture is 20 seconds at six fps, keeping host CI bounded. Converted tail frames decode at the requested time and output pixels are 1920×1080. Linux uses the MPEG-4 Part 2 test encoder; it does not exercise VideoToolbox, H.264 output, sustained phone 23.976/60 fps or TV acceptance. Evidence and retained validation failures: [airplay-seek-validation.json](../reports/airplay-seek-validation.json).

No extra owner log is needed to establish the reproduced cancellation defect. A later build/device capture is needed to measure the remaining delays using the new queue/production timings. Test small, large and repeated forward/backward seeks on a completed phone copy, a Drive copy and active Elementum input, with subtitles both on and off. Check picture, audio synchronization and resumed position on the receiver.

**Build dependency:** the source-lock still pins published KodiAirPlay r11. Before any future requested IPA, build/publish a new framework release, verify its checksum and pin it. An IPA made with the unchanged r11 framework would omit these C fixes. No workflow has been dispatched and no release has been changed.
