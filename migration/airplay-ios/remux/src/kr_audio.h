// kr_audio: the audio bridge. AirPlay (AVPlayer) cannot carry DTS, TrueHD, FLAC, Opus or Vorbis in fMP4, so those
// tracks are decoded and re-encoded to AAC (stereo, or 5.1 when the source has 6+ channels) on the same segment grid
// as the video. Video is never re-encoded. Kodi iOS code (not from GMPlayer or PrismCore).
#ifndef KR_AUDIO_H
#define KR_AUDIO_H
#include "../gmplayer/gm_stream.h"
typedef struct kr_audio kr_audio;
// Opens its own demuxer over `src` (a second connection: the video demuxer keeps its position) for stream `index`.
kr_audio *kr_audio_open(gm_source src, int index, char *err, int errlen);
int kr_audio_channels(const kr_audio *a);
int kr_audio_sample_rate(const kr_audio *a);
// fMP4 init (ftyp+moov) or media segment (moof+mdat) i of the planned grid of `s` (absolute tfdt).
int kr_audio_init(kr_audio *a, gm_stream *s, gm_buf *out, char *err, int errlen);
int kr_audio_segment(kr_audio *a, gm_stream *s, int i, gm_buf *out, char *err, int errlen);
// r8: the whole unit (ftyp+moov+moof+mdat) of segment i; the init is [0, kr_first_moof), the media segment the rest.
int kr_audio_unit(kr_audio *a, gm_stream *s, int i, gm_buf *out, char *err, int errlen);
void kr_audio_close(kr_audio *a);
// Offset of the first top-level 'moof' box (end of the init part), or -1.
int kr_first_moof(const uint8_t *p, int len);
#endif
