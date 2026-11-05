// Dolby Vision profile-5 base-layer rendering. LGPL-2.1-or-later.
#ifndef KR_DOVI_H
#define KR_DOVI_H
struct AVFrame;
typedef struct kr_dovi kr_dovi;
// Detect usable profile-5 RPU metadata (also marks these frames as requiring software color processing).
int kr_dovi_is_profile5(const struct AVFrame *frame);
// Software source -> RGB48 BT.2020/PQ at dst's requested dimensions, applying RPU reshaping and matrices.
int kr_dovi_convert(kr_dovi **ctx, struct AVFrame *dst, const struct AVFrame *src);
void kr_dovi_free(kr_dovi *ctx);
#endif
