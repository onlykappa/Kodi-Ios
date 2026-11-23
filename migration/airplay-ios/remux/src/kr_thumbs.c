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

#define KR_THUMB_COUNT 101
#define KR_THUMB_IO 32768
static atomic_int cancelled;
static pthread_mutex_t one_at_a_time = PTHREAD_MUTEX_INITIALIZER;

void kr_thumbs_cancel(void) { atomic_store(&cancelled, 1); }

typedef struct {
    kr_source *source;
    int64_t pos, size, bytes;
} thumb_io;

static int io_read(void *opaque, uint8_t *buf, int n) {
    thumb_io *io = opaque;
    if (io->size >= 0 && io->pos >= io->size) return AVERROR_EOF;
    int r = kr_source_read(io->source, io->pos, buf, n);
    if (r < 0) return AVERROR(EIO);
    if (r == 0) return AVERROR_EOF;
    io->pos += r;
    io->bytes += r;
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

typedef struct {
    int (*cancel)(void *);
    void *context;
} cancel_pair;
static cancel_pair active_cancel;
static int either_cancel(void *context) {
    (void)context;
    return atomic_load(&cancelled) || (active_cancel.cancel && active_cancel.cancel(active_cancel.context));
}

static void rest_ms(int ms) {
    if (ms <= 0) return;
    struct timespec t = {ms / 1000, (long)(ms % 1000) * 1000000L};
    nanosleep(&t, NULL);
}

static int file_exists(const char *path) { return access(path, R_OK) == 0; }

// Decodes `pkt` (one keyframe) and returns the picture fitted into a width x height RGB24 buffer (black bars), or 0.
static int picture_of(AVCodecContext *dec, AVPacket *pkt, AVFrame *frame, struct SwsContext **sws, int *sws_w, int *sws_h, int *sws_fmt,
                      uint8_t *rgb, int width, int height) {
    avcodec_flush_buffers(dec);
    if (avcodec_send_packet(dec, pkt) < 0) return 0;
    avcodec_send_packet(dec, NULL);   // drain: a keyframe on its own can sit in the decoder's reorder delay
    int got = 0;
    for (int i = 0; i < 4 && !got; i++) {
        int r = avcodec_receive_frame(dec, frame);
        if (r == 0) got = 1;
        else if (r != AVERROR(EAGAIN)) break;
    }
    if (!got) return 0;
    if (frame->width <= 0 || frame->height <= 0) { av_frame_unref(frame); return 0; }
    // fit the picture into the box, keeping its shape
    double scale = (double)width / frame->width;
    if ((double)height / frame->height < scale) scale = (double)height / frame->height;
    int w = (int)(frame->width * scale + 0.5), h = (int)(frame->height * scale + 0.5);
    if (w < 2) w = 2;
    if (h < 2) h = 2;
    w &= ~1; h &= ~1;
    if (*sws == NULL || *sws_w != frame->width || *sws_h != frame->height || *sws_fmt != frame->format) {
        sws_freeContext(*sws);
        *sws = sws_getContext(frame->width, frame->height, frame->format, w, h, AV_PIX_FMT_RGB24, SWS_AREA, NULL, NULL, NULL);
        *sws_w = frame->width; *sws_h = frame->height; *sws_fmt = frame->format;
    }
    if (!*sws) { av_frame_unref(frame); return 0; }
    memset(rgb, 0, (size_t)width * height * 3);
    int x0 = (width - w) / 2, y0 = (height - h) / 2;
    uint8_t *dst[4] = { rgb + ((size_t)y0 * width + x0) * 3, NULL, NULL, NULL };
    int stride[4] = { width * 3, 0, 0, 0 };
    sws_scale(*sws, (const uint8_t *const *)frame->data, frame->linesize, 0, frame->height, dst, stride);
    av_frame_unref(frame);
    return 1;
}

int kr_thumbs_make(const char *url, const char *out_dir, int width, int height, int quality, int pause_ms,
                   int (*cancel)(void *), void *context, kr_thumbs_result *result, char *err, int errlen) {
    if (!url || !out_dir || width < 16 || height < 16 || width > 1280 || height > 720) { fail(err, errlen, "bad arguments"); return -1; }
    if (pthread_mutex_trylock(&one_at_a_time) != 0) { fail(err, errlen, "busy"); return -1; }
    atomic_store(&cancelled, 0);
    active_cancel.cancel = cancel; active_cancel.context = context;
    struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    kr_thumbs_result local = { 0, KR_THUMB_COUNT, 0, 0 };
    int ret = -1, have = 0;
    kr_source *src = NULL;
    AVFormatContext *fmt = NULL;
    AVIOContext *avio = NULL;
    AVCodecContext *dec = NULL;
    AVPacket *pkt = av_packet_alloc();
    AVFrame *frame = av_frame_alloc();
    struct SwsContext *sws = NULL;
    int sws_w = 0, sws_h = 0, sws_fmt = -1;
    uint8_t *rgb = malloc((size_t)width * height * 3);
    uint8_t *iobuf = NULL;
    thumb_io io = { 0, 0, -1, 0 };
    char path[1024], tmp[1100], what[200] = "";
#ifdef __APPLE__
    pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
#endif
    if (!pkt || !frame || !rgb) { fail(err, errlen, "out of memory"); goto end; }
    src = kr_source_open_interruptible(url, 12, either_cancel, NULL, what, sizeof what);
    if (!src) { fail(err, errlen, what[0] ? what : "cannot open the source"); goto end; }
    io.source = src; io.size = kr_source_size(src);
    iobuf = av_malloc(KR_THUMB_IO);
    avio = iobuf ? avio_alloc_context(iobuf, KR_THUMB_IO, 0, &io, io_read, NULL, io_seek) : NULL;
    fmt = avformat_alloc_context();
    if (!avio || !fmt) { fail(err, errlen, "out of memory"); goto end; }
    fmt->pb = avio;
    fmt->flags |= AVFMT_FLAG_CUSTOM_IO;
    AVDictionary *options = NULL;
    av_dict_set(&options, "probesize", "1048576", 0);
    av_dict_set(&options, "analyzeduration", "1000000", 0);
    int r = avformat_open_input(&fmt, NULL, NULL, &options);
    av_dict_free(&options);
    if (r < 0) { fmt = NULL; fail(err, errlen, "not a video this build can open"); goto end; }
    if (avformat_find_stream_info(fmt, NULL) < 0) { fail(err, errlen, "cannot read the streams"); goto end; }
    int vi = av_find_best_stream(fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (vi < 0) { fail(err, errlen, "no video"); goto end; }
    AVStream *vs = fmt->streams[vi];
    for (unsigned i = 0; i < fmt->nb_streams; i++) if ((int)i != vi) fmt->streams[i]->discard = AVDISCARD_ALL;
    double duration = fmt->duration > 0 ? fmt->duration / (double)AV_TIME_BASE : (vs->duration > 0 ? vs->duration * av_q2d(vs->time_base) : 0);
    if (duration < 5) { fail(err, errlen, "length unknown"); goto end; }
    const AVCodec *codec = vs->codecpar->codec_id == AV_CODEC_ID_AV1 ? avcodec_find_decoder_by_name("libdav1d") : NULL;
    if (!codec) codec = avcodec_find_decoder(vs->codecpar->codec_id);
    if (!codec) { fail(err, errlen, "no decoder for this video"); goto end; }
    dec = avcodec_alloc_context3(codec);
    if (!dec || avcodec_parameters_to_context(dec, vs->codecpar) < 0) { fail(err, errlen, "decoder setup"); goto end; }
    dec->thread_count = 1;
    if (avcodec_open2(dec, codec, NULL) < 0) { fail(err, errlen, "decoder will not open"); goto end; }
    for (int n = 0; n < KR_THUMB_COUNT; n++) {
        snprintf(path, sizeof path, "%s/%d.jpg", out_dir, n);
        if (file_exists(path)) { have++; continue; }
        if (either_cancel(NULL)) break;
        double at = duration * n / 100.0;
        if (n == 100) at = duration - 1.0;
        if (at < 0) at = 0;
        int64_t ts = av_rescale_q((int64_t)(at * AV_TIME_BASE), AV_TIME_BASE_Q, vs->time_base);
        if (vs->start_time != AV_NOPTS_VALUE) ts += vs->start_time;
        if (av_seek_frame(fmt, vi, ts, AVSEEK_FLAG_BACKWARD) < 0) continue;
        int made = 0;
        for (int tries = 0; tries < 400 && !made; tries++) {
            if (av_read_frame(fmt, pkt) < 0) break;
            if (pkt->stream_index == vi && (pkt->flags & AV_PKT_FLAG_KEY))
                made = picture_of(dec, pkt, frame, &sws, &sws_w, &sws_h, &sws_fmt, rgb, width, height);
            av_packet_unref(pkt);
            if (either_cancel(NULL)) break;
        }
        if (!made) continue;
        snprintf(tmp, sizeof tmp, "%s.part", path);
        if (!stbi_write_jpg(tmp, width, height, 3, rgb, quality < 1 ? 1 : quality > 100 ? 100 : quality) || rename(tmp, path) != 0) { remove(tmp); continue; }
        have++; local.made++;
        rest_ms(pause_ms);
    }
    if (have >= KR_THUMB_COUNT) {
        snprintf(path, sizeof path, "%s/done", out_dir);
        FILE *marker = fopen(path, "w");
        if (marker) { fputs("101\n", marker); fclose(marker); }
    }
    ret = have;
end:
    if (dec) avcodec_free_context(&dec);
    if (fmt) avformat_close_input(&fmt);
    if (avio) { av_freep(&avio->buffer); avio_context_free(&avio); } else av_free(iobuf);
    if (src) kr_source_close(src);
    sws_freeContext(sws);
    av_frame_free(&frame);
    av_packet_free(&pkt);
    free(rgb);
    struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
    local.seconds = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    local.bytes = io.bytes;
    if (result) *result = local;
    active_cancel.cancel = NULL;
    pthread_mutex_unlock(&one_at_a_time);
    return ret;
}

// Entry points for Kodi's Python (ctypes). Blocking: call from a thread. `out` gets "reason|made=N|bytes=B|seconds=S".
__attribute__((visibility("default"))) int kodi_thumbs_make(const char *url, const char *out_dir, int width, int height, int quality, int pause_ms,
                                                           char *out, int outlen) {
    kr_thumbs_result r = { 0, KR_THUMB_COUNT, 0, 0 };
    char err[200] = "";
    int n = kr_thumbs_make(url, out_dir, width, height, quality, pause_ms, NULL, NULL, &r, err, sizeof err);
    if (out && outlen > 0) snprintf(out, outlen, "%s|made=%d|bytes=%lld|seconds=%.1f", err, r.made, (long long)r.bytes, r.seconds);
    return n;
}
__attribute__((visibility("default"))) void kodi_thumbs_cancel(void) { kr_thumbs_cancel(); }
