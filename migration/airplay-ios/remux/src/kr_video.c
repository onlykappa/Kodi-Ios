// kr_video: decode -> scale/convert -> H.264 encode -> fragmented MP4, one segment at a time (see kr_video.h).
// Window rule: segment i carries the source frames whose presentation time lies in [start_i, start_{i+1}) of the
// planned grid (the same grid kr_audio and the playlists use), so consecutive segments tile the timeline exactly and
// no source keyframe is needed at the boundary (decoding starts at the keyframe before start_i; earlier frames are
// decoded and dropped). Timestamps stay the source's (absolute), so tfdt places each fragment on the timeline.
// A fresh encoder per segment: its first frame is an IDR, no B-frames, so every segment is a closed GOP.
#include "kr_video.h"
#include "kr_audio.h"  // kr_first_moof
#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/hwcontext.h>
#include <libavutil/imgutils.h>
#include <libavutil/opt.h>
#include <libavutil/pixdesc.h>
#include <libswscale/swscale.h>

struct kr_video {
    gm_source src;
    int64_t pos;
    AVFormatContext *in;
    int index;
    AVCodecContext *dec;
    AVBufferRef *hw;          // VideoToolbox device, NULL for software decoding
    int ow, oh;               // output size
    AVRational fps;           // source frame rate (for the encoder's framerate hint)
    struct SwsContext *sws;
    int sws_w, sws_h, sws_fmt;
    atomic_int abort;
    gm_buf unit0;             // segment 0's whole unit, kept from the init request for the seg0 request after it
};

static const char *encoder_name;

void kr_video_set_encoder(const char *name) { encoder_name = name && *name ? name : NULL; }
const char *kr_video_encoder(void) { return encoder_name ? encoder_name : "h264_videotoolbox"; }
int kr_video_available(void) { return avcodec_find_encoder_by_name(kr_video_encoder()) != NULL; }

void kr_video_output_size(int w, int h, int *ow, int *oh) {
    if (w <= 0 || h <= 0) { w = KR_VIDEO_MAX_W; h = KR_VIDEO_MAX_H; }
    double k = fmin(1.0, fmin((double)KR_VIDEO_MAX_W / w, (double)KR_VIDEO_MAX_H / h));
    int a = (int)lround(w * k), b = (int)lround(h * k);
    a &= ~1; b &= ~1;
    *ow = a < 2 ? 2 : a; *oh = b < 2 ? 2 : b;
}

const char *kr_video_codecs(double fps) { return fps > 30.5 ? "avc1.64002A" : KR_VIDEO_CODECS; }

int kr_video_bitrate(int ow, int oh) {
    double r = 7e6 * ((double)ow * oh) / (1920.0 * 1080.0);
    return (int)fmax(1.5e6, fmin(8e6, r));
}

int kr_video_in_window(double t, double start, double end) {
    const double eps = 1e-6;
    return t >= start - eps && (end < 0 || t < end - eps);
}

void kr_video_window(gm_stream *s, int i, double *start, double *end) {
    int n = gm_stream_segment_count(s);
    *start = i <= 0 ? -1e9 : gm_stream_segment_start(s, i);  // the first segment also takes anything before 0
    *end = i + 1 < n ? gm_stream_segment_start(s, i + 1) : -1;
}

static void seterr(char *err, int len, const char *what, int r) {
    if (!err || len <= 0) return;
    char e[96] = "";
    if (r < 0) av_strerror(r, e, sizeof e);
    snprintf(err, (size_t)len, "video conversion: %s%s%s", what, *e ? ": " : "", e);
}

int kr_video_pick_stream(gm_stream *s) {
    int v = gm_stream_selected_video(s);
    if (v >= 0) return v;
    AVFormatContext *f = gm_stream_format_context(s);
    for (unsigned i = 0; f && i < f->nb_streams; i++) {
        AVStream *st = f->streams[i];
        if (st->codecpar->codec_type != AVMEDIA_TYPE_VIDEO || (st->disposition & AV_DISPOSITION_ATTACHED_PIC)) continue;
        if (avcodec_find_decoder(st->codecpar->codec_id)) return (int)i;
    }
    return -1;
}

