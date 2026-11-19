// kr_speech: a stretch of a video's sound as 16 kHz mono 16-bit samples, for on-device speech recognition (the speech
// subtitle check, ISSUE-347). Kodi iOS AirPlay framework.
#ifndef KR_SPEECH_H
#define KR_SPEECH_H
#include <stdint.h>
#define KR_SPEECH_RATE 16000
// url: a local path, file: URL or http(s) link (read through kr_source). audio: the Kodi audio stream number (the
// n-th audio track), or -1 for the file's default. Decodes from `start` for up to `seconds`, reading at most
// `max_bytes` of the file (0: no limit), so a high-bitrate stream is not read for long. *pcm is malloc'd (caller
// frees); *first is where the first sample is on the video's clock (seconds). Returns 0, or -1 with err filled.
int kr_speech_pcm(const char *url, int audio, double start, double seconds, int64_t max_bytes,
                  int16_t **pcm, int *samples, double *first, char *err, int errlen);
#endif
