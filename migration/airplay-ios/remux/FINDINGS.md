# AirPlay MKV remux: findings (2026-11-03)

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

## Not verified

Nothing here has run on an iPhone or an Apple TV. The host tests check structure and timing, not that AVPlayer
accepts the stream. GMPlayer's authors state their fMP4 output plays in AVFoundation; ours is the same muxer setup.
The AAC bridge output decodes cleanly with FFmpeg and keeps each channel's level.
