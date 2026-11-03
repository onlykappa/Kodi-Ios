// kr_audio: decode -> resample -> AAC encode -> fragmented MP4, one segment at a time.
// Each segment covers whole 1024-sample AAC frames: [floor(start*SR/1024), floor(end*SR/1024)) frames, so the
// segments tile the timeline with no gap or overlap. A fresh encoder per segment is fed two frames of pre-roll that are
// dropped, so the encoder's priming does not land at the segment start.
#include "kr_audio.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/channel_layout.h>
#include <libavutil/opt.h>
#include <libswresample/swresample.h>

#define FRAME 1024
#define PREROLL (2 * FRAME)

struct kr_audio {
    gm_source src;
    int64_t pos;
    AVFormatContext *in;
    int index;
    AVCodecContext *dec;
    int rate, channels;
    AVChannelLayout layout;
    double duration;
};

static void seterr(char *err, int len, const char *what, int r) {
    if (!err || len <= 0) return;
    char e[96] = "";
    if (r < 0) av_strerror(r, e, sizeof e);
    snprintf(err, (size_t)len, "audio bridge: %s%s%s", what, *e ? ": " : "", e);
}

static int in_read(void *o, uint8_t *buf, int n) {
    kr_audio *a = o;
    int r = a->src.read(a->src.ctx, a->pos, buf, n);
    if (r > 0) { a->pos += r; return r; }
    return r == 0 ? AVERROR_EOF : AVERROR(EIO);
}

static int64_t in_seek(void *o, int64_t off, int whence) {
    kr_audio *a = o;
    int64_t size = a->src.size ? a->src.size(a->src.ctx) : -1;
    switch (whence & ~AVSEEK_FORCE) {
        case AVSEEK_SIZE: return size;
        case SEEK_SET: a->pos = off; break;
        case SEEK_CUR: a->pos += off; break;
        case SEEK_END: if (size < 0) return -1; a->pos = size + off; break;
        default: return -1;
    }
    return a->pos;
}

kr_audio *kr_audio_open(gm_source src, int index, char *err, int errlen) {
    kr_audio *a = calloc(1, sizeof *a);
    if (!a) return NULL;
    a->src = src; a->index = index;
    uint8_t *iob = av_malloc(1 << 16);
    AVIOContext *io = avio_alloc_context(iob, 1 << 16, 0, a, in_read, NULL, in_seek);
    a->in = avformat_alloc_context();
    if (!io || !a->in) { seterr(err, errlen, "out of memory", 0); av_free(iob); goto fail; }
    a->in->pb = io;
    int r = avformat_open_input(&a->in, NULL, NULL, NULL);
    if (r < 0) { seterr(err, errlen, "open", r); a->in = NULL; avio_context_free(&io); goto fail; }
    if ((r = avformat_find_stream_info(a->in, NULL)) < 0) { seterr(err, errlen, "probe", r); goto fail; }
    if (index < 0 || index >= (int)a->in->nb_streams || a->in->streams[index]->codecpar->codec_type != AVMEDIA_TYPE_AUDIO) {
        seterr(err, errlen, "no such audio track", 0); goto fail;
    }
    AVStream *st = a->in->streams[index];
    const AVCodec *dec = avcodec_find_decoder(st->codecpar->codec_id);
    if (!dec) { seterr(err, errlen, "no decoder for this audio codec", 0); goto fail; }
    a->dec = avcodec_alloc_context3(dec);
    avcodec_parameters_to_context(a->dec, st->codecpar);
    a->dec->pkt_timebase = st->time_base;
    if ((r = avcodec_open2(a->dec, dec, NULL)) < 0) { seterr(err, errlen, "decoder", r); goto fail; }
    int src_rate = st->codecpar->sample_rate > 0 ? st->codecpar->sample_rate : 48000;
    a->rate = src_rate > 48000 ? 48000 : (src_rate < 32000 ? 48000 : src_rate);
    a->channels = st->codecpar->ch_layout.nb_channels >= 6 ? 6 : 2;
    av_channel_layout_default(&a->layout, a->channels);
    a->duration = a->in->duration > 0 ? a->in->duration / (double)AV_TIME_BASE : 0;
    for (unsigned i = 0; i < a->in->nb_streams; i++) a->in->streams[i]->discard = i == (unsigned)index ? AVDISCARD_DEFAULT : AVDISCARD_ALL;
    return a;
fail:
    kr_audio_close(a);
    return NULL;
}

