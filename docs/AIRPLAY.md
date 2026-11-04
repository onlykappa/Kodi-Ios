# AirPlay playback and seeking — owner bug 3 / ISSUE-093

Status: partial source fix in draft PR #8. The reproduced seek-cancellation failure and fully bridged-file admission are repaired on the host. Long Drive seek delays, broader codec/HDR coverage and device acceptance remain open. No IPA, iOS framework build or merge.

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

## Compatibility audit

An extension identifies a container, not the video/audio codec or receiver capability. Current source and published r11 do not support every possible file.

| Input | Current route and evidence | Remaining limits |
| --- | --- | --- |
| MKV / MK3D / WebM | Matroska demuxer, HLS remux or conversion. Host coverage includes H.264, HEVC, MPEG-2 and VP9 + Opus. | Fully bridged VP9 + Opus admission requires this new source fix/new framework. AV1 decoding is not enabled. |
| AVI | AVI demuxer; host MPEG-4 Part 2 + MP3 converts and seeks. | The extension does not establish support for every legacy AVI codec. |
| TS / MTS / M2TS | MPEG-TS demuxer; host H.264 + AC-3 timing/seeks checked, including nonzero start times. | Unsupported contained codecs still need decoders. |
| MP4 / M4V / MOV | Direct to Apple's player by extension or byte probe. | Codec-aware conversion fallback is bypassed; an unsupported codec/audio track cannot be repaired merely because the container is MP4. This needs a separate routing change and fixtures. |
| HLS / M3U8 | Direct to Apple's player. | Receiver must accept the playlist's codecs and delivery. Current converter does not demux HLS. |
| VOB / MPEG-PS, ASF/WMV, FLV, Ogg video and other containers | Not among the four enabled FFmpeg input demuxers. | Add/test specific demuxers, corresponding decoders and seek fixtures before claiming support. Renaming extensions cannot add support. |
| Converted video | Enabled video decoders: H.264, HEVC, VP8, VP9, MPEG-1, MPEG-2, MPEG-4 Part 2; hardware where available, software fallback for supported profiles. H.264 output capped at 1920×1080, aspect preserved. | AV1 decoder/hardware acceleration and software fallback are not enabled. Other codecs/profiles require explicit support; software 4K can be too slow. |
| Audio | Copy AAC/AC-3/E-AC-3/ALAC/MP3/supported PCM; bridge DTS/TrueHD/MLP/FLAC/Opus/Vorbis to AAC. | Not every audio codec/profile is covered. Converted 7.1 is reduced to at most 5.1; this does not preserve lossless/Atmos features. |
| HDR / Dolby Vision | Apple-compatible copy may preserve original signaling; compatibility output is 8-bit BT.709 SDR. | No proper HDR tone/gamut mapping in the compatibility path. Dolby Vision profile 5 is not correctly rendered. SDR labeling alone is not HDR conversion. |
| Subtitles | Text tracks can become WebVTT or be burned into compatible video. | Bitmap PGS/DVD/DVB subtitles are not handled by the current text burn-in path. |

The practical expansion path is content-aware routing for MP4/MOV, additional tested container/decoder coverage (including an AV1 decode path), and proper HDR/Dolby Vision conversion. Each needs real fixtures, seek/timestamp validation and device acceptance; none is silently marked completed by this seek fix.

## Validation and next device test

1,095 compiled native host checks pass, plus 25 AirPlay Python tests and eight iOS static tests. The tests cover overlapping seek requests with prefetch off/on, backward/forward retries, actual 4K 10-bit decode/downscale, WebM/VP9/Opus and AVI/MPEG-4/MP3, and existing audio/subtitle/copy/remux/HTTP/stop paths. Genuine failure tests still return errors.

The actual 4K fixture is 20 seconds at six fps, keeping host CI bounded. Converted tail frames decode at the requested time and output pixels are 1920×1080. Linux uses the MPEG-4 Part 2 test encoder; it does not exercise VideoToolbox, H.264 output, sustained phone 23.976/60 fps or TV acceptance. Evidence and retained validation failures: [airplay-seek-validation.json](../reports/airplay-seek-validation.json).

No extra owner log is needed to establish the reproduced cancellation defect. A later build/device capture is needed to measure the remaining delays using the new queue/production timings. Test small, large and repeated forward/backward seeks on a completed phone copy, a Drive copy and active Elementum input, with subtitles both on and off. Check picture, audio synchronization and resumed position on the receiver.

**Build dependency:** the source-lock still pins published KodiAirPlay r11. Before any future requested IPA, build/publish a new framework release, verify its checksum and pin it. An IPA made with the unchanged r11 framework would omit these C fixes. No workflow has been dispatched and no release has been changed.
