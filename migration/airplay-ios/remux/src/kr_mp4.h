// Inspect sample metadata inside coalesced storage fragments; never read their media payloads.
#ifndef KR_MP4_H
#define KR_MP4_H
#include "kr_source.h"
typedef struct { int64_t time, offset; } kr_mp4_fragment;
// Returns a complete sorted keyframe timeline, or -1 without changing the caller's plan. Four bounded,
// independent cursors share the source cache. The interrupt also covers metadata reads and thread shutdown.
int kr_mp4_keyframes(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,double timebase,double first_time,
                     int (*interrupt)(void *),void *context,double **times,int *ntimes);
#endif
