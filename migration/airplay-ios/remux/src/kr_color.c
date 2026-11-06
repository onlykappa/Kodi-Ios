#include "kr_color.h"
#include "kr_dovi.h"
#include <errno.h>
#include <stdlib.h>
#include <libavutil/frame.h>
#include <libavutil/opt.h>
#include <libswscale/swscale.h>

struct kr_color { SwsContext *unpack, *map, *pack, *preserve; kr_dovi *dovi; };

int kr_color_is_hdr(const AVFrame *f) {
    return f && (f->color_trc == AVCOL_TRC_SMPTE2084 || f->color_trc == AVCOL_TRC_ARIB_STD_B67 ||
                 f->colorspace == AVCOL_SPC_IPT_C2 || kr_dovi_is_profile5(f));
}

void kr_color_free(kr_color *ctx) {
    if (!ctx) return;
    kr_dovi_free(ctx->dovi);
    sws_free_context(&ctx->unpack); sws_free_context(&ctx->map); sws_free_context(&ctx->pack); sws_free_context(&ctx->preserve); free(ctx);
}

int kr_color_convert(kr_color **ctx, AVFrame *dst, const AVFrame *src) {
    if (!ctx || !src || !dst) return AVERROR(EINVAL);
    if (!*ctx) *ctx = calloc(1, sizeof **ctx);
    if (!*ctx) return AVERROR(ENOMEM);
    kr_color *c = *ctx;
    if (src->colorspace == AVCOL_SPC_IPT_C2 || kr_dovi_is_profile5(src)) {
        AVFrame *pq = av_frame_alloc();
        if (!pq) return AVERROR(ENOMEM);
        pq->width = dst->width; pq->height = dst->height;
        int r = kr_dovi_convert(&c->dovi, pq, src);
        if (r >= 0) r = kr_color_convert(ctx, dst, pq);
        av_frame_free(&pq);
        return r;
    }
    if (!c->map) c->map = sws_alloc_context();
    if (!c->map) return AVERROR(ENOMEM);
    AVFrame *in = av_frame_alloc(), *rgb = av_frame_alloc();
    int r = AVERROR(ENOMEM);
    if (!in || !rgb) goto done;
    // Resize before the expensive 3D color map. Keep 16-bit RGB and the original
    // transfer/primaries, so 4K sources are mapped at output resolution without an 8-bit HDR intermediate.
    in->format = AV_PIX_FMT_RGB48LE; in->width = dst->width; in->height = dst->height;
    if ((r = av_frame_get_buffer(in, 0)) < 0 || (r = av_frame_copy_props(in, src)) < 0) goto done;
    if (kr_color_is_hdr(in) && in->color_primaries == AVCOL_PRI_UNSPECIFIED) in->color_primaries = AVCOL_PRI_BT2020;
    int cs = src->colorspace == AVCOL_SPC_BT2020_NCL || src->colorspace == AVCOL_SPC_BT2020_CL ? SWS_CS_BT2020
           : src->colorspace == AVCOL_SPC_BT470BG || src->colorspace == AVCOL_SPC_SMPTE170M ? SWS_CS_ITU601
           : src->colorspace == AVCOL_SPC_BT709 || src->height > 576 ? SWS_CS_ITU709 : SWS_CS_ITU601;
    int flags = src->width >= dst->width * 2 || src->height >= dst->height * 2 ? SWS_FAST_BILINEAR : SWS_BILINEAR;
    c->unpack = sws_getCachedContext(c->unpack, src->width, src->height, src->format,
                                    in->width, in->height, in->format, flags, NULL, NULL, NULL);
    if (!c->unpack) { r = AVERROR(ENOMEM); goto done; }
    r = sws_setColorspaceDetails(c->unpack, sws_getCoefficients(cs), src->color_range == AVCOL_RANGE_JPEG,
                                sws_getCoefficients(cs), 1, 0, 1 << 16, 1 << 16);
    if (r < 0) goto done;
    r = sws_scale(c->unpack, (const uint8_t *const *)src->data, src->linesize, 0, src->height, in->data, in->linesize);
    if (r < 0) goto done;
    in->colorspace = AVCOL_SPC_RGB; in->color_range = AVCOL_RANGE_JPEG;
    c->map->flags = SWS_BILINEAR;
    av_opt_set_int(c->map, "threads", 0, 0);
    c->map->intent = SWS_INTENT_PERCEPTUAL;
    rgb->format = AV_PIX_FMT_RGB48LE; rgb->width = dst->width; rgb->height = dst->height;
    rgb->color_range = AVCOL_RANGE_JPEG; rgb->color_primaries = AVCOL_PRI_BT709;
    rgb->color_trc = AVCOL_TRC_BT709; rgb->colorspace = AVCOL_SPC_RGB;
    // Dynamic mode maps transfer/gamut, retaining precision before the final eight-bit pack.
    r = sws_scale_frame(c->map, rgb, in);
    if (r < 0) goto done;
    // In this pinned FFmpeg, the managed YUV output path saturates neutral chroma. RGB48
    // mapping followed by the proven matrix/range pack avoids that defect (pixel-tested).
    c->pack = sws_getCachedContext(c->pack, rgb->width, rgb->height, AV_PIX_FMT_RGB48LE,
                                  dst->width, dst->height, dst->format, SWS_BILINEAR | SWS_ACCURATE_RND, NULL, NULL, NULL);
    if (!c->pack) { r = AVERROR(ENOMEM); goto done; }
    r = sws_setColorspaceDetails(c->pack, sws_getCoefficients(SWS_CS_ITU709), 1,
                                sws_getCoefficients(SWS_CS_ITU709), 0, 0, 1 << 16, 1 << 16);
    if (r < 0) goto done;
    dst->color_range = AVCOL_RANGE_MPEG; dst->color_primaries = AVCOL_PRI_BT709;
    dst->color_trc = AVCOL_TRC_BT709; dst->colorspace = AVCOL_SPC_BT709;
    if (!dst->data[0] && (r = av_frame_get_buffer(dst, 0)) < 0) goto done;
    r = sws_scale(c->pack, (const uint8_t *const *)rgb->data, rgb->linesize, 0, rgb->height, dst->data, dst->linesize);
done:
    av_frame_free(&in); av_frame_free(&rgb);
    return r;
}