static int in_read(void *o, uint8_t *buf, int n) {
    kr_video *v = o;
    if (atomic_load(&v->abort)) return AVERROR_EXIT;
    int r = v->src.read(v->src.ctx, v->pos, buf, n);
    if (r > 0) { v->pos += r; return r; }
    return r == 0 ? AVERROR_EOF : AVERROR(EIO);
}

static int64_t in_seek(void *o, int64_t off, int whence) {
    kr_video *v = o;
    int64_t size = v->src.size ? v->src.size(v->src.ctx) : -1;
    switch (whence & ~AVSEEK_FORCE) {
        case AVSEEK_SIZE: return size;
        case SEEK_SET: v->pos = off; break;
        case SEEK_CUR: v->pos += off; break;
        case SEEK_END: if (size < 0) return -1; v->pos = size + off; break;
        default: return -1;
    }
    return v->pos;
}

// Hardware decoding when the decoder offers VideoToolbox frames, else the first software format.
static enum AVPixelFormat pick_format(AVCodecContext *c, const enum AVPixelFormat *fmts) {
    for (const enum AVPixelFormat *p = fmts; *p != AV_PIX_FMT_NONE; p++)
        if (*p == AV_PIX_FMT_VIDEOTOOLBOX && c->hw_device_ctx) return *p;
    for (const enum AVPixelFormat *p = fmts; *p != AV_PIX_FMT_NONE; p++) {
        const AVPixFmtDescriptor *d = av_pix_fmt_desc_get(*p);
        if (d && !(d->flags & AV_PIX_FMT_FLAG_HWACCEL)) return *p;
    }
    return fmts[0];
}

static int open_decoder(kr_video *v, int hw, char *err, int errlen) {
    AVStream *st = v->in->streams[v->index];
    const AVCodec *dec = avcodec_find_decoder(st->codecpar->codec_id);
    if (!dec) { seterr(err, errlen, "no decoder for this video codec", 0); return -1; }
    avcodec_free_context(&v->dec);
    av_buffer_unref(&v->hw);
    v->dec = avcodec_alloc_context3(dec);
    if (!v->dec) { seterr(err, errlen, "out of memory", 0); return -1; }
    avcodec_parameters_to_context(v->dec, st->codecpar);
    v->dec->pkt_timebase = st->time_base;
    v->dec->get_format = pick_format;
    // VideoToolbox (iOS build only: the host FFmpeg has no hwaccel, av_hwdevice_ctx_create fails, software it is).
    if (hw && av_hwdevice_ctx_create(&v->hw, AV_HWDEVICE_TYPE_VIDEOTOOLBOX, NULL, NULL, 0) == 0)
        v->dec->hw_device_ctx = av_buffer_ref(v->hw);
    else v->dec->thread_count = 0;  // software: all cores
    int r = avcodec_open2(v->dec, dec, NULL);
    if (r < 0) { seterr(err, errlen, "decoder", r); return -1; }
    return 0;
}

