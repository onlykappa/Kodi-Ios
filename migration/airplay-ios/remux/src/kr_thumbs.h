// kr_thumbs: the seek bar's preview strip. One small JPEG per whole percent of a video's length (0.jpg ... 100.jpg), each the
// keyframe at or before that time, made in the background so the player's card can show where a drag is going. Kodi iOS.
#ifndef KR_THUMBS_H
#define KR_THUMBS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    int made;          // pictures written by this call (existing ones are kept and not counted)
    int total;         // pictures the strip has when it is complete (101)
    int64_t bytes;     // bytes read from the source
    double seconds;    // wall time of the call
} kr_thumbs_result;
// Writes out_dir/N.jpg for N = 0..100 (a picture already there is kept), then out_dir/done. width x height is the box
// every picture is fitted into (black bars when the aspect differs); quality 1-100; pause_ms is the rest between pictures so the
// work stays gentle. cancel() true (or kr_thumbs_cancel) stops it between pictures and inside a read; what was made stays.
// Returns the number of pictures the strip holds afterwards, or -1 with err filled (nothing is written for a file with no video
// or an unknown length). One call at a time per process.
int kr_thumbs_make(const char *url, const char *out_dir, int width, int height, int quality, int pause_ms,
                   int (*cancel)(void *), void *context, kr_thumbs_result *result, char *err, int errlen);
void kr_thumbs_cancel(void);
#ifdef __cplusplus
}
#endif
#endif