int kr_color_preserve(kr_color **ctx,AVFrame *dst,const AVFrame *src) {
    if(!ctx || !src || !dst)return AVERROR(EINVAL);
    if(!*ctx)*ctx=calloc(1,sizeof **ctx);if(!*ctx)return AVERROR(ENOMEM);
    kr_color *c=*ctx;
    c->preserve=sws_getCachedContext(c->preserve,src->width,src->height,src->format,
                    dst->width,dst->height,dst->format,SWS_BICUBIC,NULL,NULL,NULL);
    if(!c->preserve)return AVERROR(ENOMEM);
    int cs=src->colorspace==AVCOL_SPC_BT2020_NCL || src->colorspace==AVCOL_SPC_BT2020_CL?SWS_CS_BT2020:
           src->colorspace==AVCOL_SPC_BT470BG || src->colorspace==AVCOL_SPC_SMPTE170M?SWS_CS_ITU601:SWS_CS_ITU709;
    const int *coeff=sws_getCoefficients(cs);int full=src->color_range==AVCOL_RANGE_JPEG;
    if(sws_setColorspaceDetails(c->preserve,coeff,full,coeff,full,0,1<<16,1<<16)<0)return AVERROR(EINVAL);
    int r=av_frame_get_buffer(dst,32);if(r<0)return r;
    if((r=av_frame_copy_props(dst,src))<0)return r;
    r=sws_scale(c->preserve,(const uint8_t * const*)src->data,src->linesize,0,src->height,dst->data,dst->linesize);
    return r==dst->height?0:AVERROR(EINVAL);
}
