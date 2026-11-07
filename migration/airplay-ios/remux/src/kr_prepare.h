// Prepare a complete, seekable MP4 before playback, from a local or loopback Drive source.
#ifndef KR_PREPARE_H
#define KR_PREPARE_H
#include <libavformat/avformat.h>
typedef int (*kr_prepare_progress)(int stage, double done, double total, void *context);
// Returns 1 only for a portable MP4 with original video resolution/HDR and AAC audio.
int kr_prepare_ready(AVFormatContext *format);
// JSON describes the file, without paths. Negative on invalid input.
int kodi_airplay_probe(const char *input, char *json, int size);
int kodi_airplay_probe_ex(const char *input,char *json,int size,kr_prepare_progress progress,void *context);
// r14: 1 when probe/prepare accept an http://127.0.0.1 source (streamed, no downloaded copy).
int kodi_airplay_prepare_streams(void);
int kodi_airplay_prepare_hdr(void);
// r15: 1 keeps each Blu-ray picture subtitle (PGS) track in output.sub<track>.<language>[.forced].sup beside the MP4
// instead of refusing the file; 0 (default) refuses it, so they are never silently dropped.
void kodi_airplay_prepare_keep_image_subs(int on);
void kodi_airplay_prepare_audio_languages(const char *list);   // r25: "en,eng" keeps the first audio + these
// Writes output.partial then validates and atomically renames it to output. Input is never modified.
// progress stages: 0 video, 1 audio, 2 packaging, 3 verification. Return 0 success, -2 paused, -1 failure.
int kodi_airplay_prepare(const char *input, const char *output, kr_prepare_progress progress,
                         void *context, char *error, int error_size);
// r16: output goes directly to a bounded-memory consumer. track 0 is the MP4;
// other tracks are preserved PGS sidecars, with suffix identifying language/forced flag.
// Return nonzero from write to accept bytes, zero to cancel. No working files are opened.
typedef int (*kr_prepare_write)(int track,const char *suffix,const uint8_t *data,int size,void *context);
int kodi_airplay_prepare_to(const char *input,kr_prepare_write write,void *write_context,
                           kr_prepare_progress progress,void *context,char *error,int error_size);
int kodi_airplay_verify(const char *input,const char *output,char *error,int error_size);
#endif
