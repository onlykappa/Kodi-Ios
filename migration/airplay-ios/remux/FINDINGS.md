# AirPlay MKV remux: findings (2026-11-03)

Latest owner bug 3 investigation/source fixes (2026-11-04): [AirPlay playback and seeking](../../../docs/AIRPLAY.md), ISSUE-093. 1,095 native host checks pass; published framework pin remains r11 and device acceptance is pending. Earlier r7/r8 findings below are historical, not universal format support.

Studied three projects (shallow clones, read locally):

| | Licence | What it offers | Used |
|---|---|---|---|
| GMPlayer | MIT | Portable C core on FFmpeg: open via byte-source callbacks, keyframe segment plan, per-rendition fMP4 init/media segments with absolute `tfdt`, WebVTT from text subtitles, HDR colour info. Swift HLS playlist + loopback server. | C core copied (gmplayer/), playlists ported to C |
| PrismCore | LGPL-2.1+ + App Store exception | Same idea with more: DTS/TrueHD bridged to **E-AC-3**, subtitle burn-in, Dolby Vision handling, Rust/Swift. | Design reference only, no code |
| CastTV | none | Casting UI and a remux server in Swift. | Ideas only, no code |

## Decision: GMPlayer core + our own small audio bridge

GMPlayer only serves audio Apple can play (AAC, AC-3, E-AC-3, ALAC, MP3, LPCM). Torrents and Drive files that people
play through Kodi often carry **DTS** (most Blu-ray rips), **TrueHD** (remuxes), **FLAC**, **Opus** or **Vorbis**
(WebM). Skipping them would play those films silent, which the brief rules out. So an audio bridge is needed.

PrismCore's bridge is Swift/Rust tied to its session classes. Copying it would bring LGPL obligations on top of
FFmpeg's and still need a C port. We wrote `src/kr_audio.c` (≈300 lines on libavcodec/libswresample instead):
decode → resample → **AAC** (stereo, or 5.1 when the source has 6+ channels), on the video's segment grid in whole
1024-sample frames, so segments tile with no gap (checked by the host tests). AAC rather than PrismCore's E-AC-3
because every AirPlay receiver (Apple TV, HomePod, AirPlay speakers, smart TVs) takes AAC; E-AC-3 would keep
Atmos-less 5.1 to a receiver but fails on speakers. Changing the target later is one encoder name.

## What changed from GMPlayer's design

- **The server cannot stay on 127.0.0.1.** With AirPlay video the Apple TV fetches the playlist and every segment
  itself. The server listens on the phone's Wi-Fi address while AirPlay plays, and every path carries a random
  128-bit token (404 without it). Loopback mode is kept for tests.
- C server instead of Swift (KodiAirPlay is an Objective-C dylib loaded by Python with ctypes).
- Two fixes in the copied core, marked in the code: an early-stopping keyframe index planned one segment for a
  whole short file; the last segment's open end ignored a non-zero start time (MPEG-TS), cutting the tail.

## r7: picture bridge (compat mode)

Many TVs with built-in AirPlay (owner: TCL Roku TV) cannot decode HEVC: they take the audio segments, never a video
one, and play sound only (r6 detects this). r7 converts the picture on the phone (src/kr_video.c, modeled on the
audio bridge):

- Per segment of the planned grid: frames with presentation time in [start_i, start_{i+1}) are decoded (VideoToolbox
  through FFmpeg's hwaccel when available, software otherwise, and a software retry if VideoToolbox refuses the
  stream), scaled with libswscale to at most 1920x1080 8-bit 4:2:0 BT.709 and encoded by a fresh h264_videotoolbox
  encoder (High, level 4.0 / 4.2 above 30 fps, ~7 Mbit/s at 1080p, no B-frames, IDR on the first frame: a closed GOP
  per segment). Timestamps are the source's, so tfdt is absolute on the same grid as audio and subtitles. The demuxer
  seek is checked (MPEG-TS lands past the target) and goes further back when late.
- kr_remux_start(url, lan, compat, ...): compat serves /video/ converted; the master says CODECS avc1.640028,
  RESOLUTION capped, VIDEO-RANGE=SDR. A file whose video AirPlay cannot carry (VP9, MPEG-2, MPEG-1) switches to compat
  by itself; otherwise the framework restarts once in compat at the current position when the TV plays sound only
  ("Converting the picture for this TV..." meanwhile), and shows r6's "No picture on the TV" only if that fails too.
- Battery and heat: hardware decode + encode run only for segments the TV asks for (it reads a few ahead), one at a
  time (one encoder session); stopping the server aborts a conversion at its next packet and frees everything.