kr_video *kr_video_open(gm_source src, int index, char *err, int errlen) {
    kr_video *v = calloc(1, sizeof *v);
    if (!v) return NULL;
    v->src = src; v->index = index; v->sws_fmt = -1;
    uint8_t *iob = av_malloc(1 << 16);
    AVIOContext *io = avio_alloc_context(iob, 1 << 16, 0, v, in_read, NULL, in_seek);
    v->in = avformat_alloc_context();
    if (!io || !v->in) { seterr(err, errlen, "out of memory", 0); av_free(iob); goto fail; }
    v->in->pb = io;
    v->in->probesize = 2 * 1024 * 1024;
    v->in->max_analyze_duration = 2 * AV_TIME_BASE;
    int r = avformat_open_input(&v->in, NULL, NULL, NULL);
    if (r < 0) { seterr(err, errlen, "open", r); v->in = NULL; avio_context_free(&io); goto fail; }
    if ((r = avformat_find_stream_info(v->in, NULL)) < 0) { seterr(err, errlen, "probe", r); goto fail; }
    if (index < 0 || index >= (int)v->in->nb_streams || v->in->streams[index]->codecpar->codec_type != AVMEDIA_TYPE_VIDEO) {
        seterr(err, errlen, "no such video track", 0); goto fail;
    }
    if (!kr_video_available()) { seterr(err, errlen, "no H.264 encoder in this build", 0); goto fail; }
    if (open_decoder(v, 1, err, errlen) < 0) goto fail;
    AVStream *st = v->in->streams[index];
    kr_video_output_size(st->codecpar->width, st->codecpar->height, &v->ow, &v->oh);
    v->fps = st->avg_frame_rate.num > 0 && st->avg_frame_rate.den > 0 ? st->avg_frame_rate : st->r_frame_rate;
    if (v->fps.num <= 0 || v->fps.den <= 0) v->fps = (AVRational){ 24000, 1001 };
    for (unsigned i = 0; i < v->in->nb_streams; i++) v->in->streams[i]->discard = i == (unsigned)index ? AVDISCARD_DEFAULT : AVDISCARD_ALL;
    return v;
fail:
    kr_video_close(v);
    return NULL;
}

int kr_video_width(const kr_video *v) { return v ? v->ow : 0; }
int kr_video_height(const kr_video *v) { return v ? v->oh : 0; }
int kr_video_hw_decode(const kr_video *v) { return v && v->hw ? 1 : 0; }
void kr_video_abort(kr_video *v) { if (v) atomic_store(&v->abort, 1); }

void kr_video_close(kr_video *v) {
    if (!v) return;
    avcodec_free_context(&v->dec);
    av_buffer_unref(&v->hw);
    sws_freeContext(v->sws);
    if (v->in) {
        AVIOContext *io = v->in->pb;
        avformat_close_input(&v->in);
        if (io) { av_freep(&io->buffer); avio_context_free(&io); }
    }
    free(v->unit0.data);
    free(v);
}

