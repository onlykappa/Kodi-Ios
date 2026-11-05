/* Dolby Vision profile-5 base-layer renderer. LGPL-2.1-or-later.
 * Reshaping / matrix sequence follows libplacebo (Niklas Haas et al.), commit
 * 0e4352271c7cf85399d2589df4158781cf4c4e93, src/shaders/colorspace.c and
 * src/include/libplacebo/utils/libav_internal.h. Kodi changes: CPU implementation,
 * validated FFmpeg metadata, direct reshaping/matrices, one-dimensional PQ tables
 * and output-size component resampling (no approximate 3D color LUT).
 * See THIRD-PARTY-NOTICES. No enhancement-layer/FEL composition is performed here.
 */
#include "kr_dovi.h"
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/frame.h>
#include <libavutil/intreadwrite.h>
#include <libavutil/opt.h>
#include <libavutil/pixdesc.h>
#include <libavutil/mastering_display_metadata.h>
#include <libswscale/swscale.h>

struct kr_dovi {
    struct SwsContext *scale;
    AVDOVIRpuDataHeader header;
    AVDOVIDataMapping mapping;
    AVDOVIColorMetadata color;
    float decode[65537];
    uint16_t encode[65026];
    double nonlinear[9], linear[9], offset[3];
    int ready;
};
static double clip(double x, double lo, double hi) { return fmax(lo, fmin(hi, x)); }
static const AVDOVIMetadata *metadata(const AVFrame *f) {
    const AVFrameSideData *sd = av_frame_get_side_data(f, AV_FRAME_DATA_DOVI_METADATA);
    if (!sd || sd->size < sizeof(AVDOVIMetadata)) return NULL;
    const AVDOVIMetadata *m = (const void *)sd->data;
#define FITS(field, type) (m->field >= sizeof(*m) && m->field % _Alignof(type) == 0 && m->field <= sd->size && sizeof(type) <= sd->size-m->field)
    if (!FITS(header_offset,AVDOVIRpuDataHeader) || !FITS(mapping_offset,AVDOVIDataMapping) || !FITS(color_offset,AVDOVIColorMetadata)) return NULL;
#undef FITS
    return m;
}
int kr_dovi_is_profile5(const AVFrame *f) {
    const AVDOVIMetadata *m = f ? metadata(f) : NULL;
    const AVDOVIRpuDataHeader *h = m ? av_dovi_get_header(m) : NULL;
    return h && h->vdr_rpu_profile == 0 && h->bl_video_full_range_flag;
}
void kr_dovi_free(kr_dovi *c) {
    if (!c) return;
    sws_free_context(&c->scale); free(c);
}
static double pq_decode(double v) {
    double p = pow(clip(v,0,1), 1.0/(2523.0/32));
    return pow(fmax(p-3424.0/4096,0)/(2413.0/128-2392.0/128*p), 1.0/(2610.0/16384));
}
static double pq_encode(double v) {
    double p = pow(fmax(v,0),2610.0/16384);
    return clip(pow((3424.0/4096+2413.0/128*p)/(1+2392.0/128*p),2523.0/32),0,1);
}
static double decode_pq(const kr_dovi *c, double v) {
    double p=clip(v,0,1)*65536;int i=(int)p;
    return i==65536 ? c->decode[i] : c->decode[i]+(p-i)*(c->decode[i+1]-c->decode[i]);
}
static double encode_pq(const kr_dovi *c, double v) {
    // Float exponent/mantissa index gives a logarithmic table with fine resolution near black.
    float p=(float)clip(v,0,1);uint32_t bits;memcpy(&bits,&p,sizeof bits);
    unsigned i=bits>>14;double f=(bits&16383)/16384.0;
    return (c->encode[i]+f*(c->encode[i+1]-c->encode[i]))/65535.0;
}
static int validate(const AVDOVIRpuDataHeader *h, const AVDOVIDataMapping *m, const AVDOVIColorMetadata *c) {
    if (h->vdr_rpu_profile != 0 || !h->bl_video_full_range_flag || h->bl_bit_depth < 8 || h->bl_bit_depth > 16 ||
        h->coef_log2_denom > 32 || !h->disable_residual_flag) return AVERROR(ENOTSUP);
    for (int k=0;k<9;k++) if (!c->ycc_to_rgb_matrix[k].den || !c->rgb_to_lms_matrix[k].den) return AVERROR_INVALIDDATA;
    for (int k=0;k<3;k++) {
        if (!c->ycc_to_rgb_offset[k].den) return AVERROR_INVALIDDATA;
        const AVDOVIReshapingCurve *r = &m->curves[k];
        if (r->num_pivots < 2 || r->num_pivots > 9) return AVERROR_INVALIDDATA;
        for (int i=0;i<r->num_pivots;i++)
            if (r->pivots[i] >= (1u<<h->bl_bit_depth) || (i && r->pivots[i] <= r->pivots[i-1])) return AVERROR_INVALIDDATA;
        for (int i=0;i<r->num_pivots-1;i++) {
            if (r->mapping_idc[i] == AV_DOVI_MAPPING_POLYNOMIAL) {
                if (r->poly_order[i]<1 || r->poly_order[i]>2) return AVERROR_INVALIDDATA;
            } else if (r->mapping_idc[i] == AV_DOVI_MAPPING_MMR) {
                if (r->mmr_order[i]<1 || r->mmr_order[i]>3) return AVERROR_INVALIDDATA;
            } else return AVERROR_INVALIDDATA;
        }
    }
    return 0;
}
static void render_pixel(const kr_dovi *c, const double input[3], double out[3]) {
    double sig[3], shaped[3], linear[3];
    double scale = ldexp(1.0,-c->header.coef_log2_denom), pivot_scale = ldexp(1.0,-c->header.bl_bit_depth);
    for (int k=0;k<3;k++) {
        const AVDOVIReshapingCurve *r=&c->mapping.curves[k];
        sig[k]=clip(input[k],r->pivots[0]*pivot_scale,r->pivots[r->num_pivots-1]*pivot_scale);
    }
    for (int k=0;k<3;k++) {
        const AVDOVIReshapingCurve *r=&c->mapping.curves[k]; int i=0;
        while (i<r->num_pivots-2 && sig[k]>=r->pivots[i+1]*pivot_scale) i++;
        double v=0;
        if (r->mapping_idc[i]==AV_DOVI_MAPPING_POLYNOMIAL) {
            for (int j=r->poly_order[i];j>=0;j--) v=v*sig[k]+r->poly_coef[i][j]*scale;
        } else {
            double terms[7]={sig[0],sig[1],sig[2],sig[0]*sig[1],sig[0]*sig[2],sig[1]*sig[2],sig[0]*sig[1]*sig[2]};
            v=r->mmr_constant[i]*scale;
            for (int n=0;n<7;n++) {
                double power=terms[n];
                for (int j=0;j<r->mmr_order[i];j++,power*=terms[n]) v+=r->mmr_coef[i][j][n]*scale*power;
            }
        }
        shaped[k]=clip(v,0,1);
    }
    for (int k=0;k<3;k++) {
        double v=0;
        for (int j=0;j<3;j++) v+=c->nonlinear[k*3+j]*(shaped[j]-c->offset[j]);
        linear[k]=decode_pq(c,v);
    }
    for (int k=0;k<3;k++) {
        double v=0;
        for (int j=0;j<3;j++) v+=c->linear[k*3+j]*linear[j];
        out[k]=encode_pq(c,v);
    }
}
static int configure(kr_dovi *c, const AVDOVIMetadata *meta) {
    const AVDOVIRpuDataHeader *h=av_dovi_get_header(meta);
    const AVDOVIDataMapping *m=av_dovi_get_mapping(meta);
    const AVDOVIColorMetadata *color=av_dovi_get_color(meta);
    int r=validate(h,m,color); if (r<0) return r;
    if (c->ready && !memcmp(&c->header,h,sizeof *h) && !memcmp(&c->mapping,m,sizeof *m) &&
        !memcmp(c->color.ycc_to_rgb_matrix,color->ycc_to_rgb_matrix,sizeof color->ycc_to_rgb_matrix) &&
        !memcmp(c->color.ycc_to_rgb_offset,color->ycc_to_rgb_offset,sizeof color->ycc_to_rgb_offset) &&
        !memcmp(c->color.rgb_to_lms_matrix,color->rgb_to_lms_matrix,sizeof color->rgb_to_lms_matrix)) { c->color=*color;return 0; }
    if (!c->ready) {
        for (int i=0;i<=65536;i++) c->decode[i]=(float)pq_decode(i/65536.0);
        for (unsigned i=0;i<65026;i++) {
            uint32_t bits=i<<14;float f;memcpy(&f,&bits,sizeof f);
            c->encode[i]=(uint16_t)lround(pq_encode(f)*65535);
        }
    }
    c->header=*h; c->mapping=*m; c->color=*color;
    static const double hpe[3][3]={{3.06441879,-2.16597676,.10155818},{-.65612108,1.78554118,-.12943749},{.01736321,-.04725154,1.03004253}};
    for(int k=0;k<3;k++) { c->offset[k]=av_q2d(color->ycc_to_rgb_offset[k]);
        for(int j=0;j<3;j++){c->nonlinear[k*3+j]=av_q2d(color->ycc_to_rgb_matrix[k*3+j]);c->linear[k*3+j]=0;
            for(int n=0;n<3;n++)c->linear[k*3+j]+=hpe[k][n]*av_q2d(color->rgb_to_lms_matrix[n*3+j]);}}
    c->ready=1;
    return 0;
}
int kr_dovi_convert(kr_dovi **ctx, AVFrame *dst, const AVFrame *src) {
    if (!ctx || !dst || !src) return AVERROR(EINVAL);
    const AVPixFmtDescriptor *desc=av_pix_fmt_desc_get(src->format);
    if (!desc || desc->nb_components<3 || (desc->flags & (AV_PIX_FMT_FLAG_RGB|AV_PIX_FMT_FLAG_HWACCEL))) return AVERROR(ENOTSUP);
    const AVDOVIMetadata *meta=metadata(src);
    if (!meta) return AVERROR_INVALIDDATA;
    if (!*ctx) *ctx=calloc(1,sizeof **ctx);
    if (!*ctx) return AVERROR(ENOMEM);
    kr_dovi *c=*ctx; int r=configure(c,meta); if (r<0) return r;
    AVFrame *raw=av_frame_alloc(); if (!raw) return AVERROR(ENOMEM);
    raw->format=AV_PIX_FMT_YUV444P16LE; raw->width=dst->width; raw->height=dst->height;
    if ((r=av_frame_get_buffer(raw,0))<0) goto done;
    c->scale=sws_getCachedContext(c->scale,src->width,src->height,src->format,raw->width,raw->height,raw->format,SWS_BILINEAR,NULL,NULL,NULL);
    if (!c->scale) { r=AVERROR(ENOMEM); goto done; }
    // Raw component codes, not a YCbCr -> RGB conversion or limited-range expansion.
    if ((r=sws_setColorspaceDetails(c->scale,sws_getCoefficients(SWS_CS_ITU709),1,sws_getCoefficients(SWS_CS_ITU709),1,0,1<<16,1<<16))<0) goto done;
    if ((r=sws_scale(c->scale,(const uint8_t *const *)src->data,src->linesize,0,src->height,raw->data,raw->linesize))<0) goto done;
    dst->format=AV_PIX_FMT_RGB48LE;
    if ((r=av_frame_get_buffer(dst,0))<0 || (r=av_frame_copy_props(dst,src))<0) goto done;
    av_frame_remove_side_data(dst,AV_FRAME_DATA_DOVI_METADATA); av_frame_remove_side_data(dst,AV_FRAME_DATA_DOVI_RPU_BUFFER);
    dst->color_range=AVCOL_RANGE_JPEG; dst->colorspace=AVCOL_SPC_RGB; dst->color_primaries=AVCOL_PRI_BT2020; dst->color_trc=AVCOL_TRC_SMPTE2084;
    if(c->color.source_max_pq && c->color.source_max_pq<=4095){
        av_frame_remove_side_data(dst,AV_FRAME_DATA_MASTERING_DISPLAY_METADATA);
        AVMasteringDisplayMetadata *master=av_mastering_display_metadata_create_side_data(dst);
        if(!master){r=AVERROR(ENOMEM);goto done;}
        master->has_luminance=1;
        master->max_luminance=av_d2q(pq_decode(c->color.source_max_pq/4095.0)*10000,1000000);
        master->min_luminance=av_d2q(pq_decode(clip(c->color.source_min_pq/4095.0,0,1))*10000,1000000);
    }
    for (int y=0;y<dst->height;y++) for (int x=0;x<dst->width;x++) {
        double input[3],output[3];
        for (int k=0;k<3;k++) {
            input[k]=AV_RL16(raw->data[k]+y*raw->linesize[k]+x*2)/65536.0;
        }
        render_pixel(c,input,output);
        for (int k=0;k<3;k++) {
            AV_WL16(dst->data[0]+y*dst->linesize[0]+x*6+k*2,(unsigned)lround(output[k]*65535));
        }
    }
    r=0;
done: av_frame_free(&raw); return r;
}
