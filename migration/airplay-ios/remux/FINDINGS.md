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

## Not verified

Nothing here has run on an iPhone or an Apple TV. The host tests check structure and timing, not that AVPlayer
accepts the stream. GMPlayer's authors state their fMP4 output plays in AVFoundation; ours is the same muxer setup.
The AAC bridge output decodes cleanly with FFmpeg and keeps each channel's level.