// ── output into a gm_buf ───────────────────────────────────────────────────────
typedef struct { gm_buf *b; int64_t pos; } wctx;
static int ensure(gm_buf *b, int64_t need) {
    if (need <= b->cap) return 0;
    int64_t cap = b->cap ? b->cap : 1 << 20;
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

// One segment being produced: encoder + muxer, packets held back one to give each its exact duration.
typedef struct {
    kr_video *v;
    AVCodecContext *enc;
    AVFormatContext *oc;
    AVIOContext *io;
    wctx w;
    AVRational tb;            // source stream time base (= encoder and output time base)
    AVPacket *held;
    int64_t end_ts;           // window end in tb, or AV_NOPTS_VALUE
    int written, header, sent;
    // The encoder counts frames (pts 0, 1, 2... in 1/fps: any encoder takes that time base, MPEG-4 refuses 1/90000);
    // with no B-frames packets come out in input order, and frame n's source timestamp is src_pts[n % RING].
#define RING 1024
    int64_t src_pts[RING];
    int64_t last_pts;         // the latest source pts sent (frames must increase)
    AVFrame *conv;
} job;

static int open_encoder(job *j, char *err, int errlen) {
    kr_video *v = j->v;
    const AVCodec *codec = avcodec_find_encoder_by_name(kr_video_encoder());
    if (!codec) { seterr(err, errlen, "no H.264 encoder in this build", 0); return -1; }
    AVCodecContext *c = j->enc = avcodec_alloc_context3(codec);
    if (!c) { seterr(err, errlen, "out of memory", 0); return -1; }
    c->width = v->ow; c->height = v->oh;
    c->pix_fmt = AV_PIX_FMT_YUV420P;
    const enum AVPixelFormat *fmts = NULL;
    int nfmts = 0;
    if (avcodec_get_supported_config(NULL, codec, AV_CODEC_CONFIG_PIX_FORMAT, 0, (const void **)&fmts, &nfmts) >= 0 &&
        fmts && nfmts > 0) {  // NV12 when the encoder takes it (VideoToolbox's native layout), else yuv420p, else its first
        int nv12 = 0, i420 = 0;
        for (int i = 0; i < nfmts; i++) { nv12 |= fmts[i] == AV_PIX_FMT_NV12; i420 |= fmts[i] == AV_PIX_FMT_YUV420P; }
        c->pix_fmt = nv12 ? AV_PIX_FMT_NV12 : i420 ? AV_PIX_FMT_YUV420P : fmts[0];
    }
    c->time_base = av_inv_q(v->fps);
    c->framerate = v->fps;
    c->sample_aspect_ratio = (AVRational){ 1, 1 };
    c->bit_rate = kr_video_bitrate(v->ow, v->oh);
    c->rc_max_rate = c->bit_rate * 3 / 2;
    c->rc_buffer_size = (int)c->bit_rate * 2;
    c->gop_size = 100000;      // one keyframe: the first frame of the segment
    c->max_b_frames = 0;       // pts == dts, closed GOP
    c->color_range = AVCOL_RANGE_MPEG;
    c->color_primaries = AVCOL_PRI_BT709; c->color_trc = AVCOL_TRC_BT709; c->colorspace = AVCOL_SPC_BT709;
    c->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;  // closed GOP by construction: one IDR first, no B-frames
    if (!strcmp(codec->name, "h264_videotoolbox")) {
        c->profile = AV_PROFILE_H264_HIGH;
        av_opt_set_int(c->priv_data, "level", av_q2d(v->fps) > 30.5 ? 42 : 40, 0);  // matches kr_video_codecs
        av_opt_set_int(c->priv_data, "realtime", 1, 0);      // speed over size: segments are made while the TV waits
        av_opt_set_int(c->priv_data, "allow_sw", 0, 0);      // the hardware encoder only (battery)
    }
    int r = avcodec_open2(c, codec, NULL);
    if (r < 0) { seterr(err, errlen, "encoder", r); return -1; }

    avformat_alloc_output_context2(&j->oc, NULL, "mp4", NULL);
    AVStream *os = j->oc ? avformat_new_stream(j->oc, NULL) : NULL;
    uint8_t *iob = av_malloc(1 << 16);
    j->io = iob ? avio_alloc_context(iob, 1 << 16, 1, &j->w, NULL, w_write, w_seek) : NULL;
    if (!os || !j->io) { if (!j->io) av_free(iob); seterr(err, errlen, "muxer", 0); return -1; }
    avcodec_parameters_from_context(os->codecpar, c);
    if (c->codec_id == AV_CODEC_ID_H264) os->codecpar->codec_tag = MKTAG('a', 'v', 'c', '1');
    os->time_base = j->tb;
    os->avg_frame_rate = v->fps;
    j->oc->pb = j->io;
    j->oc->flags |= AVFMT_FLAG_BITEXACT;
    j->oc->avoid_negative_ts = AVFMT_AVOID_NEG_TS_DISABLED;
    AVDictionary *o = NULL;
    av_dict_set(&o, "movflags", "frag_keyframe+empty_moov+default_base_moof+delay_moov+frag_discont", 0);
    r = avformat_write_header(j->oc, &o);
    av_dict_free(&o);
    if (r < 0) { seterr(err, errlen, "mux header", r); return -1; }
    j->header = 1;
    return 0;
}

static int write_packet(job *j, AVPacket *pk) {
    pk->stream_index = 0;
    pk->dts = pk->pts;
    pk->pos = -1;
    av_packet_rescale_ts(pk, j->tb, j->oc->streams[0]->time_base);  // the muxer picked its own timescale
    int r = av_interleaved_write_frame(j->oc, pk);
    if (r == 0) j->written++;
    return r;
}

// Holds each encoded packet until the next one arrives, so its duration reaches exactly the next frame (and the last
// one reaches the window end): the fragments tile with no gap.
static int take_packets(job *j, int flushing) {
    AVPacket *pk = av_packet_alloc();
    int r = 0;
    while (avcodec_receive_packet(j->enc, pk) == 0) {
        if (pk->pts == AV_NOPTS_VALUE || pk->pts < 0 || pk->pts >= j->sent) { av_packet_unref(pk); continue; }
        pk->pts = j->src_pts[pk->pts % RING];  // back to the source's (absolute) time
        if (j->held->data) {
            if (pk->pts <= j->held->pts) { av_packet_unref(pk); continue; }  // never out of order (no B-frames)
            j->held->duration = pk->pts - j->held->pts;
            r = write_packet(j, j->held);
            av_packet_unref(j->held);
            if (r < 0) break;
        }
        av_packet_move_ref(j->held, pk);
    }
    if (flushing && j->held->data && r >= 0) {
        int64_t d = j->end_ts != AV_NOPTS_VALUE ? j->end_ts - j->held->pts : 0;
        if (d <= 0) d = j->held->duration > 0 ? j->held->duration : av_rescale_q(1, av_inv_q(j->v->fps), j->tb);
        j->held->duration = d;
        r = write_packet(j, j->held);
        av_packet_unref(j->held);
    }
    av_packet_free(&pk);
    return r;
}

// Scale/convert a decoded (software) frame to the encoder's size and format; HDR and 10-bit become 8-bit BT.709 range
// without tone mapping.
static int convert(job *j, AVFrame *src, char *err, int errlen) {
    kr_video *v = j->v;
    if (!v->sws || v->sws_w != src->width || v->sws_h != src->height || v->sws_fmt != src->format) {
        sws_freeContext(v->sws);
        v->sws = sws_getContext(src->width, src->height, src->format, v->ow, v->oh, j->enc->pix_fmt,
                                SWS_BILINEAR, NULL, NULL, NULL);
        if (!v->sws) { seterr(err, errlen, "scaler", 0); return -1; }
        int in_cs = src->colorspace == AVCOL_SPC_BT2020_NCL || src->colorspace == AVCOL_SPC_BT2020_CL ? SWS_CS_BT2020
                  : src->colorspace == AVCOL_SPC_BT470BG || src->colorspace == AVCOL_SPC_SMPTE170M ? SWS_CS_ITU601
                  : src->colorspace == AVCOL_SPC_BT709 ? SWS_CS_ITU709
                  : (src->height > 576 ? SWS_CS_ITU709 : SWS_CS_ITU601);
        int full = src->color_range == AVCOL_RANGE_JPEG;
        sws_setColorspaceDetails(v->sws, sws_getCoefficients(in_cs), full, sws_getCoefficients(SWS_CS_ITU709), 0,
                                 0, 1 << 16, 1 << 16);
        v->sws_w = src->width; v->sws_h = src->height; v->sws_fmt = src->format;
    }
    if (!j->conv) {
        j->conv = av_frame_alloc();
        if (!j->conv) return -1;
        j->conv->format = j->enc->pix_fmt; j->conv->width = v->ow; j->conv->height = v->oh;
        if (av_frame_get_buffer(j->conv, 0) < 0) { seterr(err, errlen, "out of memory", 0); return -1; }
    }
    if (av_frame_make_writable(j->conv) < 0) return -1;
    sws_scale(v->sws, (const uint8_t * const *)src->data, src->linesize, 0, src->height, j->conv->data, j->conv->linesize);
    return 0;
}

static int encode_frame(job *j, AVFrame *fr, int64_t pts, char *err, int errlen) {
    AVFrame *sw = fr;
    AVFrame *tmp = NULL;
    if (fr->format == AV_PIX_FMT_VIDEOTOOLBOX) {  // a hardware frame: copy it down (NV12 or P010)
        tmp = av_frame_alloc();
        if (!tmp || av_hwframe_transfer_data(tmp, fr, 0) < 0) { av_frame_free(&tmp); seterr(err, errlen, "hardware frame", 0); return -1; }
        tmp->colorspace = fr->colorspace; tmp->color_range = fr->color_range;
        sw = tmp;
    }
    if (!j->enc && open_encoder(j, err, errlen) < 0) { av_frame_free(&tmp); return -1; }
    int r = convert(j, sw, err, errlen);
    av_frame_free(&tmp);
    if (r < 0) return -1;
    j->src_pts[j->sent % RING] = pts;
    j->conv->pts = j->sent;
    j->last_pts = pts;
    j->conv->pict_type = j->sent == 0 ? AV_PICTURE_TYPE_I : AV_PICTURE_TYPE_NONE;
    if ((r = avcodec_send_frame(j->enc, j->conv)) < 0) { seterr(err, errlen, "encode", r); return -1; }
    j->sent++;
    // The encoder keeps its own reference only if it needs one; a fresh buffer next time keeps this frame intact.
    av_frame_unref(j->conv); av_frame_free(&j->conv);
    return take_packets(j, 0) < 0 ? (seterr(err, errlen, "mux", 0), -1) : 0;
}

// Positions the demuxer on a packet of the stream presented at or before `start`. A backward seek is not exact in
// every container (MPEG-TS lands on the next keyframe after the target), so the first packet is checked and the seek
// goes further back when it is late; the beginning of the file is the last resort.
static void seek_before(kr_video *v, double start) {
    AVStream *st = v->in->streams[v->index];
    double back = 0.25;
    AVPacket *p = av_packet_alloc();
    for (int k = 0; p && k < 6; k++, back *= 4) {
        double from = start - back;
        if (from <= 0) break;
        int64_t ts = (int64_t)(from / av_q2d(st->time_base));
        if (av_seek_frame(v->in, v->index, ts, AVSEEK_FLAG_BACKWARD) < 0) break;
        int ok = 0;
        while (av_read_frame(v->in, p) >= 0) {
            // The first keyframe of the stream decides (MPEG-TS lands mid-GOP: frames before it cannot be decoded).
            int is_key = p->stream_index == v->index && (p->flags & AV_PKT_FLAG_KEY);
            int64_t t0 = p->pts != AV_NOPTS_VALUE ? p->pts : p->dts;
            av_packet_unref(p);
            if (!is_key) continue;
            ok = t0 == AV_NOPTS_VALUE || t0 * av_q2d(st->time_base) <= start + 1e-6;
            break;
        }
        if (ok && av_seek_frame(v->in, v->index, ts, AVSEEK_FLAG_BACKWARD) >= 0) { av_packet_free(&p); return; }
    }
    av_packet_free(&p);
    av_seek_frame(v->in, -1, 0, AVSEEK_FLAG_BACKWARD);
}

// The whole unit (ftyp+moov+moof+mdat) for the source frames in [start, end).
static int produce(kr_video *v, double start, double end, gm_buf *out, char *err, int errlen) {
    out->len = 0;
    AVStream *st = v->in->streams[v->index];
    job j = { .v = v, .tb = st->time_base, .w = { out, 0 } };
    j.held = av_packet_alloc();
    j.end_ts = end >= 0 ? llround(end / av_q2d(st->time_base)) : AV_NOPTS_VALUE;
    AVPacket *pkt = av_packet_alloc();
    AVFrame *fr = av_frame_alloc();
    int r = -1, eof = 0, done = 0, retried = 0;
    if (!j.held || !pkt || !fr) { seterr(err, errlen, "out of memory", 0); goto out; }
    seek_before(v, start);
    avcodec_flush_buffers(v->dec);
    while (!done && !eof) {
        if (atomic_load(&v->abort)) { seterr(err, errlen, "stopped", 0); goto out; }
        int rr = av_read_frame(v->in, pkt);
        if (rr == AVERROR_EOF) { eof = 1; avcodec_send_packet(v->dec, NULL); }
        else if (rr < 0) { seterr(err, errlen, "read", rr); goto out; }
        else if (pkt->stream_index != v->index) { av_packet_unref(pkt); continue; }
        else {
            int sr = avcodec_send_packet(v->dec, pkt);
            av_packet_unref(pkt);
            if (sr < 0 && sr != AVERROR(EAGAIN) && sr != AVERROR_INVALIDDATA && v->hw && !retried && j.sent == 0) {
                // VideoToolbox refused this stream (a profile the phone's decoder lacks): software from here on.
                retried = 1;
                if (open_decoder(v, 0, err, errlen) < 0) goto out;
                seek_before(v, start);
                continue;
            }
        }
        while (avcodec_receive_frame(v->dec, fr) == 0) {
            int64_t pts = fr->best_effort_timestamp != AV_NOPTS_VALUE ? fr->best_effort_timestamp : fr->pts;
            if (pts == AV_NOPTS_VALUE) { av_frame_unref(fr); continue; }
            double t = pts * av_q2d(st->time_base);
            if (end >= 0 && t >= end - 1e-6) { done = 1; av_frame_unref(fr); break; }
            if (kr_video_in_window(t, start, end) && (j.sent == 0 || pts > j.last_pts)) {
                if (encode_frame(&j, fr, pts, err, errlen) < 0) { av_frame_unref(fr); goto out; }
            }
            av_frame_unref(fr);
        }
    }
    if (!j.enc) { seterr(err, errlen, "no video in this segment", 0); goto out; }
    avcodec_send_frame(j.enc, NULL);
    if (take_packets(&j, 1) < 0) { seterr(err, errlen, "mux", 0); goto out; }
    av_write_trailer(j.oc);
    avio_flush(j.io);
    r = j.written > 0 ? 0 : -1;
    if (r < 0) seterr(err, errlen, "no video in this segment", 0);
out:
    if (j.io) { av_freep(&j.io->buffer); avio_context_free(&j.io); }
    if (j.oc) avformat_free_context(j.oc);
    avcodec_free_context(&j.enc);
    av_frame_free(&j.conv);
    av_packet_free(&j.held);
    av_frame_free(&fr); av_packet_free(&pkt);
    return r;
}

// Segment 0 as a whole unit (ftyp+moov+moof+mdat), made once: the init request and the seg0 request right after it.
static int unit0(kr_video *v, gm_stream *s, char *err, int errlen) {
    if (v->unit0.len > 0) return 0;
    double start, end;
    kr_video_window(s, 0, &start, &end);
    if (produce(v, start, end, &v->unit0, err, errlen) < 0) { v->unit0.len = 0; return -1; }
    return 0;
}

int kr_video_init(kr_video *v, gm_stream *s, gm_buf *out, char *err, int errlen) {
    if (!v) { seterr(err, errlen, "not open", 0); return -1; }
    if (unit0(v, s, err, errlen) < 0) return -1;
    int m = kr_first_moof(v->unit0.data, v->unit0.len);
    if (m <= 0) { seterr(err, errlen, "bad init split", 0); return -1; }
    out->len = 0;
    if (ensure(out, m) < 0) { seterr(err, errlen, "out of memory", 0); return -1; }
    memcpy(out->data, v->unit0.data, (size_t)m);
    out->len = m;
    return 0;
}

int kr_video_segment(kr_video *v, gm_stream *s, int i, gm_buf *out, char *err, int errlen) {
    if (!v || i < 0 || i >= gm_stream_segment_count(s)) { seterr(err, errlen, "bad segment index", 0); return -1; }
    if (i == 0 && v->unit0.len > 0) {
        int m = kr_first_moof(v->unit0.data, v->unit0.len);
        if (m <= 0) { seterr(err, errlen, "bad segment split", 0); return -1; }
        out->len = 0;
        if (ensure(out, v->unit0.len - m) < 0) { seterr(err, errlen, "out of memory", 0); return -1; }
        memcpy(out->data, v->unit0.data + m, (size_t)(v->unit0.len - m));
        out->len = v->unit0.len - m;
        return 0;
    }
    double start, end;
    kr_video_window(s, i, &start, &end);
    if (produce(v, start, end, out, err, errlen) < 0) return -1;
    int m = kr_first_moof(out->data, out->len);
    if (m <= 0) { seterr(err, errlen, "bad segment split", 0); return -1; }
    memmove(out->data, out->data + m, (size_t)(out->len - m));
    out->len -= m;
    return 0;
}
