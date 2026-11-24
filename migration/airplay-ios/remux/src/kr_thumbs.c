// kr_thumbs: see kr_thumbs.h. Software decode of one keyframe per picture over kr_source (HTTP Range or file).
#include "kr_thumbs.h"
#include "kr_source.h"
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libavutil/mathematics.h>
#include <libswscale/swscale.h>
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#ifdef __APPLE__
#include <pthread/qos.h>
#endif

#define KR_THUMB_IO 32768
#define KR_THUMB_REQUEST (512 * 1024)   // one range request holds a typical keyframe and is read to its end: the connection is reused for the next picture

typedef struct {
    kr_source *source;
    int64_t pos, size;
    atomic_llong bytes;
} thumb_io;

struct kr_thumbs {
    pthread_mutex_t lock;          // one picture at a time: the demuxer and the decoder are shared by fill and frame
    atomic_int stopped;            // kr_thumbs_stop: reads are interrupted, a fill ends
    atomic_int active;             // fills and frames in progress: kr_thumbs_close waits for them, so a closed session is never used by a call that is still running
    int (*cancel)(void *);
    void *cancel_context;
    thumb_io io;
    kr_source *src;
    AVFormatContext *fmt;
    AVIOContext *avio;
    AVCodecContext *dec;
    AVPacket *pkt;
    AVFrame *frame;
    struct SwsContext *sws;
    int sws_w, sws_h, sws_fmt;
    uint8_t *rgb;
    int width, height, quality, vi;
    double duration;
    int step, count;               // one picture every `step` seconds: index i is the keyframe at or before i*step; `count` of them
    char dir[900];
};

static int io_read(void *opaque, uint8_t *buf, int n) {
    thumb_io *io = opaque;
    if (io->size >= 0 && io->pos >= io->size) return AVERROR_EOF;
    int r = kr_source_read(io->source, io->pos, buf, n);
    if (r < 0) return AVERROR(EIO);
    if (r == 0) return AVERROR_EOF;
    io->pos += r;
    atomic_fetch_add(&io->bytes, r);
    return r;
}

static int64_t io_seek(void *opaque, int64_t offset, int whence) {
    thumb_io *io = opaque;
    if (whence == AVSEEK_SIZE) return io->size;
    int64_t target = whence == SEEK_SET ? offset : whence == SEEK_CUR ? io->pos + offset : whence == SEEK_END ? io->size + offset : -1;
    if (target < 0) return AVERROR(EINVAL);
    io->pos = target;
    return target;
}

static void fail(char *err, int errlen, const char *what) {
    if (err && errlen > 0) snprintf(err, errlen, "%s", what);
}

static int interrupted(void *context) {
    kr_thumbs *t = context;
    return atomic_load(&t->stopped) || (t->cancel && t->cancel(t->cancel_context));
}

static void rest_ms(int ms) {
    if (ms <= 0) return;
    struct timespec t = {ms / 1000, (long)(ms % 1000) * 1000000L};
    nanosleep(&t, NULL);
}

static int file_exists(const char *path) { return access(path, R_OK) == 0; }

