// kr_thumbs: the seek bar's preview strip. One small JPEG every KR_THUMB_STEP seconds of a video (0.jpg, 1.jpg ...: picture i is the keyframe at or before i * step
// seconds), so the player's card can show where a drag is going. The grid (step, count, seconds) is written to out_dir/grid. Kodi iOS.
//
// A SESSION keeps one video open (its container probed once, one decoder): opening a debrid file from nothing costs seconds, a picture from an open session one seek and one
// keyframe. Two ways to ask it for pictures, from different threads: kr_thumbs_fill makes the whole strip in the background (the pictures near `center` first), and
// kr_thumbs_frame makes ONE now, for the picture the finger rests on; a frame request waits for the picture in hand, at most about a second.
#ifndef KR_THUMBS_H
#define KR_THUMBS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define KR_THUMB_STEP 5      // seconds between pictures
#define KR_THUMB_MAX 2400    // most pictures for one video: a longer one gets a wider step
typedef struct kr_thumbs kr_thumbs;
typedef struct {
    int made;          // pictures written by this call (existing ones are kept and not counted)
    int held;          // pictures the folder holds afterwards
    int count;         // pictures the whole strip has
    int64_t bytes;     // bytes read from the source since the session opened
    double seconds;    // wall time of the call
} kr_thumbs_result;
// Opens `url` (http(s) with Range requests, or a file) and prepares to write out_dir/N.jpg, width x height each (black bars when the shape differs), JPEG quality 1-100.
// NULL with err filled for a file with no video, an unknown length or no decoder. `cancel` (may be NULL) is polled inside reads too.
kr_thumbs *kr_thumbs_open(const char *url, const char *out_dir, int width, int height, int quality, int (*cancel)(void *), void *context, char *err, int errlen);
// One picture, now: 1 when it was made, 0 when it was already there, -1 on failure. Thread-safe against kr_thumbs_fill.
int kr_thumbs_frame(kr_thumbs *t, int index, char *err, int errlen);
// Makes every missing picture, coarse first (every 6th, then every 3rd, then the rest), from picture `center` (-1: from the start) outwards, ahead first; `pause_ms` is the rest between pictures (a waiting
// kr_thumbs_frame gets its turn in it). `budget_mb` (0: none) ends it once the session has read that much from the source. Writes out_dir/done when all are there. Returns the pictures held, or -1 when stopped before the first one could be made.
int kr_thumbs_fill(kr_thumbs *t, int pause_ms, int center, int budget_mb, kr_thumbs_result *result);
// Stops a running fill and interrupts reads at once (the buffer is running low): the session stays usable after kr_thumbs_resume.
void kr_thumbs_stop(kr_thumbs *t);
void kr_thumbs_resume(kr_thumbs *t);
void kr_thumbs_close(kr_thumbs *t);
// One call for tests and the idle pre-build: open, fill, close.
int kr_thumbs_make(const char *url, const char *out_dir, int width, int height, int quality, int pause_ms, int center, int budget_mb, kr_thumbs_result *result, char *err, int errlen);
#ifdef __cplusplus
}
#endif
#endif