int kr_audio_channels(const kr_audio *a) { return a ? a->channels : 0; }
int kr_audio_sample_rate(const kr_audio *a) { return a ? a->rate : 0; }

void kr_audio_close(kr_audio *a) {
    if (!a) return;
    avcodec_free_context(&a->dec);
    if (a->in) {
        AVIOContext *io = a->in->pb;
        avformat_close_input(&a->in);
        if (io) { av_freep(&io->buffer); avio_context_free(&io); }
    }
    av_channel_layout_uninit(&a->layout);
    free(a);
}

int kr_first_moof(const uint8_t *p, int len) {
    int off = 0;
    while (off + 8 <= len) {
        uint64_t size = ((uint32_t)p[off] << 24) | (p[off+1] << 16) | (p[off+2] << 8) | p[off+3];
        if (!memcmp(p + off + 4, "moof", 4)) return off;
        if (size == 1 && off + 16 <= len) { size = 0; for (int k = 0; k < 8; k++) size = size << 8 | p[off+8+k]; }
        if (size < 8) return -1;
        off += (int)size;
    }
    return -1;
}

// ── output into a gm_buf ───────────────────────────────────────────────────────
typedef struct { gm_buf *b; int64_t pos; } wctx;
static int ensure(gm_buf *b, int64_t need) {
    if (need <= b->cap) return 0;
    int64_t cap = b->cap ? b->cap : 65536;
    while (cap < need) cap *= 2;
    uint8_t *q = realloc(b->data, (size_t)cap);
    if (!q) return -1;
    b->data = q; b->cap = (int)cap;
    return 0;
}
static int w_write(void *o, const uint8_t *buf, int n) {
    wctx *w = o;
    if (ensure(w->b, w->pos + n) < 0) return AVERROR(ENOMEM);
    memcpy(w->b->data + w->pos, buf, (size_t)n);
    w->pos += n;
    if (w->pos > w->b->len) w->b->len = (int)w->pos;
    return n;
}
static int64_t w_seek(void *o, int64_t off, int whence) {
    wctx *w = o;
    if (whence == AVSEEK_SIZE) return w->b->len;
    if (whence == SEEK_SET) w->pos = off; else if (whence == SEEK_CUR) w->pos += off; else if (whence == SEEK_END) w->pos = w->b->len + off;
    return w->pos;
}

// PCM collected for [first, first + have) samples, planar float, a->channels planes.
typedef struct { float *pl[8]; int64_t first, have, cap; } pcm;
static int pcm_put(pcm *p, int ch, int64_t at, float **data, int n) {
    if (at < p->first + p->have) {  // overlap with what we have: drop the repeated part
        int64_t skip = p->first + p->have - at;
        if (skip >= n) return 0;
        at += skip; n -= (int)skip;
        for (int c = 0; c < ch; c++) data[c] += skip;
    }
    int64_t gap = at - (p->first + p->have);  // a hole in the source: silence
    if (p->have + gap + n > p->cap) {
        int64_t cap = p->cap ? p->cap : 1 << 16;
        while (cap < p->have + gap + n) cap *= 2;
        for (int c = 0; c < ch; c++) { float *q = realloc(p->pl[c], (size_t)cap * sizeof(float)); if (!q) return -1; p->pl[c] = q; }
        p->cap = cap;
    }
    for (int c = 0; c < ch; c++) {
        memset(p->pl[c] + p->have, 0, (size_t)gap * sizeof(float));
        memcpy(p->pl[c] + p->have + gap, data[c], (size_t)n * sizeof(float));
    }
    p->have += gap + n;
    return 0;
}

