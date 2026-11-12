// kr_upscale for builds without Apple's frame processor (host tests, Linux): no AI engine, said plainly.
// The iPhone build compiles kr_upscale.m instead (build-airplay.sh leaves this file out there).
#include "kr_upscale.h"
#include <stdio.h>

int kr_upscale_support(int w, int h, int ow, int oh, int engine, char *json, int size) {
    (void)w; (void)h; (void)ow; (void)oh; (void)engine;
    int n = snprintf(json, (size_t)size, "{\"os26\":0,\"engine\":\"none\",\"engine_id\":-1,\"scale\":0,\"model\":\"none\","
                     "\"model_pct\":0,\"why\":\"AI upscaling needs iOS 26 on an iPhone\"}");
    return n < size ? n : -1;
}
int kr_upscale_model(int w, int h, int ow, int oh, int engine, int start, float *pct) {
    (void)w; (void)h; (void)ow; (void)oh; (void)engine; (void)start;
    if (pct) *pct = 0;
    return -1;
}
kr_upscale *kr_upscale_open(int w, int h, int ow, int oh, int engine, char *err, int errlen) {
    (void)w; (void)h; (void)ow; (void)oh; (void)engine;
    if (err && errlen > 0) snprintf(err, (size_t)errlen, "AI upscaling is not available on this device");
    return NULL;
}
int kr_upscale_frame(kr_upscale *u, void *src, double seconds, int sequential, void **out, char *err, int errlen) {
    (void)u; (void)src; (void)seconds; (void)sequential;
    if (out) *out = NULL;
    if (err && errlen > 0) snprintf(err, (size_t)errlen, "AI upscaling is not available on this device");
    return -1;
}
int kr_upscale_out_width(const kr_upscale *u) { (void)u; return 0; }
int kr_upscale_out_height(const kr_upscale *u) { (void)u; return 0; }
int kr_upscale_engine(const kr_upscale *u) { (void)u; return -1; }
const char *kr_upscale_name(const kr_upscale *u) { (void)u; return "none"; }
double kr_upscale_busy_ms(const kr_upscale *u) { (void)u; return 0; }
long kr_upscale_frames(const kr_upscale *u) { (void)u; return 0; }
void kr_upscale_close(kr_upscale *u) { (void)u; }
int kr_device_state(char *json, int size) {
    int n = snprintf(json, (size_t)size, "{\"battery\":-1,\"charging\":-1,\"thermal\":\"unknown\",\"thermal_id\":-1,\"low_power\":0}");
    return n < size ? n : -1;
}