// Decodes `pkt` (one keyframe) and puts the picture, fitted into width x height with black bars, in t->rgb. 1 when there is one.
static int picture_of(kr_thumbs *t) {
    avcodec_flush_buffers(t->dec);
    if (avcodec_send_packet(t->dec, t->pkt) < 0) return 0;
    avcodec_send_packet(t->dec, NULL);   // drain: a keyframe on its own can sit in the decoder's reorder delay
    int got = 0;
    for (int i = 0; i < 4 && !got; i++) {
        int r = avcodec_receive_frame(t->dec, t->frame);
        if (r == 0) got = 1;
        else if (r != AVERROR(EAGAIN)) break;
    }
    if (!got) return 0;
    AVFrame *f = t->frame;
    if (f->width <= 0 || f->height <= 0) { av_frame_unref(f); return 0; }
    double scale = (double)t->width / f->width;
    if ((double)t->height / f->height < scale) scale = (double)t->height / f->height;
    int w = (int)(f->width * scale + 0.5), h = (int)(f->height * scale + 0.5);
    if (w < 2) w = 2;
    if (h < 2) h = 2;
    w &= ~1; h &= ~1;
    if (!t->sws || t->sws_w != f->width || t->sws_h != f->height || t->sws_fmt != f->format) {
        sws_freeContext(t->sws);
        t->sws = sws_getContext(f->width, f->height, f->format, w, h, AV_PIX_FMT_RGB24, SWS_AREA, NULL, NULL, NULL);
        t->sws_w = f->width; t->sws_h = f->height; t->sws_fmt = f->format;
    }
    if (!t->sws) { av_frame_unref(f); return 0; }
    memset(t->rgb, 0, (size_t)t->width * t->height * 3);
    int x0 = (t->width - w) / 2, y0 = (t->height - h) / 2;
    uint8_t *dst[4] = { t->rgb + ((size_t)y0 * t->width + x0) * 3, NULL, NULL, NULL };
    int stride[4] = { t->width * 3, 0, 0, 0 };
    sws_scale(t->sws, (const uint8_t *const *)f->data, f->linesize, 0, f->height, dst, stride);
    av_frame_unref(f);
    return 1;
}