// Decode the source over [s_begin, s_end) samples (output rate) into `p`.
static int collect(kr_audio *a, int64_t s_begin, int64_t s_end, pcm *p, char *err, int errlen) {
    AVStream *st = a->in->streams[a->index];
    double t = (double)s_begin / a->rate - 0.5;
    int64_t ts = t > 0 ? (int64_t)(t / av_q2d(st->time_base)) : 0;
    if (av_seek_frame(a->in, a->index, ts, AVSEEK_FLAG_BACKWARD) < 0) av_seek_frame(a->in, -1, 0, AVSEEK_FLAG_BACKWARD);
    avcodec_flush_buffers(a->dec);
    p->first = s_begin; p->have = 0;
    SwrContext *swr = NULL;
    AVPacket *pkt = av_packet_alloc();
    AVFrame *fr = av_frame_alloc();
    int r = 0, eof = 0;
    while (p->first + p->have < s_end && !eof) {
        r = av_read_frame(a->in, pkt);
        if (r == AVERROR_EOF) { eof = 1; avcodec_send_packet(a->dec, NULL); }
        else if (r < 0) { seterr(err, errlen, "read", r); goto out; }
        else if (pkt->stream_index != a->index) { av_packet_unref(pkt); continue; }
        else { avcodec_send_packet(a->dec, pkt); av_packet_unref(pkt); }
        while (avcodec_receive_frame(a->dec, fr) == 0) {
            int64_t pts = fr->best_effort_timestamp != AV_NOPTS_VALUE ? fr->best_effort_timestamp : fr->pts;
            if (pts == AV_NOPTS_VALUE) { av_frame_unref(fr); continue; }
            if (!swr) {
                if (swr_alloc_set_opts2(&swr, &a->layout, AV_SAMPLE_FMT_FLTP, a->rate, &fr->ch_layout,
                                        fr->format, fr->sample_rate, 0, NULL) < 0 || swr_init(swr) < 0) {
                    seterr(err, errlen, "resampler", 0); r = -1; av_frame_unref(fr); goto out;
                }
            }
            int maxout = (int)av_rescale_rnd(fr->nb_samples, a->rate, fr->sample_rate, AV_ROUND_UP) + 64;
            float *planes[8]; uint8_t *tmp = NULL;
            av_samples_alloc((uint8_t **)planes, NULL, a->channels, maxout, AV_SAMPLE_FMT_FLTP, 0);
            tmp = (uint8_t *)planes[0];
            int got = swr_convert(swr, (uint8_t **)planes, maxout, (const uint8_t **)fr->extended_data, fr->nb_samples);
            int64_t at = llround(pts * av_q2d(st->time_base) * a->rate);
            if (got > 0 && at + got > s_begin) {
                if (at < s_begin) {  // trim the part before the window
                    int skip = (int)(s_begin - at);
                    for (int c = 0; c < a->channels; c++) planes[c] += skip;
                    got -= skip; at = s_begin;
                }
                if (pcm_put(p, a->channels, at, planes, got) < 0) { av_free(tmp); seterr(err, errlen, "out of memory", 0); r = -1; av_frame_unref(fr); goto out; }
            }
            av_free(tmp);
            av_frame_unref(fr);
        }
    }
    r = 0;
out:
    av_frame_free(&fr); av_packet_free(&pkt); swr_free(&swr);
    return r;
}

