// kr_video (r7): the picture bridge for AirPlay receivers that cannot decode the source video (many TVs' built-in
// AirPlay has no HEVC; VP9 / MPEG-2 / MPEG-4 ASP are not AirPlay codecs at all). Each segment of the planned grid is
// decoded (VideoToolbox when FFmpeg has it, else software), scaled to at most 1920x1080 8-bit 4:2:0 SDR and encoded
// to H.264 High (h264_videotoolbox on the phone) with a fresh closed GOP that starts with an IDR on the segment's
// first frame, then muxed to fMP4 with absolute tfdt like kr_audio. Modeled on kr_audio. Kodi iOS code.
// HDR (PQ/HLG, 10-bit) is only range/matrix converted to 8-bit BT.709: no tone mapping or gamut mapping (libswscale
// has none), so HDR sources look flat, washed out and slightly desaturated. Dolby Vision profile 5 looks wrong.
#ifndef KR_VIDEO_H
#define KR_VIDEO_H
#include "../gmplayer/gm_stream.h"
typedef struct kr_video kr_video;
// A seek superseded speculative conversion. Distinct from a decode/read/encode failure.
#define KR_VIDEO_CANCELLED (-2)

// The CODECS value the master playlist declares for the converted video (H.264 High, level 4.0).
#define KR_VIDEO_CODECS "avc1.640028"
// CODECS for a frame rate: level 4.0 up to 30 fps, 4.2 above (1080p60).
const char *kr_video_codecs(double fps);
#define KR_VIDEO_MAX_W 1920
#define KR_VIDEO_MAX_H 1080

// Output size for a w x h source: aspect kept, at most 1920x1080, even dimensions, never upscaled.
void kr_video_output_size(int w, int h, int *ow, int *oh);
// Target bit rate (bit/s) for an output size: ~7 Mbit/s at 1080p, scaled by area, at least 1.5 Mbit/s.
int kr_video_bitrate(int ow, int oh);
// Frames of a segment: source frames with presentation time t in [start, end) (seconds; end < 0: to the end).
// The windows of consecutive segments tile the timeline with no gap or overlap. Exposed for tests.
int kr_video_in_window(double t, double start, double end);
// Segment i's window on the planned grid of `s` (end -1 for the last segment).
void kr_video_window(gm_stream *s, int i, double *start, double *end);

// Encoder used for the converted video. NULL / not set: "h264_videotoolbox" (iOS). FFmpeg has no LGPL software H.264
// encoder, so the host tests set "mpeg4" here to exercise decode -> scale -> encode -> mux -> tfdt; the bytes are
// then MPEG-4 Part 2, not H.264 (the playlist still declares KR_VIDEO_CODECS). Not thread-safe: set before use.
void kr_video_set_encoder(const char *name);
const char *kr_video_encoder(void);
// 1 when the configured encoder exists in this FFmpeg build.
int kr_video_available(void);

// The source video stream to convert: the engine's choice, else the first video stream FFmpeg can decode (VP9,
// MPEG-2... that the copy path skips). -1 when none.
int kr_video_pick_stream(gm_stream *s);

// Opens its own demuxer over `src` (a second connection) for video stream `index`.
kr_video *kr_video_open(gm_source src, int index, char *err, int errlen);
int kr_video_width(const kr_video *v);   // output size
int kr_video_height(const kr_video *v);
int kr_video_hw_decode(const kr_video *v);  // 1 when VideoToolbox decodes
// r11: how the last segment's frames were scaled/converted (log): GPU transfer or CPU (libswscale).
const char *kr_video_path(const kr_video *v);
// fMP4 init (ftyp+moov) or media segment (moof+mdat) i of the planned grid of `s` (absolute tfdt).
int kr_video_init(kr_video *v, gm_stream *s, gm_buf *out, char *err, int errlen);
int kr_video_segment(kr_video *v, gm_stream *s, int i, gm_buf *out, char *err, int errlen);
// r8: the whole unit (ftyp+moov+moof+mdat) of segment i; the init is [0, kr_first_moof), the media segment the rest.
int kr_video_unit(kr_video *v, gm_stream *s, int i, gm_buf *out, char *err, int errlen);
// Makes a running conversion give up at the next packet (server stopping), and every later one. Any thread.
void kr_video_abort(kr_video *v);
// r8: makes the conversion in progress (a prefetch the receiver no longer needs after a seek) give up at the next
// packet; the next conversion runs normally. Any thread.
void kr_video_cancel(kr_video *v);
void kr_video_close(kr_video *v);
// r10: burns subtitles into every converted frame from now on: source text subtitle stream sub_index (>= 0), else
// the external file (.srt / .vtt / .ass / .ssa). Once per converter (the libass track is kept for the session; other
// subtitles mean a new session). No stream and no file: nothing burned, 0. -1 with a reason when they cannot be read.
// Segment windows and timestamps are unchanged.
int kr_video_burn(kr_video *v, int sub_index, const char *file, char *err, int errlen);
int kr_video_burning(const kr_video *v);
int kr_video_burn_events(const kr_video *v);  // subtitle events loaded so far (tests, log)
long kr_video_burn_drawn(const kr_video *v);  // r11: converted frames with a subtitle drawn on them so far
#endif