- Limits: HDR (PQ/HLG) gets no tone or gamut mapping (libswscale has none): it looks washed out. Dolby Vision profile
  5 looks wrong. AV1 is not decoded (FFmpeg's AV1 decoder needs dav1d, an external library). Each segment's encoder
  is new, so the SPS/PPS in the init (from segment 0) must equal every segment's; VideoToolbox gives the same
  parameter sets for the same settings, but this is unverified on a TV.
- Host tests: FFmpeg has no LGPL software H.264 encoder and Linux has no VideoToolbox, so the tests run the same
  pipeline with FFmpeg's MPEG-4 Part 2 encoder (kr_video_set_encoder("mpeg4")): window tiling, keyframe at every
  segment start on the grid, every source frame converted once, absolute tfdt (MPEG-TS at 1.4 s), 10-bit PQ HEVC to
  8-bit, CODECS in the master, audio alongside, stop during a conversion. The H.264 bytes themselves are only made on
  the phone.

## r8: the picture per receiver, faster segments, the holder follows the screen

Owner build-136 (HEVC MKV from Drive to a TCL Roku TV): the TV (User-Agent `AirPlay/2.0 (App/80.141.0)
MFi_AirPlay_Device (MFiModelGroup/...)`) fetched the master itself, read the HEVC video init, hung up on the segments,
and AirPlay switched off ~10 s after it started. r7's restart waited for 30 s of sound only, so it never ran. Segments
took 1.2-4.5 s (Drive over HTTP, every request under one lock, the video init muxing segment 0 again).

- **Per receiver** (kr_remux.c): when the source video is not H.264 and the converter exists, a request whose
  User-Agent contains `MFi_AirPlay_Device` (third-party AirPlay 2 receivers: TVs' built-in AirPlay) gets the compat
  master (CODECS avc1.640028 / 64002A, RESOLUTION at most 1920x1080, VIDEO-RANGE=SDR) whose video variant is
  `/cvideo/index.m3u8`; its `/video/` requests are converted as well (a TV that skips the master). Everyone else keeps
  the copy: the phone's player (`AppleCoreMedia/... (iPhone; ...)`) and an Apple TV (tvOS's player also says
  AppleCoreMedia, with `(Apple TV; U; CPU OS ...)`; from knowledge of tvOS, not measured here). Conservative on
  purpose: only the MFi tag switches. Both variants use the session's one plan, so EXTINFs and segment starts are
  identical (host test: same playlist, same first frame per segment). The audio and subtitle renditions are shared.
  kodi.log says `compat: <UA> gets the picture as H.264: <variant line>`.
- **Fallback** (build-airplay.sh): external playback ending within 20 s with no video segment served to a receiver
  other than the phone (`kr_remux_served_external`, by User-Agent) restarts once in compat mode, unless the TV
  already had the converted picture or the video is H.264. The restart plays on the phone if the TV dropped the route
  (iOS decides whether AirPlay picks it up again): not verified.
- **Latency**: the playlists are made once at start (no lock per request). Each rendition has its own production lane
  and lock: copied video on the session demuxer, converted video on the converter's, copied audio and subtitles on a
  second demuxer over its own connection (the same file opened again, the plan copied: `gm_stream_adopt_plan`), each
  AAC bridge on its own. Units are made once (`gm_stream_track_unit`, `kr_video_unit`, `kr_audio_unit`): the init and
  segment 0 come from one pass. Inits are kept for the session; media segments in an LRU of 24 / 64 MB (a segment made
  ahead and not yet asked for is never pushed out by another one made ahead). After segment N of a rendition is
  served, two background workers make N+1 and N+2 (whichever job's lane is free; the start of the default video and
  audio is made right at start). A request far from the queued jobs drops them and cancels a conversion made for the
  old place (between packets, so the demuxer stays usable); stop aborts every connection first and joins the workers.
  Host test over a slow Range source (0.1 s per request, 2 MB/s): cold video segment ~380 ms, audio ~650 ms, both at
  once ~390 ms (was the sum); with prefetch the segments after the first are answered in ~1 ms; a repeated segment or
  init ~0 ms. Memory: up to 64 MB of segments plus a second demuxer; the converter still runs one segment at a time,
  now up to two ahead of the TV (more warmth for compat sessions, none once the player closes).
- **Holder**: r4 fixed the holder to the orientation Kodi had when Apple's player opened; when Kodi stopped and turned
  to portrait underneath, Apple's controls stayed laid out landscape on the portrait screen (owner screenshot). The
  holder now allows any orientation but upside down, opens in the current one, and lays the player out on every size
  change; healKodi on dismiss stays (ISSUE-081).
- ThreadSanitizer run of the host tests: the new lanes, cache and workers report no races of their own; what remains
  is FFmpeg's frame threads (uninstrumented) and two older ones (the error message string, the accept loop's socket).

## Not verified

Nothing here has run on an iPhone or an Apple TV. r8: the Objective-C (fallback restart, holder layout) is not
compiled here (no macOS); whether the TCL Roku TV plays the converted /cvideo/ stream, and other TVs' User-Agents
(Samsung, LG, Vizio, Sony), are unknown until a phone test. The host tests check structure and timing, not that AVPlayer
accepts the stream. GMPlayer's authors state their fMP4 output plays in AVFoundation; ours is the same muxer setup.
The AAC bridge output decodes cleanly with FFmpeg and keeps each channel's level.
