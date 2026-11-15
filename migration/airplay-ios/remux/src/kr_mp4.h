// Inspect sample metadata inside coalesced storage fragments; never read their media payloads.
#ifndef KR_MP4_H
#define KR_MP4_H
#include "kr_source.h"
typedef struct { int64_t time, offset; } kr_mp4_fragment;
// Returns a complete sorted keyframe timeline, or -1 without changing the caller's plan. Four bounded,
// independent cursors share the source cache. The interrupt also covers metadata reads and thread shutdown.
int kr_mp4_keyframes(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,double timebase,double first_time,
                     int (*interrupt)(void *),void *context,double **times,int *ntimes);
// ISSUE-346: the same scan in the track's own ticks, so it can be kept and re-timed. first: the presentation time
// of the first sample of the first fragment. kr_mp4_moof_keys adds one fragment header's keyframes (preparation reads
// each header as it is written); kr_mp4_keys_times gives kr_mp4_keyframes' sorted seconds from them.
typedef struct { int64_t *ticks; int n, cap; int64_t first; int has_first; } kr_mp4_keys;
int kr_mp4_keyframe_ticks(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,
                          int (*interrupt)(void *),void *context,kr_mp4_keys *out);
int kr_mp4_moof_keys(const uint8_t *moof,uint32_t len,int track,kr_mp4_keys *out);
int kr_mp4_keys_times(const kr_mp4_keys *keys,double timebase,double first_time,double **times,int *ntimes);
void kr_mp4_keys_free(kr_mp4_keys *keys);
// The phone's saved scans, keyed by the file's mfra bytes, its size and the track. origin: 0 a cast, 1 preparation.
uint64_t kr_mp4_cache_key(const uint8_t *mfra,uint32_t len,int64_t size,int track);
int kr_mp4_cache_load(uint64_t key,kr_mp4_keys *out,int *origin);
void kr_mp4_cache_save(uint64_t key,const kr_mp4_keys *keys,int origin);
#endif
