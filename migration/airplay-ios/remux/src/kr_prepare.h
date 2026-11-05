// Prepare one local, seekable MP4 before playback. No server/session globals or HTTP input.
#ifndef KR_PREPARE_H
#define KR_PREPARE_H
#include <libavformat/avformat.h>
typedef int (*kr_prepare_progress)(int stage, double done, double total, void *context);
// Returns 1 only for a portable MP4 with original video resolution/HDR and AAC audio.
int kr_prepare_ready(AVFormatContext *format);
// JSON describes the file, without paths. Negative on invalid input.
int kodi_airplay_probe(const char *input, char *json, int size);
// Writes output.partial then validates and atomically renames it to output. Input is never modified.
// progress stages: 0 video, 1 audio, 2 packaging, 3 verification. Return 0 success, -2 paused, -1 failure.
int kodi_airplay_prepare(const char *input, const char *output, kr_prepare_progress progress,
                         void *context, char *error, int error_size);
#endif