// Encode samples [s0, s1) (whole frames; pre-roll before s0 when available) into a full ftyp+moov+moof+mdat unit.
static int produce(kr_audio *a, int64_t s0, int64_t s1, gm_buf *out, char *err, int errlen) {
    out->len = 0;
    int64_t begin = s0 - PREROLL > 0 ? s0 - PREROLL : 0;
    pcm p = {0};
    int r = collect(a, begin, s1 + FRAME, &p, err, errlen);
    if (r < 0) goto done;
    const AVCodec *enc = avcodec_find_encoder(AV_CODEC_ID_AAC);
    AVCodecContext *ec = enc ? avcodec_alloc_context3(enc) : NULL;
    if (!ec) { seterr(err, errlen, "no AAC encoder", 0); r = -1; goto done; }
    ec->sample_rate = a->rate; ec->sample_fmt = AV_SAMPLE_FMT_FLTP;
    av_channel_layout_copy(&ec->ch_layout, &a->layout);
    ec->bit_rate = a->channels == 6 ? 384000 : 160000;
    ec->time_base = (AVRational){1, a->rate};
    ec->flags |= AV_CODEC_FLAG_GLOBAL_HEADER | AV_CODEC_FLAG_BITEXACT;
    if ((r = avcodec_open2(ec, enc, NULL)) < 0) { seterr(err, errlen, "AAC encoder", r); avcodec_free_context(&ec); goto done; }

    AVFormatContext *oc = NULL;
    avformat_alloc_output_context2(&oc, NULL, "mp4", NULL);
    AVStream *os = oc ? avformat_new_stream(oc, NULL) : NULL;
    wctx w = { out, 0 };
    uint8_t *iob = av_malloc(1 << 16);
    AVIOContext *io = avio_alloc_context(iob, 1 << 16, 1, &w, NULL, w_write, w_seek);
    if (!os || !io) { seterr(err, errlen, "muxer", 0); r = -1; goto mux_done; }
    avcodec_parameters_from_context(os->codecpar, ec);
    os->time_base = (AVRational){1, a->rate};
    oc->pb = io;
    oc->flags |= AVFMT_FLAG_BITEXACT;
    oc->avoid_negative_ts = AVFMT_AVOID_NEG_TS_DISABLED;
    AVDictionary *o = NULL;
    av_dict_set(&o, "movflags", "frag_keyframe+empty_moov+default_base_moof+delay_moov+frag_discont", 0);
    r = avformat_write_header(oc, &o);
    av_dict_free(&o);
    if (r < 0) { seterr(err, errlen, "mux header", r); goto mux_done; }

    AVFrame *fr = av_frame_alloc();
    AVPacket *pk = av_packet_alloc();
    int64_t total = p.have;  // samples from `begin`
    int written = 0;
    for (int64_t off = 0; ; off += FRAME) {
        int flushing = off >= total || begin + off >= s1 + FRAME;
        if (!flushing) {
            fr->nb_samples = FRAME; fr->format = AV_SAMPLE_FMT_FLTP; fr->sample_rate = a->rate;
            av_channel_layout_copy(&fr->ch_layout, &a->layout);
            av_frame_get_buffer(fr, 0);
            int n = (int)(total - off < FRAME ? total - off : FRAME);
            for (int c = 0; c < a->channels; c++) {
                memcpy(fr->data[c], p.pl[c] + off, (size_t)n * sizeof(float));
                if (n < FRAME) memset((float *)fr->data[c] + n, 0, (size_t)(FRAME - n) * sizeof(float));
            }
            fr->pts = begin + off;
            r = avcodec_send_frame(ec, fr);
            av_frame_unref(fr);
        } else r = avcodec_send_frame(ec, NULL);
        while (avcodec_receive_packet(ec, pk) == 0) {
            // The encoder's packet pts is the input pts minus its priming (initial_padding); keep [s0, s1).
            if (pk->pts >= s0 && pk->pts < s1) {
                pk->dts = pk->pts; pk->duration = FRAME; pk->stream_index = 0;
                av_packet_rescale_ts(pk, ec->time_base, os->time_base);
                if (av_interleaved_write_frame(oc, pk) == 0) written++;
            }
            av_packet_unref(pk);
        }
        if (flushing) break;
    }
    av_frame_free(&fr); av_packet_free(&pk);
    av_write_trailer(oc);
    avio_flush(io);
    r = written > 0 ? 0 : -1;
    if (r < 0) seterr(err, errlen, "no audio in this segment", 0);
mux_done:
    if (io) { av_freep(&io->buffer); avio_context_free(&io); }
    if (oc) avformat_free_context(oc);
    avcodec_free_context(&ec);
done:
    for (int c = 0; c < 8; c++) free(p.pl[c]);
    return r;
}

static void window(kr_audio *a, gm_stream *s, int i, int64_t *s0, int64_t *s1) {
    int n = gm_stream_segment_count(s);
    double start = gm_stream_segment_start(s, i);
    double end = i + 1 < n ? gm_stream_segment_start(s, i + 1) : fmax(gm_stream_duration(s), a->duration) + 1.0;
    *s0 = (int64_t)floor(start * a->rate / FRAME) * FRAME;
    *s1 = (int64_t)floor(end * a->rate / FRAME) * FRAME;
    if (i + 1 >= n) *s1 += FRAME;  // the tail: whatever is left
}

int kr_audio_init(kr_audio *a, gm_stream *s, gm_buf *out, char *err, int errlen) {
    int64_t s0, s1;
    window(a, s, 0, &s0, &s1);
    if (produce(a, s0, s1, out, err, errlen) < 0) return -1;
    int m = kr_first_moof(out->data, out->len);
    if (m <= 0) { seterr(err, errlen, "bad init split", 0); return -1; }
    out->len = m;
    return 0;
}

int kr_audio_segment(kr_audio *a, gm_stream *s, int i, gm_buf *out, char *err, int errlen) {
    if (!a || i < 0 || i >= gm_stream_segment_count(s)) { seterr(err, errlen, "bad segment index", 0); return -1; }
    int64_t s0, s1;
    window(a, s, i, &s0, &s1);
    if (produce(a, s0, s1, out, err, errlen) < 0) return -1;
    int m = kr_first_moof(out->data, out->len);
    if (m <= 0) { seterr(err, errlen, "bad segment split", 0); return -1; }
    memmove(out->data, out->data + m, (size_t)(out->len - m));
    out->len -= m;
    return 0;
}
