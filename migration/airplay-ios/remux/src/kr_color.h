// Color-managed compatibility output using FFmpeg 8.1's dynamic frame API.
#ifndef KR_COLOR_H
#define KR_COLOR_H
struct AVFrame;
typedef struct kr_color kr_color;
int kr_color_is_hdr(const struct AVFrame *frame);
// Software frames only. dst format/size must be set; output is limited-range BT.709 SDR.
int kr_color_convert(kr_color **ctx, struct AVFrame *dst, const struct AVFrame *src);
void kr_color_free(kr_color *ctx);
#endif
