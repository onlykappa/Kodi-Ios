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
};

static int64_t io_clock(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec; }
double kr_source_io_ms(const kr_source *s) { return s ? atomic_load(&s->io_ns) / 1e6 : 0; }

static int interrupted(void *opaque) { return atomic_load(&((kr_source *)opaque)->aborted); }

kr_source *kr_source_open(const char *url, int timeout_s, char *err, int errlen) {
    kr_source *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    AVDictionary *o = NULL;
    char t[32];
    snprintf(t, sizeof t, "%lld", (long long)(timeout_s > 0 ? timeout_s : 30) * 1000000LL);
    av_dict_set(&o, "rw_timeout", t, 0);
    if (!strncmp(url, "http", 4)) {
        av_dict_set(&o, "reconnect", "1", 0);
        // r9: give up a dead connection in seconds, not FFmpeg's 120-s backoff (build-138: audio after a seek hung
        // until the session ended); kr_source_read reopens at the offset instead.
        av_dict_set(&o, "reconnect_on_network_error", "1", 0);
        av_dict_set(&o, "reconnect_delay_max", "2", 0);
        av_dict_set(&o, "reconnect_max_retries", "3", 0);
        av_dict_set(&o, "seekable", "1", 0);  // Elementum and Drive answer Range requests
        av_dict_set(&o, "user_agent", "Kodi-iOS-AirPlay/1", 0);
    }
    AVIOInterruptCB cb = { interrupted, s };
    int r = avio_open2(&s->io, url, AVIO_FLAG_READ, &cb, &o);
    av_dict_free(&o);
    if (r < 0) {
        if (err && errlen > 0) {
            char e[128]; av_strerror(r, e, sizeof e);
            snprintf(err, (size_t)errlen, "cannot open the stream (%s)", e);
        }
        free(s);
        return NULL;
    }
    return s;
}

int64_t kr_source_size(kr_source *s) { return s && s->io ? avio_size(s->io) : -1; }

static int read_once(kr_source *s, int64_t offset, uint8_t *buf, int n);

// r9: a failed read (seek refused, connection dropped) is tried again from a fresh Range request at the offset.
int kr_source_read(kr_source *s, int64_t offset, uint8_t *buf, int n) {
    int64_t start = io_clock();
    int r = read_once(s, offset, buf, n);
    for (int k = 0; r < 0 && k < 2 && s && s->io && !atomic_load(&s->aborted); k++) {
        avio_seek(s->io, offset, SEEK_SET | AVSEEK_FORCE);
        s->pos = -1;  // forces the seek in read_once
        r = read_once(s, offset, buf, n);
    }
    if (s) atomic_fetch_add(&s->io_ns, io_clock() - start);
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
    if (s->io) avio_closep(&s->io);
    free(s);
}
