// kr_source: gm_source over FFmpeg's avio (http/https/file). Seeks become HTTP Range requests.
#include "kr_source.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <libavformat/avio.h>
#include <libavutil/dict.h>
#include <libavutil/error.h>

struct kr_source {
    AVIOContext *io;
    int64_t pos;
    atomic_int aborted;
    atomic_llong io_ns;
    atomic_llong deadline_ns;
    char *url;
    int timeout_s;
    int (*extra_interrupt)(void *);
    void *interrupt_context;
};

static int64_t io_clock(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec; }
double kr_source_io_ms(const kr_source *s) { return s ? atomic_load(&s->io_ns) / 1e6 : 0; }

static int interrupted(void *opaque) {
    kr_source *s = opaque;
    int64_t deadline = atomic_load(&s->deadline_ns);
    int extra=s->extra_interrupt && s->extra_interrupt(s->interrupt_context);
    return atomic_load(&s->aborted) || (deadline && io_clock() >= deadline) || extra;
}

void kr_source_set_interrupt(kr_source *s, int (*callback)(void *), void *context) {
    if(s){s->extra_interrupt=callback;s->interrupt_context=context;}
}

static int open_at(kr_source *s, int64_t offset) {
    AVDictionary *o = NULL;
    char t[32];
    snprintf(t, sizeof t, "%lld", (long long)s->timeout_s * 1000000LL);
    av_dict_set(&o, "rw_timeout", t, 0);
    int http = !strncmp(s->url, "http://", 7) || !strncmp(s->url, "https://", 8);
    if (http) {
        // Bound speculative upstream fetching: the Drive proxy grows open-ended reads to 8 MiB.
        // Keep probing small, then use 1 MiB requests; FFmpeg advances across range boundaries.
        av_dict_set(&o, "initial_request_size", "262144", 0);
        av_dict_set(&o, "request_size", "1048576", 0);
        av_dict_set(&o, "short_seek_size", "65536", 0);
        av_dict_set(&o, "multiple_requests", "1", 0);
        snprintf(t, sizeof t, "%lld", (long long)offset);
        av_dict_set(&o, "offset", t, 0);
        // Retries belong to kr_source_read's shared deadline, not a second HTTP backoff loop.
        av_dict_set(&o, "seekable", "1", 0);  // Elementum and Drive answer Range requests
        av_dict_set(&o, "user_agent", "Kodi-iOS-AirPlay/1", 0);
    }
    AVIOInterruptCB cb = { interrupted, s };
    int r = avio_open2(&s->io, s->url, AVIO_FLAG_READ, &cb, &o);
    av_dict_free(&o);
    if (r >= 0 && !http && offset && avio_seek(s->io, offset, SEEK_SET) < 0) r = AVERROR(EIO);
    if (r < 0) { if (s->io) avio_closep(&s->io); }
    else s->pos = offset;
    return r;
}

kr_source *kr_source_open(const char *url, int timeout_s, char *err, int errlen) {
    if (!url) return NULL;
    kr_source *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->url = strdup(url);
    s->timeout_s = timeout_s > 0 ? timeout_s : 30;
    if (!s->url) { free(s); return NULL; }
    atomic_store(&s->deadline_ns, io_clock() + (int64_t)s->timeout_s * 1000000000LL);
    int r = open_at(s, 0);
    atomic_store(&s->deadline_ns, 0);
    if (r < 0) {
        if (err && errlen > 0) {
            char e[128]; av_strerror(r, e, sizeof e);
            snprintf(err, (size_t)errlen, "cannot open the stream (%s)", e);
        }
        kr_source_close(s);
        return NULL;
    }
    return s;
}

int64_t kr_source_size(kr_source *s) { return s && s->io ? avio_size(s->io) : -1; }

static int read_once(kr_source *s, int64_t offset, uint8_t *buf, int n);

// Retry a failed connection using a NEW AVIO context, at the requested offset (no probe at zero).
// All attempts share one timeout budget, so retries cannot turn a 30-second read into 90 seconds.
int kr_source_read(kr_source *s, int64_t offset, uint8_t *buf, int n) {
    if (!s || !buf || offset < 0 || n < 0 || atomic_load(&s->aborted)) return -1;
    if (!n) return 0;
    int64_t start = io_clock();
    atomic_store(&s->deadline_ns, start + (int64_t)s->timeout_s * 1000000000LL);
    int r = read_once(s, offset, buf, n);
    for (int k = 0; r < 0 && k < 2 && !interrupted(s); k++) {
        if (s->io) avio_closep(&s->io);
        if (open_at(s, offset) >= 0) r = read_once(s, offset, buf, n);
    }
    atomic_store(&s->deadline_ns, 0);
    atomic_fetch_add(&s->io_ns, io_clock() - start);
    return r;
}

static int read_once(kr_source *s, int64_t offset, uint8_t *buf, int n) {
    if (!s || !s->io || atomic_load(&s->aborted)) return -1;
    if (offset != s->pos) {
        int64_t r = avio_seek(s->io, offset, SEEK_SET);
        if (r < 0) return -1;
        s->pos = offset;
    }
    int got = 0;
    while (got < n) {
        int r = avio_read(s->io, buf + got, n - got);
        if (r == AVERROR_EOF || r == 0) break;
        if (r < 0) { if (!got) return -1; break; }
        got += r;
    }
    s->pos += got;
    return got;
}

static int64_t gm_size(void *ctx) { return kr_source_size(ctx); }
static int gm_read(void *ctx, int64_t off, uint8_t *buf, int n) { return kr_source_read(ctx, off, buf, n); }

gm_source kr_source_gm(kr_source *s) { gm_source g = { s, gm_size, gm_read }; return g; }

void kr_source_abort(kr_source *s) { if (s) atomic_store(&s->aborted, 1); }

void kr_source_close(kr_source *s) {
    if (!s) return;
    s->extra_interrupt=NULL;s->interrupt_context=NULL;
    if (s->io) avio_closep(&s->io);
    free(s->url);
    free(s);
}