static kr_thumbs *open_with(const char *url, const char *out_dir, int width, int height, int quality, int (*cancel)(void *), void *context, double hint, int mfra, char *err, int errlen) {
    if (!url || !out_dir || width < 16 || height < 16 || width > 1280 || height > 720 || strlen(out_dir) > 800) { fail(err, errlen, "bad arguments"); return NULL; }
    kr_thumbs *t = calloc(1, sizeof *t);
    if (!t) { fail(err, errlen, "out of memory"); return NULL; }
    pthread_mutex_init(&t->lock, NULL);
    t->cancel = cancel; t->cancel_context = context;
    t->width = width; t->height = height; t->quality = quality < 1 ? 1 : quality > 100 ? 100 : quality;
    t->sws_fmt = -1;
    snprintf(t->dir, sizeof t->dir, "%s", out_dir);
    char what[200] = "";
    t->pkt = av_packet_alloc();
    t->frame = av_frame_alloc();
    t->rgb = malloc((size_t)width * height * 3);
    if (!t->pkt || !t->frame || !t->rgb) { fail(err, errlen, "out of memory"); goto bad; }
    t->src = kr_source_open_tuned(url, 12, interrupted, t, KR_THUMB_REQUEST, what, sizeof what);
    if (!t->src) { fail(err, errlen, what[0] ? what : "cannot open the source"); goto bad; }
    t->io.source = t->src; t->io.size = kr_source_size(t->src);
    uint8_t *iobuf = av_malloc(KR_THUMB_IO);
    t->avio = iobuf ? avio_alloc_context(iobuf, KR_THUMB_IO, 0, &t->io, io_read, NULL, io_seek) : NULL;
    t->fmt = avformat_alloc_context();
    if (!t->avio || !t->fmt) { if (!t->avio) av_free(iobuf); fail(err, errlen, "out of memory"); goto bad; }
    t->fmt->pb = t->avio;
    t->fmt->flags |= AVFMT_FLAG_CUSTOM_IO;
    AVDictionary *options = NULL;
    av_dict_set(&options, "probesize", "1048576", 0);
    av_dict_set(&options, "analyzeduration", "1000000", 0);
    // A fragmented MP4 (a Drive copy) is opened by its fragment index, as the player does, not by reading every fragment: 139 s became 2.7 s in the model of a phone's network
    // (owner log b142eafc: 72 s). Its length is then only the first fragment's, so the caller's hint is used, or, with none, the file is opened the slow way.
    if (mfra) av_dict_set(&options, "use_mfra_for", "pts", 0);
    int r = avformat_open_input(&t->fmt, NULL, NULL, &options);
    av_dict_free(&options);
    if (r < 0) { t->fmt = NULL; fail(err, errlen, "not a video this build can open"); goto bad; }
    if (avformat_find_stream_info(t->fmt, NULL) < 0) { fail(err, errlen, "cannot read the streams"); goto bad; }
    t->vi = av_find_best_stream(t->fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (t->vi < 0) { fail(err, errlen, "no video"); goto bad; }
    AVStream *vs = t->fmt->streams[t->vi];
    for (unsigned i = 0; i < t->fmt->nb_streams; i++) if ((int)i != t->vi) t->fmt->streams[i]->discard = AVDISCARD_ALL;
    t->duration = t->fmt->duration > 0 ? t->fmt->duration / (double)AV_TIME_BASE : (vs->duration > 0 ? vs->duration * av_q2d(vs->time_base) : 0);
    if (mfra && hint >= 5 && (t->duration < 5 || t->duration < hint * 0.5)) t->duration = hint;   // the index-opened length is the first fragment's
    if (t->duration < 5) { fail(err, errlen, "length unknown"); goto bad; }
    t->step = KR_THUMB_STEP;
    t->count = (int)(t->duration / t->step) + 1;
    if (t->count > KR_THUMB_MAX) { t->step = (int)(t->duration / (KR_THUMB_MAX - 1)) + 1; t->count = (int)(t->duration / t->step) + 1; }
    if (t->count < 2) t->count = 2;
    {   // the grid, for the player's Python: step, count, duration (whole seconds)
        char gpath[1000];
        snprintf(gpath, sizeof gpath, "%s/grid", t->dir);
        FILE *g = fopen(gpath, "w");
        if (g) { fprintf(g, "%d %d %d\n", t->step, t->count, (int)t->duration); fclose(g); }
    }
    const AVCodec *codec = vs->codecpar->codec_id == AV_CODEC_ID_AV1 ? avcodec_find_decoder_by_name("libdav1d") : NULL;
    if (!codec) codec = avcodec_find_decoder(vs->codecpar->codec_id);
    if (!codec) { fail(err, errlen, "no decoder for this video"); goto bad; }
    t->dec = avcodec_alloc_context3(codec);
    if (!t->dec || avcodec_parameters_to_context(t->dec, vs->codecpar) < 0) { fail(err, errlen, "decoder setup"); goto bad; }
    t->dec->thread_count = 1;
    if (avcodec_open2(t->dec, codec, NULL) < 0) { fail(err, errlen, "decoder will not open"); goto bad; }
    return t;
bad:
    kr_thumbs_close(t);
    return NULL;
}

kr_thumbs *kr_thumbs_open_hint(const char *url, const char *out_dir, int width, int height, int quality, double duration_hint, int (*cancel)(void *), void *context, char *err, int errlen) {
    kr_thumbs *t = open_with(url, out_dir, width, height, quality, cancel, context, duration_hint, 1, err, errlen);
    if (!t && duration_hint < 5 && err && errlen > 0 && strcmp(err, "length unknown") == 0) {   // no length by the quick way and none given: the slow way
        err[0] = 0;
        t = open_with(url, out_dir, width, height, quality, cancel, context, 0, 0, err, errlen);
    }
    return t;
}

kr_thumbs *kr_thumbs_open(const char *url, const char *out_dir, int width, int height, int quality, int (*cancel)(void *), void *context, char *err, int errlen) {
    return kr_thumbs_open_hint(url, out_dir, width, height, quality, 0, cancel, context, err, errlen);
}

// The picture for one percent, with t->lock held. 1 made, 0 there already, -1 failed.
static int make_one(kr_thumbs *t, int index) {
    char path[1000], tmp[1010];
    snprintf(path, sizeof path, "%s/%d.jpg", t->dir, index);
    if (file_exists(path)) return 0;
    AVStream *vs = t->fmt->streams[t->vi];
    double at = (double)index * t->step;
    if (at > t->duration - 1.0) at = t->duration - 1.0;
    if (at < 0) at = 0;
    int64_t ts = av_rescale_q((int64_t)(at * AV_TIME_BASE), AV_TIME_BASE_Q, vs->time_base);
    if (vs->start_time != AV_NOPTS_VALUE) ts += vs->start_time;
    if (av_seek_frame(t->fmt, t->vi, ts, AVSEEK_FLAG_BACKWARD) < 0) return -1;
    int made = 0;
    for (int tries = 0; tries < 400 && !made; tries++) {
        if (interrupted(t)) break;
        if (av_read_frame(t->fmt, t->pkt) < 0) break;
        if (t->pkt->stream_index == t->vi && (t->pkt->flags & AV_PKT_FLAG_KEY)) made = picture_of(t);
        av_packet_unref(t->pkt);
    }
    if (!made) return -1;
    snprintf(tmp, sizeof tmp, "%s.part", path);
    if (!stbi_write_jpg(tmp, t->width, t->height, 3, t->rgb, t->quality) || rename(tmp, path) != 0) { remove(tmp); return -1; }
    return 1;
}

int kr_thumbs_frame(kr_thumbs *t, int index, char *err, int errlen) {
    if (!t || index < 0 || index >= t->count) { fail(err, errlen, "bad index"); return -1; }
    atomic_fetch_add(&t->active, 1);
    pthread_mutex_lock(&t->lock);
    int r = make_one(t, index);
    pthread_mutex_unlock(&t->lock);
    if (r < 0) fail(err, errlen, interrupted(t) ? "stopped" : "no picture there");
    atomic_fetch_sub(&t->active, 1);
    return r;
}

// The order the pictures are made in. Coarse first, so the whole film has a picture within a minute of any point as early as possible (a drag then always has something
// near to show): every 12th picture (one a minute), then every 6th, every 3rd, then the rest; inside a round the one at `center` first, then one ahead, one behind, two
// ahead ... (ahead first: that is where a drag usually goes). Returns how many are listed.
static int level_of(int i) { return i % 12 == 0 ? 0 : i % 6 == 0 ? 1 : i % 3 == 0 ? 2 : 3; }
static int make_order(int center, int count, int *order) {
    int n = 0;
    if (center < 0 || center >= count) center = 0;
    for (int level = 0; level < 4; level++) {
        for (int d = 0; d < count; d++) {
            int a = center + d, b = center - d;
            if (a < count && level_of(a) == level) order[n++] = a;
            if (d && b >= 0 && level_of(b) == level) order[n++] = b;
        }
    }
    return n;
}

static int held_count(kr_thumbs *t) {
    char path[1000];
    int have = 0;
    for (int n = 0; n < t->count; n++) {
        snprintf(path, sizeof path, "%s/%d.jpg", t->dir, n);
        if (file_exists(path)) have++;
    }
    return have;
}

int kr_thumbs_fill(kr_thumbs *t, int pause_ms, int center, int budget_mb, kr_thumbs_result *result) {
    if (!t) return -1;
    atomic_fetch_add(&t->active, 1);
#ifdef __APPLE__
    pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
#endif
    struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    int *order = malloc(sizeof(int) * (size_t)t->count * 2), made = 0, failures = 0, listed = 0;
    if (!order) { atomic_fetch_sub(&t->active, 1); return -1; }
    listed = make_order(center, t->count, order);
    long long budget = budget_mb > 0 ? (long long)budget_mb * 1024 * 1024 : 0;
    for (int step = 0; step < listed && !interrupted(t); step++) {
        if (budget && atomic_load(&t->io.bytes) >= budget) break;   // the data allowance for this title is spent
        pthread_mutex_lock(&t->lock);
        int r = make_one(t, order[step]);
        pthread_mutex_unlock(&t->lock);
        if (r > 0) { made++; rest_ms(pause_ms); }   // a waiting kr_thumbs_frame takes the lock in this rest
        else if (r < 0 && ++failures > 12) break;   // a file whose keyframes will not decode: do not go on for ever
    }
    free(order);
    int have = held_count(t);
    if (have >= t->count) {
        char path[1000];
        snprintf(path, sizeof path, "%s/done", t->dir);
        FILE *marker = fopen(path, "w");
        if (marker) { fprintf(marker, "%d\n", t->count); fclose(marker); }
    }
    struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
    if (result) { result->made = made; result->held = have; result->count = t->count; result->bytes = atomic_load(&t->io.bytes); result->seconds = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9; }
    atomic_fetch_sub(&t->active, 1);
    return have;
}

void kr_thumbs_stop(kr_thumbs *t) { if (t) atomic_store(&t->stopped, 1); }
void kr_thumbs_resume(kr_thumbs *t) { if (t) atomic_store(&t->stopped, 0); }

void kr_thumbs_close(kr_thumbs *t) {
    if (!t) return;
    atomic_store(&t->stopped, 1);
    // A fill or a frame in another thread ends at once (its reads are interrupted); wait for it before anything is freed. About 15 s at most, then the session is leaked
    // rather than freed under a call that is still running.
    for (int waited = 0; atomic_load(&t->active) > 0; waited++) {
        if (waited > 3000) return;
        rest_ms(5);
    }
    pthread_mutex_lock(&t->lock);
    if (t->dec) avcodec_free_context(&t->dec);
    if (t->fmt) avformat_close_input(&t->fmt);
    if (t->avio) { av_freep(&t->avio->buffer); avio_context_free(&t->avio); }
    if (t->src) kr_source_close(t->src);
    sws_freeContext(t->sws);
    av_frame_free(&t->frame);
    av_packet_free(&t->pkt);
    free(t->rgb);
    pthread_mutex_unlock(&t->lock);
    pthread_mutex_destroy(&t->lock);
    free(t);
}

int kr_thumbs_make(const char *url, const char *out_dir, int width, int height, int quality, int pause_ms, int center, int budget_mb, kr_thumbs_result *result, char *err, int errlen) {
    kr_thumbs *t = kr_thumbs_open(url, out_dir, width, height, quality, NULL, NULL, err, errlen);
    if (!t) return -1;
    int have = kr_thumbs_fill(t, pause_ms, center, budget_mb, result);
    kr_thumbs_close(t);
    return have;
}

// Entry points for Kodi's Python (ctypes). The handle is a pointer carried as a 64-bit integer; 0 is "no session". All of them but open/close may be called from
// different threads for one session (a fill in one, frame requests in another).
#define KR_EXPORT __attribute__((visibility("default")))
KR_EXPORT int64_t kodi_thumbs_open(const char *url, const char *out_dir, int width, int height, int quality, char *err, int errlen) {
    return (int64_t)(intptr_t)kr_thumbs_open(url, out_dir, width, height, quality, NULL, NULL, err, errlen);
}
// With the length the player knows, in seconds (0: none): a fragmented MP4 is then opened by its fragment index (quick) and the length is taken from the hint.
KR_EXPORT int64_t kodi_thumbs_open2(const char *url, const char *out_dir, int width, int height, int quality, int duration_hint, char *err, int errlen) {
    return (int64_t)(intptr_t)kr_thumbs_open_hint(url, out_dir, width, height, quality, (double)duration_hint, NULL, NULL, err, errlen);
}
KR_EXPORT int kodi_thumbs_frame(int64_t handle, int index, char *err, int errlen) { return kr_thumbs_frame((kr_thumbs *)(intptr_t)handle, index, err, errlen); }
KR_EXPORT int kodi_thumbs_fill(int64_t handle, int pause_ms, int center, int budget_mb, char *out, int outlen) {
    kr_thumbs_result r = { 0, 0, 0, 0, 0 };
    int n = kr_thumbs_fill((kr_thumbs *)(intptr_t)handle, pause_ms, center, budget_mb, &r);
    if (out && outlen > 0) snprintf(out, outlen, "made=%d|held=%d|count=%d|bytes=%lld|seconds=%.1f", r.made, r.held, r.count, (long long)r.bytes, r.seconds);
    return n;
}
KR_EXPORT void kodi_thumbs_stop(int64_t handle) { kr_thumbs_stop((kr_thumbs *)(intptr_t)handle); }
KR_EXPORT void kodi_thumbs_resume(int64_t handle) { kr_thumbs_resume((kr_thumbs *)(intptr_t)handle); }
KR_EXPORT void kodi_thumbs_close(int64_t handle) { kr_thumbs_close((kr_thumbs *)(intptr_t)handle); }
