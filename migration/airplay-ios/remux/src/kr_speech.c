#include "kr_speech.h"
#include "kr_source.h"
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { kr_source *src; int64_t pos, read, limit; } reader;

static int in_read(void *o, uint8_t *buf, int n) {
    reader *r = o;
    if (r->limit && r->read >= r->limit) return AVERROR_EOF;   // the byte budget is spent: what was decoded is kept
    int got = kr_source_read(r->src, r->pos, buf, n);
    if (got > 0) { r->pos += got; r->read += got; return got; }
    return got == 0 ? AVERROR_EOF : AVERROR(EIO);
}
static int64_t in_seek(void *o, int64_t off, int whence) {
    reader *r = o;
    int64_t size = kr_source_size(r->src);
    switch (whence & ~AVSEEK_FORCE) {
        case AVSEEK_SIZE: return size;
        case SEEK_SET: r->pos = off; break;
        case SEEK_CUR: r->pos += off; break;
        case SEEK_END: if (size < 0) return -1; r->pos = size + off; break;
        default: return -1;
    }
    return r->pos;
}
static int fail(char *err, int len, const char *what, int code) {
    if (err && len > 0) {
        char e[96] = ""; if (code < 0) av_strerror(code, e, sizeof e);
        snprintf(err, (size_t)len, "speech sample: %s%s%s", what, *e ? ": " : "", e);
    }
    return -1;
}

int kr_speech_pcm(const char *url, int audio, double start, double seconds, int64_t max_bytes,
                  int16_t **pcm, int *samples, double *first, char *err, int errlen) {
    if (!url || !pcm || !samples || !first || !isfinite(start) || start < 0 || !isfinite(seconds) || seconds <= 0 || seconds > 600)
        return fail(err, errlen, "bad arguments", 0);
    *pcm = NULL; *samples = 0; *first = -1;
    char link[4200];
    if (url[0] == '/') snprintf(link, sizeof link, "file:%s", url); else snprintf(link, sizeof link, "%s", url);
    reader r = {0};
    AVFormatContext *f = NULL; AVCodecContext *dec = NULL; SwrContext *swr = NULL; AVPacket *p = NULL; AVFrame *fr = NULL;
    AVIOContext *io = NULL; int16_t *out = NULL; int want = (int)(seconds * KR_SPEECH_RATE), have = 0, result = -1, q;
    r.src = kr_source_open(link, 20, err, errlen); r.limit = max_bytes;
    if (!r.src) return -1;
    uint8_t *iob = av_malloc(1 << 16);
    io = iob ? avio_alloc_context(iob, 1 << 16, 0, &r, in_read, NULL, in_seek) : NULL;
    f = avformat_alloc_context();
    if (!io || !f) { if (!io) av_free(iob); fail(err, errlen, "out of memory", 0); goto end; }
    f->pb = io; f->probesize = 2 * 1024 * 1024; f->max_analyze_duration = 2 * AV_TIME_BASE;
    if ((q = avformat_open_input(&f, NULL, NULL, NULL)) < 0) { f = NULL; fail(err, errlen, "open", q); goto end; }
    if ((q = avformat_find_stream_info(f, NULL)) < 0) { fail(err, errlen, "probe", q); goto end; }
    int index = -1;
    if (audio < 0) index = av_find_best_stream(f, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0);
    else for (unsigned i = 0, n = 0; i < f->nb_streams; i++)
        if (f->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO && (int)n++ == audio) { index = (int)i; break; }
    if (index < 0) { fail(err, errlen, "no such audio track", 0); goto end; }
    for (unsigned i = 0; i < f->nb_streams; i++) if ((int)i != index) f->streams[i]->discard = AVDISCARD_ALL;
    AVStream *st = f->streams[index];
    const AVCodec *codec = avcodec_find_decoder(st->codecpar->codec_id);
    dec = codec ? avcodec_alloc_context3(codec) : NULL;
    if (!dec || avcodec_parameters_to_context(dec, st->codecpar) < 0 || (q = avcodec_open2(dec, codec, NULL)) < 0) {
        fail(err, errlen, "no decoder for this sound", codec ? q : 0); goto end;
    }
    AVChannelLayout mono = AV_CHANNEL_LAYOUT_MONO;
    // The default downmix keeps the centre channel (where films put the dialogue) at -3 dB.
    if ((q = swr_alloc_set_opts2(&swr, &mono, AV_SAMPLE_FMT_S16, KR_SPEECH_RATE, &dec->ch_layout, dec->sample_fmt,
                                 dec->sample_rate, 0, NULL)) < 0 || (q = swr_init(swr)) < 0) { fail(err, errlen, "resampler", q); goto end; }
    out = malloc((size_t)want * sizeof *out + 64 * sizeof *out); p = av_packet_alloc(); fr = av_frame_alloc();
    if (!out || !p || !fr) { fail(err, errlen, "out of memory", 0); goto end; }
    double tb = av_q2d(st->time_base);
    if (start > 0) av_seek_frame(f, index, (int64_t)(start / tb), AVSEEK_FLAG_BACKWARD);   // a failed seek decodes from the top
    int eof = 0;
    while (have < want && !eof) {
        q = av_read_frame(f, p);
        if (q < 0) { eof = 1; avcodec_send_packet(dec, NULL); }
        else if (p->stream_index != index) { av_packet_unref(p); continue; }
        else { q = avcodec_send_packet(dec, p); av_packet_unref(p); if (q < 0 && q != AVERROR(EAGAIN)) continue; }
        while (have < want && avcodec_receive_frame(dec, fr) == 0) {
            int64_t ts = fr->best_effort_timestamp;
            double at = ts == AV_NOPTS_VALUE ? -1 : ts * tb, len = fr->sample_rate > 0 ? (double)fr->nb_samples / fr->sample_rate : 0;
            if (at >= 0 && at + len <= start) { av_frame_unref(fr); continue; }   // before the stretch (seeks land early)
            if (*first < 0) *first = at >= 0 ? at : start;
            uint8_t *dst = (uint8_t *)(out + have);
            int made = swr_convert(swr, &dst, want - have, (const uint8_t **)fr->extended_data, fr->nb_samples);
            av_frame_unref(fr);
            if (made < 0) { fail(err, errlen, "resample", made); goto end; }
            have += made;
        }
    }
    if (have < KR_SPEECH_RATE) { fail(err, errlen, "less than a second of sound", 0); goto end; }
    *pcm = out; out = NULL; *samples = have; result = 0;
end:
    free(out); av_frame_free(&fr); av_packet_free(&p); swr_free(&swr); avcodec_free_context(&dec);
    if (f) avformat_close_input(&f); else avformat_free_context(f);
    if (io) { av_freep(&io->buffer); avio_context_free(&io); }
    kr_source_close(r.src);
    return result;
}
