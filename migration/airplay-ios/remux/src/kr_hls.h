// kr_hls: the HLS playlists AVPlayer reads from the loopback server. One video variant, an audio group (every audio
// track: Apple's codecs copied, DTS/TrueHD/FLAC/Opus/Vorbis bridged to AAC) and a WebVTT text-subtitle group.
// Playlist logic ported from GMPlayer's GMStreamSession.swift (MIT, (c) 2026 Gaston Morixe).
#ifndef KR_HLS_H
#define KR_HLS_H
#include "../gmplayer/gm_stream.h"

enum { KR_AUDIO_NONE = 0, KR_AUDIO_COPY = 1, KR_AUDIO_AAC = 2 };

// How an audio track reaches AirPlay: copied (Apple plays it), re-encoded to AAC, or not at all.
int kr_audio_route(const gm_track_info *t);
// HLS CODECS token for an audio track as served ("ec-3", "mp4a.40.2"...).
const char *kr_audio_token(const gm_track_info *t);
// RFC 5646 language for an ISO 639-2 code ("" for und/unknown).
const char *kr_language(const char *iso639);

// Playlists as malloc'd strings (caller frees). `base` is like "http://127.0.0.1:49152".
// video_codec is the variant's video CODECS value (kr_hls_video_codec).
// compat (r7): the video variant is the converted picture (kr_video): CODECS avc1.640028 (High 4.0; 64002A above
// 30 fps), RESOLUTION capped at 1920x1080, VIDEO-RANGE=SDR, BANDWIDTH from the encoder's bit rate.
char *kr_hls_master(gm_stream *s, const char *base, int compat);
// r8: the same with the video variant's media playlist at base/<video_dir>/index.m3u8 ("video", or "cvideo" for the
// converted picture served to one receiver while the others get the copy).
char *kr_hls_master_at(gm_stream *s, const char *base, int compat, const char *video_dir);
char *kr_hls_media(gm_stream *s, const char *prefix, const char *seg_ext, int with_map);
// "avc1.640028" / "hvc1.2.4.L150.90" for the selected video (from the stream's profile and level).
void kr_hls_video_codec(gm_stream *s, char *out, int len);
#endif
